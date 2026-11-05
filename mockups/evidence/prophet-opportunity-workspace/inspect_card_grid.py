"""Measure the short Today shelf on the public HTML emitted by the normal producer."""

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


def inspect(site: Path, out: Path, viewports, themes, locales):
    if (site / "premiumdata").exists() or (site / "us_stocks.json").exists():
        raise ValueError("Use the public-only artifact directory.")
    out.mkdir(parents=True, exist_ok=True)
    server, port = serve_site_dir(site)
    origin = f"http://127.0.0.1:{port}"
    rows = []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            for width in viewports:
                expected = 4 if width >= 1200 else 3 if width >= 960 else 2 if width >= 640 else 1
                for theme in themes:
                    for locale in locales:
                        context = browser.new_context(
                            viewport={"width": width, "height": 900 if width >= 1200 else 844},
                            locale=locale, color_scheme=theme, service_workers="block",
                        )
                        try:
                            context.route("**/*", lambda route: route.continue_()
                                          if urlsplit(route.request.url).netloc == f"127.0.0.1:{port}"
                                          else route.abort())
                            context.add_init_script(state_seed_source({"theme": theme, "locale": locale}))
                            page = context.new_page()
                            page.goto(origin + "/us_stocks.html", wait_until="domcontentloaded")
                            grid = page.locator("#us-today-grid")
                            grid.locator(":scope > .po-card").first.wait_for(state="visible")
                            page.evaluate("document.fonts.ready")
                            row = grid.evaluate("""el => {
                                const style = getComputedStyle(el);
                                const cards = Array.from(el.querySelectorAll(':scope > .po-card'));
                                return {
                                    viewport: innerWidth,
                                    theme: document.documentElement.dataset.theme,
                                    locale: document.documentElement.dataset.lang,
                                    grid_width: el.getBoundingClientRect().width,
                                    gap: parseFloat(style.columnGap),
                                    tracks: style.gridTemplateColumns.split(' ').map(parseFloat),
                                    cards: cards.map(card => ({
                                        ticker: card.dataset.ticker,
                                        width: card.getBoundingClientRect().width,
                                        left: card.getBoundingClientRect().left,
                                        top: card.getBoundingClientRect().top,
                                    })),
                                    overflow: document.documentElement.scrollWidth > innerWidth,
                                };
                            }""")
                            ideal = (row["grid_width"] - row["gap"] * (expected - 1)) / expected
                            filename = f"today-{width}-{theme}-{locale}.png"
                            png = grid.screenshot(path=out / filename)
                            row.update(
                                expected_columns=expected, expected_track_width=ideal,
                                file=filename, sha256=hashlib.sha256(png).hexdigest(),
                                passed=(row["viewport"] == width and row["theme"] == theme
                                        and row["locale"] == locale and not row["overflow"]
                                        and len(row["tracks"]) == expected
                                        and all(abs(track - ideal) <= 1 for track in row["tracks"])
                                        and all(abs(card["width"] - ideal) <= 1 for card in row["cards"])),
                            )
                            rows.append(row)
                        finally:
                            context.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
    report = {
        "source_html_sha256": hashlib.sha256((site / "us_stocks.html").read_bytes()).hexdigest(),
        "access": "anonymous, isolated public build", "cases": rows,
    }
    (out / "observations.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"Compact Today grid: {sum(r['passed'] for r in rows)}/{len(rows)} cases passed.")
    return all(r["passed"] for r in rows)


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("site", type=Path)
    cli.add_argument("output", type=Path)
    cli.add_argument("--widths", type=int, nargs="+", default=[1440, 1024, 768, 390])
    cli.add_argument("--themes", nargs="+", default=["light", "dark"])
    cli.add_argument("--locales", nargs="+", default=["en", "zh"])
    args = cli.parse_args()
    raise SystemExit(0 if inspect(args.site.resolve(), args.output, args.widths,
                                  args.themes, args.locales) else 1)
