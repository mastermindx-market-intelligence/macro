"""Allocation is a Tier-1 surface: meaning first, quant receipts behind disclosure."""

from __future__ import annotations

import html as html_lib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "allocation.html.j2"
SITE = ROOT / "site" / "allocation.html"


def _glance_text(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"<script\b.*?</script>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<style\b.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<details\b.*?</details>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return " ".join(html_lib.unescape(text).split())


def test_template_uses_plain_primary_section_names() -> None:
    src = TEMPLATE.read_text(encoding="utf-8")
    for phrase in (
        "Lower-risk option",
        "What to add or trim",
        "Theme leadership",
        "Leadership handoff",
        "Long-history check",
        "How Mastermind AI uses this page",
        "Emerging themes",
    ):
        assert phrase in src
    for old in (
        "Optional de-risk overlay",
        "Buy & sell entries — the playbook",
        "Narrative lifecycle board",
        "What is actually validated — sector backtest",
        "AI desk guardrails",
        "Candidate themes — discovery radar",
    ):
        assert old not in src


def test_theme_table_keeps_quant_receipts_off_the_glance_columns() -> None:
    src = TEMPLATE.read_text(encoding="utf-8")
    start = src.index("<!-- ============ 02")
    end = src.index("<!-- ============ 03", start)
    board = src[start:end]
    assert ">Hurst<" not in board
    assert "{{ t('Score', '评分') }}" not in board
    assert "zfmt(cr.crowding_z)" in board  # retained only as a tooltip receipt
    assert "t('Crowded','拥挤')" in board
    assert "t('Normal','正常')" in board


def test_long_history_details_keep_machine_statistics_behind_click() -> None:
    src = TEMPLATE.read_text(encoding="utf-8")
    start = src.index("<!-- ============ 04")
    end = src.index("<!-- ============ 05", start)
    history = src[start:end]
    assert '<details class="study-details">' in history
    assert "See long-history evidence" in history
    assert "Test strength" in history
    assert "DSR" in history  # exact receipt still exists inside disclosure
    assert "B.verdict[k]" not in history
    for raw in ("validated_risk_control", "display_only", "modest_or_none", "no_basket_drawdown_edge"):
        assert raw not in history


def test_ai_rules_are_human_copy_not_raw_contract_fields() -> None:
    src = TEMPLATE.read_text(encoding="utf-8")
    start = src.index("<!-- ============ 05")
    end = src.index("<!-- live desk", start)
    ai = src[start:end]
    for raw_expr in ("A.overall_verdict", "A.reader_contract", "A.do_not_conclude", "A.ai_directive"):
        assert raw_expr not in ai
    assert '<details class="panel study-details ai-use">' in ai


def test_committed_allocation_glance_has_no_machine_language() -> None:
    text = _glance_text(SITE)
    for required in (
        "Lower-risk option",
        "Theme leadership",
        "Leadership handoff",
        "Long-history check",
        "Emerging themes",
    ):
        assert required in text
    for banned in (
        "DSR",
        "Hurst",
        "validated_risk_control",
        "display_only",
        "discipline_not_prediction",
        "rank-IC",
        "z 1.91",
        "What is actually validated",
    ):
        assert banned not in text
