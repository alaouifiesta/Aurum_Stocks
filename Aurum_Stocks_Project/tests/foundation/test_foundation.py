#!/usr/bin/env python3
"""
tests/test_foundation.py — R1-R4 contracts.
Run: python tests/test_foundation.py
"""
from __future__ import annotations

import datetime as dt
import os, re, sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "src"))

from aurum_stocks.foundation import label_spec as ls
from aurum_stocks.foundation import dataset_roles as dr
from aurum_stocks.foundation import pit_harness as ph
from aurum_stocks.foundation import observation_builder as ob
from aurum_stocks.calibration.data_provider import SyntheticDataProvider


# ---- R2: label spec versioned + immutable -------------------------------------
def test_label_spec_versioned_immutable():
    reg = ls.LabelSpecRegistry()
    v1 = ls.create_label_spec("LBL_V1", k=1.5, horizon_min=90,
                              time_encoding=ls.TimeEncoding.SIGN_RETURN,
                              calibration_ref="CAL_2026_001")
    reg.register(v1)
    # frozen dataclass: cannot mutate
    try:
        v1.k = 2.0
        raise AssertionError("LabelSpec must be immutable")
    except Exception:
        pass
    # re-registering LBL_V1 with different content is rejected
    v1b = ls.create_label_spec("LBL_V1", k=2.0, horizon_min=90,
                               time_encoding=ls.TimeEncoding.SIGN_RETURN)
    try:
        reg.register(v1b)
        raise AssertionError("must reject overwriting LBL_V1")
    except ValueError:
        pass
    # a different choice becomes a new version
    v2 = ls.create_label_spec("LBL_V2", k=2.0, horizon_min=120,
                              time_encoding=ls.TimeEncoding.TERNARY_ZERO)
    reg.register(v2)
    assert reg.ids() == ["LBL_V1", "LBL_V2"]
    print("ok  R2  label_spec versioned + immutable")


# ---- R1: calibration burn ------------------------------------------------------
def test_calibration_burn_guard():
    ledger = dr.CalibrationBurnLedger()
    ledger.burn(dr.BurnedSlice(start_date=dt.date(2026, 1, 5), end_date=dt.date(2026, 1, 9),
                               symbols=frozenset({"MGNI", "CRDO"})))
    pa = dr.PartitionAssigner(burn_ledger=ledger,
                              train_end=dt.date(2026, 6, 1), val_end=dt.date(2026, 6, 20),
                              oos_end=dt.date(2026, 6, 30))
    burned_ts = pd.Timestamp("2026-01-06 10:00", tz="America/New_York")
    clean_ts = pd.Timestamp("2026-03-02 10:00", tz="America/New_York")
    assert pa.assign("MGNI", burned_ts) == dr.DatasetRole.CALIBRATION_ONLY
    assert pa.assign("MGNI", clean_ts) in dr.PIPELINE_ROLES
    # leak guard
    rows = [{"observation_id": "a", "dataset_role": dr.DatasetRole.CALIBRATION_ONLY},
            {"observation_id": "b", "dataset_role": dr.DatasetRole.TRAIN}]
    try:
        dr.assert_no_calibration_leak(rows)
        raise AssertionError("leak guard should have fired")
    except AssertionError as e:
        assert "leaked" in str(e)
    assert [r["observation_id"] for r in dr.filter_pipeline_dataset(rows)] == ["b"]
    print("ok  R1  calibration burn guard excludes pilot")


# ---- R3: PIT harness catches lookahead ----------------------------------------
def test_pit_harness_catches_leak():
    bars = SyntheticDataProvider().get_minute_bars("MGNI", dt.date(2025, 1, 2))
    cases = [ph.PITCase(bars=bars, signal_ts=bars.index[150]),
             ph.PITCase(bars=bars, signal_ts=bars.index[300])]
    results = ph.validate_registry(
        {"trailing_return": ph.fixture_trailing_return,
         "peek_next_bar": ph.fixture_peek_next_bar}, cases)
    assert results["trailing_return"].passed, "PIT-safe feature must PASS"
    assert not results["peek_next_bar"].passed, "leaky feature must PIT_FAIL"
    print("ok  R3  PIT harness PASS safe / FAIL leaky")


# ---- R4: ObservationBuilder signs + is setup-agnostic --------------------------
class _StubSymbols(ob.SymbolRegistryResolver):
    def resolve(self, symbol, as_of): return f"{symbol}@symrev1"
class _StubRegime(ob.RegimeRegistryResolver):
    def resolve(self, as_of): return "REGIME_SNAP_001"
class _StubSetups(ob.SetupRegistryResolver):
    def resolve(self, setup_type): return f"{setup_type}@v1"
class _StubLabels(ob.LabelSpecProvider):
    def current_label_spec_id(self): return "LBL_V1"
class _StubUniverse(ob.UniverseRegistryResolver):
    def resolve(self, universe_id, as_of): return f"{universe_id}@1"
class _StubScanner(ob.ScannerRegistryResolver):
    def resolve(self, scanner_id): return f"{scanner_id}@1"
class _StubBars(ob.BarSource):
    def __init__(self, bars): self._bars = bars
    def bars_as_of(self, symbol, signal_ts):
        past = self._bars.loc[self._bars.index <= signal_ts]
        return past, past.index[-1]   # data_as_of = last past bar (<= signal_ts)
class _StubFeatures(ob.FeatureComputer):
    def compute(self, symbol, signal_ts, bars):
        return {"trailing_return": ph.fixture_trailing_return(bars, signal_ts)}


def test_observation_builder_contract():
    bars = SyntheticDataProvider().get_minute_bars("CRDO", dt.date(2025, 1, 3))
    ledger = dr.CalibrationBurnLedger()
    pa = dr.PartitionAssigner(burn_ledger=ledger, train_end=dt.date(2025, 12, 31))
    builder = ob.ObservationBuilder(
        _StubSymbols(), _StubRegime(), _StubSetups(), _StubLabels(),
        _StubBars(bars), _StubFeatures(), pa, _StubUniverse(), _StubScanner())
    ev = ob.SignalEvent(symbol="CRDO", signal_ts=bars.index[200],
                        setup_type="ORB", direction="LONG",
                        scanner_id="PREMARKET_GAP", universe_id="SMALL_CAP_US",
                        scanner_score=0.91, scanner_rank=2,
                        candidate_batch_id="SCAN_2025_01_03_0930")
    row = builder.build(ev)
    row.assert_signed()
    assert row.symbol_registry_id and row.regime_snapshot_id and row.setup_version \
        and row.label_spec_id and row.universe_version_id and row.scanner_version_id, \
        "row must be fully signed (6 ids)"
    assert row.data_as_of_ts <= row.signal_ts_utc
    assert "trailing_return" in row.features
    assert row.scanner_rank == 2 and row.candidate_batch_id == "SCAN_2025_01_03_0930"
    # a DIFFERENT setup must flow through the SAME generic path (no branching)
    ev2 = ob.SignalEvent(symbol="CRDO", signal_ts=bars.index[200],
                         setup_type="GAP_AND_GO", direction="LONG",
                         scanner_id="PREMARKET_GAP", universe_id="SMALL_CAP_US")
    row2 = builder.build(ev2)
    assert row2.setup_type == "GAP_AND_GO" and row2.setup_version == "GAP_AND_GO@v1"
    # GC-7: a SHORT direction is a HARD FAIL
    try:
        builder.build(ob.SignalEvent("CRDO", bars.index[200], "ORB", "SHORT",
                                     scanner_id="PREMARKET_GAP", universe_id="SMALL_CAP_US"))
        raise AssertionError("expected LongOnlyViolation")
    except ob.LongOnlyViolation:
        pass
    print("ok  R4  ObservationBuilder produces fully-signed rows + GC-7 hard fail")


def test_observation_builder_is_setup_agnostic():
    """Source-scan guard: the builder must contain no per-setup branching."""
    src = open(ob.__file__).read()
    banned = [r"if\s+setup", r"elif\s+setup", r"setup_type\s*==", r"match\s+setup"]
    hits = [p for p in banned if re.search(p, src)]
    assert not hits, f"setup branching found in observation_builder: {hits}"
    print("ok  R4  observation_builder is setup-agnostic (no if setup ==)")


if __name__ == "__main__":
    test_label_spec_versioned_immutable()
    test_calibration_burn_guard()
    test_pit_harness_catches_leak()
    test_observation_builder_contract()
    test_observation_builder_is_setup_agnostic()
    print("\nALL FOUNDATION TESTS PASSED")
