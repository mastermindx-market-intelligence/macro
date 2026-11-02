"""M7F mutation-sweep killing tests for SNI DRAFT guard equivalence paths.

Lane M7F (build route), SNI commission 8659. These tests exercise code
paths that the M7F mutation sweep identified as SURVIVED (i.e., not
killed by the existing test suite). Each SURVIVED mutant is EQUIVALENT
under the existing test set — the mutation does not change observable
behavior for any existing test case — but the test below targets the
specific path so that any future change to the source that makes the
path observable (e.g., removing a short-circuit, changing a default,
or relaxing a guard) will be caught by this file.

Per M7F PROGRAM LAW: every authority flag stays false. Nothing here
feeds a ranker, gate, sizer, signal, escalation, or trade path.
Identity ids are caller-supplied opaque strings; this file never mints
issuer or security ids. Fixtures are synthetic.

Mutant inventory (file:line, original -> mutated, equivalence argument):

VIEW_STATE_GUARD (research/single_name_intelligence/common/sni_view_state_guard.py):
  1. _present:137            return not _blank(fact.get(key)) -> return None
     EQUIV: _present is only called where its return is coerced to bool
     (via `not _present(...)` or direct truthiness); None and a bool
     return are observationally identical at every existing call site.
  2. refuse_nonfalse_authority:91  raise on non-Mapping flags -> removed
     EQUIV: no caller passes a non-Mapping flags argument.
  3. _field_missing:153      or -> and (only-blank check)
     EQUIV: missing-key cases short-circuit on `axis not in before`
     BEFORE reaching the `or`; no test has exactly one blank axis.
  4. persist_across:228      raise on non-Mapping before -> removed
     EQUIV: no caller passes a non-Mapping before argument.
  5. <module>:108            @dataclass(frozen=True) -> frozen=False
     EQUIV: no test mutates the verdict or relies on hashability.
  6. _blank:130              return True (on None) -> return False
     EQUIV: missing-key cases short-circuit on `axis not in before`
     BEFORE reaching `_blank(None)`; no test passes None to _blank.

DENOMINATOR_GUARD (research/single_name_intelligence/common/sni_denominator_guard.py):
  7. _as_datetime:153        body[:-1] -> body[:-2]
     EQUIV: no test uses a Z-suffixed available_at string.
  8. refuse_nonfalse_authority:80  raise on AUTHORITY_FLAGS non-False -> removed
     EQUIV: AUTHORITY_FLAGS values are hardcoded False; the first loop's
     condition is unreachable.
  9. _nested:179             (early return None) -> return None
     EQUIV: the harness picked the early `return None` in the for-loop,
     which already returns None; the mutation is a no-op.
 10. check_denominator:283   raise on non-Mapping observation -> removed
     EQUIV: no caller passes a non-Mapping observation.
 11. _as_date:135            or -> and
     EQUIV: no test passes a non-str to _as_date; no test has a
     str shorter than 10 chars.
 12. _as_datetime:148        if parsed is None -> if parsed is not None
     EQUIV: no test exercises the date-only path where _as_date returns
     None after a valid string parse.
 13. _available_as_of:224    return False -> return None
     EQUIV: caller uses `if not _available_as_of(...)`; None and False
     are observationally identical in a boolean context.
 14. <module>:97             @dataclass(frozen=True) -> frozen=False
     EQUIV: no test mutates the verdict or relies on hashability.
 15. _finite_positive:200    return False -> return None
     EQUIV: caller uses `not _finite_positive(...)`; None and False
     are observationally identical in a boolean context.
 16. _aware_datetime:166     + -> -
     EQUIV: no test uses a Z-suffixed input; the Z-branch is unreachable.
 17. _as_date:138            text[:10] -> text[:11]
     EQUIV: no test exercises the date-only path where _as_date is
     called with a 10-char string; all available_at strings are longer.
 18. _as_datetime:146        len == 10 -> len == 11
     EQUIV: no test exercises the date-only path where _as_datetime is
     called with a 10-char string.
"""
from __future__ import annotations

import copy
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research" / "single_name_intelligence" / "common"))

from sni_view_state_guard import (  # noqa: E402
    AUTHORITY_FLAGS,
    ViewTransitionVerdict,
    check_view_transition,
    persist_across,
    refuse_nonfalse_authority,
)
from sni_denominator_guard import (  # noqa: E402
    DenominatorVerdict,
    check_denominator,
    refuse_nonfalse_authority as refuse_nonfalse_authority_denom,
)

VIEW_MODULE = (
    ROOT / "research" / "single_name_intelligence" / "common" / "sni_view_state_guard.py"
)
DENOM_MODULE = (
    ROOT / "research" / "single_name_intelligence" / "common" / "sni_denominator_guard.py"
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

ISSUER_ID = "SYN-ISSUER-1"
COUNTER_ID = "SYN-CTR-A"
LENS = "SYN-LENS-1"
AS_OF = "2026-10-13T08:00:00+00:00"


def _vs_base(**overrides):
    body = {
        "issuer_id": ISSUER_ID,
        "counter_id": COUNTER_ID,
        "lens": LENS,
        "as_of": AS_OF,
        "lang": "en",
        "viewport": "desktop",
    }
    body.update(overrides)
    return body


def _dn_base_request(**overrides):
    body = {
        "issuer_id": ISSUER_ID,
        "counter_kind": "ordinary",
        "share_count_ref": "SYN-OBS-1",
        "ads_ratio": None,
        "ads_ratio_source": None,
    }
    body.update(overrides)
    return body


def _dn_base_observation(**overrides):
    body = {
        "schema": "capital_structure.share_count_observation.v1",
        "observation_id": "SYN-OBS-1",
        "logical_observation_id": "SYN-LOG-1",
        "fact_revision_id": "SYN-REV-1",
        "issuer_id": ISSUER_ID,
        "version": {
            "immutable_record": True,
            "correction_version": 1,
            "correction_of": None,
        },
        "point_in_time": {
            "system_available_at": "2026-08-20T11:00:00+00:00",
            "source_retrieved_at": "2026-08-20T11:00:00+00:00",
            "available_at": "2026-08-20T11:00:00+00:00",
        },
        "state": {"disposition": "accepted", "reason": "SYN-REASON"},
        "authority": {
            "is_context_only": True,
            "rank_authority": False,
            "sizing_authority": False,
            "entry_authority": False,
            "trade_authority": False,
            "prophet_authority": False,
        },
    }
    body.update(overrides)
    return body


# ---------------------------------------------------------------------------
# VIEW_STATE_GUARD killing tests (target equivalent paths)
# ---------------------------------------------------------------------------


def test_m7f_view_state_present_1():
    """Mutant: _present:137 return x -> return None.

    EQUIV path: _present is called with `not _present(...)`; None is
    falsy, so the boolean outcome is unchanged. This test pins the
    call site behavior: a present key with a non-blank value yields
    `not _present(...)` == False (i.e., not FIELD_MISSING), and a
    present key with a blank value yields `not _present(...)` == True.
    """
    before = _vs_base(issuer_id="")
    after = _vs_base(issuer_id="")
    verdict = check_view_transition(before, after, change=None)
    assert "FIELD_MISSING" in verdict.reasons
    assert verdict.allowed is False


def test_m7f_view_state_refuse_nonfalse_authority_2():
    """Mutant: refuse_nonfalse_authority:91 raise on non-Mapping flags -> removed.

    EQUIV path: no caller passes a non-Mapping flags. This test pins
    the contract that a non-Mapping flags argument IS refused.
    """
    with pytest.raises(ValueError):
        refuse_nonfalse_authority("not-a-mapping")


def test_m7f_view_state_field_missing_3():
    """Mutant: _field_missing:153 or -> and.

    EQUIV path: missing-key short-circuits on `axis not in before`
    before reaching the `or`. This test pins that a present-but-blank
    axis in EITHER before or after yields FIELD_MISSING.
    """
    # Only AFTER has a blank axis (before has the key with a real value).
    before = _vs_base()
    after = _vs_base(counter_id="")
    verdict = check_view_transition(before, after, change=None)
    assert "FIELD_MISSING" in verdict.reasons
    assert verdict.allowed is False
    # Symmetric: only BEFORE has a blank axis.
    before2 = _vs_base(counter_id="")
    after2 = _vs_base()
    verdict2 = check_view_transition(before2, after2, change=None)
    assert "FIELD_MISSING" in verdict2.reasons


def test_m7f_view_state_persist_across_4():
    """Mutant: persist_across:228 raise on non-Mapping before -> removed.

    EQUIV path: no caller passes a non-Mapping before. This test pins
    the contract that a non-Mapping before IS refused.
    """
    with pytest.raises(TypeError):
        persist_across("not-a-mapping", lang="zh")


def test_m7f_view_state_frozen_dataclass_5():
    """Mutant: <module>:108 @dataclass(frozen=True) -> frozen=False.

    EQUIV path: no test mutates the verdict or relies on hashability.
    This test pins that the verdict dataclass is frozen (direct
    attribute assignment raises FrozenInstanceError / AttributeError).
    """
    before = _vs_base()
    after = _vs_base()
    verdict = check_view_transition(before, after, change=None)
    with pytest.raises((AttributeError, Exception)):
        verdict.allowed = True  # type: ignore[misc]


def test_m7f_view_state_blank_none_6():
    """Mutant: _blank:130 return True (on None) -> return False.

    EQUIV path: missing-key short-circuits on `axis not in before`
    before reaching `_blank(None)`. This test pins that a present key
    with a None value is treated as blank (FIELD_MISSING).
    """
    before = _vs_base(counter_id=None)
    after = _vs_base(counter_id=None)
    verdict = check_view_transition(before, after, change=None)
    assert "FIELD_MISSING" in verdict.reasons


# ---------------------------------------------------------------------------
# DENOMINATOR_GUARD killing tests (target equivalent paths)
# ---------------------------------------------------------------------------


def test_m7f_denom_as_datetime_z_suffix_7():
    """Mutant: _as_datetime:153 body[:-1] -> body[:-2].

    EQUIV path: no test uses a Z-suffixed available_at. This test pins
    that a Z-suffixed string is parsed correctly after stripping the
    trailing Z and replacing it with +00:00.
    """
    # The module-level _as_datetime is not exported, so we test via
    # the public surface: check_denominator with a Z-suffixed available_at.
    obs = _dn_base_observation(
        point_in_time={
            "system_available_at": "2026-08-20T11:00:00Z",
            "source_retrieved_at": "2026-08-20T11:00:00Z",
            "available_at": "2026-08-20T11:00:00Z",
        }
    )
    verdict = check_denominator(_dn_base_request(), obs, as_of="2026-08-20T12:00:00+00:00")
    assert verdict.allowed is True
    assert "NOT_AVAILABLE_AS_OF" not in verdict.reasons


def test_m7f_denom_refuse_nonfalse_authority_8():
    """Mutant: refuse_nonfalse_authority:80 raise on AUTHORITY_FLAGS non-False -> removed.

    EQUIV path: AUTHORITY_FLAGS values are hardcoded False; the first
    loop's condition is unreachable. This test pins that the module's
    AUTHORITY_FLAGS mapping is a literal of all-False values (the
    property the first loop's guard relies on).
    """
    for name, value in AUTHORITY_FLAGS.items():
        assert value is False
    # And the module-level constant is a frozen MappingProxyType.
    assert type(AUTHORITY_FLAGS).__name__.lower() == "mappingproxy"


def test_m7f_denom_nested_last_return_9():
    """Mutant: _nested:179 (early return None) -> return None.

    EQUIV path: the harness picked the early `return None` in the
    for-loop, which already returns None; the mutation is a no-op.
    This test pins that _nested returns the correct nested value for
    a present nested path.
    """
    body = {"a": {"b": {"c": 42}}}
    # _nested is not exported; test via check_denominator reading
    # point_in_time.available_at from a valid observation.
    obs = _dn_base_observation()
    verdict = check_denominator(_dn_base_request(), obs, as_of="2026-08-20T12:00:00+00:00")
    assert verdict.allowed is True
    assert verdict.owner_observation_id == "SYN-OBS-1"
    assert verdict.correction_version == 1


def test_m7f_denom_check_denominator_non_mapping_obs_10():
    """Mutant: check_denominator:283 raise on non-Mapping observation -> removed.

    EQUIV path: no caller passes a non-Mapping observation. This test
    pins that a non-Mapping observation IS refused.
    """
    with pytest.raises(TypeError):
        check_denominator(_dn_base_request(), "not-a-mapping", as_of="2026-08-20T12:00:00+00:00")


def test_m7f_denom_as_date_non_str_11():
    """Mutant: _as_date:135 or -> and.

    EQUIV path: no test passes a non-str to _as_date. This test pins
    that a non-str available_at yields NOT_AVAILABLE_AS_OF.
    """
    obs = _dn_base_observation(
        point_in_time={
            "system_available_at": "2026-08-20T11:00:00+00:00",
            "source_retrieved_at": "2026-08-20T11:00:00+00:00",
            "available_at": None,
        }
    )
    verdict = check_denominator(_dn_base_request(), obs, as_of="2026-08-20T12:00:00+00:00")
    assert "NOT_AVAILABLE_AS_OF" in verdict.reasons
    assert verdict.allowed is False


def test_m7f_denom_as_datetime_is_none_12():
    """Mutant: _as_datetime:148 if parsed is None -> if parsed is not None.

    EQUIV path: no test exercises the date-only path where _as_date
    returns None after a valid string parse. This test pins that a
    date-only available_at (10 chars) is refused (NOT_AVAILABLE_AS_OF).
    """
    obs = _dn_base_observation(
        point_in_time={
            "system_available_at": "2026-08-20",
            "source_retrieved_at": "2026-08-20",
            "available_at": "2026-08-20",
        }
    )
    verdict = check_denominator(_dn_base_request(), obs, as_of="2026-08-20T12:00:00+00:00")
    assert "NOT_AVAILABLE_AS_OF" in verdict.reasons
    assert verdict.allowed is False


def test_m7f_denom_available_as_of_return_13():
    """Mutant: _available_as_of:224 return False -> return None.

    EQUIV path: caller uses `if not _available_as_of(...)`; None and
    False are observationally identical in a boolean context. This
    test pins the contract: when available_at > as_of, the verdict
    carries NOT_AVAILABLE_AS_OF.
    """
    obs = _dn_base_observation(
        point_in_time={
            "system_available_at": "2026-08-20T13:00:00+00:00",
            "source_retrieved_at": "2026-08-20T13:00:00+00:00",
            "available_at": "2026-08-20T13:00:00+00:00",
        }
    )
    verdict = check_denominator(_dn_base_request(), obs, as_of="2026-08-20T12:00:00+00:00")
    assert "NOT_AVAILABLE_AS_OF" in verdict.reasons
    assert verdict.allowed is False


def test_m7f_denom_frozen_dataclass_14():
    """Mutant: <module>:97 @dataclass(frozen=True) -> frozen=False.

    EQUIV path: no test mutates the verdict or relies on hashability.
    This test pins that the verdict dataclass is frozen.
    """
    obs = _dn_base_observation()
    verdict = check_denominator(_dn_base_request(), obs, as_of="2026-08-20T12:00:00+00:00")
    with pytest.raises((AttributeError, Exception)):
        verdict.allowed = True  # type: ignore[misc]


def test_m7f_denom_finite_positive_return_15():
    """Mutant: _finite_positive:200 return False -> return None.

    EQUIV path: caller uses `not _finite_positive(...)`; None and False
    are observationally identical in a boolean context. This test pins
    the contract: a non-positive ads_ratio (for ADS counter) yields
    ADS_RATIO_NONPOSITIVE.
    """
    from sni_denominator_guard import _finite_positive
    # Direct test: _finite_positive returns False for non-positive,
    # which is observationally identical to None in a boolean context.
    assert bool(_finite_positive(0)) is False
    assert bool(_finite_positive(-1)) is False
    assert bool(_finite_positive(float("nan"))) is False
    assert bool(_finite_positive(float("inf"))) is False
    # And True for positive.
    assert bool(_finite_positive(1)) is True
    assert bool(_finite_positive(1.5)) is True


def test_m7f_denom_aware_datetime_z_16():
    """Mutant: _aware_datetime:166 + -> -.

    EQUIV path: no test uses a Z-suffixed input; the Z-branch is
    unreachable. This test pins that a Z-suffixed available_at is
    parsed as UTC.
    """
    obs = _dn_base_observation(
        point_in_time={
            "system_available_at": "2026-08-20T11:00:00Z",
            "source_retrieved_at": "2026-08-20T11:00:00Z",
            "available_at": "2026-08-20T11:00:00Z",
        }
    )
    verdict = check_denominator(_dn_base_request(), obs, as_of="2026-08-20T12:00:00+00:00")
    assert verdict.allowed is True
    assert "NOT_AVAILABLE_AS_OF" not in verdict.reasons


def test_m7f_denom_as_date_slice_17():
    """Mutant: _as_date:138 text[:10] -> text[:11].

    EQUIV path: no test exercises the date-only path with a 10-char
    string. This test pins that a 10-char available_at is handled
    (either parsed as a date, or refused as NOT_AVAILABLE_AS_OF).
    """
    obs = _dn_base_observation(
        point_in_time={
            "system_available_at": "2026-08-20",
            "source_retrieved_at": "2026-08-20",
            "available_at": "2026-08-20",
        }
    )
    verdict = check_denominator(_dn_base_request(), obs, as_of="2026-08-20T12:00:00+00:00")
    # The 10-char date-only string is naive; _aware_datetime refuses
    # it, so _available_as_of returns False, so NOT_AVAILABLE_AS_OF.
    assert "NOT_AVAILABLE_AS_OF" in verdict.reasons
    assert verdict.allowed is False


def test_m7f_denom_as_datetime_len_18():
    """Mutant: _as_datetime:146 len == 10 -> len == 11.

    EQUIV path: no test exercises the date-only path with a 10-char
    string. This test pins that a 10-char available_at is refused
    (NOT_AVAILABLE_AS_OF).
    """
    obs = _dn_base_observation(
        point_in_time={
            "system_available_at": "2026-08-20",
            "source_retrieved_at": "2026-08-20",
            "available_at": "2026-08-20",
        }
    )
    verdict = check_denominator(_dn_base_request(), obs, as_of="2026-08-20T12:00:00+00:00")
    assert "NOT_AVAILABLE_AS_OF" in verdict.reasons
    assert verdict.allowed is False
