"""M7A mutation-sweep killing tests for two SNI DRAFT guard modules.

SNI-local DRAFT contract tests. They consume owner-supplied opaque identity
strings (Stock Identity / Data OS) and never mint issuer, listing, or
security ids. HISTORICAL-DESCRIPTIVE only: rank_authority, gate_authority,
size_authority, signal_authority, escalation_authority and trade_authority
stay literal False. Fixtures are synthetic.

Each test below kills one mutant from the M7A sweep
(research/single_name_intelligence/reviews/MUTATION_SWEEP_M7A_2026-10-14.md)
that the pre-existing suite (tests/test_sni_counter_relation_guard.py,
tests/test_sni_entitlement_guard.py) did NOT kill. The docstring of each
test names the mutant: file:line and original -> mutated. Every test passes
on unmutated code; against its mutant the cited assertion fails.

This module does not register, validate, or feed a ranker, gate, sizer,
signal, escalation, or trade path. No network, no git access.
"""
from __future__ import annotations

import sys
from dataclasses import FrozenInstanceError
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research" / "single_name_intelligence" / "common"))

import sni_counter_relation_guard as crg  # noqa: E402
import sni_entitlement_guard as eng  # noqa: E402

AS_OF = "2026-02-01T00:00:00+00:00"


def _relation(**overrides):
    """Synthetic owner-sourced counter-relation record (all ids opaque)."""
    record = {
        "relation_id": "owner-rel-1",
        "source_ref": "owner://stock_identity/rel-1",
        "issuer_id": "issr-1",
        "available_at": "2026-01-01T00:00:00+00:00",
        "members": [
            {"listing_id": "L1", "counter_kind": "ordinary", "currency": "HKD"},
            {"listing_id": "L2", "counter_kind": "ads", "currency": "USD"},
        ],
    }
    record.update(overrides)
    return record


def _request():
    return {
        "issuer_id": "issr-1",
        "left_listing_id": "L1",
        "right_listing_id": "L2",
    }


def _entitlement(**overrides):
    """Synthetic Research-Vault-shaped entitlement record (ids opaque)."""
    record = {
        "entitlement_ref": "vault://entitlements/e-1",
        "account_id": "acct-1",
        "document_ids": ["doc-1", "doc-2"],
        "valid_from": "2026-01-01T00:00:00+00:00",
    }
    record.update(overrides)
    return record


def _private_request(**overrides):
    record = {
        "surface": "private",
        "document_id": "doc-1",
        "account_id": "acct-1",
        "want_full_text": True,
    }
    record.update(overrides)
    return record


# ---------------------------------------------------------------- counter_relation


def test_m7a_counter_relation_refuse_nonfalse_authority_2():
    """Kill mutant M7A counter_relation #2
    (sni_counter_relation_guard.py:85-86, delete
    `if not isinstance(flags, Mapping): raise ValueError(...)`) -> `pass`.

    A non-Mapping flags argument must be refused with ValueError (not an
    AttributeError from the later .items() call).
    """
    with pytest.raises(ValueError, match="not a mapping"):
        crg.refuse_nonfalse_authority(["rank_authority"])


def test_m7a_counter_relation__blank_6():
    """Kill mutant M7A counter_relation #6
    (sni_counter_relation_guard.py:126, `return True` -> `return None`)
    in _blank's `value is None` branch.

    A None relation_id is blank: the verdict must carry RELATION_ID_MISSING.
    The mutated _blank(None) returns falsy None, so the reason is dropped
    and the verdict flips to allowed.
    """
    assert crg._blank(None) is True
    verdict = crg.check_counter_relation(
        _request(), [_relation(relation_id=None)], as_of=AS_OF
    )
    assert verdict.reasons == ("RELATION_ID_MISSING",)
    assert verdict.allowed is False
    assert verdict.relation_id is None


def test_m7a_counter_relation__members_11():
    """Kill mutant M7A counter_relation #11
    (sni_counter_relation_guard.py:181, `return ()` -> `return None`)
    in _members' `members is None` branch.

    A relation whose members is None contains no listings at all: the
    verdict must be RELATION_SET_MISSING, not a TypeError while iterating
    the None return value.
    """
    verdict = crg.check_counter_relation(
        _request(), [_relation(members=None)], as_of=AS_OF
    )
    assert verdict.reasons == ("RELATION_SET_MISSING",)
    assert verdict.allowed is False


def test_m7a_counter_relation__blank_17():
    """Kill mutant M7A counter_relation #17
    (sni_counter_relation_guard.py:129, `return False` -> `return None`)
    in _blank's final branch.

    _blank is typed `-> bool`; a non-blank value must yield literal False,
    not a falsy None.
    """
    assert crg._blank("owner-rel-1") is False
    assert crg._blank(0) is False


def test_m7a_counter_relation_refuse_nonfalse_authority_25(monkeypatch):
    """Kill mutant M7A counter_relation #25
    (sni_counter_relation_guard.py:78-82, delete the if-raise inside the
    AUTHORITY_FLAGS loop `if value is not False: raise ValueError(...)`).

    Defense-in-depth contract: if any module authority flag were ever
    non-False, refuse_nonfalse_authority() must refuse even when the
    caller passes no flags of their own.
    """
    monkeypatch.setattr(
        crg, "AUTHORITY_FLAGS", {"rank_authority": True}, raising=True
    )
    with pytest.raises(ValueError, match="authority flag"):
        crg.refuse_nonfalse_authority()


def test_m7a_counter_relation__as_date_27():
    """Kill mutant M7A counter_relation #27
    (sni_counter_relation_guard.py:138, `or` -> `and` in
    `if not isinstance(text, str) or len(text) < 10:`).

    A non-string input must be refused to None, never raise: with `and`
    the mutated guard calls len() on the non-string.
    """
    assert crg._as_date(20260101) is None
    assert crg._as_date(None) is None
    assert crg._as_date(b"2026-01-01") is None


def test_m7a_counter_relation__members_30():
    """Kill mutant M7A counter_relation #30
    (sni_counter_relation_guard.py:182-183, delete
    `if isinstance(members, (str, bytes, Mapping)): raise TypeError(...)`
    "must be a sequence of mappings").

    members as a plain Mapping (or str) must be refused with the
    "sequence of mappings" TypeError, not fall through to per-member
    TypeErrors with a different message.
    """
    with pytest.raises(TypeError, match="sequence of mappings"):
        crg.check_counter_relation(
            _request(),
            [_relation(members={"L1": {"counter_kind": "ordinary"}})],
            as_of=AS_OF,
        )
    with pytest.raises(TypeError, match="sequence of mappings"):
        crg.check_counter_relation(
            _request(), [_relation(members="L1,L2")], as_of=AS_OF
        )


# ------------------------------------------------------------------ entitlement


def test_m7a_entitlement__blank_5():
    """Kill mutant M7A entitlement #5
    (sni_entitlement_guard.py:122, `return False` -> `return None`)
    in _blank's final branch.

    _blank is typed `-> bool`; a non-blank value must yield literal False,
    not a falsy None.
    """
    assert eng._blank("doc-1") is False
    assert eng._blank(0) is False


def test_m7a_entitlement__as_date_8():
    """Kill mutant M7A entitlement #8
    (sni_entitlement_guard.py:138, `10` -> `11` in
    `date.fromisoformat(text[:10])`).

    Only the first 10 characters participate: a 10-char ISO date with a
    trailing suffix still parses to the same calendar date.
    """
    assert eng._as_date("2026-03-04trailing") == date(2026, 3, 4)


def test_m7a_entitlement_gate_access_13():
    """Kill mutant M7A entitlement #13
    (sni_entitlement_guard.py:216-217, delete
    `if not isinstance(request, Mapping): raise TypeError(...)`) -> `pass`.

    A non-Mapping request must be refused with TypeError, not an
    AttributeError from the later request.get(...) calls.
    """
    with pytest.raises(TypeError, match="request must be a Mapping"):
        eng.gate_access(
            ["surface", "private"],
            None,
            as_of=AS_OF,
            loader=lambda document_id: "PAYLOAD",
        )


def test_m7a_entitlement_refuse_nonfalse_authority_15(monkeypatch):
    """Kill mutant M7A entitlement #15
    (sni_entitlement_guard.py:75-79, delete the if-raise inside the
    AUTHORITY_FLAGS loop `if value is not False: raise ValueError(...)`).

    Defense-in-depth contract: if any module authority flag were ever
    non-False, refuse_nonfalse_authority() must refuse even when the
    caller passes no flags of their own.
    """
    monkeypatch.setattr(
        eng, "AUTHORITY_FLAGS", {"trade_authority": True}, raising=True
    )
    with pytest.raises(ValueError, match="authority flag"):
        eng.refuse_nonfalse_authority()


def test_m7a_entitlement__as_date_18():
    """Kill mutant M7A entitlement #18
    (sni_entitlement_guard.py:135, `10` -> `11` in
    `if not isinstance(text, str) or len(text) < 10:`).

    A well-formed 10-character ISO date is not too short: it must parse,
    not refuse to None.
    """
    assert eng._as_date("2026-01-15") == date(2026, 1, 15)


def test_m7a_entitlement__document_entitled_21():
    """Kill mutant M7A entitlement #21
    (sni_entitlement_guard.py:179, `return False` -> `return True` when
    document_ids is not one of list/tuple/frozenset/set).

    A document_ids value that is not a container (here: a bare string)
    is not an entitlement: the verdict must carry DOCUMENT_NOT_ENTITLED,
    stay refused, and never call the loader.
    """
    calls: list[object] = []

    def loader(document_id):
        calls.append(document_id)
        return "PAYLOAD"

    verdict = eng.gate_access(
        _private_request(),
        _entitlement(document_ids="doc-1"),
        as_of=AS_OF,
        loader=loader,
    )
    assert verdict.reasons == ("DOCUMENT_NOT_ENTITLED",)
    assert verdict.allowed is False
    assert calls == []


def test_m7a_entitlement_gate_access_23():
    """Kill mutant M7A entitlement #23
    (sni_entitlement_guard.py:218-219, delete
    `if entitlement is not None and not isinstance(entitlement, Mapping):
    raise TypeError(...)`) -> `pass`.

    A non-None non-Mapping entitlement must be refused with TypeError,
    not an AttributeError from the later entitlement.get(...) calls.
    """
    with pytest.raises(TypeError, match="entitlement must be a Mapping or None"):
        eng.gate_access(
            _private_request(),
            ["entitlement"],
            as_of=AS_OF,
            loader=lambda document_id: "PAYLOAD",
        )


def test_m7a_entitlement_module_24():
    """Kill mutant M7A entitlement #24
    (sni_entitlement_guard.py:92, `@dataclass(frozen=True)` ->
    `@dataclass(frozen=False)` on AccessVerdict).

    An access verdict is immutable: mutating an adjudicated verdict must
    raise FrozenInstanceError.
    """
    verdict = eng.AccessVerdict(allowed=True, reasons=())
    with pytest.raises(FrozenInstanceError):
        verdict.allowed = False


def test_m7a_entitlement__document_entitled_30():
    """Kill mutant M7A entitlement #30
    (sni_entitlement_guard.py:177, `return False` -> `return None`)
    in _document_entitled's blank/non-str branch.

    _document_entitled is typed `-> bool`; a blank or non-string
    document_id must yield literal False, not a falsy None.
    """
    assert eng._document_entitled(None, ["doc-1"]) is False
    assert eng._document_entitled("", ["doc-1"]) is False
    assert eng._document_entitled(123, ["doc-1"]) is False
