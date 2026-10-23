"""Synthetic retained issuer source: no network/provider or real candidate effects."""
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from engine.press import desk_planner as P, validators as V
from scripts import stage_issuer_release_press as S, run_press as R
from tests import press_fixtures as F

URL = 'https://www.sec.gov/Archives/edgar/data/123456/000012345626000001/exampleex99.htm'
BODY = ('Exhibit 99 Example Energy, Inc. Oct. 21, 2026 Example Energy reports third-quarter results. '
        'Example Energy, Inc. (NYSE: EXM) reports adjusted diluted EPS of $1.24 per share '
        'for the three months ended September 30, 2026, versus $1.13 a year earlier. '
        'GAAP diluted EPS was $2.28 versus $1.18 per share. '
        'Backlog was 36.7 GW, including new origination of 3.7 GW. '
        'Annual adjusted EPS guidance remains unchanged at $3.92 to $4.02. '
        'Backlog is not delivered energy or revenue. Results are available beginning at 7:30 a.m. ET today.')

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def dump(path, obj):path.write_text(json.dumps(obj));return digest(path)

@pytest.fixture
def inputs(tmp_path):
    root=F.fixture_root(tmp_path/'fixture',engine_artifacts=False)
    (root/'site/stocks').mkdir(parents=True,exist_ok=True)
    (root/'site/stocks/EXM.html').write_text('<html>Example Energy</html>')
    doc=tmp_path/'release.html';doc.write_text('<html><body>'+BODY+'</body></html>')
    receipt=tmp_path/'retrieval.json'
    rh=dump(receipt,dict(url=URL,final_url=URL,status=200,method='GET',raw_sha256=digest(doc),bytes=doc.stat().st_size,observed_at='2026-10-23T12:00:00Z'))
    qualification=tmp_path/'qualification.json'
    q=dict(kind='sec_issuer_release_qualification',source_origin='issuer_authored',source_url=URL,
      accession='0000123456-26-000001',issuer='Example Energy, Inc.',title='Example Energy reports third-quarter results.',
      document_sha256=digest(doc),body_sha256=hashlib.sha256(BODY.encode()).hexdigest(),release_date='2026-10-21',
      release_date_literal='Oct. 21, 2026',declared_available_at='2026-10-21T11:30:00Z',availability_literal='beginning at 7:30 a.m. ET today',
      fiscal_period_literal='three months ended September 30, 2026',review_result='accepted_as_editorial_candidate_only',
      rights_basis=dict(qualification='independent_factual_citation',scope='Independently written issuer-attributed facts; no source republication.',limitations=['No blanket license or independent verification; copying remains restricted.'],terms_review='Reviewed source-specific restrictions; SEC hosting does not remove issuer rights.'),
      reviewed_claims=[dict(id='adjusted_eps',literal='adjusted diluted EPS of $1.24 per share for the three months ended September 30, 2026, versus $1.13 a year earlier.',quantity_literals=['1.24','1.13']),dict(id='backlog',literal='Backlog was 36.7 GW, including new origination of 3.7 GW.',quantity_literals=['36.7','3.7'])],
      reviewed_tickers={'EXM':'Example Energy, Inc. (NYSE: EXM)'},source_qualifiers=['Annual adjusted EPS guidance remains unchanged at $3.92 to $4.02.','Backlog is not delivered energy or revenue.'],allow_stage=False,allow_emit=False,publication_approved=False)
    qh=dump(qualification,q)
    return dict(document_path=doc,document_sha256=digest(doc),qualification_path=qualification,qualification_sha256=qh,retrieval_path=receipt,retrieval_sha256=rh,root=root,as_of='2026-10-23T13:00:00Z')

def invoke(inputs):return P.plan_external_candidate(source_kind='sec_issuer_release',**inputs)
def mutate(inputs, fn, kind='qualification'):
    p=inputs[kind+'_path'];o=json.loads(p.read_text());fn(o);inputs[kind+'_sha256']=dump(p,o)
def stage(inputs):
    kwargs={k:v for k,v in inputs.items() if k not in ('as_of','root')}
    return S.stage_issuer_release_candidate(inputs['root'],P.load_config(inputs['root']),now=datetime(2026,10,23,13,tzinfo=timezone.utc),**kwargs)

def test_candidate_only_full_raw_issuer_tier_and_no_effects(inputs,monkeypatch):
    monkeypatch.setattr(P,'plan',lambda *a,**k:pytest.fail('no selection'))
    monkeypatch.setattr(S.writer,'write',lambda *a,**k:pytest.fail('no provider'))
    before={str(p):p.read_bytes() for p in inputs['root'].rglob('*') if p.is_file()}
    r=invoke(inputs);ctx=r['validation_context']
    assert r['operation']=='planning_only' and not r['allow_stage'] and not r['allow_emit'] and not r['publication_approved']
    assert not r['cadence_consumed'] and 'id' not in r
    assert r['source_ref']=='issuer_sec:0000123456-26-000001:exampleex99.htm'
    assert ctx['raw_documents'][0]['text']==BODY
    assert ctx['primary_source']['name']=='Example Energy, Inc.' and ctx['primary_source']['kind']=='external'
    assert ctx['allowed_links']==['https://www.mastermind-x.com/stocks/EXM.html']
    assert all(f['tier']=='third_party' for f in ctx['facts'])
    assert 'unchanged' in ctx['facts'][-2]['text']
    assert r['source_clocks']['observed_at']!=r['source_clocks']['declared_available_at']
    assert before=={str(p):p.read_bytes() for p in inputs['root'].rglob('*') if p.is_file()}

def test_issuer_numbers_never_clear_our_value_or_receipt_floor(inputs,monkeypatch):
    ctx=invoke(inputs)['validation_context'];cfg=P.load_config(inputs['root'])
    draft={'body_html':'<p>Issuer adjusted EPS was $1.24 against $1.13 per share. Backlog was 36.7 GW with 3.7 GW originated.</p>'}
    own=V.check_our_value(draft,ctx,cfg);receipts=V.check_receipts(draft,ctx,cfg)
    assert own['ok'] is False and own['metrics']['our_value_share']==0 and receipts['ok'] is False
    monkeypatch.setattr(S,'_stage_preplanned_slots',lambda *a,**k:pytest.fail('must refuse before checkpoint/provider'))
    assert stage(inputs)['staged'] is False

@pytest.mark.parametrize('kind',['document','qualification','retrieval'])
def test_changed_original_evidence_refuses(inputs,kind):
    inputs[kind+'_path'].write_bytes(inputs[kind+'_path'].read_bytes()+b' ')
    with pytest.raises(ValueError,match='hash'):invoke(inputs)

@pytest.mark.parametrize('key,value',[
 ('source_origin','government_authored'),('accession','0000123456-26-000002'),('source_url',URL.replace('www.sec.gov','www.sec.gov.evil.test')),
 ('issuer','Different issuer'),('release_date','2026-10-22'),('release_date_literal','Oct. 20, 2026'),
 ('declared_available_at','2026-10-24T11:30:00Z'),('fiscal_period_literal','three months ended June 30, 2026'),
 ('allow_stage',True),('source_qualifiers',[]),('rights_basis',{}),('body_sha256','0'*64),
 ('reviewed_tickers',{'EXM':'Different issuer EXM'})])
def test_reviewed_identity_date_use_scope_fail_closed(inputs,key,value):
    mutate(inputs,lambda q:q.update({key:value}))
    with pytest.raises(ValueError):invoke(inputs)

@pytest.mark.parametrize('field,value',[('status',403),('method','POST'),('final_url',URL+'?alias=1'),('raw_sha256','0'*64),('bytes',1),('observed_at','2026-10-24T12:00:00Z')])
def test_original_retrieval_identity_refuses(inputs,field,value):
    mutate(inputs,lambda r:r.update({field:value}),'retrieval')
    with pytest.raises(ValueError):invoke(inputs)

@pytest.mark.parametrize('literal',[
 'adjusted diluted EPS of $2.28 per share for the three months ended September 30, 2026, versus $1.13 a year earlier.',
 'Annual adjusted EPS guidance was raised to $3.92 to $4.02.',
 'Realized demand was 36.7 GW.',
])
def test_adjusted_gaap_guidance_and_demand_mismatch_refuse(inputs,literal):
    mutate(inputs,lambda q:q['reviewed_claims'][0].update(literal=literal))
    with pytest.raises(ValueError,match='literal'):invoke(inputs)

def test_wrong_quantity_and_date_window_refuse(inputs):
    mutate(inputs,lambda q:q['reviewed_claims'][0].update(quantity_literals=['2.28']))
    with pytest.raises(ValueError,match='whole source atom'):invoke(inputs)
    mutate(inputs,lambda q:q['reviewed_claims'][0].update(quantity_literals=['1.24']))
    inputs['as_of']='2026-12-01T13:00:00Z'
    with pytest.raises(ValueError,match='window'):invoke(inputs)

def test_dossier_absence_and_symlink_ancestry_refuse(inputs,tmp_path):
    (inputs['root']/'site/stocks/EXM.html').unlink()
    with pytest.raises(ValueError,match='dossier'):invoke(inputs)
    link=tmp_path/'alias';link.symlink_to(inputs['document_path'].parent,target_is_directory=True)
    inputs['document_path']=link/inputs['document_path'].name
    with pytest.raises(ValueError,match='symlink'):invoke(inputs)

def test_context_only_incumbent_extractor_and_bound_hash(inputs):
    p=inputs['root']/'data/market_state/latest.json';p.parent.mkdir(parents=True,exist_ok=True)
    h=dump(p,{'asof':'2026-10-22','score':44,'verdict':'MIXED'})
    row={'id':'market_state_score','artifact':'data/market_state/latest.json','sha256':h,'relevance':'Synthetic test of extractor binding, not production relevance approval.'}
    mutate(inputs,lambda q:q.update(first_party_context=[row]))
    r=invoke(inputs);assert r['validation_context']['facts'][-1]['tier']=='first_party'
    assert r['source_revisions']['artifact:data/market_state/latest.json']=='sha256:'+h
    mutate(inputs,lambda q:q['first_party_context'][0].update(id='invented_fact'))
    with pytest.raises(ValueError,match='measurement'):invoke(inputs)

def test_stable_source_identity_across_reviews_and_revisions(inputs):
    a=invoke(inputs);stage_dir=inputs['root']/'data/press/staging';stage_dir.mkdir(parents=True,exist_ok=True)
    dump(stage_dir/'earlier.json',{'id':'old','desk':'brief','sources':[a['source_ref']],'as_of':'2026-10-22'})
    # A harmless original-byte formatting revision is separately hash-bound.
    inputs['document_path'].write_text('<html>\n<body>'+BODY+'</body></html>');inputs['document_sha256']=digest(inputs['document_path'])
    mutate(inputs,lambda q:q.update(document_sha256=inputs['document_sha256']))
    mutate(inputs,lambda r:r.update(raw_sha256=inputs['document_sha256'],bytes=inputs['document_path'].stat().st_size),'retrieval')
    b=invoke(inputs);assert b['source_ref']==a['source_ref'] and b['candidate_id']!=a['candidate_id']
    assert b['blocked_by_existing_coverage']
    assert S._slot_id(a)==S._slot_id(b)

@pytest.mark.parametrize('item',[{'sources':['issuer_sec:accession:document']},{'slot':{'seed_refs':['issuer_sec:accession:document']}},{'provenance':{'admission_receipt':{'rail':'private_issuer_release'}}},{'id':'press-issuer-abc'}])
def test_public_emit_guard_survives_provenance_strip(item):
    assert R._is_private_official_stage(item)

def test_unknown_external_source_kind_refuses(inputs):
    with pytest.raises(ValueError):P.plan_external_candidate(source_kind='arbitrary_url',**inputs)

def _reviewed_numeric_context(inputs):
    """Synthetic availability control ONLY, not NEE/editorial context approval."""
    p=inputs['root']/'data/market_state/latest.json';p.parent.mkdir(parents=True,exist_ok=True)
    payload={'asof':'2026-10-22','score':44,'verdict':'MIXED','components':[{'key':'trend','score':48,'weight':0.24},{'key':'risk','score':14,'weight':0.18},{'key':'breadth','score':35,'weight':0.16}]}
    h=dump(p,payload)
    rows=[{'id':fid,'artifact':'data/market_state/latest.json','sha256':h,'relevance':'Offline synthetic availability test only; does not qualify live relevance.'} for fid in ['market_state_score','market_state_trend','market_state_risk','market_state_breadth']]
    mutate(inputs,lambda q:q.update(first_party_context=rows))

def test_staging_reuses_exclusive_checkpoint_single_adapter_no_regeneration(inputs,monkeypatch):
    _reviewed_numeric_context(inputs);calls=[]
    ledger=inputs['root']/'data/press/published.jsonl'; ledger_before=ledger.read_bytes()
    def fail(slot,cfg,**kwargs):
        path=inputs['root']/'data/press/staging'/f"{slot['id']}.json"
        record=json.loads(path.read_text())
        assert record['provenance']['admission_receipt']['rail']=='private_issuer_release'
        calls.append(kwargs)
        return {'ok':False,'draft':None,'reason':'offline stub failure','provider':None,'state':kwargs['state'].snapshot()}
    monkeypatch.setattr(S.writer,'write',fail)
    a=stage(inputs);assert a['staged'] and len(calls)==1 and calls[0]['single_provider_attempt'] is True
    b=stage(inputs);assert not b['staged'] and len(calls)==1
    assert ledger.read_bytes()==ledger_before
    record=json.loads((inputs['root']/'data/press/staging'/f"{a['staged_slot_id']}.json").read_text())
    assert R._is_private_official_stage(record)
    record.pop('provenance');assert R._is_private_official_stage(record)

def test_cadence_includes_quarantined_and_pending_before_effect(inputs,monkeypatch):
    _reviewed_numeric_context(inputs);directory=inputs['root']/'data/press/staging';directory.mkdir(parents=True,exist_ok=True)
    for i,status in enumerate(['quarantined','in_progress']):
        dump(directory/f'{i}.json',{'id':f'other-{i}','desk':'brief','as_of':'2026-10-23','status':status,'sources':['other:'+str(i)]})
    monkeypatch.setattr(S,'_stage_preplanned_slots',lambda *a,**k:pytest.fail('cadence refusal before effect'))
    assert 'cadence' in stage(inputs)['reason']

def test_cli_requires_private_invocation_and_has_no_backdate(inputs):
    with pytest.raises(SystemExit):S.main(['--help'])
    args=[]
    for name in ['document','qualification','retrieval']:
        args.extend(['--'+name,str(inputs[name+'_path']),'--'+name+'-sha256',inputs[name+'_sha256']])
    with pytest.raises(SystemExit):S.main(args)
    with pytest.raises(SystemExit):S.main(args+['--confirm-private-staging','--as-of','2026-10-21'])

@pytest.mark.parametrize('clock',['2026-10-21T11:31:00Z','2026-10-21T07:30:00Z','2026-10-21T11:30:00+01:00','2026-10-21T07:30:00-05:00'])
def test_declared_availability_rejects_wrong_same_day_time_or_offset(inputs,clock):
    mutate(inputs,lambda q:q.update(declared_available_at=clock))
    with pytest.raises(ValueError,match='literal time/timezone'):invoke(inputs)

def test_declared_availability_accepts_equivalent_eastern_instant_and_null_unknown(inputs):
    mutate(inputs,lambda q:q.update(declared_available_at='2026-10-21T07:30:00-04:00'))
    assert invoke(inputs)['source_clocks']['declared_available_at']=='2026-10-21T11:30:00+00:00'
    mutate(inputs,lambda q:q.update(declared_available_at=None,availability_literal=None))
    clocks=invoke(inputs)['source_clocks']
    assert clocks['declared_available_at'] is None and clocks['observed_at']=='2026-10-23T12:00:00+00:00'

def test_declared_availability_does_not_assume_unknown_source_timezone(inputs):
    # A separately bound original may use another zone. This narrow form must
    # refuse an invented precision rather than silently interpreting it as ET.
    text=inputs['document_path'].read_text().replace('a.m. ET today','a.m. UTC today')
    inputs['document_path'].write_text(text);inputs['document_sha256']=digest(inputs['document_path'])
    altered=BODY.replace('a.m. ET today','a.m. UTC today')
    mutate(inputs,lambda q:q.update(document_sha256=inputs['document_sha256'],body_sha256=hashlib.sha256(altered.encode()).hexdigest(),availability_literal='beginning at 7:30 a.m. UTC today'))
    mutate(inputs,lambda r:r.update(raw_sha256=inputs['document_sha256'],bytes=inputs['document_path'].stat().st_size),'retrieval')
    with pytest.raises(ValueError,match='unsupported declared availability time/timezone'):invoke(inputs)

@pytest.mark.parametrize('release_date,date_literal,time_literal,declared,observed,as_of',[
 ('2026-11-01','Nov. 01, 2026','beginning at 1:30 a.m. ET today','2026-11-01T05:30:00Z','2026-11-02T12:00:00Z','2026-11-02T13:00:00Z'),
 ('2026-03-08','Mar. 08, 2026','beginning at 2:30 a.m. ET today','2026-03-08T07:30:00Z','2026-03-09T12:00:00Z','2026-03-09T13:00:00Z'),
])
def test_declared_availability_refuses_dst_fold_and_gap(inputs,release_date,date_literal,time_literal,declared,observed,as_of):
    body=BODY.replace('Oct. 21, 2026',date_literal).replace('beginning at 7:30 a.m. ET today',time_literal)
    # Keep the fictional fiscal period earlier than either release date.
    body=body.replace('September 30, 2026','September 30, 2025')
    inputs['document_path'].write_text('<html><body>'+body+'</body></html>')
    inputs['document_sha256']=digest(inputs['document_path']);inputs['as_of']=as_of
    def change(q):
        q.update(document_sha256=inputs['document_sha256'],body_sha256=hashlib.sha256(body.encode()).hexdigest(),release_date=release_date,release_date_literal=date_literal,declared_available_at=declared,availability_literal=time_literal,fiscal_period_literal='three months ended September 30, 2025')
        q['reviewed_claims'][0]['literal']=q['reviewed_claims'][0]['literal'].replace('September 30, 2026','September 30, 2025')
    mutate(inputs,change)
    mutate(inputs,lambda r:r.update(raw_sha256=inputs['document_sha256'],bytes=inputs['document_path'].stat().st_size,observed_at=observed),'retrieval')
    with pytest.raises(ValueError,match='ambiguous or nonexistent declared availability'):invoke(inputs)

def test_exported_normalizer_binds_inline_html_not_browser_transcription(inputs):
    from engine.press.issuer_release_candidate import normalized_issuer_body
    html=inputs['document_path'].read_text().replace('36.7 GW','<b>36.7 GW</b>').replace('3.7 GW','<i>3.7 GW</i>')
    inputs['document_path'].write_text(html);inputs['document_sha256']=digest(inputs['document_path'])
    body,bh=normalized_issuer_body(html)
    assert '36.7 GW , including' in body and body!=BODY
    def change(q):
        q.update(document_sha256=inputs['document_sha256'],body_sha256=bh)
        q['reviewed_claims'][1]['literal']='Backlog was 36.7 GW , including new origination of 3.7 GW .'
    mutate(inputs,change)
    mutate(inputs,lambda r:r.update(raw_sha256=inputs['document_sha256'],bytes=inputs['document_path'].stat().st_size),'retrieval')
    r=invoke(inputs)
    assert r['body_sha256']==bh and r['document_sha256']!=bh
    assert r['validation_context']['raw_documents'][0]['text']==body
    mutate(inputs,lambda q:q['reviewed_claims'][1].update(literal='Backlog was 36.7 GW, including new origination of 3.7 GW.'))
    with pytest.raises(ValueError,match='literal'):invoke(inputs)

@pytest.mark.parametrize('key,value',[('source_url',123),('release_date',False)])
def test_malformed_source_types_are_named_value_refusals(inputs,key,value):
    mutate(inputs,lambda q:q.update({key:value}))
    with pytest.raises(ValueError,match='identity and dates'):invoke(inputs)

def test_missing_observed_clock_is_named_value_refusal(inputs):
    mutate(inputs,lambda r:r.pop('observed_at'),'retrieval')
    with pytest.raises(ValueError,match='observed_at requires'):invoke(inputs)

def _cli_args(inputs):
    args=['--root',str(inputs['root']),'--confirm-private-staging']
    for name in ('document','qualification','retrieval'):
        args.extend(['--'+name,str(inputs[name+'_path']),'--'+name+'-sha256',inputs[name+'_sha256']])
    return args

def test_cli_hash_and_missing_config_refusals_are_structured(inputs,capsys):
    inputs['document_sha256']='0'*64
    assert S.main(_cli_args(inputs))==1
    out=capsys.readouterr().out;result=json.loads(out[out.index('{'):])
    assert result['staged'] is False and 'hash mismatch' in result['reason']
    (inputs['root']/'config/press.yml').unlink()
    assert S.main(_cli_args(inputs))==1
    out=capsys.readouterr().out;assert 'config/press.yml' in json.loads(out[out.index('{'):])['reason']

def test_cli_atomic_collision_retains_original_operation(inputs,monkeypatch,capsys):
    monkeypatch.setattr(S,'stage_issuer_release_candidate',lambda *a,**k:(_ for _ in ()).throw(FileExistsError()))
    assert S.main(_cli_args(inputs))==1
    out=capsys.readouterr().out
    assert 'reconcile original operation, never replay' in json.loads(out[out.index('{'):])['reason']

def test_issuer_refusal_annotations_name_the_issuer_rail(inputs,capsys):
    assert not stage(inputs)['staged']
    assert 'press_issuer_stage_refused' in capsys.readouterr().out

def test_direct_script_help_bootstraps_repo_path():
    import subprocess,sys
    result=subprocess.run([sys.executable,str(Path(S.__file__)),'--help'],capture_output=True,text=True)
    assert result.returncode==0 and '--confirm-private-staging' in result.stdout

def test_cli_post_checkpoint_valueerror_preserves_unknown_original_identity(inputs,monkeypatch,capsys):
    _reviewed_numeric_context(inputs);calls=[]
    real_stage=S.stage_issuer_release_candidate
    def fixed_stage(root,cfg,**kwargs):
        return real_stage(root,cfg,now=datetime(2026,10,23,13,tzinfo=timezone.utc),**kwargs)
    monkeypatch.setattr(S,'stage_issuer_release_candidate',fixed_stage)
    identity=S._slot_id(invoke(inputs));checkpoint=inputs['root']/'data/press/staging'/f'{identity}.json'
    def uncertain(slot,cfg,**kwargs):
        assert checkpoint.exists()
        assert json.loads(checkpoint.read_text())['progress']['phase']=='provider_started'
        calls.append(slot['id'])
        raise ValueError('offline post-checkpoint transport ambiguity')
    monkeypatch.setattr(S.writer,'write',uncertain)
    assert S.main(_cli_args(inputs))==1
    text=capsys.readouterr().out;out=json.loads(text[text.index('{'):])
    assert out['effect_unknown'] is True
    assert out['original_slot_id']==identity and out['retry_allowed'] is False
    assert 'press_issuer_effect_unknown' in text and 'press_issuer_stage_refused' not in text
    record=json.loads(checkpoint.read_text())
    assert record['status']=='in_progress' and record['progress']['phase']=='provider_started'
    assert calls==[identity]
    assert S.main(_cli_args(inputs))==1
    assert calls==[identity]  # Duplicate/source guard retains the same operation.

# Synthetic retained-input boundary regression: no real SEC retrieval or emission.
@pytest.mark.parametrize('field', ['claim', 'source qualifier'])
@pytest.mark.parametrize('quantity_literals', [[], ['1']])
def test_grouped_amount_does_not_anchor_truncated_reviewed_span(inputs, field, quantity_literals):
    from engine.press.issuer_release_candidate import normalized_issuer_body
    original = inputs['document_path'].read_text()
    altered = original.replace('Backlog was 36.7 GW', 'Revenue was $1,000. Backlog was 36.7 GW')
    inputs['document_path'].write_text(altered)
    inputs['document_sha256'] = digest(inputs['document_path'])
    body, body_hash = normalized_issuer_body(altered)
    def change(q):
        q.update(document_sha256=inputs['document_sha256'], body_sha256=body_hash)
        if field == 'claim':
            q['reviewed_claims'][1] = {'id': 'revenue', 'literal': 'Revenue was $1', 'quantity_literals': quantity_literals}
        else:
            q['source_qualifiers'][1] = 'Revenue was $1'
    mutate(inputs, change)
    mutate(inputs, lambda r: r.update(raw_sha256=inputs['document_sha256'],
                                      bytes=inputs['document_path'].stat().st_size), 'retrieval')
    assert not any(json.loads(inputs['qualification_path'].read_text())[k]
                   for k in ('allow_stage', 'allow_emit', 'publication_approved'))
    with pytest.raises(ValueError, match='literal source span|whole source atom'):
        invoke(inputs)


@pytest.mark.parametrize('source,literal,allowed', [
    ('Revenue was $1,000', 'Revenue was $1', False),
    ('Revenue was $1,000', 'Revenue was $1,000', True),
    ('Revenue was 1.25', 'Revenue was 1.2', False),
    ('Revenue was $1.25', 'Revenue was $1.25', True),
    ('Revenue was 1.25%', 'Revenue was 1.25', False),
    ('Revenue was 1.25%', 'Revenue was 1.25%', True),
    ('Revenue was $1.00', 'Revenue was $1', False),
    ('Items 1, 2, and 3', 'Items 1, 2', True),
    ('Revenue was $1,000. Revenue was $1', 'Revenue was $1', True),
    ('Revenue was -1,000', 'Revenue was -1', False),
    ('Revenue was -1,000', 'Revenue was -1,000', True),
])
def test_reviewed_span_numeric_boundaries(source, literal, allowed):
    from engine.press.issuer_release_candidate import _whole_numeric_occurrence
    assert _whole_numeric_occurrence(literal, source) is allowed


@pytest.mark.parametrize('source,atom,allowed', [
    ('Revenue was 1,000', '1', False),
    ('Revenue was 1,000 and 1', '1', True),
    ('Revenue was 1.25', '1', False),
    ('Revenue was 1.25', '1.25', True),
    ('Revenue was 1.25%', '1.25', False),
    ('Revenue was 1,000', '1000', False),
])
def test_explicit_numeric_atom_boundaries(source, atom, allowed):
    from engine.press.issuer_release_candidate import _whole_numeric_occurrence
    assert _whole_numeric_occurrence(atom, source) is allowed

def test_complete_grouped_amount_reaches_real_fact_anchor_offline(inputs):
    from engine.press.issuer_release_candidate import normalized_issuer_body
    original = inputs['document_path'].read_text()
    altered = original.replace('Backlog was 36.7 GW', 'Revenue was $1,000. Backlog was 36.7 GW')
    inputs['document_path'].write_text(altered)
    inputs['document_sha256'] = digest(inputs['document_path'])
    _, body_hash = normalized_issuer_body(altered)
    def change(q):
        q.update(document_sha256=inputs['document_sha256'], body_sha256=body_hash)
        q['reviewed_claims'][1] = {'id': 'revenue', 'literal': 'Revenue was $1,000', 'quantity_literals': []}
    mutate(inputs, change)
    mutate(inputs, lambda r: r.update(raw_sha256=inputs['document_sha256'],
                                      bytes=inputs['document_path'].stat().st_size), 'retrieval')
    plan = invoke(inputs)
    assert plan['allow_emit'] is False and plan['publication_approved'] is False
    assert V.check_fact_anchor({'body_html': '<p>Revenue was $1,000.</p>'},
                               plan['validation_context'], P.load_config(inputs['root']))['ok']

@pytest.mark.parametrize('field', ['claim', 'source qualifier'])
@pytest.mark.parametrize('source, reviewed', [
    ('Revenue was $1M', 'Revenue was $1'),
    ('Revenue was $1million', 'Revenue was $1'),
    ('Revenue was $1,000USD', 'Revenue was $1,000'),
    ('Revenue was $1.25B', 'Revenue was $1.25'),
])
def test_attached_numeric_suffix_cannot_validate_truncated_issuer_span(inputs, field, source, reviewed):
    from engine.press.issuer_release_candidate import normalized_issuer_body
    original = inputs['document_path'].read_text()
    altered = original.replace('Backlog was 36.7 GW', source + '. Backlog was 36.7 GW')
    inputs['document_path'].write_text(altered)
    inputs['document_sha256'] = digest(inputs['document_path'])
    _, body_hash = normalized_issuer_body(altered)
    def change(q):
        q.update(document_sha256=inputs['document_sha256'], body_sha256=body_hash)
        if field == 'claim':
            q['reviewed_claims'][1] = {'id': 'revenue', 'literal': reviewed, 'quantity_literals': []}
        else:
            q['source_qualifiers'][1] = reviewed
    mutate(inputs, change)
    mutate(inputs, lambda r: r.update(raw_sha256=inputs['document_sha256'],
                                      bytes=inputs['document_path'].stat().st_size), 'retrieval')
    with pytest.raises(ValueError, match='literal source span'):
        invoke(inputs)


@pytest.mark.parametrize('source, reviewed, expected', [
    ('Revenue was $1M', 'Revenue was $1', False),
    ('Revenue was $1M', 'Revenue was $1M', True),
    ('Revenue was $1million', 'Revenue was $1', False),
    ('Revenue was $1,000USD', 'Revenue was $1,000', False),
    ('Revenue was $1.25B', 'Revenue was $1.25', False),
    ('FY1 earnings were up', '1', False),
    ('FY1 earnings were up', 'FY1 earnings', True),
])
def test_numeric_word_edge_occurrence_boundaries(source, reviewed, expected):
    from engine.press.issuer_release_candidate import _whole_numeric_occurrence
    assert _whole_numeric_occurrence(reviewed, source) is expected
