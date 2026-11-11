"""M8A mutation-sweep killing tests for two SNI DRAFT guard modules.

SNI-local DRAFT contract tests. They consume owner-supplied opaque identity
strings (Stock Identity / Data OS) and never mint issuer, listing, or
security ids. HISTORICAL-DESCRIPTIVE only: rank_authority, gate_authority,
size_authority, signal_authority, escalation_authority and trade_authority
stay literal False. Fixtures are synthetic.

Each test below kills one mutant from the M8A sweep
(research/single_name_intelligence/reviews/MUTATION_SWEEP_M8A_2026-10-14.md)
that the pre-existing suite
(tests/test_sni_class_duplicate_guard.py,
tests/test_sni_three_clock_guard.py,
tests/test_sni_famvcc_repair.py)
did NOT kill. The docstring of each test names the mutant: file:line and
original -> mutated. Every test passes on unmutated code; against its
mutant the cited assertion fails.

This module does not register, validate, or feed a ranker, gate, sizer,
signal, escalation, or trade path. No network, no git access.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research" / "single_name_intelligence" / "common"))

import sni_class_duplicate_guard as cdg  # noqa: E402
import sni_three_clock_guard as tcg  # noqa: E402


# ============================================================ class_duplicate


def test_m8a_class_duplicate__blank_constbool_l139():
    """Kill mutant M8A class_duplicate #1
    (sni_class_duplicate_guard.py:139 col 15-19, ``return True``
    -> ``return False``).

    _blank is the absence test for opaque text. ``_blank("")`` must be
    literal True; the mutation makes it False, which means an empty
    string is treated as a valid pair security id and a structurally
    bad pair record is no longer refused on the empty-string branch.
    """
    assert cdg._blank("") is True


def test_m8a_class_duplicate__blank_return_none_l137():
    """Kill mutant M8A class_duplicate #2
    (sni_class_duplicate_guard.py:137 col 8-19, ``return True``
    -> ``return None``).

    _blank(None) must be literal True. The mutation returns None, which
    is falsy at every call site and lets a None sid slip past the
    _pair_shape_ok check.
    """
    assert cdg._blank(None) is True


def test_m8a_class_duplicate__blank_return_none_l139():
    """Kill mutant M8A class_duplicate #3
    (sni_class_duplicate_guard.py:139 col 8-19, ``return True``
    -> ``return None``).

    _blank("") must be literal True. The mutation returns None, which
    is falsy and lets an empty-string sid slip past _pair_shape_ok.
    """
    assert cdg._blank("") is True


def test_m8a_class_duplicate__blank_return_none_l140():
    """Kill mutant M8A class_duplicate #4
    (sni_class_duplicate_guard.py:140 col 4-16, ``return False``
    -> ``return None``).

    _blank(123) (a non-None, non-empty, non-string value) must be
    literal False. The mutation returns None, which is also falsy but
    is not the literal False the contract returns for a present value.
    """
    assert cdg._blank(123) is False


def test_m8a_class_duplicate__pair_shape_ok_boolop_l155():
    """Kill mutant M8A class_duplicate #5
    (sni_class_duplicate_guard.py:155 col 11-50,
    ``not isinstance(sid, str) or _blank(sid)``
    -> ``not isinstance(sid, str) and _blank(sid)``).

    A pair whose security_ids list carries a non-string entry (e.g. an
    int) must be refused. The mutated condition requires BOTH
    "not a string" AND "_blank" to be true, so a non-string that is
    also non-blank is accepted and the pair is silently treated as
    structurally well-formed.
    """
    # First sid is an int (not a string); second is a valid string.
    # The original condition refuses this on the first sid; the
    # mutated condition accepts it (the int is not a string but
    # _blank(5) is False, so the AND is False, so the body does not
    # run, so the sid is treated as good).
    assert cdg._pair_shape_ok([5, "valid-id"]) is False


# ============================================================ three_clock


def test_m8a_three_clock__as_date_boolop_l202():
    """Kill mutant M8A three_clock #1
    (sni_three_clock_guard.py:202 col 7-51,
    ``not isinstance(text, str) or len(text) != 10``
    -> ``not isinstance(text, str) and len(text) != 10``).

    _as_date must refuse any non-string input regardless of its length.
    The mutated condition only refuses when BOTH clauses are true, so a
    non-string of length 10 (a 10-byte bytestring here) falls through
    to ``date.fromisoformat`` and raises TypeError, which is not the
    contract's None-on-bad-input behaviour.
    """
    # 10-byte non-string: original returns None; mutated tries
    # date.fromisoformat(bytes_obj) and raises TypeError.
    assert tcg._as_date(b"\x00" * 10) is None


def test_m8a_three_clock__blank_return_none_l172():
    """Kill mutant M8A three_clock #2
    (sni_three_clock_guard.py:172 col 8-19, ``return True``
    -> ``return None``).

    _blank("") must be literal True. The mutation returns None, which
    is falsy and lets an empty-string record value pass the
    "field is present" check in _present, so a blank record value
    is silently accepted for ECONOMIC / OWNER_KNOWN / PUBLICATION.
    """
    assert tcg._blank("") is True


def test_m8a_three_clock__coerce_field_value_return_none_l254():
    """Kill mutant M8A three_clock #3
    (sni_three_clock_guard.py:254 col 4-26,
    ``return (parsed_dt, True)`` -> ``return None``).

    The success branch of _coerce_field_value for the non-require_aware
    path that reaches the final ``return parsed_dt, True`` must return a
    (datetime, True) tuple, not None. The mutation returns None, which
    the caller tries to unpack and fails on. The string is a valid aware
    datetime but NOT a valid YYYY-MM-DD date, so _as_date returns None
    and execution falls through to _aware_value, then to L254.
    """
    parsed, ok = tcg._coerce_field_value(
        "2026-01-01T00:00:00+00:00", require_aware=False
    )
    assert ok is True
    assert isinstance(parsed, datetime)
    assert parsed.tzinfo is not None
    assert parsed.utcoffset() == timezone.utc.utcoffset(parsed)


def test_m8a_three_clock__as_datetime_const_int_l215():
    """Kill mutant M8A three_clock #4
    (sni_three_clock_guard.py:215 col 22-23, ``1`` -> ``2``
    in ``body = body[:-1]``).

    A Z-suffixed ISO 8601 string is parsed by stripping exactly one
    trailing character. The mutation strips two, which leaves a
    truncated body that ``datetime.fromisoformat`` cannot parse, so
    _as_datetime returns None for a well-formed aware datetime. The
    correct path returns a non-None aware datetime.
    """
    parsed = tcg._as_datetime("2026-01-01T00:00:00Z")
    assert parsed is not None
    assert isinstance(parsed, datetime)
    # The Z is stripped and the body parses; year/month/day survive.
    assert (parsed.year, parsed.month, parsed.day) == (2026, 1, 1)


def test_m8a_three_clock__coerce_field_value_return_none_l242():
    """Kill mutant M8A three_clock #5
    (sni_three_clock_guard.py:242 col 8-26,
    ``return (None, False)`` -> ``return None``).

    The non-conforming branch of _coerce_field_value must return a
    (None, False) tuple, never bare None. The mutation returns None,
    which the caller cannot unpack. The function is called directly
    here because classify_clocks stringifies the record value before
    calling _coerce_field_value, so the non-string branch is only
    reachable from an external caller.
    """
    parsed, ok = tcg._coerce_field_value(20260630, require_aware=False)
    assert parsed is None
    assert ok is False


def test_m8a_three_clock__blank_constbool_l170():
    """Kill mutant M8A three_clock #6
    (sni_three_clock_guard.py:170 col 15-19, ``return True``
    -> ``return False``).

    _blank(None) must be literal True. The mutation returns False, so
    a None record value is treated as present by _present and the
    clock is silently filled from a None rather than refused as
    missing.
    """
    assert tcg._blank(None) is True
