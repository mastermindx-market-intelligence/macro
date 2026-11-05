"""A02G counter-relation guard tests: dual counters without minted ids.

SNI-local DRAFT contract tests. They consume owner-supplied opaque identity
strings (Stock Identity / Data OS) and never mint issuer, listing, or
security ids. HISTORICAL-DESCRIPTIVE only: rank_authority, gate_authority,
size_authority, signal_authority, escalation_authority and trade_authority
stay literal False. Fixtures are synthetic.

This module does not register, validate, or feed a ranker, gate, sizer,
signal, escalation, or trade path.
"""
from __future__ import annotations

import ast
import copy
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research" / "single_name_intelligence" / "common"))

from sni_counter_relation_guard import (  # noqa: E402
    AUTHORITY_FLAGS,
    COUNTER_KINDS,
    REASONS,
    CounterRelationVerdict,
    check_counter_relation,
    refuse_nonfalse_authority,
    relation_key,
)

MODULE_PATH = (
    ROOT
    / "research"
    / "single_name_intelligence"
    / "common"
    / "sni_counter_relation_guard.py"
)

FLAG_NAMES = (
    "rank_authority",
    "gate_authority",
    "size_authority",
    "signal_authority",
    "escalation_authority",
    "trade_authority",
)

LEFT = "SYN-LISTING-a1"
RIGHT = "SYN-LISTING-b1"
THIRD = "SYN-LISTING-c1"
AS_OF = "2026-06-01T00:00:00+00:00"


class _Omit:
    pass


_OMIT = _Omit()


def _request(**overrides):
    body = {
        "issuer_id": "SYN-ISSUER-1",
        "left_listing_id": LEFT,
        "right_listing_id": RIGHT,
    }
    body.update(overrides)
    drop = [key for key, val in body.items() if val is _OMIT]
    for key in drop:
        del body[key]
    return body


def _relation(**overrides):
    body = {
        "relation_id": "SYN-REL-1",
        "issuer_id": "SYN-ISSUER-1",
        "source_ref": "SYN-SRC-1",
        "available_at": "2026-05-01T00:00:00+00:00",
        "members": (
            {"listing_id": LEFT, "counter_kind": "ordinary", "currency": "HKD"},
            {"listing_id": RIGHT, "counter_kind": "ads", "currency": "USD"},
        ),
    }
    body.update(overrides)
    drop = [key for key, val in body.items() if val is _OMIT]
    for key in drop:
        del body[key]
    return body


def _swapped(request):
    return {
        "issuer_id": request.get("issuer_id"),
        "left_listing_id": request.get("right_listing_id"),
        "right_listing_id": request.get("left_listing_id"),
    }


def _assert_contract(verdict: CounterRelationVerdict) -> None:
    assert verdict.reasons == tuple(
        code for code in REASONS if code in set(verdict.reasons)
    )
    assert len(verdict.reasons) == len(set(verdict.reasons))
    for code in verdict.reasons:
        assert code in REASONS, (code, verdict.reasons)
    assert verdict.allowed == (verdict.reasons == ())
    assert verdict.authority_flags is AUTHORITY_FLAGS
    for name in FLAG_NAMES:
        assert verdict.authority_flags[name] is False
        assert verdict.authority_flags[name] is not True


def _assert_refused(verdict: CounterRelationVerdict, *codes: str) -> None:
    assert verdict.allowed is False, verdict
    got = set(verdict.reasons)
    for code in codes:
        assert code in got, (code, verdict.reasons)
    _assert_contract(verdict)


def _assert_allowed(verdict: CounterRelationVerdict) -> None:
    assert verdict.allowed is True, verdict.reasons
    assert verdict.reasons == ()
    _assert_contract(verdict)


# ---------------------------------------------------------------------------
# Single-flip case builders (exactly one field of the positive control flips)
# ---------------------------------------------------------------------------


def _case_same_listing():
    return _request(right_listing_id=LEFT), (_relation(),), AS_OF


def _case_set_missing():
    relation = _relation(
        members=(
            {"listing_id": LEFT, "counter_kind": "ordinary", "currency": "HKD"},
            {"listing_id": THIRD, "counter_kind": "ads", "currency": "USD"},
        )
    )
    return _request(), (relation,), AS_OF


def _case_not_available():
    return (
        _request(),
        (_relation(available_at="2026-07-01T00:00:00+00:00"),),
        AS_OF,
    )


def _case_ambiguous():
    relations = (
        _relation(),
        _relation(relation_id="SYN-REL-2", source_ref="SYN-SRC-2"),
    )
    return _request(), relations, AS_OF


def _case_relation_id_missing():
    return _request(), (_relation(relation_id=""),), AS_OF


def _case_unsourced():
    return _request(), (_relation(source_ref=""),), AS_OF


def _case_issuer_mismatch():
    return _request(), (_relation(issuer_id="SYN-ISSUER-2"),), AS_OF


def _case_duplicate_member():
    relation = _relation(
        members=(
            {"listing_id": LEFT, "counter_kind": "ordinary", "currency": "HKD"},
            {"listing_id": LEFT, "counter_kind": "ordinary", "currency": "HKD"},
            {"listing_id": RIGHT, "counter_kind": "ads", "currency": "USD"},
        )
    )
    return _request(), (relation,), AS_OF


def _case_counter_kind_unknown():
    relation = _relation(
        members=(
            {"listing_id": LEFT, "counter_kind": "ordinary", "currency": "HKD"},
            {"listing_id": RIGHT, "counter_kind": "adr", "currency": "USD"},
        )
    )
    return _request(), (relation,), AS_OF


def _case_currency_undeclared():
    relation = _relation(
        members=(
            {"listing_id": LEFT, "counter_kind": "ordinary", "currency": ""},
            {"listing_id": RIGHT, "counter_kind": "ads", "currency": "USD"},
        )
    )
    return _request(), (relation,), AS_OF


_FLIP_CASES = (
    ("SAME_LISTING", _case_same_listing),
    ("RELATION_SET_MISSING", _case_set_missing),
    ("RELATION_NOT_AVAILABLE_AS_OF", _case_not_available),
    ("AMBIGUOUS_RELATION", _case_ambiguous),
    ("RELATION_ID_MISSING", _case_relation_id_missing),
    ("RELATION_UNSOURCED", _case_unsourced),
    ("ISSUER_MISMATCH", _case_issuer_mismatch),
    ("DUPLICATE_MEMBER", _case_duplicate_member),
    ("COUNTER_KIND_UNKNOWN", _case_counter_kind_unknown),
    ("CURRENCY_UNDECLARED", _case_currency_undeclared),
)


# ---------------------------------------------------------------------------
# T1 positive controls
# ---------------------------------------------------------------------------


def test_a02g_positive_control_allowed():
    verdict = check_counter_relation(_request(), (_relation(),), as_of=AS_OF)
    _assert_allowed(verdict)
    assert verdict.relation_id == "SYN-REL-1"
    assert verdict.allowed is True


def test_a02g_positive_control_swap_identical():
    straight = check_counter_relation(_request(), (_relation(),), as_of=AS_OF)
    swapped = check_counter_relation(_swapped(_request()), (_relation(),), as_of=AS_OF)
    _assert_allowed(straight)
    _assert_allowed(swapped)
    assert straight == swapped


def test_a02g_positive_control_third_relation_absent():
    empty = check_counter_relation(_request(), (), as_of=AS_OF)
    _assert_refused(empty, "RELATION_SET_MISSING")
    assert empty.relation_id is None


# ---------------------------------------------------------------------------
# T2 one dedicated single-flip test per REASONS entry
# ---------------------------------------------------------------------------


def test_a02g_flip_same_listing():
    request, relations, as_of = _case_same_listing()
    verdict = check_counter_relation(request, relations, as_of=as_of)
    _assert_refused(verdict, "SAME_LISTING")
    assert verdict.reasons == ("SAME_LISTING",)
    assert verdict.relation_id is None


def test_a02g_flip_relation_set_missing():
    request, relations, as_of = _case_set_missing()
    verdict = check_counter_relation(request, relations, as_of=as_of)
    _assert_refused(verdict, "RELATION_SET_MISSING")
    assert verdict.reasons == ("RELATION_SET_MISSING",)
    assert verdict.relation_id is None


def test_a02g_flip_relation_not_available_as_of():
    request, relations, as_of = _case_not_available()
    verdict = check_counter_relation(request, relations, as_of=as_of)
    _assert_refused(verdict, "RELATION_NOT_AVAILABLE_AS_OF")
    assert verdict.reasons == ("RELATION_NOT_AVAILABLE_AS_OF",)
    assert verdict.relation_id == "SYN-REL-1"


def test_a02g_flip_ambiguous_relation():
    request, relations, as_of = _case_ambiguous()
    verdict = check_counter_relation(request, relations, as_of=as_of)
    _assert_refused(verdict, "AMBIGUOUS_RELATION")
    assert verdict.reasons == ("AMBIGUOUS_RELATION",)
    assert verdict.relation_id is None
    reversed_order = check_counter_relation(
        request, tuple(reversed(relations)), as_of=as_of
    )
    assert reversed_order == verdict


def test_a02g_flip_relation_id_missing():
    request, relations, as_of = _case_relation_id_missing()
    verdict = check_counter_relation(request, relations, as_of=as_of)
    _assert_refused(verdict, "RELATION_ID_MISSING")
    assert verdict.reasons == ("RELATION_ID_MISSING",)
    assert verdict.relation_id is None


def test_a02g_flip_relation_unsourced():
    request, relations, as_of = _case_unsourced()
    verdict = check_counter_relation(request, relations, as_of=as_of)
    _assert_refused(verdict, "RELATION_UNSOURCED")
    assert verdict.reasons == ("RELATION_UNSOURCED",)
    assert verdict.relation_id == "SYN-REL-1"


def test_a02g_flip_issuer_mismatch():
    request, relations, as_of = _case_issuer_mismatch()
    verdict = check_counter_relation(request, relations, as_of=as_of)
    _assert_refused(verdict, "ISSUER_MISMATCH")
    assert verdict.reasons == ("ISSUER_MISMATCH",)
    assert verdict.relation_id == "SYN-REL-1"


def test_a02g_flip_duplicate_member():
    request, relations, as_of = _case_duplicate_member()
    verdict = check_counter_relation(request, relations, as_of=as_of)
    _assert_refused(verdict, "DUPLICATE_MEMBER")
    assert verdict.reasons == ("DUPLICATE_MEMBER",)


def test_a02g_flip_counter_kind_unknown():
    request, relations, as_of = _case_counter_kind_unknown()
    verdict = check_counter_relation(request, relations, as_of=as_of)
    _assert_refused(verdict, "COUNTER_KIND_UNKNOWN")
    assert verdict.reasons == ("COUNTER_KIND_UNKNOWN",)


def test_a02g_flip_currency_undeclared():
    request, relations, as_of = _case_currency_undeclared()
    verdict = check_counter_relation(request, relations, as_of=as_of)
    _assert_refused(verdict, "CURRENCY_UNDECLARED")
    assert verdict.reasons == ("CURRENCY_UNDECLARED",)


# ---------------------------------------------------------------------------
# Swap symmetry over every single-flip case
# ---------------------------------------------------------------------------


def test_a02g_swap_symmetry_all_single_flips():
    assert len(_FLIP_CASES) == len(REASONS)
    for code, builder in _FLIP_CASES:
        request, relations, as_of = builder()
        straight = check_counter_relation(request, relations, as_of=as_of)
        flipped = check_counter_relation(
            _swapped(request), relations, as_of=as_of
        )
        _assert_refused(straight, code)
        _assert_refused(flipped, code)
        assert straight == flipped, (code, straight, flipped)


# ---------------------------------------------------------------------------
# relation_key ordering
# ---------------------------------------------------------------------------


def test_a02g_relation_key_orders_without_altering():
    assert relation_key(RIGHT, LEFT) == (LEFT, RIGHT)
    assert relation_key(LEFT, RIGHT) == (LEFT, RIGHT)
    assert relation_key(LEFT, LEFT) == (LEFT, LEFT)
    key = relation_key("SYN-LISTING-b1 ", "SYN-LISTING-a1")
    assert isinstance(key, tuple)
    assert len(key) == 2
    assert key == ("SYN-LISTING-a1", "SYN-LISTING-b1 ")
    assert key[1] == "SYN-LISTING-b1 "
    assert relation_key("SYN-LISTING-a1 ", LEFT) == (LEFT, "SYN-LISTING-a1 ")


def test_a02g_relation_key_symmetric():
    for a, b in (
        (LEFT, RIGHT),
        (RIGHT, LEFT),
        (THIRD, LEFT),
        ("SYN-LISTING-b1 ", LEFT),
    ):
        assert relation_key(a, b) == relation_key(b, a)


# ---------------------------------------------------------------------------
# Third listing in the relation
# ---------------------------------------------------------------------------


def test_a02g_third_listing_leaves_pair_verdict_unchanged():
    two = check_counter_relation(_request(), (_relation(),), as_of=AS_OF)
    _assert_allowed(two)
    relation = _relation(
        members=(
            {"listing_id": LEFT, "counter_kind": "ordinary", "currency": "HKD"},
            {"listing_id": RIGHT, "counter_kind": "ads", "currency": "USD"},
            {"listing_id": THIRD, "counter_kind": "ordinary", "currency": "CNY"},
        )
    )
    three = check_counter_relation(_request(), (relation,), as_of=AS_OF)
    _assert_allowed(three)
    assert three == two
    pair_with_third = check_counter_relation(
        _request(right_listing_id=THIRD), (relation,), as_of=AS_OF
    )
    _assert_allowed(pair_with_third)
    assert pair_with_third.relation_id == "SYN-REL-1"


# ---------------------------------------------------------------------------
# Availability edge cases
# ---------------------------------------------------------------------------


def test_a02g_not_available_missing_available_at():
    verdict = check_counter_relation(
        _request(), (_relation(available_at=_OMIT),), as_of=AS_OF
    )
    _assert_refused(verdict, "RELATION_NOT_AVAILABLE_AS_OF")


def test_a02g_not_available_naive_available_at():
    verdict = check_counter_relation(
        _request(),
        (_relation(available_at="2026-05-01T00:00:00"),),
        as_of=AS_OF,
    )
    _assert_refused(verdict, "RELATION_NOT_AVAILABLE_AS_OF")


def test_a02g_not_available_date_only_available_at():
    verdict = check_counter_relation(
        _request(), (_relation(available_at="2026-05-01"),), as_of=AS_OF
    )
    _assert_refused(verdict, "RELATION_NOT_AVAILABLE_AS_OF")


def test_a02g_not_available_naive_as_of():
    verdict = check_counter_relation(
        _request(), (_relation(),), as_of="2026-06-01T00:00:00"
    )
    _assert_refused(verdict, "RELATION_NOT_AVAILABLE_AS_OF")


def test_a02g_available_equal_as_of_allowed():
    exact = check_counter_relation(
        _request(),
        (_relation(available_at="2026-06-01T00:00:00+00:00"),),
        as_of=AS_OF,
    )
    _assert_allowed(exact)
    offset_equivalent = check_counter_relation(
        _request(),
        (_relation(available_at="2026-06-01T02:00:00+02:00"),),
        as_of=AS_OF,
    )
    _assert_allowed(offset_equivalent)


# ---------------------------------------------------------------------------
# Blank ids and unknown kinds
# ---------------------------------------------------------------------------


def test_a02g_blank_counter_kind_unknown():
    relation = _relation(
        members=(
            {"listing_id": LEFT, "counter_kind": "ordinary", "currency": "HKD"},
            {"listing_id": RIGHT, "counter_kind": "", "currency": "USD"},
        )
    )
    verdict = check_counter_relation(_request(), (relation,), as_of=AS_OF)
    _assert_refused(verdict, "COUNTER_KIND_UNKNOWN")


def test_a02g_blank_listing_ids_refuse():
    both_none = check_counter_relation(
        _request(left_listing_id=None, right_listing_id=None),
        (_relation(),),
        as_of=AS_OF,
    )
    _assert_refused(both_none, "SAME_LISTING")
    both_blank = check_counter_relation(
        _request(left_listing_id="", right_listing_id=""),
        (_relation(),),
        as_of=AS_OF,
    )
    _assert_refused(both_blank, "SAME_LISTING")
    one_blank = check_counter_relation(
        _request(left_listing_id=None), (_relation(),), as_of=AS_OF
    )
    _assert_refused(one_blank, "RELATION_SET_MISSING")


def test_a02g_blank_request_issuer_mismatch():
    verdict = check_counter_relation(
        _request(issuer_id=""), (_relation(),), as_of=AS_OF
    )
    _assert_refused(verdict, "ISSUER_MISMATCH")
    verdict_none = check_counter_relation(
        _request(issuer_id=None), (_relation(),), as_of=AS_OF
    )
    _assert_refused(verdict_none, "ISSUER_MISMATCH")


# ---------------------------------------------------------------------------
# T5 de-dup and order
# ---------------------------------------------------------------------------


def test_a02g_multiple_reasons_order_and_dedup():
    relation = _relation(
        source_ref="",
        issuer_id="SYN-ISSUER-2",
        members=(
            {"listing_id": LEFT, "counter_kind": "adr", "currency": ""},
            {"listing_id": RIGHT, "counter_kind": "warrant", "currency": None},
        ),
    )
    verdict = check_counter_relation(_request(), (relation,), as_of=AS_OF)
    _assert_refused(
        verdict,
        "RELATION_UNSOURCED",
        "ISSUER_MISMATCH",
        "COUNTER_KIND_UNKNOWN",
        "CURRENCY_UNDECLARED",
    )
    assert verdict.reasons == (
        "RELATION_UNSOURCED",
        "ISSUER_MISMATCH",
        "COUNTER_KIND_UNKNOWN",
        "CURRENCY_UNDECLARED",
    )
    assert len(verdict.reasons) == len(set(verdict.reasons))


# ---------------------------------------------------------------------------
# T6 adversarial id cases
# ---------------------------------------------------------------------------


def test_a02g_adversarial_trailing_space():
    verdict = check_counter_relation(
        _request(right_listing_id="SYN-LISTING-b1 "), (_relation(),), as_of=AS_OF
    )
    _assert_refused(verdict, "RELATION_SET_MISSING")


def test_a02g_adversarial_case_change():
    verdict = check_counter_relation(
        _request(right_listing_id="SYN-LISTING-B1"), (_relation(),), as_of=AS_OF
    )
    _assert_refused(verdict, "RELATION_SET_MISSING")


def test_a02g_adversarial_cyrillic_lookalike():
    lookalike = "SYN-LISTING-а1"
    assert lookalike != LEFT
    assert ord(lookalike[-2]) == 0x0430
    verdict = check_counter_relation(
        _request(left_listing_id=lookalike), (_relation(),), as_of=AS_OF
    )
    _assert_refused(verdict, "RELATION_SET_MISSING")


def test_a02g_adversarial_member_side_variant():
    spaced = _relation(
        members=(
            {"listing_id": LEFT, "counter_kind": "ordinary", "currency": "HKD"},
            {"listing_id": "SYN-LISTING-b1 ", "counter_kind": "ads", "currency": "USD"},
        )
    )
    verdict = check_counter_relation(_request(), (spaced,), as_of=AS_OF)
    _assert_refused(verdict, "RELATION_SET_MISSING")
    lookalike = "SYN-LISTING-а1"
    cyrillic_member = _relation(
        members=(
            {"listing_id": lookalike, "counter_kind": "ordinary", "currency": "HKD"},
            {"listing_id": RIGHT, "counter_kind": "ads", "currency": "USD"},
        )
    )
    verdict_cyr = check_counter_relation(_request(), (cyrillic_member,), as_of=AS_OF)
    _assert_refused(verdict_cyr, "RELATION_SET_MISSING")


# ---------------------------------------------------------------------------
# T3 authority
# ---------------------------------------------------------------------------


def test_a02g_authority_refuse_nonfalse():
    refuse_nonfalse_authority()
    refuse_nonfalse_authority(AUTHORITY_FLAGS)
    refuse_nonfalse_authority(dict(AUTHORITY_FLAGS))
    for bad in (True, 0, None, ""):
        with pytest.raises(ValueError):
            refuse_nonfalse_authority({"rank_authority": bad})
    with pytest.raises(ValueError):
        refuse_nonfalse_authority({"trade_authority": True})


def test_a02g_authority_flags_frozen():
    with pytest.raises(TypeError):
        AUTHORITY_FLAGS["rank_authority"] = True
    for name in FLAG_NAMES:
        assert AUTHORITY_FLAGS[name] is False
        assert AUTHORITY_FLAGS[name] is not True
    verdict = check_counter_relation(_request(), (_relation(),), as_of=AS_OF)
    assert verdict.authority_flags is AUTHORITY_FLAGS


def test_a02g_verdict_allowed_iff_reasons_empty():
    clean = CounterRelationVerdict(
        allowed=True, reasons=(), relation_id="SYN-REL-1"
    )
    assert clean.allowed is True
    forced = CounterRelationVerdict(
        allowed=True, reasons=("SAME_LISTING",), relation_id=None
    )
    assert forced.allowed is False
    with pytest.raises(ValueError):
        CounterRelationVerdict(
            allowed=False, reasons=("NOT_A_REASON",), relation_id=None
        )


# ---------------------------------------------------------------------------
# T4 static scans
# ---------------------------------------------------------------------------


def test_a02g_static_scan_module_source():
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
    for banned in ("datetime.now", "utcnow", "date.today", "time.time", "open("):
        assert banned not in source, banned


def test_a02g_static_scan_no_normalisation():
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
    fn_names = {
        n.name
        for n in ast.walk(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert "check_counter_relation" in fn_names
    assert "relation_key" in fn_names


# ---------------------------------------------------------------------------
# Never mints, never mutates
# ---------------------------------------------------------------------------


def test_a02g_never_mints_ids_or_mutates_inputs():
    request = _request()
    relation = _relation()
    request_copy = copy.deepcopy(request)
    relation_copy = copy.deepcopy(relation)
    verdict = check_counter_relation(request, (relation,), as_of=AS_OF)
    _assert_allowed(verdict)
    assert verdict.relation_id == "SYN-REL-1"
    assert request == request_copy
    assert relation == relation_copy
    refused = check_counter_relation(
        _request(), (_relation(relation_id="", source_ref=""),), as_of=AS_OF
    )
    _assert_refused(refused, "RELATION_ID_MISSING", "RELATION_UNSOURCED")
    assert refused.relation_id is None
    missing = check_counter_relation(
        _request(right_listing_id="SYN-LISTING-zz"), (_relation(),), as_of=AS_OF
    )
    _assert_refused(missing, "RELATION_SET_MISSING")
    assert missing.relation_id is None


def test_a02g_malformed_inputs_raise_typeerror():
    with pytest.raises(TypeError):
        check_counter_relation("not-a-mapping", (_relation(),), as_of=AS_OF)
    with pytest.raises(TypeError):
        check_counter_relation(_request(), ("not-a-relation",), as_of=AS_OF)
    with pytest.raises(TypeError):
        check_counter_relation(_request(), None, as_of=AS_OF)
    with pytest.raises(TypeError):
        check_counter_relation(_request(), "not-relations", as_of=AS_OF)
    bad_member = _relation(members=(("not-a-mapping",), {"listing_id": LEFT}))
    with pytest.raises(TypeError):
        check_counter_relation(_request(), (bad_member,), as_of=AS_OF)


# ---------------------------------------------------------------------------
# Frozen constants
# ---------------------------------------------------------------------------


def test_a02g_frozen_constants():
    assert REASONS == (
        "SAME_LISTING",
        "RELATION_SET_MISSING",
        "RELATION_NOT_AVAILABLE_AS_OF",
        "AMBIGUOUS_RELATION",
        "RELATION_ID_MISSING",
        "RELATION_UNSOURCED",
        "ISSUER_MISMATCH",
        "DUPLICATE_MEMBER",
        "COUNTER_KIND_UNKNOWN",
        "CURRENCY_UNDECLARED",
    )
    assert COUNTER_KINDS == ("ordinary", "ads")
    assert len(REASONS) == len(set(REASONS))
    assert AUTHORITY_FLAGS == dict.fromkeys(FLAG_NAMES, False)
