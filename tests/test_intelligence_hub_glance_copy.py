"""Intelligence Hub keeps machine receipts off the primary reading path."""
from __future__ import annotations

import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"
TEMPLATE = TEMPLATES / "intelligence_hub.html.j2"
SITE = ROOT / "site" / "intelligence_hub.html"


def _macro(name: str, markup: str) -> str:
    text = TEMPLATE.read_text(encoding="utf-8")
    start = text.index("{% macro " + name)
    end_marker = "{%- endmacro %}"
    end = text.index(end_marker, start) + len(end_marker)
    macro_src = text[start:end]
    prelude = ""
    if name == "qlword":
        for var in ("QL_EN", "QL_ZH"):
            vm = re.search(r"{% set " + var + r" = .*? %}", text)
            assert vm, f"{var} missing"
            prelude += vm.group(0)
    env = Environment(autoescape=True)
    return env.from_string(prelude + macro_src + markup).render()


def test_entry_badge_is_review_language_not_machine_buy_jargon() -> None:
    html = _macro("entrybadge", "{{ entrybadge({'buyable': true, 'tier': 'T2'}) }}")
    assert "ready to review" in html.lower()
    assert "可复核" in html
    assert "Technical tier: T2" in html
    assert "Validated confluence buy" not in html
    assert "entry T2" not in html
    assert "⚡" not in html


def test_qledger_states_render_as_human_status_words() -> None:
    cases = [
        ("UNGRADED", "ql-ungraded", "no history", "暂无记录"),
        ("ACCRUING", "ql-accruing", "building record", "记录积累中"),
        ("GRADED", "ql-graded-pos", "measured", "已有记录"),
    ]
    for state, css, en, zh in cases:
        html = _macro("qlword", "{{ qlword({'state': '" + state + "', 'css_class': '" + css + "'}) }}")
        assert en in html
        assert zh in html
        assert f">{state.lower()}<" not in html


def test_ranking_explainer_is_short_plain_tier_two_copy() -> None:
    text = TEMPLATE.read_text(encoding="utf-8")
    m = re.search(r'aria-label="How this page ranks names"\s+data-tip-en="([^"]+)"', text)
    assert m, "ranking help tooltip missing"
    tip = m.group(1)
    assert len(tip.split()) <= 80
    for banned in ("genuine signal ×", "Deliberately NOT ranked", "crowd favourite"):
        assert banned not in tip
    assert "room for the move" in tip.lower()
    assert "Policy intent is shown as context" in tip


def test_track_record_uses_evidence_wording_not_proof_language() -> None:
    text = TEMPLATE.read_text(encoding="utf-8")
    assert "pre-registered significance bar" not in text
    assert "{{ t('proven', '已验证') }}" not in text
    assert "preset evidence threshold" in text
    assert "{{ t('supported', '有证据') }}" in text


def test_desk_rail_does_not_expose_raw_qledger_labels() -> None:
    text = TEMPLATE.read_text(encoding="utf-8")
    rail = text[text.index('{# ── desk rail.'):text.index('{# ── EMERGING EDGE')]
    assert "qc.label" not in rail
    assert "UNGRADED · n=0" not in rail
    assert "qlreceipt(qc" in rail


def test_committed_page_matches_plain_language_contract() -> None:
    html = SITE.read_text(encoding="utf-8")
    for required in ("ready to review", "no history", "building record", "measured"):
        assert required in html
    for banned in ("Validated confluence buy", "UNGRADED · n=0", "pre-registered significance bar", ">proven<", "⚡"):
        assert banned not in html
