# Roadmap

> **Authoritative phase roadmap:** `../../IMPLEMENTATION_ROADMAP.md` (8 phases with live status: MDVPL ✅ → Collection → Store → Dataset Builder → Feature Discovery → ML → Paper → Live). This file gives the Priority/discovery context behind those phases; where the two differ on phase status, IMPLEMENTATION_ROADMAP.md wins.


## Done — Priority #1 & #2 (the discovery substrate)
- Calibration framework (triple-barrier, label-property metrics only) + burn ledger + partition assigner.
- Foundation contracts R1–R4; PIT harness + gate; feature registry (admission + lifecycle).
- Reference registries: symbol (SCD-2 PIT, NO-FALLBACK) · regime (HOURLY) · setup · scanner · universe.
- Observation Builder: setup-agnostic, 6-id signature, GC-7 long-only hard-fail.
- Integrity suite (6 checks) + `READY_FOR_COLLECTION` interlock.
- Data-integrity registries: data_quality · news · halt · microstructure(reserved).
- Research registry (pre-registration + ledger) · Label registry (write-once).
- Pre-registered calibration rubric ratified + hashed.

## Immediate next action (operator)
Execute the SIP calibration run (`docs/Operator/CALIBRATION_RUNBOOK.md`) → freeze `LBL_V1` →
`READY_FOR_COLLECTION = TRUE`. Only the operator can run it (no vendor data in the build env).

## Build order after `LBL_V1` freeze (ratified)
```
1. READY_FOR_COLLECTION   (flips TRUE on freeze)
2. Data Collection
3. Observation Accumulation
4. OOS Validation
5. Scanner Validation      (does scanner_score/rank add edge?)
6. Rank Validation
7. Paper Trading Activation ← first order placed, PAPER_ONLY
8. Execution Quality Validation
```
No live trading at any step.

## Priority #3 (NOT AUTHORIZED — design only exists)
Execution track: broker adapters (TradeZero-Paper primary, IBKR-Paper secondary), execution
event/fill/slippage models, paper trade journal, EOD flatten + post-close verification,
position sizing engine (in risk layer). Lives behind `READY_FOR_TRADING` (broker_registry +
OOS-validated edge). Supreme contracts always hold: PAPER_ONLY · LONG_ONLY · INTRADAY_ONLY ·
Research Firewall · Execution Firewall · Full-Population Observation.

## Reserved tracks
- `scanners/` — empty, Priority #3.
- `microstructure_registry` — reserved for L2 / order-flow / tick; populated features still
  take the full discovery path (no privileged features).
