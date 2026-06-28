"""research/knowledge/stats.py — descriptive statistics for event families & chronology.

DESCRIPTIVE ONLY. Counts, frequencies, durations, and chronology (e.g. how long after the
anchor a kind first appears). There are NO performance metrics, NO win-rate, NO returns, NO
Sharpe, NO edge, NO scores of any kind — those are forbidden in this layer. Read-only.
"""
from __future__ import annotations

import datetime as dt
import statistics as st
from collections import Counter

from .archetypes import family_sizes  # re-exported convenience

_FORBIDDEN = {"score", "win_rate", "winrate", "return", "returns", "sharpe", "edge",
              "pnl", "expectancy", "probability", "prediction", "signal", "sentiment"}


def _parse(ts: str) -> dt.datetime:
    return dt.datetime.fromisoformat(ts)


def _describe(values) -> dict:
    values = list(values)
    if not values:
        return {"count": 0}
    return {"count": len(values), "min": min(values),
            "median": st.median(values), "max": max(values),
            "mean": round(st.fmean(values), 3)}


def kind_frequency(timelines) -> dict:
    c = Counter(e.kind for tl in timelines for e in tl.events)
    return dict(c.most_common())


def phase_distribution(timelines) -> dict:
    return dict(Counter(e.phase for tl in timelines for e in tl.events))


def events_per_timeline(timelines) -> dict:
    return _describe(len(tl.events) for tl in timelines)


def inter_event_gap_seconds(timelines) -> dict:
    gaps = []
    for tl in timelines:
        ts = [_parse(e.ts_utc) for e in tl.events]
        gaps += [(b - a).total_seconds() for a, b in zip(ts, ts[1:])]
    return _describe(gaps)


def time_to_first_kind_minutes(timelines, kind: str) -> dict:
    """Descriptive chronology: minutes from anchor to the first occurrence of `kind`.
    A timing description of history, NOT a performance/edge measure."""
    mins = []
    for tl in timelines:
        anchor = _parse(tl.anchor_ts_utc)
        first = next((e for e in tl.events if e.kind == kind and e.phase == "POST"), None)
        if first is not None:
            mins.append((_parse(first.ts_utc) - anchor).total_seconds() / 60.0)
    return _describe(mins)


def kind_pair_frequency(timelines) -> dict:
    """Counts of consecutive (kind -> next kind) pairs. Descriptive co-occurrence; NOT a
    transition probability and NOT a prediction."""
    c = Counter()
    for tl in timelines:
        kinds = [e.kind for e in tl.events]
        for a, b in zip(kinds, kinds[1:]):
            c[f"{a}->{b}"] += 1
    return dict(c.most_common())


def family_summary(timelines, scheme: str = "kind_set") -> dict:
    return family_sizes(timelines, scheme)


def summary(timelines) -> dict:
    out = {
        "timelines": len(list(timelines)) if not isinstance(timelines, list) else len(timelines),
        "kind_frequency": kind_frequency(timelines),
        "phase_distribution": phase_distribution(timelines),
        "events_per_timeline": events_per_timeline(timelines),
        "inter_event_gap_seconds": inter_event_gap_seconds(timelines),
    }
    # defensive: this layer never emits a forbidden (performance/edge) key
    assert not (_FORBIDDEN & set(out)), "statistical explorer must stay descriptive-only"
    return out
