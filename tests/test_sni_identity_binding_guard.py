"""A03/A04 identity-binding-guard tests: listing binds are refused with named reasons.

SNI-local DRAFT contract tests. They consume owner-supplied opaque identity
strings (Stock Identity / Data OS) shaped like listing, security, and
issuer records; they never mint issuer or security ids. HISTORICAL-DESCRIPTIVE
only: rank_authority, gate_authority, size_authority, signal_authority,
escalation_authority and trade_authority stay literal False. Fixtures are
synthetic.

This module does not register, validate, or feed a ranker, gate, sizer,
signal, escalation, or trade path.

Sibling: tests/test_sni_identity_refusals.py (A03/A04 profile/identity walk).
This file covers the SNI-local binding-guard refusal contract and does not
duplicate those cases.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research" / "single_name_intelligence" / "common"))

from sni_identity_binding_guard import (  # noqa: E402
    AUTHORITY_FLAGS,
    REASONS,
    IdentityBindingVerdict,
    bind_identity,
    refuse_nonfalse_authority,
)

MODULE_PATH = (
    ROOT
    / "research"
    / "single_name_intelligence"
    / "common"
    / "sni_identity_binding_guard.py"
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
LISTING_ID = "SYN-LIST-1"
SECURITY_ID = "SYN-SEC-1"
ISSUER_ID = "SYN-ISS-1"
CURRENCY = "CCC"
DISPLAY_CODE = "QZX"
DISPLAY_NAME = "Synthetic Holding One"
OWNER_LIST = "SYN-OWNER-LIST-1"
OWNER_SEC = "SYN-OWNER-SEC-1"
OWNER_ISS = "SYN-OWNER-ISS-1"

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

_UNSET = object()


class _Omit:
    pass


_OMIT = _Omit()


def _drop_omit(body: dict) -> dict:
    drop = [key for key, val in body.items() if val is _OMIT]
    for key in drop:
        del body[key]
    return body


def _base_request(**overrides):
    body = {
        "listing_id": LISTING_ID,
        "issuer_id": ISSUER_ID,
        "currency": CURRENCY,
        "operation_needs_issuer": True,
    }
    body.update(overrides)
    return _drop_omit(body)


def _null_request(**overrides):
    body = {
        "issuer_id": None,
        "operation_needs_issuer": False,
    }
    body.update(overrides)
    return _base_request(**body)


def _base_listing(**overrides):
    body = {
        "listing_id": LISTING_ID,
        "security_id": SECURITY_ID,
        "currency": CURRENCY,
        "owner_ref": OWNER_LIST,
        "available_at": AVAILABLE_AT,
        "display_code": DISPLAY_CODE,
        "display_name": DISPLAY_NAME,
    }
    body.update(overrides)
    return _drop_omit(body)


def _base_security(**overrides):
    body = {
        "security_id": SECURITY_ID,
        "issuer_id": ISSUER_ID,
        "owner_ref": OWNER_SEC,
        "available_at": AVAILABLE_AT,
    }
    body.update(overrides)
    return _drop_omit(body)


def _null_security(**overrides):
    return _base_security(issuer_id=None, **overrides)


def _base_issuer(**overrides):
    body = {
        "issuer_id": ISSUER_ID,
        "owner_ref": OWNER_ISS,
        "available_at": AVAILABLE_AT,
    }
    body.update(overrides)
    return _drop_omit(body)


def _bind(
    *,
    request=_UNSET,
    listing=_UNSET,
    security=_UNSET,
    issuer=_UNSET,
    as_of=AS_OF,
):
    if request is _UNSET:
        request = _base_request()
    if listing is _UNSET:
        listing = _base_listing()
    if security is _UNSET:
        security = _base_security()
    if issuer is _UNSET:
        issuer = _base_issuer()
    return bind_identity(
        request,
        listing=listing,
        security=security,
        issuer=issuer,
        as_of=as_of,
    )


def _assert_contract(verdict: IdentityBindingVerdict) -> None:
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


def _assert_refused(verdict: IdentityBindingVerdict, *codes: str) -> None:
    assert verdict.allowed is False, verdict
    got = set(verdict.reasons)
    for code in codes:
        assert code in got, (code, verdict.reasons)
    _assert_contract(verdict)


def _assert_allowed(verdict: IdentityBindingVerdict) -> None:
    assert verdict.allowed is True, verdict.reasons
    assert verdict.reasons == ()
    _assert_contract(verdict)


def _assert_only(verdict: IdentityBindingVerdict, code: str) -> None:
    _assert_refused(verdict, code)
    assert verdict.reasons == (code,), verdict.reasons


# ---------------------------------------------------------------------------
# Positive controls
# ---------------------------------------------------------------------------


def test_a03g_positive_with_issuer():
    verdict = _bind()
    _assert_allowed(verdict)
    assert verdict.listing_id == LISTING_ID
    assert verdict.security_id == SECURITY_ID
    assert verdict.issuer_id == ISSUER_ID


def test_a03g_positive_null_issuer_when_not_needed():
    verdict = _bind(
        request=_null_request(),
        security=_null_security(),
        issuer=None,
    )
    _assert_allowed(verdict)
    assert verdict.listing_id == LISTING_ID
    assert verdict.security_id == SECURITY_ID
    assert verdict.issuer_id is None


def test_a03g_positive_available_at_exactly_equal():
    verdict = _bind(
        listing=_base_listing(available_at=AS_OF),
        security=_base_security(available_at=AS_OF),
        issuer=_base_issuer(available_at=AS_OF),
    )
    _assert_allowed(verdict)


# ---------------------------------------------------------------------------
# One single-flip test per REASONS entry
# ---------------------------------------------------------------------------


def test_a03g_reason_null_issuer_refused():
    verdict = _bind(
        request=_null_request(operation_needs_issuer=True),
        security=_null_security(),
        issuer=None,
    )
    _assert_only(verdict, "NULL_ISSUER_REFUSED")
    assert verdict.issuer_id is None


def test_a03g_reason_listing_record_missing():
    verdict = _bind(listing=None)
    _assert_only(verdict, "LISTING_RECORD_MISSING")
    assert verdict.listing_id is None


def test_a03g_reason_security_record_missing():
    verdict = _bind(security=None)
    _assert_only(verdict, "SECURITY_RECORD_MISSING")
    assert verdict.security_id is None
    assert verdict.issuer_id is None


def test_a03g_reason_issuer_record_missing():
    verdict = _bind(issuer=None)
    _assert_only(verdict, "ISSUER_RECORD_MISSING")
    assert verdict.issuer_id == ISSUER_ID


def test_a03g_reason_owner_ref_missing():
    verdict = _bind(listing=_base_listing(owner_ref=""))
    _assert_only(verdict, "OWNER_REF_MISSING")


def test_a03g_reason_listing_id_mismatch():
    verdict = _bind(request=_base_request(listing_id="SYN-LIST-2"))
    _assert_only(verdict, "LISTING_ID_MISMATCH")


def test_a03g_reason_listing_security_mismatch():
    verdict = _bind(listing=_base_listing(security_id="SYN-SEC-2"))
    _assert_only(verdict, "LISTING_SECURITY_MISMATCH")


def test_a03g_reason_security_issuer_mismatch():
    verdict = _bind(issuer=_base_issuer(issuer_id="SYN-ISS-2"))
    _assert_only(verdict, "SECURITY_ISSUER_MISMATCH")


def test_a03g_reason_request_issuer_mismatch():
    verdict = _bind(request=_base_request(issuer_id="SYN-ISS-2"))
    _assert_only(verdict, "REQUEST_ISSUER_MISMATCH")


def test_a03g_reason_currency_mismatch():
    verdict = _bind(request=_base_request(currency="DDD"))
    _assert_only(verdict, "CURRENCY_MISMATCH")


def test_a03g_reason_not_available_as_of():
    verdict = _bind(
        listing=_base_listing(available_at="2026-08-20T13:00:00+00:00"),
    )
    _assert_only(verdict, "NOT_AVAILABLE_AS_OF")


def test_a03g_reason_id_looks_derived():
    verdict = _bind(listing=_base_listing(display_code="LIST"))
    _assert_only(verdict, "ID_LOOKS_DERIVED")


# ---------------------------------------------------------------------------
# Null issuer stays null; never back-filled
# ---------------------------------------------------------------------------


def test_a03g_null_issuer_never_backfilled_from_request():
    verdict = _bind(
        request=_base_request(issuer_id=ISSUER_ID, operation_needs_issuer=True),
        security=_null_security(),
        issuer=None,
    )
    _assert_refused(verdict, "NULL_ISSUER_REFUSED")
    assert verdict.issuer_id is None
    assert "REQUEST_ISSUER_MISMATCH" in verdict.reasons


def test_a03g_null_issuer_omitted_needs_flag_refuses():
    verdict = _bind(
        request=_null_request(operation_needs_issuer=_OMIT),
        security=_null_security(),
        issuer=None,
    )
    _assert_only(verdict, "NULL_ISSUER_REFUSED")
    assert verdict.issuer_id is None


def test_a03g_null_issuer_zero_needs_flag_refuses():
    verdict = _bind(
        request=_null_request(operation_needs_issuer=0),
        security=_null_security(),
        issuer=None,
    )
    _assert_only(verdict, "NULL_ISSUER_REFUSED")
    assert verdict.issuer_id is None


# ---------------------------------------------------------------------------
# Padding / alias / currency variants
# ---------------------------------------------------------------------------


def test_a03g_zero_padded_listing_id_refused():
    verdict = _bind(
        request=_base_request(listing_id="0700"),
        listing=_base_listing(listing_id="700"),
    )
    _assert_only(verdict, "LISTING_ID_MISMATCH")


def test_a03g_zero_padded_listing_id_triple_refused():
    verdict = _bind(
        request=_base_request(listing_id="00700"),
        listing=_base_listing(listing_id="0700"),
    )
    _assert_only(verdict, "LISTING_ID_MISMATCH")


def test_a03g_display_code_alias_as_listing_id_refused():
    verdict = _bind(request=_base_request(listing_id=DISPLAY_CODE))
    _assert_refused(verdict, "LISTING_ID_MISMATCH")
    assert verdict.allowed is False
    assert "LISTING_ID_MISMATCH" in verdict.reasons


def test_a03g_currency_case_mismatch():
    verdict = _bind(request=_base_request(currency="ccc"))
    _assert_only(verdict, "CURRENCY_MISMATCH")


def test_a03g_currency_trailing_space_mismatch():
    verdict = _bind(request=_base_request(currency=CURRENCY + " "))
    _assert_only(verdict, "CURRENCY_MISMATCH")


def test_a03g_currency_leading_space_mismatch():
    verdict = _bind(request=_base_request(currency=" " + CURRENCY))
    _assert_only(verdict, "CURRENCY_MISMATCH")


# ---------------------------------------------------------------------------
# ID_LOOKS_DERIVED extras
# ---------------------------------------------------------------------------


def test_a03g_id_looks_derived_id_embeds_display_code():
    embedded = "SYN-" + DISPLAY_CODE + "-1"
    verdict = _bind(
        request=_base_request(listing_id=embedded),
        listing=_base_listing(listing_id=embedded),
    )
    _assert_only(verdict, "ID_LOOKS_DERIVED")


def test_a03g_id_looks_derived_skips_two_char_display_code():
    verdict = _bind(listing=_base_listing(display_code="SY"))
    _assert_allowed(verdict)


def test_a03g_id_looks_derived_display_name():
    verdict = _bind(listing=_base_listing(display_name="SEC"))
    _assert_only(verdict, "ID_LOOKS_DERIVED")


# ---------------------------------------------------------------------------
# Availability: naive, missing, one microsecond after
# ---------------------------------------------------------------------------


def test_a03g_available_at_naive():
    verdict = _bind(listing=_base_listing(available_at="2026-08-20T11:00:00"))
    _assert_only(verdict, "NOT_AVAILABLE_AS_OF")


def test_a03g_available_at_missing():
    verdict = _bind(listing=_base_listing(available_at=_OMIT))
    _assert_only(verdict, "NOT_AVAILABLE_AS_OF")


def test_a03g_available_at_one_microsecond_after():
    verdict = _bind(
        listing=_base_listing(available_at="2026-08-20T12:00:00.000001+00:00"),
    )
    _assert_only(verdict, "NOT_AVAILABLE_AS_OF")


def test_a03g_as_of_naive_refuses():
    verdict = _bind(as_of="2026-08-20T12:00:00")
    _assert_only(verdict, "NOT_AVAILABLE_AS_OF")


def test_a03g_security_available_at_naive():
    verdict = _bind(security=_base_security(available_at="2026-08-20T11:00:00"))
    _assert_only(verdict, "NOT_AVAILABLE_AS_OF")


# ---------------------------------------------------------------------------
# Owner-ref on other present records
# ---------------------------------------------------------------------------


def test_a03g_owner_ref_missing_on_security():
    verdict = _bind(security=_base_security(owner_ref=""))
    _assert_only(verdict, "OWNER_REF_MISSING")


def test_a03g_owner_ref_missing_on_issuer():
    verdict = _bind(issuer=_base_issuer(owner_ref=None))
    _assert_only(verdict, "OWNER_REF_MISSING")


# ---------------------------------------------------------------------------
# Authority
# ---------------------------------------------------------------------------


def test_a03g_refuse_nonfalse_authority_raises():
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
        refuse_nonfalse_authority({"signal_authority": ""})
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
        one[name] = ""
        with pytest.raises(ValueError):
            refuse_nonfalse_authority(one)


def test_a03g_authority_flags_immutable():
    with pytest.raises(TypeError):
        AUTHORITY_FLAGS["rank_authority"] = True
    with pytest.raises(TypeError):
        AUTHORITY_FLAGS["trade_authority"] = False
    for name in FLAG_NAMES:
        assert AUTHORITY_FLAGS[name] is False
        assert AUTHORITY_FLAGS[name] is not True
        assert AUTHORITY_FLAGS[name] is not 0  # noqa: F632
        assert AUTHORITY_FLAGS[name] is not None


def test_a03g_verdict_authority_flags_property():
    allowed = _bind()
    refused = _bind(listing=None)
    for verdict in (allowed, refused):
        assert verdict.authority_flags is AUTHORITY_FLAGS
        for name in FLAG_NAMES:
            assert verdict.authority_flags[name] is False


# ---------------------------------------------------------------------------
# Static source contract
# ---------------------------------------------------------------------------


def test_a03g_module_source_reasons_and_no_tickers():
    source = MODULE_PATH.read_text(encoding="utf-8")
    for code in REASONS:
        assert code in source, code
    assert re.search(r"\b\d{4,5}\.HK\b", source) is None
    for ticker in US_TICKER_LITERALS:
        assert ticker not in source, ticker
    for needle in (
        "datetime.now",
        "utcnow",
        "date.today",
        "time.time",
        "open(",
    ):
        assert needle not in source, needle


def test_a03g_reasons_tuple_order_and_unique():
    assert REASONS == (
        "NULL_ISSUER_REFUSED",
        "LISTING_RECORD_MISSING",
        "SECURITY_RECORD_MISSING",
        "ISSUER_RECORD_MISSING",
        "OWNER_REF_MISSING",
        "LISTING_ID_MISMATCH",
        "LISTING_SECURITY_MISMATCH",
        "SECURITY_ISSUER_MISMATCH",
        "REQUEST_ISSUER_MISMATCH",
        "CURRENCY_MISMATCH",
        "NOT_AVAILABLE_AS_OF",
        "ID_LOOKS_DERIVED",
    )
    assert len(REASONS) == len(set(REASONS))


# ---------------------------------------------------------------------------
# De-dup and REASONS order
# ---------------------------------------------------------------------------


def test_a03g_verdict_dedup_and_order():
    verdict = _bind(
        request=_base_request(listing_id="SYN-LIST-2", currency="DDD"),
        listing=_base_listing(owner_ref=""),
        security=_base_security(owner_ref=""),
    )
    _assert_refused(
        verdict,
        "OWNER_REF_MISSING",
        "LISTING_ID_MISMATCH",
        "CURRENCY_MISMATCH",
    )
    assert verdict.reasons == (
        "OWNER_REF_MISSING",
        "LISTING_ID_MISMATCH",
        "CURRENCY_MISMATCH",
    )
    assert len(verdict.reasons) == len(set(verdict.reasons))


# ---------------------------------------------------------------------------
# Adversarial id cases (exact string; no case-fold/strip/normalise)
# ---------------------------------------------------------------------------


def test_a03g_listing_id_trailing_space():
    verdict = _bind(request=_base_request(listing_id=LISTING_ID + " "))
    _assert_only(verdict, "LISTING_ID_MISMATCH")


def test_a03g_listing_id_case_mismatch():
    verdict = _bind(request=_base_request(listing_id="syn-list-1"))
    _assert_only(verdict, "LISTING_ID_MISMATCH")


def test_a03g_listing_id_cyrillic_lookalike():
    latin = "SYN-LISTa"
    cyrillic = "SYN-LIST" + "\u0430"
    assert latin != cyrillic
    verdict = _bind(
        request=_base_request(listing_id=latin),
        listing=_base_listing(listing_id=cyrillic),
    )
    _assert_only(verdict, "LISTING_ID_MISMATCH")
