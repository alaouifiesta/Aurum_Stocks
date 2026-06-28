"""research/news/archive.py — the canonical historical news archive.

Append-only. Never overwrites, never deletes. Duplicate detection LINKS records
(via `duplicate_of`); it never removes a sighting, because two vendors can report
the same story with different `news_available_ts` — and PIT depends on the earliest.

This store is INDEPENDENT of the production registries DB. It does not modify, read,
or depend on registries/db.py. It is research infrastructure.
"""
from __future__ import annotations

import datetime as dt
import sqlite3
import uuid

from .records import NewsRecord, _parse_utc

_DDL = """
CREATE TABLE IF NOT EXISTS news_archive (
    record_id            TEXT PRIMARY KEY,
    article_id           TEXT NOT NULL,
    vendor               TEXT NOT NULL,
    source               TEXT NOT NULL,
    tickers              TEXT NOT NULL,         -- comma-joined, sorted
    headline_hash        TEXT NOT NULL,
    publish_ts_utc       TEXT NOT NULL,
    news_available_ts_utc TEXT NOT NULL,
    language             TEXT NOT NULL,
    market_session       TEXT NOT NULL,
    availability_delay_seconds REAL NOT NULL,
    collection_ts_utc    TEXT NOT NULL,
    content_hash         TEXT,
    duplicate_of         TEXT,                  -- record_id of an earlier sighting
    dup_kind             TEXT,                  -- EXACT / CONTENT / STORY / NULL
    schema_version       TEXT NOT NULL,
    ingestion_ts_utc     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_news_vendor_article ON news_archive(vendor, article_id);
CREATE INDEX IF NOT EXISTS ix_news_hl ON news_archive(headline_hash);
CREATE INDEX IF NOT EXISTS ix_news_avail ON news_archive(news_available_ts_utc);
"""

# Window within which two same-headline, ticker-overlapping items from different
# vendors are treated as the SAME story (linked, not deleted).
STORY_WINDOW_SECONDS = 3600


class NewsArchive:
    def __init__(self, conn: sqlite3.Connection | None = None):
        self.conn = conn or sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(_DDL)

    # -- duplicate detection (returns (duplicate_of, dup_kind) or (None, None)) ----
    def _find_duplicate(self, rec: NewsRecord):
        cur = self.conn.cursor()
        # 1) exact: same vendor + article_id
        row = cur.execute(
            "SELECT record_id FROM news_archive WHERE vendor=? AND article_id=? "
            "ORDER BY ingestion_ts_utc LIMIT 1", (rec.vendor, rec.article_id)).fetchone()
        if row:
            return row["record_id"], "EXACT"
        # 2) content: identical raw bytes (any vendor)
        if rec.content_hash:
            row = cur.execute(
                "SELECT record_id FROM news_archive WHERE content_hash=? AND content_hash<>'' "
                "ORDER BY ingestion_ts_utc LIMIT 1", (rec.content_hash,)).fetchone()
            if row:
                return row["record_id"], "CONTENT"
        # 3) story: same headline_hash + ticker overlap + within time window
        avail = _parse_utc(rec.news_available_ts_utc)
        rticks = set(rec.tickers)
        for row in cur.execute(
                "SELECT record_id, tickers, news_available_ts_utc FROM news_archive "
                "WHERE headline_hash=?", (rec.headline_hash,)).fetchall():
            other = set(row["tickers"].split(",")) if row["tickers"] else set()
            if rticks & other:
                dt_other = _parse_utc(row["news_available_ts_utc"])
                if abs((avail - dt_other).total_seconds()) <= STORY_WINDOW_SECONDS:
                    return row["record_id"], "STORY"
        return None, None

    def record(self, rec: NewsRecord) -> dict:
        """Append a record. Always inserts (append-only); if a duplicate is found it
        is inserted WITH a `duplicate_of` link and a `dup_kind`, never dropped.
        Returns {record_id, status, duplicate_of, dup_kind}."""
        dup_of, dup_kind = self._find_duplicate(rec)
        record_id = str(uuid.uuid4())
        self.conn.execute(
            "INSERT INTO news_archive VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (record_id, rec.article_id, rec.vendor, rec.source, ",".join(rec.tickers),
             rec.headline_hash, rec.publish_ts_utc, rec.news_available_ts_utc,
             rec.language, rec.market_session, rec.availability_delay_seconds,
             rec.collection_ts_utc, rec.content_hash, dup_of, dup_kind,
             rec.schema_version, dt.datetime.now(dt.timezone.utc).isoformat()))
        self.conn.commit()
        return {"record_id": record_id,
                "status": "DUPLICATE" if dup_of else "NEW",
                "duplicate_of": dup_of, "dup_kind": dup_kind}

    # -- read-only queries --------------------------------------------------------
    def count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM news_archive").fetchone()[0]

    def duplicates(self) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM news_archive WHERE duplicate_of IS NOT NULL").fetchall()

    def available_as_of(self, ticker: str, as_of_utc: str) -> list[sqlite3.Row]:
        """PIT query: items for `ticker` whose news_available_ts <= as_of. The ONLY
        availability key is news_available_ts (never publish_ts)."""
        out = []
        for row in self.conn.execute(
                "SELECT * FROM news_archive WHERE news_available_ts_utc<=? "
                "ORDER BY news_available_ts_utc", (as_of_utc,)).fetchall():
            if ticker.upper() in (row["tickers"].split(",") if row["tickers"] else []):
                out.append(row)
        return out
