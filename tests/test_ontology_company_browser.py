"""Synthetic browser proof of the Macro company inspector, never live source reads."""
from __future__ import annotations

import hashlib
import json
import mimetypes
from pathlib import Path
from urllib.parse import urlsplit

import pytest

from tests.test_ontology_explorer_brain_browser import browser

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://macro.example"
PREFIX = "/api/company-intelligence/private/"
HEADERS = {"Content-Type": "application/json", "Cache-Control": "private, no-store",
           "Vary": "Authorization, Cookie"}


def fixtures(symbol="TEST"):
    receipt = {
        "schema": "company_intelligence.current_issuer_identity/v1", "identity_mode": "current",
        "issuer_id": "ISS:US-XNAS-TEST", "evidenced_cik": "0000000001",
        "source_commit": "b" * 40,
        "sources": {name: {"sha256": str(i) * 64, "byte_length": 512}
                    for i, name in enumerate(("security_master", "vendor_aliases", "issuer_master"), 1)},
        "evidence_source": "sec_company_tickers", "evidence_snapshot": "2026-01-01",
    }
    raw = json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode()
    context = {
        "schema": "company_intelligence.private_company_context/v1", "identity_mode": "current",
        "query": {"namespace": "store", "symbol": symbol}, "security_id": "SEC:US-XNAS-" + symbol,
        "issuer_binding": {"issuer_id": receipt["issuer_id"], "evidenced_cik": receipt["evidenced_cik"],
                           "identity_snapshot_reference": {"schema": receipt["schema"],
                           "sha256": hashlib.sha256(raw).hexdigest(), "byte_length": len(raw)}},
        "identity_receipt": receipt,
    }
    entry = {"fact_id": "integration:" + "a" * 64, "kind": "product_integration", "lifecycle": "planned",
             "fact_reference": {"schema": "company_intelligence.product_integration_fact/v1",
                                "sha256": "c" * 64, "byte_length": 500},
             "edition_reference": {"schema": "company_intelligence.issuer_disclosure_edition/v1",
                                   "sha256": "d" * 64, "byte_length": 400}}
    selection = {"schema": "company_intelligence.private_issuer_selections/v1", "generation": "fixture-generation",
                 "identity_mode": "current", "issuer_role": "subject_disclosing_company",
                 "issuer_binding": context["issuer_binding"], "selections": [entry]}
    fact = {"schema": "company_intelligence.private_product_integration/v2",
            "fact": {"fact_id": entry["fact_id"], "kind": entry["kind"], "lifecycle": entry["lifecycle"],
                     "subject_id": receipt["issuer_id"], "product": "SYNTHETIC TEST PRODUCT",
                     "platform": "SYNTHETIC TEST PLATFORM", "amount": None},
            "reference": entry["fact_reference"], "edition": entry["edition_reference"],
            "source_timing": {"published_date": "2025-12-31", "published_at": None,
                              "publication_precision": "date", "known_at": "2026-01-02T09:30:00Z"},
            "generation": selection["generation"], "authority": "context_only"}
    return context, selection, fact


SHELL = '''<!doctype html><html><head><link rel="stylesheet" href="/ontology.css">
<link rel="stylesheet" href="/ontology-company.css"><link rel="stylesheet" href="/theme.css">
<style>body{margin:0;background:var(--bg);color:var(--text);font-family:var(--font-ui)}</style></head>
<body><main class="ox-wrap"><section id="ox-company" class="ox-company">
<h2><span class="l-en">Company research</span><span class="l-zh">公司研究</span></h2>
<p class="ox-note"><span class="l-en">Inspect source-announced plans. Company selection does not establish a connection to the WTI path.</span>
<span class="l-zh">查看来源披露的计划。选择公司并不确立其与 WTI 路径的联系。</span></p>
<form class="ox-company-form"><label class="ox-company-label"><span>Company / 公司</span>
<input id="company-query" maxlength="24" autocomplete="off" spellcheck="false"></label>
<button class="ox-cta" type="submit"><span class="l-en">Inspect company</span><span class="l-zh">查看公司</span></button>
<button class="ox-cta secondary" type="button" data-company-clear>Clear / 清除</button></form>
<div data-company-result aria-live="polite"></div></section></main>
<script type="module" src="/ontology-company.js"></script></body></html>'''

AUTH = """window.testSession = {user:{id:'00000000-0000-4000-8000-000000000001'},access_token:'fixture-token'};
window.testCanonicalUser=window.testSession.user;
window.MDXAuth = {user:()=>window.testCanonicalUser,client:async()=>({auth:{getSession:async()=>({data:{session:window.testSession}}),
onAuthStateChange:fn=>{window.changeAuth=fn;return{data:{subscription:{unsubscribe(){}}}}}}})};"""


@pytest.fixture
def page(browser):
    context = browser.new_context()
    page = context.new_page()
    yield page
    context.close()


def start(page, *, context=None, selection=None, fact=None, status=200, headers=None, auth=True,
          full_shell=False, analytics=None, signed_out_before_mount=False):
    values = fixtures()
    payloads = [values[0] if context is None else context,
                values[1] if selection is None else selection,
                values[2] if fact is None else fact]
    seen = []
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    if full_shell:
        page.add_init_script("""window.testSession={user:{id:'00000000-0000-4000-8000-000000000001',
          email:'fixture@example.invalid',user_metadata:{}},access_token:'fixture-token'};
          window.__testAuthCallbacks=[];
          window.__testSDK={createClient:()=>({auth:{
            getSession:async()=>({data:{session:window.testSession}}),
            onAuthStateChange:fn=>{window.__testAuthCallbacks.push(fn);
              queueMicrotask(()=>fn('INITIAL_SESSION',window.testSession));
              return {data:{subscription:{unsubscribe(){}}}};},
            signOut:async()=>{throw new Error('synthetic SDK signout failure');}
          }})};""")
    else:
        page.add_init_script(AUTH + ("" if auth else "window.testSession=null;")
                             + ("window.testCanonicalUser=null;" if signed_out_before_mount else ""))

    def route(request):
        url = request.request.url
        path = urlsplit(url).path
        if path.startswith(PREFIX):
            seen.append({"url": url, "headers": request.request.headers})
            index = 0 if "company-context" in path else 1 if "/issuers/" in path else 2
            request.fulfill(status=status, headers=HEADERS if headers is None else headers,
                            body=json.dumps(payloads[index]))
        elif path == "/ontology.html":
            request.fulfill(status=200, content_type="text/html",
                            body=(ROOT / "site/ontology.html").read_text() if full_shell else SHELL)
        elif full_shell and path == "/supabase.js":
            request.fulfill(status=200, content_type="text/javascript", body="window.supabase=window.__testSDK;")
        elif path == "/api/collect" and analytics is not None:
            analytics.append(request.request.post_data or "")
            request.fulfill(status=204)
        elif path.startswith("/api/"):
            request.fulfill(status=503, content_type="application/json", body='{"detail":"Synthetic unavailable reading"}')
        else:
            source = ROOT / ("site" if full_shell else "templates") / path.lstrip("/")
            if source.is_file() and source.is_relative_to(ROOT):
                request.fulfill(status=200, content_type=mimetypes.guess_type(source)[0] or "application/octet-stream",
                                body=source.read_bytes())
            else:
                # Every request is intercepted. No real site, provider, or source is contacted.
                request.fulfill(status=204)
    page.route("**/*", route)
    page.goto(("https://www.mastermind-x.com" if full_shell else BASE) + "/ontology.html")
    page.wait_for_function("document.querySelector('[data-company-result]').dataset.state === 'idle'")
    return seen, errors


def lookup(page):
    page.locator("#ox-company input").fill("test")
    page.locator("#ox-company button[type=submit]").click()


def settled(page, state):
    page.wait_for_function("s => document.querySelector('[data-company-result]').dataset.state === s", arg=state)


@pytest.mark.parametrize("theme", ["dark", "light"])
@pytest.mark.parametrize("language", ["en", "zh"])
@pytest.mark.parametrize("width", [390, 820, 1440])
def test_complete_private_read_without_storage_or_implied_exposure(page, theme, language, width):
    page.set_viewport_size({"width": width, "height": 900})
    seen, errors = start(page)
    page.evaluate("([theme,lang])=>{document.documentElement.dataset.theme=theme;document.documentElement.dataset.lang=lang}", [theme, language])
    assert seen == []
    lookup(page)
    settled(page, "ready")
    assert len(seen) == 2  # No automatic fact read.
    page.locator(".ox-company-choices button").click()
    page.get_by_text("SYNTHETIC TEST PRODUCT", exact=True).wait_for()
    assert len(seen) == 3
    assert "ISS%3AUS-XNAS-TEST" in seen[1]["url"]
    assert all(item["headers"].get("authorization") == "Bearer fixture-token" for item in seen)
    assert "2025-12-31" in page.locator(".ox-company-fact").inner_text()
    assert "2026-01-02T09:30:00Z" in page.locator(".ox-company-fact").inner_text()
    assert "2025-12-31T00:00" not in page.content()
    assert page.url == BASE + "/ontology.html"
    assert page.evaluate("[localStorage.length,sessionStorage.length]") == [0, 0]
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    assert errors == []
    page.evaluate("window.testSession=null;window.changeAuth('SIGNED_OUT',null)")
    settled(page, "idle")
    assert "SYNTHETIC TEST PRODUCT" not in page.content()
    assert "fixture-generation" not in page.content()
    assert len(seen) == 3


@pytest.mark.parametrize("kind", ["generation", "subject", "reference", "numeric", "timing", "extra"])
def test_malformed_or_unjoined_fact_is_never_rendered(page, kind):
    _, _, fact = fixtures()
    if kind == "generation": fact["generation"] = "wrong-generation"
    if kind == "subject": fact["fact"]["subject_id"] = "ISS:US-XNAS-OTHER"
    if kind == "reference": fact["reference"] = {**fact["reference"], "sha256": "e" * 64}
    if kind == "numeric": fact["fact"]["amount"] = 100
    if kind == "timing": fact["source_timing"]["published_at"] = "2025-12-31T00:00:00Z"
    if kind == "extra": fact["secret"] = "MUST_NOT_RENDER"
    seen, errors = start(page, fact=fact)
    lookup(page)
    settled(page, "ready")
    page.locator(".ox-company-choices button").click()
    settled(page, "unavailable")
    assert "SYNTHETIC TEST PRODUCT" not in page.content()
    assert "MUST_NOT_RENDER" not in page.content()
    assert len(seen) == 3
    assert errors == []


@pytest.mark.parametrize("status,code,expected", [(401,"AUTHENTICATION_REQUIRED","signed_out"),
    (403,"ENTITLEMENT_REQUIRED","forbidden"), (503,"SOURCE_RUNTIME_UNAVAILABLE","unavailable"),
    (524,"UNKNOWN","unavailable"), (401,"ENTITLEMENT_REQUIRED","unavailable")])
def test_refusal_is_closed_and_never_retried(page, status, code, expected):
    body = {"schema":"company_intelligence.private_error/v1","code":code,"automatic_retry_permitted":False}
    seen, errors = start(page, context=body, status=status)
    lookup(page)
    settled(page, expected)
    page.wait_for_timeout(100)
    assert len(seen) == 1
    assert errors == []


def test_empty_selection_is_not_an_error_or_a_fact(page):
    _, selection, _ = fixtures()
    selection["selections"] = []
    seen, _ = start(page, selection=selection)
    lookup(page)
    settled(page, "empty")
    assert len(seen) == 2
    assert page.locator(".ox-company-choices button").count() == 0


@pytest.mark.parametrize("missing", ["Cache-Control", "Vary", "Content-Type"])
def test_private_response_requires_transport_headers(page, missing):
    seen, _ = start(page, headers={k:v for k,v in HEADERS.items() if k != missing})
    lookup(page)
    settled(page, "unavailable")
    assert len(seen) == 1


def test_signed_out_does_not_read_private_api(page):
    seen, _ = start(page, auth=False)
    lookup(page)
    settled(page, "signed_out")
    assert seen == []


def test_wrong_identity_receipt_is_not_an_issuer_lookup(page):
    context, _, _ = fixtures()
    context["issuer_binding"]["identity_snapshot_reference"]["sha256"] = "0" * 64
    seen, _ = start(page, context=context)
    lookup(page)
    settled(page, "unavailable")
    assert len(seen) == 1


def test_user_text_never_becomes_html(page):
    _, _, fact = fixtures()
    fact["fact"]["product"] = '<img src=x onerror="alert(1)">'
    seen, _ = start(page, fact=fact)
    lookup(page)
    settled(page, "ready")
    page.locator(".ox-company-choices button").click()
    page.get_by_text(fact["fact"]["product"], exact=True).wait_for()
    assert page.locator(".ox-company-fact img").count() == 0
    assert len(seen) == 3


def test_canonical_fallback_signout_cannot_reauthorize_from_stale_sdk_session(page):
    seen, _ = start(page)
    lookup(page)
    settled(page, "ready")
    page.locator(".ox-company-choices button").click()
    page.get_by_text("SYNTHETIC TEST PRODUCT", exact=True).wait_for()
    page.evaluate("window.dispatchEvent(new CustomEvent('mdx-auth',{detail:{user:null,event:'SIGNED_OUT'}}))")
    settled(page, "idle")
    assert "SYNTHETIC TEST PRODUCT" not in page.content()
    assert page.locator("input").input_value() == ""
    lookup(page)
    settled(page, "signed_out")
    assert len(seen) == 3


def test_canonical_signout_before_module_mount_refuses_stale_sdk_session(page):
    seen, errors = start(page, signed_out_before_mount=True)
    lookup(page)
    settled(page, "signed_out")
    assert seen == []
    assert errors == []


def test_draft_query_edit_removes_previous_issuer_and_fact(page):
    seen, _ = start(page)
    lookup(page)
    settled(page, "ready")
    page.locator(".ox-company-choices button").click()
    page.get_by_text("SYNTHETIC TEST PRODUCT", exact=True).wait_for()
    page.locator("input").fill("OTHER")
    settled(page, "idle")
    assert "SYNTHETIC TEST PRODUCT" not in page.content()
    assert len(seen) == 3


def test_actual_macro_shell_auth_and_analytics_keep_private_values_local(page):
    analytics = []
    seen, errors = start(page, full_shell=True, analytics=analytics)
    page.wait_for_function("window.MDXAuth && window.MDXAuth.user()")
    lookup(page)
    settled(page, "ready")
    page.locator(".ox-company-choices button").click()
    page.get_by_text("SYNTHETIC TEST PRODUCT", exact=True).wait_for()
    page.locator("#ox-company summary").click()
    page.locator(".ox-company-fact dd").first.click()
    page.evaluate("window.mmTrack('exit', {test_boundary:true})")
    page.wait_for_function("window.__mm_a === true")
    page.wait_for_timeout(100)
    assert analytics, "the incumbent analytics path must actually execute in this fixture"
    serialized = "\n".join(analytics) + page.evaluate("JSON.stringify([Object.entries(localStorage),Object.entries(sessionStorage)])")
    for private in ("SYNTHETIC TEST PRODUCT", "fixture-generation", "ISS:US-XNAS-TEST", "integration:", "fixture-token"):
        assert private not in serialized
    assert page.url == "https://www.mastermind-x.com/ontology.html"
    # Exercise the real canonical fallback, not a manually emitted lookalike event.
    page.evaluate("window.MDXAuth.signOut()")
    settled(page, "idle")
    assert "SYNTHETIC TEST PRODUCT" not in page.content()
    lookup(page)
    settled(page, "signed_out")
    assert len(seen) == 3
    assert errors == []


@pytest.mark.parametrize("canonical", ["null", "{id:'other-owner'}", "throw"])
def test_restored_page_rereads_canonical_owner_despite_stale_sdk(page, canonical):
    seen, errors = start(page)
    lookup(page)
    settled(page, "ready")
    assert len(seen) == 2
    page.evaluate("window.dispatchEvent(new PageTransitionEvent('pagehide',{persisted:true}))")
    settled(page, "idle")
    if canonical == "throw":
        page.evaluate("() => { window.MDXAuth.user=()=>{throw new Error('canonical unavailable')}; }")
    else:
        page.evaluate("value=>{window.testCanonicalUser=value}", None if canonical == "null" else {"id":"other-owner"})
    page.evaluate("window.dispatchEvent(new PageTransitionEvent('pageshow',{persisted:true}))")
    lookup(page)
    settled(page, "signed_out")
    assert len(seen) == 2
    assert page.locator(".ox-company-choices button").count() == 0
    assert errors == []
