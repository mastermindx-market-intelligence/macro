"""Isolated Chromium dialog replay. No production or canonical-state writes."""
from __future__ import annotations
import argparse, copy, hashlib, json, mimetypes, sys, time
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlsplit, unquote
from urllib.request import Request, urlopen
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from scripts import watch_release_publications as watcher

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    out = ap.parse_args().out
    out.mkdir(parents=True, exist_ok=True)
    if (out / "public_before.json").exists() and (out / "isolated_recovery.json").exists():
        # Retain the exact observed incident and archive replay across UI retries.
        public = json.loads((out / "public_before.json").read_text())
        recovered = json.loads((out / "isolated_recovery.json").read_text())
        before = next(r for r in public["publications"] if r.get("event_id") == "cpi:2026-10-14")
    else:
        with urlopen(Request("https://www.mastermind-x.com/live/release_publications.json",
                     headers={"Cache-Control": "no-cache"}), timeout=15) as response:
            public = json.load(response)
        before = next(r for r in public["publications"] if r.get("event_id") == "cpi:2026-10-14")
        assert before["data_ready"] is False, "Incident changed; do not invent a before state"
        original_schedule = watcher.scheduled_releases
        try:
            watcher.scheduled_releases = lambda *_a, **_kw: []
            _, recovered = watcher.detect(now=datetime.now(timezone.utc), timeout=15,
                state={"publications": {before["event_id"]: copy.deepcopy(before)}})
        finally:
            watcher.scheduled_releases = original_schedule
    after = next(r for r in recovered["publications"] if r.get("event_id") == before["event_id"])
    assert after["data_ready"] is True and after.get("actual")
    assert after["detected_at"] == before["detected_at"]
    for name, value in (("public_before.json", public), ("isolated_recovery.json", recovered)):
        (out / name).write_text(json.dumps(value, indent=2))
    soup = BeautifulSoup((ROOT / "site/macro.html").read_text(), "html.parser")
    modal = soup.find(id="dlg-events")
    # Replay the actual dialog controller, including its entrance classes. The
    # isolated fixture supplies an authorized tier; no live session is touched.
    dialog_controller = next(s.string for s in soup.find_all("script")
        if "window.mx5OpenDlg = function(id)" in (s.string or ""))
    styles = "\n".join(str(link) for link in soup.find_all("link", rel="stylesheet"))
    fixed = "2026-10-14T12:31:45Z"
    results = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome", headless=True)
        try:
            for theme in ("light", "dark"):
                for language in ("en", "zh"):
                    for label, size in (("desktop", {"width":1126,"height":1102}),
                                        ("mobile", {"width":390,"height":844})):
                        context = browser.new_context(viewport=size)
                        page = context.new_page()
                        page.add_init_script("""
                            const RealDate = Date;
                            const fixtureNow = RealDate.parse("2026-10-14T12:31:45Z");
                            const fixtureStart = RealDate.now();
                            const fixtureClock = () => fixtureNow + RealDate.now() - fixtureStart;
                            window.Date = class extends RealDate {
                              constructor(...args) { super(...(args.length ? args : [fixtureClock()])); }
                              static now() { return fixtureClock(); }
                            };
                        """)
                        verified = copy.deepcopy(after)
                        verified["verified_at"] = fixed
                        for key in ("last_attempt_at", "last_success_at"):
                            if isinstance(verified.get("extraction"), dict):
                                verified["extraction"][key] = fixed
                        active = {"verified":False, "polls":0, "documents":0}
                        errors = []
                        page.on("pageerror", lambda error: errors.append(str(error)))
                        html = (f'<html data-theme="{theme}" data-lang="{language}" lang="{language}">'
                            f'<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">{styles}</head>'
                            f'<body class="page-macro mx4-grid"><div class="grid">'
                            f'<div class="panel span12 mx5-rack-panel">{modal}</div></div>'
                            '<script>window.MMXAccessPreview={isAnon:()=>false};</script>'
                            f'<script>{dialog_controller}</script>'
                            '<script src="/release_publications_live.js"></script></body></html>')
                        def serve(route):
                            parsed = urlsplit(route.request.url)
                            name = unquote(parsed.path).lstrip("/")
                            if parsed.hostname != "calendar-regression.test":
                                route.abort(); return
                            if name == "macro.html":
                                active["documents"] += 1
                                route.fulfill(status=200,content_type="text/html",body=html); return
                            if name == "live/release_publications.json":
                                active["polls"] += 1
                                envelope = {"schema":"release_publications.v2", "built":fixed,
                                    "publications":[verified if active["verified"] else before],
                                    "events":[{"event_id":before["event_id"],"type":"CPI","date":"2026-10-14",
                                        "time_et":"08:30","scheduled_at":"2026-10-14T08:30:00-04:00",
                                        "data_ready":active["verified"],
                                        "status":"published" if active["verified"] else "published_unparsed"}]}
                                route.fulfill(status=200,content_type="application/json",
                                    headers={"Cache-Control":"no-store"},body=json.dumps(envelope)); return
                            asset = (ROOT / "site" / name).resolve()
                            if asset.is_relative_to((ROOT / "site").resolve()) and asset.is_file():
                                route.fulfill(status=200,body=asset.read_bytes(),
                                    content_type=mimetypes.guess_type(name)[0] or "application/octet-stream")
                            else: route.fulfill(status=404,body="Not in isolated fixture")
                        page.route("**/*", serve)
                        page.goto("http://calendar-regression.test/macro.html",wait_until="domcontentloaded")
                        page.evaluate("window.mx5OpenDlg('dlg-events')")
                        page.locator('.mx-live-event-card[data-live-verified="false"]').wait_for(state="visible",timeout=10000)
                        page.wait_for_function("""() => {
                            const card = document.querySelector('.mx-live-event-card[data-live-verified="false"]');
                            if (!card) return false;
                            for (let n=card; n; n=n.parentElement) {
                                if (Number(getComputedStyle(n).opacity) < .99) return false;
                            }
                            const r=card.getBoundingClientRect();
                            return card.contains(document.elementFromPoint(r.left+r.width/2,r.top+20));
                        }""", timeout=5000)
                        page.evaluate("window.__regressionDialog = document.getElementById('dlg-events')")
                        started = time.monotonic()
                        active["verified"] = True
                        page.locator('.mx-live-event-card[data-live-verified="true"]').wait_for(state="visible",timeout=5000)
                        elapsed = (time.monotonic()-started)*1000
                        assert elapsed < 2600, elapsed
                        assert active["documents"] == 1
                        assert page.evaluate("window.__regressionDialog === document.getElementById('dlg-events')")
                        assert not errors, errors
                        painted = page.locator('.mx-live-event-card[data-live-verified="true"]').evaluate("""el => {
                            const r = el.getBoundingClientRect();
                            const hit = document.elementFromPoint(r.left + r.width/2, r.top + Math.min(r.height/2, 40));
                            return {hit: hit && hit.tagName, contains: el.contains(hit),
                              ancestors: [el, el.parentElement, el.parentElement.parentElement,
                                el.closest(".mx5-dlg"), el.closest(".grid"), document.body].filter(Boolean).map(n => {
                                  const s = getComputedStyle(n); const b = n.getBoundingClientRect();
                                  return {tag:n.tagName, cls:n.className, opacity:s.opacity, display:s.display,
                                    visibility:s.visibility, contain:s.contain, overflow:s.overflow,
                                    transform:s.transform, width:b.width, height:b.height}; })};
                        }""")
                        assert painted["contains"], painted
                        shot = f"{theme}_{language}_{label}.png"
                        page.screenshot(path=str(out/shot),full_page=False)
                        results.append({"theme":theme,"language":language,"viewport":label,
                            "snapshot_to_visible_ms":round(elapsed,2),"polls":active["polls"],
                            "document_requests":active["documents"],"dialog_identity_preserved":True,
                            "page_errors":errors,"screenshot":shot})
                        context.close()
        finally: browser.close()
    report = {"scope":"isolated Chromium component replay; controlled clock; not production latency",
        "client_sha256":hashlib.sha256((ROOT/"templates/release_publications_live.js").read_bytes()).hexdigest(),
        "original_event":before["event_id"],"original_detection_preserved":True,
        "official_source_url":after["source_url"],"official_source_sha256":after.get("source_sha256"),
        "parser":after.get("parser"),"cases":results,
        "max_snapshot_to_visible_ms":max(r["snapshot_to_visible_ms"] for r in results)}
    (out/"proof.json").write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))

if __name__ == "__main__":
    main()
