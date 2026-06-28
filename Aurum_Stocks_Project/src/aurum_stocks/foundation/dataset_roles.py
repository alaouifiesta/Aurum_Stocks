"""
foundation/dataset_roles.py  —  R1: burn the calibration pilot.

Any observation that participated in choosing k/H/TIME must be permanently
excluded from TRAIN/VAL/OOS/VAULT. Without this, every future result is
contaminated (the truth-definition was tuned on the same data we later test on).

Mechanism (spec §5 "pilot slice ... then burned"):
  * Calibration consumes an explicit pilot SLICE (symbols x date-window).
  * That slice is recorded immutably in a CalibrationBurnLedger.
  * The PartitionAssigner stamps anything inside a burned slice as
    CALIBRATION_ONLY and it is auto-excluded by every downstream pipeline.
The slice-based guard is stronger than per-row tracking: nothing inside the
burned region can ever leak, even rows generated later.
"""
from __future__ import annotations

import datetime as dt
import hashlib
from dataclasses import dataclass, field
from enum import Enum


class DatasetRole(str, Enum):
    CALIBRATION_ONLY = "CALIBRATION_ONLY"   # burned — never enters discovery
    TRAIN = "TRAIN"
    VALIDATION = "VALIDATION"
    OOS = "OOS"
    VAULT = "VAULT"


PIPELINE_ROLES = frozenset(
    {DatasetRole.TRAIN, DatasetRole.VALIDATION, DatasetRole.OOS, DatasetRole.VAULT}
)


@dataclass(frozen=True)
class BurnedSlice:
    """An immutable region consumed by calibration. symbols=None means ALL."""
    start_date: dt.date
    end_date: dt.date
    symbols: frozenset | None = None
    reason: str = "TB_CALIBRATION"

    def contains(self, symbol: str, ts: dt.datetime) -> bool:
        d = ts.date()
        if not (self.start_date <= d <= self.end_date):
            return False
        return self.symbols is None or symbol in self.symbols


class CalibrationBurnLedger:
    """Append-only registry of burned slices. The authoritative exclusion list."""

    def __init__(self):
        self._slices: list[BurnedSlice] = []

    def burn(self, slice_: BurnedSlice) -> None:
        self._slices.append(slice_)

    def is_burned(self, symbol: str, ts: dt.datetime) -> bool:
        return any(s.contains(symbol, ts) for s in self._slices)

    def fingerprint(self) -> str:
        parts = sorted(
            f"{s.start_date}|{s.end_date}|{'ALL' if s.symbols is None else ','.join(sorted(s.symbols))}"
            for s in self._slices
        )
        return hashlib.sha256("\n".join(parts).encode()).hexdigest()[:16]


@dataclass
class PartitionAssigner:
    """Deterministic, write-once role assignment.

    Burn check first (R1). Otherwise a chronological split by date boundaries.
    Boundaries correspond to VP1 (still PENDING ratification): supply them once
    ratified. The mechanism is frozen; only the boundary dates are pending.
    """
    burn_ledger: CalibrationBurnLedger
    train_end: dt.date | None = None
    val_end: dt.date | None = None
    oos_end: dt.date | None = None   # after oos_end -> VAULT

    def assign(self, symbol: str, ts: dt.datetime) -> DatasetRole:
        if self.burn_ledger.is_burned(symbol, ts):
            return DatasetRole.CALIBRATION_ONLY
        d = ts.date()
        if self.train_end is None:
            # Boundaries not yet set (VP1 pending): leave unpartitioned-but-safe.
            # Still NEVER returns a pipeline role for burned data (handled above).
            return DatasetRole.TRAIN  # placeholder; real boundaries set at VP1
        if d <= self.train_end:
            return DatasetRole.TRAIN
        if self.val_end and d <= self.val_end:
            return DatasetRole.VALIDATION
        if self.oos_end and d <= self.oos_end:
            return DatasetRole.OOS
        return DatasetRole.VAULT


def assert_no_calibration_leak(rows) -> None:
    """Hard guard for any discovery pipeline. `rows` is an iterable of objects/dicts
    carrying a `dataset_role`. Raises if any CALIBRATION_ONLY row is present."""
    leaked = [
        getattr(r, "observation_id", None) or (r.get("observation_id") if isinstance(r, dict) else None)
        for r in rows
        if _role_of(r) == DatasetRole.CALIBRATION_ONLY
    ]
    if leaked:
        raise AssertionError(
            f"CALIBRATION_ONLY rows leaked into a discovery pipeline: {leaked[:5]}"
            f"{' ...' if len(leaked) > 5 else ''}"
        )


def filter_pipeline_dataset(rows):
    """Return only pipeline-eligible rows; calibration rows are dropped silently."""
    return [r for r in rows if _role_of(r) in PIPELINE_ROLES]


def _role_of(r) -> DatasetRole:
    v = getattr(r, "dataset_role", None)
    if v is None and isinstance(r, dict):
        v = r.get("dataset_role")
    return v if isinstance(v, DatasetRole) else DatasetRole(v)
