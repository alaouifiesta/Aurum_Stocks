"""
foundation/label_spec.py  —  R2: versioned, immutable Triple-Barrier label spec.

After calibration fixes (k, H, TIME-encoding), the choice is sealed as an
immutable, versioned object: LBL_V1. V1 can never be edited; a different choice
becomes LBL_V2, LBL_V3, ... The registry is append-only and refuses mutation.

This module holds NO calibration logic and makes NO performance claim — it only
records the frozen truth-definition as a first-class object.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
from dataclasses import dataclass, asdict
from enum import Enum


class TimeEncoding(str, Enum):
    TERNARY_ZERO = "TERNARY_ZERO"   # TIME outcome -> 0 (neutral 3-class)
    SIGN_RETURN = "SIGN_RETURN"     # TIME outcome -> sign of horizon-end return


@dataclass(frozen=True)
class LabelSpec:
    """Immutable. The frozen triple-barrier truth-definition for a collection era."""
    label_spec_id: str          # e.g. "LBL_V1"
    k: float                    # TB2 (symmetric ATR multiplier)
    horizon_min: int            # TB3 (time barrier, minutes; capped at RTH close)
    time_encoding: TimeEncoding # TB4
    atr_period: int = 14        # TB1 (frozen)
    atr_timeframe_min: int = 5  # TB1 (frozen)
    tie_break: str = "STOP_FIRST"        # TB5 (frozen)
    path_resolution_min: int = 1         # TB5 (frozen)
    created_at_utc: str = ""
    calibration_ref: str = ""   # research_registry INSTRUMENT_CALIBRATION id

    def content_hash(self) -> str:
        payload = {k: v for k, v in asdict(self).items()
                   if k not in ("created_at_utc",)}
        payload["time_encoding"] = self.time_encoding.value
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode()
        ).hexdigest()[:16]

    def to_json(self) -> str:
        d = asdict(self)
        d["time_encoding"] = self.time_encoding.value
        d["content_hash"] = self.content_hash()
        return json.dumps(d, indent=2)


def create_label_spec(label_spec_id: str, k: float, horizon_min: int,
                      time_encoding: TimeEncoding, calibration_ref: str = "") -> LabelSpec:
    """Build a spec from a calibration choice. Stamps created_at automatically."""
    return LabelSpec(
        label_spec_id=label_spec_id, k=float(k), horizon_min=int(horizon_min),
        time_encoding=TimeEncoding(time_encoding),
        created_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
        calibration_ref=calibration_ref,
    )


class LabelSpecRegistry:
    """Append-only store. A given label_spec_id is write-once; re-registering the
    same id with different content is rejected. Existing specs are never mutated."""

    def __init__(self):
        self._by_id: dict[str, LabelSpec] = {}

    def register(self, spec: LabelSpec) -> LabelSpec:
        existing = self._by_id.get(spec.label_spec_id)
        if existing is not None:
            if existing.content_hash() != spec.content_hash():
                raise ValueError(
                    f"{spec.label_spec_id} already frozen with different content "
                    f"({existing.content_hash()} != {spec.content_hash()}). "
                    f"Create a new version (e.g. LBL_V2) instead."
                )
            return existing  # idempotent re-register of identical content
        self._by_id[spec.label_spec_id] = spec
        return spec

    def get(self, label_spec_id: str) -> LabelSpec:
        return self._by_id[label_spec_id]

    def ids(self) -> list[str]:
        return sorted(self._by_id)
