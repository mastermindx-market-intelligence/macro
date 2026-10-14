"""A11 denominator-guard tests: unbound share counts are refused with named reasons.

SNI-local DRAFT contract tests. They consume owner-supplied opaque identity
strings (Stock Identity / Data OS) and Capital Structure observation
mappings; they never mint issuer or security ids, share counts, or ADS
ratios. HISTORICAL-DESCRIPTIVE only: rank_authority, gate_authority,
size_authority, signal_authority, escalation_authority and trade_authority
stay literal False. Fixtures are synthetic.

This module does not register, validate, or feed a ranker, gate, sizer,
signal, escalation, or trade path.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research" / "single_name_intelligence" / "common"))

from sni_denominator_guard import (  # noqa: E402
    AUTHORITY_FLAGS,
    COUNTER_KINDS,
    OWNER_SCHEMA,
    REASONS,
    DenominatorVerdict,
    check_denominator,
    refuse_nonfalse_authority,
)

MODULE_PATH = (
    ROOT
    / "research"
    / "single_name_intelligence"
    / "common"
    / "sni_denominator_guard.py"
)

FLAG_NAMES = (
    "rank_authority",
    "gate_authority",
    "size_authority",
    "signal_authority",
    "escalation_authority",
    "trade_authority",
)

AS_OF = "2026-08-20T12:00:00+00:00"
AVAILABLE_AT = "2026-08-20T11:00:00+00:00"
OBS_ID = "SYN-OBS-1"
ISSUER_ID = "SYN-ISSUER-1"
ADS_RATIO_SOURCE = "SYN-ADS-RATIO-OWNER-1"

US_TICKER_LITERALS = (
    "BABA",
    "TCEHY",
    "AAPL",
    "MSFT",
    "NVDA",
    "GOOGL",
    "AMZN",
    "META",
    "TSLA",
)


class _Omit:
    pass


_OMIT = _Omit()


def _base_request(**overrides):
    body = {
        "issuer_id": ISSUER_ID,
        "counter_kind": "ordinary",
        "share_count_ref": OBS_ID,
        "ads_ratio": None,
        "ads_ratio_source": None,
    }
    body.update(overrides)
    drop = [key for key, val in body.items() if val is _OMIT]
    for key in drop:
        del body[key]
    return body


def _ads_request(**overrides):
    body = {
        "counter_kind": "ads",
        "ads_ratio": 8,
        "ads_ratio_source": ADS_RATIO_SOURCE,
    }
    body.update(overrides)
    return _base_request(**body)


def _base_observation(**overrides):
    body = {
        "schema": OWNER_SCHEMA,
        "observation_id": OBS_ID,
        "logical_observation_id": "SYN-LOG-1",
        "fact_revision_id": "SYN-REV-1",
        "issuer_id": ISSUER_ID,
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
    }
    body.update(overrides)
    drop = [key for key, val in body.items() if val is _OMIT]
    for key in drop:
        del body[key]
    return body


def _check(request, observation, **kwargs):
    kwargs.setdefault("as_of", AS_OF)
    return check_denominator(request, observation, **kwargs)


def _assert_contract(verdict: DenominatorVerdict) -> None:
    for code in verdict.reasons:
        assert code in REASONS, (code, verdict.reasons)
    for name in FLAG_NAMES:
        assert verdict.authority_flags[name] is False
        assert verdict.authority_flags[name] is not True
    if verdict.allowed:
        assert verdict.reasons == ()
    else:
        assert verdict.allowed is False
        assert verdict.reasons


def _assert_refused(verdict: DenominatorVerdict, *codes: str) -> None:
    assert verdict.allowed is False, verdict
    got = set(verdict.reasons)
    for code in codes:
        assert code in got, (code, verdict.reasons)
    _assert_contract(verdict)


def _assert_allowed(verdict: DenominatorVerdict) -> None:
    assert verdict.allowed is True, verdict.reasons
    assert verdict.reasons == ()
    _assert_contract(verdict)


def _assert_only(verdict: DenominatorVerdict, code: str) -> None:
    _assert_refused(verdict, code)
    assert verdict.reasons == (code,), verdict.reasons


def _obs_version(correction_version):
    return _base_observation(
        version={
            "immutable_record": True,
            "correction_version": correction_version,
            "correction_of": None,
        }
    )


def _obs_available(available_at):
    return _base_observation(
        point_in_time={
            "system_available_at": AVAILABLE_AT,
            "source_retrieved_at": AVAILABLE_AT,
            "available_at": available_at,
        }
    )


def _obs_authority(**overrides):
    auth = {
        "is_context_only": True,
        "rank_authority": False,
        "sizing_authority": False,
        "entry_authority": False,
        "trade_authority": False,
        "prophet_authority": False,
    }
    auth.update(overrides)
    return _base_observation(authority=auth)


# ---------------------------------------------------------------------------
# Positive controls
# ---------------------------------------------------------------------------


def test_positive_ordinary():
    verdict = _check(_base_request(), _base_observation())
    _assert_allowed(verdict)
    assert verdict.owner_observation_id == OBS_ID
    assert verdict.correction_version == 1
    assert COUNTER_KINDS == ("ordinary", "ads")


def test_positive_ads():
    verdict = _check(_ads_request(), _base_observation())
    _assert_allowed(verdict)
    assert verdict.owner_observation_id == OBS_ID
    assert verdict.correction_version == 1


def test_positive_ordinary_with_matching_expected_version():
    verdict = _check(
        _base_request(),
        _base_observation(),
        expected_correction_version=1,
    )
    _assert_allowed(verdict)


# ---------------------------------------------------------------------------
# One single-flip test per REASONS entry
# ---------------------------------------------------------------------------


def test_reason_share_count_missing():
    verdict = _check(_base_request(), None)
    _assert_only(verdict, "SHARE_COUNT_MISSING")
    assert verdict.owner_observation_id is None
    assert verdict.correction_version is None


def test_reason_owner_schema_mismatch():
    verdict = _check(
        _base_request(),
        _base_observation(schema="capital_structure.share_count_observation.v0"),
    )
    _assert_only(verdict, "OWNER_SCHEMA_MISMATCH")


def test_reason_owner_ref_missing():
    verdict = _check(
        _base_request(),
        _base_observation(observation_id="SYN-OBS-OTHER"),
    )
    _assert_only(verdict, "OWNER_REF_MISSING")


def test_reason_correction_version_missing():
    verdict = _check(_base_request(), _obs_version(None))
    _assert_only(verdict, "CORRECTION_VERSION_MISSING")
    assert verdict.correction_version is None


def test_reason_correction_version_mismatch():
    verdict = _check(
        _base_request(),
        _base_observation(),
        expected_correction_version=2,
    )
    _assert_only(verdict, "CORRECTION_VERSION_MISMATCH")
    assert verdict.correction_version == 1


def test_reason_not_available_as_of():
    verdict = _check(
        _base_request(),
        _obs_available("2026-08-20T13:00:00+00:00"),
    )
    _assert_only(verdict, "NOT_AVAILABLE_AS_OF")


def test_reason_owner_authority_nonfalse():
    verdict = _check(_base_request(), _obs_authority(rank_authority=True))
    _assert_only(verdict, "OWNER_AUTHORITY_NONFALSE")


def test_reason_owner_disposition_not_accepted():
    verdict = _check(
        _base_request(),
        _base_observation(state={"disposition": "rejected", "reason": "SYN-REASON"}),
    )
    _assert_only(verdict, "OWNER_DISPOSITION_NOT_ACCEPTED")


def test_reason_issuer_mismatch():
    verdict = _check(_base_request(issuer_id="SYN-ISSUER-2"), _base_observation())
    _assert_only(verdict, "ISSUER_MISMATCH")


def test_reason_ads_ratio_missing():
    verdict = _check(_ads_request(ads_ratio=None), _base_observation())
    _assert_only(verdict, "ADS_RATIO_MISSING")


def test_reason_ads_ratio_unsourced():
    verdict = _check(_ads_request(ads_ratio_source=None), _base_observation())
    _assert_only(verdict, "ADS_RATIO_UNSOURCED")


def test_reason_ads_ratio_nonpositive():
    verdict = _check(_ads_request(ads_ratio=0), _base_observation())
    _assert_only(verdict, "ADS_RATIO_NONPOSITIVE")


def test_reason_counter_kind_unknown():
    verdict = _check(_base_request(counter_kind="warrant"), _base_observation())
    _assert_only(verdict, "COUNTER_KIND_UNKNOWN")


# ---------------------------------------------------------------------------
# Adversarial issuer identity (exact string; no case-fold/strip/normalise)
# ---------------------------------------------------------------------------


def test_issuer_trailing_space():
    verdict = _check(_base_request(issuer_id=ISSUER_ID + " "), _base_observation())
    _assert_only(verdict, "ISSUER_MISMATCH")


def test_issuer_case_mismatch():
    verdict = _check(_base_request(issuer_id="syn-issuer-1"), _base_observation())
    _assert_only(verdict, "ISSUER_MISMATCH")


def test_issuer_cyrillic_lookalike():
    latin = "SYN-ISSUERa"
    cyrillic = "SYN-ISSUER" + "\u0430"
    assert latin != cyrillic
    verdict = _check(
        _base_request(issuer_id=latin),
        _base_observation(issuer_id=cyrillic),
    )
    _assert_only(verdict, "ISSUER_MISMATCH")


# ---------------------------------------------------------------------------
# Adversarial correction_version
# ---------------------------------------------------------------------------


def test_correction_version_true():
    verdict = _check(_base_request(), _obs_version(True))
    _assert_only(verdict, "CORRECTION_VERSION_MISSING")


def test_correction_version_str_1():
    verdict = _check(_base_request(), _obs_version("1"))
    _assert_only(verdict, "CORRECTION_VERSION_MISSING")


def test_correction_version_zero():
    verdict = _check(_base_request(), _obs_version(0))
    _assert_only(verdict, "CORRECTION_VERSION_MISSING")


def test_correction_version_negative():
    verdict = _check(_base_request(), _obs_version(-1))
    _assert_only(verdict, "CORRECTION_VERSION_MISSING")


def test_correction_version_float():
    verdict = _check(_base_request(), _obs_version(1.0))
    _assert_only(verdict, "CORRECTION_VERSION_MISSING")


# ---------------------------------------------------------------------------
# Adversarial ads_ratio
# ---------------------------------------------------------------------------


def test_ads_ratio_true():
    verdict = _check(_ads_request(ads_ratio=True), _base_observation())
    _assert_only(verdict, "ADS_RATIO_NONPOSITIVE")


def test_ads_ratio_str_2():
    verdict = _check(_ads_request(ads_ratio="2"), _base_observation())
    _assert_only(verdict, "ADS_RATIO_NONPOSITIVE")


def test_ads_ratio_zero():
    verdict = _check(_ads_request(ads_ratio=0), _base_observation())
    _assert_only(verdict, "ADS_RATIO_NONPOSITIVE")


def test_ads_ratio_negative():
    verdict = _check(_ads_request(ads_ratio=-1), _base_observation())
    _assert_only(verdict, "ADS_RATIO_NONPOSITIVE")


def test_ads_ratio_nan():
    verdict = _check(_ads_request(ads_ratio=float("nan")), _base_observation())
    _assert_only(verdict, "ADS_RATIO_NONPOSITIVE")


def test_ads_ratio_inf():
    verdict = _check(_ads_request(ads_ratio=float("inf")), _base_observation())
    _assert_only(verdict, "ADS_RATIO_NONPOSITIVE")


# ---------------------------------------------------------------------------
# Availability: naive, one microsecond after, exactly equal
# ---------------------------------------------------------------------------


def test_available_at_naive():
    verdict = _check(_base_request(), _obs_available("2026-08-20T11:00:00"))
    _assert_only(verdict, "NOT_AVAILABLE_AS_OF")


def test_available_at_one_microsecond_after():
    verdict = _check(
        _base_request(),
        _obs_available("2026-08-20T12:00:00.000001+00:00"),
    )
    _assert_only(verdict, "NOT_AVAILABLE_AS_OF")


def test_available_at_exactly_equal_allowed():
    verdict = _check(_base_request(), _obs_available(AS_OF))
    _assert_allowed(verdict)


def test_available_at_missing():
    pit = {
        "system_available_at": AVAILABLE_AT,
        "source_retrieved_at": AVAILABLE_AT,
    }
    verdict = _check(_base_request(), _base_observation(point_in_time=pit))
    _assert_only(verdict, "NOT_AVAILABLE_AS_OF")


def test_as_of_naive_refuses():
    verdict = _check(
        _base_request(),
        _base_observation(),
        as_of="2026-08-20T12:00:00",
    )
    _assert_only(verdict, "NOT_AVAILABLE_AS_OF")


# ---------------------------------------------------------------------------
# Ordinary carrying a non-None ads_ratio (both branches)
# ---------------------------------------------------------------------------


def test_ordinary_ads_ratio_unsourced():
    verdict = _check(
        _base_request(ads_ratio=8, ads_ratio_source=None),
        _base_observation(),
    )
    _assert_only(verdict, "ADS_RATIO_UNSOURCED")


def test_ordinary_ads_ratio_nonpositive_when_sourced():
    verdict = _check(
        _base_request(ads_ratio=0, ads_ratio_source=ADS_RATIO_SOURCE),
        _base_observation(),
    )
    _assert_only(verdict, "ADS_RATIO_NONPOSITIVE")


def test_ordinary_ads_ratio_valid_when_sourced_allowed():
    verdict = _check(
        _base_request(ads_ratio=8, ads_ratio_source=ADS_RATIO_SOURCE),
        _base_observation(),
    )
    _assert_allowed(verdict)


# ---------------------------------------------------------------------------
# Authority
# ---------------------------------------------------------------------------


def test_observation_trade_authority_true():
    verdict = _check(_base_request(), _obs_authority(trade_authority=True))
    _assert_only(verdict, "OWNER_AUTHORITY_NONFALSE")


def test_is_context_only_not_true():
    verdict = _check(_base_request(), _obs_authority(is_context_only=False))
    _assert_only(verdict, "OWNER_AUTHORITY_NONFALSE")


def test_refuse_nonfalse_authority_raises():
    refuse_nonfalse_authority()
    refuse_nonfalse_authority(AUTHORITY_FLAGS)
    refuse_nonfalse_authority(dict(AUTHORITY_FLAGS))
    with pytest.raises(ValueError):
        refuse_nonfalse_authority({"rank_authority": True})
    with pytest.raises(ValueError):
        refuse_nonfalse_authority({"gate_authority": 0})
    with pytest.raises(ValueError):
        refuse_nonfalse_authority({"size_authority": None})
    with pytest.raises(ValueError):
        refuse_nonfalse_authority({"signal_authority": 0})
    with pytest.raises(ValueError):
        refuse_nonfalse_authority({"escalation_authority": None})
    with pytest.raises(ValueError):
        refuse_nonfalse_authority(
            {
                "rank_authority": False,
                "gate_authority": False,
                "size_authority": False,
                "signal_authority": False,
                "escalation_authority": False,
                "trade_authority": True,
            }
        )
    for name in FLAG_NAMES:
        one = dict(AUTHORITY_FLAGS)
        one[name] = True
        with pytest.raises(ValueError):
            refuse_nonfalse_authority(one)
        one[name] = 0
        with pytest.raises(ValueError):
            refuse_nonfalse_authority(one)
        one[name] = None
        with pytest.raises(ValueError):
            refuse_nonfalse_authority(one)


def test_authority_flags_immutable():
    with pytest.raises(TypeError):
        AUTHORITY_FLAGS["rank_authority"] = True
    with pytest.raises(TypeError):
        AUTHORITY_FLAGS["trade_authority"] = False
    for name in FLAG_NAMES:
        assert AUTHORITY_FLAGS[name] is False
        assert AUTHORITY_FLAGS[name] is not True
        assert AUTHORITY_FLAGS[name] is not 0  # noqa: F632
        assert AUTHORITY_FLAGS[name] is not None


def test_verdict_authority_flags_property():
    allowed = _check(_base_request(), _base_observation())
    refused = _check(_base_request(), None)
    for verdict in (allowed, refused):
        assert verdict.authority_flags is AUTHORITY_FLAGS
        for name in FLAG_NAMES:
            assert verdict.authority_flags[name] is False


# ---------------------------------------------------------------------------
# Static source contract
# ---------------------------------------------------------------------------


def test_module_source_reasons_and_no_tickers():
    source = MODULE_PATH.read_text(encoding="utf-8")
    for code in REASONS:
        assert code in source, code
    assert re.search(r"\b\d{4,5}\.HK\b", source) is None
    for ticker in US_TICKER_LITERALS:
        assert ticker not in source, ticker


def test_reasons_tuple_order_and_unique():
    assert REASONS == (
        "SHARE_COUNT_MISSING",
        "OWNER_SCHEMA_MISMATCH",
        "OWNER_REF_MISSING",
        "CORRECTION_VERSION_MISSING",
        "CORRECTION_VERSION_MISMATCH",
        "NOT_AVAILABLE_AS_OF",
        "OWNER_AUTHORITY_NONFALSE",
        "OWNER_DISPOSITION_NOT_ACCEPTED",
        "ISSUER_MISMATCH",
        "ADS_RATIO_MISSING",
        "ADS_RATIO_UNSOURCED",
        "ADS_RATIO_NONPOSITIVE",
        "COUNTER_KIND_UNKNOWN",
    )
    assert len(REASONS) == len(set(REASONS))
    assert OWNER_SCHEMA == "capital_structure.share_count_observation.v1"


# ---------------------------------------------------------------------------
# De-dup and REASONS order
# ---------------------------------------------------------------------------


def test_verdict_dedup_and_order():
    request = _base_request(issuer_id="", counter_kind="warrant")
    observation = _base_observation(schema="not-the-owner-schema")
    verdict = _check(request, observation)
    _assert_refused(
        verdict,
        "OWNER_SCHEMA_MISMATCH",
        "ISSUER_MISMATCH",
        "COUNTER_KIND_UNKNOWN",
    )
    assert verdict.reasons == (
        "OWNER_SCHEMA_MISMATCH",
        "ISSUER_MISMATCH",
        "COUNTER_KIND_UNKNOWN",
    )
    assert len(verdict.reasons) == len(set(verdict.reasons))


def test_observation_none_request_only_reasons():
    request = _base_request(issuer_id="", counter_kind="note")
    verdict = _check(request, None)
    _assert_refused(
        verdict,
        "SHARE_COUNT_MISSING",
        "ISSUER_MISMATCH",
        "COUNTER_KIND_UNKNOWN",
    )
    assert verdict.reasons == (
        "SHARE_COUNT_MISSING",
        "ISSUER_MISMATCH",
        "COUNTER_KIND_UNKNOWN",
    )
    assert len(verdict.reasons) == len(set(verdict.reasons))


def test_observation_none_does_not_emit_owner_schema_reasons():
    request = _base_request()
    verdict = _check(request, None)
    _assert_only(verdict, "SHARE_COUNT_MISSING")
    assert "OWNER_SCHEMA_MISMATCH" not in verdict.reasons
    assert "OWNER_REF_MISSING" not in verdict.reasons
    assert "CORRECTION_VERSION_MISSING" not in verdict.reasons
    assert "NOT_AVAILABLE_AS_OF" not in verdict.reasons
    assert "OWNER_AUTHORITY_NONFALSE" not in verdict.reasons
    assert "OWNER_DISPOSITION_NOT_ACCEPTED" not in verdict.reasons


def test_share_count_missing_blank_ref():
    verdict = _check(_base_request(share_count_ref=""), _base_observation())
    _assert_refused(verdict, "SHARE_COUNT_MISSING", "OWNER_REF_MISSING")
    assert verdict.reasons == ("SHARE_COUNT_MISSING", "OWNER_REF_MISSING")


def test_blank_request_issuer_with_observation():
    verdict = _check(_base_request(issuer_id=""), _base_observation())
    _assert_only(verdict, "ISSUER_MISMATCH")


def test_accumulate_ads_missing_and_unsourced():
    verdict = _check(
        _ads_request(ads_ratio=None, ads_ratio_source=None),
        _base_observation(),
    )
    assert verdict.reasons == ("ADS_RATIO_MISSING", "ADS_RATIO_UNSOURCED")


def test_owner_ref_missing_blank_observation_id():
    verdict = _check(
        _base_request(),
        _base_observation(observation_id=""),
    )
    _assert_only(verdict, "OWNER_REF_MISSING")
    assert verdict.owner_observation_id is None


def test_accepted_dispositions_override():
    obs = _base_observation(state={"disposition": "observed", "reason": "SYN"})
    refused = _check(_base_request(), obs)
    _assert_only(refused, "OWNER_DISPOSITION_NOT_ACCEPTED")
    allowed = _check(
        _base_request(),
        obs,
        accepted_dispositions=("observed",),
    )
    _assert_allowed(allowed)
