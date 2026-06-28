# Documentation Index

Authoritative entry point. Start at **`Reference/SYSTEM_STATE_LOCK.md`** (single source of truth),
then read by area. Anything under **`Archive/`** is historical and **NOT authoritative for
implementation**.

## Reference/ — authoritative state & contracts
| file | purpose |
|---|---|
| `Reference/SYSTEM_STATE_LOCK.md` | **Single source of truth** — gate, locks, build status |
| `Reference/PROJECT_STATUS.md` | Gate · blocker · `rubric_hash` · integrity · priority · build completion |
| `Reference/PROJECT_TREE.md` | Full repository tree |
| `Reference/REGISTRY_REFERENCE.md` | Every registry |
| `Reference/LABEL_SYSTEM.md` | Triple-barrier · LabelSpec · freeze · immutability |
| `Reference/GATE_STATE.md` | Gate conditions table + locked flags |
| `Reference/INTEGRITY_SUITE.md` | The 6 integrity checks + READY_FOR_COLLECTION |
| `Reference/MIGRATION_INVENTORY.md` | Tables · migrations · pending |
| `Reference/ROADMAP.md` | Priority/discovery context only — **operational roadmap is `../IMPLEMENTATION_ROADMAP.md`** |
| `Reference/FINAL_REPOSITORY_AUDIT.md` | Last full repository audit (PASS) — *historical snapshot, not current state* |

## Architecture/ — how the system is shaped
| file | purpose |
|---|---|
| `Architecture/ARCHITECTURE_OVERVIEW.md` | The five production layers |
| `Architecture/DEPENDENCY_MAP.md` | Module · depends on · used by (no cycles) |
| `Architecture/ARCHITECTURE_REVIEW.md` | Full architecture review (findings + Dataset Builder design) |

## Implementation/ — active build blueprints (current phase)
| file | purpose |
|---|---|
| `Implementation/MARKET_DATA_VALIDATION_PROVENANCE.md` | MDVPL design — **IMPLEMENTED** in `pipeline/mdvpl/` (tested) |
| `Implementation/COLLECTION_LAYER_ARCHITECTURE.md` | Collection Layer + Observation Store + Dataset Builder blueprint |

## Operator/ — run the system
| file | purpose |
|---|---|
| `Operator/OPERATOR_EXECUTION_GUIDE.md` | Non-developer, 8-phase execution guide |
| `Operator/SIP_SETUP_GUIDE.md` | SIP vs IEX · provider requirements · validation · freeze verify |
| `Operator/CALIBRATION_RUNBOOK.md` | Raw SIP → frozen LBL_V1 |
| `Operator/DEPLOYMENT_GUIDE.md` | Python · venv · deps · tests · calibration · DB backup/restore |

## Research/ — the read-only research platform
| file | purpose |
|---|---|
| `Research/RESEARCH_PLATFORM_GUIDE.md` | Operator manual for `research/` + full lifecycle |
| `Research/RESEARCH_EVENT_RECONSTRUCTION.md` | RERL: factual event timelines from PIT data |
| `Research/RESEARCH_EVENT_KNOWLEDGE.md` | REKL: archetypes · graph · query · stats · viz |

## Code areas (where the docs map to)
| area | docs |
|---|---|
| `src/aurum_stocks/` (frozen substrate) | Architecture/ + Reference/ |
| `pipeline/` (runtime: MDVPL -> Collection -> Store -> Dataset Builder) | Implementation/ |
| `research/` (read-only research platform) | Research/ |
| `ops/` (operator calibration scripts) | Operator/ |

## Archive/ — historical, NOT authoritative
Frozen design packages and superseded proposals. Kept for history only; **do not implement from
`Archive/`**. See `Archive/README.md`.
