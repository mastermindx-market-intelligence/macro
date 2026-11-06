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
        central={"as_of": "2026-11-03"},
        cycles={"meta": {"asOf": "2026-11-03"}},
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
