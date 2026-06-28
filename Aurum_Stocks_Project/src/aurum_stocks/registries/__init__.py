"""Aurum Stocks — concrete reference registries (Priority #2 build).

SQLite-backed implementations of the R4 resolver ports, honoring the v3 locks:
  LOCK-1 regime cadence = HOURLY · LOCK-2 NO-FALLBACK resolvers · (LOCK-3 hash in R4).
"""
from . import db  # noqa: F401
from .symbol_registry import SymbolRegistry, SymbolRegistryResolverImpl  # noqa: F401
from .regime_registry import RegimeRegistry, RegimeRegistryResolverImpl  # noqa: F401
from .setup_registry import SetupRegistry, SetupRegistryResolverImpl  # noqa: F401
from .universe_registry import UniverseRegistry, UniverseRegistryResolverImpl  # noqa: F401
from .scanner_registry import ScannerRegistry, ScannerRegistryResolverImpl  # noqa: F401
from .data_quality_registry import DataQualityRegistry, DataQualityResolver  # noqa: F401
from .news_registry import NewsRegistry, NewsResolver  # noqa: F401
from .halt_registry import HaltRegistry, HaltResolver  # noqa: F401
from .microstructure_registry import MicrostructureRegistry  # noqa: F401
from .research_registry import ResearchRegistry  # noqa: F401
from .label_registry import LabelRegistry  # noqa: F401
