# Project Inventory

Complete inventory of the repository, taken from the **actual filesystem** (not from memory).
Columns: **Nec.** = necessary · **Old** = superseded · **Move** = needs relocation · **Arch.** =
archived (historical, non-authoritative) · **Exec** = the runtime execution path depends on it
(`future` = depended on once that layer is built).

Totals: 73 Python files (src 34 · research 29 · pipeline 8 · ops 2) · 9 test suites · 41 docs ·
5 root config/meta. **Nothing requires moving; nothing is a stray; nothing is missing that blocks
the next phase.** Archive is already separated and labelled non-authoritative.

---

## 1. Code — `src/aurum_stocks/` (frozen production substrate)
| path | purpose | Nec. | Old | Move | Arch. | Exec |
|---|---|---|---|---|---|---|
| `foundation/dataset_roles.py` | R1 burn ledger + partition assigner | Y | N | — | — | Y |
| `foundation/label_spec.py` | R2 immutable LabelSpec | Y | N | — | — | Y |
| `foundation/pit_harness.py` | R3 lookahead defense | Y | N | — | — | Y |
| `foundation/observation_builder.py` | R4 setup-agnostic signed ObservationRow + 6-id signature | Y | N | — | — | Y |
| `foundation/pit_gate.py` | PASS/FAIL/UNKNOWN feature gate | Y | N | — | — | Y |
| `foundation/feature_registry.py` | feature admission + lifecycle | Y | N | — | — | future |
| `registries/db.py` | SQLite DDL (15 tables) + UTC-ISO helpers | Y | N | — | — | Y |
| `registries/symbol_registry.py` | SCD-2 PIT, NO-FALLBACK, anti-survivorship | Y | N | — | — | Y |
| `registries/regime_registry.py` | HOURLY regime snapshots | Y | N | — | — | Y |
| `registries/setup_registry.py` · `scanner_registry.py` · `universe_registry.py` | candidate/scan/universe provenance | Y | N | — | — | Y |
| `registries/data_quality_registry.py` · `news_registry.py` · `halt_registry.py` · `microstructure_registry.py` | data-integrity registries (microstructure RESERVED) | Y | N | — | — | Y |
| `registries/research_registry.py` | pre-registration manifest + experiment ledger | Y | N | — | — | future |
| `registries/label_registry.py` | write-once frozen label + 3 hashes | Y | N | — | — | Y |
| `integrity/integrity_suite.py` | 6 checks + READY_FOR_COLLECTION | Y | N | — | — | Y |
| `providers/providers.py` | news/halt/data-quality ABCs + mocks | Y | N | — | — | Y |
| `calibration/{config,barriers,metrics,grid,report,data_provider}.py` | label calibration framework | Y | N | — | — | Y |
| `calibration/README.md` | calibration framework readme | Y | N | — | — | N |
| `run_calibration.py` | synthetic/demo calibration CLI | Y | N | — | — | N |
| `scanners/__init__.py` | RESERVED (Priority #3) — empty by design | Y | N | — | — | N |
| `*/__init__.py` (package markers) | package structure | Y | N | — | — | Y |

## 2. Code — `pipeline/` (runtime data pipeline)
| path | purpose | Nec. | Old | Move | Arch. | Exec |
|---|---|---|---|---|---|---|
| `pipeline/mdvpl/source.py` | provider-agnostic `MarketDataSource` ABC + `MockMarketDataSource` | Y | N | — | — | Y |
| `pipeline/mdvpl/checks.py` | data-quality checks (facts only) | Y | N | — | — | Y |
| `pipeline/mdvpl/provenance.py` | append-only provenance record + log | Y | N | — | — | Y |
| `pipeline/mdvpl/report.py` | read-only quality report | Y | N | — | — | Y |
| `pipeline/mdvpl/validator.py` | orchestrator (pass-through, no transform) | Y | N | — | — | Y |
| `pipeline/run_mdvpl.py` | MDVPL demo CLI (mock; no real API) | Y | N | — | — | N |
| `pipeline/{__init__,mdvpl/__init__}.py` | package markers | Y | N | — | — | Y |

## 3. Code — `research/` (read-only research platform)
| path | purpose | Nec. | Old | Move | Arch. | Exec |
|---|---|---|---|---|---|---|
| `research/news/{records,archive,providers}.py` | canonical news archive (provenance only) + provider mocks | Y | N | — | — | N |
| `research/notebooks/research_session.py` (+ `NOTEBOOK_TEMPLATE.md`) | provenance recorder + template | Y | N | — | — | N |
| `research/inspector/observation_inspector.py` | explain one ObservationRow | Y | N | — | — | N |
| `research/explore/dataset_explorer.py` | read-only counts | Y | N | — | — | N |
| `research/audit/coverage_audit.py` | read-only coverage reporting | Y | N | — | — | N |
| `research/reconstruction/{timeline,detectors,engine}.py` | RERL factual event timelines | Y | N | — | — | N |
| `research/knowledge/{archetypes,graph,query,stats,viz}.py` | REKL knowledge base | Y | N | — | — | N |
| `research/demo.py` | synthetic data for tool demos | Y | N | — | — | N |
| `research/run_{inspector,explorer,audit,reconstruct,knowledge}.py` | read-only demo CLIs | Y | N | — | — | N |

## 4. Operations & CLIs
| path | purpose | Nec. | Old | Move | Arch. | Exec |
|---|---|---|---|---|---|---|
| `ops/run_lbl_calibration.py` | operator SIP calibration → freeze LBL_V1 | Y | N | — | — | Y |
| `ops/verify_lbl_freeze.py` | verify freeze + recompute gate (read-only) | Y | N | — | — | Y |
| `ops/README.md` | how to run the ops scripts | Y | N | — | — | N |
| `run_tests.sh` | full test-suite runner | Y | N | — | — | N |

## 5. Tests — `tests/`
| path | purpose | Nec. | Old | Move | Arch. | Exec |
|---|---|---|---|---|---|---|
| `tests/foundation/test_foundation.py` | R1–R4 + builder + GC-7 | Y | N | — | — | N |
| `tests/registries/test_registries.py` · `test_data_integrity.py` | registries + data-integrity | Y | N | — | — | N |
| `tests/calibration/test_barriers.py` | PIT ATR · tie-break · horizon cap | Y | N | — | — | N |
| `tests/integrity/test_feature_gate_integrity.py` | PIT gate + integrity 6/6 | Y | N | — | — | N |
| `tests/research/test_research_platform.py` · `test_reconstruction.py` · `test_knowledge.py` | research/RERL/REKL | Y | N | — | — | N |
| `tests/pipeline/test_mdvpl.py` | MDVPL (clean/faults/pass-through/provenance) | Y | N | — | — | N |
| `tests/conftest.py` · `tests/*/conftest.py` · `tests/*/__init__.py` | path setup + markers | Y | N | — | — | N |

## 6. Configuration / setup
| path | purpose | Nec. | Old | Move | Arch. | Exec |
|---|---|---|---|---|---|---|
| `pyproject.toml` | packaging (src layout) + pytest config | Y | N | — | — | Y |
| `.env.example` | `POLYGON_API_KEY` · `DATA_PROVIDER=polygon` · `DATA_FEED=sip` | Y | N | — | — | Y |
| `.gitignore` | ignore caches/db artifacts | Y | N | — | — | N |
| `README.md` (repo root) | entry point / onboarding | Y | N | — | — | N |

## 7. Documentation — `docs/` (authoritative)
| path | purpose | Nec. | Old | Move | Arch. | Exec |
|---|---|---|---|---|---|---|
| `docs/DOCUMENTATION_INDEX.md` | doc entry point | Y | N | — | — | N |
| `docs/Reference/*` (10) | SYSTEM_STATE_LOCK (truth) · PROJECT_STATUS/TREE · REGISTRY · LABEL · GATE · INTEGRITY · MIGRATION · ROADMAP · AUDIT | Y | N | — | — | N |
| `docs/Architecture/*` (3) | ARCHITECTURE_OVERVIEW · DEPENDENCY_MAP · ARCHITECTURE_REVIEW | Y | N | — | — | N |
| `docs/Implementation/*` (2) | MDVPL + Collection-Layer blueprints (active) | Y | N | — | — | N |
| `docs/Operator/*` (4) | OPERATOR_EXECUTION_GUIDE · SIP_SETUP_GUIDE · CALIBRATION_RUNBOOK · DEPLOYMENT_GUIDE | Y | N | — | — | N |
| `docs/Research/*` (3) | PLATFORM_GUIDE · EVENT_RECONSTRUCTION · EVENT_KNOWLEDGE | Y | N | — | — | N |

## 8. Documentation — `docs/Archive/` (historical, NOT authoritative)
| path | purpose | Nec. | Old | Move | Arch. | Exec |
|---|---|---|---|---|---|---|
| `docs/Archive/README.md` | states the archive is non-authoritative | Y | N | — | Y | N |
| `docs/Archive/AURUM_STOCKS_*.md` (15) | original Phase-1 spec, registry/execution/paper designs, freeze package/plan, scanner spec, rubric-frozen, state locks, Priority-2 reports | keep | Y | — | Y | N |
| `docs/Archive/DEMO_calibration_report.md` | synthetic demo output (never freezes label) | keep | Y | — | Y | N |
| `docs/Archive/EVENT_INTELLIGENCE_LAYER.md` · `NEWS_INTELLIGENCE_LAYER.md` | superseded design proposals (EIL/NIL) | keep | Y | — | Y | N |

> All Archive files are **retained on purpose** (history/traceability) and already moved + labelled
> non-authoritative. None should be implemented from.

## 9. Root handoff documents (this task)
| path | purpose |
|---|---|
| `PROJECT_INVENTORY.md` | this inventory |
| `FINAL_PROJECT_TREE.md` | the final tree of every file/folder |
| `IMPLEMENTATION_ROADMAP.md` | all phases in order, with status |
| `NEXT_STEP.md` | the single next action |

## 10. Missing files
**None block the next phase.** The repository is self-contained and hand-off-ready. Optional, non-
blocking additions a production repo *may* want (not present, not required by the architecture):
- `LICENSE` (legal; project-owner's choice).
- `CHANGELOG.md` (release history; currently captured by Archive design packages + git).

No file from any previous conversation is needed: every artifact that was built already exists in
the repository. If a future task needs an input that is genuinely absent, it will be named and
requested before proceeding (per the handoff rules).
