"""A07/A08 then-known-view tests: post-cutoff facts cannot enter a view.

SNI-local DRAFT contract tests for the three-clock (publication /
owner-known / retrieval) then-known compiler. They consume owner-supplied
fact records shaped like Company Event/Earnings and Research Vault owner
records; fact ids are caller-supplied opaque strings and are never minted,
folded, stripped, or normalised here. HISTORICAL-DESCRIPTIVE only:
rank_authority, gate_authority, size_authority, signal_authority,
escalation_authority and trade_authority stay literal False. Fixtures are
synthetic.

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

from sni_then_known_guard import (  # noqa: E402
    AUTHORITY_FLAGS,
    EXCLUSION_REASONS,
    REASONS,
    ThenKnownView,
    clock_triplet,
    refuse_nonfalse_authority,
    then_known_view,
)

MODULE_PATH = (
    ROOT
    / "research"
    / "single_name_intelligence"
    / "common"
    / "sni_then_known_guard.py"
)

FLAG_NAMES = (
    "rank_authority",
    "gate_authority",
    "size_authority",
    "signal_authority",
    "escalation_authority",
    "trade_authority",
)

CUTOFF = "2026-06-01T00:00:00+00:00"


class _Omit:
    pass


_OMIT = _Omit()


def _item(**overrides):
    body = {
        "fact_id": "SYN-FACT-1",
        "economic_time": "2026-01-15T00:00:00+00:00",
        "owner_known_at": "2026-03-02T10:05:00+00:00",
        "published_at": "2026-03-01T08:00:00+00:00",
        "retrieved_at": "2026-03-02T11:00:00+00:00",
        "supersedes": None,
        "vintaged": False,
    }
    body.update(overrides)
    drop = [key for key, val in body.items() if val is _OMIT]
    for key in drop:
        del body[key]
    return body


def _trio():
    return [
        _item(fact_id="SYN-FACT-1"),
        _item(fact_id="SYN-FACT-2"),
        _item(fact_id="SYN-FACT-3"),
    ]


def _freeze(reasons):
    found = set(reasons)
    return tuple(code for code in REASONS if code in found)


def _view(items, cutoff=CUTOFF):
    return then_known_view(items, cutoff=cutoff)


def _assert_contract(view):
    assert view.reasons == _freeze(view.reasons)
    assert view.allowed is (not view.reasons)
    assert view.authority_flags is AUTHORITY_FLAGS
    for name in FLAG_NAMES:
        assert view.authority_flags[name] is False


def _assert_allowed(view):
    assert view.allowed is True, view.reasons
    assert view.reasons == ()
    _assert_contract(view)


def _assert_refused(view, *codes):
    assert view.allowed is False, view.reasons
    got = set(view.reasons)
    for code in codes:
        assert code in got, (code, view.reasons)
    # Fail closed: a validation refusal carries no partial view.
    assert view.included == ()
    assert view.excluded == ()
    _assert_contract(view)


# ---------------------------------------------------------------------------
# Positive controls (T1)
# ---------------------------------------------------------------------------


def test_a07g_positive_control_three_items_included_in_order():
    view = _view(_trio())
    _assert_allowed(view)
    assert view.included == ("SYN-FACT-1", "SYN-FACT-2", "SYN-FACT-3")
    assert view.excluded == ()


def test_a07g_positive_control_generator_input():
    view = _view(item for item in _trio())
    _assert_allowed(view)
    assert view.included == ("SYN-FACT-1", "SYN-FACT-2", "SYN-FACT-3")


def test_a07g_reasons_and_exclusion_reasons_frozen_contract():
    assert REASONS == (
        "FACT_ID_MISSING",
        "DUPLICATE_FACT_ID",
        "ECONOMIC_TIME_INVALID",
        "OWNER_KNOWN_INVALID",
        "PUBLISHED_INVALID",
        "RETRIEVED_INVALID",
        "OWNER_KNOWN_BEFORE_PUBLISHED",
        "RETRIEVED_BEFORE_PUBLISHED",
        "SUPERSEDES_UNKNOWN",
        "SUPERSEDES_CYCLE",
    )
    assert EXCLUSION_REASONS == (
        "PUBLISHED_AFTER_CUTOFF",
        "OWNER_KNOWN_AFTER_CUTOFF",
        "RETRIEVED_AFTER_CUTOFF_UNVINTAGED",
        "SUPERSEDED_BY_THEN_KNOWN",
    )
    assert len(REASONS) == len(set(REASONS))
    assert len(EXCLUSION_REASONS) == len(set(EXCLUSION_REASONS))


# ---------------------------------------------------------------------------
# economic_time is never a knowledge clock
# ---------------------------------------------------------------------------


def test_a07g_economic_time_after_cutoff_included():
    items = [_item(fact_id="SYN-FACT-1", economic_time="2026-12-31T00:00:00+00:00")]
    view = _view(items)
    _assert_allowed(view)
    assert view.included == ("SYN-FACT-1",)


def test_a07g_equality_with_cutoff_included_each_clock():
    items = [
        # published == cutoff forces the later clocks to the same instant.
        _item(
            fact_id="SYN-FACT-ALL-EQ",
            published_at=CUTOFF,
            owner_known_at=CUTOFF,
            retrieved_at=CUTOFF,
        ),
        _item(
            fact_id="SYN-FACT-OWNER-EQ",
            published_at="2026-05-01T08:00:00+00:00",
            owner_known_at=CUTOFF,
            retrieved_at="2026-05-01T09:00:00+00:00",
        ),
        _item(
            fact_id="SYN-FACT-RETR-EQ",
            published_at="2026-05-01T08:00:00+00:00",
            owner_known_at="2026-05-01T09:00:00+00:00",
            retrieved_at=CUTOFF,
        ),
    ]
    view = _view(items)
    _assert_allowed(view)
    assert view.included == (
        "SYN-FACT-ALL-EQ",
        "SYN-FACT-OWNER-EQ",
        "SYN-FACT-RETR-EQ",
    )


def test_a07g_mixed_offset_cutoff_equality_included():
    cutoff = "2026-06-01T08:00:00+08:00"
    items = [
        _item(
            fact_id="SYN-FACT-EQ",
            published_at="2026-06-01T00:00:00+00:00",
            owner_known_at="2026-06-01T00:00:00+00:00",
            retrieved_at="2026-06-01T00:00:00+00:00",
        ),
        _item(
            fact_id="SYN-FACT-AFTER",
            published_at="2026-06-01T01:00:00+00:00",
            owner_known_at="2026-06-01T01:00:00+00:00",
            retrieved_at="2026-06-01T01:00:00+00:00",
        ),
    ]
    view = _view(items, cutoff=cutoff)
    _assert_allowed(view)
    assert view.included == ("SYN-FACT-EQ",)
    assert view.excluded == (("SYN-FACT-AFTER", "PUBLISHED_AFTER_CUTOFF"),)


# ---------------------------------------------------------------------------
# vintaged retrieval
# ---------------------------------------------------------------------------


def test_a07g_vintaged_true_retrieved_after_cutoff_included():
    items = [
        _item(
            fact_id="SYN-FACT-1",
            retrieved_at="2026-07-01T11:00:00+00:00",
            vintaged=True,
        )
    ]
    view = _view(items)
    _assert_allowed(view)
    assert view.included == ("SYN-FACT-1",)
    assert view.excluded == ()


def test_a07g_vintaged_int_one_excluded():
    items = [
        _item(
            fact_id="SYN-FACT-1",
            retrieved_at="2026-07-01T11:00:00+00:00",
            vintaged=1,
        )
    ]
    view = _view(items)
    _assert_allowed(view)
    assert view.included == ()
    assert view.excluded == (("SYN-FACT-1", "RETRIEVED_AFTER_CUTOFF_UNVINTAGED"),)


def test_a07g_vintaged_missing_excluded():
    items = [
        _item(fact_id="SYN-FACT-1", retrieved_at="2026-07-01T11:00:00+00:00", vintaged=_OMIT)
    ]
    view = _view(items)
    _assert_allowed(view)
    assert view.excluded == (("SYN-FACT-1", "RETRIEVED_AFTER_CUTOFF_UNVINTAGED"),)


# ---------------------------------------------------------------------------
# Single-flip validation refusals (T2): one field of the positive control
# ---------------------------------------------------------------------------


def test_a07g_flip_fact_id_missing():
    items = _trio()
    items[1]["fact_id"] = None
    _assert_refused(_view(items), "FACT_ID_MISSING")


def test_a07g_flip_duplicate_fact_id():
    items = _trio()
    items[2]["fact_id"] = "SYN-FACT-1"
    _assert_refused(_view(items), "DUPLICATE_FACT_ID")


def test_a07g_flip_economic_time_invalid():
    items = _trio()
    items[0]["economic_time"] = "2026-01-15T00:00:00"
    _assert_refused(_view(items), "ECONOMIC_TIME_INVALID")


def test_a07g_flip_owner_known_invalid():
    items = _trio()
    items[0]["owner_known_at"] = "not-a-timestamp"
    _assert_refused(_view(items), "OWNER_KNOWN_INVALID")


def test_a07g_flip_published_invalid():
    items = _trio()
    del items[0]["published_at"]
    _assert_refused(_view(items), "PUBLISHED_INVALID")


def test_a07g_flip_retrieved_invalid():
    items = _trio()
    items[0]["retrieved_at"] = "2026-13-01T00:00:00+00:00"
    _assert_refused(_view(items), "RETRIEVED_INVALID")


def test_a07g_flip_owner_known_before_published():
    items = _trio()
    items[0]["owner_known_at"] = "2026-02-28T08:00:00+00:00"
    _assert_refused(_view(items), "OWNER_KNOWN_BEFORE_PUBLISHED")


def test_a07g_flip_retrieved_before_published():
    items = _trio()
    items[0]["retrieved_at"] = "2026-02-28T09:00:00+00:00"
    _assert_refused(_view(items), "RETRIEVED_BEFORE_PUBLISHED")


def test_a07g_flip_supersedes_unknown():
    items = _trio()
    items[0]["supersedes"] = "SYN-FACT-404"
    _assert_refused(_view(items), "SUPERSEDES_UNKNOWN")


def test_a07g_flip_supersedes_cycle():
    items = _trio()
    items[0]["supersedes"] = "SYN-FACT-1"
    _assert_refused(_view(items), "SUPERSEDES_CYCLE")


def test_a07g_owner_known_equal_published_allowed():
    stamp = "2026-03-01T08:00:00+00:00"
    items = [_item(fact_id="SYN-FACT-1", owner_known_at=stamp, published_at=stamp)]
    _assert_allowed(_view(items))


def test_a07g_retrieved_equal_published_allowed():
    stamp = "2026-03-01T08:00:00+00:00"
    items = [
        _item(
            fact_id="SYN-FACT-1",
            published_at=stamp,
            owner_known_at=stamp,
            retrieved_at=stamp,
        )
    ]
    _assert_allowed(_view(items))


# ---------------------------------------------------------------------------
# Exclusions
# ---------------------------------------------------------------------------


def test_a07g_excluded_published_after_cutoff():
    items = [
        _item(fact_id="SYN-FACT-OLD"),
        _item(
            fact_id="SYN-FACT-NEW",
            published_at="2026-07-01T08:00:00+00:00",
            owner_known_at="2026-07-01T10:00:00+00:00",
            retrieved_at="2026-07-01T11:00:00+00:00",
        ),
    ]
    view = _view(items)
    _assert_allowed(view)
    assert view.included == ("SYN-FACT-OLD",)
    assert view.excluded == (("SYN-FACT-NEW", "PUBLISHED_AFTER_CUTOFF"),)


def test_a07g_excluded_owner_known_after_cutoff():
    items = [
        _item(
            fact_id="SYN-FACT-1",
            published_at="2026-05-01T08:00:00+00:00",
            owner_known_at="2026-07-01T10:00:00+00:00",
            retrieved_at="2026-07-01T11:00:00+00:00",
            vintaged=True,
        )
    ]
    view = _view(items)
    _assert_allowed(view)
    assert view.included == ()
    assert view.excluded == (("SYN-FACT-1", "OWNER_KNOWN_AFTER_CUTOFF"),)


def test_a07g_excluded_retrieved_after_cutoff_unvintaged():
    items = [
        _item(
            fact_id="SYN-FACT-1",
            published_at="2026-05-01T08:00:00+00:00",
            owner_known_at="2026-05-02T10:00:00+00:00",
            retrieved_at="2026-07-01T11:00:00+00:00",
            vintaged=False,
        )
    ]
    view = _view(items)
    _assert_allowed(view)
    assert view.included == ()
    assert view.excluded == (("SYN-FACT-1", "RETRIEVED_AFTER_CUTOFF_UNVINTAGED"),)


def test_a07g_excluded_superseded_by_then_known():
    items = [
        _item(fact_id="SYN-FACT-OLD"),
        _item(
            fact_id="SYN-FACT-NEW",
            published_at="2026-04-01T08:00:00+00:00",
            owner_known_at="2026-04-02T10:00:00+00:00",
            retrieved_at="2026-04-02T11:00:00+00:00",
            supersedes="SYN-FACT-OLD",
        ),
    ]
    view = _view(items)
    _assert_allowed(view)
    assert view.included == ("SYN-FACT-NEW",)
    assert view.excluded == (("SYN-FACT-OLD", "SUPERSEDED_BY_THEN_KNOWN"),)


def test_a07g_excluded_two_reasons_carries_first():
    items = [
        _item(
            fact_id="SYN-FACT-1",
            published_at="2026-07-01T08:00:00+00:00",
            owner_known_at="2026-07-01T10:00:00+00:00",
            retrieved_at="2026-07-01T11:00:00+00:00",
            vintaged=False,
        )
    ]
    view = _view(items)
    _assert_allowed(view)
    assert view.excluded == (("SYN-FACT-1", "PUBLISHED_AFTER_CUTOFF"),)
    assert view.included == ()


def test_a07g_superseding_after_cutoff_does_not_exclude():
    items = [
        _item(fact_id="SYN-FACT-OLD"),
        _item(
            fact_id="SYN-FACT-LATE",
            published_at="2026-07-01T08:00:00+00:00",
            owner_known_at="2026-07-01T10:00:00+00:00",
            retrieved_at="2026-07-01T11:00:00+00:00",
            supersedes="SYN-FACT-OLD",
        ),
    ]
    view = _view(items)
    _assert_allowed(view)
    assert view.included == ("SYN-FACT-OLD",)
    assert view.excluded == (("SYN-FACT-LATE", "PUBLISHED_AFTER_CUTOFF"),)


def test_a07g_superseding_then_known_excludes():
    items = [
        _item(fact_id="SYN-FACT-OLD"),
        _item(
            fact_id="SYN-FACT-NEW",
            supersedes="SYN-FACT-OLD",
            published_at="2026-04-01T08:00:00+00:00",
            owner_known_at="2026-04-01T10:00:00+00:00",
            retrieved_at="2026-04-01T11:00:00+00:00",
        ),
    ]
    view = _view(items)
    _assert_allowed(view)
    assert view.included == ("SYN-FACT-NEW",)
    assert view.excluded == (("SYN-FACT-OLD", "SUPERSEDED_BY_THEN_KNOWN"),)


def test_a07g_superseded_item_can_still_supersede_noniterative():
    items = [
        _item(fact_id="SYN-FACT-A"),
        _item(fact_id="SYN-FACT-B", supersedes="SYN-FACT-A"),
        _item(
            fact_id="SYN-FACT-C",
            supersedes="SYN-FACT-B",
            published_at="2026-04-01T08:00:00+00:00",
            owner_known_at="2026-04-01T10:00:00+00:00",
            retrieved_at="2026-04-01T11:00:00+00:00",
        ),
    ]
    view = _view(items)
    _assert_allowed(view)
    # One pass: C (then-known) supersedes B; B (itself superseded, but
    # passing the three clock checks) still supersedes A.
    assert view.included == ("SYN-FACT-C",)
    assert view.excluded == (
        ("SYN-FACT-A", "SUPERSEDED_BY_THEN_KNOWN"),
        ("SYN-FACT-B", "SUPERSEDED_BY_THEN_KNOWN"),
    )


def test_a07g_self_supersession_is_cycle():
    items = [_trio()[0], _item(fact_id="SYN-FACT-2", supersedes="SYN-FACT-2")]
    _assert_refused(_view(items), "SUPERSEDES_CYCLE")


def test_a07g_two_item_supersedes_cycle():
    items = [
        _item(fact_id="SYN-FACT-1", supersedes="SYN-FACT-2"),
        _item(fact_id="SYN-FACT-2", supersedes="SYN-FACT-1"),
    ]
    view = _view(items)
    _assert_refused(view, "SUPERSEDES_CYCLE")
    assert view.reasons == ("SUPERSEDES_CYCLE",)


def test_a07g_blank_supersedes_treated_as_absent():
    items = [
        _item(fact_id="SYN-FACT-1", supersedes=None),
        _item(fact_id="SYN-FACT-2", supersedes=""),
    ]
    view = _view(items)
    _assert_allowed(view)
    assert view.included == ("SYN-FACT-1", "SYN-FACT-2")


def test_a07g_duplicate_exact_only_no_folding():
    items = [_item(fact_id="SYN-FACT-1"), _item(fact_id="SYN-FACT-1 ")]
    view = _view(items)
    # FAMILY TEXT RULE v2: a padded fact_id is ABSENT, never a different valid id.
    _assert_refused(view, "FACT_ID_MISSING")


def test_a07g_fail_closed_validation_with_excludable_items():
    items = [
        _item(
            fact_id="SYN-FACT-POST",
            published_at="2026-07-01T08:00:00+00:00",
            owner_known_at="2026-07-01T10:00:00+00:00",
            retrieved_at="2026-07-01T11:00:00+00:00",
        ),
        _item(fact_id=None),
    ]
    view = _view(items)
    _assert_refused(view, "FACT_ID_MISSING")


def test_a07g_included_and_excluded_preserve_input_order():
    items = [
        _item(fact_id="SYN-FACT-3"),
        _item(fact_id="SYN-FACT-1"),
        _item(
            fact_id="SYN-FACT-2",
            published_at="2026-07-01T08:00:00+00:00",
            owner_known_at="2026-07-01T10:00:00+00:00",
            retrieved_at="2026-07-01T11:00:00+00:00",
        ),
        _item(fact_id="SYN-FACT-4"),
    ]
    view = _view(items)
    _assert_allowed(view)
    assert view.included == ("SYN-FACT-3", "SYN-FACT-1", "SYN-FACT-4")
    assert view.excluded == (("SYN-FACT-2", "PUBLISHED_AFTER_CUTOFF"),)


def test_a07g_allowed_true_with_only_exclusions():
    items = [
        _item(
            fact_id="SYN-FACT-POST",
            published_at="2026-07-01T08:00:00+00:00",
            owner_known_at="2026-07-01T10:00:00+00:00",
            retrieved_at="2026-07-01T11:00:00+00:00",
        )
    ]
    view = _view(items)
    assert view.allowed is True
    assert view.reasons == ()
    assert view.excluded == (("SYN-FACT-POST", "PUBLISHED_AFTER_CUTOFF"),)
    empty = _view([])
    assert empty.allowed is True
    assert empty.included == () and empty.excluded == ()


# ---------------------------------------------------------------------------
# clock_triplet
# ---------------------------------------------------------------------------


def test_a07g_clock_triplet_positive():
    triplet = clock_triplet(_item())
    assert len(triplet) == 3
    assert triplet[0].isoformat() == "2026-03-01T08:00:00+00:00"
    assert triplet[1].isoformat() == "2026-03-02T10:05:00+00:00"
    assert triplet[2].isoformat() == "2026-03-02T11:00:00+00:00"
    for value in triplet:
        assert value.tzinfo is not None


def test_a07g_clock_triplet_raises_naive():
    with pytest.raises(ValueError):
        clock_triplet(_item(owner_known_at="2026-03-02T10:05:00"))
    with pytest.raises(ValueError):
        clock_triplet(_item(published_at="2026-03-01"))


def test_a07g_clock_triplet_raises_missing():
    bare = _item()
    del bare["retrieved_at"]
    with pytest.raises(ValueError):
        clock_triplet(bare)
    with pytest.raises(ValueError):
        clock_triplet({})


def test_a07g_clock_triplet_raises_garbage():
    with pytest.raises(ValueError):
        clock_triplet(_item(published_at="garbage"))
    with pytest.raises(ValueError):
        clock_triplet(_item(retrieved_at="2026-13-01T00:00:00+00:00"))


def test_a07g_clock_triplet_non_mapping_raises():
    with pytest.raises(TypeError):
        clock_triplet(["not", "a", "mapping"])


def test_a07g_cutoff_naive_or_garbage_raises():
    with pytest.raises(ValueError):
        _view(_trio(), cutoff="2026-06-01T00:00:00")
    with pytest.raises(ValueError):
        _view(_trio(), cutoff="2026-06-01")
    with pytest.raises(ValueError):
        _view(_trio(), cutoff="not-a-cutoff")


def test_a07g_non_mapping_item_raises():
    with pytest.raises(TypeError):
        _view([_item(), "not-a-mapping"])
    with pytest.raises(TypeError):
        _view("not-an-iterable-of-items")


# ---------------------------------------------------------------------------
# Authority (T3)
# ---------------------------------------------------------------------------


def test_a07g_authority_refuse_nonfalse_true_zero_none_empty():
    refuse_nonfalse_authority()
    refuse_nonfalse_authority(AUTHORITY_FLAGS)
    refuse_nonfalse_authority(dict(AUTHORITY_FLAGS))
    for name in FLAG_NAMES:
        for bad in (True, 0, None, ""):
            flags = dict(AUTHORITY_FLAGS)
            flags[name] = bad
            with pytest.raises(ValueError):
                refuse_nonfalse_authority(flags)


def test_a07g_authority_flags_frozen_false():
    for name in FLAG_NAMES:
        assert AUTHORITY_FLAGS[name] is False
    with pytest.raises(TypeError):
        AUTHORITY_FLAGS["rank_authority"] = True
    allowed_view = _view(_trio())
    refused_view = _view([_item(fact_id=None)])
    assert allowed_view.authority_flags is AUTHORITY_FLAGS
    assert refused_view.authority_flags is AUTHORITY_FLAGS


def test_a07g_view_cannot_carry_partial_view():
    with pytest.raises(ValueError):
        ThenKnownView(
            allowed=False,
            reasons=("FACT_ID_MISSING",),
            included=("SYN-FACT-1",),
            excluded=(),
        )
    with pytest.raises(ValueError):
        ThenKnownView(
            allowed=False,
            reasons=("FACT_ID_MISSING",),
            included=(),
            excluded=(("SYN-FACT-1", "PUBLISHED_AFTER_CUTOFF"),),
        )
    coerced = ThenKnownView(
        allowed=True, reasons=("FACT_ID_MISSING",), included=(), excluded=()
    )
    assert coerced.allowed is False
    assert coerced.reasons == ("FACT_ID_MISSING",)


# ---------------------------------------------------------------------------
# Static scans (T4)
# ---------------------------------------------------------------------------


def test_a07g_static_scan_module_source():
    source = MODULE_PATH.read_text(encoding="utf-8")
    for code in REASONS:
        assert code in source, code
    for code in EXCLUSION_REASONS:
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


def test_a07g_static_scan_no_normalisation_ast():
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
    assert import_hits == [], import_hits
    fn_names = {
        n.name
        for n in ast.walk(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert "clock_triplet" in fn_names
    assert "then_known_view" in fn_names


# ---------------------------------------------------------------------------
# De-dup and order (T5)
# ---------------------------------------------------------------------------


def test_a07g_reasons_dedup_and_order_three():
    items = [
        _item(fact_id="SYN-FACT-A", economic_time="2026-01-15T00:00:00"),
        _item(fact_id="SYN-FACT-B", economic_time="2026-02-15T00:00:00"),
        _item(fact_id="SYN-FACT-C", supersedes="SYN-FACT-404"),
        _item(fact_id="SYN-FACT-D", published_at=None),
    ]
    view = _view(items)
    _assert_refused(view, "ECONOMIC_TIME_INVALID", "SUPERSEDES_UNKNOWN")
    assert view.reasons == (
        "ECONOMIC_TIME_INVALID",
        "PUBLISHED_INVALID",
        "SUPERSEDES_UNKNOWN",
    )
    assert len(view.reasons) == len(set(view.reasons))


# ---------------------------------------------------------------------------
# Adversarial id cases (T6)
# ---------------------------------------------------------------------------


def test_a07g_adversarial_fact_id_trailing_space():
    items = [
        _item(fact_id="SYN-FACT-1"),
        _item(fact_id="SYN-FACT-2", supersedes="SYN-FACT-1 "),
    ]
    _assert_refused(_view(items), "SUPERSEDES_UNKNOWN")


def test_a07g_adversarial_fact_id_case_change():
    items = [
        _item(fact_id="SYN-FACT-1"),
        _item(fact_id="SYN-FACT-2", supersedes="syn-fact-1"),
    ]
    _assert_refused(_view(items), "SUPERSEDES_UNKNOWN")


def test_a07g_adversarial_fact_id_cyrillic_lookalike():
    items = [
        _item(fact_id="SYN-FACT-1"),
        _item(fact_id="SYN-FACT-2", supersedes="SYN-FаCT-1"),
    ]
    view = _view(items)
    _assert_refused(view, "SUPERSEDES_UNKNOWN")
    assert "SYN-FACT-1" != "SYN-FаCT-1"
