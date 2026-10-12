import sys,json,hashlib
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import parse_qs,urlsplit
sys.path.insert(0,'/Volumes/Mastermind/agent-workspaces/sol/tiingo-ingestion-20261009')
from collectors.tiingo_archive import validate_receipt
from scripts.tiingo_materialize import verified_raw
from lib.dataos.tiingo_reader import read_research_view,read_research_statement_timeline
E=Path('/Users/chriswong/.codex/visualizations/2026/10/11/01a12ab6-92cb-7c42-a711-42673ebb6b50/tiingo-phase1'); R=Path('/Volumes/Mastermind/market-data/tiingo')
scope=json.loads((E/'aapl-deep-fundamentals-scope.json').read_text()); cutoff=datetime.now(timezone.utc).isoformat(); rows=[]; variants={}
for source in ('fund-statements','fund-daily'):
 for p in sorted((R/'receipts'/source).rglob('*.json')):
  receipt=json.loads(p.read_text())
  if receipt['observed_at_utc'] < scope['observed_at_utc']:continue
  assert receipt['symbol']=='AAPL'; identity=validate_receipt(receipt); raw=verified_raw(R,receipt); view=read_research_view(source,receipt['observed_at_utc'][:10],identity,root=R,max_rows=1000000)
  assert all(x['source_receipt_id']==identity and x['source_sha256']==receipt['raw_sha256'] for x in view.rows)
  dates=[x['statement_public_release_date_vendor'] if source=='fund-statements' else x['market_date'] for x in view.rows]
  assert dates and min(dates)[:10]>=scope['requested_start'] and max(dates)[:10]<=scope['requested_end']
  record={'source':source,'receipt_path':str(p.relative_to(R)),'receipt_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'receipt_id':identity,'raw_sha256':receipt['raw_sha256'],'http_status':receipt['http_status'],'original_capture_utc':receipt['observed_at_utc'],'raw_bytes':len(raw),'raw_records':len(json.loads(raw)),'projected_rows':len(view.rows),'first_returned_date':min(dates),'last_returned_date':max(dates),'raw_and_row_lineage_verified':True}
  if source=='fund-statements':
   variant=parse_qs(urlsplit(receipt['request_path']).query)['asReported'][0]; assert variant in ('true','false') and variant not in variants
   timeline=read_research_statement_timeline('AAPL',[(receipt['observed_at_utc'][:10],identity)],scope['requested_start'],scope['requested_end'],cutoff,as_reported=variant=='true',root=R,acknowledge_hindsight=True,max_rows=1000000)
   record['timeline_metadata']=timeline.metadata(); variants[variant]=view.rows
  rows.append(record)
assert len(rows)==3 and set(variants)=={'true','false'}
def key(x):return (x['fiscal_year'],x['fiscal_quarter'],x['statement_type'],x['metric_code'])
a={key(x):x['metric_value'] for x in variants['true']}; b={key(x):x['metric_value'] for x in variants['false']}; common=set(a)&set(b)
proof={'schema':'tiingo_deep_fundamentals_qualification.v1','observed_at_utc':cutoff,'requested_start':scope['requested_start'],'requested_end':scope['requested_end'],'receipts':rows,'common_fiscal_metrics':len(common),'different_fiscal_metrics':sum(a[k]!=b[k] for k in common),'method_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'all_three_raw_and_projected_receipts_verified':True,'full_history_completeness':False,'canonical_identity_admitted':False,'historical_known_at_proven':False,'pit_backtest_eligible':False,'other_ticker_entitlements_inferred':False}
(E/'aapl-deep-fundamentals-qualified.json').write_text(json.dumps(proof,indent=2,sort_keys=True)+'\n'); print(json.dumps(proof,indent=2,sort_keys=True))
