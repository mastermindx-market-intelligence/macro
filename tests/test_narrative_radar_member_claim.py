"""Intro copy on the China narrative radar page (templates/china_narrative_radar.html.j2).

The member chips are each basket's top members by trailing 63-day return
(engine/china_narrative_radar.py sorts top_members by ret_63d). No field in the payload screens
entries, so the intro names the 63-day ordering instead of promising "clean entries".
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader

_ROOT = Path(__file__).resolve().parent.parent
_MEMBERS = [{"ticker": "002639.SZ", "name_zh": "雪人集团", "ret_63d": 33.39},
            {"ticker": "300001.SZ", "name_zh": "特锐德", "ret_63d": 12.0}]
_ICE = {"id": "ice", "name": "Ice & Snow Industry", "name_zh": "冰雪产业",
        "category": "Consumer", "category_zh": "消费", "ret_63d": 41.2, "rank_63d": 1,
        "above_200d": False, "global_ai": None, "top_members": _MEMBERS,
        "state": {"score": 42.0, "label": "Recovering", "label_zh": "修复回升",
                  "dist_200d_pct": -0.0, "drawdown_pct": -10.9}}
_CPO = {**_ICE, "id": "ths_cpo",
        "global_ai": {"mom_4w_pct": 3.1, "direction": "up", "validated_tag": "validated",
                      "as_of": "2026-10-16"}}


def _render(baskets=None) -> str:
    data = {"as_of": "2026-10-16", "provenance": {},
            "baskets": [_ICE] if baskets is None else baskets}
    env = Environment(loader=FileSystemLoader(str(_ROOT / "templates")), autoescape=True)
    return env.get_template("china_narrative_radar.html.j2").render(
        data=data, data_json=json.dumps(data, ensure_ascii=False), generated_utc="TEST", C={})


def _reader_text(html: str) -> str:
    """Visible copy: drop style and script blocks and class attributes; keep title."""
    text = re.sub(r"<style\b[^>]*>.*?</style>", "", html, flags=re.I | re.S)
    text = re.sub(r"<script\b[^>]*>.*?</script>", "", text, flags=re.I | re.S)
    return re.sub(r'\s*class="[^"]*"', "", text)


def _banner_halves(html: str) -> tuple[str, str]:
    banner = html.split('<div class="honesty-banner">', 1)[1].split("</div>", 1)[0]
    en = re.findall(r'<span class="l-en">(.*?)</span>', banner, flags=re.S)
    zh = re.findall(r'<span class="l-zh">(.*?)</span>', banner, flags=re.S)
    return next(s for s in en if "t=3.27" in s), next(s for s in zh if "t=3.27" in s)


def _ths_cpo_study() -> dict[str, dict[str, str]]:
    """ths_cpo rows of reports/china-global-theme.md, keyed by era. mv_semis_t is the controls t."""
    text = (_ROOT / "reports" / "china-global-theme.md").read_text(encoding="utf-8")
    header = None
    rows: dict[str, dict[str, str]] = {}
    for line in text.splitlines():
        parts = line.split()
        if parts[:2] == ["basket", "era"]:
            header = parts
            continue
        if header and parts and parts[0] == "ths_cpo":
            rec = dict(zip(header, parts))
            rows[rec["era"]] = rec
    return rows


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


def test_reader_text_drops_validated_words_but_keeps_the_class():
    html = _render([_CPO])
    text = _reader_text(html)
    assert "validated" not in text.lower()
    assert "已验证" not in text and "经验证" not in text
    assert 'class="ai-tag validated"' in html


def test_confirmed_chip_replaces_the_validated_label():
    chip = _render([_CPO]).split('<div class="ai-chip">', 1)[1].split("</div>", 1)[0]
    assert "confirmed" in chip and "已确认" in chip


def test_arrow_title_prints_confirmed_for_the_validated_tag():
    html = _render([_CPO])
    title = re.search(r'<span class="ai-arrow" title="([^"]*)"', html)
    assert title is not None
    assert title.group(1).rsplit(" · ", 1)[-1] == "confirmed"


@pytest.mark.parametrize("tag", ["partial", "2024+-only", "weak"])
def test_other_tags_print_unchanged_and_skip_the_confirmed_chip(tag):
    basket = {**_CPO, "global_ai": {**_CPO["global_ai"], "validated_tag": tag}}
    html = _render([basket])
    title = re.search(r'<span class="ai-arrow" title="([^"]*)"', html)
    assert title is not None
    assert title.group(1).rsplit(" · ", 1)[-1] == tag
    chip = html.split('<div class="ai-chip">', 1)[1].split("</div>", 1)[0]
    assert "confirmed" not in chip and "已确认" not in chip


def test_disclaimer_names_both_windows_in_each_language():
    en, zh = _banner_halves(_render([_CPO]))
    for token in ("t=3.27", "241", "t=1.36", "124"):
        assert token in en, token
        assert token in zh, token
    for banned in ("#773", "#754"):
        assert banned not in en and banned not in zh


def test_chip_title_names_each_window_of_the_study():
    html = _render([_CPO])
    title = re.search(r'class="ai-tag validated" title="([^"]*)"', html)
    assert title is not None
    for phrase in ("t=3.27 over the full backtest", "2.27 with market controls",
                   "t=3.03 before 2024", "t=1.36 from 2024"):
        assert phrase in title.group(1), phrase


def test_study_numbers_appear_on_the_chip_or_the_disclaimer():
    rows = _ths_cpo_study()
    assert rows["full"]["n"] == "241"
    assert rows["full"]["uni_t"] == "3.27"
    assert rows["full"]["mv_semis_t"] == "2.27"
    assert rows["pre-2024"]["uni_t"] == "3.03"
    assert rows["2024+"]["n"] == "124"
    assert rows["2024+"]["uni_t"] == "1.36"
    html = _render([_CPO])
    title = re.search(r'class="ai-tag validated" title="([^"]*)"', html)
    assert title is not None
    banner = html.split('<div class="honesty-banner">', 1)[1].split("</div>", 1)[0]
    surface = title.group(1) + "\n" + banner
    for token in (rows["full"]["n"], rows["full"]["uni_t"], rows["full"]["mv_semis_t"],
                  rows["pre-2024"]["uni_t"], rows["2024+"]["n"], rows["2024+"]["uni_t"]):
        assert token in surface, token
