/* test_stock_seasonality_selection.cjs — P12.T44 symbol-selection ownership harness.

   Extracts the production selection seam out of the supplied
   templates/stock_seasonality.js — from `var quick` through the end of `adopt`,
   immediately before the "Deep link" comment, carrying the file's own
   generation declaration when present — and runs the REAL pick and adopt
   bodies under Node `vm` with a controlled fetch, minimal DOM/history doubles
   and async microtask settling. No browser, no network, no packages. Only
   infrastructure living outside the seam ($, note, closePop, entityUrl,
   readScale, render, hasNeutral) is stubbed; nothing under test is mirrored.

   Usage:
     node tests/js/test_stock_seasonality_selection.cjs [path/to/stock_seasonality.js]

   The source path defaults to ../../templates/stock_seasonality.js relative to
   this file's directory (tests/js) after integration. Exit 0 when every case
   passes, 1 otherwise.

   Every entity payload is a SYNTHETIC TRANSPORT FIXTURE: the symbols, names and
   cumulative arrays exist only to carry bytes through the selection pipeline
   and make no market-data claim of any kind. */
"use strict";

var fs = require("fs");
var path = require("path");
var vm = require("vm");
var crypto = require("crypto");

var DEFAULT_SOURCE = path.resolve(__dirname, "..", "..", "templates", "stock_seasonality.js");
var SEAM_START = "var quick = $(\"sx-quick\");";
var SEAM_END = "/* Deep link";

var sourcePath = path.resolve(process.argv[2] || DEFAULT_SOURCE);
var source;
try {
  source = fs.readFileSync(sourcePath, "utf8");
} catch (e) {
  console.error("harness: cannot read source " + sourcePath + " (" + e.message + ")");
  process.exit(1);
}

var startIdx = source.indexOf(SEAM_START);
var endIdx = source.indexOf(SEAM_END);
if (startIdx < 0 || endIdx < 0 || endIdx <= startIdx) {
  console.error("harness: selection seam (var quick .. before Deep link) not found in " + sourcePath);
  process.exit(1);
}
var seam = source.slice(startIdx, endIdx);
if (seam.indexOf("function pick(") < 0 || seam.indexOf("function adopt(") < 0) {
  console.error("harness: seam does not carry the real pick and adopt bodies");
  process.exit(1);
}
console.log("generation declaration: " +
  (seam.indexOf("var pickGeneration") >= 0 ? "present (real source declaration)" : "absent (pre-repair source)"));
console.log("seam bytes: " + Buffer.byteLength(seam, "utf8"));

/* ── synthetic transport fixtures ─────────────────────────────────────── */
function synthYears(nYears) {
  var out = [], y, i, v;
  for (y = 0; y < nYears; y++) {
    var cum = [0];
    for (i = 1; i < 365; i++) {
      v = ((y * 31 + i * 7) % 13) - 6;          // deterministic fixture noise
      cum.push(cum[i - 1] + v / 1e6);
    }
    out.push({ year: 2000 + y, cum: cum });
  }
  return out;
}
function synthEntity(sym) {
  return {
    symbol: sym,
    name: "Synthetic transport fixture " + sym,
    calendar: { cum_scale: 1e-6 },
    coverage: { n_years_complete: 8 },
    neutral: null,
    family: null,
    default_window: { start_doy: 1, end_doy: 31 },
    years: synthYears(8)
  };
}

/* ── minimal DOM / history doubles + controlled fetch ─────────────────── */
function makeEl(id) {
  return {
    id: id, attrs: { "data-on": "0" }, children: [], hidden: false,
    textContent: "", value: "", style: {}, dataset: {}, disabled: false,
    setAttribute: function (k, v) { this.attrs[k] = String(v); },
    getAttribute: function (k) { return k in this.attrs ? this.attrs[k] : null; },
    appendChild: function (c) { this.children.push(c); return c; },
    removeChild: function (c) {
      var i = this.children.indexOf(c);
      if (i >= 0) this.children.splice(i, 1);
      return c;
    },
    querySelector: function () { return null; },
    querySelectorAll: function () { return []; },
    addEventListener: function () {},
    focus: function () {}
  };
}

var START_URL = "https://calendar-fixtures.invalid/seasonality";

function freshWorld(seedSymbol) {
  var els = {};
  ["sx-quick", "sx-err", "sx-nocov", "sx-name", "sx-sym", "sx-results"].forEach(function (id) {
    els[id] = makeEl(id);
  });
  var input = makeEl("sx-search");
  input.dataset = { phZh: "" };
  var neutralBtn = makeEl("sx-panel-neutral");
  var panelBtns = ["raw", "detrended", "neutral"].map(function (v) {
    var b = makeEl("panel-" + v); b.dataset.v = v; return b;
  });
  var lookbackBtns = ["0", "5", "10", "25"].map(function (v) {
    var b = makeEl("lookback-" + v); b.dataset.v = v; return b;
  });

  var fetchCalls = [];
  function makeResponse(call, desc) {
    desc = desc || {};
    var status = desc.status == null ? 200 : desc.status;
    if (status < 200 || status >= 300) {
      return {
        ok: false, status: status,
        json: function () { return Promise.reject(new Error("fixture: body refused for status " + status)); }
      };
    }
    if (desc.holdJson) {
      var body = desc.body, release, fail;
      var jp = new Promise(function (res, rej) { release = res; fail = rej; });
      call.unblockJson = function () { release(JSON.parse(JSON.stringify(body))); };
      call.failJson = function () { fail(new Error("fixture: decode failure")); };
      return { ok: true, status: status, json: function () { return jp; } };
    }
    return {
      ok: true, status: status,
      json: function () {
        call.jsonReads = (call.jsonReads || 0) + 1;
        return Promise.resolve(JSON.parse(JSON.stringify(desc.body)));
      }
    };
  }
  function controlledFetch(url, opts) {
    var call = { url: url, opts: opts, settled: false, unblockJson: null, failJson: null };
    var p = new Promise(function (resolve, reject) {
      call.resolve = function (desc) {
        if (call.settled) return;
        call.settled = true;
        resolve(makeResponse(call, desc));
      };
      call.reject = function (err) {
        if (call.settled) return;
        call.settled = true;
        reject(err);
      };
    });
    fetchCalls.push(call);
    return p;
  }

  var historyCalls = [];
  var renderCalls = [];
  var closePopCalls = 0;
  var state = { a: 1, b: 31, lookback: 0, panel: "raw", central: "median", dragged: false, symbol: seedSymbol };

  var sb = {
    document: {
      documentElement: makeEl("html"),
      querySelector: function (sel) { return String(sel).indexOf("neutral") >= 0 ? neutralBtn : null; },
      querySelectorAll: function () { return panelBtns.concat(lookbackBtns); }
    },
    window: {
      location: { href: START_URL },
      DATA_BASE: "https://calendar-fixtures.invalid/r2",
      addEventListener: function () {},
      removeEventListener: function () {},
      pageYOffset: 0,
      matchMedia: function () { return { matches: false }; }
    },
    history: {
      replaceState: function (a, b, url) { historyCalls.push({ a: a, b: b, url: url }); },
      pushState: function (a, b, url) { historyCalls.push({ a: a, b: b, url: url }); }
    },
    URL: URL,
    fetch: controlledFetch,
    $: function (id) { return els[id] || null; },
    note: function (id, on) { var n = els[id]; if (n) n.setAttribute("data-on", on ? "1" : "0"); },
    entityUrl: function (sym) {
      var base = sb.window.DATA_BASE || "";
      if (base && base.slice(-1) !== "/") base += "/";
      return base + "seasonalitydata/entities/" + encodeURIComponent(sym) + ".json";
    },
    closePop: function () {
      closePopCalls++;
      els["sx-results"].hidden = true;
      els["sx-results"].textContent = "";
      input.setAttribute("aria-expanded", "false");
    },
    readScale: function () {},
    render: function () { renderCalls.push({ symbol: state.symbol }); },
    hasNeutral: function () { return false; },
    state: state,
    E: synthEntity(seedSymbol),
    SLOTS: 365,
    DEFAULT_A: 1,
    DEFAULT_B: 31,
    input: input
  };
  vm.runInNewContext(seam, sb, { filename: "selection-seam.js" });
  if (typeof sb.pick !== "function" || typeof sb.adopt !== "function") {
    throw new Error("seam did not define the real pick and adopt functions");
  }

  return {
    sb: sb,
    els: els,
    fetchCalls: fetchCalls,
    historyCalls: historyCalls,
    renderCalls: renderCalls,
    closePopCalls: function () { return closePopCalls; },
    pick: function (sym) { return sb.pick(sym); },
    symbol: function () { return state.symbol; },
    state: function () { return state; },
    symText: function () { return els["sx-sym"].textContent; },
    nameText: function () { return els["sx-name"].textContent; },
    notice: function () {
      return {
        err: els["sx-err"].attrs["data-on"],
        nocov: els["sx-nocov"].attrs["data-on"]
      };
    },
    urlSymbol: function () {
      if (!historyCalls.length) return null;
      return new URL(historyCalls[historyCalls.length - 1].url).searchParams.get("symbol");
    },
    expectedUrl: function (sym) {
      var base = sb.window.DATA_BASE || "";
      if (base && base.slice(-1) !== "/") base += "/";
      return base + "seasonalitydata/entities/" + encodeURIComponent(sym) + ".json";
    },
    settle: function () {
      /* one macrotask turn drains every pending microtask chain */
      return new Promise(function (r) { setImmediate(r); });
    },
    settleHard: function () {
      var self = this;
      return self.settle().then(function () { return self.settle(); });
    }
  };
}

/* ── case runner ──────────────────────────────────────────────────────── */
var failures = [];
var caseCount = 0;
function assert(cond, msg) {
  if (!cond) throw new Error(msg);
}
function assertEq(actual, expected, label) {
  if (actual !== expected) {
    throw new Error(label + ": expected " + JSON.stringify(expected) + ", got " + JSON.stringify(actual));
  }
}
async function runCase(name, fn) {
  caseCount++;
  try {
    await fn();
    console.log("PASS  " + name);
  } catch (e) {
    var why = e && e.message ? e.message : String(e);
    failures.push({ name: name, why: why });
    console.log("FAIL  " + name + " :: " + why);
  }
}

/* ── the regression cases ─────────────────────────────────────────────── */
async function main() {
  console.log("source: " + sourcePath);
  console.log("source sha256: " + crypto.createHash("sha256").update(Buffer.from(source, "utf8")).digest("hex"));

  /* Ownership race: A then B, each late-A outcome. */
  await runCase("C01 A-then-B: late A success must not displace adopted B", async function () {
    var w = freshWorld("SPY");
    w.pick("SYNA"); w.pick("SYNB");
    await w.settleHard();
    assertEq(w.fetchCalls.length, 2, "transport calls");
    w.fetchCalls[1].resolve({ status: 200, body: synthEntity("SYNB") });
    await w.settleHard();
    assertEq(w.symbol(), "SYNB", "symbol after B adopts");
    w.fetchCalls[0].resolve({ status: 200, body: synthEntity("SYNA") });
    await w.settleHard();
    assertEq(w.symbol(), "SYNB", "symbol after stale A success");
    assertEq(w.renderCalls.length, 1, "adoptions");
    assertEq(w.notice().err, "0", "sx-err");
    assertEq(w.notice().nocov, "0", "sx-nocov");
    assertEq(w.urlSymbol(), "SYNB", "url symbol");
  });

  await runCase("C02 A-then-B: late A transport failure must not raise sx-err over adopted B", async function () {
    var w = freshWorld("SPY");
    w.pick("SYNA"); w.pick("SYNB");
    await w.settleHard();
    w.fetchCalls[1].resolve({ status: 200, body: synthEntity("SYNB") });
    await w.settleHard();
    w.fetchCalls[0].reject(new Error("fixture: transport failure"));
    await w.settleHard();
    assertEq(w.symbol(), "SYNB", "loaded symbol retained");
    assertEq(w.notice().err, "0", "sx-err after stale rejection");
    assertEq(w.notice().nocov, "0", "sx-nocov");
    assertEq(w.renderCalls.length, 1, "adoptions");
  });

  await runCase("C03 A-then-B: late A 404 must not raise sx-nocov over adopted B", async function () {
    var w = freshWorld("SPY");
    w.pick("SYNA"); w.pick("SYNB");
    await w.settleHard();
    w.fetchCalls[1].resolve({ status: 200, body: synthEntity("SYNB") });
    await w.settleHard();
    w.fetchCalls[0].resolve({ status: 404 });
    await w.settleHard();
    assertEq(w.symbol(), "SYNB", "loaded symbol retained");
    assertEq(w.notice().nocov, "0", "sx-nocov after stale 404");
    assertEq(w.notice().err, "0", "sx-err");
    assertEq(w.renderCalls.length, 1, "adoptions");
  });

  /* Ownership race: the decoded body itself arrives late. */
  await runCase("C04 delayed decoded A body after adopted B must not adopt", async function () {
    var w = freshWorld("SPY");
    w.pick("SYNA");
    w.fetchCalls[0].resolve({ status: 200, holdJson: true, body: synthEntity("SYNA") });
    await w.settleHard();
    w.pick("SYNB");
    w.fetchCalls[1].resolve({ status: 200, body: synthEntity("SYNB") });
    await w.settleHard();
    assertEq(w.symbol(), "SYNB", "B adopted");
    assertEq(w.symbol(), "SYNB", "symbol before stale body decodes");
    w.fetchCalls[0].unblockJson();
    await w.settleHard();
    assertEq(w.symbol(), "SYNB", "symbol after stale decoded body");
    assertEq(w.renderCalls.length, 1, "adoptions");
  });

  await runCase("C05 stale decoded body that fails decode must not raise sx-err", async function () {
    var w = freshWorld("SPY");
    w.pick("SYNA");
    w.fetchCalls[0].resolve({ status: 200, holdJson: true, body: synthEntity("SYNA") });
    await w.settleHard();
    w.pick("SYNB");
    w.fetchCalls[1].resolve({ status: 200, body: synthEntity("SYNB") });
    await w.settleHard();
    w.fetchCalls[0].failJson();
    await w.settleHard();
    assertEq(w.notice().err, "0", "sx-err after stale decode failure");
    assertEq(w.notice().nocov, "0", "sx-nocov");
    assertEq(w.symbol(), "SYNB", "loaded symbol retained");
  });

  await runCase("C16 stale response is ignored before reading its JSON body", async function () {
    var w = freshWorld("SPY");
    w.pick("SYNA"); w.pick("SYNB");
    w.fetchCalls[0].resolve({ status: 200, body: synthEntity("SYNA") });
    await w.settleHard();
    assertEq(w.fetchCalls[0].jsonReads || 0, 0, "stale JSON body reads");
    assertEq(w.renderCalls.length, 0, "stale response cannot adopt while B is pending");
    assertEq(w.symbol(), "SPY", "loaded symbol retained until B settles");
    w.fetchCalls[1].resolve({ status: 200, body: synthEntity("SYNB") });
    await w.settleHard();
    assertEq(w.fetchCalls[1].jsonReads, 1, "current JSON body reads");
    assertEq(w.symbol(), "SYNB", "latest symbol adopts normally");
  });

  /* Ownership race: three selections resolved out of order. */
  await runCase("C06 three selections resolved out of order: only the latest owns", async function () {
    var w = freshWorld("SPY");
    w.pick("SYNA"); w.pick("SYNB"); w.pick("SYNC");
    await w.settleHard();
    assertEq(w.fetchCalls.length, 3, "transport calls");
    w.fetchCalls[0].resolve({ status: 200, body: synthEntity("SYNA") });
    await w.settleHard();
    assertEq(w.symbol(), "SPY", "oldest success alone adopts nothing");
    w.fetchCalls[2].resolve({ status: 200, body: synthEntity("SYNC") });
    await w.settleHard();
    assertEq(w.symbol(), "SYNC", "latest success adopts");
    w.fetchCalls[1].resolve({ status: 200, body: synthEntity("SYNB") });
    await w.settleHard();
    assertEq(w.symbol(), "SYNC", "middle success stays stale");
    assertEq(w.renderCalls.length, 1, "adoptions");
    assertEq(w.notice().err, "0", "sx-err");
    assertEq(w.notice().nocov, "0", "sx-nocov");
  });

  /* Ownership vs the already-loaded symbol: SPY is on screen, A pending. */
  await runCase("C07 pending A then already-loaded SPY reselection invalidates A success", async function () {
    var w = freshWorld("SPY");
    w.pick("SYNA");
    w.pick("SPY");
    await w.settleHard();
    w.fetchCalls[0].resolve({ status: 200, body: synthEntity("SYNA") });
    await w.settleHard();
    assertEq(w.symbol(), "SPY", "loaded SPY retained");
    assertEq(w.renderCalls.length, 0, "no adoption");
    assertEq(w.notice().err, "0", "sx-err");
    assertEq(w.notice().nocov, "0", "sx-nocov");
    assertEq(w.urlSymbol(), null, "url untouched by invalidated request");
  });

  await runCase("C08 pending A then already-loaded SPY reselection invalidates A failure", async function () {
    var w = freshWorld("SPY");
    w.pick("SYNA");
    w.pick("SPY");
    await w.settleHard();
    w.fetchCalls[0].reject(new Error("fixture: transport failure"));
    await w.settleHard();
    assertEq(w.symbol(), "SPY", "loaded SPY retained");
    assertEq(w.notice().err, "0", "sx-err after invalidated failure");
    assertEq(w.renderCalls.length, 0, "no adoption");
  });

  await runCase("C09 pending A then already-loaded SPY reselection invalidates A 404", async function () {
    var w = freshWorld("SPY");
    w.pick("SYNA");
    w.pick("SPY");
    await w.settleHard();
    w.fetchCalls[0].resolve({ status: 404 });
    await w.settleHard();
    assertEq(w.symbol(), "SPY", "loaded SPY retained");
    assertEq(w.notice().nocov, "0", "sx-nocov after invalidated 404");
    assertEq(w.renderCalls.length, 0, "no adoption");
  });

  /* Same pending symbol twice: the latest response owns, the first is stale. */
  await runCase("C10 same pending symbol selected twice: superseded response cannot re-adopt", async function () {
    var w = freshWorld("SPY");
    w.pick("SYNA"); w.pick("SYNA");
    await w.settleHard();
    assertEq(w.fetchCalls.length, 2, "transport calls for two selections");
    w.fetchCalls[1].resolve({ status: 200, body: synthEntity("SYNA") });
    await w.settleHard();
    assertEq(w.symbol(), "SYNA", "latest response adopts");
    w.fetchCalls[0].resolve({ status: 200, body: synthEntity("SYNA") });
    await w.settleHard();
    assertEq(w.symbol(), "SYNA", "symbol after superseded response");
    assertEq(w.renderCalls.length, 1, "adoptions for repeated symbol");
  });

  /* Existing behavior pinned: latest 404 / latest failure keep the loaded chart
     and show the existing notice. */
  await runCase("C11 latest 404 retains the loaded entity and shows sx-nocov", async function () {
    var w = freshWorld("SPY");
    w.pick("SYN404");
    await w.settleHard();
    w.fetchCalls[0].resolve({ status: 404 });
    await w.settleHard();
    assertEq(w.notice().nocov, "1", "sx-nocov shown");
    assertEq(w.notice().err, "0", "sx-err stays off");
    assertEq(w.symbol(), "SPY", "loaded entity retained");
    assertEq(w.renderCalls.length, 0, "no adoption");
    assertEq(w.symText(), "", "visible symbol untouched");
  });

  await runCase("C12 latest transport failure retains the loaded entity and shows sx-err", async function () {
    var w = freshWorld("SPY");
    w.pick("SYNNET");
    await w.settleHard();
    w.fetchCalls[0].reject(new Error("fixture: transport failure"));
    await w.settleHard();
    assertEq(w.notice().err, "1", "sx-err shown");
    assertEq(w.notice().nocov, "0", "sx-nocov stays off");
    assertEq(w.symbol(), "SPY", "loaded entity retained");
    assertEq(w.renderCalls.length, 0, "no adoption");
  });

  /* Existing behavior pinned: ordinary latest success. */
  await runCase("C13 ordinary latest success updates identity, URL, and clears notices", async function () {
    var w = freshWorld("SPY");
    w.pick("SYNB");
    await w.settleHard();
    assertEq(w.fetchCalls.length, 1, "transport calls");
    assertEq(w.fetchCalls[0].url, w.expectedUrl("SYNB"), "request URL");
    assertEq(w.fetchCalls[0].opts && w.fetchCalls[0].opts.credentials, "omit", "request credentials option");
    w.fetchCalls[0].resolve({ status: 200, body: synthEntity("SYNB") });
    await w.settleHard();
    assertEq(w.symbol(), "SYNB", "state symbol");
    assertEq(w.symText(), "SYNB", "visible symbol");
    assertEq(w.nameText(), "Synthetic transport fixture SYNB", "visible name");
    assertEq(w.urlSymbol(), "SYNB", "url symbol");
    assertEq(w.notice().err, "0", "sx-err");
    assertEq(w.notice().nocov, "0", "sx-nocov");
    assertEq(w.state().panel, "raw", "panel reset");
    assertEq(w.state().lookback, 0, "lookback reset");
    assertEq(w.state().a, 1, "gate start from shipped default_window");
    assertEq(w.state().b, 31, "gate end from shipped default_window");
    assert(w.closePopCalls() >= 1, "picker closed");
  });

  /* A valid selection of the already-loaded symbol clears obsolete notices. */
  await runCase("C14 valid loaded-symbol reselection clears obsolete notices", async function () {
    var w = freshWorld("SPY");
    w.pick("SYNNET");
    await w.settleHard();
    w.fetchCalls[0].reject(new Error("fixture: transport failure"));
    await w.settleHard();
    assertEq(w.notice().err, "1", "error notice showing");
    w.pick("SYN404");
    await w.settleHard();
    w.fetchCalls[1].resolve({ status: 404 });
    await w.settleHard();
    assertEq(w.notice().nocov, "1", "no-coverage notice showing");
    assertEq(w.notice().err, "0", "error notice cleared by newer selection");
    w.pick("SPY");
    await w.settleHard();
    assertEq(w.notice().err, "0", "error notice cleared by loaded-symbol reselection");
    assertEq(w.notice().nocov, "0", "no-coverage notice cleared by loaded-symbol reselection");
    assertEq(w.symbol(), "SPY", "loaded entity retained");
    assertEq(w.renderCalls.length, 0, "no adoption");
  });

  /* Only a NONEMPTY selection may take ownership. */
  await runCase("C15 empty selection must not steal ownership from a pending request", async function () {
    var w = freshWorld("SPY");
    w.pick("SYNA");
    await w.settleHard();
    w.pick(null);
    w.pick("");
    await w.settleHard();
    w.fetchCalls[0].resolve({ status: 200, body: synthEntity("SYNA") });
    await w.settleHard();
    assertEq(w.symbol(), "SYNA", "pending request still owns after empty selections");
    assertEq(w.renderCalls.length, 1, "adoptions");
    assertEq(w.fetchCalls.length, 1, "no transport for empty selections");
  });

  var passed = caseCount - failures.length;
  console.log("cases: " + passed + " passed, " + failures.length + " failed of " + caseCount);
  console.log("RESULT: " + passed + "/" + caseCount + " passed");
  if (failures.length) process.exit(1);
}

main().catch(function (e) {
  console.error("harness crashed: " + (e && e.stack || e));
  process.exit(1);
});
