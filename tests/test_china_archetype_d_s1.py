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
        'class="v-thesis cnx-thesis"><span class="l-en">{{ _ms_thesis or \'Market-state headline unavailable.\' }}',
        'class="cnx-playbook-context"',
        "{{ t('Model headline','模型原始标题') }}",
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


def test_upcoming_events_prioritize_high_impact_without_replacing_the_card() -> None:
    assert "{% set _ev_pool = [] %}" in TPL
    assert "if c.importance == 'high'" in TPL
    assert "if c.importance != 'high'" in TPL
    assert "{% set _ev_shown = _ev_pool[:4] %}" in TPL
    assert "ROW 1: What To Do + Upcoming Events" in TPL


def test_deep_link_rail_avoids_redundant_news_and_alert_shortcuts() -> None:
    links = TPL.split('<div class="cnx-links">', 1)[1].split("</div>", 1)[0]
    assert 'href="china_policy_watch.html"' in links
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
        "{% if imminent and _event_clock.get('status') == 'dated' %}"
        '<div class="cnx-row"><span class="ic" aria-hidden="true"></span>'
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
    # Keep the producer-owned market-state headline on the incumbent .v-thesis
    # node and render playbook posture as a separately qualified context node.
    # This publication contract intentionally stays inside the China template
    # closure; the existing live-plane suite owns live-script behavior.
    assert '<p class="v-thesis cnx-thesis">' in TPL
    assert "{{ _ms_thesis or 'Market-state headline unavailable.' }}" in TPL
    assert "{{ _ms_thesis_zh or '市场状态标题暂不可用。' }}" in TPL
    assert '<div class="cnx-playbook-context">' in TPL
    assert TPL.count("_hero_clause[0]") == 1
    assert TPL.count("_hero_clause[1]") == 1


# Legacy CN presentation must not turn a sampled stress percentile into all-market odds.
import copy
import pytest


def _risk_reading_fixture():
    from tests.test_risk_radar_dlg_partial import _RD
    raw = {'schema': 'risk_radar_intl.v1', 'market': 'cn', 'state': 'risk-off',
           'asof': '2026-09-18', 'top_score': 94, 'dominant_scare': 'breadth',
           'dominant_label_en': 'Breadth breakdown (all-boats)',
           'dominant_label_zh': '广度普跌（普跌）'}
    rd = copy.deepcopy(_RD)
    rd.update(state='risk-off', top_score=94, dd21=.5, gross=.62,
              label_en=raw['dominant_label_en'], label_zh=raw['dominant_label_zh'])
    rd['scares'] = [{'scare': 'breadth', 'label_en': raw['dominant_label_en'],
                     'label_zh': raw['dominant_label_zh'], 'score': 98.2,
                     'tier': 'A', 'band': 'risk-off', 'firing_legs': []}]
    raw['scares'] = copy.deepcopy(rd['scares'])
    return raw, rd


def test_risk_reading_names_sampled_breadth_not_all_market_collapse():
    from scripts.build_china import _china_risk_reading
    raw, rd = _risk_reading_fixture()
    view = _china_risk_reading(raw, rd)
    assert view['radar']['label_en'] == 'Weak large-cap participation'
    assert view['radar']['label_zh'] == '大盘股参与偏弱'
    assert view['radar']['scares'][0]['label_en'] == view['radar']['label_en']


def test_risk_reading_preserves_every_nonlabel_field_and_both_inputs():
    from scripts.build_china import _china_risk_reading
    raw, rd = _risk_reading_fixture()
    before = copy.deepcopy((raw, rd))
    view = _china_risk_reading(raw, rd)
    expected = copy.deepcopy(rd)
    for obj in [expected, expected['scares'][0]]:
        obj.update(label_en='Weak large-cap participation', label_zh='大盘股参与偏弱')
    assert view['radar'] == expected
    assert (raw, rd) == before
    view['radar']['scares'][0]['firing_legs'].append({'extra': 1})
    assert (raw, rd) == before
    assert view['basis']['source_label_en'] == 'Breadth breakdown (all-boats)'


@pytest.mark.parametrize('field,value', [('schema','unknown'), ('market','hk'),
    ('composition',None), ('composition',{}), ('state','calm'), ('top_score',12)])
def test_risk_reading_unknown_construction_or_mismatched_snapshot_not_reinterpreted(field,value):
    from scripts.build_china import _china_risk_reading
    raw, rd = _risk_reading_fixture()
    raw[field] = value
    view = _china_risk_reading(raw, rd)
    assert view['basis'] is None and view['radar'] == rd


@pytest.mark.parametrize('raw,rd', [(None,None), ({},{}), ([],[]), ('bad','bad')])
def test_risk_reading_absence_cannot_create_an_interpretation(raw,rd):
    from scripts.build_china import _china_risk_reading
    assert _china_risk_reading(raw,rd)['basis'] is None


def test_risk_reading_calm_or_other_driver_keeps_original_headline():
    from scripts.build_china import _china_risk_reading
    raw, rd = _risk_reading_fixture()
    raw.update(state='calm', dominant_label_en='No elevated driver')
    rd.update(state='calm', label_en='No elevated driver')
    assert _china_risk_reading(raw,rd)['radar']['label_en'] == 'No elevated driver'
    raw, rd = _risk_reading_fixture()
    raw.update(dominant_scare='rate_shock', dominant_label_en='US rate shock')
    rd['label_en'] = 'US rate shock'
    assert _china_risk_reading(raw,rd)['radar']['label_en'] == 'US rate shock'


def test_risk_reading_explains_percentile_and_scoped_horizon_without_new_odds():
    from scripts.build_china import _china_risk_reading
    raw, rd = _risk_reading_fixture()
    basis = _china_risk_reading(raw,rd)['basis']
    assert basis['score_kind'] == 'historical_stress_percentile'
    assert basis['benchmark_en'] == 'Shanghai Composite'
    assert basis['horizon_sessions'] == 21
    assert 'not a pullback probability' in basis['explanation_en']
    assert 'curated large-cap sample' in basis['explanation_en']
    assert '并非回撤概率' in basis['explanation_zh']
    assert 'state-based' in basis['probability_note_en']
    assert 'current' not in basis['explanation_en'].lower()


def test_risk_reading_actual_shared_dialog_uses_the_scoped_copy():
    from scripts.build_china import _china_risk_reading, _radar_dlg_vm
    from tests.test_risk_radar_dlg_partial import _render
    raw, rd = _risk_reading_fixture()
    view = _china_risk_reading(raw,rd)
    vm = {'market_state': {'radar': rd}, 'risk_reading': view}
    ctx = _radar_dlg_vm(vm, {'date': '2026-09-18', 'risk_radar': raw})
    html = _render(rd=view['radar'], scares=view['radar']['scares'], ctx=ctx)
    assert 'Weak large-cap participation' in html and '大盘股参与偏弱' in html
    assert 'all-boats' not in html and '广度普跌（普跌）' not in html
    assert 'not a pullback probability' in html and 'state-based' in html
    assert rd['top_score'] == 94 and rd['dd21'] == .5


@pytest.mark.parametrize('bad', [None, '', '94', True, float('nan'), float('inf'), -1, 101, 10**400])
def test_risk_reading_invalid_score_cannot_gain_numeric_interpretation(bad):
    from scripts.build_china import _china_risk_reading
    raw, rd = _risk_reading_fixture()
    raw['top_score'] = bad
    assert _china_risk_reading(raw, rd)['basis'] is None


def test_risk_reading_display_composition_is_also_out_of_scope():
    from scripts.build_china import _china_risk_reading
    raw, rd = _risk_reading_fixture()
    rd['composition'] = {'status': 'reviewed'}
    assert _china_risk_reading(raw, rd)['basis'] is None


def test_risk_reading_same_value_other_driver_is_not_breadth_attribution():
    from scripts.build_china import _china_risk_reading
    raw, rd = _risk_reading_fixture()
    raw['dominant_scare'] = 'capital_flow'
    rd.update(label_en='Capital outflow / FX', label_zh='资本外流／汇率')
    assert _china_risk_reading(raw,rd)['radar']['label_en'] == rd['label_en']


# Execute the actual published page and its existing dialog view-model, not a
# hand-written copy of the card. All fixtures are synthetic, never live proof.
def _render_china_risk_case(recession, action_en="", action_zh="", *, playbook=None, latest_updates=None, **extra):
    from jinja2 import ChainableUndefined, Environment, FileSystemLoader
    from engine import china_tier1, i18n
    from scripts.build_china import _radar_dlg_vm

    radar = dict(state="caution", top_score=82, label_en="Sample stress",
                 label_zh="样本压力", state_zh="谨慎", do_en=action_en,
                 do_zh=action_zh, gross=0.8, dd5=None, dd10=None, dd21=None,
                 dd_lift=None, dd_base={}, is_loud=True, scares=[],
                 forward_log=None, cycle=None, counterread=None, amp=0,
                 amp_flags_en=[], amp_flags_zh=[], recovery=None, track=None)
    latest = dict(date="2026-09-18", quad_name="Growth-scare", cycle_tag="mid",
                  confidence=0.6, risk_radar={"state": "caution"}, conditions={"recession": recession},
                  alerts=[])
    market_state = dict(color="yellow", score=46, label_en="Mixed", label_zh="混合",
                        headline_en="Fixture headline", headline_zh="样本标题", radar=radar)
    env = Environment(loader=FileSystemLoader(str(ROOT / "templates")),
                      autoescape=False, undefined=ChainableUndefined)
    env.globals.update(td=i18n.td, tr=i18n.tr, t=i18n.t,
                       **{k: getattr(china_tier1, k, None) for k in
                          ("posture_lane", "posture_tone", "reason_faces", "hero_clause", "slowdown_face", "connect_flow_face", "regime_watch_face")})
    latest.update(latest_updates or {})
    ctx = _radar_dlg_vm({"market_state": market_state}, latest)
    return env.get_template("china.html.j2").render(
        mode="macro", latest=latest, market_state=market_state, sectors=[], radar_dlg=ctx, pb=playbook, **extra)


def _risk_card(html):
    from bs4 import BeautifulSoup
    card = BeautifulSoup(html, "html.parser").find(
        "div", attrs={"class": "cnx-card", "onclick": "cnxOpenDlg('cnx-dlg-risk')"})
    assert card is not None
    return card


def test_washed_out_margin_receipt_does_not_claim_crowding():
    from engine.china_tier1 import reason_faces
    low = reason_faces([("+", "Margin leverage capitulated", "融资杠杆已出清")], n=1)[0]
    high = reason_faces([("-", "Margin leverage crowded", "融资杠杆拥挤")], n=1)[0]
    assert "top" not in low["tip_en"].lower()
    assert "最高" not in low["tip_zh"]
    assert low["tip_en"] != high["tip_en"]
    assert low["tip_zh"] != high["tip_zh"]


def test_missing_risk_guidance_never_manufactures_sizing_advice():
    card = _risk_card(_render_china_risk_case(None))
    footer = card.select_one(".cnx-foot").get_text(" ", strip=True)
    assert "High pullback risk" not in footer
    assert "size down" not in footer and "缩仓" not in footer
    assert "unavailable" in footer.lower() and "暂不可用" in footer


import pytest


@pytest.mark.parametrize("record", [None, {}, {"score": None, "label": "low"},
    {"score": True, "label": "low"}, {"score": "20", "label": "low"},
    {"score": float("nan"), "label": "low"}, {"score": float("inf"), "label": "low"},
    {"score": -1, "label": "low"}, {"score": 101, "label": "low"},
    {"score": 20, "label": "unknown"}])
def test_missing_or_invalid_slowdown_never_becomes_calm(record):
    card = _risk_card(_render_china_risk_case(record))
    text = card.get_text(" ", strip=True)
    assert "Economic slowdown" in text and "经济放缓" in text
    assert "Deep-drawdown" not in text and "深跌仪表" not in text
    row = next(r for r in card.select(".cnx-kv") if "Economic slowdown" in r.get_text())
    value = row.select_one(".v").get_text(" ", strip=True)
    assert "unavailable" in value.lower() and "暂不可用" in value
    assert "Calm" not in value and "平静" not in value


@pytest.mark.parametrize("score,label,en,zh", [
    (0, "low", "calm", "平静"), (30, "elevated", "softening", "走弱"),
    (45, "high", "weak", "疲弱"), (70, "low", "calm", "平静")])
def test_slowdown_glance_uses_the_same_producer_label_as_dialog(score, label, en, zh):
    html = _render_china_risk_case({"score": score, "label": label})
    card = _risk_card(html)
    row = next((r for r in card.select(".cnx-kv") if "Economic slowdown" in r.get_text()), None)
    assert row is not None, "the economic gauge must be named for its actual input"
    assert en in row.select_one(".v").get_text().lower() and zh in row.get_text()
    from bs4 import BeautifulSoup
    dialog = BeautifulSoup(html, "html.parser").find(id="cnx-dlg-risk")
    assert en in dialog.get_text().lower() and zh in dialog.get_text()


@pytest.mark.parametrize("en,zh", [("Owner guidance", "来源指引"),
                                   ("Owner guidance", ""), ("", "来源指引"), ("  ", "  ")])
def test_risk_guidance_preserves_available_language_without_inventing_the_other(en, zh):
    card = _risk_card(_render_china_risk_case({"score": 0, "label": "low"}, en, zh))
    footer = card.select_one(".cnx-foot")
    english = footer.select_one(".l-en").get_text(strip=True)
    chinese = footer.select_one(".l-zh").get_text(strip=True)
    assert english == (en.strip() or "Risk guidance unavailable — inspect the evidence.")
    assert chinese == (zh.strip() or "风险指引暂不可用——请查看依据。")


@pytest.mark.parametrize('score', [10**400, -(10**400)])
def test_integrated_slowdown_rejects_extreme_integers_without_losing_context(score):
    from engine.china_tier1 import slowdown_face
    from scripts.build_china import _radar_dlg_vm
    reading = slowdown_face({'score': score, 'label': 'low'})
    assert reading == {'score': None, 'en': 'unavailable', 'zh': '暂不可用', 'tone': 'muted'}
    context = _radar_dlg_vm({}, {'conditions': {'recession': {'score': score, 'label': 'low'}}})
    assert context['slowdown'] == reading


def test_integrated_risk_card_retains_both_probability_scope_and_economic_nulls():
    html = _render_china_risk_case(None)
    card = _risk_card(html)
    assert 'Economic slowdown' in card.get_text()
    assert 'Unavailable' in card.get_text()
    assert 'Deep-drawdown gauge' not in card.get_text()
    assert 'size down' not in card.get_text()
    assert 'data-risk-score-basis' in TPL
    assert 'Shanghai ≥5% · 21 sessions' in TPL
    assert 'participation_panel' in TPL


# Regime directions describe the model, not current economic levels or an entry.
@pytest.mark.parametrize("quad", ["Q1", "Q2", "Q3", "Q4"])
def test_regime_definition_separates_signals_from_levels(quad):
    from engine.china_playbook import QUAD_MEANING_CN
    en, zh = QUAD_MEANING_CN[quad]
    assert "model" in en.lower() and "signal" in en.lower()
    assert "模型" in zh and "信号" in zh
    assert "price levels" in en.lower() and "价格水平" in zh
    for claim in ("~70%", "best contrarian", "fear peaking", "accumulate", "命中率", "恐慌见顶", "吸纳"):
        assert claim not in en.lower() + zh


@pytest.mark.parametrize("quad,base", [("Q1", 1), ("Q2", 0), ("Q3", -1), ("Q4", 2)])
@pytest.mark.parametrize("liquidity,monetary", [("expanding", 1), ("contracting", -1), ("neutral", 0)])
@pytest.mark.parametrize("margin,positioning", [(10, 1), (50, 0), (90, -1)])
def test_regime_wording_preserves_existing_posture_arithmetic(quad, base, liquidity, monetary, margin, positioning):
    from engine.china_playbook import _dial, _POSTURES
    latest = {"quad": quad, "liquidity_overlay": liquidity}
    internals = {"margin": {"pctile": margin}}
    before = copy.deepcopy((latest, internals))
    result = _dial(latest, internals)
    expected = base + monetary + positioning
    assert result["score"] == expected
    assert result["posture"] == _POSTURES[max(0, min(4, 2 + expected))]
    assert (latest, internals) == before


@pytest.mark.parametrize("quad", ["Q1", "Q2", "Q3", "Q4"])
def test_regime_reason_is_a_prior_not_a_measured_entry_call(quad):
    from engine.china_playbook import _dial
    sign, en, zh = _dial({"quad": quad}, {})["reasons"][0]
    assert "regime prior" in en.lower() and "先验" in zh
    assert "not an entry signal" in en.lower() and "不是入场信号" in zh
    for claim in ("70%", "best contrarian", "hold up best", "fade strength", "命中率", "最抗跌"):
        assert claim not in en.lower() + zh


@pytest.mark.parametrize("quad", ["Q1", "Q2", "Q3", "Q4"])
def test_regime_producer_and_actual_page_do_not_reintroduce_bottom_claims(quad, monkeypatch):
    from engine import china_playbook
    from bs4 import BeautifulSoup
    monkeypatch.setattr(china_playbook.config, "load", lambda: {"china": {"yahoo": {"sector_etfs": {}}}})
    payload = china_playbook.build({"quad": quad}, None, [], {})
    html = _render_china_risk_case(None, playbook=payload)
    dialog = BeautifulSoup(html, "html.parser").find(id="cnx-dlg-playbook")
    assert dialog is not None
    text = dialog.get_text(" ", strip=True)
    assert "regime prior" in text.lower() and "先验" in text
    assert "70%" not in text and "命中率" not in text
    assert "not an entry signal" in text.lower() and "不是入场信号" in text


@pytest.mark.parametrize("earlier,latest,direction", [(1.4, 0.8, -1), (-0.5, -0.2, 1)])
def test_regime_inflation_direction_is_not_the_price_level(earlier, latest, direction):
    import pandas as pd
    from engine.china_axes import _monthly_sign
    from engine.china_playbook import QUAD_MEANING_CN
    frame = pd.DataFrame({"cpi_yoy": [earlier] * 63 + [latest]},
                         index=pd.bdate_range("2026-01-05", periods=64))
    assert _monthly_sign(frame, "cpi_yoy", 63).iloc[-1] == direction
    # Falling positive inflation is not deflation; improving negative inflation
    # is not an increasing price level. The producer keeps these meanings apart.
    en, zh = QUAD_MEANING_CN["Q4" if direction < 0 else "Q2"]
    assert "not price levels" in en and "不是价格水平" in zh


# A page-only rebake consumes the saved assessment, not newly arrived raw inputs.
@pytest.fixture
def saved_regime_render(tmp_path, monkeypatch):
    from scripts import build_china as bc
    from engine import china_run
    import json
    monkeypatch.delenv('RENDER_NO_DRIP', raising=False)
    monkeypatch.delenv('CHINA_FAST_RENDER', raising=False)
    monkeypatch.setattr(bc.config, 'data_dir', lambda: tmp_path)
    path = tmp_path / 'china_regime' / 'latest.json'
    path.parent.mkdir()
    document = {'date': '2026-09-21', 'quad': 'Q4', 'growth_score': -.143,
                'conditions': {'roro': {'roro': .175}},
                'fear_euphoria': {'fe_score': 78},
                'market_drivers': {'evidence': ['copper +1.7σ']}}
    path.write_text(json.dumps(document))
    def forbidden():
        pytest.fail('render-only path invoked the analytical publisher')
    monkeypatch.setattr(china_run, 'run', forbidden)
    return bc, path, document


@pytest.mark.parametrize('flag', ['RENDER_NO_DRIP', 'CHINA_FAST_RENDER'])
def test_render_snapshot_reuses_saved_values_without_recalculation(saved_regime_render, monkeypatch, flag):
    bc, path, document = saved_regime_render
    monkeypatch.setenv(flag, '1')
    before = path.read_bytes()
    loaded = bc._regime_for_page()
    assert loaded == document
    loaded['conditions']['roro']['roro'] = 999
    assert bc._regime_for_page() == document
    assert path.read_bytes() == before


@pytest.mark.parametrize('flag', ['RENDER_NO_DRIP', 'CHINA_FAST_RENDER'])
@pytest.mark.parametrize('bad', ['absent', 'broken_json', 'list', 'bad_date', 'missing_date', 'bad_quad'])
def test_render_snapshot_rejects_bad_cache_without_engine_fallback(saved_regime_render, monkeypatch, flag, bad):
    import json
    bc, path, document = saved_regime_render
    monkeypatch.setenv(flag, '1')
    if bad == 'absent': path.unlink()
    elif bad == 'broken_json': path.write_text('{')
    elif bad == 'list': path.write_text('[]')
    else:
        if bad == 'bad_date': document['date'] = '2026-02-30'
        elif bad == 'missing_date': document.pop('date')
        else: document['quad'] = 'not-a-quadrant'
        path.write_text(json.dumps(document))
    before = path.read_bytes() if path.exists() else None
    with pytest.raises(RuntimeError, match='saved China assessment'):
        bc._regime_for_page()
    assert (path.read_bytes() if path.exists() else None) == before


@pytest.mark.parametrize('flag', ['RENDER_NO_DRIP', 'CHINA_FAST_RENDER'])
def test_render_snapshot_actual_main_keeps_prior_page_when_cache_missing(saved_regime_render, monkeypatch, caplog, flag):
    bc, path, _ = saved_regime_render
    monkeypatch.setenv(flag, '1'); path.unlink()
    def no_page_write(*args, **kwargs):
        pytest.fail('invalid saved snapshot must not publish a replacement page')
    monkeypatch.setattr(bc, 'write_page', no_page_write)
    assert bc.main() == 0  # incumbent per-page fail-soft contract, with error log
    assert 'saved China assessment' in caplog.text
    assert not path.exists()


@pytest.mark.parametrize('flag_value', [None, '', '0'])
def test_render_snapshot_normal_lane_retains_analytical_owner(saved_regime_render, monkeypatch, flag_value):
    from engine import china_run
    bc, path, _ = saved_regime_render
    path.unlink()
    if flag_value is not None:
        monkeypatch.setenv('RENDER_NO_DRIP', flag_value)
        monkeypatch.setenv('CHINA_FAST_RENDER', flag_value)
    calls = []
    produced = {'date': '2026-09-22', 'quad': 'Q1'}
    def run():
        calls.append(True)
        return produced
    monkeypatch.setattr(china_run, 'run', run)
    assert bc._regime_for_page() is produced
    assert calls == [True]


def test_render_snapshot_real_main_uses_the_qualified_loader():
    import inspect
    from scripts import build_china as bc
    assert 'latest = _regime_for_page()' in inspect.getsource(bc.main)


def test_render_snapshot_both_render_modes_block_score_history_writes():
    import inspect
    from scripts import build_china as bc
    source = inspect.getsource(bc.main)
    start = source.index('_ms_sc = _ms_snap.get("score")')
    end = source.index('# Expose last 11 rows', start)
    history_writer = source[start:end]
    assert 'if _no_network_render():' in history_writer
    assert 'environ.get("CHINA_FAST_RENDER")' not in history_writer
    assert 'elif _ms_sc is None:' in history_writer


# Exact saved/display boundary: no catch-all subset comparison may excuse drift.
def _projection_boundary_fixture():
    import copy
    saved = {"conditions": {"roro": {"score": 0.175}, "charts": {"roro": [1., 2.]}},
             "fear_euphoria": {"fe_score": 78}, "market_drivers": {"strength": .94}}
    additions = {"conditions.roro_html": "<svg>roro</svg>",
                 "conditions.recession_html": "<svg>slowdown</svg>",
                 "conditions.drawdown_html": "<svg>drawdown</svg>",
                 "fear_euphoria.chart_html": "<svg>sentiment</svg>",
                 "conditions.breadth": {"above200_pctile": .1587, "div": False}}
    displayed = copy.deepcopy(saved)
    for path, value in additions.items():
        parent, key = path.split(".")
        displayed[parent][key] = copy.deepcopy(value)
    return saved, displayed, additions


def test_projection_boundary_accepts_only_exact_reviewed_additions():
    from research.grey_deer.china_render_projection_check import verify_projection
    saved, displayed, additions = _projection_boundary_fixture()
    proof = verify_projection(saved, displayed, expected_additions=additions)
    assert proof["saved_measurements_unchanged"] is True
    assert set(proof["reviewed_additions"]) == set(additions)
    assert proof["saved_leaf_count"] == 5


@pytest.mark.parametrize("change", ["measurement", "removed", "unknown", "chart", "breadth", "missing_expected", "extra_expected", "chart_shape", "bool_measurement", "list_shape", "missing_domain", "existing_display_key"])
def test_projection_boundary_rejects_unqualified_changes(change):
    from research.grey_deer.china_render_projection_check import verify_projection
    saved, displayed, expected = _projection_boundary_fixture()
    if change == "measurement": displayed["fear_euphoria"]["fe_score"] = 81
    elif change == "removed": del displayed["market_drivers"]["strength"]
    elif change == "unknown": displayed["conditions"]["another_score"] = 90
    elif change == "chart": displayed["conditions"]["roro_html"] = "<svg>wrong</svg>"
    elif change == "breadth": displayed["conditions"]["breadth"]["div"] = True
    elif change == "missing_expected": del expected["conditions.breadth"]
    elif change == "extra_expected": expected["conditions.new_model"] = 1
    elif change == "chart_shape": displayed["conditions"]["charts"]["roro"].append(3.)
    elif change == "bool_measurement": displayed["conditions"]["roro"]["score"] = True
    elif change == "list_shape": displayed["conditions"]["charts"]["roro"] = {"0": 1., "1": 2.}
    elif change == "missing_domain": del displayed["conditions"]
    else: saved["conditions"]["roro_html"] = "<svg>previous</svg>"
    with pytest.raises(AssertionError):
        verify_projection(saved, displayed, expected_additions=expected)


def test_projection_boundary_is_immutable_and_handles_matching_nulls():
    import copy
    from research.grey_deer.china_render_projection_check import verify_projection
    saved, displayed, expected = _projection_boundary_fixture()
    saved["market_drivers"]["unavailable"] = displayed["market_drivers"]["unavailable"] = None
    before = copy.deepcopy((saved, displayed, expected))
    verify_projection(saved, displayed, expected_additions=expected)
    assert (saved, displayed, expected) == before


@pytest.mark.parametrize('report', [{}, {'sources': {}}, {'sources': None}, None])
def test_page_time_health_keeps_missing_source_families_visible(monkeypatch, report):
    from scripts import build_china
    monkeypatch.setattr(build_china.store, 'read_status', lambda: report)
    rows = build_china._health_rows()
    assert len(rows) == 7
    assert len({row['key'] for row in rows}) == 7
    assert all(row['status'] == 'unknown' and row['last'] == '—' for row in rows)


def test_page_time_collection_success_does_not_certify_freshness(monkeypatch):
    from scripts import build_china
    report = {'sources': {'china_prices': {'status': 'ok', 'last_date': '2026-08-01', 'rows': 900}}}
    before = copy.deepcopy(report)
    monkeypatch.setattr(build_china.store, 'read_status', lambda: report)
    row = build_china._health_rows()[0]
    assert row['status'] == 'ok' and row['last'] == '2026-08-01'
    assert row['status_basis'] == 'collection_report_not_freshness'
    assert report == before


@pytest.mark.parametrize('invalid', ['garbled', [], {'status': 'ok', 'last_date': 'not-a-date'}])
def test_page_time_health_bad_row_is_explicit(monkeypatch, invalid):
    from scripts import build_china
    monkeypatch.setattr(build_china.store, 'read_status', lambda: {'sources': {'china_prices': invalid}})
    row = build_china._health_rows()[0]
    assert row['last'] == '—'
    assert row['status_basis'] == 'collection_report_not_freshness'


def test_page_time_saved_hero_is_dated_not_live():
    from bs4 import BeautifulSoup
    doc = BeautifulSoup(_render_china_risk_case(None), 'html.parser')
    pill = doc.find(id='ms-live-pill')
    assert pill is not None
    assert 'LIVE' not in pill.get_text() and '实时' not in pill.get_text()
    assert 'Saved assessment' in pill.get_text() and '已保存评估' in pill.get_text()
    stamp = doc.find(id='ms-date')
    assert stamp['data-assessment-asof'] == '2026-09-18'
    assert stamp.find('time')['datetime'] == '2026-09-18'


def test_page_time_health_disclosure_reports_collection_not_freshness():
    from bs4 import BeautifulSoup
    health = [{'key':'china_prices','en':'Prices / sectors','zh':'价格 / 板块',
               'status':'ok','last':'2026-08-01','status_basis':'collection_report_not_freshness'}]
    doc = BeautifulSoup(_render_china_risk_case(None, health=health), 'html.parser')
    disclosure = doc.select_one('details.cnx-dh')
    assert disclosure and disclosure.find('summary')
    text = disclosure.get_text(' ', strip=True)
    assert 'Collection succeeded' in text and '采集成功' in text
    assert 'fresh' not in text.lower() and 'Current' not in text
    assert '2026-08-01' in text and '2026-09-18' not in text
    assert 'does not certify' in text and '不代表' in text


@pytest.mark.parametrize('file', ['templates/china_risk_state_live.js','site/china_risk_state_live.js'])
def test_page_time_client_preserves_baseline_and_full_update_date(file):
    source = (ROOT / file).read_text()
    assert 'data-assessment-asof' in source
    assert 'ms-snapshot-kind' in source
    assert 'Intraday snapshot' in source and '盘中快照' in source
    assert 'Updated ' in source and '更新于 ' in source
    assert '.toISOString().slice(0, 16)' in source
    assert 'Quote timing unverified' in source
    assert 'pill.classList.remove("on")' in source


def test_page_time_client_asset_pair_stays_equal():
    assert (ROOT/'templates/china_risk_state_live.js').read_bytes() == (ROOT/'site/china_risk_state_live.js').read_bytes()


def test_page_time_unreadable_collection_report_is_not_missing_page(monkeypatch):
    from scripts import build_china
    def unreadable():
        raise ValueError('invalid stored report')
    monkeypatch.setattr(build_china.store, 'read_status', unreadable)
    rows = build_china._health_rows()
    assert len(rows) == 7 and all(row['status'] == 'unknown' for row in rows)


def test_page_time_unknown_collection_state_cannot_be_green():
    from bs4 import BeautifulSoup
    rows = [{'en':'Breadth','zh':'广度','status':'unexpected','last':'—'}]
    doc = BeautifulSoup(_render_china_risk_case(None, health=rows), 'html.parser')
    disclosure = doc.select_one('details.cnx-dh')
    assert 'Collection needs checking' in disclosure.get_text()
    assert 'Collection succeeded' not in disclosure.get_text()


@pytest.mark.parametrize('file', ['templates/china_risk_state_live.js','site/china_risk_state_live.js'])
@pytest.mark.parametrize('built,real_time,expected', [
    ('2026-08-01T03:04:00Z',False,'Updated 2026-08-01 03:04 UTC · Quotes delayed'),
    ('2026-08-01T11:04:00+08:00',True,'Updated 2026-08-01 03:04 UTC · Quote feed marked real-time'),
    ('2026-08-01T03:04:00Z',None,'Updated 2026-08-01 03:04 UTC · Quote timing unverified')])
def test_page_time_executed_client_discloses_dated_update(file,built,real_time,expected):
    from tests.test_risk_state_live_session_floor import _harness
    feed={'built':built,'nightly_asof':'2026-07-31','live_active':True,
          'realtime':real_time,'display':{'verdict':'RISK_OFF','score':33,
          'label_en':'Risk-off','label_zh':'避险'},'live':{},'nightly':{}}
    result=_harness((ROOT/file).read_text(),feed,'cn')
    assert 'error' not in result
    assert result['date'] == expected and result['pill_on'] is False
    assert result['score'] == result['numeral'] == '33'


@pytest.mark.parametrize('file', ['templates/china_risk_state_live.js','site/china_risk_state_live.js'])
def test_page_time_executed_nightly_patch_stays_dated(file):
    from tests.test_risk_state_live_session_floor import _harness
    feed={'built':'2026-08-01T03:04:00Z','nightly_asof':'2026-07-31','live_active':False,
          'display':{'verdict':'RISK_OFF','score':33,'label_en':'Risk-off','label_zh':'避险'}}
    result=_harness((ROOT/file).read_text(),feed,'cn')
    assert result['date'] == 'As of 2026-07-31' and result['pill_on'] is False


@pytest.mark.parametrize('instant,day', [
    ('2026-09-23T15:59:59+00:00', '2026-09-23'),
    ('2026-09-23T16:00:00+00:00', '2026-09-24'),
    ('2026-09-24T00:00:00+08:00', '2026-09-24'),
    ('2026-09-26T10:00:00+00:00', '2026-09-26'),
])
def test_event_clock_uses_beijing_civil_date_not_saved_regime(monkeypatch, instant, day):
    from datetime import datetime, date
    from engine import china_event_calendar as calendar
    from scripts import build_china
    def forbidden():
        raise AssertionError('event view must not read the stale regime date')
    monkeypatch.setattr(calendar, '_regime_asof', forbidden)
    view = build_china._china_event_context(now=datetime.fromisoformat(instant))
    assert view['event_clock']['status'] == 'dated'
    assert view['event_clock']['asof'] == day
    assert view['event_clock']['timezone'] == 'Asia/Shanghai'
    expected = calendar.china_macro_events(asof=date.fromisoformat(day), horizon_days=14)
    assert view['calendar'] == expected
    assert all(row['date'] >= day for row in view['calendar'])
    assert all(row['type'] != 'LPR' for row in view['calendar'])
    if view['imminent']:
        assert view['imminent']['date'] in view['imminent']['en']
        assert view['imminent']['date'] in view['imminent']['zh']
        assert 'today' not in view['imminent']['en']
        assert '今天' not in view['imminent']['zh']


@pytest.mark.parametrize('bad', ['2026-09-24', True, float('nan')])
def test_event_clock_invalid_instant_cannot_fall_back_to_old_assessment(bad):
    from scripts import build_china
    view = build_china._china_event_context(now=bad)
    assert view['event_clock']['status'] == 'unavailable'
    assert view['calendar'] == view['event_strip'] == []
    assert view['imminent'] is None


def test_event_clock_naive_datetime_is_not_assumed_utc():
    from datetime import datetime
    from scripts import build_china
    view = build_china._china_event_context(now=datetime(2026, 9, 24))
    assert view['event_clock']['status'] == 'unavailable'


def test_event_clock_failure_is_not_a_quiet_calendar(monkeypatch):
    from datetime import datetime, timezone
    from engine import china_event_calendar as calendar
    from scripts import build_china
    def broken(**kwargs):
        raise ValueError('calendar source unreadable')
    monkeypatch.setattr(calendar, 'china_macro_events', broken)
    view = build_china._china_event_context(now=datetime(2026, 9, 24, tzinfo=timezone.utc))
    assert view['event_clock']['status'] == 'unavailable'
    assert view['calendar'] == view['event_strip'] == [] and view['imminent'] is None


def test_event_clock_all_three_views_share_one_explicit_date(monkeypatch):
    from datetime import datetime, timezone
    from engine import china_event_calendar as calendar
    from scripts import build_china
    calls = []
    for name in ('china_macro_events', 'high_impact_strip', 'imminent_line'):
        result = None if name == 'imminent_line' else []
        def record(*, asof, horizon_days, _name=name, _result=result):
            calls.append((_name, asof.isoformat(), horizon_days))
            return _result
        monkeypatch.setattr(calendar, name, record)
    view = build_china._china_event_context(now=datetime(2026, 9, 23, 16, tzinfo=timezone.utc))
    assert calls == [(n, '2026-09-24', 14) for n in
        ('china_macro_events', 'high_impact_strip', 'imminent_line')]
    assert view['event_clock']['status'] == 'dated'
    assert view['calendar'] == view['event_strip'] == [] and view['imminent'] is None


def test_event_clock_builder_binds_existing_consumer():
    source = (ROOT / 'scripts/build_china.py').read_text()
    assert 'vm.update(_china_event_context())' in source
    assert 'cec.china_macro_events(horizon_days=14)' not in source
    assert 'cec.high_impact_strip(horizon_days=14)' not in source
    assert 'cec.imminent_line(horizon_days=14)' not in source


def test_event_clock_rendered_card_and_dialog_explain_reference_date():
    from datetime import datetime, timezone
    from scripts import build_china
    from bs4 import BeautifulSoup
    view = build_china._china_event_context(now=datetime(2026, 9, 23, 16, tzinfo=timezone.utc))
    doc = BeautifulSoup(_render_china_risk_case(None, **view), 'html.parser')
    card = doc.find('div', onclick="cnxOpenDlg('cnx-dlg-events')")
    dialog = doc.find(id='cnx-dlg-events')
    for surface in (card, dialog):
        text = surface.get_text(' ', strip=True)
        assert '2026-09-24' in text and 'Calendar reference' in text and '日历基准' in text
        assert 'Schedule estimates' in text and '排期估计' in text
        assert '2026-09-21' not in text
    assert 'Days from reference' in dialog.get_text() and '相对基准日' in dialog.get_text()
    assert 'today' not in view['imminent']['en']


@pytest.mark.parametrize('status,expected', [('dated','No scheduled events'), ('unavailable','Event timing unavailable')])
def test_event_clock_empty_and_unavailable_are_distinct(status, expected):
    from bs4 import BeautifulSoup
    doc = BeautifulSoup(_render_china_risk_case(None, calendar=[], event_strip=[],
        event_clock={'status':status, 'asof':'2026-09-24' if status=='dated' else None}), 'html.parser')
    card = doc.find('div', onclick="cnxOpenDlg('cnx-dlg-events')")
    assert expected in card.get_text()
    assert 'calendar is quiet' not in card.get_text().lower()


def test_event_clock_default_samples_wall_time_once(monkeypatch):
    from datetime import datetime, timezone
    from scripts import build_china
    calls = []
    class Frozen(datetime):
        @classmethod
        def now(cls, tz=None):
            calls.append(tz)
            return cls(2026, 9, 23, 16, tzinfo=timezone.utc)
    monkeypatch.setattr(build_china, 'datetime', Frozen)
    view = build_china._china_event_context()
    assert calls == [timezone.utc]
    assert view['event_clock']['asof'] == '2026-09-24'


def test_event_clock_same_day_event_never_claims_release_is_pending():
    from datetime import datetime, timezone
    from scripts import build_china
    view = build_china._china_event_context(now=datetime(2026, 9, 21, 15, tzinfo=timezone.utc))
    assert view['imminent']['days_until'] == 0
    assert view['imminent']['date'] == '2026-09-21'
    assert 'today' not in view['imminent']['en'] and 'tomorrow' not in view['imminent']['en']
    assert 'Scheduled' in view['imminent']['en'] and '排期' in view['imminent']['zh']


@pytest.mark.parametrize('value', [None, True, False, '123', float('nan'), float('inf'), -float('inf'), 10**400])
def test_connect_context_invalid_flow_is_unknown_not_support(value):
    from engine import china_tier1 as tier
    face = tier.connect_flow_face({'net': value})
    assert face['net'] is None and face['tone'] == 'muted'
    assert face['en'] == 'Unavailable' and face['zh'] == '暂不可用'


@pytest.mark.parametrize('value,en,zh,tone', [(123.4,'Net buying','净买入','up'),
    (-123.4,'Net selling','净卖出','down'), (0,'Flat net flow','净流入为零','muted')])
def test_connect_context_valid_signs_do_not_invent_entry_advice(value,en,zh,tone):
    from engine import china_tier1 as tier
    source = {'net':value,'cum_20d':value*20,'pos_days_20':10,'hold_mktcap':20000}
    face = tier.connect_flow_face(source)
    assert (face['en'],face['zh'],face['tone']) == (en,zh,tone)
    assert face['net'] == value and face['cum_20d'] == value*20
    assert source == {'net':value,'cum_20d':value*20,'pos_days_20':10,'hold_mktcap':20000}


@pytest.mark.parametrize('source', [None, {}, {'pending_quad':'Q1','pending_days':0},
    {'pending_quad':'Q1','pending_days':True}, {'pending_quad':'Q1','pending_days':-1},
    {'pending_quad':'Q1','pending_days':'2'}, {'pending_quad':'Q5','pending_days':2},
    {'quad':'Q4','pending_quad':'Q4','pending_days':2}])
def test_regime_context_does_not_promote_invalid_transition(source):
    from engine import china_tier1 as tier
    assert tier.regime_watch_face(source) is None


@pytest.mark.parametrize('code,en,zh', [('Q1','Goldilocks','金发姑娘'),('Q2','Reflation','再通胀'),
    ('Q3','Stagflation','滞胀'),('Q4','Growth-scare','增长担忧')])
def test_regime_context_watch_is_pending_not_an_accepted_regime(code,en,zh):
    from engine import china_tier1 as tier
    source={'quad':'Q2' if code!='Q2' else 'Q1','pending_quad':code,'pending_days':2}
    face=tier.regime_watch_face(source)
    assert face == {'en':en,'zh':zh,'days':2}
    assert source['quad'] != code


@pytest.mark.parametrize('value', [None, float('nan'), float('inf'), 'bad', False])
def test_connect_context_real_page_survives_missing_values(value):
    from bs4 import BeautifulSoup
    html=_render_china_risk_case(None,internals={'southbound':{'net':value,'cum_20d':None,'pos_days_20':None}})
    soup=BeautifulSoup(html,'html.parser')
    rail=soup.select_one('[data-cn-driver-rail]')
    assert rail and len(rail.select('a')) == 4
    flow=rail.select_one('a[href="#cnx-dlg-flows"]')
    assert 'Unavailable' in flow.get_text() and '暂不可用' in flow.get_text()
    card=soup.select_one('.cnx-card[onclick="cnxOpenDlg(\'cnx-dlg-flows\')"]')
    assert 'Unavailable' in card.get_text() and 'supporting Hong Kong' not in card.get_text()
    assert 'None' not in card.get_text() and 'nan' not in card.get_text().lower()


@pytest.mark.parametrize('value,label', [(123.4,'Net buying'),(-123.4,'Net selling'),(0,'Flat net flow')])
def test_connect_context_real_page_has_scope_and_no_mismatched_units(value,label):
    from bs4 import BeautifulSoup
    html=_render_china_risk_case(None,internals={'southbound':{'net':value,'cum_20d':0,'pos_days_20':0}})
    soup=BeautifulSoup(html,'html.parser'); rail=soup.select_one('[data-cn-driver-rail]')
    assert rail and label in rail.get_text() and 'Hong Kong flows' in rail.get_text()
    assert 'bn' not in rail.get_text() and '亿' not in rail.get_text()
    assert 'Radar state' in rail.get_text() and 'mainland inflows' not in rail.get_text().lower()


@pytest.mark.parametrize('days,visible', [(2,True),(0,False),(-1,False),(True,False),('2',False)])
def test_regime_context_header_and_detail_agree_on_pending_transition(days,visible):
    from bs4 import BeautifulSoup
    html=_render_china_risk_case(None, latest_updates={'quad':'Q4','pending_quad':'Q2','pending_days':days})
    soup=BeautifulSoup(html,'html.parser'); chip=soup.select_one('[data-cn-pending-regime]')
    assert bool(chip) is visible
    if visible:
        assert 'Transition pending' in chip.get_text() and '再通胀' in chip.get_text()
        assert 'Confirmation pending' in soup.get_text()
    else:
        assert 'No pending transition recorded' in soup.get_text()


@pytest.mark.parametrize('field,value', [('cum_20d',None),('cum_20d',float('inf')),
    ('pos_days_20',False),('pos_days_20',21),('pos_days_20',1.5),('hold_mktcap',-1)])
def test_connect_context_invalid_detail_preserves_valid_net(field,value):
    from engine import china_tier1 as tier
    result=tier.connect_flow_face({'net':12,field:value})
    assert result['net']==12 and result[field] is None


def test_regime_context_links_preserve_all_original_deep_destinations():
    from bs4 import BeautifulSoup
    soup=BeautifulSoup(_render_china_risk_case(None),'html.parser')
    links=soup.select('[data-cn-driver-rail] a')
    assert {a['href'] for a in links}=={'#cnx-dlg-policy','#cnx-dlg-flows','#cnx-dlg-risk','#cnx-dlg-property'}
    assert all(soup.select_one(a['href']) is not None for a in links)
    assert soup.select_one('a[href="flow_velocity.html"]') is not None


def test_backdrop_helpers_reach_existing_fast_renderer(tmp_path,monkeypatch):
    import pickle
    from scripts import render_china_fast as fast
    from engine import china_tier1 as tier
    cache=tmp_path/'_dev_china_vm.pkl';cache.write_bytes(pickle.dumps({}))
    monkeypatch.setattr(fast.config,'data_dir',lambda:tmp_path)
    monkeypatch.setattr(fast.config,'load',lambda:{'storage':{'site_dir':str(tmp_path)}})
    modes=[]
    class Template:
        def __init__(self,owner): self.owner=owner
        def render(self,**vm):
            assert self.owner.globals.get('connect_flow_face') is tier.connect_flow_face
            assert self.owner.globals.get('regime_watch_face') is tier.regime_watch_face
            modes.append(vm['mode']);return '<html>contract probe</html>'
    class Env:
        def __init__(self,*args,**kwargs): self.globals={}
        def get_template(self,name):
            assert name=='china.html.j2';return Template(self)
    monkeypatch.setattr(fast,'Environment',Env)
    monkeypatch.setattr(fast,'write_page',lambda path,content:path.write_text(content))
    assert fast.main()==0 and modes==['macro','stocks']
