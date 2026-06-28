"""research/reconstruction/engine.py — assemble a reconstructed timeline.

Read-only. Decoupled: it accepts any `bar_source` exposing
    get_minute_bars(symbol, date) -> tz-aware ET DataFrame[open,high,low,close,volume,...]
(the same contract the calibration DataProvider already uses). It writes nothing, registers
nothing, and produces no features/signals — only a chronological, factual Timeline.

PIT discipline: each detector is internally trailing/cumulative (never peeks forward), so every
entry is honest at its own timestamp. The timeline spans forward of the anchor only as a RECORD;
post-anchor entries are tagged POST (outcome/forward) and are firewalled from feature use.
"""
from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

import pandas as pd

from . import detectors as D
from .timeline import Timeline, TimelineEvent, PRE, AT, POST

ET = ZoneInfo("America/New_York")


def _utc_iso(ts: pd.Timestamp) -> str:
    return ts.tz_convert("UTC").isoformat()


def _phase(ts: pd.Timestamp, anchor: pd.Timestamp) -> str:
    a = anchor.floor("min")
    t = ts.floor("min")
    if t < a:
        return PRE
    if t == a:
        return AT
    return POST


class ReconstructionEngine:
    def __init__(self, bar_source, *, or_minutes: int = 15, vol_k: float = 3.0,
                 vol_lookback: int = 20, sweep_lookback: int = 10,
                 cluster_window: int = 5, cluster_min: int = 3):
        self.bar_source = bar_source
        self.or_minutes = or_minutes
        self.vol_k = vol_k
        self.vol_lookback = vol_lookback
        self.sweep_lookback = sweep_lookback
        self.cluster_window = cluster_window
        self.cluster_min = cluster_min

    def reconstruct(self, symbol: str, anchor_ts_utc: str, *,
                    anchor_kind: str = "NEWS", anchor_ref: dict | None = None,
                    pre_minutes: int = 30, post_minutes: int = 120,
                    halts: list | None = None) -> Timeline:
        """Build the timeline around `anchor_ts_utc` (a UTC ISO string) for `symbol`.
        `halts` (optional, read-only) = list of (start_ts_utc, end_ts_utc, reason)."""
        anchor = pd.Timestamp(anchor_ts_utc)
        if anchor.tzinfo is None:
            raise ValueError("anchor_ts_utc must be timezone-aware (UTC)")
        anchor_et = anchor.tz_convert(ET)
        date = anchor_et.date()

        bars = self.bar_source.get_minute_bars(symbol, date)
        tl = Timeline(symbol=symbol, anchor_ts_utc=_utc_iso(anchor),
                      anchor_kind=anchor_kind, anchor_ref=anchor_ref or {},
                      pre_minutes=pre_minutes, post_minutes=post_minutes)

        # anchor event itself
        tl.add(TimelineEvent(_utc_iso(anchor), anchor_kind, AT, anchor_ref or {}))

        if bars is None or len(bars) == 0:
            return tl.sort()

        # run all detectors over the full session (correct OR / VWAP / session extremes)
        raw = []
        raw += D.opening_range(bars, self.or_minutes)
        raw += D.volume_expansion(bars, self.vol_k, self.vol_lookback)
        raw += D.sweeps(bars, self.sweep_lookback)
        raw += D.breakouts(bars, self.or_minutes)
        raw += D.vwap_interactions(bars)

        # optional halts (read-only input)
        for h in (halts or []):
            start, end, reason = h[0], h[1], (h[2] if len(h) > 2 else "")
            raw.append((pd.Timestamp(start), "HALT_START", {"reason": reason}))
            raw.append((pd.Timestamp(end), "HALT_RESUME", {"reason": reason}))

        # clusters over the assembled facts (excluding the anchor)
        raw += D.clusters(raw, self.cluster_window, self.cluster_min)

        # window bounds (capped at session close via the bars themselves)
        lo = anchor - pd.Timedelta(minutes=pre_minutes)
        hi = anchor + pd.Timedelta(minutes=post_minutes)

        for ts, kind, detail in raw:
            ts = ts.tz_convert("UTC") if ts.tzinfo else ts.tz_localize("UTC")
            if lo <= ts <= hi:
                tl.add(TimelineEvent(_utc_iso(ts), kind, _phase(ts, anchor), detail))

        return tl.sort()
