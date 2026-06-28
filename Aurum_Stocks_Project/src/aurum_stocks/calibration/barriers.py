"""
calibration/barriers.py — point-in-time ATR and triple-barrier resolution.

Honors the FROZEN rules from spec v1.0-RC2:
  * ATR(14) on 5-minute bars, computed strictly from bars completed BEFORE entry.
  * Barrier touches evaluated on 1-minute bars (high/low within bar).
  * Symmetric, volatility-scaled barriers: profit/stop at ref ± k*ATR.
  * Tie-break STOP_FIRST: a single bar touching both barriers resolves to STOP.
  * Time barrier H, capped at RTH close (no cross-session holds).

Design note (efficiency + correctness): for each candidate entry we scan the
forward path ONCE up to the largest H in the grid, recording each forward bar's
favourable/adverse excursion in ATR units and its minutes-from-entry. Every
(k,H) cell is then resolved from those precomputed monotone excursion envelopes,
so the whole grid reuses one path walk per entry.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import config


# ---------------------------------------------------------------------------
# Point-in-time ATR(14) on 5-minute bars
# ---------------------------------------------------------------------------
def atr_5m_pit(bars_1m: pd.DataFrame, entry_ts: pd.Timestamp) -> float | None:
    """Wilder ATR(period) on 5-min bars, using only 5-min buckets that CLOSED at
    or before `entry_ts`. Returns None if insufficient history."""
    past = bars_1m.loc[bars_1m.index < entry_ts]
    if past.empty:
        return None
    agg = past.resample(f"{config.ATR_TIMEFRAME_MIN}min", label="right", closed="right").agg(
        {"high": "max", "low": "min", "close": "last"}
    ).dropna()
    # Keep only buckets whose right edge (close time) is <= entry_ts (fully formed).
    agg = agg.loc[agg.index <= entry_ts]
    if len(agg) < config.ATR_PERIOD + 1:
        return None
    high, low, close = agg["high"].values, agg["low"].values, agg["close"].values
    prev_close = np.empty_like(close)
    prev_close[0] = close[0]
    prev_close[1:] = close[:-1]
    tr = np.maximum.reduce([
        high - low,
        np.abs(high - prev_close),
        np.abs(low - prev_close),
    ])
    # Wilder smoothing (RMA).
    p = config.ATR_PERIOD
    atr = tr[1:p + 1].mean()
    for x in tr[p + 1:]:
        atr = (atr * (p - 1) + x) / p
    return float(atr) if atr > 0 else None


# ---------------------------------------------------------------------------
# Forward excursion envelope (one scan per entry, reused across the grid)
# ---------------------------------------------------------------------------
@dataclass
class Envelope:
    ref: float
    atr: float
    spread: float
    minutes: np.ndarray       # minutes from entry for each forward bar
    up_max: np.ndarray        # running max favourable excursion, in ATR units
    dn_min: np.ndarray        # running min adverse excursion, in ATR units (<= 0)
    close_ret: np.ndarray     # (close-ref)/ref per forward bar (for TIME outcome)


def build_envelope(bars_1m: pd.DataFrame, entry_ts: pd.Timestamp,
                   session_close: pd.Timestamp, max_h_min: int) -> Envelope | None:
    """Precompute the forward excursion envelope for one entry, long-orientation
    (up = favourable). Symmetric barriers make this sufficient to characterise the
    label distribution. Path is confined to the current session."""
    atr = atr_5m_pit(bars_1m, entry_ts)
    if atr is None:
        return None
    entry_row = bars_1m.loc[bars_1m.index == entry_ts]
    if entry_row.empty:
        return None
    ref = float(entry_row["close"].iloc[0])
    spread = float((entry_row["ask"] - entry_row["bid"]).iloc[0])

    horizon_end = min(entry_ts + pd.Timedelta(minutes=max_h_min), session_close)
    fwd = bars_1m.loc[(bars_1m.index > entry_ts) & (bars_1m.index <= horizon_end)]
    if fwd.empty:
        return None

    minutes = (fwd.index - entry_ts).total_seconds().values / 60.0
    up = (fwd["high"].values - ref) / atr
    dn = (fwd["low"].values - ref) / atr
    up_max = np.maximum.accumulate(up)          # monotone non-decreasing
    dn_min = np.minimum.accumulate(dn)          # monotone non-increasing
    close_ret = (fwd["close"].values - ref) / ref
    return Envelope(ref, atr, spread, minutes, up_max, dn_min, close_ret)


# ---------------------------------------------------------------------------
# Resolve one (k, H) cell from a precomputed envelope
# ---------------------------------------------------------------------------
@dataclass
class Outcome:
    barrier: str           # "PROFIT" | "STOP" | "TIME"
    ttr_min: float         # minutes to resolution (H for TIME)
    realized_return: float # signed return at resolution (TIME: at horizon end)
    barrier_distance: float
    spread: float


def resolve(env: Envelope, k: float, h_min: int) -> Outcome:
    # Restrict to bars within H.
    last = int(np.searchsorted(env.minutes, h_min, side="right"))  # bars[:last] within H
    if last <= 0:
        return Outcome("TIME", float(h_min), 0.0, k * env.atr, env.spread)

    um = env.up_max[:last]
    dm = env.dn_min[:last]
    # First index reaching profit / stop (accumulated arrays are monotone).
    profit_idx = int(np.searchsorted(um, k, side="left"))
    profit_hit = profit_idx < last
    stop_idx = int(np.searchsorted(-dm, k, side="left"))  # -dm is non-decreasing
    stop_hit = stop_idx < last

    barrier_distance = k * env.atr

    if not profit_hit and not stop_hit:
        return Outcome("TIME", float(env.minutes[last - 1]),
                       float(env.close_ret[last - 1]), barrier_distance, env.spread)
    if profit_hit and not stop_hit:
        return Outcome("PROFIT", float(env.minutes[profit_idx]),
                       k * env.atr / env.ref, barrier_distance, env.spread)
    if stop_hit and not profit_hit:
        return Outcome("STOP", float(env.minutes[stop_idx]),
                       -k * env.atr / env.ref, barrier_distance, env.spread)
    # Both hit: earlier bar wins; same bar -> STOP_FIRST (frozen tie-break).
    if profit_idx < stop_idx:
        return Outcome("PROFIT", float(env.minutes[profit_idx]),
                       k * env.atr / env.ref, barrier_distance, env.spread)
    else:
        return Outcome("STOP", float(env.minutes[stop_idx]),
                       -k * env.atr / env.ref, barrier_distance, env.spread)
