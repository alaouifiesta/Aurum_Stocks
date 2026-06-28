# Research Event Reconstruction Layer (RERL)

Read-only research layer that reconstructs the **full chronological timeline** of an event
(especially news) from point-in-time market data, linking the anchor to subsequent **factual**
tape occurrences. It builds a **historical knowledge base** for future research/models. It is
**separate** from the Observation Builder, Feature Registry, and Label System, and changes no
Gate, Registry, Label, or Priority #3.

> **Hard guarantees (true by construction):** read-only · no features · no scanner candidates ·
> no ML · no trading decisions · no scores/sentiment/direction-as-signal · no future-information
> leakage at any detection point. Entries are factual, each with its own timestamp.

## What it produces
A `Timeline` anchored at an event's `available_ts` (t0), spanning `[-pre, +post]` minutes, listing
timestamped facts, each tagged by **phase**: `PRE` (before t0), `AT` (the anchor), `POST` (after t0
— **forward / outcome-side context, firewalled** from any feature path).

Detected fact types (all deterministic, rule-based, trailing/cumulative — never peek forward):
`OPENING_RANGE_SET` · `OR_BREAK_UP/DOWN` · `VOLUME_EXPANSION` (vol ≥ k× trailing median) ·
`SWEEP_OF_HIGHS/LOWS` (prior extreme taken out then reclaimed) · `NEW_SESSION_HIGH/LOW` ·
`VWAP_CROSS_UP/DOWN` (cumulative-session VWAP) · `HALT_START/RESUME` (read-only input) ·
`CLUSTER` (≥ N facts within a window). None carries a score, direction-as-signal, or label.

## PIT / firewall design
- Each detector uses only bars **up to and including** the bar it fires on (trailing windows,
  cumulative VWAP) — so every entry is honest at its **own** timestamp.
- The timeline extends past t0 only as a **record**; `POST` entries are explicitly forward/outcome
  context and must never be consumed as pre-signal inputs. Every entry keeps its timestamp so any
  future consumer can apply its **own** point-in-time cut.
- `TimelineEvent` structurally **rejects** any `detail` key in
  {score, signal, sentiment, bullish, bearish, label, prediction, probability, feature, rank, edge}.

## Folder
```
research/reconstruction/
├── timeline.py     Timeline + TimelineEvent (+ render / to_json); forbids score/signal keys
├── detectors.py    deterministic factual detectors (OR, volume, sweeps, breakouts, VWAP, clusters)
└── engine.py       ReconstructionEngine — assembles a phase-tagged timeline (read-only)
research/run_reconstruct.py   demo CLI
```

## Usage
```python
from research.reconstruction import ReconstructionEngine
# bar_source = any object exposing get_minute_bars(symbol, date) -> tz-aware ET OHLCV frame
eng = ReconstructionEngine(bar_source)
tl = eng.reconstruct("ABCD", "2025-03-03T15:00:00+00:00",
                     anchor_ref={"news_record_id": "..."}, pre_minutes=30, post_minutes=120)
print(tl.render())          # human-readable timeline
data = tl.to_dict()         # serialisable knowledge-base record
```
Demo (synthetic bars, offline): `python research/run_reconstruct.py --demo`.

## Boundaries
RERL never writes production data, never registers a feature, never emits a candidate or signal.
A real run requires a PIT bar source (e.g. the operator's SIP provider) and, optionally, a
read-only halt source. Any future predictive use of a timeline must go through the standard
feature-discovery path (admission, PIT proof, pre-registration, OOS, FDR, Vault) — never directly.
