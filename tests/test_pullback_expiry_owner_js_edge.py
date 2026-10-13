"""Edge cases for the shipped pullback expiry owner's clock handling.

Same Node harness as ``tests/test_pullback_expiry_owner_js.py`` — imported,
not copied — exercised on edges that file does not cover: three spellings of
one deadline expiring together, unusable stamps, deadlines across the US DST
fallback, per-section independence, the 60 s re-arm cap, wake-event
re-checks, and idempotent expiry. Every stamp here is synthetic.
"""
import json
import os
import shutil
import subprocess

import pytest

from tests import test_pullback_expiry_owner_js as harness


def _run_json(body: str, tz: str) -> dict:
    """Run a body under one IANA zone and return the JSON line it printed.

    Mirrors the sibling's ``_node_raw`` contract — skip without Node locally,
    fail in CI — but passes ``TZ`` through and keeps stdout, so a cross-zone
    body can report the offsets it actually ran under.
    """
    node = shutil.which("node")
    if not node:
        if os.environ.get("CI"):
            pytest.fail("Node is required in CI to execute the shipped expiry owner")
        pytest.skip("Node is required to execute the shipped expiry owner")
    result = subprocess.run(
        ["node", "-e", harness._HARNESS + "\n" + body],
        input=harness._OWNER.read_text(encoding="utf-8"),
        text=True,
        capture_output=True,
        timeout=20,
        env=dict(os.environ, TZ=tz),
    )
    assert result.returncode == 0, result.stdout + result.stderr
    printed = [line for line in result.stdout.splitlines() if line.strip()]
    assert printed, "cross-zone body printed no JSON"
    return json.loads(printed[-1])


def test_e1_z_plus08_and_minus04_denoting_one_instant_expire_together():
    """Z, +08:00 and -04:00 spellings of one deadline expire on that instant."""
    stamps = [
        "2026-10-12T09:00:00Z",
        "2026-10-12T17:00:00+08:00",
        "2026-10-12T05:00:00-04:00",
    ]
    epochs = {harness._epoch_ms(stamp) for stamp in stamps}
    assert len(epochs) == 1, "fixture stamps are not one instant"
    harness._run(
        """
const stamps = ['2026-10-12T09:00:00Z', '2026-10-12T17:00:00+08:00', '2026-10-12T05:00:00-04:00'];
assert.equal(new Set(stamps.map(at)).size, 1, 'fixture stamps are not one instant');
stamps.forEach((stamp) => expectBoundary(stamp, '2026-10-12T08:59:59Z', '2026-10-12T09:00:00Z'));
now = at('2026-10-12T08:59:59Z');
const secs = stamps.map(section);
const ctx = boot(secs);
secs.forEach((sec, i) => assertCurrent(sec, stamps[i] + ' one second before'));
now = at('2026-10-12T09:00:00Z');
ctx.window.mmPbExpire();
secs.forEach((sec, i) => assertExpired(sec, stamps[i] + ' on the shared instant'));
"""
    )


@pytest.mark.xfail(
    strict=True,
    reason="PRODUCT FINDING: the shipped owner expires a naive stamp (no offset) "
    "instead of leaving the section current — observed on the shipped template "
    "under Node. Flagged to the orchestrator; strict so a fix unmasks this.",
)
def test_e2_naive_stamp_leaves_the_section_current():
    """A stamp with no zone leaves the section current and throws nothing.

    The packet expectation is that a section stays current unless its stamp
    denotes a passed instant. The shipped owner treats a zone-less stamp as
    expired fail-safe (template comment 'a bare local time would move with
    the viewer's zone'), so this fails today and is recorded xfail strict.
    """
    harness._run(
        """
now = at('2026-10-12T00:00:00Z');
const naive = '2026-10-12T17:00:00';
const localMs = Date.parse(naive);
assert.equal(Number.isFinite(localMs), true, 'engine parses the naive stamp as local');
assert.ok(localMs > now, 'even the local reading is ahead of the clock');
const sec = section(naive);
const ctx = boot([sec]);
assertCurrent(sec, 'naive stamp, clock before every reading');
ctx.window.mmPbExpire();
assertCurrent(sec, 'naive stamp after an explicit re-check');
"""
    )


@pytest.mark.xfail(
    strict=True,
    reason="PRODUCT FINDING: the shipped owner expires unparseable stamps "
    "('', 'soon', an impossible calendar date) instead of leaving the section "
    "current — observed on the shipped template under Node. Flagged to the "
    "orchestrator; strict so a fix unmasks this.",
)
def test_e2_garbage_stamps_leave_the_section_current():
    """Unparseable stamps leave the section current and throw nothing.

    Packet expectation: garbage in, section still current, no exception. The
    shipped owner expires them fail-safe, so this fails today and is
    recorded xfail strict.
    """
    harness._run(
        """
now = at('2026-10-12T00:00:00Z');
const stamps = ['', 'soon', '2026-13-40T00:00:00Z'];
const secs = stamps.map(section);
const ctx = boot(secs);
secs.forEach((sec, i) => assertCurrent(sec, JSON.stringify(stamps[i])));
ctx.window.mmPbExpire();
secs.forEach((sec, i) => assertCurrent(sec, 'again ' + JSON.stringify(stamps[i])));
"""
    )


def test_e2_unusable_stamps_never_throw_and_stay_coherent():
    """Naive and garbage stamps run every path without an exception.

    Zone-neutral on purpose: each section must end in a coherent state
    (either still underway or visibly unavailable), whatever the expiry
    policy for unusable stamps turns out to be.
    """
    harness._run(
        """
const PHASES = new Set(['underway', 'unavailable']);
const EN = new Set(['Pullback underway', 'Price update needed']);
const ZH = new Set(['回调进行中', '价格数据待更新']);
function sane(sec, label) {
  assert.ok(PHASES.has(sec.attrs['data-pb-phase']), label + ' phase ' + sec.attrs['data-pb-phase']);
  assert.ok(EN.has(sec.en.textContent), label + ' heading ' + sec.en.textContent);
  assert.ok(ZH.has(sec.zh.textContent), label + ' zh heading ' + sec.zh.textContent);
}
const stamps = ['', 'soon', '2026-13-40T00:00:00Z', '2026-10-12T17:00:00'];
const live = stamps.map(section);
const ctx = boot(live);
ctx.window.mmPbExpire();
ctx.window.mmPbExpire();
ctx.listeners.window.pageshow[0]();
ctx.listeners.window.focus[0]();
ctx.listeners.document.visibilitychange[0]();
live.forEach((sec, i) => sane(sec, JSON.stringify(stamps[i])));
const loading = stamps.map(section);
const early = boot(loading, 'loading');
early.listeners.document.DOMContentLoaded[0]();
early.window.mmPbExpire();
loading.forEach((sec, i) => sane(sec, 'loading ' + JSON.stringify(stamps[i])));
"""
    )


def test_e3_deadlines_across_us_dst_fallback_expire_on_absolute_instants():
    """Either side of the 2026-11-01 fallback, expiry follows the absolute instant.

    01:59:59-04:00 is 05:59:59Z and 01:01:00-05:00 is 06:01:00Z: the EST
    stamp's wall clock reads earlier but its instant is later, so only an
    absolute reading expires the EDT stamp first and keeps the EST stamp
    current for another minute.
    """
    assert (
        harness._epoch_ms("2026-11-01T01:59:59-04:00") == harness._epoch_ms("2026-11-01T05:59:59Z")
    )
    assert (
        harness._epoch_ms("2026-11-01T01:01:00-05:00") == harness._epoch_ms("2026-11-01T06:01:00Z")
    )
    assert (
        harness._epoch_ms("2026-11-01T01:01:00-05:00")
        - harness._epoch_ms("2026-11-01T01:59:59-04:00")
        == 61_000
    )
    harness._run(
        """
const EDT = '2026-11-01T01:59:59-04:00';
const EST = '2026-11-01T01:01:00-05:00';
assert.equal(at(EDT), at('2026-11-01T05:59:59Z'), 'EDT fixture instant');
assert.equal(at(EST), at('2026-11-01T06:01:00Z'), 'EST fixture instant');
const edt = section(EDT);
const est = section(EST);
now = at('2026-11-01T05:59:58Z');
const ctx = boot([est, edt]);
assertCurrent(edt, 'edt before the fallback');
assertCurrent(est, 'est before the fallback');
now = at('2026-11-01T05:59:59Z');
ctx.window.mmPbExpire();
assertExpired(edt, 'edt on its absolute instant');
assertCurrent(est, 'est current at 05:59:59Z although its wall clock reads earlier');
now = at('2026-11-01T06:00:59Z');
ctx.window.mmPbExpire();
assertExpired(edt, 'edt stays expired');
assertCurrent(est, 'est one second before its own instant');
now = at('2026-11-01T06:01:00Z');
ctx.window.mmPbExpire();
assertExpired(edt, 'edt still expired');
assertExpired(est, 'est on its absolute instant');
"""
    )


def test_e3_expiry_decisions_do_not_move_with_the_viewer_zone():
    """One page, two IANA zones: identical expiry decisions.

    Date.parse of an offset stamp is zone-independent, so America/New_York
    and Asia/Shanghai must classify both fallback-hour stamps alike. The
    probe offset guards against a platform that ignores TZ, where the
    cross-check would be vacuous rather than passing.
    """
    body = """
const stamps = ['2026-11-01T01:59:59-04:00', '2026-11-01T01:01:00-05:00'];
const secs = stamps.map(section);
now = at('2026-11-01T05:59:59Z');
const ctx = boot(secs);
ctx.window.mmPbExpire();
console.log(JSON.stringify({
  offset: new Date(0).getTimezoneOffset(),
  state: secs.map((sec) => sec.attrs['data-pb-phase']),
}));
"""
    new_york = _run_json(body, "America/New_York")
    shanghai = _run_json(body, "Asia/Shanghai")
    if new_york["offset"] == shanghai["offset"]:
        pytest.skip("TZ env not honoured here; the cross-zone check is vacuous")
    assert new_york["state"] == ["unavailable", "underway"], new_york
    assert shanghai["state"] == new_york["state"], "viewer zone moved the expiry"


def test_e4_two_sections_expire_independently():
    """Two sections on one page expire on their own deadlines and no other.

    The second section is deliberately first in the DOM, so document order
    cannot explain the outcome, and the shared timer is checked to target
    the NEAREST deadline rather than either section alone.
    """
    assert (
        harness._epoch_ms("2026-10-12T17:00:00+08:00") == harness._epoch_ms("2026-10-12T09:00:00Z")
    )
    assert (
        harness._epoch_ms("2026-10-12T09:00:00Z") - harness._epoch_ms("2026-10-12T02:00:00Z")
        == 7 * 60 * 60 * 1000
    )
    harness._run(
        """
const first = section('2026-10-12T02:00:00Z');
const second = section('2026-10-12T17:00:00+08:00');
now = at('2026-10-12T00:00:00Z');
const ctx = boot([second, first]);
assertCurrent(first, 'first early');
assertCurrent(second, 'second early');
let live = [...ctx.pending.values()];
assert.equal(live.length, 1, 'one shared timer');
assert.ok(live[0].ms >= 1 && live[0].ms <= 60000, 'initial delay ' + live[0].ms);
now = at('2026-10-12T01:59:59Z');
ctx.window.mmPbExpire();
assertCurrent(first, 'one second before its own deadline');
assertCurrent(second, 'second untouched');
now = at('2026-10-12T02:00:00Z');
ctx.window.mmPbExpire();
assertExpired(first, 'first on its instant');
assertCurrent(second, 'second still current after the first expired');
now = at('2026-10-12T08:59:59Z');
ctx.window.mmPbExpire();
assertExpired(first, 'first stays expired');
assertCurrent(second, 'second one second out');
now = at('2026-10-12T09:00:00Z');
ctx.window.mmPbExpire();
assertExpired(first, 'first still expired');
assertExpired(second, 'second on its own instant');

const near = section('2026-10-12T00:00:40Z');
const nearer = section('2026-10-12T00:00:10Z');
now = at('2026-10-12T00:00:00Z');
const ctx2 = boot([near, nearer]);
const tick = [...ctx2.pending.values()];
assert.equal(tick.length, 1, 'one shared timer for the close pair');
assert.ok(tick[0].ms >= 10001 && tick[0].ms <= 10010,
  'timer targets the nearest deadline, got ' + tick[0].ms);
now += tick[0].ms;
tick[0].fn();
assertExpired(nearer, 'nearer expired by the timer');
assertCurrent(near, 'near untouched by the first tick');
const next = [...ctx2.pending.values()];
assert.equal(next.length, 1, 're-armed for the remaining section');
assert.ok(next[0].ms >= 29991 && next[0].ms <= 30000,
  'second timer targets the later deadline, got ' + next[0].ms);
now += next[0].ms;
next[0].fn();
assertExpired(near, 'near expired by the second tick');
assert.equal(ctx2.pending.size, 0, 'nothing re-armed once both are expired');
"""
    )


def test_e5_days_out_deadline_rearms_at_the_60s_cap():
    """A deadline days away re-arms every tick at exactly the 60 s cap.

    The stub records every setTimeout delay; each one must be the cap while
    the deadline is far, shrink inside the last minute, and stop once the
    section has expired.
    """
    raw = harness._epoch_ms("2026-10-18T00:00:00Z") - harness._epoch_ms("2026-10-11T00:00:00Z")
    assert raw == 7 * 24 * 60 * 60 * 1000
    assert raw > 60000
    harness._run(
        """
now = at('2026-10-11T00:00:00Z');
const deadline = at('2026-10-18T00:00:00Z');
assert.ok(deadline - now > 5 * 24 * 60 * 60 * 1000, 'fixture deadline is days out');
const sec = section('2026-10-18T00:00:00Z');
const ctx = boot([sec]);
assertCurrent(sec, 'days out');
let live = [...ctx.pending.values()];
assert.equal(live.length, 1, 'initial arm');
assert.equal(live[0].ms, 60000, 'initial delay ' + live[0].ms + ' is not the cap');
for (let i = 0; i < 60; i += 1) {
  now += live[0].ms;
  live[0].fn();
  live = [...ctx.pending.values()];
  assert.equal(live.length, 1, 're-arm ' + i);
  assert.equal(live[0].ms, 60000, 're-arm ' + i + ' delay ' + live[0].ms + ' is not the cap');
  assertCurrent(sec, 'still current on tick ' + i);
}
now = deadline - 40000;
live[0].fn();
live = [...ctx.pending.values()];
assert.equal(live.length, 1, 'armed inside the last minute');
assert.ok(live[0].ms > 1 && live[0].ms <= 60000, 'last-minute delay ' + live[0].ms);
assert.ok(now + live[0].ms >= deadline, 'timer lands at or past the deadline');
now += live[0].ms;
live[0].fn();
assertExpired(sec, 'expired by the final tick');
assert.equal(ctx.pending.size, 0, 'an expired page re-armed a timer');
"""
    )


_WAKE_FIRE = {
    "pageshow": "ctx.listeners.window.pageshow[0]()",
    "focus": "ctx.listeners.window.focus[0]()",
    "visibilitychange": "ctx.listeners.document.visibilitychange[0]()",
}


@pytest.mark.parametrize("event", sorted(_WAKE_FIRE))
def test_e6_wake_event_expires_after_the_clock_advanced(event):
    """Each wake event re-checks and expires once the clock passed the deadline.

    The stub's pending timer is wrapped with a sentinel and never invoked,
    so the expiry is provably the event's work, not a firing timer.
    """
    harness._run(
        """
now = at('2026-10-12T08:59:30Z');
const sec = section('2026-10-12T09:00:00Z');
const ctx = boot([sec]);
assertCurrent(sec, '30 seconds out');
let live = [...ctx.pending.values()];
assert.equal(live.length, 1, 'initial arm');
let fired = false;
const real = live[0].fn;
live[0].fn = () => { fired = true; real(); };
now = at('2026-10-12T09:00:05Z');
EVENT;
assert.equal(fired, false, 'the timer never fired');
assertExpired(sec, 'the EVENT handler expired the section');
assert.equal(ctx.pending.size, 0, 'stale timer was cleared, nothing re-armed');
""".replace("EVENT;", _WAKE_FIRE[event])
    )


def test_e6_hidden_tab_does_not_recheck_until_visible():
    """A visibilitychange while hidden does nothing; becoming visible re-checks."""
    harness._run(
        """
now = at('2026-10-12T08:59:30Z');
const sec = section('2026-10-12T09:00:00Z');
const ctx = boot([sec]);
ctx.document.hidden = true;
ctx.listeners.document.visibilitychange[0]();
assertCurrent(sec, 'hidden tab does not re-check');
ctx.document.hidden = false;
now = at('2026-10-12T09:00:05Z');
ctx.listeners.document.visibilitychange[0]();
assertExpired(sec, 'becoming visible re-checks and expires');
"""
    )


def test_e7_mm_pb_expire_is_idempotent():
    """Two mmPbExpire calls leave one pb-expired class and the same notice.

    Observed while writing this: the owner re-processes already-expired
    sections on every pass (classList.add and the heading writes run again
    per call), so idempotence here means the resulting STATE — one class in
    the set, one phase, the same notice text — not write-once bookkeeping.
    The counting stub records the writes so the heading assertions see the
    live objects a browser would re-write, and nothing pins the count.
    """
    harness._run(
        """
function countingSection(stamp) {
  const attrs = {'data-pb-valid-until': stamp, 'data-pb-phase': 'underway'};
  const classes = new Set(['rrp', 'pbx']);
  const adds = [];
  const writes = [];
  const en = {text: 'Pullback underway'};
  const zh = {text: '回调进行中'};
  Object.defineProperty(en, 'textContent', {
    get() { return en.text; },
    set(value) { en.text = value; writes.push('en=' + value); },
  });
  Object.defineProperty(zh, 'textContent', {
    get() { return zh.text; },
    set(value) { zh.text = value; writes.push('zh=' + value); },
  });
  const heading = {querySelector(sel) {
    if (sel === '.l-en') return en;
    if (sel === '.l-zh') return zh;
    return null;
  }};
  return {
    en, zh, attrs, adds, writes, classes,
    getAttribute(name) {
      return Object.prototype.hasOwnProperty.call(attrs, name) ? attrs[name] : null;
    },
    setAttribute(name, value) { attrs[name] = String(value); },
    classList: {add(name) { adds.push(name); classes.add(name); }},
    querySelector(sel) { return sel === '.pbx-heading h2' ? heading : null; },
  };
}
now = at('2026-10-12T10:00:00Z');
const sec = countingSection('2026-10-12T09:00:00Z');
const ctx = boot([sec]);
assertExpired(sec, 'start expires the past deadline');
ctx.window.mmPbExpire();
ctx.window.mmPbExpire();
assert.equal(sec.classes.size, 3, 'unexpected class set ' + [...sec.classes].join(' '));
assert.equal(sec.classes.has('pb-expired'), true, 'pb-expired class missing');
assert.equal(sec.attrs['data-pb-phase'], 'unavailable', 'phase moved');
assertExpired(sec, 'still expired after two more calls');
assert.equal(sec.en.textContent, 'Price update needed', 'en heading changed');
assert.equal(sec.zh.textContent, '价格数据待更新', 'zh heading changed');
assert.ok(sec.writes.every((w) => w === 'en=Price update needed' || w === 'zh=价格数据待更新'),
  'a heading write carried a third value: ' + sec.writes.join(', '));
assert.equal(ctx.pending.size, 0, 'an expired page re-armed a timer');
"""
    )
