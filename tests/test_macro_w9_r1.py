"""W9 r1 — macro.html plain-language faces, one-integer alerts, stance law, Markets nulls.

Renders templates/dashboard.html.j2 against synthetic VMs (same env as
test_dashboard_template_render) and pins the packet's frozen strings plus the
unknown/cautious default on every stance map.
"""
from __future__ import annotations

import re
from pathlib import Path

from tests.test_dashboard_template_render import _base_vm, _env

ROOT = Path(__file__).resolve().parents[1]


def _ms(**over) -> dict:
    row = {
        "color": "yellow",
        "score": 55,
        "label_en": "Caution",
        "label_zh": "谨慎",
        "headline_en": "A mixed tape.",
        "headline_zh": "盘面混杂。",
        "asof": "2026-07-04",
        "overrides": [],
        "flip_en": "",
        "flip_zh": "",
        "components": [
            {"key": "trend", "score": 50, "label_en": "Trend", "label_zh": "趋势"},
        ],
        "radar": {
            "state": "caution",
            "label_en": "Caution",
            "label_zh": "谨慎",
            "do_en": "Watch.",
            "do_zh": "观望。",
            "top_score": 55,
        },
    }
    row.update(over)
    return row


def _alert(rule="gex_flip_cross", tier="watch", **over) -> dict:
    from engine.alerts import alert_view
    row = alert_view(rule, over.pop("severity", "warn"),
                     over.pop("message", "GEX: spot crossed the gamma flip (net -31bn, spot vs flip -0.4%)"),
                     over.pop("message_zh", "GEX：现价穿越 gamma 翻转点"))
    row["tier"] = tier
    row.update(over)
    return row


def _render(mode="macro", **over) -> str:
    vm = _base_vm()
    vm.update(over)
    return _env().get_template("dashboard.html.j2").render(**vm, mode=mode)


def _face(html: str, sid: str) -> str:
    m = re.search(rf'id="{sid}"[\s\S]*?</div>\s*{{# /{sid}', html)
    if m:
        return m.group(0)
    # fallback: slice from id to the next sx-v5 / sx id
    m = re.search(rf'id="{sid}"[\s\S]{{0,8000}}', html)
    assert m, f"module {sid} missing"
    return m.group(0)


# --------------------------------------------------------------------------- #
# 1. Grey Deer — program name demoted; engine noun is capital restrictions
# --------------------------------------------------------------------------- #

def test_grey_deer_face_names_the_fact_not_the_program():
    src = (ROOT / "templates" / "_risk_envelope_band.html.j2").read_text()
    assert "No Grey Deer policy active" not in src
    assert "未启用任何 Grey Deer 政策" not in src
    assert "No capital restrictions in force" in src
    assert "当前无资金限制" in src
    # chip stays (0 active / 0 项生效)
    assert 'gde-policy-count' in src
    assert "项生效" in src


# --------------------------------------------------------------------------- #
# 2. GEX detail on the face; machine message + what_* in dlg-news
# --------------------------------------------------------------------------- #

def test_alert_face_prints_detail_not_machine_message():
    html = _render(alerts=[_alert()])
    face = html[html.find('id="sx-news-v2"'):html.find('id="sx-deep-context"')]
    assert "Options hedging just flipped from damping moves to amplifying them" in face
    assert "期权对冲由抑制波动转为放大波动" in face
    assert "GEX: spot crossed the gamma flip" not in face
    dlg = html[html.find('id="dlg-news"'):html.find('id="dlg-news"') + 12000]
    # message stays as receipt; what_* is the orphaned explanation
    assert "GEX: spot crossed the gamma flip" in dlg
    assert "Dealer gamma (GEX) measures how options hedging" in dlg


# --------------------------------------------------------------------------- #
# 3. One-integer alert count
# --------------------------------------------------------------------------- #

def test_alert_count_hero_n_equals_face_of_n():
    alerts = [
        _alert("gex_flip_cross", "watch"),
        _alert("hy_oas_widening", "act",
               message="HY OAS 1-day widening +0.50pp is 4.2 sigma",
               message_zh="HY OAS"),
        _alert("event_risk", "context",
               message="Event-risk window: CPI tomorrow",
               message_zh="事件"),
        _alert("growth_confidence_floor", "context",
               message="Growth axis confidence dropped below 40%",
               message_zh="增长"),
        _alert("sector_rs_cross_high", "context",
               message="XLI RS vs SPY crossed above 80th pctile",
               message_zh="板块"),
        _alert("circuit_breaker_open", "context",
               message="Source 'fred' marked dead after 3 consecutive failures",
               message_zh="中断"),
    ]
    html = _render(
        market_state=_ms(),
        alerts=alerts,
        macro_news={"headlines": [
            {"title": "Oracle prints a beat", "title_zh": "甲骨文超预期",
             "importance": "high", "source_name": "Reuters"},
        ], "synthesis": {}},
    )
    # Hero canonical N
    hero = re.search(
        r'class="ms-alerts"[\s\S]{0,400}?<span class="ct[^"]*">(\d+)</span>',
        html,
    )
    assert hero, "hero fired-alerts chip missing"
    n = int(hero.group(1))
    assert n == 6, f"hero N expected 6, got {n}"
    # Face labelled slice uses the same N
    assert f"need action · of {n}" in html
    assert f"条需处理 · 共 {n} 条" in html
    # slice ≤ N (act+watch + promoted event_risk = 3)
    assert "3 need action · of 6" in html
    # news row labelled, excluded from both integers
    assert "Headline" in html
    assert "头条" in html
    # footer agrees with the same pair
    assert html.count("3 need action · of 6") >= 2


# --------------------------------------------------------------------------- #
# 4. Stance maps — packet strings verbatim, unknown → cautious
# --------------------------------------------------------------------------- #

_CAUTIOUS_EN = "Watch — this read is being updated."
_CAUTIOUS_ZH = "观望——该读数更新中。"
_EV_NONE_WHY_EN = (
    "Events feed is reconnecting — re-checked nightly. "
    "The rest of this page is unaffected."
)
_EV_NONE_WHY_ZH = "事件数据源重连中——每晚重新检查。本页其余内容不受影响。"


def test_sentiment_stance_panic():
    html = _render(fear_greed={"dial": 12, "label_en": "Extreme Fear", "label_zh": "极度恐惧"})
    assert "Watch — don't chase weakness; extremes can snap back." in html
    assert "观望——不追跌，极端情绪可能快速反转。" in html


def test_sentiment_stance_fear_is_panic_lane():
    html = _render(fear_greed={"dial": 32, "label_en": "Fear", "label_zh": "恐慌"})
    assert "Watch — don't chase weakness; extremes can snap back." in html


def test_sentiment_stance_neutral():
    html = _render(fear_greed={"dial": 50, "label_en": "Neutral", "label_zh": "中性"})
    assert "Stand aside — nothing to do from this panel today." in html
    assert "暂不行动——本面板今日无需操作。" in html


def test_sentiment_stance_euphoria():
    html = _render(fear_greed={"dial": 88, "label_en": "Extreme Greed", "label_zh": "极度贪婪"})
    assert "Protect gains — stretched optimism cuts both ways." in html
    assert "保住收益——情绪过热双向都有风险。" in html


def test_sentiment_stance_greed_is_euphoria_lane():
    html = _render(fear_greed={"dial": 70, "label_en": "Greed", "label_zh": "贪婪"})
    assert "Protect gains — stretched optimism cuts both ways." in html


def test_sentiment_stance_unknown():
    html = _render(fear_greed=None)
    sent = html[html.find('id="sx-v5-sentiment"'):html.find('id="sx-v5-sector"')]
    assert _CAUTIOUS_EN in sent
    assert _CAUTIOUS_ZH in sent


def test_sector_stance_heating():
    html = _render(sector_heat={
        "heating": [{"name": "Energy", "name_zh": "能源", "rank": 1}],
        "cooling": [],
    })
    assert "Watch the heating list — rotation, not chasing." in html
    assert "关注升温板块——是轮动，不是追涨。" in html


def test_sector_stance_all_quiet():
    html = _render(sector_heat={"heating": [], "cooling": [{"name": "Utilities", "rank": 11}]})
    assert "Stand aside — no sector is running hot today." in html
    assert "暂不行动——今日无板块过热。" in html


def test_sector_stance_unknown():
    html = _render(sector_heat=None)
    sect = html[html.find('id="sx-v5-sector"'):html.find('id="sx-markets-v2"')]
    assert _CAUTIOUS_EN in sect
    assert _CAUTIOUS_ZH in sect


def test_aibrief_stance_high_n():
    html = _render(macro_news={"synthesis": {
        "high_impact_count": 4, "dominant_channel": "inflation",
        "top_tickers": [],
    }, "channel_label": {"inflation": ["inflation", "通胀"]}, "headlines": []})
    assert "Watch — don't chase headlines; let prices settle first." in html
    assert "观望——不追新闻，先等价格企稳。" in html
    assert "Dominant theme:" in html
    assert "Dominant channel:" not in html[html.find('id="sx-aibrief-v2"'):html.find('id="sx-news-v2"')]
    assert "主线：" in html


def test_aibrief_stance_theme_thread():
    html = _render(macro_news={"synthesis": {
        "high_impact_count": 2, "dominant_channel": "inflation",
        "top_tickers": [],
    }, "channel_label": {"inflation": ["inflation", "通胀"]}, "headlines": []})
    assert "Watch the inflation thread — no action needed yet." in html
    assert "关注通胀主线——暂无需操作。" in html


def test_aibrief_stance_zero():
    html = _render(macro_news={"synthesis": {
        "high_impact_count": 0, "dominant_channel": "",
        "top_tickers": [],
    }, "headlines": []})
    assert "Ignore — nothing in the news flow demands action." in html
    assert "可忽略——新闻流中无需行动事项。" in html


def test_aibrief_stance_unknown():
    html = _render(macro_news={"synthesis": {}, "headlines": []})
    brief = html[html.find('id="sx-aibrief-v2"'):html.find('id="sx-news-v2"')]
    assert _CAUTIOUS_EN in brief
    assert _CAUTIOUS_ZH in brief


def test_events_stance_n_positive():
    html = _render(macro_catalysts=[
        {"impact": "high", "label": "CPI", "label_zh": "CPI", "date": "2026-07-10"},
        {"impact": "high", "label": "FOMC", "label_zh": "FOMC", "date": "2026-07-11"},
        {"impact": "med", "label": "Claims", "label_zh": "初请", "date": "2026-07-09"},
    ])
    assert "Get ready — 2 big prints ahead; avoid adding risk right before them." in html
    assert "做好准备——前方有 2 项重磅数据，公布前不宜加仓。" in html


def test_events_stance_n_zero():
    html = _render(macro_catalysts=[])
    ev = html[html.find('id="sx-events-v2"'):html.find('id="sx-v5-fed"') if 'id="sx-v5-fed"' in html else html.find('id="sx-v5-sentiment"')]
    assert "Nothing scheduled that should change positioning this week." in ev
    assert "本周暂无应改变仓位的安排。" in ev


def test_markets_is_exempt_from_stance_law():
    """Seat ruling: Markets is a quote tape, not a signal panel."""
    html = _render()
    start = html.find('id="sx-markets-v2"')
    # Risk module is gated on market_state; the next always-present sibling is policy
    # (or aibrief). Bound the face, not the rest of the page.
    end_candidates = [html.find(s, start + 1) for s in
                      ('id="sx-risk-v2"', 'id="sx-policy-v2"', 'id="sx-aibrief-v2"')]
    end = min(i for i in end_candidates if i != -1)
    mkt = html[start:end]
    assert 'id="sx-markets-v2"' in mkt
    for banned in (
        "Watch — don't chase",
        "Stand aside",
        "Protect gains",
        "Get ready",
        "Ignore —",
        _CAUTIOUS_EN,
    ):
        assert banned not in mkt, f"Markets face leaked stance {banned!r}"


# --------------------------------------------------------------------------- #
# 5. Markets SSR skeleton, never a bare em dash
# --------------------------------------------------------------------------- #

def test_markets_ssr_is_skeleton_not_dash():
    html = _render()
    start = html.find('id="sx-markets-v2"')
    end_candidates = [html.find(s, start + 1) for s in
                      ('id="sx-risk-v2"', 'id="sx-policy-v2"', 'id="sx-aibrief-v2"')]
    end = min(i for i in end_candidates if i != -1)
    mkt = html[start:end]
    assert "mx5-mkt-price nb-px skel" in mkt
    assert 'aria-busy="true"' in mkt
    # no bare-em-dash price/delta in the strip
    assert not re.search(r'mx5-mkt-price[^>]*>—</div>', mkt)
    assert not re.search(r'mx5-mkt-delta[^>]*>—</div>', mkt)


# --------------------------------------------------------------------------- #
# 6. Regime tip null guard + tip↔module reconciliation
# --------------------------------------------------------------------------- #

def test_regime_tip_omits_weakest_support_when_row_is_absent():
    html = _render(latest={
        **_base_vm()["latest"],
        "quad": "Q3",
        "raw_quad": "Q4",
        "confidence": 0.4,
        "flip_condition": {"label_unsupported": True, "component": None},
        "quad_vector": {"transition_momentum": {}},
    }, market_state=_ms())
    # Today's axes row is on; Weakest support row is not
    assert "Today’s axes" in html or "Today's axes" in html
    # The tip must not advertise a Weakest-support row that is not rendered
    tips = re.findall(r'<span class="tip">[\s\S]*?</span></span>', html)
    joined = " ".join(tips)
    assert "Weakest support:" not in joined
    assert "最弱支撑：" not in joined or "最弱支撑读数暂缺" in joined


def test_regime_tip_null_z_uses_missing_sentence():
    html = _render(latest={
        **_base_vm()["latest"],
        "quad": "Q2",
        "confidence": 0.7,
        "flip_condition": {
            "component": "copper_gold", "axis": "growth",
            "z": None, "threshold": 1.0, "margin": 0.4,
        },
        "quad_vector": {"transition_momentum": {}},
    }, market_state=_ms())
    assert "One input didn't settle today, so the weakest-support read is off." in html
    assert "有一项输入今日未结算，最弱支撑读数暂缺。" in html
    assert "slope z —" not in html
    assert "斜率 z —" not in html


# --------------------------------------------------------------------------- #
# W9 r2 — unknown events, N==0 badge, geometry, 21/21 ZH channels, nits
# --------------------------------------------------------------------------- #

_DENIAL_EN = "No top-tier prints in the window."
_DENIAL_ZH = "窗口内无一线数据。"


def test_events_stance_unknown():
    html = _render(macro_catalysts=None)
    ev = html[html.find('id="sx-events-v2"'):html.find('id="sx-v5-fed"') if 'id="sx-v5-fed"' in html else html.find('id="sx-v5-sentiment"')]
    assert _CAUTIOUS_EN in ev
    assert _CAUTIOUS_ZH in ev
    assert _EV_NONE_WHY_EN in ev
    assert _EV_NONE_WHY_ZH in ev
    assert "mx5-ev-none-copy" in ev
    assert "Nothing scheduled that should change positioning this week." not in ev
    assert "本周暂无应改变仓位的安排。" not in ev
    assert _DENIAL_EN not in ev
    assert _DENIAL_ZH not in ev


def test_events_failed_fetch_vs_genuinely_empty():
    """Producer contract on the face: None = cautious; [] = quiet calendar."""
    failed = _render(macro_catalysts=None)
    empty = _render(macro_catalysts=[])
    failed_ev = failed[failed.find('id="sx-events-v2"'):failed.find('id="sx-v5-sentiment"')]
    empty_ev = empty[empty.find('id="sx-events-v2"'):empty.find('id="sx-v5-sentiment"')]
    assert _CAUTIOUS_EN in failed_ev
    assert _EV_NONE_WHY_EN in failed_ev
    assert _EV_NONE_WHY_ZH in failed_ev
    assert "Nothing scheduled that should change positioning this week." in empty_ev
    assert "Nothing scheduled that should change positioning this week." not in failed_ev
    assert _CAUTIOUS_EN not in empty_ev
    assert _EV_NONE_WHY_EN not in empty_ev
    assert "mx5-ev-none-copy" in failed_ev
    assert "mx5-ev-none-copy" not in empty_ev
    assert _DENIAL_EN not in failed_ev
    assert _DENIAL_ZH not in failed_ev
    assert _DENIAL_EN in empty_ev
    assert _DENIAL_ZH in empty_ev


def test_alert_badge_n_zero_is_neutral_not_amber():
    html = _render(
        alerts=[],
        macro_news={"headlines": [
            {"title": "Oracle prints a beat", "title_zh": "甲骨文超预期",
             "importance": "high", "source_name": "Reuters"},
            {"title": "Second print", "title_zh": "第二条",
             "importance": "med", "source_name": "WSJ"},
        ], "synthesis": {}},
    )
    face = html[html.find('id="sx-news-v2"'):html.find('id="sx-deep-context"')]
    assert "No alerts today" in face
    assert "今日无警报" in face
    assert "of 0" not in face
    assert "共 0 条" not in face
    # badge is the default muted chip, not the warn/amber alarm
    badge = re.search(r'<div class="mx5-card-badge"[^>]*>', face)
    assert badge, "alerts badge missing"
    assert "mx5-warn-ink" not in badge.group(0)
    assert "mx5-warn-dim" not in badge.group(0)
    assert "Headline" in face
    assert "头条" in face


def test_alert_badge_n_positive_unchanged():
    html = _render(alerts=[_alert()], macro_news={"headlines": [], "synthesis": {}})
    face = html[html.find('id="sx-news-v2"'):html.find('id="sx-deep-context"')]
    assert "1 need action · of 1" in face
    assert "1 条需处理 · 共 1 条" in face
    assert "No alerts today" not in face
    badge = re.search(r'<div class="mx5-card-badge"[^>]*>', face)
    assert badge and "mx5-warn-ink" in badge.group(0)


def test_markets_price_geometry_lives_on_the_node():
    src = (ROOT / "templates" / "dashboard.html.j2").read_text()
    m = re.search(r"body\.page-macro\.mx4-grid \.mx5-mkt-price\{([^}]+)\}", src)
    assert m, ".mx5-mkt-price rule missing"
    body = m.group(1)
    assert "min-height:1em" in body
    assert "min-width:8ch" in body
    assert "display:block" in body
    assert "min-width:4.5ch" not in src[src.find("body.page-macro.mx4-grid .mx5-mkt-price"):src.find("body.page-macro.mx4-grid .mx5-mkt-delta")]
    tok = re.search(r"body\.page-macro\.mx4-grid \.mx5-mkt-price\.dtp-token\{([^}]+)\}", src)
    assert tok, "dtp-token override on the price node missing"
    assert "font-size:19px" in tok.group(1)
    assert "text-transform:none" in tok.group(1)


def test_sector_null_keeps_its_why():
    html = _render(sector_heat=None)
    sect = html[html.find('id="sx-v5-sector"'):html.find('id="sx-markets-v2"')]
    assert _CAUTIOUS_EN in sect
    assert "Sector data — accruing from nightly log." in sect
    assert "板块数据 — 每晚积累中。" in sect


def test_sentiment_greed_label_wins_over_fear_range_dial():
    html = _render(fear_greed={"dial": 38, "label_en": "Greed", "label_zh": "贪婪"})
    sent = html[html.find('id="sx-v5-sentiment"'):html.find('id="sx-v5-sector"')]
    assert "Protect gains — stretched optimism cuts both ways." in sent
    assert "Watch — don't chase weakness; extremes can snap back." not in sent


def test_aibrief_zh_channel_twins_all_21():
    from engine.macro_news import CHANNEL_LABEL
    assert len(CHANNEL_LABEL) == 21
    missing = []
    for slug, (en, zh) in CHANNEL_LABEL.items():
        assert any("\u4e00" <= c <= "\u9fff" for c in zh), f"{slug} ZH is not Chinese: {zh!r}"
        html = _render(macro_news={
            "synthesis": {
                "high_impact_count": 2, "dominant_channel": slug, "top_tickers": [],
            },
            "headlines": [],
            # no channel_label on the payload — producer table / env global must win
        })
        brief = html[html.find('id="sx-aibrief-v2"'):html.find('id="sx-news-v2"')]
        if zh not in brief:
            missing.append(f"face:{slug}")
        if f"关注{zh}主线" not in brief:
            missing.append(f"stance:{slug}")
        if f"Watch the {en} thread" not in brief:
            missing.append(f"stance-en:{slug}")
    assert not missing, missing


def test_build_site_catalysts_init_is_none_not_empty_list():
    src = (ROOT / "scripts" / "build_site.py").read_text()
    assert "macro_catalysts, macro_news_data, macro_brief_data = None, None, None" in src
    assert "load_upcoming_catalysts" in src
    assert "macro_catalysts, macro_news_data, macro_brief_data = [], None, None" not in src


# --------------------------------------------------------------------------- #
# W9 r3 — full tri-state sweep, one-population counts, warn-on-need
# --------------------------------------------------------------------------- #

_CPI = {"impact": "high", "label": "CPI", "label_zh": "CPI", "date": "2026-07-10"}


def _slice(html: str, start: str, *ends: str) -> str:
    i = html.find(start)
    assert i != -1, f"missing {start}"
    stops = [html.find(e, i + 1) for e in ends]
    stops = [s for s in stops if s != -1]
    return html[i:(min(stops) if stops else i + 12000)]


def _dislo(**over) -> dict:
    row = {
        "dislocation_active": True,
        "verdict": "stand_aside",
        "put_state": "known",
        "put_state_reliable": True,
        "fed_put": True,
        "geo_reversibility": {"agreement": "corroborates"},
        "catalyst_narrative": {"agreement": "corroborates"},
    }
    row.update(over)
    return row


def test_hero_next_event_chip_tri_state():
    """7543: populated chip only; None and [] print no next-event chip."""
    none_html = _render(market_state=_ms(), macro_catalysts=None)
    empty_html = _render(market_state=_ms(), macro_catalysts=[])
    full_html = _render(market_state=_ms(), macro_catalysts=[_CPI])
    none_hero = _slice(none_html, 'class="mx2-alerts-row"', 'id="sx-evidence"')
    empty_hero = _slice(empty_html, 'class="mx2-alerts-row"', 'id="sx-evidence"')
    full_hero = _slice(full_html, 'class="mx2-alerts-row"', 'id="sx-evidence"')
    assert "CPI" not in none_hero
    assert "CPI" not in empty_hero
    assert "CPI" in full_hero
    assert _DENIAL_EN not in none_hero
    assert _CAUTIOUS_EN not in none_hero  # chip is omitted, not a cautious claim


def test_wtd_event_row_tri_state():
    """8642: None does not pick an event or claim an empty calendar."""
    none_wtd = _slice(_render(macro_catalysts=None), 'id="sx-evidence"', 'id="sx-events-v2"')
    empty_wtd = _slice(_render(macro_catalysts=[]), 'id="sx-evidence"', 'id="sx-events-v2"')
    full_wtd = _slice(_render(macro_catalysts=[_CPI]), 'id="sx-evidence"', 'id="sx-events-v2"')
    assert "CPI: expect noise" not in none_wtd
    assert "CPI: expect noise" not in empty_wtd
    assert "CPI: expect noise" in full_wtd
    assert _DENIAL_EN not in none_wtd


def _first_wnx_card(html: str) -> str:
    face = _slice(html, 'id="sx-deep-context"', 'id="dlg-evidence"', 'id="dlg-events"')
    m = re.search(r'<a class="wnx-card"[\s\S]*?</a>', face)
    assert m, "wnx-card missing"
    return m.group(0)


def test_where_next_week_ahead_tri_state():
    """11928: None → cautious card; [] → Macro Weather fallback; list → event."""
    none_card = _first_wnx_card(_render(macro_catalysts=None))
    empty_card = _first_wnx_card(_render(macro_catalysts=[]))
    full_card = _first_wnx_card(_render(macro_catalysts=[_CPI]))
    assert _CAUTIOUS_EN in none_card
    assert "Macro Weather" not in none_card
    assert _DENIAL_EN not in none_card
    assert "Macro Weather" in empty_card
    assert _CAUTIOUS_EN not in empty_card
    assert "CPI" in full_card


def test_dlg_events_tri_state():
    """12238/12293/12365/12386: None is cautious; [] is the empty-data denial."""
    none_dlg = _slice(_render(macro_catalysts=None), 'id="dlg-events"', 'id="dlg-markets"')
    empty_dlg = _slice(_render(macro_catalysts=[]), 'id="dlg-events"', 'id="dlg-markets"')
    full_dlg = _slice(_render(macro_catalysts=[_CPI]), 'id="dlg-events"', 'id="dlg-markets"')
    assert _CAUTIOUS_EN in none_dlg
    assert _EV_NONE_WHY_EN in none_dlg
    assert _EV_NONE_WHY_ZH in none_dlg
    assert "No events data available." not in none_dlg
    assert "暂无事件数据。" not in none_dlg
    assert _DENIAL_EN not in none_dlg
    assert "No events data available." in empty_dlg
    assert "暂无事件数据。" in empty_dlg
    assert _CAUTIOUS_EN not in empty_dlg
    assert _EV_NONE_WHY_EN not in empty_dlg
    assert "CPI" in full_dlg
    assert "This Week" in full_dlg


def test_stocks_band_tristate_source_pin_unreachable_code():
    """Source-string pin on unreachable stocks week-ahead band (not a render).

    The lower-fold band sits inside the macro-only regime-radar wrapper, so no
    stocks-mode (or macro-mode) full-page render emits it. The tri-state
    `is not none` guards are verified by grepping the template fragment, never
    by a rendered page.
    """
    src = (ROOT / "templates" / "dashboard.html.j2").read_text()
    start = src.find("{# Week ahead — original lower-fold band")
    end = src.find("{# Market heatmap — moved to MARKETS tray", start)
    assert start != -1 and end != -1
    frag = src[start:end]
    assert "mode == 'stocks' and ((macro_catalysts is not none and macro_catalysts)" in frag
    assert "{% if macro_catalysts is not none and macro_catalysts %}" in frag
    assert "{% if macro_catalysts %}" not in frag.replace(
        "{% if macro_catalysts is not none and macro_catalysts %}", ""
    )


def test_news_calendar_tri_state():
    """news.html.j2:40 — None is cautious; [] is the empty-window denial."""
    from tests.test_news_page_render import _empty_vm, _env as _news_env

    def _news(**over) -> str:
        vm = _empty_vm()
        vm.update(over)
        return _news_env().get_template("news.html.j2").render(**vm)

    none_html = _news(macro_catalysts=None)
    empty_html = _news(macro_catalysts=[])
    full_html = _news(macro_catalysts=[_CPI])
    assert _CAUTIOUS_EN in none_html
    assert "No scheduled events in the window." not in none_html
    assert "窗口内暂无排定事件。" not in none_html
    assert "No scheduled events in the window." in empty_html
    assert "窗口内暂无排定事件。" in empty_html
    assert _CAUTIOUS_EN not in empty_html
    assert "CPI" in full_html
    assert "No scheduled events in the window." not in full_html


def test_dislocation_one_population_counts():
    """Hero N == dialog row count == face 'of N' when a dislocation is live."""
    latest = dict(_base_vm()["latest"])
    latest["dislocation"] = _dislo()
    html = _render(market_state=_ms(), alerts=[], latest=latest)
    hero = re.search(
        r'class="ms-alerts"[\s\S]{0,400}?<span class="ct[^"]*">(\d+)</span>',
        html,
    )
    assert hero, "hero fired-alerts chip missing"
    n = int(hero.group(1))
    assert n == 1, f"hero N expected 1, got {n}"
    face = _slice(html, 'id="sx-news-v2"', 'id="sx-deep-context"')
    assert f"of {n}" in face
    assert f"共 {n} 条" in face
    assert "0 need action · of 1" in face
    dlg = _slice(html, 'id="dlg-news"', 'id="dlg-deep-context"')
    n_dlg = dlg.count("data-al-row")
    assert n_dlg == n
    assert "Selling has turned stressed" in dlg
    assert "抛售已转为压力状态" in dlg

    html2 = _render(market_state=_ms(), alerts=[_alert()], latest=latest)
    hero2 = re.search(
        r'class="ms-alerts"[\s\S]{0,400}?<span class="ct[^"]*">(\d+)</span>',
        html2,
    )
    n2 = int(hero2.group(1))
    assert n2 == 2
    face2 = _slice(html2, 'id="sx-news-v2"', 'id="sx-deep-context"')
    assert "1 need action · of 2" in face2
    dlg2 = _slice(html2, 'id="dlg-news"', 'id="dlg-deep-context"')
    n2_dlg = dlg2.count("data-al-row")
    assert n2_dlg == n2

    html3 = _render(
        market_state=_ms(),
        alerts=[_alert(), _alert("hy_oas_widening", "act")],
        latest=latest,
    )
    hero3 = re.search(
        r'class="ms-alerts"[\s\S]{0,400}?<span class="ct[^"]*">(\d+)</span>',
        html3,
    )
    n3 = int(hero3.group(1))
    assert n3 == 3
    face3 = _slice(html3, 'id="sx-news-v2"', 'id="sx-deep-context"')
    assert "2 need action · of 3" in face3
    dlg3 = _slice(html3, 'id="dlg-news"', 'id="dlg-deep-context"')
    assert dlg3.count("data-al-row") == n3


def test_alert_badge_need_zero_total_positive_is_neutral():
    """(need=0, total=1): labelled slice, no warn tokens."""
    latest = dict(_base_vm()["latest"])
    latest["dislocation"] = _dislo()
    html = _render(market_state=_ms(), alerts=[], latest=latest)
    face = _slice(html, 'id="sx-news-v2"', 'id="sx-deep-context"')
    assert "0 need action · of 1" in face
    assert "0 条需处理 · 共 1 条" in face
    assert "No alerts today" not in face
    badge = re.search(r'<div class="mx5-card-badge"[^>]*>', face)
    assert badge, "alerts badge missing"
    assert "mx5-warn-ink" not in badge.group(0)
    assert "mx5-warn-dim" not in badge.group(0)


def test_load_upcoming_catalysts_docstring_names_builder_exception():
    src = (ROOT / "engine" / "macro_news.py").read_text()
    start = src.find("def load_upcoming_catalysts")
    doc = src[start:start + 900]
    assert "builder exception" in doc
    assert "None on fetch failure" not in doc
    assert "no network fetch" in doc.lower() or "There is no network fetch" in doc


def test_sector_null_why_uses_mx_empty_pair():
    html = _render(sector_heat=None)
    sect = _slice(html, 'id="sx-v5-sector"', 'id="sx-markets-v2"')
    assert 'class="mx-empty"' in sect
    assert "mx-empty-why" in sect
    assert 'style="font-size:12px;color:var(--ink-3);margin-top:6px"' not in sect

