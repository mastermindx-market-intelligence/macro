#!/usr/bin/env python3
"""Check structural evidence identities and falsifiers; no browser or Paper mutation."""
from __future__ import annotations
import copy
import gzip
import json
import tempfile
from pathlib import Path
from page_observations import EVIDENCE, RAW, attach_page_observations, normalize_capture


def main():
    root = Path(__import__('sys').argv[1] if len(__import__('sys').argv) > 1 else '.')
    baseline = json.loads((root/'data/paper-page-directory.json').read_text())
    raw = json.loads(gzip.decompress((root/RAW).read_bytes()))
    evidence = json.loads((root/EVIDENCE).read_text())
    checks = []
    def check(name, condition):
        assert condition, name
        checks.append({'name': name, 'result': 'PASS'})
    observed = normalize_capture(raw, baseline)
    check('raw read receipts reproduce the entire observation file', observed == evidence['pages'])
    check('106 exact listed-only pages, 12 files and 1837 complete board identities',
          len(observed) == 106 and len({p['file_id'] for p in observed}) == 12 and
          sum(len(p['artboards']) for p in observed) == 1837)
    check('12 successful zero-artboard reads remain explicit', sum(p['artboard_count'] == 0 for p in observed) == 12)
    check('two capped lists require 26 individually observed tail boards',
          sum(p['initial_returned_artboards'] < p['artboard_count'] for p in observed) == 2 and
          sum(p['artboard_count'] - p['initial_returned_artboards'] for p in observed) == 26)
    check('provider data-loss warning retained on the exact duplicate file only',
          {p['file_id'] for p in observed if p['warnings']} == {'01M3NQQ5KHTEZ50AGPT3RAD4BN'})
    short_ids = [b['id'] for p in observed for b in p['artboards']]
    compound_ids = [p['file_id']+'/'+p['page_id']+'/'+b['id'] for p in observed for b in p['artboards']]
    check('repeated short IDs coexist with 1837 unique compound identities',
          len(set(short_ids)) < len(short_ids) and len(set(compound_ids)) == 1837)
    data = {'pages': copy.deepcopy(baseline), 'artboards': [{'sentinel': 'unchanged'}], 'metadata': {}}
    before = copy.deepcopy(data)
    attach_page_observations(data, root)
    check('frozen pages and board data remain unchanged', data['pages'] == before['pages'] and data['artboards'] == before['artboards'])
    check('no product-owner, approval, successor or archival fields inferred', all(
          not ({'product_owner', 'rig_state', 'rig_receipt', 'successor', 'disposition'} & set(p)) for p in data['page_observations']))
    check('coverage separates completed metadata reads from remaining retention work',
          data['metadata']['structural_observations']['remaining_pages'] == 0 and
          data['metadata']['structural_observations']['observed_artboards'] == 1837)

    def reject(name, change):
        altered = copy.deepcopy(raw); change(altered)
        try:
            normalize_capture(altered, baseline)
        except (ValueError, KeyError, TypeError, StopIteration):
            check(name, True)
        else:
            check(name, False)
    def envelope(item):
        r = item['response']
        if isinstance(r.get('structuredContent'), dict):
            return r['structuredContent'], lambda value: r.update(structuredContent=value)
        block = next(x for x in r['content'] if x.get('type') == 'text' and x.get('text', '').startswith('{'))
        return json.loads(block['text']), lambda value: block.update(text=json.dumps(value))
    def alter_part(item, predicate, update):
        value, save = envelope(item)
        for block in value['result']['content']:
            if block.get('type') != 'text': continue
            try: part = json.loads(block['text'])
            except ValueError: continue
            if predicate(part):
                update(part); block['text'] = json.dumps(part); save(value); return
        raise AssertionError('fixture part missing')
    reject('duplicate page observation is rejected', lambda r: r['page_reads'].append(copy.deepcopy(r['page_reads'][0])))
    reject('unknown page cannot be promoted from a read', lambda r: r['page_reads'][0].update(page_id='p-NOT-FOUND'))
    reject('mismatched returned file is rejected', lambda r: alter_part(r['page_reads'][0], lambda p:'file' in p, lambda p:p['file'].update(id='WRONG')))
    reject('mismatched returned page is rejected', lambda r: alter_part(r['page_reads'][0], lambda p:'pageId' in p, lambda p:p.update(pageId='p-WRONG')))
    reject('unsafe page URL is rejected', lambda r: alter_part(r['page_reads'][0], lambda p:'pageId' in p, lambda p:p.update(url='javascript:alert(1)')))
    reject('a failed read is never a zero-artboard success', lambda r: r['page_reads'][0]['response'].update(isError=True))
    reject('non-UTC timestamp offsets cannot be ordered as UTC strings', lambda r: r['page_reads'][0].update(observed_at='2026-11-04T09:00:00.000+02:00'))
    reject('mixed timestamp precision cannot corrupt completion order', lambda r: r['page_reads'][0].update(observed_at='2026-11-04T08:00:00Z'))
    reject('supplemental timestamp uses the same canonical UTC precision', lambda r: r['supplemental_reads'][0].update(observed_at='2026-11-04T08:00:00.000001Z'))
    reject('missing tail-node reads cannot claim a completed capped list', lambda r: r.update(supplemental_reads=[x for x in r['supplemental_reads'] if x['tool']!='get_node_info']))
    reject('missing root summary cannot certify tail-node membership', lambda r: r.update(supplemental_reads=[x for x in r['supplemental_reads'] if x['tool']!='get_tree_summary']))
    reject('duplicate supplemental node is rejected', lambda r: r['supplemental_reads'].append(copy.deepcopy(next(x for x in r['supplemental_reads'] if x['tool']=='get_node_info'))))
    reject('board on another page is rejected', lambda r: alter_part(next(x for x in r['supplemental_reads'] if x['tool']=='get_node_info'), lambda p:'parentId' in p, lambda p:p.update(parentId='root_node_p-WRONG')))
    populated = next(i for i,x in enumerate(observed) if x['artboard_count'] and not x['completion_reads'])
    reject('nonfinite board geometry is rejected', lambda r: alter_part(r['page_reads'][populated], lambda p:'pageId' in p, lambda p:p['artboards'][0].update(width=float('inf'))))
    reject('negative or Boolean counts are rejected', lambda r: alter_part(r['page_reads'][0], lambda p:'pageId' in p, lambda p:p.update(artboardCount=True)))

    with tempfile.TemporaryDirectory(prefix='f03-read-evidence-') as tmp:
        target = Path(tmp); (target/EVIDENCE).parent.mkdir(parents=True)
        (target/EVIDENCE).write_text(json.dumps(evidence)); (target/RAW).write_bytes((root/RAW).read_bytes()+b'corruption')
        untouched = {'pages': baseline, 'metadata': {}}
        snapshot = copy.deepcopy(untouched)
        try: attach_page_observations(untouched, target)
        except ValueError: check('raw digest failure attaches no partial projection', untouched == snapshot)
        else: check('raw digest failure attaches no partial projection', False)
        (target/EVIDENCE).unlink()
        untouched = {'pages': baseline, 'metadata': {'structural_observations': {'observed_pages': 106}}}
        try: attach_page_observations(untouched, target)
        except ValueError: check('missing prior evidence cannot leave a stale completion claim', True)
        else: check('missing prior evidence cannot leave a stale completion claim', False)
    print(json.dumps({'kind':'read_evidence_identity_checks_not_acceptance','status':'PASS',
                      'check_count':len(checks),'checks':checks,'limits':['Metadata, not full-content or visual comparison.','No move, archival, input-path, browser or approval proof.']}, indent=2))


if __name__ == '__main__':
    main()
