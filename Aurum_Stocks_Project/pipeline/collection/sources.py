"""pipeline/collection/sources.py — builder input ports for the Collection Layer.

Two concrete implementations of the FROZEN builder ports (defined in
foundation.observation_builder). Neither modifies the builder; they are the as-of inputs it
already expects.

  MdvplBarSource     implements BarSource: serves ONLY the MDVPL-validated bars at or before
                     signal_ts, and reports data_as_of_ts <= signal_ts (PIT). Read-only;
                     transforms nothing (bars are the verbatim pass-through MDVPL returned).

  NullFeatureComputer implements FeatureComputer: returns {} — the empty/identity port. The
                     Collection Layer generates NO features (Phase 2 hard constraint). The
                     builder requires a FeatureComputer; this is the no-op that satisfies the
                     contract without computing anything.
"""
from __future__ import annotations

import pandas as pd

from aurum_stocks.foundation.observation_builder import BarSource, FeatureComputer


def _bar_ts(bar: dict) -> pd.Timestamp:
    """Parse a validated bar's UTC ISO 'ts' into a tz-aware UTC Timestamp."""
    return pd.Timestamp(bar["ts"])


class MdvplBarSource(BarSource):
    """As-of bar source backed by MDVPL-validated bars.

    `validated_bars` maps symbol -> list[bar dict] (UTC ISO 'ts'), exactly as returned by
    MarketDataValidator (pass-through, unchanged). The collector constructs one of these per
    (symbol, day) batch from the validated batch data.
    """

    def __init__(self, validated_bars: dict[str, list[dict]]):
        # Defensive copy of the mapping only (bar dicts themselves are left untouched / verbatim).
        self._by_symbol = {s: list(rows) for s, rows in validated_bars.items()}

    def bars_as_of(self, symbol: str, signal_ts: pd.Timestamp):
        """Return (bars with ts <= signal_ts, data_as_of_ts<=signal_ts).

        data_as_of_ts is the newest bar timestamp at or before signal_ts. If no bar is at or
        before signal_ts, no input was used: data_as_of_ts == signal_ts (still <= signal_ts,
        PIT-safe) and an empty bar list is returned. Never reads beyond signal_ts.
        """
        cutoff = signal_ts.tz_convert("UTC")
        rows = [b for b in self._by_symbol.get(symbol, []) if _bar_ts(b) <= cutoff]
        if rows:
            data_as_of = max(_bar_ts(b) for b in rows)
        else:
            data_as_of = cutoff
        return rows, data_as_of


class NullFeatureComputer(FeatureComputer):
    """Computes NO features. Returns the empty dict for every observation (Phase 2 constraint)."""

    def compute(self, symbol: str, signal_ts, bars) -> dict:
        return {}
