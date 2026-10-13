"""Macro volatility diagnostics — one engine-true detail surface.

The display binds to vm['vol_weather'] from scripts/build_site.py:
_vol_weather_view() exactly as before. The 2026-09-23 Macro UX follow-up
reverses only the #7539 Round-3 placement deviation: detailed volatility,
curve, correlation and dispersion rows belong inside #dlg-risk, not under the
primary scorecard dial.

The contract is presentation-only: one instance on the page, no duplicate in
#dlg-sentiment, no engine recompute, class-driven severity, honest young-data
states, bilingual plain words, and a compact Risk Detail host.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

MACRO_HTML = ROOT / "site" / "macro.html"
VOL_WEATHER_JSON = ROOT / "site" / "basketdata" / "vol_weather.json"

# Phrases banned from the glance tier (R-W1-B). Internal metric names belong in
# the isle's dialog / disclosure tier — never on the glance row.
BANNED_GLANCE_PHRASES_EN = (
    "Vol-of-vol balance",
    "Term structure",
    "vol demand",
    "Single-stock vol",
)
BANNED_GLANCE_PHRASES_ZH = (
    "期限结构",
    "波动率的波动",
    "盘中波动需求",
    "个股波动率",
)


# ---------------------------------------------------------------------------
# Fixtures (engine-true: bind to the real vm the build produced)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def vol_weather() -> dict:
    """Pull vm['vol_weather'] via scripts.build_site._vol_weather_view().

    File-backed (site/basketdata/vol_weather.json, written by build_theme_addons
    and read by _vol_weather_view). Never hand-typed shapes — the assertion
    surface is bound to whatever shape the engine emits.
    """
    # Engine-true call: invoke the real helper the build uses.
    try:
        from scripts.build_site import _vol_weather_view

        live_view = _vol_weather_view()
        if live_view:
            return live_view
    except Exception:  # noqa: BLE001
        pass
    if VOL_WEATHER_JSON.exists():
        return json.loads(VOL_WEATHER_JSON.read_text())
    pytest.skip(f"vol_weather.json not found at {VOL_WEATHER_JSON}")


@pytest.fixture(scope="module")
def macro_html() -> str:
    if not MACRO_HTML.exists():
        pytest.skip(f"site/macro.html not found at {MACRO_HTML}")
    return MACRO_HTML.read_text()


def _shipping_projection(html: str) -> str:
    """Return the committed document plus any local linked stylesheets.

    The render pipeline externalizes large ``<style>`` blocks into content-
    hashed assets. Regression checks must follow the bytes the browser loads,
    rather than assume every CSS rule remains inline in ``macro.html``.
    """
    linked_css = []
    for href in re.findall(r'<link[^>]+href="([^"]+\.css(?:\?[^"#]*)?)"', html):
        rel = href.split("?", 1)[0]
        if rel.startswith(("/", "http://", "https://")):
            continue
        css_path = MACRO_HTML.parent / rel
        if css_path.is_file():
            linked_css.append(css_path.read_text(encoding="utf-8"))
    return html + "\n" + "\n".join(linked_css)


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


def _slice_vol_weather_strip(host_html: str) -> str:
    """Walk from `data-sx-vw-strip` back to the strip's opening `<div`, then
    forward to its matching close. Returns the substring of the whole strip.

    `data-sx-vw-strip` is a *mid-attribute* on the strip's opening div — not
    the div itself. Walk BACKWARDS to find the strip's `<div`, then walk
    FORWARDS counting div opens/closes from depth=1 (the strip itself).
    """
    attr_pos = host_html.find("data-sx-vw-strip")
    if attr_pos < 0:
        return ""
    # Walk backwards to the strip's opening <div
    div_start = host_html.rfind("<div", 0, attr_pos)
    if div_start < 0:
        return ""
    depth = 1  # we are inside the strip's opening div
    i = div_start + 4
    n = len(host_html)
    # Skip past the strip's opening tag — find its `>` so we don't recount
    # the strip's own opener. Walk until we exit the opener tag.
    while i < n and host_html[i] != ">":
        i += 1
    i += 1  # step past the `>`
    while i < n:
        if host_html.startswith("<div", i) and (
            host_html.startswith("<div ", i) or host_html.startswith("<div>", i)
        ):
            depth += 1
            i += 5
        elif host_html.startswith("</div>", i):
            depth -= 1
            i += 6
            if depth == 0:
                return host_html[div_start:i]
        else:
            i += 1
    raise AssertionError("close not found for vol-weather strip")


def _vw_host_slice(macro_html: str) -> str:
    """Return the dedicated Risk Detail host for volatility diagnostics.

    The helper deliberately keys off the new section sentinel. Historical
    RED-first tests still call this helper against pre-move HTML and therefore
    continue to prove the placement capability was absent there.
    """
    sentinel = '<section class="riskdlg-vw"'
    start = macro_html.index(sentinel)
    end = macro_html.index("</section>", start) + len("</section>")
    return macro_html[start:end]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestUDB2W1VwFold:
    """The vol-weather chips now live inside Risk Detail (R3 fold)."""

    def test_chips_present_inside_risk_detail(self, vol_weather, macro_html):
        host = _vw_host_slice(macro_html)
        assert 'data-sx-vw-host="risk-detail"' in host
        assert "data-sx-vw-strip" in host
        keys = [c["key"] for c in vol_weather["chips"]]
        for key in keys:
            assert f'data-sx-vw-chip="{key}"' in host, (
                f"Chip key {key} missing from Risk Detail"
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

    def test_risk_detail_carries_scope_class_for_styling(self, macro_html):
        host = _vw_host_slice(macro_html)
        assert "sx-vw-strip--risk-detail" in host
        assert "sx-vw-strip--risk-isle" not in host

    def test_bilingual_section_heading_inside_risk_detail(self, macro_html):
        host = _vw_host_slice(macro_html)
        assert "Volatility &amp; correlation" in host
        assert "波动率与相关性" in host

    def test_detail_rows_do_not_resurrect_legacy_dialog_classes(self, macro_html):
        host = _vw_host_slice(macro_html)
        assert "mx5-dlg-factor-row" not in host
        assert "vsb-vw-row" not in host
        assert 'id="vsb-vol-weather-section"' not in host

    def test_plain_word_names_inside_isle(self, macro_html):
        """R-W1-B: glance tier carries only tier words + plain clauses.
        Internal metric names (Term structure / Vol-of-vol balance /
        vol demand / Single-stock vol / 期限结构 / 波动率的波动 /
        盘中波动需求 / 个股波动率) demote to the isle's disclosure tier.
        """
        host = _vw_host_slice(macro_html)
        # Slice to ONLY the vol-weather strip so disclosure-tier rows outside
        # the strip cannot false-fail us.
        glance = _slice_vol_weather_strip(host)
        assert glance, "vol-weather strip must exist inside Risk Detail"
        for phrase in BANNED_GLANCE_PHRASES_EN + BANNED_GLANCE_PHRASES_ZH:
            assert phrase not in glance, (
                f"Banned internal metric name {phrase!r} must not appear on glance tier "
                f"(demote to disclosure tier per R-W1-B)"
            )

    def test_no_raw_values_or_pctile_scoreboard(self, vol_weather, macro_html):
        """One-integer law (UD-B1 R-L): the glance tier must not show raw chip
        values (15.3, -0.5, 0.722, …) or "higher than N% of days" pctile
        scoreboard phrases. The hero already owns the now-N/100 read; the
        vol-weather glance row carries the tier word only.
        """
        host = _vw_host_slice(macro_html)
        glance = _slice_vol_weather_strip(host)
        assert glance, "vol-weather strip must exist inside Risk Detail"
        # pctile phrases must not appear on glance
        assert "higher than" not in glance, (
            "Glance tier must not carry 'higher than N% of days' pctile phrase (one-integer law)"
        )
        assert "lower than" not in glance, (
            "Glance tier must not carry 'lower than N% of days' pctile phrase (one-integer law)"
        )
        assert "% of days" not in glance, (
            "Glance tier must not carry the '% of days' pctile scoreboard"
        )
        # Raw chip values must not appear on glance.
        for chip in vol_weather.get("chips", []):
            v = chip.get("value")
            if v is None:
                continue
            for fmt in (
                f">{v}<",
                f">{abs(v)}<",
                f">{v:.1f}<",
                f">{abs(v):.1f}<",
            ):
                if fmt in glance:
                    raise AssertionError(
                        f"Raw chip value {v!r} leaked into glance tier; one-integer law broken"
                    )

    def test_no_inline_color_style_on_rows(self, macro_html):
        """R-W1-F: tier colour keys off class-based path only — no inline
        style="...--sg-wx-c..." on rows, no inline style="color:..." on rows.
        theme.css is the only material-decision surface for vol-weather rows.
        """
        host = _vw_host_slice(macro_html)
        glance = _slice_vol_weather_strip(host)
        assert glance, "vol-weather strip must exist inside Risk Detail"
        # No --sg-wx-c keying on rows
        assert "--sg-wx-c" not in glance, (
            "Inline --sg-wx-c keying on vol-weather rows is forbidden (R-W1-F)"
        )
        # No inline style="color:..." or style="background-color:..." on rows
        row_blocks = re.findall(
            r'<div\s+class="sx-vw-row[^"]*"[^>]*>', glance,
        )
        for rb in row_blocks:
            assert "style=" not in rb, (
                f"Vol-weather row must not carry inline style attributes "
                f"(theme.css is the only style surface): {rb!r}"
            )

    def test_data_tier_attr_drives_colour(self, macro_html):
        """R-W1-F: every non-young chip row carries a `data-tier` attribute
        whose value matches the row's class (.sx-vw-row--{tier}). The class
        is the colour key in theme.css; data-tier is the template-emitted
        contract that documents which class applies to which row.
        """
        host = _vw_host_slice(macro_html)
        glance = _slice_vol_weather_strip(host)
        assert glance, "vol-weather strip must exist inside Risk Detail"
        row_re = re.compile(
            r'<div\s+class="sx-vw-row\s+(?P<cls>sx-vw-row--\w+)"\s+'
            r'data-sx-vw-chip="(?P<chip>\w+)"\s+'
            r'data-tier="(?P<tier>\w+)"',
        )
        rows = row_re.findall(glance)
        assert rows, "vol-weather strip should contain at least one row"
        for cls, chip, tier in rows:
            expected_class = f"sx-vw-row--{tier}"
            assert cls == expected_class, (
                f"Row chip={chip!r} has class {cls!r} but data-tier={tier!r} "
                f"(expected class={expected_class!r} — the class IS the colour key)"
            )

    def test_primary_scorecard_keeps_dial_and_risk_entry_without_weather_stack(self, macro_html):
        sc_left = _slice_from_sentinel(macro_html, '<div class="mx5-sc-left">')
        assert "mx5-gauge-svg" in sc_left or "mx5-gauge" in sc_left
        assert "mx5BtnRisk" in sc_left
        assert "data-sx-vw-strip" not in sc_left
        assert "mx5-sc-vw" not in sc_left
        projection = _shipping_projection(macro_html)
        assert (
            "body.page-macro.mx4-grid #sx-risk-v2 .sxg-face{display:none!important;}"
            in projection
            or "body.page-macro.mx4-grid #sx-risk-v2 .sxg-face{display:none!important}"
            in projection
            or "body.page-macro.mx4-grid #sx-risk-v2 .sxg-face{display:none !important}"
            in projection
        )

    def test_strip_lives_in_risk_detail_before_sentiment(self, macro_html):
        host = _vw_host_slice(macro_html)
        assert "data-sx-vw-strip" in host
        dlg_start = macro_html.index('<div class="mx5-dlg" id="dlg-risk"')
        vw_pos = macro_html.index('<section class="riskdlg-vw"', dlg_start)
        sentiment_pos = macro_html.index('<div class="riskdlg-sentiment"', dlg_start)
        assert dlg_start < vw_pos < sentiment_pos, (
            "Volatility diagnostics must sit in Risk Detail before Sentiment"
        )

    def test_strip_present_once_inside_risk_detail(self, macro_html):
        host = _vw_host_slice(macro_html)
        assert host.count("data-sx-vw-strip") == 1
        assert macro_html.count("data-sx-vw-strip") == 1
        assert macro_html.count('data-sx-vw-host="risk-detail"') == 1

    def test_no_volatility_rows_outside_risk_detail(self, macro_html):
        host = _vw_host_slice(macro_html)
        remainder = macro_html.replace(host, "", 1)
        assert "data-sx-vw-strip" not in remainder
        assert "data-sx-vw-chip=" not in remainder
        assert 'class="mx5-sc-vw"' not in macro_html
        assert 'data-sx-vw-host="mx5-sc-left"' not in macro_html

    def test_risk_detail_layout_is_compact_desktop_and_stacked_mobile(self, macro_html):
        projection = _shipping_projection(macro_html)
        assert "body.page-macro .riskdlg-vw .sx-vw-strip{" in projection
        assert "grid-template-columns:repeat(2,minmax(0,1fr));" in projection
        assert "@media(max-width:640px)" in projection
        mobile = projection[projection.index("@media(max-width:640px)"):]
        assert "body.page-macro .riskdlg-vw .sx-vw-strip" in mobile
        assert "grid-template-columns:minmax(0,1fr);" in mobile


    def test_glance_cor1m_and_cor3m_labels_are_distinct(self, macro_html):
        """Glance rows 6/7 (cor1m / cor3m) must not share one label.
        Labels come from the engine's own names, not invented copy.
        """
        host = _vw_host_slice(macro_html)
        glance = _slice_vol_weather_strip(host)
        def _name_for(key: str) -> str:
            m = re.search(
                rf'data-sx-vw-chip="{re.escape(key)}".*?'
                rf'<div class="sx-vw-name">\s*'
                rf'<span class="l-en">(?P<en>[^<]*)</span>'
                rf'<span class="l-zh">(?P<zh>[^<]*)</span>',
                glance,
                re.DOTALL,
            )
            assert m, f"glance row for {key} not found"
            return f"{m.group('en')}|{m.group('zh')}"
        cor1m = _name_for("cor1m")
        cor3m = _name_for("cor3m")
        assert cor1m != cor3m, (
            f"cor1m and cor3m glance labels must be distinct; both are {cor1m!r}"
        )
        # Engine's own labels (engine/vol_velocity.py _chip_cor1m/_chip_cor3m).
        assert "How much stocks move together" in cor1m
        assert "3-month implied correlation" in cor3m
        assert "3个月隐含相关性" in cor3m


    def test_ok_chip_with_extreme_band_shows_storm_tier(self, vol_weather, macro_html):
        """An extreme-band chip must render the 'storm' / '风暴' tier word
        on the right column of its row. Tier word comes from band
        classification (engine-side), not raw values.
        """
        host = _vw_host_slice(macro_html)
        # Find at least one extreme chip from the VM
        extreme_keys = [
            c["key"] for c in vol_weather.get("chips", []) if c.get("band") == "extreme"
        ]
        if not extreme_keys:
            pytest.skip("No extreme-band chip in current VM (engine output varies)")
        for k in extreme_keys:
            row_pat = re.compile(
                rf'<div\s+class="sx-vw-row\s+sx-vw-row--extreme"\s+'
                rf'data-sx-vw-chip="{re.escape(k)}"[^>]*>(?P<body>.*?)</div>\s*</div>\s*<svg\s+class="sg-pos-mark\s+sg-pos-mark--'
                rf'(?P<tier>.*?)</div>',
                re.DOTALL,
            )
            # Use the original tier body match: find the chip's own row, then
            # look at the .sx-vw-tier block inside it.
            row_pat = re.compile(
                rf'<div\s+class="sx-vw-row\s+sx-vw-row--extreme"\s+'
                rf'data-sx-vw-chip="{re.escape(k)}"(?P<body>.*?)<div\s+class="sx-vw-tier">(?P<tier>.*?)</div>\s*</div>',
                re.DOTALL,
            )
            m = row_pat.search(host)
            assert m, (
                f"Extreme-band row for chip={k!r} not found in mx5-sc-vw host"
            )
            tier_body = m.group("tier")
            assert "storm" in tier_body and "风暴" in tier_body, (
                f"Extreme-band row chip={k!r} must show 'storm' / '风暴' tier word; "
                f"got tier body: {tier_body!r}"
            )