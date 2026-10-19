from pathlib import Path
import pytest
import tests.test_ontology_explorer_brain_browser as incumbent
from tests.test_ontology_explorer_brain_browser import browser, synthetic_snapshot

PREPARED = Path(__file__).resolve().parents[1] / "templates" / "ontology.js"
def test_signout_clears_current_owner_read_and_brain_selection(browser, synthetic_snapshot, monkeypatch):
    monkeypatch.setattr(incumbent, "ONTOLOGY_JS", PREPARED)
    context, page = incumbent._open(browser, synthetic_snapshot, width=1440, height=900)
    try:
        page.locator("#ox-steps .ox-brain-action").first.click()
        assert page.evaluate("window.MM_BRAIN_CFG.getOntologySelection()") is not None
        page.evaluate("window.dispatchEvent(new CustomEvent('mdx-auth',{detail:{user:null,event:'SIGNED_OUT'}}))")
        assert page.locator("#ox-root .ox-hero").count() == 0
        assert page.locator("#ox-root .ox-gate").count() == 1
        assert page.evaluate("window.MM_BRAIN_CFG.getOntologySelection()") is None
    finally:
        context.close()


def test_old_uncooperative_owner_response_cannot_repaint_after_signout(browser, synthetic_snapshot):
    context = browser.new_context()
    page = context.new_page()
    try:
        page.set_content(incumbent.SHELL)
        page.evaluate("() => { window.fetch=()=>new Promise(resolve=>{window.finishOldReading=resolve;}); }")
        page.add_script_tag(path=str(PREPARED))
        page.wait_for_function("typeof window.finishOldReading === 'function'")
        page.evaluate("window.dispatchEvent(new CustomEvent('mdx-auth',{detail:{user:null,event:'SIGNED_OUT'}}))")
        page.evaluate("snapshot=>window.finishOldReading({ok:true,status:200,json:async()=>snapshot})",synthetic_snapshot)
        page.evaluate("()=>new Promise(resolve=>setTimeout(resolve,0))")
        assert page.locator("#ox-root .ox-hero").count() == 0
        assert page.locator("#ox-root .ox-gate").count() == 1
    finally:
        context.close()


def test_account_changes_before_publication_refuse_old_account_snapshot(browser, synthetic_snapshot):
    context = browser.new_context()
    page = context.new_page()
    try:
        page.set_content(incumbent.SHELL)
        page.evaluate("""snapshot=>{
          window.currentOwner={id:'first'};
          window.MDXAuth={user:()=>window.currentOwner,client:async()=>({auth:{getSession:async()=>({data:{session:{user:window.currentOwner,access_token:'fixture-'+window.currentOwner.id}}})}})};
          window.fetch=async()=>({ok:true,status:200,json:async()=>{window.currentOwner={id:'second'};return snapshot;}});
        }""",synthetic_snapshot)
        page.add_script_tag(path=str(PREPARED))
        page.wait_for_selector("#ox-root .ox-gate",state="attached")
        assert page.locator("#ox-root .ox-hero").count() == 0
    finally:
        context.close()


def test_missing_canonical_owner_refuses_even_with_stale_sdk_session(browser):
    context=browser.new_context()
    page=context.new_page()
    try:
        page.set_content(incumbent.SHELL)
        page.evaluate("""() => {
          window.calls=0;
          window.MDXAuth.user=()=>null;
          window.fetch=async()=>{window.calls++;throw new Error('must not fetch');};
        }""")
        page.add_script_tag(path=str(PREPARED))
        page.wait_for_selector("#ox-root .ox-gate",state="attached")
        assert page.evaluate("window.calls") == 0
        assert page.locator("#ox-root .ox-hero").count() == 0
    finally:
        context.close()


@pytest.mark.parametrize('width',[390,1440])
def test_existing_membership_handoff_is_explicit_and_refusals_have_no_action(browser,synthetic_snapshot,monkeypatch,width):
    monkeypatch.setattr(incumbent,'ONTOLOGY_JS',PREPARED)
    monkeypatch.setattr(incumbent,'ONTOLOGY_CSS',PREPARED.with_suffix('.css'))
    monkeypatch.setattr(incumbent,'SHELL',incumbent.SHELL.replace('<div id="mock-brain"',
      '<section id="ox-company" data-company-ready="true"></section><div id="mock-brain"'))
    synthetic_snapshot['source']['substrate_asof']={'min':'2025-12-31','max':'2026-01-01'}
    synthetic_snapshot['exposure_screens']=[{
      'id':'fixture','label':{'en':'Synthetic exposure','zh':'合成敞口'},
      'n':2,'unevaluable':17,'cuts':{'synthetic_cut':2.5},
      'companies':{'linked':[{'symbol':'TEST','security_id':'SEC:US-XNAS-TEST'}],
                   'unlinked':[{'symbol':'UNKNOWN','reason':'unresolved'}]}
    }]
    context,page=incumbent._open(browser,synthetic_snapshot,width=width,height=900)
    try:
        page.evaluate("""() => {
          window.companyChoices=[];
          document.getElementById('ox-company').addEventListener('ontology-select-company',event=>window.companyChoices.push(event.detail));
        }""")
        assert page.evaluate('window.companyChoices') == []
        exposure=page.locator('[data-exposure-membership]')
        exposure.locator('summary').first.click()
        assert '17' in exposure.inner_text()
        assert '2026-01-01' in exposure.inner_text()
        assert exposure.locator('button').count() == 1
        assert exposure.locator('li',has_text='UNKNOWN').locator('button').count() == 0
        button=exposure.locator('button')
        assert button.bounding_box()['height'] >= 44
        original_url=page.url
        button.click()
        chosen=page.evaluate('window.companyChoices')
        assert len(chosen)==1
        assert chosen[0]['symbol']=='TEST'
        assert chosen[0]['security_id']=='SEC:US-XNAS-TEST'
        assert chosen[0]['manifest_hash']==synthetic_snapshot['source']['source_manifest_hash']
        assert page.url==original_url
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    finally:
        context.close()


import json
from urllib.parse import urlsplit
from tests.test_ontology_company_browser import fixtures, start, settled

@pytest.mark.parametrize('identity_matches',[True,False])
@pytest.mark.parametrize('width',[390,1440])
def test_explicit_owner_membership_to_private_company_read(browser,synthetic_snapshot,identity_matches,width):
    context=browser.new_context(viewport={'width':width,'height':900})
    page=context.new_page()
    try:
        company,selection,fact=fixtures()
        if not identity_matches:
            company['security_id']='SEC:US-XNAS-OTHER'
        seen,errors=start(page,context=company,selection=selection,fact=fact,full_shell=True,analytics=[])
        synthetic_snapshot['source']['substrate_asof']={'min':'2025-12-31','max':'2026-01-01'}
        synthetic_snapshot['exposure_screens']=[{
            'id':'fixture','label':{'en':'Synthetic exposure','zh':'合成敞口'},
            'n':2,'unevaluable':17,'cuts':{'synthetic_cut':2.5},
            'companies':{'linked':[{'symbol':'TEST','security_id':'SEC:US-XNAS-TEST'}],
                'unlinked':[{'symbol':'UNKNOWN','reason':'unresolved'}],'ranked':False}
        }]
        def prepared_asset(route):
            name=Path(urlsplit(route.request.url).path).name
            source=PREPARED.parent/name
            if source.is_file():
                route.fulfill(status=200,content_type='text/css' if name.endswith('.css') else 'text/javascript',body=source.read_bytes())
            else:
                route.fallback()
        page.route('**/ontology*.js*',prepared_asset)
        page.route('**/ontology.css*',prepared_asset)
        page.route('**/api/ontology/explorer/v1**',lambda route:route.fulfill(status=200,content_type='application/json',body=json.dumps(synthetic_snapshot)))
        page.reload()
        page.locator('#ox-root .ox-hero').wait_for()
        settled(page,'idle')
        assert seen==[]
        membership=page.locator('[data-exposure-membership]')
        membership.locator(':scope > summary').click()
        button=membership.locator('button')
        button.wait_for(state='visible')
        button.click()
        settled(page,'ready' if identity_matches else 'unavailable')
        if identity_matches:
            assert len(seen)==2
            assert page.locator('#ox-company input').input_value()=='TEST'
            assert '2026-01-01' in membership.inner_text()
            page.locator('.ox-company-choices button').click()
            page.get_by_text('SYNTHETIC TEST PRODUCT',exact=True).wait_for()
            assert len(seen)==3
            assert page.url.endswith('/ontology.html')
            page.evaluate("window.dispatchEvent(new CustomEvent('mdx-auth',{detail:{user:null,event:'SIGNED_OUT'}}))")
            assert page.locator('#ox-root .ox-hero').count()==0
            assert 'SYNTHETIC TEST PRODUCT' not in page.content()
            assert page.locator('#ox-company input').input_value()==''
        else:
            assert len(seen)==1
            assert page.locator('.ox-company-choices button').count()==0
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        assert errors==[]
    finally:
        context.close()


def test_back_forward_restore_loads_a_new_reading_after_clearing_old_state(browser, synthetic_snapshot):
    context, page = incumbent._open(browser, synthetic_snapshot, width=1440, height=900)
    try:
        before = page.evaluate("window.__fetchCount")
        page.locator("#ox-steps .ox-brain-action").first.click()
        page.evaluate("window.dispatchEvent(new PageTransitionEvent('pagehide',{persisted:true}))")
        assert page.locator("#ox-root .ox-hero").count() == 0
        assert page.evaluate("window.MM_BRAIN_CFG.getOntologySelection()") is None
        page.evaluate("window.dispatchEvent(new PageTransitionEvent('pageshow',{persisted:true}))")
        page.locator("#ox-root .ox-hero").wait_for()
        assert page.evaluate("window.__fetchCount") == before + 1
    finally:
        context.close()
