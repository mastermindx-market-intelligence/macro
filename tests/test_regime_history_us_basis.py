"""US regime-history page: the regime-age note and an honest sample window.

W33 SPEC 1 (findings F1/F2/F6 of the W32D design packet):

* ``engine/playbook.py:886-898`` composes ``regime_age_note`` /
  ``regime_age_note_zh`` and ``:875-884`` composes ``progress``; both are
  published at ``:936-938`` and reach the vm whole through
  ``scripts/build_site.py:7924`` (``latest=latest``) — yet at the seed no
  template anywhere rendered them, so the page printed a distribution with no
  marker for where the stretch in force sits inside it.
* The panel's help text claimed ``since 2007`` while the printed periods
  (127/152/72/91 = 442) are the unwindowed sample: 287 of those 442 segments
  start before 2007 (``engine/playbook.py:226-241`` applies no window).
* The length is a row count (``quad_segments``), and
  ``data/regime/regime_history.parquet`` holds one row for every Monday to
  Friday in its span: 15,497 rows, 15,497 weekdays, Christmas included. So it
  is a count of weekdays, market holidays included, and the labels say that.
* ``quad_segments`` ends with the period still running, whose length is only
  its age so far. The note and the progress atoms now read finished periods
  only: on the committed record the median for Reflation is 31 of 151, not 30
  of 152. The four table rows still come from ``transition_stats`` through
  ``scripts/build_site.py``, which this change does not touch, so that row
  still prints 30.

Synthetic fixtures only: no ``data/`` or ``site/`` read and no builder call.

Run: MM_DATA_GUARD=off PYTHONPATH=. python3 -m pytest \
    tests/test_regime_history_us_basis.py -q
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from jinja2 import Environment, FileSystemLoader  # noqa: E402

from engine import i18n  # noqa: E402
from engine import playbook  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "history.html.j2"

# --- the committed record, read through the finished periods only ------------
AGE_NOTE = (
    "This Reflation stretch is 17 weekdays old (historical median: 31). "
    "When Reflation ended, it went to: Goldilocks 47%, Stagflation 34%, "
    "Growth scare 19%"
)
AGE_NOTE_ZH = (
    "本轮再通胀已持续 17 天（周一至周五计，历史中位数：31）。当再通胀结束时，"
    "它转向了：理想增长 47%、滞胀 34%、增长恐慌 19%"
)
PROGRESS = {"age_days": 17, "median_days": 31, "pct_longer": 75.0,
            "median_remaining_days": 22, "phase": "early", "bar_pct": 19.8,
            "zone_early_pct": 23.3, "zone_mid_pct": 52.0, "n_history": 151}

# --- the four rows site/history.html prints (F1: 127/152/72/91) -------------
LIFESPAN_ROWS = [
    {"name": "Goldilocks", "n": 127, "median": 29,
     "next": "Reflation 38%, Stagflation 27%",
     "next_zh": "再通胀 38%、滞胀 27%"},
    {"name": "Reflation", "n": 152, "median": 30,
     "next": "Goldilocks 47%, Stagflation 34%",
     "next_zh": "理想增长 47%、滞胀 34%"},
    {"name": "Stagflation", "n": 72, "median": 16,
     "next": "Growth scare 44%, Goldilocks 31%",
     "next_zh": "增长恐慌 44%、理想增长 31%"},
    {"name": "Growth scare", "n": 91, "median": 23,
     "next": "Goldilocks 52%, Reflation 26%",
     "next_zh": "理想增长 52%、再通胀 26%"},
]

REMAINING_EN = ("among past runs that reached this age and continued, the median "
                "further length was 22 weekdays")
REMAINING_ZH = "历史上达到此存续期后继续延续的周期，其后续长度中位数为 22 天（周一至周五计）"
ATOMS_EN = ("17 weekdays old", "median 31",
            "75% of predecessors ran longer", REMAINING_EN,
            "151 periods in the sample", "phase early")
ATOMS_ZH = ("17 天（周一至周五计）", "中位数 31", "75% 的前期周期持续更久",
            REMAINING_ZH, "151 个样本时段", "阶段 早期")

BANNED = ("实时", "申报", "证伪", "validated", "已验证", "live", "forecast",
          "falsifier", "refuted", "z-score", "percentile rank", "probability",
          "概率", "当前", "最新", "独立")


def _latest(playbook: dict | None = "default") -> dict:
    out = {"date": "2026-10-19"}
    if playbook == "default":
        out["playbook"] = {"regime_age_note": AGE_NOTE,
                           "regime_age_note_zh": AGE_NOTE_ZH,
                           "progress": dict(PROGRESS)}
    elif playbook is not None:
        out["playbook"] = playbook
    return out


def _render(latest: dict, rows: list | None = None) -> str:
    """Render the page the way scripts/build_site.py:7923-7929 does."""
    env = Environment(loader=FileSystemLoader(str(ROOT / "templates")),
                      autoescape=False)
    env.globals.update(td=i18n.td, tr=i18n.tr)
    html = env.get_template("history.html.j2").render(
        latest=latest, generated_utc="2026-10-20 16:50",
        chart_regime="", chart_axes="",
        lifespan_rows=LIFESPAN_ROWS if rows is None else rows)
    return re.sub(r"\s+", " ", html)


def _view(html: str, drop: str) -> str:
    """The reader's text in one language: drop the other language's spans."""
    out = re.sub(r'<span class="l-%s">.*?</span>' % drop, " ", html)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", out))


def _panel(html: str) -> str:
    return html.split("Regime lifespans")[1]


def _age_block() -> list:
    lines = TEMPLATE.read_text(encoding="utf-8").splitlines()
    start = next((i for i, ln in enumerate(lines)
                  if "latest.playbook.progress" in ln), None)
    if start is None:
        return []
    end = next(i for i in range(start + 1, len(lines))
               if lines[i].strip() == "<table>")
    return lines[start:end]


def test_renders_the_committed_regime_age_note() -> None:
    html = _render(_latest())
    en, zh = _view(html, "zh"), _view(html, "en")
    assert "This Reflation stretch is 17 weekdays old" in en
    assert "(historical median: 31)" in en
    assert "Goldilocks 47%, Stagflation 34%, Growth scare 19%" in en
    assert "本轮再通胀已持续 17 天（周一至周五计，历史中位数：31）" in zh
    assert "理想增长 47%、滞胀 34%、增长恐慌 19%" in zh
    hit = re.search(r'<span class="l-zh">\s*(本轮再通胀[^<]*?)\s*</span>', html)
    assert hit, "the zh twin of the age note is not inside an l-zh span"
    assert re.sub(r"\s+", "", hit.group(1)) == re.sub(r"\s+", "", AGE_NOTE_ZH)


def test_progress_atoms_render_when_the_prose_note_is_none() -> None:
    """engine/playbook.py:886-888 returns None unless cur['median_days'] and
    nxt — the atomic progress fields must carry the panel on their own."""
    pb = {"regime_age_note": None, "regime_age_note_zh": None,
          "progress": dict(PROGRESS)}
    html = _render(_latest(pb))
    en, zh = _view(html, "zh"), _view(html, "en")
    assert "This Reflation stretch" not in en
    for phrase in ATOMS_EN:
        assert phrase in en, f"progress atom missing from EN: {phrase!r}"
    for phrase in ATOMS_ZH:
        assert phrase in zh, f"progress atom missing from zh: {phrase!r}"


def test_block_absent_when_playbook_missing() -> None:
    """The HK/CN/CA `latest` shape has no playbook key: degrade to the seed
    rendering, never to a blank row or a leaked None."""
    html = _render({"date": "2026-10-19"})
    panel = _panel(html)
    en = _view(html, "zh")
    assert panel.count("<tr>") == 5, "the lifespan table lost or gained a row"
    assert "None" not in panel
    assert "weekdays old" not in en
    assert "periods in the sample" not in en
    for row in LIFESPAN_ROWS:
        assert row["name"] in html


def test_help_text_no_longer_claims_a_2007_window() -> None:
    html = _render(_latest())
    en, zh = _view(html, "zh"), _view(html, "en")
    assert "since 2007" not in en
    assert "自 2007 年以来" not in zh
    assert "2007" not in en and "2007" not in zh
    assert "Every regime period in this classifier" in en
    assert "the front page's odds come from" in en
    assert "首页的概率即来自这些基准概率" in zh


def test_median_column_states_its_unit() -> None:
    """quad_segments counts rows, and the frame has one for every weekday."""
    html = _render(_latest())
    en, zh = _view(html, "zh"), _view(html, "en")
    assert "median length (weekdays)" in en
    assert "存续中位数（周一至周五计，天）" in zh
    assert "median length (days)" not in en
    assert "median length (trading days)" not in en
    assert "存续中位数（交易日）" not in zh


def test_median_remaining_states_its_past_sample() -> None:
    """It is a fact about past runs, so it must not read as this run's future."""
    pb = {"regime_age_note": None, "regime_age_note_zh": None,
          "progress": dict(PROGRESS)}
    html = _render(_latest(pb))
    en, zh = _view(html, "zh"), _view(html, "en")
    assert REMAINING_EN in en
    assert REMAINING_ZH in zh
    for old in ("of median remaining", "about 22", "remaining", "trading days"):
        assert old not in en, old
    for old in ("中位剩余", "剩余", "个交易日"):
        assert old not in zh, old


def test_median_remaining_clause_absent_when_no_past_run_went_further() -> None:
    pb = {"regime_age_note": None, "regime_age_note_zh": None,
          "progress": {**PROGRESS, "median_remaining_days": None}}
    html = _render(_latest(pb))
    assert "among past runs" not in _view(html, "zh")
    assert "历史上达到此存续期" not in _view(html, "en")
    assert "None" not in _panel(html)


# --- engine: the period still running is not a sample of its own length --------

def _series(lengths: list) -> "playbook.pd.Series":
    """[(quad, n_weekdays), ...] on a Monday-to-Friday index."""
    pd = playbook.pd
    quads = [quad for quad, n in lengths for _ in range(n)]
    return pd.Series(quads, index=pd.bdate_range(end="2026-10-16", periods=len(quads)))


def _alternating(q2_lengths: list, running: int) -> "playbook.pd.Series":
    """Finished Q2 periods with a 5-weekday Q1 after each, then Q2 still running."""
    closed = [seg for n in q2_lengths for seg in (("Q2", n), ("Q1", 5))]
    return _series(closed + [("Q2", running)])


EIGHT = [10, 20, 30, 40, 50, 60, 70, 80]


def test_quad_segments_ends_with_the_period_still_running() -> None:
    """The premise of closed_durations. If this changes, iloc[:-1] drops a real one."""
    seg = playbook.quad_segments(_alternating([10, 20], 7))
    assert seg["days"].tolist() == [10, 5, 20, 5, 7]
    assert seg.iloc[-1]["quad"] == "Q2"


def test_closed_durations_drops_only_the_running_period() -> None:
    durs = playbook.closed_durations(_alternating([10, 20], 7), "Q2")
    assert durs.tolist() == [10, 20]
    assert playbook.closed_durations(_alternating([10, 20], 7), "Q1").tolist() == [5, 5]


def test_closed_median_is_none_with_no_finished_period() -> None:
    frame = _series([("Q1", 5), ("Q2", 3)])
    assert playbook.closed_median(frame, "Q2") is None
    assert playbook.closed_median(frame, "Q1") == 5
    assert playbook.closed_median(_alternating([10, 20, 60], 100), "Q2") == 20
    assert playbook.closed_median(_alternating([26, 27], 100), "Q2") == 26


def test_progress_reads_finished_periods_only() -> None:
    """Nine Q2 periods with the running one, eight without: every figure shifts."""
    got = playbook.regime_progress(_alternating(EIGHT, 35), "Q2", 35)
    assert got["n_history"] == 8
    assert got["median_days"] == 45, "40 would mean the running period was counted"
    assert got["pct_longer"] == 62.0, "56 would mean it inflated the denominator"
    assert got["median_remaining_days"] == 25
    assert got["age_days"] == 35
    assert got["phase"] == "mid"
    assert got["bar_pct"] == pytest.approx(47.9)
    assert got["zone_early_pct"] == pytest.approx(45.3)
    assert got["zone_mid_pct"] == pytest.approx(77.0)


def test_progress_needs_eight_finished_periods() -> None:
    assert playbook.regime_progress(_alternating(EIGHT[:7], 35), "Q2", 35) is None
    assert playbook.regime_progress(_alternating(EIGHT, 35), "Q2", 35) is not None


def test_progress_past_every_finished_period() -> None:
    got = playbook.regime_progress(_alternating(EIGHT, 100), "Q2", 100)
    assert got["pct_longer"] == 0.0
    assert got["median_remaining_days"] is None
    assert got["phase"] == "overdue"
    assert got["bar_pct"] == 100.0


def test_age_note_is_the_pinned_text_on_the_finished_median() -> None:
    nxt = {"Q1": 0.47, "Q3": 0.34, "Q4": 0.19}
    en, zh = playbook.regime_age_note(_alternating([21, 31, 41], 500), "Q2", 17, nxt)
    assert en == AGE_NOTE
    assert zh == AGE_NOTE_ZH


@pytest.mark.parametrize("lengths, nxt", [
    ([("Q1", 5), ("Q2", 3)], {"Q1": 1.0}),
    ([("Q2", 10), ("Q1", 5), ("Q2", 3)], {}),
])
def test_age_note_is_absent_without_a_median_or_a_next(lengths, nxt) -> None:
    assert playbook.regime_age_note(_series(lengths), "Q2", 3, nxt) == (None, None)


def test_build_playbook_reads_progress_and_note_through_the_helpers() -> None:
    """build_playbook is too heavy to call here, so pin the wiring in its source."""
    tree = ast.parse((ROOT / "engine" / "playbook.py").read_text(encoding="utf-8"))
    fn = next(n for n in tree.body
              if isinstance(n, ast.FunctionDef) and n.name == "build_playbook")
    calls = {n.func.id for n in ast.walk(fn)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    assert {"regime_progress", "regime_age_note"} <= calls
    assert "quad_segments" not in calls


def test_added_lines_are_within_the_length_and_copy_laws() -> None:
    block = _age_block()
    assert block, "the regime-age block is missing from history.html.j2"
    src = TEMPLATE.read_text(encoding="utf-8").splitlines()
    touched = list(block) + [ln for ln in src if "median length" in ln
                             or "Every regime period" in ln
                             or "本分类器中的每一个周期时段" in ln]
    assert len(touched) > len(block), "the header/help edits are missing"
    for line in touched:
        assert len(line) <= 100, f"added line over 100 chars: {line[:40]!r}"
        low = line.lower()
        for bad in BANNED:
            assert bad not in low, f"banned token {bad!r} in an added line"
        assert not re.search(r"#[0-9a-fA-F]{3,8}\b", line), "new colour literal"
        assert "color-mix" not in line
