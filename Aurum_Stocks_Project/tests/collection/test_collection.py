"""tests/collection/test_collection.py — Phase 2 Collection Layer suite.

Verifies the Collection Layer's invariants against the REAL frozen substrate:
full-population accounting, PIT, no features, GC-7 long-only, NO-FALLBACK rejection,
burn isolation, MDVPL-verdict quarantine, idempotency/dedup, recovery/resume, append-only
manifest, and — critically — that running collection leaves the integrity suite 6/6 GREEN and
the READY_FOR_COLLECTION gate unchanged (substrate untouched).
"""
from __future__ import annotations

import datetime as dt
import os
import sys
from zoneinfo import ZoneInfo

import pandas as pd

_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _root)
sys.path.insert(0, os.path.join(_root, "src"))

from aurum_stocks.foundation.observation_builder import SignalEvent, ObservationRow
from aurum_stocks.foundation.dataset_roles import (
    DatasetRole, BurnedSlice, assert_no_calibration_leak, filter_pipeline_dataset,
)
from aurum_stocks.integrity import integrity_suite as isuite

from pipeline.collection.candidate_source import CandidateSource, MockCandidateSource
from pipeline.collection.sink import InMemoryObservationSink
from pipeline.collection.manifest import IngestManifest, BatchStatus
from pipeline.collection.rejections import RejectionCode
from pipeline.collection.keys import candidate_key
from pipeline.collection.wiring import build_mock_collection_engine

ET = ZoneInfo("America/New_York")
D1 = dt.date(2024, 3, 1)
D2 = dt.date(2024, 3, 4)


# --------------------------------------------------------------------- full population
def test_full_population_every_candidate_observed():
    eng = build_mock_collection_engine()
    r = eng.collect_batch("KTOS", D1)
    assert r.status == "COMMITTED" and r.verdict == "PASS"
    assert r.candidate_count == 3 and r.stored_count == 3
    assert r.accounted, r                      # stored+dup+rejected+burned == candidates
    assert len(eng.sink) == 3
    assert all(isinstance(row, ObservationRow) for row in eng.sink.rows())
    print("ok  full-population: every candidate observed, accounted")


# --------------------------------------------------------------------- no features
def test_no_features_generated():
    eng = build_mock_collection_engine()
    eng.collect_batch("KTOS", D1)
    assert all(row.features == {} for row in eng.sink.rows()), "Collection must emit NO features"
    print("ok  no features: every row features == {}")


# --------------------------------------------------------------------- PIT
def test_pit_data_as_of_not_after_signal():
    eng = build_mock_collection_engine()
    eng.collect_batch("KTOS", D1)
    for row in eng.sink.rows():
        assert row.data_as_of_ts <= row.signal_ts_utc, "PIT violation"
        row.assert_signed()                    # 6-id signature + PIT re-checked by the frozen row
    print("ok  PIT: data_as_of_ts <= signal_ts_utc for every row")


# --------------------------------------------------------------------- GC-7 long only
class _ShortCandidates(CandidateSource):
    def candidates(self, symbol, date):
        ts = pd.Timestamp(dt.datetime.combine(date, dt.time(10, 0), ET))
        return [SignalEvent(symbol, ts, "GAP_GO", direction="SHORT",
                            scanner_id="SCAN_MOMENTUM", universe_id="SMALL_CAP_US")]


def test_long_only_hard_fail_not_stored():
    eng = build_mock_collection_engine()
    eng.candidates = _ShortCandidates()
    r = eng.collect_batch("KTOS", D1)
    assert r.stored_count == 0 and r.rejected_count == 1 and r.accounted
    assert len(eng.sink) == 0
    recs = eng.rejections.by_code(RejectionCode.LONG_ONLY_VIOLATION)
    assert len(recs) == 1, "GC-7 long-only violation must be recorded, not stored"
    print("ok  GC-7: non-LONG candidate hard-failed and recorded, never stored")


# --------------------------------------------------------------------- NO-FALLBACK
def test_no_fallback_rejection_recorded():
    # An unknown symbol has no PIT symbol version -> MISSING_SYMBOL_VERSION (no substitute).
    eng = build_mock_collection_engine()      # known symbols: KTOS/PTON/NVAX
    r = eng.collect_batch("GHOST", D1)
    assert r.stored_count == 0 and r.rejected_count == 3 and r.accounted
    recs = eng.rejections.by_code(RejectionCode.MISSING_SYMBOL_VERSION)
    assert len(recs) == 3 and len(eng.sink) == 0
    assert all(rec.reason_code in RejectionCode.REJECTIONS for rec in recs)
    print("ok  NO-FALLBACK: unknown symbol rejected (MISSING_SYMBOL_VERSION), never stored")


# --------------------------------------------------------------------- signature determinism
def test_signature_and_key_deterministic():
    e1 = build_mock_collection_engine(); e1.collect_batch("KTOS", D1)
    e2 = build_mock_collection_engine(); e2.collect_batch("KTOS", D1)
    sig1 = sorted(r.registry_signature_hash for r in e1.sink.rows())
    sig2 = sorted(r.registry_signature_hash for r in e2.sink.rows())
    assert sig1 == sig2, "registry_signature_hash must be reproducible"
    roles1 = sorted(str(r.dataset_role) for r in e1.sink.rows())
    roles2 = sorted(str(r.dataset_role) for r in e2.sink.rows())
    assert roles1 == roles2, "dataset_role must be deterministic"
    print("ok  determinism: signatures + roles reproducible across runs")


# --------------------------------------------------------------------- idempotency / dedup
def test_idempotent_dedup_shared_sink():
    sink = InMemoryObservationSink()
    a = build_mock_collection_engine(sink=sink, manifest=IngestManifest())
    a.collect_batch("KTOS", D1)
    assert len(sink) == 3
    # fresh manifest -> no skip; dedup must catch every row at the sink (candidate_key).
    b = build_mock_collection_engine(sink=sink, manifest=IngestManifest())
    r = b.collect_batch("KTOS", D1)
    assert r.stored_count == 0 and r.duplicate_count == 3 and r.accounted
    assert len(sink) == 3, "no duplicate rows written"
    print("ok  idempotency: re-collection dedups at the sink (0 new, 3 dup)")


def test_recovery_skip_via_manifest():
    sink = InMemoryObservationSink(); man = IngestManifest()
    eng = build_mock_collection_engine(sink=sink, manifest=man)
    eng.collect([(s, D1) for s in ("KTOS", "PTON", "NVAX")])
    assert len(sink) == 9
    # simulate restart: NEW engine, SAME sink+manifest, superset of specs
    eng2 = build_mock_collection_engine(sink=sink, manifest=man)
    specs = [(s, d) for s in ("KTOS", "PTON", "NVAX") for d in (D1, D2)]
    res = eng2.collect(specs)
    skipped = [r for r in res if r.status == "SKIPPED"]
    committed = [r for r in res if r.status == "COMMITTED"]
    assert len(skipped) == 3 and len(committed) == 3, (len(skipped), len(committed))
    assert len(sink) == 18, "only the new (D2) batches added"
    print("ok  recovery: committed batches skipped, only unfinished work resumed")


# --------------------------------------------------------------------- MDVPL quarantine
def test_mdvpl_fail_quarantines_batch():
    eng = build_mock_collection_engine(faults=frozenset({"negative_price"}))
    r = eng.collect_batch("KTOS", D1)
    assert r.status == "QUARANTINED" and r.verdict == "FAIL"
    assert len(eng.sink) == 0, "no observations from a FAIL batch (no zero-fill)"
    assert eng.manifest.status("KTOS", D1) == BatchStatus.QUARANTINED
    print("ok  quarantine: MDVPL FAIL withholds the batch, stores nothing")


# --------------------------------------------------------------------- burn isolation
def test_burn_isolation_never_enters_store():
    burn = BurnedSlice(start_date=D1, end_date=D1, symbols=None)  # whole day burned
    eng = build_mock_collection_engine(burned_slice=burn)
    r = eng.collect_batch("KTOS", D1)
    assert r.stored_count == 0 and r.burned_count == 3 and r.accounted
    assert len(eng.sink) == 0, "CALIBRATION_ONLY rows must never enter the store"
    excl = eng.rejections.by_code(RejectionCode.BURNED_CALIBRATION_SLICE)
    assert len(excl) == 3 and all(e.is_exclusion for e in excl)
    assert_no_calibration_leak(eng.sink.rows())          # trivially holds: none present
    # a non-burned day on the same engine still collects normally
    r2 = eng.collect_batch("KTOS", D2)
    assert r2.stored_count == 3 and len(eng.sink) == 3
    assert filter_pipeline_dataset(eng.sink.rows()) == eng.sink.rows()
    print("ok  burn isolation: burned slice excluded; non-burned day unaffected")


# --------------------------------------------------------------------- append-only manifest
def test_manifest_is_append_only():
    eng = build_mock_collection_engine()
    eng.collect_batch("KTOS", D1)
    evs = eng.manifest.events("KTOS", D1)
    assert [e["event_type"] for e in evs] == [BatchStatus.STARTED, BatchStatus.COMMITTED]
    # re-running the same batch is skipped (committed) and writes NO new events
    n_before = eng.manifest.count()
    eng.collect_batch("KTOS", D1)
    assert eng.manifest.count() == n_before, "skip adds no events; nothing mutated in place"
    print("ok  manifest: append-only event log, status derived (no in-place updates)")


# --------------------------------------------------------------------- substrate untouched
def test_substrate_and_gate_untouched_after_collection():
    eng = build_mock_collection_engine()
    eng.collect([(s, d) for s in ("KTOS", "PTON") for d in (D1, D2)])
    checks = isuite.run_suite()
    assert len(checks) == 6 and all(c.passed for c in checks), isuite.render(checks)
    gate = isuite.ready_for_collection(
        lbl_v1_frozen=False, registries_built=True, pit_gate_operational=True,
        universe_ready=True, scanner_ready=True, checks=checks)
    assert gate["ready"] is False and gate["conditions"]["LBL_V1_FROZEN"] is False
    assert gate["integrity"] == "6/6 GREEN"
    print(f"ok  substrate untouched: integrity {gate['integrity']}, gate still FALSE")


if __name__ == "__main__":
    for _name, _fn in sorted(globals().items()):
        if _name.startswith("test_") and callable(_fn):
            _fn()
    print("\nALL COLLECTION TESTS PASSED")
