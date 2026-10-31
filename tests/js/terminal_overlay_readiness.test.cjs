// Run the entire shipped portal script; only browser DOM and time are simulated.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(process.env.OVERLAY_SOURCE || path.resolve(__dirname, '../../templates/terminal_overlay.js'), 'utf8');

function browser(mobile = false) {
  let now = 100000, serial = 0;
  const timers = new Map();
  const listeners = {};
  const setTimeout = (fn, delay = 0) => { timers.set(++serial, {at: now + delay, fn}); return serial; };
  function advance(ms) {
    const end = now + ms;
    for (let n = 0; n < 1000; n++) {
      const next = [...timers].filter(([, t]) => t.at <= end).sort((a, b) => a[1].at - b[1].at || a[0] - b[0])[0];
      if (!next) { now = end; return; }
      timers.delete(next[0]); now = next[1].at; next[1].fn();
    }
    throw new Error('timer loop');
  }
  class Element {
    constructor(tag) {
      this.tagName = tag.toUpperCase(); this.children = []; this.attrs = {}; this.events = {};
      this.style = {setProperty(k, v) { this[k] = v; }}; this._classes = new Set();
      this.classList = {add: (...cs) => cs.forEach(c => this._classes.add(c)),
        remove: (...cs) => cs.forEach(c => this._classes.delete(c)), contains: c => this._classes.has(c)};
      if (tag === 'iframe') this.contentWindow = {postMessage() {}};
    }
    set className(s) { this._classes = new Set(s.split(/\s+/).filter(Boolean)); }
    get className() { return [...this._classes].join(' '); }
    get isConnected() { return this === body || this === head || Boolean(this.parentNode?.isConnected); }
    get offsetWidth() { return 100; }
    setAttribute(k, v) { this.attrs[k] = String(v); }
    getAttribute(k) { return this.attrs[k] ?? null; }
    removeAttribute(k) { delete this.attrs[k]; }
    appendChild(el) { el.parentNode = this; this.children.push(el); return el; }
    insertBefore(el, before) {
      el.parentNode = this; const i = this.children.indexOf(before);
      if (i < 0) this.children.push(el); else this.children.splice(i, 0, el);
      return el;
    }
    removeChild(el) { this.children.splice(this.children.indexOf(el), 1); el.parentNode = null; }
    addEventListener(name, fn) { (this.events[name] ||= []).push(fn); }
    fire(name, data = {}) { (this.events[name] || []).forEach(fn => fn(data)); }
    focus() {}
    querySelector(selector) {
      for (const el of this.children) {
        if ((selector[0] === '.' && el.classList.contains(selector.slice(1))) ||
            (selector[0] === '#' && el.id === selector.slice(1))) return el;
        const match = el.querySelector(selector); if (match) return match;
      }
      return null;
    }
    set innerHTML(html) {
      // Minimal tag stack: classes/nesting from actual emitted markup, no product logic.
      this.children = []; const stack = [this];
      for (const match of html.matchAll(/<(\/?)([a-z][\w-]*)([^>]*)>/gi)) {
        if (match[1]) { if (stack.length > 1) stack.pop(); continue; }
        const el = new Element(match[2]);
        const cls = /class="([^"]*)"/.exec(match[3]); if (cls) el.className = cls[1];
        stack.at(-1).appendChild(el);
        if (!match[3].endsWith('/') && !['br', 'input', 'img', 'meta', 'link'].includes(match[2])) stack.push(el);
      }
    }
  }
  const body = new Element('body'), head = new Element('head'), html = new Element('html');
  const location = {hostname: 'www.mastermind-x.com', protocol: 'https:', href: 'https://www.mastermind-x.com/stocks/POWI.html'};
  const document = {body, head, documentElement: html, activeElement: null,
    createElement: tag => new Element(tag),
    getElementById: id => body.querySelector('#' + id) || head.querySelector('#' + id)};
  const window = {location, innerWidth: mobile ? 390 : 1440, innerHeight: 900, scrollX: 0, scrollY: 120,
    matchMedia: () => ({matches: mobile}), scrollTo() {},
    addEventListener(name, fn) { (listeners[name] ||= []).push(fn); }, dispatchEvent() {},
    history: {state: null, pushState(value) { this.state = value; }, go() { this.state = null; }} };
  const context = {window, document, location, navigator: {userAgent: 'test', platform: 'test', maxTouchPoints: 0},
    URL, CustomEvent: class {}, Date: {now: () => now}, setTimeout,
    clearTimeout: id => timers.delete(id), requestAnimationFrame: fn => setTimeout(fn, 16)};
  vm.runInNewContext(source, context);
  const emit = (name, event) => (listeners[name] || []).forEach(fn => fn(event));
  function open(symbol = 'POWI') {
    window.MDXTerminalOverlay.open({url: 'https://app.mastermind-x.com/terminal?symbol=' + symbol + '&embed=dashboard', symbol});
    return document.getElementById('mm-terminal-overlay').querySelector('.mmto-frame');
  }
  return {open, advance, emit, close: () => window.MDXTerminalOverlay.close(),
    root: () => document.getElementById('mm-terminal-overlay'),
    message: (frame, type, overrides = {}) => emit('message', {source: frame.contentWindow,
      origin: 'https://app.mastermind-x.com', data: {source: 'mastermind-terminal', type, symbol: 'POWI'}, ...overrides})};
}

test('stalled navigation retains recovery actions after nine seconds and one minute', () => {
  for (const mobile of [false, true]) {
    const b = browser(mobile); b.open(); b.advance(9100);
    assert.equal(b.root().classList.contains('is-ready'), false);
    assert.equal(b.root().classList.contains('is-loading'), true);
    assert.equal(b.root().classList.contains('is-slow'), true);
    assert.ok(b.root().querySelector('.mmto-back'));
    assert.ok(b.root().querySelector('.mmto-newtab'));
    b.advance(60000); assert.equal(b.root().classList.contains('is-ready'), false);
    b.root().querySelector('.mmto-back').fire('click');
    assert.equal(b.root().classList.contains('is-open'), false);
  }
});
test('document load fallback and shell-ready fallback still reveal', () => {
  for (const type of ['load', 'terminal:ready']) {
    const b = browser(), frame = b.open();
    if (type === 'load') frame.fire('load'); else b.message(frame, type);
    b.advance(7100); assert.equal(b.root().classList.contains('is-ready'), true);
  }
});
test('matching visual-ready reveals after the cold minimum', () => {
  const b = browser(), frame = b.open(); b.message(frame, 'terminal:visual-ready');
  b.advance(899); assert.equal(b.root().classList.contains('is-ready'), false);
  b.advance(1); assert.equal(b.root().classList.contains('is-ready'), true);
});
test('foreign source, origin and mismatched symbols cannot reveal a stalled frame', () => {
  const b = browser(), frame = b.open();
  b.message(frame, 'terminal:visual-ready', {origin: 'https://unrelated.example'});
  b.message(frame, 'terminal:visual-ready', {source: {}});
  b.message(frame, 'terminal:visual-ready', {data: {source: 'mastermind-terminal', type: 'terminal:visual-ready', symbol: 'CAT'}});
  b.advance(10000); assert.equal(b.root().classList.contains('is-ready'), false);
});
test('mobile remount ignores discarded frame loads and readiness', () => {
  const b = browser(true), old = b.open(); b.close(); b.advance(1); const current = b.open();
  assert.notEqual(current, old); old.fire('load'); b.message(old, 'terminal:visual-ready');
  b.advance(10000); assert.equal(b.root().classList.contains('is-ready'), false);
  b.message(current, 'terminal:visual-ready'); b.advance(1);
  assert.equal(b.root().classList.contains('is-ready'), true);
});
test('Escape and Back close a stalled overlay without revealing it', () => {
  for (const event of ['keydown', 'popstate']) {
    const b = browser(); b.open(); b.advance(9100);
    b.emit(event, {key: 'Escape', preventDefault() {}});
    b.advance(10000); assert.equal(b.root().classList.contains('is-open'), false);
    assert.equal(b.root().classList.contains('is-ready'), false);
  }
});
