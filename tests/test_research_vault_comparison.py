"""Qualified synthetic owners over the actual canonical Read service."""
from dataclasses import replace
from datetime import datetime, timezone
import copy, hashlib, json
from unittest.mock import Mock
import pytest
from engine.research_vault import catalog, fulltext
from engine.research_vault.r2_store import LocalStore
from engine.research_vault.read_service import ResearchReadService, ServerReadContext
from engine.research_vault.read_adapters import BrainResearchAdapter, TOOL_NAMES
from engine.research_vault.comparison import ComparisonOwners, QualifiedBasis, QualifiedRevision
from engine.research_intelligence.store import StoredResearchIntelligence
from engine.research_intelligence.schema import SCHEMA
from engine.research_intelligence.selection import build_selection_catalog, source_context_receipt

NOW=datetime(2026,10,3,tzinfo=timezone.utc)
def sha(raw):return hashlib.sha256(raw.encode() if isinstance(raw,str) else raw).hexdigest()
BASIS={'subject':'demand','horizon':'2027','units':'percent','currency':'not_applicable','scenario':'base'}
CTX=ServerReadContext(principal_id='member',entitlement='pro',scopes=frozenset({'find_evidence'}),surface='brain')
def rio(rid,institution,text):
    doc={'id':rid,'source_type':'institutional_research','source_name':'Synthetic','institution':institution,'desk':'','title':'Synthetic','published_at':'2026-10-01','content_sha256':sha(text)}
    claims=[{'statement':unit,'evidence':[{'quote_span':unit}],'numbers':[],'entities':[],'horizon':'','explicit':False} for unit in text.split('\n') if unit]
    analysis={'thesis':{'summary':'A synthetic institution presents a qualified demand outlook.','direction':'unclear','mechanism':[],'conviction':'','support_claim_indices':[0]},'assumptions':[],'forecasts':[],'catalysts':[],'falsifiers':[],'counterarguments':[],'implications':[],'uncertainties':[],'belief_delta':{'statement':'','support_claim_indices':[]},'consensus_relation':{'statement':'','support_claim_indices':[]}}
    obj={'schema':SCHEMA,'document':doc,'claims':claims,'analysis':analysis,'authority':'descriptive_research_only'}
    receipt={'prompt_version':'mastermind.research_intelligence.extractor.v3','source_context':source_context_receipt(build_selection_catalog(doc,text))}
    return StoredResearchIntelligence(document_id=rid,artifact_sha256=sha('artifact-'+rid+text),rio_sha256=sha(json.dumps(obj)),source_content_sha256=sha(text),artifact_key='synthetic',pointer_key='synthetic',pointer_version='1',is_latest=True,receipt=receipt,rio=obj)

@pytest.fixture
def configured(tmp_path):
    ids=('fixture-left','fixture-right')
    texts={ids[0]:'Aster Bank expects demand growth of 3% in 2027 under the base scenario.',ids[1]:'Other Bank expects demand growth of 4% in 2027 under the base scenario.'}
    institutions={ids[0]:'Aster Bank',ids[1]:'Other Bank'}
    items=[{'id':rid,'title':'Synthetic','institution':institutions[rid],'published_at':f'2026-10-0{i+1}T00:00:00Z','side':'sell','pages':1,'language':'en','summary_points':['Synthetic metadata']} for i,rid in enumerate(ids)]
    records={rid:fulltext.build_extracted_text(report_id=rid,source_pdf_sha256=sha('pdf-'+rid),text=texts[rid],extractor_name='pdftotext',extractor_version='synthetic-v1',page_count=1,text_layer_state='full') for rid in ids}
    stored={rid:rio(rid,institutions[rid],texts[rid]) for rid in ids}
    store=LocalStore(tmp_path/'catalog');store.put_bytes(catalog.CATALOG_KEY,catalog.serialize({'schema':catalog.SCHEMA,'items':items},NOW))
    calls={'load':[],'commit':[],'preflight':[]}
    def load(rid,item):calls['load'].append(rid);return records[rid]
    def binding(legs):return tuple((x['id'],x['extracted']['source_pdf_sha256'],x['extracted']['extracted_text_sha256'],x['stored'].artifact_sha256,x['selected_ref']['claim_index']) for x in legs)
    def basis(ctx,ref,legs):
        return QualifiedBasis(binding(legs),(dict(BASIS),dict(BASIS)),({'kind':'source_topic','subject':'demand','provenance':'synthetic-source-adjudication'},)*2,'synthetic-independent-basis')
    def pre(ctx,pair,now):calls['preflight'].append(pair);return True
    def commit(ctx,pair,now):calls['commit'].append(pair);return True
    owners=ComparisonOwners(lambda ctx,obj:True,pre,commit,basis)
    service=ResearchReadService(catalog_store=store,corpus_connection=lambda:None,preview_selector=lambda _:[],extracted_text_loader=load,source_digest_reader=lambda rid:records[rid]['source_pdf_sha256'],rio_reader=lambda rid:stored[rid],clock=lambda:NOW,comparison_owners=owners)
    return service,owners,records,stored,calls,binding

def prepare(service):return service.comparison_view(caller_context=CTX,request={'action':'prepare','left':{'report_id':'fixture-left'},'right':{'report_id':'fixture-right'}})
def request(prepared):return {'action':'compare','left':prepared['left']['claims'][0]['ref'],'right':prepared['right']['claims'][0]['ref'],'basis_ref':'synthetic-basis'}
def compare(service,req):return service.comparison_view(caller_context=CTX,request=req)

def test_default_missing_owners_refuses_before_private_reads(configured):
    service,_,_,_,calls,_=configured;service._comparison_owners=None
    assert prepare(service)['reason']=='COMPARISON_OWNERS_UNAVAILABLE'
    assert not calls['load'] and not calls['commit']

def test_denied_context_and_mcp_surface_refuse_before_reads(configured):
    service,_,_,_,calls,_=configured
    for ctx in ({'entitlement':'pro'},replace(CTX,entitlement='preview'),replace(CTX,scopes=frozenset()),replace(CTX,surface='mcp')):
        assert service.comparison_view(caller_context=ctx,request={})['state']=='DENIED'
    assert not calls['load']

def test_prepare_then_pair_retains_both_exact_spans_and_partial_state(configured):
    service,_,records,_,calls,_=configured;p=prepare(service)
    assert p['state']=='INPUTS_ONLY' and p['basis_state']=='UNRESOLVED' and 'comparison' not in p
    for side in ('left','right'):
        assert p[side]['revision_state']=='CURRENT'
        assert p[side]['source_context']['coverage']=='PARTIAL_SOURCE_CONTEXT'
    got=compare(service,request(p));assert got['state']=='AVAILABLE'
    assert got['comparison']['relation']=='DIFFERING_SOURCE_STATEMENTS'
    assert got['comparison']['revision_relation']=='UNCLASSIFIED'
    assert 'RIO_PARTIAL' in got['limitations']
    for side in ('left','right'):
        span=got['comparison'][side]['evidence'][0];body=records[span['report_id']]['text'].encode()
        assert body[span['start_byte']:span['end_byte']]==span['text'].encode()
    assert calls['commit']==[('fixture-left','fixture-right')]*2

@pytest.mark.parametrize('key,value',[('source_pdf_sha256','f'*64),('extracted_text_sha256','f'*64),('rio_artifact_sha256','f'*64),('claim_index',True),('claim_index',29),('user_ctx',{})])
def test_requested_identity_index_and_injection_fail_without_commit(configured,key,value):
    service,_,_,_,calls,_=configured;req=request(prepare(service));calls['commit'].clear();req['left'][key]=value
    got=compare(service,req);assert got['state']=='UNAVAILABLE' and 'comparison' not in got and 'left' not in got
    assert not calls['commit']

def test_missing_semantic_and_basis_owners_are_not_inferred(configured):
    service,owners,_,_,calls,_=configured
    service._comparison_owners=replace(owners,semantic=lambda *_:False)
    assert prepare(service)['reason']=='SEMANTIC_UNQUALIFIED';assert not calls['commit']
    service._comparison_owners=owners;req=request(prepare(service));calls['commit'].clear()
    service._comparison_owners=replace(owners,basis=None)
    assert compare(service,req)['reason']=='BASIS_UNAVAILABLE';assert not calls['commit']

@pytest.mark.parametrize('mutation',['different_horizon','wrong_binding','current_alias','unmapped_alias'])
def test_unqualified_owner_basis_fails_closed(configured,mutation):
    service,owners,_,_,calls,binding=configured;req=request(prepare(service));calls['commit'].clear()
    def basis(ctx,ref,legs):
        obj=owners.basis(ctx,ref,legs)
        if mutation=='different_horizon':return replace(obj,bases=(obj.bases[0],{**BASIS,'horizon':'2030'}))
        if mutation=='wrong_binding':return replace(obj,bindings=(('wrong',)*4,obj.bindings[1]))
        sec='SEC:US-XNYS-MMC'
        subject={'kind':'historical_security','security_id':sec,'alias_vendor':'store' if mutation=='current_alias' else 'native_reference','resolution_state':'UNMAPPED' if mutation=='unmapped_alias' else 'RESOLVED','resolution_date':'2026-10-01','decision_at':'2026-10-03T00:00:00Z','provenance':'synthetic'}
        return replace(obj,bases=({**BASIS,'subject':sec},{**BASIS,'subject':sec}),subjects=(subject,subject))
    service._comparison_owners=replace(owners,basis=basis)
    got=compare(service,req);assert got['state']=='UNAVAILABLE';assert not calls['commit']
    if mutation in {'current_alias','unmapped_alias'}:assert got['reason']=='HISTORICAL_ALIAS_UNQUALIFIED'

def test_source_race_and_failed_atomic_quota_expose_neither_leg(configured):
    service,owners,records,_,calls,_=configured;req=request(prepare(service));calls['commit'].clear()
    def changed(ctx,ref,legs):
        answer=owners.basis(ctx,ref,legs)
        rid='fixture-right';records[rid]=fulltext.build_extracted_text(report_id=rid,source_pdf_sha256=records[rid]['source_pdf_sha256'],text='A corrected synthetic body has a different extracted text identity.',extractor_name='pdftotext',extractor_version='synthetic-v1',page_count=1,text_layer_state='full')
        return answer
    service._comparison_owners=replace(owners,basis=changed)
    got=compare(service,req);assert got['state']=='UNAVAILABLE' and 'left' not in got;assert not calls['commit']
    service._comparison_owners=replace(owners,commit=lambda *_:False)
    got=prepare(service);assert got['state']=='UNAVAILABLE' and 'left' not in got

def test_preflight_failure_does_not_read_private_source(configured):
    service,owners,_,_,calls,_=configured;service._comparison_owners=replace(owners,preflight=lambda *_:False)
    assert prepare(service)['reason']=='QUOTA_UNAVAILABLE';assert not calls['load'] and not calls['commit']

def test_aggregate_budget_omits_whole_units_and_never_compares_overflow(configured,monkeypatch):
    service,_,_,_,calls,_=configured
    import engine.research_vault.comparison as module
    monkeypatch.setattr(module,'MAX_CHARS',100)
    got=prepare(service);assert got['state']=='UNAVAILABLE' and 'left' not in got;assert not calls['commit']

def test_partial_receipt_version_tamper_and_owner_exceptions_refuse(configured):
    service,owners,_,stored,calls,_=configured
    stored['fixture-left'].receipt['source_context']['coverage']='COMPLETE'
    assert prepare(service)['state']=='UNAVAILABLE';assert not calls['commit']
    service._comparison_owners=replace(owners,semantic=Mock(side_effect=RuntimeError('synthetic')))
    assert prepare(service)['state']=='UNAVAILABLE'

def test_private_adapter_does_not_add_a_public_tool(configured):
    service,_,_,_,_,_=configured;adapter=BrainResearchAdapter(service)
    assert adapter.comparison_view({'action':'prepare','left':{'report_id':'fixture-left'},'right':{'report_id':'fixture-right'}},server_context=CTX)['state']=='INPUTS_ONLY'
    assert set(TOOL_NAMES)=={'research_status','research_search','research_fetch','research_find_evidence'}


def test_failed_atomic_commit_is_exercised_after_qualified_reads(configured):
    service,owners,_,_,calls,_=configured
    failed=Mock(return_value=False);service._comparison_owners=replace(owners,commit=failed)
    got=prepare(service)
    assert got['reason']=='QUOTA_UNAVAILABLE' and 'left' not in got and 'right' not in got
    assert len(calls['load'])==4
    failed.assert_called_once()


def test_rio_artifact_race_refuses_before_commit(configured):
    service,owners,_,stored,calls,_=configured;req=request(prepare(service));calls['commit'].clear()
    def changed(ctx,ref,legs):
        answer=owners.basis(ctx,ref,legs)
        stored['fixture-right']=replace(stored['fixture-right'],artifact_sha256='f'*64)
        return answer
    service._comparison_owners=replace(owners,basis=changed)
    assert compare(service,req)['reason']=='RIO_CHANGED'
    assert not calls['commit']


def revision_pair(configured):
    service,owners,records,stored,calls,binding=configured
    doc,_=service._read_catalog(NOW);doc=copy.deepcopy(doc)
    next(item for item in doc['items'] if item['id']=='fixture-right')['institution']='Aster Bank'
    service._catalog_store.put_bytes(catalog.CATALOG_KEY,catalog.serialize(doc,NOW))
    right='fixture-right';quote='Correction: our prior demand estimate was an error.'
    text='Aster Bank expects demand growth of 4% in 2027 under the base scenario.\n'+quote
    records[right]=fulltext.build_extracted_text(report_id=right,source_pdf_sha256=sha('corrected-pdf'),text=text,extractor_name='pdftotext',extractor_version='synthetic-v1',page_count=1,text_layer_state='full')
    stored[right]=rio(right,'Aster Bank',text)
    def basis(ctx,ref,legs):return replace(owners.basis(ctx,ref,legs),families=('synthetic-family',)*2)
    def revision(ctx,ref,legs):return QualifiedRevision(binding(legs),'CORRECTED_FACTUAL_ERROR',quote,'synthetic-independent-revision')
    service._comparison_owners=replace(owners,basis=basis,revision=revision)
    return service,doc,records,stored,calls

def test_same_family_correction_and_wrong_chronology_are_distinct(configured):
    service,doc,_,_,calls=revision_pair(configured)
    req=request(prepare(service));req['revision_ref']='synthetic-correction';calls['commit'].clear()
    got=compare(service,req);assert got['state']=='AVAILABLE'
    assert got['comparison']['revision_relation']=='CORRECTED_FACTUAL_ERROR'
    assert got['comparison']['revision_support']['text'].startswith('Correction:')
    next(item for item in doc['items'] if item['id']=='fixture-left')['published_at']='2026-10-03T00:00:00Z'
    service._catalog_store.put_bytes(catalog.CATALOG_KEY,catalog.serialize(doc,NOW));calls['commit'].clear()
    assert compare(service,req)['reason']=='REVISION_CHRONOLOGY_UNQUALIFIED';assert not calls['commit']

@pytest.mark.parametrize('same_pdf,expected',[(True,'IDENTICAL_REPORT_REISSUE'),(False,'IDENTICAL_EXTRACTED_TEXT')])
def test_identical_text_reissue_classes_do_not_become_changed_view(configured,same_pdf,expected):
    service,_,records,stored,calls=revision_pair(configured)
    text=records['fixture-left']['text']
    records['fixture-right']=fulltext.build_extracted_text(report_id='fixture-right',source_pdf_sha256=records['fixture-left']['source_pdf_sha256'] if same_pdf else sha('another-pdf'),text=text,extractor_name='pdftotext',extractor_version='synthetic-v1',page_count=1,text_layer_state='full')
    stored['fixture-right']=rio('fixture-right','Aster Bank',text)
    req=request(prepare(service));calls['commit'].clear()
    assert compare(service,req)['comparison']['revision_relation']==expected
    req['revision_ref']='synthetic-correction';calls['commit'].clear()
    assert compare(service,req)['reason']=='REVISION_ANNOTATION_CONFLICT';assert not calls['commit']

def test_real_12000_aggregate_quote_budget_refuses_complete_pair(configured):
    service,_,records,stored,calls,_=configured
    for rid,institution in [('fixture-left','Aster Bank'),('fixture-right','Other Bank')]:
        units=[institution+f' scenario {index} expects '+('synthetic demand scope '*58)+'in 2027 under the base scenario.' for index in range(6)]
        assert max(map(len,units))<1600
        text='\n'.join(units)
        records[rid]=fulltext.build_extracted_text(report_id=rid,source_pdf_sha256=sha('large-'+rid),text=text,extractor_name='pdftotext',extractor_version='synthetic-v1',page_count=1,text_layer_state='full')
        stored[rid]=rio(rid,institution,text)
        stored[rid].rio['claims'][0]['evidence']=[{'quote_span':unit} for unit in units]
    req={'action':'compare','basis_ref':'synthetic-basis'}
    for side,rid in [('left','fixture-left'),('right','fixture-right')]:
        req[side]={'report_id':rid,'source_pdf_sha256':records[rid]['source_pdf_sha256'],'extracted_text_sha256':records[rid]['extracted_text_sha256'],'rio_artifact_sha256':stored[rid].artifact_sha256,'claim_index':0}
    got=compare(service,req)
    assert got['reason']=='OUTPUT_BUDGET_UNAVAILABLE' and 'left' not in got and 'comparison' not in got
    assert not calls['commit']


def test_historical_security_basis_uses_existing_dataos_resolver_and_publication_vintage(configured):
    from lib.dataos.identity import AliasRow, VendorAliasTable
    from engine.research_vault.subjects import resolve_candidates, CANDIDATE_SCHEMA
    from datetime import date
    service,owners,records,stored,calls,binding=configured
    aliases=VendorAliasTable([AliasRow(vendor='synthetic_vendor',vendor_symbol='MMC',security_id='SEC:US-XNYS-MMC',valid_from=date(2020,1,1))])
    for rid,institution in [('fixture-left','Aster Bank'),('fixture-right','Other Bank')]:
        text=institution+' expects MMC demand growth of 3% in 2027 under the base scenario.'
        records[rid]=fulltext.build_extracted_text(report_id=rid,source_pdf_sha256=sha('mmc-'+rid),text=text,extractor_name='pdftotext',extractor_version='synthetic-v1',page_count=1,text_layer_state='full')
        stored[rid]=rio(rid,institution,text)
    def basis(ctx,ref,legs):
        subjects=[]
        for leg in legs:
            candidates={'schema':CANDIDATE_SCHEMA,'report_id':leg['id'],'candidates':[{'symbol':'MMC','confidence':0.9,'methods':['synthetic-literal-mention'],'source_fields':['body']} ]}
            resolved=resolve_candidates(candidates,aliases=aliases,alias_vendor='synthetic_vendor',published_at=leg['item']['published_at'],decision_at=NOW)
            row=resolved['subjects'][0]
            subjects.append({'kind':'historical_security','security_id':row['security_id'],'alias_vendor':row['alias_vendor'],'resolution_state':row['resolution_state'],'resolution_date':row['resolution_date'],'decision_at':resolved['decision_at'],'provenance':'existing-dataos-synthetic-owner'})
        return QualifiedBasis(binding(legs),({**BASIS,'subject':'SEC:US-XNYS-MMC'},)*2,tuple(subjects),'synthetic-qualified-basis')
    service._comparison_owners=replace(owners,basis=basis)
    req=request(prepare(service));assert compare(service,req)['state']=='AVAILABLE'
    def wrong_vintage(ctx,ref,legs):
        obj=basis(ctx,ref,legs);row={**obj.subjects[0],'resolution_date':'2020-01-01'}
        return replace(obj,subjects=(row,obj.subjects[1]))
    service._comparison_owners=replace(owners,basis=wrong_vintage);calls['commit'].clear()
    assert compare(service,req)['reason']=='HISTORICAL_ALIAS_UNQUALIFIED';assert not calls['commit']

def test_thin_source_degradation_is_retained_separately_from_current_rio(configured,monkeypatch):
    service,_,records,_,_,_=configured
    rid='fixture-left';record=records[rid]
    records[rid]=fulltext.build_extracted_text(report_id=rid,source_pdf_sha256=record['source_pdf_sha256'],text=record['text'],extractor_name='pdftotext',extractor_version='synthetic-v1',page_count=1,text_layer_state='thin')
    doc,_=service._read_catalog(NOW)
    monkeypatch.setattr(service,'_read_catalog',lambda now:(doc,{'known_degradation':[]}))
    got=prepare(service)
    assert got['state']=='INPUTS_ONLY' and got['left']['revision_state']=='CURRENT'
    assert 'FULL_TEXT_PARTIAL' in got['limitations'] and 'RIO_PARTIAL' in got['limitations']


def test_existing_brain_compare_branch_reaches_private_adapter_and_actual_service(configured):
    import ast, os
    from pathlib import Path
    service,_,_,_,calls,_=configured
    file=Path(os.environ.get('I03_SOURCE_ROOT',Path(__file__).parents[1]))/'engine/neuralweb/brain_market_intel.py'
    nodes=[n for n in ast.parse(file.read_text()).body if isinstance(n,ast.FunctionDef) and n.name in {'search_research','_research_compare','_server_read_context'}]
    ns={'Path':Path,'datetime':datetime,'_RESEARCH_LIMIT_DEFAULT':5,'_MODE_COMPARE':'compare','_is_mode':lambda value,wanted:isinstance(value,str) and value.strip().lower()==wanted,'_brain_research_adapter':lambda:BrainResearchAdapter(service)}
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(file),'exec'),ns)
    req={'action':'prepare','left':{'report_id':'fixture-left'},'right':{'report_id':'fixture-right'}}
    assert ns['search_research'](Path('/synthetic'),mode=' COMPARE ',comparison=req,user_ctx={'user_id':'member'})['state']=='INPUTS_ONLY'
    calls['load'].clear()
    assert ns['search_research'](Path('/synthetic'),mode='compare',comparison=req,user_ctx=None)['state']=='DENIED'
    assert not calls['load']


def add_second_claim(records, stored, rid, institution):
    text = records[rid]['text'] + '\n' + institution + ' expects demand growth of 5% in 2028 under the base scenario.'
    records[rid] = fulltext.build_extracted_text(report_id=rid, source_pdf_sha256=records[rid]['source_pdf_sha256'], text=text, extractor_name='pdftotext', extractor_version='synthetic-v1', page_count=1, text_layer_state='full')
    stored[rid] = rio(rid, institution, text)


def test_cached_basis_cannot_qualify_other_claim_in_same_artifact(configured):
    service, owners, records, stored, calls, _ = configured
    add_second_claim(records, stored, 'fixture-left', 'Aster Bank')
    req = request(prepare(service)); captured = []
    def capture(ctx, ref, legs):
        answer = owners.basis(ctx, ref, legs); captured.append(answer); return answer
    service._comparison_owners = replace(owners, basis=capture)
    assert compare(service, req)['state'] == 'AVAILABLE'
    cached = captured[0]; calls['commit'].clear()
    service._comparison_owners = replace(owners, basis=lambda *_: cached)
    req['left']['claim_index'] = 1
    got = compare(service, req)
    assert got['state'] == 'UNAVAILABLE'
    assert got['reason'] == 'BASIS_UNQUALIFIED' and 'left' not in got
    assert not calls['commit']


def test_cached_revision_cannot_qualify_other_claim_in_same_artifact(configured):
    service, _, records, stored, calls = revision_pair(configured)
    add_second_claim(records, stored, 'fixture-left', 'Aster Bank')
    owners = service._comparison_owners; captured = []
    def capture(ctx, ref, legs):
        answer = owners.revision(ctx, ref, legs); captured.append(answer); return answer
    service._comparison_owners = replace(owners, revision=capture)
    req = request(prepare(service)); req['revision_ref'] = 'synthetic-correction'
    assert compare(service, req)['state'] == 'AVAILABLE'
    cached = captured[0]; calls['commit'].clear()
    service._comparison_owners = replace(owners, revision=lambda *_: cached)
    req['left']['claim_index'] = 1
    got = compare(service, req)
    assert got['state'] == 'UNAVAILABLE'
    assert got['reason'] == 'REVISION_UNQUALIFIED' and 'left' not in got
    assert not calls['commit']


@pytest.mark.parametrize('mutation', ['withdrawal', 'institution', 'published_at'])
def test_final_catalog_target_race_refuses_before_commit(configured, mutation):
    service, owners, _, _, calls, _ = configured
    req = request(prepare(service)); calls['commit'].clear()
    def changed(ctx, ref, legs):
        answer = owners.basis(ctx, ref, legs)
        doc, _ = service._read_catalog(NOW); doc = copy.deepcopy(doc)
        if mutation == 'withdrawal':
            doc['items'] = [item for item in doc['items'] if item['id'] != 'fixture-right']
        else:
            target = next(item for item in doc['items'] if item['id'] == 'fixture-right')
            target[mutation] = 'Changed Bank' if mutation == 'institution' else '2026-10-01T12:00:00Z'
        service._catalog_store.put_bytes(catalog.CATALOG_KEY, catalog.serialize(doc, NOW))
        return answer
    service._comparison_owners = replace(owners, basis=changed)
    got = compare(service, req)
    assert got['state'] == 'UNAVAILABLE'
    assert got['reason'] == 'CATALOG_TARGET_CHANGED' and 'left' not in got and 'comparison' not in got
    assert not calls['commit']


def test_final_semantic_recheck_cannot_withdraw_target_before_delivery(configured):
    service, owners, _, _, calls, _ = configured
    req = request(prepare(service)); calls['commit'].clear(); count = []
    def semantic(ctx, obj):
        count.append(obj.document_id)
        if len(count) == 4:
            doc, _ = service._read_catalog(NOW); doc = copy.deepcopy(doc)
            doc['items'] = [x for x in doc['items'] if x['id'] != 'fixture-right']
            service._catalog_store.put_bytes(catalog.CATALOG_KEY, catalog.serialize(doc, NOW))
        return True
    service._comparison_owners = replace(owners, semantic=semantic)
    got = compare(service, req)
    assert got['state'] == 'UNAVAILABLE' and got['reason'] == 'CATALOG_TARGET_CHANGED'
    assert not calls['commit']


def test_unrelated_catalog_metadata_change_does_not_freeze_selected_pair(configured):
    service, owners, _, _, calls, _ = configured
    req = request(prepare(service)); calls['commit'].clear()
    def changed(ctx, ref, legs):
        for side, leg in zip(('left', 'right'), legs):
            assert leg['selected_ref'] == req[side]
        answer = owners.basis(ctx, ref, legs)
        doc, _ = service._read_catalog(NOW); doc = copy.deepcopy(doc)
        unrelated = copy.deepcopy(doc['items'][0]); unrelated['id'] = 'fixture-unrelated'
        doc['items'].append(unrelated)
        service._catalog_store.put_bytes(catalog.CATALOG_KEY, catalog.serialize(doc, NOW))
        return answer
    service._comparison_owners = replace(owners, basis=changed)
    assert compare(service, req)['state'] == 'AVAILABLE'
    assert calls['commit'] == [('fixture-left', 'fixture-right')]


def test_owner_boolean_index_is_not_an_exact_claim_binding(configured):
    service, owners, _, _, calls, _ = configured
    req = request(prepare(service)); calls['commit'].clear()
    def malformed(ctx, ref, legs):
        answer = owners.basis(ctx, ref, legs)
        return replace(answer, bindings=((*answer.bindings[0][:4], False), answer.bindings[1]))
    service._comparison_owners = replace(owners, basis=malformed)
    got = compare(service, req)
    assert got['state'] == 'UNAVAILABLE' and got['reason'] == 'BASIS_UNQUALIFIED'
    assert not calls['commit']
