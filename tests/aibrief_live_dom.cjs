/* Browser DOM contract checks. Run with jsdom and fixtures emitted from the
   actual Jinja/view implementation; this is not production browser proof.
   AIBRIEF_JSDOM=/path/to/jsdom node tests/aibrief_live_dom.cjs fixtures.json */
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const {JSDOM} = require(process.env.AIBRIEF_JSDOM || "jsdom");
const fixtures = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const code = fs.readFileSync(path.join(__dirname, "../templates/aibrief.js"), "utf8");
const pause = () => new Promise(resolve => setTimeout(resolve, 25));
const response = (body, status = 200) => new Response(JSON.stringify(body), {
  status, headers: {"Content-Type": "application/json"}
});

async function boot(fetcher, html = fixtures.old) {
  const dom = new JSDOM("<!doctype html><html><body>" + html + "</body></html>", {
    url: "https://www.mastermind-x.com/macro.html", runScripts: "outside-only", pretendToBeVisual: true
  });
  const w = dom.window, intervals = [], deadlines = [], calls = [];
  w.Element.prototype.getClientRects = function () { return this.isConnected ? [{}] : []; };
  w.TextDecoder = TextDecoder;
  w.setInterval = fn => { intervals.push(fn); return intervals.length; };
  w.setTimeout = (fn, ms) => { deadlines.push({fn, ms}); return deadlines.length; };
  w.clearTimeout = () => {};
  w.requestAnimationFrame = fn => { fn(); return 0; };
  w.fetch = (url, options) => { calls.push({url, options}); return fetcher(url, options); };
  w.eval(code);
  await pause();
  return {w, dom, intervals, deadlines, calls, root: () => w.document.querySelector(".aib2")};
}

(async () => {
  let t = await boot(() => Promise.reject(new Error("offline")));
  assert.equal(t.root().dataset.status, "stale");
  assert.match(t.root().textContent, /AI update overdue/);
  assert.equal(t.root().querySelector("details").open, false);
  assert.doesNotMatch(t.root().textContent, /Updated daily/);
  t.dom.window.close();

  t = await boot(() => Promise.resolve(response(fixtures.fresh)));
  assert.equal(t.root().dataset.status, "available");
  assert.match(t.root().textContent, /Current qualified read/);
  assert.equal(t.calls[0].url, "/api/aibrief/v1/macro");
  assert.equal(t.calls[0].options.credentials, "same-origin");
  assert.equal(t.calls[0].options.cache, "no-store");
  t.root().__aibDeadline = -1;
  t.intervals[0]();
  assert.equal(t.root().dataset.status, "stale");
  assert.equal(t.root().querySelector("details").open, false);
  t.dom.window.close();

  t = await boot(() => Promise.resolve(response({}, 401)));
  assert.equal(t.root().querySelector(".aib2-content"), null);
  assert.equal(t.root().querySelector(".aib2-retained"), null);
  assert.match(t.root().textContent, /Sign in/);
  t.intervals[0]();
  assert.match(t.root().textContent, /Sign in/);
  t.dom.window.close();

  const attack = {...fixtures.fresh, html: fixtures.fresh.html.replace("Current qualified read", '<img src="x" onerror="alert(1)">')};
  t = await boot(() => Promise.resolve(response(attack)));
  assert.equal(t.root().dataset.status, "stale");
  assert.equal(t.root().querySelector("img"), null);
  t.dom.window.close();

  let release;
  t = await boot(() => new Promise(resolve => { release = resolve; }));
  for (let i = 0; i < 4; i++) t.w.document.dispatchEvent(new t.w.MouseEvent("click"));
  assert.equal(t.calls.length, 1);
  t.deadlines.find(row => row.ms === 10000).fn();
  release(response(fixtures.fresh));
  await pause();
  assert.equal(t.root().dataset.status, "stale"); // Late reply after abort cannot paint.
  t.dom.window.close();

  t = await boot(() => Promise.resolve(response({...fixtures.fresh,
    server_time: new Date(Date.now() - 3600000).toISOString()})));
  assert.equal(t.root().dataset.status, "stale"); // Cached API body cannot mint a new lifetime.
  t.dom.window.close();

  t = await boot(() => Promise.resolve(response({...fixtures.fresh, sequence: 1})),
    fixtures.old.replace('data-sequence="0"', 'data-sequence="5"'));
  assert.equal(t.root().dataset.sequence, "5");
  assert.doesNotMatch(t.root().textContent, /Current qualified read/);
  t.dom.window.close();

  t = await boot(() => Promise.resolve(response(fixtures.fresh)));
  for (let i = 0; i < 4; i++) t.w.document.dispatchEvent(new t.w.MouseEvent("click"));
  await pause();
  assert.equal(t.calls.length, 1); // A dialog interaction cannot flood the read API.
  t.dom.window.close();
  console.log("8 AI Brief DOM scenarios passed");
})().catch(error => { console.error(error); process.exitCode = 1; });
