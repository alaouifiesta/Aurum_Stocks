"""research/demo.py — synthetic data so the read-only tools can be demonstrated
offline. SELF-TEST / DEMO ONLY. These are not real observations and never freeze,
train, or decide anything."""
from __future__ import annotations

from aurum_stocks.foundation.observation_builder import ObservationRow, registry_signature
from aurum_stocks.foundation.dataset_roles import DatasetRole
from research.news import NewsArchive, MockNewsProvider


def make_row(obs_id, *, symbol="ABCD", signal="2025-03-03T15:00:00+00:00",
             setup="GAP_AND_GO", sym_v="SYM-1", reg="REG-1", setup_v="SET-1",
             lbl="LBL_V1", uni="UNI-1", scn="SCN-1", direction="LONG",
             data_as_of=None, role=DatasetRole.TRAIN, features=None, sig_override=None):
    data_as_of = data_as_of or signal
    sig = sig_override or registry_signature(sym_v, reg, setup_v, lbl, uni, scn)
    return ObservationRow(
        observation_id=obs_id, schema_version="obs-1", symbol=symbol,
        symbol_registry_id=sym_v, setup_type=setup, setup_version=setup_v,
        direction=direction, signal_ts_utc=signal, signal_ts_et=signal,
        regime_snapshot_id=reg, label_spec_id=lbl, universe_version_id=uni,
        scanner_version_id=scn, registry_signature_hash=sig, data_as_of_ts=data_as_of,
        dataset_role=role, features=features or {"atr": 1.0, "rvol": 2.0},
        ingestion_ts_utc=signal)


def make_demo_rows():
    return [
        make_row("obs-1", symbol="ABCD", reg="REG-1", setup="GAP_AND_GO",
                 signal="2025-03-03T15:00:00+00:00"),
        make_row("obs-2", symbol="WXYZ", reg="REG-2", setup="OPENING_RANGE",
                 signal="2025-04-07T14:45:00+00:00"),
        make_row("obs-3", symbol="ABCD", reg="REG-1", setup="GAP_AND_GO",
                 signal="2025-03-10T15:30:00+00:00"),
    ]


def make_demo_archive():
    arch = NewsArchive()
    for rec in MockNewsProvider().fetch("ABCD", "2025-03-03T00:00:00+00:00",
                                        "2025-03-03T23:59:00+00:00"):
        arch.record(rec)
    return arch
