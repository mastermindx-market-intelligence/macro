"""Market Structure keeps model implementation jargon out of the primary reading path."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "market_structure.html.j2"
SITE = ROOT / "site" / "market_structure.html"


def _src() -> str:
    return TEMPLATE.read_text(encoding="utf-8")


def test_page_uses_systematic_fund_language() -> None:
    src = _src()
    assert "Machine money flows" not in src
    assert "machine money" not in src.lower()
    assert "Machine-money" not in src
    assert "Systematic fund flows" in src
    assert "Systematic-flow agreement" in src
    assert "systematic funds" in src.lower()


def test_header_and_seo_use_reader_language() -> None:
    src = _src()
    assert "Machine Flows" not in src
    assert "machine money flows" not in src.lower()
    assert "Dealer hedging · systematic fund flows · stock-picking conditions · options-implied weekly range" in src
    assert "Systematic Fund Flows" in src


def test_systematic_help_is_plain_and_methodology_is_demoted() -> None:
    src = _src()
    start = src.index("<h2>{{ t('Systematic fund flows'")
    end = src.index("{% if sys is not none %}", start)
    block = src[start:end]
    m = re.search(r'<span class="l-en"><b>What these are</b><br>(.*?)</span>', block, re.S)
    assert m, "systematic-fund help text missing"
    text = re.sub(r'<[^>]+>', ' ', m.group(1))
    assert len(text.split()) <= 75
    for banned in ("min(1", "z-score", "20/50/100/200d", "full backcast", "AUM"):
        assert banned not in text
    assert "model estimates" in text.lower()
    assert "not observed fund positions" in text.lower()


def test_systematic_stances_are_plain_language() -> None:
    src = _src()
    for required in (
        "Systematic funds: aligned",
        "systematic buying is already in the price",
        "systematic funds are stepping back",
        "systematic flows aren't pushing either way",
    ):
        assert required in src
    for banned in (
        "Machine money:",
        "machine buying is already in the price",
        "machine money is stepping back",
        "machine flows aren't pushing either way",
    ):
        assert banned not in src


def test_weekly_range_kpis_use_plain_labels() -> None:
    src = _src()
    kpi = src[src.index('<div class="kpi-row" style="margin-top:8px">', src.index("PANEL 6")):]
    assert "typical range (about 68% of weeks)" in kpi
    assert "wide range (about 95% of weeks)" in kpi
    assert "typical range (±1σ" not in kpi
    assert "wide range (±2σ" not in kpi


def test_footer_is_short_model_guidance() -> None:
    src = _src()
    footer = src[src.index("{# ── Footer ── #}"):src.index("</div>{# /wrap #}")]
    assert "Market context, not buy or sell signals." in footer
    assert "Systematic-fund figures are model estimates, not observed positions." in footer
    assert "Read them as direction and scale" in footer
    for banned in ("stylised $300B pool", "10% volatility target", "Machine-flow figures"):
        assert banned not in footer


def test_committed_page_matches_market_structure_copy_contract() -> None:
    html = SITE.read_text(encoding="utf-8")
    for required in (
        "Systematic fund flows",
        "typical range (about 68% of weeks)",
        "wide range (about 95% of weeks)",
        "Market context, not buy or sell signals.",
    ):
        assert required in html
    for banned in (
        "Machine money flows",
        "Machine money:",
        "Machine-money flows aren't on this page yet.",
        "machine buying is already in the price",
    ):
        assert banned not in html


def test_chinese_fallback_copy_uses_the_same_fund_name() -> None:
    # Covers dormant missing-data and funds-cutting branches, not just today's snapshot.
    for path in (TEMPLATE, SITE):
        assert "机器资金" not in path.read_text(encoding="utf-8")


def test_weekly_model_ranges_retain_the_approximation_qualifier() -> None:
    for path in (TEMPLATE, SITE):
        html = path.read_text(encoding="utf-8")
        assert "typical range (about 68% of weeks)" in html
        assert "wide range (about 95% of weeks)" in html
