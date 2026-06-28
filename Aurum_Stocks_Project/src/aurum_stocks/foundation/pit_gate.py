"""
foundation/pit_gate.py — the PIT Feature Gate (PASS / FAIL / UNKNOWN).

Generalises the R3 harness into the registration gate. Only PASS admits a feature;
FAIL and UNKNOWN both REJECT (your lock: UNKNOWN == REJECTED). UNKNOWN means the
harness could not *prove* safety (insufficient coverage) — "untested" is not "safe".
Re-testing after UNKNOWN is legitimate (PIT-safety is deterministic, not statistical).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum

from .pit_harness import PITCase, validate_feature


class Verdict(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"


@dataclass
class GateRun:
    pit_run_id: str
    feature_name: str
    feature_version: str
    verdict: Verdict
    n_cases: int
    coverage: dict
    remediation: str  # "" if PASS; else NEW_VERSION / NEW_TEST_PACK

    @property
    def admits(self) -> bool:
        return self.verdict is Verdict.PASS


def run_gate(feature_name: str, feature_version: str, fn, cases: list[PITCase],
             lookback_window: int = 0) -> GateRun:
    rid = f"PIT_{uuid.uuid4().hex[:10]}"

    # 1) deterministic correctness: truncated vs full must agree.
    res = validate_feature(feature_name, fn, cases)

    # 2) coverage diagnostics (else the PASS would be unprovable).
    has_future = any((c.bars.index > c.signal_ts).any() for c in cases)
    n_positions = len({c.signal_ts for c in cases})
    vals = [fn(c.bars.loc[c.bars.index <= c.signal_ts], c.signal_ts) for c in cases]
    not_all_null = any(v is not None and v == v for v in vals)  # v==v rejects NaN
    lookback_ok = (lookback_window == 0) or any(
        (c.bars.index <= c.signal_ts).sum() >= lookback_window for c in cases)
    coverage = {"has_future_bars": has_future, "n_positions": n_positions,
                "not_all_null": not_all_null, "lookback_exercised": lookback_ok}

    if res.failures:
        verdict, remediation = Verdict.FAIL, "NEW_VERSION"
    elif not (has_future and n_positions >= 2 and not_all_null and lookback_ok):
        verdict, remediation = Verdict.UNKNOWN, "NEW_TEST_PACK"  # or NEW_VERSION
    else:
        verdict, remediation = Verdict.PASS, ""

    return GateRun(rid, feature_name, feature_version, verdict,
                   len(cases), coverage, remediation)


class PITGateLedger:
    """Append-only record of gate runs; the feature registry references these ids."""

    def __init__(self):
        self._runs: dict[str, GateRun] = {}

    def record(self, run: GateRun) -> str:
        self._runs[run.pit_run_id] = run
        return run.pit_run_id

    def verdict_of(self, pit_run_id: str) -> Verdict:
        return self._runs[pit_run_id].verdict

    def get(self, pit_run_id: str) -> GateRun:
        return self._runs[pit_run_id]
