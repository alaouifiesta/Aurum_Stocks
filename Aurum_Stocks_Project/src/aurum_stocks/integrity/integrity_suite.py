"""
foundation/integrity_suite.py — the collection interlock (item 8).

Runs the mandatory integrity checks against a live registry set and computes
READY_FOR_COLLECTION. A single RED ⇒ READY_FOR_COLLECTION = FALSE. This gate
outranks any feature.

Checks:
  1. PIT lookup correctness        (symbol + regime resolvers)
  2. Burn isolation                (CALIBRATION_ONLY never enters a pipeline)
  3. Version resolution (signing)  (6 ids signed; data_as_of <= signal_ts)
  4. Anti-survivorship             (PIT universe membership)
  5. Rebuild determinism           (same inputs -> same signature; history stable)
  6. Completeness audit (GC-2)     (batch_size == observation_count)
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import pandas as pd

from ..foundation import dataset_roles as dr
from ..foundation import observation_builder as ob
from ..registries import db
from ..registries.symbol_registry import SymbolRegistry, SymbolRegistryResolverImpl
from ..registries.regime_registry import RegimeRegistry, RegimeRegistryResolverImpl
from ..registries.setup_registry import SetupRegistry, SetupRegistryResolverImpl
from ..registries.universe_registry import UniverseRegistry, UniverseRegistryResolverImpl
from ..registries.scanner_registry import ScannerRegistry, ScannerRegistryResolverImpl


def _ts(s):
    return pd.Timestamp(s, tz="America/New_York")


@dataclass
class Check:
    name: str
    passed: bool
    detail: str = ""


# --- minimal builder dependencies for the signing/determinism checks ----------
class _Bars(ob.BarSource):
    def bars_as_of(self, symbol, signal_ts):
        idx = pd.date_range(end=signal_ts, periods=20, freq="1min")
        return pd.DataFrame({"close": range(20)}, index=idx), idx[-1]
class _Labels(ob.LabelSpecProvider):
    def current_label_spec_id(self): return "LBL_V1"
class _Feats(ob.FeatureComputer):
    def compute(self, symbol, signal_ts, bars): return {"n": int(len(bars))}


def _seed(conn):
    SymbolRegistry(conn).upsert(symbol="KTOS", exchange="NASDAQ", sector="Defense",
        shares_outstanding=130e6, free_float=120e6, listing_status="LISTED",
        country="US", is_etf=False, is_adr=False, is_spac=False,
        active_from=dt.date(2022, 1, 1), valid_from=_ts("2025-01-02 09:30"))
    # later version (used by determinism/history-stability check)
    SymbolRegistry(conn).upsert(symbol="KTOS", exchange="NASDAQ", sector="Defense",
        shares_outstanding=160e6, free_float=120e6, listing_status="LISTED",
        country="US", is_etf=False, is_adr=False, is_spac=False,
        active_from=dt.date(2022, 1, 1), valid_from=_ts("2025-06-01 09:30"))
    # delisted-later + pre-IPO names for anti-survivorship
    SymbolRegistry(conn).upsert(symbol="PTON", exchange="NASDAQ", sector="Consumer",
        shares_outstanding=350e6, free_float=300e6, listing_status="LISTED",
        country="US", is_etf=False, is_adr=False, is_spac=False,
        active_from=dt.date(2020, 1, 1), active_to=dt.date(2025, 6, 1),
        valid_from=_ts("2024-01-02 09:30"))
    SymbolRegistry(conn).upsert(symbol="NEWCO", exchange="NASDAQ", sector="Tech",
        shares_outstanding=50e6, free_float=20e6, listing_status="LISTED",
        country="US", is_etf=False, is_adr=False, is_spac=False,
        active_from=dt.date(2025, 7, 1), valid_from=_ts("2025-07-01 09:30"))
    RegimeRegistry(conn).add_snapshot(regime_ts=_ts("2025-03-03 09:00"),
        regime_spec_version="REGIME_V1", risk_state="NEUTRAL")
    RegimeRegistry(conn).add_snapshot(regime_ts=_ts("2025-03-03 10:00"),
        regime_spec_version="REGIME_V1", risk_state="RISK_ON")
    SetupRegistry(conn).register(setup_id="ORB", version="1", detector_ref="d/orb.py@a1")
    UniverseRegistry(conn).add_universe(universe_id="SMALL_CAP_US", universe_spec_version="1",
        membership_rule={"exclude_is_etf": True, "exclude_is_adr": True,
                         "exclude_is_spac": True}, valid_from=_ts("2024-01-01 00:00"))
    ScannerRegistry(conn).register(scanner_id="PREMARKET_GAP", scanner_spec_version="1",
        candidate_generation_logic="scan/gap.py@a1")


def _builder(conn):
    pa = dr.PartitionAssigner(burn_ledger=dr.CalibrationBurnLedger(),
                              train_end=dt.date(2025, 12, 31))
    return ob.ObservationBuilder(
        SymbolRegistryResolverImpl(conn), RegimeRegistryResolverImpl(conn, "REGIME_V1"),
        SetupRegistryResolverImpl(conn), _Labels(), _Bars(), _Feats(), pa,
        UniverseRegistryResolverImpl(conn), ScannerRegistryResolverImpl(conn))


def _event(ts, batch="SCAN_B1", rank=1):
    return ob.SignalEvent("KTOS", ts, "ORB", "LONG", scanner_id="PREMARKET_GAP",
                          universe_id="SMALL_CAP_US", scanner_score=0.9, scanner_rank=rank,
                          candidate_batch_id=batch)


def check_pit_lookup(conn) -> Check:
    res = SymbolRegistryResolverImpl(conn)
    v1 = res.resolve("KTOS", _ts("2025-03-01 10:00"))    # before 2nd version
    v2 = res.resolve("KTOS", _ts("2025-07-01 10:00"))    # after 2nd version
    ok = v1 == "KTOS#0001" and v2 == "KTOS#0002"
    # never returns a future-effective version
    try:
        res.resolve("KTOS", _ts("2021-01-01 10:00"))
        future_ok = False
    except ob.MissingSymbolVersion:
        future_ok = True
    return Check("1_pit_lookup", ok and future_ok, f"{v1},{v2},no_future={future_ok}")


def check_burn_isolation() -> Check:
    ledger = dr.CalibrationBurnLedger()
    ledger.burn(dr.BurnedSlice(dt.date(2025, 1, 5), dt.date(2025, 1, 9),
                               symbols=frozenset({"KTOS"})))
    pa = dr.PartitionAssigner(burn_ledger=ledger, train_end=dt.date(2025, 12, 31))
    burned = pa.assign("KTOS", _ts("2025-01-06 10:00"))
    clean = pa.assign("KTOS", _ts("2025-03-06 10:00"))
    rows = [{"observation_id": "a", "dataset_role": dr.DatasetRole.CALIBRATION_ONLY}]
    leaked = False
    try:
        dr.assert_no_calibration_leak(rows)
    except AssertionError:
        leaked = True
    ok = (burned is dr.DatasetRole.CALIBRATION_ONLY
          and clean in dr.PIPELINE_ROLES and leaked)
    return Check("2_burn_isolation", ok, f"burned={burned.value},leak_caught={leaked}")


def check_version_signing(conn) -> Check:
    row = _builder(conn).build(_event(_ts("2025-03-03 10:00")))
    try:
        row.assert_signed()
        signed = True
    except AssertionError:
        signed = False
    six = all([row.symbol_registry_id, row.regime_snapshot_id, row.setup_version,
               row.label_spec_id, row.universe_version_id, row.scanner_version_id])
    pit = row.data_as_of_ts <= row.signal_ts_utc
    return Check("3_version_signing", signed and six and pit,
                 f"sig={row.registry_signature_hash}")


def check_anti_survivorship(conn) -> Check:
    res = UniverseRegistryResolverImpl(conn)
    uni = res.members("SMALL_CAP_US", _ts("2025-03-01 10:00"), conn)
    ok = "PTON" in uni and "NEWCO" not in uni
    return Check("4_anti_survivorship", ok, f"PTON_in={'PTON' in uni},NEWCO_out={'NEWCO' not in uni}")


def check_rebuild_determinism(conn) -> Check:
    b = _builder(conn)
    r1 = b.build(_event(_ts("2025-03-03 10:00")))
    r2 = b.build(_event(_ts("2025-03-03 10:00")))
    same_sig = r1.registry_signature_hash == r2.registry_signature_hash
    # history stability: the 2025-03 row still resolves to the FIRST symbol version
    # even though a later (2025-06) version exists.
    stable = r1.symbol_registry_id == "KTOS#0001"
    return Check("5_rebuild_determinism", same_sig and stable,
                 f"same_sig={same_sig},history_stable={stable}")


def check_completeness_audit(conn) -> Check:
    """GC-2: every candidate in a batch yields an observation."""
    b = _builder(conn)
    batch = "SCAN_2025_03_03_0930"
    candidates = [_event(_ts("2025-03-03 10:00"), batch=batch, rank=i) for i in range(1, 6)]
    observed = [b.build(c) for c in candidates]
    audit_ok = len(observed) == len(candidates) and \
        all(o.candidate_batch_id == batch for o in observed)
    return Check("6_completeness_audit", audit_ok,
                 f"candidates={len(candidates)},observed={len(observed)}")


def run_suite() -> list[Check]:
    conn = db.connect(":memory:")
    db.init_schema(conn)
    _seed(conn)
    return [
        check_pit_lookup(conn),
        check_burn_isolation(),
        check_version_signing(conn),
        check_anti_survivorship(conn),
        check_rebuild_determinism(conn),
        check_completeness_audit(conn),
    ]


def render(checks: list[Check]) -> str:
    lines = ["REGISTRY INTEGRITY SUITE", "=" * 40]
    for c in checks:
        lines.append(f"[{'GREEN' if c.passed else 'RED  '}] {c.name}  {c.detail}")
    n_green = sum(c.passed for c in checks)
    lines += ["-" * 40, f"{n_green}/{len(checks)} GREEN"]
    return "\n".join(lines)


def ready_for_collection(*, lbl_v1_frozen: bool, registries_built: bool,
                         pit_gate_operational: bool, universe_ready: bool,
                         scanner_ready: bool, checks: list[Check] | None = None) -> dict:
    checks = checks if checks is not None else run_suite()
    integrity_green = all(c.passed for c in checks)
    conditions = {
        "LBL_V1_FROZEN": lbl_v1_frozen,
        "REGISTRIES_BUILT": registries_built,
        "INTEGRITY_SUITE_GREEN": integrity_green,
        "PIT_GATE_OPERATIONAL": pit_gate_operational,
        "UNIVERSE_REGISTRY_READY": universe_ready,
        "SCANNER_REGISTRY_READY": scanner_ready,
    }
    return {"ready": all(conditions.values()), "conditions": conditions,
            "integrity": f"{sum(c.passed for c in checks)}/{len(checks)} GREEN"}
