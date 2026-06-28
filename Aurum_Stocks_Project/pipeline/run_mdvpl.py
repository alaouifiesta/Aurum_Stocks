#!/usr/bin/env python3
"""MDVPL demo (read-only, mock provider — no real API).
   python pipeline/run_mdvpl.py --demo
   python pipeline/run_mdvpl.py --demo --fault crossed_spread"""
import argparse, datetime as dt, os, sys
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root); sys.path.insert(0, os.path.join(_root, "src"))
from pipeline.mdvpl import MockMarketDataSource, MarketDataValidator, ProvenanceLog

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--symbol", default="ABCD")
    ap.add_argument("--fault", default="", help="inject a fault (e.g. gap, crossed_spread)")
    ap.add_argument("--single-venue", action="store_true")
    a = ap.parse_args()
    if not a.demo:
        sys.exit("This CLI supports --demo only (mock provider; no real API).")
    src = MockMarketDataSource(consolidated=not a.single_venue,
                               faults=frozenset({a.fault} if a.fault else set()))
    log = ProvenanceLog()
    res = MarketDataValidator(log).validate(src, a.symbol, dt.date(2025, 3, 3),
                                            streams=("bars", "quotes", "news"))
    print(res.report.render())
    print(f"\nprovenance rows: {log.count()}  feed_type={res.provenance.feed_type}")

if __name__ == "__main__":
    main()
