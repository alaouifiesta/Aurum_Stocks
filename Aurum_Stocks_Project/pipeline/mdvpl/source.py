"""pipeline/mdvpl/source.py — provider-agnostic market-data source interface (read-only).

Every vendor looks identical to the rest of the system through this one port, so changing the
data provider later is just swapping an adapter — no change anywhere else. NO real API is used:
only the abstract interface and a deterministic Mock adapter live here. Sources are read-only and
make no decisions; they return raw rows and declare their capabilities.

Row shapes (timestamps are UTC ISO-8601 strings):
  bar   = {ts, open, high, low, close, volume}
  quote = {ts, bid, ask}
  trade = {ts, price, size}
  news  = {article_id, news_available_ts, publish_ts, vendor, source}
"""
from __future__ import annotations

import datetime as dt
from abc import ABC, abstractmethod
from dataclasses import dataclass
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
UTC = dt.timezone.utc


@dataclass(frozen=True)
class Capabilities:
    vendor: str
    streams: tuple              # subset of ("bars","quotes","trades","news")
    consolidated: bool          # True = SIP/consolidated tape; False = single-venue (rejected)
    history_days: int


class MarketDataSource(ABC):
    """Read-only, as-of market-data source. Adapters implement this and nothing else."""
    vendor: str = "abstract"
    adapter_version: str = "0"

    @abstractmethod
    def capabilities(self) -> Capabilities: ...

    @abstractmethod
    def minute_bars(self, symbol: str, date: dt.date) -> list[dict]: ...

    def quotes(self, symbol: str, date: dt.date) -> list[dict]:
        return []

    def trades(self, symbol: str, date: dt.date) -> list[dict]:
        return []

    def news(self, symbol: str, start_utc: str, end_utc: str) -> list[dict]:
        return []


def _rth_minutes(date: dt.date):
    cur = dt.datetime.combine(date, dt.time(9, 30), ET)
    stop = dt.datetime.combine(date, dt.time(16, 0), ET)
    while cur < stop:
        yield cur
        cur += dt.timedelta(minutes=1)


def _iso(d: dt.datetime) -> str:
    return d.astimezone(UTC).isoformat()


class MockMarketDataSource(MarketDataSource):
    """Deterministic synthetic source for tests/demos. NOT real data.

    `faults` injects specific data-quality problems so the validator's checks can be exercised:
      gap · out_of_order · duplicate · bad_ohlc · negative_price · crossed_spread ·
      missing_news_available
    `consolidated=False` simulates a single-venue (non-SIP) feed.
    """
    vendor = "MOCK"
    adapter_version = "mock-1"

    def __init__(self, *, consolidated: bool = True, faults: frozenset = frozenset()):
        self.consolidated = consolidated
        self.faults = frozenset(faults)

    def capabilities(self) -> Capabilities:
        return Capabilities(self.vendor, ("bars", "quotes", "trades", "news"),
                            self.consolidated, 3650)

    def _base_price(self, symbol: str) -> float:
        return 5.0 + (sum(ord(c) for c in symbol) % 1000) / 100.0

    def minute_bars(self, symbol: str, date: dt.date) -> list[dict]:
        rows = []
        price = self._base_price(symbol)
        for i, ts in enumerate(_rth_minutes(date)):
            openp = round(price, 4)
            price = round(price + (0.01 if i % 2 == 0 else -0.005), 4)
            closep = round(price, 4)
            hi = round(max(openp, closep) + 0.03, 4)
            lo = round(min(openp, closep) - 0.03, 4)
            vol = 1000 + (i % 7) * 50
            rows.append({"ts": _iso(ts), "open": openp, "high": hi, "low": lo,
                         "close": closep, "volume": vol})
        if "gap" in self.faults and len(rows) > 30:
            del rows[20:25]                                  # 5-minute hole
        if "out_of_order" in self.faults and len(rows) > 3:
            rows[1], rows[2] = rows[2], rows[1]
        if "duplicate" in self.faults and len(rows) > 5:
            rows.insert(5, dict(rows[5]))
        if "bad_ohlc" in self.faults and rows:
            rows[10]["low"] = rows[10]["high"] + 1.0         # low > high
        if "negative_price" in self.faults and rows:
            rows[12]["close"] = -1.0
        return rows

    def quotes(self, symbol: str, date: dt.date) -> list[dict]:
        rows = []
        for i, ts in enumerate(_rth_minutes(date)):
            mid = self._base_price(symbol) + (i % 10) * 0.001
            rows.append({"ts": _iso(ts), "bid": round(mid - 0.01, 4),
                         "ask": round(mid + 0.01, 4)})
        if "crossed_spread" in self.faults and len(rows) > 8:
            rows[8]["bid"], rows[8]["ask"] = rows[8]["ask"], rows[8]["bid"]  # bid > ask
        return rows

    def trades(self, symbol: str, date: dt.date) -> list[dict]:
        out = []
        for i, ts in enumerate(_rth_minutes(date)):
            if i % 30 == 0:
                out.append({"ts": _iso(ts), "price": round(self._base_price(symbol), 4),
                            "size": 100 + i})
        return out

    def news(self, symbol: str, start_utc: str, end_utc: str) -> list[dict]:
        avail = {"news_available_ts": start_utc}
        if "missing_news_available" in self.faults:
            avail = {}
        return [{"article_id": f"{symbol}-n1", "publish_ts": start_utc,
                 "vendor": self.vendor, "source": "mock-wire", **avail}]
