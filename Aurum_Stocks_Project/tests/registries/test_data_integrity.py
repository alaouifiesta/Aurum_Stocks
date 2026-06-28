#!/usr/bin/env python3
"""
tests/test_data_integrity.py — new Priority-#2 components.
Run: python tests/test_data_integrity.py
"""
from __future__ import annotations

import datetime as dt
import os, sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "src"))

from aurum_stocks.registries import db
from aurum_stocks.registries.data_quality_registry import DataQualityRegistry, DataQualityResolver
from aurum_stocks.registries.news_registry import NewsRegistry, NewsResolver
from aurum_stocks.registries.halt_registry import HaltRegistry, HaltResolver
from aurum_stocks.registries.microstructure_registry import MicrostructureRegistry
from aurum_stocks.registries.research_registry import ResearchRegistry, ResearchRegistryError
from aurum_stocks.registries.label_registry import LabelRegistry, LabelRegistryError
from aurum_stocks.providers import providers as P
from aurum_stocks.foundation import feature_registry as fr


def _ts(s): return pd.Timestamp(s, tz="America/New_York")
def _conn():
    c = db.connect(":memory:"); db.init_schema(c); return c
DAY = dt.date(2025, 3, 3)


def test_data_quality_asof_vs_retrospective():
    c = _conn(); dq = DataQualityRegistry(c); res = DataQualityResolver(c)
    prov = P.MockDataQualityProvider()
    # AS_OF: clean at 10:00, outage flagged at 10:30
    dq.record_as_of(symbol="KTOS", as_of=_ts("2025-03-03 10:00"), **{k: v for k, v in
                    prov.assess_as_of("KTOS", _ts("2025-03-03 10:00")).items()})
    dq.record_as_of(symbol="KTOS", as_of=_ts("2025-03-03 10:30"), feed_outage_active=True)
    # PIT: at 10:15 we see the 10:00 snapshot (clean); at 10:45 we see the outage
    assert res.is_quarantined_as_of("KTOS", _ts("2025-03-03 10:15")) is False
    assert res.is_quarantined_as_of("KTOS", _ts("2025-03-03 10:45")) is True
    # RETROSPECTIVE present but separate
    dq.record_retrospective(symbol="KTOS", session_date=DAY,
                            **prov.assess_session("KTOS", DAY))
    assert res.retrospective("KTOS", DAY)["missing_bars_pct"] == 0.4
    print("ok  data_quality AS_OF (PIT) vs RETROSPECTIVE separation")


def test_news_pit_available_ts():
    c = _conn(); reg = NewsRegistry(c); res = NewsResolver(c)
    for item in P.MockNewsProvider().fetch("KTOS", DAY):
        reg.add(symbol="KTOS", news_available_ts=item["available_ts"],
                news_publish_ts=item["publish_ts"], source=item["source"],
                vendor=item["vendor"], headline_hash=item["headline_hash"])
    # published 09:31, available 09:34 -> NOT actionable at 09:32, actionable at 09:35
    assert res.available_as_of("KTOS", _ts("2025-03-03 09:32")) == []
    got = res.available_as_of("KTOS", _ts("2025-03-03 09:35"))
    assert len(got) == 1 and abs(got[0]["publication_delay_sec"] - 180) < 1
    print("ok  news PIT keyed on news_available_ts (not publish_ts)")


def test_halt_asof():
    c = _conn(); reg = HaltRegistry(c); res = HaltResolver(c)
    for h in P.MockHaltProvider().fetch("KTOS", DAY):
        reg.add_halt(symbol="KTOS", **h)
    assert res.is_halted_at("KTOS", _ts("2025-03-03 10:02")) is True   # mid-halt
    assert res.is_halted_at("KTOS", _ts("2025-03-03 10:06")) is False  # resumed
    assert res.is_halted_at("KTOS", _ts("2025-03-03 09:59")) is False  # before
    assert len(res.episodes("KTOS")) == 1
    print("ok  halt as-of PIT status + episodes")


def test_microstructure_reserved():
    c = _conn(); m = MicrostructureRegistry(c)
    m.reserve(microstructure_version_id="L2_DEPTH@reserved", data_type="L2_DEPTH",
              vendor="TBD", resolution="tick")
    assert len(m.list_reserved()) == 1
    try:
        m.reserve(microstructure_version_id="x", data_type="NOT_A_TYPE")
        raise AssertionError("bad data_type must raise")
    except ValueError:
        pass
    print("ok  microstructure registry reserved + type guard")


def test_research_preregistration():
    c = _conn(); rr = ResearchRegistry(c)
    # pre-registration requires predicted_effect + frozen_test_spec
    try:
        rr.register_hypothesis(hypothesis_id="H#1", statement="RVOL helps", predicted_effect="",
                               frozen_test_spec={})
        raise AssertionError("must require predicted_effect + test spec")
    except ResearchRegistryError:
        pass
    rr.register_hypothesis(hypothesis_id="H#1", statement="High RVOL improves balance",
                           predicted_effect="positive", frozen_test_spec={"test": "LRT", "q": 0.10},
                           features_used=["rvol@1"])
    rr.transition("H#1", "TESTING"); rr.transition("H#1", "OOS_FAIL")
    rr.transition("H#1", "REJECTED")
    # REJECTED is terminal; re-test needs a NEW id
    try:
        rr.transition("H#1", "TESTING")
        raise AssertionError("REJECTED must be terminal")
    except ResearchRegistryError:
        pass
    rr.log_experiment(hypothesis_id="H#1", feature="rvol@1", dataset="OOS", sample_size=400,
                      result="fail")
    assert rr.family_size() == 1
    print("ok  research pre-registration + append-only ledger + terminal REJECTED")


def test_label_registry_write_once():
    c = _conn(); lr = LabelRegistry(c)
    content = {"label_spec_id": "LBL_TEST", "k": 1.25, "H_minutes": 30,
               "time_encoding": "TERNARY", "tie_break": "STOP_FIRST"}
    out = lr.freeze(label_spec_id="LBL_TEST", spec_version="1", content=content,
                    calibration_report_hash="crh", rubric_hash="rh")
    assert out["label_spec_hash"] and lr.exists("LBL_TEST")
    # write-once: cannot re-freeze the same id
    try:
        lr.freeze(label_spec_id="LBL_TEST", spec_version="1", content=content,
                  calibration_report_hash="crh", rubric_hash="rh")
        raise AssertionError("re-freeze must fail (immutable)")
    except LabelRegistryError:
        pass
    print("ok  label_registry write-once + content hash  (no LBL_V1 created)")


def test_liquidity_shock_class():
    assert fr.FeatureClass.LIQUIDITY_SHOCK.value == "LIQUIDITY_SHOCK"
    assert fr.FeatureClass.LIQUIDITY_SHOCK is not fr.FeatureClass.LIQUIDITY_STATE
    print("ok  LIQUIDITY_SHOCK feature class present (distinct from LIQUIDITY_STATE)")


if __name__ == "__main__":
    test_data_quality_asof_vs_retrospective()
    test_news_pit_available_ts()
    test_halt_asof()
    test_microstructure_reserved()
    test_research_preregistration()
    test_label_registry_write_once()
    test_liquidity_shock_class()
    print("\nALL DATA-INTEGRITY TESTS PASSED")
