"""A36G share-class duplicate guard tests: a pack holding two or more
securities of one issuer is refused unless an owner-declared pair covers
exactly those securities and declares dedup true.

SNI-local DRAFT contract tests. They consume owner-supplied opaque identity
strings (Stock Identity / Data OS) and never mint issuer or security ids.
HISTORICAL-DESCRIPTIVE only: rank_authority, gate_authority, size_authority,
signal_authority, escalation_authority and trade_authority stay literal
False. Fixtures are synthetic.

This module does not register, validate, or feed a ranker, gate, sizer,
signal, escalation, or trade path.
"""
from __future__ import annotations

import ast
import itertools
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research" / "single_name_intelligence" / "common"))

from sni_class_duplicate_guard import (  # noqa: E402
    AUTHORITY_FLAGS,
    REASONS,
    ClassDuplicateVerdict,
    check_class_duplicates,
    refuse_nonfalse_authority,
)

MODULE_PATH = (
    ROOT
    / "research"
    / "single_name_intelligence"
    / "common"
    / "sni_class_duplicate_guard.py"
)

FLAG_NAMES = (
    "rank_authority",
    "gate_authority",
    "size_authority",
    "signal_authority",
    "escalation_authority",
    "trade_authority",
)


class _Omit:
    pass


_OMIT = _Omit()


def _member(**overrides):
    body = {
        "security_id": "SYN-SEC-A",
        "issuer_id": "SYN-ISSUER-1",
        "owner_ref": "SYN-OWNER-X",
    }
    body.update(overrides)
    drop = [key for key, val in body.items() if val is _OMIT]
    for key in drop:
        del body[key]
    return body


def _pair(**overrides):
    body = {
        "pair_id": "SYN-PAIR-1",
        "issuer_id": "SYN-ISSUER-1",
        "security_ids": ("SYN-SEC-A", "SYN-SEC-B"),
        "primary_security_id": "SYN-SEC-A",
        "dedup": True,
        "owner_ref": "SYN-OWNER-X",
    }
    body.update(overrides)
    drop = [key for key, val in body.items() if val is _OMIT]
    for key in drop:
        del body[key]
    return body


def _two_class_pack():
    return [_member(), _member(security_id="SYN-SEC-B")]


def _three_single_pack():
    return [
        _member(),
        _member(security_id="SYN-SEC-B", issuer_id="SYN-ISSUER-2"),
        _member(security_id="SYN-SEC-C", issuer_id="SYN-ISSUER-3"),
    ]


def _assert_contract(verdict: ClassDuplicateVerdict) -> None:
    got = set(verdict.reasons)
    assert got <= set(REASONS), verdict.reasons
    assert list(verdict.reasons) == [code for code in REASONS if code in got]
    assert len(verdict.reasons) == len(got)
    assert verdict.allowed == (verdict.reasons == ())
    if not verdict.allowed:
        assert verdict.counted_security_ids == ()
    assert verdict.authority_flags is AUTHORITY_FLAGS
    for name in FLAG_NAMES:
        assert AUTHORITY_FLAGS[name] is False


def _assert_allowed(verdict: ClassDuplicateVerdict) -> None:
    assert verdict.allowed is True, verdict.reasons
    assert verdict.reasons == ()
    _assert_contract(verdict)


def _assert_refused(verdict: ClassDuplicateVerdict, *codes: str) -> None:
    assert verdict.allowed is False, verdict.reasons
    got = set(verdict.reasons)
    for code in codes:
        assert code in got, (code, verdict.reasons)
    _assert_contract(verdict)


# ---------------------------------------------------------------------------
# T1 positive controls
# ---------------------------------------------------------------------------


def test_a36g_positive_three_single_class_issuers():
    verdict = check_class_duplicates(_three_single_pack(), share_class_pairs=[])
    _assert_allowed(verdict)
    assert verdict.counted_security_ids == ("SYN-SEC-A", "SYN-SEC-B", "SYN-SEC-C")
    assert verdict.duplicate_issuers == ()


def test_a36g_positive_declared_pair_drops_nonprimary():
    verdict = check_class_duplicates(_two_class_pack(), share_class_pairs=[_pair()])
    _assert_allowed(verdict)
    assert verdict.counted_security_ids == ("SYN-SEC-A",)
    assert verdict.duplicate_issuers == ("SYN-ISSUER-1",)


def test_a36g_positive_pair_covering_nothing_ignored():
    foreign = _pair(
        pair_id="SYN-PAIR-9",
        issuer_id="SYN-ISSUER-9",
        security_ids=("SYN-SEC-X", "SYN-SEC-Y"),
        primary_security_id="SYN-SEC-X",
    )
    verdict = check_class_duplicates(_three_single_pack(), share_class_pairs=[foreign])
    _assert_allowed(verdict)
    assert verdict.counted_security_ids == ("SYN-SEC-A", "SYN-SEC-B", "SYN-SEC-C")
    empty_pack = check_class_duplicates([], share_class_pairs=[foreign])
    _assert_refused(empty_pack, "PACK_MISSING")
    assert empty_pack.reasons == ("PACK_MISSING",)


# ---------------------------------------------------------------------------
# T2 one single-flip test per REASONS entry
# ---------------------------------------------------------------------------


def test_a36g_flip_pack_missing():
    for empty in ([], None):
        verdict = check_class_duplicates(empty, share_class_pairs=[_pair()])
        _assert_refused(verdict, "PACK_MISSING")
        assert verdict.reasons == ("PACK_MISSING",)
        assert verdict.duplicate_issuers == ()
        assert verdict.counted_security_ids == ()


def test_a36g_flip_member_unsourced():
    for blank in ("", None):
        pack = [_member(owner_ref=blank), _member(security_id="SYN-SEC-B")]
        verdict = check_class_duplicates(pack, share_class_pairs=[_pair()])
        _assert_refused(verdict, "MEMBER_UNSOURCED")
        assert verdict.reasons == ("MEMBER_UNSOURCED",)


def test_a36g_flip_security_id_missing():
    for blank in ("", None):
        pack = [_member(), _member(security_id=blank)]
        verdict = check_class_duplicates(pack, share_class_pairs=[_pair()])
        _assert_refused(verdict, "SECURITY_ID_MISSING")
        assert "ISSUER_DUPLICATE_UNDECLARED" in verdict.reasons
        assert verdict.duplicate_issuers == ("SYN-ISSUER-1",)


def test_a36g_flip_issuer_id_missing():
    for blank in ("", None):
        pack = [_member(), _member(security_id="SYN-SEC-B", issuer_id=blank)]
        verdict = check_class_duplicates(pack, share_class_pairs=[_pair()])
        _assert_refused(verdict, "ISSUER_ID_MISSING")
        assert verdict.reasons == ("ISSUER_ID_MISSING",)
        assert verdict.duplicate_issuers == ()


def test_a36g_flip_duplicate_security():
    pack = [
        _member(),
        _member(security_id="SYN-SEC-A", issuer_id="SYN-ISSUER-2"),
        _member(security_id="SYN-SEC-C", issuer_id="SYN-ISSUER-3"),
    ]
    verdict = check_class_duplicates(pack, share_class_pairs=[])
    _assert_refused(verdict, "DUPLICATE_SECURITY")
    assert verdict.reasons == ("DUPLICATE_SECURITY",)
    assert verdict.duplicate_issuers == ()
    same_issuer = [_member(), _member(security_id="SYN-SEC-A")]
    dup = check_class_duplicates(same_issuer, share_class_pairs=[])
    _assert_refused(dup, "DUPLICATE_SECURITY", "ISSUER_DUPLICATE_UNDECLARED")
    assert dup.duplicate_issuers == ("SYN-ISSUER-1",)


def test_a36g_flip_pair_unsourced():
    for overrides in ({"pair_id": ""}, {"owner_ref": None}):
        verdict = check_class_duplicates(
            _two_class_pack(), share_class_pairs=[_pair(**overrides)]
        )
        _assert_refused(verdict, "PAIR_UNSOURCED", "ISSUER_DUPLICATE_UNDECLARED")


def test_a36g_flip_pair_invalid():
    for overrides in (
        {"primary_security_id": "SYN-SEC-Z"},
        {"primary_security_id": None},
    ):
        verdict = check_class_duplicates(
            _two_class_pack(), share_class_pairs=[_pair(**overrides)]
        )
        _assert_refused(verdict, "PAIR_INVALID", "ISSUER_DUPLICATE_UNDECLARED")


def test_a36g_flip_issuer_duplicate_undeclared():
    verdict = check_class_duplicates(_two_class_pack(), share_class_pairs=[])
    _assert_refused(verdict, "ISSUER_DUPLICATE_UNDECLARED")
    assert verdict.reasons == ("ISSUER_DUPLICATE_UNDECLARED",)
    assert verdict.duplicate_issuers == ("SYN-ISSUER-1",)
    noncovering = check_class_duplicates(
        _two_class_pack(),
        share_class_pairs=[
            _pair(
                security_ids=("SYN-SEC-A", "SYN-SEC-Z"),
                primary_security_id="SYN-SEC-A",
            )
        ],
    )
    _assert_refused(noncovering, "ISSUER_DUPLICATE_UNDECLARED")
    assert noncovering.reasons == ("ISSUER_DUPLICATE_UNDECLARED",)


def test_a36g_flip_pair_issuer_mismatch():
    verdict = check_class_duplicates(
        _two_class_pack(),
        share_class_pairs=[_pair(issuer_id="SYN-ISSUER-OTHER")],
    )
    _assert_refused(verdict, "PAIR_ISSUER_MISMATCH")
    assert verdict.reasons == ("PAIR_ISSUER_MISMATCH",)
    assert "ISSUER_DUPLICATE_UNDECLARED" not in verdict.reasons


def test_a36g_flip_pair_not_deduplicated():
    verdict = check_class_duplicates(
        _two_class_pack(), share_class_pairs=[_pair(dedup=False)]
    )
    _assert_refused(verdict, "PAIR_NOT_DEDUPLICATED")
    assert verdict.reasons == ("PAIR_NOT_DEDUPLICATED",)


# ---------------------------------------------------------------------------
# Module-specific rules
# ---------------------------------------------------------------------------


def test_a36g_three_classes_one_issuer_refuse():
    pack = [
        _member(),
        _member(security_id="SYN-SEC-B"),
        _member(security_id="SYN-SEC-C"),
    ]
    verdict = check_class_duplicates(pack, share_class_pairs=[_pair()])
    _assert_refused(verdict, "ISSUER_DUPLICATE_UNDECLARED")
    assert verdict.reasons == ("ISSUER_DUPLICATE_UNDECLARED",)
    assert verdict.duplicate_issuers == ("SYN-ISSUER-1",)
    assert verdict.counted_security_ids == ()


def test_a36g_dedup_int_one_refuses():
    verdict = check_class_duplicates(
        _two_class_pack(), share_class_pairs=[_pair(dedup=1)]
    )
    _assert_refused(verdict, "PAIR_NOT_DEDUPLICATED")
    assert verdict.reasons == ("PAIR_NOT_DEDUPLICATED",)


def test_a36g_dedup_string_true_refuses():
    verdict = check_class_duplicates(
        _two_class_pack(), share_class_pairs=[_pair(dedup="true")]
    )
    _assert_refused(verdict, "PAIR_NOT_DEDUPLICATED")
    assert verdict.reasons == ("PAIR_NOT_DEDUPLICATED",)


def test_a36g_dedup_none_refuses():
    verdict = check_class_duplicates(
        _two_class_pack(), share_class_pairs=[_pair(dedup=None)]
    )
    _assert_refused(verdict, "PAIR_NOT_DEDUPLICATED")
    assert verdict.reasons == ("PAIR_NOT_DEDUPLICATED",)


def test_a36g_pair_sids_length_one_invalid():
    short = _pair(security_ids=("SYN-SEC-A",))
    verdict = check_class_duplicates(_two_class_pack(), share_class_pairs=[short])
    _assert_refused(verdict, "PAIR_INVALID", "ISSUER_DUPLICATE_UNDECLARED")
    not_a_container = _pair(security_ids="SYN-SEC-AB")
    strverdict = check_class_duplicates(
        _two_class_pack(), share_class_pairs=[not_a_container]
    )
    _assert_refused(strverdict, "PAIR_INVALID", "ISSUER_DUPLICATE_UNDECLARED")


def test_a36g_pair_sids_length_three_invalid():
    triple = _pair(
        security_ids=("SYN-SEC-A", "SYN-SEC-B", "SYN-SEC-C"),
        primary_security_id="SYN-SEC-A",
    )
    verdict = check_class_duplicates(_two_class_pack(), share_class_pairs=[triple])
    _assert_refused(verdict, "PAIR_INVALID", "ISSUER_DUPLICATE_UNDECLARED")


def test_a36g_pair_sids_equal_strings_invalid():
    equal = _pair(
        security_ids=("SYN-SEC-A", "SYN-SEC-A"),
        primary_security_id="SYN-SEC-A",
    )
    verdict = check_class_duplicates(_two_class_pack(), share_class_pairs=[equal])
    _assert_refused(verdict, "PAIR_INVALID", "ISSUER_DUPLICATE_UNDECLARED")


def test_a36g_permutation_invariance_allowed():
    pack = [
        _member(),
        _member(security_id="SYN-SEC-B"),
        _member(security_id="SYN-SEC-D", issuer_id="SYN-ISSUER-2"),
        _member(security_id="SYN-SEC-E", issuer_id="SYN-ISSUER-2"),
        _member(security_id="SYN-SEC-C", issuer_id="SYN-ISSUER-3"),
    ]
    p1 = _pair()
    p2 = _pair(
        pair_id="SYN-PAIR-2",
        issuer_id="SYN-ISSUER-2",
        security_ids=("SYN-SEC-D", "SYN-SEC-E"),
        primary_security_id="SYN-SEC-D",
    )
    p3 = _pair(
        pair_id="SYN-PAIR-3",
        issuer_id="SYN-ISSUER-9",
        security_ids=("SYN-SEC-X", "SYN-SEC-Y"),
        primary_security_id="SYN-SEC-X",
    )
    base = None
    for perm in itertools.permutations([p1, p2, p3]):
        verdict = check_class_duplicates(pack, share_class_pairs=list(perm))
        _assert_allowed(verdict)
        snapshot = (
            verdict.allowed,
            verdict.reasons,
            verdict.duplicate_issuers,
            verdict.counted_security_ids,
        )
        if base is None:
            base = snapshot
        assert snapshot == base, perm
    assert base == (
        True,
        (),
        ("SYN-ISSUER-1", "SYN-ISSUER-2"),
        ("SYN-SEC-A", "SYN-SEC-D", "SYN-SEC-C"),
    )


def test_a36g_permutation_invariance_refused():
    pack = _two_class_pack()
    p1 = _pair(dedup=False)
    p2 = _pair(pair_id="SYN-PAIR-2", issuer_id="SYN-ISSUER-OTHER")
    p3 = _pair(
        pair_id="SYN-PAIR-3",
        issuer_id="SYN-ISSUER-9",
        security_ids=("SYN-SEC-X", "SYN-SEC-Y"),
        primary_security_id="SYN-SEC-X",
    )
    base = None
    for perm in itertools.permutations([p1, p2, p3]):
        verdict = check_class_duplicates(pack, share_class_pairs=list(perm))
        _assert_refused(verdict, "PAIR_NOT_DEDUPLICATED", "PAIR_ISSUER_MISMATCH")
        snapshot = (
            verdict.allowed,
            verdict.reasons,
            verdict.duplicate_issuers,
            verdict.counted_security_ids,
        )
        if base is None:
            base = snapshot
        assert snapshot == base, perm
    assert base == (
        False,
        ("PAIR_ISSUER_MISMATCH", "PAIR_NOT_DEDUPLICATED"),
        ("SYN-ISSUER-1",),
        (),
    )


def test_a36g_counted_empty_when_refused():
    refused_cases = [
        (_two_class_pack(), []),
        (_two_class_pack(), [_pair(dedup=False)]),
        (None, []),
        ([], []),
        (_two_class_pack(), [_pair(issuer_id="SYN-ISSUER-OTHER")]),
        ([_member(), _member(security_id="SYN-SEC-A")], []),
        ([_member(owner_ref="")], []),
        ([_member(security_id=None)], []),
    ]
    for pack, pairs in refused_cases:
        verdict = check_class_duplicates(pack, share_class_pairs=pairs)
        assert verdict.allowed is False
        assert verdict.counted_security_ids == ()
        _assert_contract(verdict)


def test_a36g_two_duplicated_issuers_need_both_pairs():
    pack = [
        _member(),
        _member(security_id="SYN-SEC-B"),
        _member(security_id="SYN-SEC-D", issuer_id="SYN-ISSUER-2"),
        _member(security_id="SYN-SEC-E", issuer_id="SYN-ISSUER-2"),
    ]
    p1 = _pair()
    p2 = _pair(
        pair_id="SYN-PAIR-2",
        issuer_id="SYN-ISSUER-2",
        security_ids=("SYN-SEC-D", "SYN-SEC-E"),
        primary_security_id="SYN-SEC-D",
    )
    only_one = check_class_duplicates(pack, share_class_pairs=[p1])
    _assert_refused(only_one, "ISSUER_DUPLICATE_UNDECLARED")
    assert only_one.reasons == ("ISSUER_DUPLICATE_UNDECLARED",)
    both = check_class_duplicates(pack, share_class_pairs=[p1, p2])
    _assert_allowed(both)
    assert both.counted_security_ids == ("SYN-SEC-A", "SYN-SEC-D")


def test_a36g_unrelated_invalid_pair_still_refuses():
    invalid = _pair(
        pair_id="SYN-PAIR-9",
        security_ids=("SYN-SEC-X", "SYN-SEC-X"),
        primary_security_id="SYN-SEC-X",
    )
    verdict = check_class_duplicates(_three_single_pack(), share_class_pairs=[invalid])
    _assert_refused(verdict, "PAIR_INVALID")
    assert verdict.reasons == ("PAIR_INVALID",)
    unsourced = _pair(
        pair_id="SYN-PAIR-8",
        issuer_id="SYN-ISSUER-9",
        security_ids=("SYN-SEC-X", "SYN-SEC-Y"),
        primary_security_id="SYN-SEC-X",
        owner_ref="",
    )
    unsourced_verdict = check_class_duplicates(
        _three_single_pack(), share_class_pairs=[unsourced]
    )
    _assert_refused(unsourced_verdict, "PAIR_UNSOURCED")
    assert unsourced_verdict.reasons == ("PAIR_UNSOURCED",)


def test_a36g_duplicate_issuers_sorted_and_populated_when_allowed():
    pack = [
        _member(security_id="SYN-SEC-B", issuer_id="SYN-ISSUER-2"),
        _member(security_id="SYN-SEC-E", issuer_id="SYN-ISSUER-2"),
        _member(security_id="SYN-SEC-A", issuer_id="SYN-ISSUER-1"),
        _member(security_id="SYN-SEC-D", issuer_id="SYN-ISSUER-1"),
    ]
    pairs = [
        _pair(
            security_ids=("SYN-SEC-A", "SYN-SEC-D"),
            primary_security_id="SYN-SEC-A",
        ),
        _pair(
            pair_id="SYN-PAIR-2",
            issuer_id="SYN-ISSUER-2",
            security_ids=("SYN-SEC-B", "SYN-SEC-E"),
            primary_security_id="SYN-SEC-B",
        ),
    ]
    verdict = check_class_duplicates(pack, share_class_pairs=pairs)
    _assert_allowed(verdict)
    assert verdict.duplicate_issuers == ("SYN-ISSUER-1", "SYN-ISSUER-2")
    assert verdict.counted_security_ids == ("SYN-SEC-B", "SYN-SEC-A")


def test_a36g_counted_follows_pack_order():
    pack = [
        _member(security_id="SYN-SEC-B"),
        _member(security_id="SYN-SEC-C", issuer_id="SYN-ISSUER-3"),
        _member(security_id="SYN-SEC-A"),
    ]
    verdict = check_class_duplicates(pack, share_class_pairs=[_pair()])
    _assert_allowed(verdict)
    assert verdict.counted_security_ids == ("SYN-SEC-C", "SYN-SEC-A")


def test_a36g_type_errors_for_malformed_containers():
    with pytest.raises(TypeError):
        check_class_duplicates([_member(), "not-a-mapping"], share_class_pairs=[])
    with pytest.raises(TypeError):
        check_class_duplicates("not-a-pack", share_class_pairs=[])
    with pytest.raises(TypeError):
        check_class_duplicates(
            _three_single_pack(), share_class_pairs=[_pair(), "not-a-mapping"]
        )
    with pytest.raises(TypeError):
        check_class_duplicates(_three_single_pack(), share_class_pairs=_pair())


# ---------------------------------------------------------------------------
# T5 de-dup and order
# ---------------------------------------------------------------------------


def test_a36g_reasons_dedup_and_order():
    pack = [
        _member(owner_ref=""),
        _member(security_id="SYN-SEC-B"),
        _member(security_id=None, issuer_id="SYN-ISSUER-2"),
    ]
    verdict = check_class_duplicates(pack, share_class_pairs=[_pair(pair_id="")])
    _assert_refused(
        verdict,
        "MEMBER_UNSOURCED",
        "SECURITY_ID_MISSING",
        "PAIR_UNSOURCED",
        "ISSUER_DUPLICATE_UNDECLARED",
    )
    assert verdict.reasons == (
        "MEMBER_UNSOURCED",
        "SECURITY_ID_MISSING",
        "PAIR_UNSOURCED",
        "ISSUER_DUPLICATE_UNDECLARED",
    )
    assert len(set(verdict.reasons)) == len(verdict.reasons)
    assert verdict.duplicate_issuers == ("SYN-ISSUER-1",)


# ---------------------------------------------------------------------------
# T3 authority
# ---------------------------------------------------------------------------


def test_a36g_authority_refuse_nonfalse_raises():
    refuse_nonfalse_authority()
    refuse_nonfalse_authority(AUTHORITY_FLAGS)
    refuse_nonfalse_authority(dict(AUTHORITY_FLAGS))
    for bad in (True, 0, None, ""):
        with pytest.raises(ValueError):
            refuse_nonfalse_authority({"rank_authority": bad})
        with pytest.raises(ValueError):
            refuse_nonfalse_authority({name: bad for name in FLAG_NAMES})
    with pytest.raises(ValueError):
        refuse_nonfalse_authority("not-a-mapping")


def test_a36g_authority_flags_frozen():
    with pytest.raises(TypeError):
        AUTHORITY_FLAGS["rank_authority"] = True  # type: ignore[index]
    for name in FLAG_NAMES:
        assert AUTHORITY_FLAGS[name] is False
        assert AUTHORITY_FLAGS[name] is not True
    allowed = check_class_duplicates(_three_single_pack(), share_class_pairs=[])
    assert allowed.authority_flags is AUTHORITY_FLAGS
    refused = check_class_duplicates(_two_class_pack(), share_class_pairs=[])
    assert refused.authority_flags is AUTHORITY_FLAGS


# ---------------------------------------------------------------------------
# T4 static scan of the module source
# ---------------------------------------------------------------------------


def test_a36g_static_scan_module_source():
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
    tree = ast.parse(source)
    forbidden_attr = {"lower", "upper", "casefold", "strip", "replace", "title"}
    attr_hits = [
        (node.lineno, node.func.attr)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in forbidden_attr
    ]
    assert attr_hits == [], attr_hits
    fn_names = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert "check_class_duplicates" in fn_names
    assert "refuse_nonfalse_authority" in fn_names


# ---------------------------------------------------------------------------
# T6 adversarial id cases
# ---------------------------------------------------------------------------


def test_a36g_adversarial_trailing_space_refuses():
    pack = [_member(), _member(security_id="SYN-SEC-B ")]
    verdict = check_class_duplicates(pack, share_class_pairs=[_pair()])
    # FAMILY TEXT RULE v2: a padded security_id is ABSENT, never a
    # different valid id; the undeclared duplicate still refuses.
    _assert_refused(verdict, "SECURITY_ID_MISSING", "ISSUER_DUPLICATE_UNDECLARED")
    assert verdict.reasons == ("SECURITY_ID_MISSING", "ISSUER_DUPLICATE_UNDECLARED")


def test_a36g_adversarial_case_change_refuses():
    pack = [_member(), _member(security_id="syn-sec-b")]
    verdict = check_class_duplicates(pack, share_class_pairs=[_pair()])
    _assert_refused(verdict, "ISSUER_DUPLICATE_UNDECLARED")
    assert verdict.reasons == ("ISSUER_DUPLICATE_UNDECLARED",)


def test_a36g_adversarial_cyrillic_lookalike_refuses():
    cyrillic_a = "SYN-SEC-" + "а"  # U+0430 CYRILLIC SMALL LETTER A
    assert cyrillic_a != "SYN-SEC-a"
    pack = [_member(security_id="SYN-SEC-a"), _member(security_id=cyrillic_a)]
    pair = _pair(
        security_ids=("SYN-SEC-a", "SYN-SEC-b"),
        primary_security_id="SYN-SEC-a",
    )
    verdict = check_class_duplicates(pack, share_class_pairs=[pair])
    _assert_refused(verdict, "ISSUER_DUPLICATE_UNDECLARED")
    assert verdict.reasons == ("ISSUER_DUPLICATE_UNDECLARED",)


# ---------------------------------------------------------------------------
# Contract sweep across cases
# ---------------------------------------------------------------------------


def test_a36g_verdict_contract_across_cases():
    cases = [
        (_three_single_pack(), []),
        (_two_class_pack(), [_pair()]),
        (_two_class_pack(), []),
        (_two_class_pack(), [_pair(dedup=False)]),
        (_two_class_pack(), [_pair(issuer_id="SYN-ISSUER-OTHER")]),
        (_two_class_pack(), [_pair(security_ids=("SYN-SEC-A",))]),
        (_two_class_pack(), [_pair(pair_id="")]),
        ([_member(), _member(security_id="SYN-SEC-A")], []),
        ([_member(), _member(security_id=None)], []),
        ([_member(), _member(issuer_id="")], [_pair()]),
        ([_member(owner_ref="")], [_pair()]),
        ([], []),
        (None, []),
    ]
    for pack, pairs in cases:
        verdict = check_class_duplicates(pack, share_class_pairs=pairs)
        _assert_contract(verdict)
        assert isinstance(verdict, ClassDuplicateVerdict)
