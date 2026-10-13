"""China Risk Radar dialog focus lifecycle.

Runs the shipped cnxOpenDlg / cnxCloseDlg / keydown handlers. Fixtures are
synthetic. A fake clock stands in for setTimeout and requestAnimationFrame.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _between(start: str, end: str) -> str:
    page = (ROOT / "templates" / "china.html.j2").read_text()
    a = page.index(start)
    return page[a:page.index(end, a)]


# Open, then close, with the saved opener missing or disconnected. Focus must
# leave the dialog. A connected card opener is the control case.
_GONE_JS = r"""
const assert = require('node:assert/strict');
const src = require('node:fs').readFileSync(0, 'utf8');
let nextId = 1;
const timers = [];
const rafs = [];
global.setTimeout = (fn, ms) => {
  const id = nextId++;
  timers.push({id, ms: Number(ms) || 0, fn, dead: false});
  return id;
};
global.clearTimeout = (id) => {
  const t = timers.find(x => x.id === id);
  if (t) t.dead = true;
};
global.requestAnimationFrame = (fn) => { rafs.push(fn); return rafs.length; };
function flushRaf() {
  let guard = 0;
  while (rafs.length && guard++ < 12) {
    const batch = rafs.splice(0, rafs.length);
    for (const fn of batch) fn();
  }
}
function advance(ms) {
  let left = ms;
  while (left > 0) {
    const live = timers.filter(t => !t.dead);
    if (!live.length) return;
    let step = left;
    for (const t of live) if (t.ms < step) step = t.ms;
    left -= step;
    for (const t of timers) if (!t.dead) t.ms -= step;
    for (const t of timers.filter(x => !x.dead && x.ms <= 0)) { t.dead = true; t.fn(); }
  }
}
function makeClassList(initial) {
  const set = new Set(initial || []);
  return {
    contains(c) { return set.has(c); },
    add() { for (let i = 0; i < arguments.length; i++) set.add(arguments[i]); },
    remove() { for (let i = 0; i < arguments.length; i++) set.delete(arguments[i]); },
    toggle(c) { if (set.has(c)) set.delete(c); else set.add(c); },
  };
}
function boot(opts) {
  opts = opts || {};
  timers.length = 0;
  rafs.length = 0;
  const nodes = [];
  const doc = {
    activeElement: null,
    listeners: [],
    body: null,
    addEventListener(type, fn) { this.listeners.push({type, fn}); },
    getElementById(id) { return nodes.find(n => n.id === id) || null; },
    querySelector(sel) { return query(sel)[0] || null; },
    querySelectorAll(sel) { return query(sel); },
  };
  function el(o) {
    const node = {
      id: o.id || '', tag: o.tag || 'div', name: o.name || o.tag,
      classes: new Set(o.classes || []),
      attrs: Object.assign({}, o.attrs || {}),
      parentElement: null, children: [], listeners: [], style: {},
      tabIndex: o.tabIndex == null ? 0 : o.tabIndex,
      role: o.role || '',
      _connected: true,
      get isConnected() { return this._connected; },
      getClientRects() { return [{}]; },
      focus() { doc.activeElement = this; },
      contains(other) {
        for (let n = other; n; n = n.parentElement) if (n === this) return true;
        return false;
      },
      closest(sel) {
        for (let n = this; n; n = n.parentElement) if (match(n, sel)) return n;
        return null;
      },
      querySelector(sel) {
        const found = [];
        walk(this, sel, found);
        return found[0] || null;
      },
      querySelectorAll(sel) {
        const found = [];
        walk(this, sel, found);
        return found;
      },
      addEventListener(type, fn) { this.listeners.push({type, fn}); },
      removeEventListener(type, fn) {
        this.listeners = this.listeners.filter(l => l.fn !== fn || l.type !== type);
      },
      dispatchEvent(ev) {
        for (const l of this.listeners.slice()) if (l.type === ev.type) l.fn(ev);
      },
      click() { if (this.onClick) this.onClick(); },
    };
    node.classList = makeClassList(o.classes || []);
    nodes.push(node);
    return node;
  }
  function add(parent, child) {
    child.parentElement = parent;
    parent.children.push(child);
    return child;
  }
  function match(node, sel) {
    sel = sel.trim();
    if (!sel || sel === '*') return true;
    if (sel.indexOf(',') >= 0) return sel.split(',').some(part => match(node, part));
    let rest = sel;
    const nots = [];
    rest = rest.replace(/:not\(([^)]+)\)/g, (_, inner) => { nots.push(inner); return ''; });
    if (nots.some(inner => match(node, inner))) return false;
    const attrs = [];
    rest = rest.replace(/\[([^\]]+)\]/g, (_, inner) => { attrs.push(inner); return ''; });
    for (const attr of attrs) {
      const parts = attr.split('=');
      const key = parts[0];
      const want = parts.length > 1 ? parts[1].replace(/^"|"$/g, '') : null;
      const got = key === 'role' ? node.role : node.attrs[key];
      if (want == null) { if (got == null) return false; }
      else if (String(got) !== want) return false;
    }
    const bits = rest.split(/(?=\.)/).filter(Boolean);
    let tag = '';
    for (const bit of bits) {
      if (bit.charAt(0) === '#') {
        const idBits = bit.split('.');
        if (node.id !== idBits[0].slice(1)) return false;
        for (const extra of idBits.slice(1)) if (!node.classList.contains(extra)) return false;
      } else if (bit.charAt(0) === '.') {
        if (!node.classList.contains(bit.slice(1).split(':')[0])) return false;
      } else if (bit.indexOf(':') >= 0) {
        const pseudo = bit.split(':')[1];
        const t = bit.split(':')[0];
        if (t) tag = t;
        if (pseudo === 'disabled' && !node.disabled) return false;
      } else if (bit) {
        tag = bit;
      }
    }
    if (tag && node.tag !== tag) return false;
    return true;
  }
  function walk(root, sel, out) {
    for (const child of root.children) {
      if (match(child, sel)) out.push(child);
      walk(child, sel, out);
    }
  }
  function query(sel) {
    const out = [];
    for (const node of nodes) if (match(node, sel)) out.push(node);
    return out;
  }
  const body = el({tag: 'body', name: 'body'});
  doc.body = body;
  const risk = el({id: 'cnx-dlg-risk', classes: ['cnx-dlg'], name: 'risk'});
  const panel = add(risk, el({classes: ['cnx-dlg-panel'], name: 'panel'}));
  const closeBtn = add(panel, el({tag: 'button', classes: ['cnx-dlg-close'], name: 'close'}));
  add(panel, el({tag: 'button', name: 'tail'}));
  const backdrop = add(risk, el({classes: ['cnx-dlg-backdrop'], name: 'backdrop'}));
  const card = el({tag: 'div', classes: ['cnx-card'], role: 'button', name: 'card', tabIndex: 0});
  const location = {pathname: '/china.html', hash: opts.hash || ''};
  const history = {replaceState(_s, _t, url) {
    const i = String(url).indexOf('#');
    location.hash = i >= 0 ? url.slice(i) : '';
    location.pathname = i >= 0 ? url.slice(0, i) : url;
  }};
  const win = {scrollY: 480, mmPbExpire() {}, addEventListener() {}};
  doc.activeElement = opts.active === undefined ? card : opts.active;
  card.onClick = () => { if (win.cnxOpenDlg) win.cnxOpenDlg('cnx-dlg-risk'); };
  closeBtn.onClick = () => { if (win.cnxCloseDlg) win.cnxCloseDlg(); };
  backdrop.onClick = () => { if (win.cnxCloseDlg) win.cnxCloseDlg(); };
  new Function('document', 'window', 'history', 'location', src)(doc, win, history, location);
  return {doc, win, risk, panel, closeBtn, backdrop, card, body};
}
function finish(h, how) {
  if (how === 'escape') {
    h.doc.activeElement = h.doc.activeElement || h.closeBtn;
    const e = {key: 'Escape', target: h.doc.activeElement};
    for (const l of h.doc.listeners.slice()) if (l.type === 'keydown') l.fn(e);
  } else if (how === 'button') {
    h.closeBtn.click();
  } else {
    h.backdrop.click();
  }
  advance(1000);
}
function assertOutside(h, label) {
  assert.equal(h.risk.classList.contains('open'), false, label + ' closed');
  assert.equal(h.risk.classList.contains('cnx-closing'), false, label + ' not closing');
  const act = h.doc.activeElement;
  assert.ok(!act || !h.risk.contains(act), label + ' focus left the dialog');
  assert.equal(act, h.body, label + ' focus on body');
}
const which = process.env.CN_CASE;
if (which === 'none') {
  for (const how of ['escape', 'button', 'backdrop']) {
    const h = boot({active: null, hash: '#cnx-dlg-risk'});
    flushRaf();
    assert.equal(h.risk.classList.contains('open'), true, 'hash opened');
    assert.equal(h.doc.activeElement, h.closeBtn, 'focus entered on hash open');
    finish(h, how);
    assertOutside(h, 'no opener ' + how);
  }
} else if (which === 'detached') {
  for (const how of ['escape', 'button', 'backdrop']) {
    const h = boot({active: null});
    h.doc.activeElement = h.card;
    h.win.cnxOpenDlg('cnx-dlg-risk');
    flushRaf();
    h.card._connected = false;
    finish(h, how);
    assertOutside(h, 'detached opener ' + how);
  }
} else {
  throw new Error('CN_CASE');
}
"""


def _run(case: str) -> None:
    # The IIFE wrapper stays outside the slice. Stop before its closing `})();`.
    src = _between(
        "var _hmMounted=false;",
        "window.addEventListener('hashchange',cnxResolveHash);",
    )
    src += "window.addEventListener('hashchange',cnxResolveHash);"
    node = shutil.which("node")
    if not node:
        if os.environ.get("CI"):
            pytest.fail("Node is required in CI to execute the shipped dialog scripts")
        pytest.skip("Node is required to execute the shipped dialog scripts")
    env = dict(os.environ)
    env["CN_CASE"] = case
    result = subprocess.run(
        [node, "-e", _GONE_JS], input=src, text=True, capture_output=True, timeout=20, env=env,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_close_moves_focus_out_when_the_risk_dialog_has_no_opener():
    """Hash open with nothing focused, then Escape, the close button, or the backdrop.

    The close button must not keep focus inside the dialog after it shuts.
    """
    _run("none")


def test_close_moves_focus_out_when_the_opener_was_removed():
    """A disconnected opener cannot take focus back, so focus leaves the dialog."""
    _run("detached")
