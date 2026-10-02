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
    assert (
        "@media (max-width:600px){.sm-map[data-news-gbr=\"1\"] .wm-c[data-iso3=\"GBR\"],html[data-theme=\"light\"] .sm-map[data-news-gbr=\"1\"] .wm-c[data-iso3=\"GBR\"]{stroke-width:1.5;stroke-dasharray:13 8}}"
        in TEMPLATE
    )


def test_t6_labels_never_break_mid_word():
    assert ".sm-events .src,.sm-events li>span{white-space:nowrap}" in TEMPLATE


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