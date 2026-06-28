"""
registries/halt_registry.py — halt episodes as first-class objects.

AS-OF (PIT): at signal_ts you know halts that STARTED <= signal_ts and whether currently
halted. RETROSPECTIVE: "do signals before a halt behave differently?" is answered by
joining observations to episodes after the fact — you may NOT build an imminent-halt
feature (a coming halt is unknowable at signal_ts = pure lookahead).
"""
from __future__ import annotations

import sqlite3
import uuid

import pandas as pd

from .db import to_utc_iso


class HaltRegistry:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def add_halt(self, *, symbol, halt_start_ts: pd.Timestamp,
                 halt_end_ts: pd.Timestamp | None = None, halt_reason="",
                 luld_band_pct=None, resumption_ts: pd.Timestamp | None = None,
                 source="") -> str:
        halt_id = f"HALT_{uuid.uuid4().hex[:10]}"
        self.conn.execute(
            """INSERT INTO halt_registry
               (halt_id, symbol, halt_start_ts, halt_end_ts, halt_reason, luld_band_pct,
                resumption_ts, source)
               VALUES (?,?,?,?,?,?,?,?)""",
            (halt_id, symbol, to_utc_iso(halt_start_ts),
             to_utc_iso(halt_end_ts) if halt_end_ts is not None else None, halt_reason,
             luld_band_pct, to_utc_iso(resumption_ts) if resumption_ts is not None else None,
             source),
        )
        self.conn.commit()
        return halt_id


class HaltResolver:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def is_halted_at(self, symbol: str, as_of: pd.Timestamp) -> bool:
        """PIT: a halt that started at-or-before as_of and has not yet ended by as_of.
        Only halts with start <= as_of are considered (no future knowledge)."""
        a = to_utc_iso(as_of)
        row = self.conn.execute(
            """SELECT 1 FROM halt_registry
               WHERE symbol=? AND halt_start_ts <= ?
                 AND (halt_end_ts IS NULL OR halt_end_ts > ?)
               LIMIT 1""",
            (symbol, a, a),
        ).fetchone()
        return row is not None

    def halts_started_before(self, symbol: str, as_of: pd.Timestamp) -> list[dict]:
        """PIT: halt episodes known at signal time (started <= as_of)."""
        rows = self.conn.execute(
            """SELECT * FROM halt_registry
               WHERE symbol=? AND halt_start_ts <= ?
               ORDER BY halt_start_ts DESC""",
            (symbol, to_utc_iso(as_of)),
        ).fetchall()
        return [dict(r) for r in rows]

    def episodes(self, symbol: str) -> list[dict]:
        """RETROSPECTIVE: all episodes, for after-the-fact 'pre-halt behavior' research.
        Not PIT — never derive a pre-signal feature from this."""
        rows = self.conn.execute(
            "SELECT * FROM halt_registry WHERE symbol=? ORDER BY halt_start_ts", (symbol,)
        ).fetchall()
        return [dict(r) for r in rows]
