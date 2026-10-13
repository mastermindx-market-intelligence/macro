"""US Risk Radar dialog focus: stacked overlays must keep Tab.

Runs the shipped `_tabStop` / `_trapTab` bodies. Fixtures are synthetic.
"""
from pathlib import Path

from tests.test_us_pullback_modal_integration import _node_raw

ROOT = Path(__file__).resolve().parents[1]


def _between(path: str, start: str, end: str) -> str:
    page = (ROOT / path).read_text()
    a = page.index(start)
    return page[a:page.index(end, a)]


# Dialog plus four overlays that legitimately sit above it. `page` is mutated
# per case so one sliced trap serves every overlay and the closed control.
_OVERLAY_JS = r"""
const assert = require('node:assert/strict');
const page = {rr: null, tr: null, hm: null};
const doc = {
  activeElement: null,
  getElementById(id) {
    if (id !== 'rr-modal-overlay') throw new Error('unexpected id ' + id);
    return page.rr;
  },
  querySelector(sel) {
    if (sel === '.rr-tr-overlay.is-open') {
      return (page.tr && page.tr.classes.has('is-open')) ? page.tr : null;
    }
    if (sel === '.hm-ov') return page.hm;
    throw new Error('unexpected selector ' + sel);
  },
};
function el(name, tag, classes) {
  const node = {
    name, tag, classes: new Set(classes || []), parentElement: null, children: [],
    tabIndex: 0,
    getClientRects() { return [{}]; },
    focus() { doc.activeElement = this; },
    contains(o) { for (let n = o; n; n = n.parentElement) if (n === this) return true; return false; },
    closest(sel) {
      if (sel === '[inert]' || sel === 'details:not([open])') return null;
      if (sel === '.lens-pop.open') {
        for (let n = this; n; n = n.parentElement) {
          if (n.classes.has('lens-pop') && n.classes.has('open')) return n;
        }
        return null;
      }
      throw new Error('unexpected closest ' + sel);
    },
    querySelector() { return null; },
    querySelectorAll(sel) {
      const parts = sel.split(','), out = [];
      const hit = c => parts.some(p => p === c.tag || p.startsWith(c.tag + ':')
                                  || (c.tag === 'a' && p === 'a[href]'));
      (function walk(n) { for (const c of n.children) { if (hit(c)) out.push(c); walk(c); } })(this);
      return out;
    },
  };
  node.classList = {contains(c) { return node.classes.has(c); }};
  return node;
}
function add(parent, child) { child.parentElement = parent; parent.children.push(child); return child; }
const dlg = el('dialog', 'div');
const first = add(dlg, el('close', 'button'));
const last = add(dlg, el('tail', 'button'));
const outside = el('outside', 'button');
function reset() { page.rr = null; page.tr = null; page.hm = null; doc.activeElement = null; }
function tab(from, shift) {
  doc.activeElement = from;
  const e = {key: 'Tab', shiftKey: !!shift, defaultPrevented: false,
             preventDefault() { this.defaultPrevented = true; }};
  trap(dlg, e);
  return e;
}
function stays(name, from) {
  const e = tab(from, false);
  assert.equal(e.defaultPrevented, false, name + ' Tab');
  assert.equal(doc.activeElement, from, name + ' Tab focus');
  const back = tab(from, true);
  assert.equal(back.defaultPrevented, false, name + ' Shift+Tab');
  assert.equal(doc.activeElement, from, name + ' Shift+Tab focus');
}
const src = require('node:fs').readFileSync(0, 'utf8');
const trap = new Function('document', src + '; return _trapTab;')(doc);

reset();
const rr = el('rr', 'div', ['open']);
page.rr = rr;
stays('rr-modal-overlay', add(rr, el('rr-btn', 'button')));

reset();
const tr = el('tr', 'div', ['rr-tr-overlay', 'is-open']);
page.tr = tr;
stays('rr-tr-overlay', add(tr, el('tr-btn', 'button')));

reset();
const hm = el('hm', 'div', ['hm-ov']);
page.hm = hm;
stays('hm-ov', add(hm, el('hm-btn', 'button')));

reset();
const lens = el('lens', 'div', ['lens-pop', 'open']);
stays('lens-pop', add(lens, el('lens-btn', 'button')));

// Closed or absent: focus behind the dialog is pulled back to the first stop.
reset();
page.rr = el('rr-closed', 'div', []);
page.tr = el('tr-closed', 'div', ['rr-tr-overlay']);
let e = tab(outside, false);
assert.equal(e.defaultPrevented, true, 'closed overlays Tab');
assert.equal(doc.activeElement, first, 'closed overlays focus');

reset();
e = tab(outside, false);
assert.equal(e.defaultPrevented, true, 'absent overlays Tab');
assert.equal(doc.activeElement, first, 'absent overlays focus');
"""


def test_stacked_overlays_keep_tab_and_stray_focus_still_returns():
    """Four overlays above an open US dialog own Tab; a bare stray focus does not."""
    src = _between("templates/dashboard.html.j2", "function _tabStop(el){", "function _prefReduced(")
    _node_raw(_OVERLAY_JS, src)
