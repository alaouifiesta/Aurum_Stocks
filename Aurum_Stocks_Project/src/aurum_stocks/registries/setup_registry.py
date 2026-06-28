"""
registries/setup_registry.py — append-only versioned setup definitions + resolver.

Setup versioning is code-provenance (§3.5). resolve(setup_type) returns the ACTIVE
version's id for that setup_id; unknown/none → UnknownSetup. The Observation Engine
never branches on setup_id — this registry just records and validates versions.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import sqlite3

from ..foundation.observation_builder import SetupRegistryResolver, UnknownSetup


def _row_hash(*f) -> str:
    return hashlib.sha256("|".join(str(x) for x in f).encode()).hexdigest()[:16]


class SetupRegistry:
    """Append-only versioned setup definitions."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def register(self, *, setup_id: str, version: str, detector_ref: str,
                 name="", description="", params: dict | None = None,
                 status="ACTIVE", author="") -> str:
        svid = f"{setup_id}@{version}"
        params_json = json.dumps(params or {}, sort_keys=True)
        rh = _row_hash(setup_id, version, detector_ref, params_json)
        self.conn.execute(
            """INSERT OR IGNORE INTO setup_registry
               (setup_version_id, setup_id, version, name, description, detector_ref,
                params, status, created_at, author, row_hash)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (svid, setup_id, version, name, description, detector_ref, params_json,
             status, dt.datetime.now(dt.timezone.utc).isoformat(), author, rh),
        )
        self.conn.commit()
        return svid

    def deprecate(self, setup_id: str, version: str) -> None:
        # status flip is the one allowed non-content mutation (never deletes history)
        self.conn.execute(
            "UPDATE setup_registry SET status='DEPRECATED' WHERE setup_id=? AND version=?",
            (setup_id, version))
        self.conn.commit()


class SetupRegistryResolverImpl(SetupRegistryResolver):
    """R4 port. Resolve to the ACTIVE version id of a setup_id; NO FALLBACK to deprecated."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def resolve(self, setup_type: str) -> str:
        row = self.conn.execute(
            """SELECT setup_version_id FROM setup_registry
               WHERE setup_id=? AND status='ACTIVE'
               ORDER BY version DESC LIMIT 1""",
            (setup_type,),
        ).fetchone()
        if row is None:
            raise UnknownSetup(f"no ACTIVE version registered for setup '{setup_type}'")
        return row["setup_version_id"]
