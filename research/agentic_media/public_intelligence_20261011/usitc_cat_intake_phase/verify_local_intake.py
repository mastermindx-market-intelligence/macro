"""Verify the original USITC notice through isolated incumbent consumers.

Usage: python -B verify_local_intake.py REPOSITORY ORIGINAL_PDF NEW_OUTPUT
No network, provider, canonical-store or Press-stage effects are permitted.
"""
from datetime import date, datetime, timezone
from pathlib import Path
import copy
import hashlib
import json
import sqlite3
import subprocess
import sys

ID = 'usitc-2026-10-13-337-ta-1473'
PDF_SHA = '5fbe36883a69a418ff3cfd4bfe7cb0efbf63fb322d379e46344185daf6e0571e'


def digest(blob):
    return hashlib.sha256(blob).hexdigest()


def main():
    root, pdf, out = [Path(p).resolve() for p in sys.argv[1:]]
    raw = pdf.read_bytes()
    assert digest(raw) == PDF_SHA, 'source hash mismatch'
    assert not out.exists(), 'preserve prior evidence'
    sidepath = Path(__file__).with_name('usitc_cat_sidecar.json')
    sidebytes = sidepath.read_bytes()
    side = json.loads(sidebytes)
    checks = []

    def passed(name, condition):
        assert condition, name
        checks.append(name)

    def audit(event, args):
        if event in {'socket.connect', 'socket.getaddrinfo', 'socket.sendto'}:
            raise RuntimeError('network forbidden')

    sys.addaudithook(audit)
    sys.path.insert(0, str(root))
    from engine.research_vault import ingest, r2_store
    from engine.press import desk_planner as planner
    from engine.research_vault.slugs import slug_map
    text = subprocess.check_output(['pdftotext', '-layout', str(pdf), '-'], text=True)
    pages = [p for p in text.split('\f') if p.strip()]
    flat = ' '.join(text.split())
    passed('two_complete_original_pages', len(pages) == 2)
    passed('agency_and_investigation_identity', 'UNITED STATES INTERNATIONAL TRADE COMMISSION' in flat and '337-TA-1473' in flat)
    passed('actual_commission_vote_and_issue_date', 'vote for this determination took place on October 13, 2026' in flat and 'Issued: October 13, 2026' in flat)
    passed('separate_institution_date', 'On January 7, 2026' in flat)
    passed('exact_parties_and_roles', 'Doosan Bobcat North America' in flat and 'respondent Caterpillar, Inc.' in flat)
    passed('withdrawal_not_merits_disposition', 'partially terminating' in flat and 'based on withdrawal of the complaint' in flat)
    passed('motions_and_initial_determinations_dates', all(x in flat for x in ['On August 31, 2026', 'On September 4, 2026', 'On September 10, 2026', 'Order Nos. 25 and 26']))
    passed('unopposed_motions_and_no_review_petition', 'unopposed by Caterpillar' in flat and 'No party filed a petition for review of either of the two subject IDs' in flat)
    passed('four_exact_patent_identifiers', all(x in flat for x in ['7,831,364', '8,047,760', '8,364,356', '10,934,684']))
    passed('current_claim_groups_not_prior_withdrawals', 'claims 3-6 and 11 of the ʼ356 patent; claims 3-5 of the ʼ760 patent; claims 3 and 15 of the ʼ684 patent; and claims 1, 4, and 17-19 of the ʼ364 patent are hereby terminated' in flat)
    passed('earlier_august_disposition_distinct', 'On August 26, 2026' in flat)
    passed('scope_of_agreement_statement', 'no other agreements, written or oral, express or implied, between the parties concerning the subject matter of the investigation' in flat)
    passed('date_only_metadata_no_promotion', side['published_at'] == '2026-10-13' and side['top_pick'] is False)
    passed('existing_canonical_issuer_only', side['tickers'] == ['CAT'])
    passed('summary_carries_partial_and_no_merits_caveats', 'does not terminate the entire' in side['summary_points'][0] and 'not a finding that infringement occurred' in side['summary_points'][1])
    out.mkdir(parents=True)
    storepath = out/'store'
    inbox = storepath/'research_inbox'; inbox.mkdir(parents=True)
    (inbox/f'{ID}.pdf').write_bytes(raw)
    (inbox/f'{ID}.json').write_bytes(sidebytes)
    store = r2_store.LocalStore(storepath)
    before = {str(p): digest(p.read_bytes()) for p in storepath.rglob('*') if p.is_file()}
    now = datetime(2026, 10, 14, 17, 30, tzinfo=timezone.utc)
    dry = ingest.run(store, out/'dry.sqlite', now=now, dry_run=True)
    passed('existing_ingester_dry_run', dry['ingested'] == 1 and dry['failed'] == 0)
    passed('dry_store_unchanged', before == {str(p): digest(p.read_bytes()) for p in storepath.rglob('*') if p.is_file()})
    result = ingest.run(store, out/'corpus.sqlite', now=now, dry_run=False)
    passed('isolated_ingest_and_publication', result['ingested'] == 1 and result['failed'] == 0 and result['catalog_published'] and result['corpus_published'])
    cat = json.loads(result['catalog_bytes']); row = cat['items'][0]
    passed('exact_catalog', row['title'] == side['title'] and len(cat['items']) == 1 and row['id'] == ID and row['pages'] == 2 and row['published_at'] == side['published_at'] and row['tickers'] == ['CAT'] and row['summary_points'] == side['summary_points'])
    with sqlite3.connect(f"file:{out/'corpus.sqlite'}?mode=ro", uri=True) as db:
        stored = db.execute('SELECT published_at,body FROM documents WHERE doc_id=?', (ID,)).fetchone()
    passed('exact_index_text_and_vintage', stored == (side['published_at'], text))
    records = list((storepath/'research_vault/fulltext').rglob('*.json'))
    passed('single_fulltext', len(records) == 1)
    fulltext = json.loads(records[0].read_bytes())
    passed('exact_fulltext_and_source_binding', fulltext['text'] == text and fulltext['source_pdf_sha256'] == PDF_SHA and fulltext['page_count'] == 2)
    again = ingest.run(store, out/'corpus.sqlite', now=now, dry_run=False)
    passed('same_source_idempotence', again['ingested'] == 0 and again['skipped'] == 1)
    fixture = out/'planner'; catalog = fixture/'data/research_vault/catalog.json'
    catalog.parent.mkdir(parents=True); catalog.write_bytes(result['catalog_bytes'])
    cfg = planner.load_config(root)
    def plan(blocked=()):
        return planner.plan(['research_desk'], root=fixture, cfg=cfg, as_of=date(2026,10,14), extra_blocked_refs=blocked)
    slots = plan()
    passed('isolated_research_selection', len(slots) == 1 and slots[0]['sources'] == ['research_vault:'+ID])
    passed('held_source_refuses', plan(['research_vault:'+ID]) == [])
    for label, changes in [('future', {'published_at':'2026-10-15'}), ('stale', {'published_at':'2026-09-01'}), ('empty', {'summary_points':[]})]:
        variant = copy.deepcopy(cat); variant['items'][0].update(changes); catalog.write_text(json.dumps(variant))
        passed(label+'_refuses', plan() == [])
    catalog.write_bytes(result['catalog_bytes'])
    passed('original_inputs_and_cutover_unchanged', pdf.read_bytes() == raw and sidepath.read_bytes() == sidebytes and cfg['cutover'] is False)
    proof = {'checks':checks, 'passed':len(checks), 'source_id':ID, 'pdf_sha256':PDF_SHA, 'sidecar_sha256':digest(sidebytes), 'slug':slug_map([row])[ID], 'candidate_slot':slots[0], 'provider_calls':0, 'canonical_writes':0, 'press_staging_writes':0, 'publication':False, 'execution':'isolated_local_fixtures'}
    (out/'result.json').write_text(json.dumps(proof,indent=2)+'\n')
    print(json.dumps({'passed':len(checks),'result':str(out/'result.json')}))


if __name__ == '__main__':
    main()
