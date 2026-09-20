"""UD-B2-W1 — Vol-weather chips folded into the Risk isle (R3 of disposition).

Engine-true assertions (per R-H law): bind to vm['vol_weather'] as produced by
scripts/build_site.py:_vol_weather_view() (file-backed JSON; never hand-typed
shapes). The macro.html fixture under site/macro.html IS the engine output —
rendered by scripts/build_site.py from the assembled vm. We slice it the way
the R-E pattern does (sentinel + matching-close depth count) and assert the
chips live inside #sx-risk-v2 and are absent from #dlg-sentiment.

Spec: research/UNIFIED_DASHBOARD_DISPOSITION.md row 21 (risk isle IMPROVE R3)
and row 35 (vol-weather chips IMPROVE R3 — absorbed into the risk isle).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

MACRO_HTML = ROOT / "site" / "macro.html"
VOL_WEATHER_JSON = ROOT / "site" / "basketdata" / "vol_weather.json"


# ---------------------------------------------------------------------------
# Fixtures (engine-true: bind to the real vm the build produced)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def vol_weather() -> dict:
    """Pull vm['vol_weather'] as scripts/build_site.py:_vol_weather_view does.

    File-backed (site/basketdata/vol_weather.json, written by build_theme_addons
    and read by _vol_weather_view). Never hand-typed shapes — the assertion
    surface is bound to whatever shape the engine emits.
    """
    if VOL_WEATHER_JSON.exists():
        return json.loads(VOL_WEATHER_JSON.read_text())
    pytest.skip(f"vol_weather.json not found at {VOL_WEATHER_JSON}")


@pytest.fixture(scope="module")
def macro_html() -> str:
    if not MACRO_HTML.exists():
        pytest.skip(f"site/macro.html not found at {MACRO_HTML}")
    return MACRO_HTML.read_text()


# ---------------------------------------------------------------------------
# Slice extraction helpers
# ---------------------------------------------------------------------------


def _slice_from_sentinel(html: str, sentinel: str) -> str:
    """Return the substring starting at the sentinel and ending at the matching
    closing </div> at depth 0 (i.e. the div opened by the sentinel).

    Uses a simple state machine on '<div ' / '<div>' / '</div>'. The risk isle
    and the dialogs are flat enough that no nested .sx lives inside either, so
    this depth-1 close is exact.
    """
    start = html.index(sentinel)
    depth = 0
    i = start
    n = len(html)
    while i < n:
        if html.startswith("<div ", i) or html.startswith("<div>", i):
            depth += 1
            i += 5
        elif html.startswith("</div>", i):
            depth -= 1
            i += 6
            if depth == 0:
                return html[start:i]
        else:
            i += 1
    raise AssertionError(f"close not found for sentinel {sentinel!r}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestUDB2W1VwFold:
    """The vol-weather chips now live inside the risk isle (R3 fold)."""

    def test_chips_present_inside_risk_isle(self, vol_weather, macro_html):
        sentinel = '<div class="sx" id="sx-risk-v2"'
        isle = _slice_from_sentinel(macro_html, sentinel)
        assert "data-sx-vw-strip" in isle, (
            "Risk isle slice must contain the vol-weather sub-row (data-sx-vw-strip)"
        )
        # Every chip key in the real VM must appear inside the isle slice
        keys = [c["key"] for c in vol_weather["chips"]]
        for k in keys:
            assert f'data-sx-vw-chip="{k}"' in isle, (
                f"Chip key {k} missing from risk isle slice"
            )

    def test_chips_absent_from_dlg_sentiment(self, macro_html):
        sentinel = '<div class="mx5-dlg" id="dlg-sentiment"'
        dlg = _slice_from_sentinel(macro_html, sentinel)
        # Old sibling-section sentinel must not appear inside the dialog
        assert 'id="vsb-vol-weather-section"' not in dlg, (
            "dlg-sentiment must no longer carry the vol-weather section"
        )
        # And the new scoped class must not appear inside the dialog either
        assert "data-sx-vw-strip" not in dlg, (
            "dlg-sentiment must not contain the new scoped vol-weather strip"
        )
        assert "data-sx-vw-chip=" not in dlg, (
            "dlg-sentiment must not contain any data-sx-vw-chip rows"
        )

    def test_chips_appear_exactly_once_on_page(self, vol_weather, macro_html):
        """Per spec: chips appear EXACTLY ONCE on the page after the fold."""
        # Count via the unique data-sx-vw-chip= attribute the new template emits
        n = macro_html.count("data-sx-vw-chip=")
        assert n == len(vol_weather["chips"]), (
            f"Expected exactly {len(vol_weather['chips'])} vol-weather chip rows "
            f"on the page (one per VM chip); got {n}"
        )
        # And the OLD dialog-row marker must be entirely gone from the page
        assert macro_html.count('data-vsb-chip="') == 0, (
            "Old dialog-row data-vsb-chip marker must not appear on the page"
        )

    def test_old_id_sibling_section_gone(self, macro_html):
        assert 'id="vsb-vol-weather-section"' not in macro_html, (
            "Old sibling-section id (vsb-vol-weather-section) must not appear on the page"
        )

    def test_isle_carries_scope_class_for_styling(self, macro_html):
        sentinel = '<div class="sx" id="sx-risk-v2"'
        isle = _slice_from_sentinel(macro_html, sentinel)
        assert "sx-vw-strip--risk-isle" in isle, (
            "Risk isle sub-row must carry the scoped class for theme.css rules"
        )

    def test_chip_plain_text_inside_isle(self, vol_weather, macro_html):
        sentinel = '<div class="sx" id="sx-risk-v2"'
        isle = _slice_from_sentinel(macro_html, sentinel)
        # Spot-check: at least one chip's plain_en text lands inside the isle
        # (not somewhere else on the page).
        first_plain = next(
            (c.get("plain_en") for c in vol_weather["chips"] if c.get("plain_en")),
            None,
        )
        if first_plain:
            assert first_plain in isle, (
                f"Chip plain text {first_plain!r} must be inside the risk isle"
            )
        # And at least one pctile history phrase is inside the isle
        assert "higher than" in isle or "lower than" in isle, (
            "Risk isle must carry at least one pctile history phrase"
        )

    def test_bilingual_eyebrow_inside_isle(self, macro_html):
        sentinel = '<div class="sx" id="sx-risk-v2"'
        isle = _slice_from_sentinel(macro_html, sentinel)
        assert "Volatility weather" in isle
        assert "波动率天气" in isle

    def test_isle_contains_no_dlg_class(self, macro_html):
        """The sub-row must NOT carry any dialog-only class."""
        sentinel = '<div class="sx" id="sx-risk-v2"'
        isle = _slice_from_sentinel(macro_html, sentinel)
        assert "mx5-dlg-factor-row" not in isle, (
            "Risk isle sub-row must not use the dialog factor-row class"
        )
        assert "vsb-vw-row" not in isle, (
            "Risk isle sub-row must not use the old dialog row class"
        )
