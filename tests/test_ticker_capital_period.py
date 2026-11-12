"""Exact financial adapter and native bilingual fragment; no full page/provider."""
import ast
from datetime import date
from pathlib import Path
from typing import Any
import pytest
from jinja2 import Environment, StrictUndefined
from lib.numeric import finite

ROOT = Path(__file__).resolve().parents[1]
def adapter(path):
    tree = ast.parse(path.read_text())
    names = {"_build_financials", "_humanize_number", "_clean_str"}
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    assert {n.name for n in nodes} == names
    env = {"Any": Any, "date": date, "finite": finite}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), env)
    return env["_build_financials"]

build = adapter(ROOT/"scripts/build_ticker_pages.py")
template = (ROOT/"templates/ticker.html.j2").read_text()
start = template.index("{% if financials.leverage_rows or financials.cap_rows %}")
end = template.index("  </section>", start)
fragment = Environment(autoescape=True, undefined=StrictUndefined).from_string(template[start:end])

@pytest.mark.parametrize("coverage,expected", [
    ("full", "Buybacks (TTM)"),
    ("annual_fallback", "Buybacks (annual fallback)"),
    ("partial", "Buybacks (partial quarters)"),
    ("missing", "Buybacks (period unqualified)"),
    (None, "Buybacks (period unqualified)"),
    ("bogus", "Buybacks (period unqualified)"),
    ([], "Buybacks (period unqualified)"),
    ({"source": "legacy"}, "Buybacks (period unqualified)"),
])
@pytest.mark.parametrize("amount", [0, 100_000_000])
def test_coverage_and_values(coverage, expected, amount):
    payload = {"capital_allocation":{"repurch_ttm":amount,"repurch_coverage":coverage}}
    result = build(payload)
    assert result["cap_rows"][0]["label_en"].startswith(expected)
    assert result["cap_rows"][0]["value"] == ("$0" if amount == 0 else "$100.0M")
    for lang in [0,1]:
        html = fragment.render(financials=result,t=lambda en,zh: [en,zh][lang])
        assert result["cap_rows"][0][["label_en","label_zh"][lang]] in html

@pytest.mark.parametrize("period", [None,{},{"fy":True,"period_end":"2025-06-30"},
    {"fy":2025,"period_end":"2025-99-99"}, {"fy":2025,"period_end":"<script>"},
    {"fy":"2025","period_end":"2025-06-30"}])
def test_unknown_period_is_explicit(period):
    p={"capital_allocation":{"repurch_ttm":100,"repurch_coverage":"annual_fallback",
        "repurch_annual_period":period,"sbc_ttm":20,"sbc_annual_period":period}}
    rows=build(p)["cap_rows"]
    assert all("period unknown" in r["label_en"] and "期间未知" in r["label_zh"] for r in rows)

def test_distinct_periods_and_unrelated_fields():
    p={"capital_allocation":{"repurch_ttm":100_000_000,"repurch_coverage":"annual_fallback",
       "repurch_annual_period":{"fy":2025,"period_end":"2025-06-30"},
       "sbc_ttm":150_000_000,"sbc_annual_period":{"fy":2026,"period_end":"2026-06-30"},
       "shares_yoy_change_pct":-1,"net_buyback_after_sbc":None}}
    result=build(p)
    assert "FY2025 / 2025-06-30" in result["cap_rows"][0]["label_en"]
    assert "FY2026 / 2026-06-30" in result["cap_rows"][1]["label_en"]
    assert result["cap_rows"][2]["value"] == "-1.0%"
    for lang in [0,1]:
        html=fragment.render(financials=result,t=lambda en,zh: [en,zh][lang])
        assert "FY2025 / 2025-06-30" in html and "FY2026 / 2026-06-30" in html
        assert "TTM" not in html
