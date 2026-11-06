"""Actual existing Radar partial consumer; no standalone replacement dashboard."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader, select_autoescape

from tests.test_risk_envelope_multi_asset import _context, _envelope

ROOT = Path(__file__).resolve().parents[1]
ENV = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=select_autoescape(default=True))


def render(context=None, *, full=True):
    name = "_risk_envelope_band.html.j2" if full else "risk_envelope/_multi_asset_context.html.j2"
    return ENV.get_template(name).render(risk_envelope=_envelope(context) if full else None, multi_asset_context=context)


def test_existing_radar_contains_context_once():
    html = render(_context()); soup = BeautifulSoup(html, "html.parser")
    assert len(soup.select("#gde-multi-asset-context")) == 1
    assert len(soup.select("#gde-multi-asset-context tbody tr")) == 11
    assert soup.select_one("#gde-multi-asset-title").get_text(strip=True)


def test_absent_context_preserves_old_consumer():
    assert "gde-multi-asset-context" not in render()


def test_absent_relative_gain_not_labeled_profit():
    soup = BeautifulSoup(render(_context()), "html.parser")
    row = soup.select_one('[data-multi-asset-instrument="EEM"]')
    assert "-1.00%" in row.get_text()
    assert "+3.12%" in row.get_text()
    assert "Lost less" in row.get_text()
    assert "not a positive gain" in row.get_text()


def test_benchmark_is_not_preferred_holding():
    assert "not a preferred holding" in render(_context())


def test_wrapper_and_cash_limits_visible():
    html = render(_context())
    for text in ["not cash", "not spot oil", "Cash is not represented by a bond fund", "not synchronized native foreign markets"]:
        assert text in html


def test_capture_is_not_original_publication():
    assert "not when the provider first published" in render(_context())


def test_stale_warning_is_visible():
    html = render(_context(expected_session="2026-11-05"))
    assert "Older snapshot" in html
    assert "do not describe the current market" in html


def test_en_zh_both_available():
    soup = BeautifulSoup(render(_context()), "html.parser")
    section = soup.select_one("#gde-multi-asset-context")
    assert len(section.select(".l-en")) > 20 and len(section.select(".l-zh")) > 20


def test_native_details_and_table_accessibility():
    soup = BeautifulSoup(render(_context()), "html.parser")
    section = soup.select_one("#gde-multi-asset-context")
    assert section.get("aria-labelledby") == "gde-multi-asset-title"
    assert section.select_one("details > summary")
    table = section.select_one('table[role="table"]')
    assert table.get("aria-describedby") == "gde-multi-asset-limits"
    assert len(table.select('th[scope="col"]')) == 4
    assert all(cell.has_attr("data-label-en") and cell.has_attr("data-label-zh") for cell in table.select("td"))


def test_template_output_escapes_untrusted_labels():
    context = _context(); context["rows"][0]["label_en"] = '<script>alert("x")</script>'
    html = render(context, full=False)
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


@pytest.mark.parametrize("field,value", [("can_trade", True), ("can_size", 0), ("can_rank", None)])
def test_invalid_authority_never_renders_values(field, value):
    context = _context(); context["authority"][field] = value
    html = render(context, full=False)
    assert "does not meet the descriptive-only contract" in html
    assert "-1.00%" not in html


def test_bad_schema_withholds():
    context = _context(); context["schema"] = "other"
    assert "Cross-asset evidence is unavailable" in render(context, full=False)


def test_json_schema_accepts_optional_context():
    import jsonschema
    schema = json.loads((ROOT / "contracts/risk_envelope.schema.json").read_text())
    jsonschema.validate(_envelope(_context()), schema)


def test_json_schema_rejects_capital_authority():
    import jsonschema
    schema = json.loads((ROOT / "contracts/risk_envelope.schema.json").read_text())
    envelope = _envelope(_context()); envelope["multi_asset_context"]["authority"]["can_size"] = True
    with pytest.raises(jsonschema.ValidationError): jsonschema.validate(envelope, schema)


def test_render_does_not_mutate_evidence():
    context = _context(); before = copy.deepcopy(context)
    render(context); assert context == before


@pytest.mark.parametrize("mutation", [
    "unknown_context_field", "unknown_row_field", "string_return", "missing_source_digest",
    "wrong_return_basis", "wrong_currency", "missing_limitations", "numeric_capture",
    "negative_coverage", "unknown_window_field",
])
def test_shared_schema_rejects_unsafe_or_incomplete_context(mutation):
    import jsonschema
    schema = json.loads((ROOT / "contracts/risk_envelope.schema.json").read_text())
    envelope = _envelope(_context())
    context = envelope["multi_asset_context"]
    row = context["rows"][0]
    if mutation == "unknown_context_field":
        context["allocation_weight"] = 0.8
    elif mutation == "unknown_row_field":
        row["expected_return"] = 0.2
    elif mutation == "string_return":
        row["absolute_return"] = "0.2"
    elif mutation == "missing_source_digest":
        del row["source_digest"]
    elif mutation == "wrong_return_basis":
        row["return_basis"] = "price_return"
    elif mutation == "wrong_currency":
        row["currency"] = "HKD"
    elif mutation == "missing_limitations":
        del context["limitations"]
    elif mutation == "numeric_capture":
        context["captured_at"] = 42
    elif mutation == "negative_coverage":
        context["coverage"]["observed"] = -1
    elif mutation == "unknown_window_field":
        context["window"]["quote_timestamp"] = "2026-11-05T15:00:00Z"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(envelope, schema)


def test_disclosure_reuses_existing_spacing():
    soup = BeautifulSoup(render(_context()), "html.parser")
    assert soup.select_one("#gde-multi-asset-context > details.gde-disc > summary")
