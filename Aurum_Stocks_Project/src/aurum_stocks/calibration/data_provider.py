"""
calibration/data_provider.py — point-in-time 1-minute bar sources.

The calibration engine is data-source-agnostic. It depends only on the
`DataProvider` interface, which returns a tz-aware (America/New_York) DataFrame
of 1-minute bars for one symbol/day with columns:
    open, high, low, close, volume, bid, ask

Two implementations ship here:
  * SyntheticDataProvider  — generates plausible small-cap intraday paths so the
    framework can be run and validated end-to-end WITHOUT real data. For
    self-test / demo ONLY. Never use it to make the real TB2/TB3/TB4 decision.
  * PolygonDataProvider    — adapter for real SIP 1-minute aggregates + quotes.
    Requires your API key and network access; UNTESTED in this sandbox. Verify
    against current Polygon docs before relying on it.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
import datetime as dt

import numpy as np
import pandas as pd

from . import config


class DataProvider(ABC):
    """Returns 1-minute bars for one symbol on one calendar date (ET)."""

    @abstractmethod
    def get_minute_bars(self, symbol: str, date: dt.date) -> pd.DataFrame:
        """Index: tz-aware ET timestamps. Columns: open,high,low,close,volume,bid,ask.
        Must include the premarket warm-up window so ATR is warm by the open.
        Returns an empty frame if the symbol did not trade that day."""
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Synthetic provider (self-test only)
# ---------------------------------------------------------------------------
class SyntheticDataProvider(DataProvider):
    """Generates a 1-minute small-cap-like session: gappy open, intraday vol smile,
    occasional jumps, spread that widens at low price / high vol. Seeded per
    (symbol, date) for reproducibility. NOT real data."""

    def __init__(self, base_seed: int = 7):
        self.base_seed = base_seed

    def _seed(self, symbol: str, date: dt.date) -> int:
        return (self.base_seed * 1_000_003 + hash((symbol, date.toordinal()))) % (2**31)

    def get_minute_bars(self, symbol: str, date: dt.date) -> pd.DataFrame:
        rng = np.random.default_rng(self._seed(symbol, date))

        start = pd.Timestamp(f"{date} {config.PREMARKET_START}", tz=config.TZ)
        end = pd.Timestamp(f"{date} {config.RTH_CLOSE}", tz=config.TZ)
        idx = pd.date_range(start, end, freq="1min", inclusive="left")
        n = len(idx)

        # Base price per symbol (small caps span ~$1.5 .. ~$60).
        base_price = float(np.interp(abs(hash(symbol)) % 1000 / 1000.0, [0, 1], [1.5, 60.0]))

        # Per-minute volatility with a smile: higher near open & close.
        minutes_from_open = (idx - pd.Timestamp(f"{date} {config.RTH_OPEN}", tz=config.TZ))
        m = minutes_from_open.total_seconds().values / 60.0
        smile = 1.0 + 0.9 * np.exp(-((m - 0) ** 2) / (2 * 25 ** 2)) \
                    + 0.5 * np.exp(-((m - 390) ** 2) / (2 * 30 ** 2))
        per_min_vol = 0.0016 * smile  # ~0.16% baseline per-minute std, scaled by smile

        # Daily drift: small caps have fat-tailed daily moves.
        daily_drift = rng.standard_t(df=3) * 0.0008

        # Occasional intraday jumps (news spikes).
        jumps = np.zeros(n)
        n_jumps = rng.poisson(0.8)
        for _ in range(n_jumps):
            j = rng.integers(0, n)
            jumps[j] = rng.standard_normal() * 0.02

        shocks = rng.standard_normal(n) * per_min_vol + daily_drift / max(n, 1) + jumps
        # Mild mean reversion so paths aren't pure random walk.
        log_price = np.empty(n)
        lp = np.log(base_price)
        anchor = lp
        for i in range(n):
            lp += shocks[i] - 0.02 * (lp - anchor)
            log_price[i] = lp
        close = np.exp(log_price)

        # Build OHLC around the close path.
        intrabar = per_min_vol * close
        high = close + np.abs(rng.standard_normal(n)) * intrabar
        low = close - np.abs(rng.standard_normal(n)) * intrabar
        open_ = np.empty(n)
        open_[0] = close[0]
        open_[1:] = close[:-1]
        high = np.maximum.reduce([high, open_, close])
        low = np.minimum.reduce([low, open_, close])

        # Volume: U-shaped intraday, thin in premarket.
        is_rth = (idx.time >= dt.time(9, 30)) & (idx.time < dt.time(16, 0))
        vol_shape = (1.5 + np.exp(-((m) ** 2) / (2 * 40 ** 2)) + np.exp(-((m - 390) ** 2) / (2 * 40 ** 2)))
        volume = (rng.gamma(2.0, 1.0, n) * 5000 * vol_shape * np.where(is_rth, 1.0, 0.15)).astype(np.int64)

        # Spread: wider at low price and high vol (cents-based, small-cap realistic).
        spread = np.maximum(0.01, (0.0008 * close + 0.5 * intrabar))
        bid = close - spread / 2.0
        ask = close + spread / 2.0

        df = pd.DataFrame(
            {"open": open_, "high": high, "low": low, "close": close,
             "volume": volume, "bid": bid, "ask": ask},
            index=idx,
        )
        df.index.name = "ts"
        return df


# ---------------------------------------------------------------------------
# Polygon adapter (real SIP data) — stub, wire up locally.
# ---------------------------------------------------------------------------
class PolygonDataProvider(DataProvider):
    """Real SIP 1-minute aggregates + NBBO quotes via Polygon.

    NOT exercised in the build sandbox (no key / no network). Endpoints follow
    Polygon's documented shapes as of writing; confirm against current docs:
      * Aggregates: GET /v2/aggs/ticker/{symbol}/range/1/minute/{from}/{to}
      * Quotes:     GET /v3/quotes/{symbol}  (for per-minute spread; optional)
    If you only have aggregates (no quotes), pass a spread model instead of NBBO.
    """

    BASE = "https://api.polygon.io"

    def __init__(self, api_key: str, session=None, spread_model=None):
        self.api_key = api_key
        self._session = session  # inject a requests.Session locally
        self.spread_model = spread_model  # callable(close)->spread if no quotes

    def get_minute_bars(self, symbol: str, date: dt.date) -> pd.DataFrame:
        if self._session is None:
            raise RuntimeError(
                "PolygonDataProvider needs a requests.Session and network access. "
                "Wire it up in your local environment; it is intentionally not run "
                "inside the build sandbox."
            )
        day = date.isoformat()
        url = f"{self.BASE}/v2/aggs/ticker/{symbol}/range/1/minute/{day}/{day}"
        params = {"adjusted": "true", "sort": "asc", "limit": 50000, "apiKey": self.api_key}
        r = self._session.get(url, params=params, timeout=30)
        r.raise_for_status()
        results = r.json().get("results", [])
        if not results:
            return pd.DataFrame(
                columns=["open", "high", "low", "close", "volume", "bid", "ask"]
            )
        df = pd.DataFrame(results).rename(
            columns={"o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"}
        )
        df["ts"] = pd.to_datetime(df["t"], unit="ms", utc=True).dt.tz_convert(config.TZ)
        df = df.set_index("ts")[["open", "high", "low", "close", "volume"]]
        # Spread: from a model if quotes are unavailable. Replace with real NBBO
        # if you have the quotes feed (recommended for the spread-ratio metric).
        model = self.spread_model or (lambda c: 0.0008 * c + 0.01)
        spread = df["close"].map(model).clip(lower=0.01)
        df["bid"] = df["close"] - spread / 2.0
        df["ask"] = df["close"] + spread / 2.0
        return df
