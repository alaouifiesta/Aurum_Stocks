"""
foundation/feature_registry.py — admission contract + lifecycle (item 6).

No anonymous features: a definition is admitted only if it carries
formula_ref · version · pit_proof(=PASS) · economic_rationale · feature_class.
The rationale's *presence* is required; its *content* never affects any verdict.

Lifecycle: OBSERVATION → TESTING → PROVISIONAL → CONFIRMED, with → REJECTED terminal.
(The CONFIRMED transition's OOS/Vault checks are hooks for the discovery phase.)
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from enum import Enum

from .pit_gate import PITGateLedger, Verdict


class FeatureClass(str, Enum):
    PRICE_STATE = "PRICE_STATE"
    LIQUIDITY_STATE = "LIQUIDITY_STATE"
    LIQUIDITY_SHOCK = "LIQUIDITY_SHOCK"    # sudden change/derivative (vol spike, spread compression, depth surge)
    SESSION_STATE = "SESSION_STATE"
    CROSS_MARKET = "CROSS_MARKET"
    SEQUENCE_STATE = "SEQUENCE_STATE"      # OUTCOME-DERIVED (resolved-before-signal)
    EXECUTION_STATE = "EXECUTION_STATE"    # OUTCOME-MODELED (never a pre-signal feature)
    CUSTOM = "CUSTOM"


class FeatureStatus(str, Enum):
    OBSERVATION = "OBSERVATION"
    TESTING = "TESTING"
    PROVISIONAL = "PROVISIONAL"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class FeatureDefinition:
    feature_id: str
    name: str
    version: str
    formula_ref: str          # module + commit hash
    inputs: tuple
    lookback_window: int
    pit_proof: str            # PIT gate run id (must be a PASS)
    economic_rationale: str   # presence required; content never gates a verdict
    feature_class: FeatureClass
    author: str = ""
    cross_row_dependent: bool = False  # required True for SEQUENCE_STATE
    created_at: str = ""


class AdmissionRejected(Exception):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


class FeatureRegistry:
    """Append-only registry; admission enforces the no-anonymous-features contract."""

    _ALLOWED = {
        FeatureStatus.OBSERVATION: {FeatureStatus.TESTING, FeatureStatus.REJECTED},
        FeatureStatus.TESTING: {FeatureStatus.PROVISIONAL, FeatureStatus.REJECTED},
        FeatureStatus.PROVISIONAL: {FeatureStatus.CONFIRMED, FeatureStatus.REJECTED},
        FeatureStatus.CONFIRMED: set(),
        FeatureStatus.REJECTED: set(),  # terminal
    }

    def __init__(self, pit_ledger: PITGateLedger):
        self._defs: dict[tuple, FeatureDefinition] = {}
        self._status: dict[tuple, FeatureStatus] = {}
        self._pit = pit_ledger

    def admit(self, d: FeatureDefinition) -> FeatureDefinition:
        # No-anonymous-features: every required field must be present/non-empty.
        for fld in ("feature_id", "name", "version", "formula_ref", "pit_proof",
                    "economic_rationale"):
            if not getattr(d, fld):
                raise AdmissionRejected(f"missing required field: {fld}")
        if not isinstance(d.feature_class, FeatureClass):
            raise AdmissionRejected("feature_class must be a FeatureClass enum")
        if d.lookback_window is None or d.lookback_window < 0:
            raise AdmissionRejected("lookback_window must be >= 0")
        # PIT proof must be a PASS (UNKNOWN/FAIL are rejected — UNKNOWN == REJECTED).
        try:
            verdict = self._pit.verdict_of(d.pit_proof)
        except KeyError:
            raise AdmissionRejected(f"pit_proof {d.pit_proof} not found in gate ledger")
        if verdict is not Verdict.PASS:
            raise AdmissionRejected(f"pit_proof verdict is {verdict.value}, only PASS admits")
        # feature_class / PIT-class cross-check.
        if d.feature_class is FeatureClass.EXECUTION_STATE:
            raise AdmissionRejected(
                "EXECUTION_STATE is OUTCOME-MODELED — it cannot be a pre-signal feature")
        if d.feature_class is FeatureClass.SEQUENCE_STATE and not d.cross_row_dependent:
            raise AdmissionRejected(
                "SEQUENCE_STATE requires cross_row_dependent=True (resolved-before-signal)")

        key = (d.feature_id, d.version)
        if key in self._defs:
            raise AdmissionRejected(f"{key} already admitted (versions are write-once)")
        object.__setattr__(d, "created_at",
                           dt.datetime.now(dt.timezone.utc).isoformat())
        self._defs[key] = d
        self._status[key] = FeatureStatus.OBSERVATION
        return d

    def status(self, feature_id: str, version: str) -> FeatureStatus:
        return self._status[(feature_id, version)]

    def transition(self, feature_id: str, version: str, new: FeatureStatus) -> None:
        key = (feature_id, version)
        cur = self._status[key]
        if new not in self._ALLOWED[cur]:
            raise AdmissionRejected(f"illegal transition {cur.value} -> {new.value}")
        self._status[key] = new
