"""W11 r4 — lane-true feed words both lanes, session-anchored tips.

Seat-frozen revised spec (release review of r2+r3). r1/r2/r3 repairs stay
frozen except the superseded feed-word phrases and the rvol tip day-words.
"""
from __future__ import annotations

import re
from pathlib import Path

from tests.test_intraday_flow_w11_r1 import _region, _src
from tests.test_intraday_flow_w11_r2 import (
    FEED_MATRIX,
    LANES,
    RELATIVE_DAY,
    STATES,
    _stamp,
    needs_node,
)

ROOT = Path(__file__).resolve().parents[1]

# r3 dealer list plus the ZH pair the rvol tip used.
RENDERED_BANNED = RELATIVE_DAY + ("今日", "昨日")
DAY_WORD_RE = re.compile(
    r"(?i)(?<![\w.])(today'?s?|yesterday|tomorrow)(?![\w])|今天|昨天|明天|今日|昨日"
)
LANE_NOUNS_EN = ("quotes", "tape", "options")
LANE_NOUNS_ZH = ("行情", "资金带", "期权流")


def _rendered_copy(src: str) -> str:
    """Whole-template rendered strings: identifiers and comments excluded."""
    text = re.sub(r"\{#.*?#\}", "", src, flags=re.S)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"(^|[^:])//.*?$", r"\1", text, flags=re.M)
    text = re.sub(r"\b[A-Za-z_][A-Za-z0-9_]*today[A-Za-z0-9_]*\b", "", text, flags=re.I)
    return text


def _day_word_hits(blob: str) -> list[tuple[int, str]]:
    hits = []
    for i, line in enumerate(blob.splitlines(), 1):
        if DAY_WORD_RE.search(line):
            hits.append((i, line.strip()[:160]))
    return hits


def test_rvol_tip_is_session_anchored_both_lanes():
    src = _src()
    assert "This session\\'s volume vs a normal day at this exact time" in src
    assert "本时段成交量与同一时段正常水平之比" in src
    assert "Today's volume vs a normal day" not in src
    assert "今日成交量与该时段正常水平之比" not in src


def test_whole_template_rendered_strings_have_no_relative_day_words():
    """Extend the r3 dealer+stamp sweep to _src() rendered copy."""
    rendered = _rendered_copy(_src())
    hits = _day_word_hits(rendered)
    assert hits == [], f"rendered day-word hits: {hits}"
    for word in RENDERED_BANNED:
        # Identifier stems (bars_today) were stripped; leftover is rendered copy.
        if word.lower() in ("today", "yesterday", "tomorrow"):
            assert not re.search(rf"(?i)(?<![\w.]){re.escape(word)}(?![\w])", rendered), word
        else:
            assert word not in rendered, word


@needs_node
def test_feedword_matrix_lane_true_both_languages():
    src = _src()
    js = _region(src, "function feedWord", "function computeStance")
    from tests.test_intraday_flow_w11_r1 import _run_node

    script = f"""
    {js}
    var lanes = ['quotes','tape','options'];
    var states = ['live','unavailable','connecting'];
    var out = {{}};
    lanes.forEach(function(lane){{
      states.forEach(function(st){{
        out[lane+'|'+st] = feedWord(st, lane);
      }});
    }});
    process.stdout.write(JSON.stringify(out));
    """
    out = _run_node(script)
    for lane in LANES:
        for state in STATES:
            got = out[f"{lane}|{state}"]
            en, zh = FEED_MATRIX[(lane, state)]
            assert got["en"] == en, (lane, state, got)
            assert got["zh"] == zh, (lane, state, got)
            assert lane not in got["en"], (lane, state, got["en"])
            for noun in LANE_NOUNS_ZH:
                assert noun not in got["zh"], (lane, state, got["zh"], noun)


@needs_node
def test_en_stutter_absent_and_no_lane_noun_in_own_phrase():
    src = _src()
    fn = _region(src, "function feedWord", "function computeStance")
    assert "carrying the tape" not in fn
    assert "tape data not coming through" not in fn
    all_live = _stamp("live", "live", "live")
    all_down = _stamp("unavailable", "unavailable", "unavailable")
    mixed = _stamp("live", "connecting", "unavailable")
    for r in (all_live, all_down, mixed):
        assert "tape · carrying the tape" not in r["raw"]
        assert "tape · tape data" not in r["raw"]
        for row in r["tipRowsEn"]:
            label, _, phrase = row.partition(" · ")
            assert label in LANE_NOUNS_EN
            assert label not in phrase, (row, "lane noun leaked into phrase")
        for row in r["tipRowsZh"]:
            label, _, phrase = row.partition(" · ")
            assert label in LANE_NOUNS_ZH
            assert label not in phrase, (row, "ZH lane noun leaked into phrase")


@needs_node
def test_tip_rows_are_dom_rows_not_one_delimiter_string():
    r = _stamp("live", "live", "live")
    assert len(r["tipRowsEn"]) == 3
    assert len(r["tipRowsZh"]) == 3
    assert r["raw"].count('class="ift-feed-row"') == 3
    assert "lens-src" in r["raw"]
    # The in-row delimiter must not also join the three rows.
    assert "quotes · carrying prices · tape" not in r["raw"]
    assert "行情 · 报价已送达 · 资金带" not in r["raw"]
    assert r["tipRowsEn"] == [
        "quotes · carrying prices",
        "tape · carrying trades",
        "options · carrying flow",
    ]
    assert r["tipRowsZh"] == [
        "行情 · 报价已送达",
        "资金带 · 成交已送达",
        "期权流 · 流数据已送达",
    ]


@needs_node
def test_mixed_state_probe_both_lanes():
    """quotes=live, tape=connecting, options=unavailable — r1/r2 mixed probe, r4 copy."""
    r = _stamp("live", "connecting", "unavailable")
    en = " ".join(r["en"])
    zh = " ".join(r["zh"])
    assert "options flow not coming through" in en
    assert "期权流数据未送达" in zh
    assert "feeds still connecting" not in en
    assert "some feeds not coming through" not in en
    assert r["tipRowsEn"] == [
        "quotes · carrying prices",
        "tape · still connecting",
        "options · flow not coming through",
    ]
    assert r["tipRowsZh"] == [
        "行情 · 报价已送达",
        "资金带 · 连接中",
        "期权流 · 流数据未送达",
    ]


@needs_node
def test_two_connecting_headline_says_connecting_not_not_coming_through():
    two = _stamp("live", "connecting", "connecting")
    en = " ".join(two["en"])
    zh = " ".join(two["zh"])
    assert "feeds still connecting" in en
    assert "数据连接中" in zh
    assert "not coming through" not in en
    assert "未送达" not in zh
    three = _stamp("connecting", "connecting", "connecting")
    assert "feeds still connecting" in " ".join(three["en"])
    assert "数据连接中" in " ".join(three["zh"])
    assert "some feeds not coming through" not in " ".join(three["en"])
    assert "部分数据未送达" not in " ".join(three["zh"])
    one = _stamp("live", "connecting", "live")
    assert "feeds still connecting" in " ".join(one["en"])
    assert "tape still connecting" not in " ".join(one["en"])
    assert "数据连接中" in " ".join(one["zh"])


def test_setups_live_ratification_is_recorded_not_dnt8():
    """Seat-ratified 2026-09-11: labelled signal-count, not a freshness claim."""
    r3 = (ROOT / "tests" / "test_intraday_flow_w11_r3.py").read_text(encoding="utf-8")
    readme = (ROOT / "mockups" / "evidence" / "intraday-flow-w11" / "README.md").read_text(
        encoding="utf-8"
    )
    needle = (
        "no freshness-claiming live/实时 string; the labelled signal-count "
        "'setups live' is present and seat-ratified 2026-09-11"
    )
    assert needle in r3
    assert needle in readme
    assert "DNT #8" not in readme
    assert "DO-NOT-TOUCH #8" not in readme
    assert "no live string anywhere" not in readme
    assert "no live string anywhere" not in r3
