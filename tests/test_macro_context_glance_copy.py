"""Macro Context keeps statistical implementation jargon out of the glance path."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "macro_context.html.j2"
SITE = ROOT / "site" / "macro_context.html"


def _src() -> str:
    return TEMPLATE.read_text(encoding="utf-8")


def test_seo_describes_context_without_live_or_internal_copy() -> None:
    src = _src()
    m = re.search(r"seo_desc = '([^']+)'", src)
    assert m, "seo_desc missing"
    desc = m.group(1)
    assert "Live macro label board" not in desc
    assert "display-only context" not in desc
    assert "Macro context board" in desc


def test_hero_confidence_is_named_as_regime_confidence() -> None:
    src = _src()
    assert "% confidence</span>" not in src
    assert "regime confidence" in src
    assert "周期置信" in src


def test_primary_context_badge_is_short_plain_language() -> None:
    src = _src()
    assert "Display-only context — not signals" not in src
    assert "Context only — not a trade signal" in src
    assert "仅作背景 — 非交易信号" in src


def test_regime_model_help_avoids_implementation_jargon() -> None:
    src = _src()
    m = re.search(r'data-tip-en="([^"]+)"\s+data-tip-zh="([^"]+)"[^>]*>\s*<span class="kpi-label">\{\{ t\(\'Regime model\'', src)
    assert m, "regime-model tooltip missing"
    en, zh = m.groups()
    assert len(en.split()) <= 55
    for banned in ("hidden-Markov", "posterior", "P(quad)", "Hazard rate", "causal refit"):
        assert banned not in en
    assert "statistical regime model" in en
    assert "context, not a scored signal" in en
    assert "统计周期模型" in zh


def test_contradiction_explainer_is_plain_and_short() -> None:
    src = _src()
    assert "Contradiction pairs are display-only" not in src
    assert "graded signal authority" not in src
    assert "Contradictions are context only" in src
    assert "do not change scores or rankings" in src


def test_footer_disclaimer_is_concise_product_guidance() -> None:
    src = _src()
    assert "Display-only — labels, not signals." not in src
    assert "pre-registration gate" not in src
    assert "authority to modify any position or scoring surface" not in src
    assert "Context labels, not trade signals." in src
    assert "have not been validated as trade signals" in src
    assert "Macro Weather Station · market context only" in src


def test_committed_page_matches_plain_language_contract() -> None:
    html = SITE.read_text(encoding="utf-8")
    for required in (
        "Macro context board",
        "regime confidence",
        "Context only — not a trade signal",
        "statistical regime model",
        "Contradictions are context only",
        "Context labels, not trade signals.",
        "Macro Weather Station · market context only",
    ):
        assert required in html
    for banned in (
        "Live macro label board",
        "Display-only context — not signals",
        "hidden-Markov",
        "P(quad)",
        "Hazard rate",
        "causal refit",
        "Contradiction pairs are display-only",
        "pre-registration gate",
    ):
        assert banned not in html
