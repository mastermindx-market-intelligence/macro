"""Research-package verification only; no product admission or trading logic.

Default: verifies the documented catalog and the hash-bound diagnostic summary.
Optional --snapshot checks the exact previously recovered native file through the
one-file inspection helper. Obtain native bytes through an authorized owner; this
package does not distribute them. A standard-engine cross-check is still owed.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXPECTED_BLOB = '01a732f8e4d5db94011957797b9df9ba1c865aa3'
EXPECTED_SHA256 = '4392e814502723b988629ea759311192fb1c7d77eb2274c654c0a6d4bde1425e'

def git_blob(b: bytes) -> str:
    return hashlib.sha1(b'blob ' + str(len(b)).encode() + b'\0' + b).hexdigest()

def catalog_rows(text: str) -> list[dict[str,str]]:
    rows = []
    fields = ('task_id','investor_question','evidence_and_boundary','useful_output_and_falsifier','prior_research_and_consumer')
    for line in text.splitlines():
        if re.match(r'^\| W9-J\d\d \|', line):
            values = [v.strip() for v in line.strip('|').split('|')]
            if len(values) != len(fields):
                raise ValueError('catalog row shape mismatch')
            rows.append(dict(zip(fields, values)))
    return rows

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--snapshot', type=Path, help='Optional exact native earnings.parquet; never writes it')
    args = ap.parse_args()
    checks = []
    def check(name: str, condition: bool) -> None:
        checks.append({'name':name,'passed':bool(condition)})
    cat_path=ROOT/'INDUSTRIALS_WAVE9_RESEARCH_TO_PRODUCT_CATALOG_2026-09-23.md'
    cat=cat_path.read_text(); audit=(ROOT/'INDUSTRIALS_WAVE9_HISTORICAL_DATA_AUDIT_2026-09-23.md').read_text()
    rows=catalog_rows(cat)
    check('24 unique, fully specified investor tasks', len(rows)==24 and len({r['task_id'] for r in rows})==24 and all(all(r.values()) for r in rows))
    check('task IDs continuous', [r['task_id'] for r in rows]==[f'W9-J{i:02}' for i in range(1,25)])
    check('six complete dossier headings', re.findall(r'^### (W9-D\d\d)',cat,re.M)==[f'W9-D{i:02}' for i in range(1,7)])
    check('30 distinct proposed requirements', re.findall(r'^\| (W9-T\d\d) \|',cat,re.M)==[f'W9-T{i:02}' for i in range(1,31)])
    check('all eight waves referenced', all(f'W{i}' in cat for i in range(1,9)))
    check('current operation in both documents', all('gmi-industrials-sector-research-20260923-sol-001' in x for x in (cat,audit)))
    check('same research carrier in both documents', all('sol/industrials-sector-research-20260923' in x for x in (cat,audit)))
    check('same protected procedure pin', all('a7d2b3049e5cdc523e91e61a6e9d70a1cb911157' in x for x in (cat,audit)))
    check('missing estimate basis cannot become beat', 'must not certify a beat' in cat and 'does not certify their comparison' in audit)
    check('no raw snapshot publication claimed', 'excluded from this public research publication and the portable package' in audit)
    check('proposal and final handoff boundaries explicit', 'not the final Fable CEO implementation handoff' in cat and 'Do not issue the final Fable implementation handoff yet' in cat)
    check('held-out distinction retained', 'development cases' in cat and 'eight-company set is a feasibility sample' in cat)
    check('schema proposed, not silently live', 'does not prove schema enrollment' in cat)
    check('raw Git blob and SHA256 in audit', EXPECTED_BLOB in audit and EXPECTED_SHA256 in audit)
    check('calendar age derived independently', (date(2026,7,28)-date(2026,6,19)).days==39 and (date(2026,7,30)-date(2026,6,19)).days==41)
    summary=json.loads((ROOT/'WAVE9_SNAPSHOT_DIAGNOSTIC.json').read_text())
    check('diagnostic metadata matches native blob', summary['file_blob']==EXPECTED_BLOB and summary['sha256']==EXPECTED_SHA256 and summary['bytes']==18581)
    check('row clock counts reconcile', sum(summary['as_of_counts'].values())==summary['rows']==1364)
    check('nonnull/null estimate counts reconcile', summary['eps_nonnull']+summary['eps_null']==1364)
    check('selected EXPO/PNR rows preserve old clocks', all(r['as_of'].startswith('2026-06-19') for r in summary['selected_rows']))
    check('historical values not certified consensus', summary['qualified_consensus_comparisons']==0)
    # JSON is a derivative of this written catalog, not a production data registry.
    catalog=json.loads((ROOT/'WAVE9_TASK_CATALOG.json').read_text())
    check('task JSON is exact derivative', catalog['tasks']==rows and catalog['research_only'] is True)
    if args.snapshot:
        from inspect_wave9_snapshot import read_snapshot
        b=args.snapshot.read_bytes()
        check('input native bytes match both digests',len(b)==18581 and git_blob(b)==EXPECTED_BLOB and hashlib.sha256(b).hexdigest()==EXPECTED_SHA256)
        raw,meta=read_snapshot(args.snapshot)
        check('decoded row and footer checks',meta['rows']==1364 and all(c['page_boundary_and_stats_match'] for c in meta['column_checks']))
        check('decoded clock distribution matches report',dict(Counter(r['as_of'] for r in raw))==summary['as_of_counts'])
        check('decoded estimate null count matches report',sum(r['eps_forecast'] is None for r in raw)==103)
        check('decoded histories match report',sum(bool(json.loads(r['surprises_json'])) for r in raw)==4)
        selected={r['ticker']:r for r in raw}
        check('four editorial examples match decoded rows',all(selected[r['ticker']]==r for r in summary['selected_rows']))
        check('five exact-label absences confirmed',all(k not in selected for k in summary['absent_exact_labels']))
    result={'research_only':True,'checks':checks,'passed':sum(c['passed'] for c in checks),'failed':sum(not c['passed'] for c in checks),'snapshot_rechecked':bool(args.snapshot),'standard_engine_crosscheck':False,'application_tests_run':False}
    print(json.dumps(result,indent=2))
    return 0 if result['failed']==0 else 1

if __name__=='__main__':
    raise SystemExit(main())
