"""
registries/regime_registry.py — append-only HOURLY snapshots (LOCK-1) + PIT resolver.

The resolver returns the latest snapshot at-or-before signal_ts for a given
(spec_version, cadence). Missing → MissingRegimeSnapshot (NO FALLBACK).
"""
from __future__ import annotations

import datetime as dt
import hashlib
import sqlite3

import pandas as pd

from .db import to_utc_iso
from ..foundation.observation_builder import RegimeRegistryResolver, MissingRegimeSnapshot

DEFAULT_CADENCE = "HOURLY"   # RG1 LOCKED


def _row_hash(*f) -> str:
    return hashlib.sha256("|".join(str(x) for x in f).encode()).hexdigest()[:16]


class RegimeRegistry:
    """Append-only snapshot writer."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def add_snapshot(self, *, regime_ts: pd.Timestamp, regime_spec_version: str,
                     spy_trend=None, qqq_trend=None, iwm_trend=None, vix_level=None,
                     breadth_ratio=None, risk_state=None,
                     cadence=DEFAULT_CADENCE, source="derived") -> str:
        rt = to_utc_iso(regime_ts)
        rid = f"RGM_{regime_spec_version}_{cadence}_{rt.replace(':', '').replace('-', '')}"
        rh = _row_hash(rt, cadence, regime_spec_version, risk_state)
        self.conn.execute(
            """INSERT OR IGNORE INTO market_regime_registry
               (regime_snapshot_id, regime_ts, cadence, spy_trend, qqq_trend, iwm_trend,
                vix_level, breadth_ratio, risk_state, regime_spec_version, source,
                row_hash, ingested_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (rid, rt, cadence, spy_trend, qqq_trend, iwm_trend, vix_level, breadth_ratio,
             risk_state, regime_spec_version, source, rh,
             dt.datetime.now(dt.timezone.utc).isoformat()),
        )
        self.conn.commit()
        return rid


class RegimeRegistryResolverImpl(RegimeRegistryResolver):
    """R4 port. Latest snapshot at-or-before signal_ts; NO FALLBACK."""

    def __init__(self, conn: sqlite3.Connection, regime_spec_version: str,
                 cadence: str = DEFAULT_CADENCE):
        self.conn = conn
        self.spec = regime_spec_version
        self.cadence = cadence

    def resolve(self, as_of: pd.Timestamp) -> str:
        row = self.conn.execute(
            """SELECT regime_snapshot_id FROM market_regime_registry
               WHERE regime_spec_version=? AND cadence=? AND regime_ts <= ?
               ORDER BY regime_ts DESC LIMIT 1""",
            (self.spec, self.cadence, to_utc_iso(as_of)),
        ).fetchone()
        if row is None:
            raise MissingRegimeSnapshot(
                f"no {self.cadence} {self.spec} snapshot at/<= {as_of.isoformat()}")
        return row["regime_snapshot_id"]
