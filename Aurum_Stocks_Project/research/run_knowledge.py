#!/usr/bin/env python3
"""Research Event Knowledge Layer demo (read-only).
   python research/run_knowledge.py --demo
Builds timelines for a few symbols (synthetic bars), then shows families, an event tree,
a relationship graph, descriptive stats, and a heatmap. No scores/signals/predictions."""
import argparse, os, sys
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root); sys.path.insert(0, os.path.join(_root, "src"))
from research.reconstruction import ReconstructionEngine
from research.knowledge import archetypes as A, stats as S, viz as V

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    if not a.demo:
        sys.exit("This CLI currently supports --demo (synthetic).")
    from aurum_stocks.calibration.data_provider import SyntheticDataProvider
    eng = ReconstructionEngine(SyntheticDataProvider())
    anchor = "2025-03-03T15:00:00+00:00"
    tls = [eng.reconstruct(sym, anchor, pre_minutes=15, post_minutes=60)
           for sym in ("MGNI", "PLUG", "RIG")]

    print("# FAMILIES (archetype = kind_set)")
    for key, n in A.family_sizes(tls, "kind_set").items():
        print(f"  [{n}]  {key[:80]}")
    print("\n# EVENT TREE (first timeline)\n" + V.event_tree(tls[0]))
    print("\n# RELATIONSHIP GRAPH (first timeline, head)")
    print("\n".join(V.render_graph(tls[0]).splitlines()[:8]))
    print("\n# DESCRIPTIVE STATS")
    summ = S.summary(tls)
    print("  kinds:", dict(list(summ["kind_frequency"].items())[:6]))
    print("  phases:", summ["phase_distribution"])
    print("  events/timeline:", summ["events_per_timeline"])
    print("\n# HEATMAP (counts)\n" + "\n".join(V.render_heatmap(tls).splitlines()[:10]))

if __name__ == "__main__":
    main()
