"""SPEC 4 (W33-LB) — say when the estimate-trend leg has no window.

`engine/theme_revisions.py` emits `broadening_state` and the cascade copies it
into every row; `engine/foresight_score.py` reads it inside the acceleration
axis, scoring an unmapped `INSUFFICIENT_HISTORY` at the same default as
`FLAT_LOW`. The template never mentioned the key, so a lit Estimates stop and a
scored acceleration axis hid the fact that the trend leg had no window.

Copy must not exceed the producer: the state may only be described as
"no trend window" / "暂无趋势窗口" — never as flat estimates, never as a proxy
direction, and never with a field the vm does not carry.

Synthetic fixtures only. No store, no builder, no network, no `site/` or
`data/` write.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _row(**over):
    """A Tier-P card row in the committed `rare_earth_critical_min` shape."""
    row = {
        "theme": "rare_earth_critical_min", "name": "Rare Earth / Critical Minerals",
        "tier": "P", "stage": "WATCH",
        "bottleneck_band": "TIGHT", "bottleneck_text_only": False, "tightness": 0.9,
        "bottleneck_regime": True, "demand_band": None, "demand_strength": None,
        "capex_yoy": None, "revision_breadth": 0.667, "revision_level": "POSITIVE",
        "broadening_state": "INSUFFICIENT_HISTORY", "est_drift_90d": None,
        "guidance_band": None, "guidance_net": None, "guidance_raisers": None,
        "guidance_cutters": None, "altdata_summary": None, "n_altdata_leading": 0,
        "altdata_members": None, "glut_band": None, "glut_score": None,
        "theme_feed_summary": None, "rationale": "synthetic fixture",
        "entry_ready": False, "entry_note": "synthetic", "score": 45.0,
        "score_detail": {"verdict": "watch", "base": 69.9, "n_axes_live": 5,
                         "axes": {"magnitude": None, "acceleration": 0.39,
                                  "bottleneck": None, "pricing_power": 0.43,
                                  "underpricing": 0.94, "purity": None, "timing": 0.4},
                         "caps": ["WATCH (late) -> capped at 45"]},
        "size_band": None, "size_note": None,
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


def _estimates_stop(card):
    """The Estimates relay stop's opening `<div>` tag."""
    at = card.index(">Estimates</span>")
    return card[card.rindex('<div class="fx-stop', 0, at):at]


def test_insufficient_history_wears_a_visible_mark():
    card = _card(_render([_row()]))
    assert "no trend window" in card, "the gap is still invisible"
    assert "暂无趋势窗口" in card
    # The fix must not change `l4`: the Estimates stop stays lit.
    assert "fx-stop lit" in _estimates_stop(card)
    # The sentinel itself never reaches the reader, in a mark or in the receipt.
    assert "INSUFFICIENT_HISTORY" not in card


def test_real_direction_states_reach_the_receipt_only():
    shapes = (("grid_electrification", "RISING"), ("memory_storage", "ROLLING"),
              ("nuclear_power", "MIXED"), ("defense_aerospace", "FLAT_LOW"))
    for theme, state in shapes:
        card = _card(_render([_row(theme=theme, name=theme, broadening_state=state)]))
        titles = re.findall(r'title="([^"]*)"', card)
        assert any("trend " + state in ti for ti in titles), state
        assert "no trend window" not in card, state
        assert "暂无趋势窗口" not in card, state
        assert "fx-prov" not in card, state


def test_absent_state_renders_nothing():
    for row in (_row(broadening_state=None), _row_no_key()):
        card = _card(_render([row]))
        assert "no trend window" not in card
        assert "暂无趋势窗口" not in card
        assert "trend " not in card
        assert "None" not in card, "the interpreter sentinel reached the page"
        assert "Estimates / revision breadth +0.67" in card


def _row_no_key():
    row = _row()
    row.pop("broadening_state")
    return row


def test_source_guard_no_proxy_or_window_copy():
    lines = (ROOT / "templates" / "foresight.html.j2").read_text(
        encoding="utf-8").splitlines()
    new = [ln for ln in lines if ("broadening_state" in ln or "no trend window" in ln
                                  or "暂无趋势窗口" in ln)]
    assert new, "the trend-state lines disappeared"
    for ln in new:
        low = ln.casefold()
        assert "broadening_proxy" not in low, ln
        assert "basis_days" not in low, ln
        assert "flat" not in low, ln
        assert "forecast" not in low, ln
    text = "\n".join(lines).casefold()
    assert "broadening_proxy" not in text
    assert "basis_days" not in text
