#!/usr/bin/env python3
"""
tests/test_registries.py — Priority #2 registry implementation + v3 locks.
Run: python tests/test_registries.py
"""
from __future__ import annotations

import datetime as dt
import os, sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "src"))

from aurum_stocks.registries import db
from aurum_stocks.registries.symbol_registry import SymbolRegistry, SymbolRegistryResolverImpl
from aurum_stocks.registries.regime_registry import RegimeRegistry, RegimeRegistryResolverImpl
from aurum_stocks.registries.setup_registry import SetupRegistry, SetupRegistryResolverImpl
from aurum_stocks.foundation import observation_builder as ob


def _ts(s):
    return pd.Timestamp(s, tz="America/New_York")


def _conn():
    c = db.connect(":memory:")
    db.init_schema(c)
    return c


# ---- symbol_registry: trigger policy + PIT + NO-FALLBACK + anti-survivorship ----
def test_symbol_versioning_trigger_and_pit():
    c = _conn()
    sr = SymbolRegistry(c)
    base = dict(symbol="MGNI", exchange="NASDAQ", sector="Tech",
                shares_outstanding=140e6, free_float=120e6, listing_status="LISTED",
                active_from=dt.date(2023, 1, 1))
    sr.upsert(valid_from=_ts("2025-01-02 09:30"), **base)
    # immaterial refresh (+0.2% shares) -> NO new version
    sr.upsert(valid_from=_ts("2025-02-01 09:30"), **{**base, "shares_outstanding": 140e6 * 1.002})
    # material dilution (+10% shares) -> new version
    sr.upsert(valid_from=_ts("2025-03-01 09:30"), **{**base, "shares_outstanding": 154e6})
    n = c.execute("SELECT COUNT(*) c FROM symbol_registry WHERE symbol='MGNI'").fetchone()["c"]
    assert n == 2, f"expected 2 versions (initial + material), got {n}"

    res = SymbolRegistryResolverImpl(c)
    v_feb = res.resolve("MGNI", _ts("2025-02-15 10:00"))
    v_apr = res.resolve("MGNI", _ts("2025-04-15 10:00"))
    assert v_feb == "MGNI#0001" and v_apr == "MGNI#0002", (v_feb, v_apr)
    print("ok  symbol trigger policy + PIT resolution")


def test_symbol_no_fallback():
    c = _conn()
    SymbolRegistry(c).upsert(symbol="CRDO", exchange="NASDAQ", sector="Tech",
                             shares_outstanding=100e6, free_float=80e6,
                             listing_status="LISTED", active_from=dt.date(2024, 1, 1),
                             valid_from=_ts("2025-01-02 09:30"))
    res = SymbolRegistryResolverImpl(c)
    # before the first valid_from -> NO FALLBACK, must raise
    try:
        res.resolve("CRDO", _ts("2024-06-01 10:00"))
        raise AssertionError("expected MissingSymbolVersion (no fallback)")
    except ob.MissingSymbolVersion:
        pass
    print("ok  symbol NO-FALLBACK raises MissingSymbolVersion")


def test_anti_survivorship_universe():
    c = _conn()
    sr = SymbolRegistry(c)
    # PTON: listed 2020, delisted 2025-06-01
    sr.upsert(symbol="PTON", exchange="NASDAQ", sector="Consumer",
              shares_outstanding=350e6, free_float=300e6, listing_status="LISTED",
              active_from=dt.date(2020, 9, 1), active_to=dt.date(2025, 6, 1),
              valid_from=_ts("2024-01-02 09:30"))
    # NEWCO: IPO 2025-07-01
    sr.upsert(symbol="NEWCO", exchange="NASDAQ", sector="Tech",
              shares_outstanding=50e6, free_float=20e6, listing_status="LISTED",
              active_from=dt.date(2025, 7, 1),
              valid_from=_ts("2025-07-01 09:30"))
    res = SymbolRegistryResolverImpl(c)
    uni = res.universe(_ts("2025-03-01 10:00"))
    assert "PTON" in uni, "later-delisted name must be present pre-delist (no survivorship)"
    assert "NEWCO" not in uni, "not-yet-IPO'd name must be absent"
    print("ok  anti-survivorship universe")


# ---- regime_registry: HOURLY PIT + NO-FALLBACK ---------------------------------
def test_regime_hourly_pit():
    c = _conn()
    rr = RegimeRegistry(c)
    for h, rs in [(9, "RISK_ON"), (10, "RISK_ON"), (11, "RISK_OFF")]:
        rr.add_snapshot(regime_ts=_ts(f"2025-01-02 {h:02d}:00"),
                        regime_spec_version="REGIME_V1", risk_state=rs)
    res = RegimeRegistryResolverImpl(c, "REGIME_V1", cadence="HOURLY")
    rid = res.resolve(_ts("2025-01-02 10:45"))   # should map to the 10:00 snapshot
    got = c.execute("SELECT risk_state, regime_ts FROM market_regime_registry WHERE regime_snapshot_id=?",
                    (rid,)).fetchone()
    assert got["risk_state"] == "RISK_ON" and "15:00" in got["regime_ts"], dict(got)
    # before first snapshot -> NO FALLBACK
    try:
        res.resolve(_ts("2025-01-02 08:00"))
        raise AssertionError("expected MissingRegimeSnapshot")
    except ob.MissingRegimeSnapshot:
        pass
    print("ok  regime HOURLY PIT + NO-FALLBACK")


# ---- setup_registry ------------------------------------------------------------
def test_setup_resolver():
    c = _conn()
    SetupRegistry(c).register(setup_id="ORB", version="1", detector_ref="detectors/orb.py@abc123")
    res = SetupRegistryResolverImpl(c)
    assert res.resolve("ORB") == "ORB@1"
    try:
        res.resolve("GAP_AND_GO")
        raise AssertionError("expected UnknownSetup")
    except ob.UnknownSetup:
        pass
    print("ok  setup resolver + UnknownSetup")


# ---- ObservationBuilder end-to-end with concrete registries + LOCK-2/3 ---------
class _Bars(ob.BarSource):
    def bars_as_of(self, symbol, signal_ts):
        idx = pd.date_range(end=signal_ts, periods=30, freq="1min")
        return pd.DataFrame({"close": range(30)}, index=idx), idx[-1]
class _Labels(ob.LabelSpecProvider):
    def current_label_spec_id(self): return "LBL_V1"
class _Feats(ob.FeatureComputer):
    def compute(self, symbol, signal_ts, bars): return {"n_bars": int(len(bars))}


def test_builder_with_registries_locks():
    from aurum_stocks.registries.universe_registry import UniverseRegistry, UniverseRegistryResolverImpl
    from aurum_stocks.registries.scanner_registry import ScannerRegistry, ScannerRegistryResolverImpl
    from aurum_stocks.foundation.dataset_roles import PartitionAssigner, CalibrationBurnLedger
    c = _conn()
    SymbolRegistry(c).upsert(symbol="KTOS", exchange="NASDAQ", sector="Defense",
                             shares_outstanding=130e6, free_float=120e6,
                             listing_status="LISTED", active_from=dt.date(2022, 1, 1),
                             valid_from=_ts("2025-01-02 09:30"))
    RegimeRegistry(c).add_snapshot(regime_ts=_ts("2025-03-03 09:00"),
                                   regime_spec_version="REGIME_V1", risk_state="NEUTRAL")
    SetupRegistry(c).register(setup_id="ORB", version="1", detector_ref="d/orb.py@a1")
    UniverseRegistry(c).add_universe(universe_id="SMALL_CAP_US", universe_spec_version="1",
                                     membership_rule={"price_band": [2, 20]},
                                     valid_from=_ts("2025-01-01 00:00"))
    ScannerRegistry(c).register(scanner_id="PREMARKET_GAP", scanner_spec_version="1",
                                candidate_generation_logic="scan/gap.py@a1")

    builder = ob.ObservationBuilder(
        SymbolRegistryResolverImpl(c), RegimeRegistryResolverImpl(c, "REGIME_V1"),
        SetupRegistryResolverImpl(c), _Labels(), _Bars(), _Feats(),
        PartitionAssigner(burn_ledger=CalibrationBurnLedger(), train_end=dt.date(2025, 12, 31)),
        UniverseRegistryResolverImpl(c), ScannerRegistryResolverImpl(c),
    )
    ev = ob.SignalEvent("KTOS", _ts("2025-03-03 10:00"), "ORB", "LONG",
                        scanner_id="PREMARKET_GAP", universe_id="SMALL_CAP_US",
                        scanner_score=0.88, scanner_rank=3,
                        candidate_batch_id="SCAN_2025_03_03_0930")
    row = builder.build(ev)
    row.assert_signed()
    # RH2: signature hash is deterministic over the SIX ids
    assert row.registry_signature_hash == ob.registry_signature(
        row.symbol_registry_id, row.regime_snapshot_id, row.setup_version,
        row.label_spec_id, row.universe_version_id, row.scanner_version_id)
    assert row.symbol_registry_id == "KTOS#0001" and row.setup_version == "ORB@1"
    assert row.universe_version_id == "SMALL_CAP_US@1" and row.scanner_version_id == "PREMARKET_GAP@1"
    assert row.scanner_rank == 3 and row.candidate_batch_id == "SCAN_2025_03_03_0930"
    print(f"ok  builder+registries signed row, 6-id sig={row.registry_signature_hash}")

    # LOCK-2: a signal before KTOS existed -> ObservationRejected(MISSING_SYMBOL_VERSION)
    ev_bad = ob.SignalEvent("KTOS", _ts("2021-06-01 10:00"), "ORB", "LONG",
                            scanner_id="PREMARKET_GAP", universe_id="SMALL_CAP_US")
    try:
        builder.build(ev_bad)
        raise AssertionError("expected ObservationRejected")
    except ob.ObservationRejected as r:
        assert r.reason == "MISSING_SYMBOL_VERSION", r.reason
    print("ok  builder LOCK-2 rejects with MISSING_SYMBOL_VERSION (no fallback)")


if __name__ == "__main__":
    test_symbol_versioning_trigger_and_pit()
    test_symbol_no_fallback()
    test_anti_survivorship_universe()
    test_regime_hourly_pit()
    test_setup_resolver()
    test_builder_with_registries_locks()
    print("\nALL REGISTRY TESTS PASSED")
