'use strict';
/*
 * shared_shell_terminal_handoff.test.cjs
 *
 * Behavioural verification, under `node --test` and WITHOUT a browser, of the
 * Shared Shell terminal compatibility repair (run
 * shared-shell-terminal-compatibility-20261018-c1-r1, parent
 * shared-shell-production-20261018-c1).
 *
 * Anti-tautology rule: every shipped function executed here is EXTRACTED
 * verbatim from the repo-relative sources below - the candidate gate and the
 * five handoff helpers plus the whole openInternal() body from
 * templates/terminal_overlay.js, and the real Terminal-launch chain from
 * templates/stocktable.js. Only fixtures (a recording Location, overlay/history/
 * body-lock counters, and MMXSharedShell candidates that queue, accept or refuse
 * with the supplied bridge semantics) and the expected destinations live in this
 * file. Missing files or anchors fail loudly; nothing silently skips, and a
 * semantics change in the shipped seams moves these tests.
 *
 * Mocked execution is NOT browser acceptance. These tests prove the shipped
 * seams' decisions - ordering (handoff before any overlay build/frame/history/
 * body-lock), strict native-URL admission, the admitted RELATIVE /terminal
 * destination, retained safe symbol/AI/return scope, dropped embed-only
 * parameters and secrets, and the refusal/claim paths. Real Next/Caddy response
 * bytes, real beta -> www -> app nesting, adoption, testing and deployment
 * remain owned by the attended parent.
 *
 * Where to run: place this file one directory under the macro repo root (e.g.
 * tests/) and run `node --test` from that root, or set MMX_TC_SOURCE_ROOT (a
 * directory containing macro/ and mastermind-terminal/), MMX_MACRO_SOURCE_ROOT
 * and/or MMX_TERMINAL_SOURCE_ROOT.
 */
const { test } = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const APP_ORIGIN = 'https://app.mastermind-x.com';
const LEGACY_ORIGIN = 'https://www.mastermind-x.com';
const APEX_ORIGIN = 'https://mastermind-x.com';
const SHELL_ORIGIN = 'https://beta.mastermind-x.com';
const MAX_URL = 8192; // the supplied bridge's own bound, asserted, never mirrored as logic

/* ---- explicit repo-relative source extraction ---- */
function rootsFor(envName, prefixes) {
  const roots = [];
  if (process.env[envName]) roots.push(process.env[envName]);
  if (process.env.MMX_TC_SOURCE_ROOT) {
    for (const p of prefixes) roots.push(path.join(process.env.MMX_TC_SOURCE_ROOT, p));
  }
  roots.push(process.cwd());
  for (const p of prefixes) roots.push(path.join(process.cwd(), p));
  roots.push(path.resolve(__dirname, '..'));
  roots.push(path.resolve(__dirname, '..', '..'));
  for (const p of prefixes) roots.push(path.resolve(__dirname, '..', '..', p));
  return roots;
}
const MACRO_ROOTS = rootsFor('MMX_MACRO_SOURCE_ROOT', ['macro', path.join('..', 'macro')]);
const TERMINAL_ROOTS = rootsFor('MMX_TERMINAL_SOURCE_ROOT',
  ['terminal', path.join('mastermind-terminal', 'terminal'), path.join('..', 'mastermind-terminal', 'terminal')]);

function readSource(roots, rel, label) {
  const tried = [];
  for (const root of roots) {
    const p = path.join(root, rel);
    tried.push(p);
    if (fs.existsSync(p)) return fs.readFileSync(p, 'utf8');
  }
  throw new Error(label + ' source missing: ' + rel + ' (tried: ' + tried.join(' | ') + ')');
}
function overlaySrc() { return readSource(MACRO_ROOTS, 'templates/terminal_overlay.js', 'terminal_overlay'); }
function stocktableSrc() { return readSource(MACRO_ROOTS, 'templates/stocktable.js', 'stocktable'); }

/* balanced-block extraction, string/regexp-and-comment aware. An if/else chain
 * is ONE block for our purposes: when depth returns to zero and `else` follows,
 * the scan continues, so STOCK_CHAIN is the complete shipped decision tree. */
function braceMatched(text, startAnchor, label) {
  const i = text.indexOf(startAnchor);
  assert.ok(i !== -1, label + ': start anchor missing: ' + startAnchor);
  let depth = 0, k = text.indexOf('{', i), inStr = null;
  for (; k < text.length; k++) {
    const c = text[k];
    if (inStr) { if (c === '\\') k++; else if (c === inStr) inStr = null; continue; }
    if (c === '"' || c === "'" || c === '`') { inStr = c; continue; }
    if (c === '/' && text[k + 1] === '/') { k = text.indexOf('\n', k); if (k === -1) break; continue; }
    if (c === '/' && text[k + 1] === '*') { const e = text.indexOf('*/', k); k = e === -1 ? text.length : e + 1; continue; }
    if (c === '{') depth++;
    else if (c === '}') {
      depth--;
      if (depth === 0) {
        const cont = /^\s*else\b/.exec(text.slice(k + 1));
        if (!cont) return text.slice(i, k + 1);
        k += cont[0].length;
      }
    }
  }
  throw new Error(label + ': unbalanced block');
}
function extractFn(text, name, label) { return braceMatched(text, 'function ' + name + '(', label + '.' + name); }
function countOf(hay, needle) { return hay.split(needle).length - 1; }

/* the shipped handoff implementation, as one executable prelude */
const HANDOFF_HELPERS = [
  'mmxSharedShellNativeURL',
  'mmxSharedShellReturnOrigin',
  'mmxSharedShellSafeReturn',
  'mmxSharedShellTerminalDestination',
  'mmxSharedShellTerminalHandoff',
].map((n) => extractFn(overlaySrc(), n, 'handoff')).join('\n');
const OPEN_INTERNAL = braceMatched(overlaySrc(), 'function openInternal(config) {', 'openInternal');
/* the shipped stock-table launch chain, verbatim (if / else-if candidate / else) */
const STOCK_CHAIN = braceMatched(stocktableSrc(), 'if (T && T.on && T.on() && T.open) {', 'stocktable-chain');

/* ---- fixtures ---- */
function makeLocation(initial) {
  const base = new URL(initial || (LEGACY_ORIGIN + '/china_lookup.html#NVDA'));
  const rec = { hrefWrites: [], replaced: [], assigned: [], hashWrites: [] };
  const loc = {
    origin: base.origin, hostname: base.hostname, protocol: base.protocol,
    pathname: base.pathname, search: base.search, hash: base.hash,
  };
  let href = base.href;
  Object.defineProperty(loc, 'href', {
    get: function () { return href; },
    set: function (v) { rec.hrefWrites.push(String(v)); rec.assigned.push(String(v)); },
  });
  Object.defineProperty(loc, 'hash', {
    get: function () { return base.hash; },
    set: function (v) { rec.hashWrites.push(String(v)); },
  });
  loc.replace = function (u) { rec.replaced.push(String(u)); };
  loc.assign = function (u) { rec.assigned.push(String(u)); };
  return { loc: loc, rec: rec };
}
/* Candidate bridges mirror the OBSERVED contract of the supplied
 * mmx.shared-shell.v1 child bridge, not its code: navigate(href, mode) accepts
 * only push/replace, records the destination, and returns true when the href is
 * admitted (queued pre-INIT or performed when active) or false when refused.
 * Pre-INIT acceptance performs NO local transition, so a seam that mutated
 * Location after a claimed handoff would be visible in the recording. */
function makeBridge(kind, extra) {
  const b = { kind: kind, calls: [], navigate: function (href, mode) {
    b.calls.push([String(href), mode]);
    if (kind === 'refuse') return false;
    return true;
  } };
  Object.defineProperty(b, 'active', { get: function () { return kind === 'active'; } });
  return Object.assign(b, extra || {});
}
function overlayCounters() {
  return { opened: 0, buildOverlay: 0, createFrame: 0, ensureFrame: 0, destroyFrame: 0,
    freshMobileLaunchUrl: 0, lockDashboard: 0, unlockDashboard: 0, armHistoryGuard: 0,
    releaseHistoryGuard: 0, consumeHistoryGuard: 0, showToast: 0, beginLoading: 0,
    setLaunchOrigin: 0, postMessages: 0, timers: 0, documentListeners: 0 };
}
function overlayRoot() {
  return { setAttribute: function () {}, removeAttribute: function () {},
    classList: { add: function () {}, remove: function () {}, contains: function () { return false; } },
    querySelector: function () { return null; }, offsetWidth: 100 };
}
function runIn(code, sandbox) { vm.runInNewContext(code, sandbox); return sandbox; }

/* Incumbent owner definitions (theme.js terminalUrl/terminalEmbedUrl, supplied
 * as owner excerpts) produce exactly these two absolute app URLs; the app route
 * is the canonical '/' variant in the portal URL and the explicit '/terminal'
 * variant in the direct URL. */
function incumbentConfig(opts) {
  opts = opts || {};
  const base = opts.base === undefined ? APP_ORIGIN + '/terminal' : opts.base;
  const ticker = opts.ticker === undefined ? 'NVDA' : opts.ticker;
  const ret = opts.ret === undefined ? (LEGACY_ORIGIN + '/china_lookup.html#NVDA') : opts.ret;
  const qs = function (extra) {
    const parts = [];
    if (ticker) parts.push('sym=' + encodeURIComponent(ticker));
    parts.push('from=macro');
    if (ret !== null) parts.push('ret=' + encodeURIComponent(ret));
    if (opts.ai) parts.push('ai=1');
    if (extra) parts.push(extra);
    return '?' + parts.join('&');
  };
  const directUrl = base + qs(null);
  const embedUrl = base + qs('embed=dashboard');
  return {
    symbol: opts.symbol === undefined ? ticker : opts.symbol,
    url: opts.url === undefined ? embedUrl : opts.url,
    directUrl: opts.directUrl === undefined ? directUrl : opts.directUrl,
    targetOrigin: opts.targetOrigin === undefined ? APP_ORIGIN : opts.targetOrigin,
    trigger: null, returnFocus: null,
  };
}

/* run the shipped openInternal() with the shipped helpers, against a candidate
 * or a standalone document, and return every observable side effect */
function launchOverlay(opts) {
  opts = opts || {};
  const lf = makeLocation(opts.documentHref);
  const st = overlayCounters();
  const root = opts.noRoot ? null : overlayRoot();
  const frame = opts.noFrame ? null : { isConnected: true, contentWindow: {
    postMessage: function () { st.postMessages++; } } };
  const sandbox = {
    URL: URL, URLSearchParams: URLSearchParams, encodeURIComponent: encodeURIComponent,
    decodeURIComponent: decodeURIComponent, String: String, Number: Number, Object: Object,
    Array: Array, Date: Date, Math: Math, setTimeout: function () { st.timers++; return 1; },
    clearTimeout: function () {}, requestAnimationFrame: function () {},
    location: lf.loc,
    document: { activeElement: null, body: {}, head: {},
      getElementById: function () { return null; },
      querySelector: function () { return null; },
      addEventListener: function () { st.documentListeners++; },
      createElement: function () { return { style: {}, setAttribute: function () {} }; } },
    window: {
      location: lf.loc,
      MMXSharedShell: opts.bridge || undefined,
      MM_TERMINAL_BASE: opts.base === undefined ? APP_ORIGIN + '/terminal' : opts.base,
      addEventListener: function () {}, removeEventListener: function () {},
      dispatchEvent: function () {},
    },
    // shipped handoff helpers, extracted verbatim
    prelude: HANDOFF_HELPERS,
    // incumbent overlay internals, stubbed to counters (never reimplemented)
    isDashboardHost: function () { return opts.hostOff !== true; },
    buildOverlay: function () { st.buildOverlay++; return root; },
    createFrame: function () { st.createFrame++; return frame; },
    ensureFrame: function () { st.ensureFrame++; return frame; },
    destroyFrame: function () { st.destroyFrame++; },
    freshMobileLaunchUrl: function (u) { st.freshMobileLaunchUrl++; return u; },
    shouldRemountFrame: function () { return false; },
    setLaunchOrigin: function () { st.setLaunchOrigin++; },
    lockDashboard: function () { st.lockDashboard++; },
    unlockDashboard: function () { st.unlockDashboard++; },
    armHistoryGuard: function () { st.armHistoryGuard++; },
    releaseHistoryGuard: function () { st.releaseHistoryGuard++; },
    consumeHistoryGuard: function () { st.consumeHistoryGuard++; },
    showToast: function () { st.showToast++; },
    beginLoading: function () { st.beginLoading++; },
    startSlowTimer: function () {}, scheduleShellFallback: function () {},
    scheduleFrameLoadFallback: function () {}, markReady: function () {},
    state: { open: true, booted: false, ready: false, path: '', symbol: '', frame: frame,
      overlay: root, loader: null, toast: null, slow: null, newTab: {},
      closeTimer: 0, targetOrigin: '', directUrl: '', lastConfig: null },
    config: opts.config === undefined ? incumbentConfig(opts) : opts.config,
  };
  runIn(sandbox.prelude + '\n' + OPEN_INTERNAL + '\nopenInternal(config);', sandbox);
  delete sandbox.prelude;
  return { st: st, lf: lf, bridge: opts.bridge, sandbox: sandbox };
}

/* ===================================================================== *
 * 1. shipped-text invariants
 * ===================================================================== */
test('terminal_overlay: the candidate handoff is the first decision in openInternal, before host check and overlay build', function () {
  const call = OPEN_INTERNAL.indexOf('mmxSharedShellTerminalHandoff(config)');
  assert.ok(call !== -1, 'handoff gate missing from the shipped openInternal');
  assert.ok(call < OPEN_INTERNAL.indexOf('isDashboardHost()'), 'gate must precede the dashboard-host branch');
  assert.ok(call < OPEN_INTERNAL.indexOf('buildOverlay()'), 'gate must precede any overlay build');
  assert.ok(/if \(mmxSharedShellTerminalHandoff\(config\)\) return;/.test(OPEN_INTERNAL),
    'the gate must return, not fall through to the portal');
});
test('terminal_overlay: the gate keys on candidate presence, never on bridge .active (pre-INIT included)', function () {
  assert.ok(!/_ss\d?\.active|MMXSharedShell\s*\.\s*active/.test(overlaySrc()),
    'an .active gate reintroduced would strand the pre-INIT window on the nested overlay');
  assert.ok(overlaySrc().includes('window.MMXSharedShell'), 'presence gate missing');
  assert.strictEqual(countOf(overlaySrc(), 'window.MDXTerminalOverlay ='), 1, 'single overlay surface');
});
test('terminal_overlay: existing direct-parent messaging semantics and guards are untouched', function () {
  const text = overlaySrc();
  assert.ok(text.includes("    if (!state.frame || event.source !== state.frame.contentWindow) return;"),
    'the source===frame.contentWindow guard must be exactly as shipped');
  assert.ok(text.includes("    if (event.origin !== state.targetOrigin) return;"),
    'the targetOrigin (apex/www-derived) guard must be exactly as shipped');
  assert.strictEqual(countOf(text, 'postMessage('), 1, 'no new postMessage surface (no relay invented)');
  assert.ok(!/targetOrigin\s*===|indexOf\(['"]https?:\/\/(beta|app)\./.test(text),
    'the messaging allowlist must not be widened by the repair');
  assert.ok(!SHELL_ORIGIN_RE().test(text), 'the shell origin must never be baked into the launch owner');
});
function SHELL_ORIGIN_RE() { return /beta\.mastermind-x\.com/; }
test('terminal_overlay: no invented surfaces - no storage, network, CSP or route-registry logic in the launch owner', function () {
  const text = overlaySrc();
  for (const banned of ['localStorage', 'sessionStorage', 'document.cookie', 'fetch(', 'XMLHttpRequest',
    'eval(', 'import(', 'Content-Security-Policy', 'frame-ancestors', 'X-Frame-Options']) {
    assert.ok(!text.includes(banned), 'unexpected ' + banned + ' in templates/terminal_overlay.js');
  }
});
test('terminal_overlay: the handoff surface is exposed for the stock-table fallback (one admission rule)', function () {
  const text = overlaySrc();
  assert.ok(/terminalHandoff:\s*mmxSharedShellTerminalHandoff/.test(text), 'handoff not exposed');
  assert.ok(/terminalDestination:\s*mmxSharedShellTerminalDestination/.test(text), 'normalizer not exposed');
  assert.ok(/open: function \(config\) \{ openInternal\(config\); \}/.test(text), 'incumbent open() semantics changed');
  assert.ok(/close: requestClose/.test(text) && /isOpen: function \(\) \{ return state\.open; \}/.test(text),
    'incumbent close/isOpen changed');
});

/* ===================================================================== *
 * 2. openInternal behaviour: candidate, standalone, refused, invalid
 * ===================================================================== */
test('standalone (no bridge): the incumbent overlay portal still builds, frames and animates', function () {
  const r = launchOverlay({});
  assert.strictEqual(r.st.buildOverlay, 1);
  assert.strictEqual(r.st.ensureFrame, 1);
  assert.strictEqual(r.st.beginLoading, 1, 'branded loader path kept');
  assert.strictEqual(r.st.lockDashboard, 0, 'state.open=true skips re-lock, as before');
  assert.deepStrictEqual(r.lf.rec.hrefWrites, [], 'standalone overlay must not navigate');
});
test('standalone non-dashboard host: raw Location fallback is byte-identical to the incumbent', function () {
  const r = launchOverlay({ hostOff: true });
  assert.deepStrictEqual(r.lf.rec.hrefWrites, [incumbentConfig().directUrl]);
  assert.strictEqual(r.st.buildOverlay, 0);
});
test('standalone no-root / no-frame fallbacks: raw Location to directUrl, unchanged', function () {
  for (const opts of [{ noRoot: true }, { noFrame: true }]) {
    const r = launchOverlay(opts);
    assert.deepStrictEqual(r.lf.rec.hrefWrites, [incumbentConfig().directUrl], JSON.stringify(opts));
  }
});
test('candidate PRE-INIT: handoff is claimed by presence; zero overlay, frame, history or body-lock effects', function () {
  const bridge = makeBridge('queued');
  const r = launchOverlay({ bridge: bridge });
  assert.strictEqual(bridge.calls.length, 1, 'exactly one handoff');
  assert.strictEqual(r.st.buildOverlay, 0, 'no overlay root built');
  assert.strictEqual(r.st.createFrame, 0, 'no app iframe created (defect B nested frame)');
  assert.strictEqual(r.st.ensureFrame, 0);
  assert.strictEqual(r.st.destroyFrame, 0);
  assert.strictEqual(r.st.freshMobileLaunchUrl, 0, 'no mobile cache-buster for a native route');
  assert.strictEqual(r.st.armHistoryGuard, 0, 'no history entry pushed under the shell');
  assert.strictEqual(r.st.lockDashboard, 0, 'no body lock / inert sweep');
  assert.strictEqual(r.st.showToast, 0);
  assert.strictEqual(r.st.beginLoading, 0);
  assert.strictEqual(r.st.postMessages, 0, 'no parent->iframe messaging on a handoff');
  assert.deepStrictEqual(r.lf.rec.hrefWrites, [], 'a claimed handoff never raw-writes Location');
  assert.deepStrictEqual(r.lf.rec.replaced, []);
  assert.deepStrictEqual(r.lf.rec.assigned, []);
});
test('candidate ACTIVE: same single handoff, still no overlay side effects', function () {
  const bridge = makeBridge('active');
  const r = launchOverlay({ bridge: bridge });
  assert.strictEqual(bridge.calls.length, 1);
  assert.strictEqual(bridge.calls[0][1], 'push', 'incumbent push semantics preserved');
  assert.strictEqual(r.st.buildOverlay, 0);
  assert.strictEqual(r.st.ensureFrame, 0);
  assert.deepStrictEqual(r.lf.rec.hrefWrites, []);
});
test('candidate: the destination is always the admitted RELATIVE /terminal route - never the absolute app URL', function () {
  for (const kind of ['queued', 'active', 'refuse']) {
    const bridge = makeBridge(kind);
    const r = launchOverlay({ bridge: bridge });
    const dest = bridge.calls[0][0];
    assert.ok(dest.startsWith('/terminal'), kind + ': destination must be route-relative: ' + dest);
    assert.ok(!/^[a-z]+:\/\//.test(dest) && dest.indexOf(APP_ORIGIN) === -1,
      kind + ': an absolute app URL can never be admitted by the closed bridge');
    assert.ok(dest.length <= MAX_URL, 'bridge URL bound respected');
    assert.strictEqual(r.st.buildOverlay, 0);
    assert.deepStrictEqual(r.lf.rec.hrefWrites, [], kind + ': no raw fallback after claim/refusal');
  }
});
test('candidate: retained safe symbol / AI / return semantics', function () {
  const bridge = makeBridge('active');
  launchOverlay({ bridge: bridge, ai: true });
  const u = new URL(bridge.calls[0][0], LEGACY_ORIGIN + '/');
  assert.strictEqual(u.pathname, '/terminal');
  assert.strictEqual(u.searchParams.get('symbol'), 'NVDA', 'incumbent sym= renamed to the native route parameter');
  assert.strictEqual(u.searchParams.get('ai'), '1', 'AI workspace intent kept');
  assert.strictEqual(u.searchParams.get('from'), 'macro', 'incumbent Dashboard-return intent kept');
  assert.strictEqual(u.searchParams.get('ret'), LEGACY_ORIGIN + '/china_lookup.html#NVDA',
    'exact return page, hash included, as the incumbent terminalUrl() carried it');
});
test('candidate: embed-only parameters and auth secrets are never forwarded to the native route', function () {
  const bridge = makeBridge('active');
  launchOverlay({ bridge: bridge });
  const raw = bridge.calls[0][0];
  assert.ok(raw.indexOf('embed') === -1, 'embed=dashboard is portal-iframe presentation, not native state');
  for (const secret of ['access_token', 'refresh_token', 'id_token', 'token_hash', 'code_verifier', 'authorization']) {
    assert.ok(raw.indexOf(secret) === -1, secret + ' must never reach a shell navigation');
  }
  assert.ok(raw.indexOf('sym=') === -1, 'the retired query spelling is not duplicated');
});
test('candidate: symbol falls back to the incumbent query when the launch carries no config.symbol', function () {
  const bridge = makeBridge('active');
  launchOverlay({ bridge: bridge, config: { url: incumbentConfig().url, directUrl: incumbentConfig().directUrl } });
  const u = new URL(bridge.calls[0][0], LEGACY_ORIGIN + '/');
  assert.strictEqual(u.searchParams.get('symbol'), 'NVDA');
  assert.strictEqual(u.searchParams.get('from'), 'macro');
});
test('candidate: dotted symbols survive exactly (BRK.B, 9988.HK, 0002.HK)', function () {
  for (const t of ['BRK.B', '9988.HK', '0002.HK', '8035.T']) {
    const bridge = makeBridge('active');
    launchOverlay({ bridge: bridge, ticker: t });
    const u = new URL(bridge.calls[0][0], LEGACY_ORIGIN + '/');
    assert.strictEqual(u.searchParams.get('symbol'), t);
  }
});
test('candidate: return links stay on this document\u2019s own first-party origin, the incumbent convention', function () {
  const docs = [LEGACY_ORIGIN + '/china_lookup.html#NVDA', APEX_ORIGIN + '/stock.html#AAPL'];
  for (const doc of docs) {
    const cases = [
      [doc, doc],
      [doc + '?signin=1', doc + '?signin=1'], // incumbent CTA state is safe return state
      ['https://evil.example/return', null],
      [doc.replace('https://', 'http://'), null],
      [doc.replace('mastermind-x.com', 'mastermind-x.com.evil'), null],
      ['javascript:alert(1)', null],
      ['', null],
    ];
    for (const [ret, expected] of cases) {
      const bridge = makeBridge('active');
      launchOverlay({ bridge: bridge, documentHref: doc, ret: ret });
      const u = new URL(bridge.calls[0][0], LEGACY_ORIGIN + '/');
      assert.strictEqual(u.searchParams.get('ret'), expected, 'ret=' + ret + ' doc=' + doc);
      assert.strictEqual(u.searchParams.get('from'), 'macro', 'the native return-to-Dashboard affordance survives');
      assert.strictEqual(bridge.calls.length, 1);
    }
  }
});
test('candidate: a refused handoff claims the launch - no overlay, no raw Location, no nested native UI', function () {
  const bridge = makeBridge('refuse');
  const r = launchOverlay({ bridge: bridge });
  assert.strictEqual(bridge.calls.length, 1);
  assert.strictEqual(r.st.buildOverlay, 0);
  assert.strictEqual(r.st.ensureFrame, 0);
  assert.strictEqual(r.st.armHistoryGuard, 0);
  assert.strictEqual(r.st.lockDashboard, 0);
  assert.deepStrictEqual(r.lf.rec.hrefWrites, []);
  assert.deepStrictEqual(r.lf.rec.replaced, []);
});
test('candidate: an invalid configured native URL is refused, never a nested overlay', function () {
  const bad = [
    APP_ORIGIN + '/terminalx',              // wrong route
    APP_ORIGIN + '/analysis',               // unrelated app route
    APP_ORIGIN.replace('.com', '.com.evil') + '/terminal',
    'http://app.mastermind-x.com/terminal', // not the exact https origin
    'https://user:pw@app.mastermind-x.com/terminal',
    APP_ORIGIN + '/terminal?debug=1',
    APP_ORIGIN + '/terminal#frag',
    'https://beta.mastermind-x.com/terminal', // the shell route is not the native base
    '', null, 42, {}, [], true,
  ];
  for (const base of bad) {
    const bridge = makeBridge('active');
    const r = launchOverlay({ bridge: bridge, base: base });
    assert.deepStrictEqual(bridge.calls, [], 'invalid base must not be handed to navigate: ' + base);
    assert.strictEqual(r.st.buildOverlay, 0, 'invalid base must not fall through to the nested overlay: ' + base);
    assert.deepStrictEqual(r.lf.rec.hrefWrites, [], 'invalid base must not raw-write Location: ' + base);
  }
});
test('candidate: the canonical "/" native variant is admitted as the /terminal route', function () {
  const bridge = makeBridge('active');
  launchOverlay({ bridge: bridge, base: APP_ORIGIN + '/', url: APP_ORIGIN + '/?sym=NVDA&from=macro', directUrl: APP_ORIGIN + '/terminal?sym=NVDA&from=macro' });
  const u = new URL(bridge.calls[0][0], LEGACY_ORIGIN + '/');
  assert.strictEqual(u.pathname, '/terminal');
  assert.strictEqual(u.searchParams.get('symbol'), 'NVDA');
});
test('candidate: a launch URL that is not the native app route is refused, not reframed', function () {
  for (const url of ['https://evil.example/terminal?sym=NVDA', LEGACY_ORIGIN + '/terminal?sym=NVDA',
    'https://user:pw@app.mastermind-x.com/terminal', '/terminal?sym=NVDA',
    APP_ORIGIN + '/analysis?symbol=NVDA']) {
    const bridge = makeBridge('active');
    const r = launchOverlay({ bridge: bridge, config: { url: url, symbol: 'NVDA' } });
    assert.deepStrictEqual(bridge.calls, [], 'refused: ' + url);
    assert.strictEqual(r.st.buildOverlay, 0, 'no nested UI for a refused destination: ' + url);
    assert.deepStrictEqual(r.lf.rec.hrefWrites, [], 'no raw fallback for a refused destination: ' + url);
  }
});
test('candidate on a non-dashboard host (the shell-nested real case): never the raw www/terminal bounce', function () {
  const bridge = makeBridge('queued');
  const r = launchOverlay({ bridge: bridge, hostOff: true });
  assert.strictEqual(bridge.calls.length, 1);
  assert.ok(bridge.calls[0][0].startsWith('/terminal'));
  assert.deepStrictEqual(r.lf.rec.hrefWrites, [], 'the old bounce would have moved the shell frame');
});
test('candidate: an unrelated (non-Terminal) launch shape is not silently swallowed', function () {
  const bridge = makeBridge('queued');
  const r = launchOverlay({ bridge: bridge, config: null });
  assert.deepStrictEqual(bridge.calls, [], 'openInternal still rejects a missing config first');
  assert.strictEqual(r.st.buildOverlay, 0);
});

/* ===================================================================== *
 * 3. stock-table direct fallback (the second owner surface)
 * ===================================================================== */
/* The stock-table chain is executed verbatim, and in candidate mode it calls the
 * SHIPPED mmxSharedShellTerminalHandoff (extracted into a second vm context that
 * shares the same window object), so the fallback is proven against the real
 * admission rules rather than a fixture re-implementation. */
function stockClick(opts) {
  opts = opts || {};
  const lf = makeLocation(opts.documentHref);
  const st = overlayCounters();
  const base = Object.prototype.hasOwnProperty.call(opts, 'base')
    ? opts.base : APP_ORIGIN + '/terminal';
  const T = opts.T === undefined
    ? { on: function () { return opts.terminalOff ? false : true; },
        url: function (t) { return APP_ORIGIN + '/terminal?sym=' + encodeURIComponent(t || '') +
          '&from=macro&ret=' + encodeURIComponent(lf.loc.href); },
        open: opts.noOpen ? undefined : function (t, trigger) {
          st.opened = (st.opened || 0) + 1; st.lastOpen = [t, trigger]; } }
    : opts.T;
  const win = { location: lf.loc, MMXSharedShell: opts.bridge, MM_TERMINAL_BASE: base };
  if (!opts.noHandoff) {
    const helperRealm = vm.createContext({ window: win, URL: URL, URLSearchParams: URLSearchParams,
      String: String, encodeURIComponent: encodeURIComponent, Object: Object, Math: Math });
    vm.runInContext(HANDOFF_HELPERS, helperRealm);
    win.MDXTerminalOverlay = {
      terminalHandoff: helperRealm.mmxSharedShellTerminalHandoff,
      terminalDestination: helperRealm.mmxSharedShellTerminalDestination,
    };
    assert.strictEqual(typeof win.MDXTerminalOverlay.terminalHandoff, 'function',
      'the shipped handoff must be extractable for the table fallback');
  }
  const row = { ticker: opts.ticker === undefined ? 'NVDA' : opts.ticker };
  const tr = { style: {}, addEventListener: function () {} };
  const link = 'china_lookup.html#' + encodeURIComponent(row.ticker);
  const sandbox = {
    URL: URL, URLSearchParams: URLSearchParams, encodeURIComponent: encodeURIComponent, String: String,
    window: win, location: lf.loc, T: T, link: link, row: row, tr: tr,
  };
  runIn('function clickChain() ' + STOCK_CHAIN.replace(/^if/, '{ if').replace(/$/, ' }') + '\nclickChain();', sandbox);
  return { st: st, lf: lf, bridge: opts.bridge, win: win, sandbox: sandbox };
}
test('stocktable: no candidate keeps both incumbent behaviors exactly', function () {
  const warm = stockClick({});
  assert.strictEqual(warm.st.opened, 1, 'MDXTerminal.open is still the primary path');
  assert.deepStrictEqual(warm.lf.rec.assigned, []);
  const cold = stockClick({ noOpen: true });
  assert.deepStrictEqual(cold.lf.rec.assigned, [APP_ORIGIN + '/terminal?sym=NVDA&from=macro&ret=' +
    encodeURIComponent(LEGACY_ORIGIN + '/china_lookup.html#NVDA')], 'incumbent absolute fallback URL kept');
  const off = stockClick({ terminalOff: true });
  assert.deepStrictEqual(off.lf.rec.assigned, ['china_lookup.html#NVDA'], 'disabled-Terminal same-page link kept');
});
test('stocktable: candidate present routes to the admitted relative /terminal, never the absolute app URL', function () {
  for (const kind of ['queued', 'active']) {
    const bridge = makeBridge(kind);
    const r = stockClick({ bridge: bridge, noOpen: true });
    assert.strictEqual(bridge.calls.length, 1, 'the shipped handoff navigated exactly once');
    assert.ok(bridge.calls[0][0].startsWith('/terminal'), bridge.calls[0][0]);
    const u = new URL(bridge.calls[0][0], LEGACY_ORIGIN + '/');
    assert.strictEqual(u.pathname, '/terminal');
    assert.strictEqual(u.searchParams.get('symbol'), 'NVDA');
    assert.strictEqual(u.searchParams.get('from'), 'macro');
    assert.strictEqual(u.searchParams.get('ret'), LEGACY_ORIGIN + '/china_lookup.html#NVDA');
    assert.ok(bridge.calls[0][0].indexOf('embed') === -1, 'embed-only parameter not forwarded');
    assert.deepStrictEqual(r.lf.rec.assigned, [], 'a candidate never gets a raw Location write');
    assert.strictEqual(r.st.opened, 0, 'no overlay launch either: MDXTerminal.open is not reached from here');
  }
});
test('stocktable: candidate mode still prefers MDXTerminal.open (the gated overlay seam)', function () {
  const bridge = makeBridge('queued');
  const r = stockClick({ bridge: bridge });
  assert.strictEqual(r.st.opened, 1, 'the incumbent primary path is unchanged');
  assert.deepStrictEqual(bridge.calls, [], 'the table itself must not double-navigate');
  assert.deepStrictEqual(r.lf.rec.assigned, []);
});
test('stocktable: candidate without the overlay controller still offers only the relative native route', function () {
  const bridge = makeBridge('queued');
  const r = stockClick({ bridge: bridge, noHandoff: true, noOpen: true });
  assert.strictEqual(bridge.calls.length, 1);
  assert.ok(bridge.calls[0][0].startsWith('/terminal?'), bridge.calls[0][0]);
  const u = new URL(bridge.calls[0][0], LEGACY_ORIGIN + '/');
  assert.strictEqual(u.searchParams.get('symbol'), 'NVDA');
  assert.strictEqual(u.searchParams.get('ret'), LEGACY_ORIGIN + '/china_lookup.html');
  assert.deepStrictEqual(r.lf.rec.assigned, []);
});
test('stocktable: candidate with Terminal disabled keeps the incumbent same-page destination', function () {
  const bridge = makeBridge('queued');
  const r = stockClick({ bridge: bridge, terminalOff: true });
  assert.deepStrictEqual(bridge.calls, [['china_lookup.html#NVDA', 'push']], 'link semantics preserved');
  assert.deepStrictEqual(r.lf.rec.assigned, []);
});
test('stocktable: a refused native handoff does not escape the frame', function () {
  const bridge = makeBridge('refuse');
  const r = stockClick({ bridge: bridge, noOpen: true });
  assert.strictEqual(bridge.calls.length, 1);
  assert.deepStrictEqual(r.lf.rec.assigned, [], 'refusal must not raw-write window.location.href');
});
test('stocktable: an invalid configured native base is claimed (nothing navigates, nothing escapes)', function () {
  const bridge = makeBridge('active');
  const r = stockClick({ bridge: bridge, noOpen: true, T: {
    on: function () { return true; },
    url: function () { return 'https://app.mastermind-x.com.evil/terminal?sym=NVDA'; } } });
  assert.deepStrictEqual(bridge.calls, []);
  assert.deepStrictEqual(r.lf.rec.assigned, []);
});
test('stocktable: shipped text no longer hands an absolute URL to the bridge and still gates on presence', function () {
  const text = stocktableSrc();
  assert.ok(!/navigate\(_d/.test(text), "the old _ss.navigate(_d, 'push') absolute-URL bounce is still present");
  assert.ok(text.includes('} else if (window.MMXSharedShell) {'), 'presence gate missing');
  assert.ok(text.includes('window.MDXTerminalOverlay'), 'fallback must reuse the centralized handoff');
  assert.ok(/window\.location\.href = _d/.test(text), 'standalone raw assignment must remain');
  assert.ok(!/_ss\d?\.active/.test(text), 'no .active gate in the table fallback');
});

/* ===================================================================== *
 * 4. cross-cutting
 * ===================================================================== */
test('the repair invents no API: the shipped seams use only the closed bridge surface', function () {
  const text = HANDOFF_HELPERS + '\n' + STOCK_CHAIN + '\n' + OPEN_INTERNAL;
  assert.ok(!/__MMX_SHARED_BRIDGE_INSTALLED__/.test(text), 'bridge internals must not be reimplemented here');
  assert.ok(!/openAuth|applyingContext|AUTH_INTENTS/.test(text),
    'the closed API {navigate,openAuth,active,applyingContext} is not redefined by the launch owners');
  assert.ok(!/AUTH_REQUEST/.test(text), 'launch owners do not emit auth protocol messages');
});
test('defect A is header-side only: no macro launch owner invents CSP or frame-ancestors logic', function () {
  const text = HANDOFF_HELPERS + '\n' + STOCK_CHAIN + '\n' + OPEN_INTERNAL;
  assert.ok(!/Content-Security-Policy|frame-ancestors|X-Frame-Options/.test(text));
});
test('the handoff is idempotent per launch and offers one destination string', function () {
  const bridge = makeBridge('active');
  const first = launchOverlay({ bridge: bridge });
  assert.strictEqual(bridge.calls.length, 1);
  const second = launchOverlay({ bridge: makeBridge('active') });
  assert.strictEqual(second.bridge.calls.length, 1);
});


test('native handoff does not nest credential-like or recursive return state', function () {
  const doc = LEGACY_ORIGIN + '/china_lookup.html';
  for (const ret of [doc + '?access_token=canary', doc + '#refresh_token=canary',
    doc + '?onboard=resume&code=canary', doc + '?type=recovery',
    'https://user:canary@www.mastermind-x.com/china_lookup.html',
    doc + '?ret=' + encodeURIComponent(doc + '?access_token=canary')]) {
    const bridge = makeBridge('active');
    launchOverlay({ bridge: bridge, documentHref: doc, ret: ret });
    const u = new URL(bridge.calls[0][0], LEGACY_ORIGIN + '/');
    assert.strictEqual(u.searchParams.get('ret'), null, ret);
    assert.strictEqual(u.searchParams.get('symbol'), 'NVDA');
  }
});

test('safe native return preserves presentation bytes but drops child transport', function () {
  const bridge = makeBridge('active');
  const doc = LEGACY_ORIGIN + '/china_lookup.html';
  launchOverlay({ bridge: bridge, documentHref: doc,
    ret: doc + '?q=A%20B&mmx_shell=1&mmx_generation=g1#NVDA' });
  const u = new URL(bridge.calls[0][0], LEGACY_ORIGIN + '/');
  assert.strictEqual(u.searchParams.get('ret'), doc + '?q=A%20B#NVDA');
});

test('missing native controller fallback retains only a page return', function () {
  const bridge = makeBridge('active');
  const doc = LEGACY_ORIGIN + '/china_lookup.html';
  const result = stockClick({ bridge: bridge, noHandoff: true, noOpen: true,
    documentHref: doc + '?onboard=resume&code=canary#access_token=canary' });
  const u = new URL(bridge.calls[0][0], LEGACY_ORIGIN + '/');
  assert.strictEqual(u.searchParams.get('ret'), doc);
  assert.deepStrictEqual(result.lf.rec.assigned, []);
});
