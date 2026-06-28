# Research Notebook — <short title>

> Copy this file per hypothesis. Every notebook MUST open a ResearchSession so its
> provenance (hashes, label version, dataset version, timestamp) is recorded. A
> notebook NEVER modifies production data — it reads the immutable dataset and writes
> only to its own research log.

## 0. Provenance (auto-recorded)
```python
import sys, os
sys.path.insert(0, os.path.abspath("."))            # repo root  -> import research
sys.path.insert(0, os.path.abspath("src"))          # src        -> import aurum_stocks
from research.notebooks import ResearchSession
# from aurum_stocks.registries.db import connect
# from aurum_stocks.registries.label_registry import LabelRegistry
# lr = LabelRegistry(connect("aurum.sqlite"))       # read-only

with ResearchSession.open(
        hypothesis_id="H#001",
        dataset_version="<dataset tag>",
        # label_registry=lr,                          # captures LBL_V1 hash if frozen
) as session:
    print(session.manifest())
    # ... your read-only analysis here ...
```

## 1. Hypothesis
State it precisely, with the predicted effect BEFORE looking at OOS/Vault. Register it
in the Research Registry (pre-registration) — this notebook does not replace that.

## 2. Data (read-only)
Load observations / news archive read-only. Do not write to the registries DB.

## 3. Analysis
Counts / inspection / coverage only at this stage. No predictive features, no scoring.

## 4. Result
Record outcome; close the session (automatic on block exit).
