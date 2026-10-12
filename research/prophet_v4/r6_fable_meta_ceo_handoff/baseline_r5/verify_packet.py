"""Verify a research-plan packet, not the Prophet application or its performance.

Standard library only. No external requests, model fitting, product imports, source
modification or protected outcomes. An invalid packet fails with a nonzero exit.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile

ROOT = Path(__file__).resolve().parent

def bad_constant(value: str):
    raise ValueError(f'Nonfinite JSON token: {value}')

def load(name: str):
    return json.loads((ROOT/name).read_text(encoding='utf-8'), parse_constant=bad_constant)

def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def verify() -> dict:
    checks = []
    def check(name: str, condition: bool):
        if not condition:
            raise AssertionError(name)
        checks.append({'check':name,'result':'PASS'})

    required = ['PROPHET_US_MASTER_PLAN_R5.md','RESEARCH_DOCKET.md','BUILD_PROGRAM.md',
                'INPUT_MANIFEST.json','SOURCE_REGISTER.json','RESEARCH_DOCKET.json',
                'BUILD_PROGRAM.json','DECISION_REGISTER.json','CARRIER_MAP.json',
                'REQUIREMENT_CROSSWALK.json','ACCEPTANCE_CATALOG.json','ACTIVATION_GATES.json',
                'PROPOSAL_STATUS.json','START_HERE.md','build_catalogs.py','build_crosswalk.py']
    check('All designated deliverables exist',all((ROOT/x).is_file() for x in required))
    for p in sorted(ROOT.rglob('*.json')):
        if p.name not in {'MANIFEST.json','VERIFICATION_REPORT.json'}:
            json.loads(p.read_text(encoding='utf-8'),parse_constant=bad_constant)
    check('All substantive JSON files parse without nonfinite numbers',True)

    im=load('INPUT_MANIFEST.json')
    check('Four exact inherited dossiers',len(im)==4 and {x['id'] for x in im}=={'R1','R2','R3','R4'})
    for x in im:
        check(f"{x['id']} input digest",sha(ROOT/x['file'])==x['sha256'])
        check(f"{x['id']} word-count receipt",len((ROOT/x['file']).read_text().split())==x['words'])

    qs=load('RESEARCH_DOCKET.json')['packets']; bs=load('BUILD_PROGRAM.json')['units']
    ds=load('DECISION_REGISTER.json')['decisions']; rs=load('REQUIREMENT_CROSSWALK.json')['requirements']
    ss=load('SOURCE_REGISTER.json')['sources']; ac=load('ACCEPTANCE_CATALOG.json'); cases=ac['cases']
    qi={x['id'] for x in qs};bi={x['id'] for x in bs};di={x['id'] for x in ds};ri={x['id'] for x in rs};si={x['id'] for x in ss}
    check('24 unique research packets',len(qs)==len(qi)==24 and qi=={f'Q{i:02}' for i in range(1,25)})
    check('29 unique build units',len(bs)==len(bi)==29 and bi=={f'B{i:02}' for i in range(29)})
    check('12 concrete owner decisions',len(ds)==len(di)==12)
    check('36 traced product/research requirements',len(rs)==len(ri)==36)
    check('Source references unique',len(ss)==len(si))
    for q in qs:
        check(q['id']+' consumers and source refs', bool(q['build_consumers']) and set(q['build_consumers'])<=bi and set(q['source_refs'])<=si)
        check(q['id']+' no study authority',q['status']=='PROPOSED_WORK_PACKET' and q['protected_outcomes_may_be_opened_by_this_packet'] is False)
        check(q['id']+' decision and falsifier',all(bool(q[k].strip()) for k in ['question','population','inputs','controls','method','decision','falsifier','owner']))
    for b in bs:
        check(b['id']+' dependencies/reference identity', set(b['depends_on'])<=bi and b['id'] not in b['depends_on'] and set(b['research_packets'])<=qi)
        check(b['id']+' not dispatched and proof defined', b['status']=='DESIGN_NOT_DISPATCHED' and all(b[k].strip() for k in ['outcome','owner_scope','inputs','outputs','proof','release_limit','discriminating_cases']))
    # Deterministic Kahn topological order proves only graph structure, not schedulability.
    done=[]
    remaining={b['id']:set(b['depends_on']) for b in bs}
    while remaining:
        ready=sorted(k for k,v in remaining.items() if v<=set(done))
        check('DAG progress '+str(len(done)),bool(ready))
        for k in ready:
            done.append(k);del remaining[k]
    check('All build units reachable from B00',done[0]=='B00' and len(done)==29)
    check('No false global B4 wait for shared historical measurement','B05' not in next(b for b in bs if b['id']=='B06')['depends_on'])
    gates=load('ACTIVATION_GATES.json')['gates']
    check('Live B4 activation remains gated',any(g['unit']=='B06' and g['branch']=='prospective B4 policy-cell capture' and 'B05' in g['requires_builds'] for g in gates))
    for g in gates:
        check(g['id']+' branch references',g['unit'] in bi and set(g['requires_builds'])<=bi and set(g['requires_decisions'])<=di)
    for d in ds:
        check(d['id']+' output and ownership defined',d['status']=='OPEN_OWNER_DECISION' and d['creates_authority'] is False and set(d['blocked_consumers'])<=bi and all(d[k].strip() for k in ['owner','required_evidence','required_output','forbidden_shortcut']))
    for r in rs:
        check(r['id']+' traced to builds, research and decisions', bool(r['build_units']) and set(r['build_units'])<=bi and set(r['research_packets'])<=qi and set(r['decision_dependencies'])<=di and r['master_plan_sections'])
    check('No build orphan from requirement coverage',set.union(*(set(r['build_units']) for r in rs))==bi)
    check('Every research packet has a declared build consumer',all(q['build_consumers'] for q in qs))

    check('126 case entries, not statistical N',len(cases)==126 and len({x['id'] for x in cases})==126)
    check('All cases not executed and not production proven',all(c['execution_status']=='NOT_EXECUTED' and c['production_proven'] is False for c in cases))
    for prefix,count in [('R3',36),('R4',48)]:
        inherited=load('inputs/'+prefix+'_ACCEPTANCE_CASES.json')['cases']
        expected={prefix+':'+c['id']:c for c in inherited}
        actual={c['id']:c['original_case'] for c in cases if c['origin']==prefix}
        check(prefix+' inherited case text preserved verbatim as JSON values',actual==expected and len(actual)==count)
    check('42 added integrated cases',sum(x['origin']=='R5' for x in cases)==42)
    check('Acceptance cases refer to existing builds and requirements',all(set(c['build_units'])<=bi and set(c.get('requirements',[]))<=ri for c in cases))
    check('All build units have mapped required case(s)',set.union(*(set(c['build_units']) for c in cases))==bi)
    # Every requirement must have at least one explicitly associated integrated case OR
    # a case under one of its implementing build units (inherited cases retain old fields).
    check('Every requirement reaches at least one acceptance case',all(any(r['id'] in c.get('requirements',[]) or set(r['build_units']) & set(c['build_units']) for c in cases) for r in rs))

    cs=load('CARRIER_MAP.json')['carriers']
    check('13 unique historical existing carriers',len(cs)==len({c['number'] for c in cs})==13)
    check('No refreshed current status fabricated',all(c['current_head_and_runtime_state']=='NOT_RECHECKED_R5' for c in cs))
    status=load('PROPOSAL_STATUS.json')
    check('No action authority',all(v is False for v in status['authority'].values()))
    check('No registration/product/execution/mission completion claim',all(status[k] is False for k in ['registered_trial','source_committed','source_changes','workers_dispatched','production_proven','mission_complete']))

    main=(ROOT/'PROPHET_US_MASTER_PLAN_R5.md').read_text(encoding='utf-8')
    check('26 master-plan sections',set(int(x) for x in re.findall(r'^## (\d+)\.',main,re.M))==set(range(1,27)))
    check('Required core docs named and readable',all(n in main and (ROOT/n).is_file() for n in ['BUILD_PROGRAM.md','RESEARCH_DOCKET.md','CARRIER_MAP.json','DECISION_REGISTER.json','ACCEPTANCE_CATALOG.json']))
    check('All R5 citations resolve',set(re.findall(r'\b[IX]\d{2}\b',main))<=si)
    for name in ['PROPHET_US_MASTER_PLAN_R5.md','RESEARCH_DOCKET.md','BUILD_PROGRAM.md','START_HERE.md']:
        text=(ROOT/name).read_text()
        check(name+' no empty placeholder tokens',not re.search(r'\b(?:TBD|TODO|FIXME)\b',text))
        check(name+' balanced fenced blocks',sum(l.startswith('```') for l in text.splitlines())%2==0)
    if (ROOT/'MANIFEST.json').exists():
        manifest=load('MANIFEST.json')
        for item in manifest['files']:
            p=ROOT/item['path']
            check('Manifest '+item['path'],p.is_file() and p.stat().st_size==item['bytes'] and sha(p)==item['sha256'])
        check('Manifest contains every content file',set(x['path'] for x in manifest['files'])==set(str(p.relative_to(ROOT)) for p in ROOT.rglob('*') if p.is_file() and p.name not in {'MANIFEST.json','VERIFICATION_REPORT.json'} and '__pycache__' not in p.parts))
    return {'verification_scope':'LOCAL_DOCUMENT_STRUCTURE_AND_HASHES_ONLY','status':'PASS',
            'check_count':len(checks),'counts':{'research_packets':24,'build_units':29,'decisions':12,'requirements':36,'acceptance_entries':126,'acceptance_executed':0,'production_acceptance_tests_run':0},
            'topological_order':done,'checks':checks,
            'limits':['No native Prophet test suite executed','No market outcomes read or model fitted','No independent non-author review','No worker admission or production proof','Acyclic does not imply dependencies currently satisfied']}

if __name__=='__main__':
    try:
        result=verify()
    except (AssertionError,ValueError,OSError,KeyError,TypeError) as exc:
        print(f'PACKET VERIFICATION FAILED: {exc}',file=sys.stderr)
        sys.exit(1)
    data=json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+'\n'
    (ROOT/'VERIFICATION_REPORT.json').write_text(data,encoding='utf-8')
    print(json.dumps({'status':result['status'],'scope':result['verification_scope'],'checks':result['check_count'],'counts':result['counts']},indent=2))
