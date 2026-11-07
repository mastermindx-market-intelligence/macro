"""User-visible parity, disclosure, tier isolation and coherence of native Sector views."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import date, timedelta
import hashlib
import json
import os
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


def test_missing_dated_owner_refuses_only_when_addendum_is_present(specimen, monkeypatch):
    import builtins

    original_import = builtins.__import__
    requested = []

    def missing_owner(name, *args, **kwargs):
        if name == "engine.sector_dated_context":
            requested.append(name)
            raise ModuleNotFoundError("PRIVATE_DEPENDENCY_PATH")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", missing_owner)
    inputs, receipt = specimen
    result = project_sector_view(inputs, receipt, audience="preview")
    assert "dated_context" not in result["data"]["core"]
    assert requested == []

    inputs.central["dated_context"] = json.loads((ROOT / "tests" / "fixtures" /
        "leadership_rotation" / "dated_context_current_v1.json").read_text())
    with pytest.raises(SectorViewUnavailable) as error:
        project_sector_view(inputs, receipt, audience="preview")
    assert str(error.value) == "invalid_sector_dated_context"
    assert "PRIVATE_DEPENDENCY_PATH" not in str(error.value)
    assert requested == ["engine.sector_dated_context"]


def _dated_context_owner_inputs():
    path = ROOT / "tests" / "fixtures" / "leadership_rotation" / "dated_context_inputs_v1.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _dated_context_owner_packet(**overrides):
    from engine.sector_dated_context import project_dated_context

    inputs = _dated_context_owner_inputs()
    inputs.update(overrides)
    return project_dated_context(**inputs)


@pytest.mark.parametrize("case", ["complete", "missing_risk", "missing_theme", "historical", "invalid_cutoff",
    "revision_only", "bottleneck_only", "historical_missing_risk", "historical_missing_theme"])
def test_dated_context_preserves_the_actual_owner_packet_without_sector_authority(specimen, case):
    changes = {"missing_risk": {"public_risk_document": None},
               "missing_theme": {"config_document": {}},
               "historical": {"decision_cutoff": "2026-10-01T20:00:00Z"},
               "invalid_cutoff": {"decision_cutoff": "yesterday"},
               "historical_missing_risk": {"decision_cutoff": "2026-10-01T20:00:00Z", "public_risk_document": None},
               "historical_missing_theme": {"decision_cutoff": "2026-10-01T20:00:00Z", "config_document": {}}}.get(case, {})
    if case in ("revision_only", "bottleneck_only"):
        regime = _dated_context_owner_inputs()["regime_document"]
        regime.pop("bottleneck" if case == "revision_only" else "theme_revisions")
        changes["regime_document"] = regime
    packet = _dated_context_owner_packet(**changes)
    inputs, receipt = specimen
    inputs.central["dated_context"] = packet
    result = project_sector_view(inputs, receipt, audience="preview")
    actual = result["data"]["core"]["dated_context"]
    assert actual == packet and actual is not packet
    assert actual["limitations"]["current_sector_usable"] is False
    assert actual["limitations"]["historically_admissible"] is False
    assert all(value is False for value in actual["authority"].values())
    assert actual["market_risk"]["scope"] == "market_global"
    assert all(row["falsifier"]["met"] is False for row in actual["comparison"]["entries"])
    if case == "complete":
        frozen = ROOT / "tests" / "fixtures" / "leadership_rotation" / "dated_context_current_v1.json"
        assert actual == json.loads(frozen.read_text(encoding="utf-8"))
        assert actual["observations"]["bottleneck"]["asof"] == "2026-09-01"
        assert actual["observations"]["revision_state"]["asof"] == "2026-11-06"
        assert actual["observations"]["revision_state"]["n_covered"] == 3
        assert actual["theme"]["roster_size"] == 5
        assert receipt.source_session != actual["observations"]["revision_state"]["asof"]
    if case == "historical":
        frozen = ROOT / "tests" / "fixtures" / "leadership_rotation" / "dated_context_historical_v1.json"
        assert actual == json.loads(frozen.read_text(encoding="utf-8"))
    # The next generation's absence withdraws the addendum. No prior packet cache.
    del inputs.central["dated_context"]
    assert "dated_context" not in project_sector_view(inputs, receipt, audience="preview")["data"]["core"]


@pytest.mark.parametrize("case", ["schema", "scope", "authority", "authority_zero", "sector_claim",
    "pit_zero", "top_field", "observation_field", "comparison_identity", "evaluation", "met",
    "met_zero", "reference", "nonfinite", "cycle", "oversize", "roster_duplicate", "attribution",
    "theme_with_positive", "top_status", "partial_with_both", "missing_cluster", "market_supported",
    "partial_historical", "fractional_net_up", "negative_net_up", "null_breadth",
    "member_count", "covered_count", "coverage_ratio", "null_risk_score", "null_policy", "unavailable_positive_risk"])
def test_dated_context_rejects_tampering_instead_of_transporting_arbitrary_json(specimen, case):
    packet = _dated_context_owner_packet()
    if case == "schema": packet["schema"] = "other/v1"
    elif case == "scope": packet["scope"] = "selected_sector_cause"
    elif case == "authority": packet["authority"]["may_trade"] = True
    elif case == "authority_zero": packet["authority"]["may_trade"] = 0
    elif case == "sector_claim": packet["limitations"]["current_sector_usable"] = True
    elif case == "pit_zero": packet["limitations"]["historically_admissible"] = 0
    elif case == "top_field": packet["private_manifest"] = {"secret": "must-not-leak"}
    elif case == "observation_field": packet["observations"]["order"] = {"size": 1}
    elif case == "comparison_identity": packet["comparison"]["entries"][0]["id"] = "sector_cause"
    elif case == "evaluation": packet["comparison"]["evaluation"] = "validated"
    elif case == "met": packet["comparison"]["entries"][0]["falsifier"]["met"] = True
    elif case == "met_zero": packet["comparison"]["entries"][0]["falsifier"]["met"] = 0
    elif case == "reference": packet["comparison"]["entries"][0]["evidence_refs"] = ["market_risk.not_present"]
    elif case == "nonfinite": packet["market_risk"]["coherence"]["contradictions"] = [float("nan")]
    elif case == "cycle": packet["market_risk"]["coherence"]["contradictions"] = [packet]
    elif case == "oversize": packet["market_risk"]["coherence"]["contradictions"] = ["x" * 16384]
    elif case == "roster_duplicate": packet["theme"]["roster"][1] = packet["theme"]["roster"][0]
    elif case == "attribution": packet["provenance"]["source_attribution"]["config_document"]["raw_sha256"] = "not-a-hash"
    elif case == "theme_with_positive": packet["theme"]["status"] = "unavailable"
    elif case == "top_status": packet["status"] = "partial"
    elif case == "partial_with_both": packet["observations"]["status"] = "partial"
    elif case == "missing_cluster": del packet["observations"]["contributors"]
    elif case == "market_supported": packet["comparison"]["entries"][3]["status"] = "supported"
    elif case == "partial_historical": packet["comparison"]["status"] = "withheld"
    elif case == "fractional_net_up": packet["observations"]["revision_state"]["net_up_total"] = 0.5
    elif case == "negative_net_up": packet["observations"]["revision_state"]["net_up_total"] = -1
    elif case == "null_breadth": packet["observations"]["revision_state"]["breadth"] = None
    elif case == "member_count": packet["observations"]["revision_state"]["n_members"] = 6
    elif case == "covered_count": packet["observations"]["revision_state"]["n_covered"] = 2
    elif case == "coverage_ratio": packet["observations"]["revision_state"]["coverage"] = 0.9
    elif case == "null_risk_score": packet["market_risk"]["measured_state"]["score"] = None
    elif case == "null_policy": packet["market_risk"]["policy_summary"]["posture"] = None
    elif case == "unavailable_positive_risk": packet["market_risk"]["status"] = "unavailable";packet["status"] = "partial"
    inputs, receipt = specimen
    inputs.central["dated_context"] = packet
    with pytest.raises(SectorViewUnavailable, match="invalid_sector_dated_context"):
        project_sector_view(inputs, receipt, audience="preview")


def test_dated_context_accepts_owner_integral_counts_unicode_and_opaque_clock_evidence(specimen):
    raw = _dated_context_owner_inputs()
    regime, risk, attribution = (raw["regime_document"], raw["public_risk_document"],
                                 raw["source_attribution"])
    revisions = regime["theme_revisions"]["themes"]["memory_storage"]
    revisions["n_covered"], revisions["n_members"] = 3.0, 5.0
    regime["freshness"]["asof"] = {"invalid_owner_clock": ["retained evidence"]}
    regime["bottleneck"]["themes"]["memory_storage"]["fingerprint"]["components"]["leg7_member_inventory"]["weight_provisional"] = True
    risk["coherence"]["contradictions"] = [0] * 300
    risk["authority"]["envelope_may_gate"] = True
    attribution["regime_document"]["source_ref"] = "来源" * 150
    packet = _dated_context_owner_packet(regime_document=regime, public_risk_document=risk,
                                         source_attribution=attribution)
    assert packet["status"] == "dated_context"
    inputs, receipt = specimen
    inputs.central["dated_context"] = packet
    result = project_sector_view(inputs, receipt, audience="preview")["data"]["core"]["dated_context"]
    assert result == packet
    assert result["market_risk"]["source_authority"]["envelope_may_gate"] is True
    assert result["authority"]["may_gate"] is False


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


# --- Persistent Sector Leadership: optional dated dossier child --------------
# The dossier is a display-only evidence packet over the frozen eleven-identity
# native cohort. The projector only carries an accepted packet; it never
# composes one, never fills a missing measurement and never adds authority.

_NATIVE_DOSSIER_IDS = ("XLB", "XLC", "XLE", "XLF", "XLI", "XLK", "XLP", "XLRE",
                       "XLU", "XLV", "XLY")


def _native_measured_read():
    """A measured read over the full native cohort, as the owner emits it."""
    groups = []
    for index, ident in enumerate(_NATIVE_DOSSIER_IDS):
        groups.append({
            "group_id": ident, "name_en": f"{ident} Sector", "name_zh": None,
            "current": {"status": "measured", "rank": index + 1,
                        "rs_21d": 1.0 + index, "rs_63d": 2.0 + index, "reason": None},
        })
    return {
        "schema": "leadership_rotation_context.measured_group_read/v1",
        "status": "available",
        "generation": {"session_end": "2026-11-03", "benchmark": "SPY",
                       "id": "2026-11-03|SPY|us_sectors_11",
                       "cohort_id": "us_sectors_11", "price_basis": "total_return"},
        "cohort": {"expected_n": 11, "measured_n": 11, "horizon": "rs_21d"},
        "groups": groups,
    }


def _dossier_rows(values=None):
    """One bounded representative row per native identity, in native order.

    The default is COHERENT with the owner's measured read: a child
    measurement equals the measurement of the SAME parent group, which is the
    only way the owner ever emits a non-null child value.
    """
    values = values or {}
    rows = []
    for index, ident in enumerate(_NATIVE_DOSSIER_IDS):
        rs_21d, rs_63d = values.get(ident, (1.0 + index, 2.0 + index))
        present = sum(value is not None for value in (rs_21d, rs_63d))
        rows.append({
            "group_id": ident, "name_en": f"{ident} Sector", "name_zh": None,
            "status": ("available" if present == 2 else "partial" if present
                       else "unavailable"),
            "relative_wealth_pct": {"rs_21d": rs_21d, "rs_63d": rs_63d},
            "null_reasons": {"rs_21d": None if rs_21d is not None else "missing_input",
                             "rs_63d": None if rs_63d is not None else "missing_input"},
            "qualification_reasons": [],
        })
    return rows


def _dossier_packet(rows):
    """An accepted dossier packet: every status and count follows the rows."""
    counts = {}
    for sessions in (21, 63):
        field = f"rs_{sessions}d"
        valid = [row["relative_wealth_pct"][field] for row in rows
                 if row["relative_wealth_pct"][field] is not None]
        counts[str(sessions)] = {
            "expected_n": 11, "measured_n": len(valid),
            "positive_n": sum(1 for value in valid if value > 0) if valid else None,
        }
    any_values = any(row["relative_wealth_pct"][f"rs_{sessions}d"] is not None
                     for row in rows for sessions in (21, 63))
    all_available = all(row["status"] == "available" for row in rows)
    return {
        "schema": "leadership_rotation_context.sector_dossiers/v1",
        "status": "partial" if any_values else "unavailable",
        "measurement_status": ("available" if all_available
                               else "partial" if any_values else "unavailable"),
        "cohort_id": "us_sectors_11",
        "population": "eleven_sector_etf_proxies",
        "as_of": "2026-11-03",
        "benchmark": "SPY",
        "price_basis": "total_return",
        "units": "pct",
        "windows_sessions": [21, 63],
        "unavailable_windows": {"sessions": [5, 20], "reason": "not_supplied_by_owner"},
        "absolute_returns": {"status": "unavailable", "reason": "not_supplied_by_owner"},
        "compatibility_key": "2026-11-03|SPY|us_sectors_11",
        "source_generation": {"status": "unavailable",
                              "reason": "immutable_generation_not_supplied", "id": None},
        "availability": {"mode": "dated_snapshot", "decision_cutoff": None,
                         "original_available_at": None, "historically_admissible": False,
                         "reason": "original_availability_not_supplied"},
        "history": {"mode": "reconstructed_price_history", "naturally_observed": False},
        "freshness": {"status": "unverified",
                      "reason": "owner_freshness_receipt_not_supplied"},
        "corrections": {"status": "unavailable",
                        "reason": "native_revision_selection_not_supplied"},
        "authority": {"may_rank": False, "may_gate": False, "may_size": False,
                      "may_trade": False, "may_escalate": False},
        "forecasts": {"status": "not_qualified", "expected_return": None,
                      "persistence_estimate": None, "allocation_weight": None},
        "mechanism": {"status": "unavailable", "reason": "no_qualified_evidence",
                      "owner": "engine.theme_graph"},
        "risk": {"status": "unavailable", "reason": "no_qualified_risk_context",
                 "owner": "engine.risk_envelope", "scope": None},
        "constituent_breadth": {"status": "unavailable",
                                "reason": "native_membership_not_supplied"},
        "constituent_concentration": {"status": "unavailable",
                                      "reason": "native_weights_not_supplied"},
        "cross_sector_breadth_counts": counts,
        "dependency_audit": {"source_roots": ["engine.sector_cycles"],
                              "source_family_count": 1, "independence": "not_established",
                              "shared_rolling_windows": True,
                              "constituent_overlap": "unknown"},
        "diagnostics": {"qualification_reasons": [], "duplicate_groups": [],
                         "outside_cohort": [], "malformed_source_rows": 0,
                         "malformed_measured_rows": 0},
        "groups": rows,
    }


@pytest.fixture
def dossier_specimen(specimen):
    inputs, receipt = specimen
    inputs.central["measured_read"] = _native_measured_read()
    inputs.central["measured_read"]["sector_dossiers"] = _dossier_packet(_dossier_rows())
    return inputs, receipt


def _dossier_of(result):
    return result["data"]["core"]["measured_read"]["sector_dossiers"]


def test_absent_dossier_keeps_the_incumbent_representation_and_hash(specimen):
    """Absent optional input stays byte-identical to the pre-change projector."""
    inputs, receipt = specimen
    preview = project_sector_view(inputs, receipt, audience="preview")
    entitled = project_sector_view(inputs, receipt, audience="entitled")
    assert "measured_read" not in preview["data"]["core"]
    assert "sector_dossiers" not in json.dumps(preview)
    # Golden values captured from engine/sector_native_view.py at the input
    # commit 334b26b5, before the dossier child existed.
    assert preview["receipt"]["content_sha256"] == (
        "480de3eb6567aa1e022ead7a7cabffe4c4d9359ffa9735c5e92e45166d9dc8be")
    assert entitled["receipt"]["content_sha256"] == (
        "3ec21169d85a29b08b5b76e924b01e1298a3c5ec068dfa7b26e7a4088614d2e5")


def test_measured_read_without_a_dossier_keeps_the_incumbent_hash(specimen):
    inputs, receipt = specimen
    inputs.central["measured_read"] = _native_measured_read()
    preview = project_sector_view(inputs, receipt, audience="preview")
    entitled = project_sector_view(inputs, receipt, audience="entitled")
    assert "sector_dossiers" not in preview["data"]["core"]["measured_read"]
    assert preview["receipt"]["content_sha256"] == (
        "cafd4d575e1bb98d55f7c08913ff4264a87465bc1247cd23c00b42869205cee2")
    assert entitled["receipt"]["content_sha256"] == (
        "674cb6d5b8cb914b1bd3a5ba0a0aab4a8c7b63fa688303ccc4c0cec5d94f1f59")


@pytest.mark.parametrize("audience", ["preview", "entitled"])
def test_valid_dossier_survives_the_native_projector(dossier_specimen, audience):
    inputs, receipt = dossier_specimen
    dossier = _dossier_of(project_sector_view(inputs, receipt, audience=audience))
    assert dossier["schema"] == "leadership_rotation_context.sector_dossiers/v1"
    assert dossier["cohort_id"] == "us_sectors_11"
    assert dossier["population"] == "eleven_sector_etf_proxies"
    assert dossier["units"] == "pct"
    assert dossier["windows_sessions"] == [21, 63]
    assert dossier["unavailable_windows"] == {
        "sessions": [5, 20], "reason": "not_supplied_by_owner"}
    assert [group["group_id"] for group in dossier["groups"]] == list(_NATIVE_DOSSIER_IDS)
    assert len(dossier["groups"]) == 11
    assert dossier["status"] == "partial"
    assert dossier["measurement_status"] == "available"
    assert dossier["cross_sector_breadth_counts"]["21"] == {
        "expected_n": 11, "measured_n": 11, "positive_n": 11}
    assert all(flag is False for flag in dossier["authority"].values())
    assert dossier["forecasts"] == {
        "status": "not_qualified", "expected_return": None,
        "persistence_estimate": None, "allocation_weight": None}
    assert dossier["source_generation"] == {
        "status": "unavailable", "reason": "immutable_generation_not_supplied", "id": None}
    assert dossier["availability"]["original_available_at"] is None
    assert dossier["availability"]["historically_admissible"] is False
    assert dossier["freshness"]["status"] == "unverified"
    assert dossier["corrections"]["status"] == "unavailable"
    assert dossier["history"]["naturally_observed"] is False


def test_all_null_unavailable_packet_keeps_every_native_identity(dossier_specimen):
    inputs, receipt = dossier_specimen
    rows = _dossier_rows({ident: (None, None) for ident in _NATIVE_DOSSIER_IDS})
    inputs.central["measured_read"]["sector_dossiers"] = _dossier_packet(rows)
    dossier = _dossier_of(project_sector_view(inputs, receipt, audience="preview"))
    assert dossier["status"] == "unavailable"
    assert dossier["measurement_status"] == "unavailable"
    assert [group["group_id"] for group in dossier["groups"]] == list(_NATIVE_DOSSIER_IDS)
    assert all(group["status"] == "unavailable" for group in dossier["groups"])
    assert all(value is None for group in dossier["groups"]
               for value in group["relative_wealth_pct"].values())
    assert all(group["null_reasons"]["rs_21d"] == "missing_input"
               for group in dossier["groups"])
    assert dossier["cross_sector_breadth_counts"]["63"] == {
        "expected_n": 11, "measured_n": 0, "positive_n": None}


def test_partial_window_is_preserved_not_completed(dossier_specimen):
    inputs, receipt = dossier_specimen
    rows = _dossier_rows({"XLB": (1.0, None)})
    inputs.central["measured_read"]["sector_dossiers"] = _dossier_packet(rows)
    dossier = _dossier_of(project_sector_view(inputs, receipt, audience="preview"))
    first = dossier["groups"][0]
    assert first["group_id"] == "XLB"
    assert first["status"] == "partial"
    assert first["relative_wealth_pct"] == {"rs_21d": 1.0, "rs_63d": None}
    assert first["null_reasons"] == {"rs_21d": None, "rs_63d": "missing_input"}
    assert dossier["measurement_status"] == "partial"


def test_dated_availability_is_preserved_without_claiming_original_availability(
        dossier_specimen):
    inputs, receipt = dossier_specimen
    projected = _dossier_of(project_sector_view(inputs, receipt, audience="preview"))
    assert projected["availability"]["mode"] == "dated_snapshot"
    assert projected["availability"]["decision_cutoff"] is None
    assert projected["availability"]["original_available_at"] is None
    assert projected["availability"]["historically_admissible"] is False


def test_as_known_request_withholds_every_measurement(dossier_specimen):
    """An as-known request withholds the measurements; it never carries one.

    The owner supplies no original availability clock under an as-known
    request, so it withholds every value and keeps the packet honest.
    """
    inputs, receipt = dossier_specimen
    rows = _dossier_rows({ident: (None, None) for ident in _NATIVE_DOSSIER_IDS})
    packet = _dossier_packet(rows)
    packet["availability"].update(mode="as_known",
                                  decision_cutoff="2026-11-03T23:59:00+00:00")
    inputs.central["measured_read"]["sector_dossiers"] = packet
    projected = _dossier_of(project_sector_view(inputs, receipt, audience="preview"))
    assert projected["availability"]["mode"] == "as_known"
    assert projected["availability"]["decision_cutoff"] == "2026-11-03T23:59:00+00:00"
    assert projected["availability"]["original_available_at"] is None
    assert projected["availability"]["historically_admissible"] is False
    assert projected["status"] == "unavailable"
    assert projected["measurement_status"] == "unavailable"
    assert all(value is None for group in projected["groups"]
               for value in group["relative_wealth_pct"].values())


@pytest.mark.parametrize("change", [
    lambda d: d["groups"][0].update(group_id="QQQ"),
    lambda d: d["groups"][1].update(group_id="XLK"),
    lambda d: d["groups"][0].update(group_id="xlk"),
    lambda d: d["groups"].pop(),
    lambda d: d["groups"].append(deepcopy(d["groups"][0])),
    lambda d: d["groups"].reverse(),
])
def test_broken_identity_set_fails_closed(dossier_specimen, change):
    inputs, receipt = dossier_specimen
    change(inputs.central["measured_read"]["sector_dossiers"])
    with pytest.raises(SectorViewUnavailable, match="^invalid_sector_dossier_identity$"):
        project_sector_view(inputs, receipt, audience="preview")


@pytest.mark.parametrize("value", [
    True, False, float("nan"), float("inf"), -float("inf"), "3.2", [], {}, -100.1,
])
def test_invalid_measurements_fail_closed_without_losing_the_other_window(
        dossier_specimen, value):
    inputs, receipt = dossier_specimen
    inputs.central["measured_read"]["sector_dossiers"]["groups"][0][
        "relative_wealth_pct"]["rs_21d"] = value
    with pytest.raises(SectorViewUnavailable, match="^invalid_sector_dossiers$"):
        project_sector_view(inputs, receipt, audience="preview")


@pytest.mark.parametrize("block,key,value", [
    ("authority", "may_rank", True),
    ("authority", "may_gate", 1),
    ("authority", "may_size", "false"),
    ("authority", "may_trade", None),
    ("authority", "may_escalate", 0),
    ("forecasts", "expected_return", 0.05),
    ("forecasts", "persistence_estimate", 1.0),
    ("forecasts", "allocation_weight", 0.2),
])
def test_forged_authority_or_forecast_fails_closed(dossier_specimen, block, key, value):
    inputs, receipt = dossier_specimen
    inputs.central["measured_read"]["sector_dossiers"][block][key] = value
    with pytest.raises(SectorViewUnavailable, match="^invalid_sector_dossiers$"):
        project_sector_view(inputs, receipt, audience="preview")


def test_qualified_forecasts_or_reshaped_authority_fail_closed(dossier_specimen):
    inputs, receipt = dossier_specimen
    dossier = inputs.central["measured_read"]["sector_dossiers"]
    dossier["forecasts"]["status"] = "qualified"
    with pytest.raises(SectorViewUnavailable, match="^invalid_sector_dossiers$"):
        project_sector_view(inputs, receipt, audience="preview")
    dossier["forecasts"]["status"] = "not_qualified"
    dossier["authority"].pop("may_escalate")
    with pytest.raises(SectorViewUnavailable, match="^invalid_sector_dossiers$"):
        project_sector_view(inputs, receipt, audience="preview")


@pytest.mark.parametrize("change,code", [
    (lambda d: d.update(as_of="2026-11-04"), "mixed_sector_dossier_binding"),
    (lambda d: d.update(benchmark="QQQ"), "mixed_sector_dossier_binding"),
    (lambda d: d.update(compatibility_key="2026-11-04|SPY|us_sectors_11"),
     "mixed_sector_dossier_binding"),
    (lambda d: d.update(cohort_id="top_6"), "invalid_sector_dossiers"),
    (lambda d: d.update(population="six_sector_etf_proxies"), "invalid_sector_dossiers"),
    (lambda d: d.update(units="ratio"), "invalid_sector_dossiers"),
    (lambda d: d.update(windows_sessions=[21, 63, 126]), "invalid_sector_dossiers"),
    (lambda d: d.update(unavailable_windows={"sessions": [5], "reason": "not_supplied_by_owner"}),
     "invalid_sector_dossiers"),
    (lambda d: d.update(unavailable_windows="SPY"), "invalid_sector_dossiers"),
    (lambda d: d.update(availability={"mode": "live"}), "invalid_sector_dossiers"),
    (lambda d: d.update(dependency_audit="engine.sector_cycles"), "invalid_sector_dossiers"),
    (lambda d: d.update(diagnostics={"qualification_reasons": "none"}),
     "invalid_sector_dossiers"),
    (lambda d: d.update(diagnostics="none"), "invalid_sector_dossiers"),
    (lambda d: d.update(cross_sector_breadth_counts={"21": {"expected_n": 11,
                                                             "measured_n": 11,
                                                             "positive_n": 11}}),
     "invalid_sector_dossiers"),
    (lambda d: d.update(price_basis="price_only"), "invalid_sector_dossiers"),
    (lambda d: d.update(schema="leadership_rotation_context.sector_dossiers/v2"),
     "invalid_sector_dossiers"),
])
def test_dossier_contradicting_its_parent_or_contract_fails_closed(
        dossier_specimen, change, code):
    inputs, receipt = dossier_specimen
    change(inputs.central["measured_read"]["sector_dossiers"])
    with pytest.raises(SectorViewUnavailable, match=f"^{code}$"):
        project_sector_view(inputs, receipt, audience="preview")


@pytest.mark.parametrize("change", [
    lambda m: m["generation"].update(cohort_id="top_6"),
    lambda m: m["generation"].update(id="2026-11-04|SPY|us_sectors_11"),
    lambda m: m["generation"].update(price_basis="price_only"),
    lambda m: m["groups"][5].update(group_id="QQQ"),
])
def test_dossier_conflicting_with_the_carrying_measured_read_fails_closed(
        dossier_specimen, change):
    inputs, receipt = dossier_specimen
    change(inputs.central["measured_read"])
    with pytest.raises(SectorViewUnavailable, match="^mixed_sector_dossier_binding$"):
        project_sector_view(inputs, receipt, audience="preview")


@pytest.mark.parametrize("change", [
    lambda d: d["cross_sector_breadth_counts"]["21"].update(measured_n=10),
    lambda d: d["cross_sector_breadth_counts"]["21"].update(expected_n=12),
    lambda d: d["cross_sector_breadth_counts"]["21"].update(positive_n=3),
    lambda d: d["cross_sector_breadth_counts"]["21"].update(positive_n=True),
    lambda d: d["cross_sector_breadth_counts"].pop("63"),
    lambda d: d.update(status="unavailable"),
    lambda d: d.update(measurement_status="partial"),
    lambda d: d["groups"][0].update(status="partial"),
    lambda d: d["groups"][0].update(null_reasons={"rs_21d": "missing_input",
                                                  "rs_63d": None}),
    lambda d: d["groups"][0].update(relative_wealth_pct={"rs_21d": None, "rs_63d": 3.5},
                                    null_reasons={"rs_21d": None, "rs_63d": None}),
])
def test_inconsistent_counts_status_or_values_fail_closed(dossier_specimen, change):
    inputs, receipt = dossier_specimen
    change(inputs.central["measured_read"]["sector_dossiers"])
    with pytest.raises(SectorViewUnavailable, match="^invalid_sector_dossiers$"):
        project_sector_view(inputs, receipt, audience="preview")


def test_dossier_on_an_outage_stub_fails_closed(specimen):
    inputs, receipt = specimen
    inputs.central["measured_read"] = {
        "schema": "leadership_rotation_context.measured_group_read/v1",
        "status": "unavailable", "reason": "projection_error",
        "sector_dossiers": _dossier_packet(_dossier_rows()),
    }
    with pytest.raises(SectorViewUnavailable, match="^invalid_sector_dossiers$"):
        project_sector_view(inputs, receipt, audience="preview")


def test_dossier_projection_is_detached_from_the_caller(dossier_specimen):
    inputs, receipt = dossier_specimen
    before = deepcopy(inputs)
    first = project_sector_view(inputs, receipt, audience="entitled")
    second = project_sector_view(inputs, receipt, audience="entitled")
    assert first == second
    dossier = _dossier_of(first)
    dossier["groups"][0]["relative_wealth_pct"]["rs_21d"] = 999
    dossier["groups"][0]["qualification_reasons"].append("MUTATED")
    dossier["dependency_audit"]["source_roots"].append("MUTATED")
    assert inputs == before
    # The mutated projection must not alias the inputs or a later projection.
    survivor = _dossier_of(second)
    assert survivor["groups"][0]["relative_wealth_pct"]["rs_21d"] == 1.0
    assert survivor["groups"][0]["qualification_reasons"] == []
    assert survivor["dependency_audit"]["source_roots"] == ["engine.sector_cycles"]


def test_dossier_value_moves_the_authorized_content_hash(dossier_specimen):
    inputs, receipt = dossier_specimen
    first = project_sector_view(inputs, receipt, audience="preview")
    # An authorized value moves in the parent and in the child together: the
    # owner only emits a child value that equals its own parent group.
    inputs.central["measured_read"]["groups"][0]["current"]["rs_21d"] = 2.5
    inputs.central["measured_read"]["sector_dossiers"]["groups"][0][
        "relative_wealth_pct"]["rs_21d"] = 2.5
    second = project_sector_view(inputs, receipt, audience="preview")
    assert first["receipt"]["content_sha256"] != second["receipt"]["content_sha256"]
    assert first["data"]["brief"] == second["data"]["brief"]
    assert first["receipt"]["published_at"] == second["receipt"]["published_at"]


def test_dossier_does_not_bypass_the_existing_byte_ceiling(dossier_specimen):
    inputs, receipt = dossier_specimen
    inputs.handoff["theme_context"]["leadership"]["stance_en"] = "x" * (4 * 1024 * 1024)
    with pytest.raises(SectorViewUnavailable, match="^projection_too_large$"):
        project_sector_view(inputs, receipt, audience="preview")
    inputs.handoff["theme_context"]["leadership"]["stance_en"] = "Existing owner stance."
    inputs.central["measured_read"]["sector_dossiers"]["groups"][0]["name_en"] = "x" * 4096
    with pytest.raises(SectorViewUnavailable, match="^invalid_sector_dossiers$"):
        project_sector_view(inputs, receipt, audience="preview")


def test_dossier_projection_never_reads_a_loader_or_clock(dossier_specimen, monkeypatch):
    import builtins
    import engine.sector_native_view as module
    from datetime import datetime

    class NoClock(datetime):
        @classmethod
        def now(cls, *args, **kwargs):
            raise AssertionError("implicit current clock")

    def forbidden(*args, **kwargs):
        raise AssertionError("implicit data or configuration load")

    inputs, receipt = dossier_specimen
    with monkeypatch.context() as m:
        m.setattr(builtins, "open", forbidden)
        m.setattr(Path, "read_text", forbidden)
        m.setattr(Path, "read_bytes", forbidden)
        m.setattr(module, "datetime", NoClock)
        result = project_sector_view(inputs, receipt, audience="preview")
    assert len(_dossier_of(result)["groups"]) == 11


@pytest.mark.parametrize("change", [
    lambda d: d["source_generation"].update(id="2026-11-03|SPY|us_sectors_11"),
    lambda d: d["availability"].update(mode="live"),
    lambda d: d["availability"].update(decision_cutoff="not-a-time"),
    lambda d: d["availability"].update(decision_cutoff="2026-11-03T00:00:00"),
    lambda d: d["dependency_audit"].update(source_roots="engine.sector_cycles"),
    lambda d: d["availability"].update(original_available_at="2026-11-03T00:00:00Z"),
    lambda d: d["availability"].update(historically_admissible=True),
    lambda d: d["history"].update(naturally_observed=True),
    lambda d: d["history"].update(mode="observed_price_history"),
    lambda d: d["freshness"].update(status="verified"),
    lambda d: d["corrections"].update(status="no_correction"),
    lambda d: d["constituent_breadth"].update(status="available"),
    lambda d: d["constituent_concentration"].update(status="available"),
    lambda d: d["dependency_audit"].update(independence="established"),
    lambda d: d["dependency_audit"].update(shared_rolling_windows=False),
    lambda d: d["risk"].update(scope="sector"),
    lambda d: d["mechanism"].update(status="available"),
    lambda d: d["absolute_returns"].update(status="available"),
    lambda d: d["source_generation"].update(status="available"),
])
def test_stated_limitations_cannot_be_promoted(dossier_specimen, change):
    """A stated limitation stays stated; it is never upgraded into a capability."""
    inputs, receipt = dossier_specimen
    change(inputs.central["measured_read"]["sector_dossiers"])
    with pytest.raises(SectorViewUnavailable, match="^invalid_sector_dossiers$"):
        project_sector_view(inputs, receipt, audience="preview")


def test_unavailable_provenance_and_limitations_are_preserved(dossier_specimen):
    inputs, receipt = dossier_specimen
    dossier = _dossier_of(project_sector_view(inputs, receipt, audience="preview"))
    assert dossier["absolute_returns"]["status"] == "unavailable"
    assert dossier["constituent_breadth"]["status"] == "unavailable"
    assert dossier["constituent_concentration"]["status"] == "unavailable"
    assert dossier["mechanism"]["status"] == "unavailable"
    assert dossier["risk"]["status"] == "unavailable"
    assert dossier["risk"]["scope"] is None
    assert dossier["dependency_audit"]["independence"] == "not_established"
    assert dossier["dependency_audit"]["shared_rolling_windows"] is True
    # The compatibility key is a compatibility key, never a generation identity.
    assert dossier["compatibility_key"] == "2026-11-03|SPY|us_sectors_11"
    assert dossier["source_generation"]["id"] is None


# --- Persistent Sector Leadership: the dossier stays bound to its parent ------
# The owner emits a non-null child measurement only when it equals the measured
# read of the SAME parent group, and it withholds every measurement whenever
# its own qualification reasons are non-empty. These cases hold the projector
# to that contract.


@pytest.mark.parametrize("field,value", [
    ("rs_21d", 99.5),
    ("rs_63d", 88.25),
])
def test_child_only_measurement_mutation_is_refused(dossier_specimen, field, value):
    """A child measurement that detaches from its own parent group is refused."""
    inputs, receipt = dossier_specimen
    inputs.central["measured_read"]["sector_dossiers"]["groups"][0][
        "relative_wealth_pct"][field] = value
    with pytest.raises(SectorViewUnavailable, match="^mixed_sector_dossier_binding$"):
        project_sector_view(inputs, receipt, audience="preview")


def test_child_measurement_over_a_null_parent_field_is_refused(dossier_specimen):
    """A child value where its own parent group has none is refused."""
    inputs, receipt = dossier_specimen
    inputs.central["measured_read"]["groups"][0]["current"]["rs_63d"] = None
    with pytest.raises(SectorViewUnavailable, match="^mixed_sector_dossier_binding$"):
        project_sector_view(inputs, receipt, audience="preview")


def test_a_withheld_child_measurement_is_never_completed_from_the_parent(dossier_specimen):
    """The owner can qualify more strictly than the parent; the gap stays a gap."""
    inputs, receipt = dossier_specimen
    rows = _dossier_rows({"XLB": (1.0, None)})
    inputs.central["measured_read"]["sector_dossiers"] = _dossier_packet(rows)
    parent = inputs.central["measured_read"]["groups"][0]["current"]
    assert parent["rs_63d"] == 2.0
    dossier = _dossier_of(project_sector_view(inputs, receipt, audience="preview"))
    assert dossier["groups"][0]["relative_wealth_pct"]["rs_63d"] is None
    assert dossier["groups"][0]["null_reasons"]["rs_63d"] == "missing_input"


def test_a_null_parent_measurement_keeps_a_null_child(dossier_specimen):
    inputs, receipt = dossier_specimen
    inputs.central["measured_read"]["groups"][0]["current"]["rs_63d"] = None
    rows = _dossier_rows({"XLB": (1.0, None)})
    inputs.central["measured_read"]["sector_dossiers"] = _dossier_packet(rows)
    dossier = _dossier_of(project_sector_view(inputs, receipt, audience="preview"))
    assert dossier["groups"][0]["relative_wealth_pct"]["rs_63d"] is None


@pytest.mark.parametrize("roots,count", [
    (["engine.sector_cycles", "engine.other_family"], 2),
    (["engine.sector_cycles", "engine.sector_cycles"], 2),
    (["engine.other_family"], 1),
    ([], 1),
    (["engine.sector_cycles"], 2),
    (["engine.sector_cycles"], 0),
])
def test_source_family_semantics_are_the_owner_closed_set(dossier_specimen, roots, count):
    """One source family, or none: never a foreign, duplicate or counted twice."""
    inputs, receipt = dossier_specimen
    audit = inputs.central["measured_read"]["sector_dossiers"]["dependency_audit"]
    audit["source_roots"] = roots
    audit["source_family_count"] = count
    with pytest.raises(SectorViewUnavailable, match="^invalid_sector_dossiers$"):
        project_sector_view(inputs, receipt, audience="preview")


def test_an_unattributed_source_root_cannot_carry_measurements(dossier_specimen):
    inputs, receipt = dossier_specimen
    audit = inputs.central["measured_read"]["sector_dossiers"]["dependency_audit"]
    audit["source_roots"] = []
    audit["source_family_count"] = 0
    with pytest.raises(SectorViewUnavailable, match="^invalid_sector_dossiers$"):
        project_sector_view(inputs, receipt, audience="preview")


def test_the_source_family_is_the_owner_closed_set(dossier_specimen):
    inputs, receipt = dossier_specimen
    audit = _dossier_of(project_sector_view(inputs, receipt, audience="preview"))
    assert audit["dependency_audit"]["source_roots"] == ["engine.sector_cycles"]
    assert audit["dependency_audit"]["source_family_count"] == 1
    assert audit["dependency_audit"]["independence"] == "not_established"


def test_forged_as_known_packet_cannot_carry_measurements(dossier_specimen):
    """An as-known request withholds the measurements, so it may not carry one."""
    inputs, receipt = dossier_specimen
    inputs.central["measured_read"]["sector_dossiers"]["availability"].update(
        mode="as_known", decision_cutoff="2026-11-03T23:59:00+00:00")
    with pytest.raises(SectorViewUnavailable, match="^invalid_sector_dossiers$"):
        project_sector_view(inputs, receipt, audience="preview")


def test_dated_snapshot_cannot_carry_a_decision_cutoff(dossier_specimen):
    inputs, receipt = dossier_specimen
    inputs.central["measured_read"]["sector_dossiers"]["availability"].update(
        decision_cutoff="2026-11-03T23:59:00+00:00")
    with pytest.raises(SectorViewUnavailable, match="^invalid_sector_dossiers$"):
        project_sector_view(inputs, receipt, audience="preview")


@pytest.mark.parametrize("field", ["price_basis", "as_of"])
def test_a_withheld_qualification_cannot_carry_measurements(dossier_specimen, field):
    """The owner withholds every value when its own qualification is absent."""
    inputs, receipt = dossier_specimen
    inputs.central["measured_read"]["sector_dossiers"][field] = None
    with pytest.raises(SectorViewUnavailable, match="^invalid_sector_dossiers$"):
        project_sector_view(inputs, receipt, audience="preview")


def test_measurements_require_a_qualified_parent_return_basis(dossier_specimen):
    inputs, receipt = dossier_specimen
    inputs.central["measured_read"]["generation"]["price_basis"] = None
    with pytest.raises(SectorViewUnavailable, match="^mixed_sector_dossier_binding$"):
        project_sector_view(inputs, receipt, audience="preview")

# --- BEGIN PSL NATIVE QUALIFICATION CONTRACT TESTS ---
# --- Persistent Sector Leadership: the owner's own qualification contract ---
# The dossier producer is the owner's engine/leadership_rotation_context.py at
# 5b4962a381711328cc01dbe788f9ca4b5f4f7e4d (blob
# 49f160a8d661e8be2dc7fb072f9406888967c8fc, raw sha256
# 6b38a6524cf2698b47e3b946550a246e6d3ebcc90f93644be1a8d77fdf96dfcf). That
# producer is not part of this repository revision, so the packets below are
# the bytes that exact producer composed: the positive cases are the owner's
# own output rather than a hand-written fixture, and their digests pin them.
_PRODUCER_COMMIT = "5b4962a381711328cc01dbe788f9ca4b5f4f7e4d"
_PRODUCER_BLOB = "49f160a8d661e8be2dc7fb072f9406888967c8fc"
_PRODUCER_SOURCE_SHA256 = (
    "6b38a6524cf2698b47e3b946550a246e6d3ebcc90f93644be1a8d77fdf96dfcf")

# The owner's own canonical input pair, and the one edit each variant applies
# to it. The producer composes every packet from these two documents.
_GENUINE_INPUTS_JSON = r"""{"cycles":{"meta":{"asOf":"2026-11-03","benchmark":"SPY","rs_history":{"as_of":"2026-11-03","basis":"tr","benchmark":"SPY","mode":"reconstructed_price_history","naturally_observed":false,"schema":"sector_cycles.rs_history.v1"}},"sectors":[{"kind":"sector","now":{"rs_21d":1.0,"rs_63d":2.0},"ticker":"XLB"},{"kind":"sector","now":{"rs_21d":2.0,"rs_63d":3.0},"ticker":"XLC"},{"kind":"sector","now":{"rs_21d":3.0,"rs_63d":4.0},"ticker":"XLE"},{"kind":"sector","now":{"rs_21d":4.0,"rs_63d":5.0},"ticker":"XLF"},{"kind":"sector","now":{"rs_21d":5.0,"rs_63d":6.0},"ticker":"XLI"},{"kind":"sector","now":{"rs_21d":6.0,"rs_63d":7.0},"ticker":"XLK"},{"kind":"sector","now":{"rs_21d":7.0,"rs_63d":8.0},"ticker":"XLP"},{"kind":"sector","now":{"rs_21d":8.0,"rs_63d":9.0},"ticker":"XLRE"},{"kind":"sector","now":{"rs_21d":9.0,"rs_63d":10.0},"ticker":"XLU"},{"kind":"sector","now":{"rs_21d":10.0,"rs_63d":11.0},"ticker":"XLV"},{"kind":"sector","now":{"rs_21d":11.0,"rs_63d":12.0},"ticker":"XLY"}]},"read":{"cohort":{"expected_n":11,"horizon":"rs_21d","measured_n":11},"generation":{"benchmark":"SPY","cohort_id":"us_sectors_11","id":"2026-11-03|SPY|us_sectors_11","price_basis":"total_return","session_end":"2026-11-03"},"groups":[{"current":{"metric":"relative_wealth_pct","rank":1,"reason":null,"rs_21d":1.0,"rs_63d":2.0,"status":"measured","units":"pct","z":0.5},"group_id":"XLB","group_kind":"sector","name_en":"XLB Sector","name_zh":null},{"current":{"metric":"relative_wealth_pct","rank":2,"reason":null,"rs_21d":2.0,"rs_63d":3.0,"status":"measured","units":"pct","z":0.5},"group_id":"XLC","group_kind":"sector","name_en":"XLC Sector","name_zh":null},{"current":{"metric":"relative_wealth_pct","rank":3,"reason":null,"rs_21d":3.0,"rs_63d":4.0,"status":"measured","units":"pct","z":0.5},"group_id":"XLE","group_kind":"sector","name_en":"XLE Sector","name_zh":null},{"current":{"metric":"relative_wealth_pct","rank":4,"reason":null,"rs_21d":4.0,"rs_63d":5.0,"status":"measured","units":"pct","z":0.5},"group_id":"XLF","group_kind":"sector","name_en":"XLF Sector","name_zh":null},{"current":{"metric":"relative_wealth_pct","rank":5,"reason":null,"rs_21d":5.0,"rs_63d":6.0,"status":"measured","units":"pct","z":0.5},"group_id":"XLI","group_kind":"sector","name_en":"XLI Sector","name_zh":null},{"current":{"metric":"relative_wealth_pct","rank":6,"reason":null,"rs_21d":6.0,"rs_63d":7.0,"status":"measured","units":"pct","z":0.5},"group_id":"XLK","group_kind":"sector","name_en":"XLK Sector","name_zh":null},{"current":{"metric":"relative_wealth_pct","rank":7,"reason":null,"rs_21d":7.0,"rs_63d":8.0,"status":"measured","units":"pct","z":0.5},"group_id":"XLP","group_kind":"sector","name_en":"XLP Sector","name_zh":null},{"current":{"metric":"relative_wealth_pct","rank":8,"reason":null,"rs_21d":8.0,"rs_63d":9.0,"status":"measured","units":"pct","z":0.5},"group_id":"XLRE","group_kind":"sector","name_en":"XLRE Sector","name_zh":null},{"current":{"metric":"relative_wealth_pct","rank":9,"reason":null,"rs_21d":9.0,"rs_63d":10.0,"status":"measured","units":"pct","z":0.5},"group_id":"XLU","group_kind":"sector","name_en":"XLU Sector","name_zh":null},{"current":{"metric":"relative_wealth_pct","rank":10,"reason":null,"rs_21d":10.0,"rs_63d":11.0,"status":"measured","units":"pct","z":0.5},"group_id":"XLV","group_kind":"sector","name_en":"XLV Sector","name_zh":null},{"current":{"metric":"relative_wealth_pct","rank":11,"reason":null,"rs_21d":11.0,"rs_63d":12.0,"status":"measured","units":"pct","z":0.5},"group_id":"XLY","group_kind":"sector","name_en":"XLY Sector","name_zh":null}],"schema":"leadership_rotation_context.measured_group_read/v1","source_roots":["engine.sector_cycles"],"status":"available"}}"""
_GENUINE_VARIANTS_JSON = r"""{"baseline":{},"duplicate_source":{"extra_source_rows":[{"kind":"sector","now":{"rs_21d":1.0,"rs_63d":2.0},"ticker":"XLB"}]},"global_and_duplicate":{"extra_source_rows":[{"kind":"sector","now":{"rs_21d":1.0,"rs_63d":2.0},"ticker":"XLB"}],"history":{"as_of":"2026-10-30"}},"global_qualified":{"history":{"as_of":"2026-10-30"}},"independent_missing_window":{"read_null_rs_63d":["XLB"],"source_null_rs_63d":["XLB"]},"malformed_source_12":{"extra_source_rows":[{"kind":"sector","now":{},"ticker":"TOOLONGIDENTITY0"},{"kind":"sector","now":{},"ticker":"TOOLONGIDENTITY1"},{"kind":"sector","now":{},"ticker":"TOOLONGIDENTITY2"},{"kind":"sector","now":{},"ticker":"TOOLONGIDENTITY3"},{"kind":"sector","now":{},"ticker":"TOOLONGIDENTITY4"},{"kind":"sector","now":{},"ticker":"TOOLONGIDENTITY5"},{"kind":"sector","now":{},"ticker":"TOOLONGIDENTITY6"},{"kind":"sector","now":{},"ticker":"TOOLONGIDENTITY7"},{"kind":"sector","now":{},"ticker":"TOOLONGIDENTITY8"},{"kind":"sector","now":{},"ticker":"TOOLONGIDENTITY9"},{"kind":"sector","now":{},"ticker":"TOOLONGIDENTITY10"},{"kind":"sector","now":{},"ticker":"TOOLONGIDENTITY11"}]},"multi_global_reasons":{"history":{"as_of":"2026-10-30","mode":"observed_price_history","schema":"sector_cycles.rs_history.v2"}},"outside_cohort":{"extra_source_rows":[{"kind":"sector","now":{},"ticker":"XLCB"}]}}"""
# The packets the producer composed from them.
_GENUINE_PACKETS_JSON = r"""{"baseline":{"absolute_returns":{"reason":"not_supplied_by_owner","status":"unavailable"},"as_of":"2026-11-03","authority":{"may_escalate":false,"may_gate":false,"may_rank":false,"may_size":false,"may_trade":false},"availability":{"decision_cutoff":null,"historically_admissible":false,"mode":"dated_snapshot","original_available_at":null,"reason":"original_availability_not_supplied"},"benchmark":"SPY","cohort_id":"us_sectors_11","compatibility_key":"2026-11-03|SPY|us_sectors_11","constituent_breadth":{"reason":"native_membership_not_supplied","status":"unavailable"},"constituent_concentration":{"reason":"native_weights_not_supplied","status":"unavailable"},"corrections":{"reason":"native_revision_selection_not_supplied","status":"unavailable"},"cross_sector_breadth_counts":{"21":{"expected_n":11,"measured_n":11,"positive_n":11},"63":{"expected_n":11,"measured_n":11,"positive_n":11}},"dependency_audit":{"constituent_overlap":"unknown","independence":"not_established","shared_rolling_windows":true,"source_family_count":1,"source_roots":["engine.sector_cycles"]},"diagnostics":{"duplicate_groups":[],"malformed_measured_rows":0,"malformed_source_rows":0,"outside_cohort":[],"qualification_reasons":[]},"forecasts":{"allocation_weight":null,"expected_return":null,"persistence_estimate":null,"status":"not_qualified"},"freshness":{"reason":"owner_freshness_receipt_not_supplied","status":"unverified"},"groups":[{"group_id":"XLB","name_en":"XLB Sector","name_zh":null,"null_reasons":{"rs_21d":null,"rs_63d":null},"qualification_reasons":[],"relative_wealth_pct":{"rs_21d":1.0,"rs_63d":2.0},"status":"available"},{"group_id":"XLC","name_en":"XLC Sector","name_zh":null,"null_reasons":{"rs_21d":null,"rs_63d":null},"qualification_reasons":[],"relative_wealth_pct":{"rs_21d":2.0,"rs_63d":3.0},"status":"available"},{"group_id":"XLE","name_en":"XLE Sector","name_zh":null,"null_reasons":{"rs_21d":null,"rs_63d":null},"qualification_reasons":[],"relative_wealth_pct":{"rs_21d":3.0,"rs_63d":4.0},"status":"available"},{"group_id":"XLF","name_en":"XLF Sector","name_zh":null,"null_reasons":{"rs_21d":null,"rs_63d":null},"qualification_reasons":[],"relative_wealth_pct":{"rs_21d":4.0,"rs_63d":5.0},"status":"available"},{"group_id":"XLI","name_en":"XLI Sector","name_zh":null,"null_reasons":{"rs_21d":null,"rs_63d":null},"qualification_reasons":[],"relative_wealth_pct":{"rs_21d":5.0,"rs_63d":6.0},"status":"available"},{"group_id":"XLK","name_en":"XLK Sector","name_zh":null,"null_reasons":{"rs_21d":null,"rs_63d":null},"qualification_reasons":[],"relative_wealth_pct":{"rs_21d":6.0,"rs_63d":7.0},"status":"available"},{"group_id":"XLP","name_en":"XLP Sector","name_zh":null,"null_reasons":{"rs_21d":null,"rs_63d":null},"qualification_reasons":[],"relative_wealth_pct":{"rs_21d":7.0,"rs_63d":8.0},"status":"available"},{"group_id":"XLRE","name_en":"XLRE Sector","name_zh":null,"null_reasons":{"rs_21d":null,"rs_63d":null},"qualification_reasons":[],"relative_wealth_pct":{"rs_21d":8.0,"rs_63d":9.0},"status":"available"},{"group_id":"XLU","name_en":"XLU Sector","name_zh":null,"null_reasons":{"rs_21d":null,"rs_63d":null},"qualification_reasons":[],"relative_wealth_pct":{"rs_21d":9.0,"rs_63d":10.0},"status":"available"},{"group_id":"XLV","name_en":"XLV Sector","name_zh":null,"null_reasons":{"rs_21d":null,"rs_63d":null},"qualification_reasons":[],"relative_wealth_pct":{"rs_21d":10.0,"rs_63d":11.0},"status":"available"},{"group_id":"XLY","name_en":"XLY Sector","name_zh":null,"null_reasons":{"rs_21d":null,"rs_63d":null},"qualification_reasons":[],"relative_wealth_pct":{"rs_21d":11.0,"rs_63d":12.0},"status":"available"}],"history":{"mode":"reconstructed_price_history","naturally_observed":false},"measurement_status":"available","mechanism":{"owner":"engine.theme_graph","reason":"no_qualified_evidence","status":"unavailable"},"population":"eleven_sector_etf_proxies","price_basis":"total_return","risk":{"owner":"engine.risk_envelope","reason":"no_qualified_risk_context","scope":null,"status":"unavailable"},"schema":"leadership_rotation_context.sector_dossiers/v1","source_generation":{"id":null,"reason":"immutable_generation_not_supplied","status":"unavailable"},"status":"partial","unavailable_windows":{"reason":"not_supplied_by_owner","sessions":[5,20]},"units":"pct","windows_sessions":[21,63]},"duplicate_source":{"absolute_returns":{"reason":"not_supplied_by_owner","status":"unavailable"},"as_of":"2026-11-03","authority":{"may_escalate":false,"may_gate":false,"may_rank":false,"may_size":false,"may_trade":false},"availability":{"decision_cutoff":null,"historically_admissible":false,"mode":"dated_snapshot","original_available_at":null,"reason":"original_availability_not_supplied"},"benchmark":"SPY","cohort_id":"us_sectors_11","compatibility_key":"2026-11-03|SPY|us_sectors_11","constituent_breadth":{"reason":"native_membership_not_supplied","status":"unavailable"},"constituent_concentration":{"reason":"native_weights_not_supplied","status":"unavailable"},"corrections":{"reason":"native_revision_selection_not_supplied","status":"unavailable"},"cross_sector_breadth_counts":{"21":{"expected_n":11,"measured_n":10,"positive_n":10},"63":{"expected_n":11,"measured_n":10,"positive_n":10}},"dependency_audit":{"constituent_overlap":"unknown","independence":"not_established","shared_rolling_windows":true,"source_family_count":1,"source_roots":["engine.sector_cycles"]},"diagnostics":{"duplicate_groups":["XLB"],"malformed_measured_rows":0,"malformed_source_rows":0,"outside_cohort":[],"qualification_reasons":[]},"forecasts":{"allocation_weight":null,"expected_return":null,"persistence_estimate":null,"status":"not_qualified"},"freshness":{"reason":"owner_freshness_receipt_not_supplied","status":"unverified"},"groups":[{"group_id":"XLB","name_en":"XLB Sector","name_zh":null,"null_reasons":{"rs_21d":"duplicate_group_identity","rs_63d":"duplicate_group_identity"},"qualification_reasons":["duplicate_group_identity"],"relative_wealth_pct":{"rs_21d":null,"rs_63d":null},"status":"unavailable"},{"group_id":"XLC","name_en":"XLC Sector","name_zh":null,"null_reasons":{"rs_21d":null,"rs_63d":null},"qualification_reasons":[],"relative_wealth_pct":{"rs_21d":2.0,"rs_63d":3.0},"status":"available"},{"group_id":"XLE","name_en":"XLE Sector","name_zh":null,"null_reasons":{"rs_21d":null,"rs_63d":null},"qualification_reasons":[],"relative_wealth_pct":{"rs_21d":3.0,"rs_63d":4.0},"status":"available"},{"group_id":"XLF","name_en":"XLF Sector","name_zh":null,"null_reasons":{"rs_21d":null,"rs_63d":null},"qualification_reasons":[],"relative_wealth_pct":{"rs_21d":4.0,"rs_63d":5.0},"status":"available"},{"group_id":"XLI","name_en":"XLI Sector","name_zh":null,"null_reasons":{"rs_21d":null,"rs_63d":null},"qualification_reasons":[],"relative_wealth_pct":{"rs_21d":5.0,"rs_63d":6.0},"status":"available"},{"group_id":"XLK","name_en":"XLK Sector","name_zh":null,"null_reasons":{"rs_21d":null,"rs_63d":null},"qualification_reasons":[],"relative_wealth_pct":{"rs_21d":6.0,"rs_63d":7.0},"status":"available"},{"group_id":"XLP","name_en":"XLP Sector","name_zh":null,"null_reasons":{"rs_21d":null,"rs_63d":null},"qualification_reasons":[],"relative_wealth_pct":{"rs_21d":7.0,"rs_63d":8.0},"status":"available"},{"group_id":"XLRE","name_en":"XLRE Sector","name_zh":null,"null_reasons":{"rs_21d":null,"rs_63d":null},"qualification_reasons":[],"relative_wealth_pct":{"rs_21d":8.0,"rs_63d":9.0},"status":"available"},{"group_id":"XLU","name_en":"XLU Sector","name_zh":null,"null_reasons":{"rs_21d":null,"rs_63d":null},"qualification_reasons":[],"relative_wealth_pct":{"rs_21d":9.0,"rs_63d":10.0},"status":"available"},{"group_id":"XLV","name_en":"XLV Sector","name_zh":null,"null_reasons":{"rs_21d":null,"rs_63d":null},"qualification_reasons":[],"relative_wealth_pct":{"rs_21d":10.0,"rs_63d":11.0},"status":"available"},{"group_id":"XLY","name_en":"XLY Sector","name_zh":null,"null_reasons":{"rs_21d":null,"rs_63d":null},"qualification_reasons":[],"relative_wealth_pct":{"rs_21d":11.0,"rs_63d":12.0},"status":"available"}],"history":{"mode":"reconstructed_price_history","naturally_observed":false},"measurement_status":"partial","mechanism":{"owner":"engine.theme_graph","reason":"no_qualified_evidence","status":"unavailable"},"population":"eleven_sector_etf_proxies","price_basis":"total_return","risk":{"owner":"engine.risk_envelope","reason":"no_qualified_risk_context","scope":null,"status":"unavailable"},"schema":"leadership_rotation_context.sector_dossiers/v1","source_generation":{"id":null,"reason":"immutable_generation_not_supplied","status":"unavailable"},"status":"partial","unavailable_windows":{"reason":"not_supplied_by_owner","sessions":[5,20]},"units":"pct","windows_sessions":[21,63]},"global_and_duplicate":{"absolute_returns":{"reason":"not_supplied_by_owner","status":"unavailable"},"as_of":"2026-11-03","authority":{"may_escalate":false,"may_gate":false,"may_rank":false,"may_size":false,"may_trade":false},"availability":{"decision_cutoff":null,"historically_admissible":false,"mode":"dated_snapshot","original_available_at":null,"reason":"original_availability_not_supplied"},"benchmark":"SPY","cohort_id":"us_sectors_11","compatibility_key":"2026-11-03|SPY|us_sectors_11","constituent_breadth":{"reason":"native_membership_not_supplied","status":"unavailable"},"constituent_concentration":{"reason":"native_weights_not_supplied","status":"unavailable"},"corrections":{"reason":"native_revision_selection_not_supplied","status":"unavailable"},"cross_sector_breadth_counts":{"21":{"expected_n":11,"measured_n":0,"positive_n":null},"63":{"expected_n":11,"measured_n":0,"positive_n":null}},"dependency_audit":{"constituent_overlap":"unknown","independence":"not_established","shared_rolling_windows":true,"source_family_count":1,"source_roots":["engine.sector_cycles"]},"diagnostics":{"duplicate_groups":["XLB"],"malformed_measured_rows":0,"malformed_source_rows":0,"outside_cohort":[],"qualification_reasons":["history_session_mismatch"]},"forecasts":{"allocation_weight":null,"expected_return":null,"persistence_estimate":null,"status":"not_qualified"},"freshness":{"reason":"owner_freshness_receipt_not_supplied","status":"unverified"},"groups":[{"group_id":"XLB","name_en":"XLB Sector","name_zh":null,"null_reasons":{"rs_21d":"history_session_mismatch","rs_63d":"history_session_mismatch"},"qualification_reasons":["duplicate_group_identity","history_session_mismatch"],"relative_wealth_pct":{"rs_21d":null,"rs_63d":null},"status":"unavailable"},{"group_id":"XLC","name_en":"XLC Sector","name_zh":null,"null_reasons":{"rs_21d":"history_session_mismatch","rs_63d":"history_session_mismatch"},"qualification_reasons":["history_session_mismatch"],"relative_wealth_pct":{"rs_21d":null,"rs_63d":null},"status":"unavailable"},{"group_id":"XLE","name_en":"XLE Sector","name_zh":null,"null_reasons":{"rs_21d":"history_session_mismatch","rs_63d":"history_session_mismatch"},"qualification_reasons":["history_session_mismatch"],"relative_wealth_pct":{"rs_21d":null,"rs_63d":null},"status":"unavailable"},{"group_id":"XLF","name_en":"XLF Sector","name_zh":null,"null_reasons":{"rs_21d":"history_session_mismatch","rs_63d":"history_session_mismatch"},"qualification_reasons":["history_session_mismatch"],"relative_wealth_pct":{"rs_21d":null,"rs_63d":null},"status":"unavailable"},{"group_id":"XLI","name_en":"XLI Sector","name_zh":null,"null_reasons":{"rs_21d":"history_session_mismatch","rs_63d":"history_session_mismatch"},"qualification_reasons":["history_session_mismatch"],"relative_wealth_pct":{"rs_21d":null,"rs_63d":null},"status":"unavailable"},{"group_id":"XLK","name_en":"XLK Sector","name_zh":null,"null_reasons":{"rs_21d":"history_session_mismatch","rs_63d":"history_session_mismatch"},"qualification_reasons":["history_session_mismatch"],"relative_wealth_pct":{"rs_21d":null,"rs_63d":null},"status":"unavailable"},{"group_id":"XLP","name_en":"XLP Sector","name_zh":null,"null_reasons":{"rs_21d":"history_session_mismatch","rs_63d":"history_session_mismatch"},"qualification_reasons":["history_session_mismatch"],"relative_wealth_pct":{"rs_21d":null,"rs_63d":null},"status":"unavailable"},{"group_id":"XLRE","name_en":"XLRE Sector","name_zh":null,"null_reasons":{"rs_21d":"history_session_mismatch","rs_63d":"history_session_mismatch"},"qualification_reasons":["history_session_mismatch"],"relative_wealth_pct":{"rs_21d":null,"rs_63d":null},"status":"unavailable"},{"group_id":"XLU","name_en":"XLU Sector","name_zh":null,"null_reasons":{"rs_21d":"history_session_mismatch","rs_63d":"history_session_mismatch"},"qualification_reasons":["history_session_mismatch"],"relative_wealth_pct":{"rs_21d":null,"rs_63d":null},"status":"unavailable"},{"group_id":"XLV","name_en":"XLV Sector","name_zh":null,"null_reasons":{"rs_21d":"history_session_mismatch","rs_63d":"history_session_mismatch"},"qualification_reasons":["history_session_mismatch"],"relative_wealth_pct":{"rs_21d":null,"rs_63d":null},"status":"unavailable"},{"group_id":"XLY","name_en":"XLY Sector","name_zh":null,"null_reasons":{"rs_21d":"history_session_mismatch","rs_63d":"history_session_mismatch"},"qualification_reasons":["history_session_mismatch"],"relative_wealth_pct":{"rs_21d":null,"rs_63d":null},"status":"unavailable"}],"history":{"mode":"reconstructed_price_history","naturally_observed":false},"measurement_status":"unavailable","mechanism":{"owner":"engine.theme_graph","reason":"no_qualified_evidence","status":"unavailable"},"population":"eleven_sector_etf_proxies","price_basis":"total_return","risk":{"owner":"engine.risk_envelope","reason":"no_qualified_risk_context","scope":null,"status":"unavailable"},"schema":"leadership_rotation_context.sector_dossiers/v1","source_generation":{"id":null,"reason":"immutable_generation_not_supplied","status":"unavailable"},"status":"unavailable","unavailable_windows":{"reason":"not_supplied_by_owner","sessions":[5,20]},"units":"pct","windows_sessions":[21,63]},"global_qualified":{"absolute_returns":{"reason":"not_supplied_by_owner","status":"unavailable"},"as_of":"2026-11-03","authority":{"may_escalate":false,"may_gate":false,"may_rank":false,"may_size":false,"may_trade":false},"availability":{"decision_cutoff":null,"historically_admissible":false,"mode":"dated_snapshot","original_available_at":null,"reason":"original_availability_not_supplied"},"benchmark":"SPY","cohort_id":"us_sectors_11","compatibility_key":"2026-11-03|SPY|us_sectors_11","constituent_breadth":{"reason":"native_membership_not_supplied","status":"unavailable"},"constituent_concentration":{"reason":"native_weights_not_supplied","status":"unavailable"},"corrections":{"reason":"native_revision_selection_not_supplied","status":"unavailable"},"cross_sector_breadth_counts":{"21":{"expected_n":11,"measured_n":0,"positive_n":null},"63":{"expected_n":11,"measured_n":0,"positive_n":null}},"dependency_audit":{"constituent_overlap":"unknown","independence":"not_established","shared_rolling_windows":true,"source_family_count":1,"source_roots":["engine.sector_cycles"]},"diagnostics":{"duplicate_groups":[],"malformed_measured_rows":0,"malformed_source_rows":0,"outside_cohort":[],"qualification_reasons":["history_session_mismatch"]},"forecasts":{"allocation_weight":null,"expected_return":null,"persistence_estimate":null,"status":"not_qualified"},"freshness":{"reason":"owner_freshness_receipt_not_supplied","status":"unverified"},"groups":[{"group_id":"XLB","name_en":"XLB Sector","name_zh":null,"null_reasons":{"rs_21d":"history_session_mismatch","rs_63d":"history_session_mismatch"},"qualification_reasons":["history_session_mismatch"],"relative_wealth_pct":{"rs_21d":null,"rs_63d":null},"status":"unavailable"},{"group_id":"XLC","name_en":"XLC Sector","name_zh":null,"null_reasons":{"rs_21d":"history_session_mismatch","rs_63d":"history_session_mismatch"},"qualification_reasons":["history_session_mismatch"],"relative_wealth_pct":{"rs_21d":null,"rs_63d":null},"status":"unavailable"},{"group_id":"XLE","name_en":"XLE Sector","name_zh":null,"null_reasons":{"rs_21d":"history_session_mismatch","rs_63d":"history_session_mismatch"},"qualification_reasons":["history_session_mismatch"],"relative_wealth_pct":{"rs_21d":null,"rs_63d":null},"status":"unavailable"},{"group_id":"XLF","name_en":"XLF Sector","name_zh":null,"null_reasons":{"rs_21d":"history_session_mismatch","rs_63d":"history_session_mismatch"},"qualification_reasons":["history_session_mismatch"],"relative_wealth_pct":{"rs_21d":null,"rs_63d":null},"status":"unavailable"},{"group_id":"XLI","name_en":"XLI Sector","name_zh":null,"null_reasons":{"rs_21d":"history_session_mismatch","rs_63d":"history_session_mismatch"},"qualification_reasons":["history_session_mismatch"],"relative_wealth_pct":{"rs_21d":null,"rs_63d":null},"status":"unavailable"},{"group_id":"XLK","name_en":"XLK Sector","name_zh":null,"null_reasons":{"rs_21d":"history_session_mismatch","rs_63d":"history_session_mismatch"},"qualification_reasons":["history_session_mismatch"],"relative_wealth_pct":{"rs_21d":null,"rs_63d":null},"status":"unavailable"},{"group_id":"XLP","name_en":"XLP Sector","name_zh":null,"null_reasons":{"rs_21d":"history_session_mismatch","rs_63d":"history_session_mismatch"},"qualification_reasons":["history_session_mismatch"],"relative_wealth_pct":{"rs_21d":null,"rs_63d":null},"status":"unavailable"},{"group_id":"XLRE","name_en":"XLRE Sector","name_zh":null,"null_reasons":{"rs_21d":"history_session_mismatch","rs_63d":"history_session_mismatch"},"qualification_reasons":["history_session_mismatch"],"relative_wealth_pct":{"rs_21d":null,"rs_63d":null},"status":"unavailable"},{"group_id":"XLU","name_en":"XLU Sector","name_zh":null,"null_reasons":{"rs_21d":"history_session_mismatch","rs_63d":"history_session_mismatch"},"qualification_reasons":["history_session_mismatch"],"relative_wealth_pct":{"rs_21d":null,"rs_63d":null},"status":"unavailable"},{"group_id":"XLV","name_en":"XLV Sector","name_zh":null,"null_reasons":{"rs_21d":"history_session_mismatch","rs_63d":"history_session_mismatch"},"qualification_reasons":["history_session_mismatch"],"relative_wealth_pct":{"rs_21d":null,"rs_63d":null},"status":"unavailable"},{"group_id":"XLY","name_en":"XLY Sector","name_zh":null,"null_reasons":{"rs_21d":"history_session_mismatch","rs_63d":"history_session_mismatch"},"qualification_reasons":["history_session_mismatch"],"relative_wealth_pct":{"rs_21d":null,"rs_63d":null},"status":"unavailable"}],"history":{"mode":"reconstructed_price_history","naturally_observed":false},"measurement_status":"unavailable","mechanism":{"owner":"engine.theme_graph","reason":"no_qualified_evidence","status":"unavailable"},"population":"eleven_sector_etf_proxies","price_basis":"total_return","risk":{"owner":"engine.risk_envelope","reason":"no_qualified_risk_context","scope":null,"status":"unavailable"},"schema":"leadership_rotation_context.sector_dossiers/v1","source_generation":{"id":null,"reason":"immutable_generation_not_supplied","status":"unavailable"},"status":"unavailable","unavailable_windows":{"reason":"not_supplied_by_owner","sessions":[5,20]},"units":"pct","windows_sessions":[21,63]},"independent_missing_window":{"absolute_returns":{"reason":"not_supplied_by_owner","status":"unavailable"},"as_of":"2026-11-03","authority":{"may_escalate":false,"may_gate":false,"may_rank":false,"may_size":false,"may_trade":false},"availability":{"decision_cutoff":null,"historically_admissible":false,"mode":"dated_snapshot","original_available_at":null,"reason":"original_availability_not_supplied"},"benchmark":"SPY","cohort_id":"us_sectors_11","compatibility_key":"2026-11-03|SPY|us_sectors_11","constituent_breadth":{"reason":"native_membership_not_supplied","status":"unavailable"},"constituent_concentration":{"reason":"native_weights_not_supplied","status":"unavailable"},"corrections":{"reason":"native_revision_selection_not_supplied","status":"unavailable"},"cross_sector_breadth_counts":{"21":{"expected_n":11,"measured_n":11,"positive_n":11},"63":{"expected_n":11,"measured_n":10,"positive_n":10}},"dependency_audit":{"constituent_overlap":"unknown","independence":"not_established","shared_rolling_windows":true,"source_family_count":1,"source_roots":["engine.sector_cycles"]},"diagnostics":{"duplicate_groups":[],"malformed_measured_rows":0,"malformed_source_rows":0,"outside_cohort":[],"qualification_reasons":[]},"forecasts":{"allocation_weight":null,"expected_return":null,"persistence_estimate":null,"status":"not_qualified"},"freshness":{"reason":"owner_freshness_receipt_not_supplied","status":"unverified"},"groups":[{"group_id":"XLB","name_en":"XLB Sector","name_zh":null,"null_reasons":{"rs_21d":null,"rs_63d":"missing_input"},"qualification_reasons":[],"relative_wealth_pct":{"rs_21d":1.0,"rs_63d":null},"status":"partial"},{"group_id":"XLC","name_en":"XLC Sector","name_zh":null,"null_reasons":{"rs_21d":null,"rs_63d":null},"qualification_reasons":[],"relative_wealth_pct":{"rs_21d":2.0,"rs_63d":3.0},"status":"available"},{"group_id":"XLE","name_en":"XLE Sector","name_zh":null,"null_reasons":{"rs_21d":null,"rs_63d":null},"qualification_reasons":[],"relative_wealth_pct":{"rs_21d":3.0,"rs_63d":4.0},"status":"available"},{"group_id":"XLF","name_en":"XLF Sector","name_zh":null,"null_reasons":{"rs_21d":null,"rs_63d":null},"qualification_reasons":[],"relative_wealth_pct":{"rs_21d":4.0,"rs_63d":5.0},"status":"available"},{"group_id":"XLI","name_en":"XLI Sector","name_zh":null,"null_reasons":{"rs_21d":null,"rs_63d":null},"qualification_reasons":[],"relative_wealth_pct":{"rs_21d":5.0,"rs_63d":6.0},"status":"available"},{"group_id":"XLK","name_en":"XLK Sector","name_zh":null,"null_reasons":{"rs_21d":null,"rs_63d":null},"qualification_reasons":[],"relative_wealth_pct":{"rs_21d":6.0,"rs_63d":7.0},"status":"available"},{"group_id":"XLP","name_en":"XLP Sector","name_zh":null,"null_reasons":{"rs_21d":null,"rs_63d":null},"qualification_reasons":[],"relative_wealth_pct":{"rs_21d":7.0,"rs_63d":8.0},"status":"available"},{"group_id":"XLRE","name_en":"XLRE Sector","name_zh":null,"null_reasons":{"rs_21d":null,"rs_63d":null},"qualification_reasons":[],"relative_wealth_pct":{"rs_21d":8.0,"rs_63d":9.0},"status":"available"},{"group_id":"XLU","name_en":"XLU Sector","name_zh":null,"null_reasons":{"rs_21d":null,"rs_63d":null},"qualification_reasons":[],"relative_wealth_pct":{"rs_21d":9.0,"rs_63d":10.0},"status":"available"},{"group_id":"XLV","name_en":"XLV Sector","name_zh":null,"null_reasons":{"rs_21d":null,"rs_63d":null},"qualification_reasons":[],"relative_wealth_pct":{"rs_21d":10.0,"rs_63d":11.0},"status":"available"},{"group_id":"XLY","name_en":"XLY Sector","name_zh":null,"null_reasons":{"rs_21d":null,"rs_63d":null},"qualification_reasons":[],"relative_wealth_pct":{"rs_21d":11.0,"rs_63d":12.0},"status":"available"}],"history":{"mode":"reconstructed_price_history","naturally_observed":false},"measurement_status":"partial","mechanism":{"owner":"engine.theme_graph","reason":"no_qualified_evidence","status":"unavailable"},"population":"eleven_sector_etf_proxies","price_basis":"total_return","risk":{"owner":"engine.risk_envelope","reason":"no_qualified_risk_context","scope":null,"status":"unavailable"},"schema":"leadership_rotation_context.sector_dossiers/v1","source_generation":{"id":null,"reason":"immutable_generation_not_supplied","status":"unavailable"},"status":"partial","unavailable_windows":{"reason":"not_supplied_by_owner","sessions":[5,20]},"units":"pct","windows_sessions":[21,63]},"malformed_source_12":{"absolute_returns":{"reason":"not_supplied_by_owner","status":"unavailable"},"as_of":"2026-11-03","authority":{"may_escalate":false,"may_gate":false,"may_rank":false,"may_size":false,"may_trade":false},"availability":{"decision_cutoff":null,"historically_admissible":false,"mode":"dated_snapshot","original_available_at":null,"reason":"original_availability_not_supplied"},"benchmark":"SPY","cohort_id":"us_sectors_11","compatibility_key":"2026-11-03|SPY|us_sectors_11","constituent_breadth":{"reason":"native_membership_not_supplied","status":"unavailable"},"constituent_concentration":{"reason":"native_weights_not_supplied","status":"unavailable"},"corrections":{"reason":"native_revision_selection_not_supplied","status":"unavailable"},"cross_sector_breadth_counts":{"21":{"expected_n":11,"measured_n":11,"positive_n":11},"63":{"expected_n":11,"measured_n":11,"positive_n":11}},"dependency_audit":{"constituent_overlap":"unknown","independence":"not_established","shared_rolling_windows":true,"source_family_count":1,"source_roots":["engine.sector_cycles"]},"diagnostics":{"duplicate_groups":[],"malformed_measured_rows":0,"malformed_source_rows":12,"outside_cohort":[],"qualification_reasons":[]},"forecasts":{"allocation_weight":null,"expected_return":null,"persistence_estimate":null,"status":"not_qualified"},"freshness":{"reason":"owner_freshness_receipt_not_supplied","status":"unverified"},"groups":[{"group_id":"XLB","name_en":"XLB Sector","name_zh":null,"null_reasons":{"rs_21d":null,"rs_63d":null},"qualification_reasons":[],"relative_wealth_pct":{"rs_21d":1.0,"rs_63d":2.0},"status":"available"},{"group_id":"XLC","name_en":"XLC Sector","name_zh":null,"null_reasons":{"rs_21d":null,"rs_63d":null},"qualification_reasons":[],"relative_wealth_pct":{"rs_21d":2.0,"rs_63d":3.0},"status":"available"},{"group_id":"XLE","name_en":"XLE Sector","name_zh":null,"null_reasons":{"rs_21d":null,"rs_63d":null},"qualification_reasons":[],"relative_wealth_pct":{"rs_21d":3.0,"rs_63d":4.0},"status":"available"},{"group_id":"XLF","name_en":"XLF Sector","name_zh":null,"null_reasons":{"rs_21d":null,"rs_63d":null},"qualification_reasons":[],"relative_wealth_pct":{"rs_21d":4.0,"rs_63d":5.0},"status":"available"},{"group_id":"XLI","name_en":"XLI Sector","name_zh":null,"null_reasons":{"rs_21d":null,"rs_63d":null},"qualification_reasons":[],"relative_wealth_pct":{"rs_21d":5.0,"rs_63d":6.0},"status":"available"},{"group_id":"XLK","name_en":"XLK Sector","name_zh":null,"null_reasons":{"rs_21d":null,"rs_63d":null},"qualification_reasons":[],"relative_wealth_pct":{"rs_21d":6.0,"rs_63d":7.0},"status":"available"},{"group_id":"XLP","name_en":"XLP Sector","name_zh":null,"null_reasons":{"rs_21d":null,"rs_63d":null},"qualification_reasons":[],"relative_wealth_pct":{"rs_21d":7.0,"rs_63d":8.0},"status":"available"},{"group_id":"XLRE","name_en":"XLRE Sector","name_zh":null,"null_reasons":{"rs_21d":null,"rs_63d":null},"qualification_reasons":[],"relative_wealth_pct":{"rs_21d":8.0,"rs_63d":9.0},"status":"available"},{"group_id":"XLU","name_en":"XLU Sector","name_zh":null,"null_reasons":{"rs_21d":null,"rs_63d":null},"qualification_reasons":[],"relative_wealth_pct":{"rs_21d":9.0,"rs_63d":10.0},"status":"available"},{"group_id":"XLV","name_en":"XLV Sector","name_zh":null,"null_reasons":{"rs_21d":null,"rs_63d":null},"qualification_reasons":[],"relative_wealth_pct":{"rs_21d":10.0,"rs_63d":11.0},"status":"available"},{"group_id":"XLY","name_en":"XLY Sector","name_zh":null,"null_reasons":{"rs_21d":null,"rs_63d":null},"qualification_reasons":[],"relative_wealth_pct":{"rs_21d":11.0,"rs_63d":12.0},"status":"available"}],"history":{"mode":"reconstructed_price_history","naturally_observed":false},"measurement_status":"available","mechanism":{"owner":"engine.theme_graph","reason":"no_qualified_evidence","status":"unavailable"},"population":"eleven_sector_etf_proxies","price_basis":"total_return","risk":{"owner":"engine.risk_envelope","reason":"no_qualified_risk_context","scope":null,"status":"unavailable"},"schema":"leadership_rotation_context.sector_dossiers/v1","source_generation":{"id":null,"reason":"immutable_generation_not_supplied","status":"unavailable"},"status":"partial","unavailable_windows":{"reason":"not_supplied_by_owner","sessions":[5,20]},"units":"pct","windows_sessions":[21,63]},"multi_global_reasons":{"absolute_returns":{"reason":"not_supplied_by_owner","status":"unavailable"},"as_of":"2026-11-03","authority":{"may_escalate":false,"may_gate":false,"may_rank":false,"may_size":false,"may_trade":false},"availability":{"decision_cutoff":null,"historically_admissible":false,"mode":"dated_snapshot","original_available_at":null,"reason":"original_availability_not_supplied"},"benchmark":"SPY","cohort_id":"us_sectors_11","compatibility_key":"2026-11-03|SPY|us_sectors_11","constituent_breadth":{"reason":"native_membership_not_supplied","status":"unavailable"},"constituent_concentration":{"reason":"native_weights_not_supplied","status":"unavailable"},"corrections":{"reason":"native_revision_selection_not_supplied","status":"unavailable"},"cross_sector_breadth_counts":{"21":{"expected_n":11,"measured_n":0,"positive_n":null},"63":{"expected_n":11,"measured_n":0,"positive_n":null}},"dependency_audit":{"constituent_overlap":"unknown","independence":"not_established","shared_rolling_windows":true,"source_family_count":1,"source_roots":["engine.sector_cycles"]},"diagnostics":{"duplicate_groups":[],"malformed_measured_rows":0,"malformed_source_rows":0,"outside_cohort":[],"qualification_reasons":["history_session_mismatch","history_schema_not_qualified","evidence_mode_not_qualified"]},"forecasts":{"allocation_weight":null,"expected_return":null,"persistence_estimate":null,"status":"not_qualified"},"freshness":{"reason":"owner_freshness_receipt_not_supplied","status":"unverified"},"groups":[{"group_id":"XLB","name_en":"XLB Sector","name_zh":null,"null_reasons":{"rs_21d":"history_session_mismatch","rs_63d":"history_session_mismatch"},"qualification_reasons":["evidence_mode_not_qualified","history_schema_not_qualified","history_session_mismatch"],"relative_wealth_pct":{"rs_21d":null,"rs_63d":null},"status":"unavailable"},{"group_id":"XLC","name_en":"XLC Sector","name_zh":null,"null_reasons":{"rs_21d":"history_session_mismatch","rs_63d":"history_session_mismatch"},"qualification_reasons":["evidence_mode_not_qualified","history_schema_not_qualified","history_session_mismatch"],"relative_wealth_pct":{"rs_21d":null,"rs_63d":null},"status":"unavailable"},{"group_id":"XLE","name_en":"XLE Sector","name_zh":null,"null_reasons":{"rs_21d":"history_session_mismatch","rs_63d":"history_session_mismatch"},"qualification_reasons":["evidence_mode_not_qualified","history_schema_not_qualified","history_session_mismatch"],"relative_wealth_pct":{"rs_21d":null,"rs_63d":null},"status":"unavailable"},{"group_id":"XLF","name_en":"XLF Sector","name_zh":null,"null_reasons":{"rs_21d":"history_session_mismatch","rs_63d":"history_session_mismatch"},"qualification_reasons":["evidence_mode_not_qualified","history_schema_not_qualified","history_session_mismatch"],"relative_wealth_pct":{"rs_21d":null,"rs_63d":null},"status":"unavailable"},{"group_id":"XLI","name_en":"XLI Sector","name_zh":null,"null_reasons":{"rs_21d":"history_session_mismatch","rs_63d":"history_session_mismatch"},"qualification_reasons":["evidence_mode_not_qualified","history_schema_not_qualified","history_session_mismatch"],"relative_wealth_pct":{"rs_21d":null,"rs_63d":null},"status":"unavailable"},{"group_id":"XLK","name_en":"XLK Sector","name_zh":null,"null_reasons":{"rs_21d":"history_session_mismatch","rs_63d":"history_session_mismatch"},"qualification_reasons":["evidence_mode_not_qualified","history_schema_not_qualified","history_session_mismatch"],"relative_wealth_pct":{"rs_21d":null,"rs_63d":null},"status":"unavailable"},{"group_id":"XLP","name_en":"XLP Sector","name_zh":null,"null_reasons":{"rs_21d":"history_session_mismatch","rs_63d":"history_session_mismatch"},"qualification_reasons":["evidence_mode_not_qualified","history_schema_not_qualified","history_session_mismatch"],"relative_wealth_pct":{"rs_21d":null,"rs_63d":null},"status":"unavailable"},{"group_id":"XLRE","name_en":"XLRE Sector","name_zh":null,"null_reasons":{"rs_21d":"history_session_mismatch","rs_63d":"history_session_mismatch"},"qualification_reasons":["evidence_mode_not_qualified","history_schema_not_qualified","history_session_mismatch"],"relative_wealth_pct":{"rs_21d":null,"rs_63d":null},"status":"unavailable"},{"group_id":"XLU","name_en":"XLU Sector","name_zh":null,"null_reasons":{"rs_21d":"history_session_mismatch","rs_63d":"history_session_mismatch"},"qualification_reasons":["evidence_mode_not_qualified","history_schema_not_qualified","history_session_mismatch"],"relative_wealth_pct":{"rs_21d":null,"rs_63d":null},"status":"unavailable"},{"group_id":"XLV","name_en":"XLV Sector","name_zh":null,"null_reasons":{"rs_21d":"history_session_mismatch","rs_63d":"history_session_mismatch"},"qualification_reasons":["evidence_mode_not_qualified","history_schema_not_qualified","history_session_mismatch"],"relative_wealth_pct":{"rs_21d":null,"rs_63d":null},"status":"unavailable"},{"group_id":"XLY","name_en":"XLY Sector","name_zh":null,"null_reasons":{"rs_21d":"history_session_mismatch","rs_63d":"history_session_mismatch"},"qualification_reasons":["evidence_mode_not_qualified","history_schema_not_qualified","history_session_mismatch"],"relative_wealth_pct":{"rs_21d":null,"rs_63d":null},"status":"unavailable"}],"history":{"mode":"reconstructed_price_history","naturally_observed":false},"measurement_status":"unavailable","mechanism":{"owner":"engine.theme_graph","reason":"no_qualified_evidence","status":"unavailable"},"population":"eleven_sector_etf_proxies","price_basis":"total_return","risk":{"owner":"engine.risk_envelope","reason":"no_qualified_risk_context","scope":null,"status":"unavailable"},"schema":"leadership_rotation_context.sector_dossiers/v1","source_generation":{"id":null,"reason":"immutable_generation_not_supplied","status":"unavailable"},"status":"unavailable","unavailable_windows":{"reason":"not_supplied_by_owner","sessions":[5,20]},"units":"pct","windows_sessions":[21,63]},"outside_cohort":{"absolute_returns":{"reason":"not_supplied_by_owner","status":"unavailable"},"as_of":"2026-11-03","authority":{"may_escalate":false,"may_gate":false,"may_rank":false,"may_size":false,"may_trade":false},"availability":{"decision_cutoff":null,"historically_admissible":false,"mode":"dated_snapshot","original_available_at":null,"reason":"original_availability_not_supplied"},"benchmark":"SPY","cohort_id":"us_sectors_11","compatibility_key":"2026-11-03|SPY|us_sectors_11","constituent_breadth":{"reason":"native_membership_not_supplied","status":"unavailable"},"constituent_concentration":{"reason":"native_weights_not_supplied","status":"unavailable"},"corrections":{"reason":"native_revision_selection_not_supplied","status":"unavailable"},"cross_sector_breadth_counts":{"21":{"expected_n":11,"measured_n":11,"positive_n":11},"63":{"expected_n":11,"measured_n":11,"positive_n":11}},"dependency_audit":{"constituent_overlap":"unknown","independence":"not_established","shared_rolling_windows":true,"source_family_count":1,"source_roots":["engine.sector_cycles"]},"diagnostics":{"duplicate_groups":[],"malformed_measured_rows":0,"malformed_source_rows":0,"outside_cohort":["XLCB"],"qualification_reasons":[]},"forecasts":{"allocation_weight":null,"expected_return":null,"persistence_estimate":null,"status":"not_qualified"},"freshness":{"reason":"owner_freshness_receipt_not_supplied","status":"unverified"},"groups":[{"group_id":"XLB","name_en":"XLB Sector","name_zh":null,"null_reasons":{"rs_21d":null,"rs_63d":null},"qualification_reasons":[],"relative_wealth_pct":{"rs_21d":1.0,"rs_63d":2.0},"status":"available"},{"group_id":"XLC","name_en":"XLC Sector","name_zh":null,"null_reasons":{"rs_21d":null,"rs_63d":null},"qualification_reasons":[],"relative_wealth_pct":{"rs_21d":2.0,"rs_63d":3.0},"status":"available"},{"group_id":"XLE","name_en":"XLE Sector","name_zh":null,"null_reasons":{"rs_21d":null,"rs_63d":null},"qualification_reasons":[],"relative_wealth_pct":{"rs_21d":3.0,"rs_63d":4.0},"status":"available"},{"group_id":"XLF","name_en":"XLF Sector","name_zh":null,"null_reasons":{"rs_21d":null,"rs_63d":null},"qualification_reasons":[],"relative_wealth_pct":{"rs_21d":4.0,"rs_63d":5.0},"status":"available"},{"group_id":"XLI","name_en":"XLI Sector","name_zh":null,"null_reasons":{"rs_21d":null,"rs_63d":null},"qualification_reasons":[],"relative_wealth_pct":{"rs_21d":5.0,"rs_63d":6.0},"status":"available"},{"group_id":"XLK","name_en":"XLK Sector","name_zh":null,"null_reasons":{"rs_21d":null,"rs_63d":null},"qualification_reasons":[],"relative_wealth_pct":{"rs_21d":6.0,"rs_63d":7.0},"status":"available"},{"group_id":"XLP","name_en":"XLP Sector","name_zh":null,"null_reasons":{"rs_21d":null,"rs_63d":null},"qualification_reasons":[],"relative_wealth_pct":{"rs_21d":7.0,"rs_63d":8.0},"status":"available"},{"group_id":"XLRE","name_en":"XLRE Sector","name_zh":null,"null_reasons":{"rs_21d":null,"rs_63d":null},"qualification_reasons":[],"relative_wealth_pct":{"rs_21d":8.0,"rs_63d":9.0},"status":"available"},{"group_id":"XLU","name_en":"XLU Sector","name_zh":null,"null_reasons":{"rs_21d":null,"rs_63d":null},"qualification_reasons":[],"relative_wealth_pct":{"rs_21d":9.0,"rs_63d":10.0},"status":"available"},{"group_id":"XLV","name_en":"XLV Sector","name_zh":null,"null_reasons":{"rs_21d":null,"rs_63d":null},"qualification_reasons":[],"relative_wealth_pct":{"rs_21d":10.0,"rs_63d":11.0},"status":"available"},{"group_id":"XLY","name_en":"XLY Sector","name_zh":null,"null_reasons":{"rs_21d":null,"rs_63d":null},"qualification_reasons":[],"relative_wealth_pct":{"rs_21d":11.0,"rs_63d":12.0},"status":"available"}],"history":{"mode":"reconstructed_price_history","naturally_observed":false},"measurement_status":"available","mechanism":{"owner":"engine.theme_graph","reason":"no_qualified_evidence","status":"unavailable"},"population":"eleven_sector_etf_proxies","price_basis":"total_return","risk":{"owner":"engine.risk_envelope","reason":"no_qualified_risk_context","scope":null,"status":"unavailable"},"schema":"leadership_rotation_context.sector_dossiers/v1","source_generation":{"id":null,"reason":"immutable_generation_not_supplied","status":"unavailable"},"status":"partial","unavailable_windows":{"reason":"not_supplied_by_owner","sessions":[5,20]},"units":"pct","windows_sessions":[21,63]}}"""

# The canonical digest of each composed packet.
_GENUINE_PACKET_DIGESTS = {
    "baseline":
        "5955b08ecd1197469c59ad61c76e20fe4a4f3617f43e0fdfb5552e8bbfcf995b",
    "duplicate_source":
        "5d3c7afbbfa4b56f8a1122ac15b184595d373c8c0e1c6e331812ebbf9a935e67",
    "global_and_duplicate":
        "5597fb6c22330a93cbed173a0dec7b901d0b80c1ec3968448b1f9f6cee5d8751",
    "global_qualified":
        "3f5c9fa73eff58e59c890a5553d31b74718b35b03033b796f1917290412a0e5f",
    "independent_missing_window":
        "2093d4c541d69a99baae9298a554b363f9cd33525144cfc9d000fd1b171655bf",
    "malformed_source_12":
        "901bb18ddf5c858821bd66e01788fb94732510ddc0ac08b44744cb23cc866df9",
    "multi_global_reasons":
        "851ef31998dd2c8ecdfeb38b3817a92a9f179fffb89bfa33734ab5abe1966d78",
    "outside_cohort":
        "41b2f72f80fa948d83e8f7ac2503836a1b39e1f02a3e068f62a1542ef21ac28e"}


def _canonical(payload) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)


def _sha256_of(payload) -> str:
    return hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()


@pytest.fixture
def genuine_packets():
    """The owner's own composed packets, checked against their pinned digests."""
    packets = json.loads(_GENUINE_PACKETS_JSON)
    assert sorted(packets) == sorted(_GENUINE_PACKET_DIGESTS)
    for name, packet in packets.items():
        assert _sha256_of(packet) == _GENUINE_PACKET_DIGESTS[name], name
    return packets


def _genuine_inputs(variant) -> dict:
    """The canonical owner input pair with one variant applied."""
    inputs = json.loads(_GENUINE_INPUTS_JSON)
    inputs["cycles"]["meta"]["rs_history"].update(variant.get("history", {}))
    for ident in variant.get("source_null_rs_63d", ()):
        for row in inputs["cycles"]["sectors"]:
            if row["ticker"] == ident:
                row["now"].pop("rs_63d", None)
    for ident in variant.get("read_null_rs_63d", ()):
        for group in inputs["read"]["groups"]:
            if group["group_id"] == ident:
                group["current"]["rs_63d"] = None
    for row in variant.get("extra_source_rows", ()):
        inputs["cycles"]["sectors"].append(deepcopy(row))
    return inputs


def _producer_source_path():
    """Where the owner's producer source is reachable from, if it is.

    An explicitly requested source must be the pinned one. The in-tree file is
    used only when it IS the pinned revision, because a different revision of
    the same file is not the owner this projection was qualified against.
    """
    override = os.environ.get("PSL_DOSSIER_PRODUCER")
    if override:
        path = Path(override)
        if not path.is_file():
            raise AssertionError(f"the requested producer source is absent: {path}")
        return path, True
    in_tree = ROOT / "engine" / "leadership_rotation_context.py"
    if in_tree.is_file():
        return in_tree, False
    return None, False


def _load_producer(path):
    import importlib.util
    spec = importlib.util.spec_from_file_location("psl_dossier_producer", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_the_genuine_packets_are_the_actual_producer_output(genuine_packets):
    """Cross-check the frozen packets against the owner's own producer.

    The producer is never imported by the projector. This case only proves that
    the packets the suite carries are the ones that exact producer composes.
    """
    path, requested = _producer_source_path()
    if path is None:
        pytest.skip("the owner's dossier producer is not reachable from here")
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != _PRODUCER_SOURCE_SHA256:
        if requested:
            raise AssertionError(
                f"the requested producer source is not the pinned revision: {path}")
        pytest.skip(f"the in-tree producer is not the pinned revision: {path}")
    producer = _load_producer(path)
    compose = getattr(producer, "_compose_sector_dossiers", None)
    if compose is None:
        pytest.skip("the reachable producer does not compose sector dossiers")
    variants = json.loads(_GENUINE_VARIANTS_JSON)
    for name, packet in genuine_packets.items():
        inputs = _genuine_inputs(variants[name])
        composed = compose(inputs["cycles"], inputs["read"],
                           expected_group_ids=list(_NATIVE_DOSSIER_IDS),
                           decision_cutoff=None)
        assert composed == packet, name


@pytest.mark.parametrize("name", sorted(_GENUINE_PACKET_DIGESTS))
def test_the_owners_genuine_packets_are_accepted(genuine_packets, dossier_specimen,
                                                  name):
    """Every packet the owner itself composed is carried, never refused."""
    inputs, receipt = dossier_specimen
    inputs.central["measured_read"]["sector_dossiers"] = deepcopy(
        genuine_packets[name])
    projected = _dossier_of(project_sector_view(inputs, receipt, audience="preview"))
    assert projected["schema"] == "leadership_rotation_context.sector_dossiers/v1"
    assert [group["group_id"] for group in projected["groups"]] == list(
        _NATIVE_DOSSIER_IDS)
    assert len(projected["groups"]) == 11


def test_the_genuine_malformed_row_count_keeps_the_valid_native_measurements(
        genuine_packets, dossier_specimen):
    """The owner counts malformed rows over its own 128-row input bound.

    Twelve malformed source rows beside eleven valid native rows leave every
    valid native measurement published: a positive count withholds nothing on
    its own.
    """
    packet = genuine_packets["malformed_source_12"]
    assert packet["diagnostics"]["malformed_source_rows"] == 12
    inputs, receipt = dossier_specimen
    inputs.central["measured_read"]["sector_dossiers"] = deepcopy(packet)
    projected = _dossier_of(project_sector_view(inputs, receipt, audience="preview"))
    assert projected["diagnostics"]["malformed_source_rows"] == 12
    assert projected["diagnostics"]["malformed_measured_rows"] == 0
    assert projected["measurement_status"] == "available"
    assert all(group["status"] == "available" for group in projected["groups"])
    assert all(value is not None for group in projected["groups"]
               for value in group["relative_wealth_pct"].values())


def test_the_genuine_duplicate_packet_withholds_only_the_duplicated_row(
        genuine_packets, dossier_specimen):
    """A duplicated identity is withheld; every other row keeps its values."""
    packet = genuine_packets["duplicate_source"]
    assert packet["diagnostics"]["duplicate_groups"] == ["XLB"]
    inputs, receipt = dossier_specimen
    inputs.central["measured_read"]["sector_dossiers"] = deepcopy(packet)
    projected = _dossier_of(project_sector_view(inputs, receipt, audience="preview"))
    first = projected["groups"][0]
    assert first["group_id"] == "XLB"
    assert first["qualification_reasons"] == ["duplicate_group_identity"]
    assert first["relative_wealth_pct"] == {"rs_21d": None, "rs_63d": None}
    assert first["null_reasons"] == {"rs_21d": "duplicate_group_identity",
                                     "rs_63d": "duplicate_group_identity"}
    assert all(group["status"] == "available"
               for group in projected["groups"][1:])
    assert projected["diagnostics"]["duplicate_groups"] == ["XLB"]


def test_the_genuine_global_qualification_withholds_every_measurement(
        genuine_packets, dossier_specimen):
    """A global qualification withholds every child measurement."""
    packet = genuine_packets["global_qualified"]
    assert packet["diagnostics"]["qualification_reasons"] == [
        "history_session_mismatch"]
    inputs, receipt = dossier_specimen
    inputs.central["measured_read"]["sector_dossiers"] = deepcopy(packet)
    projected = _dossier_of(project_sector_view(inputs, receipt, audience="preview"))
    assert projected["status"] == "unavailable"
    assert projected["measurement_status"] == "unavailable"
    assert all(value is None for group in projected["groups"]
               for value in group["relative_wealth_pct"].values())
    assert all(group["qualification_reasons"] == ["history_session_mismatch"]
               for group in projected["groups"])


def test_the_genuine_independent_window_missingness_is_preserved(
        genuine_packets, dossier_specimen):
    """An unqualified row may miss one window and keep the other one."""
    packet = genuine_packets["independent_missing_window"]
    assert packet["groups"][0]["qualification_reasons"] == []
    inputs, receipt = dossier_specimen
    inputs.central["measured_read"]["sector_dossiers"] = deepcopy(packet)
    projected = _dossier_of(project_sector_view(inputs, receipt, audience="preview"))
    first = projected["groups"][0]
    assert first["group_id"] == "XLB"
    assert first["relative_wealth_pct"] == {"rs_21d": 1.0, "rs_63d": None}
    assert first["null_reasons"] == {"rs_21d": None, "rs_63d": "missing_input"}
    assert first["qualification_reasons"] == []


def test_the_genuine_global_reason_list_is_not_sorted_and_still_carried(
        genuine_packets, dossier_specimen):
    """The owner publishes its global list in construction order.

    The projector must not require that list to be lexicographically sorted,
    and it must not require the withheld reason to be the first published
    reason of the row's own list.
    """
    packet = genuine_packets["multi_global_reasons"]
    published = packet["diagnostics"]["qualification_reasons"]
    assert published != sorted(published)
    inputs, receipt = dossier_specimen
    inputs.central["measured_read"]["sector_dossiers"] = deepcopy(packet)
    projected = _dossier_of(project_sector_view(inputs, receipt, audience="preview"))
    first = projected["groups"][0]
    assert first["null_reasons"]["rs_21d"] == "history_session_mismatch"
    assert first["null_reasons"]["rs_21d"] in first["qualification_reasons"]
    assert first["null_reasons"]["rs_21d"] != first["qualification_reasons"][0]


def test_the_genuine_duplicate_keeps_the_earlier_global_reason(genuine_packets,
                                                               dossier_specimen):
    """A duplicated identity keeps the earlier global reason, not its own.

    The owner publishes the row's qualification list sorted, so the duplicate
    reason is not the reason the row was withheld with. The projector must not
    force the null reason to be the duplicate reason.
    """
    packet = genuine_packets["global_and_duplicate"]
    assert packet["diagnostics"]["qualification_reasons"] == [
        "history_session_mismatch"]
    assert packet["diagnostics"]["duplicate_groups"] == ["XLB"]
    inputs, receipt = dossier_specimen
    inputs.central["measured_read"]["sector_dossiers"] = deepcopy(packet)
    projected = _dossier_of(project_sector_view(inputs, receipt, audience="preview"))
    first = projected["groups"][0]
    assert first["group_id"] == "XLB"
    assert first["qualification_reasons"] == ["duplicate_group_identity",
                                              "history_session_mismatch"]
    assert first["relative_wealth_pct"] == {"rs_21d": None, "rs_63d": None}
    assert first["null_reasons"] == {"rs_21d": "history_session_mismatch",
                                     "rs_63d": "history_session_mismatch"}


def test_the_genuine_outside_cohort_identity_is_carried(genuine_packets,
                                                         dossier_specimen):
    """An identity the owner read outside the cohort stays outside it."""
    packet = genuine_packets["outside_cohort"]
    assert packet["diagnostics"]["outside_cohort"] == ["XLCB"]
    inputs, receipt = dossier_specimen
    inputs.central["measured_read"]["sector_dossiers"] = deepcopy(packet)
    projected = _dossier_of(project_sector_view(inputs, receipt, audience="preview"))
    assert projected["diagnostics"]["outside_cohort"] == ["XLCB"]
    assert [group["group_id"] for group in projected["groups"]] == list(
        _NATIVE_DOSSIER_IDS)


# --- the demonstrated tamper regressions ------------------------------------
# Each tamper keeps the packet's own derived counts and statuses consistent
# with its rows, so it isolates exactly ONE owner relation.


def _tampered(packet, mutate):
    copy = deepcopy(packet)
    mutate(copy)
    return copy


@pytest.mark.parametrize("name,mutate", [
    # A global qualification with values: the owner withholds every
    # measurement of every row when it qualifies the packet.
    ("baseline", lambda p: (
        p["diagnostics"].update(qualification_reasons=["history_session_mismatch"]),
        [group.update(qualification_reasons=["history_session_mismatch"])
         for group in p["groups"]])),
    # A row qualification with that row's own values.
    ("baseline", lambda p: p["groups"][0].update(
        qualification_reasons=["thin_history"])),
    # A duplicate diagnostic that names a row the owner still measured.
    ("baseline", lambda p: p["diagnostics"].update(duplicate_groups=["XLB"])),
    # A genuine duplicate diagnostic removed from the diagnostic list.
    ("duplicate_source", lambda p: p["diagnostics"].update(duplicate_groups=[])),
    # A global qualification omitted from one affected row.
    ("global_qualified", lambda p: p["groups"][0].update(
        qualification_reasons=[])),
    # A qualified row whose null reason is outside its own qualification list.
    ("global_qualified", lambda p: p["groups"][0].update(
        null_reasons={"rs_21d": "outside_reason",
                      "rs_63d": "outside_reason"})),
    # A native cohort identity published as an outside-cohort identity.
    ("baseline", lambda p: p["diagnostics"].update(outside_cohort=["XLK"])),
])
def test_a_contradicting_owner_relation_is_refused(genuine_packets, dossier_specimen,
                                                    name, mutate):
    inputs, receipt = dossier_specimen
    inputs.central["measured_read"]["sector_dossiers"] = _tampered(
        genuine_packets[name], mutate)
    with pytest.raises(SectorViewUnavailable, match="^invalid_sector_dossiers$"):
        project_sector_view(inputs, receipt, audience="preview")


@pytest.mark.parametrize("key", ["malformed_source_rows", "malformed_measured_rows"])
@pytest.mark.parametrize("count,accepted", [
    (0, True), (12, True), (128, True), (129, False), (-1, False), (True, False),
])
def test_the_malformed_row_count_uses_the_owner_input_bound(genuine_packets,
                                                             dossier_specimen, key,
                                                             count, accepted):
    """The owner's own input bound is 128 rows, inclusive; a boolean is not."""
    inputs, receipt = dossier_specimen
    inputs.central["measured_read"]["sector_dossiers"] = _tampered(
        genuine_packets["baseline"],
        lambda p: p["diagnostics"].update({key: count}))
    if accepted:
        projected = _dossier_of(project_sector_view(inputs, receipt,
                                                    audience="preview"))
        assert projected["diagnostics"][key] == count
        # A positive count alone never withholds the valid native measurements.
        assert all(value is not None for group in projected["groups"]
                   for value in group["relative_wealth_pct"].values())
    else:
        with pytest.raises(SectorViewUnavailable, match="^invalid_sector_dossiers$"):
            project_sector_view(inputs, receipt, audience="preview")


def test_an_unselected_parent_window_may_still_carry_a_child_measurement(
        dossier_specimen):
    """The parent's selected horizon is not an extra gate on the other window.

    The owner's parent group can be unmeasured on its selected horizon while
    the other window holds a real measurement. The child that equals that
    measurement is carried, and the missing window stays missing.
    """
    inputs, receipt = dossier_specimen
    read = _native_measured_read()
    first = read["groups"][0]
    first["current"] = {"status": "unmeasured", "reason": "missing_input",
                         "rs_21d": None, "rs_63d": 2.0, "rank": None}
    for index, group in enumerate(read["groups"][1:], start=1):
        group["current"]["rank"] = index
    read["cohort"]["measured_n"] = 10
    read["status"] = "partial"
    inputs.central["measured_read"] = read
    rows = _dossier_rows({"XLB": (None, 2.0)})
    inputs.central["measured_read"]["sector_dossiers"] = _dossier_packet(rows)
    projected = _dossier_of(project_sector_view(inputs, receipt, audience="preview"))
    first = projected["groups"][0]
    assert first["group_id"] == "XLB"
    assert first["relative_wealth_pct"] == {"rs_21d": None, "rs_63d": 2.0}
    assert first["null_reasons"] == {"rs_21d": "missing_input", "rs_63d": None}


# --- the absent optional paths keep the base revision's bytes ---------------
# Golden values captured from engine/sector_native_view.py at the input commit
# 334b26b540ea82fc2593ab3a723ceda65be32b3b, before the dossier child existed.
_ABSENT_BYTE_PARITY = [
    ("preview", "nomeasured",
     "480de3eb6567aa1e022ead7a7cabffe4c4d9359ffa9735c5e92e45166d9dc8be"),
    ("preview", "nodossier",
     "cafd4d575e1bb98d55f7c08913ff4264a87465bc1247cd23c00b42869205cee2"),
    ("preview", "core+history",
     "4f1c6e6c8624a495d8f0b14337d13e6686a502725cd06be79c72afa9709dac80"),
    ("entitled", "nomeasured",
     "3ec21169d85a29b08b5b76e924b01e1298a3c5ec068dfa7b26e7a4088614d2e5"),
    ("entitled", "nodossier",
     "674cb6d5b8cb914b1bd3a5ba0a0aab4a8c7b63fa688303ccc4c0cec5d94f1f59"),
    ("entitled", "core+history",
     "4f1c6e6c8624a495d8f0b14337d13e6686a502725cd06be79c72afa9709dac80"),
]


@pytest.mark.parametrize("audience,case,golden", _ABSENT_BYTE_PARITY)
def test_the_absent_optional_paths_keep_the_base_byte_parity(specimen, audience,
                                                              case, golden):
    """An absent optional path stays byte-identical to the base revision."""
    inputs, receipt = specimen
    result = project_sector_view(inputs, receipt, audience=audience)
    if case == "nomeasured":
        assert "measured_read" not in result["data"]["core"]
        assert result["receipt"]["content_sha256"] == golden
        return
    read_inputs = deepcopy(inputs)
    read_inputs.central["measured_read"] = _native_measured_read()
    read_result = project_sector_view(read_inputs, receipt, audience=audience)
    if case == "nodossier":
        assert "sector_dossiers" not in read_result["data"]["core"]["measured_read"]
        assert read_result["receipt"]["content_sha256"] == golden
        return
    assert _sha256_of({"core": read_result["data"]["core"],
                        "history": read_result["data"]["history"]}) == golden
# --- END PSL NATIVE QUALIFICATION CONTRACT TESTS ---


# Optional exact 5/20/63 companion. These fixtures were produced by the current
# owner for 2026-11-05; no legacy fixture date is changed to make them fit.
_WINDOW_FIXTURE_DIR = ROOT / "tests" / "fixtures" / "leadership_rotation"


def _exact_window_packet(name="complete"):
    return json.loads((_WINDOW_FIXTURE_DIR /
        f"sector_window_measurements.{name}.v1.json").read_text())


def _exact_window_parent(packet):
    end = packet["end_session"]
    return {
        "schema": "leadership_rotation_context.measured_group_read/v1",
        "status": "available",
        "generation": {"session_end": end, "benchmark": packet["benchmark"],
            "id": f"{end}|{packet['benchmark']}|us_sectors_11",
            "cohort_id": "us_sectors_11", "price_basis": "total_return"},
        "cohort": {"expected_n": 11, "measured_n": 11, "horizon": "rs_21d"},
        "groups": [{"group_id": ident, "group_kind": "sector",
            "name_en": ident, "name_zh": None,
            "current": {"status": "measured", "rank": i + 1,
                "rs_21d": 1.0 + i, "rs_63d": 2.0 + i, "reason": None,
                "metric": "relative_wealth_pct", "units": "pct"}}
            for i, ident in enumerate(_NATIVE_DOSSIER_IDS)],
        "sector_window_measurements": packet,
    }


@pytest.mark.parametrize("name", ["complete", "unavailable"])
def test_exact_window_native_carries_owner_packet_and_parent_binding(name):
    from engine.sector_native_view import _measured_read
    packet = _exact_window_packet(name)
    parent = _exact_window_parent(packet)
    result = _measured_read(parent, packet["end_session"])
    assert result["sector_window_measurements"] == packet
    assert result["sector_window_measurements"] is not packet
    assert result["generation"] == parent["generation"]
    assert all(row["group_kind"] == "sector" for row in result["groups"])
    assert all(row["current"]["metric"] == "relative_wealth_pct" and
        row["current"]["units"] == "pct" for row in result["groups"])


@pytest.mark.parametrize("name,wrong", [
    ("multi_global_reasons", None),
    ("global_and_duplicate", "duplicate_group_identity"),
])
def test_exact_window_legacy_first_global_cause_is_not_any_global_member(
        genuine_packets, dossier_specimen, name, wrong):
    inputs, receipt = dossier_specimen
    packet = deepcopy(genuine_packets[name])
    reasons = packet["diagnostics"]["qualification_reasons"]
    wrong = wrong or reasons[1]
    assert wrong != reasons[0]
    packet["groups"][0]["null_reasons"] = {"rs_21d": wrong, "rs_63d": wrong}
    inputs.central["measured_read"]["sector_dossiers"] = packet
    with pytest.raises(SectorViewUnavailable, match="invalid_sector_dossiers"):
        project_sector_view(inputs, receipt, audience="preview")


def _exact_owner_case(case="complete", binding=None):
    """Current producer over an explicit NYSE-session fixture ending Nov 5.

    Aug 7..Nov 5 has 64 endpoints after the Labor Day closure. This is a test
    table, not a production calendar or observed market history.
    """
    from engine import leadership_rotation_context as owner
    assert hashlib.sha256((ROOT / "engine/leadership_rotation_context.py").read_bytes()).hexdigest() == (
        "43b1cf3a19d3f73dc6a29a319bcc81f3745cda153c3419e492396b48b9068c61")
    sessions, day = [], date(2026, 8, 7)
    while day <= date(2026, 11, 5):
        if day.weekday() < 5 and day != date(2026, 9, 7):
            sessions.append(day.isoformat())
        day += timedelta(days=1)
    assert len(sessions) == 64
    rows = [{"session": day, **{ident: 100.0 + i + j
        for j, ident in enumerate((*_NATIVE_DOSSIER_IDS, "SPY"))}}
        for i, day in enumerate(sessions)]
    if case == "missing_member":
        rows[-6].pop("XLB")
    elif case == "missing_benchmark":
        rows[-6].pop("SPY")
    elif case == "interior_gap":
        rows[-3].pop("XLB")
    elif case == "ordinary_all_null":
        rows = [{"session": row["session"], "SPY": row["SPY"]} for row in rows]
    elif case == "absolute_percent_overflow":
        rows[-6]["XLB"], rows[-1]["XLB"] = 1e-307, 1.0
        rows[-6]["SPY"], rows[-1]["SPY"] = 1e-305, 1.0
    elif case == "benchmark_percent_overflow":
        rows[-6]["SPY"], rows[-1]["SPY"] = 1e-307, 1.0
    elif case in ("insufficient", "blocked_insufficient"):
        sessions, rows = sessions[-21:], rows[-21:]
        if case == "blocked_insufficient":
            rows.append({**rows[-1], "session": "2026-11-06"})
    return owner.measure_sector_windows(rows, benchmark="SPY",
        end_session="2026-11-05", source_session="2026-11-05",
        reference_sessions=sessions, source_binding=binding)


@pytest.mark.parametrize("case", [
    "complete", "missing_member", "missing_benchmark", "interior_gap",
    "ordinary_all_null", "absolute_percent_overflow", "benchmark_percent_overflow",
    "insufficient", "blocked_insufficient",
])
def test_exact_window_current_producer_relationships_are_preserved(case):
    from engine.sector_native_view import _measured_read
    packet = _exact_owner_case(case)
    result = _measured_read(_exact_window_parent(packet), packet["end_session"])
    assert result["sector_window_measurements"] == packet
    cell = packet["groups"][0]["windows"]["5"]
    if case == "absolute_percent_overflow":
        assert cell["absolute_return_pct"] is None
        assert cell["null_reasons"]["absolute_return_pct"] == "non_finite_input"
        assert cell["relative_wealth_pct"] is not None
    elif case == "missing_benchmark":
        assert cell["absolute_return_pct"] is not None and cell["relative_wealth_pct"] is None
    elif case == "interior_gap":
        assert cell["coverage"] == {"observed_n": 5, "expected_n": 6, "ratio": 0.833333}
        assert cell["status"] == "available"
    elif case == "ordinary_all_null":
        assert packet["status"] == "unavailable" and packet["reason"] is None


def _exact_recount(packet):
    measured, complete = 0, 0
    for key in ("5", "20", "63"):
        wm, wc = 0, 0
        for group in packet["groups"]:
            cell = group["windows"][key]
            n = sum(cell[f] is not None for f in ("absolute_return_pct", "relative_wealth_pct"))
            cell["status"] = "available" if n == 2 else "partial" if n else "unavailable"
            wm += int(n > 0); wc += int(n == 2)
        packet["windows"][key]["status"] = "available" if wc == 11 else "partial" if wm else "unavailable"
        measured += wm; complete += wc
    packet["diagnostics"]["measured_cells"] = measured
    packet["diagnostics"]["complete_cells"] = complete
    packet["status"] = ("unavailable" if packet["reason"] else "available"
                        if complete == 33 else "partial" if measured else "unavailable")


@pytest.mark.parametrize("change", [
    "null", "empty", "schema", "extra", "group_order", "duplicate_group", "missing_group",
    "window_set", "window_bool", "bad_day", "parent_day", "cohort", "basis", "benchmark",
    "authority", "cell_status", "window_status", "top_status", "count", "coverage_denominator",
    "coverage_ratio", "coverage_boolean", "count_boolean", "reason_pair", "percentage_floor",
    "benchmark_floor", "nonfinite", "block_benchmark", "missing_benchmark_dependency",
    "relative_only_missing", "relative_only_invalid", "local_block_cause", "local_insufficient_cause",
    "null_start", "null_start_nonzero", "unsorted_columns", "bad_duplicate_date", "bad_future_date",
    "future_not_future", "unknown_binding", "receipt_withheld_present", "naive_clock",
    "clock_limitation", "unknown_limit", "missing_authority",
])
def test_exact_window_semantic_contradictions_refuse_whole_native_child(change):
    from engine.sector_native_view import _measured_read
    packet = _exact_window_packet("unavailable" if change == "block_benchmark" else "complete")
    parent = _exact_window_parent(packet)
    cell, window = packet["groups"][0]["windows"]["5"], packet["windows"]["5"]
    if change == "null": parent["sector_window_measurements"] = None
    elif change == "empty": parent["sector_window_measurements"] = {}
    elif change == "schema": packet["schema"] += ".unknown"
    elif change == "extra": packet["may_trade"] = False
    elif change == "group_order": packet["groups"].reverse()
    elif change == "duplicate_group": packet["groups"][1]["group_id"] = "XLB"
    elif change == "missing_group": packet["groups"].pop()
    elif change == "window_set": packet["windows_sessions"] = [5, 21, 63]
    elif change == "window_bool": window["window_sessions"] = True
    elif change == "bad_day": packet["source_session"] = packet["end_session"] = "2026-02-30"
    elif change == "parent_day": parent["generation"]["session_end"] = "2026-11-04"
    elif change == "cohort": parent["generation"]["cohort_id"] = "foreign"
    elif change == "basis": parent["generation"]["price_basis"] = "price"
    elif change == "benchmark": packet["benchmark"] = "QQQ"
    elif change == "authority": packet["authority"]["may_trade"] = True
    elif change == "cell_status": cell["status"] = "partial"
    elif change == "window_status": window["status"] = "partial"
    elif change == "top_status": packet["status"] = "partial"
    elif change == "count": packet["diagnostics"]["measured_cells"] = 32
    elif change == "coverage_denominator": cell["coverage"]["expected_n"] = 5
    elif change == "coverage_ratio": cell["coverage"]["ratio"] = 0.5
    elif change == "coverage_boolean": cell["coverage"]["observed_n"] = True
    elif change == "count_boolean": packet["diagnostics"]["panel_rows"] = True
    elif change == "reason_pair": cell["null_reasons"]["absolute_return_pct"] = "missing_input"
    elif change == "percentage_floor": cell["absolute_return_pct"] = -100.01
    elif change == "benchmark_floor": window["benchmark_return_pct"] = -100.01
    elif change == "nonfinite": cell["relative_wealth_pct"] = float("inf")
    elif change == "block_benchmark":
        window["benchmark_return_pct"], window["benchmark_null_reason"] = 1.0, None
    elif change == "missing_benchmark_dependency":
        window["benchmark_return_pct"], window["benchmark_null_reason"] = None, "benchmark_missing"
    elif change in ("relative_only_missing", "relative_only_invalid"):
        cell["absolute_return_pct"] = None
        cell["null_reasons"]["absolute_return_pct"] = (
            "missing_input" if change == "relative_only_missing" else "invalid_price")
        _exact_recount(packet)
    elif change in ("local_block_cause", "local_insufficient_cause"):
        cause = "future_tail" if change == "local_block_cause" else "insufficient_reference_history"
        cell["absolute_return_pct"] = cell["relative_wealth_pct"] = None
        cell["null_reasons"] = dict.fromkeys(("absolute_return_pct", "relative_wealth_pct"), cause)
        _exact_recount(packet)
    elif change == "null_start": window["start_session"] = None
    elif change == "null_start_nonzero":
        packet = _exact_owner_case("insufficient"); parent = _exact_window_parent(packet)
        packet["windows"]["63"]["benchmark_coverage"].update(observed_n=1, ratio=0.015625)
    elif change == "unsorted_columns": packet["diagnostics"]["columns"].reverse()
    elif change == "bad_duplicate_date": packet["diagnostics"]["duplicate_sessions"] = ["2026-02-30"]
    elif change == "bad_future_date": packet["diagnostics"]["future_tail_sessions"] = ["2026-02-30"]
    elif change == "future_not_future": packet["diagnostics"]["future_tail_sessions"] = ["2026-11-05"]
    elif change == "unknown_binding": packet["diagnostics"]["binding_keys"] = ["authoritative"]
    elif change == "receipt_withheld_present":
        packet["receipt"] = {"owner": "opaque"}; packet["diagnostics"]["receipt_withheld"] = True
    elif change == "naive_clock":
        packet["clocks"]["publication"] = "2026-11-05T23:00:00"
        packet["limitations"]["publication"] = {"status": "supplied", "clock": packet["clocks"]["publication"]}
    elif change == "clock_limitation": packet["clocks"]["publication"] = "2026-11-05T23:00:00Z"
    elif change == "unknown_limit": packet["limitations"]["freshness"]["status"] = "verified"
    elif change == "missing_authority": packet["authority"].pop("may_size")
    with pytest.raises(SectorViewUnavailable):
        _measured_read(parent, "2026-11-05")


@pytest.mark.parametrize("kind", ["ascii_bytes", "container_length", "cycle", "exotic", "depth", "nodes"])
def test_exact_window_receipt_is_bounded_before_copy_or_container_serialization(kind, monkeypatch):
    import engine.sector_native_view as native
    packet = _exact_window_packet()
    if kind == "ascii_bytes": receipt = {"a": "中" * 3000}
    elif kind == "container_length": receipt = {"a": [0] * 257}
    elif kind == "cycle":
        receipt = {}; receipt["a"] = receipt
    elif kind == "exotic":
        class HostObject(dict):
            def __deepcopy__(self, memo):
                raise AssertionError("custom copy invoked")
        receipt = HostObject(a=1)
    elif kind == "depth":
        receipt = {}; node = receipt
        for _ in range(9):
            node["a"] = {}; node = node["a"]
    else: receipt = {str(i): [0] * 64 for i in range(32)}
    packet["receipt"] = receipt
    parent = _exact_window_parent(packet)
    original_dumps = native.json.dumps
    def no_copy(*args, **kwargs):
        raise AssertionError("copy before admission")
    def primitives_only(value, *args, **kwargs):
        assert type(value) not in (dict, list), "container serialized before admission"
        return original_dumps(value, *args, **kwargs)
    monkeypatch.setattr(native, "deepcopy", no_copy)
    monkeypatch.setattr(native.json, "dumps", primitives_only)
    with pytest.raises(SectorViewUnavailable, match="invalid_sector_window_measurements"):
        native._sector_window_measurements(packet, parent, "2026-11-05", set(_NATIVE_DOSSIER_IDS))


@pytest.mark.parametrize("receipt", [
    {"many": [None] * 256},
    {str(i): [{} for _ in range(10)] for i in range(32)},  # >256 containers; each is small
    {"a": "中" * 2000, "mixed": [None, False, 1.0, -0.0, "opaque"]},
])
def test_exact_window_receipt_owner_bounds_detach_and_preserve(receipt):
    from engine.sector_native_view import _measured_read
    packet = _exact_owner_case(binding={"receipt": receipt})
    before = deepcopy(packet)
    result = _measured_read(_exact_window_parent(packet), "2026-11-05")
    assert result["sector_window_measurements"] == before
    assert result["sector_window_measurements"]["receipt"] is not packet["receipt"]
    packet["receipt"].clear()
    assert result["sector_window_measurements"] == before


@pytest.mark.parametrize("clock", ["20261105T230000+0000", "2026-W45-4T23:00:00+00:00",
                                    "2026-11-05 23:00:00.123456+00:00"])
def test_exact_window_supplied_aware_owner_clocks_keep_their_text(clock):
    from engine.sector_native_view import _measured_read
    packet = _exact_owner_case(binding={"clocks": dict.fromkeys(
        ("publication", "availability", "correction", "history"), clock)})
    result = _measured_read(_exact_window_parent(packet), "2026-11-05")["sector_window_measurements"]
    assert result["clocks"] == packet["clocks"]
    assert result["limitations"]["availability"] == {"status": "supplied", "clock": clock}
    assert result["limitations"]["corrections"]["status"] == "unavailable"
    assert result["limitations"]["point_in_time"]["status"] == "not_qualified"


def test_exact_window_unmeasured_legacy_and_generationless_stub_have_different_admission():
    from engine.sector_native_view import _measured_read
    packet = _exact_window_packet()
    parent = _exact_window_parent(packet)
    parent["status"] = "unavailable"
    parent["cohort"]["measured_n"] = 0
    for row in parent["groups"]:
        row["current"].update(status="unmeasured", rank=None, rs_21d=None, rs_63d=None,
                              reason="missing_input")
    assert _measured_read(parent, "2026-11-05")["sector_window_measurements"] == packet
    stub = {"schema": parent["schema"], "status": "unavailable", "reason": "projection_error",
            "sector_window_measurements": packet}
    with pytest.raises(SectorViewUnavailable, match="invalid_sector_window_measurements"):
        _measured_read(stub, "2026-11-05")


def test_exact_window_valid_companion_does_not_hide_present_invalid_legacy():
    from engine.sector_native_view import _measured_read
    packet = _exact_window_packet()
    parent = _exact_window_parent(packet)
    parent["sector_dossiers"] = {"schema": "malformed"}
    with pytest.raises(SectorViewUnavailable, match="invalid_sector_dossiers"):
        _measured_read(parent, "2026-11-05")


def test_exact_window_canonical_fixture_hashes():
    for name, expected in [
        ("complete", "6b33895711742dee8cb1366baab5572a6aef31d6ca9ca6d0f81e32ab879e6dae"),
        ("unavailable", "e4419e3a4d7dabce4ad4fd760c1fc37d05b8fe1111102ac5b0bb13b1a980f17e"),
    ]:
        raw = (_WINDOW_FIXTURE_DIR / f"sector_window_measurements.{name}.v1.json").read_bytes()
        assert hashlib.sha256(raw).hexdigest() == expected

@pytest.mark.parametrize("scope", ["group", "benchmark"])
@pytest.mark.parametrize("observed", [2, 20])
def test_exact_nested_window_coverage_is_one_captured_panel(scope, observed):
    from engine.sector_native_view import _measured_read
    packet = _exact_window_packet()
    windows = packet["windows"] if scope == "benchmark" else packet["groups"][0]["windows"]
    key = "5" if observed == 2 else "63"
    coverage = windows[key]["benchmark_coverage" if scope == "benchmark" else "coverage"]
    coverage.update(observed_n=observed, ratio=round(observed / coverage["expected_n"], 6))
    with pytest.raises(SectorViewUnavailable, match="invalid_sector_window_measurements"):
        _measured_read(_exact_window_parent(packet), "2026-11-05")
