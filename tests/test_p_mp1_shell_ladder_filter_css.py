"""P-MP1-SHELL — the `data-lifef` CSS filter's reveal half.

Caught during evidence capture (real payload, browser-rendered): a card
matching the active `?life=<cell>` filter was still invisible whenever
show-more's `.sm-hidden` class (or tier_preview.js's `.mx-tier-hidden`) had
already applied to it — the hide-half rule
(`#us-standouts[data-lifef=X] #us-life-grid > [data-life]:not([data-life=X])`)
correctly EXCLUDES a matching card, but that card's OWN `display:none
!important` from `.sm-hidden` (theme.css) was never overridden, so it stayed
hidden regardless. Verified live: filtering to `delivering` (lifecycle_counts
count = 1) showed ZERO visible cards before the fix, exactly 1 (the real
row) after.

This mirrors the PRE-EXISTING `data-stagef` filter's own reveal-half rule
(dashboard.html.j2, `.sm-hidden[data-stage="X"]{display:flex!important}`,
with its own code comment naming this exact failure mode) — the fix here is
the same idiom applied to `data-lifef`/`data-life`.

This suite asserts the CSS text directly (no browser needed) so the fix
cannot regress silently; the live behavior was verified once, by hand, in
the browser preview during this packet's build (see PR body evidence).
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DASH = (ROOT / "templates" / "dashboard.html.j2").read_text()

CELLS = ["watch", "ready", "entered", "delivering", "overtime", "invalidated", "resolved"]


def test_hide_half_targets_every_cell():
    for cell in CELLS:
        pattern = (
            r'#us-standouts\[data-lifef="%s"\]\s+#us-life-grid\s*>\s*'
            r'\[data-life\]:not\(\[data-life="%s"\]\)' % (re.escape(cell), re.escape(cell))
        )
        assert re.search(pattern, DASH), f"hide-half rule missing for cell {cell!r}"


def test_reveal_half_overrides_sm_hidden_for_every_cell():
    """The bug this suite exists to pin: a matching card that also carries
    .sm-hidden (show-more's own collapse) must be revealed, not left hidden
    by the OTHER !important rule."""
    for cell in CELLS:
        pattern = (
            r'#us-standouts\[data-lifef="%s"\]\s+#us-life-grid\s*>\s*'
            r'\.sm-hidden\[data-life="%s"\]' % (re.escape(cell), re.escape(cell))
        )
        assert re.search(pattern, DASH), f"reveal-half rule missing for cell {cell!r}"
    # the reveal rule must actually win: display:flex !important, matching
    # .pvcard's own base display value (theme is flex, not block/grid).
    reveal_block = re.search(
        r'(#us-standouts\[data-lifef="watch"\][^\n]*\n(?:[^\n]*\n){0,7}?[^\n]*display:\s*flex\s*!important;\s*\})',
        DASH,
    )
    assert reveal_block, "reveal-half block not found or does not end in display:flex !important"


def test_resolved_default_hidden_rule_still_present():
    """Two-total law (ruling §6): resolved sits OUTSIDE the default/unfiltered
    view — the pre-existing rule this reveal fix must not have disturbed."""
    assert '#us-standouts:not([data-lifef="resolved"]) #us-life-grid > [data-life="resolved"] { display: none !important; }' in DASH


def test_showmore_bar_hidden_while_a_life_filter_is_active():
    assert '#us-standouts[data-lifef] #us-life-grid + .sm-bar { display: none !important; }' in DASH


def _lifecycle_script() -> str:
    marker = "P-MP1-SHELL §7 — the lifecycle ladder's filter + URL law"
    start = DASH.index(marker)
    start = DASH.index("<script>", start) + len("<script>")
    end = DASH.index("</script>", start)
    return DASH[start:end]


def _run_lifecycle_node(assertions: str) -> None:
    import shutil
    import subprocess

    node = shutil.which("node")
    assert node, "node is required by the existing code-gated JavaScript contract"
    harness = r"""
const historyCalls = [];
const grid = {id: 'us-life-grid'};
const target = {
  id: 'pv-CVCO-BULL-20260915',
  getAttribute: (name) => name === 'data-life' ? 'entered' : null,
  closest: (selector) => selector === '#us-life-grid' ? grid : null,
};
const link = {
  getAttribute: (name) => name === 'href' ? '#pv-CVCO-BULL-20260915' : null,
  closest: (selector) => selector === 'a.pv-newer' ? link : (selector === '#us-life-grid' ? grid : null),
};
const box = {
  attrs: {'data-lifef': 'resolved'}, listeners: {},
  setAttribute(name, value){ this.attrs[name] = String(value); },
  removeAttribute(name){ delete this.attrs[name]; },
  getAttribute(name){ return this.attrs[name] || null; },
  addEventListener(name, fn){ this.listeners[name] = fn; },
};
const elements = {'us-standouts': box, 'pv-CVCO-BULL-20260915': target};
global.document = { getElementById: (id) => elements[id] || null };
global.window = { getComputedStyle: () => ({display: 'flex'}) };
global.location = {pathname: '/us_stocks.html', search: '?foo=keep&life=resolved', hash: ''};
global.history = { replaceState: (_a, _b, url) => historyCalls.push(url) };
""" + _lifecycle_script() + assertions
    proc = subprocess.run([node, "-e", harness], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_newer_record_link_selects_loaded_target_lifecycle_before_native_fragment_navigation():
    _run_lifecycle_node(r"""
if (typeof box.listeners.click !== 'function') throw new Error('delegated newer-record handler is absent');
historyCalls.length = 0;
let prevented = 0;
box.listeners.click({
  target: link, button: 0, metaKey: false, ctrlKey: false, shiftKey: false, altKey: false,
  defaultPrevented: false, preventDefault(){ prevented += 1; },
});
if (box.getAttribute('data-lifef') !== 'entered') throw new Error('target lifecycle was not selected');
if (historyCalls.length !== 1 || historyCalls[0] !== '/us_stocks.html?foo=keep&life=entered') {
  throw new Error('query parameters/lifecycle URL were not preserved: ' + JSON.stringify(historyCalls));
}
if (prevented !== 0) throw new Error('native fragment navigation was stolen');
if (link.getAttribute('href') !== '#pv-CVCO-BULL-20260915') throw new Error('published destination changed');
""")


def test_newer_record_link_leaves_modified_click_and_missing_target_untouched():
    _run_lifecycle_node(r"""
if (typeof box.listeners.click !== 'function') throw new Error('delegated newer-record handler is absent');
historyCalls.length = 0;
box.listeners.click({
  target: link, button: 0, metaKey: true, ctrlKey: false, shiftKey: false, altKey: false,
  defaultPrevented: false, preventDefault(){ throw new Error('modified click was prevented'); },
});
if (box.getAttribute('data-lifef') !== 'resolved' || historyCalls.length) {
  throw new Error('modified click mutated the current page');
}
link.getAttribute = (name) => name === 'href' ? '#pv-NOT-LOADED' : null;
box.listeners.click({
  target: link, button: 0, metaKey: false, ctrlKey: false, shiftKey: false, altKey: false,
  defaultPrevented: false, preventDefault(){ throw new Error('missing target click was prevented'); },
});
if (box.getAttribute('data-lifef') !== 'resolved' || historyCalls.length) {
  throw new Error('missing/unauthorized target mutated the current page');
}
""")
