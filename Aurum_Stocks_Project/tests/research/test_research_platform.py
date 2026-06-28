"""Tests for the research platform (read-only infrastructure)."""
import os
import sys
import tempfile

_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _root)
sys.path.insert(0, os.path.join(_root, "src"))

from research.news import NewsArchive, NewsRecord, MockNewsProvider, PolygonNewsProvider
from research.news.records import market_session, availability_delay_seconds, headline_hash
from research.notebooks import ResearchSession, FROZEN_RUBRIC_HASH
from research.inspector import inspect_row, evaluate
from research.explore import dataset_explorer as DE
from research.audit import coverage_audit as CA
from research.demo import make_row, make_demo_rows, make_demo_archive


def test_news_record_provenance_only():
    rec = NewsRecord.build(
        article_id="A1", vendor="mock", source="wire", tickers=["abcd"],
        headline="ABCD reports something",
        publish_ts_utc="2025-03-03T14:59:15+00:00",
        news_available_ts_utc="2025-03-03T15:00:00+00:00", raw="body")
    assert rec.market_session == "RTH"                      # 10:00 ET
    assert rec.availability_delay_seconds == 45.0
    assert rec.tickers == ("ABCD",)
    assert rec.content_hash and rec.headline_hash
    # NO interpretation fields exist on the record
    for forbidden in ("sentiment", "score", "label", "bullish", "bearish"):
        assert not hasattr(rec, forbidden)
    print("news record provenance-only OK")


def test_market_session_boundaries():
    assert market_session("2025-03-03T12:00:00+00:00") == "PREMARKET"   # 07:00 ET
    assert market_session("2025-03-03T15:00:00+00:00") == "RTH"         # 10:00 ET
    assert market_session("2025-03-03T22:00:00+00:00") == "AFTERHOURS"  # 17:00 ET
    assert market_session("2025-03-01T15:00:00+00:00") == "CLOSED"      # Saturday
    print("market session boundaries OK")


def test_archive_append_only_and_dedup():
    arch = NewsArchive()
    r1 = NewsRecord.build(article_id="A1", vendor="V1", source="s", tickers=["ABCD"],
                          headline="ABCD update", publish_ts_utc="2025-03-03T14:59:00+00:00",
                          news_available_ts_utc="2025-03-03T15:00:00+00:00", raw="x")
    assert arch.record(r1)["status"] == "NEW"
    # exact dup: same vendor+article_id
    assert arch.record(r1)["dup_kind"] == "EXACT"
    # content dup: different id, same raw -> CONTENT
    r2 = NewsRecord.build(article_id="A2", vendor="V1", source="s", tickers=["ABCD"],
                          headline="totally different", publish_ts_utc="2025-03-03T14:00:00+00:00",
                          news_available_ts_utc="2025-03-03T14:01:00+00:00", raw="x")
    assert arch.record(r2)["dup_kind"] == "CONTENT"
    # story dup: different vendor+id, same headline + ticker within window
    r3 = NewsRecord.build(article_id="B9", vendor="V2", source="s2", tickers=["ABCD"],
                          headline="ABCD update", publish_ts_utc="2025-03-03T15:10:00+00:00",
                          news_available_ts_utc="2025-03-03T15:12:00+00:00", raw="y")
    assert arch.record(r3)["dup_kind"] == "STORY"
    # append-only: every record retained (4 rows, 3 of them linked as duplicates)
    assert arch.count() == 4
    assert len(arch.duplicates()) == 3
    print("archive append-only + dedup OK")


def test_archive_pit_query():
    arch = make_demo_archive()
    before = arch.available_as_of("ABCD", "2025-03-03T13:00:00+00:00")
    after = arch.available_as_of("ABCD", "2025-03-03T23:00:00+00:00")
    assert len(after) >= len(before)        # more available later
    # never returns items whose available_ts is after the as_of
    for row in arch.available_as_of("ABCD", "2025-03-03T15:00:00+00:00"):
        assert row["news_available_ts_utc"] <= "2025-03-03T15:00:00+00:00"
    print("archive PIT query OK")


def test_providers_mock_and_stub():
    recs = MockNewsProvider().fetch("ABCD", "2025-03-03T00:00:00+00:00",
                                    "2025-03-03T23:59:00+00:00")
    assert len(recs) == 3 and all(isinstance(r, NewsRecord) for r in recs)
    try:
        PolygonNewsProvider(api_key="").fetch("ABCD", "a", "b")
        assert False, "stub should refuse"
    except NotImplementedError:
        pass
    print("providers mock + stub OK")


def test_research_session_records_provenance():
    class DummyLabelReg:
        def get(self, k):
            return {"label_spec_hash": "abc", "calibration_report_hash": "def"} if k == "LBL_V1" else None
    with tempfile.TemporaryDirectory() as d:
        s = ResearchSession.open("H#001", "ds-2025Q1", label_registry=DummyLabelReg(), log_dir=d)
        m = s.manifest()
        assert m["hypothesis_id"] == "H#001"
        assert m["dataset_version"] == "ds-2025Q1"
        assert m["registry_hashes"]["rubric_hash"] == FROZEN_RUBRIC_HASH
        assert m["registry_hashes"]["label_spec_hash"] == "abc"
        assert m["label_version"] == "LBL_V1"
        assert m["execution_ts_utc"]
        s.close("DONE")
        files = os.listdir(d)
        assert len(files) == 1 and files[0].endswith(".jsonl")
    # no-label case
    with tempfile.TemporaryDirectory() as d:
        s2 = ResearchSession.open("H#002", "ds", log_dir=d)
        assert s2.manifest()["label_version"] is None
    print("research session provenance OK")


def test_inspector_pass_and_fail():
    good = make_row("obs-good")
    assert evaluate(good)["passed"] is True
    assert "PASS" in inspect_row(good)
    # long-only violation
    short = make_row("obs-short", direction="SHORT")
    assert evaluate(short)["passed"] is False
    # PIT violation
    pit = make_row("obs-pit", data_as_of="2025-03-04T00:00:00+00:00")
    assert evaluate(pit)["checks"]["pit_data_as_of"][0] is False
    # signature mismatch
    bad = make_row("obs-badsig", sig_override="deadbeef")
    assert evaluate(bad)["checks"]["signature_match"][0] is False
    print("inspector pass/fail OK")


def test_explorer_counts_only():
    rows = make_demo_rows()
    assert DE.total(rows) == 3
    assert DE.by_symbol(rows) == {"ABCD": 2, "WXYZ": 1}
    assert DE.by_regime(rows) == {"REG-1": 2, "REG-2": 1}
    assert DE.by_month(rows) == {"2025-03": 2, "2025-04": 1}
    assert set(DE.by_setup(rows)) == {"GAP_AND_GO", "OPENING_RANGE"}
    print("explorer counts OK")


def test_audit_reports():
    rows = make_demo_rows()
    # add a duplicate (same symbol/signal/setup as obs-1) and a bad-signature row
    dup = make_row("obs-dup", symbol="ABCD", signal="2025-03-03T15:00:00+00:00",
                   setup="GAP_AND_GO")
    badsig = make_row("obs-bad", sig_override="deadbeef")
    short = make_row("obs-short", direction="SHORT")
    rows2 = rows + [dup, badsig, short]
    assert ("ABCD", "2025-03-03T15:00:00+00:00", "GAP_AND_GO") in CA.duplicate_observations(rows2)
    assert "obs-bad" in CA.signature_integrity(rows2)
    assert "obs-short" in CA.long_only_violations(rows2)
    # orphan: known sets omit SYM-1 -> all rows flagged as missing symbol ref
    orph = CA.orphan_observations(rows, {"symbol": {"OTHER"}})
    assert len(orph["symbol"]) == 3
    # news coverage statistic (not a feature)
    nc = CA.news_coverage(rows, make_demo_archive())
    assert nc["observations"] == 3 and 0 <= nc["coverage_pct"] <= 100
    # render does not raise
    assert "Data Coverage Audit" in CA.render_report(
        rows, known={"symbol": {"SYM-1"}}, archive=make_demo_archive())
    print("audit reports OK")


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("\nALL RESEARCH PLATFORM TESTS PASSED")
