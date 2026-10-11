"""US Risk Radar popup switches to observed damage without replacing its modal shell.

Uses the existing product-sized Jinja render fixture; no new modal framework.
"""
from copy import deepcopy

from bs4 import BeautifulSoup
import pytest

from tests.test_macro_risk_dialog import _vm, _render, _dlg
from tests.test_risk_radar_pullback_depth_template import native_view


def dialog(view=None, *, mode="macro"):
    vm = _vm()
    if view is not None:
        vm["us_pullback_view"] = view
    return BeautifulSoup(_dlg(_render(vm=vm, mode=mode)), "html.parser")


def test_current_active_observation_leads_and_original_risk_evidence_remains_accessible():
    mode = "macro"
    root = dialog(native_view("us"), mode=mode)
    assert len(root.select('#dlg-risk')) <= 1  # extracted snippet begins inside the modal
    measured = root.select_one("section.rrp")
    assert measured and measured.get("data-pb-phase") == "underway"
    assert measured.select_one('[data-metric="current"]').get_text(strip=True) == "−6.8%"
    assert measured.select_one('[data-metric="worst"]').get_text(strip=True) == "−7.4%"
    assert measured.select_one('[data-forecast-status="unavailable"]')
    old = root.select_one(".riskdlg-brief")
    assert old is not None
    assert old.find_parent("details", class_="riskdlg-legacy-details") is not None
    disclosure = root.select_one("details.riskdlg-legacy-details")
    assert disclosure is not None and not disclosure.has_attr("open")
    assert "Forward risk and drivers" in disclosure.select_one("summary").get_text(" ", strip=True)
    html = str(root)
    assert "mx5CloseDlg()" in html
    assert "mx5-dlg-backdrop" in html


@pytest.mark.parametrize("phase", ["stabilizing", "recovering"])
def test_repair_observations_keep_the_measurement_primary_without_authorizing_buy(phase):
    view = native_view("us")
    view["phase"] = phase
    view["observation"]["phase"] = phase
    root = dialog(view)
    assert root.select_one("section.rrp").get("data-pb-phase") == phase
    assert "not a new-entry signal" in root.get_text(" ", strip=True)
    assert root.select_one('details.riskdlg-legacy-details') is not None


@pytest.mark.parametrize("change", [
    ("quality", "delayed"),
    ("schema", "wrong.v1"),
    ("clock", "intraday"),
    ("valid_until", None),
    ("available", False),
    ("market", "cn"),
    ("active", False),
    ("phase", "monitoring"),
    # Rejected by the fragment's price checks: must not displace the popup either.
    ("low_close", None),
    ("close", 101.0),
])
def test_unqualified_or_pre_episode_view_keeps_previous_forecast_first_layout(change):
    v = native_view("us")
    k, value = change
    v["observation"][k] = value
    if k == "phase":
        v["phase"] = value
    root = dialog(v)
    assert root.select_one("section.rrp") is None
    assert root.select_one(".riskdlg-brief")
    assert root.select_one("details.riskdlg-legacy-details") is None


def test_missing_view_keeps_existing_popup_untouched():
    root = dialog()
    assert root.select_one(".riskdlg-brief")
    assert root.select_one("section.rrp") is None


def test_shared_pullback_css_is_present_in_the_real_us_page():
    html = _render(vm=_vm(), mode="macro")
    assert ".riskdlg-legacy-details" in html
    assert ".rrp-metrics" in html


ILLUS_LINK = '<link rel="stylesheet" href="illus.css">'


def test_observed_path_chart_loads_the_shared_illustration_stylesheet():
    # Without the shared stylesheet the chart's stroke path fills black and its
    # axis labels collapse into one unpositioned run (seen in the served page).
    vm = _vm()
    vm["us_pullback_view"] = native_view("us")
    html = _render(vm=vm, mode="macro")
    dlg = _dlg(html)
    assert dlg.count(ILLUS_LINK) == 1
    assert dlg.index(ILLUS_LINK) < dlg.index('class="ilx')


@pytest.mark.parametrize("view", [None, "inactive", "no_chart"])
def test_macro_page_is_unchanged_when_no_observed_chart_renders(view):
    vm = _vm()
    if view == "inactive":
        v = native_view("us")
        v["observation"]["quality"] = "delayed"
        vm["us_pullback_view"] = v
    elif view == "no_chart":
        v = native_view("us")
        v["detail_chart_html"] = ""
        vm["us_pullback_view"] = v
        assert dialog(v).select_one("section.rrp") is not None
    assert ILLUS_LINK not in _render(vm=vm, mode="macro")


def test_illustration_stylesheet_is_published_beside_the_macro_page():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    assert (root / "templates" / "illus.css").is_file()
    assert '"illus.css"' in (root / "scripts" / "build_site.py").read_text()



# A popup-shaped tree in the order the shipped dialog renders it. `shown` is what
# getClientRects reports: Chrome still reports boxes for a closed <details>' content
# (it is content-visibility skipped, not display:none), which defeated a box-only
# filter in the served-page keyboard check.
FAKE_DIALOG_JS = r"""
const assert = require('node:assert/strict');
const doc = {activeElement: null};
function el(tag, opts = {}) {
  return {tag, open: !!opts.open, shown: opts.shown !== false, tabIndex: opts.tabIndex ?? 0,
          name: opts.name || tag, children: [], parentElement: null,
          getClientRects() { return this.shown ? [{}] : []; },
          focus() { doc.activeElement = this; },
          contains(o) { for (let n = o; n; n = n.parentElement) if (n === this) return true; return false; },
          closest(sel) {
            if (sel === '[inert]' || sel === '.lens-pop.open') return null;
            assert.equal(sel, 'details:not([open])');
            for (let n = this; n; n = n.parentElement) if (n.tag === 'details' && !n.open) return n;
            return null;
          },
          querySelector(sel) {
            assert.equal(sel, ':scope > summary');
            return this.children.find(c => c.tag === 'summary') || null;
          },
          querySelectorAll(sel) {
            const parts = sel.split(','), out = [];
            const hit = c => parts.some(p => p === c.tag || p.startsWith(c.tag + ':')
                                        || (c.tag === 'a' && p === 'a[href]'));
            (function walk(n) { for (const c of n.children) { if (hit(c)) out.push(c); walk(c); } })(this);
            return out;
          }};
}
function add(parent, child) { child.parentElement = parent; parent.children.push(child); return child; }
const dlg = el('div');
const close = add(dlg, el('button', {name: 'close'}));
add(dlg, el('button', {name: 'decorative', tabIndex: -1}));
add(dlg, el('button', {name: 'unrendered', shown: false}));
const why = add(dlg, el('details'));
const whySummary = add(why, el('summary', {name: 'why no estimate'}));
add(why, el('a', {name: 'why link'}));
const legacy = add(dlg, el('details'));
const legacySummary = add(legacy, el('summary', {name: 'forward risk and drivers'}));
const body = add(legacy, el('div'));
const driver = add(body, el('button', {name: 'driver'}));
const method = add(body, el('details'));
const methodSummary = add(method, el('summary', {name: 'method'}));
add(method, el('a', {name: 'method link'}));
const names = list => list.map(n => n.name);
"""


def _node(script: str, stdin: str) -> None:
    _node_raw(FAKE_DIALOG_JS + script, stdin)


def _node_raw(script: str, stdin: str) -> None:
    import os
    import shutil
    import subprocess
    node = shutil.which("node")
    if not node:
        # A skip would turn these regressions green without running them.
        if os.environ.get("CI"):
            pytest.fail("Node is required in CI to execute the shipped dialog scripts")
        pytest.skip("Node is required to execute the shipped dialog scripts")
    result = subprocess.run([node, "-e", script], input=stdin, text=True,
                            capture_output=True, timeout=20)
    assert result.returncode == 0, result.stdout + result.stderr


def _between(path: str, start: str, end: str) -> str:
    from pathlib import Path
    page = (Path(__file__).resolve().parents[1] / path).read_text()
    a = page.index(start)
    return page[a:page.index(end, a)]


def test_tab_trap_wraps_over_the_closed_forward_risk_disclosure():
    """Run the shipped `_tabStop`/`_trapTab` bodies against the popup's stop order.

    The forward-risk evidence now sits in a closed <details>. A trap that counts its
    hidden controls never sees focus reach `last`, so Tab walks out of the modal."""
    src = _between("templates/dashboard.html.j2", "function _tabStop(el){", "function _prefReduced(")
    _node(r"""
const src = require('node:fs').readFileSync(0, 'utf8');
const trap = new Function('document', src + '; return _trapTab;')(doc);
function tab(from, shift = false) {
  doc.activeElement = from;
  const e = {key: 'Tab', shiftKey: shift, prevented: false, preventDefault() { this.prevented = true; }};
  trap(dlg, e);
  return e;
}
// Closed disclosures: the forward-risk summary is the last stop, so Tab wraps.
let e = tab(legacySummary);
assert.equal(e.prevented, true);
assert.equal(doc.activeElement, close);
e = tab(close, true);
assert.equal(e.prevented, true);
assert.equal(doc.activeElement, legacySummary);
// Opened: its own controls become stops, a nested closed disclosure keeps only its summary.
legacy.open = true;
e = tab(legacySummary);
assert.equal(e.prevented, false);
e = tab(methodSummary);
assert.equal(e.prevented, true);
assert.equal(doc.activeElement, close);
// Non-Tab keys are never intercepted.
doc.activeElement = legacySummary;
const esc = {key: 'Escape', shiftKey: false, prevented: false, preventDefault() { this.prevented = true; }};
trap(dlg, esc);
assert.equal(esc.prevented, false);
""", src)
