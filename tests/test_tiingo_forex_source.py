"""Offline exact-receipt Forex diagnostics never admit final bars."""
import copy
import hashlib
import json
from dataclasses import replace

import pytest
import collectors.tiingo_archive as archive_owner
from lib.dataos.tiingo_reader import TiingoView, TiingoViewRefusal
from lib.dataos.tiingo_views import research_rows
from lib.dataos.tiingo_forex import diagnose_forex_view, read_forex_watch_source, QUALIFICATION_GAPS
from scripts.tiingo_materialize import materialize_one


def payload():
    return [{"ticker": "usdjpy", "date": stamp, "open": 149.0, "high": 150.0,
             "low": 148.0, "close": close}
            for stamp, close in [("2026-10-19T00:00:00Z", 149.1), ("2026-10-19T00:01:00Z", 149.2)]]


def view_for(data=None):
    data = payload() if data is None else data
    raw = json.dumps(data).encode()
    rec = {"schema": "mastermind.tiingo.raw_receipt.v1", "source": "forex-bars",
           "symbol": "usdjpy", "vendor": "tiingo",
           "raw_sha256": hashlib.sha256(raw).hexdigest(),
           "observed_at_utc": "2026-10-21T13:00:00Z",
           "request_path": archive_owner.request_path("forex-bars", "usdjpy", {"resampleFreq": "1min"})}
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
