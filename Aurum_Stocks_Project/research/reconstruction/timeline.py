"""research/reconstruction/timeline.py — the reconstructed event timeline.

A Timeline is a chronological list of FACTUAL, timestamped tape occurrences anchored to
one event (typically a news item). It is OUTCOME-SIDE research context: entries after the
anchor are labelled POST/forward and are firewalled from any pre-signal feature path.

There are NO scores, NO directions-as-signals, NO predictions, NO features here — only
"what objectively happened, and when". Every entry carries its own timestamp so any future
consumer can apply its own point-in-time cut.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict

# Phase of an entry relative to the anchor event (t0).
PRE = "PRE"     # strictly before the anchor became available
AT = "AT"       # same minute as the anchor
POST = "POST"   # after the anchor — FORWARD / OUTCOME-SIDE context (firewalled)

# Forbidden keys: a guard so a detail dict can never smuggle a score/signal/feature.
_FORBIDDEN_DETAIL_KEYS = {
    "score", "signal", "sentiment", "bullish", "bearish", "label",
    "prediction", "probability", "feature", "rank", "edge",
}


@dataclass(frozen=True)
class TimelineEvent:
    ts_utc: str          # UTC ISO timestamp of the occurrence (its OWN time)
    kind: str            # factual type, e.g. VWAP_CROSS_UP, VOLUME_EXPANSION, SWEEP_OF_HIGHS
    phase: str           # PRE / AT / POST relative to the anchor
    detail: dict = field(default_factory=dict)

    def __post_init__(self):
        bad = _FORBIDDEN_DETAIL_KEYS & set(self.detail or {})
        if bad:
            raise ValueError(f"timeline detail may not contain {sorted(bad)} "
                             f"(RERL is factual-only, no scores/signals/features)")


@dataclass
class Timeline:
    symbol: str
    anchor_ts_utc: str                 # t0 — the event being reconstructed around
    anchor_kind: str = "NEWS"
    anchor_ref: dict = field(default_factory=dict)   # provenance (e.g. news record id)
    pre_minutes: int = 30
    post_minutes: int = 120
    events: list[TimelineEvent] = field(default_factory=list)

    def add(self, ev: TimelineEvent) -> None:
        self.events.append(ev)

    def sort(self) -> "Timeline":
        self.events.sort(key=lambda e: (e.ts_utc, e.kind))
        return self

    def of_phase(self, phase: str) -> list[TimelineEvent]:
        return [e for e in self.events if e.phase == phase]

    def kinds(self) -> dict:
        from collections import Counter
        return dict(sorted(Counter(e.kind for e in self.events).items()))

    def to_dict(self) -> dict:
        d = asdict(self)
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    def render(self) -> str:
        L = [
            "=" * 70,
            f"EVENT RECONSTRUCTION TIMELINE  ·  {self.symbol}",
            f"anchor: {self.anchor_kind} @ {self.anchor_ts_utc}",
            f"window: -{self.pre_minutes}m .. +{self.post_minutes}m   "
            f"({len(self.events)} events)",
            "=" * 70,
        ]
        for e in self.events:
            tag = {PRE: "  ", AT: ">>", POST: " +"}.get(e.phase, "  ")
            det = "  ".join(f"{k}={v}" for k, v in e.detail.items())
            L.append(f"{tag} [{e.phase:<4}] {e.ts_utc}  {e.kind:<22} {det}")
        L.append("=" * 70)
        L.append("NOTE: POST entries are forward/outcome context — not features, not signals.")
        return "\n".join(L)
