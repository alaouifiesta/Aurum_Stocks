"""pipeline/collection/collector.py — the Collection Engine (Phase 2 orchestrator).

Per (symbol, trading-day) batch it: validates the (mock) source via MDVPL, gates on the
verdict, then OBSERVES every candidate the CandidateSource yields by calling the FROZEN
ObservationBuilder — storing each fully-signed, PIT ObservationRow exactly once and accounting
for every candidate that is not stored (rejected or burn-excluded). It is:

  * additive      — imports the frozen substrate read-only; constructs, never modifies;
  * full-population — candidate_count == stored + duplicate + rejected + burned (asserted);
  * PIT           — bars are served as-of signal_ts; the builder re-asserts data_as_of<=signal_ts;
  * idempotent    — re-running a batch stores nothing new (sink dedup on candidate_key);
  * recoverable   — committed batches are skipped; interrupted ones safely reprocess;
  * storage-agnostic — depends ONLY on the ObservationSink port (refinement #2).

It generates no features (NullFeatureComputer), no scores, no signals, no predictions, no
trades, and writes no outcome. Burned CALIBRATION_ONLY rows never enter the sink.
"""
from __future__ import annotations

from dataclasses import dataclass

from aurum_stocks.foundation.observation_builder import (
    ObservationBuilder, LongOnlyViolation, ObservationRejected,
    SymbolRegistryResolver, RegimeRegistryResolver, SetupRegistryResolver,
    UniverseRegistryResolver, ScannerRegistryResolver, LabelSpecProvider, FeatureComputer,
)
from aurum_stocks.foundation.dataset_roles import (
    DatasetRole, PartitionAssigner, assert_no_calibration_leak,
)

from .candidate_source import CandidateSource
from .sink import ObservationSink
from .manifest import IngestManifest
from .rejections import RejectionLedger, RejectionCode
from .sources import MdvplBarSource, NullFeatureComputer
from .keys import candidate_key

# Verdicts that withhold a batch (no rows stored). PASS always collects.
_FAIL = "FAIL"
_WARN = "WARN"


@dataclass
class ResolverBundle:
    """The frozen registry resolver ports + partitioner + feature computer (all injected).

    The engine constructs an ObservationBuilder per batch from this bundle plus the batch's
    as-of bar source. It never holds a concrete registry — only the abstract ports.
    """
    symbols: SymbolRegistryResolver
    regimes: RegimeRegistryResolver
    setups: SetupRegistryResolver
    labels: LabelSpecProvider
    universes: UniverseRegistryResolver
    scanners: ScannerRegistryResolver
    partitioner: PartitionAssigner
    features: FeatureComputer = None  # defaults to NullFeatureComputer (no features)

    def __post_init__(self):
        if self.features is None:
            self.features = NullFeatureComputer()


@dataclass
class BatchResult:
    symbol: str
    trade_date: str
    status: str                  # COMMITTED / QUARANTINED / SKIPPED
    verdict: str = ""
    candidate_count: int = 0
    stored_count: int = 0        # newly stored this run
    duplicate_count: int = 0     # already present (idempotent re-collection)
    rejected_count: int = 0      # builder refused to sign
    burned_count: int = 0        # CALIBRATION_ONLY excluded (never stored)

    @property
    def accounted(self) -> bool:
        """Full-population: every candidate is stored, duplicated, rejected, or burn-excluded."""
        return (self.stored_count + self.duplicate_count
                + self.rejected_count + self.burned_count) == self.candidate_count


class CollectionEngine:
    def __init__(self, *, validator, source, candidates: CandidateSource,
                 bundle: ResolverBundle, sink: ObservationSink, manifest: IngestManifest,
                 rejections: RejectionLedger, streams=("bars", "quotes"),
                 quarantine_on_warn: bool = False):
        self.validator = validator
        self.source = source
        self.candidates = candidates
        self.bundle = bundle
        self.sink = sink                       # ObservationSink port (no concrete dependency)
        self.manifest = manifest
        self.rejections = rejections
        self.streams = streams
        self.quarantine_on_warn = quarantine_on_warn

    # ------------------------------------------------------------------ per batch
    def collect_batch(self, symbol: str, date) -> BatchResult:
        # Recovery: a committed batch is skipped (idempotent resume).
        if self.manifest.is_committed(symbol, date):
            return BatchResult(symbol=symbol, trade_date=str(date), status="SKIPPED")

        # 1) validate the (mock) source, read-only, via MDVPL.
        vr = self.validator.validate(self.source, symbol, date, streams=self.streams)
        verdict = vr.provenance.verdict
        content_hash = vr.provenance.content_hash

        self.manifest.started(symbol, date, content_hash=content_hash)

        # 2) verdict gate. FAIL (and WARN if configured) -> quarantine, store nothing.
        if verdict == _FAIL or (self.quarantine_on_warn and verdict == _WARN):
            self.manifest.quarantined(symbol, date, content_hash=content_hash,
                                      verdict=verdict, detail="MDVPL verdict gate")
            return BatchResult(symbol=symbol, trade_date=str(date),
                               status="QUARANTINED", verdict=verdict)

        # 3) bind an as-of bar source from the validated (pass-through) bars and build a
        #    builder for this batch (frozen builder; constructed, not modified).
        bar_source = MdvplBarSource({symbol: vr.data.get("bars", [])})
        builder = ObservationBuilder(
            self.bundle.symbols, self.bundle.regimes, self.bundle.setups, self.bundle.labels,
            bar_source, self.bundle.features, self.bundle.partitioner,
            self.bundle.universes, self.bundle.scanners,
        )

        candidate_count = stored = duplicate = rejected = burned = 0

        for event in self.candidates.candidates(symbol, date):
            candidate_count += 1
            try:
                row = builder.build(event)
            except LongOnlyViolation as e:                       # GC-7 hard fail
                rejected += 1
                self.rejections.record(candidate_key="", reason_code=RejectionCode.LONG_ONLY_VIOLATION,
                                       message=str(e), symbol=event.symbol, signal_ts=event.signal_ts,
                                       setup_type=event.setup_type, scanner_id=event.scanner_id)
                continue
            except ObservationRejected as e:                     # NO-FALLBACK rejection
                rejected += 1
                self.rejections.record(candidate_key="", reason_code=e.reason, message=str(e),
                                       symbol=event.symbol, signal_ts=event.signal_ts,
                                       setup_type=event.setup_type, scanner_id=event.scanner_id)
                continue

            key = candidate_key(event, row.registry_signature_hash)

            # Burn isolation: a CALIBRATION_ONLY row never enters the store (recorded as exclusion).
            if row.dataset_role == DatasetRole.CALIBRATION_ONLY:
                burned += 1
                self.rejections.record(candidate_key=key,
                                       reason_code=RejectionCode.BURNED_CALIBRATION_SLICE,
                                       message="burned calibration slice (excluded from store)",
                                       symbol=event.symbol, signal_ts=event.signal_ts,
                                       setup_type=event.setup_type, scanner_id=event.scanner_id)
                continue

            if self.sink.append(key, row):
                stored += 1
            else:
                duplicate += 1

        # 4) full-population guard + no-leak guard, then commit (append-only).
        result = BatchResult(symbol=symbol, trade_date=str(date), status="COMMITTED",
                             verdict=verdict, candidate_count=candidate_count, stored_count=stored,
                             duplicate_count=duplicate, rejected_count=rejected, burned_count=burned)
        if not result.accounted:
            raise AssertionError(
                f"full-population accounting failed for {symbol}|{date}: "
                f"candidates={candidate_count} stored={stored} dup={duplicate} "
                f"rejected={rejected} burned={burned}")
        assert_no_calibration_leak(self.sink.rows())   # nothing burned ever reached the store

        self.manifest.committed(symbol, date, content_hash=content_hash, verdict=verdict,
                                candidate_count=candidate_count, stored_count=stored,
                                duplicate_count=duplicate, rejected_count=rejected,
                                burned_count=burned)
        return result

    # ------------------------------------------------------------------ many batches
    def collect(self, batch_specs) -> list[BatchResult]:
        """Process many (symbol, date) batches. Already-committed batches are skipped
        (recovery/resume). Returns one BatchResult per spec."""
        return [self.collect_batch(s, d) for (s, d) in batch_specs]
