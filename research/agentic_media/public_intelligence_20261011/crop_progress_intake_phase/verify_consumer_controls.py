"""Fault injection against the read-only inspector; in-memory fixture only."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys

repo, storepath = (Path(x).resolve() for x in sys.argv[1:])
sys.path.insert(0, str(repo))
spec = importlib.util.spec_from_file_location('crop_inspector', Path(__file__).with_name('inspect_crop_consumption.py'))
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
from engine.research_vault import fulltext_store
raw = {str(p.relative_to(storepath)): p.read_bytes() for p in storepath.rglob('*') if p.is_file()}
before = {k: hashlib.sha256(v).hexdigest() for k,v in raw.items()}

class MemoryStore:
    def __init__(self, values):
        self.values = values
    def get_bytes_strict_bounded(self, key, limit):
        value = self.values.get(key)
        assert value is None or len(value) <= limit
        return value

def changed_catalog(**kw):
    data = dict(raw)
    cat = json.loads(data['research_vault/catalog.json'])
    cat['items'][0].update(kw)
    data['research_vault/catalog.json'] = json.dumps(cat).encode()
    return data

controls = []
good = probe.inspect(MemoryStore(raw))
assert good['state'] == 'CANONICAL_SOURCE_AND_FULLTEXT_VERIFIED'
controls.append('original_source_passes')
receipt = fulltext_store.receipt_key(probe.ID)
derivative = fulltext_store.derivative_key(probe.ID, probe.PDF_SHA)
for name, key, expected in [
    ('missing_receipt_pending', receipt, 'PENDING_INCUMBENT_INGEST'),
    ('missing_fulltext_pending', derivative, 'CATALOG_RECEIPT_READY_FULLTEXT_PENDING'),
]:
    data=dict(raw); data.pop(key)
    assert probe.inspect(MemoryStore(data))['state'] == expected
    controls.append(name)
cases = {
    'wrong_date_refused': changed_catalog(published_at='2026-10-14'),
    'invented_ticker_refused': changed_catalog(tickers=['DE']),
    'wrong_pages_refused': changed_catalog(pages=40),
    'changed_summary_refused': changed_catalog(summary_points=['Unverified replacement']),
    'wrong_pdf_refused': {**raw, f'research_vault/{probe.ID}.pdf':b'%PDF-changed'},
    'wrong_sidecar_refused': {**raw, f'research_inbox/{probe.ID}.json':b'{}'},
    'wrong_fulltext_refused': {**raw, derivative:b'{}'},
}
for name, data in cases.items():
    try:
        probe.inspect(MemoryStore(data))
    except (AssertionError, ValueError, KeyError):
        controls.append(name)
    else:
        raise AssertionError(name)
assert before == {k:hashlib.sha256(v).hexdigest() for k,v in raw.items()}
assert before == {str(p.relative_to(storepath)):hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in storepath.rglob('*') if p.is_file()}
print(json.dumps({'controls':controls,'passed':len(controls),'source_store_unchanged':True,
                  'canonical_writes':0,'provider_calls':0,'publication':False},indent=2))
