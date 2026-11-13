"""Pure checks for the served-route pullback matrix. No browser."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.verify_risk_radar_pullback_matrix as matrix

EM = "\u2014"
EN_BLOCK = "\n".join((
    "FURTHER DOWNSIDE",
    "Estimate unavailable",
    "We can measure the decline that has already happened. A reliable range for the next low is not yet available.",
    "Further decline from the latest close",
    EM,
    "Total pullback depth",
    EM,
    "Why no estimate?",
))
ZH_BLOCK = "\n".join((
    "进一步跌幅",
    "估计暂不可用",
    "可以测量已发生的跌幅，但下一低点的可靠区间尚不可用。",
    "自最新收盘价起的进一步跌幅",
    EM,
    "回撤总深度",
    EM,
    "为什么暂无估计？",
))
EN_DETAIL = (
    "Publishing a range takes historical tests for this market, benchmark, price measurement "
    "and time window. Risk level and existing pullback probabilities are not a forecast of "
    "the remaining drop."
)
FORECAST_SNIPPET = (
    '<div class="rrp-forecast" data-forecast-status="unavailable">'
    '<h3><span class="l-en">Estimate unavailable</span>'
    '<span class="l-zh">估计暂不可用</span></h3>'
    '<p><span class="l-en">We can measure the decline that has already happened. '
    'A reliable range for the next low is not yet available.</span>'
    '<span class="l-zh">可以测量已发生的跌幅，但下一低点的可靠区间尚不可用。</span></p>'
    '<div class="rrp-forecast-row"><span class="l-en">Further decline from the latest close</span>'
    '<span class="l-zh">自最新收盘价起的进一步跌幅</span>'
    f'<strong>{EM}</strong></div>'
    '<div class="rrp-forecast-row"><span class="l-en">Total pullback depth</span>'
    '<span class="l-zh">回撤总深度</span>'
    f'<strong>{EM}</strong></div>'
    '</div>'
)


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
        "forecast_row_text": f"Further decline from the latest close {EM}\nTotal pullback depth {EM}",
        "forecast_row_count": 2,
        "forecast_values": [EM, EM],
        "forecast_block_text": EN_BLOCK,
        "data_lang": "en",
        "data_theme": "dark",
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


def test_details_cell_option_covers_expanded_and_collapsed():
    """The driver must be able to measure <details> open, not only the default closed state.

    A forecast sentence inside the closed disclosure is absent from JavaScript
    innerText, so a collapsed-only matrix would pass that page.
    """
    pages = matrix.parse_pages("us=macro.html,cn=china.html")
    collapsed = matrix.enumerate_cells(pages)
    assert len(collapsed) == 20
    assert all(cell.get("details", "collapsed") == "collapsed" for cell in collapsed)
    expanded = matrix.enumerate_cells(pages, details="expanded")
    assert len(expanded) == 20
    assert {cell["details"] for cell in expanded} == {"expanded"}
    both = matrix.enumerate_cells(pages, details="both")
    assert len(both) == 40
    assert {cell["details"] for cell in both} == {"collapsed", "expanded"}
    text = Path(matrix.__file__).read_text(encoding="utf-8")
    drive = text.split("def _drive_cell", 1)[1].split("\ndef run_matrix", 1)[0]
    assert "section.pbx details > summary" in drive
    assert 'cell.get("details") == "expanded"' in drive
    expand = text.split("def _expand_details", 1)[1].split("\ndef _count_tab_escapes", 1)[0]
    # A closed dialog hides the summary. Playwright's click then reports
    # "not visible" even with force, which is the JavaScript-off cell.
    # The summary's own click still opens the disclosure.
    assert "el.click()" in expand


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


def test_worded_forecast_line_fails():
    """G1: a digit-free sentence in the forecast block is still an estimate."""
    result = matrix.evaluate_cell(
        _js_cell(),
        _measured(
            forecast_row_count=2,
            forecast_row_text="a deep further drop is likely",
            forecast_values=[EM, EM],
            forecast_block_text="Estimate unavailable\na deep further drop is likely\nsevere",
        ),
    )
    assert result["passed"] is False
    assert "forecast_block_text_ok" in result["failures"]


def test_empty_forecast_values_fail():
    """G1: two rows and an empty row string used to pass the digit check."""
    measured = _measured(forecast_row_count=2, forecast_row_text="")
    measured.pop("forecast_values")
    missing = matrix.evaluate_cell(_js_cell(), measured)
    assert missing["passed"] is False
    assert "forecast_values_ok" in missing["failures"]
    blank = matrix.evaluate_cell(
        _js_cell(),
        _measured(forecast_row_count=2, forecast_row_text="", forecast_values=["", ""]),
    )
    assert blank["passed"] is False
    assert "forecast_values_ok" in blank["failures"]


def test_expanded_forecast_copy_passes_and_collapsed_copy_passes():
    collapsed = matrix.evaluate_cell(_js_cell(), _measured())
    assert collapsed["passed"] is True
    expanded = matrix.evaluate_cell(
        _js_cell(),
        _measured(forecast_block_text=EN_BLOCK + "\n" + EN_DETAIL),
    )
    assert expanded["passed"] is True
    assert expanded["checks"]["forecast_block_text_ok"] is True


def test_innertext_joined_allow_phrases_pass_and_a_new_sentence_fails():
    """innerText joins inline spans onto one line. That line is still the allow-list.

    JavaScript-off Chromium also keeps display:none text in innerText, so an
    English phrase and its Chinese twin land on the same line, and the em dash
    sticks to the label ('Further decline from the latest close —').
    """
    en = (
        "FURTHER DOWNSIDE",
        "Estimate unavailable",
        "We can measure the decline that has already happened. A reliable range for the next low is not yet available.",
        "Further decline from the latest close",
        "Total pullback depth",
        "Why no estimate?",
        EN_DETAIL,
    )
    zh = (
        "进一步跌幅",
        "估计暂不可用",
        "可以测量已发生的跌幅，但下一低点的可靠区间尚不可用。",
        "自最新收盘价起的进一步跌幅",
        "回撤总深度",
        "为什么暂无估计？",
        "发布区间需要针对本市场、基准、价格衡量方式和时间范围的历史检验。风险水平与现有回撤概率并非对剩余跌幅的预测。",
    )
    joined = "\n".join((
        en[0] + zh[0],
        en[1] + zh[1],
        en[2] + zh[2],
        en[3] + zh[3] + EM,
        en[4] + zh[4] + EM,
        en[5] + zh[5],
        en[6] + zh[6],
    ))
    cell = _js_cell(javascript=False)
    ok = matrix.evaluate_cell(
        cell,
        _measured(
            dialog_visible=False,
            pbx_present=True,
            time_datetime="2026-01-02T00:00:00Z",
            forecast_values=[EM, EM],
            forecast_block_text=joined,
        ),
    )
    assert ok["passed"] is True, ok["failures"]
    spaced = matrix.evaluate_cell(
        _js_cell(),
        _measured(forecast_block_text="\n".join((
            en[0], en[1], en[2], en[3] + " " + EM, en[4] + " " + EM, en[5],
        ))),
    )
    assert spaced["passed"] is True, spaced["failures"]
    assert spaced["checks"]["forecast_block_text_ok"] is True
    planted = matrix.evaluate_cell(
        cell,
        _measured(
            dialog_visible=False,
            pbx_present=True,
            time_datetime="2026-01-02T00:00:00Z",
            forecast_values=[EM, EM],
            forecast_block_text=joined + "\nA deep further drop is likely",
        ),
    )
    assert planted["passed"] is False
    assert "forecast_block_text_ok" in planted["failures"]
    percent = matrix.evaluate_cell(
        _js_cell(),
        _measured(forecast_block_text=en[3] + " 4.2%"),
    )
    assert percent["passed"] is False
    assert "forecast_block_text_ok" in percent["failures"]


def test_missing_lang_and_theme_fail():
    """G2: a measurement that omits data_lang / data_theme fails closed."""
    measured = _measured()
    measured.pop("data_lang")
    measured.pop("data_theme")
    result = matrix.evaluate_cell(_js_cell(), measured)
    assert result["passed"] is False
    assert "lang_applied" in result["failures"]
    assert "theme_applied" in result["failures"]


def test_js_off_numeric_forecast_fails():
    """G3: JS-off used to ignore forecast row text such as a percent estimate."""
    cell = _js_cell(javascript=False)
    result = matrix.evaluate_cell(
        cell,
        _measured(
            dialog_visible=False,
            pbx_present=True,
            time_datetime="2026-01-02T00:00:00Z",
            forecast_row_text="12% further downside",
            forecast_block_text="12% further downside",
            forecast_values=["12%", EM],
        ),
    )
    assert result["passed"] is False
    assert "forecast_values_ok" in result["failures"]
    assert "forecast_block_text_ok" in result["failures"]
    both_languages = matrix.evaluate_cell(
        cell,
        _measured(
            dialog_visible=False,
            pbx_present=True,
            time_datetime="2026-01-02T00:00:00Z",
            forecast_block_text=EN_BLOCK + "\n" + ZH_BLOCK,
            forecast_values=[EM, EM],
        ),
    )
    assert both_languages["passed"] is True


def test_measurer_returns_forecast_values_and_block_text():
    source = matrix._MEASURE_JS
    assert "forecast_values" in source
    assert "forecast_block_text" in source
    assert ".rrp-forecast" in source
    assert "querySelector('strong')" in source


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
        _measured(
            forecast_heading_text="估计暂不可用",
            forecast_block_text=ZH_BLOCK,
            data_lang="zh",
        ),
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
        '<time datetime="2026-01-02T00:00:00Z">2026-01-02</time>'
        + FORECAST_SNIPPET
        + '</section></div>'
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


def test_require_active_rejects_a_phase_outside_the_active_set():
    """G8: the flag is off by default, and on it demands an active phase."""
    quiet = matrix.evaluate_cell(_js_cell(), _measured(phase="repaired"))
    assert quiet["passed"] is True
    assert "phase_active" not in quiet["checks"]
    blocked = matrix.evaluate_cell(_js_cell(), _measured(phase="repaired"), require_active=True)
    assert blocked["passed"] is False
    assert "phase_active" in blocked["failures"]
    for phase in ("underway", "stabilizing", "recovering"):
        ok = matrix.evaluate_cell(_js_cell(), _measured(phase=phase), require_active=True)
        assert ok["passed"] is True, phase
        assert ok["checks"]["phase_active"] is True


def test_js_off_require_active_uses_the_server_phase():
    cell = _js_cell(javascript=False, page="cn", file="china.html")
    base = dict(
        dialog_visible=False,
        pbx_present=True,
        time_datetime="2026-01-02T00:00:00Z",
        forecast_values=[EM, EM],
        forecast_block_text=EN_BLOCK + "\n" + ZH_BLOCK,
    )
    assert matrix.evaluate_cell(cell, _measured(**base, phase="monitoring"))["passed"] is True
    denied = matrix.evaluate_cell(cell, _measured(**base, phase="monitoring"), require_active=True)
    assert denied["passed"] is False
    assert "phase_active" in denied["failures"]
    html = (
        '<div class="cnx-dlg" id="cnx-dlg-risk"><section class="rrp pbx" data-pb-phase="unavailable">'
        '<time datetime="2026-01-02T00:00:00Z">2026-01-02</time>'
        + FORECAST_SNIPPET
        + "</section></div>"
    )
    from_dom = matrix.evaluate_cell(cell, matrix._static_measurement(html, "cn"), require_active=True)
    assert from_dom["phase"] == "unavailable"
    assert from_dom["passed"] is False
    assert "phase_active" in from_dom["failures"]


def test_cli_require_active_reaches_the_driver(monkeypatch, tmp_path):
    seen = {}

    def fake_run(base, pages, out_dir, chrome=None, require_active=False, details="collapsed"):
        seen["require_active"] = require_active
        seen["details"] = details
        return matrix.assemble_receipt(base, "2026-01-01T00:00:00Z", "chromium 0", [{"pass": True}])

    monkeypatch.setattr(matrix, "run_matrix", fake_run)
    argv = ["--base", "https://example.test", "--pages", "us=macro.html", "--out", str(tmp_path)]
    assert matrix.main(argv) == 0
    assert seen["require_active"] is False
    assert matrix.main(argv + ["--require-active"]) == 0
    assert seen["require_active"] is True


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


class _BrowserType:
    name = "chromium"


class _Context:
    def route(self, *_args, **_kwargs):
        return None

    def add_init_script(self, *_args, **_kwargs):
        return None

    def new_page(self):
        return object()

    def close(self):
        return None


class _Browser:
    version = "120.0"
    browser_type = _BrowserType()

    def new_context(self, **_kwargs):
        return _Context()

    def close(self):
        return None


class _Chromium:
    def __init__(self, fail=()):
        self.fail = set(fail)
        self.calls = []

    def launch(self, **kwargs):
        self.calls.append(dict(kwargs))
        if kwargs.get("channel") == "chrome" and "channel" in self.fail:
            raise RuntimeError("Chromium distribution 'chrome' is not found")
        if "executable_path" in kwargs and "path" in self.fail:
            raise RuntimeError("bad path")
        if "channel" not in kwargs and "executable_path" not in kwargs and "bundled" in self.fail:
            raise RuntimeError("no bundled browser")
        return _Browser()


class _Manager:
    def __init__(self, chromium):
        self.chromium = chromium

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


def test_launch_uses_system_chrome_when_it_starts():
    chromium = _Chromium()
    _browser, source = matrix._launch_browser(chromium, None)
    assert source == "system-chrome"
    assert chromium.calls == [{"headless": True, "channel": "chrome"}]


def test_launch_falls_back_to_bundled_chromium():
    """G9: a missing system Chrome channel launches the bundled browser."""
    chromium = _Chromium(fail={"channel"})
    _browser, source = matrix._launch_browser(chromium, None)
    assert source == "bundled-chromium"
    assert chromium.calls[0] == {"headless": True, "channel": "chrome"}
    assert chromium.calls[1] == {"headless": True}


def test_launch_uses_an_explicit_path_without_fallback():
    chromium = _Chromium()
    _browser, source = matrix._launch_browser(chromium, "/tmp/chrome-bin")
    assert source == "explicit-path"
    assert chromium.calls == [{"headless": True, "executable_path": "/tmp/chrome-bin"}]
    missing = _Chromium(fail={"path"})
    with pytest.raises(matrix.SetupError):
        matrix._launch_browser(missing, "/tmp/missing-chrome")
    assert len(missing.calls) == 1


def test_launch_reports_setup_error_when_nothing_starts():
    chromium = _Chromium(fail={"channel", "bundled"})
    with pytest.raises(matrix.SetupError, match="could not launch the browser"):
        matrix._launch_browser(chromium, None)


def test_run_matrix_records_bundled_chromium_when_chrome_is_missing(monkeypatch, tmp_path):
    chromium = _Chromium(fail={"channel"})
    monkeypatch.setattr(matrix, "_open_playwright", lambda: _Manager(chromium))
    monkeypatch.setattr(
        matrix,
        "_drive_cell",
        lambda page, base, cell, out_dir, require_active=False: {"pass": True, "page": cell["page"]},
    )
    receipt = matrix.run_matrix("https://example.test", [("us", "macro.html")], tmp_path)
    assert receipt["browser_source"] == "bundled-chromium"
    assert receipt["browser_version"] == "chromium 120.0"
    assert receipt["pass"] is True
    assert chromium.calls[0]["channel"] == "chrome"
    assert "channel" not in chromium.calls[1]
    assert "executable_path" not in chromium.calls[1]


def test_browser_library_import_is_inside_the_driver():
    text = Path(matrix.__file__).read_text(encoding="utf-8")
    head, marker, tail = text.partition("def run_matrix")
    assert marker == "def run_matrix"
    assert "playwright" not in head
    assert "from playwright.sync_api import sync_playwright" in tail
