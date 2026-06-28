"""research/notebooks/research_session.py — provenance recorder for every hypothesis.

A research session auto-stamps the provenance that makes a result reproducible:
  * hypothesis id
  * dataset version
  * registry hashes (rubric, and label_spec if LBL_V1 is frozen)
  * label version (e.g. LBL_V1, or None if not yet frozen)
  * execution timestamp (UTC)

It writes an append-only manifest to a research log directory. It NEVER modifies
production data: it only reads hashes/versions (read-only) and writes to its own log.
It runs no models and computes no features.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import uuid
from dataclasses import dataclass, field, asdict

FROZEN_RUBRIC_HASH = "11cf5f1c64319a790e172e104df4878f8c6eecaa50503588b6e89962ed01628c"


@dataclass
class ResearchSession:
    hypothesis_id: str
    dataset_version: str
    registry_hashes: dict = field(default_factory=dict)
    label_version: str | None = None
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    execution_ts_utc: str = field(
        default_factory=lambda: dt.datetime.now(dt.timezone.utc).isoformat())
    status: str = "OPEN"
    log_dir: str = "./research_log"

    @staticmethod
    def open(hypothesis_id: str, dataset_version: str, *,
             label_registry=None, rubric_hash: str = FROZEN_RUBRIC_HASH,
             log_dir: str = "./research_log") -> "ResearchSession":
        """Capture provenance (read-only) and write the opening manifest.

        `label_registry`, if provided, is queried READ-ONLY for the frozen LBL_V1
        spec hash and version. Nothing is written to it."""
        hashes = {"rubric_hash": rubric_hash}
        label_version = None
        if label_registry is not None:
            try:
                rec = label_registry.get("LBL_V1")
                if rec:
                    label_version = "LBL_V1"
                    hashes["label_spec_hash"] = rec.get("label_spec_hash", "")
                    hashes["calibration_report_hash"] = rec.get("calibration_report_hash", "")
            except Exception:
                pass  # read-only best-effort; never fail the session on registry read
        s = ResearchSession(hypothesis_id=hypothesis_id, dataset_version=dataset_version,
                            registry_hashes=hashes, label_version=label_version,
                            log_dir=log_dir)
        s._write("OPEN")
        return s

    def close(self, status: str = "DONE") -> None:
        self.status = status
        self._write("CLOSE")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close("ERROR" if exc_type else "DONE")
        return False

    def manifest(self) -> dict:
        return asdict(self)

    def _write(self, phase: str) -> None:
        os.makedirs(self.log_dir, exist_ok=True)
        path = os.path.join(self.log_dir, f"{self.session_id}.jsonl")
        rec = {"phase": phase, "written_ts_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
               **self.manifest()}
        with open(path, "a") as fh:           # append-only
            fh.write(json.dumps(rec) + "\n")
