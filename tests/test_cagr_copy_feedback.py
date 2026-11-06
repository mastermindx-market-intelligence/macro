"""Focused tests for the CAGR calculator copy-result feedback handler.

Extracts the ``{% block calc_script %}`` body from the proposed
``templates/calculators/cagr.html.j2``, runs it under Node's ``vm`` module with
a minimal DOM/navigator/clipboard stub (no real browser, clipboard, network or
third-party package), and drives the ``#copy-result`` click handler through:

* modern clipboard resolve / reject / synchronous throw
* legacy ``execCommand('copy')`` true / false / throw
* invalid result (no copy attempt at all)
* retry resets feedback and the manual field
* explicit manual select-and-copy recovery, localized via the existing
  ``t('EN', 'ZH')`` convention

Negative controls: the same battery is run against the pre-fix handler
(embedded below verbatim) and the tests assert the battery *detects* the old
false-success behavior — i.e. the assertions discriminate the repair instead of
merely matching source strings.

Limitations: requires the ``node`` binary on PATH (skipped otherwise, with
reason); promise settlement is observed via microtask/setImmediate ticks, which
covers the then/catch handlers but not real browser permission prompts.
"""

import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

TEMPLATE_PATH = Path(
    os.environ.get("CAGR_TEMPLATE_PATH", Path(__file__).resolve().parents[1] / "templates/calculators/cagr.html.j2")
)
NODE = shutil.which("node")

pytestmark = pytest.mark.skipif(NODE is None, reason="node runtime not available on PATH")

# Valid find-mode inputs -> CAGR: 7.00% over 10.0 years (per the §6 self-check).
INPUTS = {"v0": "10,000", "v1": "19,672", "years": "10"}

# Exact copyLine output for those inputs (thousands separator is locale-dependent
# in Node builds, so both forms are accepted; everything else is exact).
COPYLINE_RE = re.compile(
    r"^CAGR: 7\.00% over 10\.0 years "
    r"\(\$(?:10,000|10000) → \$(?:19,672|19672)\) — mastermind-x\.com$"
)

SCENARIOS = [
    {"name": "modern-resolve", "clipboard": "resolve", "execCommand": True, "inputs": INPUTS},
    {"name": "modern-reject", "clipboard": "reject", "execCommand": True, "inputs": INPUTS},
    {"name": "modern-sync-throw", "clipboard": "throw", "execCommand": True, "inputs": INPUTS},
    {"name": "fallback-true", "clipboard": "none", "execCommand": True, "inputs": INPUTS},
    {"name": "fallback-false", "clipboard": "none", "execCommand": False, "inputs": INPUTS},
    {"name": "fallback-throw", "clipboard": "none", "execCommand": "throw", "inputs": INPUTS},
    {"name": "invalid-result", "clipboard": "resolve", "execCommand": True, "inputs": {}},
    {"name": "retry-reset", "clipboard": "reject", "execCommand": True, "inputs": INPUTS,
     "phase2": {"clipboard": "resolve"}},
    {"name": "select-button", "clipboard": "reject", "execCommand": True, "inputs": INPUTS,
     "selectAfterFail": True},
]

HARNESS_JS = """\
"use strict";
const fs = require("fs");
const vm = require("vm");

const jsSource = fs.readFileSync(process.argv[2], "utf8");
const scenarios = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));

function runScenario(sc) {
  const els = {};
  const obs = { focusCalls: [], selectCalls: [], timeouts: [], appended: [],
                removed: [], execCommandCalls: 0, writeTextCalls: 0, writeTextArg: null,
                handlerThrows: 0 };
  let elCounter = 0;

  function makeEl(id) {
    const el = {
      id: id, value: "", textContent: "", hidden: false, style: {}, attrs: {},
      dataset: {}, _classes: new Set(), listeners: {},
      addEventListener: function (t, f) { (el.listeners[t] = el.listeners[t] || []).push(f); },
      querySelector: function () { return null; },
      querySelectorAll: function () { return []; },
      focus: function () { obs.focusCalls.push(id); },
      select: function () { obs.selectCalls.push(id); },
      setAttribute: function (k, v) { el.attrs[k] = v; }
    };
    el.classList = {
      add: function (c) { el._classes.add(c); },
      remove: function (c) { el._classes.delete(c); },
      contains: function (c) { return el._classes.has(c); }
    };
    return el;
  }
  function getEl(id) { if (!els[id]) els[id] = makeEl(id); return els[id]; }

  const documentStub = {
    listeners: {},
    addEventListener: function (t, f) {
      (documentStub.listeners[t] = documentStub.listeners[t] || []).push(f);
    },
    getElementById: function (id) { return getEl(id); },
    createElement: function (tag) { return makeEl("@" + tag + "#" + (elCounter++)); },
    body: {
      appendChild: function (c) { obs.appended.push(c.id); },
      removeChild: function (c) { obs.removed.push(c.id); }
    },
    execCommand: function () {
      obs.execCommandCalls++;
      const r = sc.execCommand === undefined ? true : sc.execCommand;
      if (r === "throw") throw new Error("execCommand denied");
      return r === true;
    }
  };

  const nav = {};
  function applyClipboard(mode) {
    if (mode === "none") { delete nav.clipboard; return; }
    nav.clipboard = { writeText: function (t) {
      obs.writeTextCalls++;
      obs.writeTextArg = t;
      if (mode === "reject") return Promise.reject(new Error("NotAllowedError"));
      if (mode === "throw") throw new Error("NotAllowedError: synchronous");
      return Promise.resolve(true);
    } };
  }
  applyClipboard(sc.clipboard);

  // Mirror the static markup: the manual-recovery widgets start hidden.
  ["v0", "v1", "years", "cagr-rate", "date-start", "date-end",
   "copied", "copy-result", "copy-fail", "copy-manual",
   "copy-manual-text", "copy-manual-select"].forEach(getEl);
  if (els["copy-fail"]) els["copy-fail"].hidden = true;
  if (els["copy-manual"]) els["copy-manual"].hidden = true;
  Object.keys(sc.inputs || {}).forEach(function (k) { getEl(k).value = sc.inputs[k]; });

  const sandbox = {
    document: documentStub,
    navigator: nav,
    console: { log: function () {}, error: function () {}, warn: function () {} },
    setTimeout: function (fn, d) {
      obs.timeouts.push({ fn: fn, delay: d, cleared: false });
      return obs.timeouts.length;
    },
    clearTimeout: function (id) { if (obs.timeouts[id - 1]) obs.timeouts[id - 1].cleared = true; },
    Math: Math, Date: Date, JSON: JSON, Promise: Promise,
    isFinite: isFinite, isNaN: isNaN, parseFloat: parseFloat, parseInt: parseInt,
    String: String, Number: Number, Array: Array, Object: Object, RegExp: RegExp, Error: Error
  };
  vm.createContext(sandbox);
  vm.runInContext(jsSource, sandbox, { filename: "cagr-inline.js" });

  (documentStub.listeners["DOMContentLoaded"] || []).forEach(function (f) { f(); });

  function click(id) {
    const hs = els[id] && els[id].listeners.click;
    if (!hs) return false;
    hs.forEach(function (h) {
      // a browser contains exceptions thrown inside an event listener
      try { h({ target: null }); } catch (e) { obs.handlerThrows++; }
    });
    return true;
  }
  const settle = function () { return new Promise(function (r) { setImmediate(r); }); };

  return (async function () {
    click("copy-result");
    await settle(); await settle();
    if (sc.phase2) {
      applyClipboard(sc.phase2.clipboard);
      click("copy-result");
      await settle(); await settle();
    }
    if (sc.selectAfterFail) click("copy-manual-select");

    function cls(id, c) { return els[id] ? els[id]._classes.has(c) : false; }
    const mf = "copy-manual-text";
    return {
      scenario: sc.name,
      successShown: cls("copied", "show"),
      failShown: els["copy-fail"] ? els["copy-fail"].hidden === false : false,
      manualShown: els["copy-manual"] ? els["copy-manual"].hidden === false : false,
      manualValue: els[mf] ? els[mf].value : null,
      writeTextCalls: obs.writeTextCalls,
      writeTextArg: obs.writeTextArg,
      execCommandCalls: obs.execCommandCalls,
      handlerThrows: obs.handlerThrows,
      timeoutDelays: obs.timeouts.map(function (t) { return t.delay; }),
      textareaAppended: obs.appended.length,
      textareaRemoved: obs.removed.length,
      focusCalls: obs.focusCalls.slice(),
      manualFieldSelects: obs.selectCalls.filter(function (x) { return x === mf; }).length,
      selectButtonWired: !!(els["copy-manual-select"] && els["copy-manual-select"].listeners.click)
    };
  })();
}

(async function main() {
  const out = [];
  for (const sc of scenarios) out.push(await runScenario(sc));
  process.stdout.write(JSON.stringify(out));
})().catch(function (e) {
  process.stderr.write("HARNESS ERROR: " + ((e && e.stack) || e));
  process.exit(1);
});
"""

OLD_SCRIPT = r"""(function(){
  "use strict";

  var mode = "find";

  function compute(inp){
    var m=inp.mode, V0=inp.V0, V1=inp.V1, n=inp.n, cagrRate=inp.cagrRate;
    if(!(V0>0)) return {ok:false, msg:"Enter a beginning value above zero."};
    if(!(n>0))  return {ok:false, msg:"Enter a number of years (or two dates)."};
    var underYear = n < 1;
    if(m === "find"){
      if(!(V1>0)) return {ok:false, msg:"Enter an ending value above zero."};
      var CAGR = 100 * (Math.pow(V1 / V0, 1 / n) - 1);
      var totalGain = 100 * (V1 / V0 - 1);
      return {ok:true, mode:"find", CAGR:CAGR, V1:V1, V0:V0, n:n, totalGain:totalGain, underYear:underYear};
    } else {
      if(!(cagrRate !== null && isFinite(cagrRate))) return {ok:false, msg:"Enter a CAGR rate."};
      if(cagrRate <= -100) return {ok:false, msg:"rate too low"};
      var g = cagrRate / 100;
      var projV1 = V0 * Math.pow(1 + g, n);
      var totalGain2 = 100 * (projV1 / V0 - 1);
      return {ok:true, mode:"project", V1:projV1, V0:V0, n:n, cagrRate:cagrRate, totalGain:totalGain2, underYear:underYear};
    }
  }

  document.addEventListener("DOMContentLoaded", function(){
    var $ = function(id){ return document.getElementById(id); };
    var els = { v0:$("v0"), v1:$("v1"), years:$("years"), cagrRate:$("cagr-rate"),
                dateStart:$("date-start"), dateEnd:$("date-end") };
    var outMain=$("out-main"), outUnit=$("out-unit"), outPlain=$("out-plain"),
        outGain=$("out-gain"), outYears=$("out-years"), rowDtGain=$("row-dt-gain"),
        seg=$("mode-seg"), copyBtn=$("copy-result"), copied=$("copied");
    var rowV1=$("row-v1"), rowCagr=$("row-cagr");

    function numFrom(el){ var v=parseFloat((el.value||"").replace(/,/g,"").trim()); return isFinite(v)?v:NaN; }
    function money(n){ return "$" + Math.abs(n).toLocaleString("en-US",{maximumFractionDigits:0}); }
    function parseDays(){
      var s=els.dateStart.value, e=els.dateEnd.value;
      if(!s||!e) return null;
      var d = (new Date(e) - new Date(s)) / 86400000;
      return isFinite(d) && d >= 0 ? d : null;
    }
    function dash(){ outMain.textContent="—"; outGain.textContent="—"; outYears.textContent="—"; }

    var last=null;
    function render(){
      var days = parseDays();
      var n = days !== null ? days / 365.25 : numFrom(els.years);
      var inp = { mode:mode, V0:numFrom(els.v0), V1:numFrom(els.v1), n:n, cagrRate:numFrom(els.cagrRate) };
      if(mode==="find" && isNaN(inp.V1)) inp.V1 = NaN;
      if(mode==="project" && isNaN(inp.cagrRate)) inp.cagrRate = null;
      var res=compute(inp); last=res;
      if(!res.ok){ dash(); outPlain.textContent=res.msg; outPlain.className="co-plain"; return; }
      outMain.textContent = (res.CAGR >= 0 ? "+" : "") + res.CAGR.toFixed(2) + "%";
      outPlain.textContent = "ok";
      outGain.textContent = (res.totalGain >= 0 ? "+" : "") + res.totalGain.toFixed(1) + "% total";
      outYears.textContent = res.n.toFixed(res.n>=1?2:4) + " yr";
    }

    function copyLine(){
      if(!last || !last.ok) return "";
      if(last.mode==="find"){
        return "CAGR: " + last.CAGR.toFixed(2) + "% over " + last.n.toFixed(1) + " years" +
          " (" + money(last.V0) + " → " + money(last.V1) + ") — mastermind-x.com";
      } else {
        return "Projected value: " + money(last.V1) + " from " + money(last.V0) +
          " at " + last.cagrRate.toFixed(2) + "% for " + last.n.toFixed(1) + " years — mastermind-x.com";
      }
    }
    copyBtn.addEventListener("click", function(){
      var line=copyLine(); if(!line) return;
      var done=function(){ copied.classList.add("show"); setTimeout(function(){copied.classList.remove("show");},1600); };
      if(navigator.clipboard && navigator.clipboard.writeText){ navigator.clipboard.writeText(line).then(done,done); }
      else { var ta=document.createElement("textarea"); ta.value=line; document.body.appendChild(ta); ta.select();
        try{document.execCommand("copy");}catch(e){} document.body.removeChild(ta); done(); }
    });

    ["v0","v1","years","cagr-rate","date-start","date-end"].forEach(function(id){
      var el=document.getElementById(id); if(el) el.addEventListener("input", render);
    });
    render();
  });
})();
"""


def extract_script(template_text: str) -> str:
    """Return the raw JS body of the calc_script block."""
    m = re.search(r"\{%\s*block\s+calc_script\s*%\}(.*?)\{%\s*endblock\s*%\}",
                  template_text, re.S)
    assert m, "calc_script block not found in template"
    body = m.group(1).strip()
    assert body.startswith("<script>") and body.endswith("</script>"), \
        "calc_script block must contain a single <script> element"
    return body[len("<script>"):-len("</script>")]


def run_node(js_source: str, scenarios=SCENARIOS):
    """Run the extracted handler under Node VM; return {scenario: observation}."""
    with tempfile.TemporaryDirectory(prefix="cagr-copy-test-") as td:
        tdp = Path(td)
        (tdp / "handler.js").write_text(js_source, encoding="utf-8")
        (tdp / "harness.js").write_text(HARNESS_JS, encoding="utf-8")
        (tdp / "scenarios.json").write_text(json.dumps(scenarios), encoding="utf-8")
        proc = subprocess.run(
            [NODE, str(tdp / "harness.js"), str(tdp / "handler.js"), str(tdp / "scenarios.json")],
            capture_output=True, text=True, timeout=60,
        )
    assert proc.returncode == 0, "node harness failed:\n" + proc.stderr
    return {r["scenario"]: r for r in json.loads(proc.stdout)}


@pytest.fixture(scope="module")
def results():
    return run_node(extract_script(TEMPLATE_PATH.read_text(encoding="utf-8")))


@pytest.fixture(scope="module")
def old_results():
    """The pre-fix handler, run through the identical battery (negative control)."""
    return run_node(OLD_SCRIPT)


# ── proposed implementation ──────────────────────────────────────────────────

def test_modern_success_shows_copied_only(results):
    r = results["modern-resolve"]
    assert r["successShown"] is True
    assert r["failShown"] is False
    assert r["manualShown"] is False
    assert r["writeTextCalls"] == 1
    assert r["execCommandCalls"] == 0
    assert COPYLINE_RE.match(r["writeTextArg"]), r["writeTextArg"]
    assert r["timeoutDelays"] == [1600]  # existing success ack timeout preserved


def test_modern_reject_never_shows_success(results):
    r = results["modern-reject"]
    assert r["successShown"] is False
    assert r["failShown"] is True
    assert r["manualShown"] is True
    assert COPYLINE_RE.match(r["manualValue"]), r["manualValue"]
    assert r["writeTextCalls"] == 1       # exactly one attempt
    assert r["execCommandCalls"] == 0     # no hidden retry after rejection
    assert r["timeoutDelays"] == []       # success ack never scheduled


def test_modern_sync_throw_never_shows_success(results):
    r = results["modern-sync-throw"]
    assert r["successShown"] is False
    assert r["failShown"] is True
    assert r["manualShown"] is True
    assert COPYLINE_RE.match(r["manualValue"]), r["manualValue"]
    assert r["writeTextCalls"] == 1
    assert r["execCommandCalls"] == 0
    assert r["handlerThrows"] == 0          # sync throw handled, not propagated


def test_fallback_true_shows_success(results):
    r = results["fallback-true"]
    assert r["successShown"] is True
    assert r["failShown"] is False
    assert r["manualShown"] is False
    assert r["execCommandCalls"] == 1
    assert r["textareaAppended"] == 1 and r["textareaRemoved"] == 1
    assert r["timeoutDelays"] == [1600]


def test_fallback_false_shows_failure(results):
    r = results["fallback-false"]
    assert r["successShown"] is False
    assert r["failShown"] is True
    assert r["manualShown"] is True
    assert COPYLINE_RE.match(r["manualValue"]), r["manualValue"]
    assert r["textareaAppended"] == r["textareaRemoved"] == 1


def test_fallback_throw_shows_failure(results):
    r = results["fallback-throw"]
    assert r["successShown"] is False
    assert r["failShown"] is True
    assert r["manualShown"] is True
    assert COPYLINE_RE.match(r["manualValue"]), r["manualValue"]
    assert r["textareaAppended"] == r["textareaRemoved"] == 1


def test_invalid_result_makes_no_attempt(results):
    r = results["invalid-result"]
    assert r["writeTextCalls"] == 0
    assert r["execCommandCalls"] == 0
    assert r["successShown"] is False
    assert r["failShown"] is False
    assert r["manualShown"] is False


def test_retry_resets_feedback_and_manual_field(results):
    r = results["retry-reset"]
    assert r["writeTextCalls"] == 2
    assert r["successShown"] is True        # second attempt succeeded
    assert r["failShown"] is False          # stale failure cleared
    assert r["manualShown"] is False
    assert r["manualValue"] == ""
    assert r["timeoutDelays"] == [1600]     # fresh ack only


def test_manual_select_is_explicit_user_action(results):
    r = results["select-button"]
    assert r["failShown"] is True
    assert r["selectButtonWired"] is True
    assert r["focusCalls"] == ["copy-manual-text"]
    assert r["manualFieldSelects"] >= 1


def test_async_failure_does_not_steal_focus(results):
    r = results["modern-reject"]
    assert r["focusCalls"] == []            # failure path must not grab focus
    assert r["manualFieldSelects"] == 0


def test_localized_manual_recovery_strings_present():
    text = TEMPLATE_PATH.read_text(encoding="utf-8")
    # localized failure note via the existing t('EN','ZH') convention
    assert "t('Copy failed — clipboard access was blocked. Select the text below and copy it manually.'," in text
    assert "复制失败——剪贴板访问被拒绝。请选中下方文本手动复制。" in text
    # localized manual-recovery label and explicit select action
    assert "t('Result text — select and copy', '结果文本——选中并复制')" in text
    assert "t('Select all', '全选')" in text
    # failure exposed through status semantics; recovery field is readonly
    assert 'id="copy-fail" role="status" hidden' in text
    assert '<input id="copy-manual-text" readonly>' in text


# ── negative controls: the battery must catch the pre-fix behavior ──────────

def test_negative_control_old_false_success_is_detected(old_results, results):
    for name in ("modern-reject", "fallback-false", "fallback-throw"):
        assert old_results[name]["successShown"] is True, \
            f"battery failed to catch old false-success on {name}"
        assert results[name]["successShown"] is False, \
            f"new implementation does not differ from old on {name}"


def test_negative_control_old_sync_throw_breaks_silently(old_results, results):
    # pre-fix handler propagates the sync throw (browser console error), shows
    # nothing at all; the proposed handler contains it and shows the recovery UI
    old = old_results["modern-sync-throw"]
    assert old["handlerThrows"] == 1
    assert old["successShown"] is False and old["failShown"] is False
    new = results["modern-sync-throw"]
    assert new["handlerThrows"] == 0
    assert new["failShown"] is True and new["manualShown"] is True


def test_negative_control_old_lacks_failure_and_manual_recovery(old_results, results):
    old = old_results["modern-reject"]
    assert old["failShown"] is False
    assert old["manualShown"] is False
    assert results["modern-reject"]["failShown"] is True
    assert results["modern-reject"]["manualShown"] is True
    assert old_results["fallback-false"]["failShown"] is False
    # no manual select wiring in the old handler at all
    for r in old_results.values():
        assert r["selectButtonWired"] is False
