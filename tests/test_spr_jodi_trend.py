"""The JODI cell on templates/spr.html.j2 must show the 12-month read beside the month move.

The engine already ships jodi_yoy_pct + jodi_trend on every country row
(engine/strategic_reserves.py:186-187, trend_word() at :122 returns the "—" sentinel on
short history); these tests pin the wire: the cell renders a second, independently
coloured "12m +/-x.x% . word" line under the untouched MoM line, the zh slot carries
the Chinese trend word, and a row without a 12-month read (None or "—") renders no
pair and never raises. Rendered from inline fixtures shaped like the committed record;
no site/ or data/ read, no network.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from jinja2 import Environment

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine import strategic_reserves as sr     # noqa: E402

REPO = Path(__file__).resolve().parent.parent
TEMPLATE = (REPO / "templates/spr.html.j2").read_text(encoding="utf-8")
MACROS = "".join(TEMPLATE.splitlines(True)[:8])

BASE = {"iso": "IN", "name": "India", "name_zh": "印度", "flag": "",
        "jodi_total_mb": None, "jodi_as_of": None, "jodi_mom_mb": None,
        "jodi_assess": None, "jodi_yoy_pct": None, "jodi_trend": None,
        "net_imports_kbd": None, "stock_cover_days": None}


def _cell_source():
    """The JODI cell, sliced from the template as it is committed (SPEC 2 target)."""
    start = TEMPLATE.index("{% if c.jodi_total_mb is not none %}")
    end = TEMPLATE.index("{% elif c.curated_total_mb %}")
    return TEMPLATE[start:end] + "{% endif %}"


def _render(row, stub=True):
    src = _cell_source()
    ctx = {"c": row, "assess_word": sr.ASSESS_WORD, "assess_word_zh": sr.ASSESS_WORD_ZH}
    if stub:
        ctx["t"] = lambda en, zh="": "%s|%s" % (en, zh)
    else:
        src = MACROS + src
    out = Environment(autoescape=True).from_string(src).render(**ctx)
    return re.sub(r"[ \t]+", " ", out)


def _row(**kw):
    return {**BASE, **kw}


def _div_class(out, needle):
    for m in re.finditer(r'<div class="(sm[^"]*)">(.*?)</div>', out, re.S):
        if needle in m.group(2):
            return m.group(1)
    return None


def test_row_renders_the_twelve_month_pair_from_a_committed_shaped_record():
    out = _render(_row(jodi_total_mb=45.3, jodi_as_of="2026-03",
                       jodi_mom_mb=-17.1, jodi_yoy_pct=4.4,
                       jodi_trend="rising"))
    assert "12m|近12个月 +4.4%" in out
    assert "rising" in out
    assert _div_class(out, "+4.4%") == "sm up"
    assert "-17.1M/mo" in out           # the month line stays; 12m is additive


def test_japan_row_shows_a_falling_twelve_month_read_beside_a_positive_month():
    out = _render(_row(jodi_total_mb=268.3, jodi_as_of="2026-07",
                       jodi_mom_mb=1.6, jodi_yoy_pct=-21.7,
                       jodi_trend="falling"))
    assert _div_class(out, "-21.7%") == "sm down"
    assert _div_class(out, "+1.6M/mo") == "sm up"


def test_zh_slot_carries_the_trend_word():
    out = None
    for trend, zh in (("rising", "上升"), ("falling", "下降"), ("flat", "持平")):
        out = _render(_row(jodi_total_mb=100.0, jodi_as_of="2026-07",
                           jodi_mom_mb=1.0, jodi_yoy_pct=2.0,
                           jodi_trend=trend))
        assert "%s|%s" % (trend, zh) in out
    assert "12m|近12个月" in out


def test_rows_without_a_twelve_month_read_render_no_trend_pair():
    out = _render(_row())                      # China-shaped: no JODI at all
    assert "12m" not in out
    assert "%" not in out
    short = _render(_row(jodi_total_mb=50.0, jodi_as_of="2026-07",
                         jodi_mom_mb=1.0, jodi_yoy_pct=None,
                         jodi_trend="—"))      # short history: yoy is None (m1)
    assert "+1.0M/mo" in short
    assert "12m" not in short
    assert "%" not in short


def test_short_history_sentinel_renders_no_chip():
    out = _render(_row(jodi_total_mb=50.0, jodi_as_of="2026-07",
                       jodi_mom_mb=1.0, jodi_yoy_pct=2.0,
                       jodi_trend="—"))
    assert "+2.0%" in out
    assert "—" not in out
    assert "None" not in out
    after = out.split("+2.0%")[1].split("</div>")[0]
    assert " · " not in after
