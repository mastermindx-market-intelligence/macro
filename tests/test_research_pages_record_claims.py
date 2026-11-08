"""The report landing page states only what its own catalog record supports.

Two render-path drops on `site/research/<slug>.html`, both values already present in
the committed catalog:

* the Pro gate promised "The full summary" unconditionally, including for records
  whose `summary_points` is empty. Those records were never summarized upstream
  (`engine/research_vault/ingest.py:551-553`), so the page says none is available
  and does not imply one is on the way;
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

_NO_SUMMARY_EN = "No summary is available for this report."
_NO_SUMMARY_ZH = "本篇暂无摘要。"
_MEMBERS_EN = "PDF is for MastermindX Pro members."
_MEMBERS_ZH = "原始 PDF 为 MastermindX Pro 会员专享。"


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
    assert _NO_SUMMARY_EN in html
    assert _NO_SUMMARY_ZH in html
    zh = html[html.index('<span class="l-zh">', html.index(_NO_SUMMARY_EN)):]
    assert _NO_SUMMARY_ZH in zh[:zh.index("</span>")]


def test_zero_summary_record_does_not_imply_a_summary_is_coming():
    """engine/research_vault/ingest.py:551-553: upstream never summarized these."""
    html = _render(_ZERO)
    for phrase in ("still being prepared", "摘要仍在整理中", "整理中", "Summary pending",
                   "summary is coming"):
        assert phrase not in html, phrase


def test_zero_summary_record_keeps_the_pdf_for_members_clause():
    html = _render(_ZERO)
    en = html[html.index(_NO_SUMMARY_EN):]
    assert _MEMBERS_EN in " ".join(en[:en.index("</span>")].split())
    zh = html[html.index(_NO_SUMMARY_ZH):]
    assert _MEMBERS_ZH in zh[:zh.index("</span>")]


def test_summary_with_points_still_promises_the_full_summary_and_its_count():
    item = dict(_ZERO, summary_points=["One point.", "Two point.", "Three point."])
    html = _render(item)
    assert "The full summary (3 key points)" in html
    assert _NO_SUMMARY_EN not in html
    assert _NO_SUMMARY_ZH not in html


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
    assert rp._norm(_ZERO)["top_pick"] is False
    absent = {k: v for k, v in _PICK.items() if k != "top_pick"}
    assert rp._norm(absent)["top_pick"] is False


def test_norm_counts_only_a_real_true_as_a_top_pick():
    """A bare truthiness test made the string "false" a desk highlight."""
    for value in ("false", "False", "true", "0", 1, 0, "", None, [True]):
        n = rp._norm(dict(_PICK, top_pick=value))
        assert n["top_pick"] is False, repr(value)


def test_string_false_renders_no_highlight_flag():
    assert "Highlighted" not in _render(dict(_PICK, top_pick="false"))
