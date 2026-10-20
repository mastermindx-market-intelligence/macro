"""Browser witness for the actual Bio page, with explicit synthetic auth/API seams.

No server, source intake, entitlement claim, or external network is used. Run from
an owned worktree after rendering the paired Bio assets. Output is QA evidence.
"""
from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import re
from pathlib import Path
import sys
from urllib.parse import parse_qs, urlencode, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lib.site_assets import emit_theme_js
from playwright.sync_api import sync_playwright

FIXTURES = ROOT / "research/catalyst_intelligence/decision_desk_r1/fixtures/company_evidence_r2"
OUT = Path(os.environ.get("DECISION_DESK_QA_DIR", str(ROOT / ".pytest_cache/decision_host_browser")))
ORIGIN = "http://catalyst-host.invalid"


def run() -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    checks, layouts, fonts, calls, errors, missing_assets = [], [], [], [], [], set()
    page_fixture = json.loads((FIXTURES / "company-page.json").read_text())
    row = page_fixture["rows"][0]
    status = {"wmn": 200}
    theme_js = emit_theme_js(ROOT / "templates/theme.js")

    with sync_playwright() as runtime:
        executable = os.environ.get("CATALYST_CHROMIUM_EXECUTABLE")
        browser = runtime.chromium.launch(headless=True, **({"executable_path": executable} if executable else {}))
        context = browser.new_context(viewport={"width": 1440, "height": 1000}, service_workers="block")
        page = context.new_page()
        page.set_default_timeout(10000)
        page.on("pageerror", lambda error: errors.append(str(error)))

        def route(request_route):
            request = request_route.request
            parsed = urlsplit(request.url)
            if parsed.netloc != "catalyst-host.invalid":
                request_route.fulfill(status=204, body="")
                return
            if parsed.path.startswith("/api/biocatalyst/"):
                calls.append({"path": parsed.path, "query": parsed.query,
                              "synthetic_auth_present": request.headers.get("authorization") == "Bearer synthetic-browser-token"})
                headers = {"cache-control": "private, no-store", "vary": "Authorization"}
                if not calls[-1]["synthetic_auth_present"]:
                    request_route.fulfill(status=401, content_type="application/json", body='{"detail":"synthetic access required"}', headers=headers)
                    return
                if "what-matters-next" not in parsed.path:
                    request_route.fulfill(status=403, content_type="application/json", body='{"detail":"synthetic legacy source unavailable"}', headers=headers)
                    return
                if status["wmn"] != 200:
                    request_route.fulfill(status=status["wmn"], content_type="application/json", body='{"detail":"synthetic correction or access refusal"}', headers=headers)
                    return
                query = parse_qs(parsed.query)
                if parsed.path.endswith("/detail"):
                    raw = (FIXTURES / "company-detail.json").read_bytes()
                else:
                    view = query.get("view", ["upcoming"])[0]
                    days = query.get("horizon_days", ["None"])[0]
                    name = f"page-{view}-{days}.json"
                    raw = (FIXTURES / name).read_bytes()
                request_route.fulfill(status=200, content_type="application/json", body=raw, headers=headers)
                return
            relative = parsed.path.lstrip("/")
            if ".." in Path(relative).parts:
                request_route.fulfill(status=400, body="")
                return
            if relative == "theme.js":
                request_route.fulfill(status=200, content_type="application/javascript", body=theme_js)
                return
            for family in ("site", "templates"):
                candidate = ROOT / family / relative
                if candidate.is_file() and candidate.resolve().is_relative_to((ROOT / family).resolve()):
                    request_route.fulfill(status=200, content_type=mimetypes.guess_type(relative)[0] or "application/octet-stream", body=candidate.read_bytes())
                    return
            missing_assets.add(relative)
            request_route.fulfill(status=204, body="")

        context.route("**/*", route)
        root = page.locator("#bci-decision-root")

        def loaded():
            root.locator(".bci-dd-card").first.wait_for(state="visible")

        def auth(account="qa-account-a"):
            page.evaluate("""id => {
              window.__hostQaUser = id ? {id} : null;
              window.MDXAuth = {
                user: () => window.__hostQaUser,
                client: () => Promise.resolve({auth: {getSession: () => Promise.resolve({data: {
                  session: window.__hostQaUser ? {access_token: 'synthetic-browser-token', user: window.__hostQaUser} : null
                }})}})
              };
              window.dispatchEvent(new CustomEvent('mdx-auth', {detail: {user: window.__hostQaUser, event: id ? 'SIGNED_IN' : 'SIGNED_OUT'}}));
            }""", account)

        try:
            page.goto(ORIGIN + "/biocatalyst.html", wait_until="networkidle")
            assert not calls, "anonymous shell must not read the owner source"
            assert root.locator(".bci-dd-card").count() == 0
            assert page.locator("#bci-source-research").get_attribute("open") is None
            assert page.locator("#mmb-boot").count() == 1, "shared launcher stub must actually be present"
            page.set_viewport_size({"width": 390, "height": 844})
            assert not page.locator("#mmb-boot").is_visible(), "Mobile Bio source drill-down must not have an overlapping duplicate Brain trigger"
            page.set_viewport_size({"width": 1440, "height": 1000})
            assert page.locator("#mmb-boot").is_visible(), "desktop keeps the canonical shared Brain trigger"
            checks.append("Mobile suppresses the duplicate lazy Brain trigger; desktop preserves the existing launcher")
            checks.append("Actual data-free page mounts primary Decision Desk before any source request")
            # Real keyboard modality + computed paint, not focus identity alone.
            for focus_theme in ("dark", "light"):
                page.evaluate("value => document.documentElement.dataset.theme = value", focus_theme)
                page.keyboard.press("Tab")
                summary = page.locator("#bci-source-research > summary")
                summary.focus()
                paint = summary.evaluate("""node => { const s=getComputedStyle(node); return {
                  visible:node.matches(':focus-visible'), style:s.outlineStyle,
                  width:parseFloat(s.outlineWidth), color:s.outlineColor,
                  token:s.getPropertyValue('--link').trim()}; }""")
                assert paint["visible"] and paint["style"] == "solid" and paint["width"] >= 2, paint
                assert paint["token"] and paint["color"] not in ("transparent", "rgba(0, 0, 0, 0)"), paint
            page.evaluate("document.documentElement.dataset.theme='dark'")
            checks.append("Trial evidence keyboard focus has an actually painted outline in both themes")
            auth(); loaded()
            assert all(c["path"].endswith("what-matters-next") for c in calls)
            assert all(c["synthetic_auth_present"] for c in calls)
            checks.append("Actual host fetchJson attaches synthetic test session; collapsed trial tools do not fetch")
            root.locator("[data-open-key]").first.click()
            root.locator('[role="tabpanel"]').wait_for()
            root.locator('[data-tab="sources"]').click()
            links = root.locator('[role="tabpanel"] a').evaluate_all("nodes => nodes.map(node => node.href)")
            assert any(link.startswith("https://www.sec.gov/") for link in links), links
            assert "bci_case=" in page.url and "bci_task=sources" in page.url
            checks.append("Case opens real detail handler consumer and source-context link; URL records selected task")
            page.go_back(); loaded()
            page.wait_for_function("document.querySelector('#bci-decision-root [data-tab=setup]')?.getAttribute('aria-selected') === 'true'")
            checks.append("Browser Back restores Setup without a history echo")
            direct = {"bci_case": row["event_fact_ref"], "bci_issuer": row["row_key"]["issuer_id"], "bci_task": "sources", "unrelated": "keep"}
            page.goto(ORIGIN + "/biocatalyst.html?" + urlencode(direct), wait_until="networkidle")
            auth(); loaded(); root.locator('[role="tabpanel"] a').first.wait_for()
            assert "unrelated=keep" in page.url
            checks.append("Direct case link restores only an admitted loaded row and preserves unrelated URL state")
            for theme in ("dark", "light"):
                for language in ("en", "zh"):
                    for width in (320, 390, 768, 1440):
                        page.set_viewport_size({"width": width, "height": 1000 if width > 390 else 844})
                        page.evaluate("""([theme, language]) => {
                          document.documentElement.dataset.theme = theme;
                          document.documentElement.dataset.lang = language;
                          document.dispatchEvent(new Event('langchange'));
                        }""", [theme, language])
                        loaded(); root.locator('[role="tabpanel"]').wait_for()
                        geometry = root.evaluate("""node => {
                          const r=node.getBoundingClientRect();
                          return {left:r.left,right:r.right,width:innerWidth,scroll:document.documentElement.scrollWidth};
                        }""")
                        assert geometry["left"] >= -1 and geometry["right"] <= width + 1, geometry
                        assert geometry["scroll"] <= width + 1, geometry
                        layouts.append({"theme": theme, "language": language, "width": width, "geometry": geometry})
                        if language == "zh":
                            cdp = context.new_cdp_session(page)
                            cdp.send("DOM.enable"); cdp.send("CSS.enable")
                            document = cdp.send("DOM.getDocument")
                            node = cdp.send("DOM.querySelector", {"nodeId": document["root"]["nodeId"], "selector": "#bci-decision-root h2"})
                            found = cdp.send("CSS.getPlatformFontsForNode", {"nodeId": node["nodeId"]})["fonts"]
                            assert found and not any("LastResort" in f["familyName"] for f in found), found
                            fonts.append({"width": width, "theme": theme, "fonts": found})
                            cdp.detach()
                        if (theme, language, width) in [("dark", "en", 1440), ("light", "zh", 390)]:
                            page.screenshot(path=str(OUT / f"host-{theme}-{language}-{width}.png"), full_page=True)
            checks.append("Actual integrated page fits 16 theme/language/viewport combinations with eight CJK font inspections")
            page.evaluate("document.documentElement.dataset.lang='en';document.dispatchEvent(new Event('langchange'))")
            loaded(); root.locator('[role="tabpanel"]').wait_for()
            count = len(calls); auth(None)
            assert root.locator(".bci-dd-card").count() == 0 and root.locator('[role="tabpanel"]').count() == 0
            page.wait_for_timeout(100)
            assert len(calls) == count
            checks.append("Idle logout synchronously clears case/detail without an anonymous source fetch")
            auth(); loaded(); status["wmn"] = 503
            root.get_by_role("button", name=re.compile(r"^Refresh")).click()
            page.wait_for_function("document.querySelectorAll('#bci-decision-root .bci-dd-card').length === 0")
            assert root.locator('[role="tabpanel"]').count() == 0
            status["wmn"] = 200; root.get_by_role("button", name=re.compile(r"^Refresh")).click(); loaded()
            checks.append("Unavailable corrected composition clears old case and permits later fresh recovery")
            page.evaluate("window.dispatchEvent(new PageTransitionEvent('pagehide',{persisted:true}))")
            assert root.locator(".bci-dd-card").count() == 0
            page.evaluate("window.dispatchEvent(new PageTransitionEvent('pageshow',{persisted:true}))")
            loaded(); checks.append("Simulated BFCache lifecycle event clears and revalidates; not a real cache-admission claim")
            page.locator("#bci-source-research > summary").click()
            page.wait_for_function("document.querySelector('#bci-workspace').dataset.state === 'locked'")
            assert any(c["path"].endswith("catalyst-radar") for c in calls)
            assert root.locator(".bci-dd-card").first.is_visible(), "legacy source refusal must not hide a valid WMN case"
            checks.append("Secondary legacy controls remain reachable and preserve paid/source refusal independently")
            page.goto(ORIGIN + "/biocatalyst.html?bci_case=unknown-case", wait_until="networkidle")
            before = len(calls); auth(); loaded()
            assert "not in the loaded review" in page.locator("#bci-decision-route-status").inner_text()
            assert not any(c["path"].endswith("/detail") for c in calls[before:])
            checks.append("Unknown direct case is explained without inventing or fetching another universe")
            page.goto(ORIGIN + "/biocatalyst.html?bci_case=a&bci_case=b", wait_until="networkidle")
            before = len(calls); auth(); page.wait_for_timeout(100)
            assert len(calls) == before and root.locator(".bci-dd-card").count() == 0
            checks.append("Ambiguous direct case route makes zero source requests")
            assert not errors, errors
            return {"status": "PASS", "browser_version": browser.version, "checks": checks,
                    "layouts": layouts, "cjk_fonts": fonts, "page_errors": errors,
                    "source_requests": calls, "optional_assets_unavailable": sorted(missing_assets),
                    "auth": "synthetic MDXAuth session, not a production entitled account",
                    "api": "exact retained synthetic R2 owner/API fixtures; no native admission or live data",
                    "html_sha256": hashlib.sha256((ROOT / "site/biocatalyst.html").read_bytes()).hexdigest(),
                    "theme_sha256": hashlib.sha256(theme_js.encode()).hexdigest()}
        except Exception:
            page.screenshot(path=str(OUT / "failure.png"), full_page=True)
            (OUT / "failure.json").write_text(json.dumps({"checks": checks, "errors": errors, "url": page.url, "body_tail": page.locator("body").inner_text()[-3500:]}, indent=2))
            raise
        finally:
            context.close(); browser.close()


if __name__ == "__main__":
    result = run()
    (OUT / "verification.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"status": result["status"], "checks": len(result["checks"]), "layouts": len(result["layouts"]), "font_checks": len(result["cjk_fonts"]), "page_errors": result["page_errors"], "output": str(OUT)}))
