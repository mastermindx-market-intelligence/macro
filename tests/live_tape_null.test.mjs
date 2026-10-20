// W9 r2 / B1: live.js null-tape is Markets-only; nav ticker is a silent no-op.
// Real-DOM fixture (parent chain + closest), not a stub that pins closest:null.
// Isolated from live_tape.test.mjs so a pre-existing ^TNX toFixed rounding
// mismatch on this Node cannot swallow the probe.
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import vm from "node:vm";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const SRC = fs.readFileSync(path.join(HERE, "..", "templates", "live.js"), "utf8");

function matchSimple(el, sel) {
  sel = String(sel || "").trim();
  if (!sel) return false;
  if (sel.startsWith("#")) return el.id === sel.slice(1);
  const classes = [];
  const attrs = [];
  const classRe = /\.([A-Za-z][\w-]*)/g;
  let m;
  while ((m = classRe.exec(sel))) classes.push(m[1]);
  const attrRe = /\[([^\]]+)\]/g;
  while ((m = attrRe.exec(sel))) attrs.push(m[1]);
  for (const c of classes) if (!el._classes.has(c)) return false;
  for (const raw of attrs) {
    const eq = raw.indexOf("=");
    if (eq < 0) {
      if (!el.hasAttribute(raw)) return false;
    } else {
      const k = raw.slice(0, eq);
      const v = raw.slice(eq + 1).replace(/^['"]|['"]$/g, "");
      if (String(el.getAttribute(k)) !== v) return false;
    }
  }
  return classes.length > 0 || attrs.length > 0;
}

function makeEl(attrs, cls, extra) {
  const a = Object.assign({}, attrs || {});
  const classes = new Set(String(cls || "").split(/\s+/).filter(Boolean));
  const kids = [];
  let text = (extra && extra.textContent) || "";
  let html = (extra && extra.innerHTML) || text;
  const el = {
    id: (extra && extra.id) || a.id || "",
    parentNode: null,
    title: (extra && extra.title) || "",
    _attrs: a,
    _classes: classes,
    _kids: kids,
    get textContent() { return text; },
    set textContent(v) { text = v == null ? "" : String(v); html = text; },
    get innerHTML() { return html; },
    set innerHTML(v) { html = v == null ? "" : String(v); },
    get className() { return [...classes].join(" "); },
    set className(v) {
      classes.clear();
      String(v || "").split(/\s+/).filter(Boolean).forEach((x) => classes.add(x));
    },
    getAttribute: (k) => (k === "id" ? (el.id || null) : (k in a ? a[k] : null)),
    setAttribute: (k, v) => {
      a[k] = String(v);
      if (k === "id") el.id = String(v);
    },
    removeAttribute: (k) => { delete a[k]; },
    hasAttribute: (k) => k === "id" ? Boolean(el.id) : k in a,
    classList: {
      add: (...c) => c.forEach((x) => classes.add(x)),
      remove: (...c) => c.forEach((x) => classes.delete(x)),
      contains: (x) => classes.has(x),
    },
    appendChild(child) {
      kids.push(child);
      child.parentNode = el;
      return child;
    },
    querySelector(sel) {
      const all = el.querySelectorAll(sel);
      return all[0] || null;
    },
    querySelectorAll(sel) {
      const parts = String(sel).split(",").map((s) => s.trim()).filter(Boolean);
      const out = [];
      const seen = new Set();
      const walk = (n) => {
        (n._kids || []).forEach((c) => {
          if (parts.some((p) => matchSimple(c, p)) && !seen.has(c)) {
            seen.add(c);
            out.push(c);
          }
          walk(c);
        });
      };
      walk(el);
      return out;
    },
    closest(sel) {
      let n = el;
      while (n) {
        if (matchSimple(n, sel) || (sel.startsWith("#") && n.id === sel.slice(1))) return n;
        n = n.parentNode;
      }
      return null;
    },
  };
  if (el.id) a.id = el.id;
  return el;
}

const docRoot = makeEl({}, "", { id: "document-root" });
const markets = makeEl({}, "", { id: "sx-markets-v2" });
const mktPx = makeEl(
  { "data-sym": "ES=F", "data-mkt": "us", "data-bare": "" },
  "mx5-mkt-price nb-px skel",
);
mktPx.setAttribute("aria-busy", "true");
markets.appendChild(mktPx);

const NAV_PREV = "6,712.25";
const nav = makeEl({}, "nb-tape", { id: "nb-tape" });
const navPx = makeEl({ "data-sym": "ES=F" }, "nb-px");
navPx.textContent = NAV_PREV;
navPx.innerHTML = NAV_PREV;
nav.appendChild(navPx);

docRoot.appendChild(markets);
docRoot.appendChild(nav);

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
  getElementById: (id) => {
    if (id === "sx-markets-v2") return markets;
    return null;
  },
  createElement: () => makeEl({}, ""),
  querySelectorAll: (sel) => docRoot.querySelectorAll(sel),
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

// (a) #sx-markets-v2 tile → packet null design
assert.ok(mktPx.closest("#sx-markets-v2") === markets, "markets tile closest must resolve");
assert.ok(mktPx._classes.has("dtp-token"), "null tape quote should add dtp-token");
assert.ok(mktPx._classes.has("behind"), "null tape quote should add behind");
assert.ok(!mktPx._classes.has("skel"), "null tape quote should drop the loading skeleton");
assert.equal(mktPx.getAttribute("data-live"), "behind");
assert.equal(mktPx.title, "", "null tape quote must not use an EN-only title=");
assert.equal(mktPx.textContent, "—", "behind glyph so .dtp-token.behind has content to tint");
assert.match(mktPx.innerHTML, /—/);
const nullLine = markets.querySelector(".mx-mkt-null");
assert.ok(nullLine, "packet empty line mounts inside #sx-markets-v2");
assert.ok(nullLine._classes.has("mx-empty"), "empty line carries .mx-empty");
assert.match(nullLine.innerHTML, /mx-empty-why/, "packet plain line is the required why");
assert.match(nullLine.innerHTML, /Quotes unavailable — the rest of this page is unaffected\./);
assert.match(nullLine.innerHTML, /行情暂不可用——本页其余内容不受影响。/);
assert.equal(nullLine.parentNode, markets);

// (b) nav-ticker node OUTSIDE #sx-markets-v2 → pinned NO-OP
assert.equal(navPx.closest("#sx-markets-v2"), null, "nav ticker is outside Markets");
assert.equal(navPx.innerHTML, NAV_PREV, "nav ticker innerHTML must stay at the previous rendering");
assert.equal(navPx.textContent, NAV_PREV, "nav ticker textContent must stay at the previous rendering");
assert.ok(!navPx._classes.has("dtp-token"), "nav ticker must not gain dtp-token");
assert.ok(!navPx._classes.has("behind"), "nav ticker must not gain behind");
assert.equal(navPx.getAttribute("data-live"), null, "nav ticker must not be stamped behind");

console.log("live_tape_null.test.mjs: all assertions passed");
console.log("nav-ticker NO-OP pin: innerHTML unchanged at", JSON.stringify(NAV_PREV));
console.log("markets null branch: mx-empty-why + bilingual packet line mounted under #sx-markets-v2");
