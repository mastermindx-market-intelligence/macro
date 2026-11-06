// Execute the shipped live client against a controlled DOM and exchange clock.
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import test from "node:test";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const SRC = fs.readFileSync(path.join(ROOT, "templates/live.js"), "utf8");
const NOW = Date.parse("2026-10-07T02:00:00Z");

function matches(el, selector) {
  const s = selector.trim();
  const tag = s.match(/^[a-z]+/i);
  if (tag && el.tagName !== tag[0].toUpperCase()) return false;
  const id = s.match(/#([\w-]+)/);
  if (id && el.id !== id[1]) return false;
  for (const m of s.matchAll(/\.([\w-]+)/g)) if (!el.classList.contains(m[1])) return false;
  for (const m of s.matchAll(/\[([\w-]+)(?:=['"]?([^\]'"]+)['"]?)?\]/g)) {
    if (!el.hasAttribute(m[1])) return false;
    if (m[2] !== undefined && el.getAttribute(m[1]) !== m[2]) return false;
  }
  return true;
}

function element(tag = "div", attrs = {}, text = "") {
  const a = { ...attrs }, classes = new Set((a.class || "").split(/\s+/).filter(Boolean));
  const children = [];
  let ownText = text, ownHtml = null;
  const el = {
    tagName: tag.toUpperCase(), parentNode: null, children, style: {},
    get id() { return a.id || ""; }, set id(v) { a.id = String(v); },
    get className() { return [...classes].join(" "); },
    set className(v) { classes.clear(); String(v).split(/\s+/).filter(Boolean).forEach(x => classes.add(x)); },
    get textContent() { return ownText + children.map(c => c.textContent).join(""); },
    set textContent(v) { ownText = String(v ?? ""); ownHtml = null; children.length = 0; },
    get innerHTML() { return ownHtml ?? ownText + children.map(c => c.outerHTML).join(""); },
    set innerHTML(v) {
      ownHtml = String(v); ownText = ""; children.length = 0;
      const stack = [el];
      for (const token of ownHtml.match(/<[^>]*>|[^<]+/g) || []) {
        if (token.startsWith("</")) { if (stack.length > 1) stack.pop(); continue; }
        if (token.startsWith("<")) {
          const name = token.match(/^<([\w-]+)/)?.[1]; if (!name) continue;
          const attrs = {};
          for (const m of token.matchAll(/([\w-]+)="([^"]*)"/g)) attrs[m[1]] = m[2];
          const child = element(name, attrs); stack.at(-1).appendChild(child); stack.push(child);
        } else stack.at(-1).appendChild(element("text", {}, token));
      }
    },
    get outerHTML() { return "<" + tag + ">" + el.innerHTML + "</" + tag + ">"; },
    get firstChild() { return children[0] || null; },
    get firstElementChild() { return children[0] || null; },
    get nextSibling() { const p = el.parentNode; return p ? p.children[p.children.indexOf(el) + 1] || null : null; },
    get title() { return a.title || ""; }, set title(v) { a.title = String(v); },
    classList: {
      add: (...v) => v.forEach(x => classes.add(x)),
      remove: (...v) => v.forEach(x => classes.delete(x)),
      contains: x => classes.has(x),
      toggle: (x, on) => { if (on ?? !classes.has(x)) classes.add(x); else classes.delete(x); },
    },
    getAttribute: k => k === "class" ? el.className : (a[k] ?? null),
    setAttribute: (k, v) => { if (k === "class") el.className = v; else a[k] = String(v); },
    removeAttribute: k => { delete a[k]; },
    hasAttribute: k => k === "class" ? Boolean(el.className) : Object.hasOwn(a, k),
    appendChild(child) { return el.insertBefore(child, null); },
    insertBefore(child, before) {
      if (child.parentNode) child.parentNode.removeChild(child);
      const idx = before ? children.indexOf(before) : children.length;
      children.splice(idx < 0 ? children.length : idx, 0, child); child.parentNode = el; return child;
    },
    removeChild(child) { const i = children.indexOf(child); if (i >= 0) children.splice(i, 1); child.parentNode = null; },
    remove() { if (el.parentNode) el.parentNode.removeChild(el); },
    querySelectorAll(selector) {
      const out = [], selectors = selector.split(",");
      function walk(n) { n.children.forEach(c => { if (selectors.some(s => matches(c, s))) out.push(c); walk(c); }); }
      walk(el); return out;
    },
    querySelector: selector => el.querySelectorAll(selector)[0] || null,
    closest(selector) { for (let n = el; n; n = n.parentNode) if (matches(n, selector)) return n; return null; },
  };
  return el;
}

function session(region = "cn", extra = {}) {
  return {
    region, open: false, state: "holiday", timezone: "Asia/Shanghai",
    local_time: "2026-10-07T10:00:00+08:00", session_date: "2026-10-07",
    holiday_name: "National Day", holiday_name_zh: "国庆节",
    expected_session: "2026-09-30", next_open: "2026-10-08T09:30:00+08:00",
    calendar_verified: true, checked_at: "2026-10-07T01:59:00Z",
    valid_until: "2026-10-07T03:00:00Z", data_frozen: true, early_close: false,
    source_urls: ["https://www.sse.com.cn/official-calendar"], ...extra,
  };
}
function entry(extra = {}) {
  return {
    price: 10, source: "tencent", quote_ts: "2026-09-30T07:00:00Z",
    data_through: "2026-09-30", data_frozen: true, data_state: "current",
    session_state: "holiday", stale: true, ...extra,
  };
}
function quote(price = 99, extra = {}) {
  return { price, source: "tencent", ts: NOW, prevClose: 10, changePct: 890, delayMin: 0, ...extra };
}
async function client({ pathname = "/china_stocks.html", symbols = ["600519.SS"], sessions = { cn: session() }, tickers = {}, quotes, ws = false, snapshotSessions, overlay, workerQuotes, rowDates = {} } = {}) {
  let now = NOW;
  const root = element("html", { "data-lang": "en" });
  const head = root.appendChild(element("head")), body = root.appendChild(element("body"));
  const nav = body.appendChild(element("nav", { class: "site-nav" }));
  const main = body.appendChild(element("main"));
  const px = {}, chg = {};
  for (const sym of symbols) {
    const row = main.appendChild(element("div"));
    const mkt = /\.HK$/.test(sym) ? "hk" : /\.(SS|SZ|BJ)$/.test(sym) ? "cn" : /\.(TO|V)$/.test(sym) ? "ca" : "us";
    px[sym] = row.appendChild(element("span", { class: "nb-px", "data-sym": sym, "data-mkt": mkt, ...(rowDates[sym] ? { "data-through": rowDates[sym] } : {}) }, "10.00"));
    chg[sym] = row.appendChild(element("span", { class: "nb-chg up", "data-sym": sym, "data-mkt": mkt }, "+1.00%"));
    row.appendChild(element("span", { class: "nb-dvg alert" }, "old divergence"));
  }
  const events = {}, intervals = [];
  const response = {
    quotes: quotes ?? Object.fromEntries(symbols.map(s => [s, quote()])), quoteTs: NOW,
    overlay: overlay === undefined ? { sessions, tickers } : overlay,
    snapshotSessions,
    worker: workerQuotes === null ? null : { quotes: workerQuotes, ts: NOW },
  };
  const requests = [], sockets = [];
  class Clock extends Date { constructor(...args) { super(...(args.length ? args : [now])); } static now() { return now; } }
  class Socket { constructor(url) { this.url = url; sockets.push(this); } close() {} }
  const document = {
    documentElement: root, body, head, readyState: "complete", hidden: false,
    createElement: tag => element(tag),
    getElementById: id => root.querySelector("#" + id),
    querySelector: s => root.querySelector(s), querySelectorAll: s => root.querySelectorAll(s),
    addEventListener: (name, fn) => { (events[name] ??= []).push(fn); },
  };
  const location = { pathname, protocol: "https:", host: "example.test" };
  const window = {
    LIVE_ENABLED: true, LIVE_SNAPSHOT_URL: "live/quotes.json", LIVE_DELAYED_MIN: 0,
    LIVE_POLL_SEC: 60, LIVE_WS_TAPE: ws, location, WebSocket: Socket,
    LIVE_QUOTES_URL: workerQuotes === undefined ? "" : "https://worker.test",
  };
  const context = {
    window, document, location, Date: Clock, WebSocket: Socket,
    setInterval: fn => { intervals.push(fn); return intervals.length; }, clearInterval() {},
    setTimeout: () => 1, clearTimeout() {}, localStorage: { removeItem() {} },
    fetch: async url => {
      requests.push(url);
      const data = url.includes("overlay.json") ? response.overlay
        : url.startsWith("https://worker.test") ? response.worker
        : { quotes: response.quotes, ts: response.quoteTs, sessions: response.snapshotSessions };
      return { ok: data !== null, json: async () => data };
    },
    console,
  };
  vm.runInNewContext(SRC, context);
  async function flush() { await new Promise(resolve => setImmediate(resolve)); }
  await flush();
  return {
    root, nav, main, px, chg, requests, response, sockets,
    strip: () => document.getElementById("market-session-status"),
    async refresh() { window.LiveQuotes.refresh(); await flush(); },
    async advance(ms) { now += ms; intervals.forEach(fn => fn()); await flush(); },
    language(lang) { root.setAttribute("data-lang", lang); (events.langchange || []).forEach(fn => fn()); },
  };
}

test("verified holiday beats a fresh retrieval and preserves baseline, percent and true provenance", async () => {
  const c = await client({ tickers: { "600519.SS": entry() } });
  assert.equal(c.px["600519.SS"].textContent, "10.00");
  assert.equal(c.chg["600519.SS"].textContent, "+1.00%");
  assert.equal(c.px["600519.SS"].getAttribute("data-live"), "closed");
  assert.equal(c.px["600519.SS"].getAttribute("data-through"), "2026-09-30");
  assert.equal(c.px["600519.SS"].getAttribute("data-quote-ts"), "2026-09-30T07:00:00Z");
  assert.match(c.px["600519.SS"].getAttribute("data-tip-en"), /tencent/);
  assert.equal(c.main.querySelectorAll(".nb-dvg").length, 0);
  const strip = c.strip();
  assert.ok(strip); assert.equal(strip.getAttribute("role"), "status");
  assert.match(strip.textContent, /National Day/); assert.match(strip.textContent, /国庆节/);
  assert.match(strip.textContent, /2026-09-30/); assert.match(strip.textContent, /2026-10-08/);
  assert.match(strip.textContent, /09:30/);
  assert.ok(strip.querySelector(".l-en")); assert.ok(strip.querySelector(".l-zh"));
});

test("holiday does not erase missing, invalid or late data", async () => {
  for (const state of ["missing", "invalid", "late"]) {
    const c = await client({ tickers: { "600519.SS": entry({ data_state: state, data_through: state === "late" ? "2026-09-29" : null }) } });
    assert.equal(c.px["600519.SS"].getAttribute("data-data-state"), state);
    assert.notEqual(c.px["600519.SS"].getAttribute("data-live"), "closed");
    assert.match(c.px["600519.SS"].getAttribute("data-tip-en"), /closed/i);
    assert.match(c.px["600519.SS"].getAttribute("data-tip-en"), new RegExp(state, "i"));
    assert.match(c.strip().textContent, new RegExp("prices " + state, "i"));
    assert.equal(c.px["600519.SS"].textContent, "10.00");
  }
});

test("missing quote still receives an honest holiday/data badge without clearing carried display", async () => {
  const c = await client({ quotes: {}, tickers: { "600519.SS": entry({ price: null, data_state: "missing" }) } });
  assert.equal(c.px["600519.SS"].textContent, "10.00");
  assert.equal(c.px["600519.SS"].getAttribute("data-data-state"), "missing");
  assert.equal(c.px["600519.SS"].getAttribute("data-live"), "behind");
});

test("calendar expiry cannot remain an asserted closure or live status when fetch fails", async () => {
  const c = await client({ tickers: { "600519.SS": entry() } });
  c.response.overlay = null;
  await c.advance(61 * 60000);
  assert.equal(c.px["600519.SS"].getAttribute("data-session-state"), "unverified");
  assert.equal(c.px["600519.SS"].getAttribute("data-live"), "behind");
  assert.match(c.strip().textContent, /unverified/i);
  assert.match(c.strip().textContent, /未确认/);
});

test("unknown calendar coverage keeps display and identifies the missing authority", async () => {
  const c = await client({ sessions: { cn: session("cn", { state: "unverified", open: null, calendar_verified: false, data_frozen: false }) } });
  assert.equal(c.px["600519.SS"].textContent, "10.00");
  assert.equal(c.px["600519.SS"].getAttribute("data-live"), "behind");
  assert.equal(c.px["600519.SS"].getAttribute("data-session-state"), "unverified");
});

test("noncash and unknown foreign symbols never inherit a US holiday freeze", async () => {
  const symbols = ["AAPL", "ES=F", "EURUSD=X", "BTC-USD", "BTC-EUR", "7203.T", "UNKNOWN.B", "^UNKNOWN", "^TNX", "DX-Y.NYB"];
  const c = await client({ pathname: "/us_stocks.html", symbols, sessions: { us: session("us") } });
  assert.equal(c.px.AAPL.textContent, "10.00");
  for (const sym of symbols.slice(1)) {
    assert.notEqual(c.px[sym].textContent, "10.00", sym);
    assert.notEqual(c.px[sym].getAttribute("data-live"), "closed", sym);
  }
});

test("all supported cash suffixes and known equity indices use their own session", async () => {
  const symbols = ["000001.SZ", "430047.BJ", "0700.HK", "SHOP.TO", "ABC.V", "^HSI", "^HSCC", "^HSIL", "^GSPC", "^VIX", "BRK.B", "^GSPTSE", "^SPCDNX"];
  const c = await client({ symbols, sessions: { cn: session(), hk: session("hk"), us: session("us"), ca: session("ca") },
    quotes: Object.fromEntries(symbols.map(sym => [sym, quote(99, { ts: Date.parse("2026-09-30T07:00:00Z") })])) });
  for (const sym of symbols) assert.equal(c.px[sym].getAttribute("data-live"), "closed", sym);
});

test("Hong Kong stays live while a differing Connect closure appears separately", async () => {
  const c = await client({
    pathname: "/hk_stocks.html", symbols: ["0700.HK"],
    sessions: {
      hk: session("hk", { state: "open", open: true, data_frozen: false, holiday_name: null, holiday_name_zh: null, timezone: "Asia/Hong_Kong" }),
      connect: session("connect"),
    },
  });
  assert.equal(c.px["0700.HK"].textContent, "99.00");
  assert.equal(c.px["0700.HK"].getAttribute("data-live"), "1");
  assert.match(c.strip().textContent, /Stock Connect/);
  assert.match(c.strip().textContent, /互联互通/);
  assert.match(c.strip().textContent, /National Day/);
});

test("reopening refresh resumes price updates and does not duplicate the bilingual strip", async () => {
  const c = await client({ tickers: { "600519.SS": entry() } });
  c.response.overlay = { sessions: { cn: session("cn", { state: "open", open: true, data_frozen: false, holiday_name: null, holiday_name_zh: null, checked_at: "2026-10-07T02:00:00Z" }) }, tickers: {} };
  await c.refresh(); await c.refresh(); c.language("zh");
  assert.equal(c.px["600519.SS"].textContent, "99.00");
  assert.equal(c.px["600519.SS"].getAttribute("data-live"), "1");
  assert.equal(c.px["600519.SS"].getAttribute("data-through"), null);
  assert.equal(c.px["600519.SS"].getAttribute("data-quote-ts"), "2026-10-07T02:00:00.000Z");
  assert.equal(c.root.querySelectorAll("#market-session-status").length, 1);
  assert.match(c.strip().textContent, /交易中/);
});

test("the regional strip fetches the same overlay even on a page without quote nodes", async () => {
  const c = await client({ symbols: [], pathname: "/canada.html", sessions: { ca: session("ca", { holiday_name: "Thanksgiving", holiday_name_zh: "感恩节", timezone: "America/Toronto" }) } });
  assert.ok(c.requests.includes("live/overlay.json"));
  assert.match(c.strip().textContent, /Thanksgiving/);
});

test("equity websocket frames cannot bypass closure while futures remain independently live", async () => {
  const c = await client({ pathname: "/us_stocks.html", symbols: ["AAPL", "ES=F"], sessions: { us: session("us") }, ws: true });
  assert.equal(c.sockets.length, 1);
  c.sockets[0].onmessage({ data: JSON.stringify({ sym: "AAPL", price: 888, ts: NOW, basis: "quote" }) });
  assert.equal(c.px.AAPL.textContent, "10.00");
  c.sockets[0].onmessage({ data: JSON.stringify({ sym: "ES=F", price: 321, ts: NOW, basis: "quote" }) });
  assert.match(c.px["ES=F"].textContent, /321/);
  assert.notEqual(c.px["ES=F"].getAttribute("data-live"), "closed");
});

test("invalid quote numbers do not overwrite a carried cash price", async () => {
  const c = await client({ quotes: { "600519.SS": quote(-99) }, tickers: { "600519.SS": entry({ data_state: "invalid" }) } });
  assert.equal(c.px["600519.SS"].textContent, "10.00");
  assert.equal(c.px["600519.SS"].getAttribute("data-data-state"), "invalid");
});

test("calendar updates remain authoritative when the quote snapshot arrives out of order", async () => {
  const c = await client({ sessions: { cn: session("cn", { state: "open", open: true, data_frozen: false }) } });
  assert.equal(c.px["600519.SS"].textContent, "99.00");
  c.response.quoteTs = NOW - 60000;
  c.response.overlay = { sessions: { cn: session("cn", { checked_at: "2026-10-07T02:00:00Z" }) }, tickers: { "600519.SS": entry() } };
  await c.refresh();
  assert.equal(c.px["600519.SS"].getAttribute("data-live"), "closed");
  assert.equal(c.px["600519.SS"].textContent, "10.00");
  assert.match(c.strip().textContent, /National Day/);
});

test("expiry retains the last accepted frozen baseline and its original date", async () => {
  const c = await client({ tickers: { "600519.SS": entry({ price: 12 }) } });
  assert.equal(c.px["600519.SS"].textContent, "12.00");
  c.response.overlay = null;
  await c.advance(61 * 60000);
  assert.equal(c.px["600519.SS"].textContent, "12.00");
  assert.equal(c.px["600519.SS"].getAttribute("data-through"), "2026-09-30");
  assert.equal(c.px["600519.SS"].getAttribute("data-quote-ts"), "2026-09-30T07:00:00Z");
});

test("unknown coverage never presents an inferred expected date as a confirmed close", async () => {
  const c = await client({ sessions: { cn: session("cn", { state: "unverified", calendar_verified: false }) } });
  assert.doesNotMatch(c.strip().textContent, /Last confirmed close|上次确认收盘/);
});

test("bad-print warning stays visible without mislabeling the healthy stored baseline", async () => {
  const c = await client({ tickers: { "600519.SS": entry({ quote_ts: new Date(NOW).toISOString(), quote_state: "invalid", divergence: { flag: "bad_print", severity: "info" } }) } });
  assert.equal(c.px["600519.SS"].getAttribute("data-data-state"), "current");
  assert.equal(c.px["600519.SS"].getAttribute("data-quote-state"), "invalid");
  assert.equal(c.px["600519.SS"].getAttribute("data-live"), "behind");
  assert.match(c.px["600519.SS"].getAttribute("data-tip-en"), /Rejected quote/);
  assert.match(c.strip().textContent, /Quote rejected/);
});

test("naive or malformed calendar receipts remain unverified", async () => {
  for (const extra of [
    { checked_at: "2026-10-07T01:59:00" },
    { valid_until: "not-a-time" },
    { checked_at: "2026-10-08T01:59:00Z", valid_until: "2026-10-09T03:00:00Z" },
  ]) {
    const c = await client({ sessions: { cn: session("cn", extra) } });
    assert.equal(c.px["600519.SS"].getAttribute("data-session-state"), "unverified");
    assert.match(c.strip().textContent, /unverified/i);
  }
});

test("missing, synthetic, malformed and future quote clocks cannot certify cash prices", async () => {
  for (const extra of [
    { ts: null }, { ts: 0 }, { ts: -1 }, { ts: "2026-10-07T02:00:00Z" },
    { ts: Infinity }, { ts: 1e99 }, { ts: NOW + 120000 }, { tsSynthetic: true },
  ]) {
    const c = await client({ quotes: { "600519.SS": quote(99, extra) }, tickers: { "600519.SS": entry() } });
    assert.equal(c.px["600519.SS"].textContent, "10.00");
    assert.equal(c.px["600519.SS"].getAttribute("data-data-state"), "current");
    assert.equal(c.px["600519.SS"].getAttribute("data-quote-state"), "invalid", JSON.stringify(extra));
    assert.equal(c.px["600519.SS"].getAttribute("data-live"), "behind");
    assert.match(c.strip().textContent, /Quote rejected/);
  }
});

test("a bad cash quote clock is rejected during an open session too", async () => {
  const c = await client({
    sessions: { cn: session("cn", { state: "open", open: true, data_frozen: false }) },
    quotes: { "600519.SS": quote(99, { ts: null }) },
    tickers: { "600519.SS": entry({ data_frozen: false }) },
  });
  assert.equal(c.px["600519.SS"].textContent, "10.00");
  assert.equal(c.px["600519.SS"].getAttribute("data-live"), "behind");
  assert.equal(c.px["600519.SS"].getAttribute("data-session-state"), "open");
});

test("a missing calendar response cannot bypass cash quote honesty", async () => {
  for (const ts of [NOW, null]) {
    const c = await client({ sessions: {}, quotes: { "600519.SS": quote(99, { ts }) } });
    assert.equal(c.px["600519.SS"].textContent, "10.00");
    assert.equal(c.px["600519.SS"].getAttribute("data-session-state"), "unverified");
    assert.equal(c.px["600519.SS"].getAttribute("data-live"), "behind");
    if (ts === null) assert.equal(c.px["600519.SS"].getAttribute("data-quote-state"), "invalid");
  }
});

test("Asia-hours fast snapshot supplies current status while the overlay is expired or missing", async () => {
  for (const oldOverlay of [
    null,
    { sessions: { cn: session("cn", { checked_at: "2026-10-06T10:00:00Z", valid_until: "2026-10-06T11:00:00Z" }) }, tickers: { "600519.SS": entry() } },
  ]) {
    const c = await client({ overlay: oldOverlay, snapshotSessions: { cn: session() },
      quotes: { "600519.SS": quote(10, { ts: Date.parse("2026-09-30T07:00:00Z") }) } });
    assert.equal(c.px["600519.SS"].getAttribute("data-live"), "closed");
    assert.equal(c.px["600519.SS"].textContent, "10.00");
    assert.equal(c.strip().getAttribute("data-session-state"), "holiday");
  }
});

test("a healthy worker uses one fast snapshot request for independent session status", async () => {
  const c = await client({
    pathname: "/hk_stocks.html", symbols: ["0700.HK"], overlay: null,
    workerQuotes: { "0700.HK": quote(77) },
    snapshotSessions: { hk: session("hk", { state: "open", open: true, data_frozen: false }), connect: session("connect") },
  });
  assert.equal(c.px["0700.HK"].textContent, "77.00");
  assert.equal(c.px["0700.HK"].getAttribute("data-live"), "1");
  assert.match(c.strip().textContent, /Stock Connect/);
  assert.equal(c.requests.filter(url => url === "live/quotes.json").length, 1);
  assert.equal(c.requests.filter(url => url.startsWith("https://worker.test")).length, 1);
});

test("worker failure shares that same snapshot promise for quote fallback and status", async () => {
  const c = await client({
    pathname: "/hk_stocks.html", symbols: ["0700.HK"], overlay: null, workerQuotes: null,
    snapshotSessions: { hk: session("hk", { state: "open", open: true, data_frozen: false }) },
  });
  assert.equal(c.px["0700.HK"].textContent, "99.00");
  assert.equal(c.px["0700.HK"].getAttribute("data-live"), "1");
  assert.equal(c.requests.filter(url => url === "live/quotes.json").length, 1);
});

test("an older overlay and its frozen flag cannot undo a newer snapshot reopening", async () => {
  const c = await client({
    pathname: "/hk_stocks.html", symbols: ["0700.HK"],
    sessions: { hk: session("hk") }, tickers: { "0700.HK": entry() },
    snapshotSessions: { hk: session("hk") },
  });
  assert.equal(c.px["0700.HK"].getAttribute("data-live"), "closed");
  c.response.snapshotSessions = { hk: session("hk", {
    state: "open", open: true, data_frozen: false, checked_at: "2026-10-07T02:00:00Z",
    holiday_name: null, holiday_name_zh: null,
  }) };
  await c.refresh();
  assert.equal(c.px["0700.HK"].textContent, "99.00");
  assert.equal(c.px["0700.HK"].getAttribute("data-live"), "1");
  c.response.snapshotSessions = undefined;
  await c.refresh();
  assert.equal(c.px["0700.HK"].getAttribute("data-live"), "1");
  assert.equal(c.strip().getAttribute("data-session-state"), "open");
});

test("a newer valid worker observation supersedes an older rejected overlay quote after reopening", async () => {
  const oldClocks = [
    { quote_ts: "2026-09-30T07:00:00Z" }, { quote_ts: null }, { quote_ts: "2026-10-08T02:00:00Z" },
    { quote_ts: new Date(NOW).toISOString(), quote_clock_invalid: true, stale_reason: "bad print (limit-move guard)" },
    ...["synthetic", "missing", "invalid", "future"].map(kind => ({
      quote_ts: new Date(NOW).toISOString(), stale_reason: kind + " quote timestamp",
    })),
  ];
  for (const oldClock of oldClocks) {
  const c = await client({
    pathname: "/hk_stocks.html", symbols: ["0700.HK"],
    sessions: { hk: session("hk") },
    tickers: { "0700.HK": entry({ ...oldClock, quote_state: "invalid", divergence: { flag: "bad_print", severity: "info" } }) },
    snapshotSessions: { hk: session("hk", { state: "open", open: true, data_frozen: false,
      checked_at: new Date(NOW).toISOString(), holiday_name: null, holiday_name_zh: null }) },
    workerQuotes: { "0700.HK": quote(77, { ts: NOW - 15 * 60000 }) },
  });
  assert.equal(c.px["0700.HK"].textContent, "77.00");
  assert.equal(c.px["0700.HK"].getAttribute("data-live"), "1");
  assert.equal(c.px["0700.HK"].getAttribute("data-data-state"), "current");
  assert.notEqual(c.px["0700.HK"].getAttribute("data-quote-state"), "invalid");
  assert.doesNotMatch(c.strip().textContent, /Quote rejected|报价已拒绝/);
  c.response.worker.quotes["0700.HK"] = quote(88, { ts: null });
  await c.refresh();
  assert.equal(c.px["0700.HK"].getAttribute("data-quote-state"), "invalid");
  assert.notEqual(c.px["0700.HK"].textContent, "88.00");
  }
});

test("a newer completed-session expectation ages retained history without healing known defects", async () => {
  for (const state of ["current", "late", "missing", "invalid", "unverified"]) {
    const c = await client({
      pathname: "/us_stocks.html", symbols: ["AAPL"],
      tickers: { AAPL: entry({ data_state: state, data_through: "2026-09-30" }) },
      snapshotSessions: { us: session("us", { expected_session: "2026-10-06", session_date: "2026-10-06",
        local_time: "2026-10-06T22:00:00-04:00", timezone: "America/New_York",
        state: "postclose", open: false, data_frozen: false,
        checked_at: new Date(NOW).toISOString() }) },
      workerQuotes: { AAPL: quote(77) },
    });
    assert.equal(c.px.AAPL.getAttribute("data-data-state"), state === "current" ? "late" : state);
    assert.doesNotMatch(c.px.AAPL.textContent, /77\.00/);
    if (state === "current") assert.match(c.strip().textContent, /Some prices late/);
  }
});

test("fast snapshot status advances even when its quote timestamp is older", async () => {
  const c = await client({
    pathname: "/hk_stocks.html", symbols: ["0700.HK"],
    snapshotSessions: { hk: session("hk", { state: "open", open: true, data_frozen: false }) },
    overlay: null, rowDates: { "0700.HK": "2026-09-30" },
  });
  assert.equal(c.px["0700.HK"].getAttribute("data-live"), "1");
  c.response.quoteTs = NOW - 1000;
  c.response.snapshotSessions = { hk: session("hk", { checked_at: "2026-10-07T02:00:00Z" }) };
  await c.refresh();
  assert.equal(c.px["0700.HK"].textContent, "10.00");
  assert.equal(c.px["0700.HK"].getAttribute("data-live"), "closed");
  assert.equal(c.strip().getAttribute("data-session-state"), "holiday");
});

test("a regional page with no quote nodes still receives the fast snapshot status", async () => {
  const c = await client({
    pathname: "/canada.html", symbols: [], overlay: null,
    snapshotSessions: { ca: session("ca", { holiday_name: "Thanksgiving", holiday_name_zh: "感恩节", timezone: "America/Toronto" }) },
  });
  assert.match(c.strip().textContent, /Thanksgiving/);
  assert.equal(c.strip().getAttribute("data-session-state"), "holiday");
  assert.equal(c.requests.filter(url => url === "live/quotes.json").length, 1);
});

test("session receipts merge per market without discarding other regions", async () => {
  const c = await client({
    pathname: "/hk_stocks.html", symbols: ["0700.HK", "600519.SS"],
    sessions: { cn: session(), hk: session("hk") },
    quotes: { "0700.HK": quote(), "600519.SS": quote(10, { ts: Date.parse("2026-09-30T07:00:00Z") }) },
    snapshotSessions: { hk: session("hk", {
      state: "open", open: true, data_frozen: false, checked_at: "2026-10-07T02:00:00Z",
    }) },
  });
  assert.equal(c.px["0700.HK"].getAttribute("data-live"), "1");
  assert.equal(c.px["600519.SS"].getAttribute("data-live"), "closed");
});

test("snapshot-only holiday health follows the observation session rather than minute age", async () => {
  for (const ts of ["2026-09-30T07:00:00Z", "2026-09-29T20:00:00Z"]) {
    const c = await client({
      overlay: null, snapshotSessions: { cn: session() },
      quotes: { "600519.SS": quote(10, { ts: Date.parse(ts) }) },
    });
    assert.equal(c.px["600519.SS"].textContent, "10.00");
    assert.equal(c.px["600519.SS"].getAttribute("data-live"), "closed");
    assert.equal(c.px["600519.SS"].getAttribute("data-data-state"), "current");
    assert.match(c.px["600519.SS"].getAttribute("data-tip-en"), /tencent/);
    assert.match(c.px["600519.SS"].getAttribute("data-tip-en"), /2026-09/);
    assert.doesNotMatch(c.strip().textContent, /prices late/i);
  }
});

test("snapshot-only earlier-session observations stay visibly late during a holiday", async () => {
  const c = await client({
    overlay: null, snapshotSessions: { cn: session() },
    quotes: { "600519.SS": quote(10, { ts: Date.parse("2026-09-29T07:00:00Z") }) },
  });
  assert.equal(c.px["600519.SS"].textContent, "10.00");
  assert.equal(c.px["600519.SS"].getAttribute("data-data-state"), "late");
  assert.equal(c.px["600519.SS"].getAttribute("data-live"), "stale");
  assert.match(c.strip().textContent, /prices late/i);
});

test("snapshot-only missing or undatable observations do not become healthy holiday data", async () => {
  for (const [quotes, expected] of [
    [{}, "missing"],
    [{ "600519.SS": quote(10, { ts: null }) }, "unverified"],
    [{ "600519.SS": quote(10, { tsSynthetic: true }) }, "unverified"],
  ]) {
    const c = await client({ overlay: null, snapshotSessions: { cn: session() }, quotes });
    assert.equal(c.px["600519.SS"].getAttribute("data-data-state"), expected);
    assert.equal(c.px["600519.SS"].getAttribute("data-live"), "behind");
    assert.equal(c.px["600519.SS"].textContent, "10.00");
  }
});

test("an explicit row date survives and takes precedence over a later quote observation", async () => {
  const c = await client({
    overlay: null, snapshotSessions: { cn: session() }, rowDates: { "600519.SS": "2026-09-29" },
    quotes: { "600519.SS": quote(10, { ts: Date.parse("2026-09-30T07:00:00Z") }) },
  });
  assert.equal(c.px["600519.SS"].getAttribute("data-through"), "2026-09-29");
  assert.equal(c.px["600519.SS"].getAttribute("data-data-state"), "late");
  assert.match(c.px["600519.SS"].getAttribute("data-tip-en"), /Prices through 2026-09-29/);
  assert.match(c.px["600519.SS"].getAttribute("data-tip-en"), /Quote time: 2026-09-30/);
});
