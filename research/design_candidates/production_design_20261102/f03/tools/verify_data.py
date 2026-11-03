#!/usr/bin/env python3
"""Independent identity, evidence and relative-link checks; no external effects."""
import argparse,csv,gzip,hashlib,json,re
from pathlib import Path
from urllib.parse import urlsplit,unquote

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--inputs',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--skip-doc-links',action='store_true');a=ap.parse_args();src,out=a.inputs,a.output
    read=lambda p:json.loads(p.read_text()); checks=[]
    def check(name,condition):
        assert condition,name
        checks.append({'name':name,'result':'PASS'})
    provenance=read(out/'data/provenance.json')
    for name,sha in provenance['source_blob_map'].items():
        b=(src/name).read_bytes();check('immutable input '+name,hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==sha)
    sessions=read(out/'data/assignment-directory.json');ids={s['id'] for s in sessions};check('all 36 assignments unique',len(ids)==len(sessions)==36)
    rr=read(out/'data/route-assignment-projection.json');original=read(src/'route-ownership.json')['rows'];byid={r['canonical_registry_id']:r for r in rr}
    check('348 exact canonical identities',len(rr)==len(byid)==348 and set(byid)=={r['page_id'] for r in original})
    for row in original:
        d=byid[row['page_id']]
        check('retained canonical fields '+row['page_id'],all(d[k]==row[k] for k in ['repo','route','route_kind','primary_session','source_template','builder','access_shell','payload_tier','lifecycle','scope_disposition','shared_archetype_owner','governed_regions']) and d['delegated_slices']==row['delegated_design_slices'])
    check('valid route assignments/slices',all(r['primary_session'] in ids and set(r['delegated_slices'])<=ids for r in rr))
    deltas=read(out/'data/source-delta-projection.json');check('nine deltas have no invented canonical IDs',len(deltas)==9 and all(d['canonical_registry_id'] is None for d in deltas))
    pages=read(out/'data/paper-page-directory.json');pk=lambda p:(p['paper_file_id'],p['paper_page_id']);pmap={pk(p):p for p in pages};baseline=read(src/'paper-files.json');expected={(f['file_id'],p['id']) for f in baseline for p in f['pages']}
    check('299 original pages and exactly two live observations',len(pages)==len(pmap)==301 and expected<=set(pmap) and len(set(pmap)-expected)==2)
    check('listed-only null counts are not empty pages',sum(p['board_count'] is None for p in pages)==106)
    boards=read(out/'data/paper-artboard-directory.json');bm={(b['paper_file_id'],b['paper_page_id'],b['artboard_id']):b for b in boards};ob=read(src/'paper-artboards.json')
    check('2450 exact compound artboard identities',len(boards)==len(bm)==2450 and set(bm)=={(b['file_id'],b['page_id'],b['artboard_id']) for b in ob})
    check('artboard names/geometry/custody preserved',all(all(bm[(b['file_id'],b['page_id'],b['artboard_id'])][k]==b[k] for k in ['name','width','height','child_count','page_custodian']) and bm[(b['file_id'],b['page_id'],b['artboard_id'])]['product_owner']==b['primary_session'] for b in ob))
    check('WTI three ownership exceptions retained',[(b['artboard_id'],b['product_owner'],b['page_custodian']) for b in boards if b['product_owner']!=b['page_custodian']]==[(b['artboard_id'],b['primary_session'],b['page_custodian']) for b in ob if b['primary_session']!=b['page_custodian']])
    actions=read(out/'data/resource-action-ledger.json');check('all 301 actions truthfully not dispatched',len(actions)==301 and all(not x['applied'] and x['effect_status']=='NOT_DISPATCHED' and x['admission_receipt'] is None and x['readback'] is None and x['final_destination_url'] is None and all(v is None for v in x['preservation_checks'].values()) for x in actions))
    destinations=read(out/'data/proposed-destinations.json');check('51 proposals without fabricated destination IDs',len(destinations)==51 and all(x['actual_file_id'] is None and x['actual_folder_id'] is None for x in destinations))
    check('no approval fabricated',all(p['rig_state'] is None and p['rig_receipt'] is None and p['candidate_selection'] is None for p in pages))
    for p in pages:
        for rel in p['recorded_successors']+p['recorded_predecessors']:
            check('lineage endpoints exist '+rel['source_page_id']+'→'+rel['target_page_id'],(rel['source_file_id'],rel['source_page_id']) in pmap and (rel['target_file_id'],rel['target_page_id']) in pmap and (out/rel['evidence']).is_file())
    inv_bytes=gzip.decompress((out/'evidence/generated-document-inventory.json.gz').read_bytes());check('full Macro inventory digest',hashlib.sha256(inv_bytes).hexdigest()=='4ddbd8102368d3af8a8a02a54f49ac2dfea485472feb771237c6f9a7d0e77026');inv=json.loads(inv_bytes)
    with (out/'data/generated-document-index.csv').open() as f:members=list(csv.DictReader(f))
    check('member CSV has every tracked path once',len(members)==14025 and {m['path'] for m in members}==set(inv['tracked_html']))
    check('member CSV full documents exact',{m['path'] for m in members if m['is_full_document']=='True'}==set(inv['document_paths']))
    check('member CSV included legacy paths exact',{m['path'] for m in members if m['export_disposition']=='included_legacy'}==set(inv['projection']['legacyPaths']))
    check('all seven inventory gaps have assigned design owner and null ID',len(read(out/'data/inventory-gaps.json'))==7 and all(x['design_assignment'] in ids and x['canonical_registry_id'] is None for x in read(out/'data/inventory-gaps.json')))
    native=read(out/'evidence/native-source-inventory.json');check('native census explicit 29/7 scope',native['receipt']['terminal_count']==29 and native['receipt']['mastermind_count']==7 and len(native['rows'])==36)
    check('two native source additions remain noncanonical',sorted(r['raw_generator_row']['route'] for r in native['rows'] if r['canonical_registry_id'] is None)==['/dev/options-plan','/options/equity-replay'])
    if not a.skip_doc_links:
        missing=[]
        for f in out.rglob('*.md'):
            for target in re.findall(r'\]\(([^)]+)\)',f.read_text()):
                u=urlsplit(target)
                if u.scheme or not u.path:continue
                if not (f.parent/unquote(u.path)).exists():missing.append({'file':str(f.relative_to(out)),'target':target})
        for target in ['DIRECTORY.md','CONTRACT.md','README.md','inventory.html','evidence/inventory-receipt.json','data/generated-document-index.csv']:
            if not (out/target).is_file():missing.append({'file':'directory/inventory HTML','target':target})
        check('all relative document links resolve',not missing)
    print(json.dumps({'kind':'pinned_input_identity_and_link_checks_not_visual_or_live_acceptance','status':'PASS','check_count':len(checks),'checks':checks},indent=2))

if __name__=='__main__':main()
