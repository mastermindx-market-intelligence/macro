"""Render and inherited consequence-contract tests for the News cockpit.

The current design uses a read-stable feed and a story workspace. Legacy
consequence semantics and rendering safety remain acceptance requirements.

Historical test intent:

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
    assert "News intelligence" in html


def test_empty_vm_renders_without_exception():
    html = _render_empty()
    assert len(html) > 500
    assert "News intelligence" in html          # header always renders
    assert "quiet" in html.lower()             # empty-feed state










def _css_rule(html: str, selector: str) -> str:
    matches = re.findall(re.escape(selector) + r"\{([^}]*)\}", html, re.S)
    assert matches, f"missing CSS rule for {selector}"
    return "\n".join(matches)
















def test_calendar_renders_catalysts_and_strip():
    html = _render_full()
    assert "FOMC decision" in html or "FOMC决议" in html
    assert "Jobless claims" in html or "初请失业金" in html




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




def test_bilingual_spans_present():
    html = _render_full()
    assert 'class="l-en"' in html and 'class="l-zh"' in html
    assert "新闻情报" in html                    # zh title span emitted


def test_disclaimer_renders():
    html = _render_full()
    assert "informational purposes" in html.lower()


def test_consequence_section_is_single_column_not_nx_cols():
    """MAJOR 4 ruling: #nxConsequence is a full-width single column, not nx-cols."""
    html = _render_full()
    assert 'class="nx-consequence" id="nxConsequence"' in html
    assert 'class="nx-cols" id="nxConsequence"' not in html
    # The releases board may still use nx-cols; only this section left that grid.
    assert 'id="ndImpact"' in html
    assert '.nd-dialog .nx-rel-grid' in html
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
            },
            {
                "event_id": "cev-b",
                "event_time": "2026-09-06",
                "event_time_en": "6 Sep 2026",
                "event_time_zh": "2026年9月6日",
                "title_en": "BBB reported earnings",
                "title_zh": "BBB公布业绩",
                "direct_tickers": ["BBB"],
            },
            {
                "event_id": "cev-c",
                "event_time": "2026-09-05",
                "event_time_en": "5 Sep 2026",
                "event_time_zh": "2026年9月5日",
                "title_en": "CCC reported earnings",
                "title_zh": "CCC公布业绩",
                "direct_tickers": ["CCC"],
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


def test_row_without_direct_tickers_never_prints_named():
    """F05-017 R2 D3: a row with ``direct_tickers == []`` (closed-key
    contract; second-order events stripped per Q1=strip) renders the
    ticker badge as absent in BOTH locales — never the "Also watching"
    / "同时关注" branch, never "Named" / "点名", never "No named ticker"
    / "未点名标的"."""
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
            "title_en": "A regime event without series title",
            "title_zh": "宏观环境事件（无系列标题）",
            "direct_tickers": [],
            "note_en": None,
            "note_zh": None,
        }],
    }
    html = _env().get_template("news.html.j2").render(**vm)
    start = html.index('id="nxConsequence"')
    end = html.index("</section>", start)
    section = html[start:end]
    assert "Also watching" not in section
    assert "同时关注" not in section
    # Direct-ticker absence is honest: no "Named" / "点名" chip.
    assert '<span class="l-en">Named</span>' not in section
    assert '<span class="l-zh">点名</span>' not in section
    # The dead branch is gone.
    assert "No named ticker" not in section
    assert "未点名标的" not in section


def test_row_with_direct_tickers_prints_named():
    """F05-017 R2 D3: the companion to the test above — a direct-ticker
    row renders the "Named" / "点名" chip in BOTH locales."""
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
            "event_id": "cev-nvda",
            "event_time": "2026-09-07",
            "event_time_en": "7 Sep 2026",
            "event_time_zh": "2026年9月7日",
            "title_en": "NVDA reported earnings",
            "title_zh": "NVDA公布业绩",
            "direct_tickers": ["NVDA"],
            "note_en": None,
            "note_zh": None,
        }],
    }
    html = _env().get_template("news.html.j2").render(**vm)
    start = html.index('id="nxConsequence"')
    end = html.index("</section>", start)
    section = html[start:end]
    assert '<span class="l-en">Named</span>' in section
    assert '<span class="l-zh">点名</span>' in section
    assert "NVDA" in section


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
    assert "News intelligence" in html          # page structure intact


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
    assert 'class="nd-row"' in html


def test_naive_duplicate_macro_news_kwarg_raises_typeerror():
    """Pins the failure mode if build_site regresses to **vm without dropping macro_news."""
    vm = {k: v for k, v in _full_vm().items() if k not in _EXPLICIT_KWARGS}
    tmpl = _env().get_template("news.html.j2")
    with pytest.raises(TypeError, match="multiple values for keyword argument 'macro_news'"):
        tmpl.render(**vm, macro_news=dict(vm["macro_news"]),
                    macro_releases=None, news_rejected=None, news_calibration=None,
                    financial_news=None, news_feed=[])


# Session D collision integration: locale/search/gated-state defects recovered
# from the frozen Web Chat UIUX lane and composed into the canonical #7591 carrier.





























# --------------------------------------------------------------------------- #
# F05 per-family inspection uses the existing producer and card contract.
def _family_inspection_surface():
    from engine.chronicle import impact, schema
    events = []
    for i in range(6):
        events.append(schema.new_event(
            id=schema.make_id("earnings", f"inspect-{i}", "2026-09-07"),
            ts="2026-09-07T00:00:00Z", date="2026-09-07", source="earnings",
            source_ref=f"inspect-{i}", kind="earnings", title="Raw title stays private",
            facts=[], tickers=[f"E{i}"], themes=[], weight_hint=1,
            links=schema.make_links(site="/x.html")))
    events.append(schema.new_event(
        id=schema.make_id("macro_release", "inspect-macro", "2026-09-07"),
        ts="2026-09-07T00:00:00Z", date="2026-09-07", source="macro_release",
        source_ref="inspect-macro", kind="print", title="Macro print: claims = 206",
        facts=[], tickers=[], themes=[], weight_hint=1,
        links=schema.make_links(site="/x.html")))
    return impact.glance_consequence_surface(events, limit=1)


def test_family_inspection_exposes_capped_records_and_typed_empty_sections():
    vm = _full_vm()
    vm["chronicle_impact"] = _family_inspection_surface()
    html = _env().get_template("news.html.j2").render(**vm)
    section = html.split('id="nxConsequence"', 1)[1].split("</section>", 1)[0]
    assert section.count('class="nx-depth nx-family"') == 6
    assert 'class="nx-depth nx-family" open' not in section
    assert "Browse by event type" in section and "按事件类型查看" in section
    assert "Showing 4 of 6 records" in section and "显示6条中的4条" in section
    assert "No recorded events of this type in this window." in section
    assert "Recorded events do not name a market exposure." in section
    assert "该时段没有此类已记录事件。" in section
    assert "已记录事件未点名市场敞口。" in section
    earnings = next(v for v in vm["chronicle_impact"]["family_views"] if v["family"] == "earnings")
    assert len(earnings["rows"]) == 4
    for row in earnings["rows"]:
        for ticker in row["direct_tickers"]:
            assert f'href="stock.html#{ticker}"' in section
    assert "Raw title stays private" not in section
    assert "prophet_ledger" not in section


def test_family_inspection_absent_for_unavailable_legacy_payload():
    vm = _full_vm()
    vm["chronicle_impact"] = {"rows": [], "reason_en": "Source unavailable."}
    html = _env().get_template("news.html.j2").render(**vm)
    assert 'class="nx-depth nx-family"' not in html
    assert "Source unavailable." in html


# F05-017 family_tally tip + closed-key row guards
# --------------------------------------------------------------------------- #
from engine.chronicle import impact as _impact_mod  # R5 — use the engine's
                                                       # tip output, not a mirror.


def _ci_with_rows(extra_rows=None, tally=None, **overrides):
    base_tally = tally if tally is not None else [
        {"family": "research_vault", "label_en": "Research notes",
         "label_zh": "研究纪要", "state": "no_events", "in_window": 0,
         "named": 0, "shown": 0},
        {"family": "macro_release", "label_en": "Economic data",
         "label_zh": "经济数据", "state": "no_events", "in_window": 0,
         "named": 0, "shown": 0},
        {"family": "earnings", "label_en": "Earnings reports",
         "label_zh": "业绩公告", "state": "named", "in_window": 3,
         "named": 1, "shown": 1},
        {"family": "earnings_call", "label_en": "Earnings calls",
         "label_zh": "业绩电话会", "state": "named", "in_window": 2,
         "named": 2, "shown": 2},
        {"family": "regime_flip", "label_en": "Macro backdrop shifts",
         "label_zh": "宏观环境转向", "state": "no_events", "in_window": 0,
         "named": 0, "shown": 0},
        {"family": "risk_band", "label_en": "Risk radar shifts",
         "label_zh": "风险雷达变化", "state": "no_events", "in_window": 0,
         "named": 0, "shown": 0},
    ]
    # R5: the render test imports the engine's tip formatter rather than
    # mirroring it. Any change to R1 punctuation / R2 pluralization shows
    # up in BOTH this test path and the engine's own tip test.
    tip_en, tip_zh = _impact_mod.build_family_tally_tip(base_tally)
    base = {
        "stance_en": "Recent market events and the names they touch — shown only when an event maps to a named exposure.",
        "stance_zh": "近期市场事件及其涉及的标的——仅在事件对应到明确标的时显示。",
        "reason_en": None,
        "reason_zh": None,
        "empty_kind": None,
        "window_label_en": "Events from 31 Aug to 7 Sep 2026",
        "window_label_zh": "2026年8月31日至9月7日的事件",
        "families": {"earnings": 1},
        "family_tally": base_tally,
        "family_tally_tip_en": tip_en,
        "family_tally_tip_zh": tip_zh,
        "rows": [{
            "event_id": "cev-aapl", "event_time": "2026-09-07",
            "event_time_en": "7 Sep 2026", "event_time_zh": "2026年9月7日",
            "title_en": "AAPL reported earnings", "title_zh": "AAPL公布业绩",
            "direct_tickers": ["AAPL"], "note_en": None, "note_zh": None,
        }],
    }
    if extra_rows is not None:
        base["rows"] = extra_rows
    base.update(overrides)
    if "family_tally" in overrides or tally is not None:
        # If caller overrode tally, recompute via the engine's formatter.
        base["family_tally_tip_en"], base["family_tally_tip_zh"] = (
            _impact_mod.build_family_tally_tip(base["family_tally"])
        )
    return base


def test_family_tally_tip_is_lens_q_button_with_both_locale_attrs():
    """F05-017: the family_tally trigger is a <button.lens-q> with both data-tip-*."""
    vm = _full_vm()
    vm["chronicle_impact"] = _ci_with_rows()
    html = _env().get_template("news.html.j2").render(**vm)
    start = html.index('id="nxConsequence"')
    end = html.index("</section>", start)
    section = html[start:end]
    assert '<button type="button" class="lens-q"' in section
    m = re.search(
        r'<button type="button" class="lens-q"\s+aria-label="([^"]+)"\s+data-tip-en="([^"]+)"\s+data-tip-zh="([^"]+)">\?</button>',
        section,
    )
    assert m, section
    aria, tip_en, tip_zh = m.group(1), m.group(2), m.group(3)
    assert aria == tip_en, "aria-label must mirror tip's aria-label"
    assert tip_en.startswith("This week by event type")
    assert tip_zh.startswith("本周按事件类型")
    assert tip_en.endswith("Cards show only events that name a stock.")
    assert tip_zh.endswith("卡片仅展示点名的个股事件。")
    # Per-family state phrases present in both locales.
    assert "Earnings reports (1/3):" in section
    assert "业绩公告" in section
    assert "Earnings calls" in section
    assert "业绩电话会" in section
    assert "Research notes" in section
    assert "研究纪要" in section
    assert "Economic data" in section
    assert "经济数据" in section
    assert "Macro backdrop shifts" in section
    assert "宏观环境转向" in section
    assert "Risk radar shifts" in section
    assert "风险雷达变化" in section


def test_family_tally_tip_no_raw_family_slug_in_section_or_tip():
    """F05-017: raw family keys (earnings_call / macro_release / etc.) never
    appear as visible text or inside any data-tip-* attribute."""
    vm = _full_vm()
    vm["chronicle_impact"] = _ci_with_rows()
    html = _env().get_template("news.html.j2").render(**vm)
    start = html.index('id="nxConsequence"')
    end = html.index("</section>", start)
    section = html[start:end]
    for slug in ("earnings_call", "macro_release", "regime_flip", "risk_band",
                 "research_vault", "prophet_ledger"):
        assert slug not in section, f"raw family slug leaked: {slug!r}"


def test_family_tally_tip_omitted_when_tally_missing():
    """F05-017: the build-site fallback dict lacks family_tally; the trigger
    must be omitted (NOT a broken empty button)."""
    vm = _full_vm()
    vm["chronicle_impact"] = {
        "stance_en": "Recent market events and the names they touch — shown only when an event maps to a named exposure.",
        "stance_zh": "近期市场事件及其涉及的标的——仅在事件对应到明确标的时显示。",
        "reason_en": None,
        "reason_zh": None,
        "empty_kind": None,
        "window_label_en": "Events from 31 Aug to 7 Sep 2026",
        "window_label_zh": "2026年8月31日至9月7日的事件",
        # NO family_tally — this is the fallback dict shape.
        "families": {"earnings": 1},
        "rows": [{
            "event_id": "cev-aapl", "event_time": "2026-09-07",
            "event_time_en": "7 Sep 2026", "event_time_zh": "2026年9月7日",
            "title_en": "AAPL reported earnings", "title_zh": "AAPL公布业绩",
            "direct_tickers": ["AAPL"], "note_en": None, "note_zh": None,
        }],
    }
    html = _env().get_template("news.html.j2").render(**vm)
    start = html.index('id="nxConsequence"')
    end = html.index("</section>", start)
    section = html[start:end]
    assert '<button type="button" class="lens-q"' not in section
    assert "data-tip-en" not in section


def test_family_tally_tip_full_width_zh_punctuation():
    """F05-017 R1: ZH segments use full-width U+FF08 / U+FF09 parens and
    U+FF1A colon; segments joined with U+FF1B (；). EN uses ASCII with
    "; " joins and ". " before the close. The EN-side aria-label mirrors
    tip_en verbatim per the sibling idiom (``bonds.html.j2:5``)."""
    vm = _full_vm()
    vm["chronicle_impact"] = _ci_with_rows()
    html = _env().get_template("news.html.j2").render(**vm)
    start = html.index('id="nxConsequence"')
    end = html.index("</section>", start)
    section = html[start:end]
    m = re.search(
        r'data-tip-en="([^"]+)"\s+data-tip-zh="([^"]+)"',
        section,
    )
    assert m, section
    tip_en = m.group(1)
    tip_zh = m.group(2)
    # ZH: full-width parens + colon inside each segment.
    assert "（" in tip_zh
    assert "）" in tip_zh
    assert "：" in tip_zh
    # ZH segments joined by U+FF1B.
    assert "；" in tip_zh
    # ZH close preceded by full-width period (U+3002).
    assert "。卡片仅展示点名的个股事件。" in tip_zh
    # EN: ASCII parens + colon, joined with "; ", close preceded by ". ".
    assert "; " in tip_en
    assert ". Cards show only events that name a stock." in tip_en
    # R2 plurals: with named=1, EN shows "1 name a stock" (singular).
    assert "1 name a stock" in tip_en
    assert "1 names a stock" not in tip_en


def test_family_tally_tip_omitted_on_newest_200_fallback_window():
    """F05-017 R8: window_mode == newest_200_fallback emits NO tip — the
    ``family_tally_tip_en/zh`` keys are empty strings, the template renders
    no ``.lens-q`` button, and there is no ``data-tip-en`` attribute.
    """
    vm = _full_vm()
    vm["chronicle_impact"] = _ci_with_rows(
        window_mode="newest_200_fallback",
        window_label_en="Latest 200 recorded events",
        window_label_zh="最近记录的200个事件",
        family_tally_tip_en="",
        family_tally_tip_zh="",
    )
    html = _env().get_template("news.html.j2").render(**vm)
    start = html.index('id="nxConsequence"')
    end = html.index("</section>", start)
    section = html[start:end]
    assert '<button type="button" class="lens-q"' not in section
    assert "data-tip-en" not in section


def test_consequence_section_no_calibrated_causal_or_market_feed():
    """F05-017 / F10 NO-CALIBRATED-FIELD: row keys never include calibrated_* /
    causal_label or second_order_*; the section never prints them; Market Feed
    (the explicitly-unserved alias) is gone too."""
    template = (ROOT / "templates" / "news.html.j2").read_text(encoding="utf-8")
    for forbidden in (
        "calibrated_impact", "calibrated_impact_reason", "causal_label",
        "second_order_tickers", "second_order_truncated",
        "second_order_candidate_count", "second_order_dropped_count",
        "Market Feed",
    ):
        assert forbidden not in template, f"template leaks {forbidden!r}"
    vm = _full_vm()
    vm["chronicle_impact"] = _ci_with_rows()
    html = _env().get_template("news.html.j2").render(**vm)
    start = html.index('id="nxConsequence"')
    end = html.index("</section>", start)
    section = html[start:end]
    for forbidden in (
        "calibrated", "causal", "Market Feed", "Also watching", "同时关注",
    ):
        assert forbidden not in section, f"section leaks {forbidden!r}"


def test_consequence_nx_sub_line_count_at_most_three_with_tip():
    """F05-017: the section still has <= 3 stacked .nx-sub lines; the lens-q
    trigger is appended to the window-label line, not as a 4th stacked line."""
    vm = _full_vm()
    vm["chronicle_impact"] = _ci_with_rows()
    html = _env().get_template("news.html.j2").render(**vm)
    start = html.index('id="nxConsequence"')
    end = html.index("</section>", start)
    section = html[start:end]
    nx_sub_count = section.count('<p class="nx-sub"')
    assert nx_sub_count <= 3, f"got {nx_sub_count} nx-sub lines"
    assert '<button type="button" class="lens-q"' in section


def test_consequence_honest_empty_all_families_fixture_in_en_and_zh():
    """F05-017: an all-families fixture (macro / regime / risk / research / etc.,
    ticker-less) renders the typed empty plus a tip naming each family's
    state in plain words, in both EN and ZH."""
    vm = _full_vm()
    tally = [
        {"family": "research_vault", "label_en": "Research notes",
         "label_zh": "研究纪要", "state": "none_named", "in_window": 4,
         "named": 0, "shown": 0},
        {"family": "macro_release", "label_en": "Economic data",
         "label_zh": "经济数据", "state": "none_named", "in_window": 2,
         "named": 0, "shown": 0},
        {"family": "earnings", "label_en": "Earnings reports",
         "label_zh": "业绩公告", "state": "no_events", "in_window": 0,
         "named": 0, "shown": 0},
        {"family": "earnings_call", "label_en": "Earnings calls",
         "label_zh": "业绩电话会", "state": "no_events", "in_window": 0,
         "named": 0, "shown": 0},
        {"family": "regime_flip", "label_en": "Macro backdrop shifts",
         "label_zh": "宏观环境转向", "state": "none_named", "in_window": 1,
         "named": 0, "shown": 0},
        {"family": "risk_band", "label_en": "Risk radar shifts",
         "label_zh": "风险雷达变化", "state": "no_events", "in_window": 0,
         "named": 0, "shown": 0},
    ]
    tip_en, tip_zh = _impact_mod.build_family_tally_tip(tally)
    vm["chronicle_impact"] = {
        "stance_en": None,
        "stance_zh": None,
        "reason_en": "No event with a named market exposure in the last 7 days.",
        "reason_zh": "近7天没有带明确市场敞口的事件。",
        "empty_kind": "no_named_exposure",
        "window_label_en": "Events from 31 Aug to 7 Sep 2026",
        "window_label_zh": "2026年8月31日至9月7日的事件",
        "families": {},
        "family_tally": tally,
        "family_tally_tip_en": tip_en,
        "family_tally_tip_zh": tip_zh,
        "rows": [],
    }
    html = _env().get_template("news.html.j2").render(**vm)
    start = html.index('id="nxConsequence"')
    end = html.index("</section>", start)
    section = html[start:end]
    # Typed empty visible in BOTH locales.
    assert "No event with a named market exposure in the last 7 days." in section
    assert "近7天没有带明确市场敞口的事件。" in section
    assert "nx-empty-lead" in section
    # Tip is present, naming each family in plain words in both locales.
    m = re.search(
        r'<button type="button" class="lens-q"\s+aria-label="([^"]+)"\s+data-tip-en="([^"]+)"\s+data-tip-zh="([^"]+)">\?</button>',
        section,
    )
    assert m, section
    tip_en, tip_zh = m.group(2), m.group(3)
    # R4 — single-string assertion per label, not a disjunctive chain.
    assert "Research notes (0/4): 4 events, none name a single stock" in tip_en
    assert "Economic data (0/2): 2 events, none name a single stock" in tip_en
    assert "Earnings reports (0/0): no events this week" in tip_en
    assert "Earnings calls (0/0): no events this week" in tip_en
    assert "Macro backdrop shifts (0/1): 1 event, none name a single stock" in tip_en
    assert "Risk radar shifts (0/0): no events this week" in tip_en
    # ZH labels (full-width parens + colon).
    assert "研究纪要（0/4）：4个事件，均未点名个股" in tip_zh
    assert "经济数据（0/2）：2个事件，均未点名个股" in tip_zh
    assert "业绩公告（0/0）：本周无事件" in tip_zh
    assert "业绩电话会（0/0）：本周无事件" in tip_zh
    assert "宏观环境转向（0/1）：1个事件，均未点名个股" in tip_zh
    assert "风险雷达变化（0/0）：本周无事件" in tip_zh
    # Raw family slugs never appear anywhere in the section.
    for slug in ("earnings_call", "macro_release", "regime_flip", "risk_band",
                 "research_vault", "prophet_ledger"):
        assert slug not in section, f"raw family slug leaked: {slug!r}"



def test_current_cockpit_controls_and_preserved_depth_have_real_destinations():
    html = _render_full()
    for identity in ("newsDesk", "ndFeedPanel", "ndDetail", "ndFilters", "ndCalendar", "ndImpact", "ndWorkspace"):
        assert f'id="{identity}"' in html
    assert 'href="calendar.html"' not in html
    assert 'data-open-panel="ndCalendar"' in html
    assert 'data-open-panel="ndImpact"' in html
    assert 'aria-controls="ndFeedPanel"' in html
    assert 'id="ndSavedStoriesMobile"' in html


def test_seed_is_script_safe_and_server_rows_escape_source_text():
    import json
    vm = _empty_vm()
    vm["news_feed"] = [_feed_item('<img src=x onerror=alert(1)> </script>')]
    vm["news_feed"][0]["url"] = "javascript:alert(1)"
    html = _env().get_template("news.html.j2").render(**vm)
    seed = re.search(r'<script type="application/json" id="ndSeed">(.*?)</script>', html, re.S).group(1)
    assert json.loads(seed)["stories"][0]["title"].startswith("<img")
    assert "<img src=x" not in html
    assert 'href="javascript:alert(1)"' not in html
    assert "\\u003c/script\\u003e" in seed


def test_source_rows_have_no_six_item_cap_and_progressive_fallback_is_bounded():
    vm = _empty_vm()
    vm["news_feed"] = [_feed_item(f"Report {i}") for i in range(50)]
    html = _env().get_template("news.html.j2").render(**vm)
    feed = html.split('id="ndFeed">')[1].split('</ol>')[0]
    assert feed.count('class="nd-row"') == 30
    assert 'id="ndMore"' in html


def test_release_numbers_require_a_declared_unit():
    vm = _full_vm()
    html = _env().get_template("news.html.j2").render(**vm)
    calendar = html.split('id="ndCalendar"')[1].split('</dialog>')[0]
    assert "Nonfarm Payrolls" in calendar
    assert "147000.0" not in calendar
    vm["macro_releases"]["cards"][0]["unit"] = "persons"
    html = _env().get_template("news.html.j2").render(**vm)
    assert "147000.0 persons" in html


def test_page_width_and_mobile_dialog_are_scoped_to_news():
    css = (ROOT / "templates/news_desk.css").read_text()
    assert "body:has(.news-desk)" in css
    assert "grid-template-columns:174px minmax(400px,1fr)" in css
    assert '.nd-detail[data-open="true"]' in css
    assert "prefers-reduced-motion" in css
    assert '.nd-dialog [hidden]{display:none!important}' in css
    assert not re.search(r'\.site-nav\s*\{', css)


@pytest.mark.parametrize("asset", ["news_desk.js", "news_company.js", "news_research.js", "news_desk.css"])
def test_committed_news_page_contains_current_canonical_asset(asset):
    # Caddy serves the committed page, not this suite's freshly rendered VM.
    # An old inline asset must therefore fail even when source-only DOM tests pass.
    source = (ROOT / "templates" / asset).read_text(encoding="utf-8").strip()
    page = (ROOT / "site" / "news.html").read_text(encoding="utf-8")
    assert source and page.count(source) == 1, f"stale or duplicated committed News asset: {asset}"
