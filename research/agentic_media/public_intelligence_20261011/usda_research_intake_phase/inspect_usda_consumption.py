"""Read-only, exact-source inspection after the incumbent Research ingester runs.

Local: python -B inspect_usda_consumption.py REPO LOCAL_STORE
VPS: send this file on SSH stdin to /opt/macro/.venv/bin/python -B - /opt/macro
The VPS path uses only the already-provisioned Research namespace. No extraction,
provider, producer dispatch, catalog mutation or raw body output occurs.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import re
import subprocess
import sys

ID = 'usda-2026-10-09-wasde-676'
PDF_SHA = '6cc97c08be7e683b6114ae8e16d49fce2f21dce3ed3f9933b0acbd2d37e6840b'
SIDE_SHA = '1a215b20c74538f8532757ce2ee043b5784a3e6573e857a8d51eeca8ffd2c80e'
DATE = '2026-10-09T16:00:00Z'


def digest(blob):
    return hashlib.sha256(blob).hexdigest()


def inspect(store):
    from engine.research_vault import fulltext_store
    reads = []

    def get(key, limit):
        data = store.get_bytes_strict_bounded(key, limit)
        reads.append({'key': key, 'present': data is not None,
                      'sha256': digest(data) if data is not None else None})
        return data

    raw = get('research_vault/catalog.json', 32 * 1024 * 1024)
    assert raw is not None, 'canonical catalog absent'
    rows = [x for x in json.loads(raw)['items'] if x.get('id') == ID]
    assert len(rows) <= 1, 'duplicate canonical identity'
    receipt_raw = get(fulltext_store.receipt_key(ID), 64 * 1024)
    out = {'observed_at': datetime.now(timezone.utc).isoformat(),
           'source_id': ID, 'source_sha256': PDF_SHA, 'reads': reads,
           'catalog_rows': len(rows), 'state': 'PENDING_INCUMBENT_INGEST',
           'writes': 0, 'provider_calls': 0, 'publication': False,
           'stock_ticker': None, 'press_draft_accepted': False}
    if not rows or receipt_raw is None:
        return out
    receipt = json.loads(receipt_raw)
    assert fulltext_store.parse_receipt_digest(receipt_raw, ID) == PDF_SHA, 'receipt source mismatch'
    assert receipt.get('pages') == 40 and receipt.get('text_layer') == 'full'
    # The producer receipt supplies the true inbox path; local fixtures use a
    # shorter filename, while canonical ingress uses the complete stable id.
    side_key = str(receipt['pdf_key']).removesuffix('.pdf') + '.json'
    side_raw = get(side_key, 64 * 1024)
    assert side_raw is not None and digest(side_raw) == SIDE_SHA, 'sidecar drift'
    side = json.loads(side_raw)
    item = rows[0]
    assert item['published_at'] == DATE and item['pages'] == 40
    assert item['summary_points'] == side['summary_points'] and item['tickers'] == []
    vault_pdf = get(f'research_vault/{ID}.pdf', 2 * 1024 * 1024)
    assert vault_pdf is not None and digest(vault_pdf) == PDF_SHA, 'promoted PDF mismatch'
    derivative_raw = get(fulltext_store.derivative_key(ID, PDF_SHA), 2 * 1024 * 1024)
    if derivative_raw is None:
        out['state'] = 'CATALOG_RECEIPT_READY_FULLTEXT_PENDING'
        return out
    record = fulltext_store.decode_record(derivative_raw, ID, PDF_SHA)
    assert record is not None, 'invalid canonical derivative'
    body = ' '.join(record['text'].split())
    assert record['page_count'] == 40 and 'October 9, 2026' in body and '740 million' in body
    out.update(state='CANONICAL_SOURCE_AND_FULLTEXT_VERIFIED',
               published_at=item['published_at'], pages=40,
               summary_points=len(item['summary_points']),
               fulltext_chars=record['char_count'], fulltext_sha256=record['extracted_text_sha256'])
    return out


def main():
    root = Path(sys.argv[1]).resolve()
    sys.path.insert(0, str(root))
    from engine.research_vault.r2_store import R2Store, build_store
    if len(sys.argv) == 3:
        store = build_store(local_dir=sys.argv[2])
        head_before = head_after = None
    else:
        assert root == Path('/opt/macro'), 'unexpected installed root'
        names = {'R2_RESEARCH_ENDPOINT', 'R2_RESEARCH_ACCESS_KEY_ID',
                 'R2_RESEARCH_SECRET_ACCESS_KEY', 'R2_RESEARCH_BUCKET', 'R2_BUCKET'}
        for line in Path('/etc/macro-api.env').read_text().splitlines():
            match = re.match(r'^\s*(?:export\s+)?([A-Z0-9_]+)=(.*)$', line)
            if match and match[1] in names:
                value = match[2].strip()
                if len(value) > 1 and value[0] == value[-1] and value[0] in "\"'":
                    value = value[1:-1]
                os.environ[match[1]] = value
        store = build_store()
        assert isinstance(store, R2Store) and store.available
        head_before = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
    result = inspect(store)
    if len(sys.argv) == 2:
        head_after = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
    result.update(installed_head_before=head_before, installed_head_after=head_after,
                  stable_installed_head=head_before == head_after,
                  local_fixture=len(sys.argv) == 3)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
