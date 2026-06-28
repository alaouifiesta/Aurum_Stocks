#!/usr/bin/env python3
"""Event Reconstruction CLI (read-only). Demo:
   python research/run_reconstruct.py --demo
Builds a timeline around a synthetic news anchor using synthetic bars (self-test only)."""
import argparse, os, sys
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root); sys.path.insert(0, os.path.join(_root, "src"))
from research.reconstruction import ReconstructionEngine

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--symbol", default="MGNI")
    ap.add_argument("--anchor", default="2025-03-03T15:00:00+00:00",
                    help="anchor (news) timestamp, UTC ISO")
    ap.add_argument("--pre", type=int, default=30)
    ap.add_argument("--post", type=int, default=120)
    a = ap.parse_args()
    if not a.demo:
        sys.exit("This CLI currently supports --demo (synthetic bars). Wire a real "
                 "PIT bar source to reconstruct real timelines.")
    from aurum_stocks.calibration.data_provider import SyntheticDataProvider
    tl = ReconstructionEngine(SyntheticDataProvider()).reconstruct(
        a.symbol, a.anchor, anchor_ref={"note": "synthetic demo anchor"},
        pre_minutes=a.pre, post_minutes=a.post)
    print(tl.render())

if __name__ == "__main__":
    main()
