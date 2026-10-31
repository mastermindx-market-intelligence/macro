"""US Risk Radar Escape: the document capture listener closes dlg-risk.

Runs the shipped dialog script from ``var _dlgActive`` through the listener
that ends at the alert deep-link comment. The lifecycle suite stops before
that listener, so these cases dispatch it. Fixtures are synthetic.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_START = "var _dlgActive = null;"
_END = "/* ── Alert deep-link resolution"


def _slice(path: str, start: str, end: str) -> str:
    page = (ROOT / path).read_text()
    at = page.index(start)
    return page[at:page.index(end, at)]


# Same timer/DOM stand-in as tests/test_us_dialog_focus_lifecycle.py, plus a
# capture flag on document.addEventListener and stopImmediatePropagation.
_ESCAPE_JS = r"""
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
  while (rafs.length && guard++ < 10) {
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
  };
}
function boot() {
  const state = {rr: null, tr: null};
  const doc = {
    activeElement: null,
    listeners: [],
    documentElement: {classList: makeClassList(), style: {}},
    body: {classList: makeClassList(['page-macro']), style: {}},
    addEventListener(type, fn, capture) {
      this.listeners.push({type, fn, capture: capture === true});
    },
    removeEventListener(type, fn) {
      this.listeners = this.listeners.filter(l => l.type !== type || l.fn !== fn);
    },
    getElementById(id) {
      if (id === 'dlg-risk') return dlg;
      if (id === 'rr-modal-overlay') return state.rr;
      return null;
    },
    querySelector(sel) {
      if (sel === '.rr-tr-overlay') return state.tr;
      if (sel === '.mx5-hm-stage' || sel === '.rr-tr-overlay.is-open' || sel === '.hm-ov') return null;
      throw new Error('document.querySelector ' + sel);
    },
  };
  function el(name, tag, classes) {
    const node = {
      name, tag, classes: new Set(classes || []),
      parentElement: null, parentNode: null, children: [],
      listeners: [], attrs: {}, style: {}, tabIndex: 0, disabled: false, onclick: null,
      getClientRects() { return [{}]; },
      focus() { doc.activeElement = this; },
      contains(o) { for (let n = o; n; n = n.parentElement) if (n === this) return true; return false; },
      closest(sel) {
        if (sel === '[inert]' || sel === 'details:not([open])' || sel === '.lens-pop.open') return null;
        throw new Error('closest ' + sel);
      },
      querySelector(sel) {
        let found = null;
        (function walk(n) {
          for (const c of n.children) {
            if (found) return;
            if (sel.charAt(0) === '.' && c.classes.has(sel.slice(1))) { found = c; return; }
            walk(c);
          }
        })(this);
        return found;
      },
      querySelectorAll(sel) {
        const parts = sel.split(','), out = [];
        // Exact forms only: a bare tag, tag:not(:disabled), tag:disabled, a[href]
        // and the tabindex clause. Any other selector matches nothing.
        const hit = c => parts.some(p => {
          const s = p.trim();
          if (s === c.tag) return true;
          if (s === c.tag + ':not(:disabled)') return !c.disabled;
          if (s === c.tag + ':disabled') return c.disabled;
          if (s === 'a[href]') return c.tag === 'a' && 'href' in c.attrs;
          if (s === '[tabindex]:not([tabindex="-1"])') return 'tabindex' in c.attrs && c.attrs.tabindex !== '-1';
          return false;
        });
        (function walk(n) { for (const c of n.children) { if (hit(c)) out.push(c); walk(c); } })(this);
        return out;
      },
      setAttribute(k, v) { this.attrs[k] = String(v); },
      removeAttribute(k) { delete this.attrs[k]; },
      addEventListener(type, fn) { this.listeners.push({type, fn}); },
      removeEventListener(type, fn) {
        this.listeners = this.listeners.filter(l => l.type !== type || l.fn !== fn);
      },
      dispatchEvent(ev) {
        for (const l of this.listeners.slice()) if (l.type === ev.type) l.fn(ev);
      },
    };
    node.classList = makeClassList(classes || []);
    return node;
  }
  function add(parent, child) {
    child.parentElement = parent; child.parentNode = parent; parent.children.push(child); return child;
  }
  const dlg = el('dialog', 'div');
  const panel = add(dlg, el('panel', 'div', ['mx5-dlg-panel']));
  const closeBtn = add(panel, el('close', 'button'));
  const tail = add(panel, el('tail', 'button'));
  add(dlg, el('backdrop', 'div', ['mx5-dlg-backdrop']));
  const opener = el('opener', 'button');
  const win = {
    pageYOffset: 0, scrollTo() {}, dispatchEvent() {},
    matchMedia() { return {matches: false}; },
    mx5CloseAllPopovers() {}, mmPbExpire() {},
    MMXAccessPreview: {isAnon() { return false; }},
  };
  const api = new Function('document', 'window', src + '\nreturn {open: window.mx5OpenDlg, close: window.mx5CloseDlg};')(doc, win);
  // The close button runs the onclick text served on the shipped dlg-risk
  // close button, with mx5CloseDlg bound to the shipped close function.
  const shipped = process.env.ES1_CLOSE_ONCLICK;
  if (shipped) closeBtn.onclick = () => new Function('mx5CloseDlg', shipped)(api.close);
  return {doc, dlg, closeBtn, tail, opener, state, open: api.open, close: api.close};
}
function press(doc, key) {
  const e = {
    key, shiftKey: false, defaultPrevented: false, immediateStopped: false,
    preventDefault() { this.defaultPrevented = true; },
    stopImmediatePropagation() { this.immediateStopped = true; },
  };
  const list = doc.listeners.filter(l => l.type === 'keydown');
  for (const capture of [true, false]) {
    for (const l of list) {
      if (l.capture !== capture) continue;
      l.fn(e);
      if (e.immediateStopped) return e;
    }
  }
  // Default action: Enter or Space on an enabled button runs its click handler.
  const act = doc.activeElement;
  e.activated = false;
  if ((key === 'Enter' || key === ' ') && !e.defaultPrevented && act && act.tag === 'button'
      && !act.disabled && typeof act.onclick === 'function') {
    e.activated = true;
    act.onclick();
  }
  return e;
}
function opened() {
  const h = boot();
  assert.equal(h.opener.tag, 'button');
  h.doc.activeElement = h.opener;
  h.open('dlg-risk');
  flushRaf();
  assert.equal(h.dlg.classList.contains('open'), true, 'opened');
  assert.equal(h.doc.activeElement, h.closeBtn, 'focus entered the dialog');
  return h;
}
function overlay(classes) {
  return {classList: makeClassList(classes)};
}
const which = process.env.ES1_CASE;
if (which === 'closes') {
  const h = opened();
  const e = press(h.doc, 'Escape');
  assert.equal(e.immediateStopped, true, 'stopImmediatePropagation');
  advance(400);
  assert.equal(h.dlg.classList.contains('open'), false, 'closed after the timer');
  assert.equal(h.dlg.classList.contains('mx5-dlg-closing'), false, 'closing class cleared');
  assert.equal(h.doc.activeElement, h.opener, 'focus returned to the opener');
} else if (which === 'capture') {
  const h = boot();
  const keys = h.doc.listeners.filter(l => l.type === 'keydown');
  assert.equal(keys.length, 1, 'one document keydown listener before open');
  assert.equal(keys[0].capture, true);
} else if (which === 'rr-modal') {
  const h = opened();
  h.state.rr = overlay(['open']);
  const e = press(h.doc, 'Escape');
  assert.equal(e.immediateStopped, false, 'overlay keeps the event');
  advance(400);
  assert.equal(h.dlg.classList.contains('open'), true, 'dlg-risk stays open');
  assert.equal(h.dlg.classList.contains('mx5-dlg-closing'), false, 'close did not start');
  assert.equal(h.doc.activeElement, h.closeBtn, 'focus stays in the dialog');
} else if (which === 'tr-overlay') {
  const h = opened();
  h.state.tr = overlay(['rr-tr-overlay', 'is-open']);
  const e = press(h.doc, 'Escape');
  assert.equal(e.immediateStopped, false, 'transcript overlay keeps the event');
  advance(400);
  assert.equal(h.dlg.classList.contains('open'), true, 'dlg-risk stays open');
  assert.equal(h.dlg.classList.contains('mx5-dlg-closing'), false, 'close did not start');
} else if (which === 'enter-close') {
  const h = opened();
  const e = press(h.doc, 'Enter');
  assert.equal(e.immediateStopped, false, 'the Escape listener leaves Enter alone');
  assert.equal(e.defaultPrevented, false, 'Enter keeps its default action');
  assert.equal(e.activated, true, 'Enter activated the focused close button');
  advance(400);
  assert.equal(h.dlg.classList.contains('open'), false, 'closed after the timer');
  assert.equal(h.doc.activeElement, h.opener, 'focus returned to the opener');
} else if (which === 'space-close') {
  const h = opened();
  const e = press(h.doc, ' ');
  assert.equal(e.immediateStopped, false, 'the Escape listener leaves Space alone');
  assert.equal(e.defaultPrevented, false, 'Space keeps its default action');
  assert.equal(e.activated, true, 'Space activated the focused close button');
  advance(400);
  assert.equal(h.dlg.classList.contains('open'), false, 'closed after the timer');
  assert.equal(h.doc.activeElement, h.opener, 'focus returned to the opener');
} else if (which === 'other-key') {
  const h = opened();
  h.doc.activeElement = h.tail;
  let e = press(h.doc, 'Enter');
  assert.equal(e.immediateStopped, false, 'Enter on tail');
  assert.equal(e.activated, false, 'tail has no click handler');
  advance(400);
  assert.equal(h.dlg.classList.contains('open'), true, 'Enter on tail left the dialog open');
  assert.equal(h.doc.activeElement, h.tail, 'Enter on tail left focus');
  // "Esc" is a key string, not the Escape key, and not an activation key.
  h.doc.activeElement = h.closeBtn;
  e = press(h.doc, 'Esc');
  assert.equal(e.immediateStopped, false, 'Esc');
  assert.equal(e.activated, false, 'Esc');
  advance(400);
  assert.equal(h.dlg.classList.contains('open'), true, 'Esc left the dialog open');
  assert.equal(h.dlg.classList.contains('mx5-dlg-closing'), false, 'Esc did not start close');
  assert.equal(h.doc.activeElement, h.closeBtn, 'Esc left focus');
} else if (which === 'disabled-first') {
  const h = boot();
  h.closeBtn.disabled = true;
  h.doc.activeElement = h.opener;
  h.open('dlg-risk');
  flushRaf();
  assert.equal(h.dlg.classList.contains('open'), true, 'opened');
  assert.equal(h.doc.activeElement, h.tail, 'focus skipped the disabled close button');
} else if (which === 'idle') {
  const h = boot();
  assert.equal(h.dlg.classList.contains('open'), false);
  const e = press(h.doc, 'Escape');
  assert.equal(e.immediateStopped, false, 'no dialog, event not stopped');
  advance(400);
  assert.equal(h.dlg.classList.contains('open'), false);
  assert.notEqual(h.doc.activeElement, h.opener);
} else {
  throw new Error('ES1_CASE');
}
"""


def _close_button() -> str:
    """The first button inside the shipped dlg-risk panel, as served markup."""
    page = (ROOT / "templates/dashboard.html.j2").read_text()
    at = page.index('id="dlg-risk"')
    head = page[at:page.index("mx5-dlg-body", at)]
    start = head.index("<button")
    return head[start:head.index(">", start) + 1]


def _onclick(button: str) -> str:
    import re

    found = re.findall(r'\sonclick="([^"]*)"', button)
    return found[0] if len(found) == 1 else ""


def _run(case: str) -> None:
    import os
    import shutil
    import subprocess

    node = shutil.which("node")
    if not node:
        import pytest
        pytest.skip("Node is required to execute the shipped dialog scripts")
    src = _slice("templates/dashboard.html.j2", _START, _END)
    env = dict(os.environ)
    env["ES1_CASE"] = case
    env["ES1_CLOSE_ONCLICK"] = _onclick(_close_button())
    result = subprocess.run(
        [node, "-e", _ESCAPE_JS], input=src, text=True,
        capture_output=True, timeout=20, env=env,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_escape_closes_the_open_risk_dialog_and_returns_focus():
    """A button-opened dlg-risk closes on Escape and focus returns to that button."""
    _run("closes")


def test_escape_listener_is_registered_in_capture():
    """The document listener is registered with capture true."""
    _run("capture")


def test_escape_leaves_the_dialog_while_the_release_radar_modal_is_open():
    """#rr-modal-overlay.open owns Escape: dlg-risk stays up and the event is not stopped."""
    _run("rr-modal")


def test_escape_leaves_the_dialog_while_the_transcript_overlay_is_open():
    """.rr-tr-overlay.is-open owns Escape, so dlg-risk stays open."""
    _run("tr-overlay")


def test_enter_on_the_close_button_closes_through_its_click_handler():
    """Enter passes the listener untouched and activates the focused close button."""
    _run("enter-close")


def test_space_on_the_close_button_closes_through_its_click_handler():
    """Space passes the listener untouched and activates the focused close button."""
    _run("space-close")


def test_shipped_close_button_is_an_enabled_button_that_closes_the_dialog():
    """Enter and Space close dlg-risk only through this markup's own onclick."""
    button = _close_button()
    assert 'class="mx5-dlg-close"' in button
    assert 'type="button"' in button
    assert "disabled" not in button
    assert _onclick(button) == "mx5CloseDlg()"


def test_enter_elsewhere_and_the_esc_string_do_not_close_the_dialog():
    """The listener handles only the key string Escape; Enter on a plain button and Esc leave it up."""
    _run("other-key")


def test_open_focus_skips_a_disabled_first_button():
    """_focusFirst asks for button:not(:disabled), so a disabled close button is passed over."""
    _run("disabled-first")


def test_escape_with_no_dialog_does_not_stop_the_event():
    """With nothing open, Escape does not call stopImmediatePropagation."""
    _run("idle")
