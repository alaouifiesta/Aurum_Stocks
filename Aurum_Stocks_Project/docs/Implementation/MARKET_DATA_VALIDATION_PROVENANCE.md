# Market Data Validation & Provenance Layer (MDVPL) — Design (DESIGN ONLY)

> **Status: DESIGN PROPOSAL — NOT BUILT. NON-GATING. The last architectural piece before
> implementation.** No code, no implementation, no registry/feature/gate/label change, and no
> change to the Observation Builder. `READY_FOR_COLLECTION` remains FALSE; all frozen artifacts
> stand.

MDVPL sits **between raw market-data sources and the Collection Layer**. It is a **gatekeeper and
provenance recorder**, not a transformer. It validates and **describes** data; it never edits data,
never creates features, and never creates observations.

```
raw sources (SIP bars/quotes/trades, news/halts/CAs)
        │
        ▼
┌──────────────────────────────────────────────┐
│  MDVPL  — validate · normalize interface ·   │   →  Quality Report (read-only)
│           record provenance                  │   →  Provenance Record (append-only)
└───────────────┬──────────────────────────────┘
                │ (data passes through UNCHANGED + a verdict)
                ▼
        Collection Layer → Observation Builder
```

---

## 1. Single responsibility
**Judge whether a batch of market data is fit to feed collection, and record exactly where it came
from — without altering it.** Two outputs only: a **Quality Report** (read-only) and a
**Provenance Record** (append-only). Nothing else.

## 2. What it is NOT (hard exclusions)
- **Not a transformer:** it never repairs, fills, smooths, adjusts, or re-times data. A bad batch is
  *flagged*, never *fixed*.
- **Not a feature/observation producer:** zero features, zero `ObservationRow`s, zero scores,
  signals, sentiment, or predictions.
- **Not a gate:** it does not flip `READY_FOR_COLLECTION` or any production gate. It emits a verdict
  the future Collection Layer may consult; the existing gate set is untouched.
- **Not a registry change:** it reads the existing registries read-only; it adds none.

---

## 3. Provider-agnostic interface (interface unification)
MDVPL defines a single **read-only source contract** so every vendor looks identical to collection:
```
MarketDataSource (read-only, as-of):
    minute_bars(symbol, date)      -> rows[ts, open, high, low, close, volume]
    quotes(symbol, date)           -> rows[ts, bid, ask]
    trades(symbol, date)           -> rows[ts, price, size]            (optional)
    news(symbol, window)           -> provenance records (news_available_ts is the key)
    capabilities()                 -> which streams + SIP/consolidated flag + history depth
```
- The shape mirrors the contract the calibration `DataProvider` and RERL bar source already use, so
  **no new data model is introduced** — MDVPL only *unifies* and *wraps* sources behind one port.
- A vendor adapter (Polygon/Massive, others) implements this port; MDVPL is **vendor-agnostic** and
  any adapter is interchangeable. Adapters are read-only and make no decisions.
- `capabilities()` lets MDVPL **refuse non-SIP/single-venue feeds** before any validation (the SIP
  rule), since a true spread requires consolidated NBBO.

---

## 4. Validation checks (data-quality only, no edits)
Per batch = `(source, symbol, date[, stream])`. Each check yields PASS / WARN / FAIL + facts.

| group | check | failure example |
|---|---|---|
| **Completeness** | expected bars/quotes present for the session (incl. premarket warm-up) | missing minutes, truncated session |
| **Chronology** | timestamps strictly increasing, tz-aware UTC, correct ET/DST mapping | out-of-order rows, naive/ambiguous ts |
| **Coverage** | continuous coverage across the requested window | unexplained gaps between bars |
| **Sane values** | `low ≤ open/close ≤ high`, prices > 0, volume ≥ 0, `bid ≤ ask`, finite | crossed/negative spread, zero/negative price |
| **Consolidation** | volume consistent with consolidated SIP magnitude | single-venue (~2–5%) → not SIP |
| **Corporate-action sanity** | adjustment consistent with `symbol_registry` CA events (read-only) | unexplained price jump vs known split |
| **Halt consistency** | bar gaps reconcile with `halt_registry` (read-only) | gap with no halt / halt with prints |
| **News provenance** | `news_available_ts` present and `≥ publish_ts` plausibility | missing availability time |
| **Duplication** | duplicate timestamps / rows within a batch | repeated minute |

Outputs are **descriptions of facts** (counts, gap lists, offending timestamps). No score, no
ranking, no "quality grade as a number used downstream" — just PASS/WARN/FAIL + the evidence.

---

## 5. Provenance record (append-only)
One immutable record per validated batch, so every byte that ever feeds collection is traceable:
```
provenance:
  provenance_id            (uuid)
  source / vendor / adapter_version
  stream                   (bars | quotes | trades | news)
  symbol(s) / time_range   (UTC)
  feed_type                (SIP / consolidated flag)
  row_count / content_hash (sha256 of the raw batch bytes)
  fetch_ts_utc             (when fetched)
  validation_verdict       (PASS | WARN | FAIL)
  report_ref               (link to the quality report)
  schema_version
```
Append-only, never edited; a re-fetch is a **new** provenance record (links to prior by
`content_hash`). This is the data-side analogue of the news/event archives and the Collection
Layer's ingest manifest — they reconcile by `content_hash`.

---

## 6. Quality report (read-only output)
Per run, a human- and machine-readable report: the batch identity + provenance ref, every check's
PASS/WARN/FAIL with evidence, and a batch-level verdict. It **modifies no data**. The Collection
Layer may **consult** the verdict to decide whether to proceed or quarantine a window — but MDVPL
itself takes no such action and writes nothing into the observation path.

---

## 7. How it connects (and stays decoupled)
- **Upstream:** vendor adapters implement `MarketDataSource` (read-only).
- **Reads (read-only):** `symbol_registry` (CA/identity), `halt_registry` (gaps), `data_quality`
  semantics (AS_OF vs RETROSPECTIVE) — to *reconcile*, never to write.
- **Downstream:** the **Collection Layer** consumes the *same* validated source through the *same*
  port and consults the verdict; the **Observation Builder is unchanged** and sits one layer further
  down. MDVPL never calls the builder.
- **Firewall:** quality findings are **analysis-time facts**, never features. A `RETROSPECTIVE`
  quality flag may filter a window at research time but can never become a pre-signal input.

---

## 8. Append-only & read-only guarantees
- **Data:** never modified — MDVPL is pass-through; the raw batch flows on unchanged.
- **Provenance:** append-only; corrections/re-fetches are new records.
- **Reports:** read-only artifacts written to a validation output area, append-only.
- **Registries/gate/label:** untouched; reads only.

---

## 9. Position in the end-to-end path (now fixed)
```
LBL_V1 Frozen
      ▼
Market Data Validation & Provenance Layer (MDVPL)   ← this design
      ▼
Collection Layer
      ▼
Observation Store
      ▼
Dataset Builder
      ▼
Feature Discovery (future)
      ▼
ML  →  Paper Trading  →  Live Trading
```
MDVPL is the **first runtime step after the label is frozen**: it guarantees that only clean,
SIP-consolidated, fully-provenanced data ever reaches the Collection Layer — so every `ObservationRow`
downstream rests on validated, traceable inputs.

---

## 10. Why this is the last design piece
With MDVPL specified, every layer from frozen label to live trading has an agreed contract:
validated input (MDVPL) → signed immutable rows (Collection/Observation Store) → reproducible
datasets (Dataset Builder) → the existing discovery path (Feature Discovery → ML) → PAPER → LIVE.
Implementation can now proceed **layer by layer, each behind its own ratified gate**.

## 11. What this study does NOT change
No code, no registries, no gate, no label, no features, no Observation Builder. `READY_FOR_COLLECTION
= FALSE` and all frozen hashes stand. Building MDVPL would be a separate, explicitly-ratified
engineering task with its own gate — **awaiting your decision to begin implementation.**
