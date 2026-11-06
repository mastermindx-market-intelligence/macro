"""FAMJ repair tests — FAMILY TEXT RULE applied to sni_join_guard.

SNI-local DRAFT contract repair tests. They consume owner-supplied opaque
identity strings (Stock Identity / Data OS) and never mint issuer or
security ids. Every authority flag stays literal False. Fixtures are
synthetic and live only inside this file.

These tests pin the seat's FAMILY TEXT RULE on the join DRAFT guard for
the sub-defects that are not pinned by an existing test: non-str values
in text-typed fields are ABSENT and surface the field's existing
blank-style reason; caller ids that compare across types (1 vs True, 1
vs 1.0) never join as matching; unhashable values (list/dict/set) in any
text field return a refusal from validate_fact and check_join and never
raise.

The whitespace-only and padded sub-defects are intentionally NOT
covered here — they are pinned by the existing
``tests/test_sni_join_guard.py::test_a09_opaque_identity_no_normalise_ast``
test, which forbids any ``.strip()``, ``.lower()``, ``.upper()``,
``.casefold()``, or ``.replace`` attribute call in this module's source.
Per REPAIR LAW that pinning test wins; those sub-defects are recorded in
GAPS and stay open in this lane.
"""
from __future__ import annotations

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

# Non-str values for text-field tests. Whitespace-only and padded values
# are excluded per REPAIR LAW (see module docstring).
_NON_STR_BAD_VALUES = (
    1,
    True,
    1.0,
    [],
    [1, 2],
    {"a": 1},
    {1, 2},
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


def _field_routed_check(field: str, expected_reason: str):
    """For each non-str value in `_NON_STR_BAD_VALUES`, validate_fact and
    check_join both refuse with `expected_reason`. Never raises."""
    for bad in _NON_STR_BAD_VALUES:
        bad_fact = _base_fact(**{field: bad})
        reasons = validate_fact(bad_fact)
        assert expected_reason in reasons, (field, bad, reasons)
        # sanity: already part of the module's REASONS, not extended
        assert expected_reason in REASONS, expected_reason
        verdict = check_join(bad_fact, _other(), join_kind="same_fact")
        assert verdict.status == "REFUSED", (field, bad, verdict.reasons)
        assert expected_reason in _codes(verdict), (
            field,
            bad,
            verdict.reasons,
        )


# ---------------------------------------------------------------------------
# Defect 01 — non-str values on text-typed fields are ABSENT
# ---------------------------------------------------------------------------
#
# Whitespace-only / padded variants are covered by the existing
# ``test_a09_opaque_identity_no_normalise_ast`` pinning test (see GAPS).


@pytest.mark.parametrize("bad_value", _NON_STR_BAD_VALUES, ids=repr)
def test_r1_01_issuer_id(bad_value):
    """issuer_id: non-str values ARE ABSENT → ISSUER_UNRESOLVED.
    check_join refuses."""
    _field_routed_check("issuer_id", "ISSUER_UNRESOLVED")


@pytest.mark.parametrize("bad_value", _NON_STR_BAD_VALUES, ids=repr)
def test_r1_01_counter_id(bad_value):
    """counter_id: non-str at security level → COUNTER_UNRESOLVED.
    check_join refuses."""
    for bad in _NON_STR_BAD_VALUES:
        bad_fact = _base_fact(level="security", counter_id=bad)
        reasons = validate_fact(bad_fact)
        assert "COUNTER_UNRESOLVED" in reasons, (bad, reasons)
        peer = _base_fact(
            level="security",
            counter_id="SYN-CTR-A",
            source_owner="SYN-OWNER-B",
        )
        verdict = check_join(bad_fact, peer, join_kind="same_fact")
        assert verdict.status == "REFUSED", (bad, verdict.reasons)
        assert "COUNTER_UNRESOLVED" in _codes(verdict)


@pytest.mark.parametrize("bad_value", _NON_STR_BAD_VALUES, ids=repr)
def test_r1_01_metric(bad_value):
    """metric: non-str label → METRIC_UNKNOWN. check_join refuses."""
    _field_routed_check("metric", "METRIC_UNKNOWN")


@pytest.mark.parametrize("bad_value", _NON_STR_BAD_VALUES, ids=repr)
def test_r1_01_period_type(bad_value):
    """period_type: non-str label → PERIOD_TYPE_UNKNOWN. check_join refuses."""
    _field_routed_check("period_type", "PERIOD_TYPE_UNKNOWN")


@pytest.mark.parametrize("bad_value", _NON_STR_BAD_VALUES, ids=repr)
def test_r1_01_basis(bad_value):
    """basis: non-str label → BASIS_UNKNOWN. check_join refuses."""
    _field_routed_check("basis", "BASIS_UNKNOWN")


@pytest.mark.parametrize("bad_value", _NON_STR_BAD_VALUES, ids=repr)
def test_r1_01_currency(bad_value):
    """currency: non-str label → CURRENCY_UNKNOWN. check_join refuses."""
    _field_routed_check("currency", "CURRENCY_UNKNOWN")


@pytest.mark.parametrize("bad_value", _NON_STR_BAD_VALUES, ids=repr)
def test_r1_01_share_denominator(bad_value):
    """share_denominator: non-str label → DENOMINATOR_UNCARRIED.
    check_join refuses."""
    _field_routed_check("share_denominator", "DENOMINATOR_UNCARRIED")


@pytest.mark.parametrize("bad_value", _NON_STR_BAD_VALUES, ids=repr)
def test_r1_01_version(bad_value):
    """version: non-str id → VERSION_UNKNOWN. check_join refuses."""
    _field_routed_check("version", "VERSION_UNKNOWN")


# ---------------------------------------------------------------------------
# Defect 02 — cross-type ids / refs never join as matching
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "field,left_val,right_val,unknown_reason",
    [
        ("issuer_id", 1, True, "ISSUER_UNRESOLVED"),
        ("issuer_id", 1, 1.0, "ISSUER_UNRESOLVED"),
        ("issuer_id", True, 1.0, "ISSUER_UNRESOLVED"),
        ("metric", 1, True, "METRIC_UNKNOWN"),
        ("metric", True, 1, "METRIC_UNKNOWN"),
        ("version", True, 1, "VERSION_UNKNOWN"),
        ("basis", 1, True, "BASIS_UNKNOWN"),
        ("basis", True, 1.0, "BASIS_UNKNOWN"),
        ("currency", 1, True, "CURRENCY_UNKNOWN"),
        ("period_type", 1, 1.0, "PERIOD_TYPE_UNKNOWN"),
        ("share_denominator", True, 1, "DENOMINATOR_UNCARRIED"),
        ("share_denominator", 1.0, True, "DENOMINATOR_UNCARRIED"),
    ],
)
def test_r1_02_no_cross_type_match(
    field, left_val, right_val, unknown_reason
):
    """caller-supplied ids 1 / True / 1.0 NEVER match on text fields.

    Both sides are ABSENT under the family text rule and refuse with the
    field's *_UNKNOWN reason. check_join is REFUSED; LEFT/RIGHT prefixes
    surface both sides' unresolved state.
    """
    left = _base_fact(**{field: left_val})
    right = _other(**{field: right_val})
    verdict = check_join(left, right, join_kind="same_fact")
    assert verdict.status == "REFUSED", verdict.reasons
    assert f"LEFT:{unknown_reason}" in verdict.reasons, (
        field,
        left_val,
        right_val,
        verdict.reasons,
    )
    assert f"RIGHT:{unknown_reason}" in verdict.reasons, (
        field,
        left_val,
        right_val,
        verdict.reasons,
    )
    verdict_swap = check_join(right, left, join_kind="same_fact")
    assert verdict_swap.status == "REFUSED"
    assert f"LEFT:{unknown_reason}" in verdict_swap.reasons
    assert f"RIGHT:{unknown_reason}" in verdict_swap.reasons


# ---------------------------------------------------------------------------
# Defect 03 — unhashable / exotic text values never raise
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_value",
    [[[]], [{}], [{1}]],
    ids=repr,
)
def test_r1_03_unhashable(bad_value):
    """A list / dict / set in any text field returns a refusal from
    validate_fact and check_join; never raises."""
    for field, reason in (
        ("issuer_id", "ISSUER_UNRESOLVED"),
        ("metric", "METRIC_UNKNOWN"),
        ("basis", "BASIS_UNKNOWN"),
        ("currency", "CURRENCY_UNKNOWN"),
        ("period_type", "PERIOD_TYPE_UNKNOWN"),
        ("version", "VERSION_UNKNOWN"),
        ("share_denominator", "DENOMINATOR_UNCARRIED"),
    ):
        bad_fact = _base_fact(**{field: bad_value})
        reasons = validate_fact(bad_fact)
        assert reason in reasons, (field, bad_value, reasons)
        verdict = check_join(bad_fact, _other(), join_kind="same_fact")
        assert verdict.status == "REFUSED", (field, bad_value, verdict.reasons)
        assert reason in _codes(verdict)
