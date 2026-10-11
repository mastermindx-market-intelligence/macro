"""IM02: source-bound, gap-aware performance-series admission (no UI yet).

All supplied decisions here are synthetic fixtures. The production publisher
must supply exact already-qualified Overview rows and saved-series witnesses.
"""
from __future__ import annotations

from copy import deepcopy
import json

import pandas as pd
import pytest

from engine.intl_performance_records import build_return_records
from engine.intl_performance_charts import build_chart_records
from tests.test_intl_inspector_view import supplied as inspector_supplied
from lib.intl_chart_publication import build_source_bound_charts

REF = "intl-supplied-close:sha256:" + "a" * 64


@pytest.fixture
def inputs():
    make, _, frame = inspector_supplied.__wrapped__()
    return make, frame


def _case(inputs, *, basis="usd_unhedged", drop_fx=False, data=None):
    make, frame = inputs
    if data is not None:
        frame = data
    raw = build_return_records(frame, market_ids=["JP", "GB"], source_reference=REF)
    view = make(basis=basis, data=raw)
    chart = build_chart_records(
        frame, market_ids=["JP", "GB"], horizon="1m",
        basis="local" if basis == "local" else "usd",
        source_reference=REF,
    )
    ids = ["^N225", "^FTSE", "GBPUSD=X"]
    if not drop_fx:
        ids.append("USDJPY=X")
    evidence = [
        {"series_id":s, "source_reference":REF,
         "content_sha256":"a" * 64, "basis_state":"accepted",
         "latest_completed_observation":frame.index[-1].isoformat(),
         "calendar_ref":"intl-conservative-observed-eod-tplus2-v1",
         "decision_ref":"saved-parquet:sha256:"+"b"*64}
        for s in ids
    ]
    return view, chart, evidence


def _project(view, chart, evidence):
    return build_source_bound_charts(view, chart, source_evidence=evidence)


def test_two_owner_qualified_markets_rebase_to_100_without_recomputing_return(inputs):
    view, chart, evidence = _case(inputs)
    before = deepcopy((view, chart, evidence))
    result = _project(view, chart, evidence)
    assert result["schema"] == "intl-source-bound-chart.v1"
    assert result["status"] == "available"
    assert len(result["cohorts"]) == 1
    # The incumbent Compare catalogue owns ranking order; GB leads here.
    assert result["cohorts"][0]["market_ids"] == ["GB", "JP"]
    assert result["benchmark"] == {
        "status":"unavailable", "reason":"benchmark_source_not_qualified"}
    for line in result["series"]:
        row = next(r for r in view["rows"] if r.get("market_id") == line["market_id"])
        assert line["status"] == "source_bound_observed"
        assert line["points"][0]["rebased"] == 100.0
        assert line["points"][-1]["rebased"] == pytest.approx(
            100.0 + row["metric"]["value"], abs=1e-7)
        assert line["gaps"] == 0
        assert all(p["rebased"] is not None for p in line["points"])
    assert (view, chart, evidence) == before
    json.dumps(result, allow_nan=False)


def test_real_interior_missing_fx_is_null_and_never_interpolated(inputs):
    _, frame = inputs
    frame = frame.copy()
    date = frame.index[12]  # Inside the actual 1m owner window.
    frame.loc[date, "USDJPY=X"] = float("nan")
    view, chart, evidence = _case(inputs, data=frame)
    result = _project(view, chart, evidence)
    japan = next(line for line in result["series"] if line["market_id"] == "JP")
    gap = next(p for p in japan["points"] if p["timestamp"] == date.isoformat())
    assert gap["rebased"] is None and gap["reason"] == "missing_fx"
    assert japan["gaps"] >= 1
    assert japan["points"][0]["rebased"] == 100.0
    assert japan["points"][-1]["rebased"] is not None
    assert result["status"] == "partial"


def test_missing_fx_witness_withholds_only_japan_usd_series(inputs):
    view, chart, evidence = _case(inputs, drop_fx=True)
    result = _project(view, chart, evidence)
    assert [line["market_id"] for line in result["series"]] == ["GB"]
    assert result["cohorts"] == []
    assert result["status"] == "partial"


def test_missing_fx_does_not_withhold_independently_qualified_local_series(inputs):
    view, chart, evidence = _case(inputs, basis="local", drop_fx=True)
    result = _project(view, chart, evidence)
    assert [line["market_id"] for line in result["series"]] == ["JP", "GB"]


def test_denied_owner_market_does_not_leak_identity_or_points(inputs):
    make, frame = inputs
    raw = build_return_records(frame, market_ids=["JP", "GB"], source_reference=REF)
    def deny(receipts):
        for item in receipts:
            if item["binding"]["market_id"] == "JP":
                item["disclosure"]["metadata"] = "denied"
    view = make(data=raw, edit=deny)
    _, chart, evidence = _case(inputs)
    result = _project(view, chart, evidence)
    assert [line["market_id"] for line in result["series"]] == ["GB"]
    assert "Nikkei" not in json.dumps(result)
    assert result["status"] == "partial"


def test_raw_chart_without_exact_owner_source_cannot_publish(inputs):
    view, chart, evidence = _case(inputs)
    chart["source_reference"] = "unqualified:unknown"
    result = _project(view, chart, evidence)
    assert result["status"] == "unavailable" and result["series"] == []


def test_missing_saved_source_evidence_cannot_promote_numerical_points(inputs):
    view, chart, evidence = _case(inputs)
    assert _project(view, chart, [])["series"] == []
    evidence[0]["content_sha256"] = "c" * 64
    result = _project(view, chart, evidence)
    assert len(result["series"]) == 1


def test_owner_endpoint_parity_mismatch_withholds_that_market(inputs):
    view, chart, evidence = _case(inputs)
    # Keep the incumbent validated Overview immutable; corrupt only the
    # unqualified numerical chart endpoint to exercise this chart-bound gate.
    modified = deepcopy(chart)
    modified["records"][0]["points"][-1]["value"] *= 1.01
    result = _project(view, modified, evidence)
    assert [r["market_id"] for r in result["series"]] == ["GB"]


def test_chart_window_mismatch_cannot_enter_same_period_cohort(inputs):
    view, chart, evidence = _case(inputs)
    chart["records"][0]["window"]["start"] = "2025-12-11T00:00:00"
    result = _project(view, chart, evidence)
    assert "JP" not in [r["market_id"] for r in result["series"]]


def test_source_denial_returns_unavailable_without_fake_benchmark(inputs):
    view, chart, evidence = _case(inputs)
    for x in evidence:
        x["basis_state"] = "unknown"
    result = _project(view, chart, evidence)
    assert result["status"] == "unavailable"
    assert result["series"] == []
    assert result["benchmark"]["status"] == "unavailable"


def test_duplicate_source_witness_fails_closed_for_only_its_market(inputs):
    view, chart, evidence = _case(inputs)
    duplicate = deepcopy(evidence)
    duplicate.append(deepcopy(evidence[0]))
    result = _project(view, chart, duplicate)
    assert [line["market_id"] for line in result["series"]] == ["GB"]


def test_unknown_or_fake_calendar_cannot_authenticate_chart_levels(inputs):
    view, chart, evidence = _case(inputs)
    for item in evidence:
        item["calendar_ref"] = "fabricated:calendar"
    result = _project(view, chart, evidence)
    assert result["series"] == []


def test_chart_duplicate_market_or_out_of_order_points_cannot_select_winner(inputs):
    view, chart, evidence = _case(inputs)
    duplicate = deepcopy(chart)
    duplicate["records"].append(deepcopy(chart["records"][0]))
    assert [r["market_id"] for r in _project(view, duplicate, evidence)["series"]] == ["GB"]
    backward = deepcopy(chart)
    backward["records"][0]["points"][8], backward["records"][0]["points"][9] = (
        backward["records"][0]["points"][9], backward["records"][0]["points"][8])
    assert [r["market_id"] for r in _project(view, backward, evidence)["series"]] == ["GB"]


def test_nonfinite_or_negative_observed_sample_makes_that_line_unavailable(inputs):
    view, chart, evidence = _case(inputs)
    for value in [float("nan"), float("inf"), -1.0, True]:
        corrupt = deepcopy(chart)
        corrupt["records"][0]["points"][8]["value"] = value
        result = _project(view, corrupt, evidence)
        assert [r["market_id"] for r in result["series"]] == ["GB"]


def test_different_matched_owner_windows_do_not_create_false_cohort(inputs):
    view, chart, evidence = _case(inputs)
    original = deepcopy(view)
    original["rows"][0]["metric"]["window"]["start"] = "2025-12-17T00:00:00"
    # The strict incumbent validator must refuse this damaged projection;
    # it is not a reason to accept two unlike periods.
    with pytest.raises(ValueError, match="invalid_compare_input"):
        _project(original, chart, evidence)


def test_conflicting_duplicate_saved_series_id_cannot_select_an_arbitrary_witness(inputs):
    view, chart, evidence = _case(inputs)
    conflicting = deepcopy(evidence)
    bad = deepcopy(evidence[0])
    bad["content_sha256"] = "c" * 64
    bad["basis_state"] = "unknown"
    conflicting.append(bad)
    result = _project(view, chart, conflicting)
    assert [line["market_id"] for line in result["series"]] == ["GB"]
