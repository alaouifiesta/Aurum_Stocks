"""
registries/symbol_registry.py — SCD-2, point-in-time, NO-FALLBACK resolver.

Writer applies the §1.4.1 versioning trigger policy (categorical change, or
shares/float move beyond a materiality threshold, or a bucket crossing). Resolver
implements the R4 SymbolRegistryResolver port and obeys LOCK-2: a missing version
raises MissingSymbolVersion (never a fallback to the latest).
"""
from __future__ import annotations

import datetime as dt
import hashlib
import sqlite3

import pandas as pd

from .db import to_utc_iso
from ..foundation.observation_builder import SymbolRegistryResolver, MissingSymbolVersion

MATERIAL_CHANGE_PCT = 0.01  # SR2 (proposed): |Δ| >= 1% of value triggers a version

# Float buckets (free-float shares). Boundaries are re-bucketable (raw stored).
FLOAT_BUCKETS = [(20e6, "MICRO"), (75e6, "SMALL"), (300e6, "MID"), (float("inf"), "LARGE")]


def float_bucket(free_float: float | None) -> str | None:
    if free_float is None:
        return None
    for hi, name in FLOAT_BUCKETS:
        if free_float < hi:
            return name
    return "LARGE"


def _row_hash(*fields) -> str:
    return hashlib.sha256("|".join(str(f) for f in fields).encode()).hexdigest()[:16]


class SymbolRegistry:
    """Append-only SCD-2 writer."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def _latest(self, symbol: str) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM symbol_registry WHERE symbol=? ORDER BY valid_from DESC LIMIT 1",
            (symbol,),
        ).fetchone()

    def upsert(self, *, symbol, valid_from: pd.Timestamp, exchange, sector,
               shares_outstanding, free_float, listing_status,
               active_from: dt.date, active_to: dt.date | None = None,
               country=None, is_etf=False, is_adr=False, is_spac=False,
               borrowable_flag=True,
               attr_as_of: pd.Timestamp | None = None, source="vendor") -> str | None:
        """Append a new version IFF the trigger policy fires. Returns the
        symbol_registry_id of the (new or existing) governing version, or the new id;
        returns None only if nothing was written AND no prior version exists."""
        prev = self._latest(symbol)
        fb = float_bucket(free_float)
        reason = None
        if prev is None:
            reason = "INITIAL"
        else:
            cat_changed = (
                exchange != prev["exchange"] or sector != prev["sector"]
                or listing_status != prev["listing_status"]
                or country != prev["country"]
                or int(is_etf) != prev["is_etf"] or int(is_adr) != prev["is_adr"]
                or int(is_spac) != prev["is_spac"]
                or int(borrowable_flag) != prev["borrowable_flag"])
            if cat_changed:
                reason = "CATEGORICAL"
            elif fb != prev["float_bucket"]:
                reason = "BUCKET_CROSS"
            elif _rel_change(shares_outstanding, prev["shares_outstanding"]) >= MATERIAL_CHANGE_PCT:
                reason = "SHARES_THRESHOLD"
            elif _rel_change(free_float, prev["float_raw"]) >= MATERIAL_CHANGE_PCT:
                reason = "FLOAT_THRESHOLD"
        if reason is None:
            return prev["symbol_registry_id"]  # dedup: immaterial vendor refresh

        seq = self.conn.execute(
            "SELECT COUNT(*) c FROM symbol_registry WHERE symbol=?", (symbol,)
        ).fetchone()["c"] + 1
        srid = f"{symbol}#{seq:04d}"
        vf = to_utc_iso(valid_from)
        rh = _row_hash(symbol, exchange, sector, shares_outstanding, free_float,
                       fb, listing_status, country, is_etf, is_adr, is_spac,
                       borrowable_flag, vf)
        self.conn.execute(
            """INSERT INTO symbol_registry
               (symbol_registry_id, symbol, exchange, sector, shares_outstanding,
                float_raw, float_bucket, listing_status, country, is_etf, is_adr,
                is_spac, borrowable_flag, active_from, active_to,
                valid_from, attr_as_of, version_reason, source, row_hash, ingested_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (srid, symbol, exchange, sector, shares_outstanding, free_float, fb,
             listing_status, country, int(is_etf), int(is_adr), int(is_spac),
             int(borrowable_flag), active_from.isoformat(),
             active_to.isoformat() if active_to else None,
             vf, to_utc_iso(attr_as_of) if attr_as_of is not None else None,
             reason, source, rh, dt.datetime.now(dt.timezone.utc).isoformat()),
        )
        self.conn.commit()
        return srid


def _rel_change(a, b) -> float:
    if a is None or b is None or b == 0:
        return float("inf") if a != b else 0.0
    return abs(a - b) / abs(b)


class SymbolRegistryResolverImpl(SymbolRegistryResolver):
    """R4 port. PIT lookup; NO FALLBACK (LOCK-2)."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def resolve(self, symbol: str, as_of: pd.Timestamp) -> str:
        row = self.conn.execute(
            """SELECT symbol_registry_id, active_from, active_to, listing_status
               FROM symbol_registry
               WHERE symbol=? AND valid_from <= ?
               ORDER BY valid_from DESC LIMIT 1""",
            (symbol, to_utc_iso(as_of)),
        ).fetchone()
        if row is None:
            raise MissingSymbolVersion(f"{symbol} @ {as_of.isoformat()}: no PIT version")
        # universe membership at as_of (anti-survivorship; no fallback)
        d = as_of.date().isoformat()
        if not (row["active_from"] <= d and (row["active_to"] is None or d < row["active_to"])):
            raise MissingSymbolVersion(f"{symbol} not in PIT universe @ {d}")
        return row["symbol_registry_id"]

    def universe(self, as_of: pd.Timestamp) -> list[str]:
        """Point-in-time universe: symbols listed at as_of (incl. later-delisted)."""
        d = as_of.date().isoformat()
        rows = self.conn.execute(
            """SELECT DISTINCT symbol FROM symbol_registry
               WHERE active_from <= ? AND (active_to IS NULL OR ? < active_to)""",
            (d, d),
        ).fetchall()
        return sorted(r["symbol"] for r in rows)
