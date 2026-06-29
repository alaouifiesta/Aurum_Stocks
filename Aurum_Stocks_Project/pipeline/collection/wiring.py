"""pipeline/collection/wiring.py — mock assembly for the Collection Layer (tests/demo).

Assembles a runnable CollectionEngine from the frozen builder ports + MDVPL mock source + a
deterministic candidate source. The stub resolvers below are demo/test scaffolding (the same
role MockMarketDataSource plays for MDVPL): they implement the frozen registry resolver PORTS
without touching the registries DB, and they honour NO-FALLBACK — an unknown symbol / setup /
scanner / universe RAISES the proper builder exception rather than substituting a value.

Nothing here is a registry, a scanner, a feature, a label, or a gate.
"""
from __future__ import annotations

import datetime as dt

from aurum_stocks.foundation import observation_builder as ob
from aurum_stocks.foundation.dataset_roles import (
    PartitionAssigner, CalibrationBurnLedger, BurnedSlice,
)
from pipeline.mdvpl.source import MockMarketDataSource
from pipeline.mdvpl.validator import MarketDataValidator

from .candidate_source import MockCandidateSource
from .sink import InMemoryObservationSink
from .manifest import IngestManifest
from .rejections import RejectionLedger
from .collector import CollectionEngine, ResolverBundle


# --- stub resolvers (demo scaffolding; implement the frozen ports; NO-FALLBACK) ----------
class StubSymbols(ob.SymbolRegistryResolver):
    def __init__(self, known): self.known = set(known)
    def resolve(self, symbol, as_of):
        if symbol not in self.known:
            raise ob.MissingSymbolVersion(f"no PIT symbol version for {symbol!r}")
        return f"{symbol}@symrev1"

class StubRegime(ob.RegimeRegistryResolver):
    def resolve(self, as_of): return "REGIME_SNAP_001"

class StubSetups(ob.SetupRegistryResolver):
    def __init__(self, known): self.known = set(known)
    def resolve(self, setup_type):
        if setup_type not in self.known:
            raise ob.UnknownSetup(f"unknown setup {setup_type!r}")
        return f"{setup_type}@v1"

class StubUniverse(ob.UniverseRegistryResolver):
    def __init__(self, known): self.known = set(known)
    def resolve(self, universe_id, as_of):
        if universe_id not in self.known:
            raise ob.MissingUniverseVersion(f"no universe version for {universe_id!r}")
        return f"{universe_id}@1"

class StubScanner(ob.ScannerRegistryResolver):
    def __init__(self, known): self.known = set(known)
    def resolve(self, scanner_id):
        if scanner_id not in self.known:
            raise ob.UnknownScanner(f"unknown scanner {scanner_id!r}")
        return f"{scanner_id}@1"

class StubLabels(ob.LabelSpecProvider):
    # Wiring-only label id (no real LBL_V1 frozen yet); changes no frozen label.
    def current_label_spec_id(self): return "LBL_MOCK@wiring"


def build_mock_collection_engine(
    *,
    symbols=("KTOS", "PTON", "NVAX"),
    setup_type="GAP_GO",
    scanner_id="SCAN_MOMENTUM",
    universe_id="SMALL_CAP_US",
    burned_slice: BurnedSlice | None = None,
    train_end: dt.date | None = None,
    val_end: dt.date | None = None,
    oos_end: dt.date | None = None,
    consolidated: bool = True,
    faults=frozenset(),
    quarantine_on_warn: bool = False,
    sink=None,
    manifest=None,
):
    """Build a CollectionEngine wired to the deterministic mock provider.

    `sink`/`manifest` may be supplied to share state across simulated restarts (recovery tests).
    `burned_slice` (optional) seeds the CalibrationBurnLedger to exercise burn isolation.
    """
    burn = CalibrationBurnLedger()
    if burned_slice is not None:
        burn.burn(burned_slice)
    partitioner = PartitionAssigner(burn_ledger=burn, train_end=train_end,
                                    val_end=val_end, oos_end=oos_end)

    bundle = ResolverBundle(
        symbols=StubSymbols(symbols), regimes=StubRegime(), setups=StubSetups({setup_type}),
        labels=StubLabels(), universes=StubUniverse({universe_id}),
        scanners=StubScanner({scanner_id}), partitioner=partitioner,
    )
    engine = CollectionEngine(
        validator=MarketDataValidator(),
        source=MockMarketDataSource(consolidated=consolidated, faults=frozenset(faults)),
        candidates=MockCandidateSource(setup_type=setup_type, scanner_id=scanner_id,
                                       universe_id=universe_id),
        bundle=bundle,
        # NOTE: `is not None` (not `or`) — an empty InMemoryObservationSink is falsy (len 0),
        # so `sink or ...` would wrongly discard a caller-supplied empty sink.
        sink=sink if sink is not None else InMemoryObservationSink(),
        manifest=manifest if manifest is not None else IngestManifest(),
        rejections=RejectionLedger(),
        quarantine_on_warn=quarantine_on_warn,
    )
    return engine
