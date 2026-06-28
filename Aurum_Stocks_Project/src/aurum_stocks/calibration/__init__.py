"""Aurum Stocks — Calibration Framework (Phase 1, Priority #1).

Decides the Triple-Barrier label definition (TB2 k, TB3 H, TB4 TIME-encoding)
on label-property grounds only. Feature-blind by construction.
"""
from . import config, barriers, metrics, grid, report  # noqa: F401
from .data_provider import (  # noqa: F401
    DataProvider, SyntheticDataProvider, PolygonDataProvider,
)
