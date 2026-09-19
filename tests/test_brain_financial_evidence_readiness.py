"""Financial evidence readiness: exact facts stay separate from context metrics.

This is a source-bound admission packet, not another calculator or fact store.
"""
from __future__ import annotations

import importlib
import importlib.util
import json
import math

import pytest

MODULE = "engine.neuralweb.financial_evidence_readiness"


def module():
    assert importlib.util.find_spec(MODULE) is not None, "financial evidence readiness module is not implemented"
    return importlib.import_module(MODULE)


def source_span(*, state="byte_replayed", rights="rp_public_primary_v1"):
    return {
        "schema": "source_span.v1",
        "span_id": "span_62ac5b46e003dffa2124",
        "document_id": "disclosure_document_" + "a" * 64,
        "document_version": 1,
        "locator": {
            "kind": "text_span",
            "sub_kind": "transcript_segment",
            "segment_index": 0,
            "span_start_byte": 19519,
            "span_end_byte": 19526,
        },
        "text_sha256": "4" * 64,
        "display_excerpt": "109,417",
        "rights_profile": rights,
        "authority": "context_only",
        "receipt_state": state,
        "receipt": {
            "source_sha256": "d" * 64,
            "segment_sha256": "d" * 64,
            "segment_bytes": 173598,
            "segment_index": 0,
            "span_start_byte": 19519,
            "span_end_byte": 19526,
            "text_sha256": "4" * 64,
        },
        "unreplayable_reason": None,
    }


def workspace_result(*, fact=None, lifecycle_state="corrected"):
    if fact is None:
        fact = {
            "schema": "event_fact.v1",
            "fact_id": "fact_revenue_gaap",
            "event_id": "evt_cik0000320193_2026q3_results",
            "metric": "revenue",
            "value": 109417.0,
            "unit": "usd_millions",
            "period": "2026-06-27",
            "basis": "gaap",
            "source_span": source_span(),
        }
    return {
        "available": True,
        "ticker": "AAPL",
        "event_id": "evt_cik0000320193_2026q3_results",
        "event_alias": "AAPL/2026Q3",
        "workspace": {
            "schema": "event_workspace.v1",
            "event_id": "evt_cik0000320193_2026q3_results",
            "fiscal_period": {"year": 2026, "quarter": 3, "calendar_end": "2026-06-27"},
            "lifecycle": {
                "state": lifecycle_state,
                "observed_at": "2026-09-19T04:41:41Z",
                "source_available_at": "2026-07-30T20:30:28Z",
            },
            "facts": [fact],
            "generation_id": "28fd09b9e05e598559b1f324",
            "authority": "context_only",
            "prophet_flags": {
                "may_rank": False,
                "may_size": False,
                "may_gate": False,
                "prophet_authority": False,
            },
        },
        "is_context_only": True,
        "display_only": True,
        "authority": "context_only",
        "receipt": {
            "generation_id": "28fd09b9e05e598559b1f324",
            "workspace_sha256": "e" * 64,
        },
    }


def company_result():
    return {
        "available": True,
        "ticker": "AAPL",
        "latest_event": {
            "event_id": "cie_98e318c37ec1a2a1f83c45e1",
            "call_date": "2026-07-30",
            "metrics": {
                "revenue_growth_pct": 16,
                "eps_growth_pct": 29,
                "gross_margin_pct": 50.1,
                "sentiment": 0.22,
            },
            "field_lineage": {
                "metrics": {
                    "revenue_growth_pct": "earnings_history",
                    "eps_growth_pct": "earnings_history",
                    "gross_margin_pct": "earnings_history",
                    "sentiment": "score_overlay",
                }
            },
        },
        "is_context_only": True,
        "display_only": True,
        "authority": "context_only",
    }


def test_exact_revenue_and_context_metrics_are_machine_distinct():
    r = module().build_financial_evidence_readiness(
        workspace_result=workspace_result(),
        company_result=company_result(),
    )
    assert r["schema"] == "brain.financial_evidence_readiness.v1"
    assert r["status"] == "partial"
    assert r["authority"] == "context_only"
    assert r["ticker"] == "AAPL"
    assert r["event"]["event_id"] == "evt_cik0000320193_2026q3_results"
    assert r["event"]["lifecycle_state"] == "corrected"
    assert r["event"]["generation_id"] == "28fd09b9e05e598559b1f324"

    assert r["exact_facts"] == [{
        "fact_id": "fact_revenue_gaap",
        "metric": "revenue",
        "value": "109417",
        "unit": "usd_millions",
        "currency": "USD",
        "amount_scale": "millions",
        "period_end": "2026-06-27",
        "basis": "gaap",
        "source": {
            "span_id": "span_62ac5b46e003dffa2124",
            "text_sha256": "4" * 64,
            "source_sha256": "d" * 64,
            "receipt_state": "byte_replayed",
            "rights_profile": "rp_public_primary_v1",
        },
    }]

    by_name = {x["metric"]: x for x in r["context_metrics"]}
    assert set(by_name) == {"revenue_growth_pct", "eps_growth_pct", "gross_margin_pct"}
    assert by_name["gross_margin_pct"]["value"] == "50.1"
    assert by_name["gross_margin_pct"]["lineage"] == "earnings_history"
    assert by_name["gross_margin_pct"]["evidence_class"] == "context_metric_not_span_bound"
    assert "sentiment" not in by_name


def test_readiness_refuses_to_invent_period_duration_or_calculator_payload():
    r = module().build_financial_evidence_readiness(
        workspace_result=workspace_result(),
        company_result=company_result(),
    )
    readiness = r["financial_bridge_readiness"]
    assert readiness["ready"] is False
    assert readiness["calculator_payload"] is None
    assert readiness["blockers"] == [
        "current_revenue_period_duration_unavailable",
        "prior_exact_revenue_unavailable",
        "exact_gross_margin_unavailable",
        "exact_operating_profit_inputs_unavailable",
        "cash_bridge_inputs_unavailable",
        "valuation_inputs_unavailable",
    ]
    assert "period_months" not in json.dumps(r)
    assert any("period label" in x.lower() for x in readiness["next_evidence_needed"])
    assert any("prior event" in x.lower() for x in readiness["next_evidence_needed"])


def test_context_gross_margin_never_upgrades_to_exact_financial_fact():
    r = module().build_financial_evidence_readiness(
        workspace_result=workspace_result(),
        company_result=company_result(),
    )
    assert [x["metric"] for x in r["exact_facts"]] == ["revenue"]
    assert "exact_gross_margin_unavailable" in r["financial_bridge_readiness"]["blockers"]


@pytest.mark.parametrize("mutation", ["unreplayable", "private_rights", "non_gaap", "bad_unit", "nan"])
def test_malformed_or_nonpublic_revenue_is_not_promoted_to_exact_fact(mutation):
    fact = {
        "schema": "event_fact.v1",
        "fact_id": "fact_revenue_gaap",
        "event_id": "evt_cik0000320193_2026q3_results",
        "metric": "revenue",
        "value": 109417.0,
        "unit": "usd_millions",
        "period": "2026-06-27",
        "basis": "gaap",
        "source_span": source_span(),
    }
    if mutation == "unreplayable":
        fact["source_span"] = source_span(state="unreplayable")
    elif mutation == "private_rights":
        fact["source_span"] = source_span(rights="rp_private_v1")
    elif mutation == "non_gaap":
        fact["basis"] = "non_gaap"
    elif mutation == "bad_unit":
        fact["unit"] = "currency_unknown"
    elif mutation == "nan":
        fact["value"] = float("nan")
    r = module().build_financial_evidence_readiness(
        workspace_result=workspace_result(fact=fact),
        company_result=company_result(),
    )
    assert r["exact_facts"] == []
    assert "current_exact_revenue_unavailable" in r["financial_bridge_readiness"]["blockers"]


def test_typed_absence_stays_absent_not_zero():
    fact = {
        "schema": "event_fact.v1",
        "fact_id": "fact_revenue_gaap",
        "event_id": "evt_cik0000320193_2026q3_results",
        "metric": "revenue",
        "typed_absence": {
            "reason": "no_span_addressable_evidence",
            "subject": "revenue",
        },
    }
    r = module().build_financial_evidence_readiness(
        workspace_result=workspace_result(fact=fact),
        company_result=company_result(),
    )
    assert r["exact_facts"] == []
    assert "current_exact_revenue_unavailable" in r["financial_bridge_readiness"]["blockers"]
    assert "109417" not in json.dumps(r)


def test_unavailable_workspace_can_still_return_bounded_context_metrics():
    r = module().build_financial_evidence_readiness(
        workspace_result={"available": False, "ticker": "AAPL", "note": "not covered"},
        company_result=company_result(),
    )
    assert r["status"] == "context_only"
    assert r["exact_facts"] == []
    assert len(r["context_metrics"]) == 3
    assert r["financial_bridge_readiness"]["ready"] is False
    assert r["financial_bridge_readiness"]["blockers"][0] == "current_exact_revenue_unavailable"


def test_bad_context_numbers_are_dropped_not_serialized_as_nan():
    ctx = company_result()
    ctx["latest_event"]["metrics"]["gross_margin_pct"] = float("inf")
    ctx["latest_event"]["metrics"]["eps_growth_pct"] = True
    r = module().build_financial_evidence_readiness(
        workspace_result=workspace_result(),
        company_result=ctx,
    )
    assert {x["metric"] for x in r["context_metrics"]} == {"revenue_growth_pct"}
    json.dumps(r, allow_nan=False)


def test_packet_has_no_trade_or_signal_authority():
    r = module().build_financial_evidence_readiness(
        workspace_result=workspace_result(),
        company_result=company_result(),
    )
    dumped = json.dumps(r).lower()
    for forbidden in ("target_price", '"rank"', '"score"', '"trade"', '"signal"', '"probability"'):
        assert forbidden not in dumped
    assert r["authority"] == "context_only"
    assert r["financial_bridge_readiness"]["authority"] == "admission_only"


def test_reader_wrapper_uses_existing_company_intelligence_readers_once(monkeypatch):
    m = module()
    calls = []
    def current(params):
        calls.append(("workspace", dict(params)))
        return workspace_result()
    def context(params):
        calls.append(("company", dict(params)))
        return company_result()
    monkeypatch.setattr(m, "_reader_functions", lambda: (current, context))
    r = m.read_financial_evidence_readiness({"ticker": "aapl"})
    assert r["ticker"] == "AAPL"
    assert calls == [
        ("workspace", {"ticker": "AAPL"}),
        ("company", {"ticker": "AAPL"}),
    ]


@pytest.mark.parametrize("bad", ["", "../AAPL", "AAPL/../../x", True, None, "AAPL PRIVATE"])
def test_invalid_ticker_refuses_before_any_reader(monkeypatch, bad):
    m = module()
    monkeypatch.setattr(m, "_reader_functions", lambda: (
        lambda _p: (_ for _ in ()).throw(AssertionError("workspace reader called")),
        lambda _p: (_ for _ in ()).throw(AssertionError("company reader called")),
    ))
    r = m.read_financial_evidence_readiness({"ticker": bad})
    assert r["status"] == "invalid_request"
    assert r["exact_facts"] == []
    assert r["context_metrics"] == []


def test_unknown_request_fields_fail_closed_without_echo(monkeypatch):
    m = module()
    monkeypatch.setattr(m, "_reader_functions", lambda: (
        lambda _p: (_ for _ in ()).throw(AssertionError("reader called")),
        lambda _p: (_ for _ in ()).throw(AssertionError("reader called")),
    ))
    r = m.read_financial_evidence_readiness({
        "ticker": "AAPL",
        "portfolio": "PRIVATE_CUSTOMER_MARKER",
    })
    assert r["status"] == "invalid_request"
    assert "PRIVATE_CUSTOMER_MARKER" not in json.dumps(r)


def test_packet_is_bounded_and_deterministic():
    m = module()
    a = m.build_financial_evidence_readiness(
        workspace_result=workspace_result(),
        company_result=company_result(),
    )
    b = m.build_financial_evidence_readiness(
        workspace_result=workspace_result(),
        company_result=company_result(),
    )
    assert a == b
    assert len(json.dumps(a, sort_keys=True)) < 12000
