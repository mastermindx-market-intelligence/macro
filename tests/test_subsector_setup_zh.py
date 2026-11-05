"""Subsector detail ZH "setup" wording (#7646 Cycles wave, lane A2_D36).

On a no-sizing surface the Chinese for a chart setup is 形态, the deck's own
rendering (copy_deck.json brief.lane_sub_get_ready), never 配置, which reads
as an allocation or position configuration.

Lane L6.5h (SIC-D35/D38) adds the dossier colour rules: an entry state is never
carried by a market-direction colour (red/green flip under ZH), and no container
takes an edge stripe. A setup tier is a grade, not a health or wayfinding
state: T1-T4 step down in ink weight and fill, never in hue, so a green T2 can
not read as a falling price on a ZH page. The node render of the localized engine words lives in
tests/test_product_chrome.py, next to the page's existing render harness.

Lane L6.5q (O-INT iii) applies the same wording rule to the fund dossier
(templates/sector.html.j2, sectors/<F>.html). Its 3-day entry heading is 入场形态,
never 入场配置. A measured base rate is 基准率, the deck's word
(components.prior_gloss), never 胜率: the deck reserves 胜率 for "not a win rate"
(components.grader_caption).

Pure text checks; no node.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SUBSECTOR = ROOT / "templates" / "subsector_detail.html.j2"
DECK = ROOT / "design_refs" / "sector-paper-20261021" / "copy_deck.json"

REQUIRED = ("T1 · 已确认形态", "T2 · 早期形态", "L('Own setup','自身形态')")
FORBIDDEN = "配置"


def setup_zh_problems(text: str) -> list[str]:
    """Every reason the text fails the setup wording rule; empty when it passes."""
    problems = [f"missing {s!r}" for s in REQUIRED if s not in text]
    if FORBIDDEN in text:
        problems.append(f"{FORBIDDEN!r} appears {text.count(FORBIDDEN)} time(s)")
    return problems


def test_subsector_template_uses_the_deck_word_for_setup():
    text = SUBSECTOR.read_text(encoding="utf-8")
    for s in REQUIRED:
        assert s in text, s


def test_subsector_template_has_no_allocation_word():
    assert FORBIDDEN not in SUBSECTOR.read_text(encoding="utf-8")


def test_deck_renders_setup_as_xingtai():
    deck = json.loads(DECK.read_text(encoding="utf-8"))
    row = deck["brief"]["lane_sub_get_ready"]
    assert row["en"].startswith("Setup")
    assert "形态" in row["zh"]
    assert FORBIDDEN not in row["zh"]


def test_subsector_template_passes_the_rule():
    assert setup_zh_problems(SUBSECTOR.read_text(encoding="utf-8")) == []


@pytest.mark.parametrize(
    "old",
    [
        "const zh = {T1:'T1 · 已确认配置',T2:'T2 · 早期配置',T3:'T3 · 形成中'};",
        "L('Own setup','自身配置')",
    ],
)
def test_the_rule_rejects_the_base_strings(old):
    text = SUBSECTOR.read_text(encoding="utf-8") + "\n" + old
    assert any(FORBIDDEN in p for p in setup_zh_problems(text))
    assert setup_zh_problems(old)


@pytest.mark.parametrize(
    "banned",
    [
        "border-left",
        "color-mix",
        ".tier.T1{background:var(--up)",
        ".tier.T2{background:var(--ok)",
        ".tier.T3{background:var(--info)",
        ".member-card.buyable{border-color:var(--up)",
        "esc(e.reason)",
        "esc(m.stock_state",
    ],
)
def test_subsector_template_keeps_state_off_direction_colour(banned):
    assert banned not in SUBSECTOR.read_text(encoding="utf-8")


def test_subsector_template_names_engine_words_in_chinese():
    text = SUBSECTOR.read_text(encoding="utf-8")
    for zh in ("动量偏多", "动量偏空", "动量分歧", "已回落", "等待确认", "入场信号开启"):
        assert zh in text, zh


def test_subsector_chart_legend_wraps_on_phones():
    """SIC-D37: on a phone the shared chart legend (one nowrap line, ~291px)
    ran under the price scale and the fullscreen button. The page wraps it
    to 29ch below 560px; the desktop legend keeps its single line. The space
    in `{ #chart-host` stops Jinja reading `{#` as a comment opener."""
    text = SUBSECTOR.read_text(encoding="utf-8")
    assert "@media (max-width:560px){ #chart-host .bchart-legend{white-space:normal;max-width:29ch" in text
    assert "#chart-host .bchart-legend span{white-space:nowrap}" in text
    assert "{#chart-host" not in text


DOSSIER = ROOT / "templates" / "sector.html.j2"
DOSSIER_REQUIRED = ("'入场形态 — 3 日视角'", "实测基准率（见底部表格）", "以下即为这些基准率。")
DOSSIER_FORBIDDEN = ("配置", "胜率", "基础概率")


def dossier_zh_problems(text: str) -> list[str]:
    """Every reason the dossier text fails the wording rule; empty when it passes."""
    problems = [f"missing {s!r}" for s in DOSSIER_REQUIRED if s not in text]
    problems += [f"{w!r} appears {text.count(w)} time(s)" for w in DOSSIER_FORBIDDEN if w in text]
    return problems


def test_fund_dossier_passes_the_wording_rule():
    assert dossier_zh_problems(DOSSIER.read_text(encoding="utf-8")) == []


def test_deck_names_base_rate_jizhunlv_and_reserves_shenglv():
    deck = json.loads(DECK.read_text(encoding="utf-8"))
    assert "基准率" in deck["components"]["prior_gloss"]["zh"]
    assert "并非胜率" in deck["components"]["grader_caption"]["zh"]


@pytest.mark.parametrize(
    "old",
    [
        "{{ t('Entry setup — the 3-day view', '入场配置 — 3 日视角') }}",
        "和主看板「板块买卖配置」用的是同一套买卖读数",
        "各状态附有实测基准胜率（见底部表格）",
        "以下即为这些基准胜率。",
        "基础概率是这个状态在随后 63 天里对 SPY 的实际表现。",
    ],
)
def test_the_dossier_rule_rejects_the_base_strings(old):
    text = DOSSIER.read_text(encoding="utf-8") + "\n" + old
    assert dossier_zh_problems(text)
