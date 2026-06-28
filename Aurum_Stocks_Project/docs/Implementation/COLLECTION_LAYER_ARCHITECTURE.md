# Collection Layer — Architecture Study (DESIGN ONLY)

> **Status: DESIGN PROPOSAL — NOT BUILT. NON-GATING.**
> No code, no implementation, no registry/feature/gate/label change. This studies the **future**
> Collection Layer that runs *after* `LBL_V1` is frozen. It modifies nothing today;
> `READY_FOR_COLLECTION` remains FALSE and every frozen artifact is untouched.

The Collection Layer's job is narrow: **turn raw SIP market data (+ recorded news/halts/CAs) into
immutable, point-in-time, fully-signed `ObservationRow`s** using the *already-built* contracts
(observation builder, registries, label spec, dataset roles). It computes **no features, no
scores, no signals**, and decides **no trades**.

---

## 1. Observation Store architecture
A dedicated, append-only **observation store**, separate from the lean registries DB. Three
namespaces mirroring the spec (`observation_core` · `observation_features` · `observation_outcome`):

- **core** — one immutable row per candidate: the signed `ObservationRow` fields (symbol, the 6
  signed reference-version ids, `registry_signature_hash`, `direction=LONG`, `signal_ts`,
  `data_as_of_ts ≤ signal_ts`, `dataset_role`, scan context, `ingestion_ts`).
- **features** — narrow/versioned `(observation_id, feature_name, value, feature_def_version,
  pit_safe)`. *Written by the builder only*, never by collection logic that sees outcomes.
- **outcome** — forward namespace (triple-barrier primitives), written *later* by a separate
  forward job; never read by any feature builder.

Design invariants: append-only at the storage layer; `observation_id` immutable; `split_partition`
assigned once at insert and never re-drawn; core/features/outcome are **physically separable** so a
feature builder process can never touch outcome rows.

```
        ┌─────────────────────────────────────────────┐
        │  Observation Store (append-only)            │
        │   core  ⟂  features  ⟂  outcome (forward)   │
        └───────────────┬───────────────┬─────────────┘
        signed rows ←───┘               └───→ forward outcome job (separate)
```

---

## 2. Historical collection pipeline (backfill)
Deterministic, replayable, idempotent. For each (symbol, trading-day) in the PIT universe:
```
1. RESOLVE universe as-of D (anti-survivorship) from symbol_registry
2. FETCH raw SIP for D: minute bars + NBBO quotes + (optionally) trades, with premarket warm-up
3. BUILD PIT context as-of each candidate ts: regime snapshot, halt state, data-quality flags,
   news available (news_available_ts ≤ signal_ts) — all read-only registry/archive lookups
4. DETECT candidates (setup-agnostic: every candidate event is observed — full population)
5. For each candidate → ObservationBuilder.build(...) → signed ObservationRow (LONG only)
6. ASSIGN split_partition deterministically; APPEND to observation_store.core (+ features)
7. RECORD batch in an ingest manifest (counts, window, status, content hashes)
```
**Idempotency:** re-running a (symbol, day) is keyed by a deterministic candidate key
`(symbol, signal_ts, setup_type)` + `registry_signature`; an already-present key is skipped, not
duplicated. Replaying the whole backfill yields the identical store (rebuild determinism — an
existing integrity check).

---

## 3. Live collection pipeline (paper/forward, still no trading)
Same builder, streaming source. Collection ≠ trading; this only *records* observations forward.
```
stream SIP (bars/quotes) ─→ rolling PIT context (regime/halt/news as-of now)
   ─→ candidate detection (full population) ─→ ObservationBuilder.build(...)
   ─→ append core(+features) ─→ schedule the forward triple-barrier outcome job
```
- **As-of discipline:** live context uses only data with `available_ts ≤ now`; `data_as_of_ts`
  records the newest input used and must be `≤ signal_ts`.
- **Outcome is forward:** the barrier outcome for a live observation resolves later (after `H`);
  the outcome job writes `observation_outcome` only, never features.
- **No decision:** the live pipeline emits rows; it places no orders (PAPER trading is a later,
  separate, authorized step gated by `READY_FOR_TRADING`, not by collection).

---

## 4. How SIP bars / quotes / trades / news enter the system
| input | role | enters via | PIT key |
|---|---|---|---|
| **SIP minute bars** | ATR / price path / session aggregates | bar source `get_minute_bars` | bar close ≤ signal_ts |
| **SIP NBBO quotes** | true spread (barrier÷spread, ref/bid/ask) | quote source as-of | quote ts ≤ signal_ts |
| **SIP trades** (optional) | finer microstructure context (RESERVED use) | trade source as-of | trade ts ≤ signal_ts |
| **News** | provenance context (NOT a feature) | `news_registry` index / news archive | `news_available_ts ≤ signal_ts` |
| **Halts / CAs** | state + identity (anti-survivorship) | `halt_registry` / `symbol_registry` SCD-2 | as-of signal_ts |

All inputs are funneled through **read-only, as-of resolvers**; nothing reads ahead of `signal_ts`.
Quotes are required for a true spread — IEX/single-venue is rejected (the SIP rule).

---

## 5. Append-only guarantees
- **Storage-layer append-only**, not merely by convention: no UPDATE/DELETE path on core/outcome;
  corrections are *new* rows linked via `supersedes` (mirrors news/event archives).
- `observation_id`, `registry_signature_hash`, and `split_partition` are **write-once**.
- Late/duplicate ingestion is deduplicated by deterministic key (no second row for the same
  candidate); a re-detected candidate is a no-op, never an overwrite.
- The forward outcome write is a **one-time** transition per observation (PROFIT/STOP/TIME),
  recorded once and immutable thereafter.

---

## 6. Recovery after interruption
- **Manifest-driven resumption:** every (symbol, day) batch is checkpointed in an ingest manifest
  with status `{STARTED, COMMITTED, FAILED}`. On restart, resume from the first non-`COMMITTED`
  batch.
- **Transactional commit per batch:** a batch's rows commit atomically; a crash mid-batch leaves it
  `STARTED` → re-run reprocesses it idempotently (dedup keys prevent doubles).
- **Exactly-once effect** via idempotent keys even with at-least-once delivery from the source.
- **Live gaps:** a stream outage is recorded as a data-quality `AS_OF` gap; affected windows are
  flagged (quarantine), never silently zero-filled. Backfill can later fill the gap append-only.

---

## 7. Partitioning strategy
Two orthogonal partitionings, kept distinct:
- **Research partition** (`split_partition ∈ {TRAIN, VAL, OOS, VAULT}`) — assigned **once,
  deterministically**, at insert; governs validation discipline; never changes.
- **Physical partition** — by **trading date** (and optionally symbol bucket) for storage/scan
  locality. Time-ordered, append-friendly, and aligned with how backfill and queries run
  (per-day).
The burned **calibration** slice is excluded from both (it never enters the store).

---

## 8. Storage layout for millions of observations
- **Columnar, date-partitioned files** (e.g., Parquet) for `observation_core` and
  `observation_features`, one partition per trading day (optionally sub-partitioned by symbol
  bucket). Append = write a new partition/file; existing files are never mutated.
- **`observation_features` stays narrow** (long format), so adding a feature definition appends rows
  for new observations without rewriting history (and never touches old rows).
- **`observation_outcome`** in its own date-partitioned set, physically separate from features
  (firewall by storage boundary).
- A small **index/catalog** (could remain SQLite) maps partitions → row counts, hashes, manifest
  status — the *catalog* is small even when the *data* is huge.
- This layout gives predictable scan cost (read only the days/columns needed) and supports the
  **streaming/chunked** access contract the Dataset Builder and REKL/explorer require at scale.

---

## 9. SQLite limitations and migration path
SQLite is ideal **now** (registries, catalogs, tests: small, transactional, zero-dep). At
collection scale it strains on: very large single-file tables, heavy concurrent writers, and
analytic scans over millions of rows.
**Migration path (staged, no rewrite of contracts):**
1. **Keep SQLite** for the registries + the **catalog/manifest** (small, relational, transactional).
2. **Move the observation store** to **date-partitioned columnar files (Parquet)** for core/features/
   outcome (analytic, append-only, scalable) behind the *same* read/write **port** the builder uses.
3. If strong multi-writer concurrency is later needed, the catalog can move to a server DB
   (Postgres/DuckDB-over-files) **without** changing `ObservationRow` or the builder API — the store
   is accessed through a port, so the engine is storage-agnostic.
The contracts (`ObservationRow`, 6-id signature, partitions) are storage-independent by design, so
migration is an **adapter swap**, not an architecture change.

---

## 10. Backup strategy
- **Append-only ⇒ incremental backup is trivial:** new date partitions are immutable; back them up
  once and never again.
- **Pre-freeze / pre-milestone snapshots:** back up the registries + catalog (SQLite `.backup`) and
  the frozen `LBL_V1` DB before and after the freeze (already in `DEPLOYMENT_GUIDE`).
- **3-2-1 discipline:** the immutable partitions + the catalog + the manifests are sufficient to
  **rebuild deterministically**; keep at least one off-site copy of the frozen label and the
  catalog.
- **Integrity on restore:** re-run the integrity suite + a rebuild-determinism check after any
  restore before trusting the store.

---

## 11. Dataset Builder interaction
The (separately-proposed, **not** built) Research Dataset Builder sits **above** the store and
reads it **read-only, streaming/chunked**:
```
observation store (date-partitioned, append-only)
        │  read-only, by partition + selection spec
        ▼
Research Dataset Builder  →  versioned, content-hashed DatasetFrame + manifest
```
- Builder pushes selection down to partitions (partition pruning), never loads everything in memory.
- It binds a dataset to the frozen `label_spec_id` and stamps registry/rubric hashes for
  reproducibility; outcome columns appear only with `with_labels=True`.
- It writes **nothing** back to the store and creates **no features** — it packages and stamps
  provenance only (per the Architecture Review §5).

---

## 12. Exact sequence: raw SIP → `ObservationRow`
```
 1. PIT universe as-of D                     (symbol_registry, anti-survivorship)
 2. Fetch raw SIP for (symbol, D)            (minute bars + NBBO quotes [+ trades]; premarket warm-up)
 3. Candidate detection (setup-agnostic)     (full population: every candidate event becomes a row)
 4. For each candidate at signal_ts:
    a. Resolve symbol version  as-of signal_ts          (NO-FALLBACK)
    b. Resolve regime snapshot as-of signal_ts          (HOURLY)
    c. Resolve setup / universe / scanner versions      (registries)
    d. Bind frozen label_spec_id (LBL_V1)
    e. Compute PIT features from data ≤ signal_ts        (pit_safe asserted; UNKNOWN == REJECTED)
    f. Set data_as_of_ts = newest input used            (MUST be ≤ signal_ts)
    g. Quote state: ref/bid/ask/spread; halt/SSR flags   (as-of signal_ts)
    h. News context: only news_available_ts ≤ signal_ts  (provenance, not a feature)
 5. registry_signature_hash = sign(symbol, regime, setup, label, universe, scanner)  (6 ids)
 6. Enforce contracts: direction == LONG (GC-7) · missing version ⇒ ObservationRejected (NO-FALLBACK)
 7. Assign split_partition deterministically (write-once)
 8. Emit immutable ObservationRow → append to observation_store.core (+ features)
 9. (Later, forward) triple-barrier outcome job resolves PROFIT/STOP/TIME → observation_outcome
10. Record batch in ingest manifest (counts, hashes, status) for recovery + determinism
```
Every step is an as-of lookup or a pure transform; **no step reads beyond `signal_ts`**, and the
outcome (step 9) lives in a separate forward namespace that no feature builder may read.

---

## 13. What this study does NOT change
No code, no registries, no gate, no label, no features. `READY_FOR_COLLECTION = FALSE` and all
frozen hashes stand. Building the Collection Layer would be a separate, explicitly-ratified
engineering task with its own gate — **awaiting your decision**.
