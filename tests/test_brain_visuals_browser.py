"""Real Chromium checks of native illustration rendering; illustrative fixtures only."""
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from engine.neuralweb.brain_visuals import compile_visual

ROOT = Path(__file__).resolve().parents[1]


def sample(template="bar", identity="sample", **values):
    args = {"version": 1, "template": template, "title": "Illustrative comparison / 示例比较",
            "basis": "illustrative", "columns": ["Period", "Alpha", "Beta"],
            "rows": [["First", 2, 3], ["Missing", None, -2], ["Third", -3, 0]], "unit": "bp", **values}
    result = compile_visual(args, [], identity)
    assert "visual" in result, result
    return result


@pytest.fixture
def page():
    script = ROOT / "templates/mm_brain_visuals.js"
    assert script.exists(), "native renderer is missing"
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 390, "height": 844}, reduced_motion="reduce")
        page.set_content('<html data-theme="dark" data-lang="en"><head></head><body style="margin:16px"><div id="mmb-root"><div class="mmb-bub"><div class="mmb-charts" id="host"></div></div></div></body></html>')
        page.add_style_tag(content='#mmb-root{--mmb-info:#5b9bf0;--mmb-text:#e6eaf0;--mmb-muted:#a2adba;--mmb-ink:white;--mmb-panel:#181b21;--mmb-hi:white;--mmb-line:#39404b;--font-ui:system-ui;--font-mono:monospace}body{background:#101215;color:#e6eaf0}html[data-theme=light] #mmb-root{--mmb-text:#17212e;--mmb-muted:#525d6b;--mmb-ink:#17212e;--mmb-panel:white;--mmb-hi:#101215;--mmb-line:#d6dce3}html[data-theme=light] body{background:#f3f5f8;color:#17212e}')
        page.add_style_tag(path=str(ROOT / "templates/mm_brain_visuals.css"))
        page.add_script_tag(path=str(script))
        yield page
        browser.close()


def mount(page, wire):
    return page.evaluate('(wire)=>MMBrainVisuals.mount(document.querySelector("#host"),wire)', wire)


def test_renderer_asset_exists():
    assert (ROOT / "templates/mm_brain_visuals.js").exists(), "native renderer is missing"


def test_null_segments_and_native_data_disclosure(page):
    assert mount(page, sample("line"))
    assert page.locator('figure[data-template=line]').count() == 1
    page.locator('summary').first.click()
    assert page.locator('table').inner_text().count("—") == 1
    assert page.locator('svg').get_attribute('preserveAspectRatio') != 'none'
    assert page.locator('path[data-series="0"]').count() == 2  # null creates two separate segments
    assert not page.locator('svg').evaluate('(e)=>/NaN|Infinity/.test(e.outerHTML)')


def test_repeated_delivery_and_malformed_history_fail_closed(page):
    wire = sample()
    assert mount(page, wire)
    assert mount(page, wire)
    assert page.locator('figure').count() == 1
    bad = {**wire, "visual_id": "b" * 24, "visual": {**wire["visual"], "rows": [["A", True, 2]]}}
    assert not mount(page, bad)
    bad = {**wire, "visual_id": "c" * 24, "visual": {**wire["visual"], "title": '<img src=x onerror=alert(1)>'}}
    assert not mount(page, bad)
    assert page.locator('img').count() == 0
    page.evaluate('MMBrainVisuals.clear(document.querySelector("#host"))')
    assert page.locator('figure').count() == 0


def test_csv_escapes_formulas_and_preserves_exact_null_numeric_values(page):
    wire = sample("table", columns=["Label", "Value"], rows=[["=HYPERLINK(1)", 2.123456789012345], ["+SUM(1)", None], ["@cmd", -2], ["\t=1+1", 0]])
    assert mount(page, wire)
    csv = page.evaluate('(s)=>MMBrainVisuals.csv(s)', wire["visual"])
    assert '"\'=HYPERLINK(1)"' in csv
    assert '"\'+SUM(1)"' in csv
    assert '"\'@cmd"' in csv
    assert '"\'\t=1+1"' in csv
    assert '2.123456789012345' in csv
    assert '"-2"' in csv


@pytest.mark.parametrize("width", [390, 820, 1440])
@pytest.mark.parametrize("theme,lang", [("dark", "en"), ("light", "en"), ("dark", "zh"), ("light", "zh")])
def test_all_templates_responsive_theme_language(page, width, theme, lang):
    page.set_viewport_size({"width": width, "height": 900})
    page.evaluate('([theme,lang])=>{document.documentElement.dataset.theme=theme;document.documentElement.dataset.lang=lang}', [theme, lang])
    variants = [sample(k, k) for k in ("bar", "line", "area", "table", "metrics")]
    variants += [sample("scatter", "scatter", columns=["X", "Y"], rows=[[1, 2], [2, None], [3, -1]])]
    variants += [sample("donut", "donut", columns=["Category", "Value"], rows=[["A", 3], ["B", 2], ["C", None]])]
    variants += [sample(k, k, columns=["Subject", "Description", "Detail"], rows=[["US", "Watch / 观察", "Long explanation " * 15], ["China", "Wait / 等待", "Source update pending"]]) for k in ("status", "scenarios", "timeline", "flow")]
    for wire in variants:
        assert mount(page, wire), wire
    page.wait_for_timeout(100)
    assert page.locator('figure').count() == 11
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    assert not page.locator('svg').evaluate_all('(items)=>items.some(e=>/NaN|Infinity/.test(e.outerHTML))')
    text = page.locator('figure').first.inner_text()
    assert ("示意" if lang == "zh" else "Illustrative") in text
    # Numeric tables and controls remain operable without a mouse.
    page.locator('summary').first.focus()
    page.keyboard.press('Enter')
    assert page.locator('details').first.get_attribute('open') is not None


def test_browser_precision_and_zero_baseline(page):
    assert mount(page, sample("bar", rows=[["Low", -0.00012, 0], ["High", 0.00014, 0]]))
    assert page.locator('line[data-zero]').count() == 1
    labels = page.locator('text[data-tick]').all_text_contents()
    assert len(labels) == len(set(labels))
    assert not page.locator('rect[data-bar]').evaluate_all('(items)=>items.some(e=>Number(e.getAttribute("height"))<0)')


@pytest.mark.parametrize("later_series_style", [False, True])
def test_donut_is_a_ring_and_missing_shares_are_disclosed(page, later_series_style):
    if later_series_style:
        # Series color rules must not fill a ring when styles are composed later.
        page.add_style_tag(content="#mmb-root .mmb-v-series-0{fill:currentColor}")
    assert mount(page, sample('donut', columns=['Category', 'Value'], rows=[['A', 3], ['B', 2], ['Missing', None]]))
    # ResizeObserver can replace the SVG between a locator's query and evaluation.
    # Select connected nodes and read their styles in one synchronous observation.
    rings = page.wait_for_function(
        """() => {
            const items = Array.from(document.querySelectorAll('svg circle'));
            if (!items.length || items.some(e => !e.isConnected)) return false;
            return items.map(e => ({
                classes: e.getAttribute('class'),
                attributeFill: e.getAttribute('fill'),
                computedFill: getComputedStyle(e).fill
            }));
        }"""
    ).json_value()
    assert len(rings) == 2, rings
    assert all(ring["computedFill"] == "none" for ring in rings), rings
    assert 'known values only' in page.locator('figure').inner_text()


def test_bars_too_small_to_see_have_visible_disclosure(page):
    assert mount(page, sample('bar', columns=['Category', 'Value'], rows=[['Small', 1], ['Large', 1e9]]))
    assert 'too small to see' in page.locator('figure').inner_text()


@pytest.mark.parametrize("later_series_style", [False, True])
def test_initial_resize_delivery_keeps_rings_connected_and_real_resize_redraws(page, later_series_style):
    if later_series_style:
        page.add_style_tag(content="#mmb-root .mmb-v-series-0{fill:currentColor}")
    wire = sample('donut', columns=['Category', 'Value'], rows=[['A', 3], ['B', 2], ['Missing', None]])
    initial = page.evaluate('''(wire) => {
        MMBrainVisuals.mount(document.querySelector('#host'), wire);
        const original = document.querySelector('figure svg');
        const rings = Array.from(original.querySelectorAll('circle'));
        // Two rendering frames include the observer's initial delivery. A no-op
        // width notification must not detach nodes already handed to a reader.
        return new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(() => resolve({
            sameSvg: document.querySelector('figure svg') === original,
            rings: rings.map(e => ({connected: e.isConnected, fill: getComputedStyle(e).fill}))
        }))));
    }''', wire)
    assert initial == {'sameSvg': True, 'rings': [{'connected': True, 'fill': 'none'}] * 2}
    page.set_viewport_size({'width': 820, 'height': 844})
    page.wait_for_function('''() => {
        const plot = document.querySelector('.mmb-v-plot'), svg = plot.querySelector('svg');
        return svg && Number(svg.getAttribute('width')) === Math.floor(plot.getBoundingClientRect().width);
    }''')
    assert page.locator('svg').get_attribute('width') == '788'
    assert page.locator('svg circle').evaluate_all('(items) => items.every(e => e.isConnected && getComputedStyle(e).fill === "none")')
    assert 'known values only' in page.locator('figure').inner_text()


def test_csv_download_keeps_utf8_bom_and_escaped_values(page, tmp_path):
    assert mount(page, sample('table', columns=['标签', 'Value'], rows=[['=1+1', -2.25], ['已知', None]]))
    page.locator('summary').click()
    with page.expect_download() as info:
        page.locator('.mmb-v-export').click()
    output = tmp_path / 'visual.csv'
    info.value.save_as(output)
    data = output.read_bytes()
    assert data.startswith(b'\xef\xbb\xbf')
    assert '"\'=1+1","-2.25"' in data.decode('utf-8-sig')


def test_asymmetric_diverging_bars_label_the_actual_zero_baseline(page):
    assert mount(page, sample('bar', columns=['Maturity','Change'], rows=[['Short',1.1],['Long',-3.8]]))
    assert '0' in page.locator('text[data-tick]').all_text_contents()


@pytest.mark.parametrize('template', ['status','scenarios','timeline','flow','table','metrics'])
def test_source_bound_text_visuals_render_without_becoming_fictional(page, template):
    rows = [['2026-10-15','CPI release']] if template not in ('table','metrics') else [['Price','$1,234']]
    bindings = [{'row':0,'column':c,'tool':'fixture_read','call_id':'source1','pointer':f'/rows/0/{c}'} for c in (range(2) if template not in ('table','metrics') else [1])]
    wire = compile_visual({'version':1,'template':template,'title':'Synthetic source fixture, not market data','basis':'source','columns':['Label','Value'],'rows':rows,'bindings':bindings}, [('fixture_read',{'rows':rows},'source1')], 'source-fixture')
    assert 'visual' in wire
    assert mount(page, wire)
    assert 'Data values match retrieved output' in page.locator('.mmb-v-basis').inner_text()
    assert 'Illustrative' not in page.locator('.mmb-v-basis').inner_text()
    assert rows[0][1] in page.locator('figure').inner_text()
    broken = {**wire, 'visual_id':'d'*24, 'visual':{**wire['visual'],'provenance':{**wire['visual']['provenance'],'text_cells_matched':0}}}
    assert not mount(page, broken)


def test_legacy_numeric_only_visual_snapshot_still_renders(page):
    wire = sample()
    wire['visual']['provenance'].pop('text_cells_matched', None)
    assert mount(page, wire)
    assert page.locator('figure').count() == 1


def candle_sample(**overrides):
    return sample(
        "candlestick",
        columns=["Candle", "Open", "High", "Low", "Close"],
        rows=[
            ["1", 110, 114, 105, 106],
            ["2", 106, 109, 101, 102],
            ["Pivot", 102, 107, 101, 106],
            ["Breakout", 106, 111, 104, 110],
        ],
        subtitle="Fictional 30-minute pivot", **overrides,
    )


def test_candle_pivot_entry_stop_and_breakout_are_real_svg_geometry(page):
    assert mount(page, candle_sample())
    assert page.locator('figure[data-template=candlestick]').count() == 1
    assert page.locator('rect[data-candle-index]').count() == 4
    assert page.locator('rect[data-pivot-index="2"]').count() == 1
    assert page.locator('circle[data-breakout-index="3"]').count() == 1
    assert page.locator('line[data-level="entry"]').count() == 1
    assert page.locator('line[data-level="stop"]').count() == 1
    assert 'Illustrative' in page.locator('.mmb-v-basis').inner_text()
    assert '106' in page.locator('.mmb-v-candle-note').inner_text() or '107' in page.locator('.mmb-v-candle-note').inner_text()
    page.locator('details summary').first.click()
    assert 'Pivot' in page.locator('table').first.inner_text()
    assert page.locator('table tbody tr').count() == 4
    assert page.locator('svg[role="img"] desc').count() == 1
    for viewport in [390, 820, 1440]:
        page.set_viewport_size({"width": viewport, "height": 844})
        page.wait_for_timeout(30)
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), viewport
    page.evaluate('document.documentElement.setAttribute("data-theme","light");document.documentElement.setAttribute("data-lang","zh")')
    assert '转折蜡烛' in page.locator('.mmb-v-candle-note').inner_text()


def test_candle_without_two_opposite_prior_candles_has_no_false_breakout(page):
    wire=candle_sample(rows=[
        ["1", 100, 103, 99, 102],
        ["2", 102, 105, 101, 104],
        ["3", 104, 108, 103, 107],
        ["4", 107, 110, 105, 108],
    ])
    assert mount(page,wire)
    assert page.locator('rect[data-pivot-index]').count() == 0
    assert page.locator('line[data-level]').count() == 0
    assert page.locator('circle[data-breakout-index]').count() == 0
    assert 'No two-candle reversal pivot' in page.locator('.mmb-v-candle-note').inner_text()


def test_browser_validator_rejects_chart_history_ohlc_tampering(page):
    wire=candle_sample()
    wire["visual"]["rows"][0][2] = 90
    assert not mount(page,wire)
    assert page.locator('.mmb-v').count() == 0
