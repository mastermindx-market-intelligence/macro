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
  const tail = add(panel, el({tag: 'button', name: 'tail'}));
  const backdrop = add(risk, el({classes: ['cnx-dlg-backdrop'], name: 'backdrop'}));
  const markets = el({id: 'cnx-dlg-markets', classes: ['cnx-dlg'], name: 'markets'});
  const mpanel = add(markets, el({classes: ['cnx-dlg-panel'], name: 'mpanel'}));
  add(mpanel, el({tag: 'button', classes: ['cnx-dlg-close'], name: 'mclose'}));
  const card = el({tag: 'div', classes: ['cnx-card'], role: 'button', name: 'card', tabIndex: 0});
  const fullRisk = el({tag: 'span', classes: ['cnx-pop-link'], name: 'full-risk', tabIndex: -1});
  const anchor = el({tag: 'a', name: 'internals', attrs: {href: '#cnx-dlg-risk'}});
  let layerBtn = null;
  if (opts.layer === 'hm' || opts.layer === 'lens' || opts.layer === 'below') {
    const classes = opts.layer === 'hm' ? ['hm-ov']
      : opts.layer === 'lens' ? ['lens-pop', 'open']
      : ['cnx-hm-wrap', 'hm-full'];
    const layer = el({classes: classes, name: 'layer'});
    layerBtn = add(layer, el({tag: 'button', name: 'layerbtn'}));
  }
  const location = {pathname: '/china.html', hash: opts.hash || ''};
  const history = {replaceState(_s, _t, url) {
    const i = String(url).indexOf('#');
    location.hash = i >= 0 ? url.slice(i) : '';
    location.pathname = i >= 0 ? url.slice(0, i) : url;
  }};
  const win = {scrollY: opts.scrollY == null ? 640 : opts.scrollY, mmPbExpire() {}, addEventListener() {}};
  if (opts.focus === 'body') doc.activeElement = body;
  else if (opts.active === undefined) doc.activeElement = card;
  else doc.activeElement = opts.active;
  card.onClick = () => { if (win.cnxOpenDlg) win.cnxOpenDlg('cnx-dlg-risk'); };
  closeBtn.onClick = () => { if (win.cnxCloseDlg) win.cnxCloseDlg(); };
  backdrop.onClick = () => { if (win.cnxCloseDlg) win.cnxCloseDlg(); };
  new Function('document', 'window', 'history', 'location', src)(doc, win, history, location);
  return {doc, win, risk, panel, closeBtn, tail, backdrop, card, body, markets, fullRisk, anchor, layerBtn};
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
} else if (which === 'card' || which === 'span' || which === 'anchor' || which === 'hashbody') {
  for (const how of ['escape', 'button', 'backdrop']) {
    const h = which === 'hashbody'
      ? boot({focus: 'body', hash: '#cnx-dlg-risk'})
      : boot({});
    flushRaf();
    let opener = h.body;
    if (which === 'card') {
      opener = h.card;
      h.doc.activeElement = h.card;
      const enter = key(h, 'Enter');
      assert.equal(enter.defaultPrevented, true, 'card enter');
    } else if (which === 'span') {
      opener = h.fullRisk;
      h.doc.activeElement = h.fullRisk;
      h.win.cnxOpenDlg('cnx-dlg-risk');
    } else if (which === 'anchor') {
      opener = h.anchor;
      h.doc.activeElement = h.anchor;
      h.win.cnxOpenDlg('cnx-dlg-risk');
    }
    flushRaf();
    assert.equal(h.risk.classList.contains('open'), true, which + ' opened');
    assert.equal(h.doc.activeElement, h.closeBtn, which + ' focus entered');
    finish(h, how);
    assert.equal(h.risk.classList.contains('open'), false, which + ' ' + how + ' closed');
    assert.equal(h.doc.activeElement, opener, which + ' ' + how + ' returned');
    assert.ok(!h.risk.contains(h.doc.activeElement), which + ' left the dialog');
  }
} else if (which === 'reopen') {
  const h = boot({});
  h.doc.activeElement = h.card;
  key(h, 'Enter');
  flushRaf();
  h.win.cnxCloseDlg();
  advance(50);
  assert.equal(h.risk.classList.contains('cnx-closing'), true, 'close still pending');
  assert.ok(h.risk.contains(h.doc.activeElement), 'focus still inside during the race');
  h.win.cnxOpenDlg('cnx-dlg-risk');
  flushRaf();
  advance(1000);
  h.panel.dispatchEvent({type: 'transitionend', target: h.panel});
  assert.equal(h.risk.classList.contains('open'), true, 'reopened dialog stayed open');
  assert.equal(h.risk.classList.contains('cnx-closing'), false, 'reopened dialog not closing');
  assert.ok(h.risk.contains(h.doc.activeElement), 'focus stayed in the reopened dialog');
  h.win.cnxCloseDlg();
  advance(1000);
  h.panel.dispatchEvent({type: 'transitionend', target: h.panel});
  assert.equal(h.doc.activeElement, h.card, 'original opener kept');
} else if (which === 'other') {
  const h = boot({});
  h.doc.activeElement = h.card;
  key(h, 'Enter');
  flushRaf();
  h.win.cnxCloseDlg();
  advance(50);
  const stayed = h.doc.activeElement;
  h.win.cnxOpenDlg('cnx-dlg-markets');
  advance(1000);
  h.panel.dispatchEvent({type: 'transitionend', target: h.panel});
  assert.equal(h.risk.classList.contains('open'), false, 'risk closed for the other dialog');
  assert.equal(h.markets.classList.contains('open'), true, 'other dialog open');
  assert.equal(h.doc.activeElement, stayed, 'risk done() did not move focus');
  assert.notEqual(h.doc.activeElement, h.card, 'opener was not restored by the stale close');
} else if (which === 'overlay') {
  for (const layer of ['hm', 'lens']) {
    const h = boot({layer: layer});
    h.doc.activeElement = h.card;
    h.win.cnxOpenDlg('cnx-dlg-risk');
    flushRaf();
    h.doc.activeElement = h.layerBtn;
    let e = key(h, 'Tab');
    assert.equal(e.defaultPrevented, false, layer + ' tab');
    assert.equal(h.doc.activeElement, h.layerBtn, layer + ' tab focus');
    e = key(h, 'Tab', {shift: true});
    assert.equal(e.defaultPrevented, false, layer + ' shift tab');
    assert.equal(h.doc.activeElement, h.layerBtn, layer + ' shift focus');
    key(h, 'Escape');
    assert.equal(h.risk.classList.contains('open'), true, layer + ' escape left the dialog open');
    assert.equal(h.risk.classList.contains('cnx-closing'), false, layer + ' escape did not start close');
  }
  const below = boot({layer: 'below'});
  below.doc.activeElement = below.card;
  below.win.cnxOpenDlg('cnx-dlg-risk');
  flushRaf();
  below.doc.activeElement = below.layerBtn;
  const stolen = key(below, 'Tab');
  assert.equal(stolen.defaultPrevented, true, 'heatmap under the dialog is still trapped');
  assert.equal(below.doc.activeElement, below.closeBtn, 'stray focus below the dialog returns');
  const plain = boot({});
  plain.doc.activeElement = plain.card;
  plain.win.cnxOpenDlg('cnx-dlg-risk');
  flushRaf();
  plain.doc.activeElement = plain.card;
  const back = key(plain, 'Tab');
  assert.equal(back.defaultPrevented, true, 'open dialog still traps a stray tab');
  assert.equal(plain.doc.activeElement, plain.closeBtn);
  const shift = key(plain, 'Tab', {shift: true});
  plain.doc.activeElement = plain.card;
  const shift2 = key(plain, 'Tab', {shift: true});
  assert.equal(shift2.defaultPrevented, true, 'shift tab from outside wraps to the last stop');
  assert.equal(plain.doc.activeElement, plain.tail);
  assert.equal(shift.defaultPrevented, true);
} else if (which === 'inert') {
  const h = boot({});
  h.doc.activeElement = h.card;
  let e = key(h, 'Tab');
  assert.equal(e.defaultPrevented, false, 'closed dialog ignores tab');
  assert.equal(h.doc.activeElement, h.card);
  e = key(h, 'Tab', {shift: true});
  assert.equal(e.defaultPrevented, false, 'closed dialog ignores shift tab');
  h.win.cnxOpenDlg('cnx-dlg-risk');
  flushRaf();
  h.win.cnxCloseDlg();
  assert.equal(h.risk.classList.contains('cnx-closing'), true);
  h.doc.activeElement = h.card;
  e = key(h, 'Tab');
  assert.equal(e.defaultPrevented, false, 'closing dialog ignores tab');
  assert.equal(h.doc.activeElement, h.card);
  advance(1000);
  e = key(h, 'Tab');
  assert.equal(e.defaultPrevented, false, 'dialog ignores tab after close');
} else if (which === 'scroll') {
  const h = boot({scrollY: 640, active: null});
  const y = h.win.scrollY;
  assert.equal(h.body.style.overflow || '', '');
  h.win.cnxOpenDlg('cnx-dlg-markets');
  assert.equal(h.body.style.overflow, 'hidden', 'first dialog locks scroll');
  h.win.cnxOpenDlg('cnx-dlg-risk');
  flushRaf();
  assert.equal(h.markets.classList.contains('open'), false, 'previous dialog closed');
  assert.equal(h.risk.classList.contains('open'), true);
  assert.equal(h.body.style.overflow, 'hidden', 'risk dialog keeps the lock');
  h.win.cnxCloseDlg();
  assert.equal(h.body.style.overflow, '', 'close clears the lock at once');
  advance(1000);
  assert.equal(h.risk.classList.contains('open'), false);
  assert.equal(h.body.style.overflow, '');
  assert.equal(h.win.scrollY, y, 'scroll position unchanged');
} else {
  throw new Error('CN_CASE');
}
function key(h, name, extra) {
  const e = {
    key: name,
    shiftKey: !!(extra && extra.shift),
    target: h.doc.activeElement,
    defaultPrevented: false,
    preventDefault() { this.defaultPrevented = true; },
  };
  for (const l of h.doc.listeners.slice()) if (l.type === 'keydown') l.fn(e);
  return e;
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


# Dialog motion that prefers-reduced-motion:no-preference turns on. The reduce
# block has to name transition:none for the same elements; a separate media
# query is not a neutralization the audit can see in the style text.
_DIALOG_MOTION = ("cnx-dlg-backdrop", "cnx-dlg-panel", "cnx-dlg-body")


def _no_preference_blocks(text: str) -> list[str]:
    import re

    from tests.test_us_dialog_focus_lifecycle import _matching_brace

    header = re.compile(r"@media[^{]*prefers-reduced-motion\s*:\s*no-preference\b", re.I)
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


def _motion_classes(blocks: list[str], *, require_none: bool) -> set[str]:
    from tests.test_us_dialog_focus_lifecycle import (
        _covers_class,
        _css_rules,
        _declares_transition_none,
    )

    found: set[str] = set()
    for body in blocks:
        for selector, declarations in _css_rules(body):
            if "transition" not in declarations:
                continue
            has_none = _declares_transition_none(declarations)
            if require_none != has_none:
                continue
            if not require_none and not _has_transition_decl(declarations):
                continue
            for name in _DIALOG_MOTION:
                if _covers_class(selector, name):
                    found.add(name)
    return found


def _has_transition_decl(declarations: str) -> bool:
    """A transition shorthand or longhand that is not merely a comment."""
    import re

    cleaned = re.sub(r"/\*.*?\*/", "", declarations, flags=re.S)
    return re.search(r"(?:^|[;{\s])transition(?:-[a-z]+)?\s*:", cleaned) is not None


def test_reduced_motion_neutralizes_china_dialog_transitions():
    """prefers-reduced-motion:reduce must set transition:none on the dialog shell.

    The no-preference block fades the backdrop, raises the panel, and staggers
    the body. The reduce block has to cancel those transitions in its own text.
    """
    from tests.test_us_dialog_focus_lifecycle import _reduce_motion_blocks

    text = (ROOT / "templates" / "china.html.j2").read_text()
    animated = _motion_classes(_no_preference_blocks(text), require_none=False)
    assert animated == set(_DIALOG_MOTION), animated
    neutralized = _motion_classes(_reduce_motion_blocks(text), require_none=True)
    missing = sorted(animated - neutralized)
    assert not missing, "reduced-motion transition:none missing for " + ", ".join(missing)


def test_close_returns_focus_to_the_card_the_span_and_the_hash_opener():
    """Connected openers get focus back. A hash open with body focused returns to body."""
    _run("card")
    _run("span")
    _run("anchor")
    _run("hashbody")


def test_reopen_cancels_the_pending_close_and_keeps_the_original_opener():
    """Open, close, reopen at +50ms. The stale close must not shut the new open."""
    _run("reopen")
    _run("other")


def test_stacked_overlays_keep_tab_and_escape():
    """Heatmap and lens overlays above the dialog are not swallowed by its trap."""
    _run("overlay")


def test_trap_is_inert_while_the_risk_dialog_is_closed_or_closing():
    _run("inert")


def test_scroll_lock_clears_after_close_and_keeps_scroll_position():
    """Opening another dialog first must not leave the page locked after close."""
    _run("scroll")


def _style_chunks(text: str) -> str:
    parts = []
    i = 0
    while True:
        start = text.find("<style", i)
        if start < 0:
            break
        start = text.find(">", start)
        end = text.find("</style>", start)
        if start < 0 or end < 0:
            break
        parts.append(text[start + 1:end])
        i = end + len("</style>")
    return "\n".join(parts)


def _iter_rules(body: str) -> list[tuple[str, str]]:
    from tests.test_us_dialog_focus_lifecycle import _matching_brace, _skip_jinja_or_comment

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
            end = _matching_brace(body, brace)
            rules.extend(_iter_rules(body[brace + 1:end - 1]))
            i = end
            continue
        brace = body.find("{", i)
        if brace < 0:
            break
        end = _matching_brace(body, brace)
        rules.append((body[i:brace].strip(), body[brace + 1:end - 1]))
        i = end
    return rules


def test_reduced_motion_close_button_and_pullback_fragment_do_not_move():
    """Close control and the pullback chart have no motion left under reduce.

    Playwright is not installed for this interpreter, so this reads the style
    text. The fragment sets animation:none itself; the dialog reduce block sets
    animation:none on the shell the fragment sits in.
    """
    import re

    from tests.test_us_dialog_focus_lifecycle import _covers_class, _reduce_motion_blocks

    styles = _style_chunks((ROOT / "templates" / "china.html.j2").read_text())
    moving = []
    for selector, declarations in _iter_rules(styles):
        if not _covers_class(selector, "cnx-dlg-close"):
            continue
        cleaned = re.sub(r"/\*.*?\*/", "", declarations, flags=re.S)
        for prop in ("transition", "animation"):
            for found in re.finditer(rf"(?:^|[;{{\s]){prop}\s*:\s*([^;]+)", cleaned):
                if found.group(1).strip() != "none":
                    moving.append(prop)
    assert not moving, moving

    css = (ROOT / "templates" / "_risk_radar_pullback_depth.css.j2").read_text()
    assert "transition:" not in css
    for needle in (".ilx-path", ".ilx-water", ".ilx-ref", ".ilx-tag", ".ilx-dot"):
        assert needle in css
    assert css.count("animation:none") >= 5

    shell = {"cnx-dlg-backdrop": False, "cnx-dlg-panel": False, "cnx-dlg-body": False}
    for body in _reduce_motion_blocks((ROOT / "templates" / "china.html.j2").read_text()):
        for selector, declarations in _iter_rules(body):
            if not re.search(r"(?:^|[;{\s])animation\s*:\s*none\b", declarations):
                continue
            for name in shell:
                if _covers_class(selector, name):
                    shell[name] = True
    missing = [name for name, ok in shell.items() if not ok]
    assert not missing, missing


class _Bag:
    """Stand-in for missing China view-model fields. Renders empty, never a quote."""

    def __str__(self):
        return ""

    def __html__(self):
        from markupsafe import Markup
        return Markup("")

    def __html_format__(self, spec):
        return self.__html__()

    def __format__(self, spec):
        return ""

    def __iter__(self):
        return iter(())

    def __bool__(self):
        return False

    def __len__(self):
        return 0

    def __int__(self):
        return 0

    def __float__(self):
        return 0.0

    def __index__(self):
        return 0

    def __round__(self, n=None):
        return 0

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return self

    def __getitem__(self, key):
        return self

    def __call__(self, *args, **kwargs):
        return self

    def __eq__(self, other):
        return False

    def __ne__(self, other):
        return True

    def __lt__(self, other):
        return False

    def __gt__(self, other):
        return False

    def __le__(self, other):
        return False

    def __ge__(self, other):
        return False

    def __add__(self, other):
        return 0

    def __radd__(self, other):
        return 0

    def __sub__(self, other):
        return 0

    def __rsub__(self, other):
        return 0

    def __mul__(self, other):
        return 0

    def __rmul__(self, other):
        return 0

    def __truediv__(self, other):
        return 0

    def __floordiv__(self, other):
        return 0

    def __mod__(self, other):
        return 0

    def get(self, *args, **kwargs):
        return self

    def items(self):
        return []

    def keys(self):
        return []

    def values(self):
        return []

    def startswith(self, *args):
        return False

    def split(self, *args):
        return []


def _render_china() -> str:
    from jinja2 import Environment, FileSystemLoader, Undefined

    class Missing(_Bag, Undefined):
        pass

    def empty(*args, **kwargs):
        return ""

    def hero(*args, **kwargs):
        return ("", "")

    env = Environment(
        loader=FileSystemLoader(str(ROOT / "templates")),
        autoescape=False,
        undefined=Missing,
    )
    env.globals.update(
        td=empty, tr=empty, t=empty, t_pctile=empty,
        posture_lane=empty, posture_tone=empty, reason_faces=lambda *a, **k: [],
        hero_clause=hero,
    )

    class Latest:
        date = "2026-01-01"

        def __getattr__(self, name):
            return Missing()

    return env.get_template("china.html.j2").render(
        mode="macro", latest=Latest(), market_state=Missing(), sectors=[],
    )


def test_rendered_page_overlays_and_risk_dialog_name():
    """Only the risk dialog is a dialog. Overlays above it are not in the markup.

    The page script still names .hm-ov and .lens-pop.open, which the trap yields
    to. #rr-modal-overlay and .rr-tr-overlay are absent. The heatmap stage under
    the dialog (.cnx-hm-wrap.hm-full) has a lower z-index, so it stays trapped.
    """
    import re

    from bs4 import BeautifulSoup

    html = _render_china()
    soup = BeautifulSoup(html, "html.parser")
    assert soup.select("#rr-modal-overlay") == []
    assert soup.select(".rr-tr-overlay") == []
    assert soup.select(".hm-ov") == []
    assert soup.select(".lens-pop") == []
    assert [node.get("id") for node in soup.select("[role=dialog]")] == ["cnx-dlg-risk"]
    assert soup.select_one("#cn-hm-embed") is not None
    # Lens tips render only when a face is present. The page template still
    # carries data-tip, and the shipped script yields to .lens-pop.open.
    assert "data-tip" in (ROOT / "templates" / "china.html.j2").read_text()
    assert ".hm-ov" in html and ".lens-pop.open" in html

    risk = soup.select_one("#cnx-dlg-risk")
    assert risk.get("role") == "dialog"
    assert risk.get("aria-modal") == "true"
    label_id = risk.get("aria-labelledby")
    title = soup.select_one("#" + label_id)
    assert title is not None and title.find_parent(id="cnx-dlg-risk") is not None
    assert title.get_text(strip=True)
    close = risk.select_one("button.cnx-dlg-close")
    assert close.get("aria-label") in ("Close", "关闭")
    assert close.get("aria-label") not in ("×", "x", "X")

    links = [
        node for node in soup.select("span.cnx-pop-link")
        if "cnx-dlg-risk" in (node.get("onclick") or "")
    ]
    assert len(links) == 1
    assert links[0].get("tabindex") is None and links[0].get("href") is None
    assert "Full risk detail" in links[0].get_text(" ", strip=True)

    def z_index(snippet: str) -> int:
        at = html.find(snippet)
        assert at >= 0, snippet
        block = html[at:html.find("}", at)]
        found = re.search(r"z-index:\s*(\d+)", block)
        assert found, snippet
        return int(found.group(1))

    assert z_index("body.page-china .cnx-hm-wrap.hm-full{") < z_index("body.page-china .cnx-dlg{")
    assert "animation:none" in html and ".rrp .rrp-chart .ilx-path" in html
