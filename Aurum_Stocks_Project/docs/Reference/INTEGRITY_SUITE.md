# Integrity Suite

`src/aurum_stocks/integrity/integrity_suite.py` runs the mandatory checks against a live
registry set and computes `READY_FOR_COLLECTION`. **A single RED ⇒ gate FALSE.** This gate
outranks any feature. Current status: **6/6 GREEN**.

## Checks
| # | check | proves |
|---|---|---|
| 1 | `pit_lookup` | symbol/regime resolvers return the version valid at `as_of`; never a future version |
| 2 | `burn_isolation` | a burned (CALIBRATION_ONLY) slice never enters a pipeline partition; `assert_no_calibration_leak` fires |
| 3 | `version_signing` | every row carries 6 signed reference versions; `data_as_of ≤ signal_ts` |
| 4 | `anti_survivorship` | PIT universe includes later-delisted names, excludes pre-IPO names |
| 5 | `rebuild_determinism` | identical inputs → identical signature; a later symbol version does not change an old row's resolution |
| 6 | `completeness_audit` (GC-2/9) | every candidate in a scan batch yields an observation (`batch_size == observation_count`) |

## API
- `run_suite() -> list[Check]` — runs all six against a fresh in-memory registry set.
- `render(checks) -> str` — human-readable GREEN/RED report.
- `ready_for_collection(*, lbl_v1_frozen, registries_built, pit_gate_operational,
  universe_ready, scanner_ready, checks) -> dict` — computes the gate (all conditions AND).

## Relationship to the gate
`INTEGRITY_SUITE_GREEN` is one of the `READY_FOR_COLLECTION` conditions (see `GATE_STATE.md`).
It does **not** include `LBL_V1_FROZEN`; that is a separate condition currently FALSE.

## How to run
`./run_tests.sh` (the integrity test lives at `tests/integrity/test_feature_gate_integrity.py`)
or, programmatically, `from aurum_stocks.integrity import integrity_suite as I; I.run_suite()`.
