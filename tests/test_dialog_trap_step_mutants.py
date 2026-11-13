"""Killers for the dialog Tab-trap mutants the existing suites let survive.

Lane MT5's mutation survey ran 34 single-edit mutants over the two shipped
Tab traps (``_trapTab``/``_tabStop`` in templates/dashboard.html.j2 and
``_riskTrapTab``/``_riskTabStop``/``_RISK_STOPS`` in templates/china.html.j2)
against the five existing suites. 22 died. Ten survive because the current
fixtures cannot even express the difference — no fixture has a disabled
button, an anchor stop, a tabindex=0 div, an inert subtree, an empty dialog,
or a ``focus()`` that throws. One test here per survivor, each driving the
SHIPPED function bodies under node exactly like
``test_us_pullback_modal_integration.py`` does:

A8  / C6   drop the ``if(!focusable.length) return;`` guard -> empty-dialog tests
A9         ``button:not(:disabled)`` -> ``button``             -> disabled-button test
A10        drop the ``a[href]`` selector term                  -> anchor test
A12 / C10  drop the ``[tabindex]`` selector term               -> tabindex-div tests
A14 / C12  drop the ``[inert]`` stop filter                    -> inert tests
A25 / C23  move ``preventDefault()`` after the ``focus()`` call -> throwing-focus tests

Each test is proven FAIL-with-mutant and PASS-restored in the lane RETURN
(one summary line each). Two further survivors, A22/C20 — dropping
``i < 0 || `` from the forward branch — are EQUIVALENT, not survived: when
``i === -1`` the mutant evaluates ``i === n-1``, which is false because the
empty-list guard both versions keep means ``n >= 1``, so it falls through to
``i + 1 === 0`` — the exact target the dropped disjunct selects.
"""
from pathlib import Path

from tests.test_us_pullback_modal_integration import _between, _node_raw

# A fake document/element pair with MORE of the CSS-selector surface than the
# one in test_us_pullback_modal_integration.py: :disabled, [tabindex] and
# [inert] must be distinguishable, or the selector/filter mutants change
# nothing here either. focus() records into doc.activeElement, and an element
# with throwOnFocus set refuses focus — that is the only way to observe WHERE
# in the shipped tail the preventDefault() call sits.
FAKE_JS = r"""
const assert = require('node:assert/strict');
const doc = {activeElement: null,
  getElementById() { return null; },
  querySelector() { return null; }};
function matches(c, p) {
  p = p.trim();
  if (p === 'a[href]') return c.tag === 'a' && !!c.href;
  if (p === 'summary') return c.tag === 'summary';
  if (p === '[tabindex]:not([tabindex="-1"])')
    return c.attrs.tabindex !== undefined && c.attrs.tabindex !== '-1';
  const m = p.match(/^([a-z]+)(:not\(([^)]*)\))?$/);
  if (!m || m[1] !== c.tag) return false;
  if (m[3] === ':disabled') return !c.disabled;
  return true;
}
function el(tag, opts = {}) {
  return {tag, name: opts.name || tag, open: !!opts.open, shown: opts.shown !== false,
          disabled: !!opts.disabled, inert: !!opts.inert, href: opts.href,
          attrs: opts.tabindex !== undefined ? {tabindex: String(opts.tabindex)} : {},
          tabIndex: opts.tabIndex ?? (opts.tabindex !== undefined ? Number(opts.tabindex) : 0),
          throwOnFocus: false, children: [], parentElement: null, checkVisibility: opts.checkVisibility,
          getClientRects() { return this.shown ? [{}] : []; },
          focus() { if (this.throwOnFocus) throw new Error('focus refused'); doc.activeElement = this; },
          contains(o) { for (let n = o; n; n = n.parentElement) if (n === this) return true; return false; },
          closest(sel) {
            if (sel === '.lens-pop.open') return null;
            for (let n = this; n; n = n.parentElement) {
              if (sel === '[inert]' && n.inert) return n;
              if (sel === 'details:not([open])' && n.tag === 'details' && !n.open) return n;
            }
            return null;
          },
          querySelector(sel) {
            assert.equal(sel, ':scope > summary');
            return this.children.find(c => c.tag === 'summary') || null;
          },
          querySelectorAll(sel) {
            const parts = sel.split(','), out = [];
            const hit = c => parts.some(p => matches(c, p));
            (function walk(n) { for (const c of n.children) { if (hit(c)) out.push(c); walk(c); } })(this);
            return out;
          }};
}
function add(parent, child) { child.parentElement = parent; parent.children.push(child); return child; }
// The popup-shaped dialog: close button, an optional middle stop built by the
// caller, then the two closed disclosures whose summaries end the order.
function stdDialog(buildMiddle) {
  const dlg = el('div');
  dlg.classList = {contains(name) { return name === 'open'; }};
  const close = add(dlg, el('button', {name: 'close'}));
  const middle = buildMiddle ? buildMiddle(dlg, close) : null;
  const why = add(dlg, el('details'));
  const whySummary = add(why, el('summary', {name: 'why no estimate'}));
  add(why, el('a', {name: 'why link', href: '#why'}));
  const legacy = add(dlg, el('details'));
  const legacySummary = add(legacy, el('summary', {name: 'forward risk and drivers'}));
  return {dlg, close, middle, why, whySummary, legacy, legacySummary};
}
function bareDialog() {
  const dlg = el('div');
  dlg.classList = {contains(name) { return name === 'open'; }};
  return dlg;
}
function cnDialog(buildMiddle) {
  const d = stdDialog(buildMiddle);
  doc.querySelector = sel => {
    if (sel === '.hm-ov') return null;
    assert.equal(sel, '#cnx-dlg-risk.open:not(.cnx-closing)');
    return d.dlg;
  };
  return d;
}
function usTrap() {
  return new Function('document', require('node:fs').readFileSync(0, 'utf8') + '; return _trapTab;')(doc);
}
function cnTrap() {
  return new Function('document', require('node:fs').readFileSync(0, 'utf8') + '; return _riskTrapTab;')(doc);
}
function tabEv(shift = false) {
  return {key: 'Tab', shiftKey: shift, prevented: false, preventDefault() { this.prevented = true; }};
}
function usTab(trap, dlg, from, shift = false) {
  doc.activeElement = from;
  const e = tabEv(shift);
  trap(dlg, e);
  return e;
}
function cnTab(trap, from, shift = false) {
  doc.activeElement = from;
  const e = tabEv(shift);
  trap(e);
  return e;
}
"""


def _us_src() -> str:
    return _between("templates/dashboard.html.j2", "function _tabStop(el){", "function _prefReduced(")


def _cn_src() -> str:
    return _between("templates/china.html.j2", "function _riskTabStop(el){", "function cnxOpenDlg(")


def _run(body: str, src: str) -> None:
    _node_raw(FAKE_JS + body, src)


def test_us_trap_over_an_empty_dialog_is_neither_prevented_nor_stepped():
    """Kills A8 (drop the empty-list guard): with no stops the shipped trap must
    leave the Tab to the engine — the guard-less mutant indexes focusable[-1]
    and throws."""
    _run(r"""
const dlg = bareDialog();
const outside = el('button', {name: 'outside'});
const trap = usTrap();
const e = usTab(trap, dlg, outside);
assert.equal(e.prevented, false);
assert.equal(doc.activeElement, outside);
""", _us_src())


def test_us_trap_keeps_disabled_buttons_out_of_the_step_order():
    """Kills A9 (``button:not(:disabled)`` -> ``button``): a disabled button is
    not a stop, so a Tab from it is a stray-focus pull-back to the near end —
    not a step to its DOM neighbours."""
    _run(r"""
const d = stdDialog((dlg, close) => add(dlg, el('button', {name: 'off', disabled: true})));
const trap = usTrap();
let e = usTab(trap, d.dlg, d.middle, true);
assert.equal(e.prevented, true);
assert.equal(doc.activeElement, d.legacySummary);
e = usTab(trap, d.dlg, d.middle);
assert.equal(e.prevented, true);
assert.equal(doc.activeElement, d.close);
""", _us_src())


def test_us_trap_keeps_anchors_in_the_step_order():
    """Kills A10 (drop ``a[href]``): an anchor between the close button and the
    disclosures is a middle stop the trap must step onto, both directions."""
    _run(r"""
const d = stdDialog((dlg, close) => add(dlg, el('a', {name: 'method note', href: '#method'})));
const trap = usTrap();
let e = usTab(trap, d.dlg, d.close);
assert.equal(e.prevented, true);
assert.equal(doc.activeElement, d.middle);
e = usTab(trap, d.dlg, d.whySummary, true);
assert.equal(e.prevented, true);
assert.equal(doc.activeElement, d.middle);
""", _us_src())


def test_us_trap_counts_a_tabindex_zero_div_in_the_step_order():
    """Kills A12 (drop ``[tabindex]:not([tabindex="-1"])``): a tabindex=0 div is
    a stop; without the term the trap steps over it to the next element."""
    _run(r"""
const d = stdDialog((dlg, close) => add(dlg, el('div', {name: 'chart', tabindex: 0})));
const trap = usTrap();
const e = usTab(trap, d.dlg, d.close);
assert.equal(e.prevented, true);
assert.equal(doc.activeElement, d.middle);
""", _us_src())


def test_us_trap_skips_controls_under_an_inert_ancestor():
    """Kills A14 (drop the ``[inert]`` filter): a button under an inert wrapper
    is not a stop, so a Tab from it pulls focus back to the near end."""
    _run(r"""
const d = stdDialog((dlg) => {
  const wrap = add(dlg, el('div', {name: 'wrap', inert: true}));
  return add(wrap, el('button', {name: 'buried'}));
});
const trap = usTrap();
let e = usTab(trap, d.dlg, d.middle, true);
assert.equal(e.prevented, true);
assert.equal(doc.activeElement, d.legacySummary);
e = usTab(trap, d.dlg, d.middle);
assert.equal(e.prevented, true);
assert.equal(doc.activeElement, d.close);
""", _us_src())


def test_us_trap_prevents_default_before_moving_focus():
    """Kills A25 (preventDefault after focus()): the wrap target refuses focus
    and throws. The shipped tail has already cancelled the native Tab by then;
    the reordered mutant throws first, so the event ships un-prevented."""
    _run(r"""
const d = stdDialog();
d.close.throwOnFocus = true;
const trap = usTrap();
doc.activeElement = d.whySummary;
const e = tabEv(true);
try { trap(d.dlg, e); } catch (err) { assert.equal(String(err).includes('focus refused'), true); }
assert.equal(e.prevented, true);
assert.equal(doc.activeElement, d.whySummary);
""", _us_src())


def test_cn_trap_over_an_empty_dialog_is_neither_prevented_nor_stepped():
    """Kills C6 (drop the empty-list guard): same empty-dialog contract as the
    Macro page's trap."""
    _run(r"""
const dlg = bareDialog();
doc.querySelector = sel => {
  if (sel === '.hm-ov') return null;
  assert.equal(sel, '#cnx-dlg-risk.open:not(.cnx-closing)');
  return dlg;
};
const outside = el('button', {name: 'outside'});
const trap = cnTrap();
const e = cnTab(trap, outside);
assert.equal(e.prevented, false);
assert.equal(doc.activeElement, outside);
""", _cn_src())


def test_cn_trap_counts_a_tabindex_zero_div_in_the_step_order():
    """Kills C10 (drop the ``[tabindex]`` term of ``_RISK_STOPS``)."""
    _run(r"""
const d = cnDialog((dlg, close) => add(dlg, el('div', {name: 'chart', tabindex: 0})));
const trap = cnTrap();
const e = cnTab(trap, d.close);
assert.equal(e.prevented, true);
assert.equal(doc.activeElement, d.middle);
""", _cn_src())


def test_cn_trap_skips_controls_under_an_inert_ancestor():
    """Kills C12 (drop the ``[inert]`` filter of ``_riskTabStop``)."""
    _run(r"""
const d = cnDialog((dlg) => {
  const wrap = add(dlg, el('div', {name: 'wrap', inert: true}));
  return add(wrap, el('button', {name: 'buried'}));
});
const trap = cnTrap();
let e = cnTab(trap, d.middle, true);
assert.equal(e.prevented, true);
assert.equal(doc.activeElement, d.legacySummary);
e = cnTab(trap, d.middle);
assert.equal(e.prevented, true);
assert.equal(doc.activeElement, d.close);
""", _cn_src())


def test_cn_trap_prevents_default_before_moving_focus():
    """Kills C23 (preventDefault after focus()) on the China trap."""
    _run(r"""
const d = cnDialog();
d.close.throwOnFocus = true;
const trap = cnTrap();
doc.activeElement = d.whySummary;
const e = tabEv(true);
try { trap(e); } catch (err) { assert.equal(String(err).includes('focus refused'), true); }
assert.equal(e.prevented, true);
assert.equal(doc.activeElement, d.whySummary);
""", _cn_src())
