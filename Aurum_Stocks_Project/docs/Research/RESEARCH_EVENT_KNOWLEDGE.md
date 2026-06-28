# Research Event Knowledge Layer (REKL)

Read-only, independent research layer (`research/knowledge/`) that turns RERL **Timelines** into a
browsable **historical knowledge base** — without any interpretation. It builds **on top of** the
Event Reconstruction Layer and changes nothing in the production system.

> **Forbidden by construction across this whole layer:** features · scores · sentiment ·
> bullish/bearish · signals · predictions · ML · scanner logic · trading logic · and any change to
> Gate / Registry / Label / Observation Builder / Integrity / Calibration. Outputs are read-only;
> the optional archetype index is append-only.

## Components

### 1. Event Archetypes (`archetypes.py`)
Groups **similar timelines into research families** by a deterministic, **structural** key — no
ML, no clustering, no score. Schemes from fine to coarse:
`phase_kind_seq` → `kind_seq` → `kind_set` → `post_kind_set`. Two timelines are in the same family
iff they share the key under the chosen scheme. Optional **`ArchetypeIndex`** (SQLite) accumulates
families across runs, **append-only** (never updates/deletes).

### 2. Event Relationship Graph (`graph.py`)
Links events **within** one timeline by **factual temporal relations only**: `FOLLOWS`
(consecutive in time), `SAME_MINUTE`, `WITHIN_<W>M`. Edges carry only `delta_seconds` — no
weights-as-scores, no causal/predictive labels. Exports Graphviz **DOT**.

### 3. Research Query Engine (`query.py`)
Searches by **filter conditions only** — `kinds`, `phases`, `ts` range, `symbols`, and predicates
on **factual** detail fields (e.g. `ratio >= 4`). It **selects**, it never ranks/scores/predicts.
Filtering on a forbidden key (score/signal/…) is rejected. `select_timelines(...)` does
timeline-level boolean selection (contains-kind, archetype family, min-events).

### 4. Statistical Explorer (`stats.py`)
**Descriptive statistics only**: kind frequency, phase distribution, events-per-timeline,
inter-event gaps, time-to-first-kind (chronology), consecutive-kind-pair counts, family sizes.
**No** win-rate, returns, Sharpe, edge, or any performance/score metric (guarded).

### 5. Visualization (`viz.py`)
Dependency-free text/markup: `render_timeline`, `event_tree` (phase→kind→times),
`render_graph` / `graph_dot` (relationship graph + DOT), and `heatmap` / `render_heatmap`
(**counts** per kind × minute-bucket-from-anchor). Every cell is a count or a fact — never a score.

## Folder
```
research/knowledge/
├── archetypes.py   structural families (+ append-only ArchetypeIndex)
├── graph.py        Event Relationship Graph (factual relations, DOT)
├── query.py        Research Query Engine (filter conditions only)
├── stats.py        Statistical Explorer (descriptive only)
└── viz.py          timelines · event trees · relationship graphs · heatmaps
research/run_knowledge.py   demo CLI
```

## Usage
```python
from research.reconstruction import ReconstructionEngine
from research.knowledge import archetypes as A, stats as S, viz as V, Query

timelines = [ReconstructionEngine(bar_source).reconstruct(sym, anchor_ts) for sym, anchor_ts in ...]

A.family_sizes(timelines, "kind_set")          # research families
Query(kinds={"VWAP_CROSS_UP"}, phases={"POST"}).run(timelines)   # filter only
S.summary(timelines)                            # descriptive stats
print(V.event_tree(timelines[0]))               # visualise
print(V.render_heatmap(timelines))              # counts heatmap
```
Demo (synthetic, offline): `python research/run_knowledge.py --demo`.

## Boundaries
REKL never writes production data, never emits a feature/score/signal/prediction, and performs no
ML or trading logic. Any future predictive use of these families/graphs must pass the standard
feature-discovery path (admission, PIT proof, pre-registration, OOS, FDR, Vault) — never directly
from this knowledge layer.
