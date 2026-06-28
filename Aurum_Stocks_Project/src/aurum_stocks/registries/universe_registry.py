"""
registries/universe_registry.py — versioned tradeable universes (CHANGE #2).

Append-only membership RULES (SMALL_CAP_US, ...). Membership is DERIVED point-in-time
from the rule + symbol_registry (so it inherits anti-survivorship). Each Observation
carries the universe_version_id it was scanned under.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import sqlite3

import pandas as pd

from .db import to_utc_iso
from ..foundation.observation_builder import UniverseRegistryResolver, MissingUniverseVersion


def _row_hash(*f) -> str:
    return hashlib.sha256("|".join(str(x) for x in f).encode()).hexdigest()[:16]


class UniverseRegistry:
    """Append-only versioned universe membership rules."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def add_universe(self, *, universe_id: str, universe_spec_version: str,
                     membership_rule: dict, valid_from: pd.Timestamp,
                     source="manual") -> str:
        uvid = f"{universe_id}@{universe_spec_version}"
        vf = to_utc_iso(valid_from)
        rule_json = json.dumps(membership_rule, sort_keys=True)
        rh = _row_hash(universe_id, universe_spec_version, rule_json, vf)
        self.conn.execute(
            """INSERT OR IGNORE INTO universe_registry
               (universe_version_id, universe_id, universe_spec_version, membership_rule,
                valid_from, created_at, source, row_hash)
               VALUES (?,?,?,?,?,?,?,?)""",
            (uvid, universe_id, universe_spec_version, rule_json, vf,
             dt.datetime.now(dt.timezone.utc).isoformat(), source, rh),
        )
        self.conn.commit()
        return uvid


class UniverseRegistryResolverImpl(UniverseRegistryResolver):
    """R4 port. PIT resolution of the universe spec; NO FALLBACK."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def resolve(self, universe_id: str, as_of: pd.Timestamp) -> str:
        row = self.conn.execute(
            """SELECT universe_version_id FROM universe_registry
               WHERE universe_id=? AND valid_from <= ?
               ORDER BY valid_from DESC LIMIT 1""",
            (universe_id, to_utc_iso(as_of)),
        ).fetchone()
        if row is None:
            raise MissingUniverseVersion(f"{universe_id} @ {as_of.isoformat()}: no PIT version")
        return row["universe_version_id"]

    def members(self, universe_id: str, as_of: pd.Timestamp, symbol_conn) -> list[str]:
        """Derived PIT membership = structural rule applied to the symbol_registry PIT
        universe. Price/ADV/RVOL filters are applied by the scanner with market data;
        here we apply the structural filters (listed, not ETF/ADR/SPAC, float buckets)."""
        uvid = self.resolve(universe_id, as_of)
        rule = json.loads(self.conn.execute(
            "SELECT membership_rule FROM universe_registry WHERE universe_version_id=?",
            (uvid,)).fetchone()["membership_rule"])
        allowed_buckets = set(rule.get("float_buckets", []))
        exclude_etf = rule.get("exclude_is_etf", True)
        exclude_adr = rule.get("exclude_is_adr", True)
        exclude_spac = rule.get("exclude_is_spac", True)
        d = as_of.date().isoformat()
        rows = symbol_conn.execute(
            """SELECT sr.symbol, sr.float_bucket, sr.is_etf, sr.is_adr, sr.is_spac
               FROM symbol_registry sr
               WHERE sr.valid_from <= ? AND sr.active_from <= ?
                 AND (sr.active_to IS NULL OR ? < sr.active_to)
                 AND sr.valid_from = (
                     SELECT MAX(valid_from) FROM symbol_registry s2
                     WHERE s2.symbol = sr.symbol AND s2.valid_from <= ?)""",
            (to_utc_iso(as_of), d, d, to_utc_iso(as_of)),
        ).fetchall()
        out = []
        for r in rows:
            if exclude_etf and r["is_etf"]:
                continue
            if exclude_adr and r["is_adr"]:
                continue
            if exclude_spac and r["is_spac"]:
                continue
            if allowed_buckets and r["float_bucket"] not in allowed_buckets:
                continue
            out.append(r["symbol"])
        return sorted(out)
