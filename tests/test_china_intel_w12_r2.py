"""W12 r2 china_intel heal — five-state B1, lane-equal regime colour,
dated briefs, degraded why, ZH fallback content. Both lanes.
"""
from __future__ import annotations

import re
import shutil
import tempfile
from datetime import date, timedelta
from pathlib import Path

from engine import china_intel_bus as bus
from tests.test_china_intel_w12_r1 import (
    _b, _cmd, _lane, _outside_details, _render, _today,
)


def _asof(days: int) -> str:
    return (_today() - timedelta(days=days)).isoformat()


def _stamp(b: dict) -> dict:
    """Copy `_staleness` onto a briefing dict the way `briefing()` does."""
    sa, rec = bus._staleness(b)
    b["surface_asof"] = sa
    b["max_staleness_days"] = rec["age"]
    b["max_staleness_feed"] = rec["key"]
    b["max_staleness_feed_asof"] = rec["asof"]
    b["stale_working_feeds"] = rec["working"]
    b["staleness_undated"] = rec["undated"]
    b["staleness_state"] = rec["state"]
    return b


def _feed(asof=None, **extra):
    d = dict(extra)
    if asof is not None:
        d["asof"] = asof
    return d


def _chip_lanes(html: str) -> tuple[str, str]:
    rest = _outside_details(html)
    m = re.search(r'<span class="mc warn[^"]*"[^>]*>([\s\S]*?)</span>\s*<span class="mode-badge">', rest)
    blob = m.group(1) if m else rest
    return _lane(blob, "l-en"), _lane(blob, "l-zh")


# --------------------------------------------------------------------------- #
# B1 — five states, both lanes; no stale-as-working fallback
# --------------------------------------------------------------------------- #

def test_b1_state1_all_fresh_chip_suppressed_both_lanes():
    b = _stamp(_b(
        news=_feed(_asof(0)), policy=_feed(_asof(1)), radar=_feed(_asof(2)),
    ))
    assert b["staleness_state"] == "fresh"
    assert b["stale_working_feeds"]
    html = _render(b, cmd_full=_cmd(2))
    rest = _outside_details(html)
    en, zh = _lane(rest, "l-en"), _lane(rest, "l-zh")
    assert "Oldest feed" not in en
    assert "最旧数据源" not in zh
    assert "Feed timestamps unavailable" not in en
    assert "数据源时间不可用" not in zh
    assert "No feed is current" not in en


def test_b1_state2_mixed_names_only_working_feed_both_lanes():
    b = _stamp(_b(
        news=_feed(_asof(0), band="steady"),
        policy=_feed(_asof(70), pboc_stance="neutral"),
        radar=_feed(_asof(1)),
    ))
    assert b["staleness_state"] == "mixed"
    assert {w["key"] for w in b["stale_working_feeds"]} <= {"news", "radar"}
    assert all(w["age"] <= 2 for w in b["stale_working_feeds"])
    html = _render(b, cmd_full=_cmd(2))
    en, zh = _chip_lanes(html)
    assert "Oldest feed · 70d — News still current." in en or (
        "Oldest feed · 70d — Divergence Radar still current." in en)
    assert "最旧数据源 · 70天——" in zh and "仍为最新。" in zh
    assert "still current" in en
    assert "Still reading" not in en
    assert "仍在读取" not in zh


def test_b1_state3_all_stale_names_failure_both_lanes():
    b = _stamp(_b(
        news=_feed(_asof(70)),
        policy=_feed(_asof(40)),
        altdata=_feed(_asof(30)),
    ))
    rec = bus._staleness(b)[1]
    assert rec["state"] == "all_stale"
    assert rec["working"] == []
    assert rec["age"] == 70
    html = _render(_stamp(b), cmd_full=_cmd(2))
    en, zh = _chip_lanes(html)
    assert "No feed is current — oldest 70d." in en
    assert "所有数据源均非最新——最旧 70 天。" in zh
    assert "still current" not in en
    assert "仍为最新" not in zh


def test_b1_state4_outage_renders_never_suppressed_both_lanes():
    b = _stamp(_b(
        news={"band": "steady"},
        policy={"pboc_stance": "neutral"},
        radar={},
    ))
    assert b["staleness_state"] == "outage"
    html = _render(b, cmd_full=_cmd(2))
    en, zh = _chip_lanes(html)
    assert "Feed timestamps unavailable." in en
    assert "数据源时间不可用。" in zh
    assert "Oldest feed" not in en


def test_b1_state4_no_feeds_at_all_is_outage_not_all_clear():
    sa, rec = bus._staleness({"news": None, "policy": None, "altdata": None,
                              "radar": None, "analysis": None,
                              "policy_phrase": None, "narrative_divergence": None,
                              "special_situations": None, "command": None})
    assert rec["state"] == "outage"
    b = _stamp(_b())
    # `_b()` defaults staleness_state to fresh for empty fixtures; the bus
    # path is outage. Re-stamp over the default.
    html = _render(b, cmd_full=_cmd(2))
    en, zh = _chip_lanes(html)
    assert "Feed timestamps unavailable." in en
    assert "数据源时间不可用。" in zh


def test_b1_state5_undated_among_dated_joins_naming_both_lanes():
    b = _stamp(_b(
        news={"band": "steady"},  # present, no asof
        policy=_feed(_asof(70), pboc_stance="neutral"),
    ))
    rec = bus._staleness(b)[1]
    assert rec["state"] == "undated_among"
    assert "news" in rec["undated"]
    assert rec["age"] == 70
    html = _render(b, cmd_full=_cmd(2))
    en, zh = _chip_lanes(html)
    assert "Oldest dated feed · 70d · News: no timestamp." in en
    assert "最旧有时间数据源 · 70天 · 新闻：无时间戳" in zh


def test_b1_no_stale_fallback_into_working():
    """The r1 lie: empty working fell back to a 30d feed as 'still reading'."""
    b = {
        "news": {"asof": _asof(70)},
        "policy": {"asof": _asof(40)},
        "altdata": {"asof": _asof(30)},
        "radar": None, "analysis": None, "policy_phrase": None,
        "narrative_divergence": None, "special_situations": None, "command": None,
    }
    rec = bus._staleness(b)[1]
    assert rec["working"] == []
    assert rec["state"] == "all_stale"
    assert rec["age"] == 70


# --------------------------------------------------------------------------- #
# Degraded-AI why — enum → words, never the enum, never nothing
# --------------------------------------------------------------------------- #

def test_degraded_why_maps_enum_both_lanes_never_leaks():
    why = bus._degraded_why("brain_timeout")
    assert why["en"].startswith("The AI read timed out")
    assert "超时" in why["zh"]
    assert "brain_timeout" not in why["en"]
    assert "brain_timeout" not in why["zh"]
    html = _render(_b(
        analysis={"llm_synthesis": None,
                  "llm_synthesis_degraded_reason": "brain_timeout"},
        llm_synthesis_degraded_why=why,
    ), cmd_full=_cmd(2))
    rest = _outside_details(html)
    en, zh = _lane(rest, "l-en"), _lane(rest, "l-zh")
    assert "The AI read timed out" in en
    assert "AI 解读超时" in zh
    assert "brain_timeout" not in rest
    assert "not_wired" not in rest


def test_degraded_why_unknown_enum_uses_generic_sentence():
    why = bus._degraded_why("some_new_enum")
    assert why["en"] == "The AI read is unavailable."
    assert why["zh"] == "AI 解读不可用。"
    assert "some_new_enum" not in why["en"]


# --------------------------------------------------------------------------- #
# Dated briefs — every card in the module has as-of + source chip
# --------------------------------------------------------------------------- #

def test_dated_brief_cards_carry_asof_and_source_chip_both_lanes():
    today = str(_today())
    b = _b(
        policy_phrase={"asof": today, "n_events_recent": 0, "recent_events": [],
                       "cold_start_organs": []},
        narrative_divergence={"asof": today, "divergence_z": 0.2,
                              "risk_flag": False, "trend_5d": "flat"},
        analysis={"asof": today,
                  "conviction": [{"sector_en": "Brokers", "sector_zh": "券商",
                                  "radar_sign": "positive", "opportunity_score": 50,
                                  "stage": "early", "context_conviction": 40,
                                  "edge_remaining": 0.4,
                                  "conviction_band": ["Moderate", "中等"],
                                  "surfaces_confirming": ["radar"],
                                  "rationale_en": "Radar leads.",
                                  "rationale_zh": "雷达领先。"}],
                  "flagged_tickers": [{"ticker": "600030.SS", "name": "中信证券",
                                       "side": "long-context",
                                       "surfaces": ["radar"]}],
                  "chains": [{"band": "forming", "label_en": "Easing chain",
                              "label_zh": "宽松链条", "k": 1, "n": 3,
                              "links": []}]},
        conviction=[{"sector_en": "Brokers", "sector_zh": "券商",
                     "radar_sign": "positive", "opportunity_score": 50,
                     "stage": "early", "context_conviction": 40,
                     "edge_remaining": 0.4,
                     "conviction_band": ["Moderate", "中等"],
                     "surfaces_confirming": ["radar"],
                     "rationale_en": "Radar leads.",
                     "rationale_zh": "雷达领先。"}],
        flagged_tickers=[{"ticker": "600030.SS", "name": "中信证券",
                          "side": "long-context", "surfaces": ["radar"]}],
    )
    html = _render(b, cmd_full=_cmd(2))
    section = re.search(
        r'<section data-l1="dated-cards">([\s\S]*?)</section>', html).group(1)
    heads = re.findall(
        r'<div class="ci-card-head">\s*<div class="ci-card-title">([\s\S]*?)</div>([\s\S]*?)</div>',
        section)
    assert heads, "no ci-card-head in dated-cards"
    titles = []
    for title_html, rest in heads:
        title = re.sub(r"<[^>]+>", "", title_html)
        assert today in rest, f"dated card missing as-of: {title}"
        assert 'class="surf"' in rest, f"dated card missing source chip: {title}"
        titles.append(title)
    blob = " ".join(titles)
    assert "Policy language shifts" in blob and "政策表述变化" in blob
    assert "Onshore / offshore tone" in blob
    assert "Cross-surface conviction" in blob
    assert "Flagged tickers" in blob
    assert "Transmission chains" in blob
    assert "传导链条" in blob
    en, zh = _lane(section, "l-en"), _lane(section, "l-zh")
    assert "Desk synthesis" in en
    assert "综合解读" in zh
    assert "Policy language" in en
    assert "政策表述" in zh


def test_undated_transmission_chains_fold_into_lead_brief():
    b = _b(analysis={"chains": [{"band": "forming", "label_en": "Easing chain",
                                 "label_zh": "宽松链条", "k": 1, "n": 3,
                                 "links": []}]})
    html = _render(b, cmd_full=_cmd(2))
    dated = re.search(r'<section data-l1="dated-cards">([\s\S]*?)</section>', html).group(1)
    lead = re.search(r'<section data-l1="lead-brief">([\s\S]*?)</section>', html).group(1)
    assert "Transmission chains" not in dated
    assert "传导链条" not in dated
    assert "Easing chain" in lead
    assert "kept on the lead brief" in _lane(lead, "l-en")


# --------------------------------------------------------------------------- #
# ZH fallback content pin (missing-zh fixture)
# --------------------------------------------------------------------------- #

def test_s6_missing_zh_fixture_pins_unavailable_content_not_english():
    out = bus._bilingual_predictions(["Hold the 1-year loan rate."])
    assert out == [{"en": "Hold the 1-year loan rate.", "zh": "暂无中文摘要"}]
    b = _b(policy={"pboc_stance": "neutral", "asof": str(_today()),
                   "predictions": out})
    html = _render(b, cmd_full=None)
    rest = _outside_details(html)
    zh, en = _lane(rest, "l-zh"), _lane(rest, "l-en")
    assert "暂无中文摘要" in zh
    assert "Hold the 1-year loan rate." in en
    assert "Hold the 1-year loan rate." not in zh


# --------------------------------------------------------------------------- #
# Dead CSS + name-tip + method-band stance
# --------------------------------------------------------------------------- #

def test_orphaned_css_from_deletions_gone():
    html = _render(_b(), cmd_full=_cmd(2))
    css = html.split("</style>")[0]
    for sel in (".desks {", ".desk {", ".desk:hover", ".desk .dh",
                ".desk-asof", ".desk-chips", ".disc-score-bar",
                "a.scard", ".cards {"):
        assert sel not in css, sel


def test_command_name_truncation_keeps_full_name_tip():
    html = _render(_b(), cmd_full=_cmd(3))
    assert 'data-tip-en="名称0"' in html
    assert 'data-tip-zh="名称0"' in html


def test_method_band_has_no_ignore_stance():
    html = _render(_b(), cmd_full=_cmd(2))
    band = re.search(r'<section data-l1="method-band">([\s\S]*?)</section>', html).group(1)
    assert "ci-stance" not in band
    assert "Ignore" not in _lane(band, "l-en")
    assert "可忽略" not in _lane(band, "l-zh")


def test_zh_stance_uses_estate_canonical():
    html = _render(_b(salience=[{"kind": "news", "label_en": "X", "label_zh": "甲",
                                 "detail_en": "ok", "detail_zh": "可"}]),
                   cmd_full=_cmd(2))
    zh = _lane(_outside_details(html), "l-zh")
    assert "观望——勿追涨" in zh
    assert "观察，勿追高" not in zh


# --------------------------------------------------------------------------- #
# Regime computed-style — both lanes (S1 rig idiom)
# --------------------------------------------------------------------------- #

def test_regime_hex_computed_style_both_lanes():
    from playwright.sync_api import sync_playwright

    b = _b(regime={"roro": 0.4, "risk_tilt": 1, "band_en": "Greed", "band_zh": "贪婪"})
    html = _render(b, cmd_full=_cmd(2))
    root = Path(__file__).resolve().parents[1]
    staging = Path(tempfile.mkdtemp(prefix="ci-w12-r2-regime-"))
    try:
        (staging / "index.html").write_text(html, encoding="utf-8")
        shutil.copy(root / "templates" / "theme.css", staging / "theme.css")
        shutil.copy(root / "templates" / "theme.js", staging / "theme.js")
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.goto((staging / "index.html").as_uri(), wait_until="load")
            page.evaluate(
                """() => {
                  window.__skyDeck = true;
                  ['.sky-fx','#mmb-root','#mmb-boot','.ift-aurora','.mx5-aurora']
                    .forEach((s) => document.querySelectorAll(s).forEach((n) => n.remove()));
                }"""
            )

            def colour(locale: str) -> str:
                page.evaluate(
                    """(loc) => {
                      const el = document.documentElement;
                      if (typeof window.setLang === 'function') window.setLang(loc);
                      else { el.setAttribute('data-lang', loc); el.lang = loc; }
                    }""",
                    locale,
                )
                observed = page.evaluate(
                    "() => document.documentElement.getAttribute('data-lang')")
                assert (observed or "en") == locale, observed
                return page.evaluate(
                    """() => {
                      const b = document.querySelector('.cmdbar .regime b.on');
                      if (!b) return 'MISSING';
                      return getComputedStyle(b).color;
                    }"""
                )

            en_c = colour("en")
            zh_c = colour("zh")
            browser.close()
        # #1f9a55 = rgb(31, 154, 85); ZH flips to #d23f3f = rgb(210, 63, 63)
        assert en_c == "rgb(31, 154, 85)", en_c
        assert zh_c == "rgb(210, 63, 63)", zh_c
    finally:
        shutil.rmtree(staging, ignore_errors=True)
