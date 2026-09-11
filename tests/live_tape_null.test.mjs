// W9 r1 / M2: live.js patchPriceNode null branch.
// Isolated from live_tape.test.mjs so a pre-existing ^TNX toFixed rounding
// mismatch on this Node cannot swallow the probe.
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import vm from "node:vm";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const SRC = fs.readFileSync(path.join(HERE, "..", "templates", "live.js"), "utf8");

function makeEl(attrs, cls) {
  const a = Object.assign({}, attrs);
  const classes = new Set((cls || "").split(/\s+/).filter(Boolean));
  return {
    _attrs: a,
    textContent: "",
    innerHTML: "",
    title: "stale leftover",
    parentNode: null,
    getAttribute: (k) => (k in a ? a[k] : null),
    setAttribute: (k, v) => { a[k] = String(v); },
    removeAttribute: (k) => { delete a[k]; },
    hasAttribute: (k) => k in a,
    classList: {
      add: (...c) => c.forEach((x) => classes.add(x)),
      remove: (...c) => c.forEach((x) => classes.delete(x)),
      contains: (x) => classes.has(x),
    },
    closest: () => null,
    querySelector: () => null,
    appendChild: () => {},
    _classes: classes,
  };
}

const esPx = makeEl({ "data-sym": "ES=F", "data-mkt": "us", "data-bare": "" }, "mx5-mkt-price nb-px skel");
const ALL = [esPx];
function matchSel(sel) {
  const wantPx = sel.includes("nb-px");
  const wantChg = sel.includes("nb-chg");
  return ALL.filter((el) => {
    const isPx = el._classes.has("nb-px");
    const isChg = el._classes.has("nb-chg");
    return (wantPx && isPx) || (wantChg && isChg);
  });
}

let wsInstance = null;
class FakeWebSocket {
  constructor(url) { this.url = url; wsInstance = this; setTimeout(() => this.onopen && this.onopen(), 0); }
  close() {}
}

const listeners = {};
const documentStub = {
  readyState: "complete",
  hidden: false,
  documentElement: { getAttribute: () => "en" },
  head: { appendChild: () => {} },
  getElementById: () => null,
  createElement: () => ({ id: "", textContent: "", setAttribute: () => {} }),
  querySelectorAll: (sel) => matchSel(sel),
  addEventListener: (ev, fn) => { (listeners[ev] = listeners[ev] || []).push(fn); },
};

const windowStub = {
  LIVE_ENABLED: true,
  LIVE_POLL_SEC: 999999,
  LIVE_DELAYED_MIN: 0,
  LIVE_WS_TAPE: true,
  WebSocket: FakeWebSocket,
  setInterval: () => 0,
  clearInterval: () => {},
  setTimeout: (fn, ms) => setTimeout(fn, ms),
  clearTimeout: (id) => clearTimeout(id),
  location: { protocol: "https:", host: "www.example.com" },
  localStorage: { removeItem: () => {}, getItem: () => null, setItem: () => {} },
};
windowStub.window = windowStub;

const ctx = {
  window: windowStub,
  document: documentStub,
  WebSocket: FakeWebSocket,
  fetch: async () => ({ ok: true, json: async () => null }),
  setInterval: windowStub.setInterval,
  clearInterval: windowStub.clearInterval,
  setTimeout: windowStub.setTimeout,
  clearTimeout: windowStub.clearTimeout,
  location: windowStub.location,
  Date, Math, Number, JSON, Promise, Object, console,
};
vm.createContext(ctx);
vm.runInContext(SRC, ctx);

await new Promise((r) => setTimeout(r, 5));
assert.ok(wsInstance, "live.js should have opened a /ws/tape socket");

wsInstance.onmessage({ data: JSON.stringify({ sym: "ES=F", price: null, ts: Date.now(), basis: "quote" }) });
assert.ok(esPx._classes.has("dtp-token"), "null tape quote should add dtp-token");
assert.ok(esPx._classes.has("behind"), "null tape quote should add behind");
assert.ok(!esPx._classes.has("skel"), "null tape quote should drop the loading skeleton");
assert.equal(esPx.getAttribute("data-live"), "behind");
assert.equal(esPx.title, "", "null tape quote must not use an EN-only title=");
assert.match(esPx.innerHTML, /Quotes unavailable — the rest of this page is unaffected\./);
assert.match(esPx.innerHTML, /行情暂不可用——本页其余内容不受影响。/);

console.log("live_tape_null.test.mjs: all assertions passed");
