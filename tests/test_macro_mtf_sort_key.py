"""site20 S2 r5 (F2): macro Multi-Timeframe tape RSI cells carry a numeric sort key.

templates/tablesort.js sorts a column numerically only when every non-missing
cell parses as a number. Each MTF-tape cell renders an arrow glyph plus the RSI
("▲61"), which is text, so the timeframe <td> must carry data-sort="<rsi>", and
data-sort="" (a missing value, sorted last) when the cell or its RSI is absent.
Renders only the mx5-dlg-mtf-tbl block of templates/dashboard.html.j2 with a
synthetic MS2 fixture; no data/ reads.
"""
from __future__ import annotations

import pathlib

import jinja2
from bs4 import BeautifulSoup

ROOT = pathlib.Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "dashboard.html.j2"
OPEN = '<table class="mx5-dlg-mtf-tbl">'


def _render(indices):
    src = TEMPLATE.read_text(encoding="utf-8")
    assert src.count(OPEN) == 1, "expected exactly one MTF tape table in dashboard.html.j2"
    start = src.index(OPEN)
    end = src.index("</table>", start) + len("</table>")
    html = jinja2.Environment().from_string(src[start:end]).render(MS2={"mtf": {"indices": indices}})
    return BeautifulSoup(html, "html.parser")


def _row(label, cells):
    return {"label_en": label, "label_zh": label, "cells": cells,
            "tone": "flat", "confluence_en": "Mixed", "confluence_zh": "分歧"}


def test_mtf_rsi_cells_carry_numeric_data_sort():
    soup = _render([
        _row("S&P 500", {
            "D": {"tone": "up", "arrow": "▲", "rsi": 61.4},
            "3D": {"tone": "dn", "arrow": "▼", "rsi": 7.6},
            "W": {"tone": "flat", "arrow": "▲", "rsi": None},
            # "M" absent: the template renders the flat placeholder cell
        }),
    ])
    tds = soup.select("tbody tr")[0].find_all("td", recursive=False)
    assert len(tds) == 6
    assert [td.get("data-sort") for td in tds[1:5]] == ["61", "8", "", ""]
    # visible text is unchanged: arrow glyph + rounded RSI, or the placeholder
    assert [td.get_text() for td in tds[1:5]] == ["▲61", "▼8", "▲·", "·"]
    # the label and confluence columns stay text (no key)
    assert tds[0].get("data-sort") is None
    assert tds[5].get("data-sort") is None
