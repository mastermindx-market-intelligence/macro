"""User-visible parity, disclosure, tier isolation and coherence of native Sector views."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import date, timedelta
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine.sector_native_view import (  # noqa: E402
    SectorViewInputs, SectorViewReceipt, SectorViewUnavailable,
    build_brief_series, project_sector_view,
)


@pytest.fixture
def specimen():
    days, current = [], date(2026, 10, 6)
    while len(days) < 21:
        if current.weekday() < 5:
            days.append(current.isoformat())
        current += timedelta(days=1)
    assert days[-1] == "2026-11-03"
    def rows(lane, n):
        return [{"ticker": f"{lane}-{i}", "name": f"{lane} row {i}",
                 "kind": "theme", "href": f"basket/{lane}-{i}.html",
                 "book_wt": None, "signal_grade": "descriptive",
                 "private_debug": "MUST_NOT_LEAK"} for i in range(n)]
    board = {lane: rows(lane, n) for lane, n in {
        "buy_now": 4, "buy_soon": 0, "on_the_run": 0,
        "take_profits": 0, "hold": 2, "avoid": 3,
    }.items()}
    board["more"] = {"hidden_rows": ["MUST_NOT_LEAK"]}
    board["notable"] = [{"name": "MUST_NOT_LEAK"}]
    inputs = SectorViewInputs(
        central={"as_of": "2026-11-03", "sectors": [{"id": "xlv", "ticker": "XLV", "kind": "sector", "name": "Health Care"}]},
        cycles={"meta": {"asOf": "2026-11-03", "rs_history": {"schema": "sector_cycles.rs_history.v1", "mode": "reconstructed_price_history", "naturally_observed": False, "basis": "tr", "benchmark": "SPY", "horizons_sessions": [21, 63], "max_points_per_sector": 252}}, "sectors": [{"id": "xlv", "ticker": "XLV", "kind": "sector", "rs_history": [], "turns": []}]},
        baskets={"as_of": "2026-11-03", "theme_intel": {"as_of": "2026-11-03"},
                 "construction": "Equal-weight baskets, rebalanced monthly.",
                 "history_note": "Current-roster history is descriptive, not a track record.",
                 "chart": {"dates": days, "bench": [100 + .5 * i for i in range(21)],
                           "baskets": {"us_sector_health": [100 + 1.6 * i for i in range(21)]}}},
        handoff={"theme_context": {"as_of": "2026-11-03", "leadership": {
            "state": "rotating", "days_in_state": 3,
            "stance_en": "Existing owner stance.", "stance_zh": "既有研判。",
            "strength": [{"id": "us_sector_health", "name": "Health Care",
                          "name_zh": "医疗保健", "desk_score": 78, "breadth": .817}],
            "trailing_leader": {"id": "memory_storage", "name": "Memory, HBM & Storage"},
        }}, "factor_season": {"chip_en": "Existing context only", "tone": "headwind"},
                 "private_manifest": {"artifacts": ["SECRET_PAID_ARTIFACT"]}},
        action_board={"schema": "sector_intelligence_action_board.v1",
                      "as_of": "2026-11-03", "action_board": board,
                      "baskets_sha256": "PRIVATE_INPUT_HASH"},
    )
    receipt = SectorViewReceipt("sector-g1", "2026-11-03", "2026-11-06T02:00:00Z",
                                "stale", "cohort-v1")
    return inputs, receipt


def test_preserves_owner_leadership_comparison_and_source_clock(specimen):
    inputs, receipt = specimen
    result = project_sector_view(inputs, receipt, audience="preview")
    brief = result["data"]["brief"]
    assert brief["headline"] == {"en": "Leadership is rotating.", "zh": "领涨正在轮动。"}
    assert brief["leadership"]["stance_en"] == "Existing owner stance."
    assert brief["leadership"]["strength"][0]["name"] == "Health Care"
    comparison = brief["comparison"]
    assert comparison["basket_kind"] == "equal_weight_sector_basket"
    assert comparison["benchmark"] == "SPY"
    assert comparison["source_notes"]["construction"] == "Equal-weight baskets, rebalanced monthly."
    assert comparison["price_basis"] == "not_declared_by_chart"
    assert comparison["series"]["sessions"] == 20
    assert len(comparison["series"]["points"]) == 21
    assert comparison["series"]["start"] == "2026-10-06"
    assert comparison["series"]["end"] == "2026-11-03"
    assert comparison["series"]["value"] == pytest.approx(20)
    assert result["receipt"]["source_session"] == "2026-11-03"
    assert result["receipt"]["published_at"] == "2026-11-06T02:00:00Z"
    assert result["receipt"]["qualification"] == "stale"


def test_formula_matches_executed_existing_browser_owner(specimen):
    inputs, _ = specimen
    original = (ROOT / "templates/_sector_central_brief.js.j2").read_text()
    original = original[:original.index("function renderBriefEvidence")]
    command = original + "\nprocess.stdout.write(JSON.stringify(buildSectorBriefSeries(" + (
        json.dumps("us_sector_health") + "," + json.dumps(inputs.baskets["chart"]) + ")));"
    )
    completed = subprocess.run(["node", "-"], input=command, text=True,
                               capture_output=True, check=True, timeout=10)
    owner = json.loads(completed.stdout)
    projected = build_brief_series("us_sector_health", inputs.baskets["chart"])
    assert projected["start"] == owner["start"] and projected["end"] == owner["end"]
    assert projected["value"] == pytest.approx(owner["value"], abs=1e-12)
    for a, b in zip(projected["points"], owner["points"], strict=True):
        assert a["date"] == b["date"]
        assert a["value"] == pytest.approx(b["value"], abs=1e-12)


def test_preview_uses_shared_hold_avoid_budget_and_has_no_paid_rows(specimen):
    inputs, receipt = specimen
    preview = project_sector_view(inputs, receipt, audience="preview")
    paid = project_sector_view(inputs, receipt, audience="entitled")
    board = preview["data"]["action_board"]
    assert board["total"] == 9 and board["locked"] == 3
    assert [r["ticker"] for r in board["lanes"]["hold"]["rows"]] == ["hold-0", "hold-1"]
    assert [r["ticker"] for r in board["lanes"]["avoid"]["rows"]] == ["avoid-0"]
    raw = json.dumps(preview)
    assert "buy_now-3" not in raw and "avoid-1" not in raw and "avoid-2" not in raw
    assert "MUST_NOT_LEAK" not in raw and "PRIVATE_INPUT_HASH" not in raw
    assert "SECRET_PAID_ARTIFACT" not in raw
    assert paid["data"]["action_board"]["locked"] == 0
    assert len(paid["data"]["action_board"]["lanes"]["avoid"]["rows"]) == 3
    assert board["lanes"]["buy_now"]["rows"][0]["book_wt"] is None


def test_preview_hash_does_not_reveal_changes_to_withheld_content(specimen):
    inputs, receipt = specimen
    first = project_sector_view(inputs, receipt, audience="preview")
    paid_first = project_sector_view(inputs, receipt, audience="entitled")
    inputs.action_board["action_board"]["buy_now"][3]["name"] = "Changed hidden row"
    second = project_sector_view(inputs, replace(receipt, generation_id="sector-g2"), audience="preview")
    paid_second = project_sector_view(inputs, receipt, audience="entitled")
    assert first["data"] == second["data"]
    assert first["receipt"]["content_sha256"] == second["receipt"]["content_sha256"]
    assert first["receipt"]["generation_id"] != second["receipt"]["generation_id"]
    assert paid_first["receipt"]["content_sha256"] != paid_second["receipt"]["content_sha256"]


def test_inputs_are_immutable_and_projection_has_no_aliases(specimen):
    inputs, receipt = specimen
    before = deepcopy(inputs)
    a = project_sector_view(inputs, receipt, audience="entitled")
    b = project_sector_view(inputs, receipt, audience="entitled")
    assert a == b and inputs == before
    a["data"]["brief"]["leadership"]["strength"][0]["name"] = "Changed caller view"
    a["data"]["action_board"]["lanes"]["buy_now"]["rows"][0]["ticker"] = "Changed"
    assert inputs == before and a != b


@pytest.mark.parametrize("change,code", [
    (lambda x: x.cycles["meta"].update(asOf="2026-11-04"), "mixed_core_sessions"),
    (lambda x: x.handoff["theme_context"].update(as_of="2026-11-04"), "mixed_brief_sessions"),
    (lambda x: x.action_board.update(as_of="2026-11-02"), "mixed_brief_sessions"),
    (lambda x: x.baskets["theme_intel"].update(as_of="2026-11-02"), "mixed_brief_sessions"),
    (lambda x: x.action_board.pop("as_of"), "invalid_source_session"),
    (lambda x: x.action_board.pop("schema"), "invalid_action_board_contract"),
    (lambda x: x.baskets["chart"]["dates"].__setitem__(-1, "2026-11-04"), "comparison_session_mismatch"),
])
def test_required_sources_cannot_mix_sessions_or_lose_contract(specimen, change, code):
    inputs, receipt = specimen
    change(inputs)
    with pytest.raises(SectorViewUnavailable, match=f"^{code}$"):
        project_sector_view(inputs, receipt, audience="preview")


def test_older_baseline_requires_explicit_receipt_and_remains_visible(specimen):
    inputs, receipt = specimen
    inputs.central["as_of"] = inputs.cycles["meta"]["asOf"] = "2026-11-04"
    newer = replace(receipt, source_session="2026-11-04")
    with pytest.raises(SectorViewUnavailable, match="mixed_brief_sessions"):
        project_sector_view(inputs, newer, audience="preview")
    result = project_sector_view(inputs, replace(newer, baseline_session="2026-11-03"), audience="preview")
    assert result["data"]["brief"]["status"] == "declared_older_baseline"
    assert result["data"]["brief"]["as_of"] == "2026-11-03"
    assert result["data"]["action_board"]["as_of"] == "2026-11-03"
    assert result["receipt"]["source_session"] == "2026-11-04"
    assert result["receipt"]["baseline_session"] == "2026-11-03"


@pytest.mark.parametrize("value", [None, 0, -1, True, float("nan"), float("inf")])
def test_bad_comparison_closes_are_unavailable_never_zero_or_new_signal(specimen, value):
    inputs, receipt = specimen
    inputs.baskets["chart"]["bench"][-1] = value
    result = project_sector_view(inputs, receipt, audience="preview")
    assert result["data"]["brief"]["comparison"]["status"] == "unavailable"
    assert result["data"]["brief"]["comparison"]["series"] is None
    assert result["data"]["brief"]["leadership"]["strength"][0]["name"] == "Health Care"


def test_missing_comparison_window_is_honest(specimen):
    inputs, receipt = specimen
    inputs.baskets["chart"]["dates"].pop()
    result = project_sector_view(inputs, receipt, audience="preview")
    assert result["data"]["brief"]["comparison"]["reason"] == "matching_closes_unavailable"


def test_dangerous_source_links_do_not_reach_native_view(specimen):
    inputs, receipt = specimen
    rows = inputs.action_board["action_board"]["buy_now"]
    rows[0]["href"] = "javascript:alert(1)"
    rows[1]["href"] = "https://attacker.invalid/path.html"
    rows[2]["href"] = "../private.html"
    result = project_sector_view(inputs, receipt, audience="preview")
    assert all("href" not in row for row in result["data"]["action_board"]["lanes"]["buy_now"]["rows"])


def test_nonfinite_visible_values_and_oversized_projection_fail_closed(specimen):
    inputs, receipt = specimen
    inputs.action_board["action_board"]["buy_now"][0]["score"] = float("nan")
    with pytest.raises(SectorViewUnavailable, match="invalid_projection_value"):
        project_sector_view(inputs, receipt, audience="preview")
    inputs.action_board["action_board"]["buy_now"][0]["score"] = 67
    inputs.handoff["theme_context"]["leadership"]["stance_en"] = "x" * (4 * 1024 * 1024)
    with pytest.raises(SectorViewUnavailable, match="projection_too_large"):
        project_sector_view(inputs, receipt, audience="preview")


def test_projection_never_reads_a_loader_or_clock(specimen, monkeypatch):
    import builtins
    import engine.sector_native_view as module
    from datetime import datetime

    class NoClock(datetime):
        @classmethod
        def now(cls, *args, **kwargs):
            raise AssertionError("implicit current clock")
    def forbidden(*args, **kwargs):
        raise AssertionError("implicit data or configuration load")
    inputs, receipt = specimen
    with monkeypatch.context() as m:
        m.setattr(builtins, "open", forbidden)
        m.setattr(Path, "read_text", forbidden)
        m.setattr(Path, "read_bytes", forbidden)
        m.setattr(module, "datetime", NoClock)
        result = project_sector_view(inputs, receipt, audience="preview")
    assert result["receipt"]["qualification"] == "stale"


@pytest.mark.parametrize("field,value,code", [
    ("generation_id", "../current", "invalid_receipt"),
    ("input_version", "/private/source", "invalid_receipt"),
    ("qualification", "fresh_from_poll", "invalid_qualification"),
    ("published_at", "2026-11-06T02:00:00", "invalid_publication_clock"),
    ("baseline_session", "2026-11-04", "future_baseline"),
])
def test_bad_public_receipts_are_closed_safe_codes(specimen, field, value, code):
    inputs, receipt = specimen
    with pytest.raises(SectorViewUnavailable, match=f"^{code}$"):
        project_sector_view(inputs, replace(receipt, **{field: value}), audience="preview")


def test_nested_metadata_cannot_hide_inside_allowed_fields(specimen):
    inputs, receipt = specimen
    inputs.action_board["action_board"]["buy_now"][0]["name"] = {"private": "HIDDEN"}
    with pytest.raises(SectorViewUnavailable, match="^invalid_projection_value$"):
        project_sector_view(inputs, receipt, audience="preview")


@pytest.fixture
def complete_specimen(specimen):
    inputs, receipt = specimen
    inputs.central["publication"] = {"private": "PRIVATE_CORE"}
    row = inputs.central["sectors"][0]
    row.update(name_zh="医疗保健", accent="#123456", private="PRIVATE_CORE",
        momentum={"rs_21d": 2.5, "rs_63d": None, "rs_21d_rank": 1, "rs_rank": None,
                  "above_200d": False, "lead": "leading", "fading": "PRIVATE_CORE"},
        heat={"heat_1M": None, "breadth_pct": 0, "adv": 0, "dec": 12, "raw": "PRIVATE_CORE"},
        rotation={"state": "LEADING", "state_plain_en": "Existing rotation",
                  "state_plain_zh": "既有轮动", "score": "PRIVATE_CORE"},
        conviction={"label_en": "Existing label", "score": "PRIVATE_CORE"},
        cycle={"phaseLabel": "Existing phase", "phase": "PRIVATE_CORE"})
    inputs.central["measured_read"] = {
        "schema": "leadership_rotation_context.measured_group_read/v1", "status": "partial",
        "generation": {"session_end": "2026-11-03", "benchmark": "SPY", "id": "PRIVATE_CORE"},
        "cohort": {"expected_n": 2, "measured_n": 1, "horizon": "rs_21d", "z_reference": "PRIVATE_CORE"},
        "groups": [
            {"group_id": "XLV", "name_en": "Health Care", "name_zh": "医疗保健",
             "current": {"status": "measured", "rank": 1, "rs_21d": 2.5,
                         "rs_63d": None, "reason": None, "z": "PRIVATE_CORE"}},
            {"group_id": "XLK", "name_en": "Technology", "name_zh": None,
             "current": {"status": "unmeasured", "rank": None, "rs_21d": None,
                         "rs_63d": None, "reason": "missing_input", "z": "PRIVATE_CORE"}},
        ], "research_estimate": "PRIVATE_CORE",
    }
    row = inputs.cycles["sectors"][0]
    row.update(rs_history=[
        {"date": "2026-10-30", "rs_21d": -1.25, "rs_63d": 0, "private": "PRIVATE_CYCLE"},
        {"date": "2026-11-03", "rs_21d": 2.5, "rs_63d": -3.5},
    ], turns=[
        {"date": "2026-10-01", "k": "trough", "major": False,
         "provisional": False, "mag_pct": None, "px": "PRIVATE_CYCLE"},
        {"date": "2026-11-02", "k": "peak", "major": True,
         "provisional": True, "mag_pct": 20.5, "px": "PRIVATE_CYCLE"},
    ], price="PRIVATE_CYCLE", osc="PRIVATE_CYCLE", now="PRIVATE_CYCLE", proj="PRIVATE_CYCLE")
    inputs.cycles["meta"]["rs_history"]["as_of"] = "2026-11-03"
    inputs.cycles["meta"]["rs_history"]["source_cohort"] = "PRIVATE_CYCLE"
    return inputs, receipt


@pytest.mark.parametrize("audience", ["preview", "entitled"])
def test_core_history_are_one_allowlisted_detached_generation(complete_specimen, audience):
    inputs, receipt = complete_specimen
    before = deepcopy(inputs)
    result = project_sector_view(inputs, receipt, audience=audience)
    core, history = result["data"]["core"], result["data"]["history"]
    assert core["as_of"] == history["meta"]["asOf"] == result["receipt"]["source_session"]
    assert core["sectors"][0]["momentum"] == {
        "rs_21d": 2.5, "rs_63d": None, "rs_21d_rank": 1, "rs_rank": None,
        "above_200d": False, "lead": "leading",
    }
    assert core["sectors"][0]["heat"] == {"heat_1M": None, "breadth_pct": 0, "adv": 0, "dec": 12}
    assert core["sectors"][0]["cycle"] == {"phaseLabel": "Existing phase"}
    assert core["measured_read"]["groups"][1]["current"]["rank"] is None
    assert core["measured_read"]["groups"][1]["current"]["reason"] == "missing_input"
    assert history["sectors"][0]["rs_history"] == [
        {"date": "2026-10-30", "rs_21d": -1.25, "rs_63d": 0},
        {"date": "2026-11-03", "rs_21d": 2.5, "rs_63d": -3.5},
    ]
    assert history["sectors"][0]["turns"][0] == {
        "date": "2026-10-01", "k": "trough", "major": False,
        "provisional": False, "mag_pct": None,
    }
    assert "PRIVATE_CORE" not in json.dumps(result) and "PRIVATE_CYCLE" not in json.dumps(result)
    assert inputs == before
    core["sectors"][0]["momentum"]["rs_21d"] = 999
    history["sectors"][0]["rs_history"][0]["rs_21d"] = 999
    assert inputs == before


def test_core_and_history_both_change_the_authorized_content_hash(complete_specimen):
    inputs, receipt = complete_specimen
    first = project_sector_view(inputs, receipt, audience="preview")
    inputs.central["sectors"][0]["momentum"]["rs_21d"] = 3
    second = project_sector_view(inputs, receipt, audience="preview")
    inputs.cycles["sectors"][0]["rs_history"][-1]["rs_21d"] = 3
    third = project_sector_view(inputs, receipt, audience="preview")
    assert len({view["receipt"]["content_sha256"] for view in (first, second, third)}) == 3
    assert first["data"]["brief"] == second["data"]["brief"] == third["data"]["brief"]
    assert first["receipt"]["published_at"] == second["receipt"]["published_at"] == receipt.published_at


def test_missing_measurements_and_empty_source_series_stay_explicit(specimen):
    inputs, receipt = specimen
    result = project_sector_view(inputs, receipt, audience="preview")
    assert "measured_read" not in result["data"]["core"]
    assert result["data"]["history"]["sectors"][0]["rs_history"] == []
    inputs.central["measured_read"] = {
        "schema": "leadership_rotation_context.measured_group_read/v1",
        "status": "unavailable", "reason": "projection_error",
    }
    result = project_sector_view(inputs, receipt, audience="preview")
    assert result["data"]["core"]["measured_read"] == inputs.central["measured_read"]
    assert result["data"]["history"]["sectors"][0]["rs_history"] == []


@pytest.mark.parametrize("change,code", [
    (lambda x: x.central.pop("sectors"), "invalid_sector_core"),
    (lambda x: x.central["sectors"].append(deepcopy(x.central["sectors"][0])), "invalid_sector_core"),
    (lambda x: x.central["sectors"][0].update(name=""), "invalid_sector_core"),
    (lambda x: x.central["sectors"][0]["momentum"].update(rs_21d=True), "invalid_sector_core"),
    (lambda x: x.central["sectors"][0]["heat"].update(adv=float("nan")), "invalid_sector_core"),
    (lambda x: x.central["sectors"][0]["cycle"].update(phaseLabel={"hidden": 1}), "invalid_sector_core"),
    (lambda x: x.central["measured_read"]["generation"].update(session_end="2026-11-02"), "mixed_measured_session"),
    (lambda x: x.central["measured_read"]["cohort"].update(measured_n=True), "invalid_measured_read"),
    (lambda x: x.central["measured_read"]["cohort"].update(measured_n=2), "invalid_measured_read"),
    (lambda x: x.central["measured_read"]["cohort"].update(horizon="rs_63d"), "invalid_measured_read"),
    (lambda x: x.central["measured_read"]["groups"][0]["current"].update(rank=2), "invalid_measured_read"),
    (lambda x: x.central["measured_read"].update(status="available"), "invalid_measured_read"),
    (lambda x: x.central["measured_read"]["groups"].pop(), "invalid_measured_read"),
    (lambda x: x.central["sectors"][0]["momentum"].update(rs_rank=1.5), "invalid_sector_core"),
    (lambda x: x.central["sectors"][0]["heat"].update(adv=-1), "invalid_sector_core"),
    (lambda x: x.cycles["sectors"][0].pop("turns"), "invalid_sector_history"),
    (lambda x: x.central["measured_read"]["groups"][0]["current"].update(rank=None), "invalid_measured_read"),
    (lambda x: x.central["measured_read"]["groups"].append(deepcopy(x.central["measured_read"]["groups"][0])), "invalid_measured_read"),
    (lambda x: x.cycles.update(sectors=[]), "invalid_sector_history"),
    (lambda x: x.central.update(sectors=[]), "invalid_sector_core"),
    (lambda x: x.cycles["meta"].pop("rs_history"), "invalid_sector_history"),
    (lambda x: x.cycles["meta"]["rs_history"].update(as_of="2026-11-02"), "invalid_sector_history"),
    (lambda x: x.cycles["meta"]["rs_history"].update(naturally_observed=0), "invalid_sector_history"),
    (lambda x: x.cycles["meta"]["rs_history"].update(max_points_per_sector=252.0), "invalid_sector_history"),
    (lambda x: x.cycles["meta"]["rs_history"].update(horizons_sessions=[21.0, 63]), "invalid_sector_history"),
    (lambda x: x.cycles["sectors"][0].update(ticker="XLK"), "mixed_sector_identity"),
    (lambda x: x.cycles["sectors"][0].update(id="xlk"), "mixed_sector_identity"),
    (lambda x: x.cycles["sectors"][0].pop("rs_history"), "invalid_sector_history"),
    (lambda x: x.cycles["sectors"][0]["rs_history"].reverse(), "invalid_sector_history"),
    (lambda x: x.cycles["sectors"][0]["rs_history"][-1].update(date="2026-11-04"), "invalid_sector_history"),
    (lambda x: x.cycles["sectors"][0]["rs_history"][-1].update(rs_21d=None), "invalid_sector_history"),
    (lambda x: x.cycles["sectors"][0]["rs_history"][-1].update(rs_63d=True), "invalid_sector_history"),
    (lambda x: x.cycles["sectors"][0]["rs_history"][-1].update(date="2026-02-30"), "invalid_source_session"),
    (lambda x: x.cycles["sectors"][0]["turns"][-1].update(mag_pct=-1), "invalid_sector_history"),
    (lambda x: x.cycles["sectors"][0]["turns"][-1].update(major=1), "invalid_sector_history"),
    (lambda x: x.cycles["sectors"][0]["turns"][-1].update(k="projected_peak"), "invalid_sector_history"),
    (lambda x: x.cycles["sectors"][0]["turns"][-1].update(date="2026-11-04"), "invalid_sector_history"),
    (lambda x: x.cycles["sectors"][0]["turns"][-1].update(date="2026-10-01"), "invalid_sector_history"),
])
def test_invalid_core_history_never_enters_a_complete_generation(complete_specimen, change, code):
    inputs, receipt = complete_specimen
    change(inputs)
    with pytest.raises(SectorViewUnavailable, match=f"^{code}$"):
        project_sector_view(inputs, receipt, audience="entitled")


@pytest.mark.parametrize("section,key,limit,code", [
    ("central", "sectors", 100, "invalid_sector_core"),
    ("cycles", "sectors", 100, "invalid_sector_history"),
    ("history", "rs_history", 252, "invalid_sector_history"),
    ("history", "turns", 256, "invalid_sector_history"),
])
def test_native_bounds_reject_oversize_without_silent_truncation(complete_specimen, section, key, limit, code):
    inputs, receipt = complete_specimen
    owner = inputs.cycles["sectors"][0] if section == "history" else getattr(inputs, section)
    owner[key] = [deepcopy(owner[key][0])] * (limit + 1)
    with pytest.raises(SectorViewUnavailable, match=f"^{code}$"):
        project_sector_view(inputs, receipt, audience="preview")


def test_earlier_last_observation_is_not_filled_to_source_date(complete_specimen):
    inputs, receipt = complete_specimen
    inputs.cycles["sectors"][0]["rs_history"].pop()
    result = project_sector_view(inputs, receipt, audience="preview")
    assert result["data"]["history"]["sectors"][0]["rs_history"][-1]["date"] == "2026-10-30"
    assert result["data"]["history"]["meta"]["asOf"] == "2026-11-03"


def test_nullable_rotation_and_independent_unmeasured_horizon_are_preserved(complete_specimen):
    inputs, receipt = complete_specimen
    inputs.central["sectors"][0]["rotation"] = None
    inputs.central["measured_read"]["groups"][1]["current"]["rs_63d"] = 4.2
    result = project_sector_view(inputs, receipt, audience="preview")
    assert result["data"]["core"]["sectors"][0]["rotation"] is None
    missing = result["data"]["core"]["measured_read"]["groups"][1]["current"]
    assert missing["rank"] is None and missing["rs_21d"] is None and missing["rs_63d"] == 4.2


def test_same_identity_set_preserves_distinct_owner_orders(specimen):
    inputs, receipt = specimen
    core = {"id": "xlk", "ticker": "XLK", "kind": "sector", "name": "Technology"}
    history = {"id": "xlk", "ticker": "XLK", "kind": "sector", "rs_history": [], "turns": []}
    inputs.central["sectors"].insert(0, core)
    inputs.cycles["sectors"].append(history)
    result = project_sector_view(inputs, receipt, audience="preview")
    assert [r["id"] for r in result["data"]["core"]["sectors"]] == ["xlk", "xlv"]
    assert [r["id"] for r in result["data"]["history"]["sectors"]] == ["xlv", "xlk"]
    inputs.central["sectors"].pop()
    with pytest.raises(SectorViewUnavailable, match="mixed_sector_identity"):
        project_sector_view(inputs, receipt, audience="preview")
