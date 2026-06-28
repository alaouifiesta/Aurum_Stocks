"""research/news/records.py — the canonical news record (provenance only).

Records every news event EXACTLY as it arrived. There is NO feature extraction,
NO scoring, NO sentiment, NO classification of meaning here — only historical truth
and the timestamps that make it point-in-time correct.

The PIT key is `news_available_ts_utc` (when we could first act on it), never
`publish_ts_utc` (what the vendor claims).
"""
from __future__ import annotations

import datetime as dt
import hashlib
import re
from dataclasses import dataclass, field
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
SCHEMA_VERSION = "news-1"

# Regular Trading Hours boundaries (ET), used only to label the market session a
# record arrived in. This is a calendar fact, not a feature.
_PREMARKET_OPEN = dt.time(4, 0)
_RTH_OPEN = dt.time(9, 30)
_RTH_CLOSE = dt.time(16, 0)
_AFTERHOURS_CLOSE = dt.time(20, 0)


def normalize_headline(headline: str) -> str:
    """Lowercase + collapse whitespace. Used ONLY to compute a stable hash so the
    same headline hashes identically; the raw headline is preserved elsewhere."""
    return re.sub(r"\s+", " ", (headline or "").strip().lower())


def headline_hash(headline: str) -> str:
    return hashlib.sha256(normalize_headline(headline).encode("utf-8")).hexdigest()


def content_hash(raw: str | bytes) -> str:
    if isinstance(raw, str):
        raw = raw.encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _parse_utc(ts: str | dt.datetime) -> dt.datetime:
    if isinstance(ts, dt.datetime):
        d = ts
    else:
        d = dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))
    if d.tzinfo is None:
        raise ValueError("timestamps must be timezone-aware (UTC)")
    return d.astimezone(dt.timezone.utc)


def market_session(available_ts_utc: str | dt.datetime) -> str:
    """PREMARKET / RTH / AFTERHOURS / CLOSED for the ET wall-clock of availability.
    Weekends -> CLOSED. This is descriptive context, never a signal."""
    et = _parse_utc(available_ts_utc).astimezone(ET)
    if et.weekday() >= 5:
        return "CLOSED"
    t = et.time()
    if _PREMARKET_OPEN <= t < _RTH_OPEN:
        return "PREMARKET"
    if _RTH_OPEN <= t < _RTH_CLOSE:
        return "RTH"
    if _RTH_CLOSE <= t < _AFTERHOURS_CLOSE:
        return "AFTERHOURS"
    return "CLOSED"


def availability_delay_seconds(publish_ts_utc: str | dt.datetime,
                               available_ts_utc: str | dt.datetime) -> float:
    """available - publish, in seconds. Stored as-is (can be negative if a vendor
    back-dates a publish time); we record the truth, we do not 'fix' it."""
    return (_parse_utc(available_ts_utc) - _parse_utc(publish_ts_utc)).total_seconds()


@dataclass(frozen=True)
class NewsRecord:
    """One immutable news event, recorded exactly as it arrived. Provenance only."""
    article_id: str                 # vendor-native id (dedup key within a vendor)
    vendor: str                     # POLYGON / BENZINGA / MOCK / ...
    source: str                     # publisher/source within the vendor feed
    tickers: tuple[str, ...]        # symbol(s) the vendor attached
    headline_hash: str              # sha256 of normalized headline (raw kept by archive)
    publish_ts_utc: str             # vendor-claimed publication time (metadata)
    news_available_ts_utc: str      # PIT KEY: when we could first act on it
    language: str                   # e.g. "en" (as reported; not interpreted)
    market_session: str             # PREMARKET/RTH/AFTERHOURS/CLOSED at availability
    availability_delay_seconds: float
    collection_ts_utc: str          # when our pipeline ingested it
    content_hash: str = ""          # sha256 of raw bytes (exact-dup key), optional
    duplicate_of: str | None = None # link to an earlier record (never deletion)
    schema_version: str = SCHEMA_VERSION

    @staticmethod
    def build(*, article_id: str, vendor: str, source: str, tickers, headline: str,
              publish_ts_utc, news_available_ts_utc, language: str = "en",
              collection_ts_utc=None, raw: str | bytes | None = None) -> "NewsRecord":
        """Derive the provenance fields. No interpretation of content occurs."""
        avail = _parse_utc(news_available_ts_utc)
        coll = _parse_utc(collection_ts_utc) if collection_ts_utc else \
            dt.datetime.now(dt.timezone.utc)
        return NewsRecord(
            article_id=str(article_id), vendor=vendor.upper(), source=source,
            tickers=tuple(sorted({t.upper() for t in tickers})),
            headline_hash=headline_hash(headline),
            publish_ts_utc=_parse_utc(publish_ts_utc).isoformat(),
            news_available_ts_utc=avail.isoformat(),
            language=language,
            market_session=market_session(avail),
            availability_delay_seconds=availability_delay_seconds(publish_ts_utc, avail),
            collection_ts_utc=coll.isoformat(),
            content_hash=content_hash(raw) if raw is not None else "",
        )
