"""Research Event Reconstruction Layer (RERL) — read-only.

Reconstructs the full chronological timeline of an event (esp. news) from point-in-time
market data, linking it to subsequent factual tape occurrences (opening range, volume
expansion, sweeps, breakouts, VWAP crossings, halts, clusters). Standalone and separate
from Observation Builder, Feature Registry, and the Label System. It produces NO features,
NO scanner candidates, NO ML, NO trading decisions, and consumes NO future information at
any detection point. Post-anchor entries are forward/outcome context, firewalled."""
from .timeline import Timeline, TimelineEvent, PRE, AT, POST  # noqa: F401
from .engine import ReconstructionEngine  # noqa: F401
from . import detectors  # noqa: F401
