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
  node.blur = function () {};
  node.click = function () { node.dispatchEvent({ type: 'click', target: node }); };
  node.querySelector = function (sel) { return queryAll(node, sel)[0] || null; };
  node.querySelectorAll = function (sel) { return queryAll(node, sel); };
  Object.defineProperty(node, 'firstChild', { get: function () { return node.childNodes[0] || null; } });
  Object.defineProperty(node, 'lastChild', { get: function () { return node.childNodes[node.childNodes.length - 1] || null; } });
  Object.defineProperty(node, 'children', { get: function () { return node.childNodes.slice(); } });
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
    get: function () { return node.textContent; },
    set: function (value) {
      // Stub-level innerHTML: parse a small subset (option/li/tr/button) into
      // real child nodes so renderSliceSelector / renderRerating populate the
      // DOM tree the way a real browser would. Anything else falls back to a
      // flat text representation.
      var raw = value == null ? '' : String(value);
      node.childNodes = [];
      var re = /<([a-z][a-z0-9]*)\b([^>]*)>([\s\S]*?)<\/\1>/gi;
      var m, lastIdx = 0;
      while ((m = re.exec(raw)) !== null) {
        if (m.index > lastIdx) {
          var txt = raw.slice(lastIdx, m.index).trim();
          if (txt) node.appendChild(makeNode('span', {}))._text = txt;
        }
        var tag = m[1].toLowerCase();
        var attrs = m[2] || '';
        var body = m[3] || '';
        var child = makeNode(tag, {});
        var attrRe = /([a-zA-Z][\w-]*)\s*=\s*"([^"]*)"/g;
        var am;
        while ((am = attrRe.exec(attrs)) !== null) {
          child.setAttribute(am[1], am[2]);
        }
        // Recurse for nested tags (simple single-level).
        child.innerHTML = body;
        node.appendChild(child);
        lastIdx = re.lastIndex;
      }
      if (lastIdx < raw.length) {
        var tail = raw.slice(lastIdx).trim();
        if (tail) node.appendChild(makeNode('span', {}))._text = tail;
      }
      node._text = '';
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

function matchSel(node, sel) {
  sel = String(sel || '').trim();
  if (!sel) return false;
  if (sel.charAt(0) === '#') return node.id === sel.slice(1);
  if (sel.charAt(0) === '.') return classSet(node.className).indexOf(sel.slice(1)) >= 0;
  var attr = sel.match(/^([a-z][\w-]*)?\[([^=\]]+)="([^"]*)"\]$/i);
  if (attr) {
    if (attr[1] && node.tagName !== attr[1].toUpperCase()) return false;
    return node.getAttribute(attr[2]) === attr[3];
  }
  var tagged = sel.match(/^([a-z][\w-]*)$/i);
  if (tagged) return node.tagName === tagged[1].toUpperCase();
  var combo = sel.match(/^([a-z][\w-]*)\.([\w-]+)$/i);
  if (combo) return node.tagName === combo[1].toUpperCase() && classSet(node.className).indexOf(combo[2]) >= 0;
  return false;
}

function walk(node, visit) {
  visit(node);
  node.childNodes.forEach(function (child) { walk(child, visit); });
}

function queryAll(root, selector) {
  var parts = String(selector || '').split(',').map(function (i) { return i.trim(); }).filter(Boolean);
  var found = [];
  parts.forEach(function (part) {
    var tokens = part.split(/\s+/);
    var pool = [root];
    tokens.forEach(function (token, index) {
      var next = [];
      pool.forEach(function (start) {
        walk(start, function (node) {
          if ((index === 0 ? true : node !== start) && matchSel(node, token)) next.push(node);
        });
      });
      pool = next;
    });
    pool.forEach(function (node) { if (found.indexOf(node) < 0) found.push(node); });
  });
  found.item = function (i) { return found[i]; };
  return found;
}

var byId = {};
function attach(node) { if (node.id) byId[node.id] = node; return node; }

var html = makeNode('html');
html.setAttribute('data-lang', scenario.lang || 'en');
var document = {
  documentElement: html,
  body: null,
  activeElement: null,
  querySelector: function (sel) { return queryAll(html, sel)[0] || null; },
  querySelectorAll: function (sel) { return queryAll(html, sel); },
  getElementById: function (id) { return byId[id] || null; },
  getElementsByClassName: function () { return []; },
  getElementsByTagName: function () { return []; },
  addEventListener: function () {},
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
sections.forEach(function (sid) {
  var sec = attach(makeNode('section', { id: sid }));
  sec.setAttribute('data-fi-mount', sid);
  main.appendChild(sec);
});

var mounts = [
  'what-changed-list', 'slice-select', 'rerating-steps', 'rerating-bridge',
  'falsifiers', 'conflict-list', 'view-tabs', 'view-panels', 'domain-grid',
  'coverage-eyebrow', 'atlas-gap',
  'exposure-thead', 'exposure-thead-more', 'exposure-rows', 'exposure-rows-more',
  'exposure-more', 'exposure-cards', 'exposure-cards-more', 'exposure-cards-list',
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
  var el = attach(makeNode(tag, { 'data-fi-mount': m }));
  el.hidden = false;
  main.appendChild(el);
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

var windowObj = {
  location: { hash: '' },
  history: { replaceState: function () {} },
  document: document,
  fetch: fetch,
  MDXAuth: null,
  matchMedia: function () { return { matches: false, addEventListener: function () {} }; },
  addEventListener: function () {},
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
    fetchCalls: fetchCalls.slice()
  };
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
  process.stdout.write(JSON.stringify({ first: snapshot(), second: null }));
}, function (error) {
  process.stderr.write(String(error && error.stack || error));
  process.exit(1);
});
