"""Real-render browser proof for China P0 risk semantics.

Serves the generated site without response interception and verifies desktop/mobile,
English/Chinese, dark/light. Writes screenshots and a machine-readable receipt.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *_args: Any) -> None:
        return


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--site-dir", type=Path)
    parser.add_argument("--base-url")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    server: ThreadingHTTPServer | None = None
    if args.base_url:
        base_url = args.base_url.rstrip("/")
        render_mode = "real rendered page from supplied base URL; no interception"
    else:
        if not args.site_dir:
            parser.error("--site-dir or --base-url is required")
        server = ThreadingHTTPServer(
            ("127.0.0.1", 0), partial(Quiet, directory=str(args.site_dir))
        )
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base_url = f"http://127.0.0.1:{server.server_port}"
        render_mode = "real locally generated site/china.html; no interception"

    results: list[dict[str, Any]] = []
    failures: list[str] = []

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            for device, width, height in (
                ("desktop", 1440, 1000),
                ("mobile", 390, 844),
            ):
                for lang in ("en", "zh"):
                    for theme in ("dark", "light"):
                        cell = f"{device}-{lang}-{theme}"
                        errors: list[str] = []
                        failed_responses: list[dict[str, Any]] = []
                        page = browser.new_page(
                            viewport={"width": width, "height": height},
                            has_touch=device == "mobile",
                            is_mobile=device == "mobile",
                            reduced_motion="reduce",
                        )
                        page.on("pageerror", lambda exc, e=errors: e.append(str(exc)))
                        page.on(
                            "response",
                            lambda response, out=failed_responses: out.append(
                                {"url": response.url, "status": response.status}
                            )
                            if response.status >= 500
                            else None,
                        )
                        page.add_init_script(
                            f"localStorage.setItem('theme','{theme}');"
                            f"localStorage.setItem('lang','{lang}');"
                            "localStorage.removeItem('themeAuto');"
                            "window.LIVE_POLL_SEC=3600;"
                        )

                        try:
                            response = page.goto(
                                base_url + "/china.html",
                                wait_until="load",
                                timeout=60_000,
                            )
                            assert response and response.status == 200
                            page.wait_for_timeout(900)
                            assert page.locator("html").get_attribute("data-lang") == lang
                            assert page.locator("html").get_attribute("data-theme") == theme

                            hero = page.locator(".cnx-hero").first
                            hero.scroll_into_view_if_needed()
                            assert hero.is_visible()
                            score = page.locator("#ms-score").inner_text().strip()
                            assert score == "39", (cell, "measured score", score)
                            boundary = page.locator("#ms-boundary-chip")
                            assert boundary.is_visible()
                            boundary_text = boundary.inner_text().strip()
                            expected_boundary = (
                                "near Mixed boundary · 3 points below"
                                if lang == "en"
                                else "接近「混合」边界 · 低 3 分"
                            )
                            assert expected_boundary in boundary_text, (cell, boundary_text)
                            thesis = page.locator(".v-thesis").first.inner_text().strip()
                            expected_thesis = (
                                "Participation and liquidity are weak; trend remains soft."
                                if lang == "en"
                                else "参与度与流动性偏弱；趋势仍然疲软。"
                            )
                            assert expected_thesis in thesis, (cell, thesis)

                            hazard_name = "Transition hazard" if lang == "en" else "转变风险"
                            hazard_button = page.get_by_role(
                                "button", name=re.compile(hazard_name, re.I)
                            ).first
                            assert hazard_button.is_visible()
                            assert "not a crash probability" in (hazard_button.get_attribute("data-tip-en") or "")
                            assert "并非崩盘概率" in (hazard_button.get_attribute("data-tip-zh") or "")
                            assert hazard_button.get_attribute("aria-controls") == "cnx-pop-risk"
                            hazard_button.click()
                            popover = page.locator("#cnx-pop-risk")
                            assert popover.is_visible()
                            pop_text = popover.inner_text().strip()
                            for fragment in (
                                ("98th percentile" if lang == "en" else "第98百分位"),
                                ("Historical model estimate" if lang == "en" else "历史模型估计"),
                                ("Live forward evidence still accruing" if lang == "en" else "实时前瞻证据仍在积累"),
                                "×0.62",
                            ):
                                assert fragment in pop_text, (cell, "popover", fragment, pop_text)
                            pop_overflow = popover.evaluate("e => e.scrollWidth - e.clientWidth")
                            assert pop_overflow <= 1, (cell, "popover overflow", pop_overflow)
                            pop_shot = args.output_dir / f"{cell}-popover.png"
                            page.screenshot(path=str(pop_shot))

                            popover.locator(".cnx-pop-link").click()
                            dialog = page.locator("#cnx-dlg-risk")
                            assert dialog.is_visible()
                            dialog_text = dialog.inner_text().strip()
                            required_en = (
                                "MEASURED STATE",
                                "TRANSITION HAZARD",
                                "FORWARD ODDS",
                                "EVIDENCE / AUTHORITY",
                                "near Mixed boundary",
                                "98th percentile",
                                "Historical model estimate",
                                "50%",
                                "normal historical rate 30.5%",
                                "1.64× reference odds",
                                "16 matured",
                                "5 loud",
                                "2 hits",
                                "18 awaiting maturity",
                                "ADVISORY — does not override measured tape",
                                "advisory risk-budget reference",
                                "×0.62",
                                "never selects stocks",
                            )
                            required_zh = (
                                "实测状态",
                                "转变风险",
                                "前瞻概率",
                                "证据／权限",
                                "接近「混合」边界",
                                "第98百分位",
                                "历史模型估计",
                                "50%",
                                "常态历史率 30.5%",
                                "1.64× 参考概率",
                                "16 条已成熟",
                                "5 条强警报",
                                "2 次命中",
                                "18 条待成熟",
                                "提示性 — 不覆盖实测盘面",
                                "提示性风险预算参考",
                                "×0.62",
                                "不用于选股",
                            )
                            for fragment in required_en if lang == "en" else required_zh:
                                assert fragment in dialog_text, (
                                    cell,
                                    "dialog missing",
                                    fragment,
                                )
                            for banned in (
                                "98/100",
                                "half of normal",
                                "suggested size",
                                "约常规一半",
                                "建议仓位",
                            ):
                                assert banned.lower() not in dialog_text.lower(), (
                                    cell,
                                    "banned copy",
                                    banned,
                                )
                            gross = dialog.locator(".rrx-gross")
                            assert gross.count() == 1
                            assert "×0.62" in (gross.get_attribute("data-tip-en") or "")
                            assert "never selects stocks" in (gross.get_attribute("data-tip-en") or "")
                            assert "不用于选股" in (gross.get_attribute("data-tip-zh") or "")

                            panel = dialog.locator(".cnx-dlg-panel")
                            panel_overflow = panel.evaluate(
                                "e => e.scrollWidth - e.clientWidth"
                            )
                            root_overflow = page.evaluate(
                                "document.documentElement.scrollWidth - document.documentElement.clientWidth"
                            )
                            assert panel_overflow <= 1, (
                                cell,
                                "dialog overflow",
                                panel_overflow,
                            )
                            assert root_overflow <= 1, (
                                cell,
                                "page overflow",
                                root_overflow,
                            )
                            assert dialog.get_attribute("role") == "dialog"
                            assert dialog.get_attribute("aria-modal") == "true"
                            labelledby = dialog.get_attribute("aria-labelledby")
                            assert labelledby and page.locator(f"#{labelledby}").count() == 1
                            close_name = (
                                "Close risk context" if lang == "en" else "关闭风险背景"
                            )
                            close_button = page.get_by_role("button", name=close_name)
                            assert close_button.count() == 1

                            dialog_shot = args.output_dir / f"{cell}-dialog.png"
                            page.screenshot(path=str(dialog_shot))
                            close_button.click()
                            assert not dialog.is_visible()

                            # Keyboard parity for the rack-card entry point.
                            rack = page.locator(".cnx-hazard-card")
                            rack.scroll_into_view_if_needed()
                            rack.focus()
                            page.keyboard.press("Enter")
                            assert dialog.is_visible()
                            page.get_by_role("button", name=close_name).click()

                            result = {
                                "cell": cell,
                                "http": response.status,
                                "page_sha256": hashlib.sha256(response.body()).hexdigest(),
                                "score": score,
                                "boundary": boundary_text,
                                "measured_headline": thesis,
                                "popover_overflow_px": pop_overflow,
                                "dialog_overflow_px": panel_overflow,
                                "page_overflow_px": root_overflow,
                                "dialog_semantics_verified": True,
                                "banned_copy_absent": True,
                                "keyboard_dialog_entry": True,
                                "bilingual_close_name": close_name,
                                "page_errors": errors,
                                "failed_5xx_responses": failed_responses,
                                "screenshots": [pop_shot.name, dialog_shot.name],
                                "passed": not errors and not failed_responses,
                            }
                            assert result["passed"], result
                            results.append(result)
                            print(json.dumps(result, ensure_ascii=False), flush=True)
                        except Exception as exc:  # preserve per-cell evidence
                            failure_shot = args.output_dir / f"{cell}-failure.png"
                            try:
                                page.screenshot(path=str(failure_shot), full_page=False)
                            except Exception:
                                pass
                            failures.append(f"{cell}: {exc!r}")
                            results.append(
                                {
                                    "cell": cell,
                                    "passed": False,
                                    "error": repr(exc),
                                    "page_errors": errors,
                                    "failed_5xx_responses": failed_responses,
                                    "failure_screenshot": failure_shot.name,
                                }
                            )
                        finally:
                            page.close()
            browser.close()
    finally:
        if server:
            server.shutdown()
            server.server_close()

    receipt = {
        "operation_key": "cn-risk-p0-semantics-20260923-solpro-001",
        "mode": render_mode,
        "base_url": base_url,
        "cases": results,
        "passed": not failures and len(results) == 8,
        "failures": failures,
    }
    (args.output_dir / "browser-results.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if failures:
        print("FAILURES")
        for failure in failures:
            print(" -", failure)
        return 1
    print(f"PASS {len(results)}/8 browser cells")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
