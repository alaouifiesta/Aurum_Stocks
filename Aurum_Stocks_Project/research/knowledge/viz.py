"""research/knowledge/viz.py — visualization (text/markup, dependency-free).

Renders Timelines, Event Trees, Relationship Graphs (Graphviz DOT), and Heatmaps. Every cell
is a COUNT or a FACT — there are no scores, no colours-by-edge, no performance shading. Output
is read-only strings/structures the operator can view or export.
"""
from __future__ import annotations

import datetime as dt
from collections import Counter, defaultdict

from .graph import build_graph


def _parse(ts: str) -> dt.datetime:
    return dt.datetime.fromisoformat(ts)


def render_timeline(tl) -> str:
    """Delegate to the RERL Timeline renderer (chronological factual listing)."""
    return tl.render()


def event_tree(tl) -> str:
    """ASCII tree: phase -> kind -> [timestamps]."""
    by_phase = defaultdict(lambda: defaultdict(list))
    for e in tl.events:
        by_phase[e.phase][e.kind].append(e.ts_utc[11:19])
    L = [f"EVENT TREE  ·  {tl.symbol}  (anchor {tl.anchor_ts_utc})"]
    for phase in ("PRE", "AT", "POST"):
        if phase not in by_phase:
            continue
        L.append(f"├─ {phase}")
        kinds = by_phase[phase]
        for ki, (kind, times) in enumerate(sorted(kinds.items())):
            branch = "└─" if ki == len(kinds) - 1 else "├─"
            L.append(f"│   {branch} {kind}  ({len(times)})  {', '.join(times)}")
    return "\n".join(L)


def graph_dot(tl, *, within_minutes: int = 5) -> str:
    return build_graph(tl, within_minutes=within_minutes).to_dot()


def render_graph(tl, *, within_minutes: int = 5) -> str:
    """Text adjacency of the relationship graph (factual relations + delta seconds)."""
    g = build_graph(tl, within_minutes=within_minutes)
    name = {n.idx: f"{n.kind}@{n.ts_utc[11:19]}" for n in g.nodes}
    L = [f"RELATIONSHIP GRAPH  ·  {tl.symbol}  ({len(g.nodes)} nodes, {len(g.edges)} edges)"]
    adj = g.adjacency()
    for idx in sorted(adj):
        for dst, rel, delta in adj[idx]:
            L.append(f"  {name[idx]:<28} --{rel}({int(delta)}s)--> {name[dst]}")
    return "\n".join(L)


def heatmap(timelines, *, bucket_minutes: int = 5) -> dict:
    """Counts of each kind per relative-minute bucket (bucket = minutes from anchor).
    Returns {kinds, buckets, grid} — grid[kind][bucket] = COUNT. No scores."""
    cells = defaultdict(Counter)
    buckets = set()
    for tl in timelines:
        anchor = _parse(tl.anchor_ts_utc)
        for e in tl.events:
            rel = (_parse(e.ts_utc) - anchor).total_seconds() / 60.0
            b = int(rel // bucket_minutes) * bucket_minutes
            cells[e.kind][b] += 1
            buckets.add(b)
    kinds = sorted(cells)
    buckets = sorted(buckets)
    grid = {k: {b: cells[k].get(b, 0) for b in buckets} for k in kinds}
    return {"kinds": kinds, "buckets": buckets, "grid": grid,
            "bucket_minutes": bucket_minutes}


def render_heatmap(timelines, *, bucket_minutes: int = 5) -> str:
    hm = heatmap(timelines, bucket_minutes=bucket_minutes)
    if not hm["kinds"]:
        return "(no events)"
    header = "kind \\ +min".ljust(24) + "".join(f"{b:>5}" for b in hm["buckets"])
    L = [f"HEATMAP (counts, {bucket_minutes}-min buckets, minutes from anchor)", header]
    for k in hm["kinds"]:
        row = "".join(f"{hm['grid'][k][b]:>5}" for b in hm["buckets"])
        L.append(k.ljust(24) + row)
    return "\n".join(L)
