"""Existing-producer catalog fence; no runtime qualification is enabled here.

Only an explicitly identified producer may adopt a legacy/COMPLETE catalog.
BUILDING is never taken over automatically. Other writers and old effects must
be settled outside this helper before writer_protocol_qualified can become True.
"""
from __future__ import annotations

import copy
import base64
from collections import deque
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from engine.research_vault import catalog as catalog_mod
from engine.research_vault import fulltext, fulltext_store
from engine.research_vault import producer_generation as contract


# Two opaque versions can appear after a catalog effect (readback and terminal).
# At worst JSON escapes each UTF-8 byte as six bytes; 64KiB covers both, the
# result record and their bounded metadata. The synchronous writer does not
# append other operations between that intent and its acknowledgement records.
CATALOG_VERSION_MAX_BYTES = 4096
POST_EFFECT_EVIDENCE_BYTES = 64 * 1024
FULLTEXT_SOURCE_CUT_KEY = "producer_fulltext_source_cut"


def record_fulltext_source_cut(conn, document, sources, *, receipt_digests=None, record_digests=None):
    """Retain this explicit staged cut in the same private corpus transaction."""
    ids = contract.admitted_cohort_from_catalog(document)
    if (type(sources) is not dict or set(sources) != set(ids)
            or any(value is not None and (type(value) is not str or len(value) != 64
                or any(c not in "0123456789abcdef" for c in value))
                for value in sources.values())):
        raise GenerationWriteUnavailable("invalid fulltext source cut")
    cut = {
            "schema": "research_vault.producer_fulltext_source_cut.v1",
            "catalog_payload_sha256": contract.compute_catalog_payload_digest(document),
            "sources": sources}
    if receipt_digests is not None or record_digests is not None:
        if (type(receipt_digests) is not dict or set(receipt_digests) != set(ids)
                or type(record_digests) is not dict or not set(record_digests) <= set(ids)
                or any(value is None for value in record_digests.values())
                or any(v is not None and (type(v) is not str or len(v) != 64
                    or any(c not in "0123456789abcdef" for c in v))
                    for v in (*receipt_digests.values(), *record_digests.values()))):
            raise GenerationWriteUnavailable("invalid cached source cut")
        cut.update(schema="research_vault.producer_fulltext_source_cut.v2",
                   receipts=receipt_digests, records=record_digests)
    conn.execute("INSERT INTO meta(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (FULLTEXT_SOURCE_CUT_KEY, json.dumps(cut, sort_keys=True, separators=(",", ":"))))


def _validate_fulltext_source_cut(blob, document, members):
    """Check the staged PDF cut again before COMPLETE, including continuation.

    The original publication journal already binds these exact corpus bytes.
    Keeping the cut in that image preserves the same check when the original
    parent resumes a wholly unissued completion tail; no new journal protocol
    or replay authority is introduced. Older prefix-only images have no cut.
    """
    if not blob.startswith(b"SQLite format 3\x00"):
        return  # Existing pre-composition callers may publish opaque fixtures.
    import sqlite3
    conn = sqlite3.connect(":memory:")
    try:
        conn.deserialize(blob)
        conn.execute("PRAGMA trusted_schema=OFF")
        conn.execute("PRAGMA query_only=ON")
        if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='meta'").fetchone() is None:
            return
        row = conn.execute("SELECT value FROM meta WHERE key=?", (FULLTEXT_SOURCE_CUT_KEY,)).fetchone()
        if row is None:
            return
        cut = json.loads(row[0])
        expected = {m["report_id"]: m["source_pdf_sha256"] for m in members}
        version = cut.get('schema') if type(cut) is dict else None
        fields = {"schema", "catalog_payload_sha256", "sources"}
        if version == "research_vault.producer_fulltext_source_cut.v2":
            fields |= {"receipts", "records"}
        if (type(cut) is not dict or set(cut) != fields
                or version not in {"research_vault.producer_fulltext_source_cut.v1", "research_vault.producer_fulltext_source_cut.v2"}
                or cut["catalog_payload_sha256"] != contract.compute_catalog_payload_digest(document)
                or type(cut["sources"]) is not dict or cut["sources"] != expected):
            raise GenerationWriteUnavailable("fulltext source cut changed before COMPLETE")
        if version == "research_vault.producer_fulltext_source_cut.v2":
            receipts = {m['report_id']: m['receipt_sha256'] for m in members}
            records = {m['report_id']: m['derivative_record_sha256'] for m in members}
            bound_rows = {row[0] for row in conn.execute(
                'SELECT doc_id FROM documents WHERE fulltext_binding IS NOT NULL AND doc_id IN (SELECT value FROM json_each(?))',
                (json.dumps(sorted(expected)),))}
            if (type(cut['receipts']) is not dict or cut['receipts'] != receipts
                    or type(cut['records']) is not dict or set(cut['records']) != bound_rows
                    or any(type(value) is not str or len(value) != 64
                        or any(c not in '0123456789abcdef' for c in value)
                        for value in cut['records'].values())
                    or any(digest != records[rid] for rid, digest in cut['records'].items())):
                raise GenerationWriteUnavailable("cached canonical source cut changed before COMPLETE")
    finally:
        conn.close()


class GenerationWriteUnavailable(RuntimeError):
    """Refusal or uncertain write; caller must not retry or publish COMPLETE."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _dump(document: dict) -> bytes:
    return (json.dumps(document, ensure_ascii=False, indent=2, allow_nan=False)
            + "\n").encode("utf-8")


def _read(store: Any, key: str, bound: int) -> bytes | None:
    value = store.get_bytes_strict_bounded(key, bound)
    if value is not None and (type(value) is not bytes or len(value) > bound):
        raise GenerationWriteUnavailable("invalid bounded read")
    return value


def _catalog_read(store: Any):
    value = store.get_bytes_strict_bounded_versioned(
        catalog_mod.CATALOG_KEY, contract.CATALOG_MAX_BYTES)
    if value is None:
        raise GenerationWriteUnavailable("invalid catalog versioned miss")
    if value.data is None and value.version is None:
        return None
    if (type(value.data) is not bytes or len(value.data) > contract.CATALOG_MAX_BYTES
            or type(value.version) is not str or not value.version):
        raise GenerationWriteUnavailable("invalid catalog versioned read")
    try:
        if len(value.version.encode("utf-8")) > CATALOG_VERSION_MAX_BYTES:
            raise GenerationWriteUnavailable("catalog version outside evidence bound")
    except UnicodeError:
        raise GenerationWriteUnavailable("invalid catalog version encoding") from None
    return value


def _census_member(store: Any, report_id: str, *, read_cache=None) -> dict:
    receipt = _read(store, fulltext_store.receipt_key(report_id),
                    fulltext_store.RECEIPT_MAX_BYTES)
    source = (fulltext_store.parse_receipt_digest(receipt, report_id)
              if receipt is not None else None)
    record = (_read(store, fulltext_store.derivative_key(report_id, source),
                    fulltext_store.FULLTEXT_MAX_BYTES)
              if source is not None else None)
    if receipt is None:
        layer = "missing"
    elif source is None:
        layer = "digest_unknown"
    elif record is None:
        layer = "missing"
    else:
        decoded = fulltext_store.decode_record(record, report_id, source)
        layer = "corrupt" if decoded is None else decoded["text_layer_state"]
    if read_cache is not None:
        read_cache.capture(report_id, receipt, record)
    return {"report_id": report_id,
            "source_pdf_sha256": source,
            "receipt_sha256": None if receipt is None else _sha(receipt),
            "derivative_record_sha256": None if record is None else _sha(record),
            "layer": layer}


def _census(store: Any, document: dict, *, read_cache=None) -> list[dict]:
    ids = contract.admitted_cohort_from_catalog(document)
    if not ids:
        raise GenerationWriteUnavailable("adopted generation needs admitted cohort")
    from engine.research_vault.r2_store import R2Store
    # Same ordinary prebuilt client qualification as the incumbent receipt
    # reader. Strict receipt/derivative reads share no response bodies, perform
    # no writes and create no clients. Injected, wrapped and subclass stores
    # remain serial; duck typing does not establish thread safety.
    if type(store) is not R2Store or store._receipt_reads_thread_safe is not True:
        return [_census_member(store, report_id, read_cache=read_cache) for report_id in sorted(ids)]
    members, pending = [], deque()
    keys = iter(sorted(ids))
    pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="rv-census")
    try:
        while True:
            while len(pending) < 4:
                try:
                    report_id = next(keys)
                except StopIteration:
                    break
                pending.append(pool.submit(_census_member, store, report_id, read_cache=read_cache))
            if not pending:
                break
            # Deterministic report order, at most four member reads admitted.
            # A failure submits no next member and never abandons started I/O.
            members.append(pending.popleft().result())
    finally:
        for future in pending:
            future.cancel()
        pool.shutdown(wait=True)
    return members


class ProducerGenerationSession:
    """One in-process writer session over the incumbent canonical catalog."""

    @classmethod
    def begin(cls, store: Any, catalog: dict, identity: dict, *, now: datetime,
              evidence=None, read_cache=None):
        if not isinstance(now, datetime) or now.tzinfo is None:
            raise GenerationWriteUnavailable("explicit aware producer clock required")
        if (not isinstance(identity, dict)
                or set(identity) != {"source_commit", "run"}
                or not isinstance(identity["source_commit"], str)
                or len(identity["source_commit"]) != 40
                or any(c not in "0123456789abcdef" for c in identity["source_commit"])
                or not isinstance(identity["run"], str) or not identity["run"]
                or identity["run"] != identity["run"].strip()):
            raise GenerationWriteUnavailable("explicit producer identity required")
        if evidence is not None:
            from engine.research_vault.generation_evidence import FileGenerationEvidence
            if type(evidence) is not FileGenerationEvidence or evidence.identity != identity:
                raise GenerationWriteUnavailable("original evidence identity mismatch")
        for name in ("get_bytes_strict_bounded", "get_bytes_strict_bounded_versioned",
                     "put_bytes_strict_conditional",
                     "validate_strict_conditional_write_capability"):
            if not callable(getattr(store, name, None)):
                raise GenerationWriteUnavailable("conditional Store API required")
        store.validate_strict_conditional_write_capability()
        current = _catalog_read(store)
        if current is None:
            raise GenerationWriteUnavailable("legacy bootstrap first; no fenced cohort yet")
        selected = catalog_mod.parse_strict(current.data, now=now, check_future_clock=False)
        if contract.compute_catalog_payload_digest(selected) != contract.compute_catalog_payload_digest(catalog):
            raise GenerationWriteUnavailable("catalog moved before adoption")
        prior = selected.get(contract.GENERATION_FIELD)
        if prior is not None:
            contract.validate_generation(prior)
            if prior["state"] != contract.GENERATION_STATE_COMPLETE:
                raise GenerationWriteUnavailable("original BUILDING owner must settle")
        members = None if read_cache is None else read_cache.inherited_members(
            selected, prior, store, producer_commit=identity['source_commit'])
        if members is None:
            if read_cache is not None:
                read_cache.reset()
            members = _census(store, selected, read_cache=read_cache)
        if read_cache is not None:
            read_cache.seal(members)
        session = cls()
        session.store = store
        session.catalog_version = current.version
        session.catalog_bytes = current.data
        session.active = True
        session.failure = ""
        session.evidence = evidence
        session._confirmed_writes: dict[str, bytes] = {}
        session.record = {
            "schema": contract.GENERATION_SCHEMA, "epoch": str(uuid4()),
            "state": contract.GENERATION_STATE_BUILDING,
            "producer_source_commit": identity["source_commit"],
            "producer_run": identity["run"], "started_at": int(now.timestamp()),
            "catalog_members_sha256": contract.compute_catalog_members_digest([m["report_id"] for m in members]),
            "inventory_sha256": contract.compute_inventory_digest(members),
            "extractor_name": fulltext_store.EXTRACTOR_NAME,
            "extractor_version": fulltext_store.EXTRACTOR_VERSION,
            "extracted_text_schema": fulltext.EXTRACTED_TEXT_SCHEMA,
            "segmenter_version": fulltext.SEGMENTER_VERSION, "members": members,
        }
        if prior is not None and session.record["epoch"] == prior["epoch"]:
            raise GenerationWriteUnavailable("epoch generator reused predecessor")
        contract.validate_generation(session.record)
        selected[contract.GENERATION_FIELD] = copy.deepcopy(session.record)
        session._cas(_dump(selected))
        catalog[contract.GENERATION_FIELD] = copy.deepcopy(session.record)
        return session

    def _fail(self, reason: str):
        self.active = False
        self.failure = reason
        raise GenerationWriteUnavailable(reason)

    def _evidence(self, kind: str, payload: dict, *, reserve_bytes=0):
        if self.evidence is None:
            return None
        try:
            return self.evidence.append(kind, payload, reserve_bytes=reserve_bytes)
        except Exception as exc:
            self._fail("original-run evidence unavailable: " + type(exc).__name__)

    def _intent(self, key: str, data: bytes, content_type: str, *, conditional=False,
                expected_version=None):
        if self.evidence is None:
            return None
        payload = {"key": key, "sha256": _sha(data), "bytes": len(data),
                   "content_type": content_type, "conditional": conditional,
                   "expected_version": expected_version,
                   "epoch": self.record["epoch"]}
        # Preserve the actual visibility intent, including BEGIN/COMPLETE, before
        # its CAS. Corpus/PDF bytes stay on their existing carrier; the journal
        # records their actual write digest, never duplicates report contents.
        if key == catalog_mod.CATALOG_KEY:
            payload["catalog_base64"] = base64.b64encode(data).decode("ascii")
        return self._evidence("write_intent", payload,
                              reserve_bytes=POST_EFFECT_EVIDENCE_BYTES)

    def _result(self, operation, outcome: str):
        if self.evidence is not None:
            self._evidence("write_result", {"operation": operation, "outcome": outcome})

    def record_publication(self, corpus_path, pending_receipts, *, catalog_bytes: bytes):
        """Retain the exact batch before the corpus/catalog visibility cut.

        This is evidence for the original owner, not a replay or completion API.
        An unavailable sink refuses before this publication batch begins.
        """
        from pathlib import Path
        self.assert_current()
        path = Path(corpus_path)
        # The native image budget also binds direct library callers; lack of a
        # journal must not allow an oversized image to be written before COMPLETE
        # notices the bounded readback failure.
        if path.stat().st_size > contract.CORPUS_MAX_BYTES:
            self._fail("publication corpus outside evidence bound")
        if self.evidence is None:
            return
        try:
            if type(catalog_bytes) is not bytes or len(catalog_bytes) > contract.CATALOG_MAX_BYTES:
                self._fail("publication catalog outside evidence bound")
            planned = catalog_mod.parse_strict(catalog_bytes, check_future_clock=False)
            if planned.get(contract.GENERATION_FIELD) != self.record:
                self._fail("publication catalog must preserve current BUILDING")
            before = path.stat()
            if before.st_size > contract.CORPUS_MAX_BYTES:
                self._fail("publication corpus outside evidence bound")
            digest = hashlib.sha256()
            total = 0
            with path.open("rb") as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    total += len(block)
                    if total > contract.CORPUS_MAX_BYTES:
                        self._fail("publication corpus outside evidence bound")
                    digest.update(block)
            after = path.stat()
            if (total != before.st_size or
                    (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns)):
                self._fail("publication corpus changed during evidence capture")
            pending = [{"key": key, "sha256": _sha(data), "bytes": len(data),
                        "body_base64": base64.b64encode(data).decode("ascii")}
                       for key, data in pending_receipts]
            # Reserve the rest of this serial batch before its first effect:
            # catalog base64 fits within 2x raw bytes; two bounded opaque
            # versions plus fixed corpus/catalog metadata fit within 64KiB;
            # retain another 64KiB for the last intent's acknowledgement check.
            # Each receipt needs two fixed-size envelopes and its escaped key
            # (at most six JSON bytes per UTF-8 input byte), never its body again.
            reserve = (2 * len(catalog_bytes) + 2 * POST_EFFECT_EVIDENCE_BYTES
                       + sum(6 * len(row["key"].encode("utf-8")) + 4096 for row in pending))
            self._evidence("publication_plan", {
                "epoch": self.record["epoch"],
                "catalog_predecessor_sha256": _sha(self.catalog_bytes),
                "catalog_predecessor_version": self.catalog_version,
                "catalog_sha256": _sha(catalog_bytes), "catalog_bytes": len(catalog_bytes),
                "catalog_base64": base64.b64encode(catalog_bytes).decode("ascii"),
                "corpus_sha256": digest.hexdigest(), "corpus_bytes": before.st_size,
                "pending_receipts": pending}, reserve_bytes=reserve)
        except GenerationWriteUnavailable:
            raise
        except Exception as exc:
            self._fail("publication evidence unavailable: " + type(exc).__name__)

    def assert_current(self):
        if not self.active:
            raise GenerationWriteUnavailable(self.failure or "session closed")
        try:
            current = _catalog_read(self.store)
        except Exception as exc:
            self._fail("catalog currentness unavailable: " + type(exc).__name__)
        if (current is None or current.version != self.catalog_version
                or current.data != self.catalog_bytes):
            self._fail("catalog predecessor moved")

    def _cas(self, data: bytes):
        self.assert_current()
        operation = self._intent(catalog_mod.CATALOG_KEY, data, "application/json",
                                 conditional=True, expected_version=self.catalog_version)
        try:
            ok = self.store.put_bytes_strict_conditional(catalog_mod.CATALOG_KEY, data,
                                                  expected_version=self.catalog_version,
                                                  content_type="application/json")
        except Exception as exc:
            self._result(operation, "exception_effect_unknown")
            self._fail("catalog conditional effect uncertain: " + type(exc).__name__)
        if not ok:
            self._result(operation, "conditional_conflict")
            self._fail("catalog conditional conflict")
        self._result(operation, "returned_true")
        try:
            current = _catalog_read(self.store)
        except Exception as exc:
            self._fail("catalog conditional readback unavailable: " + type(exc).__name__)
        if current is None or current.data != data:
            self._fail("catalog conditional readback mismatch")
        self.catalog_bytes, self.catalog_version = current.data, current.version
        self._evidence("catalog_observed", {"sha256": _sha(current.data),
                       "version": current.version, "operation": operation})

    def prepare_catalog(self, document: dict) -> bytes:
        self.assert_current()
        # Every checkpoint remains BUILDING. It carries the measured starting
        # cut; no interim inventory or full coverage claim is made.
        document[contract.GENERATION_FIELD] = copy.deepcopy(self.record)
        return _dump(document)

    def put(self, key: str, data: bytes, content_type: str) -> bool:
        self.assert_current()
        if key == catalog_mod.CATALOG_KEY:
            document = catalog_mod.parse_strict(data, check_future_clock=False)
            block = document.get(contract.GENERATION_FIELD)
            if block != self.record:
                self._fail("catalog write must preserve current BUILDING")
            self._cas(data)
            return True
        operation = self._intent(key, data, content_type)
        try:
            ok = bool(self.store.put_bytes(key, data, content_type))
        except Exception as exc:
            self._result(operation, "exception_effect_unknown")
            self._fail("covered write effect uncertain: " + type(exc).__name__)
        if not ok:
            # The legacy Store boolean may hide a transport exception. False is
            # not proof that an unconditional PUT had no remote effect.
            self._result(operation, "returned_false_effect_unknown")
            self._fail("covered write rejected")
        self._result(operation, "returned_true")
        if key == contract.CORPUS_KEY or key.startswith(fulltext_store.RECEIPT_PREFIX):
            self._confirmed_writes[key] = data
        return True

    def complete(self, document: dict, *, now: datetime) -> bytes:
        try:
            return self._complete(document, now=now)
        except Exception as exc:
            self.active = False
            if not self.failure:
                self.failure = "completion refused: " + type(exc).__name__
            if isinstance(exc, GenerationWriteUnavailable):
                raise
            raise GenerationWriteUnavailable(self.failure) from None

    def _complete(self, document: dict, *, now: datetime) -> bytes:
        self.assert_current()
        published = catalog_mod.parse_strict(self.catalog_bytes, check_future_clock=False)
        if (contract.compute_catalog_payload_digest(document)
                != contract.compute_catalog_payload_digest(published)):
            self._fail("completion catalog was not published in BUILDING")
        if (not isinstance(now, datetime) or now.tzinfo is None
                or int(now.timestamp()) < self.record["started_at"]):
            self._fail("explicit completion clock must follow start")
        for key, expected in self._confirmed_writes.items():
            bound = (contract.CORPUS_MAX_BYTES if key == contract.CORPUS_KEY
                     else fulltext_store.RECEIPT_MAX_BYTES)
            if _read(self.store, key, bound) != expected:
                self._fail("covered write readback mismatch")
        if contract.CORPUS_KEY not in self._confirmed_writes:
            self._fail("final corpus publication not confirmed")
        corpus = _read(self.store, contract.CORPUS_KEY, contract.CORPUS_MAX_BYTES)
        if corpus is None:
            self._fail("current corpus absent")
        members = _census(self.store, document)
        _validate_fulltext_source_cut(corpus, document, members)
        record = copy.deepcopy(self.record)
        record.update(state=contract.GENERATION_STATE_COMPLETE,
                      completed_at=int(now.timestamp()), corpus_sha256=_sha(corpus),
                      catalog_payload_sha256=contract.compute_catalog_payload_digest(document),
                      members=members,
                      catalog_members_sha256=contract.compute_catalog_members_digest([m["report_id"] for m in members]),
                      inventory_sha256=contract.compute_inventory_digest(members),
                      classification_counts={layer: sum(m["layer"] == layer for m in members)
                                             for layer in contract.CLASSIFICATION_COUNT_KEYS})
        contract.validate_generation(record)
        selected = copy.deepcopy(document)
        selected[contract.GENERATION_FIELD] = record
        data = _dump(selected)
        self._cas(data)
        self._evidence("terminal", {"epoch": record["epoch"], "state": "COMPLETE",
                       "catalog_sha256": _sha(data), "catalog_version": self.catalog_version})
        self.active = False
        document[contract.GENERATION_FIELD] = record
        return data


class FencedProducerStore:
    """Existing Store reads stay unchanged; adopted producer PUTs use its fence."""

    def __init__(self, store: Any, session: ProducerGenerationSession):
        self._store = store
        self.generation_session = session

    def __getattr__(self, name: str):
        return getattr(self._store, name)

    def put_bytes(self, key: str, data: bytes, content_type: str = "application/octet-stream"):
        return self.generation_session.put(key, data, content_type)

    def put_bytes_strict_conditional(self, key: str, data: bytes, *,
                                    expected_version: str | None,
                                    content_type: str = "application/octet-stream"):
        self.generation_session.assert_current()
        # The incumbent fulltext writer alone creates immutable revisions.
        # A catalog or fixed-key conditional PUT must not bypass the session.
        if not key.startswith(fulltext_store.FULLTEXT_PREFIX) or expected_version is not None:
            raise GenerationWriteUnavailable("only immutable derivative conditional writes allowed")
        operation = self.generation_session._intent(
            key, data, content_type, conditional=True, expected_version=None)
        try:
            result = self._store.put_bytes_strict_conditional(
                key, data, expected_version=None, content_type=content_type)
        except Exception as exc:
            self.generation_session._result(operation, "exception_effect_unknown")
            self.generation_session._fail("immutable conditional effect uncertain: " + type(exc).__name__)
        self.generation_session._result(
            operation, "returned_true" if result else "conditional_conflict")
        return result
