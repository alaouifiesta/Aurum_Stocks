"""pipeline/collection/candidate_source.py — where candidates come from.

The Collection Layer OBSERVES candidates; it does not DETECT them. "Full-Population
Observation" means every candidate a source yields becomes exactly one observation (or one
recorded rejection) — never a filtered/ranked subset. Detection (scanner logic, scoring,
ranking) is a separate, currently-RESERVED component (src/aurum_stocks/scanners/, Priority #3)
and is explicitly OUT OF SCOPE for Phase 2.

  CandidateSource     the port: candidates(symbol, date) -> iterable[SignalEvent].
  MockCandidateSource deterministic, edge-free test/demo source. It emits LONG candidates at
                      fixed RTH minutes with opaque setup/scanner/universe ids and NO score or
                      rank (scanner_score/scanner_rank stay None — computing them would be
                      scanner logic, which is forbidden here).
"""
from __future__ import annotations

import datetime as dt
from abc import ABC, abstractmethod
from collections.abc import Iterable
from zoneinfo import ZoneInfo

import pandas as pd

from aurum_stocks.foundation.observation_builder import SignalEvent

ET = ZoneInfo("America/New_York")


class CandidateSource(ABC):
    """Read-only source of candidate SignalEvents for a (symbol, trading-day)."""

    @abstractmethod
    def candidates(self, symbol: str, date: dt.date) -> Iterable[SignalEvent]:
        ...


class MockCandidateSource(CandidateSource):
    """Deterministic, edge-free candidate source for tests/demo.

    For each (symbol, day) it emits a fixed, reproducible set of candidates at the configured
    RTH minutes. No randomness, no scoring, no ranking, no setup branching — pure plumbing
    input so the Collection Engine's full-population behaviour can be exercised.
    """

    def __init__(
        self,
        *,
        minutes: tuple[tuple[int, int], ...] = ((10, 0), (11, 0), (14, 30)),
        setup_type: str = "GAP_GO",
        scanner_id: str = "SCAN_MOMENTUM",
        universe_id: str = "SMALL_CAP_US",
    ):
        self.minutes = minutes
        self.setup_type = setup_type
        self.scanner_id = scanner_id
        self.universe_id = universe_id

    def candidates(self, symbol: str, date: dt.date) -> list[SignalEvent]:
        out: list[SignalEvent] = []
        for i, (hh, mm) in enumerate(self.minutes):
            ts = pd.Timestamp(dt.datetime.combine(date, dt.time(hh, mm), ET))
            out.append(
                SignalEvent(
                    symbol=symbol,
                    signal_ts=ts,
                    setup_type=self.setup_type,
                    direction="LONG",                      # full-population is long-only here
                    scanner_id=self.scanner_id,
                    universe_id=self.universe_id,
                    scanner_score=None,                    # NO edge / NO score computed
                    scanner_rank=None,                     # NO ranking computed
                    candidate_batch_id=f"{symbol}|{date}",
                )
            )
        return out
