#!/usr/bin/env python3
"""Verify a prepared Prophet Fable handoff. No network or product/runtime imports.

This validates document content, hashes and routing/ownership invariants only.
It does not run the listed production acceptance cases or register any study.
"""
from __future__ import annotations
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import sys
import zipfile

ROOT = Path(__file__).resolve().parent
EXPECTED_R5_ZIP_SHA256 = 'ded2d954327f30ade2430689d11e715c1d1cf292e45e6347c3752d7865025635'

class PacketError(ValueError):
    pass

class Checks:
    def __init__(self) -> None:
        self.count = 0
    def require(self, ok: bool, message: str) -> None:
        self.count += 1
        if not ok:
            raise PacketError(message)

def load(path: str) -> dict:
    with (ROOT / path).open(encoding='utf-8') as handle:
        return json.load(handle)

def snapshot() -> dict:
    return {
        'policy': load('EXTERNAL_FABRIC_POLICY.json'),
        'status': load('HANDOFF_STATUS.json'),
        'authority': load('AUTHORITY_DELEGATION.json'),
        'build': load('effective/BUILD_PROGRAM.json'),
        'research': load('effective/RESEARCH_DOCKET.json'),
        'decisions': load('effective/DECISION_REGISTER.json'),
        'requirements': load('effective/REQUIREMENT_CROSSWALK.json'),
        'acceptance': load('effective/ACCEPTANCE_CATALOG.json'),
        'handoff_cases': load('R6_HANDOFF_ACCEPTANCE.json'),
        'gates': load('effective/ACTIVATION_GATES.json'),
    }

def validate(c: dict, ck: Checks) -> None:
    p=c['policy'];s=c['status'];a=c['authority']
    ck.require(p['delegated_execution']=='EXTERNAL_FABRIC_ONLY','external-only delegation changed')
    for field in ['built_in_subagents_allowed','internal_codex_fallback_allowed','nested_builtin_delegation_allowed','requires_astra','fable_default_implementer']:
        ck.require(p[field] is False, 'prohibited routing/authority: '+field)
    ck.require(a['external_fabric_only'] is True,'delegation does not retain external restriction')
    ck.require(a['requires_astra'] is False,'Astra approval dependency reintroduced')
    ck.require(s['actual_receiver'] is None,'preparation falsely names a receiver')
    for field in ['pickup_ack','started','repository_source_changes','trials_registered','models_trained','mission_complete','requires_astra']:
        ck.require(s[field] is False,'preparation falsely advances '+field)
    ck.require(s['delivery']=='NOT_SENT_TO_CONCRETE_FABLE_SESSION','delivery status inflated')
    ck.require(s['product_acceptance_tests_run']==0,'product tests falsely claimed')
    ck.require(a['receiver_acknowledged'] is False and a['children_started']==0,'delegation confused with execution')
    ck.require(a['prepared_record_source_adopted'] is False,'source adoption falsely claimed')
    ck.require(all(v is True for v in a['program_decision_authority'].values()),'delegated program decision missing')
    builds=c['build']['units']; qs=c['research']['packets']; ds=c['decisions']['decisions']
    bid={x['id'] for x in builds};qid={x['id'] for x in qs};did={x['id'] for x in ds}
    ck.require(len(builds)==29 and bid=={f'B{i:02}' for i in range(29)},'build coverage changed')
    ck.require(len(qs)==24 and qid=={f'Q{i:02}' for i in range(1,25)},'research coverage changed')
    ck.require(len(ds)==12 and did=={f'D{i:02}' for i in range(1,13)},'decision coverage changed')
    for u in builds:
        ck.require(u['owner'].startswith('Fable Meta-CEO'),'non-Fable program dependency '+u['id'])
        ck.require(u['requires_astra'] is False,'Astra needed by '+u['id'])
        ck.require(u['execution_route']=='EXTERNAL_FABRIC_ONLY','wrong build route '+u['id'])
        ck.require(u['status']=='SPECIFIED_NOT_DISPATCHED','build state overstated '+u['id'])
        ck.require(set(u['depends_on'])<=bid,'dangling build dependency '+u['id'])
        ck.require(set(u['research_packets'])<=qid,'dangling research dependency '+u['id'])
        ck.require(set(u['decision_ids'])<=did,'dangling decision dependency '+u['id'])
    for q in qs:
        ck.require(q['owner'].startswith('Fable Meta-CEO'),'non-Fable research owner '+q['id'])
        ck.require(q['requires_astra'] is False and q['execution_route']=='EXTERNAL_FABRIC_ONLY','wrong research route '+q['id'])
        ck.require(q['protected_outcomes_may_be_opened_by_this_packet'] is False,'study protection changed '+q['id'])
        ck.require(set(q['build_consumers'])<=bid,'unknown research consumer '+q['id'])
    for d in ds:
        ck.require(d['accountable_owner']=='Fable Meta-CEO' and d['requires_astra'] is False,'decision not delegated '+d['id'])
        ck.require(len(d['resolution_steps'])>=4 and bool(d['completion_artifact']),'missing resolution procedure '+d['id'])
        ck.require(set(d['blocked_consumers'])<=bid,'unknown decision consumer '+d['id'])
        ck.require(d['creates_authority'] is False,'worklist confused with runtime authority '+d['id'])
    graph={u['id']:u['depends_on'] for u in builds};state={}
    def visit(k: str) -> None:
        if state.get(k)==1:raise PacketError('cyclic build graph at '+k)
        if state.get(k)==2:return
        state[k]=1
        for x in graph[k]:visit(x)
        state[k]=2
    for k in graph:visit(k)
    ck.require(len(state)==29,'graph incomplete')
    reqs=c['requirements']['requirements']
    ck.require(len(reqs)==36,'requirement count changed')
    for r in reqs:
        ck.require(set(r['build_units'])<=bid and bool(r['build_units']),'unmapped requirement '+r['id'])
        ck.require(set(r['research_packets'])<=qid and set(r['decision_dependencies'])<=did,'bad requirement link '+r['id'])
    ck.require(c['acceptance']['counts']['entries']==126 and len(c['acceptance']['cases'])==126,'inherited cases removed')
    ck.require(c['acceptance']['all_execution_status']=='NOT_EXECUTED','inherited product case execution inflated')
    newcases=c['handoff_cases']['cases']
    ck.require(len(newcases)==30 and len({x['id'] for x in newcases})==30,'handoff cases incomplete')
    for x in newcases:ck.require(x['status']=='NOT_EXECUTED','handoff operating proof fabricated '+x['id'])
    ck.require(len(c['gates']['r6_branch_clarifications'])==5,'branch clarifications missing')
    for x in c['gates']['r6_branch_clarifications']:
        ck.require(x['unit'] in bid and len(x['still_required'])>0,'branch gate erased required proof')

def test_rejections(c: dict) -> list[str]:
    mutations=[
        ('native_subagent_allowed',lambda x:x['policy'].__setitem__('built_in_subagents_allowed',True)),
        ('internal_fallback_allowed',lambda x:x['policy'].__setitem__('internal_codex_fallback_allowed',True)),
        ('astra_build_dependency',lambda x:x['build']['units'][3].__setitem__('requires_astra',True)),
        ('decision_not_fable',lambda x:x['decisions']['decisions'][5].__setitem__('accountable_owner','Former principal')),
        ('fake_worker_start',lambda x:x['status'].__setitem__('started',True)),
        ('missing_build',lambda x:x['build']['units'].pop()),
        ('graph_cycle',lambda x:x['build']['units'][0].__setitem__('depends_on',['B28'])),
        ('missing_requirement',lambda x:x['requirements']['requirements'].pop()),
        ('fake_operating_test_pass',lambda x:x['handoff_cases']['cases'][0].__setitem__('status','PASS')),
        ('outcome_read_permission',lambda x:x['research']['packets'][0].__setitem__('protected_outcomes_may_be_opened_by_this_packet',True)),
    ]
    passed=[]
    for name,mutate in mutations:
        altered=deepcopy(c);mutate(altered)
        try:validate(altered,Checks())
        except PacketError:passed.append(name)
        else:raise PacketError('mutation was not rejected: '+name)
    return passed

def main() -> None:
    ck=Checks();data=snapshot();validate(data,ck)
    oldzip=ROOT/'archives/R5_source_packet.zip'
    ck.require(sha256(oldzip.read_bytes()).hexdigest()==EXPECTED_R5_ZIP_SHA256,'R5 source archive hash mismatch')
    with zipfile.ZipFile(oldzip) as z:
        ck.require(z.testzip() is None,'R5 archive corrupt')
        ck.require(len(z.namelist())==28,'R5 member census changed')
        for name in z.namelist():
            pp=PurePosixPath(name)
            ck.require(not pp.is_absolute() and '..' not in pp.parts,'unsafe baseline member')
            ck.require((ROOT/'baseline_r5'/name).read_bytes()==z.read(name),'baseline modified: '+name)
    # Preserve source program semantics; ownership/status may change but scientific fields cannot disappear.
    for key,oldfile,arr,allowed in [
        ('build','BUILD_PROGRAM.json','units',{'owner','status'}),
        ('research','RESEARCH_DOCKET.json','packets',{'owner','status'}),
        ('decisions','DECISION_REGISTER.json','decisions',{'owner','status'})]:
        old=load('baseline_r5/'+oldfile)[arr];new={x['id']:x for x in data[key][arr]}
        for item in old:
            for field,value in item.items():
                if field not in allowed:ck.require(new[item['id']][field]==value,'baseline semantic field lost: '+item['id']+'.'+field)
    ck.require(data['requirements']==load('baseline_r5/REQUIREMENT_CROSSWALK.json'),'requirement objects modified')
    ck.require(data['acceptance']==load('baseline_r5/ACCEPTANCE_CATALOG.json'),'inherited acceptance objects modified')
    for x in data['build']['units']+data['research']['packets']:
        path=ROOT/'work_cards'/(x['id']+'.md')
        ck.require(path.is_file(),'missing individual work card '+x['id'])
        text=path.read_text()
        ck.require('existing external fabric only' in text and 'Required Astra return: none' in text,'card lost routing rule '+x['id'])
    ck.require(len(list((ROOT/'work_cards').glob('*.md')))==53,'work-card count changed')
    for name in ['START_HERE.md','FABLE_START_PROMPT.md','FABLE_META_CEO_EXECUTION_HANDOFF.md','FIRST_WAVE_RUNBOOK.md','DECISION_RESOLUTION_PLAYBOOK.md','REVIEW_RELEASE_AND_RECOVERY.md','SUPERSESSION_MAP.md','INDEPENDENT_REVIEW_BRIEF.md','canonical_records/agentos/decisions/DEC-PROPHET-US-FABLE-META-CEO-DELEGATION.md']:
        ck.require((ROOT/name).is_file() and (ROOT/name).stat().st_size>150,'missing substantive document '+name)
    effective_master=(ROOT/'effective/PROPHET_US_MASTER_PLAN_R6.md').read_text()
    ck.require('**Effective version:** R6' in effective_master,'effective plan version is stale')
    ck.require('**Current handoff checkpoint:** Macro #6805 issue comment `5793406610`' in effective_master,'effective plan points to old current checkpoint')
    ck.require('**Current operation:** `prophet-us-fable-meta-ceo-20260923-001`' in effective_master,'effective plan operation is stale')
    manifest=load('MANIFEST.json');expected=set()
    ck.require(len({x['path'] for x in manifest['files']})==len(manifest['files']),'duplicate manifest paths')
    for item in manifest['files']:
        name=item['path'];p=PurePosixPath(name)
        ck.require(not p.is_absolute() and '..' not in p.parts,'unsafe manifest path '+name)
        raw=(ROOT/name).read_bytes();expected.add(name)
        ck.require(len(raw)==item['bytes'] and sha256(raw).hexdigest()==item['sha256'],'manifest mismatch '+name)
    actual={str(p.relative_to(ROOT)) for p in ROOT.rglob('*') if p.is_file() and str(p.relative_to(ROOT)) not in {'MANIFEST.json','VERIFICATION_REPORT.json'} and '__pycache__' not in p.parts}
    ck.require(expected==actual,'manifest file census mismatch')
    rejected=test_rejections(data)
    report={
        'status':'PASS','scope':'LOCAL_HANDOFF_DOCUMENT_HASH_GRAPH_AND_RESPONSIBILITY_CHECKS_ONLY',
        'document_checks':ck.count,'deliberately_invalid_document_mutations_rejected':len(rejected),'mutation_names':rejected,
        'counts':{'build_units':29,'research_packets':24,'decisions':12,'requirements':36,'work_cards':53,'inherited_acceptance_requirements':126,'additional_operating_requirements':30,'all_acceptance_requirements':156,'product_or_operating_acceptance_tests_executed':0,'baseline_members_verified':28,'manifest_content_files':len(manifest['files'])},
        'source_edits':False,'workers_dispatched':0,'models_trained':0,'registered_trials':0,'production_proven':False,
        'requires_astra':False,'external_fabric_only':True,
    }
    encoded=json.dumps(report,ensure_ascii=False,indent=2)+'\n'
    (ROOT/'VERIFICATION_REPORT.json').write_text(encoded,encoding='utf-8')
    sys.stdout.write(encoded)

if __name__=='__main__':
    try:main()
    except (OSError,ValueError,KeyError,TypeError,zipfile.BadZipFile) as exc:
        print('HANDOFF VERIFICATION FAILED: '+str(exc),file=sys.stderr)
        raise SystemExit(1)
