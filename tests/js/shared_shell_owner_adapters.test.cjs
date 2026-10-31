"use strict";
/* ============================================================================
 * shared_shell_owner_adapters.test.cjs — Node VM tests for the Shared Shell
 * owner adapter edits (run shared-shell-owner-final-20261018-c1-r1).
 *
 * Where to run: AFTER the parent applies shared_shell_owner_final_edits.json
 * to the original PR source (Macro #7949 8eea49839b22fc332edeff1d687d80a62d413acf),
 * inside that repo checkout:
 *
 *   MMX_TEMPLATES_DIR=/path/to/repo/templates node --test shared_shell_owner_adapters.test.cjs
 *   (or plain: node --test shared_shell_owner_adapters.test.cjs  from the repo root)
 *
 * What it does: extracts the ACTUAL repository functions from the patched
 * templates/theme.js, templates/account.js and templates/onboard.js by source
 * text, and evaluates them in node:vm contexts with deterministic fakes — a
 * bridge object whose `applyingContext` is a frozen getter mirroring the real
 * child bridge (true synchronously for the duration of a bridge setter call,
 * INCLUDING the initial INIT apply, which happens while the presented flag is
 * still false), a synchronous document event registry, and a recording
 * localStorage. It observes storage writes and synchronous preference-event
 * consumers. Static + VM only: no browser, no runtime, no live/embedded
 * acceptance is claimed or required. Parent-side bridge/INIT integration
 * remains on the original PRs.
 * ==========================================================================*/

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

// ----------------------------------------------------------------- locating --
function locate(name) {
  const cands = [];
  if (process.env.MMX_TEMPLATES_DIR) cands.push(path.join(process.env.MMX_TEMPLATES_DIR, name));
  cands.push(path.join(process.cwd(), "templates", name));
  cands.push(path.join(__dirname, "templates", name));
  cands.push(path.resolve(__dirname, "..", "templates", name));
  for (const c of cands) {
    if (fs.existsSync(c)) return c;
  }
  assert.fail("template not found: " + name + " (searched: " + cands.join(", ") +
    "; set MMX_TEMPLATES_DIR to the patched repo templates directory)");
}
function readTemplate(name) { return fs.readFileSync(locate(name), "utf8"); }

const themeSrc = readTemplate("theme.js");
const accountSrc = readTemplate("account.js");
const onboardSrc = readTemplate("onboard.js");

// ---------------------------------------------------------------- extraction --
// Pulls the real `function NAME(...) { ... }` text out of the repository file,
// scanning with a string/comment-aware brace counter. Throws a named failure if
// the seam is absent (i.e. the adapter edits were not applied).
function extractFn(src, fileLabel, name) {
  const header = new RegExp("function\\s+" + name + "\\s*\\(");
  const m = header.exec(src);
  if (!m) {
    assert.fail("function " + name + " not found in " + fileLabel +
      " — the owner adapter edits are not applied there (or the seam was renamed)");
  }
  const start = m.index;
  const open = src.indexOf("{", start);
  let depth = 0, j = open, inStr = null, inComment = null;
  while (j < src.length) {
    const c = src[j], d = src[j + 1];
    if (inComment === "//") { if (c === "\n") inComment = null; j++; continue; }
    if (inComment === "/*") { if (c === "*" && d === "/") { inComment = null; j += 2; continue; } j++; continue; }
    if (inStr) { if (c === "\\") { j += 2; continue; } if (c === inStr) inStr = null; j++; continue; }
    if (c === "'" || c === '"' || c === "`") { inStr = c; j++; continue; }
    if (c === "/" && d === "/") { inComment = "//"; j += 2; continue; }
    if (c === "/" && d === "*") { inComment = "/*"; j += 2; continue; }
    if (c === "{") depth++;
    else if (c === "}") { depth--; j++; if (depth === 0) break; continue; }
    j++;
  }
  assert.equal(depth, 0, "brace scan unterminated for " + name + " in " + fileLabel);
  return src.slice(start, j);
}
function extractAll(src, fileLabel, names) {
  return names.map((n) => extractFn(src, fileLabel, n)).join("\n;\n");
}

// ------------------------------------------------------------- fake fixtures --
// The fixed bridge intent vocabulary the adapter is allowed to emit.
const INTENT_TOKENS = ["signin", "signup", "settings", "billing"];

function makeBridge(initial) {
  initial = initial || {};
  const st = { presented: !!initial.presented, applying: false };
  const calls = [];
  const api = {
    __mmxBridge: "mmx.shared-shell.v1",
    navigate: function () { return false; },
    openAuth: function (intent) {
      calls.push({ intent: intent, presented: st.presented, applying: st.applying });
      // Adapter rule: only fixed tokens ever cross the bridge. (The provided
      // bridge snippet lists ["signin","signup","settings","billing"]; the
      // existing wire contract uses billing; legacy UI upgrade maps to it.
      // UI modes and standalone upgrade behavior remain unchanged.)
      assert.ok(INTENT_TOKENS.indexOf(intent) !== -1,
        "openAuth received a non-fixed intent token: " + intent);
      return true;
    },
  };
  // Frozen read-only getters, exactly like the real bridge object: `applying`
  // is true synchronously for the duration of every bridge setter invocation —
  // including the initial apply, which runs while `presented` is still false.
  Object.defineProperty(api, "active", { enumerable: true, get: function () { return st.presented === true; } });
  Object.defineProperty(api, "applyingContext", { enumerable: true, get: function () { return st.applying === true; } });
  try { Object.freeze(api); } catch (e) {}
  return { api: api, st: st, calls: calls };
}

// Mirrors the bridge applyContext shape (suppress=true around the synchronous
// setter call, cleared in a finally — try/finally ownership is bridge-side).
function bridgeApply(bridge, fn) {
  bridge.st.applying = true;
  let err = null;
  try { fn(); } catch (e) { err = e; } finally { bridge.st.applying = false; }
  return err;
}

function makeDom() {
  const listeners = Object.create(null);
  const themeBtns = [{}, {}];
  const langBtns = [{}];
  const docEl = {
    attrs: Object.create(null),
    lang: "en",
    getAttribute: function (k) { return k in this.attrs ? this.attrs[k] : null; },
    setAttribute: function (k, v) { this.attrs[k] = String(v); },
    style: {},
    classList: { add: function () {}, remove: function () {}, toggle: function () {}, contains: function () { return false; } },
  };
  docEl.attrs["data-theme"] = "dark";
  docEl.attrs["data-lang"] = "en";
  const documentMock = {
    documentElement: docEl,
    head: { appendChild: function (node) { documentMock.injected.push(node); } },
    injected: [],
    activeElement: null,
    cookie: "",
    readyState: "complete",
    addEventListener: function (type, fn) { (listeners[type] = listeners[type] || []).push(fn); },
    removeEventListener: function (type, fn) {
      const l = listeners[type] || []; const i = l.indexOf(fn); if (i !== -1) l.splice(i, 1);
    },
    // Synchronous dispatch, like real document event propagation: preference
    // event consumers run INSIDE the bridge's synchronous apply window.
    dispatchEvent: function (evt) {
      const l = (listeners[evt.type] || []).slice();
      for (const fn of l) fn(evt);
      return true;
    },
    querySelectorAll: function (sel) {
      if (sel === ".theme-btn") return themeBtns;
      if (sel === ".lang-btn") return langBtns;
      return [];
    },
    getElementById: function () { return null; },
    createElement: function (tag) {
      return { tagName: String(tag).toUpperCase(), defer: false, onload: null, onerror: null,
               setAttribute: function () {}, style: {} };
    },
  };
  return { docEl: docEl, document: documentMock, listeners: listeners, themeBtns: themeBtns, langBtns: langBtns };
}

function makeStorage(initial) {
  const data = Object.assign({}, initial || {});
  const writes = [];
  return {
    getItem: function (k) { return Object.prototype.hasOwnProperty.call(data, k) ? data[k] : null; },
    setItem: function (k, v) { writes.push([k, String(v)]); data[k] = String(v); },
    removeItem: function (k) { writes.push([k, null]); delete data[k]; },
    writes: writes,
    keysUsed: function () { return Array.from(new Set(writes.map((w) => w[0]))); },
  };
}

function FakeCustomEvent(type, init) { this.type = type; this.detail = init && init.detail; }

const LEGACY_PREF_KEYS = ["theme", "themeAuto", "lang"];

// --------------------------------------------------------------- theme.js ----
function buildThemeContext(opts) {
  opts = opts || {};
  const names = [
    "_mmShellBridge", "_mmShellApplying", "_mmShellAuthHandoff",
    "curTheme", "curLang", "setTheme", "setLang",
    "_sharedPref", "_isTheme", "_isFlag", "_isLang",
    "_applyServerPrefs", "_savePrefToServer", "_hookPrefSync", "_acctOwnsPref",
    "_mmOpenOnboard", "_openSDash",
  ];
  const code = extractAll(themeSrc, "templates/theme.js", names);
  const dom = makeDom();
  const storage = makeStorage(opts.storage);
  const timers = [];
  const log = {
    skyFx: [], charts: 0, segment: 0, auto: 0, hydrate: 0, timers: [], updateUser: [],
    themes: [], langs: [], onboardOpen: [], sdShown: [], sdBuild: 0, sdRender: 0, sdAria: 0,
  };
  const sandbox = {
    docEl: dom.docEl,
    document: dom.document,
    CustomEvent: FakeCustomEvent,
    localStorage: storage,
    location: { pathname: "/index.html", href: "https://www.mastermind-x.com/index.html", search: "", origin: "https://www.mastermind-x.com" },
    setTimeout: function (fn, ms) { timers.push({ fn: fn, ms: ms }); log.timers.push(ms); return timers.length; },
    clearTimeout: function () {},
    themeCharts: function () { log.charts++; },
    skyToggleFx: function (tm) { log.skyFx.push(tm); },
    _syncThemeSegment: function () { log.segment++; },
    setThemeAuto: function () { log.auto++; },
    _buildSDash: function () { log.sdBuild++; },
    _renderSDash: function () { log.sdRender++; },
    _sdShow: function (s) { log.sdShown.push(s); },
    _sdRelabelAria: function () { log.sdAria++; },
    _sdOverlay: { classList: { add: function () {}, remove: function () {} }, offsetWidth: 0, querySelector: function () { return null; } },
    _curUser: opts.user || null,
    _authEnabled: opts.authEnabled !== false,
    _prefSyncing: false,
    _prefHooked: false,
    _prefSaveTimer: null,
    _prefSavePending: null,
    _mmSharedAssetRoot: "/",
    getSupabaseClient: function () {
      return Promise.resolve({ auth: { updateUser: function (data) {
        // normalize cross-vm objects to host realm for assertions
        log.updateUser.push(JSON.parse(JSON.stringify(data)));
        return Promise.resolve({});
      } } });
    },
  };
  const windowObj = {
    hydrateMTF: function () { log.hydrate++; },
    addEventListener: function () {},
    removeEventListener: function () {},
  };
  if (opts.bridge) windowObj.MMXSharedShell = opts.bridge.api;
  if (opts.mmOnboard !== false) windowObj.MMOnboard = { open: function (m) { log.onboardOpen.push(m); } };
  sandbox.window = windowObj;
  const ctx = vm.createContext(sandbox);
  vm.runInContext(code, ctx, { filename: "owner-adapter-snippets(theme.js)" });
  // Synchronous preference-event consumers on the existing events.
  dom.document.addEventListener("themechange", function (e) { log.themes.push(e.detail); });
  dom.document.addEventListener("langchange", function (e) { log.langs.push(e.detail); });
  return {
    sandbox: sandbox, dom: dom, storage: storage, log: log, timers: timers,
    fireLastTimer: function () { const t = timers[timers.length - 1]; if (!t) return false; t.fn(); return true; },
    flushAllTimers: function () { const list = timers.slice(); timers.length = 0; list.forEach((t) => t.fn()); },
  };
}

test("theme.js bridge helpers exist and carry NO presented-state prerequisite", () => {
  for (const n of ["_mmShellBridge", "_mmShellApplying", "_mmShellAuthHandoff"]) {
    const body = extractFn(themeSrc, "templates/theme.js", n);
    assert.ok(!/\bactive\b/.test(body),
      n + " must be keyed on candidate existence / applyingContext only — it reads the presented flag");
  }
  const c = buildThemeContext({});
  assert.equal(c.sandbox._mmShellBridge(), null);
  assert.equal(c.sandbox._mmShellApplying(), false);
  assert.equal(c.sandbox._mmShellAuthHandoff("signin"), false);
});

test("candidate exists while the bridge is NOT yet presenting: applyingContext is observed anyway", () => {
  const b = makeBridge({ presented: false });
  const c = buildThemeContext({ bridge: b });
  b.st.applying = true;
  assert.equal(c.sandbox._mmShellApplying(), true);
  b.st.applying = false;
  assert.equal(c.sandbox._mmShellApplying(), false);
});

test("INITIAL bridge apply (presented=false, applyingContext=true): no storage writes, no account write, repaint + emit + existing handlers, no flourish, Auto survives", () => {
  const b = makeBridge({ presented: false });
  const c = buildThemeContext({ bridge: b, storage: { theme: "dark", themeAuto: "1", lang: "en" }, user: { id: "u1" } });
  c.sandbox._hookPrefSync();
  const err = bridgeApply(b, function () { c.sandbox.setTheme("light"); });
  assert.equal(err, null);
  assert.deepEqual(c.storage.writes, []);                      // nothing persisted…
  assert.equal(c.storage.getItem("theme"), "dark");            // …legacy value survives
  assert.equal(c.storage.getItem("themeAuto"), "1");           // Auto mode NOT ended
  assert.deepEqual(c.log.timers, []);                          // no debounce scheduled
  assert.equal(c.log.updateUser.length, 0);                    // no server write queued
  assert.equal(c.dom.docEl.attrs["data-theme"], "light");      // repaint happened
  assert.equal(c.log.charts, 1);
  assert.equal(c.log.segment, 1);
  assert.equal(c.log.hydrate, 1);
  assert.deepEqual(c.log.skyFx, []);                           // flourish suppressed
  assert.deepEqual(c.log.themes, ["light"]);                   // same detail shape, synchronous
  assert.match(c.dom.themeBtns[0].innerHTML, /Dark/);          // button relabel preserved
  assert.equal(b.st.applying, false);                          // bridge finally cleanup

  const err2 = bridgeApply(b, function () { c.sandbox.setLang("zh"); });
  assert.equal(err2, null);
  assert.equal(c.storage.getItem("lang"), "en");               // no lang persistence either
  assert.deepEqual(c.storage.writes, []);
  assert.equal(c.dom.docEl.attrs["data-lang"], "zh");
  assert.equal(c.dom.docEl.lang, "zh-CN");                     // WCAG lang sync is presentation: stays
  assert.deepEqual(c.log.langs, ["zh"]);
  assert.equal(c.dom.langBtns[0].textContent, "EN");           // relabel preserved
});

test("LATER bridge apply (presented=true, applyingContext=true): same no-write repaint semantics", () => {
  const b = makeBridge({ presented: true });
  const c = buildThemeContext({ bridge: b, storage: { theme: "dark", themeAuto: "1" }, user: { id: "u1" } });
  c.sandbox._hookPrefSync();
  bridgeApply(b, function () { c.sandbox.setTheme("light"); });
  assert.deepEqual(c.storage.writes, []);
  assert.equal(c.storage.getItem("themeAuto"), "1");
  assert.deepEqual(c.log.timers, []);
  assert.deepEqual(c.log.skyFx, []);
  assert.deepEqual(c.log.themes, ["light"]);
  bridgeApply(b, function () { c.sandbox.setLang("zh"); });
  assert.deepEqual(c.storage.writes, []);
  assert.deepEqual(c.log.langs, ["zh"]);
});

test("user-driven theme choice while the shell presents keeps the EXACT legacy persistence + flourish + pref-sync write", async () => {
  const b = makeBridge({ presented: true });
  const c = buildThemeContext({ bridge: b, storage: { theme: "dark", themeAuto: "1" }, user: { id: "u1" } });
  c.sandbox._hookPrefSync();
  c.sandbox.setTheme("light");                                 // not a bridge apply
  assert.deepEqual(c.storage.writes, [["theme", "light"], ["themeAuto", null]]);
  assert.deepEqual(c.log.skyFx, ["light"]);
  assert.deepEqual(c.log.timers, [800]);                       // legacy debounce armed
  assert.ok(c.fireLastTimer());
  await new Promise(function (r) { setImmediate(r); });
  assert.equal(c.log.updateUser.length, 1);
  // the incumbent call shape: sb.auth.updateUser({ data: {...})
  assert.deepEqual(c.log.updateUser[0], { data: { theme: "light", theme_auto: "0" } });
});

test("standalone (no candidate): byte-equivalent legacy behavior incl. late server prefs with the _prefSyncing loop guard", () => {
  const c = buildThemeContext({ storage: {}, user: { id: "u1" } });
  c.sandbox._hookPrefSync();
  c.sandbox.setTheme("light");
  assert.deepEqual(c.storage.writes, [["theme", "light"], ["themeAuto", null]]);
  assert.deepEqual(c.log.skyFx, ["light"]);
  c.log.timers.length = 0;
  c.storage.writes.length = 0;
  // late server prefs: applied exactly as before (theme + Auto + lang), with the
  // existing _prefSyncing guard swallowing the echo saves it fires.
  c.sandbox._applyServerPrefs({ user_metadata: { theme: "dark", lang: "zh", theme_auto: "1" } });
  assert.equal(c.dom.docEl.attrs["data-theme"], "dark");
  assert.equal(c.log.auto, 1);
  assert.equal(c.dom.docEl.attrs["data-lang"], "zh");
  assert.deepEqual(c.log.timers, []);
  // no parallel preference namespace is ever minted
  for (const k of c.storage.keysUsed()) {
    assert.ok(LEGACY_PREF_KEYS.indexOf(k) !== -1, "unexpected storage key written: " + k);
  }
});

test("candidate present (pre-INIT window included): late _applyServerPrefs never fights the parent context", () => {
  for (const presented of [false, true]) {
    const b = makeBridge({ presented: presented });
    const c = buildThemeContext({ bridge: b, storage: { theme: "light", lang: "en" } });
    c.sandbox._hookPrefSync();
    c.sandbox._applyServerPrefs({ user_metadata: { theme: "dark", lang: "zh", theme_auto: "1" } });
    assert.equal(c.dom.docEl.attrs["data-theme"], "dark", "presented=" + presented);   // untouched repaint
    assert.equal(c.dom.docEl.attrs["data-lang"], "en", "presented=" + presented);
    assert.equal(c.log.auto, 0);
    assert.deepEqual(c.storage.writes, []);
    assert.deepEqual(c.log.themes, []);
    assert.deepEqual(c.log.langs, []);
  }
});

test("setter exception during a bridge apply: bridge finally clears suppression; the apply persisted nothing; a later user choice still persists", () => {
  const b = makeBridge({ presented: false });
  const c = buildThemeContext({ bridge: b, storage: {}, user: { id: "u1" } });
  c.sandbox._hookPrefSync();
  c.sandbox.themeCharts = function () { throw new Error("chart boom"); };
  const err = bridgeApply(b, function () { c.sandbox.setTheme("light"); });
  assert.ok(err instanceof Error);
  assert.equal(b.st.applying, false);                          // cleanup handled (bridge-side finally)
  assert.equal(c.dom.docEl.attrs["data-theme"], "light");      // repaint happened before the throw
  assert.deepEqual(c.storage.writes, []);                      // but persisted nothing
  assert.deepEqual(c.log.themes, []);                          // dispatch never reached
  c.sandbox.themeCharts = function () { c.log.charts++; };
  c.sandbox.setTheme("dark");                                  // post-apply user choice: legacy intact
  assert.deepEqual(c.storage.writes.map((w) => w[0]), ["theme", "themeAuto"]);
  assert.deepEqual(c.log.timers, [800]);
});

test("_mmOpenOnboard is the single auth seam: fixed tokens, claims pre-INIT (queue-safe), never opens an in-frame sheet or lazy-loads the script", () => {
  const b = makeBridge({ presented: false });
  const c = buildThemeContext({ bridge: b });
  c.sandbox._mmOpenOnboard("signup");
  c.sandbox._mmOpenOnboard(undefined);
  c.sandbox._mmOpenOnboard("upgrade");
  c.sandbox._mmOpenOnboard("reset");                           // whitelist default → signin
  assert.deepEqual(b.calls.map((x) => x.intent), ["signup", "signin", "billing", "signin"]);
  assert.deepEqual(b.calls.map((x) => x.presented), [false, false, false, false]);
  assert.deepEqual(c.log.onboardOpen, []);                     // no MMOnboard.open
  assert.deepEqual(c.dom.document.injected, []);               // no lazy script load
  assert.equal(c.sandbox.window.__mmOnboardLoading, undefined);
});

test("standalone _mmOpenOnboard keeps the legacy sheet route and lazy-load fallback", () => {
  const c = buildThemeContext({});
  c.sandbox._mmOpenOnboard("upgrade");
  assert.deepEqual(c.log.onboardOpen, ["upgrade"]);
  const c2 = buildThemeContext({ mmOnboard: false });
  c2.sandbox._mmOpenOnboard("signin");
  assert.equal(c2.dom.document.injected.length, 1);            // the original load path, untouched
});

test("_openSDash is the single settings seam: 'settings' intent only, section never forwarded, dash never built; exactly one intent per entry", () => {
  const b = makeBridge({ presented: true });
  const c = buildThemeContext({ bridge: b, user: { id: "u1" } });
  c.sandbox._openSDash("account");
  assert.equal(b.calls.length, 1);
  assert.deepEqual(b.calls[0], { intent: "settings", presented: true, applying: false });
  assert.equal(c.log.sdBuild, 0);
  assert.equal(c.log.sdRender, 0);
  c.sandbox._openSDash();
  assert.equal(b.calls.length, 2);                             // one per explicit entry — no seam duplicates
  assert.equal(c.log.sdBuild, 0);
});

test("standalone _openSDash still builds and shows the dashboard", () => {
  const c = buildThemeContext({ user: { id: "u1" } });
  c.sandbox._openSDash("account");
  assert.equal(c.log.sdBuild, 1);
  assert.equal(c.log.sdRender, 1);
  assert.deepEqual(c.log.sdShown, ["account"]);
});

test("theme.js guard topology: seam count is exact and public auth/settings exports stay guard-free", () => {
  assert.ok(themeSrc.includes("    open: function (mode) { _mmOpenOnboard(mode || 'signin'); },"));
  assert.ok(themeSrc.includes("  window.MMSettings = { open: function (section) { _openSDash(section); }, close: _closeSDash };"));
  assert.equal((themeSrc.match(/_mmShellAuthHandoff\(/g) || []).length, 3,
    "_mmShellAuthHandoff must appear exactly at its definition plus the _mmOpenOnboard and _openSDash seams");
  const st = extractFn(themeSrc, "templates/theme.js", "setTheme");
  assert.ok(/var shellApply = _mmShellApplying\(\);/.test(st));
  assert.ok(/if \(!shellApply\) skyToggleFx\(tm\);/.test(st));
  assert.ok(/_prefSyncing \|\| _mmShellApplying\(\) \|\| !_curUser/.test(
    extractFn(themeSrc, "templates/theme.js", "_savePrefToServer")));
  assert.ok(/if \(_mmShellBridge\(\)\) return;/.test(
    extractFn(themeSrc, "templates/theme.js", "_applyServerPrefs")));
});

// -------------------------------------------------------------- account.js ---
function buildAccountContext(opts) {
  opts = opts || {};
  const names = ["_mmShellPresent", "_mmShellApplying", "_acctKey", "curTheme", "applyPrefs", "persistPref", "claimsPref"];
  const code = extractAll(accountSrc, "templates/account.js", names);
  const dom = makeDom();
  const storage = makeStorage({});
  const timers = [];
  const log = { setTheme: [], setLang: [], prefState: [], flush: 0, timers: [] };
  const sandbox = {
    document: dom.document,
    localStorage: storage,
    setTimeout: function (fn, ms) { timers.push({ fn: fn, ms: ms }); log.timers.push(ms); return timers.length; },
    clearTimeout: function () {},
    _hydrating: false,
    _authApplying: false,
    _mounted: true,
    state: opts.state || { loaded: true, unavail: false, acct: { authenticated: true, id: "u1", email: "a@b.test" } },
    _prefPending: {}, _prefOwner: "", _prefState: {}, _prefFlight: null, _prefTimer: null, _wgen: 1,
    _setPrefState: function (k, s) { log.prefState.push([k, s]); },
    _flushPrefs: function () { log.flush++; },
  };
  const windowObj = {
    setTheme: function (v) { log.setTheme.push(v); },
    setLang: function (v) { log.setLang.push(v); },
    addEventListener: function () {},
    removeEventListener: function () {},
  };
  if (opts.bridge) windowObj.MMXSharedShell = opts.bridge.api;
  sandbox.window = windowObj;
  const ctx = vm.createContext(sandbox);
  vm.runInContext(code, ctx, { filename: "owner-adapter-snippets(account.js)" });
  return { sandbox: sandbox, dom: dom, storage: storage, log: log, timers: timers };
}

test("account.js helpers exist and carry NO presented-state prerequisite", () => {
  for (const n of ["_mmShellPresent", "_mmShellApplying"]) {
    const body = extractFn(accountSrc, "templates/account.js", n);
    assert.ok(!/\bactive\b/.test(body), n + " reads the presented flag");
  }
  const c = buildAccountContext({});
  assert.equal(c.sandbox._mmShellPresent(), false);
  assert.equal(c.sandbox._mmShellApplying(), false);
});

test("late account hydration never overrides a qualified parent context (pre-INIT included)", () => {
  const b = makeBridge({ presented: false });
  const c = buildAccountContext({ bridge: b });
  c.sandbox.applyPrefs({ authenticated: true, prefs: { theme: "light", lang: "zh" } });
  assert.deepEqual(c.log.setTheme, []);
  assert.deepEqual(c.log.setLang, []);
  assert.equal(c.dom.docEl.attrs["data-theme"], "dark");       // nothing repainted by hydration
  assert.equal(c.sandbox._hydrating, false);
});

test("standalone applyPrefs still hydrates exactly as before", () => {
  const c = buildAccountContext({});
  c.sandbox.applyPrefs({ authenticated: true, prefs: { theme: "light", lang: "zh" } });
  assert.deepEqual(c.log.setTheme, ["light"]);
  assert.deepEqual(c.log.setLang, ["zh"]);
  assert.equal(c.sandbox._hydrating, false);                   // fence released
});

test("persistPref queues NOTHING during a bridge apply (initial window included) but keeps the user-edit queue", () => {
  const b = makeBridge({ presented: false });
  const c = buildAccountContext({ bridge: b });
  bridgeApply(b, function () { c.sandbox.persistPref("theme", "light"); });
  assert.deepEqual(Object.keys(c.sandbox._prefPending), []);
  assert.deepEqual(c.log.timers, []);
  assert.deepEqual(c.log.prefState, []);
  // user edit while the shell presents: legacy queue intact
  c.sandbox.persistPref("theme", "dark");
  assert.equal(c.sandbox._prefPending.theme, "dark");
  assert.deepEqual(c.log.timers, [500]);
  assert.deepEqual(c.log.prefState, [["theme", "queued"]]);
});

test("claimsPref stays exactly symmetric with the persistPref guard (single-owner handshake)", () => {
  const b = makeBridge({ presented: true });
  const c = buildAccountContext({ bridge: b });
  assert.equal(c.sandbox.claimsPref("theme"), true);           // user window: account panel owns it
  assert.equal(c.sandbox.claimsPref("alert_categories"), false);
  b.st.applying = true;
  assert.equal(c.sandbox.claimsPref("theme"), false);          // during apply: neither writer claims
  assert.equal(c.sandbox.claimsPref("lang"), false);
  b.st.applying = false;
  c.sandbox._authApplying = true;                              // legacy fences keep their roles
  assert.equal(c.sandbox.claimsPref("theme"), false);
  c.sandbox._authApplying = false;
  c.sandbox.state.acct = { authenticated: false };
  assert.equal(c.sandbox.claimsPref("theme"), false);
});

test("account.js guard wiring and the untouched MMAccount export", () => {
  assert.ok(/if \(_mmShellPresent\(\)\) return;/.test(
    extractFn(accountSrc, "templates/account.js", "applyPrefs")));
  assert.ok(/_hydrating \|\| _authApplying \|\| _mmShellApplying\(\)/.test(
    extractFn(accountSrc, "templates/account.js", "persistPref")));
  assert.ok(/_hydrating \|\| _authApplying \|\| _mmShellApplying\(\)/.test(
    extractFn(accountSrc, "templates/account.js", "claimsPref")));
  assert.ok(accountSrc.includes("    claimsPref: function (key) { try { return claimsPref(key); } catch (e) { return false; } }"));
});

// -------------------------------------------------------------- onboard.js ---
function buildOnboardContext(opts) {
  opts = opts || {};
  const names = ["normTier", "_mmShellHandoff", "openSheet"];
  const code = extractAll(onboardSrc, "templates/onboard.js", names);
  const dom = makeDom();
  const S = {
    mode: null, step: 0, plan: "essential", period: "annual", prefs: {},
    firstName: "", lastName: "", email: "", password: "", password2: "",
    confirmPending: false, open: false, compare: false,
  };
  const scrim = { style: {}, classList: { add: function (c) { (scrim.added = scrim.added || []).push(c); }, remove: function () {} } };
  const el = { scrim: scrim, body: null, foot: null };
  const log = { ensure: 0, build: 0, render: 0, redraw: 0, nudge: 0, stash: 0, skin: 0, upgrade: 0, reset: 0, raf: 0 };
  const handle = { upgradeOpts: null };
  const sandbox = {
    document: dom.document,
    location: { pathname: "/index.html", search: "", hash: "", hostname: "www.mastermind-x.com", origin: "https://www.mastermind-x.com" },
    setTimeout: function () { return 0; },
    clearTimeout: function () {},
    localStorage: makeStorage({}),
    sessionStorage: makeStorage({}),
    requestAnimationFrame: function (cb) { log.raf++; cb(); },
    URLSearchParams: function (q) { return new (require("node:url").URLSearchParams)(q); },
    TIER_ALIAS: { insider: "essential" },
    ensureAssets: function () { log.ensure++; },
    build: function () { log.build++; },
    sbClient: function () { return Promise.resolve(null); },
    syncSkin: function () { log.skin++; },
    render: function () { log.render++; },
    redrawDesk: function () { log.redraw++; },
    nudgeIdle: function () { log.nudge++; },
    stashSave: function () { log.stash++; },
    armReset: function () { log.reset++; },
    openUpgrade: function (o) { log.upgrade++; handle.upgradeOpts = o; },
    STEP_ACCOUNT: 1, STEP_PREFS: 2, STEP_PLAN: 3,
    S: S, el: el,
  };
  const windowObj = { addEventListener: function () {}, removeEventListener: function () {} };
  if (opts.bridge) windowObj.MMXSharedShell = opts.bridge.api;
  sandbox.window = windowObj;
  const ctx = vm.createContext(sandbox);
  vm.runInContext(code, ctx, { filename: "owner-adapter-snippets(onboard.js)" });
  return { sandbox: sandbox, dom: dom, S: S, el: el, log: log, handle: handle };
}

test("onboard _mmShellHandoff: existence-keyed, fixed tokens only, false without a candidate, no presented read", () => {
  const body = extractFn(onboardSrc, "templates/onboard.js", "_mmShellHandoff");
  assert.ok(!/\bactive\b/.test(body), "_mmShellHandoff reads the presented flag");
  const c = buildOnboardContext({});
  assert.equal(c.sandbox._mmShellHandoff("signin"), false);    // standalone: legacy path survives
  const b = makeBridge({ presented: false });
  const c2 = buildOnboardContext({ bridge: b });
  assert.equal(c2.sandbox._mmShellHandoff("signup"), true);    // claims pre-INIT (bridge.openAuth queues)
  assert.equal(c2.sandbox._mmShellHandoff("upgrade"), true);
  assert.deepEqual(b.calls.map((x) => x.intent), ["signup", "billing"]);
  assert.deepEqual(b.calls.map((x) => x.presented), [false, false]);
});

test("openSheet is the single sheet seam: every opener hands off, opts never cross, no in-frame build, upgrade lane unreachable", () => {
  const b = makeBridge({ presented: false });
  const c = buildOnboardContext({ bridge: b });
  c.sandbox.openSheet("upgrade", { plan: "pro", period: "annual" });
  c.sandbox.openSheet("signup", {});
  c.sandbox.openSheet("reset", {});                            // recovery converges to signin
  c.sandbox.openSheet("signin");
  assert.deepEqual(b.calls.map((x) => x.intent), ["billing", "signup", "signin", "signin"]);
  assert.equal(c.log.build, 0);
  assert.equal(c.log.ensure, 0);
  assert.equal(c.log.upgrade, 0);                              // guard precedes the upgrade branch
  assert.equal(c.S.mode, null);
  assert.deepEqual(Object.keys(c.handle), ["upgradeOpts"]);
});

test("standalone openSheet keeps the exact legacy modes/opts flow (sign-in/sign-up/upgrade routing intact)", () => {
  const c = buildOnboardContext({});
  c.sandbox.openSheet("signin", { plan: "pro", period: "annual", resume: false });
  assert.equal(c.log.build, 1);
  assert.equal(c.S.mode, "signin");
  assert.equal(c.S.plan, "pro");                               // normTier seam preserved (real function)
  assert.equal(c.S.period, "annual");
  assert.equal(c.S.step, 1);
  assert.equal(c.S.open, true);
  assert.equal(c.el.scrim.style.display, "flex");
  assert.equal(c.log.raf, 1);
  assert.equal(c.log.stash, 1);
  const opts = { me: { tier: "pro" } };
  c.sandbox.openSheet("upgrade", opts);
  assert.equal(c.log.upgrade, 1);
  assert.equal(c.handle.upgradeOpts, opts);                    // opts pass through untouched standalone
});

test("onboard guards are centralized: exactly two _mmShellHandoff sites, export line byte-identical", () => {
  assert.equal((onboardSrc.match(/_mmShellHandoff\(/g) || []).length, 2,
    "_mmShellHandoff must appear only at its definition plus the single openSheet call site");
  assert.ok(onboardSrc.includes("  window.MMOnboard = { open: openSheet, close: closeSheet, applyChrome: applyAuthChrome };"));
  const body = extractFn(onboardSrc, "templates/onboard.js", "openSheet");
  assert.ok(body.indexOf("_mmShellHandoff(") !== -1 && body.indexOf("_mmShellHandoff(") < body.indexOf("openUpgrade(opts"),
    "the guard must precede the upgrade branch");
});

// ------------------------------------------------------------- cross-file ----
test("storage hygiene: nowhere does the adapter introduce a parallel preference key", () => {
  const b = makeBridge({ presented: true });
  const c = buildThemeContext({ bridge: b, storage: { theme: "dark", themeAuto: "1" }, user: { id: "u1" } });
  c.sandbox._hookPrefSync();
  c.sandbox.setTheme("light");
  c.sandbox.setLang("zh");
  for (const k of c.storage.keysUsed()) {
    assert.ok(LEGACY_PREF_KEYS.indexOf(k) !== -1, "unexpected storage key written: " + k);
  }
});

test("adapter adds no browser/runtime requirements: extracted seams never reference fetch/XHR/cookie/timer APIs beyond the incumbent ones", () => {
  // The seams this artifact edits must still not gain network or cookie access.
  const seams = [
    extractFn(themeSrc, "templates/theme.js", "setTheme"),
    extractFn(themeSrc, "templates/theme.js", "setLang"),
    extractFn(themeSrc, "templates/theme.js", "_mmOpenOnboard"),
    extractFn(themeSrc, "templates/theme.js", "_openSDash"),
    extractFn(themeSrc, "templates/theme.js", "_mmShellAuthHandoff"),
    extractFn(accountSrc, "templates/account.js", "persistPref"),
    extractFn(accountSrc, "templates/account.js", "claimsPref"),
    extractFn(onboardSrc, "templates/onboard.js", "openSheet"),
    extractFn(onboardSrc, "templates/onboard.js", "_mmShellHandoff"),
  ];
  for (const s of seams) {
    assert.ok(!/\bfetch\s*\(/.test(s), "seam references fetch()");
    assert.ok(!/\bXMLHttpRequest\b/.test(s), "seam references XMLHttpRequest");
    assert.ok(!/document\.cookie/.test(s), "seam reads document.cookie");
  }
});
