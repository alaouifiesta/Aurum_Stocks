"""pipeline/collection/keys.py — the deterministic candidate key.

Idempotency and deduplication key on a *deterministic* identity, never on the
ObservationRow.observation_id (which the frozen builder fills with a fresh uuid4 per call)
nor on ingestion_ts (also non-deterministic). Re-running a batch must therefore recompute
the same key for the same candidate and be recognised as already-collected.

Identity inputs (refinement #6 — scanner_id is included explicitly for future
multi-scanner compatibility, in addition to the registry_signature which already encodes
the resolved scanner_version_id):

    (symbol, signal_ts[UTC ISO], setup_type, scanner_id, registry_signature)

The registry_signature is the frozen 6-id RH2 hash produced by the builder, so two
candidates that resolve to different reference versions get different keys even if their
surface fields match. Pure function; no I/O; imports nothing from the frozen substrate.
"""
from __future__ import annotations

import hashlib


def _utc_iso(signal_ts) -> str:
    """Normalise a tz-aware pandas/py timestamp to a UTC ISO-8601 string."""
    if hasattr(signal_ts, "tz_convert"):          # pandas.Timestamp (tz-aware)
        return signal_ts.tz_convert("UTC").isoformat()
    if hasattr(signal_ts, "astimezone"):          # datetime
        import datetime as _dt
        return signal_ts.astimezone(_dt.timezone.utc).isoformat()
    return str(signal_ts)


def candidate_key(event, registry_signature: str) -> str:
    """Deterministic 32-hex identity for one candidate observation.

    `event` is a foundation.observation_builder.SignalEvent (duck-typed: needs
    .symbol, .signal_ts, .setup_type, .scanner_id). `registry_signature` is the row's
    registry_signature_hash (the frozen 6-id hash).
    """
    parts = (
        str(event.symbol),
        _utc_iso(event.signal_ts),
        str(event.setup_type),
        str(getattr(event, "scanner_id", "") or ""),
        str(registry_signature),
    )
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:32]
