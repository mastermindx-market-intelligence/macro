"""SPEC 2 (W33-LB) — the filing-fingerprint evidence depth reaches the page.

`engine/theme_fingerprint.py` writes, per leg, `n_reporting`, `latest_fy`,
`min_required` and `met_gate`, and returns `None` below `MIN_MEMBERS` so nothing
is fabricated. The template never opened the `fingerprint` object: the
"from filings" mark said "annual … provisional" without a count or a year, and
`prov_mark` fires only on the stage substring, so the fingerprint-only rows
banded NEUTRAL/LOOSE wore no mark at all.

Synthetic fixtures only: every value below is quoted from the committed cascade
record shape. No store, no builder, no network, no `site/` or `data/` write.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# The committed `medical_devices` fingerprint block.
FP_MEDICAL = {
    "n_legs_live": 1,
    "components": {
        "leg7_member_inventory": {"value": 0.434, "n_reporting": 10,
                                  "latest_fy": 2026, "met_gate": True,
                                  "description": "PRODUCER DOCSTRING THAT MUST NOT PRINT"},
        "leg8_member_backlog": {"value": None, "n_reporting": 2,
                                "latest_fy": 2026, "met_gate": False,
                                "description": "SECOND PRODUCER DOCSTRING"},
    },
}
# The committed `glp1_obesity` fingerprint block: a FY2022 backlog read on one
# reporting member, suppressed by the producer's gate.
FP_GLP1 = {
    "n_legs_live": 1,
    "components": {
        "leg7_member_inventory": {"value": 0.33, "n_reporting": 5,
                                  "latest_fy": 2025, "met_gate": True},
        "leg8_member_backlog": {"value": None, "n_reporting": 1,
                                "latest_fy": 2022, "met_gate": False},
    },
}
# The committed `cybersecurity` shape: exactly at the 3-member floor, and a
# stage string with no `(fingerprint)` qualifier, so `prov_mark` never fires.
FP_CYBER = {
    "n_legs_live": 1,
    "components": {
        "leg7_member_inventory": {"value": 0.21, "n_reporting": 3,
                                  "latest_fy": 2026, "met_gate": True},
    },
}


def _row(**over):
    row = {
        "theme": "medical_devices", "name": "Medical Devices",
        "tier": "P", "stage": "PRECIPICE (fingerprint)",
        "bottleneck_band": "TIGHTENING (fingerprint)",
        "bottleneck_text_only": False, "bottleneck_fingerprint_only": True,
        "tightness": 0.434, "bottleneck_regime": True,
        "demand_band": None, "demand_strength": None, "capex_yoy": None,
        "revision_breadth": 0.076, "revision_level": "POSITIVE",
        "broadening_state": None, "est_drift_90d": None,
        "guidance_band": None, "guidance_net": None, "guidance_raisers": None,
        "guidance_cutters": None, "altdata_summary": None, "n_altdata_leading": 0,
        "altdata_members": None, "glut_band": None, "glut_score": None,
        "theme_feed_summary": None, "rationale": "synthetic fixture",
        "entry_ready": False, "entry_note": "synthetic", "score": 61.0,
        "score_detail": {"verdict": "watch", "axes": {}, "caps": []},
        "size_band": None, "size_note": None, "fingerprint": dict(FP_MEDICAL),
    }
    row.update(over)
    return row


def _render(themes, **over):
    env = Environment(loader=FileSystemLoader(str(ROOT / "templates")),
                      autoescape=True)
    ctx = dict(
        cascade={"sizing": None, "demand_pool": None, "dislocation": None},
        themes=themes, stage_counts={}, stage_order=[],
        demand_pool=None, dislocation=None,
        track={"foresight": 0, "bottleneck": 0, "glut": 0, "revisions": 0,
               "guidance": 0, "emergence": 0, "subsector": 0, "recent": []},
        grade=None, emergence=None, subsectors=None, convergence=None, power=None,
        analyst=None, monitor=None, health=None,
        asof="2026-10-20", generated_utc="2026-10-20 00:00 UTC",
        nav_prefix="", active_section="research", active_page="foresight",
    )
    ctx.update(over)
    return env.get_template("foresight.html.j2").render(**ctx)


def _card(html):
    start = html.index('<article class="fx-card')
    return html[start:html.index("</article>", start)]


def _depth(card):
    """The filing-depth receipt only — never a sibling `fx-note`."""
    at = card.index("Filing depth")
    return card[card.rindex("<p", 0, at):card.index("</p>", at)]


def test_reporting_count_and_fiscal_year_render_from_the_committed_row_shape():
    html = _render([_row()])
    depth = _depth(_card(html))
    assert "<b>10</b>" in depth, "the reporting count never reaches the page"
    assert "FY2026" in depth and "财年" in depth
    assert "members reporting" in depth and "家成员披露" in depth
    assert "member inventory" in depth and "成员库存" in depth
    # leg8 was suppressed by the producer's gate: its count shows, never a value.
    assert "<b>2</b>" in depth and "member backlog" in depth
    assert "too few members" in depth and "成员过少" in depth
    assert "0.434" not in html, "a leg value reached the page"
    assert "description" not in depth
    assert "PRODUCER DOCSTRING" not in html


def test_glp1_row_shows_the_fy2025_read_and_the_single_member_leg():
    row = _row(theme="glp1_obesity", name="GLP-1 / Obesity",
               stage="BROADENING (fingerprint)", fingerprint=dict(FP_GLP1))
    html = _render([row])
    depth = _depth(_card(html))
    assert "FY2025" in depth, "the leg7 fiscal year never reaches the page"
    assert "<b>5</b>" in depth
    # The FY2022 backlog read renders as a suppressed leg's year and count only.
    assert "FY2022" in depth and "<b>1</b>" in depth
    assert "too few members" in depth
    assert "0.33" not in html, "a leg value reached the page"


def test_no_fingerprint_object_renders_nothing():
    for row in (_row(fingerprint=None), _row_no_key()):
        html = _render([row])
        assert '<article class="fx-card' in html, "the card stopped rendering"
        card = _card(html)
        assert "Filing depth" not in card
        assert "年报深度" not in card
        assert "members reporting" not in card and "家成员披露" not in card


def _row_no_key():
    row = _row()
    row.pop("fingerprint")
    return row


def test_fingerprint_only_row_without_a_stage_qualifier_still_shows_depth():
    row = _row(theme="cybersecurity", name="Cybersecurity", stage="WATCH",
               bottleneck_band="NEUTRAL", fingerprint=dict(FP_CYBER))
    card = _card(_render([row]))
    assert "from filings" not in card, "prov_mark must not fire on a bare WATCH stage"
    assert "来自年报" not in card
    depth = _depth(card)
    assert "<b>3</b>" in depth and "FY2026" in depth
    assert "too few members" not in depth, "a leg at the floor is not suppressed"
    assert "<b>1</b>" in depth, "n_legs_live never reaches the page"


def test_a_leg_with_no_fiscal_year_never_prints_fynone():
    # `engine/theme_fingerprint.py` emits `latest_fy: None` for a leg no member
    # reported; the count still renders, the year clause does not.
    fp = {
        "n_legs_live": 1,
        "components": {
            "leg7_member_inventory": {"value": 0.21, "n_reporting": 4,
                                      "latest_fy": 2026, "met_gate": True},
            "leg8_member_backlog": {"value": None, "n_reporting": 0,
                                    "latest_fy": None, "met_gate": False},
        },
    }
    html = _render([_row(fingerprint=fp)])
    depth = _depth(_card(html))
    assert "FYNone" not in html, "a missing fiscal year printed as FYNone"
    assert "None" not in depth
    assert "FY2026" in depth and "<b>4</b>" in depth
    assert "<b>0</b>" in depth and "member backlog" in depth
    assert "too few members" in depth
    # One year label, on the leg that has a year; the "?" tip prose is not a label.
    assert depth.count('<span class="l-en">fiscal year</span>') == 1, \
        "the year label outlived its value"
    assert depth.count('<span class="l-zh">财年</span>') == 1


# D03 T36 / F02 + F09: current confirmation-only reads cannot certify
# an early thesis. Reuse the actual-template and fingerprint fixtures above;
# keep historical flags, source stages, counts and withheld values intact.

def _t36_convergence(*, hot=True, earliness=0.8, physical_confirmed=False):
    row = {
        "theme": "medical_devices", "name": "Medical Devices",
        "stage": "PRECIPICE (fingerprint)", "heat": 0.75,
        "n_lit": 3, "n_available": 5, "n_signals": 3,
        "lit_sources": ["demand", "guidance", "analyst"],
        "signals": ["demand", "guidance", "analyst"],
        "earliness": earliness, "earliness_absent": earliness is None,
        "physical_confirmed": physical_confirmed,
    }
    return {"ranked": [row], "heating_up": [row] if hot else [],
            "max_sources": 5, "max_signals": 5, "meta_drivers": []}


def _t36_render(*, mode="CONFIRMER-ONLY", hot=True, earliness=0.8,
                stage="PRECIPICE (fingerprint)", physical_confirmed=False,
                **over):
    return _render(
        [_row(stage=stage, fingerprint=dict(FP_GLP1))],
        convergence=_t36_convergence(hot=hot, earliness=earliness,
                                    physical_confirmed=physical_confirmed),
        health={"mode": mode, "legs": {}} if mode is not None else None,
        **over,
    )


def _t36_hero(html):
    at = html.index('<header class="fx-hero">')
    return html[at:html.index("</header>", at)]


def _t36_convergence_section(html):
    at = html.index('<div class="fx-sec"><span class="sh-dot"></span><h2>')
    end = html.index('<div class="fx-sec"><span class="sh-dot" style=', at)
    return html[at:end]


def _t36_record(html):
    at = html.index("Track record — graded forward vs SPY")
    start = html.rindex("<details", 0, at)
    return html[start:html.index("</details>", at) + len("</details>")]


@pytest.mark.parametrize("stage", [
    "PRECIPICE (fingerprint)", "PRECIPICE (text)", "BROADENING (fingerprint)",
])
def test_t36_current_summary_cannot_promote_an_early_thesis(stage):
    hero = _t36_hero(_t36_render(stage=stage))
    assert "sit early in the cycle right now" not in hero
    assert "处于周期早段" not in hero
    assert "supply is tightening before estimates have moved" not in hero
    assert "Early status is unconfirmed" in hero
    assert "早期状态尚未确认" in hero
    assert "confirmations only" in hero and "仅显示确认信号" in hero


@pytest.mark.parametrize("hot", [True, False])
def test_t36_convergence_and_empty_state_explain_the_missing_lead(hot):
    section = _t36_convergence_section(_t36_render(hot=hot))
    for unsupported in (
        "Heating up early", "正在早期升温", "the earliest heads-up",
        "最早的提示", "they surface here first", "会首先出现在此",
        "still early", "仍属早期", "several agree at once while it is still early",
    ):
        assert unsupported not in section
    assert "Signals converging" in section and "信号共振" in section
    assert "Leading supply inputs are unavailable" in section
    assert "领先供给输入不可用" in section
    # The row or partial-source receipt remains available in either state.
    assert "Medical Devices" in section
    assert "3" in section and "5" in section
    assert "demand" in section and "guidance" in section


@pytest.mark.parametrize("earliness", [0.8, 0.5, 0.2, None])
def test_t36_current_convergence_keeps_source_counts_without_early_certification(earliness):
    section = _t36_convergence_section(_t36_render(earliness=earliness))
    assert "still early" not in section and "仍属早期" not in section
    assert "convergence heat 0.75" in section and "3/5 sources" in section
    assert "PRECIPICE (fingerprint)" in section
    if earliness is None or earliness >= 0.5:
        assert "Early status unconfirmed" in section
        assert "早期状态待确认" in section
    else:
        assert "mid-cycle" in section and "周期中段" in section


def test_t36_conflicting_supply_flag_does_not_override_current_health():
    section = _t36_convergence_section(_t36_render(physical_confirmed=True))
    assert "✓" not in section
    assert "Supply read unconfirmed" in section and "供给读数待确认" in section
    assert "source supply-confirmed: True" in section
    assert "convergence heat 0.75" in section


def test_t36_current_card_keeps_filing_qualifiers_member_floor_and_raw_stage():
    card = _card(_t36_render())
    assert "Supply unconfirmed" in card and "供给待确认" in card
    assert 'title="PRECIPICE (fingerprint)"' in card
    assert "Supply is tight before estimates have moved" not in card
    assert "供给已紧、预期未动" not in card
    assert "from filings" in card and "来自年报" in card
    assert "provisional until a live numeric series confirms" in card
    depth = _depth(card)
    assert "<b>5</b>" in depth and "FY2025" in depth
    assert "<b>1</b>" in depth and "FY2022" in depth
    assert "value withheld — too few members" in depth
    assert "成员过少——数值不予给出" in depth
    assert "0.33" not in card and "None" not in depth


def test_t36_text_basis_qualifier_still_explains_pending_numeric_confirmation():
    card = _card(_t36_render(stage="PRECIPICE (text)"))
    assert "Supply unconfirmed" in card
    assert "early text" in card and "纯文本" in card
    assert "awaiting a hard, numeric supply confirmation" in card
    assert "待硬性数值供给确认" in card


@pytest.mark.parametrize("mode", ["FULL", None])
def test_t36_other_health_modes_keep_existing_current_early_presentation(mode):
    html = _t36_render(mode=mode, physical_confirmed=True)
    hero = _t36_hero(html)
    section = _t36_convergence_section(html)
    assert "sit early in the cycle right now" in hero
    assert "Heating up early" in section and "正在早期升温" in section
    assert "still early" in section and "仍属早期" in section
    assert "supply-confirmed" in section and "供给确认" in section
    assert "Supply unconfirmed" not in _card(html)


def test_t36_historical_grading_and_flag_time_stance_are_mode_independent():
    track = {"foresight": 12, "bottleneck": 2, "glut": 0, "revisions": 5,
             "guidance": 1, "emergence": 0, "subsector": 0,
             "recent": [{"theme": "medical_devices", "asof": "2026-08-01",
                         "stage": "PRECIPICE (fingerprint)",
                         "bottleneck_band": "TIGHTENING (fingerprint)",
                         "members": ["AAA", "BBB"]}]}
    grade = {"n_graded": 4, "pooled_hit_rate": 0.75, "pooled_n_directional": 4,
             "pooled_ci95": [0.3, 0.95], "n_significant_fdr": 0,
             "by_stage": {
                 "PRECIPICE": {"n": 4, "n_dir": 4, "hit_rate": 0.75,
                               "hits": 3, "avg_excess_pct": 2.5},
                 "WATCH": {"n": 2, "hit_rate": None, "avg_excess_pct": None},
             }}
    limited = _t36_record(_t36_render(mode="CONFIRMER-ONLY", track=track, grade=grade))
    full = _t36_record(_t36_render(mode="FULL", track=track, grade=grade))
    assert limited == full
    assert "Early" in limited and "早期" in limited
    assert "control arm" in limited and "对照组" in limited
    assert "2026-08-01" in limited and "AAA" in limited and "BBB" in limited
    assert "75%" in limited and "+2.5%" in limited


def test_t36_render_does_not_mutate_source_convergence_or_fingerprint():
    from copy import deepcopy

    themes = [_row(fingerprint=deepcopy(FP_GLP1))]
    convergence = _t36_convergence()
    original = deepcopy((themes, convergence))
    _render(themes, convergence=convergence,
            health={"mode": "CONFIRMER-ONLY", "legs": {}})
    assert (themes, convergence) == original
