"""Edge cases for the shipped Risk Radar pullback expiry owner.

Runs ``templates/_risk_radar_pullback_depth.js.j2`` under Node with a fake
document and a controllable clock. Every stamp in here is synthetic.
"""
import os
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

_OWNER = Path(__file__).resolve().parents[1] / "templates" / "_risk_radar_pullback_depth.js.j2"

# The owner reads global Date / window / document. The prelude installs a
# movable Date.now and a setTimeout queue that honours clearTimeout, then
# evaluates the shipped script against whatever sections the case built.
_HARNESS = r"""
const assert = require('node:assert/strict');
const SOURCE = require('node:fs').readFileSync(0, 'utf8');
if (!SOURCE.includes('mmPbExpire') || !SOURCE.includes('data-pb-valid-until')) {
  throw new Error('stdin is not the pullback expiry owner');
}
let now = 0;
Date.now = () => now;

function at(iso) {
  const ms = Date.parse(iso);
  if (!Number.isFinite(ms)) throw new Error('unparseable fixture ' + iso);
  return ms;
}
function remember(map, type, fn) {
  if (!Object.prototype.hasOwnProperty.call(map, type)) map[type] = [];
  map[type].push(fn);
}
function nlisteners(map, type) {
  return Object.prototype.hasOwnProperty.call(map, type) ? map[type].length : 0;
}
function section(stamp) {
  const attrs = {'data-pb-valid-until': stamp, 'data-pb-phase': 'underway'};
  const classes = new Set(['rrp', 'pbx']);
  const en = {textContent: 'Pullback underway'};
  const zh = {textContent: '回调进行中'};
  const heading = {
    querySelector(sel) {
      if (sel === '.l-en') return en;
      if (sel === '.l-zh') return zh;
      return null;
    },
  };
  return {
    en, zh, attrs, classes,
    getAttribute(name) {
      return Object.prototype.hasOwnProperty.call(attrs, name) ? attrs[name] : null;
    },
    setAttribute(name, value) { attrs[name] = String(value); },
    classList: {add(name) { classes.add(name); }},
    querySelector(sel) { return sel === '.pbx-heading h2' ? heading : null; },
  };
}
function assertCurrent(sec, label) {
  assert.equal(sec.classes.has('pb-expired'), false, label);
  assert.equal(sec.attrs['data-pb-phase'], 'underway', label);
  assert.equal(sec.en.textContent, 'Pullback underway', label);
}
function assertExpired(sec, label) {
  assert.equal(sec.classes.has('pb-expired'), true, label);
  assert.equal(sec.attrs['data-pb-phase'], 'unavailable', label);
  assert.equal(sec.en.textContent, 'Price update needed', label);
  assert.equal(sec.zh.textContent, '价格数据待更新', label);
}
function boot(list, readyState = 'complete') {
  const pending = new Map();
  const listeners = {document: Object.create(null), window: Object.create(null)};
  let seq = 0;
  const document = {
    readyState,
    hidden: false,
    querySelectorAll(sel) {
      if (sel !== '.rrp.pbx[data-pb-valid-until]') {
        throw new Error('unexpected querySelectorAll: ' + sel);
      }
      return list;
    },
    addEventListener(type, fn) { remember(listeners.document, type, fn); },
  };
  const window = {
    setTimeout(fn, ms) {
      const id = ++seq;
      pending.set(id, {fn, ms, id});
      return id;
    },
    clearTimeout(id) { pending.delete(id); },
    addEventListener(type, fn) { remember(listeners.window, type, fn); },
  };
  new Function('window', 'document', SOURCE)(window, document);
  if (typeof window.mmPbExpire !== 'function') throw new Error('mmPbExpire was not installed');
  return {window, document, pending, listeners};
}
function expectBoundary(stamp, earlyIso, exactIso) {
  const sec = section(stamp);
  now = at(earlyIso);
  const ctx = boot([sec]);
  assertCurrent(sec, stamp + ' @ ' + earlyIso);
  now = at(exactIso);
  ctx.window.mmPbExpire();
  assertExpired(sec, stamp + ' @ ' + exactIso);
  now = at(exactIso) + 1000;
  ctx.window.mmPbExpire();
  assertExpired(sec, stamp + ' after ' + exactIso);
}
"""


def _epoch_ms(stamp: str) -> int:
    parsed = datetime.fromisoformat(stamp)
    if parsed.tzinfo is None:
        raise AssertionError(f"naive stamp has no UTC instant: {stamp}")
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    return (parsed - epoch) // timedelta(milliseconds=1)


def _node_raw(script: str, stdin: str) -> None:
    node = shutil.which("node")
    if not node:
        if os.environ.get("CI"):
            pytest.fail("Node is required in CI to execute the shipped expiry owner")
        pytest.skip("Node is required to execute the shipped expiry owner")
    result = subprocess.run(
        [node, "-e", script],
        input=stdin,
        text=True,
        capture_output=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def _run(body: str) -> None:
    _node_raw(_HARNESS + "\n" + body, _OWNER.read_text(encoding="utf-8"))


def test_x1_plus08_expires_at_0900z():
    """17:00+08 is 09:00Z: still current one second before, expired on the instant."""
    assert _epoch_ms("2026-10-12T17:00:00+08:00") == _epoch_ms("2026-10-12T09:00:00Z")
    _run(
        "expectBoundary('2026-10-12T17:00:00+08:00',"
        " '2026-10-12T08:59:59Z', '2026-10-12T09:00:00Z');\n"
    )


def test_x2_z_suffix_is_honoured():
    """A trailing Z is a UTC deadline, current one second before and expired on it."""
    assert _epoch_ms("2026-10-12T17:00:00Z") == _epoch_ms("2026-10-12T17:00:00+00:00")
    _run(
        "expectBoundary('2026-10-12T17:00:00Z',"
        " '2026-10-12T16:59:59Z', '2026-10-12T17:00:00Z');\n"
    )


def test_x3_negative_offsets_honoured_across_us_dst():
    """-04:00 and -05:00 are the stamp's own offset, including the 2026-11-01 fallback.

    US clocks repeat 01:30 that morning: 01:30-04:00 is 05:30Z and 01:30-05:00
    is 06:30Z. The two stamps must not collapse to one instant.
    """
    assert _epoch_ms("2026-10-12T17:00:00-04:00") == _epoch_ms("2026-10-12T21:00:00Z")
    assert _epoch_ms("2026-11-02T17:00:00-05:00") == _epoch_ms("2026-11-02T22:00:00Z")
    assert _epoch_ms("2026-11-01T01:30:00-04:00") == _epoch_ms("2026-11-01T05:30:00Z")
    assert _epoch_ms("2026-11-01T01:30:00-05:00") == _epoch_ms("2026-11-01T06:30:00Z")
    assert (
        _epoch_ms("2026-11-01T01:30:00-05:00") - _epoch_ms("2026-11-01T01:30:00-04:00")
        == 3_600_000
    )
    _run(
        """
expectBoundary('2026-10-12T17:00:00-04:00', '2026-10-12T20:59:59Z', '2026-10-12T21:00:00Z');
expectBoundary('2026-11-02T17:00:00-05:00', '2026-11-02T21:59:59Z', '2026-11-02T22:00:00Z');
expectBoundary('2026-11-01T01:30:00-04:00', '2026-11-01T05:29:59Z', '2026-11-01T05:30:00Z');
expectBoundary('2026-11-01T01:30:00-05:00', '2026-11-01T06:29:59Z', '2026-11-01T06:30:00Z');
const edt = section('2026-11-01T01:30:00-04:00');
const est = section('2026-11-01T01:30:00-05:00');
now = at('2026-11-01T05:29:59Z');
const ctx = boot([est, edt]);
assertCurrent(edt, 'edt before fallback hour');
assertCurrent(est, 'est before fallback hour');
now = at('2026-11-01T05:30:00Z');
ctx.window.mmPbExpire();
assertExpired(edt, 'edt at 05:30Z');
assertCurrent(est, 'est still an hour out at 05:30Z');
now = at('2026-11-01T06:30:00Z');
ctx.window.mmPbExpire();
assertExpired(edt, 'edt stays expired');
assertExpired(est, 'est at 06:30Z');
"""
    )


def test_x4_naive_stamp_is_expired():
    """A stamp with no offset is expired even while every local reading is still ahead.

    2026-10-10T00:00:00Z is before 17:00 on 2026-10-12 in every offset from UTC-12
    through UTC+14. The case also checks this engine's own local parse is still
    in the future, so the expiry is the fail-safe and not an already-passed clock.
    """
    _run(
        """
now = at('2026-10-10T00:00:00Z');
const naiveMs = Date.parse('2026-10-12T17:00:00');
assert.equal(Number.isFinite(naiveMs), true, 'naive ISO is a local reading on this engine');
assert.ok(naiveMs > now, 'local reading of the naive stamp is still in the future');
const sec = section('2026-10-12T17:00:00');
boot([sec]);
assertExpired(sec, 'naive stamp');
"""
    )


def test_x5_garbage_stamps_expire_without_throwing():
    """Empty, non-dates, and an offset-shaped impossible calendar all fail safe."""
    _run(
        """
now = at('2026-10-11T00:00:00Z');
const stamps = ['', 'soon', '2026-13-40T99:00:00+08:00'];
const secs = stamps.map(section);
const ctx = boot(secs);
secs.forEach((sec, i) => assertExpired(sec, JSON.stringify(stamps[i])));
ctx.window.mmPbExpire();
secs.forEach((sec, i) => assertExpired(sec, 'again ' + JSON.stringify(stamps[i])));
"""
    )


def test_x6_timer_rearmed_within_60s_when_deadline_is_days_away():
    """A deadline days out still re-arms with a delay of at most 60 seconds."""
    raw = _epoch_ms("2026-10-14T00:00:00Z") - _epoch_ms("2026-10-11T00:00:00Z")
    assert raw == 3 * 24 * 60 * 60 * 1000
    assert raw > 60_000
    _run(
        """
now = at('2026-10-11T00:00:00Z');
const raw = at('2026-10-14T00:00:00Z') - now;
assert.ok(raw > 60000, 'fixture deadline is more than a minute away');
assert.ok(raw > 2 * 24 * 60 * 60 * 1000, 'fixture deadline is days away');
const sec = section('2026-10-14T00:00:00Z');
const ctx = boot([sec]);
assertCurrent(sec, 'days away');
let live = [...ctx.pending.values()];
assert.equal(live.length, 1, 'initial arm');
assert.ok(live[0].ms >= 1 && live[0].ms <= 60000, 'initial delay ' + live[0].ms);
now += live[0].ms;
live[0].fn();
live = [...ctx.pending.values()];
assert.equal(live.length, 1, 're-armed once');
assert.ok(live[0].ms >= 1 && live[0].ms <= 60000, 're-arm delay ' + live[0].ms);
assertCurrent(sec, 'still current after one tick');
"""
    )


def test_x7_mm_pb_expire_twice_does_not_double_install():
    """Two mmPbExpire calls leave one live timer and one listener per wake event."""
    _run(
        """
function wakeCounts(ctx) {
  return {
    visibilitychange: nlisteners(ctx.listeners.document, 'visibilitychange'),
    pageshow: nlisteners(ctx.listeners.window, 'pageshow'),
    focus: nlisteners(ctx.listeners.window, 'focus'),
    DOMContentLoaded: nlisteners(ctx.listeners.document, 'DOMContentLoaded'),
  };
}
now = at('2026-10-11T00:00:00Z');
const started = boot([section('2026-10-20T00:00:00Z')]);
assert.equal(wakeCounts(started).visibilitychange, 1);
assert.equal(wakeCounts(started).pageshow, 1);
assert.equal(wakeCounts(started).focus, 1);
assert.equal(wakeCounts(started).DOMContentLoaded, 0);
assert.equal(started.pending.size, 1, 'one timer after start');
started.window.mmPbExpire();
started.window.mmPbExpire();
assert.equal(wakeCounts(started).visibilitychange, 1, 'visibilitychange doubled');
assert.equal(wakeCounts(started).pageshow, 1, 'pageshow doubled');
assert.equal(wakeCounts(started).focus, 1, 'focus doubled');
assert.equal(wakeCounts(started).DOMContentLoaded, 0);
assert.equal(started.pending.size, 1, 'two mmPbExpire calls left two timers');
started.listeners.window.pageshow[0]();
started.listeners.window.focus[0]();
started.document.hidden = false;
started.listeners.document.visibilitychange[0]();
assert.equal(wakeCounts(started).visibilitychange, 1);
assert.equal(wakeCounts(started).pageshow, 1);
assert.equal(wakeCounts(started).focus, 1);
assert.equal(started.pending.size, 1, 'wake listeners installed another timer');

now = at('2026-10-11T00:00:00Z');
const loading = boot([section('2026-10-20T00:00:00Z')], 'loading');
assert.equal(wakeCounts(loading).DOMContentLoaded, 1);
assert.equal(wakeCounts(loading).visibilitychange, 0);
assert.equal(wakeCounts(loading).pageshow, 0);
assert.equal(wakeCounts(loading).focus, 0);
assert.equal(loading.pending.size, 0, 'start has not run');
loading.window.mmPbExpire();
loading.window.mmPbExpire();
assert.equal(wakeCounts(loading).DOMContentLoaded, 1);
assert.equal(wakeCounts(loading).visibilitychange, 0);
assert.equal(wakeCounts(loading).pageshow, 0);
assert.equal(wakeCounts(loading).focus, 0);
assert.equal(loading.pending.size, 1, 'two early mmPbExpire calls left two timers');
loading.listeners.document.DOMContentLoaded[0]();
assert.equal(wakeCounts(loading).visibilitychange, 1);
assert.equal(wakeCounts(loading).pageshow, 1);
assert.equal(wakeCounts(loading).focus, 1);
assert.equal(loading.pending.size, 1);
loading.window.mmPbExpire();
loading.window.mmPbExpire();
assert.equal(wakeCounts(loading).visibilitychange, 1);
assert.equal(wakeCounts(loading).pageshow, 1);
assert.equal(wakeCounts(loading).focus, 1);
assert.equal(wakeCounts(loading).DOMContentLoaded, 1);
assert.equal(loading.pending.size, 1, 'calls after load left two timers');
"""
    )


def test_x8_two_sections_expire_on_their_own_stamps():
    """US 17:00+08 and a second section at 12:00-04 expire at 09:00Z and 16:00Z."""
    assert _epoch_ms("2026-10-12T17:00:00+08:00") == _epoch_ms("2026-10-12T09:00:00Z")
    assert _epoch_ms("2026-10-12T12:00:00-04:00") == _epoch_ms("2026-10-12T16:00:00Z")
    _run(
        """
const us = section('2026-10-12T17:00:00+08:00');
const other = section('2026-10-12T12:00:00-04:00');
now = at('2026-10-12T08:59:59Z');
const ctx = boot([other, us]);
assertCurrent(us, 'us early');
assertCurrent(other, 'other early');
now = at('2026-10-12T09:00:00Z');
ctx.window.mmPbExpire();
assertExpired(us, 'us at 09:00Z');
assertCurrent(other, 'other still current at 09:00Z');
now = at('2026-10-12T15:59:59Z');
ctx.window.mmPbExpire();
assertExpired(us, 'us stays expired');
assertCurrent(other, 'other one second before its own deadline');
now = at('2026-10-12T16:00:00Z');
ctx.window.mmPbExpire();
assertExpired(us, 'us still expired at 16:00Z');
assertExpired(other, 'other at 16:00Z');
"""
    )


def test_x9_far_future_timeout_stays_inside_signed_32_bit():
    """A valid_until more than 7 days out must not arm a delay above 2**31-1 ms.

    Browsers store setTimeout's delay in a signed 32-bit integer. 2**31-1 ms is
    about 24.8 days, so a 40-day stamp is past both the 7-day scenario and that
    ceiling. An uncapped deadline-minus-now would be an illegal delay.
    """
    raw = _epoch_ms("2026-11-20T00:00:00Z") - _epoch_ms("2026-10-11T00:00:00Z")
    assert raw == 40 * 24 * 60 * 60 * 1000
    assert raw > 7 * 24 * 60 * 60 * 1000
    assert raw > 2**31 - 1
    _run(
        """
const MAX_DELAY = 2147483647;
now = at('2026-10-11T00:00:00Z');
const stamp = '2026-11-20T00:00:00Z';
const raw = at(stamp) - now;
assert.equal(MAX_DELAY, 2 ** 31 - 1);
assert.ok(raw > 7 * 24 * 60 * 60 * 1000, 'fixture is more than 7 days out');
assert.ok(raw > MAX_DELAY, 'uncapped delay would exceed signed 32-bit setTimeout');
const sec = section(stamp);
const ctx = boot([sec]);
assertCurrent(sec, 'far future still current');
const live = [...ctx.pending.values()];
assert.equal(live.length, 1, 'a far-future section still arms one timer');
assert.ok(live[0].ms >= 1, 'delay ' + live[0].ms);
assert.ok(live[0].ms <= MAX_DELAY, 'delay ' + live[0].ms);
"""
    )


_FOCUS_FIXTURE = r"""
function node(name, kids = []) {
  return {
    name, kids,
    contains(other) {
      if (other === this) return true;
      return this.kids.some((kid) => kid.contains(other));
    },
  };
}
function dialogWith(stamp) {
  const summary = node('history-summary');
  const current = node('pbx-current', [summary]);
  const sub = node('rrp-sub');
  const why = node('why-summary');
  const forecast = node('rrp-forecast', [why]);
  const sec = section(stamp);
  const inner = node('root-inner', [current, sub, forecast]);
  const close = node('close');
  const dlg = node('dlg', [close]);
  let focused = null;
  const focusable = (n) => { n.focus = () => { focused = n; }; return n; };
  [close, dlg, summary, why].forEach(focusable);
  sec.contains = (other) => inner.contains(other);
  sec.closest = (sel) => (sel === '[role="dialog"]' ? dlg : null);
  sec.querySelectorAll = (sel) => {
    if (sel !== '.pbx-current, .rrp-sub') throw new Error('unexpected root query: ' + sel);
    return [current, sub];
  };
  dlg.querySelector = (sel) => (sel === 'button[aria-label="Close"]' ? close : null);
  return {sec, summary, why, close, dlg, focused: () => focused};
}
"""


def test_x10_expiry_hands_focus_from_the_hidden_history_to_the_close_button():
    """Focus on the history summary moves to the dialog's close button at expiry.

    Expiry hides `.pbx-current`, which holds that summary. Without the hand-off
    keyboard focus would fall to the page behind an aria-modal dialog.
    """
    _run(
        _FOCUS_FIXTURE
        + """
now = at('2026-10-12T08:59:59Z');
const f = dialogWith('2026-10-12T17:00:00+08:00');
const ctx = boot([f.sec]);
ctx.document.activeElement = f.summary;
assertCurrent(f.sec, 'before');
assert.equal(f.focused(), null, 'nothing moved while current');
now = at('2026-10-12T09:00:00Z');
ctx.window.mmPbExpire();
assertExpired(f.sec, 'at deadline');
assert.equal(f.focused(), f.close, 'focus went to the close button');
"""
    )


def test_x11_expiry_leaves_focus_that_stays_visible_alone():
    """Focus on a control expiry keeps visible, or outside the section, is not moved."""
    _run(
        _FOCUS_FIXTURE
        + """
now = at('2026-10-12T09:00:00Z');
const kept = dialogWith('2026-10-12T17:00:00+08:00');
const outside = dialogWith('2026-10-12T17:00:00+08:00');
const ctx = boot([]);
ctx.document.querySelectorAll = () => [kept.sec, outside.sec];
ctx.document.activeElement = kept.why;
ctx.window.mmPbExpire();
assertExpired(kept.sec, 'kept');
assertExpired(outside.sec, 'outside');
assert.equal(kept.focused(), null, 'the forecast summary stays visible, so focus stays');
assert.equal(outside.focused(), null, 'focus in another section is not taken');
"""
    )


def test_x12_expiry_without_a_close_button_focuses_the_dialog():
    """A dialog shell without a labelled close button still keeps focus inside it."""
    _run(
        _FOCUS_FIXTURE
        + """
now = at('2026-10-12T09:00:00Z');
const f = dialogWith('2026-10-12T17:00:00+08:00');
f.dlg.querySelector = () => null;
const ctx = boot([]);
ctx.document.querySelectorAll = () => [f.sec];
ctx.document.activeElement = f.summary;
ctx.window.mmPbExpire();
assertExpired(f.sec, 'no close button');
assert.equal(f.focused(), f.dlg, 'focus stays on the dialog itself');
"""
    )
