"""Render the editable blueprint locally; this is not proof of Paper import."""
import asyncio
import hashlib
import json
from pathlib import Path

from playwright.async_api import async_playwright

HERE = Path(__file__).resolve().parent
ORIGIN = "http://127.0.0.1:8768"
URL = ORIGIN + "/mockups/options_workspace_revamp/preview_paper_blueprint.html?all=1"
OUT = HERE / "paper-preview"


async def main():
    OUT.mkdir(exist_ok=True)
    errors = []
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1600, "height": 1400}, service_workers="block")

        async def route_request(route):
            if route.request.url.startswith(ORIGIN + "/"):
                await route.continue_()
            else:
                await route.abort()

        await context.route("**/*", route_request)
        page = await context.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        await page.goto(URL, wait_until="networkidle")
        await page.wait_for_function("window.paperPreview?.ready === true")
        structure = await page.evaluate("window.paperPreview.report")
        layout = await page.evaluate("window.paperPreview.inspectLayout()")
        shots = []
        for board_id in ["brief-desktop-light", "brief-mobile-dark", "scanner-desktop-light", "scanner-mobile-dark", "ticker-desktop-dark", "ticker-mobile-light", "flow-desktop-dark", "leaders-mobile-dark"]:
            await page.evaluate("id => window.paperPreview.renderBoard(id)", board_id)
            await page.evaluate("window.scrollTo(0, 0)")
            board = page.locator('[data-board-id="' + board_id + '"]')
            box = await board.bounding_box()
            clip = dict(x=box["x"], y=box["y"], width=box["width"], height=min(1100, box["height"]))
            path = OUT / (board_id + "-top.png")
            await page.screenshot(path=str(path), clip=clip)
            shots.append(path.name)
            if board_id.startswith("ticker") or board_id.startswith("scanner"):
                section = board.locator('[data-fragment-id]').filter(has_text="Gamma vs price").first if board_id.startswith("ticker") else board.locator('[data-fragment-id]').filter(has_text="Screener").first
                if await section.count():
                    path = OUT / (board_id + "-detail.png")
                    await section.screenshot(path=str(path))
                    shots.append(path.name)
        await context.close()
        await browser.close()
    report = {"scope": "Local HTML assembly only; not Paper rendering", "blueprint_sha256": hashlib.sha256((HERE / "paper_blueprint.json").read_bytes()).hexdigest(), "structure": structure, "layout": layout, "page_errors": errors, "screenshots": shots}
    (OUT / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"boards": len(layout), "page_errors": errors, "layout": [{"id": row["id"], "width": row["width"], "height": row["height"], "overflow_count": len(row["overflow"]), "supporting_text_below_12_5": len(row["supportingTextBelow12_5"])} for row in layout], "screenshots": shots}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
