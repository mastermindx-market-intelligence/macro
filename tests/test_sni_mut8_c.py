"""M8C mutation-sweep killing tests for sni_denominator_guard.py and
sni_comparison_guard.py.

Each test below kills one mutant that survived the existing importer
suite during the M8C sweep (seed 20261016, 40 mutants per module; see
research/single_name_intelligence/reviews/MUTATION_SWEEP_M8C_2026-10-14.md).
The docstring of each test names the exact mutant (file:line, original ->
mutated) it was re-verified against.

Importer set run by the harness for sni_denominator_guard:
    tests/test_sni_denominator_guard.py,
    tests/test_sni_guard_family_invariants.py,
    tests/test_sni_guard_chain_composition.py,
    tests/test_sni_famdc_repair.py,
    tests/test_sni_mut7_f.py.

Importer set run by the harness for sni_comparison_guard:
    tests/test_sni_comparison_guard.py,
    tests/test_sni_guard_family_invariants.py,
    tests/test_sni_guard_chain_composition.py,
    tests/test_sni_mut7_g.py.

Program law (SNI commission 8659) holds here too: these tests never set an
authority flag true in any production path -- the AUTHORITY_FLAGS tests
prove the module REFUSES a corrupted self-check table, which is the
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

import sni_denominator_guard as d  # noqa: E402
import sni_comparison_guard as c  # noqa: E402
from sni_denominator_guard import (  # noqa: E402
    AUTHORITY_FLAGS as DENOM_AUTHORITY_FLAGS,
    refuse_nonfalse_authority,
)
from sni_comparison_guard import (  # noqa: E402
    AUTHORITY_FLAGS as COMP_AUTHORITY_FLAGS,
    _finite_positive_real as _comp_fpr,
)


# ---------------------------------------------------------------------------
# DENOMINATOR killing tests
# ---------------------------------------------------------------------------


def test_m8c_denom_as_date_slice_4():
    """Mutant M8C id=4: sni_denominator_guard.py:161 col40 `10` -> `11`
    (in `_as_date`: `text[:10]` became `text[:11]`, so a 10+1 character
    prefix where the 11th character is not a digit of an ISO date stopped
    parsing and the function returned None instead of the first 10 chars
    as a date)."""
    assert d._as_date("2026-01-05extra") == date(2026, 1, 5)


def test_m8c_denom_as_datetime_date_only_6():
    """Mutant M8C id=6: sni_denominator_guard.py:173
    `return datetime(parsed.year, parsed.month, parsed.day)` -> `return None`
    (in `_as_datetime`: every bare-date 10-char input now returns None
    instead of a naive datetime)."""
    assert d._as_datetime("2026-08-20") == datetime(2026, 8, 20, 0, 0)


def test_m8c_denom_refuse_nonfalse_authority_non_mapping_19():
    """Mutant M8C id=19: sni_denominator_guard.py:87-88 deletion of
    `if not isinstance(flags, Mapping): raise ValueError("authority flags
    is not a mapping")` (a non-mapping flags argument fell through to
    `.items()` and raised AttributeError instead of the contract's
    ValueError)."""
    with pytest.raises(ValueError, match="authority flags is not a mapping"):
        refuse_nonfalse_authority(["rank_authority"])  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="authority flags is not a mapping"):
        refuse_nonfalse_authority(("rank_authority",))  # type: ignore[arg-type]


def test_m8c_denom_text_present_minus_one_to_plus_one_21():
    """Mutant M8C id=21: sni_denominator_guard.py:131 col22 `-` -> `+`
    (in `_text_present`: `value[-1]` became `value[+1]`, so a trailing-
    whitespace text ref was judged by its second character instead of its
    last and reported TRUE for input like "a x")."""
    assert d._text_present("a x") is True
    assert d._text_present("a x ") is False


def test_m8c_denom_blank_empty_string_23():
    """Mutant M8C id=23: sni_denominator_guard.py:144 col15 `True` -> `False`
    (in `_blank`: the ``return True`` for `value == ""` became `return
    False`, so an empty string stopped being treated as blank)."""
    assert d._blank("") is True
    assert d._blank(None) is True
    assert d._blank(0) is False
    assert d._blank("x") is False


def test_m8c_denom_finite_positive_float_28():
    """Mutant M8C id=28: sni_denominator_guard.py:224 col23 `0` -> `1`
    (in `_finite_positive`: `return value > 0` became `return value > 1`,
    so the float 1.0 stopped being accepted as a positive finite
    value)."""
    assert d._finite_positive(1.0) is True
    assert d._finite_positive(0.5) is True
    assert d._finite_positive(1) is True
    assert d._finite_positive(2) is True


def test_m8c_denom_refuse_nonfalse_authority_module_flags_29(monkeypatch):
    """Mutant M8C id=29: sni_denominator_guard.py:79-83 deletion of
    `if value is not False: raise ValueError(...)` inside the
    AUTHORITY_FLAGS self-check loop (a corrupted module flags table
    stopped being refused). Proves the refusal, never grants authority:
    the frozen table is restored by monkeypatch."""
    monkeypatch.setattr(d, "AUTHORITY_FLAGS", {"rank_authority": True})
    with pytest.raises(ValueError, match="must be literal False"):
        refuse_nonfalse_authority()


def test_m8c_denom_as_date_lt_to_le_30():
    """Mutant M8C id=30: sni_denominator_guard.py:158 col46 `<` -> `<=`
    (in `_as_date`: `len(text) < 10` became `len(text) <= 10`, so
    exactly 10-character strings returned None instead of the parsed
    date)."""
    assert d._as_date("2026-01-05") == date(2026, 1, 5)


def test_m8c_denom_as_datetime_z_suffix_38():
    """Mutant M8C id=38: sni_denominator_guard.py:176 col22 `1` -> `2`
    (in `_as_datetime`: `body[:-1]` became `body[:-2]`, so a Z-suffixed
    input left one non-Z character before fromisoformat and failed to
    parse). The public `_aware_datetime` strips Z and rewrites it as
    `+00:00`, so this branch is reachable only by a direct test of the
    private helper."""
    assert d._as_datetime("2026-01-05T00:00:00Z") == datetime(
        2026, 1, 5, 0, 0, 0
    )


# ---------------------------------------------------------------------------
# COMPARISON killing tests
# ---------------------------------------------------------------------------


def test_m8c_comp_finite_positive_real_one_2():
    """Mutant M8C id=2: sni_comparison_guard.py:217 col23 `0` -> `1`
    (in `_finite_positive_real`: `return value > 0` became `return
    value > 1`, so the int 1 stopped being accepted as a positive real
    value)."""
    assert _comp_fpr(1) is True
    assert _comp_fpr(0) is False
    assert _comp_fpr(-1) is False
    assert _comp_fpr(1.0) is True
    assert _comp_fpr(0.5) is True
    assert _comp_fpr(True) is False


def test_m8c_comp_fx_reasons_non_mapping_8():
    """Mutant M8C id=8: sni_comparison_guard.py:281-282 deletion of
    `if not isinstance(fx, Mapping): raise TypeError("fx must be a Mapping
    or None")` (the public `check_comparison` already raises TypeError on
    the same input at L335, so the public path is equivalent; the
    defense-in-depth guard is reachable only via a direct call to
    `_fx_reasons`). Under the mutant a direct call falls through to
    `.get` and raises AttributeError instead. The two legs must be
    cross-currency so the same-currency short-circuit at L275 does not
    preempt the fx argument's type check."""
    with pytest.raises(TypeError, match="fx must be a Mapping"):
        c._fx_reasons(
            {"currency": "USD"},
            {"currency": "HKD"},
            "not-a-mapping",  # type: ignore[arg-type]
            as_of="2026-06-15T16:00:00+00:00",
            max_fx_staleness_seconds=300,
        )


def test_m8c_comp_text_present_minus_to_plus_16():
    """Mutant M8C id=16: sni_comparison_guard.py:151 col22 `-` -> `+`
    (in `_text_present`: `value[-1]` became `value[+1]`, so a string
    whose last character is whitespace but whose second character is
    not stopped being reported as ABSENT)."""
    assert c._text_present("a x") is True
    assert c._text_present("a x ") is False


def test_m8c_comp_text_present_zero_to_one_26():
    """Mutant M8C id=26: sni_comparison_guard.py:150 col22 `0` -> `1`
    (in `_text_present`: `value[0]` became `value[1]`, so a leading-
    whitespace input whose second character is not whitespace stopped
    being reported as ABSENT)."""
    assert c._text_present(" hello") is False
    assert c._text_present("h ello") is True
    assert c._text_present("  ") is False


def test_m8c_comp_text_present_minus_one_to_minus_two_37():
    """Mutant M8C id=37: sni_comparison_guard.py:151 col23 `1` -> `2`
    (in `_text_present`: `value[-1]` became `value[-2]`, so a trailing
    whitespace test ref that has a non-whitespace character one in from
    the end was judged by index -2 and returned True)."""
    assert c._text_present("a x ") is False
    assert c._text_present("a  x") is True


# ---------------------------------------------------------------------------
# Authority-flags sanity for both modules (anchors the module-level
# mapping's all-False contract at the start of every M8C run; not a
# mutation kill, just a smoke pin).
# ---------------------------------------------------------------------------


def test_m8c_authority_flags_anchors():
    for name in (
        "rank_authority",
        "gate_authority",
        "size_authority",
        "signal_authority",
        "escalation_authority",
        "trade_authority",
    ):
        assert DENOM_AUTHORITY_FLAGS[name] is False
        assert COMP_AUTHORITY_FLAGS[name] is False