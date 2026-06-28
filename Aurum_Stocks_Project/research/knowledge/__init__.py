"""Research Event Knowledge Layer (REKL) — read-only, independent.

Builds a historical knowledge base over RERL Timelines WITHOUT any interpretation:
  archetypes  group similar timelines into research families (deterministic, structural)
  graph       Event Relationship Graph — factual temporal relations within a timeline
  query       Research Query Engine — search by filter conditions only (no ranking)
  stats       Statistical Explorer — descriptive statistics only (no performance/edge)
  viz         Visualization — timelines, event trees, relationship graphs, heatmaps

Forbidden by construction across this layer: features, scores, sentiment, bullish/bearish,
signals, predictions, ML, scanner logic, trading logic, and any change to the production system.
"""
from . import archetypes, graph, query, stats, viz  # noqa: F401
from .archetypes import archetype_key, group_by_archetype, family_sizes, ArchetypeIndex  # noqa: F401
from .graph import build_graph, EventRelationshipGraph  # noqa: F401
from .query import Query, select_timelines  # noqa: F401
