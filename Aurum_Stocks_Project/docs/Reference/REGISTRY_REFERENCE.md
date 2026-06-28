# Registry Reference

All registries are SQLite-backed (`registries/db.py`), append-only, and point-in-time.
Timestamps are stored as **UTC ISO** so lexicographic order = chronological order (the basis
of every as-of lookup). Reference resolvers are **NO-FALLBACK**.

## Reference registries (sign the observation)

### Symbol — `symbol_registry.py`
SCD Type-2, point-in-time. A symbol has many versions over time; an observation references
the version valid at `signal_ts`. Versioning trigger (§ build): categorical change
(exchange/sector/listing/country/is_etf/is_adr/is_spac/borrowable), float-bucket crossing, or
shares/float move ≥ 1% (immaterial refreshes dedupe → no version explosion). Continuous
metrics (market cap, ADV, RVOL) are **derived PIT**, not versioned. `resolve(symbol, as_of)`
raises `MissingSymbolVersion` if none. `universe(as_of)` returns the anti-survivorship PIT
universe (later-delisted present, pre-IPO absent). Companion: `short_interest_snapshot` (PIT).

### Regime — `regime_registry.py`
HOURLY snapshots (`RG1` locked). `resolve(as_of)` returns the latest snapshot at-or-before
`signal_ts` for a `regime_spec_version`; raises `MissingRegimeSnapshot` otherwise. Finer
cadence later = a new `REGIME_V2`, never a mutation.

### Setup — `setup_registry.py`
Open, versioned candidate-source provenance (Gap&Go, ORB, …). `resolve(setup_type)` → active
version id; raises `UnknownSetup`. The observation engine never branches on setup id.

### Scanner — `scanner_registry.py`
Code-provenance versioned scanners. `resolve(scanner_id)` → active `scanner_version_id`,
recorded on every observation so "which scanner found this?" is answerable. Scanner is a
research artifact, not a proven edge.

### Universe — `universe_registry.py`
Versioned membership **rules** (SMALL_CAP_US, …). Membership is **derived PIT** from the rule
+ symbol_registry (inherits anti-survivorship). `resolve(universe_id, as_of)` → version;
`members(...)` applies structural filters (listed, not ETF/ADR/SPAC, float buckets).

## Data-integrity registries (guard against fake edge)

### Data Quality — `data_quality_registry.py`
Two record kinds, never confused. **AS_OF** (PIT): feed-outage / missing-prints / stale-quote
computable from data ≤ signal_ts — may flag/reject an observation. **RETROSPECTIVE**
(session-level: missing-bars%, bad-ticks, CA-anomaly, quality score) — **analysis-time filter
only, never a feature**.

### News — `news_registry.py`
Provenance with the lookahead-critical distinction: **`news_available_ts`** (when we could
act — the PIT key) vs `news_publish_ts` (claimed publication — metadata only). Resolvers key
on `available_ts ≤ signal_ts`. Stores a headline **hash**, not full text.

### Halt — `halt_registry.py`
Halt episodes (start/end/reason: LULD/volatility/news). `is_halted_at(symbol, as_of)` is PIT
(only halts started ≤ as_of). "Pre-halt behavior" is a **retrospective** research join — an
imminent-halt feature is forbidden (pure lookahead).

### Microstructure — `microstructure_registry.py`
**RESERVED**, empty. Provisioned for future L2 / order-flow / tick research so no
re-architecture is needed later. When populated, its features still pass the full discovery
path (no privileged features).

## Meta-research & label

### Research — `research_registry.py`
Pre-registration manifest: every hypothesis is REGISTERED with `predicted_effect` + a frozen
test spec **before** any OOS/Vault look. Append-only Experiment Ledger logs every run.
REJECTED is terminal (re-test needs a new id). `family_size()` (FDR family) is counted from
the ledger.

### Label — `label_registry.py`
Write-once frozen `LabelSpec` + three hashes (`label_spec_hash`, `calibration_report_hash`,
`rubric_hash`). Re-freezing an id is blocked (immutable ⇒ `LBL_V2`). Currently the empty
mechanism — **no `LBL_V1` exists** until calibration is executed.

> `broker_registry` table exists in the schema (paper-execution provenance) but belongs to the
> execution track (Priority #3) and gates `READY_FOR_TRADING`, not `READY_FOR_COLLECTION`.
