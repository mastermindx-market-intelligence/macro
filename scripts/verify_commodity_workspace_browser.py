"""Exercise the rendered commodity research journey in an anonymous local browser.

Serve the existing site only. No collector, economic recomputation, credentials,
monitor activation or production write is involved.
"""
from __future__ import annotations

import argparse
import hashlib
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
import re
import tempfile
from threading import Thread
from urllib.parse import parse_qs, unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


def verify(receipt: Path) -> None:
    from playwright.sync_api import expect, sync_playwright

    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(ROOT / "site")))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    checks, errors = [], []
    result = {"scope": "anonymous local rendered page", "production_verified": False}
    try:
        with tempfile.TemporaryDirectory(prefix="commodity-browser-") as folder, sync_playwright() as browser_api:
            browser = browser_api.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1440, "height": 900}, accept_downloads=True)
            context.add_init_script("localStorage.setItem('theme','dark');localStorage.setItem('lang','en');localStorage.removeItem('themeAuto');")
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            def capture_review(name):
                image_dir = receipt.resolve().parent / "evidence" / receipt.stem
                image_dir.mkdir(parents=True, exist_ok=True)
                target = image_dir / (name + ".png")
                page.screenshot(path=str(target), full_page=False)
                result.setdefault("screenshots", []).append({
                    "file": str(target.relative_to(ROOT)) if target.is_relative_to(ROOT) else str(target),
                    "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                    "theme": page.evaluate("document.documentElement.dataset.theme"),
                    "lang": page.evaluate("document.documentElement.dataset.lang || document.documentElement.lang"),
                    "viewport": page.viewport_size,
                    "route": urlsplit(page.url).path + "#" + urlsplit(page.url).fragment,
                    "page_sha256": hashlib.sha256((ROOT / "site/commodities.html").read_bytes()).hexdigest(),
                })
            page.goto(f"http://127.0.0.1:{server.server_address[1]}/commodities.html", wait_until="load")
            page.locator("#cw-panel-overview").wait_for(state="visible")
            data = json.loads(page.locator("#cw-data").text_content())
            page.evaluate("document.fonts.ready")
            style = page.locator(".cw-hero h2").evaluate("(el)=>getComputedStyle(el).fontSize")
            radius = page.locator(".cw-focus").first.evaluate("(el)=>getComputedStyle(el).borderRadius")
            heading_token = page.locator("html").evaluate("el=>getComputedStyle(el).getPropertyValue('--fs-h1').trim()")
            assert style == heading_token, (style, heading_token)
            assert 24 <= float(style.removesuffix("px")) <= 32, style
            assert page.locator(".cw-hero p").first.evaluate("el=>parseFloat(getComputedStyle(el).fontSize)") < float(style.removesuffix("px"))
            assert radius == "14px", radius
            checks.append("compact headline resolves the canonical heading token above body text; panel radius resolves")
            entry = page.locator("#cw-brain-entry")
            entry.wait_for(state="visible")
            assert not page.locator("#mmb-boot").is_visible()
            brain_requests = []
            page.on("request", lambda request: brain_requests.append(request.url) if urlsplit(request.url).path.endswith("/mm_brain.js") else None)
            page.route("**/mm_brain.js*", lambda route: route.abort())
            entry.focus()
            page.keyboard.press("Enter")
            page.wait_for_function("document.querySelector('#cw-brain-status').textContent.includes('Could not open')")
            assert entry.get_attribute("aria-busy") == "false"
            checks.append("failed assistant load remains visible and retryable through the inline entry")
            page.unroute("**/mm_brain.js*")
            page.keyboard.press("Enter")
            page.locator("#mmb-panel.open").wait_for(state="visible")
            page.wait_for_function("document.querySelector('#mmb-panel').contains(document.activeElement)")
            assert not page.locator("#mmb-launch").is_visible()
            page.keyboard.press("Escape")
            page.wait_for_function("!document.querySelector('#mmb-panel').classList.contains('open')")
            assert entry.evaluate("(el)=>document.activeElement === el")
            request_count = len(brain_requests)
            page.keyboard.press("Enter")
            page.locator("#mmb-panel.open").wait_for(state="visible")
            page.wait_for_function("document.querySelector('#mmb-panel').contains(document.activeElement)")
            assert len(brain_requests) == request_count
            page.keyboard.press("Escape")
            page.wait_for_function("!document.querySelector('#mmb-panel').classList.contains('open')")
            assert entry.evaluate("(el)=>document.activeElement === el")
            checks.append("keyboard retry opens shared Brain, reuses mounted owner and returns focus on close")
            result["assistant_scope"] = "anonymous local widget; no prompt submitted"
            def check_unobstructed_returns():
                numbers = page.locator(".cw-hero-metric strong.cw-number:visible, #cw-panel-overview .cw-family-member .cw-number:visible, #cw-panel-overview .cw-focus-top .cw-number:visible, #cw-panel-overview .cw-context-tile .cw-number:visible")
                assert numbers.count() > 0, "No current Overview readings were selected for obstruction checks"
                for number in numbers.all():
                    number.scroll_into_view_if_needed()
                    assert number.evaluate("(el)=>{const r=el.getBoundingClientRect();const hit=document.elementFromPoint(r.left+r.width/2,r.top+r.height/2);return el===hit||el.contains(hit);}"), number.inner_text()
                return numbers.count()
            result["unobstructed_desktop_returns"] = check_unobstructed_returns()
            checks.append("overview numeric values remain unobstructed at desktop scroll positions")

            universe = page.locator("[data-cw-universe]")
            inspector = page.locator("[data-cw-inspector]")
            def open_brief(asset_id):
                page.locator("#cw-tab-explore").click()
                if not universe.is_visible():
                    page.locator("[data-cw-results-back]").click()
                if page.locator(f'[data-cw-universe-row="{asset_id}"]').is_hidden():
                    filters = page.locator(".cw-filter-details")
                    if filters.get_attribute("open") is None:
                        filters.locator("summary").click()
                    filters.locator("[data-cw-reset-filters]").click()
                page.locator(f'[data-cw-universe-row="{asset_id}"] .cw-name-cell [data-cw-open]').click()
                expect(page.locator(f'#cw-panel-explore [data-cw-asset="{asset_id}"]')).to_be_visible()

            def close_receipt_to(trigger):
                page.keyboard.press("Escape")
                expect(inspector).not_to_be_visible()
                expect(trigger).to_be_focused()

            page.locator("#cw-tab-explore").click()
            expect(universe).to_be_visible()
            rows = page.locator("[data-cw-universe-row]:visible")
            assert rows.count() == len(data["assets"]) == 17
            checks.append("Explore presents the complete 17-commodity published universe")
            selected_before = page.locator("[data-cw-pick]:checked").evaluate_all("els=>els.map(el=>el.value)")
            reading_categories = {key: 0 for key in ("positive", "negative", "zero", "unavailable")}
            state_names = {"up": ("Up", "向上"), "down": ("Down", "向下"), "flat": ("Flat", "持平"),
                           "bull": ("Positive", "偏强"), "bear": ("Negative", "偏弱"), "neutral": ("Neutral", "中性")}
            for locale in ("en", "zh"):
                page.evaluate("locale=>window.setLang(locale)", locale)
                for asset in data["assets"]:
                    row = page.locator(f'[data-cw-universe-row="{asset["id"]}"]')
                    for metric in ("1m", "20", "trend", "momentum"):
                        value = asset.get(metric) if metric in ("trend", "momentum") else asset["change_1m_pct"] if metric == "1m" else asset["returns"][metric]
                        if metric in ("trend", "momentum"):
                            reading = state_names.get(value, ("Unavailable", "暂不可用"))[locale == "zh"]
                        elif value is None:
                            reading = "Unavailable" if locale == "en" else "暂不可用"
                        else:
                            reading = f"{value:+.1f}%"
                        if locale == "en" and metric not in ("trend", "momentum"):
                            category = "unavailable" if value is None else "positive" if value > 0 else "negative" if value < 0 else "zero"
                            reading_categories[category] += 1
                        trigger = row.locator(f'.cw-reading-button[data-cw-inspect="{asset["id"]}:{metric}"]')
                        prefix = ("Inspect " if locale == "en" else "核查") + asset["label"][locale]
                        expect(trigger).to_have_accessible_name(re.compile(re.escape(prefix) + r".*" + re.escape(reading)))
            result["accessible_reading_cases"] = {"scope": "actual published universe; no values injected",
                                                  "numeric_cases_observed": reading_categories,
                                                  "numeric_cases_not_present": [key for key, count in reading_categories.items() if count == 0],
                                                  "languages": ["en", "zh"], "trend_and_momentum": True}
            checks.append("actual universe source buttons expose commodity, reading/sign and available state in both languages")
            page.evaluate("window.setLang('en')")
            gold_row = page.locator('[data-cw-universe-row="gold"]')
            gold_trigger = gold_row.locator('.cw-reading-button[data-cw-inspect="gold:1m"]')
            gold_trigger.click()
            expect(inspector).to_be_visible()
            expect(page.locator("[data-cw-inspector-close]")).to_be_focused()
            gold_asset = next(asset for asset in data["assets"] if asset["id"] == "gold")
            gold_value = gold_asset["change_1m_pct"]
            gold_reading = ("+" if gold_value > 0 else "") + f"{gold_value:.1f}%" if gold_value is not None else "Unavailable"
            expect(inspector.locator("[data-cw-inspector-value]")).to_have_text(gold_reading)
            expect(inspector.locator("[data-cw-inspector-facts]")).to_contain_text("Analysis snapshot")
            expect(inspector.locator("[data-cw-inspector-facts]")).to_contain_text(gold_asset["as_of"] or "Not recorded")
            expect(inspector.locator("[data-cw-inspector-facts] > div").filter(has_text="Price observation time")).to_contain_text("Not recorded")
            for key in ("Tab", "Shift+Tab", "Shift+Tab", "Tab"):
                page.keyboard.press(key)
                assert inspector.evaluate("el=>el.contains(document.activeElement)"), key
            capture_review("gold-source-desktop-dark-en")
            close_receipt_to(gold_trigger)
            checks.append("native source dialog preserves exact reading, independent clocks, modal focus and Escape return")

            page.locator('[data-cw-family="energy"]').click()
            page.locator("[data-cw-search]").fill("gold")
            expect(page.locator("[data-cw-universe-empty]")).to_be_visible()
            assert page.locator("[data-cw-universe-row]:visible").count() == 0
            assert set(page.locator("[data-cw-pick]:checked").evaluate_all("els=>els.map(el=>el.value)")) == set(selected_before)
            page.locator("[data-cw-universe-empty] [data-cw-reset-filters]").click()
            expect(page.locator("[data-cw-search]")).to_be_focused()
            assert rows.count() == len(data["assets"])
            checks.append("search and family intersect, preserve comparison selection and recover with visible focus")
            page.locator('[data-cw-layout="map"]').click()
            mapped = [asset for asset in data["assets"] if asset["trend"] in ("up", "flat", "down") and asset["momentum"] in ("bull", "neutral", "bear")]
            assert mapped, "Published universe has no qualified trend/momentum cell to exercise"
            for cell in page.locator("[data-cw-map-trend]").all():
                count = sum(asset["trend"] == cell.get_attribute("data-cw-map-trend") and asset["momentum"] == cell.get_attribute("data-cw-map-momentum") for asset in mapped)
                expect(cell.locator("[data-cw-map-count]")).to_have_text(str(count))
            picked = mapped[0]
            cell = page.locator(f'[data-cw-map-trend="{picked["trend"]}"][data-cw-map-momentum="{picked["momentum"]}"]')
            cell.focus()
            page.keyboard.press("Enter")
            expect(page.locator("[data-cw-table-view]")).to_be_visible()
            expect(page.locator("[data-cw-trend]")).to_have_value(picked["trend"])
            expect(page.locator("[data-cw-momentum]")).to_have_value(picked["momentum"])
            expected_ids = [asset["id"] for asset in mapped if asset["trend"] == picked["trend"] and asset["momentum"] == picked["momentum"]]
            assert rows.evaluate_all("els=>els.map(el=>el.dataset.cwUniverseRow)") == expected_ids
            expect(rows.first.locator("[data-cw-open]").first).to_be_focused()
            checks.append("signal map counts actual independent states and transfers keyboard focus to matching results")
            filters = page.locator(".cw-filter-details")
            if filters.get_attribute("open") is None:
                filters.locator("summary").click()
            filters.locator("[data-cw-reset-filters]").click()
            page.locator('[data-cw-family="precious"]').click()
            page.locator("[data-cw-search]").fill("gold")
            page.locator("[data-cw-sort]").select_option("return_desc")
            assert rows.count() == 1
            gold_row.locator(".cw-name-cell [data-cw-open]").click()
            expect(page.locator('#cw-panel-explore [data-cw-asset="gold"]')).to_be_visible()
            page.locator("[data-cw-results-back]").click()
            expect(gold_row.locator(".cw-name-cell [data-cw-open]")).to_be_focused()
            expect(page.locator("[data-cw-search]")).to_have_value("gold")
            expect(page.locator('[data-cw-family="precious"]')).to_have_attribute("aria-pressed", "true")
            expect(page.locator("[data-cw-sort]")).to_have_value("return_desc")
            assert set(page.locator("[data-cw-pick]:checked").evaluate_all("els=>els.map(el=>el.value)")) == set(selected_before)
            checks.append("brief and Back preserve search, family, sort, selection and the exact result focus")
            filters.locator("[data-cw-reset-filters]").click()
            page.locator("[data-cw-sort]").select_option("source")
            page.locator("#cw-tab-overview").click()
            page.locator("#cw-tab-explore").click()
            gold_trigger.click()
            page.go_back()
            expect(page.locator("#cw-panel-overview")).to_be_visible()
            expect(inspector).not_to_be_visible()
            expect(page.locator("#cw-tab-overview")).to_be_focused()
            checks.append("browser Back dismisses an open receipt and restores focus to the current visible route")
            page.locator('#cw-panel-overview .cw-focus[data-cw-open="oil"]').click()
            primary_number = page.locator('[data-cw-asset="oil"] .cw-detail-price strong .cw-number')
            assert primary_number.evaluate("(el)=>parseFloat(getComputedStyle(el).fontSize)") >= 30
            return_number = page.locator('[data-cw-asset="oil"] .cw-return strong .cw-number').first
            assert return_number.evaluate("(el)=>parseFloat(getComputedStyle(el).fontSize)") >= 22
            checks.append("primary and session returns retain numeric hierarchy instead of caption styling")
            physical = page.locator("#cw-physical-oil")
            assert physical.is_visible()
            assert data["physical"]["headline"]["en"] in page.locator("#cw-physical-title").inner_text()
            assert data["physical"]["clock"]["en"] in physical.locator(".cw-physical-clock").inner_text()
            assert data["physical"]["downstream"]["en"] in physical.locator(".cw-physical-consequences").inner_text()
            assert physical.locator(".cw-stock").count() == len(data["physical"]["stocks"]) > 0
            physical.locator("summary").click()
            for stock in data["physical"]["stocks"]:
                for date in (stock["anomaly"]["reference"]["start"], stock["change_4w"]["window_start"], stock["change_4w"]["window_end"]):
                    if date:
                        assert date in physical.inner_text()
            physical.locator("summary").click()
            checks.append("exact published physical headline, clocks, dates and downstream context")
            physical_name_checks = 0
            for locale in ("en", "zh"):
                page.evaluate("locale=>window.setLang(locale)", locale)
                units = {"million_barrels": "million bbl" if locale == "en" else "百万桶",
                         "seasonal_z": "z", "days": "days" if locale == "en" else "天"}
                for stock in data["physical"]["stocks"]:
                    observations = ((stock["id"] + "_stocks_mb", stock["level"], ".1f"),
                                    (stock["id"] + "_z", stock["anomaly"], "+.2f"),
                                    (stock["id"] + "_chg_4w_mb", stock["change_4w"], "+.1f"),
                                    ({"crude": "days_supply", "gasoline": "gasoline_days", "distillate": "distillate_days"}[stock["id"]], stock["days_cover"], ".1f"))
                    for key, observation, number_format in observations:
                        trigger = physical.locator(f'[data-cw-physical-inspect="{key}"]')
                        value = observation["value"]
                        reading = format(value, number_format) + " " + units[observation["unit"]] if value is not None else "Unavailable" if locale == "en" else "暂不可用"
                        prefix = ("Inspect " if locale == "en" else "核查") + stock["label"][locale]
                        expect(trigger).to_have_accessible_name(re.compile(re.escape(prefix) + r".*" + re.escape(reading)))
                        physical_name_checks += 1
                        # Each of the four receipt types is exercised on the first actual stock.
                        if stock is data["physical"]["stocks"][0]:
                            trigger.click()
                            expected = f'{value:g} {units[observation["unit"]]}' if value is not None else "Unavailable" if locale == "en" else "暂不可用"
                            expect(inspector.locator("[data-cw-inspector-value]")).to_have_text(expected)
                            facts = inspector.locator("[data-cw-inspector-facts]")
                            expect(facts).to_contain_text("Observation week ending" if locale == "en" else "观察周截至")
                            expect(facts).to_contain_text(observation["observation_at"] or ("Not recorded" if locale == "en" else "未记录"))
                            expect(facts).to_contain_text(data["as_of"])
                            if observation.get("release_at") is None:
                                expect(facts.locator("div").filter(has_text="Publication time" if locale == "en" else "发布时间")).to_contain_text("Not recorded" if locale == "en" else "未记录")
                            if locale == "en" and key.endswith("_z"):
                                capture_review("physical-seasonal-source-desktop-dark-en")
                            close_receipt_to(trigger)
            result["physical_accessible_name_checks"] = physical_name_checks
            checks.append("stock, seasonal deviation, four-week change and days-cover names retain actual values/units in both languages")
            checks.append("all four physical receipt types preserve observation week, analysis date, unknown release clock and Escape focus")
            page.evaluate("window.setLang('en')")
            page.locator('[data-cw-hypothesis="oil"] input[value="supply"]').check()
            page.locator("#cw-tab-relationships").click()
            assert "Supply disruption" in page.locator("#cw-investigation-title").inner_text()
            assert "has not established" in page.locator("#cw-investigation-state").inner_text()
            assert page.locator('.cw-physical-summary[data-cw-chain-asset="oil"]').is_visible()
            page.locator("#cw-panel-relationships [data-cw-go-physical]:visible").click()
            assert page.locator("#cw-panel-explore").is_visible()
            page.wait_for_function("document.activeElement.id === 'cw-physical-oil'")
            assert page.locator('[data-cw-hypothesis="oil"] input[value="supply"]').is_checked()
            page.locator("#cw-tab-relationships").click()
            checks.append("physical evidence navigation preserves the selected explanation and keyboard focus")
            supply = page.locator("#cw-investigation-mechanism").inner_text()
            page.locator("#cw-investigation-tests summary").click()
            assert page.locator("#cw-investigation-support").is_visible()
            assert page.locator("#cw-investigation-invalidate").is_visible()
            checks.append("oil supply selection carries a conditional mechanism and evidence questions")
            open_brief("oil")
            page.locator('[data-cw-hypothesis="oil"] input[value="demand"]').check()
            page.locator("#cw-tab-relationships").click()
            assert "Demand expansion" in page.locator("#cw-investigation-title").inner_text()
            assert page.locator("#cw-investigation-mechanism").inner_text() != supply
            checks.append("changing explanation changes the investigation")
            company_links = page.locator('[data-cw-chain-asset="oil"] .cw-cohorts a')
            result["available_company_continuations"] = company_links.count()
            if company_links.count():
                href = company_links.first.get_attribute("href")
                assert href, href
                target = urlsplit(href)
                params = parse_qs(target.query)
                assert target.scheme == "https" and target.netloc == "app.mastermind-x.com"
                assert target.path == "/analysis"
                assert set(params) == {"symbol", "page", "mo_from", "mo_chain", "mo_channel", "mo_asof", "mo_security"}, params
                assert params["page"] == ["intelligence"] and params["mo_from"] == ["transmission"]
                assert params["symbol"][0] and params["mo_security"][0].startswith("SEC:")
                assert company_links.first.get_attribute("target") == "_blank"
                result["company_continuation_href"] = href
                checks.append("company continuation retains its verified identity and opens separately")
            page.locator("#cw-tab-research").click()
            form = page.locator("#cw-research-form")
            form.locator('[name="window_sessions"]').select_option("20")
            assert page.locator("[data-cw-note-window]").inner_text() == "20 trading sessions"
            assert all(not label.is_visible() for label in page.locator(".cw-step-title .l-zh").all())
            checks.append("research headings show only the chosen language and context follows the draft lookback")
            form.locator('[name="threshold"]').fill("0")
            form.locator('[name="expires_on"]').fill("2099-01-01")
            with page.expect_download() as download_info:
                form.locator('button[type="submit"]').click()
            downloaded = Path(folder) / "condition.json"
            download_info.value.save_as(downloaded)
            draft = json.loads(downloaded.read_text())
            assert draft["asset"] == "oil" and draft["hypothesis"] == "demand"
            assert draft["threshold"] == 0 and draft["metric_contract"]["field"] == "velocity.r20"
            assert draft["monitoring_active"] is False and draft["effect"] == "export_only"
            assert draft["as_saved_evidence"]["physical"] == data["physical"]
            assert draft["as_saved_evidence"]["physical"]["point_in_time_verified"] is False
            assert downloaded.stat().st_size <= 131072
            checks.append("real research export retains dated physical evidence and fits its import limit")
            checks.append("real download preserves exact condition, hypothesis and inactive monitoring")
            result["research_as_of"] = draft["as_of"]
            result["workspace_fingerprint"] = draft["snapshot_fingerprint"]
            # A separate browser context has no page-local draft map or prior storage.
            fresh_context = browser.new_context(viewport={"width": 1440, "height": 900}, accept_downloads=True)
            fresh_context.add_init_script("localStorage.setItem('theme','dark');localStorage.setItem('lang','en');")
            fresh = fresh_context.new_page()
            fresh.on("pageerror", lambda error: errors.append(str(error)))
            fresh.goto(f"http://127.0.0.1:{server.server_address[1]}/commodities.html", wait_until="load")
            fresh.locator("#cw-tab-research").click()
            fresh_form = fresh.locator("#cw-research-form")
            assert fresh_form.locator('[name="threshold"]').input_value() == ""
            assert fresh_form.locator('[name="window_sessions"]').input_value() == ""
            fresh.locator("#cw-import-file").set_input_files(downloaded)
            fresh.wait_for_function("document.querySelector('#cw-export-status').textContent.includes('Draft reopened')")
            for field in ("operator", "threshold", "expires_on", "window_sessions"):
                assert fresh_form.locator(f'[name="{field}"]').input_value() == str(draft[field])
            assert "Demand expansion" in fresh.locator("#cw-research-hypothesis").inner_text()
            with fresh.expect_download() as reopened_info:
                fresh_form.locator('button[type="submit"]').click()
            reopened = Path(folder) / "condition-fresh-document.json"
            reopened_info.value.save_as(reopened)
            assert json.loads(reopened.read_text()) == draft
            result["fresh_document_import"] = {"separate_browser_context": True, "exact_export_round_trip": True,
                                               "threshold": 0, "window_sessions": 20, "monitoring_active": False}
            checks.append("exported research restores in a fresh document with exact condition and complete evidence")
            expired = dict(draft, expires_on=draft["as_of"])
            expired_file = Path(folder) / "condition-expired.json"
            expired_file.write_text(json.dumps(expired))
            fresh.locator("#cw-import-file").set_input_files(expired_file)
            fresh.wait_for_function("document.querySelector('#cw-export-status').textContent.includes('expiry date has passed')")
            assert "no monitoring is active" in fresh.locator("#cw-export-status").inner_text()
            assert fresh_form.locator('[name="expires_on"]').input_value() == draft["as_of"]
            checks.append("an expired historical draft reopens with an explicit inactive expiry disclosure")
            fresh_context.close()
            page.locator("#cw-tab-relationships").click()
            page.locator("[data-cw-relationship-asset]").select_option("gold")
            assert "Gold" in page.locator("#cw-investigation-title").inner_text()
            assert "Supply disruption" not in page.locator("#cw-investigation-title").inner_text()
            assert not page.locator('.cw-physical-summary[data-cw-chain-asset="oil"]').is_visible()
            assert not page.locator("#cw-physical-oil").is_visible()
            checks.append("changing commodity removes the oil explanation and petroleum claims")
            assert page.locator('.cw-physical-summary[data-cw-chain-asset="gold"]').is_visible()
            open_brief("gold")
            gold_physical = page.locator("#cw-gold-physical")
            assert gold_physical.is_visible()
            assert "close-based proxy" in gold_physical.locator(".cw-eyebrow").inner_text().lower()
            assert gold_physical.locator(".cw-gold-value").inner_text() == f'{data["gold_physical"]["premium_pct"]:+.2f}%'
            assert data["gold_physical"]["clock"] in gold_physical.locator(".cw-physical-clock").inner_text()
            assert "Official benchmark unavailable" in gold_physical.locator(".cw-physical-clock").inner_text()
            gold = next(asset for asset in data["assets"] if asset["id"] == "gold")
            assert gold["read"]["headline"]["en"] in page.locator('[data-cw-asset="gold"] .cw-reading').inner_text()
            checks.append("Gold proxy retains its exact published timestamp, percentage units and price interpretation")

            page.locator("#cw-tab-compare").click()
            page.locator("[data-cw-window]").select_option("60")
            selected = page.locator("[data-cw-compare]:checked").evaluate_all("els=>els.map(el=>el.value)")
            values = [asset["returns"]["60"] for asset in data["assets"] if asset["id"] in selected]
            scale = max(abs(value) for value in values if value is not None)
            for asset in data["assets"]:
                if asset["id"] not in selected:
                    continue
                row = page.locator(f'[data-cw-compare-plot="{asset["id"]}"]')
                value = asset["returns"]["60"]
                mark = row.locator("[data-cw-plot-mark]")
                if value is None:
                    assert not mark.is_visible()
                else:
                    fraction = mark.bounding_box()["width"] / row.locator(".cw-bar").bounding_box()["width"]
                    assert abs(fraction - (abs(value) / scale / 2 if scale else 0)) < .002
            checks.append("comparison window changes actual bar geometry on one shared signed scale")
            selected_asset = next(asset for asset in data["assets"] if asset["id"] in selected)
            comparison_trigger = page.locator(f'[data-cw-current-inspect="{selected_asset["id"]}"]')
            selected_value = selected_asset["returns"]["60"]
            selected_reading = ("+" if selected_value > 0 else "") + f"{selected_value:.1f}%" if selected_value is not None else "Unavailable"
            expect(comparison_trigger).to_have_accessible_name(re.compile(r"60.*" + re.escape(selected_reading)))
            comparison_trigger.click()
            expect(inspector.locator("[data-cw-inspector-label]")).to_have_text("60-session price change")
            expect(inspector.locator("[data-cw-inspector-value]")).to_have_text(selected_reading)
            close_receipt_to(comparison_trigger)
            assert page.locator(f'[data-cw-compare-row="{selected_asset["id"]}"] [data-cw-inspect="{selected_asset["id"]}:1m"]').is_visible()
            checks.append("selected-window receipt follows 60 sessions while the distinct one-month column remains available")

            page.locator("#cw-tab-research").click()
            page.locator("#cw-import-file").set_input_files(downloaded)
            page.wait_for_function("document.querySelector('#cw-export-status').textContent.includes('Draft reopened')")
            page.locator("#cw-tab-relationships").click()
            assert "Demand expansion" in page.locator("#cw-investigation-title").inner_text()
            assert page.locator("[data-cw-relationship-asset]").input_value() == "oil"
            checks.append("real file import restores the same investigation")
            page.locator("#cw-tab-research").click()
            page.go_back()
            page.locator("#cw-panel-relationships").wait_for(state="visible")
            assert "Demand expansion" in page.locator("#cw-investigation-title").inner_text()
            checks.append("browser history preserves investigation context")
            page.locator("[data-cw-relationship-asset]").select_option("corn")
            assert "Corn" in page.locator("#cw-investigation-title").inner_text()
            assert not page.locator("#cw-investigation-tests").is_visible()
            assert page.locator("#cw-investigation-support").text_content() == ""
            checks.append("partial coverage clears stale support and invalidation text")
            page.evaluate("window.setLang('zh')")
            page.set_viewport_size({"width": 390, "height": 844})
            page.locator("[data-cw-relationship-asset]").select_option("oil")
            assert "需求" in page.locator("#cw-investigation-title").inner_text()
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
            checks.append("Chinese mobile investigation retains meaning without horizontal overflow")
            page.evaluate("window.setTheme('light')")
            page.wait_for_timeout(1400)
            assert page.evaluate("document.documentElement.dataset.theme") == "light"
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
            checks.append("light mobile view retains the investigation and layout")
            page.locator("#cw-panel-relationships [data-cw-go-physical]:visible").click()
            assert data["physical"]["headline"]["zh"] in page.locator("#cw-physical-title").inner_text()
            for card in page.locator("#cw-physical-oil .cw-stock").all():
                card.scroll_into_view_if_needed()
                assert card.locator(".cw-stock-level").is_visible()
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
            checks.append("Chinese mobile physical evidence retains all stock cards and dates without page overflow")

            page.locator("#cw-tab-overview").click()
            assert page.locator(".cw-hero-metric strong.cw-number").first.evaluate("el=>parseFloat(getComputedStyle(el).fontSize)") >= 22
            result["unobstructed_mobile_returns"] = check_unobstructed_returns()
            assert not page.locator("#mmb-launch").is_visible()
            checks.append("overview numeric values remain unobstructed at mobile scroll positions")
            page.goto(f"http://127.0.0.1:{server.server_address[1]}/commodities.html#cw/research/gold", wait_until="load")
            page.reload(wait_until="load")
            page.locator("#cw-panel-research").wait_for(state="visible")
            tab_box = page.locator("#cw-tab-research").bounding_box()
            strip_box = page.locator("[data-cw-tablist]").bounding_box()
            assert tab_box["x"] >= strip_box["x"] - 1
            assert tab_box["x"] + tab_box["width"] <= strip_box["x"] + strip_box["width"] + 1
            page.locator("#cw-tab-compare").click()
            editor = page.locator("[data-cw-compare-editor]")
            assert editor.get_attribute("open") is None
            editor.locator("summary").click()
            picks = page.locator(".cw-compare-picks").bounding_box()
            for choice in page.locator(".cw-compare-picks label").all():
                box = choice.bounding_box()
                assert box["y"] + box["height"] <= picks["y"] + picks["height"] + 1
            checks.append("mobile direct routes reveal the active tab and comparison choices are not clipped")
            page.locator("[data-cw-finish-selection]").click()
            assert editor.get_attribute("open") is None
            expect(editor.locator("summary")).to_be_focused()
            checks.append("Done collapses the selection editor and returns focus to its summary")
            responsive_cells = []
            for width in (320, 768):
                page.set_viewport_size({"width": width, "height": 900})
                for locale in ("en", "zh"):
                    page.evaluate("locale=>window.setLang(locale)", locale)
                    for theme in ("dark", "light"):
                        page.evaluate("theme=>window.setTheme(theme)", theme)
                        for tab in ("overview", "explore", "compare"):
                            page.locator("#cw-tab-" + tab).click()
                            page.evaluate("document.fonts.ready")
                            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), (width, locale, theme, tab)
                            if tab == "explore":
                                assert rows.count() == len(data["assets"])
                                source = gold_row.locator('.cw-reading-button[data-cw-inspect="gold:1m"]')
                                source.click()
                                box = inspector.bounding_box()
                                assert box and box["x"] >= -1 and box["x"] + box["width"] <= width + 1, (width, locale, theme, box)
                                if width == 320:
                                    assert abs(box["x"]) <= 1 and abs(box["width"] - width) <= 1, (locale, theme, "phone receipt must occupy full width", box)
                                assert inspector.evaluate("el=>el.scrollWidth <= el.clientWidth + 1"), (width, locale, theme, "inspector contents")
                                if width == 320 and locale == "zh" and theme == "light":
                                    capture_review("gold-source-320-light-zh")
                                close_receipt_to(source)
                            responsive_cells.append({"width": width, "locale": locale, "theme": theme, "view": tab})
            result["responsive_layout_checks"] = responsive_cells
            checks.append("320px and 768px Overview, universe, Compare and source dialog fit in both themes and languages")
            assert not errors, errors
            checks.append("no uncaught browser errors")
            context.close()

            # A separate intercepted origin tests the existing cross-product URL contract.
            # It serves local bytes and a destination stub; it is not a Terminal login or deployment proof.
            fixture_context = browser.new_context(viewport={"width": 1440, "height": 900})
            fixture_context.add_init_script("localStorage.setItem('theme','dark');localStorage.setItem('lang','en');")
            site_root = (ROOT / "site").resolve()
            def serve_fixture(route):
                target = urlsplit(route.request.url)
                if target.scheme == "https" and target.netloc == "www.mastermind-x.com":
                    asset = (site_root / unquote(target.path).lstrip("/")).resolve()
                    if asset.is_relative_to(site_root) and asset.is_file():
                        route.fulfill(path=str(asset), content_type=mimetypes.guess_type(str(asset))[0] or "application/octet-stream")
                        return
                elif target.scheme == "https" and target.netloc == "app.mastermind-x.com" and target.path == "/analysis":
                    route.fulfill(status=200, content_type="text/html", body="<title>Company destination fixture</title>")
                    return
                route.abort()
            fixture_context.route("**/*", serve_fixture)
            fixture = fixture_context.new_page()
            fixture.on("pageerror", lambda error: errors.append(str(error)))
            initial = "https://www.mastermind-x.com/commodities.html#cw/relationships/gold?window=60&compare=oil%2Cgold&hypothesis=rates"
            fixture.goto(initial, wait_until="load")
            fixture.locator("#cw-panel-relationships").wait_for(state="visible")
            company = fixture.locator('[data-cw-chain-asset="gold"] [data-cw-company-href]').first
            original = parse_qs(urlsplit(company.get_attribute("data-cw-company-href")).query)
            href = company.get_attribute("href")
            params = parse_qs(urlsplit(href).query)
            assert set(params) == set(original) | {"from", "ret"}, params
            assert all(params[key] == value for key, value in original.items())
            assert params["from"] == ["macro"] and params["ret"] == [initial]
            company.locator("xpath=ancestor::details[1]").locator(":scope > summary").click()
            with fixture.expect_popup() as opened:
                company.click()
            destination = opened.value
            destination.wait_for_load_state("load")
            assert destination.url == href
            checks.append("first-party company link opens with unchanged identity fields and exact Macro return")
            destination.goto(params["ret"][0], wait_until="load")
            destination.locator("#cw-panel-relationships").wait_for(state="visible")
            explanation = next(item for item in data["hypotheses"]["gold"] if item["id"] == "rates")
            assert explanation["label"]["en"] in destination.locator("#cw-investigation-title").inner_text()
            assert destination.locator('[data-cw-hypothesis="gold"] input[value="rates"]').is_checked()
            assert destination.locator("[data-cw-window]").input_value() == "60"
            assert destination.locator("[data-cw-compare]:checked").count() == 2
            checks.append("decoded company return restores commodity, tab, window, comparisons and hypothesis")
            result["company_return_transport"] = {"scope": "intercepted first-party-origin fixture; authenticated Terminal unverified",
                                                  "requested_href": href, "return_url": params["ret"][0], "restored": True}
            assert not errors, errors
            fixture_context.close()
            browser.close()
        result["passed"] = True
    except Exception as exc:
        result["passed"] = False
        result["failure"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        server.shutdown()
        server.server_close()
        result["checks"] = checks
        result["browser_errors"] = errors
        receipt.parent.mkdir(parents=True, exist_ok=True)
        receipt.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
        print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, required=True)
    verify(parser.parse_args().receipt)
