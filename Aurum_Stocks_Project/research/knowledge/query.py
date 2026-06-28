"""research/knowledge/query.py — Research Query Engine (filter conditions only).

Searches events/timelines by FILTER CONDITIONS. It SELECTS; it never ranks, scores, predicts,
or orders by any notion of edge. Detail predicates may filter on the factual descriptors that
already exist on an event (e.g. count, ratio, level, volume, vwap) — filtering on a fact is not
creating a score. Read-only.
"""
from __future__ import annotations

import operator as _op
from dataclasses import dataclass, field

from .archetypes import archetype_key, timeline_id

_OPS = {"==": _op.eq, "!=": _op.ne, ">": _op.gt, ">=": _op.ge,
        "<": _op.lt, "<=": _op.le, "in": lambda a, b: a in b}

# Filtering may never invent these — they are not facts on an event.
_FORBIDDEN = {"score", "signal", "sentiment", "bullish", "bearish", "label",
              "prediction", "probability", "feature", "rank", "edge"}


@dataclass
class Query:
    kinds: set | None = None
    phases: set | None = None
    ts_from: str | None = None
    ts_to: str | None = None
    symbols: set | None = None
    detail: list = field(default_factory=list)  # list of (key, op, value)

    def __post_init__(self):
        for key, _, _ in self.detail:
            if key in _FORBIDDEN:
                raise ValueError(f"cannot filter on forbidden non-fact key {key!r}")

    def _match_event(self, ev, symbol: str) -> bool:
        if self.kinds is not None and ev.kind not in self.kinds:
            return False
        if self.phases is not None and ev.phase not in self.phases:
            return False
        if self.symbols is not None and symbol not in self.symbols:
            return False
        if self.ts_from is not None and ev.ts_utc < self.ts_from:
            return False
        if self.ts_to is not None and ev.ts_utc > self.ts_to:
            return False
        for key, op, value in self.detail:
            if key not in ev.detail:
                return False
            if not _OPS[op](ev.detail[key], value):
                return False
        return True

    def run(self, timelines) -> list:
        """Return [(timeline_id, event), ...] for every matching event."""
        out = []
        for tl in timelines:
            tid = timeline_id(tl)
            for ev in tl.events:
                if self._match_event(ev, tl.symbol):
                    out.append((tid, ev))
        return out


def select_timelines(timelines, *, contains_kind: str | None = None,
                     archetype: tuple | None = None, min_events: int | None = None,
                     symbols: set | None = None) -> list:
    """Timeline-level selection (boolean). `archetype=(scheme, key)`."""
    out = []
    for tl in timelines:
        if symbols is not None and tl.symbol not in symbols:
            continue
        if contains_kind is not None and not any(e.kind == contains_kind for e in tl.events):
            continue
        if min_events is not None and len(tl.events) < min_events:
            continue
        if archetype is not None:
            scheme, key = archetype
            if archetype_key(tl, scheme) != key:
                continue
        out.append(tl)
    return out
