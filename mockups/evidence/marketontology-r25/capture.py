"""R25 integrated-page proof through the existing page-evidence driver.
Only ontology/Brain service responses are synthetic; the page, lazy loader,
widget, tokens, request builder and real controls are the current site assets.
No credentials, provider calls, source-owner writes or production claims.
"""
from __future__ import annotations
import hashlib
import json
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import capture_page_evidence as capture
from engine.ontology_explorer import compose_snapshot
from tests.ontology_explorer_fixtures import SLUG, build_root, chain_state
OUT = Path(__file__).resolve().parent


class FixturePage:
    def __init__(self, page, owner):
        self.page, self.owner = page, owner

    def __getattr__(self, name):
        return getattr(self.page, name)

    def goto(self, url, **kwargs):
        self.owner.mode = parse_qs(urlparse(url).query).get("r25", ["matched"])[0]
        response = self.page.goto(url, **kwargs)
        self.page.wait_for_selector("#ox-steps .ox-leg", state="attached")
        self.page.evaluate("""() => {
            window.MDXAuth = {enabled: () => false,
                user: () => ({id: 'synthetic-proof-user'}),
                onChange: callback => callback({id: 'synthetic-proof-user'})};
            document.querySelector('.ox-hero-action').click();
        }""")
        self.page.locator(".ox-brain-action").first.click()
        self.page.wait_for_selector("#mmb-panel.open #mmb-ta", state="visible")
        lang = self.page.get_attribute("html", "data-lang")
        self.page.locator("#mmb-ta").fill("解释此环节" if lang == "zh" else "Explain this selected step")
        self.page.locator("#mmb-send").click()
        self.page.wait_for_selector(".mmb-ontology-receipt", state="visible")
        self.page.locator(".mmb-ontology-receipt").scroll_into_view_if_needed()
        return response


class FixtureContext:
    def __init__(self, context, snapshot, lang):
        self.context, self.snapshot, self.lang = context, snapshot, lang
        self.mode = "matched"
        context.route("**/*", self.route)

    def __getattr__(self, name):
        return getattr(self.context, name)

    def new_page(self):
        return FixturePage(self.context.new_page(), self)

    def route(self, route):
        url = urlparse(route.request.url)
        def reply(body):
            route.fulfill(status=200, content_type="application/json", body=json.dumps(body))
        if url.hostname not in {"127.0.0.1", "localhost"}:
            route.abort()
        elif url.path == "/api/ontology/explorer/v1":
            reply(self.snapshot)
        elif url.path == "/api/brain/me":
            reply({"tier": "pro", "quotas": {lane: {"lane": lane, "remaining": 10, "limit": 10}
                                                   for lane in ("fast", "pro")}})
        elif url.path == "/api/brain/threads":
            reply({"threads": []})
        elif url.path == "/api/brain/stream":
            request = route.request.post_data_json
            ref = request.get("context", {}).get("ontology_selection")
            source = self.snapshot["source"]
            leg = self.snapshot["path"]["legs"][0]
            expected = {"chain": source["chain"], "revision": source["rev"],
                        "asof": source["asof"], "manifest_hash": source["source_manifest_hash"],
                        "node_id": leg["node_id"]}
            assert ref == expected, "The actual widget must forward the fixture's exact reference"
            matched = self.mode == "matched"
            receipt = {"schema": "ontology_selection_receipt.v1", "status": "unverified"}
            if matched:
                receipt.update(status="matched", scope="selected_read_at_turn_start", reference=expected,
                    step_title=leg["title"][self.lang], path_title=self.snapshot["path"]["title"][self.lang])
            text = (("前两个条件未满足。后段读数为真，并不能激活这条路径。" if self.lang == "zh" else
                     "The first two conditions are not met. Later true readings do not activate this path.") if matched else
                    ("所选路径证据未能核验。请刷新路径后重新选择环节。" if self.lang == "zh" else
                     "The selected path evidence could not be verified. Refresh the path and select the step again."))
            events = [{"type": "meta", "thread_id": None}, {"type": "delta", "text": text},
                      {"type": "done", "citations": [], "selection_unverified": not matched,
                       "ontology_selection_receipt": receipt, "degraded": False}]
            route.fulfill(status=200, content_type="text/event-stream",
                          body="".join("data: " + json.dumps(event) + "\n\n" for event in events))
        elif url.path.startswith("/api/"):
            route.fulfill(status=401, content_type="application/json", body='{"detail":"Offline fixture only"}')
        else:
            route.continue_()


class FixtureBrowser:
    def __init__(self, browser, snapshot):
        self.browser, self.snapshot = browser, snapshot

    def new_context(self, **kwargs):
        return FixtureContext(self.browser.new_context(**kwargs), self.snapshot,
                              "zh" if kwargs.get("locale", "").startswith("zh") else "en")

    def close(self):
        self.browser.close()


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke", action="store_true", help="One bounded cell in a separate smoke directory")
    args = parser.parse_args()
    out = OUT / "smoke" if args.smoke else OUT
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="mo-r25-evidence-") as tmp:
        source_root = build_root(Path(tmp), state_doc=chain_state(confirmed=(False, False, True, True)))
        snapshot = compose_snapshot(source_root, chain=SLUG, now=datetime(2026, 1, 4, tzinfo=UTC))
    fixture = json.dumps(snapshot, indent=2, sort_keys=True, ensure_ascii=False).encode()
    (out / "fixture.json").write_bytes(fixture)
    server, port = capture.serve_site_dir(ROOT / "site")
    driver = capture.playwright_page_driver(settle_ms=750)
    driver._browser = FixtureBrowser(driver._browser, snapshot)
    inputs = ["site/ontology.html", "site/ontology.js", "site/ontology.css", "site/theme.js",
              "site/theme.css", "site/mm_brain.js", "templates/ontology.js", "templates/ontology.css",
              "templates/mm_brain.js", "tests/ontology_explorer_fixtures.py"]
    target = {"kind": "rendered_fixture", "production_proof": "none",
              "fixture": "fixture.json", "fixture_sha256": hashlib.sha256(fixture).hexdigest(),
              "network": "loopback static assets and synthetic ontology/Brain API responses only",
              "construction_inputs": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in inputs},
              "adapter_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "response_limits": "The real widget is driven by disclosed matched/unverified service fixtures; this is not backend runtime or entitlement proof."}
    routes = ["/ontology.html?r25=matched"] if args.smoke else [
        "/ontology.html?r25=matched", "/ontology.html?r25=unverified"]
    try:
        result = capture.run_capture(
            rows=capture.synthesize_rows(routes, []), driver=driver,
            base_url=f"http://127.0.0.1:{port}", output_dir=out / "images", manifest_dir=out,
            viewports=["mobile"] if args.smoke else ["desktop", "mobile"],
            locales=["en"] if args.smoke else ["en", "zh"],
            themes=["dark"] if args.smoke else ["dark", "light"],
            delay_ms=0, timeout_s=30, generated_at=datetime.now(UTC).isoformat(), target=target,
            force_states=[] if args.smoke else capture.parse_force_states([
                "control-hover:hover(.mmb-ontology-return,#mmb-ta)",
                "control-focus:focus(.mmb-ontology-return,#mmb-ta)"]))
    finally:
        driver.close()
        server.shutdown()
        server.server_close()
    for key, filename in [("manifest", "manifest.json"), ("smells", "ux-smells.json")]:
        (out / filename).write_text(json.dumps(result[key], indent=2, ensure_ascii=False) + "\n")
    rows = [state for page in result["manifest"]["pages"] for state in page["states"]]
    print(json.dumps({"outcome": result["manifest"]["outcome"], "totals": result["manifest"]["totals"],
                      "failed": [{key: state.get(key) for key in ["viewport", "locale", "theme", "reason"]}
                                 for state in rows if not state.get("captured")]}))
    if any(not state.get("captured") for state in rows):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
