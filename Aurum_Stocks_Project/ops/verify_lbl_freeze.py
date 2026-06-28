#!/usr/bin/env python3
"""
ops/verify_lbl_freeze.py — verify the LBL_V1 freeze and recompute the gate.

Read-only checks. Safe to run anytime:
  * with --db pointing at a registry DB where LBL_V1 was frozen → full verification,
  * with no --db (dry mode) → runs the integrity suite and shows the gate is FALSE
    (because LBL_V1 is absent), demonstrating the tool without creating anything.

Changes nothing. No calibration, no label creation.
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

FROZEN_RUBRIC_HASH = "11cf5f1c64319a790e172e104df4878f8c6eecaa50503588b6e89962ed01628c"


def main():
    ap = argparse.ArgumentParser(description="Verify LBL_V1 freeze + recompute the gate.")
    ap.add_argument("--db", default="", help="registry DB path (omit for dry mode)")
    args = ap.parse_args()

    from aurum_stocks.integrity import integrity_suite as I
    from aurum_stocks.registries import db
    from aurum_stocks.registries.label_registry import LabelRegistry, canonical_label_hash

    print("=== Integrity Suite ===")
    checks = I.run_suite()
    print(I.render(checks))
    integrity_green = all(c.passed for c in checks)

    lbl_frozen = False
    if args.db and os.path.exists(args.db):
        conn = db.connect(args.db)
        lr = LabelRegistry(conn)
        rec = lr.get("LBL_V1")
        print("\n=== LBL_V1 freeze checks ===")
        if rec is None:
            print("[RED ] LBL_V1 not found in label_registry")
        else:
            import json
            content = json.loads(rec["content_json"])
            recomputed = canonical_label_hash(content)
            ok_hash = recomputed == rec["label_spec_hash"]
            ok_rubric = rec["rubric_hash"] == FROZEN_RUBRIC_HASH
            ok_sealed = bool(rec["sealed"])
            print(f"[{'GREEN' if ok_hash else 'RED  '}] label_spec_hash recomputes")
            print(f"[{'GREEN' if ok_rubric else 'RED  '}] rubric_hash matches frozen value")
            print(f"[{'GREEN' if rec['calibration_report_hash'] else 'RED  '}] calibration_report_hash present")
            print(f"[{'GREEN' if ok_sealed else 'RED  '}] burn sealed")
            lbl_frozen = ok_hash and ok_rubric and ok_sealed and bool(rec["calibration_report_hash"])
    else:
        print("\n(dry mode: no --db given or path missing → LBL_V1 treated as absent)")

    s = I.ready_for_collection(
        lbl_v1_frozen=lbl_frozen, registries_built=True,
        pit_gate_operational=True, universe_ready=True, scanner_ready=True, checks=checks)
    print("\n=== Gate ===")
    print(f"integrity: {s['integrity']}")
    for k, v in s["conditions"].items():
        print(f"   {'OK ' if v else 'XX '} {k} = {v}")
    print(f"\nREADY_FOR_COLLECTION = {s['ready']}")
    sys.exit(0 if s["ready"] else 1)


if __name__ == "__main__":
    main()
