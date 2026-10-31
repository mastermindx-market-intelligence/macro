"""China regime-history page: did each analog's move hold at 120 sessions?

W33 SPEC 4 (finding F7 of the W32D design packet, template-only part):
``site/china_intel/analogs.json`` carries ``fwd_shcomp.h120`` and
``fwd_csi300.h120`` for every record, but ``templates/china_history.html.j2``
printed only the 20-session SHCOMP and the 60-session CSI300 columns — so two
of the five printed analogs pointed the wrong way (2026-04-10: +4.6% at 20
sessions, -4.9% at 120). ``fan.h120.n = 11`` against ``fan.h20.n = 12``: one
analog's 120-session window has not resolved, so a null must print an em dash
exactly like ``:202``/``:204`` already do, never ``0.0%`` and never a blank
cell. ``scripts/build_china.py`` is READ-ONLY, so this is display-only.

Synthetic fixtures only: no ``data/`` or ``site/`` read, no builder call.
Record 1 and record 2's SHCOMP triple are quoted verbatim by the packet; the
fields the packet elides (record 2/3 CSI300 and distances) are lane-filled and
are never asserted on.

Run: MM_DATA_GUARD=off PYTHONPATH=. python3 -m pytest \
    tests/test_regime_history_china_analogs.py -q
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from jinja2 import Environment, FileSystemLoader  # noqa: E402

from engine import i18n  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "china_history.html.j2"
STAMP = "2026-10-20 17:10 UTC"

ANALOGS = [
    {"date": "2024-02-06", "distance": 0.0, "quad": "Q3",
     "fwd_shcomp": {"h20": 0.0711, "h60": 0.0984, "h120": 0.0114},
     "fwd_csi300": {"h20": 0.0615, "h60": 0.0846, "h120": 0.0157}},
    {"date": "2026-04-10", "distance": 0.412, "quad": "Q3",
     "fwd_shcomp": {"h20": 0.0464, "h60": 0.0019, "h120": -0.0492},
     "fwd_csi300": {"h20": 0.0388, "h60": -0.0104, "h120": -0.0412}},
    {"date": "2016-02-12", "distance": 0.523, "quad": "Q3",
     "fwd_shcomp": {"h20": 0.0551, "h60": 0.0623, "h120": 0.0806},
     "fwd_csi300": {"h20": 0.0497, "h60": 0.0583, "h120": 0.0742}},
]
UNRESOLVED = [{"date": "2026-10-16", "distance": 0.0, "quad": "Q3",
               "fwd_shcomp": {"h20": 0.01, "h60": 0.02, "h120": None},
               "fwd_csi300": {"h20": 0.01, "h60": 0.02, "h120": None}}]

# the analog table sits inside {% if phase_strip or era_table or phase_current %}
# (templates/china_history.html.j2:105), so a truthy phase_current is what makes
# the block reachable at all.
PHASE_CURRENT = {"phase": "BROADENING", "confidence": 0.62, "asof": "2026-10-16"}

MARKERS = ("sh120", "csi120", "SHCOMP 120d", "CSI300 120d", "generated_utc")
BANNED = ("实时", "申报", "证伪", "validated", "已验证", "live", "forecast",
          "falsifier", "refuted", "z-score", "percentile rank", "probability",
          "概率", "当前", "最新", "独立")


def _render(analogs) -> str:
    env = Environment(loader=FileSystemLoader(str(ROOT / "templates")),
                      autoescape=False)
    env.globals.update(td=i18n.td, tr=i18n.tr)
    html = env.get_template("china_history.html.j2").render(
        latest={"date": "2026-10-16"}, generated_utc=STAMP,
        chart_regime="", chart_axes="", phase_strip=[], era_table=[],
        phase_current=dict(PHASE_CURRENT), analogs=analogs)
    return re.sub(r"\s+", " ", html)


def _view(html: str, drop: str) -> str:
    out = re.sub(r'<span class="l-%s">.*?</span>' % drop, "", html)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", out))


def _analog_row(html: str, date: str) -> str:
    """The one <tr> body carrying `date` — the analog table is the only place a
    full ISO date is printed inside a row."""
    for chunk in html.split("<tr>")[1:]:
        body = chunk.split("</tr>")[0]
        if date in body and "<td" in body:
            return body
    raise AssertionError("no analog row for %s" % date)


def test_h120_columns_render_the_committed_analog_values() -> None:
    html = _render(ANALOGS)
    en = _view(html, "zh")
    assert "SHCOMP 120d" in en and "CSI300 120d" in en
    assert "+1.1%" in en, "2024-02-06 SHCOMP h120 (0.0114) did not render"
    assert "-4.9%" in en, "2026-04-10 SHCOMP h120 (-0.0492) did not render"
    assert "+8.1%" in en, "2016-02-12 SHCOMP h120 (0.0806) did not render"
    assert "+1.6%" in en and "-4.1%" in en and "+7.4%" in en, "CSI300 h120 missing"
    assert "上证120日" in _view(html, "en") and "沪深300 120日" in _view(html, "en")


def test_unresolved_h120_renders_an_em_dash() -> None:
    html = _render(UNRESOLVED)
    row = _analog_row(html, "2026-10-16")
    assert row.count("—") == 2, row
    assert "0.0%" not in row, "a null h120 must never print as zero"
    assert "+1.0%" in row and "+2.0%" in row, "the resolved horizons vanished"


def test_existing_h20_and_h60_columns_unchanged() -> None:
    html = _render(ANALOGS)
    en = _view(html, "zh")
    assert "SHCOMP 20d" in en and "CSI300 60d" in en
    row = _analog_row(html, "2024-02-06")
    text = _view(row, "zh")
    assert "+7.1%" in text, "the 20-session SHCOMP cell changed"
    assert "+8.5%" in text, "the 60-session CSI300 cell changed"
    assert text.index("+7.1%") < text.index("+1.1%"), "column order shifted"
    assert text.index("+8.5%") < text.index("+1.6%"), "column order shifted"


def test_median_column_states_its_unit() -> None:
    """data/china_regime/regime_history.parquet has a row for every Monday to Friday
    in its span, 12-25 and 1-1 included, so a length is a count of weekdays."""
    html = _render(ANALOGS)
    en, zh = _view(html, "zh"), _view(html, "en")
    assert "median length (weekdays)" in en
    assert "存续中位数（周一至周五计，天）" in zh
    assert "median length (days)" not in en
    assert "存续中位数（天）" not in zh


def test_panel_degrades_with_no_analogs() -> None:
    html = _render([])
    assert "Historical analogs" not in html
    assert "Display-only analog readout" not in html
    assert "Cycle Phase Memory" in html, "the whole phase panel was skipped"
    assert "None" not in html.split("Cycle Phase Memory")[1]


def test_generation_stamp_prints_utc_once() -> None:
    html = _render(ANALOGS)
    stamp = re.search(
        r'<p class="muted"><span class="l-en">Generated</span>.*?</p>', html)
    assert stamp, "no generation stamp"
    assert stamp.group(0).count("UTC") == 1, stamp.group(0)
    assert STAMP in stamp.group(0)


def test_bilingual_and_copy_laws() -> None:
    html = _render(ANALOGS)
    for phrase in ("SHCOMP 120d", "CSI300 120d"):
        assert re.search(r'<span class="l-en">%s</span>' % re.escape(phrase), html)
    for phrase in ("上证120日", "沪深300 120日"):
        assert re.search(r'<span class="l-zh">%s</span>' % re.escape(phrase), html)
    src = TEMPLATE.read_text(encoding="utf-8")
    for phrase in ("Display-only analog readout", "no forward projection",
                   "CN-SYS-R1", "no extrapolation"):
        assert phrase in src, "a CN-SYS disclaimer was dropped: %s" % phrase
    touched = [ln for ln in src.splitlines()
               if any(mark in ln for mark in MARKERS)]
    assert len(touched) >= 8, "the new China lines are missing: %d" % len(touched)
    for line in touched:
        assert len(line) <= 100, "added line over 100 chars: %r" % line[:40]
        low = line.lower()
        for bad in BANNED:
            assert bad not in low, "banned token %r in an added line" % bad
        assert not re.search(r"#[0-9a-fA-F]{3,8}\b", line), "new colour literal"
        assert "color-mix" not in line
