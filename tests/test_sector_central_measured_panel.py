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
from html.parser import HTMLParser
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
    # The native page loads the shared identity contract before this region.
    handoff = (ROOT / "templates" / "_sector_prophet_context.js.j2").read_text(encoding="utf-8")
    return handoff + "\n" + _region(PAGE.read_text(encoding="utf-8"), START, END)


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
var clearTimeout = function (id) { if(__timersLog[id-1])__timersLog[id-1].cancelled=true; };
// ── the panel skeleton, in the shipped markup shape ────────────────────────────
['si-measured', 'mr-sub', 'mr-status', 'mr-body', 'mr-cov', 'mr-list',
 'mr-unmeasured', 'mr-detail', 'mr-early', 'mr-exact', 'mr-context', 'mr-classification'].forEach(function (id) { mkEl(id); });
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
if (D0 && Object.prototype.hasOwnProperty.call(CFG, 'dated_context')) D0.dated_context=CFG.dated_context;
if (D0 && Object.prototype.hasOwnProperty.call(CFG, 'captured_classification')) D0.captured_classification=CFG.captured_classification;
__setLoc(CFG.search || '', CFG.hash || '');
__window.SECTOR_CENTRAL = D0;
if (CFG.cycles) __window.SECTOR_CYCLES = CFG.cycles;
// The native cases exercise the shipped fetch/stream/epoch path, using the
// actual native projection and wire encoder fixture supplied from Python.
var __nativeCalls=[], __nativePending=[], __sessionReads=0;
if(CFG.native) {
  __els['si-measured'].attrs['data-sector-generation']='native';
  if(CFG.auth_ready!==false) __window.MDXAuth={
    hasSession:function(){return !!CFG.has_session;},
    client:function(){return Promise.resolve({auth:{getSession:function(){__sessionReads++;return Promise.resolve({data:{session:{}}});}}});}
  };
  __window.fetch=function(url,options){
    var index=__nativeCalls.length;
    __nativeCalls.push({url:url,options:options});
    return new Promise(function(resolve,reject){
      __nativePending.push({resolve:resolve,reject:reject});
      var spec=(CFG.native_responses||[])[index];
      if(spec && !spec.defer) nativeRespond(index,spec);
    });
  };
}
function nativeRespond(index,spec) {
  var pending=__nativePending[index];
  if(!pending)throw new Error('request not started: '+index);
  if(spec.reject){pending.reject(new Error(spec.reject));return;}
  var raw=Object.prototype.hasOwnProperty.call(spec,'raw')?spec.raw:JSON.stringify(spec.body);
  if(spec.bytes)raw=new Uint8Array(spec.bytes);
  if(spec.split_utf8) {
    var bytes=new TextEncoder().encode(raw),at=bytes.findIndex(function(b){return b>=128;})+1;
    if(at<1)throw new Error('multibyte fixture missing');
    raw=new ReadableStream({start:function(controller){controller.enqueue(bytes.slice(0,at));controller.enqueue(bytes.slice(at));controller.close();}});
  }
  pending.resolve(new Response(raw,{status:spec.status||200,headers:{'content-type':spec.content_type||'application/json; charset=utf-8'}}));
}
async function drainNative() {
  // Drain Promise and ReadableStream continuations without elapsed-time sleeps.
  for(var i=0;i<4;i++)await new Promise(function(resolve){setImmediate(resolve);});
}
function nativeAuth(event,id) {dispatchWin('mdx-auth',{detail:{event:event,user:id?{id:id}:null}});}
function nativeRetry() {dispatchEl('click',{target:{closest:function(){return {getAttribute:function(k){return k==='data-native-retry'?'true':null;}};}}});}
function nativeCollect() {
  var out=collect();out.nativeState=__els['si-measured'].attrs['data-native-state'];
  out.generation=__els['si-measured'].attrs['data-native-generation'];
  out.content=__els['si-measured'].attrs['data-native-content'];
  out.exact=html('mr-exact');out.contextHidden=elOf('mr-context').hidden;
  out.calls=__nativeCalls.map(function(c){return {url:c.url,credentials:c.options.credentials,cache:c.options.cache,redirect:c.options.redirect,aborted:c.options.signal.aborted};});
  out.sessionReads=__sessionReads;out.legacy=__window.SECTOR_CENTRAL;return out;
}
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
  for (i = 0; i < l.length; i++) if(!l[i].cancelled)l[i].fn();
}
function obsClick() {
  dispatchEl('click', {target: {closest: function () {
    return {getAttribute: function (k) { return k === 'data-h' ? 'obs' : null; }};
  }}});
}
function collect() {
  return {body: html('mr-body'), sub: html('mr-sub'), status: html('mr-status'), context: html('mr-context'),
          classification: html('mr-classification'),
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
    res = subprocess.run(["node"], input=script, capture_output=True, text=True, timeout=60)
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
    # Link destinations are language-independent. Check visible copy, retaining
    # every EN-twin assertion rather than mistaking si_sector in href for prose.
    visible = []
    class CopyParser(HTMLParser):
        def handle_data(self, text):
            visible.append(text)
    parser = CopyParser()
    parser.feed(blob)
    parser.close()
    blob = " ".join(visible)
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


@needs_node
@pytest.mark.parametrize("ticker", RANKED + ["XLU", "XLRE"])
def test_selected_measured_panel_links_its_exact_sector_to_macro_prophet(ticker):
    out = _run(cfg={"search": "?g=" + ticker, "hash": "#map"})
    assert f'href="us_stocks.html?si_sector={ticker}#sector-prophet-context"' in out["detail"]
    assert "Compare in Prophet" in out["detail"]
    assert [row[0] for row in out["rows"]][:len(RANKED)] == RANKED


# ══════════════════════════════════════════════════════════════════════════════════
# 23 — PSL-3 · the dated leadership-evidence addendum
#
# The addendum is the incumbent engine's own optional projection
# (leadership_rotation_context.sector_dossiers/v1), carried on the measured read.
# It is qualified in the page against the CURRENT parent read, so every case
# below drives the REAL panel JS over the REAL engine output — never a
# hand-mirrored dossier.
# ══════════════════════════════════════════════════════════════════════════════════

EV_AS_OF = "2026-10-09"
# The frozen measured read's own numbers, over the native sector registry:
# XLK carries a literal 0.0, XLU is thin_history, XLRE is absent entirely.
EV_H21 = {"XLB": -0.6, "XLC": 1.1, "XLE": 2.4, "XLF": 0.3, "XLI": -0.2,
          "XLK": -0.5, "XLP": -1.0, "XLV": 0.2, "XLY": 1.7}
EV_H63 = {"XLB": -1.4, "XLC": 2.3, "XLE": 4.1, "XLF": 1.2, "XLI": -0.7,
          "XLK": 0.0, "XLP": -2.2, "XLV": 0.9, "XLY": 3.3}


def _ev_cycles(as_of: str = EV_AS_OF, qualified: bool = True, sectors: bool = True) -> dict:
    """A native-shaped sector-cycles payload — the shape engine.sector_cycles
    publishes (meta.asOf, meta.benchmark, rs_history with basis/mode, and one
    series_provenance per record). ``qualified=False`` drops the rs_history
    mode/naturally_observed pair, which is how the engine itself produces an
    all-null addendum."""
    from engine import sector_cycles

    rows = []
    if sectors:
        for ticker, info in sorted(sector_cycles.SECTORS.items()):
            if ticker == "XLRE":
                continue                      # the member the source never carries
            rows.append({
                "id": ticker.lower(), "ticker": ticker, "kind": "sector",
                "name": info["name"], "name_zh": info["name_zh"],
                "group": info["group"], "accent": info["accent"],
                "now": {"rs_21d": EV_H21.get(ticker), "rs_63d": EV_H63.get(ticker),
                        "thin_history": ticker == "XLU"},
                "series_provenance": {
                    "schema": "sector_cycles.series_provenance.v1",
                    "structure_basis": "tr", "rs_basis": "tr",
                    "membership": "single_instrument", "point_in_time": True,
                    "benchmark": "SPY",
                    "history_mode": "reconstructed_price_history"},
            })
    history = {"schema": "sector_cycles.rs_history.v1", "as_of": as_of,
               "basis": "tr", "benchmark": "SPY"}
    if qualified:
        history["mode"] = "reconstructed_price_history"
        history["naturally_observed"] = False
    return {"meta": {"asOf": as_of, "benchmark": "SPY", "rs_history": history},
            "sectors": rows}


def _ev_dossier(qualified: bool = True, sectors: bool = True) -> dict:
    """The engine's own dated addendum over native-shaped inputs."""
    from engine import leadership_rotation_context as lrc

    out = lrc.measured_group_read(_ev_cycles(qualified=qualified, sectors=sectors),
                                  include_sector_dossiers=True)
    return out["sector_dossiers"]


def _ev_legacy_unavailable() -> dict:
    """The engine's own measured read when nothing could be measured: status
    unavailable with all eleven cohort identities still present."""
    from engine import leadership_rotation_context as lrc

    return lrc.measured_group_read(_ev_cycles(sectors=False))


def _copy(obj: dict) -> dict:
    return json.loads(json.dumps(obj))


def _ev_state(section: str) -> tuple[str, str]:
    """The addendum's qualification state and the exact check that failed,
    read from the machine-readable attributes (never from visible copy)."""
    m = re.search(r'data-ev-state="([^"]*)" data-ev-why="([^"]*)"', section or "")
    assert m, section
    return m.group(1), m.group(2)


def _ev_section(detail: str) -> str:
    """The leadership-evidence section of the detail panel, isolated from the
    incumbent legacy facts so a legacy number can never satisfy an evidence
    assertion."""
    m = re.search(r'<section class="mr-ev".*?</section>', detail or "", re.S)
    assert m, f"no leadership-evidence section in {detail!r}"
    return m.group(0)


@needs_node
def test_23_measured_evidence_shows_native_window_values_and_receipts():
    out = _run(cfg={"search": "?g=XLE", "mr": {"sector_dossiers": _ev_dossier()}})
    ev = _ev_section(out["detail"])
    assert "Leadership evidence" in ev
    # header: native date, total-return basis, the selected identity EN/ZH
    assert "2026-10-09" in ev
    assert "total return" in ev
    assert "Energy" in ev and "能源" in ev and "XLE" in ev
    # the plain stance
    assert "Measured profile available; explanatory evidence incomplete." in ev
    # exact native windows — 21 and 63 sessions, never relabelled 1/3 months
    assert "21 trading sessions vs" in ev and "+2.4%" in ev
    assert "63 trading sessions vs" in ev and "+4.1%" in ev
    # cross-sector ETF breadth, with the eleven-sector denominator
    assert "5 of 9 measured (of 11 sectors)" in ev
    assert "Constituent participation is not supplied" in ev
    # the unavailable slots say so, and say what they are not
    assert "5- and 20-session windows are not supplied in the legacy dossier." in ev
    assert "Absolute returns are not supplied in the legacy dossier." in ev
    assert "Explanation unavailable" in ev
    assert "Sector risk context unavailable" in ev and "not a risk verdict" in ev
    # the disclosure and its receipts
    assert "<details class=\"mr-ev-det\">" in ev
    assert "Evidence details" in ev
    assert "engine.sector_cycles" in ev
    assert "2026-10-09|SPY|us_sectors_11" in ev
    assert "immutable_generation_not_supplied" in ev
    assert "owner_freshness_receipt_not_supplied" in ev
    assert "native_revision_selection_not_supplied" in ev
    assert "not_established" in ev and "shared rolling windows" in ev
    assert "not_qualified" in ev
    assert "may_rank=false" in ev and "may_trade=false" in ev and "may_escalate=false" in ev


@needs_node
def test_24_zero_is_preserved_and_never_read_as_missing():
    out = _run(cfg={"search": "?g=XLK", "mr": {"sector_dossiers": _ev_dossier()}})
    ev = _ev_section(out["detail"])
    # XLK's 63-session relative wealth is a literal 0.0 — a measured zero
    assert re.search(r'63 trading sessions vs[^<]*</dt><dd><span class="mr-flat">0\.0%</span>', ev), ev
    assert "n/a" not in ev
    assert "not measured" not in ev


@needs_node
def test_25_unavailable_identity_speaks_its_plain_reason_and_its_exact_code():
    out = _run(cfg={"search": "?g=XLRE", "mr": {"sector_dossiers": _ev_dossier()}})
    ev = _ev_section(out["detail"])
    assert "Measured profile unavailable" in ev
    assert "no data for this sector in the evidence source" in ev
    assert "missing_group" in ev          # the exact native code, in the receipt
    assert "Real Estate" in ev
    # an unavailable identity never shows a number
    assert "%" not in re.sub(r'<span class="mr-ev-code">.*?</span>', '', ev, flags=re.S)


@needs_node
def test_26_all_null_addendum_keeps_the_eleven_identities_selectable():
    """The legacy read is unavailable, the addendum is valid but every value is
    null: the legacy notice stays, all eleven cohort identities stay selectable
    as unavailable rows, and the selected one shows its exact null reason."""
    legacy = _ev_legacy_unavailable()
    out = _run(cfg={"search": "?g=XLE",
                    "mr": {"status": legacy["status"], "groups": legacy["groups"],
                           "sector_dossiers": _ev_dossier(qualified=False)}})
    assert "mx-error" in out["body"], out["body"]
    assert "could not be produced today" in out["body"], out["body"]
    assert len(out["rows"]) == 11, out["rows"]
    assert dict(out["rows"])["XLE"] == "true", out["rows"]
    assert out["un"].count("<li>") == 11, out["un"]
    assert "not measured" in out["un"]
    ev = _ev_section(out["detail"])
    assert _ev_state(ev) == ("ok", ""), ev
    assert "Measured profile unavailable" in ev
    assert "evidence_mode_not_qualified" in ev
    # every identity's exact null reason is exposed, not only the selected one
    for ticker in ("XLB", "XLC", "XLE", "XLF", "XLI", "XLK", "XLP", "XLRE",
                   "XLU", "XLV", "XLY"):
        assert ticker in ev, ticker


@needs_node
def test_27_absent_invalid_and_mismatched_addendum_leave_the_legacy_alone():
    absent = _run(cfg={"search": "?g=XLE"})
    assert "not in today" in _ev_section(absent["detail"])
    assert "+2.4%" in absent["detail"] and "1 month vs" in absent["detail"]
    assert "mr-skel-spark" in absent["hist"], "the legacy history is untouched"

    invalid = _run(cfg={"search": "?g=XLE", "mr": {"sector_dossiers": "not-an-object"}})
    assert "could not be checked" in _ev_section(invalid["detail"])
    assert _ev_state(_ev_section(invalid["detail"])) == ("invalid", "not_an_object")
    assert "+2.4%" in invalid["detail"] and "mr-skel-spark" in invalid["hist"]

    wrong_schema = _run(cfg={"search": "?g=XLE",
                             "mr": {"sector_dossiers": {"schema": "something/else/v9"}}})
    assert "could not be checked" in _ev_section(wrong_schema["detail"])

    stale = _copy(_ev_dossier())
    stale["as_of"] = "2026-10-08"
    generation_mismatch = _run(cfg={"search": "?g=XLE", "mr": {"sector_dossiers": stale}})
    assert "does not match today" in _ev_section(generation_mismatch["detail"])
    assert _ev_state(_ev_section(generation_mismatch["detail"])) == ("mismatch", "session_mismatch")
    assert "+2.4%" in generation_mismatch["detail"]

    renamed = _copy(_ev_dossier())
    renamed["groups"][0]["group_id"] = "ZZZZ"
    identity_mismatch = _run(cfg={"search": "?g=XLE", "mr": {"sector_dossiers": renamed}})
    assert "does not match today" in _ev_section(identity_mismatch["detail"])
    assert _ev_state(_ev_section(identity_mismatch["detail"])) == ("mismatch", "identity_mismatch")

    # a parent generation that lost its own benchmark cannot qualify an addendum
    no_benchmark = _run(cfg={"search": "?g=XLE", "mr": {
        "generation": {"id": "2026-10-09|SPY|us_sectors_11", "cohort_id": "us_sectors_11",
                       "session_end": "2026-10-09", "price_basis": "total_return"},
        "sector_dossiers": _ev_dossier()}})
    assert "does not match today" in _ev_section(no_benchmark["detail"])
    assert _ev_state(_ev_section(no_benchmark["detail"])) == ("mismatch", "benchmark_mismatch")

    foreign_benchmark = _copy(_ev_dossier())
    foreign_benchmark["benchmark"] = "QQQ"
    benchmark_mismatch = _run(cfg={"search": "?g=XLE",
                                   "mr": {"sector_dossiers": foreign_benchmark}})
    assert "does not match today" in _ev_section(benchmark_mismatch["detail"])
    assert _ev_state(_ev_section(benchmark_mismatch["detail"])) == ("mismatch", "benchmark_mismatch")
    # the mismatched addendum never reaches the panel
    assert "QQQ" not in _ev_section(benchmark_mismatch["detail"])


@needs_node
def test_28_forged_authority_forecast_and_provenance_are_refused_not_echoed():
    trade = _copy(_ev_dossier())
    trade["authority"]["may_trade"] = True
    out = _run(cfg={"search": "?g=XLE", "mr": {"sector_dossiers": trade}})
    ev = _ev_section(out["detail"])
    assert "claimed capabilities this read does not have" in ev
    assert _ev_state(ev) == ("refused", "authority_claimed")
    assert "may_trade=true" not in out["detail"]
    assert "+2.4%" in out["detail"], "the legacy read is untouched"

    forecast = _copy(_ev_dossier())
    forecast["forecasts"]["expected_return"] = 0.12
    out = _run(cfg={"search": "?g=XLE", "mr": {"sector_dossiers": forecast}})
    assert "claimed capabilities this read does not have" in _ev_section(out["detail"])
    assert _ev_state(_ev_section(out["detail"])) == ("refused", "forecast_value_claimed")
    assert "0.12" not in out["detail"]

    generation = _copy(_ev_dossier())
    generation["source_generation"] = {"status": "available", "id": "gen-1"}
    out = _run(cfg={"search": "?g=XLE", "mr": {"sector_dossiers": generation}})
    assert "claimed capabilities this read does not have" in _ev_section(out["detail"])
    assert _ev_state(_ev_section(out["detail"])) == ("refused", "immutable_generation_claimed")
    assert "gen-1" not in out["detail"]

    observed = _copy(_ev_dossier())
    observed["history"]["naturally_observed"] = True
    out = _run(cfg={"search": "?g=XLE", "mr": {"sector_dossiers": observed}})
    assert "claimed capabilities this read does not have" in _ev_section(out["detail"])
    assert _ev_state(_ev_section(out["detail"])) == ("refused", "naturally_observed_claimed")


@needs_node
def test_29_hostile_source_strings_are_escaped_never_rendered():
    hostile = _copy(_ev_dossier())
    hostile["groups"][2]["name_en"] = '<img src=x onerror="alert(1)">'
    hostile["groups"][2]["name_zh"] = "<script>alert(2)</script>"
    out = _run(cfg={"search": "?g=XLE", "mr": {"sector_dossiers": hostile}})
    ev = _ev_section(out["detail"])
    assert "<img src=x" not in ev
    assert "<script>alert(2)" not in ev
    assert "&lt;img src=x" in ev
    assert "&lt;script&gt;" in ev


@needs_node
def test_30_source_replacement_drops_the_stale_evidence():
    out = _run(body="""
        var before = html('mr-detail');
        __window.SECTOR_CENTRAL.measured_read.sector_dossiers = CFG.dossier2;
        dispatchDoc('langchange');
        show({before: before, after: html('mr-detail')});
    """, cfg={"search": "?g=XLE", "mr": {"sector_dossiers": _ev_dossier()},
              "dossier2": _ev_dossier(qualified=False)})
    before = _ev_section(out["before"])
    after = _ev_section(out["after"])
    assert "+2.4%" in before
    assert "+2.4%" not in after, "a replaced source must not leave stale values"
    assert "evidence_mode_not_qualified" in after


@needs_node
def test_31_selection_language_disclosure_and_focus_follow_the_inherited_journey():
    out = _run(body="""
        function clickG(g) {
            dispatchEl('click', {target: {closest: function () {
                return {getAttribute: function (k) { return k === 'data-g' ? g : null; }};
            }}});
        }
        clickG('XLY');
        var afterSelect = html('mr-detail');
        dispatchEl('toggle', {target: {className: 'mr-ev-det', open: true}});
        __docEl.attrs['data-lang'] = 'zh';
        dispatchDoc('langchange');
        var afterLang = html('mr-detail');
        var focusedAfterLang = __focused;
        clickG('XLK');
        var afterOther = html('mr-detail');
        show({afterSelect: afterSelect, afterLang: afterLang, afterOther: afterOther,
              focused: focusedAfterLang ? focusedAfterLang.getAttribute('data-g') : null,
              pressed: pressedOf(), hist: __histLog});
    """, cfg={"mr": {"sector_dossiers": _ev_dossier()}})
    assert "Consumer Discretionary" in out["afterSelect"]
    assert "<details class=\"mr-ev-det\">" in out["afterSelect"], "closed until opened"
    assert "<details class=\"mr-ev-det\" open>" in out["afterLang"], \
        "the same identity and source keep the disclosure open across a language switch"
    assert "领涨证据" in out["afterLang"], "the Chinese twin renders"
    assert "证据详情" in out["afterLang"]
    assert out["focused"] is None, "a re-render must not steal focus"
    assert "<details class=\"mr-ev-det\">" in out["afterOther"], \
        "a different identity closes the disclosure"
    assert dict(out["pressed"])["XLK"] == "true"
    assert dict(out["pressed"])["XLY"] == "false"
    assert [c for c in out["hist"] if c[0] == "push"], "the inherited deep link owns the URL"


@needs_node
def test_32_back_forward_restores_the_selection_and_its_evidence():
    out = _run(body="""
        __setLoc('?g=XLK', '');
        dispatchWin('popstate');
        show({detail: html('mr-detail'), pressed: pressedOf()});
    """, cfg={"mr": {"sector_dossiers": _ev_dossier()}})
    assert out["pressed"]["XLK"] == "true", out["pressed"]
    ev = _ev_section(out["detail"])
    assert "Technology" in ev and "科技" in ev
    assert re.search(r'63 trading sessions vs[^<]*</dt><dd><span class="mr-flat">0\.0%</span>', ev)


def test_33_the_addendum_adds_no_fetch_cache_or_lifecycle_owner():
    src = PAGE.read_text(encoding="utf-8")
    i = src.index("PSL-3 · Persistent Sector Leadership")
    j = src.index("function render() {", i)
    block = src[i:j]
    for bad in ("fetch(", "XMLHttpRequest", "setTimeout", "localStorage",
                "sessionStorage", "document.cookie"):
        assert bad not in block, bad
    # the panel still owns exactly one selection, one URL and one language hook
    region = _region(src, START, END)
    assert region.count("history.pushState") == 1
    assert region.count("addEventListener('langchange'") == 1


def test_34_evidence_styles_stay_neutral_and_native():
    src = PAGE.read_text(encoding="utf-8")
    rules = [l for l in src.split("\n") if l.startswith(".mr-ev")]
    assert rules, "no leadership-evidence styles"
    for rule in rules:
        for bad in ("border-left", "border-right", "box-shadow", "text-shadow",
                    "filter:", "backdrop-filter", "linear-gradient"):
            assert bad not in rule, rule
        if "font-family" in rule:
            assert "var(--font-mono)" in rule, rule
    # the disclosure target is at least 44px and keeps a visible focus ring
    assert ".mr-ev-sum{" in src and "min-height:44px" in src
    assert ".mr-ev-sum:focus-visible" in src


# Parent integration regressions: execute the shipped panel with the actual owner
# projection, including unavailable native provenance and same-key revisions.
def _ev_read(cycles: dict | None = None) -> dict:
    from engine import leadership_rotation_context as lrc
    return lrc.measured_group_read(
        _ev_cycles() if cycles is None else cycles, include_sector_dossiers=True)


@needs_node
def test_35_empty_native_source_keeps_eleven_truthful_unavailable_rows():
    out = _run(fixture=_ev_read({}), cfg={"search": "?g=XLE"})
    assert "could not be produced today" in out["body"]
    assert len(out["rows"]) == 11
    assert dict(out["rows"])["XLE"] == "true"
    ev = _ev_section(out["detail"])
    assert _ev_state(ev) == ("ok", "")
    assert "source_session_missing_or_invalid" in ev
    assert "2026-10-09" not in ev, "a missing source date must not borrow the page date"
    assert "0 of 0" not in ev, "unknown positive count is not a measured zero"
    assert "Evidence details" in ev


@needs_node
@pytest.mark.parametrize("case", [
    "missing_corrections", "claimed_generation", "claimed_original_time",
    "foreign_cohort", "foreign_identity", "parent_value_disagreement",
    "below_minus_100", "non_null_reason_with_value", "row_status_disagreement",
    "negative_count", "fractional_count", "inflated_count", "measurement_status",
    "malformed_diagnostic_count", "extra_provenance_field",
])
def test_36_invalid_dossier_never_displaces_legacy_values_or_history(case):
    read = _ev_read()
    baseline_history = _run(fixture=read, cfg={"search": "?g=XLE"})["hist"]
    d = read["sector_dossiers"]
    row = d["groups"][0]
    if case == "missing_corrections":
        del d["corrections"]
    elif case == "claimed_generation":
        d["source_generation"]["id"] = "unearned-generation"
    elif case == "claimed_original_time":
        d["availability"]["original_available_at"] = "2026-10-09T00:00:00Z"
    elif case == "foreign_cohort":
        d["cohort_id"] = read["generation"]["cohort_id"] = "foreign_cohort"
    elif case == "foreign_identity":
        row["group_id"] = read["groups"][0]["group_id"] = "ZZZZ"
    elif case == "parent_value_disagreement":
        row["relative_wealth_pct"]["rs_21d"] = 1.2345
    elif case == "below_minus_100":
        row["relative_wealth_pct"]["rs_21d"] = -101
        read["groups"][0]["current"]["rs_21d"] = -101
    elif case == "non_null_reason_with_value":
        row["null_reasons"]["rs_21d"] = "missing_group"
    elif case == "row_status_disagreement":
        row["status"] = "unavailable"
    elif case == "negative_count":
        d["cross_sector_breadth_counts"]["21"]["measured_n"] = -1
    elif case == "fractional_count":
        d["cross_sector_breadth_counts"]["21"]["positive_n"] = 5.5
    elif case == "inflated_count":
        d["cross_sector_breadth_counts"]["21"]["positive_n"] = 11
    elif case == "measurement_status":
        d["measurement_status"] = "available"
    elif case == "malformed_diagnostic_count":
        d["diagnostics"]["malformed_source_rows"] = -1
    elif case == "extra_provenance_field":
        d["corrections"]["revision_id"] = "claimed-revision"
    out = _run(fixture=read, cfg={"search": "?g=XLE"})
    ev = _ev_section(out["detail"])
    assert _ev_state(ev)[0] in ("invalid", "mismatch", "refused"), (case, ev)
    assert "+2.4%" in out["detail"] and "1 month vs" in out["detail"]
    assert out["hist"] == baseline_history
    assert "+2.4%" not in ev
    assert "unearned-generation" not in ev and "claimed-revision" not in ev


@needs_node
def test_37_invalid_parent_cannot_unlock_the_unavailable_selectable_grid():
    read = _ev_read({})
    read["schema"] = "foreign-parent/v9"
    out = _run(fixture=read)
    assert not out["rows"]
    assert "could not be produced today" in out["body"]


@needs_node
def test_38_native_as_known_withholding_displays_the_actual_cutoff():
    from engine import leadership_rotation_context as lrc
    cycles = _ev_cycles()
    read = _ev_read(cycles)
    read["sector_dossiers"] = lrc._compose_sector_dossiers(
        cycles, read, expected_group_ids=[g["group_id"] for g in read["groups"]],
        decision_cutoff="2026-10-08T16:00:00+00:00")
    out = _run(fixture=read, cfg={"search": "?g=XLE"})
    ev = _ev_section(out["detail"])
    assert _ev_state(ev) == ("ok", "")
    assert "2026-10-08T16:00:00+00:00" in ev
    assert "source_session_after_decision_cutoff" in ev
    assert "+2.4%" not in ev
    assert "+2.4%" in out["detail"], "the incumbent dated read remains distinct"


@needs_node
def test_39_revised_values_with_the_same_compatibility_key_reset_disclosure():
    read = _ev_read()
    revised = _copy(read)
    for row in revised["groups"]:
        if row["group_id"] == "XLE":
            row["current"]["rs_21d"] = 2.6
    for row in revised["sector_dossiers"]["groups"]:
        if row["group_id"] == "XLE":
            row["relative_wealth_pct"]["rs_21d"] = 2.6
    out = _run(fixture=read, cfg={"search": "?g=XLE", "replacement": revised}, body="""
        dispatchEl('toggle', {target: {className: 'mr-ev-det', open: true}});
        __docEl.attrs['data-lang'] = 'zh';
        dispatchDoc('langchange');
        var same = html('mr-detail');
        __window.SECTOR_CENTRAL.measured_read = CFG.replacement;
        dispatchDoc('langchange');
        show({same: same, revised: html('mr-detail')});
    """)
    assert '<details class="mr-ev-det" open>' in _ev_section(out["same"])
    ev = _ev_section(out["revised"])
    assert _ev_state(ev) == ("ok", "")
    assert "+2.6%" in ev
    assert '<details class="mr-ev-det">' in ev
    assert '<details class="mr-ev-det" open>' not in ev


@needs_node
@pytest.mark.parametrize("interruption", ["absent", "invalid", "legacy_outage"])
def test_40_interrupted_source_cannot_restore_stale_disclosure(interruption):
    out = _run(fixture=_ev_read(),
               cfg={"search": "?g=XLE", "interruption": interruption}, body="""
        var original = JSON.parse(JSON.stringify(__window.SECTOR_CENTRAL.measured_read));
        dispatchEl('toggle', {target: {className: 'mr-ev-det', open: true}});
        dispatchDoc('langchange');
        var before = html('mr-detail');
        var read = __window.SECTOR_CENTRAL.measured_read;
        if (CFG.interruption === 'invalid') read.sector_dossiers = {};
        else delete read.sector_dossiers;
        if (CFG.interruption === 'legacy_outage') read.status = 'unavailable';
        dispatchDoc('langchange');
        __window.SECTOR_CENTRAL.measured_read = original;
        dispatchDoc('langchange');
        show({before: before, after: html('mr-detail'), rows: rows().length});
    """)
    assert '<details class="mr-ev-det" open>' in _ev_section(out["before"])
    assert '<details class="mr-ev-det" open>' not in _ev_section(out["after"])
    assert "+2.4%" in _ev_section(out["after"])
    assert out["rows"] == 11


@needs_node
def test_41_detached_disclosure_toggle_cannot_reopen_the_current_packet():
    out = _run(fixture=_ev_read(), cfg={"search": "?g=XLE"}, body="""
        elOf('mr-detail').contains = function () { return false; };
        dispatchEl('toggle', {target: {className: 'mr-ev-det', open: true}});
        dispatchDoc('langchange');
        show();
    """)
    assert '<details class="mr-ev-det" open>' not in _ev_section(out["detail"])


@needs_node
def test_42_normal_all_null_normal_rebinds_selection_and_preserves_navigation():
    out = _run(fixture=_ev_read(),
               cfg={"search": "?g=XLE", "empty": _ev_read({})}, body="""
        var original = __window.SECTOR_CENTRAL.measured_read;
        __window.SECTOR_CENTRAL.measured_read = CFG.empty;
        dispatchDoc('langchange');
        var unavailable = collect();
        dispatchEl('click', {target: {closest: function () {
            return {getAttribute: function (k) { return k === 'data-g' ? 'XLK' : null; }};
        }}});
        var chosen = collect();
        __window.SECTOR_CENTRAL.measured_read = original;
        __docEl.attrs['data-lang'] = 'zh';
        dispatchDoc('langchange');
        var restored = collect();
        __setLoc('?g=XLE', '');
        dispatchWin('popstate');
        show({unavailable: unavailable, chosen: chosen, restored: restored,
              back: collect()});
    """)
    assert len(out["unavailable"]["rows"]) == 11
    assert dict(out["chosen"]["rows"])["XLK"] == "true"
    assert "source_session_missing_or_invalid" in _ev_section(out["chosen"]["detail"])
    assert dict(out["restored"]["rows"])["XLK"] == "true"
    assert "领涨证据" in _ev_section(out["restored"]["detail"])
    assert "0.0%" in _ev_section(out["restored"]["detail"])
    assert dict(out["back"]["rows"])["XLE"] == "true"
    assert "+2.4%" in _ev_section(out["back"]["detail"])

# Exact-session companion: run the shipped browser owner, including its bundled
# schema validator, on the real native Python projection. No consumer arithmetic.
def _exact_packet(name="complete"):
    return json.loads((ROOT / "tests/fixtures/leadership_rotation" /
        f"sector_window_measurements.{name}.v1.json").read_text())


def _exact_projected_parent(packet=None):
    from engine.sector_native_view import _measured_read
    packet = _exact_packet() if packet is None else packet
    read = _fixture()
    read["generation"].update(session_end=packet["end_session"],
        cohort_id=packet["cohort_id"], price_basis=packet["price_basis"],
        benchmark=packet["benchmark"])
    read["sector_window_measurements"] = packet
    return _measured_read(read, packet["end_session"])


@needs_node
@pytest.mark.parametrize("lang", ["en", "zh"])
@pytest.mark.parametrize("name", ["complete", "unavailable"])
def test_exact_native_projection_reaches_shipped_panel_with_all_eleven(lang, name):
    packet = _exact_packet(name)
    parent = _exact_projected_parent(packet)
    out = _run("show({exact:html('mr-exact'),hidden:elOf('mr-exact').hidden});",
        fixture=parent, cfg={"search":"?g=XLK","lang":lang,"as_of":packet["end_session"]})
    html = out["exact"]
    assert out["hidden"] is False
    assert f'data-exact-state="{packet["status"]}"' in html
    assert 'data-exact-selected="XLK"' in html
    assert re.findall(r'<tr data-exact-group="([^"]+)"', html) == [
        group["group_id"] for group in packet["groups"]]
    for key in ("5","20","63"):
        assert f'data-exact-window="{key}"' in html
        assert f'data-exact-benchmark="{key}"' in html
        assert packet["windows"][key]["start_session"] in html
    assert "2026-11-05" in html and "2026-08-07" in html
    assert ("21-session dossier" if lang == "en" else "原有21日档案") in html
    if name == "unavailable":
        assert ("after the stated end" if lang == "en" else "晚于所述结束日") in html
        assert html.count('data-exact-value="absolute"><span class="mr-na">—') == 36


@needs_node
@pytest.mark.parametrize("legacy", ["unavailable", "invalid", "absent_groups"])
def test_exact_selection_remains_usable_when_legacy_cannot_render(legacy):
    parent = _exact_projected_parent()
    if legacy == "unavailable":
        parent["status"] = "unavailable"
    elif legacy == "invalid":
        parent["groups"] = None  # parent binding remains valid; the legacy row container does not
    else:
        parent.pop("groups")
    out = _run("""
        dispatchEl('click',{target:{closest:function(){return {getAttribute:function(k){
          return k==='data-g'?'XLE':null;}};}}});
        show({exact:html('mr-exact'),body:html('mr-body'),history:__histLog});
        """, fixture=parent, cfg={"search":"?g=XLK"})
    assert 'data-exact-selected="XLE"' in out["exact"]
    assert len(re.findall(r'<tr data-exact-group=', out["exact"])) == 11
    assert out["history"][-1][0] == "push" and "g=XLE" in out["history"][-1][2]
    assert "mr-xwindow" not in out["body"]  # stable sibling, not a replacement legacy read


@needs_node
@pytest.mark.parametrize("replacement", ["no_root", "absent", "invalid", "new_source"])
def test_exact_withdrawal_and_revision_retire_values_and_open_state(replacement):
    source = {
        "no_root": "window.SECTOR_CENTRAL=null;",
        "absent": "delete window.SECTOR_CENTRAL.measured_read.sector_window_measurements;",
        "invalid": "window.SECTOR_CENTRAL.measured_read.sector_window_measurements.authority.may_trade=true;",
        "new_source": """var p=window.SECTOR_CENTRAL.measured_read.sector_window_measurements;
            p.clocks.publication='2026-11-06T01:00:00Z';
            p.limitations.publication={status:'supplied',clock:p.clocks.publication};""",
    }[replacement]
    body = """
      dispatchEl('toggle',{target:{className:'mr-x-det',open:true,getAttribute:function(){return 'source';}}});
      dispatchDoc('langchange');
      var opened=html('mr-exact');
      __REPLACEMENT__
      dispatchDoc('langchange');
      __setLoc('?g=XLE','#map'); dispatchWin('popstate');
      dispatchEl('click',{target:{closest:function(){return {getAttribute:function(k){return k==='data-g'?'XLK':null;}};}}});
      show({opened:opened,exact:html('mr-exact'),hidden:elOf('mr-exact').hidden});
    """.replace("__REPLACEMENT__",source)
    out = _run(body,fixture=_exact_projected_parent(),cfg={"search":"?g=XLK"})
    assert 'data-exact-disclosure="source" open' in out["opened"]
    assert 'data-exact-disclosure="source" open' not in out["exact"]
    if replacement in ("no_root","absent"):
        assert out["exact"] == "" and out["hidden"] is True
    elif replacement == "invalid":
        assert 'data-exact-state="invalid"' in out["exact"]
        assert "data-exact-value=" not in out["exact"]
    else:
        assert "2026-11-06T01:00:00Z" in out["exact"]
        assert 'data-exact-selected="XLK"' in out["exact"]


@needs_node
def test_exact_same_source_language_change_keeps_both_disclosures():
    out = _run("""
        ['compare','source'].forEach(function(kind){
          dispatchEl('toggle',{target:{className:'mr-x-det',open:true,getAttribute:function(){return kind;}}});
        });
        __docEl.attrs['data-lang']='zh';dispatchDoc('langchange');
        show({exact:html('mr-exact')});
        """,fixture=_exact_projected_parent(),cfg={"search":"?g=XLK"})
    assert 'data-exact-disclosure="source" open' in out["exact"]
    assert 'data-exact-disclosure="compare" open' in out["exact"]
    assert "精确交易时段回报" in out["exact"]
    assert 'data-exact-selected="XLK"' in out["exact"]


@needs_node
@pytest.mark.parametrize("change", ["receipt","date","benchmark","coverage"])
def test_exact_invalid_supplied_packet_never_becomes_a_figure(change):
    parent = _exact_projected_parent()
    packet = parent["sector_window_measurements"]
    if change == "receipt": packet["receipt"] = {"a":"中"*3000}
    elif change == "date": packet["windows"]["5"]["start_session"]="2026-02-30"
    elif change == "benchmark":
        packet["windows"]["5"].update(benchmark_return_pct=None,benchmark_null_reason="benchmark_missing")
    else: packet["groups"][0]["windows"]["5"]["coverage"] = {"observed_n":2,"expected_n":6,"ratio":0.333333}
    out = _run("show({exact:html('mr-exact')});",fixture=parent,cfg={"search":"?g=XLK"})
    assert 'data-exact-state="invalid"' in out["exact"]
    assert "data-exact-value=" not in out["exact"]


@needs_node
def test_exact_opaque_receipt_and_roots_are_not_executable_markup():
    parent = _exact_projected_parent()
    packet = parent["sector_window_measurements"]
    packet["receipt"]={"<script>opaque</script>":"SECRET_RECEIPT_VALUE"}
    packet["source_roots"]=['<img src=x onerror="alert(1)">']
    out = _run("show({exact:html('mr-exact')});",fixture=parent,cfg={"search":"?g=XLK"})
    assert 'data-exact-state="available"' in out["exact"]
    assert "SECRET_RECEIPT_VALUE" not in out["exact"] and "opaque</script>" not in out["exact"]
    assert '<img src=' not in out["exact"] and '&lt;img src=x' in out["exact"]


def _dated_context_fixture(*, decision_cutoff=None):
    # Consumer tests use detached, frozen outputs of the qualified owner. They
    # must not import a private fixture helper from another source branch.
    assert decision_cutoff in (None, "2026-10-01T20:00:00Z")
    name = ("dated_context_current_v1.json" if decision_cutoff is None
            else "dated_context_historical_v1.json")
    path = ROOT / "tests" / "fixtures" / "leadership_rotation" / name
    return json.loads(path.read_text(encoding="utf-8"))


@needs_node
@pytest.mark.parametrize("lang", ["en", "zh"])
def test_dated_context_displays_separate_owner_clocks_coverage_and_unmet_falsifiers(lang):
    out = _run(cfg={"lang": lang, "search": "?g=XLK", "dated_context": _dated_context_fixture()})
    context = out["context"]
    assert 'data-dated-state="ok"' in context
    assert "2026-09-01" in context and "2026-11-06" in context
    assert "3 / 5" in context and "MU, WDC, SNDK, STX, NTAP" in context
    assert context.count('data-dated-alternative=') == 4
    assert "21.9%" in context
    assert ("Market-global risk" if lang == "en" else "全市场风险") in context
    assert ("Separate policy posture" if lang == "en" else "单独列示的政策姿态") in context
    assert ("Prospective falsifier — not evaluated" if lang == "en" else "前瞻证伪条件 — 尚未评估") in context
    assert ("Sector mapping and original historical availability are not established" if lang == "en"
            else "板块映射与原始历史可用时间尚未确立") in context
    assert ("Required source coverage is unavailable" if lang == "en" else "所需来源覆盖不可用") in context
    # Independent context never overwrites the closed selected-sector evidence.
    assert "data-dated-alternative" not in out["detail"]
    assert "sector_cause" not in context


@needs_node
@pytest.mark.parametrize("case", ["authority", "sector_claim", "pit_claim", "scope", "falsifier",
    "comparison_id", "reference", "shape", "oversize", "invalid_hash", "member_count", "covered_count",
    "coverage_ratio", "null_breadth", "null_risk_score", "null_policy", "unavailable_positive_risk", "market_supported"])
def test_dated_context_invalid_packet_withdraws_all_context_readings(case):
    packet = _dated_context_fixture()
    if case == "authority": packet["authority"]["may_trade"] = True
    elif case == "sector_claim": packet["limitations"]["current_sector_usable"] = True
    elif case == "pit_claim": packet["limitations"]["historically_admissible"] = True
    elif case == "scope": packet["scope"] = "sector_cause"
    elif case == "falsifier": packet["comparison"]["entries"][0]["falsifier"]["met"] = True
    elif case == "comparison_id": packet["comparison"]["entries"][0]["id"] = "sector_cause"
    elif case == "reference": packet["comparison"]["entries"][0]["evidence_refs"] = ["private.token"]
    elif case == "shape": packet["observations"]["orders"] = ["BUY"]
    elif case == "oversize": packet["market_risk"]["coherence"]["contradictions"] = ["x" * 16384]
    elif case == "invalid_hash": packet["provenance"]["source_attribution"]["config_document"]["raw_sha256"] = "invalid"
    elif case == "member_count": packet["observations"]["revision_state"]["n_members"] = 6
    elif case == "covered_count": packet["observations"]["revision_state"]["n_covered"] = 2
    elif case == "coverage_ratio": packet["observations"]["revision_state"]["coverage"] = 0.9
    elif case == "null_breadth": packet["observations"]["revision_state"]["breadth"] = None
    elif case == "null_risk_score": packet["market_risk"]["measured_state"]["score"] = None
    elif case == "null_policy": packet["market_risk"]["policy_summary"]["posture"] = None
    elif case == "unavailable_positive_risk": packet["market_risk"]["status"] = "unavailable";packet["status"] = "partial"
    elif case == "market_supported": packet["comparison"]["entries"][3]["status"] = "supported"
    out = _run(cfg={"dated_context": packet})
    assert 'data-dated-state="invalid"' in out["context"]
    assert "data-dated-alternative=" not in out["context"]
    assert "21.9%" not in out["context"] and "Memory, HBM" not in out["context"]


@needs_node
def test_dated_context_is_independent_of_legacy_absence_and_withholds_historical_values():
    current = _run(cfg={"central": "absent", "dated_context": _dated_context_fixture()})
    assert 'data-dated-state="ok"' in current["context"]
    assert "21.9%" in current["context"]
    historical = _run(cfg={"dated_context": _dated_context_fixture(decision_cutoff="2026-10-01T20:00:00Z")})
    assert 'data-dated-state="ok"' in historical["context"]
    assert "21.9%" not in historical["context"]
    assert "No current-sector or historical conclusion is admitted" in historical["context"]


@needs_node
def test_dated_context_disclosure_resets_on_selection_replacement_and_withdrawal():
    out = _run("""
      dispatchEl('toggle',{target:{className:'mr-dc-det',open:true}});
      dispatchDoc('langchange');var same=html('mr-context');
      dispatchEl('click',{target:{closest:function(){return {getAttribute:function(k){return k==='data-g'?'XLE':null;}};}}});
      var selected=html('mr-context');
      dispatchEl('toggle',{target:{className:'mr-dc-det',open:true}});
      __window.SECTOR_CENTRAL.dated_context.theme.name='Replacement theme';
      dispatchDoc('langchange');var replaced=html('mr-context');
      delete __window.SECTOR_CENTRAL.dated_context;
      dispatchDoc('langchange');
      show({same:same,selected:selected,replaced:replaced,withdrawn:html('mr-context'),hidden:elOf('mr-context').hidden});
    """,cfg={"search":"?g=XLK", "dated_context":_dated_context_fixture()})
    assert '<details class="mr-dc-det" open>' in out["same"]
    assert '<details class="mr-dc-det" open>' not in out["selected"]
    assert "Replacement theme" in out["replaced"]
    assert '<details class="mr-dc-det" open>' not in out["replaced"]
    assert out["withdrawn"] == "" and out["hidden"] is True


@needs_node
def test_dated_context_escapes_owner_text_and_keeps_source_authority_separate():
    packet = _dated_context_fixture()
    packet["theme"]["name"] = '<img src=x onerror="alert(1)">'
    packet["comparison"]["entries"][0]["statement"] = '<script>alert(1)</script>'
    packet["market_risk"]["source_authority"]["envelope_may_gate"] = True
    out = _run(cfg={"dated_context": packet})
    assert 'data-dated-state="ok"' in out["context"]
    assert '<img src=' not in out["context"] and '&lt;img src=x' in out["context"]
    assert '<script>' not in out["context"] and '&lt;script&gt;' in out["context"]
    assert "gating, sizing, trading and escalation are disabled" in out["context"]


def _native_wire_fixture(*, generation="sector-browser-1", theme_name=None, no_read=False,
                         published_at="2026-11-06T02:00:00Z", qualification="stale", outage=False,
                         exact_companion=True, classification=None):
    """Actual native-owner projection and actual wire bytes over controlled inputs.

    This proves transport/admission; these fixtures are not production evidence.
    The separate exact-window companion is the incumbent owner's frozen fixture.
    """
    from dataclasses import replace
    from engine.sector_native_view import project_sector_view
    from lib.sector_generation_wire import encode_sector_generation
    from tests.test_sector_native_view import (
        specimen, _dossier_packet, _dossier_rows, _exact_window_parent, _exact_window_packet)
    inputs, receipt = specimen.__wrapped__()
    exact = _exact_window_packet()
    end = exact["end_session"]
    read = _exact_window_parent(exact)
    read["generation"].update(session_end=end, id=f"{end}|SPY|us_sectors_11")
    dossier = _dossier_packet(_dossier_rows())
    dossier.update(as_of=end, compatibility_key=read["generation"]["id"])
    read["sector_dossiers"] = dossier
    read["sector_window_measurements"] = exact
    if not exact_companion:
        read.pop("sector_window_measurements")
    inputs.central.update(as_of=end, measured_read=read,
        dated_context=_dated_context_fixture())
    if classification is not None:
        inputs.central["captured_classification"] = classification
    if theme_name is not None:
        inputs.central["dated_context"]["theme"]["name"] = theme_name
    inputs.central["sectors"] = [{"id": row["group_id"].lower(),
        "ticker": row["group_id"], "kind": "sector", "name": row["name_en"]}
        for row in read["groups"]]
    inputs.cycles["meta"]["asOf"] = end
    inputs.cycles["sectors"] = [{"id": row["group_id"].lower(),
        "ticker": row["group_id"], "kind": "sector", "turns": [],
        "rs_history": [{"date": day, "rs_21d": row["current"]["rs_21d"]-offset,
                        "rs_63d": row["current"]["rs_63d"]-offset}
                       for day, offset in (("2026-10-30", 0.5), (end, 0.0))]}
        for row in read["groups"]]
    if no_read:
        inputs.central.pop("measured_read")
    elif outage:
        inputs.central["measured_read"]={"schema":"leadership_rotation_context.measured_group_read/v1",
            "status":"unavailable","reason":"projection_error"}
    receipt = replace(receipt, generation_id=generation, source_session=end,
                      baseline_session=receipt.source_session, published_at=published_at,
                      qualification=qualification)
    projection = project_sector_view(inputs, receipt, audience="preview")
    return json.loads(encode_sector_generation(audience="preview", source_session=end,
        published_at=receipt.published_at, qualification=receipt.qualification,
        projection=projection))


def _run_native(body="await drainNative();show(nativeCollect());", *, wire=None, **cfg):
    cfg = {"native": True, "search": "?g=XLK", "cycles": CYC, **cfg}
    if "native_responses" not in cfg:
        cfg["native_responses"]=[{"body": wire if wire is not None else _native_wire_fixture()}]
    return _run("(async function(){" + body + "})().catch(function(e){console.error(e);process.exitCode=1;});", cfg=cfg)


@needs_node
@pytest.mark.parametrize("lang", ["en", "zh"])
def test_native_generation_hydrates_measurements_history_exact_and_context_atomically(lang):
    wire = _native_wire_fixture()
    out = _run_native(wire=wire, lang=lang, has_session=True)
    assert out["nativeState"] == "ready"
    assert out["generation"] == wire["projection"]["receipt"]["generation_id"]
    assert out["content"] == wire["projection"]["receipt"]["content_sha256"]
    assert len(out["rows"]) == 11 and ["XLK", "true"] in out["rows"]
    assert '<svg' in out["hist"] and "2026-11-05" in out["hist"]
    assert "2026-10-09" not in out["hist"]
    assert 'data-dated-state="ok"' in out["context"]
    assert out["exact"].count('data-exact-group=') == 11
    assert "21.9%" in out["context"] and "3 / 5" in out["context"]
    assert out["sessionReads"] == 1
    assert out["calls"] == [{"url": "/api/sector-generation?audience=preview",
        "credentials": "same-origin", "cache": "no-store", "redirect": "error", "aborted": False}]
    assert out["legacy"]["as_of"] == "2026-10-09"  # Other page owners retain their global.


@needs_node
def test_native_generation_language_change_uses_one_receipt_and_keeps_selection():
    out = _run_native("""
      await drainNative();var first=nativeCollect();
      __docEl.attrs['data-lang']='zh';dispatchDoc('langchange');await drainNative();
      show({first:first,second:nativeCollect()});
    """)
    assert out["first"]["content"] == out["second"]["content"]
    assert len(out["second"]["calls"]) == 1
    assert ["XLK", "true"] in out["second"]["rows"]
    assert "全市场风险" in out["second"]["context"]


@needs_node
@pytest.mark.parametrize("case,state", [(401,"unauthorized"),(403,"forbidden"),(503,"unavailable"),
    ("bad_json","invalid"),("oversize","invalid"),("wrong_session","invalid"),
    ("wrong_history","invalid"),("invalid_context","invalid"),("network","unavailable"),
    ("duplicate_ticker","invalid"),("foreign_benchmark","invalid"),("unavailable_wrong_session","invalid"),
    ("invalid_utf8","invalid")])
def test_native_generation_failure_withdraws_every_panel_source_without_static_fallback(case,state):
    wire = _native_wire_fixture()
    if isinstance(case,int): response={"body": {},"status":case}
    elif case=="bad_json": response={"raw":"not json"}
    elif case=="oversize": response={"raw":" "*(4*1024*1024+1)}
    elif case=="network": response={"reject":"offline"}
    elif case=="invalid_utf8": response={"bytes":[0xc3,0x28]}
    else:
        if case=="wrong_session":wire["projection"]["receipt"]["source_session"]="2026-11-04"
        elif case=="wrong_history":wire["projection"]["data"]["history"]["sectors"][0]["ticker"]="OTHER"
        elif case=="duplicate_ticker":
            wire["projection"]["data"]["core"]["sectors"][1]["ticker"]="XLB"
            wire["projection"]["data"]["history"]["sectors"][1]["ticker"]="XLB"
        elif case in ("foreign_benchmark","unavailable_wrong_session"):
            read=wire["projection"]["data"]["core"]["measured_read"]
            read.pop("sector_dossiers");read.pop("sector_window_measurements")
            if case=="foreign_benchmark":read["generation"]["benchmark"]="QQQ"
            else:read["status"]="unavailable";read["generation"]["session_end"]="2026-11-04"
        else:wire["projection"]["data"]["core"]["dated_context"]["theme"]["status"]="unavailable"
        response={"body":wire}
    out=_run_native("""
      await drainNative();var before=nativeCollect();nativeRetry();await drainNative();
      show({before:before,after:nativeCollect()});
    """,native_responses=[{"body":_native_wire_fixture()},response])
    assert out["before"]["nativeState"]=="ready"
    after=out["after"]
    assert after["nativeState"]==state and after["generation"]==after["content"]==""
    assert after["rows"]==[] and after["hist"] is None and after["detail"] is None
    assert after["context"]=="" and after["contextHidden"] is True
    assert "21.9%" not in after["body"] and "2026-10-09" not in after["body"]


@needs_node
def test_native_generation_signout_cancels_a_queued_request_and_blocks_cookie_retry():
    out=_run_native("""
      nativeAuth('SIGNED_OUT',null);await drainNative();nativeRetry();await drainNative();
      show(nativeCollect());
    """)
    assert out["nativeState"]=="unauthorized" and out["calls"]==[]


@needs_node
@pytest.mark.parametrize("event", ["SIGNED_OUT", "TOKEN_REFRESHED"])
def test_native_generation_identity_loss_withdraws_and_late_response_cannot_restore(event):
    out=_run_native("""
      nativeAuth('SIGNED_IN','account-a');await drainNative();
      nativeAuth(CFG.loss_event,null);nativeRespond(0,{body:CFG.late_wire});await drainNative();
      nativeRetry();await drainNative();show(nativeCollect());
    """,native_responses=[],loss_event=event,late_wire=_native_wire_fixture())
    assert out["nativeState"]=="unauthorized" and out["rows"]==[]
    assert len(out["calls"])==1 and out["calls"][0]["aborted"] is True


@needs_node
def test_native_generation_account_change_ignores_late_old_response():
    first=_native_wire_fixture(generation="account-a-generation",theme_name="Old account context")
    second=_native_wire_fixture(generation="account-b-generation",theme_name="Current account context")
    out=_run_native("""
      nativeAuth('SIGNED_IN','account-a');await drainNative();
      nativeAuth('SIGNED_IN','account-b');await drainNative();
      nativeRespond(1,{body:CFG.second});await drainNative();var fresh=nativeCollect();
      nativeRespond(0,{body:CFG.first});await drainNative();show({fresh:fresh,late:nativeCollect()});
    """,native_responses=[],first=first,second=second)
    assert out["fresh"]["generation"]==out["late"]["generation"]=="account-b-generation"
    assert "Current account context" in out["late"]["context"]
    assert "Old account context" not in out["late"]["context"]
    assert len(out["late"]["calls"])==2 and out["late"]["calls"][0]["aborted"] is True


@needs_node
def test_native_generation_replacement_resets_disclosure_even_at_the_same_session():
    first=_native_wire_fixture()
    second=_native_wire_fixture(generation="sector-browser-2",theme_name="Replacement context")
    out=_run_native("""
      await drainNative();dispatchEl('toggle',{target:{className:'mr-dc-det',open:true}});
      dispatchDoc('langchange');var opened=html('mr-context');nativeRetry();await drainNative();
      show({opened:opened,replacement:nativeCollect()});
    """,native_responses=[{"body":first},{"body":second}])
    assert '<details class="mr-dc-det" open>' in out["opened"]
    assert '<details class="mr-dc-det" open>' not in out["replacement"]["context"]
    assert out["replacement"]["generation"]=="sector-browser-2"
    assert "Replacement context" in out["replacement"]["context"]
    assert ["XLK","true"] in out["replacement"]["rows"]


@needs_node
def test_native_generation_has_one_bounded_auth_settle_and_request_timeout():
    out=_run_native("""
      await drainNative();var before=__nativeCalls.length;
      __timersLog.filter(function(t){return t.ms===3000;}).forEach(function(t){t.fn();});
      await drainNative();var loading=nativeCollect();
      __timersLog.filter(function(t){return t.ms===20000&&!t.cancelled;}).forEach(function(t){t.fn();});
      await drainNative();show({before:before,loading:loading,after:nativeCollect()});
    """,auth_ready=False,native_responses=[])
    assert out["before"]==0 and out["loading"]["nativeState"]=="loading"
    assert len(out["after"]["calls"])==1 and out["after"]["calls"][0]["aborted"] is True
    assert out["after"]["nativeState"]=="unavailable"


@needs_node
def test_native_generation_keeps_typed_absence_and_clears_missing_selection():
    out=_run_native(wire=_native_wire_fixture(no_read=True),search="?g=REMOVED")
    assert out["nativeState"]=="ready" and out["rows"]==[]
    assert 'data-dated-state="ok"' in out["context"]
    assert "This read is not in today&#39;s data yet" in out["body"]


@needs_node
@pytest.mark.parametrize("qualification", ["accepted","stale","degraded"])
def test_native_generation_preserves_aware_minute_publication_and_owner_qualification(qualification):
    out=_run_native(wire=_native_wire_fixture(published_at="2026-11-06T02:00+00:00",qualification=qualification))
    assert out["nativeState"]=="ready" and "2026-11-06T02:00+00:00" in out["sub"]


@needs_node
def test_native_generation_accepts_exact_outage_stub_without_static_measurements():
    out=_run_native(wire=_native_wire_fixture(outage=True))
    assert out["nativeState"]=="ready" and out["rows"]==[] and out["hist"] is None
    assert 'data-dated-state="ok"' in out["context"]


@needs_node
def test_native_generation_preserves_dossier_binding_when_exact_companion_is_absent():
    out=_run_native(wire=_native_wire_fixture(exact_companion=False))
    assert out["nativeState"]=="ready" and ["XLK","true"] in out["rows"]
    assert 'data-ev-state="ok"' in out["detail"]
    assert "63 trading sessions" in out["detail"]
    assert 'data-exact-state="ok"' not in out["exact"]


@needs_node
def test_native_generation_decodes_utf8_when_transport_splits_a_multibyte_character():
    wire=_native_wire_fixture(theme_name="中文 context")
    out=_run_native(native_responses=[{"body":wire,"split_utf8":True}])
    assert out["nativeState"]=="ready" and "中文 context" in out["context"]
