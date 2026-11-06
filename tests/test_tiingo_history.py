"""Evidence-bound multi-partition research EOD/daily-fundamental histories.

Synthetic offline receipts only; this suite never contacts Tiingo or starts
a producer. These studies cannot qualify a point-in-time backtest.
"""
from __future__ import annotations

from datetime import datetime
import hashlib
import json

import pytest

import collectors.tiingo_archive as a
from lib.dataos.tiingo_reader import (
    TiingoViewRefusal, read_research_history, read_research_view,
)
from scripts.tiingo_materialize import materialize_one

CUTOFF = "2026-10-10T00:00:00Z"
START = "2019-01-01"
END = "2019-01-31"


@pytest.fixture
def lake(tmp_path, monkeypatch):
    monkeypatch.setattr(a, "EXTERNAL_MOUNT", tmp_path)
    return a.Archive(tmp_path / "tiingo", check_mount=False, free_floor=0)


def saved(lake, source, data, *, symbol="AMD", observed="2026-10-09T05:00:00Z",
          start="2019-01-01", end="2019-01-20"):
    path = a.request_path(source, symbol, {"startDate": start, "endDate": end})
    response = lake.store_response(
        source, symbol, path, json.dumps(data, separators=(",", ":")).encode(),
        received_at=observed,
    )
    receipt = next(
        json.loads(file.read_text())
        for file in (lake.root / "receipts").rglob("*.json")
        if json.loads(file.read_text()).get("raw_sha256") == response["raw_sha256"]
    )
    assert materialize_one(lake.root, receipt, free_floor=0)["status"] == "WRITTEN"
    return observed[:10], response["raw_sha256"]


def history(lake, refs, **kwargs):
    args = dict(
        root=lake.root, check_mount=False,
        source="eod-bars", vendor_symbol="AMD", refs=refs,
        start_market_date=START, end_market_date=END,
        observed_before_utc=CUTOFF, acknowledge_hindsight=True,
    )
    args.update(kwargs)
    return read_research_history(**args)


def test_two_disjoint_eod_request_windows_become_one_research_series(lake):
    first = saved(lake, "eod-bars", [
        {"date": "2019-01-02", "open": 10, "close": 12, "volume": 100},
        {"date": "2019-01-03", "open": 12, "close": 13, "volume": 102},
    ], start="2019-01-01", end="2019-01-04")
    second = saved(lake, "eod-bars", [
        {"date": "2019-01-07", "open": 14, "close": 15, "volume": 105},
    ], start="2019-01-05", end="2019-01-20")
    result = history(lake, [second, first])
    assert [row["market_date"] for row in result.rows] == [
        "2019-01-02", "2019-01-03", "2019-01-07"]
    assert result.metadata()["rows"] == 3
    assert result.metadata()["source_partitions"] == 2
    assert result.metadata()["availability_clock"] == "SOURCE_CAPTURE_ONLY_NO_PIT"
    assert result.metadata()["pit_backtest_eligible"] is False
    assert result.metadata()["redistribution_admitted"] is False
    assert result.metadata()["market_session_completeness_proven"] is False
    assert result.metadata()["historical_identity_admitted"] is False
    assert all(row["source_vendor"] == "tiingo" for row in result.rows)


def test_daily_fundamentals_longitudinal_preserves_metric_granularity(lake):
    first = saved(lake, "fund-daily", [
        {"date": "2019-01-02", "peRatio": 12, "marketCap": 0},
    ], start="2019-01-01", end="2019-01-04")
    second = saved(lake, "fund-daily", [
        {"date": "2019-01-03", "peRatio": 13, "marketCap": None},
    ], start="2019-01-03", end="2019-01-20")
    result = history(lake, [first, second], source="fund-daily")
    assert [(r["market_date"], r["metric_code"], r["metric_value"]) for r in result.rows] == [
        ("2019-01-02", "marketCap", 0.0),
        ("2019-01-02", "peRatio", 12.0),
        ("2019-01-03", "marketCap", None),
        ("2019-01-03", "peRatio", 13.0),
    ]
    assert result.metadata()["observed_market_dates"] == 2
    assert result.metadata()["pit_backtest_eligible"] is False


def test_conflicting_eod_revisions_are_refused_not_last_write_wins(lake):
    first = saved(lake, "eod-bars", [{"date": "2019-01-02", "close": 12}],
                  observed="2026-10-09T05:00:00Z")
    corrected = saved(lake, "eod-bars", [{"date": "2019-01-02", "close": 120}],
                      observed="2026-10-09T06:00:00Z")
    with pytest.raises(TiingoViewRefusal, match="conflicting vendor revisions"):
        history(lake, [first, corrected])


def test_partial_fundamental_metric_set_is_not_silently_fused(lake):
    first = saved(lake, "fund-daily", [
        {"date": "2019-01-02", "peRatio": 12, "marketCap": 100},
    ])
    second = saved(lake, "fund-daily", [
        {"date": "2019-01-02", "peRatio": 12, "marketCap": 100, "netDebt": None},
    ], observed="2026-10-09T06:00:00Z")
    with pytest.raises(TiingoViewRefusal, match="conflicting vendor revisions"):
        history(lake, [first, second], source="fund-daily")


def test_identical_overlap_is_deduplicated_with_latest_capture_receipt(lake):
    first = saved(lake, "eod-bars", [{"date": "2019-01-02", "close": 12}],
                  observed="2026-10-09T05:00:00Z")
    second = saved(lake, "eod-bars", [
        {"date": "2019-01-02", "close": 12},
        {"date": "2019-01-03", "close": 14},
    ], observed="2026-10-09T06:00:00Z")
    result = history(lake, [second, first])
    assert result.identical_overlap_dates == 1
    assert len(result.rows) == 2
    assert result.rows[0]["source_observed_at_utc"] == "2026-10-09T06:00:00Z"
    assert result.rows[0]["source_sha256"] == second[1]


def test_explicit_asof_capture_cutoff_blocks_future_vintage(lake):
    capture = saved(lake, "eod-bars", [{"date": "2019-01-02", "close": 12}])
    with pytest.raises(TiingoViewRefusal, match="not observed by"):
        history(lake, [capture], observed_before_utc="2026-10-09T04:59:00Z")


def test_producer_capture_timestamps_cannot_be_promoted_to_market_time_availability(lake):
    capture = saved(lake, "eod-bars", [{"date": "2019-01-02", "close": 12}])
    result = history(lake, [capture])
    assert result.observed_before_utc == "2026-10-10T00:00:00+00:00"
    assert result.rows[0]["adjustment_basis_detail"] == "vendor_adjusted_not_historical_vintage"
    assert not result.pit_backtest_eligible
    assert not result.redistribution_admitted


def test_reader_does_not_create_any_files(lake):
    capture = saved(lake, "eod-bars", [{"date": "2019-01-02", "close": 12}])
    baseline = {
        str(p): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in lake.root.rglob("*") if p.is_file()
    }
    history(lake, [capture])
    after = {
        str(p): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in lake.root.rglob("*") if p.is_file()
    }
    assert baseline == after


def test_zero_partitions_cannot_be_reported_as_complete_history(lake):
    with pytest.raises(TiingoViewRefusal, match="explicit bounded"):
        history(lake, [])


@pytest.mark.parametrize("bad", [
    "2026-10-09T05:00:00", "garbage", "2026-10-09",
])
def test_cutoff_must_have_real_timezone(lake, bad):
    capture = saved(lake, "eod-bars", [{"date": "2019-01-02", "close": 12}])
    with pytest.raises(TiingoViewRefusal, match="date or timezone"):
        history(lake, [capture], observed_before_utc=bad)


@pytest.mark.parametrize("kwargs", [
    {"acknowledge_hindsight": False},
    {"max_partitions": True},
    {"max_rows": 0},
    {"max_rows": 1.5},
    {"start_market_date": "2019-02-01"},
    {"end_market_date": "2019-1-31"},
    {"source": "fund-statements"},
    {"vendor_symbol": "NVDA"},
])
def test_invalid_purpose_budget_identity_or_period_refuses(lake, kwargs):
    capture = saved(lake, "eod-bars", [{"date": "2019-01-02", "close": 12}])
    with pytest.raises(TiingoViewRefusal):
        history(lake, [capture], **kwargs)


def test_cannot_claim_additional_partitions_from_duplicate_reference(lake):
    capture = saved(lake, "eod-bars", [{"date": "2019-01-02", "close": 12}])
    with pytest.raises(TiingoViewRefusal, match="duplicate capture"):
        history(lake, [capture, capture])


def test_total_rows_are_bounded_across_partition_assemblies(lake):
    capture = saved(lake, "eod-bars", [
        {"date": "2019-01-02", "close": 12},
        {"date": "2019-01-03", "close": 13},
    ])
    with pytest.raises(TiingoViewRefusal, match="row cap"):
        history(lake, [capture], max_rows=1)


def test_future_market_date_after_source_capture_is_refused(lake):
    capture = saved(lake, "eod-bars", [{"date": "2029-01-02", "close": 12}])
    with pytest.raises(TiingoViewRefusal, match="future or invalid"):
        history(lake, [capture], end_market_date="2030-01-31")


def test_selected_capture_missing_from_archive_refuses_without_fallback(lake):
    with pytest.raises(TiingoViewRefusal, match="lacks artifact-bound"):
        history(lake, [("2026-10-09", "a" * 64)])


def test_observed_market_date_is_not_exchange_calendar_gap_proof(lake):
    capture = saved(lake, "eod-bars", [{"date": "2019-01-02", "close": 12}])
    result = history(lake, [capture])
    assert result.metadata()["observed_market_dates"] == 1
    assert result.metadata()["market_session_completeness_proven"] is False


@pytest.mark.parametrize("bad_refs", [
    [("2026-10-09", ["a" * 64])],
    [(None, "a" * 64)],
    [("2026-10-09", "b" * 64), ("2026-10-09", ["c" * 64])],
    [["2026-10-09", "a" * 64, "extra"]],
])
def test_untrusted_capture_reference_shape_must_refuse_cleanly(lake, bad_refs):
    with pytest.raises(TiingoViewRefusal):
        history(lake, bad_refs)


def test_selected_partition_without_rows_in_range_is_not_complete_history(lake):
    capture = saved(lake, "eod-bars", [{"date": "2019-01-02", "close": 12}])
    result = history(lake, [capture], start_market_date="2019-02-01",
                     end_market_date="2019-02-28")
    assert result.rows == ()
    assert result.metadata()["observed_market_dates"] == 0
    assert result.metadata()["market_session_completeness_proven"] is False


def test_revision_order_is_deterministic_independent_of_supplied_ref_order(lake):
    first = saved(lake, "eod-bars", [{"date": "2019-01-02", "close": 12}],
                  observed="2026-10-09T05:00:00Z")
    second = saved(lake, "eod-bars", [{"date": "2019-01-03", "close": 13}],
                   observed="2026-10-09T06:00:00Z")
    result = history(lake, [second, first])
    assert result.source_partitions == (first, second)


def test_history_cannot_accept_market_dates_outside_original_vendor_request(lake):
    # The present producer does not enforce this on raw bodies. A read-only
    # research study must not splice it into a historical series as valid.
    bad = saved(lake, "eod-bars", [{"date": "2019-01-02", "close": 12}],
                start="2019-01-06", end="2019-01-10")
    with pytest.raises(TiingoViewRefusal, match="outside original request"):
        history(lake, [bad])


def test_split_adjusted_history_cannot_silently_combine_current_adjustment_vintages(lake):
    first = saved(lake, "eod-bars", [
        {"date": "2019-01-02", "close": 12, "adjClose": 10},
    ], observed="2026-10-09T05:00:00Z")
    later = saved(lake, "eod-bars", [
        {"date": "2019-01-02", "close": 12, "adjClose": 8},
    ], observed="2026-10-09T06:00:00Z")
    with pytest.raises(TiingoViewRefusal, match="conflicting vendor revisions"):
        history(lake, [first, later])


def test_local_longitudinal_reader_uses_no_network_or_secret(monkeypatch, lake):
    capture = saved(lake, "eod-bars", [{"date": "2019-01-02", "close": 12}])

    def forbidden(*args, **kwargs):
        pytest.fail("research history used credential or contacted external provider")

    monkeypatch.setattr(a, "collect_one", forbidden)
    monkeypatch.setattr(a, "read_key", forbidden)
    from scripts import tiingo_ingest as ingest
    monkeypatch.setattr(ingest, "boats_stream", forbidden)
    assert history(lake, [capture]).metadata()["rows"] == 1


# Same existing research reader, now with a distinct as-reported/restated
# statement release timeline. The source timestamp is a vendor release claim,
# never a demonstrated historical known-at clock.
from lib.dataos.tiingo_reader import read_research_statement_timeline


def statement(release="2020-02-01", *, year=2019, quarter=4, net_income=42,
              metrics=None):
    return {
        "date": release, "year": year, "quarter": quarter,
        "statementData": {
            "incomeStatement": metrics if metrics is not None else [
                {"dataCode": "netIncome", "value": net_income},
            ],
        },
    }


def statement_saved(lake, reports, *, symbol="AMD", as_reported=True,
                    observed="2026-10-09T05:00:00Z",
                    start="2018-01-01", end="2021-12-31"):
    params = {"startDate": start, "endDate": end}
    if as_reported is not None:
        params["asReported"] = "true" if as_reported else "false"
    path = a.request_path("fund-statements", symbol, params)
    capture = lake.store_response(
        "fund-statements", symbol, path,
        json.dumps(reports, separators=(",", ":")).encode(), received_at=observed,
    )
    receipt = next(
        json.loads(file.read_text())
        for file in (lake.root / "receipts").rglob("*.json")
        if json.loads(file.read_text()).get("raw_sha256") == capture["raw_sha256"]
    )
    assert materialize_one(lake.root, receipt, free_floor=0)["status"] == "WRITTEN"
    return observed[:10], capture["raw_sha256"]


def timeline(lake, refs, **kw):
    args = dict(vendor_symbol="AMD", refs=refs, start_release_date="2019-01-01",
                end_release_date="2021-12-31", observed_before_utc=CUTOFF,
                as_reported=True, root=lake.root, check_mount=False,
                acknowledge_hindsight=True)
    args.update(kw)
    return read_research_statement_timeline(**args)


def test_as_reported_statement_releases_from_separate_captures(lake):
    first = statement_saved(lake, [statement(
        "2019-05-01", year=2019, quarter=1, net_income=1,
    )], start="2019-01-01", end="2019-09-01")
    second = statement_saved(lake, [statement(
        "2020-02-01", year=2019, quarter=0, net_income=42,
    )], start="2019-09-02", end="2020-12-31")
    result = timeline(lake, [second, first])
    assert [(r["statement_public_release_date_vendor"], r["fiscal_year"],
             r["fiscal_quarter"], r["metric_value"]) for r in result.rows] == [
        ("2019-05-01", 2019, 1, 1.0),
        ("2020-02-01", 2019, 0, 42.0),
    ]
    meta = result.metadata()
    assert meta["source"] == "fund-statements"
    assert meta["as_reported_dimension"] == "AS_REPORTED_CURRENT_PERIOD"
    assert meta["distinct_fiscal_periods"] == 2
    assert meta["source_partitions"] == 2
    assert meta["source_release_is_vendor_claim"] is True
    assert meta["availability_clock"] == "SOURCE_CAPTURE_ONLY_NO_PIT"
    assert meta["report_history_completeness_proven"] is False
    assert meta["historical_known_at_proven"] is False
    assert meta["pit_backtest_eligible"] is False
    assert meta["redistribution_admitted"] is False


def test_latest_restated_dimension_is_not_mislabeled_as_reported(lake):
    capture = statement_saved(lake, [statement(
        metrics=[{"dataCode": "netIncome", "value": -10},
                 {"dataCode": "zero", "value": 0},
                 {"dataCode": "undisclosed", "value": None}],
    )], as_reported=False)
    result = timeline(lake, [capture], as_reported=False)
    assert result.metadata()["as_reported_dimension"] == "LATEST_RESTATED_RETROSPECTIVE"
    assert [row["metric_value"] for row in result.rows] == [-10.0, None, 0.0]
    assert all(row["requested_as_reported"] is False for row in result.rows)
    assert not result.pit_backtest_eligible


def test_cannot_mix_as_reported_and_latest_restated_source_views(lake):
    one = statement_saved(lake, [statement()], as_reported=True)
    another = statement_saved(lake, [statement(net_income=123)], as_reported=False)
    with pytest.raises(TiingoViewRefusal, match="cannot mix"):
        timeline(lake, [one, another], as_reported=True)


def test_statement_revisions_with_same_release_but_different_numbers_are_refused(lake):
    before = statement_saved(lake, [statement(net_income=42)],
                             observed="2026-10-09T05:00:00Z")
    after = statement_saved(lake, [statement(net_income=40)],
                            observed="2026-10-09T06:00:00Z")
    with pytest.raises(TiingoViewRefusal, match="conflicting statement vintages"):
        timeline(lake, [before, after])


def test_statement_vintage_partial_metric_set_is_not_silently_spliced(lake):
    before = statement_saved(lake, [statement(net_income=42)],
                             observed="2026-10-09T05:00:00Z")
    after = statement_saved(lake, [statement(metrics=[
        {"dataCode": "netIncome", "value": 42},
        {"dataCode": "oneTimeGain", "value": 9},
    ])], observed="2026-10-09T06:00:00Z")
    with pytest.raises(TiingoViewRefusal, match="conflicting statement vintages"):
        timeline(lake, [before, after])


def test_different_public_release_labels_for_same_fiscal_period_remain_distinct(lake):
    first = statement_saved(lake, [statement("2020-02-01", net_income=42)])
    second = statement_saved(lake, [statement("2020-05-01", net_income=55)],
                             observed="2026-10-09T06:00:00Z")
    result = timeline(lake, [first, second])
    assert len(result.rows) == 2
    assert result.metadata()["distinct_fiscal_periods"] == 1
    assert result.metadata()["distinct_vendor_release_labels"] == 2
    assert result.metadata()["historical_known_at_proven"] is False


def test_identical_overlapping_report_is_deduplicated_by_latest_capture(lake):
    first = statement_saved(lake, [statement()], observed="2026-10-09T05:00:00Z")
    next_one = statement_saved(lake, [
        statement(), statement("2020-05-01", year=2020, quarter=1, net_income=5),
    ], observed="2026-10-09T06:00:00Z")
    result = timeline(lake, [next_one, first])
    assert len(result.rows) == 2
    assert result.identical_report_overlaps == 1
    assert result.rows[0]["source_observed_at_utc"] == "2026-10-09T06:00:00Z"
    assert result.source_partitions == (first, next_one)


def test_statement_capture_not_available_before_cutoff(lake):
    capture = statement_saved(lake, [statement()])
    with pytest.raises(TiingoViewRefusal, match="after requested observation cutoff"):
        timeline(lake, [capture], observed_before_utc="2026-10-09T04:00:00Z")


def test_vendor_release_date_outside_original_request_range_is_refused(lake):
    capture = statement_saved(lake, [statement()],
                              start="2021-01-01", end="2021-12-31")
    with pytest.raises(TiingoViewRefusal, match="outside original vendor request"):
        timeline(lake, [capture])


def test_statement_unknown_as_reported_dimension_cannot_be_assumed_true(lake):
    capture = statement_saved(lake, [statement()], as_reported=None)
    with pytest.raises(TiingoViewRefusal, match="cannot mix"):
        timeline(lake, [capture])


def test_future_claimed_statement_release_is_not_accepted_from_old_capture(lake):
    capture = statement_saved(lake, [statement("2029-02-01")], end="2030-01-01")
    with pytest.raises(TiingoViewRefusal, match="future statement release"):
        timeline(lake, [capture], end_release_date="2030-12-31")


@pytest.mark.parametrize("kwargs", [
    {"acknowledge_hindsight": False},
    {"as_reported": "true"},
    {"max_rows": True},
    {"max_partitions": 0},
    {"start_release_date": "2022-01-01"},
    {"observed_before_utc": "2026-10-09T04:00:00"},
    {"vendor_symbol": "NVDA"},
])
def test_invalid_statement_study_dimensions_fail_closed(lake, kwargs):
    capture = statement_saved(lake, [statement()])
    with pytest.raises(TiingoViewRefusal):
        timeline(lake, [capture], **kwargs)


def test_statement_missing_or_duplicate_source_references_refuse(lake):
    capture = statement_saved(lake, [statement()])
    with pytest.raises(TiingoViewRefusal, match="duplicate"):
        timeline(lake, [capture, capture])
    with pytest.raises(TiingoViewRefusal, match="lacks artifact-bound"):
        timeline(lake, [("2026-10-09", "a" * 64)])


def test_statement_timeline_never_reads_key_or_contacts_tiingo(lake, monkeypatch):
    capture = statement_saved(lake, [statement()])
    def forbidden(*a, **kw):
        pytest.fail("statement reader called vendor or key")
    from scripts import tiingo_ingest as ingest
    monkeypatch.setattr(a, "collect_one", forbidden)
    monkeypatch.setattr(a, "read_key", forbidden)
    monkeypatch.setattr(ingest, "boats_stream", forbidden)
    before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in lake.root.rglob("*") if p.is_file()}
    result = timeline(lake, [capture])
    after = {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in lake.root.rglob("*") if p.is_file()}
    assert before == after
    assert not result.pit_backtest_eligible
