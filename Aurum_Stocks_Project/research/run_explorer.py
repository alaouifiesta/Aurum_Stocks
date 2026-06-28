#!/usr/bin/env python3
"""Dataset Explorer CLI (read-only, counts only). Demo: python research/run_explorer.py --demo"""
import argparse, os, sys
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root); sys.path.insert(0, os.path.join(_root, "src"))
from research.explore import dataset_explorer
from research.demo import make_demo_rows

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    if not a.demo:
        sys.exit("This CLI currently supports --demo only (no observation store exists yet).")
    print(dataset_explorer.render(make_demo_rows()))

if __name__ == "__main__":
    main()
