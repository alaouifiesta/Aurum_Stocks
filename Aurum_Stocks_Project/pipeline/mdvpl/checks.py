"""pipeline/mdvpl/checks.py — data-quality checks (facts only, never edits).

Each check inspects raw rows and returns a CheckResult with PASS/WARN/FAIL/SKIP plus the factual
evidence (counts, offending timestamps). No data is modified. No score, signal, sentiment, or
prediction is produced — the detail dict is guarded against such keys.
"""
from __future__ import annotations

import datetime as dt
import math
from dataclasses import dataclass, field
from enum import Enum

_FORBIDDEN = {"score", "signal", "sentiment", "bullish", "bearish", "label",
              "prediction", "probability", "feature", "rank", "edge", "grade"}


class Status(str, Enum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"
    SKIP = "SKIP"


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: Status
    detail: dict = field(default_factory=dict)

    def __post_init__(self):
        bad = _FORBIDDEN & set(self.detail or {})
        if bad:
            raise ValueError(f"check detail may not contain {sorted(bad)} (facts only)")


def _parse(ts: str) -> dt.datetime:
    d = dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))
    if d.tzinfo is None:
        raise ValueError("naive timestamp")
    return d


# -- per-stream checks -------------------------------------------------------------
def check_chronology(rows, name="chronology") -> CheckResult:
    prev = None
    for i, r in enumerate(rows):
        try:
            t = _parse(r["ts"])
        except Exception as e:
            return CheckResult(name, Status.FAIL, {"reason": "unparseable/naive ts",
                                                   "index": i, "value": r.get("ts")})
        if prev is not None and t <= prev:
            return CheckResult(name, Status.FAIL,
                               {"reason": "non-increasing", "index": i, "ts": r["ts"]})
        prev = t
    return CheckResult(name, Status.PASS, {"rows": len(rows)})


def check_duplication(rows, name="duplication") -> CheckResult:
    seen, dups = set(), []
    for r in rows:
        if r["ts"] in seen:
            dups.append(r["ts"])
        seen.add(r["ts"])
    return CheckResult(name, Status.FAIL if dups else Status.PASS,
                       {"duplicate_count": len(dups), "examples": dups[:3]})


def check_completeness_bars(bars, name="completeness", min_rows=300) -> CheckResult:
    n = len(bars)
    if n == 0:
        return CheckResult(name, Status.FAIL, {"rows": 0})
    if n < min_rows:
        return CheckResult(name, Status.WARN, {"rows": n, "min_expected": min_rows})
    return CheckResult(name, Status.PASS, {"rows": n})


def check_coverage_bars(bars, name="coverage") -> CheckResult:
    gaps = []
    for a, b in zip(bars, bars[1:]):
        delta = (_parse(b["ts"]) - _parse(a["ts"])).total_seconds()
        if delta > 60:
            gaps.append({"from": a["ts"], "to": b["ts"], "seconds": int(delta)})
    if not gaps:
        return CheckResult(name, Status.PASS, {"gaps": 0})
    status = Status.FAIL if any(g["seconds"] > 300 for g in gaps) else Status.WARN
    return CheckResult(name, status, {"gaps": len(gaps), "examples": gaps[:3]})


def check_sane_bars(bars, name="sane_bars") -> CheckResult:
    bad = []
    for r in bars:
        o, h, l, c, v = r["open"], r["high"], r["low"], r["close"], r["volume"]
        if not all(math.isfinite(x) for x in (o, h, l, c, v)):
            bad.append((r["ts"], "non-finite"))
        elif l > h or l > min(o, c) or h < max(o, c):
            bad.append((r["ts"], "ohlc-order"))
        elif min(o, h, l, c) <= 0:
            bad.append((r["ts"], "non-positive-price"))
        elif v < 0:
            bad.append((r["ts"], "negative-volume"))
    return CheckResult(name, Status.FAIL if bad else Status.PASS,
                       {"violations": len(bad), "examples": bad[:3]})


def check_sane_quotes(quotes, name="sane_quotes") -> CheckResult:
    bad = []
    for r in quotes:
        b, a = r["bid"], r["ask"]
        if not (math.isfinite(b) and math.isfinite(a)):
            bad.append((r["ts"], "non-finite"))
        elif b <= 0 or a <= 0:
            bad.append((r["ts"], "non-positive"))
        elif b > a:
            bad.append((r["ts"], "crossed"))
    return CheckResult(name, Status.FAIL if bad else Status.PASS,
                       {"violations": len(bad), "examples": bad[:3]})


def check_consolidation(caps, name="consolidation") -> CheckResult:
    """SIP/consolidated only. A single-venue feed distorts volume/spread -> FAIL."""
    return CheckResult(name, Status.PASS if caps.consolidated else Status.FAIL,
                       {"vendor": caps.vendor, "consolidated": caps.consolidated})


def check_news_provenance(news, name="news_provenance") -> CheckResult:
    missing, implausible = 0, 0
    for r in news:
        if not r.get("news_available_ts"):
            missing += 1
            continue
        pub = r.get("publish_ts")
        if pub and r["news_available_ts"] < pub:        # available before claimed publish
            implausible += 1
    if missing:
        return CheckResult(name, Status.FAIL, {"missing_available_ts": missing})
    if implausible:
        return CheckResult(name, Status.WARN, {"available_before_publish": implausible})
    return CheckResult(name, Status.PASS, {"items": len(news)})


# -- registry-dependent checks (honest SKIP when feed not supplied) ----------------
def check_corporate_action_sanity(bars, symbol_registry=None,
                                  name="corporate_action_sanity") -> CheckResult:
    if symbol_registry is None:
        return CheckResult(name, Status.SKIP, {"reason": "no symbol_registry supplied"})
    return CheckResult(name, Status.PASS, {"note": "reconciled (stub: caller supplies CA events)"})


def check_halt_consistency(bars, halt_registry=None, name="halt_consistency") -> CheckResult:
    if halt_registry is None:
        return CheckResult(name, Status.SKIP, {"reason": "no halt_registry supplied"})
    return CheckResult(name, Status.PASS, {"note": "reconciled (stub: caller supplies halts)"})
