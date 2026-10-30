"""Cycle-position inputs on the China narrative radar (templates/china_narrative_radar.html.j2).

Each basket's state in site/factordata/china_narrative_radar.json carries drawdown_pct (from the
1y high) and dist_200d_pct (from the 200d SMA), rounded to one decimal by the producer. The page
prints both beside the score chip, so two baskets with the same score stay distinguishable.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

_ROOT = Path(__file__).resolve().parent.parent
_TEMPLATE = _ROOT / "templates" / "china_narrative_radar.html.j2"
_NA = '<span class="chg na">·</span>'


def _basket(bid, name, rank, ret, dd, d200, score=3.0, label="Beaten down", label_zh="深度超跌"):
    return {"id": bid, "name": name, "name_zh": name, "category": "Semiconductors",
            "category_zh": "半导体", "ret_63d": ret, "rank_63d": rank, "above_200d": False,
            "state": {"score": score, "label": label, "label_zh": label_zh,
                      "dist_200d_pct": d200, "drawdown_pct": dd},
            "global_ai": None, "top_members": []}


_OLED = _basket("oled", "OLED Display", 232, -35.0, -53.2, -20.3)
_UM = _basket("um", "Unified Market", 36, -4.05, -17.6, -10.0)


def _render(*baskets) -> str:
    data = {"as_of": "2026-10-16", "provenance": {}, "baskets": list(baskets)}
    env = Environment(loader=FileSystemLoader(str(_ROOT / "templates")), autoescape=True)
    return env.get_template("china_narrative_radar.html.j2").render(
        data=data, data_json=json.dumps(data, ensure_ascii=False), generated_utc="TEST", C={})


def _blocks(html: str, opener: str) -> list[str]:
    return [b.split("</div>", 1)[0] for b in html.split(opener)[1:]]


def _cards(html: str) -> list[str]:
    return _blocks(html, '<div class="bc-meta">')


def _headline(html: str) -> list[str]:
    return _blocks(html, '<div class="hl-meta">')


def test_card_prints_the_committed_drawdown_and_distance():
    html = _render(_OLED)
    for block in (_cards(html)[0], _headline(html)[0]):
        chips = block.split('<span class="state-chip">')[1:]
        assert any("-53.2%" in c for c in chips), block
        assert any("-20.3%" in c for c in chips), block


def test_two_tied_scores_render_different_drawdowns():
    cards = _cards(_render(_OLED, _UM))
    assert all("3/100" in c for c in cards)
    assert "-53.2%" in cards[0] and "-17.6%" in cards[1]
    assert cards[0] != cards[1]


def test_values_keep_one_decimal_and_an_explicit_sign():
    up = _basket("up", "Up Basket", 2, 5.0, -12.0, 1.1, score=60.0, label="Mid-cycle")
    flat = _basket("ice", "Ice & Snow Industry", 1, 41.2, -10.9, -0.0)
    cards = _cards(_render(up, flat))
    assert "-12.0%" in cards[0] and "+1.1%" in cards[0]
    assert "-10.9%" in cards[1] and "-0.0%" in cards[1]


def test_null_cycle_inputs_never_print_none():
    html = _render(_basket("nul", "Null Basket", 3, 1.0, None, None))
    for block in (_cards(html)[0], _headline(html)[0]):
        assert "None" not in block and "nan" not in block.lower()
        assert block.count(_NA) == 2, block
    assert "None" not in html


def test_no_new_css_colour_literal_or_color_mix():
    styles = re.findall(r"<style>(.*?)</style>", _TEMPLATE.read_text(encoding="utf-8"), re.S)
    assert len(styles) == 1
    assert len(re.findall(r"#[0-9a-fA-F]{3,8}\b", styles[0])) == 31
    assert styles[0].count("color-mix(") == 26


def test_both_languages_present_one_visible():
    html = _render(_OLED)
    for block in (_cards(html)[0], _headline(html)[0]):
        for en, zh in (("1y high", "距一年高点"), ("vs 200d", "偏离200日")):
            pair = f'<span class="l-en">{en}</span><span class="l-zh">{zh}</span>'
            assert block.count(pair) == 1, (en, block)
