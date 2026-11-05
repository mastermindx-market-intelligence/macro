'use strict';
/*
 * shared_shell_navigation_adapters.test.cjs
 *
 * Behavioral verification of the Shared Shell navigation page adapters
 * (run shared-shell-navigation-final-20261018-c1-r1) WITHOUT a browser.
 *
 * Anti-tautology rule: the adapter bodies executed here are EXTRACTED from the
 * repo-relative template sources below (templates/<file>) and run under `vm`
 * against scripted bridge fixtures. Only the bridge fixture (navigate/queue/
 * refusal semantics copied from the supplied mmx.shared-shell.v1 child bridge)
 * and the expected destination strings live in this file; nothing mirrors the
 * shipped adapter code. If the shipped snippets change semantics, these tests
 * move. Extraction fails LOUDLY when a source file or anchor is missing - it
 * never silently skips.
 *
 * Where to run: place this file one directory under the repo root (e.g.
 * tests/) and run `node --test` from the repo root, or set
 * MMX_NAV_SOURCE_ROOT=/path/to/repo.
 */
const { test } = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

/* ---- explicit repo-relative source extraction ---- */
const ROOTS = [];
if (process.env.MMX_NAV_SOURCE_ROOT) ROOTS.push(process.env.MMX_NAV_SOURCE_ROOT);
ROOTS.push(path.resolve(process.cwd()),
           path.resolve(process.cwd(), '..'),
           path.resolve(__dirname, '..'),
           path.resolve(__dirname, '..', '..'));
function readSource(rel) {
  const tried = [];
  for (const root of ROOTS) {
    const p = path.join(root, rel);
    tried.push(p);
    if (fs.existsSync(p)) return fs.readFileSync(p, 'utf8');
  }
  throw new Error('MMX template source missing: ' + rel + ' (tried: ' + tried.join(' | ') + ')');
}
function src(file) { return readSource('templates/' + file); }

/* balanced-block extraction: anchor must be unique, terminator is the first
 * line-start indent match after the anchor; returns the ORIGINAL shipped text */
function extractBlock(text, startAnchor, endAnchor, label) {
  const i = text.indexOf(startAnchor);
  assert.ok(i !== -1, label + ': start anchor missing: ' + startAnchor);
  assert.ok(text.indexOf(startAnchor, i + 1) === -1, label + ': start anchor not unique');
  const j = text.indexOf(endAnchor, i);
  assert.ok(j !== -1, label + ': end anchor missing');
  const block = text.slice(i, j + endAnchor.length);
  assert.ok(!/_ss\d?\.active/.test(block), label + ': adapter must gate on candidate presence, not .active');
  return block;
}
function braceMatched(text, startAnchor, label) {
  const i = text.indexOf(startAnchor);
  assert.ok(i !== -1, label + ': start anchor missing: ' + startAnchor);
  let depth = 0, k = text.indexOf('{', i), inStr = null;
  for (; k < text.length; k++) {
    const c = text[k];
    if (inStr) { if (c === '\\') k++; else if (c === inStr) inStr = null; continue; }
    if (c === '"' || c === "'") { inStr = c; continue; }
    if (c === '{') depth++;
    else if (c === '}') { depth--; if (depth === 0) return text.slice(i, k + 1); }
  }
  throw new Error(label + ': unbalanced block');
}

/* ---- fixtures replicating the supplied bridge's OBSERVED contract, not its
 * code: MMXSharedShell exists only in the candidate iframe; navigate() before
 * INIT queues and performs no local Location mutation; when active, a pure
 * fragment write transitions the child history synchronously and returns true;
 * a refusal returns true/false per bridge rules without touching Location. ---- */
function makeLocation(initialHash) {
  const rec = { hashWrites: 0, hrefWrites: 0, replaced: [], _hash: initialHash || '', _href: '' };
  const loc = {};
  Object.defineProperty(loc, 'hash', { get: function () { return rec._hash; },
    set: function (v) { rec.hashWrites++; rec._hash = String(v).charAt(0) === '#' ? String(v) : '#' + String(v); } });
  Object.defineProperty(loc, 'href', { get: function () { return rec._href; },
    set: function (v) { rec.hrefWrites++; rec._href = String(v); } });
  loc.replace = function (u) { rec.replaced.push(String(u)); };
  loc.assign = function (u) { rec.replaced.push(String(u)); };
  return { loc: loc, rec: rec };
}
function bridgeQueued() { /* pre-INIT candidate: accepted into the queue, NO local transition */
  const b = { calls: [], navigate: function (d, m) { b.calls.push([d, m]); return true; } };
  return b;
}
function bridgeRefusing() { /* active candidate refusing (external/sensitive/unadmitted/queue full) */
  const b = { calls: [], navigate: function (d, m) { b.calls.push([d, m]); return false; } };
  return b;
}
function run(code, sandbox) { vm.runInNewContext(code, sandbox); return sandbox; }

/* ===================================================================== *
 * 1. Analyzer pickers (canada_stock / china_lookup / hk_lookup / intl)
 * ===================================================================== */
const ANALYZER_FILES = ['canada_stock.html.j2', 'china_lookup.html.j2', 'hk_lookup.html.j2', 'intl_stock.html.j2'];
for (const file of ANALYZER_FILES) {
  const pickSrc = braceMatched(src(file), 'function pick(i) {', 'pick@' + file);
  const foreignTarget = 'some_other_market.html';
  const ticker = 'BRK.B'; // encodes to BRK.B (safe chars keep the hash exactly comparable)
  const enc = encodeURIComponent(ticker);

  function mkPickSandbox(bridge, sameMarket) {
    const lf = makeLocation('');
    const st = { fromHashCalls: 0 };
    const sandbox = {
      items: sameMarket ? [{ t: ticker, _tgt: null }] : [{ t: ticker, _tgt: foreignTarget }],
      sugg: { style: { display: '' } }, q: { value: '' },
      location: lf.loc,
      window: bridge ? { MMXSharedShell: bridge } : {},
      fromHash: function () { st.fromHashCalls++; },
    };
    return { sandbox, lf, st };
  }

  test(file + ': no bridge keeps standalone behavior', function () {
    let m = mkPickSandbox(null, false);
    run(pickSrc + '\npick(0);', m.sandbox);
    assert.strictEqual(m.lf.rec._href, foreignTarget + '#' + enc, 'cross-market raw assignment kept');
    assert.strictEqual(m.lf.rec.hrefWrites, 1);
    m = mkPickSandbox(null, true);
    run(pickSrc + '\npick(0);', m.sandbox);
    assert.strictEqual(m.lf.rec._hash, '#' + enc, 'standalone hash write kept');
    assert.strictEqual(m.st.fromHashCalls, 0, 'standalone must not call the handler manually (natural hashchange)');
  });

  test(file + ': candidate present but pre-INIT queues without any Location mutation or stale handler run', function () {
    const bridge = bridgeQueued();
    let m = mkPickSandbox(bridge, false);
    run(pickSrc + '\npick(0);', m.sandbox);
    assert.deepStrictEqual(bridge.calls, [[foreignTarget + '#' + enc, 'push']]);
    assert.strictEqual(m.lf.rec.hrefWrites, 0, 'no raw Location.href after hand-off');
    m = mkPickSandbox(bridge, true);
    run(pickSrc + '\npick(0);', m.sandbox);
    assert.deepStrictEqual(bridge.calls.slice(-1), [['#' + enc, 'push']], 'fragment passed with explicit #');
    assert.strictEqual(m.lf.rec._hash, '', 'queued navigation performs no local history transition yet');
    assert.strictEqual(m.st.fromHashCalls, 0, 'handler must NOT run before an accepted local transition');
    assert.strictEqual(m.lf.rec.hashWrites, 0, 'no synthetic hash mutation either');
  });

  test(file + ': active bridge accepted fragment transition runs the real fromHash exactly once', function () {
    const lf = makeLocation('');
    let calls = 0;
    const sandbox = {
      items: [{ t: ticker, _tgt: null }], sugg: { style: { display: '' } }, q: { value: '' },
      location: lf.loc, window: {}, fromHash: function () { calls++; },
    };
    const bridge = { calls: [], navigate: function (d, mm) { bridge.calls.push([d, mm]); lf.rec._hash = d; return true; } };
    sandbox.window = { MMXSharedShell: bridge };
    run(pickSrc + '\npick(0);', sandbox);
    assert.deepStrictEqual(bridge.calls, [['#' + enc, 'push']]);
    assert.strictEqual(calls, 1, 'local handler after accepted synchronous transition');
  });

  test(file + ': refusal never escapes (no raw assignment, no handler)', function () {
    const bridge = bridgeRefusing();
    const m = mkPickSandbox(bridge, true);
    run(pickSrc + '\npick(0);', m.sandbox);
    assert.deepStrictEqual(bridge.calls, [['#' + enc, 'push']]);
    assert.strictEqual(m.lf.rec.hashWrites, 0, 'refusal must not raw-write location.hash');
    assert.strictEqual(m.lf.rec._hash, '', 'refusal leaves the child URL untouched');
    assert.strictEqual(m.st.fromHashCalls, 0, 'handler only after an accepted transition');
    const m2 = mkPickSandbox(bridgeRefusing(), false);
    run(pickSrc + '\npick(0);', m2.sandbox);
    assert.strictEqual(m2.lf.rec.hrefWrites, 0, 'refused cross-market bounce must not escape the frame');
  });

  test(file + ': same-market adapter dispatches no synthetic hashchange', function () {
    assert.ok(!/dispatchEvent|HashChangeEvent/.test(pickSrc), 'no synthetic event in shipped pick(): ' );
  });

  test(file + ': standalone hashchange kept AND mmx:shell-location listener added', function () {
    const text = src(file);
    assert.ok(text.includes("  window.addEventListener('hashchange', fromHash);"), 'hashchange listener kept');
    assert.ok(text.includes("  window.addEventListener('mmx:shell-location', fromHash);"), 'shell-location reapply listener added');
  });
}

/* ===================================================================== *
 * 2. finance_intelligence.js evidence drawer
 * ===================================================================== */
{
  const file = 'finance_intelligence.js';
  const fnSrc = braceMatched(src(file), 'function openEvidence(recordIds) {', 'openEvidence');
  function mkSandbox(bridge, initialHash) {
    const lf = makeLocation(initialHash);
    const st = { handleHashCalls: 0 };
    const sandbox = {
      location: lf.loc,
      window: bridge ? { MMXSharedShell: bridge } : {},
      handleHash: function () { st.handleHashCalls++; },
    };
    return { sandbox, lf, st };
  }
  test('finance_intelligence: no bridge keeps standalone hash write (natural hashchange)', function () {
    const m = mkSandbox(null, '');
    run(fnSrc + '\nopenEvidence("R7 R8");', m.sandbox);
    assert.strictEqual(m.lf.rec._hash, '#evidence=R7');
    assert.strictEqual(m.lf.rec.hashWrites, 1);
    assert.strictEqual(m.st.handleHashCalls, 0);
  });
  test('finance_intelligence: same-hash arrival still calls handleHash once with no navigation', function () {
    const bridge = bridgeQueued();
    const m = mkSandbox(bridge, '#evidence=R7');
    run(fnSrc + '\nopenEvidence("R7 R8");', m.sandbox);
    assert.strictEqual(m.st.handleHashCalls, 1);
    assert.deepStrictEqual(bridge.calls, []);
  });
  test('finance_intelligence: queued (pre-INIT) hand-off mutates nothing and skips the handler', function () {
    const bridge = bridgeQueued();
    const m = mkSandbox(bridge, '');
    run(fnSrc + '\nopenEvidence("R7 R8");', m.sandbox);
    assert.deepStrictEqual(bridge.calls, [['#evidence=R7', 'push']]);
    assert.strictEqual(m.lf.rec._hash, '', 'no local transition while queued');
    assert.strictEqual(m.st.handleHashCalls, 0, 'handler only after accepted synchronous transition');
    assert.strictEqual(m.lf.rec.hashWrites, 0);
  });
  test('finance_intelligence: accepted synchronous transition runs handleHash once', function () {
    const lf = makeLocation('');
    let calls = 0;
    const bridge = { calls: [], navigate: function (d, mm) { bridge.calls.push([d, mm]); lf.rec._hash = d; return true; } };
    run(fnSrc + '\nopenEvidence("R7");', { location: lf.loc, window: { MMXSharedShell: bridge }, handleHash: function () { calls++; } });
    assert.strictEqual(calls, 1);
  });
  test('finance_intelligence: refusal performs no raw fallback and no handler run', function () {
    const bridge = bridgeRefusing();
    const m = mkSandbox(bridge, '');
    run(fnSrc + '\nopenEvidence("R7");', m.sandbox);
    assert.deepStrictEqual(bridge.calls, [['#evidence=R7', 'push']]);
    assert.strictEqual(m.lf.rec.hashWrites, 0);
    assert.strictEqual(m.st.handleHashCalls, 0);
  });
  test('finance_intelligence: hashchange kept + shell-location listener added', function () {
    const text = src(file);
    assert.ok(text.includes("    window.addEventListener('hashchange', handleHash);"));
    assert.ok(text.includes("    window.addEventListener('mmx:shell-location', handleHash);"));
  });
}

/* ===================================================================== *
 * 3. Redirect stubs: presence-gated script, hash forwarding, noscript meta
 * ===================================================================== */
const STUB_CASES = [
  { file: 'baskets_china.html.j2', dest: function (hash) { return 'sector_central_china.html' + (hash ? hash : '#si-explore'); } },
  { file: 'subsector_rotation_china.html.j2', dest: function (hash) { return 'sector_central_china.html' + (hash ? hash : '#si-movement'); } },
  { file: 'flow_desk.html.j2', dest: function () { return 'options.html#flow'; } },
  { file: 'flow_leaders.html.j2', dest: function () { return 'options.html#leaders'; } },
  { file: 'options_screener.html.j2', dest: function () { return 'options.html#scanner'; } },
  { file: 'subsector_rotation.html.j2', dest: function () { return 'sector_central.html#si-movement'; } },
  { file: 'vector_allocation.html.j2', dest: function () { return 'crypto.html#allocation'; } },
];
for (const c of STUB_CASES) {
  const iife = extractBlock(src(c.file), '<script>(function(){', '})()</script>', c.file)
    .replace(/^<script>/, '').replace(/<\/script>$/, '');
  function stubRun(bridge, hash) {
    const lf = makeLocation(hash || '');
    const sandbox = { location: lf.loc, window: bridge ? { MMXSharedShell: bridge } : {} };
    run('(' + iife + ')', sandbox);
    return { lf, sandbox };
  }
  test(c.file + ': stub redirect honors presence gate, queue and refusal without raw escape', function () {
    const plain = stubRun(null, '');
    assert.deepStrictEqual(plain.lf.rec.replaced, [c.dest('')], 'standalone replace kept');
    const fwd = stubRun(null, '#b-123');
    assert.deepStrictEqual(fwd.lf.rec.replaced, [c.dest('#b-123')], 'hash forwarding preserved verbatim');
    const bridge = bridgeQueued();
    const q = stubRun(bridge, '');
    assert.deepStrictEqual(bridge.calls, [[c.dest(''), 'replace']], 'replace semantics handed to queue pre-INIT');
    assert.deepStrictEqual(q.lf.rec.replaced, [], 'candidate present: NO raw location.replace after hand-off');
    assert.strictEqual(q.lf.rec.hashWrites, 0);
    const r = stubRun(bridgeRefusing(), '');
    assert.deepStrictEqual(r.lf.rec.replaced, [], 'refusal never raw-falls-back');
  });
  test(c.file + ': redirect meta refresh is inside head <noscript> and unrelated meta untouched', function () {
    const text = src(c.file);
    const bare = (text.match(/<meta http-equiv="refresh"/g) || []).length;
    const wrapped = (text.match(/<noscript><meta http-equiv="refresh"[^>]*><\/noscript>/g) || []).length;
    assert.ok(bare >= 1, 'meta refresh still present');
    assert.strictEqual(bare, wrapped, 'every redirect meta refresh wrapped in <noscript>');
    assert.ok(text.includes('<meta name="robots" content="noindex,follow">'), 'robots meta unchanged');
  });
}
/* baskets.html.j2: the deep-link resolver runs in <head> BEFORE INIT on stub
 * pages, so this proves the queue path end-to-end on the shipped text itself */
{
  const text = src('baskets.html.j2');
  const fnSrc = braceMatched(text, 'function resolveThemeHash(){', 'resolveThemeHash');
  function runResolver(bridge, known) {
    const lf = makeLocation('#theme-aluminum');
    const sandbox = {
      location: lf.loc,
      window: bridge ? { MMXSharedShell: bridge } : {},
      themeById: function (id) { return known ? id : null; },
    };
    run(fnSrc + '\nresolveThemeHash();', sandbox);
    return { lf, sandbox };
  }
  test('baskets.html.j2: theme-detail and fallback redirects queue pre-INIT with zero Location calls', function () {
    const bridge = bridgeQueued();
    const a = runResolver(bridge, true);
    assert.deepStrictEqual(bridge.calls, [['basket/aluminum.html', 'replace']]);
    assert.strictEqual(a.sandbox.window.__THEME_RESOLVED, 1, 'flag semantics unchanged');
    assert.deepStrictEqual(a.lf.rec.replaced, [], 'no raw replace while handled');
    const bridge2 = bridgeQueued();
    const b = runResolver(bridge2, false);
    assert.deepStrictEqual(bridge2.calls.slice(-1), [['sector_central.html#actnow-section', 'replace']]);
    assert.deepStrictEqual(b.lf.rec.replaced, []);
    const nb = runResolver(null, true);
    assert.deepStrictEqual(nb.lf.rec.replaced, ['basket/aluminum.html']);
  });
  test('baskets.html.j2: meta refresh wrapped, robots meta untouched', function () {
    assert.ok(text.includes('<noscript><meta http-equiv="refresh" content="0;url=sector_central.html#actnow-section"></noscript>'));
    assert.ok(text.includes('<meta name="robots" content="noindex,follow">'));
  });
}

/* ===================================================================== *
 * 4. gex.html.j2: symbol-carrying dest unchanged through the bridge, and the
 *    guarded dynamic meta rewrite degrades to a no-op with the noscript wrap
 * ===================================================================== */
{
  const text = src('gex.html.j2');
  const iife = extractBlock(text, '(function(){', '})();', 'gex');
  function runGex(bridge, hash) {
    const lf = makeLocation(hash);
    const metaQueries = [];
    const sandbox = {
      location: lf.loc,
      window: bridge ? { MMXSharedShell: bridge } : {},
      document: {
        getElementById: function () { return null; },
        querySelector: function (sel) { metaQueries.push(sel); return null; }, /* noscript => absent */
      },
    };
    run(iife, sandbox);
    return { lf, metaQueries };
  }
  test('gex: symbol dest carried verbatim; meta rewrite is the guarded no-op it now is', function () {
    const nb = runGex(null, '#nvda');
    assert.deepStrictEqual(nb.lf.rec.replaced, ['options.html?t=NVDA#ticker'], 'symbol-carrying destination unchanged');
    const bridge = bridgeQueued();
    const q = runGex(bridge, '#nvda');
    assert.deepStrictEqual(bridge.calls, [['options.html?t=NVDA#ticker', 'replace']]);
    assert.deepStrictEqual(q.lf.rec.replaced, [], 'no raw fallback pre-INIT');
    const legacy = runGex(null, '#flow');
    assert.deepStrictEqual(legacy.lf.rec.replaced, ['options.html#ticker'], 'legacy mode word falls back to bare ticker dest');
  });
  test('gex: meta refresh wrapped in noscript; robots untouched', function () {
    assert.ok(text.includes('<noscript><meta http-equiv="refresh" content="0;url=options.html#ticker"></noscript>'));
    assert.ok(text.includes('<meta name="robots" content="noindex,follow">'));
  });
}

/* ===================================================================== *
 * 5. terminal_overlay.js: the three openInternal fallbacks are Terminal
 *    canonicalization-respecting; the overlay native-API surfaces are not
 * ===================================================================== */
{
  const text = src('terminal_overlay.js');
  const fnSrc = braceMatched(text, 'function openInternal(config) {', 'openInternal');
  const handoffStart = text.indexOf('  function mmxSharedShellNativeURL() {');
  const handoffEnd = text.indexOf('\n  function isDashboardHost()', handoffStart);
  assert.ok(handoffStart >= 0 && handoffEnd > handoffStart, 'the shipped handoff block is present');
  const handoffSrc = text.slice(handoffStart, handoffEnd);
  function runFallback(which, bridge, opts) {
    opts = opts || {};
    const lf = makeLocation('');
    const st = { buildOverlays: 0, frames: 0 };
    const sandbox = {
      config: { url: opts.url || 'https://app.mastermind-x.com/terminal?symbol=NVDA', directUrl: opts.directUrl || 'https://www.mastermind-x.com/terminal?sym=NVDA' },
      isDashboardHost: function () { return which !== 'host-off'; },
      buildOverlay: function () { st.buildOverlays++; return which === 'no-root' ? null : {}; },
      ensureFrame: function () { st.frames++; return which === 'no-frame' ? null : {}; },
      shouldRemountFrame: function () { return false; },
      freshMobileLaunchUrl: function (u) { return u; },
      destroyFrame: function () {}, clearTimeout: function () {}, setTimeout: function () {},
      lockDashboard: function () {}, armHistoryGuard: function () {}, showToast: function () {},
      state: { open: true, closeTimer: 0, frame: null, symbol: '', lastConfig: null, targetOrigin: '', directUrl: '', newTab: {} },
      location: lf.loc,
      URL: URL, URLSearchParams: URLSearchParams,
      window: Object.assign({ MM_TERMINAL_BASE: 'https://app.mastermind-x.com/terminal',
        location: { href: 'https://www.mastermind-x.com/macro.html' } }, bridge ? { MMXSharedShell: bridge } : {}),
    };
    run(handoffSrc + '\n' + fnSrc + '\nopenInternal(config);', sandbox);
    return { lf, st, sandbox };
  }
  for (const which of ['host-off', 'no-root', 'no-frame']) {
    test('terminal_overlay ' + which + ' fallback: standalone unchanged; handled/refused never raw', function () {
      const nb = runFallback(which, null);
      assert.strictEqual(nb.lf.rec._href, 'https://www.mastermind-x.com/terminal?sym=NVDA', 'standalone raw assignment kept');
      const bridge = bridgeQueued();
      const q = runFallback(which, bridge);
      assert.deepStrictEqual(bridge.calls, [['/terminal?symbol=NVDA&from=macro', 'push']],
        'the central native handoff owns candidate launches before every overlay fallback');
      assert.deepStrictEqual(q.st, { buildOverlays: 0, frames: 0 }, 'no nested UI before the native handoff');
      assert.strictEqual(q.lf.rec.hrefWrites, 0, 'no raw Location after hand-off or refusal - external/unadmitted stays in frame');
      const refusing = bridgeRefusing();
      const r = runFallback(which, refusing);
      assert.deepStrictEqual(refusing.calls.length, 1);
      assert.strictEqual(r.lf.rec.hrefWrites, 0, 'refusal must not escape the shell frame');
    });
  }
}

/* ===================================================================== *
 * 6. Cross-cutting shipped-text invariants (guard against regressions that
 *    reintroduce the refused candidate's .active gate)
 * ===================================================================== */
{
  const touched = ANALYZER_FILES.concat([
    'baskets.html.j2', 'baskets_china.html.j2', 'dashboard.html.j2', 'finance_intelligence.js',
    'flow_desk.html.j2', 'flow_leaders.html.j2', 'gex.html.j2', 'heatmap.js', 'hk.html.j2',
    'mm_brain.js', 'options_screener.html.j2', 'sector_central.html.j2', 'stocktable.js',
    'subsector_rotation.html.j2', 'subsector_rotation.js', 'subsector_rotation_china.html.j2',
    'terminal_overlay.js', 'ticker_index.html.j2', 'vector_allocation.html.j2',
  ]);
  test('no adapter gates the bridge on .active anywhere in the touched sources', function () {
    for (const f of touched) {
      const text = src(f);
      assert.ok(!/_ss\d?\.active/.test(text), f + ': .active gate reintroduced');
    }
  });
  test('every touched source gates on window.MMXSharedShell presence and falls back only when absent', function () {
    for (const f of touched) {
      const text = src(f);
      assert.ok(text.includes('window.MMXSharedShell'), f + ': bridge presence gate missing');
    }
  });
}
