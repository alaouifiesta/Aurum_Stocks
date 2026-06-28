"""Tests for the Market Data Validation & Provenance Layer (read-only, pass-through)."""
import os
import sys
import datetime as dt

_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _root)
sys.path.insert(0, os.path.join(_root, "src"))

from pipeline.mdvpl import (
    MarketDataSource, MockMarketDataSource, MarketDataValidator, ProvenanceLog, Status,
)

DATE = dt.date(2025, 3, 3)   # Monday


def _check(result, name):
    return next(c for c in result.report.checks if c.name == name)


def test_clean_batch_passes():
    v = MarketDataValidator(ProvenanceLog())
    res = v.validate(MockMarketDataSource(), "ABCD", DATE, streams=("bars", "quotes", "news"))
    assert res.report.verdict == Status.PASS
    assert _check(res, "consolidation").status == Status.PASS
    assert _check(res, "sane_bars").status == Status.PASS
    assert _check(res, "sane_quotes").status == Status.PASS
    print("clean batch PASS OK")


def test_pass_through_does_not_modify_data():
    src = MockMarketDataSource()
    expected = src.minute_bars("ABCD", DATE)
    res = MarketDataValidator().validate(src, "ABCD", DATE, streams=("bars",))
    # the validator returns exactly the source rows, unchanged
    assert res.data["bars"] == expected
    print("pass-through (no modification) OK")


def test_faults_are_detected():
    cases = {
        "out_of_order": ("bars_chronology", Status.FAIL),
        "duplicate": ("bars_duplication", Status.FAIL),
        "bad_ohlc": ("sane_bars", Status.FAIL),
        "negative_price": ("sane_bars", Status.FAIL),
        "gap": ("coverage", Status.FAIL),               # 5-min hole -> FAIL
        "crossed_spread": ("sane_quotes", Status.FAIL),
    }
    for fault, (check_name, expected) in cases.items():
        src = MockMarketDataSource(faults={fault})
        res = MarketDataValidator().validate(src, "ABCD", DATE, streams=("bars", "quotes"))
        assert _check(res, check_name).status == expected, f"{fault}->{check_name}"
        assert res.report.verdict == Status.FAIL
    print("fault detection OK")


def test_single_venue_rejected():
    res = MarketDataValidator().validate(
        MockMarketDataSource(consolidated=False), "ABCD", DATE, streams=("bars",))
    assert _check(res, "consolidation").status == Status.FAIL
    assert res.report.verdict == Status.FAIL
    assert res.provenance.feed_type == "SINGLE_VENUE"
    print("single-venue (non-SIP) rejected OK")


def test_missing_news_available_ts():
    res = MarketDataValidator().validate(
        MockMarketDataSource(faults={"missing_news_available"}), "ABCD", DATE,
        streams=("news",))
    assert _check(res, "news_provenance").status == Status.FAIL
    print("news provenance check OK")


def test_registry_checks_skip_without_feed():
    res = MarketDataValidator().validate(MockMarketDataSource(), "ABCD", DATE, streams=("bars",))
    assert _check(res, "corporate_action_sanity").status == Status.SKIP
    assert _check(res, "halt_consistency").status == Status.SKIP
    print("registry-dependent checks SKIP honestly OK")


def test_provenance_append_only():
    log = ProvenanceLog()
    v = MarketDataValidator(log)
    r1 = v.validate(MockMarketDataSource(), "ABCD", DATE, streams=("bars",))
    r2 = v.validate(MockMarketDataSource(), "ABCD", DATE, streams=("bars",))  # re-fetch
    assert log.count() == 2                                  # append-only: both kept
    # same content -> same hash, two provenance rows linked by hash
    assert r1.provenance.content_hash == r2.provenance.content_hash
    assert len(log.by_hash(r1.provenance.content_hash)) == 2
    assert r1.provenance.provenance_id != r2.provenance.provenance_id
    print("provenance append-only OK")


def test_provider_agnostic_interface():
    # a second adapter with a different vendor flows through the same port
    class OtherMock(MockMarketDataSource):
        vendor = "OTHER"
        adapter_version = "other-9"
    res = MarketDataValidator().validate(OtherMock(), "ABCD", DATE, streams=("bars",))
    assert res.provenance.vendor == "OTHER" and res.provenance.adapter_version == "other-9"
    assert isinstance(OtherMock(), MarketDataSource)
    print("provider-agnostic interface OK")


def test_no_features_or_scores_emitted():
    res = MarketDataValidator().validate(MockMarketDataSource(), "ABCD", DATE,
                                         streams=("bars", "quotes"))
    forbidden = {"score", "signal", "sentiment", "bullish", "bearish", "label",
                 "prediction", "feature", "rank", "edge"}
    for c in res.report.checks:
        assert not (forbidden & set(c.detail))
    d = res.report.to_dict()
    assert "verdict" in d and "checks" in d        # only quality facts, no features
    print("no features/scores emitted OK")


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("\nALL MDVPL TESTS PASSED")
