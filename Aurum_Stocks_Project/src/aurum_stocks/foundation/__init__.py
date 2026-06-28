"""Aurum Stocks — Phase 1 foundation contracts (R1–R4) + feature gate.

R1 dataset_roles      — burn the calibration pilot, exclude it from discovery
R2 label_spec         — versioned, immutable triple-barrier truth-definition
R3 pit_harness        — independent lookahead defense (truncated vs full compute)
R4 observation_builder— locked, setup-agnostic, fully version-signed row contract
   pit_gate           — PASS/FAIL/UNKNOWN registration gate (UNKNOWN == REJECTED)
   feature_registry   — admission contract (no anonymous features) + lifecycle

The integrity suite lives in aurum_stocks.integrity (it depends on ..registries)."""
from . import (  # noqa: F401
    dataset_roles, label_spec, pit_harness, observation_builder,
    pit_gate, feature_registry,
)
