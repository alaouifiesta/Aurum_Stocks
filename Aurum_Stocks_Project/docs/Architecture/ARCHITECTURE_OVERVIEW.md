# Architecture Overview

Aurum Stocks (Phase 1) is an **edge-discovery substrate**, not a trading bot. It turns
every candidate signal into a statistically valid, point-in-time, fully-signed observation
row. Five layers, each with one job.

```
        ┌──────────────────────────────────────────────────────────┐
        │  REGISTRY LAYER  (reference + data-integrity, all PIT)    │
        └───────────────┬──────────────────────────────────────────┘
                        │ resolve versions / quality / news / halts (as-of signal_ts)
        ┌───────────────▼──────────────────────────────────────────┐
        │  OBSERVATION LAYER  (setup-agnostic builder)             │
        │  SignalEvent → ObservationRow (6-id signature)           │
        └───────────────┬──────────────────────────────────────────┘
                        │ every feature must clear ↓
        ┌───────────────▼──────────────────────────────────────────┐
        │  PIT LAYER  (harness + gate; UNKNOWN == REJECTED)        │
        └──────────────────────────────────────────────────────────┘
        ┌──────────────────────────────────────────────────────────┐
        │  CALIBRATION LAYER  (triple-barrier label, label-props)  │  → LBL_V1
        └──────────────────────────────────────────────────────────┘
        ┌──────────────────────────────────────────────────────────┐
        │  INTEGRITY LAYER  (6 checks) → READY_FOR_COLLECTION       │
        └──────────────────────────────────────────────────────────┘
```

## Registry layer (`src/aurum_stocks/registries`)
SQLite-backed, append-only, point-in-time. Two families: **reference** (symbol, regime,
setup, scanner, universe) supply the versions an observation is signed with; **data-integrity**
(data_quality, news, halt, microstructure) guard against fake edge from data errors. All
resolvers are **NO-FALLBACK**: a missing version raises, never substitutes. See
`REGISTRY_REFERENCE.md`.

## Observation layer (`foundation/observation_builder.py`)
The `ObservationBuilder` is **setup-agnostic** (no `if setup == …`). For each `SignalEvent`
it resolves six reference versions (symbol · regime · setup · label · universe · scanner),
computes PIT features, assigns the dataset role, and emits an immutable `ObservationRow`
signed by `registry_signature_hash` over those six versions. Contracts enforced here:
GC-7 long-only (non-LONG ⇒ `LongOnlyViolation`), NO-FALLBACK (missing version ⇒
`ObservationRejected`), data_as_of ≤ signal_ts.

## PIT layer (`foundation/pit_harness.py`, `foundation/pit_gate.py`)
Defends against lookahead. The harness recomputes a feature on **truncated** vs **full**
data and demands equality. The gate wraps it into a verdict: **PASS / FAIL / UNKNOWN**, with
coverage requirements; **UNKNOWN == REJECTED** ("untested" is not "safe"). Only PASS admits a
feature into the Feature Registry.

## Calibration layer (`src/aurum_stocks/calibration`)
Decides the label (`k`, `H`, TIME encoding) on **label-property grounds only** — never edge.
Triple-barrier: ATR(14)@5m PIT · 1-min path · STOP-first tie-break · symmetric `±k·ATR` ·
`H` capped at RTH close. Allowed metrics: hit distribution, balance/entropy, TTR,
barrier÷spread, TB4 sign-split. See `LABEL_SYSTEM.md` + `CALIBRATION_RUNBOOK.md`.

## Integrity layer (`src/aurum_stocks/integrity`)
Six checks (PIT lookup · burn isolation · 6-id signing · anti-survivorship · rebuild
determinism · completeness audit) and the `READY_FOR_COLLECTION` interlock. A single RED ⇒
gate FALSE. See `INTEGRITY_SUITE.md`.

## Cross-cutting invariants (supreme)
LONG_ONLY · INTRADAY_ONLY · PAPER_ONLY (future) · **Research Firewall** (execution data never
feeds features) · **Full-Population Observation** (every candidate observed). No code path may
route around these.
