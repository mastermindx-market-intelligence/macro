"""Render the real Cross-Asset hero fragment to guard unavailable gauge claims."""
from pathlib import Path

from jinja2 import Environment
import pytest


def _render_hero(correlation):
    source = (Path(__file__).resolve().parents[1]
              / "templates/crossasset.html.j2").read_text()
    macro = source[:source.index("<!DOCTYPE html>")]
    start = source.index("{% set _hero_tone")
    end = source.index("{# Fragility watch chip")
    template = Environment(autoescape=True).from_string(macro + source[start:end])
    return template.render(
        hero={"tone": "green", "headline_en": "Trend context", "headline_zh": "趋势背景",
              "sub_en": "Trend context", "sub_zh": "趋势背景",
              "stance_en": "Watch", "stance_zh": "留意"},
        breadth=0.5, correlation=correlation, as_of="2026-10-09",
    )


@pytest.mark.parametrize("correlation", [
    None, {}, {"verdict": "unknown"}, {"verdict": "diversified"},
    {"verdict": "converging", "absorption_pctile_5y": None},
    {"verdict": "unknown", "absorption_pctile_5y": 0.88},
])
def test_unavailable_gauge_has_bilingual_disclosure_without_invented_value(correlation):
    html = _render_hero(correlation)
    assert "Correlation data not available this build." in html
    assert "本次构建暂无相关性数据。" in html
    assert "Mostly independent" not in html
    assert "大体独立" not in html
    assert ">0%</text>" not in html
    assert 'aria-label="Correlation absorption gauge"' not in html


@pytest.mark.parametrize("value", [
    False, True, float("nan"), float("inf"), -float("inf"), -0.1, 1.1, "0.25",
])
def test_invalid_percentile_uses_unavailable_state(value):
    html = _render_hero({"verdict": "diversified", "absorption_pctile_5y": value})
    assert "Correlation data not available this build." in html
    assert "本次构建暂无相关性数据。" in html
    assert "Mostly independent" not in html
    assert 'aria-label="Correlation absorption gauge"' not in html


@pytest.mark.parametrize("verdict", ["diversified", "converging", "concentrated"])
@pytest.mark.parametrize("value,percent,en,zh", [
    (0.0, 0, "Mostly independent", "大体独立"),
    (0.25, 25, "Mostly independent", "大体独立"),
    (0.5, 50, "Partial overlap", "部分联动"),
    (0.8, 80, "Markets moving together", "各市场同步运动"),
    (1.0, 100, "Markets moving together", "各市场同步运动"),
])
def test_known_gauge_retains_values_and_bilingual_labels(verdict, value, percent, en, zh):
    html = _render_hero({"verdict": verdict, "absorption_pctile_5y": value})
    assert f">{percent}%</text>" in html
    assert en in html
    assert zh in html
    assert 'aria-label="Correlation absorption gauge"' in html
    assert "Correlation data not available this build." not in html
