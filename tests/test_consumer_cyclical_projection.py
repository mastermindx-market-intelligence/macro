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
    _DEFINITION_CONTRADICTED,
    _FORBIDDEN_BARE_KEYS,
    _LEAD_FULL,
    _LEAD_GENERIC,
    _assert_document_matches_contract_shape,
    _assert_no_forbidden_authority_keys,
    _check_explanation_for_forbidden,
    _emit_result,
    _screen_stated_definition,
    _stated_definition_contradicted,
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


#: metric -> the contract's ``kind`` vocabulary. Stated, never guessed: the
#: helper used to omit ``kind`` entirely and let the projection default it to
#: "financial", a value the contract's enum does not contain.
_KIND_BY_METRIC = {
    "total_revenue": "revenue_line",
    "advertising_revenue": "revenue_line",
    "advertising_expense": "expense_line",
}

#: metric -> the phrase a human would read in the exhibit's results table.
_LABEL_BY_METRIC = {
    "total_revenue": "Total revenue",
    "advertising_revenue": "Advertising revenue",
    "advertising_expense": "Advertising expense",
}


def _plnt_fact(
    *,
    key: str,
    period_end: str,
    value_text: str,
    native_ref: str,
    metric: str = "",
    period_role: str = "",
    kind: str = "",
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
    # ``input_refs`` names the fact KEY (see _fact_ref in the projection) and
    # the contract declares it uniqueItems, so the two facts of one pair must
    # not share a key. They did: every same-metric pair in this helper was
    # spelled with one bare FACT_KEY_* constant, which published
    # ["advertising_expense", "advertising_expense"]. Callers that still pass a
    # bare key keep today's behaviour; period_role is how a pair says which
    # side it is.
    if period_role:
        key = key + "_" + period_role
    kind = kind or _KIND_BY_METRIC.get(metric, "")
    if not definition:
        label = _LABEL_BY_METRIC.get(metric, metric.replace("_", " ").capitalize())
        definition = (
            label
            + " for the quarter ended "
            + period_end
            + ", as reported in PLNT's Q2 2026 results press release exhibit."
        )
    return {
        "key": key,
        "kind": kind,
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
        # Contract pattern ^\\d+(?:\\.\\d+)?_[a-z][a-z0-9_]*$ - a quantum, not a
        # unit label. "USD thousands" is the unit spelled twice; the scale
        # already lives in unit + scale_power10.
        "display_quantum": "1_thousand",
        "native_admitted": native_admitted,
        "native_ref": native_ref,
        # Was the CONTRACT ID, copied into a field whose enum is
        # {consolidated_company, segment, franchise_system}.
        "perimeter": "consolidated_company",
        "role": role,
        "target": "issuer:0001637207",
        "evidence": evidence
        or {
            "document": "plntq22026pressreleaseex991.htm",
            "locator": "press_release_table",
            "revision": "2026-08-06",
        },
        "rounding_envelope": rounding_envelope,
    }


def _plnt_subject() -> dict[str, Any]:
    # $defs/subject is closed (additionalProperties false) and requires exactly
    # issuer_cik, subject_type and ticker. company_name and fiscal_period_end
    # were never published anywhere, and comparison_basis is a CASE field that
    # was being shadowed here.
    return {
        "issuer_cik": "0001637207",
        "ticker": "PLNT",
        "subject_type": "company",
    }


def _plnt_facts() -> list[dict[str, Any]]:
    """Build the PLNT Q2 2026 frozen oracle as a 6-fact case.

    The values are byte-identical to frozen-spec section 5.
    """
    return [
        _plnt_fact(
            key=FACT_KEY_TOTAL_REVENUE,
            period_role="current",
            period_end="2026-06-30",
            value_text="365223",
            native_ref="src_plnt_q2_2026_ex991",
        ),
        _plnt_fact(
            key=FACT_KEY_TOTAL_REVENUE,
            period_role="prior",
            period_end="2025-06-30",
            value_text="340879",
            native_ref="src_plnt_q2_2026_ex991",
        ),
        _plnt_fact(
            key=FACT_KEY_ADVERTISING_REVENUE,
            period_role="current",
            period_end="2026-06-30",
            value_text="32922",
            native_ref="src_plnt_q2_2026_ex991",
        ),
        _plnt_fact(
            key=FACT_KEY_ADVERTISING_REVENUE,
            period_role="prior",
            period_end="2025-06-30",
            value_text="22781",
            native_ref="src_plnt_q2_2026_ex991",
        ),
        _plnt_fact(
            key=FACT_KEY_ADVERTISING_EXPENSE,
            period_role="current",
            period_end="2026-06-30",
            value_text="32922",
            native_ref="src_plnt_q2_2026_ex991",
        ),
        _plnt_fact(
            key=FACT_KEY_ADVERTISING_EXPENSE,
            period_role="prior",
            period_end="2025-06-30",
            value_text="22777",
            native_ref="src_plnt_q2_2026_ex991",
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
        # ONE record, not six. $defs/source_record requires twelve fields and
        # these were one-key stubs; more importantly a results press release
        # carries the prior-year comparatives in the same table, so six facts
        # genuinely share one document. Values are the ones the committed
        # fixture asserts - not invented. The clock is deliberately unlabeled
        # and carries no Z: SEC acceptance time is not first-public time.
        "source_records": [
            {
                "record_id": "src_plnt_q2_2026_ex991",
                "accession_no": "0001637207-26-000042",
                "issuer_cik": "0001637207",
                "publisher": "U.S. Securities and Exchange Commission",
                "source_family": "sec_edgar_exhibit",
                "document": "plntq22026pressreleaseex991.htm",
                "source_uri": (
                    "https://www.sec.gov/Archives/edgar/data/1637207/"
                    "000163720726000042/plntq22026pressreleaseex991.htm"
                ),
                "locator": (
                    "Exhibit 99.1, PLNT Q2 2026 results press release, "
                    "accession 0001637207-26-000042"
                ),
                "sec_acceptance_raw": "2026-08-06 06:30:44",
                "acceptance_clock_basis": "unlabeled",
                "observed_at": "2026-09-24",
                # frozen-spec 4a: PLNT's exhibit is retained nowhere.
                "retention_state": "not_retained",
            }
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
        f["metric"] == FACT_KEY_TOTAL_REVENUE and f["period_end"] == "2025-06-30"
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
        if f["metric"] == FACT_KEY_TOTAL_REVENUE and f["period_end"] == "2025-06-30":
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
        f["metric"] == FACT_KEY_ADVERTISING_EXPENSE and f["period_end"] == "2025-06-30"
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
            native_ref="src_plnt_q2_2026_ex991",
        ),
        _plnt_fact(
            key=FACT_KEY_TOTAL_REVENUE,
            period_end="2025-06-30",
            value_text="also-bad",
            native_ref="src_plnt_q2_2026_ex991",
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
            native_ref="src_plnt_q2_2026_ex991",
        ),
        _plnt_fact(
            key=FACT_KEY_TOTAL_REVENUE,
            period_end="2025-06-30",
            value_text="100",
            native_ref="src_plnt_q2_2026_ex991",
        ),
        _plnt_fact(
            key=FACT_KEY_ADVERTISING_REVENUE,
            period_end="2026-06-30",
            value_text="50",
            native_ref="src_plnt_q2_2026_ex991",
        ),
        _plnt_fact(
            key=FACT_KEY_ADVERTISING_REVENUE,
            period_end="2025-06-30",
            value_text="40",
            native_ref="src_plnt_q2_2026_ex991",
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
            native_ref="src_plnt_q2_2026_ex991",
        ),
        _plnt_fact(
            key=FACT_KEY_TOTAL_REVENUE,
            period_end="2025-06-30",
            value_text="200",
            native_ref="src_plnt_q2_2026_ex991",
        ),
        _plnt_fact(
            key=FACT_KEY_ADVERTISING_REVENUE,
            period_end="2026-06-30",
            value_text="50",
            native_ref="src_plnt_q2_2026_ex991",
        ),
        _plnt_fact(
            key=FACT_KEY_ADVERTISING_REVENUE,
            period_end="2025-06-30",
            value_text="40",
            native_ref="src_plnt_q2_2026_ex991",
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
            native_ref="src_plnt_q2_2026_ex991",
            rounding_envelope={"includes_zero": True},
        ),
        _plnt_fact(
            key=FACT_KEY_TOTAL_REVENUE,
            period_end="2025-06-30",
            value_text="50",
            native_ref="src_plnt_q2_2026_ex991",
            rounding_envelope={"includes_zero": True},
        ),
        _plnt_fact(
            key=FACT_KEY_ADVERTISING_REVENUE,
            period_end="2026-06-30",
            value_text="80",
            native_ref="src_plnt_q2_2026_ex991",
        ),
        _plnt_fact(
            key=FACT_KEY_ADVERTISING_REVENUE,
            period_end="2025-06-30",
            value_text="40",
            native_ref="src_plnt_q2_2026_ex991",
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
            native_ref="src_plnt_q2_2026_ex991",
        ),
        _plnt_fact(
            key=FACT_KEY_TOTAL_REVENUE,
            period_end="2025-06-30",
            value_text="50",
            native_ref="src_plnt_q2_2026_ex991",
        ),
        _plnt_fact(
            key=FACT_KEY_ADVERTISING_REVENUE,
            period_end="2026-06-30",
            value_text="200",
            native_ref="src_plnt_q2_2026_ex991",
        ),
        _plnt_fact(
            key=FACT_KEY_ADVERTISING_REVENUE,
            period_end="2025-06-30",
            value_text="40",
            native_ref="src_plnt_q2_2026_ex991",
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
            native_ref="src_plnt_q2_2026_ex991",
        ),
        _plnt_fact(
            key=FACT_KEY_TOTAL_REVENUE,
            period_end="2025-06-30",
            value_text="100",
            native_ref="src_plnt_q2_2026_ex991",
        ),
        _plnt_fact(
            key=FACT_KEY_ADVERTISING_REVENUE,
            period_end="2026-06-30",
            value_text="50",
            native_ref="src_plnt_q2_2026_ex991",
        ),
        _plnt_fact(
            key=FACT_KEY_ADVERTISING_REVENUE,
            period_end="2025-06-30",
            value_text="40",
            native_ref="src_plnt_q2_2026_ex991",
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

    # Admission may be NARROWER than the contract; it may never be wider.
    # This set carried three bases to the contract's one, so two of them were
    # admitted, projected, and emitted as a document whose root enum the
    # contract rejects.
    assert mod._ALLOWED_COMPARISON_BASIS == frozenset(
        schema["properties"]["comparison_basis"]["enum"]
    )

    # Every admitted basis must declare the period kind it is ABOUT, or the
    # pair check silently skips the binding for that word.
    assert mod._ALLOWED_COMPARISON_BASIS <= frozenset(mod._BASIS_PERIOD_KIND)

    # STRUCTURAL, not a list: this test named five constants and omitted the
    # one that had drifted, which is how the drift survived. A new mirrored
    # vocabulary now fails here until it is pinned to the schema above.
    # Found BY the structural check below on its first run: matching the
    # contract today, but unpinned, so free to drift exactly as the basis set
    # did.
    assert mod._ALLOWED_KIND == frozenset(fact["kind"]["enum"])

    pinned = {"_ALLOWED_PERIOD_KIND", "_ALLOWED_COMPARISON_BASIS", "_ALLOWED_KIND"}
    mirrored = {
        name
        for name in dir(mod)
        if name.startswith("_ALLOWED_") and isinstance(getattr(mod, name), frozenset)
    }
    assert mirrored == pinned, (
        "a mirrored vocabulary is not pinned to the published contract: "
        + ", ".join(sorted(mirrored ^ pinned))
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


# ---------------------------------------------------------------------------
# The synthetic case is an input like any other — validate it like one
# ---------------------------------------------------------------------------


def test_the_synthetic_case_validates_against_the_contract_too() -> None:
    """The case this suite uses most was the one it never validated.

    ``_plnt_case()`` drove most of this file while emitting a document with
    102 violations of the contract the projection itself authors: twelve
    required ``source_record`` fields missing, ``perimeter`` holding the
    contract id, ``kind`` defaulted to a value outside its own enum,
    ``display_quantum`` spelled as a unit label, a closed ``subject`` carrying
    three extra keys, and non-unique ``input_refs``. Every assertion read a
    computed NUMBER; not one read the document's SHAPE, so all of it was
    invisible. This is that missing assertion.
    """
    document = project_economic_change(_plnt_case())
    errors = sorted(_validator().iter_errors(document), key=lambda e: list(e.path))
    assert errors == [], [(list(e.path), e.message) for e in errors[:5]]


def test_the_two_facts_of_a_pair_never_share_a_key() -> None:
    """``input_refs`` names the fact key and the contract declares it unique.

    A pair spelled with one bare ``FACT_KEY_*`` constant on both sides
    published ``["advertising_expense", "advertising_expense"]`` — an array the
    contract rejects — for every same-metric change.
    """
    keys = [f["key"] for f in _plnt_case()["facts"]]
    assert len(keys) == len(set(keys)), keys
    document = project_economic_change(_plnt_case())
    for result in document["results"]:
        refs = result.get("input_refs") or []
        assert len(refs) == len(set(refs)), (result["key"], refs)


def test_a_refusal_names_its_cause_not_only_its_effect() -> None:
    """A refused fact must not hide behind the absence it creates.

    Refusals are deduplicated by dependency against the entries
    ``_compose_changes`` already made. While both sides of a pair were spelled
    with one bare ``FACT_KEY_*``, the refusal's dependency (the metric) equalled
    the composer's (the fact key), so the composer's
    ``no_compatible_pair_for_comparison_basis`` landed first and the admission
    reason was dropped -- the document reported that there was no pair to find
    when in truth there was one and this module declined to read half of it.
    Distinct pair keys are what keep the cause visible, so this test is a
    falsifier for the key reconciliation as much as for the refusal itself.
    """
    # Exactly ONE side is refused. Refusing both removes the metric from
    # _compose_changes entirely, so no competing entry is ever made and the
    # test cannot fail -- which is how the first version of this test passed
    # against a mutant that deleted the behaviour it claimed to pin.
    case = _plnt_case()
    current = next(
        f
        for f in case["facts"]
        if f["metric"] == FACT_KEY_ADVERTISING_EXPENSE and f["period_end"] == "2026-06-30"
    )
    current["value_text"] = "365,223"
    document = project_economic_change(case)
    reasons = {
        d["dependency"]: d["reason"] for d in document["degraded_dependencies"]
    }
    # The METRIC names the cause...
    assert reasons.get(FACT_KEY_ADVERTISING_EXPENSE) == "fact_value_text_unparseable", reasons
    # ...and the effect it caused must not be reported in its place anywhere.
    assert "no_compatible_pair_for_comparison_basis" not in reasons.values(), reasons


def test_every_native_ref_resolves_to_a_declared_source_record() -> None:
    """Provenance must point at something that exists.

    ``native_ref`` and ``source_records[].record_id`` are spelled in two
    places, and the contract validates each in isolation -- both patterns pass
    happily while the pointer dangles. The helper shipped six facts pointing at
    ``src-plntq2-2026-<metric>-<side>`` and six one-key stubs, so every pointer
    resolved only because nothing ever tried to follow one.
    """
    case = _plnt_case()
    declared = {r["record_id"] for r in case["source_records"]}
    assert declared, "the case declares no source records at all"
    for fact in case["facts"]:
        ref = fact.get("native_ref")
        assert ref in declared, (fact["key"], ref, sorted(declared))

    # ...and the MODULE must enforce it, not merely the fixture satisfy it.
    # This assertion is the one that was missing: the test above states a
    # property of ``_plnt_case()``, which a caller handing over any other
    # case is in no way bound by. Measured before the guard existed: the
    # orphan below was emitted inside a document reporting
    # ``availability: "ready"`` at zero schema errors.
    orphan = "src_this_record_was_never_declared"
    assert orphan not in declared, "probe value must not be declared"
    dangling = _plnt_case()
    assert dangling["facts"][0]["native_ref"] != orphan, "MUTATION WAS A NO-OP"
    dangling["facts"][0] = dict(dangling["facts"][0], native_ref=orphan)
    with pytest.raises(CaseShapeError) as exc:
        project_economic_change(dangling)
    # The DECLARED REASON must name the gate under test, not merely refuse:
    # DSC:A-MUTATION-THAT-DIES-UPSTREAM-NEVER-TESTS-THE-GATE-YOU-AIMED-AT.
    assert "resolves to no declared source record" in str(exc.value), exc.value
    assert orphan in str(exc.value), exc.value


def test_a_null_native_ref_is_still_admitted() -> None:
    """Absence is honest; the guard must not over-tighten into it.

    DSC:A-MINTING-DEFAULT-IS-INVISIBLE-TO-AN-EMPTINESS-GATE so_what (4)
    rules that ``null`` for ``native_ref`` is the contract's own "unknown"
    and refusing it would reject otherwise-complete facts to gain nothing.
    The committed fixture carries six null refs, so this is the live
    negative control on the resolution guard: it must stay green.
    """
    case = _fixture_case()
    assert all(f.get("native_ref") is None for f in case["facts"]), [
        f.get("native_ref") for f in case["facts"]
    ]
    document = project_economic_change(case)
    assert document["availability"] == "ready", document["availability"]


def test_native_ref_outside_the_record_id_vocabulary_is_refused() -> None:
    """Both ends of one pointer must share one vocabulary.

    ``source_record.record_id`` is pinned to ``^src_[a-z0-9_]+$`` while
    ``fact.native_ref`` carried no pattern at all, so the two ends of the
    SAME pointer were typed differently. Measured before the repair:
    ``"SRC-NOT-LEGAL"`` -- uppercase, hyphenated, matching no record_id that
    could ever be declared -- was accepted and emitted. That absence of a
    vocabulary gate is why the positive control in the dangling-pointer
    probe did not fire, and it is the structural cause of the dangle.
    """
    case = _plnt_case()
    assert case["facts"][0]["native_ref"] != "SRC-NOT-LEGAL", "MUTATION WAS A NO-OP"
    case["facts"][0] = dict(case["facts"][0], native_ref="SRC-NOT-LEGAL")
    with pytest.raises(CaseShapeError):
        project_economic_change(case)


def test_native_admitted_false_is_not_a_suppression_gate() -> None:
    """The label must never become a gate -- pinning frozen-spec 4a.

    Every real V1-CORE fact carries ``native_admitted: False`` because
    PLNT's Q2 2026 exhibit is retained nowhere, so a gate here would make
    the module structurally incapable of its own golden case. The
    ``_compose_changes`` docstring asserted exactly that suppression --
    citing section 7, while the code 20 lines below refused it citing 4a --
    so a reader who trusted the prose would have "restored" a gate that
    breaks the frozen oracle. This test makes the prose falsifiable.
    """
    case = _plnt_case()
    assert all(f.get("native_admitted") is False for f in case["facts"])
    document = project_economic_change(case)
    assert document["availability"] == "ready", document["availability"]
    assert document["results"], "native_admitted False suppressed every result"


# Every contract-required envelope field the source must SPELL. Dropping any
# one of these from a fact used to produce a document this module declared
# ``ready`` -- eight of them violating the very contract it authors, and three
# of them VALIDATING while lying.
_MINTABLE_ENVELOPE_FIELDS = (
    "basis",
    "definition",
    "display_quantum",
    "event",
    "evidence",
    "key",
    "kind",
    "metric",
    "perimeter",
    "role",
    "scale_power10",
    "sign_convention",
    "unit",
)


@_pytest.mark.parametrize("field", _MINTABLE_ENVELOPE_FIELDS)
def test_no_required_envelope_field_is_ever_minted(field: str) -> None:
    """A fact missing a required envelope field is withheld, never guessed at.

    The admission gate originally guarded only the four fields whose
    ``_envelope_*`` reader answers absence with an EMPTY sentinel
    (``value_text``, ``period_start``, ``period_end``, ``period_kind``). Every
    other required field had a reader that answered with a plausible-looking
    value instead -- ``kind`` -> ``"financial"`` (not even in its own enum),
    ``unit`` -> ``"USD"``, ``sign_convention`` -> ``"signed_as_reported"``,
    ``scale_power10`` -> ``0``, the rest -> ``""``/``None``. No emptiness check
    could catch a non-empty fabrication, and nothing in the suite executed
    those lines, so the fabrications shipped.

    Measured on the merged tree before this gate: ``basis``, ``definition``,
    ``display_quantum``, ``evidence``, ``key``, ``kind``, ``perimeter`` and
    ``role`` each produced a ``ready`` document carrying schema violations
    with ``degraded_dependencies == []``; ``event`` killed the whole case with
    ``CaseShapeError``.
    """
    case = _plnt_case()
    admitted = len(case["facts"]) - 1
    del case["facts"][0][field]
    document = project_economic_change(case)

    assert list(_validator().iter_errors(document)) == [], (
        f"dropping {field!r} published a document that violates the contract"
    )
    assert document["degraded_dependencies"], (
        f"dropping {field!r} was absorbed silently -- nothing was declared"
    )
    # The load-bearing assertion. Without it this test passes for
    # ``scale_power10`` on the unfixed engine: dropping it from ONE side of a
    # pair already degraded that pair for a DIFFERENT reason (mismatched
    # scale), which satisfied both checks above while the fabricated ``0``
    # sailed into the document. Counting is what proves the fact was refused
    # rather than published -- and it works for ``key`` too, where the victim
    # cannot be identified by the field that is missing.
    assert len(document["facts"]) == admitted, (
        f"dropping {field!r} left {len(document['facts'])} facts published, "
        f"expected {admitted} -- the unpublishable fact was not withheld"
    )


def test_the_three_silent_fabrications_are_refused_not_published() -> None:
    """``unit``/``sign_convention``/``scale_power10`` are the dangerous ones.

    Their minted defaults are all SCHEMA-VALID, so unlike ``kind`` they raise
    no violation -- the document validates cleanly while misstating what the
    numbers mean. A EUR issuer would be published as USD; a sign convention
    would be assumed rather than read; figures in thousands would be published
    as units. Nothing downstream could detect any of the three.
    """
    for field, fabrication in (
        ("unit", "USD"),
        ("sign_convention", "signed_as_reported"),
        ("scale_power10", 0),
    ):
        case = _plnt_case()
        victim_key = case["facts"][0]["key"]
        del case["facts"][0][field]
        document = project_economic_change(case)

        # The fact must not appear at all -- not with the source's value, and
        # above all not with the fabricated one.
        published = [f for f in document["facts"] if f["key"] == victim_key]
        assert published == [], (
            f"{field!r} was missing at source yet the fact was published as "
            f"{[f.get(field) for f in published]!r} (fabrication: {fabrication!r})"
        )
        reasons = {d["reason"] for d in document["degraded_dependencies"]}
        assert f"fact_{field}_missing_or_malformed" in reasons, reasons


@_pytest.mark.parametrize(
    "field",
    tuple(f for f in _MINTABLE_ENVELOPE_FIELDS if f not in ("evidence", "scale_power10")),
)
def test_a_present_but_empty_envelope_field_is_refused_too(field: str) -> None:
    """``missing_or_malformed`` has to mean both words.

    Deleting a field yields ``None``, which fails an ``isinstance(str)`` test
    on its own -- so a gate that checked ONLY the type would pass every
    absence test while still admitting ``basis: ""``. That matters precisely
    here: ``""`` is the exact value the old ``_envelope_*`` readers handed
    back, so an upstream that learned to spell the key without filling it in
    would walk straight through. Mutation control: dropping the emptiness
    half of the check survives the absence tests and is killed only by this
    one.
    """
    case = _plnt_case()
    admitted = len(case["facts"]) - 1
    case["facts"][0][field] = ""
    document = project_economic_change(case)

    assert list(_validator().iter_errors(document)) == [], field
    assert len(document["facts"]) == admitted, (
        f"an empty {field!r} was published rather than refused"
    )


def test_a_kind_outside_the_contract_enum_is_refused_by_value() -> None:
    """The original defect was a VALUE, not an absence.

    ``_envelope_kind`` minted ``"financial"`` -- a string the contract's own
    ``kind`` enum (``revenue_line``/``expense_line``) does not contain. A gate
    that merely required ``kind`` to be a non-empty string would admit it
    again, and every absence test would still pass. Only checking membership
    catches it, so this test pins the enum and not just the presence.
    """
    case = _plnt_case()
    admitted = len(case["facts"]) - 1
    case["facts"][0]["kind"] = "financial"
    document = project_economic_change(case)

    assert list(_validator().iter_errors(document)) == []
    assert len(document["facts"]) == admitted, (
        "'financial' was admitted -- the gate checks presence, not vocabulary"
    )
    reasons = {d["reason"] for d in document["degraded_dependencies"]}
    assert "fact_kind_outside_vocabulary" in reasons, reasons


# --- CC-V1 wave 6: a label the module STATES is not a property it CHECKS ------
#
# ``_select_pair`` takes ``comparison_basis`` as a parameter and never reads it
# (AST-verified).  The case declares ``explicit_same_quarter_prior_year``; the
# selector pairs on five equalities plus ``older.period_end < newest.period_end``
# and the basis is then stamped on by result key.  So the document asserts a
# same-quarter-prior-year comparison that the periods it carries contradict, at
# ``availability: ready``, ``degraded_dependencies: []`` and zero schema errors.
#
# Each test below asserts the PROPERTY, never the mechanism: a result may be
# withheld, or may carry an envelope that agrees with itself -- what it may not
# do is publish a claim its own data refutes.


_PRIOR_SUFFIX = "_prior"


def _mutate_prior_side(case: dict[str, Any], **fields: Any) -> int:
    """Apply ``fields`` to every prior-period fact.  Returns how many were hit.

    Mutating BOTH sides collapses the pair and nothing is ever declared, which
    is the vacuity trap ``test_a_refusal_names_its_cause_not_only_its_effect``
    already fell into once (see the 2026-09-27 handoff).  One side only.
    """
    touched = 0
    for fact in case["facts"]:
        if str(fact.get("key", "")).endswith(_PRIOR_SUFFIX):
            fact.update(fields)
            touched += 1
    assert touched, "no prior-side fact found -- the key convention moved"
    return touched


def _ready_results(document: dict[str, Any]) -> list[dict[str, Any]]:
    return [r for r in document["results"] if not r.get("withheld_reason")]


@_pytest.mark.parametrize(
    "label,fields",
    (
        # Coherent quarter, seven years off.  The gap is the property the basis
        # names, and nothing checked it.
        ("prior side is Q1 2019", {"period_start": "2019-01-01", "period_end": "2019-03-31"}),
        # End before its own start.  Both dates are individually valid, so the
        # contract's $defs/date cannot see it -- same shape as the native_ref
        # landmine: two fields validated in isolation.
        ("prior period is inverted", {"period_start": "2025-06-30", "period_end": "2025-04-01"}),
        # Thirty days, still labelled a quarter.
        ("prior 'quarter' spans 30 days", {"period_start": "2025-06-01", "period_end": "2025-06-30"}),
    ),
)
def test_a_pair_that_cannot_be_the_declared_basis_is_not_a_compatible_pair(
    label: str, fields: dict[str, Any]
) -> None:
    case = _plnt_case()
    assert case["comparison_basis"] == "explicit_same_quarter_prior_year"
    _mutate_prior_side(case, **fields)
    document = project_economic_change(case)

    claimed = [r for r in _ready_results(document)
               if r["basis"] == "same_quarter_prior_year_change"]
    assert claimed == [], (
        f"{label}: {len(claimed)} result(s) still claim "
        f"same_quarter_prior_year_change -- keys "
        f"{[r['key'] for r in claimed]}"
    )
    reasons = {d["reason"] for d in document["degraded_dependencies"]}
    assert "no_compatible_pair_for_comparison_basis" in reasons, (
        f"{label}: the pair was refused nowhere; reasons={sorted(reasons)}"
    )


def test_the_declared_basis_survives_the_case_it_was_written_for() -> None:
    """The bands must admit both real cases, or they are the wrong bands.

    90-day quarters, a 365-day gap.  A retail 4-5-4 quarter is 13 or 14 weeks
    and is never calendar-snapped (see the period_start landmine), so the check
    is a generous band, not an equality.
    """
    for name, case in (("synthetic", _plnt_case()), ("fixture", _fixture_case())):
        document = project_economic_change(case)
        assert document["availability"] == "ready", name
        assert document["degraded_dependencies"] == [], name
        assert len(_ready_results(document)) == 6, name


def test_a_result_never_states_a_quantum_its_own_facts_contradict() -> None:
    """``display_quantum`` is a constant selected by result key, not derived."""
    case = _plnt_case()
    for fact in case["facts"]:
        fact["display_quantum"] = "5_thousand"
    document = project_economic_change(case)
    published = {f["display_quantum"] for f in document["facts"]}
    offenders = [
        r for r in _ready_results(document)
        if r["unit"] != "percent" and r["display_quantum"] not in published
    ]
    assert offenders == [], (
        f"facts published {sorted(published)} but results state "
        f"{sorted({r['display_quantum'] for r in offenders})}"
    )


def test_a_result_never_states_a_unit_its_own_envelope_contradicts() -> None:
    """The definition sentence hardcodes 'in USD thousands'.

    Planting EUR at 10**6 leaves the envelope correct (unit and scale ARE
    derived) and the prose wrong, and the contract cannot see it because both
    halves are legal in isolation.
    """
    case = _plnt_case()
    for fact in case["facts"]:
        fact["unit"] = "EUR"
        fact["scale_power10"] = 6
    document = project_economic_change(case)
    offenders = [
        r for r in _ready_results(document)
        if r["unit"] == "EUR" and "USD" in r["definition"]
    ]
    assert offenders == [], (
        f"{len(offenders)} EUR result(s) describe themselves in USD: "
        f"{[r['key'] for r in offenders]}"
    )


def test_a_period_labelled_another_kind_cannot_serve_the_declared_basis() -> None:
    """The envelope's own word has to agree with the basis, not just its length.

    A fact that calls itself a ``year`` while spanning ninety days satisfies
    every arithmetic band a quarter basis imposes, so the span checks pass it
    and only the kind binding refuses it. Without that binding the document
    publishes a same-quarter-prior-year change over a period its own envelope
    calls something else -- the wave-6 defect in miniature, and the one arm a
    mutation round found unpinned.
    """
    case = _plnt_case()
    assert case["comparison_basis"] == "explicit_same_quarter_prior_year"
    # BOTH sides: ``_select_pair`` already requires the pair to agree on
    # ``period_kind``, so relabelling one side alone collapses the pair for a
    # reason that has nothing to do with the declared basis -- a vacuous test
    # that a mutation round caught surviving.
    for fact in case["facts"]:
        fact["period_kind"] = "year"

    document = project_economic_change(case)

    claimed = [r for r in _ready_results(document)
               if r["basis"] == "same_quarter_prior_year_change"]
    assert claimed == [], (
        "published a same-quarter comparison against periods their own "
        f"envelopes label years -- keys {[r['key'] for r in claimed]}"
    )
    reasons = {d["reason"] for d in document["degraded_dependencies"]}
    assert "no_compatible_pair_for_comparison_basis" in reasons, (
        f"the pair was refused nowhere; reasons={sorted(reasons)}"
    )


def test_provenance_names_the_current_side_first() -> None:
    """Deduping ``input_refs`` must not reorder them.

    ``_emit_result`` collapses a repeated source key, and the cheapest way to
    do that -- ``set`` -- silently randomises provenance order. The current
    side reads first, and that is a property, not a comment.
    """
    document = project_economic_change(_plnt_case())
    by_key = {result["key"]: result for result in document["results"]}
    assert by_key["total_revenue_change"]["input_refs"] == [
        "total_revenue_current",
        "total_revenue_prior",
    ]


def test_no_period_band_can_admit_an_incoherent_period() -> None:
    """Why the ``start < end`` check cannot be reached today -- pinned.

    Every span band has a positive lower bound, so a period ending before it
    starts yields a negative span and fails the band regardless. A mutation
    round found the explicit coherence check unkillable for exactly that
    reason; it stays as fail-closed defence, and this test keeps the property
    that makes it redundant from being quietly edited away.
    """
    from engine.sector_intelligence import consumer_cyclical_projection as mod

    for kind, (low, high) in mod._PERIOD_KIND_SPAN_DAYS.items():
        assert low > 0, f"{kind} band admits a zero-or-negative span"
        assert low < high, f"{kind} band is empty"
    assert mod._PRIOR_YEAR_GAP_DAYS[0] > 0
    assert mod._PRIOR_YEAR_GAP_DAYS[0] < mod._PRIOR_YEAR_GAP_DAYS[1]


# ---------------------------------------------------------------------------
# Wave 8 -- the authority guard's vocabulary, and which gate is load-bearing
# ---------------------------------------------------------------------------


def test_the_authority_guard_refuses_implementation_vocabulary() -> None:
    """A blocklist written from the rule's prose blocks the rule's own words.

    Measured 2026-09-27 on the pre-repair module: the eight-name list caught
    4 of 30 category-representative keys. ``sizing`` -- the policy's noun --
    was refused, while ``position_size``, ``weight``, ``allocation``,
    ``notional`` and ``exposure`` -- what a violating field would actually be
    called -- all passed. Frozen-spec section 6 rule 10 names CATEGORIES, so
    the guard must carry the categories' vocabulary, not their labels.
    """
    for key in (
        "position_size",
        "weight",
        "allocation",
        "notional",
        "exposure",
        "recommendation",
        "signal",
        "conviction",
        "percentile",
        "entry_price",
        "stop_loss",
    ):
        assert key not in {"sizing", "origination", "gate"}, "MUTATION WAS A NO-OP"
        with pytest.raises(CaseShapeError) as excinfo:
            _assert_no_forbidden_authority_keys({"facts": [{key: 1}]})
        assert "forbidden authority key" in str(excinfo.value), str(excinfo.value)
        assert key in str(excinfo.value), str(excinfo.value)


def test_the_contract_seal_is_what_actually_refuses_an_unlisted_key() -> None:
    """The documented guard is the SECOND line; the schema seal is the first.

    This is the test whose absence let a decorative guard read as the
    enforcement point. ``action`` is deliberately NOT in the blocklist -- it
    is ordinary English with a plausible non-authority reading -- so the
    authority walk passes it. It is still refused, by
    ``additionalProperties: false`` on every composite ``$defs``. If a future
    change ever unseals a definition, this test goes red and names the real
    mechanism instead of letting the blocklist take undeserved credit.
    """
    document = project_economic_change(_plnt_case())
    assert document["facts"], "MUTATION WAS A NO-OP"

    polluted = dict(document)
    polluted["facts"] = [dict(document["facts"][0], action="BUY")] + list(
        document["facts"][1:]
    )

    # The guard passes it -- on purpose, and this assertion pins that.
    _assert_no_forbidden_authority_keys(polluted)

    # The seal refuses it.
    with pytest.raises(CaseShapeError) as excinfo:
        _assert_document_matches_contract_shape(polluted)
    assert "violates" in str(excinfo.value), str(excinfo.value)


def test_widening_the_blocklist_did_not_refuse_ordinary_names() -> None:
    """Negative control: defense in depth must not become spurious refusal.

    ``size`` and ``weight`` are in the bare set (exact match) but kept OUT of
    the compound pattern, because that pattern also judges names that do not
    exist yet and ``sample_size`` / ``batch_size`` are ordinary engineering
    names. This is the live control on that boundary.
    """
    for key in (
        "sample_size",
        "batch_size",
        "display_quantum",
        "accession_no",
        "comparison_basis",
        "acceptance_clock_basis",
    ):
        _assert_no_forbidden_authority_keys({"facts": [{key: 1}]})

    # And the real document still emits unharmed.
    document = project_economic_change(_fixture_case())
    assert document["availability"] == "ready", document["availability"]


def test_the_compound_authority_pattern_actually_catches_compound_keys() -> None:
    """The one construct named for compound keys caught none of them.

    Measured 2026-09-27: the guard called ``_FORBIDDEN_COMPOUND_KEY_RE
    .fullmatch(k)``. A pattern of ``(^|_)(stem)(_|$)`` cannot consume a whole
    compound name -- ``composite_score`` matches ``composite``, then
    ``(_|$)`` takes one underscore and leaves ``score`` unconsumed -- so
    every compound authority key passed. A BARE stem did fullmatch, which is
    why the dead call looked alive: its only hits were names the bare
    frozenset already carried.

    Each key below is asserted absent from ``_FORBIDDEN_BARE_KEYS`` first,
    so a pass here can only mean the PATTERN fired. Without that assertion
    this test would stay green if the pattern were deleted entirely.
    """
    for key in (
        "composite_score",
        "analyst_rank",
        "conviction_score",
        "signal_strength",
        "sizing_weight",
        "market_entry",
    ):
        assert key.lower() not in _FORBIDDEN_BARE_KEYS, (
            f"{key} is in the bare set; this test would not prove the pattern fired"
        )
        with pytest.raises(CaseShapeError) as excinfo:
            _assert_no_forbidden_authority_keys({"facts": [{key: 1}]})
        assert key in str(excinfo.value), str(excinfo.value)


def test_a_degraded_entry_only_ever_reports_the_unavailable_state() -> None:
    """``state`` is a constant; the granularity lives entirely in ``reason``.

    The contract admits three values for ``degraded_dependency.state``
    (``available``/``partial``/``unavailable``) but ``_degraded`` carries
    ``state: str = "unavailable"`` and all seven call sites omit the
    argument, so ``unavailable`` is the only value a consumer can ever see --
    and ``available``, on an entry inside a list *of degraded dependencies*,
    would contradict the list it sits in. That gap is LOOSE, not false: the
    document never claims anything untrue, it is the contract that permits
    more than the producer emits. Pinned so the looseness is measured rather
    than assumed, and so a change that starts emitting a second state
    surfaces as a consumer-facing decision instead of silently widening what
    downstream code has to handle.

    Two independent degradation branches are driven -- a metric left with
    only one side of its pair, and an unparseable ``value_text`` on a metric
    whose pair is intact. Each mutation asserts that it changed the case,
    and the distinct-``reason`` assertion is what stops the state assertion
    passing for free on an empty list: a filter written against the bare
    metric name rather than the ``_current``/``_prior`` fact key silently
    mutates nothing, and every assertion below it then holds vacuously.
    """
    entries: list[dict[str, Any]] = []

    # Branch 1: one side of a pair removed -- nothing left to compare against.
    case = _fixture_case()
    before = len(case["facts"])
    case["facts"] = [f for f in case["facts"] if f["key"] != "advertising_expense_prior"]
    assert len(case["facts"]) == before - 1, (
        "fixture no longer carries 'advertising_expense_prior'; this branch "
        "mutated nothing and proves nothing"
    )
    entries += project_economic_change(case)["degraded_dependencies"]

    # Branch 2: both sides present, one of them unreadable.
    case = _fixture_case()
    case["facts"] = [
        dict(f, value_text="not-a-number") if f["key"] == "total_revenue_current" else f
        for f in case["facts"]
    ]
    assert any(f["value_text"] == "not-a-number" for f in case["facts"]), (
        "fixture no longer carries 'total_revenue_current'; this branch "
        "mutated nothing and proves nothing"
    )
    entries += project_economic_change(case)["degraded_dependencies"]

    reasons = {e["reason"] for e in entries}
    assert len(reasons) > 1, (
        f"both mutations were no-ops -- {len(entries)} entries, reasons "
        f"{reasons!r}; the state assertion below would pass vacuously"
    )

    states = {e["state"] for e in entries}
    assert states == {"unavailable"}, (
        f"degraded entries reported {sorted(states)!r} across reasons "
        f"{sorted(reasons)!r}; only 'unavailable' is produced today, so a new "
        "state is a contract-visible change that needs a consumer decision"
    )


# ---------------------------------------------------------------------------
# Result-envelope contradiction vs the stated definition
# ---------------------------------------------------------------------------
#
# ``_emit_result`` withholds the USD-thousands family when the result's own
# envelope contradicts the definition the module states for it: unit is not
# "USD", scale_power10 is not 3, or the current-period source quantum is not
# "1_thousand". These cases drive that trigger through the real projection
# and pin the real withheld_reason code; the display suite used to stand in
# for it with a hand-set literal the projection never emits.


@pytest.mark.parametrize(
    ("field", "value", "expect_withheld"),
    [
        ("unit", "EUR", True),
        ("scale_power10", 6, True),
        ("display_quantum", "10_thousand", True),
        # Control: the envelope matches the stated definition (the synthetic
        # factory's own defaults -- USD, scale 3, 1_thousand), so nothing is
        # withheld for this reason.
        ("unit", "USD", False),
    ],
    ids=[
        "unit_not_USD",
        "scale_not_3",
        "source_quantum_not_1_thousand",
        "control_envelope_matches",
    ],
)
def test_result_envelope_contradiction_withholds_advertising_net_change(
    field: str, value: Any, expect_withheld: bool
) -> None:
    """Each contradiction trigger withholds the advertising net change.

    Built from the file's existing helpers: ``_plnt_facts`` supplies the
    six-fact synthetic case, ``_plnt_case`` wraps it with subject and source
    records, and ``_result_by_key`` reads the emitted row. The mutation lands
    on BOTH advertising_revenue facts so the pair rule (the two facts must
    share unit, scale_power10 and sign_convention) still forms the pair: the
    contradiction is a claim conflict with the stated definition, not a
    pairing failure.
    """
    facts = [dict(fact) for fact in _plnt_facts()]
    mutated = 0
    for fact in facts:
        if fact["metric"] == "advertising_revenue":
            fact[field] = value
            mutated += 1
    assert mutated == 2, (
        "the synthetic factory no longer carries an advertising_revenue "
        f"pair -- mutated {mutated} facts, this case proves nothing"
    )

    document = project_economic_change(_plnt_case(facts=facts))
    row = _result_by_key(document, RESULT_KEY_ADVERTISING_NET_CHANGE)

    if expect_withheld:
        assert row["value_text"] is None, row
        assert (
            row["withheld_reason"] == _WITHHELD_REASON
        ), row
    else:
        assert (
            row["withheld_reason"] != _WITHHELD_REASON
        ), row
        assert row["value_text"] == "-4", row


# ---------------------------------------------------------------------------
# Stated-definition screen vs the verdicts (W15-F: PR #9285 review D1/D2)
# ---------------------------------------------------------------------------
#
# The stated-definition check used to run ONLY inside ``_emit_result`` -- after
# every derived row had been built, after the ``availability`` verdict and
# after the explanation lead had been selected from the internal
# ``state == "READY"`` set. A contradicting fact therefore withheld its row
# from the emitted document while the document still read ``availability:
# ready`` with the full economic lead naming the withheld row, and the rows
# derived from it kept publishing values computed from withheld input.


_WITHHELD_REASON = _DEFINITION_CONTRADICTED


def _contradict(
    facts: list[dict[str, Any]],
    fact_key: str,
    field: str,
    value: Any,
) -> None:
    """Mutate one envelope field of exactly one fact, proving the target exists."""
    hit = [fact for fact in facts if fact["key"] == fact_key]
    assert len(hit) == 1, (
        f"the synthetic factory no longer carries exactly one "
        f"{fact_key!r} fact -- this case proves nothing"
    )
    hit[0][field] = value


def test_d1_expense_current_quantum_contradiction_withholds_net_row_too() -> None:
    """Withholding advertising_expense_change must withhold its derived net row.

    Built from the file's existing helpers: ``_plnt_facts`` supplies the
    six-fact case, ``_plnt_case`` wraps it with subject and source records,
    ``_result_by_key`` reads the emitted row. Only the advertising-EXPENSE
    CURRENT fact's ``display_quantum`` contradicts the stated definition.
    """
    facts = [dict(fact) for fact in _plnt_facts()]
    _contradict(
        facts,
        FACT_KEY_ADVERTISING_EXPENSE + "_current",
        "display_quantum",
        "5_thousand",
    )
    document = project_economic_change(_plnt_case(facts=facts))

    expense = _result_by_key(document, RESULT_KEY_ADVERTISING_EXPENSE_CHANGE)
    assert expense["value_text"] is None, expense
    assert expense["withheld_reason"] == _WITHHELD_REASON, expense

    net = _result_by_key(document, RESULT_KEY_ADVERTISING_NET_CHANGE)
    assert net["value_text"] is None, net
    # The honest reason for THIS case: advertising_net_change's own
    # prior_period_fact IS the contradicting advertising-expense current
    # fact envelope (the net derivation takes the expense row's current
    # envelope as the net row's prior side), so the
    # net row itself fails the stated-definition screen with the
    # contradiction reason rather than the generic dependency_suppressed.
    assert net["withheld_reason"] == _WITHHELD_REASON, net

    # The clean-environment rows still publish their golden values.
    assert (
        _result_by_key(document, RESULT_KEY_TOTAL_REVENUE_CHANGE)["value_text"]
        == "24344"
    )
    assert (
        _result_by_key(document, RESULT_KEY_ADVERTISING_REVENUE_CHANGE)[
            "value_text"
        ]
        == "10141"
    )


def test_d2_revenue_prior_quantum_contradiction_withholds_change_and_net() -> None:
    """The screen must read BOTH envelope sides, not only current_period_fact.

    The old trigger inspected only the current side, so contradicting the
    advertising-revenue PRIOR fact left every row publishing -- including
    advertising_revenue_change itself, whose stated definition claims USD
    thousands over a fact envelope the prior side refutes.
    """
    facts = [dict(fact) for fact in _plnt_facts()]
    _contradict(
        facts,
        FACT_KEY_ADVERTISING_REVENUE + "_prior",
        "display_quantum",
        "5_thousand",
    )
    document = project_economic_change(_plnt_case(facts=facts))

    revenue = _result_by_key(document, RESULT_KEY_ADVERTISING_REVENUE_CHANGE)
    assert revenue["value_text"] is None, revenue
    assert revenue["withheld_reason"] == _WITHHELD_REASON, revenue

    net = _result_by_key(document, RESULT_KEY_ADVERTISING_NET_CHANGE)
    assert net["value_text"] is None, net
    # The net row's own envelopes are clean in THIS case; it fails because
    # its advertising_revenue_change constituent was just withheld. The
    # existing vocabulary for exactly that is the build branch's own
    # "dependency_suppressed", which the build branch of the net
    # derivation uses when a constituent row is not READY.
    assert net["withheld_reason"] == "dependency_suppressed", net


def test_screen_defensive_own_display_quantum_contradiction_withholds() -> None:
    """White-box: a row that carries its own contradicting display_quantum.

    No internal row reaches ``_screen_stated_definition`` with a
    ``display_quantum`` today -- the field is minted later, at emit time,
    by the ``setdefault`` in ``_result_provenance``. Measured with a
    capture driver wrapping the screen across the four owning suites
    (W15-F-FUR, seed 479e2c69): 609 rows enter the screen in total, 608
    of them reached from inside ``project_economic_change``, and 0 of
    those 608 carry ``display_quantum``. The single row that does carry
    it (value ``'5_thousand'``) is fed by THIS test's own direct call
    below -- the 608/0 count is therefore the scoped claim for rows
    produced inside the projection, not for the whole screen corpus.
    Either way the defensive clause is behaviour-neutral for every
    reachable internal input. This test feeds the screen the
    reachable-tomorrow input the clause exists for: BOTH envelopes clean
    (USD, 10**3, ``1_thousand``) while the row's own ``display_quantum``
    states ``5_thousand``. An envelope with that quantum contradicts the
    stated definition; so must the row itself.
    """
    row = {
        "key": RESULT_KEY_TOTAL_REVENUE_CHANGE,
        "state": "READY",
        "value_text": "24344",
        "value_decimal": Decimal("24344"),
        "unit": "USD",
        "scale_power10": 3,
        "withheld_reason": None,
        "current_period_fact": {
            "unit": "USD",
            "scale_power10": 3,
            "display_quantum": "1_thousand",
        },
        "prior_period_fact": {
            "unit": "USD",
            "scale_power10": 3,
            "display_quantum": "1_thousand",
        },
        "display_quantum": "5_thousand",
    }
    _screen_stated_definition([row])
    assert row["value_text"] is None, row
    assert row["withheld_reason"] == _WITHHELD_REASON, row
    assert row["state"] == "WITHHELD", row


def test_predicate_exempts_pct_row_on_direct_call() -> None:
    """W15-F-FUR item 3: the ``_pct`` exemption must live in the predicate.

    On the seed the exemption lived ONLY in ``_screen_stated_definition``'s
    ``key.endswith("_pct")`` skip, so a direct call on
    ``_stated_definition_contradicted`` with a ratio row carrying its own
    minted ``"0.01_percent"`` quantum -- the value ``_emit_result`` stamps
    for every ``_pct`` key at emit time -- contradicted on the defensive
    row-level clause. The predicate must be self-sufficient: a ``_pct``
    key returns False regardless of the row-level quantum, because the
    ratio describes itself as a percentage and says nothing about a
    currency, exactly as the screen reasons (#9318 review nit 3). The
    screen's skip is kept untouched; this only makes a direct caller of
    the predicate agree with the screen.
    """
    row = {
        "key": RESULT_KEY_ADVERTISING_SHARE_OF_REVENUE_CHANGE_PCT,
        "state": "READY",
        "value_text": "62.35",
        "value_decimal": Decimal("0.6235"),
        "unit": "USD",
        "scale_power10": 3,
        "withheld_reason": None,
        "current_period_fact": {
            "unit": "USD",
            "scale_power10": 3,
            "display_quantum": "1_thousand",
        },
        "prior_period_fact": {
            "unit": "USD",
            "scale_power10": 3,
            "display_quantum": "1_thousand",
        },
        "display_quantum": "0.01_percent",
    }
    assert _stated_definition_contradicted(row) is False, row


def test_emit_result_backstop_withholds_row_level_quantum_contradiction() -> None:
    """W15-F-FUR item 4: mirror the row-level clause into ``_emit_result``.

    The ``_emit_result`` BACKSTOP re-checked ``unit``, ``scale_power10``
    and the CURRENT-side envelope quantum, but not the row-level
    ``display_quantum`` clause that ``_stated_definition_contradicted``
    carries (#9318). So a pre-stamped contradicting row pushed through
    ``_emit_result`` ALONE published its value on the seed. It must
    withhold, for the same reason literal, with ``_pct`` exempted exactly
    as the screen exempts it (the guard's ``not key.endswith("_pct")``).
    Behaviour-neutral for every reachable input: for internal rows the
    ``setdefault`` in ``_result_provenance`` has just minted the key's
    canonical ``1_thousand`` a few lines above, so the new comparison
    no-ops; only a row that ARRIVES pre-stamped with a contradicting
    quantum trips it -- and the capture driver over the four owning
    suites counted 0 projection rows carrying ``display_quantum`` at the
    screen, hence 0 pre-stamped rows reaching this path today.
    """
    row = {
        "key": RESULT_KEY_TOTAL_REVENUE_CHANGE,
        "state": "READY",
        "value_text": "24344",
        "value_decimal": Decimal("24344"),
        "unit": "USD",
        "scale_power10": 3,
        "withheld_reason": None,
        "current_period_fact": {
            "unit": "USD",
            "scale_power10": 3,
            "display_quantum": "1_thousand",
        },
        "prior_period_fact": {
            "unit": "USD",
            "scale_power10": 3,
            "display_quantum": "1_thousand",
        },
        "display_quantum": "5_thousand",
    }
    emitted = _emit_result(row)
    assert emitted["value_text"] is None, emitted
    assert emitted["withheld_reason"] == _WITHHELD_REASON, emitted


def test_emit_result_backstop_withholds_prior_side_contradiction() -> None:
    """W15-F-FUY item 1: the backstop must read BOTH envelope sides.

    #9331 mirrored only the ROW-level clause into the ``_emit_result``
    BACKSTOP; the envelope trigger still read just the CURRENT side's
    quantum, while ``_stated_definition_contradicted`` checks both sides.
    The review PROVED a row with a clean current envelope and an EUR /
    ``scale_power10`` 6 / ``1_million`` PRIOR envelope makes the predicate
    return True, yet ``_emit_result`` alone published value_text='24344'
    with withheld_reason=None. It must now withhold with the same reason
    literal (bound to the engine's ``_DEFINITION_CONTRADICTED`` via
    ``_WITHHELD_REASON`` below). Behaviour-neutral THROUGH
    ``project_economic_change``: the screen runs the predicate first and
    stamps ``withheld_reason``, and the emit guard
    ``not filled.get("withheld_reason")`` keeps existing reasons, so no
    pipeline row reaches this clause un-withheld (proved by the replay
    capture over the four owning suites).
    """
    row = {
        "key": RESULT_KEY_TOTAL_REVENUE_CHANGE,
        "state": "READY",
        "value_text": "24344",
        "value_decimal": Decimal("24344"),
        "unit": "USD",
        "scale_power10": 3,
        "withheld_reason": None,
        "current_period_fact": {
            "unit": "USD",
            "scale_power10": 3,
            "display_quantum": "1_thousand",
        },
        "prior_period_fact": {
            "unit": "EUR",
            "scale_power10": 6,
            "display_quantum": "1_million",
        },
    }
    assert _stated_definition_contradicted(row) is True, row
    emitted = _emit_result(row)
    assert emitted["value_text"] is None, emitted
    assert emitted["withheld_reason"] == _WITHHELD_REASON, emitted


def test_emit_result_backstop_withholds_row_without_current_envelope() -> None:
    """W15-F-G: the backstop must still withhold a row with NO current envelope.

    On ``main`` (HEAD^ of #9343) the trigger read the CURRENT side's
    ``display_quantum`` through ``source.get("display_quantum") if
    isinstance(source, Mapping) else None``, so an absent
    ``current_period_fact`` compared as ``None`` against
    ``_STATED_DEFINITION_QUANTUM`` and the row was withheld. #9343 swapped
    that read for ``_envelope_side_contradicts(...)``, which returns False
    for a non-Mapping side -- the row then published through
    ``_emit_result``. That is a loosening: a backstop must never be looser
    than the one it replaces. This test pins the restored strictness.

    The asymmetry with the predicate is deliberate and pinned here too:
    ``_stated_definition_contradicted`` treats an absent side as
    non-contradicting (it never withheld this row), while the ``_emit_result``
    backstop withholds a row that carries no current envelope at all. An
    absent PRIOR side stays non-contradicting -- HEAD^ never read the prior
    side.
    """
    row = {
        "key": RESULT_KEY_TOTAL_REVENUE_CHANGE,
        "state": "READY",
        "value_text": "24344",
        "value_decimal": Decimal("24344"),
        "unit": "USD",
        "scale_power10": 3,
        "withheld_reason": None,
        "prior_period_fact": {
            "unit": "USD",
            "scale_power10": 3,
            "display_quantum": "1_thousand",
        },
    }
    assert "current_period_fact" not in row
    assert _stated_definition_contradicted(row) is False, row
    emitted = _emit_result(row)
    assert emitted["value_text"] is None, emitted
    assert emitted["withheld_reason"] == _WITHHELD_REASON, emitted


@pytest.mark.parametrize(
    ("present", "prior_value"),
    [
        pytest.param(False, None, id="absent_prior_side"),
        pytest.param(True, "n/a", id="malformed_prior_side_non_mapping"),
    ],
)
def test_emit_result_backstop_publishes_row_with_absent_or_malformed_prior_side(
    present: bool, prior_value: Any
) -> None:
    """W15-F-FWA item 1: pin the ABSENT-PRIOR-SIDE half of the backstop asymmetry.

    The ``_emit_result`` comment block and the ``_envelope_side_contradicts``
    docstring both state that an absent PRIOR side stays non-contradicting --
    the backstop is deliberately stricter on the CURRENT side only, because
    ``main`` never read the prior side and withholding for its absence would be
    a new tightening beyond the restored #9343 baseline. The neighbouring
    ``test_emit_result_backstop_withholds_row_without_current_envelope`` pinned
    the CURRENT half of that asymmetry; NOTHING pinned the PRIOR half, so the
    W15-V-9343c review mutant d2 survived:

    - d2 appended ``or not isinstance(filled.get("prior_period_fact"),
      Mapping)`` to the backstop's prior-side read, so a row was withheld just
      because its prior side is missing or malformed. This test FAILS under d2.
    - d3 made the per-side check return True for a non-Mapping side, erasing
      the deliberate difference between the predicate and the backstop's
      CURRENT-side-only strictness. d3 did not survive: the neighbouring test
      already fails under it. This test FAILS under d3 too: it asserts
      ``_stated_definition_contradicted(row) is False``.

    The fixture is the neighbouring test's, mirrored: a CLEAN current envelope
    (unit / scale_power10 / display_quantum all matching the stated definition)
    and a prior side that is either absent entirely (``present=False``) or
    present but non-Mapping (``"n/a"``). Observed at the seed HEAD before this
    test existed -- BOTH cases published ``value_text='24344'`` with
    ``withheld_reason=None`` and the predicate returned False. The malformed
    case is therefore NOT withheld on HEAD, so it is pinned as the same
    invariant here rather than declined.
    """
    row = {
        "key": RESULT_KEY_TOTAL_REVENUE_CHANGE,
        "state": "READY",
        "value_text": "24344",
        "value_decimal": Decimal("24344"),
        "unit": "USD",
        "scale_power10": 3,
        "withheld_reason": None,
        "current_period_fact": {
            "unit": "USD",
            "scale_power10": 3,
            "display_quantum": "1_thousand",
        },
    }
    if present:
        row["prior_period_fact"] = prior_value
        # Fixture echo, mirroring the CURRENT-side backstop test above.
        assert row["prior_period_fact"] == prior_value
    else:
        assert "prior_period_fact" not in row
    assert _stated_definition_contradicted(row) is False, row
    emitted = _emit_result(row)
    assert emitted["value_text"] == "24344", emitted
    assert emitted["withheld_reason"] is None, emitted


def _mutate_clean(facts: list[dict[str, Any]]) -> None:
    """The golden case, untouched."""


def _mutate_expense_current_quantum(facts: list[dict[str, Any]]) -> None:
    _contradict(
        facts,
        FACT_KEY_ADVERTISING_EXPENSE + "_current",
        "display_quantum",
        "5_thousand",
    )


def _mutate_revenue_prior_quantum(facts: list[dict[str, Any]]) -> None:
    _contradict(
        facts,
        FACT_KEY_ADVERTISING_REVENUE + "_prior",
        "display_quantum",
        "5_thousand",
    )


def _mutate_total_revenue_unit(facts: list[dict[str, Any]]) -> None:
    # BOTH sides of the pair, exactly as the existing trigger parametrization
    # does: the pairing rule requires the sides to share unit, so mutating
    # one side alone would collapse the pair for a reason unrelated to the
    # stated definition.
    hit = [f for f in facts if f["metric"] == FACT_KEY_TOTAL_REVENUE]
    assert len(hit) == 2, "no total_revenue pair to contradict"
    for fact in hit:
        fact["unit"] = "EUR"


def _mutate_total_revenue_scale(facts: list[dict[str, Any]]) -> None:
    hit = [f for f in facts if f["metric"] == FACT_KEY_TOTAL_REVENUE]
    assert len(hit) == 2, "no total_revenue pair to contradict"
    for fact in hit:
        fact["scale_power10"] = 6


#: The PLNT golden case emits exactly this closed set of result keys at
#: EVERY contradiction param: the stated-definition screen blanks values,
#: it never drops a row, and dropping is the ``inputs_present`` emit
#: filter's job -- which none of these mutations touches. Measured on
#: seed 479e2c69: all five params emit the identical six-key set
#: (W15-F-FUR item 2), hence ONE shared constant instead of per-param
#: sets. Pinned so a row silently omitted by that filter fails HERE,
#: instead of passing with a shrunken ``withheld_keys`` derived from
#: ``document["results"]``.
_EXPECTED_EMITTED_KEYS = {
    RESULT_KEY_TOTAL_REVENUE_CHANGE,
    RESULT_KEY_ADVERTISING_REVENUE_CHANGE,
    RESULT_KEY_ADVERTISING_EXPENSE_CHANGE,
    RESULT_KEY_ADVERTISING_NET_CHANGE,
    RESULT_KEY_ADVERTISING_CURRENT_PERIOD_NET,
    RESULT_KEY_ADVERTISING_SHARE_OF_REVENUE_CHANGE_PCT,
}

# Each case pins the EXACT withheld set (result keys whose emitted row
# carries ``value_text`` None), the EXACT emitted key set, and the
# withheld_reason of every withheld row. The sets and reasons were derived
# by running the code on seed 479e2c69 (#9318), the commit that pinned
# them, and reading the output, not guessed. They make this test
# discriminating: the old form only cross-checked availability and the
# lead against the rows, so a screen that silently stopped withholding a
# prior-side contradiction (defect D2) still passed -- the verdicts moved
# with the rows, keeping the agreement intact.
@pytest.mark.parametrize(
    ("mutate", "expected_withheld", "expected_reasons"),
    [
        (
            _mutate_clean,
            set(),
            {},
        ),
        (
            _mutate_expense_current_quantum,
            {
                RESULT_KEY_ADVERTISING_EXPENSE_CHANGE,
                RESULT_KEY_ADVERTISING_CURRENT_PERIOD_NET,
                RESULT_KEY_ADVERTISING_NET_CHANGE,
            },
            {
                RESULT_KEY_ADVERTISING_EXPENSE_CHANGE: _WITHHELD_REASON,
                RESULT_KEY_ADVERTISING_CURRENT_PERIOD_NET: _WITHHELD_REASON,
                # The expense current envelope IS this row's prior side
                # (net derivation), so the net row contradicts directly.
                RESULT_KEY_ADVERTISING_NET_CHANGE: _WITHHELD_REASON,
            },
        ),
        (
            _mutate_revenue_prior_quantum,
            {
                RESULT_KEY_ADVERTISING_REVENUE_CHANGE,
                RESULT_KEY_ADVERTISING_NET_CHANGE,
                RESULT_KEY_ADVERTISING_SHARE_OF_REVENUE_CHANGE_PCT,
            },
            {
                RESULT_KEY_ADVERTISING_REVENUE_CHANGE: _WITHHELD_REASON,
                # The net row's own envelopes stay clean here; it withholds
                # as a dependent of the withheld revenue-change constituent.
                RESULT_KEY_ADVERTISING_NET_CHANGE: "dependency_suppressed",
                # The ratio withholds as a dependent of its withheld numerator.
                RESULT_KEY_ADVERTISING_SHARE_OF_REVENUE_CHANGE_PCT: (
                    "dependency_suppressed"
                ),
            },
        ),
        (
            _mutate_total_revenue_unit,
            {
                RESULT_KEY_TOTAL_REVENUE_CHANGE,
                RESULT_KEY_ADVERTISING_SHARE_OF_REVENUE_CHANGE_PCT,
            },
            {
                RESULT_KEY_TOTAL_REVENUE_CHANGE: _WITHHELD_REASON,
                # The ratio withholds as a dependent of its withheld
                # denominator total_revenue_change.
                RESULT_KEY_ADVERTISING_SHARE_OF_REVENUE_CHANGE_PCT: (
                    "dependency_suppressed"
                ),
            },
        ),
        (
            _mutate_total_revenue_scale,
            {
                RESULT_KEY_TOTAL_REVENUE_CHANGE,
                RESULT_KEY_ADVERTISING_SHARE_OF_REVENUE_CHANGE_PCT,
            },
            {
                RESULT_KEY_TOTAL_REVENUE_CHANGE: _WITHHELD_REASON,
                # The ratio withholds as a dependent of its withheld
                # denominator total_revenue_change.
                RESULT_KEY_ADVERTISING_SHARE_OF_REVENUE_CHANGE_PCT: (
                    "dependency_suppressed"
                ),
            },
        ),
    ],
    ids=[
        "clean_golden",
        "d1_expense_current_quantum",
        "d2_revenue_prior_quantum",
        "total_revenue_unit_eur",
        "total_revenue_scale_6",
    ],
)
def test_availability_lead_and_emitted_rows_agree_under_contradictions(
    mutate,
    expected_withheld,
    expected_reasons,
) -> None:
    """The verdicts and the emitted rows must read from one truth.

    (a) availability is "ready" exactly when at least one emitted result
    actually carries a value; (b) the full economic lead may be claimed only
    when the three change rows it names all publish a value. The lead is
    asserted against the module's own constants, never a hand-copied string.
    (c) the withheld set is pinned exactly, and every withheld row carries
    the expected reason, so a screen that stops doing its job fails even
    when the remaining verdicts stay internally consistent. (d) the
    EMITTED key set is pinned exactly: ``withheld_keys`` is read from
    ``document[\"results\"]``, so without (d) a row silently dropped by
    the ``inputs_present`` emit filter would satisfy ``withheld_keys ==
    expected`` by being absent, not by being withheld.
    """
    facts = [dict(fact) for fact in _plnt_facts()]
    mutate(facts)
    document = project_economic_change(_plnt_case(facts=facts))

    emitted_keys = {r["key"] for r in document["results"]}
    assert emitted_keys == _EXPECTED_EMITTED_KEYS, (
        f"emitted set {sorted(emitted_keys)} != expected "
        f"{sorted(_EXPECTED_EMITTED_KEYS)}"
    )

    withheld_keys = {
        r["key"] for r in document["results"] if r["value_text"] is None
    }
    assert withheld_keys == expected_withheld, (
        f"withheld set {sorted(withheld_keys)} != expected "
        f"{sorted(expected_withheld)}"
    )
    for key, reason in expected_reasons.items():
        row = _result_by_key(document, key)
        assert row["value_text"] is None, row
        assert row["withheld_reason"] == reason, row

    any_published = any(
        r["value_text"] is not None for r in document["results"]
    )
    assert (document["availability"] == "ready") == any_published, (
        f"availability={document['availability']!r} but published rows="
        f"{[r['key'] for r in document['results'] if r['value_text'] is not None]}"
    )

    primary_keys = (
        RESULT_KEY_TOTAL_REVENUE_CHANGE,
        RESULT_KEY_ADVERTISING_REVENUE_CHANGE,
        RESULT_KEY_ADVERTISING_EXPENSE_CHANGE,
    )
    all_primary_publish = all(
        _result_by_key(document, key)["value_text"] is not None
        for key in primary_keys
    )
    lead = document["explanation"]["lead"]
    assert lead in (_LEAD_FULL, _LEAD_GENERIC)
    if lead == _LEAD_FULL:
        assert all_primary_publish, (
            "the full lead names the total, advertising-revenue and "
            "advertising-expense changes, but at least one of them emitted "
            "no value"
        )


#: W15-F-FVA item 3 -- an INDEPENDENT oracle of the derived-row dependency
#: mapping, hand-written from the build function (the net derivation is
#: ``ar_change - ae_change`` of the two advertising change rows, engine
#: near :1712-1715; the ratio's numerator is advertising_revenue_change
#: and its denominator total_revenue_change, engine near :1792-1800).
#: Deliberately NOT read from the engine table it checks below.
_ORACLE_DERIVED_CONSTITUENTS = {
    RESULT_KEY_ADVERTISING_NET_CHANGE: (
        RESULT_KEY_ADVERTISING_REVENUE_CHANGE,
        RESULT_KEY_ADVERTISING_EXPENSE_CHANGE,
    ),
    RESULT_KEY_ADVERTISING_SHARE_OF_REVENUE_CHANGE_PCT: (
        RESULT_KEY_ADVERTISING_REVENUE_CHANGE,
        RESULT_KEY_TOTAL_REVENUE_CHANGE,
    ),
}


def test_no_published_derived_row_has_a_withheld_constituent() -> None:
    """A derived row never publishes a value computed from a withheld row.

    (a) the engine's private ``_DERIVED_ROW_CONSTITUENTS`` equals the
    independent oracle above (read through the same function-local
    ``import ... as mod`` pattern the private-name tests already use);
    (b) the cascade holds over a grid: every single-fact contradiction of
    ``display_quantum`` / ``unit`` / ``scale_power10`` -- the field names
    the ``_mutate_*`` helpers use -- applied to each of the six PLNT
    facts (6 facts x 3 fields = 18 grid points). At each point every
    derived row that publishes a value must have every constituent also
    publishing (or absent from the emitted document entirely).
    """
    from engine.sector_intelligence import consumer_cyclical_projection as mod

    assert mod._DERIVED_ROW_CONSTITUENTS == _ORACLE_DERIVED_CONSTITUENTS

    # Execute the cascade's fixed-point claim: no derived key is itself a
    # constituent, so one pass over the table reaches the fixed point.
    _derived_keys = set(mod._DERIVED_ROW_CONSTITUENTS.keys())
    _all_constituents: set[str] = set()
    for _constituents in mod._DERIVED_ROW_CONSTITUENTS.values():
        _all_constituents.update(_constituents)
    assert _derived_keys.isdisjoint(_all_constituents), (
        f"_DERIVED_ROW_CONSTITUENTS keys overlap with constituents "
        f"({_derived_keys & _all_constituents}); the single-pass cascade "
        "would no longer reach the fixed point"
    )

    base_facts = _plnt_facts()
    for index in range(len(base_facts)):
        fact_key = base_facts[index]["key"]
        for field, value in (
            ("display_quantum", "5_thousand"),
            ("unit", "EUR"),
            ("scale_power10", 6),
        ):
            facts = [dict(fact) for fact in base_facts]
            _contradict(facts, fact_key, field, value)
            document = project_economic_change(_plnt_case(facts=facts))
            rows = {r["key"]: r for r in document["results"]}
            for derived_key, constituents in (
                _ORACLE_DERIVED_CONSTITUENTS.items()
            ):
                derived = rows.get(derived_key)
                if derived is None or derived["value_text"] is None:
                    continue
                for constituent_key in constituents:
                    constituent = rows.get(constituent_key)
                    suppressed = constituent is not None and (
                        constituent["value_text"] is None
                    )
                    assert not suppressed, (
                        f"grid point fact[{index}]={fact_key} "
                        f"field={field}: derived row {derived_key} "
                        f"publishes {derived['value_text']!r} while "
                        f"constituent {constituent_key} is withheld "
                        f"({constituent['withheld_reason']!r})"
                    )


def test_screen_withheld_rows_are_recorded_in_degraded_dependencies() -> None:
    """W15-F-FVA item 2: screen withholdings are recorded, ALWAYS.

    The module docstring's dependency-local rule promises a suppressed
    result is "recorded in ``degraded_dependencies``". The
    stated-definition screen used to withhold rows without recording
    them, so the all-six display_quantum contradiction reached
    availability "unavailable" with an empty ``degraded_dependencies``
    and died in the document's own contract self-check (HEAD c334b9ba:
    CaseShapeError, engine :1473). Block 1 builds that case exactly as
    the two quantum/unit DECLINED tests build it (mutate every fact of
    ``_plnt_case``) and asserts (a) availability, (b) the EXACT set of
    ``(dependency, reason)`` pairs the screen contributed -- every
    emitted result key, once -- and (c) the module's own validator
    accepts the recorded document. Block 2 pins one partial case, the
    D2 ``_mutate_total_revenue_unit`` mutator: availability stays
    "ready" and the list gains exactly the withheld rows' entries.

    Reason vocabulary, measured (not guessed): five of the six rows
    fail their OWN stated-definition check in the all-six quantum case
    -- including ``advertising_net_change``, whose envelopes contradict
    directly, exactly as in the committed d1 grid param -- so they
    record ``result_envelope_contradicts_stated_definition``. Only the
    ``_pct`` ratio is exempt from its own envelope check and is
    withheld by the ``_DERIVED_ROW_CONSTITUENTS`` cascade, recording
    ``dependency_suppressed``.
    """
    case = _plnt_case()
    for fact in case["facts"]:
        fact["display_quantum"] = "5_thousand"
    document = project_economic_change(case)

    # (a) every row withheld -> unavailable, never an empty ready.
    assert document["availability"] == "unavailable"

    # (b) the exact pairs the screen contributed: each of the six
    # emitted result keys, once.
    emitted_keys = {result["key"] for result in document["results"]}
    assert emitted_keys == {
        RESULT_KEY_TOTAL_REVENUE_CHANGE,
        RESULT_KEY_ADVERTISING_REVENUE_CHANGE,
        RESULT_KEY_ADVERTISING_EXPENSE_CHANGE,
        RESULT_KEY_ADVERTISING_NET_CHANGE,
        RESULT_KEY_ADVERTISING_CURRENT_PERIOD_NET,
        RESULT_KEY_ADVERTISING_SHARE_OF_REVENUE_CHANGE_PCT,
    }
    contributed = {
        (entry["dependency"], entry["reason"])
        for entry in document["degraded_dependencies"]
    }
    assert contributed == {
        (RESULT_KEY_TOTAL_REVENUE_CHANGE, _WITHHELD_REASON),
        (RESULT_KEY_ADVERTISING_REVENUE_CHANGE, _WITHHELD_REASON),
        (RESULT_KEY_ADVERTISING_EXPENSE_CHANGE, _WITHHELD_REASON),
        (RESULT_KEY_ADVERTISING_NET_CHANGE, _WITHHELD_REASON),
        (RESULT_KEY_ADVERTISING_CURRENT_PERIOD_NET, _WITHHELD_REASON),
        (RESULT_KEY_ADVERTISING_SHARE_OF_REVENUE_CHANGE_PCT,
         "dependency_suppressed"),
    }
    assert len(document["degraded_dependencies"]) == 6

    # (c) the module's own validator accepts the recorded document --
    # the same call the self-check tests use.
    _assert_document_matches_contract_shape(document)

    # -- Block 2: the D2 total_revenue_unit partial case -------------
    facts = [dict(fact) for fact in _plnt_facts()]
    _mutate_total_revenue_unit(facts)
    partial = project_economic_change(_plnt_case(facts=facts))
    assert partial["availability"] == "ready"
    pairs = {
        (entry["dependency"], entry["reason"])
        for entry in partial["degraded_dependencies"]
    }
    assert pairs == {
        (RESULT_KEY_TOTAL_REVENUE_CHANGE, _WITHHELD_REASON),
        (RESULT_KEY_ADVERTISING_SHARE_OF_REVENUE_CHANGE_PCT,
         "dependency_suppressed"),
    }
    _assert_document_matches_contract_shape(partial)


def test_make_ratio_result_refusals_and_omitted_derived_row_recording() -> None:
    """Ruling A's two legs land differently in ``degraded_dependencies``.

    Spec §8a (research/consumer_cyclical/v1/V1_PLNT_BOUNDARY_AND_FROZEN_SPEC.md):
    (i) a ratio refused for a nonpositive denominator is emitted with its
    ``withheld_reason`` and is not recorded (mutant (c) from the #9351 review,
    which records ratio refusals, fails here); (ii) a derived row omitted for
    a missing constituent is recorded as ``inputs_absent_result_omitted``,
    not as the cascade's ``dependency_suppressed``.
    """
    # (i) All six PLNT facts, with current total revenue below the prior
    # 340879: the change is negative, so the share ratio's denominator is
    # nonpositive and the ratio is withheld.
    facts = [dict(fact) for fact in _plnt_facts()]
    for fact in facts:
        if (
            fact["metric"] == FACT_KEY_TOTAL_REVENUE
            and fact["period_end"] == "2026-06-30"
        ):
            fact["value_text"] = "300000"
    document = project_economic_change(_plnt_case(facts=facts))

    assert document["availability"] == "ready", document
    share = _result_by_key(
        document, RESULT_KEY_ADVERTISING_SHARE_OF_REVENUE_CHANGE_PCT
    )
    assert share["withheld_reason"] == "denominator_nonpositive", share
    assert document["degraded_dependencies"] == [], (
        "Ruling A: a WITHHELD ratio is an answer about present inputs "
        "and is deliberately not a degraded dependency; mutant (c) "
        "would record the ratio refusal here and fail this assertion",
        document["degraded_dependencies"],
    )

    # (ii) Advertising revenue has only its current fact, so its change row
    # is omitted, and the derived ``advertising_net_change`` row, missing a
    # constituent, is omitted too.
    partial_facts = [
        _plnt_fact(
            key=FACT_KEY_TOTAL_REVENUE,
            period_role="current",
            period_end="2026-06-30",
            value_text="365223",
            native_ref="src_plnt_q2_2026_ex991",
        ),
        _plnt_fact(
            key=FACT_KEY_TOTAL_REVENUE,
            period_role="prior",
            period_end="2025-06-30",
            value_text="340879",
            native_ref="src_plnt_q2_2026_ex991",
        ),
        _plnt_fact(
            key=FACT_KEY_ADVERTISING_REVENUE,
            period_role="current",
            period_end="2026-06-30",
            value_text="32922",
            native_ref="src_plnt_q2_2026_ex991",
        ),
        _plnt_fact(
            key=FACT_KEY_ADVERTISING_EXPENSE,
            period_role="current",
            period_end="2026-06-30",
            value_text="32922",
            native_ref="src_plnt_q2_2026_ex991",
        ),
        _plnt_fact(
            key=FACT_KEY_ADVERTISING_EXPENSE,
            period_role="prior",
            period_end="2025-06-30",
            value_text="22777",
            native_ref="src_plnt_q2_2026_ex991",
        ),
    ]
    document = project_economic_change(_plnt_case(facts=partial_facts))
    pairs = {
        (entry["dependency"], entry["reason"])
        for entry in document["degraded_dependencies"]
    }
    # ``_compose_changes`` keys its entry on the fact metric and the omission
    # loop keys its entries on the result key, so both entries survive.
    assert (
        FACT_KEY_ADVERTISING_REVENUE,
        "no_compatible_pair_for_comparison_basis",
    ) in pairs, (
        "_compose_changes records the omitted metric under the "
        "metric key; expect ``advertising_revenue``, not "
        "``advertising_revenue_change``",
        pairs,
    )
    assert (
        RESULT_KEY_ADVERTISING_NET_CHANGE,
        "inputs_absent_result_omitted",
    ) in pairs
    assert (
        RESULT_KEY_ADVERTISING_NET_CHANGE,
        "dependency_suppressed",
    ) not in pairs, (
        "the cascade's own ``dependency_suppressed`` reason must NOT "
        "reach ``degraded_dependencies``; the omission loop records "
        "``inputs_absent_result_omitted`` instead",
        pairs,
    )


def test_unpaired_fact_dedupes_screen_withheld_row_in_degraded_dependencies() -> None:
    """Pin the screen recorder's dedupe on ``dependency``.

    A CONSTRUCTION: ``total_revenue_change`` is a result key, not a V1 metric,
    so admitting a fact under that metric name makes the ``_compose_changes``
    entry for the unpaired fact collide with the screen's entry for the
    ``total_revenue_change`` row withheld for a defective current
    ``display_quantum``. In V1 the two vocabularies are disjoint. Mutant (d)
    from the #9351 review (dedupe removed) makes the count 2. The first entry
    wins: at HEAD the survivor is ``no_compatible_pair_for_comparison_basis``
    and the screen's ``_DEFINITION_CONTRADICTED`` is dropped. The test pins
    the count, not the reason.
    """
    # Leg 1: an unpaired fact under the result-key metric name.
    unpaired = _plnt_fact(
        key="total_revenue_change",
        period_role="current",
        period_end="2026-06-30",
        value_text="24344",
        native_ref="src_plnt_q2_2026_ex991",
        metric="total_revenue_change",
        # ``_plnt_fact`` derives ``kind`` only for V1 metrics; without it the
        # admission gate refuses the fact (``fact_kind_outside_vocabulary``).
        kind="revenue_line",
    )

    # Leg 2: a total-revenue pair whose current envelope fails the screen.
    current = _plnt_fact(
        key=FACT_KEY_TOTAL_REVENUE,
        period_role="current",
        period_end="2026-06-30",
        value_text="365223",
        native_ref="src_plnt_q2_2026_ex991",
    )
    # The pair still selects (``display_quantum`` is not a pairing key), so
    # the change row is built ready and then withheld by the screen.
    current["display_quantum"] = "5_thousand"
    prior = _plnt_fact(
        key=FACT_KEY_TOTAL_REVENUE,
        period_role="prior",
        period_end="2025-06-30",
        value_text="340879",
        native_ref="src_plnt_q2_2026_ex991",
    )
    facts = [unpaired, current, prior]

    document = project_economic_change(_plnt_case(facts=facts))
    deps_for_trc = [
        entry
        for entry in document["degraded_dependencies"]
        if entry["dependency"] == "total_revenue_change"
    ]
    assert len(deps_for_trc) == 1, (
        "dedupe should keep exactly one entry for the "
        "``total_revenue_change`` dependency; mutant (d) (dedupe removed) "
        "lets the screen recorder add a second entry",
        deps_for_trc,
    )


def test_unpaired_fact_dedupes_emittable_keys_loop_in_degraded_dependencies() -> None:
    """Pin the result-side recorders' dedupe on ``dependency``.

    A CONSTRUCTION: ``advertising_revenue_change`` is a result key, not a V1
    metric, so admitting an unpaired fact under that metric name makes the
    ``_compose_changes`` entry collide with the ``_emittable_keys`` loop's
    entry for the absent result. Mutant (no-dedupe-guard) makes the count 2.
    The test pins the count, not the reason.
    """
    # Leg 1: an unpaired fact under the result-key metric name; no
    # advertising-revenue pair means the result is never built.
    unpaired = _plnt_fact(
        key="advertising_revenue_change",
        period_role="current",
        period_end="2026-06-30",
        value_text="289",
        native_ref="src_plnt_q2_2026_ex991",
        metric="advertising_revenue_change",
        # ``_plnt_fact`` derives ``kind`` only for V1 metrics; without it the
        # admission gate refuses the fact (``fact_kind_outside_vocabulary``).
        kind="revenue_line",
    )
    facts = [unpaired]

    document = project_economic_change(_plnt_case(facts=facts))
    deps_for_arc = [
        entry
        for entry in document["degraded_dependencies"]
        if entry["dependency"] == "advertising_revenue_change"
    ]
    assert len(deps_for_arc) == 1, (
        "dedupe should keep exactly one entry for the "
        "``advertising_revenue_change`` dependency; removing the "
        "``_already_degraded`` guard lets the ``_emittable_keys`` loop "
        "add a second entry",
        deps_for_arc,
    )


def test_v1_fact_metrics_and_emittable_result_keys_are_disjoint_and_ordered() -> None:
    """Pin the disjointness, uniqueness, and order of the two vocabularies.

    A CONSTRUCTION: ``_V1_FACT_METRICS`` and ``_EMITTABLE_RESULT_KEYS`` are
    the inputs to the result-side recorders' dedupe on ``dependency``; if
    they overlap or drift, an admitted fact collides with a result key and
    the dedupe cannot restore the one-fact-one-entry invariant. Mutant (m1)
    adds ``"total_revenue_change"`` to ``_V1_FACT_METRICS`` (overlap); mutant
    (m2) swaps two adjacent entries of ``_EMITTABLE_RESULT_KEYS`` (order).
    """
    from engine.sector_intelligence import consumer_cyclical_projection as _proj

    assert _proj._V1_FACT_METRICS.isdisjoint(_proj._EMITTABLE_RESULT_KEYS), (
        "fact metrics and emittable result keys must be disjoint; mutant "
        "(m1) adds a result key to ``_V1_FACT_METRICS``",
        _proj._V1_FACT_METRICS,
        _proj._EMITTABLE_RESULT_KEYS,
    )
    assert len(set(_proj._EMITTABLE_RESULT_KEYS)) == len(
        _proj._EMITTABLE_RESULT_KEYS
    ), (
        "_EMITTABLE_RESULT_KEYS must have no duplicates",
        _proj._EMITTABLE_RESULT_KEYS,
    )
    assert list(_proj._EMITTABLE_RESULT_KEYS) == [
        _proj.RESULT_KEY_TOTAL_REVENUE_CHANGE,
        _proj.RESULT_KEY_ADVERTISING_REVENUE_CHANGE,
        _proj.RESULT_KEY_ADVERTISING_EXPENSE_CHANGE,
        _proj.RESULT_KEY_ADVERTISING_NET_CHANGE,
        _proj.RESULT_KEY_ADVERTISING_CURRENT_PERIOD_NET,
        _proj.RESULT_KEY_ADVERTISING_SHARE_OF_REVENUE_CHANGE_PCT,
    ], (
        "_EMITTABLE_RESULT_KEYS must list the six RESULT_KEY_* values in "
        "definition order; mutant (m2) swaps two adjacent entries",
        _proj._EMITTABLE_RESULT_KEYS,
    )


# ---------------------------------------------------------------------------
# W15-B-C12C1: one malformed fact withholds itself, never kills the projection
# ---------------------------------------------------------------------------


def test_calendar_invalid_period_end_is_withheld_not_a_case_error() -> None:
    """``2026-06-31`` passes ``_DATE_RE`` but names no day on a calendar.

    Admission is regex-only, so the fact travelled into the document and the
    contract's own ``format: date`` check raised ``CaseShapeError`` from the
    backstop, losing the whole projection. The surviving-result assertions
    mirror ``test_dependency_local_degradation_unparseable_value_text``
    (advertising stays READY when one total_revenue side is refused).
    """
    facts = _plnt_facts()
    for f in facts:
        if f["metric"] == FACT_KEY_TOTAL_REVENUE and f["period_end"] == "2026-06-30":
            f["period_end"] = "2026-06-31"
            break
    document = project_economic_change(_plnt_case(facts=facts))
    emitted_fact_keys = {f["key"] for f in document["facts"]}
    assert "total_revenue_current" not in emitted_fact_keys
    reasons = {
        d["dependency"]: d["reason"] for d in document["degraded_dependencies"]
    }
    assert reasons.get(FACT_KEY_TOTAL_REVENUE) == (
        "fact_period_end_missing_or_malformed"
    ), reasons
    assert _result_by_key(
        document, RESULT_KEY_ADVERTISING_REVENUE_CHANGE
    )["value_text"] == "10141"


def test_double_minus_scale_is_withheld_not_int_crash() -> None:
    """``"--3".lstrip("-").isdigit()`` is True while ``int("--3")`` raises.

    Stripping ALL leading minuses then calling ``int`` let the string pass
    admission and crash the projection inside ``_envelope_scale``.
    """
    facts = _plnt_facts()
    for f in facts:
        if f["metric"] == FACT_KEY_TOTAL_REVENUE and f["period_end"] == "2026-06-30":
            f["scale_power10"] = "--3"
            break
    document = project_economic_change(_plnt_case(facts=facts))
    emitted_fact_keys = {f["key"] for f in document["facts"]}
    assert "total_revenue_current" not in emitted_fact_keys
    reasons = {
        d["dependency"]: d["reason"] for d in document["degraded_dependencies"]
    }
    assert reasons.get(FACT_KEY_TOTAL_REVENUE) == (
        "fact_scale_power10_missing_or_malformed"
    ), reasons


def test_superscript_scale_is_withheld() -> None:
    """``"²"`` is a Unicode digit to ``str.isdigit`` and unusable by ``int``.

    Same hole as the double minus: the gate asked the wrong predicate, so
    the crash moved to ``int()`` and the document was lost.
    """
    facts = _plnt_facts()
    for f in facts:
        if f["metric"] == FACT_KEY_TOTAL_REVENUE and f["period_end"] == "2026-06-30":
            f["scale_power10"] = "\u00b2"
            break
    document = project_economic_change(_plnt_case(facts=facts))
    emitted_fact_keys = {f["key"] for f in document["facts"]}
    assert "total_revenue_current" not in emitted_fact_keys
    reasons = {
        d["dependency"]: d["reason"] for d in document["degraded_dependencies"]
    }
    assert reasons.get(FACT_KEY_TOTAL_REVENUE) == (
        "fact_scale_power10_missing_or_malformed"
    ), reasons


def test_single_minus_and_plain_digit_scale_strings_stay_admitted() -> None:
    """Control: the tightened grammar must not refuse genuinely usable text.

    ``"-3"`` and ``"6"`` were always readable by ``_envelope_scale`` and stay
    admitted with their value preserved; no defaulting to 0, no refusal.
    """
    for scale in ("-3", "6"):
        facts = _plnt_facts()
        for f in facts:
            if (
                f["metric"] == FACT_KEY_TOTAL_REVENUE
                and f["period_end"] == "2026-06-30"
            ):
                f["scale_power10"] = scale
                break
        document = project_economic_change(_plnt_case(facts=facts))
        emitted = {f["key"]: f for f in document["facts"]}
        assert "total_revenue_current" in emitted, scale
        assert emitted["total_revenue_current"]["scale_power10"] == int(scale)
        reasons = {d["reason"] for d in document["degraded_dependencies"]}
        assert "fact_scale_power10_missing_or_malformed" not in reasons, scale


def test_calendar_invalid_period_start_is_withheld_not_a_case_error() -> None:
    """``2026-04-31`` passes ``_DATE_RE`` but April has thirty days.

    Before the fix only ``period_end`` was checked against a calendar, so an
    impossible start day reached the contract's ``format: date`` backstop and
    raised ``CaseShapeError`` for the whole projection.
    """
    facts = _plnt_facts()
    for f in facts:
        if f["metric"] == FACT_KEY_TOTAL_REVENUE and f["period_end"] == "2026-06-30":
            f["period_start"] = "2026-04-31"
            break
    document = project_economic_change(_plnt_case(facts=facts))
    emitted_fact_keys = {f["key"] for f in document["facts"]}
    assert "total_revenue_current" not in emitted_fact_keys
    reasons = {
        d["dependency"]: d["reason"] for d in document["degraded_dependencies"]
    }
    assert reasons.get(FACT_KEY_TOTAL_REVENUE) == (
        "fact_period_start_missing_or_malformed"
    ), reasons
    assert _result_by_key(
        document, RESULT_KEY_ADVERTISING_REVENUE_CHANGE
    )["value_text"] == "10141"


def test_non_ascii_decimal_digit_scale_is_withheld() -> None:
    """``int()`` reads U+0663 as 3, so an unguarded ``\\d`` would publish it.

    ``_SCALE_TEXT_RE`` spells ``[0-9]`` on purpose. These are category Nd
    digits that ``\\d`` matches; each must be refused, not rebased to 3.
    """
    for scale in ("\u0663", "\u0969", "\uff13"):
        facts = _plnt_facts()
        for f in facts:
            if (
                f["metric"] == FACT_KEY_TOTAL_REVENUE
                and f["period_end"] == "2026-06-30"
            ):
                f["scale_power10"] = scale
                break
        document = project_economic_change(_plnt_case(facts=facts))
        emitted_fact_keys = {f["key"] for f in document["facts"]}
        assert "total_revenue_current" not in emitted_fact_keys, scale
        reasons = {
            d["dependency"]: d["reason"]
            for d in document["degraded_dependencies"]
        }
        assert reasons.get(FACT_KEY_TOTAL_REVENUE) == (
            "fact_scale_power10_missing_or_malformed"
        ), (scale, reasons)
