import hashlib, json, os, shutil, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

SOURCE = Path('/Volumes/Mastermind/agent-workspaces/sol/tiingo-ingestion-20261009')
ROOT = Path('/Volumes/Mastermind/market-data/tiingo')
OUT = Path('/Users/chriswong/.codex/visualizations/2026/10/11/01a12ab6-92cb-7c42-a711-42673ebb6b50/tiingo-phase1')
RUN = 'tiingo-boats-raw-20261013-01a12ab6'
THREAD = '01a12ab6-92cb-7c42-a711-42673ebb6b50'
EXPECTED = {'scripts/tiingo_ingest.py':'ef52fd2f90842c85a362254dae219a2593fed024b340a38fa5333a50e06981e6', 'collectors/tiingo_archive.py':'54b694af53a940f8ea1148215b0a3ccfcfa5313270286b04a99c72d7dc004fa6'}
now = datetime.now(timezone.utc)
assert ('--preflight' in sys.argv or datetime(2026,10,13,0,0,tzinfo=timezone.utc) <= now < datetime(2026,10,13,0,15,tzinfo=timezone.utc)), 'raw capture only during the intended real window'
assert os.environ.get('CODEX_THREAD_ID') == THREAD
assert not (OUT / (RUN + '-scope.json')).exists(), 'existing operation must be reconciled, never replayed'
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=SOURCE,text=True).strip() == '2a08250fe61aa59ad3e1581149f0b93e9d5a17cf'
for rel, sha in EXPECTED.items(): assert hashlib.sha256((SOURCE/rel).read_bytes()).hexdigest() == sha
assert json.loads((OUT/'eod-wave5-final-qualified-archive.json').read_text())['all_eod_raw_and_projection_lineage_verified']
assert json.loads((OUT/'aapl-deep-fundamentals-collection.json').read_text())['failed'] == 0, 'prior own REST capture must have settled'
for parent in (ROOT, ROOT/'raw', ROOT/'receipts'):
    assert parent.is_dir() and not parent.is_symlink() and parent.resolve().is_relative_to(ROOT.resolve())
existing = sorted((ROOT/'receipts'/'boats-firehose').rglob('*.json'))
assert len(existing) == 22, 'new BOATS custody evidence requires reconciliation before launch'
prior = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in existing}
baseline_path=OUT/'tiingo-boats-20261013-prior-partition-binding.json'
assert hashlib.sha256(baseline_path.read_bytes()).hexdigest()=='12af3577d0c1591457b2a051c997cbb03922db02ddf929de929a723b84146998'
baseline=json.loads(baseline_path.read_text());assert prior==baseline['prior_receipt_sha256']
prior_result=OUT/'tiingo-boats-raw-20261012-01a12ab6-result.json';assert hashlib.sha256(prior_result.read_bytes()).hexdigest()==baseline['prior_finite_result_sha256']
assert json.loads(prior_result.read_text())['connections']==1 and json.loads(prior_result.read_text())['raw_messages']==20000
sys.path.insert(0,'/private/tmp/tiingo-boats-runtime-01a12ab6/lib/python3.14/site-packages')
sys.path.insert(0,str(SOURCE))
from collectors.tiingo_archive import Archive, require_space, TiingoArchiveError
from scripts.tiingo_ingest import boats_stream
require_space(ROOT,floor=40*1024**3)
if '--preflight' in sys.argv:
    print(json.dumps({'source_pins_verified':True,'prior_receipts_verified':22,'prior_finite_result_settled':True,'new_provider_requests':0,'credentials_read':False,'real_venue_window_required_for_capture':True}));raise SystemExit(0)
scope = {'schema':'tiingo_attended_raw_boats_scope.v1','run_id':RUN,'owner_thread':THREAD,'started_at_utc':now.isoformat(),'loaded_source_sha256':EXPECTED,'source_head':'2a08250fe61aa59ad3e1581149f0b93e9d5a17cf','max_seconds':600,'max_messages':2000000,'start_admission_window_utc':['2026-10-13T00:00:00+00:00','2026-10-13T00:15:00+00:00'],'admission_window_is_not_end_deadline':True,'archived_byte_stop_threshold':2*1024**3,'byte_threshold_checked_after_immutable_archive_write':True,'hard_byte_ceiling_claimed':False,'single_frame_size_bound_proven':False,'first_gap_stops_without_reconnection':True,'batch_messages':1000,'flush_seconds':5,'free_reserve_gib':35,'inflight_headroom_gib':5,'method_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'prior_partition_binding_sha256':hashlib.sha256(baseline_path.read_bytes()).hexdigest(),'preflight_free_gib':shutil.disk_usage(ROOT).free/1024**3,'prior_boats_receipts':prior,'archive_partition':'boats-firehose only','independent_intraday_partition_preserved':True,'stable_ancestors_required':True,'no_conflicting_boats_owner_identified':True,'universal_process_absence_proven':False,'provider_connection_not_yet_proven':True,'r2_publication':False,'persistent_runtime_change':False,'complete_session_coverage':False,'production_consumer_acceptance':False}
with (OUT/(RUN+'-scope.json')).open('x') as f:f.write(json.dumps(scope,indent=2,sort_keys=True)+'\n')
print(json.dumps(scope,sort_keys=True),flush=True)
class AttendedBOATSStop(TiingoArchiveError):
    pass
state={'archived_bytes':0,'archived_segments':0,'last_segment_bytes':0,'stop_reason':None}
def stop_once(reason):
    if state['stop_reason'] is None:
        state['stop_reason']=reason
        raise AttendedBOATSStop('Attended BOATS capture stopped; reconcile original receipts')
def observe(kind,payload):
    if kind=='archived':
        saved=payload['receipt'];size=saved['raw_bytes'];assert isinstance(size,int) and size>=0
        state['archived_bytes']+=size;state['last_segment_bytes']=size;state['archived_segments']+=int(saved['new_raw'])
    if state['stop_reason'] is not None:
        return  # Cleanup may archive buffered raw data; count it without another stop exception.
    if kind=='gap':
        stop_once('first_transport_gap_or_handshake_refusal')
    if kind in ('connected','archived','tick'):
        try:require_space(ROOT,floor=40*1024**3)
        except TiingoArchiveError:stop_once('resource_admission_floor_reached')
    if kind=='archived' and state['archived_bytes']>=2*1024**3:
        stop_once('archived_byte_stop_threshold')
try:
    connection_now=datetime.now(timezone.utc)
    assert datetime(2026,10,13,0,0,tzinfo=timezone.utc)<=connection_now<datetime(2026,10,13,0,15,tzinfo=timezone.utc)
    result = boats_stream(max_seconds=600,max_messages=2000000,batch_messages=1000,flush_seconds=5,archive=Archive(),observer=observe)
    assert result['bytes']==state['archived_bytes'] and result['segments']==state['archived_segments']
except Exception as exc:
    failure={'schema':'tiingo_attended_raw_boats_failure.v1','run_id':RUN,'settled_at_utc':datetime.now(timezone.utc).isoformat(),'exception_type':type(exc).__name__,'observer_outcome':state,'original_receipt_reconciliation_required':True,'partial_archive_preserved':True,'r2_publication':False,'acceptance':False}
    with (OUT/(RUN+'-failure.json')).open('x') as f:f.write(json.dumps(failure,indent=2,sort_keys=True)+'\n')
    print(json.dumps(failure,sort_keys=True),flush=True)
    raise SystemExit(1)
result={'schema':'tiingo_attended_raw_boats_result.v1','run_id':RUN,'settled_at_utc':datetime.now(timezone.utc).isoformat(),**result,'observer_outcome':state,'first_gap_stops_without_reconnection':True,'r2_publication':False,'acceptance_requires_original_raw_and_receipt_audit':True,'full_session_coverage':False,'production_consumer_acceptance':False}
with (OUT/(RUN+'-result.json')).open('x') as f:f.write(json.dumps(result,indent=2,sort_keys=True)+'\n')
print(json.dumps(result,sort_keys=True),flush=True)
