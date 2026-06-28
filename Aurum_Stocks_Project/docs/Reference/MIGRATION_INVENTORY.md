# Migration Inventory

Schema defined in `src/aurum_stocks/registries/db.py` (`DDL` list, applied by
`init_schema`). SQLite; UTC-ISO timestamps; append-only by discipline.

## Existing migrations
A `migrations` ledger table exists (`migration_id, applied_at, description, tables,
reversible`). **No migrations have been recorded yet** — the initial schema is created in one
pass by `init_schema()`. The first recorded migration should be the initial baseline when the
repo is put under a migration tool.

## Registry tables (created by `init_schema`)
| table | registry / purpose | PIT key |
|---|---|---|
| `symbol_registry` | symbol SCD-2 | `valid_from` |
| `short_interest_snapshot` | symbol companion (PIT short interest) | `as_of` |
| `market_regime_registry` | HOURLY regime snapshots | `regime_ts` |
| `setup_registry` | candidate-source provenance | (active version) |
| `scanner_registry` | scanner provenance | (active version) |
| `universe_registry` | versioned membership rules | `valid_from` |
| `broker_registry` | paper-execution provenance (execution track) | (active version) |
| `data_quality_registry` | AS_OF (PIT) + RETROSPECTIVE quality | `as_of` / `session_date` |
| `news_registry` | news provenance | `news_available_ts` |
| `halt_registry` | halt episodes | `halt_start_ts` |
| `microstructure_registry` | RESERVED (L2/order-flow) | — |
| `research_hypothesis` | pre-registration manifest | — |
| `experiment_ledger` | append-only run log | — |
| `label_registry` | write-once frozen label + 3 hashes | — |
| `migrations` | migration ledger | — |

15 tables total.

## Pending tables
**None.** Every approved Priority-#2 table is created. Future tables are explicitly **out of
current scope**:
- Execution track (Priority #3): `execution_store`, `paper_trade_journal`, fills/events — not
  yet defined as DDL; gated behind `READY_FOR_TRADING`.
- Microstructure detail tables: deferred until the reserved track is populated.

## Notes for a migration tool
- All tables use `CREATE TABLE IF NOT EXISTS`; adopting Alembic/yoyo should record the current
  schema as baseline `0001_initial`.
- Append-only invariants (symbol SCD-2, research/experiment/label write-once) are enforced in
  **code**, not by DB constraints alone — preserve this when adding migrations.
