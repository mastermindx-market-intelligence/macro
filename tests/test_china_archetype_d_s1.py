"""China dashboard publication contract.

The filename is intentionally retained because .github/ci/legacy-jobs.yml already
owns it; renaming the suite would turn this urgent UI restoration into a global CI
authority change. The contract was repurposed on 2026-09-19 after Chairman direction:
the pre-#7054 deep China macro dashboard is the published default. Archetype-D remains
recoverable in #7054 and its evidence corpus, but its six-block L1 compression is not
the production composition until separately matured and approved.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TPL = (ROOT / "templates" / "china.html.j2").read_text(encoding="utf-8")

def test_deep_dashboard_rows_are_the_published_macro_composition() -> None:
    for marker in (
        "ROW 1: What To Do + Upcoming Events",
        "ROW 2: Pullback Risk / Top Stocks + Sentiment + Sector Temperature",
        "ROW 3: Policy Monitor + Connect Flows + Macro News",
        "ROW 4: Property + AI Brief + Alerts Centre",
    ):
        assert marker in TPL


def test_deep_dashboard_cards_are_present_at_l1() -> None:
    for marker in (
        "{{ t('Market Sentiment','市场情绪') }}",
        "{{ t('Policy Monitor','政策监控') }}",
        "{{ t('Connect Flows','互联通资金') }}",
        "{{ t('Macro News','宏观新闻') }}",
    ):
        assert marker in TPL


def test_deep_dashboard_keeps_major_clickthrough_dialogs() -> None:
    for dialog_id in (
        "cnx-dlg-playbook",
        "cnx-dlg-events",
        "cnx-dlg-risk",
        "cnx-dlg-sentiment",
        "cnx-dlg-sector",
        "cnx-dlg-policy",
        "cnx-dlg-flows",
        "cnx-dlg-news",
        "cnx-dlg-property",
        "cnx-dlg-aibrief",
        "cnx-dlg-alerts",
    ):
        assert dialog_id in TPL


def test_dashboard_header_keeps_effective_date_visible() -> None:
    assert (
        '<div class="cnx-secbar"><b>{{ t(\'CHINA DASHBOARD\',\'中国看板\') }}</b>'
        "<span>{{ latest.date }}</span></div>"
    ) in TPL


def test_archetype_d_six_block_l1_is_not_the_published_default() -> None:
    for marker in (
        "L1-2 · What to do",
        "L1-3 · What changed",
        "L1-4 · Why — four drivers",
        "L1-5 · What we're watching",
        "L1-6 · Go deeper",
    ):
        assert marker not in TPL


def test_good_archetype_d_glance_patterns_are_synthesized_without_a_layout_wipe() -> None:
    # Borrow the useful interpretation layer, not the destructive six-block shell.
    for marker in (
        "{% set _hero_clause = hero_clause(pb_obj, ms) %}",
        "{% set _stance = posture_lane(_pd.posture if _pd else none) %}",
        "{% set _todo_faces = reason_faces(_pd.reasons if _pd else none) %}",
        "{% set _todo_actual = _todo_faces | rejectattr('empty') | list %}",
        "{% set _todo_shown = _todo_actual[:2] if _todo_actual else _todo_faces[:1] %}",
        "{% for face in _todo_shown %}",
        'class="cnx-hero-meta"',
        'class="v-thesis cnx-thesis"><span class="l-en">{{ _ms_truth_en }}',
        'class="cnx-playbook-context"',
        "{{ t('Current measured read','当前实测解读') }}",
        'class="cnx-row cnx-reason-row',
        'class="cnx-lens lens-q"',
        'data-tip-en="{{ face.tip_en | e }}"',
        "{% set _ev_pool = [] %}",
        "{{ t('Macro News','宏观新闻') }}",
        "{{ t('What changed ↓','最近变化 ↓') }}",
        "{% set _chg_news_n = 1 if latest.alerts else 2 %}",
        "{% for h in CN.news.headlines[:_chg_news_n] %}",
        '<a class="cnx-change-row" href="china_news.html">',
        '<a class="cnx-change-row cnx-change-alert" href="alerts.html">',
        'href="china_policy_watch.html"',
        'href="china_news.html"',
        'href="alerts.html"',
    ):
        assert marker in TPL

    # Market-state headline ownership stays with the producer/live patcher;
    # playbook context is separately qualified and cannot become a second state owner.
    assert 'class="cnx-hero-read"' not in TPL
    assert 'class="cnx-live-freshness"' in TPL
    assert 'class="cnx-stance' not in TPL
    assert "{% if _health_n and _health_ok < _health_n %}" in TPL

    # The richer original information architecture remains the page skeleton.
    for marker in (
        "ROW 1: What To Do + Upcoming Events",
        "ROW 2: Pullback Risk / Top Stocks + Sentiment + Sector Temperature",
        "ROW 3: Policy Monitor + Connect Flows + Macro News",
        "ROW 4: Property + AI Brief + Alerts Centre",
    ):
        assert marker in TPL


def test_hero_freshness_only_spends_space_when_a_feed_is_degraded() -> None:
    assert "{% set _health_n = health | length if health else 0 %}" in TPL
    assert "{% set _health_ok = health | selectattr('status','equalto','ok') | list | length if health else 0 %}" in TPL
    assert "{% if _health_n and _health_ok < _health_n %}" in TPL


def test_what_to_do_glance_caps_reasons_without_truncating_the_dialog() -> None:
    assert "{% set _todo_shown = _todo_actual[:2] if _todo_actual else _todo_faces[:1] %}" in TPL
    assert "{{ t('What To Do','该怎么做') }}</div>" in TPL
    assert '{{ t(\'What To Do\',\'该怎么做\') }} <span class="cnx-ctitle-note"' not in TPL
    assert "Current posture" not in TPL
    assert "cnx-dlg-playbook" in TPL


def test_synthesized_reason_receipts_use_the_shared_lens_plane() -> None:
    assert 'class="cnx-lens lens-q"' in TPL
    assert 'aria-label="Why this read / 为什么"' in TPL
    assert 'data-tip-en="{{ face.tip_en | e }}"' in TPL
    assert 'data-tip-zh="{{ face.tip_zh | e }}"' in TPL
    assert 'onclick="cnxToggleLens(this,event)"' not in TPL
    assert "cnxToggleLens" not in TPL
    assert "cnxCloseLenses" not in TPL
    assert "cnx-tip-open" not in TPL
    assert "document.querySelector('.lens-pop.open')" in TPL
    assert '.cnx-card[role="button"]' in TPL
    assert "e.preventDefault();card.click();" in TPL


def test_regime_watch_stays_quiet_until_a_transition_is_building() -> None:
    assert "{% if latest.pending_quad in ['Q1','Q2','Q3','Q4'] and latest.pending_days %}" in TPL
    assert "watch →" in TPL
    assert "预警 →" in TPL


def test_four_driver_synthesis_reuses_the_existing_link_rail_and_deep_dialogs() -> None:
    assert 'class="cnx-links" data-cn-driver-rail' in TPL
    assert "{{ t('Why this regime','为什么这样判断') }}" in TPL
    assert "cnx-driver-band" not in TPL
    assert "cnx-driver-rail" not in TPL
    assert "cny_yi_pair" not in TPL
    assert "{{ t('bn','亿') }}" in TPL
    for dialog in ("cnx-dlg-policy", "cnx-dlg-flows", "cnx-dlg-risk", "cnx-dlg-property"):
        assert f'href="#{dialog}"' in TPL
        assert f"cnxOpenDlg('{dialog}')" in TPL

    # The synthesis is a glance layer only; the accepted deep module rows remain.
    for marker in (
        "ROW 2: Pullback Risk / Top Stocks + Sentiment + Sector Temperature",
        "ROW 3: Policy Monitor + Connect Flows + Macro News",
        "ROW 4: Property + AI Brief + Alerts Centre",
    ):
        assert marker in TPL


def test_upcoming_events_prioritize_high_impact_without_replacing_the_card() -> None:
    assert "{% set _ev_pool = [] %}" in TPL
    assert "if c.importance == 'high'" in TPL
    assert "if c.importance != 'high'" in TPL
    assert "{% set _ev_shown = _ev_pool[:4] %}" in TPL
    assert "ROW 1: What To Do + Upcoming Events" in TPL


def test_deep_link_rail_avoids_redundant_news_and_alert_shortcuts() -> None:
    assert "{{ t('Go deeper','深入研究') }}" in TPL
    links = TPL.split('<div class="cnx-links">', 1)[1].split("</div>", 1)[0]
    assert 'href="china_policy_watch.html"' in links
    assert 'href="flow_velocity.html"' in links
    assert 'href="china_news.html"' not in links
    assert 'href="alerts.html"' not in links


def test_live_only_index_tiles_show_loading_geometry_until_live_quote_arrives() -> None:
    for symbol in ("000300.SS", "399006.SZ"):
        assert f'class="mx5-mkt-price nb-px mx-skel" data-sym="{symbol}"' in TPL
        assert f'class="mx5-mkt-delta nb-chg mx-skel" data-sym="{symbol}"' in TPL
    assert 'aria-busy="true"' in TPL


def test_index_face_and_deep_racks_remain() -> None:
    assert "MARKET TILES (C · US mx5 combined index face" in TPL
    assert '<div class="cnx-tiles">' in TPL
    assert '<div class="cnx-rack2">' in TPL
    assert TPL.count('<div class="cnx-rack3">') >= 3


def test_retired_cn_page_level_live_strip_stays_retired() -> None:
    assert 'id="cn-prophet-live"' not in TPL
    assert 'id="cnpl-phase"' not in TPL
    assert 'id="cnpl-cov"' not in TPL
    assert 'id="cnpl-asof"' not in TPL
    assert 'id="cnpl-close"' not in TPL


def test_settled_session_floor_stays_on_existing_stock_header() -> None:
    assert (
        '<div class="panel span12" id="stocks-header" '
        'data-cn-session="{{ _cn_through or \'\' }}">'
    ) in TPL


def test_direction_token_repairs_survive_the_restore() -> None:
    assert ".pv-live.cnpl-up{--plvc:var(--up)}" in TPL
    assert ".pv-live.cnpl-down{--plvc:var(--down)}" in TPL
    assert ".pv-live.cnpl-break{--plvc:var(--muted)}" in TPL


def test_calendar_glyph_regression_does_not_return() -> None:
    assert "📅" not in TPL
    assert (
        '{% if imminent %}<div class="cnx-row"><span class="ic" aria-hidden="true"></span>'
        in TPL
    )


def test_no_network_render_guard_covers_render_and_fast_modes(monkeypatch) -> None:
    from scripts import build_china

    monkeypatch.delenv("RENDER_NO_DRIP", raising=False)
    monkeypatch.delenv("CHINA_FAST_RENDER", raising=False)
    assert build_china._no_network_render() is False

    monkeypatch.setenv("RENDER_NO_DRIP", "1")
    assert build_china._no_network_render() is True
    monkeypatch.delenv("RENDER_NO_DRIP")
    monkeypatch.setenv("CHINA_FAST_RENDER", "1")
    assert build_china._no_network_render() is True


def test_no_network_render_never_calls_eastmoney_leaderboard(monkeypatch) -> None:
    import sys

    from scripts import build_china

    class _NetworkForbidden:
        def __getattr__(self, name):
            raise AssertionError(f"render lane attempted requests.{name}")

    monkeypatch.setenv("CHINA_FAST_RENDER", "1")
    monkeypatch.setitem(sys.modules, "requests", _NetworkForbidden())
    assert build_china._leaderboard() is None


def test_no_network_render_skips_stock_library_drips(monkeypatch) -> None:
    from scripts import build_china

    monkeypatch.setenv("RENDER_NO_DRIP", "1")
    assert build_china._build_china_library_for_page(alpha=None) is None


def test_no_network_render_disables_live_news_fetches(monkeypatch) -> None:
    from engine import china_news

    monkeypatch.setattr(china_news, "_cfg", lambda: {"enabled": True})
    monkeypatch.setenv("RENDER_NO_DRIP", "1")
    assert china_news.enabled() is False
    monkeypatch.delenv("RENDER_NO_DRIP")
    monkeypatch.setenv("CHINA_FAST_RENDER", "1")
    assert china_news.enabled() is False


def test_neutral_posture_and_growth_history_do_not_become_entry_advice() -> None:
    from engine.china_tier1 import posture_lane, reason_faces

    assert posture_lane("NEUTRAL") == ("Neutral", "中性")
    assert posture_lane(None) == ("Unclear", "待确认")

    face = reason_faces(
        [("+", "Growth-scare contrarian bottom context", "增长恐慌是实测的历史背景")],
        n=1,
    )[0]
    joined = " ".join((face["en"], face["zh"], face["tip_en"], face["tip_zh"])).lower()
    for forbidden in ("buying window", "add quality", "re-drawn nightly", "每晚重新校准"):
        assert forbidden.lower() not in joined
    assert "not an entry signal" in face["en"]
    assert "不是入场信号" in face["zh"]


def test_playbook_context_never_fabricates_policy_breadth_or_combined_signal() -> None:
    from engine.china_tier1 import hero_clause

    missing_headline_pb = {
        "dial": {"posture": "NEUTRAL"},
        "progress": {"phase": "mid"},
        "quad_meaning": {
            "en": "Growth-scare — both growth and prices falling.",
            "zh": "增长恐慌——增长与物价齐跌。",
        },
    }
    assert hero_clause(missing_headline_pb, {"color": "red"}) == (
        "Playbook posture: Neutral.",
        "策略姿态：中性。",
    )

    bullish_playbook = {"dial": {"posture": "CONSTRUCTIVE"}}
    assert hero_clause(
        bullish_playbook,
        {"color": "red", "headline_en": "Risk-off", "headline_zh": "避险"},
    ) == ("Playbook posture: Constructive.", "策略姿态：积极。")

    text = " ".join(hero_clause(missing_headline_pb, {"color": "red"})).lower()
    for fabricated in ("policy stays easy", "falling broadly", "buy", "entry", "act on"):
        assert fabricated not in text


def test_market_headline_and_playbook_context_have_separate_dom_owners() -> None:
    # Keep the presentation-only measured-state projection on the incumbent
    # .v-thesis node and render playbook posture as separately qualified context.
    # The live updater must patch this same owner from measured legs, never from
    # the producer's generic headline.
    assert '<p class="v-thesis cnx-thesis">' in TPL
    assert "{{ _ms_truth_en }}" in TPL
    assert "{{ _ms_truth_zh }}" in TPL
    assert '<div class="cnx-playbook-context">' in TPL
    assert TPL.count("_hero_clause[0]") == 1
    assert TPL.count("_hero_clause[1]") == 1


def test_live_market_state_projection_preserves_semantic_truth() -> None:
    js = (ROOT / "templates" / "china_risk_state_live.js").read_text(encoding="utf-8")
    site_js = (ROOT / "site" / "china_risk_state_live.js").read_text(encoding="utf-8")
    assert js == site_js
    for marker in (
        "function measuredHeadline(d, disp)",
        "function boundaryRead(disp)",
        'legScore(d, "breadth")',
        'legScore(d, "liquidity")',
        'legScore(d, "trend")',
        'document.getElementById("ms-boundary-chip")',
        "Participation and liquidity are weak; trend remains soft.",
        "参与度与流动性偏弱；趋势仍然疲软。",
    ):
        assert marker in js
    assert "blk.headline_en" not in js
    assert "blk.headline_zh" not in js
