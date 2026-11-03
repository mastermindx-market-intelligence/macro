"""X8AREP repair tests — request_repair round 1 close-out.

Closes the closeable subset of red-team findings X8A-01..08 in two DRAFT
guard modules:
``research/single_name_intelligence/common/sni_counter_relation_guard.py``
and ``research/single_name_intelligence/common/sni_entitlement_guard.py``.

Each ``test_r1_<nn>_<slug>`` either reproduces a defect and asserts the
required closed behaviour, or — for one PIN slot — asserts a contract the
base already satisfies (the X8A-07 PIN test is allowed to pass on base;
see GAPS for the set of defects the AST-scan pin leaves open).

SNI-local DRAFT contract tests. They consume owner-supplied opaque
identity strings (Stock Identity / Data OS) and never mint issuer,
listing, or security ids. HISTORICAL-DESCRIPTIVE only: rank_authority,
gate_authority, size_authority, signal_authority, escalation_authority
and trade_authority stay literal False. Fixtures are synthetic.

This module does not register, validate, or feed a ranker, gate,
sizer, signal, escalation, or trade path. No network, no git access.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research" / "single_name_intelligence" / "common"))

from sni_counter_relation_guard import check_counter_relation  # noqa: E402
from sni_entitlement_guard import gate_access  # noqa: E402


AS_OF_CRG = "2026-06-01T00:00:00+00:00"
LEFT = "SYN-LISTING-a1"
RIGHT = "SYN-LISTING-b1"


def _base_members():
    return (
        {"listing_id": LEFT, "counter_kind": "ordinary", "currency": "HKD"},
        {"listing_id": RIGHT, "counter_kind": "ads", "currency": "USD"},
    )


def _crg_base_relation(**overrides):
    body = {
        "relation_id": "SYN-REL-1",
        "issuer_id": "SYN-ISSUER-1",
        "source_ref": "SYN-SRC-1",
        "available_at": "2026-05-01T00:00:00+00:00",
        "members": _base_members(),
    }
    body.update(overrides)
    return body


def _crg_base_request():
    return {
        "issuer_id": "SYN-ISSUER-1",
        "left_listing_id": LEFT,
        "right_listing_id": RIGHT,
    }


def _crg_check(relation):
    return check_counter_relation(
        _crg_base_request(), (relation,), as_of=AS_OF_CRG
    )


def _gate_with_spy(request, entitlement):
    calls: list[object] = []

    def loader(document_id):
        calls.append(document_id)
        return "PAYLOAD"

    verdict = gate_access(
        request, entitlement, as_of="2026-10-01T12:00:00+00:00", loader=loader
    )
    return verdict, calls


# ---------------------------------------------------------------------------
# X8A-02 — non-text currency → CURRENCY_UNDECLARED
# ---------------------------------------------------------------------------


def test_r1_02_currency_non_text_undeclared():
    """X8A-02: int / float / bool currency values map to CURRENCY_UNDECLARED."""
    for bad in (840, 840.0, True, False, 0, 1):
        members = (
            {
                "listing_id": LEFT,
                "counter_kind": "ordinary",
                "currency": bad,
            },
            {
                "listing_id": RIGHT,
                "counter_kind": "ads",
                "currency": "USD",
            },
        )
        relation = _crg_base_relation(members=members)
        verdict = _crg_check(relation)
        assert "CURRENCY_UNDECLARED" in set(verdict.reasons), (bad, verdict)


# ---------------------------------------------------------------------------
# X8A-03 — non-str relation_id → RELATION_ID_MISSING; never allowed=True
# with relation_id=None
# ---------------------------------------------------------------------------


def test_r1_03_non_str_relation_id_refused():
    """X8A-03: int / float / bool / list / dict relation_id is refused;
    verdict.relation_id is None."""
    for bad in (0, 1, 1.5, True, False, [], {}):
        relation = _crg_base_relation(relation_id=bad)
        verdict = _crg_check(relation)
        assert verdict.allowed is False, (bad, verdict)
        assert "RELATION_ID_MISSING" in set(verdict.reasons), (bad, verdict)
        assert verdict.relation_id is None, (bad, verdict)


# ---------------------------------------------------------------------------
# X8A-04 — non-str source_ref → RELATION_UNSOURCED
# ---------------------------------------------------------------------------


def test_r1_04_non_str_source_ref_refused():
    """X8A-04: int / float / bool source_ref (non-str) is RELATION_UNSOURCED."""
    for bad in (42, True, False, 0, 1, 1.5):
        relation = _crg_base_relation(source_ref=bad)
        verdict = _crg_check(relation)
        assert verdict.allowed is False, (bad, verdict)
        assert "RELATION_UNSOURCED" in set(verdict.reasons), (bad, verdict)


# ---------------------------------------------------------------------------
# X8A-05 (partial) — non-str entitlement_ref → ENTITLEMENT_REF_MISSING;
# loader not called. Whitespace-only detection is pinned by the AST-scan
# no-normalisation test and remains open (see GAPS).
# ---------------------------------------------------------------------------


def test_r1_05_entitlement_ref_nonstr_refused_loader_uncalled():
    """X8A-05 (non-str part): non-str entitlement_ref is refused;
    loader is never called."""
    request = {
        "surface": "private",
        "account_id": "syn-account-1",
        "document_id": "syn-doca-42",
        "want_full_text": True,
    }
    entitlement_base = {
        "account_id": "syn-account-1",
        "document_ids": ("syn-doca-41", "syn-doca-42"),
        "valid_from": "2026-01-01T00:00:00+00:00",
        "valid_to": None,
        "revoked_at": None,
    }
    for bad in (True, False, 0, 1, 1.5):
        entitlement = dict(entitlement_base, entitlement_ref=bad)
        verdict, calls = _gate_with_spy(request, entitlement)
        assert verdict.allowed is False, (bad, verdict)
        assert "ENTITLEMENT_REF_MISSING" in set(verdict.reasons), (bad, verdict)
        assert calls == [], (bad, calls)


# ---------------------------------------------------------------------------
# X8A-06 — non-text account_id (1 vs True) → ACCOUNT_MISMATCH; loader not
# called; `1` vs `True` never matches
# ---------------------------------------------------------------------------


def test_r1_06_account_id_nontext_account_mismatch_loader_uncalled():
    """X8A-06: non-text account_id (1 vs True) → ACCOUNT_MISMATCH;
    loader is never called."""
    request = {
        "surface": "private",
        "account_id": 1,
        "document_id": "syn-doca-42",
        "want_full_text": True,
    }
    entitlement = {
        "entitlement_ref": "syn-ent-17",
        "account_id": True,
        "document_ids": ("syn-doca-41", "syn-doca-42"),
        "valid_from": "2026-01-01T00:00:00+00:00",
        "valid_to": None,
        "revoked_at": None,
    }
    verdict, calls = _gate_with_spy(request, entitlement)
    assert verdict.allowed is False, verdict
    assert "ACCOUNT_MISMATCH" in set(verdict.reasons), verdict
    assert calls == [], calls


# ---------------------------------------------------------------------------
# X8A-07 PIN — a text-present relation_id is echoed byte-for-byte.
# Whitespace-only and leading/trailing-whitespace refusals are pinned by
# the AST-scan no-normalisation test (see GAPS); this PIN test asserts the
# behaviour that DOES apply on base and on head.
# ---------------------------------------------------------------------------


def test_r1_07_pin_relation_id_byte_for_byte_echo():
    """X8A-07 PIN: a text-present relation_id is echoed byte-for-byte
    (allowed to pass on base; closes the asymmetry that trailing-space /
    listing-ids are refused)."""
    verdict = _crg_check(_crg_base_relation())
    assert verdict.allowed is True
    assert verdict.relation_id == "SYN-REL-1"
    # Explicit byte-for-byte: encode round-trip matches.
    assert verdict.relation_id.encode("utf-8") == b"SYN-REL-1"
