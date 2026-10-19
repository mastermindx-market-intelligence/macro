"""Synthetic initial-candidate checks against the actual native DataOS owner."""
from __future__ import annotations

import copy
from dataclasses import FrozenInstanceError
import hashlib
import json

import pytest

from engine.neuralweb.market_memory_identity_candidate import build_initial_reference_candidate
from lib.dataos import identity as native
from tests.test_dataos_identity import _obs_base, _obs_json, _OBS_NAMES


@pytest.fixture
def supplied():
    original, _history, rows, master = _obs_base()
    receipt = {"prospective_reference": original,
               "legacy_metadata": {"preserve": [None, False, 0, "original"]}}
    artifacts = {name: b"synthetic serialized artifact:" + name.encode() for name in _OBS_NAMES}
    return receipt, artifacts, rows, master


def compile_supplied(supplied, **changes):
    receipt, artifacts, rows, master = supplied
    args = {"receipt_before": _obs_json(receipt), "artifact_bytes": artifacts,
            "alias_records": rows, "master_records": master, "code_version": "3" * 40}
    args.update(changes)
    return build_initial_reference_candidate(**args)


def test_initial_candidate_preserves_complete_context_and_uses_native_validation(supplied, monkeypatch):
    receipt, artifacts, rows, master = supplied
    before = copy.deepcopy(supplied)
    calls = []
    real = native.validate_reference_snapshot
    def observe(a, b, c, **kw):
        calls.append((a, b, c, kw))
        return real(a, b, c, **kw)
    monkeypatch.setattr(native, "validate_reference_snapshot", observe)
    result = compile_supplied(supplied)
    assert supplied == before
    assert len(calls) == 1
    assert calls[0][0] == calls[0][2] == result.candidate_receipt_bytes
    assert calls[0][1] == artifacts
    candidate = json.loads(result.candidate_receipt_bytes)
    assert {k: candidate[k] for k in receipt} == receipt
    assert candidate["identity_observations"]["attempts"] == []
    assert candidate["identity_observations"]["anchor"]["owner_read_completed_at_utc_ns"] == str(
        receipt["prospective_reference"]["source_read_completed_at_utc_ns"])
    assert result.original_receipt_sha256 == hashlib.sha256(_obs_json(receipt)).hexdigest()
    assert result.candidate_receipt_sha256 == hashlib.sha256(result.candidate_receipt_bytes).hexdigest()
    assert result.generation_id == candidate["publication"]["generation_id"]
    assert dict(result.artifact_sha256) == {n: hashlib.sha256(b).hexdigest() for n, b in artifacts.items()}
    assert not result.published and not result.identity_admitted
    assert not isinstance(result, (native.ReferenceSnapshot, native.ReferenceReadReceipt))
    assert not any(k.startswith("read_") for k in candidate)


def test_candidate_is_detached_and_does_not_publish_or_read(supplied, monkeypatch):
    def forbidden(*_a, **_kw):
        pytest.fail("candidate attempted file I/O")
    monkeypatch.setattr("builtins.open", forbidden)
    result = compile_supplied(supplied)
    before = copy.deepcopy(result)
    supplied[0]["prospective_reference"]["probes"].clear()
    supplied[1].clear()
    supplied[2].clear()
    supplied[3].clear()
    assert result == before
    with pytest.raises(FrozenInstanceError):
        result.published = True


def test_candidate_does_not_claim_records_are_decoded_from_artifact_bytes(supplied):
    original = compile_supplied(supplied)
    changed = dict(supplied[1])
    changed["vendor_aliases.parquet"] = b"different supplied serialization"
    candidate = compile_supplied(supplied, artifact_bytes=changed)
    assert candidate.alias_semantic_sha256 == original.alias_semantic_sha256
    assert candidate.artifact_sha256 != original.artifact_sha256
    assert candidate.generation_id != original.generation_id
    assert not candidate.records_bound_to_artifacts
    assert not candidate.published and not candidate.identity_admitted


@pytest.mark.parametrize("key", ["publication", "identity_observations"])
@pytest.mark.parametrize("value", [None, {}, {"attempts": []}])
def test_existing_owner_context_is_never_reset(supplied, key, value):
    supplied[0][key] = value
    with pytest.raises(native.IdentityError, match="unpublished initial"):
        compile_supplied(supplied)


def test_nullable_revision_columns_follow_owner_base_prefix(supplied):
    for row in supplied[2]:
        row.update({k: None for k in native._REVISION_FIELDS})
    result = compile_supplied(supplied)
    native.validate_reference_snapshot(result.candidate_receipt_bytes, supplied[1],
        result.candidate_receipt_bytes, alias_records=supplied[2], master_records=supplied[3])
    supplied[2][0]["attempt_id"] = "existing-attempt"
    with pytest.raises(native.IdentityError, match="replace revision history"):
        compile_supplied(supplied)


@pytest.mark.parametrize("change", ["probe", "clock", "orphan", "missing_native"])
def test_incompatible_original_native_context_is_rejected(supplied, change):
    original = supplied[0]["prospective_reference"]
    if change == "probe":
        original["probes"]["MU"]["evidence_sha256"] = "0" * 64
    elif change == "clock":
        original["source_read_completed_at_utc_ns"] += 1
    elif change == "orphan":
        other = copy.deepcopy(supplied[2][-1]); other["vendor_symbol"] = "UNKNOWN"
        supplied[2].append(other)
    else:
        supplied[2].pop()
    with pytest.raises(native.IdentityError):
        compile_supplied(supplied)


@pytest.mark.parametrize("name", _OBS_NAMES)
def test_each_physical_artifact_is_required_and_sealed(supplied, name):
    result = compile_supplied(supplied)
    changed = dict(supplied[1]); changed[name] += b"changed"
    with pytest.raises(native.IdentityError):
        native.validate_reference_snapshot(result.candidate_receipt_bytes, changed,
            result.candidate_receipt_bytes, alias_records=supplied[2], master_records=supplied[3])
    del changed[name]
    with pytest.raises(native.IdentityError, match="complete artifact"):
        compile_supplied(supplied, artifact_bytes=changed)


@pytest.mark.parametrize("index", [2, 3])
def test_semantic_records_cannot_change_under_the_candidate(supplied, index):
    result = compile_supplied(supplied)
    supplied[index][0]["security_id"] = "SEC:US-XNAS-CHANGED"
    with pytest.raises(native.IdentityError, match="semantic record seal"):
        native.validate_reference_snapshot(result.candidate_receipt_bytes, supplied[1],
            result.candidate_receipt_bytes, alias_records=supplied[2], master_records=supplied[3])


@pytest.mark.parametrize("raw", [b'{}', b'[]', b'{"x":1,"x":2}', b'{"x":NaN}',
    b'{"x":Infinity}', b'\xff', b'{', b'[' * 30 + b'0' + b']' * 30,
    b'{"x":"' + b'x' * 262145 + b'"}', b'{"x":9223372036854775808}'])
def test_malformed_or_unbounded_json_fails_closed(supplied, raw):
    with pytest.raises(native.IdentityError):
        compile_supplied(supplied, receipt_before=raw)


@pytest.mark.parametrize("version", [None, True, "3" * 39, "A" * 40, "3" * 40 + "\n"])
def test_exact_source_identity_grammar(supplied, version):
    with pytest.raises(native.IdentityError, match="code version"):
        compile_supplied(supplied, code_version=version)


def test_custom_objects_duplicate_records_and_bad_artifact_types_refuse(supplied):
    class ForeignDict(dict):
        pass
    with pytest.raises(native.IdentityError):
        compile_supplied(supplied, artifact_bytes=ForeignDict(supplied[1]))
    with pytest.raises(native.IdentityError):
        compile_supplied(supplied, alias_records=[ForeignDict(supplied[2][0])])
    with pytest.raises(native.IdentityError, match="duplicate semantic record"):
        compile_supplied(supplied, alias_records=supplied[2] + [supplied[2][0]])
    bad = dict(supplied[1]); bad[_OBS_NAMES[0]] = bytearray(b"mutable")
    with pytest.raises(native.IdentityError, match="artifact byte bound"):
        compile_supplied(supplied, artifact_bytes=bad)


# R23: physically bind the detached candidate to actual, bounded Parquet bytes.
# Unlike the existing pure supplied-record helper, these tests may not trust
# caller-provided semantic row arrays as a substitute for decoding artifacts.
def _r23_actual_parquet_supplied(supplied):
    import pyarrow as pa
    import pyarrow.parquet as pq
    receipt, _synthetic_artifacts, aliases, master = supplied
    contents = {
        "vendor_aliases.parquet": aliases,
        "security_master.parquet": master,
        "issuer_master.parquet": [{"issuer_id": "ISS:R23-SYNTHETIC"}],
        "issuer_migrations.parquet": [{"ref": "fixture"}],
        "security_migrations.parquet": [{"ref": "fixture"}],
    }
    out = {}
    for name, records in contents.items():
        buf = pa.BufferOutputStream()
        pq.write_table(pa.Table.from_pylist(records), buf)
        out[name] = buf.getvalue().to_pybytes()
    return _obs_json(receipt), out


def test_r23_parquet_bound_candidate_decodes_exact_actual_bytes(supplied):
    from engine.neuralweb.market_memory_identity_candidate import (
        build_parquet_bound_initial_candidate,
    )
    receipt, artifact_bytes = _r23_actual_parquet_supplied(supplied)
    files_before = dict(artifact_bytes)
    prepared = build_parquet_bound_initial_candidate(
        receipt, artifact_bytes, code_version="3" * 40,
    )
    assert artifact_bytes == files_before
    assert prepared.alias_master_semantics_bound is True
    assert prepared.all_artifacts_parseable is True
    assert prepared.records_bound_to_artifacts is False  # other three have no semantic-owner seal
    assert prepared.source_authenticated is False
    assert prepared.published is False
    assert prepared.identity_admitted is False
    assert prepared.current_read_admitted is False
    assert prepared.original_receipt_sha256 == hashlib.sha256(receipt).hexdigest()
    assert prepared.candidate.generation_id == json.loads(prepared.candidate.candidate_receipt_bytes)["publication"]["generation_id"]
    assert set(prepared.decoded_record_counts) == set(native._ARTIFACT_NAMES)
    assert prepared.decoded_record_counts["vendor_aliases.parquet"] == len(supplied[2])
    assert prepared.decoded_record_counts["security_master.parquet"] == len(supplied[3])
    assert not prepared.candidate.published and not prepared.candidate.identity_admitted
    assert not prepared.candidate.records_bound_to_artifacts  # existing detached semantics unchanged
    result = json.loads(prepared.candidate.candidate_receipt_bytes)
    assert result["prospective_reference"] == supplied[0]["prospective_reference"]
    assert result["identity_observations"]["attempts"] == []


def test_r23_exact_parquet_changes_cannot_be_hidden_by_supplied_rows(supplied):
    import pyarrow as pa
    import pyarrow.parquet as pq
    from engine.neuralweb.market_memory_identity_candidate import (
        build_parquet_bound_initial_candidate,
    )
    receipt, artifacts = _r23_actual_parquet_supplied(supplied)
    changed = dict(artifacts)
    altered = copy.deepcopy(supplied[2])
    altered[1]["vendor_symbol"] = "FUTURE_FAKE"
    buf = pa.BufferOutputStream()
    pq.write_table(pa.Table.from_pylist(altered), buf)
    changed["vendor_aliases.parquet"] = buf.getvalue().to_pybytes()
    with pytest.raises(native.IdentityError):
        build_parquet_bound_initial_candidate(receipt, changed, code_version="3" * 40)


@pytest.mark.parametrize("name", _OBS_NAMES)
def test_r23_missing_or_corrupt_source_parquet_refuses(supplied, name):
    from engine.neuralweb.market_memory_identity_candidate import (
        build_parquet_bound_initial_candidate,
    )
    receipt, artifacts = _r23_actual_parquet_supplied(supplied)
    changed = dict(artifacts)
    del changed[name]
    with pytest.raises(native.IdentityError):
        build_parquet_bound_initial_candidate(receipt, changed, code_version="3" * 40)
    changed = dict(artifacts)
    changed[name] = b"NOT A PARQUET DOCUMENT"
    with pytest.raises(native.IdentityError):
        build_parquet_bound_initial_candidate(receipt, changed, code_version="3" * 40)


def test_r23_existing_published_receipt_is_not_replaced(supplied):
    from engine.neuralweb.market_memory_identity_candidate import (
        build_parquet_bound_initial_candidate,
    )
    receipt, artifacts = _r23_actual_parquet_supplied(supplied)
    parsed = json.loads(receipt)
    parsed["publication"] = {"old": "must-not-reset"}
    with pytest.raises(native.IdentityError, match="unpublished initial"):
        build_parquet_bound_initial_candidate(
            _obs_json(parsed), artifacts, code_version="3" * 40,
        )


def test_r23_no_caller_semantic_rows_or_clock_override(supplied):
    import inspect
    from engine.neuralweb.market_memory_identity_candidate import (
        build_parquet_bound_initial_candidate,
    )
    params = set(inspect.signature(build_parquet_bound_initial_candidate).parameters)
    assert params == {"receipt_before", "artifact_bytes", "code_version"}
    assert not params & {"alias_records", "master_records", "known_at", "read_completed_at",
                         "published", "security_id", "basis_id"}


def test_r23_deeply_copies_buffers_and_does_not_touch_local_files(supplied, monkeypatch):
    from engine.neuralweb.market_memory_identity_candidate import (
        build_parquet_bound_initial_candidate,
    )
    receipt, artifacts = _r23_actual_parquet_supplied(supplied)
    def forbidden(*_args, **_kwargs):
        pytest.fail("bound preparation attempted external file I/O")
    monkeypatch.setattr("builtins.open", forbidden)
    prepared = build_parquet_bound_initial_candidate(
        receipt, artifacts, code_version="3" * 40,
    )
    old = copy.deepcopy(prepared)
    artifacts.clear()
    assert prepared == old


def test_r23_existing_reader_reopens_bound_synthetic_candidate_at_actual_clock(
        supplied, tmp_path):
    """New binding + existing native reader: no backdate or canonical publisher."""
    import time
    from engine.neuralweb.market_memory_identity_candidate import (
        build_parquet_bound_initial_candidate,
    )
    from engine.entry_radar.replay.identity_observation_snapshot import (
        read_identity_snapshot,
    )
    receipt, files = _r23_actual_parquet_supplied(supplied)
    for name, raw in files.items():
        (tmp_path / name).write_bytes(raw)
    (tmp_path / "_receipt.json").write_bytes(receipt)
    with pytest.raises(native.IdentityError, match="snapshot owner context missing"):
        read_identity_snapshot(tmp_path)

    bound = build_parquet_bound_initial_candidate(
        receipt, files, code_version="3" * 40,
    )
    (tmp_path / "_receipt.json").write_bytes(bound.candidate.candidate_receipt_bytes)
    before = time.time_ns()
    observed = read_identity_snapshot(tmp_path)
    after = time.time_ns()
    read = observed.receipt.as_record()
    assert before <= int(read["read_completed_at_utc_ns"]) <= after
    assert read["generation_id"] == bound.candidate.generation_id
    assert observed.snapshot.receipt_bytes == bound.candidate.candidate_receipt_bytes
    assert observed.alias_table() is not None
    assert set(x.name for x in tmp_path.iterdir()) == {
        "_receipt.json", *native._ARTIFACT_NAMES,
    }
    assert not bound.published and not bound.identity_admitted
