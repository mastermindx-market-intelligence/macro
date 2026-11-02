"""tests/test_rotation_observation_notification.py -- the FROZEN consumer contract for
defensive-rotation observations (DR3, ``category='sector_rotation_relative'``).

RED-first against ``lib/rotation_observation_notification.py``. Fully offline and fully
deterministic: every instant and every calendar answer is injected or monkeypatched, so
no test here reads the real clock, touches a database, or sends anything.

Fixtures use the PUBLISHED US cash slate, verified against
``lib.us_cash_calendar.expected_last_session`` rather than assumed:

* 2026-10-21 (Wed) is an ordinary full session (17:00 ET settle).
* 2026-10-23 (Fri) is an ordinary full session; 10-24/10-25 are the weekend.
* 2026-11-27 (Fri) is a PUBLISHED US HALF DAY (13:00 ET close, 14:00 ET settle).
* 2026-11-26 (Thanksgiving) is a full closure, so a bar due that evening rolls back
  to 2026-11-25.
"""
from __future__ import annotations

import math
from datetime import date, datetime, timezone

import pytest

from lib import rotation_observation_notification as R
from lib import us_cash_calendar as cal

UTC = timezone.utc


# --------------------------------------------------------------------------- #
# fixtures
# --------------------------------------------------------------------------- #
def _ratio(n: float, d: float) -> float:
    """The relative wealth identity the contract enforces."""
    return ((1.0 + n / 100.0) / (1.0 + d / 100.0) - 1.0) * 100.0


def _payload(**over) -> dict:
    n, d = 1.50, -0.50
    base = {
        "source": R.SOURCE,
        "category": R.CATEGORY,
        "authority": R.AUTHORITY,
        "kind": "observed_change",
        "observation_id": "obs-2026-10-21-a",
        "num": "XLV",
        "den": "XLK",
        "pair_id": "xlv-xlk",
        "event_as_of": "2026-10-21",
        "observed_at": "2026-10-21T22:00:00+00:00",
        "not_after": "2026-10-21T23:00:00+00:00",
        "source_as_of": "2026-10-21",
        "values": {"sessions": 2, "numerator_return_pct": n,
                   "denominator_return_pct": d, "ratio_return_pct": _ratio(n, d)},
    }
    base.update(over)
    return base


# An ordinary full session, observed after the 17:00 ET settle, evaluated the same day.
OBS = datetime(2026, 10, 21, 22, 0, tzinfo=UTC)
NOW = datetime(2026, 10, 21, 22, 30, tzinfo=UTC)


def test_the_fixture_calendar_is_the_one_this_file_assumes():
    """Guard the fixture itself: if the published slate ever moves, this file's
    expected dates must move with it rather than silently testing the wrong day."""
    assert cal.expected_last_session(OBS) == date(2026, 10, 21)
    assert cal.expected_last_session(NOW) == date(2026, 10, 21)
    assert cal.expected_last_session(datetime(2026, 10, 24, 12, 0, tzinfo=UTC)) == date(2026, 10, 23)
    assert cal.expected_last_session(datetime(2026, 11, 27, 18, 0, tzinfo=UTC)) == date(2026, 11, 25)
    assert cal.expected_last_session(datetime(2026, 11, 27, 19, 0, tzinfo=UTC)) == date(2026, 11, 27)


# --------------------------------------------------------------------------- #
# the routing selector
# --------------------------------------------------------------------------- #
def test_only_our_category_claims_the_observation_contract():
    assert R.claims_rotation_observation(_payload()) is True
    for other in ("thesis_window", "holdings_material_change", "fif_saved_issuer"):
        assert R.claims_rotation_observation(_payload(category=other)) is False
    # A foreign source wearing our CATEGORY still claims it -- the drain must judge it,
    # not route it to the generic mail.
    assert R.claims_rotation_observation(_payload(source="somewhere.else.v9")) is True


@pytest.mark.parametrize("not_a_dict", [None, [], "x", 7, object()])
def test_a_non_object_payload_never_claims_the_contract(not_a_dict):
    assert R.claims_rotation_observation(not_a_dict) is False


def test_our_source_under_a_foreign_category_is_not_ours():
    """Consent is carried by the category, so a foreign category is somebody else's
    row and must keep its own legacy behaviour untouched."""
    assert R.claims_rotation_observation(_payload(category="thesis_window")) is False


# --------------------------------------------------------------------------- #
# identity triple + kind
# --------------------------------------------------------------------------- #
def test_a_well_formed_observed_change_validates_and_normalizes_to_utc():
    obs = R.validate(_payload())
    assert obs.kind == "observed_change"
    assert obs.observation_id == "obs-2026-10-21-a"
    assert obs.previous_observation_id is None
    assert (obs.num, obs.den, obs.pair_id) == ("XLV", "XLK", "xlv-xlk")
    assert obs.event_as_of == date(2026, 10, 21)
    assert obs.observed_at == OBS
    assert obs.not_after == datetime(2026, 10, 21, 23, 0, tzinfo=UTC)
    assert obs.source_as_of == date(2026, 10, 21)
    assert obs.values["sessions"] == 2


def test_a_non_utc_offset_is_normalized_rather_than_shifted():
    p = _payload(observed_at="2026-10-21T18:00:00-04:00",   # == 22:00Z
                 not_after="2026-10-21T19:00:00-04:00")
    obs = R.validate(p)
    assert obs.observed_at == OBS
    assert obs.observed_at.tzinfo is UTC


@pytest.mark.parametrize("field,good,bad", [
    ("source", R.SOURCE, "macro.rotation_observation.v2"),
    ("authority", R.AUTHORITY, "actionable"),
    ("category", R.CATEGORY, "thesis_window"),
])
def test_identity_triple_fields_are_exact_not_prefix_matched(field, good, bad):
    assert R.validate(_payload(**{field: good}))
    with pytest.raises(ValueError):
        R.validate(_payload(**{field: bad}))
    with pytest.raises(ValueError):
        R.validate(_payload(**{field: None}))


def test_a_missing_identity_field_is_rejected():
    for field in ("source", "category", "authority", "kind"):
        p = _payload()
        p.pop(field)
        with pytest.raises(ValueError):
            R.validate(p)


@pytest.mark.parametrize("kind", ["", "observed", "OBSERVED_CHANGE", "buy_signal",
                                  "data_withdrawl", None, 7])
def test_kind_must_be_one_of_the_four_frozen_kinds(kind):
    with pytest.raises(ValueError):
        R.validate(_payload(kind=kind))


def test_every_frozen_kind_is_accepted():
    assert set(R.KINDS) == {"observed_change", "reversal", "data_withdrawal", "correction"}
    for kind in R.KINDS:
        kw = {"previous_observation_id": "obs-earlier"}
        if kind == "data_withdrawal":
            kw.update({"values": None, "source_as_of": None})
        assert R.validate(_payload(kind=kind, **kw)).kind == kind


# --------------------------------------------------------------------------- #
# identifiers
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("bad", ["", "   ", None, 7, [], "o" * 129])
def test_observation_id_must_be_a_nonempty_string_within_128_chars(bad):
    with pytest.raises(ValueError):
        R.validate(_payload(observation_id=bad))


@pytest.mark.parametrize("field", ["observation_id", "pair_id"])
def test_identifiers_at_exactly_the_limit_are_accepted(field):
    assert R.validate(_payload(**{field: "x" * 128}))


@pytest.mark.parametrize("kind", ["reversal", "data_withdrawal", "correction"])
def test_previous_observation_id_is_required_for_the_three_kinds_that_reference_one(kind):
    kw = {"values": None, "source_as_of": None} if kind == "data_withdrawal" else {}
    with pytest.raises(ValueError):
        R.validate(_payload(kind=kind, **kw))
    # An explicit null is the same absence, not an empty reference.
    with pytest.raises(ValueError):
        R.validate(_payload(kind=kind, previous_observation_id=None, **kw))
    assert R.validate(_payload(kind=kind, previous_observation_id="obs-earlier", **kw))


def test_previous_observation_id_is_optional_but_still_checked_for_observed_change():
    assert R.validate(_payload(kind="observed_change")).previous_observation_id is None
    assert R.validate(_payload(kind="observed_change",
                               previous_observation_id="obs-earlier")).previous_observation_id
    with pytest.raises(ValueError):
        R.validate(_payload(kind="observed_change", previous_observation_id="p" * 129))
    with pytest.raises(ValueError):
        R.validate(_payload(kind="observed_change", previous_observation_id="  "))


# --------------------------------------------------------------------------- #
# symbol grammar
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("symbol", ["XLV", "BRK.B", "XLV.US", "ES=F", "BF-B", "600519.SS",
                                   "A1", "A" * 20, "SPY=2"])
def test_real_market_symbols_are_accepted(symbol):
    """``BRK.B``/``600519.SS`` (dot), ``BF-B`` (dash) and ``ES=F`` (equals) are all real
    tickers, and the frozen grammar admits exactly those separators."""
    assert R.validate(_payload(num=symbol)).num == symbol


def test_the_grammar_still_requires_the_first_character_to_be_alphanumeric():
    """The frozen regex pins position 0 to ``[A-Z0-9]``, so a leading punctuation mark
    is out even though it appears in the tail class."""
    for symbol in ("^VIX", ".X", "-X", "=X"):
        with pytest.raises(ValueError):
            R.validate(_payload(num=symbol))


@pytest.mark.parametrize("symbol", [
    "", "xlv", "XLV US", "XLV US extra",      # lowercase / space
    "<b>XLV</b>", 'XLV" onmouseover=1',      # HTML
    "http://evil.test", "javascript:alert",  # URL / scheme
    "XLV/../etc", "A" * 21,                  # over the 20-char ceiling / traversal
    "XLV\nB", " XL V", None, 7, True,
])
def test_anything_outside_the_symbol_grammar_is_refused(symbol):
    with pytest.raises(ValueError):
        R.validate(_payload(num=symbol))
    with pytest.raises(ValueError):
        R.validate(_payload(den=symbol))


def test_num_and_den_must_be_distinct():
    with pytest.raises(ValueError):
        R.validate(_payload(num="XLV", den="XLV"))
    assert R.validate(_payload(num="XLV", den="XLK"))


# --------------------------------------------------------------------------- #
# date / datetime grammar
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("bad", ["2026-10-7", "20261021", "2026-W01-1", "2026-10-21T00:00",
                                "2026-13-01", "2026-02-30", "not-a-date", "", None, 7,
                                date(2026, 10, 21)])
def test_event_as_of_is_a_strict_real_iso_calendar_date(bad):
    """``date.fromisoformat`` alone is NOT enough -- 3.11+ also accepts '20261021' and
    '2026-W01-1'. The shape is pinned, then the date is proved real."""
    with pytest.raises(ValueError):
        R.validate(_payload(event_as_of=bad))


def test_a_weekend_is_not_a_valid_event_as_of():
    """2026-10-24 is a Saturday; the slate has no bar for it."""
    assert not cal.is_session(date(2026, 10, 24))
    with pytest.raises(ValueError):
        R.validate(_payload(event_as_of="2026-10-24",
                            observed_at="2026-10-24T22:00:00+00:00",
                            not_after="2026-10-24T23:00:00+00:00"))


@pytest.mark.parametrize("field", ["observed_at", "not_after"])
@pytest.mark.parametrize("bad", ["2026-10-21T22:00:00", "2026-10-21 22:00", "yesterday",
                                "", None, 7, "2026-10-21T22:00:00+25:00"])
def test_instants_must_be_timezone_aware_iso8601(field, bad):
    """A naive datetime has no instant; treating it as UTC would let a producer's
    missing timezone silently move the observation."""
    with pytest.raises(ValueError):
        R.validate(_payload(**{field: bad}))


def test_not_after_must_be_strictly_after_observed_at():
    with pytest.raises(ValueError):
        R.validate(_payload(not_after="2026-10-21T22:00:00+00:00"))
    with pytest.raises(ValueError):
        R.validate(_payload(not_after="2026-10-21T21:00:00+00:00"))
    assert R.validate(_payload(not_after="2026-10-21T22:00:00.001000+00:00"))


# --------------------------------------------------------------------------- #
# source_as_of
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("kind", ["observed_change", "reversal", "correction"])
def test_a_measured_kind_needs_source_as_of_equal_to_its_own_session(kind):
    kw = {"previous_observation_id": "obs-earlier"} if kind != "observed_change" else {}
    with pytest.raises(ValueError):
        R.validate(_payload(kind=kind, source_as_of=None, **kw))
    with pytest.raises(ValueError):
        R.validate(_payload(kind=kind, source_as_of="2026-10-20", **kw))
    assert R.validate(_payload(kind=kind, source_as_of="2026-10-21", **kw))


def test_a_withdrawal_may_carry_no_source_date_or_an_older_one_but_never_a_later_one():
    kw = {"kind": "data_withdrawal", "values": None, "previous_observation_id": "obs-earlier"}
    assert R.validate(_payload(source_as_of=None, **kw)).source_as_of is None
    assert R.validate(_payload(source_as_of="2026-10-20", **kw)).source_as_of == date(2026, 10, 20)
    assert R.validate(_payload(source_as_of="2026-10-21", **kw)).source_as_of == date(2026, 10, 21)
    with pytest.raises(ValueError):
        R.validate(_payload(source_as_of="2026-10-22", **kw))
    with pytest.raises(ValueError):
        R.validate(_payload(source_as_of="2026-99-01", **kw))


# --------------------------------------------------------------------------- #
# values: types, ceilings and the relative wealth identity
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("bad", [None, [], "x", 2, 7])
def test_measured_values_must_be_an_object(bad):
    with pytest.raises(ValueError):
        R.validate(_payload(values=bad))


@pytest.mark.parametrize("sessions", [True, False, 1, 3, 0, -2, 2.0, "2", None])
def test_sessions_must_be_the_integer_two_and_not_a_bool(sessions):
    """``True`` is an int in Python. A truthy sessions field must not read as one."""
    values = dict(_payload()["values"], sessions=sessions)
    with pytest.raises(ValueError):
        R.validate(_payload(values=values))


@pytest.mark.parametrize("field", ["numerator_return_pct", "denominator_return_pct",
                                  "ratio_return_pct"])
@pytest.mark.parametrize("bad", [True, False, None, "1.5", [1.5], {},
                                 float("nan"), float("inf"), float("-inf")])
def test_every_return_is_a_finite_real_number_and_never_a_bool_string_or_nan(field, bad):
    values = dict(_payload()["values"], **{field: bad})
    with pytest.raises(ValueError):
        R.validate(_payload(values=values))


def test_a_return_of_minus_one_hundred_or_worse_is_refused():
    """1 + d/100 == 0 would make the relative wealth undefined."""
    for field in ("numerator_return_pct", "denominator_return_pct"):
        values = dict(_payload()["values"], **{field: -100.0})
        with pytest.raises(ValueError):
            R.validate(_payload(values=values))
        values = dict(_payload()["values"], **{field: -140.0})
        with pytest.raises(ValueError):
            R.validate(_payload(values=values))
    # Just above the floor is still a legal measurement.
    n, d = -99.9, -99.5
    assert R.validate(_payload(values={"sessions": 2, "numerator_return_pct": n,
                                       "denominator_return_pct": d,
                                       "ratio_return_pct": _ratio(n, d)}))


@pytest.mark.parametrize("n,d", [(1.5, -0.5), (-2.25, 3.10), (0.0, 0.0), (12.0, -4.5),
                                 (-99.9, -99.5), (0.01, -99.0), (55.0, 0.25)])
def test_the_relative_wealth_identity_is_the_ratio_not_a_free_number(n, d):
    assert R.validate(_payload(values={"sessions": 2, "numerator_return_pct": n,
                                       "denominator_return_pct": d,
                                       "ratio_return_pct": _ratio(n, d)}))
    wrong = _ratio(n, d) + 0.001
    with pytest.raises(ValueError):
        R.validate(_payload(values={"sessions": 2, "numerator_return_pct": n,
                                    "denominator_return_pct": d,
                                    "ratio_return_pct": wrong}))


def test_the_identity_tolerance_is_exactly_one_micro_percent():
    n, d = 1.5, -0.5
    exact = _ratio(n, d)
    # A ratio derived in float32 by a different producer lands a hair inside tolerance;
    # anything a tenth of a basis point outside must be refused.
    just_inside = exact + 9e-7
    just_outside = exact + 2e-6
    assert abs(just_inside - exact) <= 1e-6
    values = {"sessions": 2, "numerator_return_pct": n, "denominator_return_pct": d,
              "ratio_return_pct": just_inside}
    assert R.validate(_payload(values=values))
    with pytest.raises(ValueError):
        R.validate(_payload(values=dict(values, ratio_return_pct=just_outside)))


def test_a_withdrawal_must_carry_null_values():
    """The load-bearing withdrawal rule: re-rendering a stale positive pair after the
    evidence was withdrawn asserts a measurement that no longer has support."""
    kw = {"kind": "data_withdrawal", "source_as_of": None,
          "previous_observation_id": "obs-earlier"}
    assert R.validate(_payload(values=None, **kw)).values is None
    for stale in (_payload()["values"], {}, [], 0, False, ""):
        with pytest.raises(ValueError):
            R.validate(_payload(values=stale, **kw))


# --------------------------------------------------------------------------- #
# forward compatibility: unknown fields are tolerated, never rendered
# --------------------------------------------------------------------------- #
def test_unknown_fields_are_tolerated_so_a_producer_can_extend_the_stream():
    obs = R.validate(_payload(future_field="whatever", evidence_url="https://evil.test"))
    assert obs.num == "XLV"
    assert not hasattr(obs, "future_field")


# --------------------------------------------------------------------------- #
# the temporal gate
# --------------------------------------------------------------------------- #
def test_a_current_observation_within_not_after_sends():
    v = R.evaluate(_payload(), now_utc=NOW)
    assert v.status == R.OK and v.action == "send" and v.reason == "ok"


def test_a_malformed_payload_is_invalid_before_the_clock_is_ever_read():
    """Structural failure outranks temporality: an unevaluable verdict must not depend
    on what now_utc happened to be, so this passes even with now_utc=None."""
    v = R.evaluate(_payload(values="nope"), now_utc=None)
    assert v.status == R.INVALID
    assert v.action == "unevaluable"
    assert v.reason == R.REASON_INVALID


@pytest.mark.parametrize("now", [None, "2026-10-21T22:30:00+00:00", 7,
                                 datetime(2026, 10, 21, 22, 30)])
def test_an_unknown_or_naive_clock_is_unevaluable_and_never_a_send(now):
    v = R.evaluate(_payload(), now_utc=now)
    assert v.status == R.UNEVALUABLE
    assert v.action == "unevaluable"
    assert v.reason == R.REASON_INVALID


def test_a_future_observation_is_malformed_not_a_send():
    future_obs = datetime(2026, 10, 21, 23, 0, tzinfo=UTC)
    v = R.evaluate(_payload(observed_at="2026-10-21T23:00:00+00:00",
                            not_after="2026-10-22T01:00:00+00:00"),
                   now_utc=NOW)
    assert v.status == R.INVALID and v.action == "unevaluable"


def test_event_as_of_must_be_the_session_observed_at_settles():
    """A payload claiming 10-20 while observing on 10-21 is reporting a session it did
    not measure, whatever the clock says."""
    v = R.evaluate(_payload(event_as_of="2026-10-20", source_as_of="2026-10-20"),
                   now_utc=NOW)
    assert v.status == R.INVALID and v.action == "unevaluable"


def test_the_observation_is_one_instant_before_the_session_rolls():
    """At 16:00 ET on the observed day, els is still the prior session, so an
    observation stamped 10-20 delivered then is genuinely not stale yet."""
    early = datetime(2026, 10, 21, 20, 0, tzinfo=UTC)   # 16:00 ET, pre-settle
    assert cal.expected_last_session(early) == date(2026, 10, 20)
    v = R.evaluate(_payload(event_as_of="2026-10-20", source_as_of="2026-10-20",
                            observed_at="2026-10-20T22:00:00+00:00",
                            not_after="2026-10-21T23:00:00+00:00"),
                   now_utc=early)
    assert v.status == R.OK


def test_exact_expiry_is_expired_and_one_microsecond_earlier_is_not():
    """now == not_after counts as expired; the boundary is >=, and it is tested from
    both sides so a future '>' typo cannot pass."""
    at = datetime(2026, 10, 21, 23, 0, tzinfo=UTC)
    assert R.evaluate(_payload(), now_utc=at).status == R.EXPIRED
    assert R.evaluate(_payload(), now_utc=at - _microsecond()).status == R.OK


def _microsecond():
    from datetime import timedelta
    return timedelta(microseconds=1)


def test_expiry_suppresses_rather_than_deferring_or_retrying():
    at = datetime(2026, 10, 21, 23, 0, tzinfo=UTC)
    v = R.evaluate(_payload(), now_utc=at)
    assert v.action == "suppress"
    assert v.reason == R.REASON_EXPIRED
    # Re-deriving it a tick later yields the same terminal answer -- that is what makes
    # this a suppression and not a retry.
    assert R.evaluate(_payload(), now_utc=at + _microsecond()).status == R.EXPIRED


def test_a_stale_session_is_suppressed_even_when_not_after_has_not_passed():
    """event_as_of must STILL be the last settled session at send time."""
    later = datetime(2026, 10, 24, 12, 0, tzinfo=UTC)   # Saturday; last session is 10-23
    v = R.evaluate(_payload(), now_utc=later)
    assert v.status == R.EXPIRED and v.action == "suppress"
    assert v.reason == R.REASON_EXPIRED


# --------------------------------------------------------------------------- #
# the published calendar drives the gate: weekend, half day, holiday
# --------------------------------------------------------------------------- #
def test_a_friday_observation_is_still_current_over_the_weekend():
    saturday = datetime(2026, 10, 24, 12, 0, tzinfo=UTC)
    p = _payload(event_as_of="2026-10-23", source_as_of="2026-10-23",
                 observed_at="2026-10-23T22:00:00+00:00",
                 not_after="2026-10-27T12:00:00+00:00")
    assert R.evaluate(p, now_utc=saturday).status == R.OK
    sunday = datetime(2026, 10, 25, 23, 59, tzinfo=UTC)
    assert R.evaluate(p, now_utc=sunday).status == R.OK
    # ...and on the next Monday, once 10-23 is no longer the last settled session, it
    # is terminal. The gate never invents a weekend calendar of its own -- the
    # weekend is answered by lib.us_cash_calendar, which is the whole point.
    monday = datetime(2026, 10, 26, 22, 0, tzinfo=UTC)
    assert R.evaluate(p, now_utc=monday).status == R.EXPIRED


def test_a_thursday_observation_is_expired_by_friday_evening():
    friday_evening = datetime(2026, 10, 23, 22, 30, tzinfo=UTC)
    p = _payload(not_after="2026-10-24T23:00:00+00:00")
    assert cal.expected_last_session(friday_evening) == date(2026, 10, 23)
    assert R.evaluate(p, now_utc=friday_evening).status == R.EXPIRED


def test_a_published_us_half_day_hands_over_the_current_session_at_14_et_not_17_et():
    """2026-11-27 closes at 13:00 ET, so its bar is due at 14:00 ET -- three hours
    before an ordinary day's 17:00 ET. The boundary is observable: at 13:59 ET the
    PRIOR session (11-25, Thanksgiving 11-26 being a closure) is still the current one,
    and at 14:00 ET the half-day session takes that slot and the prior row goes stale.

    This is what pins the gate to the EXISTING calendar: an implementation that
    hardcoded 17:00 ET would keep the prior row current until 17:00 and suppress the
    half-day observation as not-yet-settled, i.e. wrong in both directions at once.
    """
    prior = _payload(event_as_of="2026-11-25", source_as_of="2026-11-25",
                     observed_at="2026-11-25T22:00:00+00:00",
                     not_after="2026-11-30T23:00:00+00:00")
    before_settle = datetime(2026, 11, 27, 18, 59, tzinfo=UTC)   # 13:59 ET
    at_settle = datetime(2026, 11, 27, 19, 0, tzinfo=UTC)         # 14:00 ET exactly
    assert cal.expected_last_session(before_settle) == date(2026, 11, 25)
    assert cal.expected_last_session(at_settle) == date(2026, 11, 27)
    assert R.evaluate(prior, now_utc=before_settle).status == R.OK
    assert R.evaluate(prior, now_utc=at_settle).status == R.EXPIRED


def test_a_half_day_observation_is_sendable_at_its_own_settle_hour():
    """The half-day session's own observation is created at 14:00 ET and must be
    deliverable immediately -- not held back until a 17:00 settle."""
    p = _payload(event_as_of="2026-11-27", source_as_of="2026-11-27",
                 observed_at="2026-11-27T19:00:00+00:00",
                 not_after="2026-11-28T23:00:00+00:00")
    for at in (datetime(2026, 11, 27, 19, 0, tzinfo=UTC),
               datetime(2026, 11, 27, 19, 30, tzinfo=UTC),
               datetime(2026, 11, 27, 22, 30, tzinfo=UTC)):
        assert R.evaluate(p, now_utc=at).status == R.OK, at
    # Past the weekend the half-day session is no longer the last settled one.
    assert R.evaluate(p, now_utc=datetime(2026, 11, 30, 22, 30, tzinfo=UTC)).status == R.EXPIRED


def test_a_half_day_observation_cannot_be_backdated_before_its_own_settle():
    """The pre-settle half-day row is not merely suppressed -- it is refused as
    malformed, because observed_at sits in the future of the injected now."""
    p = _payload(event_as_of="2026-11-27", source_as_of="2026-11-27",
                 observed_at="2026-11-27T19:00:00+00:00",
                 not_after="2026-11-28T23:00:00+00:00")
    v = R.evaluate(p, now_utc=datetime(2026, 11, 27, 18, 59, tzinfo=UTC))
    assert v.status == R.INVALID and v.action == "unevaluable"


def test_a_full_closure_rolls_back_to_the_prior_session():
    """Thanksgiving 2026-11-26: a bar due that evening is the 11-25 session."""
    thanksgiving = datetime(2026, 11, 26, 22, 0, tzinfo=UTC)
    assert cal.expected_last_session(thanksgiving) == date(2026, 11, 25)
    p = _payload(event_as_of="2026-11-25", source_as_of="2026-11-25",
                 observed_at="2026-11-25T22:00:00+00:00",
                 not_after="2026-11-27T23:00:00+00:00")
    assert R.evaluate(p, now_utc=thanksgiving).status == R.OK


def test_an_observation_dated_a_full_closure_is_invalid():
    p = _payload(event_as_of="2026-11-26", source_as_of="2026-11-26",
                 observed_at="2026-11-26T22:00:00+00:00",
                 not_after="2026-11-27T23:00:00+00:00")
    v = R.evaluate(p, now_utc=datetime(2026, 11, 26, 22, 30, tzinfo=UTC))
    assert v.status == R.INVALID and v.action == "unevaluable"


# --------------------------------------------------------------------------- #
# unknown calendar fails closed
# --------------------------------------------------------------------------- #
def test_a_calendar_that_cannot_answer_is_unevaluable_never_a_send(monkeypatch):
    def _boom(_now):
        raise ValueError("no US cash session found in the prior 30 days")
    monkeypatch.setattr(cal, "expected_last_session", _boom)
    v = R.evaluate(_payload(), now_utc=NOW)
    assert v.status == R.UNEVALUABLE
    assert v.action == "unevaluable"
    assert v.reason == R.REASON_INVALID


def test_a_calendar_module_that_cannot_import_is_unevaluable_never_a_send(monkeypatch):
    """The calendar is imported lazily so this failure is caught by the same handler as
    a lookup failure. A broken calendar must fail closed, never raise into the drain."""
    import builtins
    real_import = builtins.__import__

    def _no_calendar(name, *args, **kwargs):
        if name == "lib.us_cash_calendar":
            raise ImportError("calendar module unavailable")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _no_calendar)
    v = R.evaluate(_payload(), now_utc=NOW)
    assert v.status == R.UNEVALUABLE and v.action == "unevaluable"


def test_validate_alone_never_touches_the_calendar(monkeypatch):
    """The structural half stays usable (and testable) with no calendar at all, which
    is what lets app/mailer.py import this module and compose without a trading
    calendar in its import graph."""
    def _boom(*_a, **_k):
        raise AssertionError("validate must not consult the calendar")
    monkeypatch.setattr(cal, "expected_last_session", _boom)
    assert R.validate(_payload()).num == "XLV"


# --------------------------------------------------------------------------- #
# purity
# --------------------------------------------------------------------------- #
def test_neither_gate_reads_a_clock_when_none_is_injected():
    """evaluate() with now_utc omitted must not silently fall back to ``now()``."""
    import inspect
    src = inspect.getsource(R)
    for banned in ("datetime.now(", "date.today(", "time.time(", "utcnow("):
        assert banned not in src, f"rotation contract calls the wall clock: {banned}"


def test_validate_does_not_mutate_the_payload():
    p = _payload()
    before = {k: (dict(v) if isinstance(v, dict) else v) for k, v in p.items()}
    R.validate(p)
    assert p == before


def test_evaluate_is_deterministic_for_a_fixed_instant():
    p = _payload()
    first = R.evaluate(p, now_utc=NOW)
    for _ in range(5):
        assert R.evaluate(p, now_utc=NOW) == first


def test_the_two_reason_strings_are_the_ones_the_outbox_receives():
    assert R.REASON_INVALID == "rotation_observation_invalid"
    assert R.REASON_EXPIRED == "rotation_observation_expired"
    # Both must fit the existing terminal vocabulary: no new alert_outbox status.
    assert R.REASON_EXPIRED != "" and " " not in R.REASON_EXPIRED


def test_the_identity_check_survives_a_nan_ratio_without_raising_a_valueerror_mask():
    """A NaN would make ``abs(expected - nan) > tol`` false and let a garbage ratio
    through, so finiteness is checked BEFORE the identity -- both assertions pin it."""
    values = {"sessions": 2, "numerator_return_pct": 1.0, "denominator_return_pct": 0.5,
              "ratio_return_pct": float("nan")}
    with pytest.raises(ValueError) as ei:
        R.validate(_payload(values=values))
    assert "not finite" in str(ei.value)
    assert math.isnan(float("nan"))  # the sanity of the fixture itself
