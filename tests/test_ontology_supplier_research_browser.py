"""Actual Macro modules and native compiler projection, synthetic source custody.

All requests are intercepted; no private endpoint, provider or live source is read.
"""
from copy import deepcopy
from datetime import date
from hashlib import sha256
import json
import os
from pathlib import Path

import pytest

from app.company_supplier_research import _project, SCHEMA
from engine.company_intelligence.current_company_context import resolve_current_company
from tests.test_h20_supplier_conditional import captured, native_context, synthetic_identity_base, compose
from tests.test_ontology_company_browser import browser, page, start, supplier_fixtures, fixtures, HEADERS


def settled(page, state):
    page.wait_for_function("!['idle','loading'].includes(document.querySelector('[data-company-result]').dataset.state)")
    actual=page.locator('[data-company-result]').get_attribute('data-state')
    assert actual==state, page.locator('[data-company-result]').text_content()


@pytest.fixture
def research_wire(captured,native_context):
    native=compose(captured,native_context);candidate=_project(native)
    context=resolve_current_company(native_context[1](),'NVDA',today=date(2026,10,19))
    _,selection,fact=supplier_fixtures()
    selection['issuer_binding']=context['issuer_binding']
    fact['fact'].update(subject_id='ISS:US-XNAS-NVDA',object_id='ISS:US-XNYS-TSM')
    fact['reference'].update(native_context[0]['context']['provenance']['reference'])
    fact['edition'].update(native_context[0]['context']['provenance']['edition'])
    source=fact['source_timing']['sec_source'];o=candidate['observed']
    source.update({k:o[k] for k in ['document_id','accession','archive_url']},issuer_cik='0001045810',
        accepted_at=o['reporting_at'],retrieved_at=o['retrieved_at'],recorded_at='2026-10-09T04:00:00Z',
        snapshot_at='2026-10-09T04:00:01Z',
        manifest_key='manifests/0001045810/'+o['accession']+'/ffsec_manifest_'+'2'*64+'.json')
    fact['source_timing'].update(published_date='2026-02-25',known_at='2026-10-19T15:51:28Z')
    fact['supplier_binding'].update(identity_observed_at='2026-10-19T15:35:16Z',adopted_at='2026-10-19T15:51:28Z',
        current_subject_identity=context['issuer_binding']['identity_snapshot_reference']['sha256'],
        evidence_revision=sha256(json.dumps(source,sort_keys=True,separators=(',',':')).encode()).hexdigest())
    return context,selection,fact,{'schema':SCHEMA,'status':'available','reason':None,'disclosure':deepcopy(fact),'candidate':candidate}


def open_research(page,wire,*,full_shell=False):
    context,selection,fact,research=wire
    # The synthetic native fixtures have fixed clocks, including current identity.
    page.clock.install(time='2026-10-19T18:02:00Z')  # 2026-10-19T18:02:00Z
    seen,errors=start(page,context=context,selection=selection,fact=fact,full_shell=full_shell)
    validation=page.evaluate("""async ([context,selection])=>{
      const d=await import('/ontology-company-contract.js');
      try { const c=await d.decodePrivateCompanyContext(context,'NVDA');
        const s=d.decodePrivateIssuerSelections(selection,c.issuer_binding.issuer_id);
        d.assertPrivateContextSelection(c,s); return null;
      } catch(e) { return e.stack; }
    }""",[context,selection])
    assert validation is None, validation
    calls=[]
    def result(route):
        calls.append(route.request.url)
        route.fulfill(status=200,headers=HEADERS,body=json.dumps(research))
    page.route('**/api/company-intelligence/private/supplier-research/**',result)
    page.locator('#ox-company input').fill('NVDA')
    page.locator('#ox-company button[type=submit]').click();settled(page,'ready')
    page.locator('#ox-company .ox-company-choices button').click();settled(page,'ready')
    assert page.locator('.ox-company-fact').count()==1
    assert calls==[]
    page.locator('.ox-company-fact button').click();settled(page,'ready')
    return seen,calls,errors


@pytest.mark.parametrize('theme',['dark','light'])
@pytest.mark.parametrize('language',['en','zh'])
@pytest.mark.parametrize('width',[390,1440])
def test_native_conditional_result_and_refused_context_are_distinct_in_macro(page,research_wire,theme,language,width):
    page.set_viewport_size({'width':width,'height':1100})
    seen,calls,errors=open_research(page,research_wire,full_shell=True)
    page.evaluate("([t,l])=>{document.documentElement.dataset.theme=t;document.documentElement.dataset.lang=l;}",[theme,language])
    panel=page.locator('.ox-company-research')
    assert panel.count()==1 and panel.get_attribute('data-research-status')=='available'
    text=panel.text_content()
    for phrase in ['Reported event','Proposed transmission','What would test it','Context-only path refused',
                   'unestablished','not independent confirmations','No empirical test']:
        # The UI uses direct ordinary wording for unestablished applicability.
        assert (phrase if phrase!='unestablished' else 'not established') in text
    assert '条件' in text and '未经检验' in text
    assert len(calls)==1 and len(seen)==3 and not errors
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1')
    panel.locator('summary').click()
    assert 'eph2:' in panel.text_content()
    if folder:=os.environ.get('MO_RESEARCH_VISUAL_DIR'):
        path=Path(folder);path.mkdir(parents=True,exist_ok=True)
        page.locator('#ox-company').screenshot(path=str(path/f'{theme}-{language}-{width}.png'))
    page.evaluate("window.dispatchEvent(new CustomEvent('mdx-auth',{detail:{user:null}}))")
    assert page.locator('.ox-company-research').count()==0
    assert 'eph2:' not in page.content()
    stored=page.evaluate('JSON.stringify([Object.entries(localStorage),Object.entries(sessionStorage)])')
    for private in ('eph2:',research_wire[2]['generation'],research_wire[2]['fact']['fact_id'],'fixture-token'):
        assert private not in stored


@pytest.mark.parametrize('mutation',['extra','changed_fact','source','future','historical','authority','observed_transfer',
    'independent','occurrence','outcome','missing_test','script'])
def test_misbound_or_promoted_research_is_withheld_without_retry(page,research_wire,mutation):
    root=research_wire[3];c=root['candidate']
    if mutation=='extra':c['private_source_text']='forbidden'
    elif mutation=='changed_fact':root['disclosure']['generation']='changed'
    elif mutation=='source':c['observed']['archive_url']='https://evil.invalid/source'
    elif mutation=='future':c['observed']['verified_at']='2099-01-01T00:00:00Z'
    elif mutation=='historical':c['compiled_at']='2026-10-18T18:01:00Z'
    elif mutation=='authority':c['authority']['trade']=True
    elif mutation=='observed_transfer':c['mechanism']['state']='observed'
    elif mutation=='independent':c['lineage']['independent_corroboration']=True
    elif mutation=='occurrence':c['observed']['occurrence_at']=c['observed']['reporting_at']
    elif mutation=='outcome':c['empirical_evaluation']='confirmed'
    elif mutation=='missing_test':c['evaluation_requirements'].pop()
    elif mutation=='script':c['mechanism']['hypothesis_text']='<img src=x onerror="window.injection=true">'
    # Exact data is never inserted as HTML, even when supplied as safe text.
    if mutation=='script':
        seen,calls,errors=open_research(page,research_wire)
        assert page.locator('.ox-company-research img').count()==0
        assert page.evaluate('window.injection===undefined')
        assert len(calls)==1 and not errors
        return
    context,selection,fact,research=research_wire
    page.clock.install(time='2026-10-19T18:02:00Z')
    seen,errors=start(page,context=context,selection=selection,fact=fact)
    validation=page.evaluate("""async ([context,selection])=>{
      const d=await import('/ontology-company-contract.js');
      try { const c=await d.decodePrivateCompanyContext(context,'NVDA');
        const s=d.decodePrivateIssuerSelections(selection,c.issuer_binding.issuer_id);
        d.assertPrivateContextSelection(c,s); return null;
      } catch(e) { return e.stack; }
    }""",[context,selection])
    assert validation is None, validation
    calls=[]
    def answer(route):
        calls.append(1);route.fulfill(status=200,headers=HEADERS,body=json.dumps(research))
    page.route('**/api/company-intelligence/private/supplier-research/**',answer)
    page.locator('#ox-company input').fill('NVDA');page.locator('#ox-company button[type=submit]').click();settled(page,'ready')
    page.locator('#ox-company .ox-company-choices button').click();settled(page,'ready')
    page.locator('.ox-company-fact button').click();settled(page,'unavailable')
    assert calls==[1] and page.locator('.ox-company-research').count()==0 and not errors
    assert 'eph2:' not in page.content()


def test_planned_integration_stays_context_only_without_supplier_hypothesis(page):
    context,selection,fact=fixtures()
    seen,errors=start(page,context=context,selection=selection,fact=fact)
    calls=[]
    def answer(route):
        calls.append(route.request.url)
        route.fulfill(status=200,headers=HEADERS,body=json.dumps({
            'schema':SCHEMA,'status':'context_only','reason':'NO_QUALIFIED_SUPPLIER_ROLE',
            'disclosure':fact,'candidate':None}))
    page.route('**/api/company-intelligence/private/supplier-research/**',answer)
    page.locator('#ox-company input').fill('TEST')
    page.locator('#ox-company button[type=submit]').click();settled(page,'ready')
    page.locator('#ox-company .ox-company-choices button').click();settled(page,'ready')
    assert calls==[]
    page.locator('.ox-company-fact button').click();settled(page,'ready')
    card=page.locator('.ox-company-research')
    assert card.get_attribute('data-research-status')=='context_only'
    assert 'no second-order hypothesis is constructed' in card.text_content()
    assert page.locator('.ox-company-fact').count()==1
    assert len(calls)==1 and len(seen)==3 and not errors
    assert 'eph2:' not in page.content()
