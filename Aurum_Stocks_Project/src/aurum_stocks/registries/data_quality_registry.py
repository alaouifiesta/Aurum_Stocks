"""
registries/data_quality_registry.py — guards against fake edge from data errors.

Two record kinds, never confused:
  AS_OF         — PIT; computable from data <= signal_ts; may flag/reject an observation.
  RETROSPECTIVE — full-session; ANALYSIS-TIME FILTER ONLY; must never become a feature.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import sqlite3
import uuid

import pandas as pd

from .db import to_utc_iso


def _hash(*f) -> str:
    return hashlib.sha256("|".join(str(x) for x in f).encode()).hexdigest()[:16]


class DataQualityRegistry:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def record_as_of(self, *, symbol, as_of: pd.Timestamp, feed_outage_active=False,
                     missing_prints_in_lookback=0, stale_quote=False,
                     last_good_ts: pd.Timestamp | None = None, source="vendor") -> str:
        dq_id = f"DQA_{uuid.uuid4().hex[:10]}"
        a = to_utc_iso(as_of)
        self.conn.execute(
            """INSERT INTO data_quality_registry
               (dq_id, symbol, pit_class, as_of, feed_outage_active,
                missing_prints_in_lookback, stale_quote, last_good_ts, source,
                ingested_at, row_hash)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (dq_id, symbol, "AS_OF", a, int(feed_outage_active),
             int(missing_prints_in_lookback), int(stale_quote),
             to_utc_iso(last_good_ts) if last_good_ts is not None else None, source,
             dt.datetime.now(dt.timezone.utc).isoformat(),
             _hash(symbol, a, feed_outage_active, stale_quote)),
        )
        self.conn.commit()
        return dq_id

    def record_retrospective(self, *, symbol, session_date: dt.date, missing_bars_pct=0.0,
                             n_bad_ticks=0, n_outlier_trades=0, halt_seconds=0,
                             feed_outage_seconds=0, ca_anomaly_flag=False,
                             quality_score=1.0, source="vendor") -> str:
        dq_id = f"DQR_{uuid.uuid4().hex[:10]}"
        self.conn.execute(
            """INSERT INTO data_quality_registry
               (dq_id, symbol, pit_class, session_date, missing_bars_pct, n_bad_ticks,
                n_outlier_trades, halt_seconds, feed_outage_seconds, ca_anomaly_flag,
                quality_score, source, ingested_at, row_hash)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (dq_id, symbol, "RETROSPECTIVE", session_date.isoformat(), missing_bars_pct,
             n_bad_ticks, n_outlier_trades, halt_seconds, feed_outage_seconds,
             int(ca_anomaly_flag), quality_score, source,
             dt.datetime.now(dt.timezone.utc).isoformat(),
             _hash(symbol, session_date.isoformat(), missing_bars_pct)),
        )
        self.conn.commit()
        return dq_id


class DataQualityResolver:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def as_of(self, symbol: str, as_of: pd.Timestamp) -> dict | None:
        """PIT: latest AS_OF quality snapshot at-or-before signal time."""
        row = self.conn.execute(
            """SELECT * FROM data_quality_registry
               WHERE symbol=? AND pit_class='AS_OF' AND as_of <= ?
               ORDER BY as_of DESC LIMIT 1""",
            (symbol, to_utc_iso(as_of)),
        ).fetchone()
        return dict(row) if row else None

    def is_quarantined_as_of(self, symbol: str, as_of: pd.Timestamp) -> bool:
        """PIT flag usable at build time: feed outage or stale quote at signal."""
        r = self.as_of(symbol, as_of)
        return bool(r and (r["feed_outage_active"] or r["stale_quote"]))

    def retrospective(self, symbol: str, session_date: dt.date) -> dict | None:
        """ANALYSIS-TIME ONLY. Never feed this into a feature (it sees the whole day)."""
        row = self.conn.execute(
            """SELECT * FROM data_quality_registry
               WHERE symbol=? AND pit_class='RETROSPECTIVE' AND session_date=?
               LIMIT 1""",
            (symbol, session_date.isoformat()),
        ).fetchone()
        return dict(row) if row else None
