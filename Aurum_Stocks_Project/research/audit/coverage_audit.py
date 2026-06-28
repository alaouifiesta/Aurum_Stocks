"""research/audit/coverage_audit.py — read-only data-coverage & collection-integrity reports.

Reporting ONLY. It changes no gate, writes no data, computes no features. It surfaces
problems a collected dataset might have so a human can investigate:

  duplicate observations · orphan observations / missing registry references ·
  signature integrity · PIT violations · long-only violations ·
  regime / symbol / label / month coverage · news coverage · and hooks for
  missing-bars / halt / corporate-action coverage (which require their feeds).

Each function takes already-loaded inputs; nothing here reaches into production.
"""
from __future__ import annotations

from collections import Counter
from typing import Iterable

from aurum_stocks.foundation.observation_builder import ObservationRow, registry_signature


# -- integrity-of-collection checks ------------------------------------------------
def duplicate_observations(rows: Iterable[ObservationRow]) -> list[tuple]:
    """Full-population collection expects ONE observation per candidate. A repeated
    (symbol, signal_ts, setup_type) is a duplicate to investigate."""
    seen = Counter((r.symbol, r.signal_ts_utc, r.setup_type) for r in rows)
    return [k for k, n in seen.items() if n > 1]


def signature_integrity(rows: Iterable[ObservationRow]) -> list[str]:
    """observation_ids whose stored signature != recomputed signature."""
    bad = []
    for r in rows:
        if r.registry_signature_hash != registry_signature(
                r.symbol_registry_id, r.regime_snapshot_id, r.setup_version,
                r.label_spec_id, r.universe_version_id, r.scanner_version_id):
            bad.append(r.observation_id)
    return bad


def pit_violations(rows: Iterable[ObservationRow]) -> list[str]:
    return [r.observation_id for r in rows if r.data_as_of_ts > r.signal_ts_utc]


def long_only_violations(rows: Iterable[ObservationRow]) -> list[str]:
    return [r.observation_id for r in rows if r.direction != "LONG"]


def orphan_observations(rows: Iterable[ObservationRow], known: dict) -> dict:
    """Rows referencing a registry version NOT present in the provided `known` sets.
    `known` = {"symbol": set(...), "regime": set(...), "setup": set(...),
               "label": set(...), "universe": set(...), "scanner": set(...)}.
    Returns a per-dimension dict of offending observation_ids (missing registry refs)."""
    def miss(attr, bucket):
        s = known.get(bucket)
        if s is None:
            return []
        return [r.observation_id for r in rows if getattr(r, attr) not in s]
    return {
        "symbol": miss("symbol_registry_id", "symbol"),
        "regime": miss("regime_snapshot_id", "regime"),
        "setup": miss("setup_version", "setup"),
        "label": miss("label_spec_id", "label"),
        "universe": miss("universe_version_id", "universe"),
        "scanner": miss("scanner_version_id", "scanner"),
    }


# -- coverage summaries ------------------------------------------------------------
def coverage(rows: Iterable[ObservationRow]) -> dict:
    rows = list(rows)
    return {
        "observations": len(rows),
        "distinct_regimes": len({r.regime_snapshot_id for r in rows}),
        "distinct_symbols": len({r.symbol for r in rows}),
        "distinct_labels": len({r.label_spec_id for r in rows}),
        "distinct_months": len({(r.signal_ts_utc or "")[:7] for r in rows}),
        "distinct_universes": len({r.universe_version_id for r in rows}),
    }


def news_coverage(rows: Iterable[ObservationRow], archive) -> dict:
    """For each observation, was any news AVAILABLE at-or-before signal_ts (PIT)?
    Coverage statistic only — NOT a feature, never fed to a model."""
    rows = list(rows)
    with_news = 0
    for r in rows:
        if archive.available_as_of(r.symbol, r.signal_ts_utc):
            with_news += 1
    n = len(rows)
    return {"observations": n, "with_available_news": with_news,
            "without_news": n - with_news,
            "coverage_pct": round(100.0 * with_news / n, 1) if n else 0.0}


# Feed-dependent hooks: honest "not available without the feed" rather than fabricate.
def missing_bars(data_quality_registry=None) -> dict:
    return {"status": "REQUIRES_DATA_QUALITY_FEED" if data_quality_registry is None
            else "see data_quality_registry RETROSPECTIVE records"}


def halt_coverage(halt_registry=None) -> dict:
    return {"status": "REQUIRES_HALT_REGISTRY" if halt_registry is None else "available"}


def corporate_action_coverage(symbol_registry=None) -> dict:
    return {"status": "REQUIRES_SYMBOL_REGISTRY_CA" if symbol_registry is None else "available"}


# -- render ------------------------------------------------------------------------
def render_report(rows: Iterable[ObservationRow], *, known: dict | None = None,
                  archive=None) -> str:
    rows = list(rows)
    L = ["# Data Coverage Audit", ""]
    cov = coverage(rows)
    L.append("## coverage")
    for k, v in cov.items():
        L.append(f"   {k}: {v}")
    L.append("")
    L.append("## integrity")
    dups = duplicate_observations(rows)
    L.append(f"   duplicate_observations: {len(dups)}")
    L.append(f"   signature_integrity_failures: {len(signature_integrity(rows))}")
    L.append(f"   pit_violations: {len(pit_violations(rows))}")
    L.append(f"   long_only_violations: {len(long_only_violations(rows))}")
    if known is not None:
        orphans = orphan_observations(rows, known)
        total_orphans = sum(len(v) for v in orphans.values())
        L.append(f"   orphan_observations (missing registry refs): {total_orphans}")
        for dim, ids in orphans.items():
            if ids:
                L.append(f"      {dim}: {len(ids)}")
    L.append("")
    L.append("## news coverage")
    if archive is not None:
        nc = news_coverage(rows, archive)
        L.append(f"   with_available_news: {nc['with_available_news']}/{nc['observations']} "
                 f"({nc['coverage_pct']}%)")
    else:
        L.append("   (no news archive supplied)")
    L.append("")
    L.append("## feed-dependent coverage")
    L.append(f"   missing_bars: {missing_bars()['status']}")
    L.append(f"   halt_coverage: {halt_coverage()['status']}")
    L.append(f"   corporate_action_coverage: {corporate_action_coverage()['status']}")
    return "\n".join(L)
