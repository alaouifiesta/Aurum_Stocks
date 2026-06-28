"""
registries/news_registry.py — news provenance; the #1 small-cap lookahead trap.

PIT rule (NR1): triggers and features key on `news_available_ts` (when WE could act),
NEVER on `news_publish_ts` (claimed publication; metadata only). Only news with
`news_available_ts <= signal_ts` may be used. Stores a headline HASH, not full text.
"""
from __future__ import annotations

import datetime as dt
import sqlite3
import uuid

import pandas as pd

from .db import to_utc_iso


class NewsRegistry:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def add(self, *, symbol, news_available_ts: pd.Timestamp,
            news_publish_ts: pd.Timestamp | None = None, source="", vendor="",
            headline_hash="", category="") -> str:
        news_id = f"NEWS_{uuid.uuid4().hex[:12]}"
        avail = to_utc_iso(news_available_ts)
        pub = to_utc_iso(news_publish_ts) if news_publish_ts is not None else None
        delay = ((news_available_ts - news_publish_ts).total_seconds()
                 if news_publish_ts is not None else None)
        self.conn.execute(
            """INSERT INTO news_registry
               (news_id, symbol, source, vendor, news_publish_ts, news_available_ts,
                publication_delay_sec, headline_hash, category, ingested_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (news_id, symbol, source, vendor, pub, avail, delay, headline_hash, category,
             dt.datetime.now(dt.timezone.utc).isoformat()),
        )
        self.conn.commit()
        return news_id


class NewsResolver:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def available_as_of(self, symbol: str, as_of: pd.Timestamp) -> list[dict]:
        """PIT: all news ACTIONABLE at-or-before signal time (available_ts <= as_of)."""
        rows = self.conn.execute(
            """SELECT * FROM news_registry
               WHERE symbol=? AND news_available_ts <= ?
               ORDER BY news_available_ts DESC""",
            (symbol, to_utc_iso(as_of)),
        ).fetchall()
        return [dict(r) for r in rows]

    def latest_available(self, symbol: str, as_of: pd.Timestamp) -> dict | None:
        rows = self.available_as_of(symbol, as_of)
        return rows[0] if rows else None
