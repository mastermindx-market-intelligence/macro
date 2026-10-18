"""Bounded browser acceptance for the actual CDI component, not deployment proof.

Run from the repository root. Uses installed Playwright Chromium; never downloads
or installs a browser. Fixtures are explicitly synthetic, while --native additionally
checks the existing data-root artifact through the production reader.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import date, datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine.credit_dislocation_view import build_view, load_view


def _fixture_module():
    spec = importlib.util.spec_from_file_location("cdi_browser_fixture", ROOT / "tests/test_credit_dislocation_view.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _html(component: str, language: str, theme: str) -> str:
    # Uses the existing product token values. This is a component harness, not a
    # replacement Bonds page or an imitation of production navigation.
    return f"""<!doctype html><html data-lang="{language}" data-theme="{theme}"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>CDI component acceptance - synthetic unless labeled native</title>
<style>
:root{{--bg:#F7F8FA;--card:#FFFFFF;--text:#1C2430;--muted:#5D6B7E;--line:#C9CCD1;--border:#C9CCD1;--down:#B23C3D;--warn:#7D5922;--info:#285FFF;--up:#1E6D47}}
[data-theme=dark]{{--bg:#0F1115;--card:#181B21;--text:#D7DCE3;--muted:#8B93A1;--line:#3A4150;--border:#3A4150;--down:#E06464;--warn:#E0A030;--info:#5B9BF0;--up:#45B873}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--text);font-family:Arial,sans-serif;line-height:1.5}}
main{{max-width:1252px;margin:0 auto;padding:24px}}[data-lang=en] .l-zh,[data-lang=zh] .l-en{{display:none}}
[hidden]{{display:none!important}}button,input,select{{font:inherit}}
@media(max-width:480px){{main{{padding:14px}}}}
</style></head><body><main>{component}</main></body></html>"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--native", action="store_true")
    parser.add_argument("--as-of", type=date.fromisoformat, default=datetime.now(timezone.utc).date())
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    fixture = _fixture_module()
    from playwright.sync_api import sync_playwright
    receipt = {"scope": "actual CDI component, not full route or deployment", "deployed": False,
               "created_at": datetime.now(timezone.utc).isoformat(), "cases": [], "errors": [],
               "source_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                   for name in ["engine/credit_dislocation.py", "engine/credit_dislocation_view.py",
                                "templates/_credit_dislocation.html.j2", "scripts/verify_credit_dislocation_browser.py"]}}
    states = ["qualified_synthetic", "pricing_unqualified", "stale", "missing_source"]
    if args.native:
        states.append("native")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            for state in states:
                value = fixture.sample()
                if state == "qualified_synthetic":
                    extra = deepcopy(value["issuers"][0]); extra.update(issuer="TEST1", equity_ticker="TEST1", tier="HY")
                    extra["change_5"] = {"value_bp": None, "reason": "insufficient_history"}
                    extra["relative_change_5_bp"] = None
                    value["issuers"].append(extra)
                if state == "pricing_unqualified": value["pricing_validation"] = None
                view = (load_view(ROOT / "data", as_of=args.as_of) if state == "native" else
                        build_view(None if state == "missing_source" else value,
                                   as_of=date(2026, 11, 2) if state == "stale" else fixture.TODAY))
                for width, height in [(1440, 1100), (390, 1000)]:
                    for language in ["en", "zh"]:
                        for theme in ["light", "dark"]:
                            context = browser.new_context(viewport={"width": width, "height": height},
                                                          color_scheme=theme, reduced_motion="reduce")
                            page = context.new_page(); page.set_default_timeout(5000); errors = []
                            page.on("pageerror", lambda error: errors.append(str(error)))
                            key = f"{state}-{width}-{language}-{theme}"
                            item = {"case": key, "state": state, "language": language,
                                    "theme": theme, "viewport": [width, height]}
                            try:
                                page.set_content(_html(fixture.render(view), language, theme), wait_until="load")
                                assert page.locator("[data-cdi-root]").count() == 1
                                if view.get("available"):
                                    n = len(view["issuers"])
                                    assert page.locator("[data-cdi-issuer]:visible").count() == n
                                    assert page.locator("[data-cdi-bond-target] table").count() == 0
                                    first = view["issuers"][0]["issuer"]
                                    page.locator("[data-cdi-search]").fill(first)
                                    assert page.locator("[data-cdi-issuer]:visible").count() == 1
                                    summary = page.locator("[data-cdi-issuer]:visible > summary").first
                                    summary.focus(); page.keyboard.press("Enter")
                                    assert page.locator("[data-cdi-issuer]:visible").get_attribute("open") is not None
                                    nested = page.locator("[data-cdi-issuer]:visible [data-cdi-bond-inspector] > summary")
                                    nested.click()
                                    page.wait_for_function("document.querySelector('[data-cdi-issuer]:not([hidden]) [data-cdi-bond-inspector]').dataset.loaded === 'true'")
                                    count = page.locator("[data-cdi-issuer]:visible [data-cdi-bond-target] table").count()
                                    nested.click(); nested.click()
                                    assert page.locator("[data-cdi-issuer]:visible [data-cdi-bond-target] table").count() == count
                                    page.locator("[data-cdi-search]").fill("no-such-issuer-fixture")
                                    assert page.locator("[data-cdi-issuer]:visible").count() == 0
                                    assert page.locator("[data-cdi-no-results]").is_visible()
                                    page.locator("[data-cdi-search]").fill("")
                                    page.locator("[data-cdi-coverage]").select_option("paired")
                                    assert page.locator("[data-cdi-issuer]:visible").count() == view["paired_count"]
                                    page.locator("[data-cdi-coverage]").select_option("all")
                                    page.locator("[data-cdi-grade]").select_option("HY")
                                    assert page.locator("[data-cdi-issuer]:visible").count() == sum(r["tier"] == "HY" for r in view["issuers"])
                                    page.locator("[data-cdi-grade]").select_option("all")
                                    assert page.locator("[data-cdi-pricing]").get_attribute("data-cdi-pricing") == ("passed" if view["pricing_qualified"] else "unqualified")
                                    # Screenshot the real expanded first row, with other issuers filtered away.
                                    page.locator("[data-cdi-search]").fill(first)
                                    item.update(search=True, filters=True, keyboard=True, lazy_bonds_once=True,
                                                source_as_of=view.get("source_as_of"), paired_count=view["paired_count"],
                                                pricing_qualified=view["pricing_qualified"])
                                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
                                assert not errors, errors
                                image = args.output / (key + ".png")
                                page.screenshot(path=str(image), full_page=True)
                                item.update(status="passed", no_page_overflow=True, screenshot=image.name,
                                            screenshot_sha256=hashlib.sha256(image.read_bytes()).hexdigest())
                            except Exception as exc:
                                item.update(status="failed", error=repr(exc)); receipt["errors"].append({"case": key, "error": repr(exc)})
                            finally:
                                receipt["cases"].append(item); context.close()
        finally:
            browser.close()
    receipt["passed"] = not receipt["errors"]
    (args.output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"cases": len(receipt["cases"]), "passed": receipt["passed"], "errors": receipt["errors"]}))
    return 0 if receipt["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
