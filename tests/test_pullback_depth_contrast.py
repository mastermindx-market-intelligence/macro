"""WCAG 2.2 contrast audit — Risk Radar "pullback" section (.rrp), dark + light.

Every pair below is (ink, surface) exactly as the browser resolves them:

  ink      the ``color:`` declarations of ``templates/_risk_radar_pullback_depth.css.j2``
           (plus the shared chart ink the section embeds), with ``var(--x)`` resolved
           from site/theme.css: the dark ``:root`` block, the
           ``html[data-theme="light"]`` blocks (incl. the ``--ink-mix-*`` block that
           builds the text-grade ``--ink-*`` colors), and each token's own
           ``color-mix()`` definition. Tokens are PARSED from theme.css, never
           duplicated here, so a palette edit re-prices this audit automatically.

  surface  the background each selector paints on, walking the same rules:
           ``.rrp`` (--panel), ``.rrp-heading`` (panel2→panel gradient; the light
           theme overrides it to flat --panel), ``.rrp-study > div`` (--panel).
           Those surfaces sit on the DIALOG panel — the US ``#dlg-risk``
           ``.mx5-dlg-panel`` (templates/dashboard.html.j2) or the country
           ``.cnx-dlg-panel`` (templates/china.html.j2). Both are translucent, so
           the test composites them over the page canvas (--bg) first. Every .rrp
           surface is opaque, so the dialog layer provably never changes a ratio
           (asserted) — it stays in the chain so the audit matches the real stack.

  chart    lib/pullback_depth.py ``present()`` renders ``detail_chart_html`` via
           ``illus(kind="drawdown", accent="var(--down)", reference=0)``. Ink and
           opacities come from templates/illus.css (.ilx-path/.ilx-water-top/
           .ilx-ref/.ilx-dot-down) plus the .rrp-chart opacity pins in the pullback
           stylesheet. The chart paints on ``.rrp-study > div`` (--panel).

Thresholds (WCAG 2.2 §1.4.3/§1.4.11): >=4.5:1 body text, >=3:1 large text
(>=24px, or >=18.66px at weight >=700) and non-text indicators (chart stroke,
settle dot, focus outline). Alpha inks are composited over their surface first.

Pairs failing at HEAD are NOT hidden: they are marked ``xfail(strict=True)``
with the measured ratio (PRODUCT findings — see the lane return's NOTES).
Gradient surfaces are priced at their WORST endpoint.
"""
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]

# ---------------------------------------------------------------------------
# Sources, quoted so the drift canaries below can pin them.
# ---------------------------------------------------------------------------
PULLBACK_CSS = REPO / "templates" / "_risk_radar_pullback_depth.css.j2"
ILLUS_CSS = REPO / "templates" / "illus.css"
DASHBOARD = REPO / "templates" / "dashboard.html.j2"
CHINA = REPO / "templates" / "china.html.j2"
PULLBACK_PY = REPO / "lib" / "pullback_depth.py"

# ---------------------------------------------------------------------------
# WCAG 2.2 math — relative luminance, contrast, sRGB alpha compositing.
# ---------------------------------------------------------------------------

def _srgb_to_linear(c: float) -> float:
    # WCAG 2.2 uses the IEC sRGB break at 0.04045 (the 2.1 draft said 0.03928).
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def rel_luminance(rgb) -> float:
    r, g, b = rgb[:3]
    return (0.2126 * _srgb_to_linear(r)
            + 0.7152 * _srgb_to_linear(g)
            + 0.0722 * _srgb_to_linear(b))


def contrast_ratio(a, b) -> float:
    la, lb = rel_luminance(a), rel_luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def parse_hex(literal: str):
    """``#rrggbb`` -> (r, g, b) floats in 0..1."""
    h = literal.strip()
    assert re.fullmatch(r"#[0-9a-fA-F]{6}", h), f"not a hex colour: {h!r}"
    return tuple(int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))


def parse_rgba(literal: str):
    """``rgba(13,17,24,.88)`` -> (r, g, b, a) floats in 0..1."""
    nums = [float(n) for n in re.findall(r"\d*\.?\d+", literal)]
    assert len(nums) in (3, 4), f"not an rgb/rgba colour: {literal!r}"
    rgb = tuple(n / 255 for n in nums[:3])
    return rgb + (nums[3] if len(nums) == 4 else 1.0,)


def color_mix_srgb(pct: float, a, b):
    """CSS ``color-mix(in srgb, A pct, B)``.

    Per css-color-5 the blend is premultiplied by alpha, so
    ``color-mix(in srgb, var(--panel) 78%, transparent)`` keeps A's rgb and
    takes alpha pct/100 (it does NOT bleed transparent-black into the rgb).
    """
    t = pct / 100.0
    aa, ba = a[3], b[3]
    out_a = t * aa + (1 - t) * ba
    if out_a <= 0:
        return (0.0, 0.0, 0.0, 0.0)
    rgb = tuple((t * a[i] * aa + (1 - t) * b[i] * ba) / out_a for i in range(3))
    return rgb + (out_a,)


def over(fg, bg):
    """Porter-Duff source-over of fg onto a surface."""
    a = fg[3]
    return tuple(fg[i] * a + bg[i] * (1 - a) for i in range(3))


def solid(rgb):
    return (rgb[0], rgb[1], rgb[2], 1.0)


def hex_str(rgb) -> str:
    return "#" + "".join(f"{round(v * 255):02x}" for v in rgb[:3])


# ---------------------------------------------------------------------------
# theme.css token resolution (parsed from site/theme.css, never duplicated).
# ---------------------------------------------------------------------------

def theme_css_text() -> str:
    path = REPO / "site" / "theme.css"
    if path.exists():
        return path.read_text(encoding="utf-8")
    # Sparse worktrees omit site/; the tokens still exist in the object store.
    out = subprocess.run(["git", "show", "HEAD:site/theme.css"], cwd=REPO,
                         capture_output=True, text=True, check=True)
    return out.stdout


_LIGHT_MARKER = 'html[data-theme="light"] {'


def _strip_comments(text: str) -> str:
    """Drop /* … */ blocks so prose that quotes a token (theme.css comments do)
    can never win a first-match against the real declaration."""
    return re.sub(r"/\*.*?\*/", "", text, flags=re.S)


def _light_block_bodies(text: str):
    """Bodies of every plain ``html[data-theme="light"] { … }`` token block.

    The exact `` {`` suffix deliberately skips the compound selector
    (``html[data-theme="light"][data-lang="zh"]``) and every element rule
    (``html[data-theme="light"] .odo-needle { …``).
    """
    bodies, i = [], 0
    while True:
        start = text.find(_LIGHT_MARKER, i)
        if start < 0:
            return bodies
        end = text.index("\n}", start)
        bodies.append(text[start:end])
        i = end


class Tokens:
    """Resolved colour + type vocabulary for one theme."""

    def __init__(self, text: str, theme: str):
        text = _strip_comments(text)
        light_bodies = _light_block_bodies(text)
        assert light_bodies, "no html[data-theme=light] token block in theme.css"
        # Dark = everything before the FIRST light block: the dark :root block.
        # (The zh --up/--down swap blocks live AFTER it, so a first-match can
        # never pick them up.) The dark --ink-mix-* block, though, sits in a
        # LATER :root — after the light theme block — so mixes search the whole
        # file for dark (first match = dark :root) and light keeps its blocks.
        self.part = text[:text.find(_LIGHT_MARKER)] if theme == "dark" \
            else "\n".join(light_bodies)
        self.mix_part = text if theme == "dark" else self.part
        # The --fs-* ladder is defined once (dark :root) and never re-themed,
        # so type sizes always search the whole stripped file.
        self.type_part = text
        self.theme = theme
        self.tokens = {}
        for name in ("bg", "panel", "panel2", "text", "muted", "line",
                     "up", "down", "warn", "info"):
            self.tokens[name] = self._color(name)
        self.fs = {name: self._px(name) for name in
                   ("display", "h1", "h2", "body", "sm", "label")}
        # --ink-* = color-mix(in srgb, <hue> var(--ink-mix-<hue>), var(--text)).
        for hue in ("up", "down", "warn", "info"):
            pct = self._percent(f"ink-mix-{hue}")
            self.tokens[f"ink_{hue}"] = color_mix_srgb(
                pct, self.tokens[hue] + (1.0,), self.tokens["text"] + (1.0,))

    def _value(self, name: str) -> str:
        m = re.search(rf"--{re.escape(name)}\s*:\s*([^;]+);", self.part)
        assert m, f"--{name} not found for theme={self.theme}"
        return m.group(1).strip()

    def _color(self, name: str):
        v = self._value(name)
        mix = re.fullmatch(
            r"color-mix\(in srgb, (#[0-9a-fA-F]{6}) ([\d.]+)%, (#[0-9a-fA-F]{6})\)", v)
        if mix:
            return color_mix_srgb(float(mix.group(2)),
                                  parse_hex(mix.group(1)) + (1.0,),
                                  parse_hex(mix.group(3)) + (1.0,))[:3]
        return parse_hex(v)

    def _px(self, name: str) -> float:
        m = re.search(rf"--fs-{re.escape(name)}\s*:\s*([\d.]+)px", self.type_part)
        assert m, f"--fs-{name} not found"
        return float(m.group(1))

    def _percent(self, name: str) -> float:
        m = re.search(rf"--{re.escape(name)}\s*:\s*([\d.]+)%", self.mix_part)
        assert m, f"--{name} not found for theme={self.theme}"
        return float(m.group(1))

    def rgb(self, key: str):
        """Accept ``--ink-warn`` / ``ink_warn`` / ``panel`` spellings alike."""
        return self.tokens[key.lstrip("-").replace("-", "_")]


DARK = Tokens(theme_css_text(), "dark")
LIGHT = Tokens(theme_css_text(), "light")

# The .rrp surfaces are opaque, but they are STACKED on a translucent dialog
# panel, so resolve the dialog first and composite every surface over it:
#   page canvas --bg  ->  dialog panel (rgba, per theme)  ->  .rrp surface.
# US #dlg-risk: .mx5-dlg-panel dark rgba(13,17,24,.88) / light #ffffff
#   (templates/dashboard.html.j2, "FROSTED glass panel" block).
# Country (cn/hk/ca) dialog: .cnx-dlg-panel dark rgba(13,17,24,.94) /
#   light rgba(255,255,255,.98) (templates/china.html.j2; hk/ca mirror it).
# The blur/scrim behind the panel is flattened to the --bg canvas — moot for
# every pair below, because each .rrp surface is opaque and covers the panel.
DIALOG_PANEL = {
    ("dark", "us"): parse_rgba("rgba(13,17,24,.88)"),
    ("light", "us"): solid(parse_hex("#ffffff")),
    ("dark", "cn"): parse_rgba("rgba(13,17,24,.94)"),
    ("light", "cn"): parse_rgba("rgba(255,255,255,.98)"),
}


def dialog_base(theme: str, market: str = "us"):
    tokens = DARK if theme == "dark" else LIGHT
    return over(DIALOG_PANEL[(theme, market)], solid(tokens.rgb("bg")))


def surface(theme: str, key: str):
    """A .rrp surface token composited over the dialog panel it sits on."""
    tokens = DARK if theme == "dark" else LIGHT
    return over(solid(tokens.rgb(key)), dialog_base(theme))


def surface_keys(pair: "Pair", theme: str):
    if pair.head_bg:
        # .rrp-heading paints a panel2->panel gradient in dark (worst endpoint
        # wins); the light theme overrides the gradient with flat --panel.
        return ("--panel2", "--panel") if theme == "dark" else ("--panel",)
    return pair.surfaces


def ink(theme: str, key: str, alpha: float = 1.0):
    tokens = DARK if theme == "dark" else LIGHT
    r, g, b = tokens.rgb(key)[:3]
    return (r, g, b, alpha)


# ---------------------------------------------------------------------------
# The colour pairs.
#
#   selector · ink token · surface token(s) · font px/weight · WCAG kind
#   — every value's origin is cited in `src` (file + rule).
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Pair:
    id: str
    selector: str
    ink_key: str
    px: float
    weight: int
    kind: str                 # "text" | "non-text"
    src: str
    head_bg: bool = False     # sits on the .rrp-heading surfaces
    alpha: float = 1.0        # ink alpha before compositing (chart guides)
    surfaces: tuple = ("--panel",)


PAIRS = (
    # — section furniture (pullback css rules; tokens from theme.css) —
    Pair("rrp-text-inherited", ".rrp (base ink, inherited)", "--text",
         DARK.fs["body"], 400, "text", "pb-css:4 (color/bg) · theme.css :root+light blocks"),
    Pair("rrp-heading-h2", ".rrp .rrp-heading h2", "--text",
         DARK.fs["h1"], 800, "text", "pb-css:8 (800 × fs-h1) · bg pb-css:7/43",
         head_bg=True),
    Pair("rrp-eyebrow", ".rrp .rrp-eyebrow", "--muted",
         DARK.fs["label"], 600, "text", "pb-css:9 · bg pb-css:7/43",
         head_bg=True),
    Pair("rrp-stamp", ".rrp .rrp-stamp", "--muted",
         DARK.fs["label"], 400, "text", "pb-css:11 · bg pb-css:7/43",
         head_bg=True),
    Pair("rrp-sub", ".rrp .rrp-sub", "--muted",
         DARK.fs["body"], 400, "text", "pb-css:10 · bg pb-css:4"),
    Pair("rrp-label", ".rrp .rrp-label", "--muted",
         DARK.fs["sm"], 400, "text", "pb-css:14 · bg pb-css:4"),
    Pair("rrp-note", ".rrp .rrp-note", "--muted",
         DARK.fs["sm"], 400, "text", "pb-css:18 · bg pb-css:4"),
    Pair("rrp-age", ".rrp .rrp-age", "--muted",
         DARK.fs["sm"], 400, "text", "pb-css:19 · bg pb-css:4"),
    Pair("rrp-limit", ".rrp .rrp-limit", "--muted",
         DARK.fs["sm"], 400, "text", "pb-css:37 · bg pb-css:4"),
    Pair("rrp-chart-caption", ".rrp .rrp-chart-caption", "--muted",
         DARK.fs["sm"], 400, "text", "pb-css:55 · bg pb-css:21"),
    Pair("rrp-method-summary", ".rrp .rrp-method summary", "--text",
         DARK.fs["sm"], 400, "text", "pb-css:31 · bg pb-css:21"),
    Pair("rrp-method-summary-glyph", ".rrp .rrp-method summary::after ('+'/'−')", "--muted",
         DARK.fs["h2"], 400, "text", "pb-css:33 · bg pb-css:21"),
    Pair("rrp-forecast-row-label", ".rrp .rrp-forecast-row span (inherited)", "--text",
         DARK.fs["sm"], 400, "text", "pb-css:27 (no color) · bg pb-css:21"),
    Pair("rrp-forecast-row-value", ".rrp .rrp-forecast-row strong", "--muted",
         DARK.fs["sm"], 400, "text", "pb-css:29 · bg pb-css:21"),
    Pair("pbx-expiry", ".rrp .pbx-expiry", "--ink-warn",
         DARK.fs["body"], 400, "text", "pb-css:38 · bg pb-css:4"),
    Pair("rrp-forecast-eyebrow", ".rrp .rrp-forecast .rrp-eyebrow", "--ink-warn",
         DARK.fs["label"], 600, "text", "pb-css:26 · bg pb-css:21"),
    # — study columns sit on .rrp-study > div (--panel) —
    Pair("rrp-study-h3", ".rrp .rrp-study h3", "--text",
         DARK.fs["h2"], 700, "text", "pb-css:22 · bg pb-css:21"),
    Pair("rrp-study-p", ".rrp .rrp-study p (also .rrp-method p)", "--muted",
         DARK.fs["body"], 400, "text", "pb-css:23/36 · bg pb-css:21"),
    Pair("rrp-history-cell", ".rrp .rrp-history th/td (inherited)", "--text",
         DARK.fs["sm"], 400, "text", "pb-css:56-57 (no color) · bg pb-css:21"),
    # — signals / verdict block —
    Pair("rrp-signals-dt", ".rrp .rrp-signals dt", "--muted",
         DARK.fs["sm"], 400, "text", "pb-css:78 · bg pb-css:4"),
    Pair("rrp-signals-dd", ".rrp .rrp-signals dd", "--text",
         DARK.fs["body"], 600, "text", "pb-css:79 · bg pb-css:4"),
    Pair("rrp-verdict", ".rrp .rrp-verdict", "--text",
         DARK.fs["sm"], 400, "text", "pb-css:80 · bg pb-css:4"),
    Pair("rrp-gaps", ".rrp .rrp-gaps", "--muted",
         DARK.fs["sm"], 400, "text", "pb-css:81 · bg pb-css:4"),
    Pair("rrp-phase-trail", ".rrp .rrp-phase-trail", "--muted",
         DARK.fs["sm"], 400, "text", "pb-css:82 · bg pb-css:4"),
    # — metrics: fs-h1 28px and fs-display 46px are >=24px → LARGE text —
    Pair("rrp-metrics-strong", ".rrp .rrp-metrics strong", "--ink-down",
         DARK.fs["h1"], 600, "text", "pb-css:15 · bg pb-css:4"),
    Pair("rrp-metrics-primary", ".rrp .rrp-metrics .rrp-primary", "--ink-down",
         DARK.fs["display"], 600, "text", "pb-css:15-16 · bg pb-css:4"),
    Pair("rrp-metrics-rebound", ".rrp .rrp-metrics .rrp-rebound", "--ink-up",
         DARK.fs["h1"], 600, "text", "pb-css:15,17 · bg pb-css:4"),
    # — chart TEXT ink (illus.css; .rrp pins the elements' opacity to 1) —
    Pair("ilx-d-corner-label", ".rrp .rrp-chart .ilx-d (corner dates)", "--muted",
         10.0, 400, "text",
         "illus.css .ilx-d · opacity pinned 1 by pb-css:64 · bg pb-css:21"),
    Pair("ilx-reflab", ".rrp .rrp-chart .ilx-reflab (reference 0)", "--muted",
         9.5, 400, "text",
         "illus.css .ilx-reflab (bg panel 78% over panel = panel) · opacity 1 pb-css:64"),
    # — NON-TEXT indicators, >=3:1 (WCAG 2.2 §1.4.11) —
    Pair("ilx-path", ".rrp .rrp-chart .ilx-path (drawdown stroke)", "--down",
         1.6, 0, "non-text",
         "illus.css .ilx-path/.ilx-down + _svg_drawdown · accent lib/pullback_depth.py present()"),
    Pair("ilx-dot", ".rrp .rrp-chart .ilx-dot-down (settle point)", "--down",
         3.2, 0, "non-text", "illus.css .ilx-dot-down · illus.py _svg_drawdown"),
    Pair("focus-outline", ".rrp .rrp-method summary:focus-visible outline", "--ink-info",
         2.0, 0, "non-text", "pb-css:35 · bg pb-css:21"),
    Pair("ilx-water-top", ".rrp .rrp-chart .ilx-water-top (0% waterline)", "--down",
         1.0, 0, "non-text",
         "illus.css .ilx-water-top (stroke --down) · opacity .55 pinned by pb-css:62",
         alpha=0.55),
    Pair("ilx-ref", ".rrp .rrp-chart .ilx-ref (reference=0 rule)", "--muted",
         1.0, 0, "non-text",
         "illus.css .ilx-ref (opacity .40 = pb-css:63) · emitted for reference=0",
         alpha=0.40),
)

# Pairs that FAIL the audit at HEAD. strict xfail keeps them visible as
# PRODUCT findings and re-opens the audit the moment a fix lands (an XPASS
# fails this test) — and any NEW regression below threshold fails loudly.
KNOWN_FAILURES = {
    ("ilx-water-top", "dark"),
    ("ilx-water-top", "light"),
    ("ilx-ref", "dark"),
    ("ilx-ref", "light"),
}


def head_surface(pair: Pair, theme: str):
    """Worst-case surface under a pair, dialog panel included in the chain."""
    candidates = [surface(theme, k) for k in surface_keys(pair, theme)]
    ink_rgba = ink(theme, pair.ink_key, pair.alpha)
    return min(candidates,
               key=lambda s: contrast_ratio(over(ink_rgba, s), s))


def required_ratio(pair: Pair) -> float:
    if pair.kind == "non-text":
        return 3.0
    if pair.px >= 24.0 or (pair.px >= 18.66 and pair.weight >= 700):
        return 3.0
    return 4.5


def measure(pair: Pair, theme: str):
    bg = head_surface(pair, theme)
    fg = over(ink(theme, pair.ink_key, pair.alpha), bg)
    return contrast_ratio(fg, bg)


MEASURED = {(p.id, t): measure(p, t) for p in PAIRS for t in ("dark", "light")}


def _param_rows():
    rows = []
    for pair in PAIRS:
        for theme in ("dark", "light"):
            marks = []
            if (pair.id, theme) in KNOWN_FAILURES:
                marks.append(pytest.mark.xfail(strict=True, reason=(
                    f"PRODUCT FINDING: {pair.selector} measured "
                    f"{MEASURED[(pair.id, theme)]:.2f}:1 < "
                    f"{required_ratio(pair):.1f}:1 ({theme}) at HEAD — "
                    f"templates untouched by this test")))
            rows.append(pytest.param(pair, theme, id=f"{pair.id}-{theme}", marks=marks))
    return rows


@pytest.mark.parametrize(("pair", "theme"), _param_rows())
def test_pullback_contrast(pair: Pair, theme: str):
    ratio, need = MEASURED[(pair.id, theme)], required_ratio(pair)
    tokens = DARK if theme == "dark" else LIGHT
    ink_rgba = ink(theme, pair.ink_key, pair.alpha)
    bg = head_surface(pair, theme)
    alpha_note = "" if pair.alpha == 1.0 else f" @ alpha {pair.alpha:.2f}"
    assert ratio >= need, (
        f"{pair.selector} [{theme}]: ink {pair.ink_key}{alpha_note} "
        f"({hex_str(ink_rgba)}) on {'+'.join(surface_keys(pair, theme))} "
        f"({hex_str(bg)}) resolves to {ratio:.2f}:1 — needs {need:.1f}:1 "
        f"(raw {pair.ink_key} = {hex_str(tokens.rgb(pair.ink_key))})"
    )


# ---------------------------------------------------------------------------
# Drift canaries: the constants this audit reasons about must still be the
# bytes the templates ship. If one of these fails, re-derive the pair table.
# ---------------------------------------------------------------------------

def test_pullback_stylesheet_still_declares_the_audited_pairs():
    css = PULLBACK_CSS.read_text(encoding="utf-8")
    for needle in (
        ".rrp{display:flex;flex-direction:column;min-width:0;color:var(--text);background:var(--panel)",
        "linear-gradient(110deg,var(--panel2),var(--panel))",
        'html[data-theme="light"] .rrp .rrp-heading{background:var(--panel)}',
        ".rrp .rrp-metrics strong{display:block;font:600 var(--fs-h1)/1.3 var(--font-mono)",
        ".rrp .rrp-metrics .rrp-rebound{color:var(--ink-up)}",
        ".rrp .rrp-forecast .rrp-eyebrow{color:var(--ink-warn)}",
        "color:var(--ink-warn)}",  # .pbx-expiry
        ".rrp .rrp-method summary:focus-visible{outline:2px solid var(--ink-info)",
        ".rrp .rrp-chart .ilx-water{opacity:.55;animation:none}",
        ".rrp .rrp-chart .ilx-ref{opacity:.4;animation:none}",
        ".rrp .rrp-chart .ilx-tag,.rrp .rrp-chart .ilx-d,.rrp .rrp-chart .ilx-reflab{opacity:1;animation:none}",
        ".rrp .rrp-study>div{padding:var(--sp-5,20px);border:1px solid var(--line);border-radius:var(--r-card,12px);background:var(--panel)}",
    ):
        assert needle in css, f"pullback css drifted, re-derive the audit: {needle!r}"


def test_chart_ink_sources_still_match_the_rendered_drawdown():
    src = PULLBACK_PY.read_text(encoding="utf-8")
    # present() builds detail_chart_html with the drawdown kind in --down;
    # if the kind/accent/reference changes, the chart pairs are stale.
    assert 'kind="drawdown"' in src
    assert 'accent="var(--down)"' in src
    assert "reference=0" in src
    illus = ILLUS_CSS.read_text(encoding="utf-8")
    m = re.search(r"\.ilx-water-top\s*\{([^}]*)\}", illus)
    assert m and "var(--down)" in m.group(1), ".ilx-water-top stroke drifted"
    m = re.search(r"\.ilx-ref\s*\{([^}]*)\}", illus)
    assert m and "var(--muted)" in m.group(1) and ".4" in m.group(1), ".ilx-ref drifted"
    m = re.search(r"\.ilx-dot-down\s*\{([^}]*)\}", illus)
    assert m and "var(--down)" in m.group(1), ".ilx-dot-down fill drifted"
    m = re.search(r"\.ilx-down\s*\{([^}]*)\}", illus)
    assert m and "var(--down)" in m.group(1), ".ilx-down stroke drifted"


def test_dialog_surfaces_still_match_the_dialog_templates():
    dash = DASHBOARD.read_text(encoding="utf-8")
    assert re.search(r"\.mx5-dlg-panel\{[^}]*?background:rgba\(13,17,24,\.88\)", dash)
    assert re.search(
        r'\[data-theme="light"\] \.mx5-dlg-panel\{[^}]*?background:#ffffff;', dash, re.S)
    cn = CHINA.read_text(encoding="utf-8")
    assert "rgba(13,17,24,.94)" in cn, "cnx-dlg-panel dark surface drifted"
    assert re.search(
        r'\[data-theme="light"\] body\.page-china \.cnx-dlg-panel'
        r"\{background:rgba\(255,255,255,\.98\)", cn)


def test_dialog_layer_never_changes_a_ratio():
    """The .rrp surfaces are opaque, so pricing them over the US dialog, the CN
    dialog, or the bare page canvas must agree to float noise — one pair table
    therefore covers both dialogs."""
    for pair in PAIRS:
        for theme in ("dark", "light"):
            ink_rgba = ink(theme, pair.ink_key, pair.alpha)
            tokens = DARK if theme == "dark" else LIGHT
            ratios = []
            for base in (dialog_base(theme, "us"), dialog_base(theme, "cn"),
                         solid(tokens.rgb("bg"))):
                candidates = [over(solid(tokens.rgb(k.lstrip("-"))), base)
                              for k in surface_keys(pair, theme)]
                worst = min(candidates,
                            key=lambda s: contrast_ratio(over(ink_rgba, s), s))
                ratios.append(contrast_ratio(over(ink_rgba, worst), worst))
            assert max(ratios) - min(ratios) < 1e-9, (pair.id, theme, ratios)
            assert ratios[0] == MEASURED[(pair.id, theme)]
