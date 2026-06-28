"""research/reconstruction/detectors.py — deterministic, factual tape-event detectors.

Each detector reads a 1-minute bar frame (tz-aware ET index; columns open/high/low/close/
volume) and returns a list of (timestamp, kind, detail) facts. Every detection at time t
uses ONLY bars up to and including t (trailing windows / cumulative sums) — it never peeks
forward. These are descriptions of what happened, not features, not signals, not scores.
"""
from __future__ import annotations

import datetime as dt

import pandas as pd

RTH_OPEN = dt.time(9, 30)
RTH_CLOSE = dt.time(16, 0)


def _rth(bars: pd.DataFrame) -> pd.DataFrame:
    """Regular-trading-hours slice (PIT-neutral: a calendar filter)."""
    t = bars.index
    mask = [(RTH_OPEN <= ts.time() < RTH_CLOSE) for ts in t]
    return bars[mask]


def _typical(bars: pd.DataFrame) -> pd.Series:
    return (bars["high"] + bars["low"] + bars["close"]) / 3.0


def opening_range(bars: pd.DataFrame, or_minutes: int = 15):
    """OR levels over the first `or_minutes` of RTH, then the first breaks of those levels.
    Facts: OPENING_RANGE_SET, OR_BREAK_UP, OR_BREAK_DOWN."""
    rth = _rth(bars)
    if rth.empty:
        return []
    open_ts = rth.index[0]
    win_end = open_ts + pd.Timedelta(minutes=or_minutes)
    win = rth[rth.index < win_end]
    if win.empty:
        return []
    or_high = float(win["high"].max())
    or_low = float(win["low"].min())
    out = [(win.index[-1], "OPENING_RANGE_SET",
            {"or_high": round(or_high, 4), "or_low": round(or_low, 4),
             "or_minutes": or_minutes})]
    after = rth[rth.index >= win_end]
    up_done = down_done = False
    for ts, row in after.iterrows():
        if not up_done and row["high"] > or_high:
            out.append((ts, "OR_BREAK_UP", {"level": round(or_high, 4)}))
            up_done = True
        if not down_done and row["low"] < or_low:
            out.append((ts, "OR_BREAK_DOWN", {"level": round(or_low, 4)}))
            down_done = True
        if up_done and down_done:
            break
    return out


def volume_expansion(bars: pd.DataFrame, k: float = 3.0, lookback: int = 20):
    """A bar whose volume >= k * trailing median (prior `lookback` bars). Fact only."""
    out = []
    vol = bars["volume"].values
    idx = bars.index
    for i in range(lookback, len(bars)):
        window = vol[i - lookback:i]
        med = float(pd.Series(window).median())
        if med > 0 and vol[i] >= k * med:
            out.append((idx[i], "VOLUME_EXPANSION",
                        {"volume": int(vol[i]), "median": round(med, 1),
                         "ratio": round(vol[i] / med, 2)}))
    return out


def sweeps(bars: pd.DataFrame, lookback: int = 10):
    """Liquidity sweep facts: a bar takes out the prior `lookback` extreme then closes back
    inside it. Named by WHAT was swept (highs/lows) — a fact, not a buy/sell signal."""
    out = []
    high = bars["high"].values
    low = bars["low"].values
    close = bars["close"].values
    idx = bars.index
    for i in range(lookback, len(bars)):
        prior_high = float(high[i - lookback:i].max())
        prior_low = float(low[i - lookback:i].min())
        if high[i] > prior_high and close[i] <= prior_high:
            out.append((idx[i], "SWEEP_OF_HIGHS", {"level": round(prior_high, 4)}))
        if low[i] < prior_low and close[i] >= prior_low:
            out.append((idx[i], "SWEEP_OF_LOWS", {"level": round(prior_low, 4)}))
    return out


def breakouts(bars: pd.DataFrame, after_minutes: int = 15):
    """New session high/low facts after the opening range. NEW_SESSION_HIGH/LOW."""
    rth = _rth(bars)
    if rth.empty:
        return []
    open_ts = rth.index[0]
    start = open_ts + pd.Timedelta(minutes=after_minutes)
    run_high = run_low = None
    out = []
    for ts, row in rth.iterrows():
        h, l = float(row["high"]), float(row["low"])
        if run_high is None:
            run_high, run_low = h, l
            continue
        if ts >= start and h > run_high:
            out.append((ts, "NEW_SESSION_HIGH", {"high": round(h, 4)}))
        if ts >= start and l < run_low:
            out.append((ts, "NEW_SESSION_LOW", {"low": round(l, 4)}))
        run_high = max(run_high, h)
        run_low = min(run_low, l)
    return out


def vwap_interactions(bars: pd.DataFrame):
    """Cumulative-session VWAP crossings (PIT cumulative). VWAP_CROSS_UP / VWAP_CROSS_DOWN."""
    rth = _rth(bars)
    if len(rth) < 2:
        return []
    tp = _typical(rth)
    cum_pv = (tp * rth["volume"]).cumsum()
    cum_v = rth["volume"].cumsum().replace(0, pd.NA).ffill()
    vwap = (cum_pv / cum_v)
    diff = (rth["close"] - vwap)
    out = []
    prev = None
    for ts, d in diff.items():
        if pd.isna(d):
            continue
        if prev is not None and prev != 0 and d != 0 and (prev > 0) != (d > 0):
            kind = "VWAP_CROSS_UP" if d > 0 else "VWAP_CROSS_DOWN"
            out.append((ts, kind, {"vwap": round(float(vwap[ts]), 4)}))
        prev = d
    return out


def clusters(events, window_minutes: int = 5, min_events: int = 3):
    """Temporal clustering: >= min_events occurrences within window_minutes. Fact: CLUSTER.
    `events` is a list of (ts, kind, detail). Non-overlapping, deterministic."""
    ev = sorted(events, key=lambda e: e[0])
    out = []
    covered_until = None
    for i, (ts, _, _) in enumerate(ev):
        if covered_until is not None and ts <= covered_until:
            continue
        end = ts + pd.Timedelta(minutes=window_minutes)
        members = [e for e in ev if ts <= e[0] <= end]
        if len(members) >= min_events:
            out.append((ts, "CLUSTER",
                        {"count": len(members),
                         "span_minutes": window_minutes}))
            covered_until = end
    return out
