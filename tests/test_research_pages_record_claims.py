"""The report landing page states only what its own catalog record supports.

Two render-path drops on `site/research/<slug>.html`, both values already present in
the committed catalog:

* the Pro gate promised "The full summary" unconditionally, including for records
  whose `summary_points` is empty (the producer's own label for that state is
  "Summary pending", `scripts/build_research_vault.py:198`);
* `items[].top_pick` — the desk's own highlight flag, house label `Highlighted /
  精选` — never reached `_norm`, so 73 flagged reports landed with no endorsement.

Fixtures are synthetic and inline; the committed catalog is never a fixture. Each
fixture mirrors the shape of one real record quoted in the W32F design census.
"""
from __future__ import annotations

import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import build_research_pages as rp  # noqa: E402

# Shaped like the committed 0-point record `marketdesk-3bhwj6ebg0t-fa3dbd`.
_ZERO = {
    "id": "marketdesk-3bhwj6ebg0t-fa3dbd",
    "title": "GS Fishman Cross Border M&A Flow Update 22 Sep 2026",
    "institution": "S&T",
    "side": "sell",
    "published_at": "2026-09-22T06:14:00Z",
    "summary_points": [],
    "pages": None,
    "language": None,
    "top_pick": False,
}

# Shaped like the committed `top_pick: true` record `marketdesk-2vgkwavht24-a7588c`.
_PICK = {
    "id": "marketdesk-2vgkwavht24-a7588c",
    "title": "JPM US Market Intelligence | Afternoon Briefing Oct 14",
    "institution": "J.P. Morgan",
    "side": "sell",
    "published_at": "2026-10-15T08:52:07Z",
    "pages": 14,
    "language": "en",
    "top_pick": True,
    "summary_points": ["CPI Surprise & Inflation Pressure: a hotter-than-consensus print."],
}

_PENDING_EN = "The summary for this report is still being prepared"
_PENDING_ZH = "摘要仍在整理中"


def _render(item: dict) -> str:
    env = Environment(loader=FileSystemLoader("templates"),
                      autoescape=True, trim_blocks=True, lstrip_blocks=True)
    n = rp._norm(item)
    canonical = f"{rp.CANONICAL_BASE}/research/x.html"
    md = f"{n['inst']} research. {n['teaser']}"
    return env.get_template("research_report.html.j2").render(
        n=n, canonical=canonical, meta_desc=md,
        jsonld_str=rp._jsonld(n, canonical, md), related=[],
        excerpt_paras=[], site_base=rp.CANONICAL_BASE)


def _rr_top(html: str) -> str:
    """The `.rr-top` chrome block: institution row, desk-type stamp, highlight pin."""
    start = html.index('<div class="rr-top">')
    end = html.index("<h1>", start)
    return html[start:end]


def test_zero_summary_record_never_promises_a_full_summary():
    html = _render(_ZERO)
    assert "The full summary" not in html
    assert _PENDING_EN in html
    assert _PENDING_ZH in html
    zh = html[html.index('<span class="l-zh">', html.index(_PENDING_EN)):]
    assert _PENDING_ZH in zh[:zh.index("</span>")]


def test_summary_with_points_still_promises_the_full_summary_and_its_count():
    item = dict(_ZERO, summary_points=["One point.", "Two point.", "Three point."])
    html = _render(item)
    assert "The full summary (3 key points)" in html
    assert _PENDING_EN not in html


def test_top_pick_record_shows_the_desk_highlight_flag():
    html = _render(_PICK)
    top = _rr_top(html)
    assert "Highlighted" in top
    assert "精选" in top


def test_non_top_pick_record_shows_no_highlight_flag():
    assert "Highlighted" not in _render(dict(_PICK, top_pick=False))
    absent = {k: v for k, v in _PICK.items() if k != "top_pick"}
    assert "Highlighted" not in _render(absent)


def test_norm_exposes_top_pick_as_a_bool():
    assert rp._norm(_PICK)["top_pick"] is True
    assert rp._norm(dict(_PICK, top_pick=1))["top_pick"] is True
    assert rp._norm(_ZERO)["top_pick"] is False
    absent = {k: v for k, v in _PICK.items() if k != "top_pick"}
    assert rp._norm(absent)["top_pick"] is False
