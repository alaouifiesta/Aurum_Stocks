"""
calibration/grid.py — orchestrates the (k,H) grid search.

For each symbol/day it samples candidate entries during RTH, builds one forward
excursion envelope per entry (up to max H), then resolves every (k,H) cell from
those envelopes. Aggregates label-property metrics per cell across the whole run.

No setup logic, no features, no performance metrics — this characterises the
label definition itself, feature-blind, exactly as the Calibration Protocol (§5)
requires.
"""
from __future__ import annotations

import datetime as dt
from collections import defaultdict

import pandas as pd

from . import config, barriers, metrics
from .data_provider import DataProvider


def _rth_entry_timestamps(index: pd.DatetimeIndex) -> list:
    open_t = dt.time(*map(int, config.RTH_OPEN.split(":")))
    close_t = dt.time(*map(int, config.RTH_CLOSE.split(":")))
    rth = index[(index.time >= open_t) & (index.time < close_t)]
    # Every Nth minute.
    return list(rth[:: config.ENTRY_SAMPLE_EVERY_MIN])


def run_grid(provider: DataProvider, symbols: list, dates: list,
             k_grid=None, h_grid=None, progress=False) -> dict:
    k_grid = k_grid or config.K_GRID
    h_grid = h_grid or config.H_GRID_MIN
    max_h = max(h_grid)

    # cell -> list[Outcome]
    cell_outcomes = defaultdict(list)
    stats = {"entries": 0, "skipped_atr": 0, "skipped_path": 0,
             "symbol_days": 0, "empty_days": 0}

    for symbol in symbols:
        for date in dates:
            bars = provider.get_minute_bars(symbol, date)
            stats["symbol_days"] += 1
            if bars.empty:
                stats["empty_days"] += 1
                continue
            session_close = pd.Timestamp(f"{date} {config.RTH_CLOSE}", tz=config.TZ)
            for entry_ts in _rth_entry_timestamps(bars.index):
                env = barriers.build_envelope(bars, entry_ts, session_close, max_h)
                if env is None:
                    stats["skipped_atr"] += 1
                    continue
                stats["entries"] += 1
                for k in k_grid:
                    for h in h_grid:
                        cell_outcomes[(k, h)].append(barriers.resolve(env, k, h))
            if progress:
                print(f"  {symbol} {date}: cumulative entries={stats['entries']}")

    cells = []
    for k in k_grid:
        for h in h_grid:
            cells.append(metrics.aggregate(k, h, cell_outcomes[(k, h)]))
    return {"cells": cells, "stats": stats, "k_grid": k_grid, "h_grid": h_grid}
