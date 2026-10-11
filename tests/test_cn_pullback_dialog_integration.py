"""China Risk Radar dialog switches to observed damage without replacing its shell.

Renders the shared country dialog (templates/_risk_radar_dlg.html.j2) the way
china.html.j2 calls it. HK and Canada share the partial and must be unaffected.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader

from lib import cn_pullback_observation as pb
from lib.pullback_observation import observe
from tests.test_cn_pullback_observation_adapter import FIXED_NOW, reader, store
from tests.test_risk_radar_dlg_partial import _RD
from tests.test_risk_radar_pullback_depth_template import native_view

ROOT = Path(__file__).resolve().parents[1]


def _render(view=None, mkt="cn") -> str:
    env = Environment(loader=FileSystemLoader(str(ROOT / "templates")), autoescape=False)
    tpl = env.from_string(
        '{% import "_risk_radar_dlg.html.j2" as rrd %}'
        "{{ rrd.risk_radar_dlg(mkt, rd, none, ctx) }}"
    )
    ctx = {"title_en": "China Risk Radar", "title_zh": "中国风险雷达"}
    if view is not None:
        ctx["pullback_view"] = view
    return tpl.render(mkt=mkt, rd=_RD, ctx=ctx)


def dialog(view=None, mkt="cn"):
    return BeautifulSoup(_render(view, mkt), "html.parser")


def test_current_active_observation_leads_and_radar_evidence_remains_accessible():
    root = dialog(native_view("cn"))
    shell = root.select_one("#cnx-dlg-risk")
    assert shell.get("role") == "dialog" and shell.get("aria-modal") == "true"
    measured = shell.select_one("section.rrp")
    assert measured and measured.get("data-pb-phase") == "underway"
    assert measured.select_one('[data-metric="current"]').get_text(strip=True) == "−6.8%"
    assert measured.select_one('[data-metric="worst"]').get_text(strip=True) == "−7.4%"
    assert measured.select_one('[data-metric="rebound"]').get_text(strip=True) == "+0.6%"
    assert measured.select_one('[data-forecast-status="unavailable"]')
    assert "Estimate unavailable" in measured.get_text(" ", strip=True)
    disclosure = shell.select_one("details.riskdlg-legacy-details")
    assert disclosure is not None and not disclosure.has_attr("open")
    assert "Forward risk and drivers" in disclosure.select_one("summary").get_text(" ", strip=True)
    # The radar headline, card and footer all move inside the disclosure intact.
    assert shell.select_one(".rrd-hd").find_parent("details", class_="riskdlg-legacy-details")
    assert shell.select_one(".rrd-foot").find_parent("details", class_="riskdlg-legacy-details")
    # The measurement precedes the disclosure; the page's close owners are unchanged.
    html = str(shell)
    assert html.index('class="rrp') < html.index("riskdlg-legacy-details")
    assert shell.select_one(".cnx-dlg-close").get("onclick") == "cnxCloseDlg()"
    assert shell.select_one(".cnx-dlg-backdrop").get("onclick") == "cnxCloseDlg()"


def test_section_carries_the_expiry_owner_and_its_dated_receipt():
    root = dialog(native_view("cn"))
    measured = root.select_one("section.rrp")
    assert measured.get("data-pb-valid-until") == "2026-10-01T09:00:00+00:00"
    assert measured.get("data-pb-asof") == "2026-09-30"
    assert measured.get("data-pb-digest") == "a" * 64
    scripts = [s.get_text() for s in root.select("script")]
    assert len(scripts) == 1 and "data-pb-valid-until" in scripts[0]
    assert "Price update needed" in scripts[0] and "价格数据待更新" in scripts[0]


@pytest.mark.parametrize("change", [
    ("quality", "delayed"),
    ("schema", "wrong.v1"),
    ("clock", "intraday"),
    ("valid_until", None),
    ("available", False),
    ("market", "us"),
    ("active", False),
    ("phase", "monitoring"),
    ("low_close", None),
    ("close", 101.0),
])
def test_unqualified_or_pre_episode_view_keeps_the_existing_dialog(change):
    v = native_view("cn")
    k, value = change
    v["observation"][k] = value
    if k == "phase":
        v["phase"] = value
    root = dialog(v)
    assert root.select_one("section.rrp") is None
    assert root.select_one("details.riskdlg-legacy-details") is None
    assert root.select_one(".rrd-hd") is not None
    assert not root.select("script")


@pytest.mark.parametrize("view", [None, "not-a-mapping"])
def test_missing_or_malformed_view_keeps_the_existing_dialog(view):
    root = dialog(view)
    assert root.select_one("section.rrp") is None
    assert root.select_one("details.riskdlg-legacy-details") is None


@pytest.mark.parametrize("mkt", ["hk", "ca"])
def test_other_country_dialogs_never_render_a_china_measurement(mkt):
    with_view = _render(native_view("cn"), mkt)
    assert with_view == _render(None, mkt)
    assert f'id="{mkt}x-dlg-risk"' in with_view
    assert 'class="rrp' not in with_view and "riskdlg-legacy-details" not in with_view


def test_adapter_output_renders_end_to_end_on_the_shanghai_composite():
    view = pb.present(pb.snapshot(now=FIXED_NOW, read=reader(store()), observer=observe))
    root = dialog(view)
    measured = root.select_one("section.rrp")
    assert measured is not None
    assert measured.get("data-pb-valid-until") == "2026-10-12T09:00:00+00:00"
    assert measured.get("data-pb-asof") == "2026-10-09"
    text = measured.get_text(" ", strip=True)
    assert "Shanghai Composite" in text and "上证综指" in text
    assert "SPY" not in str(measured)
    assert measured.select_one('[data-forecast-status="unavailable"]')
    assert 'aria-label="Observed Shanghai Composite' in str(measured)


def test_china_page_ships_the_section_styles_and_the_dialog_keyboard_contract():
    page = (ROOT / "templates" / "china.html.j2").read_text()
    head, _, body = page.partition("</head>")
    assert '{% include "_risk_radar_pullback_depth.css.j2" %}' in head
    # Focus enters on open, Tab is trapped, and focus returns to the opener on close.
    assert "_riskReturnFocus=document.activeElement" in body
    assert "first.focus({preventScroll:true})" in body
    assert "_riskReturnFocus.focus({preventScroll:true})" in body
    assert "#cnx-dlg-risk.open:not(.cnx-closing)" in body
    escape = body[body.index("if(e.key!=='Escape')return;"):]
    assert escape.index("cnxCloseDlg();") < escape.index("cnxClosePops();")


def test_china_tab_trap_counts_only_stops_outside_closed_disclosures():
    """Run the shipped `_riskTabStop` against the popup's stop order: with the radar
    evidence in a closed <details>, its summary must be the trap's last stop."""
    from tests.test_us_pullback_modal_integration import _between, _node

    src = _between("templates/china.html.j2", "function _riskTabStop(el){", "function cnxOpenDlg(")
    _node(r"""
const stop = new Function(require('node:fs').readFileSync(0, 'utf8') + '; return _riskTabStop;')();
const stops = () => names(dlg.querySelectorAll('button:not([disabled]),a[href],summary').filter(stop));
assert.deepEqual(stops(), ['close', 'why no estimate', 'forward risk and drivers']);
legacy.open = true;
assert.deepEqual(stops(), ['close', 'why no estimate', 'forward risk and drivers', 'driver', 'method']);
""", src)
    keydown = (ROOT / "templates" / "china.html.j2").read_text()
    assert ".filter(_riskTabStop);" in keydown
    assert "getClientRects().length>0;});" not in keydown


def test_china_tab_handler_wraps_and_pulls_stray_focus_back_into_the_dialog():
    """Execute the shipped `_riskTrapTab`, selector and all, not just its stop filter."""
    from tests.test_us_pullback_modal_integration import _between, _node

    src = _between("templates/china.html.j2", "function _riskTabStop(el){", "function cnxOpenDlg(")
    src = src.replace("var _RISK_STOPS=", "var _RISK_STOPS=globalThis.RISK_STOPS=", 1)
    _node(r"""
let riskOpen = true;
doc.querySelector = sel => {
  if (sel === '.hm-ov') return null;
  assert.equal(sel, '#cnx-dlg-risk.open:not(.cnx-closing)');
  return riskOpen ? dlg : null;
};
const trap = new Function('document', require('node:fs').readFileSync(0, 'utf8') + '; return _riskTrapTab;')(doc);
assert.match(globalThis.RISK_STOPS, /^button:not\(:disabled\),a\[href\],input:not\(:disabled\)/);
const outside = el('button', {name: 'after the dialog'});
function tab(from, shift = false) {
  doc.activeElement = from;
  const e = {key: 'Tab', shiftKey: shift, prevented: false, preventDefault() { this.prevented = true; }};
  trap(e);
  return e;
}
// Closed disclosure: its summary is the last stop and Tab wraps both ways.
let e = tab(legacySummary);
assert.equal(e.prevented, true); assert.equal(doc.activeElement, close);
e = tab(close, true);
assert.equal(e.prevented, true); assert.equal(doc.activeElement, legacySummary);
// A middle stop is left to the browser.
e = tab(whySummary);
assert.equal(e.prevented, false); assert.equal(doc.activeElement, whySummary);
// Focus that escaped the dialog is pulled back to the near end.
e = tab(outside);
assert.equal(e.prevented, true); assert.equal(doc.activeElement, close);
e = tab(outside, true);
assert.equal(e.prevented, true); assert.equal(doc.activeElement, legacySummary);
// Opened: the nested method summary becomes last.
legacy.open = true;
e = tab(methodSummary);
assert.equal(e.prevented, true); assert.equal(doc.activeElement, close);
// No open dialog: Tab is never intercepted.
riskOpen = false;
e = tab(outside);
assert.equal(e.prevented, false); assert.equal(doc.activeElement, outside);
""", src)


def test_china_dialog_rechecks_expiry_and_cancels_a_pending_close_on_open():
    page = (ROOT / "templates" / "china.html.j2").read_text()
    opener = _between_text(page, "function cnxOpenDlg(id){", "function cnxCloseDlg(){")
    assert "if(id==='cnx-dlg-risk'&&window.mmPbExpire)window.mmPbExpire();" in opener
    assert "if(d._cnxCancelClose)d._cnxCancelClose();" in opener
    closer = _between_text(page, "function cnxCloseDlg(){", "function cnxTogglePop(")
    assert "if(el._cnxCancelClose)el._cnxCancelClose();" in closer
    assert "el._cnxCancelClose=stop;" in closer and "clearTimeout(timer)" in closer


def _between_text(page: str, start: str, end: str) -> str:
    a = page.index(start)
    return page[a:page.index(end, a)]
