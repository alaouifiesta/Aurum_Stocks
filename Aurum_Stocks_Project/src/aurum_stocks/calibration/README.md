# Aurum Stocks — Calibration Framework (Phase 1, Priority #1)

Single purpose: **decide the Triple-Barrier label definition** — `TB2` (ATR
multiplier *k*), `TB3` (time horizon *H*), `TB4` (TIME-outcome encoding) — on
**label-property grounds only**, before any official Observation dataset exists.

This closes the last open item blocking `v1.0-FROZEN` in the Phase-1 spec.

## What it does NOT do
No setups, no features, no ranking, no correlation, no AUC, no Sharpe, no ML, no
strategy testing. It is feature-blind by construction. It will not even pick a
"winner" — it presents label properties and flags which cells pass the
Calibration Protocol guards; **the final choice is yours, on real data.**

## Frozen rules it enforces (spec v1.0-RC2 §4)
- ATR(14) on 5-minute bars, computed **point-in-time** (only buckets closed
  before entry; the entry bar and everything after are invisible to ATR).
- Symmetric, volatility-scaled barriers: `ref ± k·ATR`.
- Barrier touches evaluated on **1-minute** bars.
- Tie-break **STOP_FIRST**: one bar spanning both barriers → STOP.
- Time barrier `H`, **capped at RTH close** (no cross-session holds).

## Metrics reported per (k, H) cell — the allowed list only
Profit % · Stop % · Time % · Median Time-To-Resolution · Barrier Distance vs
Typical Spread · Class Balance (min-class fraction + normalized entropy).
Plus a **TB4 hint**: sign split of horizon-end returns for TIME outcomes (a pure
label property, to inform ternary-vs-sign encoding — never feature predictiveness).

A cell is flagged **degenerate** (`*`) if it fails a guard: `time% > 70%`, any
class `< 10%`, or median `barrier/spread < 3×`.

## Run the demo (synthetic data, no network)
```bash
PYTHONPATH=. python aurum_stocks/run_calibration.py --demo --days 12 --out ./calibration_out
PYTHONPATH=. python aurum_stocks/tests/test_barriers.py   # sanity checks
```
Synthetic output is for **self-test only** — it proves the machine works. Do not
freeze TB2/TB3/TB4 from synthetic numbers.

## The real run (your environment — this makes the decision)
1. `pip install requests` and create a `requests.Session`.
2. Build a real provider:
   ```python
   import requests, datetime as dt
   from aurum_stocks.calibration import config, grid, report
   from aurum_stocks.calibration.data_provider import PolygonDataProvider

   provider = PolygonDataProvider(api_key="...", session=requests.Session())
   dates = [...]  # real SIP trading days spanning MULTIPLE regimes (see note)
   result = grid.run_grid(provider, config.SYMBOLS, dates)
   open("calibration_report.md", "w").write(report.render_markdown(result))
   ```
3. **Use SIP data**, not IEX — RVOL/spread/volume on a single-exchange feed are
   distorted, and the barrier/spread guard depends on a true spread.
4. **Span multiple regime episodes** in your date range. A label that looks
   balanced inside one quiet regime can be degenerate in another; calibrating on
   a single regime repeats the gold-project mistake.

## How to choose (label-property grounds only)
Among **non-degenerate** cells, prefer:
- High class balance (entropy near 1.0, no class starved).
- `barrier/spread` comfortably above 3× (the barrier is real, not noise).
- A median TTR consistent with the kind of move you intend to study later
  (this is a horizon choice, not a performance claim).
- Stability: pick a cell sitting in a **plateau** of balanced neighbours, not a
  lone balanced cell surrounded by degenerate ones.

Then freeze `(k, H, TIME-encoding)` as `label_spec v1`, record it as an
`INSTRUMENT_CALIBRATION` entry in the research registry, and **seal/burn the
calibration data** so it never re-enters discovery.

## Files
```
aurum_stocks/
  calibration/
    config.py          frozen TB constants + grids + symbols + guard thresholds
    data_provider.py   DataProvider ABC · SyntheticDataProvider · PolygonDataProvider(stub)
    barriers.py        PIT ATR + one-scan-per-entry triple-barrier resolution
    metrics.py         label-property aggregation (allowed metrics only)
    grid.py            (k,H) grid orchestration
    report.py          markdown + JSON rendering
  run_calibration.py   CLI entrypoint
  tests/test_barriers.py  tie-break · horizon cap · PIT ATR · monotonicity
```
