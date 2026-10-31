"""A33 release-evidence-guard tests: absent or synthetic pages are refused.

SNI-local DRAFT contract tests. They consume owner-supplied opaque identity
strings (Stock Identity / Data OS) and A0/P1 reference page evidence-slot
mappings; they never mint issuer or security ids or evidence refs.
HISTORICAL-DESCRIPTIVE only: rank_authority, gate_authority,
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

from sni_release_evidence_guard import (  # noqa: E402
    AUTHORITY_FLAGS,
    PROVENANCES,
    REASONS,
    SLOT_STATES,
    ReleaseVerdict,
    check_release,
    refuse_nonfalse_authority,
)

MODULE_PATH = (
    ROOT
    / "research"
    / "single_name_intelligence"
    / "common"
    / "sni_release_evidence_guard.py"
)

FLAG_NAMES = (
    "rank_authority",
    "gate_authority",
    "size_authority",
    "signal_authority",
    "escalation_authority",
    "trade_authority",
)

PAGE_ID = "SYN-PAGE-1"
SLOT_IDENTITY = "SYN-SLOT-IDENTITY"
SLOT_EVENT = "SYN-SLOT-EVENT"
SLOT_FINANCIAL = "SYN-SLOT-FINANCIAL"

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


def _slot(slot_id=SLOT_IDENTITY, **overrides):
    body = {
        "slot_id": slot_id,
        "state": "present",
        "provenance": "owner",
        "evidence_ref": "SYN-REF-" + str(slot_id),
        "required": True,
    }
    body.update(overrides)
    drop = [key for key, val in body.items() if val is _OMIT]
    for key in drop:
        del body[key]
    return body


def _positive_page(**overrides):
    body = {
        "page_id": PAGE_ID,
        "slots": (
            _slot(SLOT_IDENTITY),
            _slot(SLOT_EVENT),
            _slot(SLOT_FINANCIAL),
        ),
    }
    body.update(overrides)
    drop = [key for key, val in body.items() if val is _OMIT]
    for key in drop:
        del body[key]
    return body


def _flip_slot(page, index, **slot_overrides):
    slots = [dict(item) for item in page["slots"]]
    slot = dict(slots[index])
    slot.update(slot_overrides)
    drop = [key for key, val in slot.items() if val is _OMIT]
    for key in drop:
        del slot[key]
    slots[index] = slot
    out = dict(page)
    out["slots"] = tuple(slots)
    return out


def _map_slots(page, **slot_overrides):
    slots = []
    for item in page["slots"]:
        slot = dict(item)
        slot.update(slot_overrides)
        drop = [key for key, val in slot.items() if val is _OMIT]
        for key in drop:
            del slot[key]
        slots.append(slot)
    out = dict(page)
    out["slots"] = tuple(slots)
    return out


def _assert_contract(verdict: ReleaseVerdict) -> None:
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


def _assert_refused(verdict: ReleaseVerdict, *codes: str) -> None:
    assert verdict.allowed is False, verdict
    got = set(verdict.reasons)
    for code in codes:
        assert code in got, (code, verdict.reasons)
    _assert_contract(verdict)


def _assert_allowed(verdict: ReleaseVerdict) -> None:
    assert verdict.allowed is True, verdict.reasons
    assert verdict.reasons == ()
    _assert_contract(verdict)


def _assert_only(verdict: ReleaseVerdict, code: str) -> None:
    _assert_refused(verdict, code)
    assert verdict.reasons == (code,), verdict.reasons


# ---------------------------------------------------------------------------
# Positive controls
# ---------------------------------------------------------------------------


def test_a33_positive_three_owner_slots():
    verdict = check_release(_positive_page())
    _assert_allowed(verdict)
    assert verdict.present_owner_slots == (
        SLOT_IDENTITY,
        SLOT_EVENT,
        SLOT_FINANCIAL,
    )
    assert SLOT_STATES == ("present", "absent", "stale", "gated")
    assert PROVENANCES == (
        "owner",
        "synthetic_fixture",
        "test_double",
        "unknown",
    )


def test_a33_positive_required_false_absent_with_owner_present():
    page = _flip_slot(
        _positive_page(),
        2,
        state="absent",
        required=False,
        evidence_ref=_OMIT,
    )
    verdict = check_release(page)
    _assert_allowed(verdict)
    assert verdict.present_owner_slots == (SLOT_IDENTITY, SLOT_EVENT)


# ---------------------------------------------------------------------------
# One single-flip test per REASONS entry
# ---------------------------------------------------------------------------


def test_a33_reason_page_id_missing():
    verdict = check_release(_positive_page(page_id=""))
    _assert_only(verdict, "PAGE_ID_MISSING")
    assert verdict.present_owner_slots == (
        SLOT_IDENTITY,
        SLOT_EVENT,
        SLOT_FINANCIAL,
    )


def test_a33_reason_no_slots():
    verdict = check_release(_positive_page(slots=()))
    _assert_refused(verdict, "NO_SLOTS")
    assert "NO_SLOTS" in verdict.reasons
    assert verdict.present_owner_slots == ()


def test_a33_reason_duplicate_slot():
    page = _flip_slot(_positive_page(), 1, slot_id=SLOT_IDENTITY)
    verdict = check_release(page)
    _assert_only(verdict, "DUPLICATE_SLOT")


def test_a33_reason_slot_state_unknown():
    page = _flip_slot(_positive_page(), 0, state="not-a-state")
    verdict = check_release(page)
    _assert_refused(verdict, "SLOT_STATE_UNKNOWN")
    assert "SLOT_STATE_UNKNOWN" in verdict.reasons


def test_a33_reason_provenance_unknown():
    page = _flip_slot(_positive_page(), 0, provenance="unknown")
    verdict = check_release(page)
    _assert_only(verdict, "PROVENANCE_UNKNOWN")
    assert verdict.present_owner_slots == (SLOT_EVENT, SLOT_FINANCIAL)


def test_a33_reason_present_without_ref():
    page = _flip_slot(_positive_page(), 0, evidence_ref="")
    verdict = check_release(page)
    _assert_only(verdict, "PRESENT_WITHOUT_REF")


def test_a33_reason_synthetic_evidence():
    page = _flip_slot(_positive_page(), 0, provenance="synthetic_fixture")
    verdict = check_release(page)
    _assert_only(verdict, "SYNTHETIC_EVIDENCE")
    assert verdict.present_owner_slots == (SLOT_EVENT, SLOT_FINANCIAL)


def test_a33_reason_all_evidence_absent():
    page = _map_slots(_positive_page(), state="absent")
    verdict = check_release(page)
    _assert_refused(verdict, "ALL_EVIDENCE_ABSENT")
    assert "ALL_EVIDENCE_ABSENT" in verdict.reasons
    assert verdict.present_owner_slots == ()


def test_a33_reason_required_slot_not_present():
    page = _flip_slot(_positive_page(), 0, state="absent")
    verdict = check_release(page)
    _assert_only(verdict, "REQUIRED_SLOT_NOT_PRESENT")
    assert verdict.present_owner_slots == (SLOT_EVENT, SLOT_FINANCIAL)


# ---------------------------------------------------------------------------
# All-absent, all-gated, only-present synthetic
# ---------------------------------------------------------------------------


def test_a33_all_absent_page():
    page = _map_slots(_positive_page(), state="absent")
    verdict = check_release(page)
    _assert_refused(verdict, "ALL_EVIDENCE_ABSENT")
    assert verdict.present_owner_slots == ()


def test_a33_all_gated_page():
    page = _map_slots(_positive_page(), state="gated")
    verdict = check_release(page)
    _assert_refused(verdict, "ALL_EVIDENCE_ABSENT")
    assert verdict.present_owner_slots == ()


def test_a33_only_present_synthetic_fixture():
    page = {
        "page_id": PAGE_ID,
        "slots": (
            _slot(
                SLOT_IDENTITY,
                provenance="synthetic_fixture",
                evidence_ref="SYN-FIXTURE-REF-1",
            ),
        ),
    }
    verdict = check_release(page)
    _assert_refused(verdict, "SYNTHETIC_EVIDENCE", "ALL_EVIDENCE_ABSENT")
    assert verdict.reasons == ("SYNTHETIC_EVIDENCE", "ALL_EVIDENCE_ABSENT")
    assert verdict.present_owner_slots == ()


def test_a33_required_false_on_absent_allowed():
    page = _flip_slot(
        _positive_page(),
        2,
        state="absent",
        required=False,
    )
    verdict = check_release(page)
    _assert_allowed(verdict)


def test_a33_required_zero_treated_as_required():
    page = _flip_slot(_positive_page(), 0, state="absent", required=0)
    verdict = check_release(page)
    _assert_only(verdict, "REQUIRED_SLOT_NOT_PRESENT")


def test_a33_required_none_treated_as_required():
    page = _flip_slot(_positive_page(), 0, state="absent", required=None)
    verdict = check_release(page)
    _assert_only(verdict, "REQUIRED_SLOT_NOT_PRESENT")


def test_a33_required_key_absent_defaults_true():
    page = _flip_slot(_positive_page(), 0, state="stale", required=_OMIT)
    verdict = check_release(page)
    _assert_only(verdict, "REQUIRED_SLOT_NOT_PRESENT")


def test_a33_test_double_synthetic_evidence():
    page = _flip_slot(_positive_page(), 1, provenance="test_double")
    verdict = check_release(page)
    _assert_only(verdict, "SYNTHETIC_EVIDENCE")


def test_a33_provenance_not_in_set():
    page = _flip_slot(_positive_page(), 0, provenance="invented")
    verdict = check_release(page)
    _assert_only(verdict, "PROVENANCE_UNKNOWN")


def test_a33_unknown_provenance_on_absent_ok():
    page = _flip_slot(
        _positive_page(),
        2,
        state="absent",
        provenance="unknown",
        required=False,
        evidence_ref=_OMIT,
    )
    verdict = check_release(page)
    _assert_allowed(verdict)


def test_a33_present_owner_slots_input_order():
    page = {
        "page_id": PAGE_ID,
        "slots": (
            _slot(SLOT_EVENT, provenance="synthetic_fixture"),
            _slot(SLOT_IDENTITY),
            _slot(SLOT_FINANCIAL, state="gated", required=False),
            _slot("SYN-SLOT-EVAL"),
        ),
    }
    verdict = check_release(page)
    _assert_refused(verdict, "SYNTHETIC_EVIDENCE")
    assert verdict.present_owner_slots == (SLOT_IDENTITY, "SYN-SLOT-EVAL")


def test_a33_none_page_id_missing():
    verdict = check_release(_positive_page(page_id=None))
    _assert_only(verdict, "PAGE_ID_MISSING")


def test_a33_none_evidence_ref():
    page = _flip_slot(_positive_page(), 0, evidence_ref=None)
    verdict = check_release(page)
    _assert_only(verdict, "PRESENT_WITHOUT_REF")


def test_a33_all_evidence_absent_optional_absent_only():
    page = _map_slots(_positive_page(), state="absent", required=False)
    verdict = check_release(page)
    _assert_only(verdict, "ALL_EVIDENCE_ABSENT")


# ---------------------------------------------------------------------------
# Authority
# ---------------------------------------------------------------------------


def test_a33_refuse_nonfalse_authority():
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


def test_a33_authority_flags_immutable():
    with pytest.raises(TypeError):
        AUTHORITY_FLAGS["rank_authority"] = True
    with pytest.raises(TypeError):
        AUTHORITY_FLAGS["trade_authority"] = False
    for name in FLAG_NAMES:
        assert AUTHORITY_FLAGS[name] is False
        assert AUTHORITY_FLAGS[name] is not True
        assert AUTHORITY_FLAGS[name] is not 0  # noqa: F632
        assert AUTHORITY_FLAGS[name] is not None


def test_a33_verdict_authority_flags_property():
    allowed = check_release(_positive_page())
    refused = check_release(_positive_page(page_id=""))
    for verdict in (allowed, refused):
        assert verdict.authority_flags is AUTHORITY_FLAGS
        for name in FLAG_NAMES:
            assert verdict.authority_flags[name] is False


# ---------------------------------------------------------------------------
# Static source contract
# ---------------------------------------------------------------------------


def test_a33_module_source_contract():
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


def test_a33_reasons_tuple_order_and_unique():
    assert REASONS == (
        "PAGE_ID_MISSING",
        "NO_SLOTS",
        "DUPLICATE_SLOT",
        "SLOT_STATE_UNKNOWN",
        "PROVENANCE_UNKNOWN",
        "PRESENT_WITHOUT_REF",
        "SYNTHETIC_EVIDENCE",
        "ALL_EVIDENCE_ABSENT",
        "REQUIRED_SLOT_NOT_PRESENT",
    )
    assert len(REASONS) == len(set(REASONS))
    assert SLOT_STATES == ("present", "absent", "stale", "gated")
    assert PROVENANCES == (
        "owner",
        "synthetic_fixture",
        "test_double",
        "unknown",
    )


# ---------------------------------------------------------------------------
# De-dup and REASONS order
# ---------------------------------------------------------------------------


def test_a33_verdict_dedup_and_order():
    page = {
        "page_id": "",
        "slots": (
            _slot(
                SLOT_IDENTITY,
                state="present",
                provenance="synthetic_fixture",
                evidence_ref="",
            ),
            _slot(
                SLOT_IDENTITY,
                state="present",
                provenance="synthetic_fixture",
                evidence_ref="",
            ),
        ),
    }
    verdict = check_release(page)
    _assert_refused(
        verdict,
        "PAGE_ID_MISSING",
        "DUPLICATE_SLOT",
        "PRESENT_WITHOUT_REF",
        "SYNTHETIC_EVIDENCE",
        "ALL_EVIDENCE_ABSENT",
    )
    assert verdict.reasons == (
        "PAGE_ID_MISSING",
        "DUPLICATE_SLOT",
        "PRESENT_WITHOUT_REF",
        "SYNTHETIC_EVIDENCE",
        "ALL_EVIDENCE_ABSENT",
    )
    assert len(verdict.reasons) == len(set(verdict.reasons))


def test_a33_empty_page_three_reasons_order():
    verdict = check_release({"page_id": "", "slots": ()})
    _assert_refused(verdict, "PAGE_ID_MISSING", "NO_SLOTS", "ALL_EVIDENCE_ABSENT")
    assert verdict.reasons == (
        "PAGE_ID_MISSING",
        "NO_SLOTS",
        "ALL_EVIDENCE_ABSENT",
    )
    assert len(verdict.reasons) == len(set(verdict.reasons))


# ---------------------------------------------------------------------------
# Adversarial page_id / slot_id (exact string; no case-fold/strip/normalise)
# ---------------------------------------------------------------------------


def test_a33_t6_slot_id_trailing_space():
    original = SLOT_IDENTITY
    variant = original + " "
    assert original != variant
    page = _flip_slot(_positive_page(), 1, slot_id=variant)
    verdict = check_release(page)
    _assert_allowed(verdict)
    assert verdict.present_owner_slots == (
        SLOT_IDENTITY,
        variant,
        SLOT_FINANCIAL,
    )
    dup = _flip_slot(_positive_page(), 1, slot_id=original)
    _assert_only(check_release(dup), "DUPLICATE_SLOT")


def test_a33_t6_slot_id_case_change():
    original = SLOT_IDENTITY
    variant = "syn-slot-identity"
    assert original != variant
    page = _flip_slot(_positive_page(), 1, slot_id=variant)
    verdict = check_release(page)
    _assert_allowed(verdict)
    assert variant in verdict.present_owner_slots
    assert original in verdict.present_owner_slots


def test_a33_t6_slot_id_cyrillic_lookalike():
    latin = "SYN-SLOTa"
    cyrillic = "SYN-SLOT" + "\u0430"
    assert latin != cyrillic
    page = {
        "page_id": PAGE_ID,
        "slots": (
            _slot(latin),
            _slot(cyrillic),
            _slot(SLOT_FINANCIAL),
        ),
    }
    verdict = check_release(page)
    _assert_allowed(verdict)
    assert verdict.present_owner_slots == (latin, cyrillic, SLOT_FINANCIAL)
    dup = {
        "page_id": PAGE_ID,
        "slots": (
            _slot(latin),
            _slot(latin),
            _slot(SLOT_FINANCIAL),
        ),
    }
    _assert_only(check_release(dup), "DUPLICATE_SLOT")


def test_a33_t6_page_id_trailing_space_not_blank():
    verdict = check_release(_positive_page(page_id=PAGE_ID + " "))
    _assert_allowed(verdict)


def test_a33_page_id_case_variant_not_blank():
    verdict = check_release(_positive_page(page_id="syn-page-1"))
    _assert_allowed(verdict)
