"""pipeline/collection/manifest.py — append-only, event-sourced ingest manifest.

Records the lifecycle of every (symbol, trading-day) batch as an APPEND-ONLY event log
(refinement #3): no row is ever updated or deleted in place. Batch status is *derived* by
folding the log (latest event per batch wins), never stored mutably.

Event types
  BATCH_STARTED      a batch began processing (written before any observation is built)
  BATCH_COMMITTED    a batch finished successfully (carries counts + MDVPL content_hash)
  BATCH_QUARANTINED  a batch was withheld (e.g. MDVPL verdict FAIL) — no rows stored

Recovery mechanism (refinement #5)
  A batch is COMPLETE iff its LATEST event is BATCH_COMMITTED (a later re-run that commits
  again is harmless — see below). On restart the engine asks `is_committed(batch_key)`:
    * latest event == BATCH_COMMITTED  -> skip (already done, safe to resume past it);
    * latest event == BATCH_STARTED (crash mid-batch) -> reprocess. Reprocessing is safe
      because the ObservationSink deduplicates on the deterministic candidate_key, so already
      -stored rows are no-ops and only the unfinished remainder is added (exactly-once effect);
    * latest event == BATCH_QUARANTINED -> reprocess only if inputs changed (a new content_hash
      indicates new data); otherwise it stays quarantined;
    * no events at all -> a fresh batch, process normally.
  Because status is derived from an append-only log, recovery never depends on an in-place flag
  that a crash could leave half-written.

The manifest lives in its OWN sqlite catalog (independent connection, in-memory by default),
mirroring pipeline/mdvpl/provenance.py. It NEVER touches the frozen registries DB.
"""
from __future__ import annotations

import datetime as dt
import sqlite3
import uuid
from dataclasses import dataclass

SCHEMA_VERSION = "ingest-manifest-1"


class BatchStatus:
    STARTED = "BATCH_STARTED"
    COMMITTED = "BATCH_COMMITTED"
    QUARANTINED = "BATCH_QUARANTINED"
    NONE = "NONE"          # derived: no events for this batch


_DDL = """
CREATE TABLE IF NOT EXISTS ingest_events (
    event_id        TEXT PRIMARY KEY,
    seq             INTEGER,                 -- monotonic per-connection ordering
    batch_key       TEXT NOT NULL,           -- "<symbol>|<date>"
    event_type      TEXT NOT NULL,           -- BATCH_STARTED / BATCH_COMMITTED / BATCH_QUARANTINED
    symbol          TEXT NOT NULL,
    trade_date      TEXT NOT NULL,
    content_hash    TEXT,                    -- MDVPL batch content hash (provenance link)
    verdict         TEXT,                    -- MDVPL verdict at commit/quarantine
    candidate_count INTEGER,
    stored_count    INTEGER,                 -- newly stored this event
    duplicate_count INTEGER,                 -- already-present (idempotent re-collection)
    rejected_count  INTEGER,
    burned_count    INTEGER,                 -- CALIBRATION_ONLY excluded (never stored)
    detail          TEXT,
    event_ts_utc    TEXT NOT NULL,
    schema_version  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_ingest_batch ON ingest_events(batch_key, seq);
"""


@dataclass(frozen=True)
class ManifestEvent:
    event_id: str
    seq: int
    batch_key: str
    event_type: str
    symbol: str
    trade_date: str
    content_hash: str = ""
    verdict: str = ""
    candidate_count: int = 0
    stored_count: int = 0
    duplicate_count: int = 0
    rejected_count: int = 0
    burned_count: int = 0
    detail: str = ""


def batch_key(symbol: str, date) -> str:
    return f"{symbol}|{date}"


class IngestManifest:
    """Append-only event log over an independent sqlite catalog."""

    def __init__(self, conn: sqlite3.Connection | None = None):
        self.conn = conn or sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(_DDL)

    # -- append-only writes (one INSERT per event; never UPDATE/DELETE) -----------------
    def _next_seq(self) -> int:
        row = self.conn.execute("SELECT COALESCE(MAX(seq), 0) + 1 AS n FROM ingest_events").fetchone()
        return int(row["n"])

    def _emit(self, *, symbol, date, event_type, **kw) -> ManifestEvent:
        ev = ManifestEvent(
            event_id=str(uuid.uuid4()), seq=self._next_seq(),
            batch_key=batch_key(symbol, date), event_type=event_type,
            symbol=str(symbol), trade_date=str(date), **kw,
        )
        self.conn.execute(
            "INSERT INTO ingest_events (event_id,seq,batch_key,event_type,symbol,trade_date,"
            "content_hash,verdict,candidate_count,stored_count,duplicate_count,rejected_count,"
            "burned_count,detail,event_ts_utc,schema_version) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (ev.event_id, ev.seq, ev.batch_key, ev.event_type, ev.symbol, ev.trade_date,
             ev.content_hash, ev.verdict, ev.candidate_count, ev.stored_count, ev.duplicate_count,
             ev.rejected_count, ev.burned_count, ev.detail,
             dt.datetime.now(dt.timezone.utc).isoformat(), SCHEMA_VERSION),
        )
        self.conn.commit()
        return ev

    def started(self, symbol, date, *, content_hash: str = "") -> ManifestEvent:
        return self._emit(symbol=symbol, date=date, event_type=BatchStatus.STARTED,
                          content_hash=content_hash)

    def committed(self, symbol, date, *, content_hash, verdict,
                  candidate_count, stored_count, duplicate_count, rejected_count,
                  burned_count, detail="") -> ManifestEvent:
        return self._emit(symbol=symbol, date=date, event_type=BatchStatus.COMMITTED,
                          content_hash=content_hash, verdict=verdict,
                          candidate_count=candidate_count, stored_count=stored_count,
                          duplicate_count=duplicate_count, rejected_count=rejected_count,
                          burned_count=burned_count, detail=detail)

    def quarantined(self, symbol, date, *, content_hash, verdict, detail="") -> ManifestEvent:
        return self._emit(symbol=symbol, date=date, event_type=BatchStatus.QUARANTINED,
                          content_hash=content_hash, verdict=verdict, detail=detail)

    # -- derived reads (fold the log; never stored mutably) ----------------------------
    def latest_event(self, symbol, date):
        return self.conn.execute(
            "SELECT * FROM ingest_events WHERE batch_key=? ORDER BY seq DESC LIMIT 1",
            (batch_key(symbol, date),)).fetchone()

    def status(self, symbol, date) -> str:
        row = self.latest_event(symbol, date)
        return row["event_type"] if row else BatchStatus.NONE

    def is_committed(self, symbol, date) -> bool:
        return self.status(symbol, date) == BatchStatus.COMMITTED

    def pending(self, batch_specs) -> list[tuple]:
        """Given an iterable of (symbol, date), return those NOT already committed
        (recovery: the set to (re)process)."""
        return [(s, d) for (s, d) in batch_specs if not self.is_committed(s, d)]

    def events(self, symbol=None, date=None) -> list[sqlite3.Row]:
        if symbol is None:
            return self.conn.execute("SELECT * FROM ingest_events ORDER BY seq").fetchall()
        return self.conn.execute(
            "SELECT * FROM ingest_events WHERE batch_key=? ORDER BY seq",
            (batch_key(symbol, date),)).fetchall()

    def count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM ingest_events").fetchone()[0]
