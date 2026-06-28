#!/usr/bin/env python3
"""
run_calibration.py — entrypoint for the Triple-Barrier label calibration.

Demo (synthetic data, no network needed):
    python run_calibration.py --demo --days 10 --out ./calibration_out

Real run (your environment, your key — make the actual TB2/TB3/TB4 decision):
    # provide a PolygonDataProvider wired with a requests.Session + api key,
    # then call run_grid over config.SYMBOLS and your chosen trading dates.

The framework computes ONLY label-property metrics. It does not pick a winner;
you choose among non-degenerate cells on label-property grounds, on REAL data.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os

import pandas as pd

from aurum_stocks.calibration import config, grid, report
from aurum_stocks.calibration.data_provider import SyntheticDataProvider


def recent_weekdays(n: int, end: dt.date | None = None) -> list:
    end = end or dt.date.today()
    days, d = [], end
    while len(days) < n:
        if d.weekday() < 5:
            days.append(d)
        d -= dt.timedelta(days=1)
    return sorted(days)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true", help="use synthetic data")
    ap.add_argument("--days", type=int, default=10)
    ap.add_argument("--symbols", nargs="*", default=None,
                    help="default: full universe from config")
    ap.add_argument("--out", default="./calibration_out")
    args = ap.parse_args()

    symbols = args.symbols or config.SYMBOLS
    dates = recent_weekdays(args.days)

    if args.demo:
        provider = SyntheticDataProvider(base_seed=7)
        note = ("SYNTHETIC data — self-test only. Do NOT use these numbers to freeze "
                "TB2/TB3/TB4. Re-run with a PolygonDataProvider on real SIP data.")
    else:
        raise SystemExit(
            "Real run: construct a PolygonDataProvider(api_key, session=...) and call "
            "grid.run_grid(provider, config.SYMBOLS, dates). Not available in --demo-less "
            "mode here because no data vendor is reachable from this environment."
        )

    print(f"Running grid: {len(symbols)} symbols x {len(dates)} days "
          f"x {len(config.K_GRID)}k x {len(config.H_GRID_MIN)}H ...")
    result = grid.run_grid(provider, symbols, dates)

    os.makedirs(args.out, exist_ok=True)
    md = report.render_markdown(result, title="Aurum Stocks — TB Calibration (DEMO)", note=note)
    with open(os.path.join(args.out, "calibration_report.md"), "w") as f:
        f.write(md)
    with open(os.path.join(args.out, "calibration_result.json"), "w") as f:
        f.write(report.to_json(result))
    print(md)
    print(f"\nWrote report to {args.out}/")


if __name__ == "__main__":
    main()
