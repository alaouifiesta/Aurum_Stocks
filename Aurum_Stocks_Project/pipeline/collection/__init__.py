"""pipeline/collection/ — the Collection Layer (Phase 2). Additive; isolated.

Turns MDVPL-validated (mock) market data into immutable, point-in-time, fully-signed
ObservationRows using ONLY the already-frozen Phase-1 contracts (ObservationBuilder,
PartitionAssigner, the registry resolver ports). It computes no features, no scores, no
signals, makes no predictions, and decides no trades. It modifies no frozen contract,
registry, label, gate, or hash.

Pieces (each behind a generic port so storage/sources can be swapped later):
  keys              deterministic candidate key (idempotency / dedup)
  sources           BarSource over MDVPL-validated bars + Null (empty) FeatureComputer
  candidate_source  CandidateSource port + deterministic MockCandidateSource (no edge)
  sink              ObservationSink port + InMemoryObservationSink (Memory/File/DB future)
  rejections        append-only RejectionLedger with structured reason codes
  manifest          append-only, event-sourced IngestManifest (recovery / resume)
  collector         CollectionEngine orchestrator (full-population, PIT, idempotent)
  wiring            mock assembly factory for tests/demo
"""
from __future__ import annotations

from .keys import candidate_key
from .sources import MdvplBarSource, NullFeatureComputer
from .candidate_source import CandidateSource, MockCandidateSource
from .sink import ObservationSink, InMemoryObservationSink
from .rejections import RejectionLedger, RejectionRecord, RejectionCode
from .manifest import IngestManifest, ManifestEvent, BatchStatus
from .collector import CollectionEngine, ResolverBundle, BatchResult

__all__ = [
    "candidate_key",
    "MdvplBarSource", "NullFeatureComputer",
    "CandidateSource", "MockCandidateSource",
    "ObservationSink", "InMemoryObservationSink",
    "RejectionLedger", "RejectionRecord", "RejectionCode",
    "IngestManifest", "ManifestEvent", "BatchStatus",
    "CollectionEngine", "ResolverBundle", "BatchResult",
]
