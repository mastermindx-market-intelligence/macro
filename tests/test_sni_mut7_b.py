"""M7B mutation-sweep killing tests (SNI DRAFT guards, 2026-10-14 sweep).

One targeted test per non-equivalent surviving mutant from the M7B sweep of
research/single_name_intelligence/common/sni_then_known_guard.py and
research/single_name_intelligence/common/sni_session_state_guard.py
(review: research/single_name_intelligence/reviews/
MUTATION_SWEEP_M7B_2026-10-14.md). Each docstring names its mutant
(file:line, original -> mutated). Fixtures are synthetic; fact ids and
calendar refs are caller-supplied opaque strings, never minted here.
HISTORICAL-DESCRIPTIVE only: rank_authority, gate_authority, size_authority,
signal_authority, escalation_authority and trade_authority stay literal
False, and nothing here registers, validates, or feeds a ranker, gate,
sizer, signal, escalation, or trade path.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research" / "single_name_intelligence" / "common"))

from sni_session_state_guard import session_state  # noqa: E402
from sni_then_known_guard import clock_triplet, then_known_view  # noqa: E402

_UTC = timezone.utc


def _fact(**overrides):
    fact = {
        "fact_id": "SYN-FACT-M7B-1",
        "economic_time": "2026-01-10T00:00:00Z",
        "published_at": "2026-01-15T09:00:01Z",
        "owner_known_at": "2026-01-15T09:05:02Z",
        "retrieved_at": "2026-01-15T10:00:03Z",
        "supersedes": "",
        "vintaged": False,
    }
    fact.update(overrides)
    return fact


def _hk_day(**overrides):
    day = {
        "calendar_id": "SYN-CAL-M7B-1",
        "owner_ref": "SYN-CAL-OWNER-M7B-1",
        "timezone": "Asia/Hong_Kong",
        "trading_date": "2026-10-07",
        "day_kind": "full",
        "sessions": (("09:30", "12:00"), ("13:00", "16:00")),
        "halts": (),
    }
    day.update(overrides)
    return day


def test_m7b_then_known__aware_value_004():
    """Mutant then_known-004: sni_then_known_guard.py:159
    `text[:-1] + "+00:00"` -> `text[:-1] - "+00:00"` (arithmetic swap).

    A trailing-Z instant must parse to an aware datetime (the Z suffix is
    rewritten to +00:00 with string concatenation); the mutant subtracts
    two strings and the whole view compile crashes instead of including a
    then-known fact.
    """
    verdict = then_known_view([_fact()], cutoff="2026-01-15T12:00:00Z")
    assert verdict.allowed is True
    assert verdict.included == ("SYN-FACT-M7B-1",)
    assert verdict.excluded == ()


def test_m7b_then_known__aware_value_014():
    """Mutant then_known-014: sni_then_known_guard.py:159
    `text[:-1]` -> `text[:-2]` (constant perturbation 1 -> 2).

    Stripping two characters before the Z eats the seconds digit:
    "2026-01-15T09:00:01Z" would parse as 09:00:00 (or refuse). The
    triplet must carry the exact original seconds.
    """
    parsed = clock_triplet(
        {
            "published_at": "2026-01-15T09:00:01Z",
            "owner_known_at": "2026-01-15T09:05:02Z",
            "retrieved_at": "2026-01-15T10:00:03Z",
        }
    )
    assert parsed == (
        datetime(2026, 1, 15, 9, 0, 1, tzinfo=_UTC),
        datetime(2026, 1, 15, 9, 5, 2, tzinfo=_UTC),
        datetime(2026, 1, 15, 10, 0, 3, tzinfo=_UTC),
    )


def test_m7b_session_state__wall_minute_012():
    """Mutant session_state-012: sni_session_state_guard.py:177
    `len(head) not in (1, 2)` -> `len(head) not in (2, 2)` (int 1 -> 2).

    A one-digit hour is a legal wall-clock bound ("9:30"); the mutant
    refuses every single-digit-hour session as SESSION_TIME_INVALID.
    """
    day = _hk_day(sessions=(("9:30", "12:00"),))
    verdict = session_state(day, at="2026-10-07T09:45:00+08:00")
    assert verdict.allowed is True
    assert verdict.state == "open"
    assert verdict.reasons == ()


def test_m7b_session_state__calendar_date_028():
    """Mutant session_state-028: sni_session_state_guard.py:155
    `len(year) != 4 or len(month) != 2 or len(day) != 2`
    -> same with `and` (BoolOp flip). Classified EQUIVALENT in the sweep:
    the len(text) != 10 gate at line 149 refuses every short form before
    line 155 runs, and any 10-char input with non-(4,2,2) part lengths
    also fails date() construction under the mutant (out-of-range month,
    day, or year raises -> None both ways). This test is kept as boundary
    coverage pinning the strict-form refusal; it kills no mutant.
    """
    day = _hk_day(trading_date="2026-1-15")
    verdict = session_state(day, at="2026-01-15T10:00:00+08:00")
    assert verdict.allowed is False
    assert "DATE_INVALID" in verdict.reasons
    assert verdict.state is None


def test_m7b_session_state__load_zone_029():
    """Mutant session_state-029: sni_session_state_guard.py:224
    `not isinstance(name, str) or name == "" or name not in _iana_names()`
    -> same with `and` (BoolOp flip).

    A non-string timezone must be refused as TIMEZONE_INVALID, never
    raise: the isinstance short-circuit guards the set membership test,
    and an unhashable value (a list) would crash the mutant.
    """
    day = _hk_day(timezone=["Asia/Hong_Kong"])
    verdict = session_state(day, at="2026-10-07T10:00:00+08:00")
    assert verdict.allowed is False
    assert "TIMEZONE_INVALID" in verdict.reasons
    assert verdict.state is None
