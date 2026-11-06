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



@pytest.mark.parametrize("family", ["single", "batch"])
@pytest.mark.parametrize("field", ["verified_at_utc", "assessed_at_utc"])
@pytest.mark.parametrize("clock", [
    "2026-10-19T040400,9Z",
    "20261019t040400,5z",
    "2026-10-19T040400.0000000001Z",
])
def test_candidate_families_refuse_lossy_compact_caller_clocks(family, field, clock):
    assessor = candidate_assessment if family == "single" else (
        lambda **kwargs: batch_assessment(count=1, **kwargs))
    with pytest.raises(TiingoViewRefusal):
        assessor(**{field: clock})


@pytest.mark.parametrize("family", ["single", "batch"])
@pytest.mark.parametrize("clock", [
    "2026-10-19T040400.{fraction}Z",
    "20261019t040400.{fraction}z",
    "2026-10-19 05:04:00.{fraction}+0100",
])
def test_candidate_families_preserve_compact_caller_nanosecond_order(family, clock):
    assessor = candidate_assessment if family == "single" else (
        lambda **kwargs: batch_assessment(count=1, **kwargs))
    with pytest.raises(TiingoViewRefusal):
        assessor(
            verified_at_utc=clock.format(fraction="000000002"),
            assessed_at_utc=clock.format(fraction="000000001"),
        )


@pytest.mark.parametrize("family", ["single", "batch"])
@pytest.mark.parametrize("clock", [
    "2026-10-19T040400.{fraction}Z",
    "20261019t040400.{fraction}z",
    "2026-10-19 05:04:00.{fraction}+0100",
])
def test_candidate_families_accept_lossless_ordered_iso_caller_clocks(family, clock):
    assessor = candidate_assessment if family == "single" else (
        lambda **kwargs: batch_assessment(count=1, **kwargs))
    result = assessor(
        verified_at_utc=clock.format(fraction="000000001"),
        assessed_at_utc=clock.format(fraction="000000002"),
    )
    satisfied = (result["windows"][0]["candidate_checks_satisfied"]
                 if family == "single" else result["batch_checks_satisfied"])
    assert satisfied is True
    assert result["policy_state"] == "CANDIDATE_NOT_ADOPTED"
    assert result["eligible_observations"] == []
    assert result["monitoring_admitted"] is False



@pytest.mark.parametrize("family", ["single", "batch"])
@pytest.mark.parametrize("field", ["verified_at_utc", "assessed_at_utc"])
@pytest.mark.parametrize("clock", [
    "2026-10-19T05:04:00.{fraction}+00:60",
    "20261019t030400.{fraction}-0060",
    "2026-10-19T06:43:00.{fraction}+01:99",
    "20261019t012500.{fraction}-0199",
    "2026-10-20T04:04:00.{fraction}+24:00",
    "20261018t040400.{fraction}-2400",
])
def test_candidate_families_refuse_invalid_offset_components(family, field, clock):
    assessor = candidate_assessment if family == "single" else (
        lambda **kwargs: batch_assessment(count=1, **kwargs))
    clocks = {
        "verified_at_utc": "2026-10-19T04:04:00.000000001Z",
        "assessed_at_utc": "2026-10-19T04:04:00.000000002Z",
    }
    clocks[field] = clock.format(
        fraction="000000001" if field == "verified_at_utc" else "000000002")
    with pytest.raises(TiingoViewRefusal):
        assessor(**clocks)


@pytest.mark.parametrize("family", ["single", "batch"])
@pytest.mark.parametrize("clock", [
    "2026-10-20T04:03:00.{fraction}+23:59",
    "20261018t040500.{fraction}-2359",
])
def test_candidate_families_accept_valid_offset_boundaries(family, clock):
    assessor = candidate_assessment if family == "single" else (
        lambda **kwargs: batch_assessment(count=1, **kwargs))
    result = assessor(
        verified_at_utc=clock.format(fraction="000000001"),
        assessed_at_utc=clock.format(fraction="000000002"),
    )
    satisfied = (result["windows"][0]["candidate_checks_satisfied"]
                 if family == "single" else result["batch_checks_satisfied"])
    assert satisfied is True
    assert result["policy_state"] == "CANDIDATE_NOT_ADOPTED"
    assert result["eligible_observations"] == []
    assert result["monitoring_admitted"] is False


import gzip
import io
import json
import os
from pathlib import Path

import pytest

import collectors.tiingo_archive as archive_module
from lib.dataos.tiingo_reader import read_research_view
from scripts.tiingo_materialize import (
    BoundedTiingoRead,
    materialize_one,
)


@pytest.fixture
def bounded_root(tmp_path, monkeypatch):
    # A canonical fixture root; separate tests supply an actual symlink spelling.
    mount = tmp_path.resolve()
    monkeypatch.setattr(archive_module, "EXTERNAL_MOUNT", mount)
    root = mount / "archive"
    root.mkdir()
    return root


def test_held_directory_distinguishes_absence_and_keeps_all_names(bounded_root):
    folder = bounded_root / "receipts"
    folder.mkdir()
    for name in ("one.json", ".incoming-x", "not-json"):
        (folder / name).write_bytes(b"{}")
    with BoundedTiingoRead(bounded_root, check_mount=False) as context:
        with context.directory(("receipts",)) as fd:
            with os.scandir(fd) as entries:
                assert {entry.name for entry in entries} == {
                    "one.json", ".incoming-x", "not-json"
                }
        with pytest.raises(FileNotFoundError):
            with context.directory(("absent",)):
                pytest.fail("missing directory unexpectedly opened")
        context.verify_bindings()


@pytest.mark.parametrize("position", ["root", "ancestor", "leaf"])
def test_no_follow_refuses_even_valid_symlink_target(bounded_root, position):
    outside = bounded_root.parent / "outside"
    outside.mkdir()
    (outside / "item.json").write_bytes(b'{"value":1}')
    if position == "root":
        alias = bounded_root.parent / "root-alias"
        alias.symlink_to(bounded_root, target_is_directory=True)
        with pytest.raises(OSError):
            BoundedTiingoRead(alias, check_mount=False)
        return
    if position == "ancestor":
        (bounded_root / "alias").symlink_to(outside, target_is_directory=True)
        selected = ("alias", "item.json")
    else:
        (bounded_root / "alias.json").symlink_to(outside / "item.json")
        selected = ("alias.json",)
    with BoundedTiingoRead(bounded_root, check_mount=False) as context:
        with pytest.raises(OSError) as caught:
            context.read_metadata(selected)
        assert not isinstance(caught.value, FileNotFoundError)
        assert context.used["metadata"] == 0


def test_fifo_is_refused_without_a_blocking_read(bounded_root):
    os.mkfifo(bounded_root / "pipe.json")
    with BoundedTiingoRead(bounded_root, check_mount=False) as context:
        with pytest.raises(archive_module.TiingoArchiveError, match="regular file"):
            context.read_metadata(("pipe.json",))
        assert context.used["metadata"] == 0


def test_metadata_budget_counts_actual_repeated_reads(bounded_root):
    (bounded_root / "one.json").write_bytes(b"{}")
    with BoundedTiingoRead(bounded_root, check_mount=False, metadata_limit=4) as context:
        assert context.read_metadata(("one.json",)) == {}
        assert context.read_metadata(("one.json",)) == {}
        assert context.used["metadata"] == 4
        with pytest.raises(archive_module.TiingoArchiveError, match="allowance"):
            context.read_metadata(("one.json",))


@pytest.mark.parametrize("body", [b'{"same":1,"same":2}', b'{"x":NaN}', b"[]"])
def test_ambiguous_or_nonobject_metadata_is_not_a_receipt(bounded_root, body):
    (bounded_root / "bad.json").write_bytes(body)
    with BoundedTiingoRead(bounded_root, check_mount=False) as context:
        with pytest.raises(archive_module.TiingoArchiveError):
            context.read_metadata(("bad.json",))


def test_absent_optional_file_cannot_appear_unnoticed(bounded_root):
    with BoundedTiingoRead(bounded_root, check_mount=False) as context:
        assert context.read_metadata(("later.json",), missing_ok=True) is None
        (bounded_root / "later.json").write_bytes(b"{}")
        with pytest.raises(archive_module.TiingoArchiveError, match="binding changed"):
            context.verify_bindings()


def test_identical_bytes_at_replacement_inode_are_disclosed(bounded_root):
    selected = bounded_root / "one.json"
    selected.write_bytes(b"{}")
    with BoundedTiingoRead(bounded_root, check_mount=False) as context:
        assert context.read_metadata(("one.json",)) == {}
        replacement = bounded_root / "replacement"
        replacement.write_bytes(b"{}")
        os.replace(replacement, selected)
        with pytest.raises(archive_module.TiingoArchiveError, match="binding changed"):
            context.verify_bindings()


def test_in_place_mutation_during_read_is_refused(bounded_root, monkeypatch):
    selected = bounded_root / "one.json"
    selected.write_bytes(b'{"x":0}')
    with BoundedTiingoRead(bounded_root, check_mount=False) as context:
        original = context._bounded_stream

        def mutate_after_read(fp, kind, limit):
            result = original(fp, kind, limit)
            selected.write_bytes(b'{"x":1000}')
            return result

        monkeypatch.setattr(context, "_bounded_stream", mutate_after_read)
        with pytest.raises(archive_module.TiingoArchiveError, match="while being read"):
            context.read_metadata(("one.json",))


def test_raw_budget_is_aggregate_across_distinct_files(bounded_root):
    for name in ("one.gz", "two.gz"):
        (bounded_root / name).write_bytes(gzip.compress(b"1234", mtime=0))
    with BoundedTiingoRead(bounded_root, check_mount=False, raw_limit=7) as context:
        assert context.read_raw_gzip(("one.gz",), expected_raw_bytes=4) == b"1234"
        with pytest.raises(archive_module.TiingoArchiveError, match="remaining allowance"):
            context.read_raw_gzip(("two.gz",), expected_raw_bytes=4)
        assert context.used["raw"] == 4


def test_claimed_small_raw_length_cannot_hide_expansion(bounded_root, monkeypatch):
    (bounded_root / "raw.gz").write_bytes(gzip.compress(b"A" * 100_000, mtime=0))
    # Measure actual decoded data below GzipFile's buffering layer. Merely
    # checking the wrapper's returned-byte count would miss decoded read-ahead.
    decoded_lengths = []
    original = gzip._GzipReader.read

    def observe_decoder(self, size=-1):
        decoded = original(self, size)
        decoded_lengths.append(len(decoded))
        return decoded

    monkeypatch.setattr(gzip._GzipReader, "read", observe_decoder)
    with BoundedTiingoRead(bounded_root, check_mount=False, raw_limit=8) as context:
        with pytest.raises(archive_module.TiingoArchiveError, match="allowance"):
            context.read_raw_gzip(("raw.gz",), expected_raw_bytes=4)
        assert context.used["raw"] == 5  # four allowed bytes plus one refusal sentinel
        assert sum(decoded_lengths) == 5


def test_compressed_guard_precedes_decompression(bounded_root):
    body = gzip.compress(b"1234", mtime=0)
    (bounded_root / "raw.gz").write_bytes(body)
    with BoundedTiingoRead(
        bounded_root, check_mount=False, compressed_limit=len(body) - 1
    ) as context:
        with pytest.raises(archive_module.TiingoArchiveError, match="allowance"):
            context.read_raw_gzip(("raw.gz",), expected_raw_bytes=4)
        assert context.used["raw"] == 0


def test_encoded_normalized_budget_is_separate_and_aggregate(bounded_root):
    (bounded_root / "one.parquet").write_bytes(b"123")
    (bounded_root / "two.parquet").write_bytes(b"456")
    with BoundedTiingoRead(bounded_root, check_mount=False, normalized_limit=5) as context:
        assert context.read_normalized(("one.parquet",)) == b"123"
        with pytest.raises(archive_module.TiingoArchiveError, match="allowance"):
            context.read_normalized(("two.parquet",))
        assert context.used["normalized"] == 3
        assert context.used["raw"] == 0


@pytest.fixture
def materialized_view(bounded_root):
    archive = archive_module.Archive(bounded_root, check_mount=False, free_floor=0)
    saved = archive.store_response(
        "eod-bars", "AMD", archive_module.request_path("eod-bars", "AMD"),
        b'[{"date":"2019-01-03","close":22,"adjClose":18}]',
        received_at="2026-10-09T05:00:00+00:00",
    )
    receipt_path = next((bounded_root / "receipts").rglob("*.json"))
    receipt = json.loads(receipt_path.read_text())
    assert materialize_one(bounded_root, receipt, free_floor=0)["status"] == "WRITTEN"
    return bounded_root, saved, receipt_path, receipt


def test_optional_reader_preserves_the_legacy_exact_view(materialized_view):
    root, saved, receipt_path, _receipt = materialized_view
    legacy = read_research_view(
        "eod-bars", "2026-10-09", saved["raw_sha256"],
        root=root, check_mount=False,
    )
    with BoundedTiingoRead(root, check_mount=False) as context:
        strict = read_research_view(
            "eod-bars", "2026-10-09", saved["receipt_id"],
            root=root, check_mount=False, receipt_path=receipt_path,
            read_context=context,
        )
        context.verify_bindings()
        assert strict == legacy
        assert strict.authority == "RESEARCH_ONLY_VENDOR_SOURCE"
        assert strict.pit_backtest_eligible is False


def test_parquet_parser_consumes_verified_snapshot_and_later_change_withholds(
    materialized_view, monkeypatch
):
    import pyarrow.parquet as pq

    root, saved, receipt_path, _receipt = materialized_view
    target = next((root / "normalized").rglob("*.parquet"))
    original = pq.ParquetFile

    def replace_after_snapshot(source, *args, **kwargs):
        assert isinstance(source, io.BytesIO)
        target.write_bytes(b"not the verified parquet")
        return original(source, *args, **kwargs)

    monkeypatch.setattr(pq, "ParquetFile", replace_after_snapshot)
    with BoundedTiingoRead(root, check_mount=False) as context:
        result = read_research_view(
            "eod-bars", "2026-10-09", saved["receipt_id"],
            root=root, check_mount=False, receipt_path=receipt_path,
            read_context=context,
        )
        assert result.rows[0]["close_raw"] == 22
        with pytest.raises(archive_module.TiingoArchiveError, match="binding changed"):
            context.verify_bindings()

# Bounded archive census regressions use real temporary retained artifacts.
from pathlib import Path
import os
import lib.dataos.tiingo_forex as census_fx
import scripts.tiingo_materialize as census_materializer


_CENSUS_ASSESSED = "2026-10-21T08:04:00Z"
_CENSUS_ADMISSION_FLAGS = (
    "monitoring_admitted", "dataos_identity_admitted",
    "pit_backtest_eligible", "redistribution_admitted",
)


@pytest.fixture
def census_lake(tmp_path, monkeypatch):
    """Temporary retained evidence, with one explicit private assessment clock."""
    mount = tmp_path.resolve()
    monkeypatch.setattr(archive_owner, "EXTERNAL_MOUNT", mount)
    monkeypatch.setattr(census_fx, "_census_now_utc", lambda: _CENSUS_ASSESSED)
    lake = archive_owner.Archive(mount / "lake", check_mount=False, free_floor=0)

    def retain(rows, *, pair="USDJPY", frequency="1min",
               observed_at="2026-10-21T08:01:00Z", params=None, materialize=True):
        query = {"resampleFreq": frequency, **(params or {})}
        raw = json.dumps(rows, allow_nan=False).encode()
        saved = lake.store_response(
            "forex-bars", pair.lower(),
            archive_owner.request_path("forex-bars", pair.lower(), query),
            raw, received_at=observed_at,
        )
        day = archive_owner.capture_day(saved["observed_at_utc"])
        stem = Path(saved["path"]).name.removesuffix(".raw.gz")
        receipt_path = lake.root / "receipts" / "forex-bars" / day / (stem + ".json")
        receipt = json.loads(receipt_path.read_text())
        output = materialize_one(lake.root, receipt, free_floor=0) if materialize else None
        return {"saved": saved, "receipt": receipt, "receipt_path": receipt_path,
                "materialized": output, "raw": raw}

    return lake, retain


def _census_rows(count=240, *, start="2026-10-21T04:00:00Z", pair="USDJPY",
                 step_minutes=1, base=149.0):
    origin = datetime.fromisoformat(start.replace("Z", "+00:00"))
    return [{
        "ticker": pair.lower(),
        "date": (origin + timedelta(minutes=index * step_minutes)).isoformat(),
        "open": base + index / 1000,
        "high": base + .02 + index / 1000,
        "low": base - .02 + index / 1000,
        "close": base + .005 + index / 1000,
    } for index in range(count)]


def _census_native_rows(minutes):
    assert len(minutes) % 240 == 0
    result = []
    for offset in range(0, len(minutes), 240):
        block = minutes[offset:offset + 240]
        result.append({
            "ticker": block[0]["ticker"], "date": block[0]["date"],
            "open": block[0]["open"], "high": max(row["high"] for row in block),
            "low": min(row["low"] for row in block), "close": block[-1]["close"],
        })
    return result


def _census_seed_closed(fixture, *, pair="USDJPY"):
    _lake, retain = fixture
    minutes = _census_rows(pair=pair)
    minute = retain(minutes, pair=pair)
    native = retain(_census_native_rows(minutes), pair=pair, frequency="4hour",
                    observed_at="2026-10-21T08:02:00Z")
    return minutes, minute, native


def _census_run(lake, *, pair="USDJPY", count=1):
    return census_fx.read_forex_source_batch_candidate(
        expected_pair=pair, consecutive=count,
        policy_version=census_fx.BATCH_CANDIDATE_POLICY_VERSION,
        root=lake.root, check_mount=False,
    )


def _census_file_hashes(root):
    return {path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in root.rglob("*") if path.is_file() and not path.is_symlink()}


def _assert_census_no_admission(evidence):
    assert evidence["eligible_observations"] == []
    for flag in _CENSUS_ADMISSION_FLAGS:
        assert evidence[flag] is False
    for claim in ("atomic_census_proven", "global_inventory_completeness_proven",
                  "owner_quiescence_independently_verified", "historical_availability_proven"):
        assert evidence[claim] is False
    assert evidence["product_use_approval"]["state"] == "COMPLETE"
    assessment = evidence["assessment"]
    if assessment is not None:
        assert assessment["policy_state"] == "CANDIDATE_NOT_ADOPTED"
        assert assessment["eligible_observations"] == []
        for flag in _CENSUS_ADMISSION_FLAGS:
            assert assessment[flag] is False
        assert assessment["inventory_evidence"]["atomic_census_proven"] is False
    json.dumps(evidence, allow_nan=False)


def test_observed_census_reads_dense_retained_views_without_admitting_or_writing(census_lake):
    lake, _retain = census_lake
    _minutes, minute, native = _census_seed_closed(census_lake)
    before = _census_file_hashes(lake.root)

    evidence = _census_run(lake)

    assert evidence["state"] == "observed_census_complete_policy_unadopted"
    assert evidence["schema"] == census_fx.BATCH_CENSUS_SCHEMA
    assert evidence["capture_dates"] == ["2026-10-21"]
    assert evidence["fixed_latest_interval_end_utc"] == "2026-10-21T08:00:00+00:00"
    assert evidence["observed_scans_equal"] is True
    assert len(evidence["scans"]) == 2
    assert {scan["entry_count_before_filter"] for scan in evidence["scans"]} == {2}
    assert evidence["scans"][0]["snapshot_sha256"] == evidence["scans"][1]["snapshot_sha256"]
    assert {view["receipt_id"] for view in evidence["selected_views"]} == {
        minute["saved"]["receipt_id"], native["saved"]["receipt_id"],
    }
    assert all(view["state"] == "exact_view_verified" for view in evidence["selected_views"])
    assert evidence["selected_row_references"] == 241
    assert all(evidence["byte_reads"][kind] > 0
               for kind in ("metadata", "raw", "compressed", "normalized"))
    assert evidence["assessment"]["batch_checks_satisfied"] is True
    assert evidence["assessment"]["inventory_evidence"]["inventory_selection_consistent"] is True
    assert _census_file_hashes(lake.root) == before
    _assert_census_no_admission(evidence)


def test_observed_census_n10_scans_three_utc_capture_days_and_preserves_offset(census_lake):
    lake, retain = census_lake
    minutes = _census_rows(2400, start="2026-10-19T16:00:00Z")
    natives = _census_native_rows(minutes)
    retain(minutes)
    # Literal date is October 20; its actual UTC capture partition is October 19.
    first = retain(natives[:1], frequency="4hour", observed_at="2026-10-20T00:10:00+02:00")
    retain(natives[1:7], frequency="4hour", observed_at="2026-10-20T23:59:00Z")
    retain(natives[7:], frequency="4hour", observed_at="2026-10-21T08:02:00Z")

    evidence = _census_run(lake, count=10)

    assert evidence["capture_dates"] == ["2026-10-19", "2026-10-20", "2026-10-21"]
    assert evidence["assessment"]["batch_checks_satisfied"] is True
    assert len(evidence["assessment"]["slots"]) == 10
    assert evidence["selected_row_references"] == 2410
    assert [entry["state"] for entry in evidence["scans"][0]["directories"]] == ["observed"] * 3
    for scan in evidence["scans"]:
        item = next(item for item in scan["entries"]
                    if item["receipt_id"] == first["saved"]["receipt_id"])
        assert item["capture_day"] == "2026-10-19"
        assert "/2026-10-19/" in item["path"]
        assert item["source_observed_at_utc"] == "2026-10-20T00:10:00+02:00"
    for slot in evidence["assessment"]["slots"][:-1]:
        assert slot["role"] == "supporting"
        assert slot["candidate_assessment"]["candidate_checks_satisfied"] is False
        assert slot["supporting_checks_satisfied"] is True
    _assert_census_no_admission(evidence)


def test_observed_census_counts_257_other_pair_entries_before_metadata_or_filtering(census_lake, monkeypatch):
    lake, retain = census_lake
    for index in range(257):
        retain(_census_rows(1, pair="EURUSD", base=1.0 + index / 1000),
               pair="EURUSD", materialize=False)

    def forbidden(*_args, **_kwargs):
        pytest.fail("entry ceiling must be enforced before metadata or source-view reads")

    monkeypatch.setattr(census_materializer.BoundedTiingoRead, "read_metadata", forbidden)
    monkeypatch.setattr(census_fx, "read_research_view", forbidden)
    with pytest.raises(TiingoViewRefusal, match="entry cap") as caught:
        _census_run(lake)

    evidence = caught.value.census_evidence
    assert evidence["state"] == "refused"
    assert evidence["scans"][0]["entry_count_before_filter"] == 257
    assert evidence["scans"][0]["entries"] == []
    assert evidence["selected_views"] == []
    assert evidence["byte_reads"]["metadata"] == 0
    _assert_census_no_admission(evidence)


def test_observed_census_cannot_filter_away_malformed_other_pair_receipt(census_lake, monkeypatch):
    lake, retain = census_lake
    _census_seed_closed(census_lake)
    other = retain(_census_rows(1, pair="EURUSD"), pair="EURUSD")
    record = dict(other["receipt"])
    record["raw_bytes"] = "not-an-integer"
    record["receipt_id"] = archive_owner.receipt_identity(record)
    other["receipt_path"].write_text(json.dumps(record))
    monkeypatch.setattr(census_fx, "read_research_view",
                        lambda *_a, **_k: pytest.fail("malformed census reached view acquisition"))

    with pytest.raises(TiingoViewRefusal, match="metadata") as caught:
        _census_run(lake)

    evidence = caught.value.census_evidence
    assert evidence["scans"][0]["entry_count_before_filter"] == 3
    relative = other["receipt_path"].relative_to(lake.root).as_posix()
    assert any(item["path"] == relative and item["state"] == "unverified"
               for item in evidence["scans"][0]["entries"])
    assert evidence["selected_views"] == []
    _assert_census_no_admission(evidence)


@pytest.mark.parametrize("frequency", ["1min", "4hour"])
def test_observed_census_refuses_tenth_selected_reference_before_any_view(census_lake, monkeypatch, frequency):
    lake, retain = census_lake
    for index in range(10):
        retain(_census_rows(1, base=149 + index / 1000), frequency=frequency)
    monkeypatch.setattr(census_fx, "read_research_view",
                        lambda *_a, **_k: pytest.fail("selected reference cap was enforced after a view read"))

    with pytest.raises(TiingoViewRefusal, match="selected-reference cap") as caught:
        _census_run(lake)

    evidence = caught.value.census_evidence
    assert len(evidence["scans"][0]["entries"]) == 10
    assert all(item["selection"] == "selected" for item in evidence["scans"][0]["entries"])
    assert evidence["selected_views"] == []
    assert evidence["byte_reads"]["metadata"] > 0
    assert evidence["byte_reads"]["raw"] == evidence["byte_reads"]["normalized"] == 0
    _assert_census_no_admission(evidence)


def test_observed_census_passes_native_128_row_cap_into_the_real_reader(census_lake, monkeypatch):
    lake, retain = census_lake
    retain(_census_rows(129, start="2026-09-01T00:00:00Z", step_minutes=240), frequency="4hour")
    real_read = census_fx.read_research_view
    caps = []

    def observe_read(*args, **kwargs):
        caps.append(kwargs["max_rows"])
        assert kwargs["read_context"] is not None
        return real_read(*args, **kwargs)

    monkeypatch.setattr(census_fx, "read_research_view", observe_read)
    with pytest.raises(TiingoViewRefusal, match="row cap") as caught:
        _census_run(lake)

    assert caps == [128]
    evidence = caught.value.census_evidence
    assert evidence["selected_row_references"] == 0
    assert evidence["byte_reads"]["normalized"] > 0
    assert evidence["byte_reads"]["raw"] > 0
    assert evidence["selected_views"][0]["state"] == "acquiring"
    _assert_census_no_admission(evidence)


def test_observed_census_passes_remaining_row_budget_into_each_real_read(census_lake, monkeypatch):
    lake, retain = census_lake
    retain(_census_rows(3))
    retain(_census_rows(3, base=150))
    monkeypatch.setattr(census_fx, "MAX_BATCH_INPUT_ROWS", 5)
    real_read = census_fx.read_research_view
    caps = []

    def observe_read(*args, **kwargs):
        caps.append(kwargs["max_rows"])
        return real_read(*args, **kwargs)

    monkeypatch.setattr(census_fx, "read_research_view", observe_read)
    with pytest.raises(TiingoViewRefusal, match="row cap") as caught:
        _census_run(lake)

    assert caps == [5, 2]
    evidence = caught.value.census_evidence
    assert evidence["selected_row_references"] == 3
    assert [item["state"] for item in evidence["selected_views"]] == ["exact_view_verified", "acquiring"]
    assert evidence["assessment"] is None
    _assert_census_no_admission(evidence)


def test_observed_census_retains_late_correction_despite_misleading_request_dates(census_lake):
    lake, retain = census_lake
    minutes, original, _native = _census_seed_closed(census_lake)
    corrected = copy.deepcopy(minutes)
    corrected[100]["close"] += .001  # Same aggregate OHLC; a real closed-minute change.
    correction = retain(corrected, observed_at="2026-10-21T08:03:00Z",
                        params={"startDate": "2010-01-01", "endDate": "2010-01-02"})

    evidence = _census_run(lake)

    correction_id = correction["saved"]["receipt_id"]
    assert evidence["state"] == "observed_census_complete_policy_unadopted"
    assert evidence["assessment"]["batch_checks_satisfied"] is False
    assert any(item["receipt_id"] == correction_id and item["selection"] == "selected"
               for item in evidence["scans"][0]["entries"])
    inventory = {item["source"]["source_receipt_id"]: item["source"]
                 for item in evidence["assessment"]["input_inventory"]}
    assert "startDate=2010-01-01" in inventory[correction_id]["source_request_path"]
    assert inventory[correction_id]["source_observed_at_utc"] == "2026-10-21T08:03:00Z"
    minute_check = evidence["assessment"]["slots"][0]["minute_vintage_check"]
    assert {original["saved"]["receipt_id"], correction_id} <= set(minute_check["compared_closed_receipt_ids"])
    assert minute_check["conflicting_closed_receipt_ids"]
    assert minute_check["supplied_closed_minute_values_consistent"] is False
    assert evidence["assessment"]["comparison_semantics"]["correction_selection"] is False
    _assert_census_no_admission(evidence)


@pytest.mark.parametrize("mutation", ["add", "remove", "change"])
def test_observed_census_second_scan_records_real_inventory_mutation(census_lake, monkeypatch, mutation):
    lake, retain = census_lake
    _census_seed_closed(census_lake)
    other = retain(_census_rows(1, pair="EURUSD"), pair="EURUSD")
    old_bytes = other["receipt_path"].read_bytes()
    old_hash = hashlib.sha256(old_bytes).hexdigest()
    real_scan = census_fx._scan_forex_receipts
    scans = 0
    added = []

    def observe_scan(*args, **kwargs):
        nonlocal scans
        scans += 1
        if scans == 2:
            if mutation == "add":
                added.append(retain(_census_rows(1, pair="GBPUSD"), pair="GBPUSD",
                                    observed_at="2026-10-21T08:03:00Z", materialize=False))
            elif mutation == "remove":
                other["receipt_path"].unlink()
            else:
                changed = dict(other["receipt"])
                changed["record_count_hint"] += 1
                changed["receipt_id"] = archive_owner.receipt_identity(changed)
                other["receipt_path"].write_text(json.dumps(changed, sort_keys=True))
        return real_scan(*args, **kwargs)

    monkeypatch.setattr(census_fx, "_scan_forex_receipts", observe_scan)
    monkeypatch.setattr(census_fx, "assess_forex_source_batch_candidate",
                        lambda *_a, **_k: pytest.fail("unstable observed evidence reached candidate assessment"))
    if mutation == "add":
        evidence = _census_run(lake)
        assert evidence["state"] == "withheld"
        assert "observed_receipt_inventory_changed" in evidence["withheld_reasons"]
        assert evidence["observed_scans_equal"] is False
        assert [scan["entry_count_before_filter"] for scan in evidence["scans"]] == [3, 4]
        added_id = added[0]["saved"]["receipt_id"]
        assert added_id not in {item["receipt_id"] for item in evidence["scans"][0]["entries"]}
        assert added_id in {item["receipt_id"] for item in evidence["scans"][1]["entries"]}
    else:
        # The descriptor-bound reader may refuse before a second complete digest;
        # that refusal must still expose the observations actually made.
        with pytest.raises(TiingoViewRefusal, match="changed|disappeared") as caught:
            _census_run(lake)
        evidence = caught.value.census_evidence
        assert evidence["state"] == "refused"
        assert evidence["scans"][0]["entry_count_before_filter"] == 3
        relative = other["receipt_path"].relative_to(lake.root).as_posix()
        original_item = next(item for item in evidence["scans"][0]["entries"] if item["path"] == relative)
        original_record = json.loads(old_bytes)
        canonical_hash = hashlib.sha256(json.dumps(original_record, sort_keys=True,
            separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        assert original_item["receipt_metadata_sha256"] == canonical_hash
        if mutation == "remove":
            assert not other["receipt_path"].exists()
            assert evidence["scans"][1]["entry_count_before_filter"] == 2
            assert relative not in {item["path"] for item in evidence["scans"][1]["entries"]}
            assert evidence["observed_scans_equal"] is False
        else:
            assert hashlib.sha256(other["receipt_path"].read_bytes()).hexdigest() != old_hash
            assert evidence["scans"][1]["entry_count_before_filter"] == 3
            assert any(item["path"] == relative and item["state"] == "unverified"
                       for item in evidence["scans"][1]["entries"])
    assert scans == 2
    assert len(evidence["scans"]) == 2
    assert evidence["assessment"] is None
    _assert_census_no_admission(evidence)


def test_observed_census_withholds_if_assessment_crosses_its_fixed_boundary(census_lake, monkeypatch):
    lake, retain = census_lake
    minutes = _census_rows(start="2026-10-21T00:00:00Z")
    retain(minutes, observed_at="2026-10-21T04:01:00Z")
    retain(_census_native_rows(minutes), frequency="4hour", observed_at="2026-10-21T04:02:00Z")
    # Invocation, both scan boundaries and verification precede 08:00;
    # assessment reaches the next slot. No older-window fallback is allowed.
    clocks = iter(["2026-10-21T07:59:59Z"] * 6 + ["2026-10-21T08:00:00Z"])
    monkeypatch.setattr(census_fx, "_census_now_utc", lambda: next(clocks))
    monkeypatch.setattr(census_fx, "assess_forex_source_batch_candidate",
                        lambda *_a, **_k: pytest.fail("a shifted anchor reached candidate assessment"))

    evidence = _census_run(lake)

    assert evidence["state"] == "withheld"
    assert evidence["fixed_latest_interval_end_utc"] == "2026-10-21T04:00:00+00:00"
    assert evidence["assessed_at_utc"] == "2026-10-21T08:00:00Z"
    assert evidence["observed_scans_equal"] is True
    assert evidence["withheld_reasons"] == ["assessment_crossed_fixed_four_hour_boundary"]
    assert evidence["assessment"] is None
    _assert_census_no_admission(evidence)


def test_observed_census_does_not_synthesize_a_view_for_retained_empty_raw(census_lake):
    lake, retain = census_lake
    empty = retain([])
    assert empty["materialized"]["status"] == "EMPTY_NORMALIZED"
    before = _census_file_hashes(lake.root)

    evidence = _census_run(lake)

    assert evidence["state"] == "withheld"
    assert evidence["withheld_reasons"] == ["selected_materialized_view_unavailable"]
    assert evidence["selected_row_references"] == 0
    assert evidence["selected_views"] == [{
        "path": empty["receipt_path"].relative_to(lake.root).as_posix(),
        "receipt_id": empty["saved"]["receipt_id"], "frequency": "1min",
        "state": "materialized_view_unavailable", "empty_payload_proven": False,
    }]
    assert evidence["assessment"] is None
    assert evidence["byte_reads"]["raw"] == evidence["byte_reads"]["normalized"] == 0
    assert _census_file_hashes(lake.root) == before
    _assert_census_no_admission(evidence)


def test_observed_census_preserves_literal_cnh_and_excludes_cny_without_aliasing(census_lake):
    lake, retain = census_lake
    _minutes, minute, native = _census_seed_closed(census_lake, pair="USDCNH")
    cny = retain(_census_rows(1, pair="USDCNY"), pair="USDCNY")

    evidence = _census_run(lake, pair="USDCNH")

    assert evidence["assessment"]["batch_checks_satisfied"] is True
    assert evidence["pair_candidate"] == "USDCNH"
    assert {item["receipt_id"] for item in evidence["selected_views"]} == {
        minute["saved"]["receipt_id"], native["saved"]["receipt_id"],
    }
    item = next(item for item in evidence["scans"][0]["entries"]
                if item["receipt_id"] == cny["saved"]["receipt_id"])
    assert item["pair"] == "USDCNY"
    assert item["selection"] == "other_literal_pair_or_frequency"
    projection = evidence["assessment"]["slots"][0]["candidate_projection"]
    assert projection["literal_pair"] == "USDCNH"
    assert projection["quote_units_per_base_unit"] == "CNH per USD"
    _assert_census_no_admission(evidence)


@pytest.mark.parametrize("kind", ["directory", "fifo", "symlink_file", "symlink_directory"])
def test_observed_census_rejects_nonregular_entries_before_metadata(census_lake, monkeypatch, kind):
    lake, _retain = census_lake
    parent = lake.root / "receipts" / "forex-bars" / "2026-10-21"
    parent.mkdir(parents=True, exist_ok=True)
    entry = parent / ("0" * 16 + "-" + "0" * 24 + ".json")
    if kind == "directory":
        entry.mkdir()
    elif kind == "fifo":
        os.mkfifo(entry)
    elif kind == "symlink_file":
        target = lake.root.parent / "outside-receipt.json"
        target.write_text("{}")
        entry.symlink_to(target)
    else:
        target = lake.root.parent / "outside-receipt-directory"
        target.mkdir()
        entry.symlink_to(target, target_is_directory=True)
    monkeypatch.setattr(census_materializer.BoundedTiingoRead, "read_metadata",
                        lambda *_a, **_k: pytest.fail("nonregular entry reached metadata read"))

    with pytest.raises(TiingoViewRefusal, match="nonregular") as caught:
        _census_run(lake)

    evidence = caught.value.census_evidence
    assert evidence["scans"][0]["entry_count_before_filter"] == 1
    assert evidence["scans"][0]["entries"] == [{
        "path": entry.relative_to(lake.root).as_posix(), "state": "unverified",
    }]
    assert evidence["selected_views"] == []
    assert evidence["byte_reads"]["metadata"] == 0
    _assert_census_no_admission(evidence)


# Strict Parquet count boundaries: controlled parser objects preserve the real
# retained fixture's lineage while exposing inconsistent footer/table counts.
def _install_strict_parquet_count_probe(
    materialized_view, monkeypatch, *, file_rows, group_rows, table_rows,
    group_count=None,
):
    from types import SimpleNamespace
    import pyarrow.parquet as pq

    root, saved, _receipt_path, _receipt = materialized_view
    expected = read_research_view(
        "eod-bars", "2026-10-09", saved["raw_sha256"], root=root, check_mount=False,
    )
    calls = []

    def row_group(index):
        calls.append(("group", index))
        return SimpleNamespace(num_rows=group_rows[index])

    def to_pylist():
        calls.append("convert")
        return list(expected.rows)

    table = SimpleNamespace(num_rows=table_rows, to_pylist=to_pylist)

    def read():
        calls.append("decode")
        return table

    metadata = SimpleNamespace(
        num_rows=file_rows,
        num_row_groups=len(group_rows) if group_count is None else group_count,
        row_group=row_group,
    )

    def parquet_file(source):
        calls.append(("open", isinstance(source, io.BytesIO)))
        return SimpleNamespace(metadata=metadata, read=read)

    monkeypatch.setattr(pq, "ParquetFile", parquet_file)
    return calls


def _read_strict_count_fixture(materialized_view, *, max_rows=1):
    root, saved, receipt_path, _receipt = materialized_view
    with BoundedTiingoRead(root, check_mount=False) as context:
        return read_research_view(
            "eod-bars", "2026-10-09", saved["receipt_id"],
            root=root, check_mount=False, receipt_path=receipt_path,
            read_context=context, max_rows=max_rows,
        )


@pytest.mark.parametrize(
    "file_rows,group_rows,visited_groups",
    [
        (-1, (), []),
        (True, (1,), []),
        (1.0, (1,), []),
        (2, (2,), []),
        (1, (-1,), [0]),
        (1, (True,), [0]),
        (1, (1.0,), [0]),
        (1, (0,), [0]),
        (0, (1,), [0]),
        # Refuse the cumulative overflow before inspecting the later bad group.
        (1, (1, 1, -1), [0, 1]),
    ],
    ids=[
        "negative-file", "boolean-file", "float-file", "file-over-cap",
        "negative-group", "boolean-group", "float-group", "sum-below-file",
        "sum-above-file", "cumulative-overflow-before-next-group",
    ],
)
def test_strict_parquet_counts_refuse_invalid_metadata_before_decode(
    materialized_view, monkeypatch, file_rows, group_rows, visited_groups,
):
    calls = _install_strict_parquet_count_probe(
        materialized_view, monkeypatch, file_rows=file_rows,
        group_rows=group_rows, table_rows=1,
    )

    with pytest.raises(TiingoViewRefusal):
        _read_strict_count_fixture(materialized_view)

    assert calls == [("open", True)] + [("group", index) for index in visited_groups]


@pytest.mark.parametrize("group_count", [-1, True, 1.0])
def test_strict_parquet_counts_refuse_invalid_group_count_before_decode(
    materialized_view, monkeypatch, group_count,
):
    calls = _install_strict_parquet_count_probe(
        materialized_view, monkeypatch, file_rows=1, group_rows=(1,),
        table_rows=1, group_count=group_count,
    )

    with pytest.raises(TiingoViewRefusal):
        _read_strict_count_fixture(materialized_view)

    assert calls == [("open", True)]


@pytest.mark.parametrize("table_rows", [-1, 0, 2, True, 1.0])
def test_strict_parquet_counts_refuse_decoded_mismatch_before_python_conversion(
    materialized_view, monkeypatch, table_rows,
):
    calls = _install_strict_parquet_count_probe(
        materialized_view, monkeypatch, file_rows=1,
        group_rows=(1,), table_rows=table_rows,
    )

    with pytest.raises(TiingoViewRefusal, match="Parquet decoded"):
        _read_strict_count_fixture(materialized_view)

    assert calls == [("open", True), ("group", 0), "decode"]


@pytest.mark.parametrize("max_rows", [True, 1.0, float("nan"), "1"])
def test_strict_parquet_counts_require_integer_cap_before_archive_access(
    materialized_view, monkeypatch, max_rows,
):
    root, saved, receipt_path, _receipt = materialized_view

    def forbidden(*_args, **_kwargs):
        pytest.fail("invalid strict cap reached archive acquisition")

    with BoundedTiingoRead(root, check_mount=False) as context:
        monkeypatch.setattr(context, "assert_root", forbidden)
        with pytest.raises(TiingoViewRefusal, match="invalid reader purpose or cap"):
            read_research_view(
                "eod-bars", "2026-10-09", saved["receipt_id"],
                root=root, check_mount=False, receipt_path=receipt_path,
                read_context=context, max_rows=max_rows,
            )


def test_strict_parquet_counts_accept_consistent_exact_limit(
    materialized_view, monkeypatch,
):
    calls = _install_strict_parquet_count_probe(
        materialized_view, monkeypatch, file_rows=1, group_rows=(0, 1), table_rows=1,
    )

    result = _read_strict_count_fixture(materialized_view)

    assert len(result.rows) == 1
    assert result.rows[0]["close_raw"] == 22
    assert calls[-2:] == ["decode", "convert"]


def test_strict_parquet_counts_leave_legacy_decode_path_unchanged(
    materialized_view, monkeypatch,
):
    calls = _install_strict_parquet_count_probe(
        materialized_view, monkeypatch, file_rows=1, group_rows=(-1,), table_rows=-1,
    )
    root, saved, _receipt_path, _receipt = materialized_view

    result = read_research_view(
        "eod-bars", "2026-10-09", saved["raw_sha256"],
        root=root, check_mount=False, max_rows=1, read_context=None,
    )

    assert len(result.rows) == 1
    assert calls == [("open", False), "decode", "convert"]


@pytest.mark.parametrize("frequency,limit", [("1min", 20_000), ("4hour", 128)])
def test_census_strict_row_count_refuses_oversized_result_before_accounting(
    census_lake, monkeypatch, frequency, limit,
):
    lake, retain = census_lake
    retain(_census_rows(1), frequency=frequency)
    real_read = census_fx.read_research_view
    caps = []

    def oversized(*args, **kwargs):
        caps.append(kwargs["max_rows"])
        view = real_read(*args, **kwargs)
        return replace(view, rows=view.rows * (limit + 1))

    def forbidden(*_args, **_kwargs):
        pytest.fail("oversized reader result reached the pure assessor")

    monkeypatch.setattr(census_fx, "read_research_view", oversized)
    monkeypatch.setattr(census_fx, "assess_forex_source_batch_candidate", forbidden)

    with pytest.raises(TiingoViewRefusal, match="exact-reader result exceeds") as caught:
        _census_run(lake)

    assert caps == [limit]
    evidence = caught.value.census_evidence
    assert evidence["state"] == "refused"
    assert evidence["selected_row_references"] == 0
    assert [item["state"] for item in evidence["selected_views"]] == ["acquiring"]
    assert len(evidence["scans"]) == 1
    assert evidence["assessment"] is None
    _assert_census_no_admission(evidence)


def test_census_strict_row_count_refuses_result_over_remaining_budget(
    census_lake, monkeypatch,
):
    lake, retain = census_lake
    retain(_census_rows(3))
    retain(_census_rows(3, base=150))
    monkeypatch.setattr(census_fx, "MAX_BATCH_INPUT_ROWS", 5)
    real_read = census_fx.read_research_view
    caps = []

    def ignores_caller_cap(*args, **kwargs):
        caps.append(kwargs["max_rows"])
        # Simulate an upstream contract regression without a malformed file.
        return real_read(*args, **{**kwargs, "max_rows": 3})

    def forbidden(*_args, **_kwargs):
        pytest.fail("over-budget reader result reached the pure assessor")

    monkeypatch.setattr(census_fx, "read_research_view", ignores_caller_cap)
    monkeypatch.setattr(census_fx, "assess_forex_source_batch_candidate", forbidden)

    with pytest.raises(TiingoViewRefusal, match="exact-reader result exceeds") as caught:
        _census_run(lake)

    assert caps == [5, 2]
    evidence = caught.value.census_evidence
    assert evidence["state"] == "refused"
    assert evidence["selected_row_references"] == 3
    assert [item["state"] for item in evidence["selected_views"]] == [
        "exact_view_verified", "acquiring",
    ]
    assert len(evidence["scans"]) == 1
    assert evidence["assessment"] is None
    _assert_census_no_admission(evidence)


def test_response_observation_storage_delay_cannot_close_a_forex_candidate(census_lake, monkeypatch):
    lake, _retain = census_lake
    minute_rows = _census_rows(start="2026-10-21T00:00:00Z")
    native_rows = _census_native_rows(minute_rows)
    bodies = [json.dumps(rows, allow_nan=False).encode()
              for rows in (minute_rows, native_rows)]
    # The minute response is complete before 04:00; storage finishes after it.
    # The native request follows that storage and is observed after 04:00.
    phases = [
        ("2026-10-21T03:59:59.900000+00:00", "2026-10-21T04:00:00.100000+00:00",
         "2026-10-21T04:00:01+00:00"),
        ("2026-10-21T04:00:02+00:00", "2026-10-21T04:00:02.100000+00:00",
         "2026-10-21T04:00:03+00:00"),
    ]
    clock = {"now": phases[0][0], "response": None}
    requests = []

    class Response:
        headers = {"Content-Type": "application/json"}

        def __init__(self, index):
            self.index = index

        def __enter__(self):
            return self

        def read(self, limit):
            assert limit == archive_owner.MAX_RESPONSE_BYTES + 1
            clock["now"] = phases[self.index][0]
            return bodies[self.index]

        def __exit__(self, *args):
            clock["now"] = phases[self.index][1]

    def open_response(req, timeout):
        index = len(requests)
        assert index < len(bodies)
        requests.append(req.full_url)
        clock["response"] = index
        return Response(index)

    def delayed_storage_check(root, *, floor):
        clock["now"] = phases[clock["response"]][2]

    monkeypatch.setattr(archive_owner.urllib.request, "urlopen", open_response)
    monkeypatch.setattr(archive_owner, "utc_now", lambda: clock["now"])
    monkeypatch.setattr(archive_owner, "require_space", delayed_storage_check)
    retained_responses = [
        archive_owner.collect_one(lake, "forex-bars", "usdjpy", "synthetic-test-key",
                                  {"resampleFreq": frequency})
        for frequency in ("1min", "4hour")
    ]
    assert len(requests) == 2
    assert requests[0].endswith("resampleFreq=1min")
    assert requests[1].endswith("resampleFreq=4hour")
    assert clock["now"] == "2026-10-21T04:00:03+00:00"

    references = []
    for saved, limit in zip(retained_responses, (240, 128)):
        day = archive_owner.capture_day(saved["observed_at_utc"])
        stem = Path(saved["path"]).name.removesuffix(".raw.gz")
        receipt_path = lake.root / "receipts" / "forex-bars" / day / (stem + ".json")
        receipt = json.loads(receipt_path.read_text())
        assert materialize_one(lake.root, receipt, free_floor=0)["status"] == "WRITTEN"
        references.append((saved, limit, day, receipt_path))

    views = []
    with BoundedTiingoRead(lake.root, check_mount=False) as context:
        for saved, limit, day, receipt_path in references:
            view = read_research_view(
                "forex-bars", day, saved["receipt_id"], root=lake.root,
                check_mount=False, receipt_path=receipt_path, read_context=context,
                max_rows=limit,
            )
            views.append((view, saved["receipt_id"]))
        context.verify_bindings()

    result = candidate_assessment(
        views, verified_at_utc="2026-10-21T04:00:04Z",
        assessed_at_utc="2026-10-21T04:00:05Z",
    )
    window = result["windows"][0]
    assert window["checks"]["valid_comparison"] is True
    assert window["checks"]["dense_minute_grid"] is True
    assert window["checks"]["normalized_ohlc_agreement"] is True
    assert window["checks"]["both_responses_observed_after_interval_end"] is False
    assert window["failed_checks"] == ["both_responses_observed_after_interval_end"]
    assert window["candidate_checks_satisfied"] is False
    assert views[0][0].source_observed_at_utc == phases[0][0]
    assert views[1][0].source_observed_at_utc == phases[1][0]
    assert result["eligible_observations"] == []
    assert result["policy_state"] == "CANDIDATE_NOT_ADOPTED"
    for flag in _CENSUS_ADMISSION_FLAGS:
        assert result[flag] is False


# Versioned clock provenance remains a research qualification, not admission.
_CLOCK_CONTRACT = "local_utc_after_bounded_read_before_http_exit/v1"
_CLOCK_SINGLE_V1 = "tiingo-forex-local-close-candidate/1"
_CLOCK_SINGLE_V2 = "tiingo-forex-local-close-candidate/2"
_CLOCK_BATCH_V1 = "tiingo-forex-local-close-batch-candidate/1"
_CLOCK_BATCH_V2 = "tiingo-forex-local-close-batch-candidate/2"


def _clock_contract_read(lake, retained):
    saved, receipt_path = retained["saved"], retained["receipt_path"]
    with BoundedTiingoRead(lake.root, check_mount=False) as context:
        view = read_research_view(
            "forex-bars", archive_owner.capture_day(saved["observed_at_utc"]),
            saved["receipt_id"], root=lake.root, check_mount=False,
            receipt_path=receipt_path, read_context=context, max_rows=240,
        )
        context.verify_bindings()
    return view, saved["receipt_id"]


@pytest.fixture
def clock_contract_case(census_lake, monkeypatch):
    lake, retain = census_lake

    def capture(rows, *, frequency="1min", observed_at="2026-10-21T08:01:00+00:00",
                closed_at=None, storage_at=None):
        raw = json.dumps(rows, allow_nan=False).encode()
        clock = {"now": observed_at}

        class Response:
            headers = {"Content-Type": "application/json"}

            def __enter__(self):
                return self

            def read(self, limit):
                assert limit == archive_owner.MAX_RESPONSE_BYTES + 1
                clock["now"] = observed_at
                return raw

            def __exit__(self, *args):
                clock["now"] = closed_at or observed_at

        with monkeypatch.context() as patched:
            patched.setattr(archive_owner.urllib.request, "urlopen",
                            lambda req, timeout: Response())
            patched.setattr(archive_owner, "utc_now", lambda: clock["now"])
            if storage_at is not None:
                def delayed_space(root, *, floor):
                    clock["now"] = storage_at
                patched.setattr(archive_owner, "require_space", delayed_space)
            saved = archive_owner.collect_one(
                lake, "forex-bars", "usdjpy", "synthetic-test-key",
                {"resampleFreq": frequency},
            )
        day = archive_owner.capture_day(saved["observed_at_utc"])
        stem = Path(saved["path"]).name.removesuffix(".raw.gz")
        receipt_path = lake.root / "receipts" / "forex-bars" / day / (stem + ".json")
        receipt = json.loads(receipt_path.read_text())
        materialized = materialize_one(lake.root, receipt, free_floor=0)
        assert materialized["status"] in {"WRITTEN", "EXISTS"}
        return {"saved": saved, "receipt_path": receipt_path, "receipt": receipt,
                "materialized": materialized}

    return lake, retain, capture


def _clock_contract_single(views, **kwargs):
    options = dict(expected_pair="USDJPY", minute_receipt_id=views[0][1],
                   four_hour_receipt_id=views[1][1],
                   verified_at_utc="2026-10-21T08:03:00Z",
                   assessed_at_utc="2026-10-21T08:04:00Z")
    options.update(kwargs)
    return assess_forex_source_candidate(views[0][0], views[1][0], **options)


def _clock_contract_batch(views, *, extra_minutes=(), extra_native=(), **kwargs):
    options = dict(expected_pair="USDJPY", consecutive=1,
                   verified_at_utc="2026-10-21T08:03:00Z",
                   assessed_at_utc="2026-10-21T08:04:00Z")
    options.update(kwargs)
    return assess_forex_source_batch_candidate(
        (views[0],) + tuple(extra_minutes), (views[1],) + tuple(extra_native), **options)


def _clock_contract_no_admission(result):
    assert result["policy_state"] == "CANDIDATE_NOT_ADOPTED"
    assert result["eligible_observations"] == []
    for flag in _CENSUS_ADMISSION_FLAGS:
        assert result[flag] is False


def test_clock_contract_legacy_receipts_keep_v1_but_fail_current_policy(clock_contract_case):
    lake, retain, _capture = clock_contract_case
    rows = _census_rows()
    records = (retain(rows), retain(_census_native_rows(rows), frequency="4hour",
                                   observed_at="2026-10-21T08:02:00Z"))
    views = tuple(_clock_contract_read(lake, record) for record in records)
    before = _census_file_hashes(lake.root)
    for view, _receipt in views:
        assert getattr(view, "source_observation_clock_contract", None) is None
        assert "source_observation_clock_contract" not in view.metadata()
    historical = _clock_contract_single(views, policy_version=_CLOCK_SINGLE_V1)
    assert historical["policy_version"] == _CLOCK_SINGLE_V1
    assert historical["windows"][0]["candidate_checks_satisfied"] is True
    assert "clock_contract_qualification" not in historical["windows"][0]
    historical_batch = _clock_contract_batch(views, policy_version=_CLOCK_BATCH_V1)
    assert historical_batch["batch_checks_satisfied"] is True
    assert "clock_contract_qualification" not in historical_batch["slots"][0]

    strict = _clock_contract_single(views)
    window = strict["windows"][0]
    assert strict["policy_version"] == _CLOCK_SINGLE_V2
    assert window["checks"]["both_responses_observed_after_interval_end"] is True
    assert window["failed_checks"] == ["response_observation_clock_contracts_qualified"]
    assert window["candidate_checks_satisfied"] is False
    assert window["clock_contract_qualification"]["unqualified_receipt_ids"] == sorted(
        receipt for _view, receipt in views)
    batch = _clock_contract_batch(views)
    assert batch["policy_version"] == _CLOCK_BATCH_V2
    assert batch["slots"][0]["candidate_assessment"]["checks"][
        "response_observation_clock_contracts_qualified"] is False
    assert batch["batch_checks_satisfied"] is False
    assert len(batch["input_inventory"]) == 2
    for result in (historical, historical_batch, strict, batch):
        _clock_contract_no_admission(result)
    assert _census_file_hashes(lake.root) == before


def test_clock_contract_marked_receipts_support_current_candidate_batch_and_census(clock_contract_case):
    lake, _retain, capture = clock_contract_case
    rows = _census_rows()
    records = (capture(rows), capture(_census_native_rows(rows), frequency="4hour",
                                     observed_at="2026-10-21T08:02:00+00:00"))
    views = tuple(_clock_contract_read(lake, record) for record in records)
    for record, (view, receipt_id) in zip(records, views):
        assert record["receipt"]["observation_clock_contract"] == _CLOCK_CONTRACT
        assert record["saved"]["observation_clock_contract"] == _CLOCK_CONTRACT
        assert archive_owner.validate_receipt(record["receipt"]) == receipt_id
        assert getattr(view, "source_observation_clock_contract", None) == _CLOCK_CONTRACT
        assert "source_observation_clock_contract" not in view.rows[0]
    strict = _clock_contract_single(views)
    assert strict["policy_version"] == _CLOCK_SINGLE_V2
    assert strict["schema"] == "mastermind.tiingo.forex_source_candidate_assessment.v2"
    assert strict["windows"][0]["candidate_checks_satisfied"] is True
    assert strict["windows"][0]["clock_contract_qualification"]["unqualified_receipt_ids"] == []
    batch = _clock_contract_batch(views)
    assert batch["policy_version"] == _CLOCK_BATCH_V2
    assert batch["batch_checks_satisfied"] is True
    for result in (strict, batch):
        _clock_contract_no_admission(result)

    before = _census_file_hashes(lake.root)
    census = census_fx.read_forex_source_batch_candidate(
        expected_pair="USDJPY", consecutive=1, root=lake.root, check_mount=False)
    assert census["policy_version"] == _CLOCK_BATCH_V2
    assert census["assessment"]["batch_checks_satisfied"] is True
    assert all(item["source_observation_clock_contract"] == _CLOCK_CONTRACT
               for item in census["selected_views"])
    _assert_census_no_admission(census)
    assert _census_file_hashes(lake.root) == before


def test_clock_contract_marked_preclose_response_stays_open_after_storage_delay(clock_contract_case):
    lake, _retain, capture = clock_contract_case
    rows = _census_rows()
    minute = capture(rows, observed_at="2026-10-21T07:59:59.900000+00:00",
                     closed_at="2026-10-21T08:00:00.100000+00:00",
                     storage_at="2026-10-21T08:00:01+00:00")
    native = capture(_census_native_rows(rows), frequency="4hour",
                     observed_at="2026-10-21T08:02:00+00:00")
    views = tuple(_clock_contract_read(lake, record) for record in (minute, native))
    result = _clock_contract_single(views)
    window = result["windows"][0]
    assert window["checks"]["response_observation_clock_contracts_qualified"] is True
    assert window["checks"]["dense_minute_grid"] is True
    assert window["checks"]["normalized_ohlc_agreement"] is True
    assert window["failed_checks"] == ["both_responses_observed_after_interval_end"]
    assert window["candidate_checks_satisfied"] is False
    _clock_contract_no_admission(result)


def test_clock_contract_reuse_never_upgrades_an_unmarked_first_receipt(clock_contract_case):
    lake, retain, capture = clock_contract_case
    rows = _census_rows()
    original = retain(rows)
    native = capture(_census_native_rows(rows), frequency="4hour",
                     observed_at="2026-10-21T08:02:00+00:00")
    before = _census_file_hashes(lake.root)
    repeated = capture(rows, observed_at="2026-10-21T08:02:30+00:00")
    assert repeated["saved"]["new_raw"] is False
    assert repeated["saved"]["receipt_id"] == original["saved"]["receipt_id"]
    assert repeated["saved"]["observed_at_utc"] == original["saved"]["observed_at_utc"]
    assert "observation_clock_contract" not in repeated["saved"]
    assert "observation_clock_contract" not in repeated["receipt"]
    views = tuple(_clock_contract_read(lake, record) for record in (repeated, native))
    result = _clock_contract_single(views)
    assert result["windows"][0]["clock_contract_qualification"]["unqualified_receipt_ids"] == [
        original["saved"]["receipt_id"]]
    assert result["windows"][0]["candidate_checks_satisfied"] is False
    assert _census_file_hashes(lake.root) == before
    _clock_contract_no_admission(result)



def test_clock_contract_unsupported_declaration_stays_readable_but_unqualified(clock_contract_case):
    lake, retain, capture = clock_contract_case
    rows = _census_rows()
    minute = retain(rows, materialize=False)
    # A syntactically valid future declaration has coherent original lineage.
    changed = {**minute["receipt"], "observation_clock_contract": "unsupported/99"}
    changed["receipt_id"] = archive_owner.receipt_identity(changed)
    minute["receipt_path"].write_text(json.dumps(changed))
    minute["receipt"] = changed
    minute["saved"] = {**minute["saved"], "receipt_id": changed["receipt_id"]}
    assert materialize_one(lake.root, changed, free_floor=0)["status"] == "WRITTEN"
    native = capture(_census_native_rows(rows), frequency="4hour",
                     observed_at="2026-10-21T08:02:00+00:00")
    views = tuple(_clock_contract_read(lake, record) for record in (minute, native))
    assert getattr(views[0][0], "source_observation_clock_contract", None) == "unsupported/99"
    historical = _clock_contract_single(views, policy_version=_CLOCK_SINGLE_V1)
    assert historical["windows"][0]["candidate_checks_satisfied"] is True
    strict = _clock_contract_single(views)
    qualification = strict["windows"][0]["clock_contract_qualification"]
    assert qualification["unqualified_receipt_ids"] == [minute["saved"]["receipt_id"]]
    evidence = next(item for item in qualification["relevant_receipts"]
                    if item["source_receipt_id"] == minute["saved"]["receipt_id"])
    assert evidence["state"] == "unsupported"
    assert evidence["declared_contract"] == "unsupported/99"
    assert strict["windows"][0]["candidate_checks_satisfied"] is False
    _clock_contract_no_admission(historical)
    _clock_contract_no_admission(strict)


@pytest.mark.parametrize("reidentify", [False, True])
def test_clock_contract_tampering_refuses_original_receipt_or_materialized_lineage(
        clock_contract_case, reidentify):
    lake, _retain, capture = clock_contract_case
    record = capture(_census_rows())
    changed = dict(record["receipt"])
    changed["observation_clock_contract"] = "unsupported/99"
    if reidentify:
        changed["receipt_id"] = archive_owner.receipt_identity(changed)
        record["saved"] = {**record["saved"], "receipt_id": changed["receipt_id"]}
    record["receipt_path"].write_text(json.dumps(changed))
    with pytest.raises(TiingoViewRefusal):
        _clock_contract_read(lake, record)


def test_clock_contract_reader_does_not_take_a_manifest_claim_as_receipt_provenance(clock_contract_case):
    lake, retain, _capture = clock_contract_case
    record = retain(_census_rows())
    manifest_path = next((lake.root / "manifests").rglob("*.json"))
    manifest = json.loads(manifest_path.read_text())
    manifest["source_observation_clock_contract"] = _CLOCK_CONTRACT
    manifest_path.write_text(json.dumps(manifest))
    view, _receipt_id = _clock_contract_read(lake, record)
    assert getattr(view, "source_observation_clock_contract", None) is None
    assert "source_observation_clock_contract" not in view.metadata()


@pytest.mark.parametrize("frequency", ["1min", "4hour"])
@pytest.mark.parametrize("relevant", [True, False])
def test_clock_contract_unknown_competing_vintage_is_not_hidden_by_an_open_clock(
        clock_contract_case, frequency, relevant):
    lake, retain, capture = clock_contract_case
    rows = _census_rows()
    records = (capture(rows), capture(_census_native_rows(rows), frequency="4hour",
                                     observed_at="2026-10-21T08:02:00+00:00"))
    views = tuple(_clock_contract_read(lake, record) for record in records)
    competing_rows = [dict(rows[0])] if frequency == "1min" else _census_native_rows(rows)
    competing_rows[0]["close"] += .001
    if not relevant:
        competing_rows[0]["date"] = "2026-10-21T00:00:00Z"
    competing = retain(competing_rows, frequency=frequency,
                       observed_at="2026-10-21T07:59:00Z")
    extra = _clock_contract_read(lake, competing)
    kwargs = {"extra_minutes" if frequency == "1min" else "extra_native": (extra,)}
    historical = _clock_contract_batch(views, policy_version=_CLOCK_BATCH_V1, **kwargs)
    assert historical["batch_checks_satisfied"] is True
    strict = _clock_contract_batch(views, **kwargs)
    qualification = strict["slots"][0]["clock_contract_qualification"]
    assert len(strict["input_inventory"]) == 3
    assert (extra[1] in qualification["unqualified_receipt_ids"]) is relevant
    assert strict["batch_checks_satisfied"] is (not relevant)
    if frequency == "4hour":
        candidate = _clock_contract_single(views, known_native_vintages=(extra,))
        assert candidate["windows"][0]["candidate_checks_satisfied"] is (not relevant)
        _clock_contract_no_admission(candidate)
    _clock_contract_no_admission(historical)
    _clock_contract_no_admission(strict)


@pytest.mark.parametrize("family,version", [
    ("candidate", "tiingo-forex-local-close-candidate/3"),
    ("candidate", _CLOCK_BATCH_V2),
    ("batch", "tiingo-forex-local-close-batch-candidate/3"),
    ("batch", _CLOCK_SINGLE_V2),
    ("census", "tiingo-forex-local-close-batch-candidate/3"),
])
def test_clock_contract_versions_refuse_without_implicit_fallback(clock_contract_case, family, version):
    lake, _retain, capture = clock_contract_case
    rows = _census_rows()
    records = (capture(rows), capture(_census_native_rows(rows), frequency="4hour",
                                     observed_at="2026-10-21T08:02:00+00:00"))
    views = tuple(_clock_contract_read(lake, record) for record in records)
    with pytest.raises(TiingoViewRefusal, match="policy"):
        if family == "candidate":
            _clock_contract_single(views, policy_version=version)
        elif family == "batch":
            _clock_contract_batch(views, policy_version=version)
        else:
            census_fx.read_forex_source_batch_candidate(
                expected_pair="USDJPY", consecutive=1, policy_version=version,
                root=lake.root, check_mount=False)
