# Project Status

| field | value |
|---|---|
| **READY_FOR_COLLECTION** | **FALSE** |
| Current blocker | `LBL_V1_FROZEN = FALSE` — SIP calibration run not yet executed |
| RUBRIC_RATIFIED | **TRUE** |
| Frozen `rubric_hash` | `11cf5f1c64319a790e172e104df4878f8c6eecaa50503588b6e89962ed01628c` |
| Integrity status | **6/6 GREEN** |
| Priority #2 | **BUILD COMPLETE** (registries · observation · PIT · calibration · integrity · data-integrity · research/label registries) |
| Priority #3 | **NOT AUTHORIZED** (no execution / scanner logic / ML / trading) |
| Pipeline · MDVPL | **IMPLEMENTED + tested** (`pipeline/mdvpl/`; read-only validation/provenance; mock provider only) |
| Research platform | **COMPLETE + tested** (news · inspector · explore · audit · RERL · REKL — read-only) |
| Tests | **9 suites green** |
| `LBL_V1` | **NOT created** (calibration not executed; Label Registry is the empty mechanism) |

## Build completion (Priority #2)
- Reference registries: symbol (SCD-2 PIT, NO-FALLBACK) · regime (HOURLY) · setup · scanner · universe — **done**.
- Observation Builder: setup-agnostic, 6-id signature (RH2), GC-7 long-only hard-fail — **done**.
- PIT Feature Gate (PASS/FAIL/UNKNOWN; UNKNOWN==REJECTED) — **done**.
- Feature Registry (no-anonymous-features admission + lifecycle; `LIQUIDITY_SHOCK` class) — **done**.
- Calibration Framework (label-property metrics only) + Burn Ledger + Partition Assigner — **done**.
- Integrity Suite (6 checks) + `READY_FOR_COLLECTION` interlock — **done**.
- Data-integrity registries: data_quality · news · halt · microstructure(reserved) — **done**.
- Research Registry (pre-registration + ledger) · Label Registry (write-once) — **done**.
- Provider interfaces + mocks (no SIP/network) — **done**.

## Beyond Priority #2 (additive, non-gating)
- Research platform (`research/`): news archive · observation inspector · dataset explorer · coverage audit — **done**.
- RERL (`research/reconstruction/`): factual event timelines — **done**.
- REKL (`research/knowledge/`): archetypes · graph · query · stats · viz — **done**.
- Pipeline Phase 1 — MDVPL (`pipeline/mdvpl/`): provider-agnostic data validation + append-only provenance, read-only/pass-through — **done, tested**.
- None of the above changes the gate; `READY_FOR_COLLECTION` stays FALSE until `LBL_V1` is frozen.

## Execution phases (summary)
Operational roadmap of record: **`IMPLEMENTATION_ROADMAP.md`** (single reference). This table is a
status snapshot only; on any disagreement, `IMPLEMENTATION_ROADMAP.md` wins.

| # | phase | status |
|---|---|---|
| 0 | Foundations & Calibration substrate | ✅ done |
| — | `LBL_V1` freeze (operator, SIP) | ⬜ not started — **the single blocker** |
| 1 | MDVPL (Market Data Validation & Provenance) | ✅ done — tested |
| 2 | Collection Layer | ⬜ not started (next) |
| 3 | Observation Store | ⬜ not started |
| 4 | Dataset Builder | ⬜ not started |
| 5 | Feature Discovery | 🔒 future (authorization required) |
| 6 | ML | 🔒 future |
| 7 | Paper Trading | 🔒 future |
| 8 | Live Trading | 🔒 future (`LIVE_ALLOWED = FALSE`) |

## Single remaining action (operator)
Ratify-confirmed rubric is frozen. Execute the SIP calibration run per
`docs/Operator/CALIBRATION_RUNBOOK.md` → freeze `LBL_V1` → `READY_FOR_COLLECTION` flips TRUE.
No data vendor is reachable from the build environment, so only the operator can run it.

> Authoritative status lives in `docs/Reference/SYSTEM_STATE_LOCK.md`.
