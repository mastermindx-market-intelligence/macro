"""Producer-only bounded canonical reads for the incumbent full-body stage.

No Store factory, PDF, extraction, listing or remote write. The assigning parent
owns source integration; a worker patch is assistance, never writer admission.
"""
from __future__ import annotations

from collections import deque
from concurrent.futures import ThreadPoolExecutor
import json

from engine.research_vault import fulltext_index as index, fulltext_store


def _pending(document_ids, receipts):
    if not isinstance(receipts, (tuple, list)) or len(receipts) > len(document_ids):
        raise ValueError('finite pending receipt plan required')
    allowed = {fulltext_store.receipt_key(rid): rid for rid in document_ids}
    result = {}
    for pair in receipts:
        if not isinstance(pair, (tuple, list)) or len(pair) != 2:
            raise ValueError('invalid pending receipt pair')
        key, raw = pair
        if (not isinstance(key, str) or key not in allowed or key in result
                or type(raw) is not bytes or len(raw) > fulltext_store.RECEIPT_MAX_BYTES):
            raise ValueError('invalid pending receipt plan')
        try:
            decoded = json.loads(raw.decode('utf-8'))
        except (ValueError, UnicodeError):
            raise ValueError('invalid pending receipt JSON') from None
        if (type(decoded) is not dict
                or decoded.get('id', allowed[key]) != allowed[key]):
            raise ValueError('pending receipt identity mismatch')
        # A valid native receipt may honestly have an unknown digest. Do not
        # invent one; the stage then removes obsolete body qualifications.
        result[key] = raw
    return result


def stage_from_store(conn, document, store, pending_receipts, *, max_rows, max_body_bytes):
    if (type(max_rows) is not int or not 1 <= max_rows <= index.MAX_ROWS
            or type(max_body_bytes) is not int or not 1 <= max_body_bytes <= index.MAX_BODY_BYTES):
        raise ValueError('finite explicit stage bounds required')
    ids = index._cohort(document)
    if len(ids) > max_rows:
        raise ValueError('catalog exceeds explicit row bound')
    pending = _pending(ids, pending_receipts)
    reader = getattr(store, 'get_bytes_strict_bounded', None)
    if not callable(reader):
        raise ValueError('strict bounded Store reader required')
    # The incumbent qualifier permits only its exact, prebuilt R2 client (or
    # exact fenced wrapper); duck Stores and unknown wrappers stay serial.
    from engine.research_vault.ingest import _receipt_read_workers
    workers = _receipt_read_workers(store, 4)

    def read(key, bound):
        value = reader(key, bound)
        if value is not None and (type(value) is not bytes or len(value) > bound):
            raise ValueError('invalid bounded Store response')
        return value

    def receipt(rid):
        key = fulltext_store.receipt_key(rid)
        return pending[key] if key in pending else read(key, fulltext_store.RECEIPT_MAX_BYTES)

    def member(rid):
        first = receipt(rid)
        digest = fulltext_store.parse_receipt_digest(first, rid) if first is not None else None
        raw = (read(fulltext_store.derivative_key(rid, digest), fulltext_store.FULLTEXT_MAX_BYTES)
               if digest is not None else None)
        record = fulltext_store.decode_record(raw, rid, digest) if raw is not None else None
        last = receipt(rid)  # after the derivative read, before any body upgrade
        current = fulltext_store.parse_receipt_digest(last, rid) if last is not None else None
        return rid, record, current

    def ordered():
        if workers == 1:
            for rid in ids:
                yield member(rid)
            return
        pool = ThreadPoolExecutor(max_workers=workers, thread_name_prefix='rv-fulltext-stage')
        queue, remaining = deque(), iter(ids)
        try:
            while True:
                while len(queue) < workers:
                    try:
                        rid = next(remaining)
                    except StopIteration:
                        break
                    queue.append(pool.submit(member, rid))
                if not queue:
                    break
                yield queue.popleft().result()
        finally:
            for future in queue:
                future.cancel()
            pool.shutdown(wait=True, cancel_futures=True)

    stream, sources, last_loaded = ordered(), {}, None

    def load(rid):
        nonlocal last_loaded
        for current_id, record, digest in stream:
            sources[current_id] = digest
            if current_id == rid:
                last_loaded = current_id
                return record
        raise ValueError('stage requested a non-monotonic member')

    def current(rid):
        nonlocal last_loaded
        if last_loaded != rid:
            raise ValueError('stage receipt must follow its record load')
        last_loaded = None
        return sources[rid]

    conn.execute('SAVEPOINT rv_fulltext_publication')
    try:
        counts = index.stage(conn, document, record_loader=load,
            source_digest_reader=current, max_rows=max_rows, max_body_bytes=max_body_bytes)
        # index.stage skips absent corpus rows. Their receipts still belong to
        # the final generation cut, including a missing trailing/all-missing row.
        for rid, _record, digest in stream:
            sources[rid] = digest
        conn.execute('RELEASE SAVEPOINT rv_fulltext_publication')
        return {'counts': counts, 'source_digests': sources}
    except BaseException:
        conn.execute('ROLLBACK TO SAVEPOINT rv_fulltext_publication')
        conn.execute('RELEASE SAVEPOINT rv_fulltext_publication')
        raise
    finally:
        stream.close()  # drains started reads even after a stage failure
