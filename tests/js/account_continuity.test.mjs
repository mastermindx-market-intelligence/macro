// tests/js/account_continuity.test.mjs — site-20 bundle S1 (templates/account.js)
//
// Runs the REAL templates/account.js inside a node:vm context over a small fake
// DOM, fake timers and a hand-driven fetch, then drives it the way the macro
// page does (theme.js defines window.MDXAuth, so account.js mounts in macro
// mode and theme.js calls window.MMAccount.open()).  Every response is
// answered explicitly by the test, so ordering races are deterministic.
//
//   node --test tests/js/account_continuity.test.mjs
//   ACCOUNT_JS_PATH=/path/to/preimage.js node --test tests/js/account_continuity.test.mjs
//
// The ACCOUNT_JS_PATH override exists only to prove the regressions red on the
// pre-fix source; CI always runs against templates/account.js.
// All accounts below are fictional (example.test).
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import vm from 'node:vm';

process.env.TZ = 'UTC';
const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const SRC_PATH = process.env.ACCOUNT_JS_PATH || join(ROOT, 'templates', 'account.js');
const SRC = readFileSync(SRC_PATH, 'utf8');
const API_BASE = 'https://api.example.test';

// ------------------------------------------------------------ fake DOM ----
const VOID = new Set(['input', 'br', 'img', 'hr', 'meta', 'link', 'path', 'circle', 'rect',
  'line', 'polyline', 'polygon', 'source', 'use', 'ellipse']);
function unescapeHTML(s) {
  return String(s).replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'").replace(/&amp;/g, '&');
}
function escapeHTML(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

class TextNode {
  constructor(data, doc) { this.nodeType = 3; this.data = String(data); this.parentNode = null; this.ownerDocument = doc; }
  get textContent() { return this.data; }
  set textContent(v) { this.data = String(v); }
}

class ClassList {
  constructor(el) { this.el = el; }
  _get() { return (this.el.getAttribute('class') || '').split(/\s+/).filter(Boolean); }
  _set(a) { this.el.setAttribute('class', a.join(' ')); }
  contains(c) { return this._get().includes(c); }
  add(...cs) { const a = this._get(); for (const c of cs) if (!a.includes(c)) a.push(c); this._set(a); }
  remove(...cs) { this._set(this._get().filter((x) => !cs.includes(x))); }
  toggle(c, force) {
    const has = this.contains(c);
    const want = force === undefined ? !has : !!force;
    if (want && !has) this.add(c);
    if (!want && has) this.remove(c);
    return want;
  }
}

function addListener(target, type, fn, opts) {
  const capture = opts === true || !!(opts && typeof opts === 'object' && opts.capture);
  if (!target._ls.some((l) => l.type === type && l.fn === fn && l.capture === capture)) {
    target._ls.push({ type, fn, capture });
  }
}
function removeListener(target, type, fn, opts) {
  const capture = opts === true || !!(opts && typeof opts === 'object' && opts.capture);
  target._ls = target._ls.filter((l) => !(l.type === type && l.fn === fn && l.capture === capture));
}
function callListeners(node, ev, phase) {
  for (const l of node._ls.slice()) {
    if (l.type !== ev.type) continue;
    if (phase === 'capture' && !l.capture) continue;
    if (phase === 'bubble' && l.capture) continue;
    ev.currentTarget = node;
    l.fn.call(node, ev);
  }
}
// Capture (outermost first) -> target -> bubble (innermost first), stopping on stopPropagation.
function dispatch(target, ev) {
  if (!ev.target) ev.target = target;
  const path = [];
  for (let n = target.parentNode; n; n = n.parentNode) path.push(n);
  for (let i = path.length - 1; i >= 0 && !ev._stopped; i--) callListeners(path[i], ev, 'capture');
  if (!ev._stopped) callListeners(target, ev, 'target');
  if (ev.bubbles !== false) for (let i = 0; i < path.length && !ev._stopped; i++) callListeners(path[i], ev, 'bubble');
  return !ev.defaultPrevented;
}

class El {
  constructor(tag, doc) {
    this.nodeType = 1; this.tagName = String(tag).toUpperCase(); this.ownerDocument = doc;
    this._attrs = new Map(); this.childNodes = []; this.parentNode = null; this._ls = [];
    this.style = {}; this.disabled = false; this.classList = new ClassList(this);
  }
  get nodeName() { return this.tagName; }
  get localName() { return this.tagName.toLowerCase(); }
  get children() { return this.childNodes.filter((n) => n.nodeType === 1); }
  get firstChild() { return this.childNodes[0] || null; }
  get lastChild() { return this.childNodes[this.childNodes.length - 1] || null; }
  get parentElement() { return this.parentNode && this.parentNode.nodeType === 1 ? this.parentNode : null; }
  getAttribute(n) { n = String(n).toLowerCase(); return this._attrs.has(n) ? this._attrs.get(n) : null; }
  setAttribute(n, v) { this._attrs.set(String(n).toLowerCase(), String(v)); }
  removeAttribute(n) { this._attrs.delete(String(n).toLowerCase()); }
  hasAttribute(n) { return this._attrs.has(String(n).toLowerCase()); }
  get id() { return this.getAttribute('id') || ''; }
  set id(v) { this.setAttribute('id', v); }
  get className() { return this.getAttribute('class') || ''; }
  set className(v) { this.setAttribute('class', v); }
  get options() { return this.tagName === 'SELECT' ? this.querySelectorAll('option') : undefined; }
  get value() {
    if (this.tagName === 'SELECT') {
      if (this._value !== undefined) return this._value;
      const opts = this.options;
      const sel = opts.find((o) => o.hasAttribute('selected'));
      return sel ? sel.value : (opts[0] ? opts[0].value : '');
    }
    if (this._value !== undefined) return this._value;
    const v = this.getAttribute('value');
    if (this.tagName === 'OPTION') return v !== null ? v : this.textContent;
    return v === null ? '' : v;
  }
  set value(v) {
    v = String(v);
    if (this.tagName === 'SELECT') { this._value = this.options.some((o) => o.value === v) ? v : ''; return; }
    this._value = v;
  }
  get textContent() {
    return this.childNodes.map((n) => n.textContent).join('');
  }
  set textContent(v) {
    for (const c of this.childNodes) c.parentNode = null;
    this.childNodes = [];
    const s = String(v == null ? '' : v);
    if (s) this.appendChild(new TextNode(s, this.ownerDocument));
  }
  get innerHTML() {
    return this.childNodes.map(serialize).join('');
  }
  set innerHTML(html) {
    for (const c of this.childNodes) c.parentNode = null;
    this.childNodes = [];
    parseInto(this, String(html == null ? '' : html));
  }
  appendChild(node) {
    if (node.parentNode) node.parentNode._removeChild(node);
    node.parentNode = this; this.childNodes.push(node); return node;
  }
  insertBefore(node, ref) {
    if (!ref) return this.appendChild(node);
    if (node.parentNode) node.parentNode._removeChild(node);
    const i = this.childNodes.indexOf(ref);
    node.parentNode = this;
    if (i < 0) this.childNodes.push(node); else this.childNodes.splice(i, 0, node);
    return node;
  }
  removeChild(node) { this._removeChild(node); return node; }
  _removeChild(node) {
    const i = this.childNodes.indexOf(node);
    if (i >= 0) this.childNodes.splice(i, 1);
    node.parentNode = null;
  }
  remove() { if (this.parentNode) this.parentNode._removeChild(this); }
  contains(other) { for (let n = other; n; n = n.parentNode) if (n === this) return true; return false; }
  focus() { this.ownerDocument.activeElement = this; }
  blur() { if (this.ownerDocument.activeElement === this) this.ownerDocument.activeElement = this.ownerDocument.body; }
  click() { dispatch(this, makeEvent('click')); }
  scrollIntoView() {}
  getBoundingClientRect() { return { top: 0, left: 0, right: 0, bottom: 0, width: 0, height: 0 }; }
  addEventListener(type, fn, opts) { addListener(this, type, fn, opts); }
  removeEventListener(type, fn, opts) { removeListener(this, type, fn, opts); }
  dispatchEvent(ev) { return dispatch(this, ev); }
  matches(sel) { return matchesSelector(this, sel); }
  closest(sel) {
    for (let n = this; n && n.nodeType === 1; n = n.parentNode) if (matchesSelector(n, sel)) return n;
    return null;
  }
  _walk(out) {
    for (const c of this.childNodes) if (c.nodeType === 1) { out.push(c); c._walk(out); }
    return out;
  }
  querySelectorAll(sel) { return this._walk([]).filter((n) => matchesSelector(n, sel)); }
  querySelector(sel) { return this.querySelectorAll(sel)[0] || null; }
  getElementsByTagName(t) { t = String(t).toUpperCase(); return this._walk([]).filter((n) => t === '*' || n.tagName === t); }
}

function serialize(n) {
  if (n.nodeType === 3) return escapeHTML(n.data);
  const tag = n.tagName.toLowerCase();
  const attrs = [...n._attrs].map(([k, v]) => ` ${k}="${escapeHTML(v)}"`).join('');
  if (VOID.has(tag)) return `<${tag}${attrs}>`;
  return `<${tag}${attrs}>${n.childNodes.map(serialize).join('')}</${tag}>`;
}

const TOKEN_RE = /<!--[\s\S]*?-->|<(\/?)([a-zA-Z][\w-]*)\b((?:[^>"']|"[^"]*"|'[^']*')*)>|([^<]+)/g;
const ATTR_RE = /([^\s=\/]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+)))?/g;
function parseInto(root, html) {
  const doc = root.ownerDocument;
  const stack = [root];
  let m;
  TOKEN_RE.lastIndex = 0;
  while ((m = TOKEN_RE.exec(html))) {
    const top = stack[stack.length - 1];
    if (m[4] !== undefined) { top.appendChild(new TextNode(unescapeHTML(m[4]), doc)); continue; }
    if (m[2] === undefined) continue; // comment
    const tag = m[2].toLowerCase();
    if (m[1] === '/') {
      for (let i = stack.length - 1; i > 0; i--) {
        if (stack[i].tagName.toLowerCase() === tag) { stack.length = i; break; }
      }
      continue;
    }
    const el = new El(tag, doc);
    const rawAttrs = m[3] || '';
    let a;
    ATTR_RE.lastIndex = 0;
    while ((a = ATTR_RE.exec(rawAttrs))) {
      const val = a[2] !== undefined ? a[2] : a[3] !== undefined ? a[3] : a[4] !== undefined ? a[4] : '';
      el.setAttribute(a[1], unescapeHTML(val));
    }
    top.appendChild(el);
    if (!VOID.has(tag) && !/\/\s*$/.test(rawAttrs)) stack.push(el);
  }
}

// --------------------------------------------------------- selectors ------
function splitTop(s, sepTest) {
  const out = []; let cur = ''; let depth = 0; let q = null;
  for (const ch of s) {
    if (q) { cur += ch; if (ch === q) q = null; continue; }
    if (ch === '"' || ch === "'") { q = ch; cur += ch; continue; }
    if (ch === '[' || ch === '(') depth++;
    if (ch === ']' || ch === ')') depth--;
    if (depth === 0 && sepTest(ch)) { if (cur.trim()) out.push(cur.trim()); cur = ''; continue; }
    cur += ch;
  }
  if (cur.trim()) out.push(cur.trim());
  return out;
}
function parseCompound(s) {
  if (/^[>+~]$/.test(s)) throw new Error('fake DOM: combinator not supported: ' + s);
  const c = { tag: null, id: null, classes: [], attrs: [] };
  let rest = s;
  const tm = /^([a-zA-Z][\w-]*|\*)/.exec(rest);
  if (tm) { c.tag = tm[1] === '*' ? null : tm[1].toUpperCase(); rest = rest.slice(tm[0].length); }
  while (rest) {
    let m;
    if ((m = /^#([\w-]+)/.exec(rest))) { c.id = m[1]; }
    else if ((m = /^\.([\w-]+)/.exec(rest))) { c.classes.push(m[1]); }
    else if ((m = /^\[\s*([\w:-]+)\s*(?:([~^$*|]?=)\s*(?:"([^"]*)"|'([^']*)'|([^\]\s]+)))?\s*\]/.exec(rest))) {
      c.attrs.push({ name: m[1].toLowerCase(), op: m[2] || null, val: m[3] !== undefined ? m[3] : m[4] !== undefined ? m[4] : m[5] });
    } else throw new Error('fake DOM: unsupported selector part: ' + rest + ' in ' + s);
    rest = rest.slice(m[0].length);
  }
  return c;
}
function matchCompound(el, c) {
  if (!el || el.nodeType !== 1) return false;
  if (c.tag && el.tagName !== c.tag) return false;
  if (c.id && el.getAttribute('id') !== c.id) return false;
  for (const k of c.classes) if (!el.classList.contains(k)) return false;
  for (const a of c.attrs) {
    const v = el.getAttribute(a.name);
    if (v === null) return false;
    if (!a.op) continue;
    if (a.op === '=' && v !== a.val) return false;
    if (a.op === '^=' && !v.startsWith(a.val)) return false;
    if (a.op === '$=' && !v.endsWith(a.val)) return false;
    if (a.op === '*=' && !v.includes(a.val)) return false;
    if (a.op === '~=' && !v.split(/\s+/).includes(a.val)) return false;
    if (a.op === '|=' && !(v === a.val || v.startsWith(a.val + '-'))) return false;
  }
  return true;
}
function matchesSelector(el, sel) {
  for (const group of splitTop(sel, (ch) => ch === ',')) {
    const parts = splitTop(group, (ch) => /\s/.test(ch)).map(parseCompound);
    if (!matchCompound(el, parts[parts.length - 1])) continue;
    let node = el.parentNode; let ok = true;
    for (let i = parts.length - 2; i >= 0; i--) {
      while (node && !matchCompound(node, parts[i])) node = node.parentNode;
      if (!node) { ok = false; break; }
      node = node.parentNode;
    }
    if (ok) return true;
  }
  return false;
}

function makeEvent(type, init = {}) {
  return {
    type, bubbles: init.bubbles !== false, detail: init.detail, key: init.key,
    target: null, currentTarget: null, defaultPrevented: false, _stopped: false,
    preventDefault() { this.defaultPrevented = true; },
    stopPropagation() { this._stopped = true; },
    stopImmediatePropagation() { this._stopped = true; },
  };
}

class Doc {
  constructor() {
    this.nodeType = 9; this._ls = []; this.parentNode = null;
    this.readyState = 'complete'; this.cookie = '';
    this.documentElement = new El('html', this);
    this.documentElement.parentNode = this;
    this.documentElement.setAttribute('data-theme', 'dark');
    this.documentElement.setAttribute('data-lang', 'en');
    this.documentElement.appendChild(new El('head', this));
    this.documentElement.appendChild(new El('body', this));
    this.activeElement = this.body;
  }
  get head() { return this.documentElement.children[0]; }
  get body() { return this.documentElement.children[1]; }
  createElement(t) { return new El(t, this); }
  createTextNode(s) { return new TextNode(s, this); }
  getElementById(id) { return this.documentElement._walk([]).find((n) => n.getAttribute('id') === id) || null; }
  querySelectorAll(sel) { return [this.documentElement, ...this.documentElement._walk([])].filter((n) => matchesSelector(n, sel)); }
  querySelector(sel) { return this.querySelectorAll(sel)[0] || null; }
  addEventListener(type, fn, opts) { addListener(this, type, fn, opts); }
  removeEventListener(type, fn, opts) { removeListener(this, type, fn, opts); }
  dispatchEvent(ev) { ev.target = ev.target || this; callListeners(this, ev, 'capture'); callListeners(this, ev, 'bubble'); return !ev.defaultPrevented; }
}

class FakeStorage {
  constructor() { this._m = new Map(); }
  get length() { return this._m.size; }
  key(i) { return [...this._m.keys()][i] ?? null; }
  getItem(k) { return this._m.has(String(k)) ? this._m.get(String(k)) : null; }
  setItem(k, v) { this._m.set(String(k), String(v)); }
  removeItem(k) { this._m.delete(String(k)); }
  clear() { this._m.clear(); }
}

// ------------------------------------------------------------- env --------
export const ACCT_A = Object.freeze({
  authenticated: true, email: 'avery@example.test', name: 'Avery Example', user_id: 'user-a-fictional',
  plan_label: 'Free', providers: ['email'], provider_label: 'Email',
  created_at: '2026-01-02T00:00:00Z', last_sign_in_at: '2026-10-01T00:00:00Z',
});
export const ACCT_B = Object.freeze({
  authenticated: true, email: 'blake@example.test', name: 'Blake Example', user_id: 'user-b-fictional',
  plan_label: 'Free', providers: ['email'], provider_label: 'Email',
  created_at: '2026-02-03T00:00:00Z', last_sign_in_at: '2026-10-02T00:00:00Z',
});
export const PREFS_ON = Object.freeze({
  prefs: {
    alert_email_optin: true, alert_categories: ['holdings_material_change'],
    tz: 'Europe/London', quiet_hours: { start: '22:00', end: '07:00' },
  },
  unset: [],
});

const clone = (x) => (x === undefined ? undefined : JSON.parse(JSON.stringify(x)));

export function makeEnv(opts = {}) {
  const doc = new Doc();
  if (opts.lang) doc.documentElement.setAttribute('data-lang', opts.lang);
  if (opts.theme) doc.documentElement.setAttribute('data-theme', opts.theme);

  // fake timers ------------------------------------------------------------
  let now = 0; let seq = 0;
  const timers = new Map();
  const setTimeoutFake = (fn, ms, ...args) => { const id = ++seq; timers.set(id, { id, at: now + (Number(ms) || 0), fn, args }); return id; };
  const clearTimeoutFake = (id) => { timers.delete(id); };

  // hand-driven fetch -------------------------------------------------------
  const calls = [];
  const fetchFake = (url, init = {}) => new Promise((resolve, reject) => {
    let body;
    if (typeof init.body === 'string') { try { body = JSON.parse(init.body); } catch (e) { body = init.body; } }
    calls.push({
      url: String(url), path: new URL(String(url)).pathname, method: String(init.method || 'GET').toUpperCase(),
      headers: clone(init.headers || {}), body, resolve, reject, done: false,
    });
  });

  // MDXAuth (theme.js) fake ---------------------------------------------------
  const auth = { user: opts.user === undefined ? { id: 'user-a-fictional', email: ACCT_A.email } : opts.user, cbs: [], signOutCalls: 0 };
  const MDXAuth = {
    client: () => Promise.resolve({ auth: { getSession: () => Promise.resolve({ data: { session: { access_token: 'fictional-token' } } }) } }),
    signOut: () => { auth.signOutCalls += 1; return Promise.resolve(); },
    onChange: (cb) => { auth.cbs.push(cb); cb(auth.user, 'INITIAL_SESSION'); },
  };

  const win = {
    document: doc, console,
    location: { hostname: 'localhost', href: 'http://localhost/start.html', reloadCalls: 0, reload() { this.reloadCalls += 1; } },
    navigator: { language: 'en-US', clipboard: { writeText: () => Promise.resolve() } },
    localStorage: new FakeStorage(),
    setTimeout: setTimeoutFake, clearTimeout: clearTimeoutFake,
    setInterval: () => 0, clearInterval: () => {},
    fetch: fetchFake,
    confirm: () => true,
    MM_API: API_BASE,
    __mmNavMarketLoading: true,
    MDXAuth,
    CustomEvent: class { constructor(type, init = {}) { Object.assign(this, makeEvent(type, init)); } },
    Event: class { constructor(type, init = {}) { Object.assign(this, makeEvent(type, init)); } },
  };
  win.window = win; win.self = win; win.globalThis = win;
  win.setTheme = (t) => { doc.documentElement.setAttribute('data-theme', t); doc.dispatchEvent(makeEvent('themechange', { detail: t })); };
  win.setLang = (l) => { doc.documentElement.setAttribute('data-lang', l); doc.dispatchEvent(makeEvent('langchange', { detail: l })); };

  vm.createContext(win);
  vm.runInContext(SRC, win, { filename: SRC_PATH });

  const settle = async () => { for (let i = 0; i < 25; i++) await new Promise((r) => setImmediate(r)); };
  const env = {
    win, doc, calls, auth, settle,
    get now() { return now; },
    async advance(ms) {
      const end = now + ms;
      for (;;) {
        let next = null;
        for (const t of timers.values()) if (t.at <= end && (!next || t.at < next.at || (t.at === next.at && t.id < next.id))) next = t;
        if (!next) break;
        timers.delete(next.id); now = next.at;
        next.fn(...next.args);
        await settle();
      }
      now = end; await settle();
    },
    pending(path, method = 'GET') { return calls.filter((c) => !c.done && c.path === path && c.method === method.toUpperCase()); },
    requests(path, method = 'GET') { return calls.filter((c) => c.path === path && c.method === method.toUpperCase()); },
    posts(path) { return calls.filter((c) => c.path === path && c.method === 'POST'); },
    // status + JSON body; data === undefined simulates a non-JSON body (r.json() rejects)
    respond(call, status, data) {
      assert.ok(call, 'respond(): no such request');
      assert.ok(!call.done, 'respond(): request already answered');
      call.done = true;
      call.resolve({
        ok: status >= 200 && status < 300, status,
        json: () => (data === undefined ? Promise.reject(new SyntaxError('Unexpected token < in JSON')) : Promise.resolve(clone(data))),
      });
    },
    fail(call) { assert.ok(call && !call.done, 'fail(): no pending request'); call.done = true; call.reject(new TypeError('Failed to fetch')); },
    authEvent(evt, user) { auth.user = user; for (const cb of auth.cbs.slice()) cb(user, evt); },
    panel() { return doc.querySelector('.mmacc'); },
    panelText() { const p = doc.querySelector('.mmacc'); return p ? p.textContent : ''; },
    q(sel) { return doc.querySelector(sel); },
    byId(id) { return doc.getElementById(id); },
    click(el) { assert.ok(el, 'click(): element not found'); return dispatch(el, makeEvent('click')); },
    change(el, value) { assert.ok(el, 'change(): element not found'); if (value !== undefined) el.value = value; return dispatch(el, makeEvent('change')); },
    key(el, key) { return dispatch(el || doc.body, makeEvent('keydown', { key })); },
  };
  return env;
}

// Open the panel and answer the account read (+ the alert-prefs read when signed in).
export async function openWith(env, status, acct, prefsResp = { prefs: {}, unset: [] }) {
  env.win.MMAccount.open();
  await env.settle();
  env.respond(env.pending('/api/account')[0], status, acct);
  await env.settle();
  if (status === 200 && acct && acct.authenticated) {
    const pr = env.pending('/api/account/prefs')[0];
    assert.ok(pr, 'signed-in load must read /api/account/prefs');
    env.respond(pr, 200, prefsResp);
    await env.settle();
  }
}
export const openSignedIn = (env, acct = ACCT_A, prefsResp) => openWith(env, 200, acct, prefsResp);
const GUEST_TITLE = 'Access session';

// ===================================================================== tests ==
// Exemplars (keep them). Name every test with its task prefix "S1-0k" so
// `--test-name-pattern "S1-03"` selects one task's set.

test('S1-03 positive: a real anonymous 401 still renders the signed-out flow', async () => {
  const env = makeEnv({ user: null });
  await openWith(env, 401, { detail: 'Not authenticated' });
  assert.ok(env.panelText().includes(GUEST_TITLE), 'anonymous read must render the guest note');
});

test('S1-03 red: a 503 account read is unavailable, never the signed-out flow', async () => {
  const env = makeEnv();
  await openWith(env, 503, { detail: 'Service unavailable' });
  assert.ok(!env.panelText().includes(GUEST_TITLE), '503 rendered the guest flow');
  assert.ok(env.q('[data-act="retry-load"]'), 'unavailable state must offer an explicit retry');
});

test('S1-01 red: rapid theme then lang persists both final values', async () => {
  const env = makeEnv();
  await openSignedIn(env);
  env.win.setTheme('light');
  env.win.setLang('zh');
  await env.advance(1000);
  const posts = env.posts('/api/account/prefs');
  assert.equal(posts.length, 1, 'one coalesced save');
  assert.deepEqual(posts[0].body, { theme: 'light', lang: 'zh' });
});

test('S1-01 positive: hydration from the account does not echo a write', async () => {
  const env = makeEnv();
  await openSignedIn(env, { ...ACCT_A, prefs: { theme: 'light', lang: 'zh' } });
  await env.advance(1000);
  assert.equal(env.doc.documentElement.getAttribute('data-theme'), 'light');
  assert.equal(env.doc.documentElement.getAttribute('data-lang'), 'zh');
  assert.equal(env.posts('/api/account/prefs').length, 0, 'hydration echoed a save');
});

// ------------------------------------------------------------ helpers ------
const UNAVAIL_EN = 'Can’t load your account right now';
const UNAVAIL_ZH = '暂时无法加载你的账户';
const SO_UNKNOWN_EN = 'We couldn’t confirm that your other devices were signed out.';
const SO_UNKNOWN_ZH = '无法确认其他设备已退出登录';
const SAVED_EN = 'Saved';
const TZ_LON = 'Europe/London';
const TZ_NY = 'America/New_York';
const TZ_HK = 'Asia/Hong_Kong';
const SIGNOUT_ALL = '/api/account/signout-everywhere';
const PREFS = '/api/account/prefs';

const saveOk = (prefs) => ({ ok: true, prefs: prefs || {} });
const openPosts = (env, path = PREFS) => env.posts(path).filter((c) => !c.done);
const prefState = (env, key) => { const n = env.q('[data-pref-' + key + ']'); return n ? n.getAttribute('data-pref-' + key) : null; };
const msgText = (env, id) => { const m = env.byId(id); return m ? m.textContent : ''; };
const tzSel = (env) => env.byId('mmacc-tz');
const catBtn = (env, c) => env.q('[data-act="alert-cat"][data-cat="' + c + '"]');
const optinBtn = (env) => env.q('[data-act="alert-optin"]');
const prefsWith = (over) => ({ ok: true, prefs: { ...PREFS_ON.prefs, ...over } });
async function escClose(env) { env.key(null, 'Escape'); await env.settle(); }
async function reopen(env) { env.win.MMAccount.open(); await env.settle(); }

// ===================================================== S1-03 (account read) ==

test('S1-03 red: a network failure on the account read is unavailable, not guest', async () => {
  const env = makeEnv();
  env.win.MMAccount.open(); await env.settle();
  env.fail(env.pending('/api/account')[0]); await env.settle();
  assert.ok(!env.panelText().includes(GUEST_TITLE), 'network failure rendered the guest flow');
  assert.ok(env.q('[data-acct-state="unavailable"]'), 'unavailable state missing');
  assert.ok(env.q('[data-act="retry-load"]'), 'retry missing');
});

test('S1-03 red: a 200 non-JSON account envelope is unavailable, not guest', async () => {
  const env = makeEnv();
  await openWith(env, 200, undefined);
  assert.ok(!env.panelText().includes(GUEST_TITLE), 'non-JSON 200 rendered the guest flow');
  assert.ok(env.q('[data-acct-state="unavailable"]'), 'unavailable state missing');
});

test('S1-03 red: a 200 envelope without a boolean authenticated is unavailable', async () => {
  const env = makeEnv();
  await openWith(env, 200, {});
  assert.ok(!env.panelText().includes(GUEST_TITLE), 'malformed 200 rendered the guest flow');
  assert.ok(env.q('[data-acct-state="unavailable"]'), 'unavailable state missing');
  assert.equal(env.requests(PREFS).length, 0, 'malformed envelope must not read alert prefs');
});

test('S1-03 positive: a 200 {authenticated:false} still renders the signed-out flow', async () => {
  const env = makeEnv({ user: null });
  await openWith(env, 200, { authenticated: false });
  assert.ok(env.panelText().includes(GUEST_TITLE), 'real anonymous 200 must render the guest note');
  assert.equal(env.q('[data-acct-state="unavailable"]'), null);
});

test('S1-03 red: retry after a 503 restores the account without a page reload', async () => {
  const env = makeEnv();
  await openWith(env, 503, { detail: 'Service unavailable' });
  env.click(env.q('[data-act="retry-load"]')); await env.settle();
  const reads = env.pending('/api/account');
  assert.equal(reads.length, 1, 'retry must issue exactly one new account read');
  env.respond(reads[0], 200, ACCT_A); await env.settle();
  env.respond(env.pending(PREFS)[0], 200, { prefs: {}, unset: [] }); await env.settle();
  assert.ok(env.panelText().includes(ACCT_A.email), 'recovered account not rendered');
  assert.equal(env.q('[data-acct-state="unavailable"]'), null);
  assert.equal(env.win.location.reloadCalls, 0, 'recovery must not need a reload');
});

test('S1-03 red: closing (Escape) and reopening after a 503 re-reads the account', async () => {
  const env = makeEnv();
  await openWith(env, 503, { detail: 'Service unavailable' });
  await escClose(env);
  assert.ok(!env.panel().classList.contains('open'), 'Escape must close the panel');
  await reopen(env);
  assert.equal(env.requests('/api/account').length, 2, 'reopen after unavailable must re-read');
});

test('S1-03 red: a late read from an earlier account generation cannot replace newer state', async () => {
  const env = makeEnv();
  env.win.MMAccount.open(); await env.settle();
  env.authEvent('SIGNED_IN', { id: 'user-b-fictional', email: ACCT_B.email }); await env.settle();
  const reads = env.pending('/api/account');
  assert.equal(reads.length, 2, 'an account switch while loading must start a newer read');
  env.respond(reads[1], 200, ACCT_B); await env.settle();
  env.respond(env.pending(PREFS)[0], 200, { prefs: {}, unset: [] }); await env.settle();
  env.respond(reads[0], 200, ACCT_A); await env.settle();
  assert.ok(env.panelText().includes(ACCT_B.email), 'newer account missing');
  assert.ok(!env.panelText().includes(ACCT_A.email), 'late older read replaced the newer account');
  assert.equal(env.requests(PREFS).length, 1, 'late older read must not trigger a prefs read');
});

test('S1-03 positive: a signed-in read renders the account', async () => {
  const env = makeEnv();
  await openSignedIn(env);
  assert.ok(env.panelText().includes(ACCT_A.email));
  assert.equal(env.q('[data-acct-state="unavailable"]'), null);
});

test('S1-03 positive: a same-account SIGNED_IN after load does not re-read', async () => {
  const env = makeEnv();
  await openSignedIn(env);
  env.authEvent('SIGNED_IN', { id: 'user-a-fictional', email: ACCT_A.email }); await env.settle();
  assert.equal(env.requests('/api/account').length, 1);
});

test('S1-03 red: ZH unavailable copy is shown, not the signed-out flow', async () => {
  const env = makeEnv({ lang: 'zh' });
  await openWith(env, 503, { detail: 'Service unavailable' });
  assert.ok(env.panelText().includes(UNAVAIL_ZH), 'ZH unavailable title missing');
  assert.ok(env.panelText().includes('重试'), 'ZH retry missing');
});

test('S1-03 red: EN unavailable copy is shown', async () => {
  const env = makeEnv();
  await openWith(env, 502, { detail: 'Bad gateway' });
  assert.ok(env.panelText().includes(UNAVAIL_EN), 'EN unavailable title missing');
});

// ============================================ S1-01 (theme / lang persistence) ==

test('S1-01 red: rapid lang then theme persists both final values', async () => {
  const env = makeEnv();
  await openSignedIn(env);
  env.win.setLang('zh');
  env.win.setTheme('light');
  await env.advance(1000);
  const posts = env.posts(PREFS);
  assert.equal(posts.length, 1, 'one coalesced save');
  assert.deepEqual(posts[0].body, { lang: 'zh', theme: 'light' });
});

test('S1-01 red: repeated edits to one field keep its last value and the other field', async () => {
  const env = makeEnv();
  await openSignedIn(env);
  env.win.setTheme('light'); env.win.setTheme('dark'); env.win.setTheme('light');
  env.win.setLang('zh');
  await env.advance(1000);
  const posts = env.posts(PREFS);
  assert.equal(posts.length, 1);
  assert.deepEqual(posts[0].body, { theme: 'light', lang: 'zh' });
});

test('S1-01 red: one save in flight at a time; later edits follow the reply', async () => {
  const env = makeEnv();
  await openSignedIn(env);
  env.win.setLang('zh');
  await env.advance(600);
  assert.equal(env.posts(PREFS).length, 1);
  env.win.setTheme('light'); env.win.setTheme('dark');
  await env.advance(1000);
  assert.equal(env.posts(PREFS).length, 1, 'a second save started while the first was in flight');
  assert.equal(prefState(env, 'theme'), 'queued');
  env.respond(env.posts(PREFS)[0], 200, saveOk({ lang: 'zh' })); await env.settle();
  assert.equal(prefState(env, 'lang'), 'acked');
  const posts = env.posts(PREFS);
  assert.equal(posts.length, 2, 'queued edit must be sent after the reply');
  assert.deepEqual(posts[1].body, { theme: 'dark' });
  env.respond(posts[1], 200, saveOk({ theme: 'dark' })); await env.settle();
  assert.equal(prefState(env, 'theme'), 'acked');
});

test('S1-01 red: a rejected save is failed, never acked', async () => {
  const env = makeEnv();
  await openSignedIn(env);
  env.win.setTheme('light');
  await env.advance(600);
  env.respond(env.posts(PREFS)[0], 400, { detail: { field: 'theme', en: 'Bad theme', zh: '主题无效' } }); await env.settle();
  assert.equal(prefState(env, 'theme'), 'failed');
  env.win.setTheme('dark');
  await env.advance(600);
  env.respond(env.posts(PREFS)[1], 200, saveOk({ theme: 'dark' })); await env.settle();
  assert.equal(prefState(env, 'theme'), 'acked');
});

test('S1-01 red: an older failure does not mark a re-queued edit failed', async () => {
  const env = makeEnv();
  await openSignedIn(env);
  env.win.setTheme('light');
  await env.advance(600);
  env.win.setTheme('dark');
  env.respond(env.posts(PREFS)[0], 500, undefined); await env.settle();
  assert.equal(prefState(env, 'theme'), 'queued', 'older failure overwrote the newer queued edit');
  await env.advance(600);
  const posts = env.posts(PREFS);
  assert.equal(posts.length, 2);
  assert.deepEqual(posts[1].body, { theme: 'dark' });
  env.respond(posts[1], 200, saveOk({ theme: 'dark' })); await env.settle();
  assert.equal(prefState(env, 'theme'), 'acked');
});

test('S1-01 red: an account switch before the debounce never sends the old account prefs', async () => {
  const env = makeEnv();
  await openSignedIn(env);
  env.win.setTheme('light');
  env.authEvent('SIGNED_IN', { id: 'user-b-fictional', email: ACCT_B.email }); await env.settle();
  await env.advance(1000);
  assert.equal(env.posts(PREFS).length, 0, 'previous account prefs were sent');
  env.respond(env.pending('/api/account')[0], 200, ACCT_B); await env.settle();
  env.respond(env.pending(PREFS)[0], 200, { prefs: {}, unset: [] }); await env.settle();
  await env.advance(1000);
  assert.equal(env.posts(PREFS).length, 0, 'switch to B echoed or replayed A prefs');
  assert.ok(env.panelText().includes(ACCT_B.email));
});

test('S1-01 red: a sign-out before the debounce drops the pending save', async () => {
  const env = makeEnv();
  await openSignedIn(env);
  env.win.setTheme('light');
  env.authEvent('SIGNED_OUT', null); await env.settle();
  await env.advance(1000);
  assert.equal(env.posts(PREFS).length, 0, 'pending save survived sign-out');
});

test('S1-01 positive: a signed-out theme change is not persisted to an account', async () => {
  const env = makeEnv({ user: null });
  await openWith(env, 401, { detail: 'Not authenticated' });
  env.win.setTheme('light');
  await env.advance(1000);
  assert.equal(env.posts(PREFS).length, 0);
});

test('S1-01 positive: a language change re-renders the open panel in ZH', async () => {
  const env = makeEnv();
  await openSignedIn(env, ACCT_A, PREFS_ON);
  env.win.setLang('zh'); await env.settle();
  assert.ok(env.panelText().includes('你的时区'), 'panel did not re-render in ZH');
  assert.ok(env.panelText().includes(ACCT_A.email));
});

// ================================== S1-02 (notification-preference callbacks) ==

test('S1-02 red: a tz ack stores its own submitted value, not the current control', async () => {
  const env = makeEnv();
  await openSignedIn(env, ACCT_A, PREFS_ON);
  env.change(tzSel(env), TZ_NY);
  await env.advance(600);
  env.change(tzSel(env), TZ_HK);
  await env.advance(600);
  const first = env.posts(PREFS)[0];
  assert.deepEqual(first.body, { tz: TZ_NY });
  env.respond(first, 200, prefsWith({ tz: TZ_NY })); await env.settle();
  assert.equal(tzSel(env).getAttribute('data-prev'), TZ_NY, 'ack recorded a value it never submitted');
  assert.equal(tzSel(env).value, TZ_HK, 'newer edit was overwritten');
  const second = openPosts(env)[0];
  assert.ok(second, 'newer tz must be sent after the older reply');
  assert.deepEqual(second.body, { tz: TZ_HK });
  env.respond(second, 200, prefsWith({ tz: TZ_HK })); await env.settle();
  assert.equal(tzSel(env).getAttribute('data-prev'), TZ_HK);
  assert.equal(tzSel(env).value, TZ_HK);
  assert.equal(msgText(env, 'mmacc-alert-msg'), SAVED_EN);
});

test('S1-02 red: a rejected first tz edit reverts to the hydrated value with the server copy', async () => {
  const env = makeEnv();
  await openSignedIn(env, ACCT_A, PREFS_ON);
  env.change(tzSel(env), TZ_NY);
  await env.advance(600);
  env.respond(env.posts(PREFS)[0], 400, { detail: { field: 'tz', en: 'Bad zone', zh: '时区无效' } }); await env.settle();
  assert.equal(tzSel(env).value, TZ_LON);
  assert.equal(msgText(env, 'mmacc-alert-msg'), 'Bad zone');
});

test('S1-02 red: an older tz failure cannot roll back a newer queued tz', async () => {
  const env = makeEnv();
  await openSignedIn(env, ACCT_A, PREFS_ON);
  env.change(tzSel(env), TZ_NY);
  await env.advance(600);
  env.change(tzSel(env), TZ_HK);
  await env.advance(600);
  env.respond(env.posts(PREFS)[0], 500, undefined); await env.settle();
  assert.equal(tzSel(env).value, TZ_HK, 'older failure rolled back the newer edit');
  assert.equal(msgText(env, 'mmacc-alert-msg'), '', 'older failure reported an error over newer intent');
  const second = openPosts(env)[0];
  assert.ok(second);
  assert.deepEqual(second.body, { tz: TZ_HK });
  env.respond(second, 200, prefsWith({ tz: TZ_HK })); await env.settle();
  assert.equal(tzSel(env).getAttribute('data-prev'), TZ_HK);
  assert.equal(msgText(env, 'mmacc-alert-msg'), SAVED_EN);
});

test('S1-02 red: an older category failure cannot roll back newer category intent', async () => {
  const env = makeEnv();
  await openSignedIn(env, ACCT_A, PREFS_ON);
  env.click(catBtn(env, 'thesis_window'));
  await env.advance(600);
  assert.deepEqual(env.posts(PREFS)[0].body, { alert_categories: ['holdings_material_change', 'thesis_window'] });
  env.click(catBtn(env, 'holdings_material_change'));
  await env.advance(600);
  env.respond(env.posts(PREFS)[0], 500, undefined); await env.settle();
  assert.equal(catBtn(env, 'thesis_window').getAttribute('aria-checked'), 'true', 'newer intent rolled back');
  assert.equal(catBtn(env, 'holdings_material_change').getAttribute('aria-checked'), 'false', 'newer intent rolled back');
  assert.equal(msgText(env, 'mmacc-alert-msg'), '');
  const second = openPosts(env)[0];
  assert.ok(second);
  assert.deepEqual(second.body, { alert_categories: ['thesis_window'] });
  env.respond(second, 200, prefsWith({ alert_categories: ['thesis_window'] })); await env.settle();
  assert.equal(msgText(env, 'mmacc-alert-msg'), SAVED_EN);
});

test('S1-02 positive: a rejected category reverts to the acked set with error copy', async () => {
  const env = makeEnv();
  await openSignedIn(env, ACCT_A, PREFS_ON);
  env.click(catBtn(env, 'thesis_window'));
  await env.advance(600);
  env.respond(env.posts(PREFS)[0], 400, { detail: { field: 'alert_categories', en: 'Bad category', zh: '类别无效' } }); await env.settle();
  assert.equal(catBtn(env, 'thesis_window').getAttribute('aria-checked'), 'false');
  assert.equal(catBtn(env, 'holdings_material_change').getAttribute('aria-checked'), 'true');
  assert.equal(msgText(env, 'mmacc-alert-msg'), 'Bad category');
});

test('S1-02 red: an opt-in ack after close/reopen drives the reopened control and survives reopen', async () => {
  const env = makeEnv();
  await openSignedIn(env, ACCT_A, PREFS_ON);
  env.click(optinBtn(env));
  await env.advance(600);
  assert.deepEqual(env.posts(PREFS)[0].body, { alert_email_optin: false });
  await escClose(env); await reopen(env);
  env.respond(env.posts(PREFS)[0], 200, prefsWith({ alert_email_optin: false })); await env.settle();
  assert.equal(optinBtn(env).getAttribute('aria-checked'), 'false', 'reopened control kept the stale value');
  assert.equal(env.q('.mmacc-alerts').getAttribute('data-on'), 'false');
  await escClose(env); await reopen(env);
  assert.equal(optinBtn(env).getAttribute('aria-checked'), 'false', 'acked opt-out lost on reopen');
});

test('S1-02 positive: a rejected opt-in reverts with the server copy', async () => {
  const env = makeEnv();
  await openSignedIn(env, ACCT_A, PREFS_ON);
  env.click(optinBtn(env));
  await env.advance(600);
  env.respond(env.posts(PREFS)[0], 400, { detail: { field: 'alert_email_optin', en: 'Could not save', zh: '无法保存' } }); await env.settle();
  assert.equal(optinBtn(env).getAttribute('aria-checked'), 'true');
  assert.equal(msgText(env, 'mmacc-alert-msg'), 'Could not save');
});

test('S1-02 red: an older quiet-hours failure cannot roll back newer quiet hours', async () => {
  const env = makeEnv();
  await openSignedIn(env, ACCT_A, PREFS_ON);
  env.change(env.byId('mmacc-qh-start'), '23:00');
  await env.advance(600);
  assert.deepEqual(env.posts(PREFS)[0].body, { quiet_hours: { start: '23:00', end: '07:00' } });
  env.change(env.byId('mmacc-qh-end'), '06:00');
  await env.advance(600);
  env.respond(env.posts(PREFS)[0], 500, undefined); await env.settle();
  assert.equal(env.byId('mmacc-qh-start').value, '23:00', 'older failure rolled back newer start');
  assert.equal(env.byId('mmacc-qh-end').value, '06:00', 'older failure rolled back newer end');
  const second = openPosts(env)[0];
  assert.ok(second);
  assert.deepEqual(second.body, { quiet_hours: { start: '23:00', end: '06:00' } });
  env.respond(second, 200, prefsWith({ quiet_hours: { start: '23:00', end: '06:00' } })); await env.settle();
  assert.equal(env.byId('mmacc-qh-start').getAttribute('data-prev'), '23:00');
  assert.equal(env.byId('mmacc-qh-end').getAttribute('data-prev'), '06:00');
  assert.equal(msgText(env, 'mmacc-alert-msg'), SAVED_EN);
});

test('S1-02 red: a queued alert edit is dropped on an account switch', async () => {
  const env = makeEnv();
  await openSignedIn(env, ACCT_A, PREFS_ON);
  env.change(tzSel(env), TZ_NY);
  env.authEvent('SIGNED_IN', { id: 'user-b-fictional', email: ACCT_B.email }); await env.settle();
  env.respond(env.pending('/api/account')[0], 200, ACCT_B); await env.settle();
  env.respond(env.pending(PREFS)[0], 200, PREFS_ON); await env.settle();
  await env.advance(1000);
  assert.equal(env.posts(PREFS).length, 0, 'previous account tz was sent');
  assert.equal(tzSel(env).value, TZ_LON);
  assert.equal(msgText(env, 'mmacc-alert-msg'), '');
});

test('S1-02 red: an in-flight ack from the previous account cannot touch the new account', async () => {
  const env = makeEnv();
  await openSignedIn(env, ACCT_A, PREFS_ON);
  env.change(tzSel(env), TZ_NY);
  await env.advance(600);
  const aPost = env.posts(PREFS)[0];
  env.authEvent('SIGNED_IN', { id: 'user-b-fictional', email: ACCT_B.email }); await env.settle();
  env.respond(env.pending('/api/account')[0], 200, ACCT_B); await env.settle();
  env.respond(env.pending(PREFS)[0], 200, PREFS_ON); await env.settle();
  env.respond(aPost, 200, prefsWith({ tz: TZ_NY })); await env.settle();
  assert.ok(env.panelText().includes(ACCT_B.email));
  assert.equal(tzSel(env).value, TZ_LON);
  assert.equal(tzSel(env).getAttribute('data-prev'), TZ_LON);
  assert.equal(msgText(env, 'mmacc-alert-msg'), '', 'old account callback wrote into the new panel');
});

test('S1-02 red: a reload hydrates the saved tz as the acked rollback baseline', async () => {
  const env = makeEnv();
  await openSignedIn(env, ACCT_A, prefsWith({ tz: TZ_NY }));
  assert.equal(tzSel(env).value, TZ_NY);
  assert.equal(tzSel(env).getAttribute('data-prev'), TZ_NY);
});

// ==================================================== S1-04 (sign out all) ==

async function signOutAllWith(env, answer) {
  env.click(env.q('[data-act="signout-all"]')); await env.settle();
  const call = openPosts(env, SIGNOUT_ALL)[0];
  assert.ok(call, 'sign-out-everywhere must POST');
  answer(call); await env.settle();
}

test('S1-04 red: a 500 non-JSON reply is not a global sign-out', async () => {
  const env = makeEnv();
  await openSignedIn(env);
  await signOutAllWith(env, (c) => env.respond(c, 500, undefined));
  assert.equal(env.auth.signOutCalls, 0, 'failed revocation signed this device out');
  assert.ok(msgText(env, 'mmacc-signout-msg').includes(SO_UNKNOWN_EN));
});

test('S1-04 red: a transport failure is not a global sign-out', async () => {
  const env = makeEnv();
  await openSignedIn(env);
  await signOutAllWith(env, (c) => env.fail(c));
  assert.equal(env.auth.signOutCalls, 0);
  assert.ok(msgText(env, 'mmacc-signout-msg').includes(SO_UNKNOWN_EN));
});

test('S1-04 red: a 200 unreadable reply is unknown, not success', async () => {
  const env = makeEnv();
  await openSignedIn(env);
  await signOutAllWith(env, (c) => env.respond(c, 200, undefined));
  assert.equal(env.auth.signOutCalls, 0);
  assert.ok(msgText(env, 'mmacc-signout-msg').includes(SO_UNKNOWN_EN));
});

test('S1-04 red: a 200 {ok:false} without an error is unknown, not success', async () => {
  const env = makeEnv();
  await openSignedIn(env);
  await signOutAllWith(env, (c) => env.respond(c, 200, { ok: false }));
  assert.equal(env.auth.signOutCalls, 0);
  assert.ok(msgText(env, 'mmacc-signout-msg').includes(SO_UNKNOWN_EN));
});

test('S1-04 positive: an authoritative {ok:true} signs out', async () => {
  const env = makeEnv();
  await openSignedIn(env);
  await signOutAllWith(env, (c) => env.respond(c, 200, { ok: true }));
  assert.equal(env.auth.signOutCalls, 1);
});

test('S1-04 positive: a 429 keeps the session and shows the server copy (EN)', async () => {
  const env = makeEnv();
  await openSignedIn(env);
  await signOutAllWith(env, (c) => env.respond(c, 429, { ok: false, error: 'Too many requests', error_zh: '请求过多' }));
  assert.equal(env.auth.signOutCalls, 0);
  assert.ok(env.panelText().includes('Too many requests'));
});

test('S1-04 positive: a 429 shows the ZH server copy', async () => {
  const env = makeEnv({ lang: 'zh' });
  await openSignedIn(env);
  await signOutAllWith(env, (c) => env.respond(c, 429, { ok: false, error: 'Too many requests', error_zh: '请求过多' }));
  assert.equal(env.auth.signOutCalls, 0);
  assert.ok(env.panelText().includes('请求过多'));
});

test('S1-04 positive: a 502 with an error keeps the session and shows it', async () => {
  const env = makeEnv();
  await openSignedIn(env);
  await signOutAllWith(env, (c) => env.respond(c, 502, { ok: false, error: 'Upstream unavailable', error_zh: '上游不可用' }));
  assert.equal(env.auth.signOutCalls, 0);
  assert.ok(env.panelText().includes('Upstream unavailable'));
});

test('S1-04 red: a double click sends one revocation request', async () => {
  const env = makeEnv();
  await openSignedIn(env);
  env.click(env.q('[data-act="signout-all"]'));
  env.click(env.q('[data-act="signout-all"]'));
  await env.settle();
  assert.equal(env.posts(SIGNOUT_ALL).length, 1, 'double click sent two revocations');
});

test('S1-04 red: ZH unknown copy after a server failure', async () => {
  const env = makeEnv({ lang: 'zh' });
  await openSignedIn(env);
  await signOutAllWith(env, (c) => env.respond(c, 500, undefined));
  assert.equal(env.auth.signOutCalls, 0);
  assert.ok(msgText(env, 'mmacc-signout-msg').includes(SO_UNKNOWN_ZH));
});

test('S1-04 positive: local sign-out stays a separate, labelled action', async () => {
  const env = makeEnv();
  await openSignedIn(env);
  const local = env.q('[data-act="signout"]');
  const all = env.q('[data-act="signout-all"]');
  assert.ok(local && all);
  assert.notEqual(local.textContent, all.textContent);
  env.click(local); await env.settle();
  assert.equal(env.auth.signOutCalls, 1);
  assert.equal(env.posts(SIGNOUT_ALL).length, 0, 'local sign-out must not call global revocation');
});
