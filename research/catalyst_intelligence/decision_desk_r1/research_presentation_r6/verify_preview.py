"""Verify only the new synthetic company-research preview, with network disabled."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import runpy
from urllib.parse import urlencode, urlsplit

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
ORIGIN = "http://catalyst-research.invalid"


def verify(output: Path) -> dict:
    if output.exists():
        raise FileExistsError("Choose a fresh R6 evidence directory")
    output = output.resolve()
    # Never put this new proof in an accepted previous capture directory.
    if not output.is_relative_to(HERE.resolve()):
        raise ValueError("R6 evidence belongs under this new research-presentation directory")
    helpers = runpy.run_path(str(HERE / "build_preview.py"))
    captures = helpers["load_captures"]()
    output.mkdir(parents=True)
    html_path = helpers["build"](output / "Research_Assessment_Contract_Replay.html")
    html = html_path.read_text(encoding="utf-8")
    checks, layouts, fonts, errors, network = [], [], [], [], []
    source_paths = [
        "templates/catalyst_research_assessment.js",
        "templates/biocatalyst_decision_desk.css",
        "research/catalyst_intelligence/decision_desk_r1/theme_excerpt.css",
        "research/catalyst_intelligence/decision_desk_r1/research_presentation_r6/build_preview.py",
        "research/catalyst_intelligence/decision_desk_r1/research_presentation_r6/preview_shell.html",
        "research/catalyst_intelligence/decision_desk_r1/research_presentation_r6/verify_preview.py",
    ]
    with sync_playwright() as runtime:
        executable = os.environ.get("CATALYST_CHROMIUM_EXECUTABLE")
        browser = runtime.chromium.launch(headless=True, **({"executable_path": executable} if executable else {}))
        context = browser.new_context(service_workers="block")
        page = context.new_page()
        page.set_default_timeout(10000)
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)

        def route(request_route):
            request = request_route.request
            parsed = urlsplit(request.url)
            if parsed.netloc == "catalyst-research.invalid" and parsed.path == "/" and request.resource_type == "document":
                request_route.fulfill(status=200, content_type="text/html", body=html)
            else:
                network.append(request.url)
                request_route.abort()
        context.route("**/*", route)
        root = page.locator("#research")

        def open_case(case="delayed_reconstruction", locale="en", theme="dark", width=1440):
            page.set_viewport_size({"width": width, "height": 1000 if width == 1440 else 844})
            page.goto(ORIGIN + "/?" + urlencode({"case": case, "lang": locale, "theme": theme}))
            root.locator("h2").wait_for(state="visible")

        for case in captures:
            for locale in ("en", "zh"):
                for theme in ("dark", "light"):
                    for width in (1440, 390):
                        open_case(case, locale, theme, width)
                        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), "horizontal page overflow"
                        assert root.locator("h2").inner_text().strip()
                        assert not root.locator("button,a").count(), "research output must not offer a trade or navigation action"
                        assert root.locator("details").count(), "source/timing disclosure missing"
                        # Open evidence deliberately to inspect wrapping and identity rather than hide it.
                        root.locator("details").first.evaluate("(node) => node.open = true")
                        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), "expanded source overflow"
                        text = root.inner_text()
                        assert "sha256:" in text and captures[case]["focal"]["identity_epoch"] in text
                        filename = f"{case}-{theme}-{locale}-{width}.png"
                        page.screenshot(path=str(output / filename), full_page=True)
                        layouts.append({
                            "case": case, "locale": locale, "theme": theme, "width": width,
                            "screenshot": filename, "sha256": hashlib.sha256((output / filename).read_bytes()).hexdigest(),
                        })
                        if locale == "zh":
                            session = context.new_cdp_session(page)
                            session.send("DOM.enable"); session.send("CSS.enable")
                            document = session.send("DOM.getDocument")
                            node = session.send("DOM.querySelector", {"nodeId": document["root"]["nodeId"], "selector": "#research h2"})
                            used = session.send("CSS.getPlatformFontsForNode", {"nodeId": node["nodeId"]})["fonts"]
                            assert any(item["glyphCount"] > 0 and item["familyName"] != "LastResort" for item in used), "Chinese font fallback unavailable"
                            fonts.append({"case": case, "theme": theme, "width": width, "fonts": used})
                            session.detach()
        checks.append("two exact owner captures render in sixteen EN/ZH, dark/light and desktop/mobile states")

        open_case()
        original = root.inner_text()
        page.select_option("#previewCase", "history_missing")
        missing = root.inner_text()
        assert original != missing, "missing comparison must have a distinct presentation"
        assert page.evaluate("researchPreview.captures.history_missing.news_context.current.views.length") > 0
        checks.append("missing prior evidence remains distinct while current company evidence survives")

        page.select_option("#previewLanguage", "zh")
        assert page.evaluate("document.documentElement.lang") == "zh-CN"
        assert root.inner_text() != missing
        page.select_option("#previewTheme", "light")
        assert page.evaluate("document.documentElement.dataset.theme") == "light"
        checks.append("language and theme controls update the actual component")

        open_case()
        assert page.evaluate("""() => {
          const packet=JSON.parse(JSON.stringify(researchPreview.captures.delayed_reconstruction));
          packet.peer_context.context.cohort.formed_at='2026-09-28T13:00Z';
          packet.peer_context.context.window.end_at='2026-09-28T20:00Z';
          return researchPreview.component.setAssessment(packet);
        }""")
        assert "Peer movement" in root.inner_text()
        checks.append("producer-valid reduced peer clocks render without relaxing strict v3 envelopes")

        for fault in ("blocked_open", "retrospective_cohort"):
            accepted = page.evaluate("""fault => {
              const packet=JSON.parse(JSON.stringify(researchPreview.captures.delayed_reconstruction));
              if (fault==='blocked_open') {
                packet.entry_context.owner_projection.state='ENTRY_OPEN';
                packet.entry_context.owner_projection.entry_open=true;
              } else {
                packet.peer_context.context.cohort.formed_at=packet.peer_context.context.window.end_at;
              }
              return researchPreview.component.setAssessment(packet);
            }""", fault)
            assert accepted is False
            assert root.locator("h2").inner_text() == "Research unavailable"
            assert root.locator("details").count() == 0
        checks.append("blocked-open entry and retrospective cohorts refuse without retaining old content")

        open_case()
        marker = '<img src=x onerror="window.researchInjected=true">'
        page.evaluate("""marker => {
          const packet=JSON.parse(JSON.stringify(researchPreview.captures.delayed_reconstruction));
          packet.news_context.current.views[0].display.plain_status=marker;
          researchPreview.component.setAssessment(packet);
        }""", marker)
        assert marker in root.inner_text()
        assert root.locator("img,iframe,script").count() == 0
        assert page.evaluate("window.researchInjected === undefined")
        checks.append("owner-authored evidence is text and cannot execute markup")

        page.evaluate("""() => {
          const packet=JSON.parse(JSON.stringify(researchPreview.captures.delayed_reconstruction));
          packet.source_admission_established=true;
          try { researchPreview.component.setAssessment(packet); } catch (_) {}
        }""")
        assert marker not in root.inner_text()
        assert root.locator("h2").inner_text() == "Research unavailable"
        refused = root.text_content()
        assert all(value not in refused for value in ("+12%", "cik:0001045810", "Peer movement", "sha256:"))
        assert root.locator("details,.bci-dd-card").count() == 0
        checks.append("an invalid replacement clears all prior research content synchronously")

        page.evaluate("researchPreview.component.setAssessment(researchPreview.captures.delayed_reconstruction)")
        assert root.locator("h2").count() == 1
        page.evaluate("researchPreview.component.destroy()")
        assert not root.inner_text().strip()
        checks.append("a restored valid packet renders and teardown removes the view")
        assert not network, network
        assert not errors, errors
        checks.append("no network calls, browser exceptions or console errors")
        browser_version = browser.version
        browser.close()
    receipt = {
        "schema": "catalyst.research_presentation_browser.v1",
        "scope": "SYNTHETIC_RESEARCH_PREVIEW_ONLY",
        "owner_head": helpers["OWNER_HEAD"],
        "owner_receipt_sha256": helpers["RECEIPT_SHA256"],
        "source_admission": False, "live_wmn_binding": False,
        "entitled_runtime_verified": False, "production_publication_verified": False,
        "browser": browser_version, "checks": checks, "layouts": layouts,
        "font_checks": fonts, "network_requests": network, "browser_errors": errors,
        "source_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in source_paths},
        "html_sha256": hashlib.sha256(html_path.read_bytes()).hexdigest(),
    }
    (output / "verification.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    receipt = verify(parser.parse_args().output_dir)
    print(json.dumps({"checks": len(receipt["checks"]), "layouts": len(receipt["layouts"]),
                      "font_checks": len(receipt["font_checks"]), "errors": receipt["browser_errors"]}))
