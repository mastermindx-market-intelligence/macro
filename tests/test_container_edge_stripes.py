"""tests/test_container_edge_stripes.py — no colored container-edge stripe in
the dashboard / shared theme / intraday-flow templates.

Chairman design rule 2026-10-18 (docs/DESIGN_DOCTRINE.md §3): no colored left
border, inset stripe, pseudo-element rail or equivalent edge accent on cards,
panels, callouts, rows, navigation selections or banners — and never move the
stripe to another edge. Identity rides the icon, the name ink and labeled
semantic text. Chart series, data marks, neutral dividers and complete focus
outlines keep their distinct jobs.

  GUARD 1 — pseudo-element edge bars: an absolutely positioned ``::before`` /
  ``::after`` drawing a <=5px bar along a full container edge (the ``.acth``,
  ``.anv2-lane-hd``, ``.lst-ovl-hd``, ``.stance-card``, ``.nbcard``,
  ``.wnx-card`` and ``.rr-modal`` idiom this file was written to retire).
  One allowlisted site: the board ladder's NEUTRAL ``--text`` pressed-cell
  underline in theme.css.

  GUARD 2 — inset box-shadow stripes: ``inset 3px 0 0 <color>`` style shadows
  (one axis offset, no blur) that paint a single edge of a cell or tab. One
  allowlisted site: the ladder's NEUTRAL ``--text`` pressed-button underline.

  GUARD 3 — colored single-edge borders (left/top/right): a RATCHET. The legacy
  rails below carry real border width (removing them moves layout) or need a
  replacement label for the state they encode, so they are migrated in a
  follow-up, not here. A NEW colored edge fails; a removed legacy entry also
  fails until it is deleted from the pin, so the list only ever shrinks.

Browser-free: source checks over the templates and app UI roots. Historical
three-file guards remain; the estate guard has no decorative left-edge debt.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = "templates/dashboard.html.j2"
THEME = "templates/theme.css"
INTRADAY = "templates/intraday_flow.html.j2"
FILES = (DASHBOARD, THEME, INTRADAY)
SRC = {name: (ROOT / name).read_text(encoding="utf-8") for name in FILES}

_RULE_RE = re.compile(r"([^{}]+)\{([^{}]*)\}")


def _rules(name: str):
    """Yield (selector, body) for every innermost ``sel { body }`` block."""
    for m in _RULE_RE.finditer(SRC[name]):
        selector = " ".join(m.group(1).strip().splitlines()[-1].split()) if m.group(1).strip() else ""
        yield selector, m.group(2)


# --------------------------------------------------------------------------- #
# GUARD 1 — pseudo-element edge bars
# --------------------------------------------------------------------------- #

GUARD1_ALLOWED = {
    # Neutral (--text) underline under the pressed board-ladder cell: a
    # selection mark in ink, not a colored accent.
    (THEME, '.mx-ladder--board .mx-cell[aria-pressed="true"]::after'),
}

# The exact selectors this file retired. Named so a revert reads plainly.
RETIRED_PSEUDO = re.compile(
    r"\.(?:acth|anv2-lane-hd|lst-ovl-hd|stance-card|nbcard[\w.-]*|wnx-card|rr-modal)::?before\b")


def _decl(body: str, prop: str) -> str | None:
    m = re.search(r"(?<![-\w])%s\s*:\s*([^;]+)" % re.escape(prop), body)
    return m.group(1).strip() if m else None


def _is_zero(v: str | None) -> bool:
    return v is not None and v in {"0", "0px"}


def _px(v: str | None) -> float | None:
    m = re.fullmatch(r"([0-9.]+)px", v or "")
    return float(m.group(1)) if m else None


def _edges(body: str) -> dict[str, str | None]:
    edges = {k: _decl(body, k) for k in ("top", "right", "bottom", "left")}
    inset = (_decl(body, "inset") or "").split()
    if inset:
        # CSS shorthand: 1 → all, 2 → (block, inline), 3 → (top, inline, bottom), 4 → t r b l
        t, r, b, l = {1: inset * 4, 2: inset * 2, 3: inset + inset[1:2]}.get(len(inset), inset)[:4]
        for k, v in zip(("top", "right", "bottom", "left"), (t, r, b, l)):
            edges[k] = edges[k] or v
    return edges


def _is_edge_bar(body: str) -> bool:
    if not re.search(r"position\s*:\s*absolute", body):
        return False
    e = _edges(body)
    w, h = _px(_decl(body, "width")), _px(_decl(body, "height"))
    vertical = (w is not None and w <= 5 and _is_zero(e["top"]) and _is_zero(e["bottom"])
                and (_is_zero(e["left"]) or _is_zero(e["right"])))
    horizontal = (h is not None and h <= 5 and _is_zero(e["left"]) and _is_zero(e["right"])
                  and (_is_zero(e["top"]) or _is_zero(e["bottom"])))
    return vertical or horizontal


def test_guard1_allowlist_still_names_real_sites():
    found = {(name, sel) for name in FILES for sel, _ in _rules(name)}
    stale = GUARD1_ALLOWED - found
    assert not stale, f"stale GUARD1 allowlist entries — delete them: {sorted(stale)}"


@pytest.mark.parametrize("name", FILES)
def test_guard1_no_pseudo_element_edge_bar(name):
    hits = [sel for sel, body in _rules(name)
            if re.search(r"::?(?:before|after)\b", sel) and _is_edge_bar(body)
            and (name, sel) not in GUARD1_ALLOWED]
    assert not hits, f"{name}: pseudo-element edge stripe(s) — remove, identity rides the label ink: {hits}"


@pytest.mark.parametrize("name", FILES)
def test_guard1_retired_stripe_selectors_stay_gone(name):
    hits = sorted({m.group(0) for m in RETIRED_PSEUDO.finditer(SRC[name])})
    assert not hits, f"{name}: retired container stripe reintroduced: {hits}"


# --------------------------------------------------------------------------- #
# GUARD 2 — inset box-shadow stripes
# --------------------------------------------------------------------------- #

# inset <x> <y> <blur>: a stripe is exactly one non-zero axis offset, no blur.
_INSET_RE = re.compile(r"\binset\s+(-?[0-9.]+)(?:px)?\s+(-?[0-9.]+)(?:px)?\s+(-?[0-9.]+)(?:px)?")

GUARD2_ALLOWED = {
    # Neutral (--text) underline under the pressed ladder button: ink, not accent.
    (THEME, '.mx-ladder:not(.mx-ladder--board) button[aria-pressed="true"]'),
}


def _inset_stripes(body: str) -> list[str]:
    out = []
    for decl in re.findall(r"box-shadow\s*:\s*([^;]+)", body):
        for m in _INSET_RE.finditer(decl):
            x, y, blur = (abs(float(g)) for g in m.groups())
            if blur == 0 and (x == 0) != (y == 0) and max(x, y) >= 2:
                out.append(m.group(0))
    return out


def test_guard2_allowlist_still_names_real_sites():
    found = {(name, sel) for name in FILES for sel, body in _rules(name) if _inset_stripes(body)}
    stale = GUARD2_ALLOWED - found
    assert not stale, f"stale GUARD2 allowlist entries — delete them: {sorted(stale)}"


@pytest.mark.parametrize("name", FILES)
def test_guard2_no_inset_shadow_stripe(name):
    hits = [(sel, s) for sel, body in _rules(name) for s in _inset_stripes(body)
            if (name, sel) not in GUARD2_ALLOWED]
    assert not hits, f"{name}: inset-shadow edge stripe(s): {hits}"


# --------------------------------------------------------------------------- #
# GUARD 3 — colored single-edge borders (ratchet)
# --------------------------------------------------------------------------- #

_EDGE_DECL_RE = re.compile(
    r"(?<![-\w])(border-(?:top|left|right|inline-start|inline-end|block-start)(?:-color)?)\s*:\s*([^;]+)")
# Tokens that are neutral surface/ink, not semantic color.
_NEUTRAL_VARS = {"line", "hair", "hair-strong", "glass-line", "rule", "text",
                 "ink-1", "ink-2", "ink-3", "panel", "panel2", "bg", "tile", "mx5-glass-border"}


def _is_colored(value: str) -> bool:
    if any(v not in _NEUTRAL_VARS for v in re.findall(r"var\(\s*--([\w-]+)", value)):
        return True
    for h in re.findall(r"#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b", value):
        h = h if len(h) == 6 else "".join(c * 2 for c in h)
        r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
        if max(r, g, b) - min(r, g, b) > 24:
            return True
    return False


# Legacy colored edges awaiting migration (follow-up to the 2026-11-02 stripe
# sweep). Most carry real border width or encode a state that needs a labeled
# replacement first. Delete an entry when you migrate it; never add one.
GUARD3_LEGACY = {
    DASHBOARD: {
        (".nb-cau-pop .cau-row + .cau-row", "border-top"),
        (".nb-entry", "border-top"),
        (".nbe-buy_now, .nbe-partial", "border-top-color"),
        (".nbe-buy_soon, .nbe-watch, .nbe-await_confluence", "border-top-color"),
        (".nbe-wait_pullback, .nbe-hold, .nbe-bounce_wait", "border-top-color"),
        (".nbe-extended, .nbe-topping", "border-top-color"),
        (".nbe-exit, .nbe-avoid, .nbe-blocked", "border-top-color"),
    },
    THEME: set(),
    INTRADAY: {
        # Lit top edge on the lane-tinted glass card. Its rule line also holds an
        # untokenised color-mix and a 15px radius, so editing it trips the
        # design ratchet; migrate it together with a radius + lane-line token.
        (".spot-card", "border-top-color"),
    },
}


def _colored_edges(name: str) -> set[tuple[str, str]]:
    return {(sel, m.group(1)) for sel, body in _rules(name)
            for m in _EDGE_DECL_RE.finditer(body) if _is_colored(m.group(2))}


@pytest.mark.parametrize("name", FILES)
def test_guard3_no_new_colored_edge(name):
    new = _colored_edges(name) - GUARD3_LEGACY[name]
    assert not new, (f"{name}: new colored single-edge border(s) — use an even neutral border "
                     f"and a labeled state instead: {sorted(new)}")


@pytest.mark.parametrize("name", FILES)
def test_guard3_legacy_pin_only_shrinks(name):
    gone = GUARD3_LEGACY[name] - _colored_edges(name)
    assert not gone, f"{name}: migrated legacy edge(s) — delete them from GUARD3_LEGACY: {sorted(gone)}"


# --------------------------------------------------------------------------- #
# Estate guard: left accents in shared styles, page styles and generated UI.
# Unlike the historical three-file ratchet, this has no decorative-rail debt.
# Functional exceptions below name geometry and its consumer, not legacy style.
# --------------------------------------------------------------------------- #

_LEFT_RE = re.compile(
    r"(?<![-\w])border-(?:left|inline-start)(?:-(?:color|width|style))?\s*:\s*([^;]+)")
_NEUTRAL_TOKEN = re.compile(
    r"(?:^|[-_])(?:line(?:\d|[-_](?:strong|soft|quiet))?|hair(?:-strong|-soft|-\d)?|grid|rule(?:-soft)?|border|brd|muted|faint|text|bg|panel2?)$|^thl$")

_FUNCTIONAL_LEFT = {
    # Playback glyphs and plotted triangle/price/interval marks.
    "templates/dashboard.html.j2": (".tm-play.is-playing .tm-play-ico", ".fbm-fulcrum"),
    "templates/hk.html.j2": (".tm-play.is-playing .tm-play-ico",),
    "templates/vector.html.j2": (".vtm-play.is-playing .vtm-play-ico",),
    "templates/sector_cycles.css": (".cyc-legend .lm-pk", ".cyc-legend .lm-tr"),
    "templates/options.html.j2": (".oew-lad-mk.flip",),
    "templates/watchlist.html.j2": (".seam-gap .over", ".seam-brk .span"),
    # Solid/dashed relationship connectors, including severed links.
    "templates/ontology.css": ('.station[data-link="false"] .st-break::after',),
    "templates/gmi.css": (".gmi-chain-step",),
    "templates/government-revenue-parity.css": (".atlas-hop",),
    # Timeline stems, hierarchy guides and comparison-table group separators.
    "templates/theme.css": (".af-item",),
    "templates/commodities.html.j2": (".tl-item",),
    "templates/intl_workspace_history.css": (".intl-history__timeline",),
    "templates/ticker_news.css": (".tn-members",),
    "templates/intl.html.j2": (".grp",),
    "templates/theme_tree.html.j2": (".tt-subtheme",),
    "templates/intraday_flow.html.j2": (".comp-seg + .comp-seg",),
    "templates/stock-dashboard.css": (".ca-v36-an-go", ".hk-v37-an-go"),
}

_FUNCTIONAL_PSEUDO = {
    "templates/theme.css": (".mx-ladder--board", ".mx-mark--", ".dmr-zero", ".dmr-track"),
    "templates/landing.css": (".founding-fill::after", ".psc-stages::before"),
    "templates/stock-dashboard.css": (".ca-v36-lead-row", ".hk-v37-lead-row"),
    "templates/fundamental_forensics.css": (".ff-gate-slots::before",),
    "templates/mm_brain.js": (".mmb-tk-rows::before", ".mmb-recap-list::before"),
    "templates/china_news.html.j2": (".tp-spine::before",),
    "templates/gmi.css": (".gmi-thread li::before",),
    "templates/help.html.j2": (".help-log::before", ".help-log::after"),
    "templates/news.html.j2": (".nxi-tick::before", ".nxw-item::before"),
    "templates/press/press_news.css": (".river::before",),
    "templates/reports.html.j2": (".rc-tl::before",),
    "templates/ticker.html.j2": (".lrow .lnode::before", ".tl::before", ".dna .dtr::before"),
    "templates/transmission.html.j2": (".cx-step:not(:last-child)::before",),
    "templates/dashboard.html.j2": (".rkc-mood-mini-track::after", ".rr-model-track::before"),
    "templates/factors.html.j2": (".rl-track::before", ".tp-rail::before"),
    "templates/intl.html.j2": (".tbl-gauge-track::after",),
    "templates/smart_money.html.j2": (".rotbars .rb-track::after",),
    "templates/subsector_rotation.js": (".sr-vs-mid::before",),
    "templates/stocktable.js": (".stf-rsz::after",),
    "templates/basket_detail.html.j2": (".gpr-rail::before",),
    "templates/finance_intelligence.css": (".fi-rerating-steps::before",),
    "templates/government-revenue-parity.css": (".atlas-hop.historic .atlas-node:after",),
    "templates/intelligence_hub.html.j2": (".sp::before",),
    "templates/watchlist.html.j2": (".stg.s-extended i::after", ".stg.s-invalid i::after"),
}



# Retained direct-source assets and embedded builder CSS are part of the website.
# These files are read as text; no market builder is executed.
_DIRECT_UI_SOURCES = (
    "scripts/build_vector.py",  # ci-trigger-closure: data — embedded CSS text, never imported
    "site/products/mastermind-ai.html",
    "site/products/market-dashboards.html",
    "site/products/market-terminal.html",
    "site/learn.html",
    "site/financial_lineage.html",
    "site/coming-soon.html",
    "site/_mockup_ccw_credit_desk.html",
    "site/start.html",
    "site/cycle.css",
    "site/radar_panel.js",
    "site/scene-motion.css",
    "site/odds.css",
)
_FUNCTIONAL_LEFT["site/odds.css"] = (".od-fm-tbl th.hsep, .od-fm-tbl td.hsep",)
_FUNCTIONAL_PSEUDO.update({
    "site/products/mastermind-ai.html": (".stgm .seg::before", ".ma-core::before"),
    "site/products/market-dashboards.html": (".stgm .seg::before", ".md-tp::before", ".md-assets::before", ".md-eng::before"),
    "site/products/market-terminal.html": (".stgm .seg::before",),
    "site/cycle.css": (".cyc-grp-3 + .cyc-grp-3::before",),
})


def _estate_sources():
    for directory in ("templates", "app"):
        for path in sorted((ROOT / directory).rglob("*")):
            if (not path.is_file() or path.suffix not in {".css", ".j2", ".html", ".js"}
                    or path.name.endswith(".min.js")
                    or path.name.startswith(("plotly-", "lightweight-charts"))):
                continue
            yield path.relative_to(ROOT).as_posix(), path.read_text(encoding="utf-8")

    for name in _DIRECT_UI_SOURCES:
        path = ROOT / name
        text = path.read_text(encoding="utf-8")
        yield name, text
        # A retained source page may have had its own stylesheet externalized.
        # Inspect its fingerprinted sheets under the page owner's identity.
        if path.suffix == ".html":
            refs = set(re.findall(r"(?:\.\./)?assets/css/[0-9a-f]{8}\.css", text))
            for ref in sorted(refs):
                asset = (path.parent / ref).resolve()
                asset.relative_to(ROOT / "site")
                yield name, asset.read_text(encoding="utf-8")


def _blank_source(match):
    return "".join("\n" if c == "\n" else " " for c in match.group())


def _clean_source(text):
    return re.sub(r"/\*.*?\*/|\{#.*?#\}|<!--.*?-->", _blank_source, text, flags=re.S)


def _estate_rules(text):
    clean = re.sub(r"\{\{.*?\}\}|\{%.*?%\}|\$\{[^{}]*\}", _blank_source,
                   _clean_source(text), flags=re.S)
    for match in re.finditer(r"\{([^{}]*)\}", clean):
        previous = max(clean.rfind("{", 0, match.start()), clean.rfind("}", 0, match.start())) + 1
        prefix = clean[previous:match.start()].strip()
        selector = prefix.splitlines()[-1].strip().lstrip(" +'\"") if prefix else ""
        if selector.startswith(("if ", "function ", "for ", "return ", "const ", "let ", "var ")):
            continue
        yield selector, text[match.start(1):match.end(1)]


def _left_accent(body):
    hits = []
    for match in _LEFT_RE.finditer(_clean_source(body)):
        value = match[1].strip()
        if value in {"0", "0px", "none", "inherit", "initial", "unset"}:
            continue
        width = re.match(r"([\d.]+)(px|rem|em)\b", value)
        wide = bool(width and float(width[1]) > (1 if width[2] == "px" else 0.0625))
        tokens = re.findall(r"var\(\s*--([\w-]+)", value)
        chromatic = (any(not _NEUTRAL_TOKEN.search(t) for t in tokens)
                     or bool(re.search(r"currentcolor|\b(?:red|green|blue|orange|purple|yellow|cyan|magenta)\b|\{\{|\$\{", value, re.I))
                     or bool(re.search(r"#[0-9a-fA-F]{3,8}\b|\brgba?\(", value)))
        if wide or chromatic:
            hits.append(match.group())
    return hits


def _estate_pseudo_bar(body):
    if _decl(body, "content") in {"none", "normal"}:
        return False
    if _decl(body, "position") not in {"absolute", "fixed", "sticky"}:
        # A painted block inserted before card content is also an edge strip.
        return (_decl(body, "display") == "block" and _px(_decl(body, "height")) is not None
                and 0 < _px(_decl(body, "height")) <= 6
                and _decl(body, "width") in {None, "auto", "100%"}
                and bool(_decl(body, "background")))
    e = _edges(body)
    present = lambda value: value not in {None, "auto"}
    w, h = _px(_decl(body, "width")), _px(_decl(body, "height"))
    vertical = (w is not None and 0 < w <= 6 and (present(e["left"]) or present(e["right"]))
                and ((present(e["top"]) and present(e["bottom"])) or _decl(body, "height") == "100%"))
    horizontal = (h is not None and 0 < h <= 6 and (present(e["top"]) or present(e["bottom"]))
                  and ((present(e["left"]) and present(e["right"])) or _decl(body, "width") == "100%"))
    return vertical or horizontal


def _estate_inset_stripe(body):
    for match in re.finditer(r"\binset\s+(-?[\d.]+)(?:px)?\s+(-?[\d.]+)(?:px)?(?:\s+(-?[\d.]+)(?:px)?)?", body):
        x, y, blur = (float(match[1]), float(match[2]), float(match[3] or 0))
        if blur == 0 and (x == 0) != (y == 0) and max(abs(x), abs(y)) >= 2:
            return True
    return False


def test_estate_has_no_decorative_left_edges_or_shadow_rails():
    hits = []
    for name, text in _estate_sources():
        for selector, body in _estate_rules(text):
            if _left_accent(body) and not any(s in selector for s in _FUNCTIONAL_LEFT.get(name, ())):
                hits.append((name, selector, "left edge", _left_accent(body)))
            if _estate_inset_stripe(body) and (name, selector) not in GUARD2_ALLOWED:
                hits.append((name, selector, "inset stripe"))
            if re.search(r"::?(before|after)\b", selector) and _estate_pseudo_bar(body):
                if not any(s in selector for s in _FUNCTIONAL_PSEUDO.get(name, ())):
                    hits.append((name, selector, "pseudo stripe"))
        for match in re.finditer(r'''\bstyle\s*=\s*(["'])(.*?)\1''', _clean_source(text), re.S):
            if _left_accent(match[2]) or _estate_inset_stripe(match[2]):
                hits.append((name, "inline", match[2]))
        if re.search(r"\.style\.(?:borderLeft|borderInlineStart)(?:Color|Width)?\s*=", _clean_source(text)):
            hits.append((name, "runtime side-border assignment"))
    assert not hits, "Decorative container edges remain:\n" + "\n".join(map(str, hits))


@pytest.mark.parametrize("body", [
    "border-left:3px solid var(--warn)",
    "border-inline-start:2px solid var(--line)",
    "border-left-color:var(--up)",
    "border-left:1px solid currentColor",
    "border-left:3px solid {{ state_color }}",
    "border-left:3px solid ${color}",
])
def test_estate_detector_catches_css_and_runtime_left_accents(body):
    assert _left_accent(body)


@pytest.mark.parametrize("body", [
    "box-shadow:inset 3px 0 var(--warn)",
    "box-shadow:inset -3px 0 0 var(--up), var(--card-shadow)",
    "box-shadow:inset 0 -3px 0 var(--link)",
])
def test_estate_detector_catches_two_offset_and_composite_shadows(body):
    assert _estate_inset_stripe(body)


@pytest.mark.parametrize("body", [
    "border-left:1px solid var(--line)",
    "border-inline-start:1px solid var(--mq-line-strong)",
    "border-left:0",
])
def test_estate_detector_allows_neutral_structural_rules(body):
    assert not _left_accent(body)


def test_estate_detector_preserves_complete_focus_outlines():
    assert not _estate_inset_stripe("box-shadow:inset 0 0 0 2px var(--link)")
    assert not _estate_inset_stripe("box-shadow:0 0 0 3px var(--link)")


def test_estate_detector_catches_shortened_and_unpainted_rail_geometry():
    assert _estate_pseudo_bar('content:"";position:absolute;left:0;top:12px;bottom:12px;width:3px')
    assert not _estate_pseudo_bar('content:none;position:absolute;left:0;top:0;bottom:0;width:3px')
    assert not _estate_pseudo_bar('content:"";width:4px;height:4px;background:var(--warn)')



def test_retired_element_rails_are_not_emitted():
    """Actual spans must not bypass the border/pseudo/shadow detectors."""
    sources = dict(_estate_sources())
    for name, retired in {
        "templates/macro_monetary.html.j2": ("mc-rail-bar", "mc-arrival-bar", "mc-stance-bar", "mc-dest-bar"),
        "templates/government-revenue-page.js.j2": ("queue-rail", "candidate-rail"),
        "templates/_prophet_card.html.j2": ("mx-cap mx-cap--",),
    }.items():
        for token in retired:
            assert token not in sources[name], (name, token)
