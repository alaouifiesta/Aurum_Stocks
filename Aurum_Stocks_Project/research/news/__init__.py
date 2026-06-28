"""Canonical historical news archive (provenance only) + provider interfaces.

No feature extraction, no scoring, no sentiment, no classification of meaning.
The PIT key is news_available_ts; publish_ts is metadata only."""
from .records import NewsRecord, market_session, headline_hash, content_hash  # noqa: F401
from .archive import NewsArchive  # noqa: F401
from .providers import (  # noqa: F401
    NewsProvider, HistoricalNewsProvider, PolygonNewsProvider,
    BenzingaProvider, MockNewsProvider,
)
