"""Verify the actual, unchanged macro target; never splice or restyle the page.

Local anonymous browser proof, not production. The shared evidence capturer owns
screenshot manifests; this probe supplies interaction/data/placement assertions.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from lib.macro_economic_backdrop import build_economic_backdrop
from scripts.capture_page_evidence import serve_site_dir


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    target = ROOT / "site/macro.html"
    receipt = json.loads(Path(__file__).with_name("canonical-target-receipt.json").read_text())
    html_digest = hashlib.sha256(target.read_bytes()).hexdigest()
    assert html_digest == receipt["html_sha256"]
    assert all(hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == h for p, h in receipt["source_hashes"].items())
    cards = build_economic_backdrop(ROOT / "site/macrodata", page_built_at=receipt["utc"])
    report = {"kind": "ACTUAL_LOCAL_CANONICAL_TARGET", "production": False,
              "at": datetime.now(timezone.utc).isoformat(), "html_sha256": html_digest,
              "source_hashes": receipt["source_hashes"], "cases": [], "journeys": []}
    server, port = serve_site_dir(ROOT / "site")
    from playwright.sync_api import sync_playwright
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            for width in (1440, 768, 390):
                for theme, lang in (("dark", "en"), ("light", "en"), ("dark", "zh"), ("light", "zh")):
                    ctx = browser.new_context(viewport={"width": width, "height": 900}, reduced_motion="reduce")
                    try:
                        ctx.route("**/*", lambda route: route.continue_() if urlparse(route.request.url).hostname == "127.0.0.1" else route.abort())
                        tab = ctx.new_page()
                        errors = []
                        tab.on("pageerror", lambda error: errors.append(str(error)))
                        tab.goto(f"http://127.0.0.1:{port}/macro.html", wait_until="load")
                        tab.evaluate("([t,l])=>{window.setTheme ? window.setTheme(t) : document.documentElement.dataset.theme=t;window.setLang ? window.setLang(l) : document.documentElement.dataset.lang=l;document.documentElement.lang=l}", [theme, lang])
                        tab.evaluate("document.fonts.ready")
                        row = tab.locator(".ebd")
                        assert row.is_visible() and tab.locator(".ebd-card").count() == 3
                        positions = tab.evaluate("""() => {const r=s=>document.querySelector(s).getBoundingClientRect();return {market_bottom:r('#sx-markets-v2').bottom,row_top:r('.ebd').top,row_bottom:r('.ebd').bottom,actions_top:r('#sx-evidence').top}}""")
                        assert positions["market_bottom"] <= positions["row_top"]
                        assert positions["row_bottom"] <= positions["actions_top"]
                        height = row.bounding_box()["height"]
                        assert width != 1440 or height <= 240
                        assert tab.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
                        for card in cards:
                            node = row.locator("article").filter(has=tab.locator("#ebd-t-" + card["id"]))
                            assert card["state"][lang] in node.inner_text()
                            if card.get("basis"):
                                assert card["basis"][lang] in node.locator(".ebd-label").inner_text()
                            for fact in card["facts"]:
                                assert fact["value"][lang] in node.inner_text()
                                assert not fact["period"] or fact["period"] in node.inner_text()
                            assert node.locator("a.ebd-go").get_attribute("href") == card["href"]
                            assert node.locator("a.ebd-go").bounding_box()["height"] >= 44
                        row.screenshot(path=str(out / f"row-{width}-{theme}-{lang}.png"))
                        summary_heights = row.locator("summary").evaluate_all("els=>els.map(e=>e.getBoundingClientRect().height)")
                        assert len(summary_heights) == 3 and min(summary_heights) >= 44
                        control = row.locator("summary").first
                        control.focus()
                        tab.keyboard.press("Enter")
                        assert row.locator("details").first.get_attribute("open") is not None
                        tab.keyboard.press("Enter")
                        assert row.locator("details").first.get_attribute("open") is None
                        assert not errors, errors
                        report["cases"].append({"width": width, "theme": theme, "lang": lang,
                                                "row_height": height, "placement": positions,
                                                "keyboard_receipt": True, "source_receipt_heights": summary_heights, "page_errors": errors})
                        if width == 1440 and lang == "en" and theme == "dark":
                            for card in cards:
                                tab.locator(f"#ebd-t-{card['id']}").locator("..").locator("a.ebd-go").click()
                                tab.wait_for_load_state("load")
                                tab.locator(".mq-headline").wait_for(state="visible")
                                assert urlparse(tab.url).path == card["href"]
                                assert card["state"][lang] in tab.locator(".mq-headline").inner_text()
                                report["journeys"].append({"topic": card["id"], "destination": card["href"], "same_owner_state": True})
                                tab.go_back(wait_until="load")
                    finally:
                        ctx.unroute_all(behavior="wait")
                        ctx.close()
            browser.close()
        report["status"] = "PASS"
        return 0
    finally:
        server.shutdown()
        server.server_close()
        assert hashlib.sha256(target.read_bytes()).hexdigest() == html_digest
        (out / "receipt.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
        print(json.dumps({"status": report.get("status", "INCOMPLETE"), "cases": len(report["cases"]),
                          "journeys": len(report["journeys"]), "receipt": str(out / "receipt.json")}))


if __name__ == "__main__":
    raise SystemExit(main())
