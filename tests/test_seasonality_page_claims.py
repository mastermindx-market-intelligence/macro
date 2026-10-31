"""Factor seasonality page claims: F3 outline month, F4 row starts, F5 footer.

F3: the mosaic's outlined month must come from the artifact (seas.now.month),
not the viewer's browser clock. F4: each mosaic row prints its own history
start, and the header must stop asserting one start for all six styles.
F5: the footer sentence must end clean and point at a real public
destination. Fixtures are inline and synthetic with INT month keys — the
committed JSON stores STRING month keys while the producer renders from ints,
so int keys are the render contract (F7).
"""
from __future__ import annotations

import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from engine.i18n import td, tr

TEMPLATES = Path(__file__).resolve().parents[1] / "templates"

# The six committed (key, label, start, context_only) tuples, in artifact order.
SIX = [
    ("value", "Value (HML)", "价值 (HML)", "1926-07", False),
    ("profitability", "Profitability (RMW)", "盈利 (RMW)", "1963-07", False),
    ("investment", "Investment (CMA)", "投资 (CMA)", "1963-07", False),
    ("momentum", "Momentum (Mom)", "动量 (Mom)", "1927-01", True),
    ("size", "Size (SMB)", "规模 (SMB)", "1926-07", True),
    ("market", "Market (Mkt-RF)", "市场 (Mkt-RF)", "1926-07", True),
]


def _seas(month=10, drop=()):
    cell = {"mean": 0.5, "median": 0.4, "hit": 60, "n": 10}
    factors = []
    for key, en, zh, start, ctx in SIX:
        f = {"key": key, "label_en": en, "label_zh": zh, "start": start,
             "context_only": ctx}
        for win in ("full", "trailing_30y", "trailing_10y"):
            f[win] = {m: dict(cell) for m in range(1, 13) if (key, m) not in drop}
        factors.append(f)
    seas = {"as_of": "2026-08", "source": "Ken French Data Library",
            "disclosure_en": "d", "disclosure_zh": "d", "factors": factors}
    if month is not None:
        seas["now"] = {"month": month, "month_label_en": "Xmonth",
                       "month_label_zh": "月", "headline_en": "h",
                       "headline_zh": "h", "stance_en": "s", "stance_zh": "s",
                       "chip_en": "", "chip_zh": ""}
    return seas


def _render(seas, built="2026-10-19"):
    env = Environment(loader=FileSystemLoader(str(TEMPLATES)), autoescape=True)
    env.globals.update(td=td, tr=tr, zip=zip)
    return env.get_template("seasonality.html.j2").render(seas=seas, built=built)


def _curm_months(html):
    out = []
    for m in re.finditer(r'<(\w+)\b([^>]*class="[^"]*\bcurm\b[^"]*"[^>]*)>', html):
        dm = re.search(r'data-m="(\d+)"', m.group(2))
        out.append((m.group(1), dm.group(1) if dm else None))
    return out


def test_outline_follows_the_artifact_month_not_the_viewer_clock():
    html = _render(_seas(month=10))
    assert html.count('<th class="mosh curm" data-m="10">') == 3
    assert len(re.findall(r'<td class="mos[^"]*\bcurm\b[^"]*" data-m="10"',
                          html)) == 18
    assert {dm for _, dm in _curm_months(html)} == {"10"}
    assert "getMonth" not in html
    assert "new Date" not in html


def test_outline_month_survives_a_stale_build():
    html = _render(_seas(month=3), built="2026-10-19 21:00 UTC")
    assert html.count('<th class="mosh curm" data-m="3">') == 3
    assert len(re.findall(r'<td class="mos[^"]*\bcurm\b[^"]*" data-m="3"',
                          html)) == 18
    assert {dm for _, dm in _curm_months(html)} == {"3"}


def test_no_outline_when_the_artifact_has_no_graded_month():
    for seas in (_seas(month=None), dict(_seas(month=None), now=None)):
        html = _render(seas)
        assert re.search(r'class="[^"]*\bcurm\b', html) is None


def test_each_row_prints_its_own_history_start():
    html = _render(_seas())
    rows = re.findall(r'<td class="mosf">(.*?)</td>', html, re.S)[:6]
    by_key = {}
    for r in rows:
        text = " ".join(re.sub(r"<[^>]+>", " ", r).split())
        for key, en, _zh, start, _ctx in SIX:
            if text.startswith(en):
                assert start in text, key
                by_key[key] = text
    assert len(by_key) == 6
    assert "1926-07" in by_key["value"]
    assert "1963-07" in by_key["profitability"]
    assert "1926-07" not in by_key["profitability"]
    assert "1963-07" in by_key["investment"]
    assert "1927-01" in by_key["momentum"]
    assert "1926-07" in by_key["size"]
    assert "1926-07" in by_key["market"]


def test_header_no_longer_claims_one_start_for_every_style():
    top = _render(_seas()).split('<div class="topline">')[1].split("</div>")[0]
    assert "STYLE" not in top
    assert "1926-07+" not in top
    assert "1926-07 起" not in top


def test_footer_points_at_a_real_public_destination():
    html = _render(_seas())
    i = html.find("font-size:12px;margin:0")
    assert i != -1
    footer = html[i:html.find("</p>", i)]
    assert 'href="methodology.html#seasonality"' in footer
    assert "score —." not in footer
    assert "仅仅作" not in footer
    assert "仅为描述" in footer


def test_empty_cells_take_the_outline_too():
    html = _render(_seas(month=10, drop={("value", 10)}))
    assert html.count('<td class="mos muted curm" data-m="10">') == 3
    assert html.count('data-m="10"') == 21  # 18 tds + 3 headers, all outlined
    assert {dm for _, dm in _curm_months(html)} == {"10"}


def test_mosaic_is_not_empty():
    html = _render(_seas())
    assert len(re.findall(r'<td class="mos[" ]', html)) == 216
    assert 'class="mm"' in html
