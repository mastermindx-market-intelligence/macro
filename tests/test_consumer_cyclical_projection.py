"""Tests for ``engine.sector_intelligence.consumer_cyclical_projection``.

All values used here are SYNTHETIC except the PLNT Q2 2026 frozen golden
oracle, which is reproduced verbatim from
``research/consumer_cyclical/v1/V1_PLNT_BOUNDARY_AND_FROZEN_SPEC.md``
section 5. The spec numbers are the acceptance oracle, not a formula
service: tests pin them exactly.
"""

from __future__ import annotations

import builtins
import datetime as _dt
import socket as _socket
import time as _time
from typing import Any

import pytest

from engine.sector_intelligence.consumer_cyclical_projection import (
    CONTRACT_ID,
    CaseShapeError,
    FACT_KEY_ADVERTISING_EXPENSE,
    FACT_KEY_ADVERTISING_REVENUE,
    FACT_KEY_TOTAL_REVENUE,
    RESULT_KEY_ADVERTISING_CURRENT_PERIOD_NET,
    RESULT_KEY_ADVERTISING_EXPENSE_CHANGE,
    RESULT_KEY_ADVERTISING_NET_CHANGE,
    RESULT_KEY_ADVERTISING_REVENUE_CHANGE,
    RESULT_KEY_ADVERTISING_SHARE_OF_REVENUE_CHANGE_PCT,
    RESULT_KEY_TOTAL_REVENUE_CHANGE,
    SCHEMA_VERSION,
    _check_explanation_for_forbidden,
    project_economic_change,
)


# ---------------------------------------------------------------------------
# Synthetic PLNT golden-case factory
# ---------------------------------------------------------------------------


def _plnt_fact(
    *,
    key: str,
    period_end: str,
    value_text: str,
    native_ref: str,
    metric: str = "",
    definition: str = "",
    basis: str = "REPORTED",
    role: str = "REPORTED_FACT",
    unit: str = "USD",
    scale_power10: int = 3,
    sign_convention: str = "SIGNED",
    period_kind: str = "quarter",
    native_admitted: bool = True,
    rounding_envelope: dict[str, Any] | None = None,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "key": key,
        "metric": metric,
        "value_text": value_text,
        "unit": unit,
        "scale_power10": scale_power10,
        "sign_convention": sign_convention,
        "period_start": period_end[:4] + "-01-01",
        "period_end": period_end,
        "period_kind": period_kind,
        "event": "PLNT Q2 2026, quarter ended " + period_end,
        "published_at": "2026-08-06T00:00:00Z",
        "basis": basis,
        "definition": definition,
        "display_quantum": "USD thousands",
        "native_admitted": native_admitted,
        "native_ref": native_ref,
        "perimeter": "consumer_cyclical_intelligence_read_model.v1",
        "role": role,
        "target": "issuer:0001637207",
        "evidence": evidence
        or {
            "document": "plntq2202026pressreleaseex991.htm",
            "locator": "press_release_table",
            "revision": "2026-08-06",
        },
        "rounding_envelope": rounding_envelope,
    }


def _plnt_subject() -> dict[str, Any]:
    return {
        "issuer_cik": "0001637207",
        "ticker": "PLNT",
        "company_name": "Planet Fitness, Inc.",
        "fiscal_period_end": "2026-06-30",
        "comparison_basis": "explicit_same_quarter_prior_year",
    }


def _plnt_facts() -> list[dict[str, Any]]:
    """Build the PLNT Q2 2026 frozen oracle as a 6-fact case.

    The values are byte-identical to frozen-spec section 5.
    """
    return [
        _plnt_fact(
            key=FACT_KEY_TOTAL_REVENUE,
            period_end="2026-06-30",
            value_text="365223",
            native_ref="src-plntq2-2026-total_revenue-current",
        ),
        _plnt_fact(
            key=FACT_KEY_TOTAL_REVENUE,
            period_end="2025-06-30",
            value_text="340879",
            native_ref="src-plntq2-2026-total_revenue-prior",
        ),
        _plnt_fact(
            key=FACT_KEY_ADVERTISING_REVENUE,
            period_end="2026-06-30",
            value_text="32922",
            native_ref="src-plntq2-2026-advertising_revenue-current",
        ),
        _plnt_fact(
            key=FACT_KEY_ADVERTISING_REVENUE,
            period_end="2025-06-30",
            value_text="22781",
            native_ref="src-plntq2-2026-advertising_revenue-prior",
        ),
        _plnt_fact(
            key=FACT_KEY_ADVERTISING_EXPENSE,
            period_end="2026-06-30",
            value_text="32922",
            native_ref="src-plntq2-2026-advertising_expense-current",
        ),
        _plnt_fact(
            key=FACT_KEY_ADVERTISING_EXPENSE,
            period_end="2025-06-30",
            value_text="22777",
            native_ref="src-plntq2-2026-advertising_expense-prior",
        ),
    ]


def _plnt_case(**overrides: Any) -> dict[str, Any]:
    case: dict[str, Any] = {
        "contract_id": CONTRACT_ID,
        "schema_version": SCHEMA_VERSION,
        "generated_at": "2026-09-24T00:00:00Z",
        "subject": _plnt_subject(),
        "comparison_basis": "explicit_same_quarter_prior_year",
        "facts": _plnt_facts(),
        "source_records": [
            {"record_id": "src-plntq2-2026-total_revenue-current"},
            {"record_id": "src-plntq2-2026-total_revenue-prior"},
            {"record_id": "src-plntq2-2026-advertising_revenue-current"},
            {"record_id": "src-plntq2-2026-advertising_revenue-prior"},
            {"record_id": "src-plntq2-2026-advertising_expense-current"},
            {"record_id": "src-plntq2-2026-advertising_expense-prior"},
        ],
    }
    case.update(overrides)
    return case


def _result_by_key(document: dict[str, Any], key: str) -> dict[str, Any]:
    for r in document["results"]:
        if r["key"] == key:
            return r
    raise AssertionError("result not found: " + key)


# ---------------------------------------------------------------------------
# Golden oracle — frozen spec section 5 (acceptance gate)
# ---------------------------------------------------------------------------


def test_plnt_golden_oracle_value_texts() -> None:
    document = project_economic_change(_plnt_case())
    assert _result_by_key(document, RESULT_KEY_TOTAL_REVENUE_CHANGE)["value_text"] == "24344"
    assert _result_by_key(document, RESULT_KEY_ADVERTISING_REVENUE_CHANGE)["value_text"] == "10141"
    assert _result_by_key(document, RESULT_KEY_ADVERTISING_EXPENSE_CHANGE)["value_text"] == "10145"
    assert _result_by_key(document, RESULT_KEY_ADVERTISING_NET_CHANGE)["value_text"] == "-4"
    assert _result_by_key(document, RESULT_KEY_ADVERTISING_CURRENT_PERIOD_NET)["value_text"] == "0"
    assert _result_by_key(document, RESULT_KEY_ADVERTISING_SHARE_OF_REVENUE_CHANGE_PCT)["value_text"] == "41.66"


def test_plnt_golden_oracle_states() -> None:
    document = project_economic_change(_plnt_case())
    assert document["availability"] == "ready"
    ready_keys = {r["key"] for r in document["results"] if r["state"] == "READY"}
    assert ready_keys == {
        RESULT_KEY_TOTAL_REVENUE_CHANGE,
        RESULT_KEY_ADVERTISING_REVENUE_CHANGE,
        RESULT_KEY_ADVERTISING_EXPENSE_CHANGE,
        RESULT_KEY_ADVERTISING_NET_CHANGE,
        RESULT_KEY_ADVERTISING_CURRENT_PERIOD_NET,
        RESULT_KEY_ADVERTISING_SHARE_OF_REVENUE_CHANGE_PCT,
    }


def test_plnt_advertising_changes_are_not_equal() -> None:
    """Precision law: 10141 vs 10145 — they are NOT equal at displayed precision."""
    document = project_economic_change(_plnt_case())
    ar = _result_by_key(document, RESULT_KEY_ADVERTISING_REVENUE_CHANGE)
    ae = _result_by_key(document, RESULT_KEY_ADVERTISING_EXPENSE_CHANGE)
    assert ar["value_text"] != ae["value_text"]
    assert ar["value_text"] == "10141"
    assert ae["value_text"] == "10145"


def test_plnt_minus_four_residual_survives() -> None:
    """Precision law: the -4 residual must survive in the output."""
    document = project_economic_change(_plnt_case())
    net = _result_by_key(document, RESULT_KEY_ADVERTISING_NET_CHANGE)
    assert net["value_text"] == "-4"
    assert str(net["value_decimal"]) == "-4"


def test_plnt_percentage_uses_quantize_two_places_half_up() -> None:
    """Precision law: 2dp ROUND_HALF_UP. 10141/24344 = 41.657069... -> 41.66."""
    document = project_economic_change(_plnt_case())
    pct = _result_by_key(document, RESULT_KEY_ADVERTISING_SHARE_OF_REVENUE_CHANGE_PCT)
    assert pct["value_text"] == "41.66"
    assert pct["unit"] == "PERCENT"


def test_plnt_input_refs_are_bound_per_result() -> None:
    """Frozen-spec section 6 rule 2: every ready result binds its input refs."""
    document = project_economic_change(_plnt_case())
    for r in document["results"]:
        if r["state"] != "READY":
            continue
        assert isinstance(r["input_refs"], list)
        assert r["input_refs"], "input_refs must be non-empty for ready results"


def test_plnt_unit_scale_sign_preserved() -> None:
    """Frozen-spec section 6 rule 1: unit / scale_power10 / sign_convention preserved."""
    document = project_economic_change(_plnt_case())
    total = _result_by_key(document, RESULT_KEY_TOTAL_REVENUE_CHANGE)
    assert total["unit"] == "USD"
    assert total["scale_power10"] == 3
    assert total["sign_convention"] == "SIGNED"


def test_plnt_explanation_has_four_fields() -> None:
    document = project_economic_change(_plnt_case())
    explanation = document["explanation"]
    assert explanation["lead"]
    assert explanation["counterevidence"]
    assert explanation["next_observation"]
    assert explanation["does_not_prove"]


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_deterministic_byte_identical_output() -> None:
    a = project_economic_change(_plnt_case())
    b = project_economic_change(_plnt_case())
    assert a == b


def test_no_io(monkeypatch: pytest.MonkeyPatch) -> None:
    """Composition must succeed with open / socket / time patched.

    The composer reads ``generated_at`` from the caller-supplied case
    (string field), never the wall clock, so no datetime patch is
    required — but open / socket / time must never be invoked.
    """

    def _explode(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("IO/clock was read by the composer")

    monkeypatch.setattr(builtins, "open", _explode)
    monkeypatch.setattr(_socket, "socket", _explode)
    monkeypatch.setattr(_time, "time", _explode)

    document = project_economic_change(_plnt_case())
    assert document["availability"] == "ready"


def test_generated_at_is_caller_supplied() -> None:
    case = _plnt_case(generated_at="2030-01-15T12:34:56Z")
    document = project_economic_change(case)
    assert document["generated_at"] == "2030-01-15T12:34:56Z"


def test_generated_at_falls_back_to_sentinel_when_missing() -> None:
    case = _plnt_case()
    case.pop("generated_at")
    document = project_economic_change(case)
    assert document["generated_at"] == "1970-01-01T00:00:00Z"


# ---------------------------------------------------------------------------
# Malformed case shape (section 6 rule 8)
# ---------------------------------------------------------------------------


def test_malformed_case_refuses_missing_subject() -> None:
    case = _plnt_case()
    case.pop("subject")
    with pytest.raises(CaseShapeError):
        project_economic_change(case)


def test_malformed_case_refuses_subject_wrong_type() -> None:
    case = _plnt_case()
    case["subject"] = "PLNT"
    with pytest.raises(CaseShapeError):
        project_economic_change(case)


def test_malformed_case_refuses_missing_comparison_basis() -> None:
    case = _plnt_case()
    case.pop("comparison_basis")
    with pytest.raises(CaseShapeError):
        project_economic_change(case)


def test_malformed_case_refuses_unknown_comparison_basis() -> None:
    case = _plnt_case()
    case["comparison_basis"] = "open_ended"
    with pytest.raises(CaseShapeError):
        project_economic_change(case)


def test_malformed_case_refuses_missing_facts() -> None:
    case = _plnt_case()
    case.pop("facts")
    with pytest.raises(CaseShapeError):
        project_economic_change(case)


def test_malformed_case_refuses_facts_wrong_type() -> None:
    case = _plnt_case()
    case["facts"] = "not a list"
    with pytest.raises(CaseShapeError):
        project_economic_change(case)


# ---------------------------------------------------------------------------
# Dependency-local degradation
# ---------------------------------------------------------------------------


def test_dependency_local_degradation_missing_total_revenue_prior() -> None:
    """Missing one fact value suppresses only the results that depend on it."""
    facts = _plnt_facts()
    facts = [f for f in facts if not (
        f["key"] == FACT_KEY_TOTAL_REVENUE and f["period_end"] == "2025-06-30"
    )]
    case = _plnt_case(facts=facts)
    document = project_economic_change(case)
    # Advertising results stay READY (no dependency on total_revenue).
    assert _result_by_key(document, RESULT_KEY_ADVERTISING_REVENUE_CHANGE)["state"] == "READY"
    assert _result_by_key(document, RESULT_KEY_ADVERTISING_EXPENSE_CHANGE)["state"] == "READY"
    assert _result_by_key(document, RESULT_KEY_ADVERTISING_NET_CHANGE)["state"] == "READY"
    # total_revenue_change is suppressed; the share-of-revenue ratio is withheld.
    total_keys = {r["key"] for r in document["results"]}
    assert RESULT_KEY_TOTAL_REVENUE_CHANGE not in total_keys
    share = _result_by_key(document, RESULT_KEY_ADVERTISING_SHARE_OF_REVENUE_CHANGE_PCT)
    assert share["state"] == "WITHHELD"
    assert share["value_text"] is None
    # Degradation is recorded.
    degraded_reasons = [d["reason"] for d in document["degraded_dependencies"]]
    assert "no_compatible_pair_for_comparison_basis" in degraded_reasons


def test_dependency_local_degradation_unparseable_value_text() -> None:
    """A fact with unparseable value_text suppresses its result only."""
    facts = _plnt_facts()
    for f in facts:
        if f["key"] == FACT_KEY_TOTAL_REVENUE and f["period_end"] == "2025-06-30":
            f["value_text"] = "not-a-number"
            break
    case = _plnt_case(facts=facts)
    document = project_economic_change(case)
    # Advertising change results stay READY.
    assert _result_by_key(document, RESULT_KEY_ADVERTISING_REVENUE_CHANGE)["state"] == "READY"
    # Total revenue change is suppressed.
    total_keys = {r["key"] for r in document["results"]}
    assert RESULT_KEY_TOTAL_REVENUE_CHANGE not in total_keys
    # Share-of-revenue withheld (dependency).
    share = _result_by_key(document, RESULT_KEY_ADVERTISING_SHARE_OF_REVENUE_CHANGE_PCT)
    assert share["state"] == "WITHHELD"
    reasons = [d["reason"] for d in document["degraded_dependencies"]]
    assert "fact_value_text_unparseable" in reasons


def test_dependency_local_degradation_research_oracle_native_admitted_false() -> None:
    """Frozen-spec section 7: research values with native_admitted=False are not retained receipts."""
    facts = _plnt_facts()
    for f in facts:
        if f["key"] == FACT_KEY_TOTAL_REVENUE and f["period_end"] == "2025-06-30":
            f["native_admitted"] = False
            break
    case = _plnt_case(facts=facts)
    document = project_economic_change(case)
    total_keys = {r["key"] for r in document["results"]}
    assert RESULT_KEY_TOTAL_REVENUE_CHANGE not in total_keys
    reasons = [d["reason"] for d in document["degraded_dependencies"]]
    assert "fact_native_admitted_false" in reasons


def test_dependency_local_degradation_keeps_ready_results_distinct() -> None:
    """A single missing fact must NOT suppress unrelated ready results."""
    facts = _plnt_facts()
    facts = [f for f in facts if not (
        f["key"] == FACT_KEY_ADVERTISING_EXPENSE and f["period_end"] == "2025-06-30"
    )]
    case = _plnt_case(facts=facts)
    document = project_economic_change(case)
    # total_revenue_change and advertising_revenue_change stay READY.
    assert _result_by_key(document, RESULT_KEY_TOTAL_REVENUE_CHANGE)["state"] == "READY"
    assert _result_by_key(document, RESULT_KEY_ADVERTISING_REVENUE_CHANGE)["state"] == "READY"
    # advertising_expense_change is suppressed.
    keys = {r["key"] for r in document["results"]}
    assert RESULT_KEY_ADVERTISING_EXPENSE_CHANGE not in keys
    # advertising_net_change is withheld (depends on advertising_expense_change).
    net = _result_by_key(document, RESULT_KEY_ADVERTISING_NET_CHANGE)
    assert net["state"] == "WITHHELD"


# ---------------------------------------------------------------------------
# Unavailable on zero ready (section 6 rule 3)
# ---------------------------------------------------------------------------


def test_availability_unavailable_when_no_facts() -> None:
    case = _plnt_case(facts=[])
    document = project_economic_change(case)
    assert document["availability"] == "unavailable"
    # Zero READY results — the 3 derived WITHHELD envelopes are still
    # emitted so the explanation and downstream callers can see why
    # each one was suppressed; none of them is READY.
    assert all(r["state"] != "READY" for r in document["results"])
    assert all(r["value_text"] is None for r in document["results"])
    assert document["degraded_dependencies"] == []


def test_availability_unavailable_when_only_malformed_facts() -> None:
    """A single malformed fact yields zero ready results -> unavailable, never empty ready."""
    facts = [
        _plnt_fact(
            key=FACT_KEY_TOTAL_REVENUE,
            period_end="2026-06-30",
            value_text="not-a-number",
            native_ref="src-bad-1",
        ),
        _plnt_fact(
            key=FACT_KEY_TOTAL_REVENUE,
            period_end="2025-06-30",
            value_text="also-bad",
            native_ref="src-bad-2",
        ),
    ]
    case = _plnt_case(facts=facts)
    document = project_economic_change(case)
    assert document["availability"] == "unavailable"
    assert all(r["state"] == "WITHHELD" for r in document["results"]) or document["results"] == []
    reasons = [d["reason"] for d in document["degraded_dependencies"]]
    assert "fact_value_text_unparseable" in reasons


def test_availability_unavailable_when_research_oracles_only() -> None:
    facts = _plnt_facts()
    for f in facts:
        f["native_admitted"] = False
    case = _plnt_case(facts=facts)
    document = project_economic_change(case)
    assert document["availability"] == "unavailable"


def test_unavailable_never_renders_as_ready() -> None:
    case = _plnt_case(facts=[])
    document = project_economic_change(case)
    assert document["availability"] != "ready"
    assert document["availability"] == "unavailable"


# ---------------------------------------------------------------------------
# Ratio withholding (section 6 rule 6)
# ---------------------------------------------------------------------------


def test_ratio_withheld_on_nonpositive_denominator_zero() -> None:
    """When total_revenue_change == 0 the ratio is WITHHELD with denominator_nonpositive."""
    facts = [
        _plnt_fact(
            key=FACT_KEY_TOTAL_REVENUE,
            period_end="2026-06-30",
            value_text="100",
            native_ref="src-tr-c",
        ),
        _plnt_fact(
            key=FACT_KEY_TOTAL_REVENUE,
            period_end="2025-06-30",
            value_text="100",
            native_ref="src-tr-p",
        ),
        _plnt_fact(
            key=FACT_KEY_ADVERTISING_REVENUE,
            period_end="2026-06-30",
            value_text="50",
            native_ref="src-ar-c",
        ),
        _plnt_fact(
            key=FACT_KEY_ADVERTISING_REVENUE,
            period_end="2025-06-30",
            value_text="40",
            native_ref="src-ar-p",
        ),
    ]
    document = project_economic_change(_plnt_case(facts=facts))
    share = _result_by_key(document, RESULT_KEY_ADVERTISING_SHARE_OF_REVENUE_CHANGE_PCT)
    assert share["state"] == "WITHHELD"
    assert share["value_text"] is None
    assert share["value_decimal"] is None
    assert share["withheld_reason"] == "denominator_nonpositive"


def test_ratio_withheld_on_negative_denominator() -> None:
    """When total_revenue_change is negative the ratio is WITHHELD with denominator_nonpositive."""
    facts = [
        _plnt_fact(
            key=FACT_KEY_TOTAL_REVENUE,
            period_end="2026-06-30",
            value_text="100",
            native_ref="src-tr-c",
        ),
        _plnt_fact(
            key=FACT_KEY_TOTAL_REVENUE,
            period_end="2025-06-30",
            value_text="200",
            native_ref="src-tr-p",
        ),
        _plnt_fact(
            key=FACT_KEY_ADVERTISING_REVENUE,
            period_end="2026-06-30",
            value_text="50",
            native_ref="src-ar-c",
        ),
        _plnt_fact(
            key=FACT_KEY_ADVERTISING_REVENUE,
            period_end="2025-06-30",
            value_text="40",
            native_ref="src-ar-p",
        ),
    ]
    document = project_economic_change(_plnt_case(facts=facts))
    share = _result_by_key(document, RESULT_KEY_ADVERTISING_SHARE_OF_REVENUE_CHANGE_PCT)
    assert share["state"] == "WITHHELD"
    assert share["withheld_reason"] == "denominator_nonpositive"


def test_ratio_withheld_when_denominator_envelope_includes_zero() -> None:
    """Frozen-spec section 6 rule 6: ratio withheld when the denominator's
    declared rounding_envelope includes zero, even when the realised
    value is positive."""
    facts = [
        _plnt_fact(
            key=FACT_KEY_TOTAL_REVENUE,
            period_end="2026-06-30",
            value_text="100",
            native_ref="src-tr-c",
            rounding_envelope={"includes_zero": True},
        ),
        _plnt_fact(
            key=FACT_KEY_TOTAL_REVENUE,
            period_end="2025-06-30",
            value_text="50",
            native_ref="src-tr-p",
            rounding_envelope={"includes_zero": True},
        ),
        _plnt_fact(
            key=FACT_KEY_ADVERTISING_REVENUE,
            period_end="2026-06-30",
            value_text="80",
            native_ref="src-ar-c",
        ),
        _plnt_fact(
            key=FACT_KEY_ADVERTISING_REVENUE,
            period_end="2025-06-30",
            value_text="40",
            native_ref="src-ar-p",
        ),
    ]
    document = project_economic_change(_plnt_case(facts=facts))
    share = _result_by_key(document, RESULT_KEY_ADVERTISING_SHARE_OF_REVENUE_CHANGE_PCT)
    assert share["state"] == "WITHHELD"
    assert share["withheld_reason"] == "denominator_rounding_envelope_includes_zero"


# ---------------------------------------------------------------------------
# Greater-than-100% passthrough (section 6 rule 6)
# ---------------------------------------------------------------------------


def test_ratio_greater_than_100_passes_through() -> None:
    """Percentages > 100 are NOT automatically invalid."""
    facts = [
        _plnt_fact(
            key=FACT_KEY_TOTAL_REVENUE,
            period_end="2026-06-30",
            value_text="100",
            native_ref="src-tr-c",
        ),
        _plnt_fact(
            key=FACT_KEY_TOTAL_REVENUE,
            period_end="2025-06-30",
            value_text="50",
            native_ref="src-tr-p",
        ),
        _plnt_fact(
            key=FACT_KEY_ADVERTISING_REVENUE,
            period_end="2026-06-30",
            value_text="200",
            native_ref="src-ar-c",
        ),
        _plnt_fact(
            key=FACT_KEY_ADVERTISING_REVENUE,
            period_end="2025-06-30",
            value_text="40",
            native_ref="src-ar-p",
        ),
    ]
    document = project_economic_change(_plnt_case(facts=facts))
    share = _result_by_key(document, RESULT_KEY_ADVERTISING_SHARE_OF_REVENUE_CHANGE_PCT)
    assert share["state"] == "READY"
    # advertising_revenue_change = 200 - 40 = 160; total_revenue_change = 50;
    # 160 / 50 = 3.2 -> 320.00%.
    assert share["value_text"] == "320.00"


# ---------------------------------------------------------------------------
# Missing/invalid result is never zero, never bearish
# ---------------------------------------------------------------------------


def test_withheld_is_never_zero_and_never_bearish() -> None:
    """A missing result is rendered as None (withheld_reason), never 0 or bearish text."""
    facts = [
        _plnt_fact(
            key=FACT_KEY_TOTAL_REVENUE,
            period_end="2026-06-30",
            value_text="100",
            native_ref="src-tr-c",
        ),
        _plnt_fact(
            key=FACT_KEY_TOTAL_REVENUE,
            period_end="2025-06-30",
            value_text="100",
            native_ref="src-tr-p",
        ),
        _plnt_fact(
            key=FACT_KEY_ADVERTISING_REVENUE,
            period_end="2026-06-30",
            value_text="50",
            native_ref="src-ar-c",
        ),
        _plnt_fact(
            key=FACT_KEY_ADVERTISING_REVENUE,
            period_end="2025-06-30",
            value_text="40",
            native_ref="src-ar-p",
        ),
    ]
    document = project_economic_change(_plnt_case(facts=facts))
    share = _result_by_key(document, RESULT_KEY_ADVERTISING_SHARE_OF_REVENUE_CHANGE_PCT)
    assert share["state"] == "WITHHELD"
    assert share["value_text"] is None
    assert share["value_decimal"] is None
    assert share["withheld_reason"]
    assert share["value_text"] != "0"


# ---------------------------------------------------------------------------
# Forbidden-conclusion guard (section 5)
# ---------------------------------------------------------------------------


def test_check_explanation_for_forbidden_rejects_dues_as_observed_visits() -> None:
    bad = {
        "lead": "Dues are observed visits in this period.",
        "counterevidence": "no",
        "next_observation": "no",
        "does_not_prove": "no",
    }
    with pytest.raises(CaseShapeError) as exc:
        _check_explanation_for_forbidden(bad)
    assert "dues_described_as_observed_visits" in str(exc.value)


def test_check_explanation_for_forbidden_rejects_organic_growth_label() -> None:
    bad = {
        "lead": "After subtracting advertising alone, the remainder is organic growth.",
        "counterevidence": "no",
        "next_observation": "no",
        "does_not_prove": "no",
    }
    with pytest.raises(CaseShapeError) as exc:
        _check_explanation_for_forbidden(bad)
    assert "advertising_alone_called_organic_growth" in str(exc.value)


def test_check_explanation_for_forbidden_accepts_default_explanation() -> None:
    """The default explanation text must NOT trigger the guard."""
    document = project_economic_change(_plnt_case())
    _check_explanation_for_forbidden(document["explanation"])


def test_check_explanation_for_forbidden_rejects_isolated_advertising_organic() -> None:
    bad = {
        "lead": "Subtracting advertising isolates the organic remainder.",
        "counterevidence": "no",
        "next_observation": "no",
        "does_not_prove": "no",
    }
    with pytest.raises(CaseShapeError) as exc:
        _check_explanation_for_forbidden(bad)
    assert "advertising_alone_called_organic_growth" in str(exc.value)


# ---------------------------------------------------------------------------
# Authority-key guard (section 6 rule 10)
# ---------------------------------------------------------------------------


def test_authority_key_guard_refuses_rank_field() -> None:
    case = _plnt_case()
    document = project_economic_change(case)
    # The default document never carries a forbidden authority key.
    forbidden = {"rank", "score", "entry", "gate", "sizing", "origination", "attractiveness", "composite"}
    def walk(node: object) -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                if isinstance(k, str) and k in forbidden:
                    raise AssertionError("forbidden authority key present: " + k)
                walk(v)
        elif isinstance(node, (list, tuple)):
            for child in node:
                walk(child)
    walk(document)


# ---------------------------------------------------------------------------
# result key set
# ---------------------------------------------------------------------------


def test_results_emitted_keys_match_golden_set() -> None:
    document = project_economic_change(_plnt_case())
    emitted_keys = {r["key"] for r in document["results"]}
    assert emitted_keys == {
        RESULT_KEY_TOTAL_REVENUE_CHANGE,
        RESULT_KEY_ADVERTISING_REVENUE_CHANGE,
        RESULT_KEY_ADVERTISING_EXPENSE_CHANGE,
        RESULT_KEY_ADVERTISING_NET_CHANGE,
        RESULT_KEY_ADVERTISING_CURRENT_PERIOD_NET,
        RESULT_KEY_ADVERTISING_SHARE_OF_REVENUE_CHANGE_PCT,
    }


def test_results_sorted_deterministically_by_key() -> None:
    document = project_economic_change(_plnt_case())
    keys = [r["key"] for r in document["results"]]
    assert keys == sorted(keys)
