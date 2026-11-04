"""D03 T47: real Pick Lab markup plus local navigation-state regressions.

The Node harness executes the rendered inline navigation script, using a small
DOM model built from that same HTML. Real-browser geometry/focus/motion proof is
recorded separately; this does not claim that the model is a browser.
"""
from __future__ import annotations

from html.parser import HTMLParser
import json
from pathlib import Path
import subprocess

from jinja2 import Environment, FileSystemLoader
import pytest

from engine.pick_lab.render import build_vm


ROOT = Path(__file__).resolve().parents[1]
TABS = ("scoreboard", "velocity", "allbooks", "beta", "longhold", "accountability", "method")
ENTRY = "plab_1d_pure"
SECOND = "plab_1d_regime"
LONG_HOLD = "plab_lh_compounder"


def navigation_vm(*, empty=False, singleton=False):
    """Small producer-shaped fixture; no production file, engine or ledger runs."""
    if empty:
        return build_vm(None, None)
    rows = []
    for eid, en, zh, family, role in (
        (ENTRY, "1D Pure", "1日纯速", "A", "entry"),
        (SECOND, "1D Regime", "1日制度", "A", "entry"),
        (LONG_HOLD, "LH Compounder", "长持复利", "LH", "hold_thesis"),
    ):
        if singleton and eid == SECOND:
            continue
        rows.append(dict(engine_id=eid, name_en=en, name_zh=zh, family=family,
                         horizon_role=role, ruler="21d_spy_excess", status="accruing",
                         n_fires=0, n_open=0, n_dates=0, months_span=None,
                         wr21_abs=None, wr21_excess=None, med_excess21=None,
                         mfe_med=None, mae_med=None, asym=None, nav_excess_cum=None,
                         max_dd=None, vs_random_lift=None, vs_universe_lift=None))
    payload = {"as_of": "2026-11-02", "scoreboard": rows, "books": {}, "lanes": {}, "regime": {}}
    lh = {"as_of": "2026-11-02", "books": {}}
    fires = {"fires_by_book": {eid: [
        {"ticker": "AAA", "fire_date": "2026-11-01", "ret21_excess": None, "matured": False},
        {"ticker": "BBB", "fire_date": "2026-10-01", "ret21_excess": 0.02, "matured": True},
    ] for eid in (ENTRY, LONG_HOLD)}}
    return build_vm(payload, lh, fires_dict=fires)


def render_navigation(*, empty=False, singleton=False):
    env = Environment(loader=FileSystemLoader(str(ROOT / "templates")), autoescape=True)
    return env.get_template("us_stocks_lab.html.j2").render(**navigation_vm(empty=empty, singleton=singleton))


class Markup(HTMLParser):
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self, html):
        super().__init__()
        self.nodes = [{"tag": "document", "attrs": {}, "parent": None, "text": ""}]
        self.stack = [0]
        self.scripts = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.nodes.append({"tag": tag, "attrs": dict(attrs), "parent": self.stack[-1], "text": ""})
        if tag not in self.VOID:
            self.stack.append(len(self.nodes) - 1)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.nodes[self.stack[i]]["tag"] == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        self.nodes[self.stack[-1]]["text"] += data

    def with_class(self, name):
        return [n for n in self.nodes if name in (n["attrs"].get("class") or "").split()]

    def by_id(self, value):
        return next((n for n in self.nodes if n["attrs"].get("id") == value), None)

    def navigation_script(self):
        scripts = [n["text"] for n in self.nodes if n["tag"] == "script" and not n["attrs"].get("src")]
        return next(s for s in scripts if ".book-drill" in s)


@pytest.mark.parametrize("empty", [False, True])
def test_main_tabs_retain_all_sections_with_reciprocal_relationships(empty):
    dom = Markup(render_navigation(empty=empty))
    tabs = dom.with_class("tabbtn")
    ids = [n["attrs"]["id"] for n in dom.nodes if n["attrs"].get("id")]
    assert len(ids) == len(set(ids)), "Rendered IDs must be unique"
    assert tuple(n["attrs"]["data-tab"] for n in tabs) == TABS
    for i, tab in enumerate(tabs):
        a = tab["attrs"]
        assert a["type"] == "button"
        assert a["role"] == "tab"
        assert a["aria-selected"] == ("true" if i == 0 else "false")
        assert a["tabindex"] == ("0" if i == 0 else "-1")
        panel = dom.by_id(a["aria-controls"])
        assert panel and panel["attrs"]["data-tab-panel"] == a["data-tab"]
        assert panel["attrs"]["role"] == "tabpanel"
        assert panel["attrs"]["aria-labelledby"] == a["id"]
        assert dom.by_id(panel["attrs"]["aria-labelledby"]) is tab
        assert panel["attrs"]["tabindex"] == "0"
        assert ("hidden" in panel["attrs"]) is (i != 0)


def test_book_selector_preserves_identity_history_and_accessibility():
    dom = Markup(render_navigation())
    chips = dom.with_class("book-chip")
    assert [n["attrs"]["data-ab"] for n in chips] == [ENTRY, SECOND]
    for i, chip in enumerate(chips):
        a = chip["attrs"]
        assert a["type"] == "button" and a["role"] == "tab"
        assert a["aria-selected"] == ("true" if i == 0 else "false")
        assert a["tabindex"] == ("0" if i == 0 else "-1")
        panel = dom.by_id(a["aria-controls"])
        assert panel["attrs"]["id"] == "ab-" + a["data-ab"]
        assert panel["attrs"]["aria-labelledby"] == a["id"]
        assert dom.by_id(panel["attrs"]["aria-labelledby"]) is chip
        assert panel["attrs"]["role"] == "tabpanel"
        assert ("hidden" in panel["attrs"]) is (i != 0)
    focus_targets = [n for n in dom.nodes if "data-book-focus" in n["attrs"]]
    assert len(focus_targets) == len(chips) + 4  # Existing four LH grids retained.
    assert all(n["attrs"].get("tabindex") == "-1" for n in focus_targets)
    assert all(n["attrs"].get("role") == "heading" for n in focus_targets)
    assert dom.by_id("lh-" + LONG_HOLD)
    assert len(dom.with_class("all-fires-details")) == 2


@pytest.mark.parametrize("scenario", [
    "initial", "arrow_wrap", "arrow_cycle", "home_end", "native_activation", "panel_tabstop",
    "nested_books", "entry_drill", "longhold_drill", "missing_destination",
    "missing_chip", "malformed_control", "motion_preference_changes",
    "modified_keys", "empty_page", "singleton_book", "removed_chip", "wrong_label",
])
def test_actual_inline_navigation_state(scenario):
    dom = Markup(render_navigation(empty=scenario == "empty_page", singleton=scenario == "singleton_book"))
    request = {"nodes": dom.nodes, "script": dom.navigation_script(), "scenario": scenario,
               "entry": ENTRY, "second": SECOND, "longhold": LONG_HOLD}
    result = subprocess.run(
        ["node", str(ROOT / "tests/js/pick_lab_navigation_harness.cjs")],
        input=json.dumps(request), text=True, capture_output=True, timeout=20,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout) == {"scenario": scenario, "passed": True}
