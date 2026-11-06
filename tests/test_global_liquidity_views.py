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
    # O1: an all-rejected package is a readable package (status) whose section
    # disposition is "unavailable"; nothing reads it as an available forecast.
    assert views["status"] == "available"
    assert views["disposition"] == "unavailable"
    assert views["disposition_basis"] == "no_issued_cell"
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


def test_o1_forecast_section_disposition_follows_issued_cells():
    full = _compose(t09=_pkg(cells=[_issued_cell()]))["statistical_forecast"]
    assert full["status"] == "available"
    assert full["disposition"] == "available"
    assert "disposition_basis" not in full
    rejected = _cell(disposition="withheld_no_gain")
    none = _compose(t09=_pkg(cells=[rejected]))["statistical_forecast"]
    assert none["status"] == "available"
    assert none["disposition"] == "unavailable"
    assert none["disposition_basis"] == "no_issued_cell"
    assert none["cells"][0]["estimate_type"] == "unavailable"
    for cell in none["cells"]:
        assert _walk_numbers(cell) == [cell["horizon_weeks"]]
    validate_views(_compose(t09=_pkg(cells=[rejected])))


def test_o2_rule_c_path_claim_allowed_is_refused_at_every_input_depth():
    # Rule c: no input may carry path_claim_allowed, at any depth, under any
    # value; the composer refuses rather than reading it.
    for value in (True, False, None, 1):
        for key in ("anchor", "announcements", "assumptions"):
            oi = copy.deepcopy(_outlook_inputs())
            node = oi[key]
            node = node[0] if isinstance(node, list) else node
            node["path_claim_allowed"] = value
            with pytest.raises(ViewsContractError, match="refused key"):
                _compose(oi=oi)
    # and the composed document never carries the key
    dump = json.dumps(_compose(oi=_outlook_inputs()), sort_keys=True)
    assert "path_claim_allowed" not in dump


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


# --- T22 M2 projection -------------------------------------------------------
#
# The projection under test lives in the Liquidity & Central Banks composer:
# engine/market_os/macro_workspaces/liquidity_central_banks.py::_glt_view_rows
# turns the M1 display-only ``views`` block into workspace metric rows, the
# presenter hook lib/macro_suite_view.py::_glt_view_note supplies the visible
# note, and lib/macro_suite_labels.py carries every reviewed EN/ZH string.

from collections.abc import Mapping as _ViewMapping  # noqa: E402

from tests.test_macro_workspace_liquidity_central_banks import (  # noqa: E402
    BASE_LCB_METRIC_COUNT,
    BUILT_AT,
    ROOT,
    _base_cb_desk,
    _base_glt,
    _base_hist,
    _t21_render_html,
)
from engine.market_os.macro_workspaces import (  # noqa: E402
    contract,
    liquidity_central_banks,
)
from lib import macro_suite_labels as labels_module  # noqa: E402
from lib import macro_suite_view as suite_view  # noqa: E402
from scripts.check_macro_command_copy import find_violations  # noqa: E402
from scripts.count_macro_command_machine_text import count_file  # noqa: E402

STALE_BUILT_AT = "2026-10-17T00:00:00Z"  # 13 days past the 2026-09-04 as-of
LIVE_BUILT_AT = "2026-10-27T00:00:00Z"   # one day past the 2026-10-26 live day


def _lcb_with(views, built_at=BUILT_AT):
    """A finalized LCB snapshot whose glt envelope carries ``views``."""
    g = copy.deepcopy(_base_glt())
    if views.get("as_of") is not None:
        g["state"]["asof"] = views["as_of"]
    g["views"] = views
    return contract.finalize(liquidity_central_banks.compose(
        g, _base_cb_desk(), _base_hist(), built_at=built_at))


def _rows(snap):
    return {m["metric_id"]: m for m in snap["metrics"]["items"]
            if str(m["metric_id"]).startswith("glt_view_")}


def _view_rows(snap, tmp_path=None):
    """Presenter rows for the glt_view_ metrics, built exactly as the page does."""
    from scripts import build_macro_suite_pages as builder
    artifact = {
        "path": "macrodata/workspaces/liquidity_central_banks/US/latest.json",
        "manifest_path": "macrodata/workspaces/manifest.json",
        "sha256": "fixture",
        "bytes": 1,
        "min_client_contract": builder.MIN_CLIENT_CONTRACT,
    }
    view = suite_view.build_view(
        snap, page_built_at=BUILT_AT, artifact=artifact,
        layout=builder._layout_for("liquidity_central_banks"))
    return [r for r in view["metrics"]
            if str(r.get("metric_id", "")).startswith("glt_view_")]


def _prow(snap, tmp_path=None):
    return {r["metric_id"]: r for r in _view_rows(snap, tmp_path)}


def _lawful_regions():
    """The M1 ``eu`` region sits outside the projection whitelist; this is the
    lawful five-region fixture named in the M2 packet (W5)."""
    return [
        {"region": "us", "state": "blocked", "owner": CROSS_REPO_OWNER},
        {"region": "euro_area", "state": "blocked", "owner": "ecb data seat"},
        {"region": "japan", "state": "missing_input", "owner": CROSS_REPO_OWNER},
        {"region": "china", "state": "available", "owner": CROSS_REPO_OWNER},
        {"region": "hong_kong", "state": "missing_input", "owner": CROSS_REPO_OWNER},
    ]


def _lawful_xblock(**over):
    return _xblock(regions=_lawful_regions(), **over)


def _lawful_cross():
    return _cross(
        transmission=_lawful_xblock(),
        repricing=_lawful_xblock(label="identified_effect"),
    )


_FULL_BOUNDS = [
    {"component": "treasury_general_account", "horizon_weeks": 4,
     "low": 840_000, "high": 860_000},
    {"component": "reverse_repo_others", "horizon_weeks": 4,
     "low": 140_000, "high": 160_000},
]


def _full_views(**over):
    kw = dict(
        history=[_hist("2026-09-01")],
        t09=_pkg(cells=[_issued_cell(),
                        _cell(horizon=8, disposition="withheld_no_gain")]),
        cross=_lawful_cross(),
        oi=_outlook_inputs(bounds=_FULL_BOUNDS),
    )
    kw.update(over)
    return _compose(**kw)


def _live_views(tmp_path):
    day = date(2026, 10, 26)
    return _compose(
        day=day, env=_env(day),
        t09=json.loads(T09_PATH.read_text(encoding="utf-8")),
        oi={"probe": outlook_snapshot(tmp_path, as_of=day)},
    )


def _visible_texts(row):
    for field in ("label", "value", "absence", "unit", "basis", "freshness",
                  "sample_note"):
        pair = row.get(field)
        if isinstance(pair, _ViewMapping):
            for lang in ("en", "zh"):
                text = pair.get(lang)
                if isinstance(text, str) and text:
                    yield field, lang, text


FORBIDDEN_VIEW_WORDS = (
    "buy", "sell", "long", "short", "overweight", "underweight", "catch-up",
    "upside", "laggard", "target", "买入", "卖出", "做多", "做空", "补涨",
    "上行空间", "目标价", "目标",
)


def test_t22_journey_a_no_views_keeps_t21_rows_identical():
    g = copy.deepcopy(_base_glt())
    g["state"]["asof"] = AS_OF.isoformat()
    g["views"] = _full_views()
    with_views = contract.finalize(liquidity_central_banks.compose(
        g, _base_cb_desk(), _base_hist(), built_at=BUILT_AT))
    g2 = copy.deepcopy(g)
    del g2["views"]
    without = contract.finalize(liquidity_central_banks.compose(
        g2, _base_cb_desk(), _base_hist(), built_at=BUILT_AT))
    assert len(without["metrics"]["items"]) == BASE_LCB_METRIC_COUNT
    assert _rows(without) == {}
    assert without["metrics"]["items"] == \
        with_views["metrics"]["items"][:BASE_LCB_METRIC_COUNT]
    assert _rows(with_views)
    assert len(with_views["metrics"]["items"]) == \
        BASE_LCB_METRIC_COUNT + len(_rows(with_views))


def test_t22_journey_b_announced_and_conditional_render_distinct_labels(tmp_path):
    views = _full_views()
    snap = _lcb_with(views)
    rows = _rows(snap)
    ann = rows["glt_view_outlook_treasury_general_account_h4"]
    cond = rows["glt_view_outlook_reverse_repo_others_h4"]
    assert ann["value"] == 850_000 and ann["basis"] == "glt_est_announced_scenario"
    assert cond["value"] == 150_000 and cond["basis"] == "glt_est_conditional_accounting"
    assert rows["glt_view_outlook_residual"]["value"] is None
    prow = _prow(snap)
    p_ann = prow["glt_view_outlook_treasury_general_account_h4"]
    p_cond = prow["glt_view_outlook_reverse_repo_others_h4"]
    assert p_ann["basis"]["en"] != p_cond["basis"]["en"]
    assert p_ann["sample_note"]["en"] != p_cond["sample_note"]["en"]
    assert p_ann["sample_note"]["zh"] != p_cond["sample_note"]["zh"]
    assert p_ann["sample_note"]["en"].startswith("Announced scenario")
    assert p_cond["sample_note"]["en"].startswith("Conditional accounting")
    html = _t21_render_html(snap, tmp_path)
    g2 = copy.deepcopy(_base_glt())
    g2["state"]["asof"] = views["as_of"]
    html0 = _t21_render_html(contract.finalize(liquidity_central_banks.compose(
        g2, _base_cb_desk(), _base_hist(), built_at=BUILT_AT)), tmp_path)
    assert 'type="range"' not in html
    # No NEW input, script or style: the page chrome (nav search) is shared.
    assert html.count("<input") == html0.count("<input")
    assert html.count("<script") == html0.count("<script")
    assert html.count("<style") == html0.count("<style")


def test_t22_journey_c_narrowed_evidence_shows_word_not_number(tmp_path):
    views = _compose(
        oi=_outlook_inputs(),
        cross=_cross(
            transmission=_xblock(disposition="narrowed", regions=_lawful_regions()),
            repricing=_lawful_xblock(),
        ),
    )
    snap = _lcb_with(views)
    rows = _rows(snap)
    prow = _prow(snap)
    note = prow["glt_view_transmission"]["sample_note"]
    assert note["en"].startswith("Observed association, not a causal effect. Narrowed")
    assert note["zh"].startswith("观察到的关联，并非因果效应。新证据已将其收窄")
    assert all(m["value"] is None for mid, m in rows.items()
               if mid.startswith("glt_view_transmission"))
    assert rows["glt_view_transmission"]["basis"] == "glt_evidence_narrowed"
    html = _t21_render_html(snap, tmp_path)
    low = html.lower()
    assert "catch-up" not in low and "upside" not in low


def test_t22_journey_d_regions_missing_input_and_funds_missing(tmp_path):
    views = _compose(oi=_outlook_inputs(), cross=_lawful_cross())
    snap = _lcb_with(views)
    rows = _rows(snap)
    prow = _prow(snap)
    for name in ("us", "euro_area", "japan", "china", "hong_kong"):
        assert f"glt_view_transmission_region_{name}" in rows
        assert f"glt_view_repricing_region_{name}" in rows
    us_note = prow["glt_view_transmission_region_us"]["sample_note"]
    assert us_note["en"] == (
        "Missing input: this region's local inputs are not supplied. "
        "Owner: the liquidity research lab.")
    eu_note = prow["glt_view_transmission_region_euro_area"]["sample_note"]
    assert eu_note["en"] == (
        "Missing input: this region's local inputs are not supplied. "
        "The owner is named in the research record.")
    china_note = prow["glt_view_transmission_region_china"]["sample_note"]
    assert china_note["en"] == "Inputs on file; no regional value is shown on this page."
    assert rows["glt_view_transmission_region_china"]["value"] is None
    for fund in CARDLESS_TARGETS:
        assert f"glt_view_transmission_fund_{fund}" in rows
        assert f"glt_view_repricing_fund_{fund}" in rows
    assert "glt_view_transmission_fund_spy" not in rows
    assert "glt_view_repricing_fund_spy" not in rows
    for mid, m in rows.items():
        if "_region_" in mid or "_fund_" in mid:
            assert m["value"] is None
    html = _t21_render_html(snap, tmp_path)
    assert "ecb data seat" not in html.lower()


def test_t22_journey_e_stale_page_turns_simulated_into_stale():
    views = _full_views()
    fresh = _lcb_with(views, built_at=BUILT_AT)
    stale = _lcb_with(views, built_at=STALE_BUILT_AT)
    for snap, expected in ((fresh, "SIMULATED"), (stale, "STALE_SOURCE")):
        rows = _rows(snap)
        valued = [m for mid, m in rows.items()
                  if mid.startswith("glt_view_outlook") and m["value"] is not None]
        assert valued
        assert all(m["freshness"] == expected for m in valued)
    for snap in (fresh, stale):
        rows = _rows(snap)
        assert all(m["freshness"] not in ("CURRENT", "LATE_WITHIN_TOLERANCE")
                   for m in rows.values())
        for r in _view_rows(snap):
            assert r["freshness_tone"] != "ok"
    assert all(m["freshness"] == "HISTORICAL_AS_KNOWN"
               for mid, m in _rows(stale).items()
               if mid.startswith("glt_view_replay"))


def test_t22_journey_f_replay_as_known_and_corrections():
    hist = [
        _hist("2026-09-01",
              corrections=[{"field": "tga", "corrected_at": "2026-09-02",
                            "note_key": "source_revised"}]),
        _hist("2026-08-28"),
    ]
    snap = _lcb_with(_full_views(history=hist))
    rows = _rows(snap)
    prow = _prow(snap)
    tga1 = rows["glt_view_replay_1_tga"]
    assert tga1["value"] == 800_000
    assert tga1["revised_at"] == "2026-09-02"
    assert tga1["calculation_as_of"] == "2026-09-01"
    assert prow["glt_view_replay_1_tga"]["sample_note"]["en"] == (
        "As known on 1 September 2026. Corrected on 2 September 2026 after a "
        "source revision.")
    assert prow["glt_view_replay_2_reserves"]["sample_note"]["en"] == (
        "As known on 28 August 2026.")
    snap2 = _lcb_with(_full_views(history=None))
    rows2 = _rows(snap2)
    replay_ids = [mid for mid in rows2 if mid.startswith("glt_view_replay")]
    assert replay_ids == ["glt_view_replay"]
    assert rows2["glt_view_replay"]["null_reason"] == "INSUFFICIENT_HISTORY"
    assert _prow(snap2)["glt_view_replay"]["sample_note"]["en"].startswith(
        "No history: past issues of these views are not recorded yet")
    keep = lambda d: {mid: m for mid, m in d.items()
                      if not mid.startswith("glt_view_replay")}  # noqa: E731
    assert keep(rows) == keep(rows2)


def test_t22_c37_estimate_type_labels_are_distinct():
    snap = _lcb_with(_full_views())
    rows = _rows(snap)
    prow = _prow(snap)
    texts = {
        "observed": prow["glt_view_replay_1_reserves"]["basis"],
        "announced": prow["glt_view_outlook_treasury_general_account_h4"]["basis"],
        "conditional": prow["glt_view_outlook_reverse_repo_others_h4"]["basis"],
        "forecast_rejected": prow["glt_view_forecast_reserves_h8"]["basis"],
        "forecast_not_cleared": prow["glt_view_forecast_reserves_h4"]["basis"],
        "association": prow["glt_view_transmission"]["sample_note"],
        "identified": prow["glt_view_repricing"]["sample_note"],
        "residual": prow["glt_view_outlook_residual"]["basis"],
    }
    assert texts["observed"]["en"] == "Observed, as published then"
    assert texts["announced"]["en"] == "Announced scenario: follows a published schedule"
    assert texts["conditional"]["en"] == "Conditional accounting: follows a stated assumption"
    assert texts["forecast_rejected"]["en"] == "Forecast rejected"
    assert texts["forecast_not_cleared"]["en"] == "Not cleared for display"
    assert texts["association"]["en"].startswith("Observed association, not a causal effect.")
    assert texts["identified"]["en"].startswith("Causal-effect study.")
    assert texts["residual"]["en"] == "Unavailable: no value"
    en = [p["en"] for p in texts.values()]
    zh = [p["zh"] for p in texts.values()]
    assert len(set(en)) == len(en)
    assert len(set(zh)) == len(zh)
    assert all(m["value"] is None for mid, m in rows.items()
               if mid == "glt_view_outlook_residual")


def test_t22_c37_number_without_estimate_type_is_refused():
    views = _compose(oi=_outlook_inputs())
    views["conditional_outlook"]["components"]["treasury_general_account"][
        "points"][0].pop("estimate_type")
    snap = _lcb_with(views)
    rows = _rows(snap)
    assert len(rows) == 5
    assert all(m["value"] is None for mid, m in rows.items()
               if mid.startswith("glt_view_outlook"))
    assert rows["glt_view_outlook"]["transformation"] == \
        "glt_view_note.reason.views_contract_refused"


def test_t22_c38_six_states_are_distinct(tmp_path):
    partial_assumptions = [
        {"id": "qt", "component": "total_assets", "kind": "weekly_delta",
         "value": -5000},
        {"id": "hold-tga", "component": "treasury_general_account",
         "kind": "hold_level"},
        {"id": "hold-rrp-foreign", "component": "reverse_repo_foreign_official",
         "kind": "hold_level"},
        {"id": "hold-frn", "component": "federal_reserve_notes",
         "kind": "hold_level"},
        {"id": "hold-other", "component": "other_nonreserve_and_capital",
         "kind": "hold_level"},
    ]
    views = _compose(
        history=[_hist("2026-09-01",
                       corrections=[{"field": "reserves",
                                     "corrected_at": "2026-09-02",
                                     "note_key": "source_revised"}])],
        t09=_pkg(day="2026-09-10"),
        cross=_lawful_cross(),
        oi=_outlook_inputs(assumptions=partial_assumptions),
    )
    views["conditional_outlook"]["components"]["federal_reserve_notes"][
        "points"][0]["level"] = 0
    snap = _lcb_with(views)
    rows = _rows(snap)
    prow = _prow(snap)
    missing_note = prow["glt_view_transmission_fund_gld"]["sample_note"]["en"]
    assert missing_note.startswith("Missing: no regional study design on file")
    zero_row = prow["glt_view_outlook_federal_reserve_notes_h4"]
    assert zero_row["value"] == {"en": "0", "zh": "0"}
    assert zero_row["absence"] is None
    partial_row = prow["glt_view_outlook_treasury_general_account_h4"]
    assert partial_row["presence"]["en"] == "Partial"
    assert "Some lines have no path, so bank reserves are not shown." in \
        partial_row["sample_note"]["en"]
    assert "glt_view_outlook_reverse_repo_others" in rows
    assert rows["glt_view_outlook_reverse_repo_others"]["null_reason"] == "NOT_COVERED"
    revised_row = prow["glt_view_replay_1_reserves"]
    assert "Corrected on 2 September 2026" in revised_row["sample_note"]["en"]
    assert rows["glt_view_replay_1_reserves"]["revised_at"] == "2026-09-02"
    expired_row = prow["glt_view_forecast"]
    assert "dated after this page's cutoff" in expired_row["sample_note"]["en"]
    assert expired_row["freshness"]["en"] == "Not yet released"
    views_warm = _compose(history=[], t09=_pkg(), cross=_lawful_cross(),
                          oi=_outlook_inputs())
    prow_warm = _prow(_lcb_with(views_warm))
    warm_note = prow_warm["glt_view_replay"]["sample_note"]["en"]
    assert warm_note.startswith("Warm-up: the issue record has started")
    markers = {
        "missing": missing_note,
        "zero": zero_row["value"]["en"] + "/" + zero_row["presence"]["en"],
        "partial": partial_row["presence"]["en"] + partial_row["sample_note"]["en"],
        "warmup": warm_note,
        "revised": revised_row["sample_note"]["en"],
        "expired": expired_row["sample_note"]["en"] + expired_row["freshness"]["en"],
    }
    values = list(markers.values())
    assert len(set(values)) == len(values)


def test_t22_c39_replay_values_are_as_known_not_current(tmp_path):
    hist = [
        _hist("2026-09-01"),
        _hist("2026-08-28",
              components={"reserves": 2_900_000, "tga": 700_000, "rrp": 500_000}),
    ]
    views = _full_views(history=hist)
    snap = _lcb_with(views)
    rows = _rows(snap)
    assert rows["glt_view_replay_1_reserves"]["value"] == 3_000_000
    assert rows["glt_view_replay_2_reserves"]["value"] == 2_900_000
    current_values = {m["value"] for m in snap["metrics"]["items"]
                      if not str(m["metric_id"]).startswith("glt_view_")}
    assert 3_000_000 not in current_values
    assert 2_900_000 not in current_values
    for mid, m in rows.items():
        if mid.startswith("glt_view_replay"):
            assert m["calculation_as_of"] == (
                "2026-09-01" if "_1_" in mid else "2026-08-28")
            assert m["freshness"] == "HISTORICAL_AS_KNOWN"
    refused = _full_views()
    refused["replay"]["rows"][0]["estimate_types_as_known"]["reserves"] = \
        "statistical_forecast"
    rows2 = _rows(_lcb_with(refused))
    assert all(m["value"] is None for mid, m in rows2.items()
               if mid.startswith("glt_view_replay"))


def test_t22_no_total_interval():
    snap = _lcb_with(_full_views())
    rows = _rows(snap)
    assert rows["glt_view_outlook_treasury_general_account_h4_low"]["value"] == 840_000
    assert rows["glt_view_outlook_treasury_general_account_h4_high"]["value"] == 860_000
    assert rows["glt_view_outlook_reverse_repo_others_h4_low"]["value"] == 140_000
    assert rows["glt_view_outlook_reverse_repo_others_h4_high"]["value"] == 160_000
    assert not any(mid.startswith("glt_view_outlook_reserves") and
                   mid.endswith(("_low", "_high")) for mid in rows)
    assert not any("total_interval" in mid or "_sum" in mid for mid in rows)
    sum_lows = 840_000 + 140_000
    sum_highs = 860_000 + 160_000
    assert all(m["value"] not in (sum_lows, sum_highs)
               for mid, m in rows.items() if mid.startswith("glt_view_outlook"))


def test_t22_bounds_carry_no_probability_interpretation():
    snap = _lcb_with(_full_views())
    prow = _prow(snap)
    bounds_rows = [r for r in prow.values()
                   if r["metric_id"].endswith(("_low", "_high"))]
    assert bounds_rows
    for r in bounds_rows:
        assert "not probability" in r["basis"]["en"]
        assert "并非概率" in r["basis"]["zh"]
        assert "not probability" in r["sample_note"]["en"]
        assert "并非概率" in r["sample_note"]["zh"]
    for r in prow.values():
        if r["metric_id"].endswith(("_low", "_high")):
            continue
        for _field, _lang, text in _visible_texts(r):
            assert "probab" not in text.lower()
            assert "概率" not in text


def test_t22_forbidden_words_absent_from_view_rows(tmp_path):
    refused = _compose(oi=_outlook_inputs())
    refused["conditional_outlook"]["components"]["total_assets"][
        "points"][0].pop("estimate_type")
    variants = {
        "full": _full_views(),
        "live": _live_views(tmp_path),
        "refused": refused,
    }
    for name, views in variants.items():
        snap = _lcb_with(views, built_at=LIVE_BUILT_AT if name == "live"
                         else BUILT_AT)
        prow = _view_rows(snap)
        assert prow
        for r in prow:
            for _field, _lang, text in _visible_texts(r):
                low = text.lower()
                for word in FORBIDDEN_VIEW_WORDS:
                    assert word not in low, (name, r["metric_id"], word)


def test_t22_live_shape_renders_five_family_rows(tmp_path):
    views = _live_views(tmp_path)
    snap = _lcb_with(views, built_at=LIVE_BUILT_AT)
    rows = _rows(snap)
    prow = _prow(snap)
    assert set(rows) == {
        "glt_view_outlook", "glt_view_forecast", "glt_view_transmission",
        "glt_view_repricing", "glt_view_replay",
    }
    assert all(m["value"] is None for m in rows.values())
    assert "Data degraded" in prow["glt_view_outlook"]["sample_note"]["en"]
    forecast = prow["glt_view_forecast"]
    # The real study package yields one shared disposition at every cell:
    # rejected (withheld, no model beat the simple baselines).
    assert forecast["basis"]["en"] == "Forecast rejected"
    assert forecast["sample_note"]["en"] == (
        "Unavailable: rejected at every tested horizon — no forecast model beat "
        "the simple baselines.")
    assert "held by the liquidity research lab" in \
        prow["glt_view_transmission"]["sample_note"]["en"]
    assert "held by the liquidity research lab" in \
        prow["glt_view_repricing"]["sample_note"]["en"]
    assert prow["glt_view_replay"]["sample_note"]["en"].startswith(
        "No history: past issues of these views")


def test_t22_end_to_end_render_is_clean(tmp_path):
    views = _full_views()
    snap = _lcb_with(views)
    labels_module.reset_unknown_tokens()
    html = _t21_render_html(snap, tmp_path)
    out = Path(tmp_path) / "m2_e2e.html"
    out.write_text(html, encoding="utf-8")
    assert find_violations(html) == []
    assert count_file(out)["top"]["strict"] == 0
    # The base T21 page itself records pre-existing unknown vocabulary tokens;
    # the projection must add none of its own.
    for token in labels_module.unknown_tokens():
        assert not token.startswith(("metric:glt_view", "basis:glt_est",
                                     "basis:glt_forecast", "basis:glt_evidence",
                                     "basis:glt_region", "basis:glt_fund"))
        assert "glt_view_note:" not in token
    prow = _view_rows(snap)
    assert prow
    assert all(r["sample_note"] is not None for r in prow)


def _def_id_resolves(def_id, views):
    """The W2.7 linkage grammar, resolved against the views dict."""
    if not isinstance(views, _ViewMapping) or not isinstance(def_id, str):
        return False

    def _block(name):
        b = views.get(name)
        return b if isinstance(b, _ViewMapping) else None

    m = re.match(r"^views\.(conditional_outlook|statistical_forecast|"
                 r"transmission|repricing_evidence|replay)$", def_id)
    if m:
        return _block(m.group(1)) is not None
    outlook = _block("conditional_outlook")
    if outlook is None:
        return False
    m = re.match(r"^views\.conditional_outlook\.components\.([a-z_]+)$", def_id)
    if m:
        comps = outlook.get("components")
        return isinstance(comps, _ViewMapping) and m.group(1) in comps
    m = re.match(r"^views\.conditional_outlook\.components\.([a-z_]+)"
                 r"\.points\[h=(\d+)\]\.level$", def_id)
    if m:
        comps = outlook.get("components") or {}
        comp = comps.get(m.group(1))
        if not isinstance(comp, _ViewMapping):
            return False
        return any(isinstance(p, _ViewMapping) and p.get("horizon_weeks") == int(m.group(2))
                   and "level" in p for p in comp.get("points") or [])
    m = re.match(r"^views\.conditional_outlook\.components\.([a-z_]+)"
                 r"\.points\[h=(\d+)\]\.scenario_bounds\.(low|high)$", def_id)
    if m:
        comps = outlook.get("components") or {}
        comp = comps.get(m.group(1))
        if not isinstance(comp, _ViewMapping):
            return False
        point = next((p for p in comp.get("points") or []
                      if isinstance(p, _ViewMapping)
                      and p.get("horizon_weeks") == int(m.group(2))), None)
        bounds = point.get("scenario_bounds") if isinstance(point, _ViewMapping) else None
        return isinstance(bounds, _ViewMapping) and m.group(3) in bounds
    if def_id == "views.conditional_outlook.reserves":
        return isinstance(outlook.get("reserves"), _ViewMapping)
    m = re.match(r"^views\.conditional_outlook\.reserves"
                 r"\.points\[h=(\d+)\]\.level$", def_id)
    if m:
        reserves = outlook.get("reserves")
        if not isinstance(reserves, _ViewMapping):
            return False
        return any(isinstance(p, _ViewMapping) and p.get("horizon_weeks") == int(m.group(1))
                   and "level" in p for p in reserves.get("points") or [])
    if def_id == "views.conditional_outlook.statistical_residual":
        return "statistical_residual" in outlook
    forecast = _block("statistical_forecast")
    if def_id == "views.statistical_forecast.cells":
        return forecast is not None and isinstance(forecast.get("cells"), list)
    m = re.match(r"^views\.statistical_forecast\.cells"
                 r"\[target=([a-z]+),h=(\d+)\]\.disposition$", def_id)
    if m:
        cells = forecast.get("cells") if forecast else None
        return isinstance(cells, list) and any(
            isinstance(c, _ViewMapping) and c.get("target") == m.group(1)
            and c.get("horizon_weeks") == int(m.group(2))
            and "disposition" in c for c in cells)
    m = re.match(r"^views\.(transmission|repricing_evidence)"
                 r"\.regions\[region=([a-z_]+)\]\.state$", def_id)
    if m:
        block = _block(m.group(1))
        regions = block.get("regions") if block else None
        return isinstance(regions, list) and any(
            isinstance(r, _ViewMapping) and r.get("region") == m.group(2)
            and "state" in r for r in regions)
    m = re.match(r"^views\.(transmission|repricing_evidence)"
                 r"\.targets\[target=([a-z]+)\]\.state$", def_id)
    if m:
        block = _block(m.group(1))
        entries = block.get("targets") if block else None
        return isinstance(entries, list) and any(
            isinstance(e, _ViewMapping) and e.get("target") == m.group(2)
            and "state" in e for e in entries)
    m = re.match(r"^views\.replay\.rows\[known_at=([0-9-]+)\]"
                 r"\.components_as_known\.(reserves|tga|rrp)$", def_id)
    if m:
        block = _block("replay")
        for row in (block.get("rows") if block else None) or []:
            if isinstance(row, _ViewMapping) and row.get("known_at") == m.group(1):
                comps = row.get("components_as_known")
                return isinstance(comps, _ViewMapping) and m.group(2) in comps
        return False
    return False


def test_t22_definition_ids_resolve_in_views(tmp_path):
    for views, built in ((_full_views(), BUILT_AT),
                         (_live_views(tmp_path), LIVE_BUILT_AT),
                         (failed_views(AS_OF), BUILT_AT),
                         (_full_views(), BUILT_AT)):
        snap = _lcb_with(views, built_at=built)
        rows = _rows(snap)
        assert rows
        for mid, m in rows.items():
            assert _def_id_resolves(m["definition_id"], views), (mid, m["definition_id"])


def test_t22_as_of_mismatch_refuses_all_families():
    views = _compose(oi=_outlook_inputs())
    g = copy.deepcopy(_base_glt())  # state.asof stays 2026-08-28
    g["views"] = views              # views as_of is 2026-09-04
    snap = contract.finalize(liquidity_central_banks.compose(
        g, _base_cb_desk(), _base_hist(), built_at=BUILT_AT))
    rows = _rows(snap)
    assert len(rows) == 5
    assert all(m["transformation"] == "glt_view_note.reason.as_of_mismatch"
               for m in rows.values())
    assert all(m["null_reason"] == "DISAGREEMENT" for m in rows.values())
    assert all(m["freshness"] == "SOURCE_FAILED" for m in rows.values())


def test_t22_compose_failed_renders_five_failed_rows():
    for as_of in (AS_OF, None):
        views = failed_views(as_of)
        snap = _lcb_with(views)
        rows = _rows(snap)
        assert len(rows) == 5
        assert all(m["transformation"] == "glt_view_note.reason.views_compose_failed"
                   for m in rows.values())
        assert all(m["value"] is None and m["null_reason"] == "SOURCE_FAILED"
                   for m in rows.values())


def test_t22_unknown_note_token_is_recorded():
    labels_module.reset_unknown_tokens()
    metric = {"metric_id": "glt_view_x", "transformation": "glt_view_note.nope"}
    assert suite_view._glt_view_note(metric) is None
    assert "glt_view_note:glt_view_note.nope" in labels_module.unknown_tokens()
    labels_module.reset_unknown_tokens()


def test_t22_audit_a_forecast_rows_carry_no_number(tmp_path):
    snap = _lcb_with(_full_views())
    rows = _rows(snap)
    prow = _prow(snap)
    forecast_rows = {mid: m for mid, m in rows.items()
                     if mid.startswith("glt_view_forecast")}
    assert forecast_rows
    assert all(m["value"] is None for m in forecast_rows.values())
    assert rows["glt_view_forecast_reserves_h4"]["basis"] == "glt_forecast_not_cleared"
    assert rows["glt_view_forecast_reserves_h4"]["transformation"] == \
        "glt_view_note.forecast.not_cleared"
    assert "Not cleared for display" in prow["glt_view_forecast_reserves_h4"]["basis"]["en"]
    html = _t21_render_html(snap, tmp_path)
    assert "3,050" not in html
    assert "3,050.0" not in html
    assert "usd_funding_impulse" not in html


def test_t22_audit_b_k1_only_scenario_or_accounting_and_live_degraded(tmp_path):
    snap = _lcb_with(_full_views())
    rows = _rows(snap)
    valued = [m for mid, m in rows.items()
              if mid.startswith("glt_view_outlook") and m["value"] is not None]
    assert valued
    assert {m["basis"] for m in valued} <= {
        "glt_est_announced_scenario", "glt_est_conditional_accounting",
        "glt_est_scenario_bounds"}
    prow = _prow(_lcb_with(_live_views(tmp_path), built_at=LIVE_BUILT_AT))
    assert "Data degraded" in prow["glt_view_outlook"]["sample_note"]["en"]


def test_t22_audit_c_no_product_reads_path_claim_allowed():
    import engine.market_os.macro_workspaces.liquidity_central_banks as lcb_mod
    for mod in (lcb_mod, suite_view, labels_module):
        text = Path(mod.__file__).read_text(encoding="utf-8")
        assert "path_claim_allowed" not in text
    views = _compose(oi=_outlook_inputs())
    views["conditional_outlook"]["path_claim_allowed"] = True
    snap = _lcb_with(views)
    rows = _rows(snap)
    assert len(rows) == 5
    assert all(m["transformation"] == "glt_view_note.reason.views_contract_refused"
               for m in rows.values())


def test_t22_audit_d_k3_k7_render_no_effect_number(tmp_path):
    views = _compose(oi=_outlook_inputs(), cross=_lawful_cross())
    views["transmission"]["baseline_comparison"] = {"comparator": "persistence_baseline"}
    snap = _lcb_with(views)
    rows = _rows(snap)
    assert any(mid.startswith("glt_view_transmission") for mid in rows)
    assert any(mid.startswith("glt_view_repricing") for mid in rows)
    assert all(m["value"] is None for mid, m in rows.items()
               if mid.startswith(("glt_view_transmission", "glt_view_repricing")))
    html = _t21_render_html(snap, tmp_path)
    assert "0.40" not in html
    assert "usd_funding_impulse" not in html


def test_t22_audit_e_k8_missing_input_per_region_and_cardless_funds():
    base_regions = _lawful_regions()
    v1 = _compose(oi=_outlook_inputs(),
                  cross=_cross(transmission=_xblock(regions=base_regions),
                               repricing=_lawful_xblock()))
    regions2 = [dict(r) for r in base_regions]
    regions2[0] = {"region": "us", "state": "missing_input",
                   "owner": CROSS_REPO_OWNER}
    v2 = _compose(oi=_outlook_inputs(),
                  cross=_cross(transmission=_xblock(regions=regions2),
                               repricing=_lawful_xblock()))
    t1 = {mid: m for mid, m in _rows(_lcb_with(v1)).items()
          if mid.startswith("glt_view_transmission")}
    t2 = {mid: m for mid, m in _rows(_lcb_with(v2)).items()
          if mid.startswith("glt_view_transmission")}
    assert t1 == t2
    assert t1
    assert any(mid.endswith("_region_us") for mid in t1)
    prow = _prow(_lcb_with(v1))
    for mid, r in prow.items():
        if "_region_" in mid or "_fund_" in mid:
            assert "Observed association" not in r["sample_note"]["en"]
            assert "观察到的关联" not in r["sample_note"]["zh"]


def test_t22_audit_f_announced_only_never_a_comparator(tmp_path):
    views = _compose(oi=_outlook_inputs(), cross=_lawful_cross())
    views["transmission"]["baseline_comparison"] = {"comparator": "announced_only"}
    snap = _lcb_with(views)
    rows = _rows(snap)
    t_ids = sorted(mid for mid in rows if mid.startswith("glt_view_transmission"))
    assert t_ids == ["glt_view_transmission"]
    assert rows["glt_view_transmission"]["transformation"] == \
        "glt_view_note.reason.views_contract_refused"
    assert "glt_view_repricing_region_us" in rows
    html = _t21_render_html(snap, tmp_path)
    assert "announced only" not in html.lower()


def test_t22_audit_g_confidence_never_attaches_to_a_row(tmp_path):
    refused = _compose(oi=_outlook_inputs())
    refused["conditional_outlook"]["path_claim_allowed"] = True
    for views, built in ((_full_views(), BUILT_AT),
                         (_live_views(tmp_path), LIVE_BUILT_AT),
                         (refused, BUILT_AT)):
        snap = _lcb_with(views, built_at=built)
        rows = _rows(snap)
        assert rows
        for mid, m in rows.items():
            assert m["uncertainty"] == {"kind": None, "value": None}
        for r in _view_rows(snap):
            for _field, _lang, text in _visible_texts(r):
                assert "confidence" not in text.lower()
                assert "置信" not in text


# --- T22 M5r producer gate ---
from tests.test_global_liquidity_transmission import glt_builder  # noqa: F401,E402
from engine.global_liquidity_views import VIEW_VERSION  # noqa: E402


@pytest.mark.parametrize("stored_shape", ["absent", "old_version", "not_a_dict"])
def test_t22_producer_rewrites_views_less_artifact_once(glt_builder, capsys, stored_shape):
    """A stored contract whose views block is absent or of another view version is
    rewritten once (first_known_at preserved); the next identical run is unchanged."""
    glt_builder.run()  # seed the stored artifact set
    seed = glt_builder.contract()
    assert seed["views"]["view_version"] == VIEW_VERSION
    assert set(VIEW_NAMES) <= set(seed["views"])
    fk = seed["state"]["event_reference"]["clocks"]["first_known_at"]

    # Store the shapes a pre-T22 (or version-bumped) host can hold.
    stored = glt_builder.contract()
    if stored_shape == "absent":
        del stored["views"]
    elif stored_shape == "old_version":
        stored["views"]["view_version"] = "glt_views_v0"
    else:
        stored["views"] = None
    glt_builder.mod.CONTRACT_PATH.write_text(json.dumps(stored, indent=2, sort_keys=True))

    capsys.readouterr()
    glt_builder.run()  # same asof + same source_snapshot_hash, views not current
    out = capsys.readouterr().out
    notices = [ln for ln in out.splitlines() if ln.startswith("::notice title=glt-nightly::")]
    assert len(notices) == 1 and "outcome=written" in notices[0]

    rewritten = glt_builder.contract()
    assert rewritten["views"]["view_version"] == VIEW_VERSION
    assert set(rewritten["views"]) == set(seed["views"])  # same five view names
    assert set(VIEW_NAMES) <= set(rewritten["views"])
    assert rewritten["state"]["event_reference"]["clocks"]["first_known_at"] == fk
    assert rewritten["freshness"]["clocks"]["first_known_at"] == fk

    snap = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in glt_builder.paths()}
    capsys.readouterr()
    glt_builder.run()  # the next identical run is unchanged again
    out = capsys.readouterr().out
    notices = [ln for ln in out.splitlines() if ln.startswith("::notice title=glt-nightly::")]
    assert len(notices) == 1 and "outcome=unchanged" in notices[0]
    for p in glt_builder.paths():
        assert (p.read_bytes(), p.stat().st_mtime_ns) == snap[p]


def test_t22_producer_current_views_artifact_stays_unchanged(glt_builder, capsys):
    """Views present and version current: the T23 idempotency holds unchanged."""
    glt_builder.run()
    snap = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in glt_builder.paths()}

    capsys.readouterr()
    glt_builder.run()  # identical asof + hash + current views block
    out = capsys.readouterr().out
    notices = [ln for ln in out.splitlines() if ln.startswith("::notice title=glt-nightly::")]
    assert len(notices) == 1 and "outcome=unchanged" in notices[0]
    for p in glt_builder.paths():
        assert (p.read_bytes(), p.stat().st_mtime_ns) == snap[p]
