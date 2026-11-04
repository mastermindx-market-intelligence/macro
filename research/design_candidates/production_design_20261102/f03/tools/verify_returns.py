#!/usr/bin/env python3
"""Bounded return-observation checks; not browser, review or Paper acceptance."""
from __future__ import annotations
import argparse, copy, hashlib, importlib.util, json, re
from pathlib import Path

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
    check('36 unique assignments; exactly eight observed returns',len(sessions)==len({s['id'] for s in sessions})==36 and set(returns)=={'F01','F02','D07','D08','D08A','D08B','D08C','D08D'})
    for s in sessions:
        retained={k:v for k,v in s.items() if k not in builder.RETURN_FIELDS}
        digest=hashlib.sha256(json.dumps(retained,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        check('retained assignment fields '+s['id'],digest==baseline['assignment_retained_field_sha256'][s['id']])
    by_id={s['id']:s for s in sessions}
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
    check('source law continuation separated from original pin',meta['procedure_sha']=='c57adacb338fe837c7d585f1e372c64d9b0118ec' and meta['continuation_procedure_sha']=='910803421beca53ca25145392725ab2d84c7a8e9')
    check('native operation IDs unique; no unknown F03 effects',len(native['operations'])==len({x['operation_id'] for x in native['operations']}) and native['unresolved_effects']==[])
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
    proposed=copy.deepcopy(sessions); late_bad=copy.deepcopy(curated)
    late_bad['assignment_returns']['F01']['status']='SENTINEL: must not partially apply'
    late_bad['assignment_returns']['D08D']['source_contract']='javascript:late_failure'
    try: builder.apply_assignment_returns(proposed,late_bad)
    except AssertionError: check('invalid later row leaves all assignments unchanged',proposed==sessions)
    else: check('invalid later row leaves all assignments unchanged',False)
    print(json.dumps({'kind':'bounded_return_refresh_identity_and_source_checks_not_acceptance','status':'PASS','check_count':len(checks),'checks':checks,'limitations':['Original 399-input suite is historical, not rerun here.','Native visual observation, browser interaction, hosted CI and formal RIG are separate.']},indent=2))

if __name__=='__main__':main()
