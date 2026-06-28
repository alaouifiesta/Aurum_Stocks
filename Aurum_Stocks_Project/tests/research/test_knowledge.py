"""Tests for the Research Event Knowledge Layer (read-only, descriptive)."""
import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _root)
sys.path.insert(0, os.path.join(_root, "src"))

from research.reconstruction import Timeline, TimelineEvent, PRE, AT, POST
from research.knowledge import (
    archetypes as A, graph as G, query as Q, stats as S, viz as V, ArchetypeIndex,
)


def _tl(symbol, anchor, events):
    tl = Timeline(symbol=symbol, anchor_ts_utc=anchor)
    for ts, kind, phase, detail in events:
        tl.add(TimelineEvent(ts, kind, phase, detail))
    return tl.sort()


def _sample():
    a = "2025-03-03T15:00:00+00:00"
    t1 = _tl("ABCD", a, [
        ("2025-03-03T14:55:00+00:00", "VOLUME_EXPANSION", PRE, {"ratio": 3.4}),
        ("2025-03-03T15:00:00+00:00", "NEWS", AT, {}),
        ("2025-03-03T15:02:00+00:00", "VWAP_CROSS_UP", POST, {"vwap": 10.0}),
        ("2025-03-03T15:03:00+00:00", "OR_BREAK_UP", POST, {"level": 10.5}),
    ])
    t2 = _tl("WXYZ", a, [
        ("2025-03-03T14:58:00+00:00", "VOLUME_EXPANSION", PRE, {"ratio": 5.0}),
        ("2025-03-03T15:00:00+00:00", "NEWS", AT, {}),
        ("2025-03-03T15:02:00+00:00", "VWAP_CROSS_UP", POST, {"vwap": 20.0}),
        ("2025-03-03T15:03:00+00:00", "OR_BREAK_UP", POST, {"level": 21.0}),
    ])  # same kind-set/seq as t1 -> same family
    t3 = _tl("QQQQ", a, [
        ("2025-03-03T15:00:00+00:00", "NEWS", AT, {}),
        ("2025-03-03T15:10:00+00:00", "SWEEP_OF_LOWS", POST, {"level": 5.0}),
    ])  # different family
    return [t1, t2, t3]


def test_archetypes_group_similar():
    tls = _sample()
    fam_set = A.group_by_archetype(tls, "kind_set")
    # t1 & t2 share a family; t3 is its own
    sizes = sorted(len(v) for v in fam_set.values())
    assert sizes == [1, 2]
    # finer scheme still groups t1,t2 (identical sequence)
    fam_seq = A.group_by_archetype(tls, "kind_seq")
    assert max(len(v) for v in fam_seq.values()) == 2
    # deterministic key
    assert A.archetype_key(tls[0], "kind_set") == A.archetype_key(tls[1], "kind_set")
    print("archetypes group similar OK")


def test_archetype_index_append_only():
    idx = ArchetypeIndex()
    for tl in _sample():
        idx.record(tl, "kind_set")
    assert idx.count() == 3
    key = A.archetype_key(_sample()[0], "kind_set")
    assert len(idx.members("kind_set", key)) == 2     # t1 + t2
    assert max(idx.family_sizes("kind_set").values()) == 2
    print("archetype index append-only OK")


def test_relationship_graph_factual():
    tl = _sample()[0]
    g = G.build_graph(tl, within_minutes=5)
    assert len(g.nodes) == 4
    rels = {e.relation for e in g.edges}
    assert "FOLLOWS" in rels                      # consecutive
    assert any(r.startswith("WITHIN_") for r in rels)
    # edges carry only factual delta_seconds (no weight/score attribute)
    for e in g.edges:
        assert hasattr(e, "delta_seconds") and not hasattr(e, "score")
    assert g.to_dot().startswith("digraph")
    print("relationship graph factual OK")


def test_query_engine_filters_only():
    tls = _sample()
    # by kind + phase
    res = Q.Query(kinds={"VWAP_CROSS_UP"}, phases={POST}).run(tls)
    assert len(res) == 2 and all(ev.kind == "VWAP_CROSS_UP" for _, ev in res)
    # detail predicate on a FACT (ratio >= 4) — filtering, not scoring
    res2 = Q.Query(kinds={"VOLUME_EXPANSION"}, detail=[("ratio", ">=", 4.0)]).run(tls)
    assert len(res2) == 1
    # timeline-level selection
    sel = Q.select_timelines(tls, contains_kind="SWEEP_OF_LOWS")
    assert len(sel) == 1 and sel[0].symbol == "QQQQ"
    # forbidden filter key rejected
    try:
        Q.Query(detail=[("score", ">=", 1)])
        assert False
    except ValueError:
        pass
    print("query engine filters-only OK")


def test_stats_descriptive_only():
    tls = _sample()
    kf = S.kind_frequency(tls)
    assert kf["NEWS"] == 3 and kf["VWAP_CROSS_UP"] == 2
    pd = S.phase_distribution(tls)
    assert pd[AT] == 3
    ept = S.events_per_timeline(tls)
    assert ept["count"] == 3 and ept["max"] == 4
    gap = S.inter_event_gap_seconds(tls)
    assert gap["count"] >= 1
    ttf = S.time_to_first_kind_minutes(tls, "VWAP_CROSS_UP")
    assert ttf["count"] == 2 and ttf["min"] == 2.0     # 15:02 - 15:00 = 2 min
    pairs = S.kind_pair_frequency(tls)
    assert "VWAP_CROSS_UP->OR_BREAK_UP" in pairs
    summ = S.summary(tls)
    forbidden = {"score", "win_rate", "return", "sharpe", "edge", "pnl", "prediction"}
    assert not (forbidden & set(summ))
    print("stats descriptive-only OK")


def test_viz_outputs():
    tls = _sample()
    tree = V.event_tree(tls[0])
    assert "EVENT TREE" in tree and "POST" in tree
    dot = V.graph_dot(tls[0])
    assert dot.startswith("digraph")
    rg = V.render_graph(tls[0])
    assert "RELATIONSHIP GRAPH" in rg
    hm = V.heatmap(tls, bucket_minutes=5)
    assert "NEWS" in hm["grid"] and all(isinstance(c, int)
                                        for row in hm["grid"].values() for c in row.values())
    txt = V.render_heatmap(tls, bucket_minutes=5)
    assert "HEATMAP" in txt
    print("viz outputs OK")


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("\nALL KNOWLEDGE LAYER TESTS PASSED")
