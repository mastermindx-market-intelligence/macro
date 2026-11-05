"""Real legacy technical-chart controls with synthetic, explicitly local OHLC data.

Exercises source intake, displayed dates, cache recovery and turn cleanup through
the actual widget. No model, live price, ChartBus or production claim is made.
"""
from datetime import date, timedelta
from playwright.sync_api import expect
from tests.test_brain_history_widget import page  # noqa: F401
from tests.test_brain_visuals_widget import stream


def bars(start=date(2024, 1, 1), end=date(2026, 10, 21)):
    out = []
    day = start
    while day <= end:
        if day.weekday() < 5:
            price = 100 + len(out) / 10
            out.append([day.isoformat(), price, price + 2, price - 1, price + 1, 1000])
        day += timedelta(days=1)
    return out


def source(page, rows, mode="ok"):
    page.evaluate("""([rows,mode])=>{
      window.__barRows=rows;window.__barMode=mode;window.__barCalls=0;
      const old=window.fetch;
      window.fetch=(url,options={})=>{
        if(!url.endsWith('/TEST.json'))return old(url,options);
        window.__barCalls++;
        if(window.__barMode==='fail')return Promise.reject(new Error('temporary outage'));
        if(window.__barMode==='hold')return new Promise(resolve=>{window.__resolveBars=()=>resolve({
          ok:true,json:()=>Promise.resolve({bars:window.__barRows})});});
        return Promise.resolve({ok:true,json:()=>Promise.resolve({bars:window.__barRows})});
      };
    }""", [rows, mode])


def chart(page, timeframe="DAILY", count=1, hold=False):
    events = [{"type": "delta", "text": "Synthetic technical-chart fixture."}]
    events.extend({"type": "chart", "ticker": "TEST", "timeframe": timeframe} for _ in range(count))
    if not hold:
        events.append({"type": "done", "charts": [], "citations": []})
    stream(page, events, hold=hold)


def test_ranges_use_dates_not_pixels_and_controls_make_no_requests(page):
    source(page, bars())
    chart(page)
    svg = page.locator(".mmb-cx-body > svg")
    expect(svg).to_have_attribute("data-start", "2025-10-21")
    expected = {"1M": "2026-09-21", "3M": "2026-07-21", "6M": "2026-04-21",
                "YTD": "2026-01-01", "1Y": "2025-10-21", "MAX": "2024-01-01"}
    page.evaluate("""()=>{
      window.__controlRequests=[];
      const old=window.fetch;
      window.fetch=(...args)=>{window.__controlRequests.push(String(args[0]));return old(...args);};
    }""")
    for label, start in expected.items():
        button = page.locator(".mmb-cx-ranges").get_by_role("button", name=label, exact=True)
        button.click()
        expect(svg).to_have_attribute("data-start", start)
        expect(svg).to_have_attribute("data-end", "2026-10-21")
        expect(button).to_have_attribute("aria-pressed", "true")
    count = svg.get_attribute("data-bars")
    page.set_viewport_size({"width": 390, "height": 844})
    page.wait_for_timeout(250)
    expect(svg).to_have_attribute("data-start", "2024-01-01")
    expect(svg).to_have_attribute("data-bars", count)
    expect(page.locator(".mmb-cx-src")).to_contain_text("Close-price overview")
    for button in page.locator(".mmb-cx-ranges button").all():
        box = button.bounding_box()
        assert box and round(box["width"], 4) >= 44 and round(box["height"], 4) >= 44
    assert page.evaluate("window.__controlRequests") == []
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
    page.locator(".mmb-cx-ranges").get_by_role("button", name="1M", exact=True).click()
    # Both overlays are warmed from the complete source although only ~23 bars show.
    expect(page.locator(".mmb-cx-body > svg > path")).to_have_count(2)


def test_invalid_ohlc_is_rejected_and_missing_volume_is_not_zero(page):
    rows = bars(date(2026, 8, 1))
    rows[-1][5] = None
    for index, bad in enumerate([None, "", "  ", True, False, "NaN", "Infinity"]):
        rows.append([(date(2026, 10, 22) + timedelta(days=index)).isoformat(), bad, 200, 90, 120, None])
    rows.extend([["2026-11-01", 120, 110, 90, 130, 1000], ["2026-02-30", 100, 120, 90, 110, 1000]])
    # Unsorted input and a duplicate valid date must still give one chronological bar.
    rows.append(rows[0][:])
    source(page, list(reversed(rows)))
    chart(page)
    svg = page.locator(".mmb-cx-body > svg")
    expect(svg).to_have_attribute("data-end", "2026-10-21")
    expect(svg).to_have_attribute("data-bars", str(len(bars(date(2026, 8, 1)))))
    bounds = svg.bounding_box()
    assert bounds
    svg.hover(position={"x": bounds["width"] - 65, "y": bounds["height"] / 3})
    expect(page.locator(".mmb-cx-vol")).to_have_text("V —")
    assert "NaN" not in svg.inner_html()
    assert "Infinity" not in svg.inner_html()


def test_weekly_and_monthly_contract_aggregate_real_daily_bars(page):
    rows = bars(date(2026, 9, 1))
    rows[-1][5] = None
    source(page, rows)
    chart(page, "WEEKLY")
    first = page.locator(".mmb-cx").last
    expect(first.locator(".mmb-cx-tf")).to_have_text("weekly")
    expect(first.locator("svg")).to_have_attribute("data-bars", "8")
    expect(first.locator(".mmb-cx-src")).to_contain_text("Aggregated from daily data")
    bounds = first.locator("svg").bounding_box()
    first.locator("svg").hover(position={"x": bounds["width"] - 65, "y": bounds["height"] / 3})
    # Oct 19-21: first open 103.4, max high 105.6, min low 102.4, last close 104.6.
    expect(first.locator(".mmb-cx-read")).to_contain_text("O 103.4")
    expect(first.locator(".mmb-cx-read")).to_contain_text("H 105.6")
    expect(first.locator(".mmb-cx-read")).to_contain_text("L 102.4")
    expect(first.locator(".mmb-cx-read")).to_contain_text("C 104.6")
    expect(first.locator(".mmb-cx-vol")).to_have_text("V —")
    chart(page, "MONTHLY")
    last = page.locator(".mmb-cx").last
    expect(last.locator(".mmb-cx-tf")).to_have_text("monthly")
    expect(last.locator("svg")).to_have_attribute("data-bars", "2")
    assert page.evaluate("window.__barCalls") == 1


def test_unchanged_width_resize_notification_keeps_hovered_aggregation(page):
    # ResizeObserver sends an initial notification and can later report height
    # changes. Neither changes the chart's horizontal drawing geometry.
    page.evaluate("""() => {
      const NativeObserver = window.ResizeObserver;
      window.ResizeObserver = class extends NativeObserver {
        constructor(callback) {
          super(callback);
          window.__chartResizeNotification = callback;
        }
      };
    }""")
    rows = bars(date(2026, 9, 1))
    rows[-1][5] = None
    source(page, rows)
    chart(page, "WEEKLY")
    svg = page.locator(".mmb-cx-body > svg")
    expect(svg).to_have_attribute("data-bars", "8")
    bounds = svg.bounding_box()
    svg.hover(position={"x": bounds["width"] - 65, "y": bounds["height"] / 3})
    read = page.locator(".mmb-cx-read")
    expect(read).to_contain_text("O 103.4")
    page.evaluate("window.__hoveredChart = document.querySelector('.mmb-cx-body > svg')")
    page.clock.install()
    page.evaluate("""() => {
      const box = document.querySelector('.mmb-cx');
      box.style.paddingBottom = '1px';
      window.__chartResizeNotification([{target: box, contentRect: box.getBoundingClientRect()}]);
    }""")
    page.clock.run_for(121)  # deliver the existing 120ms relayout debounce
    assert svg.evaluate("node => node === window.__hoveredChart")
    for value in ["O 103.4", "H 105.6", "L 102.4", "C 104.6"]:
        expect(read).to_contain_text(value)
    expect(page.locator(".mmb-cx-vol")).to_have_text("V —")
    # A real pointer exit still restores the ordinary last-close readout.
    page.mouse.move(0, 0)
    expect(read).to_have_text("104.6+0.29%")
    # A genuine width change still rebuilds at the new geometry.
    page.evaluate("""() => {
      const box = document.querySelector('.mmb-cx');
      box.style.width = '600px';
      window.__chartResizeNotification([{target: box, contentRect: box.getBoundingClientRect()}]);
    }""")
    page.clock.run_for(121)
    assert svg.evaluate("node => node !== window.__hoveredChart")
    assert svg.evaluate("""node => node.viewBox.baseVal.width ===
        Math.max(280, Math.min(1100, Math.round(node.parentNode.clientWidth)))""")
    expect(svg).to_have_attribute("data-bars", "8")


def test_failed_fetch_is_retryable_and_cache_expires(page):
    source(page, bars(), mode="fail")
    chart(page)
    expect(page.locator(".mmb-cx-miss")).to_be_visible()
    page.evaluate("window.__barMode='ok'")
    chart(page)
    expect(page.locator(".mmb-cx-body > svg")).to_have_count(1)
    assert page.evaluate("window.__barCalls") == 2
    page.evaluate("window.__clockNow=Date.now;Date.now=()=>window.__clockNow()+61000")
    chart(page)
    expect(page.locator(".mmb-cx-body > svg")).to_have_count(2)
    assert page.evaluate("window.__barCalls") == 3


def test_concurrent_cards_share_fetch_and_late_data_cannot_survive_stop(page):
    source(page, bars(), mode="hold")
    chart(page, count=2, hold=True)
    page.wait_for_function("!!window.__resolveBars")
    expect(page.locator(".mmb-cx")).to_have_count(2)
    assert page.evaluate("window.__barCalls") == 1
    page.locator("#mmb-send").click()
    expect(page.locator(".mmb-cx")).to_have_count(0)
    page.evaluate("window.__resolveBars()")
    page.wait_for_timeout(100)
    expect(page.locator(".mmb-cx, .mmb-chart")).to_have_count(0)


def test_month_end_clamps_and_locale_keeps_selected_range(page):
    source(page, bars(date(2026, 1, 1), date(2026, 3, 31)))
    chart(page)
    page.locator(".mmb-cx-ranges").get_by_role("button", name="1M", exact=True).click()
    svg = page.locator(".mmb-cx-body > svg")
    # Feb 28 is Saturday in this synthetic weekday series; the first actual bar is Mar 2.
    expect(svg).to_have_attribute("data-start", "2026-03-02")
    page.evaluate("document.documentElement.dataset.lang='zh';document.dispatchEvent(new Event('langchange'))")
    expect(page.locator(".mmb-cx-tf")).to_have_text("日线")
    expect(page.locator(".mmb-cx-ranges")).to_have_attribute("aria-label", "图表日期范围")
    expect(svg).to_have_attribute("data-range", "1M")
