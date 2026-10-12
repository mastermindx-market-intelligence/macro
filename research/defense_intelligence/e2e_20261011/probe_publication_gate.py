#!/usr/bin/env python3
"""Read-only source-bound diagnostic; never executes the full workflow.

Read the pinned Git object through an existing repository and execute only two
small shell conditionals with local stubs. No product file, package installation,
source acquisition, workflow dispatch or publication is performed.
Exit0 means the documented unsafe source behavior reproduced, NOT acceptance.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

PIN = '5267c66846e7733bc1eb30edc1524daff51598ca'
PATH = '.github/workflows/government-revenue-live.yml'
BLOB = '33e09e0a5ad62d5b2ff3316e36992d20059b9681'
EXCERPTS = ['6cd8f1ab415882e73de18c00f359bb5b8f3fd9234ce6e359eabd251d63732bce',
            '730f152054a219f8656a493e07771d8c7ce5d521dc5f923c1af8a4c317d51af2']


def git_blob(raw: bytes) -> str:
    return hashlib.sha1(f'blob {len(raw)}\0'.encode()+raw).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    args = parser.parse_args()
    raw = subprocess.run(['git','-C',str(args.repo.resolve()),'show',f'{PIN}:{PATH}'],
                         check=True, capture_output=True, timeout=10).stdout
    actual = git_blob(raw)
    if actual != BLOB:
        raise ValueError('Source identity differs; do not apply old expectations')
    lines = raw.decode('utf-8').splitlines()
    extract = lambda a,b:'\n'.join(l[10:] for l in lines[a-1:b])+'\n'
    snippets=[extract(583,586),extract(611,618)]
    for snippet, expected in zip(snippets, EXCERPTS):
        if hashlib.sha256(snippet.encode()).hexdigest()!=expected:
            raise ValueError('Exact source excerpt differs; refuse execution')
    prelude=['have(){ return 1; };\n','before=original; after=mutated; status=0;\n']
    cases=['pytest_unavailable','prover_mutates_candidate_tree']
    results=[]
    with tempfile.TemporaryDirectory(prefix='govrev-research-gate-') as tmp:
        summary=Path(tmp)/'summary'
        env={'PATH':'/usr/bin:/bin','GOVREV_CANDIDATE_PROOF_FATAL':'1',
             'GITHUB_STEP_SUMMARY':str(summary)}
        for name, init, snippet in zip(cases,prelude,snippets):
            run=subprocess.run(['/bin/bash','-c',init+snippet],env=env,capture_output=True,
                               text=True,timeout=5,check=False)
            results.append({'case':name,'exit_code':run.returncode,'stdout':run.stdout.strip(),
                            'summary':summary.read_text() if summary.exists() else '',
                            'excerpt_sha256':hashlib.sha256(snippet.encode()).hexdigest()})
    reproduced=(all(r['exit_code']==0 for r in results)
                and 'UNPROVEN' in results[0]['stdout'] and 'PASSED' in results[1]['summary'])
    print(json.dumps({'source_pin':PIN,'workflow_git_blob':actual,'results':results,
                      'documented_fail_open_reproduced':reproduced,
                      'product_acceptance':False,'full_workflow_run':False,
                      'product_source_changed':False,'production_or_network_calls':False},indent=2))
    return 0 if reproduced else 1


if __name__=='__main__':
    raise SystemExit(main())
