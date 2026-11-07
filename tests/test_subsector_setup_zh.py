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

Lane L6.8 (O-INT vi, state matrix dossier/error R3A-74) gives the subsector chart
a failure state of its own. A mount that throws, or a chart script that never
arrived, puts an assertive bilingual notice with a Retry button in the chart's
420px frame; the rest of the page stays. The notice is a neutral surface: no
direction or health colour, no edge stripe. Its node behaviour lives in
tests/test_product_chrome.py.

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


CHART_FAILURE_REQUIRED = (
    'role="alert"',
    "L('Chart unavailable right now', '图表暂不可用')",
    "本页的概况、成分与证据不受影响。",
    "L('Retry', '重试')",
    "s.src = '../chart.js';",
    "s.onerror = () => chartUnavailable(true);",
)
CHART_FAILURE_BANNED_INK = ("var(--up)", "var(--down)", "var(--ok)", "var(--warn)", "var(--act)", "border-left", "color-mix")


def test_subsector_chart_failure_is_wired_to_both_paths():
    """The cited mount line keeps its place; a throw and a missing script both
    reach the notice."""
    text = SUBSECTOR.read_text(encoding="utf-8")
    lines = text.splitlines()
    assert "console.error('chart mount failed', err); chartUnavailable(false);" in lines[213]
    assert lines[214].strip() == "} else if (CHART_KEY) { chartUnavailable(false); }"
    for s in CHART_FAILURE_REQUIRED:
        assert s in text, s


def test_subsector_chart_failure_notice_is_neutral():
    text = SUBSECTOR.read_text(encoding="utf-8")
    start = text.index(".id-chart-err{")
    css = text[start:text.index("\n", start)]  # the notice rules end its line
    for banned in CHART_FAILURE_BANNED_INK:
        assert banned not in css, banned


DOSSIER_CHART_FAILURE_REQUIRED = (
    '<div class="tv-err" role="alert">',
    '<span class="l-en">Chart unavailable right now</span><span class="l-zh">图表暂不可用</span>',
    '<script src="https://s3.tradingview.com/tv.js" onerror="tvUnavailable()"></script>',
    "<script>if (!window.TradingView) { tvUnavailable(); } else new TradingView.widget(",
)


def test_fund_dossier_chart_failure_is_a_typed_notice():
    """SIC GAP-B #6: the fund dossier's chart is a third-party embed. When tv.js
    never arrives (blocked, offline) the 440px frame was an empty box with no
    reason. A failed load and a missing global both now reach one bilingual
    notice; the notice is defined before the script that can fire it."""
    text = DOSSIER.read_text(encoding="utf-8")
    for s in DOSSIER_CHART_FAILURE_REQUIRED:
        assert s in text, s
    assert text.index("function tvUnavailable()") < text.index('onerror="tvUnavailable()"')


def test_fund_dossier_chart_failure_notice_is_neutral():
    text = DOSSIER.read_text(encoding="utf-8")
    start = text.index("  .tv-err {")
    css = text[start:text.index("  .tv-err .s", start)]
    for banned in CHART_FAILURE_BANNED_INK:
        assert banned not in css, banned


def test_fund_dossier_header_names_its_data_date():
    """SIC GAP-B #7: the dossier showed only the signal's trigger day, so a
    stale page read as a live one. The header now carries the last close the
    page was built from; the producer sets it beside the ETF close series."""
    text = DOSSIER.read_text(encoding="utf-8")
    assert "{% if s.as_of %}<span class=\"asof muted\">{{ t('Data as of','数据截至') }} {{ s.as_of }}</span>{% endif %}" in text
    head = text[text.index('<div class="topline">'):text.index('<span style="flex:1"></span>')]
    assert 'class="asof' in head
    src = (ROOT / "scripts" / "build_site.py").read_text(encoding="utf-8")  # ci-trigger-closure: data — parse-only builder source, declared in sector-cycles-wave paths; imports not followed
    assert '        ec = etf["close"].dropna()\n        s["as_of"] = str(ec.index.max().date())' in src


def test_fund_dossier_stoch_label_follows_its_value():
    """SIC GAP-B #20: the Stoch tile read 超卖 (Washout) at 49. The label now
    follows the engine's daily StochRSI bands (engine/cycles.py: <20 oversold,
    >80 overbought); a missing value carries no label."""
    text = DOSSIER.read_text(encoding="utf-8")
    assert "<span class=\"sc-s\">{{ t('Washout','超卖') }}</span>" not in text
    assert "{% if sv is not none %}{{ t('Washout','超卖') if sv < 20 else (t('high','偏高') if sv > 80 else t('mid','中性')) }}{% endif %}" in text


def test_fund_dossier_failed_cycle_note_takes_warning_ink():
    """SIC GAP-B #21: the failed-cycle warning was drawn in market-direction
    ink (.neg, green under ZH). It is a neutral note with a warning tint and an
    even border, never a direction colour or an edge stripe."""
    text = DOSSIER.read_text(encoding="utf-8")
    assert "{% if s.cycle.failed_cycle %}<p class=\"fail-note\">" in text
    assert "{% if s.cycle.failed_cycle %}<p class=\"neg\"" not in text
    start = text.index("  .fail-note {")
    css = text[start:text.index("}", start)]
    # The tint is the theme's warning surface token (the design ratchet forbids
    # a colour-mix literal on an added line), so the note reads the token.
    assert "var(--esurf-warn-soft)" in css
    for banned in ("var(--up)", "var(--down)", "var(--ok)", "var(--act)", "border-left", "border-right", "border-top:", "border-bottom:"):
        assert banned not in css, banned


def test_fund_dossier_translation_names_the_completed_cycle_when_failed():
    """SIC GAP-B #14: "strong cycles top late, a healthy-uptrend sign" sat next
    to "Failed cycle". The engine copy describes the last completed cycle; on a
    failed cycle the page says so in the same line."""
    text = DOSSIER.read_text(encoding="utf-8")
    line = next(l for l in text.splitlines() if "t(cp.translation, cp.translation_zh)" in l)
    assert "{% if s.cycle.failed_cycle %}" in line
    assert "That describes the last completed cycle; the current one has since failed (below)." in line
    assert "以上描述的是上一个已完成的周期；当前周期其后已失败（见下）。" in line


CHINA_CYCLES = ROOT / "templates" / "sector_cycles_china.html.j2"


def test_china_cycles_provenance_names_no_internal_file():
    """SIC GAP-B m2: the China cycles page's provenance note cited a repository
    path and an internal phase name on the customer face, and its Chinese used
    配置 for a setup. The note describes the testing in plain words and uses 形态."""
    text = CHINA_CYCLES.read_text(encoding="utf-8")
    start = text.index('<div class="sc-provenance" role="note">')
    note = text[start:text.index("</div>", start)]
    for banned in ("research/", ".md", "Phase-0", "PHASE0", "配置"):
        assert banned not in note, banned
    assert "当形态与今天相似时" in note
    assert "Our own first-pass testing" in note
