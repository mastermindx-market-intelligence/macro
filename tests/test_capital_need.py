"""Acceptance tests for the bounded ``capital_need.v1`` read model."""

from __future__ import annotations

import json
from copy import deepcopy

import pytest
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
            *[{"key": key, "usd": 0, "reported": True, "drop_reason": None, "tag": key}
              for key in ("y2", "y3", "y4", "y5", "after5")],
        ],
        "total_reported_usd": y1,
        "as_of": period["filed"],
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
    assert result["reported"]["debt_due"] is None
    assert result["derived"]["near_term_cash_cover"] is None
    assert result["derived"]["near_term_cash_gap_usd"] is None
    assert result["derived"]["scenario_runway"]["value_months"] == 20.0


def test_stale_cash_blocks_current_coverage():
    as_of = date(2026, 9, 22)
    cash = extract_cash_runway(
        _load(FIXTURES / "cash_runway" / "synthetic_burn.json"),
        cik="0000099999",
        as_of=as_of,
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

    assert result["status"] == "unknown"
    assert "cash_filed_after_as_of" in result["coverage"]["reasons"]
    assert result["reported"]["cash"] is None
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
    assert 'capital_need = _capital_need_for_page(blob, generated_utc)' in source
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
            "schema": "capital_need.v1", "version": 1,
            "authority": {"class": "context_only", "display_only": True},
            "reported": {}, "status": "partial",
            "derived": {"near_term_cash_cover": None, "scenario_runway": {"state": "scenario"}},
        },
    )

    assert 'data-panel="capital_need.v1"' in html
    assert "Capital-need coverage is partial" in html
    assert "cash on hand covers 323%" not in html


def _control():
    cutoff = date(2025, 6, 1)
    cash = extract_cash_runway(
        _load(FIXTURES / "cash_runway" / "synthetic_burn.json"),
        cik="0000099999", as_of=cutoff,
    )
    return _same_period_debt("0000099999", cash["period"]), cash, cutoff


def _render(result, cash=None):
    from jinja2 import Environment, FileSystemLoader
    from engine import i18n
    env = Environment(loader=FileSystemLoader("templates"), autoescape=True)
    env.globals["t"] = i18n.t
    return env.get_template("_debt_maturity.html.j2").render(
        debt_maturity={"status": "not_loaded"}, cash_runway=cash,
        capital_need=result,
    )


@pytest.mark.parametrize("side", ["debt", "cash"])
@pytest.mark.parametrize("field,value", [
    ("cik", None), ("cik", ""), ("cik", True), ("cik", "12345678901"),
    ("schema", "etf_holdings.v1"), ("schema", None), ("version", True), ("version", 2),
    ("unit", "EUR"), ("unit", None), ("currency", "EUR"), ("currency", None),
    ("scope", "investor_held_par"), ("scope", None), ("source_scope", "unknown"),
    ("as_of", None), ("as_of", "bad"), ("as_of", "2025-02-27"),
    ("as_of", "2025-06-02"),
])
def test_rejected_source_never_exposes_values_or_coverage(side, field, value):
    debt, cash, cutoff = _control()
    (debt if side == "debt" else cash)[field] = value
    result = assemble_capital_need(debt, cash, as_of=cutoff)
    assert result["status"] != "complete"
    assert result["derived"]["near_term_cash_cover"] is None
    assert result["derived"]["near_term_cash_gap_usd"] is None
    assert result["reported"]["debt_due" if side == "debt" else "cash"] is None
    if side == "cash":
        assert result["derived"]["scenario_runway"] is None
    html = _render(result, cash)
    assert "covers 500%" not in html
    if side == "cash":
        assert "cash lasts" not in html
        assert "no burn to measure" not in html


@pytest.mark.parametrize("side", ["debt", "cash"])
@pytest.mark.parametrize("key,value", [
    ("filed", None), ("filed", "not-a-date"), ("filed", "2025-06-02"),
    ("end", "2025-02-30"), ("end", None), ("accn", ""), ("accn", []),
    ("form", "10-Q"), ("form", []), ("fp", "Q4"), ("fy", None), ("fy", True),
    ("stale", "false"),
])
def test_incomplete_or_invalid_filing_metadata_is_refused(side, key, value):
    debt, cash, cutoff = _control()
    (debt if side == "debt" else cash)["period"][key] = value
    result = assemble_capital_need(debt, cash, as_of=cutoff)
    assert result["status"] != "complete"
    assert result["derived"]["near_term_cash_cover"] is None
    assert "covers 500%" not in _render(result)


@pytest.mark.parametrize("cutoff", [None, "bad", "2025-02-30", True, {}, "20250228"])
def test_invalid_assembly_clock_refuses_all_numbers(cutoff):
    debt, cash, _ = _control()
    result = assemble_capital_need(debt, cash, as_of=cutoff)
    assert result["status"] == "unknown"
    assert all(v is None for v in result["reported"].values())
    assert all(v is None for v in result["derived"].values())


@pytest.mark.parametrize("bad", [None, "1", True, False, -1, float("nan"), float("inf"), -float("inf"), 10**400])
@pytest.mark.parametrize("field", ["cash_usd", "capex_usd", "debt"])
def test_nonfinite_malformed_or_negative_values_refused(field, bad):
    debt, cash, cutoff = _control()
    if field == "debt":
        debt["buckets"][0]["usd"] = bad
        debt["total_reported_usd"] = bad
    else:
        cash[field] = bad
    result = assemble_capital_need(debt, cash, as_of=cutoff)
    assert result["status"] != "complete"
    assert result["derived"]["near_term_cash_cover"] is None
    assert "covers 500%" not in _render(result, cash)


@pytest.mark.parametrize("kind", ["duplicate", "conflicting_duplicate", "unknown_key", "total_mismatch", "malformed", "unreported_number"])
def test_debt_integrity_is_validated_before_fact_exposure(kind):
    debt, cash, cutoff = _control()
    if "duplicate" in kind:
        duplicate = deepcopy(debt["buckets"][0])
        if kind == "conflicting_duplicate":
            duplicate["usd"] += 1
        debt["buckets"].append(duplicate)
    elif kind == "unknown_key":
        debt["buckets"][0]["key"] = "held_par"
    elif kind == "total_mismatch":
        debt["total_reported_usd"] += 1
    elif kind == "malformed":
        debt["buckets"] = [1]
    else:
        debt["buckets"][0]["reported"] = False
    result = assemble_capital_need(debt, cash, as_of=cutoff)
    assert result["reported"]["debt_due"] is None
    assert result["derived"]["near_term_cash_cover"] is None


def test_partial_ladder_is_not_complete():
    debt, cash, cutoff = _control()
    debt["buckets"] = debt["buckets"][:1]
    result = assemble_capital_need(debt, cash, as_of=cutoff)
    assert result["status"] == "partial"
    assert "debt_ladder_incomplete" in result["coverage"]["reasons"]
    assert result["derived"]["near_term_cash_cover"] is None
    assert result["reported"]["debt_due"]["buckets_reported"] == 1


def test_explicit_zero_principal_is_not_missing_or_a_division_error():
    debt, cash, cutoff = _control()
    debt["buckets"][0]["usd"] = debt["total_reported_usd"] = 0
    result = assemble_capital_need(debt, cash, as_of=cutoff)
    assert result["status"] == "complete"
    assert result["derived"]["near_term_cash_cover"]["state"] == "not_applicable"
    assert result["derived"]["near_term_cash_cover"]["value_pct"] is None
    assert result["derived"]["near_term_cash_gap_usd"] == 0
    assert "reports zero principal" in _render(result)


def test_zero_cash_produces_zero_cover_and_full_shortfall():
    debt, cash, cutoff = _control()
    cash["cash_usd"] = 0
    result = assemble_capital_need(debt, cash, as_of=cutoff)
    assert result["status"] == "complete"
    assert result["derived"]["near_term_cash_cover"]["value_pct"] == 0
    assert result["derived"]["near_term_cash_gap_usd"] == 10_000_000


def test_derived_values_are_recomputed_from_reported_facts():
    debt, cash, cutoff = _control()
    cash.update(free_cash_flow_usd=float("nan"), annual_burn_usd=1,
                monthly_burn_usd=1, runway_months=999, runway_display="self_funding")
    result = assemble_capital_need(debt, cash, as_of=cutoff)
    assert result["derived"]["free_cash_flow"]["value"] == -30_000_000
    assert result["derived"]["scenario_runway"]["value_months"] == 20
    assert result["derived"]["scenario_runway"]["display"] == "months"


def test_negative_ocf_is_valid_but_not_negative_cash_or_capex():
    debt, cash, cutoff = _control()
    cash["ocf_usd"] = -10_000_000
    result = assemble_capital_need(debt, cash, as_of=cutoff)
    assert result["status"] == "complete"
    assert result["derived"]["free_cash_flow"]["value"] == -50_000_000
    assert result["derived"]["scenario_runway"]["value_months"] == 12


@pytest.mark.parametrize("start", [None, "bad", "2024-10-01", "2023-01-01"])
def test_cash_annual_duration_required(start):
    debt, cash, cutoff = _control()
    cash["period"]["start"] = start
    result = assemble_capital_need(debt, cash, as_of=cutoff)
    assert result["reported"]["cash"] is None
    assert result["derived"]["scenario_runway"] is None


def test_freshness_is_recomputed_and_window_is_historical():
    debt, cash, _ = _control()
    result = assemble_capital_need(debt, cash, as_of=date(2026, 6, 1))
    assert result["status"] == "complete"
    html = _render(result)
    assert "Cash reported at 2024-12-31 covers 500%" in html
    assert "12-month bucket following that fiscal period end" in html
    assert "next 12 months" not in html
    stale = assemble_capital_need(debt, cash, as_of=date(2026, 9, 22))
    assert stale["status"] == "partial"
    assert stale["derived"]["near_term_cash_cover"] is None
    assert stale["derived"]["scenario_runway"]["state"] == "stale"
    assert "cash_period_stale" in stale["coverage"]["reasons"]


@pytest.mark.parametrize("mutate", ["schema", "version", "authority", "status", "state", "nan", "inf", "gap"])
def test_template_rejects_malformed_or_rejected_cached_calculations(mutate):
    debt, cash, cutoff = _control()
    result = assemble_capital_need(debt, cash, as_of=cutoff)
    if mutate == "schema":
        result["schema"] = "holdings.v1"
    elif mutate == "version":
        result["version"] = 2
    elif mutate == "authority":
        result["authority"]["class"] = "trade"
    elif mutate == "status":
        result["status"] = "identity_mismatch"
    elif mutate == "state":
        result["derived"]["near_term_cash_cover"]["state"] = "rejected"
    elif mutate in ("nan", "inf"):
        result["derived"]["near_term_cash_cover"]["value_pct"] = float(mutate)
    else:
        result["derived"]["near_term_cash_gap_usd"] = "invalid"
    html = _render(result)
    assert "covers 500%" not in html
    assert "invalid" not in html
    assert "covers nan%" not in html and "covers inf%" not in html


@pytest.mark.parametrize("debt,cash", [("bad", []), ({"period": []}, 1), (None, None)])
def test_malformed_blocks_do_not_raise(debt, cash):
    result = assemble_capital_need(debt, cash, as_of=date(2025, 6, 1))
    assert result["status"] == "unknown"


def test_overflow_in_coverage_is_typed_unknown_not_an_exception():
    debt, cash, cutoff = _control()
    debt["buckets"][0]["usd"] = debt["total_reported_usd"] = 1e-300
    result = assemble_capital_need(debt, cash, as_of=cutoff)
    assert result["derived"]["near_term_cash_cover"] is None
    assert "coverage_arithmetic_nonfinite" in result["coverage"]["reasons"]


@pytest.mark.parametrize("ledger", [
    {"note": "Canonical EDGAR CIKs", "tickers": {"AAPL": 320193, "AMZN": 1018724}},
    {"tickers": {"AAPL": {"cik": 320193}, "AMZN": {"cik": 1018724}}},
    {"AAPL": 320193, "AMZN": 1018724},
])
def test_canonical_wrapped_ledger_resolves_existing_issuer_cache(monkeypatch, tmp_path, ledger):
    from scripts import build_debt_maturity as producer
    path = tmp_path / "ticker_cik_ledger.json"
    path.write_text(json.dumps(ledger))
    monkeypatch.setattr(producer, "_cik_ledger_path", lambda: path)
    monkeypatch.setattr(producer, "_issuer_master_path", lambda: tmp_path / "absent.parquet")
    assert producer.resolve_cik(" aapl ") == "0000320193"
    assert producer.resolve_cik("AMZN") == "0001018724"
    assert producer.resolve_cik("note") is None
    assert producer.resolve_cik("MISSING") is None


def test_malformed_ledger_wrapper_does_not_fall_through_to_metadata(monkeypatch, tmp_path):
    from scripts import build_debt_maturity as producer
    path = tmp_path / "ticker_cik_ledger.json"
    path.write_text(json.dumps({"tickers": [], "AAPL": 320193}))
    monkeypatch.setattr(producer, "_cik_ledger_path", lambda: path)
    monkeypatch.setattr(producer, "_issuer_master_path", lambda: tmp_path / "absent.parquet")
    assert producer.resolve_cik("AAPL") is None


def test_panel_shows_reported_inputs_separately_from_derived_scenario():
    debt, cash, cutoff = _control()
    html = _render(assemble_capital_need(debt, cash, as_of=cutoff))
    for expected in ("Reported operating cash flow", "$10000000",
                     "Reported equipment spending (capex outflow)", "$40000000",
                     "Derived free cash flow (operating cash flow minus capex)", "$-30000000",
                     "2024-01-01", "2024-12-31", "synthetic-2025-01", "USD"):
        assert expected in html


def test_all_debt_panel_copy_is_anchored_to_fiscal_period_end():
    from jinja2 import Environment, FileSystemLoader
    from engine import i18n
    debt, cash, cutoff = _aapl_blocks()
    env = Environment(loader=FileSystemLoader("templates"), autoescape=True)
    env.globals["t"] = i18n.t
    html = env.get_template("_debt_maturity.html.j2").render(
        debt_maturity=debt, cash_runway=cash,
        capital_need=assemble_capital_need(debt, cash, as_of=cutoff),
    )
    assert "next 12 months" not in html.lower()
    assert "All maturity buckets are measured from fiscal period end 2024-09-28" in html
    assert "First 12 months after period end" in html


@pytest.mark.parametrize("side", ["debt", "cash"])
@pytest.mark.parametrize("available", ["bad", None, "2026-01-01", "2025-01-01", "2025-06-01T12:00:00Z"])
def test_optional_availability_clock_is_enforced_when_present(side, available):
    debt, cash, cutoff = _control()
    (debt if side == "debt" else cash)["source_available_at"] = available
    # Source clocks must not predate availability even within request cutoff.
    if side == "cash":
        cash["as_of"] = "2025-02-28"
    result = assemble_capital_need(debt, cash, as_of=cutoff)
    assert result["derived"]["near_term_cash_cover"] is None
    assert f"{side}_source_available_clock_invalid" in result["coverage"]["reasons"]


def test_optional_availability_clock_accepts_known_utc_source():
    debt, cash, cutoff = _control()
    debt["source_available_at"] = cash["source_available_at"] = "2025-02-28T10:00:00Z"
    assert assemble_capital_need(debt, cash, as_of=cutoff)["status"] == "complete"


@pytest.mark.parametrize("bad_field", ["cash", "months", "zero_claim", "zero_period"])
def test_template_rejects_boolean_or_forged_zero_scenario(bad_field):
    debt, cash, cutoff = _control()
    result = assemble_capital_need(debt, cash, as_of=cutoff)
    if bad_field == "cash":
        result["reported"]["cash"]["value"] = True
    elif bad_field == "months":
        result["derived"]["scenario_runway"]["value_months"] = True
    else:
        cover = result["derived"]["near_term_cash_cover"]
        cover.update(state="not_applicable", reason="reported_zero_y1_principal", value_pct=None)
        if bad_field == "zero_period":
            cover["period"] = {"end": "2099-12-31"}
        else:
            cover["value_pct"] = 1
    html = _render(result)
    assert "about True months" not in html
    assert "reports zero principal" not in html
    if bad_field == "cash":
        assert "covers 500%" not in html
        assert "Cash reported at" not in html


def test_producer_resolvers_preserve_acquisition_separately_from_evaluation(monkeypatch):
    from scripts import build_stock_library as builder
    facts = _load(FIXTURES / 'cash_runway' / 'synthetic_burn.json')
    # Add a six-bucket issuer schedule to this explicit test companyfacts.
    from engine.debt_maturity import BUCKETS
    for key, tag, *_ in BUCKETS:
        facts['facts']['us-gaap'][tag] = {'units': {'USD': [{
            'end': '2024-12-31', 'val': 10_000_000 if key == 'y1' else 0,
            'accn': 'synthetic-2025-01', 'fy': 2024, 'fp': 'FY',
            'form': '10-K', 'filed': '2025-02-28',
        }]}}
    fetched = '2025-03-01T09:35:07.756441+00:00'
    facts['fetched_at'] = fetched
    monkeypatch.setattr(builder, '_dm_load', lambda ticker: ('0000099999', facts, 'loaded'))
    cutoff = date(2025, 6, 1)
    debt = builder._resolve_debt_maturity('SYNTHETIC', 'Technology', cutoff)
    cash = builder._resolve_cash_runway('SYNTHETIC', 'Technology', cutoff, debt)
    result = builder._resolve_capital_need('SYNTHETIC', 'Technology', cutoff, debt, cash)
    assert result['status'] == 'complete'
    assert debt['fetched_at'] == cash['fetched_at'] == fetched
    assert result['source_clock']['evaluation_as_of'] == '2025-06-01'
    for side in ('debt', 'cash'):
        assert result['source_clock'][side + '_acquisition'] == {'state': 'observed', 'fetched_at': fetched}
        assert result['source_clock'][side + '_filed'] == '2025-02-28'
    html = _render(result)
    assert fetched in html
    assert '2025-06-01' in html


@pytest.mark.parametrize('value', [None, 'bad', '2025-03-01T10:00:00', '2027-01-01T00:00:00Z'])
def test_acquisition_missing_or_invalid_is_not_replaced_with_evaluation(value):
    debt, cash, cutoff = _control()
    debt['fetched_at'] = cash['fetched_at'] = value
    result = assemble_capital_need(debt, cash, as_of=cutoff)
    for side in ('debt', 'cash'):
        acquisition = result['source_clock'][side + '_acquisition']
        assert acquisition['fetched_at'] != cutoff.isoformat()
        if value != '2027-01-01T00:00:00Z':
            assert acquisition == {'state': 'unknown', 'fetched_at': None}
    if value is not None:
        assert result['derived']['near_term_cash_cover'] is None


def test_huge_integer_cik_is_unknown_without_string_conversion_error():
    debt, cash, cutoff = _control()
    debt['cik'] = 10**10000
    result = assemble_capital_need(debt, cash, as_of=cutoff)
    assert result['derived']['near_term_cash_cover'] is None
    assert 'debt_cik_unknown' in result['coverage']['reasons']
    json.dumps(result, allow_nan=False)


def test_source_date_objects_are_normalized_for_json():
    debt, cash, cutoff = _control()
    debt['as_of'] = cash['as_of'] = cutoff
    result = assemble_capital_need(debt, cash, as_of=cutoff)
    assert result['status'] == 'complete'
    json.dumps(result, allow_nan=False)


def test_large_exact_integer_debt_total_preserves_value():
    debt, cash, cutoff = _control()
    debt['buckets'][0]['usd'] = debt['total_reported_usd'] = 9_007_199_254_740_993
    result = assemble_capital_need(debt, cash, as_of=cutoff)
    assert result['status'] == 'complete'
    assert result['reported']['debt_due']['total_reported_usd'] == 9_007_199_254_740_993


def test_render_consumer_recomputes_poisoned_cached_scenario_and_freshness():
    from scripts.build_ticker_pages import _capital_need_for_page
    debt, cash, cutoff = _control()
    cached = assemble_capital_need(debt, cash, as_of=cutoff)
    cached['derived']['scenario_runway'].update(value_months=999, monthly_burn_usd=1)
    blob = {'debt_maturity': debt, 'cash_runway': cash, 'capital_need': cached}
    actual = _capital_need_for_page(blob, '2025-06-01 10:00 UTC')
    assert actual['derived']['scenario_runway']['value_months'] == 20
    assert '999 months' not in _render(actual)
    stale = _capital_need_for_page(blob, '2026-09-22 10:00 UTC')
    assert stale['derived']['near_term_cash_cover'] is None
    assert stale['derived']['scenario_runway']['state'] == 'stale'


def test_render_consumer_never_uses_cached_math_without_sources():
    from scripts.build_ticker_pages import _capital_need_for_page
    debt, cash, cutoff = _control()
    cached = assemble_capital_need(debt, cash, as_of=cutoff)
    result = _capital_need_for_page({'capital_need': cached}, '2025-06-01 10:00 UTC')
    assert result['status'] == 'unknown'
    assert all(value is None for value in result['derived'].values())


def test_template_malformed_debt_bucket_container_does_not_raise():
    debt, cash, cutoff = _control()
    result = assemble_capital_need(debt, cash, as_of=cutoff)
    result['reported']['debt_due']['buckets'] = 1
    assert 'covers 500%' not in _render(result)


def test_acquisition_cannot_precede_known_source_availability():
    debt, cash, cutoff = _control()
    for block in (debt, cash):
        block.update(as_of='2025-06-01', source_available_at='2025-03-01',
                     fetched_at='2025-02-28T12:00:00Z')
    result = assemble_capital_need(debt, cash, as_of=cutoff)
    assert result['status'] == 'unknown'
    assert result['derived']['near_term_cash_cover'] is None


@pytest.mark.parametrize('status', ['reported', 'no_maturity_facts', 'unresolved'])
def test_product_context_rebuilds_debt_displays_and_order(tmp_path, status):
    from jinja2 import Environment, FileSystemLoader
    from engine import i18n
    from scripts.build_ticker_pages import build_page_context, load_all_aggregates
    debt, cash, cutoff = _control()
    debt.update(status=status, near_share_pct=999, total_display='$0', buckets_reported=99,
                buckets_total=99)
    debt['period']['label'] = 'FORGED PERIOD'
    for row in debt['buckets']:
        row.update(display='$999T', share_pct=999, label_en='FORGED BUCKET')
    debt['buckets'] = debt['buckets'][1:] + debt['buckets'][:1]
    ctx = build_page_context(
        'SYNTHETIC', 'Synthetic issuer', 'Technology',
        {'blob': {'debt_maturity': debt, 'cash_runway': cash}},
        load_all_aggregates(tmp_path), '2025-06-01 10:00 UTC',
    )
    projected = ctx['debt_maturity']
    if status == 'reported':
        assert projected['buckets'][0]['key'] == 'y1'
        assert projected['buckets'][0]['display'] == '$10.0M'
        assert projected['total_display'] == '$10.0M'
        assert projected['near_share_pct'] == 100
        assert projected['buckets_reported'] == projected['buckets_total'] == 6
    else:
        assert projected['period'] is None
        assert all(not row['reported'] for row in projected['buckets'])
    env = Environment(loader=FileSystemLoader('templates'), autoescape=True)
    env.globals['t'] = i18n.t
    html = env.get_template('_debt_maturity.html.j2').render(**ctx)
    for poisoned in ('$999T', '999%', 'FORGED PERIOD', 'FORGED BUCKET', '99/99'):
        assert poisoned not in html
    if status == 'reported':
        assert 'it reported $10.0M due' in html
        assert '6/6' in html
    else:
        assert 'it reported $10.0M due' not in html


@pytest.mark.parametrize('y1', [0, 10_000_000])
def test_debt_display_projection_preserves_zero_and_partial_missingness(y1):
    from scripts.build_ticker_pages import _debt_maturity_for_page
    debt, cash, cutoff = _control()
    debt['buckets'][0]['usd'] = debt['total_reported_usd'] = y1
    debt['buckets'].pop()
    result = assemble_capital_need(debt, cash, as_of=cutoff)
    projected = _debt_maturity_for_page(debt, result)
    assert projected['buckets'][0]['usd'] == y1
    assert projected['buckets'][0]['reported'] is True
    assert projected['buckets'][-1]['reported'] is False
    assert projected['buckets'][-1]['display'] is None
    assert projected['buckets_reported'] == 5
    assert result['derived']['near_term_cash_cover'] is None
