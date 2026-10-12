import json,sys
from datetime import datetime,timezone
from pathlib import Path
sys.path.insert(0,'/Volumes/Mastermind/agent-workspaces/sol/tiingo-ingestion-20261009')
from scripts.tiingo_corpus_audit import audit_corpus
from scripts.tiingo_ingest import Task
e=Path('/Users/chriswong/.codex/visualizations/2026/10/11/01a12ab6-92cb-7c42-a711-42673ebb6b50/tiingo-phase1')
s=json.loads((e/'eod-1000-wave4-candidates.json').read_text())
tasks=[Task('eod-bars',r['ticker'],{'startDate':r['request_start'],'endDate':r['request_end']}) for r in s['selected']]
assert len(tasks)==1000
result=audit_corpus(tasks,observed_before=datetime.now(timezone.utc).isoformat(),max_receipts=5500,read_budget=1024**3,detail_limit=1000)
(e/'eod-wave4-final-exact-audit.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
print(json.dumps({k:result[k] for k in ['observed_before_utc','expected_requests','plan_sha256','all_receipts_inspected','request_status_counts','scan']},indent=2))
assert result['plan_sha256']=='8a4f60518d5b5c013ed7faa6e2f6386f35d8ac9e58e72d2b7bdaedf515083530'
assert result['all_receipts_inspected']
assert sum(result['request_status_counts'].get(k,0) for k in ['RAW_RECORDS_CAPTURED','EMPTY_CAPTURED'])==999
assert result['request_status_counts'].get('NOT_FOUND',0)==1
missing=[r for r in result['requests'] if r['status']=='NOT_FOUND']
assert len(missing)==1 and missing[0]['symbol']=='BAFE'
assert result['scan'].get('invalid_receipts_or_payloads',0)==0
