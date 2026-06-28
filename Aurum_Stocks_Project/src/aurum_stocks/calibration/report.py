"""
calibration/report.py — renders the calibration result.

Presents label properties per (k,H) and flags which cells satisfy the
Calibration Protocol guards (balanced, resolvable, barrier clears the spread).
It deliberately does NOT pick a "winner" via any performance metric — the final
TB2/TB3/TB4 choice is a human decision made on REAL SIP data, among the
non-degenerate cells, on label-property grounds only.
"""
from __future__ import annotations

import json


def _grid_table(cells, k_grid, h_grid, value_fn, fmt="{:.0%}") -> str:
    lut = {(c.k, c.h_min): c for c in cells}
    header = "| k \\ H |" + "|".join(f" {h}m " for h in h_grid) + "|"
    sep = "|" + "---|" * (len(h_grid) + 1)
    rows = [header, sep]
    for k in k_grid:
        cellvals = []
        for h in h_grid:
            c = lut[(k, h)]
            v = fmt.format(value_fn(c))
            cellvals.append(f" {v}{'*' if c.degenerate else ''} ")
        rows.append(f"| {k} |" + "|".join(cellvals) + "|")
    return "\n".join(rows)


def render_markdown(result: dict, title="Calibration Report", note="") -> str:
    cells, k_grid, h_grid = result["cells"], result["k_grid"], result["h_grid"]
    s = result["stats"]
    out = [f"# {title}", ""]
    if note:
        out += [f"> {note}", ""]
    out += [
        f"**Entries evaluated:** {s['entries']:,}  ·  "
        f"**symbol-days:** {s['symbol_days']}  ·  "
        f"**empty days:** {s['empty_days']}  ·  "
        f"**skipped (insufficient ATR):** {s['skipped_atr']:,}",
        "",
        "`*` marks a degenerate cell (fails a Calibration Protocol guard: "
        "time%>70%, any class<10%, or barrier/spread<3×).",
        "",
        "## Profit %", _grid_table(cells, k_grid, h_grid, lambda c: c.profit_pct),
        "", "## Stop %", _grid_table(cells, k_grid, h_grid, lambda c: c.stop_pct),
        "", "## Time %", _grid_table(cells, k_grid, h_grid, lambda c: c.time_pct),
        "", "## Class Balance (normalized entropy, 1.0 = perfectly balanced)",
        _grid_table(cells, k_grid, h_grid, lambda c: c.class_entropy, fmt="{:.2f}"),
        "", "## Median Time To Resolution (minutes, resolved only)",
        _grid_table(cells, k_grid, h_grid, lambda c: c.median_ttr_min, fmt="{:.0f}"),
        "", "## Barrier Distance / Typical Spread (median)",
        _grid_table(cells, k_grid, h_grid, lambda c: c.barrier_spread_ratio, fmt="{:.1f}"),
        "",
    ]

    # Non-degenerate candidates, sorted by balance (a label property, not performance).
    ok = [c for c in cells if not c.degenerate]
    ok.sort(key=lambda c: c.class_entropy, reverse=True)
    out += ["## Non-degenerate candidate cells (by class balance)", ""]
    if not ok:
        out += ["_None passed all guards — widen/adjust the grid or inspect the data._", ""]
    else:
        out += ["| k | H | profit% | stop% | time% | balance | TTR | bar/spread | TIME +/-/0 |",
                "|---|---|---|---|---|---|---|---|---|"]
        for c in ok[:12]:
            out.append(
                f"| {c.k} | {c.h_min}m | {c.profit_pct:.0%} | {c.stop_pct:.0%} | "
                f"{c.time_pct:.0%} | {c.class_entropy:.2f} | {c.median_ttr_min:.0f}m | "
                f"{c.barrier_spread_ratio:.1f} | "
                f"{c.time_pos_pct:.0%}/{c.time_neg_pct:.0%}/{c.time_flat_pct:.0%} |"
            )
        out += ["",
                "**TB4 hint:** the `TIME +/-/0` column is the sign split of horizon-end "
                "returns for TIME outcomes. A roughly even split favours ternary "
                "(TIME=0); a strong skew suggests sign-of-return may carry information "
                "— decide on label-property grounds, never on feature predictiveness.",
                ""]
    return "\n".join(out)


def to_json(result: dict) -> str:
    return json.dumps(
        {"stats": result["stats"], "k_grid": result["k_grid"],
         "h_grid": result["h_grid"], "cells": [c.as_dict() for c in result["cells"]]},
        indent=2,
    )
