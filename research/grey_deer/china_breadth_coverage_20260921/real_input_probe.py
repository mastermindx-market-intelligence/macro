"""Read an existing China close artifact; never write to shared data."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import pandas as pd
import pyarrow.parquet as pq

root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(root))
from lib import config
from collectors.china_breadth import ChinaBreadthAdapter

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', type=Path, required=True)
args = parser.parse_args()
source = args.source
settings = config.load()['china']
names = list(dict.fromkeys(t for group in settings['constituents'].values() for t in group))
source_bytes = source.read_bytes()
columns = set(pq.ParquetFile(io.BytesIO(source_bytes)).schema.names)
selected = [n for n in names if n in columns]
frame = pd.read_parquet(io.BytesIO(source_bytes), columns=selected)
receipt = {'source': str(source), 'source_sha256': hashlib.sha256(source_bytes).hexdigest(),
           'input_rows': len(frame), 'input_asof': str(frame.index.max()),
           'configured_names': len(names), 'available_columns': len(selected),
           'kind': 'stored-input canary, not a live collector refresh'}
output = Path(__file__).parent
with tempfile.TemporaryDirectory(dir=output) as tmp:
    adapter = ChinaBreadthAdapter.__new__(ChinaBreadthAdapter)
    adapter.cfg, adapter.const_cfg = settings['breadth'], settings['constituents']
    adapter.cache_path = Path(tmp) / 'china_breadth' / '_closes_cache.parquet'
    adapter._download_closes = lambda *_: frame.copy()
    receipt['latest_quote_count'] = int(frame.iloc[-1].notna().sum())
    receipt['ma_eligible'] = {str(w): int(frame.tail(w).notna().all().sum())
                            if len(frame) >= w else 0 for w in adapter.cfg['ma_windows']}
    try:
        baseline = adapter.compute(frame)
        result = adapter.fetch(full_history=True)['breadth']
        pd.testing.assert_frame_equal(result, baseline)
        receipt.update(status='accepted', original_math_unchanged=True,
                       output_asof=str(result.index[-1]),
                       latest_breadth=result.iloc[-1].to_dict())
    except Exception as exc:
        receipt.update(status='rejected', error=f'{type(exc).__name__}: {exc}')
(output / 'real_input_receipt.json').write_text(json.dumps(receipt, indent=2))
print(json.dumps(receipt, indent=2))
