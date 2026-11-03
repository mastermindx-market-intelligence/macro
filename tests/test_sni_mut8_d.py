"""M8D mutation-sweep killing tests for two SNI DRAFT guard modules.

Targets mutants that survived the existing suite in
research/single_name_intelligence/common/sni_join_guard.py and
research/single_name_intelligence/common/sni_ads_ratio_guard.py
(sweep record: research/single_name_intelligence/reviews/
MUTATION_SWEEP_M8D_2026-10-14.md). Each test names the exact mutant in its
docstring (file:line, original -> mutated) and kills exactly that mutant;
all pass on unmutated code.

SNI-local DRAFT contract tests. They consume owner-supplied opaque identity
strings (Stock Identity / Data OS) and synthetic depositary-ratio interval
records; they never mint issuer or security ids or ratios.
HISTORICAL-DESCRIPTIVE only: rank_authority, gate_authority, size_authority,
signal_authority, escalation_authority and trade_authority stay literal
False. Fixtures are synthetic.

This module does not register, validate, or feed a ranker, gate, sizer,
signal, escalation, or trade path.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMMON = ROOT / "research" / "single_name_intelligence" / "common"
sys.path.insert(0, str(COMMON))

import pytest  # noqa: E402

from sni_ads_ratio_guard import (  # noqa: E402
    _aware_datetime,
    _blank as ads_blank,
    _available_as_of,
    refuse_nonfalse_authority as ads_refuse_nonfalse_authority,
)
from sni_join_guard import (  # noqa: E402
    JoinVerdict,
    _known_at_later_than_as_of,
)


# ---------------------------------------------------------------------------
# sni_ads_ratio_guard.py survivors
# ---------------------------------------------------------------------------


def test_m8d_ads_ratio_guard__refuse_nonfalse_authority_isinstance_08():
    """Mutant sni_ads_ratio_guard_08: sni_ads_ratio_guard.py:75
    `if not isinstance(flags, Mapping): raise ValueError(...)` -> `pass`.

    A non-Mapping flags argument must raise ValueError("authority flags is
    not a mapping"), never AttributeError from `.items()` below.
    """
    with pytest.raises(ValueError, match="not a mapping"):
        ads_refuse_nonfalse_authority(["not-a-mapping"])


def test_m8d_ads_ratio_guard__blank_empty_string_14():
    """Mutant sni_ads_ratio_guard_14: sni_ads_ratio_guard.py:108
    `_blank` `value == ""` -> `value != ""`.

    `_blank("")` is True: the empty string is treated as ABSENT. The
    mutation inverts the boolean and flips `_blank("")` to False.
    """
    assert ads_blank("") is True


def test_m8d_ads_ratio_guard__aware_datetime_z_suffix_33():
    """Mutant sni_ads_ratio_guard_33: sni_ads_ratio_guard.py:202
    `_aware_datetime` `text[:-1] + "+00:00"` -> `text[:-1] - "+00:00"`.

    A Z-suffixed UTC timestamp must compare with a `+00:00`-suffixed one as
    the same instant; the mutation is plain str subtraction (TypeError).
    """
    parsed = _aware_datetime("2020-01-15T00:00:00Z")
    assert parsed is not None
    assert _available_as_of("2020-01-15T00:00:00Z", "2020-01-15T00:00:00+00:00") is True


# ---------------------------------------------------------------------------
# sni_join_guard.py survivors
# ---------------------------------------------------------------------------


def test_m8d_join_guard___post_init___allowed_with_reasons_13():
    """Mutant sni_join_guard_13: sni_join_guard.py:173
    `if self.reasons: raise ValueError("ALLOWED verdict cannot carry reasons")`
    -> `pass`.

    A JoinVerdict(status="ALLOWED", reasons=("X",), ...) is malformed and must
    be refused at construction time.
    """
    with pytest.raises(ValueError, match="ALLOWED verdict cannot carry reasons"):
        JoinVerdict(
            status="ALLOWED",
            reasons=("X",),
            join_kind="same_fact",
        )


def test_m8d_join_guard___known_at_later_than_as_of_non10_35():
    """Mutant sni_join_guard_35: sni_join_guard.py:263
    `_known_at_later_than_as_of` `len(as_of) == 10` -> `len(as_of) != 10`.

    On the date branch (when len(as_of) != 10 in the original), `_as_date`
    strips to first 10 chars; on the datetime branch, the full string is
    compared. The mutation swaps the branches; for a known_at whose time
    makes it strictly later (same date), the original returns True (dt
    comparison), the mutated returns False (date strip equal).
    """
    assert (
        _known_at_later_than_as_of("2020-01-01T00:00:01", "2020-01-01T00:00:00")
        is True
    )


def test_m8d_join_guard___known_at_later_than_as_of_strict_38():
    """Mutant sni_join_guard_38: sni_join_guard.py:268
    `_known_at_later_than_as_of` `kd > ad` -> `kd >= ad` (date branch).

    The contract is STRICTLY later: an equal known_at and as_of is NOT
    later-than and must return False. The mutation makes equal dates pass.
    """
    assert (
        _known_at_later_than_as_of("2020-01-01", "2020-01-01") is False
    )


def test_m8d_join_guard___known_at_later_than_as_of_datetime_path_39():
    """Mutant sni_join_guard_39: sni_join_guard.py:271
    `_known_at_later_than_as_of` `if kt is None or at is None: return False`
    -> `if kt is not None or at is not None: return False`.

    On the datetime branch (as_of len != 10), parseable datetimes must
    compare by value. The mutation returns False as long as either side is
    parseable, which inverts the contract.
    """
    assert (
        _known_at_later_than_as_of("2020-01-15T00:00:00", "2020-01-01T00:00:00")
        is True
    )


# ---------------------------------------------------------------------------
# Hardening for the un-observable module-level guard
# ---------------------------------------------------------------------------


def test_m8d_join_guard___module_level_authority_flags_pin():
    """Hardening for sni_join_guard.py:137 (module-level AUTHORITY_FLAGS
    per-key check) and the analogous site in sni_ads_ratio_guard.py:68.

    Both module-level guards are un-observable on the public contract because
    AUTHORITY_FLAGS is a module constant of literal False values; this test
    pins that the JoinVerdict post_init (line 166) does catch a True
    call-site flag, which is the OBSERVABLE behaviour the family rule ships.
    """
    from types import MappingProxyType

    with pytest.raises(ValueError):
        JoinVerdict(
            status="ALLOWED",
            reasons=(),
            join_kind="same_fact",
            authority=MappingProxyType(
                {
                    "rank_authority": False,
                    "gate_authority": True,  # one slot True
                    "size_authority": False,
                    "signal_authority": False,
                    "escalation_authority": False,
                    "trade_authority": False,
                }
            ),
        )
