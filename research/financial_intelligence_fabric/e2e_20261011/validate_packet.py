#!/usr/bin/env python3
"""Validate planning artifacts; does not execute project code or query a service."""
from __future__ import annotations
import argparse
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys


def main() -> int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root',type=Path,default=Path(__file__).resolve().parent)
    ap.add_argument('--output',type=Path)
    args=ap.parse_args();root=args.root.resolve();fail=[]
    def require(ok,description):
        if not ok:fail.append(description)
    load=lambda f:json.loads((root/f).read_text())
    sources=load('SOURCE_INDEX.json')['sources'];tasks=load('TASK_GRAPH.json')['tasks']
    cases=load('ACCEPTANCE_MATRIX.json')['cases'];packs=load('SPECIALIST_PACKS.json')['packs']
    si={x['id'] for x in sources};ti={x['id'] for x in tasks};ci={x['id'] for x in cases}
    require(len(si)==len(sources)==36,'36 unique source records required')
    require(len(ti)==len(tasks)==39,'39 unique tasks required')
    require(len(ci)==len(cases)==54,'54 unique acceptance cases required')
    require({p['id'] for p in packs}=={f'PK{i:02}' for i in range(1,13)},'Twelve packs required')
    for s in sources:
        if 'commit' in s:require(bool(re.fullmatch('[0-9a-f]{40}',s['commit'])),f"Bad source pin {s['id']}")
        require(bool(s.get('note')),f"Missing evidence limit {s['id']}")
    dependencies={t['id']:set(t['requires_all']) for t in tasks}
    for t in tasks:
        require(dependencies[t['id']]<=ti,f"Unknown dependency {t['id']}")
        require(t['state']=='planned_not_dispatched',f"False runtime state {t['id']}")
        require(set(t['acceptance_cases'])<=ci,f"Unknown acceptance ref {t['id']}")
        require(bool(t['outputs']) and bool(t['acceptance_evidence']),f"Unspecified outcome {t['id']}")
        inverse={c['id'] for c in cases if t['id'] in c['tasks']}
        require(inverse==set(t['acceptance_cases']),f"Case/task mismatch {t['id']}")
    order=[];remaining=dict(dependencies)
    while remaining:
        ready=sorted(k for k,v in remaining.items() if v<=set(order))
        if not ready:fail.append('Dependency cycle');break
        order.extend(ready)
        for k in ready:del remaining[k]
    for c in cases:
        require(bool(c['tasks']) and set(c['tasks'])<=ti,f"Unowned case {c['id']}")
    owners=Counter(p for t in tasks for p in t.get('specialist_pack_ids',[]))
    require(owners==Counter({f'PK{i:02}':1 for i in range(1,13)}),'Each specialist pack needs one task owner')
    require(load('TASK_GRAPH.json')['not_runtime_queue'] is True,'Task graph must not be runtime queue')
    broken=[];cited=set()
    for file in sorted(root.glob('*.md')):
        text=file.read_text()
        for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)',text):
            if re.match(r'\w+://',target) or target.startswith('#'):continue
            p=target.split('#',1)[0]
            if not (file.parent/p).is_file():broken.append(f'{file.name}: {target}')
        cited.update(re.findall(r'\b(?:S|E)\d{2}\b',text))
    require(not broken,'Broken relative links: '+str(broken))
    require(cited<=si,'Unknown cited sources: '+str(cited-si))
    for p in root.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
    public_text='\n'.join(p.read_text() for p in root.iterdir() if p.is_file() and p.suffix in ['.md','.json','.py'])
    private_patterns=[r'/'+'Users/'+r'[^\s]+',r'/'+'Volumes/'+r'[^\s]+',r'/'+'private/var/db',r'BEGIN (?:RSA |OPENSSH )?PRIVATE KEY',r'ghp_[A-Za-z0-9]{20,}',r'sk-proj-[A-Za-z0-9]{20,}']
    require(not any(re.search(p,public_text) for p in private_patterns),'Private host/credential pattern found')
    handoff=(root/'FABLE_HANDOFF.md').read_text()
    for phrase in ['native Opus','task operators','model: opus','SCOPE','OUT OF SCOPE','NOT DONE UNLESS','RETURN']:
        require(phrase in handoff,'Missing handoff requirement '+phrase)
    master=(root/'MASTERPLAN.md').read_text()
    for phrase in ['Prophet shadow','excluded','250','1,000','Excel','source','cutoff']:
        require(phrase in master,'Missing core scope/acceptance term '+phrase)
    probe=load('PROBE_RESULTS.json')
    require(probe['independent_mutations']==14 and len(probe['incorrectly_accepted_and_disclosed_fields'])==9,'Probe count mismatch')
    require(probe['repair_hypothesis']['all_14_mutations_refused'] and probe['repair_hypothesis']['all_four_policy_results_byte_equal'],'Hypothesis evidence missing')
    require(probe['source_patch_applied'] is False and probe['production_http_calls'] is False,'Probe scope inflated')
    result={'packet_validation':'PASS' if not fail else 'FAIL','scope':'Documentation/schema/link/DAG checks and Python syntax only; not product tests or scientific acceptance','checks':{'sources':len(sources),'tasks':len(tasks),'acceptance_cases':len(cases),'specialist_packs':len(packs),'acyclic_graph':len(order)==len(tasks),'relative_links_resolve':not broken,'source_reference_ids_resolve':cited<=si,'case_assignments_checked':True,'python_syntax_checked':True,'public_text_pattern_scan':'PASS' if not fail else 'See failures'},'topological_order':order,'failures':fail,'full_product_test_suite_run':False,'fleet_dispatched':False,'production_or_browser_proof':False}
    raw=json.dumps(result,indent=2)+'\n'
    if args.output:args.output.write_text(raw)
    print(raw)
    return 0 if not fail else 1


if __name__=='__main__':
    raise SystemExit(main())
