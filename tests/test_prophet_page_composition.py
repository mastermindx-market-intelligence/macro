"""User-facing composition and degraded-source contracts for the US workspace."""
from bs4 import BeautifulSoup
from tests.test_dashboard_template_render import _base_vm, _env
from tests.test_action_board_hover_cards import _sector, _theme

def render(vm):
    return BeautifulSoup(_env().get_template("dashboard.html.j2").render(**vm, mode="stocks"), "html.parser")

def test_current_opportunities_precede_context_without_losing_source_controls():
    doc = render(_base_vm())
    nodes = list(doc.find_all(True))
    assert nodes.index(doc.select_one("#us-standouts")) < nodes.index(doc.select_one("#action-board"))
    assert nodes.index(doc.select_one("#us-standouts")) < nodes.index(doc.select_one("#prophet-market-context"))
    assert {b["data-src"] for b in doc.select("#us-src-toggle button")} == {"today", "candidates", "plans"}
    assert len(doc.select("h1")) == 1
    for link in doc.select(".prophet-section-nav a[href^='#']"):
        assert doc.find(id=link["href"][1:]), link["href"]

def test_stock_source_survives_independent_theme_source_failure():
    vm = _base_vm()
    expected = [c["data-ticker"] for c in render(vm).select("#us-cand-grid .po-card")]
    vm["action_board"] = None
    doc = render(vm)
    assert [c["data-ticker"] for c in doc.select("#us-cand-grid .po-card")] == expected
    assert set(expected) == {"ACME", "ZEUS"}
    assert doc.select_one("#us-src-toggle")
    assert not doc.select_one(".prophet-empty-workspace")
    assert not doc.select_one("#action-board")

def test_missing_board_retains_useful_navigation_without_false_freshness():
    vm = _base_vm()
    vm.update(us_standouts=None, action_board=None, us_prophet_book=None)
    doc = render(vm)
    assert len(doc.select("#us-standouts")) == 1
    empty = doc.select_one("#us-standouts.prophet-empty-workspace")
    assert empty and "Opportunities unavailable" in empty.get_text()
    header = doc.select_one("#stocks-header")
    assert "Board date unavailable" in header.get_text()
    assert not header.select_one(".stk-fresh-dot")
    for link in doc.select(".prophet-section-nav a[href^='#']"):
        assert doc.find(id=link["href"][1:]), link["href"]

def test_observation_feed_follows_cards_and_keeps_every_observation():
    vm = _base_vm()
    rows = [{"ticker": f"OBS{i}", "state": "PULLBACK"} for i in range(18)]
    vm["us_leader_observations"] = {
        "status": "ready", "source": {"data_session": "2026-07-04"},
        "counts": {"active": 18}, "rows": rows,
    }
    doc = render(vm)
    feed = doc.select_one("#us-leader-observations .plo-rows")
    assert [r["data-ticker"] for r in feed.select(".plo-row")] == [r["ticker"] for r in rows]
    assert feed["tabindex"] == "0"
    assert doc.find(id=feed["aria-labelledby"])
    nodes = list(doc.find_all(True))
    assert nodes.index(doc.select_one("#us-cand-grid")) < nodes.index(feed)
    assert not feed.select("button,[data-src],.pv-setup-inline")

def test_stand_aside_overlay_counts_rows_and_carries_explanation_separately():
    vm = _base_vm()
    vm["action_board"] = {
        "buy_now": [], "buy_soon": [], "on_the_run": [], "take_profits": [],
        "hold": [_sector(), _theme(), _sector()], "avoid": [_theme()],
        "notable": [], "buy": [], "more": {"hold": 8, "avoid": 2},
    }
    doc = render(vm)
    lane = doc.select_one("#action-board .act-hold")
    rows = lane.select_one("#dash-hold-fold")
    # initListOverlay intentionally counts direct children; an explanatory
    # paragraph used to be counted as a fifth holding.
    assert len(rows.find_all(recursive=False)) == int(lane.select_one(".acth-count").get_text()) == 4
    carry = lane.select_one(":scope > [data-ovl-carry]")
    assert carry and "+10 more" in carry.get_text()
    assert not rows.select("[data-ovl-carry]")
