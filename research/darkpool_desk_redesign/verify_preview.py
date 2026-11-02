"""Exercise the offline Dark Pool design reference in a real browser."""
import argparse
import csv
from pathlib import Path
from playwright.sync_api import sync_playwright

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--chrome")
    parser.add_argument("--shots", type=Path)
    args = parser.parse_args()
    base = Path(__file__).resolve().parent
    if args.shots:
        args.shots.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=args.chrome)
        tested = 0
        for width, height in [(1440, 960), (768, 1024), (390, 844), (320, 700)]:
            for lang in ["en", "zh"]:
                for theme in ["dark", "light"]:
                    page = browser.new_page(viewport={"width": width, "height": height})
                    errors = []
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    page.goto((base / "preview.html").as_uri())
                    if lang == "zh":
                        page.locator("#lang").click()
                    if theme == "light":
                        page.locator("#theme").click()
                    assert page.locator("html").get_attribute("lang") == lang
                    assert page.locator("html").get_attribute("data-theme") == theme
                    assert page.locator("#map [data-tk]").count() == 25
                    assert page.locator(".ticker").inner_text() == "SHW"
                    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), (width, lang)
                    if args.shots and (width, lang, theme) in [(1440,"en","dark"),(390,"en","light")]:
                        page.screenshot(path=str(args.shots / f"desk-{width}-{theme}.png"))
                    page.locator('#map [data-tk="CIEN"]').focus()
                    page.keyboard.press("Enter")
                    assert page.locator(".ticker").inner_text() == "CIEN"
                    if width <= 670:
                        assert page.locator("#inspector").evaluate("e => document.activeElement === e")
                        page.locator("#back").click()
                        assert page.evaluate("document.activeElement.dataset.tk") == "CIEN"
                    assert "259" in page.locator(".stats").inner_text()
                    page.locator('[data-scope="above"]').click()
                    assert page.locator("#map [data-tk]").count() == 27
                    assert page.locator('#map [data-tk="APH"]').count() == 1
                    page.locator('[data-scope="unusual"]').click()
                    assert page.locator('#map [data-tk="APH"]').count() == 0
                    page.locator('[data-group="flat"]').click()
                    assert page.locator(".rows tbody tr").count() == 3
                    page.locator('[data-scope="older"]').click()
                    page.locator("#query").fill("ETHA")
                    assert page.locator(".rows tbody tr").count() == 1
                    page.locator('#list [data-tk="ETHA"]').click()
                    assert page.locator(".rows tbody tr td").nth(1).inner_text() == "—"
                    assert page.locator(".metricrow b").first.inner_text() == "—"
                    assert page.locator(".trendwrap svg").count() == 0
                    with page.expect_download() as download:
                        page.locator("#csv").click()
                    assert download.value.suggested_filename.endswith("-older.csv")
                    csv_text = Path(download.value.path()).read_text()
                    record = next(csv.DictReader(csv_text.splitlines()))
                    assert (record["ticker"], record["asof"]) == ("ETHA","2026-08-04")
                    assert all(record[k] == "" for k in ("participation","participation_z","pattern","ats_frac","venue_week"))
                    assert record["price_change_pct"] != ""
                    page.locator("#query").fill("NO-MATCH-XYZ")
                    assert page.locator("#clear").count() == 1
                    page.locator("#clear").click()
                    assert page.locator(".rows tbody tr").count() == 8
                    page.locator('[data-page="1"]').click()
                    assert "9–16" in page.locator(".pager").inner_text()
                    page.locator("#order").select_option("ticker")
                    assert page.locator(".rows tbody tr button").first.inner_text() == "AEP"
                    page.locator('[data-tab="venues"]').click()
                    assert page.locator(".venuerow").count() == 8
                    assert "2026-09-21" in page.locator("#content").inner_text()
                    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                    page.locator('[data-tab="method"]').click()
                    assert page.locator("#content li").count() == 6
                    page.locator("#findStock").click()
                    assert page.locator("#query").evaluate("e => document.activeElement === e")
                    assert page.locator('[data-scope="all"]').get_attribute("aria-pressed") == "true"
                    page.locator(".adv summary").click()
                    page.locator('[data-preset="rising"]').click()
                    assert page.locator("#minShare").input_value() == "2"
                    assert page.locator("#advTrend").input_value() == "rising"
                    page.locator('[data-preset="short"]').click()
                    assert page.locator('[data-preset="short"]').get_attribute("aria-pressed") == "true"
                    page.locator("#resetAdvanced").click()
                    assert page.locator("#minShare").input_value() == ""
                    assert not errors, errors
                    page.close()
                    tested += 1
                    print(f"PASS {width} {lang} {theme}", flush=True)
        browser.close()
        print(f"{tested}/16 desktop, tablet and phone configurations passed.")

if __name__ == "__main__":
    main()
