# Final Project Tree

> Generated from the actual filesystem. Every file and folder in the repository.
> Authoritative state: `docs/Reference/SYSTEM_STATE_LOCK.md`. Historical/non-authoritative: `docs/Archive/`.

```
aurum-stocks/
├── .env.example
├── .gitignore
├── FINAL_PROJECT_TREE.md
├── PROJECT_INVENTORY.md
├── README.md
├── docs
│   ├── Architecture
│   │   ├── ARCHITECTURE_OVERVIEW.md
│   │   ├── ARCHITECTURE_REVIEW.md
│   │   ├── DEPENDENCY_MAP.md
│   ├── Archive
│   │   ├── AURUM_STOCKS_BUILD_INTEGRATION_ADDENDUM.md
│   │   ├── AURUM_STOCKS_DATA_INTEGRITY_REGISTRIES.md
│   │   ├── AURUM_STOCKS_EXECUTION_ARCHITECTURE.md
│   │   ├── AURUM_STOCKS_FINAL_DIRECTIVES_LOCK.md
│   │   ├── AURUM_STOCKS_LBL_V1_FREEZE_PACKAGE.md
│   │   ├── AURUM_STOCKS_LBL_V1_FREEZE_PLAN.md
│   │   ├── AURUM_STOCKS_PAPER_EXECUTION_ARCHITECTURE.md
│   │   ├── AURUM_STOCKS_PHASE1_SPEC.md
│   │   ├── AURUM_STOCKS_PRIORITY2_BUILD_INCREMENT.md
│   │   ├── AURUM_STOCKS_PRIORITY2_ENGINEERING_REPORT.md
│   │   ├── AURUM_STOCKS_REGISTRY_DESIGN.md
│   │   ├── AURUM_STOCKS_RUBRIC_FROZEN.md
│   │   ├── AURUM_STOCKS_SCANNER_SPEC.md
│   │   ├── AURUM_STOCKS_STATE_LOCK.md
│   │   ├── DEMO_calibration_report.md
│   │   ├── EVENT_INTELLIGENCE_LAYER.md
│   │   ├── NEWS_INTELLIGENCE_LAYER.md
│   │   ├── README.md
│   ├── DOCUMENTATION_INDEX.md
│   ├── Implementation
│   │   ├── COLLECTION_LAYER_ARCHITECTURE.md
│   │   ├── MARKET_DATA_VALIDATION_PROVENANCE.md
│   ├── Operator
│   │   ├── CALIBRATION_RUNBOOK.md
│   │   ├── DEPLOYMENT_GUIDE.md
│   │   ├── OPERATOR_EXECUTION_GUIDE.md
│   │   ├── SIP_SETUP_GUIDE.md
│   ├── Reference
│   │   ├── FINAL_REPOSITORY_AUDIT.md
│   │   ├── GATE_STATE.md
│   │   ├── INTEGRITY_SUITE.md
│   │   ├── LABEL_SYSTEM.md
│   │   ├── MIGRATION_INVENTORY.md
│   │   ├── PROJECT_STATUS.md
│   │   ├── PROJECT_TREE.md
│   │   ├── REGISTRY_REFERENCE.md
│   │   ├── ROADMAP.md
│   │   ├── SYSTEM_STATE_LOCK.md
│   ├── Research
│   │   ├── RESEARCH_EVENT_KNOWLEDGE.md
│   │   ├── RESEARCH_EVENT_RECONSTRUCTION.md
│   │   ├── RESEARCH_PLATFORM_GUIDE.md
├── ops
│   ├── README.md
│   ├── run_lbl_calibration.py
│   ├── verify_lbl_freeze.py
├── pipeline
│   ├── __init__.py
│   ├── mdvpl
│   │   ├── __init__.py
│   │   ├── checks.py
│   │   ├── provenance.py
│   │   ├── report.py
│   │   ├── source.py
│   │   ├── validator.py
│   ├── run_mdvpl.py
├── pyproject.toml
├── research
│   ├── __init__.py
│   ├── audit
│   │   ├── __init__.py
│   │   ├── coverage_audit.py
│   ├── demo.py
│   ├── explore
│   │   ├── __init__.py
│   │   ├── dataset_explorer.py
│   ├── inspector
│   │   ├── __init__.py
│   │   ├── observation_inspector.py
│   ├── knowledge
│   │   ├── __init__.py
│   │   ├── archetypes.py
│   │   ├── graph.py
│   │   ├── query.py
│   │   ├── stats.py
│   │   ├── viz.py
│   ├── news
│   │   ├── __init__.py
│   │   ├── archive.py
│   │   ├── providers.py
│   │   ├── records.py
│   ├── notebooks
│   │   ├── NOTEBOOK_TEMPLATE.md
│   │   ├── __init__.py
│   │   ├── research_session.py
│   ├── reconstruction
│   │   ├── __init__.py
│   │   ├── detectors.py
│   │   ├── engine.py
│   │   ├── timeline.py
│   ├── run_audit.py
│   ├── run_explorer.py
│   ├── run_inspector.py
│   ├── run_knowledge.py
│   ├── run_reconstruct.py
├── run_tests.sh
├── src
│   ├── aurum_stocks
│   │   ├── __init__.py
│   │   ├── calibration
│   │   │   ├── README.md
│   │   │   ├── __init__.py
│   │   │   ├── barriers.py
│   │   │   ├── config.py
│   │   │   ├── data_provider.py
│   │   │   ├── grid.py
│   │   │   ├── metrics.py
│   │   │   ├── report.py
│   │   ├── foundation
│   │   │   ├── __init__.py
│   │   │   ├── dataset_roles.py
│   │   │   ├── feature_registry.py
│   │   │   ├── label_spec.py
│   │   │   ├── observation_builder.py
│   │   │   ├── pit_gate.py
│   │   │   ├── pit_harness.py
│   │   ├── integrity
│   │   │   ├── __init__.py
│   │   │   ├── integrity_suite.py
│   │   ├── providers
│   │   │   ├── __init__.py
│   │   │   ├── providers.py
│   │   ├── registries
│   │   │   ├── __init__.py
│   │   │   ├── data_quality_registry.py
│   │   │   ├── db.py
│   │   │   ├── halt_registry.py
│   │   │   ├── label_registry.py
│   │   │   ├── microstructure_registry.py
│   │   │   ├── news_registry.py
│   │   │   ├── regime_registry.py
│   │   │   ├── research_registry.py
│   │   │   ├── scanner_registry.py
│   │   │   ├── setup_registry.py
│   │   │   ├── symbol_registry.py
│   │   │   ├── universe_registry.py
│   │   ├── run_calibration.py
│   │   ├── scanners
│   │   │   ├── __init__.py
├── tests
│   ├── calibration
│   │   ├── __init__.py
│   │   ├── test_barriers.py
│   ├── conftest.py
│   ├── foundation
│   │   ├── __init__.py
│   │   ├── test_foundation.py
│   ├── integrity
│   │   ├── __init__.py
│   │   ├── test_feature_gate_integrity.py
│   ├── pipeline
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── test_mdvpl.py
│   ├── registries
│   │   ├── __init__.py
│   │   ├── test_data_integrity.py
│   │   ├── test_registries.py
│   ├── research
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── test_knowledge.py
│   │   ├── test_reconstruction.py
│   │   ├── test_research_platform.py
```

## Top-level map
- `src/aurum_stocks/` — frozen production substrate (foundation · registries · calibration · integrity · providers · scanners).
- `pipeline/` — runtime data pipeline (mdvpl IMPLEMENTED; collection/store/dataset_builder pending).
- `research/` — read-only research platform (news · notebooks · inspector · explore · audit · reconstruction · knowledge).
- `ops/` — operator calibration scripts (freeze/verify LBL_V1).
- `tests/` — 9 suites (one per area).
- `docs/` — Reference · Architecture · Implementation · Operator · Research · Archive.
- root — README · pyproject.toml · run_tests.sh · .env.example · .gitignore · PROJECT_INVENTORY · FINAL_PROJECT_TREE · IMPLEMENTATION_ROADMAP · NEXT_STEP.
