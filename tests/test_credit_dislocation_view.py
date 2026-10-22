"""Reader and actual-template tests for the existing Bonds CDI consumer."""
from copy import deepcopy
from datetime import date
import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
import pytest

from engine.credit_dislocation import AUTHORITY, SCHEMA, _state
from engine.credit_dislocation_view import build_view, compact_context, load_view

ROOT = Path(__file__).resolve().parents[1]
TODAY = date(2026, 10, 16)


def sample():
    return {"schema": SCHEMA, "authority": dict(AUTHORITY), "display_only": True,
            "status": "partial", "as_of": "2026-10-16", "source_as_of": "2026-10-16",
            "pricing_validation": {"status": "passed", "source_binding_verified": True,
                                   "observation_as_of": "2026-10-16"},
            "observation_id": "cdi:synthetic", "issuers": [{
                "issuer": "TEST0", "equity_ticker": "TEST0", "tier": "IG",
                "theme": "hyperscaler_credit", "state": "credit_widening_equity_steadier",
                "change_5": {"value_bp": 25, "reason": None},
                "change_21": {"value_bp": 45, "reason": None},
                "equity_5": {"value_pct": 0, "reason": None},
                "relative_change_5_bp": 20, "peer_change_5_bp": 5,
                "acceleration_bp_per_session": 2, "peer_issuers": ["TEST1", "TEST2", "TEST3"],
                "bonds": [{"identifier": {"value": "037833100", "kind": "cusip", "checksum_valid": True},
                           "name": "Synthetic senior note", "maturity": "2031-10-16",
                           "coupon_pct": 5, "price_clean": 99, "g_spread_bp": 120,
                           "near_par_call_flag": False}]}]}


def render(view):
    env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=True)
    template = env.from_string('{% macro t(en,zh) %}<span class="l-en">{{ en }}</span><span class="l-zh">{{ zh }}</span>{% endmacro %}{% include "_credit_dislocation.html.j2" %}')
    return template.render(cdi=view)


def test_current_view_and_units():
    view = build_view(sample(), as_of=TODAY)
    row = view["issuers"][0]
    assert view["status"] == "partial"
    assert view["paired_count"] == 1
    assert row["change"] == "+25.0 bp"
    assert row["relative"] == "+20.0 bp"
    assert row["equity"] == "+0.0%"
    assert row["bonds"][0]["coupon"] == "5.00%"
    assert row["bonds"][0]["price"] == "99.00"


def test_reader_does_not_trust_old_fresh_status():
    view = build_view(sample(), as_of=date(2026, 11, 2))
    assert view["status"] == "stale"
    assert view["source_as_of"] == "2026-10-16"
    assert view["issuers"][0]["state"] == "historical_only"
    assert "Historical" in view["title_en"]
    assert view["issuers"][0]["relative"] == "+20.0 bp"


@pytest.mark.parametrize("change", [
    {"schema": "not.cdi"}, {"authority": {"rank": False}},
    {"authority": {**AUTHORITY, "escalate": True}},
    {"authority": {key: 0 for key in AUTHORITY}},
    {"display_only": False}, {"source_as_of": "invalid"},
    {"source_as_of": "2026-10-19"}, {"as_of": "2026-10-19"},
    {"status": "unavailable"}, {"issuers": {}},
])
def test_invalid_or_unauthorized_contract_fails_closed(change):
    payload = sample()
    payload.update(change)
    view = build_view(payload, as_of=TODAY)
    assert not view["available"]
    assert not view["issuers"]
    assert not any(view["authority"].values())


def test_missing_source_does_not_look_calm():
    html = render(build_view(None, as_of=TODAY))
    assert "Credit comparison unavailable" in html
    assert "not evidence of low risk" in html
    assert "data-cdi-issuer " not in html
    assert "Credit stress: low" not in html


def test_duplicate_issuer_rejected():
    payload = sample()
    payload["issuers"].append(deepcopy(payload["issuers"][0]))
    assert build_view(payload, as_of=TODAY)["reason"] == "invalid_or_duplicate_issuer"


def test_missing_values_render_dash_not_zero():
    payload = sample()
    row = payload["issuers"][0]
    row["relative_change_5_bp"] = None
    row["equity_5"] = {"value_pct": None, "reason": "equity_unavailable"}
    view = build_view(payload, as_of=TODAY)
    assert view["issuers"][0]["equity"] == "—"
    assert view["issuers"][0]["relative"] == "—"
    assert view["paired_count"] == 0
    assert "Equity observations unavailable" in render(view)


def test_bilingual_actual_template_and_lazy_bond_rows():
    html = render(build_view(sample(), as_of=TODAY))
    for text in ["Stocks and their bonds", "股票与其债券", "Test the countercase", "检验相反解释", "CDS: unavailable", "CDS：暂无数据", "037833100"]:
        assert text in html
    assert "data-cdi-bond-template" in html
    assert "content.cloneNode(true)" in html
    assert "aria-live=\"polite\"" in html
    assert "<caption>" in html
    assert "min-width:680px" in html
    assert "activate" not in html.lower()


def test_untrusted_names_and_attribute_strings_are_escaped():
    payload = sample()
    payload["issuers"][0]["issuer"] = '<script>alert("x")</script>'
    payload["issuers"][0]["bonds"][0]["name"] = '<img src=x onerror=alert(1)>'
    html = render(build_view(payload, as_of=TODAY))
    assert '<script>alert("x")</script>' not in html
    assert '<img src=x' not in html
    assert '&lt;script&gt;' in html
    assert '&lt;img' in html


def test_invalid_identifier_flag_remains_visible():
    payload = sample()
    payload["issuers"][0]["bonds"][0]["identifier"]["checksum_valid"] = False
    assert "Identifier unresolved" in render(build_view(payload, as_of=TODAY))


def test_context_carries_no_new_risk_authority_or_quotes():
    result = compact_context(build_view(sample(), as_of=TODAY))
    assert result["authority"] == AUTHORITY
    assert result["prediction_validated"] is False
    assert result["cds_available"] is False
    assert result["source_as_of"] == "2026-10-16"
    assert "price_clean" not in json.dumps(result)
    assert "bonds.html#credit-dislocation" == result["href"]


def test_missing_context_not_zero_risk():
    result = compact_context(build_view(None, as_of=TODAY))
    assert result["paired_issuer_count"] is None
    assert result["mapped_bond_count"] is None
    assert result["status"] == "unavailable"


def test_loader_missing_json_and_nan(tmp_path):
    assert not load_view(tmp_path, as_of=TODAY)["available"]
    path = tmp_path / "corp_bonds/credit_dislocation.json"
    path.parent.mkdir()
    path.write_text('{"invalid": NaN}')
    assert not load_view(tmp_path, as_of=TODAY)["available"]
    path.write_text(json.dumps(sample()))
    assert load_view(tmp_path, as_of=TODAY)["available"]


def test_file_bound_limits(tmp_path, monkeypatch):
    import engine.credit_dislocation_view as module
    monkeypatch.setattr(module, "MAX_SNAPSHOT_BYTES", 3)
    path = tmp_path / "corp_bonds/credit_dislocation.json"
    path.parent.mkdir()
    path.write_text(json.dumps(sample()))
    assert load_view(tmp_path, as_of=TODAY)["reason"] == "snapshot_exceeds_size_limit"


@pytest.mark.parametrize("relative,absolute,equity", [(20, -5, 0), (-20, 35, 0), (-20, 1, -5)])
def test_relative_resilience_is_not_absolute_recovery(relative, absolute, equity):
    assert _state(relative, equity, stale=False, absolute_change=absolute) == "relative_gap_only"


def test_existing_bonds_template_binds_one_comparison():
    source = (ROOT / "templates/bonds.html.j2").read_text()
    builder = (ROOT / "scripts/build_bonds.py").read_text()
    Environment().parse(source)
    assert source.count('{% include "_credit_dislocation.html.j2" %}') == 1
    assert '{% if cdi is not defined %}' in source
    assert 'cdi=cdi' in builder
    assert 'snap["corporate_credit"]["dislocation"] = compact_context(cdi)' in builder


@pytest.mark.parametrize("pricing", [None, {}, {"status": "passed"},
    {"status": "passed", "source_binding_verified": True, "observation_as_of": "2026-10-15"}])
def test_view_withholds_derived_values_without_exact_pricing_qualification(pricing):
    value = sample()
    value["pricing_validation"] = pricing
    view = build_view(value, as_of=TODAY)
    assert view["pricing_qualified"] is False
    assert view["paired_count"] == 0
    assert view["issuers"][0]["relative"] == "\u2014"
    assert view["issuers"][0]["bonds"][0]["spread"] == "\u2014"
    assert compact_context(view)["pricing_qualified"] is False
    assert 'data-cdi-pricing="unqualified"' in render(view)

def _sample_with_instrument_history():
    from engine.corp_credit import (
        INSTRUMENT_HISTORY_BASIS, INSTRUMENT_HISTORY_POPULATION, INSTRUMENT_HISTORY_SCHEMA,
    )
    from lib.nyse_calendar import session_n_back
    payload = sample()
    payload["pricing_validation"]["instrument_history_verified"] = True
    payload["issuers"][0]["bonds"][0]["instrument_history"] = {
        "schema": INSTRUMENT_HISTORY_SCHEMA, "population": INSTRUMENT_HISTORY_POPULATION,
        "valuation_basis": INSTRUMENT_HISTORY_BASIS,
        "status": "available", "reason": None, "observations": 22,
        "first_seen": "2026-08-03",
        "observed_from": session_n_back(TODAY, 21).isoformat(),
        "observed_through": TODAY.isoformat(), "currency": "USD",
        "cmt_as_of": TODAY.isoformat(), "calculation_convention": "clean",
        "historical_publication_qualified": False,
        "independent_historical_pricing_qualified": False,
        "change_5": {"value_bp": 25.0, "reason": None},
        "change_21": {"value_bp": 105.0, "reason": None},
    }
    return payload


def test_instrument_history_uses_existing_bilingual_inspector():
    view = build_view(_sample_with_instrument_history(), as_of=TODAY)
    bond = view["issuers"][0]["bonds"][0]
    assert bond["history5"] == "+25.0 bp"
    assert bond["history21"] == "+105.0 bp"
    html = render(view)
    for text in ["Instrument history", "债券历史", "5 / 21 sessions", "5 / 21个交易日",
                 "22 observed dates", "USD", "Treasury observation", "美国国债观察日",
                 "historical publication timing", "历史发布时点"]:
        assert text in html
    assert "data-cdi-bond-template" in html
    assert "independently verified historical prices" in html
    assert not any(view["authority"].values())


def test_history_binding_is_separate_from_latest_pricing_and_stays_dated():
    payload = _sample_with_instrument_history()
    stale = build_view(payload, as_of=date(2026, 11, 2))
    assert stale["status"] == "stale"
    assert stale["issuers"][0]["state"] == "historical_only"
    assert stale["issuers"][0]["bonds"][0]["history5"] == "+25.0 bp"
    payload["pricing_validation"].pop("instrument_history_verified")
    view = build_view(payload, as_of=TODAY)
    assert view["pricing_qualified"] is True
    bond = view["issuers"][0]["bonds"][0]
    assert bond["history5"] == "—"
    assert bond["history21"] == "—"
    assert "22 observed dates" in bond["history_coverage_en"]
    assert "matching validation binding" in bond["history_reason_en"]


@pytest.mark.parametrize("change", [
    {"observations": 23}, {"observations": True}, {"observations": 5},
    {"observed_through": "2026-10-19"}, {"first_seen": "2026-10-19"},
    {"cmt_as_of": "2026-10-19"}, {"currency": "EUR"},
    {"historical_publication_qualified": True},
    {"independent_historical_pricing_qualified": True},
])
def test_view_rejects_inconsistent_or_promoted_history(change):
    payload = _sample_with_instrument_history()
    payload["issuers"][0]["bonds"][0]["instrument_history"].update(change)
    bond = build_view(payload, as_of=TODAY)["issuers"][0]["bonds"][0]
    assert bond["history5"] == "—"
    assert bond["history21"] == "—"
    assert bond["history_reason_en"] == "Instrument history is invalid"


def test_unqualified_price_never_leaks_new_history_numbers():
    payload = _sample_with_instrument_history()
    payload["pricing_validation"]["status"] = "unqualified"
    view = build_view(payload, as_of=TODAY)
    bond = view["issuers"][0]["bonds"][0]
    assert bond["history5"] == "—"
    assert bond["history21"] == "—"
    assert "+105.0 bp" not in render(view)
    assert view["paired_count"] == 0
