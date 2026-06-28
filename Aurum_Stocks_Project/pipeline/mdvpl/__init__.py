"""Market Data Validation & Provenance Layer (MDVPL).

Validates raw market data and records its provenance BEFORE the Collection Layer. Provider-
agnostic (swap the adapter, change nothing else). Read-only / pass-through: it never edits data
and creates no features/observations/scores/signals. Outputs: a quality report (read-only) and an
append-only provenance record."""
from .source import MarketDataSource, MockMarketDataSource, Capabilities  # noqa: F401
from .checks import CheckResult, Status  # noqa: F401
from .provenance import ProvenanceRecord, ProvenanceLog  # noqa: F401
from .report import QualityReport  # noqa: F401
from .validator import MarketDataValidator, ValidationResult  # noqa: F401
