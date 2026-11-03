"""X8AREP2 repair tests — request_repair round 2 close-out.

Closes the regression and the whitespace halves round 1 left open in two
DRAFT guard modules:
``research/single_name_intelligence/common/sni_counter_relation_guard.py``
and ``research/single_name_intelligence/common/sni_entitlement_guard.py``.

Each ``test_r2_<nn>_<slug>`` either reproduces a defect and asserts the
required closed behaviour, or — for the text-present PIN slot — asserts a
contract the base already satisfies (FAMILY TEXT RULE v2 allows the
byte-for-byte echo on text-present ids; the FAMILY TEXT RULE v2 helper
itself is verified by ``test_r2_02_*``).

SNI-local DRAFT contract tests. They consume owner-supplied opaque
identity strings (Stock Identity / Data OS) and never mint issuer,
listing, or security ids. HISTORICAL-DESCRIPTIVE only: rank_authority,
gate_authority, size_authority, signal_authority, escalation_authority
and trade_authority stay literal False. Fixtures are synthetic.

This module does not register, validate, or feed a ranker, gate,
sizer, signal, escalation, or trade path. No network, no git access.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research" / "single_name_intelligence" / "common"))

from sni_counter_relation_guard import check_counter_relation  # noqa: E402
from sni_entitlement_guard import gate_access  # noqa: E402

CRG_MODULE_PATH = (
    ROOT
    / "research"
    / "single_name_intelligence"
    / "common"
    / "sni_counter_relation_guard.py"
)
ENT_MODULE_PATH = (
    ROOT
    / "research"
    / "single_name_intelligence"
    / "common"
    / "sni_entitlement_guard.py"
)

AS_OF_CRG = "2026-06-01T00:00:00+00:00"
LEFT = "SYN-LISTING-a1"
RIGHT = "SYN-LISTING-b1"
AS_OF_ENT = "2026-10-01T12:00:00+00:00"
_VALID_FROM = "2026-01-01T00:00:00+00:00"
_ACCOUNT = "syn-account-1"
_DOCUMENT = "syn-doca-42"
_ENT_REF = "syn-ent-17"


def _crg_base_members():
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
        "members": _crg_base_members(),
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


def _ent_private_request(**overrides):
    body = {
        "surface": "private",
        "account_id": _ACCOUNT,
        "document_id": _DOCUMENT,
        "want_full_text": True,
    }
    body.update(overrides)
    return body


def _ent_base_entitlement(**overrides):
    body = {
        "entitlement_ref": _ENT_REF,
        "account_id": _ACCOUNT,
        "document_ids": (_DOCUMENT, "syn-doca-41"),
        "valid_from": _VALID_FROM,
        "valid_to": None,
        "revoked_at": None,
    }
    body.update(overrides)
    return body


def _gate_with_spy(request, entitlement):
    calls: list[object] = []

    def loader(document_id):
        calls.append(document_id)
        return "PAYLOAD"

    verdict = gate_access(
        request, entitlement, as_of=AS_OF_ENT, loader=loader
    )
    return verdict, calls


# ---------------------------------------------------------------------------
# X8AREP2-01 — REGRESSION. account_id whitespace / leading / trailing /
# None pairs route to ACCOUNT_MISMATCH with the loader uncalled;
# a clean text-present pair still opens.
# ---------------------------------------------------------------------------


def test_r2_01_account_id_blank_pairs_refuse_loader_uncalled():
    """X8AREP2-01 REGRESSION: account_id whitespace / leading / trailing
    / None pairs refuse with ACCOUNT_MISMATCH; loader is never called;
    a clean text-present pair still opens exactly as before."""
    blank_pairs = (
        ("", ""),
        (" ", " "),
        ("　", "　"),
        (" acct", " acct"),
        ("acct\n", "acct\n"),
        (None, None),
    )
    for request_aid, ent_aid in blank_pairs:
        request = _ent_private_request(account_id=request_aid)
        entitlement = _ent_base_entitlement(account_id=ent_aid)
        verdict, calls = _gate_with_spy(request, entitlement)
        assert verdict.allowed is False, (request_aid, ent_aid, verdict)
        assert "ACCOUNT_MISMATCH" in set(verdict.reasons), (
            request_aid,
            ent_aid,
            verdict,
        )
        assert calls == [], (request_aid, ent_aid, calls)

    # PIN: clean text-present pair still opens.
    request = _ent_private_request(account_id=_ACCOUNT)
    entitlement = _ent_base_entitlement(account_id=_ACCOUNT)
    verdict, calls = _gate_with_spy(request, entitlement)
    assert verdict.allowed is True, verdict
    assert verdict.reasons == (), verdict
    assert calls == [_DOCUMENT], calls


# ---------------------------------------------------------------------------
# X8AREP2-02 — FAMILY TEXT RULE v2 helper added to BOTH owned modules;
# AST-scan no-normalisation rule remains green.
# ---------------------------------------------------------------------------


def _module_has_text_present(path: Path) -> bool:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "_text_present":
            return True
    return False


def _module_normalisation_free(path: Path) -> bool:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden_attr = {"lower", "upper", "casefold", "strip", "replace"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in forbidden_attr:
                return False
    return True


def test_r2_02_text_present_helper_added_to_both_modules():
    """X8AREP2-02: ``_text_present`` is defined in both owned modules;
    both stay free of strip / lower / upper / casefold / replace calls
    (A02G and A18 AST-scan tests stay green)."""
    assert _module_has_text_present(CRG_MODULE_PATH), (
        "sni_counter_relation_guard.py must define _text_present"
    )
    assert _module_has_text_present(ENT_MODULE_PATH), (
        "sni_entitlement_guard.py must define _text_present"
    )
    assert _module_normalisation_free(CRG_MODULE_PATH), (
        "sni_counter_relation_guard.py contains a forbidden "
        "normalisation call"
    )
    assert _module_normalisation_free(ENT_MODULE_PATH), (
        "sni_entitlement_guard.py contains a forbidden "
        "normalisation call"
    )


# ---------------------------------------------------------------------------
# X8AREP2-03 — counter-relation whitespace halves: relation_id,
# source_ref, currency through ``_text_present``. PIN: relation_id
#    "SYN-REL-1" echoed byte-for-byte.
# ---------------------------------------------------------------------------


def test_r2_03_counter_relation_whitespace_refused_idate():
    """X8AREP2-03: whitespace / leading / trailing whitespace values
    for relation_id / source_ref / currency are refused with the
    matching reason; a text-present relation_id is echoed unchanged."""
    bad_relation_id_inputs = (" ", "\t", "\n", "　", " REL", "REL\n")
    for ws in bad_relation_id_inputs:
        relation = _crg_base_relation(relation_id=ws)
        verdict = _crg_check(relation)
        assert verdict.allowed is False, (ws, verdict)
        assert "RELATION_ID_MISSING" in set(verdict.reasons), (ws, verdict)
        assert verdict.relation_id is None, (ws, verdict)

    for ws in bad_relation_id_inputs:
        relation = _crg_base_relation(source_ref=ws)
        verdict = _crg_check(relation)
        assert verdict.allowed is False, (ws, verdict)
        assert "RELATION_UNSOURCED" in set(verdict.reasons), (ws, verdict)

    for ws in bad_relation_id_inputs:
        relation = _crg_base_relation(
            members=(
                {
                    "listing_id": LEFT,
                    "counter_kind": "ordinary",
                    "currency": ws,
                },
                {
                    "listing_id": RIGHT,
                    "counter_kind": "ads",
                    "currency": "USD",
                },
            )
        )
        verdict = _crg_check(relation)
        assert verdict.allowed is False, (ws, verdict)
        assert "CURRENCY_UNDECLARED" in set(verdict.reasons), (ws, verdict)


def test_r2_03_pin_relation_id_byte_for_byte_echo():
    """X8AREP2-03 PIN. A text-present relation_id is echoed byte-for-byte
    in the verdict (allowed to pass on base; closes the asymmetry that
    trailing-space relation_ids were echoed verbatim)."""
    verdict = _crg_check(_crg_base_relation())
    assert verdict.allowed is True
    assert verdict.relation_id == "SYN-REL-1"
    assert verdict.relation_id.encode("utf-8") == b"SYN-REL-1"


# ---------------------------------------------------------------------------
# X8AREP2-04 — entitlement_ref whitespace half: leading / trailing / empty
# / whitespace values route to ENTITLEMENT_REF_MISSING; loader uncalled.
# ---------------------------------------------------------------------------


def test_r2_04_entitlement_ref_whitespace_refused_loader_uncalled():
    """X8AREP2-04: whitespace / leading / trailing whitespace
    entitlement_ref values are refused with ENTITLEMENT_REF_MISSING;
    loader is never called."""
    request = _ent_private_request()
    bad_inputs = (" ", "\t", "\n", "　", " ref", "ref\n")
    for ws in bad_inputs:
        entitlement = _ent_base_entitlement(entitlement_ref=ws)
        verdict, calls = _gate_with_spy(request, entitlement)
        assert verdict.allowed is False, (ws, verdict)
        assert "ENTITLEMENT_REF_MISSING" in set(verdict.reasons), (
            ws,
            verdict,
        )
        assert calls == [], (ws, calls)