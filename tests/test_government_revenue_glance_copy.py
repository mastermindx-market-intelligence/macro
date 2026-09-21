"""Government Revenue keeps evidence machinery behind plain workspace language."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "government_revenue.html.j2"
SITE = ROOT / "site" / "government_revenue.html"


def _src() -> str:
    return TEMPLATE.read_text(encoding="utf-8")


def test_primary_workspace_chrome_uses_reader_language() -> None:
    src = _src()
    required = (
        "Procurement intelligence",
        "Track procurement changes",
        "Loading official records",
        "tracked changes",
        "linked companies",
        "Evidence status",
        "Saved research",
        "Change feed",
        "Award activity",
    )
    for phrase in required:
        assert phrase in src
    banned = (
        "Vertical intelligence · procurement",
        "Watch the procurement tape",
        "Reading official receipts",
        "governed changes",
        "mapped exposure",
        "Truth layer",
        "Research briefcase",
        "Decision queue",
    )
    for phrase in banned:
        assert phrase not in src
    assert "{{ t('Award tape','授标脉搏') }}" not in src


def test_snapshot_copy_replaces_evidence_cut_chrome() -> None:
    src = _src()
    assert "{{ t('Snapshot','数据快照') }}" in src
    assert "{{ t('Updated','最近更新') }}" in src
    assert "Showing a compact snapshot while the full workspace loads." in src
    # The detailed inspector keeps an Evidence cut timestamp for auditability.
    assert src.count("Evidence cut") == 1
    assert "Last assembled" not in src
    assert "compact evidence cut" not in src


def test_source_detail_actions_avoid_receipt_jargon() -> None:
    src = _src()
    assert "Source details" in src
    assert "Open official source" in src
    assert "Evidence receipts" not in src
    assert "official receipt" not in src


def test_authority_limit_copy_is_plain_language() -> None:
    src = _src()
    assert "This row stays limited to what the source data can support." in src
    assert "dataset provenance and authority limits" not in src


def test_company_link_legend_is_plain() -> None:
    src = _src()
    assert "Company link found" in src
    assert "Evidence linked" not in src
    assert "Link pending" in src


def test_committed_page_matches_government_revenue_contract() -> None:
    html = SITE.read_text(encoding="utf-8")
    for required in (
        "Procurement intelligence",
        "Track procurement changes",
        "Evidence status",
        "Saved research",
        "Change feed",
        "Source details",
        "Open official source",
        "Company link found",
    ):
        assert required in html
    for banned in (
        "Vertical intelligence · procurement",
        "Truth layer",
        "Research briefcase",
        "Decision queue",
        "Evidence receipts",
        "official receipt",
    ):
        assert banned not in html
    assert '<span class="l-en">Award tape</span>' not in html
