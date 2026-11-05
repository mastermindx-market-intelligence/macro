"""SPEC 1 (W33-LB) — the pre-cap score base and the axis count reach the page.

`engine/foresight_score.py` returns `score_detail.base` and
`score_detail.n_axes_live` for every row, and `display_axes` always carries all
seven axes with the dark ones as `None`. The public page printed the raw
interpreter sentinel into the `fx-score` title and never said what the score was
capped *from*, nor on how many axes it rests.

Synthetic fixtures only: every value below is quoted from the committed cascade
record shape. No store, no builder, no network, no `site/` or `data/` write.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# The committed `space_satellite` axes dict: seven keys, four of them dark.
AXES_SPACE = {
    "magnitude": None, "acceleration": 0.35, "bottleneck": 0.55,
    "pricing_power": 1.0, "underpricing": 0.53, "purity": None, "timing": 0.4,
}
# The committed `rare_earth_critical_min` axes dict.
AXES_RARE = {
    "magnitude": None, "acceleration": 0.39, "bottleneck": None,
    "pricing_power": 0.43, "underpricing": 0.94, "purity": None, "timing": 0.4,
}


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
                         "axes": dict(AXES_RARE),
                         "caps": ["WATCH (late) -> capped at 45"]},
        "size_band": None, "size_note": None,
    }
    row.update(over)
    return row


def _render(themes, **over):
    """Full-page render through the real template with the complete vm key set."""
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


def test_base_and_axis_count_render_from_the_committed_row_shape():
    card = _card(_render([_row()]))
    assert "69.9" in card, "the uncapped base never reaches the card"
    assert "before the cap" in card and "上限前" in card
    assert re.search(r">5</b>\s*<span class=\"l-en\">of 7 axes reading</span>", card)
    assert "/ 7 项有读数" in card


def test_no_literal_none_in_the_axis_tooltip():
    row = _row(score_detail={"verdict": "watch", "base": 69.9, "n_axes_live": 4,
                             "axes": dict(AXES_SPACE),
                             "caps": ["WATCH (late) -> capped at 45"]})
    html = _render([row])
    assert "None" not in html, "the interpreter sentinel reaches the public bytes"
    title = re.search(r'<span class="fx-score" title="([^"]*)"', html).group(1)
    assert title == ("acceleration 0.35 · bottleneck 0.55 · pricing_power 1.0"
                     " · underpricing 0.53 · timing 0.4")


def test_base_hidden_when_absent_or_equal():
    missing = _card(_render([_row(score_detail=None)]))
    assert "before the cap" not in missing and "上限前" not in missing
    assert "fx-cap" not in missing

    null_base = _card(_render([_row(score_detail={"verdict": "watch", "base": None,
                                                  "axes": {}, "caps": []})]))
    assert "before the cap" not in null_base and "上限前" not in null_base
    assert "fx-cap" not in null_base

    # The committed `fintech_payments` shape: score 38.3 / base 38.3 / caps [].
    equal = _card(_render([_row(score=38.3, stage="BROADENING",
                                score_detail={"verdict": "watch", "base": 38.3,
                                              "n_axes_live": 6, "axes": {},
                                              "caps": []})]))
    assert "before the cap" not in equal and "上限前" not in equal
    assert "38.3" not in equal
    assert "fx-cap" not in equal
    # The axis count is separate from the cap and still renders.
    assert re.search(r">6</b>\s*<span class=\"l-en\">of 7 axes reading</span>", equal)


def test_axis_marker_counts_only_the_axes_the_producer_sent():
    four = _card(_render([_row(score_detail={"verdict": "watch", "base": 60.0,
                                             "n_axes_live": 4,
                                             "axes": dict(AXES_SPACE),
                                             "caps": []})]))
    assert re.search(r">4</b>\s*<span class=\"l-en\">of 7 axes reading</span>", four)
    assert ">7</b>" not in four

    # n_axes_live (3) disagrees with axes|length (7 keys): the producer's own
    # count wins, so a `n_axes_live -> axes|length` mutant goes red here.
    disagree = _card(_render([_row(score_detail={"verdict": "watch", "base": 60.0,
                                                 "n_axes_live": 3,
                                                 "axes": dict(AXES_SPACE),
                                                 "caps": []})]))
    assert re.search(r">3</b>\s*<span class=\"l-en\">of 7 axes reading</span>", disagree)
    assert ">4</b>" not in disagree and ">7</b>" not in disagree
