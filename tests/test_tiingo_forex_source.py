"""Offline exact-receipt Forex diagnostics never admit final bars."""
import copy
import hashlib
import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest
import collectors.tiingo_archive as archive_owner
from lib.dataos.tiingo_reader import TiingoView, TiingoViewRefusal
from lib.dataos.tiingo_views import research_rows
from lib.dataos.tiingo_forex import (
    diagnose_forex_view, read_forex_watch_source, reconcile_forex_intervals,
    QUALIFICATION_GAPS, MAX_RECONCILIATION_NATIVE_ROWS,
)
from scripts.tiingo_materialize import materialize_one


def payload():
    return [{"ticker": "usdjpy", "date": stamp, "open": 149.0, "high": 150.0,
             "low": 148.0, "close": close}
            for stamp, close in [("2026-10-19T00:00:00Z", 149.1), ("2026-10-19T00:01:00Z", 149.2)]]


def view_for(data=None, *, frequency="1min", observed_at="2026-10-21T13:00:00Z"):
    data = payload() if data is None else data
    raw = json.dumps(data).encode()
    rec = {"schema": "mastermind.tiingo.raw_receipt.v1", "source": "forex-bars",
           "symbol": "usdjpy", "vendor": "tiingo",
           "raw_sha256": hashlib.sha256(raw).hexdigest(),
           "observed_at_utc": observed_at,
           "request_path": archive_owner.request_path("forex-bars", "usdjpy", {"resampleFreq": frequency})}
    ident = archive_owner.receipt_identity(rec)
    rows = tuple(research_rows(raw, rec))
    return TiingoView(source="forex-bars", source_sha256=rec["raw_sha256"],
                     source_observed_at_utc=rec["observed_at_utc"], purpose="INSPECTION",
                     pit_backtest_eligible=False, redistribution_admitted=False, rows=rows,
                     source_request_path=rec["request_path"]), ident


def project(view, ident):
    return diagnose_forex_view(view, expected_pair="USDJPY", receipt_id=ident)


def test_dense_valid_source_retains_lineage_but_never_becomes_final_or_eligible():
    view, ident = view_for()
    before = copy.deepcopy(view.rows)
    result = project(view, ident)
    assert view.rows == before
    assert result["eligible_observations"] == []
    assert result["monitoring_admitted"] is False
    assert set(QUALIFICATION_GAPS) <= set(result["withheld_reasons"])
    assert result["source"]["source_receipt_id"] == ident
    assert result["source"]["source_observed_at_utc"] != result["candidate_observations"][0]["bar_at_vendor"]
    assert [x["source_row_ordinal"] for x in result["candidate_observations"]] == [0, 1]
    assert result["candidate_observations"][0]["vendor_ohlc"]["close"] == 149.1
    assert result["diagnostics"]["value_issue_counts"] == {}  # Missing FX volume is allowed.
    forbidden = {"bar_end", "available_at", "expires_at", "bar_sequence", "status", "observation_id", "revision", "feed", "calendar"}
    assert all(not forbidden.intersection(x) for x in result["candidate_observations"])
    json.dumps(result, allow_nan=False)


def test_empty_view_is_explicit_but_not_missing_or_unavailable():
    view, ident = view_for([])
    result = project(view, ident)
    assert result["source_state"] == "empty"
    assert result["diagnostics"]["rows"] == 0
    assert "empty_vendor_view" in result["withheld_reasons"]
    assert result["eligible_observations"] == []


@pytest.mark.parametrize("change", ["same", "different"])
def test_equal_instants_with_different_offsets_retain_both_rows_and_diagnose_conflicts(change):
    data = payload()
    data[1]["date"] = "2026-10-19T01:00:00+01:00"
    if change == "same":
        data[1]["close"] = data[0]["close"]
    view, ident = view_for(data)
    result = project(view, ident)
    assert result["diagnostics"]["duplicate_instant_rows"] == 1
    assert result["diagnostics"]["conflicting_ohlc_instants"] == int(change == "different")
    assert [x["bar_at_vendor"] for x in result["candidate_observations"]] == [x["date"] for x in data]
    assert result["eligible_observations"] == []


def test_distinct_nanoseconds_are_not_collapsed_into_duplicate_instants():
    data = payload()
    data[0]["date"] = "2026-10-19T00:00:00.000000001Z"
    data[1]["date"] = "2026-10-19T00:00:00.000000002Z"
    view, ident = view_for(data)
    d = project(view, ident)["diagnostics"]
    assert d["unique_valid_timestamp_instants"] == 2
    assert d["duplicate_instant_rows"] == 0
    assert d["value_issue_counts"]["subminute_timestamp"] == 2


def test_disorder_and_observed_spacing_do_not_reorder_fill_or_assert_missing_data():
    data = payload()
    data.insert(1, {**data[0], "date": "2026-10-19T04:00:00Z"})
    view, ident = view_for(data)
    result = project(view, ident)
    assert [x["bar_at_vendor"] for x in result["candidate_observations"]] == [x["date"] for x in data]
    d = result["diagnostics"]
    assert d["out_of_order_valid_timestamp_steps"] == 1
    assert d["observed_timestamp_steps_gt_reference"] == 1
    assert d["maximum_observed_timestamp_step_seconds"] == 239 * 60
    assert d["timestamp_spacing_proves_missing_data"] is False
    assert result["eligible_observations"] == []


@pytest.mark.parametrize("value,reason", [(None, "missing"), (True, "boolean"), (0, "nonpositive"),
    (-1, "nonpositive"), (float("nan"), "nonfinite"), (float("inf"), "nonfinite"), ("149.1", "not_numeric")])
def test_invalid_prices_are_retained_as_diagnostic_evidence_never_zero_filled(value, reason):
    view, ident = view_for()
    view.rows[0]["vendor_close"] = value
    result = project(view, ident)
    candidate = result["candidate_observations"][0]
    assert candidate["issues"]["close"] == reason
    if value is None:
        assert candidate["vendor_ohlc"]["close"] is None
    assert result["eligible_observations"] == []
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("stamp", ["2026-10-19T00:00:00", "not-a-clock", None])
def test_invalid_or_naive_timestamps_never_inherit_utc(stamp):
    view, ident = view_for()
    view.rows[0]["bar_at_vendor"] = stamp
    result = project(view, ident)
    assert result["candidate_observations"][0]["bar_at_vendor"] == stamp
    assert result["diagnostics"]["value_issue_counts"]["invalid_timestamp"] == 1
    assert result["eligible_observations"] == []


def test_inconsistent_ohlc_and_caller_supplied_final_assertions_are_not_admission():
    view, ident = view_for()
    view.rows[0].update(vendor_high=100, status="final", feed="claimed", revision=9,
                       available_at="2026-10-19T00:00:00Z", bar_end="2026-10-19T00:00:00Z")
    result = project(view, ident)
    assert result["candidate_observations"][0]["issues"]["ohlc_bounds"] == "inconsistent"
    assert result["eligible_observations"] == []


@pytest.mark.parametrize("key,value", [("ticker_vendor", "eurusd"),
    ("source_receipt_id", "0" * 64), ("source_sha256", "0" * 64),
    ("source_observed_at_utc", "2026-10-20T13:00:00Z"),
    ("source_rights_admitted", True), ("dataos_identity_admitted", True),
    ("pit_backtest_eligible", True), ("canonical_price_basis_admitted", True)])
def test_wrong_identity_mixed_lineage_or_promoted_flags_refuse(key, value):
    view, ident = view_for()
    view.rows[0][key] = value
    with pytest.raises(TiingoViewRefusal, match="lineage"):
        project(view, ident)


@pytest.mark.parametrize("kwargs", [{"source": "boats-bars"}, {"purpose": "PIT_BACKTEST"},
    {"pit_backtest_eligible": True}, {"redistribution_admitted": True}])
def test_bridge_does_not_inherit_claimed_canonical_authority(kwargs):
    view, ident = view_for()
    with pytest.raises(TiingoViewRefusal):
        project(replace(view, **kwargs), ident)


def test_row_budget_never_silently_truncates():
    view, ident = view_for()
    with pytest.raises(TiingoViewRefusal, match="cap"):
        project(replace(view, rows=view.rows * 10_001), ident)


@pytest.fixture
def retained(tmp_path, monkeypatch):
    monkeypatch.setattr(archive_owner, "EXTERNAL_MOUNT", tmp_path)
    lake = archive_owner.Archive(tmp_path / "lake", check_mount=False, free_floor=0)
    saved = lake.store_response("forex-bars", "usdjpy",
        archive_owner.request_path("forex-bars", "usdjpy", {"resampleFreq": "1min"}),
        json.dumps(payload()).encode(), received_at="2026-10-21T13:00:00Z")
    path = next((lake.root / "receipts/forex-bars").glob("*/*.json"))
    receipt = json.loads(path.read_text())
    output = materialize_one(lake.root, receipt, free_floor=0)
    return lake.root, path, receipt, saved, output


def test_file_boundary_uses_exact_existing_reader_and_leaves_artifacts_unchanged(retained):
    root, path, receipt, saved, output = retained
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob("*") if p.is_file()}
    result = read_forex_watch_source("2026-10-21", saved["receipt_id"], expected_pair="USDJPY",
                                    root=root, receipt_path=path, check_mount=False)
    assert result["source"]["source_sha256"] == receipt["raw_sha256"]
    assert result["diagnostics"]["rows"] == 2
    assert result["eligible_observations"] == []
    assert before == {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob("*") if p.is_file()}


@pytest.mark.parametrize("failure", ["raw_corruption", "manifest_promotion", "missing_manifest"])
def test_integrity_or_admission_failures_propagate_not_empty_success(retained, failure):
    root, path, receipt, saved, output = retained
    manifest = root / output["path"].replace("normalized/", "manifests/").replace(".parquet", ".json")
    if failure == "raw_corruption":
        (root / receipt["raw_path"]).write_bytes(b"corrupt")
    elif failure == "missing_manifest":
        manifest.unlink()
    else:
        content = json.loads(manifest.read_text()); content["redistribution_admitted"] = True
        manifest.write_text(json.dumps(content))
    with pytest.raises(TiingoViewRefusal):
        read_forex_watch_source("2026-10-21", saved["receipt_id"], expected_pair="USDJPY",
                               root=root, receipt_path=path, check_mount=False)


def test_equal_numeric_prices_are_not_a_conflict_due_to_int_float_representation():
    view, ident = view_for()
    view.rows[1]["bar_at_vendor"] = view.rows[0]["bar_at_vendor"]
    view.rows[0]["vendor_close"] = 149.0
    view.rows[1]["vendor_close"] = 149
    d = project(view, ident)["diagnostics"]
    assert d["duplicate_instant_rows"] == 1
    assert d["conflicting_ohlc_instants"] == 0



def minute_fixture(count=240, start=0):
    origin = datetime(2026, 10, 19, tzinfo=timezone.utc)
    return [{"ticker": "usdjpy", "date": (origin + timedelta(minutes=n)).isoformat(),
             "open": 149 + n / 1000, "high": 149.02 + n / 1000,
             "low": 148.98 + n / 1000, "close": 149.005 + n / 1000}
            for n in range(start, start + count)]


def native_fixture(minutes, label="2026-10-19T00:00:00Z"):
    return [{"ticker": "usdjpy", "date": label, "open": minutes[0]["open"],
             "high": max(row["high"] for row in minutes),
             "low": min(row["low"] for row in minutes),
             "close": minutes[-1]["close"]}]


def reconciliation_views(minutes=None, native=None, **clocks):
    minutes = minute_fixture() if minutes is None else minutes
    native = native_fixture(minutes) if native is None else native
    return (
        view_for(minutes, observed_at=clocks.get("minute_clock", "2026-10-21T13:00:00Z")),
        view_for(native, frequency="4hour",
                 observed_at=clocks.get("native_clock", "2026-10-21T13:00:02Z")),
    )


def reconcile(views):
    (minute, minute_id), (native, native_id) = views
    return reconcile_forex_intervals(minute, native, expected_pair="USDJPY",
                                    minute_receipt_id=minute_id, four_hour_receipt_id=native_id)


def start_window(result):
    return result["hypotheses"][0]["windows"][0]


@pytest.mark.parametrize("omitted", [None, 50])
def test_interval_equality_keeps_dense_and_sparse_coverage_separate(omitted):
    minutes = minute_fixture()
    if omitted is not None:
        minutes.pop(omitted)
    views = reconciliation_views(minutes)
    before = copy.deepcopy(views)
    result = reconcile(views)
    assert views == before
    window = start_window(result)
    assert window["all_ohlc_equal"] is True
    assert window["coverage"]["dense_240_minute_grid"] is (omitted is None)
    assert window["coverage"]["missing_expected_minute_slots"] == int(omitted is not None)
    assert window["coverage"]["missing_slots_prove_missing_vendor_data"] is False
    assert window["coverage"]["internal_unobserved_slots"] == int(omitted is not None)
    assert result["eligible_observations"] == []
    for flag in ("monitoring_admitted", "dataos_identity_admitted",
                 "pit_backtest_eligible", "redistribution_admitted"):
        assert result[flag] is False
    assert result["inputs"]["minute"]["product_use_approval"]["state"] == "COMPLETE"
    assert "product_rights_mapping_not_admitted" not in result["inputs"]["minute"]["withheld_reasons"]
    json.dumps(result, allow_nan=False)


def test_four_label_hypotheses_and_half_open_edges_remain_explicit():
    minutes = minute_fixture(722, -241)
    native = native_fixture(minute_fixture())
    result = reconcile(reconciliation_views(minutes, native))
    assert [h["summary"]["all_ohlc_equal_windows"] for h in result["hypotheses"]] == [1, 0, 0, 0]
    window = start_window(result)
    assert window["coverage"]["observed_source_row_ordinals"] == list(range(241, 481))
    assert window["edge_rows"] == {
        "at_interval_start": [241], "at_interval_end": [481],
        "last_before_start": [240], "first_at_or_after_end": [481],
    }
    assert result["comparison_semantics"]["hypothesis_selection"] is False


def test_native_ohlc_can_match_partial_open_interval_without_proving_closure():
    result = reconcile(reconciliation_views(minute_fixture(170),
        minute_clock="2026-10-19T02:49:03Z", native_clock="2026-10-19T02:49:05Z"))
    window = start_window(result)
    coverage = window["coverage"]
    assert window["all_ohlc_equal"] is True
    assert coverage["observed_minute_rows"] == 170
    assert coverage["missing_expected_minute_slots"] == 70
    assert coverage["missing_expected_minute_ranges"] == [{
        "first_utc": "2026-10-19T02:50:00+00:00",
        "last_utc": "2026-10-19T03:59:00+00:00", "slots": 70,
    }]
    assert coverage["interval_end_after_minute_receipt_observed"] is True
    assert coverage["interval_end_after_four_hour_receipt_observed"] is True
    assert coverage["trailing_unobserved_slots"] == 70
    assert result["receipt_observation_clocks"]["four_hour_minus_minute_nanoseconds"] == 2_000_000_000
    assert result["comparison_semantics"]["vendor_finality_proven"] is False
    assert result["eligible_observations"] == []


@pytest.mark.parametrize("minute_clock,native_clock,expected", [
    ("2026-10-19T03:59:59Z", "2026-10-19T04:00:00Z", (True, False)),
    ("2026-10-19T04:00:00Z", "2026-10-19T03:59:59Z", (False, True)),
    ("2026-10-19T04:00:00Z", "2026-10-19T04:00:00Z", (False, False)),
])
def test_each_original_receipt_clock_is_compared_separately(minute_clock, native_clock, expected):
    result = reconcile(reconciliation_views(minute_clock=minute_clock, native_clock=native_clock))
    coverage = start_window(result)["coverage"]
    assert (coverage["interval_end_after_minute_receipt_observed"],
            coverage["interval_end_after_four_hour_receipt_observed"]) == expected
    assert result["eligible_observations"] == []


def test_matching_close_does_not_hide_native_ohlc_mismatch():
    minutes = minute_fixture()
    native = native_fixture(minutes)
    native[0]["high"] += 1
    window = start_window(reconcile(reconciliation_views(minutes, native)))
    assert window["close_equal"] is True
    assert window["all_ohlc_equal"] is False
    assert window["equal_fields"] == {"open": True, "high": False, "low": True, "close": True}


@pytest.mark.parametrize("value", [None, True, 0, float("nan"), float("inf"), "149"])
@pytest.mark.parametrize("side", ["minute", "native"])
def test_invalid_numeric_evidence_withholds_comparison_and_serializes(value, side):
    views = reconciliation_views()
    views[0 if side == "minute" else 1][0].rows[0]["vendor_close"] = value
    result = reconcile(views)
    assert start_window(result)["all_ohlc_equal"] is None
    assert start_window(result)["blocked_reasons"]
    assert result["eligible_observations"] == []
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("stamp", [
    None, "not-a-clock", "2026-10-19T00:00:00",
    "2026-10-19T00:00:00.0000000001Z", "2026-10-19T00:00:00.000000001Z",
    "2026-10-19T00:00:00,000000001Z", "2026-10-19T00:00:00,0000000001Z",
])
@pytest.mark.parametrize("side", ["minute", "native"])
def test_invalid_or_subminute_clocks_never_gain_alignment_by_rounding(stamp, side):
    views = reconciliation_views()
    views[0 if side == "minute" else 1][0].rows[0]["bar_at_vendor"] = stamp
    result = reconcile(views)
    window = start_window(result)
    assert window["all_ohlc_equal"] is None
    assert result["row_issues"][side if side == "minute" else "four_hour"]
    assert result["eligible_observations"] == []
    json.dumps(result, allow_nan=False)


def test_nanoseconds_remain_distinct_but_cannot_form_a_minute_grid():
    views = reconciliation_views()
    views[0][0].rows[0]["bar_at_vendor"] = "2026-10-19T00:00:00.000000001Z"
    views[0][0].rows[1]["bar_at_vendor"] = "2026-10-19T00:00:00.000000002Z"
    result = reconcile(views)
    assert result["inputs"]["minute"]["diagnostics"]["duplicate_instant_rows"] == 0
    window = start_window(result)
    assert len(window["coverage"]["unexpected_minute_instants_utc"]) == 2
    assert window["coverage"]["dense_240_minute_grid"] is False
    assert window["all_ohlc_equal"] is None


@pytest.mark.parametrize("side", [0, 1])
@pytest.mark.parametrize("conflicting", [False, True])
def test_identical_or_conflicting_duplicate_instants_never_select_a_winner(side, conflicting):
    views = list(reconciliation_views())
    view, receipt = views[side]
    duplicate = dict(view.rows[0])
    duplicate["bar_at_vendor"] = "2026-10-19T01:00:00+01:00"
    if conflicting:
        duplicate["vendor_close"] += 0.001
    views[side] = (replace(view, rows=(*view.rows, duplicate)), receipt)
    result = reconcile(views)
    assert result["inputs"]["minute" if side == 0 else "four_hour"]["diagnostics"]["conflicting_ohlc_instants"] == int(conflicting)
    assert start_window(result)["all_ohlc_equal"] is None
    if side == 1:
        assert all(w["all_ohlc_equal"] is None for w in result["hypotheses"][0]["windows"])
    assert result["comparison_semantics"]["correction_selection"] is False


def test_timestamp_order_is_used_for_aggregation_without_mutating_original_order():
    minutes = minute_fixture()
    native = native_fixture(minutes)
    minutes.reverse()
    views = reconciliation_views(minutes, native)
    before = copy.deepcopy(views)
    result = reconcile(views)
    assert views == before
    window = start_window(result)
    assert window["all_ohlc_equal"] is True
    assert window["coverage"]["observed_source_row_ordinals"] == list(reversed(range(240)))
    assert result["inputs"]["minute"]["candidate_observations"][0]["bar_at_vendor"] == minutes[0]["date"]


@pytest.mark.parametrize("failure", ["frequency_request", "frequency_row", "pair", "receipt", "clock_precision"])
def test_reconciliation_refuses_wrong_context_or_precision(failure):
    views = list(reconciliation_views())
    view, receipt = views[0]
    if failure == "frequency_request":
        view = replace(view, source_request_path=archive_owner.request_path(
            "forex-bars", "usdjpy", {"resampleFreq": "4hour"}))
    elif failure == "frequency_row":
        view.rows[0]["requested_resample_frequency"] = "4hour"
    elif failure == "pair":
        view.rows[0]["ticker_vendor"] = "eurusd"
    elif failure == "receipt":
        receipt = "0" * 64
    else:
        view = replace(view, source_observed_at_utc="2026-10-21T13:00:00.0000000001Z")
    views[0] = (view, receipt)
    with pytest.raises(TiingoViewRefusal):
        reconcile(views)


def test_empty_inputs_are_distinct_and_no_fake_missing_data_claim_is_made():
    native = native_fixture(minute_fixture())
    result = reconcile(reconciliation_views([], native))
    window = start_window(result)
    assert window["coverage"]["observed_grid_state"] == "empty"
    assert window["coverage"]["missing_expected_minute_slots"] == 240
    assert window["coverage"]["leading_unobserved_slots"] is None
    assert window["blocked_reasons"] == ["no_observed_minute_rows"]
    result = reconcile(reconciliation_views([], []))
    assert all(h["windows"] == [] for h in result["hypotheses"])
    assert result["eligible_observations"] == []


def test_native_row_and_total_comparison_budgets_refuse_without_truncating():
    views = list(reconciliation_views())
    native, receipt = views[1]
    views[1] = (replace(native, rows=native.rows * (MAX_RECONCILIATION_NATIVE_ROWS + 1)), receipt)
    with pytest.raises(TiingoViewRefusal, match="native row cap"):
        reconcile(views)
    views = list(reconciliation_views())
    minute, receipt = views[0]
    views[0] = (replace(minute, rows=minute.rows * 40), receipt)
    native, receipt = views[1]
    views[1] = (replace(native, rows=native.rows * 12), receipt)
    with pytest.raises(TiingoViewRefusal, match="row reference cap"):
        reconcile(views)


def test_interval_arithmetic_never_wraps_out_of_timestamp_range():
    views = reconciliation_views()
    views[1][0].rows[0]["bar_at_vendor"] = "2262-04-11T23:47:16.854775807Z"
    result = reconcile(views)
    assert start_window(result)["blocked_reasons"] == ["interval_clock_out_of_range"]
    assert result["eligible_observations"] == []



@pytest.mark.parametrize("kind", ["unplaced", "outside_edge", "invalid_native"])
def test_all_emitted_row_references_are_charged_to_output_budget(monkeypatch, kind):
    import lib.dataos.tiingo_forex as forex
    views = list(reconciliation_views())
    view, receipt = views[0]
    rows = tuple(dict(row) for row in view.rows[:3])
    for row in rows:
        row["bar_at_vendor"] = None if kind == "unplaced" else "2026-10-19T04:00:00Z"
    views[0] = (replace(view, rows=rows), receipt)
    if kind == "invalid_native":
        views[1][0].rows[0]["bar_at_vendor"] = None
    # No minute row is selected by the first [00:00, 04:00) window. Its
    # unplaced list or duplicated boundary lists must still consume budget.
    monkeypatch.setattr(forex, "MAX_RECONCILIATION_ROW_REFERENCES", 3)
    with pytest.raises(TiingoViewRefusal, match="row reference cap"):
        reconcile(views)



def test_nanosecond_response_clocks_are_preserved_without_becoming_minute_labels():
    result = reconcile(reconciliation_views(
        minute_clock="2026-10-21T13:00:00.000000001Z",
        native_clock="2026-10-21T13:00:00.000000002Z"))
    clocks = result["receipt_observation_clocks"]
    assert clocks["four_hour_minus_minute_nanoseconds"] == 1
    assert clocks["minute_source_observed_at_utc"].endswith(".000000001Z")
    assert start_window(result)["all_ohlc_equal"] is True
    assert result["eligible_observations"] == []


@pytest.mark.parametrize("clock", [
    "2026-10-21T13:00:00,000000001Z", "2026-10-21T13:00:00,0000000001Z",
])
def test_comma_fraction_response_clocks_refuse_instead_of_silently_losing_precision(clock):
    views = list(reconciliation_views())
    view, receipt = views[0]
    views[0] = (replace(view, source_observed_at_utc=clock), receipt)
    with pytest.raises(TiingoViewRefusal, match="capture context"):
        reconcile(views)
