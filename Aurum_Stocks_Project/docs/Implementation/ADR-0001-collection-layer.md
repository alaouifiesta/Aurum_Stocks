# ADR-0001 — Collection Layer (Phase 2)

* **Status:** Accepted (Phase 2 implementation)
* **Scope:** `pipeline/collection/` + `tests/collection/`
* **Constraint envelope:** mock provider only · no SIP · no real execution · no scanner logic ·
  no feature generation · no ML · no trading · no prediction · no modification of any frozen
  contract, registry, gate, label, `ObservationRow`, `rubric_hash`, or Phase-1 foundation.
  Completely additive and isolated.

## Context

Phase 1 froze the substrate: the setup-agnostic `ObservationBuilder` (signing every row with the
6-id `registry_signature`), the `PartitionAssigner` / `CalibrationBurnLedger`, the registry
resolver ports, and the MDVPL validation/provenance layer. The Collection Layer's only job is to
turn MDVPL-validated (mock) market data into immutable, point-in-time, fully-signed
`ObservationRow`s — full-population — without computing features, scores, signals, predictions,
or trades, and without altering anything frozen. Persistence of those rows (the durable
date-partitioned Observation Store) is **Phase 3** and is deliberately left behind a port here.

## Decisions

1. **Additive isolation.** The layer imports the frozen substrate read-only and *constructs* its
   objects (e.g. one `ObservationBuilder` per batch); it modifies no frozen module. Verified: zero
   content changes to any tracked Phase-1 file; the full suite stays green at 10/10 and the
   integrity suite remains 6/6 GREEN with `READY_FOR_COLLECTION` still FALSE after collection runs.

2. **Storage behind a generic port (`ObservationSink`).** `CollectionEngine` depends only on the
   abstract `ObservationSink`; it never references a concrete sink. `InMemoryObservationSink` is the
   reference implementation. Future Memory / File (Parquet) / Database sinks — and the Phase-3
   durable store — satisfy the same interface. Append-only + write-once: a `candidate_key` is
   inserted at most once; a repeat insert is a no-op, never an overwrite.

3. **Append-only, event-sourced ingest manifest.** Batch lifecycle is recorded as an append-only
   log of `BATCH_STARTED` / `BATCH_COMMITTED` / `BATCH_QUARANTINED` events in an independent SQLite
   catalog (mirroring `mdvpl/provenance.py`; never the registries DB). Status is **derived** by
   folding the log (latest event per batch wins) — never updated in place.

4. **Deterministic candidate key (idempotency).** `ObservationRow.observation_id` (uuid4) and
   `ingestion_ts` are non-deterministic by design in the frozen builder, so dedup/idempotency key
   on a deterministic identity instead:
   `(symbol, signal_ts[UTC], setup_type, scanner_id, registry_signature)`.
   `scanner_id` is included explicitly for future multi-scanner compatibility, in addition to the
   `registry_signature` which already encodes the resolved `scanner_version_id`.

5. **Structured rejection codes.** Every non-stored candidate is recorded with a machine-readable
   `reason_code` plus a human message. Rejection codes mirror the builder's `ObservationRejected`
   reasons exactly (`MISSING_SYMBOL_VERSION`, `MISSING_REGIME_SNAPSHOT`, `UNKNOWN_SETUP`,
   `MISSING_UNIVERSE_VERSION`, `UNKNOWN_SCANNER`), plus `LONG_ONLY_VIOLATION` for the GC-7 hard
   fail and `BURNED_CALIBRATION_SLICE` for the burn exclusion.

6. **NO-FALLBACK preserved.** Resolver failures surface as `ObservationRejected` and are recorded,
   never substituted. GC-7 long-only is a hard fail (`LongOnlyViolation`), recorded and never
   stored.

7. **No features.** The builder requires a `FeatureComputer`; the layer supplies
   `NullFeatureComputer` (returns `{}`). This is the empty/identity port, not feature generation.

8. **Candidates are observed, not detected.** A `CandidateSource` port supplies `SignalEvent`s;
   `MockCandidateSource` is deterministic and edge-free (no score, no rank). Real scanner detection
   stays RESERVED and out of scope.

9. **Full-population accounting.** Per batch, `candidate_count == stored + duplicate + rejected +
   burned` is asserted before commit. Nothing is silently dropped.

10. **Burn isolation.** A row stamped `CALIBRATION_ONLY` by the `PartitionAssigner` never enters
    the sink; it is counted as `burned` and recorded as an exclusion. `assert_no_calibration_leak`
    guards the store at commit.

11. **MDVPL verdict gate.** `PASS` collects; `WARN` collects (flagged) unless
    `quarantine_on_warn`; `FAIL` quarantines the batch with zero observations (no zero-fill).

## Recovery mechanism

On restart the engine asks the manifest `is_committed(batch_key)`:

* latest event `BATCH_COMMITTED` → **skip** (already done; safe to resume past it);
* latest event `BATCH_STARTED` (crash mid-batch) → **reprocess**; safe because the sink dedups on
  `candidate_key`, so already-stored rows are no-ops and only the remainder is added (exactly-once
  effect);
* latest event `BATCH_QUARANTINED` → reprocess only if inputs changed (new `content_hash`);
* no events → fresh batch, process normally.

Because status is derived from an append-only log, recovery never depends on an in-place flag that
a crash could leave half-written.

## Consequences

* Swapping in the Phase-3 durable store is an adapter behind `ObservationSink` — no engine change.
* Idempotency and recovery are storage-agnostic (they ride on the deterministic key + event log).
* Row-level byte reproducibility is intentionally *not* claimed (uuid/ingestion_ts vary); identity
  and dedup are at the signature/key level, matching the integrity suite's rebuild-determinism.

## Explicitly deferred (not in Phase 2)

Durable date-partitioned Observation Store (Phase 3); forward triple-barrier **outcome** namespace;
Dataset Builder (Phase 4); live/streaming collection; real candidate detection / scanners / scores;
features; ML; prediction; trading/broker/SIP; the `LBL_V1` freeze. Real-data collection remains
gated on the operator freezing `LBL_V1` (`READY_FOR_COLLECTION` blocker); Phase 2 builds and tests
only against the mock provider.
