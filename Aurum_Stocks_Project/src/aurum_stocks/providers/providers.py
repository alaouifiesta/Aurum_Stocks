"""
registries/providers.py — provider interfaces + MOCK implementations.

Where real SIP/vendor data is required, the system depends on these ABCs, never on a
concrete vendor. Mock providers return deterministic canned data so the registries are
buildable and testable with no network and no real SIP. (Mirrors the calibration
DataProvider ABC + SyntheticDataProvider pattern.)
"""
from __future__ import annotations

import datetime as dt
from abc import ABC, abstractmethod

import pandas as pd


# ---- interfaces -------------------------------------------------------------
class NewsProvider(ABC):
    @abstractmethod
    def fetch(self, symbol: str, day: dt.date) -> list[dict]:
        """Each item: {publish_ts, available_ts, source, vendor, headline_hash, category}."""


class HaltProvider(ABC):
    @abstractmethod
    def fetch(self, symbol: str, day: dt.date) -> list[dict]:
        """Each item: {halt_start_ts, halt_end_ts, halt_reason, luld_band_pct, resumption_ts}."""


class DataQualityProvider(ABC):
    @abstractmethod
    def assess_as_of(self, symbol: str, as_of: pd.Timestamp) -> dict: ...
    @abstractmethod
    def assess_session(self, symbol: str, day: dt.date) -> dict: ...


# ---- mock implementations ---------------------------------------------------
def _et(day: dt.date, hh: int, mm: int) -> pd.Timestamp:
    return pd.Timestamp(dt.datetime(day.year, day.month, day.day, hh, mm),
                        tz="America/New_York")


class MockNewsProvider(NewsProvider):
    """One headline at 09:31 ET published, delivered (available) 3 minutes later."""
    def fetch(self, symbol, day):
        pub = _et(day, 9, 31)
        return [{"publish_ts": pub, "available_ts": pub + pd.Timedelta(minutes=3),
                 "source": "PR_NEWSWIRE", "vendor": "MOCK",
                 "headline_hash": f"h_{symbol}_{day.isoformat()}", "category": "EARNINGS"}]


class MockHaltProvider(HaltProvider):
    """One LULD halt 10:00–10:05 ET."""
    def fetch(self, symbol, day):
        return [{"halt_start_ts": _et(day, 10, 0), "halt_end_ts": _et(day, 10, 5),
                 "halt_reason": "LULD_UP", "luld_band_pct": 10.0,
                 "resumption_ts": _et(day, 10, 5)}]


class MockDataQualityProvider(DataQualityProvider):
    def assess_as_of(self, symbol, as_of):
        return {"feed_outage_active": False, "missing_prints_in_lookback": 0,
                "stale_quote": False, "last_good_ts": as_of}
    def assess_session(self, symbol, day):
        return {"missing_bars_pct": 0.4, "n_bad_ticks": 2, "n_outlier_trades": 1,
                "halt_seconds": 300, "feed_outage_seconds": 0, "ca_anomaly_flag": False,
                "quality_score": 0.98}
