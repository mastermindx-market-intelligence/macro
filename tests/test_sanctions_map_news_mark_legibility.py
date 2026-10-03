"""tests/test_sanctions_map_news_mark_legibility.py — F02 O21d.

UK "official press" map mark + panel legibility fixes (D1/D4/D6/D7).
No browser; verifies the CSS and the rendered HTML for both states
(public_news_state='ok' and 'none_recent' / no public_news).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from engine import europe_news_intel, sanctions_map
from tests.test_sanctions_map_event_pins import (
    _render as _render,
    _write_events_parquet as _write_events_parquet,
    _write_ofac as _write_ofac,
)

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = (ROOT / "templates" / "sanctions_map.html.j2").read_text(encoding="utf-8")


# O28 R2 — 4-line mobile block that replaces the legacy @media (max-width:600px)
# line.  W/OD/OL chosen by measured sweep (D54); the block MUST appear
# verbatim in TEMPLATE and its opacities MUST match the receipt's
# `dom.json` recorded values (see test_t12).
NEW_MOBILE_BLOCK = "\n".join([
    "@media (max-width:600px){.sm-map[data-news-gbr=\"1\"] .wm-c[data-iso3=\"GBR\"],html[data-theme=\"light\"] .sm-map[data-news-gbr=\"1\"] .wm-c[data-iso3=\"GBR\"]{stroke-width:1.25;stroke-dasharray:none;stroke-opacity:.85}",
    "html[data-theme=\"light\"] .sm-map[data-news-gbr=\"1\"] .wm-c[data-iso3=\"GBR\"]{stroke-opacity:.85}",
    ".sm-legend .sm-legend-news i{border:1.25px solid var(--ink-link);opacity:.85}",
    "html[data-theme=\"light\"] .sm-legend .sm-legend-news i{opacity:.85}}",
])


# Slice from "@media (max-width:600px){" to its closing "}}" (inclusive).
def _mobile_slice(t: str) -> str:
    start = t.index("@media (max-width:600px){")
    # find matching closing brace: scan brace depth
    depth = 0
    i = start
    while i < len(t):
        ch = t[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return t[start:i + 1]
        i += 1
    raise AssertionError("no closing brace for @media (max-width:600px) block")


# --------------------------------------------------------------------------- #
# t1 / t2 / t6 — static CSS rules
# --------------------------------------------------------------------------- #
def test_t1_base_and_light_mark_rules_carry_vector_effect_and_dasharray():
    base = ".sm-map[data-news-gbr=\"1\"] .wm-c[data-iso3=\"GBR\"]{stroke:var(--ink-link);stroke-width:1.25;vector-effect:non-scaling-stroke;stroke-dasharray:4 2.5;stroke-linecap:round;stroke-linejoin:round}"
    light = "html[data-theme=\"light\"] .sm-map[data-news-gbr=\"1\"] .wm-c[data-iso3=\"GBR\"]{stroke:var(--ink-link);stroke-width:1.25;vector-effect:non-scaling-stroke;stroke-dasharray:4 2.5;stroke-linecap:round;stroke-linejoin:round}"
    assert base in TEMPLATE, "base mark rule missing or wrong"
    assert light in TEMPLATE, "light mark rule missing or wrong"
    assert "vector-effect:non-scaling-stroke" in TEMPLATE
    assert "stroke-dasharray" in TEMPLATE


def test_t2_mobile_media_block_overrides_stroke_dasharray_for_gbr():
    assert NEW_MOBILE_BLOCK in TEMPLATE, (
        "O28: legacy @media (max-width:600px) line not replaced by 4-line NEW_MOBILE_BLOCK"
    )


def test_t7_mobile_mark_never_dashed_below_600():
    # O28 — the dashed "13 8" pattern was a 1.5px closed silhouette at 390; the
    # mobile rule must drop the dasharray entirely (solid, non-scaling hairline).
    assert "stroke-dasharray:13 8" not in TEMPLATE, (
        "O28: legacy '13 8' dasharray must be removed from TEMPLATE"
    )
    mobile = _mobile_slice(TEMPLATE)
    assert "stroke-dasharray:none" in mobile, (
        "O28: @media (max-width:600px) block must contain stroke-dasharray:none"
    )


def test_t8_mobile_legend_key_matches_mark_per_theme():
    import re
    mobile = _mobile_slice(TEMPLATE)
    # base GBR mark stroke-opacity (.85); light override is the second rule (.85)
    base_mark_op = re.search(
        r"data-news-gbr=\"1\"\]\s+\.wm-c\[data-iso3=\"GBR\"\][^\{]*\{[^}]*stroke-opacity:(\.\d+)",
        mobile,
    )
    assert base_mark_op, "O28: base GBR mark stroke-opacity not found in mobile block"
    assert base_mark_op.group(1) == ".85", (
        f"O28: base mark stroke-opacity={base_mark_op.group(1)} must be .85"
    )
    light_mark_op = re.search(
        r"html\[data-theme=\"light\"\]\s+\.sm-map\[data-news-gbr=\"1\"\]\s+\.wm-c\[data-iso3=\"GBR\"\]\{stroke-opacity:(\.\d+)\}",
        mobile,
    )
    assert light_mark_op, "O28: light GBR mark stroke-opacity override not found"
    assert light_mark_op.group(1) == ".85", (
        f"O28: light mark stroke-opacity={light_mark_op.group(1)} must be .85"
    )
    # legend key border-width 1.25px solid; opacities .85 / .85
    assert "stroke-width:1.25;" in mobile, "O28: mobile GBR mark must be stroke-width:1.25;"
    assert "border:1.25px solid var(--ink-link)" in mobile, (
        "O28: mobile legend key must be border:1.25px solid var(--ink-link)"
    )
    assert "stroke-dasharray:none" in mobile
    assert "solid" in mobile
    base_key_op = re.search(
        r"\.sm-legend\s+\.sm-legend-news\s+i\{border:1\.25px solid var\(--ink-link\);opacity:(\.\d+)\}",
        mobile,
    )
    assert base_key_op, "O28: base legend news key opacity rule not found"
    assert base_key_op.group(1) == ".85", (
        f"O28: base legend key opacity={base_key_op.group(1)} must be .85"
    )
    light_key_op = re.search(
        r"html\[data-theme=\"light\"\]\s+\.sm-legend\s+\.sm-legend-news\s+i\{opacity:(\.\d+)\}",
        mobile,
    )
    assert light_key_op, "O28: light legend news key opacity rule not found"
    assert light_key_op.group(1) == ".85", (
        f"O28: light legend key opacity={light_key_op.group(1)} must be .85"
    )


def test_t9_desktop_key_matches_mark():
    # Outside the @media (max-width:600px) block, the desktop rules must remain
    # untouched: legend key is 1.25px dashed, BOTH GBR mark rules (base + light)
    # carry stroke-width:1.25 and a stroke-dasharray value that is not "none".
    import re
    mobile = _mobile_slice(TEMPLATE)
    before = TEMPLATE[: TEMPLATE.index(mobile)]
    after = TEMPLATE[TEMPLATE.index(mobile) + len(mobile):]
    desktop = before + after
    assert "1.25px dashed" in desktop, (
        "O28: desktop legend news key must remain 1.25px dashed"
    )
    base_mark = re.search(
        r"\.sm-map\[data-news-gbr=\"1\"\]\s+\.wm-c\[data-iso3=\"GBR\"\]\{stroke:var\(--ink-link\);stroke-width:1\.25;vector-effect:non-scaling-stroke;stroke-dasharray:(\d+\s+\S+);stroke-linecap:round;stroke-linejoin:round\}",
        desktop,
    )
    assert base_mark, "O28: desktop base GBR mark rule not found"
    assert base_mark.group(1).strip() != "none", (
        "O28: desktop base GBR mark dasharray must not be 'none'"
    )
    light_mark = re.search(
        r"html\[data-theme=\"light\"\]\s+\.sm-map\[data-news-gbr=\"1\"\]\s+\.wm-c\[data-iso3=\"GBR\"\]\{stroke:var\(--ink-link\);stroke-width:1\.25;vector-effect:non-scaling-stroke;stroke-dasharray:(\d+\s+\S+);stroke-linecap:round;stroke-linejoin:round\}",
        desktop,
    )
    assert light_mark, "O28: desktop light GBR mark rule not found"
    assert light_mark.group(1).strip() != "none", (
        "O28: desktop light GBR mark dasharray must not be 'none'"
    )


def test_t10_mobile_block_has_no_colour_literals():
    mobile = _mobile_slice(TEMPLATE)
    for tok in ("color-mix(", "#", "rgb("):
        assert tok not in mobile, (
            f"O28: mobile block must not contain literal '{tok}'"
        )


def test_t11_390_is_inside_breakpoint():
    import re
    mobile = _mobile_slice(TEMPLATE)
    m = re.search(r"max-width:(\d+)px", mobile)
    assert m, "O28: @media max-width not found in mobile block"
    assert int(m.group(1)) >= 390, (
        f"O28: breakpoint {m.group(1)}px must cover 390 px"
    )


def test_t6_labels_never_break_mid_word():
    assert ".sm-events .src,.sm-events li>span{white-space:nowrap}" in TEMPLATE


# --------------------------------------------------------------------------- #
# t12 — D54 choice ↔ receipt drift guard
# --------------------------------------------------------------------------- #
def test_t12_mobile_mark_is_not_quieter_than_light_floor():
    """O28 R2 (D54): the chosen OD/OL values pinned in the template
    MUST match the values the mobile-key receipt recorded. A drift
    between the CSS and the receipt means the template was changed
    without re-running the sweep — fail closed."""
    import json as _json
    import re as _re

    dom_path = (
        ROOT / "mockups" / "evidence" / "sanctions-map-mobile-key" / "dom.json"
    )
    assert dom_path.is_file(), (
        f"O28 R2: missing mobile-key receipt at {dom_path} — "
        "run capture.py with the chosen (W, OD, OL) first."
    )
    dom = _json.loads(dom_path.read_text(encoding="utf-8"))
    cells = dom.get("cells", {})
    # O28 R2 receipt captures all four (theme × locale) cells; the
    # opacities must agree across locales for each theme.
    for theme in ("dark", "light"):
        opacities = []
        for locale in ("en", "zh"):
            key = f"{theme}-{locale}"
            assert key in cells, f"O28 R2: missing cell {key} in dom.json"
            opacities.append(cells[key]["gbr_stroke_opacity"])
        assert opacities[0] == opacities[1], (
            f"O28 R2: {theme} mark opacity drift across locales: {opacities}"
        )

    dark_od = cells["dark-en"]["gbr_stroke_opacity"]
    light_ol = cells["light-en"]["gbr_stroke_opacity"]
    expected_dark = ".85"
    expected_light = ".85"
    # Browser computed style reports "0.85" while CSS source writes
    # ".85" — compare numerically.
    assert abs(float(dark_od) - float(expected_dark)) < 1e-6, (
        f"O28 R2: receipt dark opacity {dark_od} must equal CSS value {expected_dark}"
    )
    assert abs(float(light_ol) - float(expected_light)) < 1e-6, (
        f"O28 R2: receipt light opacity {light_ol} must equal CSS value {expected_light}"
    )

    # Confirm the template still carries the same opacities.
    mobile = _mobile_slice(TEMPLATE)
    base_mark_op = _re.search(
        r"data-news-gbr=\"1\"\]\s+\.wm-c\[data-iso3=\"GBR\"\][^\{]*\{[^}]*stroke-opacity:(\.\d+)",
        mobile,
    )
    assert base_mark_op, "O28 R2: CSS base mark stroke-opacity not found"
    assert abs(float(base_mark_op.group(1)) - float(dark_od)) < 1e-6, (
        f"O28 R2: CSS dark opacity {base_mark_op.group(1)} "
        f"drifts from receipt {dark_od}"
    )
    light_mark_op = _re.search(
        r"html\[data-theme=\"light\"\]\s+\.sm-map\[data-news-gbr=\"1\"\]\s+\.wm-c\[data-iso3=\"GBR\"\]\{stroke-opacity:(\.\d+)\}",
        mobile,
    )
    assert light_mark_op, "O28 R2: CSS light mark stroke-opacity not found"
    assert abs(float(light_mark_op.group(1)) - float(light_ol)) < 1e-6, (
        f"O28 R2: CSS light opacity {light_mark_op.group(1)} "
        f"drifts from receipt {light_ol}"
    )


# --------------------------------------------------------------------------- #
# t3 — source order: mark rule after .is-hi rule in BOTH base and light
# --------------------------------------------------------------------------- #
def test_t3_mark_rule_appears_after_is_hi_rule_in_both_blocks():
    base_is_hi = TEMPLATE.index('.sm-map[data-hi] .wm-c.is-hi{fill-opacity:.85')
    base_mark = TEMPLATE.index(
        '.sm-map[data-news-gbr="1"] .wm-c[data-iso3="GBR"]{stroke:var(--ink-link);stroke-width:1.25'
    )
    assert base_mark > base_is_hi, (
        f"base: mark offset {base_mark} must be after .is-hi offset {base_is_hi}"
    )

    light_is_hi = TEMPLATE.index(
        'html[data-theme="light"] .sm-map[data-hi] .wm-c.is-hi{fill-opacity:.52'
    )
    light_mark = TEMPLATE.index(
        'html[data-theme="light"] .sm-map[data-news-gbr="1"] .wm-c[data-iso3="GBR"]{stroke:var(--ink-link);stroke-width:1.25'
    )
    assert light_mark > light_is_hi, (
        f"light: mark offset {light_mark} must be after .is-hi offset {light_is_hi}"
    )


# --------------------------------------------------------------------------- #
# t4 / t5 — render under (a) UK event and (b) no event
# --------------------------------------------------------------------------- #
@pytest.fixture
def _vm_with_uk_event(tmp_path, monkeypatch):
    parquet = tmp_path / "europe_news_vector" / "events.parquet"
    _write_events_parquet(parquet)  # default: asof = yesterday (state='ok')
    monkeypatch.setattr(europe_news_intel, "_events_path", lambda: parquet)
    sdn, meta, cfg = _write_ofac(tmp_path)
    return sanctions_map.build(sdn_file=sdn, meta_file=meta, programs_config=cfg)


@pytest.fixture
def _vm_with_no_recent_event(tmp_path, monkeypatch):
    parquet = tmp_path / "europe_news_vector" / "events.parquet"
    _write_events_parquet(parquet, asof_offset_days=-3)  # state='none_recent'
    monkeypatch.setattr(europe_news_intel, "_events_path", lambda: parquet)
    sdn, meta, cfg = _write_ofac(tmp_path)
    return sanctions_map.build(sdn_file=sdn, meta_file=meta, programs_config=cfg)


def test_t4_render_with_uk_event_includes_legend_key_and_heading_and_zh_note(_vm_with_uk_event):
    assert _vm_with_uk_event["public_news_state"] == "ok"
    html = _render(_vm_with_uk_event)
    assert 'class="sm-legend-news"' in html
    assert "UK: official press, last 2 days" in html
    assert "英国：近两日官方新闻" in html
    assert "Official press · last 2 days" in html
    assert "官方新闻 · 近两日" in html
    assert 'class="sm-orig l-zh"' in html
    assert "标题为官方英文原文" in html
    assert 'data-news-gbr="1"' in html  # the map must still be marked


def test_t5_render_with_no_recent_event_has_no_legend_key_or_zh_note(_vm_with_no_recent_event):
    import re
    assert _vm_with_no_recent_event["public_news_state"] == "none_recent"
    assert _vm_with_no_recent_event["public_news"] == []
    html = _render(_vm_with_no_recent_event)
    assert '<li class="sm-legend-news"' not in html
    assert '<p class="sm-orig' not in html
    assert "标题为官方英文原文" not in html
    # The figure MUST NOT carry data-news-gbr; the attribute only renders when
    # at least one UK row survives the freshness bound.
    assert not re.search(r'<figure[^>]*\bdata-news-gbr=', html, re.S)