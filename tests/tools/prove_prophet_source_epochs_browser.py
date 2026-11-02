"""Local candidate browser proof; synthetic data, ephemeral browser, no live login.

Run from repository root:
python tests/tools/prove_prophet_source_epochs_browser.py --output /tmp/epoch-proof
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import mimetypes
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import pytest
from playwright.sync_api import sync_playwright
from tests.test_prophet_source_epochs_reader import (
    epoch_fixture, run_production_refresh, _bytes,
)



def capture_design_evidence(browser, origin, state, canonical_payload, proof, output):
    """Use the repo's canonical emitter with a real reader-path browser driver."""
    from datetime import datetime, timezone
    from scripts import capture_page_evidence as evidence

    output.mkdir(parents=True, exist_ok=True)
    driver_cells = []

    class ReaderDriver:
        def capture(self, *, url, cell, timeout_s):
            context = browser.new_context(
                viewport={"width": cell.width, "height": cell.height})
            context.add_init_script(
                "localStorage.setItem('theme'," + json.dumps(cell.theme) + ");"
                "localStorage.setItem('lang'," + json.dumps(cell.locale) + ");")
            page = context.new_page()
            page.route("**/*", lambda route: route.continue_()
                       if route.request.url.startswith(origin + "/") else route.abort())
            errors, failures = [], []
            counters = {"requests": 0, "bytes": 0}
            page.on("pageerror", lambda error: errors.append(
                {"text": str(error), "source_url": None}))
            page.on("response", lambda response: failures.append(
                {"url": response.url, "status": response.status})
                if response.status >= 400 else None)
            page.on("request", lambda request: counters.__setitem__(
                "requests", counters["requests"] + 1))

            def finished(request):
                try:
                    counters["bytes"] += int(request.sizes().get("responseBodySize") or 0)
                except Exception:
                    pass

            page.on("requestfinished", finished)
            state.update(payload=canonical_payload, status=200, requests=0)
            try:
                response = page.goto(url, wait_until="domcontentloaded",
                                     timeout=timeout_s * 1000)
                assert response is not None and response.ok
                page.wait_for_function("!document.getElementById('us-life-wall')",
                                       timeout=15000)
                page.locator("#us-src-btn-plan").click()
                disclosure = page.locator("#us-prophet-source-epochs")
                disclosure.wait_for(state="visible")
                disclosure.locator("summary").click()
                assert disclosure.locator("details").evaluate("el => el.open")
                assert disclosure.get_attribute("data-settlement-status") == "PENDING"
                page.evaluate("""() => {
                  const label=document.createElement('p');
                  label.textContent='LOCAL CANDIDATE · SYNTHETIC FIXTURES · NOT PRODUCTION';
                  label.style.cssText='font:12px monospace;color:inherit;margin:0 0 8px';
                  document.getElementById('us-prophet-source-epochs').prepend(label);
                }""")
                disclosure.scroll_into_view_if_needed()
                applied_force = None
                if cell.force_state is not None:
                    # Establish keyboard modality before the canonical focus helper.
                    page.keyboard.press("Tab")
                    applied_force = evidence._apply_interaction_force(page, cell.force_state)
                    assert applied_force == cell.force_state.name
                    assert disclosure.locator("summary").evaluate(
                        "el => el.matches(':focus-visible')")
                applied = page.evaluate("""() => ({
                  theme:document.documentElement.dataset.theme,
                  locale:document.documentElement.dataset.lang,
                  radius:getComputedStyle(document.querySelector(
                    '#us-prophet-source-epochs details')).borderTopLeftRadius
                })""")
                assert applied == {"theme": cell.theme, "locale": cell.locale,
                                   "radius": "8px"}, applied
                assert not errors, errors
                observed = page.evaluate(evidence._OBSERVER_SCRIPT.strip(),
                                         dict(evidence.DEFAULT_OBSERVER_CONFIG)) or {}
                screenshot = page.screenshot(full_page=True)
                driver_cells.append({"cell_id": cell.cell_id, **applied,
                                     "focus_visible": cell.force_state is not None})
                return evidence.CellObservation(
                    cell_id=cell.cell_id, loaded=True, screenshot_png=screenshot,
                    observed=observed, console_errors=tuple(errors),
                    failed_responses=tuple(failures),
                    request_count=counters["requests"],
                    payload_bytes_total=counters["bytes"],
                    applied_theme=applied["theme"], applied_locale=applied["locale"],
                    applied_force_state=applied_force)
            finally:
                context.close()

    target = {
        "kind": "local_synthetic_reader_fixture",
        "resolved_sha_or_none": proof["head"],
        "source_sha256": proof["source_sha256"],
        "harness_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "rendered_html_sha256": proof["rendered_html_sha256"],
        "disclosure": proof["environment"],
        "driver": "ReaderDriver in tests/tools/prove_prophet_source_epochs_browser.py; "
                  "real Plans click and disclosure interaction; no account or live payload",
    }
    result = evidence.run_capture(
        rows=[evidence.normalize_row(
            {"page_id": "macro:us-stocks-prophet-source-epochs",
             "route": "/us_stocks.html", "repo": "macro"}, index=0)],
        driver=ReaderDriver(), base_url=origin, output_dir=output,
        manifest_dir=output, viewports=("desktop", "mobile"),
        locales=("en", "zh"), themes=("dark", "light"), delay_ms=0,
        timeout_s=20, generated_at=datetime.now(timezone.utc).isoformat(),
        target=target,
        selection={"basis": "local production-template synthetic reader path"},
        force_states=evidence.parse_force_states(
            ["epoch_summary_focus:focus(#us-prophet-source-epochs summary)"]))
    manifest = result["manifest"]
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    assert manifest["totals"]["states_captured"] == 16, manifest["totals"]
    assert len(driver_cells) == 16
    receipt = (
        "schema: mastermind.page_evidence_receipt.v1\n"
        "changed_paths:\n"
        "  - templates/_prophet_source_epochs.html.j2\n"
        "manifest: " + (output / "manifest.json").relative_to(ROOT).as_posix() + "\n"
    )
    (output / "EVIDENCE.yml").write_text(receipt)
    proof["canonical_visual_evidence"] = {
        "manifest": (output / "manifest.json").relative_to(ROOT).as_posix(),
        "states": driver_cells,
        "emitter_sha256": evidence.module_source_sha256(),
    }


def prove(output: Path, visual_output: Path | None = None):
    output.mkdir(parents=True, exist_ok=True)
    proof = {
        "schema": "prophet_source_epochs.browser_proof.v1",
        "environment": "local candidate; synthetic data; no production or real account",
        "route": "/us_stocks.html",
        "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "source_sha256": {},
        "matrix": [], "refusal_cases": [], "page_errors": [], "missing_assets": [],
    }
    for name in [
        "engine/prophet_source_epochs.py", "scripts/build_site.py",
        "templates/dashboard.html.j2", "templates/_prophet_source_epochs.html.j2",
        "templates/_prophet_source_epochs.js.j2",
    ]:
        proof["source_sha256"][name] = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
    with tempfile.TemporaryDirectory(prefix="prophet-epoch-browser-") as temporary:
        fixture = epoch_fixture(Path(temporary))
        b = copy.deepcopy(fixture["vm"]["us_standouts"])
        b["buy"][1].update(ticker="BETA", name="Synthetic replacement")
        (fixture["site"] / "factordata" / "us_standouts.json").write_bytes(_bytes(b))
        with pytest.MonkeyPatch.context() as patch:
            run_production_refresh(fixture, patch)
        payload_path = fixture["site"] / "premiumdata" / "us_stocks.json"
        canonical_payload = json.loads(payload_path.read_text())
        proof["rendered_html_sha256"] = hashlib.sha256(
            (fixture["site"] / "us_stocks.html").read_bytes()).hexdigest()
        state = {"payload": canonical_payload, "status": 200, "requests": 0}

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                path = urlsplit(self.path).path
                if path == "/premiumdata/us_stocks.json":
                    state["requests"] += 1
                    content = json.dumps(state["payload"]).encode()
                    self.send_response(state["status"])
                    self.send_header("Content-Type", "application/json")
                else:
                    relative = path.lstrip("/") or "us_stocks.html"
                    candidates = [fixture["site"] / relative, ROOT / "templates" / relative]
                    found = next((p for p in candidates if p.is_file()
                                  and (p.resolve().is_relative_to(fixture["site"].resolve())
                                       or p.resolve().is_relative_to((ROOT / "templates").resolve()))), None)
                    if found is None:
                        proof["missing_assets"].append(path)
                        self.send_response(404)
                        content = b""
                    else:
                        content = found.read_bytes()
                        self.send_response(200)
                    self.send_header("Content-Type", mimetypes.guess_type(relative)[0] or "application/octet-stream")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        origin = f"http://127.0.0.1:{server.server_port}"
        proof["origin"] = "ephemeral loopback HTTP server"
        try:
            with sync_playwright() as runtime:
                browser = runtime.chromium.launch(headless=True)
                proof["browser"] = browser.version
                for width in (1440, 390):
                    for theme in ("dark", "light"):
                        for language in ("en", "zh"):
                            context = browser.new_context(viewport={"width": width, "height": 1000})
                            context.add_init_script(
                                "localStorage.setItem('theme'," + json.dumps(theme) + ");"
                                "localStorage.setItem('lang'," + json.dumps(language) + ");"
                            )
                            page = context.new_page()
                            page.route("**/*", lambda route: route.continue_()
                                       if route.request.url.startswith(origin + "/")
                                       else route.abort())
                            errors = []
                            page.on("pageerror", lambda error: errors.append(str(error)))
                            state.update(payload=canonical_payload, status=200, requests=0)
                            page.goto(origin + "/us_stocks.html", wait_until="domcontentloaded")
                            page.wait_for_function("!document.getElementById('us-life-wall')", timeout=15000)
                            assert state["requests"] == 1
                            page.locator("#us-src-btn-plan").click()
                            disclosure = page.locator("#us-prophet-source-epochs")
                            disclosure.wait_for(state="visible")
                            assert disclosure.get_attribute("data-source-relation") == "SEPARATE_EPOCHS"
                            assert disclosure.get_attribute("data-settlement-status") == "PENDING"
                            assert page.locator("#us-prophet-epoch-refusal").is_hidden()
                            assert page.locator("#us-life-grid").get_by_text("ZEUS", exact=True).count() > 0
                            assert page.locator("#us-cand-grid").get_by_text("BETA", exact=True).count() > 0
                            summary = disclosure.locator("summary")
                            summary.focus()
                            page.keyboard.press("Enter")
                            try:
                                page.wait_for_function("document.querySelector('#us-prophet-source-epochs details').open", timeout=2000)
                            except Exception:
                                print(json.dumps({"keyboard_diagnostic": page.evaluate("({active:document.activeElement.tagName,open:document.querySelector('#us-prophet-source-epochs details').open})")}))
                                disclosure.screenshot(path=str(output / "keyboard-failure.png"))
                                raise
                            page.keyboard.press("Enter")
                            page.wait_for_function("!document.querySelector('#us-prophet-source-epochs details').open", timeout=2000)
                            summary.click()
                            page.wait_for_function("document.querySelector('#us-prophet-source-epochs details').open", timeout=2000)
                            page.evaluate("""() => {
                              const label=document.createElement('p');
                              label.textContent='LOCAL CANDIDATE · SYNTHETIC FIXTURES · NOT PRODUCTION';
                              label.style.cssText='font:12px monospace;color:inherit;margin:0 0 8px';
                              document.getElementById('us-prophet-source-epochs').prepend(label);
                            }""")
                            disclosure.evaluate("el => el.scrollIntoView({block:'center'})")
                            bounds = disclosure.evaluate("""el => ({
                              scrollWidth:el.scrollWidth,clientWidth:el.clientWidth,
                              right:el.getBoundingClientRect().right,
                              viewport:window.innerWidth,
                              summaryHeight:el.querySelector('summary').getBoundingClientRect().height,
                              radius:getComputedStyle(el.querySelector('details')).borderTopLeftRadius,
                              theme:document.documentElement.dataset.theme,
                              lang:document.documentElement.dataset.lang,
                              unoccluded:Array.from(el.querySelectorAll('dd')).every(row=>{
                                const r=row.getBoundingClientRect();
                                const top=document.elementFromPoint(r.left+r.width/2,r.top+r.height/2);
                                return !!top && el.contains(top);
                              })
                            })""")
                            assert bounds["scrollWidth"] <= bounds["clientWidth"] + 1, bounds
                            assert bounds["right"] <= bounds["viewport"] + 1, bounds
                            assert bounds["summaryHeight"] >= 40, bounds
                            assert bounds["radius"] == "8px", bounds
                            assert bounds["unoccluded"], bounds
                            assert bounds["theme"] == theme and bounds["lang"] == language, bounds
                            filename = f"{width}-{theme}-{language}.png"
                            disclosure.screenshot(path=str(output / filename))
                            proof["matrix"].append({
                                "viewport": width, "theme": theme, "language": language,
                                "relation": "SEPARATE_EPOCHS", "settlement": "PENDING",
                                "same_epoch_payload_loaded": True, "keyboard_toggle": True,
                                "pointer_toggle": True, "bounds": bounds, "screenshot": filename,
                                "page_errors": sorted(set(errors)),
                            })
                            page.locator("#us-src-btn-cand").click()
                            assert not disclosure.is_visible()
                            assert page.locator("#us-cand-grid").get_by_text("BETA", exact=True).first.is_visible()
                            proof["matrix"][-1]["return_to_screener"] = True
                            context.close()

                for case in ("different_board", "different_index", "missing", "false_settled", "denied"):
                    payload = copy.deepcopy(canonical_payload)
                    if case == "different_board":
                        payload["source_epochs"]["current_board"]["sha256"] = "a" * 64
                    elif case == "different_index":
                        payload["source_epochs"]["index"]["sha256"] = "b" * 64
                    elif case == "missing":
                        payload.pop("source_epochs")
                    elif case == "false_settled":
                        payload["source_epochs"]["settlement_status"] = "SETTLED"
                    state.update(payload=payload, status=403 if case == "denied" else 200, requests=0)
                    context = browser.new_context(viewport={"width": 390, "height": 1000})
                    page = context.new_page()
                    page.route("**/*", lambda route: route.continue_()
                               if route.request.url.startswith(origin + "/")
                               else route.abort())
                    page.goto(origin + "/us_stocks.html", wait_until="domcontentloaded")
                    page.locator("#us-src-btn-plan").click()
                    if case != "denied":
                        page.locator("#us-prophet-epoch-refusal").wait_for(state="visible", timeout=15000)
                    else:
                        page.wait_for_function("document.getElementById('us-tw-signin') && !document.getElementById('us-tw-signin').hidden", timeout=15000)
                    assert state["requests"] == 1
                    assert page.locator("#us-life-wall").count() == 1
                    assert page.locator("#us-life-grid").get_by_text("ZEUS", exact=True).count() == 0
                    assert page.locator("#us-cand-grid").get_by_text("BETA", exact=True).count() == 0
                    assert page.locator("#us-prophet-source-epochs").get_attribute("data-settlement-status") == "PENDING"
                    proof["refusal_cases"].append({
                        "case": case, "paid_rows_appended": False,
                        "wall_retained": True, "settlement": "PENDING",
                    })
                    if case == "different_index":
                        page.locator("#us-prophet-source-epochs details").evaluate("el => el.open=true")
                        page.locator("#us-prophet-source-epochs").evaluate("el => el.scrollIntoView({block:'center'})")
                        page.locator("#us-prophet-source-epochs").screenshot(path=str(output / "390-refused-index.png"))
                    context.close()
                if visual_output is not None:
                    capture_design_evidence(
                        browser, origin, state, canonical_payload, proof, visual_output)
                browser.close()
        finally:
            server.shutdown()
            server.server_close()
        proof["missing_assets"] = sorted(set(proof["missing_assets"]))
    proof["verdict"] = "PASS"
    (output / "receipt.json").write_text(json.dumps(proof, indent=2) + "\n")
    print(json.dumps({"verdict": proof["verdict"], "matrix_cells": len(proof["matrix"]),
                      "refusal_cases": len(proof["refusal_cases"]), "output": str(output)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--visual-output", type=Path,
                        help="Canonical visual evidence directory inside this checkout.")
    args = parser.parse_args()
    prove(args.output.resolve(),
          args.visual_output.resolve() if args.visual_output else None)
