# Project Tree

```
aurum-stocks/
├── README.md
├── pyproject.toml                 # src-layout packaging + pytest config
├── run_tests.sh                   # runs the full suite (PYTHONPATH=src)
├── .env.example                   # POLYGON_API_KEY · DATA_PROVIDER=polygon · DATA_FEED=sip
├── .gitignore
│
├── docs/
│   ├── DOCUMENTATION_INDEX.md     # entry point
│   ├── Reference/                 # SYSTEM_STATE_LOCK · PROJECT_* · REGISTRY · LABEL · GATE · INTEGRITY · MIGRATION · ROADMAP · AUDIT
│   ├── Architecture/              # ARCHITECTURE_OVERVIEW · DEPENDENCY_MAP · ARCHITECTURE_REVIEW
│   ├── Implementation/            # MARKET_DATA_VALIDATION_PROVENANCE · COLLECTION_LAYER_ARCHITECTURE (active blueprints)
│   ├── Operator/                  # OPERATOR_EXECUTION_GUIDE · SIP_SETUP_GUIDE · CALIBRATION_RUNBOOK · DEPLOYMENT_GUIDE
│   ├── Research/                  # RESEARCH_PLATFORM_GUIDE · RESEARCH_EVENT_RECONSTRUCTION · RESEARCH_EVENT_KNOWLEDGE
│   └── Archive/                   # historical / NOT authoritative (see Archive/README.md)
│
├── ops/                           # calibration operations (operator scripts)
│   ├── README.md
│   ├── run_lbl_calibration.py     # orchestrate grid run → freeze LBL_V1 (operator-confirmed)
│   └── verify_lbl_freeze.py       # verify freeze hashes + recompute the gate (read-only)
│
├── src/
│   └── aurum_stocks/
│       ├── foundation/            # R1–R4 contracts + feature gate
│       │   ├── dataset_roles.py       # R1  burn ledger + partition assigner
│       │   ├── label_spec.py          # R2  immutable versioned LabelSpec
│       │   ├── pit_harness.py         # R3  lookahead defense
│       │   ├── observation_builder.py # R4  setup-agnostic signed row contract
│       │   ├── pit_gate.py            #     PASS/FAIL/UNKNOWN gate
│       │   └── feature_registry.py    #     admission + lifecycle (+ FeatureClass)
│       ├── registries/            # reference + data-integrity registries
│       │   ├── db.py                  # SQLite schema (DDL) + UTC-ISO helpers
│       │   ├── symbol_registry.py     # SCD-2 PIT, NO-FALLBACK resolver
│       │   ├── regime_registry.py     # HOURLY snapshots
│       │   ├── setup_registry.py      # candidate-source provenance
│       │   ├── scanner_registry.py    # scanner provenance
│       │   ├── universe_registry.py   # versioned membership rules
│       │   ├── data_quality_registry.py  # AS_OF (PIT) vs RETROSPECTIVE
│       │   ├── news_registry.py       # news_available_ts (PIT)
│       │   ├── halt_registry.py       # halt episodes
│       │   ├── microstructure_registry.py # RESERVED
│       │   ├── research_registry.py   # pre-registration manifest + ledger
│       │   └── label_registry.py      # write-once frozen label + 3 hashes
│       ├── calibration/           # triple-barrier label calibration framework
│       │   ├── config.py · barriers.py · metrics.py · grid.py · report.py
│       │   └── data_provider.py       # DataProvider ABC · Synthetic · Polygon(stub)
│       ├── integrity/             # integrity suite + READY_FOR_COLLECTION
│       │   └── integrity_suite.py
│       ├── providers/             # provider ABCs + mocks (news/halt/data-quality)
│       │   └── providers.py
│       ├── scanners/              # RESERVED for Priority #3 (empty by design)
│       └── run_calibration.py     # CLI entry (calibration framework)
│
├── pipeline/                      # runtime data pipeline (post-LBL_V1; isolated from src/)
│   ├── mdvpl/                     # Market Data Validation & Provenance Layer  [IMPLEMENTED]
│   │   ├── source.py             # provider-agnostic MarketDataSource ABC + MockMarketDataSource
│   │   ├── checks.py             # data-quality checks (facts only)
│   │   ├── provenance.py         # append-only ProvenanceRecord + ProvenanceLog
│   │   ├── report.py             # read-only QualityReport
│   │   └── validator.py          # orchestrator (pass-through, no transform)
│   └── run_mdvpl.py              # demo CLI (mock provider; no real API)
│
├── research/                     # read-only research platform (this phase)
│   ├── news/                      # canonical news archive (provenance only) + providers
│   ├── notebooks/                 # research-session recorder + NOTEBOOK_TEMPLATE.md
│   ├── inspector/                 # Observation Inspector
│   ├── explore/                   # Dataset Explorer (counts only)
│   ├── audit/                     # Data Coverage Audit (reporting only)
│   ├── reconstruction/            # Event Reconstruction Layer (factual timelines)
│   ├── knowledge/                 # Event Knowledge Layer (archetypes·graph·query·stats·viz)
│   ├── demo.py                    # synthetic data for tool demos (self-test only)
│   └── run_inspector.py · run_explorer.py · run_audit.py · run_reconstruct.py · run_knowledge.py
│
└── tests/
    ├── conftest.py                # puts src/ on sys.path
    ├── foundation/test_foundation.py
    ├── registries/test_registries.py
    ├── registries/test_data_integrity.py
    ├── calibration/test_barriers.py
    ├── integrity/test_feature_gate_integrity.py
    ├── research/test_research_platform.py · test_reconstruction.py · test_knowledge.py
    └── pipeline/test_mdvpl.py
```

All five test files pass from this layout (`./run_tests.sh`).
