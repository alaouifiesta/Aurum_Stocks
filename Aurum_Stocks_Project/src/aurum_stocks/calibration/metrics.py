"""
calibration/metrics.py — label-property aggregation.

ALLOWED (Engineering Directive, Priority #1):
    Profit %, Stop %, Time %, Median Time To Resolution,
    Barrier Distance vs Typical Spread, Class Balance.

FORBIDDEN here by directive (NOT computed anywhere in this framework):
    AUC, Correlation, Feature Importance, ML, Sharpe, Strategy testing.

The goal is a stable, balanced LABEL definition — never performance.
TB4 helper: the sign breakdown of TIME-resolved returns is a pure label
property (not predictiveness), reported to inform the TIME-encoding choice.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict

import numpy as np

from . import config


@dataclass
class CellMetrics:
    k: float
    h_min: int
    n: int
    profit_pct: float
    stop_pct: float
    time_pct: float
    median_ttr_min: float          # over resolved (PROFIT|STOP) outcomes
    barrier_spread_ratio: float    # median (k*ATR)/spread
    min_class_fraction: float
    class_entropy: float           # normalized 0..1 (1 = perfectly balanced 3-class)
    # TB4 label property: among TIME outcomes, sign of return at the horizon.
    time_pos_pct: float
    time_neg_pct: float
    time_flat_pct: float
    degenerate: bool
    degenerate_reasons: tuple

    def as_dict(self):
        d = asdict(self)
        d["degenerate_reasons"] = list(self.degenerate_reasons)
        return d


def _entropy3(p, s, t) -> float:
    probs = [x for x in (p, s, t) if x > 0]
    if not probs:
        return 0.0
    h = -sum(x * np.log(x) for x in probs)
    return float(h / np.log(3))  # normalize to [0,1]


def aggregate(k: float, h_min: int, outcomes: list) -> CellMetrics:
    n = len(outcomes)
    if n == 0:
        return CellMetrics(k, h_min, 0, *([0.0] * 11), True, ("no_samples",))

    barriers = np.array([o.barrier for o in outcomes])
    n_profit = int((barriers == "PROFIT").sum())
    n_stop = int((barriers == "STOP").sum())
    n_time = int((barriers == "TIME").sum())
    p, s, t = n_profit / n, n_stop / n, n_time / n

    resolved_ttr = [o.ttr_min for o in outcomes if o.barrier in ("PROFIT", "STOP")]
    median_ttr = float(np.median(resolved_ttr)) if resolved_ttr else float(h_min)

    ratios = [o.barrier_distance / o.spread for o in outcomes if o.spread > 0]
    bsr = float(np.median(ratios)) if ratios else 0.0

    # TB4: sign of TIME-resolved returns.
    time_rets = np.array([o.realized_return for o in outcomes if o.barrier == "TIME"])
    if time_rets.size:
        tp = float((time_rets > 0).mean())
        tn = float((time_rets < 0).mean())
        tf = float((time_rets == 0).mean())
    else:
        tp = tn = tf = 0.0

    min_class = min(p, s, t)
    ent = _entropy3(p, s, t)

    reasons = []
    if t > config.MAX_TIME_FRACTION:
        reasons.append(f"time%>{config.MAX_TIME_FRACTION:.0%}")
    if min_class < config.MIN_CLASS_FRACTION:
        reasons.append(f"min_class<{config.MIN_CLASS_FRACTION:.0%}")
    if bsr < config.MIN_BARRIER_SPREAD_RATIO:
        reasons.append(f"barrier/spread<{config.MIN_BARRIER_SPREAD_RATIO:g}")
    degenerate = bool(reasons)

    return CellMetrics(
        k=k, h_min=h_min, n=n,
        profit_pct=p, stop_pct=s, time_pct=t,
        median_ttr_min=median_ttr, barrier_spread_ratio=bsr,
        min_class_fraction=min_class, class_entropy=ent,
        time_pos_pct=tp, time_neg_pct=tn, time_flat_pct=tf,
        degenerate=degenerate, degenerate_reasons=tuple(reasons),
    )
