"""research/explore/dataset_explorer.py — read-only dataset statistics (counts only).

Answers "how many observations? per regime / setup / symbol / month / universe / label?"
These are COUNTS. There is no analytics, no ranking, no correlation, no AUC, no ML, and
nothing that touches outcomes or the future. Operates on any iterable of ObservationRows.
"""
from __future__ import annotations

from collections import Counter
from typing import Iterable

from aurum_stocks.foundation.observation_builder import ObservationRow


def _counts(rows: Iterable[ObservationRow], key) -> dict:
    return dict(sorted(Counter(key(r) for r in rows).items()))


def total(rows: Iterable[ObservationRow]) -> int:
    return sum(1 for _ in rows)


def by_regime(rows):   return _counts(rows, lambda r: r.regime_snapshot_id)
def by_setup(rows):    return _counts(rows, lambda r: r.setup_type)
def by_symbol(rows):   return _counts(rows, lambda r: r.symbol)
def by_universe(rows): return _counts(rows, lambda r: r.universe_version_id)
def by_label(rows):    return _counts(rows, lambda r: r.label_spec_id)
def by_month(rows):    return _counts(rows, lambda r: (r.signal_ts_utc or "")[:7])
def by_role(rows):     return _counts(rows, lambda r: str(r.dataset_role))


def summary(rows: Iterable[ObservationRow]) -> dict:
    rows = list(rows)
    return {
        "total": len(rows),
        "by_regime": by_regime(rows),
        "by_setup": by_setup(rows),
        "by_symbol": by_symbol(rows),
        "by_month": by_month(rows),
        "by_universe": by_universe(rows),
        "by_label": by_label(rows),
        "by_role": by_role(rows),
    }


def render(rows: Iterable[ObservationRow]) -> str:
    s = summary(rows)
    L = [f"OBSERVATIONS: {s['total']}", ""]
    for dim in ("by_regime", "by_setup", "by_symbol", "by_month", "by_universe",
                "by_label", "by_role"):
        L.append(f"{dim}:")
        for k, v in s[dim].items():
            L.append(f"   {k or '(blank)'}: {v}")
        L.append("")
    return "\n".join(L)
