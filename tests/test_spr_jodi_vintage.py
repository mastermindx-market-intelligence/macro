"""JODI vintage on the SPR page: the world total carries its reporters' own months.

Covers scripts/build_spr._global_jodi_vm (the recency gate plus the as_of / oldest /
excluded keys it records), the "Global picture" JODI tile rendered from a
committed-shaped record, and the page copy that must quote the producer's own
~2-3 month publication lag instead of a hardcoded 1-2 months. No network, no
data/ or site/ reads: every fixture is an inline dict/frame.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd
from jinja2 import Environment

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine import strategic_reserves as sr            # noqa: E402
from scripts.build_spr import _global_jodi_vm          # noqa: E402

REPO = Path(__file__).resolve().parent.parent
TEMPLATE = (REPO / "templates/spr.html.j2").read_text(encoding="utf-8")
LINES = TEMPLATE.splitlines(True)
MACROS = "".join(LINES[:8])          # the template's own t() / mb() / tbadge() macros
SCFG = {"iea_public_mb": 1500.0, "iea_industry_mb": 600.0, "iea_min_days": 90}


def _monthly(values, start, assess=1):
    idx = pd.date_range(start, periods=len(values), freq="MS")
    return pd.DataFrame({"level": [float(v) for v in values],
                         "assess": [assess] * len(values)}, index=idx)


def _slice_lines(marker):
    i = next(n for n, ln in enumerate(LINES) if marker in ln)
    j = next(n for n, ln in enumerate(LINES) if "OFFICIAL GOLD" in ln)
    return MACROS + "".join(LINES[i:j])


def _render_global_tile(agg):
    """Render the GLOBAL AGGREGATE slice and return just the JODI tile div."""
    html = Environment(autoescape=True).from_string(_slice_lines("GLOBAL AGGREGATE")).render(
        agg=agg, scfg=SCFG)
    needle = "JODI reporters"
    if needle not in html:
        return html
    start = html.rfind('<div class="ie">', 0, html.index(needle))
    depth, i = 0, start
    while True:
        m = re.compile(r"<div\b|</div>").search(html, i)
        depth += 1 if m.group(0) == "<div" else -1
        i = m.end()
        if depth == 0:
            return html[start:i]


def _committed_shaped_agg(**over):
    agg = {"total_mb": 1562.0, "n_reporting": 14, "as_of": "2026-07", "oldest": "2026-03",
           "excluded": ["AE", "BR"], "n_excluded": 2}
    agg.update(over)
    return agg


def _rendered_sub_div():
    """The COUNTRY COMPARISON .sub line, rendered through the template's own macros."""
    anchor = TEMPLATE.index("Strategic reserve = government-held")
    start = TEMPLATE.rindex('<div class="sub"', 0, anchor)
    src = MACROS + TEMPLATE[start:TEMPLATE.index("</div>", start) + len("</div>")]
    return Environment(autoescape=True).from_string(src).render()


def _plain(html):
    """The tile with its markup stripped: what a reader actually sees."""
    return re.sub(r"<[^>]+>", "", html)


def _slot(html, lang):
    m = re.search(r'<span class="l-%s">(.*?)</span>' % lang, html, re.S)
    return m.group(1) if m else ""


def test_global_aggregate_vm_carries_the_reporters_as_of_month():
    raw = {"US": _monthly([120000.0, 121000.0, 122000.0], "2026-05-01"),
           "IN": _monthly([45000.0, 45200.0, 45300.0], "2026-01-01")}
    agg = _global_jodi_vm(raw)
    assert agg["as_of"] == "2026-07"
    assert agg["oldest"] == "2026-03"
    empty = _global_jodi_vm({})
    assert empty["as_of"] == ""
    assert empty["oldest"] == ""
    assert empty["n_excluded"] == 0
    assert empty["total_mb"] is None


def test_global_aggregate_vm_names_reporters_dropped_as_stale():
    raw = {"US": _monthly([120000.0], "2026-07-01"),
           "AE": _monthly([3900.0], "2018-12-01")}
    agg = _global_jodi_vm(raw)
    assert agg["excluded"] == ["AE"]
    assert agg["n_excluded"] == 1
    assert agg["oldest"] == "2026-07"          # stale AE must not drag the range
    assert agg["total_mb"] == 120.0            # AE's 3.9 MMbbl is not in the sum


def test_tile_renders_the_real_jodi_months_from_a_committed_shaped_record():
    tile = _render_global_tile(_committed_shaped_agg())
    assert "1,562" in tile
    plain = _plain(tile)
    assert "2026-03 → 2026-07" in plain
    assert "latest reports" in tile and "最新报送" in tile
    assert "excluded as stale" in tile and "已剔除停报" in tile
    assert re.search(r"latest reports.*2026-03 → 2026-07", plain)
    assert re.search(r"excluded as stale.*: AE, BR", plain)


def test_tile_prints_one_month_when_every_reporter_is_current():
    tile = _render_global_tile(_committed_shaped_agg(oldest="2026-07",
                                                     excluded=[], n_excluded=0))
    assert "2026-07" in tile
    assert "→" not in tile


def test_tile_omits_the_stale_line_when_nothing_was_excluded():
    tile = _render_global_tile(_committed_shaped_agg(excluded=[], n_excluded=0))
    assert "excluded as stale" not in tile
    assert "已剔除停报" not in tile


def test_tile_renders_no_bare_label_when_the_month_is_unknown():
    tile = _render_global_tile(_committed_shaped_agg(as_of="", oldest="",
                                                     excluded=[], n_excluded=0))
    assert "latest reports" not in tile
    assert "最新报送" not in tile
    assert "None" not in tile


def test_page_copy_no_longer_claims_a_one_to_two_month_jodi_lag():
    sub = _rendered_sub_div()
    assert "1-2" not in sub
    assert "1-2" not in sr.SPR_CAVEAT["en"]
    assert "1-2" not in sr.SPR_CAVEAT["zh"]
    assert "1-2" not in (sr.__doc__ or "")
    assert "2-3 month" in sr.SPR_CAVEAT["en"]
    assert "2-3个月" in sr.SPR_CAVEAT["zh"]
    collector = (REPO / "collectors/jodi.py").read_text(encoding="utf-8")
    assert "~2-3 month" in collector


def test_zh_jodi_copy_uses_disclosure_not_live():
    zh = _slot(_rendered_sub_div(), "zh")
    assert "实时" not in zh
    assert "申报" not in zh
    assert "披露" in zh
