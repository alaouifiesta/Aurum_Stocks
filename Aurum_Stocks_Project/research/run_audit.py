#!/usr/bin/env python3
"""Data Coverage Audit CLI (read-only reporting). Demo: python research/run_audit.py --demo"""
import argparse, os, sys
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root); sys.path.insert(0, os.path.join(_root, "src"))
from research.audit import coverage_audit
from research.demo import make_demo_rows, make_demo_archive

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    if not a.demo:
        sys.exit("This CLI currently supports --demo only (no observation store exists yet).")
    rows = make_demo_rows()
    known = {"symbol": {"SYM-1"}, "regime": {"REG-1", "REG-2"}, "setup": {"SET-1"},
             "label": {"LBL_V1"}, "universe": {"UNI-1"}, "scanner": {"SCN-1"}}
    print(coverage_audit.render_report(rows, known=known, archive=make_demo_archive()))

if __name__ == "__main__":
    main()
