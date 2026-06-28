"""Aurum Stocks — Research Platform (read-only, evidence-producing).

This package is ADDITIVE research infrastructure. It touches none of the locked
production substrate (registries, gate, label, integrity, calibration). Hard rules,
true by construction across every module here:

  * produces EVIDENCE only — never a trading decision,
  * consumes only as-of-available information — never future information,
  * creates NO predictive features, NO scores, NO sentiment, NO labels.

Subpackages:
  news/      canonical historical news archive + provider interfaces/mocks (provenance only)
  notebooks/ research-session provenance recorder (auto-stamps hashes/versions)
  inspect/   ObservationRow inspector (debugging / explainability)
  explore/   read-only dataset statistics (counts only)
  audit/     read-only data-coverage / integrity-of-collection reports
"""
