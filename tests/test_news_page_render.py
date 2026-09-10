"""Render smoke tests for the 2026 Markets-News revamp (news.html.j2).

The page is a hero-led, importance-ranked, aged single feed (build_site builds the
unified `news_feed`; the template renders it). These tests pin the SHIPPED design's
invariants and the critical house-law guards:
  • renders with a full vm and with an all-empty vm (null-safety)
  • schema-violating side-artifacts degrade, never raise
  • no translated text inside a title= attribute (CI i18n guard)
  • internal scorer strings never surface; reason slugs are de-underscored
  • a story row carries exactly ONE label — no event / direction / AI chips (the
    Undefined guard the AI chip needed is moot: the branch no longer exists)
  • the build_site render-call shape (no duplicate macro_news kwarg) holds
  • bilingual l-en/l-zh spans are emitted

Mirrors scripts/build_site.py's Jinja env (autoescape=False, same loader).
"""
from __future__ import annotations

import re
from pathlib import Path

import jinja2
import pytest

ROOT = Path(__file__).resolve().parent.parent


def _env() -> jinja2.Environment:
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(ROOT / "templates")),
        autoescape=False,
    )
    try:
        from engine import i18n  # noqa: PLC0415
        env.globals.update(td=i18n.td, tr=i18n.tr)
    except Exception:  # noqa: BLE001
        env.globals.update(td=lambda en: en, tr=lambda en: en)
    return env


# --------------------------------------------------------------------------- #
# fixtures
# --------------------------------------------------------------------------- #
def _feed_item(title="Fed holds rates steady", lane="fed", theme="monetary",
               rank=60.0, tickers=None, event=None, ai_importance=None,
               sentiment=None, seendate="2026-07-22T10:00:00Z") -> dict:
    return {
        "title": title, "title_zh": "美联储维持利率不变",
        "url": "https://reuters.com/x", "domain": "reuters.com",
        "source_name": "Reuters", "source_tier": "tier1",
        "seendate": seendate, "theme": theme, "lane": lane,
        "rank_score": rank, "tickers": tickers or [], "event": event,
        "ai_importance": ai_importance, "ai_sentiment": sentiment,
        "novelty_z": 1.8, "echo": {"n_sources": 3},
    }


def _full_vm() -> dict:
    feed = [
        _feed_item("RTX beats Q2, raises FY guidance", "companies", "earnings", 74.0,
                   ["RTX"], {"event_type": "guidance_raise", "direction": "bullish"}),
        _feed_item("Fed officials signal patience on cuts", "fed", "monetary", 62.0),
        _feed_item("Tesla slumps as AI-spend concerns weigh", "companies", "stocks", 55.0,
                   ["TSLA"], {"event_type": "rating_change", "direction": "bearish"}),
        _feed_item("Payrolls cool at the margin", "macro", "labor", 48.0),
        _feed_item("Broad market drifts lower", "markets", "macro", 40.0),
    ]
    return dict(
        news_feed=feed,
        latest={"date": "2026-07-22", "conditions": {"risk_appetite": {
            "news_sentiment_state": "optimistic", "news_sentiment_z": 0.7}}},
        macro_news={
            "headlines": [f for f in feed if f["lane"] in ("fed", "macro", "markets")],
            "synthesis": {"top_tickers": ["RTX", "TSLA"], "top_channels": []},
            "fetched_at": "2026-07-22T06:00:00Z",
        },
        macro_news_disclaimer="News is display-only context and never feeds a signal.",
        macro_news_disclaimer_zh="新闻仅为展示性背景，绝不构成信号。",
        macro_catalysts=[{"date": "2026-07-30", "time_et": "2:00pm",
                          "label": "FOMC decision", "label_zh": "FOMC决议"}],
        event_strip=[{"dow": "Thu", "md": "Jul 24", "label": "Jobless claims",
                      "label_zh": "初请失业金"}],
        prediction_markets={"events": [{"label_en": "July FOMC", "label_zh": "7月FOMC",
                             "outcomes": [{"outcome": "Hold", "prob": 82}]}]},
        macro_releases={"cards": [{
            "display_name": "Nonfarm Payrolls", "release": "nonfarm_payrolls",
            "actual": 147000.0, "prior": 139000.0, "prior_label": "vs prior",
            "period": "Jun 2026", "surprise_size": "notable", "direction_tag": "bullish",
            "summary": "Payrolls above prior."}]},
        news_rejected={"feeds": {"macro": [
            {"title": "10 stocks to buy this week", "domain": "fool.com",
             "reason": "stock_pick_roundup"}]}},
        news_calibration={"classes": [
            {"event_type": "earnings_result", "n": 14, "verdict": "accruing"}]},
        financial_news={"providers": {"polygon": True}, "market": []},
    )


def _empty_vm() -> dict:
    return dict(
        news_feed=[], latest={"date": "2026-07-22", "conditions": None},
        macro_news=None, macro_news_disclaimer="", macro_news_disclaimer_zh="",
        macro_catalysts=[], event_strip=[], prediction_markets=None,
        macro_releases=None, news_rejected=None, news_calibration=None,
        financial_news=None,
    )


def _render_full() -> str:
    return _env().get_template("news.html.j2").render(**_full_vm())


def _render_empty() -> str:
    return _env().get_template("news.html.j2").render(**_empty_vm())


# --------------------------------------------------------------------------- #
# render / structure
# --------------------------------------------------------------------------- #
def test_full_vm_renders_without_exception():
    html = _render_full()
    assert len(html) > 1000
    assert "What matters now" in html


def test_empty_vm_renders_without_exception():
    html = _render_empty()
    assert len(html) > 500
    assert "What matters now" in html          # header always renders
    assert "quiet" in html.lower()             # empty-feed state


def test_hero_lead_story_renders():
    html = _render_full()
    assert "nx-lead" in html
    assert "RTX beats Q2" in html              # top-ranked story leads the hero
    assert "Top story" in html or "头条" in html


def test_the_impact_ring_is_gone_and_stays_gone():
    """The ring set an 8px uppercase label inside a circular overflow:hidden clip.

    It fits at 8px and clips the moment a browser enforces a minimum font size —
    measured on the live page, from 12px at the 60px ring and from 10px at the 50px
    mobile ring, which is what the operator saw ("IMPAC" with the T cut off). Type
    that small is not under our control, so the fix is that no text lives inside a
    circular clip here at all; the list's order carries the ranking and the
    diagnostics drawer keeps the receipt. Re-adding the ring re-opens the defect.
    """
    html = _render_full()
    assert "nx-impact" not in html
    assert "font-size:8px" not in html, "sub-9px type is not under design control"
    # the lead still leads, and still wraps rather than overflowing on a narrow screen
    assert "nx-lead-title" in html
    assert ".nx-lead-title{ overflow-wrap:anywhere; }" in html


def test_feed_renders_ranked_story_cards():
    html = _render_full()
    assert html.count("nx-story") >= 5         # one row per feed item
    # No per-row score badge: a number beside every headline is the system talking
    # about itself, and the list is already in rank order (the masthead says so).
    assert "nx-rankdot" not in html


def test_lane_and_search_data_attributes_present():
    """The lane filter + search read data-lane / data-search — the previously-dead
    data-search attribute is now wired."""
    html = _render_full()
    assert 'data-lane="fed"' in html and 'data-lane="companies"' in html
    assert "data-search=" in html
    assert 'id="nxSeg"' in html and 'id="nxSearch"' in html


def test_release_board_renders():
    html = _render_full()
    assert "Nonfarm Payrolls" in html
    assert "147" in html


def test_calendar_renders_catalysts_and_strip():
    html = _render_full()
    assert "FOMC decision" in html or "FOMC决议" in html
    assert "Jobless claims" in html or "初请失业金" in html


def test_diagnostics_collapsed_and_relocated():
    """Reject log + calibration live in ONE collapsed drawer, not as prominent boards."""
    html = _render_full()
    assert '<details class="nx-diag">' in html        # a collapsed <details> drawer
    assert "Newsroom diagnostics" in html or "新闻室诊断" in html


# --------------------------------------------------------------------------- #
# house-law guards
# --------------------------------------------------------------------------- #
def test_no_translated_title_attrs():
    """No translated (CJK) text inside a title= attribute (check_title_i18n guard)."""
    import re
    html = _render_full()
    for t_val in re.findall(r'title=["\']([^"\']+)["\']', html):
        assert not any('一' <= c <= '鿿' for c in t_val), \
            f"Translated text in title= attribute: {t_val!r}"


def test_no_span_leak_in_placeholder():
    """The search placeholder must be a plain string, not a t() span pair."""
    import re
    html = _render_full()
    ph = re.search(r'placeholder="([^"]*)"', html)
    assert ph and "<span" not in ph.group(1), "t() must never populate an attribute"


def test_importance_reasons_and_internal_slugs_never_render():
    html = _render_full()
    assert "importance_reasons" not in html
    assert "intelligence_score" not in html    # internal scorer keys never surface as text
    # reject reason is de-underscored, never the raw slug
    assert "stock_pick_roundup" not in html


def test_a_story_carries_exactly_one_label():
    """Was: the AI chip renders only for a real ai_importance (a Jinja Undefined guard).

    The chip itself is gone. A headline used to carry theme + event + direction +
    "✦ AI" + up to five tickers — five to nine coloured objects each — which is what
    made the list unreadable. One theme label survives on the row; the rest is source
    and time. The Undefined bug it guarded cannot recur because the branch is gone,
    and this pins that: a real ai_importance must still not produce a chip.
    """
    html = _render_full()
    assert "nx-chip ai" not in html
    vm = _full_vm()
    vm["news_feed"][0]["ai_importance"] = 92.0
    html2 = _env().get_template("news.html.j2").render(**vm)
    assert "nx-chip ai" not in html2
    # exactly one theme label inside each story row (the lead and the also-big
    # column carry their own, so count per row rather than over the whole page)
    rows = re.findall(r'<article class="nx-story.*?</article>', html2, re.S)
    assert rows, "no story rows rendered"
    for row in rows:
        assert row.count('class="nx-chip th-') == 1, "a story row grew a second label"
        for gone in ("nx-chip evt", "nx-chip ai", "dir-up", "dir-down", "dir-mixed"):
            assert gone not in row, f"{gone} came back to the row"


def test_bilingual_spans_present():
    html = _render_full()
    assert 'class="l-en"' in html and 'class="l-zh"' in html
    assert "当下要闻" in html                    # zh title span emitted


def test_disclaimer_renders():
    html = _render_full()
    assert "display-only" in html.lower()


def test_consequence_section_is_single_column_not_nx_cols():
    """MAJOR 4 ruling: #nxConsequence is a full-width single column, not nx-cols."""
    html = _render_full()
    assert 'class="nx-consequence" id="nxConsequence"' in html
    assert 'class="nx-cols" id="nxConsequence"' not in html
    # The releases board may still use nx-cols; only this section left that grid.
    assert "#nxConsequence{ margin-top:26px; }" in html
    assert "#nxConsequence .nx-rel-grid{ grid-template-columns:repeat(auto-fill,minmax(280px,1fr)); gap:14px; }" in html
    assert "html[data-theme=\"light\"] #nxConsequence .nx-rel{" in html
    assert "var(--card-shadow)" in html and "var(--popover-shadow)" in html
    # No <main> wrapper inside the consequence section.
    start = html.index('id="nxConsequence"')
    end = html.index("</section>", start)
    assert "<main>" not in html[start:end]


def test_consequence_empty_exposure_state_is_typed_sentence_only():
    """NM-3: ZERO qualifying rows prints the typed empty; dated header still shows."""
    vm = _full_vm()
    vm["chronicle_impact"] = {
        "stance_en": None,
        "stance_zh": None,
        "reason_en": "No event with a named market exposure in the last 7 days.",
        "reason_zh": "近7天没有带明确市场敞口的事件。",
        "empty_kind": "no_named_exposure",
        "window_label_en": "Events from 31 Aug to 7 Sep 2026",
        "window_label_zh": "2026年8月31日至9月7日的事件",
        "rows": [],
    }
    html = _env().get_template("news.html.j2").render(**vm)
    start = html.index('id="nxConsequence"')
    end = html.index("</section>", start)
    section = html[start:end]
    assert "No event with a named market exposure in the last 7 days." in section
    assert "近7天没有带明确市场敞口的事件。" in section
    assert "Cards appear when an event maps to a named exposure." in section
    assert "当事件对应到明确标的时，卡片会在此显示。" in section
    assert "Events from 31 Aug to 7 Sep 2026" in section
    assert "2026年8月31日至9月7日的事件" in section
    assert "nx-empty-lead" in section
    assert "nx-empty-next" in section
    assert "nx-rel-grid" not in section
    assert "We don’t size these yet" not in section
    assert "Sizes come from similar past episodes" not in section
    assert "Not available yet" not in section
    assert "No named ticker" not in section
    assert "未点名标的" not in section


def test_consequence_card_date_is_plain_not_raw_iso():
    """R3: the card prints '7 Sep 2026' / '2026年9月7日', never 2026-09-07."""
    vm = _full_vm()
    vm["chronicle_impact"] = {
        "stance_en": "Recent market events and the names they touch — shown only when an event maps to a named exposure.",
        "stance_zh": "近期市场事件及其涉及的标的——仅在事件对应到明确标的时显示。",
        "reason_en": None,
        "reason_zh": None,
        "empty_kind": None,
        "window_label_en": "Events from 31 Aug to 7 Sep 2026",
        "window_label_zh": "2026年8月31日至9月7日的事件",
        "rows": [
            {
                "event_id": "cev-a",
                "event_time": "2026-09-07",
                "event_time_en": "7 Sep 2026",
                "event_time_zh": "2026年9月7日",
                "title_en": "AAA reported earnings",
                "title_zh": "AAA公布业绩",
                "direct_tickers": ["AAA"],
                "second_order_tickers": [],
                "second_order_truncated": False,
            },
            {
                "event_id": "cev-b",
                "event_time": "2026-09-06",
                "event_time_en": "6 Sep 2026",
                "event_time_zh": "2026年9月6日",
                "title_en": "BBB reported earnings",
                "title_zh": "BBB公布业绩",
                "direct_tickers": ["BBB"],
                "second_order_tickers": [],
                "second_order_truncated": False,
            },
            {
                "event_id": "cev-c",
                "event_time": "2026-09-05",
                "event_time_en": "5 Sep 2026",
                "event_time_zh": "2026年9月5日",
                "title_en": "CCC reported earnings",
                "title_zh": "CCC公布业绩",
                "direct_tickers": ["CCC"],
                "second_order_tickers": [],
                "second_order_truncated": False,
            },
        ],
    }
    html = _env().get_template("news.html.j2").render(**vm)
    start = html.index('id="nxConsequence"')
    end = html.index("</section>", start)
    section = html[start:end]
    assert "7 Sep 2026" in section
    assert "2026年9月7日" in section
    assert "2026-09-07" not in section
    assert "Events from 31 Aug to 7 Sep 2026" in section
    assert "Named exposures only — no sizing, not a forecast." in section
    assert "仅列出相关标的——不做幅度推算，非预测。" in section
    assert "Sizes come from similar past episodes" not in section
    assert "We don’t size these yet" not in section
    assert "Size not available yet" not in section
    assert "暂无幅度" not in section


def test_consequence_one_row_renders_card_not_empty():
    """NM-3: one qualifying row is a card; empty state stays off."""
    vm = _full_vm()
    vm["chronicle_impact"] = {
        "stance_en": "Recent market events and the names they touch — shown only when an event maps to a named exposure.",
        "stance_zh": "近期市场事件及其涉及的标的——仅在事件对应到明确标的时显示。",
        "reason_en": None,
        "reason_zh": None,
        "empty_kind": None,
        "window_label_en": "Events from 31 Aug to 7 Sep 2026",
        "window_label_zh": "2026年8月31日至9月7日的事件",
        "rows": [{
            "event_id": "cev-solo",
            "event_time": "2026-09-07",
            "event_time_en": "7 Sep 2026",
            "event_time_zh": "2026年9月7日",
            "title_en": "AAPL reported earnings",
            "title_zh": "AAPL公布业绩",
            "direct_tickers": ["AAPL"],
            "second_order_tickers": [],
            "second_order_truncated": False,
        }],
    }
    html = _env().get_template("news.html.j2").render(**vm)
    start = html.index('id="nxConsequence"')
    end = html.index("</section>", start)
    section = html[start:end]
    assert "nx-rel-grid" in section
    assert "AAPL reported earnings" in section
    assert "AAPL公布业绩" in section
    assert "No event with a named market exposure" not in section
    assert "Size not available yet" not in section
    assert "暂无幅度" not in section


def test_consequence_fallback_label_renders():
    """NM-3: newest-200 fallback prints the dated-corpus-free label."""
    vm = _full_vm()
    vm["chronicle_impact"] = {
        "stance_en": "Recent market events and the names they touch — shown only when an event maps to a named exposure.",
        "stance_zh": "近期市场事件及其涉及的标的——仅在事件对应到明确标的时显示。",
        "reason_en": None,
        "reason_zh": None,
        "empty_kind": None,
        "window_mode": "newest_200_fallback",
        "window_label_en": "Latest 200 recorded events",
        "window_label_zh": "最近记录的200个事件",
        "rows": [{
            "event_id": "cev-fb",
            "event_time": None,
            "event_time_en": None,
            "event_time_zh": None,
            "title_en": "AAPL reported earnings",
            "title_zh": "AAPL公布业绩",
            "direct_tickers": ["AAPL"],
            "second_order_tickers": [],
            "second_order_truncated": False,
        }],
    }
    html = _env().get_template("news.html.j2").render(**vm)
    start = html.index('id="nxConsequence"')
    end = html.index("</section>", start)
    section = html[start:end]
    assert "Latest 200 recorded events" in section
    assert "最近记录的200个事件" in section


def test_consequence_zh_earnings_card_has_no_ascii_spaces():
    """ZH spacing: no ASCII spaces around the middot or inside an earnings sentence."""
    vm = _full_vm()
    vm["chronicle_impact"] = {
        "stance_en": "Recent market events and the names they touch — shown only when an event maps to a named exposure.",
        "stance_zh": "近期市场事件及其涉及的标的——仅在事件对应到明确标的时显示。",
        "reason_en": None,
        "reason_zh": None,
        "empty_kind": None,
        "window_label_en": "Events from 31 Aug to 7 Sep 2026",
        "window_label_zh": "2026年8月31日至9月7日的事件",
        "rows": [{
            "event_id": "cev-aapl",
            "event_time": "2026-09-07",
            "event_time_en": "7 Sep 2026",
            "event_time_zh": "2026年9月7日",
            "title_en": "AAPL reported earnings",
            "title_zh": "AAPL公布业绩",
            "direct_tickers": ["AAPL"],
            "second_order_tickers": [],
            "second_order_truncated": False,
        }],
    }
    html = _env().get_template("news.html.j2").render(**vm)
    start = html.index('id="nxConsequence"')
    end = html.index("</section>", start)
    section = html[start:end]
    zh_title = re.search(r'class="l-zh">AAPL公布业绩</span>', section)
    assert zh_title, section
    assert "AAPL 公布" not in section
    assert "已结 · " not in section
    assert " · 达到" not in section


def test_consequence_stance_and_section_line_once_each_locale():
    """r4 (d): stance + section line appear exactly once per locale on a built page."""
    vm = _full_vm()
    vm["chronicle_impact"] = {
        "stance_en": "Recent market events and the names they touch — shown only when an event maps to a named exposure.",
        "stance_zh": "近期市场事件及其涉及的标的——仅在事件对应到明确标的时显示。",
        "reason_en": None,
        "reason_zh": None,
        "empty_kind": None,
        "window_label_en": "Events from 31 Aug to 7 Sep 2026",
        "window_label_zh": "2026年8月31日至9月7日的事件",
        "rows": [{
            "event_id": "cev-aapl",
            "event_time": "2026-09-07",
            "event_time_en": "7 Sep 2026",
            "event_time_zh": "2026年9月7日",
            "title_en": "AAPL reported earnings",
            "title_zh": "AAPL公布业绩",
            "direct_tickers": ["AAPL"],
            "second_order_tickers": [],
            "second_order_truncated": False,
            "note_en": None,
            "note_zh": None,
        }],
    }
    html = _env().get_template("news.html.j2").render(**vm)
    start = html.index('id="nxConsequence"')
    end = html.index("</section>", start)
    section = html[start:end]
    stance_en = "Recent market events and the names they touch — shown only when an event maps to a named exposure."
    stance_zh = "近期市场事件及其涉及的标的——仅在事件对应到明确标的时显示。"
    line_en = "Named exposures only — no sizing, not a forecast."
    line_zh = "仅列出相关标的——不做幅度推算，非预测。"
    assert section.count(stance_en) == 1
    assert section.count(stance_zh) == 1
    assert section.count(line_en) == 1
    assert section.count(line_zh) == 1
    assert "Size not available yet" not in section
    assert "Sizes come from similar past episodes" not in section
    assert "watch, don’t chase" not in section
    assert "观察为主，不必追高" not in section


def test_consequence_flip_note_renders_without_size_slot():
    """NM-5: the unstable-direction note prints; the size slot does not."""
    vm = _full_vm()
    vm["chronicle_impact"] = {
        "stance_en": "Recent market events and the names they touch — shown only when an event maps to a named exposure.",
        "stance_zh": "近期市场事件及其涉及的标的——仅在事件对应到明确标的时显示。",
        "reason_en": None,
        "reason_zh": None,
        "empty_kind": None,
        "window_label_en": "Events from 31 Aug to 7 Sep 2026",
        "window_label_zh": "2026年8月31日至9月7日的事件",
        "rows": [{
            "event_id": "cev-ca",
            "event_time": "2026-09-04",
            "event_time_en": "4 Sep 2026",
            "event_time_zh": "2026年9月4日",
            "title_en": "Canada's macro backdrop turned from stagflation to reflation",
            "title_zh": "加拿大宏观环境由滞胀转向再通胀",
            "direct_tickers": ["EWC"],
            "second_order_tickers": [],
            "second_order_truncated": False,
            "note_en": "changed direction twice this week — unstable",
            "note_zh": "本周两度转向——尚不稳定",
        }],
    }
    html = _env().get_template("news.html.j2").render(**vm)
    start = html.index('id="nxConsequence"')
    end = html.index("</section>", start)
    section = html[start:end]
    assert "changed direction twice this week — unstable" in section
    assert "本周两度转向——尚不稳定" in section
    assert "EWC" in section
    assert "Size not available yet" not in section
    assert "暂无幅度" not in section


def test_template_and_built_page_omit_no_named_ticker_branch():
    """NM-B: the selector guarantees a named exposure; the dead label is gone."""
    template = (ROOT / "templates" / "news.html.j2").read_text(encoding="utf-8")
    assert "No named ticker" not in template
    assert "未点名标的" not in template
    html = _render_full()
    assert "No named ticker" not in html
    assert "未点名标的" not in html


def test_second_order_only_row_prints_also_watching_not_named():
    """NM-B: a second-order-only row prints Also watching / 同时关注, never Named."""
    vm = _full_vm()
    vm["chronicle_impact"] = {
        "stance_en": "Recent market events and the names they touch — shown only when an event maps to a named exposure.",
        "stance_zh": "近期市场事件及其涉及的标的——仅在事件对应到明确标的时显示。",
        "reason_en": None,
        "reason_zh": None,
        "empty_kind": None,
        "window_label_en": "Events from 31 Aug to 7 Sep 2026",
        "window_label_zh": "2026年8月31日至9月7日的事件",
        "rows": [{
            "event_id": "cev-so",
            "event_time": "2026-09-07",
            "event_time_en": "7 Sep 2026",
            "event_time_zh": "2026年9月7日",
            "title_en": "Research note on AI spending",
            "title_zh": "关于人工智能开支的研究纪要",
            "direct_tickers": [],
            "second_order_tickers": ["NVDA"],
            "second_order_truncated": False,
            "note_en": None,
            "note_zh": None,
        }],
    }
    html = _env().get_template("news.html.j2").render(**vm)
    start = html.index('id="nxConsequence"')
    end = html.index("</section>", start)
    section = html[start:end]
    assert "Also watching" in section
    assert "同时关注" in section
    assert "NVDA" in section
    assert '<span class="l-en">Named</span>' not in section
    assert '<span class="l-zh">点名</span>' not in section
    assert "No named ticker" not in section
    assert "未点名标的" not in section


def test_build_site_passes_unfiltered_event_spine_to_glance():
    """The site builder hands the full loaded spine to glance — no pre-filter."""
    src = (ROOT / "scripts" / "build_site.py").read_text(encoding="utf-8")
    load = "_evs = _spine_mod.load_events_jsonl(_ev_path) if _ev_path.exists() else []"
    call = "_chronicle_impact = _impact_mod.glance_consequence_surface(_evs)"
    assert load in src
    assert call in src
    between = src.split(load, 1)[1].split(call, 1)[0]
    assert "_evs =" not in between
    assert "filter" not in between
    assert "[" not in between


# --------------------------------------------------------------------------- #
# degrade-safety — schema-violating side-artifacts must not raise
# --------------------------------------------------------------------------- #
_BAD_ARTIFACT_CASES = [
    ("calibration_is_list", {"news_calibration": [1, 2, 3]}),
    ("calibration_classes_str", {"news_calibration": {"classes": "x"}}),
    ("releases_cards_str", {"macro_releases": {"cards": "x"}}),
    ("releases_is_list", {"macro_releases": [1, 2]}),
    ("cards_of_strings", {"macro_releases": {"cards": ["a", "b"]}}),
    ("rejected_is_list", {"news_rejected": [1, 2]}),
    ("rejected_feeds_str", {"news_rejected": {"feeds": "x"}}),
    ("rejected_items_str", {"news_rejected": {"feeds": {"macro": "xy"}}}),
    ("news_feed_str", {"news_feed": "not-a-list"}),
    ("news_feed_items_bad", {"news_feed": [1, "x", None]}),
]


@pytest.mark.parametrize("case_id,overrides", _BAD_ARTIFACT_CASES,
                         ids=[c[0] for c in _BAD_ARTIFACT_CASES])
def test_schema_violating_artifact_degrades_not_raises(case_id, overrides):
    vm = _empty_vm()
    vm.update(overrides)
    html = _env().get_template("news.html.j2").render(**vm)
    assert len(html) > 500
    assert "What matters now" in html          # page structure intact


def test_string_cards_release_board_shows_no_release_section():
    """cards-as-string degrades the release board out (empty), never raises."""
    vm = _empty_vm()
    vm["macro_releases"] = {"cards": "x"}
    html = _env().get_template("news.html.j2").render(**vm)
    assert "Nonfarm Payrolls" not in html      # nothing bogus rendered
    assert len(html) > 500


# --------------------------------------------------------------------------- #
# build_site render-call shape — no duplicate macro_news kwarg (with news_feed)
# --------------------------------------------------------------------------- #
# build_site.py's vm carries 'macro_news'; macro_releases/news_rejected/
# news_calibration/financial_news/news_feed are separate locals passed explicitly.
_EXPLICIT_KWARGS = ("macro_releases", "news_rejected", "news_calibration",
                    "financial_news", "news_feed")


def test_build_site_render_call_shape_no_duplicate_kwarg():
    vm = {k: v for k, v in _full_vm().items() if k not in _EXPLICIT_KWARGS}
    assert "macro_news" in vm
    render_vm = {k: v for k, v in vm.items() if k != "macro_news"}   # the W3 fix
    html = _env().get_template("news.html.j2").render(
        **render_vm,
        macro_news=dict(vm["macro_news"]),
        macro_releases=None, news_rejected=None, news_calibration=None,
        financial_news=None, news_feed=_full_vm()["news_feed"],
    )
    assert len(html) > 1000
    assert "nx-story" in html


def test_naive_duplicate_macro_news_kwarg_raises_typeerror():
    """Pins the failure mode if build_site regresses to **vm without dropping macro_news."""
    vm = {k: v for k, v in _full_vm().items() if k not in _EXPLICIT_KWARGS}
    tmpl = _env().get_template("news.html.j2")
    with pytest.raises(TypeError, match="multiple values for keyword argument 'macro_news'"):
        tmpl.render(**vm, macro_news=dict(vm["macro_news"]),
                    macro_releases=None, news_rejected=None, news_calibration=None,
                    financial_news=None, news_feed=[])
