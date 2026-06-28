"""
registries/db.py — SQLite store for the three reference registries.

Timestamps are stored as **UTC ISO-8601** strings so lexicographic comparison
equals chronological order (the basis of every PIT range lookup). Dates are
stored as 'YYYY-MM-DD'.
"""
from __future__ import annotations

import sqlite3

import pandas as pd

SCHEMA_VERSION = "reg_v1"


def to_utc_iso(ts: pd.Timestamp) -> str:
    """tz-aware Timestamp -> UTC ISO string (sortable)."""
    if ts.tzinfo is None:
        raise ValueError("timestamp must be tz-aware (PIT requires explicit tz)")
    return ts.tz_convert("UTC").isoformat()


def connect(path: str = ":memory:") -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


DDL = [
    # --- symbol_registry: SCD-2, pure append-only (valid_to derived) -----------
    """
    CREATE TABLE IF NOT EXISTS symbol_registry (
        symbol_registry_id TEXT PRIMARY KEY,
        symbol             TEXT NOT NULL,
        exchange           TEXT,
        sector             TEXT,
        shares_outstanding REAL,
        float_raw          REAL,        -- free float (shares)
        float_bucket       TEXT,
        listing_status     TEXT NOT NULL,
        country            TEXT,
        is_etf             INTEGER,
        is_adr             INTEGER,
        is_spac            INTEGER,
        borrowable_flag    INTEGER,
        active_from        TEXT NOT NULL,
        active_to          TEXT,
        valid_from         TEXT NOT NULL, -- UTC ISO
        attr_as_of         TEXT,
        version_reason     TEXT,
        source             TEXT,
        correction_of      TEXT,
        row_hash           TEXT,
        ingested_at        TEXT,
        UNIQUE(symbol, valid_from)
    );""",
    "CREATE INDEX IF NOT EXISTS idx_sym_pit ON symbol_registry(symbol, valid_from DESC);",
    "CREATE INDEX IF NOT EXISTS idx_sym_universe ON symbol_registry(active_from, active_to);",

    # --- market_regime_registry: append-only snapshots, HOURLY (LOCK-1) --------
    """
    CREATE TABLE IF NOT EXISTS market_regime_registry (
        regime_snapshot_id  TEXT PRIMARY KEY,
        regime_ts           TEXT NOT NULL,   -- UTC ISO; must be <= referencing signal_ts
        cadence             TEXT NOT NULL,   -- HOURLY (RG1 locked)
        spy_trend           REAL,
        qqq_trend           REAL,
        iwm_trend           REAL,
        vix_level           REAL,
        breadth_ratio       REAL,
        risk_state          TEXT,            -- derived
        regime_spec_version TEXT NOT NULL,
        source              TEXT,
        row_hash            TEXT,
        ingested_at         TEXT,
        UNIQUE(regime_ts, cadence, regime_spec_version)
    );""",
    "CREATE INDEX IF NOT EXISTS idx_regime_pit ON market_regime_registry(regime_spec_version, cadence, regime_ts DESC);",

    # --- setup_registry: append-only versioned definitions ---------------------
    """
    CREATE TABLE IF NOT EXISTS setup_registry (
        setup_version_id TEXT PRIMARY KEY,
        setup_id         TEXT NOT NULL,
        version          TEXT NOT NULL,
        name             TEXT,
        description      TEXT,
        detector_ref     TEXT,            -- module path + commit hash
        params           TEXT,            -- JSON
        status           TEXT NOT NULL,   -- ACTIVE / DEPRECATED
        created_at       TEXT,
        author           TEXT,
        row_hash         TEXT,
        UNIQUE(setup_id, version)
    );""",
    "CREATE INDEX IF NOT EXISTS idx_setup_active ON setup_registry(setup_id, status);",

    # --- short_interest companion (PIT, bi-monthly feed; not a symbol version) --
    """
    CREATE TABLE IF NOT EXISTS short_interest_snapshot (
        symbol             TEXT NOT NULL,
        as_of              TEXT NOT NULL,   -- UTC ISO
        short_interest_pct REAL,
        source             TEXT,
        PRIMARY KEY (symbol, as_of)
    );""",
    "CREATE INDEX IF NOT EXISTS idx_si_pit ON short_interest_snapshot(symbol, as_of DESC);",

    # --- universe_registry: versioned membership rules (CHANGE #2) --------------
    """
    CREATE TABLE IF NOT EXISTS universe_registry (
        universe_version_id   TEXT PRIMARY KEY,
        universe_id           TEXT NOT NULL,   -- SMALL_CAP_US / MID_CAP_US / LARGE_CAP_US
        universe_spec_version TEXT NOT NULL,
        membership_rule       TEXT NOT NULL,   -- JSON
        valid_from            TEXT NOT NULL,   -- UTC ISO
        created_at            TEXT,
        source                TEXT,
        row_hash              TEXT,
        UNIQUE(universe_id, valid_from)
    );""",
    "CREATE INDEX IF NOT EXISTS idx_universe_pit ON universe_registry(universe_id, valid_from DESC);",

    # --- scanner_registry: code-provenance versioned scanners (CHANGE #3) -------
    """
    CREATE TABLE IF NOT EXISTS scanner_registry (
        scanner_version_id       TEXT PRIMARY KEY,
        scanner_id               TEXT NOT NULL,
        scanner_spec_version     TEXT NOT NULL,
        candidate_generation_logic TEXT,        -- module+commit+factor-set ref
        universe_id              TEXT,
        status                   TEXT NOT NULL,  -- ACTIVE / DEPRECATED
        created_at               TEXT,
        row_hash                 TEXT,
        UNIQUE(scanner_id, scanner_spec_version)
    );""",
    "CREATE INDEX IF NOT EXISTS idx_scanner_active ON scanner_registry(scanner_id, status);",

    # --- broker_registry: paper/live execution backends (CHANGE #5) ------------
    """
    CREATE TABLE IF NOT EXISTS broker_registry (
        broker_version_id   TEXT PRIMARY KEY,
        broker_id           TEXT NOT NULL,   -- TRADEZERO_PAPER / IBKR_PAPER / DAS_SIM / OTHER
        broker_spec_version TEXT NOT NULL,
        mode                TEXT NOT NULL,   -- PAPER / LIVE
        adapter_ref         TEXT,
        capabilities        TEXT,            -- JSON {long, short=false, partials}
        status              TEXT NOT NULL,
        created_at          TEXT,
        row_hash            TEXT,
        UNIQUE(broker_id, broker_spec_version)
    );""",

    # --- data_quality_registry: AS_OF (PIT) + RETROSPECTIVE (analysis-only) -----
    """
    CREATE TABLE IF NOT EXISTS data_quality_registry (
        dq_id                    TEXT PRIMARY KEY,
        symbol                   TEXT NOT NULL,
        pit_class                TEXT NOT NULL,   -- AS_OF | RETROSPECTIVE
        as_of                    TEXT,            -- AS_OF: UTC ISO
        session_date             TEXT,            -- RETROSPECTIVE: YYYY-MM-DD
        feed_outage_active       INTEGER,         -- AS_OF
        missing_prints_in_lookback INTEGER,       -- AS_OF
        stale_quote              INTEGER,         -- AS_OF
        last_good_ts             TEXT,            -- AS_OF
        missing_bars_pct         REAL,            -- RETROSPECTIVE
        n_bad_ticks              INTEGER,         -- RETROSPECTIVE
        n_outlier_trades         INTEGER,         -- RETROSPECTIVE
        halt_seconds             INTEGER,         -- RETROSPECTIVE
        feed_outage_seconds      INTEGER,         -- RETROSPECTIVE
        ca_anomaly_flag          INTEGER,         -- RETROSPECTIVE
        quality_score            REAL,            -- RETROSPECTIVE
        source                   TEXT,
        ingested_at              TEXT,
        row_hash                 TEXT
    );""",
    "CREATE INDEX IF NOT EXISTS idx_dq_asof ON data_quality_registry(symbol, pit_class, as_of DESC);",
    "CREATE INDEX IF NOT EXISTS idx_dq_session ON data_quality_registry(symbol, session_date);",

    # --- news_registry: provenance; PIT keyed on news_available_ts --------------
    """
    CREATE TABLE IF NOT EXISTS news_registry (
        news_id            TEXT PRIMARY KEY,
        symbol             TEXT NOT NULL,
        source             TEXT,            -- originator (PR, SEC, exchange, social)
        vendor             TEXT,            -- data provider that delivered it
        news_publish_ts    TEXT,            -- claimed publication (METADATA only)
        news_available_ts  TEXT NOT NULL,   -- when we could act (PIT timestamp)
        publication_delay_sec REAL,         -- available - publish
        headline_hash      TEXT,            -- store hash, not full text
        category           TEXT,
        ingested_at        TEXT
    );""",
    "CREATE INDEX IF NOT EXISTS idx_news_pit ON news_registry(symbol, news_available_ts DESC);",

    # --- halt_registry: halt episodes; as-of status is PIT ---------------------
    """
    CREATE TABLE IF NOT EXISTS halt_registry (
        halt_id        TEXT PRIMARY KEY,
        symbol         TEXT NOT NULL,
        halt_start_ts  TEXT NOT NULL,   -- UTC ISO
        halt_end_ts    TEXT,            -- null while ongoing
        halt_reason    TEXT,            -- LULD_UP/LULD_DOWN/VOLATILITY/NEWS_PENDING/...
        luld_band_pct  REAL,
        resumption_ts  TEXT,
        source         TEXT
    );""",
    "CREATE INDEX IF NOT EXISTS idx_halt_pit ON halt_registry(symbol, halt_start_ts DESC);",

    # --- microstructure_registry: RESERVED (empty now) -------------------------
    """
    CREATE TABLE IF NOT EXISTS microstructure_registry (
        microstructure_version_id TEXT PRIMARY KEY,
        data_type   TEXT,             -- L2_DEPTH/ORDER_FLOW/TICK_BY_TICK/IMBALANCE
        vendor      TEXT,
        resolution  TEXT,
        schema_ref  TEXT,
        pit_notes   TEXT,
        status      TEXT NOT NULL,    -- RESERVED
        created_at  TEXT
    );""",

    # --- research_registry: hypothesis pre-registration (Manifest) -------------
    """
    CREATE TABLE IF NOT EXISTS research_hypothesis (
        hypothesis_id    TEXT PRIMARY KEY,
        statement        TEXT NOT NULL,
        predicted_effect TEXT NOT NULL,   -- registered BEFORE testing
        created_at       TEXT,
        author           TEXT,
        features_used    TEXT,            -- JSON list of feature_id@version
        label_spec_version TEXT,
        setup_scope      TEXT,
        symbol_scope     TEXT,
        regime_scope     TEXT,
        frozen_test_spec TEXT NOT NULL,   -- JSON, frozen before any OOS/Vault look
        status           TEXT NOT NULL,   -- REGISTERED/TESTING/OOS_PASS/OOS_FAIL/VAULT_PASS/VAULT_FAIL/CONFIRMED/REJECTED
        oos_result       TEXT,
        vault_result     TEXT,
        row_hash         TEXT
    );""",
    # --- experiment_ledger: append-only run log --------------------------------
    """
    CREATE TABLE IF NOT EXISTS experiment_ledger (
        experiment_id TEXT PRIMARY KEY,
        hypothesis_id TEXT NOT NULL,
        run_date      TEXT,
        feature       TEXT,
        dataset       TEXT,
        sample_size   INTEGER,
        result        TEXT,
        created_at    TEXT
    );""",
    "CREATE INDEX IF NOT EXISTS idx_exp_hyp ON experiment_ledger(hypothesis_id);",

    # --- label_registry: frozen LabelSpec + the three hashes (write-once) ------
    """
    CREATE TABLE IF NOT EXISTS label_registry (
        label_spec_id           TEXT PRIMARY KEY,
        spec_version            TEXT NOT NULL,
        content_json            TEXT NOT NULL,
        label_spec_hash         TEXT NOT NULL,
        calibration_report_hash TEXT,
        rubric_hash             TEXT,
        burn_ledger_ref         TEXT,
        sealed                  INTEGER NOT NULL DEFAULT 0,
        created_at              TEXT,
        author                  TEXT
    );""",

    # --- migrations ledger -----------------------------------------------------
    """
    CREATE TABLE IF NOT EXISTS migrations (
        migration_id TEXT PRIMARY KEY,
        applied_at   TEXT,
        description  TEXT,
        tables       TEXT,
        reversible   INTEGER
    );""",
]


def init_schema(conn: sqlite3.Connection) -> None:
    for stmt in DDL:
        conn.execute(stmt)
    conn.commit()
