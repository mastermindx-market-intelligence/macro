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
* ``median length (days)`` prints trading sessions, not calendar days
  (``engine/playbook.py:222`` is a row count); the producer's own prose says
  "trading days" (``engine/playbook.py:889``).

Synthetic fixtures only: no ``data/`` or ``site/`` read and no builder call.

Run: MM_DATA_GUARD=off PYTHONPATH=. python3 -m pytest \
    tests/test_regime_history_us_basis.py -q
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from jinja2 import Environment, FileSystemLoader  # noqa: E402

from engine import i18n  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "history.html.j2"

# --- the committed record (values quoted by the design packet's F2) ---------
AGE_NOTE = (
    "This Reflation stretch is 17 trading days old (historical median: 30). "
    "When Reflation ended, it went to: Goldilocks 47%, Stagflation 34%, "
    "Growth scare 19%"
)
AGE_NOTE_ZH = (
    "本轮再通胀已持续 17 个交易日（历史中位数：30）。当再通胀结束时，"
    "它转向了：理想增长 47%、滞胀 34%、增长恐慌 19%"
)
PROGRESS = {"age_days": 17, "median_days": 30, "pct_longer": 75.0,
            "median_remaining_days": 22, "phase": "early", "bar_pct": 19.8,
            "zone_early_pct": 23.3, "zone_mid_pct": 52.0, "n_history": 152}

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

ATOMS_EN = ("17 trading days old", "median 30",
            "75% of predecessors ran longer",
            "about 22 sessions of median remaining",
            "152 periods in the sample", "phase early")
ATOMS_ZH = ("17 个交易日", "中位数 30", "75% 的前期周期持续更久",
            "中位剩余约 22 个交易日", "152 个样本时段", "阶段 早期")

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
    assert "This Reflation stretch is 17 trading days old" in en
    assert "(historical median: 30)" in en
    assert "Goldilocks 47%, Stagflation 34%, Growth scare 19%" in en
    assert "本轮再通胀已持续 17 个交易日（历史中位数：30）" in zh
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
    assert "trading days old" not in en
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
    """F6: engine/playbook.py:222 counts rows of a trading-day frame."""
    html = _render(_latest())
    en, zh = _view(html, "zh"), _view(html, "en")
    assert "median length (trading days)" in en
    assert "存续中位数（交易日）" in zh
    assert "median length (days)" not in en


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
