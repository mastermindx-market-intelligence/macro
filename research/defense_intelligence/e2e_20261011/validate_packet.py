#!/usr/bin/env python3
"""Local planning consistency checks; no product tests, network or runtime writes."""
from __future__ import annotations
import ast
import argparse
import hashlib
import json
from pathlib import Path
import re


def validate(root: Path) -> dict:
    errors=[]
    def check(value, text):
        if not value:errors.append(text)
    def load(name):return json.loads((root/name).read_text())
    d=load('DELIVERY_CONTRACTS.json');s=load('SOURCE_INDEX.json');e=load('EVIDENCE.json')
    tasks=d['tasks'];cases=d['acceptance_cases'];sources=s['sources']
    ti={t['id'] for t in tasks};ai={a['id'] for a in cases};si={x['id'] for x in sources}
    check(len(ti)==len(tasks)==d['task_count'],'Unique task count')
    check(len(ai)==len(cases)==d['acceptance_case_count'],'Unique acceptance count')
    check(len(si)==len(sources)==s['source_count'],'Unique source count')
    edges={t['id']:set(t['requires_all']) for t in tasks};order=[];left=dict(edges)
    for t in tasks:
        check(edges[t['id']]<=ti,'Known dependencies: '+t['id'])
        check(t['state']=='planned_not_dispatched','No fake runtime state: '+t['id'])
        check(bool(t['deliverable']) and bool(t['scope_paths']),'Concrete contract: '+t['id'])
        inverse={a['id'] for a in cases if t['id'] in a['tasks']}
        check(inverse==set(t['acceptance_cases']),'Bidirectional acceptance: '+t['id'])
    while left:
        ready=sorted(k for k,v in left.items() if v<=set(order))
        if not ready:errors.append('Dependency cycle');break
        order.extend(ready)
        for k in ready:del left[k]
    for a in cases:check(bool(a['tasks']) and set(a['tasks'])<=ti,'Assigned case: '+a['id'])
    waves=d['legacy_wave_map'];expected={'D0R'}|{f'D{i}' for i in range(1,21)}
    check(set(waves)==expected,'All original21waves mapped')
    check(waves['D19']['disposition']=='excluded_not_completed' and not waves['D19']['tasks'],'Prophet not marked completed')
    for w,v in waves.items():
        if w!='D19':check(bool(v['tasks']) and set(v['tasks'])<=ti,'Included wave has task: '+w)
    cited=set();broken=[]
    for f in root.glob('*.md'):
        text=f.read_text();cited.update(re.findall(r'\b[SE]\d{2}\b',text))
        for link in re.findall(r'\[[^\]]+\]\(([^)]+)\)',text):
            if re.match(r'\w+://',link) or link.startswith('#'):continue
            if not (root/link.split('#')[0]).is_file():broken.append(link)
    check(cited<=si,'All source IDs resolve')
    check(not broken,'Relative links: '+str(broken))
    for f in root.glob('*.py'):ast.parse(f.read_text(),filename=f.name)
    for source in sources:
        if source.get('commit'):check(bool(re.fullmatch('[a-f0-9]{40}',source['commit'])),'Valid source SHA '+source['id'])
        check(bool(source['note']),'Evidence qualification '+source['id'])
    probe=root/'probe_publication_gate.py';raw=probe.read_bytes();blob=hashlib.sha1(f'blob {len(raw)}\0'.encode()+raw).hexdigest()
    check(blob==e['packaged_probe_verification']['script_git_blob'],'Executed probe equals packaged source')
    check(e['packaged_probe_verification']['documented_fail_open_reproduced'],'Actual probe evidence')
    check(e['product_tests_run'] is False and e['fleet_dispatched'] is False,'No inflated proof')
    text='\n'.join(f.read_text() for f in root.iterdir() if f.is_file() and f.suffix in {'.md','.json','.py'})
    patterns=[r'/'+'Users/'+r'\S+',r'/'+'Volumes/'+r'\S+',r'BEGIN (?:RSA |OPENSSH )?PRIVATE KEY',r'ghp_[a-zA-Z0-9]{20,}',r'sk-proj-[a-zA-Z0-9]{20,}']
    check(not any(re.search(p,text) for p in patterns),'Private host/credential pattern scan')
    handoff=(root/'FABLE_HANDOFF.md').read_text()
    for term in ['native Opus','task operators','MISSION','OUT OF SCOPE','NOT DONE UNLESS','RETURN']:
        check(term in handoff,'Handoff field '+term)
    return {'status':'PASS' if not errors else 'FAIL','scope':'Packet consistency/source-ref/DAG/links/syntax only; not product or model acceptance',
            'counts':{'tasks':len(tasks),'acceptance_cases':len(cases),'source_records':len(sources),'original_waves':len(waves)},
            'dependency_order':order,'errors':errors,'product_tests_run':False,'production_browser_proof':False,'fleet_dispatched':False,
            'probe_blob':blob,'source_reference_ids_resolve':cited<=si,'relative_links_resolve':not broken}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=Path(__file__).resolve().parent);p.add_argument('--output',type=Path);a=p.parse_args()
    result=validate(a.root.resolve());raw=json.dumps(result,indent=2)+'\n'
    if a.output:a.output.write_text(raw)
    print(raw);raise SystemExit(0 if result['status']=='PASS' else 1)
