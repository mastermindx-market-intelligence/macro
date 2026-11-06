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


SHELL = '''<!doctype html><html><head><meta charset="utf-8"><link rel="stylesheet" href="/ontology.css">
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
    page.locator("#ox-company .ox-company-choices button").click()
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
    page.locator("#ox-company .ox-company-choices button").click()
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
    assert page.locator("#ox-company .ox-company-choices button").count() == 0


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
    page.locator("#ox-company .ox-company-choices button").click()
    page.get_by_text(fact["fact"]["product"], exact=True).wait_for()
    assert page.locator(".ox-company-fact img").count() == 0
    assert len(seen) == 3


def test_canonical_fallback_signout_cannot_reauthorize_from_stale_sdk_session(page):
    seen, _ = start(page)
    lookup(page)
    settled(page, "ready")
    page.locator("#ox-company .ox-company-choices button").click()
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
    page.locator("#ox-company .ox-company-choices button").click()
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
    page.locator("#ox-company .ox-company-choices button").click()
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
    assert page.locator("#ox-company .ox-company-choices button").count() == 0
    assert errors == []



def supplier_fixtures():
    context, selection, fact = fixtures()
    entry = selection['selections'][0]
    entry.update(kind='disclosed_supplier', lifecycle='reported_use')
    entry['fact_reference']['schema'] = 'company_intelligence.disclosed_supplier_fact/v1'
    entry['edition_reference']['schema'] = 'company_intelligence.sec_disclosure_edition/v1'
    fact['schema'] = 'company_intelligence.private_disclosed_supplier/v1'
    fact['fact'].update(kind='disclosed_supplier', lifecycle='reported_use', revision=1,
        object_id='ISS:US-XNYS-OTHER', product='SYNTHETIC SUPPLIER WAFERS', platform='foundry_services', economic_share=None)
    source = {'snapshot_id':'ffsecsrc_'+'1'*64, 'snapshot_at':'2026-01-02T09:00:00Z',
        'manifest_key':'manifests/0000000001/0000000001-26-000001/ffsec_manifest_'+'2'*64+'.json',
        'document_id':'sec_document_'+'3'*64,'accession':'0000000001-26-000001','issuer_cik':'0000000001',
        'archive_url':'https://www.sec.gov/Archives/edgar/data/1/000000000126000001/synthetic.htm',
        'accepted_at':'2025-12-31T16:00:00Z','retrieved_at':'2026-01-02T08:00:00Z','recorded_at':'2026-01-02T08:30:00Z',
        'retrieval_receipt_id':'sec_archive_receipt_'+'4'*64,'span_start_byte':10,'span_end_byte':50,'span_sha256':'5'*64}
    fact['source_timing']['sec_source'] = source
    fact['supplier_binding'] = {'direction':'object_supplies_subject','identity_mode':'current',
        'identity_observed_at':'2026-01-03T08:00:00Z','adopted_at':'2026-01-03T09:00:00Z',
        'evidence_revision':hashlib.sha256(json.dumps(source,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
        'span':{'start_byte':10,'end_byte':50,'text_sha256':'5'*64},
        'subject_identity':context['issuer_binding']['identity_snapshot_reference']['sha256'],'object_identity':'6'*64,
        'current_subject_identity':context['issuer_binding']['identity_snapshot_reference']['sha256'],'current_object_identity':'6'*64}
    return context, selection, fact


@pytest.mark.parametrize('theme,language,width', [('dark','en',1440),('light','zh',390)])
def test_supplier_has_distinct_role_attribution_and_clocks_without_plan_or_effect(page, theme, language, width):
    context, selection, fact = supplier_fixtures()
    page.set_viewport_size({'width':width,'height':1000})
    seen, errors = start(page,context=context,selection=selection,fact=fact)
    page.evaluate('([t,l])=>{document.documentElement.dataset.theme=t;document.documentElement.dataset.lang=l}',[theme,language])
    lookup(page); settled(page,'ready')
    assert len(seen)==2
    button=page.locator('#ox-company .ox-company-choices button')
    assert 'Disclosed supplier' in button.get_attribute('aria-label')
    button.click(); page.get_by_text('SYNTHETIC SUPPLIER WAFERS',exact=True).wait_for()
    card=page.locator('.ox-company-fact'); text=card.inner_text()
    assert '2026-01-03T09:00:00Z' in text and '2026-01-02T08:00:00Z' in text
    assert 'ISS:US-XNYS-OTHER' in text
    assert not card.get_by_text('An announced plan',exact=True).count()
    assert card.locator('a').get_attribute('href') == fact['source_timing']['sec_source']['archive_url']
    assert card.locator('a').get_attribute('rel') == 'noopener noreferrer'
    assert len(seen)==3 and errors==[]
    assert page.evaluate('[localStorage.length,sessionStorage.length]')==[0,0]
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.evaluate("window.testSession=null;window.changeAuth('SIGNED_OUT',null)")
    settled(page,'idle');assert 'SYNTHETIC SUPPLIER WAFERS' not in page.content()


@pytest.mark.parametrize('change', ['plan_relabel','wrong_schema','wrong_edition','direction','historical','future_adoption',
    'identity_after_adoption','retrieval_reversed','wrong_cik','wrong_subject_receipt','span','evidence_digest',
    'source_url','source_body','quantity','missing_object'])
def test_supplier_malformed_or_misbound_projection_is_never_rendered(page, change):
    context, selection, fact = supplier_fixtures()
    source=fact['source_timing']['sec_source']; binding=fact['supplier_binding']
    if change=='plan_relabel':fact['fact']['kind']='product_integration'
    if change=='wrong_schema':fact['schema']='company_intelligence.private_product_integration/v2'
    if change=='wrong_edition':fact['edition']={**fact['edition'],'schema':'company_intelligence.issuer_disclosure_edition/v1'}
    if change=='direction':binding['direction']='subject_supplies_object'
    if change=='historical':binding['identity_mode']='historical'
    if change=='future_adoption':binding['adopted_at']='9999-01-01T00:00:00Z'
    if change=='identity_after_adoption':binding['identity_observed_at']='2026-01-04T00:00:00Z'
    if change=='retrieval_reversed':source['retrieved_at']='2025-12-30T00:00:00Z'
    if change=='wrong_cik':source['issuer_cik']='0000000002'
    if change=='wrong_subject_receipt':binding['current_subject_identity']='7'*64
    if change=='span':binding['span']['end_byte']=51
    if change=='evidence_digest':binding['evidence_revision']='8'*64
    if change=='source_url':source['archive_url']='https://www.sec.gov.evil.invalid/Archives/fake.htm'
    if change=='source_body':source['body']='SECRET_BODY'
    if change=='quantity':fact['fact']['economic_share']=0.5
    if change=='missing_object':del fact['fact']['object_id']
    seen,errors=start(page,context=context,selection=selection,fact=fact)
    lookup(page);settled(page,'ready');page.locator('#ox-company .ox-company-choices button').click()
    settled(page,'unavailable')
    assert 'SYNTHETIC SUPPLIER WAFERS' not in page.content() and 'SECRET_BODY' not in page.content()
    assert len(seen)==3 and errors==[]


def test_actual_native_supplier_wire_reaches_macro_consumer(page, tmp_path):
    """Exercise the implemented native publisher/reader, not a hand-written wire fixture."""
    from tests.test_sec_supplier_adoption import case as supplier_case, publish_synthetic
    from engine.company_intelligence import issuer_disclosure_owner as owner
    from engine.company_intelligence import issuer_disclosure_selection as selections
    from engine.company_intelligence import issuer_disclosures as native
    c = supplier_case.__wrapped__(tmp_path)
    publish_synthetic(c)
    authority = owner.CurrentDisclosureOwner(c.source, c.state)
    fact = native.read_disclosure(c.artifacts, authority,
        native.Request(c.spec['fact']['fact_id'], owner.PURPOSE, owner.AUDIENCE))
    selection = selections.read_issuer_selection(authority, authority, lambda:c.artifacts,
        c.spec['fact']['subject_id'], purpose=owner.PURPOSE, audience=owner.AUDIENCE)
    receipt = c.identities['subject']
    context = {'schema':'company_intelligence.private_company_context/v1','identity_mode':'current',
        'query':{'namespace':'store','symbol':'ALPHA'},'security_id':'SEC:US-XNAS-ALPHA',
        'issuer_binding':selection['issuer_binding'],'identity_receipt':receipt}
    seen, errors = start(page,context=context,selection=selection,fact=fact,full_shell=True)
    page.locator('#ox-company input').fill('ALPHA')
    page.locator('#ox-company button[type=submit]').click();settled(page,'ready')
    page.locator('#ox-company .ox-company-choices button').click()
    page.get_by_text('Widget',exact=True).wait_for()
    assert len(seen)==3 and errors==[]
    assert 'ISS:US-XNAS-BETA' in page.locator('.ox-company-fact').inner_text()
    assert c.body.decode() not in page.content()
