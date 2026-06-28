"""
registries/label_registry.py — write-once frozen label specs + the three hashes.

Mechanism only. NO LBL_V1 is created here (calibration is not executed). freeze() is
write-once: a label_spec_id can never be edited — recalibration produces a NEW id
(LBL_V2), per FD-1 immutability.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import sqlite3


class LabelRegistryError(Exception):
    pass


def canonical_label_hash(content: dict) -> str:
    """label_spec_hash = sha256 of canonical content (sorted keys, no whitespace),
    excluding the hash field itself."""
    payload = {k: v for k, v in content.items() if k != "label_spec_hash"}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class LabelRegistry:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def freeze(self, *, label_spec_id: str, spec_version: str, content: dict,
               calibration_report_hash: str, rubric_hash: str,
               burn_ledger_ref: str = "", author: str = "") -> dict:
        """Write-once. Computes label_spec_hash from content. Raises if id exists."""
        if self.conn.execute("SELECT 1 FROM label_registry WHERE label_spec_id=?",
                             (label_spec_id,)).fetchone():
            raise LabelRegistryError(
                f"{label_spec_id} already frozen — immutable; use a new id (e.g. LBL_V2)")
        label_spec_hash = canonical_label_hash(content)
        content_json = json.dumps(content, sort_keys=True, separators=(",", ":"))
        self.conn.execute(
            """INSERT INTO label_registry
               (label_spec_id, spec_version, content_json, label_spec_hash,
                calibration_report_hash, rubric_hash, burn_ledger_ref, sealed,
                created_at, author)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (label_spec_id, spec_version, content_json, label_spec_hash,
             calibration_report_hash, rubric_hash, burn_ledger_ref, 0,
             dt.datetime.now(dt.timezone.utc).isoformat(), author),
        )
        self.conn.commit()
        return {"label_spec_id": label_spec_id, "label_spec_hash": label_spec_hash,
                "calibration_report_hash": calibration_report_hash, "rubric_hash": rubric_hash}

    def seal(self, label_spec_id: str) -> None:
        self.conn.execute("UPDATE label_registry SET sealed=1 WHERE label_spec_id=?",
                          (label_spec_id,))
        self.conn.commit()

    def get(self, label_spec_id: str) -> dict | None:
        r = self.conn.execute("SELECT * FROM label_registry WHERE label_spec_id=?",
                              (label_spec_id,)).fetchone()
        return dict(r) if r else None

    def exists(self, label_spec_id: str) -> bool:
        return self.get(label_spec_id) is not None
