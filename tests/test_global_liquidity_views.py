"""Tests for engine/global_liquidity_views.py (GLT T22 M1, display-only).

Every fixture below is synthetic (copied T08 fixture builders, synthetic T09
cells, synthetic cross-repo science blocks, synthetic replay history). The
economic law under test: a number only travels with the estimate type its
upstream record declared, an unsupported disposition carries a word and no
number, and a missing field is named, never invented.
"""

from __future__ import annotations

import copy
import json
import re
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

import engine.global_liquidity_outlook as outlook_module
from engine.global_liquidity_outlook import (
    H41_ASSETS_LINE,
    H41_CAPITAL_LINE,
    H41_RESERVES_LINE,
    snapshot as outlook_snapshot,
)
from engine.global_liquidity_views import (
    AUTHORITY,
    CONDITIONING_KEYS,
    CROSS_REPO_OWNER,
    ESTIMATE_TYPES,
    EVIDENCE_LABELS,
    PRODUCT_DISPOSITIONS,
    REPLAY_ESTIMATE_TYPES,
    REPLAY_MAX,
    SOURCE_DISPOSITION_MAP,
    VIEW_NAMES,
    ViewsContractError,
    compose_views,
    failed_views,
    validate_view,
    validate_views,
)

NY = ZoneInfo("America/New_York")

# --- copied T08 fixture builders (never imported from another test module) ---
FR_NOTES = "Federal Reserve notes, net of F.R. Bank holdings"
RRP_FOREIGN = "Reverse repurchase agreements: Foreign official and international accounts"
RRP_OTHERS = "Reverse repurchase agreements: Others"
TERM_DEPOSITS = "Deposits: Term deposits held by depository institutions"
TGA_LINE = "Deposits: U.S. Treasury, General Account"
DEPOSITS_FOREIGN = "Deposits: Foreign official"
DEPOSITS_OTHERS = "Deposits: Other"
DEFERRED_CASH = "Deferred availability cash items"
TREASURY_CONTRIBS = "Treasury contributions to credit facilities"
EARNINGS_REMITTANCES = "Earnings remittances due to the U.S. Treasury"
OTHER_LIABILITIES = "Other liabilities and accrued dividends"

FIXTURE_ROW = {
    FR_NOTES: 2_300_000,
    RRP_FOREIGN: 380_000,
    RRP_OTHERS: 150_000,
    TERM_DEPOSITS: 0,
    TGA_LINE: 800_000,
    DEPOSITS_FOREIGN: 10_000,
    DEPOSITS_OTHERS: 120_000,
    DEFERRED_CASH: 1_000,
    TREASURY_CONTRIBS: 5_000,
    EARNINGS_REMITTANCES: -230_000,
    OTHER_LIABILITIES: 40_000,
    H41_CAPITAL_LINE: 50_000,
    H41_RESERVES_LINE: 3_000_000,
    H41_ASSETS_LINE: 6_626_000,
}

AS_OF = date(2026, 9, 4)

T09_PATH = Path(__file__).resolve().parents[1] / "research" / "GLT_T09_FORECAST_RESULT_2026-10-13.json"
REAL_T09_DAY = date(2026, 10, 19)


def make_anchor(row=None):
    return {
        "observed_on": date(2026, 9, 2),
        "published_at": datetime(2026, 9, 3, 16, 30, tzinfo=NY),
        "publication_tz": "America/New_York",
        "row": dict(FIXTURE_ROW if row is None else row),
    }


def make_announcements():
    return [
        {
            "id": "tga-qra-2026q3",
            "component": "treasury_general_account",
            "kind": "schedule",
            "published_at": datetime(2026, 8, 4, 8, 30, tzinfo=NY),
            "changes": [{"effective": date(2026, 9, 30), "level": 850_000}],
        },
        {
            "id": "tga-qra-2026q3-rev",
            "component": "treasury_general_account",
            "kind": "schedule",
            "published_at": date(2026, 9, 10),
            "supersedes": "tga-qra-2026q3",
            "changes": [{"effective": date(2026, 9, 30), "level": 900_000}],
        },
        {
            "id": "financing-shift-2026-09-15",
            "component": "treasury_general_account",
            "kind": "financing_source",
            "published_at": date(2026, 9, 15),
            "changes": [{"effective": date(2026, 9, 16), "delta": -200_000}],
        },
        {
            "id": "same-day-after-cutoff",
            "component": "treasury_general_account",
            "kind": "schedule",
            "published_at": datetime(2026, 9, 4, 8, 30, tzinfo=NY),
            "changes": [{"effective": date(2026, 9, 30), "level": 700_000}],
        },
    ]


def make_assumptions():
    return [
        {
            "id": "qt-runoff-assumption",
            "component": "total_assets",
            "kind": "weekly_delta",
            "value": -5_000,
        },
        {"id": "hold-tga", "component": "treasury_general_account", "kind": "hold_level"},
        {
            "id": "hold-reverse-repo-others",
            "component": "reverse_repo_others",
            "kind": "hold_level",
        },
        {
            "id": "hold-reverse-repo-foreign-official",
            "component": "reverse_repo_foreign_official",
            "kind": "hold_level",
        },
        {
            "id": "hold-federal-reserve-notes",
            "component": "federal_reserve_notes",
            "kind": "hold_level",
        },
        {
            "id": "hold-other-nonreserve-and-capital",
            "component": "other_nonreserve_and_capital",
            "kind": "hold_level",
        },
    ]


# --- views helpers -----------------------------------------------------------

def _env(day=AS_OF):
    return {"state": {"asof": day.isoformat()}}


def _outlook_inputs(unit="USD_bn", bounds=None, assumptions=None, announcements=None,
                    anchor=None):
    oi = {
        "anchor": anchor if anchor is not None else make_anchor(),
        "announcements": announcements if announcements is not None else make_announcements(),
        "assumptions": assumptions if assumptions is not None else make_assumptions(),
        "unit": unit,
    }
    if bounds is not None:
        oi["scenario_bounds"] = bounds
    return oi


def _compose(day=AS_OF, history=None, t09=None, cross=None, oi=None, env=None):
    return compose_views(
        env if env is not None else _env(day),
        history,
        t09,
        cross,
        as_of=day,
        outlook_inputs=oi,
    )


def _pkg(day="2026-09-01", cells=None):
    return {"run": {"as_of": day + "T11:16:11+00:00"}, "cells": cells if cells is not None else []}


def _cell(target="reserves_wresbal_bn", horizon=4, disposition="issued", **over):
    cell = {
        "target": target,
        "horizon_weeks": horizon,
        "candidate": "candidate_a",
        "disposition": disposition,
        "estimate_type": "statistical_forecast" if disposition == "issued" else "unavailable",
    }
    cell.update(over)
    return cell


def _issued_cell(target="reserves_wresbal_bn", horizon=4, point=3_050.0):
    return _cell(
        target,
        horizon,
        "issued",
        point=point,
        interval={"low": point - 100.0, "high": point + 100.0, "nominal": 80},
        probability_interpretation="preregistered interval covering frequency",
        calibration_ref="GLT_T09_FORECAST_RESULT_2026-10-13",
    )


CARDLESS_TARGETS = ["efa", "eem", "gld", "slv", "dbc", "uso", "cper"]


def _xblock(disposition="supported", label="observed_association", **over):
    block = {
        "status": "available",
        "disposition": disposition,
        "label": label,
        "rows": [{"key": "usd_funding_impulse", "value": 0.4, "estimate_type": label}],
        "regions": [
            {"region": "us", "state": "available", "owner": "h41 owner seat"},
            {"region": "eu", "state": "blocked", "owner": "ecb data seat"},
        ],
        "targets": [
            {"target": name, "has_card": False} for name in CARDLESS_TARGETS
        ] + [{"target": "spy", "has_card": True}],
    }
    block.update(over)
    return block


def _cross(transmission=None, repricing=None):
    return {
        "transmission": transmission if transmission is not None else _xblock(),
        "repricing_evidence": repricing if repricing is not None else _xblock(),
    }


def _hist(known_at, components=None, types=None, corrections=None):
    return {
        "known_at": known_at,
        "components_as_known": components
        if components is not None
        else {"reserves": 3_000_000, "tga": 800_000, "rrp": 530_000},
        "estimate_types_as_known": types
        if types is not None
        else {"reserves": "observed", "tga": "observed", "rrp": "observed"},
        "corrections": corrections if corrections is not None else [],
    }


def _walk_numbers(obj):
    found = []

    def _walk(node):
        if isinstance(node, bool):
            return
        if isinstance(node, (int, float)):
            found.append(node)
        elif isinstance(node, dict):
            for value in node.values():
                _walk(value)
        elif isinstance(node, (list, tuple)):
            for value in node:
                _walk(value)

    _walk(obj)
    return found


# --- C37: a number without its declared estimate type is refused -------------

def test_c37_numeric_without_estimate_type_is_refused():
    bad_rows = [{"key": "usd_funding_impulse", "value": 1.5}]
    with pytest.raises(ViewsContractError):
        _compose(cross={"transmission": _xblock(rows=bad_rows), "repricing_evidence": _xblock()})
    # the row shape itself is refused even when the value is None, so the
    # refusal does not lean on the whole-document numeric walk
    with pytest.raises(ViewsContractError):
        _compose(cross={"transmission": _xblock(rows=[{"key": "x", "value": None}]),
                        "repricing_evidence": _xblock()})

    bad_types = dict({"reserves": "observed", "tga": "observed", "rrp": "unavailable"})
    with pytest.raises(ViewsContractError):
        _compose(history=[_hist("2026-09-01", {"reserves": 1, "tga": 2, "rrp": 3}, bad_types)])

    bare = {
        "status": "available",
        "rows": [{"key": "x", "change_from_anchor": 1.0, "estimate_type": "observed_association"}],
        "nested": {"level": 1.0},
    }
    with pytest.raises(ViewsContractError):
        validate_view("transmission", bare)


def test_c37_estimate_types_and_dispositions_are_distinct_tokens():
    assert not (set(ESTIMATE_TYPES) & set(EVIDENCE_LABELS))
    assert not (set(PRODUCT_DISPOSITIONS) & (set(ESTIMATE_TYPES) | set(EVIDENCE_LABELS)
                                             | set(REPLAY_ESTIMATE_TYPES)))
    assert not (set(SOURCE_DISPOSITION_MAP) & (set(ESTIMATE_TYPES) | set(PRODUCT_DISPOSITIONS))
                - {"unavailable"})  # the shared degraded sentinel is the one overlap
    assert not (set(CONDITIONING_KEYS) & (set(ESTIMATE_TYPES) | set(EVIDENCE_LABELS)))
    assert set(SOURCE_DISPOSITION_MAP.values()) <= set(PRODUCT_DISPOSITIONS) | {"unavailable"}

    views = _compose(
        day=date(2026, 9, 4),
        history=[_hist("2026-09-01")],
        t09=_pkg(cells=[_issued_cell()]),
        cross=_cross(),
        oi=_outlook_inputs(),
    )
    outlook_tokens = {
        p["estimate_type"]
        for comp in views["conditional_outlook"]["components"].values()
        for p in comp["points"]
    }
    assert outlook_tokens <= {"announced_scenario", "conditional_accounting"}
    assert views["statistical_forecast"]["cells"][0]["estimate_type"] == "statistical_forecast"
    assert all(r["estimate_type"] == "observed_association"
               for r in views["transmission"]["rows"])
    assert views["replay"]["rows"][0]["estimate_types_as_known"]["reserves"] == "observed"
    assert len({views["statistical_forecast"]["cells"][0]["estimate_type"],
                "observed_association",
                views["conditional_outlook"]["reserves"]["estimate_type"]}) == 3


def test_c38_input_states_are_distinct():
    missing = _compose(t09=None)["statistical_forecast"]
    zero_assumptions = copy.deepcopy(make_assumptions())
    zero_assumptions[0]["value"] = 0
    zero = _compose(oi=_outlook_inputs(assumptions=zero_assumptions))["conditional_outlook"]
    assert zero["status"] == "available"
    assert any(p["change_from_anchor"] == 0 for p in zero["components"]["total_assets"]["points"])

    partial_assumptions = [a for a in make_assumptions()
                           if a["id"] != "hold-reverse-repo-others"]
    partial = _compose(oi=_outlook_inputs(assumptions=partial_assumptions))["conditional_outlook"]
    warmup = _compose(history=[])["replay"]
    revised = _compose(history=[_hist("2026-09-01", corrections=[
        {"field": "tga", "corrected_at": "2026-09-02", "note_key": "source_revised"}
    ])])["replay"]
    expired = _compose(day=date(2026, 9, 4), env=_env(),
                       t09=_pkg(day="2026-09-05"))["statistical_forecast"]

    tuples = {
        ("statistical_forecast", missing["status"], missing["reason_key"]),
        ("conditional_outlook", zero["status"], None),
        ("conditional_outlook", partial["status"], partial["reason_key"]),
        ("replay", warmup["status"], warmup["reason_key"]),
        ("replay", revised["rows"][0]["row_state"], None),
        ("statistical_forecast", expired["status"], expired["reason_key"]),
    }
    assert missing["reason_key"] == "forecast_package_missing"
    assert partial["reason_key"] == "component_unavailable"
    assert warmup["reason_key"] == "issue_history_warming_up"
    assert revised["rows"][0]["row_state"] == "corrected"
    assert expired["reason_key"] == "forecast_package_after_as_of"
    assert len(tuples) == 6


# --- C39: replay is source-known only ---------------------------------------

def test_c39_replay_shows_only_known_at_le_as_of():
    records = [
        _hist("2026-08-28"),
        _hist("2026-09-01"),
        _hist("2026-09-04"),
    ]
    replay = _compose(day=AS_OF, history=records)["replay"]
    assert replay["status"] == "available"
    assert [r["known_at"] for r in replay["rows"]] == ["2026-09-04", "2026-09-01", "2026-08-28"]


def test_c39_replay_refuses_future_known_at():
    with pytest.raises(ViewsContractError):
        _compose(history=[_hist("2026-09-05")])


def test_c39_replay_refuses_injected_current_value():
    record = _hist("2026-09-01")
    record["current_value"] = {"reserves": 3_100_000}
    with pytest.raises(ViewsContractError):
        _compose(history=[record])


def test_c39_replay_refuses_illustrative_scenario():
    with pytest.raises(ViewsContractError):
        types = {"reserves": "illustrative", "tga": "observed", "rrp": "observed"}
        _compose(history=[_hist("2026-09-01", {"reserves": 1, "tga": 2, "rrp": 3}, types)])
    with pytest.raises(ViewsContractError):
        types = {"reserves": "statistical_forecast", "tga": "observed", "rrp": "observed"}
        _compose(history=[_hist("2026-09-01", {"reserves": 1, "tga": 2, "rrp": 3}, types)])


def test_c39_replay_row_without_corrections_is_refused():
    record = _hist("2026-09-01")
    del record["corrections"]
    with pytest.raises(ViewsContractError):
        _compose(history=[record])
    record2 = _hist("2026-09-01")
    record2["corrections"] = None
    with pytest.raises(ViewsContractError):
        _compose(history=[record2])


def test_c39_replay_keeps_last_eight_newest_first():
    records = [_hist((date(2026, 7, 1) + timedelta(days=7 * i)).isoformat())
               for i in range(10)]
    replay = _compose(history=records)["replay"]
    kept = [r["known_at"] for r in replay["rows"]]
    assert len(kept) == REPLAY_MAX
    expected = sorted((r["known_at"] for r in records), reverse=True)[:REPLAY_MAX]
    assert kept == expected
    assert kept[0] == "2026-09-02"


def test_c39_leaving_replay_restores_current_cutoff():
    history = [_hist("2026-08-28"), _hist("2026-09-01")]
    t_now = date(2026, 9, 4)
    t_old = date(2026, 9, 1)
    views_old = _compose(day=t_old, env=_env(t_old), history=history)
    views_now = _compose(day=t_now, env=_env(t_now), history=history)
    views_now_without = _compose(day=t_now, env=_env(t_now), history=None)
    assert views_old["as_of"] == "2026-09-01"
    assert views_now["as_of"] == "2026-09-04"
    assert len(views_old["replay"]["rows"]) == 2
    for name in VIEW_NAMES:
        if name == "replay":
            continue
        assert views_now[name] == views_now_without[name]


# --- D: no value without a supported disposition ------------------------------

def test_d_non_supported_dispositions_carry_no_value():
    for disposition in ("rejected", "insufficient", "narrowed", "not_identified"):
        block = _xblock(disposition=disposition)
        views = _compose(cross={"transmission": block, "repricing_evidence": _xblock()})
        assert views["transmission"]["rows"] == []

    real = json.loads(T09_PATH.read_text(encoding="utf-8"))
    views = _compose(day=REAL_T09_DAY, env=_env(REAL_T09_DAY), t09=real)["statistical_forecast"]
    assert views["status"] == "available"
    assert len(views["cells"]) == 9
    assert all(c["disposition"] == "rejected" for c in views["cells"])
    assert all(c["estimate_type"] == "unavailable" for c in views["cells"])
    for cell in views["cells"]:
        numbers = _walk_numbers(cell)
        assert numbers == [cell["horizon_weeks"]]
    dump = json.dumps(views, sort_keys=True)
    for word in ("persistence", "announced_only", "seasonal", "training_only",
                 "ridge", "residual_ar", "relative_gain", "conformal",
                 "best_baseline", "abstention_reason", "gain_ci", "mean_width"):
        assert word not in dump


def test_e_component_intervals_never_total():
    views = _compose(oi=_outlook_inputs(bounds=[
        {"component": "total_assets", "horizon_weeks": 4, "low": -25_000, "high": -15_000},
    ]))["conditional_outlook"]
    assert views["status"] in ("available", "partial")

    def _keys(node, out):
        if isinstance(node, dict):
            out.update(node.keys())
            for value in node.values():
                _keys(value, out)
        elif isinstance(node, list):
            for value in node:
                _keys(value, out)

    keys = set()
    _keys(views, keys)
    assert not any(k == "total" for k in keys)
    assert not any("interval" in k for k in keys)
    for point in views["reserves"]["points"]:
        assert "scenario_bounds" not in point


# --- H: forecast issuance and outlook inputs ---------------------------------

def test_h_supported_forecast_without_probability_interpretation_is_refused():
    cell = _issued_cell()
    del cell["probability_interpretation"]
    with pytest.raises(ViewsContractError):
        _compose(t09=_pkg(cells=[cell]))

    full = _compose(t09=_pkg(cells=[_issued_cell()]))["statistical_forecast"]
    assert full["status"] == "available"
    issued = full["cells"][0]
    assert issued["disposition"] == "supported"
    assert issued["estimate_type"] == "statistical_forecast"
    assert issued["point"] == 3_050.0
    assert issued["interval"] == {"low": 2_950.0, "high": 3_150.0, "nominal": 80}


def test_h_outlook_input_interval_is_refused():
    for poisoned in ("interval", "quantiles", "probability_interpretation"):
        anchor = make_anchor()
        anchor["row"][poisoned] = 5
        with pytest.raises(ViewsContractError):
            _compose(oi=_outlook_inputs(anchor=anchor))
        announcements = make_announcements()
        announcements[0][poisoned] = 5
        with pytest.raises(ViewsContractError):
            _compose(oi=_outlook_inputs(announcements=announcements))
        assumptions = make_assumptions()
        assumptions[0][poisoned] = 5
        with pytest.raises(ViewsContractError):
            _compose(oi=_outlook_inputs(assumptions=assumptions))


def test_h_scenario_bounds_are_copied_and_labelled():
    bounds = [{"component": "total_assets", "horizon_weeks": 4, "low": -25_000, "high": -15_000}]
    views = _compose(oi=_outlook_inputs(bounds=bounds))["conditional_outlook"]
    point = views["components"]["total_assets"]["points"][0]
    assert point["scenario_bounds"] == {"low": -25_000, "high": -15_000}
    assert point["conditioning_assumption_key"] == "glt_cond_weekly_change"
    assert point["estimate_type"] == "conditional_accounting"
    assert point["published_at"] == "2026-09-03T20:30:00+00:00"  # anchor lineage
    tga_point = views["components"]["treasury_general_account"]["points"][0]
    assert tga_point["conditioning_assumption_key"] == "glt_cond_announced_schedule"
    assert tga_point["estimate_type"] == "announced_scenario"
    assert tga_point["published_at"] == "2026-08-04T12:30:00+00:00"  # admitted announcement
    assert tga_point["scenario_bounds"] is None

    with pytest.raises(ViewsContractError):
        _compose(oi=_outlook_inputs(bounds=[
            {"component": "total_assets", "horizon_weeks": 4, "low": -15_000, "high": -25_000}]))
    with pytest.raises(ViewsContractError):
        _compose(oi=_outlook_inputs(bounds=[
            {"component": "reserves", "horizon_weeks": 4, "low": -1, "high": 1}]))
    with pytest.raises(ViewsContractError):
        _compose(oi=_outlook_inputs(bounds=[
            {"component": "total_assets", "horizon_weeks": 5, "low": -1, "high": 1}]))


# --- audit rulings -----------------------------------------------------------

def test_audit_a_k2_forecast_renders_unavailable_without_numbers():
    real = json.loads(T09_PATH.read_text(encoding="utf-8"))
    day = date(2026, 10, 26)
    views = _compose(day=day, env=_env(day), t09=real)["statistical_forecast"]
    assert views["package_as_of"] == "2026-10-19"
    assert all(c["estimate_type"] == "unavailable" for c in views["cells"])
    dump = json.dumps(views, sort_keys=True)
    for word in ("best_baseline", "seasonal_calendar", "persistence", "announced_only",
                 "relative_gain", "gain_ci", "mean_width", "abstention_reason",
                 "interval", "reason"):
        assert word not in dump
    for cell in views["cells"]:
        assert _walk_numbers(cell) == [cell["horizon_weeks"]]


def test_audit_b_k1_outlook_types_and_live_probe_degraded(tmp_path):
    probe = outlook_snapshot(tmp_path, as_of=date(2026, 10, 26))
    assert probe["headline"]["state"] == "data_degraded"
    day = date(2026, 10, 26)
    views = _compose(day=day, env=_env(day), oi={"probe": probe})["conditional_outlook"]
    assert views == {"status": "data_degraded", "reason_key": "h41_table5_owner_loader_missing"}
    full = _compose(day=day, env=_env(day), oi={"probe": probe})
    dump = json.dumps(full, sort_keys=True)
    for word in ("gaps", "not found", "parquet"):
        assert word not in dump


def test_audit_c_no_path_claim_allowed_read():
    import engine.global_liquidity_views as views_module
    import scripts.build_global_liquidity_transmission as producer_module
    for path in (Path(views_module.__file__), Path(producer_module.__file__)):
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"[\"']path_claim_allowed[\"']\s*\]", text)
        assert not re.search(r"\.get\(\s*[\"']path_claim_allowed", text)


def test_audit_d_cross_repo_none_is_owner_named_unavailable():
    views = _compose()
    expected = {
        "status": "unavailable",
        "reason_key": "science_results_not_published_to_product_plane",
        "owner": CROSS_REPO_OWNER,
    }
    assert views["transmission"] == expected
    assert views["repricing_evidence"] == expected


def test_audit_e_regions_blocked_is_missing_input_and_cardless_targets_missing():
    views = _compose(cross=_cross())["transmission"]
    regions = {r["region"]: r for r in views["regions"]}
    assert regions["us"]["state"] == "available"
    assert regions["eu"]["state"] == "missing_input"
    assert regions["eu"]["owner"] == "ecb data seat"
    targets = {t["target"]: t for t in views["targets"]}
    for name in CARDLESS_TARGETS:
        assert targets[name]["state"] == "missing"
        assert set(targets[name]) == {"target", "state"}
    assert targets["spy"]["state"] == "available"

    with pytest.raises(ViewsContractError):
        _compose(cross=_cross(transmission=_xblock(regions=[
            {"region": "eu", "state": "missing_input", "owner": ""}])))


def test_audit_f_announced_only_comparator_is_refused():
    block = _xblock(baseline_comparison={"comparator": "announced_only"})
    with pytest.raises(ViewsContractError):
        _compose(cross=_cross(transmission=block))
    block2 = _xblock(baseline_comparison={"comparator": "identified_effect_vs_announced"})
    views = _compose(cross=_cross(transmission=block2))["transmission"]
    dump = json.dumps(views, sort_keys=True)
    assert "announced_only" not in dump


def test_audit_g_no_confidence_key_attaches_to_views():
    views = _compose(
        history=[_hist("2026-09-01")],
        t09=_pkg(cells=[_issued_cell()]),
        cross=_cross(),
        oi=_outlook_inputs(),
    )
    dump = json.dumps(views, sort_keys=True)
    assert '"confidence"' not in dump
    assert "glt_confidence" not in dump


def test_views_are_json_safe_and_deterministic():
    a = _compose(
        history=[_hist("2026-09-01")],
        t09=_pkg(cells=[_issued_cell()]),
        cross=_cross(),
        oi=_outlook_inputs(),
    )
    b = _compose(
        history=[_hist("2026-09-01")],
        t09=_pkg(cells=[_issued_cell()]),
        cross=_cross(),
        oi=_outlook_inputs(),
    )
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)

    assumptions = copy.deepcopy(make_assumptions())
    assumptions[0]["value"] = Decimal(-5_000)
    with pytest.raises(ViewsContractError):
        _compose(oi=_outlook_inputs(assumptions=assumptions))


def test_compose_views_does_not_mutate_inputs():
    history = [_hist("2026-09-01")]
    t09 = _pkg(cells=[_issued_cell()])
    cross = _cross()
    oi = _outlook_inputs(bounds=[
        {"component": "total_assets", "horizon_weeks": 4, "low": -25_000, "high": -15_000}])
    env = _env()
    snapshots = tuple(copy.deepcopy(x) for x in (env, history, t09, cross, oi))
    _compose(history=history, t09=t09, cross=cross, oi=oi, env=env)
    assert (env, history, t09, cross, oi) == snapshots


# --- producer attach ---------------------------------------------------------

def _stub_payload(asof="2026-10-07"):
    return {
        "meta": {
            "schema": "global_liquidity_transmission.v1",
            "source_snapshot_hash": "a" * 64,
            "generated_at": "2026-10-08T06:00:00Z",
        },
        "state": {"asof": asof},
        "quality": {"status": "ok"},
        "freshness": {"asof": asof},
    }


@pytest.fixture
def producer(tmp_path, monkeypatch):
    import scripts.build_global_liquidity_transmission as producer_module
    for name in ("CONTRACT_PATH", "HISTORY_PATH", "HISTORY_META_PATH", "COMPARISON_PATH"):
        monkeypatch.setattr(producer_module, name, tmp_path / name.lower())
    monkeypatch.setattr(producer_module, "load_producer_config", lambda: {})
    monkeypatch.setattr(producer_module.store, "read", lambda provider, sid: None)
    payload = _stub_payload()

    def _stub_contract(**kwargs):
        copied = copy.deepcopy(payload)
        copied["meta"]["generated_at"] = kwargs["generated_at"].isoformat()
        return copied, None

    monkeypatch.setattr(producer_module, "build_contract", _stub_contract)
    return producer_module, tmp_path


def test_producer_attaches_views_beside_envelope(producer):
    module, tmp_path = producer
    out = tmp_path / "replay.json"
    module.build(asof="2026-10-07", out=str(out))
    written = json.loads(out.read_text(encoding="utf-8"))
    assert set(written) == {"meta", "state", "quality", "freshness", "views"}
    assert written["state"] == _stub_payload()["state"]
    assert written["quality"] == _stub_payload()["quality"]
    assert written["freshness"] == _stub_payload()["freshness"]
    assert written["meta"]["source_snapshot_hash"] == "a" * 64

    views = written["views"]
    assert views["view_version"] == "glt_views_v1"
    assert views["authority"] == AUTHORITY
    assert views["as_of"] == "2026-10-07"
    assert views["transmission"] == {
        "status": "unavailable",
        "reason_key": "science_results_not_published_to_product_plane",
        "owner": CROSS_REPO_OWNER,
    }
    assert views["replay"]["status"] == "no_history"
    assert views["conditional_outlook"]["status"] == "data_degraded"
    validate_views(views)


def test_producer_missing_t09_yields_unavailable(producer, monkeypatch, tmp_path):
    module, _ = producer
    monkeypatch.setattr(module, "T09_RESULT_PATH", tmp_path / "missing.json")
    out = tmp_path / "replay.json"
    module.build(asof="2026-10-07", out=str(out))
    views = json.loads(out.read_text(encoding="utf-8"))["views"]
    assert views["statistical_forecast"] == {
        "status": "unavailable",
        "reason_key": "forecast_package_missing",
    }


def test_producer_unreadable_t09_yields_unavailable(producer, monkeypatch, tmp_path):
    module, _ = producer
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(module, "T09_RESULT_PATH", bad)
    out = tmp_path / "replay.json"
    module.build(asof="2026-10-07", out=str(out))
    views = json.loads(out.read_text(encoding="utf-8"))["views"]
    assert views["statistical_forecast"] == {
        "status": "unavailable",
        "reason_key": "forecast_package_unreadable",
    }


def test_producer_compose_failure_yields_views_compose_failed_and_no_print(producer, monkeypatch, capsys):
    module, tmp_path = producer
    out1 = tmp_path / "replay1.json"
    module.build(asof="2026-10-07", out=str(out1))
    clean = capsys.readouterr().out

    def _boom(*args, **kwargs):
        raise RuntimeError("compose exploded")

    monkeypatch.setattr(module, "compose_views", _boom)
    out2 = tmp_path / "replay2.json"
    module.build(asof="2026-10-07", out=str(out2))
    failed = capsys.readouterr().out

    normalize = lambda text: re.sub(r"wall_s=[0-9.]+", "wall_s=X", text)
    assert normalize(failed) == normalize(clean)
    views = json.loads(out2.read_text(encoding="utf-8"))["views"]
    expected = {"status": "unavailable", "reason_key": "views_compose_failed"}
    for name in VIEW_NAMES:
        assert views[name] == expected
    assert views["as_of"] == "2026-10-07"
    validate_views(views)

    assert failed_views("2026-10-07") == views
    assert failed_views(None)["as_of"] is None
    validate_views(failed_views("not-a-date"))
