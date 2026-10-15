"""Existing-producer catalog fence; no runtime qualification is enabled here.

Only an explicitly identified producer may adopt a legacy/COMPLETE catalog.
BUILDING is never taken over automatically. Other writers and old effects must
be settled outside this helper before writer_protocol_qualified can become True.
"""
from __future__ import annotations

import copy
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
    return value


def _census_member(store: Any, report_id: str) -> dict:
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
    return {"report_id": report_id,
            "source_pdf_sha256": source,
            "receipt_sha256": None if receipt is None else _sha(receipt),
            "derivative_record_sha256": None if record is None else _sha(record),
            "layer": layer}


def _census(store: Any, document: dict) -> list[dict]:
    ids = contract.admitted_cohort_from_catalog(document)
    if not ids:
        raise GenerationWriteUnavailable("adopted generation needs admitted cohort")
    from engine.research_vault.r2_store import R2Store
    # Same ordinary prebuilt client qualification as the incumbent receipt
    # reader. Strict receipt/derivative reads share no response bodies, perform
    # no writes and create no clients. Injected, wrapped and subclass stores
    # remain serial; duck typing does not establish thread safety.
    if type(store) is not R2Store or store._receipt_reads_thread_safe is not True:
        return [_census_member(store, report_id) for report_id in sorted(ids)]
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
                pending.append(pool.submit(_census_member, store, report_id))
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
    def begin(cls, store: Any, catalog: dict, identity: dict, *, now: datetime):
        if not isinstance(now, datetime) or now.tzinfo is None:
            raise GenerationWriteUnavailable("explicit aware producer clock required")
        if (not isinstance(identity, dict)
                or set(identity) != {"source_commit", "run"}
                or not isinstance(identity["source_commit"], str)
                or len(identity["source_commit"]) != 40
                or any(c not in "0123456789abcdef" for c in identity["source_commit"])
                or not isinstance(identity["run"], str) or not identity["run"].strip()):
            raise GenerationWriteUnavailable("explicit producer identity required")
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
        members = _census(store, selected)
        session = cls()
        session.store = store
        session.catalog_version = current.version
        session.catalog_bytes = current.data
        session.active = True
        session.failure = ""
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
        try:
            ok = self.store.put_bytes_strict_conditional(catalog_mod.CATALOG_KEY, data,
                                                  expected_version=self.catalog_version,
                                                  content_type="application/json")
        except Exception as exc:
            self._fail("catalog conditional effect uncertain: " + type(exc).__name__)
        if not ok:
            self._fail("catalog conditional conflict")
        try:
            current = _catalog_read(self.store)
        except Exception as exc:
            self._fail("catalog conditional readback unavailable: " + type(exc).__name__)
        if current is None or current.data != data:
            self._fail("catalog conditional readback mismatch")
        self.catalog_bytes, self.catalog_version = current.data, current.version

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
        try:
            ok = bool(self.store.put_bytes(key, data, content_type))
        except Exception as exc:
            self._fail("covered write effect uncertain: " + type(exc).__name__)
        if not ok:
            self._fail("covered write rejected")
        if key == contract.CORPUS_KEY or key.startswith(fulltext_store.RECEIPT_PREFIX):
            self._confirmed_writes[key] = data
        return True

    def complete(self, document: dict, *, now: datetime) -> bytes:
        try:
            return self._complete(document, now=now)
        except Exception as exc:
            self.active = False
            self.failure = "completion refused: " + type(exc).__name__
            if isinstance(exc, GenerationWriteUnavailable):
                raise
            raise GenerationWriteUnavailable(self.failure) from None

    def _complete(self, document: dict, *, now: datetime) -> bytes:
        self.assert_current()
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
        return self._store.put_bytes_strict_conditional(
            key, data, expected_version=None, content_type=content_type)
