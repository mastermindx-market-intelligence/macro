"""Strict civil-time reading of the pullback expiry stamp.

Date.parse rolls impossible civil times forward, so a section can keep
claiming a current assessment. These cases are synthetic and run the shipped
owner under the Node harness in tests/test_pullback_expiry_owner_js.py.
The producer writes ``datetime.isoformat()`` of a UTC instant with whole
seconds (``2026-10-12T21:00:00+00:00``); seconds are required, and a fraction
is accepted only when every digit is zero.
"""
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from bs4 import BeautifulSoup

from tests import test_pullback_expiry_owner_js as harness
from tests.test_risk_radar_pullback_depth_template import native_view, render

_ROOT = Path(__file__).resolve().parents[1]
_UNTIL_RULE = ".rrp.pb-expired .rrp-until{display:none}"
_UNTIL_INNER = (
    "<br>\n"
    "      {{ t('Current until','有效至') }} "
    '<time datetime="{{ o.get(\'valid_until\')|e }}">{{ _vu_disp|e }}</time>'
)

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


def test_expired_section_hides_the_current_until_stamp():
    """A past deadline adds pb-expired, and that class hides the until stamp.

    The span wraps only the line break and the Current-until clock. The time
    element's datetime stays the producer's valid_until.
    """
    source = (_ROOT / "templates" / "_risk_radar_pullback_depth.html.j2").read_text(encoding="utf-8")
    wrapped = re.search(
        r"\{%- if current and _vu_disp %\}<span class=\"rrp-until\">(.*?)</span>\{% endif %\}",
        source,
        re.S,
    )
    assert wrapped, "Current until is not wrapped in span.rrp-until"
    assert wrapped.group(1) == _UNTIL_INNER
    assert source.count('class="rrp-until"') == 1
    assert "o.get('asof')" not in wrapped.group(1)

    css = (_ROOT / "templates" / "_risk_radar_pullback_depth.css.j2").read_text(encoding="utf-8")
    assert css.count(_UNTIL_RULE) == 1
    assert "#" not in _UNTIL_RULE and "color" not in _UNTIL_RULE

    html = render(native_view("us"), "us")
    soup = BeautifulSoup(html, "html.parser")
    section = soup.select_one("section.rrp")
    assert section.get("data-pb-phase") == "underway"
    assert "pb-expired" not in (section.get("class") or [])
    stamp = section.get("data-pb-valid-until")
    until = section.select_one("span.rrp-until")
    assert until is not None and until.parent.get("class") == ["rrp-stamp"]
    times = until.find_all("time")
    assert [node.get("datetime") for node in times] == [stamp]
    assert until.select_one(".l-en").get_text() == "Current until"
    settled = [node for node in section.select(".rrp-stamp time") if node is not times[0]]
    assert len(settled) == 1 and until not in settled[0].parents
    assert soup.select(".rrp.pb-expired .rrp-until") == []
    section["class"] = list(section.get("class") or []) + ["pb-expired"]
    assert soup.select(".rrp.pb-expired .rrp-until") == [until]

    later = "2026-10-02T00:00:00Z"
    assert harness._epoch_ms(stamp) < harness._epoch_ms(later)
    harness._run(
        "now = at(%r);\n"
        "const sec = section(%r);\n"
        "boot([sec]);\n"
        "assertExpired(sec, 'rendered US view past its deadline');\n"
        % (later, stamp)
    )
