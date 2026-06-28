# Architecture Review (Report Only)

> **Scope:** review of the existing design only. **No code was modified, no file moved, no API
> changed, no registry/feature/gate/layer added.** This is an engineering report. It ends with a
> **Design-Only** specification for a proposed `Research Dataset Builder` (no implementation).

## 0. Verdict
**The architecture is sound.** The layering is clean and acyclic, the production substrate is
frozen and tested (Integrity 6/6, 8/8 suites green), and the additive research layers are correctly
read-only and firewalled. The findings below are **refinements and forward-looking scalability
notes**, not defects that block anything. `READY_FOR_COLLECTION = FALSE` (single blocker
`LBL_V1_FROZEN`) is unaffected by anything here.

---

## 1. Layer-by-layer review

| layer | files / LOC | single responsibility | assessment |
|---|---|---|---|
| **Foundation** | 7 / ~792 | contracts R1–R4 + PIT gate + feature-registry admission | Clean. Defines ports; imports nothing upward. The home of `ObservationRow` and `registry_signature` — the correct dependency sink. |
| **Registries** | 13 / ~1200 | reference + data-integrity PIT stores | Largest layer, as expected. Uniform pattern (db + per-registry module). One shared `db.py` (DDL) — good. Watch growth (see 3.7). |
| **Calibration** | 7 / ~634 | decide the label on label-property grounds | Self-contained; owns its own `DataProvider`. Correctly isolated from discovery. |
| **Integrity** | 2 / ~218 | 6 checks + `READY_FOR_COLLECTION` | Correctly sits *above* foundation+registries (own package to avoid a cycle). Good. |
| **Providers** | 2 / ~70 | news/halt/data-quality ABCs + mocks | Thin and correct. (Naming overlap noted in 2.4.) |
| **Research** | inspector/explore/audit/news/notebooks (~694) | read-only tooling over rows/news | Correctly additive, read-only. Couples to prod only via `ObservationRow` + `label_registry.get` (read-only). |
| **Reconstruction (RERL)** | 4 / ~352 | factual event timelines from PIT bars | Decoupled via duck-typed `get_minute_bars`. Forbidden-key guard structural. Good. |
| **Knowledge (REKL)** | 6 / ~451 | archetypes·graph·query·stats·viz over timelines | Deterministic, descriptive-only, guarded. Builds only on RERL `Timeline`. Good. |

**Dependency direction (verified, acyclic):**
`foundation.ports → registries → integrity`; `calibration` standalone; research/RERL/REKL depend
*downward only* on `aurum_stocks.foundation.observation_builder` (4×), `calibration.data_provider`
(2×, demo), `registries.{db,label_registry}` (1× each, read-only). No upward or cyclic edges.
REKL depends only on RERL; RERL depends on nothing in research except its own `Timeline`.

---

## 2. Findings — duplication, coupling, separable responsibilities

### 2.1 News provenance is modelled in two places (mild, intentional, but worth a seam)
`registries/news_registry.py` (prod, lean: `news_available_ts`, `publish_ts`, headline **hash**,
delay) and `research/news/records.py` (richer: vendor, tickers, language, session, dedup) both
model news provenance. This is **intentional** (lean PIT index vs raw archive) and matches the NIL
design, **but** the two field sets are defined independently. *Refinement (no action now):* when
the news archive is eventually built for real, define one canonical provenance field-set and have
the registry index project a subset of it — so the two never drift. Today: acceptable.

### 2.2 Two "bar source" contracts express the same shape
`get_minute_bars(symbol, date) -> OHLCV` exists as the calibration `DataProvider` ABC, and RERL
re-uses the *same shape* by duck typing (it does not import the ABC, by design, to stay decoupled).
This is **not harmful** (duck typing is deliberate), but the contract is now relied on in two
places without a shared, named protocol. *Refinement:* a tiny shared `BarSource` Protocol (typing
only) could document the contract once. Low priority; not a defect.

### 2.3 `ObservationBuilder.BarSource` vs calibration `DataProvider` — similar but distinct
Foundation declares its own `BarSource` port (`bars_as_of(symbol, signal_ts) -> (bars, data_as_of)`)
which is **semantically different** from calibration's `get_minute_bars(symbol, date)` (PIT-as-of
vs whole-day). These are correctly *not* merged — different responsibilities. No duplication;
flagged only to confirm the distinction is intentional.

### 2.4 The word "provider"/"Provider" is overloaded across four modules
`calibration.data_provider`, `providers.providers`, RERL bar source, `research/news/providers`. All
are legitimately different abstractions, but the shared name invites confusion for a new engineer.
*Refinement (doc-only):* a one-line glossary distinguishing them. No code change.

### 2.5 Coupling is minimal and correct
The only research→prod coupling is reading `ObservationRow`/`registry_signature` and one read-only
`label_registry.get`. There is **no unnecessary coupling**: research never imports integrity,
calibration internals (beyond the demo provider), or any writer. This is the desired shape.

### 2.6 Separable responsibility already well-honoured
Detection (RERL detectors), representation (`Timeline`), and knowledge (REKL) are cleanly separated;
each is independently testable. No responsibility currently spans layers improperly.

---

## 3. Findings — scalability, performance, organisation, testability, maintainability

### 3.1 Millions of observations — the in-memory iterables are the main scaling limit
`dataset_explorer`, `coverage_audit`, REKL `stats`/`query`/`archetypes` all take **in-memory
iterables/lists** of rows or timelines (some call `list(...)` internally). That is perfect for
inspection and for thousands of rows, but **will not scale to millions** held at once. *This is the
single most important forward-looking item.* The eventual fix is a **streaming / chunked** or
**query-pushdown-to-store** access pattern (operate over the SQLite/observation store, not a Python
list). No action now (no store exists yet) — but the future Dataset Builder (§5) should establish
the streaming contract so REKL/explorer can consume batches.

### 3.2 REKL relationship graph is O(n²) per timeline
`build_graph` compares all event pairs for `SAME_MINUTE`/`WITHIN`. Fine for the ~30–80-event
timelines seen in the demo; **quadratic** if a timeline ever holds thousands of events. *Refinement:*
when needed, bound it with a sliding window over time-sorted events (linear for `WITHIN_W`). Not a
defect at current sizes.

### 3.3 Registries: single-file SQLite + write-once-in-code invariants
Append-only/write-once is enforced in **code**, not DB constraints, and everything lives in one
SQLite file. At millions of rows this is a **collection-store** concern (the registries themselves
stay small — symbol/regime/setup versions). *Forward note:* the **observation store** (not yet
built) is where row volume lands; it should be designed for partitioning by date/partition and for
append-only at the storage layer, with backups before any freeze (already in `DEPLOYMENT_GUIDE`).

### 3.4 Performance: VWAP/volume/sweep detectors recompute per call
RERL detectors recompute trailing/cumulative quantities each run. Acceptable per-timeline; if a
batch reconstructs thousands of anchors on the same day, the **same day's bars are re-fetched and
re-scanned per anchor**. *Refinement:* a per-(symbol,date) bar/feature cache at batch time. Belongs
to the Dataset Builder (§5), not to RERL.

### 3.5 File organisation — healthy, two minor notes
- `research/` mixes **operator tooling** (inspector/explore/audit), a **data source** (news), and
  **derivation** (reconstruction/knowledge). The grouping is fine, but a short `research/README.md`
  mapping the subpackages would help a newcomer. (Doc-only; not required.)
- Demo CLIs (`run_*.py`) live at `research/` root; a `research/cli/` folder would tidy them later.
  Cosmetic.

### 3.6 Testability — strong
8 suites, deterministic, no network, structural guards (forbidden-key rejection, signature
recompute, PIT assertions). The duck-typed bar source and in-memory iterables make units trivially
testable. **No testability problem.** The only gap is the absence of a **fixture for a realistic
large dataset** to exercise the §3.1 scaling path — which can't exist until collection does.

### 3.7 Maintainability — strong, one watch item
Uniform patterns, immutable contracts, versioned specs, append-only stores, and a single
source-of-truth doc. **Watch item:** the `registries/` layer (13 modules) is the most likely place
for future sprawl; keep new registries out unless ratified (the gate/condition set is locked, which
already protects this).

---

## 4. What is explicitly NOT a problem
- No layer performs a duplicate *function* of another (news provenance in two forms is index-vs-
  archive, not duplication of logic).
- No cyclic or upward dependency.
- No research layer can mutate production, emit a feature/score/signal, or affect the gate.
- The five "Provider"-named abstractions are genuinely distinct responsibilities.

---

## 5. Design-Only — `Research Dataset Builder` (NOT implemented)

The review finds the design sound, so — **design only, no code** — here is the next proposed layer.

### 5.1 Single responsibility
**Turn the immutable observation store into versioned, reproducible, read-only research datasets
(frames) for analysis** — and nothing else. It *assembles and snapshots*; it does not compute
features, score, predict, or decide.

### 5.2 What it receives (inputs)
- A **read-only handle** to the observation store (once collection exists) and the reference
  registries (PIT, read-only).
- A **selection spec**: partition(s) (`TRAIN/VAL/OOS/VAULT`), date/regime/universe/label-version
  filters, and the frozen `label_spec_id` to bind to.
- Optionally, read-only handles to the **news archive** and **RERL timelines** for *context joins*
  (kept as separate, clearly-labelled context columns — never merged into a pre-signal feature).

### 5.3 What it produces (outputs)
- A **DatasetFrame**: a flat, append-only, **content-hashed** snapshot of `ObservationRow`s (their
  already-signed fields + outcome primitives **only with `with_labels=True`**), tagged with a
  **dataset_version**, the bound `label_spec_id`, and the registry/rubric hashes (provenance).
- A **manifest** (reusing the existing `ResearchSession`/Research-Registry pattern) recording
  exactly which rows, which versions, and which hashes produced the frame — so the dataset is
  **deterministically rebuildable** and never silently drifts.
- Datasets are **read-only once produced**; regeneration creates a new `dataset_version` (never an
  edit), mirroring the label's write-once discipline.

### 5.4 How it connects to existing layers
- **Reads** the observation store + reference registries (PIT, read-only) — like the explorer/audit
  do today, but at **dataset scale** via a **streaming/chunked** contract (the §3.1 fix lives here).
- **Reuses** `dataset_roles` partitions (it never re-partitions), the frozen `label_spec`, and the
  Research Registry for pre-registration/provenance.
- **May attach** RERL/REKL **context** as labelled context columns; this context is outcome-side and
  carries the same firewall flags — it is never presented as a pre-signal input.
- **Writes nothing** to production; emits dataset artifacts to a research output area, append-only.

### 5.5 Why it is NOT a Feature Layer
- It performs **no computation that predicts the label**: it selects, snapshots, and stamps
  provenance. Every column it emits **already exists** as a signed observation field or an outcome
  primitive — it **derives no new predictive quantity**.
- It produces **no scores, no signals, no sentiment, no direction, no ranking** — and any genuine
  feature must still pass the **existing** discovery path (Feature Registry admission, PIT proof,
  pre-registered hypothesis, OOS, FDR, Vault). The Dataset Builder *feeds* that path with clean,
  versioned data; it is not part of it.
- It honours the **research/execution firewall**: outcome/label columns appear only under
  `with_labels=True`, and context joins are flagged forward — so the builder cannot become a
  back-door for leakage or for privileged features.

> In one line: the Dataset Builder is the **bridge from the immutable observation store to
> reproducible research frames** — a packager and provenance-stamper, explicitly *upstream* of any
> feature work, never a feature layer itself.

---

## 6. Recommendation
Adopt the findings as **forward-looking refinements** (none blocking). The most valuable single
design decision for scale is to make the **Research Dataset Builder** establish a
**streaming/chunked, store-backed** access contract, so the existing explorer/audit/REKL tools can
later consume millions of rows in batches rather than in memory.

**No further building until a new architecture decision is taken.** This report changes nothing in
the repository; status remains `READY_FOR_COLLECTION = FALSE`, Integrity 6/6, Priority #3 NOT
authorized.
