from pathlib import Path
from copy import deepcopy
from datetime import date
import json
import pytest
from engine.company_intelligence import defense_profiles as profiles
from engine.company_intelligence.event_workspace_build import build_event_workspace
from engine.company_intelligence.event_workspace import write_workspace_generation
from engine.company_intelligence.identity import IssuerRegistry
from engine.earnings_release.binding import bind_release_document
from engine.company_intelligence.documents import verify_span, SourceSpan
from engine.government_revenue.defense_economics_producer import build_defense_economics_payload, load_defense_owner_snapshot

FIXTURES=Path(__file__).with_name('fixtures')/'company_intelligence'/'defense'


def make_workspace(ticker,*,observed='2026-10-13T03:03:46Z',prior=None):
    filing=json.loads((FIXTURES/(ticker+'.filing.json')).read_text())
    body=(FIXTURES/(ticker+'.segment.html')).read_text()
    bound=bind_release_document(body=body,**filing)
    return build_event_workspace(registry=IssuerRegistry(profiles.defense_issuer(t) for t in profiles.DEFENSE_TICKERS),
        ticker=ticker,asof=date.fromisoformat(filing['filing_date']),fiscal_period=profiles.source_fiscal_period(bound,ticker),
        exhibit_body=body,filing=filing,transcript=None,observed_at=observed,
        source_available_at=filing['acceptance_datetime'],profile=profiles.defense_profile(ticker),
        prior_source_sha256=prior['sources'][0]['source_sha256'] if prior else None,
        prior_observed_at=prior['lifecycle']['observed_at'] if prior else None,
        prior_lifecycle_state=prior['lifecycle']['state'] if prior else None)


def snapshot_root(tmp_path):
    rows={}
    for ticker in profiles.DEFENSE_TICKERS:
        w=make_workspace(ticker);rows[w['event_id']]=w
    write_workspace_generation(tmp_path/'data/company_intelligence',rows)
    return tmp_path


def test_quartet_reported_segment_literals_through_owner_writer_and_pure_reader(tmp_path):
    root=snapshot_root(tmp_path)
    result=build_defense_economics_payload(root,generated_at='2026-10-13T04:00:00Z')
    expected=[(4101,594,14.5),(8269,1042,12.6),(2093,156,7.5),(1054,12.3)]
    for row,values in zip(result['profiles'],expected):
        assert tuple(f['value'] for f in row['axes']['economics']['facts'])==values
        assert row['axes']['participation']['state']=='missing_owner'
        assert row['program_workshare'] is None
        assert row['shareholder_capture']['state']=='not_asserted'
        assert row['contrary_case_zh']
    assert result['profiles'][3]['axes']['economics']['state']=='partial'


def test_owner_profile_replays_each_numeric_span_and_refuses_source_drift():
    ws=make_workspace('RTX');body=(FIXTURES/'RTX.segment.html').read_text()
    for fact in ws['facts']:
        if fact['metric'] not in profiles.METRICS or fact.get('typed_absence'):continue
        p=fact['source_span'];span=SourceSpan(document_id=p['document_id'],document_version=p['document_version'],locator=p['locator'],text_sha256=p['text_sha256'],display_excerpt=p['display_excerpt'],rights_profile=p['rights_profile'],receipt_state=p['receipt_state'],receipt=p['receipt'],span_id=p['span_id'])
        verify_span(span,segment_text=body,body_sha256=ws['sources'][0]['source_sha256'])
        with pytest.raises(ValueError):verify_span(span,segment_text=body+'x',body_sha256=ws['sources'][0]['source_sha256'])


def test_unchanged_source_preserves_owner_first_observation():
    old=make_workspace('LMT');new=make_workspace('LMT',observed='2026-10-14T00:00:00Z',prior=old)
    assert new['lifecycle']['observed_at']==old['lifecycle']['observed_at']


def test_owner_value_tampering_cannot_quote_a_numeric_claim(tmp_path):
    root=snapshot_root(tmp_path);owner=load_defense_owner_snapshot(root)
    for held in owner['rows'].values():
        if held['workspace']['issuer']['company_id']==profiles.defense_issuer('RTX').company_id:
            next(f for f in held['workspace']['facts'] if f['metric']=='defense_segment_operating_profit')['value']=1043
    from engine.company_intelligence.contracts import canonical_json_bytes
    from hashlib import sha256
    for event_id,held in owner['rows'].items():
        held['sha256']=sha256(canonical_json_bytes(held['workspace'])).hexdigest()
        owner['manifest']['files']['workspaces/'+event_id+'.json']['sha256']=held['sha256']
    owner['manifest_sha256']=sha256(canonical_json_bytes(owner['manifest'])).hexdigest()
    with pytest.raises(ValueError,match='literal'):build_defense_economics_payload(root,generated_at='2026-10-13T04:00:00Z',owner_inputs=owner)


def test_owner_disk_hash_and_document_subject_mismatch_fail_closed(tmp_path):
    root=snapshot_root(tmp_path);owner=load_defense_owner_snapshot(root)
    held=next(iter(owner['rows'].values()));fact=next(f for f in held['workspace']['facts'] if f['metric'] in profiles.METRICS and not f.get('typed_absence'))
    fact['source_span']['document_id']='different_document'
    from engine.company_intelligence.contracts import canonical_json_bytes
    from hashlib import sha256
    event_id=held['workspace']['event_id'];held['sha256']=sha256(canonical_json_bytes(held['workspace'])).hexdigest();owner['manifest']['files']['workspaces/'+event_id+'.json']['sha256']=held['sha256']
    owner['manifest_sha256']=sha256(canonical_json_bytes(owner['manifest'])).hexdigest()
    with pytest.raises(ValueError,match='document'):build_defense_economics_payload(root,generated_at='2026-10-13T04:00:00Z',owner_inputs=owner)
    marker=owner['manifest'];relative=next(iter(marker['files']));p=root/'data/company_intelligence/event_workspaces/generations'/marker['generation_id']/relative;p.write_bytes(p.read_bytes()+b' ')
    with pytest.raises(ValueError,match='hash'):load_defense_owner_snapshot(root)


def test_missing_owner_and_pre_observation_cutoff_withhold_facts(tmp_path):
    assert all(p['axes']['economics']['state']=='unreviewed' for p in build_defense_economics_payload(tmp_path,generated_at='2026-10-13T04:00:00Z')['profiles'])
    root=snapshot_root(tmp_path)
    assert all(not p['axes']['economics']['facts'] for p in build_defense_economics_payload(root,generated_at='2026-10-13T04:00:00Z',as_of='2026-10-12T00:00:00Z')['profiles'])


def test_aged_owner_facts_remain_visible_without_inventing_freshness_policy(tmp_path):
    root=snapshot_root(tmp_path)
    stale=build_defense_economics_payload(root,generated_at='2026-11-13T04:00:00Z')
    assert all(p['axes']['economics']['state'] in ('supported','partial') and p['axes']['economics']['facts'] for p in stale['profiles'])
    a=build_defense_economics_payload(root,generated_at='2026-10-13T04:00:00Z')
    b=build_defense_economics_payload(root,generated_at='2026-10-13T05:00:00Z')
    assert a['content_id']==b['content_id']


def test_partial_explicit_snapshot_and_manifest_hash_are_not_owner_admission(tmp_path):
    root=snapshot_root(tmp_path);owner=load_defense_owner_snapshot(root)
    partial=deepcopy(owner);partial['rows'].pop(next(iter(partial['rows'])))
    with pytest.raises(ValueError,match='incomplete'):build_defense_economics_payload(root,generated_at='2026-10-13T04:00:00Z',owner_inputs=partial)
    owner['manifest_sha256']='0'*64
    with pytest.raises(ValueError,match='manifest_hash'):build_defense_economics_payload(root,generated_at='2026-10-13T04:00:00Z',owner_inputs=owner)


def projected_mutation(ticker,mutate):
    filing=json.loads((FIXTURES/(ticker+'.filing.json')).read_text())
    original=(FIXTURES/(ticker+'.segment.html')).read_text()
    normal=bind_release_document(body=original,**filing)
    changed=bind_release_document(body=mutate(original),**filing)
    return profiles.extract_segment_facts(ticker=ticker,bound=changed,document_id=changed.revision.document_id,
        event_id='mutation:'+ticker,fiscal_period=profiles.source_fiscal_period(normal,ticker))


def test_swapped_reported_adjusted_headers_refuse_current_financial_admission():
    def swap(body):return body.replace('Reported','__BASIS__').replace('Adjusted','Reported').replace('__BASIS__','Adjusted')
    assert all(f.get('typed_absence') for f in projected_mutation('RTX',swap))


@pytest.mark.parametrize('ticker',profiles.DEFENSE_TICKERS)
def test_comparative_current_year_header_swap_never_quotes_first_numeric_cell(ticker):
    def swap(body):return body.replace('2026','__YEAR__').replace('2025','2026').replace('__YEAR__','2025')
    assert all(f.get('typed_absence') for f in projected_mutation(ticker,swap))


def test_negative_reported_amount_preserves_literal_sign_and_receipt():
    def negative(body):
        assert '>594<' in body
        return body.replace('>594<','>(594)<',1)
    facts=projected_mutation('LMT',negative)
    fact=next(f for f in facts if f['metric']=='defense_segment_operating_profit')
    assert fact['value']==-594 and fact['source_span']['display_excerpt']=='(594)'
    assert fact['source_span']['receipt_state']=='byte_replayed'


def test_split_sign_or_displaced_value_is_not_silently_positive():
    def split(body):return body.replace('>594<','>-<',1)
    fact=next(f for f in projected_mutation('LMT',split) if f['metric']=='defense_segment_operating_profit')
    assert fact.get('typed_absence')
