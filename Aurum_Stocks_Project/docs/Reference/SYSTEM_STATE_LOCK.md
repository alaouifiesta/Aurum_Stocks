# SYSTEM STATE LOCK — Single Source of Truth
**Authoritative project status.** If any other document disagrees with this one, this wins.
Last normalized: repository pass (src layout + docs). Behavior unchanged; all tests green.

## Gate
```
READY_FOR_COLLECTION = FALSE
  blocker: LBL_V1_FROZEN = FALSE  (SIP calibration run not executed)
  all other conditions TRUE · integrity 6/6 GREEN · burn not yet sealed
```

## Locks (ratified / frozen)
| lock | value |
|---|---|
| RUBRIC_RATIFIED | TRUE |
| rubric_hash | `11cf5f1c64319a790e172e104df4878f8c6eecaa50503588b6e89962ed01628c` |
| RG1 regime cadence | HOURLY |
| TRADING_DIRECTION | LONG_ONLY (structural absence of short/borrow/locate) |
| TRADING_STYLE | INTRADAY_ONLY (force EOD flatten — execution track) |
| TRADING_MODE | PAPER_ONLY · LIVE_ALLOWED = FALSE (hardcoded) |
| Observation signature | 6 ids (symbol·regime·setup·label·universe·scanner) |
| Supreme contracts | Research Firewall · Execution Firewall · Full-Population Observation |

## Build status
| area | status |
|---|---|
| Priority #1 (calibration substrate) | COMPLETE |
| Priority #2 (registries · observation · PIT · integrity · data-integrity · research/label) | COMPLETE |
| Priority #3 (execution / scanner logic / ML) | NOT AUTHORIZED — design only |
| Pipeline · MDVPL (`pipeline/mdvpl/`) | IMPLEMENTED + tested (read-only validation/provenance; mock provider only) |
| `LBL_V1` | NOT created (mechanism empty) |
| Tests | 5 suites GREEN |
| Schema | 15 tables; 0 pending |

## Verification record (audited PASS)
Edge-blind · Pre-registration · Burn isolation · Label-property-only · Cross-regime stability ·
Immutability · Gate-dependency — all PASS (LBL_V1 Freeze Package audit).

## Single remaining action
Operator executes the SIP calibration run → freeze `LBL_V1` → re-verify gate →
`READY_FOR_COLLECTION = TRUE`. Nothing else is outstanding; no new design is required.

## Pointers
Status detail → `PROJECT_STATUS.md` · gate → `GATE_STATE.md` · registries →
`REGISTRY_REFERENCE.md` · label → `LABEL_SYSTEM.md` · runbook → `CALIBRATION_RUNBOOK.md` ·
integrity → `INTEGRITY_SUITE.md` · deps → `DEPENDENCY_MAP.md` · tables →
`MIGRATION_INVENTORY.md` · operational roadmap → `../../IMPLEMENTATION_ROADMAP.md` (single reference) · priority context → `ROADMAP.md` · history → `../Archive/`.
