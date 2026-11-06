"""X8BREP repair tests (REQUEST_REPAIR round 1, X8B DRAFT guard family text rule).

These are the fail-first tests for the X8BREP repair round. Each closed
defect from research/single_name_intelligence/reviews/
X8B_GUARD_REDTEAM_2026-10-14.md has exactly one test function, named
``test_r1_<nn>_<slug>`` per the lane spec. Each test reproduces the
EVIDENCE block from the review and asserts the refusal the FAMILY TEXT
RULE + LAZULE RULING demands.

The FAMILY TEXT RULE says a caller-supplied opaque id/ref/text field
counts as present ONLY when ``_text_present`` returns True: the value
must be a ``str``, non-empty after ``str.strip``, and equal to its
stripped form. Anything else -- None, empty string, whitespace,
leading/trailing whitespace or newline, int, float, bool, bytes, list,
dict, set, any other object -- is ABSENT and maps to the same
refusal reason the module already emits for a blank value of that
field.

X8B-05 (session-state owner_ref follows FAMILY TEXT RULE) is OPEN and
NOT tested here: ``test_a12_adversarial_owner_ref_opaque`` in
``tests/test_sni_session_state_guard.py`` (lines 460-484) pins the
permissive behaviour (trailing-space, case-variant, Cyrillic
lookalike owner_ref values are accepted). Per the lane REPAIR LAW,
that defect is left open and recorded in GAPS.

The tests import the modules the same way the existing SNI guard
tests do: the path is appended to ``sys.path`` at module load and the
module is imported by its bare stem. They do NOT pop, delete, or
replace any ``sys.modules`` key.

HISTORICAL-DESCRIPTIVE only: rank_authority, gate_authority,
size_authority, signal_authority, escalation_authority and
trade_authority stay literal False. Fixtures are synthetic; fact ids
and calendar refs are caller-supplied opaque strings, never minted
here.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research" / "single_name_intelligence" / "common"))

from sni_session_state_guard import REASONS as SS_REASONS  # noqa: E402
from sni_session_state_guard import session_state  # noqa: E402
from sni_then_known_guard import REASONS as TK_REASONS  # noqa: E402
from sni_then_known_guard import then_known_view  # noqa: E402

CUTOFF = "2026-06-01T00:00:00+00:00"

_HK_TZ = "Asia/Hong_Kong"
_AT_MORNING = "2026-10-07T10:00:00+08:00"


def _fact(**overrides):
    """Build a well-formed fact; default to a string fact_id so we can
    isolate one field-flip per probe."""
    body = {
        "fact_id": "SYN-FACT-1",
        "economic_time": "2026-01-15T00:00:00+00:00",
        "owner_known_at": "2026-03-02T10:05:00+00:00",
        "published_at": "2026-03-01T08:00:00+00:00",
        "retrieved_at": "2026-03-02T11:00:00+00:00",
        "supersedes": None,
        "vintaged": False,
    }
    body.update(overrides)
    return body


def _hk_day(**overrides):
    """Build a well-formed HK calendar; default calendar_id and
    owner_ref to non-blank strings so we can isolate one field-flip
    per probe."""
    day = {
        "calendar_id": "SYN-CAL-HK-1",
        "owner_ref": "SYN-CAL-OWNER-HK-1",
        "timezone": _HK_TZ,
        "trading_date": "2026-10-07",
        "day_kind": "full",
        "sessions": (("09:30", "12:00"), ("13:00", "16:00")),
        "halts": (),
    }
    day.update(overrides)
    return day


# ---------------------------------------------------------------------------
# X8B-01: non-text fact_id -> FACT_ID_MISSING (never collides).
# Reproduces the EVIDENCE: fact_id=1, True, 1.0, False, 0 all emit
# FACT_ID_MISSING (never allowed) and never collide in DUPLICATE_FACT_ID.
# ---------------------------------------------------------------------------


def test_r1_01_fact_id_non_text_refused():
    for value in (1, True, 1.0, False, 0, 0.0):
        view = then_known_view([_fact(fact_id=value)], cutoff=CUTOFF)
        assert view.allowed is False, value
        assert view.reasons == ("FACT_ID_MISSING",), (value, view.reasons)
        assert view.included == ()
        assert view.excluded == ()


def test_r1_01_fact_id_int_and_bool_do_not_collide():
    """A second item with a different non-text spelling must NOT trip
    DUPLICATE_FACT_ID -- both items are ABSENT, not equal."""
    items = [_fact(fact_id=1), _fact(fact_id=True)]
    view = then_known_view(items, cutoff=CUTOFF)
    assert view.allowed is False
    assert "DUPLICATE_FACT_ID" not in view.reasons, view.reasons
    assert "FACT_ID_MISSING" in view.reasons, view.reasons
    assert view.included == ()
    assert view.excluded == ()


def test_r1_01_fact_id_int_and_float_do_not_collide():
    items = [_fact(fact_id=1), _fact(fact_id=1.0)]
    view = then_known_view(items, cutoff=CUTOFF)
    assert view.allowed is False
    assert "DUPLICATE_FACT_ID" not in view.reasons, view.reasons
    assert "FACT_ID_MISSING" in view.reasons, view.reasons
    assert view.included == ()
    assert view.excluded == ()


def test_r1_01_fact_id_zero_and_false_do_not_collide():
    items = [_fact(fact_id=0), _fact(fact_id=False)]
    view = then_known_view(items, cutoff=CUTOFF)
    assert view.allowed is False
    assert "DUPLICATE_FACT_ID" not in view.reasons, view.reasons
    assert "FACT_ID_MISSING" in view.reasons, view.reasons
    assert view.included == ()
    assert view.excluded == ()


# ---------------------------------------------------------------------------
# X8B-02: padded fact_id -> FACT_ID_MISSING, never included.
# Reproduces the EVIDENCE: ' ', ' SYN-FACT-1', 'SYN-FACT-1\t',
# 'SYN-FACT-1\xa0', 'SYN-FACT-1\n' all refuse and are not in included.
# ---------------------------------------------------------------------------


def test_r1_02_fact_id_whitespace_only_refused():
    view = then_known_view([_fact(fact_id=" ")], cutoff=CUTOFF)
    assert view.allowed is False
    assert view.reasons == ("FACT_ID_MISSING",), view.reasons
    assert " " not in view.included


# NOTE: padded fact_id ("X ") is PINNED by test_a07g_duplicate_exact_only_no_folding
# in tests/test_sni_then_known_guard.py (lines 528-534): padded ids are
# asserted as a distinct non-blank opaque string and are PRESERVED.
# Per REPAIR LAW, that defect portion is left open and no test for it is
# added here. The whitespace-only case below is the unpinned part of X8B-02
# and is closed.


# ---------------------------------------------------------------------------
# X8B-03: unhashable fact_id -> FACT_ID_MISSING, never raises. And the
# same applies to a non-text supersedes -> SUPERSEDES_UNKNOWN, never
# raises. Reproduces the EVIDENCE: fact_id=[1,2] RAISED TypeError on base.
# ---------------------------------------------------------------------------


def test_r1_03_fact_id_list_does_not_raise_and_is_missing():
    try:
        view = then_known_view([_fact(fact_id=[1, 2])], cutoff=CUTOFF)
    except TypeError as exc:  # pragma: no cover -- bug regression
        pytest.fail("fact_id=[1,2] raised TypeError: %s" % exc)
    assert view.allowed is False
    assert view.reasons == ("FACT_ID_MISSING",), view.reasons
    assert view.included == ()


def test_r1_03_fact_id_dict_does_not_raise_and_is_missing():
    try:
        view = then_known_view([_fact(fact_id={"k": 1})], cutoff=CUTOFF)
    except TypeError as exc:  # pragma: no cover -- bug regression
        pytest.fail("fact_id=dict raised TypeError: %s" % exc)
    assert view.allowed is False
    assert view.reasons == ("FACT_ID_MISSING",), view.reasons


def test_r1_03_fact_id_set_does_not_raise_and_is_missing():
    try:
        view = then_known_view([_fact(fact_id={1, 2})], cutoff=CUTOFF)
    except TypeError as exc:  # pragma: no cover -- bug regression
        pytest.fail("fact_id=set raised TypeError: %s" % exc)
    assert view.allowed is False
    assert view.reasons == ("FACT_ID_MISSING",), view.reasons


def test_r1_03_supersedes_list_does_not_raise_and_is_unknown():
    """A list-valued supersedes (non-None, non-text) must emit
    SUPERSEDES_UNKNOWN, never raise, never silently treat as a string."""
    try:
        view = then_known_view(
            [_fact(fact_id="SYN-FACT-1", supersedes=[1, 2])],
            cutoff=CUTOFF,
        )
    except TypeError as exc:  # pragma: no cover -- bug regression
        pytest.fail("supersedes=[1,2] raised TypeError: %s" % exc)
    assert view.allowed is False
    assert "SUPERSEDES_UNKNOWN" in view.reasons, view.reasons


def test_r1_03_supersedes_dict_does_not_raise_and_is_unknown():
    try:
        view = then_known_view(
            [_fact(fact_id="SYN-FACT-1", supersedes={"k": 1})],
            cutoff=CUTOFF,
        )
    except TypeError as exc:  # pragma: no cover -- bug regression
        pytest.fail("supersedes=dict raised TypeError: %s" % exc)
    assert view.allowed is False
    assert "SUPERSEDES_UNKNOWN" in view.reasons, view.reasons


# ---------------------------------------------------------------------------
# X8B-06: calendar_id not text-present -> CALENDAR_MISSING (existing
# reason). Reproduces the EVIDENCE: calendar_id=None, '', int, bool,
# list all allowed=True on base; under FAMILY TEXT RULE they refuse with
# CALENDAR_MISSING (the existing reason, no new code).
# ---------------------------------------------------------------------------


def test_r1_06_calendar_id_none_refused_with_calendar_missing():
    day = _hk_day(calendar_id=None)
    verdict = session_state(day, at=_AT_MORNING)
    assert verdict.allowed is False, verdict
    assert "CALENDAR_MISSING" in verdict.reasons, verdict.reasons
    assert verdict.state is None


def test_r1_06_calendar_id_empty_refused_with_calendar_missing():
    day = _hk_day(calendar_id="")
    verdict = session_state(day, at=_AT_MORNING)
    assert verdict.allowed is False, verdict
    assert "CALENDAR_MISSING" in verdict.reasons, verdict.reasons
    assert verdict.state is None


def test_r1_06_calendar_id_whitespace_refused_with_calendar_missing():
    day = _hk_day(calendar_id=" ")
    verdict = session_state(day, at=_AT_MORNING)
    assert verdict.allowed is False, verdict
    assert "CALENDAR_MISSING" in verdict.reasons, verdict.reasons


def test_r1_06_calendar_id_int_refused_with_calendar_missing():
    day = _hk_day(calendar_id=1)
    verdict = session_state(day, at=_AT_MORNING)
    assert verdict.allowed is False, verdict
    assert "CALENDAR_MISSING" in verdict.reasons, verdict.reasons


def test_r1_06_calendar_id_bool_refused_with_calendar_missing():
    day = _hk_day(calendar_id=True)
    verdict = session_state(day, at=_AT_MORNING)
    assert verdict.allowed is False, verdict
    assert "CALENDAR_MISSING" in verdict.reasons, verdict.reasons


def test_r1_06_calendar_id_list_refused_with_calendar_missing():
    day = _hk_day(calendar_id=[1, 2])
    verdict = session_state(day, at=_AT_MORNING)
    assert verdict.allowed is False, verdict
    assert "CALENDAR_MISSING" in verdict.reasons, verdict.reasons


# ---------------------------------------------------------------------------
# Reasons-tuples sanity: confirm neither module's REASONS tuple changed.
# ---------------------------------------------------------------------------


def test_r1_reasons_tuples_unchanged():
    assert TK_REASONS == (
        "FACT_ID_MISSING",
        "DUPLICATE_FACT_ID",
        "ECONOMIC_TIME_INVALID",
        "OWNER_KNOWN_INVALID",
        "PUBLISHED_INVALID",
        "RETRIEVED_INVALID",
        "OWNER_KNOWN_BEFORE_PUBLISHED",
        "RETRIEVED_BEFORE_PUBLISHED",
        "SUPERSEDES_UNKNOWN",
        "SUPERSEDES_CYCLE",
    )
    assert SS_REASONS == (
        "CALENDAR_MISSING",
        "OWNER_REF_MISSING",
        "TIMEZONE_INVALID",
        "DATE_INVALID",
        "DAY_KIND_UNKNOWN",
        "SESSION_TIME_INVALID",
        "SESSIONS_INCONSISTENT",
        "HALT_INVALID",
        "AT_INVALID",
        "AT_OUTSIDE_TRADING_DATE",
    )