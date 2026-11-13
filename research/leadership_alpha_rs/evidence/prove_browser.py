"""Manual, offline browser proof; never a server or production publisher.

Requires the existing Playwright environment and an installed Chromium.
Run after building the real source-pinned preview. Output must be a new evidence
folder so prior receipts cannot be silently replaced.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview", type=Path, required=True)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    args = parser.parse_args()
    preview = args.preview.resolve(strict=True)
    output = args.evidence_dir.resolve()
    output.mkdir(parents=True, exist_ok=False)
    proof = {"preview_sha256": hashlib.sha256(preview.read_bytes()).hexdigest(),
             "mode": "OFFLINE_RESEARCH_PREVIEW_NOT_PRODUCTION", "cases": []}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        proof["browser_version"] = browser.version
        for width, height, device in ((1440, 1100, "desktop"), (390, 844, "mobile")):
            for theme in ("dark", "light"):
                for language in ("en", "zh"):
                    context = browser.new_context(viewport={"width": width, "height": height})
                    page = context.new_page()
                    errors, remote_requests = [], []
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
                    page.on("request", lambda req: remote_requests.append(req.url)
                            if req.url.startswith(("https://", "http://")) else None)
                    page.goto(preview.as_uri(), wait_until="load")
                    if theme == "light":
                        page.locator("#ll-theme").click()
                    if language == "zh":
                        page.locator("#ll-language").click()
                    assert page.locator("html").get_attribute("data-theme") == theme
                    assert page.locator("html").get_attribute("data-lang") == language
                    heading = page.locator("h1").inner_text()
                    assert heading == ("Leadership Lab" if language == "en" else "领先股研究")
                    rows = page.locator("[data-leader-row]")
                    total = rows.count()
                    assert total > 0
                    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
                    first_row_y = rows.first.bounding_box()["y"]
                    number_boxes = [cell.bounding_box() for cell in rows.first.locator('td.ll-number').all()]
                    core_metrics_visible = len(number_boxes) == 2 and all(
                        box and box['x'] >= 0 and box['x'] + box['width'] <= width
                        and box['y'] + box['height'] <= height for box in number_boxes)
                    banner = page.locator('.ll-current-banner')
                    context_label_visible = (banner.count() == 0 or
                        banner.locator('strong .l-' + language).first.is_visible())
                    metric_font = page.locator('.ll-text-metric .l-' + language).evaluate(
                        "el => parseFloat(getComputedStyle(el).fontSize)")
                    page.screenshot(path=str(output / f"{device}-{theme}-{language}.png"))
                    # Real interactions: no-match state, reset, sector filtering,
                    # issuer dossier, source/method disclosure and theme coverage.
                    page.locator("#ll-search").fill("__NO_MATCH_EXPECTED__")
                    assert page.locator("[data-leader-row]:visible").count() == 0
                    assert page.locator("#ll-empty").is_visible()
                    page.locator("#ll-search").fill("")
                    assert page.locator("[data-leader-row]:visible").count() == total
                    selected_sector = rows.first.get_attribute("data-sector")
                    page.locator("#ll-sector").select_option(value=selected_sector)
                    assert all(row.get_attribute("data-sector") == selected_sector
                               for row in page.locator("[data-leader-row]:visible").all())
                    page.locator("#ll-sector").select_option(value="")
                    rows.first.locator("summary").click()
                    assert rows.first.locator("details").get_attribute("open") is not None
                    expanded_no_overflow = page.evaluate(
                        "document.documentElement.scrollWidth <= window.innerWidth + 1")
                    assert expanded_no_overflow
                    peer_visible = page.locator(".ll-peer-context:visible").count() > 0
                    page.locator(".ll-method > summary").click()
                    assert page.locator(".ll-method").get_attribute("open") is not None
                    page.locator(".ll-group-list > summary").click()
                    assert page.locator(".ll-group-list").get_attribute("open") is not None
                    assert not errors, errors
                    assert not remote_requests, remote_requests
                    proof["cases"].append({"device": device, "width": width, "height": height,
                                           "theme": theme, "language": language, "rows": total,
                                           "first_row_y": first_row_y, "document_overflow": False,
                                           "metric_font_size": metric_font,
                                           "first_screen_leader": first_row_y < height,
                                           "core_metrics_visible": bool(core_metrics_visible),
                                           "context_label_visible": context_label_visible,
                                           "expanded_dossier_overflow": not expanded_no_overflow,
                                           "peer_context_visible_after_expand": peer_visible,
                                           "console_errors": errors, "remote_requests": remote_requests,
                                           "interactions": "PASS"})
                    context.close()
        browser.close()
    (output / "receipt.json").write_text(json.dumps(proof, indent=2), encoding="utf-8")
    print(json.dumps(proof, indent=2))
    assert all(case["metric_font_size"] >= 22 for case in proof["cases"]), "Primary metric typography too small"
    assert all(case["first_screen_leader"] for case in proof["cases"]), "No leader visible on first screen"
    assert all(not case["expanded_dossier_overflow"] for case in proof["cases"]), "Expanded dossier causes page overflow"
    assert all(case['core_metrics_visible'] for case in proof['cases']), 'Alpha and RS are not both visible at a glance'
    assert all(case['context_label_visible'] for case in proof['cases']), 'Current-context label is hidden'


if __name__ == "__main__":
    main()
