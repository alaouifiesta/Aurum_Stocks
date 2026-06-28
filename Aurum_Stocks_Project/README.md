# Aurum Stocks — Phase 1 (Edge-Discovery Substrate)

US small-cap ($2–$20), **long-only, intraday-only** quantitative **edge-discovery** substrate.
Not a trading bot: it turns every candidate signal into a statistically valid, point-in-time,
fully version-signed observation row. Discovery > optimization · Data > models · Evidence > beliefs.

> **Status:** `READY_FOR_COLLECTION = FALSE` — single blocker `LBL_V1_FROZEN = FALSE`
> (SIP calibration run not executed). Integrity 6/6 GREEN. Priority #3 NOT authorized.
> Authoritative status: [`docs/Reference/SYSTEM_STATE_LOCK.md`](docs/Reference/SYSTEM_STATE_LOCK.md).

## Layout (src layout)
```
src/aurum_stocks/{foundation,registries,calibration,integrity,providers,scanners}
tests/{foundation,registries,calibration,integrity}
ops/    (operator calibration scripts)
docs/   (start at Reference/SYSTEM_STATE_LOCK.md; full index in DOCUMENTATION_INDEX.md)
.env.example
```
Full tree: [`docs/Reference/PROJECT_TREE.md`](docs/Reference/PROJECT_TREE.md).

## Run the tests
```bash
./run_tests.sh           # or: PYTHONPATH=src pytest
```
All five suites pass. (Python ≥3.11, pandas, numpy.)

## Operate the future SIP calibration
Set up data and run per [`docs/Operator/SIP_SETUP_GUIDE.md`](docs/Operator/SIP_SETUP_GUIDE.md) and
[`docs/Operator/DEPLOYMENT_GUIDE.md`](docs/Operator/DEPLOYMENT_GUIDE.md):
```bash
cp .env.example .env     # POLYGON_API_KEY, DATA_FEED=sip
python ops/run_lbl_calibration.py --start <d> --end <d> --symbols-file pilot_symbols.txt --db aurum.sqlite
python ops/verify_lbl_freeze.py --db aurum.sqlite
```

## Read in this order (new-engineer onboarding)
1. `docs/Reference/SYSTEM_STATE_LOCK.md` — where things stand (source of truth).
2. `docs/Architecture/ARCHITECTURE_OVERVIEW.md` — the five layers.
3. `docs/Reference/REGISTRY_REFERENCE.md` — every registry.
4. `docs/Reference/LABEL_SYSTEM.md` + `docs/Operator/CALIBRATION_RUNBOOK.md` — the truth-definition and how it's frozen.
5. `docs/Reference/INTEGRITY_SUITE.md` + `docs/Reference/GATE_STATE.md` — the collection gate.
6. `docs/Architecture/DEPENDENCY_MAP.md` + `docs/Reference/MIGRATION_INVENTORY.md` — internals.
7. `IMPLEMENTATION_ROADMAP.md` — **the operational phase roadmap (single reference)**; `docs/Reference/ROADMAP.md` gives priority context only.

## Non-negotiable contracts
LONG_ONLY · INTRADAY_ONLY · PAPER_ONLY (future) · Research Firewall (execution data never
feeds features) · Full-Population Observation (every candidate observed) · NO-FALLBACK
resolvers · immutable, hash-identified label. No code path may route around these.
