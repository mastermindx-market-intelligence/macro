"""T18 — Sector Central measured-read journey panel (`#si-measured`, LR-T18-M1).

The page's own JS is executed under node rather than mirrored in Python (the same
mirrored-guard-is-vacuous trap GR1 pins): every assertion below runs the REGION that
ships, extracted between `/* mr-panel:start */` and `/* mr-panel:end */` and driven
through a stub DOM.

What is pinned:

  * every unknown/failure state is a DIFFERENT visible state (A44): nodata / absent /
    outage / invalid each carry their own class and copy — never an empty box;
  * unknown is never zero: an unmeasured sector speaks a plain reason; no reason code,
    slug, event id, z value, or English-only string leaks into either language;
  * A42: a history failure (script error / timeout / generation mismatch) lands ONLY in
    `#mr-hist` — the ranked list and the selection are byte-for-byte untouched;
  * the map → list → detail → history journey works by mouse, keyboard, deep link,
    Back/Forward, and a langchange re-render preserves selection and mode.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "templates" / "sector_central.html.j2"
FIXTURE = ROOT / "tests" / "fixtures" / "leadership_rotation" / "measured_read_v1.json"

needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")

START = "/* mr-panel:start */"
END = "/* mr-panel:end */"

#: A SECTOR_CYCLES payload whose rs_history generation matches the fixture's
#: `generation.history_as_of` — the shape the cycle-clock overlay embeds.
CYC = {
    "meta": {"rs_history": {"schema": "sector_cycles.rs_history.v1", "as_of": "2026-10-09"}},
    "sectors": [{"ticker": "XLE", "rs_history": [
        {"date": "2026-10-07", "rs_21d": 2.0, "rs_63d": 3.9},
        {"date": "2026-10-08", "rs_21d": 2.2, "rs_63d": 4.0},
        {"date": "2026-10-09", "rs_21d": 2.4, "rs_63d": 4.1},
    ]}],
}

RANKED = ["XLE", "XLY", "XLC", "XLF", "XLV", "XLK", "XLI", "XLB", "XLP"]


def _region(src: str, a: str, b: str) -> str:
    i = src.index(a)
    return src[i:src.index(b, i) + len(b)]


def _panel_js() -> str:
    return _region(PAGE.read_text(encoding="utf-8"), START, END)


def _fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


HARNESS_PRELUDE = r"""
// ── stub DOM (the contract the region may rely on) ─────────────────────────────
var __els = {}, __rows = [], __segbtns = [], __focused = null;
var __timersLog = [], __histLog = [], __docL = {}, __winL = {};
var __matchMediaMobile = false;
function mkEl(id) {
  var el = {
    id: id || '', html: '', hidden: false, attrs: {}, className: '',
    __scrolled: 0, __scrollArgs: null, __l: {},
    setAttribute: function (k, v) { el.attrs[k] = String(v); },
    getAttribute: function (k) {
      return Object.prototype.hasOwnProperty.call(el.attrs, k) ? el.attrs[k] : null;
    },
    addEventListener: function (t, f) { (el.__l[t] = el.__l[t] || []).push(f); },
    focus: function () { __focused = el; },
    scrollIntoView: function (o) { el.__scrolled++; el.__scrollArgs = o; },
    closest: function () { return null; },
    querySelectorAll: function (sel) { return __query(sel); }
  };
  if (id) __els[id] = el;
  // Like a browser, a parent's innerHTML reflects later writes into its
  // children (a revision marker stands in for the serialisation).
  Object.defineProperty(el, 'innerHTML', {
    get: function () { return el.__rev ? el.html + '<!--rev ' + el.__rev + '-->' : el.html; },
    set: function (v) {
      el.html = String(v); el.__rev = 0; __harvest(el);
      for (var p = el.__parent; p; p = p.__parent) p.__rev = (p.__rev || 0) + 1;
    }
  });
  return el;
}
function __query(sel) {
  if (sel === '.mr-row') return __rows.slice();
  if (sel === '.mr-segbtn') return __segbtns.slice();
  return [];
}
// Every innerHTML assignment re-harvests the two button shapes the region renders,
// preserving document order (ranked list, then unmeasured, then the seg buttons).
function __harvest(el) {
  if (el.id === 'mr-body') { __rows = []; __segbtns = []; }
  else if (el.id === 'mr-list') { __rows = []; }
  else if (el.id === 'mr-detail') { __segbtns = []; }
  var re = /<button type="button" class="([^"]*)" (data-g|data-h)="([^"]*)" aria-pressed="([^"]*)">/g, m;
  while ((m = re.exec(el.html))) {
    var b = mkEl('');
    b.className = m[1];
    b.attrs[m[2]] = m[3];
    b.attrs['aria-pressed'] = m[4];
    if (m[1].indexOf('mr-row') >= 0) __rows.push(b);
    if (m[1].indexOf('mr-segbtn') >= 0) __segbtns.push(b);
  }
  // Browser-faithful: an innerHTML write DETACHES every node it replaces and the
  // ids in the new markup resolve to FRESH nodes, so a region that caches a
  // reference across a reset is caught writing into a detached node.
  (el.__owned || []).forEach(__drop);
  el.__owned = [];
  var reid = /id="([^"]+)"/g, im;
  while ((im = reid.exec(el.html))) { mkEl(im[1]).__parent = el; el.__owned.push(im[1]); }
}
function __drop(id) {
  var e = __els[id];
  if (!e) return;
  (e.__owned || []).forEach(__drop);
  delete __els[id];
}
var __docEl = mkEl('html');
var __document = {
  documentElement: __docEl,
  getElementById: function (id) {
    return Object.prototype.hasOwnProperty.call(__els, id) ? __els[id] : null;
  },
  addEventListener: function (t, f) { (__docL[t] = __docL[t] || []).push(f); }
};
var __loc = { pathname: '/sector-central', search: '', hash: '', href: 'https://mm.test/sector-central' };
function __setLoc(search, hash) {
  __loc.search = search; __loc.hash = hash;
  __loc.href = 'https://mm.test' + __loc.pathname + search + hash;
}
var __window = {
  addEventListener: function (t, f, c) { (__winL[t] = __winL[t] || []).push({ fn: f, capture: !!c }); },
  matchMedia: function (q) { return { matches: __matchMediaMobile && q.indexOf('760') >= 0 }; },
  setTimeout: function (fn, ms) { __timersLog.push({ fn: fn, ms: ms }); return __timersLog.length; },
  SECTOR_CENTRAL: null,
  SECTOR_CYCLES: null
};
var __history = {
  pushState: function (s, t, u) { __histLog.push(['push', s, u]); },
  replaceState: function (s, t, u) { __histLog.push(['replace', s, u]); }
};
var document = __document, window = __window, location = __loc, history = __history;
var setTimeout = function (fn, ms) { return __window.setTimeout(fn, ms); };
// ── the panel skeleton, in the shipped markup shape ────────────────────────────
['si-measured', 'mr-sub', 'mr-status', 'mr-body', 'mr-cov', 'mr-list',
 'mr-unmeasured', 'mr-detail', 'mr-early'].forEach(function (id) { mkEl(id); });
__els['mr-body'].innerHTML = '<div class="mr-grid"><div class="rvx-card mr-listbox">' +
  '<div class="mr-cov" id="mr-cov"></div><ol class="mr-list" id="mr-list"></ol>' +
  '<ul class="mr-list mr-unmeasured" id="mr-unmeasured" hidden></ul></div>' +
  '<div class="rvx-card mr-detail" id="mr-detail" aria-live="polite"></div></div>' +
  '<div class="mr-early" id="mr-early"></div>';
// ── scenario wiring — BEFORE the region's init runs ────────────────────────────
var FIX = __FIXTURE__;
var CFG = __CFG__;
var MR = JSON.parse(JSON.stringify(FIX));
if (CFG.mr) { Object.keys(CFG.mr).forEach(function (k) { MR[k] = CFG.mr[k]; }); }
var D0 = null;
if (CFG.central !== 'none' && CFG.central !== 'absent') {
  D0 = { as_of: CFG.as_of || '2026-10-09', measured_read: MR };
} else if (CFG.central === 'absent') {
  D0 = { as_of: CFG.as_of || '2026-10-09' };
}
if (CFG.lang) __docEl.attrs['data-lang'] = CFG.lang;
__setLoc(CFG.search || '', CFG.hash || '');
__window.SECTOR_CENTRAL = D0;
if (CFG.cycles) __window.SECTOR_CYCLES = CFG.cycles;
var CYC = {meta: {rs_history: {schema: 'sector_cycles.rs_history.v1', as_of: '2026-10-09'}},
  sectors: [{ticker: 'XLE', rs_history: [
    {date: '2026-10-07', rs_21d: 2.0, rs_63d: 3.9},
    {date: '2026-10-08', rs_21d: 2.2, rs_63d: 4.0},
    {date: '2026-10-09', rs_21d: 2.4, rs_63d: 4.1}]}]};
// ── driving helpers ─────────────────────────────────────────────────────────────
function html(id) { var e = __document.getElementById(id); return e ? e.html : null; }
function elOf(id) { return __document.getElementById(id); }
function rows() { return __els['si-measured'].querySelectorAll('.mr-row'); }
function rowByG(g) {
  var r = rows(), i;
  for (i = 0; i < r.length; i++) if (r[i].getAttribute('data-g') === g) return r[i];
  return null;
}
function pressedOf() {
  var o = {}, r = rows(), i;
  for (i = 0; i < r.length; i++) o[r[i].getAttribute('data-g')] = r[i].getAttribute('aria-pressed');
  return o;
}
function segState() {
  var b = __els['si-measured'].querySelectorAll('.mr-segbtn'), o = {}, i;
  for (i = 0; i < b.length; i++) o[b[i].getAttribute('data-h')] = b[i].getAttribute('aria-pressed');
  return o;
}
function dispatchDoc(name, evt) {
  var l = __docL[name] || [], i;
  for (i = 0; i < l.length; i++) l[i](evt || {});
}
function dispatchWin(name, evt) {
  var l = __winL[name] || [], i;
  for (i = 0; i < l.length; i++) l[i].fn(evt || {});
}
function dispatchEl(name, evt) {
  var l = __els['si-measured'].__l[name] || [], i;
  for (i = 0; i < l.length; i++) l[i](evt || {});
}
function fireTimers() {
  var l = __timersLog.slice(), i;
  for (i = 0; i < l.length; i++) l[i].fn();
}
function obsClick() {
  dispatchEl('click', {target: {closest: function () {
    return {getAttribute: function (k) { return k === 'data-h' ? 'obs' : null; }};
  }}});
}
function collect() {
  return {body: html('mr-body'), sub: html('mr-sub'), status: html('mr-status'),
          cov: html('mr-cov'), list: html('mr-list'), un: html('mr-unmeasured'),
          unHidden: elOf('mr-unmeasured') ? elOf('mr-unmeasured').hidden : null, detail: html('mr-detail'),
          hist: html('mr-hist'), early: html('mr-early'), rows: rows().map(function (r) {
            return [r.getAttribute('data-g'), r.getAttribute('aria-pressed')];
          }),
          seg: segState(),
          histCalls: __histLog, timers: __timersLog.map(function (t) { return t.ms; }),
          scrolled: __els['si-measured'].__scrolled};
}
function show(o) { process.stdout.write(JSON.stringify(o == null ? collect() : o)); }
"""


def _run(body: str = "show();", fixture: dict | None = None, cfg: dict | None = None) -> dict:
    fx = json.dumps(fixture if fixture is not None else _fixture())
    cf = json.dumps(cfg or {})
    script = HARNESS_PRELUDE + _panel_js() + "\n" + textwrap.dedent(body)
    script = script.replace("__FIXTURE__", fx).replace("__CFG__", cf)
    res = subprocess.run(["node", "-e", script], capture_output=True, text=True, timeout=60)
    assert res.returncode == 0, f"node failed:\nSTDERR:\n{res.stderr}"
    assert res.stdout.strip(), f"no stdout; stderr:\n{res.stderr}"
    return json.loads(res.stdout)


def _all_text(out: dict) -> str:
    return " ".join(str(v) for v in out.values())


def _button(html: str, ticker: str) -> str:
    m = re.search(r'<button type="button" class="mr-row[^"]*" data-g="%s".*?</button>' % ticker, html, re.S)
    assert m, f"no ranked row for {ticker}"
    return m.group(0)


# ══════════════════════════════════════════════════════════════════════════════════
# 1 — A44: every unknown/failure state is distinct
# ══════════════════════════════════════════════════════════════════════════════════

@needs_node
def test_01_a44_states_are_distinct_classes_and_copy():
    nodata = _run(cfg={"central": "none"})
    assert "mx-error" in nodata["body"]
    assert "Data for this page did not load." in nodata["body"]
    assert nodata["sub"] == "" and nodata["status"] == ""
    absent = _run(cfg={"central": "absent"})
    assert "mx-empty" in absent["body"]
    assert "not in today" in absent["body"] and "next nightly build" in absent["body"]
    outage = _run(cfg={"mr": {"status": "unavailable"}})
    assert "mx-error" in outage["body"] and "could not be produced today" in outage["body"]
    states = {"nodata": nodata["body"], "absent": absent["body"], "outage": outage["body"]}
    assert len(set(states.values())) == 3, "a failure state shares another's exact copy"
    for bad_schema in ({"mr": {"schema": "bogus/v9"}}, {"mr": {"groups": "no"}},
                       {"mr": {"status": "weird"}}):
        invalid = _run(cfg=bad_schema)
        assert "mr-invalid" in invalid["body"], bad_schema
        assert "could not be checked" in invalid["body"], bad_schema
    assert invalid["body"] not in states.values()


# ══════════════════════════════════════════════════════════════════════════════════
# 2 — the ranked list
# ══════════════════════════════════════════════════════════════════════════════════

@needs_node
def test_02_ranked_order_and_values():
    out = _run()
    order = [r[0] for r in out["rows"]][: len(RANKED)]
    assert order == RANKED, order
    assert all(r[1] == "false" for r in out["rows"]), "nothing is pre-selected"
    xle = _button(out["list"], "XLE")
    assert "+4.1%" in xle and "+2.4%" in xle, xle
    assert xle.index("+2.4%") < xle.index("+4.1%"), "1 mo column must precede 3 mo"
    assert "Energy" in xle and "mr-sr" in xle


# ══════════════════════════════════════════════════════════════════════════════════
# 3 — unmeasured sectors speak a plain reason, never a number
# ══════════════════════════════════════════════════════════════════════════════════

@needs_node
def test_03_unmeasured_rows_are_plain_words_never_numbers():
    out = _run()
    assert out["unHidden"] is False
    assert "not measured — no price data for this sector today" in out["un"]
    assert "not measured — not enough price history yet" in out["un"]
    assert "Real Estate" in out["un"] and "Utilities" in out["un"]
    for li in re.findall(r"<li>.*?</li>", out["un"], re.S):
        assert "%" not in li, li
        assert "0.0" not in li, li
        assert not re.search(r"\d", li), li


# ══════════════════════════════════════════════════════════════════════════════════
# 4 — no slug, reason code, id, event_type or z value leaks into either language
# ══════════════════════════════════════════════════════════════════════════════════

def _leak_scenarios() -> list[tuple[str, dict, str]]:
    obs_body = """
        __window.SECTOR_CYCLES = CYC;
        dispatchDoc('sc:cycles-data');
        obsClick();
        show();
    """
    return [
        ("nodata", {"central": "none"}, "show();"),
        ("absent", {"central": "absent"}, "show();"),
        ("outage", {"mr": {"status": "unavailable"}}, "show();"),
        ("invalid", {"mr": {"schema": "x"}}, "show();"),
        ("full-en", {}, "show();"),
        ("full-zh", {"lang": "zh"}, "show();"),
        ("hist-en", {"search": "?g=XLE"}, """
            __window.SECTOR_CYCLES = CYC;
            dispatchDoc('sc:cycles-data');
            show();
        """),
        ("obs-en", {"search": "?g=XLK"}, obs_body),
        ("obs-zh", {"search": "?g=XLK", "lang": "zh"}, obs_body),
        ("gen-mismatch", {"search": "?g=XLE",
                          "cycles": {"meta": {"rs_history": {"as_of": "2026-10-08"}},
                                     "sectors": []}}, "show();"),
        ("unmeasured-detail", {"search": "?g=XLRE"}, "show();"),
        ("early-unavailable", {"mr": {"early_context": {"status": "unavailable"}}}, "show();"),
    ]


@needs_node
def test_04_no_slug_reason_code_id_or_z_value_in_any_state_or_language():
    banned = ["missing_input", "thin_history", "ai_semis", "xlk-xle:handoff", "cross_handoff",
              '"z"', "watch", "partial_coverage", "research_estimate", "no_admitted_model",
              "event_type", "from_key", "to_key"]
    fixture = _fixture()
    banned += [str(g["current"]["z"]) for g in fixture["groups"] if g["current"].get("z") is not None]
    blobs = []
    for name, cfg, body in _leak_scenarios():
        out = _run(body=body, cfg=cfg)
        text = _all_text(out)
        assert text.strip(), f"{name} produced nothing"
        blobs.append((name, text))
    for name, text in blobs:
        low = text.lower()
        for bad in banned:
            assert bad.lower() not in low, f"{name}: banned {bad!r} in output"


# ══════════════════════════════════════════════════════════════════════════════════
# 5 — coverage strip
# ══════════════════════════════════════════════════════════════════════════════════

@needs_node
def test_05_coverage_copy_names_n_k_and_the_bounds():
    cov = _run()["cov"]
    assert "Measured 9 of 11" in cov, cov
    assert "5 of 9 measured sectors" in cov and "over 3 months" in cov, cov
    assert "Counting the 2 unmeasured: between 5 and 7 of 11" in cov, cov
    assert "not a confidence interval" in cov, cov


# ══════════════════════════════════════════════════════════════════════════════════
# 6 — status chips
# ══════════════════════════════════════════════════════════════════════════════════

@needs_node
def test_06_partial_and_stale_chips():
    out = _run()
    assert "mr-chip-partial" in out["status"]
    assert "Partial — 9 of 11 measured" in out["status"], out["status"]
    assert "mr-chip-stale" not in out["status"], "equal dates must not read stale"
    stale = _run(cfg={"as_of": "2026-10-10"})
    assert "mr-chip-stale" in stale["status"]
    assert "Older than this page — measured 2026-10-09, page data 2026-10-10" in stale["status"]
    assert "mr-chip-partial" in stale["status"], "partial and stale can co-exist"


# ══════════════════════════════════════════════════════════════════════════════════
# 7 — deep link
# ══════════════════════════════════════════════════════════════════════════════════

@needs_node
def test_07_deep_link_selects_restores_hash_and_ignores_unknown():
    out = _run(cfg={"search": "?g=XLE", "hash": ""})
    assert ["replace", None, "/sector-central?g=XLE#map"] in out["histCalls"], out["histCalls"]
    assert "Energy" in out["detail"] and "+4.1%" in out["detail"]
    assert "1 month vs" in out["detail"] and "Measured order" in out["detail"]
    assert "1 of 9 measured" in out["detail"]
    assert out["hist"] is not None and "mr-skel-spark" in out["hist"], "history arms in wait state"
    nope = _run(cfg={"search": "?g=NOPE"})
    assert "Pick a sector" in nope["detail"], nope["detail"]
    assert "mr-dh" not in nope["detail"]
    assert all(r[1] == "false" for r in nope["rows"])
    assert nope["histCalls"] == [], "an unknown g must not rewrite the URL"
    prehashed = _run(cfg={"search": "?g=XLE", "hash": "#map"})
    assert prehashed["histCalls"] == [], "hash already present — no rewrite"


# ══════════════════════════════════════════════════════════════════════════════════
# 8 — history states
# ══════════════════════════════════════════════════════════════════════════════════

@needs_node
def test_08_history_wait_ready_mismatch_and_unpublished():
    wait = _run(cfg={"search": "?g=XLE"})
    assert "mr-skel-spark" in wait["hist"] and "Loading history" in wait["hist"]
    ready = _run("""
        __window.SECTOR_CYCLES = CYC;
        dispatchDoc('sc:cycles-data');
        show();
    """, cfg={"search": "?g=XLE"})
    assert '<polyline class="mr-spark-line" points="0.0,6.7 150.0,5.4 300.0,4.0"' in ready["hist"], ready["hist"]
    assert 'y1="60.0"' in ready["hist"] and "mr-spark-zero" in ready["hist"]
    assert "2026-10-07 → 2026-10-09 · 3 points" in ready["hist"]
    assert "Reconstructed from prices" in ready["hist"]
    mismatch = _run(cfg={"search": "?g=XLE",
                         "cycles": {"meta": {"rs_history": {"as_of": "2026-10-08"}}, "sectors": []}})
    assert "mr-gen" in mismatch["hist"], mismatch["hist"]
    assert "2026-10-08" in mismatch["hist"] and "2026-10-09" in mismatch["hist"]
    assert "polyline" not in mismatch["hist"], "never draw from the other generation"
    unpublished = _run(cfg={"search": "?g=XLE", "cycles": {"meta": {}, "sectors": []}})
    assert "not published yet" in unpublished["hist"]
    short = _run(cfg={"search": "?g=XLE",
                      "cycles": {"meta": {"rs_history": {"as_of": "2026-10-09"}},
                                 "sectors": [{"ticker": "XLE",
                                              "rs_history": [{"date": "2026-10-09", "rs_21d": 2.4,
                                                                              "rs_63d": 4.1}]}]}})
    assert "Not enough history points to draw." in short["hist"]


# ══════════════════════════════════════════════════════════════════════════════════
# 9 — A42: a history failure is confined to #mr-hist
# ══════════════════════════════════════════════════════════════════════════════════

@needs_node
def test_09_a42_history_script_error_confined_to_hist_box():
    out = _run("""
        __window.SECTOR_CYCLES = CYC;
        dispatchDoc('sc:cycles-data');
        var beforeList = html('mr-list');
        var beforeHist = html('mr-hist');
        dispatchWin('error', {target: {tagName: 'SCRIPT', src: 'sector_cycles_data.js?v=x'}});
        var afterErr = {hist: html('mr-hist'), listIdentical: beforeList === html('mr-list'),
                        pressed: pressedOf()};
        dispatchEl('click', {target: {closest: function () { return rowByG('XLY'); }}});
        show({
            beforeHist: beforeHist,
            afterErr: afterErr,
            histAfterSwitch: html('mr-hist'),
            listStillIdentical: beforeList === html('mr-list'),
            pressedAfterSwitch: pressedOf(),
            detailAfterSwitch: html('mr-detail')
        });
    """, cfg={"search": "?g=XLE"})
    assert "polyline" in out["beforeHist"], "the ready history should have drawn first"
    assert "mx-error" in out["afterErr"]["hist"], out["afterErr"]["hist"]
    assert "History unavailable right now" in out["afterErr"]["hist"]
    assert out["afterErr"]["listIdentical"] is True, "the ranked list was re-rendered"
    assert out["afterErr"]["pressed"]["XLE"] == "true", "selection lost on history failure"
    assert out["listStillIdentical"] is True
    assert "mx-error" in out["histAfterSwitch"], "stale other-group spark after switching"
    assert "polyline" not in out["histAfterSwitch"]
    assert "Consumer Discretionary" in out["detailAfterSwitch"]
    assert out["pressedAfterSwitch"]["XLY"] == "true"
    assert out["pressedAfterSwitch"]["XLE"] == "false"


# ══════════════════════════════════════════════════════════════════════════════════
# 10 — the 20s timeout backstop
# ══════════════════════════════════════════════════════════════════════════════════

@needs_node
def test_10_timeout_backstop_arms_once_then_fails():
    out = _run("""
        dispatchDoc('si:view', {detail: 'map'});
        var t1 = __timersLog.map(function (t) { return t.ms; });
        dispatchDoc('si:view', {detail: 'map'});
        var t2 = __timersLog.map(function (t) { return t.ms; });
        var scrolled = __els['si-measured'].__scrolled;
        fireTimers();
        show({t1: t1, t2: t2, scrolled: scrolled, timers: __timersLog.length,
              hist: html('mr-hist')});
    """, cfg={"search": "?g=XLE"})
    assert out["t1"] == [20000], out["t1"]
    assert out["t2"] == [20000], "a second si:view must not arm a second timer"
    assert out["timers"] == 1
    assert out["scrolled"] == 1, "the deep-linked view scrolls once"
    assert "mx-error" in out["hist"], out["hist"]
    assert "History unavailable right now" in out["hist"]
    prehashed = _run(cfg={"search": "?g=XLE", "hash": "#map"})
    assert prehashed["timers"] == [20000], "init arms the backstop when already on #map"


# ══════════════════════════════════════════════════════════════════════════════════
# 11 — recorded-at-the-time (obs) history
# ══════════════════════════════════════════════════════════════════════════════════

@needs_node
def test_11_obs_history_for_xlk_and_its_failure_states():
    out = _run("""
        __window.SECTOR_CYCLES = CYC;
        dispatchDoc('sc:cycles-data');
        obsClick();
        show();
    """, cfg={"search": "?g=XLK"})
    h = out["hist"]
    assert "1 recorded event filed under this sector" in h, h
    assert "2026-09-21" in h and "day 14" in h and 'href="#moving"' in h
    assert "Earliest start" in h and "Longest running" in h and "Recorded as of" in h
    assert "2026-10-09" in h
    assert out["seg"]["obs"] == "true", out["seg"]
    assert out["seg"]["recon"] == "false", out["seg"]
    variants = {
        "unavailable": ({"confirmed_events": {"status": "unavailable"}},
                        "mx-error", "Recorded events are unavailable right now"),
        "none": ({"confirmed_events": {"status": "none"}},
                 "mx-empty", "No recorded events are open."),
        "gen": ({"confirmed_events": {"status": "incompatible_generation", "as_of": "2026-10-01"}},
                "mr-gen", "2026-10-01"),
        "truncated": ({"confirmed_events": {"status": "available", "as_of": "2026-10-09",
                                            "truncated": True,
                                            "rows": [{"sector": "Utilities", "started": "2026-10-01",
                                                      "day_n": 2}]}},
                      "mx-empty", "Not among the 12 most recent recorded events shown here."),
        "no-match": ({"confirmed_events": {"status": "available", "as_of": "2026-10-09",
                                           "truncated": False, "rows": []}},
                     "mx-empty", "No recorded events for this sector."),
    }
    seen = set()
    for name, (patch, cls, copy) in variants.items():
        v = _run("""
            obsClick();
            show();
        """, cfg={"search": "?g=XLK", "mr": patch})
        h = v["hist"]
        assert cls in h, (name, h)
        assert copy in h, (name, h)
        if name == "gen":
            assert "2026-10-09" in h, "the mismatch box must carry both dates"
        seen.add((cls, copy))
    assert len(seen) == len(variants), "two obs failure states are indistinguishable"


# ══════════════════════════════════════════════════════════════════════════════════
# 12 — the early box
# ══════════════════════════════════════════════════════════════════════════════════

@needs_node
def test_12_early_box_watch_muted_broadening_clause_no_forecast():
    out = _run()
    e = out["early"]
    assert "No early reading to show today." in e, e
    assert "mr-early-clause" not in out["early"], "state 'watch' must not render a clause"
    assert "Early observation — context only" in e and "2026-10-09" in e
    assert "Based on 2 of 2 checks" in e and "partial coverage" in e
    assert "Forecast: none" in e
    broad = _run(cfg={"mr": {"early_context": {
        "status": "available", "as_of": "2026-10-09", "state": "BROADENING",
        "coverage": {"evaluable_2s": 4, "registered_pairs": 5}, "reason_codes": []}}})
    assert "More sectors are starting to keep up" in broad["early"], broad["early"]
    assert "Based on 4 of 5 checks" in broad["early"]
    assert "partial coverage" not in broad["early"]
    admitted = _run(cfg={"mr": {"research_estimate": {
        "status": "estimate", "probability": 0.5, "horizon_sessions": 21}}})
    assert "Forecast: none" not in admitted["early"], admitted["early"]
    assert "Research estimate" in admitted["early"], admitted["early"]


# ══════════════════════════════════════════════════════════════════════════════════
# 13 — ZH rendering
# ══════════════════════════════════════════════════════════════════════════════════

@needs_node
def test_13_zh_mode_renders_chinese_fact_language_only():
    out = _run(cfg={"lang": "zh", "search": "?g=XLE", "cycles": CYC})
    d = out["detail"]
    assert "能源" in d and "XLE" in d
    assert "1个月 相对标普500" in d and "3个月 相对标普500" in d
    assert "实测排序" in d and "第 1 / 共 9 个已测" in d
    assert "证据日期" in d and "2026-10-09" in d
    for en in ("1 month vs", "3 months vs", "Measured order", "Evidence date", "Energy"):
        assert en not in d, f"EN fact label leaked into ZH: {en}"
    assert "已测 9 / 11" in out["cov"], out["cov"]
    assert "部分 — 9 / 11 已测" in out["status"], out["status"]
    assert "未测 — 今日缺少该板块价格数据" in out["un"]
    assert "未测 — 价格历史不足" in out["un"]
    assert "按价格重建" in out["hist"] and "个点" in out["hist"]
    assert "预测：无" in out["early"]
    assert "证据日期 2026-10-09 · 11 个美国板块" in out["sub"]


# ══════════════════════════════════════════════════════════════════════════════════
# 14 — Back/Forward and keyboard
# ══════════════════════════════════════════════════════════════════════════════════

@needs_node
def test_14_popstate_restores_escape_clears_arrows_move():
    out = _run("""
        __setLoc('?g=XLY', '');
        dispatchWin('popstate');
        var afterPop = {pressed: pressedOf(), detail: html('mr-detail')};
        dispatchEl('keydown', {key: 'ArrowDown', target: rows()[0], preventDefault: function () {}});
        var afterDown = __focused && __focused.getAttribute('data-g');
        dispatchEl('keydown', {key: 'ArrowUp', target: __focused, preventDefault: function () {}});
        var afterUp = __focused && __focused.getAttribute('data-g');
        dispatchEl('keydown', {key: 'Escape', target: rows()[1], preventDefault: function () {}});
        show({afterPop: afterPop, afterDown: afterDown, afterUp: afterUp,
              pressedAfterEsc: pressedOf(), histCalls: __histLog,
              focusedAfterEsc: __focused ? __focused.getAttribute('data-g') : null,
              detailAfterEsc: html('mr-detail')});
    """)
    assert out["afterPop"]["pressed"]["XLY"] == "true", out["afterPop"]
    assert "Consumer Discretionary" in out["afterPop"]["detail"]
    assert out["afterDown"] == "XLY", "ArrowDown must move to the next row"
    assert out["afterUp"] == "XLE", "ArrowUp must move back"
    assert all(v == "false" for v in out["pressedAfterEsc"].values()), out["pressedAfterEsc"]
    assert "Pick a sector" in out["detailAfterEsc"]
    assert out["focusedAfterEsc"] == "XLY", "focus must return to the cleared row"
    replaces = [c for c in out["histCalls"] if c[0] == "replace"]
    assert replaces and "g=" not in replaces[-1][2], replaces


# ══════════════════════════════════════════════════════════════════════════════════
# 15 — static placement + hygiene (no node)
# ══════════════════════════════════════════════════════════════════════════════════

def test_15_static_placement_and_hygiene():
    src = PAGE.read_text(encoding="utf-8")
    map_start = src.index('<section class="si-view" data-view="map">')
    moving_start = src.index('<section class="si-view" data-view="moving">')
    si_map = src.index('id="si-map"')
    measured = src.index('id="si-measured"')
    cyclemap = src.index('id="sc-cyclemap"')
    assert map_start < si_map < measured < cyclemap < moving_start
    assert src.count(START) == 1 and src.count(END) == 1
    js = _panel_js()
    for bad in ("title=", "style.textContent", "insertRule", "cssText",
                "createElement('style'", 'createElement("style"'):
        assert bad not in js, bad
    assert src.index(START) < src.index('<script src="si_workspace.js">'), \
        "the panel must run before the workspace router"


def test_16_panel_script_is_closed_and_the_router_still_parses():
    """LR-T18-EV1R finding (2026-10-14): the mr-panel ``<script>`` was opened
    and never closed, so an HTML parser swallowed ``<script src="si_workspace.js">``
    as script text. In a browser that is a SyntaxError at parse: the panel never
    runs and the workspace router is never fetched. The node harness above
    extracts the IIFE between the markers, so only a parser-level check sees it.
    """
    from html.parser import HTMLParser

    src = PAGE.read_text(encoding="utf-8")
    end = src.index(END)
    nxt = src.index("<script", end)
    assert "</script>" in src[end:nxt], \
        "the mr-panel <script> must close before the next <script>"

    seen: list = []

    class _P(HTMLParser):
        def handle_starttag(self, tag, attrs):
            if tag == "script":
                seen.append(dict(attrs).get("src"))

    _P(convert_charrefs=True).feed(src)
    assert "si_workspace.js" in seen, \
        "si_workspace.js must parse as a <script> element, not as script text"


# ══════════════════════════════════════════════════════════════════════════════════
# 17 — a runtime language switch re-renders into LIVE nodes (LR-T18-EV1R finding)
# ══════════════════════════════════════════════════════════════════════════════════

@needs_node
def test_17_langchange_rerender_keeps_the_list_and_selection_visible():
    """EV1R found the list blank after a runtime EN→ZH switch: render() reset
    #mr-body to the skeleton and kept writing into the detached nodes. The
    harness now detaches replaced nodes like a browser does, so a stale cached
    reference shows up here as an empty live list."""
    out = _run(body="""
        __docEl.attrs['data-lang'] = 'zh';
        dispatchDoc('langchange');
        show();
    """, cfg={"search": "?g=XLE", "cycles": CYC})
    assert [g for g, _ in out["rows"]][:9] == RANKED, out["rows"]
    assert dict(out["rows"])["XLE"] == "true"
    assert "能源" in out["list"] and "Energy" not in out["list"]
    assert "能源" in out["detail"] and "XLE" in out["detail"]
    assert "未测 — 今日缺少该板块价格数据" in out["un"]
    assert out["unHidden"] is False
    assert "已测 9 / 11" in out["cov"], out["cov"]
    assert "预测：无" in out["early"]
    assert "按价格重建" in out["hist"]


@needs_node
def test_17b_a_state_view_then_valid_data_restores_a_live_grid():
    out = _run(body="""
        __window.SECTOR_CENTRAL = {as_of: '2026-10-09', measured_read: MR};
        dispatchDoc('langchange');
        show();
    """, cfg={"central": "absent", "cycles": CYC})
    assert [g for g, _ in out["rows"]][:9] == RANKED, out["rows"]
    assert "Energy" in out["list"]
    assert "mx-empty" not in out["body"]


# ══════════════════════════════════════════════════════════════════════════════════
# 18 — 390 px: 44 px touch targets and the unmeasured rows stay legible
# ══════════════════════════════════════════════════════════════════════════════════

def test_18_mobile_touch_targets_and_unmeasured_rows_stack():
    src = PAGE.read_text(encoding="utf-8")
    i = src.index("@media (max-width:760px){ .mr-grid")
    block = src[i:src.index("}\n", src.index(".mr-row-na .mr-why", i)) + 1]
    m = re.search(r"([^{}]*)\{min-height:44px\}", block)
    assert m, block
    targets = {t.strip() for t in m.group(1).split(",")}
    assert {".mr-row", ".mr-segbtn", ".mr-link"} <= targets, targets
    assert ".mr-row-na{grid-template-columns:minmax(0,1fr);" in block, block
    assert ".mr-name{white-space:normal}" in block, block


# ══════════════════════════════════════════════════════════════════════════════════
# LR-FIX-B1 — R1 ZH failure copy
# ══════════════════════════════════════════════════════════════════════════════════

#: 12 named failure/unknown states and their (en, zh) copy. Each must render
#: Chinese in ZH and never carry an ASCII word of 4+ letters from its EN twin.
ZH_FAILURE_STATES = [
    ("no_data", {"central": "none"}, "show();",
     "Data for this page did not load.", "页面数据未能加载"),
    ("absent", {"central": "absent"}, "show();",
     "not in today", "今日数据尚未包含"),
    ("unavailable", {"mr": {"status": "unavailable"}}, "show();",
     "could not be produced today", "今日无法生成此项读数"),
    ("cycles_failed", {"search": "?g=XLE", "cycles": CYC}, """
        __window.SECTOR_CYCLES = CYC;
        dispatchDoc('sc:cycles-data');
        dispatchWin('error', {target: {tagName: 'SCRIPT',
                                       src: 'sector_cycles_data.js?v=x'}});
        show();
    """,
     "History unavailable right now", "历史暂不可用"),
    ("history_unpublished", {"search": "?g=XLE",
                             "cycles": {"meta": {}, "sectors": []}}, "show();",
     "not published yet", "尚未发布"),
    ("too_few_points", {"search": "?g=XLE",
                        "cycles": {"meta": {"rs_history": {"as_of": "2026-10-09"}},
                                   "sectors": [{"ticker": "XLE",
                                                "rs_history": [{"date": "2026-10-09",
                                                                 "rs_21d": 2.4,
                                                                 "rs_63d": 4.1}]}]}}, "show();",
     "Not enough history points", "历史数据点不足"),
    ("obs_unavailable", {"search": "?g=XLK", "mr": {"confirmed_events": {"status": "unavailable"}}}, """
        obsClick();
        show();
    """,
     "Recorded events are unavailable right now", "已记录事件暂不可用"),
    ("obs_none", {"search": "?g=XLK", "mr": {"confirmed_events": {"status": "none"}}}, """
        obsClick();
        show();
    """,
     "No recorded events are open", "目前没有已记录事件"),
    ("obs_not_in_12", {"search": "?g=XLK",
                       "mr": {"confirmed_events": {"status": "available", "as_of": "2026-10-09",
                                                   "truncated": True,
                                                   "rows": [{"sector": "Utilities", "started": "2026-10-01",
                                                             "day_n": 2}]}}}, """
        obsClick();
        show();
    """,
     "Not among the 12 most recent", "最近 12 个"),
    ("obs_none_for_sector", {"search": "?g=XLK",
                             "mr": {"confirmed_events": {"status": "available", "as_of": "2026-10-09",
                                                         "truncated": False, "rows": []}}}, """
        obsClick();
        show();
    """,
     "No recorded events for this sector", "该板块暂无已记录事件"),
    ("early_unavailable", {"mr": {"early_context": {"status": "unavailable"}}}, "show();",
     "Early observation unavailable today", "早期观察暂不可用"),
]


@needs_node
@pytest.mark.parametrize("name,cfg,body,en_twin,zh_twin", ZH_FAILURE_STATES,
                         ids=[s[0] for s in ZH_FAILURE_STATES])
def test_18_zh_failure_states_render_chinese(name, cfg, body, en_twin, zh_twin):
    """R1: every bare-English string passed to mxError/mxEmpty in the panel IIFE
    must render Chinese in ZH and contain no ASCII word of 4+ letters from its
    EN twin. # MUTATION: panel still emits English mxError/mxEmpty on every
    failure state -> ZH fixture shows ASCII strings -> assertion fails."""
    out = _run(body=body, cfg=dict(cfg, lang="zh"))
    # Only check rendered text fields (not URL/histCalls logs)
    blob = " ".join(str(out.get(k, "")) for k in
                    ("body", "sub", "status", "cov", "list", "un",
                     "detail", "hist", "early"))
    assert zh_twin in blob, f"{name}: expected Chinese copy {zh_twin!r} in {blob!r}"
    for en in re.findall(r"[A-Za-z]{4,}", en_twin):
        assert en not in blob, \
            f"{name}: ASCII word {en!r} from EN twin leaked into ZH render: {blob!r}"


# ══════════════════════════════════════════════════════════════════════════════════
# LR-FIX-B1 — R2 null/hostile group guard
# ══════════════════════════════════════════════════════════════════════════════════

HOSTILE_GROUPS = [
    ("null_item", [None]),
    ("number_item", [42]),
    ("numeric_id", [{"group_id": 7}]),
    ("empty_object", [{}]),
]

HOSTILE_PARAMS = [
    pytest.param(groups, search, lang, id=f"{name}-{lang}{'-link' if search else ''}")
    for name, groups in HOSTILE_GROUPS
    for search in ("", "?g=XLK")
    for lang in ("en", "zh")
]


@needs_node
@pytest.mark.parametrize("groups,search,lang", HOSTILE_PARAMS)
def test_19_null_and_hostile_groups_fail_to_named_invalid_state(groups, search, lang):
    """R2: render()'s validation gate requires every element of M2.groups to
    satisfy g && typeof g === 'object' && typeof g.group_id === 'string';
    otherwise the existing mr-invalid state. The init deep-link loop dereferences
    groups[gi].group_id only after a guard, so groups=[null] never throws at
    IIFE init. # MUTATION: validation gate dereferences g.group_id unguarded ->
    node throws "Cannot read property 'group_id' of null" before render()."""
    out = _run(cfg={"mr": {"groups": groups}, "lang": lang, "search": search})
    assert "mr-invalid" in out["body"], \
        f"groups={groups} search={search!r} lang={lang} expected mr-invalid, got {out['body']!r}"
    if lang == "zh":
        assert "无法校验" in out["body"] or "不显示" in out["body"], out["body"]


# ══════════════════════════════════════════════════════════════════════════════════
# LR-FIX-B1 — N-RE1 admitted estimate branch
# ══════════════════════════════════════════════════════════════════════════════════

@needs_node
def test_20_admitted_estimate_renders_display_only_line():
    """N-RE1: re_ with status='estimate' + valid probability/horizon renders the
    'Research estimate — display only' line; every other shape falls through to
    the unchanged 'Forecast: none — …' line. The measured read (list, cov,
    status, sub, rows, un, detail) is byte-identical to the no-estimate render.
    # MUTATION: panel gates on status==='available' (a word the producer never
    emits) -> admitted estimate falls through to 'Forecast: none' -> assertion
    fails on 'Research estimate' substring."""
    no_est = _run()
    en_est = _run(cfg={"mr": {"research_estimate": {
        "status": "estimate", "probability": 0.62, "horizon_sessions": 21}}})
    assert "Research estimate — display only: 62% over the next 21 sessions" in en_est["early"], \
        en_est["early"]
    assert "Forecast: none" not in en_est["early"], en_est["early"]
    zh_est = _run(cfg={"mr": {"research_estimate": {
        "status": "estimate", "probability": 0.62, "horizon_sessions": 21}},
                       "lang": "zh"})
    assert "62%" in zh_est["early"], zh_est["early"]
    assert "21 个交易日" in zh_est["early"], zh_est["early"]
    assert "Forecast: none" not in zh_est["early"], zh_est["early"]
    # The measured read is byte-identical: the estimate touches early only.
    for key in ("list", "cov", "status", "sub", "rows", "un", "detail"):
        assert no_est[key] == en_est[key], (key, no_est[key], en_est[key])
    # Negative cases fall through to the unchanged "Forecast: none" line.
    bad_cases = [
        {"status": "available"},
        {"status": "estimate", "probability": 1.5, "horizon_sessions": 21},
        {"status": "estimate", "probability": "0.6", "horizon_sessions": 21},
        {"status": "estimate", "probability": 0.5, "horizon_sessions": 0},
        {"status": "estimate", "probability": 0.5, "horizon_sessions": 2.5},
        {},
    ]
    for bad in bad_cases:
        out = _run(cfg={"mr": {"research_estimate": bad}})
        assert "Forecast: none" in out["early"], (bad, out["early"])
        assert "Research estimate" not in out["early"], (bad, out["early"])


# ══════════════════════════════════════════════════════════════════════════════════
# LR-FIX-B1 — basis "unknown" is not called "price only"
# ══════════════════════════════════════════════════════════════════════════════════

@needs_node
def test_21_basis_unknown_is_not_called_price_only():
    """basis(b) must distinguish price_only from any other shape (e.g. 'unknown'):
    price_only → 'price only' / '仅价格'; anything else → 'basis not stated' /
    '未注明价格口径'. # MUTATION: basis(b) returns 'price only' for any non-
    total_return value -> 'unknown' is mislabelled as 'price only' -> assertion
    on 'basis not stated' fails."""
    out = _run(cfg={"mr": {"generation": {"price_basis": "unknown"}}})
    assert "basis not stated" in out["sub"], out["sub"]
    zh = _run(cfg={"mr": {"generation": {"price_basis": "unknown"}}, "lang": "zh"})
    assert "未注明价格口径" in zh["sub"], zh["sub"]
    po = _run(cfg={"mr": {"generation": {"price_basis": "price_only"}}})
    assert "price only" in po["sub"], po["sub"]
    assert "basis not stated" not in po["sub"], po["sub"]


# ══════════════════════════════════════════════════════════════════════════════════
# LR-FIX-B1 — series hydration guard
# ══════════════════════════════════════════════════════════════════════════════════

@needs_node
def test_22_series_hydration_wait_then_ready_and_failed():
    """B4: a cycles core whose XLK record lacks rs_history, with
    window.SC_SERIES_DATA set, must show a loading skeleton (not 'Not enough
    history points') until either (a) the series lands via SECTOR_CYCLES_SERIES
    merged in + sc:cycles-data, (b) a script error fires for the series URL, or
    (c) the 20 s backstop expires. The existing CYCLES_STATE failed/ready path
    stays unchanged when rs_history is present on the record.
    # MUTATION: reconHtml hits the 'Not enough history points' path the moment
    rec.rs_history is missing (no series hydration guard) -> loading skeleton
    assertion fails; second mutation: no capture-phase listener matches
    sector_cycles_series_data.js -> 'History unavailable right now' assertion
    fails after a script error for that URL."""
    # (a) wait state: the cycles core carries no rs_history, SC_SERIES_DATA is
    # a string, and SECTOR_CYCLES_SERIES is undefined. renderHist should show
    # the loading skeleton, NOT the "Not enough history points" message.
    out = _run(body="""
        var core = {meta: {rs_history: {as_of: '2026-10-09'}},
                    sectors: [{ticker: 'XLE', rs_history: [
                      {date: '2026-10-07', rs_21d: 2.0, rs_63d: 3.9},
                      {date: '2026-10-08', rs_21d: 2.2, rs_63d: 4.0},
                      {date: '2026-10-09', rs_21d: 2.4, rs_63d: 4.1}]}]};
        __window.SC_SERIES_DATA = 'sector_cycles_series_data.js';
        // the split core carries an XLK record WITHOUT rs_history (the heavy
        // arrays live in the series file), and the core has landed: the wait
        // must come from the series guard, not from the CYCLES_STATE wait.
        core.sectors.push({ticker: 'XLK'});
        __window.SECTOR_CYCLES = core;
        dispatchDoc('sc:cycles-data');
        show();
    """, cfg={"search": "?g=XLK", "mr": {"groups": [
        g for g in _fixture()["groups"] if g["group_id"] != "XLK"
    ] + [{"group_id": "XLK", "name_en": "Technology", "name_zh": "科技",
          "current": {"status": "measured", "rs_21d": 3.5, "rs_63d": 5.0, "rank": 1,
                      "reason": None, "metric": "relative_wealth_pct", "units": "pct",
                      "z": 0.0}}]}})
    assert "mr-skel-spark" in out["hist"], out["hist"]
    assert "Not enough history points" not in out["hist"], out["hist"]
    # (b) ready: after the series lands and sc:cycles-data dispatches, the
    # trail draws. (rs_history appears on the XLK record after the merge.)
    ready = _run(body="""
        var core = {meta: {rs_history: {as_of: '2026-10-09'}},
                    sectors: [{ticker: 'XLE', rs_history: [
                      {date: '2026-10-07', rs_21d: 2.0, rs_63d: 3.9},
                      {date: '2026-10-08', rs_21d: 2.2, rs_63d: 4.0},
                      {date: '2026-10-09', rs_21d: 2.4, rs_63d: 4.1}]}]};
        __window.SC_SERIES_DATA = 'sector_cycles_series_data.js';
        __window.SECTOR_CYCLES = core;
        __window.SECTOR_CYCLES_SERIES = {
          sectors: [{ticker: 'XLK', rs_history: [
            {date: '2026-10-07', rs_21d: 1.0, rs_63d: 2.0},
            {date: '2026-10-08', rs_21d: 1.2, rs_63d: 2.2},
            {date: '2026-10-09', rs_21d: 1.4, rs_63d: 2.4}]}]};
        core.sectors.push({ticker: 'XLK', rs_history:
          __window.SECTOR_CYCLES_SERIES.sectors[0].rs_history});
        dispatchDoc('sc:cycles-data');
        show();
    """, cfg={"search": "?g=XLK", "mr": {"groups": [
        g for g in _fixture()["groups"] if g["group_id"] != "XLK"
    ] + [{"group_id": "XLK", "name_en": "Technology", "name_zh": "科技",
          "current": {"status": "measured", "rs_21d": 3.5, "rs_63d": 5.0, "rank": 1,
                      "reason": None, "metric": "relative_wealth_pct", "units": "pct",
                      "z": 0.0}}]}})
    assert "polyline" in ready["hist"], ready["hist"]
    # (c) failed: a script error for sector_cycles_series_data.js sets the
    # SERIES_STATE to 'failed' and the next renderHist shows the named failure
    # state.
    failed = _run(body="""
        var core = {meta: {rs_history: {as_of: '2026-10-09'}},
                    sectors: [{ticker: 'XLK'}]};
        __window.SC_SERIES_DATA = 'sector_cycles_series_data.js';
        __window.SECTOR_CYCLES = core;
        dispatchDoc('sc:cycles-data');
        dispatchWin('error', {target: {tagName: 'SCRIPT',
                                       src: 'sector_cycles_series_data.js?v=x'}});
        show();
    """, cfg={"search": "?g=XLK", "mr": {"groups": [
        g for g in _fixture()["groups"] if g["group_id"] != "XLK"
    ] + [{"group_id": "XLK", "name_en": "Technology", "name_zh": "科技",
          "current": {"status": "measured", "rs_21d": 3.5, "rs_63d": 5.0, "rank": 1,
                      "reason": None, "metric": "relative_wealth_pct", "units": "pct",
                      "z": 0.0}}]}})
    assert "History unavailable right now" in failed["hist"], failed["hist"]
    # (d) 20s backstop: when the series URL is set but never lands, the backstop
    # fires the failure state.
    backstop = _run(body="""
        var core = {meta: {rs_history: {as_of: '2026-10-09'}},
                    sectors: [{ticker: 'XLK'}]};
        __window.SC_SERIES_DATA = 'sector_cycles_series_data.js';
        __window.SECTOR_CYCLES = core;
        dispatchDoc('sc:cycles-data');
        fireTimers();
        show();
    """, cfg={"search": "?g=XLK", "mr": {"groups": [
        g for g in _fixture()["groups"] if g["group_id"] != "XLK"
    ] + [{"group_id": "XLK", "name_en": "Technology", "name_zh": "科技",
          "current": {"status": "measured", "rs_21d": 3.5, "rs_63d": 5.0, "rank": 1,
                      "reason": None, "metric": "relative_wealth_pct", "units": "pct",
                      "z": 0.0}}]}})
    assert "History unavailable right now" in backstop["hist"], backstop["hist"]
    # (e) the series LANDED but carries no history for this sector: the 20 s
    # backstop must not relabel that as a load failure — the honest state is
    # "Not enough history points" (ORCH-FIX amendment: the backstop latches
    # 'failed' only while SECTOR_CYCLES_SERIES is still undefined).
    landed_empty = _run(body="""
        var core = {meta: {rs_history: {as_of: '2026-10-09'}},
                    sectors: [{ticker: 'XLK'}]};
        __window.SC_SERIES_DATA = 'sector_cycles_series_data.js';
        __window.SECTOR_CYCLES = core;
        dispatchDoc('sc:cycles-data');
        __window.SECTOR_CYCLES_SERIES = {};
        dispatchDoc('sc:cycles-data');
        fireTimers();
        show();
    """, cfg={"search": "?g=XLK", "mr": {"groups": [
        g for g in _fixture()["groups"] if g["group_id"] != "XLK"
    ] + [{"group_id": "XLK", "name_en": "Technology", "name_zh": "科技",
          "current": {"status": "measured", "rs_21d": 3.5, "rs_63d": 5.0, "rank": 1,
                      "reason": None, "metric": "relative_wealth_pct", "units": "pct",
                      "z": 0.0}}]}})
    assert "Not enough history points" in landed_empty["hist"], landed_empty["hist"]
    assert "History unavailable right now" not in landed_empty["hist"], landed_empty["hist"]
    # When rec.rs_history is present (today's monolith), behaviour is byte-
    # identical to base: the loading skeleton never appears for the data path.
    monolith = _run(cfg={"search": "?g=XLE", "cycles": CYC})
    assert "polyline" in monolith["hist"], monolith["hist"]
    assert "mr-skel-spark" not in monolith["hist"], monolith["hist"]
