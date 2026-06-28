#!/usr/bin/env python3
"""
ops/run_lbl_calibration.py — operator runbook entry point (run later, with real SIP).

This is ORCHESTRATION over existing modules. It does NOT define new architecture, change
registries/gate/label logic, or invent selection rules. It:
  1. validates env + refuses non-SIP feeds,
  2. registers the burn window,
  3. runs the existing calibration grid (label-property metrics only),
  4. writes the report + computes calibration_report_hash,
  5. presents non-degenerate candidate cells,
  6. freezes LBL_V1 ONLY when the operator passes an explicit --select + --confirm-freeze.

It is intentionally NOT executed during the build (no data vendor is reachable, and the
final (k,H,TIME) choice is the operator's). Synthetic data must never freeze the label.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import sys

# src layout: make aurum_stocks importable when run from the repo root
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

FROZEN_RUBRIC_HASH = "11cf5f1c64319a790e172e104df4878f8c6eecaa50503588b6e89962ed01628c"


def _require_sip_env() -> str:
    provider = os.environ.get("DATA_PROVIDER", "").lower()
    feed = os.environ.get("DATA_FEED", "").lower()
    key = os.environ.get("POLYGON_API_KEY", "")
    if provider != "polygon":
        sys.exit("ABORT: DATA_PROVIDER must be 'polygon' (see .env.example)")
    if feed != "sip":
        sys.exit("ABORT: DATA_FEED must be 'sip' — IEX distorts RVOL/spread/volume "
                 "and the barrier/spread guard depends on a true consolidated spread")
    if not key:
        sys.exit("ABORT: POLYGON_API_KEY is empty (set it in your .env)")
    return key


def _parse_args():
    p = argparse.ArgumentParser(description="Run LBL_V1 calibration on real SIP data.")
    p.add_argument("--start", required=True, help="pilot window start (YYYY-MM-DD)")
    p.add_argument("--end", required=True, help="pilot window end (YYYY-MM-DD)")
    p.add_argument("--symbols-file", required=True, help="newline-separated symbol list")
    p.add_argument("--db", required=True, help="SQLite registry DB path")
    p.add_argument("--out", default="calibration_report.md", help="report output path")
    p.add_argument("--select", default="", help='freeze choice, e.g. "k=1.25,H=30,time=TERNARY"')
    p.add_argument("--confirm-freeze", action="store_true",
                   help="freeze LBL_V1 with --select (requires explicit operator confirmation)")
    return p.parse_args()


def main():
    args = _parse_args()
    key = _require_sip_env()

    import requests  # noqa: F401  (operator installs; used by PolygonDataProvider)
    from aurum_stocks.calibration import grid, report
    from aurum_stocks.calibration.data_provider import PolygonDataProvider
    from aurum_stocks.foundation import dataset_roles as dr
    from aurum_stocks.registries import db
    from aurum_stocks.registries.label_registry import LabelRegistry

    symbols = [s.strip() for s in open(args.symbols_file) if s.strip()]
    start = dt.date.fromisoformat(args.start)
    end = dt.date.fromisoformat(args.end)
    dates = [start + dt.timedelta(d) for d in range((end - start).days + 1)]

    print(f"[1/6] SIP env OK · provider=polygon feed=sip · {len(symbols)} symbols · "
          f"{start}..{end}")
    print(f"[2/6] frozen rubric_hash = {FROZEN_RUBRIC_HASH}")

    # burn the pilot slice (excluded from collection forever)
    ledger = dr.CalibrationBurnLedger()
    ledger.burn(dr.BurnedSlice(start, end, symbols=frozenset(symbols)))
    print(f"[3/6] burn window registered: {start}..{end} ({len(symbols)} symbols)")

    import requests as _rq
    provider = PolygonDataProvider(api_key=key, session=_rq.Session())
    print("[4/6] running calibration grid (label-property metrics only)...")
    result = grid.run_grid(provider, symbols, dates)

    md = report.render_markdown(result)
    open(args.out, "w").write(md)
    report_hash = hashlib.sha256(md.encode("utf-8")).hexdigest()
    print(f"[5/6] report written: {args.out}")
    print(f"      calibration_report_hash = {report_hash}")

    print("[6/6] Review the non-degenerate candidate cells in the report against the FROZEN "
          "rubric (docs/CALIBRATION_RUNBOOK.md / docs/design/...FREEZE_PACKAGE.md).")
    if not (args.confirm_freeze and args.select):
        print("\nNo freeze performed. To freeze, re-run with e.g.:")
        print('  --select "k=1.25,H=30,time=TERNARY" --confirm-freeze')
        return

    # operator-confirmed freeze
    sel = dict(kv.split("=") for kv in args.select.split(","))
    content = {
        "label_spec_id": "LBL_V1", "spec_version": "1",
        "k": float(sel["k"]), "H_minutes": int(sel["H"]),
        "time_encoding": sel["time"].upper(),
        "atr_spec": "ATR(14)@5min,PIT", "path_eval": "1-min",
        "tie_break": "STOP_FIRST", "time_cap": "RTH_CLOSE", "embargo": "H+1bar",
    }
    conn = db.connect(args.db); db.init_schema(conn)
    out = LabelRegistry(conn).freeze(
        label_spec_id="LBL_V1", spec_version="1", content=content,
        calibration_report_hash=report_hash, rubric_hash=FROZEN_RUBRIC_HASH,
        burn_ledger_ref=f"{start}..{end}", author="operator")
    LabelRegistry(conn).seal("LBL_V1")
    print("\nLBL_V1 FROZEN (write-once):")
    print(json.dumps(out, indent=2))
    print("\nNext: python ops/verify_lbl_freeze.py --db", args.db)


if __name__ == "__main__":
    main()
