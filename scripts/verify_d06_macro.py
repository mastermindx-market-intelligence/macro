"""D06 bounded browser proof against the existing Macro page owners.

The local server serves the owned site. Edge-state pages use explicit fixture
responses; no collector, model overlay, deployment or external data write runs.
"""
from __future__ import annotations

import argparse
import functools
import hashlib
import http.server
import json
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "docs/pr-crops/d06-macro-20261104"
OUT.mkdir(parents=True, exist_ok=True)


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def capture(page, name, locator=None):
    path = OUT / (name + ".png")
    if locator:
        page.locator(locator).screenshot(path=str(path))
    else:
        page.screenshot(path=str(path), full_page=False)
    return {"path": str(path.relative_to(ROOT)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def assert_reflow(page):
    metrics = page.evaluate("""() => ({
      width:document.documentElement.clientWidth,
      scroll:document.documentElement.scrollWidth,
      wrap:document.querySelector('.wrap')?.getBoundingClientRect().width
    })""")
    assert metrics["scroll"] <= metrics["width"] + 1, metrics
    return metrics


def make_page(browser, base, width, theme, locale):
    context = browser.new_context(viewport={"width": width, "height": 900 if width > 500 else 844},
                                  reduced_motion="reduce", locale="zh-CN" if locale == "zh" else "en-US")
    context.add_init_script("localStorage.setItem('theme'," + json.dumps(theme) + ");localStorage.removeItem('themeAuto');localStorage.setItem('lang'," + json.dumps(locale) + ");")
    page = context.new_page()
    page.set_default_timeout(10000)
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.route("**/*", lambda route: route.continue_() if route.request.url.startswith(base) else route.abort())
    return context, page, errors


def market(browser, base):
    from scripts.build_market_structure_page import render
    from playwright.sync_api import expect
    receipt = {"matrix": [], "edge_cases": [], "scope": "Actual owned generated page plus explicit missing-data fixtures."}
    for width, theme, locale in [(1440, "light", "en"), (1440, "dark", "zh"),
                                  (1440, "dark", "en"), (1440, "light", "zh"),
                                  (720, "light", "en"), (390, "dark", "en"), (390, "light", "zh"),
                                  (390, "light", "en"), (390, "dark", "zh"), (320, "light", "en")]:
        context, page, errors = make_page(browser, base, width, theme, locale)
        page.goto(base + "/market_structure.html", wait_until="networkidle")
        page.wait_for_selector("#gex-chart rect")
        assert page.locator("html").get_attribute("data-theme") == theme
        assert page.locator("html").get_attribute("data-lang") == locale
        metrics = assert_reflow(page)
        if not receipt["matrix"]:
            from datetime import date
            from lib import nyse_calendar
            actual = json.loads((ROOT / "data/market_structure/latest.json").read_text())
            source_rows = {r["date"]:r for r in actual["gamma"]["history"]}
            embedded = page.evaluate("MSP_GAMMA_HIST")
            expected_days = nyse_calendar.sessions_between(date.fromisoformat(embedded[0]["date"]), date.fromisoformat(embedded[-1]["date"]))
            missing = [str(d) for d in expected_days if str(d) not in source_rows]
            assert [r["date"] for r in embedded if r.get("_missing_session")] == missing
            for row in embedded:
                if row.get("_missing_session"):
                    assert all(row[key] is None for key in ("net_gex_bn","spot","flip"))
                else:
                    assert all(row[key] == source_rows[row["date"]][key] for key in ("net_gex_bn","spot","flip","regime"))
            receipt["actual_session_gaps"] = {"observations":len(embedded)-len(missing),"missing_sessions":missing,"source_values_unchanged":True}
        order = page.locator(".msp-driver").evaluate_all("(xs)=>xs.map(x=>({name:x.dataset.driver,y:x.getBoundingClientRect().top})).sort((a,b)=>a.y-b.y).map(x=>x.name)")
        assert order == ["gex", "week", "flows", "dispersion", "vol"], order
        sizes = page.locator(".rbtn").evaluate_all("(xs)=>xs.map(x=>x.getBoundingClientRect().height)")
        assert min(sizes) >= 44, sizes
        image = capture(page, f"market-{width}-{theme}-{locale}")
        page.locator('#gex-range-btns button[data-range="21"]').click()
        page.locator('#sys-range-btns button[data-range="63"]').click()
        page.locator('#cor-range-btns button[data-range="9999"]').click()
        page.reload(wait_until="networkidle")
        for key, value in [("gex", "21"), ("sys", "63"), ("cor", "9999")]:
            assert page.locator(f'#{key}-range-btns button[aria-pressed="true"]').get_attribute("data-range") == value
        # W2.R: first useful reading, keyboard exact values, actual CSV download.
        overview = page.locator("#msp-overview")
        expect(overview).to_be_visible()
        assert overview.bounding_box()["y"] < page.locator("#gex-chart").bounding_box()["y"]
        page.locator("#gex-observations > summary").focus()
        page.keyboard.press("Enter")
        assert page.locator("#gex-observations").get_attribute("open") is not None
        assert page.locator("#gex-observations tbody tr").count() == 21
        page.locator("#gex-observations .msp-table-scroll").focus()
        assert page.locator("#gex-observations .msp-table-scroll").evaluate("(el)=>el===document.activeElement")
        with page.expect_download() as pending:
            page.locator('[data-export-series="gex"]').click()
        import csv, io
        downloaded = list(csv.reader(io.StringIO(Path(pending.value.path()).read_text(encoding="utf-8-sig"))))
        assert len(downloaded) == 22
        expected_rows = page.evaluate("MSP_GAMMA_HIST.slice(-21).map(r=>[r.date,...['net_gex_bn','spot','flip'].map(k=>typeof r[k]==='number'&&Number.isFinite(r[k])?String(r[k]):''),r._missing_session?'Missing session':'Supplied'])")
        assert downloaded[1:] == expected_rows
        page.locator("#gex-observations > summary").click()
        help_button = page.locator('.msp-driver[data-driver="week"] .help')
        help_button.focus()
        assert page.get_by_role("tooltip").is_visible()  # existing shared help owner upgrades the inline fallback
        assert help_button.get_attribute("aria-describedby")
        page.locator("#msp-snapshot-details > summary").focus()
        page.keyboard.press("Enter")
        page.locator("#watch-band summary").focus()
        page.keyboard.press("Enter")
        assert page.locator("#watch-band").get_attribute("open") is not None
        assert_reflow(page)
        assert not errors, errors
        receipt["matrix"].append({"width": width, "theme": theme, "locale": locale, "metrics": metrics,
                                   "range_persistence": True, "keyboard_help": True, "image": image})
        context.close()
    raw = json.loads((ROOT / "tests/fixtures/market_structure_latest.json").read_text())
    raw["gamma"]["history"] = [
        {"date": "2026-10-26", "net_gex_bn": 1, "spot": 100, "flip": 99},
        {"date": "2026-10-27", "net_gex_bn": None, "spot": None, "flip": 100},
        {"date": "2026-10-28", "net_gex_bn": 0, "spot": 110, "flip": 101},
        {"date": "2026-10-29", "net_gex_bn": -2, "spot": 112, "flip": 102},
    ]
    raw["systematic"]["history"] = [{"date": "2026-10-29", "vc_alloc_bn": 0, "spx_close": 100}]
    raw["dispersion"]["history"] = [{"date": f"2026-10-{26+i}", "cor1m": v} for i, v in enumerate([2, 3, None, 0, None, 4, 4])]
    raw["week_map"].update({"band_1sigma_lo": None, "band_1sigma_hi": None, "locked_close": None,
        "week_start": "2026-10-26", "week_end": "2026-10-30", "locked_at": "2026-10-23"})
    import tempfile
    with tempfile.TemporaryDirectory(prefix="d06-market-fixture-") as tmp:
        fixture = Path(tmp) / "partial.json"
        fixture.write_text(json.dumps(raw))
        html = render(ROOT, fixture=fixture)
        context, page, errors = make_page(browser, base, 390, "light", "en")
        page.route("**/market_structure.html?d06=partial", lambda route: route.fulfill(body=html, content_type="text/html"))
        page.goto(base + "/market_structure.html?d06=partial", wait_until="networkidle")
        page.wait_for_selector("#gex-chart rect")
        assert page.locator("#gex-chart rect").count() == 3
        assert page.locator('#gex-chart rect[data-value="0"]').count() == 1
        assert page.locator('#spx-flip-chart circle[data-series="spot"]').count() == 1
        assert page.locator('#spx-flip-chart path[data-series="spot"]').count() == 1
        assert page.locator('#spx-flip-chart path[data-series="flip"]').count() == 1
        assert page.locator("#sys-chart circle").count() == 2
        assert page.locator('.wm-band [data-band="1"]').count() == 0
        assert page.locator('.wm-band [data-band="2"]').count() == 1
        assert "3/4" in page.locator("#gex-range-status").inner_text()
        page.locator("#gex-observations > summary").click()
        exact = page.locator("#gex-observations tbody").inner_text()
        assert "Unavailable" in exact and "0" in exact
        assert page.locator("[data-weekly-range]").get_attribute("data-week-phase") == "expired"
        expect(page.locator("#msp-week-state")).to_contain_text("Past week")
        # Simulate a retained tab crossing the supplied week end; values remain intact.
        page.evaluate("""() => {
          const week=document.querySelector('[data-weekly-range]');
          week.dataset.weekStart='2000-01-03T00:00:00-05:00';
          week.dataset.weekExpires='2000-01-07T17:00:00-05:00';
          week.dataset.weekPhase='current';
          const age=document.querySelector('#msp-snapshot-age');
          age.dataset.ageState='dated';age.dataset.checkExpires='2000-01-07T17:00:00-05:00';
          window.dispatchEvent(new Event('pageshow'));
        }""")
        expect(page.locator("#msp-week-state")).to_contain_text("Past week")
        expect(page.locator("#msp-snapshot-age")).to_contain_text("newer session may be missing")
        assert page.locator('.wm-band [data-band="2"]').count() == 1
        assert_reflow(page)
        receipt["edge_cases"].append({"case": "gaps-zero-singleton-outer-only", "image": capture(page, "market-partial-outer-only", '[data-driver="week"]')})
        raw["gamma"]["history"] = [{"date": "2026-10-29", "net_gex_bn": None, "spot": None, "flip": None}]
        fixture.write_text(json.dumps(raw))
        html = render(ROOT, fixture=fixture)
        page.reload(wait_until="networkidle")
        assert page.locator("#gex-chart *").count() == 0
        assert page.locator("#spx-flip-chart *").count() == 0
        assert "GEX unavailable" in page.locator("#gex-range-status").inner_text()
        page.evaluate("document.documentElement.setAttribute('data-lang','zh');document.dispatchEvent(new CustomEvent('langchange'))")
        page.wait_for_function("document.querySelector('#gex-range-status').innerText.includes('暂无数据')")
        assert_reflow(page)
        assert not errors, errors
        receipt["edge_cases"].append({"case": "all-missing-and-language-change", "image": capture(page, "market-missing-zh", '[data-driver="gex"]')})
        context.close()
    return receipt


def stage(browser, base):
    import copy
    import csv
    import tempfile
    from scripts.build_stage_analysis_page import render
    from scripts.d06_macro_fixtures import stage_fixtures
    from playwright.sync_api import expect
    sga, fixtures = stage_fixtures()
    receipt = {"matrix": [], "edge_cases": [], "scope": "Actual renderer/assets; explicit synthetic 12-file data fixtures, plus actual pinned-context page."}
    with tempfile.TemporaryDirectory(prefix="d06-stage-fixtures-") as tmp:
        fp = Path(tmp) / "context.json"
        def html_for(context):
            fp.write_text(json.dumps(context))
            return render(ROOT, fixture=fp)
        fixture_html = html_for(sga)
        def setup(width, theme, locale, *, data=None, modes=None, context_vm=None):
            ctx, page, errors = make_page(browser, base, width, theme, locale)
            data = data if data is not None else copy.deepcopy(fixtures)
            modes = modes if modes is not None else {}
            counts, held = {}, {}
            body = html_for(context_vm) if context_vm is not None else fixture_html
            page.route("**/stage_analysis.html*", lambda route: route.fulfill(body=body, content_type="text/html"))
            def handle(route):
                name = route.request.url.split("/")[-1].split("?")[0]
                counts[name] = counts.get(name, 0) + 1
                mode = modes.get(name)
                if mode == "hold":
                    held[name] = route
                elif mode == "error":
                    route.fulfill(status=503, body="fixture read failure")
                elif mode == "invalid":
                    route.fulfill(body="{broken", content_type="application/json")
                else:
                    route.fulfill(body=json.dumps(data[name]), content_type="application/json")
            page.route("**/stagedata/*.json", handle)
            page.goto(base + "/stage_analysis.html?d06=fixture", wait_until="domcontentloaded")
            return ctx, page, errors, counts, held
        def tab(page, name):
            page.locator("#tab-"+name).click()
            expect(page.locator("#tab-"+name)).to_have_attribute("aria-selected", "true")
            expect(page.locator("#s-"+name)).to_be_visible()
        def keyboard_sort(page, header, cells):
            button=page.locator(header+" button")
            button.focus()
            page.keyboard.press("Enter")
            expect(page.locator(header)).to_have_attribute("aria-sort","ascending")
            expect(button).to_be_focused()
            ascending=page.locator(cells).all_text_contents()
            assert len(ascending)>1 and ascending==sorted(ascending,key=str.casefold),ascending
            page.keyboard.press("Space")
            expect(page.locator(header)).to_have_attribute("aria-sort","descending")
            expect(button).to_be_focused()
            descending=page.locator(cells).all_text_contents()
            assert descending==list(reversed(ascending)),(ascending,descending)
        for width, theme, locale in [(1440,"dark","en"),(1440,"light","zh"),(390,"light","en"),(390,"dark","zh"),(320,"light","en")]:
            ctx, page, errors, counts, held = setup(width, theme, locale)
            expect(page.locator('#screener-body > tr[data-tk]')).to_have_count(11)
            expect(page.locator("#arc-wrap")).to_have_attribute("data-population","ready")
            expect(page.locator("html")).to_have_attribute("data-theme", theme)
            expect(page.locator("html")).to_have_attribute("data-lang", locale)
            metrics=assert_reflow(page)
            sizes=page.locator('[id^="tab-"][role="tab"]').evaluate_all("(xs)=>xs.map(x=>x.getBoundingClientRect().height)")
            assert len(sizes)==6 and min(sizes)>=44, sizes
            image=capture(page,f"stage-{width}-{theme}-{locale}")
            tip=page.locator('label[for="f-rating"] .tip-q')
            tip.focus();page.keyboard.press("Enter")
            expect(tip).to_have_class(__import__("re").compile(r"\btip-open\b"))
            assert tip.get_attribute("aria-description")
            assert_reflow(page)
            page.keyboard.press("Escape")
            expect(tip).to_be_focused()
            assert tip.evaluate("(e)=>getComputedStyle(e,'::after').display")=="none"
            advanced=[]
            if width==1440 and locale=="en":
                page.locator("#f-rating").fill("80")
                expect(page.locator('#screener-body > tr[data-tk]')).to_have_count(2)
                page.locator("#tick-search").fill("NVDA")
                expect(page.locator('#screener-body > tr[data-tk]')).to_have_count(1)
                row=page.locator('#screener-body > tr[data-tk="NVDA"]')
                row.locator(".addbtn").click()
                expect(row.locator(".addbtn")).to_have_attribute("aria-pressed","true")
                assert "NVDA" in page.evaluate("JSON.parse(localStorage.getItem('sga_watch'))")
                row.locator(".exp-btn").click()
                expect(row.locator(".exp-btn")).to_have_attribute("aria-expanded","true")
                expect(page.locator('#screener-body tr.detail-row')).to_be_visible()
                with page.expect_download() as dl:
                    page.locator("#screener-csv").click()
                csvpath=OUT/"stage-filtered-fixture.csv"
                dl.value.save_as(str(csvpath))
                rows=list(csv.reader(csvpath.open(newline="")))
                assert len(rows)==2 and len(rows[0])==25 and "NVDA" in rows[1]
                assert "1.4" in rows[1] and "0.04" in rows[1] and "2026-09-04" in rows[1], rows
                page.locator("#tick-search").fill("")
                page.locator("#screener-reset").click()
                expect(page.locator('#screener-body > tr[data-tk]')).to_have_count(11)
                keyboard_sort(page,'#screener-head th[data-k="ticker"]','#screener-body > tr[data-tk] .tk')
                advanced.extend(["filter-search-sort","watchlist","row-expansion","filtered-raw-unit-CSV"])
            tab(page,"board")
            expect(page.locator("#board-body .tk").first).to_be_visible()
            page.locator('#board-seg [data-cadence="daily"]').click()
            expect(page.locator('#board-seg [data-cadence="daily"]')).to_have_attribute("aria-pressed","true")
            expect(page.locator("#board-body .tk").first).to_be_visible()
            tab(page,"industries")
            expect(page.locator("#ind-body table.screener")).to_be_visible()
            for view in ["heatmap","echeat","flows"]:
                page.locator('#ind-seg [data-iview="'+view+'"]').click()
                expect(page.locator("#ind-body table")).to_be_visible()
            page.locator('#flow-grain [data-grain="sub"]').click()
            expect(page.locator("#flow-table")).to_contain_text("Semiconductor designers")
            page.locator('#flow-grain [data-grain="industry"]').click()
            expect(page.locator("#flow-table")).to_contain_text("Semiconductors")
            if width==1440 and locale=="en":
                keyboard_sort(page,'#flow-table th[data-fk="industry_name"]','#flow-table tbody tr td:first-child')
                advanced.append("keyboard-screener-and-flow-sort-focus")
            tab(page,"earnings")
            expect(page.locator("#ern-table")).to_be_visible()
            if width==1440 and locale=="en":
                keyboard_sort(page,'#ern-table th[data-ek="ticker"]','#ern-table .callrow .tk')
                advanced.append("keyboard-earnings-sort-focus")
                call=page.locator('#ern-table .callrow[data-tk="NVDA"]')
                call.focus();page.keyboard.press("Enter")
                expect(page.locator("#reader")).to_be_visible()
                expect(page.locator("#reader-body")).to_contain_text("Synthetic fixture quotation")
                expect(page.locator("#reader-close")).to_be_focused()
                assert page.locator("#reader-terminal").get_attribute("href")
                page.keyboard.press("Shift+Tab")
                expect(page.locator("#reader-terminal")).to_be_focused()
                page.keyboard.press("Tab")
                expect(page.locator("#reader-close")).to_be_focused()
                page.keyboard.press("Escape")
                expect(page.locator("#reader")).to_be_hidden()
                expect(call).to_be_focused()
                page.locator("#ern-f-band").select_option("dn")
                expect(page.locator("#ern-body")).to_contain_text("No earnings calls match")
                page.locator("#ern-f-band").select_option("")
                advanced.append("keyboard-earnings-reader-and-filtered-empty")
            for view in ["season","compare"]:
                page.locator('#ern-seg [data-eview="'+view+'"]').click()
                expect(page.locator("#ern-body")).not_to_contain_text("could not load")
                expect(page.locator("#ern-body [data-read-state]")).to_have_count(0)
            tab(page,"altdata")
            expect(page.locator("#alt-body .altcol")).to_have_count(4)
            tab(page,"research")
            card=page.locator('#res-body .rescard[data-tk="NVDA"]')
            expect(card).to_be_visible()
            card.locator(".more").click()
            expect(card).to_have_class(__import__("re").compile(r"\bopen\b"))
            assert_reflow(page)
            assert not errors, errors
            assert set(counts)==set(fixtures) and all(n==1 for n in counts.values()), counts
            receipt["matrix"].append({"width":width,"theme":theme,"locale":locale,"metrics":metrics,
                "six_tasks":True,"all_subviews":True,"advanced":advanced,"requests":counts,"image":image})
            ctx.close()
        # Failed screener retains local controls and one pending retry; healthy tabs stay usable.
        modes={"screener.json":"error"}
        ctx,page,errors,counts,held=setup(390,"light","en",modes=modes)
        expect(page.locator('#s-screener [data-read-state="error"]')).to_be_visible()
        page.locator("#tick-search").fill("NVDA")
        page.locator("#f-rating").fill("80")
        expect(page.locator("#screener-csv")).to_be_disabled()
        modes["screener.json"]="hold"
        page.locator('[data-retry-slice="screener.json"]').click()
        expect(page.locator('#s-screener [data-read-state="loading"]')).to_be_visible()
        expect(page.locator("#tab-screener")).to_be_focused()
        tab(page,"board")
        expect(page.locator("#board-body .tk").first).to_be_visible()
        assert counts["screener.json"]==2 and "screener.json" in held, counts
        held.pop("screener.json").fulfill(body=json.dumps(fixtures["screener.json"]),content_type="application/json")
        tab(page,"screener")
        expect(page.locator('#screener-body > tr[data-tk]')).to_have_count(1)
        expect(page.locator("#tick-search")).to_have_value("NVDA")
        expect(page.locator("#f-rating")).to_have_value("80")
        expect(page.locator("#screener-csv")).to_be_enabled()
        assert counts["screener.json"]==2
        receipt["edge_cases"].append({"case":"failed-screener-retained-filters-deduplicated-pending-retry","image":capture(page,"stage-recovered-filtered", "#s-screener")})
        assert not errors,errors
        ctx.close()
        # A late weekly failure and late recovery never replace the selected Daily board.
        modes={"stage_board_weekly.json":"hold"}
        ctx,page,errors,counts,held=setup(1440,"dark","en",modes=modes)
        tab(page,"board")
        expect(page.locator('#board-body [data-read-state="loading"]')).to_be_visible()
        page.locator('#board-seg [data-cadence="daily"]').click()
        expect(page.locator("#board-body .tk").first).to_be_visible()
        before=page.locator("#board-body").inner_text()
        held.pop("stage_board_weekly.json").fulfill(status=503,body="late failure")
        expect(page.locator("#board-body")).to_have_text(before,use_inner_text=True)
        page.locator('#board-seg [data-cadence="weekly"]').click()
        expect(page.locator('#board-body [data-read-state="error"]')).to_be_visible()
        page.locator('[data-retry-slice="stage_board_weekly.json"]').click()
        expect(page.locator('#board-body [data-read-state="loading"]')).to_be_visible()
        page.locator('#board-seg [data-cadence="daily"]').click()
        expect(page.locator("#board-body .tk").first).to_be_visible()
        held.pop("stage_board_weekly.json").fulfill(body=json.dumps(fixtures["stage_board_weekly.json"]),content_type="application/json")
        expect(page.locator("#board-body")).to_have_text(before,use_inner_text=True)
        assert counts["stage_board_weekly.json"]==2 and counts["stage_board_daily.json"]==1
        receipt["edge_cases"].append({"case":"late-weekly-failure-and-recovery-preserve-selected-daily","image":capture(page,"stage-independent-board","#s-board")})
        assert not errors,errors
        ctx.close()
        # Invalid nested siblings stay errors; valid empty and unavailable history are separate states.
        data=copy.deepcopy(fixtures)
        data["earnings_season.json"]={"quarters":[{}]}
        data["industry_heatmap.json"]={"regions":{},"history":{"status":"unavailable"}}
        data["industry_flows.json"]["sub_industry_regions"]["USA"]=[]
        data["research_index.json"]={"items":[]}
        modes={"earnings_table.json":"error","altdata_trending.json":"invalid"}
        ctx,page,errors,counts,held=setup(390,"dark","en",data=data,modes=modes)
        tab(page,"industries")
        page.locator('#ind-seg [data-iview="heatmap"]').click()
        expect(page.locator("#ind-body [data-read-state]")).to_have_count(0)
        page.locator('#ind-seg [data-iview="flows"]').click()
        page.locator('#flow-grain [data-grain="sub"]').click()
        expect(page.locator('#flow-grain [data-grain="industry"]')).to_be_visible()
        page.locator('#flow-grain [data-grain="industry"]').click()
        expect(page.locator("#flow-table")).to_be_visible()
        tab(page,"earnings")
        expect(page.locator('#ern-body [data-read-state="error"]')).to_be_visible()
        page.locator('#ern-seg [data-eview="season"]').click()
        expect(page.locator('#ern-body [data-read-state="error"]')).to_be_visible()
        data["earnings_season.json"]={"data_status":"stale","quarters":[]}
        page.locator('[data-retry-slice="earnings_season.json"]').click()
        expect(page.locator("#ern-body [data-read-state]")).to_have_count(0)
        assert counts["earnings_table.json"]==1 and counts["earnings_season.json"]==2
        tab(page,"altdata")
        expect(page.locator('#alt-body [data-read-state="error"]')).to_be_visible()
        modes.pop("altdata_trending.json")
        data["altdata_trending.json"]={"sources":{"google":{"topics":[]}}}
        page.locator('[data-retry-slice="altdata_trending.json"]').click()
        expect(page.locator("#alt-body [data-read-state]")).to_have_count(0)
        expect(page.locator("#alt-body")).to_contain_text("Update date unavailable")
        tab(page,"research")
        expect(page.locator("#res-body [data-read-state]")).to_have_count(0)
        expect(page.locator("#res-body .rescard")).to_have_count(0)
        receipt["edge_cases"].append({"case":"malformed-season-invalid-JSON-stale-valid-empty-and-independent-siblings","image":capture(page,"stage-valid-empty-research","#s-research")})
        assert not errors, errors
        assert_reflow(page)
        ctx.close()
        for locale in ["en","zh"]:
            data=copy.deepcopy(fixtures)
            data["earnings_season.json"].update(data_status="stale",latest_call_date="2026-07-31")
            data["earnings_compare.json"].update(data_status="degraded",latest_call_date="2026-08-15")
            ctx,page,errors,counts,held=setup(390,"light",locale,data=data)
            tab(page,"earnings")
            for view,status,date in [("season","stale","2026-07-31"),("compare","degraded","2026-08-15")]:
                page.locator('#ern-seg [data-eview="'+view+'"]').click()
                note=page.locator('#ern-body [data-earnings-health="'+status+'"]')
                expect(note).to_be_visible()
                expect(note).to_contain_text(date)
                expect(page.locator("#ern-body")).to_contain_text("Q2 2026")
                assert_reflow(page)
            receipt["edge_cases"].append({"case":"nonempty-stale-and-degraded-earnings-"+locale,"image":capture(page,"stage-nonempty-earnings-"+locale,"#s-earnings")})
            page.locator('#ern-seg [data-eview="calls"]').click()
            expect(page.locator('#ern-body [data-earnings-health]')).to_have_count(0)
            expect(page.locator("#ern-table")).to_be_visible()
            assert all(counts.get(name)==1 for name in ["earnings_table.json","earnings_season.json","earnings_compare.json"]),counts
            assert not errors,errors
            ctx.close()
        for state in ["unknown","empty"]:
            context_vm=copy.deepcopy(sga)
            context_vm["counts"].update({k:None if state=="unknown" else 0 for k in ["total","stage1","stage2","stage3","stage4","stage2_fresh"]})
            context_vm["population"]["status"]="no_target_week" if state=="unknown" else "ok"
            ctx,page,errors,counts,held=setup(390,"light","zh",context_vm=context_vm)
            expect(page.locator("#arc-wrap")).to_have_attribute("data-population",state)
            assert page.locator("#arc-wrap circle[fill]:not([fill=none])").count()==0
            expect(page.locator(".arc-state")).to_contain_text("阶段判定暂不可用" if state=="unknown" else "没有已分类股票")
            expect(page.locator("section.hero .stancepill")).to_have_count(0)
            receipt["edge_cases"].append({"case":"population-"+state,"image":capture(page,"stage-arc-"+state,"section.hero")})
            assert not errors,errors
            ctx.close()
    return receipt


def spv(browser, base):
    import copy
    from playwright.sync_api import expect
    from scripts.build_spvector import render_page
    from scripts.d06_macro_fixtures import spv_fixture_vm
    vm=spv_fixture_vm()
    html=render_page(vm)
    receipt={"matrix":[],"edge_cases":[],"scope":"Actual Plotly helpers and renderer on explicit synthetic histories; no model/publication build."}
    for width,theme,locale in [(1440,"light","en"),(1440,"dark","zh"),(390,"dark","en"),(390,"light","zh"),(320,"light","en")]:
        ctx,page,errors=make_page(browser,base,width,theme,locale)
        page.route("**/spvector.html?d06=fixture",lambda route:route.fulfill(body=html,content_type="text/html"))
        page.goto(base+"/spvector.html?d06=fixture",wait_until="networkidle")
        expect(page.locator('[data-spv-range="1"]')).to_be_enabled()
        expect(page.locator("html")).to_have_attribute("data-theme",theme)
        expect(page.locator("html")).to_have_attribute("data-lang",locale)
        metrics=assert_reflow(page)
        expect(page.locator('#spv-allocation [data-equity-weight]')).to_have_attribute("data-equity-weight","100")
        expect(page.locator("#spv-shadow")).to_contain_text("66%")
        sizes=page.locator("[data-spv-range]").evaluate_all("(xs)=>xs.map(x=>x.getBoundingClientRect().height)")
        assert min(sizes)>=44,sizes
        ranges=[]
        for i in [0,2,3,1]:
            button=page.locator(f'[data-spv-range="{i}"]')
            expected_y=page.locator("#spv-study .js-plotly-plot").evaluate("(p,i)=>p.layout.updatemenus[0].buttons[i].args[0]['yaxis.range']",i)
            button.focus();page.keyboard.press("Enter")
            expect(button).to_have_attribute("aria-pressed","true")
            ranges.append(page.locator("#spv-study .js-plotly-plot").evaluate("(p)=>[p.layout.xaxis.range,p.layout.xaxis2.range,p.layout.xaxis3.range,p.layout.yaxis.range]"))
            assert ranges[-1][0]==ranges[-1][1]==ranges[-1][2]
            assert ranges[-1][3]==expected_y,(ranges[-1][3],expected_y)
        assert ranges[0][0]!=ranges[2][0]
        assert ranges[0][3]!=ranges[2][3]
        page.evaluate("window.scrollTo(0,0)")
        image=capture(page,f"spv-{width}-{theme}-{locale}")
        if width in (1440,390) and locale=="en":
            receipt["edge_cases"].append({"case":f"three-panel-study-{width}", "image":capture(page,f"spv-study-{width}","#spv-study")})
        for id in ["spv-gate","spv-breakdown","spv-history","spv-scorecard","spv-rules","spv-ledger","spv-methods"]:
            summary=page.locator("#"+id+" > summary")
            summary.focus();page.keyboard.press("Enter")
            expect(page.locator("#"+id)).to_have_attribute("open","")
            assert_reflow(page)
        growth=page.locator("#spv-history .js-plotly-plot").first
        assert growth.evaluate("(p)=>p.layout.yaxis.type")=="log"
        assert page.locator("#spv-study .js-plotly-plot").evaluate("(p)=>p.data.some(t=>t.name==='Buy / add')&&p.data.some(t=>t.name==='Sell / trim')")
        expect(page.locator("#spv-breakdown")).to_contain_text("24.8")
        if width==1440 and locale=="en":
            receipt["edge_cases"].append({"case":"expanded-model-depth-and-history","image":capture(page,"spv-depth","#spv-breakdown")})
        assert not errors,errors
        receipt["matrix"].append({"width":width,"theme":theme,"locale":locale,"metrics":metrics,"synced_ranges":ranges,
            "all_analytical_details":True,"log_growth":True,"model_change_markers":True,"image":image})
        ctx.close()
    for state in ["missing","last-available"]:
        absent=copy.deepcopy(vm)
        absent.update(score=None if state=="missing" else 0,score_current_available=False,
            score_as_of=None if state=="missing" else "2026-10-16",
            score_aligned_as_of=None if state=="missing" else "2026-10-16",
            overlay={"enabled":False},legs_score=None,legs_as_of=None)
        absent["disloc"].update(cap_available=False,put_available=False,gate_model_available=False)
        body=render_page(absent)
        ctx,page,errors=make_page(browser,base,390,"light","en")
        page.route("**/spvector.html?d06=fixture",lambda route:route.fulfill(body=body,content_type="text/html"))
        page.goto(base+"/spvector.html?d06=fixture",wait_until="networkidle")
        expect(page.locator("#spv-model-readings")).to_contain_text("Unavailable")
        expect(page.locator("#spv-shadow")).to_contain_text("No shadow assessment")
        assert "0/3" not in page.locator("#spv-model-readings").inner_text()
        assert_reflow(page)
        receipt["edge_cases"].append({"case":"score-"+state,"image":capture(page,"spv-"+state,"#spv-model-readings")})
        assert not errors,errors
        ctx.close()
    return receipt


def actual(browser, base):
    from playwright.sync_api import expect
    receipt={"matrix":[],"edge_cases":[],"scope":"Owned generated HTML and exact pinned producer artifacts; browser-local serving, no live feed or deployment."}
    for width,theme,locale in [(1440,"light","en"),(390,"dark","zh")]:
        ctx,page,errors=make_page(browser,base,width,theme,locale)
        page.goto(base+"/spvector.html",wait_until="networkidle")
        expect(page.locator('[data-spv-range="1"]')).to_be_enabled()
        assert_reflow(page)
        values={key:page.locator(selector).inner_text() for key,selector in [
            ("allocation","#spv-allocation"),("readings","#spv-model-readings"),("shadow","#spv-shadow")]}
        expect(page.locator("#spv-shadow")).to_contain_text("没有可用的影子评估" if locale=="zh" else "No shadow assessment")
        page.locator('[data-spv-range="3"]').click()
        expect(page.locator('[data-spv-range="3"]')).to_have_attribute("aria-pressed","true")
        ranges=page.locator("#spv-study .js-plotly-plot").evaluate("(p)=>[p.layout.xaxis.range,p.layout.xaxis2.range,p.layout.xaxis3.range]")
        assert ranges[0]==ranges[1]==ranges[2]
        page.evaluate("window.scrollTo(0,0)")
        receipt["matrix"].append({"page":"spvector.html","width":width,"theme":theme,"locale":locale,
            "source_readings":values,"ranges":ranges,"image":capture(page,f"spv-actual-{width}-{locale}")})
        assert not errors,errors
        ctx.close()
    for width,theme,locale in [(1440,"dark","en"),(390,"light","zh")]:
        ctx,page,errors=make_page(browser,base,width,theme,locale)
        files,counts={},{}
        def route_data(route):
            name=route.request.url.split("/")[-1].split("?")[0]
            path=STAGE_INPUTS/name
            counts[name]=counts.get(name,0)+1
            if not path.is_file():
                route.fulfill(status=404,body="pinned source missing");return
            raw=path.read_text();files[name]=json.loads(raw)
            route.fulfill(body=raw,content_type="application/json")
        page.route("**/stagedata/*.json",route_data)
        page.goto(base+"/stage_analysis.html",wait_until="networkidle")
        observations=[]
        def check(panel,name):
            expect(page.locator(panel+' [data-read-state="loading"]')).to_have_count(0)
            failure=page.locator(panel+' [data-read-state="error"]')
            assert failure.count()==0,{"file":name,"state":failure.inner_text() if failure.count() else "", "keys":list(files.get(name,{}))[:15]}
            observations.append({"file":name,"ready":True,"rows":len(files.get(name,{}).get("rows",[])),"source_status":files.get(name,{}).get("data_status",files.get(name,{}).get("status"))})
            assert_reflow(page)
        check("#s-screener","screener.json")
        count_bounds=page.locator(".stn .num").evaluate_all("""xs=>xs.map(e=>{
          const r=document.createRange();r.selectNodeContents(e);const text=r.getBoundingClientRect();
          const card=e.closest('.stn').getBoundingClientRect();
          return {text:e.textContent,left:text.left,right:text.right,cardLeft:card.left,cardRight:card.right};
        })""")
        assert all(x["left"]>=x["cardLeft"] and x["right"]<=x["cardRight"] for x in count_bounds),count_bounds
        for task in ["board","industries","earnings","altdata","research"]:
            page.locator("#tab-"+task).click()
            if task=="board":
                check("#board-body","stage_board_weekly.json")
                page.locator('#board-seg [data-cadence="daily"]').click()
                check("#board-body","stage_board_daily.json")
            elif task=="industries":
                check("#ind-body","industry_ranks.json")
                for view,name in [("heatmap","industry_heatmap.json"),("echeat","ec_industry_heatmap.json"),("flows","industry_flows.json")]:
                    page.locator('#ind-seg [data-iview="'+view+'"]').click();check("#ind-body",name)
            elif task=="earnings":
                check("#ern-body","earnings_table.json")
                for view,name in [("season","earnings_season.json"),("compare","earnings_compare.json")]:
                    page.locator('#ern-seg [data-eview="'+view+'"]').click();check("#ern-body",name)
            elif task=="altdata":check("#alt-body","altdata_trending.json")
            else:check("#res-body","research_index.json")
        assert len(observations)==12 and all(x==1 for x in counts.values()),counts
        page.locator("#tab-screener").click()
        page.evaluate("window.scrollTo(0,0)")
        receipt["matrix"].append({"page":"stage_analysis.html","width":width,"theme":theme,"locale":locale,
            "slices":observations,"requests":counts,"image":capture(page,f"stage-actual-{width}-{locale}")})
        assert not errors,errors
        ctx.close()
    return receipt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", choices=["market", "stage", "spv", "actual"], required=True)
    parser.add_argument("--stage-inputs", type=Path, help="Pinned stagedata directory for --only actual")
    parser.add_argument("--output-dir", type=Path, help="Separate evidence directory for a new source revision")
    args = parser.parse_args()
    global STAGE_INPUTS, OUT
    if args.output_dir:
        OUT = args.output_dir.resolve()
        OUT.mkdir(parents=True, exist_ok=True)
    STAGE_INPUTS = args.stage_inputs
    if args.only=="actual" and not STAGE_INPUTS:
        parser.error("--stage-inputs is required for actual producer proof")
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(QuietHandler, directory=str(ROOT / "site")))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    receipt = {"status": "started", "surface": args.only}
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, channel="chrome", timeout=30000)
            try:
                receipt.update(globals()[args.only](browser, base))
                receipt["status"] = "passed"
            finally:
                browser.close()
    except Exception as exc:
        receipt.update(status="failed", error=repr(exc))
        raise
    finally:
        receipt["source_hashes"] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                   for p in [Path(__file__), ROOT / "templates/market_structure.html.j2",
                                             ROOT / "templates/stage_analysis.html.j2", ROOT / "templates/spvector.html.j2"]}
        (OUT / (args.only + "-browser.json")).write_text(json.dumps(receipt, ensure_ascii=False, indent=2))
        server.shutdown(); server.server_close()
    print(json.dumps({"surface": args.only, "status": receipt["status"], "matrix": len(receipt.get("matrix", [])), "edge_cases": len(receipt.get("edge_cases", []))}))


if __name__ == "__main__":
    main()
