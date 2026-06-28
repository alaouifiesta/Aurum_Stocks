"""research/knowledge/graph.py — Event Relationship Graph (factual relations only).

Links events WITHIN a single timeline by their FACTUAL temporal relationship — never by any
interpretation, causality, or prediction. Edge relations:
  * FOLLOWS      — B is the next event after A in time
  * SAME_MINUTE  — A and B share the same wall-clock minute
  * WITHIN_<W>M  — B occurs strictly after A and within W minutes

Edges carry only `delta_seconds` (a fact). There are no weights-as-scores, no causal labels,
no directionality-as-signal. Read-only.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field


def _parse(ts: str) -> dt.datetime:
    return dt.datetime.fromisoformat(ts)


@dataclass
class GraphNode:
    idx: int
    kind: str
    phase: str
    ts_utc: str


@dataclass
class GraphEdge:
    src: int
    dst: int
    relation: str
    delta_seconds: float


@dataclass
class EventRelationshipGraph:
    nodes: list = field(default_factory=list)
    edges: list = field(default_factory=list)

    def adjacency(self) -> dict:
        adj = {n.idx: [] for n in self.nodes}
        for e in self.edges:
            adj[e.src].append((e.dst, e.relation, e.delta_seconds))
        return adj

    def to_dot(self) -> str:
        L = ["digraph timeline {", '  rankdir=LR;']
        for n in self.nodes:
            L.append(f'  {n.idx} [label="{n.kind}\\n{n.phase} {n.ts_utc[11:19]}"];')
        for e in self.edges:
            L.append(f'  {e.src} -> {e.dst} [label="{e.relation} {int(e.delta_seconds)}s"];')
        L.append("}")
        return "\n".join(L)


def build_graph(tl, *, within_minutes: int = 5) -> EventRelationshipGraph:
    evs = list(tl.events)
    nodes = [GraphNode(i, e.kind, e.phase, e.ts_utc) for i, e in enumerate(evs)]
    times = [_parse(e.ts_utc) for e in evs]
    edges: list[GraphEdge] = []
    # FOLLOWS: consecutive in time
    for i in range(len(evs) - 1):
        edges.append(GraphEdge(i, i + 1, "FOLLOWS",
                               (times[i + 1] - times[i]).total_seconds()))
    # SAME_MINUTE + WITHIN_<W>
    win = dt.timedelta(minutes=within_minutes)
    for i in range(len(evs)):
        for j in range(i + 1, len(evs)):
            delta = (times[j] - times[i]).total_seconds()
            if times[i].replace(second=0, microsecond=0) == \
               times[j].replace(second=0, microsecond=0):
                edges.append(GraphEdge(i, j, "SAME_MINUTE", delta))
            elif dt.timedelta(0) < (times[j] - times[i]) <= win:
                edges.append(GraphEdge(i, j, f"WITHIN_{within_minutes}M", delta))
    return EventRelationshipGraph(nodes=nodes, edges=edges)
