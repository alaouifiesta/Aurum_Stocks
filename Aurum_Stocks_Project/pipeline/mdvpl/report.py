"""pipeline/mdvpl/report.py — the read-only quality report.

Aggregates the per-check results into a batch verdict and renders it. It MODIFIES NO DATA and
produces no features/scores — the verdict is PASS/WARN/FAIL derived from facts only.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict

from .checks import CheckResult, Status


def verdict_of(checks) -> Status:
    statuses = {c.status for c in checks}
    if Status.FAIL in statuses:
        return Status.FAIL
    if Status.WARN in statuses:
        return Status.WARN
    return Status.PASS


@dataclass
class QualityReport:
    vendor: str
    symbol: str
    date: str
    streams: tuple
    provenance_id: str
    content_hash: str
    checks: list = field(default_factory=list)

    @property
    def verdict(self) -> Status:
        return verdict_of(self.checks)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["verdict"] = self.verdict.value
        d["checks"] = [{"name": c.name, "status": c.status.value, "detail": c.detail}
                       for c in self.checks]
        return d

    def render(self) -> str:
        L = ["# Market Data Quality Report",
             f"vendor={self.vendor}  symbol={self.symbol}  date={self.date}  "
             f"streams={','.join(self.streams)}",
             f"provenance_id={self.provenance_id}",
             f"content_hash={self.content_hash[:16]}…",
             f"VERDICT: {self.verdict.value}", ""]
        for c in self.checks:
            det = "  ".join(f"{k}={v}" for k, v in c.detail.items())
            L.append(f"  [{c.status.value:<4}] {c.name:<24} {det}")
        L.append("")
        L.append("NOTE: read-only report — data is passed through UNCHANGED; no features created.")
        return "\n".join(L)
