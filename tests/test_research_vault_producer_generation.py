"""Source-level tests for producer-generation consumer qualification.

Uses the actual canonical catalog, decoder, segmenter, corpus slug rule and
LocalStore APIs. MemoryStore and synthetic corpus/report bytes provide controlled
causal negatives; one test uses the actual filesystem LocalStore. No fixture
proves R2 operation, all-writer adoption, cached ReadService binding or production
coverage. Literal writer_protocol_qualified=True is injected only into tests;
the deployed runtime must remain unavailable until its prerequisites qualify.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from types import SimpleNamespace
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest

_ARTIFACT_DIR = os.path.dirname(os.path.abspath(__file__))

# Source integration uses the actual canonical decoder, catalog, corpus slug
# authority and Store. Artifact review may name its pinned reference source root.
_reference_root = os.environ.get("RESEARCH_GENERATION_TEST_ROOT")
if _reference_root:
    sys.path.insert(0, _reference_root)


from engine.research_vault import corpus as corpus_mod  # noqa: E402
from engine.research_vault import fulltext as fulltext_mod  # noqa: E402
from engine.research_vault import fulltext_store as store_mod  # noqa: E402

_module_path = os.path.join(_ARTIFACT_DIR, "producer_generation.py")
if not os.path.isfile(_module_path):
    _module_path = os.path.join(os.path.dirname(_ARTIFACT_DIR), "engine", "research_vault", "producer_generation.py")
_spec = importlib.util.spec_from_file_location("producer_generation", _module_path)
pg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pg)

COMMIT = "abcdef0123456789abcdef0123456789abcdef01"
OTHER_COMMIT = "0123456789abcdef0123456789abcdef01234567"
NOW = 1_700_000_000
STARTED_AT = NOW - 60
COMPLETED_AT = NOW - 50
MAX_AGE_SECONDS = 3600
CORPUS_BYTES = b"legacy fts corpus export v1\n"

FULL_TEXT = "alpha report page\fbeta report page"
THIN_TEXT = "x"
NONE_TEXT = ""


def sha256_hex(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


class MemoryStore:
    """Minimal in-memory strict versioned store matching the consumer protocol.

    ``None`` from a read means absent; an exception means unavailable. Every
    read is recorded so tests can assert there are no retries or extra reads.
    """

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.versions: dict[str, str] = {}
        self.version_seq = 0
        self.corpus: bytes | None = CORPUS_BYTES
        self.reads: list[tuple[str, str]] = []
        self.fail_strict_reads = False
        self.midflight = None  # callable(store) run inside the corpus read

    def set_object(self, key: str, blob: bytes) -> None:
        self.version_seq += 1
        self.objects[key] = blob
        self.versions[key] = f"v{self.version_seq}"

    def get_bytes_strict_bounded(self, key: str, max_bytes: int) -> bytes | None:
        if key == pg.CORPUS_KEY:
            return self._read_corpus_fixture(max_bytes)
        self.reads.append(("strict", key))
        if self.fail_strict_reads:
            raise RuntimeError("store unavailable")
        blob = self.objects.get(key)
        if blob is None:
            return None
        if len(blob) > max_bytes:
            raise ValueError("object exceeds read bound")
        return blob

    def get_bytes_strict_bounded_versioned(self, key: str, max_bytes: int):
        self.reads.append(("versioned", key))
        blob = self.objects.get(key)
        if blob is None:
            return None
        if len(blob) > max_bytes:
            raise ValueError("object exceeds read bound")
        return SimpleNamespace(data=blob, version=self.versions.get(key))

    def _read_corpus_fixture(self, max_bytes: int) -> bytes | None:
        self.reads.append(("corpus", "*"))
        if self.corpus is None:
            return None
        if len(self.corpus) > max_bytes:
            raise ValueError("corpus exceeds read bound")
        if self.midflight is not None:
            hook, self.midflight = self.midflight, None
            hook(self)
        return self.corpus


def _receipt_bytes(report_id: str, kind: str, pdf_sha: str) -> bytes:
    if kind == "digest_unknown":
        # Receipt exists but binds no usable content digest.
        return json.dumps({"id": report_id, "note": "digest unavailable"},
                          sort_keys=True, separators=(",", ":")).encode("utf-8")
    return json.dumps({"id": report_id, "content_sha256": pdf_sha},
                      sort_keys=True, separators=(",", ":")).encode("utf-8")


def _derivative_bytes(report_id: str, kind: str, pdf_sha: str) -> bytes:
    text = {"full": FULL_TEXT, "thin": THIN_TEXT, "none": NONE_TEXT}[kind]
    record = fulltext_mod.build_extracted_text(
        report_id=report_id,
        source_pdf_sha256=pdf_sha,
        text=text,
        extractor_name=store_mod.EXTRACTOR_NAME,
        extractor_version=store_mod.EXTRACTOR_VERSION,
        page_count=None,
        text_layer_state=kind,
    )
    return store_mod.encode_record(record)


def build_members(store: MemoryStore, spec: dict[str, str],
                  declare: dict[str, str] | None = None) -> list[dict]:
    """Materialize receipts/derivatives for ``spec`` and return the members.

    ``spec`` maps report id to the *stored* kind; ``declare`` optionally maps a
    report id to a *declared* layer different from what is stored (used only by
    the layer-mismatch negative tests; digests are computed after the override).
    """
    declare = declare or {}
    members: list[dict] = []
    for report_id in sorted(spec):
        kind = spec[report_id]
        pdf_sha = sha256_hex(b"pdf:" + report_id.encode("utf-8"))
        member = {
            "report_id": report_id,
            "source_pdf_sha256": None,
            "receipt_sha256": None,
            "derivative_record_sha256": None,
            "layer": declare.get(report_id, kind),
        }
        if kind != "missing":
            receipt_blob = _receipt_bytes(report_id, kind, pdf_sha)
            store.set_object(store_mod.receipt_key(report_id), receipt_blob)
            member["receipt_sha256"] = sha256_hex(receipt_blob)
        if kind in ("full", "thin", "none", "corrupt"):
            if kind == "corrupt":
                blob = b"{this is not a canonical derivative record"
            else:
                blob = _derivative_bytes(report_id, kind, pdf_sha)
            store.set_object(store_mod.derivative_key(report_id, pdf_sha), blob)
            member["derivative_record_sha256"] = sha256_hex(blob)
        if kind in ("full", "thin", "none", "corrupt"):
            member["source_pdf_sha256"] = pdf_sha
        members.append(member)
    return members


def write_catalog(store: MemoryStore, items: list[str],
                  generation: dict | None) -> bytes:
    document: dict = {
        "schema": "research_vault.catalog.v1",
        "generated_at": datetime.fromtimestamp(NOW - 50, timezone.utc).isoformat(),
        "count": len(items),
        "institutions": [],
        "items": [{"id": rid} for rid in items],
    }
    if generation is not None:
        if generation["state"] == pg.GENERATION_STATE_COMPLETE:
            generation["catalog_payload_sha256"] = pg.compute_catalog_payload_digest(document)
        document[pg.GENERATION_FIELD] = generation
    blob = json.dumps(document, sort_keys=True, separators=(",", ":")).encode("utf-8")
    store.set_object(pg.GENERATION_CATALOG_KEY, blob)
    return blob


def build_generation(store: MemoryStore, spec: dict[str, str], *,
                     overrides: dict | None = None,
                     tamper: dict | None = None,
                     declare: dict[str, str] | None = None,
                     state: str = pg.GENERATION_STATE_COMPLETE,
                     epoch: str = "epoch-1",
                     completed_at: int = COMPLETED_AT) -> dict:
    """Install a full fixture into ``store`` and return the generation mapping.

    ``overrides`` replace generation fields before digests/counts are derived;
    ``tamper`` is applied last with no recomputation, so a tampered field makes
    the mapping inconsistent exactly like an accidental or hostile edit.
    """
    members = build_members(store, spec, declare=declare)
    counts = {layer: 0 for layer in pg.CLASSIFICATION_COUNT_KEYS}
    for member in members:
        counts[member["layer"]] += 1
    member_ids = [member["report_id"] for member in members]
    generation: dict = {
        "schema": pg.GENERATION_SCHEMA,
        "epoch": epoch,
        "state": state,
        "producer_source_commit": COMMIT,
        "producer_run": "fixture-run-1",
        "started_at": STARTED_AT,
        "catalog_members_sha256": pg.compute_catalog_members_digest(member_ids),
        "inventory_sha256": pg.compute_inventory_digest(members),
        "extractor_name": store_mod.EXTRACTOR_NAME,
        "extractor_version": store_mod.EXTRACTOR_VERSION,
        "extracted_text_schema": fulltext_mod.EXTRACTED_TEXT_SCHEMA,
        "segmenter_version": fulltext_mod.SEGMENTER_VERSION,
        "members": members,
    }
    if overrides:
        generation.update(overrides)
    if state == pg.GENERATION_STATE_COMPLETE:
        generation["completed_at"] = completed_at
        generation["corpus_sha256"] = sha256_hex(CORPUS_BYTES)
        generation["classification_counts"] = counts
    if tamper:
        generation.update(tamper)
    write_catalog(store, member_ids, generation)
    return generation


def run(store: MemoryStore, *, commit: str = COMMIT,
        writer: bool = True, now: int = NOW,
        max_age: int = MAX_AGE_SECONDS):
    return pg.explained_qualification(
        store,
        expected_producer_commit=commit,
        now=now,
        max_age_seconds=max_age,
        writer_protocol_qualified=writer,
    )


def spec_with(count: int, kinds: dict[str, int]) -> dict[str, str]:
    """``count`` full members plus named extra kinds, ids in stable order."""
    spec = {f"r-{index:05d}": "full" for index in range(count)}
    next_index = count
    for kind, number in sorted(kinds.items()):
        for _ in range(number):
            spec[f"r-{next_index:05d}"] = kind
            next_index += 1
    return spec


class WriterGateTests(unittest.TestCase):
    """The writer-adoption gate must close before any store interaction."""

    def _read_sensitive_store(self) -> MemoryStore:
        store = MemoryStore()

        def boom(*_args, **_kwargs):
            raise AssertionError("store read attempted with gate closed")

        store.get_bytes_strict_bounded = boom  # type: ignore[assignment]
        store.get_bytes_strict_bounded_versioned = boom  # type: ignore[assignment]
        store._read_corpus_fixture = boom  # type: ignore[assignment]
        return store

    def test_default_gate_false_zero_reads(self) -> None:
        store = self._read_sensitive_store()
        self.assertFalse(
            pg.qualify_current_generation(
                store,
                expected_producer_commit=COMMIT,
                now=NOW,
                max_age_seconds=MAX_AGE_SECONDS,
            )
        )
        self.assertEqual(store.reads, [])

    def test_explicit_false_gate_zero_reads(self) -> None:
        store = self._read_sensitive_store()
        ok, reason = run(store, writer=False)
        self.assertFalse(ok)
        self.assertEqual(reason["code"], "writer_protocol_qualified_required")
        self.assertEqual(store.reads, [])

    def test_truthy_non_true_gate_zero_reads(self) -> None:
        store = self._read_sensitive_store()
        self.assertFalse(
            pg.qualify_current_generation(
                store,
                expected_producer_commit=COMMIT,
                now=NOW,
                max_age_seconds=MAX_AGE_SECONDS,
                writer_protocol_qualified=1,
            )
        )
        self.assertEqual(store.reads, [])

    def test_invalid_arguments_zero_reads(self) -> None:
        for kwargs in (
            {"commit": "zz"},
            {"commit": "ABCDEF0123456789ABCDEF0123456789ABCDEF01"},
            {"commit": COMMIT[:39]},
            {"now": "1700000000"},
            {"now": True},
            {"max_age": -1},
            {"max_age": True},
        ):
            store = MemoryStore()
            ok, reason = run(store, **kwargs)
            self.assertFalse(ok)
            self.assertIn(
                reason["code"],
                {
                    "expected_producer_commit_invalid",
                    "now_invalid",
                    "max_age_seconds_invalid",
                },
            )
            self.assertEqual(store.reads, [])


class ValidQualificationTests(unittest.TestCase):
    def test_valid_generation_qualifies(self) -> None:
        store = MemoryStore()
        build_generation(store, spec_with(19, {"none": 1}))  # 19/20 = 95%
        ok, reason = run(store)
        self.assertTrue(ok, reason)

    def test_valid_generation_with_every_layer_kind_qualifies(self) -> None:
        store = MemoryStore()
        # 96 full + thin + none + corrupt + digest_unknown + missing = 96/101.
        build_generation(
            store,
            spec_with(96, {"thin": 1, "none": 1, "corrupt": 1,
                           "digest_unknown": 1, "missing": 1}),
        )
        ok, reason = run(store)
        self.assertTrue(ok, reason)

    def test_threshold_exactly_95_percent_qualifies(self) -> None:
        store = MemoryStore()
        build_generation(store, spec_with(190, {"none": 10}))  # 190/200
        ok, reason = run(store)
        self.assertTrue(ok, reason)

    def test_94_99_percent_fails_integer_threshold(self) -> None:
        store = MemoryStore()
        build_generation(store, spec_with(9499, {"none": 5001}))  # 94.99%
        ok, reason = run(store)
        self.assertFalse(ok)
        self.assertEqual(reason["code"], "full_ratio_below_threshold")

    def test_95_00_percent_at_thousand_scale_qualifies(self) -> None:
        store = MemoryStore()
        build_generation(store, spec_with(9500, {"none": 500}))  # exactly 95%
        ok, reason = run(store)
        self.assertTrue(ok, reason)

    def test_all_thin_fails_threshold(self) -> None:
        store = MemoryStore()
        build_generation(store, {f"r-{index:05d}": "thin" for index in range(20)})
        ok, reason = run(store)
        self.assertFalse(ok)
        self.assertEqual(reason["code"], "full_ratio_below_threshold")


class CatalogShapeTests(unittest.TestCase):
    def test_legacy_catalog_without_generation_fails(self) -> None:
        store = MemoryStore()
        generation = build_generation(store, spec_with(19, {"none": 1}))
        self.assertIsNotNone(generation)
        write_catalog(store, sorted(f"r-{index:05d}" for index in range(20)), None)
        ok, reason = run(store)
        self.assertFalse(ok)
        self.assertEqual(reason["code"], "generation_absent")

    def test_building_generation_fails(self) -> None:
        store = MemoryStore()
        build_generation(store, spec_with(19, {"none": 1}),
                         state=pg.GENERATION_STATE_BUILDING)
        ok, reason = run(store)
        self.assertFalse(ok)
        self.assertEqual(reason["code"], "generation_building")

    def test_building_must_not_carry_completed_payload(self) -> None:
        store = MemoryStore()
        generation = build_generation(store, spec_with(19, {"none": 1}),
                                      state=pg.GENERATION_STATE_BUILDING)
        leaked = dict(generation)
        leaked["completed_at"] = COMPLETED_AT
        record, reason = pg.inspect_generation(leaked)
        self.assertIsNone(record)
        self.assertEqual(reason["code"], "generation_keyset_not_closed")

    def test_catalog_bytes_moved_midflight_fails(self) -> None:
        store = MemoryStore()
        build_generation(store, spec_with(19, {"none": 1}))

        def concurrent_writer(fresh_store: MemoryStore) -> None:
            # A writer takes the catalog to a NEW epoch between consumer reads.
            generation = build_generation(fresh_store, spec_with(19, {"none": 1}),
                                          epoch="epoch-2")
            assert generation["epoch"] == "epoch-2"

        store.midflight = concurrent_writer
        ok, reason = run(store)
        self.assertFalse(ok)
        self.assertEqual(reason["code"], "catalog_moved")

    def test_catalog_token_moved_same_bytes_fails(self) -> None:
        store = MemoryStore()
        build_generation(store, spec_with(19, {"none": 1}))

        def recharged_token(fresh_store: MemoryStore) -> None:
            fresh_store.version_seq += 1
            fresh_store.versions[pg.GENERATION_CATALOG_KEY] = (
                f"v{fresh_store.version_seq}"
            )

        store.midflight = recharged_token
        ok, reason = run(store)
        self.assertFalse(ok)
        self.assertEqual(reason["code"], "catalog_moved")

    def test_freshness_window(self) -> None:
        store = MemoryStore()
        build_generation(store, spec_with(19, {"none": 1}),
                         completed_at=NOW - MAX_AGE_SECONDS,
                         overrides={"started_at": NOW - MAX_AGE_SECONDS - 10})
        ok, reason = run(store)
        self.assertTrue(ok, reason)  # age == max_age is still fresh

        stale = MemoryStore()
        build_generation(stale, spec_with(19, {"none": 1}),
                         completed_at=NOW - MAX_AGE_SECONDS - 1,
                         overrides={"started_at": NOW - MAX_AGE_SECONDS - 10})
        ok, reason = run(stale)
        self.assertFalse(ok)
        self.assertEqual(reason["code"], "generation_stale")

    def test_completion_in_future_fails(self) -> None:
        store = MemoryStore()
        build_generation(store, spec_with(19, {"none": 1}),
                         completed_at=NOW + 10)
        ok, reason = run(store)
        self.assertFalse(ok)
        self.assertEqual(reason["code"], "generation_from_future")

    def test_producer_commit_mismatch_fails(self) -> None:
        store = MemoryStore()
        build_generation(store, spec_with(19, {"none": 1}))
        ok, reason = run(store, commit=OTHER_COMMIT)
        self.assertFalse(ok)
        self.assertEqual(reason["code"], "producer_commit_mismatch")


class MemberEvidenceTests(unittest.TestCase):
    """Every declared member binding is re-derived from live store reads."""

    def _store(self) -> MemoryStore:
        store = MemoryStore()
        build_generation(store, spec_with(19, {"none": 1}))
        return store

    def test_corrected_member_receipt_fails(self) -> None:
        store = self._store()
        report_id = "r-00000"
        new_pdf = sha256_hex(b"pdf:v2:" + report_id.encode("utf-8"))
        store.set_object(
            store_mod.receipt_key(report_id),
            _receipt_bytes(report_id, "full", new_pdf),
        )
        store.set_object(
            store_mod.derivative_key(report_id, new_pdf),
            _derivative_bytes(report_id, "full", new_pdf),
        )
        ok, reason = run(store)
        self.assertFalse(ok)
        self.assertEqual(reason["code"], "member_receipt_changed")

    def test_receipt_moved_ahead_of_member_source_fails(self) -> None:
        store = MemoryStore()
        build_generation(store, spec_with(19, {"none": 1}))
        report_id = "r-00000"
        new_pdf = sha256_hex(b"pdf:v2:" + report_id.encode("utf-8"))
        # Receipt content corrected in place; the member still binds the old
        # receipt bytes, so the live receipt digest no longer matches.
        store.set_object(
            store_mod.receipt_key(report_id),
            json.dumps({"id": report_id, "content_sha256": new_pdf},
                       sort_keys=True, separators=(",", ":")).encode("utf-8"),
        )
        ok, reason = run(store)
        self.assertFalse(ok)
        self.assertEqual(reason["code"], "member_receipt_changed")

    def test_old_derivative_revision_fails(self) -> None:
        store = MemoryStore()
        generation = build_generation(store, spec_with(19, {"none": 1}))
        report_id = "r-00000"
        declared_source = next(
            member["source_pdf_sha256"]
            for member in generation["members"]
            if member["report_id"] == report_id
        )
        self.assertIsNotNone(declared_source)
        # Overwrite the exact same revision key with different valid bytes.
        rewritten = fulltext_mod.build_extracted_text(
            report_id=report_id,
            source_pdf_sha256=declared_source,
            text="tampered replay\fother bytes",
            extractor_name=store_mod.EXTRACTOR_NAME,
            extractor_version=store_mod.EXTRACTOR_VERSION,
            page_count=None,
            text_layer_state="full",
        )
        store.set_object(
            store_mod.derivative_key(report_id, declared_source),
            store_mod.encode_record(rewritten),
        )
        ok, reason = run(store)
        self.assertFalse(ok)
        self.assertEqual(reason["code"], "member_derivative_changed")

    def test_declared_full_but_stored_thin_fails(self) -> None:
        store = MemoryStore()
        build_generation(store, {f"r-{index:05d}": "thin" for index in range(20)},
                         declare={f"r-{index:05d}": "full" for index in range(20)})
        ok, reason = run(store)
        self.assertFalse(ok)
        self.assertEqual(reason["code"], "member_layer_mismatch")

    def test_declared_corrupt_but_decodable_fails(self) -> None:
        store = MemoryStore()
        # 20 stored full, one declared corrupt: 19/20 = 95% still passes the
        # ratio gate, so the mismatch is reached at member verification.
        build_generation(store, spec_with(20, {}),
                         declare={"r-00000": "corrupt"})
        ok, reason = run(store)
        self.assertFalse(ok)
        self.assertEqual(reason["code"], "member_layer_mismatch")

    def test_derivative_read_unavailable_fails(self) -> None:
        store = self._store()
        key = store_mod.derivative_key("r-00000",
                                       sha256_hex(b"pdf:r-00000"))
        del store.objects[key]
        ok, reason = run(store)
        self.assertFalse(ok)
        self.assertEqual(reason["code"], "member_derivative_changed")

    def test_receipt_read_unavailable_fails(self) -> None:
        store = self._store()
        store.fail_strict_reads = True
        ok, reason = run(store)
        self.assertFalse(ok)
        self.assertEqual(reason["code"], "store_read_unavailable")


class CohortAndDigestTests(unittest.TestCase):
    def _generation(self, store: MemoryStore) -> dict:
        return build_generation(store, spec_with(19, {"none": 1}))

    def test_duplicate_cohort_fails_without_dedup(self) -> None:
        store = MemoryStore()
        generation = self._generation(store)
        ids = [member["report_id"] for member in generation["members"]]
        write_catalog(store, ids + [ids[0]], generation)
        ok, reason = run(store)
        self.assertFalse(ok)
        self.assertEqual(reason["code"], "catalog_duplicate_member")

    def test_invalid_cohort_member_fails(self) -> None:
        store = MemoryStore()
        generation = self._generation(store)
        ids = [member["report_id"] for member in generation["members"]]
        write_catalog(store, ids + ["Not_A_Slug"], generation)
        ok, reason = run(store)
        self.assertFalse(ok)
        self.assertEqual(reason["code"], "catalog_invalid_member")

    def test_cohort_mismatch_fails(self) -> None:
        store = MemoryStore()
        generation = self._generation(store)
        ids = [member["report_id"] for member in generation["members"]]
        write_catalog(store, ids + ["r-99999"], generation)
        ok, reason = run(store)
        self.assertFalse(ok)
        self.assertEqual(reason["code"], "cohort_mismatch")

    def test_wrong_inventory_digest_fails(self) -> None:
        store = MemoryStore()
        self._generation(store)
        ok, reason = run(store)
        self.assertTrue(ok)
        tampered = MemoryStore()
        build_generation(tampered, spec_with(19, {"none": 1}),
                         tamper={"inventory_sha256": "0" * 64})
        ok, reason = run(tampered)
        self.assertFalse(ok)
        self.assertEqual(reason["code"], "inventory_digest_mismatch")

    def test_wrong_catalog_members_digest_fails(self) -> None:
        store = MemoryStore()
        build_generation(store, spec_with(19, {"none": 1}),
                         tamper={"catalog_members_sha256": "0" * 64})
        ok, reason = run(store)
        self.assertFalse(ok)
        self.assertEqual(reason["code"], "catalog_members_digest_mismatch")

    def test_classification_count_identity_fails(self) -> None:
        store = MemoryStore()
        generation = self._generation(store)
        counts = dict(generation["classification_counts"])
        counts["full"] += 1
        store2 = MemoryStore()
        build_generation(store2, spec_with(19, {"none": 1}),
                         tamper={"classification_counts": counts})
        ok, reason = run(store2)
        self.assertFalse(ok)
        self.assertEqual(reason["code"], "classification_counts_mismatch")


class IdentityAndCorpusTests(unittest.TestCase):
    def test_bad_extractor_version_fails(self) -> None:
        store = MemoryStore()
        build_generation(store, spec_with(19, {"none": 1}),
                         overrides={"extractor_version": "pdftotext.v0"})
        ok, reason = run(store)
        self.assertFalse(ok)
        self.assertEqual(reason["code"], "decoder_identity_mismatch")

    def test_bad_extractor_name_fails(self) -> None:
        store = MemoryStore()
        build_generation(store, spec_with(19, {"none": 1}),
                         overrides={"extractor_name": "not-pdftotext"})
        ok, reason = run(store)
        self.assertFalse(ok)
        self.assertEqual(reason["code"], "decoder_identity_mismatch")

    def test_bad_extracted_text_schema_fails(self) -> None:
        store = MemoryStore()
        build_generation(store, spec_with(19, {"none": 1}),
                         overrides={"extracted_text_schema": "other.schema"})
        ok, reason = run(store)
        self.assertFalse(ok)
        self.assertEqual(reason["code"], "decoder_identity_mismatch")

    def test_bad_segmenter_version_fails(self) -> None:
        store = MemoryStore()
        build_generation(store, spec_with(19, {"none": 1}),
                         overrides={"segmenter_version": "page-byte-v9"})
        ok, reason = run(store)
        self.assertFalse(ok)
        self.assertEqual(reason["code"], "decoder_identity_mismatch")

    def test_corpus_mismatch_fails(self) -> None:
        store = MemoryStore()
        build_generation(store, spec_with(19, {"none": 1}))
        store.corpus = b"different corpus bytes"
        ok, reason = run(store)
        self.assertFalse(ok)
        self.assertEqual(reason["code"], "corpus_mismatch")

    def test_corpus_read_unavailable_fails(self) -> None:
        store = MemoryStore()
        build_generation(store, spec_with(19, {"none": 1}))
        store.corpus = None
        ok, reason = run(store)
        self.assertFalse(ok)
        self.assertEqual(reason["code"], "corpus_read_unavailable")

    def test_missing_store_method_fails(self) -> None:
        class NoCorpusStore(MemoryStore):
            get_bytes_strict_bounded = None  # type: ignore[assignment]
        naked = NoCorpusStore()
        build_generation(naked, spec_with(19, {"none": 1}))
        ok, reason = run(naked)
        self.assertFalse(ok)
        self.assertEqual(reason["code"], "store_protocol_unavailable")


class NoRetryTests(unittest.TestCase):
    def test_successful_qualification_reads_each_object_once(self) -> None:
        store = MemoryStore()
        build_generation(store, spec_with(19, {"none": 1}))
        ok, _reason = run(store)
        self.assertTrue(ok)
        counts: dict[tuple[str, str], int] = {}
        for entry in store.reads:
            counts[entry] = counts.get(entry, 0) + 1
        catalog_reads = counts.get(("versioned", pg.GENERATION_CATALOG_KEY), 0)
        self.assertEqual(catalog_reads, 2)  # initial + unchanged reread
        corpus_reads = counts.get(("corpus", "*"), 0)
        self.assertEqual(corpus_reads, 1)
        for (kind, _key), number in counts.items():
            if kind == "strict":
                self.assertEqual(number, 1)


class ValidationContractTests(unittest.TestCase):
    """Pure contract validation, no store involved."""

    def _minimal(self, **overrides) -> dict:
        members = [
            {
                "report_id": "r-001",
                "source_pdf_sha256": "a" * 64,
                "receipt_sha256": "b" * 64,
                "derivative_record_sha256": "c" * 64,
                "layer": "full",
            },
            {
                "report_id": "r-002",
                "source_pdf_sha256": None,
                "receipt_sha256": None,
                "derivative_record_sha256": None,
                "layer": "missing",
            },
        ]
        ids = [member["report_id"] for member in members]
        generation = {
            "schema": pg.GENERATION_SCHEMA,
            "epoch": "epoch-1",
            "state": pg.GENERATION_STATE_COMPLETE,
            "producer_source_commit": COMMIT,
            "producer_run": "run-1",
            "started_at": 1000,
            "completed_at": 2000,
            "catalog_members_sha256": pg.compute_catalog_members_digest(ids),
            "inventory_sha256": pg.compute_inventory_digest(members),
            "corpus_sha256": "d" * 64,
            "catalog_payload_sha256": "e" * 64,
            "extractor_name": "pdftotext",
            "extractor_version": "v1",
            "extracted_text_schema": "schema",
            "segmenter_version": "page-byte-v1",
            "classification_counts": {"full": 1, "thin": 0, "none": 0,
                                      "missing": 1, "digest_unknown": 0,
                                      "corrupt": 0},
            "members": members,
        }
        generation.update(overrides)
        return generation

    def test_minimal_complete_is_valid(self) -> None:
        record, reason = pg.inspect_generation(self._minimal())
        self.assertIsNotNone(record, reason)

    def test_state_unsupported(self) -> None:
        _record, reason = pg.inspect_generation(
            self._minimal(state="RUNNING"))
        self.assertEqual(reason["code"], "generation_state_unsupported")

    def test_schema_unsupported(self) -> None:
        _record, reason = pg.inspect_generation(
            self._minimal(schema="other.schema"))
        self.assertEqual(reason["code"], "generation_schema_unsupported")

    def test_empty_members_rejected(self) -> None:
        _record, reason = pg.inspect_generation(self._minimal(members=[]))
        self.assertEqual(reason["code"], "generation_members_empty_or_not_list")

    def test_duplicate_members_rejected(self) -> None:
        generation = self._minimal()
        generation["members"] = [generation["members"][0]] * 2
        _record, reason = pg.inspect_generation(generation)
        self.assertEqual(reason["code"], "member_ids_not_sorted_unique")

    def test_bad_commit_rejected(self) -> None:
        _record, reason = pg.inspect_generation(
            self._minimal(producer_source_commit="XYZ"))
        self.assertEqual(reason["code"], "producer_source_commit_invalid")

    def test_completed_before_started_rejected(self) -> None:
        _record, reason = pg.inspect_generation(
            self._minimal(completed_at=999))
        self.assertEqual(reason["code"], "completed_at_precedes_started_at")

    def test_bool_time_rejected(self) -> None:
        _record, reason = pg.inspect_generation(self._minimal(started_at=True))
        self.assertEqual(reason["code"], "started_at_invalid")

    def test_extra_key_rejected(self) -> None:
        _record, reason = pg.inspect_generation(self._minimal(surprise=1))
        self.assertEqual(reason["code"], "generation_keyset_not_closed")

    def test_member_binding_matrix(self) -> None:
        generation = self._minimal()
        generation["members"][1]["receipt_sha256"] = "b" * 64
        _record, reason = pg.inspect_generation(generation)
        self.assertEqual(reason["code"], "member_binding_conflict")

    def test_missing_layer_with_source_rejected(self) -> None:
        generation = self._minimal()
        generation["members"][1]["source_pdf_sha256"] = "a" * 64
        _record, reason = pg.inspect_generation(generation)
        self.assertEqual(reason["code"], "member_binding_conflict")

    def test_invalid_member_sha_rejected(self) -> None:
        generation = self._minimal()
        generation["members"][0]["source_pdf_sha256"] = "A" * 64
        _record, reason = pg.inspect_generation(generation)
        self.assertEqual(reason["code"], "member_sha_invalid")

    def test_unknown_layer_rejected(self) -> None:
        generation = self._minimal()
        generation["members"][0]["layer"] = "partial"
        _record, reason = pg.inspect_generation(generation)
        self.assertEqual(reason["code"], "member_layer_unsupported")

    def test_non_string_json_layers_return_structured_refusal(self) -> None:
        for value in ([], {}, None, True, 1):
            with self.subTest(layer=value):
                generation = self._minimal()
                generation["members"][0]["layer"] = value
                record, reason = pg.inspect_generation(generation)
                self.assertIsNone(record)
                self.assertEqual(reason["code"], "member_layer_unsupported")

    def test_invalid_generation_exception_carries_reason(self) -> None:
        try:
            pg.validate_generation(self._minimal(surprise=1))
        except pg.InvalidGeneration as exc:
            self.assertEqual(exc.reason["code"], "generation_keyset_not_closed")
        else:  # pragma: no cover
            self.fail("InvalidGeneration not raised")


class CanonicalIntegrationRepairTests(unittest.TestCase):
    """Causal repairs using canonical schema/id/key and incumbent Store protocol."""
    def test_existing_localstore_versioned_protocol_and_keys(self):
        from engine.research_vault.r2_store import LocalStore
        memory = MemoryStore()
        build_generation(memory, spec_with(19, {"none": 1}))
        with tempfile.TemporaryDirectory(prefix="generation_localstore_") as root:
            store = LocalStore(root)
            for key, blob in memory.objects.items():
                self.assertTrue(store.put_bytes(key, blob))
            self.assertTrue(store.put_bytes(pg.CORPUS_KEY, CORPUS_BYTES))
            ok, reason = run(store)
            self.assertTrue(ok, reason)
            self.assertIn("research_vault/catalog.json", memory.objects)
            self.assertTrue(all("id" in item for item in json.loads(memory.objects[pg.GENERATION_CATALOG_KEY])["items"]))
    def test_bad_catalog_schema_refused(self):
        store = MemoryStore()
        build_generation(store, spec_with(19, {"none": 1}))
        catalog = json.loads(store.objects[pg.GENERATION_CATALOG_KEY])
        catalog["schema"] = "bogus"
        store.set_object(pg.GENERATION_CATALOG_KEY, json.dumps(catalog).encode())
        ok, reason = run(store)
        self.assertFalse(ok)
        self.assertEqual(reason["code"], "catalog_unreadable")
    def test_same_ids_metadata_correction_invalidates_payload_digest(self):
        store = MemoryStore()
        build_generation(store, spec_with(19, {"none": 1}))
        catalog = json.loads(store.objects[pg.GENERATION_CATALOG_KEY])
        catalog["items"][0]["title"] = "corrected title"
        store.set_object(pg.GENERATION_CATALOG_KEY, json.dumps(catalog).encode())
        ok, reason = run(store)
        self.assertFalse(ok)
        self.assertEqual(reason["code"], "catalog_payload_mismatch")
    def test_catalog_stale_and_future_clock_refused(self):
        for offset in [-86400, 86400]:
            store = MemoryStore()
            build_generation(store, spec_with(19, {"none": 1}))
            catalog = json.loads(store.objects[pg.GENERATION_CATALOG_KEY])
            catalog["generated_at"] = datetime.fromtimestamp(NOW + offset, timezone.utc).isoformat()
            store.set_object(pg.GENERATION_CATALOG_KEY, json.dumps(catalog).encode())
            ok, reason = run(store)
            self.assertFalse(ok)
            self.assertIn(reason["code"], {"catalog_stale", "catalog_unreadable"})
    def test_current_receipt_with_absent_derivative_keeps_missing_separate(self):
        store = MemoryStore()
        generation = build_generation(store, spec_with(19, {"missing": 1}))
        member = generation["members"][-1]
        digest = "a" * 64
        receipt = json.dumps({"id": member["report_id"], "content_sha256": digest}).encode()
        store.set_object(store_mod.receipt_key(member["report_id"]), receipt)
        member.update(source_pdf_sha256=digest, receipt_sha256=sha256_hex(receipt))
        generation["inventory_sha256"] = pg.compute_inventory_digest(generation["members"])
        write_catalog(store, [m["report_id"] for m in generation["members"]], generation)
        ok, reason = run(store)
        self.assertTrue(ok, reason)
        # The declared absence cannot hide a now-present derivative.
        store.set_object(store_mod.derivative_key(member["report_id"], digest),
                         _derivative_bytes(member["report_id"], "full", digest))
        ok, reason = run(store)
        self.assertFalse(ok)
        self.assertEqual(reason["code"], "member_derivative_changed")
    def test_opaque_token_must_be_nonempty_string(self):
        class InvalidTokenStore(MemoryStore):
            def get_bytes_strict_bounded_versioned(self, key, cap):
                result = super().get_bytes_strict_bounded_versioned(key, cap)
                return SimpleNamespace(data=result.data, version=True)
        store = InvalidTokenStore()
        build_generation(store, spec_with(19, {"none": 1}))
        ok, reason = run(store)
        self.assertFalse(ok)
        self.assertEqual(reason["code"], "catalog_read_unavailable")
    def test_building_cannot_retain_complete_payload(self):
        store = MemoryStore()
        generation = build_generation(store, spec_with(19, {"none": 1}))
        generation["state"] = pg.GENERATION_STATE_BUILDING
        value, reason = pg.inspect_generation(generation)
        self.assertIsNone(value)
        self.assertEqual(reason["code"], "generation_keyset_not_closed")
    def test_default_unqualified_gate_denies_identical_local_aba_restore(self):
        from engine.research_vault.r2_store import LocalStore
        memory = MemoryStore()
        generation = build_generation(memory, spec_with(19, {"none": 1}))
        original = memory.objects[pg.GENERATION_CATALOG_KEY]
        with tempfile.TemporaryDirectory(prefix="generation_local_aba_") as root:
            store = LocalStore(root)
            store.put_bytes(pg.GENERATION_CATALOG_KEY, original)
            before = store.get_bytes_strict_bounded_versioned(pg.GENERATION_CATALOG_KEY, pg.CATALOG_MAX_BYTES)
            building = json.loads(original)
            building[pg.GENERATION_FIELD]["state"] = pg.GENERATION_STATE_BUILDING
            building[pg.GENERATION_FIELD]["epoch"] = "fresh-building-epoch"
            for name in pg.COMPLETE_KEYS - pg.BUILDING_KEYS:
                building[pg.GENERATION_FIELD].pop(name)
            store.put_bytes(pg.GENERATION_CATALOG_KEY, json.dumps(building).encode())
            store.put_bytes(pg.GENERATION_CATALOG_KEY, original)
            restored = store.get_bytes_strict_bounded_versioned(pg.GENERATION_CATALOG_KEY, pg.CATALOG_MAX_BYTES)
            self.assertEqual(restored, before)  # token/bytes expose no anti-ABA history
            self.assertFalse(pg.qualify_current_generation(store,
                expected_producer_commit=COMMIT, now=NOW, max_age_seconds=MAX_AGE_SECONDS))
            # No claim that forced writer=True detects arbitrary illegal restoration.


if __name__ == "__main__":
    unittest.main()
