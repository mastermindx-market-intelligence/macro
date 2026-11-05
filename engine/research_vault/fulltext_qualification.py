"""One read-only, intended-host resource check through incumbent Store methods.

Run as an isolated CLI, never on a Store shared with a serving process. This
permanently disables that instance's write/list/unbounded interfaces. Source
bodies exist only in an exclusive private scratch copy, removed on normal exit.
It issues no generation BEGIN, receipt, corpus, catalog or model publication.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import sqlite3
import stat
import tempfile
import threading
import time

from engine.research_vault import catalog, corpus, fulltext_store
from engine.research_vault import producer_generation as contract
from engine.research_vault.producer_generation_writer import (
    _census, record_fulltext_source_cut, _validate_fulltext_source_cut,
)

FINAL_CORPUS_MAX_BYTES = contract.CORPUS_MAX_BYTES


def _read_only(store, *, deadline, clock):
    reads = Counter()
    lock = threading.Lock()
    bounded = store.get_bytes_strict_bounded
    versioned = store.get_bytes_strict_bounded_versioned

    def classify(key, maximum):
        if clock() >= deadline:
            raise TimeoutError('resource qualification deadline')
        if key == catalog.CATALOG_KEY:
            kind, bound = 'catalog', contract.CATALOG_MAX_BYTES
        elif key == contract.CORPUS_KEY:
            kind, bound = 'corpus', contract.CORPUS_MAX_BYTES
        elif isinstance(key, str) and key.startswith(fulltext_store.RECEIPT_PREFIX) and key.endswith('.json'):
            kind, bound = 'receipt', fulltext_store.RECEIPT_MAX_BYTES
        elif isinstance(key, str) and key.startswith(fulltext_store.FULLTEXT_PREFIX) and key.endswith('.json'):
            kind, bound = 'derivative', fulltext_store.FULLTEXT_MAX_BYTES
        else:
            raise RuntimeError('read-only qualification object refused')
        if type(maximum) is not int or not 0 < maximum <= bound:
            raise RuntimeError('read-only qualification bound refused')
        with lock:
            reads[kind] += 1

    def get(key, maximum):
        classify(key, maximum)
        value = bounded(key, maximum)
        if clock() >= deadline:
            raise TimeoutError('resource qualification deadline')
        return value

    def get_version(key, maximum):
        if key != catalog.CATALOG_KEY:
            raise RuntimeError('read-only qualification version refused')
        classify(key, maximum)
        value = versioned(key, maximum)
        if clock() >= deadline:
            raise TimeoutError('resource qualification deadline')
        return value

    def refuse(*args, **kwargs):
        raise RuntimeError('read-only qualification interface refused')

    for name in ('put_bytes', 'put_bytes_strict_conditional', 'delete', 'list_prefix',
                 'get_bytes', 'get_bytes_strict', 'validate_strict_conditional_write_capability'):
        setattr(store, name, refuse)
    store.get_bytes_strict_bounded = get
    store.get_bytes_strict_bounded_versioned = get_version
    return reads


def run(store, *, scratch_root, max_seconds=750, clock=time.monotonic):
    root = Path(scratch_root)
    info = root.stat(follow_symlinks=False)
    if (not root.is_absolute() or root.is_symlink()
            or any(p.is_symlink() for p in root.parents)
            or not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid()
            or info.st_mode & 0o077):
        raise ValueError('existing private scratch root required')
    if type(max_seconds) is not int or not 1 <= max_seconds <= 750:
        raise ValueError('finite qualification deadline required')
    if shutil.disk_usage(root).free < 2 * 1024**3:
        raise ValueError('insufficient private scratch capacity')
    started = clock();deadline = started + max_seconds
    reads = _read_only(store, deadline=deadline, clock=clock)
    result = {'schema': 'research_vault.fulltext_resource_qualification.v1',
              'writer_qualified': False, 'production_accepted': False,
              'production_writes': 0, 'PDF_reads': 0, 'extractions': 0,
              'model_calls': 0, 'phase_seconds': {},
              'limits': ['read-only candidate composition; not a production generation',
                         'excludes inbox intake, processed-index, extraction and mutable publication time']}
    phase = 'restore'
    cache = None
    try:
        selected = store.get_bytes_strict_bounded_versioned(catalog.CATALOG_KEY, contract.CATALOG_MAX_BYTES)
        if selected is None:
            raise ValueError('canonical catalog absent')
        doc = catalog.parse_strict(selected.data, check_future_clock=False)
        blob = store.get_bytes_strict_bounded(contract.CORPUS_KEY, contract.CORPUS_MAX_BYTES)
        if blob is None:
            raise ValueError('canonical corpus absent')
        with tempfile.TemporaryDirectory(prefix='rv-resource-', dir=root) as directory:
            p = Path(directory) / 'corpus.sqlite'
            fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, 'wb') as stream:
                stream.write(blob)
            result['original_corpus_bytes'] = len(blob)
            result['original_corpus_sha256'] = hashlib.sha256(blob).hexdigest()
            del blob
            from engine.research_vault.producer_read_cache import CorpusReadCache
            cache = CorpusReadCache(p, doc)
            phase = 'begin_census'
            t = clock()
            initial = cache.inherited_members(doc, doc.get(contract.GENERATION_FIELD), store,
                producer_commit=os.environ.get('GITHUB_SHA'))
            result['starting_cut_inherited'] = initial is not None
            if initial is None:
                cache.reset()
                initial = _census(store, doc, read_cache=cache)
            cache.seal(initial)
            result['phase_seconds']['begin_census'] = clock() - t
            result['sealed_cache_corpus_bytes'] = p.stat().st_size
            result['initial_classifications'] = dict(Counter(row['layer'] for row in initial))
            phase = 'full_body_stage'
            conn = corpus.open_db(p)
            try:
                t = clock()
                staged = cache.stage(conn, doc, [],
                    max_rows=10000, max_body_bytes=256 * 1024 * 1024)
                record_fulltext_source_cut(conn, doc, staged['source_digests'],
                    receipt_digests=staged['receipt_digests'], record_digests=staged['record_digests'])
                conn.commit()
                result['phase_seconds']['full_body_stage'] = clock() - t
                result['uncompacted_corpus_bytes'] = p.stat().st_size
                phase = 'image_compaction'
                t = clock()
                from engine.research_vault.fulltext_index import compact_for_publication
                compact_for_publication(conn)
                result['phase_seconds']['image_compaction'] = clock() - t
            finally:
                conn.close()
                cache.close()
            result['staged_counts'] = staged['counts']
            result['final_corpus_bytes'] = p.stat().st_size
            phase = 'complete_census'
            t = clock();final = _census(store, doc)
            result['phase_seconds']['complete_census'] = clock() - t
            result['source_cut_unchanged'] = staged['source_digests'] == {
                row['report_id']: row['source_pdf_sha256'] for row in final}
            observed = store.get_bytes_strict_bounded_versioned(catalog.CATALOG_KEY, contract.CATALOG_MAX_BYTES)
            result['catalog_fence_unchanged'] = (observed is not None and
                observed.data == selected.data and observed.version == selected.version)
            result['final_classifications'] = dict(Counter(row['layer'] for row in final))
            if not result['catalog_fence_unchanged'] or not result['source_cut_unchanged']:
                result['state'] = 'OBSERVATION_CHANGED'
            elif result['final_corpus_bytes'] > FINAL_CORPUS_MAX_BYTES:
                result['state'] = 'RESOURCE_BOUND_EXCEEDED'
            else:
                t = clock()
                phase = 'source_cut_validation'
                _validate_fulltext_source_cut(p.read_bytes(), doc, final)
                result['phase_seconds']['source_cut_validation'] = clock() - t
                result['state'] = 'READONLY_RESOURCE_CHECK_PASSED'
    except Exception as exc:
        result.update(state='READONLY_RESOURCE_CHECK_UNAVAILABLE',
                      error_class=type(exc).__name__, error_phase=phase)
        if isinstance(exc, sqlite3.Error):
            # Numeric SQLite diagnostics contain neither SQL nor licensed values.
            result['sqlite_errorcode'] = getattr(exc, 'sqlite_errorcode', None)
            result['sqlite_errorname'] = getattr(exc, 'sqlite_errorname', None)
    finally:
        if cache is not None:
            cache.close()
    result['input_cache_storage'] = 'private_process_memory'
    result['elapsed_seconds'] = clock() - started
    if (result['state'] == 'READONLY_RESOURCE_CHECK_PASSED'
            and result['elapsed_seconds'] > max_seconds):
        result['state'] = 'RESOURCE_TIME_BOUND_EXCEEDED'
    result['read_calls'] = dict(reads)
    # ru_maxrss is bytes on macOS, KiB on Linux. Retain raw platform identity.
    import sys
    result['platform'] = sys.platform
    result['peak_rss_raw'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scratch-root', type=Path, required=True)
    args = parser.parse_args()
    from engine.research_vault.r2_store import R2Store, build_store
    store = build_store()
    if type(store) is not R2Store or not store.available:
        print(json.dumps({'state': 'READONLY_STORE_UNAVAILABLE', 'writer_qualified': False}))
        return 1
    try:
        result = run(store, scratch_root=args.scratch_root)
    except Exception as exc:
        result = {'state': 'READONLY_RESOURCE_CHECK_UNAVAILABLE',
                  'error_class': type(exc).__name__, 'writer_qualified': False}
    result['execution_context'] = {key: os.environ.get(key) for key in
        ('GITHUB_RUN_ID', 'GITHUB_RUN_ATTEMPT', 'GITHUB_SHA', 'RUNNER_NAME', 'RUNNER_OS')}
    print(json.dumps(result, sort_keys=True))
    return 0 if result['state'] == 'READONLY_RESOURCE_CHECK_PASSED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
