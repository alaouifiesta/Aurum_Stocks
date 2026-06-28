"""Research-session provenance recorder. Reads hashes/versions read-only; writes
only to its own append-only research log. Runs no models, computes no features."""
from .research_session import ResearchSession, FROZEN_RUBRIC_HASH  # noqa: F401
