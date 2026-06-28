# Operator Execution Guide

A step-by-step guide to take Aurum Stocks from a fresh copy of the repository all the way to
`READY_FOR_COLLECTION = TRUE`. Written for a **non-developer operator** — you do not need to
understand the architecture. Follow the phases in order. Do not skip ahead.

**What this guide does NOT do:** it does not change any code, registry, label, or gate, and it
does not start Priority #3 (trading/execution). It only tells you which commands to run.

### Conventions
- Lines in `code boxes` are commands. Type them exactly, then press Enter.
- Run every command from the **repository root** — the folder that contains `README.md`,
  `src/`, `tests/`, `ops/`, and `docs/`. The guide calls this folder `aurum-stocks/`.
- `<like-this>` means "replace with your own value."
- A **frozen reference** you will see repeatedly:
  `rubric_hash = 11cf5f1c64319a790e172e104df4878f8c6eecaa50503588b6e89962ed01628c`.

### The 8 phases at a glance
1. Repository Validation → 2. Environment Setup → 3. SIP Preparation →
4. Polygon Integration → 5. Calibration Dry Run → 6. Real SIP Calibration →
7. Post-Freeze Verification → 8. Collection Readiness.

---

## PHASE 1 — Repository Validation
**Goal:** confirm you have a complete, healthy copy of the repository before doing anything else.

### Checklist
- [ ] Inspected the key files.
- [ ] Confirmed the repository is complete.
- [ ] Ran all tests — all green.
- [ ] Confirmed the audit verdict is PASS.

### Step 1.1 — Inspect the key files
- **Objective:** know where you are and what state the project is in.
- **Files to open and read (in this order):**
  - `README.md` — overview and the current status banner.
  - `docs/Reference/SYSTEM_STATE_LOCK.md` — the single source of truth (gate, locks, build status).
  - `docs/Reference/PROJECT_STATUS.md` — current status (tests, gate, build).
  - `IMPLEMENTATION_ROADMAP.md` — the operational phase roadmap (single reference).
  - `docs/DOCUMENTATION_INDEX.md` — what every other document is for.
- **Commands:**
  ```bash
  ls
  cat README.md
  ```
- **Expected result:** you see folders `src docs tests ops` and files `README.md
  pyproject.toml run_tests.sh .env.example`. The README status line says
  `READY_FOR_COLLECTION = FALSE`, blocker `LBL_V1_FROZEN = FALSE`.
- **Troubleshooting:** if folders are missing, your copy is incomplete — re-download/extract the
  full repository and start again.

### Step 1.2 — Verify completeness
- **Objective:** confirm the source, tests, ops, and docs are all present.
- **Commands:**
  ```bash
  find src tests ops -name '*.py' | wc -l
  ls docs/*.md | wc -l
  ```
- **Expected result:** the first number is in the low 40s (around 34 source files + 5 tests +
  2 ops); the docs count is 16 or more.
- **Troubleshooting:** a very low count means files are missing — re-extract the repository.

### Step 1.3 — Run all tests
- **Objective:** prove the code works on your machine. (Requires Phase 2 done first if Python
  is not yet installed — if `python` is not found, do Phase 2, then return here.)
- **Commands:**
  ```bash
  ./run_tests.sh
  ```
- **Expected result:** five blocks print, each ending in `... PASSED`:
  `ALL TESTS PASSED`, `ALL FOUNDATION TESTS PASSED`, `ALL FEATURE-GATE / INTEGRITY TESTS
  PASSED`, `ALL DATA-INTEGRITY TESTS PASSED`, `ALL REGISTRY TESTS PASSED`.
- **Troubleshooting:**
  - `permission denied` → run `bash run_tests.sh` instead.
  - `No module named pandas/numpy` → do Phase 2 step 2.3 (install dependencies).
  - `python: command not found` → do Phase 2 step 2.1.

### Step 1.4 — Verify current health
- **Objective:** confirm the repository is green right now (the audit file is only a historical snapshot).
- **Commands:**
  ```bash
  ./run_tests.sh        # expect 9 green suites
  ```
- **Expected result:** all suites green; current state in `docs/Reference/SYSTEM_STATE_LOCK.md`.
- **Troubleshooting:** if it does not say PASS, stop and report it — do not proceed to a real
  calibration on a repository that failed audit.

---

## PHASE 2 — Environment Setup
**Goal:** a clean, isolated Python environment that runs the tests cleanly.

### Checklist
- [ ] Python 3.11+ installed.
- [ ] Virtual environment created and activated.
- [ ] Dependencies installed.
- [ ] `.env` created and filled in.
- [ ] Environment health confirmed.

### Step 2.1 — Install Python
- **Objective:** have Python 3.11 or newer.
- **Commands:**
  ```bash
  python --version
  ```
- **Expected result:** `Python 3.11.x` or higher.
- **Troubleshooting:** if missing or older, install from https://www.python.org/downloads/
  (Windows/macOS) or your system package manager (Linux). On some systems the command is
  `python3` — if so, use `python3` everywhere below.

### Step 2.2 — Create and activate a virtual environment
- **Objective:** keep this project's packages separate from the rest of your computer.
- **Commands:**
  ```bash
  python -m venv .venv
  source .venv/bin/activate        # Windows: .venv\Scripts\activate
  ```
- **Expected result:** your prompt now shows `(.venv)` at the start.
- **Troubleshooting:** on Windows PowerShell, if activation is blocked, run
  `Set-ExecutionPolicy -Scope Process RemoteSigned` then retry the activate command.

### Step 2.3 — Install dependencies
- **Objective:** install the libraries the project needs.
- **Commands:**
  ```bash
  pip install -e .
  pip install requests          # needed only for the real SIP run (Phase 4+)
  ```
- **Expected result:** pip finishes with `Successfully installed ...` and no red errors.
- **Troubleshooting:** if `pip install -e .` fails, run `pip install pandas numpy requests`
  instead — that is sufficient.

### Step 2.4 — Configure `.env`
- **Objective:** create your private settings file. It has exactly three keys.
- **Commands:**
  ```bash
  cp .env.example .env
  ```
  Then open `.env` in a text editor and set your Polygon key:
  ```
  POLYGON_API_KEY=<your-polygon-api-key>
  DATA_PROVIDER=polygon
  DATA_FEED=sip
  ```
- **Expected result:** `.env` exists with your key filled in. Leave `DATA_PROVIDER=polygon` and
  `DATA_FEED=sip` exactly as shown.
- **Troubleshooting:** you do not have a key yet? That is fine for Phases 1–2 and the Phase 5
  dry run. You need it before Phase 4. Never commit `.env` to version control (it is in
  `.gitignore`).

### Step 2.5 — Verify the environment is healthy
- **Objective:** confirm everything is wired up.
- **Commands:**
  ```bash
  python -c "import pandas, numpy; print('libs OK')"
  ./run_tests.sh
  ```
- **Expected result:** `libs OK`, then five `... PASSED` blocks.
- **Troubleshooting:** any failure here repeats a Phase-2 step above — re-check Python version,
  activation (`(.venv)` visible), and dependency install.

---

## PHASE 3 — SIP Preparation
**Goal:** make sure you can obtain the correct market data. Calibration is only valid on
**consolidated SIP** data. (Full background: `docs/Operator/SIP_SETUP_GUIDE.md`.)

### Checklist
- [ ] Understood exactly what SIP data is required.
- [ ] Confirmed your Polygon plan covers it.
- [ ] Verified SIP availability with a live test.
- [ ] Validated historical data quality.

### Step 3.1 — What SIP data is required
- **Objective:** know precisely what to buy and fetch.
- **You need, historically (not just live):**
  - **1-minute aggregate bars** (open/high/low/close/volume) — used for ATR and the price path.
  - **NBBO quotes (bid/ask)** — used to compute the true spread. The calibration uses a
    **barrier ÷ spread** quality guard, so a *real* spread matters.
  - **Consolidated SIP coverage** — all US exchanges combined, not a single venue.
  - **Enough history** to cover a pilot window that spans **3–4 distinct hourly regime
    episodes** (typically several months), for small-cap names priced **$2–$20**.
- **Expected result:** you can state "I have historical 1-minute SIP aggregates and NBBO
  quotes covering <dates>." If you cannot, you are not ready for Phase 6.

### Step 3.2 — Required Polygon subscription level
- **Objective:** pick a plan that actually includes the above.
- **What to require:** a Polygon **Stocks** plan that provides historical **aggregates** *and*
  historical **quotes (NBBO)** with **consolidated** coverage and enough history depth.
  The most basic/free tiers are delayed and usually lack full historical NBBO — **not
  sufficient**.
- **Commands:** none (this is a purchasing decision).
- **Expected result:** before subscribing, confirm on **https://polygon.io/pricing** (plan
  names and limits change over time) that your chosen plan lists historical trades/quotes and
  consolidated data.
- **Troubleshooting:** unsure if a plan includes quotes? Ask Polygon support directly, or test
  the quotes endpoint on a trial before committing.

### Step 3.3 — Verify SIP availability (live test)
- **Objective:** prove your key can fetch real bars.
- **Commands** (replace the date with a recent trading day):
  ```bash
  python - <<'PY'
  import os, requests
  key=os.environ.get("POLYGON_API_KEY") or open(".env").read().split("POLYGON_API_KEY=")[1].split()[0]
  u="https://api.polygon.io/v2/aggs/ticker/AAPL/range/1/minute/2025-06-02/2025-06-02"
  r=requests.get(u, params={"adjusted":"true","sort":"asc","limit":50,"apiKey":key}, timeout=30)
  print("HTTP", r.status_code, "| results:", len(r.json().get("results",[])))
  PY
  ```
- **Expected result:** `HTTP 200 | results: <a few hundred>`.
- **Troubleshooting:**
  - `HTTP 401/403` → bad key or your plan lacks this data.
  - `HTTP 429` → rate-limited; wait and retry, or upgrade plan.
  - `results: 0` → wrong/holiday date, or no history on your plan; try another trading day.

### Step 3.4 — Validate historical SIP data quality
- **Objective:** make sure the data is real consolidated SIP, not distorted.
- **Checks (do these for a handful of liquid and a few small-cap names):**
  1. **Volume sanity** — daily volume is in the expected consolidated range (single-venue data
     looks ~2–5% of expected).
  2. **Spread sanity** — bid/ask spreads are positive, finite, and small for liquid names.
  3. **Clock / DST** — timestamps are US-Eastern with correct daylight-saving handling.
  4. **Corporate actions** — spot-check a known split so returns/gaps are not fake.
  5. **Halt cross-check** — a known halt day shows sensible behavior.
- **Commands:** use the live test in 3.3 on several symbols/days and eyeball the numbers.
- **Expected result:** all five look right. Note any segment that looks wrong — you will
  **quarantine** (exclude) it later, never delete it.
- **Troubleshooting:** systematically tiny volumes ⇒ you are on a single-venue feed, not SIP —
  fix the plan/endpoint before continuing.

---

## PHASE 4 — Polygon Integration
**Goal:** make the data provider return real SIP data with a real spread. You are *filling in
the provided adapter*, not changing the architecture.

### Checklist
- [ ] Understood the provider interface.
- [ ] Wired the provider with your key and (recommended) real NBBO quotes.
- [ ] Tested the provider on one symbol/day.
- [ ] Ran the required validation checks.
- [ ] Reviewed the failure scenarios.

### Step 4.1 — How to replace the `PolygonDataProvider` stub
- **Objective:** turn the shipped adapter into a fully real one.
- **The file:** `src/aurum_stocks/calibration/data_provider.py`. The calibration engine only
  needs one method:
  `get_minute_bars(symbol, date)` → a table indexed by Eastern-time minute timestamps with
  columns `open, high, low, close, volume, bid, ask`, including the pre-market warm-up, and an
  **empty** table if the symbol did not trade that day.
- **What is already done for you:** `PolygonDataProvider` already fetches the 1-minute
  aggregates from Polygon and fills `open/high/low/close/volume`. You construct it with your key
  and a network session (the Phase-6 script does this automatically).
- **What you should improve (recommended):** the shipped adapter derives bid/ask from a simple
  **spread model** when you have not supplied real quotes. For a trustworthy
  barrier-÷-spread metric, supply the **real NBBO** instead, one of two ways:
  - **(a) Simplest:** pass a `spread_model` you trust (a function of price) when the provider is
    constructed, if you have a good empirical model.
  - **(b) Best:** extend `get_minute_bars` to also call Polygon's quotes endpoint
    (`/v3/quotes/{symbol}`) and set `bid`/`ask` from the per-minute NBBO.
- **Important:** keep the method name, inputs, and the seven output columns exactly the same.
  Do not change anything outside this provider. If you only have aggregates (no quotes), you may
  proceed with a spread model, but record that the spread is modeled, not measured.
- **Expected result:** `get_minute_bars` returns real bars (and, ideally, real NBBO spreads).
- **Troubleshooting:** if unsure about endpoint shapes, confirm against current Polygon docs —
  the adapter's comments name the endpoints it uses.

### Step 4.2 — Test the provider
- **Objective:** confirm one real fetch returns a well-formed table.
- **Commands** (replace symbol/date):
  ```bash
  PYTHONPATH=src python - <<'PY'
  import os, datetime as dt, requests
  from aurum_stocks.calibration.data_provider import PolygonDataProvider
  key=os.environ["POLYGON_API_KEY"]
  p=PolygonDataProvider(api_key=key, session=requests.Session())
  df=p.get_minute_bars("MGNI", dt.date(2025,6,2))
  print("rows:", len(df))
  print("columns:", list(df.columns))
  print("timezone:", df.index.tz)
  print(df.head(3))
  PY
  ```
- **Expected result:** non-zero `rows`; `columns` = `['open','high','low','close','volume',
  'bid','ask']`; `timezone` shows `America/New_York`; the first rows include pre-market minutes.
- **Troubleshooting:** see the failure scenarios in 4.4.

### Step 4.3 — Required validation checks
- **Objective:** the four things that must be true before real calibration.
- **Confirm:**
  1. Columns are exactly the seven required, in a tz-aware **Eastern** index.
  2. The pre-market warm-up is present (rows before 9:30 ET) so ATR is "warm" at the open.
  3. `volume` matches consolidated expectations (not a single venue).
  4. `bid < ask` and `ask - bid > 0` for normal minutes.
- **Expected result:** all four hold on several test symbols/days.
- **Troubleshooting:** a failing check points to the matching fix in 4.1 (columns/quotes) or 3.2
  (plan/coverage).

### Step 4.4 — Failure scenarios (and what they mean)
- **Empty table for a day that traded** → wrong date format, a market holiday, or your plan
  lacks that history. Try another trading day; verify plan depth.
- **`401/403`** → key invalid or plan does not include this data.
- **`429 Too Many Requests`** → you are fetching too fast; add pauses or upgrade.
- **Spreads all identical / suspiciously smooth** → you are using the modeled spread, not real
  NBBO; wire quotes (4.1b) for full fidelity.
- **Tiny volumes everywhere** → single-venue feed, not consolidated SIP; fix before Phase 6.

---

## PHASE 5 — Calibration Dry Run (synthetic)
**Goal:** prove the whole calibration machinery runs end-to-end **without** real data. This is
plumbing only. **Synthetic numbers must never freeze the label.**

### Checklist
- [ ] Ran the synthetic calibration.
- [ ] Found the expected output files.
- [ ] Confirmed the run succeeded.

### Step 5.1 — Execute the synthetic run
- **Objective:** generate a demo calibration report from synthetic data.
- **Commands:**
  ```bash
  PYTHONPATH=src python src/aurum_stocks/run_calibration.py --demo --days 12 --out ./calibration_out
  ```
- **Expected result:** the screen prints metric tables (Profit% / Stop% / Time% / entropy / TTR
  / barrier÷spread / TB4 sign split) and finishes with `Wrote report to ./calibration_out/`.
- **Troubleshooting:** `No module named ...` → re-activate `.venv` and re-run Phase 2.3.

### Step 5.2 — Expected outputs
- **Objective:** know what good output looks like.
- **Commands:**
  ```bash
  ls calibration_out
  head -20 calibration_out/calibration_report.md
  ```
- **Expected result:** two files — `calibration_report.md` (human-readable tables) and
  `calibration_result.json` (raw grid). The report's top line clearly says **SYNTHETIC / DEMO —
  do not use to freeze**.

### Step 5.3 — Verify success
- **Objective:** confirm the dry run is healthy.
- **What "success" means here:** the command finished without errors and produced the two files
  with populated metric tables. **It does NOT mean any cell is "the answer"** — synthetic data
  cannot decide the label.
- **Troubleshooting:** empty tables or a crash means the framework or environment is broken —
  re-run Phase 1.3 and Phase 2.5 before going further.

---

## PHASE 6 — Real SIP Calibration
**Goal:** run the real calibration on SIP data and freeze `LBL_V1`. This is the one
irreversible step — take a backup first.

### Checklist
- [ ] Backed up (there is nothing to lose yet, but establish the habit).
- [ ] Prepared the pilot symbol list and window.
- [ ] Ran the calibration (burn registered, report + hash produced).
- [ ] Reviewed candidates against the frozen rubric.
- [ ] Froze `LBL_V1` with your explicit selection.

### Step 6.1 — Prepare inputs
- **Objective:** define the pilot window and symbols.
- **Commands:** create a plain-text file `pilot_symbols.txt`, one ticker per line, e.g.:
  ```
  MGNI
  PLUG
  RIG
  ```
  Choose a `--start`/`--end` window that spans **3–4 distinct hourly regime episodes**.
- **Expected result:** `pilot_symbols.txt` exists; you know your start/end dates.
- **Troubleshooting:** too few symbols or too short a window → not enough events per cell;
  widen both (the rubric requires ≥100–300+ symbols and several months in practice).

### Step 6.2 — Run the calibration (this also registers the burn ledger)
- **Objective:** run the grid on real data and capture the report.
- **Commands:**
  ```bash
  python ops/run_lbl_calibration.py \
      --start <YYYY-MM-DD> --end <YYYY-MM-DD> \
      --symbols-file pilot_symbols.txt \
      --db aurum.sqlite \
      --out calibration_report.md
  ```
- **What happens (in plain terms):**
  - It checks your `.env` and **refuses to run unless `DATA_FEED=sip`**.
  - **Burn ledger registration:** it records your pilot window+symbols as a "burned" slice.
    Burned data is used to *choose* the label and is then **excluded from real collection
    forever**, so the label is never tested on the same data that defined it.
  - It runs the grid and writes `calibration_report.md`.
  - **Report generation:** it prints a `calibration_report_hash` — a fingerprint of the report.
- **Expected result:** steps `[1/6]…[6/6]` print; the report file is written; you see
  `calibration_report_hash = <64 hex chars>` and the frozen `rubric_hash`. **No freeze happens
  yet.**
- **Troubleshooting:**
  - `ABORT: DATA_FEED must be 'sip'` → fix `.env`.
  - `POLYGON_API_KEY is empty` → set it in `.env`.
  - A network/HTTP error → revisit Phase 4.

### Step 6.3 — Rubric verification (you decide, by the rules set in advance)
- **Objective:** pick the winning `(k, H, TIME)` cell using the **pre-registered, frozen**
  rubric — never by "what looks profitable."
- **How:** open `calibration_report.md`. Apply, in order (full detail in
  `docs/Operator/CALIBRATION_RUNBOOK.md`):
  1. Drop **degenerate** cells (marked, or failing the guards).
  2. Keep cells meeting the **acceptance bands** (balance, entropy, Time%, barrier÷spread, TTR,
     symmetry).
  3. Require **cross-regime stability** — the cell must pass in **every** episode (this is
     decisive).
  4. Break ties: stability → balance → barrier÷spread → plateau → simpler (smaller H).
  - Confirm the report's rubric fingerprint equals the frozen value:
    `11cf5f1c64319a790e172e104df4878f8c6eecaa50503588b6e89962ed01628c`.
- **Expected result:** exactly one `(k, H, TIME)` selection, justified by the rubric.
- **Troubleshooting:** **no** cell passes? That is a valid outcome — **do not relax the bands.**
  Widen the pilot (more symbols/episodes), recheck data quality, and re-run. The label stays
  unfrozen until a cell legitimately passes.

### Step 6.4 — Freeze `LBL_V1`
- **Objective:** lock the chosen label permanently.
- **Commands** (use your selected values):
  ```bash
  python ops/run_lbl_calibration.py \
      --start <YYYY-MM-DD> --end <YYYY-MM-DD> \
      --symbols-file pilot_symbols.txt \
      --db aurum.sqlite \
      --out calibration_report.md \
      --select "k=<k>,H=<H>,time=<TERNARY|SIGNED_AT_H|CENSORED>" \
      --confirm-freeze
  ```
- **Expected result:** it prints `LBL_V1 FROZEN (write-once)` with three fingerprints
  (`label_spec_hash`, `calibration_report_hash`, `rubric_hash`) and seals the burn.
- **Troubleshooting:**
  - You change your mind later? You **cannot** edit `LBL_V1`. A future re-calibration becomes a
    new `LBL_V2`; `LBL_V1` is immutable by design.
  - Made a mistake before freezing? Just re-run 6.2/6.3 — nothing is locked until
    `--confirm-freeze` succeeds. Back up `aurum.sqlite` once the freeze is done.

---

## PHASE 7 — Post-Freeze Verification
**Goal:** confirm the freeze is valid and the collection gate has flipped.

### Checklist
- [ ] Ran `verify_lbl_freeze.py` against the database.
- [ ] Integrity suite is 6/6 GREEN.
- [ ] `READY_FOR_COLLECTION` is TRUE.

### Step 7.1 — Run the verifier
- **Objective:** one command that checks everything.
- **Commands:**
  ```bash
  python ops/verify_lbl_freeze.py --db aurum.sqlite
  ```
- **Expected result:** it prints the integrity report, the freeze checks, the gate conditions,
  and finally `READY_FOR_COLLECTION = True`.
- **Troubleshooting:** `LBL_V1 not found` → the freeze in 6.4 did not complete; re-run it and
  confirm you used the same `--db` path.

### Step 7.2 — Integrity suite verification
- **Objective:** confirm the structural safety checks pass.
- **What to look for:** the block ending in `6/6 GREEN` — the six checks are PIT lookup, burn
  isolation, version signing, anti-survivorship, rebuild determinism, completeness audit.
- **Expected result:** `6/6 GREEN`. Any `RED` means stop and report.
- **Troubleshooting:** a RED check indicates a data/registry problem — do **not** start
  collection; capture the output and escalate.

### Step 7.3 — `READY_FOR_COLLECTION` verification
- **Objective:** confirm the gate opened.
- **What to look for:** every condition shows `OK`, especially `LBL_V1_FROZEN = True`, and the
  final line reads `READY_FOR_COLLECTION = True`. (The command's exit code is `0` only when the
  gate is TRUE.)
- **Expected result:** `READY_FOR_COLLECTION = True`.
- **Troubleshooting:** if it still says `False`, read which condition shows `XX` — it will be
  `LBL_V1_FROZEN`; return to Phase 6.4.

---

## PHASE 8 — Collection Readiness
**Goal:** understand precisely what has changed, and what is still forbidden.

### Checklist
- [ ] Confirmed all gate conditions are TRUE.
- [ ] Understood what remains prohibited.

### Step 8.1 — Conditions that must be TRUE
- **Objective:** know the exact bar for "collection enabled."
- **All of these must read TRUE** (verifier output, Phase 7):
  - `LBL_V1_FROZEN` — the only one that was FALSE before; flips TRUE on a valid freeze.
  - `REGISTRIES_BUILT`, `INTEGRITY_SUITE_GREEN`, `PIT_GATE_OPERATIONAL`,
    `UNIVERSE_REGISTRY_READY`, `SCANNER_REGISTRY_READY` — already TRUE.
  - Burn slice **sealed**.
- **Expected result:** `READY_FOR_COLLECTION = TRUE`. Collection may now begin.

### Step 8.2 — What remains prohibited after collection is enabled
- **Objective:** stay inside the guardrails. Enabling **collection** does **not** enable
  trading.
- **Still forbidden / still locked:**
  - **No live trading.** The system is PAPER-only; live is hard-disabled. Collection is
    research data only.
  - **No Priority #3** (execution/scanner logic/ML/trading) unless and until it is separately
    authorized; it is out of scope here.
  - **Long-only and intraday-only** remain structural — no shorting, no overnight holds.
  - **The two firewalls hold:** execution/outcome data never becomes a feature; research and
    execution stay separated.
  - **Every candidate is still observed** (full-population observation) — collection does not
    cherry-pick.
  - **The label is frozen.** Do not attempt to "tweak" `LBL_V1`; any change is a brand-new
    `LBL_V2` via a fresh calibration.
  - **Do not edit frozen artifacts or the burned slice**, and keep a backup of the post-freeze
    `aurum.sqlite`.
- **Expected result:** you operate collection within all the locks above.
- **Troubleshooting:** if any task seems to require breaking one of these rules, stop — it is
  out of scope for the operator and must be escalated, not worked around.

---

## One-page command summary
```bash
# Phase 1–2
./run_tests.sh
python -m venv .venv && source .venv/bin/activate
pip install -e . && pip install requests
cp .env.example .env            # set POLYGON_API_KEY; keep DATA_FEED=sip

# Phase 5 (synthetic dry run)
PYTHONPATH=src python src/aurum_stocks/run_calibration.py --demo --days 12 --out ./calibration_out

# Phase 6 (real SIP → freeze)
python ops/run_lbl_calibration.py --start <d> --end <d> --symbols-file pilot_symbols.txt --db aurum.sqlite --out calibration_report.md
python ops/run_lbl_calibration.py --start <d> --end <d> --symbols-file pilot_symbols.txt --db aurum.sqlite --out calibration_report.md --select "k=<k>,H=<H>,time=<TERNARY>" --confirm-freeze

# Phase 7 (verify)
python ops/verify_lbl_freeze.py --db aurum.sqlite
```

**Remember:** synthetic never freezes the label · the rubric is fixed in advance · never relax
the bands · `LBL_V1` is permanent · collection is not trading.
