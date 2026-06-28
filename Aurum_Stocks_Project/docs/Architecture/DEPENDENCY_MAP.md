# Dependency Map

Major subsystems, their internal dependencies, and consumers. (External: `pandas`, `numpy`,
`sqlite3` (stdlib). No network; no data-vendor dependency in code — only via provider ABCs.)

| module / subsystem | depends on | used by |
|---|---|---|
| `foundation.dataset_roles` (R1) | — | observation_builder, integrity_suite, calibration freeze |
| `foundation.label_spec` (R2) | — | observation_builder (label id), label freeze |
| `foundation.pit_harness` (R3) | pandas | pit_gate, tests |
| `foundation.observation_builder` (R4) | dataset_roles, pandas | all registry resolvers (implement its ports), integrity_suite |
| `foundation.pit_gate` | pit_harness | feature_registry, tests |
| `foundation.feature_registry` | pit_gate | (discovery phase), tests |
| `registries.db` | pandas, sqlite3 | every registry, integrity_suite |
| `registries.symbol_registry` | db, observation_builder (ports) | observation_builder, universe_registry, integrity_suite |
| `registries.regime_registry` | db, observation_builder (ports) | observation_builder, integrity_suite |
| `registries.setup_registry` | db, observation_builder (ports) | observation_builder, integrity_suite |
| `registries.scanner_registry` | db, observation_builder (ports) | observation_builder, integrity_suite |
| `registries.universe_registry` | db, observation_builder (ports), symbol_registry (data) | observation_builder, integrity_suite |
| `registries.data_quality_registry` | db | (collection-time flagging), tests |
| `registries.news_registry` | db | (NEWS_MOMENTUM source, future), tests |
| `registries.halt_registry` | db | (as-of halt status), tests |
| `registries.microstructure_registry` | db | RESERVED (none yet) |
| `registries.research_registry` | db | (discovery phase), tests |
| `registries.label_registry` | db | calibration freeze, gate verification |
| `calibration.*` (barriers/metrics/grid/report/config) | data_provider, pandas, numpy | run_calibration, label freeze |
| `calibration.data_provider` | pandas | calibration grid, freeze (real SIP wired by operator) |
| `integrity.integrity_suite` | foundation.*, registries.* | gate verification, tests |
| `providers.providers` | pandas | data-integrity registries (feed), tests |
| `scanners` | — | RESERVED (Priority #3) |
| `ops/run_lbl_calibration.py` | calibration.*, dataset_roles (burn), registries.db, label_registry, requests (operator) | operator (entry point) |
| `ops/verify_lbl_freeze.py` | integrity.integrity_suite, registries.db, label_registry | operator (read-only verify) |
| `pipeline.mdvpl.source` | abc, datetime, zoneinfo | mdvpl.validator, adapters (vendor-specific, future) |
| `pipeline.mdvpl.checks` | datetime, math | mdvpl.validator |
| `pipeline.mdvpl.provenance` | sqlite3 | mdvpl.validator (append-only log) |
| `pipeline.mdvpl.report` | mdvpl.checks | mdvpl.validator |
| `pipeline.mdvpl.validator` | mdvpl.{source,checks,provenance,report}, hashlib, json | (collection layer, future) |
| `research.reconstruction.*` (RERL) | duck-typed bar source | research.knowledge, tests |
| `research.knowledge.*` (REKL) | research.reconstruction (Timeline) | tests |
| `research.{inspector,explore,audit,news,notebooks}` | foundation.observation_builder, registries.{db,label_registry} (read-only) | operator research tooling, tests |

## Layered dependency direction (no cycles)
```
db ─┐
    ├─> registries.* ─┐
foundation.ports ─────┤
                      ├─> integrity.integrity_suite
foundation.{dataset_roles,label_spec} ┘
foundation.pit_harness ─> pit_gate ─> feature_registry
calibration.data_provider ─> calibration.* ─> (label freeze)
providers ─> registries.data-integrity (feed only)
```
Foundation never imports registries; registries import only foundation **ports/exceptions**;
integrity sits on top of both. This is why `integrity_suite` lives in its own package (it
depends on `..registries`, which would otherwise create a cycle if kept inside `foundation`).
