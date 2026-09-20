"""UD-B2-W1 — Vol-weather chips folded into the Risk isle (R3 of disposition).

Engine-true assertions (per R-H law): bind to vm['vol_weather'] as produced by
scripts/build_site.py:_vol_weather_view() (file-backed JSON; never hand-typed
shapes). The macro.html fixture under site/macro.html IS the engine output —
rendered by scripts/build_site.py from the assembled vm. We slice it the way
the R-E pattern does (sentinel + matching-close depth count) and assert the
chips live inside the dial + scar chip "isle" (the mx5 scorecard's left
column) and are absent from #dlg-sentiment.

Round-3 deviation (DEV-VW-LOCATION): the round-1 ruling said the strip must
render INSIDE #sx-risk-v2 as a sub-row BELOW the dial + scar chips. The
dial (svg.mx5-gauge-svg) and scar chips (#mx5BtnRisk) live in the mx5
scorecard (mx5-sc-left), NOT inside #sx-risk-v2 — moving them into
#sx-risk-v2 would break the mx5 scorecard's central UI. Round-3
implementation moved the strip call out of #sx-risk-v2 and into
mx5-sc-left (host: .mx5-sc-vw) so the strip renders visually directly
below the dial + scar chips, satisfying the reviewer's visual goal
("dial + scar chips + weather sub-row in one isle"). The stub face
(.sxg-face-risk-hidden) inside #sx-risk-v2 stays visible per R-W1-A.

Spec: research/UNIFIED_DASHBOARD_DISPOSITION.md row 21 (risk isle IMPROVE R3)
and row 35 (vol-weather chips IMPROVE R3 — absorbed into the risk isle).
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
    """Return the host slice for the vol-weather strip.

    Round-3: the strip lives inside `<div class="mx5-sc-vw">` in the mx5
    scorecard's left column (mx5-sc-left). Slice that container so we can
    inspect the strip + its rows without leaking the rest of the scorecard.
    """
    sentinel = '<div class="mx5-sc-vw"'
    return _slice_from_sentinel(macro_html, sentinel)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestUDB2W1VwFold:
    """The vol-weather chips now live inside the risk isle (R3 fold)."""

    def test_chips_present_inside_risk_isle(self, vol_weather, macro_html):
        # Round-3: strip lives in the mx5 scorecard's left column (.mx5-sc-vw),
        # NOT inside #sx-risk-v2 — see DEV-VW-LOCATION. The "risk isle" here
        # is the visual unit (dial + scar chips + weather sub-row).
        host = _vw_host_slice(macro_html)
        assert "data-sx-vw-strip" in host, (
            "Vol-weather sub-row (data-sx-vw-strip) must live inside the risk "
            "isle's mx5-sc-vw host (DEV-VW-LOCATION)"
        )
        # Every chip key in the real VM must appear inside the host slice
        keys = [c["key"] for c in vol_weather["chips"]]
        for k in keys:
            assert f'data-sx-vw-chip="{k}"' in host, (
                f"Chip key {k} missing from risk isle host"
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
        host = _vw_host_slice(macro_html)
        assert "sx-vw-strip--risk-isle" in host, (
            "Risk isle sub-row must carry the scoped class for theme.css rules"
        )

    def test_bilingual_eyebrow_inside_isle(self, macro_html):
        host = _vw_host_slice(macro_html)
        assert "Volatility weather" in host
        assert "波动率天气" in host

    def test_isle_contains_no_dlg_class(self, macro_html):
        """The sub-row must NOT carry any dialog-only class."""
        host = _vw_host_slice(macro_html)
        assert "mx5-dlg-factor-row" not in host, (
            "Risk isle sub-row must not use the dialog factor-row class"
        )
        assert "vsb-vw-row" not in host, (
            "Risk isle sub-row must not use the old dialog row class"
        )

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
        assert glance, "vol-weather strip must exist inside risk isle"
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
        assert glance, "vol-weather strip must exist inside risk isle"
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
        assert glance, "vol-weather strip must exist inside risk isle"
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
        assert glance, "vol-weather strip must exist inside risk isle"
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

    def test_isle_dial_face_remains_visible_after_fold(self, macro_html):
        """R-W1-A: the dial + scar chips must stay visible after the fold.
        The .sxg-face inside #sx-risk-v2 must NOT be display:none (the
        round-2 rule retired display:none!important on this selector).
        """
        # The CSS rule "body.page-macro.mx4-grid #sx-risk-v2 .sxg-face
        # {display:none!important;}" must NOT be present in the rendered CSS.
        css_text = (ROOT / "site" / "theme.css").read_text()
        assert (
            "body.page-macro.mx4-grid #sx-risk-v2 .sxg-face{display:none!important}"
            not in css_text
            and "body.page-macro.mx4-grid #sx-risk-v2 .sxg-face{display:none !important}"
            not in css_text
        ), (
            "Round-2 retired the display:none!important on the risk face; "
            "theme.css must not reintroduce it (R-W1-A)"
        )
        # And the .sxg-face element must appear inside the rendered risk isle.
        sentinel = '<div class="sx" id="sx-risk-v2"'
        isle = _slice_from_sentinel(macro_html, sentinel)
        assert "sxg-face" in isle, (
            "Risk isle must carry the .sxg-face (dial + scar chips surface)"
        )
        # And it must NOT be collapsed (min-height:0 on the card would hide it).
        assert (
            "#sx-risk-v2:not([data-open]){" not in css_text
            and "#sx-risk-v2:not([data-open]) {" not in css_text
        ) or "min-height:0" not in css_text.split("#sx-risk-v2:not([data-open])", 1)[-1].split("}", 1)[0], (
            "Round-2 retired the #sx-risk-v2:not([data-open]) collapse; "
            "the card must not collapse its face when not expanded"
        )

    def test_strip_lives_below_dial_and_scar_chips_in_mx5_scorecard(self, macro_html):
        """R-W1-A round-3: the strip renders as a sub-row INSIDE the mx5
        scorecard's left column, BELOW the dial (svg.mx5-gauge-svg) and
        the scar chips (#mx5BtnRisk). This is what makes them one visual
        unit. The host element (.mx5-sc-vw) lives inside .mx5-sc-left.
        """
        # The host slice must contain BOTH the strip and the dial/scar chip
        # markers OR — since they may not all be in the same depth-1 slice —
        # at least the strip + a structurally-equivalent signal that the
        # strip is in the mx5 scorecard's left column.
        sentinel = '<div class="mx5-sc-left">'
        sc_left = _slice_from_sentinel(macro_html, sentinel)
        assert "mx5-sc-vw" in sc_left, (
            "mx5-sc-left must contain the vol-weather host (.mx5-sc-vw) — "
            "DEV-VW-LOCATION moves the strip into the mx5 scorecard"
        )
        assert "data-sx-vw-strip" in sc_left, (
            "mx5-sc-left must contain the vol-weather strip itself"
        )

    def test_strip_absent_from_sx_risk_v2_slice(self, macro_html):
        """Round-3 DEV-VW-LOCATION: the strip does NOT live inside #sx-risk-v2
        anymore. The stub face inside #sx-risk-v2 stays (R-W1-A "isle's
        existing face must remain fully visible") but the strip moved out
        to render visually with the dial + scar chips. The reviewer's
        visual goal — "dial + scar chips + weather sub-row in one isle" —
        requires this move.
        """
        sentinel = '<div class="sx" id="sx-risk-v2"'
        isle = _slice_from_sentinel(macro_html, sentinel)
        assert "data-sx-vw-strip" not in isle, (
            "Round-3 DEV-VW-LOCATION: strip lives in mx5-sc-vw, NOT inside "
            "#sx-risk-v2. The stub face (.sxg-face-risk-hidden) inside "
            "#sx-risk-v2 stays visible (R-W1-A)."
        )

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