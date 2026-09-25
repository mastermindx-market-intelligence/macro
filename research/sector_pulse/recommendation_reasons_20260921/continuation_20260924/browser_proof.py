from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import hashlib
import json
import mimetypes
import tempfile
from urllib.parse import unquote, urlsplit

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[4]
SITE = ROOT / "site"
EVIDENCE = Path(__file__).resolve().parent
OUT = EVIDENCE / "browser"
SOURCE = SITE / "basket_china/cn_pharma_cxo.html"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_detail(html: str) -> tuple[str, dict, str]:
    marker = "const DETAIL = "
    assert html.count(marker) == 1
    prefix, tail = html.split(marker, 1)
    detail, end = json.JSONDecoder().raw_decode(tail)
    return prefix, detail, tail[end:]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.png"):
        old.unlink()

    source_html = SOURCE.read_text()
    prefix, base, suffix = parse_detail(source_html)

    with tempfile.TemporaryDirectory(prefix="mmx-7669-browser-controls-") as td:
        pages = Path(td)

        def page_for(name: str, mutator):
            detail = deepcopy(base)
            mutator(detail)
            raw = json.dumps(
                detail, separators=(",", ":"), ensure_ascii=False, allow_nan=False
            ).replace("</", "<\\/")
            path = pages / f"{name}.html"
            path.write_text(prefix + "const DETAIL = " + raw + suffix)
            return path, detail

        def continuation(detail: dict) -> None:
            theme = detail["theme"]
            theme.setdefault("textures", {}).setdefault("clean_entry", {})["flag"] = False
            theme["label"] = "dominant"
            theme["label_en"] = "DOMINANT"
            theme["label_zh"] = "主导"
            theme["reco"] = "accumulate"
            theme["reco_en"] = "ACCUMULATE"
            theme["reco_zh"] = "加仓"
            theme["reco_reason_code"] = "entry_not_confirmed"
            theme["reco_why_en"] = "Theme in favour; no clean entry is confirmed."
            theme["reco_why_zh"] = "主题获看好；尚未确认清晰入场点。"

        def fresh_initial(detail: dict) -> None:
            continuation(detail)
            theme = detail["theme"]
            theme["textures"]["clean_entry"]["flag"] = True
            theme["reco_reason_code"] = "entry_checks_clear"
            theme["reco_why_en"] = "Entry checks clear."
            theme["reco_why_zh"] = "入场条件已满足。"

        def demoted(detail: dict) -> None:
            theme = detail["theme"]
            theme["reco"] = "hold"
            theme["reco_en"] = "HOLD"
            theme["reco_zh"] = "持有"
            theme["reco_reason_code"] = "regime_safeguard"
            theme["reco_why_en"] = "Risk safeguard is active."
            theme["reco_why_zh"] = "风险保护已启用。"

        def stale_missing(detail: dict) -> None:
            detail["as_of"] = "2026-09-20"
            continuation(detail)
            theme = detail["theme"]
            theme.setdefault("textures", {}).pop("clean_entry", None)
            theme["reco_reason_code"] = "entry_read_unavailable"
            theme["reco_why_en"] = "Entry information unavailable."
            theme["reco_why_zh"] = "入场信息暂缺。"

        scenarios = {
            "continuation_zero_qualified": page_for(
                "continuation_zero_qualified", continuation
            ),
            "fresh_initial": page_for("fresh_initial", fresh_initial),
            "final_demoted": page_for("final_demoted", demoted),
            "stale_missing_entry": page_for("stale_missing_entry", stale_missing),
        }
        expected = {
            "continuation_zero_qualified": {
                "rating_en": "ACCUMULATE",
                "rating_zh": "加仓",
                "initial": True,
                "qualified": 0,
                "stale": False,
            },
            "fresh_initial": {
                "rating_en": "ACCUMULATE",
                "rating_zh": "加仓",
                "initial": False,
                "qualified": 0,
                "stale": False,
            },
            "final_demoted": {
                "rating_en": "HOLD",
                "rating_zh": "持有",
                "initial": False,
                "qualified": 0,
                "stale": False,
            },
            "stale_missing_entry": {
                "rating_en": "ACCUMULATE",
                "rating_zh": "加仓",
                "initial": True,
                "qualified": 0,
                "stale": True,
            },
        }

        records: list[dict] = []
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            for scenario, (scenario_path, detail) in scenarios.items():
                entry_checks = detail.get("act_now", {}).get("entry_checks") or []
                qualified = sum(1 for row in entry_checks if row.get("eligible"))
                assert qualified == expected[scenario]["qualified"], (scenario, qualified)
                for theme in ("dark", "light"):
                    for language in ("en", "zh"):
                        for width in (1440, 390):
                            context = browser.new_context(
                                viewport={"width": width, "height": 1000},
                                device_scale_factor=1,
                            )
                            context.add_init_script(
                                "localStorage.setItem('theme',"
                                + json.dumps(theme)
                                + ");localStorage.setItem('lang',"
                                + json.dumps(language)
                                + ");"
                            )
                            page_errors: list[str] = []
                            request_failures: list[str] = []
                            unavailable_live_requests: list[str] = []

                            def serve(route):
                                url = urlsplit(route.request.url)
                                if url.hostname != "continuation.local":
                                    route.fulfill(status=204, body="")
                                    return
                                path = unquote(url.path)
                                if path == f"/basket_china/{scenario}.html":
                                    route.fulfill(
                                        status=200,
                                        content_type="text/html",
                                        body=scenario_path.read_bytes(),
                                    )
                                    return
                                if path.startswith(("/live/", "/api/", "/premiumdata/")):
                                    unavailable_live_requests.append(path)
                                    route.fulfill(
                                        status=401,
                                        content_type="application/json",
                                        body='{"error":"not_part_of_local_proof"}',
                                    )
                                    return
                                target = (SITE / path.lstrip("/")).resolve()
                                if target.is_relative_to(SITE.resolve()) and target.is_file():
                                    route.fulfill(
                                        status=200,
                                        content_type=mimetypes.guess_type(str(target))[0]
                                        or "application/octet-stream",
                                        body=target.read_bytes(),
                                    )
                                else:
                                    route.fulfill(
                                        status=404, body="Unavailable in local proof"
                                    )

                            context.route("**/*", serve)
                            page = context.new_page()
                            page.on("pageerror", lambda error: page_errors.append(str(error)))
                            page.on(
                                "requestfailed",
                                lambda request: request_failures.append(request.url),
                            )
                            response = page.goto(
                                f"http://continuation.local/basket_china/{scenario}.html",
                                wait_until="networkidle",
                            )
                            assert response and response.status == 200
                            applied = page.evaluate(
                                "({theme:document.documentElement.dataset.theme,"
                                "language:document.documentElement.dataset.lang})"
                            )
                            assert applied == {
                                "theme": theme,
                                "language": language,
                            }, applied
                            hero = page.locator(".panel.hero")
                            hero_text = hero.inner_text()
                            rating = (
                                expected[scenario]["rating_en"]
                                if language == "en"
                                else expected[scenario]["rating_zh"]
                            )
                            assert rating in hero_text, (scenario, language, hero_text)
                            assert "WAIT FOR ENTRY" not in hero_text
                            assert "等待入场" not in hero_text
                            initial_visible = (
                                "Initial entry context:" in hero_text
                                if language == "en"
                                else "初始入场条件：" in hero_text
                            )
                            assert initial_visible is expected[scenario]["initial"], (
                                scenario,
                                language,
                                hero_text,
                            )
                            link = page.locator("[data-stock-entry-link]")
                            assert link.count() == 1
                            link.focus()
                            page.keyboard.press("Enter")
                            panel = page.locator("#stock-entry-checks")
                            assert panel.evaluate("element => element.open")
                            summary = panel.inner_text()
                            if scenario == "continuation_zero_qualified":
                                assert (
                                    "0 qualified" in summary
                                    if language == "en"
                                    else "0 只通过" in summary
                                )
                            stale = page.locator(".ftr-stale-banner")
                            assert (stale.count() > 0) is expected[scenario]["stale"]
                            if scenario == "stale_missing_entry":
                                assert (
                                    "Entry information unavailable." in hero_text
                                    if language == "en"
                                    else "入场信息暂缺。" in hero_text
                                )
                            geometry = page.evaluate(
                                "({scroll:document.documentElement.scrollWidth,"
                                "viewport:innerWidth})"
                            )
                            assert geometry["scroll"] <= geometry["viewport"] + 1, (
                                scenario,
                                theme,
                                language,
                                width,
                                geometry,
                            )
                            hero.scroll_into_view_if_needed()
                            filename = f"{scenario}-{theme}-{language}-{width}.png"
                            screenshot = OUT / filename
                            hero.screenshot(path=str(screenshot))
                            assert not page_errors, (scenario, page_errors)
                            assert not request_failures, (scenario, request_failures)
                            records.append(
                                {
                                    "scenario": scenario,
                                    "theme": theme,
                                    "language": language,
                                    "width": width,
                                    "http_status": response.status,
                                    "rating_visible": True,
                                    "wait_instruction_absent": True,
                                    "initial_context_visible": initial_visible,
                                    "stock_checks_opened": True,
                                    "page_errors": page_errors,
                                    "request_failures": request_failures,
                                    "page_overflow": False,
                                    "unavailable_live_requests": sorted(
                                        set(unavailable_live_requests)
                                    ),
                                    "screenshot": filename,
                                    "sha256": sha256(screenshot),
                                }
                            )
                            context.close()
                print("VERIFIED", scenario, len(records), flush=True)
            browser.close()

    receipt = {
        "source_page": SOURCE.relative_to(ROOT).as_posix(),
        "source_page_sha256": sha256(SOURCE),
        "captures": len(records),
        "records": records,
        "production": False,
        "limitations": [
            "Synthetic controls modify only DETAIL data inside the compiled current source page.",
            "No new market data, action-card decision, score, or trade permission is created.",
            "Local Chromium proof only; production/authenticated proof remains separate.",
        ],
    }
    (EVIDENCE / "browser-receipt.json").write_text(
        json.dumps(receipt, indent=2, ensure_ascii=False) + "\n"
    )
    print(
        json.dumps(
            {
                "captures": len(records),
                "errors": sum(len(row["page_errors"]) for row in records),
                "request_failures": sum(
                    len(row["request_failures"]) for row in records
                ),
                "all_no_wait": all(
                    row["wait_instruction_absent"] for row in records
                ),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
