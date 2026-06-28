"""pipeline/mdvpl/validator.py — the Market Data Validation & Provenance orchestrator.

Given a provider-agnostic source, it: fetches raw data READ-ONLY, runs the data-quality checks,
records an append-only provenance record, and returns a quality report PLUS the data UNCHANGED
(pass-through). It never edits, repairs, fills, re-times, or transforms data, and it creates no
features, observations, scores, or signals.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
from dataclasses import dataclass

from . import checks as C
from .provenance import ProvenanceLog, ProvenanceRecord
from .report import QualityReport


@dataclass
class ValidationResult:
    report: QualityReport
    provenance: ProvenanceRecord
    data: dict            # {stream: rows}  — exactly what the source returned (UNCHANGED)


class MarketDataValidator:
    def __init__(self, provenance_log: ProvenanceLog | None = None):
        self.log = provenance_log

    def validate(self, source, symbol: str, date: dt.date, *,
                 streams=("bars", "quotes"),
                 symbol_registry=None, halt_registry=None) -> ValidationResult:
        caps = source.capabilities()

        # 1) fetch raw, read-only (kept verbatim — pass-through)
        data: dict = {}
        if "bars" in streams:
            data["bars"] = source.minute_bars(symbol, date)
        if "quotes" in streams:
            data["quotes"] = source.quotes(symbol, date)
        if "trades" in streams:
            data["trades"] = source.trades(symbol, date)
        if "news" in streams:
            start = dt.datetime.combine(date, dt.time(0, 0), dt.timezone.utc).isoformat()
            end = dt.datetime.combine(date, dt.time(23, 59), dt.timezone.utc).isoformat()
            data["news"] = source.news(symbol, start, end)

        # 2) content hash over the raw batch (provenance / dedup key)
        content_hash = hashlib.sha256(
            json.dumps(data, sort_keys=True, default=str).encode("utf-8")).hexdigest()

        # 3) run checks (facts only; never edits)
        results = [C.check_consolidation(caps)]
        if "bars" in data:
            bars = data["bars"]
            results += [
                C.check_chronology(bars, "bars_chronology"),
                C.check_duplication(bars, "bars_duplication"),
                C.check_completeness_bars(bars),
                C.check_coverage_bars(bars),
                C.check_sane_bars(bars),
                C.check_corporate_action_sanity(bars, symbol_registry),
                C.check_halt_consistency(bars, halt_registry),
            ]
        if "quotes" in data:
            results += [
                C.check_chronology(data["quotes"], "quotes_chronology"),
                C.check_sane_quotes(data["quotes"]),
            ]
        if "trades" in data:
            results.append(C.check_chronology(data["trades"], "trades_chronology"))
        if "news" in data:
            results.append(C.check_news_provenance(data["news"]))

        from .report import verdict_of
        verdict = verdict_of(results)
        row_count = sum(len(v) for v in data.values())

        # 4) append-only provenance record
        rec = ProvenanceRecord.new(
            vendor=caps.vendor, adapter_version=getattr(source, "adapter_version", "0"),
            streams=",".join(streams), symbol=symbol,
            range_start=str(date), range_end=str(date),
            feed_type="CONSOLIDATED_SIP" if caps.consolidated else "SINGLE_VENUE",
            row_count=row_count, content_hash=content_hash,
            fetch_ts_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
            verdict=verdict.value)
        if self.log is not None:
            self.log.record(rec)

        # 5) read-only report (+ pass-through data)
        report = QualityReport(vendor=caps.vendor, symbol=symbol, date=str(date),
                               streams=tuple(streams), provenance_id=rec.provenance_id,
                               content_hash=content_hash, checks=results)
        return ValidationResult(report=report, provenance=rec, data=data)
