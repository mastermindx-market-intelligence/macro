"""Intro copy on the China narrative radar page (templates/china_narrative_radar.html.j2).

The member chips are each basket's top members by trailing 63-day return
(engine/china_narrative_radar.py sorts top_members by ret_63d). No field in the payload screens
entries, so the intro names the 63-day ordering instead of promising "clean entries".
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

_ROOT = Path(__file__).resolve().parent.parent
_MEMBERS = [{"ticker": "002639.SZ", "name_zh": "雪人集团", "ret_63d": 33.39},
            {"ticker": "300001.SZ", "name_zh": "特锐德", "ret_63d": 12.0}]
_ICE = {"id": "ice", "name": "Ice & Snow Industry", "name_zh": "冰雪产业",
        "category": "Consumer", "category_zh": "消费", "ret_63d": 41.2, "rank_63d": 1,
        "above_200d": False, "global_ai": None, "top_members": _MEMBERS,
        "state": {"score": 42.0, "label": "Recovering", "label_zh": "修复回升",
                  "dist_200d_pct": -0.0, "drawdown_pct": -10.9}}


def _render() -> str:
    data = {"as_of": "2026-10-16", "provenance": {}, "baskets": [_ICE]}
    env = Environment(loader=FileSystemLoader(str(_ROOT / "templates")), autoescape=True)
    return env.get_template("china_narrative_radar.html.j2").render(
        data=data, data_json=json.dumps(data, ensure_ascii=False), generated_utc="TEST", C={})


def _intro(html: str) -> str:
    return html.split('<div class="intro">', 1)[1].split("</div>", 1)[0]


def test_intro_does_not_promise_clean_entries():
    html = _render()
    assert "clean entries" not in html and "清洁入场点" not in html


def test_intro_states_what_the_chips_actually_are():
    intro = _intro(_render())
    assert "63-day" in intro and "63日" in intro


def test_member_chips_still_link_and_show_return():
    chip = _render().split('<a class="member-chip"', 1)[1].split("</a>", 1)[0]
    assert 'href="china_lookup.html#002639.SZ"' in chip
    assert 'title="002639.SZ · 63d return"' in chip
    assert "+33.4%" in chip


def test_both_language_variants_updated_together():
    intro = _intro(_render())
    en = re.findall(r'<span class="l-en">(.*?)</span>', intro)
    zh = re.findall(r'<span class="l-zh">(.*?)</span>', intro)
    assert len(en) == 1 and len(zh) == 1
    assert "clean" not in en[0] and "63-day" in en[0]
    assert "清洁" not in zh[0] and "63日" in zh[0]
