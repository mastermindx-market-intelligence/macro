"""FAMJ2 round-2 repair tests — FAMILY TEXT RULE v2 on sni_join_guard.

SNI-local DRAFT contract repair tests (REQUEST_REPAIR round 2). They
consume owner-supplied opaque identity strings (Stock Identity / Data OS)
and never mint issuer or security ids. Every authority flag stays literal
False. Fixtures are synthetic and live only inside this file. Nothing here
feeds a ranker, gate, sizer, signal, escalation, or trade path.

Round 2 closes the whitespace halves round 1 left open plus the one
loosening round 1 introduced:

01  _text_present becomes FAMILY TEXT RULE v2: whitespace-only and padded
    values (" ", "\\t", "\\u3000", " ISS", "USD\\n") are ABSENT on every
    text-typed field round 1 routes through the helper, surfacing the
    field's existing blank-style reason (no new reason codes).
02  segment_scheme_version comparison is fail closed again: when both
    sides carry a non-blank scheme version and either side is not
    text-present, SEGMENT_SCHEME_MISMATCH is emitted on the ratio path
    and the non-ratio path alike (a non-text side is never equal).
03  the _text_present docstring names FAMILY TEXT RULE v2 and the module
    implements the whitespace halves with str.isspace, never a
    normalising attribute call.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research" / "single_name_intelligence" / "common"))

from sni_join_guard import (  # noqa: E402
    REASONS,
    check_join,
    validate_fact,
)

MODULE_PATH = (
    ROOT
    / "research"
    / "single_name_intelligence"
    / "common"
    / "sni_join_guard.py"
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
    return fact


def _other(**overrides):
    base = _base_fact()
    base["source_owner"] = "SYN-OWNER-B"
    base.update(overrides)
    return base


def _bare(reason: str) -> str:
    if reason.startswith("LEFT:"):
        return reason[5:]
    if reason.startswith("RIGHT:"):
        return reason[6:]
    return reason


def _codes(verdict) -> tuple[str, ...]:
    return tuple(_bare(r) for r in verdict.reasons)


# ---------------------------------------------------------------------------
# Defect 01 — whitespace-only and padded text values are ABSENT
# ---------------------------------------------------------------------------

_R2_01_CASES = [
    # The seat's RE-CHECK set.
    ("metric", " ", "METRIC_UNKNOWN"),
    ("period_type", "\t", "PERIOD_TYPE_UNKNOWN"),
    ("issuer_id", " ISS", "ISSUER_UNRESOLVED"),
    ("currency", "USD\n", "CURRENCY_UNKNOWN"),
    ("version", "　", "VERSION_UNKNOWN"),
    ("share_denominator", " ADS", "DENOMINATOR_UNCARRIED"),
    # Whitespace-only and padded variants on the other routed fields.
    ("issuer_id", " ", "ISSUER_UNRESOLVED"),
    ("issuer_id", "\n", "ISSUER_UNRESOLVED"),
    ("issuer_id", "ISS ", "ISSUER_UNRESOLVED"),
    ("issuer_id", " ", "ISSUER_UNRESOLVED"),
    ("issuer_id", " ", "ISSUER_UNRESOLVED"),
    ("issuer_id", "\x1c", "ISSUER_UNRESOLVED"),
    ("counter_id", " ", "COUNTER_UNRESOLVED"),
    ("counter_id", " SYN-CTR-A", "COUNTER_UNRESOLVED"),
    ("metric", " ", "METRIC_UNKNOWN"),
    ("metric", " net_income", "METRIC_UNKNOWN"),
    ("period_type", " ", "PERIOD_TYPE_UNKNOWN"),
    ("period_type", "annual\n", "PERIOD_TYPE_UNKNOWN"),
    ("basis", " ", "BASIS_UNKNOWN"),
    ("basis", " reported", "BASIS_UNKNOWN"),
    ("currency", " ", "CURRENCY_UNKNOWN"),
    ("currency", "\tCNY", "CURRENCY_UNKNOWN"),
    ("share_denominator", " ", "DENOMINATOR_UNCARRIED"),
    ("share_denominator", "ADS\n", "DENOMINATOR_UNCARRIED"),
    ("version", " v1", "VERSION_UNKNOWN"),
    ("version", " ", "VERSION_UNKNOWN"),
    # A padded scheme version is ABSENT, so a set segment with a carried
    # scheme refuses with the field's existing unknown reason.
    ("segment_scheme_version", " sch-1", "SEGMENT_SCHEME_UNKNOWN"),
    ("segment_scheme_version", "　", "SEGMENT_SCHEME_UNKNOWN"),
]


@pytest.mark.parametrize(
    "field,bad_value,expected_reason", _R2_01_CASES, ids=repr
)
def test_r2_01_whitespace_and_padded_values_absent(
    field, bad_value, expected_reason
):
    """FAMILY TEXT RULE v2: whitespace-only, padded, and newline-framed
    values on a text-typed field are ABSENT and map to the reason the
    module already emits for a blank value of that field. validate_fact
    refuses, check_join refuses, and no new reason code appears."""
    if field == "counter_id":
        bad_fact = _base_fact(level="security", counter_id=bad_value)
        peer = _base_fact(
            level="security",
            counter_id="SYN-CTR-A",
            source_owner="SYN-OWNER-B",
        )
    elif field == "segment_scheme_version":
        bad_fact = _base_fact(segment="cloud", segment_scheme_version=bad_value)
        peer = _other(segment="cloud", segment_scheme_version="sch-1")
    else:
        bad_fact = _base_fact(**{field: bad_value})
        peer = _other()
    reasons = validate_fact(bad_fact)
    assert expected_reason in reasons, (field, bad_value, reasons)
    assert expected_reason in REASONS, expected_reason
    verdict = check_join(bad_fact, peer, join_kind="same_fact")
    assert verdict.status == "REFUSED", (field, bad_value, verdict.reasons)
    assert expected_reason in _codes(verdict), (field, bad_value, verdict.reasons)


# ---------------------------------------------------------------------------
# Defect 02 — scheme-version comparison is fail closed on every join path
# ---------------------------------------------------------------------------

_R2_02_CASES = [
    # (left scheme, right scheme, expect SEGMENT_SCHEME_MISMATCH)
    (1, 2, True),
    (1, 1, True),
    (True, 1, True),
    ("v1", "v2", True),
    ("v1", "v1", False),
    (1, None, False),
    (None, 1, False),
    ("", 1, False),
    ("v1", None, False),
]


@pytest.mark.parametrize("join_kind", ["ratio", "same_fact", "time_series"])
@pytest.mark.parametrize(
    "left_scheme,right_scheme,expect_mismatch", _R2_02_CASES, ids=repr
)
def test_r2_02_scheme_version_fail_closed(
    join_kind, left_scheme, right_scheme, expect_mismatch
):
    """When both sides carry a non-blank segment_scheme_version and either
    side is not text-present, SEGMENT_SCHEME_MISMATCH fires on the ratio
    path and the non-ratio path alike: a non-text side is never equal,
    not even to an equal-looking int or bool. Text-present equal versions
    produce no mismatch; blank one-sided carries stay clean."""
    left = _base_fact(metric="revenue", segment_scheme_version=left_scheme)
    right = _other(metric="net_income", segment_scheme_version=right_scheme)
    verdict = check_join(left, right, join_kind=join_kind)
    codes = _codes(verdict)
    if expect_mismatch:
        assert verdict.status == "REFUSED", (join_kind, verdict.reasons)
        assert "SEGMENT_SCHEME_MISMATCH" in codes, (join_kind, codes)
    else:
        assert "SEGMENT_SCHEME_MISMATCH" not in codes, (join_kind, codes)
    swapped = check_join(right, left, join_kind=join_kind)
    swapped_codes = _codes(swapped)
    assert ("SEGMENT_SCHEME_MISMATCH" in swapped_codes) is expect_mismatch, (
        join_kind,
        swapped_codes,
    )


# ---------------------------------------------------------------------------
# Defect 03 — the docstring names FAMILY TEXT RULE v2; isspace, never a
# normalising attribute call
# ---------------------------------------------------------------------------


def test_r2_03_family_text_rule_v2_source():
    """The module names FAMILY TEXT RULE v2, implements _text_present with
    str.isspace, and contains no normalising attribute call anywhere in
    its source text."""
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert "FAMILY TEXT RULE v2" in source
    for forbidden in ("strip", "lower", "upper", "casefold", "replace"):
        assert ("." + forbidden + "(") not in source
    tree = ast.parse(source)
    bodies = [
        ast.get_source_segment(source, node)
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "_text_present"
    ]
    assert len(bodies) == 1
    assert bodies[0] is not None
    assert "isspace" in bodies[0]
