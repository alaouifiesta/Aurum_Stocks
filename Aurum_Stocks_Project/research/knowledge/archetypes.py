"""research/knowledge/archetypes.py — group similar Timelines into research families.

Grouping is DETERMINISTIC and STRUCTURAL: a timeline's "archetype" is a stable key derived
from the factual sequence/set of its event kinds. There is NO learning (no ML/clustering), NO
score, NO similarity metric that ranks — two timelines are in the same family iff they share
the same structural key under the chosen scheme. Coarser schemes group more loosely; finer
schemes group more strictly. Read-only; the optional index is append-only.
"""
from __future__ import annotations

import datetime as dt
import sqlite3
import uuid
from collections import defaultdict

# Archetype schemes (fine -> coarse). All purely structural & factual.
SCHEMES = ("phase_kind_seq", "kind_seq", "kind_set", "post_kind_set")


def timeline_id(tl) -> str:
    return f"{tl.symbol}@{tl.anchor_ts_utc}"


def _kinds_in_order(tl):
    return [e.kind for e in tl.events]


def archetype_key(tl, scheme: str = "kind_set") -> str:
    if scheme == "kind_set":
        return "|".join(sorted({e.kind for e in tl.events}))
    if scheme == "kind_seq":
        return ">".join(_kinds_in_order(tl))
    if scheme == "phase_kind_seq":
        return ">".join(f"{e.phase}:{e.kind}" for e in tl.events)
    if scheme == "post_kind_set":
        return "|".join(sorted({e.kind for e in tl.events if e.phase == "POST"}))
    raise ValueError(f"unknown scheme {scheme!r}; choose from {SCHEMES}")


def group_by_archetype(timelines, scheme: str = "kind_set") -> dict:
    """Return {archetype_key: [timeline, ...]} — the research families."""
    fam = defaultdict(list)
    for tl in timelines:
        fam[archetype_key(tl, scheme)].append(tl)
    return dict(fam)


def family_sizes(timelines, scheme: str = "kind_set") -> dict:
    return {k: len(v) for k, v in sorted(
        group_by_archetype(timelines, scheme).items(), key=lambda kv: -len(kv[1]))}


# -- optional append-only index (accumulate families across many runs) -------------
_DDL = """
CREATE TABLE IF NOT EXISTS archetype_index (
    record_id      TEXT PRIMARY KEY,
    timeline_id    TEXT NOT NULL,
    symbol         TEXT NOT NULL,
    anchor_ts_utc  TEXT NOT NULL,
    scheme         TEXT NOT NULL,
    archetype_key  TEXT NOT NULL,
    n_events       INTEGER NOT NULL,
    ingestion_ts_utc TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_arch_key ON archetype_index(scheme, archetype_key);
"""


class ArchetypeIndex:
    """Append-only index of (timeline -> archetype_key). Never updates or deletes."""

    def __init__(self, conn: sqlite3.Connection | None = None):
        self.conn = conn or sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(_DDL)

    def record(self, tl, scheme: str = "kind_set") -> dict:
        key = archetype_key(tl, scheme)
        rid = str(uuid.uuid4())
        self.conn.execute(
            "INSERT INTO archetype_index VALUES (?,?,?,?,?,?,?,?)",
            (rid, timeline_id(tl), tl.symbol, tl.anchor_ts_utc, scheme, key,
             len(tl.events), dt.datetime.now(dt.timezone.utc).isoformat()))
        self.conn.commit()
        return {"record_id": rid, "archetype_key": key, "scheme": scheme}

    def members(self, scheme: str, key: str) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM archetype_index WHERE scheme=? AND archetype_key=? "
            "ORDER BY ingestion_ts_utc", (scheme, key)).fetchall()

    def family_sizes(self, scheme: str) -> dict:
        rows = self.conn.execute(
            "SELECT archetype_key, COUNT(*) n FROM archetype_index WHERE scheme=? "
            "GROUP BY archetype_key ORDER BY n DESC", (scheme,)).fetchall()
        return {r["archetype_key"]: r["n"] for r in rows}

    def count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM archetype_index").fetchone()[0]
