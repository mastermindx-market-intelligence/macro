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

import re
from decimal import Decimal

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


#: Stated period starts for the synthetic case. These used to be derived as
#: ``period_end[:4] + "-01-01"``, which described a Q2 as running from 1
#: January -- the *same* calendar-snapping mistake the projection itself was
#: making, which is exactly why 65 green tests never caught it. The suite now
#: states its periods instead of deriving them.
_PERIOD_START_BY_END = {
    "2026-06-30": "2026-04-01",
    "2025-06-30": "2025-04-01",
}


def _plnt_fact(
    *,
    key: str,
    period_end: str,
    value_text: str,
    native_ref: str,
    metric: str = "",
    definition: str = "",
    basis: str = "as_reported_period_value",
    role: str = "actual",
    unit: str = "USD",
    scale_power10: int = 3,
    sign_convention: str = "signed_as_reported",
    period_kind: str = "quarter",
    # frozen-spec 4a: PLNT's exhibit is retained nowhere, so False is the only
    # state that can occur for a real fact here. native_admitted is a
    # provenance label, never a suppression gate.
    native_admitted: bool = False,
    rounding_envelope: dict[str, Any] | None = None,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    # Facts pair on ``metric`` (the contract keys them <metric>_current /
    # <metric>_prior); derive it from the key when a test does not say.
    metric = metric or re.sub(r"_(current|prior|new|old)$", "", key)
    return {
        "key": key,
        "metric": metric,
        "value_text": value_text,
        "unit": unit,
        "scale_power10": scale_power10,
        "sign_convention": sign_convention,
        "period_start": _PERIOD_START_BY_END[period_end],
        "period_end": period_end,
        "period_kind": period_kind,
        "event": "plnt_q2_2026_results",
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
    ready_keys = {r["key"] for r in document["results"] if r["withheld_reason"] is None}
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
    assert Decimal(net["value_text"]) == Decimal("-4")


def test_plnt_percentage_uses_quantize_two_places_half_up() -> None:
    """Precision law: 2dp ROUND_HALF_UP. 10141/24344 = 41.657069... -> 41.66."""
    document = project_economic_change(_plnt_case())
    pct = _result_by_key(document, RESULT_KEY_ADVERTISING_SHARE_OF_REVENUE_CHANGE_PCT)
    assert pct["value_text"] == "41.66"
    assert pct["unit"] == "percent"
    assert pct["sign_convention"] == "signed_difference"


def test_plnt_input_refs_are_bound_per_result() -> None:
    """Frozen-spec section 6 rule 2: every ready result binds its input refs."""
    document = project_economic_change(_plnt_case())
    for r in document["results"]:
        if r["withheld_reason"] is not None:
            continue
        assert isinstance(r["input_refs"], list)
        assert r["input_refs"], "input_refs must be non-empty for ready results"


def test_plnt_unit_scale_sign_preserved() -> None:
    """Frozen-spec section 6 rule 1: derived results carry ``signed_difference``
    and preserve the source fact's ``scale_power10`` and ``unit``."""
    document = project_economic_change(_plnt_case())
    total = _result_by_key(document, RESULT_KEY_TOTAL_REVENUE_CHANGE)
    assert total["unit"] == "USD"
    assert total["scale_power10"] == 3
    assert total["sign_convention"] == "signed_difference"


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
    """Missing one fact value OMITS the results that depend on it (Ruling A).

    Ruling A: inputs absent -> no result, recorded in
    ``degraded_dependencies``; NOT a phantom WITHHELD result.
    """
    facts = _plnt_facts()
    facts = [f for f in facts if not (
        f["key"] == FACT_KEY_TOTAL_REVENUE and f["period_end"] == "2025-06-30"
    )]
    case = _plnt_case(facts=facts)
    document = project_economic_change(case)
    # Advertising results stay READY (no dependency on total_revenue).
    assert _result_by_key(document, RESULT_KEY_ADVERTISING_REVENUE_CHANGE)["value_text"] == "10141"
    assert _result_by_key(document, RESULT_KEY_ADVERTISING_EXPENSE_CHANGE)["value_text"] == "10145"
    assert _result_by_key(document, RESULT_KEY_ADVERTISING_NET_CHANGE)["value_text"] == "-4"
    # total_revenue_change and share ratio are OMITTED — they have no
    # inputs and never reach ``results``.
    emitted_keys = {r["key"] for r in document["results"]}
    assert RESULT_KEY_TOTAL_REVENUE_CHANGE not in emitted_keys
    assert RESULT_KEY_ADVERTISING_SHARE_OF_REVENUE_CHANGE_PCT not in emitted_keys
    # Omission is recorded in ``degraded_dependencies``.
    deps = [d.get("dependency") or d.get("fact_key") for d in document["degraded_dependencies"]]
    assert RESULT_KEY_TOTAL_REVENUE_CHANGE in deps
    assert RESULT_KEY_ADVERTISING_SHARE_OF_REVENUE_CHANGE_PCT in deps


def test_dependency_local_degradation_unparseable_value_text() -> None:
    """A fact with unparseable ``value_text`` OMITS the result (Ruling A)."""
    facts = _plnt_facts()
    for f in facts:
        if f["key"] == FACT_KEY_TOTAL_REVENUE and f["period_end"] == "2025-06-30":
            f["value_text"] = "not-a-number"
            break
    case = _plnt_case(facts=facts)
    document = project_economic_change(case)
    # Advertising change results stay READY.
    assert _result_by_key(document, RESULT_KEY_ADVERTISING_REVENUE_CHANGE)["value_text"] == "10141"
    # Total revenue change and share ratio are OMITTED.
    emitted_keys = {r["key"] for r in document["results"]}
    assert RESULT_KEY_TOTAL_REVENUE_CHANGE not in emitted_keys
    assert RESULT_KEY_ADVERTISING_SHARE_OF_REVENUE_CHANGE_PCT not in emitted_keys
    # Degraded dependencies explain why.
    deps = [d for d in document["degraded_dependencies"]]
    join = " ".join(
        (str(d.get("reason") or "") + " " + str(d.get("dependency") or ""))
        for d in deps
    )
    assert "fact_value_text_unparseable" in join or "ready_result_unavailable" in join


def test_dependency_local_degradation_research_oracle_native_admitted_false() -> None:
    """R15 section 4a: ``native_admitted`` is a provenance label, NOT a
    suppression gate. Research-oracle facts still produce results.
    """
    facts = _plnt_facts()
    for f in facts:
        f["native_admitted"] = False
    case = _plnt_case(facts=facts)
    document = project_economic_change(case)
    # The full golden set is still emitted.
    assert document["availability"] == "ready"
    assert _result_by_key(document, RESULT_KEY_TOTAL_REVENUE_CHANGE)["value_text"] == "24344"
    assert _result_by_key(document, RESULT_KEY_ADVERTISING_REVENUE_CHANGE)["value_text"] == "10141"


def test_dependency_local_degradation_keeps_ready_results_distinct() -> None:
    """A single missing fact must NOT suppress unrelated ready results."""
    facts = _plnt_facts()
    facts = [f for f in facts if not (
        f["key"] == FACT_KEY_ADVERTISING_EXPENSE and f["period_end"] == "2025-06-30"
    )]
    case = _plnt_case(facts=facts)
    document = project_economic_change(case)
    # total_revenue_change and advertising_revenue_change stay READY.
    assert _result_by_key(document, RESULT_KEY_TOTAL_REVENUE_CHANGE)["value_text"] == "24344"
    assert _result_by_key(document, RESULT_KEY_ADVERTISING_REVENUE_CHANGE)["value_text"] == "10141"
    # advertising_expense_change is OMITTED; advertising_net_change
    # depends on it and is OMITTED too; advertising_share depends on
    # advertising_revenue + total (both present) and stays READY.
    emitted_keys = {r["key"] for r in document["results"]}
    assert RESULT_KEY_ADVERTISING_EXPENSE_CHANGE not in emitted_keys
    assert RESULT_KEY_ADVERTISING_NET_CHANGE not in emitted_keys
    assert RESULT_KEY_ADVERTISING_SHARE_OF_REVENUE_CHANGE_PCT in emitted_keys


# ---------------------------------------------------------------------------
# Unavailable on zero ready (section 6 rule 3)
# ---------------------------------------------------------------------------


def test_availability_unavailable_when_no_facts() -> None:
    """Ruling A: zero facts -> ``results == []``, ``unavailable``,
    ``degraded_dependencies`` lists every unmet result key."""
    case = _plnt_case(facts=[])
    document = project_economic_change(case)
    assert document["availability"] == "unavailable"
    assert document["results"] == []
    # Degraded dependencies are non-empty and explain every unmet result.
    deps = {d.get("dependency") for d in document["degraded_dependencies"]}
    assert deps == {
        RESULT_KEY_TOTAL_REVENUE_CHANGE,
        RESULT_KEY_ADVERTISING_REVENUE_CHANGE,
        RESULT_KEY_ADVERTISING_EXPENSE_CHANGE,
        RESULT_KEY_ADVERTISING_NET_CHANGE,
        RESULT_KEY_ADVERTISING_CURRENT_PERIOD_NET,
        RESULT_KEY_ADVERTISING_SHARE_OF_REVENUE_CHANGE_PCT,
    }


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
    assert all(r["withheld_reason"] is not None for r in document["results"]) or document["results"] == []
    reasons = [d["reason"] for d in document["degraded_dependencies"]]
    assert "fact_value_text_unparseable" in reasons


def test_availability_ready_when_research_oracles_only() -> None:
    """Defect 1 / R15: ``native_admitted=False`` is a PROVENANCE LABEL,
    never a suppression gate. The Q2 2026 PLNT exhibit is research
    oracles, so every fact carries ``native_admitted: False`` and the
    projection must still produce the full ready set."""
    facts = _plnt_facts()
    for f in facts:
        f["native_admitted"] = False
    case = _plnt_case(facts=facts)
    document = project_economic_change(case)
    assert document["availability"] == "ready"
    # The provenance label propagates to the emitted facts; nothing is
    # silently downgraded to withheld.
    assert all(f["native_admitted"] is False for f in document["facts"])
    assert _result_by_key(
        document, RESULT_KEY_TOTAL_REVENUE_CHANGE
    )["withheld_reason"] is None
    assert _result_by_key(
        document, RESULT_KEY_ADVERTISING_NET_CHANGE
    )["withheld_reason"] is None


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
    assert share["withheld_reason"] is not None
    assert share["value_text"] is None
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
    assert share["withheld_reason"] is not None
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
    assert share["withheld_reason"] is not None
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
    assert share["withheld_reason"] is None
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
    assert share["withheld_reason"] is not None
    assert share["value_text"] is None
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


# ---------------------------------------------------------------------------
# Real-path end-to-end gate
#
# The synthetic tests above can all pass while the module is unusable on the
# only inputs that can actually occur, so this gate drives the projection from
# the COMMITTED fixture — real PLNT facts, every one carrying
# ``native_admitted: false`` because the Q2 2026 exhibit is retained nowhere
# (frozen spec 4a) — and validates the emitted document against the contract
# itself rather than against this file's expectations.
# ---------------------------------------------------------------------------

import json as _json
from pathlib import Path as _Path

import pytest as _pytest

_ROOT = _Path(__file__).resolve().parents[1]
_SCHEMA = (
    _ROOT
    / "contracts"
    / "sector_intelligence"
    / "consumer_cyclical_intelligence_read_model.v1.schema.json"
)
_FIXTURE = (
    _ROOT
    / "data"
    / "sector_intelligence"
    / "fixtures"
    / "consumer_cyclical_intelligence_read_model.v1.valid.json"
)

# R6 section 7.1, USD thousands. The two advertising changes are NOT equal at
# displayed table precision — the -4 residual must survive.
_GOLDEN = {
    "total_revenue_change": "24344",
    "advertising_revenue_change": "10141",
    "advertising_expense_change": "10145",
    "advertising_net_change": "-4",
    "advertising_current_period_net": "0",
    "advertising_share_of_revenue_change_pct": "41.66",
}


def _fixture_case() -> dict[str, Any]:
    fixture = _json.loads(_FIXTURE.read_text())
    return {
        "subject": fixture["subject"],
        "comparison_basis": fixture["comparison_basis"],
        "facts": fixture["facts"],
        "generated_at": fixture["generated_at"],
        "source_records": fixture["source_records"],
    }


def _validator():
    jsonschema = _pytest.importorskip("jsonschema")
    return jsonschema.Draft202012Validator(_json.loads(_SCHEMA.read_text()))


def test_real_fixture_facts_are_all_research_oracles() -> None:
    """native_admitted must be False on every real fact (frozen spec 4a)."""
    facts = _fixture_case()["facts"]
    assert facts
    assert all(f["native_admitted"] is False for f in facts)
    assert all(f["native_ref"] is None for f in facts)


def test_real_path_reproduces_the_golden_oracle() -> None:
    """Non-admitted facts must still compute — provenance is not a gate."""
    document = project_economic_change(_fixture_case())
    emitted = {r["key"]: r["value_text"] for r in document["results"]}
    assert emitted == _GOLDEN
    assert document["availability"] == "ready"
    assert document["degraded_dependencies"] == []


def test_real_path_document_validates_against_the_contract() -> None:
    document = project_economic_change(_fixture_case())
    errors = sorted(_validator().iter_errors(document), key=lambda e: list(e.path))
    assert errors == [], [
        (list(e.path), e.message) for e in errors[:5]
    ]


def test_emitted_document_is_json_serialisable() -> None:
    """Ruling B: Decimal is an internal carrier and must never be emitted."""
    document = project_economic_change(_fixture_case())
    _json.dumps(document)
    for result in document["results"]:
        assert "value_decimal" not in result
        assert "state" not in result


def test_zero_facts_is_an_unavailable_document_not_phantom_results() -> None:
    """Ruling A: absent inputs are omitted and named, never emitted as nulls."""
    case = _fixture_case()
    case["facts"] = []
    document = project_economic_change(case)
    assert document["results"] == []
    assert document["availability"] == "unavailable"
    assert document["degraded_dependencies"]
    assert _validator().is_valid(document)


def test_every_emitted_result_binds_real_input_refs() -> None:
    document = project_economic_change(_fixture_case())
    fact_keys = {f["key"] for f in _fixture_case()["facts"]}
    for result in document["results"]:
        assert result["input_refs"], result["key"]
        assert set(result["input_refs"]) <= fact_keys, result["key"]


def test_explanation_carries_no_ranking_or_sizing_authority() -> None:
    explanation = project_economic_change(_fixture_case())["explanation"]
    forbidden = {
        "ranking",
        "rank",
        "position_size",
        "sizing",
        "entry",
        "gate",
        "score",
    }
    assert not (forbidden & set(explanation))
    assert explanation["lead"]
    assert explanation["counterevidence"]
    assert explanation["next_observation"]
    assert explanation["does_not_prove"]


def test_full_case_emits_the_r6_economic_lead_not_the_neutral_fallback() -> None:
    """The lead is what a user reads first, so it must carry the R6 7.1 reading.

    Regression: the selector compared the FACT_KEY_* constants against RESULT
    keys, so the economic lead was unreachable and every document silently
    fell through to the neutral "admitted without inference" fallback.
    """
    explanation = project_economic_change(_fixture_case())["explanation"]
    lead = explanation["lead"]
    assert "nearly matching expense" in lead
    assert "one-for-one" in lead
    assert "admitted without inference" not in lead


def test_a_degraded_case_falls_back_to_the_neutral_lead() -> None:
    """The economic lead is only claimed when its three results are all ready."""
    case = _fixture_case()
    case["facts"] = [
        f for f in case["facts"] if not f["key"].startswith("advertising_expense")
    ]
    explanation = project_economic_change(case)["explanation"]
    assert "nearly matching expense" not in explanation["lead"]


def test_result_keys_and_fact_keys_are_never_interchangeable() -> None:
    """Pin the invariant whose violation caused two separate defects.

    A fact identifier is not a result identifier. The two spellings currently
    coincide (`advertising_revenue` + `_change` == `advertising_revenue_change`),
    which is exactly why confusing them stayed silent: the economic lead was
    unreachable on every input, and facts grouped on `key` never paired.
    """
    from engine.sector_intelligence import consumer_cyclical_projection as mod

    fact_keys = {
        mod.FACT_KEY_TOTAL_REVENUE,
        mod.FACT_KEY_ADVERTISING_REVENUE,
        mod.FACT_KEY_ADVERTISING_EXPENSE,
    }
    result_keys = {
        mod.RESULT_KEY_TOTAL_REVENUE_CHANGE,
        mod.RESULT_KEY_ADVERTISING_REVENUE_CHANGE,
        mod.RESULT_KEY_ADVERTISING_EXPENSE_CHANGE,
        mod.RESULT_KEY_ADVERTISING_NET_CHANGE,
        mod.RESULT_KEY_ADVERTISING_CURRENT_PERIOD_NET,
        mod.RESULT_KEY_ADVERTISING_SHARE_OF_REVENUE_CHANGE_PCT,
    }
    assert not (fact_keys & result_keys)

    document = project_economic_change(_fixture_case())
    emitted_result_keys = {r["key"] for r in document["results"]}
    emitted_fact_keys = {f["key"] for f in document["facts"]}
    assert emitted_result_keys <= result_keys
    assert not (emitted_result_keys & emitted_fact_keys)
    # input_refs name FACT keys, never result keys
    for result in document["results"]:
        assert set(result["input_refs"]) <= emitted_fact_keys
        assert not (set(result["input_refs"]) & result_keys)


def test_facts_are_grouped_by_metric_not_by_key() -> None:
    """Facts keyed <metric>_current/_prior must still pair on their metric."""
    from engine.sector_intelligence import consumer_cyclical_projection as mod

    grouped = mod._index_facts_by_metric(_fixture_case()["facts"])
    assert set(grouped) == {
        "total_revenue",
        "advertising_revenue",
        "advertising_expense",
    }
    assert all(len(v) == 2 for v in grouped.values())


# ---------------------------------------------------------------------------
# Envelope integrity — the projection must never publish a document that
# violates the contract it authors.
#
# These exist because the suite that preceded them was green while the module
# emitted empty dates, an out-of-vocabulary period_kind and non-numeric
# value_text: every assertion read the *numbers*, none re-read the emitted
# document against the schema sitting beside it in the repository.
# ---------------------------------------------------------------------------


def _fixture_case_with(mutate) -> dict[str, Any]:
    """The real fixture case with ``mutate`` applied to a copy of each fact."""
    case = _fixture_case()
    case["facts"] = [dict(fact) for fact in case["facts"]]
    for fact in case["facts"]:
        mutate(fact)
    return case


def test_thousands_separated_value_text_degrades_rather_than_breaking_the_contract() -> None:
    """A comma is how humans write money; it must not corrupt the document."""
    case = _fixture_case_with(
        lambda fact: fact.__setitem__("value_text", f"{int(fact['value_text']):,}")
    )
    assert case["facts"][0]["value_text"] == "365,223"

    document = project_economic_change(case)

    assert list(_validator().iter_errors(document)) == []
    assert document["facts"] == []
    assert document["availability"] == "unavailable"
    assert "fact_value_text_unparseable" in {
        entry["reason"] for entry in document["degraded_dependencies"]
    }


def test_a_fact_missing_its_period_envelope_is_refused_not_silently_completed() -> None:
    """Absent envelope fields are declared, never filled in with a guess."""
    for field, reason in (
        ("period_start", "fact_period_start_missing_or_malformed"),
        ("period_kind", "fact_period_kind_outside_vocabulary"),
        ("period_end", "fact_period_end_missing_or_malformed"),
    ):
        case = _fixture_case_with(lambda fact: fact.pop(field, None))
        document = project_economic_change(case)

        assert list(_validator().iter_errors(document)) == [], field
        assert document["facts"] == [], field
        assert reason in {
            entry["reason"] for entry in document["degraded_dependencies"]
        }, field


def test_period_start_is_read_from_the_source_and_never_derived() -> None:
    """Consumer Cyclical is the retail sector; fiscal periods are not calendar ones.

    The removed fallback snapped ``period_end`` to a calendar boundary, so a
    4-5-4 retail quarter ending 2025-02-01 derived a start of 2025-01-01 — a
    valid-looking date describing a 32-day "quarter".
    """
    from engine.sector_intelligence import consumer_cyclical_projection as mod

    retail_quarter = {
        "period_end": "2025-02-01",
        "period_kind": "quarter",
        "value_text": "1000",
    }
    assert mod._envelope_period_start(retail_quarter) == ""
    assert (
        mod._fact_admission_failure(retail_quarter)
        == "fact_period_start_missing_or_malformed"
    )
    assert mod._envelope_period_start({"period_start": "2024-11-03"}) == "2024-11-03"


def test_a_withheld_result_still_carries_the_period_provenance_it_must() -> None:
    """Withholding a value never justified discarding where it came from."""
    flat = _fixture_case_with(
        lambda fact: fact.__setitem__("value_text", "365223")
        if fact["metric"] == "total_revenue"
        else None
    )
    document = project_economic_change(flat)

    assert list(_validator().iter_errors(document)) == []
    withheld = [r for r in document["results"] if r.get("value_text") is None]
    assert withheld, "a non-positive denominator must withhold the ratio"
    for result in withheld:
        assert result["period_end"], result["key"]
        assert result["period_start"], result["key"]
        assert result["event"], result["key"]


def test_module_constants_mirror_the_published_contract() -> None:
    """The runtime self-check is only as honest as its mirror of the schema."""
    from engine.sector_intelligence import consumer_cyclical_projection as mod

    schema = _json.loads(_SCHEMA.read_text())
    defs = schema["$defs"]
    fact = defs["fact"]["properties"]

    assert mod._DATE_RE.pattern == defs["date"]["pattern"]
    assert mod._VALUE_TEXT_RE.pattern == defs["value_text"]["pattern"]
    assert mod._SLUG_RE.pattern == fact["event"]["pattern"]
    assert mod._ALLOWED_PERIOD_KIND == frozenset(fact["period_kind"]["enum"])
    assert mod._ALLOWED_DEGRADED_STATE == frozenset(
        defs["degraded_dependency"]["properties"]["state"]["enum"]
    )


def test_the_document_self_check_refuses_a_contract_violating_document() -> None:
    """The backstop needs its own falsifier, or it is one more untested guard."""
    from engine.sector_intelligence import consumer_cyclical_projection as mod

    good = project_economic_change(_fixture_case())
    mod._assert_document_matches_contract_shape(good)

    for field, bad_value in (
        ("period_start", ""),
        ("period_end", "2026-6-30"),
        ("period_kind", "month"),
        ("value_text", "1,000"),
        ("event", "PLNT Q2 2026"),
    ):
        broken = _json.loads(_json.dumps(good))
        broken["facts"][0][field] = bad_value
        with pytest.raises(CaseShapeError) as excinfo:
            mod._assert_document_matches_contract_shape(broken)
        assert field in str(excinfo.value)
        assert CONTRACT_ID in str(excinfo.value)

    # Every collection the guard walks needs its own falsifier: a guard that
    # only ever reads one of them is exactly the half-blind instrument these
    # tests exist to prevent.
    for field, bad_value in (
        ("period_start", ""),
        ("period_kind", "month"),
        ("event", "PLNT Q2 2026"),
        ("value_text", "1,000"),
    ):
        broken = _json.loads(_json.dumps(good))
        assert broken["results"], "fixture must emit at least one result"
        broken["results"][0][field] = bad_value
        with pytest.raises(CaseShapeError, match=field):
            mod._assert_document_matches_contract_shape(broken)

    for field, bad_value in (("dependency", "Not A Slug"), ("state", "maybe")):
        broken = _json.loads(_json.dumps(good))
        broken["degraded_dependencies"] = [
            {"dependency": "total_revenue", "reason": "r", "state": "unavailable"}
        ]
        broken["degraded_dependencies"][0][field] = bad_value
        with pytest.raises(CaseShapeError, match=field):
            mod._assert_document_matches_contract_shape(broken)


def test_the_document_self_check_runs_on_every_projection(monkeypatch) -> None:
    """Wiring is a separate fact from correctness; assert it separately."""
    from engine.sector_intelligence import consumer_cyclical_projection as mod

    seen: list[Any] = []
    monkeypatch.setattr(
        mod, "_assert_document_matches_contract_shape", lambda document: seen.append(document)
    )
    project_economic_change(_fixture_case())
    assert len(seen) == 1
    assert seen[0]["contract_id"] == CONTRACT_ID
