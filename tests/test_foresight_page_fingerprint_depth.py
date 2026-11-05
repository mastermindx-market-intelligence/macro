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
