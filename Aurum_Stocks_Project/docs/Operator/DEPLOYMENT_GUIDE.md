# Deployment Guide

Environment setup for running tests and the future calibration. No execution/trading
system is deployed (Priority #3 is not authorized).

## 1. Python
Python **3.11+**. Verify:
```bash
python --version    # 3.11 or newer
```

## 2. Virtual environment
```bash
cd aurum-stocks
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
```

## 3. Dependencies
```bash
pip install -e .                   # uses pyproject.toml (src layout)
# or minimally:
pip install pandas numpy
# for the live SIP calibration run only:
pip install requests
```

## 4. Run tests
```bash
./run_tests.sh                     # runs all five suites
# or:
PYTHONPATH=src pytest              # pyproject sets pythonpath=src, testpaths=tests
```
Expected: every suite reports `ALL … PASSED`.

## 5. Run calibration (operator, with real SIP)
```bash
cp .env.example .env               # set POLYGON_API_KEY, DATA_FEED=sip
python ops/run_lbl_calibration.py --start <d> --end <d> \
    --symbols-file pilot_symbols.txt --db aurum.sqlite --out calibration_report.md
python ops/verify_lbl_freeze.py --db aurum.sqlite
```
See `SIP_SETUP_GUIDE.md` and `CALIBRATION_RUNBOOK.md`. The build environment has no vendor
access, so this step is operator-only.

## 6. Database backup & restore
Registries persist to a single SQLite file (the `--db` path, e.g. `aurum.sqlite`). It is the
system of record once `LBL_V1` is frozen and collection begins.

**Backup (consistent, while in use):**
```bash
sqlite3 aurum.sqlite ".backup 'aurum.backup.sqlite'"
# or, when no process is writing:
cp aurum.sqlite aurum.backup.$(date +%Y%m%d).sqlite
```

**Restore:**
```bash
cp aurum.backup.sqlite aurum.sqlite      # replace the working DB with a backup
sqlite3 aurum.sqlite "PRAGMA integrity_check;"   # verify
```

**Notes**
- Append-only / write-once invariants (symbol SCD-2, research/experiment/label) are enforced
  in code; back up the file **before** any calibration freeze so the pre-freeze state is
  recoverable.
- The burn ledger and frozen `LBL_V1` are immutable by design — keep at least one backup of
  the post-freeze DB as the canonical reference.
- WAL mode is enabled; a `.backup` (above) captures a consistent snapshot including WAL.
