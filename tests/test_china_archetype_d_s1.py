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
def _render_china_risk_case(recession, action_en="", action_zh="", *, playbook=None):
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
                          ("posture_lane", "posture_tone", "reason_faces", "hero_clause", "slowdown_face")})
    ctx = _radar_dlg_vm({"market_state": market_state}, latest)
    return env.get_template("china.html.j2").render(
        mode="macro", latest=latest, market_state=market_state, sectors=[], radar_dlg=ctx, pb=playbook)


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
