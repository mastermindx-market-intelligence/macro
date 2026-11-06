#!/usr/bin/env node
"use strict";
// L6.4 capture (lanes/L6_capture.md): the Cycles wave cells under the pinned P0B recipe
// (scripts/verify_stock_dashboard_mobile_layout.cjs pins, copied exactly).
//
//   node capture.cjs --selftest          pin refusal + cell naming, no browser
//   node capture.cjs --probe             one cell per view, discovery dump to stdout
//   node capture.cjs --run [regex]       matrix + delta cells -> cells/, zh_latin/
//   node capture.cjs --manifest          MANIFEST.sha256 over cells/*.png|json, zh_latin/*.txt
//
// Needs serve_l6.py on 127.0.0.1:8741 over the L6 render tree, NODE_PATH with playwright
// 1.61.1, and L6_SERVE_LOG pointing at the server's JSONL log. Nothing outside this
// directory is written except DOM dumps under L6_TMP (default os.tmpdir()).
const fs = require("fs");
const os = require("os");
const path = require("path");
const crypto = require("crypto");
const {execFileSync, spawnSync} = require("child_process");

const CHROMIUM_PIN = "149.0.7827.55";
const PLAYWRIGHT_PIN = "1.61.1";
const HOST_PIN = {platform: "darwin", arch: "arm64"};
const BROWSER_EXECUTABLE_PIN = {name: "chrome-headless-shell", sha256: "11e393326c7d20a7c56641a7c65def33ea9c280da3b0b74cf8563b07989a0ee3"};
const LAUNCH_ARGS = ["--disable-skia-runtime-opts", "--disable-partial-raster", "--disable-gpu", "--force-color-profile=srgb", "--disable-font-subpixel-positioning", "--font-render-hinting=none", "--disable-lcd-text"];
const FONT_PIN = "/p0b-font-pin/pin.css";
const BASE = "http://127.0.0.1:8741";
const R2 = "https://pub-f7ffb4441c5f4ad983ca56ec7c651c61.r2.dev";
const CLOCK = "2026-11-05T12:00:00Z";
const EV = __dirname;
const WT = path.resolve(EV, "..", "..", "..");
const ZH_GREP = path.join(WT, "design_refs", "sector-paper-20261021", "components", "zh_latin_grep.py");
const PY = "/opt/homebrew/bin/python3";
const SERVE_LOG = process.env.L6_SERVE_LOG || "";
const TMP = process.env.L6_TMP || os.tmpdir();

const VIEWS = {
  v1: {slug: "v1-central-cycles", url: "/sector_central.html#cycles"},
  v2: {slug: "v2-sector-cycles", url: "/sector_cycles.html"},
  v3: {slug: "v3-xlk-cycle", url: "/sectors/XLK.html#cycle"},
  v4: {slug: "v4-china-cycles", url: "/sector_cycles_china.html"},
  // Delta-only: the INTL country cycles page shares site/cycle.css (L3 cross-program row); served from the HEAD blob.
  v5: {slug: "v5-intl-country-cycles", url: "/country_cycles.html"},
};
const VIEWPORTS = {1440: {width: 1440, height: 900}, 390: {width: 390, height: 844}, 375: {width: 375, height: 812}};
const NAME_RE = /^v[1-5]-[a-z-]+__(dark|light)__(en|zh)__(1440|390|375)(__[a-z0-9-]+)?$/;

// Element roles recorded in every layout JSON; the first matching selector wins.
const ROLES = {
  heading: ["#sc-hero-title", "main h1", "h1"],
  asof: ["#sc-asof", "#si-cycles-asof", ".cyc-asof", "[data-asof]"],
  generation: ["#si-cycles-gen", "[data-gen]", ".sc-gen", "[data-generation]"],
  stale_guard: ["[data-stale]", ".sc-state--stale", ".sc-stale", ".mr-chip-stale"],
  chips: ["#sc-chips"],
  chart: ["#sc-chart"],
  inspector: ["#sc-detail"],
  compare_tray: [".sc-cmp"],
  fixture_label: ["[data-fixture=\"true\"]"],
  tape_asof: ["#ftr-tape-asof"],
  strip_asof: ["#ftr-strip-asof"],
  basket_on: [".sc-bchip.on"],
  members: [".scd-members"],
  companies_unavailable: ["#scd-p-companies .sc-state--unavailable", "#scd-p-companies .scd-nc"],
  stance_unavailable: [".cc-stance-na"],
};

function matrix() {
  const cells = [];
  for (const view of ["v1", "v2", "v3"]) for (const theme of ["dark", "light"]) for (const lang of ["en", "zh"]) for (const width of [1440, 390]) cells.push({view, theme, lang, width});
  for (const theme of ["dark", "light"]) for (const width of [1440, 390]) cells.push({view: "v4", theme, lang: "zh", width});
  return cells;
}

let DELTAS = [];
try { DELTAS = require(path.join(EV, "deltas.cjs")); } catch (error) { if (error.code !== "MODULE_NOT_FOUND") throw error; }

function cellName(c) { return `${VIEWS[c.view].slug}__${c.theme}__${c.lang}__${c.width}${c.tag ? `__${c.tag}` : ""}`; }

// An anonymous capture is refused the premium payload by design (401); every other console error is unexpected.
function expectedConsoleError(e) { return /\/premiumdata\//.test(e.url || "") && /\b401\b/.test(e.text || ""); }

function sha256Bytes(bytes) { return crypto.createHash("sha256").update(bytes).digest("hex"); }
function sha256File(filename) { return sha256Bytes(fs.readFileSync(filename)); }

function checkPins(obs) {
  const errors = [];
  if (obs.playwright !== PLAYWRIGHT_PIN) errors.push(`playwright ${obs.playwright} != ${PLAYWRIGHT_PIN}`);
  if (obs.platform !== HOST_PIN.platform || obs.arch !== HOST_PIN.arch) errors.push(`host ${obs.platform}/${obs.arch} != ${HOST_PIN.platform}/${HOST_PIN.arch}`);
  if ("browserVersion" in obs && obs.browserVersion !== CHROMIUM_PIN) errors.push(`chromium ${obs.browserVersion} != ${CHROMIUM_PIN}`);
  if ("executable" in obs) {
    const exe = obs.executable;
    if (!exe) errors.push("browser executable could not be identified");
    else {
      if (exe.name !== BROWSER_EXECUTABLE_PIN.name) errors.push(`executable ${exe.name} != ${BROWSER_EXECUTABLE_PIN.name}`);
      if (exe.sha256 !== BROWSER_EXECUTABLE_PIN.sha256) errors.push(`executable sha256 ${exe.sha256} != ${BROWSER_EXECUTABLE_PIN.sha256}`);
    }
  }
  return errors;
}

async function launchedExecutable(browser) {
  try {
    const cdp = await browser.newBrowserCDPSession();
    const {processInfo} = await cdp.send("SystemInfo.getProcessInfo");
    await cdp.detach().catch(() => null);
    const pids = processInfo.filter((row) => row.type === "browser").map((row) => row.id);
    if (pids.length !== 1) return null;
    const image = execFileSync("ps", ["-o", "comm=", "-p", String(pids[0])], {encoding: "utf8"}).trim();
    if (!path.isAbsolute(image) || !fs.existsSync(image)) return null;
    return {name: path.basename(image), sha256: sha256File(image)};
  } catch (error) { return null; }
}

function injectFontPin(bytes, stylesheet) {
  const html = bytes.toString("utf8");
  const heads = html.match(/<head(?:\s[^>]*)?>/gi) || [];
  if (heads.length !== 1) throw new Error(`font pin: served owner page has ${heads.length} <head> start tags`);
  const at = html.search(/<head(?:\s[^>]*)?>/i) + heads[0].length;
  return Buffer.from(`${html.slice(0, at)}<link rel="stylesheet" href="${stylesheet}">${html.slice(at)}`, "utf8");
}

async function settleFonts(page) {
  const failed = await page.evaluate(async () => {
    const faces = Array.from(document.fonts);
    await Promise.all(faces.map((face) => face.load().catch(() => null)));
    void document.documentElement.offsetHeight;
    return faces.filter((face) => face.status !== "loaded").map((face) => `${face.family} ${face.weight}`);
  });
  if (failed.length) throw new Error(`font pin: faces did not load: ${failed.join(", ")}`);
}

function refuse(message) { console.error(`REFUSED: ${message}`); process.exit(2); }

function gitHead() { return execFileSync("git", ["-C", WT, "rev-parse", "HEAD"], {encoding: "utf8"}).trim(); }

async function openBrowser() {
  const {chromium} = require("playwright");
  const playwrightVersion = require("playwright/package.json").version;
  const hostErrors = checkPins({playwright: playwrightVersion, platform: process.platform, arch: process.arch});
  if (hostErrors.length) refuse(hostErrors.join("; "));
  const browser = await chromium.launch({headless: true, args: LAUNCH_ARGS});
  const executable = await launchedExecutable(browser);
  const errors = checkPins({playwright: playwrightVersion, platform: process.platform, arch: process.arch, browserVersion: browser.version(), executable});
  if (errors.length) { await browser.close(); refuse(errors.join("; ")); }
  return {browser, pins: {chromium: browser.version(), playwright: playwrightVersion, host: `${process.platform}/${process.arch}`, executable, launch_args: LAUNCH_ARGS, font_pin: FONT_PIN, clock: CLOCK, locale: "en-US", timezone: "UTC", dpr: 1}};
}

function readServeLog(from) {
  if (!SERVE_LOG || !fs.existsSync(SERVE_LOG)) return {counts: {}, head_fallback: [], missing: []};
  const fd = fs.openSync(SERVE_LOG, "r");
  const size = fs.fstatSync(fd).size;
  const buf = Buffer.alloc(Math.max(0, size - from));
  fs.readSync(fd, buf, 0, buf.length, from);
  fs.closeSync(fd);
  const counts = {}, headFallback = new Set(), missing = new Set();
  for (const line of buf.toString("utf8").split("\n")) {
    if (!line.trim()) continue;
    const rec = JSON.parse(line);
    counts[rec.source] = (counts[rec.source] || 0) + 1;
    if (rec.source === "head-fallback") headFallback.add(rec.path);
    if (rec.source === "missing") missing.add(rec.path);
  }
  return {counts, head_fallback: [...headFallback].sort(), missing: [...missing].sort()};
}
function serveLogSize() { return SERVE_LOG && fs.existsSync(SERVE_LOG) ? fs.statSync(SERVE_LOG).size : 0; }

async function newCellContext(browser, c, interceptions) {
  const js = c.js !== false;
  const context = await browser.newContext({viewport: VIEWPORTS[c.width], deviceScaleFactor: 1, locale: "en-US", timezoneId: "UTC", javaScriptEnabled: js, colorScheme: c.theme});
  if (js) await context.clock.setFixedTime(new Date(CLOCK));
  await context.addInitScript(({theme, lang}) => {
    try { localStorage.setItem("theme", theme); localStorage.setItem("lang", lang); localStorage.removeItem("themeAuto"); } catch (error) { /* storage unavailable */ }
  }, {theme: c.theme, lang: c.lang});
  const variantHeaders = c.variant ? {"x-l6-variant": c.variant} : {};
  await context.route("**/*", async (route) => {
    const req = route.request();
    const url = new URL(req.url());
    if (url.origin === BASE) {
      if (req.resourceType() === "document") {
        const resp = await route.fetch({headers: {...req.headers(), ...variantHeaders}});
        let body = await resp.body();
        if (resp.status() === 200 && (resp.headers()["content-type"] || "").startsWith("text/html")) body = injectFontPin(body, FONT_PIN);
        return route.fulfill({response: resp, body});
      }
      return route.continue({headers: {...req.headers(), ...variantHeaders}});
    }
    if (url.origin === R2) {
      const resp = await route.fetch({url: `${BASE}${url.pathname}${url.search}`, headers: variantHeaders});
      interceptions.push({kind: "r2-to-local", path: url.pathname, status: resp.status()});
      return route.fulfill({response: resp, headers: {...resp.headers(), "access-control-allow-origin": "*"}});
    }
    if (url.hostname === "s3.tradingview.com") {
      interceptions.push({kind: "stub-tradingview", url: `${url.origin}${url.pathname}`});
      return route.fulfill({status: 200, contentType: "application/javascript; charset=utf-8", body: TV_STUB});
    }
    interceptions.push({kind: "stub-204", url: `${url.origin}${url.pathname}`, type: req.resourceType()});
    return route.fulfill({status: 204, body: ""});
  });
  return context;
}

async function runSteps(page, steps) {
  const done = [];
  for (const step of steps || []) {
    if (step.click) {
      const loc = page.locator(step.click).first();
      const n = await page.locator(step.click).count();
      if (!n) { done.push({click: step.click, matched: 0}); continue; }
      await loc.scrollIntoViewIfNeeded().catch(() => null);
      await loc.click({timeout: 5000}).then(() => done.push({click: step.click, matched: n}), (error) => done.push({click: step.click, matched: n, error: String(error.message).split("\n")[0]}));
    } else if (step.hash) {
      await page.evaluate((h) => { location.hash = h; }, step.hash);
      done.push({hash: step.hash});
    } else if (step.scroll) {
      const n = await page.locator(step.scroll).count();
      if (n) await page.locator(step.scroll).first().scrollIntoViewIfNeeded().catch(() => null);
      done.push({scroll: step.scroll, matched: n});
    }
    await page.waitForTimeout(step.wait || 350);
  }
  return done;
}

function pageProbe(args) {
  const {roles, scope} = args;
  const vis = (el) => { const r = el.getBoundingClientRect(); const cs = getComputedStyle(el); return r.width > 0 && r.height > 0 && cs.display !== "none" && cs.visibility !== "hidden"; };
  const boxOf = (el, selector) => { const r = el.getBoundingClientRect(); return {selector, x: Math.round(r.left), y: Math.round(r.top + window.scrollY), w: Math.round(r.width), h: Math.round(r.height), visible: vis(el), text: (el.innerText || el.textContent || "").replace(/\s+/g, " ").trim().slice(0, 200)}; };
  const boxes = {};
  for (const [role, cands] of Object.entries(roles)) {
    boxes[role] = null;
    for (const s of cands) { const el = document.querySelector(s); if (el) { boxes[role] = boxOf(el, s); break; } }
  }
  const fixtures = Array.from(document.querySelectorAll("[data-fixture=\"true\"]"));
  const root = (scope && document.querySelector(scope)) || document.body;
  const sides = ["Top", "Right", "Bottom", "Left"];
  const stripes = [];
  for (const el of root.querySelectorAll("*")) {
    const cs = getComputedStyle(el);
    if (cs.display === "none") continue;
    const eff = sides.map((s) => {
      const st = cs[`border${s}Style`], col = cs[`border${s}Color`];
      if (st === "none" || st === "hidden" || col === "transparent" || /,\s*0\)$/.test(col)) return 0;
      return parseFloat(cs[`border${s}Width`]) || 0;
    });
    const mx = Math.max(...eff), mn = Math.min(...eff);
    const inset = /inset/.test(cs.boxShadow || "") && /(^|,)\s*(rgba?\([^)]*\)\s*)?-?[1-9]\d*(\.\d+)?px\s+0(px)?\s+0(px)?\s+0?(px)?\s*(rgba?\([^)]*\)\s*)?inset/.test(cs.boxShadow);
    if ((mx >= 2 && mx - mn >= 1.5 && eff.filter((x) => x === mx).length === 1) || inset) {
      const r = el.getBoundingClientRect();
      if (r.width > 0 && r.height > 8) stripes.push({el: `${el.tagName.toLowerCase()}${el.id ? `#${el.id}` : ""}${el.classList.length ? `.${Array.from(el.classList).join(".")}` : ""}`, side: inset ? "inset-shadow" : sides[eff.indexOf(mx)].toLowerCase(), width: mx, w: Math.round(r.width), h: Math.round(r.height)});
      if (stripes.length >= 30) break;
    }
  }
  const nextTurn = Array.from(root.querySelectorAll("[class*=\"next\"],[data-next-turn]")).filter(vis).slice(0, 16).map((el) => (el.innerText || "").replace(/\s+/g, " ").trim().slice(0, 120)).filter(Boolean);
  let ctx = null;
  const ctxEl = document.getElementById("si-cycles-ctx");
  if (ctxEl) { try { ctx = JSON.parse(ctxEl.textContent); } catch (error) { ctx = {parse_error: String(error)}; } }
  const fixtureText = [];
  const sizeMult = [];
  const tw = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  while (tw.nextNode()) {
    const t = tw.currentNode.nodeValue, par = tw.currentNode.parentElement;
    if (!par || /^(SCRIPT|STYLE|NOSCRIPT|TEMPLATE)$/.test(par.tagName)) continue;
    if (/\bFIX(TURE)?\b|示例数据/.test(t) && fixtureText.length < 12) fixtureText.push({el: `${par.tagName.toLowerCase()}.${Array.from(par.classList).join(".")}`, visible: vis(par), text: t.trim().slice(0, 80)});
    if (/size_mult/.test(t) && sizeMult.length < 8) { const d = par.closest("details"); sizeMult.push({el: `${par.tagName.toLowerCase()}.${Array.from(par.classList).join(".")}`, visible: vis(par), in_details: !!d, details_open: d ? d.open : null, text: t.trim().slice(0, 120)}); }
  }
  const de = document.documentElement;
  return {
    scrollWidth: Math.max(de.scrollWidth, document.body ? document.body.scrollWidth : 0),
    scrollHeight: de.scrollHeight,
    data_theme: de.getAttribute("data-theme"),
    data_lang: de.getAttribute("data-lang"),
    html_lang: de.lang,
    computed_bg: document.body ? getComputedStyle(document.body).backgroundColor : null,
    boxes,
    fixture_labels: {count: fixtures.length, visible: fixtures.filter(vis).length, texts: [...new Set(fixtures.map((el) => (el.innerText || "").trim()))].slice(0, 8)},
    fixture_text: fixtureText,
    size_mult_text: sizeMult,
    stripe_audit: {scope: scope || "body", flagged: stripes},
    next_turn_labels: nextTurn,
    cycles_ctx: ctx ? {today: ctx.today, asof: ctx.asof, fixture: ctx.fixture, generation: ctx.generation, coverage: ctx.coverage} : null,
  };
}

function discovery() {
  const ids = Array.from(document.querySelectorAll("[id]")).map((el) => el.id).filter((id) => /sc-|cyc|si-|cycle|dossier|scd/.test(id)).slice(0, 160);
  const tokens = {};
  for (const el of document.querySelectorAll("[class]")) for (const t of el.classList) if (/gen|stale|fix|asof|cmp|hz|next|turn|guard|unavail|state|scd|dossier|cyc-out|st-/.test(t)) tokens[t] = (tokens[t] || 0) + 1;
  const attrs = {};
  for (const el of document.querySelectorAll("*")) for (const a of el.getAttributeNames()) if (/^data-(gen|stale|fix|asof|state|next|turn)/.test(a)) attrs[`${a}=${el.getAttribute(a)}`.slice(0, 80)] = (attrs[`${a}=${el.getAttribute(a)}`.slice(0, 80)] || 0) + 1;
  const texts = [];
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  while (walker.nextNode()) { const s = walker.currentNode.nodeValue.trim(); if (/Fixture|示例数据|generation|Generation|Stale|stale|Live parity|代际|过期/.test(s) && texts.length < 24) texts.push(`${walker.currentNode.parentElement.tagName.toLowerCase()}.${Array.from(walker.currentNode.parentElement.classList).join(".")} :: ${s.slice(0, 120)}`); }
  return {ids, tokens, attrs, texts, title: document.title};
}

// The dossier's third-party chart is stubbed offline. The stub draws a labelled fixture
// frame in the widget's 440px slot, so a cell never shows an unexplained empty box and
// never passes the frame off as product UI. The product's own failure notice (tv.js
// missing) is pinned in tests/test_subsector_setup_zh.py.
const TV_STUB = "window.TradingView={widget:function(o){var h=document.getElementById(o&&o.container_id);"
  + "if(h)h.innerHTML='<div data-capture-fixture=\"tradingview-stub\" style=\"box-sizing:border-box;height:440px;display:flex;align-items:center;justify-content:center;padding:16px;text-align:center;border:1px dashed currentColor;border-radius:8px;opacity:.6;font:12px/1.5 ui-monospace,Menlo,monospace\">CAPTURE FIXTURE \u00b7 third-party TradingView chart stubbed offline (not product UI)</div>';}};";

async function captureCell(browser, pins, head, c, opts) {
  const name = cellName(c);
  const interceptions = [];
  const context = await newCellContext(browser, c, interceptions);
  const page = await context.newPage();
  const consoleErrors = [], pageErrors = [], failed = [], notes = [];
  page.on("console", (m) => { if (m.type() === "error") consoleErrors.push({text: m.text().slice(0, 300), url: (m.location() || {}).url || ""}); });
  page.on("pageerror", (e) => pageErrors.push(String((e && e.message) || e).slice(0, 300)));
  page.on("requestfailed", (r) => failed.push({url: r.url().slice(0, 200), failure: (r.failure() || {}).errorText}));
  const logFrom = serveLogSize();
  const resp = await page.goto(`${BASE}${VIEWS[c.view].url}`, {waitUntil: "load", timeout: 60000});
  await page.waitForLoadState("networkidle", {timeout: 20000}).catch(() => notes.push("networkidle not reached in 20 s"));
  if (c.js !== false) await settleFonts(page);
  const steps = await runSteps(page, c.steps);
  await page.waitForTimeout(500);
  if (opts.probe) {
    const found = await page.evaluate(discovery);
    await context.close();
    return {name, status: resp ? resp.status() : null, found, consoleErrors, pageErrors, failed, interceptions, serve: readServeLog(logFrom)};
  }
  const layout = await page.evaluate(pageProbe, {roles: ROLES, scope: c.scope || VIEWS[c.view].scope || null});
  const pngPath = path.join(EV, "cells", `${name}.png`);
  await page.screenshot({path: pngPath, fullPage: true, animations: "disabled", caret: "hide"});
  let zh = null;
  if (c.lang === "zh") {
    const scopeSel = c.zhScope || VIEWS[c.view].zhScope || null;
    const html = await page.evaluate((sel) => { const el = sel && document.querySelector(sel); return el ? `<html><body>${el.outerHTML}</body></html>` : document.documentElement.outerHTML; }, scopeSel);
    const dom = path.join(TMP, `l6_${name}.dom.html`);
    fs.writeFileSync(dom, html);
    const run = spawnSync(PY, ["-I", ZH_GREP, dom], {encoding: "utf8"});
    const text = `${run.stdout || ""}${run.stderr || ""}`;
    fs.writeFileSync(path.join(EV, "zh_latin", `${name}.txt`), `scope: ${scopeSel || "document"}\nrc: ${run.status}\n${text}`);
    const m = /zh-latin=(\d+)/.exec(text);
    zh = {scope: scopeSel || "document", count: m ? Number(m[1]) : null, rc: run.status, line: text.trim().split("\n").slice(-1)[0].slice(0, 400)};
  }
  const serve = readServeLog(logFrom);
  const width = VIEWPORTS[c.width].width;
  const record = {
    cell: name, view: c.view, url: VIEWS[c.view].url, theme: c.theme, lang: c.lang, viewport: VIEWPORTS[c.width], variant: c.variant || null, js: c.js !== false, steps,
    head, pins, http_status: resp ? resp.status() : null, notes,
    ...layout,
    assertions: {
      scroll_width_within_viewport: layout.scrollWidth <= width,
      console_errors: consoleErrors.length,
      console_errors_unexpected: consoleErrors.filter((e) => !expectedConsoleError(e)).length,
      size_mult_visible: layout.size_mult_text.some((x) => x.visible),
      page_errors: pageErrors.length,
      fixture_label_visible: layout.fixture_labels.visible > 0,
      theme_applied: c.js === false ? null : layout.data_theme === c.theme,
      lang_applied: c.js === false ? null : (layout.data_lang || "en") === c.lang,
      zh_latin: zh ? zh.count : null,
      // A cell that names the roles it exists to show fails when none of them has a box:
      // a scroll step can match an element inside a hidden view and still be a no-op.
      expect_visible_any: c.expectVisibleAny ? c.expectVisibleAny.some((role) => Boolean(layout.boxes[role] && layout.boxes[role].visible)) : null,
    },
    console_errors: consoleErrors, console_errors_expected: consoleErrors.filter(expectedConsoleError).map(() => "premiumdata 401 (anonymous capture)"), page_errors: pageErrors, failed_requests: failed,
    interceptions, serve, zh_latin: zh,
    png: {file: `cells/${name}.png`, sha256: sha256File(pngPath)},
  };
  fs.writeFileSync(path.join(EV, "cells", `${name}.layout.json`), `${JSON.stringify(record, null, 2)}\n`);
  await context.close();
  return record;
}

function selftest() {
  const results = [];
  const ok = (label, cond) => results.push(`${cond ? "PASS" : "FAIL"} ${label}`);
  const good = {playwright: PLAYWRIGHT_PIN, platform: "darwin", arch: "arm64", browserVersion: CHROMIUM_PIN, executable: {...BROWSER_EXECUTABLE_PIN}};
  ok("pins accept the pinned recipe", checkPins(good).length === 0);
  const wrongSha = checkPins({...good, executable: {name: BROWSER_EXECUTABLE_PIN.name, sha256: "0".repeat(64)}});
  ok("pins refuse a wrong executable sha256", wrongSha.length === 1 && /sha256/.test(wrongSha[0]));
  ok("pins refuse system Chrome", checkPins({...good, executable: {name: "Google Chrome", sha256: "1".repeat(64)}}).length === 2);
  ok("pins refuse an unidentified executable", checkPins({...good, executable: null}).length === 1);
  ok("pins refuse another chromium", checkPins({...good, browserVersion: "150.0.0.0"}).length === 1);
  ok("pins refuse another playwright", checkPins({...good, playwright: "1.60.0"}).length === 1);
  ok("pins refuse another host", checkPins({...good, arch: "x64"}).length === 1);
  const cells = matrix();
  const names = cells.map(cellName);
  ok("matrix has 28 cells", cells.length === 28);
  ok("matrix names are unique", new Set(names).size === 28);
  ok("matrix names match the cell pattern", names.every((n) => NAME_RE.test(n)));
  ok("V4 is ZH only", cells.filter((c) => c.view === "v4").every((c) => c.lang === "zh") && cells.filter((c) => c.view === "v4").length === 4);
  const dnames = DELTAS.map(cellName);
  ok(`delta names unique and patterned (${DELTAS.length})`, new Set([...names, ...dnames]).size === names.length + dnames.length && dnames.every((n) => NAME_RE.test(n)));
  ok("font pin lands after the single <head>", injectFontPin(Buffer.from("<html><head lang=x><title>t</title></head></html>"), FONT_PIN).toString().startsWith(`<html><head lang=x><link rel="stylesheet" href="${FONT_PIN}"><title>`));
  let threw = false;
  try { injectFontPin(Buffer.from("<head></head><head></head>"), FONT_PIN); } catch (error) { threw = /2 <head>/.test(error.message); }
  ok("font pin refuses two <head> tags", threw);
  for (const r of results) console.log(r);
  const failed = results.filter((r) => r.startsWith("FAIL")).length;
  console.log(`SELFTEST ${failed ? "FAIL" : "PASS"} ${results.length - failed}/${results.length}`);
  process.exit(failed ? 1 : 0);
}

function manifest() {
  const files = [];
  for (const dir of ["cells", "zh_latin"]) {
    const abs = path.join(EV, dir);
    if (!fs.existsSync(abs)) continue;
    for (const f of fs.readdirSync(abs).sort()) if (/\.(png|json|txt)$/.test(f)) files.push(`${dir}/${f}`);
  }
  files.sort();
  const lines = files.map((f) => `${sha256File(path.join(EV, f))}  ${f}`);
  fs.writeFileSync(path.join(EV, "MANIFEST.sha256"), `${lines.join("\n")}\n`);
  console.log(`MANIFEST ${lines.length} files`);
}

async function main() {
  const argv = process.argv.slice(2);
  if (argv[0] === "--selftest") return selftest();
  if (argv[0] === "--manifest") return manifest();
  const head = gitHead();
  const written = JSON.parse(fs.readFileSync(path.join(process.env.L6_OUT || "", "_l6_written.json"), "utf8"));
  if (written.head !== head) refuse(`render head ${written.head} != worktree HEAD ${head}`);
  const {browser, pins} = await openBrowser();
  try {
    if (argv[0] === "--probe") {
      const probes = [{view: "v1", theme: "dark", lang: "en", width: 1440}, {view: "v2", theme: "dark", lang: "en", width: 1440}, {view: "v3", theme: "dark", lang: "en", width: 1440}, {view: "v4", theme: "dark", lang: "zh", width: 1440}];
      for (const c of probes) console.log(JSON.stringify(await captureCell(browser, pins, head, c, {probe: true})));
      return;
    }
    if (argv[0] !== "--run") refuse(`unknown mode ${argv[0]}`);
    const filter = argv[1] ? new RegExp(argv[1]) : null;
    fs.mkdirSync(path.join(EV, "cells"), {recursive: true});
    fs.mkdirSync(path.join(EV, "zh_latin"), {recursive: true});
    const cells = [...matrix(), ...DELTAS].filter((c) => !filter || filter.test(cellName(c)));
    for (const c of cells) {
      const t0 = Date.now();
      try {
        const r = await captureCell(browser, pins, head, c, {});
        const a = r.assertions;
        console.log(`${r.cell} ev=${a.expect_visible_any} sw=${r.scrollWidth}/${r.viewport.width} ce=${a.console_errors}/${a.console_errors_unexpected} pe=${a.page_errors} fixture=${a.fixture_label_visible} ftxt=${r.fixture_text.filter((x) => x.visible).length} smult=${a.size_mult_visible} theme=${a.theme_applied} lang=${a.lang_applied} zh=${a.zh_latin} stripes=${r.stripe_audit.flagged.length} fb=${r.serve.head_fallback.length} miss=${r.serve.missing.length} ${Date.now() - t0}ms`);
      } catch (error) {
        console.log(`${cellName(c)} ERROR ${String(error.message).split("\n")[0]}`);
      }
    }
  } finally { await browser.close(); }
}

main().catch((error) => { console.error(error); process.exit(1); });
