#!/usr/bin/env python3
"""
tests/test_barriers.py — sanity checks for the frozen TB rules.
Run: python tests/test_barriers.py   (plain asserts, no pytest needed)
"""
from __future__ import annotations

import datetime as dt
import sys, os

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "src"))
from aurum_stocks.calibration import config, barriers, grid
from aurum_stocks.calibration.data_provider import SyntheticDataProvider


def _mk_bars(prices_hlc, start="2025-01-02 09:30", tz=config.TZ):
    """prices_hlc: list of (high, low, close). 1-min bars."""
    idx = pd.date_range(pd.Timestamp(start, tz=tz), periods=len(prices_hlc), freq="1min")
    df = pd.DataFrame(prices_hlc, columns=["high", "low", "close"], index=idx)
    df["open"] = df["close"].shift(1).fillna(df["close"])
    df["volume"] = 1000
    df["bid"] = df["close"] - 0.01
    df["ask"] = df["close"] + 0.01
    df.index.name = "ts"
    return df[["open", "high", "low", "close", "volume", "bid", "ask"]]


def test_tie_break_stop_first():
    """A bar whose range spans BOTH barriers must resolve to STOP (frozen tie-break)."""
    # Force a known ATR by hand via a flat warmup then a wide bar.
    env = barriers.Envelope(
        ref=10.0, atr=1.0, spread=0.02,
        minutes=np.array([1.0]),
        up_max=np.array([2.0]),   # +2 ATR reached
        dn_min=np.array([-2.0]),  # -2 ATR reached, same bar
        close_ret=np.array([0.0]),
    )
    out = barriers.resolve(env, k=1.0, h_min=15)
    assert out.barrier == "STOP", f"expected STOP on tie, got {out.barrier}"
    print("ok  tie_break_stop_first")


def test_profit_before_stop():
    env = barriers.Envelope(
        ref=10.0, atr=1.0, spread=0.02,
        minutes=np.array([1.0, 2.0, 3.0]),
        up_max=np.array([0.5, 1.0, 1.0]),   # profit (k=1) first reached at bar idx 1
        dn_min=np.array([-0.2, -0.5, -1.0]),# stop (k=1) reached later at idx 2
        close_ret=np.array([0.0, 0.0, 0.0]),
    )
    out = barriers.resolve(env, k=1.0, h_min=15)
    assert out.barrier == "PROFIT" and out.ttr_min == 2.0, out
    print("ok  profit_before_stop")


def test_time_outcome_and_horizon_cap():
    env = barriers.Envelope(
        ref=10.0, atr=1.0, spread=0.02,
        minutes=np.array([10.0, 20.0, 30.0]),
        up_max=np.array([0.3, 0.6, 5.0]),   # profit only at 30m
        dn_min=np.array([-0.1, -0.2, -0.3]),
        close_ret=np.array([0.01, 0.02, 0.5]),
    )
    # With H=15m, the 30m profit is out of horizon -> TIME, using last in-horizon bar.
    out = barriers.resolve(env, k=1.0, h_min=15)
    assert out.barrier == "TIME" and out.ttr_min == 10.0, out
    assert abs(out.realized_return - 0.01) < 1e-9, out
    print("ok  time_outcome_and_horizon_cap")


def test_atr_pit_uses_only_past():
    """ATR at entry must ignore the entry bar and everything after it."""
    bars = SyntheticDataProvider().get_minute_bars("MGNI", dt.date(2025, 1, 2))
    entry = bars.index[200]
    a1 = barriers.atr_5m_pit(bars, entry)
    # Corrupt all bars at/after entry; ATR must be unchanged.
    corrupted = bars.copy()
    corrupted.loc[corrupted.index >= entry, ["high", "low", "close"]] *= 100.0
    a2 = barriers.atr_5m_pit(corrupted, entry)
    assert a1 is not None and a2 is not None and abs(a1 - a2) < 1e-9, (a1, a2)
    print("ok  atr_pit_uses_only_past")


def test_grid_monotonicity():
    """Label-property sanity: with H fixed, larger k -> more TIME, fewer resolutions."""
    provider = SyntheticDataProvider()
    dates = [dt.date(2025, 1, 2), dt.date(2025, 1, 3)]
    res = grid.run_grid(provider, ["MGNI", "CRDO", "KTOS"], dates,
                        k_grid=[0.5, 2.0], h_grid=[60])
    lut = {(c.k, c.h_min): c for c in res["cells"]}
    assert lut[(2.0, 60)].time_pct >= lut[(0.5, 60)].time_pct, \
        (lut[(0.5, 60)].time_pct, lut[(2.0, 60)].time_pct)
    print(f"ok  grid_monotonicity (time%: k=0.5 -> {lut[(0.5,60)].time_pct:.0%}, "
          f"k=2.0 -> {lut[(2.0,60)].time_pct:.0%})")


if __name__ == "__main__":
    test_tie_break_stop_first()
    test_profit_before_stop()
    test_time_outcome_and_horizon_cap()
    test_atr_pit_uses_only_past()
    test_grid_monotonicity()
    print("\nALL TESTS PASSED")
