"""Offline research characterization of two exact pinned Macro modules.

This is NOT a product repair, live-data test, or production acceptance suite.
All FDA-like records and page failures are synthetic. Network and cache I/O are
replaced at their boundaries; the two production source files must hash exactly.
Run: python probe_r7_fda.py --source-root /path/to/macro
The default source root is ./pinned, containing the two local evidence copies.
No source downloading, credentials, remote writes or provider calls occur.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import logging
import sys
import tempfile
import types
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import requests

PIN = '2c7436bea5d1fca9d2ad1778eed1a6b55fa9e8ea'
EXPECTED = {
    'engine/fda_scarcity.py': 'd081b19c629db28e0add7d9a8a22732263f2bd08',
    'collectors/fda_shortages.py': '23b5e6f7f9357e157082053f64dcb0a7662225d0',
}


def load_module(name: str, path: Path, expected: str):
    data = path.read_bytes()
    actual = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
    if actual != expected:
        raise ValueError(f'Pinned source mismatch: {path}: {actual} != {expected}')
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'Cannot load {path}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def record(molecule='semaglutide', status='Current', availability='Available', key='A'):
    return dict(generic_name=molecule, status=status, availability=availability,
                package_ndc=f'SYNTHETIC-{key}', initial_posting_date='01/01/2026',
                fetched_utc='2026-09-23T00:00:00+00:00')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, default=Path(__file__).parent / 'pinned')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    root = args.source_root
    paths = {p: root / p if (root / p).exists() else root / Path(p).name for p in EXPECTED}
    # Source imports have only this small infrastructure dependency at import time.
    base = types.ModuleType('collectors.base')
    base.is_connection_error = lambda error: isinstance(error, requests.ConnectionError)
    config = types.ModuleType('lib.config')
    config.data_dir = lambda: (_ for _ in ()).throw(AssertionError('real data_dir forbidden'))
    collectors = types.ModuleType('collectors')
    collectors.base = base
    lib = types.ModuleType('lib')
    lib.config = config
    injected = {'collectors': collectors, 'collectors.base': base, 'lib': lib, 'lib.config': config}
    results = []

    def check(code, description, condition, observed, requirement, control=False):
        if not condition:
            raise AssertionError(f'Characterization changed: {code}: {observed!r}')
        results.append(dict(id=code, description=description, kind='control' if control else 'finding',
                            reproduced=True, observed=observed, future_requirement=requirement))

    with patch.dict(sys.modules, injected), patch.object(
            requests.sessions.Session, 'request', side_effect=AssertionError('network forbidden')):
        engine = load_module('r7_engine', paths['engine/fda_scarcity.py'], EXPECTED['engine/fda_scarcity.py'])
        collector = load_module('r7_collector', paths['collectors/fda_shortages.py'], EXPECTED['collectors/fda_shortages.py'])
        view = lambda rows: engine.compute_fda_scarcity(pd.DataFrame(rows))['glp1_obesity']

        a = view([record()])
        check('R7-F01', 'Current status with Available presentation disappears from active classification',
              a['band'] == 'NONE' and a['n_active'] == 0, a,
              'Preserve national Current status separately from manufacturer presentation availability.')
        a = view([record(), record('tirzepatide', 'Resolved', 'Available', 'B')])
        check('R7-F02', 'Mixed Current+Available and resolved molecules become a resolved theme band',
              a['band'] == 'SHORTAGE_RESOLVED' and a['n_active'] == 0, a,
              'Mixed observed national statuses cannot become a theme-wide all-clear.')
        chip = engine.format_theme_feed_chip(a, 'glp1_obesity')
        check('R7-F03', 'Resolved status is rendered as a glut inference',
              'glut tell' in chip['label'], chip,
              'State the source determination; surplus capacity and retained economics require separate evidence.')
        a = view([record(status='To Be Discontinued')])
        check('R7-F04', 'Discontinued-only input reuses the resolved machine band',
              a['band'] == 'SHORTAGE_RESOLVED' and a['n_resolved'] == 0, a,
              'Discontinuation must stay distinct from resolution in machine fields as well as text.')
        old = record(status='Resolved'); old['fetched_utc'] = '2020-01-01T00:00:00+00:00'
        new = dict(old, fetched_utc='2026-09-23T00:00:00+00:00')
        x, y = view([old]), view([new])
        check('R7-F05', 'Read function ignores supplied observation age', x == y,
              {'same_output': x == y, 'old_fetched_utc': old['fetched_utc'], 'new_fetched_utc': new['fetched_utc']},
              'An owning freshness gate must distinguish stale evidence before present-tense synthesis; no universal threshold invented here.')
        a = view([record(status='UNRECOGNIZED')])
        check('R7-F06', 'Observed unknown status is described as no records',
              a['band'] == 'NONE' and a['rationale'].startswith('no shortage records'), a,
              'Unknown status and absent records require separate missingness reasons.')
        a = view([record(availability='Limited Availability'), record('tirzepatide', 'Resolved', key='B')])
        check('R7-F07', 'Opposite-status molecule is incorrectly described as no records',
              'no records: tirzepatide' in a['rationale'], a,
              'Compute observed-molecule coverage independently from status-specific subsets.')
        a = view([record(availability='Limited Availability')])
        check('R7-C01', 'Control: Current+Limited Availability remains active', a['band'] == 'SHORTAGE_ACTIVE',
              a['band'], 'Keep this valid behavior.', True)
        a = view([record(status='Resolved')])
        check('R7-C02', 'Control: actual Resolved status recognized', a['n_resolved'] == 1,
              a['n_resolved'], 'Preserve source resolution while removing unsupported economic inference.', True)
        a = engine.compute_fda_scarcity(pd.DataFrame())
        check('R7-C03', 'Control: empty frame gives unavailable value', a == {'glp1_obesity': None},
              a, 'Keep explicit unavailable behavior; distinguish complete empty source at acquisition.', True)

        class FrozenClock:
            @staticmethod
            def now(tz=None):
                return datetime(2026, 9, 23, tzinfo=timezone.utc)

        def collect(pages, existing=None):
            # Isolate all filesystem and network effects. Existing cache presence is
            # represented by a temporary empty sentinel, never a production file.
            writes = []
            with tempfile.TemporaryDirectory(prefix='r7_fda_') as folder:
                cache = Path(folder) / 'cache.parquet'
                if existing is not None:
                    cache.touch()
                def capture(frame, *_, **__):
                    writes.append(frame.copy(deep=True))
                with patch.object(collector, '_shortages_path', return_value=cache), \
                     patch.object(collector, '_fetch_page', side_effect=pages), \
                     patch.object(collector.time, 'sleep', return_value=None), \
                     patch.object(collector, 'datetime', FrozenClock), \
                     patch.object(pd, 'read_parquet', return_value=existing), \
                     patch.object(pd.DataFrame, 'to_parquet', new=capture):
                    out = collector.fetch_shortages()
            return out, writes

        def page(rows, total):
            return {'meta': {'last_updated': '2026-09-23', 'results': {'total': total}}, 'results': rows}

        out, writes = collect([page([record()], 2), requests.HTTPError('synthetic page-2 HTTP failure')])
        check('R7-F08', 'Later page failure still publishes a partial snapshot to cache',
              len(writes) == 1 and len(out) == 1,
              {'declared_total': 2, 'published_rows': len(out), 'cache_writes': len(writes),
               'completeness_field_present': any('complete' in key for key in out.columns)},
              'Partial acquisition cannot publish an authoritative current census; preserve the last complete generation with an explicit failed-refresh receipt.')
        existing = pd.DataFrame([record(availability='Limited Availability')])
        out, writes = collect([page([record(status='Resolved')], 1)], existing)
        check('R7-F09', 'New observation overwrites earlier same-key status in cache',
              len(out) == 1 and out.iloc[0]['status'] == 'Resolved',
              {'observations_after_two_inputs': len(out), 'retained_status': out.iloc[0]['status']},
              'Preserve dated observations using the incumbent source/evidence history owner; a latest-value cache alone is not point-in-time history.')
        out, writes = collect([page([record('tirzepatide', 'Resolved', key='B')], 1)], existing)
        check('R7-F10', 'Record absent from a later complete page persists without absence metadata',
              len(out) == 2 and 'Current' in out['status'].tolist(),
              {'source_total': 1, 'cached_rows': len(out), 'retained_statuses': out['status'].tolist()},
              'Retain history but distinguish absent-from-current-snapshot, retained historical and currently observed rows.')
        out, writes = collect([page([record()], 1)])
        check('R7-F11', 'API generation metadata is dropped during normalization',
              'last_updated' not in out.columns and 'fetched_utc' in out.columns,
              {'last_updated_retained': 'last_updated' in out.columns, 'fetched_utc_retained': 'fetched_utc' in out.columns},
              'Preserve source-generation, acquisition and per-record clocks separately.')
        check('R7-C04', 'Control: complete one-page acquisition yields one cached row',
              len(out) == 1 and len(writes) == 1, {'rows': len(out), 'cache_writes': len(writes)},
              'Keep complete bounded acquisition working.', True)
        out, writes = collect([requests.ConnectionError('synthetic no-dispatch network failure')])
        check('R7-C05', 'Control: first-page connection failure does not publish',
              out is None and len(writes) == 0, {'returned_none': out is None, 'cache_writes': len(writes)},
              'Keep failed acquisition non-publishing.', True)

    receipt = {
        'artifact_kind': 'offline_pinned_source_characterization', 'research_as_of': '2026-09-23',
        'repository': 'mastermindx-market-intelligence/macro', 'source_commit': PIN,
        'source_blobs': EXPECTED, 'all_source_hashes_matched': True,
        'findings_reproduced': sum(x['kind'] == 'finding' for x in results),
        'controls_reproduced': sum(x['kind'] == 'control' for x in results),
        'network_calls': 0, 'production_cache_writes': 0, 'product_repaired': False,
        'live_incident_observed': False, 'production_acceptance': False,
        'pandas_version': pd.__version__, 'results': results,
    }
    text = json.dumps(receipt, ensure_ascii=False, indent=2) + '\n'
    if args.output:
        args.output.write_text(text, encoding='utf-8')
    print(json.dumps({k: v for k, v in receipt.items() if k != 'results'}, indent=2))
    return 0


if __name__ == '__main__':
    logging.basicConfig(level=logging.ERROR)
    raise SystemExit(main())
