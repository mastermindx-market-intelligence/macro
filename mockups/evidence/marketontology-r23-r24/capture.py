"""Integrated ontology presentation proof using existing page-evidence machinery.
Only the named ontology API receives synthetic fixtures. No credentials, live
market payload, provider calls or production claims. External network blocked.
"""
from __future__ import annotations
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
import sys
import tempfile
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import capture_page_evidence as capture
from engine.ontology_explorer import compose_snapshot
from tests.ontology_explorer_fixtures import SLUG, build_root, chain_state
OUT = Path(__file__).resolve().parent

class FixtureBrowser:
    def __init__(self, browser, snapshot):
        self.browser, self.snapshot = browser, snapshot
    def new_context(self, **kwargs):
        context = self.browser.new_context(**kwargs)
        def route_request(route):
            url = urlparse(route.request.url)
            if url.hostname not in {"127.0.0.1", "localhost"}:
                route.abort()
            elif url.path == "/api/ontology/explorer/v1":
                route.fulfill(status=200, content_type="application/json", body=json.dumps(self.snapshot))
            elif url.path.startswith("/api/"):
                route.fulfill(status=401, content_type="application/json", body='{"detail":"Offline fixture: authentication not supplied"}')
            else:
                route.continue_()
        context.route("**/*", route_request)
        return context
    def close(self):
        self.browser.close()

def main():
    with tempfile.TemporaryDirectory(prefix="mo8260-capture-") as tmp:
        root = build_root(Path(tmp), state_doc=chain_state(confirmed=(False, False, True, True)))
        snapshot = compose_snapshot(root, chain=SLUG, now=datetime(2026, 1, 4, tzinfo=UTC))
    fixture_bytes = json.dumps(snapshot, sort_keys=True, indent=2, ensure_ascii=False).encode()
    (OUT / "fixture.json").write_bytes(fixture_bytes)
    server, port = capture.serve_site_dir(ROOT / "site")
    driver = capture.playwright_page_driver(settle_ms=1250)
    driver._browser = FixtureBrowser(driver._browser, snapshot)
    inputs = ["site/ontology.html", "templates/ontology.js", "templates/ontology.css", "site/theme.css", "site/theme.js", "templates/mm_brain.js"]
    target = {"kind":"rendered_fixture", "production_proof":"none", "fixture":"fixture.json",
        "fixture_sha256":hashlib.sha256(fixture_bytes).hexdigest(),
        "fixture_recipe":"tests/ontology_explorer_fixtures.py",
        "network":"loopback static files and synthetic ontology API only; no credentials",
        "construction_inputs":{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in inputs},
        "adapter_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    try:
        result = capture.run_capture(rows=capture.synthesize_rows(["/ontology.html"], []), driver=driver,
            base_url=f"http://127.0.0.1:{port}", output_dir=OUT/"images", manifest_dir=OUT,
            viewports=["desktop","mobile"], locales=["en","zh"], themes=["dark","light"],
            delay_ms=0, timeout_s=30, generated_at=datetime.now(UTC).isoformat(), target=target,
            force_states=capture.parse_force_states(["primary-hover:hover(.ox-hero-action)","primary-focus:focus(.ox-hero-action)"]))
    finally:
        driver.close(); server.shutdown(); server.server_close()
    for key,name in [("manifest","manifest.json"),("smells","ux-smells.json")]:
        (OUT/name).write_text(json.dumps(result[key],indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({"outcome":result["manifest"]["outcome"],"totals":result["manifest"]["totals"]}))
    for page in result["manifest"]["pages"]:
        print(json.dumps({"route":page.get("route"),"states":[{k:s.get(k) for k in ["viewport","theme","locale","force_state","captured","reason","file"]} for s in page["states"]]}))
    if any(not row.get("captured") for page in result["manifest"]["pages"] for row in page["states"]):
        raise SystemExit(1)

if __name__ == "__main__":
    main()
