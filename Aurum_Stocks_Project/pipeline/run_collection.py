"""pipeline/run_collection.py — Collection Layer demo (MOCK ONLY; no real API, no SIP).

Runs the Collection Engine over a few mock (symbol, day) batches and prints a summary. This is
a demonstration entry point; it stores nothing durably and decides nothing. Mirrors
pipeline/run_mdvpl.py.

    python pipeline/run_collection.py
"""
from __future__ import annotations

import datetime as dt

from pipeline.collection.wiring import build_mock_collection_engine


def main() -> None:
    engine = build_mock_collection_engine()
    days = [dt.date(2024, 3, 1), dt.date(2024, 3, 4)]
    specs = [(s, d) for s in ("KTOS", "PTON", "NVAX") for d in days]

    results = engine.collect(specs)

    print("=== Aurum Stocks — Collection Layer (mock) ===")
    for r in results:
        print(f"  {r.symbol:6} {r.trade_date}  {r.status:10} "
              f"verdict={r.verdict or '-':4} candidates={r.candidate_count} "
              f"stored={r.stored_count} dup={r.duplicate_count} "
              f"rejected={r.rejected_count} burned={r.burned_count}")
    print(f"  observations in sink: {len(engine.sink)}")
    print(f"  rejections recorded:  {engine.rejections.count()}")
    print(f"  manifest events:      {engine.manifest.count()}")

    # Re-run identical specs: idempotent — committed batches are skipped, nothing new stored.
    before = len(engine.sink)
    again = engine.collect(specs)
    assert all(r.status == "SKIPPED" for r in again)
    assert len(engine.sink) == before
    print("  re-run: all batches SKIPPED (idempotent), sink unchanged ✔")


if __name__ == "__main__":
    main()
