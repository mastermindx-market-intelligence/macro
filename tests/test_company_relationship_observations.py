"""Synthetic storage/replay controls; no private captures or economic-precision claims."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import threading

import pytest

from engine.company_intelligence import relationship_observations as subject
from engine.company_intelligence.relationship_candidates import inspect_candidate
from engine.earnings_release.receipts import receipt_for_char_span, sha256_text
from engine.research_vault.r2_store import LocalStore
from lib.dataos.registry import Registry


def encoded(value, *, indent=None):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False,
                      separators=(",", ":") if indent is None else None,
                      indent=indent).encode("utf-8")


def authority():
    return {key: False for key in ("rank", "gate", "size", "trade", "prediction")}


def bundle(*, padding=None, indent=2):
    """Declared synthetic review claims, never genuine reviewer credentials."""
    prefix = "synthé\r\n" * 5000 if padding is None else padding
    claim = "Aurora plans Widget integration into Boreal H200 Tensor Core GPUs in calendar Q2 2024."
    source = prefix + "2024-02-26. Memory production has begun. " + claim + "\r\nEnd of synthetic statement."
    start = source.index(claim)
    receipt = receipt_for_char_span(source=source, source_sha256=sha256_text(source),
                                    char_start=start, char_end=start + len(claim)).to_dict()
    candidate = {
        "schema": "company_intelligence.relationship_candidate/v1", "candidate_id": "synthetic-c01",
        "document": {"document_id": "synthetic-document", "version": "sha256:" + sha256_text(source),
                     "source_ref": "synthetic-only", "published_date": "2024-02-26"},
        "dataset_id": None, "temporal_row": None, "receipt": receipt,
        "assertion": {"kind": "product_integration", "subject_label": "Aurora", "object_label": "Boreal",
                      "product_scope": "Widget", "lifecycle": "planned", "magnitude": None},
        "revision": {"supersedes_candidate_id": None, "relation": "original"},
        "identity_annotations": None,
    }
    candidate_raw, source_raw = encoded(candidate, indent=indent), source.encode("utf-8")
    source_record = {
        "case_id": "synthetic-C01-source-case", "source_kind": "original_issuer_announcement",
        "source_url": "synthetic-only", "retrieved_at": "2026-10-09T00:00:00Z",
        "published_date": "2024-02-26", "published_instant": None,
        "raw_sha256": sha256(source_raw).hexdigest(), "source_bytes": len(source_raw),
        "source_encoding": "UTF-8 exact round-trip", "candidate_id": candidate["candidate_id"],
        "document_id": candidate["document"]["document_id"], "assertion": candidate["assertion"],
        "native_dataset_id": None, "canonical_identity_admission": False,
        "historical_system_replay": False, "source_purpose_rights_admitted": False,
        **{key: receipt[key] for key in ("char_start", "char_end", "byte_start", "byte_end", "span_sha256")},
    }
    record_raw = encoded(source_record)
    ids = ["C01", "C02", "C03", "C04", "C05", "C06"]
    web_rows = [{"case_id": case} for case in ids]
    web_rows[0].update({"primary_url": "synthetic-only", "native_kind": "product_integration",
                        "lifecycle": "planned", "source_representation_observed":
                        "WEB_RENDERED_HTML_WITH_SEPARATE_RETAINED_INPUT_PROVENANCE"})
    web = {"schema": "research.independent_semantic_judgments/v1", "rows": web_rows,
           "admission": "NOT_ADMITTED", "authority": authority(), "graph1_projection": None,
           "reviewer_label": "synthetic-unverified"}
    web_raw = encoded(web)
    pilot = [{"case_id": case} for case in ids]
    pilot[0].update({
        "schema": "gmi.native_adoption_pilot_case_adjudication/v1", "source_url": "synthetic-only",
        "source_local_parties": ["Aurora", "Boreal"],
        "scope": {"kind": "product_integration", "lifecycle": "planned"},
        "source_binding": {"metadata_file_sha256": sha256(record_raw).hexdigest(),
                           "raw_sha256": sha256(source_raw).hexdigest(), "source_bytes": len(source_raw),
                           "candidate_id": candidate["candidate_id"], "document_id": candidate["document"]["document_id"]},
        "independent_review": {"receipt": {"sha256": sha256(web_raw).hexdigest()}},
        "native_admission": "NOT_ADMITTED", "authority": authority(), "graph1_projection": None,
    })
    context_start, context_end = start - 30, min(len(source), start + len(claim) + 20)
    context = source[context_start:context_end].encode("utf-8")
    limits = {
        "native_production_admission": "NOT_ADMITTED", "graph1_projection": None,
        "authenticated_actor_or_source_custody": False, "historical_system_replay": False,
        "production_rights_admitted": False, "public_export_rights_admitted": False,
        "training_rights_admitted": False, "source_purpose_permission_receipt": None, **authority(),
    }
    first = {
        "schema": "gmi.retained_micron_first_reader_judgment/v1", "case_id": "C01",
        "original_case_id": source_record["case_id"], "first_reader": "synthetic-first-reader",
        "new_evidence_basis": "ACTUAL_RETAINED_UTF8_BYTES_AND_BOUND_CANDIDATE_READ",
        "judgment": "SUPPORTED_WITH_MANDATORY_SCOPE_QUALIFIERS", "limits": limits,
        "candidate_reference": {"candidate_id": candidate["candidate_id"], "document_id": candidate["document"]["document_id"]},
        "source_binding": {
            "source_sha256": sha256(source_raw).hexdigest(), "source_bytes": len(source_raw),
            "candidate_sha256": sha256(candidate_raw).hexdigest(), "candidate_bytes": len(candidate_raw),
            "metadata_sha256": sha256(record_raw).hexdigest(), "metadata_bytes": len(record_raw),
            "span": {"character_start": receipt["char_start"], "character_end": receipt["char_end"],
                     "byte_start": receipt["byte_start"], "byte_end": receipt["byte_end"],
                     "bytes": receipt["span_bytes"], "sha256": receipt["span_sha256"]},
            "context": {"character_start": context_start, "character_end": context_end,
                        "byte_start": len(source[:context_start].encode("utf-8")),
                        "byte_end": len(source[:context_end].encode("utf-8")),
                        "characters": context_end - context_start, "bytes": len(context),
                        "sha256": sha256(context).hexdigest()},
        },
        "semantic_findings": {
            "candidate_kind_fit": "product_integration", "candidate_lifecycle_fit": "planned",
            "source_local_subject": "Aurora", "source_local_object": "Boreal",
            "upstream_configuration": "Widget", "downstream_configuration": "Boreal H200 Tensor Core GPUs",
            "document_date": "2024-02-26", "published_instant": None, "publication_precision": "DATE",
            "canonical_subject_id": None, "canonical_object_id": None, "current_supply_state": "UNESTABLISHED",
            "independently_verified_commerce": False,
            "economics": {"quantity": None, "revenue_share": None, "purchase_amount": None,
                          "customer_allocation": None, "exclusivity": None},
        },
    }
    independent = {
        "schema": "research.retained_byte_semantic_judgment/v1", "case_id": "C01",
        "reviewer": "synthetic-independent-reader", "native_admission": "NOT_ADMITTED",
        "authority": authority(), "graph1_projection": None,
        "original_source": {"bytes": len(source_raw), "sha256": sha256(source_raw).hexdigest()},
        "original_candidate": {"bytes": len(candidate_raw), "sha256": sha256(candidate_raw).hexdigest(),
                               "candidate_id": candidate["candidate_id"]},
        "source_span": {**{key: receipt[key] for key in ("char_start", "char_end", "byte_start", "byte_end", "span_bytes")},
                        "sha256": receipt["span_sha256"]},
        "inspected_context": {"char_start": context_start + 1, "char_end": context_end - 1},
        "finding": {"status": "SUPPORTED_WITH_REQUIRED_QUALIFIERS", "kind": "product_integration",
                    "lifecycle": "planned", "subject_label": "Aurora", "object_label": "Boreal",
                    "component_scope": "Widget", "target_scope": "H200 Tensor Core GPUs",
                    "publication_date": "2024-02-26", "publication_instant": None, "magnitude": None},
        "limitations": {"source_publisher_authenticated_by_this_read": False,
                        "source_custody_authenticated": False, "independent_commerce_verified": False,
                        "production_rights_receipt": None, "public_export_rights_receipt": None,
                        "training_rights_receipt": None},
    }
    return {
        "review_set_id": "synthetic-observation", "case_id": "C01", "candidate_bytes": candidate_raw,
        "source_bytes": source_raw, "source_record_bytes": record_raw,
        "pilot_adjudications_bytes": b"".join(encoded(row) + b"\n" for row in pilot),
        "semantic_review_bytes": web_raw, "retained_first_review_bytes": encoded(first),
        "retained_independent_review_bytes": encoded(independent),
    }


class TracedStore:
    """Failure instrumentation delegates normal behavior to the actual LocalStore."""
    def __init__(self, inner):
        self.inner = inner
        self.reads = []
        self.puts = []
        self.validations = 0

    def validate_strict_conditional_write_capability(self):
        self.validations += 1
        return self.inner.validate_strict_conditional_write_capability()

    def get_bytes_strict_bounded(self, key, *, expected_byte_length, max_byte_length):
        self.reads.append((key, expected_byte_length, max_byte_length))
        return self.inner.get_bytes_strict_bounded(key, expected_byte_length=expected_byte_length,
                                                  max_byte_length=max_byte_length)

    def put_bytes_strict_conditional(self, key, data, *, expected_version, content_type="application/octet-stream"):
        self.puts.append((key, len(data), expected_version))
        return self.inner.put_bytes_strict_conditional(key, data, expected_version=expected_version,
                                                      content_type=content_type)

    def get_bytes(self, *args, **kwargs):
        raise AssertionError("legacy read fallback forbidden")

    get_bytes_strict = get_bytes
    get_bytes_strict_bounded_versioned = get_bytes
    exists = get_bytes
    list_prefix = get_bytes
    put_bytes = get_bytes


def local_store(tmp_path):
    root = tmp_path / "private-observations"
    root.mkdir()
    return TracedStore(LocalStore(root)), root


def inventory(root):
    return {str(path.relative_to(root)): (sha256(path.read_bytes()).hexdigest(), path.stat().st_mtime_ns)
            for path in root.rglob("*") if path.is_file() and not path.is_symlink()}


def manifest_path(root, reference):
    return root / subject.PREFIX / "commits/sha256" / (reference["sha256"] + ".json")


def stored_package(root, reference):
    manifest = json.loads(manifest_path(root, reference).read_bytes())
    chunks = [(root / subject.PREFIX / "chunks/sha256" / (d["sha256"] + ".bin")).read_bytes()
              for d in manifest["chunks"]]
    return manifest, json.loads(b"".join(chunks))


def install_forged_package(store, package):
    """Deliberately make a self-consistent archive, bypassing the producer for a tamper control."""
    raw = encoded(package)
    descriptors = []
    for offset in range(0, len(raw), 16384):
        chunk = raw[offset:offset + 16384]
        digest = sha256(chunk).hexdigest()
        store.put_bytes_strict_conditional(subject.PREFIX + "chunks/sha256/" + digest + ".bin",
                                           chunk, expected_version=None)
        descriptors.append({"sha256": digest, "byte_length": len(chunk)})
    manifest = encoded({"schema": subject.MANIFEST_SCHEMA, "producer_contract": subject.PRODUCER_CONTRACT,
                        "package_sha256": sha256(raw).hexdigest(), "package_byte_length": len(raw),
                        "chunks": descriptors})
    reference = {"schema": subject.REFERENCE_SCHEMA, "sha256": sha256(manifest).hexdigest(), "byte_length": len(manifest)}
    store.put_bytes_strict_conditional(subject.PREFIX + "commits/sha256/" + reference["sha256"] + ".json",
                                       manifest, expected_version=None)
    return reference


def assert_boundaries(result):
    assert result["admission"] == "NOT_ADMITTED"
    assert result["graph1_projection"] is None
    assert result["authority"] == authority()
    assert result["purpose_scope"]["source_purpose_permission"] == "NOT_ESTABLISHED"
    assert all(result["purpose_scope"][name] is False for name in ("production", "public_export", "training"))
    if result["inspection"] is not None:
        assert result["inspection"]["admission"] == "NOT_ADMITTED"
        assert result["inspection"]["authority"] == authority()
        assert result["inspection"]["graph1_projection"] is None


def test_native_local_append_preserves_all_bytes_and_full_inspection_then_repeats(tmp_path, monkeypatch):
    store, root = local_store(tmp_path)
    supplied = bundle()
    original = deepcopy(supplied)
    calls = []
    real = subject.inspect_candidate

    def spy(candidate, **options):
        calls.append(deepcopy(options))
        return real(candidate, **options)

    monkeypatch.setattr(subject, "inspect_candidate", spy)
    first = subject.append_relationship_observation(store, **supplied)
    assert first["status"] == "COMMITTED"
    assert len(calls) == 1 and calls[0]["as_of"] is None and calls[0]["include_support_text"] is False
    reference = first["reference"]
    assert set(reference) == {"schema", "sha256", "byte_length"}
    manifest, package = stored_package(root, reference)
    assert 3 <= len(manifest["chunks"]) <= 64
    assert manifest["package_byte_length"] <= 1024 * 1024
    assert reference["byte_length"] <= 16384
    expected = inspect_candidate(json.loads(supplied["candidate_bytes"]), source=supplied["source_bytes"].decode("utf-8"))
    assert first["inspection"] == package["inspection"] == expected
    assert expected["support"]["semantic_adjudication"] == "NOT_PERFORMED"
    for role in subject._ROLES:
        raw = supplied[role + "_bytes"]
        assert package["components"][role]["text"].encode("utf-8") == raw
        assert package["components"][role]["sha256"] == sha256(raw).hexdigest()
    assert package["canonical_candidate_payload_sha256"] == sha256(encoded(json.loads(supplied["candidate_bytes"]))).hexdigest()
    assert first["review_provenance"]["binding"]["scope_summary"] == {
        "component": "Widget", "target": "Boreal H200 Tensor Core GPUs", "lifecycle": "planned", "source_local_only": True}
    for name in ("authorship", "review_independence", "source_custody", "semantic_truth"):
        assert first["review_provenance"]["binding"][name] == "NOT_AUTHENTICATED"
    before, write_count = inventory(root), len(store.puts)
    repeat = subject.append_relationship_observation(store, **supplied)
    read = subject.read_relationship_observation(store, reference)
    assert repeat["status"] == "REPEATED" and repeat["reference"] == reference
    assert read["status"] == "VERIFIED" and read["inspection"] == expected
    assert read["replay_status"] == "MATCHED_SEALED_REQUEST"
    assert len(store.puts) == write_count and inventory(root) == before
    assert all(length <= 16384 and predecessor is None for _, length, predecessor in store.puts)
    assert all(0 < expected <= maximum == 16384 for _, expected, maximum in store.reads)
    assert supplied == original
    for result in (first, repeat, read):
        assert_boundaries(result)


class FaultStore(TracedStore):
    def __init__(self, inner, mode):
        super().__init__(inner)
        self.mode = mode
        self.final_key = None
        self.after_final_reads = 0

    def get_bytes_strict_bounded(self, key, **options):
        if key == self.final_key:
            self.after_final_reads += 1
            if self.mode == "final_unknown" or (self.mode == "closure_unknown" and self.after_final_reads >= 2):
                raise RuntimeError("private-host-path must never escape")
        return super().get_bytes_strict_bounded(key, **options)

    def put_bytes_strict_conditional(self, key, data, **options):
        final = "/commits/" in key
        if (final and self.mode == "final_not_written") or (not final and self.mode == "chunk_not_written" and len(self.puts) >= 1):
            self.puts.append((key, len(data), options["expected_version"]))
            return False
        result = super().put_bytes_strict_conditional(key, data, **options)
        if final:
            self.final_key = key
            if self.mode in {"final_lost_ack", "final_unknown"}:
                raise TimeoutError("private-host-path must never escape")
        return result


@pytest.mark.parametrize("mode", ["chunk_not_written", "final_not_written"])
def test_incomplete_append_has_no_commit_and_retry_reuses_valid_chunks(tmp_path, mode):
    normal, root = local_store(tmp_path)
    store = FaultStore(normal.inner, mode)
    supplied = bundle()
    failed = subject.append_relationship_observation(store, **supplied)
    assert failed["status"] == "REFUSED" and failed["reference"] is None
    assert not list((root / subject.PREFIX / "commits").rglob("*.json"))
    old_chunks = {key: value for key, value in inventory(root).items() if "/chunks/" in key}
    assert old_chunks
    committed = subject.append_relationship_observation(normal, **supplied)
    assert committed["status"] == "COMMITTED"
    after = inventory(root)
    assert all(after[key] == value for key, value in old_chunks.items())
    assert subject.read_relationship_observation(normal, committed["reference"])["status"] == "VERIFIED"


def test_lost_final_acknowledgment_reconciles_actual_local_bytes(tmp_path):
    normal, _ = local_store(tmp_path)
    store = FaultStore(normal.inner, "final_lost_ack")
    result = subject.append_relationship_observation(store, **bundle())
    assert result["status"] == "COMMITTED"
    assert subject.read_relationship_observation(normal, result["reference"])["status"] == "VERIFIED"


@pytest.mark.parametrize("mode", ["final_unknown", "closure_unknown"])
def test_uncertain_final_effect_exposes_only_expected_reference_then_read_reconciles(tmp_path, mode):
    normal, _ = local_store(tmp_path)
    result = subject.append_relationship_observation(FaultStore(normal.inner, mode), **bundle())
    assert result["status"] == "EFFECT_UNKNOWN"
    assert result["reference"] is None and result["expected_reference"] is not None
    assert result["inspection"] is None and result["review_provenance"] is None
    assert "private-host-path" not in json.dumps(result)
    later = subject.read_relationship_observation(normal, result["expected_reference"])
    assert later["status"] == "VERIFIED"
    assert subject.append_relationship_observation(normal, **bundle())["reference"] == result["expected_reference"]


@pytest.mark.parametrize("readback", ["absent", "nonmatching"])
def test_final_put_timeout_with_no_matching_readback_remains_effect_unknown(tmp_path, readback):
    normal, root = local_store(tmp_path)

    class DelayedFinalResponse(TracedStore):
        pending = None

        def put_bytes_strict_conditional(self, key, data, **options):
            if "/commits/" not in key:
                return super().put_bytes_strict_conditional(key, data, **options)
            self.puts.append((key, len(data), options["expected_version"]))
            self.pending = (key, data, options.copy())
            if readback == "nonmatching":
                corrupt = bytes([data[0] ^ 1]) + data[1:]
                self.inner.put_bytes_strict_conditional(key, corrupt, **options)
            # The manifest attempt is unresolved, rather than an acknowledged conflict.
            raise TimeoutError("private-host-path must never escape")

    store = DelayedFinalResponse(normal.inner)
    result = subject.append_relationship_observation(store, **bundle())
    assert result["status"] == "EFFECT_UNKNOWN"
    assert result["refusal"]["code"] == "MANIFEST_EFFECT_UNKNOWN"
    assert result["reference"] is None and result["expected_reference"] is not None
    assert result["inspection"] is None and result["review_provenance"] is None
    assert result["effect_state"] == "FINAL_MANIFEST_EFFECT_UNKNOWN"
    assert "private-host-path" not in json.dumps(result)
    assert store.pending is not None
    key, data, options = store.pending
    if readback == "absent":
        # Actual LocalStore returned None at the earlier readback. Completion can
        # still occur after that observation; the fixture now makes it explicit.
        assert not manifest_path(root, result["expected_reference"]).exists()
        assert normal.inner.get_bytes_strict_bounded(
            key, expected_byte_length=len(data), max_byte_length=16384,
        ) is None
        assert normal.inner.put_bytes_strict_conditional(key, data, **options) is True
        assert subject.read_relationship_observation(normal, result["expected_reference"])["status"] == "VERIFIED"
    else:
        before = inventory(root)
        later = subject.read_relationship_observation(normal, result["expected_reference"])
        assert later["status"] == "REFUSED" and later["refusal"]["code"] == "MANIFEST_DIGEST_MISMATCH"
        assert later["review_provenance"] is None and inventory(root) == before
    assert_boundaries(result)


def test_same_content_concurrent_native_local_appends_converge(tmp_path):
    store, root = local_store(tmp_path)
    barrier = threading.Barrier(2)

    class ConcurrentStore(TracedStore):
        def get_bytes_strict_bounded(self, key, **options):
            if "/commits/" in key and not self.reads:
                barrier.wait(timeout=20)
            return super().get_bytes_strict_bounded(key, **options)

    peers = [ConcurrentStore(LocalStore(root)), ConcurrentStore(LocalStore(root))]
    supplied = bundle()
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(subject.append_relationship_observation, peer, **supplied) for peer in peers]
        results = [future.result(timeout=40) for future in futures]
    assert all(result["status"] in {"COMMITTED", "REPEATED"} for result in results)
    assert results[0]["reference"] == results[1]["reference"]
    assert subject.read_relationship_observation(store, results[0]["reference"])["status"] == "VERIFIED"


@pytest.mark.parametrize("damage", ["chunk_corrupt", "chunk_missing", "manifest_corrupt"])
def test_committed_corruption_refuses_reads_and_repeats_without_repair(tmp_path, damage):
    store, root = local_store(tmp_path)
    supplied = bundle()
    reference = subject.append_relationship_observation(store, **supplied)["reference"]
    manifest, _ = stored_package(root, reference)
    target = (manifest_path(root, reference) if damage == "manifest_corrupt" else
              root / subject.PREFIX / "chunks/sha256" / (manifest["chunks"][0]["sha256"] + ".bin"))
    if damage == "chunk_missing":
        target.unlink()
    else:
        raw = target.read_bytes()
        target.write_bytes(bytes([raw[0] ^ 1]) + raw[1:])
    before, writes = inventory(root), len(store.puts)
    assert subject.read_relationship_observation(store, reference)["status"] == "REFUSED"
    assert subject.append_relationship_observation(store, **supplied)["status"] == "REFUSED"
    assert len(store.puts) == writes and inventory(root) == before


@pytest.mark.parametrize("kind", ["symlink", "fifo", "directory"])
def test_native_exact_length_mode_rejects_nonregular_committed_chunk_without_fallback(tmp_path, kind):
    store, root = local_store(tmp_path)
    supplied = bundle()
    reference = subject.append_relationship_observation(store, **supplied)["reference"]
    manifest, _ = stored_package(root, reference)
    target = root / subject.PREFIX / "chunks/sha256" / (manifest["chunks"][0]["sha256"] + ".bin")
    raw = target.read_bytes()
    target.unlink()
    if kind == "symlink":
        alternate = tmp_path / "alternate-bytes"
        alternate.write_bytes(raw)
        target.symlink_to(alternate)
    elif kind == "fifo":
        os.mkfifo(target)
    else:
        target.mkdir()
    writes = len(store.puts)
    result = subject.read_relationship_observation(store, reference)
    assert result["status"] == "REFUSED" and result["refusal"]["code"] == "STORE_READ_FAILED"
    assert result["inspection"] is None and result["review_provenance"] is None
    assert len(store.puts) == writes


@pytest.mark.parametrize("change", ["wrong_digest", "wrong_length", "bool_length", "unknown_key", "oversize_length"])
def test_manifest_reference_digest_length_and_closed_shape_are_required(tmp_path, change):
    store, _ = local_store(tmp_path)
    reference = subject.append_relationship_observation(store, **bundle())["reference"]
    bad = dict(reference)
    if change == "wrong_digest":
        bad["sha256"] = "0" * 64
    elif change == "wrong_length":
        bad["byte_length"] += 1
    elif change == "bool_length":
        bad["byte_length"] = True
    elif change == "unknown_key":
        bad["latest"] = True
    else:
        bad["byte_length"] = 16385
    count = len(store.puts)
    result = subject.read_relationship_observation(store, bad)
    assert result["status"] == "REFUSED"
    assert result["inspection"] is None and result["review_provenance"] is None
    assert len(store.puts) == count


@pytest.mark.parametrize("damage", ["package_digest", "descriptor_length", "extra_chunk", "duplicate_json_key"])
def test_self_hashed_malformed_manifest_cannot_bypass_descriptor_limits(tmp_path, damage):
    store, root = local_store(tmp_path)
    reference = subject.append_relationship_observation(store, **bundle())["reference"]
    manifest, _ = stored_package(root, reference)
    if damage == "package_digest":
        manifest["package_sha256"] = "0" * 64
    elif damage == "descriptor_length":
        manifest["chunks"][0]["byte_length"] = True
    elif damage == "extra_chunk":
        manifest["chunks"] = [manifest["chunks"][0]] * 65
    raw = encoded(manifest)
    if damage == "duplicate_json_key":
        raw = b'{"schema":"duplicate",' + raw[1:]
    fake = {"schema": subject.REFERENCE_SCHEMA, "sha256": sha256(raw).hexdigest(), "byte_length": len(raw)}
    store.inner.put_bytes_strict_conditional(subject.PREFIX + "commits/sha256/" + fake["sha256"] + ".json",
                                             raw, expected_version=None)
    writes = len(store.puts)
    result = subject.read_relationship_observation(store, fake)
    assert result["status"] == "REFUSED" and result["review_provenance"] is None
    assert len(store.puts) == writes


@pytest.mark.parametrize("field,change,code", [
    ("source_record_bytes", lambda x: x.update(candidate_id="wrong"), "SOURCE_RECORD_MISMATCH"),
    ("retained_first_review_bytes", lambda x: x["semantic_findings"].update(source_local_object="wrong"), "REVIEW_SUBJECT_MISMATCH"),
    ("retained_first_review_bytes", lambda x: x["source_binding"]["context"].update(sha256="0" * 64), "REVIEW_CONTEXT_MISMATCH"),
    ("retained_independent_review_bytes", lambda x: x["finding"].update(target_scope="Boreal"), "REVIEW_SCOPE_MISMATCH"),
    ("retained_first_review_bytes", lambda x: x["limits"].update(prediction=True), "REVIEW_AUTHORITY_UNSUPPORTED"),
    ("semantic_review_bytes", lambda x: x.update(review_note="changed exact artifact"), "REVIEW_BINDING_MISMATCH"),
])
def test_source_metadata_review_subject_context_and_authority_bindings_fail_before_writes(tmp_path, field, change, code):
    store, _ = local_store(tmp_path)
    supplied = bundle()
    value = json.loads(supplied[field])
    change(value)
    supplied[field] = encoded(value)
    result = subject.append_relationship_observation(store, **supplied)
    assert result["status"] == "REFUSED" and result["refusal"]["code"] == code
    assert not store.puts and not store.reads
    assert result["reference"] is None and result["review_provenance"] is None
    assert_boundaries(result)


@pytest.mark.parametrize("field,raw,code", [
    ("candidate_bytes", b"{", "INPUT_JSON_INVALID"),
    ("source_bytes", b"\xff", "INPUT_UNICODE_INVALID"),
    ("source_record_bytes", b'{"a":1,"a":2}', "JSON_DUPLICATE_KEY"),
    ("source_record_bytes", b'{"a":NaN}', "INPUT_JSON_INVALID"),
    ("source_record_bytes", b'{"a":1e999}', "INPUT_JSON_INVALID"),
    ("source_record_bytes", b'{"a":"\\ud800"}', "INPUT_UNICODE_INVALID"),
    ("source_record_bytes", b"[]", "REVIEW_BINDING_MISMATCH"),
    ("retained_first_review_bytes", b"", "INPUT_LIMIT"),
    ("retained_first_review_bytes", b"x" * 65537, "INPUT_LIMIT"),
    ("candidate_bytes", b"x" * (256 * 1024 + 1), "INPUT_LIMIT"),
])
def test_invalid_and_oversized_exact_inputs_are_visible_refusals_before_store_access(tmp_path, field, raw, code):
    store, _ = local_store(tmp_path)
    supplied = bundle()
    supplied[field] = raw
    result = subject.append_relationship_observation(store, **supplied)
    assert result["status"] == "REFUSED" and result["refusal"]["code"] == code
    assert not store.reads and not store.puts and store.validations == 0


@pytest.mark.parametrize("invalid", ["depth", "nodes", "case_count", "duplicate_case"])
def test_closed_case_cardinality_and_parsed_resource_bounds(tmp_path, invalid):
    store, _ = local_store(tmp_path)
    supplied = bundle()
    if invalid == "depth":
        value = 0
        for _ in range(25):
            value = [value]
        supplied["source_record_bytes"] = encoded(value)
    elif invalid == "nodes":
        supplied["source_record_bytes"] = encoded([None] * 8193)
    elif invalid == "case_count":
        supplied["pilot_adjudications_bytes"] += b'{"case_id":"C07"}\n'
    else:
        rows = supplied["pilot_adjudications_bytes"].splitlines()
        rows[-1] = rows[0]
        supplied["pilot_adjudications_bytes"] = b"\n".join(rows) + b"\n"
    result = subject.append_relationship_observation(store, **supplied)
    assert result["status"] == "REFUSED"
    assert not store.reads and not store.puts


def test_package_cap_counts_escaping_and_refuses_before_full_package_serialization(tmp_path, monkeypatch):
    store, _ = local_store(tmp_path)
    supplied = bundle(padding="\x00" * 600000)
    assert sum(len(value) for key, value in supplied.items() if key.endswith("_bytes")) < 1024 * 1024
    original = subject.json.dumps
    full_package_serializations = []

    def guarded(value, *args, **kwargs):
        if type(value) is dict and value.get("schema") == subject.PACKAGE_SCHEMA:
            full_package_serializations.append(True)
            raise AssertionError("over-limit complete package must not be materialized")
        return original(value, *args, **kwargs)

    monkeypatch.setattr(subject.json, "dumps", guarded)
    result = subject.append_relationship_observation(store, **supplied)
    assert result["status"] == "REFUSED"
    assert result["refusal"]["code"] == "SERIALIZED_PACKAGE_LIMIT"
    assert not full_package_serializations and not store.reads and not store.puts


def test_complete_real_inspector_refusal_is_retained_and_precomputed_result_input_is_impossible(tmp_path):
    store, _ = local_store(tmp_path)
    supplied = bundle()
    candidate = json.loads(supplied["candidate_bytes"])
    candidate["assertion"]["subject_label"] = "UnstatedVendor"
    supplied["candidate_bytes"] = encoded(candidate)
    expected = inspect_candidate(candidate, source=supplied["source_bytes"].decode("utf-8"))
    result = subject.append_relationship_observation(store, **supplied)
    assert result["status"] == "REFUSED" and result["inspection"] == expected
    assert expected["refusal"]["code"] == "SOURCE_LOCAL_LABEL_UNSUPPORTED"
    assert not store.puts
    with pytest.raises(TypeError):
        subject.append_relationship_observation(store, **supplied, inspection={"inspection_status": "INSPECTABLE"})
    assert not store.puts


def test_forged_saved_positive_cannot_override_actual_refusal_or_replay_mismatch(tmp_path):
    store, root = local_store(tmp_path)
    supplied = bundle()
    reference = subject.append_relationship_observation(store, **supplied)["reference"]
    _, original = stored_package(root, reference)
    forged = deepcopy(original)
    forged["inspection"]["support"]["semantic_adjudication"] = "FORGED_POSITIVE"
    fake = install_forged_package(store.inner, forged)
    read = subject.read_relationship_observation(store, fake)
    assert read["status"] == "REFUSED" and read["refusal"]["code"] == "INSPECTION_REPLAY_MISMATCH"
    assert read["inspection"]["support"]["semantic_adjudication"] == "NOT_PERFORMED"
    assert read["review_provenance"] is None
    forged = deepcopy(original)
    candidate = json.loads(supplied["candidate_bytes"])
    candidate["assertion"]["subject_label"] = "UnstatedVendor"
    raw = encoded(candidate)
    forged["components"]["candidate"] = {"sha256": sha256(raw).hexdigest(), "byte_length": len(raw),
                                            "encoding": "utf-8", "text": raw.decode("utf-8")}
    forged["canonical_candidate_payload_sha256"] = sha256(encoded(candidate)).hexdigest()
    fake = install_forged_package(store.inner, forged)
    read = subject.read_relationship_observation(store, fake)
    assert read["status"] == "REFUSED" and read["refusal"]["code"] == "INSPECTION_REPLAY_MISMATCH"
    assert read["replay_status"] == "UNCHANGED_REQUEST_MISMATCH"
    assert read["inspection"] == inspect_candidate(candidate, source=supplied["source_bytes"].decode("utf-8"))
    assert read["inspection"]["refusal"]["code"] == "SOURCE_LOCAL_LABEL_UNSUPPORTED"
    assert read["review_provenance"] is None
    assert "FORGED_POSITIVE" not in json.dumps(read)
    assert_boundaries(read)


def test_current_support_option_and_historical_refusals_use_actual_fresh_requests(tmp_path, monkeypatch):
    store, _ = local_store(tmp_path)
    supplied = bundle()
    candidate = json.loads(supplied["candidate_bytes"])
    source = supplied["source_bytes"].decode("utf-8")
    reference = subject.append_relationship_observation(store, **supplied)["reference"]
    real, calls = subject.inspect_candidate, []

    def spy(value, **options):
        calls.append(options.copy())
        return real(value, **options)

    monkeypatch.setattr(subject, "inspect_candidate", spy)
    supported = subject.read_relationship_observation(store, reference, include_support_text=True)
    assert supported["status"] == "VERIFIED"
    assert supported["inspection"] == real(candidate, source=source, include_support_text=True)
    assert supported["replay_status"] == "CHANGED_REQUEST_NOT_SEALED_EQUALITY"
    assert supported["inspection"]["support"]["replayed_value_text"]
    assert len(calls) == 1 and calls[-1]["include_support_text"] is True
    for registry, expected_code in ((None, "AS_OF_REGISTRY_REQUIRED"), (Registry([]), "AS_OF_DATASET_REQUIRED")):
        before = len(calls)
        historical = subject.read_relationship_observation(store, reference, as_of="2024-02-26T12:00:00Z", registry=registry)
        expected = real(candidate, source=source, as_of="2024-02-26T12:00:00Z", registry=registry)
        assert historical["status"] == "ABSTAINED" and historical["inspection"] == expected
        assert expected["refusal"]["code"] == expected_code
        assert historical["review_provenance"] is None and historical["prior_observation"] is None
        assert len(calls) == before + 1
        serialized = json.dumps(historical)
        assert all(term not in serialized for term in ("Aurora", "Boreal", "Widget", "H200", "synthetic-first-reader"))
        assert_boundaries(historical)
    before = len(calls)
    invalid = subject.read_relationship_observation(store, reference, as_of="invalid-cutoff")
    assert invalid["inspection"] == real(candidate, source=source, as_of="invalid-cutoff")
    assert len(calls) == before + 1 and invalid["review_provenance"] is None


@pytest.mark.parametrize("purpose", ["public_export", "training", "prediction", "graph1_admitted"])
def test_other_purposes_abstain_without_reading_or_leaking_saved_evidence(tmp_path, purpose):
    store, _ = local_store(tmp_path)
    reference = subject.append_relationship_observation(store, **bundle())["reference"]
    reads, writes = len(store.reads), len(store.puts)
    result = subject.read_relationship_observation(store, reference, purpose=purpose)
    assert result["refusal"]["code"] == "PURPOSE_UNSUPPORTED"
    assert result["inspection"] is None and result["review_provenance"] is None
    assert len(store.reads) == reads and len(store.puts) == writes
    assert_boundaries(result)


def test_raw_candidate_identity_differs_from_canonical_payload_and_old_archive_survives(tmp_path):
    store, root = local_store(tmp_path)
    first = subject.append_relationship_observation(store, **bundle(indent=2))
    second = subject.append_relationship_observation(store, **bundle(indent=None))
    assert first["reference"] != second["reference"]
    _, a = stored_package(root, first["reference"])
    _, b = stored_package(root, second["reference"])
    assert a["components"]["candidate"]["sha256"] != b["components"]["candidate"]["sha256"]
    assert a["canonical_candidate_payload_sha256"] == b["canonical_candidate_payload_sha256"]
    assert subject.read_relationship_observation(store, first["reference"])["status"] == "VERIFIED"


@pytest.mark.parametrize("relation", ["corrects", "contradicts", "adds_review"])
def test_prior_links_are_preserved_unresolved_without_target_lookup_or_original_erasure(tmp_path, relation):
    store, root = local_store(tmp_path)
    supplied = bundle()
    original = subject.append_relationship_observation(store, **supplied)
    missing = {"schema": subject.REFERENCE_SCHEMA, "sha256": "0" * 64, "byte_length": 100}
    before = inventory(root)
    linked = subject.append_relationship_observation(store, **supplied,
                    prior_observation={"reference": missing, "relation": relation})
    assert linked["status"] == "COMMITTED" and linked["reference"] != original["reference"]
    assert linked["prior_observation"] == {"declaration": {"reference": missing, "relation": relation},
                                            "resolution": "UNRESOLVED_NO_SELECTION"}
    assert all(missing["sha256"] not in key for key, *_ in store.reads)
    after = inventory(root)
    assert all(after[key] == value for key, value in before.items())
    assert subject.read_relationship_observation(store, original["reference"])["status"] == "VERIFIED"


def test_caller_reviewer_labels_never_authenticate_review_or_producer(tmp_path):
    store, _ = local_store(tmp_path)
    supplied = bundle()
    first = json.loads(supplied["retained_first_review_bytes"])
    first["first_reader"] = "caller-claims-to-be-authenticated-publisher"
    supplied["retained_first_review_bytes"] = encoded(first)
    result = subject.append_relationship_observation(store, **supplied)
    assert result["status"] == "COMMITTED"
    for key in ("authorship", "review_independence", "source_custody", "semantic_truth"):
        assert result["review_provenance"]["binding"][key] == "NOT_AUTHENTICATED"
    assert_boundaries(result)


def test_matching_but_broadened_review_targets_cannot_remove_the_h200_scope(tmp_path):
    store, _ = local_store(tmp_path)
    supplied = bundle()
    first = json.loads(supplied["retained_first_review_bytes"])
    independent = json.loads(supplied["retained_independent_review_bytes"])
    first["semantic_findings"]["downstream_configuration"] = "Boreal"
    independent["finding"]["target_scope"] = "Boreal"
    supplied["retained_first_review_bytes"] = encoded(first)
    supplied["retained_independent_review_bytes"] = encoded(independent)
    result = subject.append_relationship_observation(store, **supplied)
    assert result["status"] == "REFUSED" and result["refusal"]["code"] == "REVIEW_SCOPE_MISMATCH"
    assert result["inspection"]["inspection_status"] == "INSPECTABLE"
    assert result["review_provenance"] is None and not store.reads and not store.puts
    assert_boundaries(result)


def test_unsupported_exact_reader_never_falls_back_or_writes(tmp_path):
    normal, _ = local_store(tmp_path)

    class PositionalOnly(TracedStore):
        def get_bytes_strict_bounded(self, key, maximum_bytes):
            raise AssertionError("positional fallback must not run")

    store = PositionalOnly(normal.inner)
    result = subject.append_relationship_observation(store, **bundle())
    assert result["status"] == "REFUSED" and result["refusal"]["code"] == "STORE_READ_FAILED"
    assert not store.puts


def test_second_process_reads_repeat_exactly_under_import_network_and_mutation_guards(tmp_path):
    store, root = local_store(tmp_path)
    supplied = bundle()
    committed = subject.append_relationship_observation(store, **supplied)
    assert committed["status"] == "COMMITTED"
    expected_current = subject.read_relationship_observation(store, committed["reference"])
    expected_historical = subject.read_relationship_observation(
        store, committed["reference"], as_of="2024-02-26T12:00:00Z", registry=Registry([]),
    )
    before = inventory(root)
    child = r'''
from importlib import import_module
import json
import os
from pathlib import Path
import sys

request = json.load(sys.stdin)
root = Path(request["root"])
assert root.is_absolute() and root.is_dir() and not root.is_symlink()
assert root.resolve(strict=True) == root
blocked = []
constructor_events = []
constructing_existing_store = False
control_name = None
control_denials = []
control_fallthroughs = []
blocked_roots = {"collectors", "requests", "urllib3", "httpx", "aiohttp", "boto3", "botocore", "tests", "pytest"}
blocked_modules = {
    "engine.earnings_release.collector", "engine.earnings_release.capture",
    "engine.earnings_release.source_capture", "test_company_relationship_observations",
    "capture_one_native_sec_filing", "urllib.request", "http.client",
}

def deny(event):
    if control_name is None:
        blocked.append(event)
    else:
        control_denials.append({"requested": control_name, "denied_event": event})
    raise RuntimeError("read-only observation fence: " + event)

def check_import(name):
    if (name.split(".")[0] in blocked_roots
            or any(name == blocked or name.startswith(blocked + ".") for blocked in blocked_modules)
            or name.startswith(("engine.collectors.", "engine.captures."))):
        deny("import:" + name)

class ImportFence:
    def find_spec(self, fullname, path=None, target=None):
        check_import(fullname)
        return None

mutation_events = {
    "os.mkdir", "os.remove", "os.rmdir", "os.rename", "os.link", "os.symlink",
    "os.chmod", "os.chown", "os.utime", "os.truncate", "os.chflags",
    "os.setxattr", "os.removexattr", "shutil.copyfile", "shutil.copytree", "shutil.rmtree",
}
process_events = {"subprocess.Popen", "os.system", "os.exec", "os.fork", "os.forkpty", "os.posix_spawn"}
write_flags = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND

def audit(event, args):
    if event == "import":
        check_import(args[0])
    if event.startswith("socket.") or event in process_events:
        deny(event)
    if event == "open":
        mode, flags = args[1], args[2]
        if ((isinstance(mode, str) and any(mark in mode for mark in "wax+"))
                or (isinstance(flags, int) and flags & write_flags)):
            deny("open:write")
    if event in mutation_events:
        # LocalStore's incumbent constructor attempts exactly this existing mkdir.
        # It is visible and narrowly allowed before the full read-only phase.
        if (event == "os.mkdir" and constructing_existing_store
                and os.path.abspath(os.fsdecode(args[0])) == str(root)
                and root.is_dir() and not root.is_symlink()):
            constructor_events.append("existing_store_directory_mkdir")
            return
        deny(event)

sys.meta_path.insert(0, ImportFence())
sys.addaudithook(audit)

# Exercise actual import resolution under the installed fence before application
# imports. Expected control events are retained separately, never cleared out of
# the unexpected-event list. A later finder proves no prohibited loader is reached.
control_names = (
    "collectors", "collectors.sec_document_spine", "collectors.fundamental_forensics_acquisition",
    "collectors.fundamental_forensics_companyfacts", "collectors.edgar_forensics",
    "tests", "tests.test_company_relationship_observations", "pytest",
    "requests", "urllib3", "httpx", "aiohttp", "boto3", "botocore",
    "urllib.request", "http.client", "capture_one_native_sec_filing", "test_company_relationship_observations",
)

class ControlFallthrough:
    def find_spec(self, fullname, path=None, target=None):
        if fullname in control_names:
            control_fallthroughs.append(fullname)
            raise AssertionError("prohibited import reached a later finder")
        return None

fallthrough = ControlFallthrough()
sys.meta_path.insert(1, fallthrough)
for requested in control_names:
    assert requested not in sys.modules
    control_name = requested
    before = len(control_denials)
    try:
        import_module(requested)
    except RuntimeError as error:
        assert str(error).startswith("read-only observation fence: import:")
    else:
        raise AssertionError("prohibited import unexpectedly succeeded")
    finally:
        control_name = None
    assert len(control_denials) == before + 1
    assert requested not in sys.modules
sys.meta_path.remove(fallthrough)
assert control_fallthroughs == []
assert import_module("urllib.parse").urlparse("https://example.invalid/path").path == "/path"

# No parent fixture/test, source acquisition, storage factory, or client import.
from engine.research_vault.r2_store import LocalStore
from engine.company_intelligence.relationship_observations import read_relationship_observation
from lib.dataos.registry import Registry

constructing_existing_store = True
store = LocalStore(root)
constructing_existing_store = False
current = read_relationship_observation(store, request["reference"])
historical = read_relationship_observation(
    store, request["reference"], as_of="2024-02-26T12:00:00Z", registry=Registry([]),
)
print(json.dumps({"current": current, "historical": historical,
                  "blocked_attempts": blocked, "constructor_events": constructor_events,
                  "intentional_guard_controls": control_denials,
                  "control_fallthroughs": control_fallthroughs, "allowed_pure_import": "urllib.parse"},
                 sort_keys=True, ensure_ascii=False, separators=(",", ":")))
'''
    project = Path(__file__).resolve().parents[1]
    environment = dict(os.environ)
    environment.update(PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(project))
    raw = encoded({"root": str(root.resolve()), "reference": committed["reference"]})
    runs = [subprocess.run([sys.executable, "-B", "-c", child], input=raw,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=project,
                           env=environment, timeout=45, check=False) for _ in range(2)]
    for run in runs:
        assert run.returncode == 0, run.stderr.decode("utf-8", "replace")
        assert run.stderr == b""
    assert runs[0].stdout == runs[1].stdout
    observed = json.loads(runs[0].stdout)
    assert observed["current"] == expected_current
    assert observed["historical"] == expected_historical
    assert observed["blocked_attempts"] == []
    assert observed["constructor_events"] == ["existing_store_directory_mkdir"]
    assert [control["requested"] for control in observed["intentional_guard_controls"]] == [
        "collectors", "collectors.sec_document_spine", "collectors.fundamental_forensics_acquisition",
        "collectors.fundamental_forensics_companyfacts", "collectors.edgar_forensics",
        "tests", "tests.test_company_relationship_observations", "pytest",
        "requests", "urllib3", "httpx", "aiohttp", "boto3", "botocore",
        "urllib.request", "http.client", "capture_one_native_sec_filing", "test_company_relationship_observations",
    ]
    assert all(control["denied_event"].startswith("import:") for control in observed["intentional_guard_controls"])
    assert observed["control_fallthroughs"] == [] and observed["allowed_pure_import"] == "urllib.parse"
    assert observed["historical"]["inspection"]["refusal"]["code"] == "AS_OF_DATASET_REQUIRED"
    assert observed["historical"]["review_provenance"] is None
    assert all(word not in json.dumps(observed["historical"])
               for word in ("Aurora", "Boreal", "Widget", "H200", "synthetic-first-reader"))
    assert inventory(root) == before
    assert_boundaries(observed["current"])
    assert_boundaries(observed["historical"])


# A timed-out component write remains unresolved until exact readback succeeds.


class DelayedChunkResponse(TracedStore):
    """A pending chunk put records its payload and raises TimeoutError before
    the underlying store commits. The subsequent readback confirms an absent
    chunk, same-length conflicting bytes, or an unreadable read failure.
    The /commits/ (manifest) path is unchanged so final-manifest behavior is
    preserved."""

    pending = None

    def __init__(self, inner, *, readback="absent"):
        super().__init__(inner)
        self.readback = readback
        self.conflicting_write = None
        self.failed_read_keys = []

    def put_bytes_strict_conditional(self, key, data, **options):
        if "/commits/" in key:
            return super().put_bytes_strict_conditional(key, data, **options)
        self.puts.append((key, len(data), options["expected_version"]))
        self.pending = (key, data, options.copy())
        if self.readback == "conflicting":
            corrupt = bytes([data[0] ^ 1]) + data[1:]
            self.conflicting_write = self.inner.put_bytes_strict_conditional(key, corrupt, **options)
        # The real payload is never committed; the attempt is unresolved.
        raise TimeoutError("private-host-path must never escape")

    def get_bytes_strict_bounded(self, key, **options):
        if (self.readback == "unreadable" and self.pending is not None
                and key == self.pending[0]):
            self.failed_read_keys.append(key)
            raise RuntimeError("private-host-path must never escape")
        return super().get_bytes_strict_bounded(key, **options)


def _complete_pending(store, pending):
    """Simulate completion of the original pending write in this test store."""
    key, data, options = pending
    return store.inner.put_bytes_strict_conditional(key, data, **options)


def test_delayed_chunk_timeout_with_absent_readback_is_component_write_effect_unknown(tmp_path):
    normal, root = local_store(tmp_path)
    store = DelayedChunkResponse(normal.inner, readback="absent")
    supplied = bundle()
    result = subject.append_relationship_observation(store, **supplied)
    assert result["status"] == "EFFECT_UNKNOWN"
    assert result["refusal"]["code"] == "COMPONENT_EFFECT_UNKNOWN"
    assert result["reference"] is None and result["expected_reference"] is None
    assert result["inspection"] is None and result["review_provenance"] is None
    assert result["effect_state"] == "COMPONENT_WRITE_EFFECT_UNKNOWN"
    assert result["integrity_status"] == "NOT_ESTABLISHED"
    assert result["replay_status"] == "NOT_PERFORMED"
    assert "private-host-path" not in json.dumps(result)
    assert not list((root / subject.PREFIX / "commits").rglob("*.json"))
    # Pending chunk was recorded; the readback is truly missing.
    assert store.pending is not None
    key, data, options = store.pending
    assert "/commits/" not in key
    assert normal.inner.get_bytes_strict_bounded(
        key, expected_byte_length=len(data), max_byte_length=16384,
    ) is None
    # Settle the original pending write in the synthetic store before another
    # append. Exact retained bytes allow that later append to finish committing.
    assert _complete_pending(store, store.pending) is True
    committed = subject.append_relationship_observation(normal, **supplied)
    assert committed["status"] == "COMMITTED"
    assert subject.read_relationship_observation(normal, committed["reference"])["status"] == "VERIFIED"
    assert_boundaries(result)


@pytest.mark.parametrize("readback", ["conflicting", "unreadable"])
def test_delayed_chunk_timeout_with_conflicting_or_unreadable_readback_is_component_write_effect_unknown(tmp_path, readback):
    normal, root = local_store(tmp_path)
    store = DelayedChunkResponse(normal.inner, readback=readback)
    supplied = bundle()
    result = subject.append_relationship_observation(store, **supplied)
    assert result["status"] == "EFFECT_UNKNOWN"
    assert result["refusal"]["code"] == "COMPONENT_EFFECT_UNKNOWN"
    assert result["reference"] is None and result["expected_reference"] is None
    assert result["inspection"] is None and result["review_provenance"] is None
    assert result["effect_state"] == "COMPONENT_WRITE_EFFECT_UNKNOWN"
    assert result["integrity_status"] == "NOT_ESTABLISHED"
    assert result["replay_status"] == "NOT_PERFORMED"
    assert "private-host-path" not in json.dumps(result)
    assert not list((root / subject.PREFIX / "commits").rglob("*.json"))
    assert store.pending is not None
    pending_key, pending_data, _ = store.pending
    if readback == "conflicting":
        assert store.conflicting_write is True
        observed = normal.inner.get_bytes_strict_bounded(
            pending_key, expected_byte_length=len(pending_data), max_byte_length=16384,
        )
        assert observed is not None and len(observed) == len(pending_data) and observed != pending_data
        # Original create-only completion cannot replace the observed collision.
        assert _complete_pending(store, store.pending) is False
        later = subject.append_relationship_observation(normal, **supplied)
        assert later["status"] == "REFUSED"
        assert later["refusal"]["code"] == "EXISTING_OBJECT_CORRUPT"
    else:
        assert store.failed_read_keys == [pending_key]
        # Read failure is distinct from an absent readable object; it cannot
        # establish component integrity or authorize another modifying attempt.
        with pytest.raises(RuntimeError, match="private-host-path"):
            store.get_bytes_strict_bounded(
                pending_key, expected_byte_length=len(pending_data), max_byte_length=16384,
            )
    assert_boundaries(result)


def test_delayed_chunk_matching_lost_ack_still_commits(tmp_path):
    """A chunk put that raises TimeoutError after committing the bytes is
    reconciled by the matching readback; the append must succeed."""
    normal, _ = local_store(tmp_path)

    class LostAckChunk(TracedStore):
        def __init__(self, inner):
            super().__init__(inner)
            self.completed_chunks = []

        def put_bytes_strict_conditional(self, key, data, **options):
            if "/commits/" in key:
                return super().put_bytes_strict_conditional(key, data, **options)
            self.completed_chunks.append(super().put_bytes_strict_conditional(key, data, **options))
            raise TimeoutError("private-host-path must never escape")

    store = LostAckChunk(normal.inner)
    result = subject.append_relationship_observation(store, **bundle())
    assert store.completed_chunks and all(value is True for value in store.completed_chunks)
    assert result["status"] == "COMMITTED"
    assert subject.read_relationship_observation(normal, result["reference"])["status"] == "VERIFIED"


def test_chunk_put_returning_false_without_exception_remains_refused(tmp_path):
    """A chunk put returning False (no exception) must remain REFUSED; the
    chunk-phase effect_unknown generalization must not reframe a definitive
    no-object return as EFFECT_UNKNOWN. Final-manifest tests must remain
    unchanged in their refusal semantics."""
    normal, root = local_store(tmp_path)
    store = FaultStore(normal.inner, "chunk_not_written")
    supplied = bundle()
    failed = subject.append_relationship_observation(store, **supplied)
    assert failed["status"] == "REFUSED"
    assert failed["reference"] is None and failed["expected_reference"] is None
    assert failed["refusal"]["code"] == "COMPONENT_NOT_AVAILABLE_AT_READBACK"
    assert failed["effect_state"] == "NO_MANIFEST_ATTEMPT_BY_THIS_CALL"
    assert not list((root / subject.PREFIX / "commits").rglob("*.json"))


@pytest.mark.parametrize("readback,code", [
    ("raises", "STORE_READ_FAILED"),
    ("wrong_type", "STORE_PROTOCOL_INVALID"),
    ("wrong_length", "STORE_LENGTH_MISMATCH"),
])
def test_confirmed_chunk_conflict_with_failed_readback_is_not_unknown_write(tmp_path, readback, code):
    normal, root = local_store(tmp_path)

    class ConfirmedConflict(TracedStore):
        blocked_key = None
        competing_write = None
        own_write = None
        failed_reads = 0

        def put_bytes_strict_conditional(self, key, data, **options):
            # Another writer creates the same chunk after the absence probe.
            self.competing_write = self.inner.put_bytes_strict_conditional(key, data, **options)
            self.own_write = super().put_bytes_strict_conditional(key, data, **options)
            self.blocked_key = key
            return self.own_write

        def get_bytes_strict_bounded(self, key, **options):
            if key == self.blocked_key:
                self.failed_reads += 1
                if readback == "raises":
                    raise RuntimeError("private-host-path must never escape")
                if readback == "wrong_type":
                    return "not bytes"
                return b""
            return super().get_bytes_strict_bounded(key, **options)

    store = ConfirmedConflict(normal.inner)
    result = subject.append_relationship_observation(store, **bundle())
    # The real LocalStore, not the injected read failure, proves no own write.
    assert store.competing_write is True and store.own_write is False
    assert store.failed_reads == 1
    assert result["status"] == "REFUSED"
    assert result["refusal"]["code"] == code
    assert result["effect_state"] == "NO_MANIFEST_ATTEMPT_BY_THIS_CALL"
    assert result["reference"] is None and result["expected_reference"] is None
    assert result["integrity_status"] == "NOT_ESTABLISHED"
    assert result["replay_status"] == "NOT_PERFORMED"
    assert not list((root / subject.PREFIX / "commits").rglob("*.json"))
    assert "private-host-path" not in json.dumps(result)
    assert_boundaries(result)
