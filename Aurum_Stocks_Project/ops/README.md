# ops/ — calibration operations

Operator scripts for the **future** SIP calibration run. They orchestrate existing modules
only — no architecture, registry, gate, or label logic is defined here.

| script | purpose |
|---|---|
| `run_lbl_calibration.py` | validate SIP env → register burn window → run the calibration grid → write report + `calibration_report_hash` → present candidates → freeze `LBL_V1` **only** on explicit operator `--select … --confirm-freeze` |
| `verify_lbl_freeze.py` | read-only: run integrity suite, verify freeze hashes, recompute `READY_FOR_COLLECTION`. Dry mode (no `--db`) shows the gate is FALSE without creating anything |

## Usage (later, by the operator)
```bash
cp .env.example .env && edit .env          # set POLYGON_API_KEY (DATA_FEED=sip)
python ops/run_lbl_calibration.py \
    --start 2025-01-02 --end 2025-06-30 \
    --symbols-file pilot_symbols.txt --db aurum.sqlite --out calibration_report.md
# review report vs the FROZEN rubric, choose (k,H,TIME), then:
python ops/run_lbl_calibration.py ... --select "k=1.25,H=30,time=TERNARY" --confirm-freeze
python ops/verify_lbl_freeze.py --db aurum.sqlite
```
Synthetic data must never freeze the label. The scripts refuse any feed other than SIP.
