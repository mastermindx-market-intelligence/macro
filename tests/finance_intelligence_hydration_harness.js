#!/usr/bin/env node
'use strict';

/*
 * Finance Intelligence dossier hydration harness.
 *
 * Builds the seven §B section skeletons, the evidence drawer, the scrim,
 * and the page-local mount points; evals the runtime IIFE against a
 * scripted fetch table; snapshots the resulting main shell state.
 */

var fs = require('fs');
var scenario = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
var runtimeJs = fs.readFileSync(process.argv[3], 'utf8');

function classSet(name) {
  return String(name || '').trim().split(/\s+/).filter(Boolean);
}

// Every string a painter assigns to innerHTML, in order (item 1 scans these).
var htmlWrites = [];
var VOID_TAGS = { area: 1, base: 1, br: 1, col: 1, embed: 1, hr: 1, img: 1, input: 1,
                  link: 1, meta: 1, param: 1, source: 1, track: 1, wbr: 1 };
function decodeEntities(text) {
  return String(text).replace(/&(#x[0-9a-f]+|#[0-9]+|amp|lt|gt|quot|apos);/gi, function (_, ent) {
    var e = ent.toLowerCase();
    if (e === 'amp') return '&';
    if (e === 'lt') return '<';
    if (e === 'gt') return '>';
    if (e === 'quot') return '"';
    if (e === 'apos') return "'";
    return String.fromCharCode(e.charAt(1) === 'x' ? parseInt(e.slice(2), 16) : parseInt(e.slice(1), 10));
  });
}
function escText(text) { return String(text).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }
function escAttr(text) { return escText(text).replace(/"/g, '&quot;'); }
function makeText(text) {
  var t = makeNode('#text');
  t.nodeType = 3;
  t._text = text;
  return t;
}
// Stack-based parser: nested elements, void tags, quoted attributes, text nodes.
function parseHtmlInto(parent, raw) {
  var stack = [parent];
  var re = /<!--[\s\S]*?-->|<\/([a-zA-Z][\w-]*)\s*>|<([a-zA-Z][\w-]*)((?:[^>"']|"[^"]*"|'[^']*')*)>|([^<]+)|</g;
  var m;
  while ((m = re.exec(raw)) !== null) {
    var top = stack[stack.length - 1];
    if (m[1]) {
      var closing = m[1].toUpperCase();
      for (var i = stack.length - 1; i > 0; i -= 1) {
        if (stack[i].tagName === closing) { stack.length = i; break; }
      }
    } else if (m[2]) {
      var tag = m[2].toLowerCase();
      var attrText = m[3] || '';
      var child = makeNode(tag, {});
      var attrRe = /([^\s=\/]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+)))?/g;
      var am;
      while ((am = attrRe.exec(attrText)) !== null) {
        var value = am[2] != null ? am[2] : am[3] != null ? am[3] : am[4] != null ? am[4] : '';
        if (am[1] === 'hidden') { child.hidden = true; continue; }
        child.setAttribute(am[1], decodeEntities(value));
      }
      top.appendChild(child);
      if (!VOID_TAGS[tag] && !/\/\s*$/.test(attrText)) stack.push(child);
    } else if (m[4] != null) {
      top.appendChild(makeText(decodeEntities(m[4])));
    } else if (m[0] === '<') {
      top.appendChild(makeText('<'));
    }
  }
}
function serializeNode(node) {
  if (node.nodeType === 3) return escText(node._text || '');
  var tag = node.tagName.toLowerCase();
  var out = '<' + tag;
  if (node.className) out += ' class="' + escAttr(node.className) + '"';
  if (node.id) out += ' id="' + escAttr(node.id) + '"';
  Object.keys(node.attributes).forEach(function (name) {
    if (name === 'class' || name === 'id' || name === 'hidden') return;
    out += ' ' + name + '="' + escAttr(node.attributes[name]) + '"';
  });
  Object.keys(node.dataset).forEach(function (key) {
    var name = 'data-' + key.replace(/[A-Z]/g, function (ch) { return '-' + ch.toLowerCase(); });
    if (!Object.prototype.hasOwnProperty.call(node.attributes, name)) out += ' ' + name + '="' + escAttr(node.dataset[key]) + '"';
  });
  if (node.hidden) out += ' hidden';
  out += '>';
  if (VOID_TAGS[tag]) return out;
  return out + serializeChildren(node) + '</' + tag + '>';
}
function serializeChildren(node) {
  if (!node.childNodes.length) return escText(node._text || '');
  return node.childNodes.map(serializeNode).join('');
}
function isConnected(node) {
  for (var n = node; n; n = n.parentNode) if (n === html) return true;
  return false;
}

function makeNode(tag, attrs) {
  attrs = attrs || {};
  var node = {
    tagName: String(tag || 'div').toUpperCase(),
    id: attrs.id || '',
    name: attrs.name || '',
    type: attrs.type || '',
    className: attrs.class || attrs.className || '',
    hidden: !!attrs.hidden,
    disabled: false,
    value: attrs.value || '',
    placeholder: '',
    tabIndex: 0,
    parentNode: null,
    childNodes: [],
    style: {},
    dataset: {},
    attributes: {},
    listeners: {},
    label: '',
    selectedIndex: 0
  };
  node.classList = {
    add: function (n) {
      var p = classSet(node.className);
      if (p.indexOf(n) < 0) p.push(n);
      node.className = p.join(' ');
    },
    remove: function (n) {
      node.className = classSet(node.className).filter(function (i) { return i !== n; }).join(' ');
    },
    toggle: function (n, force) {
      var has = classSet(node.className).indexOf(n) >= 0;
      var on = force == null ? !has : !!force;
      if (on) node.classList.add(n); else node.classList.remove(n);
    },
    contains: function (n) { return classSet(node.className).indexOf(n) >= 0; }
  };
  node.setAttribute = function (name, value) {
    value = String(value);
    node.attributes[name] = value;
    if (name === 'id') node.id = value;
    if (name === 'class') node.className = value;
    if (name.slice(0, 5) === 'data-') node.dataset[name.slice(5).replace(/-([a-z])/g, function (_, ch) { return ch.toUpperCase(); })] = value;
  };
  node.getAttribute = function (name) {
    if (name === 'id') return node.id || null;
    if (name === 'class') return node.className || null;
    if (Object.prototype.hasOwnProperty.call(node.attributes, name)) return node.attributes[name];
    if (name.slice(0, 5) === 'data-') {
      var key = name.slice(5).replace(/-([a-z])/g, function (_, ch) { return ch.toUpperCase(); });
      return node.dataset[key] == null ? null : String(node.dataset[key]);
    }
    return null;
  };
  node.removeAttribute = function (name) {
    delete node.attributes[name];
    if (name.slice(0, 5) === 'data-') {
      var key = name.slice(5).replace(/-([a-z])/g, function (_, ch) { return ch.toUpperCase(); });
      delete node.dataset[key];
    }
  };
  node.appendChild = function (child) {
    if (child.parentNode) child.parentNode.removeChild(child);
    child.parentNode = node;
    node.childNodes.push(child);
    return child;
  };
  node.removeChild = function (child) {
    node.childNodes = node.childNodes.filter(function (i) { return i !== child; });
    child.parentNode = null;
    return child;
  };
  node.insertBefore = function (child, ref) {
    if (!ref) return node.appendChild(child);
    if (child.parentNode) child.parentNode.removeChild(child);
    var at = node.childNodes.indexOf(ref);
    if (at < 0) throw new Error('insertBefore: reference is not a child');
    child.parentNode = node;
    node.childNodes.splice(at, 0, child);
    return child;
  };
  node.matches = function (sel) {
    return String(sel).split(',').some(function (part) { return matchSel(node, part.trim()); });
  };
  node.closest = function (sel) {
    for (var n = node; n && n.tagName && n.nodeType !== 9; n = n.parentNode) {
      if (n.matches && n.matches(sel)) return n;
    }
    return null;
  };
  Object.defineProperty(node, 'nextSibling', { get: function () {
    var p = node.parentNode; if (!p) return null;
    return p.childNodes[p.childNodes.indexOf(node) + 1] || null;
  } });
  Object.defineProperty(node, 'previousSibling', { get: function () {
    var p = node.parentNode; if (!p) return null;
    return p.childNodes[p.childNodes.indexOf(node) - 1] || null;
  } });
  Object.defineProperty(node, 'parentElement', { get: function () { return node.parentNode; } });
  Object.defineProperty(node, 'isConnected', { get: function () { return isConnected(node); } });
  node.contains = function (other) {
    if (other === node) return true;
    return node.childNodes.some(function (c) { return c.contains && c.contains(other); });
  };
  node.addEventListener = function (name, fn) {
    (node.listeners[name] = node.listeners[name] || []).push(fn);
  };
  node.removeEventListener = function (name, fn) {
    node.listeners[name] = (node.listeners[name] || []).filter(function (i) { return i !== fn; });
  };
  node.dispatchEvent = function (event) {
    event = event || {};
    event.target = event.target || node;
    event.currentTarget = node;
    event.preventDefault = event.preventDefault || function () { event.defaultPrevented = true; };
    (node.listeners[event.type || event] || []).forEach(function (fn) { fn.call(node, event); });
  };
  node.focus = function () { document.activeElement = node; };
  node.nodeType = 1;
  node.blur = function () {};
  node.click = function () { node.dispatchEvent({ type: 'click', target: node }); };
  node.querySelector = function (sel) { return queryAll(node, sel)[0] || null; };
  node.querySelectorAll = function (sel) { return queryAll(node, sel); };
  Object.defineProperty(node, 'firstChild', { get: function () { return node.childNodes[0] || null; } });
  Object.defineProperty(node, 'lastChild', { get: function () { return node.childNodes[node.childNodes.length - 1] || null; } });
  Object.defineProperty(node, 'children', { get: function () { return node.childNodes.filter(function (c) { return c.nodeType !== 3; }); } });
  Object.defineProperty(node, 'options', {
    get: function () {
      var out = [];
      node.childNodes.forEach(function (child) {
        if (child.tagName === 'OPTION') out.push(child);
      });
      return out;
    }
  });
  Object.defineProperty(node, 'textContent', {
    get: function () {
      if (!node.childNodes.length) return node._text || '';
      return node.childNodes.map(function (c) { return c.textContent; }).join('');
    },
    set: function (value) {
      node.childNodes = [];
      node._text = value == null ? '' : String(value);
    }
  });
  Object.defineProperty(node, 'innerHTML', {
    get: function () { return serializeChildren(node); },
    set: function (value) {
      var raw = value == null ? '' : String(value);
      htmlWrites.push(raw);
      node.childNodes.forEach(function (c) { c.parentNode = null; });
      node.childNodes = [];
      node._text = '';
      parseHtmlInto(node, raw);
    }
  });
  Object.defineProperty(node, 'offsetParent', { get: function () { return node.hidden ? null : node.parentNode || document.body; } });
  Object.keys(attrs).forEach(function (key) {
    if (key === 'class' || key === 'className' || key === 'id' || key === 'hidden' || key === 'value' || key === 'type') return;
    node.setAttribute(key, attrs[key]);
  });
  if (attrs.id) node.id = attrs.id;
  return node;
}

// One compound selector: an optional tag, then any mix of #id, .class, [attr],
// [attr="v"] and :not(<those>). Anything else THROWS: a selector the harness
// cannot evaluate used to match nothing, which is how `.fi-view-tab[data-view=…]`
// (the langchange focus restore) and `button:not([disabled])` (the drawer's
// focus trap) went untested until T11 round 3.
var SIMPLE = '#[\\w-]+|\\.[\\w-]+|\\[[\\w-]+(?:="[^"]*")?\\]';
var PART = new RegExp(SIMPLE + '|:not\\((?:' + SIMPLE + ')+\\)', 'g');
var COMPOUND = new RegExp('^([a-z][\\w-]*|\\*)?((?:' + SIMPLE + '|:not\\((?:' + SIMPLE + ')+\\))*)$', 'i');
function matchSimple(node, p) {
  if (p.slice(0, 5) === ':not(') {
    return !p.slice(5, -1).match(new RegExp(SIMPLE, 'g')).every(function (q) { return matchSimple(node, q); });
  }
  if (p.charAt(0) === '#') return node.id === p.slice(1);
  if (p.charAt(0) === '.') return classSet(node.className).indexOf(p.slice(1)) >= 0;
  var a = p.match(/^\[([\w-]+)(?:="([^"]*)")?\]$/);
  var value = node.getAttribute(a[1]);
  return a[2] === undefined ? value !== null : value === a[2];
}
function matchSel(node, sel) {
  sel = String(sel || '').trim();
  var m = sel.match(COMPOUND);
  if (!sel || !m) throw new Error('harness cannot evaluate selector: ' + sel);
  if (!node || !node.tagName) return false;
  if (m[1] && m[1] !== '*' && node.tagName !== m[1].toUpperCase()) return false;
  return (m[2].match(PART) || []).every(function (p) { return matchSimple(node, p); });
}

function walk(node, visit) {
  visit(node);
  node.childNodes.forEach(function (child) { walk(child, visit); });
}

// Selector lists of compound selectors joined by descendant (space) or child
// (>) combinators. Like the DOM: only DESCENDANTS of root match, and results
// come back in document order.
function queryAll(root, selector) {
  var hits = [];
  String(selector || '').split(',').map(function (i) { return i.trim(); }).filter(Boolean).forEach(function (part) {
    var pool = [root];
    var child = false;
    part.replace(/\s*>\s*/g, ' > ').split(/\s+/).forEach(function (token) {
      if (token === '>') { child = true; return; }
      var next = [];
      pool.forEach(function (start) {
        var candidates = [];
        if (child) candidates = start.childNodes || [];
        else walk(start, function (node) { if (node !== start) candidates.push(node); });
        candidates.forEach(function (node) {
          if (next.indexOf(node) < 0 && matchSel(node, token)) next.push(node);
        });
      });
      pool = next;
      child = false;
    });
    pool.forEach(function (node) { if (hits.indexOf(node) < 0) hits.push(node); });
  });
  var found = [];
  walk(root, function (node) { if (hits.indexOf(node) >= 0) found.push(node); });
  found.item = function (i) { return found[i]; };
  return found;
}

var byId = {};
var docListeners = {};
var winListeners = {};
function makeEvent(type, extra) {
  var ev = { type: type, defaultPrevented: false };
  ev.preventDefault = function () { ev.defaultPrevented = true; };
  Object.keys(extra || {}).forEach(function (k) { ev[k] = extra[k]; });
  return ev;
}
function fireDoc(type, extra) {
  var ev = makeEvent(type, extra);
  (docListeners[type] || []).slice().forEach(function (fn) { fn(ev); });
  return ev;
}
function fireWin(type) { (winListeners[type] || []).slice().forEach(function (fn) { fn({ type: type }); }); }
function attach(node) { if (node.id) byId[node.id] = node; return node; }

var html = makeNode('html');
html.setAttribute('data-lang', scenario.lang || 'en');
var document = {
  documentElement: html,
  body: null,
  activeElement: null,
  querySelector: function (sel) { return queryAll(html, sel)[0] || null; },
  querySelectorAll: function (sel) { return queryAll(html, sel); },
  getElementById: function (id) {
    var hit = null;
    walk(html, function (n) { if (!hit && n.id === id) hit = n; });
    return hit;
  },
  getElementsByClassName: function () { return []; },
  getElementsByTagName: function () { return []; },
  addEventListener: function (type, fn) { (docListeners[type] = docListeners[type] || []).push(fn); },
  createElement: function (tag) { return makeNode(tag); },
  createElementNS: function (_ns, tag) { return makeNode(tag); },
  readyState: 'complete'
};
var body = makeNode('body');
body.className = 'fi-page';
html.appendChild(body);
document.body = body;

var siteNav = attach(makeNode('nav', { id: 'site-nav', class: 'site-nav' }));
body.appendChild(siteNav);

var main = attach(makeNode('main', { id: 'fi-main', class: 'fi-shell' }));
main.setAttribute('data-fi-mount', 'shell');
body.appendChild(main);

// hero mounts
[
  'hero-asof', 'hero-asof-zh', 'hero-cutoff', 'hero-cutoff-zh',
  'hero-freshness', 'hero-outer'
].forEach(function (m) {
  var span = attach(makeNode('span', { 'data-fi-mount': m }));
  span.hidden = true;
  main.appendChild(span);
});

// seven L1 sections + their mounts
var sections = ['what-changed', 'rerating-map', 'system-map', 'subtheme-atlas',
                'company-exposure', 'macro-matrix', 'constraint-map'];
var sectionOf = {};
sections.forEach(function (sid) {
  var sec = attach(makeNode('section', { id: sid, class: 'fi-section' }));
  sec.setAttribute('data-fi-mount', sid);
  var head = makeNode('header', { class: 'fi-section-head' });
  head.appendChild(makeNode('h2', { class: 'fi-section-title' }));
  sec.appendChild(head);
  main.appendChild(sec);
  sectionOf[sid] = sec;
});
// Mount -> owning section, as templates/finance_intelligence.html.j2 nests them.
function homeOf(mount) {
  if (mount === 'what-changed-list') return sectionOf['what-changed'];
  if (/^(slice-select|rerating-|falsifiers|conflict)/.test(mount)) return sectionOf['rerating-map'];
  if (/^view-/.test(mount)) return sectionOf['system-map'];
  if (/^(coverage-eyebrow|domain-grid|atlas-gap)$/.test(mount)) return sectionOf['subtheme-atlas'];
  if (/^exposure-/.test(mount)) return sectionOf['company-exposure'];
  if (/^macro-/.test(mount)) return sectionOf['macro-matrix'];
  if (mount === 'constraint-list') return sectionOf['constraint-map'];
  return main;
}

var mounts = [
  'what-changed-list', 'slice-select', 'rerating-steps', 'rerating-bridge',
  'falsifiers', 'conflict-list', 'view-tabs', 'view-panels', 'domain-grid',
  'coverage-eyebrow', 'atlas-gap',
  'exposure-thead', 'exposure-thead-more', 'exposure-rows', 'exposure-rows-more',
  'exposure-more', 'exposure-cards',
  'macro-thead', 'macro-thead-more', 'macro-rows', 'macro-rows-more', 'macro-more', 'macro-cards',
  'constraint-list', 'provenance',
  'notice', 'notice-en', 'notice-zh'
];
mounts.forEach(function (m) {
  var tag = m.indexOf('thead') >= 0 ? 'thead' :
            m.indexOf('rows') >= 0 ? 'tbody' :
            m.indexOf('cards') >= 0 ? 'ul' :
            m.indexOf('select') >= 0 ? 'select' :
            m.indexOf('tabs') >= 0 ? 'div' : 'div';
  var el = attach(makeNode(tag, m === 'slice-select' ? { 'data-fi-mount': m, id: 'fi-slice-select' } : { 'data-fi-mount': m }));
  el.hidden = false;
  homeOf(m).appendChild(el);
});

// Phone rows 9..N live in a <details class="fi-disc"> sibling of the first card list,
// exactly as templates/finance_intelligence.html.j2 nests them (item 9).
[['company-exposure', 'exposure-cards-more', 'exposure-cards-list', 'fi-exposure-cards-more', 'fi-exposure-cards'],
 ['macro-matrix', 'macro-cards-more', 'macro-cards-list', 'fi-macro-cards-more', 'fi-macro-cards']].forEach(function (d) {
  var det = attach(makeNode('details', { class: 'fi-disc ' + d[3], 'data-fi-mount': d[1] }));
  det.hidden = true;
  det.appendChild(makeNode('summary', {}));
  det.appendChild(attach(makeNode('ul', { class: d[4], 'data-fi-mount': d[2] })));
  sectionOf[d[0]].appendChild(det);
});

var sliceSelect = byId['fi-slice-select'] || (function () {
  var s = attach(makeNode('select', { id: 'fi-slice-select' }));
  s.setAttribute('data-fi-mount', 'slice-select');
  main.appendChild(s);
  return s;
})();

// evidence drawer aside + scrim
var drawer = attach(makeNode('aside', { id: 'evidence-drawer', class: 'fi-drawer', hidden: true, tabindex: -1 }));
drawer.setAttribute('role', 'dialog');
drawer.setAttribute('aria-modal', 'true');
body.appendChild(drawer);
['evidence-empty', 'evidence-private-notice', 'evidence-fields'].forEach(function (m) {
  var tag = m === 'evidence-fields' ? 'dl' : 'p';
  var el = attach(makeNode(tag, { 'data-fi-mount': m }));
  el.hidden = true;
  drawer.appendChild(el);
});
var closeBtn = attach(makeNode('button', { id: 'fi-close-evidence', type: 'button' }));
drawer.appendChild(closeBtn);
var scrim = attach(makeNode('div', { id: 'fi-scrim', class: 'fi-scrim', hidden: true }));
body.appendChild(scrim);

// ──────────────────────────────────────────────────────────────────────────
// fetch stub
// ──────────────────────────────────────────────────────────────────────────
var fetchCalls = [];
function fetch(url) {
  fetchCalls.push(String(url));
  var route = (scenario.routes || {})['__default__'] || {};
  var status = route.status == null ? 200 : route.status;
  var body = route.body == null ? '' : String(route.body);
  var contentType = route.contentType || (status === 200 ? 'application/json' : 'application/json');
  var headers = { get: function (n) { return String(n).toLowerCase() === 'content-type' ? contentType : null; } };
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status: status,
    headers: headers,
    text: function () { return Promise.resolve(body); },
    json: function () { return Promise.resolve(JSON.parse(body)); }
  });
}

// Like a browser, assigning a new location.hash queues ONE hashchange task;
// the page's evidence triggers open the drawer through it.
var hashValue = scenario.hash || '';
var locationObj = {};
Object.defineProperty(locationObj, 'hash', {
  get: function () { return hashValue; },
  set: function (value) {
    value = String(value);
    if (value && value.charAt(0) !== '#') value = '#' + value;
    if (value === hashValue) return;
    hashValue = value;
    setTimeout(function () { fireWin('hashchange'); }, 0);
  }
});

var windowObj = {
  location: locationObj,
  history: { replaceState: function () {} },
  document: document,
  fetch: fetch,
  MDXAuth: null,
  matchMedia: function () { return { matches: false, addEventListener: function () {} }; },
  addEventListener: function (type, fn) { (winListeners[type] = winListeners[type] || []).push(fn); },
  innerWidth: 1440,
  requestAnimationFrame: function (fn) { return setTimeout(fn, 0); }
};
windowObj.window = windowObj;
global.document = document;
global.window = windowObj;
global.fetch = fetch;
global.location = windowObj.location;
global.history = windowObj.history;
global.HTMLElement = function () {};
global.Node = function () {};

// runtime JS resolves FI_READ_URL from <main data-fi-read-url>; bind the
// stub URL the harness's fetch table can resolve (the shipped page binds nothing
// until integration and renders the not-connected notice instead).
(function () { var m = document.getElementById('fi-main'); if (m) m.setAttribute('data-fi-read-url', '/__fi_stub__'); })();
eval(runtimeJs);

function snapshot() {
  var noticeEl = document.querySelector('[data-fi-mount="notice"]');
  var noticeEnEl = document.querySelector('[data-fi-mount="notice-en"]');
  var noticeZhEl = document.querySelector('[data-fi-mount="notice-zh"]');
  var reratingStepsEl = document.querySelector('[data-fi-mount="rerating-steps"]');
  var exposureRowsEl = document.querySelector('[data-fi-mount="exposure-rows"]');
  var atlasGridEl = document.querySelector('[data-fi-mount="domain-grid"]');
  var sliceSel = document.getElementById ? document.getElementById('fi-slice-select') : byId['fi-slice-select'];
  return {
    noticeHidden: !!(noticeEl && !noticeEl.hidden),
    noticeEn: (noticeEnEl && noticeEnEl.textContent) || '',
    noticeZh: (noticeZhEl && noticeZhEl.textContent) || '',
    reratingStepCount: (function () {
      if (!reratingStepsEl) return 0;
      var count = 0;
      walk(reratingStepsEl, function (node) {
        if (node === reratingStepsEl) return;
        if (node.tagName === 'LI' && /fi-rerating-step/.test(node.className || '')) count += 1;
      });
      return count;
    })(),
    exposureRowCount: (function () {
      if (!exposureRowsEl) return 0;
      var count = 0;
      walk(exposureRowsEl, function (node) {
        if (node === exposureRowsEl) return;
        if (node.tagName === 'TR') count += 1;
      });
      return count;
    })(),
    heroChipAria: ['hero-freshness', 'hero-outer'].map(function (mount) {
      var el = document.querySelector('[data-fi-mount="' + mount + '"]');
      return (el && el.getAttribute('aria-label')) || '';
    }),
    evidenceAriaLabels: (function () {
      var labels = [];
      ['rerating-steps', 'what-changed-list', 'conflict-list', 'constraint-list'].forEach(function (mount) {
        var root = document.querySelector('[data-fi-mount="' + mount + '"]');
        if (!root) return;
        walk(root, function (node) {
          if (node !== root && /fi-step-evidence/.test(node.className || '')) labels.push(node.getAttribute('aria-label') || '');
        });
      });
      return labels;
    })(),
    atlasCardCount: (function () {
      if (!atlasGridEl) return 0;
      var count = 0;
      walk(atlasGridEl, function (node) {
        if (node === atlasGridEl) return;
        if (/fi-slice/.test(node.className || '')) count += 1;
      });
      return count;
    })(),
    sliceOptions: (function () {
      var sel = sliceSel || byId['fi-slice-select'];
      return sel ? sel.childNodes.filter(function (c) { return c.tagName === 'OPTION'; }).length : 0;
    })(),
    fetchCalls: fetchCalls.slice(),
    // The whole live document, serialised, plus every painter write — the
    // Python side parses these with html.parser for structural assertions.
    dom: serializeNode(html),
    htmlWrites: htmlWrites.slice(),
    active: describeActive()
  };
}

var marks = { focused: null, pressed: null };
function describeActive() {
  var a = document.activeElement;
  if (!a) return null;
  return {
    tag: a.tagName.toLowerCase(),
    className: a.className || '',
    dataView: a.getAttribute ? a.getAttribute('data-view') : null,
    tabindex: a.getAttribute ? a.getAttribute('tabindex') : null,
    ariaSelected: a.getAttribute ? a.getAttribute('aria-selected') : null,
    connected: isConnected(a),
    isPriorFocus: !!marks.focused && a === marks.focused,
    isPressed: !!marks.pressed && a === marks.pressed,
    id: a.id || null
  };
}

// Scripted interactions after the first paint: each action is one user-level
// event the runtime listens for. `press` focuses then clicks, and the click
// reaches the element's own listeners and then the document (the page binds
// evidence triggers by delegation). `tick` yields one macrotask, so the
// drawer's requestAnimationFrame focus move runs before the next action.
function runAction(a) {
  if (a.do === 'tick') return new Promise(function (resolve) { setTimeout(resolve, 0); });
  if (a.do === 'clickTab' || a.do === 'focusTab') {
    var tab = document.querySelectorAll('.fi-view-tab')[a.index];
    if (!tab) throw new Error('no .fi-view-tab at index ' + a.index);
    if (a.do === 'clickTab') tab.click();
    tab.focus();
    marks.focused = tab;
  } else if (a.do === 'focus') {
    var el = document.querySelector(a.selector);
    if (!el) throw new Error('no element for ' + a.selector);
    el.focus();
    marks.focused = el;
  } else if (a.do === 'press') {
    var target = document.querySelector(a.selector);
    if (!target) throw new Error('no element for ' + a.selector);
    target.focus();
    marks.pressed = target;
    target.dispatchEvent({ type: 'click', target: target });
    fireDoc('click', { target: target });
  } else if (a.do === 'key') {
    fireDoc('keydown', { key: a.key, shiftKey: !!a.shiftKey, target: document.activeElement });
  } else if (a.do === 'lang') {
    html.setAttribute('data-lang', a.lang);
    fireDoc('langchange');
  } else if (a.do === 'langchange') {
    fireDoc('langchange');
  } else {
    throw new Error('unknown action ' + a.do);
  }
  return null;
}
function runActions(actions) {
  return (actions || []).reduce(function (chain, a) {
    return chain.then(function () { return runAction(a); });
  }, Promise.resolve());
}

function settled() {
  // Settled = fetch was made AND either the notice was populated OR the
  // hydrated document landed in the DOM. Either signal terminates the wait.
  if (fetchCalls.length === 0) return false;
  var notice = document.querySelector('[data-fi-mount="notice-en"]');
  if (notice && notice.textContent && notice.textContent.length) return true;
  // Slice options bound means hydration ran end-to-end.
  var sel = byId['fi-slice-select'];
  if (sel) {
    var options = sel.childNodes.filter(function (c) { return c.tagName === 'OPTION'; });
    if (options.length > 0) return true;
  }
  // Notice span visible (locked/updating/etc.) is also a settled state.
  var noticeOuter = document.querySelector('[data-fi-mount="notice"]');
  if (noticeOuter && noticeOuter.hidden === false) return true;
  return false;
}

function waitFor(predicate, leftover) {
  leftover = leftover == null ? 80 : leftover;
  return new Promise(function (resolve, reject) {
    function tick() {
      if (predicate()) return resolve();
      if (leftover <= 0) return reject(new Error('timed out waiting for hydration'));
      leftover -= 1;
      setTimeout(tick, 0);
    }
    tick();
  });
}

waitFor(settled).then(function () {
  var first = snapshot();
  if (!scenario.actions) return { first: first, second: null };
  return runActions(scenario.actions).then(function () { return { first: first, second: snapshot() }; });
}).then(function (out) {
  process.stdout.write(JSON.stringify(out));
}, function (error) {
  process.stderr.write(String(error && error.stack || error));
  process.exit(1);
});
