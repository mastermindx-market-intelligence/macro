import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, '/Volumes/Mastermind/agent-workspaces/sol/tiingo-ingestion-20261009')
from scripts.tiingo_corpus_audit import audit_corpus
from scripts.tiingo_ingest import Task

evidence = Path('/Users/chriswong/.codex/visualizations/2026/10/11/01a12ab6-92cb-7c42-a711-42673ebb6b50/tiingo-phase1')
selection = json.loads((evidence / 'eod-1000-wave4-candidates.json').read_text())
tasks = [Task('eod-bars', r['ticker'], {'startDate': r['request_start'], 'endDate': r['request_end']})
         for r in selection['selected']]
assert len(tasks) == 1000
result = audit_corpus(tasks, observed_before=datetime.now(timezone.utc).isoformat(),
                      max_receipts=5500, read_budget=1024**3, detail_limit=1000)
(evidence / 'eod-1000-wave4-partial-corpus-audit.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
print(json.dumps({k: result[k] for k in ('observed_before_utc', 'expected_requests', 'plan_sha256',
                                       'all_receipts_inspected', 'request_status_counts', 'scan')}, indent=2))
assert result['all_receipts_inspected']
assert 825 <= sum(result['request_status_counts'].get(k, 0) for k in ('RAW_RECORDS_CAPTURED', 'EMPTY_CAPTURED')) < 1000
assert result['scan'].get('invalid_receipts_or_payloads', 0) == 0
