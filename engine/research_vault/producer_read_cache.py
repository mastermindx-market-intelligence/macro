"""Bounded per-run input reuse in private process memory, never authority.

Only the canonical corpus/FTS image is published. Each run captures a fresh
starting census and keeps its compressed bytes in a separate in-memory SQLite
connection; no source payload cache grows the reader's image. COMPLETE always
performs a second fresh Store census. The image-retained source cut still binds
ordinary completion and the existing original-parent continuation.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sqlite3
import threading
import zlib

from engine.research_vault import corpus, fulltext_index, fulltext_store
from engine.research_vault import producer_generation as contract

TABLE = 'producer_read_cache'
MAX_RAW_BYTES = 512 * 1024 * 1024
MAX_COMPRESSED = fulltext_store.FULLTEXT_MAX_BYTES + 65536


def _sha(value):
    return None if value is None else hashlib.sha256(value).hexdigest()


def _unpack(blob, digest, size, bound):
    if blob is None:
        if digest is not None or size != 0:
            raise ValueError('inconsistent absent cached object')
        return None
    if (type(blob) is not bytes or len(blob) > MAX_COMPRESSED
            or type(size) is not int or not 0 <= size <= bound):
        raise ValueError('cached object outside bound')
    decoder = zlib.decompressobj()
    raw = decoder.decompress(blob, bound + 1)
    if (len(raw) > bound or decoder.unconsumed_tail or decoder.unused_data
            or not decoder.eof or len(raw) != size or _sha(raw) != digest):
        raise ValueError('cached object identity mismatch')
    return raw


class CorpusReadCache:
    def __init__(self, path, document):
        self.path = Path(path)
        self.ids = frozenset(contract.admitted_cohort_from_catalog(document))
        if not self.ids or len(self.ids) > fulltext_index.MAX_ROWS:
            raise ValueError('explicit bounded cache cohort required')
        h = hashlib.sha256();size = 0
        with self.path.open('rb') as stream:
            for part in iter(lambda: stream.read(1024 * 1024), b''):
                size += len(part)
                if size > contract.CORPUS_MAX_BYTES:
                    raise ValueError('restored corpus outside bound')
                h.update(part)
        self.original_sha256 = h.hexdigest()
        self.lock = threading.RLock()
        self.conn = sqlite3.connect(':memory:', check_same_thread=False)
        self.conn.enable_load_extension(False)
        self.conn.execute('PRAGMA trusted_schema=OFF')
        self.conn.execute(f'''CREATE TABLE {TABLE} (
            report_id TEXT PRIMARY KEY, receipt BLOB, receipt_sha256 TEXT,
            receipt_size INTEGER NOT NULL, record BLOB, record_sha256 TEXT,
            record_size INTEGER NOT NULL)''')
        self.sizes = {}
        self.total = 0
        self.members = {}
        self.sealed = False

    def reset(self):
        with self.lock:
            self.conn.execute(f'DELETE FROM {TABLE}')
            self.sizes.clear();self.total = 0

    def _store(self, conn, rid, receipt, record):
        if not corpus.valid_doc_id(rid):
            raise ValueError('invalid cache member')
        for value, bound in ((receipt, fulltext_store.RECEIPT_MAX_BYTES),
                             (record, fulltext_store.FULLTEXT_MAX_BYTES)):
            if value is not None and (type(value) is not bytes or len(value) > bound):
                raise ValueError('cache object outside bound')
        size = sum(len(value) for value in (receipt, record) if value is not None)
        total = self.total - self.sizes.get(rid, 0) + size
        if total > MAX_RAW_BYTES:
            raise ValueError('cache raw byte bound exceeded')
        conn.execute(f'''INSERT INTO {TABLE} VALUES(?,?,?,?,?,?,?)
            ON CONFLICT(report_id) DO UPDATE SET receipt=excluded.receipt,
            receipt_sha256=excluded.receipt_sha256,receipt_size=excluded.receipt_size,
            record=excluded.record,record_sha256=excluded.record_sha256,
            record_size=excluded.record_size''', (rid,
            None if receipt is None else zlib.compress(receipt), _sha(receipt),
            0 if receipt is None else len(receipt),
            None if record is None else zlib.compress(record), _sha(record),
            0 if record is None else len(record)))
        self.total = total;self.sizes[rid] = size

    def capture(self, rid, receipt, record):
        if rid not in self.ids:
            raise ValueError('capture outside original cohort')
        with self.lock:
            if self.sealed:
                raise ValueError('sealed starting inputs are immutable')
            self._store(self.conn, rid, receipt, record)

    def _entry(self, rid, *, receipt_only=False):
        if self.conn is None:
            raise ValueError('closed input cache')
        with self.lock:
            record_fields = 'NULL,NULL,0' if receipt_only else 'substr(record,1,?),record_sha256,record_size'
            sql = f'''SELECT substr(receipt,1,?),receipt_sha256,receipt_size,
                {record_fields} FROM {TABLE} WHERE report_id=?'''
            args = (MAX_COMPRESSED + 1, rid) if receipt_only else (MAX_COMPRESSED + 1, MAX_COMPRESSED + 1, rid)
            row = self.conn.execute(sql, args).fetchone()
        if row is None:
            return None
        receipt = _unpack(row[0], row[1], row[2], fulltext_store.RECEIPT_MAX_BYTES)
        record = _unpack(row[3], row[4], row[5], fulltext_store.FULLTEXT_MAX_BYTES)
        return receipt, record

    def inherited_members(self, document, prior, store, *, producer_commit=None):
        if prior is None:
            return None
        contract.validate_generation(prior)
        if (prior['state'] != contract.GENERATION_STATE_COMPLETE
                or prior['corpus_sha256'] != self.original_sha256
                or prior['catalog_payload_sha256'] != contract.compute_catalog_payload_digest(document)
                or {m['report_id'] for m in prior['members']} != self.ids):
            raise ValueError('previous completed cut does not bind restored corpus')
        # Historical publication identity remains required, but source inputs
        # are not persisted. A new run always takes a fresh starting census.
        return None

    def seal(self, members):
        if {m['report_id'] for m in members} != self.ids:
            raise ValueError('incomplete cached starting cut')
        expected = {m['report_id']: (m['receipt_sha256'], m['derivative_record_sha256']) for m in members}
        observed = {rid: (a, b) for rid, a, b in self.conn.execute(
            f'SELECT report_id,receipt_sha256,record_sha256 FROM {TABLE}') if rid in self.ids}
        if observed != expected:
            raise ValueError('cache does not bind the measured starting cut')
        self.members = {m['report_id']: copy.deepcopy(m) for m in members}
        self.conn.commit()
        self.sealed = True
        # Memory-only capture must not permit an already oversized native image
        # to replace the predecessor. Later staged growth is checked before PUT.
        if self.path.stat().st_size > contract.CORPUS_MAX_BYTES:
            raise ValueError('sealed cache corpus outside producer image bound')

    def close(self):
        if self.conn is not None:
            self.conn.close();self.conn = None

    def processed_receipt(self, key):
        if (not isinstance(key, str) or not key.startswith(fulltext_store.RECEIPT_PREFIX)
                or not key.endswith('.json')):
            return None
        rid = key[len(fulltext_store.RECEIPT_PREFIX):-5]
        if rid not in self.ids:
            return None
        entry = self._entry(rid, receipt_only=True)
        if entry is not None and _sha(entry[0]) != self.members[rid]['receipt_sha256']:
            raise ValueError('cached receipt changed after starting cut')
        return None if entry is None else entry[0]

    def stage(self, conn, document, own_receipts, *, max_rows, max_body_bytes):
        from engine.research_vault.fulltext_publication import _pending
        ids = fulltext_index._cohort(document)
        overrides = _pending(ids, own_receipts)
        sources, receipt_hashes, candidate_hashes = {}, {}, {}

        def load(rid):
            # This immutable cache has its own memory database. The native
            # image writer's rollback-journal spill cannot lock these reads.
            entry = self._entry(rid) if rid in self.ids else None
            receipt, raw = (None, None) if entry is None else entry
            member = self.members.get(rid)
            key = fulltext_store.receipt_key(rid)
            if member is not None:
                if (_sha(receipt) != member['receipt_sha256']
                        or _sha(raw) != member['derivative_record_sha256']):
                    raise ValueError('cached bytes changed after starting cut')
            if key in overrides:
                old_digest = fulltext_store.parse_receipt_digest(receipt, rid) if receipt is not None else None
                receipt = overrides[key]
                new_digest = fulltext_store.parse_receipt_digest(receipt, rid)
                if new_digest != old_digest:
                    raw = None
            digest = fulltext_store.parse_receipt_digest(receipt, rid) if receipt is not None else None
            sources[rid] = digest;receipt_hashes[rid] = _sha(receipt)
            # Exact raw hashes bind the canonical validation already performed
            # by this same producer's measured cut. Index.stage validates the
            # extracted body again; avoid a redundant full-record validation.
            record = (json.loads(raw.decode('utf-8')) if raw is not None and digest is not None
                and member is not None and member['layer'] in {'full', 'thin', 'none'} else None)
            if record is not None:
                candidate_hashes[rid] = _sha(raw)
            return record

        accounting = self.total, dict(self.sizes)
        conn.execute('SAVEPOINT rv_cached_fulltext_stage')
        try:
            counts = fulltext_index.stage(conn, document, record_loader=load,
                source_digest_reader=lambda rid: sources[rid],
                max_rows=max_rows, max_body_bytes=max_body_bytes)
            for rid in ids:
                if rid not in sources:
                    load(rid)
            used = {rid: candidate_hashes[rid] for rid, binding in conn.execute(
                'SELECT doc_id,fulltext_binding FROM documents WHERE doc_id IN (SELECT value FROM json_each(?))',
                (json.dumps(ids),)) if binding is not None and rid in candidate_hashes}
            conn.execute('RELEASE SAVEPOINT rv_cached_fulltext_stage')
            return {'counts': counts, 'source_digests': sources,
                    'receipt_digests': receipt_hashes, 'record_digests': used}
        except BaseException:
            self.total, self.sizes = accounting
            conn.execute('ROLLBACK TO SAVEPOINT rv_cached_fulltext_stage')
            conn.execute('RELEASE SAVEPOINT rv_cached_fulltext_stage')
            raise
