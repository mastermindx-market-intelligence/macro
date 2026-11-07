/*
 * Node guard/handshake verification for shared_shell_bridge_final.js (vm sandbox,
 * no browser, no DOM). Run from the delivered directory:
 *   node --test shared_shell_bridge_final.test.cjs
 */
'use strict';
const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const SRC = fs.readFileSync(path.join(__dirname, '..', '..', 'templates', 'shared_shell_bridge.js'), 'utf8');
const CSS = fs.readFileSync(path.join(__dirname, '..', '..', 'templates', 'shared_shell.css'), 'utf8');
const CSS_READY = /--mmx-shared-shell-css-ready:\s*([^;]+);/.exec(CSS)[1].trim();
const PROD = 'https://beta.mastermind-x.com';

function harness(opts) {
  const o = Object.assign({
    childUrl: 'https://www.mastermind-x.com/tools?q=alpha&mmx_shell=1&mmx_generation=g1#top',
    referrer: PROD + '/shell',
    parent: PROD,
    ready: 'complete',
    metaContent: '20261018.1',
    responseKind: 'content',
    standalone: false,
    cssReady: CSS_READY,
    cssReadError: false,
  }, opts || {});
  const sent = [];
  const seq = []; // ordered evidence of messages vs child-document mutations
  const calls = { scrollTo: [], setTheme: [], setLang: [], focus: [], cssReads: 0 };
  let cssReady = o.cssReady;
  const winL = {};
  const docL = {};
  const nodes = [];
  const styles = [];
  const dispatched = [];
  const replaceCalls = [];
  const pushCalls = [];
  let hloc = new URL(o.childUrl);

  function mkEl(tag, attrs) {
    const a = Object.assign({}, attrs || {});
    const el = {
      tagName: String(tag).toUpperCase(),
      nodeType: 1,
      parent: null,
      children: [],
      __attrs: a,
      getAttribute(n) { return Object.prototype.hasOwnProperty.call(a, n) ? a[n] : null; },
      setAttribute(n, v) { a[n] = String(v); },
      hasAttribute(n) { return Object.prototype.hasOwnProperty.call(a, n); },
      removeAttribute(n) { delete a[n]; },
      addEventListener() {}, removeEventListener() {},
      appendChild(c) { el.children.push(c); c.parent = el; return c; },
      focus(opt) { calls.focus.push({ el, preventScroll: !!(opt && opt.preventScroll) }); seq.push('FOCUS:' + (a.id || el.tagName)); },
      scrollIntoView() { calls.scrollTo.push({ intoView: a.id || null }); seq.push('SCROLL:' + (a.id || '')); },
      querySelectorAll(sel) { return doc.__qsa(sel); },
      closest(sel) {
        if (sel === "a[href]" && el.tagName === "A" && Object.prototype.hasOwnProperty.call(a, "href")) return el;
        return null;
      },
    };
    Object.defineProperty(el, 'id', { get: () => a.id || '' });
    Object.defineProperty(el, 'href', { get: () => a.href || '' });
    nodes.push(el);
    return el;
  }

  function MOShim(cb) {
    const self = this;
    self.__cb = cb;
    self.__active = false;
    self.observe = function () { self.__active = true; docEl.__observers.push(self); };
    self.disconnect = function () { self.__active = false; };
  }

  const docEl = mkEl('html');
  docEl.__observers = [];
  const head = mkEl('head');
  const body = mkEl('body');
  const doc = {
    nodeType: 9,
    documentElement: docEl,
    head,
    body,
    title: 'Market OS child',
    referrer: o.referrer,
    readyState: o.ready,
    activeElement: body,
    createElement(tag) {
      const a = {};
      const el = {
        tagName: String(tag).toUpperCase(),
        nodeType: 1,
        __attrs: a,
        children: [],
        getAttribute(n) { return Object.prototype.hasOwnProperty.call(a, n) ? a[n] : null; },
        setAttribute(n, v) { a[n] = String(v); },
        hasAttribute(n) { return Object.prototype.hasOwnProperty.call(a, n); },
        removeAttribute(n) { delete a[n]; },
        appendChild(c) { el.children.push(c); c.parent = el; return c; },
        addEventListener() {}, removeEventListener() {},
      };
      let text = '';
      Object.defineProperty(el, 'textContent', { get: () => text, set: (v) => { text = String(v); } });
      Object.defineProperty(el, 'content', { get: () => a.content || '', set: (v) => { a.content = String(v); } });
      if (String(tag).toLowerCase() === 'style') styles.push(el);
      return el;
    },
    querySelector(sel) { return doc.__qsa(sel)[0] || null; },
    querySelectorAll(sel) { return doc.__qsa(sel); },
    __qsa(sel) {
      if (/^meta\[name=/.test(sel)) {
        const nm = sel.replace(/^meta\[name="?([^"\]]+)"?\]$/, '$1');
        if (nm === 'mmx-shell-response') return responseNode ? [responseNode] : [];
        return metaNode && nm === 'mmx-shell-document' ? [metaNode] : [];
      }
      if (sel === 'a[href]') return nodes.filter((el) => el.tagName === 'A' && el.hasAttribute('href'));
      if (sel === 'main,[role="main"],h1') return nodes.filter((el) => el.tagName === 'MAIN' || el.getAttribute('role') === 'main' || el.tagName === 'H1');
      return [];
    },
    getElementById(id) { return nodes.find((el) => el.getAttribute('id') === String(id)) || null; },
    addEventListener(type, fn) { (docL[type] = docL[type] || []).push(fn); },
    removeEventListener(type, fn) { if (docL[type]) docL[type] = docL[type].filter((f) => f !== fn); },
    dispatchEvent(evt) { dispatched.push(evt); return true; },
  };

  const responseNode = o.responseKind === null ? null : doc.createElement('meta');
  if (responseNode) { responseNode.setAttribute('name', 'mmx-shell-response'); responseNode.setAttribute('content', o.responseKind); }
  let metaNode = null;
  if (o.metaContent !== null) {
    metaNode = doc.createElement('meta');
    metaNode.setAttribute('name', 'mmx-shell-document');
    metaNode.setAttribute('content', o.metaContent);
  }
  const setMeta = (content) => {
    if (content === null) { metaNode = null; return; }
    metaNode = doc.createElement('meta');
    metaNode.setAttribute('name', 'mmx-shell-document');
    metaNode.setAttribute('content', content);
  };

  const historyObj = {
    state: { marker: 'original' },
    pushState(state_, title, url2) {
      pushCalls.push({ state: state_, url: url2 === undefined || url2 === null ? undefined : String(url2) });
      seq.push('PUSH');
      if (url2 !== undefined && url2 !== null) { try { hloc = new URL(String(url2), hloc.href); } catch (e) {} }
    },
    replaceState(state_, title, url2) {
      replaceCalls.push({ state: state_, url: url2 === undefined || url2 === null ? undefined : String(url2) });
      seq.push('REPLACE');
      if (url2 !== undefined && url2 !== null) { try { hloc = new URL(String(url2), hloc.href); } catch (e) {} }
    },
  };
  const nativePushRef = historyObj.pushState;
  const nativeReplaceRef = historyObj.replaceState;

  const frame = { __shellFrame: true, postMessage(msg, to) { sent.push({ to, msg }); seq.push('MSG:' + msg.type); } };

  const sandbox = {
    document: doc,
    history: historyObj,
    scrollX: 0,
    scrollY: 0,
    // Simulate a stylesheet already loaded before the blocking bridge executes;
    // readiness must not depend on observing a link load event afterward.
    getComputedStyle(el) {
      calls.cssReads++;
      if (o.cssReadError) throw new Error('stylesheet unavailable');
      return { getPropertyValue(name) {
        return name === '--mmx-shared-shell-css-ready' && el.getAttribute('data-mmx-shared-shell') === '1' ? cssReady : '';
      } };
    },
    scrollTo(x, y) { calls.scrollTo.push({ x, y }); seq.push('SCROLLTO'); },
    addEventListener(type, fn) { (winL[type] = winL[type] || []).push(fn); },
    dispatchEvent(evt) { dispatched.push(evt); (winL[evt.type] || []).slice().forEach((fn) => fn(evt)); return true; },
    removeEventListener(type, fn) { if (winL[type]) winL[type] = winL[type].filter((f) => f !== fn); },
    URL, URLSearchParams, setTimeout, clearTimeout, CustomEvent, MutationObserver: MOShim,
  };
  sandbox.window = sandbox;
  sandbox.self = sandbox;
  sandbox.globalThis = sandbox;
  sandbox.parent = o.standalone ? sandbox : frame;
  Object.defineProperty(sandbox, 'location', { get: () => hloc, configurable: true });
  vm.createContext(sandbox);
  vm.runInContext(SRC, sandbox);

  const ctx = {
    sandbox, sent, seq, calls, winL, docL, doc, docEl, nodes, styles, dispatched,
    replaceCalls, pushCalls, head, frame, setMeta, mkEl,
    location: () => hloc,
    nativePushRef, nativeReplaceRef,
    api: () => sandbox.MMXSharedShell,
    setCssReady: (value) => { cssReady = value; },
    activeCount: (type) => sent.filter((s) => s.msg.type === type).length,
    lastOf: (type) => { const l = sent.filter((s) => s.msg.type === type); return l.length ? l[l.length - 1].msg : null; },
    // ordering of one event loop turn of evidence, from a marker index
    tail: (from) => seq.slice(from),
    mutateAdd(el) {
      docEl.__observers.filter((obs) => obs.__active)
        .forEach((obs) => obs.__cb([{ type: 'childList', target: docEl, addedNodes: [el] }], obs));
    },
    mutateAttr(el, name) {
      docEl.__observers.filter((obs) => obs.__active)
        .forEach((obs) => obs.__cb([{ type: 'attributes', attributeName: name, target: el }], obs));
    },
    dispatchMessage(data, overrides) {
      const evt = Object.assign({
        type: 'message',
        origin: o.parent,
        source: sandbox.parent,
        data: JSON.parse(JSON.stringify(data)),
      }, overrides || {});
      (winL.message || []).slice().forEach((fn) => fn(evt));
    },
    fireWin(type, extra) {
      (winL[type] || []).slice().forEach((fn) => fn(Object.assign({ type }, extra || {})));
    },
    fireDoc(type, extra) {
      (docL[type] || []).slice().forEach((fn) => fn(Object.assign({ type }, extra || {})));
    },
    click(el, mods) {
      const evt = Object.assign({
        type: 'click', button: 0, ctrlKey: false, metaKey: false, shiftKey: false, altKey: false,
        target: el, defaultPrevented: false, preventDefault() { evt.defaultPrevented = true; },
      }, mods || {});
      (docL.click || []).slice().forEach((fn) => fn(evt));
      return evt;
    },
  };
  ctx.initMsg = (over) => Object.assign({
    protocol: 'mmx.shared-shell.v1',
    frameGeneration: 'g1',
    type: 'INIT',
    theme: 'dark',
    locale: 'en',
    contextRevision: 3,
    canonicalPath: '/tools',
    catalog: { legacyPaths: ['/tools', '/dashboard', '/all-tools'], nativePaths: ['/pricing', '/account/settings'] },
    restore: null,
  }, over || {});
  ctx.contextMsg = (over) => Object.assign({
    protocol: 'mmx.shared-shell.v1', frameGeneration: 'g1', type: 'CONTEXT', theme: 'dark', locale: 'en', contextRevision: 4,
  }, over || {});
  ctx.activate = (over) => { ctx.dispatchMessage(ctx.initMsg(over)); return ctx; };
  return ctx;
}

// The actual incumbent setters from the supplied theme excerpt: setLang writes
// data-lang AND html lang="zh-CN" (WCAG 3.1.1) and notifies the document; setTheme
// writes data-theme and notifies. Used to prove boot restoration and the locale
// convention instead of an idealized attribute-only page.
function incumbent(ctx) {
  const seen = { theme: [], lang: [] };
  ctx.sandbox.setTheme = (v) => {
    seen.theme.push(v);
    ctx.docEl.setAttribute('data-theme', v);
    ctx.fireDoc('themechange');
  };
  ctx.sandbox.setLang = (v) => {
    seen.lang.push(v);
    ctx.docEl.setAttribute('data-lang', v);
    ctx.docEl.setAttribute('lang', v === 'zh' ? 'zh-CN' : 'en');
    ctx.fireDoc('langchange');
  };
  return seen;
}

const ENV3 = ['protocol', 'frameGeneration', 'type'];
const READY_FIELDS = ['title', 'href', 'contextRevision', 'bridgeVersion', 'documentVersion', 'responseKind'];
const BYTES = 'q=A%20B&set=1,2&set=3%2c4&plus=A+B';

test('standalone page: zero surface', () => {
  const ctx = harness({ standalone: true });
  assert.strictEqual(ctx.sandbox.MMXSharedShell, undefined);
  assert.strictEqual(ctx.sent.length, 0);
  assert.strictEqual(ctx.sandbox.history.pushState, ctx.nativePushRef);
  assert.strictEqual(ctx.docEl.getAttribute('data-mmx-shared-shell'), null);
  assert.strictEqual(ctx.calls.cssReads, 0);
  assert.strictEqual(ctx.styles.length, 0);
});

test('candidate guards: flag, generation, referrer', () => {
  assert.strictEqual(harness({ childUrl: 'https://www.mastermind-x.com/tools?mmx_generation=g1' }).api(), undefined);
  assert.strictEqual(harness({ childUrl: 'https://www.mastermind-x.com/tools?mmx_shell=0&mmx_generation=g1' }).api(), undefined);
  assert.strictEqual(harness({ childUrl: 'https://www.mastermind-x.com/tools?mmx_shell=1&mmx_generation=' }).api(), undefined);
  assert.strictEqual(harness({ childUrl: 'https://www.mastermind-x.com/tools?mmx_shell=1&mmx_generation=' + 'z'.repeat(129) }).api(), undefined);
  assert.strictEqual(harness({ referrer: 'https://evil.example/shell' }).api(), undefined);
  assert.strictEqual(harness({ referrer: PROD }).api().__mmxBridge, 'mmx.shared-shell.v1');
  // localhost parent allowance never active on www child
  assert.strictEqual(harness({ referrer: 'http://localhost:3100/shell' }).api(), undefined);
  // localhost child may use exact local parent
  const local = harness({
    childUrl: 'http://localhost:3105/tools?mmx_shell=1&mmx_generation=g1',
    referrer: 'http://127.0.0.1:3100/shell',
    parent: 'http://127.0.0.1:3100',
  });
  assert.strictEqual(local.api().active, false); // exact 127.0.0.1 parent allowed for local child
  assert.strictEqual(harness({
    childUrl: 'http://localhost:3105/tools?mmx_shell=1&mmx_generation=g1',
    referrer: 'http://localhost:4000/shell',
  }).api(), undefined); // only the exact local parents are allowed
  const local2 = harness({
    childUrl: 'http://localhost:3105/tools?mmx_shell=1&mmx_generation=g1',
    referrer: 'http://localhost:3100/shell',
    parent: 'http://localhost:3100',
  });
  assert.strictEqual(local2.api().active, false);
  local2.activate({ canonicalPath: '/tools' });
  assert.ok(local2.sent.every((s) => s.to === 'http://localhost:3100'));
  assert.strictEqual(local2.lastOf('READY').href, 'http://localhost:3105/tools');
});

test('INIT rejects unverified sources without effects', () => {
  const ctx = harness();
  ctx.dispatchMessage(ctx.initMsg(), { source: {} });
  assert.strictEqual(ctx.api().active, false);
  ctx.dispatchMessage(Object.assign(ctx.initMsg(), { frameGeneration: 'other' }));
  ctx.dispatchMessage(Object.assign(ctx.initMsg(), { protocol: 'mmx.shared-shell.v0' }));
  ctx.dispatchMessage(Object.assign(ctx.initMsg(), { evil: 1 }));
  ctx.dispatchMessage(Object.assign(ctx.initMsg(), { catalog: { legacyPaths: ['/tools'], nativePaths: ['/tools'] } }));
  ctx.dispatchMessage(Object.assign(ctx.initMsg(), { catalog: { legacyPaths: ['tools'], nativePaths: [], extra: 1 } }));
  assert.strictEqual(ctx.sent.length, 0);
  assert.strictEqual(ctx.api().active, false);
  assert.strictEqual(ctx.docEl.getAttribute('data-mmx-shared-shell'), null);
});

test('missing document meta: initialization_failed, no activation', () => {
  const ctx = harness({ metaContent: null });
  ctx.activate();
  assert.strictEqual(ctx.api().active, false);
  assert.strictEqual(ctx.sent.length, 1);
  assert.deepStrictEqual(Object.keys(ctx.sent[0].msg).sort(), ENV3.concat(['code']).sort());
  assert.strictEqual(ctx.lastOf('ERROR').code, 'initialization_failed');
  assert.strictEqual(ctx.docEl.getAttribute('data-mmx-shared-shell'), null);
  assert.strictEqual(ctx.styles.length, 0);
});

test('valid INIT: chrome suppression, context, READY shape', () => {
  const seen = { theme: [], lang: [] };
  const ctx = harness();
  ctx.sandbox.setTheme = (v) => seen.theme.push(v);
  ctx.sandbox.setLang = (v) => seen.lang.push(v);
  ctx.activate();
  assert.strictEqual(ctx.api().active, true);
  assert.strictEqual(ctx.docEl.getAttribute('data-mmx-shared-shell'), '1');
  assert.strictEqual(ctx.docEl.getAttribute('data-theme'), 'dark');
  assert.strictEqual(ctx.docEl.getAttribute('lang'), 'en');
  assert.deepStrictEqual(seen.theme, ['dark']);
  assert.deepStrictEqual(seen.lang, ['en']);
  assert.strictEqual(ctx.styles.length, 0);
  assert.ok(ctx.calls.cssReads > 0);
  const css = CSS;
  assert.ok(css.indexOf('.site-nav') !== -1 && css.indexOf('[data-mmx-all-tools]') !== -1 && css.indexOf('#mmx-all-tools') !== -1);
  assert.ok(css.indexOf('.public-nav') !== -1 && css.indexOf('.landing-nav') !== -1);
  assert.ok(css.indexOf('header') === -1);
  const mainNav = 'body > nav.nav[aria-label="Main"]';
  assert.ok(css.includes('html[data-mmx-shared-shell="1"] ' + mainNav + ','));
  // Only this body-level public component may use a nav tag selector.
  assert.ok(!/(^|[\s,>])nav(\s|\{|,|\.|$)/m.test(css.replace(mainNav, '')));
  const ready = ctx.lastOf('READY');
  assert.ok(ready);
  assert.deepStrictEqual(Object.keys(ready).sort(), ENV3.concat(READY_FIELDS).sort());
  assert.strictEqual(ready.bridgeVersion, '20261018.1');
  assert.strictEqual(ready.documentVersion, '20261018.1');
  assert.strictEqual(ready.contextRevision, 3);
  assert.strictEqual(ready.href, 'https://www.mastermind-x.com/tools?q=alpha#top');
  assert.ok(typeof ready.title === 'string' && ready.title.length <= 240);
  assert.ok(ctx.sent.every((s) => s.to === PROD));
});

test('static chrome rules are dormant and both published assets match their templates', () => {
  assert.strictEqual(CSS_READY, '1');
  for (const rule of CSS.replace(/\/\*[\s\S]*?\*\//g, '').split('}').filter((s) => s.trim())) {
    const selectors = rule.split('{')[0].split(',');
    assert.ok(selectors.every((selector) => selector.trim().startsWith('html[data-mmx-shared-shell="1"]')));
  }
  for (const [name, expected] of [['shared_shell.css', CSS], ['shared_shell_bridge.js', SRC]]) {
    assert.strictEqual(fs.readFileSync(path.join(__dirname, '..', '..', 'site', name), 'utf8'), expected);
  }
});

test('unverified INIT cannot activate or probe shell CSS', () => {
  const ctx = harness();
  ctx.dispatchMessage(ctx.initMsg(), { origin: 'https://evil.example' });
  ctx.dispatchMessage(ctx.initMsg(), { source: {} });
  ctx.dispatchMessage(ctx.initMsg({ frameGeneration: 'old-generation' }));
  assert.strictEqual(ctx.docEl.getAttribute('data-mmx-shared-shell'), null);
  assert.strictEqual(ctx.calls.cssReads, 0);
  assert.strictEqual(ctx.styles.length, 0);
  assert.strictEqual(ctx.activeCount('READY'), 0);
});

test('missing, blocked, wrong or unreadable CSS refuses activation and queued navigation', () => {
  for (const options of [{ cssReady: '' }, { cssReady: 'wrong' }, { cssReadError: true }, { cssReady: null }]) {
    const ctx = harness(options);
    assert.strictEqual(ctx.api().navigate('/dashboard'), true);
    ctx.activate();
    assert.strictEqual(ctx.api().active, false);
    assert.strictEqual(ctx.docEl.getAttribute('data-mmx-shared-shell'), null);
    assert.strictEqual(ctx.activeCount('READY'), 0);
    assert.strictEqual(ctx.activeCount('NAVIGATE'), 0);
    assert.strictEqual(ctx.lastOf('ERROR').code, 'initialization_failed');
    assert.strictEqual(ctx.docEl.__observers.length, 0);
    assert.strictEqual(ctx.styles.length, 0);
    assert.strictEqual(ctx.calls.focus.length, 0);
  }
  const unsupported = harness();
  delete unsupported.sandbox.getComputedStyle;
  unsupported.activate();
  assert.strictEqual(unsupported.api().active, false);
  assert.strictEqual(unsupported.activeCount('READY'), 0);
  assert.strictEqual(unsupported.docEl.getAttribute('data-mmx-shared-shell'), null);
});

test('CSS removed during document boot cannot produce initial READY or restoration', () => {
  const ctx = harness({ ready: 'loading' }).activate({ restore: { x: 10, y: 20 } });
  assert.strictEqual(ctx.api().active, true);
  ctx.setCssReady('');
  ctx.fireDoc('DOMContentLoaded');
  assert.strictEqual(ctx.activeCount('READY'), 0);
  assert.strictEqual(ctx.lastOf('ERROR').code, 'initialization_failed');
  assert.strictEqual(ctx.calls.scrollTo.length, 0);
  assert.strictEqual(ctx.calls.focus.length, 0);
});

test('CSS removal prevents subsequent CONTEXT or repeated INIT readiness claims', () => {
  const ctx = harness().activate();
  const readyCount = ctx.activeCount('READY');
  assert.strictEqual(readyCount, 1);
  ctx.setCssReady('');
  ctx.dispatchMessage(ctx.contextMsg());
  assert.strictEqual(ctx.activeCount('READY'), readyCount);
  assert.strictEqual(ctx.lastOf('ERROR').code, 'initialization_failed');
  ctx.dispatchMessage(ctx.initMsg({ contextRevision: 5 }));
  assert.strictEqual(ctx.activeCount('READY'), readyCount);
  assert.strictEqual(ctx.lastOf('ERROR').code, 'initialization_failed');
});

test('CONTEXT apply, staleness, unsupported_context', () => {
  const seen = { theme: [], lang: [] };
  const ctx = harness();
  ctx.sandbox.setTheme = (v) => seen.theme.push(v);
  ctx.sandbox.setLang = (v) => seen.lang.push(v);
  ctx.activate();
  ctx.dispatchMessage(ctx.contextMsg({ theme: 'light', contextRevision: 4 }));
  assert.deepStrictEqual(seen.theme, ['dark', 'light']);
  assert.strictEqual(ctx.docEl.getAttribute('data-theme'), 'light');
  ctx.dispatchMessage(ctx.contextMsg({ theme: 'dark', contextRevision: 4 }));
  assert.deepStrictEqual(seen.theme, ['dark', 'light']); // stale ignored
  const errsBefore = ctx.activeCount('ERROR');
  ctx.dispatchMessage(ctx.contextMsg({ theme: 'light', locale: 'de', contextRevision: 5 }));
  assert.strictEqual(ctx.activeCount('ERROR'), errsBefore + 1);
  assert.strictEqual(ctx.lastOf('ERROR').code, 'unsupported_context');
  assert.strictEqual(ctx.docEl.getAttribute('lang'), 'en');
});

test('user themechange echoes as CONTEXT_REQUEST; suppression while applying', () => {
  const ctx = harness();
  ctx.sandbox.setTheme = (v) => {
    ctx.docEl.setAttribute('data-theme', v);
    ctx.fireDoc('themechange'); // incumbent setter notifies; must not echo during parent apply
  };
  ctx.activate();
  assert.strictEqual(ctx.activeCount('CONTEXT_REQUEST'), 0);
  ctx.docEl.setAttribute('data-theme', 'light');
  ctx.fireDoc('themechange');
  const msg = ctx.lastOf('CONTEXT_REQUEST');
  assert.deepStrictEqual(Object.keys(msg).sort(), ENV3.concat(['theme']).sort());
  assert.strictEqual(msg.theme, 'light');
});

test('VISIBILITY dispatches exactly one CustomEvent shape', () => {
  const ctx = harness();
  ctx.activate();
  const n = ctx.dispatched.length;
  ctx.dispatchMessage({ protocol: 'mmx.shared-shell.v1', frameGeneration: 'g1', type: 'VISIBILITY', visible: false });
  ctx.dispatchMessage({ protocol: 'mmx.shared-shell.v1', frameGeneration: 'g1', type: 'VISIBILITY', visible: true, evil: 1 });
  assert.strictEqual(ctx.dispatched.length, n + 1);
  const evt = ctx.dispatched[n];
  assert.strictEqual(evt.type, 'mmx:shell-visibility');
  assert.deepStrictEqual(Object.keys(evt.detail), ['visible']);
  assert.strictEqual(evt.detail.visible, false);
});

test('LOCATION_ACCEPTED and stale kinds have no outbound effect', () => {
  const ctx = harness();
  ctx.activate();
  ctx.sandbox.MMXSharedShell.navigate('/pricing');
  const rid = ctx.lastOf('NAVIGATE').requestId;
  const before = ctx.sent.length;
  ctx.dispatchMessage({ protocol: 'mmx.shared-shell.v1', frameGeneration: 'g1', type: 'LOCATION_ACCEPTED', requestId: rid, canonicalPath: '/pricing' });
  ctx.dispatchMessage({ protocol: 'mmx.shared-shell.v1', frameGeneration: 'g1', type: 'LOCATION_ACCEPTED', requestId: 'other', canonicalPath: '/pricing', junk: 1 });
  ctx.dispatchMessage({ protocol: 'mmx.shared-shell.v1', frameGeneration: 'g1', type: 'MYSTERY' });
  assert.strictEqual(ctx.sent.length, before);
});

test('navigate after INIT: catalog-exact admission and closed keys', () => {
  const ctx = harness();
  ctx.activate();
  const before = ctx.sent.length;
  assert.strictEqual(ctx.sandbox.MMXSharedShell.navigate('/pricing'), true);
  assert.strictEqual(ctx.sandbox.MMXSharedShell.navigate('/tools-extra'), false);
  assert.strictEqual(ctx.sandbox.MMXSharedShell.navigate('https://www.mastermind-x.com/tools?access_token=x'), false);
  assert.strictEqual(ctx.sandbox.MMXSharedShell.navigate('https://evil.example/tools'), false);
  assert.strictEqual(ctx.sandbox.MMXSharedShell.navigate('/pricing', 'sideways'), false);
  const nav = ctx.lastOf('NAVIGATE');
  assert.deepStrictEqual(Object.keys(nav).sort(), ENV3.concat(['href', 'mode', 'sameDocument', 'requestId']).sort());
  assert.strictEqual(ctx.sandbox.MMXSharedShell.navigate('/pricing'), true); // fragment-free, same target
  const nav2 = ctx.lastOf('NAVIGATE');
  assert.strictEqual(nav2.href, 'https://www.mastermind-x.com/pricing');
  assert.strictEqual(nav2.mode, 'push');
  assert.strictEqual(nav2.sameDocument, false);
  assert.ok(typeof nav2.requestId === 'string' && nav2.requestId.length <= 128);
  assert.strictEqual(ctx.sent[before].msg.type, 'VIEW_STATE'); // view captured immediately before NAVIGATE
  assert.deepStrictEqual(Object.keys(ctx.sent[before].msg).sort(), ENV3.concat(['view']).sort());
  const codes = ctx.sent.slice(before).map((s) => s.msg.code).filter(Boolean);
  assert.ok(codes.indexOf('navigation_unavailable') !== -1 && codes.indexOf('authentication_navigation') !== -1);
  const errs = ctx.sent.filter((s) => s.msg.type === 'ERROR');
  assert.deepStrictEqual(Object.keys(errs[0].msg).sort(), ENV3.concat(['code']).sort());
  assert.strictEqual(ctx.sandbox.MMXSharedShell.navigate('/all-tools?mmx_generation=zz'), true);
  assert.strictEqual(ctx.lastOf('NAVIGATE').href.indexOf('mmx_'), -1); // transport stripped in canonical URL
});

test('openAuth intents only', () => {
  const ctx = harness();
  ctx.activate();
  assert.strictEqual(ctx.sandbox.MMXSharedShell.openAuth('billing'), true);
  assert.strictEqual(ctx.sandbox.MMXSharedShell.openAuth('sessions'), false);
  assert.strictEqual(ctx.activeCount('AUTH_REQUEST'), 1);
  assert.deepStrictEqual(Object.keys(ctx.lastOf('AUTH_REQUEST')).sort(), ENV3.concat(['intent']).sort());
});

test('anchors: projection, same-tab click, external, download', () => {
  const ctx = harness();
  ctx.activate();
  const pricing = ctx.mkEl('a', { href: '/pricing' });
  const external = ctx.mkEl('a', { href: 'https://external.example/x' });
  const dl = ctx.mkEl('a', { href: '/tools', download: '' });
  const secret = ctx.mkEl('a', { href: '/secret' });
  [pricing, external, dl, secret].forEach((el) => ctx.mutateAdd(el));
  assert.strictEqual(pricing.getAttribute('href'), PROD + '/pricing');
  assert.strictEqual(ctx.replaceCalls.length, 0);
  const b1 = ctx.sent.length;
  const ev1 = ctx.click(pricing);
  assert.strictEqual(ev1.defaultPrevented, true);
  assert.strictEqual(ctx.lastOf('NAVIGATE').href, 'https://www.mastermind-x.com/pricing');
  assert.strictEqual(ctx.lastOf('NAVIGATE').sameDocument, false);
  assert.strictEqual(ctx.activeCount('NAVIGATE'), 1);
  // modified click keeps native semantics
  const b2 = ctx.sent.length;
  const ev2 = ctx.click(pricing, { ctrlKey: true });
  assert.strictEqual(ev2.defaultPrevented, false);
  assert.strictEqual(ctx.sent.length, b2);
  // external keeps native anchor and opens outside the frame
  assert.strictEqual(external.getAttribute('target'), '_blank');
  assert.ok((external.getAttribute('rel') || '').indexOf('noopener') !== -1);
  // download untouched
  assert.strictEqual(dl.getAttribute('href'), '/tools');
  assert.strictEqual(dl.getAttribute('target'), null);
  // unadmitted internal link: intercepted with navigation_unavailable, no leak
  const errs = ctx.activeCount('ERROR');
  ctx.mutateAdd(secret);
  const ev4 = ctx.click(secret);
  assert.strictEqual(ev4.defaultPrevented, true);
  assert.strictEqual(ctx.activeCount('ERROR'), errs + 1);
  assert.strictEqual(ctx.lastOf('ERROR').code, 'navigation_unavailable');
  assert.strictEqual(ctx.sent[b1].to, PROD);
});

test('uncontrolled hashchange/popstate reports navigation_unavailable only', () => {
  const ctx = harness();
  ctx.activate();
  const errs = ctx.activeCount('ERROR');
  ctx.fireWin('popstate');
  ctx.fireWin('hashchange');
  assert.strictEqual(ctx.activeCount('ERROR'), errs + 2);
  assert.strictEqual(ctx.activeCount('NAVIGATE'), 0);
});

test('scroll VIEW_STATE throttled to about 100ms', async () => {
  const ctx = harness();
  ctx.activate();
  const before = ctx.activeCount('VIEW_STATE');
  ctx.sandbox.scrollY = 250;
  ctx.fireWin('scroll');
  assert.strictEqual(ctx.activeCount('VIEW_STATE'), before);
  await new Promise((r) => setTimeout(r, 220));
  const vs = ctx.lastOf('VIEW_STATE');
  assert.strictEqual(ctx.activeCount('VIEW_STATE'), before + 1);
  assert.deepStrictEqual(Object.keys(vs).sort(), ENV3.concat(['view']).sort());
  assert.strictEqual(vs.view.y, 250);
  assert.strictEqual(vs.view.x, 0);
  assert.strictEqual(vs.view.focusId, undefined);
});

test('pre-INIT: queue cap 8, replace-only history, drain after INIT', () => {
  const ctx = harness();
  const api = ctx.api();
  assert.strictEqual(api.active, false);
  // local replace retains caller state and transport; never pushes an entry
  ctx.sandbox.history.replaceState({ s: 1 }, '', '/tools');
  assert.strictEqual(ctx.replaceCalls.length, 1);
  assert.strictEqual(ctx.pushCalls.length, 0);
  assert.strictEqual(ctx.replaceCalls[0].state.s, 1);
  assert.ok(ctx.replaceCalls[0].url.indexOf('mmx_generation=g1') !== -1);
  assert.strictEqual(ctx.sandbox.MMXSharedShell.openAuth('signin'), true);
  for (let i = 0; i < 6; i++) assert.strictEqual(ctx.sandbox.MMXSharedShell.navigate('/tools?q=beta'), true);
  assert.strictEqual(ctx.sandbox.MMXSharedShell.navigate('/pricing'), false); // queue full (history+auth+6 nav)
  assert.strictEqual(ctx.sent.length, 0);
  ctx.activate();
  assert.strictEqual(ctx.activeCount('AUTH_REQUEST'), 1);
  assert.strictEqual(ctx.activeCount('NAVIGATE'), 7);
  const firstNav = ctx.sent.filter((s) => s.msg.type === 'NAVIGATE')[0].msg;
  assert.strictEqual(firstNav.sameDocument, true);
  assert.ok(firstNav.href.indexOf('/tools') !== -1 && firstNav.href.indexOf('mmx_') === -1);
  const ids = ctx.sent.filter((s) => s.msg.type === 'NAVIGATE').map((s) => s.msg.requestId);
  assert.strictEqual(new Set(ids).size, ids.length);
  // queued messages drain in order BEFORE the actual READY
  const readyIndex = ctx.sent.map((s) => s.msg.type).indexOf('READY');
  assert.strictEqual(readyIndex, ctx.sent.length - 1);
  assert.ok(readyIndex > ctx.sent.map((s) => s.msg.type).lastIndexOf('NAVIGATE'));
});

test('pre-INIT sensitive history becomes queued authentication_navigation', () => {
  const ctx = harness();
  ctx.sandbox.history.pushState({}, '', '/tools?access_token=x');
  assert.strictEqual(ctx.pushCalls.length, 0);
  assert.strictEqual(ctx.replaceCalls.length, 0);
  ctx.activate();
  assert.strictEqual(ctx.lastOf('ERROR').code, 'authentication_navigation');
});

test('restore and fresh-page focus', () => {
  const ctx = harness();
  const target = ctx.mkEl('div', { id: 'a:1' });
  ctx.activate({ restore: { x: 0, y: 1200, focusId: 'a:1' } });
  assert.ok(ctx.calls.scrollTo.some((s) => s.x === 0 && s.y === 1200));
  assert.ok(ctx.calls.focus.some((f) => f.el === target && f.preventScroll === true));
  const ctx2 = harness();
  const h1 = ctx2.mkEl('h1');
  ctx2.activate({ restore: null });
  assert.ok(ctx2.calls.focus.some((f) => f.el === h1 && f.preventScroll === true));
  assert.strictEqual(h1.getAttribute('tabindex'), null); // tabindex restored after focus
  const ctx3 = harness();
  ctx3.activate({ restore: { x: 0, y: 20, focusId: 'bad id!' } });
  assert.strictEqual(ctx3.api().active, false); // malformed INIT ignored
  assert.strictEqual(ctx3.sent.length, 0);
});

test('pagehide: listeners removed, history unwrapped, api inert', () => {
  const ctx = harness();
  ctx.activate();
  const before = ctx.sent.length;
  ctx.fireWin('pagehide');
  assert.strictEqual(ctx.winL.message.length, 0);
  assert.strictEqual(ctx.sandbox.history.pushState, ctx.nativePushRef);
  assert.strictEqual(ctx.sandbox.history.replaceState, ctx.nativeReplaceRef);
  assert.strictEqual(ctx.sandbox.MMXSharedShell, undefined);
  ctx.fireWin('popstate');
  ctx.dispatchMessage({ protocol: 'mmx.shared-shell.v1', frameGeneration: 'g1', type: 'VISIBILITY', visible: true });
  assert.strictEqual(ctx.sent.length, before);
});

/* ---- FIX 1: bounded catalog that fits the real canonical projection ---- */
test('catalog bound admits the real 13015 legacy + 14 native projection', () => {
  const legacy = [];
  for (let i = 0; i < 13015; i++) legacy.push('/t/legacy-' + i);
  const native = [];
  for (let i = 0; i < 14; i++) native.push('/n/native-' + i);
  const ctx = harness();
  ctx.activate({ canonicalPath: '/t/legacy-0', catalog: { legacyPaths: legacy, nativePaths: native } });
  assert.strictEqual(ctx.api().active, true);
  assert.strictEqual(ctx.lastOf('READY').contextRevision, 3);
  assert.strictEqual(ctx.sandbox.MMXSharedShell.navigate('/t/legacy-13000'), true);
  assert.strictEqual(ctx.sandbox.MMXSharedShell.navigate('/n/native-13'), true);
  // exact paths only: this is never authorization by path prefix
  assert.strictEqual(ctx.sandbox.MMXSharedShell.navigate('/t/legacy-1'), true); // interior of the range
  assert.strictEqual(ctx.sandbox.MMXSharedShell.navigate('/t/legacy-13000/extra'), false);
  assert.strictEqual(ctx.sandbox.MMXSharedShell.navigate('/t/legacy-20000'), false);
  assert.strictEqual(ctx.sandbox.MMXSharedShell.navigate('/t/'), false);
  assert.strictEqual(ctx.sandbox.MMXSharedShell.navigate('/n/native-14'), false);
  assert.strictEqual(ctx.sandbox.MMXSharedShell.navigate('/n/native-99'), false);
});

test('catalog rejects over-bound totals, duplicates and collisions', () => {
  const atBound = [];
  for (let i = 0; i < 49986; i++) atBound.push('/b/' + i);
  const b1 = harness();
  b1.activate({ canonicalPath: '/b/0', catalog: { legacyPaths: atBound, nativePaths: ['/n/a', '/n/b'] } });
  assert.strictEqual(b1.api().active, true); // 49986 + 14 <= 50000

  const over = [];
  for (let i = 0; i < 50001; i++) over.push('/o/' + i);
  const b2 = harness();
  b2.activate({ canonicalPath: '/o/0', catalog: { legacyPaths: over, nativePaths: [] } });
  assert.strictEqual(b2.api().active, false);
  assert.strictEqual(b2.sent.length, 0);

  const overByOne = [];
  for (let i = 0; i < 15; i++) overByOne.push('/n/x-' + i);
  const b3 = harness();
  b3.activate({ canonicalPath: '/b/0', catalog: { legacyPaths: atBound, nativePaths: overByOne } });
  assert.strictEqual(b3.api().active, false); // 49986 + 15 > 50000
  assert.strictEqual(b3.sent.length, 0);

  const b4 = harness(); // duplicate inside one list
  b4.activate({ catalog: { legacyPaths: ['/tools', '/tools'], nativePaths: [] } });
  assert.strictEqual(b4.api().active, false);
  const b5 = harness(); // legacy/native collision
  b5.activate({ catalog: { legacyPaths: ['/tools'], nativePaths: ['/tools'] } });
  assert.strictEqual(b5.api().active, false);
  const b6 = harness(); // no unbounded growth: array length is bounded before parsing
  const huge = { legacyPaths: [], nativePaths: [] };
  huge.legacyPaths.length = 60000;
  b6.activate({ catalog: huge });
  assert.strictEqual(b6.api().active, false);
});

/* ---- FIX 2: transport strip/restore keeps every non-reserved query byte ---- */
test('transport pairs never reserialize non-reserved query bytes', () => {
  const incoming = 'https://www.mastermind-x.com/tools?q=A%20B&mmx_shell=1&set=1,2&mmx_generation=g1&set=3%2c4&plus=A+B#part';
  const preserved = 'https://www.mastermind-x.com/tools?' + BYTES + '#part';
  const ctx = harness({ childUrl: incoming });
  ctx.activate();
  // READY projection
  assert.strictEqual(ctx.lastOf('READY').href, preserved);
  // history projection (child replace keeps bytes, appends only the two reserved pairs)
  ctx.sandbox.history.replaceState({}, '', '/tools?' + BYTES + '#part');
  const rep = ctx.replaceCalls[ctx.replaceCalls.length - 1];
  assert.strictEqual(rep.url, 'https://www.mastermind-x.com/tools?' + BYTES + '&mmx_shell=1&mmx_generation=g1#part');
  assert.strictEqual(ctx.lastOf('NAVIGATE').href, 'https://www.mastermind-x.com/tools?' + BYTES + '#part');
  // API projection
  assert.strictEqual(ctx.sandbox.MMXSharedShell.navigate('/all-tools?' + BYTES + '#part'), true);
  assert.strictEqual(ctx.lastOf('NAVIGATE').href, 'https://www.mastermind-x.com/all-tools?' + BYTES + '#part');
  // anchor projection
  const link = ctx.mkEl('a', { href: '/pricing?' + BYTES + '#part' });
  ctx.mutateAdd(link);
  assert.strictEqual(link.getAttribute('href'), PROD + '/pricing?' + BYTES + '#part');
  // nothing was form-urlencoded into + / %2C
  const transcript = JSON.stringify(ctx.sent.map((s) => s.msg));
  assert.ok(transcript.indexOf('%2C') === -1);
  assert.ok(transcript.indexOf('q=A+B') === -1);
  assert.ok(transcript.indexOf('set=3%2C4') === -1);
  assert.ok(transcript.indexOf(BYTES) !== -1);
});

/* ---- FIX 3: fragment navigation belongs to the parent ---- */
test('fragment anchor click: view first, child replace only, parent push', () => {
  const ctx = harness();
  ctx.activate();
  const frag = ctx.mkEl('a', { href: '#frag' });
  ctx.mkEl('div', { id: 'frag' });
  ctx.mutateAdd(frag);
  const mark = ctx.seq.length;
  const navs = ctx.activeCount('NAVIGATE');
  const ev = ctx.click(frag);
  assert.strictEqual(ev.defaultPrevented, true);
  const order = ctx.tail(mark);
  assert.deepStrictEqual(order, ['MSG:VIEW_STATE', 'REPLACE', 'SCROLL:frag', 'MSG:NAVIGATE']);
  const nav = ctx.lastOf('NAVIGATE');
  assert.strictEqual(nav.href, 'https://www.mastermind-x.com/tools?q=alpha#frag');
  assert.strictEqual(nav.mode, 'push'); // Back can return from the fragment
  assert.strictEqual(nav.sameDocument, true);
  assert.strictEqual(ctx.activeCount('NAVIGATE'), navs + 1);
  assert.strictEqual(ctx.pushCalls.length, 0);
  assert.strictEqual(ctx.replaceCalls.length, 1);
  assert.strictEqual(ctx.replaceCalls[0].state.marker, 'original'); // child state preserved
  assert.ok(ctx.replaceCalls[0].url.indexOf('mmx_generation=g1') !== -1);
});

test('already-current fragment scrolls without fabricating a parent entry', () => {
  const ctx = harness();
  ctx.activate();
  const same = ctx.mkEl('a', { href: '#top' }); // location already ends with #top
  ctx.mkEl('div', { id: 'top' });
  ctx.mutateAdd(same);
  const mark = ctx.seq.length;
  const navs = ctx.activeCount('NAVIGATE');
  const views = ctx.activeCount('VIEW_STATE');
  const replaces = ctx.replaceCalls.length;
  const ev = ctx.click(same);
  assert.strictEqual(ev.defaultPrevented, true);
  assert.deepStrictEqual(ctx.tail(mark), ['SCROLL:top']);
  assert.strictEqual(ctx.activeCount('NAVIGATE'), navs);
  assert.strictEqual(ctx.activeCount('VIEW_STATE'), views);
  assert.strictEqual(ctx.replaceCalls.length, replaces);
});

test('API navigate of a fragment: child replace only, caller mode preserved', () => {
  const ctx = harness();
  ctx.activate();
  ctx.mkEl('div', { id: 'frag' });
  ctx.mkEl('div', { id: 'other' });
  const mark = ctx.seq.length;
  assert.strictEqual(ctx.sandbox.MMXSharedShell.navigate('#frag', 'push'), true);
  assert.deepStrictEqual(ctx.tail(mark), ['MSG:VIEW_STATE', 'REPLACE', 'SCROLL:frag', 'MSG:NAVIGATE']);
  let nav = ctx.lastOf('NAVIGATE');
  assert.strictEqual(nav.mode, 'push');
  assert.strictEqual(nav.sameDocument, true);
  assert.strictEqual(nav.href, 'https://www.mastermind-x.com/tools?q=alpha#frag');
  assert.strictEqual(ctx.pushCalls.length, 0);
  const mark2 = ctx.seq.length;
  assert.strictEqual(ctx.sandbox.MMXSharedShell.navigate('#other', 'replace'), true);
  assert.deepStrictEqual(ctx.tail(mark2), ['MSG:VIEW_STATE', 'REPLACE', 'SCROLL:other', 'MSG:NAVIGATE']);
  nav = ctx.lastOf('NAVIGATE');
  assert.strictEqual(nav.mode, 'replace'); // actual caller mode preserved
  assert.strictEqual(nav.sameDocument, true);
  // whole-document target keeps sameDocument false
  assert.strictEqual(ctx.sandbox.MMXSharedShell.navigate('/pricing'), true);
  nav = ctx.lastOf('NAVIGATE');
  assert.strictEqual(nav.sameDocument, false);
  assert.strictEqual(nav.mode, 'push');
});

/* ---- FIX 4: first-party anchor handling ---- */
test('internal _blank anchors project to the parent href and keep native new-tab clicks', () => {
  const ctx = harness();
  ctx.activate();
  const nb = ctx.mkEl('a', { href: '/pricing', target: '_blank' });
  ctx.mutateAdd(nb);
  assert.strictEqual(nb.getAttribute('href'), PROD + '/pricing');
  assert.strictEqual(nb.getAttribute('rel'), null); // first-party new tab needs no rel rewrite
  const before = ctx.sent.length;
  const ev = ctx.click(nb);
  assert.strictEqual(ev.defaultPrevented, false);
  assert.strictEqual(ctx.sent.length, before); // normal new-tab click is never intercepted
  // an invalid internal _blank target stays child-native and unprojected
  const bad = ctx.mkEl('a', { href: '/secret', target: '_blank' });
  ctx.mutateAdd(bad);
  assert.strictEqual(bad.getAttribute('href'), '/secret');
  assert.strictEqual(ctx.click(bad).defaultPrevented, false);
  assert.strictEqual(ctx.sent.length, before);
  // dead schemes and downloads stay native
  const js = ctx.mkEl('a', { href: 'javascript:void(0)' });
  ctx.mutateAdd(js);
  assert.strictEqual(ctx.click(js).defaultPrevented, false);
  assert.strictEqual(ctx.sent.length, before);
});

test('explicit parent-origin targets are first-party and map back for classification', () => {
  const ctx = harness();
  ctx.activate();
  // an already-projected href fed to navigate() must not return false
  assert.strictEqual(ctx.sandbox.MMXSharedShell.navigate(PROD + '/pricing'), true);
  assert.strictEqual(ctx.lastOf('NAVIGATE').href, 'https://www.mastermind-x.com/pricing');
  assert.strictEqual(ctx.sandbox.MMXSharedShell.navigate(PROD + '/all-tools?' + BYTES + '#part'), true);
  assert.strictEqual(ctx.lastOf('NAVIGATE').href, 'https://www.mastermind-x.com/all-tools?' + BYTES + '#part');
  const back = ctx.mkEl('a', { href: PROD + '/pricing' });
  ctx.mutateAdd(back);
  assert.strictEqual(back.getAttribute('href'), PROD + '/pricing'); // normalized, still projected
  const ev = ctx.click(back);
  assert.strictEqual(ev.defaultPrevented, true);
  assert.strictEqual(ctx.lastOf('NAVIGATE').href, 'https://www.mastermind-x.com/pricing');
  // unadmitted parent path is refused as internal, not treated as external
  assert.strictEqual(ctx.sandbox.MMXSharedShell.navigate(PROD + '/tools-extra'), false);
  assert.strictEqual(ctx.lastOf('ERROR').code, 'navigation_unavailable');
  // arbitrary external origins are never internal
  assert.strictEqual(ctx.sandbox.MMXSharedShell.navigate('https://evil.example/pricing'), false);
  assert.strictEqual(ctx.sandbox.MMXSharedShell.navigate('https://beta.mastermind-x.com@evil.example/pricing'), false);
  assert.strictEqual(ctx.sandbox.MMXSharedShell.navigate(PROD.replace('https://', 'https://u@p:') + '/pricing'), false);
});

test('noopener is added without dropping existing rel tokens', () => {
  const ctx = harness();
  ctx.activate();
  const a1 = ctx.mkEl('a', { href: 'https://external.example/x', rel: 'noreferrer' });
  const a2 = ctx.mkEl('a', { href: 'https://external.example/y', rel: 'noopener noreferrer' });
  const a3 = ctx.mkEl('a', { href: 'https://external.example/z', rel: 'NOOPENER' });
  [a1, a2, a3].forEach((el) => ctx.mutateAdd(el));
  assert.strictEqual(a1.getAttribute('target'), '_blank');
  assert.strictEqual(a1.getAttribute('rel'), 'noreferrer noopener');
  assert.strictEqual(a2.getAttribute('rel'), 'noopener noreferrer');
  assert.strictEqual(a3.getAttribute('rel'), 'NOOPENER');
});

test('parent-origin hrefs never become a default _self frame navigation', () => {
  const ctx = harness();
  ctx.activate();
  // explicit _self: never rewritten to a parent-origin href, but the click is still driven by the bridge
  const selfish = ctx.mkEl('a', { href: PROD + '/pricing', target: '_self' });
  ctx.mutateAdd(selfish);
  assert.strictEqual(selfish.getAttribute('href'), PROD + '/pricing');
  const ev = ctx.click(selfish);
  assert.strictEqual(ev.defaultPrevented, true);
  assert.strictEqual(ctx.lastOf('NAVIGATE').href, 'https://www.mastermind-x.com/pricing');
  // explicit _self on a child path is now projected too: copying or opening that
  // anchor in a new tab must land on the beta shell, never the legacy origin.
  const childSelf = ctx.mkEl('a', { href: '/all-tools', target: '_self' });
  ctx.mutateAdd(childSelf);
  assert.strictEqual(childSelf.getAttribute('href'), PROD + '/all-tools');
  const selfNav = ctx.activeCount('NAVIGATE');
  assert.strictEqual(ctx.click(childSelf).defaultPrevented, true); // still bridge-driven
  assert.strictEqual(ctx.lastOf('NAVIGATE').href, 'https://www.mastermind-x.com/all-tools');
  assert.strictEqual(ctx.activeCount('NAVIGATE'), selfNav + 1);
  // role=button with a child href keeps native semantics; with a parent href it is intercepted
  const roleChild = ctx.mkEl('a', { href: '/pricing', role: 'button' });
  ctx.mutateAdd(roleChild);
  assert.strictEqual(roleChild.getAttribute('href'), '/pricing');
  assert.strictEqual(ctx.click(roleChild).defaultPrevented, false);
  const roleParent = ctx.mkEl('a', { href: PROD + '/all-tools', role: 'button' });
  ctx.mutateAdd(roleParent);
  assert.strictEqual(ctx.click(roleParent).defaultPrevented, true);
  assert.strictEqual(ctx.lastOf('NAVIGATE').href, 'https://www.mastermind-x.com/all-tools');
});

/* ---- FIX 5: readiness/context race ---- */
test('newer CONTEXT after the initial READY is acknowledged without restoring', () => {
  const ctx = harness();
  ctx.mkEl('div', { id: 'mk' });
  ctx.activate({ restore: { x: 0, y: 800, focusId: 'mk' } });
  assert.strictEqual(ctx.activeCount('READY'), 1);
  assert.ok(ctx.calls.scrollTo.some((s) => s.x === 0 && s.y === 800));
  assert.strictEqual(ctx.calls.focus.length, 1);
  const focuses = ctx.calls.focus.length;
  const scrolls = ctx.calls.scrollTo.length;
  const replaces = ctx.replaceCalls.length;
  ctx.dispatchMessage(ctx.contextMsg({ theme: 'light', contextRevision: 4 }));
  assert.strictEqual(ctx.activeCount('READY'), 2);
  const ack = ctx.lastOf('READY');
  assert.deepStrictEqual(Object.keys(ack).sort(), ENV3.concat(READY_FIELDS).sort());
  assert.strictEqual(ack.contextRevision, 4); // the revision the parent actually applied
  assert.strictEqual(ack.bridgeVersion, '20261018.1');
  assert.strictEqual(ack.documentVersion, '20261018.1');
  assert.strictEqual(ack.href, 'https://www.mastermind-x.com/tools?q=alpha#top');
  assert.strictEqual(ctx.calls.focus.length, focuses); // context updates never steal focus
  assert.strictEqual(ctx.calls.scrollTo.length, scrolls); // no repeated restoration
  assert.strictEqual(ctx.replaceCalls.length, replaces); // no child history churn
  assert.strictEqual(ctx.docEl.getAttribute('data-theme'), 'light');
  // stale, invalid and malformed contexts are never acknowledged
  const ready = ctx.activeCount('READY');
  ctx.dispatchMessage(ctx.contextMsg({ theme: 'light', contextRevision: 4 }));
  ctx.dispatchMessage(ctx.contextMsg({ theme: 'neo', contextRevision: 5 }));
  ctx.dispatchMessage(ctx.contextMsg({ contextRevision: 6, evil: 1 }));
  ctx.dispatchMessage(ctx.contextMsg({ theme: 'dark', locale: 'de', contextRevision: 7 }));
  assert.strictEqual(ctx.activeCount('READY'), ready);
  assert.strictEqual(ctx.lastOf('ERROR').code, 'unsupported_context');
  assert.strictEqual(ctx.docEl.getAttribute('data-theme'), 'light'); // 5/7 not adopted
  ctx.dispatchMessage(ctx.contextMsg({ theme: 'dark', contextRevision: 5 }));
  assert.strictEqual(ctx.activeCount('READY'), ready + 1); // still live after refusals
});

test('CONTEXT newer than an unsent initial READY yields exactly one READY', () => {
  const ctx = harness({ ready: 'loading' });
  ctx.mkEl('div', { id: 'mk' });
  ctx.activate({ restore: { x: 0, y: 640, focusId: 'mk' } });
  assert.strictEqual(ctx.activeCount('READY'), 0);
  ctx.dispatchMessage(ctx.contextMsg({ theme: 'light', contextRevision: 4 }));
  assert.strictEqual(ctx.activeCount('READY'), 0); // no duplicate ack while the first is pending
  assert.strictEqual(ctx.docL.DOMContentLoaded.length, 1); // one ready listener, no re-registration
  ctx.doc.readyState = 'interactive';
  ctx.fireDoc('DOMContentLoaded');
  assert.strictEqual(ctx.activeCount('READY'), 1);
  assert.strictEqual(ctx.lastOf('READY').contextRevision, 4); // actual applied revision
  assert.ok(ctx.calls.scrollTo.some((s) => s.x === 0 && s.y === 640)); // restored exactly once
  assert.strictEqual(ctx.calls.focus.length, 1);
  ctx.dispatchMessage(ctx.contextMsg({ theme: 'dark', contextRevision: 5 }));
  assert.strictEqual(ctx.activeCount('READY'), 2);
  assert.strictEqual(ctx.calls.focus.length, 1); // no second restoration
});

test('repeated trusted INIT is idempotent and path-validated', () => {
  const ctx = harness();
  ctx.sandbox.MMXSharedShell.navigate('/tools?q=beta');
  ctx.sandbox.MMXSharedShell.navigate('/pricing');
  assert.strictEqual(ctx.sent.length, 0);
  ctx.activate();
  assert.strictEqual(ctx.activeCount('NAVIGATE'), 2);
  assert.strictEqual(ctx.activeCount('READY'), 1);
  const observers = ctx.docEl.__observers.length;
  const styles = ctx.styles.length;
  const clicks = ctx.docL.click.length;
  const scrolls = ctx.winL.scroll.length;
  const readyListeners = (ctx.docL.DOMContentLoaded || []).length;
  const focuses = ctx.calls.focus.length;
  const replaces = ctx.replaceCalls.length;
  ctx.dispatchMessage(ctx.initMsg()); // identical trusted INIT
  assert.strictEqual(ctx.docEl.__observers.length, observers); // no new observers
  assert.strictEqual(ctx.styles.length, styles); // chrome suppression not re-applied
  assert.strictEqual(ctx.docL.click.length, clicks);
  assert.strictEqual(ctx.winL.scroll.length, scrolls);
  assert.strictEqual((ctx.docL.DOMContentLoaded || []).length, readyListeners);
  assert.strictEqual(ctx.calls.focus.length, focuses); // no repeated restoration
  assert.strictEqual(ctx.replaceCalls.length, replaces);
  assert.strictEqual(ctx.activeCount('NAVIGATE'), 2); // no queue replay
  assert.strictEqual(ctx.api().active, true);
  assert.strictEqual(ctx.activeCount('READY'), 2); // context acknowledged
  assert.strictEqual(ctx.lastOf('READY').contextRevision, 3);
  // a different requested canonical path is not acknowledged
  ctx.dispatchMessage(ctx.initMsg({ canonicalPath: '/dashboard' }));
  assert.strictEqual(ctx.activeCount('READY'), 2);
  // malformed repeats have no effect
  ctx.dispatchMessage(ctx.initMsg({ evil: 1 }));
  ctx.dispatchMessage(ctx.initMsg({ theme: 'neo' }));
  ctx.dispatchMessage(ctx.initMsg({ catalog: { legacyPaths: ['/tools'], nativePaths: ['/tools'] } }));
  assert.strictEqual(ctx.activeCount('READY'), 2);
  assert.strictEqual(ctx.api().active, true);
  assert.strictEqual(ctx.sandbox.MMXSharedShell.navigate('/all-tools'), true);
});

/* ---- FIX 6: incumbent setters ---- */
test('setters run even when the attributes already equal the request', () => {
  const seen = { theme: [], lang: [] };
  const ctx = harness();
  ctx.sandbox.setTheme = (v) => seen.theme.push(v);
  ctx.sandbox.setLang = (v) => seen.lang.push(v);
  ctx.docEl.setAttribute('data-theme', 'dark'); // already the requested values
  ctx.docEl.setAttribute('lang', 'en');
  ctx.activate();
  assert.deepStrictEqual(seen.theme, ['dark']);
  assert.deepStrictEqual(seen.lang, ['en']);
  assert.strictEqual(ctx.lastOf('READY').contextRevision, 3);
  ctx.dispatchMessage(ctx.contextMsg({ theme: 'dark', locale: 'en', contextRevision: 4 }));
  assert.deepStrictEqual(seen.theme, ['dark', 'dark']); // setter still refreshes charts/strings
  assert.deepStrictEqual(seen.lang, ['en', 'en']);
});

test('a throwing incumbent setter surfaces failure instead of READY', () => {
  const boom = () => { throw new Error('chart refresh failed'); };
  const init = harness();
  init.sandbox.setTheme = boom;
  init.activate();
  assert.strictEqual(init.api().active, false);
  assert.strictEqual(init.activeCount('READY'), 0);
  assert.strictEqual(init.lastOf('ERROR').code, 'initialization_failed');
  assert.strictEqual(init.docEl.getAttribute('data-mmx-shared-shell'), null); // no chrome claimed

  let throwing = true;
  const live = harness();
  live.sandbox.setTheme = () => { if (throwing) { throw new Error('chart refresh failed'); } };
  live.activate();
  const ready = live.activeCount('READY');
  assert.strictEqual(ready, 0);
  assert.strictEqual(live.lastOf('ERROR').code, 'initialization_failed');
  throwing = false;
  live.activate(); // INIT retried once the incumbent setter works
  const ready2 = live.activeCount('READY');
  assert.strictEqual(ready2, 1);
  throwing = true;
  live.dispatchMessage(live.contextMsg({ theme: 'light', contextRevision: 4 }));
  assert.strictEqual(live.activeCount('READY'), ready2); // never acknowledged
  assert.strictEqual(live.lastOf('ERROR').code, 'unsupported_context');
  throwing = false;
  live.dispatchMessage(live.contextMsg({ theme: 'light', contextRevision: 5 }));
  assert.strictEqual(live.activeCount('READY'), ready2 + 1); // recovers with a newer revision

  const late = harness({ ready: 'loading' });
  late.activate(); // no setter yet -> pending
  late.sandbox.setLang = boom;
  late.doc.readyState = 'interactive';
  late.fireDoc('DOMContentLoaded');
  assert.strictEqual(late.activeCount('READY'), 0);
  assert.strictEqual(late.lastOf('ERROR').code, 'initialization_failed');
});

/* ---- FIX 7: closed message contract on the wire ---- */
test('outbound messages match the host contract and never carry auth payloads', () => {
  const ALLOWED = {
    READY: READY_FIELDS,
    NAVIGATE: ['href', 'mode', 'sameDocument', 'requestId'],
    VIEW_STATE: ['view'],
    AUTH_REQUEST: ['intent'],
    CONTEXT_REQUEST: ['theme', 'locale'],
    ERROR: ['code'],
  };
  const REQUIRED = {
    READY: READY_FIELDS,
    NAVIGATE: ['href', 'mode', 'sameDocument', 'requestId'],
    VIEW_STATE: ['view'],
    AUTH_REQUEST: ['intent'],
    CONTEXT_REQUEST: [],
    ERROR: ['code'],
  };
  const ctx = harness();
  ctx.sandbox.history.pushState({}, '', '/tools?access_token=SECRETVALUE');
  const auth = ctx.mkEl('a', { href: '/auth?code=SECRETVALUE&onboard=1' });
  const ok = ctx.mkEl('a', { href: '/pricing' });
  ctx.activate();
  ctx.mutateAdd(auth);
  ctx.mutateAdd(ok);
  const ev = ctx.click(auth);
  assert.strictEqual(ev.defaultPrevented, true);
  ctx.click(ok);
  ctx.sandbox.MMXSharedShell.navigate('/dashboard');
  ctx.docEl.setAttribute('data-theme', 'light');
  ctx.fireDoc('themechange');
  ctx.sandbox.scrollY = 12;
  ctx.fireWin('scroll');
  // exact source / origin / generation only
  const before = ctx.sent.length;
  ctx.dispatchMessage(ctx.contextMsg({ contextRevision: 9 }), { source: {} });
  ctx.dispatchMessage(ctx.contextMsg({ contextRevision: 9 }), { origin: 'https://evil.example' });
  ctx.dispatchMessage(Object.assign(ctx.contextMsg({ contextRevision: 9 }), { frameGeneration: 'other' }));
  assert.strictEqual(ctx.sent.length, before);
  for (const item of ctx.sent) {
    const msg = item.msg;
    assert.strictEqual(msg.protocol, 'mmx.shared-shell.v1');
    assert.strictEqual(msg.frameGeneration, 'g1');
    assert.ok(ALLOWED[msg.type], 'closed kind: ' + msg.type);
    assert.strictEqual(item.to, PROD);
    // own required envelope fields present, unexpected keys absent
    const actual = Object.keys(msg).sort();
    ENV3.forEach((k) => assert.ok(actual.indexOf(k) !== -1, 'missing envelope key ' + k));
    assert.ok(actual.every((k) => ENV3.concat(ALLOWED[msg.type]).indexOf(k) !== -1), 'unexpected key in ' + msg.type);
    REQUIRED[msg.type].forEach((k) => assert.ok(actual.indexOf(k) !== -1, 'missing own field ' + k));
    if (msg.type === 'CONTEXT_REQUEST') assert.ok(actual.indexOf('theme') !== -1 || actual.indexOf('locale') !== -1);
    assert.strictEqual(msg.type === 'NAVIGATE' ? ['push', 'replace'].indexOf(msg.mode) !== -1 : true, true);
    if (typeof msg.href === 'string') {
      assert.ok(/https:\/\/(www\.mastermind-x\.com|beta\.mastermind-x\.com)\//.test(msg.href));
      assert.strictEqual(msg.href.indexOf('/auth'), -1);
      assert.strictEqual(msg.href.indexOf('access_token'), -1);
      assert.strictEqual(msg.href.indexOf('mmx_'), -1);
    }
  }
  const transcript = JSON.stringify(ctx.sent.map((s) => s.msg));
  assert.strictEqual(transcript.indexOf('SECRETVALUE'), -1);
  assert.strictEqual(transcript.indexOf('access_token'), -1);
  assert.strictEqual(transcript.indexOf('code_verifier'), -1);
  assert.strictEqual(ctx.activeCount('NAVIGATE'), 2); // auth link produced no navigation
  assert.ok(ctx.sent.some((s) => s.msg.type === 'ERROR' && s.msg.code === 'authentication_navigation'));
  assert.strictEqual(ctx.pushCalls.length, 0);
  assert.strictEqual(ctx.sandbox.history.state.marker, 'original'); // child state preserved
});


test('response classification distinguishes actual gate and product documents', () => {
  assert.strictEqual(harness().activate().lastOf('READY').responseKind, 'content');
  assert.strictEqual(harness({ responseKind: 'coming_soon' }).activate().lastOf('READY').responseKind, 'coming_soon');
  for (const responseKind of [null, '', 'approved', 'login_required']) {
    const ctx = harness({ responseKind }).activate();
    assert.strictEqual(ctx.lastOf('READY'), null);
    assert.strictEqual(ctx.lastOf('ERROR').code, 'initialization_failed');
  }
});

test('presentation application is visible to incumbent owners only while setters run', () => {
  const ctx = harness();
  const seen = [];
  ctx.sandbox.setTheme = () => seen.push(ctx.api().applyingContext);
  ctx.sandbox.setLang = () => seen.push(ctx.api().applyingContext);
  assert.strictEqual(ctx.api().applyingContext, false);
  ctx.activate();
  assert.deepStrictEqual(seen, [true, true]);
  assert.strictEqual(ctx.api().applyingContext, false);
  ctx.sandbox.setTheme = () => { throw new Error('setter'); };
  ctx.dispatchMessage(ctx.contextMsg());
  assert.strictEqual(ctx.api().applyingContext, false);
  assert.strictEqual(ctx.lastOf('ERROR').code, 'unsupported_context');
});

/* ================= FINAL REPAIR 1: first apply is visible before activation ====== */
test('the first context application is observable before activation and never after', () => {
  const seen = [];
  const ctx = harness();
  ctx.sandbox.setTheme = () => seen.push({ applying: ctx.api().applyingContext, active: ctx.api().active });
  ctx.sandbox.setLang = () => seen.push({ applying: ctx.api().applyingContext, active: ctx.api().active });
  assert.strictEqual(ctx.api().applyingContext, false);
  ctx.activate();
  // INIT applies the parent context while state.active is still false. The getter is
  // independent of activation, so an incumbent owner never mistakes the application
  // for a deliberate user edit, and the state safety (no sends before activation)
  // stays exactly where it was.
  assert.deepStrictEqual(seen, [{ applying: true, active: false }, { applying: true, active: false }]);
  assert.strictEqual(ctx.api().active, true);
  assert.strictEqual(ctx.api().applyingContext, false);
  ctx.dispatchMessage(ctx.contextMsg({ theme: 'light', contextRevision: 4 }));
  assert.deepStrictEqual(seen[2], { applying: true, active: true });
  assert.strictEqual(ctx.api().applyingContext, false);
});

/* ============== FINAL REPAIR 2: real boot overwrite + DOM-ready restoration ====== */
test('legacy boot theme/lang overwrite is restored at DOM ready and never echoed', () => {
  const ctx = harness({ ready: 'loading' });
  const seen = incumbent(ctx);
  ctx.mkEl('div', { id: 'mk' });
  ctx.activate({ restore: { x: 0, y: 900, focusId: 'mk' } });
  assert.deepStrictEqual(seen.theme, ['dark']);
  assert.deepStrictEqual(seen.lang, ['en']);
  // the legacy boot rewrites presentation after the head INIT, before DOMContentLoaded
  ctx.docEl.setAttribute('data-theme', 'light');
  ctx.docEl.setAttribute('data-lang', 'zh');
  ctx.docEl.setAttribute('lang', 'zh-CN');
  ctx.fireDoc('themechange');
  ctx.fireDoc('langchange');
  assert.strictEqual(ctx.activeCount('CONTEXT_REQUEST'), 0); // boot writes are not user choices
  assert.strictEqual(ctx.activeCount('READY'), 0);           // nothing claimed while unproved
  assert.strictEqual(ctx.docL.DOMContentLoaded.length, 1);
  ctx.doc.readyState = 'interactive';
  ctx.fireDoc('DOMContentLoaded');
  assert.strictEqual(ctx.activeCount('READY'), 1);
  assert.deepStrictEqual(seen.theme, ['dark', 'dark']); // unconditional reapply through the setter
  assert.deepStrictEqual(seen.lang, ['en', 'en']);
  assert.strictEqual(ctx.docEl.getAttribute('data-theme'), 'dark');
  assert.strictEqual(ctx.docEl.getAttribute('data-lang'), 'en');
  assert.strictEqual(ctx.docEl.getAttribute('lang'), 'en');
  assert.strictEqual(ctx.lastOf('READY').contextRevision, 3);
  assert.strictEqual(ctx.activeCount('CONTEXT_REQUEST'), 0); // restoration never echoes
  assert.strictEqual(ctx.docEl.__observers.length, 1);       // one anchor observer
  assert.strictEqual(ctx.styles.length, 0);                  // static stylesheet; no runtime injection
  assert.strictEqual(ctx.calls.focus.length, 1);             // restored exactly once
  assert.ok(ctx.calls.scrollTo.some((s) => s.x === 0 && s.y === 900));
});

test('a parent CONTEXT received during loading wins the DOM-ready restoration', () => {
  const ctx = harness({ ready: 'loading' });
  const seen = incumbent(ctx);
  ctx.mkEl('div', { id: 'mk' });
  ctx.activate({ restore: { x: 0, y: 640, focusId: 'mk' } });
  ctx.dispatchMessage(ctx.contextMsg({ theme: 'light', locale: 'zh', contextRevision: 4 }));
  // the boot then drags presentation the other way; the parent stays authoritative
  ctx.docEl.setAttribute('data-theme', 'dark');
  ctx.docEl.setAttribute('data-lang', 'en');
  ctx.docEl.setAttribute('lang', 'en');
  ctx.fireDoc('themechange');
  ctx.fireDoc('langchange');
  assert.strictEqual(ctx.activeCount('CONTEXT_REQUEST'), 0);
  assert.strictEqual(ctx.activeCount('READY'), 0);
  assert.strictEqual(ctx.docL.DOMContentLoaded.length, 1); // no re-registration per CONTEXT
  ctx.doc.readyState = 'interactive';
  ctx.fireDoc('DOMContentLoaded');
  assert.strictEqual(ctx.activeCount('READY'), 1);         // latest desired revision only
  assert.strictEqual(ctx.lastOf('READY').contextRevision, 4);
  assert.strictEqual(ctx.docEl.getAttribute('data-theme'), 'light');
  assert.strictEqual(ctx.docEl.getAttribute('data-lang'), 'zh');
  assert.strictEqual(ctx.docEl.getAttribute('lang'), 'zh-CN');
  assert.deepStrictEqual(seen.theme, ['dark', 'light', 'light']);
  assert.deepStrictEqual(seen.lang, ['en', 'zh', 'zh']);
  assert.ok(ctx.calls.scrollTo.some((s) => s.x === 0 && s.y === 640));
  assert.strictEqual(ctx.calls.focus.length, 1);
  assert.strictEqual(ctx.replaceCalls.length, 0);          // no child history churn
  assert.strictEqual(ctx.docL.DOMContentLoaded.length, 0); // single listener, now removed
});

test('a boot-window INIT repeated while loading still restores exactly once', () => {
  const ctx = harness({ ready: 'loading' });
  const seen = incumbent(ctx);
  ctx.mkEl('div', { id: 'mk' });
  ctx.activate({ restore: { x: 0, y: 300, focusId: 'mk' } });
  ctx.dispatchMessage(ctx.initMsg()); // identical trusted INIT while still loading
  assert.strictEqual(ctx.docL.DOMContentLoaded.length, 1); // no second ready listener
  assert.strictEqual(ctx.docEl.__observers.length, 1);     // no duplicate observer
  assert.strictEqual(ctx.styles.length, 0);                // static stylesheet; no runtime injection
  assert.strictEqual(ctx.activeCount('READY'), 0);
  ctx.doc.readyState = 'interactive';
  ctx.fireDoc('DOMContentLoaded');
  assert.strictEqual(ctx.activeCount('READY'), 1);
  assert.strictEqual(ctx.calls.focus.length, 1);           // one restoration
  assert.strictEqual(seen.theme.length, 3);                // INIT + repeat + restoration
  assert.strictEqual(seen.lang.length, 3);
  assert.strictEqual(ctx.activeCount('CONTEXT_REQUEST'), 0);
});

test('a throwing setter at DOM-ready restoration is an explicit initialization failure', () => {
  const ctx = harness({ ready: 'loading' });
  ctx.sandbox.setTheme = (v) => ctx.docEl.setAttribute('data-theme', v);
  ctx.sandbox.setLang = (v) => {
    ctx.docEl.setAttribute('data-lang', v);
    ctx.docEl.setAttribute('lang', v === 'zh' ? 'zh-CN' : 'en');
  };
  ctx.mkEl('div', { id: 'mk' });
  ctx.activate({ restore: { x: 0, y: 700, focusId: 'mk' } });
  assert.strictEqual(ctx.activeCount('READY'), 0);
  ctx.docEl.setAttribute('data-theme', 'light'); // boot overwrite
  ctx.sandbox.setTheme = () => { throw new Error('chart refresh failed'); };
  ctx.doc.readyState = 'interactive';
  ctx.fireDoc('DOMContentLoaded');
  assert.strictEqual(ctx.activeCount('READY'), 0);  // never a false READY
  assert.strictEqual(ctx.activeCount('ERROR'), 1);
  assert.strictEqual(ctx.lastOf('ERROR').code, 'initialization_failed');
  assert.strictEqual(ctx.calls.focus.length, 0);    // no restoration on a failed boot
  assert.ok(!ctx.calls.scrollTo.some((s) => s.y === 700));
  assert.strictEqual(ctx.docEl.__observers.length, 1); // and no retry re-observation
});

test('an incumbent setter that overrides the parent presentation blocks READY', () => {
  const ctx = harness();
  ctx.sandbox.setTheme = (v) => ctx.docEl.setAttribute('data-theme', v === 'dark' ? 'light' : 'dark');
  ctx.activate();
  assert.strictEqual(ctx.activeCount('READY'), 0);
  assert.strictEqual(ctx.lastOf('ERROR').code, 'initialization_failed');
  assert.strictEqual(ctx.docEl.getAttribute('data-theme'), 'light'); // the override is what we saw
  ctx.dispatchMessage(ctx.contextMsg({ theme: 'light', contextRevision: 4 }));
  assert.strictEqual(ctx.activeCount('READY'), 0); // the broken setter still overrides the request
  assert.strictEqual(ctx.lastOf('ERROR').code, 'unsupported_context');
  ctx.sandbox.setTheme = (v) => ctx.docEl.setAttribute('data-theme', v);
  ctx.dispatchMessage(ctx.contextMsg({ theme: 'light', contextRevision: 5 }));
  assert.strictEqual(ctx.activeCount('READY'), 1); // a compliant setter permits a proved recovery
});

/* ================ FINAL REPAIR 3: incumbent locale convention ================== */
test('locale read-back prefers data-lang and normalizes the zh-CN html.lang', () => {
  const ctx = harness();
  ctx.activate();
  const base = ctx.activeCount('CONTEXT_REQUEST');
  // a convention the bridge cannot normalize is never invented onto the wire
  ctx.docEl.setAttribute('data-lang', 'fr');
  ctx.docEl.setAttribute('lang', 'fr-FR');
  ctx.fireDoc('langchange');
  assert.strictEqual(ctx.activeCount('CONTEXT_REQUEST'), base);
  // the incumbent semantic key wins even against a stale html.lang
  ctx.docEl.setAttribute('data-lang', 'zh');
  ctx.docEl.setAttribute('lang', 'en');
  ctx.fireDoc('langchange');
  assert.strictEqual(ctx.lastOf('CONTEXT_REQUEST').locale, 'zh');
  // with no data-lang at all the WCAG html.lang form still maps back to the wire zh
  ctx.docEl.removeAttribute('data-lang');
  ctx.docEl.setAttribute('lang', 'zh-CN');
  ctx.fireDoc('langchange');
  assert.strictEqual(ctx.lastOf('CONTEXT_REQUEST').locale, 'zh');
  // and the same fallback for the other side of the closed vocabulary
  ctx.docEl.setAttribute('lang', 'en-US');
  ctx.fireDoc('langchange');
  assert.strictEqual(ctx.lastOf('CONTEXT_REQUEST').locale, 'en');
  const msgs = ctx.sent.slice(base).filter((s) => s.msg.type === 'CONTEXT_REQUEST');
  assert.strictEqual(msgs.length, 3);
  msgs.forEach((item) => {
    assert.deepStrictEqual(Object.keys(item.msg).sort(), ENV3.concat(['locale']).sort());
    assert.ok(['en', 'zh'].indexOf(item.msg.locale) !== -1);
  });
});

test('a genuine post-readiness zh choice survives data-lang/zh-CN and round-trips', () => {
  const ctx = harness();
  const seen = incumbent(ctx);
  ctx.activate();
  assert.strictEqual(ctx.activeCount('CONTEXT_REQUEST'), 0); // boot/application never echoes
  ctx.sandbox.setLang('zh');                                  // the user clicks the toggle
  const msg = ctx.lastOf('CONTEXT_REQUEST');
  assert.deepStrictEqual(Object.keys(msg).sort(), ENV3.concat(['locale']).sort());
  assert.strictEqual(msg.locale, 'zh');                       // not lost to lang="zh-CN"
  assert.strictEqual(ctx.activeCount('CONTEXT_REQUEST'), 1);
  ctx.dispatchMessage(ctx.contextMsg({ locale: 'zh', contextRevision: 4 }));
  assert.strictEqual(ctx.lastOf('READY').contextRevision, 4); // proved, no false mismatch
  assert.strictEqual(ctx.docEl.getAttribute('data-lang'), 'zh');
  assert.strictEqual(ctx.docEl.getAttribute('lang'), 'zh-CN');
  assert.deepStrictEqual(seen.lang, ['en', 'zh', 'zh']);
  assert.strictEqual(ctx.activeCount('CONTEXT_REQUEST'), 1);   // the parent apply is suppressed
});

/* ============== FINAL REPAIR 4: admitted first-party target semantics ========== */
test('_self, _parent and named targets are projected while default handling is kept', () => {
  const ctx = harness();
  ctx.activate();
  const self = ctx.mkEl('a', { href: '/pricing', target: '_self' });
  const parentT = ctx.mkEl('a', { href: '/dashboard?x=1', target: '_parent' });
  const named = ctx.mkEl('a', { href: '/all-tools', target: 'panel' });
  [self, parentT, named].forEach((el) => ctx.mutateAdd(el));
  assert.strictEqual(self.getAttribute('href'), PROD + '/pricing');
  assert.strictEqual(parentT.getAttribute('href'), PROD + '/dashboard?x=1');
  assert.strictEqual(named.getAttribute('href'), PROD + '/all-tools');
  assert.strictEqual(self.getAttribute('target'), '_self');    // authored target kept
  assert.strictEqual(parentT.getAttribute('target'), '_parent');
  assert.strictEqual(named.getAttribute('target'), 'panel');
  const replaces = ctx.replaceCalls.length;
  const ev = ctx.click(self);
  assert.strictEqual(ev.defaultPrevented, true);               // default stays bridge-driven
  assert.strictEqual(ctx.lastOf('NAVIGATE').href, 'https://www.mastermind-x.com/pricing');
  assert.strictEqual(ctx.lastOf('NAVIGATE').mode, 'push');
  assert.strictEqual(ctx.replaceCalls.length, replaces);       // no child history churn
  const before = ctx.sent.length;
  assert.strictEqual(ctx.click(parentT, { metaKey: true }).defaultPrevented, false); // native, beta
  ctx.mutateAttr(self, 'href');                                // re-observation is a no-op
  ctx.mutateAttr(parentT, 'href');
  assert.strictEqual(self.getAttribute('href'), PROD + '/pricing');
  assert.strictEqual(parentT.getAttribute('href'), PROD + '/dashboard?x=1');
  assert.strictEqual(ctx.sent.length, before);                 // no observer feedback
  const ext = ctx.mkEl('a', { href: 'https://external.example/y', target: '_self' });
  const dl = ctx.mkEl('a', { href: '/pricing', target: '_self', download: '' });
  const btn = ctx.mkEl('a', { href: '/pricing', target: '_self', role: 'button' });
  [ext, dl, btn].forEach((el) => ctx.mutateAdd(el));
  assert.strictEqual(ext.getAttribute('href'), 'https://external.example/y'); // external kept
  assert.strictEqual(dl.getAttribute('href'), '/pricing');                     // download kept
  assert.strictEqual(btn.getAttribute('href'), '/pricing');                    // authored button kept
  assert.strictEqual(ctx.click(btn).defaultPrevented, false);
  assert.strictEqual(ctx.sent.length, before);
});

test('an unregistered href rewrite is reclassified instead of navigating a stale target', () => {
  const ctx = harness();
  ctx.activate();
  const link = ctx.mkEl('a', { href: '/pricing', target: '_self' });
  ctx.mutateAdd(link);
  assert.strictEqual(link.getAttribute('href'), PROD + '/pricing');
  link.setAttribute('href', PROD + '/dashboard'); // the incumbent moves the same node
  ctx.mutateAttr(link, 'href');
  assert.strictEqual(link.getAttribute('href'), PROD + '/dashboard'); // re-projected, still beta
  const ev = ctx.click(link);
  assert.strictEqual(ev.defaultPrevented, true);
  assert.strictEqual(ctx.lastOf('NAVIGATE').href, 'https://www.mastermind-x.com/dashboard');
  const navs = ctx.activeCount('NAVIGATE');
  link.setAttribute('href', '/secret');           // then to something unadmitted
  ctx.mutateAttr(link, 'href');
  assert.strictEqual(link.getAttribute('href'), '/secret'); // recovery leaves the authored value
  const errs = ctx.activeCount('ERROR');
  const ev2 = ctx.click(link);
  assert.strictEqual(ev2.defaultPrevented, true);
  assert.strictEqual(ctx.activeCount('ERROR'), errs + 1);
  assert.strictEqual(ctx.lastOf('ERROR').code, 'navigation_unavailable');
  assert.strictEqual(ctx.activeCount('NAVIGATE'), navs); // the stale /dashboard was never used
});


// Real browser readiness distinguishes parser completion from deferred-script completion.
test('interactive parser state waits for deferred legacy boot before initial READY', () => {
  const ctx = harness({ ready: 'interactive' });
  const seen = incumbent(ctx);
  ctx.activate();
  assert.strictEqual(ctx.activeCount('READY'), 0);
  ctx.dispatchMessage(ctx.contextMsg({ theme: 'light', locale: 'zh', contextRevision: 4 }));
  ctx.sandbox.setTheme('dark');
  ctx.sandbox.setLang('en');
  assert.strictEqual(ctx.activeCount('CONTEXT_REQUEST'), 0);
  assert.strictEqual(ctx.activeCount('READY'), 0);
  ctx.fireDoc('DOMContentLoaded');
  assert.strictEqual(ctx.activeCount('READY'), 1);
  assert.strictEqual(ctx.lastOf('READY').contextRevision, 4);
  assert.strictEqual(ctx.docEl.getAttribute('data-theme'), 'light');
  assert.strictEqual(ctx.docEl.getAttribute('data-lang'), 'zh');
  assert.strictEqual(ctx.docEl.getAttribute('lang'), 'zh-CN');
  assert.strictEqual(seen.theme.at(-1), 'light');
  assert.strictEqual(seen.lang.at(-1), 'zh');
});

test('bootstrap observes DOMContentLoaded before a delayed INIT while images still load', () => {
  const ctx = harness({ ready: 'loading' });
  const seen = incumbent(ctx);
  assert.strictEqual((ctx.docL.DOMContentLoaded || []).length, 1);
  ctx.doc.readyState = 'interactive';
  ctx.fireDoc('DOMContentLoaded');
  ctx.activate();
  assert.strictEqual(ctx.activeCount('READY'), 1);
  assert.strictEqual((ctx.docL.DOMContentLoaded || []).length, 0);
  assert.deepStrictEqual(seen.theme, ['dark']);
  assert.deepStrictEqual(seen.lang, ['en']);
});

test('queued initial fragment callbacks cannot publish boot preferences to the parent', () => {
  const ctx = harness();
  incumbent(ctx);
  let callbacks = 0;
  const target = ctx.mkEl('div', { id: 'queued-section' });
  target.scrollIntoView = () => {
    callbacks += 1;
    ctx.sandbox.setTheme('light');
    ctx.sandbox.setLang('zh');
  };
  assert.strictEqual(ctx.api().navigate('#queued-section'), true);
  ctx.activate();
  assert.strictEqual(callbacks, 1, 'the actual queued fragment callback must run');
  assert.strictEqual(ctx.activeCount('CONTEXT_REQUEST'), 0);
  assert.strictEqual(ctx.activeCount('READY'), 1);
  assert.strictEqual(ctx.activeCount('ERROR'), 0);
  assert.strictEqual(ctx.docEl.getAttribute('data-theme'), 'dark');
  assert.strictEqual(ctx.docEl.getAttribute('data-lang'), 'en');
  assert.strictEqual(ctx.docEl.getAttribute('lang'), 'en');
});

test('correct semantic locale cannot conceal a wrong html language at readiness', () => {
  const ctx = harness();
  ctx.sandbox.setLang = (v) => {
    ctx.docEl.setAttribute('data-lang', v);
    ctx.docEl.setAttribute('lang', 'zh-CN');
  };
  ctx.activate();
  assert.strictEqual(ctx.activeCount('READY'), 0);
  assert.strictEqual(ctx.lastOf('ERROR').code, 'initialization_failed');
});


function acceptLocation(ctx, nav, canonicalPath, extra) {
  ctx.dispatchMessage(Object.assign({ protocol: 'mmx.shared-shell.v1', frameGeneration: 'g1',
    type: 'LOCATION_ACCEPTED', requestId: nav.requestId, canonicalPath }, extra || {}));
}
test('accepted fragment updates reach actual window page subscribers exactly once', () => {
  const ctx = harness();
  ctx.activate();
  let observed = 0, nativeHashEvents = 0;
  ctx.sandbox.addEventListener('mmx:shell-location', () => { observed += 1; });
  ctx.sandbox.addEventListener('hashchange', () => { nativeHashEvents += 1; });
  ctx.api().navigate('#accepted');
  const nav = ctx.lastOf('NAVIGATE');
  assert.strictEqual(observed, 0, 'parent acceptance owns the notification');
  acceptLocation(ctx, nav, '/tools?q=alpha#wrong');
  acceptLocation(ctx, nav, '/tools?q=alpha#accepted', { requestId: 'other' });
  assert.strictEqual(observed, 0);
  acceptLocation(ctx, nav, '/tools?q=alpha#accepted');
  assert.strictEqual(observed, 1);
  acceptLocation(ctx, nav, '/tools?q=alpha#accepted');
  assert.strictEqual(observed, 1, 'duplicate acknowledgments are inert');
  assert.strictEqual(nativeHashEvents, 0, 'native hashchange semantics stay unchanged');
});

test('accepted location subscriber may replace current history without an event loop', () => {
  const ctx = harness();
  ctx.activate();
  let observed = 0;
  ctx.sandbox.addEventListener('mmx:shell-location', () => {
    observed += 1;
    ctx.sandbox.history.replaceState({ local: true }, '', ctx.location().href);
  });
  ctx.api().navigate('#tab');
  acceptLocation(ctx, ctx.lastOf('NAVIGATE'), '/tools?q=alpha#tab');
  assert.strictEqual(observed, 1);
  for (let i = 0; i < 3; i++) acceptLocation(ctx, ctx.lastOf('NAVIGATE'), '/tools?q=alpha#tab');
  assert.strictEqual(observed, 1);
  assert.ok(ctx.activeCount('NAVIGATE') <= 2, 'repeated same-value notifications cannot recurse');
  assert.strictEqual(ctx.activeCount('ERROR'), 0);
});

test('superseded same-document acknowledgments cannot notify a stale page location', () => {
  const ctx = harness();
  ctx.activate();
  const observed = [];
  ctx.sandbox.addEventListener('mmx:shell-location', () => observed.push(ctx.location().hash));
  ctx.api().navigate('#one');
  const first = ctx.lastOf('NAVIGATE');
  ctx.api().navigate('#two');
  const latest = ctx.lastOf('NAVIGATE');
  acceptLocation(ctx, first, '/tools?q=alpha#one');
  assert.deepStrictEqual(observed, []);
  acceptLocation(ctx, latest, '/tools?q=alpha#two');
  assert.deepStrictEqual(observed, ['#two']);
});

test('pathname-changing history routes through the parent without altering the child document', () => {
  for (const mode of ['push', 'replace']) {
    const ctx = harness().activate();
    const before = ctx.location().href;
    const from = ctx.seq.length;
    ctx.sandbox.history[mode + 'State']({ local: true }, '', '/dashboard?q=A%20B#details');
    assert.strictEqual(ctx.location().href, before);
    assert.strictEqual(ctx.replaceCalls.length, 0);
    assert.strictEqual(ctx.pushCalls.length, 0);
    assert.strictEqual(ctx.lastOf('NAVIGATE').sameDocument, false);
    assert.strictEqual(ctx.lastOf('NAVIGATE').mode, mode);
    assert.strictEqual(ctx.lastOf('NAVIGATE').href, 'https://www.mastermind-x.com/dashboard?q=A%20B#details');
    assert.deepStrictEqual(ctx.tail(from), ['MSG:VIEW_STATE', 'MSG:NAVIGATE']);
  }
});

test('pre-INIT pathname-changing history stays put and drains as document navigation', () => {
  for (const mode of ['push', 'replace']) {
    const ctx = harness();
    const before = ctx.location().href;
    ctx.sandbox.history[mode + 'State']({ local: true }, '', '/dashboard?q=beta#details');
    assert.strictEqual(ctx.location().href, before);
    assert.strictEqual(ctx.replaceCalls.length, 0);
    assert.strictEqual(ctx.pushCalls.length, 0);
    assert.strictEqual(ctx.sent.length, 0);
    ctx.activate();
    assert.strictEqual(ctx.lastOf('NAVIGATE').sameDocument, false);
    assert.strictEqual(ctx.lastOf('NAVIGATE').mode, mode);
    assert.strictEqual(ctx.lastOf('NAVIGATE').href, 'https://www.mastermind-x.com/dashboard?q=beta#details');
  }
});

test('same-path history preserves local state and raw query bytes while parent owns entries', () => {
  for (const mode of ['push', 'replace']) {
    const ctx = harness().activate();
    const from = ctx.seq.length;
    ctx.sandbox.history[mode + 'State']({ local: true }, '', '/tools?' + BYTES + '#details');
    assert.strictEqual(ctx.replaceCalls.length, 1);
    assert.strictEqual(ctx.replaceCalls[0].state.local, true);
    assert.strictEqual(ctx.pushCalls.length, 0);
    assert.strictEqual(ctx.lastOf('NAVIGATE').sameDocument, true);
    assert.strictEqual(ctx.lastOf('NAVIGATE').mode, mode);
    assert.strictEqual(ctx.lastOf('NAVIGATE').href, 'https://www.mastermind-x.com/tools?' + BYTES + '#details');
    assert.deepStrictEqual(ctx.tail(from), ['MSG:VIEW_STATE', 'REPLACE', 'MSG:NAVIGATE']);
  }
});

test('a full pre-INIT queue cannot mutate an unreported history location', () => {
  const ctx = harness();
  for (let i = 0; i < 8; i++) assert.strictEqual(ctx.api().navigate('/dashboard?q=' + i), true);
  const before = ctx.location().href;
  ctx.sandbox.history.replaceState({}, '', '/tools?q=unreported');
  assert.strictEqual(ctx.location().href, before);
  assert.strictEqual(ctx.replaceCalls.length, 0);
  ctx.activate();
  assert.strictEqual(ctx.activeCount('NAVIGATE'), 8);
});

test('direct authentication fragments never enter API navigation messages', () => {
  const fragments = ['access_token=FRAGMENT_SECRET', 'refresh_token=FRAGMENT_SECRET',
    'token_hash=FRAGMENT_SECRET', 'id_token=FRAGMENT_SECRET', 'code_verifier=FRAGMENT_SECRET',
    'authorization=FRAGMENT_SECRET', 'AcCeSs_ToKeN=FRAGMENT_SECRET', '%61ccess_token=FRAGMENT_SECRET',
    'type=recovery&access_token=FRAGMENT_SECRET', 'pane?access_token=FRAGMENT_SECRET'];
  for (const fragment of fragments) {
    const ctx = harness().activate();
    assert.strictEqual(ctx.api().navigate('/tools#' + fragment), false, fragment);
    assert.strictEqual(ctx.activeCount('NAVIGATE'), 0, fragment);
    assert.strictEqual(ctx.lastOf('ERROR').code, 'authentication_navigation', fragment);
    assert.ok(!JSON.stringify(ctx.sent).includes('FRAGMENT_SECRET'), fragment);
  }
});

test('direct authentication fragments never mutate history before or after INIT', () => {
  for (const active of [false, true]) {
    for (const mode of ['push', 'replace']) {
      const ctx = harness();
      if (active) ctx.activate();
      const before = ctx.location().href;
      ctx.sandbox.history[mode + 'State']({}, '', '/tools#access_token=HISTORY_SECRET');
      assert.strictEqual(ctx.location().href, before);
      assert.strictEqual(ctx.replaceCalls.length, 0);
      assert.strictEqual(ctx.pushCalls.length, 0);
      if (!active) ctx.activate();
      assert.strictEqual(ctx.activeCount('NAVIGATE'), 0);
      assert.strictEqual(ctx.lastOf('ERROR').code, 'authentication_navigation');
      assert.ok(!JSON.stringify(ctx.sent).includes('HISTORY_SECRET'));
    }
  }
});

test('direct authentication-fragment anchor activation is claimed without leaking the URL', () => {
  const ctx = harness().activate();
  const anchor = ctx.mkEl('a', { href: '/tools#access_token=ANCHOR_SECRET' });
  ctx.mutateAdd(anchor);
  assert.strictEqual(ctx.click(anchor).defaultPrevented, true);
  assert.strictEqual(ctx.activeCount('NAVIGATE'), 0);
  assert.strictEqual(ctx.lastOf('ERROR').code, 'authentication_navigation');
  assert.ok(!JSON.stringify(ctx.sent).includes('ANCHOR_SECRET'));
});

test('post-readiness context never acknowledges a setter that leaves the presentation wrong', () => {
  for (const broken of ['theme', 'data-lang', 'lang']) {
    const ctx = harness();
    incumbent(ctx);
    ctx.activate();
    assert.strictEqual(ctx.activeCount('READY'), 1);
    if (broken === 'theme') ctx.sandbox.setTheme = () => ctx.docEl.setAttribute('data-theme', 'dark');
    else ctx.sandbox.setLang = () => ctx.docEl.setAttribute(broken, 'en');
    ctx.dispatchMessage(ctx.contextMsg({ theme: 'light', locale: 'zh', contextRevision: 4 }));
    assert.strictEqual(ctx.activeCount('READY'), 1, broken);
    assert.strictEqual(ctx.lastOf('ERROR').code, 'unsupported_context', broken);
  }
});

test('repeated INIT cannot falsely acknowledge a broken incumbent setter', () => {
  const ctx = harness();
  incumbent(ctx);
  ctx.activate();
  ctx.sandbox.setTheme = () => ctx.docEl.setAttribute('data-theme', 'dark');
  ctx.dispatchMessage(ctx.initMsg({ theme: 'light', contextRevision: 4 }));
  assert.strictEqual(ctx.activeCount('READY'), 1);
  assert.strictEqual(ctx.lastOf('ERROR').code, 'unsupported_context');
});

test('authentication material in the initial child URL never enters READY', () => {
  for (const suffix of ['&access_token=INITIAL_SECRET', '#access_token=INITIAL_SECRET',
    '#pane?access_token=INITIAL_SECRET']) {
    const ctx = harness({ childUrl: 'https://www.mastermind-x.com/tools?mmx_shell=1&mmx_generation=g1' + suffix });
    ctx.activate();
    assert.strictEqual(ctx.activeCount('READY'), 0, suffix);
    assert.strictEqual(ctx.lastOf('ERROR').code, 'initialization_failed', suffix);
    assert.ok(!JSON.stringify(ctx.sent).includes('INITIAL_SECRET'), suffix);
  }
});

test('persisted pagehide preserves the bridge for restored browser documents', () => {
  const ctx = harness().activate();
  const api = ctx.api();
  const wrappedHistory = ctx.sandbox.history.replaceState;
  const observers = ctx.docEl.__observers.length;
  ctx.fireWin('pagehide', { persisted: true });
  ctx.fireWin('pageshow', { persisted: true });
  assert.strictEqual(ctx.api(), api);
  assert.strictEqual(ctx.api().active, true);
  assert.strictEqual(ctx.winL.message.length, 1);
  assert.strictEqual(ctx.sandbox.history.replaceState, wrappedHistory);
  ctx.dispatchMessage(ctx.initMsg({ contextRevision: 4 }));
  assert.strictEqual(ctx.lastOf('READY').contextRevision, 4);
  assert.strictEqual(ctx.docEl.__observers.length, observers);
  assert.strictEqual(ctx.api().navigate('/dashboard'), true);
  assert.strictEqual(ctx.lastOf('NAVIGATE').sameDocument, false);
});

test('credential-bearing history URLs never mutate or enter the protocol', () => {
  for (const active of [false, true]) {
    const ctx = harness();
    if (active) ctx.activate();
    const before = ctx.location().href;
    ctx.sandbox.history.replaceState({}, '', 'https://synthetic-user:synthetic-pass@www.mastermind-x.com/tools#panel');
    assert.strictEqual(ctx.location().href, before);
    assert.strictEqual(ctx.replaceCalls.length, 0);
    if (!active) ctx.activate();
    assert.strictEqual(ctx.activeCount('NAVIGATE'), 0);
    assert.ok(!JSON.stringify(ctx.sent).includes('synthetic-pass'));
  }
});

// The public application joins the existing beta origin; it does not admit arbitrary parents.
test('app production parent earns the same exact READY handshake as beta', () => {
  const parent = 'https://app.mastermind-x.com';
  const ctx = harness({parent, referrer: parent + '/tools/calculators/cagr.html'});
  ctx.activate();
  assert.strictEqual(ctx.api().active, true);
  assert.ok(ctx.lastOf('READY'));
  assert.ok(ctx.sent.every(row => row.to === parent));
});
for (const parent of ['https://app.mastermind-x.com.evil.example', 'http://app.mastermind-x.com',
  'https://www.mastermind-x.com', 'https://evil.example']) {
  test('unapproved parent remains inert: ' + parent, () => {
    const ctx = harness({parent, referrer: parent + '/'});
    assert.strictEqual(ctx.sandbox.MMXSharedShell, undefined);
    assert.strictEqual(ctx.sent.length, 0);
  });
}
