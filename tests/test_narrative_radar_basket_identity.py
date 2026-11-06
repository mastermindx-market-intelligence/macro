"""Basket thesis + THS board name on the China narrative radar cards (W30-L36 SPEC 4).

Every committed basket carries thesis / thesis_zh / ths_concept metadata
(data/baskets_china_ths/membership.json) that build_radar() did not read. These
tests pin the pure helper basket_identity() and the card block that prints them.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from engine.narrative_radar_fields import basket_identity

_ROOT = Path(__file__).resolve().parent.parent
_THESIS = "Broad A-share AI complex — models, compute and applications."
_THESIS_ZH = "A股人工智能总线 — 模型、算力与应用。"
_META = {
    "name": "Artificial Intelligence", "name_zh": "人工智能",
    "category": "Technology & AI", "category_zh": "科技与AI",
    "thesis": _THESIS, "thesis_zh": _THESIS_ZH, "ths_concept": "人工智能",
}
_CARD = {
    "id": "ths_ai", **_META,
    "ret_63d": 12.5, "rank_63d": 1, "above_200d": True, "global_ai": None,
    "top_members": [{"ticker": "600519.SH", "name_zh": "贵州茅台", "ret_63d": 8.1}],
    "state": {"score": 42.0, "label": "Recovering", "label_zh": "修复回升",
              "dist_200d_pct": 1.2, "drawdown_pct": -3.4},
}


def _card(basket: dict) -> str:
    data = {"as_of": "2026-10-16", "provenance": {}, "baskets": [dict(basket)]}
    env = Environment(loader=FileSystemLoader(str(_ROOT / "templates")), autoescape=True)
    html = env.get_template("china_narrative_radar.html.j2").render(
        data=data, data_json=json.dumps(data, ensure_ascii=False),
        generated_utc="TEST", C={})
    i = html.index('<div class="bcard"')
    return html[i + len('<div class="bcard"'):html.index('<div class="bc-row1">', i)]


def _en_view(seg: str) -> str:
    return re.sub(r'<span class="l-zh">.*?</span>', '', seg, flags=re.DOTALL)


def _zh_view(seg: str) -> str:
    return re.sub(r'<span class="l-en[^"]*">.*?</span>', '', seg, flags=re.DOTALL)


def _without_identity(basket: dict, none_valued: bool) -> dict:
    out = {k: v for k, v in basket.items() if k not in _META
           or k in ("name", "name_zh", "category", "category_zh")}
    if none_valued:
        for k in ("thesis", "thesis_zh", "ths_concept"):
            out[k] = None
    return out


def _single_fragment(absent: str, present: str) -> str:
    """Prove present == absent with exactly ONE contiguous fragment inserted."""
    i = 0
    while i < len(absent) and i < len(present) and absent[i] == present[i]:
        i += 1
    j = 0
    while (j < len(absent) - i and j < len(present) - i
           and absent[len(absent) - 1 - j] == present[len(present) - 1 - j]):
        j += 1
    assert i + j == len(absent), "present is not absent plus one contiguous fragment"
    frag = present[i:len(present) - j]
    assert frag, "present equals absent: nothing was inserted"
    return frag


def test_basket_identity_reads_the_three_fields():
    got = basket_identity(_META)
    assert got == {"thesis": _THESIS, "thesis_zh": _THESIS_ZH, "ths_concept": "人工智能"}
    assert set(got) == {"thesis", "thesis_zh", "ths_concept"}


def test_basket_identity_degrades_to_none():
    cases = [["600519.SH", "000858.SZ"], None, {},
             {"thesis": "  ", "thesis_zh": "", "ths_concept": " "},
             {"thesis": 5, "thesis_zh": [], "ths_concept": []}]
    for bval in cases:
        got = basket_identity(bval)
        assert set(got) == {"thesis", "thesis_zh", "ths_concept"}
        assert got == {"thesis": None, "thesis_zh": None, "ths_concept": None}, bval


def test_card_prints_thesis_per_language():
    card = _card(_CARD)
    en, zh = _en_view(card), _zh_view(card)
    assert _THESIS in en and _THESIS_ZH not in en
    assert _THESIS_ZH in zh and _THESIS not in zh


def test_missing_thesis_zh_falls_back_to_thesis():
    card = _card({**_CARD, "thesis_zh": None})
    assert _THESIS in _zh_view(card)
    assert "None" not in card


def test_board_chip_is_en_only_when_it_repeats_the_zh_name():
    card = _card(_CARD)
    assert card.count('<span class="l-en state-chip">THS board 人工智能</span>') == 1
    zh = _zh_view(card)
    assert "THS board" not in zh and "同花顺板块" not in zh


def test_board_chip_renders_in_both_languages_when_it_differs():
    card = _card({**_CARD, "ths_concept": "人工智能概念"})
    en, zh = _en_view(card), _zh_view(card)
    assert "THS board" in en and "人工智能概念" in en
    assert "同花顺板块" in zh and "人工智能概念" in zh


def test_absent_identity_adds_nothing():
    for basket in (_without_identity(_CARD, False), _without_identity(_CARD, True)):
        card = _card(basket)
        assert card.count('<div class="bc-cat">') == 1
        assert "None" not in card and "THS board" not in card
    present = _card(_CARD)
    absent = _card(_without_identity(_CARD, False))
    # seed gap: category endif line, blank line, comment line — one newline each
    assert "\n      \n\n      \n" in absent, repr(absent[-60:])
    assert "\n      \n      \n" not in absent  # {%- keeps the gap unstacked
    frag = _single_fragment(absent, present)
    assert frag.startswith('      <div class="bc-cat">'), repr(frag[:40])
    n_absent = len(re.findall(r"\n[ \t]*\n", absent))
    assert n_absent == 4, n_absent   # seed card whitespace-only lines; the block adds none
    assert len(re.findall(r"\n[ \t]*\n", present)) == n_absent


def test_new_template_lines_add_no_style_or_colour_literal():
    lines = (_ROOT / "templates" / "china_narrative_radar.html.j2").read_text().splitlines()
    added = [l for l in lines if any(m in l for m in
                                     ("membership_as_of", "b.thesis", "ths_concept"))]
    assert added, "the new template markers are missing"
    allowed = {"bc-cat", "l-en", "l-zh", "state-chip", "sub"}
    for line in added:
        for banned in ("style=", "<style", "rgb(", "hsl(", "color-mix", "|safe"):
            assert banned not in line, (banned, line)
        assert not re.search(r"#[0-9a-fA-F]{3,6}", line), line
        for classes in re.findall(r'class="([^"]*)"', line):
            assert set(classes.split()) <= allowed, line
