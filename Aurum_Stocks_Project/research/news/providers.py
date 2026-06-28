"""research/news/providers.py — provider abstractions only.

Interfaces + mocks. NO external API calls are made here. The Polygon and Benzinga
providers are STUBS that refuse to run without an explicit, operator-wired session,
exactly like the calibration PolygonDataProvider. Providers return provenance-only
NewsRecords; they never score, classify, or interpret.
"""
from __future__ import annotations

import datetime as dt
from abc import ABC, abstractmethod

from .records import NewsRecord


class NewsProvider(ABC):
    """Returns news records for a symbol over a UTC time range. Provenance only."""
    name: str = "abstract"

    @abstractmethod
    def fetch(self, symbol: str, start_utc: str, end_utc: str) -> list[NewsRecord]:
        raise NotImplementedError


class HistoricalNewsProvider(NewsProvider):
    """Marker subtype for providers that serve HISTORICAL (point-in-time) news,
    i.e. they must populate `news_available_ts` honestly for the past."""
    name = "historical-abstract"


class PolygonNewsProvider(HistoricalNewsProvider):
    """STUB. Real implementation must map Polygon/Massive news payloads to NewsRecord,
    deriving news_available_ts from the feed's first-seen time (never the article's
    claimed time). Intentionally not executed here (no network, no key)."""
    name = "polygon"

    def __init__(self, api_key: str = "", session=None):
        self.api_key = api_key
        self._session = session

    def fetch(self, symbol: str, start_utc: str, end_utc: str) -> list[NewsRecord]:
        raise NotImplementedError(
            "PolygonNewsProvider is a stub. Wire a session + key in your environment; "
            "it is intentionally not run inside the research sandbox.")


class BenzingaProvider(HistoricalNewsProvider):
    """STUB. Same contract as above for the Benzinga news feed."""
    name = "benzinga"

    def __init__(self, api_key: str = "", session=None):
        self.api_key = api_key
        self._session = session

    def fetch(self, symbol: str, start_utc: str, end_utc: str) -> list[NewsRecord]:
        raise NotImplementedError(
            "BenzingaProvider is a stub. Wire a session + key in your environment.")


class MockNewsProvider(HistoricalNewsProvider):
    """Deterministic synthetic provider for tests/demos. NOT real data.

    Generates plausible provenance (with a realistic vendor availability delay) so the
    archive, inspector, explorer, and audit can be exercised end-to-end offline."""
    name = "mock"

    def __init__(self, *, delay_seconds: int = 45, seed: int = 7):
        self.delay_seconds = delay_seconds
        self.seed = seed

    def fetch(self, symbol: str, start_utc: str, end_utc: str) -> list[NewsRecord]:
        start = dt.datetime.fromisoformat(start_utc.replace("Z", "+00:00"))
        out = []
        for i in range(3):
            publish = start + dt.timedelta(hours=6 * i + 14)  # ~10:00 ET-ish
            avail = publish + dt.timedelta(seconds=self.delay_seconds)
            out.append(NewsRecord.build(
                article_id=f"{symbol}-{self.seed}-{i}", vendor="MOCK",
                source="mock-wire", tickers=[symbol],
                headline=f"{symbol} reports a corporate update number {i}",
                publish_ts_utc=publish.astimezone(dt.timezone.utc).isoformat(),
                news_available_ts_utc=avail.astimezone(dt.timezone.utc).isoformat(),
                language="en",
                raw=f"{symbol} body {i}"))
        return out
