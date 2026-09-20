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


def test_restored_dashboard_borrows_readability_not_archetype_structure() -> None:
    """New readability helpers may improve the old dashboard without replacing its deep rows."""
    assert "{% set _stance = posture_lane(" in TPL
    assert "{% set _hero_clause = hero_clause(" in TPL
    assert "{% set _todo_faces = reason_faces(" in TPL
    assert 'class="mx5-regime-pill{% if _stance_tone == \'warn\' %} rp-yellow{% elif _stance_tone == \'down\' %} rp-red{% endif %}"' in TPL
    assert "Full playbook & evidence →" in TPL
    for marker in (
        "ROW 1: What To Do + Upcoming Events",
        "ROW 2: Pullback Risk / Top Stocks + Sentiment + Sector Temperature",
        "ROW 3: Policy Monitor + Connect Flows + Macro News",
        "ROW 4: Property + AI Brief + Alerts Centre",
    ):
        assert marker in TPL


def test_macro_news_keeps_card_but_reads_as_dated_changes() -> None:
    assert "{{ t('Macro News','宏观新闻') }}" in TPL
    assert "{{ t('What Changed','最近变化') }}" in TPL
    assert "(h.published or h.date or '')[5:10]" in TPL
    assert "h.title_en or h.title" in TPL
    assert "h.title_zh or h.title" in TPL


def test_deep_footer_keeps_old_landings_and_adds_targeted_new_landings() -> None:
    for href in (
        "china_stocks.html",
        "china_heatmap.html",
        "china_intel.html",
        "china_allocation.html",
        "china_history.html",
        "aibrief.html",
        "china_policy_watch.html",
        "china_news.html",
        "alerts.html",
    ):
        assert f'href="{href}"' in TPL
