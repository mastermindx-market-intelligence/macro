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

Browser-free: plain regex over the template bytes. LOAD CLOSURE: the three
template files named in ``FILES`` via ``Path.read_text``. Nothing else.
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
        (".alert", "border-left"),
        (".alert-act", "border-left-color"),
        (".alert-warn", "border-left-color"),
        (".alert-info", "border-left-color"),
        (".stance", "border-left"),
        (".stance-run", "border-left-color"),
        (".stance-hold", "border-left-color"),
        (".stance-shift", "border-left-color"),
        (".stance-reset", "border-left-color"),
        (".nb-stage-hd", "border-left"),
        (".nb-cau-pop .cau-row + .cau-row", "border-top"),
        (".nb-entry", "border-top"),
        (".nbe-buy_now, .nbe-partial", "border-top-color"),
        (".nbe-buy_soon, .nbe-watch, .nbe-await_confluence", "border-top-color"),
        (".nbe-wait_pullback, .nbe-hold, .nbe-bounce_wait", "border-top-color"),
        (".nbe-extended, .nbe-topping", "border-top-color"),
        (".nbe-exit, .nbe-avoid, .nbe-blocked", "border-top-color"),
        ("body.page-macro #risk-state", "border-left"),
        ("body.page-macro #risk-radar", "border-left"),
        (".plo-row", "border-left"),
        ('.plo-row[data-state="PULLBACK"]', "border-left-color"),
        ('.plo-row[data-state="RESET_TURN"]', "border-left-color"),
        ('.plo-row[data-state="RESUMED"]', "border-left-color"),
        ('html[data-theme="light"] body.page-stocks .pbr-r.pbr-warm', "border-left"),
        ("body.page-macro .ms-front>.rrx>.rrx-side", "border-left"),
        ("body.page-macro .v-flip", "border-left"),
        ("#dlg-risk .riskdlg-brief", "border-left"),
        ("body.page-macro.mx4-grid .mx5-alert-item.warn", "border-left-color"),
        ("body.page-macro.mx4-grid .mx5-alert-item.info", "border-left-color"),
        (".rr-shadow-warn", "border-left"),
        ("#week-ahead .cal-ev.cal-high", "border-left-color"),
        ("#week-ahead .cal-ev.cal-med", "border-left-color"),
        ("body.page-stocks .stk-ctx-strip", "border-left"),
        ("body.page-stocks .stk-ctx-strip.ctx-green", "border-left-color"),
        ("body.page-stocks .stk-ctx-strip.ctx-yellow", "border-left-color"),
        ("body.page-stocks .stk-ctx-strip.ctx-red", "border-left-color"),
    },
    THEME: {
        (".aibrief-card", "border-left"),
        (".verdict", "border-left"),
        (".af-pin", "border-left"),
        (".sig-gate .sig-w", "border-left"),
        (".rip-zone.rz-ready", "border-left"),
        (".rip-zone.rz-basing", "border-left"),
        (".rip-zone.rz-fall", "border-left"),
        (".mx-cap--resolved::before", "border-top"),
    },
    INTRADAY: set(),
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
