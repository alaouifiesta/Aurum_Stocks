# Calibration Runbook — raw SIP → frozen `LBL_V1`

Edge-blind / feature-blind throughout. **Forbidden** inputs to any decision: Sharpe, AUC, IC,
win-rate, expectancy, or any predictive/edge metric. The full operational package is in
`docs/Archive/AURUM_STOCKS_LBL_V1_FREEZE_PACKAGE.md`; this is the working summary.

## Allowed metrics (the entire permitted set)
Profit% · Stop% · Time% · min-class fraction · normalized entropy · median TTR ·
median barrier÷spread · TB4 sign-split. Nothing else.

## Pre-registered rubric (frozen)
`rubric_hash = 11cf5f1c64319a790e172e104df4878f8c6eecaa50503588b6e89962ed01628c`
- Acceptance: min-class ≥15% ternary/30% binary · entropy ≥0.85 · Time% ∈[15,45]% ·
  barrier÷spread ≥4× (floor 3×) · median TTR ≥5min & ≤0.8·H · |Profit−Stop| ≤10pp.
- Degeneracy: Time%>70% · any class<10% · barrier÷spread<3× · <100 events/cell or /episode.
- Cross-regime stability (decisive): pass acceptance **in every** episode; entropy range ≤0.10,
  Time% range ≤15pp, barrier÷spread ≥3× each episode.
- Tie-break: stability → balance → barrier÷spread → plateau → parsimony.

## Runbook (abbreviated)
0. Pre-register rubric; compute & timestamp `rubric_hash` (**must precede the grid**). ✔ done.
1. Load **SIP** (not IEX) for the pilot window+symbols; verify CA adjustments / clock / spreads.
2. Build PIT universe as-of pilot dates (anti-survivorship).
3. Build HOURLY regimes; confirm ≥3–4 distinct episodes.
4. Register burn window in `CalibrationBurnLedger` (no overlap with collection; buffer ≥1 day).
5. Data-quality pass; mark quarantine segments (missing/outage/CA-anomaly/halt).
6. Sample **setup-blind** events (e.g. 15-min grid), excluding quarantine & halts.
7. Per trigger: PIT ATR(14)@5m; resolve triple-barrier for every `(k,H)` cell.
8. Aggregate **allowed** label-property metrics; flag degenerate cells.
9. Recompute metrics **per regime episode**.
10. Apply rubric (drop degenerate → bands → stability → tie-break) → select `(k,H,TIME)`.
11. Produce `calibration_report`; compute `calibration_report_hash`.
12. Build `LabelSpec(LBL_V1)`; compute `label_spec_hash` (canonical, hash-excluding-self).
13. Record 3 hashes + selection in Label Registry; mark `LBL_V1` immutable (write-once).
14. **Seal** the pilot slice in the burn ledger.
15. Re-run integrity suite + gate verification → `READY_FOR_COLLECTION = TRUE`.

## Failure conditions (abort — never relax bands to force a pass)
Regime diversity <3 episodes · no non-degenerate cell passes · all cells fail stability ·
rubric not pre-registered before step 7 · SIP integrity failure.

## Mock vs real
The framework ships with `SyntheticDataProvider` (self-test only) and a `PolygonDataProvider`
stub. The operator wires a real SIP provider; **no data vendor is reachable from the build
environment**, so the run itself is operator-only. Synthetic numbers must never freeze the label.
