"""A18 entitlement-guard tests: denial precedes private access.

SNI-local DRAFT contract tests for the pre-access entitlement gate.
They consume owner-shaped entitlement records (Research Vault owner)
and caller-supplied opaque account/document ids; they never mint
issuer or security ids. HISTORICAL-DESCRIPTIVE only: rank_authority,
gate_authority, size_authority, signal_authority, escalation_authority
and trade_authority stay literal False. Fixtures are synthetic.

This module does not register, validate, or feed a ranker, gate, sizer,
signal, escalation, or trade path.
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research" / "single_name_intelligence" / "common"))

from sni_entitlement_guard import (  # noqa: E402
    AUTHORITY_FLAGS,
    REASONS,
    SURFACES,
    AccessVerdict,
    gate_access,
    refuse_nonfalse_authority,
)

MODULE_PATH = (
    ROOT
    / "research"
    / "single_name_intelligence"
    / "common"
    / "sni_entitlement_guard.py"
)

FLAG_NAMES = (
    "rank_authority",
    "gate_authority",
    "size_authority",
    "signal_authority",
    "escalation_authority",
    "trade_authority",
)

_AS_OF = "2026-10-01T12:00:00+00:00"
_VALID_FROM = "2026-01-01T00:00:00+00:00"
_ACCOUNT = "syn-account-1"
_DOCUMENT = "syn-doca-42"
_ENT_REF = "syn-ent-17"
CYRILLIC_A = "\u0430"  # Cyrillic small letter a, not Latin a
assert ord(CYRILLIC_A) == 0x0430


class _Omit:
    pass


_OMIT = _Omit()


class _LoaderSpy:
    """Counts loader calls and records the arguments it was called with."""

    def __init__(self, payload: str = "SYN-PAYLOAD-7c3e-FULL-TEXT"):
        self.payload = payload
        self.calls: list[object] = []

    def __call__(self, document_id):
        self.calls.append(document_id)
        return self.payload

    @property
    def count(self) -> int:
        return len(self.calls)


def _request(**overrides):
    body = {
        "surface": "private",
        "account_id": _ACCOUNT,
        "document_id": _DOCUMENT,
        "want_full_text": True,
    }
    body.update(overrides)
    drop = [key for key, val in body.items() if val is _OMIT]
    for key in drop:
        del body[key]
    return body


def _entitlement(**overrides):
    body = {
        "entitlement_ref": _ENT_REF,
        "account_id": _ACCOUNT,
        "document_ids": ("syn-doca-41", "syn-doca-42"),
        "valid_from": _VALID_FROM,
        "valid_to": None,
        "revoked_at": None,
    }
    body.update(overrides)
    drop = [key for key, val in body.items() if val is _OMIT]
    for key in drop:
        del body[key]
    return body


def _gate(request, entitlement, spy, as_of=_AS_OF):
    return gate_access(request, entitlement, as_of=as_of, loader=spy)


def _assert_contract(verdict: AccessVerdict) -> None:
    assert verdict.allowed == (verdict.reasons == ())
    for code in verdict.reasons:
        assert code in REASONS, (code, verdict.reasons)
    assert list(verdict.reasons) == sorted(
        verdict.reasons, key=REASONS.index
    ), verdict.reasons
    assert verdict.authority_flags is AUTHORITY_FLAGS
    for name in FLAG_NAMES:
        assert verdict.authority_flags[name] is False
        assert verdict.authority_flags[name] is not True


def _assert_allowed(verdict: AccessVerdict) -> None:
    assert verdict.allowed is True, verdict.reasons
    assert verdict.reasons == ()
    _assert_contract(verdict)


def _assert_refused(verdict: AccessVerdict, spy: _LoaderSpy, *codes: str) -> None:
    assert verdict.allowed is False, verdict.reasons
    got = set(verdict.reasons)
    for code in codes:
        assert code in got, (code, verdict.reasons)
    assert spy.count == 0, spy.calls
    assert verdict.payload is None
    _assert_contract(verdict)


# ---------------------------------------------------------------------------
# Positive controls
# ---------------------------------------------------------------------------


def test_a18_positive_private_full_text_allowed():
    spy = _LoaderSpy()
    verdict = _gate(_request(), _entitlement(), spy)
    _assert_allowed(verdict)
    assert spy.count == 1
    assert spy.calls == [_DOCUMENT]
    assert verdict.payload is spy.payload


def test_a18_positive_private_want_false_still_loads_once():
    spy = _LoaderSpy()
    verdict = _gate(_request(want_full_text=False), _entitlement(), spy)
    _assert_allowed(verdict)
    assert spy.count == 1
    assert verdict.payload is spy.payload


def test_a18_positive_public_metadata_only_allowed():
    spy = _LoaderSpy()
    verdict = _gate(_request(surface="public", want_full_text=False), _entitlement(), spy)
    _assert_allowed(verdict)
    assert spy.count == 0
    assert verdict.payload is None
    bare = _gate(_request(surface="public", want_full_text=False), None, spy)
    _assert_allowed(bare)
    assert spy.count == 0
    assert bare.payload is None


# ---------------------------------------------------------------------------
# One single-flip refusal per REASONS entry
# ---------------------------------------------------------------------------


def test_a18_public_full_text_forbidden():
    spy = _LoaderSpy()
    verdict = _gate(
        _request(surface="public", want_full_text=True), _entitlement(), spy
    )
    _assert_refused(verdict, spy, "PUBLIC_FULL_TEXT_FORBIDDEN")
    assert verdict.reasons == ("PUBLIC_FULL_TEXT_FORBIDDEN",)


def test_a18_surface_unknown():
    spy = _LoaderSpy()
    verdict = _gate(_request(surface="internal"), _entitlement(), spy)
    _assert_refused(verdict, spy, "SURFACE_UNKNOWN")
    assert verdict.reasons == ("SURFACE_UNKNOWN",)


def test_a18_as_of_invalid():
    spy = _LoaderSpy()
    verdict = _gate(_request(), _entitlement(), spy, as_of="2026-10-01T12:00:00")
    _assert_refused(verdict, spy, "AS_OF_INVALID")
    assert verdict.reasons == ("AS_OF_INVALID",)


def test_a18_entitlement_missing():
    spy = _LoaderSpy()
    verdict = _gate(_request(), None, spy)
    _assert_refused(verdict, spy, "ENTITLEMENT_MISSING")
    assert verdict.reasons == ("ENTITLEMENT_MISSING",)


def test_a18_entitlement_ref_missing():
    spy = _LoaderSpy()
    verdict = _gate(_request(), _entitlement(entitlement_ref=None), spy)
    _assert_refused(verdict, spy, "ENTITLEMENT_REF_MISSING")
    assert verdict.reasons == ("ENTITLEMENT_REF_MISSING",)


def test_a18_account_mismatch():
    spy = _LoaderSpy()
    verdict = _gate(_request(account_id="syn-account-2"), _entitlement(), spy)
    _assert_refused(verdict, spy, "ACCOUNT_MISMATCH")
    assert verdict.reasons == ("ACCOUNT_MISMATCH",)


def test_a18_document_not_entitled():
    spy = _LoaderSpy()
    verdict = _gate(_request(document_id="syn-doca-99"), _entitlement(), spy)
    _assert_refused(verdict, spy, "DOCUMENT_NOT_ENTITLED")
    assert verdict.reasons == ("DOCUMENT_NOT_ENTITLED",)


def test_a18_entitlement_not_yet_valid():
    spy = _LoaderSpy()
    verdict = _gate(
        _request(), _entitlement(valid_from="2027-01-01T00:00:00+00:00"), spy
    )
    _assert_refused(verdict, spy, "ENTITLEMENT_NOT_YET_VALID")
    assert verdict.reasons == ("ENTITLEMENT_NOT_YET_VALID",)


def test_a18_entitlement_expired():
    spy = _LoaderSpy()
    verdict = _gate(
        _request(), _entitlement(valid_to="2026-06-01T00:00:00+00:00"), spy
    )
    _assert_refused(verdict, spy, "ENTITLEMENT_EXPIRED")
    assert verdict.reasons == ("ENTITLEMENT_EXPIRED",)


def test_a18_entitlement_revoked():
    spy = _LoaderSpy()
    verdict = _gate(
        _request(), _entitlement(revoked_at="2026-05-01T00:00:00+00:00"), spy
    )
    _assert_refused(verdict, spy, "ENTITLEMENT_REVOKED")
    assert verdict.reasons == ("ENTITLEMENT_REVOKED",)


# ---------------------------------------------------------------------------
# Public-surface hard refusal
# ---------------------------------------------------------------------------


def test_a18_public_fulltext_valid_entitlement_refuses():
    spy = _LoaderSpy()
    ent = _entitlement(valid_to="2027-01-01T00:00:00+00:00")
    verdict = _gate(_request(surface="public", want_full_text=True), ent, spy)
    _assert_refused(verdict, spy, "PUBLIC_FULL_TEXT_FORBIDDEN")
    assert verdict.reasons == ("PUBLIC_FULL_TEXT_FORBIDDEN",)


def test_a18_want_full_text_nonfalse_variants_refuse():
    spy = _LoaderSpy()
    for value in (True, 1, "false", None, 0, _OMIT):
        request = _request(surface="public")
        if value is _OMIT:
            del request["want_full_text"]
        else:
            request["want_full_text"] = value
        verdict = _gate(request, _entitlement(), spy)
        _assert_refused(verdict, spy, "PUBLIC_FULL_TEXT_FORBIDDEN")
        assert spy.count == 0


def test_a18_surface_case_and_space_refuse():
    spy = _LoaderSpy()
    for value in ("Public", "PRIVATE", "private ", " public", "Internal"):
        verdict = _gate(_request(surface=value), _entitlement(), spy)
        _assert_refused(verdict, spy, "SURFACE_UNKNOWN")
        assert spy.count == 0


# ---------------------------------------------------------------------------
# Timestamp handling
# ---------------------------------------------------------------------------


def test_a18_as_of_variants_invalid():
    spy = _LoaderSpy()
    for value in (
        "2026-10-01",
        "2026-10-01T12:00:00",
        "not-a-timestamp",
        "",
        None,
        "2026-13-01T00:00:00+00:00",
    ):
        verdict = _gate(_request(), _entitlement(), spy, as_of=value)
        _assert_refused(verdict, spy, "AS_OF_INVALID")
        assert spy.count == 0


def test_a18_boundary_at_valid_from_allowed():
    spy = _LoaderSpy()
    verdict = _gate(_request(), _entitlement(), spy, as_of=_VALID_FROM)
    _assert_allowed(verdict)
    assert spy.count == 1
    assert verdict.payload is spy.payload


def test_a18_boundary_at_valid_to_expired():
    spy = _LoaderSpy()
    verdict = _gate(_request(), _entitlement(valid_to=_AS_OF), spy)
    _assert_refused(verdict, spy, "ENTITLEMENT_EXPIRED")
    assert verdict.reasons == ("ENTITLEMENT_EXPIRED",)
    later = _LoaderSpy()
    ok = _gate(
        _request(), _entitlement(valid_to="2026-10-01T12:00:01+00:00"), later
    )
    _assert_allowed(ok)
    assert later.count == 1


def test_a18_boundary_at_revoked_at_revoked():
    spy = _LoaderSpy()
    verdict = _gate(_request(), _entitlement(revoked_at=_AS_OF), spy)
    _assert_refused(verdict, spy, "ENTITLEMENT_REVOKED")
    assert verdict.reasons == ("ENTITLEMENT_REVOKED",)
    later = _LoaderSpy()
    ok = _gate(
        _request(), _entitlement(revoked_at="2026-10-01T12:00:01+00:00"), later
    )
    _assert_allowed(ok)
    assert later.count == 1


def test_a18_boundary_equal_instant_offsets_allowed():
    spy = _LoaderSpy()
    verdict = _gate(
        _request(), _entitlement(), spy, as_of="2026-01-01T01:00:00+01:00"
    )
    _assert_allowed(verdict)
    assert spy.count == 1


def test_a18_open_window_valid_to_none_allowed():
    spy = _LoaderSpy()
    verdict = _gate(
        _request(), _entitlement(), spy, as_of="2030-01-01T00:00:00+00:00"
    )
    _assert_allowed(verdict)
    assert spy.count == 1


def test_a18_naive_bounds_fail_closed():
    spy = _LoaderSpy()
    naive_from = _gate(
        _request(), _entitlement(valid_from="2026-01-01T00:00:00"), spy
    )
    _assert_refused(naive_from, spy, "ENTITLEMENT_NOT_YET_VALID")
    naive_to = _gate(
        _request(), _entitlement(valid_to="2027-01-01T00:00:00"), spy
    )
    _assert_refused(naive_to, spy, "ENTITLEMENT_EXPIRED")
    naive_revoked = _gate(
        _request(), _entitlement(revoked_at="2027-01-01T00:00:00"), spy
    )
    _assert_refused(naive_revoked, spy, "ENTITLEMENT_REVOKED")
    assert spy.count == 0


# ---------------------------------------------------------------------------
# Payload hygiene
# ---------------------------------------------------------------------------


def test_a18_repr_hides_payload():
    spy = _LoaderSpy()
    verdict = _gate(_request(), _entitlement(), spy)
    _assert_allowed(verdict)
    text = repr(verdict)
    assert spy.payload not in text
    assert "payload" not in text
    assert verdict.payload is spy.payload


def test_a18_every_refusal_never_loads():
    scenarios = [
        (_request(surface="internal"), _entitlement()),
        (_request(), _entitlement()),
        (_request(surface="public", want_full_text=True), _entitlement()),
        (_request(), None),
        (_request(), _entitlement(entitlement_ref="")),
        (_request(account_id="syn-account-2"), _entitlement()),
        (_request(document_id="syn-doca-99"), _entitlement()),
        (_request(), _entitlement(valid_from="2027-01-01T00:00:00+00:00")),
        (_request(), _entitlement(valid_to="2026-06-01T00:00:00+00:00")),
        (_request(), _entitlement(revoked_at="2026-05-01T00:00:00+00:00")),
    ]
    stamps = [_AS_OF, "2026-10-01T12:00:00", _AS_OF, _AS_OF, _AS_OF, _AS_OF,
              _AS_OF, _AS_OF, _AS_OF, _AS_OF]
    for (request, ent), as_of in zip(scenarios, stamps):
        spy = _LoaderSpy()
        verdict = _gate(request, ent, spy, as_of=as_of)
        assert verdict.allowed is False, verdict.reasons
        assert spy.count == 0
        assert verdict.payload is None


# ---------------------------------------------------------------------------
# Adversarial opaque ids (T6: account_id / document_id)
# ---------------------------------------------------------------------------


def test_a18_account_trailing_space_refuses():
    spy = _LoaderSpy()
    verdict = _gate(_request(account_id=_ACCOUNT + " "), _entitlement(), spy)
    _assert_refused(verdict, spy, "ACCOUNT_MISMATCH")
    other = _LoaderSpy()
    flipped = _gate(_request(), _entitlement(account_id=_ACCOUNT + " "), other)
    _assert_refused(flipped, other, "ACCOUNT_MISMATCH")


def test_a18_account_case_change_refuses():
    spy = _LoaderSpy()
    verdict = _gate(_request(account_id="SYN-ACCOUNT-1"), _entitlement(), spy)
    _assert_refused(verdict, spy, "ACCOUNT_MISMATCH")


def test_a18_account_cyrillic_lookalike_refuses():
    spy = _LoaderSpy()
    fake = "syn-" + CYRILLIC_A + "ccount-1"
    assert fake != _ACCOUNT
    verdict = _gate(_request(account_id=fake), _entitlement(), spy)
    _assert_refused(verdict, spy, "ACCOUNT_MISMATCH")


def test_a18_document_trailing_space_refuses():
    spy = _LoaderSpy()
    verdict = _gate(_request(document_id=_DOCUMENT + " "), _entitlement(), spy)
    _assert_refused(verdict, spy, "DOCUMENT_NOT_ENTITLED")


def test_a18_document_case_change_refuses():
    spy = _LoaderSpy()
    verdict = _gate(_request(document_id="SYN-DOCA-42"), _entitlement(), spy)
    _assert_refused(verdict, spy, "DOCUMENT_NOT_ENTITLED")
    other = _LoaderSpy()
    flipped = _gate(
        _request(), _entitlement(document_ids=("SYN-DOCA-41", "SYN-DOCA-42")), other
    )
    _assert_refused(flipped, other, "DOCUMENT_NOT_ENTITLED")


def test_a18_document_cyrillic_lookalike_refuses():
    spy = _LoaderSpy()
    fake = "syn-doc" + CYRILLIC_A + "-42"
    assert fake != _DOCUMENT
    verdict = _gate(_request(document_id=fake), _entitlement(), spy)
    _assert_refused(verdict, spy, "DOCUMENT_NOT_ENTITLED")


# ---------------------------------------------------------------------------
# Multi-reason order and de-duplication (T5)
# ---------------------------------------------------------------------------


def test_a18_multi_reason_order_and_dedup():
    spy = _LoaderSpy()
    ent = _entitlement(
        entitlement_ref=None,
        account_id="syn-account-9",
        document_ids=("syn-doca-77",),
        valid_to="2026-02-01T00:00:00+00:00",
    )
    verdict = _gate(_request(), ent, spy)
    _assert_refused(
        verdict,
        spy,
        "ENTITLEMENT_REF_MISSING",
        "ACCOUNT_MISMATCH",
        "DOCUMENT_NOT_ENTITLED",
        "ENTITLEMENT_EXPIRED",
    )
    assert verdict.reasons == (
        "ENTITLEMENT_REF_MISSING",
        "ACCOUNT_MISMATCH",
        "DOCUMENT_NOT_ENTITLED",
        "ENTITLEMENT_EXPIRED",
    )
    assert len(verdict.reasons) == len(set(verdict.reasons))


def test_a18_multi_document_entitlement_allowed():
    ent = _entitlement(
        document_ids=("syn-doca-41", "syn-doca-42", "syn-doca-43")
    )
    for document_id in ("syn-doca-41", "syn-doca-43"):
        spy = _LoaderSpy()
        verdict = _gate(_request(document_id=document_id), ent, spy)
        _assert_allowed(verdict)
        assert spy.count == 1
        assert spy.calls == [document_id]


# ---------------------------------------------------------------------------
# Authority (T3)
# ---------------------------------------------------------------------------


def test_a18_authority_refuse_nonfalse_raises():
    refuse_nonfalse_authority()
    refuse_nonfalse_authority(AUTHORITY_FLAGS)
    refuse_nonfalse_authority(dict(AUTHORITY_FLAGS))
    for name in FLAG_NAMES:
        for bad in (True, 0, None, ""):
            flags = dict(AUTHORITY_FLAGS)
            flags[name] = bad
            with pytest.raises(ValueError):
                refuse_nonfalse_authority(flags)
    with pytest.raises(ValueError):
        refuse_nonfalse_authority({"rank_authority": True})
    with pytest.raises(ValueError):
        refuse_nonfalse_authority(["rank_authority"])


def test_a18_authority_flags_frozen_and_false():
    assert set(AUTHORITY_FLAGS) == set(FLAG_NAMES)
    for name in FLAG_NAMES:
        assert AUTHORITY_FLAGS[name] is False
    with pytest.raises(TypeError):
        AUTHORITY_FLAGS["rank_authority"] = True
    allow_spy = _LoaderSpy()
    allowed = _gate(_request(), _entitlement(), allow_spy)
    _assert_allowed(allowed)
    assert allowed.authority_flags is AUTHORITY_FLAGS
    deny_spy = _LoaderSpy()
    refused = _gate(_request(), None, deny_spy)
    _assert_refused(refused, deny_spy, "ENTITLEMENT_MISSING")
    assert refused.authority_flags is AUTHORITY_FLAGS


def test_a18_verdict_construction_contract():
    forced = AccessVerdict(allowed=True, reasons=("ENTITLEMENT_REVOKED",))
    assert forced.allowed is False
    assert forced.reasons == ("ENTITLEMENT_REVOKED",)
    assert forced.payload is None
    with pytest.raises(ValueError):
        AccessVerdict(
            allowed=False, reasons=("SURFACE_UNKNOWN",), payload="leaked-text"
        )
    assert "payload" not in repr(AccessVerdict(allowed=True, reasons=()))


# ---------------------------------------------------------------------------
# Static scans of the module source (T4)
# ---------------------------------------------------------------------------


def test_a18_static_scan_module_source():
    source = MODULE_PATH.read_text(encoding="utf-8")
    for code in REASONS:
        assert code in source, code
    assert re.search(r"\b\d{4,5}\.HK\b", source) is None
    for ticker in (
        "BABA",
        "TCEHY",
        "AAPL",
        "MSFT",
        "NVDA",
        "GOOGL",
        "AMZN",
        "META",
        "TSLA",
    ):
        assert ticker not in source, ticker
    for needle in ("datetime.now", "utcnow", "date.today", "time.time", "open("):
        assert needle not in source, needle


def test_a18_no_normalisation_ast():
    source = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden_attr = {"lower", "upper", "casefold", "strip", "replace"}
    attr_hits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in forbidden_attr:
                attr_hits.append((node.lineno, node.func.attr))
    assert attr_hits == [], attr_hits
    import_hits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root == "re" or "identity" in root.casefold() or root == "dataos":
                    import_hits.append((node.lineno, alias.name))
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            root = mod.split(".")[0] if mod else ""
            if root == "re" or "identity" in root.casefold() or root == "dataos":
                import_hits.append((node.lineno, mod))
            if any(a.name == "re" for a in node.names):
                import_hits.append((node.lineno, "re"))
    assert import_hits == [], import_hits


# ---------------------------------------------------------------------------
# Frozen contracts
# ---------------------------------------------------------------------------


def test_a18_reasons_and_surfaces_contract():
    assert SURFACES == ("private", "public")
    assert REASONS == (
        "SURFACE_UNKNOWN",
        "AS_OF_INVALID",
        "PUBLIC_FULL_TEXT_FORBIDDEN",
        "ENTITLEMENT_MISSING",
        "ENTITLEMENT_REF_MISSING",
        "ACCOUNT_MISMATCH",
        "DOCUMENT_NOT_ENTITLED",
        "ENTITLEMENT_NOT_YET_VALID",
        "ENTITLEMENT_EXPIRED",
        "ENTITLEMENT_REVOKED",
    )
    assert len(REASONS) == len(set(REASONS))
