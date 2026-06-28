"""Aurum Stocks runtime data pipeline (additive; isolated from the frozen src/aurum_stocks).

Build order (each layer behind its own ratified step):
  mdvpl/            Market Data Validation & Provenance Layer  [IMPLEMENTED]
  collection/       Collection Layer                           [pending]
  store/            Observation Store                          [pending]
  dataset_builder/  Research Dataset Builder                   [pending]

This package creates no features, scores, signals, predictions, or trades, and modifies no
frozen contract/registry/label/gate."""
