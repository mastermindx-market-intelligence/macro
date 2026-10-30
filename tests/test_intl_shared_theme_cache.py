"""International published pages must fetch the asset that actually ships.

A merge can change site/theme.js while retaining an old versioned script URL.
The edge treats those URLs as immutable; template/site sync alone cannot catch it.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path


SITE = Path(__file__).resolve().parents[1] / "site"
PAGES = ("intl.html", "intl_stock.html", "intl_stocks.html", "baskets_intl.html", "research_screener.html")
STAMP = re.compile(r"theme[.]js[?]v=([0-9a-f]{8})")


def test_international_published_theme_cache_matches_emitted_asset() -> None:
    asset = SITE / "theme.js"
    expected = hashlib.sha256(asset.read_bytes()).hexdigest()[:8]
    pages = [SITE / name for name in PAGES] + sorted((SITE / "basket_intl").glob("*.html"))
    assert len(pages) >= len(PAGES) + 17
    for page in pages:
        stamps = STAMP.findall(page.read_text(encoding="utf-8"))
        assert stamps == [expected], f"{page.relative_to(SITE)}: expected {expected}, got {stamps}"
