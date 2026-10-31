"""The real shell and paid table retain their card's supplied evidence and terms."""
from copy import deepcopy
import json
import re

from bs4 import BeautifulSoup
import pytest

from scripts.build_site import _split_us_board, _write_us_payload
from tests.test_dashboard_template_render import _base_vm, _env
from tests.test_prophet_opportunity_integration import _source


def _row(ticker):
    return _source(
        ticker=ticker, spark_as_of="2026-09-22", ext_z=2.5,
        alpha_entry="extended", antichase_shadow_blocked=True,
        earnings_soon={"days_to": 2, "chip_en": "Earnings in 2d", "chip_zh": "财报还有2天"},
        sector_stance="Cautious", sector_stance_zh="谨慎",
        hold={"state": "broken", "invalidation": 30},
        options_flags=[["Options context", "期权背景"]],
        conviction={"cautions": ["accounting watch", "<b>Known risk</b>"],
                    "cautions_zh": ["会计关注", "<b>已知风险</b>"]},
        prophet={"version": "us_prophet_v3", "score": 0,
                 "fusion": {"definition": "us_prophet_v3",
                            "families_active": ["F1_TECHNICAL_CONFLUENCE"],
                            "family_contribution": {"F1_TECHNICAL_CONFLUENCE": 0},
                            "families_abstaining": ["F7_QUALITY_FUNDAMENTAL"]}})


def _render(tmp_path, *, unknown_relation=False):
    rows = [_row("PVTABLEPUBLIC"), _row("PVTABLELOCKED")]
    before = deepcopy(rows)
    original = {"as_of": "2026-09-23", "buy": rows, "eligible": 2}
    shell, gate, locked = _split_us_board(original, 1, gated=True)
    records = {r["ticker"]: [{"id": r["ticker"] + "-MODEL", "asset": r["ticker"],
                             "lifecycle_state": "entered", "formation_date": "2026-08-10"}]
               for r in rows}
    state = "unknown" if unknown_relation else "available"
    vm = _base_vm()
    vm.update(us_standouts=shell, gate=gate, plan_rel={"state": state, "plans": []},
              plan_rel_by_ticker=records)
    env = _env()
    env.autoescape = True
    html = env.get_template("dashboard.html.j2").render(**vm, mode="stocks")
    island = re.search(r'<script type="application/json" id="us-stocktable-data">(.*?)</script>', html, re.S)
    _write_us_payload(env, tmp_path, gate, locked_rows=locked, us_standouts=original,
                      top_setups=None, built="test-only", plan_relations=(state, records))
    paid = json.loads((tmp_path / "premiumdata/us_stocks.json").read_text())
    assert rows == before
    return html, json.loads(island.group(1))["rows"], paid


@pytest.mark.parametrize("surface", ["shell", "paid"])
def test_table_preserves_same_entitled_card_detail(tmp_path, surface):
    html, shell_rows, paid = _render(tmp_path)
    rows = shell_rows if surface == "shell" else paid["rows"]
    assert [r["ticker"] for r in rows] == (["PVTABLEPUBLIC"] if surface == "shell" else ["PVTABLELOCKED"])
    assert "PVTABLELOCKED" not in html  # the richer table must not widen the public split
    fragment = html if surface == "shell" else paid["cards_html"]
    card = BeautifulSoup(fragment, "html.parser").select_one(
        '.po-card[data-ticker="' + rows[0]["ticker"] + '"] .pv-setup-body')
    inert = BeautifulSoup(rows[0]["setup_detail"], "html.parser").select_one("template .pv-setup-body")
    # Reparse the body outside <template>, just as the dialog moves it into the
    # active document. BeautifulSoup intentionally omits inert TemplateStrings.
    table = BeautifulSoup(str(inert), "html.parser").select_one(".pv-setup-body")
    for selector in (".pvs-company", ".pvs-snapshot", ".pvs-chart-clock",
                     ".pvs-opportunity-cautions", ".pvs-evidence-profile",
                     ".pvs-plan-relation", ".pvs-levels", ".pvs-assessment-clock"):
        assert table.select_one(selector), selector + " missing from table"
        assert str(table.select_one(selector)) == str(card.select_one(selector)), selector
    assert table.select_one('[data-evidence-family] dd').get_text() == "0.0"
    assert len(table.select(".pvs-opportunity-cautions li")) == 8
    assert "<b>Known risk</b>" in table.get_text()
    assert not table.select("b,script,iframe")
    assert table.select_one("[data-plan-exact]")["data-plan-exact"] == "unavailable"


@pytest.mark.parametrize("surface", ["shell", "paid"])
def test_unavailable_plan_read_does_not_gain_a_relation_from_ticker_map(tmp_path, surface):
    _, shell_rows, paid = _render(tmp_path, unknown_relation=True)
    rows = shell_rows if surface == "shell" else paid["rows"]
    table = BeautifulSoup(rows[0]["setup_detail"], "html.parser")
    assert table.select_one('[data-plan-relation="unknown"]')
    assert not table.select(".pvs-plan-link")
