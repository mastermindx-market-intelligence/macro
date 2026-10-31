"""M7G mutation-sweep killing tests for sni_comparison_guard.py.

Each test below kills one mutant that survived the existing importer suite
(``tests/test_sni_comparison_guard.py``, 73 tests) during the M7G sweep
(seed 20261015, 40 mutants applied; see
research/single_name_intelligence/reviews/MUTATION_SWEEP_M7G_2026-10-14.md).
The docstring of each test names the exact mutant (file:line, original ->
mutated) it was re-verified against.

Program law (SNI commission 8659) holds here too: these tests never set an
authority flag true in any production path -- the ``AUTHORITY_FLAGS`` test
proves the module REFUSES a corrupted self-check table, which is the
contract's enforcement mechanism, and monkeypatch restores the frozen
table. No identifier minting, no then-known violation, synthetic fixtures
only, nothing feeds a ranker/gate/sizer/signal/escalation/trade path.
"""
from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research" / "single_name_intelligence" / "common"))

import sni_comparison_guard as g  # noqa: E402
from sni_comparison_guard import check_comparison, refuse_nonfalse_authority  # noqa: E402


def test_m7g_sni_comparison_guard__as_date_7():
    """Mutant M7G id=7: sni_comparison_guard.py:149:46 `<` -> `<=`
    (in `_as_date`: `len(text) < 10` became `len(text) <= 10`, so exactly
    10-char ISO date strings stopped parsing)."""
    assert g._as_date("2026-01-05") == date(2026, 1, 5)


def test_m7g_sni_comparison_guard__as_date_8():
    """Mutant M7G id=8: sni_comparison_guard.py:149:48 `10` -> `11`
    (in `_as_date`: the minimum-length constant grew, so exactly 10-char
    ISO date strings returned None)."""
    assert g._as_date("2026-01-05") == date(2026, 1, 5)


def test_m7g_sni_comparison_guard__as_date_53():
    """Mutant M7G id=53: sni_comparison_guard.py:152:15
    `return date.fromisoformat(text[:10])` -> `return None`
    (in `_as_date`: every parseable date string returned None)."""
    assert g._as_date("2026-01-05") == date(2026, 1, 5)
    assert g._as_date("2026-01-05T09:30:00+08:00") == date(2026, 1, 5)


def test_m7g_sni_comparison_guard__as_date_6():
    """Mutant M7G id=6: sni_comparison_guard.py:149:33 `or` -> `and`
    (in `_as_date`: the non-str/short-circuit disjunction became a
    conjunction, so non-str inputs without ``len`` raised TypeError
    instead of returning None)."""
    assert g._as_date(123) is None
    assert g._as_date(None) is None


def test_m7g_sni_comparison_guard__as_datetime_13():
    """Mutant M7G id=13: sni_comparison_guard.py:160:20 `10` -> `11`
    (in `_as_datetime`: the bare-date branch length test changed, so an
    11-char trailing-`T` stub like "2026-01-05T" parsed as a datetime
    instead of returning None; on Python 3.11+ the 10-char happy path is
    result-identical, so the stub is the distinguishing input)."""
    assert g._as_datetime("2026-01-05") == datetime(2026, 1, 5, 0, 0)
    assert g._as_datetime("2026-01-05T") is None


def test_m7g_sni_comparison_guard__blank_49():
    """Mutant M7G id=49: sni_comparison_guard.py:141:11
    `return False` -> `return None` (in `_blank`: a present value stopped
    returning literal False). The predicate's bool contract is relied on
    by `_present`'s `not _blank(...)` and asserts below."""
    assert g._blank(5) is False
    assert g._blank("x") is False
    assert g._blank("") is True
    assert g._blank(None) is True


def test_m7g_sni_comparison_guard__finite_positive_real_57():
    """Mutant M7G id=57: sni_comparison_guard.py:196:11
    `return False` -> `return None` (in `_finite_positive_real`: the
    fall-through for non-numeric values stopped returning literal
    False)."""
    assert g._finite_positive_real("7") is False
    assert g._finite_positive_real(None) is False
    assert g._finite_positive_real(True) is False
    assert g._finite_positive_real(-1.0) is False
    assert g._finite_positive_real(5) is True


def test_m7g_sni_comparison_guard__refuse_nonfalse_authority_70():
    """Mutant M7G id=70: sni_comparison_guard.py:108-109
    deletion of `if not isinstance(flags, Mapping): raise ValueError(...)`
    (a non-mapping flags argument fell through to `.items()` and raised
    AttributeError instead of the contract's ValueError)."""
    with pytest.raises(ValueError, match="authority flags is not a mapping"):
        refuse_nonfalse_authority(["rank_authority"])  # type: ignore[arg-type]


def test_m7g_sni_comparison_guard__refuse_nonfalse_authority_75(monkeypatch):
    """Mutant M7G id=75: sni_comparison_guard.py:101-105
    deletion of the AUTHORITY_FLAGS self-check `if value is not False:
    raise ValueError(...)` inside the module-flags loop (a corrupted
    module flags table stopped being refused). Proves the refusal, never
    grants authority: the frozen table is restored by monkeypatch."""
    monkeypatch.setattr(g, "AUTHORITY_FLAGS", {"rank_authority": True})
    with pytest.raises(ValueError, match="must be literal False"):
        refuse_nonfalse_authority()


def test_m7g_sni_comparison_guard__check_comparison_73():
    """Mutant M7G id=73: sni_comparison_guard.py:303-304
    deletion of `if not isinstance(right, Mapping): raise TypeError(...)`
    (a non-mapping right leg fell into `.get` and raised AttributeError
    instead of the contract's TypeError)."""
    left = {
        "price": 1.0,
        "price_ts": "2026-06-15T15:30:00+00:00",
        "session_state": "continuous",
        "instrument_role": "target",
        "issuer_id": "iss-opaque-1",
        "currency": "USD",
        "known_at": "2026-06-15T15:31:00+00:00",
    }
    with pytest.raises(TypeError, match="right must be a Mapping"):
        check_comparison(left, "not-a-mapping", None, as_of="2026-06-15T16:00:00+00:00")
