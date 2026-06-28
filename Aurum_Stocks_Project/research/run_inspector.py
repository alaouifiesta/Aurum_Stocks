#!/usr/bin/env python3
"""Observation Inspector CLI (read-only). Demo: python research/run_inspector.py --demo"""
import argparse, os, sys
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root); sys.path.insert(0, os.path.join(_root, "src"))
from research.inspector import inspect_row
from research.demo import make_demo_rows

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--index", type=int, default=0)
    a = ap.parse_args()
    if not a.demo:
        sys.exit("This CLI currently supports --demo only (no observation store exists yet).")
    rows = make_demo_rows()
    print(inspect_row(rows[a.index]))

if __name__ == "__main__":
    main()
