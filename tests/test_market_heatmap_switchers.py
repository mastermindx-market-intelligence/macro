"""Sector/theme heatmap renderer and China toggle wiring guards.

The US owner page already carries the S&P 500 / Finviz Themes switch; this wave
does not rebuild that accepted renderer. China reuses the same multi-map renderer
while projecting the existing THS rotation + stock-map owner feeds in the browser.
Navigation exposure is sequenced behind the incumbent nav release carrier so this
PR does not create a concurrent writer for the immutable nav asset chain.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _maps(page: str) -> list[dict]:
    text = (ROOT / "site" / page).read_text(encoding="utf-8")
    match = re.search(r"data-hm-maps='([^']+)'", text)
    assert match, f"{page}: data-hm-maps missing"
    return json.loads(html.unescape(match.group(1)))


def test_us_heatmap_owner_keeps_sector_theme_switch_without_rebuild():
    maps = _maps("sector_heatmap.html")
    assert [m["key"] for m in maps] == ["sp500", "themes"]
    assert [m["url"] for m in maps] == [
        "marketdata/sp500_heatmap.json",
        "marketdata/themes_heatmap.json",
    ]
    template = (ROOT / "templates" / "sector_heatmap.html.j2").read_text(encoding="utf-8")
    assert '"key":"sp500"' in template
    assert '"key":"themes"' in template


def test_china_heatmap_switches_between_stock_sectors_and_ths_themes():
    maps = _maps("china_heatmap.html")
    assert [m["key"] for m in maps] == ["china-sectors", "china-themes"]

    sectors, themes = maps
    assert sectors["url"] == "marketdata/china_heatmap.json"
    assert themes == {
        "key": "china-themes",
        "label_en": "Themes",
        "label_zh": "主题",
        "url": "marketdata/subsector_rotation_china.json",
        "adapter": "china-ths-themes",
        "join_url": "marketdata/china_heatmap.json",
    }


def test_china_theme_view_reuses_owner_feeds_without_a_second_publisher():
    template_js = (ROOT / "templates" / "heatmap.js").read_text(encoding="utf-8")
    site_js = (ROOT / "site" / "heatmap.js").read_text(encoding="utf-8")
    assert template_js == site_js
    assert "function adaptChinaThsThemes(rotation, stocks)" in template_js
    assert "loadMapPayload(m)" in template_js
    assert "m.adapter !== 'china-ths-themes'" in template_js
    assert "subsector_rotation_china.json" in (ROOT / "templates" / "market_heatmap.html.j2").read_text(encoding="utf-8")

    # Architectural fence: the feature is a projection of existing public owner
    # artifacts. Do not mint a parallel THS heatmap JSON/source-of-truth plane.
    assert "china_themes_heatmap.json" not in template_js
    assert "china_themes_heatmap.json" not in (ROOT / "templates" / "market_heatmap.html.j2").read_text(encoding="utf-8")

