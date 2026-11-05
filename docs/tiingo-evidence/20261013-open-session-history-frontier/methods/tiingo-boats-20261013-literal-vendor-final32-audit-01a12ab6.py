"""One bounded read-only tape audit using actual vendor ticker spellings."""
import json,hashlib,sys,os,subprocess
from pathlib import Path
from datetime import datetime,timezone
C=Path('/Volumes/Mastermind/agent-workspaces/sol/tiingo-ingestion-20261009');R=Path('/Volumes/Mastermind/market-data/tiingo');E=Path('/Users/chriswong/.codex/visualizations/2026/10/11/01a12ab6-92cb-7c42-a711-42673ebb6b50/tiingo-phase1');sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert os.environ.get('CODEX_THREAD_ID')=='01a12ab6-92cb-7c42-a711-42673ebb6b50'
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=C,text=True).strip()=='2a08250fe61aa59ad3e1581149f0b93e9d5a17cf'
for rel,h in {'lib/dataos/tiingo_boats_tape.py':'98f3f3768edfc109ae645671bb217a2ea9673afcf78ccc787836310d09443db5','lib/dataos/tiingo_reader.py':'fb7a2834f37f2e1c76e00250ea5c60a9cdbab73c598a855e37e1b8a54672e976','lib/dataos/temporal.py':'4415404186f0b0d2870f42d9e4a0b95be87937863adf30cf015ed34e8bf92b67'}.items():assert sha(C/rel)==h
p=E/'tiingo-boats-raw-20261013-01a12ab6-qualified.json';assert sha(p)=='8bea6d46a5fbff25b441814bb18a360e6bd4b3edcfb2b28b9e6555ab9e035c0e';q=json.loads(p.read_text())
a=E/'tiingo-boats-20261013-actual-raw-reader-parent-acceptance.json';assert sha(a)=='f390a4bc160674bdd37582c45d03ceb5b01e7ad82bc3a22192a1c3a2cf65d95b';accepted=json.loads(a.read_text());assert accepted['original_tool_session_id']==48859 and accepted['original_terminal_return_consumed'] and accepted['original_exit_code']==0 and accepted['all_original_raw_and_reader_lineage_accepted']
d=E/'tiingo-boats-20261013-actual-vendor-selector-case-diagnosis.json';assert sha(d)=='e21afeecc0df6b87ab13a989c4cdacd24eacfec0c6e4d89227c216cda59404af';diagnosis=json.loads(d.read_text())
records=q['selected_receipts'][-32:];assert len(records)==32 and [r['receipt_path'] for r in records]==diagnosis['receipt_paths']
for r in records:assert sha(R/r['receipt_path'])==r['receipt_sha256'] and r['raw_verified'] and r['reader_lineage_verified']
scope=json.loads((E/'tiingo-boats-raw-20261013-01a12ab6-scope.json').read_text());settled=json.loads((E/'tiingo-boats-raw-20261013-01a12ab6-result.json').read_text());assert sha(E/'tiingo-boats-raw-20261013-01a12ab6-scope.json')==q['scope_sha256'] and sha(E/'tiingo-boats-raw-20261013-01a12ab6-result.json')==q['actual_settlement_sha256']
refs=[(r['first_received_at_utc'][:10],r['raw_sha256']) for r in records];sys.path.insert(0,str(C));from lib.dataos.tiingo_boats_tape import audit_boats_tape
out=E/'tiingo-boats-20261013-literal-vendor-final32-tape-audit.json';assert not out.exists();cutoff=datetime.now(timezone.utc).isoformat();reports={}
for symbol in ('aapl','msft','amzn','googl','meta','nvda','tsla','spy','qqq'):
 report=audit_boats_tape(refs,vendor_symbol=symbol,start_event_at_utc=scope['started_at_utc'],end_event_at_utc=settled['settled_at_utc'],observed_before_utc=cutoff,root=R,max_captures=32,max_events_per_capture=2000,max_observations=100000,max_examples=0)
 assert report['vendor_symbol']==symbol and report['raw_source_bytes_reverified'] and report['source_message_projection_reverified'] and not report['network'] and not report['writes'] and not report['key_read']
 assert 0<=report['selected_symbol_events']<=sum(diagnosis['actual_literal_lowercase_vendor_events_in_selected_chunk'][symbol].values())
 reports[symbol]=report
proof={'schema':'tiingo.actual_literal_vendor_bounded_tape_audit/v1','method_sha256':sha(__file__),'accepted_original_qualified_proof_sha256':sha(p),'actual_parent_acceptance_sha256':sha(a),'actual_case_diagnosis_sha256':sha(d),'observed_before_utc':cutoff,'recorded_after_audit_utc':datetime.now(timezone.utc).isoformat(),'selection':'final32 receipts of actual original2000000-message capture','receipt_count':32,'selected_receipt_sha256':{r['receipt_path']:r['receipt_sha256'] for r in records},'actual_literal_vendor_spellings':list(reports),'reports':reports,'event_window_filter_can_reduce_raw_reader_counts':True,'original_uppercase_zero_match_reports_preserved':True,'source_or_research_symbol_mutation':False,'alias_or_canonical_identity_admission':False,'full_session_or_cross_chunk_continuity':False,'provider_requests':0,'archive_or_materialization_writes':0,'publication_or_production_acceptance':False}
with out.open('x') as f:f.write(json.dumps(proof,indent=2,sort_keys=True)+'\n')
print(json.dumps({'proof_sha256':sha(out),'receipt_count':32,'selected_events':{k:v['selected_symbol_events'] for k,v in reports.items()},'archive_writes':0,'provider_requests':0,'publication':False}))
