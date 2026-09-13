"""W16 r3 — evidence-matrix rig: settle/canvas/fixture laws, no Playwright."""
from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

from scripts.capture_sector_central_w16_r3_evidence import (  # noqa: E402
    SI_VIEWS,
    _SECTOR_ZH,
    _empty_board,
    canvas_clip,
    cell_matrix,
    flows_html,
    mc_known,
    populated_board,
    render_page,
    render_us_stocks_board,
    require_clean_head,
)


def test_cell_matrix_covers_required_families():
    cells = cell_matrix()
    ids = [c["id"] for c in cells]
    families = {c["family"] for c in cells}
    assert "baseline" in families
    assert "b1" in families
    assert "tri-state" in families
    assert "tips" in families
    assert "m3" in families
    assert "sibling" in families
    assert "m6" in families
    # 8 baselines
    bases = [c for c in cells if c["family"] == "baseline"]
    assert len(bases) == 8
    themes = {(c["theme"], c["locale"], c["w"]) for c in bases}
    assert themes == {
        ("dark", "en", 1440), ("dark", "en", 390),
        ("dark", "zh", 1440), ("dark", "zh", 390),
        ("light", "en", 1440), ("light", "en", 390),
        ("light", "zh", 1440), ("light", "zh", 390),
    }
    # six tabs
    for view in SI_VIEWS:
        assert f"tab-{view}-dark-en-desktop" in ids
    # 390w h-scroll receipts for every non-overview view × both langs
    for view in SI_VIEWS:
        if view == "overview":
            continue
        assert f"hscroll-{view}-dark-en-mobile" in ids
        assert f"hscroll-{view}-dark-zh-mobile" in ids
    assert any(c["id"].startswith("b1-narrow-") for c in cells)
    assert any(c["id"].startswith("b1-mixed-") for c in cells)
    assert any(c["id"].startswith("b1-empty-") for c in cells)
    assert any(c["id"].startswith("tri-baked-") for c in cells)
    assert any(c["id"].startswith("tri-skel-") for c in cells)
    assert "tri-skel-dark-zh" in ids
    assert "tri-skel-light-zh" in ids
    assert "tri-jsreject-baked-dark-en" in ids
    assert "tri-jsreject-baked-dark-zh" in ids
    assert any(c["id"].startswith("tri-jsempty-") for c in cells)
    assert any(c["id"].startswith("tri-jsreject-") for c in cells)
    assert any(c["id"].startswith("grader-tip-") for c in cells)
    assert any(c["id"].startswith("lead-tip-") for c in cells)
    assert any(c["id"].startswith("m3-wait-") for c in cells)
    assert "sibling-usstocks-dark-en" in ids
    assert "sibling-si-dark-en" in ids
    assert any(c["id"].startswith("m6-watch-") for c in cells)
    assert "m6-absent-dark-en" in ids
    # light art-direction cells exist for visual families
    assert any(c["theme"] == "light" and c["family"] == "tri-state" for c in cells)
    assert any(c["theme"] == "light" and c["id"].startswith("tri-skel-") for c in cells)
    assert any(c["kind"] == "canvas" for c in cells)
    assert all(c["kind"] in ("fullpage", "canvas") for c in cells)


def test_populated_fixture_bakes_narrow_and_wait_lane():
    html = render_page()
    assert html.lower().count("<h1") == 1
    assert 'body class="macro-desk page-baskets"' in html
    assert "Narrow" in html and "狭窄" in html
    assert "class=\"skel\"" not in html.split('id="mkt-breadth"')[1][:80]
    assert "WAIT" in html and "等待" in html
    assert "unconfirmed — wait" in html or "未确认 — 等待" in html
    assert "clean entry" not in html
    assert "入场干净" not in html
    assert "BOTTOMING" in html
    assert "act-watch-strip" in html
    assert "Theme reasons → Sector Intelligence" not in html
    assert "+5 more" not in html
    assert "S&amp;amp;P 500" not in html
    assert "S&amp;P 500" in html or "S&P 500" in html
    for zh in _SECTOR_ZH.values():
        assert zh in html


def test_no_payload_fixture_skeleton_null_sentence_absent():
    html = render_page(market_concentration=None, baskets_as_of=None)
    chunk = html[html.index('id="internals-section"'):html.index('id="sc-heatmap"')]
    assert "class=\"skel\"" in chunk or "class='skel'" in chunk
    assert "Not in tonight" not in chunk
    assert "不在今晚的构建中" not in chunk
    assert "mx-empty" not in chunk
    assert "This read is being updated." not in chunk
    assert "该读数更新中。" not in chunk


def test_empty_board_fixture_omits_watch_wrapper():
    html = render_page(action_board=_empty_board(), bottoming=None)
    assert 'class="act-watch-strip"' not in html


def test_us_stocks_host_keeps_cta_score_and_more():
    html = render_us_stocks_board()
    assert "Theme reasons → Sector Intelligence" in html
    assert "+5 more" in html
    assert "full list on Sector Intelligence" in html
    assert 'class="pg-more' not in html
    assert 'class="act-row-score' in html
    assert 'class="act-watch-strip"' not in html
    assert "body class='macro-desk page-stocks'" in html


def test_flows_html_eleven_zh_and_net_untinted():
    html = flows_html()
    for zh in _SECTOR_ZH.values():
        assert zh in html
    assert "−$4.1B" in html or "−$4.1B" in html
    # Net cell has no background tint
    net = html[html.index("scf-net"):]
    first_td = net.split("</td>")[1] if "</td>" in net else net
    assert "background" not in first_td or "background:color-mix" not in (
        net.split("<tr")[1] if False else first_td)


def test_canvas_clip_pads_and_clamps():
    box = canvas_clip({"x": 10, "y": 10, "width": 100, "height": 40}, 1440, 900, pad=16)
    assert box["x"] == 0.0  # 10-16 clamped
    assert box["y"] == 0.0
    assert box["width"] >= 100
    edge = canvas_clip({"x": 1400, "y": 880, "width": 80, "height": 40}, 1440, 900, pad=16)
    assert edge["x"] + edge["width"] <= 1440
    assert edge["y"] + edge["height"] <= 900
    assert edge["width"] >= 4 and edge["height"] >= 4


def test_readme_art_direction_strings_live_in_rig():
    src = (ROOT / "scripts" / "capture_sector_central_w16_r3_evidence.py").read_text(
        encoding="utf-8")
    assert "## DARK TREATMENT" in src
    assert "## LIGHT TREATMENT" in src
    assert "Mechanisms that INTENTIONALLY differ" in src
    assert "SETTLE" in src
    assert "Producer-faithful populated fixture" in src
    assert "1 deselected" in src
    assert "template↔site sync REFUSED" in src
    assert "__skyDeck" in src
    assert "getAnimations" in src
    assert "canvas-context" in src or "viewport-region" in src
    assert "page.screenshot" in src
    assert "locator(" in src  # used for wait, not element.screenshot
    assert ".screenshot(" not in src.replace("page.screenshot", "")


def test_require_clean_head_refuses_when_dirty(tmp_path, monkeypatch):
    import scripts.capture_sector_central_w16_r3_evidence as M

    def fake_check_output(cmd, cwd=None, text=False):
        if cmd[:3] == ["git", "status", "--porcelain"]:
            return " M templates/sector_central.html.j2\n"
        return "deadbeef\n"

    monkeypatch.setattr(M.subprocess, "check_output", fake_check_output)
    with pytest.raises(SystemExit) as ei:
        require_clean_head(tmp_path)
    assert "porcelain not empty" in str(ei.value)


def test_mc_known_three_way():
    assert mc_known("narrow")["verdict"] == "narrow"
    assert mc_known("broad")["verdict"] == "broad"
    assert mc_known("mixed")["verdict"] == "mixed"
    board = populated_board()
    assert board["buy_soon"][0]["label"] == "BOTTOMING"
    assert board["buy_soon"][0]["stat_en"] == "unconfirmed — wait"
    assert board["buy_soon"][0]["stat_zh"] == "未确认 — 等待"
    assert board["buy_soon"][0]["chip_en"] == "WAIT"
    assert board["total"] == 44
    assert board["buy_now"][0]["kind"] == "theme"
    assert board["buy_now"][0]["reco"] == "accumulate"
    assert board["take_profits"][0]["stat_en"] == "risk check: trim"
