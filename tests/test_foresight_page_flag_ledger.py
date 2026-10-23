"""SPEC 3 (W33-LB) — `track.recent` dates the flag ledger in the Track-record panel.

`scripts/build_foresight.py` already passes `track.recent` (the eight newest
`data/foresight/log.jsonl` rows, newest first) and the panel's own prose claims
"point-in-time membership", yet the panel showed seven undated integers: no
`asof`, no stage at fire time, no members. The template never read the key.

Synthetic fixtures only: every value below is quoted from the committed ledger
rows. No store, no builder, no network, no `site/` or `data/` write.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# The two newest committed ledger rows, verbatim (`data/foresight/log.jsonl`).
RECENT_TWO = [
    {"theme": "glp1_obesity", "asof": "2026-10-18",
     "ts": "2026-10-18T05:41:51.588091+00:00", "stage": "PRECIPICE (fingerprint)",
     "bottleneck_band": "TIGHTENING (fingerprint)", "revision_breadth": 0.076,
     "language_accel": 0.0, "late_line_basis": "percentile_cov",
     "members": ["LLY", "AMGN", "HIMS", "PFE", "ZBH"]},
    {"theme": "ag_fertilizer", "asof": "2026-10-17",
     "ts": "2026-10-17T05:41:12.004512+00:00", "stage": "GLUT-RISK",
     "bottleneck_band": "LOOSE", "revision_breadth": 0.416,
     "language_accel": 0.0, "late_line_basis": "percentile_cov",
     "members": ["CF", "MOS", "CTVA", "FMC", "SMG", "DE", "AGCO"]},
]
SEVEN = ("cascade flags", "supply regimes", "fade flags", "estimate reads",
         "guidance tilts", "discovery candidates", "subsector flags")


def _track(recent):
    tr = {"foresight": 318, "bottleneck": 96, "glut": 0, "revisions": 18,
          "guidance": 12, "emergence": 4, "subsector": 7}
    if recent is not None:
        tr["recent"] = recent
    return tr


def _render(track, **over):
    env = Environment(loader=FileSystemLoader(str(ROOT / "templates")),
                      autoescape=True)
    ctx = dict(
        cascade={"sizing": None, "demand_pool": None, "dislocation": None},
        themes=[], stage_counts={}, stage_order=[],
        demand_pool=None, dislocation=None, track=track,
        grade=None, emergence=None, subsectors=None, convergence=None, power=None,
        analyst=None, monitor=None, health=None,
        asof="2026-10-20", generated_utc="2026-10-20 00:00 UTC",
        nav_prefix="", active_section="research", active_page="foresight",
    )
    ctx.update(over)
    return env.get_template("foresight.html.j2").render(**ctx)


def _panel(html):
    """The Track-record `<details>` only — never a sibling panel."""
    start = html.index("graded forward vs SPY")
    return html[start:html.index("</details>", start)]


def test_recent_flag_rows_render_with_their_asof_and_stage():
    panel = _panel(_render(_track([dict(r) for r in RECENT_TWO])))
    assert "2026-10-18" in panel, "the newest ledger row is still undated"
    assert "2026-10-17" in panel
    assert "glp1 obesity" in panel and "ag fertilizer" in panel
    for tk in ("LLY", "AMGN", "HIMS", "PFE", "ZBH", "CF", "MOS"):
        assert tk in panel, "point-in-time membership never reaches the page"
    # The stance goes through stance_word(sbase(...)); the machine stage stays a receipt.
    assert "Early" in panel and "早期" in panel
    assert "Fading" in panel and "退潮" in panel
    body = re.sub(r'title="[^"]*"', "", panel)
    assert "PRECIPICE" not in body, "internal stage vocabulary reached the glance tier"
    assert "GLUT-RISK" not in body


def test_ledger_dates_sit_inside_the_track_record_panel():
    lines = (ROOT / "templates" / "foresight.html.j2").read_text(
        encoding="utf-8").splitlines()
    comment = next(i for i, ln in enumerate(lines)
                   if "forward-graded track record" in ln)
    recent = next(i for i, ln in enumerate(lines) if "track.recent" in ln)
    close = next(i for i in range(comment, len(lines))
                 if lines[i].strip() == "</details>")
    assert comment < recent < close, "the ledger block left the Track-record panel"
    for ln in lines:
        if "title=" in ln:
            assert "track.recent" not in ln, "track.recent must never sit in a title"


def test_empty_and_absent_recent_render_nothing():
    for track in (_track([]), _track(None)):
        panel = _panel(_render(track))
        assert "<table" not in panel, "an empty ledger must not draw a table"
        assert "date each fired" not in panel and "触发日期" not in panel
        for label in SEVEN:
            assert label in panel, "a count chip disappeared"
        assert "<b>318</b>" in panel


def test_row_without_members_or_stage_degrades():
    rows = [{"theme": "memory_storage", "asof": "2026-10-16"},
            {"theme": "space_satellite", "asof": "2026-10-15", "stage": None,
             "members": None}]
    html = _render(_track(rows))
    panel = _panel(html)
    assert "2026-10-16" in panel and "2026-10-15" in panel
    assert "No read" in panel and "暂无读数" in panel
    assert "None" not in panel, "the interpreter sentinel reached the public bytes"
