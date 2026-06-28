"""
registries/research_registry.py — meta-research layer (spec §8).

Research Manifest: every hypothesis is REGISTERED (with predicted_effect + a frozen
test spec) BEFORE any OOS/Vault look — this is pre-registration as a first-class object.
Experiment Ledger: append-only log of every run. A REJECTED hypothesis is terminal; a
re-test requires a NEW hypothesis_id (anti-p-hacking). No predictive metric is computed
here — this layer only records registrations and runs.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import sqlite3
import uuid


def _hash(*f) -> str:
    return hashlib.sha256("|".join(str(x) for x in f).encode()).hexdigest()[:16]


_ALLOWED = {
    "REGISTERED": {"TESTING", "REJECTED"},
    "TESTING": {"OOS_PASS", "OOS_FAIL", "REJECTED"},
    "OOS_PASS": {"VAULT_PASS", "VAULT_FAIL", "REJECTED"},
    "OOS_FAIL": {"REJECTED"},          # a failed OOS is terminal for this hypothesis_id
    "VAULT_PASS": {"CONFIRMED", "REJECTED"},
    "VAULT_FAIL": {"REJECTED"},
    "CONFIRMED": set(),                 # terminal
    "REJECTED": set(),                  # terminal
}


class ResearchRegistryError(Exception):
    pass


class ResearchRegistry:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def register_hypothesis(self, *, hypothesis_id: str, statement: str,
                            predicted_effect: str, frozen_test_spec: dict,
                            features_used: list | None = None, label_spec_version="",
                            setup_scope="", symbol_scope="", regime_scope="",
                            author="") -> str:
        # pre-registration requires the prediction AND the test spec up front.
        if not statement or not predicted_effect or not frozen_test_spec:
            raise ResearchRegistryError(
                "pre-registration requires statement + predicted_effect + frozen_test_spec")
        if self.conn.execute("SELECT 1 FROM research_hypothesis WHERE hypothesis_id=?",
                             (hypothesis_id,)).fetchone():
            raise ResearchRegistryError(f"{hypothesis_id} already registered (append-only)")
        self.conn.execute(
            """INSERT INTO research_hypothesis
               (hypothesis_id, statement, predicted_effect, created_at, author,
                features_used, label_spec_version, setup_scope, symbol_scope, regime_scope,
                frozen_test_spec, status, row_hash)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (hypothesis_id, statement, predicted_effect,
             dt.datetime.now(dt.timezone.utc).isoformat(), author,
             json.dumps(features_used or [], sort_keys=True), label_spec_version,
             setup_scope, symbol_scope, regime_scope,
             json.dumps(frozen_test_spec, sort_keys=True), "REGISTERED",
             _hash(hypothesis_id, statement, predicted_effect)),
        )
        self.conn.commit()
        return hypothesis_id

    def status(self, hypothesis_id: str) -> str:
        r = self.conn.execute("SELECT status FROM research_hypothesis WHERE hypothesis_id=?",
                              (hypothesis_id,)).fetchone()
        if r is None:
            raise ResearchRegistryError(f"{hypothesis_id} not registered")
        return r["status"]

    def transition(self, hypothesis_id: str, new_status: str,
                   oos_result: str | None = None, vault_result: str | None = None) -> None:
        cur = self.status(hypothesis_id)
        if new_status not in _ALLOWED[cur]:
            raise ResearchRegistryError(f"illegal transition {cur} -> {new_status}")
        self.conn.execute(
            "UPDATE research_hypothesis SET status=?, oos_result=COALESCE(?,oos_result), "
            "vault_result=COALESCE(?,vault_result) WHERE hypothesis_id=?",
            (new_status, oos_result, vault_result, hypothesis_id))
        self.conn.commit()

    def log_experiment(self, *, hypothesis_id: str, feature="", dataset="",
                       sample_size=0, result="") -> str:
        if not self.conn.execute("SELECT 1 FROM research_hypothesis WHERE hypothesis_id=?",
                                 (hypothesis_id,)).fetchone():
            raise ResearchRegistryError(f"{hypothesis_id} not registered")
        exp_id = f"EXP_{uuid.uuid4().hex[:10]}"
        self.conn.execute(
            """INSERT INTO experiment_ledger
               (experiment_id, hypothesis_id, run_date, feature, dataset, sample_size,
                result, created_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            (exp_id, hypothesis_id, dt.date.today().isoformat(), feature, dataset,
             sample_size, result, dt.datetime.now(dt.timezone.utc).isoformat()),
        )
        self.conn.commit()
        return exp_id

    def family_size(self) -> int:
        """FDR family = distinct hypotheses ever tested on OOS/Vault, read from the
        append-only ledger (robust to later status changes like REJECTED). The
        statistics themselves live elsewhere; here we only count."""
        return self.conn.execute(
            """SELECT COUNT(DISTINCT hypothesis_id) c FROM experiment_ledger
               WHERE UPPER(dataset) IN ('OOS','VAULT')"""
        ).fetchone()["c"]
