"""Candidate → Plan → candidate: the one transient return, executed as real owners.

#8801 landed the exact-ID Plan hop out of a candidate detail. This is the follow-up that
brings the reader back to the SAME originating candidate with the SAME view. These
regressions execute the ACTUAL shipped owner code, sliced verbatim from the owners:

  * templates/theme.js          — the Packet2 setup-dialog owner, which now also owns the
                                  single transient candidate→Plan context;
  * templates/dashboard.html.j2 — the P0 #6185 source-mode + delegated plan-link owner;
  * templates/dashboard.html.j2 — the W8-R6 stock-table view owner (applyView).

Everything the journey only touches is a declared boundary double: a small DOM (bounded
CSS selector engine, <dialog>, delegated clicks, MutationObserver microtask delivery,
focus/scroll), the already-tested lifecycle/show-more CSS and owners, the query/filter/sort
owner in templates/stocktable.js, and USProphetLife.selectPlan — whose full target matrix
stays asserted in tests/test_prophet_plan_relation.py (unchanged and still green).

Assertions are behavioral: which exact node reopens, which source mode and table/grid view
the reader lands in, whether the source row was re-rendered away, whether exactly one
return control exists and where it is hosted, and whether the context is gone when the
source, published generation, native identity, access, Plan target or navigation changed.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PACKET2_MARKER = "/* Packet2: enhance existing entitled row details;"
NAVIGATION_MARKER = "P0 #6185 — Candidates | Plans source toggle"
STOCKVIEW_MARKER = "function initStockTableView"


def _owner_sources() -> str:
    """The three real owner slices, verbatim, as one Node program."""
    theme = (ROOT / "templates/theme.js").read_text(encoding="utf-8")
    assert theme.count(PACKET2_MARKER) == 1
    dash = (ROOT / "templates/dashboard.html.j2").read_text(encoding="utf-8")

    def inline_script(marker: str) -> str:
        assert dash.count(marker) == 1, marker
        start = dash.rfind("<script>", 0, dash.index(marker))
        end = dash.index("</script>", start)
        return dash[start + len("<script>"):end]

    # The shipped order for this journey: the dialog owner first, so the source-mode owner
    # can see window.PVSetupReturn, then the view owner that it reads.
    return "\n".join((PACKET2_MARKER + theme.split(PACKET2_MARKER, 1)[1],
                      inline_script(STOCKVIEW_MARKER), inline_script(NAVIGATION_MARKER)))


# ── boundary doubles ───────────────────────────────────────────────────────────
_HARNESS = r"""
const assert = require('node:assert/strict');

/* DOM double. Selector grammar: comma lists of compound sequences built from tag / #id /
   .class / [attr] / [attr="v"] / :scope with ' ' and '>' combinators — exactly the set the
   three owners below use. Mutation records are delivered on a microtask, like the browser. */
const mutations = [], observers = [];
let mutationScheduled = false;
function record(type, target, attributeName) {
  const interested = observers.filter(obs => (target === obs.target ||
    (obs.options.subtree && obs.target.contains(target))) &&
    (type === 'childList' ? obs.options.childList : type === 'characterData' ? obs.options.characterData :
      obs.options.attributes && (!obs.options.attributeFilter || obs.options.attributeFilter.includes(attributeName))));
  if (!interested.length) return;
  mutations.push({type, target, attributeName, interested});
  if (mutationScheduled) return;
  mutationScheduled = true;
  queueMicrotask(() => {
    mutationScheduled = false;
    const batch = mutations.splice(0, mutations.length);
    for (const obs of observers) {
      const delivered = batch.filter(item => item.interested.includes(obs));
      if (delivered.length) obs.callback(delivered, obs.self);
    }
  });
}
function parseSimple(text) {
  const parts = [];
  let i = 0;
  while (i < text.length) {
    let m;
    if (text[i] === '#' && (m = /^#([\w-]+)/.exec(text.slice(i)))) parts.push({t: 'id', v: m[1]});
    else if (text[i] === '.' && (m = /^\.([\w-]+)/.exec(text.slice(i)))) parts.push({t: 'class', v: m[1]});
    else if (text[i] === '[' && (m = /^\[([\w-]+)(?:=["']?([^"'\]]*)["']?)?\]/.exec(text.slice(i))))
      parts.push({t: 'attr', n: m[1], v: m[2] === undefined ? null : m[2]});
    else if (text[i] === ':' && (m = /^:scope/.exec(text.slice(i)))) parts.push({t: 'scope'});
    else if ((m = /^[a-zA-Z][\w-]*/.exec(text.slice(i)))) parts.push({t: 'tag', v: m[0].toLowerCase()});
    else throw new Error('unsupported selector fragment: ' + text);
    i += m[0].length;
  }
  return parts;
}
function parseSelector(sel) {
  return sel.split(',').map(chunk => {
    const seq = []; let kind = ' ';
    for (const tk of chunk.trim().replace(/\s*>\s*/g, ' > ').split(/\s+/).filter(Boolean)) {
      if (tk === '>') { kind = '>'; continue; }
      seq.push({kind, simple: parseSimple(tk)}); kind = ' ';
    }
    return seq;
  });
}
function matchSimple(node, parts, root) {
  for (const p of parts) {
    if (p.t === 'tag') { if (node.localName !== p.v) return false; }
    else if (p.t === 'id') { if (node.attrs.id !== p.v) return false; }
    else if (p.t === 'class') { if (!node.classList.contains(p.v)) return false; }
    else if (p.t === 'attr') {
      if (!Object.prototype.hasOwnProperty.call(node.attrs, p.n)) return false;
      if (p.v !== null && String(node.attrs[p.n]) !== p.v) return false;
    } else if (p.t === 'scope') { if (node !== root) return false; }
  }
  return true;
}
function matchSeq(node, seq, root) {
  let cur = node;
  for (let i = seq.length - 1; i >= 0; i--) {
    if (!matchSimple(cur, seq[i].simple, root)) return false;
    if (i === 0) return true;
    let up = cur.parentNode;
    if (seq[i].kind !== '>') { while (up && !matchSimple(up, seq[i - 1].simple, root)) up = up.parentNode; }
    if (!up || !matchSimple(up, seq[i - 1].simple, root)) return false;
    cur = up;
  }
}
class N {
  constructor(localName, nodeType) {
    this.localName = localName; this.nodeType = nodeType || 1;
    this.attrs = Object.create(null); this.kids = []; this.parentNode = null;
    this.listeners = Object.create(null); this.dataset = Object.create(null);
    this.style = Object.create(null); this._text = '';
    const self = this;
    this.classList = {
      add: (...ns) => { const s = new Set(self._tokens()); ns.forEach(n => s.add(n)); self.setAttribute('class', [...s].join(' ')); },
      remove: (...ns) => { const s = new Set(self._tokens()); ns.forEach(n => s.delete(n)); self.setAttribute('class', [...s].join(' ')); },
      contains: n => self._tokens().includes(n),
    };
  }
  _tokens() { return (this.attrs.class || '').split(/\s+/).filter(Boolean); }
  get id() { return this.attrs.id || ''; }
  set id(v) { this.setAttribute('id', String(v)); }              // ids reflect, like the DOM
  get parentElement() { const p = this.parentNode; return p && p.nodeType === 1 ? p : null; }
  get className() { return this.attrs.class || ''; }
  set className(v) { this.setAttribute('class', String(v || '')); }
  get children() { return this.kids.filter(k => k.nodeType === 1); }
  get textContent() { return this.nodeType === 3 || this.nodeType === 8 ? this._text : this.kids.map(k => k.textContent).join(''); }
  set textContent(v) {
    this.kids.forEach(k => { k.parentNode = null; }); this.kids = [];
    if (v !== '' && v != null) { const t = new N('#text', 3); t._text = String(v); t.parentNode = this; this.kids.push(t); }
    record('characterData', this);
  }
  get isConnected() { let n = this; while (n.parentNode) n = n.parentNode; return n === document.documentElement; }
  getAttribute(n) { return Object.prototype.hasOwnProperty.call(this.attrs, n) ? this.attrs[n] : null; }
  setAttribute(n, v) {
    const before = Object.prototype.hasOwnProperty.call(this.attrs, n) ? this.attrs[n] : undefined;
    this.attrs[n] = String(v);
    if (n.indexOf('data-') === 0) this.dataset[camel(n.slice(5))] = String(v);
    if (before !== this.attrs[n]) record('attributes', this, n);
  }
  removeAttribute(n) {
    if (!this.hasAttribute(n)) return;
    delete this.attrs[n];
    if (n.indexOf('data-') === 0) delete this.dataset[camel(n.slice(5))];
    record('attributes', this, n);
  }
  hasAttribute(n) { return Object.prototype.hasOwnProperty.call(this.attrs, n); }
  append(...nodes) { nodes.forEach(n => this._insert(n, this.kids.length)); return this; }
  appendChild(n) { this.append(n); return n; }
  replaceChildren(...nodes) { this.kids.slice().forEach(k => this._detach(k)); this.append(...nodes); }
  _insert(node, index) {
    if (node.parentNode) node.parentNode._detach(node);
    node.parentNode = this; this.kids.splice(index, 0, node); record('childList', this);
  }
  _detach(node) {
    const i = this.kids.indexOf(node); if (i < 0) return;
    this.kids.splice(i, 1); node.parentNode = null; record('childList', this);
  }
  before(node) { this.parentNode._insert(node, this.parentNode.kids.indexOf(this)); }
  replaceWith(node) { const p = this.parentNode, i = p.kids.indexOf(this); p._detach(this); p._insert(node, i); }
  remove() { if (this.parentNode) this.parentNode._detach(this); }
  contains(o) { let n = o; while (n) { if (n === this) return true; n = n.parentNode; } return false; }
  _walk(visit) {
    for (const k of this.kids) if (k.nodeType === 1) { if (visit(k) === false || k._walk(visit) === false) return false; }
  }
  querySelectorAll(sel) {
    const seqs = parseSelector(sel), out = [], root = this;
    this._walk(n => { if (seqs.some(sq => matchSeq(n, sq, root))) out.push(n); });
    return out;
  }
  querySelector(sel) { return this.querySelectorAll(sel)[0] || null; }
  matches(sel) { const root = this; return parseSelector(sel).some(sq => matchSeq(this, sq, root)); }
  closest(sel) {
    const seqs = parseSelector(sel), root = this;
    for (let n = this; n; n = n.parentNode) if (seqs.some(sq => matchSeq(n, sq, root))) return n;
    return null;
  }
  addEventListener(name, fn) { (this.listeners[name] = this.listeners[name] || []).push(fn); }
  getClientRects() { return visible(this) ? [{width: 10, height: 10}] : []; }
  focus() {
    effects.push(['focus', describe(this)]);
    const modal = document.querySelector('dialog[open]');
    if (visible(this) && (!modal || modal.contains(this))) document.activeElement = this;
  }
  scrollIntoView() { effects.push(['scrollIntoView', describe(this)]); scrollState.x = 0; scrollState.y = 5000; windowProps.scrollY = 5000; }
  getBoundingClientRect() { return {left: 0, top: 0, right: 900, bottom: 600}; }
  click() { fire(this, 'click'); }
  get tabIndex() { return this.hasAttribute('tabindex') ? Number(this.attrs.tabindex) : 0; }
}
function camel(n) { return n.replace(/-([a-z])/g, (_, c) => c.toUpperCase()); }
function describe(n) { return n.attrs.id || n.attrs.class || n.localName; }
function fire(node, type) {
  type = type || 'click';
  const ev = {type, target: node, defaultPrevented: false, button: 0, preventDefault() { ev.defaultPrevented = true; }};
  for (let n = node; n; n = n.parentNode) (n.listeners[type] || []).slice().forEach(fn => fn(ev));
  (document.listeners[type] || []).slice().forEach(fn => fn(ev));
  return ev;
}
function makeElement(tag) {
  const el = new N(tag);
  if (tag === 'template') el.content = new N('#document-fragment', 11);
  if (tag === 'dialog') {
    el.open = false; el.scrollTop = 0;
    el.showModal = () => { el.open = true; el.setAttribute('open', ''); effects.push(['showModal']); };
    el.close = () => { el.open = false; el.removeAttribute('open'); effects.push(['dialogClose']); queueMicrotask(() => (el.listeners.close || []).slice().forEach(fn => fn({type: 'close', target: el}))); };
  }
  return el;
}
const documentElement = new N('html'), body = new N('body');
body.parentNode = documentElement; documentElement.kids.push(body);
const document = {
  readyState: 'complete', documentElement, body, activeElement: null, listeners: Object.create(null),
  createElement: makeElement,
  createComment: (t) => { const c = new N('#comment', 8); c._text = t; return c; },
  getElementById: (id) => { let f = null; documentElement._walk(n => { if (n.attrs.id === id) { f = n; return false; } }); return f; },
  querySelector: (sel) => documentElement.querySelector(sel),
  querySelectorAll: (sel) => documentElement.querySelectorAll(sel),
  addEventListener: (name, fn) => { (document.listeners[name] = document.listeners[name] || []).push(fn); },
};
class MutationObserverDouble {
  constructor(callback) { this.callback = callback; this.self = this; }
  observe(target, options) { this.target = target; this.options = options; observers.push(this); }
  disconnect() { const i = observers.indexOf(this); if (i >= 0) observers.splice(i, 1); }
  takeRecords() { return []; }
}
const scrollState = {x: 0, y: 0}, effects = [];
/* Browsers expose window properties as globals (the view owner reads a bare StockTable),
   so assignments through window are reflected; the window plumbing stays off the global. */
const windowInternals = new Set(['scrollX', 'scrollY', 'scrollTo', 'addEventListener', 'fireWindow', 'getComputedStyle', 'listeners']);
const windowProps = {
  scrollX: 0, scrollY: 0, listeners: Object.create(null),
  scrollTo(o) { effects.push(['windowScroll', Math.round(o.top)]); windowProps.scrollX = scrollState.x = o.left || 0; windowProps.scrollY = scrollState.y = o.top || 0; },
  addEventListener(name, fn) { (windowProps.listeners[name] = windowProps.listeners[name] || []).push(fn); },
  fireWindow(name) { (windowProps.listeners[name] || []).slice().forEach(fn => fn({type: name, target: window, preventDefault() {}})); },
  getComputedStyle: () => ({getPropertyValue: () => '330px 330px 330px'}),
};
const window = new Proxy(windowProps, {
  set(t, k, v) { t[k] = v; if (typeof k === 'string' && !windowInternals.has(k)) globalThis[k] = v; return true; },
  get(t, k) { return t[k]; },
});
globalThis.document = document; globalThis.window = window;
globalThis.MutationObserver = MutationObserverDouble;
globalThis.HTMLDialogElement = function HTMLDialogElement() {};
globalThis.localStorage = {store: Object.create(null),
  getItem(k) { return Object.prototype.hasOwnProperty.call(this.store, k) ? this.store[k] : null; },
  setItem(k, v) { this.store[k] = String(v); effects.push(['persistView', k]); }};

/* Visibility: boundary double for the ALREADY-TESTED shipped rules —
   #us-stocktable-wrap shows only in candidates + .st-table-mode; .nb-grid-section shows in
   candidates without it; #us-candidate-pool only in candidates; #us-today only in today;
   #us-plan-block only in plans, and there only the selected data-life card, unless withheld;
   entitlement uses [hidden]/[aria-hidden]/.mx-tier-hidden/.mx-tier-blurred; show-more uses
   .sm-hidden. Chromium covers the real CSS. */
function mode() { return panel.getAttribute('data-prophet-src'); }
function visible(n) {
  if (n.closest('[aria-hidden="true"],[hidden],.mx-tier-hidden,.mx-tier-blurred')) return false;
  if (n.closest('.sm-hidden')) return false;
  if (n.closest('#us-plan-block')) {
    if (mode() !== 'plans') return false;
    const card = n.closest('.pvcard');
    if (card) {
      if (card._withheld) return false;
      const lifef = panel.getAttribute('data-lifef');
      if (lifef && card.getAttribute('data-life') !== lifef) return false;
    }
    return true;
  }
  if (n.closest('#us-stocktable-wrap')) return mode() === 'candidates' && panel.classList.contains('st-table-mode');
  if (n.closest('#us-today')) return mode() === 'today';
  if (n.closest('#us-candidate-pool')) return mode() === 'candidates';
  if (n.closest('.nb-grid-section')) return mode() === 'candidates' && !panel.classList.contains('st-table-mode');
  return true;
}

/* show-more: boundary double for theme.js initShowMore — its documented idempotence per
   element (data-smInit) is precisely what the return must not disturb. */
let showMoreCalls = 0;
window.initShowMore = function () {
  showMoreCalls++;
  documentElement.querySelectorAll('[data-showmore-rows]').forEach(grid => {
    if (grid.dataset.smInit) return;
    const rows = Number(grid.getAttribute('data-showmore-rows')) || 3;
    grid.children.forEach((kid, i) => { if (i >= rows) kid.classList.add('sm-hidden'); });
    grid.setAttribute('data-sm-init', '1');
  });
};
const revealShowMore = (grid) => grid.children.forEach(k => k.classList.remove('sm-hidden'));

/* USProphetLife.selectPlan: boundary double for the untouched lifecycle owner; its full
   published target matrix is asserted in tests/test_prophet_plan_relation.py. */
window.USProphetLife = { selectPlan(card) {
  if (!card || !card.classList.contains('pvcard') || card.getAttribute('data-record-only') !== '1' ||
      !card.closest('#us-life-grid') ||
      card.closest('[aria-hidden="true"],[hidden],.mx-tier-hidden,.mx-tier-blurred')) return false;
  const life = card.getAttribute('data-life');
  if (!['watch', 'ready', 'entered', 'delivering', 'overtime', 'invalidated', 'resolved'].includes(life)) return false;
  if (card._withheld) return false;
  panel.setAttribute('data-lifef', life);              // the real owner's published effect
  return true;
} };

/* StockTable: boundary double for templates/stocktable.js, which owns query/filter/sort.
   Its state object plus the init count are the observable proof that the journey leaves
   both (and the rendered rows) alone. */
const tableState = {q: 'lfu', sortKey: 'alpha', sortDir: 'desc', lane: 'continuation', sector: 'Information Technology'};
let stockTableInitCalls = 0;
window.StockTable = {
  _bi: (en, zh) => '<span class="l-en">' + en + '</span><span class="l-zh">' + zh + '</span>',
  _esc: (s) => String(s), _fmtPct: (v) => Number(v).toFixed(2) + '%', _fmtNum: (v) => String(v),
  init() { stockTableInitCalls++; },
};

/* ── fixture board, mirroring the shipped element/class contract ─────────────── */
function mk(tag, cls, attrs) {
  const el = makeElement(tag);
  if (cls) el.attrs.class = cls;
  Object.entries(attrs || {}).forEach(([k, v]) => el.setAttribute(k, v));
  return el;
}
function candidate(kind, ticker, planId) {
  const isTable = kind === 'table';
  const row = kind === 'pool' ? mk('div', 'ucp-row', {'data-ticker': ticker})
            : isTable ? mk('tr', 'st-row', {'data-ticker': ticker})
            : mk('article', 'pvcard pv-wait pv-has-setup', {'data-ticker': ticker, id: 'pv-card-' + ticker});
  const details = mk('details', isTable ? 'pv-setup-inline pv-setup-table' : 'pv-setup-inline');
  if (isTable) {
    details.setAttribute('data-setup-ticker', ticker);
    details.setAttribute('data-setup-asof', panel.getAttribute('data-board-asof'));
    row.append(mk('a', 'stf-tkr', {'href': 'stock.html#' + ticker}), mk('td'));
  } else if (kind === 'pool') {
    row.append(mk('div', 'ucp-identity'));
  } else {
    row.append(mk('a', 'pv-setup-stock-link', {'href': 'stock.html#' + ticker}));
  }
  const summary = mk('summary'); summary.textContent = 'Setup detail';
  const bodyEl = mk('div', 'pv-setup-body', {'data-native-id': ticker});
  const relation = mk('section', 'pvs-section pvs-plan-relation', {'data-plan-relation': 'related_security'});
  const rec = mk('div', 'pvs-plan-rec', {'data-plan-id': planId});
  const link = mk('button', 'pvs-plan-link', {'data-pvs-plan-target': 'pv-' + planId, type: 'button'});
  const en = mk('span', 'l-en'); en.textContent = 'View in Plans';
  const zh = mk('span', 'l-zh'); zh.textContent = '在计划中查看';
  link.append(en, zh); rec.append(link); relation.append(rec);
  bodyEl.append(mk('span', 'pvs-chart-slot', {'data-pvs-chart': '1'}), relation);
  if (isTable) {
    const holder = mk('template', 'pvs-body-source'); holder.content.append(bodyEl);
    const spark = mk('template', 'pvs-chart-source');            // a row with no published spark
    const note = mk('p', 'pvs-fallback-note'); note.textContent = 'fallback';
    details.append(summary, holder, note, spark);
    row.children[1].append(details);
  } else {
    details.append(summary, bodyEl); row.append(details);
  }
  if (kind === 'pool') row.querySelector('.ucp-identity').append(mk('a', null, {'href': 'stock.html#' + ticker}));
  return {row, details, trigger: summary, body: bodyEl, link, kind, ticker};
}
function planCard(id, life, ticker) {
  const card = mk('article', 'pvcard pv-noread pv-record',
                  {'data-life': life, 'data-record-only': '1', id: 'pv-' + id, 'data-ticker': ticker});
  card.append(mk('a', 'pv-record-link', {'href': 'stock.html#' + ticker}));
  const details = mk('details', 'pv-record-detail', {'data-plan-id': id});
  const summary = mk('summary'); summary.textContent = 'Record detail';
  const recBody = mk('div', 'pv-record-body'); recBody.textContent = 'model record ' + id;
  details.append(summary, recBody); card.append(details);
  return {card, details, trigger: summary};
}
let panel = null, headerRow = null, lifeGrid = null, candGrid = null;
const origins = {}, plans = {};
function build(opts) {
  const o = Object.assign({view: 'grid', mode: 'candidates', asof: '2026-10-09T20:00:00-04:00'}, opts || {});
  if (o.view === 'table') globalThis.localStorage.setItem('mdx_stocktable_us', 'table');
  panel = mk('div', 'panel span12 notable', {id: 'us-standouts', 'data-prophet-src': o.mode, 'data-board-asof': o.asof});
  panel.setAttribute('data-lifef', 'resolved');
  headerRow = mk('div', 'pb-hdrow');
  const tog = mk('span', 'st-view-toggle', {id: 'us-src-toggle', role: 'group'});
  tog.append(mk('button', null, {id: 'us-src-btn-today', 'data-src': 'today', type: 'button'}),
             mk('button', null, {id: 'us-src-btn-cand', 'data-src': 'candidates', type: 'button'}),
             mk('button', null, {id: 'us-src-btn-plan', 'data-src': 'plans', type: 'button'}));
  const viewTog = mk('span', 'st-view-toggle', {id: 'us-st-view-toggle'});
  viewTog.append(mk('button', null, {id: 'us-st-btn-grid', type: 'button'}), mk('button', null, {id: 'us-st-btn-table', type: 'button'}));
  headerRow.append(tog, viewTog); panel.append(headerRow);

  const planBlock = mk('div', null, {id: 'us-plan-block'});
  lifeGrid = mk('div', 'nbgrid', {id: 'us-life-grid', 'data-mp1-grid': '1', 'data-showmore-rows': '3'});
  plans.LFUS = planCard('LFUS-BULL-20260810', 'entered', 'LFUS');
  plans.OTHER = planCard('OTHER-BULL-20260811', 'watch', 'OTHER');
  plans.TDAY = planCard('TDAY-BULL-20260810', 'ready', 'TDAY');
  plans.BOAR = planCard('BOAR-BULL-20260810', 'delivering', 'BOAR');
  plans.POOL = planCard('POOL-BULL-20260810', 'entered', 'POOL');
  lifeGrid.append(plans.LFUS.card, plans.OTHER.card, plans.TDAY.card, plans.BOAR.card, plans.POOL.card);
  planBlock.append(lifeGrid);

  const today = mk('section', 'mx-sec', {id: 'us-today', 'data-today-total': '1'});
  const todayGrid = mk('div', 'nbgrid', {id: 'us-today-grid'});
  origins.today = candidate('today', 'TDAY', 'TDAY-BULL-20260810');
  todayGrid.append(origins.today.row); today.append(todayGrid);

  const gridSection = mk('div', 'nb-grid-section');
  const candidates = mk('div', 'mx-sec', {id: 'us-candidates'});
  candGrid = mk('div', 'nbgrid', {id: 'us-cand-grid', 'data-showmore-rows': '3'});
  origins.board = candidate('board', 'BOAR', 'BOAR-BULL-20260810');
  candGrid.append(origins.board.row);
  for (let i = 0; i < 4; i++) candGrid.append(mk('article', 'pvcard', {'data-ticker': 'EXTRA' + i}));
  candidates.append(candGrid); gridSection.append(candidates);

  const wrap = mk('div', null, {id: 'us-stocktable-wrap'});
  const table = mk('table', 'st-table'), tbody = mk('tbody');
  origins.table = candidate('table', 'LFUS', 'LFUS-BULL-20260810');
  tbody.append(origins.table.row); table.append(tbody); wrap.append(table);

  const pool = mk('details', 'ucp', {id: 'us-candidate-pool', 'data-as-of': '2026-10-09',
                                     'data-source-digest': 'dig-1', 'data-total': '1'});
  const poolList = mk('div', 'ucp-list');
  origins.pool = candidate('pool', 'POOL', 'POOL-BULL-20260810');
  poolList.append(origins.pool.row); pool.append(mk('summary'), poolList);

  const stockData = mk('script', null, {id: 'us-stocktable-data', type: 'application/json'});
  stockData.textContent = JSON.stringify({rows: [{ticker: 'LFUS', name: 'Lfus'}]});
  panel.append(today, gridSection, wrap, planBlock, pool, stockData);
  body.append(panel);
  window.initShowMore();
}
const dialogEl = () => document.getElementById('pv-setup-dialog');
const footEl = () => dialogEl() && dialogEl().querySelector('.pvs-dialog-foot');
const closeBtn = () => dialogEl() && dialogEl().querySelector('.pvs-close');
const returnBtns = () => document.querySelectorAll('[data-pvs-return]');
const srcBtn = (which) => document.getElementById('us-src-btn-' + which);
const flush = () => new Promise((resolve) => setTimeout(resolve, 0));

__BUILD__
__OWNERS__

const run = async () => {
  scrollState.y = windowProps.scrollY = 1200;          // the reader was mid-board
__SCENARIO__
};
run().then(() => { console.log('OK'); },
           (e) => { console.error((e && e.stack) || String(e)); process.exit(1); });
"""

_PRE = {"grid": "build({mode: 'candidates', view: 'grid'});",
        "table": "build({mode: 'candidates', view: 'table'});",
        "today": "build({mode: 'today', view: 'grid'});"}

# Open a candidate detail, hop to its exact-ID related Plan through the shipped plan-link
# owner, and record what the return has to bring back.
_JUMP_CORE = """
fire(origin.trigger);                               // candidate detail opens in the dialog
assert.equal(dialogEl().open, true, 'the candidate detail did not open');
assert.equal(document.activeElement, closeBtn(), 'the dialog must take focus on its close control');
fire(origin.link);                                  // View in Plans: snapshot, close, plans
assert.equal(document.body.dataset.pvsPlanLinkResult, 'ok');
assert.equal(document.body.dataset.pvsCandidateReturn, 'available', 'no return control after the hop');
assert.equal(returnBtns().length, 1, 'exactly one return control');
assert.equal(window.PVSetupReturn.available(), true);
assert.equal(window.USProphetSource.get(), 'plans');
"""


def _jump(kind: str, setup: str = "") -> str:
    return ("const origin = origins['%s'];\n" % kind + setup +
            "const before = {mode: window.USProphetSource.get(), view: window.USStockTable._getView(),"
            " inits: stockTableInitCalls, scroll: scrollState.y};\n" + _JUMP_CORE)


def _run(scenario: str, pre: str = _PRE["grid"]) -> None:
    node = shutil.which("node")
    assert node, "existing Node runtime is required for the candidate→Plan return journey"
    program = (_HARNESS.replace("__BUILD__", pre).replace("__OWNERS__", _owner_sources())
               .replace("__SCENARIO__", scenario))
    proc = subprocess.run([node, "-e", program], capture_output=True, text=True, timeout=30)
    assert proc.returncode == 0, "node harness failed:\n" + (proc.stderr or proc.stdout)


@pytest.mark.parametrize("kind,pre", [
    ("pool", _PRE["grid"]), ("board", _PRE["grid"]),
    ("today", _PRE["today"]), ("table", _PRE["table"]),
])
def test_return_reopens_the_exact_originating_candidate_and_is_then_spent(kind, pre):
    """Today and Screener (candidate pool row, board card, dense table row): the shipped
    owners carry the reader back to the same trigger/details/row in the same source mode
    and view, and the journey is then spent — no lingering control, no second navigation."""
    _run(
        _jump(kind)
        + """
const btn = returnBtns()[0];
assert.equal(btn.parentNode, headerRow, 'with no Plan detail open the action belongs to the panel header');
assert.ok(btn.classList.contains('mx-sec-link'), 'must reuse the existing header link-button styling');
assert.ok(btn.textContent.includes('Return to candidate') && btn.textContent.includes('返回候选'),
          'EN/ZH copy must ship together');

assert.equal(window.PVSetupReturn.run(), true, 'return refused');
assert.equal(window.USProphetSource.get(), before.mode, 'source mode not restored');
assert.equal(window.USStockTable._getView(), before.view, 'table/grid view not restored');
assert.equal(dialogEl().open, true, 'the candidate detail did not reopen');
assert.equal(origin.row.contains(origin.details), true);
assert.equal(origin.row.isConnected && origin.row.getClientRects().length === 1, true,
             'the origin row must be live and reachable again');
assert.equal(dialogEl().querySelector('.pvs-dialog-content').querySelector('.pv-setup-body'), origin.body,
             'the dialog must reopen the exact originating body node, not a stand-in');
assert.equal(document.body.dataset.pvsCandidateReturn, 'clear', 'a spent journey must clear its control');
assert.equal(returnBtns().length, 0);
assert.equal(document.activeElement, closeBtn(), 'focus must land on the dialog close control');
assert.equal(scrollState.y, before.scroll, 'the reader must be back at the origin scroll');

fire(closeBtn());                                    // Close returns to the original trigger
assert.equal(dialogEl().open, false);
assert.equal(document.activeElement, origin.trigger, 'Close must return focus to the original trigger');
assert.equal(scrollState.y, before.scroll, 'Close must return the scroll that belonged to that row');
assert.equal(stockTableInitCalls, before.inits, 'the return must not re-render the board');
""",
        pre=pre,
    )


def test_table_view_journey_restores_table_without_rerendering_the_source_row():
    """setSrc('plans') forces the table to grid. Returning must put the reader back in
    table view through the existing view owner, keep the very same <tr>, and leave the
    stock table's own query/filter/sort state alone."""
    _run(
        _jump("table")
        + """
assert.equal(before.view, 'table', 'fixture control: the reader really was in table view');
assert.equal(panel.classList.contains('st-table-mode'), false, 'Plans must have left table view');
assert.equal(window.USStockTable._getView(), 'grid');
returnBtns()[0].click();
assert.equal(panel.getAttribute('data-prophet-src'), 'candidates');
assert.equal(panel.classList.contains('st-table-mode'), true, 'table view was not restored');
assert.equal(window.USStockTable._getView(), 'table');
assert.equal(stockTableInitCalls, 1, 'applyView must not re-init StockTable — that is the row-destroying path');
assert.equal(origin.row.isConnected && visible(origin.row), true, 'the exact source row must be reachable');
assert.deepEqual([tableState.q, tableState.sortKey, tableState.sortDir, tableState.lane, tableState.sector],
                 ['lfu', 'alpha', 'desc', 'continuation', 'Information Technology']);
assert.equal(dialogEl().querySelector('#pvs-dialog-title').textContent, 'LFUS');
assert.equal(origin.body.parentNode, dialogEl().querySelector('.pvs-dialog-content'));
""",
        pre=_PRE["table"],
    )


def test_expanded_show_more_survives_the_round_trip():
    """A reader who paged deeper into the board keeps that density: the return only
    re-arms the existing owners, and show-more stays initialised on the same element."""
    _run(
        _jump("board", """
assert.equal(origin.row.classList.contains('sm-hidden'), false);
revealShowMore(candGrid);
const gridIdentity = candGrid;
const callsBefore = showMoreCalls;
""") + """
assert.equal(candGrid, gridIdentity, 'the board grid was rebuilt while the reader was away');
assert.equal(candGrid.children.filter(k => k.classList.contains('sm-hidden')).length, 0);
returnBtns()[0].click();
assert.equal(candGrid, gridIdentity);
assert.equal(candGrid.children[0], origin.row, 'the return routed to a different row');
assert.equal(origin.row.classList.contains('sm-hidden'), false, 'the return collapsed the reader expansion');
assert.equal(candGrid.getAttribute('data-sm-init'), '1', 'show-more stayed initialised on the same grid');
assert.ok(showMoreCalls > callsBefore, 'the source owner keeps re-running the idempotent show-more owner');
assert.equal(candGrid.children.filter(k => k.classList.contains('sm-hidden')).length, 0);
""",
    )


def test_return_is_offered_from_the_plan_detail_itself_and_rehosts_after_close():
    """Same candidate journey, two places the reader can act: inside that Plan's detail (a modal
    dialog makes anything behind it unreachable) and after closing it."""
    _run(
        _jump("table")
        + """
fire(plans.LFUS.trigger);                            // open that Plan's own detail
assert.equal(dialogEl().open, true);
assert.equal(returnBtns()[0].parentNode, footEl(), 'the action must be inside the open Plan detail');
assert.equal(returnBtns().length, 1, 'one journey must not render two controls');
assert.equal(visible(origin.row), false, 'the origin is hidden only because Plans is selected');
assert.equal(window.PVSetupReturn.available(), true, 'source-mode hiding is not access loss');

fire(closeBtn());                                    // close the Plan detail without returning
assert.equal(dialogEl().open, false);
assert.equal(returnBtns().length, 1, 'the action must stay usable after the Plan detail closes');
assert.equal(returnBtns()[0].parentNode, headerRow);
assert.equal(document.body.dataset.pvsCandidateReturn, 'available');

returnBtns()[0].click();
assert.equal(window.USProphetSource.get(), 'candidates');
assert.equal(document.body.dataset.pvsCandidateReturn, 'clear');
assert.equal(origin.body.parentNode, dialogEl().querySelector('.pvs-dialog-content'));
""",
        pre=_PRE["table"],
    )


def test_a_related_plan_is_a_hop_not_an_episode_and_earns_no_new_fact():
    """A related same-security Plan is the hop target, not this candidate's plan: the
    return binds the candidate it came from and writes nothing onto the Plan card."""
    _run(
        _jump("table")
        + """
const card = plans.LFUS.card;
const seen = [card.getAttribute('data-life'), card.getAttribute('data-record-only'),
              card.getAttribute('id'), card.children.length];
returnBtns()[0].click();
assert.equal(window.PVSetupReturn.available(), false);
assert.deepEqual([card.getAttribute('data-life'), card.getAttribute('data-record-only'),
                  card.getAttribute('id'), card.children.length], seen,
                 'the journey must not append plan facts to the card');
assert.equal(card.querySelector('[data-pvs-return]'), null, 'no control inside another owner card');
assert.equal(origin.body.closest('#us-life-grid'), null);
assert.equal(document.activeElement, closeBtn());
""",
        pre=_PRE["table"],
    )


@pytest.mark.parametrize("label,mutation", [
    ("row removed", "origin.row.remove();"),
    ("table re-rendered by hydration",
     "const freshBody = mk('tbody'); freshBody.append(mk('tr', 'st-row', {'data-ticker': 'LFUS'}));"
     " origin.row.parentNode.append(freshBody); origin.row.remove();"),
    ("row recycled for another ticker", "origin.details.setAttribute('data-setup-ticker', 'OTHER');"),
    ("native link moved", "origin.row.querySelector('.stf-tkr').setAttribute('href', 'stock.html#OTHER');"),
    ("published generation changed", "panel.setAttribute('data-as-of', '2026-10-10T20:00:00-04:00');"),
    ("source access withheld", "document.getElementById('us-stocktable-wrap').setAttribute('hidden', '');"),
    ("tier payload turned", "window.fireWindow('mmx-access-tier');"),
    ("auth turned", "window.fireWindow('mdx-auth');"),
    ("plan target removed", "lifeGrid.remove();"),
    ("source aria withheld", "origin.row.setAttribute('aria-hidden', 'true');"),
    ("source tier class withheld", "origin.row.classList.add('mx-tier-hidden');"),
    ("plan target renamed", "plans.LFUS.card.id = 'pv-OTHER-BULL-20260811';"),
    ("origin trigger moved", "body.append(origin.trigger);"),
])
def test_a_stale_origin_clears_the_return_control_promptly(label, mutation):
    """No source resurrection and no ghost control: whatever takes the bound origin, its
    generation, its native identity, its access or its Plan target away drops the one
    transient context — on the next microtask turn, before the reader could use it."""
    _run(
        (_jump("table")
         + """
await flush(); // settle the navigation before testing an isolated later mutation
assert.equal(window.PVSetupReturn.available(), true, 'Plans-mode hiding alone must not invalidate');
const stale = returnBtns()[0];
const why = ]]WHY[;
""" + mutation + """
await flush();
assert.equal(window.PVSetupReturn.available(), false, why + ': must invalidate the context');
assert.equal(document.body.dataset.pvsCandidateReturn, 'clear', why + ': must clear the control');
assert.equal(returnBtns().length, 0, why + ': left a dead control on screen');
assert.equal(window.PVSetupReturn.run(), false, why + ': a cleared journey must not reopen anything');
assert.equal(dialogEl().open, false, why + ': no dialog may open from a stale origin');
assert.equal(stale.parentNode, null, why + ': the cleared action must leave the page');
""").replace("]]WHY[", repr(label)),
        pre=_PRE["table"],
    )


def test_a_repeated_hop_at_the_same_plan_keeps_the_return_it_already_earned():
    """A second click on the released link has no live detail left to snapshot, but the
    bound origin has not changed — and a different target earns no inheritance."""
    _run(
        _jump("table")
        + """
fire(origin.link);                                   // the same candidate, the same Plan
assert.equal(document.body.dataset.pvsPlanLinkResult, 'ok');
assert.equal(returnBtns().length, 1, 'the same hop must not duplicate or drop the return');
assert.equal(window.PVSetupReturn.available(), true);
assert.equal(document.activeElement, plans.LFUS.card, 'the hop still lands on the exact Plan');
assert.equal(window.PVSetupReturn.run(), true);
assert.equal(window.USProphetSource.get(), 'candidates');
assert.equal(document.activeElement, closeBtn());

const o2 = origins.table;
fire(o2.trigger); fire(o2.link);
assert.equal(returnBtns().length, 1);
const rec2 = mk('div', 'pvs-plan-rec', {'data-plan-id': 'OTHER-BULL-20260811'});
const link2 = mk('button', 'pvs-plan-link', {'data-pvs-plan-target': 'pv-OTHER-BULL-20260811', type: 'button'});
link2.textContent = 'View in Plans'; rec2.append(link2);
o2.body.querySelector('.pvs-plan-relation').append(rec2);
fire(link2);                                          // a second same-security record
assert.equal(document.body.dataset.pvsPlanLinkResult, 'ok');
assert.equal(returnBtns().length, 0, 'a different Plan target must not inherit the stale return');
assert.equal(window.PVSetupReturn.available(), false);
assert.equal(window.PVSetupReturn.run(), false);
""",
        pre=_PRE["table"],
    )


def test_pool_generation_and_native_identity_are_both_required():
    """The candidate pool publishes its own digest and the board card carries its own
    native link; either moving under a still-connected row means a different source."""
    _run(
        _jump("pool")
        + """
document.getElementById('us-candidate-pool').setAttribute('data-source-digest', 'dig-2');
await flush();
assert.equal(window.PVSetupReturn.available(), false, 'a new published generation is a new source');
assert.equal(returnBtns().length, 0);
assert.equal(window.PVSetupReturn.run(), false);

fire(srcBtn('cand'));                                // back to Screener, then a fresh journey
const other = origins.board;
fire(other.trigger);
assert.equal(dialogEl().open, true);
fire(other.link);
assert.equal(document.body.dataset.pvsCandidateReturn, 'available');
other.row.querySelector('.pv-setup-stock-link').setAttribute('href', 'stock.html#SWAPPED');
await flush();
assert.equal(window.PVSetupReturn.available(), false, 'the native identity/link must be unchanged');
assert.equal(returnBtns().length, 0);
assert.equal(window.PVSetupReturn.run(), false);
assert.equal(other.row.isConnected, true, 'the row stayed live: only its identity moved');
""",
    )


def test_direct_plan_visit_offers_no_return_and_a_failed_hop_inherits_no_stale_context():
    """Plans reached without a candidate detail is a direct visit; a plan link whose exact
    target is missing claims no journey; and an explicit unrelated visit ends a live one."""
    _run(
        """
fire(srcBtn('plan'));                                // direct visit, no candidate detail first
assert.equal(window.USProphetSource.get(), 'plans');
assert.equal(returnBtns().length, 0, 'a direct Plan visit must not show a candidate-return control');
assert.equal(window.PVSetupReturn.available(), false);
assert.equal(window.PVSetupReturn.run(), false);

const origin = origins.board;
fire(srcBtn('cand'));                                // back to Screener the existing way
fire(origin.trigger);
assert.equal(dialogEl().open, true);
origin.link.setAttribute('data-pvs-plan-target', 'pv-NOPE-20260810');
fire(origin.link);
assert.equal(document.body.dataset.pvsPlanLinkResult, 'missing');
assert.equal(returnBtns().length, 0, 'no confirmed target, so no journey');
assert.equal(window.PVSetupReturn.available(), false);

// a real hop from a real candidate detail: the shipped owner had already moved to Plans
origin.link.setAttribute('data-pvs-plan-target', 'pv-BOAR-BULL-20260810');
fire(srcBtn('cand'));
fire(origin.trigger);
assert.equal(dialogEl().open, true, 'the retried hop must start from a live candidate detail');
fire(origin.link);
assert.equal(document.body.dataset.pvsPlanLinkResult, 'ok');
assert.equal(returnBtns().length, 1);

fire(srcBtn('plan'));                                // an explicit, unrelated visit
assert.equal(document.body.dataset.pvsCandidateReturn, 'clear');
assert.equal(returnBtns().length, 0, 'a direct Plans visit must not inherit a stale return');
assert.equal(window.PVSetupReturn.run(), false);
""",
    )


def test_second_candidate_journey_replaces_the_first():
    """One context, the most recent journey: the second hop is what the reader can come
    back to, and the replaced origin keeps its own row and disclosure intact."""
    _run(
        """
fire(srcBtn('today'));                               // Today shelf, reached the existing way
assert.equal(window.USProphetSource.get(), 'today');
const first = origins.today;
fire(first.trigger); fire(first.link);
assert.equal(document.body.dataset.pvsPlanLinkResult, 'ok');
assert.equal(returnBtns().length, 1);
assert.equal(window.PVSetupReturn.available(), true);

fire(srcBtn('cand'));                                // an explicit turn ends journey one
assert.equal(document.body.dataset.pvsCandidateReturn, 'clear');
const second = origins.pool;
fire(second.trigger); fire(second.link);
assert.equal(document.body.dataset.pvsPlanLinkResult, 'ok');
assert.equal(returnBtns().length, 1);

assert.equal(window.PVSetupReturn.run(), true, 'the return went to the replaced journey');
assert.equal(window.USProphetSource.get(), 'candidates', 'the second journey came from Screener');
assert.equal(dialogEl().querySelector('.pvs-dialog-content').querySelector('.pv-setup-body'), second.body);
assert.equal(dialogEl().querySelector('#pvs-dialog-title').textContent, 'POOL');
fire(closeBtn());
assert.equal(document.activeElement, second.trigger, 'focus returns to the SECOND origin');
assert.equal(first.row.contains(first.details), true, 'the replaced journey left the first row intact');
assert.equal(document.getElementById('us-today').querySelector('.pv-setup-body'), first.body,
             'the Today card keeps its own detail, exactly where it was');
""",
    )


def test_opening_another_plan_detail_ends_the_journey():
    """The action belongs to one episode: opening a DIFFERENT Plan's detail — here another
    card the same published lifecycle cell legitimately shows — is an explicit unrelated
    navigation and must not leave a return for the earlier hop."""
    _run(
        _jump("table")
        + """
assert.equal(plans.POOL.card.getAttribute('data-life'), plans.LFUS.card.getAttribute('data-life'),
             'fixture control: both cards sit in the one published lifecycle cell');
revealShowMore(lifeGrid);                            // the reader paged to it
fire(plans.POOL.trigger);                            // a Plan that is not this journey's
assert.equal(dialogEl().open, true);
assert.equal(window.PVSetupReturn.available(), false);
assert.equal(document.body.dataset.pvsCandidateReturn, 'clear');
assert.equal(returnBtns().length, 0);
assert.equal(window.PVSetupReturn.run(), false);
""",
        pre=_PRE["table"],
    )


def test_async_detail_move_and_mode_switch_keep_a_same_generation_journey():
    """Mutation delivery is asynchronous and the dialog moves live detail nodes out of
    their row: neither may destroy a valid same-generation context, and the released body
    must land back inside its own details element."""
    _run(
        """
const origin = origins.board;
fire(origin.trigger);
await flush();
assert.equal(origin.row.contains(origin.details), true, 'the details element itself must stay in its row');
assert.equal(origin.body.parentNode, dialogEl().querySelector('.pvs-dialog-content'));
assert.equal(dialogEl().open, true, 'a queued move must not dismiss a valid same-generation source');
await flush();
fire(origin.link);
await flush();
assert.equal(document.body.dataset.pvsPlanLinkResult, 'ok');
assert.equal(origin.body.parentNode, origin.details, 'the released body must return to its own details');
assert.equal(window.PVSetupReturn.available(), true, 'a same-generation move must not invalidate the journey');
assert.equal(returnBtns().length, 1);
assert.equal(origin.row.classList.contains('sm-hidden'), false);
await flush();
assert.equal(window.PVSetupReturn.available(), true);
assert.equal(window.PVSetupReturn.run(), true);
""",
    )


def test_plan_relation_target_selection_is_left_exactly_as_8801_shipped_it():
    """Guard for the reference suite: this follow-up keeps the exact data-pvs-plan-target
    and the existing USProphetLife.selectPlan call in the shipped plan-link owner."""
    source = (ROOT / "templates/dashboard.html.j2").read_text(encoding="utf-8")
    handler = source[source.index("var button = event.target"):source.index("</script>", source.index("var button = event.target"))]
    for expected in (
        "closest('.pvs-plan-link[data-pvs-plan-target]')",
        "button.getAttribute('data-pvs-plan-target')",
        "document.getElementById(target)",
        "window.USProphetLife.selectPlan(card)",
        "USProphetSource.set('plans')",
        "PVSetupReturn.establish(pending, target, card)",
        "PVSetupReturn.abandon()",
        "pvsPlanLinkResult='missing'",
        "pvsPlanLinkResult='ok'",
    ):
        assert expected in handler, expected
    assert "createElement" not in handler, "the plan-link owner must not allocate its own dialog or control"


def test_return_from_inside_open_plan_detail_restores_original_scroll_on_close():
    _run(_jump("table") + """
await flush();
fire(plans.LFUS.trigger);
await flush();
assert.equal(returnBtns()[0].parentNode, footEl());
assert.equal(scrollState.y, 5000, 'Plan detail starts at the Plan location');
returnBtns()[0].click();
assert.equal(origin.body.parentNode, dialogEl().querySelector('.pvs-dialog-content'));
assert.equal(scrollState.y, before.scroll, 'return must restore candidate scroll');
fire(closeBtn());
assert.equal(document.activeElement, origin.trigger);
assert.equal(scrollState.y, before.scroll, 'Close must retain the original candidate scroll');
""", pre=_PRE["table"])
