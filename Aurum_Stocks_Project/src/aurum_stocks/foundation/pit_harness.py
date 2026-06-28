"""
foundation/pit_harness.py  —  R3: the lookahead defense line.

A feature builder has signature:  f(bars, signal_ts) -> value
where `bars` is a 1-minute DataFrame indexed by tz-aware timestamps.

The harness computes every feature TWICE for each test case:
  1. on data TRUNCATED at signal_ts     (bars[index <= signal_ts])
  2. on the FULL frame, future included  (bars unchanged)
A point-in-time-correct feature ignores everything after signal_ts, so the two
values are identical. A feature that peeks into the future differs -> PIT_FAIL,
and it is rejected (must never be recorded into observation_features).

This is a standalone system, not an inline assertion: it runs over a registry of
feature builders against a battery of cases and emits a pass/fail report. The
ObservationBuilder (R4) only accepts features that have a PASS here.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import numpy as np
import pandas as pd

FeatureFn = Callable[[pd.DataFrame, pd.Timestamp], object]


@dataclass
class PITCase:
    bars: pd.DataFrame      # MUST include rows AFTER signal_ts to be a real test
    signal_ts: pd.Timestamp


@dataclass
class PITResult:
    feature_name: str
    passed: bool
    n_cases: int
    failures: list = field(default_factory=list)  # (case_idx, pit_value, full_value)

    @property
    def status(self) -> str:
        return "PASS" if self.passed else "PIT_FAIL"


def _equal(a, b, tol=1e-9) -> bool:
    if a is None or b is None:
        return a is b
    if isinstance(a, float) or isinstance(b, float):
        try:
            if np.isnan(a) and np.isnan(b):
                return True
        except TypeError:
            pass
        return abs(float(a) - float(b)) <= tol
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(_equal(a[k], b[k], tol) for k in a)
    return a == b


def validate_feature(name: str, fn: FeatureFn, cases: list[PITCase]) -> PITResult:
    failures = []
    for i, case in enumerate(cases):
        truncated = case.bars.loc[case.bars.index <= case.signal_ts]
        val_pit = fn(truncated, case.signal_ts)
        val_full = fn(case.bars, case.signal_ts)
        if not _equal(val_pit, val_full):
            failures.append((i, val_pit, val_full))
    return PITResult(name, passed=not failures, n_cases=len(cases), failures=failures)


def validate_registry(feature_fns: dict[str, FeatureFn],
                      cases: list[PITCase]) -> dict[str, PITResult]:
    """Run every feature; a feature is registerable only if its result PASSES."""
    return {name: validate_feature(name, fn, cases) for name, fn in feature_fns.items()}


def render_report(results: dict[str, PITResult]) -> str:
    lines = ["PIT VALIDATION REPORT", "=" * 40]
    for name, res in sorted(results.items()):
        lines.append(f"[{res.status:8}] {name}  ({res.n_cases} cases)")
        for idx, vp, vf in res.failures[:3]:
            lines.append(f"            case#{idx}: pit={vp!r} != full={vf!r}")
    n_fail = sum(1 for r in results.values() if not r.passed)
    lines += ["-" * 40, f"{len(results)} features, {n_fail} PIT_FAIL"]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# HARNESS FIXTURES ONLY — these are NOT production features. They exist solely
# to prove the harness catches leakage. (Phase-1 scope: infrastructure, not
# strategy features.)
# ---------------------------------------------------------------------------
def fixture_trailing_return(bars: pd.DataFrame, signal_ts) -> float:
    """PIT-safe: uses only bars at/before signal_ts."""
    past = bars.loc[bars.index <= signal_ts]
    if len(past) < 6:
        return 0.0
    return float(past["close"].iloc[-1] / past["close"].iloc[-6] - 1.0)


def fixture_peek_next_bar(bars: pd.DataFrame, signal_ts) -> float:
    """DELIBERATELY LEAKY: reads the bar AFTER signal_ts. The harness must FAIL it."""
    after = bars.loc[bars.index > signal_ts]
    if after.empty:
        return 0.0
    return float(after["close"].iloc[0])
