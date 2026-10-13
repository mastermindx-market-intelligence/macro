"""Strict civil-time reading of the pullback expiry stamp.

Date.parse rolls impossible civil times forward, so a section can keep
claiming a current assessment. These cases are synthetic and run the shipped
owner under the Node harness in tests/test_pullback_expiry_owner_js.py.
The producer writes ``datetime.isoformat()`` of a UTC instant with whole
seconds (``2026-10-12T21:00:00+00:00``); seconds are required, and a fraction
is accepted only when every digit is zero.
"""
from datetime import datetime, timedelta, timezone

from tests import test_pullback_expiry_owner_js as harness

_NOW = datetime(2026, 10, 12, tzinfo=timezone.utc)
_DAY = timedelta(days=1)


def _z(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def test_impossible_civil_stamps_expire_immediately():
    """November 31, hour 24, and year 9999 are not a current assessment.

    Each clock is still before the instant Date.parse would roll the stamp
    into, so a lenient parse would leave the section current.
    """
    harness._run(
        """
now = at('2026-11-30T00:00:00Z');
const nov = section('2026-11-31T00:00:00Z');
boot([nov]);
assertExpired(nov, '2026-11-31');

now = at('2026-10-12T23:00:00Z');
const hour = section('2026-10-12T24:00:00Z');
boot([hour]);
assertExpired(hour, 'hour 24');

now = at('2026-10-12T00:00:00Z');
const far = section('9999-12-31T00:00:00Z');
boot([far]);
assertExpired(far, 'year 9999');
"""
    )


def test_february_29_follows_the_gregorian_month_length():
    """2026-02-29 is not a day; 2028-02-29 is, and it flips on that instant.

    1900 is not a leap year and 2000 is. The month length has to come from
    the UTC calendar, not from a year divisible by 4.
    """
    harness._run(
        """
now = at('2026-02-28T12:00:00Z');
const plain = section('2026-02-29T00:00:00Z');
boot([plain]);
assertExpired(plain, '2026-02-29');

now = at('1900-02-28T00:00:00Z');
const century = section('1900-02-29T00:00:00Z');
boot([century]);
assertExpired(century, '1900-02-29');

function flipsOn(stamp) {
  const sec = section(stamp);
  now = at(stamp) - 1;
  const ctx = boot([sec]);
  assertCurrent(sec, stamp + ' 1ms before');
  now = at(stamp);
  ctx.window.mmPbExpire();
  assertExpired(sec, stamp + ' on its instant');
}
flipsOn('2028-02-29T00:00:00Z');
flipsOn('2000-02-29T00:00:00Z');
"""
    )


def test_producer_forms_expire_on_their_millisecond():
    """+00:00, Z, and -04:00 of one instant stay current until that instant."""
    same = {
        "2026-10-12T21:00:00+00:00",
        "2026-10-12T21:00:00Z",
        "2026-10-12T17:00:00-04:00",
    }
    assert len({harness._epoch_ms(stamp) for stamp in same}) == 1
    harness._run(
        """
const stamps = [
  '2026-10-12T21:00:00+00:00',
  '2026-10-12T21:00:00Z',
  '2026-10-12T17:00:00-04:00',
];
const instant = at(stamps[0]);
stamps.forEach((stamp) => assert.equal(at(stamp), instant, stamp));
stamps.forEach((stamp) => {
  const sec = section(stamp);
  now = instant - 1;
  const ctx = boot([sec]);
  assertCurrent(sec, stamp + ' 1ms before');
  now = instant;
  ctx.window.mmPbExpire();
  assertExpired(sec, stamp + ' at the instant');
});
"""
    )


def test_deadline_beyond_400_days_expires():
    """30 days ahead stays current; exactly 400 does too; 401 expires."""
    now_s = _z(_NOW)
    soon = _z(_NOW + 30 * _DAY)
    edge = _z(_NOW + 400 * _DAY)
    over = _z(_NOW + 401 * _DAY)
    harness._run(
        """
const day = 24 * 60 * 60 * 1000;
now = at(%r);
const soon = section(%r);
const edge = section(%r);
const over = section(%r);
assert.equal(at(%r) - now, 30 * day, '30-day fixture');
assert.equal(at(%r) - now, 400 * day, '400-day fixture');
assert.equal(at(%r) - now, 401 * day, '401-day fixture');
boot([soon, edge, over]);
assertCurrent(soon, '30 days ahead');
assertCurrent(edge, 'exactly 400 days ahead');
assertExpired(over, '401 days ahead');
"""
        % (now_s, soon, edge, over, soon, edge, over)
    )


def test_loose_spellings_expire():
    """Lowercase z, missing seconds, trailing garbage, and a leading space expire.

    Seconds are required: the producer always writes them. A zero fraction is
    the same whole second and still flips on that instant.
    """
    harness._run(
        """
now = at('2026-10-12T00:00:00Z');
const stamps = [
  '2026-12-01T00:00:00z',
  '2026-12-01T00:00Z',
  '2026-12-01T00:00:00Z trailing',
  ' 2026-12-01T00:00:00Z',
];
const secs = stamps.map(section);
const ctx = boot(secs);
secs.forEach((sec, i) => assertExpired(sec, JSON.stringify(stamps[i])));
ctx.window.mmPbExpire();
secs.forEach((sec, i) => assertExpired(sec, 'again ' + JSON.stringify(stamps[i])));

const zeroFrac = '2026-12-01T00:00:00.000Z';
const held = section(zeroFrac);
now = at(zeroFrac) - 1;
const later = boot([held]);
assertCurrent(held, 'zero fraction 1ms before');
now = at(zeroFrac);
later.window.mmPbExpire();
assertExpired(held, 'zero fraction on its instant');

const realFrac = section('2026-12-01T00:00:00.500Z');
now = at('2026-10-12T00:00:00Z');
boot([realFrac]);
assertExpired(realFrac, 'non-zero fraction');
"""
    )


def test_offset_hours_stop_at_14():
    """+14:00 is a deadline; +15:00 and a minute of 60 are not."""
    harness._run(
        """
now = at('2026-10-12T00:00:00Z');
const ok = section('2026-10-20T21:00:00+14:00');
const wide = section('2026-10-20T21:00:00+15:00');
const mins = section('2026-10-20T21:00:00+14:60');
boot([ok, wide, mins]);
assertCurrent(ok, '+14:00');
assert.equal(at('2026-10-20T21:00:00+14:00'), at('2026-10-20T07:00:00Z'));
assertExpired(wide, '+15:00');
assertExpired(mins, '+14:60');
"""
    )
