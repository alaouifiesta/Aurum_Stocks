#!/usr/bin/env python3
"""
tests/test_feature_gate_integrity.py — items 6,7,8.
Run: python tests/test_feature_gate_integrity.py
"""
from __future__ import annotations

import datetime as dt
import os, sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "src"))

from aurum_stocks.foundation import pit_harness as ph
from aurum_stocks.foundation import pit_gate as pg
from aurum_stocks.foundation import feature_registry as fr
from aurum_stocks.integrity import integrity_suite as isuite
from aurum_stocks.calibration.data_provider import SyntheticDataProvider


def _cases(n_positions=3):
    bars = SyntheticDataProvider().get_minute_bars("MGNI", dt.date(2025, 1, 2))
    return [ph.PITCase(bars=bars, signal_ts=bars.index[i]) for i in (120, 200, 300)][:n_positions]


# ---- item 7: PIT gate trichotomy ----------------------------------------------
def test_pit_gate_pass_fail_unknown():
    cases = _cases()
    p = pg.run_gate("trailing_return", "1", ph.fixture_trailing_return, cases, lookback_window=6)
    assert p.verdict is pg.Verdict.PASS, p

    f = pg.run_gate("peek_next_bar", "1", ph.fixture_peek_next_bar, cases)
    assert f.verdict is pg.Verdict.FAIL and f.remediation == "NEW_VERSION", f

    # UNKNOWN: only one position and no future bars (truncate so nothing follows signal)
    bars = SyntheticDataProvider().get_minute_bars("MGNI", dt.date(2025, 1, 2))
    last = bars.index[-1]
    u = pg.run_gate("trailing_return", "1", ph.fixture_trailing_return,
                    [ph.PITCase(bars=bars.loc[bars.index <= last], signal_ts=last)])
    assert u.verdict is pg.Verdict.UNKNOWN and u.remediation, u
    print("ok  item7  PIT gate PASS / FAIL / UNKNOWN")


# ---- item 6: feature registry admission (no anonymous features) ----------------
def test_feature_registry_admission():
    ledger = pg.PITGateLedger()
    cases = _cases()
    good = ledger.record(pg.run_gate("rvol", "1", ph.fixture_trailing_return, cases, 6))
    bad = ledger.record(pg.run_gate("leak", "1", ph.fixture_peek_next_bar, cases))
    reg = fr.FeatureRegistry(ledger)

    # anonymous (missing rationale) -> rejected
    try:
        reg.admit(fr.FeatureDefinition("rvol", "RVOL", "1", "f/rvol.py@a1", ("vol",), 6,
                                       good, "", fr.FeatureClass.LIQUIDITY_STATE))
        raise AssertionError("expected AdmissionRejected (missing rationale)")
    except fr.AdmissionRejected as e:
        assert "economic_rationale" in e.reason

    # FAIL pit_proof -> rejected (UNKNOWN==REJECTED too)
    try:
        reg.admit(fr.FeatureDefinition("leak", "Leak", "1", "f/leak.py@a1", ("x",), 0,
                                       bad, "because", fr.FeatureClass.PRICE_STATE))
        raise AssertionError("expected AdmissionRejected (pit FAIL)")
    except fr.AdmissionRejected as e:
        assert "only PASS admits" in e.reason

    # EXECUTION_STATE cannot be a pre-signal feature
    try:
        reg.admit(fr.FeatureDefinition("slip", "Slippage", "1", "f/s.py@a1", ("x",), 0,
                                       good, "because", fr.FeatureClass.EXECUTION_STATE))
        raise AssertionError("expected AdmissionRejected (EXECUTION_STATE)")
    except fr.AdmissionRejected as e:
        assert "OUTCOME-MODELED" in e.reason

    # valid admission -> OBSERVATION
    d = reg.admit(fr.FeatureDefinition("rvol", "RVOL", "1", "f/rvol.py@a1", ("vol",), 6,
                                       good, "relative volume vs 20d baseline",
                                       fr.FeatureClass.LIQUIDITY_STATE))
    assert reg.status("rvol", "1") is fr.FeatureStatus.OBSERVATION
    # REJECTED is terminal
    reg.transition("rvol", "1", fr.FeatureStatus.REJECTED)
    try:
        reg.transition("rvol", "1", fr.FeatureStatus.TESTING)
        raise AssertionError("REJECTED must be terminal")
    except fr.AdmissionRejected:
        pass
    print("ok  item6  feature registry admission + lifecycle")


# ---- item 8: integrity suite 5/5(+audit) + READY_FOR_COLLECTION ----------------
def test_integrity_suite_and_ready():
    checks = isuite.run_suite()
    assert all(c.passed for c in checks), isuite.render(checks)
    assert len(checks) == 6
    # not ready until LBL_V1 frozen
    s0 = isuite.ready_for_collection(lbl_v1_frozen=False, registries_built=True,
                                     pit_gate_operational=True, universe_ready=True,
                                     scanner_ready=True, checks=checks)
    assert s0["ready"] is False and s0["conditions"]["LBL_V1_FROZEN"] is False
    # all conditions met -> ready
    s1 = isuite.ready_for_collection(lbl_v1_frozen=True, registries_built=True,
                                     pit_gate_operational=True, universe_ready=True,
                                     scanner_ready=True, checks=checks)
    assert s1["ready"] is True, s1
    print(f"ok  item8  integrity {s1['integrity']} + READY_FOR_COLLECTION interlock")


if __name__ == "__main__":
    test_pit_gate_pass_fail_unknown()
    test_feature_registry_admission()
    test_integrity_suite_and_ready()
    print("\nALL FEATURE-GATE / INTEGRITY TESTS PASSED")
