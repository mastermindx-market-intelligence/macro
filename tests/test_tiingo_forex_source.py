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


def view_for(data=None, *, frequency="1min", observed_at="2026-10-21T13:00:00Z", pair="USDJPY"):
    data = payload() if data is None else data
    raw = json.dumps(data).encode()
    rec = {"schema": "mastermind.tiingo.raw_receipt.v1", "source": "forex-bars",
           "symbol": pair.lower(), "vendor": "tiingo",
           "raw_sha256": hashlib.sha256(raw).hexdigest(),
           "observed_at_utc": observed_at,
           "request_path": archive_owner.request_path("forex-bars", pair.lower(), {"resampleFreq": frequency})}
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


# Executable policy checks remain a research contract, never an admitted bar.
from lib.dataos.tiingo_forex import (
    assess_forex_source_candidate, CANDIDATE_POLICY_VERSION, CANDIDATE_PAIRS,
    MAX_CANDIDATE_NATIVE_VINTAGES,
)


def candidate_assessment(views=None, **kwargs):
    views = views or reconciliation_views(
        minute_clock="2026-10-19T04:01:00Z", native_clock="2026-10-19T04:02:00Z")
    (minute, minute_id), (native, native_id) = views
    options = dict(expected_pair="USDJPY", minute_receipt_id=minute_id,
                   four_hour_receipt_id=native_id, policy_version=CANDIDATE_POLICY_VERSION,
                   verified_at_utc="2026-10-19T04:03:00Z",
                   assessed_at_utc="2026-10-19T04:04:00Z")
    options.update(kwargs)
    return assess_forex_source_candidate(minute, native, **options)


def test_candidate_checks_can_pass_without_promoting_any_authority(monkeypatch):
    views = reconciliation_views(
        minute_clock="2026-10-19T04:01:00.000000001Z",
        native_clock="2026-10-19T04:02:00.000000002Z")
    before = copy.deepcopy(views)
    monkeypatch.setattr("lib.dataos.tiingo_forex.read_research_view",
                        lambda *a, **k: pytest.fail("pure assessment performed I/O"))
    result = candidate_assessment(views)
    assert views == before
    assert result["windows"][0]["candidate_checks_satisfied"] is True
    assert result["windows"][0]["assessment_state"] == "checks_satisfied_policy_unadopted"
    assert result["policy_state"] == "CANDIDATE_NOT_ADOPTED"
    assert result["eligible_observations"] == []
    assert result["owner_decisions_required"]
    assert result["requested_pair_inventory"] == list(CANDIDATE_PAIRS)
    for flag in ("monitoring_admitted", "dataos_identity_admitted",
                 "pit_backtest_eligible", "redistribution_admitted"):
        assert result[flag] is False
    projection = result["windows"][0]["candidate_projection"]
    assert projection["quote_units_per_base_unit"] == "JPY per USD"
    assert not {"status", "feed", "revision", "observation_id", "available_at"} & projection.keys()
    assert result["clocks"]["original_response_clocks"]["four_hour_source_observed_at_utc"].endswith("000000002Z")
    assert result["comparison_semantics"]["raw_arbitrary_precision_equality_proven"] is False
    assert result["product_use_approval"]["state"] == "COMPLETE"
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("clock", ["2026-10-19T08:00:00Z", "2026-10-19T09:00:00Z"])
def test_candidate_expiry_cannot_be_extended_by_late_readback(clock):
    result = candidate_assessment(verified_at_utc=clock, assessed_at_utc=clock)
    window = result["windows"][0]
    assert not window["candidate_checks_satisfied"]
    assert window["checks"]["verification_before_candidate_expiry"] is False
    assert window["candidate_projection"]["candidate_expires_at_utc"] == "2026-10-19T08:00:00+00:00"
    assert result["clocks"]["reread_extends_freshness"] is False


@pytest.mark.parametrize("clock,passes", [
    ("2026-10-19T07:59:59.999999999Z", True),
    ("2026-10-19T08:00:00.000000000Z", False),
])
def test_candidate_freshness_is_exclusive_at_exact_nanosecond_boundary(clock, passes):
    window = candidate_assessment(assessed_at_utc=clock)["windows"][0]
    assert window["candidate_checks_satisfied"] is passes


@pytest.mark.parametrize("field", ["verified_at_utc", "assessed_at_utc"])
@pytest.mark.parametrize("value", [
    "2026-10-19T04:04:00", "2026-10-19T04:04:00,000000001Z",
    "2026-10-19T04:04:00.0000000001Z", None,
])
def test_candidate_refuses_ambiguous_or_truncated_explicit_clocks(field, value):
    with pytest.raises(TiingoViewRefusal):
        candidate_assessment(**{field: value})


@pytest.mark.parametrize("options,exception", [
    ({"assessed_at_utc": "2026-10-19T04:02:59Z"}, TiingoViewRefusal),
    ({"verified_at_utc": "2026-10-19T04:01:59Z"}, TiingoViewRefusal),
    ({"policy_version": "admitted"}, TiingoViewRefusal),
    ({"expected_pair": "GBPUSD"}, archive_owner.TiingoArchiveError),
])
def test_candidate_refuses_clock_order_policy_and_wrong_identity(options, exception):
    with pytest.raises(exception):
        candidate_assessment(**options)


def test_matching_open_window_fails_closure_even_when_ohlc_matches():
    views = reconciliation_views(minute_fixture(170),
        minute_clock="2026-10-19T02:49:03Z", native_clock="2026-10-19T02:49:05Z")
    window = candidate_assessment(views)["windows"][0]
    assert window["checks"]["normalized_ohlc_agreement"] is True
    assert window["checks"]["dense_minute_grid"] is False
    assert window["checks"]["both_responses_observed_after_interval_end"] is False
    assert not window["candidate_checks_satisfied"]


@pytest.mark.parametrize("defect", ["gap", "duplicate", "invalid", "off_grid"])
def test_candidate_incomplete_or_ambiguous_grid_never_passes(defect):
    minutes = minute_fixture()
    if defect == "gap":
        minutes.pop(50)
    elif defect == "duplicate":
        minutes.append(dict(minutes[50]))
    elif defect == "invalid":
        minutes[50]["close"] = None
    else:
        minutes[50]["date"] = "2026-10-19T00:50:00.000000001Z"
    views = reconciliation_views(minutes, native_fixture(minute_fixture()),
        minute_clock="2026-10-19T04:01:00Z", native_clock="2026-10-19T04:02:00Z")
    assert not candidate_assessment(views)["windows"][0]["candidate_checks_satisfied"]


def test_candidate_slot_positions_do_not_compress_absent_intervals():
    first, third = minute_fixture(), minute_fixture(start=480)
    native = native_fixture(first) + native_fixture(third, "2026-10-19T08:00:00Z")
    views = reconciliation_views(first + third, native,
        minute_clock="2026-10-19T12:01:00Z", native_clock="2026-10-19T12:02:00Z")
    result = candidate_assessment(views, verified_at_utc="2026-10-19T12:03:00Z",
                                 assessed_at_utc="2026-10-19T12:04:00Z")
    a, b = result["windows"]
    assert b["candidate_projection"]["utc_slot_index"] - a["candidate_projection"]["utc_slot_index"] == 2
    assert not a["candidate_checks_satisfied"]
    assert b["candidate_checks_satisfied"]


def test_candidate_native_inventory_is_idempotent_order_independent_and_conflict_withholding():
    views = reconciliation_views(
        minute_clock="2026-10-19T04:01:00Z", native_clock="2026-10-19T04:02:00Z")
    native = native_fixture(minute_fixture())
    native[0]["high"] += 1
    conflict = view_for(native, frequency="4hour", observed_at="2026-10-19T04:00:01Z")
    same = views[1]
    assert candidate_assessment(views, known_native_vintages=(same, same)) == candidate_assessment(views)
    a = candidate_assessment(views, known_native_vintages=(same, conflict))
    b = candidate_assessment(views, known_native_vintages=(conflict, same))
    assert a == b
    assert a["windows"][0]["native_vintage_check"]["conflicting_closed_receipt_ids"] == [conflict[1]]
    assert not a["windows"][0]["candidate_checks_satisfied"]
    assert a["eligible_observations"] == []


def test_open_native_change_is_disclosed_without_calling_it_a_post_close_correction():
    native = native_fixture(minute_fixture())
    native[0]["high"] += 1
    old_open = view_for(native, frequency="4hour", observed_at="2026-10-19T02:49:05Z")
    result = candidate_assessment(known_native_vintages=(old_open,))
    window = result["windows"][0]
    assert window["candidate_checks_satisfied"]
    assert window["native_vintage_check"]["open_receipt_ids_not_compared_as_corrections"] == [old_open[1]]
    assert window["native_vintage_check"]["all_possible_corrections_examined"] is False
    assert window["native_vintage_check"]["minute_vintage_inventory_examined"] is False
    assert result["comparison_semantics"]["vendor_immutability_proven"] is False


@pytest.mark.parametrize("defect", ["duplicate", "unplaced", "off_grid", "invalid_price"])
def test_unusable_closed_native_vintage_cannot_disappear_from_assessment(defect):
    native = native_fixture(minute_fixture())
    if defect == "duplicate":
        native.append(dict(native[0]))
    elif defect == "off_grid":
        native[0]["date"] = "2026-10-19T00:01:00Z"
    elif defect == "invalid_price":
        native[0]["close"] = None
    extra = view_for(native, frequency="4hour", observed_at="2026-10-19T04:00:01Z")
    if defect == "unplaced":
        # The reader already rejects malformed raw timestamps. Exercise the
        # pure function's defensive boundary with an explicitly corrupted view.
        extra[0].rows[0]["bar_at_vendor"] = "unknown"
    window = candidate_assessment(known_native_vintages=(extra,))["windows"][0]
    assert not window["candidate_checks_satisfied"]
    assert extra[1] in window["native_vintage_check"]["invalid_closed_receipt_ids"]


def test_candidate_inventory_caps_context_and_future_clocks_refuse():
    extra = view_for(native_fixture(minute_fixture()), frequency="4hour",
                     observed_at="2026-10-19T04:05:00Z")
    with pytest.raises(TiingoViewRefusal):
        candidate_assessment(known_native_vintages=(extra,))
    extra = view_for(native_fixture(minute_fixture()), frequency="4hour",
                     observed_at="2026-10-19T04:00:01Z")
    with pytest.raises(TiingoViewRefusal):
        candidate_assessment(known_native_vintages=(extra,) * (MAX_CANDIDATE_NATIVE_VINTAGES + 1))
    with pytest.raises(TiingoViewRefusal):
        candidate_assessment(known_native_vintages=(view_for(),))
    with pytest.raises(TiingoViewRefusal):
        candidate_assessment(known_native_vintages=((extra[0], "wrong-receipt"),))


@pytest.mark.parametrize("pair", CANDIDATE_PAIRS)
def test_candidate_empty_input_remains_empty_without_global_pair_claim(pair):
    views = (view_for([], pair=pair, observed_at="2026-10-19T04:01:00Z"),
             view_for([], pair=pair, frequency="4hour", observed_at="2026-10-19T04:02:00Z"))
    result = candidate_assessment(views, expected_pair=pair)
    assert result["source_state"] == "empty_native_view"
    assert result["windows"] == []
    assert result["eligible_observations"] == []
    assert {"USDBRL", "USDCNH"} <= set(result["requested_pair_inventory"])
    assert result["comparison_semantics"]["global_inventory_completeness_proven"] is False



from lib.dataos.tiingo_forex import (
    assess_forex_source_batch_candidate, BATCH_CANDIDATE_POLICY_VERSION,
    BATCH_INVENTORY_SCHEMA, MAX_BATCH_MINUTE_VINTAGES,
)


def batch_views(count=3):
    minutes = minute_fixture(240 * count)
    native = []
    for index in range(count):
        start = datetime(2026, 10, 19, tzinfo=timezone.utc) + timedelta(hours=4 * index)
        native.extend(native_fixture(minutes[240 * index:240 * (index + 1)], label=start.isoformat()))
    end = datetime(2026, 10, 19, tzinfo=timezone.utc) + timedelta(hours=4 * count)
    return (
        view_for(minutes, observed_at=(end + timedelta(minutes=1)).isoformat()),
        view_for(native, frequency="4hour", observed_at=(end + timedelta(minutes=2)).isoformat()),
    ), end


def batch_assessment(views=None, *, count=3, extra_minutes=(), extra_native=(), **kwargs):
    if views is None:
        views, end = batch_views(count)
    else:
        end = datetime(2026, 10, 19, tzinfo=timezone.utc) + timedelta(hours=4 * count)
    options = {
        "expected_pair": "USDJPY", "consecutive": count,
        "policy_version": BATCH_CANDIDATE_POLICY_VERSION,
        "verified_at_utc": (end + timedelta(minutes=3)).isoformat(),
        "assessed_at_utc": (end + timedelta(minutes=4)).isoformat(),
    }
    options.update(kwargs)
    return assess_forex_source_batch_candidate(
        (views[0],) + tuple(extra_minutes), (views[1],) + tuple(extra_native), **options)


def batch_inventory(views, end, **changes):
    minute, native = views
    ids = [minute[1], native[1]]
    result = {
        "schema": BATCH_INVENTORY_SCHEMA,
        "selected_receipt_ids": {"1min": [minute[1]], "4hour": [native[1]]},
        "scans": [
            {"started_at_utc": (end + timedelta(minutes=2, seconds=10)).isoformat(),
             "completed_at_utc": (end + timedelta(minutes=2, seconds=20)).isoformat(),
             "receipt_ids": ids},
            {"started_at_utc": (end + timedelta(minutes=2, seconds=30)).isoformat(),
             "completed_at_utc": (end + timedelta(minutes=2, seconds=40)).isoformat(),
             "receipt_ids": list(reversed(ids))},
        ],
    }
    result.update(changes)
    return result


@pytest.mark.parametrize("count", [1, 2, 3, 10])
def test_batch_older_supporting_slots_keep_expired_individual_verdicts(count, monkeypatch):
    views, end = batch_views(count)
    before = copy.deepcopy(views)
    monkeypatch.setattr("lib.dataos.tiingo_forex.read_research_view",
                        lambda *a, **k: pytest.fail("pure batch performed I/O"))
    out = batch_assessment(views, count=count)
    assert views == before
    assert out["batch_checks_satisfied"] is True
    assert len(out["slots"]) == count
    for slot in out["slots"][:-1]:
        assert slot["role"] == "supporting"
        assert slot["supporting_checks_satisfied"] is True
        assert slot["candidate_assessment"]["candidate_checks_satisfied"] is False
        assert slot["candidate_assessment"]["checks"]["verification_before_candidate_expiry"] is False
        assert slot["latest_freshness_required"] is False
        assert slot["latest_freshness_satisfied"] is None
    assert out["slots"][-1]["role"] == "latest"
    assert out["slots"][-1]["latest_freshness_satisfied"] is True
    assert out["required_interval_ends_utc"][-1] == end.isoformat()
    for slot in out["slots"]:
        projection = slot["candidate_projection"]
        assert projection["candidate_available_at_utc"] == (end + timedelta(minutes=3)).isoformat()
        assert not {"status", "feed", "revision", "observation_id", "available_at"} & projection.keys()
    assert out["policy_state"] == "CANDIDATE_NOT_ADOPTED"
    assert out["eligible_observations"] == []
    assert out["product_use_approval"]["state"] == "COMPLETE"
    for flag in ("monitoring_admitted", "dataos_identity_admitted", "pit_backtest_eligible", "redistribution_admitted"):
        assert out[flag] is False
    assert out["inventory_evidence"]["inventory_selection_consistent"] is None
    assert out["inventory_evidence"]["atomic_census_proven"] is False
    json.dumps(out, allow_nan=False)


@pytest.mark.parametrize("count", [0, 11, True, 1.0, "2", None])
def test_batch_refuses_outside_incumbent_consecutive_rule_bound(count):
    with pytest.raises(TiingoViewRefusal):
        batch_assessment(consecutive=count)


def test_batch_charges_reference_and_row_budgets_before_deduplication(monkeypatch):
    views, end = batch_views(1)
    with pytest.raises(TiingoViewRefusal, match="before deduplication"):
        batch_assessment(views, count=1, extra_minutes=(views[0],) * MAX_BATCH_MINUTE_VINTAGES)
    monkeypatch.setattr("lib.dataos.tiingo_forex.MAX_BATCH_INPUT_ROWS", 400)
    with pytest.raises(TiingoViewRefusal, match="row-reference budget"):
        batch_assessment(views, count=1, extra_minutes=(views[0],))


def test_batch_duplicate_full_identity_is_reported_without_changing_slot_results():
    views, end = batch_views()
    original = batch_assessment(views)
    duplicate = batch_assessment(views, extra_minutes=(views[0],), extra_native=(views[1],))
    assert duplicate["slots"] == original["slots"]
    assert duplicate["checks"] == original["checks"]
    assert duplicate["input_inventory"] == original["input_inventory"]
    assert duplicate["duplicate_supplied_references"] == {views[0][1]: 1, views[1][1]: 1}


@pytest.mark.parametrize("difference", ["extra_field", "row_order", "number_type", "source_request"])
def test_batch_one_identity_cannot_hide_different_full_content(difference):
    views, end = batch_views(1)
    view, ident = views[0]
    original = copy.deepcopy(view)
    rows = copy.deepcopy(view.rows)
    if difference == "extra_field":
        rows[0]["unrelated_source_metadata"] = "changed"
        other = replace(view, rows=rows)
    elif difference == "row_order":
        other = replace(view, rows=tuple(reversed(rows)))
    elif difference == "number_type":
        first = copy.deepcopy(view.rows)
        first[0]["extra_numeric"] = 1
        rows[0]["extra_numeric"] = 1.0
        original, other = replace(view, rows=first), replace(view, rows=rows)
    else:
        other = replace(view, source_request_path=view.source_request_path + "&startDate=2026-10-18")
    with pytest.raises(TiingoViewRefusal):
        batch_assessment(((original, ident), views[1]), count=1, extra_minutes=((other, ident),))


def test_batch_collection_order_does_not_select_a_winner():
    views, end = batch_views(1)
    same = view_for(minute_fixture(), observed_at="2026-10-19T04:01:30Z")
    conflict_data = [dict(minute_fixture()[50]), dict(minute_fixture()[51])]
    conflict_data[0]["close"] += 0.001
    conflict_data[1]["close"] -= 0.001
    conflict = view_for(conflict_data, observed_at="2026-10-19T04:02:30Z")
    kwargs = dict(expected_pair="USDJPY", consecutive=1, policy_version=BATCH_CANDIDATE_POLICY_VERSION,
                  verified_at_utc="2026-10-19T04:03:00Z", assessed_at_utc="2026-10-19T04:04:00Z")
    a = assess_forex_source_batch_candidate((views[0], same, conflict), (views[1],), **kwargs)
    b = assess_forex_source_batch_candidate((conflict, views[0], same), (views[1],), **kwargs)
    assert a == b
    assert not a["batch_checks_satisfied"]
    assert a["slots"][0]["minute_vintage_check"]["conflicting_closed_receipt_ids"] == [conflict[1]]


def test_batch_closed_partial_cancelling_minute_changes_cannot_hide_behind_aggregate_ohlc():
    views, end = batch_views(1)
    original = minute_fixture()
    changed = copy.deepcopy(original)
    changed[50]["close"] += 0.001
    changed[51]["close"] -= 0.001
    assert native_fixture(changed) == native_fixture(original)
    conflict = view_for(changed[50:52], observed_at="2026-10-19T04:02:30Z")
    out = batch_assessment(views, count=1, extra_minutes=(conflict,))
    slot = out["slots"][0]
    assert slot["candidate_assessment"]["checks"]["normalized_ohlc_agreement"] is True
    assert conflict[1] in slot["minute_vintage_check"]["partial_closed_receipt_ids"]
    assert conflict[1] in slot["minute_vintage_check"]["conflicting_closed_receipt_ids"]
    assert not out["batch_checks_satisfied"]


def test_batch_matching_partial_receipt_corroborates_but_does_not_fill_a_grid():
    views, end = batch_views(1)
    first = view_for(minute_fixture()[:120], observed_at="2026-10-19T04:01:30Z")
    second = view_for(minute_fixture()[120:], observed_at="2026-10-19T04:02:30Z")
    out = batch_assessment(views, count=1, extra_minutes=(first, second))
    assert out["batch_checks_satisfied"]
    check = out["slots"][0]["minute_vintage_check"]
    assert check["complete_reference_receipt_ids"] == [views[0][1]]
    assert set(check["partial_closed_receipt_ids"]) == {first[1], second[1]}
    no_complete = batch_assessment((first, views[1]), count=1, extra_minutes=(second,))
    assert not no_complete["batch_checks_satisfied"]
    assert no_complete["slots"][0]["minute_vintage_check"]["complete_reference_receipt_ids"] == []


def test_batch_open_vintage_difference_is_not_a_closed_correction():
    views, end = batch_views(1)
    partial = minute_fixture()[50:52]
    partial[0]["close"] += 0.001
    opened = view_for(partial, observed_at="2026-10-19T03:59:59Z")
    out = batch_assessment(views, count=1, extra_minutes=(opened,))
    assert out["batch_checks_satisfied"]
    check = out["slots"][0]["minute_vintage_check"]
    assert check["open_receipt_ids_not_compared_as_corrections"] == [opened[1]]
    assert check["conflicting_closed_receipt_ids"] == []


@pytest.mark.parametrize("defect", ["duplicate_offset", "subminute", "unplaced", "bad_ohlc"])
def test_batch_closed_minute_ambiguity_withholds_even_with_a_good_reference(defect):
    views, end = batch_views(1)
    row = dict(minute_fixture()[50])
    data = [row]
    if defect == "duplicate_offset":
        data.append(dict(row, date="2026-10-19T01:50:00+01:00"))
    elif defect == "subminute":
        row["date"] = "2026-10-19T00:50:00.000000001Z"
    elif defect == "unplaced":
        pass  # The real reader rejects this earlier; exercise the pure boundary below.
    else:
        row["close"] = None
    extra = view_for(data, observed_at="2026-10-19T04:02:30Z")
    if defect == "unplaced":
        changed_rows = copy.deepcopy(extra[0].rows)
        changed_rows[0]["bar_at_vendor"] = "unplaceable"
        extra = (replace(extra[0], rows=changed_rows), extra[1])
    out = batch_assessment(views, count=1, extra_minutes=(extra,))
    assert not out["batch_checks_satisfied"]
    assert extra[1] in out["slots"][0]["minute_vintage_check"]["invalid_closed_receipt_ids"]


def test_batch_placeable_value_defect_outside_target_slot_does_not_poison_it():
    views, end = batch_views(1)
    outside = dict(minute_fixture()[0], date="2026-10-18T23:59:00Z", close=None)
    extra = view_for([outside], observed_at="2026-10-19T04:02:30Z")
    out = batch_assessment(views, count=1, extra_minutes=(extra,))
    assert out["batch_checks_satisfied"]
    assert out["slots"][0]["minute_vintage_check"]["invalid_closed_receipt_ids"] == []


def test_batch_checks_lineage_outside_target_slots_before_filtering():
    views, end = batch_views(1)
    row = dict(views[0][0].rows[0], bar_at_vendor="2026-10-18T23:59:00Z", ticker_vendor="eurusd")
    bad = replace(views[0][0], rows=views[0][0].rows + (row,))
    with pytest.raises(TiingoViewRefusal, match="lineage"):
        batch_assessment(((bad, views[0][1]), views[1]), count=1)


def test_batch_all_supplied_closed_native_vintages_remain_required():
    views, end = batch_views(1)
    native = native_fixture(minute_fixture())
    native[0]["high"] += 1
    conflict = view_for(native, frequency="4hour", observed_at="2026-10-19T04:02:30Z")
    out = batch_assessment(views, count=1, extra_native=(conflict,))
    assert not out["batch_checks_satisfied"]
    check = out["slots"][0]["candidate_assessment"]["native_vintage_check"]
    assert check["conflicting_closed_receipt_ids"]


def test_batch_assessment_boundary_changes_anchor_without_an_older_window_fallback():
    views, end = batch_views(1)
    earlier = batch_assessment(views, count=1, verified_at_utc="2026-10-19T07:59:59.999999999Z",
                               assessed_at_utc="2026-10-19T07:59:59.999999999Z")
    assert earlier["batch_checks_satisfied"]
    crossed = batch_assessment(views, count=1, verified_at_utc="2026-10-19T07:59:59.999999999Z",
                               assessed_at_utc="2026-10-19T08:00:00Z")
    assert crossed["required_interval_ends_utc"] == ["2026-10-19T08:00:00+00:00"]
    assert not crossed["batch_checks_satisfied"]


def test_batch_late_readback_of_open_capture_cannot_create_the_current_close():
    minutes = minute_fixture(281)
    native = native_fixture(minutes[:240]) + native_fixture(minutes[240:], label="2026-10-19T04:00:00Z")
    views = (view_for(minutes, observed_at="2026-10-19T04:41:00Z"),
             view_for(native, frequency="4hour", observed_at="2026-10-19T04:41:02Z"))
    out = batch_assessment(views, count=2, verified_at_utc="2026-10-19T09:14:00Z",
                           assessed_at_utc="2026-10-19T09:14:01Z")
    assert out["slots"][0]["supporting_checks_satisfied"]
    assert not out["slots"][0]["candidate_assessment"]["candidate_checks_satisfied"]
    assert not out["slots"][-1]["slot_checks_satisfied"]
    assert not out["batch_checks_satisfied"]


def test_batch_equal_inventory_scans_are_only_unattested_declarations():
    views, end = batch_views(1)
    evidence = batch_inventory(views, end, owner_quiescence_reference="existing owner receipt")
    out = batch_assessment(views, count=1, inventory_evidence=evidence)
    assert out["batch_checks_satisfied"]
    inv = out["inventory_evidence"]
    assert inv["inventory_selection_consistent"] is True
    assert inv["two_scan_identity_sets_equal"] is True
    assert inv["atomic_census_proven"] is False
    assert inv["owner_quiescence_independently_verified"] is False
    assert out["eligible_observations"] == []


@pytest.mark.parametrize("defect", ["omitted_view", "extra_view", "duplicate_declaration", "future_scan", "boolean_authority"])
def test_batch_declared_inventory_correspondence_and_clocks_cannot_be_faked(defect):
    views, end = batch_views(1)
    evidence = batch_inventory(views, end)
    extra = ()
    if defect == "omitted_view":
        evidence["selected_receipt_ids"]["1min"].append("a" * 64)
    elif defect == "extra_view":
        extra = (view_for(minute_fixture()[:2], observed_at="2026-10-19T04:01:30Z"),)
    elif defect == "duplicate_declaration":
        evidence["scans"][0]["receipt_ids"].append(views[0][1])
    elif defect == "future_scan":
        evidence["scans"][1]["completed_at_utc"] = "2026-10-19T04:03:01Z"
    else:
        evidence["owner_quiescence_reference"] = True
    with pytest.raises(TiingoViewRefusal):
        batch_assessment(views, count=1, extra_minutes=extra, inventory_evidence=evidence)


def test_batch_unequal_scan_identity_sets_withhold_without_retry_or_truncation():
    views, end = batch_views(1)
    evidence = batch_inventory(views, end)
    evidence["scans"][1]["receipt_ids"].append("a" * 64)
    out = batch_assessment(views, count=1, inventory_evidence=evidence)
    assert out["slots"][0]["slot_checks_satisfied"]
    assert out["inventory_evidence"]["two_scan_identity_sets_equal"] is False
    assert not out["batch_checks_satisfied"]


@pytest.mark.parametrize("field,value", [
    ("verified_at_utc", "2026-10-19T12:00:00Z"),
    ("verified_at_utc", "2026-10-19T12:03:00"),
    ("assessed_at_utc", "2026-10-19T12:02:59Z"),
    ("assessed_at_utc", "2026-10-19T12:04:00.0000000001Z"),
    ("policy_version", "admitted"),
])
def test_batch_refuses_ambiguous_clocks_future_captures_or_unknown_policy(field, value):
    with pytest.raises(TiingoViewRefusal):
        batch_assessment(**{field: value})
