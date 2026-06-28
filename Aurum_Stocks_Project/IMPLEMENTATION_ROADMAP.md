# Implementation Roadmap

The ordered path from frozen label to live trading. Each phase is built **only after** the previous
is complete and tested, and each runs **behind its own ratified step**. Status legend:
✅ done · 🟡 in progress · ⬜ not started · 🔒 gated/awaiting authorization.

| # | Phase | Status | What it is | Gate / dependency |
|---|---|---|---|---|
| 0 | **Foundations & Calibration substrate** | ✅ done | foundation R1–R4, registries, integrity 6/6, calibration framework, research platform (RERL/REKL) | tests 9/9 green |
| — | **`LBL_V1` Freeze** | ⬜ not started (operator) | run SIP calibration → freeze the label | **the single blocker**: needs real SIP; flips `READY_FOR_COLLECTION` |
| 1 | **MDVPL** (Market Data Validation & Provenance) | ✅ done | validate raw data + record provenance; provider-agnostic; read-only/pass-through | implemented in `pipeline/mdvpl/`, tested |
| 2 | **Collection Layer** | ⬜ not started | raw (validated) data → signed immutable `ObservationRow`s (full-population, PIT) | starts after this review is accepted; depends on MDVPL ✅ + `LBL_V1` for real data |
| 3 | **Observation Store** | ⬜ not started | append-only, date-partitioned store for core/features/outcome | depends on Phase 2 |
| 4 | **Dataset Builder** | ⬜ not started | versioned, content-hashed research frames (read-only, streaming) | depends on Phase 3 |
| 5 | **Feature Discovery** | 🔒 future | features via the existing discovery path (admission · PIT · pre-registration · OOS · FDR · Vault) | requires explicit authorization |
| 6 | **ML** | 🔒 future | models trained on confirmed features/datasets | requires explicit authorization |
| 7 | **Paper Trading** | 🔒 future | first orders, PAPER_ONLY (TradeZero/IBKR paper) | `READY_FOR_TRADING` + OOS-validated edge |
| 8 | **Live Trading** | 🔒 future | live execution | separate, explicit decision; `LIVE_ALLOWED` currently FALSE (hardcoded) |

> **Note on Phase 2 (Collection Layer):** Phase 2 may be fully implemented and unit-tested using
> the Mock provider. Real-data execution remains blocked until `LBL_V1` is frozen. (The same holds
> for Phases 3–4: build and unit-test against the mock provider now; only real-data runs wait on
> the freeze.)

## Where we are now
- **Done:** Phase 0, Phase 1 (MDVPL). Research platform (RERL/REKL) complete and tested.
- **In progress:** none (paused for this repository-quality pass).
- **Not started:** `LBL_V1` freeze (operator action), Collection Layer (Phase 2) and everything after.
- **Blocker:** `LBL_V1_FROZEN = FALSE` → `READY_FOR_COLLECTION = FALSE`. Phases 2–4 can be *built and
  unit-tested with the mock provider* without SIP, but cannot run on real data until the label is
  frozen.

## Build rules carried through every phase
No change to contracts / registries / labels / gates / `ObservationRow` / frozen hashes. No
features/ML/trading/scanner/prediction/score/sentiment added outside their authorized phase. Each
new layer is additive, isolated from the frozen substrate, and consumes data only through abstract
provider interfaces (adapter swap, nothing else).

## Immediate sequence (next three actions, for reference only)
1. (operator) freeze `LBL_V1` via the SIP calibration run — unblocks real data.
2. (engineer) build **Collection Layer** against the MDVPL-validated source + mock provider; test green.
3. (engineer) build **Observation Store**; wire Collection → Store; test green.

> The single next step is in `NEXT_STEP.md`.
