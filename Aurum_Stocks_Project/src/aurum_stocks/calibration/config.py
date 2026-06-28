"""
Aurum Stocks — Calibration Framework
config.py — Frozen constants for the Triple-Barrier label calibration.

This module encodes the FROZEN decisions from spec v1.0-RC2 (Section 4) plus
the grids supplied in the Engineering Directive. Nothing here may be tuned by
looking at feature predictive power (see calibration/README — feature-blind rule).
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# FROZEN Triple-Barrier rules (spec v1.0-RC2 §4) — RATIFIED, do not change here.
# ---------------------------------------------------------------------------
ATR_PERIOD = 14            # TB1 (RATIFIED): ATR(14)
ATR_TIMEFRAME_MIN = 5      # TB1 (RATIFIED): computed on 5-minute bars, point-in-time
PATH_RESOLUTION_MIN = 1    # TB5 (RATIFIED): barrier touches evaluated on 1-minute bars
TIE_BREAK = "STOP_FIRST"   # TB5 (RATIFIED): a single bar touching both barriers -> STOP first
SYMMETRIC_BARRIERS = True  # §4.1: k_profit == k_stop (barrier is a measurement instrument)

# ---------------------------------------------------------------------------
# CALIBRATION GRIDS (Engineering Directive, Priority #1) — what we are deciding.
# ---------------------------------------------------------------------------
K_GRID = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]          # TB2 candidates (ATR multiplier)
H_GRID_MIN = [15, 30, 60, 90, 120, 240]            # TB3 candidates (time horizon, minutes)

# ---------------------------------------------------------------------------
# Session (America/New_York). Path & labels are RTH-confined for calibration (§4.4).
# Premarket bars are still loaded so ATR(14)@5m is warm by the open.
# ---------------------------------------------------------------------------
TZ = "America/New_York"
PREMARKET_START = "08:00"   # ATR warm-up window start
RTH_OPEN = "09:30"
RTH_CLOSE = "16:00"         # time_barrier is capped at this (no cross-session holds)

# Candidate-entry sampling cadence during RTH (minutes). Every Nth 1-min bar.
ENTRY_SAMPLE_EVERY_MIN = 5

# ---------------------------------------------------------------------------
# Universe (Engineering Directive). Extensible — add tickers freely.
# ---------------------------------------------------------------------------
SYMBOLS = [
    "MGNI", "CRDO", "KTOS", "AAOI", "SERV",
    "CDE", "SSRM", "SATS", "TTMI", "BE",
    "HL", "SM", "SG", "BBWI", "GIL",
    "PTON", "BKKT", "NXPW", "EGAN", "AXTI",
]

# ---------------------------------------------------------------------------
# Calibration Protocol thresholds (spec §5). Used ONLY to flag degenerate cells.
# A cell is "degenerate" if the time class dominates or any class is too rare.
# These are label-property guards, NOT performance metrics.
# ---------------------------------------------------------------------------
MAX_TIME_FRACTION = 0.70   # reject if TIME% > 70%
MIN_CLASS_FRACTION = 0.10  # reject if any of profit/stop/time < 10%
# Barrier must clear the spread; reject if median (k*ATR)/spread is below this.
MIN_BARRIER_SPREAD_RATIO = 3.0
