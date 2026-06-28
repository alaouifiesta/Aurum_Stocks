# Gate State

## `READY_FOR_COLLECTION`
Computed by `aurum_stocks.integrity.integrity_suite.ready_for_collection(...)`.
**`READY_FOR_COLLECTION = AND(all conditions)`** — any single FALSE ⇒ FALSE.

| condition | now | after successful freeze |
|---|---|---|
| `LBL_V1_FROZEN` | ✗ FALSE | ✓ TRUE |
| `REGISTRIES_BUILT` | ✓ TRUE | ✓ TRUE |
| `INTEGRITY_SUITE_GREEN` (6/6) | ✓ TRUE | ✓ TRUE |
| `PIT_GATE_OPERATIONAL` | ✓ TRUE | ✓ TRUE |
| `UNIVERSE_REGISTRY_READY` | ✓ TRUE | ✓ TRUE |
| `SCANNER_REGISTRY_READY` | ✓ TRUE | ✓ TRUE |
| burn sealed | ✗ (pilot not run) | ✓ sealed |
| **`READY_FOR_COLLECTION`** | **FALSE** | **TRUE** |

**Single blocker:** `LBL_V1_FROZEN = FALSE` — the SIP calibration run has not been executed.

## Locked condition set
The condition set is locked (GC-13). The data-integrity registries (news/halt/data_quality)
are **built but are not gate conditions** — adding them remains the unratified `GATE1` proposal.

## Other locked flags
| flag | value |
|---|---|
| `RUBRIC_RATIFIED` | TRUE |
| `TRADING_MODE` | PAPER_ONLY (execution track, future) |
| `LIVE_ALLOWED` | FALSE (hardcoded; not changed in Priority #3) |
| `TRADING_DIRECTION` | LONG_ONLY |
| `TRADING_STYLE` | INTRADAY_ONLY |
| `RG1` (regime cadence) | HOURLY |
| Priority #3 | NOT AUTHORIZED |

## `READY_FOR_TRADING` (future, separate gate)
Requires `broker_registry` + an OOS-validated edge. Not in scope for collection.
