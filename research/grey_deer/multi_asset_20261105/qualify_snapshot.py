#!/usr/bin/env python3
"""Read exact existing Git snapshots and verify the real builder/Radar component.

No network acquisition, production writes, orders, forecast validation or deployment.
Browser checks use the actual component and existing CSS, in a bounded local shell.
The component shell is not acceptance of the full production page or live overlay.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from tests.test_dashboard_template_render import _env
from tests.test_macro_risk_dialog import _vm
from engine.multi_asset_daily import UNIVERSE, validate_daily_context
from scripts.build_risk_envelope import build

BOUND_SOURCES = [
    "engine/multi_asset_context.py", "engine/multi_asset_daily.py", "engine/risk_envelope.py",
    "scripts/risk_envelope_multi_asset.py", "scripts/build_risk_envelope.py",
    "templates/risk_envelope/_multi_asset_context.html.j2", "templates/_risk_envelope_band.html.j2",
    "templates/_risk_envelope_band.css.j2", "templates/theme.css", "contracts/risk_envelope.schema.json",
    "research/grey_deer/multi_asset_20261105/qualify_snapshot.py",
]


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--browser-channel", choices=["chrome", "chromium"], default=None)
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", args.revision):
        parser.error("revision must be an exact Git commit")
    output = args.output.resolve()
    if output == ROOT or any(p == ROOT / name for p in [output, *output.parents] for name in ("data", "site", ".git")):
        parser.error("proof output cannot target runtime/publication roots")
    output.mkdir(parents=True, exist_ok=True)
    inputs = []
    source_paths = ["data/yahoo/" + ticker + ".parquet" for ticker, *_ in UNIVERSE]
    source_paths += ["data/market_state/latest.json", "data/leadership_crack/latest.json", "site/marketdata/rotation_events.json"]
    with tempfile.TemporaryDirectory(prefix="multiasset-source-proof-") as directory:
        root = Path(directory)
        for path in source_paths:
            result = subprocess.run(["git", "-C", str(ROOT), "show", args.revision + ":" + path], capture_output=True)
            if result.returncode:
                inputs.append({"path": path, "status": "MISSING_AT_REVISION"})
                continue
            target = root / path; target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(result.stdout)
            inputs.append({"path": path, "status": "READ", "sha256": digest(result.stdout), "bytes": len(result.stdout)})
        captured = datetime.now(timezone.utc)
        envelope = build(root=root, now=captured)
        context = validate_daily_context(envelope["multi_asset_context"])
        assert all(v is False for v in context["authority"].values())
        for row in context["rows"]:
            if row["status"] != "OBSERVED":
                assert row["absolute_return"] is None and row["relative_return"] is None
        assert not (root / "data/risk_envelope").exists(), "builder must not publish during qualification"
    environment = Environment(loader=FileSystemLoader(ROOT / "templates"))
    component = environment.get_template("_risk_envelope_band.html.j2").render(risk_envelope=envelope)
    # Use the real Macro host token aliases and styles, not an invented token map.
    host_environment = _env()
    style_inputs = {}
    original_loader = host_environment.loader.get_source
    def tracked_loader(env, template):
        result = original_loader(env, template)
        source_path = Path(result[1]).resolve()
        style_inputs[str(source_path.relative_to(ROOT))] = digest(source_path.read_bytes())
        return result
    host_environment.loader.get_source = tracked_loader
    host_html = host_environment.get_template("dashboard.html.j2").render(**_vm(risk_envelope=envelope))
    host_styles = "\n".join(tag.get_text() for tag in BeautifulSoup(host_html, "html.parser").find_all("style"))
    css = (ROOT / "templates/theme.css").read_text() + "\n" + host_styles
    # Only the bounded test host shell is added. The feature/component/CSS are real source.
    shell = """<!doctype html><html lang="en" data-lang="en" data-theme="dark"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><style>""" + css + """
body{margin:0;background:var(--bg,#10141c);color:var(--ink-1);font-family:var(--font-ui,system-ui)}
#dlg-risk{display:block;box-sizing:border-box;width:100%;padding:16px} summary:focus-visible{outline:2px solid currentColor;outline-offset:3px}
</style></head><body class="page-macro"><main id="dlg-risk">""" + component + "</main></body></html>"
    (output / "component.html").write_text(shell)
    (output / "context.json").write_text(json.dumps(context, ensure_ascii=False, indent=2) + "\n")
    cases, shots, errors = [], [], []
    selected = {(1440, "dark", "en"), (1440, "light", "zh"), (390, "dark", "en"), (390, "light", "zh")}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, channel=args.browser_channel)
        try:
            page = browser.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            # No external feeds/fonts or model calls participate in this source proof.
            page.route("https://**/*", lambda route: route.abort())
            page.route("http://**/*", lambda route: route.abort())
            for width in [320, 390, 768, 1440]:
                for theme in ["dark", "light"]:
                    for language in ["en", "zh"]:
                        page.set_viewport_size({"width": width, "height": 1000})
                        page.set_content(shell)
                        page.evaluate("([theme,lang])=>{document.documentElement.dataset.theme=theme;document.documentElement.dataset.lang=lang;document.documentElement.lang=lang}", [theme, language])
                        target = page.locator("#gde-multi-asset-context")
                        target.evaluate("el=>{let p=el.parentElement;while(p){if(p.tagName==='DETAILS')p.open=true;p=p.parentElement}}")
                        page.evaluate("document.fonts.ready")
                        assert target.is_visible()
                        assert target.locator("tbody tr").count() == len(UNIVERSE)
                        metrics = page.evaluate("()=>({viewport:innerWidth,scroll:document.documentElement.scrollWidth,component:document.querySelector('#gde-multi-asset-context').getBoundingClientRect().width})")
                        assert metrics["scroll"] <= width + 1, metrics
                        gap = target.evaluate("el=>el.querySelector('details').getBoundingClientRect().top-el.querySelector('#gde-multi-asset-limits').getBoundingClientRect().bottom")
                        assert gap >= 3, (width, theme, language, gap)
                        summary = target.locator("details > summary")
                        summary.focus(); page.keyboard.press("Enter")
                        assert target.locator("details").get_attribute("open") is not None
                        page.keyboard.press("Enter")
                        assert target.locator("details").get_attribute("open") is None
                        case = {"width": width, "theme": theme, "language": language,
                                "horizontal_overflow": False, "keyboard_expand_collapse": True,
                                "rows": len(UNIVERSE), "metrics": metrics, "disclosure_gap_px": gap}
                        cases.append(case)
                        if (width, theme, language) in selected:
                            path = output / (str(width) + "-" + theme + "-" + language + ".png")
                            target.screenshot(path=str(path))
                            shots.append({"path": path.name, "sha256": digest(path.read_bytes()), "bytes": path.stat().st_size})
        finally:
            browser.close()
    assert not errors, errors
    receipt = {
        "schema": "multi_asset.source_component_qualification.v1", "source_revision": args.revision,
        "captured_at": captured.isoformat(), "input_artifacts": inputs,
        "context_status": context["status"], "window": context["window"], "coverage": context["coverage"],
        "context_digest": context["context_digest"], "envelope_bundle_id": envelope["bundle_id"],
        "render_source_sha256": {path: digest((ROOT / path).read_bytes()) for path in BOUND_SOURCES},
        "browser_cases": cases, "screenshots": shots, "page_errors": errors,
        "browser_channel": args.browser_channel or "playwright_chromium",
        "proof_scope": "pinned_source_snapshot_to_existing_builder_and_radar_component",
        "full_page_or_production_acceptance": False, "historical_forecast_validation": False,
        "fonts": "actual Macro host CSS with system fallback; external network disabled",
        "host_template_inputs_sha256": style_inputs, "rendered_css_sha256": digest(css.encode()),
        "raw_price_data_committed": False, "orders_or_policy_changes": False,
    }
    (output / "receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"status": "PASS", "context_status": context["status"], "coverage": context["coverage"],
                      "browser_cases": len(cases), "screenshots": len(shots), "receipt": str(output / "receipt.json")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
