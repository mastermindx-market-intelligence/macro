"""Real Chromium -> current account component -> actual ASGI digest routes -> isolated PG.

No live identities, production database, outbound mail or external network. Reuse
the already-qualified local Postgres fixture and the current published asset.
Run with the existing browser-enabled test environment and a repository path.
"""
from __future__ import annotations
import asyncio
import hashlib
import importlib
import inspect
import json
import os
from pathlib import Path
import sys
import tempfile
from urllib.parse import urlsplit

ROOT = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2]).resolve()
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT))
from fastapi import FastAPI
from playwright.async_api import async_playwright
from app import account_prefs as prefs
from tests.test_portfolio_digest_consent_postgres import db as db_fixture, quote

ORIGIN = "https://digest-fixture.example.test"
PATH = "/api/account/prefs/portfolio-digest"
A = "00000000-0000-4000-8000-000000001101"
B = "00000000-0000-4000-8000-000000001102"
asset = (ROOT / "site/account.js").read_bytes()
assert asset == (ROOT / "templates/account.js").read_bytes()
asset_sha = hashlib.sha256(asset).hexdigest()
identity = {"uid": A}
policy = {"get_unavailable": False, "lose_next_put": False}
network = []
writes = []
results = []
shots = {}

def record(name):
    results.append({"case": name, "passed": True})
    print(json.dumps({"case": name, "status": "PASS"}), flush=True)

original_store = prefs._digest_pref_store
original_gate = os.environ.get("PORTFOLIO_DIGEST_ENROLLMENT_ENABLED")
fixture = inspect.unwrap(db_fixture)()
db = next(fixture)

def store(method, path, **kwargs):
    if method == "GET":
        if policy["get_unavailable"]:
            raise OSError("synthetic preference read unavailable")
        prefix = "email_prefs?user_id=eq."
        assert path.startswith(prefix)
        uid = path[len(prefix):].split("&", 1)[0]
        assert path == prefix + uid + "&select=" + prefs._DIGEST_PREF_FIELDS
        value = db.read(uid)
        return [] if value is None else [value]
    assert method == "POST" and path == "rpc/portfolio_digest_consent_set_v1"
    body = kwargs["body"]
    assert set(body) == {"p_user_id", "p_enabled", "p_expected_revision"}
    result = db.transition(body["p_user_id"], body["p_enabled"], body["p_expected_revision"])
    writes.append({"body": body, "result": result})
    return result

prefs._digest_pref_store = store
os.environ["PORTFOLIO_DIGEST_ENROLLMENT_ENABLED"] = "1"
app = FastAPI()
app.include_router(prefs.router)
app.dependency_overrides[prefs._current_user] = lambda: {"id": identity["uid"]}

async def call_asgi(request):
    body = request.post_data_buffer or b""
    headers = await request.all_headers()
    scope = {"type": "http", "asgi": {"version": "3.0", "spec_version": "2.3"},
             "http_version": "1.1", "method": request.method, "scheme": "https",
             "path": PATH, "raw_path": PATH.encode(), "query_string": b"", "root_path": "",
             "headers": [(k.encode(), v.encode()) for k, v in headers.items()],
             "client": ("testclient", 50000), "server": ("digest-fixture.example.test", 443)}
    messages = []
    received = False
    async def receive():
        nonlocal received
        if received:
            return {"type": "http.disconnect"}
        received = True
        return {"type": "http.request", "body": body, "more_body": False}
    async def send(message):
        messages.append(message)
    await app(scope, receive, send)
    start = next(m for m in messages if m["type"] == "http.response.start")
    payload = b"".join(m.get("body", b"") for m in messages if m["type"] == "http.response.body")
    return start["status"], {k.decode(): v.decode() for k, v in start["headers"]}, payload

def html(lang):
    return """<!doctype html><html data-lang="__LANG__" data-theme="dark">
<head><meta charset="utf-8"><title>Digest consent qualification</title>
<style>body{background:#0f1115;color:#e5e7eb;font-family:system-ui;margin:40px}</style>
<script>
window.MM_API=location.origin;
window.__mmNavMarketLoading=true;
window.MDXAuth={
 client:()=>Promise.resolve({auth:{getSession:()=>Promise.resolve({
  data:{session:{access_token:'synthetic-browser-fixture-token'}}})}}),
 onChange:()=>{},signOut:()=>Promise.resolve()
};
</script><script src="/account.js?v=__HASH__" defer></script></head>
<body><h1>Account preferences</h1></body></html>""".replace("__LANG__", lang).replace("__HASH__", asset_sha[:8])

async def routed(route):
    req = route.request
    u = urlsplit(req.url)
    network.append({"path": u.path, "method": req.method})
    assert u.scheme + "://" + u.netloc == ORIGIN, "unexpected external request"
    if u.path == "/fixture.html":
        return await route.fulfill(content_type="text/html", body=html("zh" if "zh" in u.query else "en"))
    if u.path == "/account.js":
        return await route.fulfill(content_type="application/javascript", body=asset)
    if u.path == "/api/account":
        return await route.fulfill(json={"authenticated": True, "id": identity["uid"],
            "user_id": identity["uid"], "email": "synthetic@example.test", "name": "Synthetic account",
            "plan_label": "Free", "providers": ["email"], "provider_label": "Email"})
    if u.path == "/api/account/prefs" and req.method == "GET":
        return await route.fulfill(json={"prefs": {}, "unset": ["alert_email_optin"]})
    if u.path == PATH:
        status, headers, body = await call_asgi(req)
        if req.method == "PUT" and policy["lose_next_put"]:
            policy["lose_next_put"] = False
            return await route.abort("connectionreset")
        return await route.fulfill(status=status, headers=headers, body=body)
    if u.path == "/favicon.ico":
        return await route.fulfill(status=204, body="")
    raise AssertionError("unexpected fixture request " + u.path)

async def wait_phase(page, phase):
    await page.locator('[data-digest-state="' + phase + '"]').wait_for()

async def capture(page, name):
    path = OUT / (name + ".png")
    await page.locator(".mmacc-digest").screenshot(path=str(path))
    shots[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()

async def fresh(browser, lang="en"):
    context = await browser.new_context(viewport={"width": 1000, "height": 1000}, locale="zh-CN" if lang == "zh" else "en-US")
    await context.route("**/*", routed)
    page = await context.new_page()
    page.set_default_timeout(10000)
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    await page.goto(ORIGIN + "/fixture.html?lang=" + lang)
    await page.evaluate("window.MMAccount.open()")
    await page.locator(".mmacc-digest").wait_for()
    return context, page, errors

async def run():
    for uid in (A, B):
        db.sql("INSERT INTO auth.users VALUES(" + quote(uid) + ")", "supabase_auth_admin")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        browser_version = browser.version
        try:
            ctx, page, errors = await fresh(browser)
            await wait_phase(page, "ready")
            assert db.read(A) is None
            await page.locator('[data-act="digest-enable"]').click()
            await wait_phase(page, "saved")
            first = db.read(A)
            assert first["portfolio_digest_opt_in"] is True
            assert writes[-1]["body"]["p_expected_revision"] is None
            await capture(page, "english_enabled")
            await page.locator('[data-act="digest-disable"]').click()
            await wait_phase(page, "saved")
            stopped = db.read(A)
            assert stopped["portfolio_digest_opt_in"] is False
            assert stopped["portfolio_digest_revision"] != first["portfolio_digest_revision"]
            record("real_browser_asgi_pg_enable_withdraw")
            await capture(page, "english_withdrawn")

            db.transition(A, False)  # Another supported writer advances the displayed revision.
            before = len(writes)
            await page.locator('[data-act="digest-enable"]').click()
            await wait_phase(page, "conflict")
            assert len(writes) == before + 1 and writes[-1]["result"]["status"] == "stale_revision"
            assert db.read(A)["portfolio_digest_opt_in"] is False
            assert await page.locator('[data-act="digest-enable"]').is_disabled()
            await page.locator('[data-act="digest-refresh"]').click()
            await wait_phase(page, "ready")
            assert len(writes) == before + 1
            await page.locator('[data-act="digest-enable"]').click()
            await wait_phase(page, "saved")
            assert db.read(A)["portfolio_digest_opt_in"] is True
            record("real_conflict_requires_fresh_read_and_click")

            policy["lose_next_put"] = True
            before = len(writes)
            await page.locator('[data-act="digest-disable"]').click()
            await wait_phase(page, "unconfirmed")
            assert len(writes) == before + 1 and db.read(A)["portfolio_digest_opt_in"] is False
            await page.locator('[data-act="digest-refresh"]').click()
            await wait_phase(page, "ready")
            assert len(writes) == before + 1
            assert await page.locator('[data-act="digest-enable"]').is_disabled()
            assert await page.locator('[data-act="digest-disable"]').is_disabled()
            assert "confirm" in await page.locator("#mmacc-digest-msg").inner_text()
            await capture(page, "english_unconfirmed_withdrawal")
            record("committed_withdrawal_lost_reply_not_replayed_or_confirmed_by_get")
            assert not errors, errors
            await ctx.close()

            ctx, page, errors = await fresh(browser)
            await wait_phase(page, "ready")
            await page.evaluate("""() => {
              window.MDXAuth.client=()=>new Promise(resolve=>{
                window.__releaseDigestClient=()=>resolve({auth:{getSession:()=>Promise.resolve({
                  data:{session:{access_token:'synthetic-new-subject-token'}}})}});
              });
            }""")
            before = len(writes)
            await page.locator('[data-act="digest-enable"]').click()
            await page.wait_for_function("typeof window.__releaseDigestClient === 'function'")
            identity["uid"] = B
            await page.evaluate("window.__releaseDigestClient()")
            await wait_phase(page, "account_changed")
            assert len(writes) == before, "mismatched observed subject reached the database"
            assert db.read(B) is None
            record("delayed_token_subject_mismatch_refused_before_database")
            assert not errors, errors
            await ctx.close()

            identity["uid"] = A
            os.environ["PORTFOLIO_DIGEST_ENROLLMENT_ENABLED"] = "0"
            ctx, page, errors = await fresh(browser, "zh")
            await wait_phase(page, "ready")
            assert await page.locator('[data-act="digest-enable"]').is_disabled()
            assert await page.locator('[data-act="digest-enable"]').inner_text() == "开启"
            await page.locator('[data-act="digest-disable"]').click()
            await wait_phase(page, "saved")
            assert db.read(A)["portfolio_digest_opt_in"] is False
            await capture(page, "chinese_enrollment_off_withdrawal")
            record("chinese_enrollment_off_still_allows_real_withdrawal")
            assert not errors, errors
            await ctx.close()

            policy["get_unavailable"] = True
            ctx, page, errors = await fresh(browser)
            await wait_phase(page, "unavailable")
            await page.locator('[data-act="digest-disable"]').click()
            await wait_phase(page, "saved")
            assert db.read(A)["portfolio_digest_opt_in"] is False
            record("read_unavailable_still_allows_subject_bound_withdrawal")
            assert not errors, errors
            await ctx.close()
            return browser_version
        finally:
            await browser.close()

result = {"source_asset_sha256": asset_sha, "live_network": False, "live_mail": False,
          "provider_auth": "synthetic dependency seam", "api": "actual current ASGI routes",
          "database": "isolated Unix-only PostgreSQL using existing fixture"}
try:
    result["browser_version"] = asyncio.run(asyncio.wait_for(run(), timeout=90))
    result["postgres_version"] = db.sql("SHOW server_version")
    result["status"] = "PASS"
except BaseException as exc:
    result["status"] = "CANCELLED" if isinstance(exc, (KeyboardInterrupt, asyncio.CancelledError)) else "FAIL"
    result["error"] = type(exc).__name__ + ": " + str(exc)
    raise
finally:
    result["cases"] = results
    result["screenshots"] = shots
    result["rpc_calls"] = len(writes)
    result["network_requests"] = network
    result["source_sha256"] = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
                              for p in ("templates/account.js", "site/account.js", "app/account_prefs.py",
                                        "scripts/deploy/portfolio_digest_consent_v1.sql")}
    (OUT / "browser.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    prefs._digest_pref_store = original_store
    if original_gate is None:
        os.environ.pop("PORTFOLIO_DIGEST_ENROLLMENT_ENABLED", None)
    else:
        os.environ["PORTFOLIO_DIGEST_ENROLLMENT_ENABLED"] = original_gate
    fixture.close()
    print(json.dumps({"receipt": str(OUT / "browser.json"), "status": result["status"],
                      "passed_cases": len(results), "browser_version": result.get("browser_version"),
                      "postgres_version": result.get("postgres_version"), "screenshots": shots}))
