"""research/inspect/observation_inspector.py — explain ONE ObservationRow.

Pure debugging / explainability. Read-only. It loads one ObservationRow and renders
every field in human-readable form, recomputes the registry signature, checks the PIT
and long-only invariants, and explains exactly why the row would pass or fail
`assert_signed()`. It computes NO features and makes NO trading judgement.
"""
from __future__ import annotations

from aurum_stocks.foundation.observation_builder import ObservationRow, registry_signature


def evaluate(row: ObservationRow) -> dict:
    """Non-throwing version of ObservationRow.assert_signed(): returns a verdict dict."""
    required = {
        "symbol_registry_id": row.symbol_registry_id,
        "regime_snapshot_id": row.regime_snapshot_id,
        "setup_version": row.setup_version,
        "label_spec_id": row.label_spec_id,
        "universe_version_id": row.universe_version_id,
        "scanner_version_id": row.scanner_version_id,
        "registry_signature_hash": row.registry_signature_hash,
    }
    missing = [k for k, v in required.items() if not v]
    recomputed = registry_signature(
        row.symbol_registry_id, row.regime_snapshot_id, row.setup_version,
        row.label_spec_id, row.universe_version_id, row.scanner_version_id)
    sig_ok = (recomputed == row.registry_signature_hash)
    pit_ok = (row.data_as_of_ts <= row.signal_ts_utc)
    long_only_ok = (row.direction == "LONG")
    checks = {
        "fully_signed": (not missing, f"missing: {missing}" if missing else "all 6 ids present"),
        "signature_match": (sig_ok, f"recomputed={recomputed} stored={row.registry_signature_hash}"),
        "pit_data_as_of": (pit_ok, f"data_as_of={row.data_as_of_ts} <= signal={row.signal_ts_utc}"),
        "long_only": (long_only_ok, f"direction={row.direction}"),
    }
    passed = all(ok for ok, _ in checks.values())
    return {"passed": passed, "checks": checks, "recomputed_signature": recomputed}


def inspect_row(row: ObservationRow) -> str:
    v = evaluate(row)
    L = []
    L.append("=" * 64)
    L.append(f"OBSERVATION  {row.observation_id}    [{'PASS' if v['passed'] else 'FAIL'}]")
    L.append("=" * 64)
    L.append("-- identity --")
    L.append(f"  schema_version : {row.schema_version}")
    L.append(f"  symbol         : {row.symbol}")
    L.append(f"  direction      : {row.direction}")
    L.append(f"  signal_ts_utc  : {row.signal_ts_utc}")
    L.append(f"  signal_ts_et   : {row.signal_ts_et}")
    L.append(f"  data_as_of_ts  : {row.data_as_of_ts}")
    L.append(f"  ingestion_ts   : {row.ingestion_ts_utc}")
    L.append(f"  dataset_role   : {row.dataset_role}")
    L.append("-- reference versions (the 6 signed ids) --")
    L.append(f"  symbol_version   : {row.symbol_registry_id}")
    L.append(f"  regime_version   : {row.regime_snapshot_id}")
    L.append(f"  setup_version    : {row.setup_type} @ {row.setup_version}")
    L.append(f"  label_version    : {row.label_spec_id}")
    L.append(f"  universe_version : {row.universe_version_id}")
    L.append(f"  scanner_version  : {row.scanner_version_id}")
    L.append(f"  registry_signature: {row.registry_signature_hash}")
    L.append("-- scan context (recorded, NOT signature inputs) --")
    L.append(f"  scanner_score : {row.scanner_score}")
    L.append(f"  scanner_rank  : {row.scanner_rank}")
    L.append(f"  batch_id      : {row.candidate_batch_id}")
    L.append("-- features present (names only; values not interpreted) --")
    names = sorted(row.features.keys()) if isinstance(row.features, dict) else []
    L.append(f"  {len(names)} feature(s): {', '.join(names) if names else '(none)'}")
    L.append("-- validation / why pass-or-fail --")
    for name, (ok, detail) in v["checks"].items():
        L.append(f"  [{'OK ' if ok else 'XX '}] {name}: {detail}")
    L.append("=" * 64)
    return "\n".join(L)
