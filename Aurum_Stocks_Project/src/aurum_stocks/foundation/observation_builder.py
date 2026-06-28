"""
foundation/observation_builder.py  —  R4: the core contract, locked now.

    ObservationBuilder.build(signal_event) -> ObservationRow

The builder is fully GENERIC and setup-agnostic: it branches on no setup at all.
It receives an opaque SignalEvent from ANY detector and signs the row with four
versions so the row is reproducible forever:
    * symbol_registry version   (PIT, valid at signal_ts)
    * regime_snapshot version   (PIT, as-of signal_ts)
    * setup version             (from setup_registry)
    * label_spec version        (the frozen truth-definition)

It depends only on ABSTRACT resolver ports (below). The concrete registry-backed
resolvers are Priority #4 — building the contract first means we never redesign
this node when the registries land. In-memory stub resolvers are included so the
contract is runnable and testable today.

Outcome is NOT produced here: it is forward-only (written later). The builder
emits the as-of-signal row only.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import pandas as pd

from .dataset_roles import DatasetRole, PartitionAssigner

SCHEMA_VERSION = "obs_core_v1"


# ---------------------------------------------------------------------------
# Resolver failures (LOCK-2: NO FALLBACK). Resolvers raise these; the builder
# translates them into an ObservationRejected — never a row, never a fallback.
# ---------------------------------------------------------------------------
class MissingSymbolVersion(Exception):
    pass

class MissingRegimeSnapshot(Exception):
    pass

class UnknownSetup(Exception):
    pass

class MissingUniverseVersion(Exception):
    pass

class UnknownScanner(Exception):
    pass


class LongOnlyViolation(Exception):
    """GC-7 HARD FAIL: any non-LONG direction. Structural, not a soft rejection."""
    pass


class ObservationRejected(Exception):
    """Raised by build() when a row cannot be PIT-correctly signed. Carries a
    machine-readable reason for the rejection ledger."""
    def __init__(self, reason: str, detail: str = ""):
        self.reason = reason
        self.detail = detail
        super().__init__(f"{reason}: {detail}" if detail else reason)


_REJECTION_FOR = {
    MissingSymbolVersion: "MISSING_SYMBOL_VERSION",
    MissingRegimeSnapshot: "MISSING_REGIME_SNAPSHOT",
    UnknownSetup: "UNKNOWN_SETUP",
    MissingUniverseVersion: "MISSING_UNIVERSE_VERSION",
    UnknownScanner: "UNKNOWN_SCANNER",
}


# ---------------------------------------------------------------------------
# Generic input: what ANY detector must emit. Nothing setup-specific.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class SignalEvent:
    symbol: str
    signal_ts: pd.Timestamp        # tz-aware (ET)
    setup_type: str                # opaque FK into setup_registry
    direction: str = "LONG"        # GC-7: only LONG is permitted
    # scan context (GC-8/9): every candidate carries who scanned it and its rank
    scanner_id: str = ""
    universe_id: str = ""
    scanner_score: float | None = None
    scanner_rank: int | None = None
    candidate_batch_id: str = ""


# ---------------------------------------------------------------------------
# Resolver ports (implemented concretely by the registries in Priority #4).
# ---------------------------------------------------------------------------
class SymbolRegistryResolver(ABC):
    @abstractmethod
    def resolve(self, symbol: str, as_of: pd.Timestamp) -> str: ...

class RegimeRegistryResolver(ABC):
    @abstractmethod
    def resolve(self, as_of: pd.Timestamp) -> str: ...

class SetupRegistryResolver(ABC):
    @abstractmethod
    def resolve(self, setup_type: str) -> str: ...

class UniverseRegistryResolver(ABC):
    @abstractmethod
    def resolve(self, universe_id: str, as_of: pd.Timestamp) -> str: ...

class ScannerRegistryResolver(ABC):
    @abstractmethod
    def resolve(self, scanner_id: str) -> str: ...

class LabelSpecProvider(ABC):
    @abstractmethod
    def current_label_spec_id(self) -> str: ...

class BarSource(ABC):
    @abstractmethod
    def bars_as_of(self, symbol: str, signal_ts: pd.Timestamp):
        """Return (bars<=signal_ts, data_as_of_ts). data_as_of_ts MUST be <= signal_ts."""

class FeatureComputer(ABC):
    @abstractmethod
    def compute(self, symbol: str, signal_ts: pd.Timestamp, bars) -> dict:
        """Return ONLY PIT-validated features (passed the R3 harness)."""


# ---------------------------------------------------------------------------
# Output row (as-of-signal; outcome is forward-only and lives elsewhere).
# ---------------------------------------------------------------------------
@dataclass
class ObservationRow:
    observation_id: str
    schema_version: str
    symbol: str
    symbol_registry_id: str
    setup_type: str
    setup_version: str
    direction: str
    signal_ts_utc: str
    signal_ts_et: str
    regime_snapshot_id: str
    label_spec_id: str
    universe_version_id: str       # CHANGE #2
    scanner_version_id: str        # CHANGE #3
    registry_signature_hash: str   # LOCK-3 / RH2 (6 ids)
    data_as_of_ts: str
    dataset_role: DatasetRole
    features: dict
    ingestion_ts_utc: str
    # scan context (per-row values, NOT signature inputs)
    scanner_score: float | None = None
    scanner_rank: int | None = None
    candidate_batch_id: str = ""

    def assert_signed(self) -> None:
        missing = [k for k in ("symbol_registry_id", "regime_snapshot_id",
                               "setup_version", "label_spec_id",
                               "universe_version_id", "scanner_version_id",
                               "registry_signature_hash")
                   if not getattr(self, k)]
        if missing:
            raise AssertionError(f"unsigned observation, missing: {missing}")
        if self.data_as_of_ts > self.signal_ts_utc:
            raise AssertionError("PIT violation: data_as_of_ts > signal_ts_utc")
        if self.registry_signature_hash != registry_signature(
                self.symbol_registry_id, self.regime_snapshot_id, self.setup_version,
                self.label_spec_id, self.universe_version_id, self.scanner_version_id):
            raise AssertionError("registry_signature_hash mismatch")


def registry_signature(symbol_registry_id: str, regime_snapshot_id: str,
                       setup_version_id: str, label_spec_id: str,
                       universe_version_id: str, scanner_version_id: str) -> str:
    """RH2: deterministic hash over ALL SIX reference versions that built the row."""
    payload = "|".join((symbol_registry_id, regime_snapshot_id, setup_version_id,
                        label_spec_id, universe_version_id, scanner_version_id))
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


class ObservationBuilder:
    """Setup-agnostic. Builds one fully-signed ObservationRow per SignalEvent."""

    def __init__(self, symbols: SymbolRegistryResolver, regimes: RegimeRegistryResolver,
                 setups: SetupRegistryResolver, labels: LabelSpecProvider,
                 bars: BarSource, features: FeatureComputer,
                 partitioner: PartitionAssigner,
                 universes: UniverseRegistryResolver, scanners: ScannerRegistryResolver):
        self._symbols = symbols
        self._regimes = regimes
        self._setups = setups
        self._labels = labels
        self._bars = bars
        self._features = features
        self._partitioner = partitioner
        self._universes = universes
        self._scanners = scanners

    def build(self, event: SignalEvent) -> ObservationRow:
        """Build one fully-signed row, or raise ObservationRejected (NO FALLBACK).
        GC-7: a non-LONG direction is a HARD FAIL (LongOnlyViolation), never a row."""
        if event.direction != "LONG":
            raise LongOnlyViolation(f"direction={event.direction!r} forbidden (GC-7 LONG_ONLY)")

        ts = event.signal_ts
        bars, data_as_of = self._bars.bars_as_of(event.symbol, ts)
        if data_as_of > ts:
            raise AssertionError("BarSource returned future data (data_as_of > signal_ts)")

        # NO-FALLBACK resolution: a missing version rejects the observation outright.
        try:
            symbol_registry_id = self._symbols.resolve(event.symbol, ts)
            regime_snapshot_id = self._regimes.resolve(ts)
            setup_version_id = self._setups.resolve(event.setup_type)
            universe_version_id = self._universes.resolve(event.universe_id, ts)
            scanner_version_id = self._scanners.resolve(event.scanner_id)
        except tuple(_REJECTION_FOR) as e:
            raise ObservationRejected(_REJECTION_FOR[type(e)], str(e)) from e

        label_spec_id = self._labels.current_label_spec_id()
        sig = registry_signature(symbol_registry_id, regime_snapshot_id, setup_version_id,
                                 label_spec_id, universe_version_id, scanner_version_id)

        row = ObservationRow(
            observation_id=str(uuid.uuid4()),
            schema_version=SCHEMA_VERSION,
            symbol=event.symbol,
            symbol_registry_id=symbol_registry_id,
            setup_type=event.setup_type,
            setup_version=setup_version_id,
            direction=event.direction,
            signal_ts_utc=ts.tz_convert("UTC").isoformat(),
            signal_ts_et=ts.isoformat(),
            regime_snapshot_id=regime_snapshot_id,
            label_spec_id=label_spec_id,
            universe_version_id=universe_version_id,
            scanner_version_id=scanner_version_id,
            registry_signature_hash=sig,
            data_as_of_ts=data_as_of.tz_convert("UTC").isoformat(),
            dataset_role=self._partitioner.assign(event.symbol, ts),
            features=self._features.compute(event.symbol, ts, bars),
            ingestion_ts_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
            scanner_score=event.scanner_score,
            scanner_rank=event.scanner_rank,
            candidate_batch_id=event.candidate_batch_id,
        )
        row.assert_signed()
        return row
