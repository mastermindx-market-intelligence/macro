"""Advance the reused catalogue census from one new accepted response snapshot."""
import hashlib,json,sys
from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import urlsplit,parse_qs
E=Path('/Users/chriswong/.codex/visualizations/2026/10/11/01a12ab6-92cb-7c42-a711-42673ebb6b50/tiingo-phase1');R=Path('/Volumes/Mastermind/market-data/tiingo')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
prefix=sys.argv[1];assert prefix=='17'
prior=E/'eod-qualified-catalogue-coverage-wave14-prefix15-delta.json'
assert sha(prior)=='5deb88f8f6223bcfa3e5496d107146f3d023f55ebe258c3728ea248012518eff'
base=json.loads(prior.read_text());qpath=E/('eod-wave14-prefix'+prefix+'-qualified.json');q=json.loads(qpath.read_text())
assert q['all_selected_raw_and_reader_lineage_verified'] and q['base_coverage_sha256']=='47705a4a900d3b75cb3bfefcfa02bbe00c35010b4e563a30f47fb8c7ac7833a4'
assert q['method_sha256']=='cc5cfab5ee198d81b274f940ea89b081bb7e01e90a7b766659c1c458a96985b0' and q['run_scope_sha256']=='5a3864bfed6561da598799e3f4eccb7da3c385757e80162027716460baa862cf' and q['physical_capture_scope_sha256']=='d4522213d7a9c26f3dfba38361c2c48cff3cb12773a91e3acf9dd631d0ead31f' and q['physical_capture_plan_sha256']=='a584b99f91869de4f9bd234cae53e3374f133359d658b7c1c93e692239785e4d'
assert q['actual_physical_result_sha256']=='3b10f9f9eae457d850c497f45de4691c09d6ee6b2ac66bae459891a640367cdc' and q['selected_receipts']==1569 and q['new_disjoint_bars']==3131121 and q['source_quality_quarantined_response_count']==1
assert q['quarantined_receipt_id']=='fbc8e27fa55a315b86159989b328c73d4dc11334cbfa916e05084c310c537dbd' and q['quarantined_raw_sha256']=='fe36f5c36f07be21d1838bf09574d0a3bd46086377b3309d6c04c77d86bc06cc' and q['all_partial_artifact_hashes_unchanged'] and q['reconciliation_of_exact_remaining_scope'] and q['whole_invalid_receipt_retained_without_projection']
missing={r['ticker']:r for r in base['missing_request_windows']};added=histories=empty=count=0
for r in q['receipts']:
 assert r['source']=='eod-bars' and r['raw_checksum_verified'] and r['old_economic_dates_disjoint'] and sha(R/r['receipt_file'])==r['receipt_file_sha256']
 candidate=missing.pop(r['symbol']);params=parse_qs(urlsplit(r['request_path']).query)
 assert candidate['missing_request_windows']==[[params['startDate'][0],params['endDate'][0]]]
 count+=1;added+=r['projected_rows']
 if r['projected_rows']:
  assert r['projection_lineage_verified'];histories+=1;ex=candidate['exchange'];base['nonempty_candidates_by_exchange'][ex]=base['nonempty_candidates_by_exchange'].get(ex,0)+1
 else:assert r['raw_empty_response_verified'];empty+=1
base['accepted_nonempty_ticker_histories']+=histories;base['accepted_distinct_bars']+=added;base['projected_rows_across_receipts']+=added;base['accepted_receipts']+=count
assert base['accepted_nonempty_ticker_histories']==q['distinct_eod_histories_in_qualified_base_and_prefix'] and base['accepted_distinct_bars']==q['distinct_eod_bars_in_qualified_base_and_prefix']
diagp=E/'eod-wave14-prefix16-settled-quality-and-partial-custody-diagnosis.json';assert sha(diagp)=='72ed522bf0c81fe29bde3a61078886627f04c0616487870afc5778a72e01e7cf';diag=json.loads(diagp.read_text());bad=diag['offenders'][0];assert bad['symbol']=='RBGPF' and bad['receipt_id']==q['quarantined_receipt_id'] and bad['raw_sha256']==q['quarantined_raw_sha256'] and q['source_quality_quarantined_response_count']==1 and q['source_quality_quarantine_diagnosis_sha256']==sha(diagp)
assert bad['symbol'] in missing
candidate=missing[bad['symbol']];params=parse_qs(urlsplit(bad['request_path']).query);assert candidate['missing_request_windows']==[[params['startDate'][0],params['endDate'][0]]]
status=base['candidate_capture_status_counts'];assert status['CAPTURED_SOURCE_QUALITY_QUARANTINED']==1
status['CAPTURED_SOURCE_QUALITY_QUARANTINED']+=1;status['UNCAPTURED_CATALOGUE_WINDOW']-=1
assert base['source_quality_quarantine']['symbol']=='WTFNF'
base['additional_source_quality_quarantines']=[{'symbol':bad['symbol'],'receipt_id':bad['receipt_id'],'raw_sha256':bad['raw_sha256'],'diagnosis_sha256':sha(diagp),'raw_retained':True,'projection_admitted':False,'provider_retry_authorized':False}]
status['NONEMPTY_DESIRED_REQUEST_WINDOWS_CAPTURED']+=histories;status['CAPTURED_EMPTY_RESPONSE']+=empty;status['UNCAPTURED_CATALOGUE_WINDOW']-=count
base.update(observed_at_utc=datetime.now(timezone.utc).isoformat(),prior_census_sha256=sha(prior),incremental_delta_qualification_sha256={qpath.name:sha(qpath)},method_sha256=sha(Path(__file__)),missing_candidate_count=len(missing),missing_request_windows=list(missing.values()),all_own_raw_operations_settled=False,uncaptured_count_is_never_attempted_count=False,complete_vendor_history_proven=False)
base['accepted_qualification_files'][qpath.name]=sha(qpath)
assert status['CAPTURED_SOURCE_QUALITY_QUARANTINED']==2
assert len(missing)==status['UNCAPTURED_CATALOGUE_WINDOW']+status['CAPTURED_SOURCE_QUALITY_QUARANTINED'] and sum(status.values())==base['eligible_us_usd_stock_etf_public_catalogue_candidates']
out=E/('eod-qualified-catalogue-coverage-wave14-prefix'+prefix+'-delta.json')
with out.open('x') as f:json.dump(base,f,indent=2);f.write('\n')
print(json.dumps({'proof':str(out),'sha256':sha(out),'nonempty':base['accepted_nonempty_ticker_histories'],'bars':base['accepted_distinct_bars'],'empty':status['CAPTURED_EMPTY_RESPONSE'],'uncaptured':status['UNCAPTURED_CATALOGUE_WINDOW'],'quality_quarantined':status['CAPTURED_SOURCE_QUALITY_QUARANTINED'],'added_receipts':count,'capture_still_running':False,'physical_capture_settled':True}))
