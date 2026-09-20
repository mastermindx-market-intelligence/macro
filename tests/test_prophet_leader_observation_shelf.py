"""RED production-path tests for the Prophet leader-observation shelf.

The suite uses the incumbent build_prophet.main(), build_site tier split, current
dashboard template, and existing us_stocks protected payload. No alternate endpoint,
board, ranker, or plan serializer is permitted.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

from bs4 import BeautifulSoup

from engine import us_leader_pullback as organ
from engine import us_leader_pullback_coverage as cov
import scripts.build_site as bs
from tests.test_dashboard_template_render import (
    _base_vm, _env, _prophet_book, _prophet_plan,
)
from tests.test_prophet_anticipation_intake import ASOF, BUYS, _run_main


def _row(state: str | None, **extra) -> dict:
    row = {
        "schema": organ.SCHEMA,
        "construction_era": organ.CONSTRUCTION_ERA,
        "asof": ASOF,
        "state": state,
    }
    row.update(extra)
    if state is None:
        row["null_reason"] = "insufficient history"
    return {key: value for key, value in row.items() if value is not None}


def _artifact() -> dict:
    states = {
        "ZZZ": _row("RESUMED", rs_pct=0.86),
        "AAA": _row("LEADER", rs_pct=0.95),
        "DDD": _row("PULLBACK", zone_low=78.0, zone_high=82.0,
                    pullback_depth=0.10, pullback_age=5),
        "CCC": _row("RESET_TURN", zone_low=91.0, zone_high=95.0,
                    reset_low=90.0, pullback_age=8),
        "BBB": _row("LEADER", rs_pct=0.91),
        "NULL": _row(None),
    }
    return {
        "schema": cov.SCHEMA,
        "as_of": ASOF,
        "data_session": ASOF,
        "max_session": ASOF,
        "session_note": None,
        "selection_era": cov.SELECTION_ERA,
        "construction_era": organ.CONSTRUCTION_ERA,
        "authority": cov.AUTHORITY,
        "coverage": {
            "states_published": len(states),
            "state_counts": {
                "LEADER": 2,
                "PULLBACK": 1,
                "RESET_TURN": 1,
                "RESUMED": 1,
            },
            "null_counts": {"insufficient history": 1},
            "publishable": True,
        },
        "states": states,
    }


def _projection() -> dict:
    return cov.project_prophet_observations(
        _artifact(), reference_session=ASOF
    )


def _render(projection: dict | None, *, pgate=None) -> str:
    vm = _base_vm()
    vm.update({
        "gate": None,
        "life_gate": None,
        "pgate": pgate,
        "us_prophet_book": _prophet_book(
            plans=[_prophet_plan(id="PLAN-1", asset="PLAN")],
        ),
        "us_leader_observations": projection,
    })
    return _env().get_template("dashboard.html.j2").render(**vm, mode="stocks")


def test_real_prophet_publisher_adds_summary_only_and_moves_no_plan_bytes(tmp_path: Path):
    without_root = tmp_path / "without"
    with_root = tmp_path / "with"
    without_root.mkdir()
    with_root.mkdir()

    control = _run_main(without_root, BUYS, asof=ASOF)
    cov.write_artifact(_artifact(), with_root / "site")
    observed = _run_main(with_root, BUYS, asof=ASOF)

    assert json.dumps(observed["plans"], sort_keys=True) == json.dumps(
        control["plans"], sort_keys=True
    )
    for key in (
        "plan_count", "active_count", "open_count", "lifecycle_counts",
        "lifecycle_live_total", "lifecycle_grand_total",
    ):
        assert observed[key] == control[key]

    summary = observed["leader_observation_summary"]
    assert summary["status"] == "available"
    assert summary["counts"]["active"] == 5
    assert "rows" not in summary
    encoded = json.dumps(summary, sort_keys=True)
    assert all(ticker not in encoded for ticker in ("AAA", "BBB", "CCC", "DDD", "ZZZ"))

    unavailable = control["leader_observation_summary"]
    assert (unavailable["status"], unavailable["reason_code"]) == (
        "unavailable", "artifact_absent"
    )


def test_tier_split_is_pure_and_server_side():
    full = _projection()
    original = deepcopy(full)

    shell, gate, locked = bs._split_us_leader_observations(
        full, 3, gated=True
    )

    assert full == original
    assert [row["ticker"] for row in shell["rows"]] == ["AAA", "BBB", "CCC"]
    assert [row["ticker"] for row in locked] == ["DDD", "ZZZ"]
    assert gate == {
        "preview": 3,
        "locked": 2,
        "total": 5,
        "tier": "essential",
        "payload": bs.US_PAYLOAD_URL,
    }
    assert shell["counts"] == full["counts"]


def test_panel_split_and_existing_payload_carry_the_locked_remainder(tmp_path: Path):
    vm = _base_vm()
    vm["us_leader_observations"] = _projection()

    overrides, pgate, locked = bs._split_us_panels(vm, 3, gated=True)
    assert pgate["leader_observations"] == {
        "preview": 3, "locked": 2, "total": 5
    }
    assert [row["ticker"] for row in
            overrides["us_leader_observations"]["rows"]] == ["AAA", "BBB", "CCC"]
    assert [row["ticker"] for row in locked["leader_observations"]] == [
        "DDD", "ZZZ"
    ]

    render_vm = {**vm, **overrides}
    blocks = bs._render_us_panel_payload(_env(), pgate, locked, render_vm)
    assert "leader_observations_html" in blocks
    assert "DDD" in blocks["leader_observations_html"]
    assert "ZZZ" in blocks["leader_observations_html"]

    bs._write_us_payload(
        _env(), tmp_path, None,
        locked_rows=[],
        us_standouts=vm.get("us_standouts"),
        top_setups=vm.get("top_setups"),
        built=ASOF,
        pgate=pgate,
        panel_blocks=blocks,
        life_gate=None,
        locked_plans=[],
    )
    payload = json.loads(
        (tmp_path / bs.US_PAYLOAD_DIR / bs.US_PAYLOAD_NAME).read_text()
    )
    assert payload["panels"]["leader_observations"] == {
        "preview": 3, "locked": 2, "total": 5
    }
    assert payload["leader_observations_html"] == blocks[
        "leader_observations_html"
    ]


def test_rendered_shelf_is_a_separate_display_population():
    full = _projection()
    shell, gate, _locked = bs._split_us_leader_observations(
        full, 3, gated=True
    )
    pgate = {
        "tier": "essential",
        "payload": bs.US_PAYLOAD_URL,
        "preview": 3,
        "leader_observations": gate,
    }
    html = _render(shell, pgate=pgate)
    soup = BeautifulSoup(html, "html.parser")
    shelf = soup.select_one("#us-leader-observations")

    assert shelf is not None
    assert len(shelf.select(".plo-row")) == 3
    assert [row.get("data-ticker") for row in shelf.select(".plo-row")] == [
        "AAA", "BBB", "CCC"
    ]
    assert not shelf.select("[data-life], [data-mp1-grid], .cand-row, .nb-card")
    assert soup.select_one("#us-cand-grid") is not None
    assert soup.select_one("#us-life-grid") is not None

    text = shelf.get_text(" ", strip=True)
    assert ASOF in text
    assert "Leaders / waiting for entry" in text
    assert "领涨股 / 等待入场条件" in text
    for banned in (
        "buy now", "enter now", "recommended buy", "strong buy", "add position"
    ):
        assert banned not in text.lower()
    assert "2 more observed names" in text


def test_each_state_has_plain_bilingual_non_authority_copy():
    html = _render(_projection())
    soup = BeautifulSoup(html, "html.parser")
    shelf = soup.select_one("#us-leader-observations")
    text = shelf.get_text(" ", strip=True)

    assert "Leading now" in text and "当前领涨" in text
    assert "Controlled retrace" in text and "受控回撤" in text
    assert "Reset/turn context" in text and "重置/转折背景" in text
    assert "Leadership resumed" in text and "领涨已恢复" in text
    assert "do not chase" in text.lower() and "不要追高" in text


def test_empty_unavailable_and_degraded_are_visibly_distinct():
    base = _projection()

    empty = deepcopy(base)
    empty.update(status="empty", reason_code="no_active_states", rows=[])
    empty["counts"]["active"] = 0

    unavailable = deepcopy(base)
    unavailable.update(
        status="unavailable", reason_code="artifact_absent", rows=[]
    )

    degraded = deepcopy(base)
    degraded.update(status="degraded", reason_code="unknown_state_rows")

    rendered = {
        state: BeautifulSoup(_render(payload), "html.parser")
        .select_one("#us-leader-observations")
        .get_text(" ", strip=True)
        for state, payload in (
            ("empty", empty),
            ("unavailable", unavailable),
            ("degraded", degraded),
        )
    }
    assert "No active leader-reset states" in rendered["empty"]
    assert "Leader observations unavailable" in rendered["unavailable"]
    assert "Some source rows could not be classified" in rendered["degraded"]
    assert len(set(rendered.values())) == 3


def test_anonymous_preview_does_not_emit_an_empty_show_more_control():
    html = _render(_projection())
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.select_one("#us-leader-observations .plo-rows")

    assert rows is not None
    assert rows.get("data-showmore-rows") is None


def test_paid_hydration_rebuilds_the_leader_grid_before_show_more():
    source = (Path(__file__).resolve().parent.parent
              / "templates" / "dashboard.html.j2").read_text()

    assert "function hydrateLeaderObservations(html)" in source
    assert (
        "appendTo('#us-leader-observations .plo-rows', "
        "payload.leader_observations_html)"
    ) not in source
    assert "hydrateLeaderObservations(payload.leader_observations_html);" in source

    helper = source.split("function hydrateLeaderObservations(html)", 1)[1].split(
        "function hydratePanels(payload)", 1
    )[0]
    for token in (
        "document.querySelector('#us-leader-observations .plo-rows')",
        "document.createElement('div')",
        "freshGrid.className = grid.className",
        "freshGrid.setAttribute('data-showmore-rows', '3')",
        "freshGrid.innerHTML = grid.innerHTML + html",
        "grid.parentNode.insertBefore(freshGrid, grid)",
        "grid.parentNode.removeChild(grid)",
        "oldBar.parentNode.removeChild(oldBar)",
        "window.initShowMore",
    ):
        assert token in helper

    assert "payload.leader_observations_html" not in source.split(
        "function hydrate(payload)"
    )[1].split("var lifeGrid")[1], (
        "leader rows must hydrate before candidate/plan grids"
    )
