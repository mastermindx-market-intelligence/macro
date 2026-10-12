"""Pure checks for the served-route pullback matrix. No browser."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.verify_risk_radar_pullback_matrix as matrix


def _cells():
    return matrix.enumerate_cells(matrix.parse_pages("us=macro.html,cn=china.html"))


def _js_cell(**overrides):
    cell = dict(_cells()[0])
    cell.update(overrides)
    return cell


def _measured(**overrides):
    measured = {
        "dialog_visible": True,
        "pbx_present": True,
        "phase": "underway",
        "forecast_heading_text": "Estimate unavailable",
        "forecast_row_text": "Further downside from today —\nEstimated total episode depth —",
        "forecast_row_count": 2,
        "page_scroll_width": 1441,
        "page_inner_width": 1440,
        "dialog_scroll_width": 376,
        "dialog_client_width": 375,
        "tab_escapes": 0,
        "escape_closes": True,
        "focus_returns_to_opener": True,
        "time_datetime": "2026-01-02T00:00:00Z",
    }
    measured.update(overrides)
    return measured


def test_enumerates_twenty_cells():
    cells = _cells()
    assert len(cells) == 20
    required = {
        "page", "file", "lang", "theme", "viewport", "width", "height", "motion", "javascript",
    }
    assert required <= set(cells[0])
    interactive = [cell for cell in cells if cell["javascript"] and cell["motion"] == "no-preference"]
    assert len(interactive) == 16
    assert {(c["page"], c["lang"], c["theme"], c["viewport"]) for c in interactive} == {
        (page, lang, theme, viewport)
        for page in ("us", "cn")
        for lang in ("en", "zh")
        for theme in ("dark", "light")
        for viewport in ("desktop", "mobile")
    }
    for cell in interactive:
        if cell["viewport"] == "desktop":
            assert (cell["width"], cell["height"]) == (1440, 900)
        else:
            assert (cell["width"], cell["height"]) == (375, 812)
        assert cell["file"] == ("macro.html" if cell["page"] == "us" else "china.html")
    reduced = [cell for cell in cells if cell["motion"] == "reduce"]
    assert len(reduced) == 2
    assert {(c["page"], c["lang"], c["theme"], c["viewport"], c["javascript"]) for c in reduced} == {
        ("us", "en", "dark", "desktop", True),
        ("cn", "en", "dark", "desktop", True),
    }
    nojs = [cell for cell in cells if not cell["javascript"]]
    assert len(nojs) == 2
    assert {(c["page"], c["lang"], c["theme"], c["viewport"], c["motion"]) for c in nojs} == {
        ("us", "en", "dark", "desktop", "no-preference"),
        ("cn", "en", "dark", "desktop", "no-preference"),
    }


def test_tab_escape_fails():
    result = matrix.evaluate_cell(_js_cell(), _measured(tab_escapes=1))
    assert result["passed"] is False
    assert result["tab_escapes"] == 1
    assert "tab_escapes" in result["failures"]
    assert result["checks"]["dialog_visible"] is True
    assert result["checks"]["forecast_heading_ok"] is True
    record = matrix.cell_record(_js_cell(), result)
    receipt = matrix.assemble_receipt("http://127.0.0.1", "2026-01-01T00:00:00Z", "chromium 0", [record])
    assert receipt["pass"] is False
    assert receipt["schema"] == "risk_radar_pullback_matrix.v1"


def test_zh_english_heading_fails():
    result = matrix.evaluate_cell(
        _js_cell(lang="zh"),
        _measured(forecast_heading_text="Estimate unavailable"),
    )
    assert result["passed"] is False
    assert result["checks"]["forecast_heading_text"] == "Estimate unavailable"
    assert result["checks"]["forecast_heading_ok"] is False
    assert "forecast_heading_ok" in result["failures"]


def test_digit_in_forecast_rows_fails():
    result = matrix.evaluate_cell(
        _js_cell(),
        _measured(forecast_row_text="Further downside from today 4%"),
    )
    assert result["passed"] is False
    assert result["checks"]["forecast_rows_have_no_digit"] is False
    assert "forecast_rows_have_no_digit" in result["failures"]


def test_js_off_without_receipt_fails():
    cell = _js_cell(javascript=False)
    missing = matrix.evaluate_cell(cell, _measured(dialog_visible=False, time_datetime="", pbx_present=True))
    assert missing["passed"] is False
    assert missing["checks"]["time_receipt_present"] is False
    assert missing["checks"]["dialog_without_js"] == "cannot open"
    assert "time_receipt_present" in missing["failures"]
    absent = matrix.evaluate_cell(cell, _measured(dialog_visible=False, pbx_present=False, time_datetime=""))
    assert absent["passed"] is False
    assert "pbx_present" in absent["failures"]
    html = (
        '<section class="rrp pbx" data-pb-phase="underway">'
        '<time datetime="">—</time></section>'
        '<div class="mx5-dlg" id="dlg-risk"></div>'
    )
    parsed = matrix.evaluate_cell(cell, matrix._static_measurement(html, "us"))
    assert parsed["passed"] is False
    assert parsed["checks"]["pbx_present"] is True
    assert parsed["checks"]["time_receipt_present"] is False


def test_all_good_passes():
    en = matrix.evaluate_cell(_js_cell(), _measured())
    assert en["passed"] is True
    assert en["checks"]["no_page_overflow"] is True
    assert en["checks"]["no_dialog_overflow"] is True
    assert en["phase"] == "underway"
    wide = matrix.evaluate_cell(_js_cell(), _measured(page_scroll_width=1442, page_inner_width=1440))
    assert wide["passed"] is False
    assert wide["checks"]["no_page_overflow"] is False
    zh = matrix.evaluate_cell(
        _js_cell(lang="zh", page="cn", file="china.html"),
        _measured(forecast_heading_text="估计暂不可用"),
    )
    assert zh["passed"] is True
    assert zh["checks"]["forecast_heading_ok"] is True
    nojs_cell = _js_cell(javascript=False)
    nojs = matrix.evaluate_cell(
        nojs_cell,
        _measured(dialog_visible=False, pbx_present=True, time_datetime="2026-01-02T00:00:00Z"),
    )
    assert nojs["passed"] is True
    assert nojs["checks"]["dialog_without_js"] == "cannot open"
    opened = matrix.evaluate_cell(
        nojs_cell,
        _measured(dialog_visible=True, pbx_present=True, time_datetime="2026-01-02T00:00:00Z"),
    )
    assert opened["passed"] is True
    assert opened["checks"]["dialog_without_js"] == "opened"
    html = (
        '<div class="cnx-dlg" id="cnx-dlg-risk"><section class="rrp pbx" data-pb-phase="underway">'
        '<time datetime="2026-01-02T00:00:00Z">2026-01-02</time></section></div>'
    )
    from_html = matrix.evaluate_cell(_js_cell(page="cn", javascript=False), matrix._static_measurement(html, "cn"))
    assert from_html["passed"] is True
    assert from_html["phase"] == "underway"
    assert from_html["checks"]["dialog_without_js"] == "cannot open"
    receipt = matrix.assemble_receipt(
        "https://example.test/site",
        "2026-01-01T00:00:00Z",
        "chromium 0",
        [
            matrix.cell_record(_js_cell(), en, applied_via="localStorage.theme,localStorage.lang", opener="#mx5BtnRisk"),
            matrix.cell_record(_js_cell(lang="zh"), zh),
            matrix.cell_record(nojs_cell, nojs),
        ],
    )
    assert receipt["pass"] is True
    assert receipt["base"] == "https://example.test/site"
    assert receipt["browser_version"] == "chromium 0"
    assert [cell["pass"] for cell in receipt["cells"]] == [True, True, True]


def test_page_target_joins_base():
    assert matrix.page_target("https://example.test/site/", "macro.html") == "https://example.test/site/macro.html"
    assert matrix.page_target("http://127.0.0.1:8765", "china.html") == "http://127.0.0.1:8765/china.html"


def test_local_base_is_file_url(tmp_path):
    page = tmp_path / "macro.html"
    page.write_text("<html></html>", encoding="utf-8")
    url = matrix.page_target(str(tmp_path), "macro.html")
    assert url.startswith("file:")
    assert url.endswith("/macro.html")
    with pytest.raises(matrix.SetupError):
        matrix.page_target(str(tmp_path), "missing.html")
    with pytest.raises(matrix.SetupError):
        matrix.page_target(str(tmp_path / "missing-dir"), "macro.html")


def test_browser_library_import_is_inside_the_driver():
    text = Path(matrix.__file__).read_text(encoding="utf-8")
    head, marker, tail = text.partition("def run_matrix")
    assert marker == "def run_matrix"
    assert "playwright" not in head
    assert "from playwright.sync_api import sync_playwright" in tail
