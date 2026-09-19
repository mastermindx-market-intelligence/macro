"""Local real-input and explicitly controlled benchmark-gap consumer proof.

Never writes to production data/site roots. Browser gap inputs are test fixtures.
"""
from hashlib import sha256
import json
import os
from pathlib import Path
import runpy
import sys
import tempfile
from time import perf_counter
import jinja2
import pytest
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
from engine import group_pulse as GP
from engine import group_member_observations as GMO
from scripts import build_theme_detail as BTD
from scripts import check_group_member_observations as CHECK

EVIDENCE = Path(__file__).resolve().parent

def build(result, site, data):
    site.mkdir(parents=True)
    for asset in (ROOT / "site").iterdir():
        if asset.name not in {"basket", "basketdata"}:
            (site / asset.name).symlink_to(asset)
    (site / "basketdata").mkdir()
    assert not result["member_observation_errors"], result["member_observation_errors"]
    pulse = GP.site_payload_bytes(result["payload"])
    bundle = GMO.assemble_member_bundle(
        groups=result["member_observation_groups"], as_of=result["as_of"],
        generated_at=next(iter(result["payload"].values()))["generated_at"],
        source_receipts=result["source_receipts"], legacy_pulse_bytes=pulse,
    )
    (site / "basketdata/pulse.json").write_bytes(pulse)
    GP.write_member_observations_artifact(bundle, site)
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(ROOT / "templates")), autoescape=False)
    count = BTD.build_detail_pages(data, site, env, "us")
    checked = CHECK.evaluate(site)
    assert checked["ok"], checked["errors"]
    return bundle, {"pages": count, "groups": checked["group_count"],
                    "as_of": result["as_of"], "projection_digest": bundle["projection_digest"],
                    "companion_bytes": (site / "basketdata/member_observations.json").stat().st_size,
                    "rendered_detail_bytes": sum(p.stat().st_size for p in (site / "basket").glob("*.html"))}

def main():
    receipt = {"scope": "local real-input build plus controlled benchmark-gap browser test; not production acceptance",
               "group_pulse_sha256": sha256((ROOT / "engine/group_pulse.py").read_bytes()).hexdigest(),
               "template_sha256": sha256((ROOT / "templates/basket_detail.html.j2").read_bytes()).hexdigest()}
    with tempfile.TemporaryDirectory(prefix="mmx-p1-benchmark-pages-") as directory:
        temporary = Path(directory)
        start = perf_counter()
        real = GP.compute()
        compute_s = perf_counter() - start
        source_data = json.loads((ROOT / "site/basketdata/baskets.json").read_text())
        start = perf_counter()
        _, receipt["real_input_generation"] = build(real, temporary / "real/site", source_data)
        receipt["real_input_generation"].update({"compute_seconds": round(compute_s, 3),
                                                "render_and_validate_seconds": round(perf_counter() - start, 3),
                                                "timing_scope": "one current local build, not incremental overhead or production budget proof"})
        print("REAL_GENERATION", json.dumps(receipt["real_input_generation"]), flush=True)
        real_browser = runpy.run_path(str(ROOT / "research/sector_cycle_revamp/evidence/P1_MEMBER_UNITS_2026-09-17/verify_browser.py"))
        real_browser["verify"](temporary / "real/site")
        tests = runpy.run_path(str(ROOT / "tests/test_group_member_observations.py"))
        with pytest.MonkeyPatch.context() as patch:
            controlled, *_ = tests["_compute_with_observed_benchmark"](patch, temporary, "current_missing")
        group_id = tests["GROUP_ID"]
        data = {"baskets": [{"id": group_id, "name": "Controlled benchmark-gap verification fixture", "members": []}],
                "theme_intel": {"as_of": controlled["as_of"], "themes": []}}
        site = temporary / "controlled/site"
        bundle, receipt["controlled_generation"] = build(controlled, site, data)
        group = bundle["groups"][group_id]
        observed_raw = group["metrics"]["raw_daily_change"]["denominator"]
        assert observed_raw > 0
        assert group["metrics"]["benchmark_relative_daily_change"]["denominator"] == 0
        with pytest.MonkeyPatch.context() as patch:
            positive, _, _, benchmark, _ = tests["_compute_with_observed_benchmark"](patch, temporary, "complete")
        positive_data = {"baskets": [{"id": group_id, "name": "Controlled positive benchmark verification fixture", "members": []}],
                         "theme_intel": {"as_of": positive["as_of"], "themes": []}}
        positive_site = temporary / "positive/site"
        positive_bundle, receipt["controlled_positive_generation"] = build(positive, positive_site, positive_data)
        benchmark_return = float(benchmark.iloc[-1] / benchmark.iloc[-2] - 1)
        numeric = positive_bundle["groups"][group_id]["members"]["A"]["metrics"]
        raw_number = numeric["raw_daily_change"]["value"]
        relative_number = numeric["benchmark_relative_daily_change"]["value"]
        assert abs(relative_number - (raw_number - benchmark_return)) < 1e-12
        assert round(raw_number * 100, 1) != round(relative_number * 100, 1)
        states = []
        positive_states = []
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                for locale in ("en", "zh"):
                    for theme in ("dark", "light"):
                        for width in (1440, 390):
                            context = browser.new_context(viewport={"width": width, "height": 1000})
                            page = context.new_page()
                            errors = []
                            page.on("pageerror", lambda exc: errors.append(str(exc)))
                            page.add_init_script("localStorage.setItem('lang',"+json.dumps(locale)+");localStorage.setItem('theme',"+json.dumps(theme)+");")
                            page.goto((site / "basket" / (group_id + ".html")).as_uri(), wait_until="load", timeout=20000)
                            page.select_option("#mo-metric", "raw_daily_change")
                            raw = page.locator("#mo-rows tr td:nth-child(2)").all_inner_texts()
                            assert any("%" in value for value in raw)
                            page.select_option("#mo-metric", "benchmark_relative_daily_change")
                            values = page.locator("#mo-rows tr td:nth-child(2)").all_inner_texts()
                            missing = "Unavailable" if locale == "en" else "不可用"
                            assert len(values) == group["member_count"]
                            assert all(value == missing for value in values), values
                            reasons = page.locator("#mo-rows tr td:nth-child(4)").all_inner_texts()
                            assert all(("Benchmark unavailable" if locale == "en" else "基准不可用") in value for value in reasons)
                            page.locator(".mo-table-wrap").scroll_into_view_if_needed()
                            geometry = page.locator(".mo-table-wrap").evaluate("""el=>{const w=el.querySelector('.why').getBoundingClientRect(),r=el.getBoundingClientRect();return {scroll_width:el.scrollWidth,client_width:el.clientWidth,why_left:w.left,why_right:w.right,left:r.left,right:r.right}}""")
                            assert geometry["scroll_width"] <= geometry["client_width"] + 1
                            assert geometry["left"] <= geometry["why_left"] <= geometry["why_right"] <= geometry["right"] + 1
                            assert not errors, errors
                            entry = {"locale": locale, "theme": theme, "width": width,
                                     "raw_members_observed": observed_raw,
                                     "relative_members_observed": 0, "catalogue_members": len(values),
                                     "script_errors": errors, "missing_reason_geometry": geometry}
                            screenshot = EVIDENCE / f"benchmark-unavailable-{locale}-{theme}-{width}.png"
                            page.locator(".mo-band").screenshot(path=str(screenshot))
                            entry.update({"screenshot": screenshot.name, "sha256": sha256(screenshot.read_bytes()).hexdigest()})
                            states.append(entry)
                            context.close()
                for locale, theme, width in [("en", "dark", 1440), ("zh", "light", 390)]:
                    context = browser.new_context(viewport={"width": width, "height": 1000})
                    page = context.new_page()
                    page.add_init_script("localStorage.setItem('lang',"+json.dumps(locale)+");localStorage.setItem('theme',"+json.dumps(theme)+");")
                    page.goto((positive_site / "basket" / (group_id + ".html")).as_uri(), wait_until="load")
                    before = page.evaluate("JSON.stringify(DETAIL.member_observations)")
                    page.fill("#mo-search", "A")
                    pair = {"locale": locale, "theme": theme, "width": width, "fixture_member": "A",
                            "benchmark_return": benchmark_return, "raw_value": raw_number, "relative_value": relative_number,
                            "scope": "controlled positive test fixture; not market data", "screenshots": []}
                    for metric, expected_number, unit in [("raw_daily_change", raw_number, "%"),
                                                          ("benchmark_relative_daily_change", relative_number, "pp" if locale == "en" else "个百分点")]:
                        page.select_option("#mo-metric", metric)
                        value = page.locator("#mo-rows tr td:nth-child(2)").first.inner_text()
                        assert f"{expected_number*100:+.1f}" in value and unit in value, value
                        pair[metric + "_display"] = value
                        image = EVIDENCE / f"benchmark-positive-{metric}-{locale}-{theme}-{width}.png"
                        page.locator(".mo-band").screenshot(path=str(image))
                        pair["screenshots"].append({"file": image.name, "sha256": sha256(image.read_bytes()).hexdigest()})
                    assert page.evaluate("JSON.stringify(DETAIL.member_observations)") == before
                    positive_states.append(pair)
                    context.close()
            finally:
                browser.close()
        receipt["controlled_positive_browser_states"] = positive_states
        receipt["controlled_browser_states"] = states
        assert len(states) == 8
    (EVIDENCE / "page_proof.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    print("CONTROLLED_BROWSER_STATES_PASSED", len(receipt["controlled_browser_states"]), flush=True)

if __name__ == "__main__":
    main()
