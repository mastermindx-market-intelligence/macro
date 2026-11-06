"""Join actual later-repair acceptance; retain every original attempt fact."""
import hashlib, json, os
from pathlib import Path
from datetime import datetime, timezone

E = Path(__file__).resolve().parent
ROOT = '01a12ab6-92cb-7c42-a711-42673ebb6b50'
PINS = {
 'eod-qualified-catalogue-coverage-eleven-strict-timeout-later-repair-prefix01-delta.json': '1d7d8bb7762cde131f785a04f7490dc307d076d78a1607a2d73de408305e2b80',
 'eod-eleven-strict-timeout-later-repair-prefix01-qualified.json': '085c4147fc7e24579869398955a01242f5da6e6cdc2c3bb314dea9cbeabdf26e',
 'eod-eleven-structured-timeout-later-repair01-20261013-01a12ab6-result.json': 'f2340622f80e4edc1a998943699d749c6e2c5953b7c340cb61b12de9a2bafd7d',
 'tiingo-eleven-strict-timeout-later-repair-capture-actual-parent-consumption.json': '43ed640cca4aab2f4745b032ffc48d22cd28f83b952dd94fec990c7cd5021cf9',
 'tiingo-eleven-repair-prefix01-qualify01-actual-root-acceptance.json': '991df3da754c4b643cd322976b2785a3d5cdea90e2e2ac2196f988900a172f8b',
 'eod-wave15-original-six-phase-final-disposition-partition-accounting.json': '78974f63c410f4e39b176a487a1e790f4c78ba6f725ec240b0ab75d7b5b62d69',
 'tiingo-eleven-repair-prefix01-coverage01-launch-packet.json': 'cd0a644cd020a3d8fd88e86adf710165ec82f6849525e9a8df21d037c181cbb8',
 'tiingo-eleven-repair-prefix01-coverage01-observed-wait.json': 'ebc9291782fc8127f7e673f9dc81aedb0381e693e9386b8fd72b347184425030',
 'tiingo-eleven-repair-prefix01-coverage01-validation.json': '6e56ddedd6fc08b25083af2d29cde5ee8ed33afba9c8d8745639ec1b939b9086',
}

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def load(n): return json.loads((E/n).read_text())
def save(n, x):
 p = E/n
 with p.open('x') as f:
  json.dump(x, f, indent=2); f.write('\n'); f.flush(); os.fsync(f.fileno())

def main():
 method_at_start=sha(Path(__file__))
 for n,h in PINS.items(): assert sha(E/n)==h
 capture=load(next(n for n in PINS if 'capture-actual' in n))
 qa=load('tiingo-eleven-repair-prefix01-qualify01-actual-root-acceptance.json')
 old=load('eod-wave15-original-six-phase-final-disposition-partition-accounting.json')
 packet=load('tiingo-eleven-repair-prefix01-coverage01-launch-packet.json')
 wait=load(packet['exclusive_observed_wait_file']);val=load(packet['exclusive_validation_file'])
 assert capture['root']==qa['root']==packet['root']==ROOT
 assert capture['original_exit_code']==0 and capture['actual_original_terminal_return_consumed']
 assert qa['original_exit_code']==0 and qa['actual_original_terminal_return_consumed'] and qa['all_new_full_reader_results_equal_normalized_raw']
 assert qa['valid']==11 and qa['quality']==0 and qa['new_bars']==18366
 assert val['post_wait_validation_passed'] and val['observed_subprocess_wait_return_code']==0
 assert val['observed_wait_receipt_sha256']==PINS[packet['exclusive_observed_wait_file']]
 assert val['packet_sha256_at_launch']==PINS['tiingo-eleven-repair-prefix01-coverage01-launch-packet.json']
 cn=packet['new_output_files'][0];assert sha(E/cn)==val['output_sha256'][cn]
 census=load(cn);qn=qa['qualification_file'];assert sha(E/qn)==qa['qualification_sha256']==census['incremental_delta_qualification_sha256'][qn]==census['accepted_qualification_files'][qn]
 q=load(qn);assert len(q['receipts'])==11 and q['materialization_status_counts']=={'WRITTEN':11}
 repaired={r['symbol'] for r in q['receipts']};assert len(repaired)==11
 assert old['all_original_4392_identities_accounted_exactly_once'] and old['never_admitted_count']==0
 assert old['qualified_successes']+old['source_quality_quarantined_successes']+old['held_attempted_failure_count']==4392
 assert census['accepted_nonempty_ticker_histories']==old['global_histories']+11==47550
 assert census['accepted_distinct_bars']==old['global_bars']+18366==100592522
 status=census['candidate_capture_status_counts'];assert status=={'NONEMPTY_DESIRED_REQUEST_WINDOWS_CAPTURED':47550,'CAPTURED_EMPTY_RESPONSE':117,'UNCAPTURED_CATALOGUE_WINDOW':19,'CAPTURED_SOURCE_QUALITY_QUARANTINED':3}
 assert sum(status.values())==47689
 missing={r['ticker'] for r in census['missing_request_windows']};assert len(missing)==22 and not repaired&missing
 # The inherited census annotations describe the pre-repair attempt history.
 # Bind current annotations to the actual separate repair result, without
 # changing accepted counts, receipts, original failures or source bytes.
 result=load(capture['actual_result_file']) if 'actual_result_file' in capture else load('eod-eleven-structured-timeout-later-repair01-20261013-01a12ab6-result.json')
 assert result['prior_failures_retried'] is True and result['maximum_additional_attempts_per_request']==1 and not result['automatic_successor_repair']
 current=dict(census)
 current['delta_qualification_sha256']=sha(E/qn)
 current['failed_vendor_requests_not_retried']=not result['prior_failures_retried']
 current['known_uncaptured_attempted_candidates']=[r for r in census['known_uncaptured_attempted_candidates'] if r['ticker'] in missing]
 current.update(schema='tiingo.current_qualified_census_with_actual_later_repair/v1', observed_at_utc=datetime.now(timezone.utc).isoformat(), method_sha256=sha(Path(__file__)), original_census_file=cn, original_census_sha256=sha(E/cn), later_repair_result_sha256=sha(E/'eod-eleven-structured-timeout-later-repair01-20261013-01a12ab6-result.json'), original_failed_attempts_retained=True, all_this_repair_raw_operations_settled=True, all_this_repair_qualification_effects_accepted=True, inherited_all_programme_raw_terminal_claim_not_promoted=True, full_programme_acceptance=False)
 root={'schema':'tiingo.later_repair_actual_parent_consumption_and_conservation/v1','root':ROOT,'method_sha256':sha(Path(__file__)),'input_sha256':PINS,'actual_coverage_tool_session':None,'actual_coverage_exit_code':0,'actual_coverage_terminal_chunk':'00e490','actual_coverage_terminal_consumed':True,'immediate_terminal_no_session_id_allocated':True,'all_this_repair_pipeline_returns_consumed':True,'qualified_successes':11,'failed_requests':0,'never_admitted':0,'new_disjoint_bars':18366,'original4392_historical_accounting_sha256':PINS['eod-wave15-original-six-phase-final-disposition-partition-accounting.json'],'original4392_failure_facts_unchanged':True,'original_22925_91287_terminal_returns_not_reconstructed':True,'provider_requests':0,'archive_writes':0,'programme_acceptance':False}
 for n,h in PINS.items(): assert sha(E/n)==h
 assert sha(Path(__file__))==method_at_start
 save('eod-qualified-current-census-after-eleven-later-repair01.json',current)
 root['current_census_sha256']=sha(E/'eod-qualified-current-census-after-eleven-later-repair01.json')
 save('tiingo-eleven-later-repair-actual-final-parent-consumption.json',root)
 print(json.dumps({'histories':47550,'bars':100592522,'uncaptured':19,'current_census_sha256':root['current_census_sha256'],'parent_sha256':sha(E/'tiingo-eleven-later-repair-actual-final-parent-consumption.json'),'archive_writes':0,'provider_requests':0}))

if __name__=='__main__': main()
