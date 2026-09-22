"""Acceptance tests for the bounded ``capital_need.v1`` read model."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from engine.capital_need import assemble_capital_need
from engine.cash_runway import extract_cash_runway
from engine.debt_maturity import extract_maturity_ladder


FIXTURES = Path(__file__).parent / "fixtures"


def _load(path: Path) -> dict:
    return json.loads(path.read_text())


def _aapl_blocks():
    as_of = date(2026, 9, 22)
    debt = extract_maturity_ladder(
        _load(FIXTURES / "debt_maturity" / "aapl_trimmed.json"),
        cik="0000320193",
        as_of=as_of,
    )
    cash = extract_cash_runway(
        _load(FIXTURES / "cash_runway" / "aapl_cash_trimmed.json"),
        cik="0000320193",
        as_of=as_of,
    )
    return debt, cash, as_of


def _same_period_debt(cik: str, period: dict, y1: float = 10_000_000) -> dict:
    return {
        "schema": "debt_maturity.v1",
        "status": "reported",
        "cik": cik,
        "unit": "USD",
        "period": dict(period),
        "buckets": [
            {"key": "y1", "usd": y1, "reported": True, "drop_reason": None, "tag": "y1"},
            {"key": "y2", "usd": 0, "reported": True, "drop_reason": None, "tag": "y2"},
        ],
        "total_reported_usd": y1,
        "as_of": "2026-09-22",
    }


def test_aapl_period_mismatch_is_partial_and_withholds_cover():
    debt, cash, as_of = _aapl_blocks()
    # The legacy optional ladder input is guarded too; it cannot reintroduce
    # the former cross-period 323% arithmetic.
    raw_cash = _load(FIXTURES / "cash_runway" / "aapl_cash_trimmed.json")
    guarded_cash = extract_cash_runway(
        raw_cash,
        cik="0000320193",
        as_of=as_of,
        ladder=debt,
    )
    assert guarded_cash["near_term_cover_pct"] is None
    result = assemble_capital_need(
        debt,
        cash,
        issuer_id="ISS:US-XNAS-AAPL",
        security_id="SEC:US-XNAS-AAPL",
        as_of=as_of,
    )

    assert result["status"] == "partial"
    assert "debt_cash_period_mismatch" in result["coverage"]["reasons"]
    assert result["derived"]["near_term_cash_cover"] is None
    assert result["derived"]["near_term_cash_gap_usd"] is None
    # Cash remains a scenario input, while the cross-period debt join is held.
    assert result["derived"]["scenario_runway"]["state"] == "scenario"
    assert result["reported"]["debt_due"]["issuer_debt_outstanding_only"] is True


def test_same_period_burn_exposes_context_only_scenario_and_gap():
    # Keep the synthetic filing within the producer's 550-day freshness
    # window so this exercises a complete same-period join.
    as_of = date(2025, 6, 1)
    cash = extract_cash_runway(
        _load(FIXTURES / "cash_runway" / "synthetic_burn.json"),
        cik="0000099999",
        as_of=as_of,
    )
    debt = _same_period_debt("0000099999", cash["period"])
    result = assemble_capital_need(debt, cash, as_of=as_of)

    assert result["status"] == "complete"
    assert result["derived"]["near_term_cash_cover"]["value_pct"] == 500
    assert result["derived"]["near_term_cash_gap_usd"] == 0
    scenario = result["derived"]["scenario_runway"]
    assert scenario["state"] == "scenario"
    assert scenario["value_months"] == 20.0
    assert scenario["assumptions"]["no_refinancing_forecast"] is True
    assert result["authority"] == {"class": "context_only", "display_only": True}


def test_missing_debt_never_becomes_zero():
    as_of = date(2025, 6, 1)
    cash = extract_cash_runway(
        _load(FIXTURES / "cash_runway" / "synthetic_burn.json"),
        cik="0000099999",
        as_of=as_of,
    )
    result = assemble_capital_need(
        {"schema": "debt_maturity.v1", "status": "not_loaded", "cik": "0000099999"},
        cash,
        as_of=as_of,
    )

    assert result["status"] == "partial"
    assert result["reported"]["debt_due"]["total_reported_usd"] is None
    assert result["derived"]["near_term_cash_cover"] is None
    assert result["derived"]["near_term_cash_gap_usd"] is None
    assert result["derived"]["scenario_runway"]["value_months"] == 20.0


def test_stale_cash_blocks_current_coverage():
    as_of = date(2026, 9, 22)
    cash = extract_cash_runway(
        _load(FIXTURES / "cash_runway" / "synthetic_burn.json"),
        cik="0000099999",
        as_of=date(2027, 1, 1),
    )
    # Keep the exact period, but mark the debt fresh to isolate the cash stale gate.
    debt = _same_period_debt("0000099999", cash["period"])
    result = assemble_capital_need(debt, cash, as_of=as_of)

    assert result["status"] == "partial"
    assert "cash_period_stale" in result["coverage"]["reasons"]
    assert result["derived"]["near_term_cash_cover"] is None
    assert result["derived"]["scenario_runway"]["state"] == "stale"


def test_identity_mismatch_is_fail_closed():
    debt, cash, as_of = _aapl_blocks()
    cash = dict(cash)
    cash["cik"] = "0000000001"
    result = assemble_capital_need(debt, cash, as_of=as_of)

    assert result["status"] == "identity_mismatch"
    assert result["derived"]["near_term_cash_cover"] is None
    assert result["reported"]["cash"] is None


def test_investor_held_scope_is_rejected():
    debt, cash, as_of = _aapl_blocks()
    debt = dict(debt)
    debt["scope"] = "investor_held_par"
    result = assemble_capital_need(debt, cash, as_of=as_of)

    assert result["status"] == "partial"
    assert "debt_investor_held_scope_rejected" in result["coverage"]["reasons"]
    assert result["reported"]["debt_due"] is None
    assert result["derived"]["near_term_cash_cover"] is None


def test_future_filed_source_is_not_available_at_cutoff():
    debt, cash, _ = _aapl_blocks()
    result = assemble_capital_need(
        debt,
        cash,
        as_of=date(2025, 6, 1),
    )

    assert result["status"] == "partial"
    assert "cash_filed_after_as_of" in result["coverage"]["reasons"]
    assert result["reported"]["cash"]["state"] == "unknown"
    assert result["reported"]["cash"]["value"] is None
    assert result["derived"]["scenario_runway"] is None
    assert result["derived"]["near_term_cash_cover"] is None


def test_stock_library_resolver_preserves_non_filer_taxonomy():
    from scripts import build_stock_library as stock_library

    result = stock_library._resolve_capital_need(
        "SPY",
        "ETF / macro",
        date(2026, 9, 22),
        {"status": "not_applicable"},
        {"status": "not_applicable"},
    )
    assert result == {"schema": "capital_need.v1", "version": 1, "status": "not_applicable"}


def test_ticker_page_context_has_capital_need_slot():
    source = Path("scripts/build_ticker_pages.py").read_text()
    assert '"capital_need": (blob or {}).get("capital_need")' in source
    template = Path("templates/_debt_maturity.html.j2").read_text()
    assert 'data-panel="capital_need.v1"' in template


def test_panel_prints_partial_capital_need_without_cross_period_cover():
    from jinja2 import Environment, FileSystemLoader

    from engine import i18n

    env = Environment(loader=FileSystemLoader("templates"), autoescape=True)
    env.globals["t"] = i18n.t
    html = env.get_template("_debt_maturity.html.j2").render(
        debt_maturity={"status": "not_loaded"},
        cash_runway={
            "status": "reported",
            "period": {"end": "2025-09-27", "form": "10-K", "stale": False},
            "runway_display": "self_funding",
            "cash_display": "$35.9B",
            "near_term_cover_pct": 323,
        },
        capital_need={
            "schema": "capital_need.v1",
            "status": "partial",
            "derived": {"near_term_cash_cover": None, "scenario_runway": {"state": "scenario"}},
        },
    )

    assert 'data-panel="capital_need.v1"' in html
    assert "Capital-need coverage is partial" in html
    assert "cash on hand covers 323%" not in html
