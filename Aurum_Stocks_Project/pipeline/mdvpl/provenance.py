"""pipeline/mdvpl/provenance.py — append-only provenance for every validated batch.

One immutable record per validate() call, so every batch of market data that could feed
collection is traceable to its source/version/range and its quality verdict. Append-only:
never updated, never deleted; a re-fetch is a NEW record (linked by content_hash).
"""
from __future__ import annotations

import datetime as dt
import sqlite3
import uuid
from dataclasses import dataclass, asdict

SCHEMA_VERSION = "prov-1"

_DDL = """
CREATE TABLE IF NOT EXISTS provenance (
    provenance_id    TEXT PRIMARY KEY,
    vendor           TEXT NOT NULL,
    adapter_version  TEXT NOT NULL,
    streams          TEXT NOT NULL,
    symbol           TEXT NOT NULL,
    range_start      TEXT NOT NULL,
    range_end        TEXT NOT NULL,
    feed_type        TEXT NOT NULL,    -- CONSOLIDATED_SIP / SINGLE_VENUE
    row_count        INTEGER NOT NULL,
    content_hash     TEXT NOT NULL,
    fetch_ts_utc     TEXT NOT NULL,
    verdict          TEXT NOT NULL,    -- PASS / WARN / FAIL
    report_ref       TEXT,
    schema_version   TEXT NOT NULL,
    ingestion_ts_utc TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_prov_hash ON provenance(content_hash);
CREATE INDEX IF NOT EXISTS ix_prov_symbol ON provenance(symbol, range_start);
"""


@dataclass(frozen=True)
class ProvenanceRecord:
    provenance_id: str
    vendor: str
    adapter_version: str
    streams: str
    symbol: str
    range_start: str
    range_end: str
    feed_type: str
    row_count: int
    content_hash: str
    fetch_ts_utc: str
    verdict: str
    report_ref: str = ""
    schema_version: str = SCHEMA_VERSION

    @staticmethod
    def new(**kw) -> "ProvenanceRecord":
        return ProvenanceRecord(provenance_id=str(uuid.uuid4()), **kw)


class ProvenanceLog:
    """Append-only store of ProvenanceRecords (independent of the production registries DB)."""

    def __init__(self, conn: sqlite3.Connection | None = None):
        self.conn = conn or sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(_DDL)

    def record(self, rec: ProvenanceRecord) -> str:
        d = asdict(rec)
        self.conn.execute(
            "INSERT INTO provenance (provenance_id,vendor,adapter_version,streams,symbol,"
            "range_start,range_end,feed_type,row_count,content_hash,fetch_ts_utc,verdict,"
            "report_ref,schema_version,ingestion_ts_utc) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (d["provenance_id"], d["vendor"], d["adapter_version"], d["streams"], d["symbol"],
             d["range_start"], d["range_end"], d["feed_type"], d["row_count"], d["content_hash"],
             d["fetch_ts_utc"], d["verdict"], d["report_ref"], d["schema_version"],
             dt.datetime.now(dt.timezone.utc).isoformat()))
        self.conn.commit()
        return rec.provenance_id

    def count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM provenance").fetchone()[0]

    def by_hash(self, content_hash: str) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM provenance WHERE content_hash=? ORDER BY ingestion_ts_utc",
            (content_hash,)).fetchall()

    def get(self, provenance_id: str):
        return self.conn.execute(
            "SELECT * FROM provenance WHERE provenance_id=?", (provenance_id,)).fetchone()
