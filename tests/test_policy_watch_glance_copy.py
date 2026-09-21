"""Policy Watch keeps ledger mechanics out of the primary reading path."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "policy_watch.html.j2"
SITE = ROOT / "site" / "policy_watch.html"


def _src() -> str:
    return TEMPLATE.read_text(encoding="utf-8")


def test_confidence_tags_name_the_subject() -> None:
    src = _src()
    assert "High confidence" not in src
    assert "Medium confidence" not in src
    assert "Low confidence" not in src
    assert "Analysis confidence: high" in src
    assert "Analysis confidence: medium" in src
    assert "Analysis confidence: low" in src
    assert "分析把握：较高" in src


def test_void_calls_use_track_record_language_not_scoring_language() -> None:
    src = _src()
    assert "{{ t('Not scored','不计分') }}" not in src
    assert "{{ t('Excluded','不纳入记录') }}" in src
    assert "{{ t('not scored','不计分') }}" not in src
    assert "{{ t('excluded','不纳入记录') }}" in src
    assert "Excluded from track record:" in src
    assert "不纳入记录：" in src


def test_featured_calls_hide_internal_ids_but_audit_list_keeps_them() -> None:
    src = _src()
    featured = src[src.index('<div class="pw-ledger">'):src.index('<details class="pw-details">', src.index('<div class="pw-ledger">'))]
    assert '<span class="pw-call-id">{{ call.id }}</span>' not in featured
    expanded_start = src.index("{{ t('See all calls','查看全部判断') }}")
    expanded = src[expanded_start:src.index('</details>', expanded_start) + len('</details>')]
    assert '<span class="pw-call-id">{{ call.id }}</span>' in expanded


def test_market_views_use_next_review_language() -> None:
    src = _src()
    assert "{{ t('Review by','复核日期') }}" not in src
    assert "{{ t('Next review','下次复核') }}" in src


def test_committed_page_matches_plain_policy_ledger_contract() -> None:
    html = SITE.read_text(encoding="utf-8")
    for required in (
        "Analysis confidence: high",
        "Analysis confidence: medium",
        "Excluded from track record:",
        "Next review",
    ):
        assert required in html
    for banned in (
        ">Not scored<",
        "Not scored:",
        ">High confidence<",
        ">Medium confidence<",
        ">Low confidence<",
    ):
        assert banned not in html


def test_primary_featured_ledger_has_no_pxx_ids() -> None:
    html = SITE.read_text(encoding="utf-8")
    start = html.index('<div class="pw-ledger">')
    end = html.index('<details class="pw-details">', start)
    featured = html[start:end]
    assert 'class="pw-call-id"' not in featured
    expanded = html[end:html.index('</details>', end) + len('</details>')]
    assert 'class="pw-call-id"' in expanded
