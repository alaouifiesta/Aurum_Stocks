# Research Platform — Operator Manual

A complete manual for an operator who has **never seen this repository before**. It explains
every folder, every script, every command, and every document, then walks the entire lifecycle:

```
empty repository → data collection → label freeze → dataset generation → future model training
```

This phase added a **read-only research platform** (the `research/` area) on top of the existing,
locked production substrate. The research tools **produce evidence only**: they never make trading
decisions, never consume future information, and never create predictive features.

---

## Part A — What is in the repository (every folder)

| folder | what it is | may I run it? |
|---|---|---|
| `src/aurum_stocks/` | the **locked** production substrate (registries, observation builder, PIT gate, integrity, calibration). Do not modify. | indirectly (via tests / ops) |
| `tests/` | the test suites (6 of them) | yes — `./run_tests.sh` |
| `ops/` | operator scripts for the **future** SIP calibration + freeze | yes — when you have SIP |
| `research/` | **new** read-only research platform (this phase) | yes — demo + future analysis |
| `docs/` | all documentation (start at `SYSTEM_STATE_LOCK.md`) | read |
| `docs/Archive/` | historical/architecture design proposals (incl. EIL, NIL) | read |

Inside `research/`:

| subfolder | purpose |
|---|---|
| `research/news/` | the **canonical historical news archive** (provenance only) + provider interfaces/mocks |
| `research/notebooks/` | the **research-session** provenance recorder + a notebook template |
| `research/inspector/` | the **Observation Inspector** (explain one ObservationRow) |
| `research/explore/` | the **Dataset Explorer** (read-only counts) |
| `research/audit/` | the **Data Coverage Audit** (read-only reporting) |
| `research/run_*.py` | thin demo CLIs for the three tools above |
| `research/demo.py` | synthetic data for the demos (self-test only) |

---

## Part B — Every script and command

### Setup (once)
| goal | command |
|---|---|
| Python 3.11+ check | `python --version` |
| Create/activate venv | `python -m venv .venv && source .venv/bin/activate` |
| Install deps | `pip install -e .` (adds `pandas`, `numpy`) |
| Live SIP run later | `pip install requests` |

### Tests
| goal | command | expected |
|---|---|---|
| Run all suites | `./run_tests.sh` | six `... PASSED` blocks |
| Pytest variant | `PYTHONPATH=src:. pytest` | all green |

### Calibration (synthetic dry run — proves the machinery, never freezes the label)
| goal | command |
|---|---|
| Synthetic calibration | `PYTHONPATH=src python src/aurum_stocks/run_calibration.py --demo --days 12 --out ./calibration_out` |

### Operator calibration + freeze (needs real SIP — see `SIP_SETUP_GUIDE.md`)
| goal | command |
|---|---|
| Real calibration | `python ops/run_lbl_calibration.py --start <d> --end <d> --symbols-file pilot_symbols.txt --db aurum.sqlite --out calibration_report.md` |
| Freeze `LBL_V1` | add `--select "k=<k>,H=<H>,time=<TERNARY>" --confirm-freeze` to the above |
| Verify the freeze + gate | `python ops/verify_lbl_freeze.py --db aurum.sqlite` |

### Research platform (read-only)
| tool | command (demo) | what it shows |
|---|---|---|
| Observation Inspector | `python research/run_inspector.py --demo [--index N]` | every field of one ObservationRow + why it passes/fails |
| Dataset Explorer | `python research/run_explorer.py --demo` | counts per regime/setup/symbol/month/universe/label |
| Data Coverage Audit | `python research/run_audit.py --demo` | duplicates, orphans, signature/PIT/long-only checks, coverage |

> The research CLIs currently support `--demo` (synthetic) because **no observation store exists
> yet** — collection has not begun. Once collection produces observations, the same library
> functions accept the real rows.

### Research session (provenance recorder — use inside any analysis)
```python
import sys, os
sys.path.insert(0, os.path.abspath(".")); sys.path.insert(0, os.path.abspath("src"))
from research.notebooks import ResearchSession
with ResearchSession.open(hypothesis_id="H#001", dataset_version="ds-2025Q1") as s:
    print(s.manifest())     # records hashes, label version, timestamp to ./research_log
```

---

## Part C — Every document (what to read, in order)

| document | purpose |
|---|---|
| `docs/Reference/SYSTEM_STATE_LOCK.md` | **source of truth** — gate, locks, build status |
| `docs/DOCUMENTATION_INDEX.md` | index of all docs |
| `docs/Reference/PROJECT_TREE.md` | full repository tree |
| `docs/Architecture/ARCHITECTURE_OVERVIEW.md` | the five production layers |
| `docs/Reference/REGISTRY_REFERENCE.md` | every registry |
| `docs/Reference/LABEL_SYSTEM.md` · `docs/Operator/CALIBRATION_RUNBOOK.md` | the label and how it is frozen |
| `docs/Reference/INTEGRITY_SUITE.md` · `docs/Reference/GATE_STATE.md` | the collection gate |
| `docs/Operator/SIP_SETUP_GUIDE.md` · `docs/Operator/DEPLOYMENT_GUIDE.md` | data + environment |
| `docs/Operator/OPERATOR_EXECUTION_GUIDE.md` | the 8-phase execution guide (validate → … → collection readiness) |
| `docs/Research/RESEARCH_PLATFORM_GUIDE.md` | **this manual** — the research platform + full lifecycle |
| `docs/Architecture/DEPENDENCY_MAP.md` · `docs/Reference/MIGRATION_INVENTORY.md` | internals |
| `docs/Reference/FINAL_REPOSITORY_AUDIT.md` | last full audit (PASS) — *historical snapshot; not current state* |
| `docs/Archive/EVENT_INTELLIGENCE_LAYER.md`, `…/NEWS_INTELLIGENCE_LAYER.md` | future-layer designs (proposals) |

---

## Part D — The complete lifecycle (empty repository → future model training)

### Stage 1 — Empty repository → green
**Goal:** a healthy copy.
**Do:** `./run_tests.sh` → expect **9 green suites**; current state is in `docs/Reference/SYSTEM_STATE_LOCK.md` / `docs/Reference/PROJECT_STATUS.md` (the audit file is a historical snapshot, not the current-state source).
**Result:** you trust the code.

### Stage 2 — Environment + data access
**Goal:** be able to fetch real **SIP** data.
**Do:** venv + `pip install -e . requests`; `cp .env.example .env` and set `POLYGON_API_KEY`
(keep `DATA_FEED=sip`); acquire a Polygon/Massive plan with historical NBBO quotes; validate the
feed (see `SIP_SETUP_GUIDE.md`).
**Result:** real consolidated data in hand.

### Stage 3 — Label freeze (unblocks collection)
**Goal:** turn `READY_FOR_COLLECTION` from FALSE to TRUE.
**Do:** run `ops/run_lbl_calibration.py` on a pilot window spanning 3–4 regime episodes; review the
report against the frozen rubric; freeze with `--select … --confirm-freeze`; verify with
`ops/verify_lbl_freeze.py --db aurum.sqlite`.
**Result:** `LBL_V1` frozen (write-once, three hashes); the gate opens.
> This is the **only** blocker today. Everything in Stage 4+ depends on it.

### Stage 4 — Data collection
**Goal:** accumulate immutable, PIT-correct **observations** under the frozen label.
**Do:** collection runs per the ratified build order (Collection → Accumulation). Every candidate
becomes one fully-signed `ObservationRow` (6 signed reference versions). **News, halts, and
corporate actions are recorded as historical truth** — the `research/news/` archive is where the
canonical news provenance lives (provenance only; no features).
**Result:** a growing, immutable observation set + a news archive.

### Stage 5 — Inspect and audit while collecting (research platform)
**Goal:** prove the dataset is clean as it grows — produce **evidence**, not decisions.
**Do:**
- **Inspector** — examine individual rows: `research/run_inspector.py` (or `inspect_row(row)`):
  confirms each row's 6 signed versions, signature, PIT (`data_as_of ≤ signal`), and long-only.
- **Explorer** — counts: `research/run_explorer.py` (or `dataset_explorer.summary(rows)`):
  how many observations, per regime/setup/symbol/month/universe/label.
- **Audit** — coverage/integrity: `research/run_audit.py` (or `coverage_audit.render_report(...)`):
  duplicate observations, orphan/missing registry references, signature/PIT/long-only failures,
  regime/symbol/label/month coverage, and **news coverage** (a statistic, never a feature).
**Result:** documented confidence that the dataset is complete, signed, and PIT-correct.

### Stage 6 — Dataset generation
**Goal:** a versioned, reproducible research dataset.
**Do:** derive research frames from the immutable observations (deterministic rebuild). Open a
**ResearchSession** so the dataset version + registry/label hashes + timestamp are recorded for
every analysis. Pre-register each hypothesis in the Research Registry **before** any OOS look.
**Result:** a dataset tagged with provenance, ready for study — **still no features, no models**.

### Stage 7 — Future model training (separate, authorized phase)
**Goal:** (future) build predictive features / models.
**Boundary:** this is **out of scope now** and requires explicit authorization. When authorized,
any feature/model enters through the existing discovery path: Feature Registry admission, PIT
proof, pre-registered hypothesis, OOS, FDR, Vault. Raw news/event text is consumed only via the
additive annotation seam — never as a privileged feature. **Nothing in the current research
platform performs training.**

---

## Part E — Hard guarantees of this phase (restated)
- **Read-only / evidence-only.** The inspector, explorer, and audit never write production data;
  the news archive is append-only; the research session writes only to its own log.
- **No future information.** The only availability key anywhere is `news_available_ts` /
  `data_as_of_ts ≤ signal_ts`. Post-event/forward data is never an input here.
- **No predictive features, no scores, no sentiment, no labels** — the news archive and all tools
  store and report provenance and counts only.
- **No gate change.** `READY_FOR_COLLECTION = FALSE` is unchanged; the research platform does not
  touch it, the Integrity Suite, `LBL_V1`, calibration, or any frozen hash.

## Part F — Status
Research infrastructure is in place and tested (6/6 suites green). The system still waits on the
single operator action — the SIP calibration run to freeze `LBL_V1` (Stage 3). After that, the
research platform is ready to inspect, explore, and audit the collected dataset. **Do not proceed
toward execution or machine learning without explicit authorization.**
