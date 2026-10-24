"""Verify the retained Crop Progress report through isolated existing consumers.

Usage: python3 -B verify_local_intake.py REPO PDF NEW_OUTPUT_DIRECTORY
No network, provider, canonical-store, staging or publication effects.
"""
from pathlib import Path
import copy
import hashlib
import json
import re
import sqlite3
import subprocess
import sys
from datetime import date, datetime, timezone

PDF_SHA = 'ecdbbb595fb63ce179dbf0aad57541c28aec53e988489a376b2a1d002304968c'
ID = 'usda-nass-2026-10-13-crop-progress'


def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    repo, pdf, out = [Path(x).resolve() for x in sys.argv[1:]]
    assert digest(pdf) == PDF_SHA, 'source hash mismatch'
    assert not out.exists(), 'existing evidence must not be overwritten'
    sidepath = Path(__file__).with_name('crop_progress_sidecar.json')
    sidebytes = sidepath.read_bytes()
    side = json.loads(sidebytes)
    checks = []

    def passed(name, value):
        assert value, name
        checks.append(name)

    def audit(event, args):
        if event in {'socket.connect', 'socket.getaddrinfo', 'socket.sendto'}:
            raise RuntimeError('network forbidden')

    sys.addaudithook(audit)
    sys.path.insert(0, str(repo))
    from engine.research_vault import ingest, r2_store
    from engine.press import desk_planner as planner
    text = subprocess.check_output(['pdftotext', '-layout', str(pdf), '-'], text=True)
    pages = text.split('\f')
    passed('sixteen_pages', len([p for p in pages if p.strip()]) == 16)
    passed('agency_and_release_date', 'Released October 13, 2026' in pages[0]
           and 'National Agricultural Statistics Service' in pages[0])
    passed('missing_2025_and_imputation_caveat',
           all(x in pages[0] for x in ['weeks ending', 'October 5, 2025',
               'November 9, 2025', 'imputed estimates for 2025']))
    passed('corn_harvest_row', bool(re.search(r'18 States\s*\.+\s*\(NA\)\s+23\s+33\s+39', pages[1])))
    passed('corn_condition_row', bool(re.search(r'18 States\s*\.+\s*5\s+12\s+27\s+44\s+12', pages[1])))
    passed('corn_previous_condition_row', bool(re.search(r'Previous week\s*\.+\s*6\s+12\s+28\s+42\s+12', pages[1])))
    passed('soybean_harvest_row', bool(re.search(r'18 States\s*\.+\s*\(NA\)\s+25\s+46\s+50', pages[2])))
    passed('soybean_condition_row', bool(re.search(r'18 States\s*\.+\s*4\s+10\s+29\s+46\s+11', pages[3])))
    passed('soybean_previous_condition_row', bool(re.search(r'Previous week\s*\.+\s*4\s+10\s+29\s+46\s+11', pages[3])))
    passed('iowa_corn_row', bool(re.search(r'Iowa\s*\.+\s*\(NA\)\s+7\s+14\s+34', pages[1])))
    passed('iowa_soybean_row', bool(re.search(r'Iowa\s*\.+\s*\(NA\)\s+5\s+31\s+59', pages[2])))
    passed('coverage_denominators', 'harvested 93%' in pages[1]
           and 'planted 91%' in pages[1] and 'harvested 96%' in pages[2]
           and 'planted 96%' in pages[3])
    passed('methodology_and_revision', all(x in pages[13] for x in
        ['non-probability', '3,600', 'subjectively', 'acreage',
         'subject to revision the following week']))
    passed('condition_arithmetic', 44+12 == 56 and 42+12 == 54 and 46+11 == 57)
    passed('date_only_publication_no_invented_clock', side['published_at'] == '2026-10-13')
    passed('no_ticker_or_promotional_priority', side['tickers'] == [] and side['top_pick'] is False)
    out.mkdir(parents=True)
    storepath = out/'store'
    inbox = storepath/'research_inbox'; inbox.mkdir(parents=True)
    (inbox/f'{ID}.pdf').write_bytes(pdf.read_bytes())
    (inbox/f'{ID}.json').write_bytes(sidebytes)
    store = r2_store.LocalStore(storepath)
    before = {str(p):digest(p) for p in storepath.rglob('*') if p.is_file()}
    now = datetime(2026, 10, 14, 16, 45, tzinfo=timezone.utc)
    dry = ingest.run(store, out/'dry.sqlite', now=now, dry_run=True)
    passed('dry_run_one_real_report', dry['ingested'] == 1 and dry['failed'] == 0)
    passed('dry_run_store_unchanged', before == {str(p):digest(p) for p in storepath.rglob('*') if p.is_file()})
    result = ingest.run(store, out/'local.sqlite', now=now, dry_run=False)
    passed('isolated_publish_completes', result['ingested'] == 1 and result['failed'] == 0
           and result.get('catalog_published') and result.get('corpus_published'))
    cat = json.loads(result['catalog_bytes']); item = cat['items'][0]
    passed('exact_catalog_metadata', len(cat['items']) == 1 and item['id'] == ID
           and item['pages'] == 16 and item['published_at'] == side['published_at']
           and item['summary_points'] == side['summary_points'] and item['tickers'] == [])
    with sqlite3.connect(f"file:{out/'local.sqlite'}?mode=ro", uri=True) as db:
        row = db.execute('select published_at, body from documents where doc_id=?',(ID,)).fetchone()
    passed('search_index_and_vintage', row and row[0] == side['published_at']
           and row[1] == text[:60_000] and 'imputed estimates for 2025' in row[1])
    fulltexts = list((storepath/'research_vault/fulltext').rglob('*.json'))
    passed('one_fulltext_envelope', len(fulltexts) == 1)
    fulltext = json.loads(fulltexts[0].read_text())
    passed('fulltext_retains_methodology_and_hash', fulltext['text'] == text
           and fulltext['source_pdf_sha256'] == PDF_SHA and fulltext['page_count'] == 16
           and 'non-probability' in fulltext['text']
           and fulltext['extracted_text_sha256'] == hashlib.sha256(text.encode()).hexdigest())
    again = ingest.run(store, out/'local.sqlite', now=now, dry_run=False)
    passed('same_source_idempotence', again['ingested'] == 0 and again['skipped'] == 1)
    fixture = out/'planner'; catalog = fixture/'data/research_vault/catalog.json'
    catalog.parent.mkdir(parents=True); catalog.write_bytes(result['catalog_bytes'])
    cfg = planner.load_config(repo)
    def plan(blocked=()):
        return planner.plan(['research_desk'], as_of=date(2026,10,14), root=fixture,
                            cfg=cfg, extra_blocked_refs=blocked)
    slots = plan()
    passed('research_candidate_selection', len(slots) == 1 and
           slots[0]['sources'] == ['research_vault:'+ID])
    passed('candidate_has_no_issuer', slots[0]['story']['tickers'] == [])
    passed('held_source_excluded', plan(['research_vault:'+ID]) == [])
    for name, change in [('future',{'published_at':'2026-10-15'}),
                         ('stale',{'published_at':'2026-09-01'}),
                         ('empty_summary',{'summary_points':[]})]:
        other=copy.deepcopy(cat);other['items'][0].update(change)
        catalog.write_text(json.dumps(other))
        passed(name+'_refused', plan() == [])
    catalog.write_bytes(result['catalog_bytes'])
    passed('input_bytes_and_cutover_preserved', digest(pdf) == PDF_SHA
           and sidepath.read_bytes() == sidebytes and cfg['cutover'] is False)
    proof={'checks':checks,'checks_passed':len(checks),'pdf_sha256':PDF_SHA,
           'sidecar_sha256':digest(sidepath),'candidate_slot':slots[0],
           'execution_location':'local_isolated_fixtures','provider_calls':0,
           'canonical_writes':0,'press_staging_writes':0,'publication':False}
    (out/'result.json').write_text(json.dumps(proof,indent=2)+'\n')
    print(json.dumps({'checks_passed':len(checks),'result':str(out/'result.json')}))


if __name__ == '__main__':
    main()
