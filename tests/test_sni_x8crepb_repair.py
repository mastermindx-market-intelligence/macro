"""X8CREPB round-1 repair tests (red-team X8C-01, X8C-02, X8C-09, X8C-12).

Sibling of tests/test_sni_release_evidence_guard.py and
tests/test_sni_identity_binding_guard.py; covers the FAMILY TEXT RULE
enforcement on release-evidence and identity-binding DRAFT guards and
the docstring-only PIN for X8C-02. Every closed defect has exactly one
test function, named test_r1_<nn>_<slug>. Fixtures are synthetic.

This module does not register, validate, or feed a ranker, gate, sizer,
signal, escalation, or trade path. HISTORICAL-DESCRIPTIVE only.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research" / "single_name_intelligence" / "common"))

from sni_identity_binding_guard import (  # noqa: E402
    IdentityBindingVerdict,
    bind_identity,
)
from sni_release_evidence_guard import (  # noqa: E402
    ReleaseVerdict,
    check_release,
)

AS_OF = "2026-08-20T12:00:00+00:00"
AVAILABLE_AT = "2026-08-20T11:00:00+00:00"


# ---------------------------------------------------------------------------
# X8C-01 — release-evidence: a slot whose slot_id is missing/None is never
# counted as a present owner slot.
# ---------------------------------------------------------------------------


def test_r1_01_slot_id_missing_not_present_owner():
    # From the X8C-01 EVIDENCE call: three slots, the first has slot_id=None;
    # the verdict must be refused (the id-less slot cannot satisfy a required
    # slot) and the id-less slot must not appear in present_owner_slots.
    page = {
        "page_id": "P",
        "slots": (
            {
                "slot_id": None,
                "state": "present",
                "provenance": "owner",
                "evidence_ref": "X",
                "required": True,
            },
            {
                "slot_id": "S1",
                "state": "present",
                "provenance": "owner",
                "evidence_ref": "Y",
                "required": True,
            },
            {
                "slot_id": "S2",
                "state": "present",
                "provenance": "owner",
                "evidence_ref": "Z",
                "required": True,
            },
        ),
    }
    verdict = check_release(page)
    assert isinstance(verdict, ReleaseVerdict)
    assert verdict.allowed is False
    # the REASONS tuple is pinned by an existing test, so the fallback
    # refusal reason for a missing/non-text slot_id is SLOT_STATE_UNKNOWN
    assert "SLOT_STATE_UNKNOWN" in verdict.reasons
    assert None not in verdict.present_owner_slots
    assert verdict.present_owner_slots == ("S1", "S2")


def test_r1_01_slot_id_key_absent_not_present_owner():
    # From the X8C-01 EVIDENCE second call: the slot has no slot_id KEY at all
    # (the key is absent, not None); same fail-closed behaviour.
    page = {
        "page_id": "P",
        "slots": (
            {
                "state": "present",
                "provenance": "owner",
                "evidence_ref": "X",
                "required": True,
            },
            {
                "slot_id": "S1",
                "state": "present",
                "provenance": "owner",
                "evidence_ref": "Y",
                "required": True,
            },
        ),
    }
    verdict = check_release(page)
    assert verdict.allowed is False
    assert "SLOT_STATE_UNKNOWN" in verdict.reasons
    assert None not in verdict.present_owner_slots
    assert verdict.present_owner_slots == ("S1",)


# ---------------------------------------------------------------------------
# X8C-02 — identity-binding: ID_LOOKS_DERIVED keeps its substring semantics;
# the SEAT RULING says false positives are accepted by design.
# PIN tests (must pass on base and on head).
# ---------------------------------------------------------------------------


def test_r1_02_pin_display_code_substring_in_listing_id_refused():
    # PIN: display_code="0700" with listing_id="HK0700" is REFUSED
    # ID_LOOKS_DERIVED (substring rule, >= 3 chars).
    verdict = bind_identity(
        {
            "listing_id": "HK0700",
            "issuer_id": "SYN-ISS-1",
            "currency": "CCC",
            "operation_needs_issuer": True,
        },
        listing={
            "listing_id": "HK0700",
            "security_id": "SYN-SEC-1",
            "currency": "CCC",
            "owner_ref": "O",
            "available_at": AVAILABLE_AT,
            "display_code": "0700",
            "display_name": "Tencent Holdings",
        },
        security={
            "security_id": "SYN-SEC-1",
            "issuer_id": "SYN-ISS-1",
            "owner_ref": "O",
            "available_at": AVAILABLE_AT,
        },
        issuer={
            "issuer_id": "SYN-ISS-1",
            "owner_ref": "O",
            "available_at": AVAILABLE_AT,
        },
        as_of=AS_OF,
    )
    assert isinstance(verdict, IdentityBindingVerdict)
    assert verdict.allowed is False
    assert "ID_LOOKS_DERIVED" in verdict.reasons


def test_r1_02_pin_two_char_display_code_does_not_trigger():
    # PIN: a 2-character display code never triggers ID_LOOKS_DERIVED.
    verdict = bind_identity(
        {
            "listing_id": "SYN-LIST-1",
            "issuer_id": "SYN-ISS-1",
            "currency": "CCC",
            "operation_needs_issuer": True,
        },
        listing={
            "listing_id": "SYN-LIST-1",
            "security_id": "SYN-SEC-1",
            "currency": "CCC",
            "owner_ref": "O",
            "available_at": AVAILABLE_AT,
            "display_code": "SY",
            "display_name": "Synthetic Holding One",
        },
        security={
            "security_id": "SYN-SEC-1",
            "issuer_id": "SYN-ISS-1",
            "owner_ref": "O",
            "available_at": AVAILABLE_AT,
        },
        issuer={
            "issuer_id": "SYN-ISS-1",
            "owner_ref": "O",
            "available_at": AVAILABLE_AT,
        },
        as_of=AS_OF,
    )
    assert "ID_LOOKS_DERIVED" not in verdict.reasons
    assert verdict.allowed is True


# ---------------------------------------------------------------------------
# X8C-09 — release-evidence: page_id, slot_id, evidence_ref follow the
# FAMILY TEXT RULE. Non-text or padded values are ABSENT.
# ---------------------------------------------------------------------------


def test_r1_09_evidence_ref_zero_is_present_without_ref():
    # From X8C-09 RE-CHECK: evidence_ref=0 -> PRESENT_WITHOUT_REF.
    page = {
        "page_id": "P",
        "slots": (
            {
                "slot_id": "S1",
                "state": "present",
                "provenance": "owner",
                "evidence_ref": 0,
                "required": True,
            },
            {
                "slot_id": "S2",
                "state": "present",
                "provenance": "owner",
                "evidence_ref": "Y",
                "required": True,
            },
        ),
    }
    verdict = check_release(page)
    assert verdict.allowed is False
    assert "PRESENT_WITHOUT_REF" in verdict.reasons


def test_r1_09_page_id_zero_is_page_id_missing():
    # From X8C-09 RE-CHECK: page_id=0 -> PAGE_ID_MISSING.
    page = {
        "page_id": 0,
        "slots": (
            {
                "slot_id": "S1",
                "state": "present",
                "provenance": "owner",
                "evidence_ref": "X",
                "required": True,
            },
        ),
    }
    verdict = check_release(page)
    assert verdict.allowed is False
    assert "PAGE_ID_MISSING" in verdict.reasons


def test_r1_09_slot_id_zero_not_present_owner():
    # FAMILY TEXT RULE on slot_id: 0 (int) is ABSENT, so the slot is
    # refused and does not appear in present_owner_slots.
    page = {
        "page_id": "P",
        "slots": (
            {
                "slot_id": 0,
                "state": "present",
                "provenance": "owner",
                "evidence_ref": "X",
                "required": True,
            },
            {
                "slot_id": "S1",
                "state": "present",
                "provenance": "owner",
                "evidence_ref": "Y",
                "required": True,
            },
        ),
    }
    verdict = check_release(page)
    assert verdict.allowed is False
    assert "SLOT_STATE_UNKNOWN" in verdict.reasons
    assert 0 not in verdict.present_owner_slots
    assert verdict.present_owner_slots == ("S1",)


# ---------------------------------------------------------------------------
# X8C-12 — identity-binding: listing_id / security_id / issuer_id / owner_ref
# follow the FAMILY TEXT RULE. The verdict's id fields stay None whenever
# the corresponding input is not text-present, and no non-text id ever
# appears in an allowed verdict.
# ---------------------------------------------------------------------------


def test_r1_12_non_text_listing_id_never_allowed():
    # From X8C-12 RE-CHECK: a non-text listing_id on both sides must never
    # produce an allowed verdict, and the verdict.listing_id field stays None.
    verdict = bind_identity(
        {
            "listing_id": 1,
            "issuer_id": "SYN-ISS-1",
            "currency": "CCC",
            "operation_needs_issuer": True,
        },
        listing={
            "listing_id": 1,
            "security_id": "SYN-SEC-1",
            "currency": "CCC",
            "owner_ref": "O",
            "available_at": AVAILABLE_AT,
            "display_code": "QZX",
            "display_name": "Synthetic Holding One",
        },
        security={
            "security_id": "SYN-SEC-1",
            "issuer_id": "SYN-ISS-1",
            "owner_ref": "O",
            "available_at": AVAILABLE_AT,
        },
        issuer={
            "issuer_id": "SYN-ISS-1",
            "owner_ref": "O",
            "available_at": AVAILABLE_AT,
        },
        as_of=AS_OF,
    )
    assert isinstance(verdict, IdentityBindingVerdict)
    assert verdict.allowed is False
    assert verdict.listing_id is None
    assert "LISTING_ID_MISMATCH" in verdict.reasons


def test_r1_12_non_text_owner_ref_is_owner_ref_missing():
    # FAMILY TEXT RULE on owner_ref: 12345 (int) is ABSENT, so emit
    # OWNER_REF_MISSING rather than treating the int as a present owner ref.
    verdict = bind_identity(
        {
            "listing_id": "SYN-LIST-1",
            "issuer_id": "SYN-ISS-1",
            "currency": "CCC",
            "operation_needs_issuer": True,
        },
        listing={
            "listing_id": "SYN-LIST-1",
            "security_id": "SYN-SEC-1",
            "currency": "CCC",
            "owner_ref": 12345,
            "available_at": AVAILABLE_AT,
            "display_code": "QZX",
            "display_name": "Synthetic Holding One",
        },
        security={
            "security_id": "SYN-SEC-1",
            "issuer_id": "SYN-ISS-1",
            "owner_ref": "O",
            "available_at": AVAILABLE_AT,
        },
        issuer={
            "issuer_id": "SYN-ISS-1",
            "owner_ref": "O",
            "available_at": AVAILABLE_AT,
        },
        as_of=AS_OF,
    )
    assert verdict.allowed is False
    assert "OWNER_REF_MISSING" in verdict.reasons