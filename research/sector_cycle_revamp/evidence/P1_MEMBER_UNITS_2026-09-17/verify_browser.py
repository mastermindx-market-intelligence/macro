"""Verify the actual local P1 page in all eight display states; never publishes."""
from pathlib import Path
from hashlib import sha256
import argparse
import json
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[4]
EVIDENCE = Path(__file__).resolve().parent


def verify(site: Path, out: Path = EVIDENCE) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    companion = site / "basketdata/member_observations.json"
    bundle = json.loads(companion.read_text())
    group = bundle["groups"]["ai_infra"]
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            for lang in ("en", "zh"):
                for theme in ("dark", "light"):
                    for width in (1440, 390):
                        context = browser.new_context(viewport={"width": width, "height": 1000})
                        page = context.new_page()
                        errors = []
                        page.on("pageerror", lambda exc: errors.append(str(exc)))
                        page.add_init_script("localStorage.setItem('lang',"+json.dumps(lang)+");localStorage.setItem('theme',"+json.dumps(theme)+");")
                        page.goto((site / "basket/ai_infra.html").as_uri(), wait_until="load", timeout=20000)
                        page.locator("#mo-metric").wait_for(timeout=10000)
                        original = page.evaluate("JSON.stringify(DETAIL.member_observations)")
                        assert page.locator("html").get_attribute("data-lang") == lang
                        assert page.locator("html").get_attribute("data-theme") == theme
                        page.select_option("#mo-metric", "raw_daily_change")
                        raw = page.locator("#mo-rows tr").first.inner_text()
                        assert "%" in raw
                        page.select_option("#mo-metric", "benchmark_relative_daily_change")
                        relative = page.locator("#mo-rows tr").first.inner_text()
                        first_key = group["member_keys"][0]
                        first_relative = group["members"][first_key]["metrics"]["benchmark_relative_daily_change"]
                        if first_relative["value"] is None:
                            assert ("Unavailable" if lang == "en" else "不可用") in relative, relative
                            assert "%" not in relative
                        else:
                            assert ("pp" if lang == "en" else "个百分点") in relative and "%" not in relative, relative
                        page.select_option("#mo-metric", "strict_trend_200")
                        assert page.locator("#mo-rows tr").count() == group["member_count"]
                        page.select_option("#mo-filter", "unavailable")
                        assert page.locator("#mo-rows tr").count() == 1
                        missing = page.locator("#mo-rows").inner_text()
                        assert "CBRS" in missing and ("Unavailable" if lang == "en" else "不可用") in missing
                        page.locator(".mo-table-wrap").scroll_into_view_if_needed()
                        geometry = page.locator(".mo-table-wrap").evaluate("""el=>{const w=el.querySelector('.why').getBoundingClientRect(),r=el.getBoundingClientRect();return {scroll_width:el.scrollWidth,client_width:el.clientWidth,why_left:w.left,why_right:w.right,why_top:w.top,why_bottom:w.bottom,left:r.left,right:r.right,top:r.top,bottom:r.bottom}}""")
                        assert geometry["scroll_width"] <= geometry["client_width"] + 1
                        assert geometry["left"] <= geometry["why_left"] <= geometry["why_right"] <= geometry["right"] + 1
                        assert geometry["top"] <= geometry["why_top"] <= geometry["why_bottom"] <= geometry["bottom"] + 1
                        assert page.get_by_role("table").filter(has=page.locator("#mo-rows")).count() == 1
                        missing_image = out / f"member-unavailable-{lang}-{theme}-{width}.png"
                        page.locator(".mo-band").screenshot(path=str(missing_image))
                        page.select_option("#mo-filter", "all")
                        page.fill("#mo-search", "CBRS")
                        assert page.locator("#mo-rows tr").count() == 1
                        assert page.evaluate("JSON.stringify(DETAIL.member_observations)") == original
                        page.fill("#mo-search", "")
                        page.select_option("#mo-metric", "benchmark_relative_daily_change")
                        band = page.locator(".mo-band")
                        box = band.bounding_box()
                        assert box is not None and box["width"] <= width
                        assert not errors, errors
                        image = out / f"member-evidence-{lang}-{theme}-{width}.png"
                        band.screenshot(path=str(image))
                        result = {"lang": lang, "theme": theme, "viewport": width, "raw": raw, "relative": relative,
                                  "catalogue": group["member_count"], "relative_observed": group["metrics"]["benchmark_relative_daily_change"]["denominator"], "strict_200_observed": group["metrics"]["strict_trend_200"]["denominator"],
                                  "strict_200_unavailable": 1, "missing_member": "CBRS", "source_data_unchanged": True,
                                  "script_errors": errors, "section_width": box["width"], "missing_reason_geometry": geometry,
                                  "screenshot": image.name, "screenshot_sha256": sha256(image.read_bytes()).hexdigest(),
                                  "missing_screenshot": missing_image.name, "missing_screenshot_sha256": sha256(missing_image.read_bytes()).hexdigest()}
                        results.append(result)
                        print("REAL_BROWSER_STATE", lang, theme, width, "PASS", flush=True)
                        context.close()
        finally:
            browser.close()
    receipt = {"scope": "local real-input rendered page; not deployed or authenticated production proof",
               "template_sha256": sha256((ROOT / "templates/basket_detail.html.j2").read_bytes()).hexdigest(),
               "observation_digest": bundle["projection_digest"], "companion_bytes": companion.stat().st_size,
               "numeric_discriminator": "See controlled positive benchmark comparison in P1_BENCHMARK_PAIR page_proof.json; equal rounded real values are not used as subtraction proof.",
               "states": results}
    (out / "receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    assert len(results) == 8
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, default=EVIDENCE)
    args = parser.parse_args()
    verify(args.site_root, args.output_root)
