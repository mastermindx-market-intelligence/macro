/* Presentation regressions using a deliberately synthetic return fixture. */
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const {JSDOM} = require("jsdom");
const root = path.resolve(__dirname, "..");
const api = require(path.join(root, "templates/commodity-workspace.js"));

assert.equal(api.returnScale([null, undefined, NaN, Infinity, "9", -10, 5, 0]), 10);
assert.deepEqual(api.returnGeometry(-5, 10), {available:true, direction:"negative", width:25});
assert.deepEqual(api.returnGeometry(0, 0), {available:true, direction:"flat", width:0});
for (const missing of [null, undefined, NaN, Infinity, "0"]) {
  assert.deepEqual(api.returnGeometry(missing, 10), {available:false, direction:"unavailable", width:0});
}

const html = fs.readFileSync(path.join(root, "site/commodities.html"), "utf8");
const dom = new JSDOM(html, {url:"https://www.mastermind-x.com/commodities.html#cw/compare/oil?window=1m&compare=oil%2Cgold", runScripts:"outside-only"});
const w = dom.window, d = w.document;
w.HTMLElement.prototype.scrollIntoView = function() {};
w.scrollTo = function() {};
const payload = d.getElementById("cw-data"), data = JSON.parse(payload.textContent);
Object.assign(data.assets.find(a => a.id === "oil"), {change_1m_pct:0, returns:{"5":null,"20":5,"60":null,"252":1}});
Object.assign(data.assets.find(a => a.id === "gold"), {change_1m_pct:null, returns:{"5":null,"20":-10,"60":0,"252":2}});
payload.textContent = JSON.stringify(data);
w.eval(fs.readFileSync(path.join(root, "templates/commodity-workspace.js"), "utf8"));
const q = selector => {const node = d.querySelector(selector); assert.ok(node, selector); return node;};
const change = (selector, value) => {const node=q(selector); node.value=value; node.dispatchEvent(new w.Event("change", {bubbles:true}));};
const mark = asset => q('[data-cw-compare-plot="'+asset+'"] [data-cw-plot-mark]');
const note = () => q("[data-cw-note-window]").textContent;

(async () => {
  change("[data-cw-window]", "20");
  assert.equal(mark("oil").style.width, "25%");
  assert.equal(mark("gold").style.width, "50%");
  assert.ok(mark("gold").classList.contains("cw-bar-negative"));
  change("[data-cw-window]", "60");
  assert.equal(mark("oil").hidden, true);
  assert.equal(mark("gold").hidden, false);
  assert.equal(mark("gold").style.width, "0%");
  assert.equal(q('[data-cw-compare-plot="gold"] [data-cw-plot-value]').textContent, "0.0%");
  q('[data-cw-compare][value="oil"]').click();
  q('[data-cw-compare][value="gold"]').click();
  assert.equal(q("[data-cw-compare-empty]").hidden, false);
  assert.equal(q(".cw-plot-axis").hidden, true);
  assert.equal(d.querySelectorAll("[data-cw-compare-plot]:not([hidden])").length, 0);

  q("#cw-tab-research").click();
  // A browse-window change must not silently choose the research draft window.
  assert.equal(note(), "Choose a lookback window");
  change('[name="window_sessions"]', "252");
  assert.equal(note(), "252 trading sessions");
  change('#cw-research-form [name="asset"]', "gold");
  change('#cw-research-form [name="asset"]', "oil");
  assert.equal(q('[name="window_sessions"]').value, "252");
  assert.equal(note(), "252 trading sessions");
  d.documentElement.setAttribute("data-lang", "zh");
  await new Promise(resolve => setTimeout(resolve, 10));
  assert.equal(note(), "252个交易日");
  console.log("PASS signed shared scale, null/zero distinction, empty selection, draft context and language");
})().catch(error => {console.error(error);process.exitCode=1;});
