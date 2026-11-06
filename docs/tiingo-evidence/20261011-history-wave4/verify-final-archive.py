import hashlib
import json
import shutil
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, '/Volumes/Mastermind/agent-workspaces/sol/tiingo-ingestion-20261009')
from collectors.tiingo_archive import validate_receipt, receipt_identity
from scripts.tiingo_materialize import verified_raw
from lib.dataos.tiingo_reader import read_research_view

root = Path('/Volumes/Mastermind/market-data/tiingo')
output = Path('/Users/chriswong/.codex/visualizations/2026/10/11/01a12ab6-92cb-7c42-a711-42673ebb6b50/tiingo-phase1/eod-wave4-final-qualified-archive.json')
proof = {'schema': 'tiingo_live_qualification_summary.v1',
         'source_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
         'observed_at_utc': datetime.now(timezone.utc).isoformat(),
         'archive': str(root), 'capture_scope': 'BOUNDED_PILOTS_NOT_COMPLETE_BACKFILL',
         'complete_overnight_coverage': False, 'pit_backtest_eligible': False,
         'production_consumer_acceptance': False, 'receipts': [], 'boats_control_only': []}
proof['source_worktree_dirty'] = bool(subprocess.check_output(['git','status','--porcelain'],text=True).strip())
proof['loaded_source_sha256'] = {p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in ['collectors/tiingo_archive.py','scripts/tiingo_materialize.py','lib/dataos/tiingo_reader.py']}
proof['qualification_method_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
eod = {}
single_counts = {}
receipt_files = sorted((root / 'receipts').rglob('*.json'))
eod_capture_counts = Counter()
raw_context_counts = Counter()
for receipt_file in receipt_files:
    source_receipt = json.loads(receipt_file.read_text())
    validate_receipt(source_receipt)
    context_source = source_receipt.get('source', 'boats-firehose')
    context_day = (source_receipt.get('observed_at_utc') or source_receipt.get('first_received_at_utc'))[:10]
    raw_context_counts[(context_source, context_day, source_receipt['raw_sha256'])] += 1
    if source_receipt.get('source') == 'eod-bars':
        eod_capture_counts[source_receipt['symbol']] += 1
counts = Counter()
for file in receipt_files:
    receipt = json.loads(file.read_text())
    raw = verified_raw(root, receipt)
    source = receipt.get('source', 'boats-firehose')
    counts[source] += 1
    record = {'source': source, 'receipt_file': file.relative_to(root).as_posix(),
              'receipt_file_sha256': hashlib.sha256(file.read_bytes()).hexdigest(),
              'raw_sha256': receipt['raw_sha256'], 'raw_checksum_verified': True,
              'raw_bytes': len(raw), 'compressed_bytes': receipt['compressed_bytes']}
    if source == 'boats-firehose':
        frames = sum(receipt['counts'].get(k, 0) for k in ('Q', 'T', 'B'))
        for line in raw.splitlines():
            wrapper = json.loads(line)
            inner = json.loads(wrapper['raw_message'])
            proof['boats_control_only'].append({**record,
                'received_at_utc': wrapper['received_at'],
                'message_type': inner.get('messageType'),
                'response_code': inner.get('response', {}).get('code'),
                'subscription_id_present': bool(inner.get('data', {}).get('subscriptionId')),
                'market_frames': frames})
        continue
    identity = validate_receipt(receipt)
    record.update({'symbol': receipt.get('symbol'), 'receipt_id': identity,
        'http_status': receipt['http_status'], 'observed_at_utc': receipt['observed_at_utc'],
        'request_path': receipt['request_path'], 'record_count_hint': receipt.get('record_count_hint')})
    if source not in ('fund-meta', 'fund-definitions'):
        day = receipt['observed_at_utc'][:10]
        if json.loads(raw) == []:
            record.update({'projected_rows': 0, 'projection_status': 'EMPTY_NORMALIZED',
                           'raw_empty_response_verified': True})
            proof['receipts'].append(record)
            continue
        # Select the retained exact-receipt output when present; otherwise use
        # the reader's unambiguous content selector. Both paths still verify
        # the actual raw receipt and every row against this expected identity.
        selector = identity if ((root / 'manifests' / source / day / (identity + '.json')).is_file() or raw_context_counts[(source, day, receipt['raw_sha256'])] > 1) else receipt['raw_sha256']
        view = read_research_view(source, day, selector, root=root, max_rows=1000000)
        assert all(row['source_receipt_id'] == identity for row in view.rows)
        assert all(row['source_sha256'] == receipt['raw_sha256'] for row in view.rows)
        record.update({'projected_rows': len(view.rows), 'projection_lineage_verified': True, 'selector_kind': 'EXACT_RECEIPT_ID' if selector == identity else 'VERIFIED_SINGLE_CONTEXT_CONTENT'})
        if source == 'eod-bars':
            dates = [row['market_date'] for row in view.rows]
            assert len(set(dates)) == len(dates)
            record.update({'first_date': min(dates) if dates else None,
                'last_date': max(dates) if dates else None,
                'split_events': sum(row['split_factor'] not in (None, 1) for row in view.rows),
                'dividend_events': sum(row['dividend_cash'] not in (None, 0) for row in view.rows),
                'raw_adjusted_different_dates': sum(row['close_raw'] != row['close_tradj'] for row in view.rows)})
            if eod_capture_counts[receipt['symbol']] == 1:
                single_counts[receipt['symbol']] = len(view.rows)
                proof['receipts'].append(record)
                continue
            rows = eod.setdefault(receipt['symbol'], {})
            for row in view.rows:
                previous = rows.get(row['market_date'])
                economic = {k: row[k] for k in ('open_raw','high_raw','low_raw','close_raw','volume_raw',
                    'open_tradj','high_tradj','low_tradj','close_tradj','volume_vendor_adjusted','dividend_cash','split_factor')}
                if previous is not None:
                    assert previous == economic, 'same-day overlapping economic history changed'
                rows[row['market_date']] = economic
    proof['receipts'].append(record)
proof.update({'receipt_counts': dict(sorted(counts.items())),
    'distinct_eod_histories': len(eod) + len(single_counts), 'distinct_eod_bars': sum(len(rows) for rows in eod.values()) + sum(single_counts.values()),
    'all_eod_raw_and_projection_lineage_verified': True,
    'archive_bytes': sum(p.stat().st_size for p in root.rglob('*') if p.is_file()),
    'free_gib': round(shutil.disk_usage(root).free / (1024**3), 3), 'free_reserve_gib': 35})
output.write_text(json.dumps(proof, indent=2, sort_keys=True) + '\n')
print(json.dumps({k: proof[k] for k in ('observed_at_utc','source_head','receipt_counts',
    'distinct_eod_histories','distinct_eod_bars','all_eod_raw_and_projection_lineage_verified',
    'archive_bytes','free_gib','free_reserve_gib')}, indent=2))
print(json.dumps({'boats_ack': [{k: row[k] for k in ('message_type','response_code','subscription_id_present','market_frames')}
    for row in proof['boats_control_only']]}, indent=2))
