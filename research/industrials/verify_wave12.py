"""Verify research crosswalk integrity, not an application or native-code test.

Supports the portable directory and the canonical research/industrials location.
No network, credentials, external writes, product admission, or trading effects.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
EXPECTED = {f'IND-D{x:02}' for x in range(1,31)} | {f'IND-R2{x:02}' for x in range(1,19)}
EXTRA = {f'IND-SF{x:02}' for x in range(1,9)}
FLAGS = {'can_rank','can_gate','can_size','can_originate','can_open_entry'}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def git_blob(body: bytes) -> str:
    return hashlib.sha1(f'blob {len(body)}\0'.encode() + body).hexdigest()


def range_ids(text: str) -> set[str]:
    result: set[str] = set()
    for token in text.split(','):
        token = token.strip()
        if '..' not in token:
            require(bool(re.fullmatch(r'IND-(?:D\d{2}|R2\d{2})',token)), 'invalid requirement token')
            result.add(token)
            continue
        left,right = token.split('..')
        a,b = re.fullmatch(r'(IND-(?:D|R2))(\d{2})',left), re.fullmatch(r'(IND-(?:D|R2))(\d{2})',right)
        require(a is not None and b is not None, 'invalid range')
        assert a is not None and b is not None
        require(a[1] == b[1] and int(a[2]) <= int(b[2]), 'incompatible range')
        result.update(f'{a[1]}{n:02}' for n in range(int(a[2]),int(b[2])+1))
    return result


def original_file(name: str) -> Path:
    for candidate in (ROOT/name,ROOT/'sources'/name,ROOT.parent.parent/'docs'/'superpowers'/'specs'/name):
        if candidate.is_file():
            return candidate
    raise ValueError(f'Original specification unavailable: {name}')


def main() -> None:
    checks: list[str] = []
    data=json.loads((ROOT/'WAVE12_FOUNDATION_ADOPTION.json').read_text())
    require(all(data[k] is True for k in ('research_only','not_a_native_schema','not_a_runtime_queue')), 'research boundary missing')
    checks.append('research-only artifact boundary')
    require(data['research_carrier']==7789 and data['foundation_carrier']==7870 and data['inspected_foundation_head']=='45eb37bbf832e007e67ce2594674d6bfeeb3b880','carrier mismatch')
    checks.append('exact research and implementation references')
    groups=data['groups']; ids=[i for g in groups for i in g['requirements']]
    require(len(ids)==48 and len(set(ids))==48 and set(ids)==EXPECTED,'missing or duplicated prior requirement')
    checks.append('all 48 prior requirements mapped exactly once')
    require(len(groups)==9 and len({g['group'] for g in groups})==9,'group mismatch')
    require(all(g['shared_tasks'] and all(re.fullmatch(r'T(?:0[1-9]|1[0-2])',t) for t in g['shared_tasks']) and g['product_tests_executed'] is False for g in groups),'invalid upstream mapping or false product claim')
    checks.append('nine ownership groups and permitted upstream task references')
    doc=(ROOT/data['source_document']).read_text()
    rows={parts[1].strip():range_ids(parts[2].strip()) for line in doc.splitlines() if re.match(r'\| G\d{2} \|',line) for parts in [line.split('|')]}
    require(set(rows)=={g['group'] for g in groups} and all(rows[g['group']]==set(g['requirements']) for g in groups),'document/JSON crosswalk mismatch')
    checks.append('written and machine-readable crosswalk parity')
    original_ids=set()
    for ref in data['source_designs']:
        body=original_file(ref['filename']).read_bytes()
        require(git_blob(body)==ref['git_blob'],'original specification bytes differ')
        original_ids.update(re.findall(r'^\| (IND-(?:D\d{2}|R2\d{2})) \|',body.decode(),re.M))
    require(original_ids==EXPECTED,'original requirement inventory differs')
    checks.append('unchanged exact original design blobs and requirement inventory')
    require(set(data['additional_cases'])==EXTRA and len(data['additional_cases'])==8 and set(re.findall(r'^\| (IND-SF\d{2}) \|',doc,re.M))==EXTRA,'additional case mismatch')
    checks.append('eight separately labelled proposed integration cases')
    require(data['accepted_shared_release'] is None and data['live_private_binding_proven'] is False and data['fable_industrials_dispatched'] is False,'unsupported acceptance/dispatch claim')
    require(set(data['authority'])==FLAGS and all(v is False for v in data['authority'].values()),'authority drift')
    checks.append('unproven release/private/dispatch and all-false authority retained')
    print(json.dumps({'passed':len(checks),'failed':0,'scope':'research package integrity only','checks':checks},indent=2))

if __name__=='__main__':
    main()
