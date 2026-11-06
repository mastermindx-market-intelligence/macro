"""FAMDC repair tests — FAMILY TEXT RULE applied to denominator and
comparison guards (LR-MEAS-B3 → R1 REQUEST_REPAIR round 1).

Each closed defect from the seat's FROZEN REPAIR SPEC gets a parametrized
test that exercises whitespace-only, padded, and non-str (1, True, [],
{}) value classes per the FAMILY TEXT RULE. For defects where the base
``_blank`` accepted a value the spec demands ABSENT, the test fails on
the base bytes and passes on the patched module. For fields the rule
exempts — correction_version (numeric) and closed-set enums
(counter_kind, session_state, instrument_role) — the existing
numeric / set-membership checks already refuse every defect class, so
those tests pass on base and head and serve as invariant pins; the rule
explicitly tells us not to route them through ``_text_present``.

SNI-local DRAFT contract tests. They consume owner-supplied opaque
identity strings (Stock Identity / Data OS) and Capital Structure
observation mappings; they never mint issuer or security ids, share
counts, ADS ratios, FX rates, or instrument roles. HISTORICAL-DESCRIPTIVE
only: rank_authority, gate_authority, size_authority, signal_authority,
escalation_authority and trade_authority stay literal False. Fixtures are
synthetic.

This module does not register, validate, or feed a ranker, gate, sizer,
signal, escalation, or trade path.
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research" / "single_name_intelligence" / "common"))

from sni_comparison_guard import check_comparison  # noqa: E402
from sni_denominator_guard import check_denominator  # noqa: E402

# ---------------------------------------------------------------------------
# Fixtures and constants
# ---------------------------------------------------------------------------

AS_OF = "2026-08-20T12:00:00+00:00"
AVAILABLE_AT = "2026-08-20T11:00:00+00:00"
OBS_ID = "SYN-OBS-1"
ISSUER_ID = "SYN-ISSUER-1"
ADS_RATIO_SOURCE = "SYN-ADS-RATIO-OWNER-1"

COMP_AS_OF = "2026-06-15T16:00:00+00:00"
PRICE_TS = "2026-06-15T15:30:00+00:00"
KNOWN_AT = "2026-06-15T15:31:00+00:00"

OWNER_SCHEMA = "capital_structure.share_count_observation.v1"

# Whitespace-only / padded / non-str defect classes per FAMILY TEXT RULE.
WHITESPACE_VALUES = (" ", " \t", " \n")
PADDED_VALUES = ("X ", " X", "X\t")
NON_STR_VALUES = (1, True, 1.0, [], {})
# Union is the closed set the seat named explicitly; we additionally fold a
# frozenset for the unhashable test.
UNHASHABLE_VALUES = ([1, 2], {"a": 1}, {1, 2}, frozenset())


def _den_request(**overrides):
    body = {
        "issuer_id": ISSUER_ID,
        "counter_kind": "ordinary",
        "share_count_ref": OBS_ID,
        "ads_ratio": None,
        "ads_ratio_source": None,
    }
    body.update(overrides)
    return body


def _ads_request(**overrides):
    body = {
        "counter_kind": "ads",
        "ads_ratio": 8,
        "ads_ratio_source": ADS_RATIO_SOURCE,
    }
    body.update(overrides)
    return body


def _den_observation(**overrides):
    body = {
        "schema": OWNER_SCHEMA,
        "observation_id": OBS_ID,
        "version": {
            "immutable_record": True,
            "correction_version": 1,
            "correction_of": None,
        },
        "point_in_time": {
            "system_available_at": AVAILABLE_AT,
            "source_retrieved_at": AVAILABLE_AT,
            "available_at": AVAILABLE_AT,
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
        "issuer_id": ISSUER_ID,
    }
    body.update(overrides)
    return body


def _leg(**overrides):
    body = {
        "issuer_id": ISSUER_ID,
        "instrument_role": "target",
        "price": 100.0,
        "price_ts": PRICE_TS,
        "currency": "USD",
        "session_state": "continuous",
        "known_at": KNOWN_AT,
    }
    body.update(overrides)
    return body


def _fx(**overrides):
    body = {
        "base": "USD",
        "quote": "HKD",
        "rate": 7.8,
        "rate_ts": PRICE_TS,
        "known_at": KNOWN_AT,
    }
    body.update(overrides)
    return body


def _check_den(request, observation, **kwargs):
    kwargs.setdefault("as_of", AS_OF)
    return check_denominator(request, observation, **kwargs)


def _check_cmp(left, right, fx=None, **kwargs):
    params = {
        "as_of": COMP_AS_OF,
        "max_fx_staleness_seconds": 300,
        "max_price_skew_seconds": 60,
        "requested_role": "target",
    }
    params.update(kwargs)
    return check_comparison(left, right, fx, **params)


# ---------------------------------------------------------------------------
# 01 — denominator guard
# owner_ref (observation_id + share_count_ref), issuer ids,
# correction_version (numeric — PIN), counter_kind (closed set — PIN),
# ads_ratio_source.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("value", WHITESPACE_VALUES + PADDED_VALUES + NON_STR_VALUES)
def test_r1_01_denominator_owner_ref(value):
    """Both sides equal defect value — base ``_blank`` accepts each,
    ``obs_id != share_count_ref`` is False, so OWNER_REF_MISSING misses.
    FAMILY TEXT RULE treats each as ABSENT and refuses."""
    request = _den_request(share_count_ref=value)
    observation = _den_observation(observation_id=value)
    verdict = _check_den(request, observation)
    assert "OWNER_REF_MISSING" in verdict.reasons, (value, verdict.reasons)
    assert verdict.allowed is False, value


@pytest.mark.parametrize("value", WHITESPACE_VALUES + PADDED_VALUES + NON_STR_VALUES)
def test_r1_01_denominator_issuer_id(value):
    """Both sides equal defect value — base misses ISSUER_MISMATCH.
    FAMILY TEXT RULE refuses."""
    request = _den_request(issuer_id=value)
    observation = _den_observation(issuer_id=value)
    verdict = _check_den(request, observation)
    assert "ISSUER_MISMATCH" in verdict.reasons, (value, verdict.reasons)
    assert verdict.allowed is False, value


@pytest.mark.parametrize(
    "value",
    # correction_version is a numeric field; the FAMILY TEXT RULE
    # exempts numbers from ``_text_present`` and they keep their existing
    # checks. ``_correction_version_value`` rejects every value except
    # an actual int >= 1. We feed each non-int defect class and expect
    # CORRECTION_VERSION_MISSING on both base and head — invariant PIN.
    # Int ``1`` is a valid correction_version so it must NOT be in the
    # defect set.
    list(WHITESPACE_VALUES) + list(PADDED_VALUES) + [True, 1.0, [], {}],
)
def test_r1_01_denominator_correction_version(value):
    """Numeric field; the FAMILY TEXT RULE exempts numbers from
    ``_text_present``. ``_correction_version_value`` already returns
    ``None`` for every defect class, so CORRECTION_VERSION_MISSING
    fires on base and head — invariant PIN."""
    observation = _den_observation(
        version={
            "immutable_record": True,
            "correction_version": value,
            "correction_of": None,
        }
    )
    verdict = _check_den(_den_request(), observation)
    assert "CORRECTION_VERSION_MISSING" in verdict.reasons, (
        value,
        verdict.reasons,
    )
    assert verdict.allowed is False, value


@pytest.mark.parametrize("value", WHITESPACE_VALUES + PADDED_VALUES + NON_STR_VALUES)
def test_r1_01_denominator_counter_kind(value):
    """Closed-set enum; the FAMILY TEXT RULE exempts closed-set enums from
    ``_text_present``. Set membership already refuses every defect class
    with COUNTER_KIND_UNKNOWN — invariant PIN."""
    request = _den_request(counter_kind=value)
    verdict = _check_den(request, _den_observation())
    assert "COUNTER_KIND_UNKNOWN" in verdict.reasons, (value, verdict.reasons)
    assert verdict.allowed is False, value


@pytest.mark.parametrize("value", WHITESPACE_VALUES + PADDED_VALUES + NON_STR_VALUES)
def test_r1_01_denominator_ads_ratio_source(value):
    """Single-sided check on ``ads_ratio_source``. Base ``_blank`` accepts
    whitespace / padded / non-str, so ADS_RATIO_UNSOURCED misses.
    FAMILY TEXT RULE refuses each as ABSENT."""
    request = _ads_request(ads_ratio_source=value)
    verdict = _check_den(request, _den_observation())
    assert "ADS_RATIO_UNSOURCED" in verdict.reasons, (value, verdict.reasons)
    assert verdict.allowed is False, value


# ---------------------------------------------------------------------------
# 02 — comparison guard
# issuer ids, role labels (closed set — PIN), currency codes,
# session-state labels (closed set — PIN).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("value", WHITESPACE_VALUES + PADDED_VALUES + NON_STR_VALUES)
def test_r1_02_comparison_issuer_id(value):
    """Both legs equal defect value — base ``!=`` is False and
    ``_present`` returns True, so ISSUER_MISMATCH misses. FAMILY TEXT
    RULE refuses."""
    left = _leg(issuer_id=value)
    right = _leg(issuer_id=value)
    verdict = _check_cmp(left, right, _fx())
    assert "ISSUER_MISMATCH" in verdict.reasons, (value, verdict.reasons)
    assert verdict.allowed is False, value


def test_r1_02_comparison_issuer_one_vs_true():
    """``1 == True`` is True at Python level, so base considers the two
    sides equal and emits no ISSUER_MISMATCH. FAMILY TEXT RULE refuses
    — non-text sides are ABSENT and never collide."""
    left = _leg(issuer_id=1)
    right = _leg(issuer_id=True)
    verdict = _check_cmp(left, right, _fx())
    assert "ISSUER_MISMATCH" in verdict.reasons, verdict.reasons
    assert verdict.allowed is False


@pytest.mark.parametrize("value", WHITESPACE_VALUES + PADDED_VALUES + NON_STR_VALUES)
def test_r1_02_comparison_instrument_role(value):
    """Closed-set enum; set membership already refuses every defect
    class with ROLE_UNKNOWN — invariant PIN."""
    left = _leg(instrument_role=value)
    verdict = _check_cmp(left, _leg(), _fx())
    assert "ROLE_UNKNOWN" in verdict.reasons, (value, verdict.reasons)
    assert verdict.allowed is False, value


@pytest.mark.parametrize("value", WHITESPACE_VALUES + PADDED_VALUES + NON_STR_VALUES)
def test_r1_02_comparison_currency_code(value):
    """Both legs equal defect value — base ``left_ccy == right_ccy`` is
    True (or both non-str) and returns ``[]`` short-circuiting the FX
    check, so FX_MISSING / CURRENCY_PAIR_MISMATCH miss. FAMILY TEXT
    RULE refuses each as ABSENT (no same-currency short-circuit)."""
    left = _leg(currency=value)
    right = _leg(currency=value)
    verdict = _check_cmp(left, right, None)
    assert (
        "FX_MISSING" in verdict.reasons
        or "CURRENCY_PAIR_MISMATCH" in verdict.reasons
    ), (value, verdict.reasons)
    assert verdict.allowed is False, value


@pytest.mark.parametrize("value", WHITESPACE_VALUES + PADDED_VALUES + NON_STR_VALUES)
def test_r1_02_comparison_session_state(value):
    """Closed-set enum; set membership already refuses every defect
    class with SESSION_STATE_UNKNOWN — invariant PIN."""
    left = _leg(session_state=value)
    verdict = _check_cmp(left, _leg(), _fx())
    assert "SESSION_STATE_UNKNOWN" in verdict.reasons, (value, verdict.reasons)
    assert verdict.allowed is False, value


# ---------------------------------------------------------------------------
# 03 — unhashable / exotic values never raise from a public guard
# function; they are ABSENT and refused.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("field", ["issuer_id", "share_count_ref", "observation_id"])
@pytest.mark.parametrize("value", UNHASHABLE_VALUES)
def test_r1_03_unhashable_denominator(field, value):
    """Unhashable values in any text field return a refusal and never
    raise from ``check_denominator``."""
    request = _den_request()
    observation = _den_observation()
    if field == "share_count_ref":
        request["share_count_ref"] = value
        observation["observation_id"] = value
    elif field == "observation_id":
        request["share_count_ref"] = value
        observation["observation_id"] = value
    elif field == "issuer_id":
        request["issuer_id"] = value
        observation["issuer_id"] = value
    verdict = _check_den(request, observation)
    assert verdict.allowed is False, (field, value, verdict.reasons)
    assert verdict.reasons, (field, value, verdict.reasons)
    # The unhashable case must not raise and must not yield allowed=True.


@pytest.mark.parametrize(
    "field",
    ["issuer_id", "instrument_role", "currency", "session_state"],
)
@pytest.mark.parametrize("value", UNHASHABLE_VALUES)
def test_r1_03_unhashable_comparison(field, value):
    """Unhashable values in any text field return a refusal and never
    raise from ``check_comparison``. Mismatched pair of unhashables to
    ensure set construction in the FX pair-check never fires."""
    left = _leg()
    right = _leg()
    if field == "issuer_id":
        left["issuer_id"] = value
        right["issuer_id"] = value
    elif field == "instrument_role":
        left["instrument_role"] = value
    elif field == "currency":
        left["currency"] = value
        right["currency"] = value
    elif field == "session_state":
        left["session_state"] = value
    verdict = _check_cmp(left, right, _fx())
    assert verdict.allowed is False, (field, value, verdict.reasons)
    assert verdict.reasons, (field, value, verdict.reasons)