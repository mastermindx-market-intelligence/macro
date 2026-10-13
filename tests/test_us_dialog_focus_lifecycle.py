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
const dlg = el('dialog', 'div', ['open']);
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


# The open/close pair closes over _dlgActive. A manual timer queue stands in for
# setTimeout / requestAnimationFrame so a reopen at +50ms can be observed at +400ms.
_LIFECYCLE_JS = r"""
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
  const doc = {
    activeElement: null,
    listeners: [],
    documentElement: {classList: makeClassList(), style: {}},
    body: {classList: makeClassList(['page-macro']), style: {}},
    addEventListener(type, fn) { this.listeners.push({type, fn}); },
    removeEventListener(type, fn) {
      this.listeners = this.listeners.filter(l => l.type !== type || l.fn !== fn);
    },
    getElementById(id) { return id === 'dlg-risk' ? dlg : null; },
    querySelector(sel) {
      if (sel === '.mx5-hm-stage' || sel === '.rr-tr-overlay.is-open' || sel === '.hm-ov') return null;
      throw new Error('document.querySelector ' + sel);
    },
  };
  function el(name, tag, classes) {
    const node = {
      name, tag, classes: new Set(classes || []),
      parentElement: null, parentNode: null, children: [],
      listeners: [], attrs: {}, style: {}, tabIndex: 0,
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
        const hit = c => parts.some(p => {
          const s = p.trim();
          return s === c.tag || s.startsWith(c.tag + ':') || s.startsWith(c.tag + '[')
            || (c.tag === 'a' && s === 'a[href]');
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
  add(panel, el('tail', 'button'));
  add(dlg, el('backdrop', 'div', ['mx5-dlg-backdrop']));
  const opener = el('opener', 'button');
  const stray = el('stray', 'button');
  const win = {
    pageYOffset: 0, scrollTo() {}, dispatchEvent() {},
    matchMedia() { return {matches: false}; },
    mx5CloseAllPopovers() {}, mmPbExpire() {},
    MMXAccessPreview: {isAnon() { return false; }},
  };
  const api = new Function('document', 'window', src + '\nreturn {open: window.mx5OpenDlg, close: window.mx5CloseDlg};')(doc, win);
  return {doc, dlg, panel, closeBtn, opener, stray, open: api.open, close: api.close};
}
function key(doc, from) {
  doc.activeElement = from;
  const e = {key: 'Tab', shiftKey: false, defaultPrevented: false,
             preventDefault() { this.defaultPrevented = true; }};
  for (const l of doc.listeners.slice()) if (l.type === 'keydown') l.fn(e);
  return e;
}
const which = process.env.U2_CASE;
if (which === 'reopen') {
  const h = boot();
  h.doc.activeElement = h.opener;
  h.open('dlg-risk');
  flushRaf();
  assert.equal(h.dlg.classList.contains('open'), true, 'opened');
  h.close();
  advance(50);
  h.open('dlg-risk');
  flushRaf();
  h.panel.dispatchEvent({type: 'transitionend', target: h.panel, propertyName: 'transform'});
  assert.equal(h.dlg.classList.contains('open'), true, 'old close transitionend');
  assert.notEqual(h.doc.activeElement, h.opener, 'old close refocus');
  advance(400);
  assert.equal(h.dlg.classList.contains('open'), true, 'stale close timer');
  assert.notEqual(h.doc.activeElement, h.opener, 'stale close refocus');
  const e = key(h.doc, h.stray);
  assert.equal(e.defaultPrevented, true, 'stray Tab after reopen');
  assert.equal(h.doc.activeElement, h.closeBtn, 'stray Tab focus');
} else if (which === 'closed') {
  const h = boot();
  h.doc.activeElement = h.opener;
  h.open('dlg-risk');
  flushRaf();
  h.close();
  advance(400);
  assert.equal(h.dlg.classList.contains('open'), false, 'close finished');
  assert.equal(h.doc.activeElement, h.opener, 'refocus opener');
  const e = key(h.doc, h.stray);
  assert.equal(e.defaultPrevented, false, 'Tab after close');
  assert.equal(h.doc.activeElement, h.stray, 'focus stays after close');
} else {
  throw new Error('U2_CASE');
}
"""


def _lifecycle(case: str) -> None:
    import os
    src = _between(
        "templates/dashboard.html.j2",
        "var _dlgActive = null;",
        "/* Escape handler: dialog > scorecard popover > release radar modal guards */",
    )
    # _node_raw does not forward env. Run the same node contract with U2_CASE set.
    import shutil
    import subprocess
    node = shutil.which("node")
    if not node:
        import pytest
        pytest.skip("Node is required to execute the shipped dialog scripts")
    env = dict(os.environ)
    env["U2_CASE"] = case
    result = subprocess.run([node, "-e", _LIFECYCLE_JS], input=src, text=True,
                            capture_output=True, timeout=20, env=env)
    assert result.returncode == 0, result.stdout + result.stderr


def test_reopen_during_close_keeps_the_dialog_and_its_trap():
    """Close, reopen at +50ms, then the old 340ms close must not fire."""
    _lifecycle("reopen")


def test_completed_close_does_not_trap_tab():
    """Once the exit finishes, a Tab on the page is a normal page Tab."""
    _lifecycle("closed")


_HIDDEN_TRAP_JS = r"""
const assert = require('node:assert/strict');
function makeClassList(initial) {
  const set = new Set(initial || []);
  return {
    contains(c) { return set.has(c); },
    add() { for (let i = 0; i < arguments.length; i++) set.add(arguments[i]); },
    remove() { for (let i = 0; i < arguments.length; i++) set.delete(arguments[i]); },
  };
}
const doc = {
  activeElement: null,
  getElementById() { return null; },
  querySelector() { return null; },
};
function el(name, tag) {
  return {
    name, tag, parentElement: null, children: [], tabIndex: 0,
    getClientRects() { return [{}]; },
    focus() { doc.activeElement = this; },
    contains(o) { for (let n = o; n; n = n.parentElement) if (n === this) return true; return false; },
    closest(sel) {
      if (sel === '[inert]' || sel === 'details:not([open])' || sel === '.lens-pop.open') return null;
      throw new Error('closest ' + sel);
    },
    querySelector() { return null; },
    querySelectorAll(sel) {
      const parts = sel.split(','), out = [];
      const hit = c => parts.some(p => p.trim() === c.tag || p.trim().startsWith(c.tag + ':'));
      (function walk(n) { for (const c of n.children) { if (hit(c)) out.push(c); walk(c); } })(this);
      return out;
    },
  };
}
function add(parent, child) { child.parentElement = parent; parent.children.push(child); return child; }
const dlg = el('dialog', 'div');
dlg.classList = makeClassList(['open']);
const first = add(dlg, el('close', 'button'));
const outside = el('outside', 'button');
const src = require('node:fs').readFileSync(0, 'utf8');
const trap = new Function('document', src + '; return _trapTab;')(doc);
function tab(from) {
  doc.activeElement = from;
  const e = {key: 'Tab', shiftKey: false, defaultPrevented: false,
             preventDefault() { this.defaultPrevented = true; }};
  trap(dlg, e);
  return e;
}
let e = tab(outside);
assert.equal(e.defaultPrevented, true, 'open dialog pulls stray Tab');
assert.equal(doc.activeElement, first);
dlg.classList.remove('open');
e = tab(outside);
assert.equal(e.defaultPrevented, false, 'hidden dialog');
assert.equal(doc.activeElement, outside, 'hidden dialog focus');
dlg.classList.add('open', 'mx5-dlg-closing');
e = tab(outside);
assert.equal(e.defaultPrevented, false, 'closing dialog');
assert.equal(doc.activeElement, outside, 'closing dialog focus');
"""


def test_trap_is_inert_while_the_dialog_is_hidden_or_closing():
    """A handler left on the document must not steal Tab into a dialog that is not shown."""
    src = _between("templates/dashboard.html.j2", "function _tabStop(el){", "function _prefReduced(")
    _node_raw(_HIDDEN_TRAP_JS, src)


def _skip_jinja_or_comment(text: str, i: int) -> int | None:
    if text.startswith("/*", i):
        end = text.find("*/", i + 2)
        return len(text) if end < 0 else end + 2
    if text.startswith("{{", i):
        end = text.find("}}", i + 2)
        return len(text) if end < 0 else end + 2
    if text.startswith("{%", i):
        end = text.find("%}", i + 2)
        return len(text) if end < 0 else end + 2
    return None


def _matching_brace(text: str, open_at: int) -> int:
    """`open_at` points at `{`. Return the index just after the matching `}`."""
    depth = 0
    i = open_at
    n = len(text)
    while i < n:
        skipped = _skip_jinja_or_comment(text, i)
        if skipped is not None:
            i = skipped
            continue
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    raise ValueError("unbalanced brace at %s" % open_at)


def _reduce_motion_blocks(text: str) -> list[str]:
    """Bodies of `@media (prefers-reduced-motion: reduce)`, brace-matched."""
    import re
    header = re.compile(r"@media[^{]*prefers-reduced-motion\s*:\s*reduce\b", re.I)
    blocks = []
    i = 0
    while True:
        match = header.search(text, i)
        if not match:
            break
        brace = text.find("{", match.end())
        if brace < 0:
            break
        end = _matching_brace(text, brace)
        blocks.append(text[brace + 1:end - 1])
        i = end
    return blocks


def _css_rules(body: str) -> list[tuple[str, str]]:
    rules = []
    i = 0
    n = len(body)
    while i < n:
        skipped = _skip_jinja_or_comment(body, i)
        if skipped is not None:
            i = skipped
            continue
        if body[i].isspace():
            i += 1
            continue
        if body[i] == "@":
            brace = body.find("{", i)
            if brace < 0:
                break
            i = _matching_brace(body, brace)
            continue
        brace = body.find("{", i)
        if brace < 0:
            break
        selector = body[i:brace].strip()
        end = _matching_brace(body, brace)
        rules.append((selector, body[brace + 1:end - 1]))
        i = end
    return rules


def _covers_class(selector_list: str, class_name: str) -> bool:
    import re
    parts = []
    buf = []
    depth = 0
    for ch in selector_list:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        elif ch == "," and depth == 0:
            parts.append("".join(buf).strip())
            buf = []
            continue
        buf.append(ch)
    if buf:
        parts.append("".join(buf).strip())
    token = re.compile(r"\." + re.escape(class_name) + r"(?![-\w])")
    return any(token.search(part) for part in parts)


def _declares_transition_none(declarations: str) -> bool:
    import re
    cleaned = re.sub(r"/\*.*?\*/", "", declarations, flags=re.S)
    return re.search(r"(?:^|[;{\s])transition\s*:\s*none\b", cleaned) is not None


def test_reduced_motion_kills_dialog_close_and_signal_tip_transitions():
    """Under prefers-reduced-motion, the close control and signal tip do not transition."""
    text = (ROOT / "templates/dashboard.html.j2").read_text()
    found = {"mx5-dlg-close": False, "rkc-sig-tip": False}
    for body in _reduce_motion_blocks(text):
        for selector, declarations in _css_rules(body):
            if not _declares_transition_none(declarations):
                continue
            if _covers_class(selector, "mx5-dlg-close"):
                found["mx5-dlg-close"] = True
            if _covers_class(selector, "rkc-sig-tip"):
                found["rkc-sig-tip"] = True
    missing = [name for name, ok in found.items() if not ok]
    assert not missing, "reduced-motion transition:none missing for " + ", ".join(missing)
