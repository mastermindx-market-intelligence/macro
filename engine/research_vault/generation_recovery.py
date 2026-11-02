"""Read-only reconstruction, never executor settlement or recovery permission.

The owner must independently authenticate the original capture, original source,
executor quiescence and exclusive writer custody, then validate the live objects.
This helper does none of those things and opens no store. Its initial supported
subset contains exactly one acknowledged, observed BUILDING publication and a
possibly unissued tail of planned receipts. Any uncertain effect is refused.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re

from engine.research_vault import catalog, corpus, fulltext_store
from engine.research_vault import producer_generation as contract
from engine.research_vault.generation_evidence import (
    read_evidence,
    _identity,
    _pairs,
    _nonfinite,
)


class RecoveryPlanUnavailable(ValueError):
    """A bounded reason code, never source content or a private path."""


def _refuse(code):
    raise RecoveryPlanUnavailable(code)


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _digest(value):
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        _refuse("DIGEST_INVALID")
    return value


def _size(value, limit):
    if type(value) is not int or not 0 <= value <= limit:
        _refuse("BYTE_BOUND_INVALID")
    return value


def _version(value):
    if type(value) is not str or not value or len(value.encode("utf-8")) > 4096:
        _refuse("VERSION_INVALID")
    return value


def _blob(encoded, size, digest, limit):
    _size(size, limit)
    _digest(digest)
    if type(encoded) is not str or len(encoded) > 4 * ((limit + 2) // 3):
        _refuse("BODY_INVALID")
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error):
        _refuse("BODY_INVALID")
    if (
        base64.b64encode(raw).decode("ascii") != encoded
        or len(raw) != size
        or _sha(raw) != digest
    ):
        _refuse("BODY_IDENTITY_MISMATCH")
    return raw


def _receipt_id(key):
    if (
        type(key) is not str
        or not key.startswith(fulltext_store.RECEIPT_PREFIX)
        or not key.endswith(".json")
    ):
        _refuse("RECEIPT_KEY_INVALID")
    rid = key[len(fulltext_store.RECEIPT_PREFIX) : -5]
    if not corpus.valid_doc_id(rid):
        _refuse("RECEIPT_KEY_INVALID")
    return rid


def _document(raw, identity, epoch=None):
    document = catalog.parse_strict(raw, check_future_clock=False)
    record = document.get(contract.GENERATION_FIELD)
    contract.validate_generation(record)
    if record["state"] != contract.GENERATION_STATE_BUILDING:
        _refuse("BUILDING_REQUIRED_NO_COMPLETE_REPLAY")
    if (
        record["producer_source_commit"] != identity["source_commit"]
        or record["producer_run"] != identity["run"]
        or (epoch is not None and record["epoch"] != epoch)
    ):
        _refuse("ORIGINAL_IDENTITY_MISMATCH")
    return document, record


def _intent(payload, identity, epoch):
    keys = {
        "key",
        "sha256",
        "bytes",
        "content_type",
        "conditional",
        "expected_version",
        "epoch",
    }
    key = payload.get("key")
    if key == catalog.CATALOG_KEY:
        keys.add("catalog_base64")
    if (
        set(payload) != keys
        or payload["epoch"] != epoch
        or type(payload["conditional"]) is not bool
    ):
        _refuse("INTENT_INVALID")
    _digest(payload["sha256"])
    if key == catalog.CATALOG_KEY:
        if (
            payload["conditional"] is not True
            or payload["content_type"] != "application/json"
        ):
            _refuse("CATALOG_INTENT_INVALID")
        _version(payload["expected_version"])
        body = _blob(
            payload["catalog_base64"],
            payload["bytes"],
            payload["sha256"],
            contract.CATALOG_MAX_BYTES,
        )
        _document(body, identity, epoch)
    else:
        if payload["conditional"] or payload["expected_version"] is not None:
            _refuse("UNSUPPORTED_CONDITIONAL_INTENT")
        if key == contract.CORPUS_KEY:
            _size(payload["bytes"], contract.CORPUS_MAX_BYTES)
            if payload["content_type"] != "application/x-sqlite3":
                _refuse("CORPUS_INTENT_INVALID")
        elif type(key) is str and key.startswith(fulltext_store.RECEIPT_PREFIX):
            _receipt_id(key)
            _size(payload["bytes"], fulltext_store.RECEIPT_MAX_BYTES)
            if payload["content_type"] != "application/json":
                _refuse("RECEIPT_INTENT_INVALID")
        elif (
            type(key) is str
            and key.startswith("research_vault/")
            and key.endswith(".pdf")
            and corpus.valid_doc_id(key[15:-4])
        ):
            _size(payload["bytes"], 64 * 1024 * 1024)
            if payload["content_type"] != "application/pdf":
                _refuse("PDF_INTENT_INVALID")
        else:
            _refuse("UNSUPPORTED_WRITE_KEY")
    return dict(payload)


def _analyze(events, identity):
    if (
        type(events) is not list
        or not 0 < len(events) <= 100_000
        or events[0] != {"kind": "header", "payload": {"identity": identity}}
    ):
        _refuse("ORIGINAL_HEADER_REQUIRED")
    pending = observed_pending = current = plan = None
    epoch = None
    acknowledged = {}
    phase = "before_plan"
    tail_index = 0
    for index, event in enumerate(events[1:], 1):
        if (
            type(event) is not dict
            or set(event) != {"kind", "payload"}
            or type(event["payload"]) is not dict
        ):
            _refuse("EVENT_INVALID")
        kind, payload = event["kind"], event["payload"]
        if kind == "write_intent":
            if pending is not None or observed_pending is not None:
                _refuse("UNSETTLED_PRIOR_INTENT")
            if epoch is None:
                if index != 1 or payload.get("key") != catalog.CATALOG_KEY:
                    _refuse("ORIGINAL_BEGIN_REQUIRED")
                initial = _blob(
                    payload.get("catalog_base64"),
                    payload.get("bytes"),
                    payload.get("sha256"),
                    contract.CATALOG_MAX_BYTES,
                )
                _, record = _document(initial, identity)
                epoch = record["epoch"]
            intent = _intent(payload, identity, epoch)
            if (
                intent["key"] == catalog.CATALOG_KEY
                and current is not None
                and intent["expected_version"] != current["version"]
            ):
                _refuse("CATALOG_PREDECESSOR_MISMATCH")
            if (
                plan is None
                and current is not None
                and not (
                    intent["key"].startswith("research_vault/")
                    and intent["key"].endswith(".pdf")
                )
            ):
                _refuse("UNPLANNED_PREPUBLICATION_EFFECT")
            if plan is not None:
                expected = (
                    plan["corpus_intent"]
                    if phase == "corpus"
                    else (
                        plan["catalog_intent"]
                        if phase == "catalog"
                        else (
                            plan["receipts"][tail_index]
                            if phase == "receipts"
                            and tail_index < len(plan["receipts"])
                            else None
                        )
                    )
                )
                if expected is None or any(
                    intent.get(k) != expected[k]
                    for k in (
                        "key",
                        "sha256",
                        "bytes",
                        "content_type",
                        "conditional",
                        "expected_version",
                    )
                ):
                    _refuse("PUBLICATION_ORDER_OR_BODY_MISMATCH")
                if (
                    phase == "catalog"
                    and intent["catalog_base64"] != plan["catalog_base64"]
                ):
                    _refuse("PUBLICATION_CATALOG_MISMATCH")
            pending = index, intent
        elif kind == "write_result":
            if (
                set(payload) != {"operation", "outcome"}
                or type(payload["operation"]) is not int
                or pending is None
                or payload["operation"] != pending[0]
            ):
                _refuse("RESULT_ORDER_MISMATCH")
            if payload["outcome"] != "returned_true":
                _refuse("UNCERTAIN_OR_REJECTED_EFFECT")
            operation, intent = pending
            acknowledged[intent["key"]] = {
                k: intent[k] for k in ("key", "sha256", "bytes")
            }
            pending = None
            if intent["key"] == catalog.CATALOG_KEY:
                observed_pending = operation, intent
            elif plan is not None:
                if phase == "corpus":
                    phase = "catalog"
                elif phase == "receipts":
                    tail_index += 1
                else:
                    _refuse("PUBLICATION_ORDER_MISMATCH")
        elif kind == "catalog_observed":
            if (
                set(payload) != {"sha256", "version", "operation"}
                or type(payload["operation"]) is not int
                or observed_pending is None
                or payload["operation"] != observed_pending[0]
                or payload["sha256"] != observed_pending[1]["sha256"]
            ):
                _refuse("CATALOG_OBSERVATION_MISMATCH")
            _, intent = observed_pending
            current = {
                "sha256": payload["sha256"],
                "version": _version(payload["version"]),
                "bytes": _blob(
                    intent["catalog_base64"],
                    intent["bytes"],
                    intent["sha256"],
                    contract.CATALOG_MAX_BYTES,
                ),
            }
            observed_pending = None
            if plan is not None:
                if phase != "catalog":
                    _refuse("PUBLICATION_ORDER_MISMATCH")
                phase = "receipts"
        elif kind == "publication_plan":
            if (
                plan is not None
                or pending is not None
                or observed_pending is not None
                or current is None
            ):
                _refuse("AMBIGUOUS_OR_UNSETTLED_PUBLICATION")
            required = {
                "epoch",
                "catalog_predecessor_sha256",
                "catalog_predecessor_version",
                "catalog_sha256",
                "catalog_bytes",
                "catalog_base64",
                "corpus_sha256",
                "corpus_bytes",
                "pending_receipts",
            }
            if (
                set(payload) != required
                or payload["epoch"] != epoch
                or payload["catalog_predecessor_sha256"] != current["sha256"]
                or payload["catalog_predecessor_version"] != current["version"]
            ):
                _refuse("PUBLICATION_PREDECESSOR_MISMATCH")
            body = _blob(
                payload["catalog_base64"],
                payload["catalog_bytes"],
                payload["catalog_sha256"],
                contract.CATALOG_MAX_BYTES,
            )
            doc, record = _document(body, identity, epoch)
            _, predecessor = _document(current["bytes"], identity, epoch)
            if record != predecessor:
                _refuse("BUILDING_RECORD_CHANGED")
            members = frozenset(contract.admitted_cohort_from_catalog(doc))
            if type(payload["pending_receipts"]) is not list or len(
                payload["pending_receipts"]
            ) > len(members):
                _refuse("RECEIPT_PLAN_INVALID")
            receipts, seen = [], set()
            for row in payload["pending_receipts"]:
                if type(row) is not dict or set(row) != {
                    "key",
                    "sha256",
                    "bytes",
                    "body_base64",
                }:
                    _refuse("RECEIPT_PLAN_INVALID")
                rid = _receipt_id(row["key"])
                if rid not in members or row["key"] in seen:
                    _refuse("RECEIPT_PLAN_INVALID")
                raw = _blob(
                    row["body_base64"],
                    row["bytes"],
                    row["sha256"],
                    fulltext_store.RECEIPT_MAX_BYTES,
                )
                receipt = json.loads(
                    raw.decode("utf-8"),
                    object_pairs_hook=_pairs,
                    parse_constant=_nonfinite,
                )
                source_digest = fulltext_store.parse_receipt_digest(raw, rid)
                if (
                    type(receipt) is not dict
                    or receipt.get("id") != rid
                    or source_digest is None
                ):
                    _refuse("RECEIPT_IDENTITY_MISMATCH")
                promoted = acknowledged.get("research_vault/" + rid + ".pdf")
                if promoted is not None and promoted["sha256"] != source_digest:
                    _refuse("RECEIPT_PROMOTED_PDF_MISMATCH")
                seen.add(row["key"])
                receipts.append(
                    {
                        **row,
                        "body": raw,
                        "content_type": "application/json",
                        "conditional": False,
                        "expected_version": None,
                    }
                )
            _size(payload["corpus_bytes"], contract.CORPUS_MAX_BYTES)
            _digest(payload["corpus_sha256"])
            plan = {
                "catalog_base64": payload["catalog_base64"],
                "catalog_body": body,
                "receipts": receipts,
                "catalog_intent": {
                    "key": catalog.CATALOG_KEY,
                    "sha256": payload["catalog_sha256"],
                    "bytes": payload["catalog_bytes"],
                    "content_type": "application/json",
                    "conditional": True,
                    "expected_version": current["version"],
                },
                "corpus_intent": {
                    "key": contract.CORPUS_KEY,
                    "sha256": payload["corpus_sha256"],
                    "bytes": payload["corpus_bytes"],
                    "content_type": "application/x-sqlite3",
                    "conditional": False,
                    "expected_version": None,
                },
            }
            phase = "corpus"
        else:
            _refuse("UNSUPPORTED_OR_TERMINAL_EVENT")
    if pending is not None or observed_pending is not None:
        _refuse("UNSETTLED_FINAL_INTENT")
    if plan is None or phase != "receipts" or current["bytes"] != plan["catalog_body"]:
        _refuse("VISIBLE_PUBLICATION_REQUIRED")
    return {
        "state": "REQUIRES_OWNER_AND_LIVE_VALIDATION",
        "identity": dict(identity),
        "epoch": epoch,
        "catalog_bytes": current["bytes"],
        "catalog_sha256": current["sha256"],
        "catalog_version": current["version"],
        "corpus_sha256": plan["corpus_intent"]["sha256"],
        "corpus_bytes": plan["corpus_intent"]["bytes"],
        "unissued_receipts": tuple(
            (r["key"], r["body"]) for r in plan["receipts"][tail_index:]
        ),
        "required_live_checks": tuple(acknowledged.values()),
        "required_pdf_checks": tuple(
            {
                "key": "research_vault/" + _receipt_id(row["key"]) + ".pdf",
                "sha256": fulltext_store.parse_receipt_digest(
                    row["body"], _receipt_id(row["key"])
                ),
            }
            for row in plan["receipts"]
        ),
        "execution_authorized": False,
    }


def analyze_settled_publication(events, *, expected_identity):
    """Pure bounded planning over inspected events; not a capture/custody proof."""
    try:
        return _analyze(events, _identity(expected_identity))
    except RecoveryPlanUnavailable:
        raise
    except Exception:
        raise RecoveryPlanUnavailable("ORIGINAL_PUBLICATION_UNAVAILABLE") from None


def inspect_settled_publication(path, *, expected_identity, original_capture_sha256):
    """Inspect a closed captured journal; returned bytes stay private.

    A matching caller-supplied digest is not authenticated original custody.
    The result cannot be used as a grant to resume or write any object.
    """
    try:
        _digest(original_capture_sha256)
        events = read_evidence(
            path,
            expected_identity=expected_identity,
            expected_sha256=original_capture_sha256,
        )
        return analyze_settled_publication(events, expected_identity=expected_identity)
    except RecoveryPlanUnavailable:
        raise
    except Exception:
        raise RecoveryPlanUnavailable("ORIGINAL_PUBLICATION_UNAVAILABLE") from None


def inspect_live_settled_publication(
    store, path, *, expected_identity, original_capture_sha256,
    byte_budget=256 * 1024 * 1024,
):
    """Compare original recorded effects with bounded current reads, never write.

    The catalog must retain its exact bytes AND opaque version across the sweep.
    Every acknowledged object and every planned receipt's PDF must match. An
    unissued receipt must still be absent; a visible matching receipt cannot
    settle an unknown request. This observation grants no writer custody, proves
    no executor quiescence, and cannot authorize continuation or COMPLETE.
    The caller owns the existing Store and authenticates the original capture.
    """
    try:
        if type(byte_budget) is not int or not 0 < byte_budget <= 1024 * 1024 * 1024:
            _refuse("LIVE_BYTE_BUDGET_INVALID")
        plan = inspect_settled_publication(
            path, expected_identity=expected_identity,
            original_capture_sha256=original_capture_sha256,
        )
        read = getattr(store, "get_bytes_strict_bounded", None)
        versioned = getattr(store, "get_bytes_strict_bounded_versioned", None)
        if not callable(read) or not callable(versioned):
            _refuse("LIVE_STORE_PROTOCOL_UNAVAILABLE")
        remaining, observed = byte_budget, set()

        def consume(raw, bound, *, missing=False):
            nonlocal remaining
            if raw is None and missing:
                remaining -= 1
                return None
            if type(raw) is not bytes or len(raw) > bound:
                _refuse("LIVE_OBJECT_UNAVAILABLE")
            remaining -= max(1, len(raw))
            return raw

        def bound(maximum):
            if remaining <= 0:
                _refuse("LIVE_BYTE_BUDGET_EXHAUSTED")
            return min(max(1, maximum), remaining)

        def catalog_fence():
            maximum = bound(len(plan["catalog_bytes"]))
            current = versioned(catalog.CATALOG_KEY, maximum)
            raw = consume(getattr(current, "data", None), maximum)
            if (raw != plan["catalog_bytes"]
                    or type(getattr(current, "version", None)) is not str
                    or current.version != plan["catalog_version"]):
                _refuse("LIVE_CATALOG_MOVED")

        catalog_fence()
        for row in plan["required_live_checks"]:
            if row["key"] == catalog.CATALOG_KEY:
                continue
            maximum = bound(row["bytes"])
            raw = consume(read(row["key"], maximum), maximum)
            if len(raw) != row["bytes"] or _sha(raw) != row["sha256"]:
                _refuse("LIVE_OBJECT_CHANGED")
            observed.add((row["key"], row["sha256"]))
        for row in plan["required_pdf_checks"]:
            if (row["key"], row["sha256"]) in observed:
                continue
            maximum = bound(64 * 1024 * 1024)
            raw = consume(read(row["key"], maximum), maximum)
            if _sha(raw) != row["sha256"]:
                _refuse("LIVE_PDF_CHANGED")
            observed.add((row["key"], row["sha256"]))
        for key, _body in plan["unissued_receipts"]:
            maximum = bound(1)
            if consume(read(key, maximum), maximum, missing=True) is not None:
                _refuse("LIVE_UNISSUED_RECEIPT_PRESENT")
        catalog_fence()
        return {**plan, "state": "LIVE_BYTES_OBSERVED_OWNER_VALIDATION_REQUIRED",
                "read_budget_used": byte_budget - remaining,
                "execution_authorized": False}
    except RecoveryPlanUnavailable:
        raise
    except Exception:
        raise RecoveryPlanUnavailable("LIVE_VALIDATION_UNAVAILABLE") from None
