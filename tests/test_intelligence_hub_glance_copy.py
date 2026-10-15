"""Intelligence Hub keeps machine receipts off the primary reading path."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

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
    """Conditional labels are exercised by explicit full-template states below."""
    html = SITE.read_text(encoding="utf-8")
    for banned in ("Validated confluence buy", "UNGRADED · n=0", "pre-registered significance bar", ">proven<", "⚡"):
        assert banned not in html


def test_structured_watch_condition_renders_human_text_only() -> None:
    html = _macro("watchcopy", "{{ watchcopy({'text': 'Revenue falls below expectations.', 'text_zh': '营收低于预期。', 'check': {'kind': 'rel_return', 'threshold': -0.05}}) }}")
    assert 'Revenue falls below expectations.' in html
    assert '营收低于预期。' in html
    assert 'rel_return' not in html and 'threshold' not in html


def test_watch_condition_keeps_legacy_text_and_escapes_markup() -> None:
    html = _macro("watchcopy", "{{ watchcopy('A legacy condition') }}")
    assert 'A legacy condition' in html
    html = _macro("watchcopy", "{{ watchcopy({'text': '<img src=x onerror=alert(1)>'}) }}")
    assert '<img ' not in html
    assert '&lt;img' in html


def test_watch_condition_never_stringifies_invalid_shapes() -> None:
    for value in ("none", "42", "[]", "{'check': {'kind': 'rel_return'}}", "{'text': {'unexpected': 1}}"):
        html = _macro("watchcopy", "{{ watchcopy(" + value + ") }}")
        assert 'Review condition unavailable' in html
        assert '复核条件暂缺' in html
        assert 'rel_return' not in html and 'unexpected' not in html


def test_mobile_command_rows_have_a_full_width_explanation() -> None:
    src = TEMPLATE.read_text(encoding="utf-8")
    assert 'class="led-metrics"' in src and 'class="led-analysis"' in src
    assert '.led-row > .led-analysis{grid-column:2 / -1;grid-row:2;' in src
    assert '{{ watchcopy(d.falsifier) }}' in src
    assert '{{ d.falsifier|e }}' not in src


def test_rendered_watch_conditions_have_no_serialized_check() -> None:
    """The full template path stays safe even when today's page has zero watches."""
    env = Environment(loader=FileSystemLoader(str(TEMPLATES)), autoescape=True)
    env.globals["region_for"] = lambda _ticker: "us"
    falsifier = {
        "text": "Revenue falls below expectations.",
        "text_zh": "营收低于预期。",
        "check": {"subject_ticker": "TEST", "horizon_d": 20},
    }
    row = {
        "ticker": "TEST",
        "opportunity_score": 80,
        "composite_conviction": 80,
        "directions": {},
        "stage": "emerging",
        "entry_gate": None,
        "trajectory": None,
        "flags": [],
        "leading_gap": 0,
        "edge_drivers": [],
        "falsifier": falsifier,
        "price": None,
        "edge_remaining": 0.5,
        "n_confirm": 0,
        "source_mix": [],
        "sectors": [],
    }
    hub = {
        "command": [row],
        "emerging": [],
        "discovery": [],
        "exhausted": [],
        "catalysts": [],
        "track_record": None,
        "desk_grader": {},
        "sector_heat": [],
        "disclaimer": "",
        "n_universe": 1,
        "n_actionable": 1,
        "macro_context": {},
        "desks": {},
        "as_of": "2026-09-27",
        "counts": {},
    }
    html = env.get_template("intelligence_hub.html.j2").render(
        hub=hub,
        built="2026-09-27T00:00:00+00:00",
        mode="intel_hub",
        qledger_chips={},
        china=None,
        market_pulse_roster=["TEST"],
        research_implications={"cards": []},
    )
    watches = re.findall(r'<div class="watch">(.*?)</div>', html, re.S)
    assert len(watches) == 1
    watch = watches[0]
    assert "Revenue falls below expectations." in watch
    assert "营收低于预期。" in watch
    assert "subject_ticker" not in watch and "horizon_d" not in watch
    assert "&#39;text&#39;" not in watch and "&#39;check&#39;" not in watch


def _render_glance_page(*, entry_gate, qledger_chips=None) -> str:
    """Render conditional copy through the shipped template with synthetic inputs."""
    env = Environment(loader=FileSystemLoader(str(TEMPLATES)), autoescape=True)
    env.globals["region_for"] = lambda _ticker: "us"
    row = {
        "ticker": "TEST",
        "opportunity_score": 80,
        "composite_conviction": 80,
        "directions": {},
        "stage": "emerging",
        "entry_gate": entry_gate,
        "trajectory": None,
        "flags": [],
        "leading_gap": 0,
        "edge_drivers": [],
        "falsifier": None,
        "price": None,
        "edge_remaining": 0.5,
        "n_confirm": 0,
        "source_mix": [],
        "sectors": [],
    }
    hub = {
        "command": [row],
        "emerging": [],
        "discovery": [],
        "exhausted": [],
        "catalysts": [],
        "track_record": None,
        "desk_grader": {},
        "sector_heat": [],
        "disclaimer": "",
        "n_universe": 1,
        "n_actionable": 1,
        "macro_context": {},
        "desks": {},
        "as_of": "2026-09-27",
        "counts": {},
    }
    return env.get_template("intelligence_hub.html.j2").render(
        hub=hub,
        built="2026-09-27T00:00:00+00:00",
        mode="intel_hub",
        qledger_chips=qledger_chips or {},
        china=None,
        market_pulse_roster=["TEST"],
        research_implications={"cards": []},
    )


def test_full_template_renders_populated_plain_language_states() -> None:
    html = _render_glance_page(
        entry_gate={"buyable": True, "tier": "T2"},
        qledger_chips={
            "news": {"state": "UNGRADED", "css_class": "ql-ungraded"},
            "alt_data": {"state": "ACCRUING", "css_class": "ql-accruing"},
            "radar": {"state": "GRADED", "css_class": "ql-graded-pos"},
        },
    )
    assert 'class="chip en-buy"' in html
    assert '<span class="l-en">ready to review</span>' in html
    assert '<span class="l-zh">可复核</span>' in html
    for css, en, zh in (
        ("ql-ungraded", "no history", "暂无记录"),
        ("ql-accruing", "building record", "记录积累中"),
        ("ql-graded-pos", "measured", "已有记录"),
    ):
        assert (
            f'<span class="gw {css}"><span class="l-en">{en}</span>'
            f'<span class="l-zh">{zh}</span></span>'
        ) in html


@pytest.mark.parametrize(
    "entry_gate",
    [None, {}, {"buyable": False, "tier": "T2"}],
    ids=["absent", "empty", "not-buyable"],
)
def test_full_template_does_not_invent_conditional_states(entry_gate) -> None:
    html = _render_glance_page(entry_gate=entry_gate, qledger_chips={})
    assert 'class="chip en-buy"' not in html
    assert '<span class="l-en">ready to review</span>' not in html
    assert '<span class="l-zh">可复核</span>' not in html
    states = re.findall(
        r'<span class="gw ([^"]+)"><span class="l-en">([^<]+)</span>'
        r'<span class="l-zh">([^<]+)</span></span>',
        html,
    )
    assert states
    assert set(states) == {("ql-ungraded", "no history", "暂无记录")}


@pytest.mark.parametrize(
    "banned",
    ["Validated confluence buy", "UNGRADED · n=0", "pre-registered significance bar", ">proven<", "⚡"],
)
def test_committed_page_contract_rejects_forbidden_copy(tmp_path, monkeypatch, banned) -> None:
    html = _render_glance_page(entry_gate=None)
    synthetic_site = tmp_path / "intelligence_hub.html"
    synthetic_site.write_text(html.replace("</body>", f"<div>{banned}</div></body>"), encoding="utf-8")
    monkeypatch.setitem(globals(), "SITE", synthetic_site)
    with pytest.raises(AssertionError):
        test_committed_page_matches_plain_language_contract()
