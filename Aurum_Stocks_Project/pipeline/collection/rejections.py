"""pipeline/collection/rejections.py — append-only ledger of non-stored candidates.

Full-Population accounting requires that every candidate is accounted for: it is either stored
as an observation, or recorded here with a STRUCTURED reason_code (refinement #4) plus the
human-readable message. Nothing is ever silently dropped.

Two families of non-stored outcomes are recorded:
  * REJECTIONS — the frozen builder refused to sign the row. The machine codes mirror
    foundation.observation_builder exactly (ObservationRejected.reason for NO-FALLBACK resolver
    failures; a dedicated code for the GC-7 LongOnlyViolation hard-fail).
  * EXCLUSIONS — the row was validly built but must NOT enter the store (a burned
    CALIBRATION_ONLY slice never enters collection). Recorded as an exclusion, not an error.

The ledger is append-only (record-only API); it is never updated or deleted in place.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field


class RejectionCode:
    """Structured reason codes. The first five mirror builder ObservationRejected.reason."""
    MISSING_SYMBOL_VERSION = "MISSING_SYMBOL_VERSION"
    MISSING_REGIME_SNAPSHOT = "MISSING_REGIME_SNAPSHOT"
    UNKNOWN_SETUP = "UNKNOWN_SETUP"
    MISSING_UNIVERSE_VERSION = "MISSING_UNIVERSE_VERSION"
    UNKNOWN_SCANNER = "UNKNOWN_SCANNER"
    LONG_ONLY_VIOLATION = "LONG_ONLY_VIOLATION"          # GC-7 hard fail (not an ObservationRejected)
    BURNED_CALIBRATION_SLICE = "BURNED_CALIBRATION_SLICE"  # exclusion, not an error
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"                 # defensive catch-all

    # The codes that represent true builder rejections (vs. the burn exclusion).
    REJECTIONS = frozenset({
        MISSING_SYMBOL_VERSION, MISSING_REGIME_SNAPSHOT, UNKNOWN_SETUP,
        MISSING_UNIVERSE_VERSION, UNKNOWN_SCANNER, LONG_ONLY_VIOLATION, UNEXPECTED_ERROR,
    })
    EXCLUSIONS = frozenset({BURNED_CALIBRATION_SLICE})


@dataclass(frozen=True)
class RejectionRecord:
    candidate_key: str          # deterministic key (may be "" when rejection precedes signing)
    reason_code: str            # structured (RejectionCode.*)
    message: str                # human-readable detail
    symbol: str
    signal_ts: str              # UTC ISO
    setup_type: str
    scanner_id: str
    recorded_ts_utc: str = field(default="")

    @property
    def is_exclusion(self) -> bool:
        return self.reason_code in RejectionCode.EXCLUSIONS


class RejectionLedger:
    """Append-only list of RejectionRecords. Record-only; never mutated in place."""

    def __init__(self):
        self._records: list[RejectionRecord] = []

    def record(self, *, candidate_key: str, reason_code: str, message: str,
               symbol: str, signal_ts, setup_type: str = "", scanner_id: str = "") -> RejectionRecord:
        ts = signal_ts
        if hasattr(ts, "tz_convert"):
            ts = ts.tz_convert("UTC").isoformat()
        rec = RejectionRecord(
            candidate_key=candidate_key, reason_code=reason_code, message=message,
            symbol=symbol, signal_ts=str(ts), setup_type=setup_type, scanner_id=scanner_id,
            recorded_ts_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
        )
        self._records.append(rec)
        return rec

    def all(self) -> list[RejectionRecord]:
        return list(self._records)

    def rejections(self) -> list[RejectionRecord]:
        return [r for r in self._records if r.reason_code in RejectionCode.REJECTIONS]

    def exclusions(self) -> list[RejectionRecord]:
        return [r for r in self._records if r.reason_code in RejectionCode.EXCLUSIONS]

    def by_code(self, code: str) -> list[RejectionRecord]:
        return [r for r in self._records if r.reason_code == code]

    def count(self) -> int:
        return len(self._records)
