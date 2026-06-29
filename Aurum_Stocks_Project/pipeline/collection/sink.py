"""pipeline/collection/sink.py — the observation sink port (and an in-memory implementation).

The Collection Engine depends ONLY on the abstract ObservationSink (refinement #2): it never
imports or references a concrete sink. This keeps storage a swappable adapter — a future
Memory / File (Parquet, date-partitioned) / Database sink all satisfy the same port, and the
durable Observation Store is Phase 3, behind exactly this interface.

Append-only + write-once semantics (storage-layer, not by convention):
  * a candidate_key is inserted at most once; a second insert of the same key is a no-op that
    returns False (idempotent re-collection — never an overwrite, never a duplicate row);
  * stored rows are not mutated or deleted by the sink;
  * insertion order is preserved (rows() is stable).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable

from aurum_stocks.foundation.observation_builder import ObservationRow


class ObservationSink(ABC):
    """Append-only, write-once store of signed ObservationRows, keyed by candidate_key."""

    @abstractmethod
    def has(self, candidate_key: str) -> bool:
        """True if a row for this candidate_key has already been stored."""

    @abstractmethod
    def append(self, candidate_key: str, row: ObservationRow) -> bool:
        """Store row under candidate_key. Return True if newly stored, False if already present
        (no overwrite). Implementations MUST NOT mutate or replace an existing entry."""

    @abstractmethod
    def rows(self) -> Iterable[ObservationRow]:
        """Iterate stored rows in insertion order (read-only)."""

    @abstractmethod
    def __len__(self) -> int:
        ...


class InMemoryObservationSink(ObservationSink):
    """Reference in-memory sink (tests/demo). Append-only, write-once, insertion-ordered."""

    def __init__(self):
        self._by_key: dict[str, ObservationRow] = {}

    def has(self, candidate_key: str) -> bool:
        return candidate_key in self._by_key

    def append(self, candidate_key: str, row: ObservationRow) -> bool:
        if candidate_key in self._by_key:
            return False                      # write-once: never overwrite
        self._by_key[candidate_key] = row     # dict preserves insertion order (py3.7+)
        return True

    def rows(self):
        return list(self._by_key.values())

    def keys(self):
        return list(self._by_key.keys())

    def __len__(self) -> int:
        return len(self._by_key)
