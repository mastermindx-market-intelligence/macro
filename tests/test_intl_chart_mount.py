"""Attach IM02 geometry to the incumbent Compare catalogue, never a new plane."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import json

import pandas as pd
import pytest
from jinja2 import Environment, FileSystemLoader

from engine.intl_inputs import countries, source_snapshot
from engine.intl_performance_records import build_return_records
from engine.intl_workspace_overview import build_overview
from lib.intl_compare_mount import attach_compares
from lib.intl_chart_mount import attach_source_bound_charts
from tests.test_intl_inspector_view import supplied

_BASIS = "yfinance:auto_adjust=true:observed-close"
_POLICY = "intl-observed-endpoints-completed-session-v1"


@pytest.fixture()
def admitted_pair():
    frame = supplied.__wrapped__()[2]
    adjustment_bases = {
        s: _BASIS for m in countries().values() for s in (m["index"], m["fx"])
    }
    pending = source_snapshot(
        frame, source_reference="intl-supplied-close:pending",
        adjustment_bases=adjustment_bases)
    digest = pending["content_sha256"]
    ref = "intl-supplied-close:sha256:" + digest
    records = build_return_records(
        frame, market_ids=["JP", "GB"], source_reference=ref)
    roster = [
        {"market_id":market, "name_en":countries()[market]["name"],
         "name_zh":countries()[market]["name_zh"]}
        for market in ("JP", "GB")
    ]
    panels = []
    for basis in ("usd_unhedged", "local"):
        context = {"horizon":"1m", "currency_basis":basis,
                   "return_basis":"price", "source_reference":ref}
        qualifications = []
        for record in records["records"]:
            if record["horizon"] != "1m":
                continue
            for leg in ("local","usd","fx_contribution"):
                metric = record[leg]
                qualifications.append({
                    "binding": {
                        "source_reference":ref, "market_id":record["market_id"],
                        "index_id":record["index_id"], "fx_id":record["fx_id"],
                        "horizon":"1m", "currency_basis":basis,
                        "return_basis":"price", "leg":leg,
                        "value":metric["value"], "unit":metric["unit"],
                        "window":deepcopy(metric["window"])},
                    "owner_ref":"synthetic-source-owner",
                    "policy_ref":_POLICY,
                    "decision_ref":"synthetic-disclosure",
                    "quality":"qualified", "reason":None,
                    "disclosure":{"metadata":"allowed","value":"allowed"},
                })
        panel = build_overview(records,roster=roster,context=context,
                               qualifications=qualifications)
        panels.append({"context_id": "im-1m-"+basis, "overview":panel})
    workspace = {
        "config": {
            "markets":["JP","GB"], "horizons":["1m"],
            "bases":["usd_unhedged","local"],
            "default_horizon":"1m", "default_basis":"usd_unhedged",
            "source_reference":ref, "anchor_ids":[], "library_group_ids":[]},
        "panels":panels,
        "eod_snapshot":{"as_of":frame.index[-1].date().isoformat(),
                        "policy":"intl-conservative-observed-eod-tplus2-v1"},
    }
    evidence=[
        {"series_id":series,"source_reference":ref,
         "content_sha256":digest,"basis_state":"accepted",
         "adjustment_basis":_BASIS,
         "calendar_ref":"intl-conservative-observed-eod-tplus2-v1",
         "latest_completed_observation":frame.index[-1].isoformat(),
         "decision_ref":"saved-parquet:sha256:"+"b"*64}
        for series in ("^N225","USDJPY=X","^FTSE","GBPUSD=X")
    ]
    return workspace,frame,{
        "policy_id":_POLICY,
        "source_evidence":evidence,
        "adjustment_bases":adjustment_bases,
    }


def _mount(args):
    workspace, frame, packet = args
    return attach_source_bound_charts(workspace,frame,production_inputs=packet)


def _present(result):
    return [c["compare_catalogue"] for c in result["compares"]
            if "chart_geometry" in c["compare_catalogue"]]


def test_true_snapshotted_owner_inputs_create_both_chart_bases(admitted_pair):
    before = deepcopy(admitted_pair)
    result = _mount(admitted_pair)
    assert len(_present(result)) == 2
    assert all(row["chart_geometry"]["status"] == "available"
               for row in _present(result))
    assert all(row["chart_geometry"]["cohorts"][0]["paths"][0]["segments"][0]["d"]
               for row in _present(result))
    assert all(set(row["chart_names"]) == {"JP","GB"} for row in _present(result))
    assert admitted_pair[0] == before[0]
    assert admitted_pair[2] == before[2]
    pd.testing.assert_frame_equal(admitted_pair[1],before[1])
    json.dumps(result, allow_nan=False)


def test_same_incumbent_compare_catalogue_survives_denied_or_missing_data(admitted_pair):
    ws,closes,packet = admitted_pair
    missing = deepcopy(packet)
    missing["source_evidence"]=[]
    result = _mount((ws,closes,missing))
    reference = attach_compares(ws)
    assert result == reference
    assert all("chart_geometry" not in c["compare_catalogue"]
               for c in result["compares"])


@pytest.mark.parametrize("corrupt",["source_digest","snapshot_date","policy","adjustment","revoked_source"])
def test_forged_or_missing_publisher_binding_never_shows_chart(admitted_pair,corrupt):
    ws,closes,packet = deepcopy(admitted_pair)
    if corrupt=="source_digest":
        closes.iloc[3,0] *= 1.12
    elif corrupt=="snapshot_date":
        ws["eod_snapshot"]["as_of"]="2025-12-31"
    elif corrupt=="policy":
        packet["policy_id"]="fake-policy"
    elif corrupt=="adjustment":
        packet["adjustment_bases"]["^N225"]="unknown-basis"
    elif corrupt=="revoked_source":
        packet["source_evidence"][0]["basis_state"]="unknown"
    result = _mount((ws,closes,packet))
    assert "chart_geometry" not in result["compares"][0]["compare_catalogue"]


def test_partial_witness_suppresses_one_market_but_keeps_compare_rows(admitted_pair):
    ws,closes,packet = deepcopy(admitted_pair)
    packet["source_evidence"]=[
        row for row in packet["source_evidence"] if row["series_id"]!="USDJPY=X"]
    result = _mount((ws,closes,packet))
    compared = result["compares"][0]["compare_catalogue"]
    assert compared["rows"][0]["usd"]["quality"] == "qualified"
    assert "chart_geometry" not in compared
    assert compared["chart"]["status"] == "unavailable"
    assert len(compared["rows"]) == 2


def test_current_compare_template_optional_chart_does_not_break_markup(admitted_pair):
    from pathlib import Path
    ws,closes,packet=admitted_pair
    compared=_mount(admitted_pair)["compares"][0]
    root=Path(__file__).resolve().parents[1]
    env=Environment(loader=FileSystemLoader(str(root/"templates")),autoescape=True)
    rendered=env.get_template("intl_workspace/compare.html.j2").render(
        compare_catalogue=compared["compare_catalogue"],context_id=compared["context_id"])
    assert rendered.count("data-im-compare-catalogue") == 1
    assert rendered.count("data-im-chart-model") == 1
    assert rendered.count("data-im-chart-cohort") == 1
    assert 'data-im-chart-data-table' in rendered
    no_chart=attach_compares(ws)["compares"][0]
    fallback=env.get_template("intl_workspace/compare.html.j2").render(
        compare_catalogue=no_chart["compare_catalogue"],context_id=no_chart["context_id"])
    assert "Chart series and benchmark comparison are unavailable." in fallback
    assert "data-im-chart-model" not in fallback


class _ActualCompareTemplate:
    """Minimal incumbent render surface; no artificial chart calculation."""
    def __init__(self):
        from jinja2 import Environment, FileSystemLoader
        from pathlib import Path
        self.env=Environment(loader=FileSystemLoader(
            str(Path(__file__).resolve().parents[1]/"templates")),autoescape=True)

    def render(self, **vm):
        if vm.get("mode")=="stocks":
            return '<section id="international-stock-directory">Stocks</section>'
        ws=vm["intl_workspace"]
        parts=['<main id="intl-root"><section id="lb-board">Research</section>']
        for c in ws.get("compares", []):
            parts.append(self.env.get_template("intl_workspace/compare.html.j2").render(
                compare_catalogue=c["compare_catalogue"],context_id=c["context_id"]))
        parts.append('</main>')
        return ''.join(parts)


def test_normal_library_renderer_mounts_optional_qualified_charts_without_raw_policy_fields(admitted_pair):
    from lib.intl_library_mount import render_international_pages
    ws,frame,packet=admitted_pair
    html,stocks=render_international_pages(
        _ActualCompareTemplate(),{"intl_workspace":ws},chart_sources=(frame,packet))
    assert stocks.startswith("<section")
    assert html.count('data-im-compare-panel')==2
    assert html.count('data-im-chart-model="intl-chart-geometry.v1"')==2
    assert html.count('data-im-chart-selection-unavailable hidden')==2
    assert 'data-im-chart-series="JP"' in html
    assert "saved-parquet:sha256" not in html
    assert "adjustment_bases" not in html
    assert "decision_ref" not in html


def test_invalid_optional_chart_payload_does_not_disable_the_comparison_workspace(admitted_pair):
    from lib.intl_library_mount import render_international_pages
    ws,frame,packet=admitted_pair
    html,_=render_international_pages(_ActualCompareTemplate(),{"intl_workspace":ws},
                                       chart_sources=(frame,{"policy_id":"revoked"}))
    assert html.count('data-im-compare-panel')==2
    assert 'data-im-chart-model' not in html
    assert 'Chart series and benchmark comparison are unavailable.' in html
    malformed,_=render_international_pages(_ActualCompareTemplate(),{"intl_workspace":ws},
                                            chart_sources=("not-a-packet",))
    assert malformed.count('data-im-compare-panel')==2
    assert 'data-im-chart-model' not in malformed


def test_old_series_tip_does_not_borrow_the_other_markets_fresh_digest(admitted_pair):
    ws, closes, packet = deepcopy(admitted_pair)
    receipt = next(row for row in packet["source_evidence"] if row["series_id"] == "^N225")
    receipt["latest_completed_observation"] = "2025-12-30T00:00:00"
    result = _mount((ws, closes, packet))
    assert "chart_geometry" not in result["compares"][0]["compare_catalogue"]
    assert len(result["compares"][0]["compare_catalogue"]["rows"]) == 2


def test_mixed_adjustment_basis_withholds_dependent_chart_without_rejecting_compare(admitted_pair):
    ws, closes, packet = deepcopy(admitted_pair)
    receipt = next(row for row in packet["source_evidence"] if row["series_id"] == "^N225")
    receipt["adjustment_basis"] = "unadjusted-source-mismatch"
    result = _mount((ws, closes, packet))
    assert "chart_geometry" not in result["compares"][0]["compare_catalogue"]
    assert len(result["compares"][0]["compare_catalogue"]["rows"]) == 2

def test_full_source_digest_is_available_in_a_disclosure_not_always_on_header(admitted_pair):
    from lib.intl_library_mount import render_international_pages
    ws, frame, packet = admitted_pair
    html,_ = render_international_pages(
        _ActualCompareTemplate(), {"intl_workspace": ws},
        chart_sources=(frame, packet))
    assert '<details class="intl-compare__source" data-im-compare-source>' in html
    assert '<summary>' in html and 'Source evidence' in html
    assert '<code' in html and "intl-supplied-close:sha256:" in html
    assert '<wbr>' in html
    assert 'style=' not in html
