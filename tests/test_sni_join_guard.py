"""A09 join-guard tests: mismatched joins are refused with named reasons.

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
import copy
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research" / "single_name_intelligence" / "common"))

from sni_join_guard import (  # noqa: E402
    AUTHORITY_FLAGS,
    FACT_FIELDS,
    REASONS,
    JoinVerdict,
    check_join,
    refuse_nonfalse_authority,
    validate_fact,
)

MODULE_PATH = (
    ROOT
    / "research"
    / "single_name_intelligence"
    / "common"
    / "sni_join_guard.py"
)

FLAG_NAMES = (
    "rank_authority",
    "gate_authority",
    "size_authority",
    "signal_authority",
    "escalation_authority",
    "trade_authority",
)


def _base_fact(**overrides):
    fact = {
        "issuer_id": "SYN-ISSUER-1",
        "level": "issuer",
        "metric": "net_income",
        "period_type": "annual",
        "period_start": "2025-04-01",
        "period_end": "2026-03-31",
        "basis": "reported",
        "currency": "CNY",
        "source_reported_currency": "CNY",
        "scale": 0,
        "share_denominator": "NOT_PER_SHARE",
        "version": "v1",
        "known_at": "2026-05-13T17:30:00",
        "source_owner": "SYN-OWNER-A",
        "value": 100,
    }
    fact.update(overrides)
    drop = [key for key, val in fact.items() if val is _OMIT]
    for key in drop:
        del fact[key]
    return fact


class _Omit:
    pass


_OMIT = _Omit()


def _sec(**overrides):
    body = {
        "level": "security",
        "counter_id": "SYN-CTR-A",
    }
    body.update(overrides)
    return _base_fact(**body)


def _bare_reason(reason: str) -> str:
    if reason.startswith("LEFT:"):
        reason = reason[5:]
    elif reason.startswith("RIGHT:"):
        reason = reason[6:]
    if reason.startswith("SCHEMA_UNKNOWN_FIELD"):
        return "SCHEMA_UNKNOWN_FIELD"
    return reason


def _codes(verdict: JoinVerdict) -> tuple[str, ...]:
    return tuple(_bare_reason(r) for r in verdict.reasons)


def _assert_contract(verdict: JoinVerdict) -> None:
    for code in _codes(verdict):
        assert code in REASONS, (code, verdict.reasons)
    for name in FLAG_NAMES:
        assert verdict.authority[name] is False
        assert verdict.authority[name] is not True
    if verdict.status == "ALLOWED":
        assert verdict.reasons == ()
    else:
        assert verdict.status == "REFUSED"
        assert verdict.reasons


def _assert_refused(verdict: JoinVerdict, *codes: str) -> None:
    assert verdict.status == "REFUSED", verdict
    got = set(_codes(verdict))
    for code in codes:
        assert code in got, (code, verdict.reasons)
    _assert_contract(verdict)


def _assert_allowed(verdict: JoinVerdict) -> None:
    assert verdict.status == "ALLOWED", verdict.reasons
    assert verdict.reasons == ()
    _assert_contract(verdict)


def _stripped(reasons: tuple[str, ...]) -> tuple[str, ...]:
    out = []
    for reason in reasons:
        if reason.startswith("LEFT:"):
            out.append(reason[5:])
        elif reason.startswith("RIGHT:"):
            out.append(reason[6:])
        else:
            out.append(reason)
    return tuple(sorted(out))


# ---------------------------------------------------------------------------
# E1-P1 / E2-1 mismatched denominator
# ---------------------------------------------------------------------------


def test_a09_e1p1_e2p1_denominator_mismatch():
    left = _base_fact(share_denominator="BASIC")
    right = _base_fact(share_denominator="DILUTED", source_owner="SYN-OWNER-B")
    verdict = check_join(left, right, join_kind="same_fact")
    _assert_refused(verdict, "DENOMINATOR_MISMATCH")
    assert validate_fact(left) == ()
    assert validate_fact(right) == ()


def test_a09_e1p1_e2p1_denominator_uncarried():
    left = _base_fact(share_denominator=_OMIT)
    right = _base_fact()
    verdict = check_join(left, right, join_kind="same_fact")
    _assert_refused(verdict, "DENOMINATOR_UNCARRIED")
    assert "DENOMINATOR_UNCARRIED" in validate_fact(left)


def test_a09_e1p1_e2p1_ads_ratio_missing():
    left = _base_fact(share_denominator="ADS", ads_ratio=_OMIT)
    right = _base_fact(share_denominator="ADS", ads_ratio=5, source_owner="SYN-OWNER-B")
    verdict = check_join(left, right, join_kind="same_fact")
    _assert_refused(verdict, "ADS_RATIO_MISSING")
    assert "ADS_RATIO_MISSING" in validate_fact(left)


def test_a09_e1p1_e2p1_ads_ratio_mismatch():
    left = _base_fact(share_denominator="ADS", ads_ratio=5)
    right = _base_fact(
        share_denominator="ADS", ads_ratio=10, source_owner="SYN-OWNER-B"
    )
    verdict = check_join(left, right, join_kind="same_fact")
    _assert_refused(verdict, "ADS_RATIO_MISMATCH")
    assert validate_fact(left) == ()
    assert validate_fact(right) == ()


# ---------------------------------------------------------------------------
# E1-P2 / E2-2 repeated report / two stores, no version key
# ---------------------------------------------------------------------------


def test_a09_e1p2_e2p2_version_conflict():
    left = _base_fact(version="v1")
    right = _base_fact(version="v2", source_owner="SYN-OWNER-B")
    verdict = check_join(left, right, join_kind="same_fact")
    _assert_refused(verdict, "VERSION_CONFLICT")


def test_a09_e1p2_e2p2_equal_version_equal_value_allowed():
    left = _base_fact(version="v1", value=100, source_owner="SYN-OWNER-A")
    right = _base_fact(version="v1", value=100, source_owner="SYN-OWNER-B")
    verdict = check_join(left, right, join_kind="same_fact")
    _assert_allowed(verdict)


def test_a09_e1p2_e2p2_value_conflict():
    left = _base_fact(version="v1", value=100)
    right = _base_fact(version="v1", value=200, source_owner="SYN-OWNER-B")
    verdict = check_join(left, right, join_kind="same_fact")
    _assert_refused(verdict, "VALUE_CONFLICT")


def test_a09_e1p2_e2p2_supersedes_allowed():
    left = _base_fact(version="v1", value=100)
    right = _base_fact(
        version="v2",
        supersedes="v1",
        value=110,
        source_owner="SYN-OWNER-B",
    )
    verdict = check_join(left, right, join_kind="same_fact")
    _assert_allowed(verdict)
    swapped = check_join(right, left, join_kind="same_fact")
    _assert_allowed(swapped)


def test_a09_e1p2_e2p2_version_unknown():
    left = _base_fact(version=_OMIT)
    right = _base_fact(version=_OMIT, source_owner="SYN-OWNER-B")
    verdict = check_join(left, right, join_kind="same_fact")
    _assert_refused(verdict, "VERSION_UNKNOWN")
    assert "VERSION_UNKNOWN" in validate_fact(left)


# ---------------------------------------------------------------------------
# E1-P3 / E2-3 segment recast
# ---------------------------------------------------------------------------


def test_a09_e1p3_e2p3_segment_scheme_mismatch():
    left = _base_fact(segment="cloud", segment_scheme_version="sch-1")
    right = _base_fact(
        segment="cloud",
        segment_scheme_version="sch-2",
        source_owner="SYN-OWNER-B",
    )
    verdict = check_join(left, right, join_kind="same_fact")
    _assert_refused(verdict, "SEGMENT_SCHEME_MISMATCH")


def test_a09_e1p3_e2p3_segment_scheme_unknown():
    left = _base_fact(segment="cloud", segment_scheme_version=_OMIT)
    right = _base_fact(
        segment="cloud", segment_scheme_version="sch-1", source_owner="SYN-OWNER-B"
    )
    verdict = check_join(left, right, join_kind="same_fact")
    _assert_refused(verdict, "SEGMENT_SCHEME_UNKNOWN")
    assert "SEGMENT_SCHEME_UNKNOWN" in validate_fact(left)


def test_a09_e1p3_e2p3_time_series_recast_refused():
    left = _base_fact(
        segment="cloud",
        segment_scheme_version="sch-1",
        period_end="2025-03-31",
        period_start="2024-04-01",
        known_at="2025-05-13T17:30:00",
    )
    right = _base_fact(
        segment="cloud",
        segment_scheme_version="sch-2",
        period_end="2026-03-31",
        period_start="2025-04-01",
        source_owner="SYN-OWNER-B",
    )
    verdict = check_join(left, right, join_kind="time_series")
    _assert_refused(verdict, "SEGMENT_SCHEME_MISMATCH")
    assert "PERIOD_MISMATCH" not in _codes(verdict)


# ---------------------------------------------------------------------------
# E1-P4 / E2-4 late filing
# ---------------------------------------------------------------------------


def test_a09_e1p4_e2p4_period_end_missing():
    left = _base_fact(period_end=_OMIT)
    right = _base_fact()
    verdict = check_join(left, right, join_kind="same_fact")
    _assert_refused(verdict, "PERIOD_END_MISSING")
    assert "PERIOD_END_MISSING" in validate_fact(left)


def test_a09_e1p4_e2p4_timestamp_incoherent():
    left = _base_fact(
        period_end="2026-06-30",
        known_at="2026-06-01T00:00:00",
    )
    right = copy.deepcopy(left)
    right["source_owner"] = "SYN-OWNER-B"
    verdict = check_join(left, right, join_kind="same_fact")
    _assert_refused(verdict, "TIMESTAMP_INCOHERENT")
    assert "TIMESTAMP_INCOHERENT" in validate_fact(left)


def test_a09_e1p4_e2p4_not_known_as_of():
    left = _base_fact(
        period_end="2026-06-30",
        known_at="2026-08-12T16:31:00",
    )
    right = copy.deepcopy(left)
    right["source_owner"] = "SYN-OWNER-B"
    verdict = check_join(left, right, join_kind="same_fact", as_of="2026-08-01")
    _assert_refused(verdict, "NOT_KNOWN_AS_OF")
    assert "NOT_KNOWN_AS_OF" in validate_fact(left, as_of="2026-08-01")


def test_a09_e1p4_e2p4_known_at_missing():
    left = _base_fact(known_at=_OMIT)
    right = _base_fact(known_at=_OMIT, source_owner="SYN-OWNER-B")
    verdict = check_join(left, right, join_kind="same_fact", as_of="2026-08-20")
    _assert_refused(verdict, "KNOWN_AT_MISSING")
    assert "KNOWN_AT_MISSING" in validate_fact(left, as_of="2026-08-20")
    assert "KNOWN_AT_MISSING" not in validate_fact(left)


def test_a09_e1p4_e2p4_late_but_known_allowed():
    left = _base_fact(
        period_end="2026-06-30",
        period_start="2026-01-01",
        known_at="2026-08-12T16:31:00",
        period_type="interim",
    )
    right = copy.deepcopy(left)
    right["source_owner"] = "SYN-OWNER-B"
    verdict = check_join(left, right, join_kind="same_fact", as_of="2026-08-20")
    _assert_allowed(verdict)
    after_ts = check_join(
        left, right, join_kind="same_fact", as_of="2026-08-12T16:31:00"
    )
    _assert_allowed(after_ts)


# ---------------------------------------------------------------------------
# E1-P5 / E2-5 currency and scale
# ---------------------------------------------------------------------------


def test_a09_e1p5_e2p5_currency_mismatch():
    left = _base_fact(currency="HKD", source_reported_currency="HKD")
    right = _base_fact(
        currency="CNY",
        source_reported_currency="CNY",
        source_owner="SYN-OWNER-B",
    )
    verdict = check_join(left, right, join_kind="same_fact")
    _assert_refused(verdict, "CURRENCY_MISMATCH")
    assert validate_fact(left) == ()
    assert validate_fact(right) == ()
    assert "CURRENCY_LABEL_CONFLICT" not in _codes(verdict)


def test_a09_e1p5_e2p5_currency_label_conflict():
    left = _base_fact(currency="HKD", source_reported_currency="CNY")
    right = copy.deepcopy(left)
    right["source_owner"] = "SYN-OWNER-B"
    verdict = check_join(left, right, join_kind="same_fact")
    _assert_refused(verdict, "CURRENCY_LABEL_CONFLICT")
    assert "CURRENCY_LABEL_CONFLICT" in validate_fact(left)


def test_a09_e1p5_e2p5_scale_mismatch():
    left = _base_fact(scale=3)
    right = _base_fact(scale=6, source_owner="SYN-OWNER-B")
    verdict = check_join(left, right, join_kind="same_fact")
    _assert_refused(verdict, "SCALE_MISMATCH")


def test_a09_e1p5_e2p5_currency_or_scale_unknown():
    missing_ccy = _base_fact(currency=_OMIT, source_reported_currency=_OMIT)
    other = _base_fact()
    ccy_verdict = check_join(missing_ccy, other, join_kind="same_fact")
    _assert_refused(ccy_verdict, "CURRENCY_UNKNOWN")
    assert "CURRENCY_UNKNOWN" in validate_fact(missing_ccy)
    missing_scale = _base_fact(scale=_OMIT)
    scale_verdict = check_join(missing_scale, other, join_kind="same_fact")
    _assert_refused(scale_verdict, "SCALE_UNKNOWN")
    assert "SCALE_UNKNOWN" in validate_fact(missing_scale)


def test_a09_e1p5_e2p5_no_conversion_ast():
    source = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    needles = ("value", "rate", "fx", "scale")
    hits = []

    def bits(node):
        out = []
        if isinstance(node, ast.Name):
            out.append(node.id)
        elif isinstance(node, ast.Attribute):
            out.append(node.attr)
            out.extend(bits(node.value))
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            out.append(node.value)
        return out

    for node in ast.walk(tree):
        if not isinstance(node, ast.BinOp):
            continue
        if not isinstance(node.op, (ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow)):
            continue
        names = bits(node.left) + bits(node.right)
        for name in names:
            folded = name.casefold()
            for needle in needles:
                if needle in folded:
                    hits.append((node.lineno, name, type(node.op).__name__))
    assert hits == [], hits
    fn_names = {
        n.name
        for n in ast.walk(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert "check_join" in fn_names
    assert "validate_fact" in fn_names


# ---------------------------------------------------------------------------
# E1-P6 / E2-6 + fold check, dual counter
# ---------------------------------------------------------------------------


def test_a09_e1p6_e2p6_counter_mismatch():
    left = _sec(counter_id="SYN-CTR-A")
    right = _sec(counter_id="SYN-CTR-B", source_owner="SYN-OWNER-B")
    verdict = check_join(left, right, join_kind="same_fact")
    _assert_refused(verdict, "COUNTER_MISMATCH")
    assert validate_fact(left) == ()
    assert validate_fact(right) == ()


def test_a09_e1p6_e2p6_counter_unresolved_folded():
    left = _sec(counter_id=None)
    right = _sec(counter_id="SYN-CTR-A", source_owner="SYN-OWNER-B")
    verdict = check_join(left, right, join_kind="same_fact")
    _assert_refused(verdict, "COUNTER_UNRESOLVED")
    assert "COUNTER_UNRESOLVED" in validate_fact(left)


def test_a09_e1p6_e2p6_issuer_level_ignores_counter():
    left = _base_fact(level="issuer", counter_id="SYN-CTR-A")
    right = _base_fact(
        level="issuer", counter_id="SYN-CTR-B", source_owner="SYN-OWNER-B"
    )
    verdict = check_join(left, right, join_kind="same_fact")
    _assert_allowed(verdict)


def test_a09_e2p6_fold_check_unresolved_counter():
    folded = _sec(counter_id=None)
    assert "COUNTER_UNRESOLVED" in validate_fact(folded)
    peer = _sec(counter_id=None, source_owner="SYN-OWNER-B")
    verdict = check_join(folded, peer, join_kind="same_fact")
    _assert_refused(verdict, "COUNTER_UNRESOLVED")


# ---------------------------------------------------------------------------
# Opaque identity
# ---------------------------------------------------------------------------


def test_a09_opaque_identity_no_normalisation():
    left = _base_fact(issuer_id="SYN-ISSUER-1")
    right = _base_fact(issuer_id="syn-issuer-1", source_owner="SYN-OWNER-B")
    verdict = check_join(left, right, join_kind="same_fact")
    _assert_refused(verdict, "ISSUER_MISMATCH")


def test_a09_opaque_identity_unresolved():
    none_fact = _base_fact(issuer_id=None)
    empty_fact = _base_fact(issuer_id="")
    peer = _base_fact()
    none_verdict = check_join(none_fact, peer, join_kind="same_fact")
    empty_verdict = check_join(empty_fact, peer, join_kind="same_fact")
    _assert_refused(none_verdict, "ISSUER_UNRESOLVED")
    _assert_refused(empty_verdict, "ISSUER_UNRESOLVED")
    assert "ISSUER_UNRESOLVED" in validate_fact(none_fact)
    assert "ISSUER_UNRESOLVED" in validate_fact(empty_fact)


def test_a09_opaque_identity_no_normalise_ast():
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
# Positive controls
# ---------------------------------------------------------------------------


def test_a09_positive_same_fact():
    left = _base_fact(source_owner="SYN-OWNER-A")
    right = _base_fact(source_owner="SYN-OWNER-B")
    verdict = check_join(left, right, join_kind="same_fact")
    _assert_allowed(verdict)


def test_a09_positive_ratio():
    left = _base_fact(metric="revenue")
    right = _base_fact(metric="net_income", source_owner="SYN-OWNER-B")
    verdict = check_join(left, right, join_kind="ratio")
    _assert_allowed(verdict)
    same_seg = check_join(
        _base_fact(metric="revenue", segment="cloud", segment_scheme_version="sch-1"),
        _base_fact(
            metric="net_income",
            segment="cloud",
            segment_scheme_version="sch-1",
            source_owner="SYN-OWNER-B",
        ),
        join_kind="ratio",
    )
    _assert_allowed(same_seg)
    one_sided_seg = check_join(
        _base_fact(metric="revenue", segment="cloud", segment_scheme_version="sch-1"),
        _base_fact(metric="net_income", source_owner="SYN-OWNER-B"),
        join_kind="ratio",
    )
    _assert_allowed(one_sided_seg)


def test_a09_positive_time_series():
    left = _base_fact(
        period_start="2024-04-01",
        period_end="2025-03-31",
        known_at="2025-05-13T17:30:00",
        value=80,
        version="v1",
    )
    right = _base_fact(
        period_start="2025-04-01",
        period_end="2026-03-31",
        known_at="2026-05-13T17:30:00",
        value=100,
        version="v1",
        source_owner="SYN-OWNER-B",
    )
    verdict = check_join(left, right, join_kind="time_series")
    _assert_allowed(verdict)


# ---------------------------------------------------------------------------
# Completeness
# ---------------------------------------------------------------------------


def test_a09_completeness_three_defects():
    left = _base_fact(
        currency="HKD",
        source_reported_currency="HKD",
        scale=3,
        share_denominator="BASIC",
    )
    right = _base_fact(
        currency="CNY",
        source_reported_currency="CNY",
        scale=6,
        share_denominator="DILUTED",
        source_owner="SYN-OWNER-B",
    )
    verdict = check_join(left, right, join_kind="same_fact")
    _assert_refused(
        verdict, "CURRENCY_MISMATCH", "SCALE_MISMATCH", "DENOMINATOR_MISMATCH"
    )
    got = set(_codes(verdict))
    assert "CURRENCY_MISMATCH" in got
    assert "SCALE_MISMATCH" in got
    assert "DENOMINATOR_MISMATCH" in got


def test_a09_completeness_symmetric():
    left = _base_fact(
        issuer_id="SYN-ISSUER-1",
        currency="HKD",
        source_reported_currency="HKD",
        share_denominator=_OMIT,
    )
    right = _base_fact(
        issuer_id="SYN-ISSUER-2",
        currency="CNY",
        source_reported_currency="CNY",
        source_owner="SYN-OWNER-B",
    )
    ab = check_join(left, right, join_kind="same_fact")
    ba = check_join(right, left, join_kind="same_fact")
    _assert_refused(ab, "ISSUER_MISMATCH", "CURRENCY_MISMATCH", "DENOMINATOR_UNCARRIED")
    _assert_refused(ba, "ISSUER_MISMATCH", "CURRENCY_MISMATCH", "DENOMINATOR_UNCARRIED")
    assert _stripped(ab.reasons) == _stripped(ba.reasons)


def test_a09_completeness_reasons_in_tuple():
    cases = [
        (
            _base_fact(share_denominator="BASIC"),
            _base_fact(share_denominator="DILUTED"),
            "same_fact",
            None,
        ),
        (
            _base_fact(share_denominator=_OMIT),
            _base_fact(),
            "same_fact",
            None,
        ),
        (
            _base_fact(share_denominator="ADS"),
            _base_fact(share_denominator="ADS", ads_ratio=5),
            "same_fact",
            None,
        ),
        (
            _base_fact(version="v1"),
            _base_fact(version="v2"),
            "same_fact",
            None,
        ),
        (
            _base_fact(version="v1", value=1),
            _base_fact(version="v1", value=2),
            "same_fact",
            None,
        ),
        (
            _base_fact(version=_OMIT),
            _base_fact(version=_OMIT),
            "same_fact",
            None,
        ),
        (
            _base_fact(segment="cloud", segment_scheme_version="sch-1"),
            _base_fact(segment="cloud", segment_scheme_version="sch-2"),
            "same_fact",
            None,
        ),
        (
            _base_fact(period_end=_OMIT),
            _base_fact(),
            "same_fact",
            None,
        ),
        (
            _base_fact(period_end="2026-06-30", known_at="2026-06-01T00:00:00"),
            _base_fact(period_end="2026-06-30", known_at="2026-06-01T00:00:00"),
            "same_fact",
            None,
        ),
        (
            _base_fact(known_at="2026-08-12T16:31:00", period_end="2026-06-30"),
            _base_fact(known_at="2026-08-12T16:31:00", period_end="2026-06-30"),
            "same_fact",
            "2026-08-01",
        ),
        (
            _base_fact(known_at=_OMIT),
            _base_fact(known_at=_OMIT),
            "same_fact",
            "2026-08-20",
        ),
        (
            _base_fact(currency="HKD", source_reported_currency="HKD"),
            _base_fact(currency="CNY", source_reported_currency="CNY"),
            "same_fact",
            None,
        ),
        (
            _base_fact(currency="HKD", source_reported_currency="CNY"),
            _base_fact(currency="HKD", source_reported_currency="CNY"),
            "same_fact",
            None,
        ),
        (
            _base_fact(scale=3),
            _base_fact(scale=6),
            "same_fact",
            None,
        ),
        (
            _base_fact(currency=_OMIT, source_reported_currency=_OMIT),
            _base_fact(),
            "same_fact",
            None,
        ),
        (
            _base_fact(scale=_OMIT),
            _base_fact(),
            "same_fact",
            None,
        ),
        (
            _sec(counter_id="SYN-CTR-A"),
            _sec(counter_id="SYN-CTR-B"),
            "same_fact",
            None,
        ),
        (
            _sec(counter_id=None),
            _sec(),
            "same_fact",
            None,
        ),
        (
            _base_fact(issuer_id="SYN-ISSUER-1"),
            _base_fact(issuer_id="syn-issuer-1"),
            "same_fact",
            None,
        ),
        (
            _base_fact(issuer_id=None),
            _base_fact(),
            "same_fact",
            None,
        ),
        (
            _base_fact(typo_field=1),
            _base_fact(),
            "same_fact",
            None,
        ),
        (
            _base_fact(),
            _base_fact(),
            "not_a_kind",
            None,
        ),
        (
            _base_fact(metric="revenue"),
            _base_fact(metric="net_income", currency="HKD", source_reported_currency="HKD"),
            "ratio",
            None,
        ),
        (
            _base_fact(period_end="2025-03-31", segment="cloud", segment_scheme_version="a"),
            _base_fact(period_end="2026-03-31", segment="cloud", segment_scheme_version="b"),
            "time_series",
            None,
        ),
        (
            _base_fact(level="issuer"),
            _sec(),
            "same_fact",
            None,
        ),
        (
            _base_fact(metric="revenue"),
            _base_fact(metric="net_income"),
            "same_fact",
            None,
        ),
        (
            _base_fact(period_type="annual"),
            _base_fact(period_type="interim"),
            "same_fact",
            None,
        ),
        (
            _base_fact(period_end="2025-03-31"),
            _base_fact(period_end="2026-03-31"),
            "same_fact",
            None,
        ),
        (
            _base_fact(basis="reported"),
            _base_fact(basis="adjusted"),
            "same_fact",
            None,
        ),
        (
            _base_fact(segment="cloud", segment_scheme_version="sch-1"),
            _base_fact(segment="ads", segment_scheme_version="sch-1"),
            "same_fact",
            None,
        ),
    ]
    for left, right, kind, as_of in cases:
        verdict = check_join(left, right, join_kind=kind, as_of=as_of)
        _assert_contract(verdict)
        for code in _codes(verdict):
            assert code in REASONS, (code, kind, verdict.reasons)


def test_a09_completeness_schema_unknown_field():
    left = _base_fact(not_a_field=1)
    right = _base_fact()
    verdict = check_join(left, right, join_kind="same_fact")
    _assert_refused(verdict, "SCHEMA_UNKNOWN_FIELD")
    per = validate_fact(left)
    assert "SCHEMA_UNKNOWN_FIELD:not_a_field" in per


def test_a09_completeness_join_kind_unknown():
    left = _base_fact()
    right = _base_fact(source_owner="SYN-OWNER-B")
    verdict = check_join(left, right, join_kind="merge_anyway")
    _assert_refused(verdict, "JOIN_KIND_UNKNOWN")
    assert verdict.join_kind == "merge_anyway"
    assert verdict.reasons == ("JOIN_KIND_UNKNOWN",)


def test_a09_completeness_level_metric_period_basis():
    level_v = check_join(_base_fact(level="issuer"), _sec(), join_kind="same_fact")
    _assert_refused(level_v, "LEVEL_MISMATCH")
    metric_v = check_join(
        _base_fact(metric="revenue"),
        _base_fact(metric="net_income"),
        join_kind="same_fact",
    )
    _assert_refused(metric_v, "METRIC_MISMATCH")
    ratio_ok = check_join(
        _base_fact(metric="revenue"),
        _base_fact(metric="net_income"),
        join_kind="ratio",
    )
    _assert_allowed(ratio_ok)
    ptype_v = check_join(
        _base_fact(period_type="annual"),
        _base_fact(period_type="interim"),
        join_kind="time_series",
    )
    _assert_refused(ptype_v, "PERIOD_TYPE_MISMATCH")
    period_v = check_join(
        _base_fact(period_end="2025-03-31", known_at="2025-05-13T17:30:00"),
        _base_fact(period_end="2026-03-31"),
        join_kind="same_fact",
    )
    _assert_refused(period_v, "PERIOD_MISMATCH")
    ts_ok = check_join(
        _base_fact(period_end="2025-03-31", known_at="2025-05-13T17:30:00", value=80),
        _base_fact(period_end="2026-03-31", value=100),
        join_kind="time_series",
    )
    _assert_allowed(ts_ok)
    basis_v = check_join(
        _base_fact(basis="reported"),
        _base_fact(basis="adjusted"),
        join_kind="same_fact",
    )
    _assert_refused(basis_v, "BASIS_MISMATCH")
    seg_v = check_join(
        _base_fact(segment="cloud", segment_scheme_version="sch-1"),
        _base_fact(segment="ads", segment_scheme_version="sch-1"),
        join_kind="same_fact",
    )
    _assert_refused(seg_v, "SEGMENT_MISMATCH")


# ---------------------------------------------------------------------------
# Authority
# ---------------------------------------------------------------------------


def test_a09_authority_flags_false():
    pairs = [
        (_base_fact(), _base_fact(source_owner="SYN-OWNER-B"), "same_fact"),
        (
            _base_fact(currency="HKD", source_reported_currency="HKD"),
            _base_fact(currency="CNY", source_reported_currency="CNY"),
            "same_fact",
        ),
        (_sec(counter_id="SYN-CTR-A"), _sec(counter_id="SYN-CTR-B"), "same_fact"),
        (_base_fact(metric="revenue"), _base_fact(metric="net_income"), "ratio"),
        (
            _base_fact(period_end="2025-03-31", known_at="2025-05-13T17:30:00"),
            _base_fact(period_end="2026-03-31"),
            "time_series",
        ),
    ]
    for left, right, kind in pairs:
        verdict = check_join(left, right, join_kind=kind)
        _assert_contract(verdict)
        for name in FLAG_NAMES:
            assert verdict.authority[name] is False
            assert AUTHORITY_FLAGS[name] is False


def test_a09_authority_true_raises():
    bad = dict(AUTHORITY_FLAGS)
    bad["rank_authority"] = True
    with pytest.raises(ValueError):
        JoinVerdict(
            status="ALLOWED",
            reasons=(),
            join_kind="same_fact",
            authority=bad,
        )
    for name in FLAG_NAMES:
        one = dict(AUTHORITY_FLAGS)
        one[name] = True
        with pytest.raises(ValueError):
            JoinVerdict(
                status="REFUSED",
                reasons=("CURRENCY_MISMATCH",),
                join_kind="same_fact",
                authority=one,
            )


def test_a09_refuse_nonfalse_authority():
    refuse_nonfalse_authority()
    refuse_nonfalse_authority(AUTHORITY_FLAGS)
    refuse_nonfalse_authority(dict(AUTHORITY_FLAGS))
    with pytest.raises(ValueError):
        refuse_nonfalse_authority({"rank_authority": True})
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


def test_a09_fact_fields_frozen_contract():
    assert FACT_FIELDS == (
        "issuer_id",
        "counter_id",
        "level",
        "metric",
        "period_type",
        "period_start",
        "period_end",
        "basis",
        "currency",
        "source_reported_currency",
        "scale",
        "segment",
        "segment_scheme_version",
        "share_denominator",
        "ads_ratio",
        "version",
        "supersedes",
        "known_at",
        "source_owner",
        "value",
    )
    for code in (
        "SCHEMA_UNKNOWN_FIELD",
        "CURRENCY_MISMATCH",
        "CURRENCY_LABEL_CONFLICT",
        "DENOMINATOR_UNCARRIED",
        "COUNTER_UNRESOLVED",
        "VERSION_CONFLICT",
        "NOT_KNOWN_AS_OF",
        "JOIN_KIND_UNKNOWN",
        "SEGMENT_SCHEME_MISMATCH",
        "ADS_RATIO_MISMATCH",
        "TIMESTAMP_INCOHERENT",
        "VALUE_CONFLICT",
    ):
        assert code in REASONS
    assert len(REASONS) == len(set(REASONS))


# ---------------------------------------------------------------------------
# X7 red-team repairs 2026-10-13: X7-03 one-sided period_start, X7-04 ratio
# scheme-only mismatch, X7-08 bool-vs-int scale. cov7_* guard the unchanged
# positive controls and pre-existing refusals around each hole.
# ---------------------------------------------------------------------------


def _x7_one_sided_period(blank_side: str, blank: object) -> tuple[dict, dict]:
    """One fact carries period_start; the other side carries `blank`
    (_OMIT deletes the key; None and "" stay literal blanks)."""
    if blank_side == "left":
        return (
            _base_fact(period_start=blank),
            _base_fact(source_owner="SYN-OWNER-B"),
        )
    return (
        _base_fact(),
        _base_fact(period_start=blank, source_owner="SYN-OWNER-B"),
    )


def test_x7_03_same_fact_absent_left():
    left, right = _x7_one_sided_period("left", _OMIT)
    verdict = check_join(left, right, join_kind="same_fact")
    _assert_refused(verdict, "PERIOD_MISMATCH")
    assert validate_fact(left) == ()
    assert validate_fact(right) == ()
    swapped = check_join(right, left, join_kind="same_fact")
    _assert_refused(swapped, "PERIOD_MISMATCH")


def test_x7_03_same_fact_absent_right():
    left, right = _x7_one_sided_period("right", _OMIT)
    verdict = check_join(left, right, join_kind="same_fact")
    _assert_refused(verdict, "PERIOD_MISMATCH")
    assert validate_fact(left) == ()
    assert validate_fact(right) == ()
    swapped = check_join(right, left, join_kind="same_fact")
    _assert_refused(swapped, "PERIOD_MISMATCH")


def test_x7_03_same_fact_none_left():
    left, right = _x7_one_sided_period("left", None)
    verdict = check_join(left, right, join_kind="same_fact")
    _assert_refused(verdict, "PERIOD_MISMATCH")
    assert validate_fact(left) == ()
    assert validate_fact(right) == ()


def test_x7_03_same_fact_none_right():
    left, right = _x7_one_sided_period("right", None)
    verdict = check_join(left, right, join_kind="same_fact")
    _assert_refused(verdict, "PERIOD_MISMATCH")
    assert validate_fact(left) == ()
    assert validate_fact(right) == ()


def test_x7_03_same_fact_empty_left():
    left, right = _x7_one_sided_period("left", "")
    verdict = check_join(left, right, join_kind="same_fact")
    _assert_refused(verdict, "PERIOD_MISMATCH")
    assert validate_fact(left) == ()
    assert validate_fact(right) == ()


def test_x7_03_same_fact_empty_right():
    left, right = _x7_one_sided_period("right", "")
    verdict = check_join(left, right, join_kind="same_fact")
    _assert_refused(verdict, "PERIOD_MISMATCH")
    assert validate_fact(left) == ()
    assert validate_fact(right) == ()


def test_x7_03_ratio_absent_left():
    left, right = _x7_one_sided_period("left", _OMIT)
    verdict = check_join(left, right, join_kind="ratio")
    _assert_refused(verdict, "PERIOD_MISMATCH")
    assert validate_fact(left) == ()
    assert validate_fact(right) == ()
    swapped = check_join(right, left, join_kind="ratio")
    _assert_refused(swapped, "PERIOD_MISMATCH")


def test_x7_03_ratio_absent_right():
    left, right = _x7_one_sided_period("right", _OMIT)
    verdict = check_join(left, right, join_kind="ratio")
    _assert_refused(verdict, "PERIOD_MISMATCH")
    assert validate_fact(left) == ()
    assert validate_fact(right) == ()
    swapped = check_join(right, left, join_kind="ratio")
    _assert_refused(swapped, "PERIOD_MISMATCH")


def test_x7_03_ratio_none_left():
    left, right = _x7_one_sided_period("left", None)
    verdict = check_join(left, right, join_kind="ratio")
    _assert_refused(verdict, "PERIOD_MISMATCH")
    assert validate_fact(left) == ()
    assert validate_fact(right) == ()


def test_x7_03_ratio_none_right():
    left, right = _x7_one_sided_period("right", None)
    verdict = check_join(left, right, join_kind="ratio")
    _assert_refused(verdict, "PERIOD_MISMATCH")
    assert validate_fact(left) == ()
    assert validate_fact(right) == ()


def test_x7_03_ratio_empty_left():
    left, right = _x7_one_sided_period("left", "")
    verdict = check_join(left, right, join_kind="ratio")
    _assert_refused(verdict, "PERIOD_MISMATCH")
    assert validate_fact(left) == ()
    assert validate_fact(right) == ()


def test_x7_03_ratio_empty_right():
    left, right = _x7_one_sided_period("right", "")
    verdict = check_join(left, right, join_kind="ratio")
    _assert_refused(verdict, "PERIOD_MISMATCH")
    assert validate_fact(left) == ()
    assert validate_fact(right) == ()


def test_x7_04_ratio_scheme_only_mismatch_refused():
    left = _base_fact(metric="revenue", segment_scheme_version="sch-1")
    right = _base_fact(
        metric="net_income",
        segment_scheme_version="sch-2",
        source_owner="SYN-OWNER-B",
    )
    verdict = check_join(left, right, join_kind="ratio")
    _assert_refused(verdict, "SEGMENT_SCHEME_MISMATCH")
    assert validate_fact(left) == ()
    assert validate_fact(right) == ()
    swapped = check_join(right, left, join_kind="ratio")
    _assert_refused(swapped, "SEGMENT_SCHEME_MISMATCH")


def test_x7_04_ratio_equal_schemes_allowed():
    left = _base_fact(metric="revenue", segment_scheme_version="sch-1")
    right = _base_fact(
        metric="net_income", segment_scheme_version="sch-1", source_owner="SYN-OWNER-B"
    )
    verdict = check_join(left, right, join_kind="ratio")
    _assert_allowed(verdict)


def test_x7_04_ratio_one_sided_scheme_allowed():
    left = _base_fact(metric="revenue", segment_scheme_version="sch-1")
    right = _base_fact(metric="net_income", source_owner="SYN-OWNER-B")
    verdict = check_join(left, right, join_kind="ratio")
    _assert_allowed(verdict)


def test_x7_08_true_vs_one_refused():
    left = _base_fact(scale=True)
    right = _base_fact(scale=1, source_owner="SYN-OWNER-B")
    verdict = check_join(left, right, join_kind="same_fact")
    _assert_refused(verdict, "SCALE_MISMATCH")
    assert validate_fact(left) == ()
    assert validate_fact(right) == ()
    swapped = check_join(right, left, join_kind="same_fact")
    _assert_refused(swapped, "SCALE_MISMATCH")


def test_x7_08_false_vs_zero_refused():
    left = _base_fact(scale=False)
    right = _base_fact(source_owner="SYN-OWNER-B")
    verdict = check_join(left, right, join_kind="same_fact")
    _assert_refused(verdict, "SCALE_MISMATCH")
    assert validate_fact(left) == ()
    assert validate_fact(right) == ()


def test_x7_08_int_vs_equal_int_allowed():
    left = _base_fact(scale=1)
    right = _base_fact(scale=1, source_owner="SYN-OWNER-B")
    verdict = check_join(left, right, join_kind="same_fact")
    _assert_allowed(verdict)


def test_cov7_two_absent_period_start_same_fact_allowed():
    left = _base_fact(period_start=_OMIT)
    right = _base_fact(period_start=_OMIT, source_owner="SYN-OWNER-B")
    verdict = check_join(left, right, join_kind="same_fact")
    _assert_allowed(verdict)


def test_cov7_period_start_both_dates_mismatch_refused():
    left = _base_fact(period_start="2024-04-01")
    right = _base_fact(period_start="2025-04-01", source_owner="SYN-OWNER-B")
    verdict = check_join(left, right, join_kind="same_fact")
    _assert_refused(verdict, "PERIOD_MISMATCH")


def test_cov7_time_series_one_sided_period_start_allowed():
    left, right = _x7_one_sided_period("left", _OMIT)
    verdict = check_join(left, right, join_kind="time_series")
    _assert_allowed(verdict)


def test_cov7_same_fact_scheme_only_mismatch_refused():
    left = _base_fact(segment_scheme_version="sch-1")
    right = _base_fact(segment_scheme_version="sch-2", source_owner="SYN-OWNER-B")
    verdict = check_join(left, right, join_kind="same_fact")
    _assert_refused(verdict, "SEGMENT_SCHEME_MISMATCH")


def test_cov7_ratio_one_sided_segment_allowed():
    left = _base_fact(
        metric="revenue", segment="cloud", segment_scheme_version="sch-1"
    )
    right = _base_fact(metric="net_income", source_owner="SYN-OWNER-B")
    verdict = check_join(left, right, join_kind="ratio")
    _assert_allowed(verdict)


def test_cov7_ratio_equal_segments_equal_schemes_allowed():
    left = _base_fact(
        metric="revenue", segment="cloud", segment_scheme_version="sch-1"
    )
    right = _base_fact(
        metric="net_income",
        segment="cloud",
        segment_scheme_version="sch-1",
        source_owner="SYN-OWNER-B",
    )
    verdict = check_join(left, right, join_kind="ratio")
    _assert_allowed(verdict)


def test_cov7_scale_zero_vs_string_zero_refused():
    left = _base_fact(scale=0)
    right = _base_fact(scale="0", source_owner="SYN-OWNER-B")
    verdict = check_join(left, right, join_kind="same_fact")
    _assert_refused(verdict, "SCALE_MISMATCH")


def test_cov7_scale_int_mismatch_refused():
    left = _base_fact(scale=3)
    right = _base_fact(scale=6, source_owner="SYN-OWNER-B")
    verdict = check_join(left, right, join_kind="same_fact")
    _assert_refused(verdict, "SCALE_MISMATCH")


def test_cov7_positive_same_fact_and_ratio_allowed():
    verdict = check_join(
        _base_fact(source_owner="SYN-OWNER-A"),
        _base_fact(source_owner="SYN-OWNER-B"),
        join_kind="same_fact",
    )
    _assert_allowed(verdict)
    ratio = check_join(
        _base_fact(metric="revenue"),
        _base_fact(metric="net_income", source_owner="SYN-OWNER-B"),
        join_kind="ratio",
    )
    _assert_allowed(ratio)
