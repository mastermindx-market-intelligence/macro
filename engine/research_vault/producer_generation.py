"""Producer-owned generation qualification for the Research Vault.

This module is the *consumer* side of the generation seam. The incumbent
research-ingest producer is expected to publish, inside the existing canonical
``research_vault/catalog.json`` visibility object, a strict closed ``producer_generation``
mapping that binds one exact cohort sweep: which report ids were admitted,
which receipt/derivative revisions were observed, how they classified, and the
exact corpus bytes the generation was built from.

This module deliberately does NOT:

- write, mutate, publish or delete any object (no store writes of any kind),
- list any prefix,
- read any ``.pdf`` key,
- run any extractor,
- implement the writer/CAS BUILDING protocol (that adoption is a prerequisite
  and belongs to the producer owner),
- act as an independent census: it validates a producer-declared generation
  against the live store, it never invents its own inventory.

Every store interaction is bounded, strict and fail-closed. Any absent,
malformed, oversized or operationally unavailable read makes the qualification
return ``False`` with a structured negative reason. There are no retries and
no fallbacks anywhere in this module.

Store protocol expected by :func:`qualify_current_generation` (all methods
must exist; a missing method is an operational failure, never a skip):

- ``get_bytes_strict_bounded(key, max_bytes) -> bytes | None`` -- the existing
  reader contract already used by ``fulltext_store``; ``None`` means absent,
  an exception means unavailable,
- ``get_bytes_strict_bounded_versioned(key, max_bytes) -> VersionedBytes``
  for the versioned catalog read; the opaque version is a nonempty string compared together with exact bytes;
  it is not a monotonic history or anti-ABA proof,
- ``get_bytes_strict_bounded(CORPUS_KEY, max_bytes) -> bytes | None`` -- the exact current
  FTS corpus bytes that ``corpus_sha256`` binds.

Object identity is always ``sha256`` over the exact bytes read. An ETag, MD5
or any other server-side convenience digest is never accepted as a SHA-256.
"""
from __future__ import annotations

import hashlib
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from itertools import islice
import json
import re
from typing import Any, NamedTuple

__all__ = [
    "GENERATION_SCHEMA",
    "GENERATION_FIELD",
    "GENERATION_STATE_BUILDING",
    "GENERATION_STATE_COMPLETE",
    "GENERATION_CATALOG_KEY",
    "CATALOG_MAX_BYTES",
    "CORPUS_MAX_BYTES",
    "SEGMENT_PROBE_MAX_BYTES",
    "FULL_RATIO_NUMERATOR",
    "FULL_RATIO_DENOMINATOR",
    "MEMBER_LAYERS",
    "FULL_NUMERATOR_LAYERS",
    "CLASSIFICATION_COUNT_KEYS",
    "BUILDING_KEYS",
    "COMPLETE_KEYS",
    "MEMBER_KEYS",
    "InvalidGeneration",
    "QualifiedSelection",
    "explained_selection",
    "canonical_json_bytes",
    "compute_catalog_members_digest",
    "compute_catalog_payload_digest",
    "compute_inventory_digest",
    "validate_generation",
    "inspect_generation",
    "admitted_cohort_from_catalog",
    "explained_qualification",
    "qualify_current_generation",
]

GENERATION_SCHEMA = "research_vault.producer_generation.v1"
GENERATION_FIELD = "producer_generation"
GENERATION_STATE_BUILDING = "BUILDING"
GENERATION_STATE_COMPLETE = "COMPLETE"

#: The existing canonical visibility object that carries the generation. This
#: constant matches the canonical catalog key; no sidecar or new object is used.
GENERATION_CATALOG_KEY = "research_vault/catalog.json"
CORPUS_KEY = "research_vault/corpus.sqlite"

CATALOG_MAX_BYTES = 16 * 1024 * 1024
CORPUS_MAX_BYTES = 256 * 1024 * 1024

#: Local identity probe budget for canonical segmenter builds. This proves the
#: declared ``segmenter_version`` is the one implemented by the imported
#: ``fulltext`` source; it is NOT a storage or production segment policy.
SEGMENT_PROBE_MAX_BYTES = 64 * 1024

#: Qualification numerator threshold: qualification requires
#: ``FULL_RATIO_NUMERATOR * full_count >= FULL_RATIO_DENOMINATOR * members``,
#: i.e. the integer-exact form of "at least 95% full" with no float rounding.
FULL_RATIO_NUMERATOR = 100
FULL_RATIO_DENOMINATOR = 95

MEMBER_LAYERS = frozenset(
    {"full", "thin", "none", "missing", "digest_unknown", "corrupt"}
)
#: Only these member layers contribute the qualification numerator.
FULL_NUMERATOR_LAYERS = frozenset({"full"})

CLASSIFICATION_COUNT_KEYS = frozenset(
    {"full", "thin", "none", "missing", "digest_unknown", "corrupt"}
)

#: BUILDING carries no completed payload: no completion time, no corpus
#: binding and no finalized classification counts.
BUILDING_KEYS = frozenset(
    {
        "schema",
        "epoch",
        "state",
        "producer_source_commit",
        "producer_run",
        "started_at",
        "catalog_members_sha256",
        "inventory_sha256",
        "extractor_name",
        "extractor_version",
        "extracted_text_schema",
        "segmenter_version",
        "members",
    }
)

COMPLETE_KEYS = BUILDING_KEYS | {
    "completed_at",
    "corpus_sha256",
    "classification_counts",
    "catalog_payload_sha256",
}

MEMBER_KEYS = frozenset(
    {
        "report_id",
        "source_pdf_sha256",
        "receipt_sha256",
        "derivative_record_sha256",
        "layer",
    }
)

_SHA256_RE = re.compile(r"\A[0-9a-f]{64}\Z")
_COMMIT_RE = re.compile(r"\A[0-9a-f]{40}\Z")


class QualifiedSelection(NamedTuple):
    """Immutable bytes retained from one successful qualification sweep.

    An internal consumer value, never a caller-supplied readiness assertion.
    Runtime reuse still requires the current writer policy and catalog fence.
    """

    epoch: str
    producer_source_commit: str
    catalog_version: str
    catalog_sha256: str
    catalog_bytes: bytes
    corpus_sha256: str
    corpus_bytes: bytes
    completed_at: int
    qualified_at: int


class InvalidGeneration(ValueError):
    """Raised when a generation mapping violates the strict closed contract.

    ``.reason`` is the structured negative reason:
    ``{"code": str, "detail": str, "context": dict}``.
    """

    def __init__(self, code: str, detail: str = "", **context: Any) -> None:
        self.reason = {"code": code, "detail": detail, "context": context}
        text = code if not detail else f"{code}: {detail}"
        super().__init__(text)


def canonical_json_bytes(value: Any) -> bytes:
    """Deterministic UTF-8 JSON used for every digest this module defines."""
    return json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def compute_catalog_members_digest(member_ids: list[str]) -> str:
    """Digest over the sorted admitted valid report ids, canonically encoded."""
    return hashlib.sha256(canonical_json_bytes(sorted(member_ids))).hexdigest()


def compute_catalog_payload_digest(catalog: dict[str, Any]) -> str:
    """Bind all canonical catalog fields except the embedded generation itself."""
    if not isinstance(catalog, dict):
        raise InvalidGeneration("catalog_not_mapping")
    payload = {key: value for key, value in catalog.items() if key != GENERATION_FIELD}
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def compute_inventory_digest(members: list[dict[str, Any]]) -> str:
    """Digest over the deterministic canonical member records, in member order."""
    return hashlib.sha256(canonical_json_bytes(list(members))).hexdigest()


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and _SHA256_RE.fullmatch(value) is not None


def _require_nonempty_str(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InvalidGeneration(f"{name}_must_be_nonempty_str", name=name)
    return value


def _require_report_id(value: Any) -> str:
    """Structural report-id rule; slug authority stays with ``corpus``."""
    if not isinstance(value, str) or not value or value != value.strip():
        raise InvalidGeneration("member_report_id_invalid")
    if "/" in value or "\x00" in value or value in (".", ".."):
        raise InvalidGeneration("member_report_id_invalid")
    return value


def _validate_member(member: Any, position: int) -> None:
    if not isinstance(member, dict):
        raise InvalidGeneration("member_not_mapping", position=position)
    if set(member) != set(MEMBER_KEYS):
        raise InvalidGeneration(
            "member_keyset_not_closed",
            "closed member keyset violated",
            position=position,
            missing=sorted(set(MEMBER_KEYS) - set(member)),
            unexpected=sorted(set(member) - set(MEMBER_KEYS)),
        )
    _require_report_id(member["report_id"])
    layer = member["layer"]
    if not isinstance(layer, str) or layer not in MEMBER_LAYERS:
        raise InvalidGeneration("member_layer_unsupported", position=position)
    for name, value in (
        ("source_pdf_sha256", member["source_pdf_sha256"]),
        ("receipt_sha256", member["receipt_sha256"]),
        ("derivative_record_sha256", member["derivative_record_sha256"]),
    ):
        if value is not None and not _is_sha256(value):
            raise InvalidGeneration(
                "member_sha_invalid", position=position, field=name
            )
    # Closed binding matrix: what each declared layer may and must bind.
    if layer in ("full", "thin", "none", "corrupt"):
        if (
            member["source_pdf_sha256"] is None
            or member["receipt_sha256"] is None
            or member["derivative_record_sha256"] is None
        ):
            raise InvalidGeneration(
                "member_binding_conflict", position=position, layer=layer
            )
    elif layer == "digest_unknown":
        if (
            member["source_pdf_sha256"] is not None
            or member["receipt_sha256"] is None
            or member["derivative_record_sha256"] is not None
        ):
            raise InvalidGeneration(
                "member_binding_conflict", position=position, layer=layer
            )
    else:  # missing
        # Missing receipt, or current receipt present but derivative absent.
        if (member["derivative_record_sha256"] is not None
                or ((member["receipt_sha256"] is None)
                    != (member["source_pdf_sha256"] is None))):
            raise InvalidGeneration(
                "member_binding_conflict", position=position, layer=layer
            )


def validate_generation(record: Any) -> dict[str, Any]:
    """Validate the strict closed generation contract; return it unchanged.

    Raises :class:`InvalidGeneration` (with a structured ``.reason``) on any
    violation. Digests, ordering, the closed keysets, the layer binding matrix
    and (for COMPLETE) the classification-count identity are all checked here;
    time freshness, cohort equality and live-store verification belong to the
    consumer because they depend on call arguments and store state.
    """
    if not isinstance(record, dict):
        raise InvalidGeneration("generation_not_mapping")
    if record.get("schema") != GENERATION_SCHEMA:
        raise InvalidGeneration("generation_schema_unsupported")
    state = record.get("state")
    if state not in (GENERATION_STATE_BUILDING, GENERATION_STATE_COMPLETE):
        raise InvalidGeneration("generation_state_unsupported")
    expected = BUILDING_KEYS if state == GENERATION_STATE_BUILDING else COMPLETE_KEYS
    actual = set(record)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing or extra:
        raise InvalidGeneration(
            "generation_keyset_not_closed",
            "closed keyset violated",
            missing=missing,
            unexpected=extra,
            state=state,
        )

    _require_nonempty_str(record["epoch"], "epoch")
    commit = record["producer_source_commit"]
    if not isinstance(commit, str) or _COMMIT_RE.fullmatch(commit) is None:
        raise InvalidGeneration("producer_source_commit_invalid")
    _require_nonempty_str(record["producer_run"], "producer_run")
    started_at = record["started_at"]
    if type(started_at) is not int or started_at < 0:
        raise InvalidGeneration("started_at_invalid")

    members = record["members"]
    if not isinstance(members, list) or not members:
        raise InvalidGeneration("generation_members_empty_or_not_list")

    member_ids: list[str] = []
    tally = {layer: 0 for layer in CLASSIFICATION_COUNT_KEYS}
    previous: str | None = None
    for position, member in enumerate(members):
        _validate_member(member, position)
        report_id = member["report_id"]
        if previous is not None and not report_id > previous:
            raise InvalidGeneration(
                "member_ids_not_sorted_unique", position=position
            )
        previous = report_id
        member_ids.append(report_id)
        tally[member["layer"]] += 1

    if compute_catalog_members_digest(member_ids) != record["catalog_members_sha256"]:
        raise InvalidGeneration("catalog_members_digest_mismatch")
    if compute_inventory_digest(members) != record["inventory_sha256"]:
        raise InvalidGeneration("inventory_digest_mismatch")

    if state == GENERATION_STATE_COMPLETE:
        completed_at = record["completed_at"]
        if type(completed_at) is not int or completed_at < 0:
            raise InvalidGeneration("completed_at_invalid")
        if completed_at < started_at:
            raise InvalidGeneration("completed_at_precedes_started_at")
        if not _is_sha256(record["corpus_sha256"]):
            raise InvalidGeneration("corpus_sha256_invalid")
        if not _is_sha256(record["catalog_payload_sha256"]):
            raise InvalidGeneration("catalog_payload_sha256_invalid")
        counts = record["classification_counts"]
        if not isinstance(counts, dict) or set(counts) != set(CLASSIFICATION_COUNT_KEYS):
            raise InvalidGeneration("classification_counts_keyset_not_closed")
        for layer, value in counts.items():
            if type(value) is not int or value < 0:
                raise InvalidGeneration(
                    "classification_count_invalid", layer=layer
                )
        if counts != tally:
            raise InvalidGeneration("classification_counts_mismatch")
    return record


def inspect_generation(record: Any) -> tuple[dict[str, Any] | None, dict | None]:
    """Non-raising variant: ``(record, None)`` when valid, ``(None, reason)``."""
    try:
        return validate_generation(record), None
    except InvalidGeneration as exc:
        return None, exc.reason


class _Fail(Exception):
    """Internal: ends qualification immediately with a structured reason."""

    def __init__(self, code: str, detail: str = "", **context: Any) -> None:
        self.reason = {"code": code, "detail": detail, "context": context}
        super().__init__(code)


def _load_source_modules():
    """Import the real decoder/segmenter/store sources; None when unavailable."""
    try:
        from engine.research_vault import catalog, corpus, fulltext, fulltext_store  # type: ignore
    except Exception:
        return None
    return catalog, corpus, fulltext, fulltext_store


def admitted_cohort_from_catalog(document: Any) -> tuple[str, ...] | None:
    """Admitted cohort from the canonical visibility object, in item order.

    Returns ``None`` when the document does not expose an ``items`` cohort at
    all (legacy shape): the caller treats that as cohort-unavailable, never as
    an empty cohort. Duplicates and structurally invalid ids fail the whole
    qualification; they are never silently deduplicated. Slug authority is
    applied by the caller through ``corpus.valid_doc_id``.
    """
    if not isinstance(document, dict):
        raise _Fail("catalog_not_mapping")
    if "items" not in document:
        return None
    items = document["items"]
    if not isinstance(items, list):
        raise _Fail("catalog_items_not_list")
    cohort: list[str] = []
    seen: set[str] = set()
    for position, item in enumerate(items):
        if not isinstance(item, dict):
            raise _Fail("catalog_item_not_mapping", position=position)
        try:
            report_id = _require_report_id(item.get("id"))
        except InvalidGeneration:
            raise _Fail("catalog_invalid_member", position=position)
        if report_id in seen:
            raise _Fail(
                "catalog_duplicate_member", position=position, report_id=report_id
            )
        seen.add(report_id)
        cohort.append(report_id)
    if not cohort:
        raise _Fail("catalog_cohort_empty")
    return tuple(cohort)


def _require_store_protocol(store: Any) -> None:
    for name in (
        "get_bytes_strict_bounded",
        "get_bytes_strict_bounded_versioned",
    ):
        if not callable(getattr(store, name, None)):
            raise _Fail("store_protocol_unavailable", name)


def _read_catalog(store: Any) -> tuple[bytes, Any]:
    reader = getattr(store, "get_bytes_strict_bounded_versioned", None)
    if not callable(reader):
        raise _Fail("store_protocol_unavailable", "get_bytes_strict_bounded_versioned")
    try:
        result = reader(GENERATION_CATALOG_KEY, CATALOG_MAX_BYTES)
    except Exception as exc:
        raise _Fail("catalog_read_unavailable", type(exc).__name__)
    if result is None:
        raise _Fail("catalog_read_unavailable")
    blob = getattr(result, "data", None)
    token = getattr(result, "version", None)
    if (type(blob) is not bytes or len(blob) > CATALOG_MAX_BYTES
            or type(token) is not str or not token):
        raise _Fail("catalog_read_unavailable")
    return blob, token


def _read_corpus(store: Any) -> bytes:
    reader = getattr(store, "get_bytes_strict_bounded", None)
    if not callable(reader):
        raise _Fail("store_protocol_unavailable", "get_bytes_strict_bounded")
    try:
        blob = reader(CORPUS_KEY, CORPUS_MAX_BYTES)
    except Exception as exc:
        raise _Fail("corpus_read_unavailable", type(exc).__name__)
    if type(blob) is not bytes or len(blob) > CORPUS_MAX_BYTES:
        raise _Fail("corpus_read_unavailable")
    return blob


def _read_strict(store: Any, key: str, max_bytes: int) -> bytes | None:
    reader = getattr(store, "get_bytes_strict_bounded", None)
    if not callable(reader):
        raise _Fail("store_protocol_unavailable", "get_bytes_strict_bounded")
    try:
        blob = reader(key, max_bytes)
    except Exception as exc:
        raise _Fail("store_read_unavailable", type(exc).__name__, key=key)
    if blob is not None and (type(blob) is not bytes or len(blob) > max_bytes):
        raise _Fail("store_read_unavailable", "non-bytes read", key=key)
    return blob


def _verify_member(
    store: Any,
    fulltext_mod: Any,
    store_mod: Any,
    generation: dict[str, Any],
    member: dict[str, Any],
) -> None:
    report_id = member["report_id"]
    layer = member["layer"]
    declared_receipt = member["receipt_sha256"]
    declared_source = member["source_pdf_sha256"]
    declared_derivative = member["derivative_record_sha256"]

    receipt_blob = _read_strict(
        store, store_mod.receipt_key(report_id), store_mod.RECEIPT_MAX_BYTES
    )
    receipt_sha = (
        None if receipt_blob is None else hashlib.sha256(receipt_blob).hexdigest()
    )
    if receipt_sha != declared_receipt:
        raise _Fail("member_receipt_changed", report_id=report_id)
    live_digest = None
    if receipt_blob is not None:
        live_digest = store_mod.parse_receipt_digest(receipt_blob, report_id)
    if live_digest != declared_source:
        raise _Fail("member_source_changed", report_id=report_id)

    if layer == "missing" and live_digest is not None:
        derivative = _read_strict(store, store_mod.derivative_key(report_id, live_digest),
                                  store_mod.FULLTEXT_MAX_BYTES)
        if derivative is not None:
            raise _Fail("member_derivative_changed", report_id=report_id)
        return
    if layer not in ("full", "thin", "none", "corrupt"):
        # Unknown digest or missing receipt; exact current receipt was checked.
        return

    derivative_blob = _read_strict(
        store,
        store_mod.derivative_key(report_id, live_digest),
        store_mod.FULLTEXT_MAX_BYTES,
    )
    if derivative_blob is None:
        raise _Fail("member_derivative_changed", report_id=report_id)
    if hashlib.sha256(derivative_blob).hexdigest() != declared_derivative:
        raise _Fail("member_derivative_changed", report_id=report_id)
    decoded = store_mod.decode_record(derivative_blob, report_id, live_digest)
    if layer == "corrupt":
        # The exact bound bytes must still fail the strict canonical decoder.
        if decoded is not None:
            raise _Fail("member_layer_mismatch", report_id=report_id)
        return
    if decoded is None:
        raise _Fail("member_derivative_corrupt", report_id=report_id)
    if decoded.get("text_layer_state") != layer:
        raise _Fail("member_layer_mismatch", report_id=report_id)
    try:
        segments = fulltext_mod.build_segments(
            decoded,
            segmenter_version=generation["segmenter_version"],
            max_bytes=SEGMENT_PROBE_MAX_BYTES,
        )
    except Exception as exc:
        raise _Fail(
            "segmenter_identity_mismatch",
            report_id=report_id,
            detail=type(exc).__name__,
        )
    if decoded.get("text"):
        if not segments:
            raise _Fail("segmenter_identity_mismatch", report_id=report_id)
    elif segments:
        raise _Fail("segmenter_identity_mismatch", report_id=report_id)


def _parallel_member_reads(store: Any) -> bool:
    from engine.research_vault.r2_store import R2Store

    candidate = store
    if type(store).__module__ == "engine.research_vault.qualified_reader":
        # Preparation has already loaded this module. The lazy exact-type check
        # avoids an import-time cycle and admits only our corpus-budget wrapper.
        from engine.research_vault.qualified_reader import _LimitedStore
        if type(store) is not _LimitedStore:
            return False
        candidate = store.store
    return (type(candidate) is R2Store
            and getattr(candidate, "_receipt_reads_thread_safe", False) is True)


def _verify_members(store, fulltext_mod, store_mod, generation, members):
    if not _parallel_member_reads(store):
        for member in members:
            _verify_member(store, fulltext_mod, store_mod, generation, member)
        return

    # Admit one finite window at a time, and consume errors in member order.
    # The next window cannot start until every member in this one succeeded.
    pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="rv-verify")
    pending = []
    iterator = iter(members)
    try:
        while batch := list(islice(iterator, 4)):
            pending = []
            for member in batch:
                pending.append(pool.submit(_verify_member, store, fulltext_mod,
                                           store_mod, generation, member))
            for future in pending:
                future.result()
            pending = []
    finally:
        for future in pending:
            future.cancel()
        # No in-flight read survives a failed qualification into another epoch.
        pool.shutdown(wait=True)


def _qualify(
    store: Any,
    catalog_mod: Any,
    corpus_mod: Any,
    fulltext_mod: Any,
    store_mod: Any,
    *,
    expected_producer_commit: str,
    now: int,
    max_age_seconds: int,
) -> QualifiedSelection:
    _require_store_protocol(store)
    blob1, token1 = _read_catalog(store)
    try:
        selected_now = datetime.fromtimestamp(now, timezone.utc)
        catalog = catalog_mod.parse_strict(blob1, now=selected_now)
        if catalog_mod.health(catalog, now=selected_now)["state"] != catalog_mod.STATE_FRESH:
            raise _Fail("catalog_stale")
    except _Fail:
        raise
    except Exception:
        raise _Fail("catalog_unreadable")

    if GENERATION_FIELD not in catalog:
        raise _Fail(
            "generation_absent", "legacy catalog without embedded generation"
        )
    generation = catalog[GENERATION_FIELD]
    if not isinstance(generation, dict):
        raise _Fail("generation_not_mapping")
    validate_generation(generation)

    if generation["state"] != GENERATION_STATE_COMPLETE:
        raise _Fail("generation_building")
    if compute_catalog_payload_digest(catalog) != generation["catalog_payload_sha256"]:
        raise _Fail("catalog_payload_mismatch")
    if generation["producer_source_commit"] != expected_producer_commit:
        raise _Fail("producer_commit_mismatch")
    completed_at = generation["completed_at"]
    if completed_at > now:
        raise _Fail("generation_from_future")
    if now - completed_at > max_age_seconds:
        raise _Fail("generation_stale")

    # Decoder/segmenter identity must be exactly the imported source constants.
    if (
        generation["extractor_name"] != store_mod.EXTRACTOR_NAME
        or generation["extractor_version"] != store_mod.EXTRACTOR_VERSION
        or generation["extracted_text_schema"] != fulltext_mod.EXTRACTED_TEXT_SCHEMA
        or generation["segmenter_version"] != fulltext_mod.SEGMENTER_VERSION
    ):
        raise _Fail("decoder_identity_mismatch")

    cohort = admitted_cohort_from_catalog(catalog)
    if cohort is None:
        raise _Fail(
            "catalog_cohort_unavailable", "catalog does not expose an items cohort"
        )
    for position, report_id in enumerate(cohort):
        if not corpus_mod.valid_doc_id(report_id):
            raise _Fail(
                "catalog_invalid_member", position=position, report_id=report_id
            )

    members = generation["members"]
    member_ids = [member["report_id"] for member in members]
    if sorted(cohort) != member_ids:
        raise _Fail("cohort_mismatch")

    counts = generation["classification_counts"]
    numerator = counts["full"]
    denominator = len(members)
    if FULL_RATIO_NUMERATOR * numerator < FULL_RATIO_DENOMINATOR * denominator:
        raise _Fail("full_ratio_below_threshold")

    _verify_members(store, fulltext_mod, store_mod, generation, members)

    corpus_blob = _read_corpus(store)
    if hashlib.sha256(corpus_blob).hexdigest() != generation["corpus_sha256"]:
        raise _Fail("corpus_mismatch")

    blob2, token2 = _read_catalog(store)
    if blob2 != blob1 or token2 != token1:
        raise _Fail(
            "catalog_moved",
            "catalog bytes or version changed during qualification",
        )

    return QualifiedSelection(
        epoch=generation["epoch"],
        producer_source_commit=generation["producer_source_commit"],
        catalog_version=token1,
        catalog_sha256=hashlib.sha256(blob1).hexdigest(),
        catalog_bytes=blob1,
        corpus_sha256=generation["corpus_sha256"],
        corpus_bytes=corpus_blob,
        completed_at=completed_at,
        qualified_at=now,
    )


def explained_selection(
    store: Any,
    *,
    expected_producer_commit: str,
    now: int,
    max_age_seconds: int,
    writer_protocol_qualified: bool = False,
) -> tuple[QualifiedSelection | None, dict | None]:
    """Return the exact selected bytes only after one complete fenced sweep."""
    if writer_protocol_qualified is not True:
        return None, {
            "code": "writer_protocol_qualified_required",
            "detail": (
                "consumer gate requires a literal True writer-adoption "
                "qualification established outside this module"
            ),
            "context": {},
        }
    if (
        not isinstance(expected_producer_commit, str)
        or _COMMIT_RE.fullmatch(expected_producer_commit) is None
    ):
        return None, {
            "code": "expected_producer_commit_invalid",
            "detail": "must be 40 lowercase hex",
            "context": {},
        }
    if type(now) is not int or now < 0:
        return None, {
            "code": "now_invalid",
            "detail": "must be integer UTC seconds",
            "context": {},
        }
    if type(max_age_seconds) is not int or max_age_seconds < 0:
        return None, {
            "code": "max_age_seconds_invalid",
            "detail": "must be a nonnegative int",
            "context": {},
        }

    sources = _load_source_modules()
    if sources is None:
        return None, {
            "code": "source_identity_unavailable",
            "detail": "engine.research_vault fulltext/fulltext_store/corpus not importable",
            "context": {},
        }
    catalog_mod, corpus_mod, fulltext_mod, store_mod = sources

    try:
        selected = _qualify(
            store,
            catalog_mod,
            corpus_mod,
            fulltext_mod,
            store_mod,
            expected_producer_commit=expected_producer_commit,
            now=now,
            max_age_seconds=max_age_seconds,
        )
    except _Fail as exc:
        return None, exc.reason
    except InvalidGeneration as exc:
        return None, exc.reason
    except Exception as exc:  # operational/unknown: fail closed, never True
        return None, {
            "code": "unexpected_error",
            "detail": type(exc).__name__,
            "context": {},
        }
    return selected, None


def explained_qualification(
    store: Any,
    *,
    expected_producer_commit: str,
    now: int,
    max_age_seconds: int,
    writer_protocol_qualified: bool = False,
) -> tuple[bool, dict | None]:
    """Boolean compatibility view of the same single qualification sweep."""
    selected, reason = explained_selection(
        store,
        expected_producer_commit=expected_producer_commit,
        now=now,
        max_age_seconds=max_age_seconds,
        writer_protocol_qualified=writer_protocol_qualified,
    )
    return selected is not None, reason


def qualify_current_generation(
    store: Any,
    *,
    expected_producer_commit: str,
    now: int,
    max_age_seconds: int,
    writer_protocol_qualified: bool = False,
) -> bool:
    """Consumer gate: True only when the current catalog generation qualifies.

    Returns ``False`` with zero store reads unless ``writer_protocol_qualified``
    is literally ``True``: writer adoption cannot be inferred by this module,
    only externally established and recorded here. The default ``False`` is
    intentional. All qualification evidence is re-derived from live bounded
    strict reads on every call; nothing is cached or carried between calls.
    """
    ok, _reason = explained_qualification(
        store,
        expected_producer_commit=expected_producer_commit,
        now=now,
        max_age_seconds=max_age_seconds,
        writer_protocol_qualified=writer_protocol_qualified,
    )
    return ok
