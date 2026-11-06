"""SPEC 3 (W33-LB) — `track.recent` dates the flag ledger in the Track-record panel.

`scripts/build_foresight.py` already passes `track.recent` (the eight newest
`data/foresight/log.jsonl` rows, newest first) and the panel's own prose claims
"point-in-time membership", yet the panel showed seven undated integers: no
`asof`, no stage at fire time, no members. The template never read the key.

Synthetic render inputs only: RECENT_TWO quotes the committed ledger rows.
T37 summary fixtures exercise presentation; they are not live measurements.
No store, no builder, no network, no `site/` or `data/` write.
"""
from __future__ import annotations

import re
import sys
from html.parser import HTMLParser
from pathlib import Path

import pytest
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


# D03 T37 / F08 — pending 90-day outcomes remain visible after grading starts.
# Synthetic summary fixtures; counts are producer inputs, never reconstructed.
def _t37_grade(**over):
    value = {
        "n_total": 351, "n_graded": 122, "n_pending": 229,
        "pooled_hit_rate": 0.216, "pooled_n_directional": 51,
        "pooled_ci95": [0.12, 0.35], "n_significant_fdr": 0,
        "by_stage": {
            "PRECIPICE": {"n": 51, "n_dir": 51, "hit_rate": 0.216,
                          "hits": 11, "avg_excess_pct": 1.2},
            "RE-RATING": {"n": 71, "hit_rate": None, "avg_excess_pct": 1.7},
        },
    }
    value.update(over)
    return value


class _T37Chips(HTMLParser):
    """Collect chip text through nested EN/ZH spans."""

    def __init__(self):
        super().__init__()
        self.chips = []
        self.depth = 0
        self.start_depth = None
        self.current = []

    def handle_starttag(self, tag, attrs):
        if tag == "span":
            self.depth += 1
            if "fx-rchip" in dict(attrs).get("class", "").split():
                self.start_depth = self.depth
                self.current = []

    def handle_data(self, data):
        if self.start_depth is not None:
            self.current.append(data)

    def handle_endtag(self, tag):
        if tag == "span":
            if self.depth == self.start_depth:
                self.chips.append(" ".join(" ".join(self.current).split()))
                self.start_depth = None
            self.depth -= 1


def _t37_chips(panel):
    parser = _T37Chips()
    parser.feed(panel)
    return parser.chips


def _t37_pending(panel):
    return [chip for chip in _t37_chips(panel)
            if "pending 90d" in chip or "待90天" in chip]


@pytest.mark.parametrize("pending", [0, 7, 229])
def test_t37_mixed_summary_shows_declared_pending_count_once(pending):
    panel = _panel(_render(_track(RECENT_TWO),
                           grade=_t37_grade(n_pending=pending)))
    chips = _t37_pending(panel)
    assert len(chips) == 1, "pending outcomes disappeared after grading began"
    assert chips[0].startswith(str(pending) + " ")
    assert chips[0].count("pending 90d") == 1
    assert chips[0].count("待90天") == 1
    if pending == 7:
        assert "229" not in chips[0], "the template inferred total minus graded"


@pytest.mark.parametrize("total,pending", [(229, 229), (0, 0)])
def test_t37_all_pending_and_empty_ledger_keep_declared_count(total, pending):
    panel = _panel(_render(_track([]), grade=_t37_grade(
        n_total=total, n_graded=0, n_pending=pending,
        pooled_hit_rate=None, pooled_n_directional=0, by_stage={})))
    assert len(_t37_pending(panel)) == 1
    assert _t37_pending(panel)[0].startswith(str(pending) + " ")
    assert ("flags logged" if total else "no flags logged yet") in panel
    assert "pooled 90d" not in panel


_T37_MISSING = object()


@pytest.mark.parametrize("graded", [0, 122])
@pytest.mark.parametrize("pending", [
    _T37_MISSING, None, -1, True, False, 1.5, "229", [], {},
], ids=["missing", "null", "negative", "true", "false", "fraction",
        "string", "array", "object"])
def test_t37_unavailable_pending_never_fabricates_a_count(graded, pending):
    grade = _t37_grade(n_graded=graded)
    if pending is _T37_MISSING:
        grade.pop("n_pending")
    else:
        grade["n_pending"] = pending
    panel = _panel(_render(_track([]), grade=grade))
    assert _t37_pending(panel) == []
    assert "None" not in panel


def test_t37_pending_preserves_directional_control_and_flag_time_receipts():
    panel = _panel(_render(_track(RECENT_TWO), grade=_t37_grade()))
    chips = _t37_chips(panel)
    pooled = next(chip for chip in chips if "pooled 90d" in chip)
    assert "22% (51)" in pooled and "(122)" not in pooled
    control = next(chip for chip in chips if "control arm" in chip)
    assert "fwd excess" in control and "前瞻超额" in control
    assert "Late" in control and "偏晚" in control
    assert "+1.7%" in control and "(n=71)" in control
    assert "hit-rate" not in control and "命中率" not in control
    historical = panel[panel.index("<table"):panel.index("</table>") + 8]
    baseline = _panel(_render(_track(RECENT_TWO)))
    assert historical == baseline[baseline.index("<table"):
                                  baseline.index("</table>") + 8]
    assert len(_t37_pending(panel)) == 1


def test_t37_control_only_graded_results_still_show_pending():
    grade = _t37_grade(
        n_total=300, n_graded=71, n_pending=229,
        pooled_hit_rate=None, pooled_n_directional=0,
        by_stage={"RE-RATING": {"n": 71, "hit_rate": None, "avg_excess_pct": 1.7}},
    )
    panel = _panel(_render(_track(RECENT_TWO), grade=grade))
    chips = _t37_chips(panel)
    assert len(_t37_pending(panel)) == 1
    assert any("control arm" in chip and "(n=71)" in chip for chip in chips)
    assert not any("pooled 90d" in chip or "hit-rate" in chip for chip in chips)


@pytest.mark.parametrize("grade", [None, {}])
def test_t37_absent_grade_does_not_create_pending_count(grade):
    panel = _panel(_render(_track([]), grade=grade))
    assert _t37_pending(panel) == []
    for label in SEVEN:
        assert label in panel
