"""Tests for the Research Event Reconstruction Layer (read-only, factual)."""
import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _root)
sys.path.insert(0, os.path.join(_root, "src"))

import pandas as pd

from research.reconstruction import (
    ReconstructionEngine, Timeline, TimelineEvent, detectors as D, PRE, AT, POST,
)
from aurum_stocks.calibration.data_provider import SyntheticDataProvider

ET = "America/New_York"


def _mkdf(closes, highs=None, lows=None, vols=None, start="2025-03-03 09:30"):
    idx = pd.date_range(pd.Timestamp(start, tz=ET), periods=len(closes), freq="1min")
    return pd.DataFrame({
        "open": closes, "high": highs or closes, "low": lows or closes,
        "close": closes, "volume": vols or [100] * len(closes),
    }, index=idx)


def test_vwap_cross_detected():
    df = _mkdf([10.1, 10.1, 9.8, 9.8, 10.3])      # dips below VWAP, then crosses up
    evs = D.vwap_interactions(df)
    kinds = [k for _, k, _ in evs]
    assert "VWAP_CROSS_UP" in kinds
    print("vwap cross OK")


def test_volume_expansion_detected():
    df = _mkdf([10, 10, 10, 10], vols=[100, 100, 100, 400])
    evs = D.volume_expansion(df, k=3.0, lookback=2)
    assert any(k == "VOLUME_EXPANSION" and d["ratio"] >= 3.0 for _, k, d in evs)
    print("volume expansion OK")


def test_opening_range_break():
    df = _mkdf([10, 10.5, 11.5], highs=[10, 11, 12])
    evs = D.opening_range(df, or_minutes=1)
    kinds = [k for _, k, _ in evs]
    assert "OPENING_RANGE_SET" in kinds and "OR_BREAK_UP" in kinds
    print("opening range break OK")


def test_sweep_of_highs():
    # bars 0..1 set the prior high ~10; bar3 spikes to 11 then closes back below 10
    df = _mkdf([9.9, 9.9, 9.9, 9.5], highs=[10, 10, 10, 11])
    evs = D.sweeps(df, lookback=2)
    assert any(k == "SWEEP_OF_HIGHS" for _, k, _ in evs)
    print("sweep of highs OK")


def test_cluster_detected():
    base = pd.Timestamp("2025-03-03 10:00", tz=ET)
    raw = [(base + pd.Timedelta(minutes=m), "X", {}) for m in (0, 1, 2)]
    cl = D.clusters(raw, window_minutes=5, min_events=3)
    assert cl and cl[0][1] == "CLUSTER" and cl[0][2]["count"] == 3
    print("cluster OK")


def test_timeline_forbids_score_fields():
    try:
        TimelineEvent("2025-03-03T15:00:00+00:00", "X", AT, {"score": 1.0})
        assert False, "score must be rejected"
    except ValueError:
        pass
    for bad in ("signal", "bullish", "sentiment", "label", "prediction"):
        try:
            TimelineEvent("2025-03-03T15:00:00+00:00", "X", AT, {bad: 1})
            assert False
        except ValueError:
            pass
    print("timeline firewall (no score/signal/sentiment) OK")


def test_engine_end_to_end():
    eng = ReconstructionEngine(SyntheticDataProvider())
    tl = eng.reconstruct("MGNI", "2025-03-03T15:00:00+00:00",
                         anchor_ref={"news_record_id": "demo-1"},
                         pre_minutes=30, post_minutes=120)
    assert isinstance(tl, Timeline)
    # anchor present and AT phase
    assert any(e.kind == "NEWS" and e.phase == AT for e in tl.events)
    # chronological
    ts = [e.ts_utc for e in tl.events]
    assert ts == sorted(ts)
    # phases consistent with the anchor
    anchor = tl.anchor_ts_utc
    for e in tl.events:
        if e.phase == POST:
            assert e.ts_utc > anchor
        if e.phase == PRE:
            assert e.ts_utc < anchor
    # no forbidden keys anywhere (guaranteed structurally; assert anyway)
    forbidden = {"score", "signal", "sentiment", "bullish", "bearish", "label",
                 "prediction", "probability", "feature", "rank", "edge"}
    for e in tl.events:
        assert not (forbidden & set(e.detail))
    # serializable + renderable
    assert tl.to_json().startswith("{")
    assert "EVENT RECONSTRUCTION TIMELINE" in tl.render()
    print(f"engine end-to-end OK ({len(tl.events)} events; kinds={list(tl.kinds())})")


def test_engine_empty_bars_safe():
    class Empty:
        def get_minute_bars(self, symbol, date):
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    tl = ReconstructionEngine(Empty()).reconstruct("ZZZZ", "2025-03-03T15:00:00+00:00")
    assert len(tl.events) == 1 and tl.events[0].kind == "NEWS"   # only the anchor
    print("engine empty-bars safe OK")


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("\nALL RECONSTRUCTION LAYER TESTS PASSED")
