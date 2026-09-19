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
