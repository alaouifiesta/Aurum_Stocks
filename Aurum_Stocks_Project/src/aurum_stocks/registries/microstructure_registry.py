"""
registries/microstructure_registry.py — RESERVED track (CHANGE #5 / MR1).

Provisioned now so adding Level-2 / order-flow / tick research later needs no
re-architecture. Empty by default. Discipline note (enforced elsewhere, restated here):
when populated, every microstructure feature still passes Feature Registry + PIT gate +
OOS — NO privileged features — and the execution firewall remains intact.
"""
from __future__ import annotations

import datetime as dt
import sqlite3

RESERVED = "RESERVED"
DATA_TYPES = ("L2_DEPTH", "ORDER_FLOW", "TICK_BY_TICK", "IMBALANCE")


class MicrostructureRegistry:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def reserve(self, *, microstructure_version_id: str, data_type: str, vendor="",
                resolution="", schema_ref="", pit_notes="") -> str:
        if data_type not in DATA_TYPES:
            raise ValueError(f"data_type must be one of {DATA_TYPES}")
        self.conn.execute(
            """INSERT OR IGNORE INTO microstructure_registry
               (microstructure_version_id, data_type, vendor, resolution, schema_ref,
                pit_notes, status, created_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            (microstructure_version_id, data_type, vendor, resolution, schema_ref,
             pit_notes, RESERVED, dt.datetime.now(dt.timezone.utc).isoformat()),
        )
        self.conn.commit()
        return microstructure_version_id

    def list_reserved(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM microstructure_registry WHERE status='RESERVED'").fetchall()
        return [dict(r) for r in rows]
