"""
registries/scanner_registry.py — code-provenance versioned scanners (CHANGE #3).

Each Signal carries scanner_version_id so we know which scanner discovered it. The
scanner itself is a Research Artifact (GC-8), not a proven edge.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import sqlite3

from ..foundation.observation_builder import ScannerRegistryResolver, UnknownScanner


def _row_hash(*f) -> str:
    return hashlib.sha256("|".join(str(x) for x in f).encode()).hexdigest()[:16]


class ScannerRegistry:
    """Append-only versioned scanner definitions."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def register(self, *, scanner_id: str, scanner_spec_version: str,
                 candidate_generation_logic: str, universe_id: str = "",
                 status="ACTIVE") -> str:
        svid = f"{scanner_id}@{scanner_spec_version}"
        rh = _row_hash(scanner_id, scanner_spec_version, candidate_generation_logic)
        self.conn.execute(
            """INSERT OR IGNORE INTO scanner_registry
               (scanner_version_id, scanner_id, scanner_spec_version,
                candidate_generation_logic, universe_id, status, created_at, row_hash)
               VALUES (?,?,?,?,?,?,?,?)""",
            (svid, scanner_id, scanner_spec_version, candidate_generation_logic,
             universe_id, status, dt.datetime.now(dt.timezone.utc).isoformat(), rh),
        )
        self.conn.commit()
        return svid


class ScannerRegistryResolverImpl(ScannerRegistryResolver):
    """R4 port. Resolve scanner_id to its ACTIVE version id; NO FALLBACK."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def resolve(self, scanner_id: str) -> str:
        row = self.conn.execute(
            """SELECT scanner_version_id FROM scanner_registry
               WHERE scanner_id=? AND status='ACTIVE'
               ORDER BY scanner_spec_version DESC LIMIT 1""",
            (scanner_id,),
        ).fetchone()
        if row is None:
            raise UnknownScanner(f"no ACTIVE version for scanner '{scanner_id}'")
        return row["scanner_version_id"]
