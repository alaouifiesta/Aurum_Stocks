# Label System

The label is the **truth-definition** for discovery. It is frozen once (`LBL_V1`) on
label-property grounds only, then immutable forever.

## Triple-barrier (the measuring instrument, not a trade plan)
- `ATR_sig = ATR(14)@5-min`, **PIT** (only buckets closed before entry).
- `profit_barrier = ref ± k·ATR_sig`, `stop_barrier = ref ∓ k·ATR_sig` — **symmetric**,
  volatility-scaled (measures directional predictability cleanly; RR optimization is later).
- `time_barrier = signal_ts + H`, **capped at RTH close** (intraday-only; no overnight).
- Path evaluated on **1-min** bars; **STOP-first** tie-break (pessimistic) when a bar spans both.
- Embargo `H + 1` bar.

## Locked vs calibrated
| locked (not calibrated) | calibrated (frozen once) |
|---|---|
| ATR(14)@5m PIT · 1-min path · STOP-first · symmetric barriers · RTH-close cap · embargo H+1 | `k` (multiplier) · `H` (horizon) · TIME encoding |

## Outcome primitives vs label function
Primitives (always collected, immutable): `barrier_hit{PROFIT,STOP,TIME}`, exit ts/price,
bars-to-exit, MFE, MAE, realized return, path min/max, halt_affected. The label function maps
primitives → label; `PROFIT→+1`, `STOP→−1`, TIME per the chosen encoding. Both encodings are
derivable from primitives, so TIME is the cheapest item to defer.

## Calibration (how `k/H/TIME` are chosen)
On a **burned** pilot slice, **feature-blind and edge-blind**, using only label-property
metrics (hit distribution, balance/entropy, TTR, barrier÷spread, TB4 sign-split). No Sharpe /
AUC / IC / win-rate / expectancy ever. The pre-registered rubric (frozen, hashed) decides;
cross-regime stability is the decisive criterion. Full procedure: `CALIBRATION_RUNBOOK.md`.

## LabelSpec (frozen structure) — `registries/label_registry.py`
`label_spec_id · spec_version · k · H_minutes · time_encoding · atr_spec · path_eval ·
tie_break · time_cap · embargo · rubric_hash · calibration_report_hash · label_spec_hash ·
burn_ledger_ref`.

## Immutability (FD-1)
`LBL_V1` is **write-once** and immutable forever. Any recalibration produces a **new**
`LBL_V2` (new spec + new hashes) — never an edit. Observations always reference the
`label_spec_id` they were built under, so changing the label never rewrites history.

## Current state
`LBL_V1` does **not** exist yet. `RUBRIC_RATIFIED = TRUE` and `rubric_hash` is frozen
(`11cf5f1c64319a79…`). The Label Registry is the empty write-once mechanism, awaiting the SIP
calibration run.
