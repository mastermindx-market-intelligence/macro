"""Exercise Sources on the public fixture. Use an empty context and real controls."""

import argparse
import hashlib
import json
import sys
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts.capture_page_evidence import serve_site_dir, state_seed_source


def inspect(site, out):
    out.mkdir(parents=True, exist_ok=True)
    server, port = serve_site_dir(site)
    origin = f"http://127.0.0.1:{port}"
    rows = []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            for width, height in ((1440, 900), (390, 844), (320, 720)):
                for theme in ("light", "dark"):
                    for locale in ("en", "zh"):
                        ctx = browser.new_context(
                            viewport={"width": width, "height": height},
                            locale="zh-CN" if locale == "zh" else "en-US",
                            device_scale_factor=1,
                            color_scheme=theme,
                            service_workers="block",
                        )
                        ctx.route(
                            "**/*",
                            lambda route: (
                                route.continue_()
                                if urlsplit(route.request.url).netloc
                                == f"127.0.0.1:{port}"
                                else route.abort()
                            ),
                        )
                        ctx.add_init_script(
                            state_seed_source({"theme": theme, "locale": locale})
                        )
                        page = ctx.new_page()
                        row = dict(
                            width=width,
                            theme=theme,
                            locale=locale,
                            access="anonymous fixture",
                        )
                        try:
                            page.goto(
                                origin + "/us_stocks.html",
                                wait_until="domcontentloaded",
                                timeout=30000,
                            )
                            card = page.locator("#us-today-grid .po-card").first
                            row["candidate"] = card.get_attribute("data-ticker")
                            card.locator("summary.po-setup").click(timeout=8000)
                            dialog = page.locator("#pv-setup-dialog[open]")
                            tab = dialog.locator(
                                '[role=tab][aria-controls$="-sources-panel"]'
                            )
                            tab.click(timeout=8000)
                            panel = dialog.locator('[data-pvs-section="sources"]')
                            assert (
                                tab.get_attribute("aria-selected") == "true"
                                and panel.is_visible()
                            )
                            audit = panel.locator("details.pvs-audit")
                            audit.locator("summary").click()
                            assert audit.get_attribute("open") is not None
                            row["identity"] = panel.locator(
                                "xpath=ancestor::*[@data-native-id][1]"
                            ).get_attribute("data-native-id")
                            assert row["identity"] == row["candidate"]
                            row["source_fields"] = panel.locator(
                                "[data-source-field]"
                            ).evaluate_all(
                                '(xs)=>xs.map(x=>x.getAttribute("data-source-field"))'
                            )
                            assert (
                                "price_as_of" in row["source_fields"]
                                and "envelope.as_of" in row["source_fields"]
                            )
                            row["plan_text"] = panel.locator(
                                ".pvs-plan-relation"
                            ).inner_text()
                            row["plan_controls"] = panel.locator(
                                ".pvs-plan-link"
                            ).count()
                            row["applied_theme"] = page.locator("html").get_attribute(
                                "data-theme"
                            )
                            row["applied_locale"] = page.locator("html").get_attribute(
                                "data-lang"
                            )
                            assert (
                                row["applied_theme"] == theme
                                and row["applied_locale"] == locale
                            )
                            row["overflow"] = page.evaluate(
                                "document.documentElement.scrollWidth > innerWidth"
                            )
                            row["dialog_overflow"] = dialog.evaluate(
                                "(d)=>d.scrollWidth > d.clientWidth + 1"
                            )
                            name = f"sources-{width}-{theme}-{locale}.png"
                            png = page.screenshot(path=out / name)
                            row.update(
                                file=name,
                                sha256=hashlib.sha256(png).hexdigest(),
                                captured=True,
                            )
                        except Exception as exc:
                            row.update(captured=False, reason=str(exc)[:800])
                        finally:
                            rows.append(row)
                            ctx.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
    (out / "observations.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2) + "\n"
    )
    print("Sources captured", sum(bool(r["captured"]) for r in rows), "/", len(rows))
    return all(
        r["captured"] and not r["overflow"] and not r["dialog_overflow"] for r in rows
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("site", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    raise SystemExit(0 if inspect(args.site.resolve(), args.output) else 1)
