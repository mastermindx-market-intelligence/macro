#!/usr/bin/env python3
"""Bounded return-observation checks; not browser, review or Paper acceptance."""
from __future__ import annotations
import argparse, copy, hashlib, importlib.util, json, re
from pathlib import Path
from unittest.mock import patch

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('root',nargs='?',type=Path,default=Path('.')); args=ap.parse_args()
    root=args.root; read=lambda p:json.loads((root/p).read_text()); checks=[]
    def check(name,condition):
        assert condition,name
        checks.append({'name':name,'result':'PASS'})
    spec=importlib.util.spec_from_file_location('f03_builder',root/'tools/build_directory.py')
    builder=importlib.util.module_from_spec(spec); spec.loader.exec_module(builder)
    baseline=read('evidence/return-refresh-baseline.json')
    for path,expected in baseline['frozen_files'].items():
        b=(root/path).read_bytes()
        check('frozen bytes '+path,hashlib.sha256(b).hexdigest()==expected['sha256'] and builder.git_blob(b)==expected['git_blob_sha'])
    sessions=read('data/assignment-directory.json'); curated=read('tools/curation.json'); returns=curated['assignment_returns']
    check('root and tool-local curation mirrors agree',curated==read('curation.json'))
    check('36 unique assignments; exactly twelve observed returns',len(sessions)==len({s['id'] for s in sessions})==36 and set(returns)=={'F01','F02','D04','D05','D06','D07','D08','D08A','D08B','D08C','D08D','D14'})
    prior=read('evidence/proposal-reference-baseline-20261108.json')['prior_assignment_return_sha256']
    check('prior return baseline covers exactly the nine published observations',set(prior)=={'F01','F02','D05','D07','D08','D08A','D08B','D08C','D08D'})
    for sid,expected in prior.items():
        digest=hashlib.sha256(json.dumps(returns[sid],ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        check('previous return preserved exactly '+sid,digest==expected)
    for s in sessions:
        retained={k:v for k,v in s.items() if k not in builder.RETURN_FIELDS}
        digest=hashlib.sha256(json.dumps(retained,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        check('retained assignment fields '+s['id'],digest==baseline['assignment_retained_field_sha256'][s['id']])
    by_id={s['id']:s for s in sessions}
    d05=returns['D05']; obs=d05['return_observation']; sector='01M6FAXA774QT1VRDMAG7DFQ2W'
    note='evidence/d05-sector-reference-observation-20261108.md'
    check('D05 immutable observation source matches the published note',obs['source_head']=='235d60d912589e630988b67eee6ba63be37c5712' and obs['source_blob_sha']==builder.git_blob((root/note).read_bytes()) and d05['source_contract']=='https://github.com/mastermindx-market-intelligence/macro/blob/'+obs['source_head']+'/research/design_candidates/production_design_20261102/f03/'+note)
    check('D05 proposed candidate and current Read me have separate exact identities',(obs['candidate_file_id'],obs['candidate_page_id'])==(sector,'p-6-0') and (obs['readme_file_id'],obs['readme_page_id'],obs['readme_board_id'])==(sector,'p-3-0','BML-0'))
    check('D05 retained reference remains separate from both current destinations',obs['retained_reference_url']=='https://app.paper.design/file/'+sector+'/p-1-0' and len({d05['candidate_ref'],obs['readme_url'],obs['retained_reference_url']})==3)
    check('D05 observation does not invent PR or foundation qualification',obs['observed_pr_head'] is None and d05['shell_version'] is None and d05['system_version'] is None and 'proposal' in d05['status'] and 'acceptance held' in d05['status'])
    check('curation mirrors have identical bytes',(root/'curation.json').read_bytes()==(root/'tools/curation.json').read_bytes())
    check('D05 candidate board belongs to its candidate observation, not Read me',obs.get('candidate_board_id')=='GPL-0' and obs['readme_board_id']=='BML-0')
    check('D05 Markdown renders exact candidate tuple and page-navigation limit',sector+' / p-6-0 / GPL-0' in (root/'assignments/D05.md').read_text() and 'exact board URL is not verified' in (root/'assignments/D05.md').read_text())
    terminal='01M3NSZGE8JWN2EZCSF0DT05RM'; ai='01M3P1QEHS5XXQY85BJT6QR2E1'
    proposals=[
        ('D04',terminal,'p-1D-0','22UK-0',(terminal,'p-8-1','N71-1'),'d04-heatmap-reference-observation-20261108.md','7571ddf1529551f9ce69a6107d7a41bcb9bd2666'),
        ('D14',ai,'p-B-0','72Y-0',(ai,'p-9-0','1MO-0'),'d14-context-reference-observation-20261108.md','8bdae0284375609a6a82540bd993ba55f3ff6d99'),
        ('D06',terminal,'p-1E-0','23MJ-0',(None,None,None),'d06-reader-reference-observation-20261108.md','3ab49418d91b891441ba65a901a3fa71d2f9c1d1')]
    for sid,file,page,board,entry,note,blob in proposals:
        row=returns[sid]; obs=row['return_observation']; md=(root/'assignments'/(sid+'.md')).read_text()
        head='6324c7281ec91a343c5a8c78b3679f93b1cd11e6'
        source='https://github.com/mastermindx-market-intelligence/macro/blob/'+head+'/research/design_candidates/production_design_20261102/f03/evidence/'+note
        check('published proposal note and actual blob '+sid,obs['source_head']==head and obs['source_blob_sha']==blob==builder.git_blob((root/'evidence'/note).read_bytes()) and row['source_contract']==source and source in obs['evidence_urls'])
        check('proposal candidate and entry have exact distinct roles '+sid,(obs['candidate_file_id'],obs['candidate_page_id'],obs['candidate_board_id'])==(file,page,board) and (obs['readme_file_id'],obs['readme_page_id'],obs['readme_board_id'])==entry and obs['readme_url']==('https://app.paper.design/file/'+entry[0]+'/'+entry[1] if entry[0] else None) and obs['retained_reference_url'] is None)
        check('proposal remains bounded and unqualified '+sid,obs['observed_at_utc']=='2026-11-08T18:25:46Z' and obs['observed_pr_head'] is None and row['shell_version'] is None and row['system_version'] is None and 'unqualified' in row['status'] and 'does not establish a complete domain return' in obs['qualification'])
        check('proposal Markdown includes exact candidate and qualification '+sid,file+' / '+page+' / '+board in md and 'exact board URL is not verified' in md and obs['qualification'] in md and row['status'] in md)
    for sid,row in returns.items():
        check('curated return rendered '+sid,all(by_id[sid][k]==v for k,v in row.items()))
        obs=row['return_observation']
        check('immutable source and null approval '+sid,bool(re.fullmatch('[0-9a-f]{40}',obs['source_head'])) and '/blob/'+obs['source_head']+'/' in row['source_contract'] and row['rig_receipt'] is None and row['rig_state']=='draft')
        md=(root/'assignments'/(sid+'.md')).read_text()
        check('Markdown direct return '+sid,row['source_contract'] in md and obs['source_head'] in md and 'No approved candidate established' in md)
    for sid in ('D08A','D08D','D08'):
        check('no native candidate fabricated '+sid,by_id[sid]['candidate_ref'] is None and by_id[sid]['return_observation']['candidate_file_id'] is None)
    routes=read('data/route-assignment-projection.json'); deltas=read('data/source-delta-projection.json'); ledger=read('data/resource-action-ledger.json')
    check('348 exact unique route identities retained',len(routes)==len({r['canonical_registry_id'] for r in routes})==348)
    check('nine source deltas remain noncanonical',len(deltas)==9 and all(d['canonical_registry_id'] is None for d in deltas))
    check('all 301 resource effects remain undispatched',len(ledger)==301 and all(x['effect_status']=='NOT_DISPATCHED' and not x['applied'] and x['admission_receipt'] is None and x['readback'] is None for x in ledger))
    html=(root/'directory.html').read_text()
    embedded=json.loads(re.search(r'<script id="f03-data" type="application/json">([\s\S]*?)</script>',html)[1])
    check('HTML and assignment JSON share exact returns',embedded['sessions']==sessions)
    native=read('paper/native-progress.json'); meta=read('data/provenance.json')
    check('current effects derived from original native log',meta['directory']['paper_mutations']==sum(x['state']=='APPLIED_RESPONSE_OBSERVED' for x in native['operations']))
    check('source law continuation separated from original and prior pins',meta['procedure_sha']=='c57adacb338fe837c7d585f1e372c64d9b0118ec' and meta['continuation_procedure_sha']=='8eb375fe081339be759888f74a7c93d855727190' and native['previous_continuation_protected_procedure']=='86a454807bc48540d98e07ece3da454f7b2341cf')
    check('native operation IDs unique',len(native['operations'])==len({x['operation_id'] for x in native['operations']}))
    unresolved=[x['operation_id'] for x in native['operations'] if x['state']=='EFFECT_UNKNOWN']
    check('unknown effects exactly match original ledger and projection',set(unresolved)=={x['operation_id'] for x in native['unresolved_effects']} and meta['directory']['paper_unresolved_operation_ids']==unresolved and meta['directory']['paper_unresolved_effects']==len(unresolved))
    check('unknown effects are not counted as applied or hidden in aggregate state',not unresolved or meta['paper_application']=='PARTIAL_NATIVE_EFFECT_UNKNOWN__RESOURCE_ACTIONS_NOT_DISPATCHED')
    check('embedded metadata agrees with original current-effect projection',embedded['metadata']==meta)
    def rejects(name,alter):
        bad=copy.deepcopy(curated); alter(bad)
        try: builder.apply_assignment_returns(copy.deepcopy(sessions),bad)
        except (AssertionError,KeyError,TypeError): check(name,True)
        else: check(name,False)
    rejects('unknown assignment rejected',lambda c:c['assignment_returns'].update({'NEW_OWNER':copy.deepcopy(c['assignment_returns']['D08B'])}))
    rejects('canonical ownership mutation rejected',lambda c:c['assignment_returns']['D08B'].update({'canonical_registry_ids':['invented']}))
    rejects('source pin mismatch rejected',lambda c:c['assignment_returns']['D08B']['return_observation'].update({'source_head':'0'*40}))
    rejects('native candidate identity mismatch rejected',lambda c:c['assignment_returns']['D08B'].update({'candidate_ref':'https://app.paper.design/file/WRONG/p-1-0'}))
    rejects('approval promotion rejected',lambda c:c['assignment_returns']['D08B'].update({'rig_receipt':'invented','rig_state':'approved'}))
    rejects('unsafe source URL rejected',lambda c:c['assignment_returns']['D08B'].update({'source_contract':'javascript:alert(1)'}))
    def incomplete_candidate(c):
        row=c['assignment_returns']['D08B']; row.pop('candidate_ref')
        row['return_observation']['candidate_file_id']=None; row['return_observation']['candidate_page_id']=None
    rejects('incomplete explicit return rejected',incomplete_candidate)
    rejects('omitted prior return rejected',lambda c:c['assignment_returns'].pop('D08B'))
    rejects('dot-segment source escape rejected',lambda c:c['assignment_returns']['D08B'].update({'source_contract':'https://github.com/mastermindx-market-intelligence/macro/blob/'+c['assignment_returns']['D08B']['return_observation']['source_head']+'/../../blob/main/README.md'}))
    rejects('Read me compound identity mismatch rejected',lambda c:c['assignment_returns']['D08B']['return_observation'].update({'readme_page_id':'p-12-0'}))
    rejects('current Read me cannot masquerade as original',lambda c:c['assignment_returns']['D08B']['return_observation'].update({'retained_reference_url':c['assignment_returns']['D08B']['return_observation']['readme_url']}))
    for value in ('',' ','GPL-0\n','GPL/0','GPL_0','../GPL-0','GPL-0#x','<b>GPL-0</b>','`GPL-0`',0,True,[],{}):
        rejects('invalid candidate board rejected '+repr(value),lambda c,v=value:c['assignment_returns']['D05']['return_observation'].update({'candidate_board_id':v}))
    def missing_candidate(c):
        row=c['assignment_returns']['D05']; row['candidate_ref']=None
        row['return_observation'].update({'candidate_file_id':None,'candidate_page_id':None})
    rejects('candidate board requires its own candidate page',missing_candidate)
    rejects('candidate board cannot use a mismatched page tuple',lambda c:c['assignment_returns']['D05']['return_observation'].update({'candidate_page_id':'p-3-0'}))
    rejects('candidate board requires a canonical page URL',lambda c:c['assignment_returns']['D05'].update({'candidate_ref':c['assignment_returns']['D05']['candidate_ref']+'\n'}))
    legacy=copy.deepcopy(curated); legacy['assignment_returns']['D05']['return_observation'].pop('candidate_board_id')
    explicit_null=copy.deepcopy(legacy); explicit_null['assignment_returns']['D05']['return_observation']['candidate_board_id']=None
    missing=builder.apply_assignment_returns(copy.deepcopy(sessions),legacy)
    null=builder.apply_assignment_returns(copy.deepcopy(sessions),explicit_null)
    check('missing and null candidate board preserve legacy Markdown',builder.builder_entry(next(s for s in missing if s['id']=='D05'))==builder.builder_entry(next(s for s in null if s['id']=='D05')))
    untouched=copy.deepcopy(sessions); late_board=copy.deepcopy(curated)
    late_board['assignment_returns']['F01']['status']='SENTINEL: must not partially apply'
    late_board['assignment_returns']['D05']['return_observation']['candidate_board_id']='GPL-0/invalid'
    try: builder.apply_assignment_returns(untouched,late_board)
    except AssertionError: check('invalid later candidate board leaves all assignments unchanged',untouched==sessions)
    else: check('invalid later candidate board leaves all assignments unchanged',False)
    proposed=copy.deepcopy(sessions); late_bad=copy.deepcopy(curated)
    late_bad['assignment_returns']['F01']['status']='SENTINEL: must not partially apply'
    late_bad['assignment_returns']['D08D']['source_contract']='javascript:late_failure'
    try: builder.apply_assignment_returns(proposed,late_bad)
    except AssertionError: check('invalid later row leaves all assignments unchanged',proposed==sessions)
    else: check('invalid later row leaves all assignments unchanged',False)
    def project_native_fixture(fixture):
        projected=copy.deepcopy(embedded)
        with patch.object(builder,'load',return_value=fixture):
            builder.observe_directory_progress(projected,root)
        return projected
    pending_fixture=copy.deepcopy(native)
    if not pending_fixture['unresolved_effects']:
        synthetic={'operation_id':'synthetic-unknown-effect','state':'EFFECT_UNKNOWN'}
        pending_fixture['operations'].append(synthetic)
        pending_fixture['unresolved_effects'].append(copy.deepcopy(synthetic))
    actual_unresolved_count=len(native['unresolved_effects'])
    def rejects_native(name,alter):
        fixture=copy.deepcopy(pending_fixture); alter(fixture)
        try: project_native_fixture(fixture)
        except AssertionError: check(name,True)
        else: check(name,False)
    rejects_native('missing unresolved receipt fails projection',lambda n:n.update({'unresolved_effects':[]}))
    rejects_native('orphan unresolved receipt fails projection',lambda n:n['unresolved_effects'].append({'operation_id':'synthetic-orphan'}))
    rejects_native('duplicate operation ID fails projection',lambda n:n['operations'].append(copy.deepcopy(n['operations'][0])))
    rejects_native('duplicate unresolved receipt fails projection',lambda n:n['unresolved_effects'].append(copy.deepcopy(n['unresolved_effects'][0])))
    resolved_fixture=copy.deepcopy(pending_fixture)
    for op in resolved_fixture['operations']:
        if op['state']=='EFFECT_UNKNOWN': op['state']='APPLIED_RESPONSE_OBSERVED'
    resolved_fixture['unresolved_effects']=[]
    resolved=project_native_fixture(resolved_fixture)['metadata']
    check('synthetic resolved fixture clears stale unknown projection without changing actual ledger',resolved['directory']['paper_unresolved_operation_ids']==[] and resolved['directory']['paper_unresolved_effects']==0 and resolved['paper_application']=='DIRECTORY_EDITS_OBSERVED__RESOURCE_ACTIONS_NOT_DISPATCHED' and len(native['unresolved_effects'])==actual_unresolved_count)
    print(json.dumps({'kind':'bounded_return_refresh_identity_and_source_checks_not_acceptance','status':'PASS','check_count':len(checks),'checks':checks,'limitations':['Original 399-input suite is historical, not rerun here.','Native-effect reconciliation fixtures are synthetic; no actual Paper effect is resolved by a test.','Native visual observation, browser interaction, hosted CI and formal RIG are separate.']},indent=2))

if __name__=='__main__':main()
