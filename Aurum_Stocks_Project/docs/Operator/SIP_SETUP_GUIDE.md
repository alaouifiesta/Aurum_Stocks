# SIP Setup Guide

How to obtain and validate the data required to freeze `LBL_V1`. Calibration **requires
consolidated SIP data** — this is not optional.

## SIP vs IEX
- **SIP (Securities Information Processor)** = the *consolidated tape*: every trade and the
  National Best Bid/Offer (NBBO) aggregated across **all** US exchanges. It reflects true
  market volume and the true bid-ask spread.
- **IEX** = a *single venue* carrying only a small share of total volume. Volume, RVOL, and
  spread computed from IEX alone are **distorted**.
- Why it matters here: the calibration **barrier ÷ spread** guard depends on a *true*
  consolidated spread, and RVOL/$-volume need true consolidated volume. Calibrating on IEX
  would set the label on distorted microstructure. **The scripts refuse any feed but SIP.**

## Polygon requirements
The reference provider is Polygon.io (Stocks). For historical calibration you need:
- **Consolidated (SIP) coverage**, not a single-exchange feed.
- **Historical minute aggregates** (for ATR(14)@5-min and 1-min path evaluation).
- **Historical trades and quotes (NBBO)** — required to compute a true spread for the
  barrier÷spread guard.
- Enough **historical depth** to cover a pilot window spanning ≥3–4 HOURLY regime episodes.
- Real-time streaming is **not** required (calibration is historical).

## Supported Polygon plans
Plan names, limits, and pricing change over time, so **verify the current tier on
polygon.io/pricing** before subscribing. Choose a Stocks plan whose features include:
full **historical trades + quotes (NBBO)**, **minute aggregates**, and **consolidated SIP**
coverage with sufficient history. Free/most-basic tiers are typically delayed and/or limited
to aggregates without full historical NBBO and are **not sufficient** for the spread guard.
Confirm the plan exposes historical quotes before purchase.

## API key configuration
1. `cp .env.example .env`
2. Set values (only these three keys exist):
   ```
   POLYGON_API_KEY=<your key>
   DATA_PROVIDER=polygon
   DATA_FEED=sip
   ```
3. The ops scripts read these from the environment and **abort** if `DATA_FEED != sip`,
   `DATA_PROVIDER != polygon`, or the key is empty.

## Historical SIP validation procedure
Before trusting the feed, validate (this is runbook step 1):
1. **Consolidated check** — daily volume for a few liquid names matches known consolidated
   totals (orders of magnitude above any single venue). If volume looks ~2–5% of expected,
   you are on a single-venue feed, not SIP.
2. **Spread sanity** — NBBO spreads are positive, finite, and small for liquid names; the
   median barrier÷spread is computable and ≥ 3×.
3. **Clock / DST** — timestamps are ET with correct DST; session boundaries (RTH) align.
4. **Corporate-action adjustment** — splits/dividends correctly adjusted; spot-check a known
   split so returns/gaps are not fabricated.
5. **Halt cross-check** — a known LULD/volatility halt appears with sensible start/end.
Record any failures; quarantine affected segments (do not delete).

## Calibration execution procedure
```bash
python ops/run_lbl_calibration.py \
    --start <YYYY-MM-DD> --end <YYYY-MM-DD> \
    --symbols-file pilot_symbols.txt --db aurum.sqlite --out calibration_report.md
```
This registers the burn window, runs the grid (label-property metrics only), writes the
report, and prints `calibration_report_hash`. Review the non-degenerate candidate cells
against the **frozen** rubric (`docs/Operator/CALIBRATION_RUNBOOK.md`,
`rubric_hash = 11cf5f1c64319a79…`). Then freeze with your chosen cell:
```bash
python ops/run_lbl_calibration.py ... --select "k=<k>,H=<H>,time=<TERNARY|SIGNED_AT_H|CENSORED>" --confirm-freeze
```

## `LBL_V1` freeze verification procedure
```bash
python ops/verify_lbl_freeze.py --db aurum.sqlite
```
Confirms: integrity 6/6 GREEN · `label_spec_hash` recomputes · `rubric_hash` matches the
frozen value · `calibration_report_hash` present · burn sealed → prints
`READY_FOR_COLLECTION`. Exit code 0 only when the gate is TRUE.
