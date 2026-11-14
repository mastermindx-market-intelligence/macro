"""The retained cycle section must distinguish unavailable from measured OFF."""
from pathlib import Path
import re
import pytest
from jinja2 import ChainableUndefined, Environment

SOURCE = Path(__file__).resolve().parents[1] / "templates/macro_signals.html.j2"

def render(signal, lang):
    source = SOURCE.read_text()
    start = source.index("{% if latest and latest.business_cycle and latest.business_cycle.available %}")
    end_marker = "{% endif %}{# /business_cycle #}"
    section = source[start:source.index(end_marker, start) + len(end_marker)]
    cycle = {"available": True, "phase": {"label": "Unknown"}, "recession_signal": signal,
             "tiers": {}, "measured": {}, "shadow": {}, "coverage": {}}
    return Environment(undefined=ChainableUndefined, autoescape=True).from_string(section).render(
        latest={"business_cycle": cycle}, t=lambda en, zh: zh if lang == "zh" else en,
        td=lambda value: value, help=lambda *args: "")

@pytest.mark.parametrize("lang", ["en", "zh"])
@pytest.mark.parametrize("signal", [None, {}, {"available": False}, {"available": False, "state": "off"},
    {"available": False, "state": "on", "months_active": 3}, {"state": "off"},
    {"available": True, "state": None}, {"available": True, "state": "unknown"}])
def test_unavailable_signal_is_not_a_positive_off_reading(signal, lang):
    html = render(signal, lang)
    expected = "Recession signal unavailable" if lang == "en" else "衰退信号暂无数据"
    assert expected in html
    assert ("No recession signal" if lang == "en" else "无衰退信号") not in html
    assert ("Recession signal ON" if lang == "en" else "衰退信号已触发") not in html
    chip = re.search(r'<div class="chip ([^"]*)"[^>]*>.*?' + expected, html, re.S)
    assert chip and "chip-pos" not in chip[1] and "chip-neg" not in chip[1]

@pytest.mark.parametrize("lang", ["en", "zh"])
@pytest.mark.parametrize("state", ["on", "off"])
@pytest.mark.parametrize("months", [0, 1, 3, 12])
def test_measured_signal_retains_state_and_duration(state, months, lang):
    html = render({"available": True, "state": state, "months_active": months}, lang)
    assert ("Recession signal unavailable" if lang == "en" else "衰退信号暂无数据") not in html
    expected = ("Recession signal ON" if lang == "en" else "衰退信号已触发") if state == "on" else ("No recession signal" if lang == "en" else "无衰退信号")
    assert expected in html
    assert ("chip-neg" if state == "on" else "chip-pos") in html
    if state == "on" and months:
        assert str(months) + (" months" if lang == "en" else "个月") in html
