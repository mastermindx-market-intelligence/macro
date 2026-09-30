"""Closure tests for the private native economic publication stage."""
from __future__ import annotations

import json
from pathlib import Path
from types import MappingProxyType
import time

import pytest
from hashlib import sha256

from engine.earnings_narrative.private_publication import (
    EarningsPrivatePublicationError,
    MAX_POINTER_BYTES,
    POINTER_KEY,
    prepare_private_publication,
    publish_private_publication,
)
from engine.earnings_narrative import private_publication as pp
from engine.earnings_narrative.context_packets import canonical_json_bytes
from tests.earnings_economic_private_fixtures import (
    ConditionalCountingStore,
    NoConditionalStore,
    fail_manifest_readback,
    fail_source_readback,
    published_v1_case,
    reseal_manifest,
    rights_registry,
    stage_economic_case,
)
from tests.test_earnings_private_store import _staged_publication

@pytest.fixture
def valid(tmp_path: Path):
    stage = stage_economic_case(tmp_path, "valid")
    return pp.prepare_private_publication(stage)

def test_v1_stage_is_unchanged_and_refuses_v2_record(tmp_path):
    from tests.test_earnings_private_store import _staged_publication
    _public, stage, slug = _staged_publication(tmp_path)
    prepared = pp.prepare_private_publication(stage, retire_slots=("z", "a", "z"))
    assert set(prepared.manifest) == {
        "schema", "generation_id", "published_at", "source", "record_count",
        "ticker_count", "records", "context",
    }
    assert prepared.retired_slots == ("a", "z")
    record = json.loads((stage / "records" / f"{slug}.json").read_bytes())
    record["schema"] = pp.RECORD_SCHEMA_V2
    record["economic_interpretation"] = {"state": "unavailable", "reason": "no_native_selection"}
    (stage / "records" / f"{slug}.json").write_bytes(canonical_json_bytes(record))
    with pytest.raises(pp.EarningsPrivatePublicationError):
        pp.prepare_private_publication(stage)

@pytest.mark.parametrize("case", ["valid", "corrected", "amended", "wire_unavailable", "wire_interpretation", "three_handles", "currentness_none"])
def test_accepted_v2_cases(tmp_path, case):
    prepared = pp.prepare_private_publication(stage_economic_case(tmp_path, case))
    native = prepared.manifest["native"]
    assert prepared.manifest["schema"] == pp.MANIFEST_SCHEMA_V2
    if case == "valid":
        assert len(native["workspaces"]) == len(native["documents"]) == len(native["source_bodies"]) == 1
        text_key = next(iter(native["source_bodies"].values()))["text"]["object_key"]
        artifact = {item.object_key: item for item in prepared.artifacts}[text_key]
        assert artifact.content_type == "text/plain; charset=utf-8"
        dossier = native["economic_slots"]["cik:0000080424"]["slug"]
        result = pp.validate_native_closure(prepared.manifest, prepared.payloads)
        assert result[dossier]["record"]["locked_facts"] == 20
    if case in ("corrected", "amended"):
        assert len(native["workspaces"]) == len(native["documents"]) == 2
        assert len(native["source_bodies"]) == (1 if case == "amended" else 2)
    assert pp.prepare_private_publication(stage_economic_case(tmp_path / "again", case)).manifest_bytes == prepared.manifest_bytes

def test_object_and_path_faults(tmp_path, valid):
    stage = stage_economic_case(tmp_path, "valid")
    prepared = pp.prepare_private_publication(stage)
    faults = ["missing_artifact", "unexpected_artifact", "digest_mismatch", "size_mismatch", "wrong_role", "unsafe_path", "over_limit"]
    for reason in faults:
        manifest = json.loads(prepared.manifest_bytes)
        payloads = dict(prepared.payloads)
        if reason == "missing_artifact":
            payloads.pop(next(iter(manifest["native"]["source_bodies"])) + ":missing", None)
            payloads.pop(next(iter(prepared.payloads)))
        elif reason == "unexpected_artifact":
            payloads["earnings_wire_private/v1/objects/sha256/00/" + ("0" * 64) + ".json"] = b"{}\n"
        elif reason == "digest_mismatch":
            digest = next(iter(manifest["native"]["source_bodies"]))
            receipt = manifest["native"]["source_bodies"][digest]["text"]
            payloads[receipt["object_key"]] = payloads[receipt["object_key"]][:-1] + b"x"
        elif reason == "size_mismatch":
            manifest["native"]["workspaces"][next(iter(manifest["native"]["workspaces"]))]["bytes"] += 1
            manifest = reseal_manifest(manifest, pp)
        elif reason == "wrong_role":
            digest = next(iter(manifest["native"]["source_bodies"]))
            manifest["native"]["source_bodies"][digest]["text"]["object_key"] = f"{pp.PRIVATE_PREFIX}/objects/sha256/{digest[:2]}/{digest}.json"
            manifest = reseal_manifest(manifest, pp)
        elif reason == "unsafe_path":
            manifest["native"]["source_bodies"][next(iter(manifest["native"]["source_bodies"]))]["text"]["object_key"] = "../escape"
            manifest = reseal_manifest(manifest, pp)
        elif reason == "over_limit":
            manifest["native"]["workspaces"][next(iter(manifest["native"]["workspaces"]))]["bytes"] = pp.MAX_NATIVE_WORKSPACE_BYTES + 1
            manifest = reseal_manifest(manifest, pp)
        with pytest.raises(pp.EarningsPrivateClosureError) as exc:
            pp.validate_native_closure(manifest, payloads)
        assert exc.value.reason == reason

def test_chain_and_pairing_faults(tmp_path, valid):
    prepared = pp.prepare_private_publication(stage_economic_case(tmp_path, "valid"))
    manifest = json.loads(prepared.manifest_bytes)
    slug = manifest["native"]["economic_slots"]["cik:0000080424"]["slug"]
    manifest["native"]["selections"][slug]["chain"][0]["document"] = "0" * 64
    with pytest.raises(pp.EarningsPrivateClosureError) as exc:
        pp.validate_native_closure(reseal_manifest(manifest, pp), prepared.payloads)
    assert exc.value.reason == "missing_artifact"

def test_interpretation_faults(tmp_path, valid):
    prepared = pp.prepare_private_publication(stage_economic_case(tmp_path, "valid"))
    manifest = json.loads(prepared.manifest_bytes)
    slug = manifest["native"]["economic_slots"]["cik:0000080424"]["slug"]
    record_key = manifest["records"][slug]["object_key"]
    record = json.loads(prepared.payloads[record_key])
    record["economic_interpretation"]["observations"][0]["value"] = "999"
    payloads = dict(prepared.payloads)
    payloads.pop(record_key)
    body = canonical_json_bytes(record)
    digest = sha256(body).hexdigest()
    record_key = f"{pp.PRIVATE_PREFIX}/objects/sha256/{digest[:2]}/{digest}.json"
    payloads[record_key] = body
    manifest["records"][slug].update({"sha256": digest, "bytes": len(body), "object_key": record_key})
    with pytest.raises(pp.EarningsPrivateClosureError) as exc:
        pp.validate_native_closure(reseal_manifest(manifest, pp), payloads)
    assert exc.value.reason == "interpretation_mismatch"
    result = pp.validate_native_closure(reseal_manifest(manifest, pp), payloads, interpretations=False)
    assert result[slug]["chain"]

def test_rights_guard_and_surface(tmp_path, valid):
    assert pp.CLOSURE_REASONS == tuple(reason for reason in pp.CLOSURE_REASONS)
    assert len(pp.CLOSURE_REASONS) == 17
    assert issubclass(pp.EarningsPrivateClosureError, pp.EarningsPrivatePublicationError)
    with pytest.raises(ValueError):
        pp.EarningsPrivateClosureError("not-a-reason")
    with pytest.raises(pp.EarningsPrivatePublishConflict) as exc:
        pp.publish_private_publication(NoConditionalStore(tmp_path / "store"), valid)
    assert exc.value.reason == "conditional_write_unavailable"
    prepared = pp.prepare_private_publication(stage_economic_case(tmp_path / "stage", "valid"), retire_slots=["b", "a", "b"])
    assert prepared.retired_slots == ("a", "b")
    with pytest.raises(pp.EarningsPrivateClosureError) as exc:
        pp.prepare_private_publication(stage_economic_case(tmp_path / "bad", "valid"), retire_slots=[1])
    assert exc.value.reason == "malformed_native_section"

@pytest.fixture
def native(valid):
    return json.loads(valid.manifest_bytes), dict(valid.payloads)

def expect_closure(reason, callable_object, *args, **kwargs):
    with pytest.raises(pp.EarningsPrivateClosureError) as caught:
        callable_object(*args, **kwargs)
    assert caught.value.reason == reason
    return caught.value

def object_key(digest, suffix=".json"):
    return f"{pp.PRIVATE_PREFIX}/objects/sha256/{digest[:2]}/{digest}{suffix}"

def first_receipt(catalog):
    return next(iter(catalog.values()))

def test_stage_object_faults(tmp_path, native):
    manifest, payloads = native
    source_digest, source = next(iter(manifest["native"]["source_bodies"].items()))
    workspace_id, workspace_receipt = next(iter(manifest["native"]["workspaces"].items()))
    checks = {
        "missing_artifact": lambda: pp.validate_native_closure(reseal_manifest(manifest, pp), {
            key: value for key, value in payloads.items() if key != source["text"]["object_key"]
        }),
        "unexpected_artifact": lambda: pp.validate_native_closure(reseal_manifest(manifest, pp), {
            **payloads, object_key("0" * 64): b"{}\n"
        }),
        "digest_mismatch": lambda: pp.validate_native_closure(reseal_manifest(manifest, pp), {
            **payloads,
            source["text"]["object_key"]: payloads[source["text"]["object_key"]][:-1] + b"x",
        }),
        "size_mismatch": lambda: pp.validate_native_closure(reseal_manifest({
            **manifest,
            "native": {
                **manifest["native"],
                "workspaces": {**manifest["native"]["workspaces"], workspace_id: {
                    **workspace_receipt, "bytes": workspace_receipt["bytes"] + 1
                }},
            },
        }, pp), payloads),
        "over_limit": lambda: pp.validate_native_closure(reseal_manifest({
            **manifest,
            "native": {
                **manifest["native"],
                "workspaces": {**manifest["native"]["workspaces"], workspace_id: {
                    **workspace_receipt, "bytes": pp.MAX_SOURCE_BODY_BYTES + 1
                }},
            },
        }, pp), payloads),
    }
    for reason, check in checks.items():
        expect_closure(reason, check)

def test_native_stage_file_faults(tmp_path, valid):
    checks = {
        "unexpected_artifact": lambda stage: (stage / "native" / "extra.txt").write_bytes(b"x"),
        "missing_artifact": lambda stage: next(iter((stage / "native" / "workspaces").glob("*.json"))).unlink(),
        "digest_mismatch": lambda stage: _rename_stage_document(stage),
        "unsafe_path": lambda stage: _replace_one_stage_file_with_link(stage / "native" / "workspaces"),
        "over_limit": lambda stage: _make_oversized(
            next(iter((stage / "native" / "workspaces").glob("*.json"))),
        ),
    }
    for reason, fault in checks.items():
        stage = stage_economic_case(tmp_path / reason, "valid")
        fault(stage)
        expect_closure(reason, pp.prepare_private_publication, stage)


def test_round_b_public_surface(valid):
    generation_id = valid.generation_id
    digest = sha256(valid.manifest_bytes).hexdigest()

    assert pp.validate_generation_id(generation_id) == generation_id
    assert pp.validate_digest(digest) == digest
    for value in (
        type("Substr", (str,), {})(generation_id),
        1,
        generation_id.upper(),
        generation_id + "\n",
    ):
        with pytest.raises(pp.EarningsPrivatePublicationError, match="invalid earnings generation id"):
            pp.validate_generation_id(value)
    for value in (
        type("Substr", (str,), {})(digest),
        1,
        digest.upper(),
        digest + "\n",
    ):
        with pytest.raises(pp.EarningsPrivatePublicationError, match="invalid earnings digest"):
            pp.validate_digest(value)

    assert pp.PUBLISH_CONFLICT_REASONS == (
        "predecessor_conflict", "downgrade_refused", "slot_removed", "retirement_invalid",
        "chain_not_extended", "conditional_write_unavailable", "stale_native_cutoff",
        "installed_unreadable",
    )
    assert pp.NOT_FOUND_REASONS == (
        "no_slot", "unknown_generation", "unknown_record", "unknown_fact", "absent_fact",
    )
    assert pp.READ_UNAVAILABLE_REASONS == (
        "interpretation_unsupported", "rights_refused", "evidence_retired",
    )
    assert issubclass(pp.EarningsPrivatePublishConflict, pp.EarningsPrivatePublicationError)
    assert issubclass(pp.EarningsPrivatePointerEffectUnknown, pp.EarningsPrivatePublicationError)
    assert issubclass(pp.EarningsEconomicNotFound, pp.EarningsPrivateRecordNotFound)
    assert issubclass(pp.EarningsEconomicUnavailable, pp.EarningsPrivatePublicationError)
    assert not issubclass(pp.EarningsEconomicUnavailable, pp.EarningsPrivateRecordNotFound)
    assert issubclass(pp.EarningsPrivateManifestNotCurrent, pp.EarningsPrivatePublicationError)

    with pytest.raises(ValueError):
        pp.EarningsPrivatePublishConflict("not-a-reason")
    with pytest.raises(ValueError):
        pp.EarningsEconomicNotFound("not-a-reason")
    with pytest.raises(ValueError):
        pp.EarningsEconomicUnavailable("not-a-reason")
    unknown = pp.EarningsPrivatePointerEffectUnknown(generation_id, digest, "sha256:" + digest)
    assert (unknown.generation_id, unknown.pointer_sha256, unknown.expected_version) == (
        generation_id, digest, "sha256:" + digest
    )
    assert str(unknown) == "private earnings pointer write effect is unknown"
    assert not any(piece in str(unknown) for piece in (generation_id, digest))

    public_names = (
        "EarningsPrivatePublishConflict", "EarningsPrivatePointerEffectUnknown",
        "EarningsEconomicNotFound", "EarningsEconomicUnavailable",
        "EarningsPrivateManifestNotCurrent", "validate_generation_id", "validate_digest",
        "load_private_predecessor", "load_private_manifest_version", "load_economic_closure",
        "load_current_economic_view", "load_economic_evidence", "PUBLISH_CONFLICT_REASONS",
        "NOT_FOUND_REASONS", "READ_UNAVAILABLE_REASONS",
    )
    assert set(public_names) <= set(pp.__all__)


def test_round_b_fixture_surface(tmp_path):
    store, pointer = published_v1_case(tmp_path)
    assert isinstance(store, ConditionalCountingStore)
    assert pp.POINTER_KEY in store.put_calls
    stage = stage_economic_case(tmp_path, "empty_native")
    assert (stage / "native").is_dir()
    assert not list((stage / "native" / "workspaces").iterdir())
    assert not list((stage / "native" / "documents").iterdir())
    assert not list((stage / "native" / "source_bodies").iterdir())
    assert pointer["schema"] == pp.POINTER_SCHEMA


def test_v2_publication_requires_conditional_store(tmp_path):
    store, _baseline = published_v1_case(tmp_path)
    prepared = pp.prepare_private_publication(stage_economic_case(tmp_path, "valid"))
    no_conditional = NoConditionalStore(tmp_path / "no-conditional")
    with pytest.raises(pp.EarningsPrivatePublishConflict) as exc:
        pp.publish_private_publication(no_conditional, prepared)
    assert exc.value.reason == "conditional_write_unavailable"
    assert no_conditional.calls == []

    store.capability_error = RuntimeError("capability probe failed")
    store.put_calls.clear()
    with pytest.raises(pp.EarningsPrivatePublishConflict) as exc:
        pp.publish_private_publication(store, prepared)
    assert exc.value.reason == "conditional_write_unavailable"
    assert store.versioned_reads == []
    assert store.put_calls == []
    assert pp.POINTER_KEY not in store.put_calls


def test_v1_downgrade_and_retirement_are_refused_before_writes(tmp_path):
    _public, v1_stage, _slug = _staged_publication(tmp_path / "v1-stage")
    v1_prepared = pp.prepare_private_publication(v1_stage)
    store, baseline = published_v1_case(tmp_path)
    valid = pp.prepare_private_publication(stage_economic_case(tmp_path, "valid"))
    pp.publish_private_publication(store, valid)
    installed = pp.load_private_manifest(store)
    v1_prepared = pp.prepare_private_publication(v1_stage)
    store.put_calls.clear()
    with pytest.raises(pp.EarningsPrivatePublishConflict) as exc:
        pp.publish_private_publication(store, v1_prepared)
    assert exc.value.reason == "downgrade_refused"
    assert store.put_calls == []
    predecessor = pp.load_private_predecessor(store)
    assert set(predecessor) == {
        "generation_id", "manifest_key", "manifest_sha256", "manifest_bytes", "published_at"
    }
    assert predecessor["generation_id"] == installed["generation_id"]

    retired = pp.prepare_private_publication(v1_stage, retire_slots=("cik:0000080424",))
    with pytest.raises(pp.EarningsPrivatePublishConflict) as exc:
        pp.publish_private_publication(ConditionalCountingStore(tmp_path / "retired"), retired)
    assert exc.value.reason == "retirement_invalid"


def test_readback_failure_reason_and_control_twins(tmp_path):
    store, baseline = published_v1_case(tmp_path)
    prepared = pp.prepare_private_publication(stage_economic_case(tmp_path, "valid"))
    fail_source_readback(store, prepared)
    store.put_calls.clear()

    with pytest.raises(pp.EarningsPrivateClosureError) as exc:
        pp.publish_private_publication(store, prepared)

    assert exc.value.reason in {"digest_mismatch", "malformed_native_section", "unsafe_path"}
    assert store.get_bytes(pp.POINTER_KEY) == canonical_json_bytes(baseline)
    assert pp.POINTER_KEY not in store.put_calls
    assert pp.POINTER_KEY not in store.conditional_calls

    control_store, control_baseline = published_v1_case(tmp_path / "control")
    control = pp.prepare_private_publication(stage_economic_case(tmp_path / "control", "valid"))
    pp.publish_private_publication(control_store, control)
    assert control_store.get_bytes(pp.POINTER_KEY) != canonical_json_bytes(control_baseline)
    assert pp.POINTER_KEY in control_store.conditional_calls


def test_pointer_does_not_move_when_required_source_readback_fails(tmp_path):
    store, baseline = published_v1_case(tmp_path)
    before = store.get_bytes_strict_bounded(POINTER_KEY, MAX_POINTER_BYTES)
    stage = stage_economic_case(tmp_path, 'valid')
    prepared = prepare_private_publication(stage)
    fail_source_readback(store, prepared)
    with pytest.raises(EarningsPrivatePublicationError):
        publish_private_publication(store, prepared)
    assert store.get_bytes_strict_bounded(POINTER_KEY, MAX_POINTER_BYTES) == before


def test_manifest_readback_digest_mismatch_and_control_twins(tmp_path):
    store, baseline = published_v1_case(tmp_path)
    prepared = pp.prepare_private_publication(stage_economic_case(tmp_path, "valid"))
    fail_manifest_readback(store, prepared)
    store.put_calls.clear()
    store.conditional_calls.clear()
    with pytest.raises(pp.EarningsPrivateClosureError) as exc:
        pp.publish_private_publication(store, prepared)
    assert exc.value.reason == "digest_mismatch"
    assert store.get_bytes(pp.POINTER_KEY) == canonical_json_bytes(baseline)
    assert pp.POINTER_KEY not in store.put_calls
    assert pp.POINTER_KEY not in store.conditional_calls

    control_store, control_baseline = published_v1_case(tmp_path / "control")
    control = pp.prepare_private_publication(stage_economic_case(tmp_path / "control", "valid"))
    pp.publish_private_publication(control_store, control)
    assert control_store.get_bytes(pp.POINTER_KEY) == canonical_json_bytes(pp._pointer_for(control))
    assert control_store.get_bytes(pp.POINTER_KEY) != canonical_json_bytes(control_baseline)


def test_verify_before_parse_keeps_hostile_documents_typed(tmp_path):
    store, _baseline = published_v1_case(tmp_path)
    prepared = pp.prepare_private_publication(stage_economic_case(tmp_path, "valid"))
    pp.publish_private_publication(store, prepared)
    manifest = pp.load_private_manifest(store)
    slug = "pg-synthetic-economic-dossier"
    document_digest = manifest["native"]["selections"][slug]["chain"][0]["document"]
    document_receipt = manifest["native"]["documents"][document_digest]
    document_path = store.root / Path(document_receipt["object_key"])
    original = document_path.read_bytes()
    hostile = original[:-1] + bytes([original[-1] ^ 1])

    for corruption in (
        hostile,
        original[: len(original) // 2],
        b"",
        b"[]\n",
        canonical_json_bytes({**json.loads(original), "content_sha256": "0" * 64}),
    ):
        document_path.write_bytes(corruption)
        current = pp.load_private_manifest(store)
        manifest_digest = sha256(store.get_bytes(prepared.manifest_key)).hexdigest()
        for reader in (
            lambda: pp.load_economic_closure(store, manifest=current, slug=slug),
            lambda: pp.load_economic_closure(
                store, manifest=current, slug=slug, interpretation="stale_ok"
            ),
            lambda: pp.load_current_economic_view(store, "PG", manifest=current),
            lambda: pp.load_economic_evidence(
                store,
                generation_id=current["generation_id"],
                manifest_digest=manifest_digest,
                record_digest=current["records"][slug]["sha256"],
                slug=slug,
                fact_id="fact_id",
            ),
        ):
            try:
                reader()
            except Exception as exc:
                assert isinstance(exc, pp.EarningsPrivatePublicationError), type(exc)

        document_path.write_bytes(original)


@pytest.fixture
def economic_publish(tmp_path, monkeypatch):
    monkeypatch.setattr(pp, "NATIVE_RIGHTS_REGISTRY_PATH", rights_registry(tmp_path))
    store, baseline = published_v1_case(tmp_path)
    prepared = pp.prepare_private_publication(stage_economic_case(tmp_path, "valid"))
    pp.publish_private_publication(store, prepared)
    return store, prepared, baseline, monkeypatch


def test_v2_publication_refuses_when_native_rights_are_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(pp, "NATIVE_RIGHTS_REGISTRY_PATH", rights_registry(tmp_path, refusing=True))
    store, baseline = published_v1_case(tmp_path)
    prepared = pp.prepare_private_publication(stage_economic_case(tmp_path, "valid"))
    store.put_calls.clear()
    store.conditional_calls.clear()
    with pytest.raises(pp.EarningsEconomicUnavailable) as exc:
        pp.publish_private_publication(store, prepared)
    assert exc.value.reason == "rights_refused"
    assert store.put_calls == []
    assert store.conditional_calls == []
    assert store.get_bytes(pp.POINTER_KEY) == canonical_json_bytes(baseline)


def test_uncertain_pointer_write_is_never_restored(tmp_path, monkeypatch):
    monkeypatch.setattr(pp, "NATIVE_RIGHTS_REGISTRY_PATH", rights_registry(tmp_path))
    store, baseline = published_v1_case(tmp_path)
    prepared = pp.prepare_private_publication(stage_economic_case(tmp_path, "valid"))
    store.put_calls.clear()
    pointer_bytes = canonical_json_bytes(pp._pointer_for(prepared))
    old_bytes = canonical_json_bytes(baseline)
    expected_version = store.get_bytes_strict_bounded_versioned(
        pp.POINTER_KEY, pp.MAX_POINTER_BYTES
    ).version

    store.raise_before_conditional = True
    with pytest.raises(pp.EarningsPrivatePointerEffectUnknown) as exc:
        pp.publish_private_publication(store, prepared)
    assert (exc.value.generation_id, exc.value.expected_version) == (
        prepared.generation_id, expected_version
    )
    assert exc.value.pointer_sha256 == sha256(pointer_bytes).hexdigest()
    assert sha256(str(exc.value).encode()).hexdigest() != exc.value.pointer_sha256
    assert store.get_bytes(pp.POINTER_KEY) == old_bytes
    assert store.conditional_calls == [pp.POINTER_KEY]
    assert pp.POINTER_KEY not in store.put_calls

    store.raise_before_conditional = False
    store.raise_after_conditional = True
    with pytest.raises(pp.EarningsPrivatePointerEffectUnknown):
        pp.publish_private_publication(store, prepared)
    assert store.get_bytes(pp.POINTER_KEY) == pointer_bytes
    assert store.conditional_calls.count(pp.POINTER_KEY) == 2

    store.raise_after_conditional = False
    reconciled = pp.publish_private_publication(store, prepared)
    assert reconciled == pp._pointer_for(prepared)
    assert store.conditional_calls.count(pp.POINTER_KEY) == 2


def test_foreign_pointer_echo_is_not_restored(tmp_path, monkeypatch):
    monkeypatch.setattr(pp, "NATIVE_RIGHTS_REGISTRY_PATH", rights_registry(tmp_path))
    store, baseline = published_v1_case(tmp_path)
    prepared = pp.prepare_private_publication(stage_economic_case(tmp_path, "valid"))
    pointer_bytes = canonical_json_bytes(pp._pointer_for(prepared))
    store.put_calls.clear()
    store.foreign_echo = True
    with pytest.raises(pp.EarningsPrivatePointerEffectUnknown):
        pp.publish_private_publication(store, prepared)
    assert store.get_bytes(pp.POINTER_KEY) == pointer_bytes
    assert store.conditional_calls == [pp.POINTER_KEY]
    assert pp.POINTER_KEY not in store.put_calls


def test_v2_publish_validates_prepared_closure_before_store_access(tmp_path):
    store, _baseline = published_v1_case(tmp_path)
    prepared = pp.prepare_private_publication(stage_economic_case(tmp_path, "valid"))
    manifest = json.loads(prepared.manifest_bytes)
    source_digest = next(iter(manifest["native"]["source_bodies"]))
    source_key = manifest["native"]["source_bodies"][source_digest]["text"]["object_key"]
    altered = prepared.payloads[source_key] + b" "
    manifest["native"]["source_bodies"][source_digest]["text"]["sha256"] = sha256(altered).hexdigest()
    manifest = reseal_manifest(manifest, pp)
    object.__setattr__(prepared, "manifest", MappingProxyType(manifest))
    object.__setattr__(prepared, "payloads", MappingProxyType({**prepared.payloads, source_key: altered}))
    store.versioned_reads.clear()
    store.put_calls.clear()
    store.conditional_calls.clear()
    with pytest.raises(pp.EarningsPrivatePublicationError) as exc:
        pp.publish_private_publication(store, prepared)
    assert isinstance(exc.value, pp.EarningsPrivateClosureError)
    assert exc.value.reason in {"digest_mismatch", "malformed_native_section", "unsafe_path"}
    assert store.versioned_reads == []
    assert store.put_calls == []
    assert store.conditional_calls == []

    no_native = pp.prepare_private_publication(stage_economic_case(tmp_path, "wire_unavailable", name="wire"))
    manifest = json.loads(no_native.manifest_bytes)
    manifest.pop("native")
    object.__setattr__(no_native, "manifest", MappingProxyType(manifest))
    store.versioned_reads.clear()
    with pytest.raises(pp.EarningsPrivatePublicationError):
        pp.publish_private_publication(store, no_native)
    assert store.versioned_reads == []
    assert store.put_calls == []
    assert store.conditional_calls == []

    control_store, _control_baseline = published_v1_case(tmp_path / "control")
    control = pp.prepare_private_publication(stage_economic_case(tmp_path / "control", "valid"))
    pp.publish_private_publication(control_store, control)


def test_closure_mode_shape_and_strict_evidence_digest(tmp_path, economic_publish):
    store, _prepared, _baseline, _fixture_patch = economic_publish
    manifest = pp.load_private_manifest(store)
    slug = manifest["native"]["economic_slots"]["cik:0000080424"]["slug"]
    verified = pp.load_economic_closure(store, manifest=manifest, slug=slug)
    assert set(verified) == {"record", "selection", "interpretation", "chain"}

    class DeceptiveConflict(pp.EarningsPrivatePublishConflict):
        def __init__(self):
            super().__init__("downgrade_refused")
            self.reason = "conditional_write_unavailable"
    store.capability_error = DeceptiveConflict()
    prepared = pp.prepare_private_publication(stage_economic_case(tmp_path, "corrected", name="capability"))
    store.versioned_reads.clear()
    store.put_calls.clear()
    with pytest.raises(pp.EarningsPrivatePublishConflict) as capability:
        pp.publish_private_publication(store, prepared)
    assert capability.value.reason == "conditional_write_unavailable"
    assert store.versioned_reads == []
    assert store.put_calls == []

    view = pp.load_current_economic_view(store, "PG", manifest=manifest)
    fact = next(item for item in view["interpretation"]["observations"] if item.get("source_excerpt"))
    class DeceptiveStr(str):
        def __eq__(self, other):
            return True
        def __hash__(self):
            return hash("deceptive")
    with pytest.raises(pp.EarningsEconomicNotFound) as digest_error:
        pp.load_economic_evidence(
            store,
            generation_id=view["generation_id"],
            manifest_digest=view["manifest_sha256"],
            record_digest=DeceptiveStr(view["record_sha256"]),
            slug=view["slug"],
            fact_id=fact["fact_id"],
        )
    assert digest_error.value.reason == "unknown_record"
    real = pp.load_economic_evidence(
        store,
        generation_id=view["generation_id"],
        manifest_digest=view["manifest_sha256"],
        record_digest=view["record_sha256"],
        slug=view["slug"],
        fact_id=fact["fact_id"],
    )
    assert real["record_sha256"] == view["record_sha256"]


def test_predecessor_race_hooks_and_control(tmp_path):
    for race_when in ("after_key_write", "after_next_versioned_read"):
        store, _baseline = published_v1_case(tmp_path / race_when)
        prepared = pp.prepare_private_publication(stage_economic_case(tmp_path / race_when, "valid"))
        store.race_after_key = prepared.manifest_key
        store.race_when = race_when
        store.put_calls.clear()
        before_conditional_calls = list(store.conditional_calls)
        with pytest.raises(pp.EarningsPrivatePublishConflict) as exc:
            pp.publish_private_publication(store, prepared)
        assert exc.value.reason == "predecessor_conflict"
        assert store.get_bytes(pp.POINTER_KEY) == store._foreign_pointer
        assert pp.POINTER_KEY not in store.put_calls
        expected_conditionals = (
            before_conditional_calls
            if race_when == "after_key_write"
            else before_conditional_calls + [pp.POINTER_KEY]
        )
        assert store.conditional_calls == expected_conditionals

    control_store, _control_baseline = published_v1_case(tmp_path / "control")
    control = pp.prepare_private_publication(stage_economic_case(tmp_path / "control", "valid"))
    pp.publish_private_publication(control_store, control)
    assert control_store.get_bytes(pp.POINTER_KEY) == canonical_json_bytes(pp._pointer_for(control))


def test_closure_reader_matrix_and_plain_interpretation_argument(tmp_path, economic_publish):
    store, _prepared, _baseline, _patch = economic_publish
    manifest = pp.load_private_manifest(store)
    slug = manifest["native"]["economic_slots"]["cik:0000080424"]["slug"]
    entry = pp.load_economic_closure(store, manifest=manifest, slug=slug)
    assert set(entry) == {"record", "selection", "interpretation", "chain"}
    assert entry["record"]["economic_interpretation"] == entry["interpretation"]
    wire_slug = next(value for value in manifest["records"] if value != slug)
    for unknown_slug in ("unknown-slug", wire_slug):
        with pytest.raises(pp.EarningsEconomicNotFound) as unknown_error:
            pp.load_economic_closure(store, manifest=manifest, slug=unknown_slug)
        assert unknown_error.value.reason == "unknown_record"

    source_digest = next(iter(manifest["native"]["source_bodies"]))
    source_path = store.root / Path(manifest["native"]["source_bodies"][source_digest]["text"]["object_key"])
    original_source = source_path.read_bytes()
    source_path.write_bytes(bytes([original_source[0] ^ 1]) + original_source[1:])
    with pytest.raises(pp.EarningsPrivateClosureError) as source_error:
        pp.load_economic_closure(store, manifest=manifest, slug=slug, interpretation="stale_ok")
    assert source_error.value.reason == "digest_mismatch"
    source_path.write_bytes(original_source)

    record_path = store.root / Path(manifest["records"][slug]["object_key"])
    original_record = record_path.read_bytes()
    record = json.loads(original_record)
    record["economic_interpretation"]["observations"][0]["value"] = "999"
    altered_record = canonical_json_bytes(record)
    digest = sha256(altered_record).hexdigest()
    rebuilt = json.loads(json.dumps(manifest))
    rebuilt["records"][slug].update({"sha256": digest, "bytes": len(altered_record)})
    object_key = f"{pp.PRIVATE_PREFIX}/objects/sha256/{digest[:2]}/{digest}.json"
    rebuilt["records"][slug]["object_key"] = object_key
    rebuilt = reseal_manifest(rebuilt, pp)
    new_record_path = store.root / Path(object_key)
    new_record_path.parent.mkdir(parents=True, exist_ok=True)
    new_record_path.write_bytes(altered_record)
    pointer_path = store.root / Path(pp.POINTER_KEY)
    pointer = json.loads(pointer_path.read_bytes())
    pointer.update(
        generation_id=rebuilt["generation_id"],
        manifest_key=f"{pp.PRIVATE_PREFIX}/manifests/{rebuilt['generation_id']}.json",
        manifest_sha256=sha256(canonical_json_bytes(rebuilt)).hexdigest(),
        manifest_bytes=len(canonical_json_bytes(rebuilt)),
    )
    rebuilt_manifest_path = store.root / Path(
        f"{pp.PRIVATE_PREFIX}/manifests/{rebuilt['generation_id']}.json"
    )
    rebuilt_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    rebuilt_manifest_path.write_bytes(canonical_json_bytes(rebuilt))
    pointer_path.write_bytes(canonical_json_bytes(pointer))
    with pytest.raises(pp.EarningsPrivateClosureError) as interpretation_error:
        pp.load_economic_closure(store, manifest=rebuilt, slug=slug, interpretation="stale_ok")
    assert interpretation_error.value.reason == "interpretation_mismatch"

    class StringValue(str):
        pass

    for interpretation in ("STALE_OK", None, StringValue("stale_ok")):
        with pytest.raises(ValueError):
            pp.load_economic_closure(store, manifest=rebuilt, slug=slug, interpretation=interpretation)

    record_path.write_bytes(original_record)


def test_stale_ok_only_downgrades_supported_code_revision(tmp_path, monkeypatch, economic_publish):
    store, prepared, _baseline, _fixture_patch = economic_publish
    manifest = pp.load_private_manifest(store)
    slug = manifest["native"]["economic_slots"]["cik:0000080424"]["slug"]
    current = pp.load_economic_closure(store, manifest=manifest, slug=slug, interpretation="stale_ok")
    assert set(current) == {"record", "selection", "interpretation", "chain", "interpretation_state"}
    assert current["interpretation_state"] == "current"

    monkeypatch.setattr(pp.economic_interpretation, "CODE_REVISION", "0" * 64)
    with pytest.raises(pp.EarningsEconomicUnavailable) as verify_error:
        pp.load_economic_closure(store, manifest=manifest, slug=slug)
    assert verify_error.value.reason == "interpretation_unsupported"
    stale = pp.load_economic_closure(store, manifest=manifest, slug=slug, interpretation="stale_ok")
    assert stale["interpretation"] is None
    assert stale["interpretation_state"] == "stale"
    assert (stale["record"], stale["selection"], stale["chain"]) == (
        current["record"], current["selection"], current["chain"]
    )

    monkeypatch.setattr(pp.pg_profile, "PG_PROFILE_VERSION", "synthetic-other")
    with pytest.raises(pp.EarningsEconomicUnavailable) as profile_error:
        pp.load_economic_closure(store, manifest=manifest, slug=slug, interpretation="stale_ok")
    assert profile_error.value.reason == "interpretation_unsupported"


@pytest.fixture(autouse=True)
def permitting_native_rights(tmp_path, monkeypatch):
    monkeypatch.setattr(
        pp, "NATIVE_RIGHTS_REGISTRY_PATH", rights_registry(tmp_path)
    )




def test_predecessor_and_slot_rules(tmp_path):
    store, baseline = published_v1_case(tmp_path)
    pp.publish_private_publication(store, pp.prepare_private_publication(stage_economic_case(tmp_path, "valid")))
    installed = pp.load_private_manifest(store)
    empty_store, _empty_baseline = published_v1_case(tmp_path / "empty-v1")
    empty_store.put_calls.clear()

    none_bound = pp.prepare_private_publication(stage_economic_case(tmp_path, "corrected", name="none"))
    manifest = {**none_bound.manifest, "previous_manifest": None}
    manifest = reseal_manifest(manifest, pp)
    object.__setattr__(none_bound, "manifest", MappingProxyType(manifest))
    with pytest.raises(pp.EarningsPrivatePublishConflict) as exc:
        pp.publish_private_publication(empty_store, none_bound)
    assert exc.value.reason == "predecessor_conflict"
    assert empty_store.put_calls == []

    foreign = {
        "generation_id": "earnpriv_" + "1" * 32,
        "manifest_key": f"{pp.PRIVATE_PREFIX}/manifests/earnpriv_" + "1" * 32 + ".json",
        "manifest_sha256": "1" * 64,
        "manifest_bytes": 2,
        "published_at": installed["previous_manifest"]["published_at"],
    }
    other_bound = pp.prepare_private_publication(stage_economic_case(tmp_path, "corrected", name="other"))
    other_manifest = reseal_manifest({**other_bound.manifest, "previous_manifest": foreign}, pp)
    object.__setattr__(other_bound, "manifest", MappingProxyType(other_manifest))
    store.put_calls.clear()
    store.conditional_calls.clear()
    with pytest.raises(pp.EarningsPrivatePublishConflict) as exc:
        pp.publish_private_publication(store, other_bound)
    assert exc.value.reason == "predecessor_conflict"
    assert store.put_calls == []

    with pytest.raises(pp.EarningsPrivatePublishConflict) as exc:
        pp.publish_private_publication(store, pp.prepare_private_publication(stage_economic_case(tmp_path, "empty_native", name="removed")))
    assert exc.value.reason == "slot_removed"
    pp.publish_private_publication(store, pp.prepare_private_publication(stage_economic_case(tmp_path, "empty_native", name="retired"), retire_slots=("cik:0000080424",)))
    with pytest.raises(pp.EarningsPrivatePublishConflict) as exc:
        pp.publish_private_publication(store, pp.prepare_private_publication(stage_economic_case(tmp_path, "empty_native", name="invalid"), retire_slots=("cik:0000080424",)))
    assert exc.value.reason == "retirement_invalid"


def test_chain_and_cutoff_rules(tmp_path):
    store, baseline = published_v1_case(tmp_path)
    pp.publish_private_publication(store, pp.prepare_private_publication(stage_economic_case(tmp_path, "valid")))
    pp.publish_private_publication(store, pp.prepare_private_publication(stage_economic_case(tmp_path, "corrected", name="corrected")))
    pointer = store.get_bytes(pp.POINTER_KEY)
    with pytest.raises(pp.EarningsPrivatePublishConflict) as exc:
        pp.publish_private_publication(store, pp.prepare_private_publication(stage_economic_case(tmp_path, "amended", name="amended")))
    assert exc.value.reason == "chain_not_extended"
    assert store.get_bytes(pp.POINTER_KEY) == pointer
    short = pp.prepare_private_publication(stage_economic_case(tmp_path, "valid", name="short"))
    installed_selection = next(iter(pp.load_private_manifest(store)["native"]["selections"].values()))
    short_selection = next(iter(short.manifest["native"]["selections"].values()))
    assert len(short_selection["chain"]) < len(installed_selection["chain"])
    with pytest.raises(pp.EarningsPrivatePublishConflict) as exc:
        pp.publish_private_publication(store, short)
    assert exc.value.reason == "chain_not_extended"
    assert store.get_bytes(pp.POINTER_KEY) == pointer

    stale_stage = stage_economic_case(tmp_path, "corrected", name="stale")
    latest = json.loads((stale_stage / "native" / "latest.json").read_bytes())
    latest["native_source_cutoff"] = "2026-07-30T23:59:59Z"
    (stale_stage / "native" / "latest.json").write_bytes(canonical_json_bytes(latest))
    with pytest.raises(pp.EarningsPrivatePublishConflict) as exc:
        pp.publish_private_publication(store, pp.prepare_private_publication(stale_stage))
    assert exc.value.reason == "stale_native_cutoff"


def test_current_view_and_pinned_evidence(tmp_path, economic_publish):
    store, _prepared, baseline, _patch = economic_publish
    current = pp.load_private_manifest(store)
    view = pp.load_current_economic_view(store, "PG", manifest=current)
    assert set(view) == {
        "generation_id", "manifest_sha256", "record_sha256", "slug",
        "interpretation", "source",
    }
    assert view["generation_id"] == current["generation_id"]
    assert view["record_sha256"] == current["records"][view["slug"]]["sha256"]
    encoded = canonical_json_bytes(view).decode()
    assert pp.PRIVATE_PREFIX not in encoded and "objects/sha256" not in encoded
    for ticker in ("ZZZZ", "AAPL"):
        with pytest.raises(pp.EarningsEconomicNotFound) as ticker_error:
            pp.load_current_economic_view(store, ticker, manifest=current)
        assert ticker_error.value.reason == "no_slot"
    previous = pp.load_private_manifest_version(
        store,
        generation_id=baseline["generation_id"],
        expected_digest=baseline["manifest_sha256"],
    )
    with pytest.raises(pp.EarningsPrivateManifestNotCurrent):
        pp.load_current_economic_view(store, "PG", manifest=previous)

    fact = next(item for item in view["interpretation"]["observations"] if item.get("source_excerpt"))
    evidence = pp.load_economic_evidence(
        store,
        generation_id=view["generation_id"],
        manifest_digest=view["manifest_sha256"],
        record_digest=view["record_sha256"],
        slug=view["slug"],
        fact_id=fact["fact_id"],
    )
    assert set(evidence) == {
        "generation_id", "manifest_sha256", "record_sha256", "slug", "fact_id",
        "document_id", "source_sha256", "observation", "source_text",
    }
    assert evidence["source_sha256"] == view["source"]["source_sha256"]
    assert evidence["source_text"] == {"text": fact["source_excerpt"], "lang": "en"}
    with pytest.raises(pp.EarningsEconomicNotFound) as record_error:
        pp.load_economic_evidence(
            store, generation_id=view["generation_id"],
            manifest_digest=view["manifest_sha256"], record_digest="0" * 64,
            slug=view["slug"], fact_id=fact["fact_id"],
        )
    assert record_error.value.reason == "unknown_record"

    pp.publish_private_publication(
        store, pp.prepare_private_publication(stage_economic_case(tmp_path, "corrected", name="corrected"))
    )
    retained = pp.load_economic_evidence(
        store, generation_id=view["generation_id"],
        manifest_digest=view["manifest_sha256"], record_digest=view["record_sha256"],
        slug=view["slug"], fact_id=fact["fact_id"],
    )
    assert retained["generation_id"] == view["generation_id"]
    pp.publish_private_publication(
        store,
        pp.prepare_private_publication(
            stage_economic_case(tmp_path, "empty_native", name="retired"),
            retire_slots=("cik:0000080424",),
        ),
    )
    with pytest.raises(pp.EarningsEconomicUnavailable) as retired_error:
        pp.load_economic_evidence(
            store, generation_id=view["generation_id"],
            manifest_digest=view["manifest_sha256"], record_digest=view["record_sha256"],
            slug=view["slug"], fact_id=fact["fact_id"],
        )
    assert retired_error.value.reason == "evidence_retired"


def test_corrupt_immutable_source_object_is_fail_closed(tmp_path):
    manifest_key = None
    store, baseline = published_v1_case(tmp_path)
    prepared = pp.prepare_private_publication(stage_economic_case(tmp_path, "valid"))
    pp.publish_private_publication(store, prepared)
    manifest = pp.load_private_manifest(store)
    slug = manifest["native"]["economic_slots"]["cik:0000080424"]["slug"]
    digest = next(iter(manifest["native"]["source_bodies"]))
    source_key = manifest["native"]["source_bodies"][digest]["text"]["object_key"]
    path = store.root / Path(source_key)
    original = path.read_bytes()
    pointer = store.get_bytes(pp.POINTER_KEY)
    corrupt = bytes([original[0] ^ 1]) + original[1:]

    def assert_fail_closed(error):
        assert isinstance(error, pp.EarningsPrivatePublicationError)
        assert str(error) in {
            "immutable private earnings object differs",
            "immutable private earnings object collision",
        }
        assert path.read_bytes() == corrupt
        assert store.get_bytes(pp.POINTER_KEY) == pointer
        assert source_key not in store.put_calls
        assert pp.POINTER_KEY not in store.put_calls
        assert pp.POINTER_KEY not in store.conditional_calls

    store.put_calls.clear()
    store.conditional_calls.clear()
    path.write_bytes(corrupt)
    with pytest.raises(pp.EarningsPrivatePublicationError) as same_error:
        pp.publish_private_publication(store, prepared)
    assert_fail_closed(same_error.value)

    newer = pp.prepare_private_publication(stage_economic_case(tmp_path, "corrected", name="corrected"))
    store.put_calls.clear()
    store.conditional_calls.clear()
    with pytest.raises(pp.EarningsPrivatePublicationError) as newer_error:
        pp.publish_private_publication(store, newer)
    assert_fail_closed(newer_error.value)
    path.write_bytes(original)

    pp.publish_private_publication(store, prepared)
    pp.publish_private_publication(store, newer)


def test_manifest_version_reader_matrix(tmp_path):
    store, baseline = published_v1_case(tmp_path)
    prepared = pp.prepare_private_publication(stage_economic_case(tmp_path, "valid"))
    pp.publish_private_publication(store, prepared)
    baseline_manifest = pp.load_private_manifest_version(
        store,
        generation_id=baseline["generation_id"],
        expected_digest=baseline["manifest_sha256"],
    )
    current_manifest = pp.load_private_manifest_version(
        store,
        generation_id=prepared.generation_id,
        expected_digest=sha256(prepared.manifest_bytes).hexdigest(),
    )
    assert baseline_manifest == pp.validate_private_manifest(json.loads(store.get_bytes(baseline["manifest_key"])))
    assert current_manifest == dict(prepared.manifest)

    class StringValue(str):
        pass

    malformed_ids = (
        StringValue(baseline["generation_id"]),
        baseline["generation_id"].upper(),
        baseline["generation_id"] + "\n",
        baseline["generation_id"][:-1],
    )
    malformed_digests = (
        StringValue(baseline["manifest_sha256"]),
        baseline["manifest_sha256"].upper(),
        baseline["manifest_sha256"] + "\n",
        baseline["manifest_sha256"][:-1],
        "0" * 63,
    )
    for generation_id in malformed_ids:
        with pytest.raises(pp.EarningsEconomicNotFound) as error:
            pp.load_private_manifest_version(
                store, generation_id=generation_id, expected_digest=baseline["manifest_sha256"]
            )
        assert error.value.reason == "unknown_generation"
    for expected_digest in malformed_digests:
        with pytest.raises(pp.EarningsEconomicNotFound) as error:
            pp.load_private_manifest_version(
                store, generation_id=baseline["generation_id"], expected_digest=expected_digest
            )
        assert error.value.reason == "unknown_generation"


def test_cross_generation_manifest_bytes_are_refused(tmp_path):
    store, baseline = published_v1_case(tmp_path)
    prepared = pp.prepare_private_publication(stage_economic_case(tmp_path, "valid"))
    pp.publish_private_publication(store, prepared)
    path = store.root / Path(f"{pp.PRIVATE_PREFIX}/manifests/{prepared.generation_id}.json")
    original = path.read_bytes()

    invalid = b'{"schema":"unsupported"}\n'
    path.write_bytes(invalid)
    with pytest.raises(pp.EarningsPrivatePublicationError) as invalid_error:
        pp.load_private_manifest_version(
            store,
            generation_id=prepared.generation_id,
            expected_digest=sha256(invalid).hexdigest(),
        )
    assert not isinstance(invalid_error.value, pp.EarningsEconomicNotFound)

    other = canonical_json_bytes(dict(baseline))
    path.write_bytes(other)
    with pytest.raises(pp.EarningsPrivatePublicationError) as cross_error:
        pp.load_private_manifest_version(
            store,
            generation_id=prepared.generation_id,
            expected_digest=sha256(other).hexdigest(),
        )
    assert not isinstance(cross_error.value, pp.EarningsEconomicNotFound)
    path.write_bytes(original)



def test_reader_rights_are_checked(tmp_path, monkeypatch, economic_publish):
    store, _prepared, _baseline, _patch = economic_publish
    current = pp.load_private_manifest(store)
    view = pp.load_current_economic_view(store, "PG", manifest=current)
    fact = next(item for item in view["interpretation"]["observations"] if item.get("source_excerpt"))
    monkeypatch.setattr(pp, "NATIVE_RIGHTS_REGISTRY_PATH", rights_registry(tmp_path / "refused", refusing=True))
    with pytest.raises(pp.EarningsEconomicUnavailable) as view_error:
        pp.load_current_economic_view(store, "PG", manifest=current)
    assert view_error.value.reason == "rights_refused"
    with pytest.raises(pp.EarningsEconomicUnavailable) as evidence_error:
        pp.load_economic_evidence(store, generation_id=view["generation_id"], manifest_digest=view["manifest_sha256"], record_digest=view["record_sha256"], slug=view["slug"], fact_id=fact["fact_id"])
    assert evidence_error.value.reason == "rights_refused"


def test_predecessor_reader_deletion_twin(tmp_path):
    empty = ConditionalCountingStore(tmp_path / "empty")
    assert pp.load_private_predecessor(empty) is None
    store, baseline = published_v1_case(tmp_path)
    predecessor = pp.load_private_predecessor(store)
    assert predecessor == {key: baseline[key] for key in predecessor}
    manifest_path = store.root / Path(baseline["manifest_key"])
    original_manifest = manifest_path.read_bytes()
    manifest_path.unlink()
    with pytest.raises(pp.EarningsPrivatePublishConflict) as unreadable:
        pp.load_private_predecessor(store)
    assert unreadable.value.reason == "installed_unreadable"
    manifest_path.write_bytes(original_manifest)
    assert pp.load_private_predecessor(store) == predecessor


def test_mixed_v2_generation_publishes_and_reads(tmp_path):
    store, baseline = published_v1_case(tmp_path)
    stage = stage_economic_case(tmp_path, "valid")
    prepared = pp.prepare_private_publication(stage)
    assert prepared.manifest["previous_manifest"] == {
        key: baseline[key] for key in pp.load_private_predecessor(store)
    }
    pp.publish_private_publication(store, prepared)
    current = pp.load_private_manifest(store)
    assert current == dict(prepared.manifest)
    assert current["schema"] == pp.MANIFEST_SCHEMA_V2
    assert set(current) == {
        "schema", "generation_id", "published_at", "source", "record_count", "ticker_count",
        "records", "context", "native", "native_source_cutoff", "previous_manifest",
    }
    record_slugs = tuple(current["records"])
    wire_slug = next(slug for slug in record_slugs if slug != "pg-synthetic-economic-dossier")
    baseline_body = store.get_bytes(baseline["manifest_key"])
    baseline_manifest = pp.validate_v1_manifest(json.loads(baseline_body))
    baseline_record = pp.load_private_record(store, wire_slug, manifest=baseline_manifest)
    assert pp.load_private_record(store, wire_slug) == baseline_record

def test_manifest_wrong_digest_is_unknown_generation(tmp_path):
    store, baseline = published_v1_case(tmp_path)
    assert pp.load_private_manifest_version(
        store,
        generation_id=baseline["generation_id"],
        expected_digest=baseline["manifest_sha256"],
    ) == pp.validate_v1_manifest(json.loads(store.get_bytes(baseline["manifest_key"])))
    with pytest.raises(pp.EarningsEconomicNotFound) as error:
        pp.load_private_manifest_version(
            store,
            generation_id=baseline["generation_id"],
            expected_digest="0" * 64,
        )
    assert error.value.reason == "unknown_generation"


def test_stale_interpretation_identity_is_checked(tmp_path, economic_publish):
    store, _prepared, _baseline, _patch = economic_publish
    manifest = pp.load_private_manifest(store)
    slug = manifest["native"]["economic_slots"]["cik:0000080424"]["slug"]
    rebuilt = json.loads(json.dumps(manifest))
    rebuilt["native"]["selections"][slug]["interpretation_id"] = "econ_" + ("a" * 64)
    rebuilt = reseal_manifest(rebuilt, pp)
    with pytest.raises(pp.EarningsPrivateClosureError) as error:
        pp.load_economic_closure(store, manifest=rebuilt, slug=slug, interpretation="stale_ok")
    assert error.value.reason == "interpretation_mismatch"

    control = pp.load_economic_closure(store, manifest=manifest, slug=slug, interpretation="stale_ok")
    assert control["interpretation_state"] == "current"


def test_surface_validators_refuse_exact_types_without_leaking_values():
    generation_id = "earnpriv_" + "1" * 32
    digest = "a" * 64

    class StringValue(str):
        pass

    assert pp.validate_generation_id(generation_id) == generation_id
    assert pp.validate_digest(digest) == digest
    invalid_ids = (
        StringValue(generation_id), generation_id.encode(), None,
        generation_id.upper(), generation_id + "\n", generation_id[:-1],
    )
    invalid_digests = (
        StringValue(digest), digest.encode(), None, digest.upper(),
        digest + "\n", digest[:-1], digest[:63] + "A",
    )
    for value in invalid_ids:
        with pytest.raises(pp.EarningsPrivatePublicationError) as error:
            pp.validate_generation_id(value)
        assert str(error.value) == "invalid earnings generation id"
        assert not (isinstance(value, str) and value in str(error.value))
    for value in invalid_digests:
        with pytest.raises(pp.EarningsPrivatePublicationError) as error:
            pp.validate_digest(value)
        assert str(error.value) == "invalid earnings digest"
        assert not (isinstance(value, str) and value in str(error.value))


def test_empty_and_v1_retirement_cases_are_refused(tmp_path):
    empty = ConditionalCountingStore(tmp_path / "empty")
    retired = pp.prepare_private_publication(stage_economic_case(tmp_path, "valid"), retire_slots=("cik:0000080424",))
    empty.put_calls.clear()
    with pytest.raises(pp.EarningsPrivatePublishConflict) as retired_error:
        pp.publish_private_publication(empty, retired)
    assert retired_error.value.reason == "retirement_invalid"
    assert empty.put_calls == []

    store, _baseline = published_v1_case(tmp_path / "v1")
    _public, v1_path, _slug = _staged_publication(tmp_path / "v1-public")
    v1_retired = pp.prepare_private_publication(v1_path, retire_slots=("cik:0000080424",))
    store.put_calls.clear()
    with pytest.raises(pp.EarningsPrivatePublishConflict) as v1_error:
        pp.publish_private_publication(store, v1_retired)
    assert v1_error.value.reason == "retirement_invalid"
    assert store.put_calls == []


@pytest.mark.parametrize("label", ["dossier-sweep"], indirect=False)
def test_permanent_hostile_object_sweep(tmp_path, label, economic_publish):
    started = time.monotonic()
    store, prepared, _baseline, _patch = economic_publish
    manifest = pp.load_private_manifest(store)
    slug = manifest["native"]["economic_slots"]["cik:0000080424"]["slug"]
    selection = manifest["native"]["selections"][slug]
    receipts = [manifest["records"][slug], manifest["records"][next(iter(manifest["records"]))]]
    for entry in selection["chain"]:
        document = manifest["native"]["documents"][entry["document"]]
        source_digest = json.loads(store.get_bytes(document["object_key"]))["content_sha256"]
        receipts.extend((
            manifest["native"]["workspaces"][entry["workspace"]], document,
            manifest["native"]["source_bodies"][source_digest]["text"],
        ))
    keys = [prepared.manifest_key]
    keys.extend(receipt["object_key"] for receipt in receipts)
    keys = list(dict.fromkeys(keys))
    pointer_path = store.root / Path(pp.POINTER_KEY)
    pointer_bytes = pointer_path.read_bytes()
    untyped = []

    def hostile_states(original):
        states = [
            bytes([original[0] ^ 1]) + original[1:],
            original[: max(1, len(original) // 2)],
            b"",
            b"[]\n",
        ]
        if original and original.lstrip().startswith(b"{"):
            value = json.loads(original)
            for key in list(value):
                states.append(canonical_json_bytes({item: item_value for item, item_value in value.items() if item != key}))
                states.append(canonical_json_bytes({item: [] for item in value}))
        else:
            states.append(original[:-1] + bytes([original[-1] ^ 1]) if original else b"x")
        states.append(b"0" * 64 + original[64:] if len(original) > 64 else original + b"0")
        return states

    for key in keys:
        path = store.root / Path(key)
        original = path.read_bytes()
        refused = False
        for hostile in hostile_states(original):
            path.write_bytes(hostile)
            manifest_digest = sha256(store.get_bytes(prepared.manifest_key) or b"").hexdigest()
            for reader in (
                lambda: pp.load_economic_closure(store, manifest=manifest, slug=slug),
                lambda: pp.load_economic_closure(store, manifest=manifest, slug=slug, interpretation="stale_ok"),
                lambda: pp.load_current_economic_view(store, "PG", manifest=manifest),
                lambda: pp.load_economic_evidence(
                    store,
                    generation_id=manifest["generation_id"],
                    manifest_digest=manifest_digest,
                    record_digest=manifest["records"][slug]["sha256"],
                    slug=slug,
                    fact_id="fact_id",
                ),
                lambda: pp.load_private_record(store, slug),
                lambda: pp.load_private_record(store, "aapl-2026q1-call-record"),
            ):
                try:
                    reader()
                except ValueError:
                    pass
                except Exception as exc:
                    if not isinstance(exc, pp.EarningsPrivatePublicationError):
                        untyped.append((key, type(exc).__name__, str(exc)))
                    refused = True
            assert pointer_path.read_bytes() == pointer_bytes
            path.write_bytes(original)
        assert refused, key
    assert len(untyped) == 0
    print(f"C11 runtime={time.monotonic() - started:.3f}s")


def _rename_one_directory_member(directory, suffix):
    path = next(iter(directory.glob(f"*{suffix}")))
    target = path.with_name(("f" + "0" * 63) + suffix)
    path.rename(target)
    return target

def _replace_one_stage_file_with_link(directory):
    path = next(iter(directory.iterdir()))
    target = path.with_name("outside")
    target.write_bytes(b"x")
    path.unlink()
    path.symlink_to(target)
    return path

def _make_oversized(path):
    path.write_bytes(b"x" * (pp.MAX_NATIVE_WORKSPACE_BYTES + 1))
    return path

def test_catalog_roles_paths_and_limits(native):
    manifest, payloads = native
    digest, source = next(iter(manifest["native"]["source_bodies"].items()))
    source["text"]["object_key"] = pp._object_key("native_document", digest)
    expect_closure("wrong_role", pp.validate_native_closure, reseal_manifest(manifest, pp), payloads)

    source["text"]["object_key"] = "../escape"
    expect_closure("unsafe_path", pp.validate_native_closure, reseal_manifest(manifest, pp), payloads)

    source["text"]["object_key"] = pp._object_key("source_body_text", digest)
    selection = next(iter(manifest["native"]["selections"].values()))
    original_entry = dict(selection["chain"][0])
    selection["chain"] = [dict(original_entry) for _ in range(5)]
    expect_closure("over_limit", pp.validate_native_closure, reseal_manifest(manifest, pp), payloads)

    selection["chain"] = []
    expect_closure("malformed_native_section", pp.validate_native_closure, reseal_manifest(manifest, pp), payloads)

    selection["chain"] = [{"workspace": "0" * 24, "document": "0" * 64}]
    selection["selection"]["facts"] = [
        {"workspace_generation_id": original_entry["workspace"], "event_id": "x", "fact_id": str(index)}
        for index in range(25)
    ]
    expect_closure("over_limit", pp.validate_native_closure, reseal_manifest(manifest, pp), payloads)

def test_duplicate_key_with_different_bound(native):
    manifest, payloads = native
    record_receipt = first_receipt(manifest["records"])
    next(iter(manifest["native"]["workspaces"].values())).update(record_receipt)
    expect_closure("wrong_role", pp.validate_native_closure, reseal_manifest(manifest, pp), payloads)

def _rename_stage_document(stage):
    directory = stage / "native" / "documents"
    path = next(iter(directory.glob("*.json")))
    target = path.with_name("f" + "0" * 63 + ".json")
    path.rename(target)
    manifest_path = stage / "native" / "latest.json"
    stage_manifest = json.loads(manifest_path.read_bytes())
    for selection in stage_manifest["selections"].values():
        for entry in selection["chain"]:
            if entry["document"] == path.stem:
                entry["document"] = target.stem
    manifest_path.write_bytes(canonical_json_bytes(stage_manifest))
    return target

def test_chain_faults(tmp_path):
    reasons = {
        "predecessor_cycle": lambda document: document.update(
            supersedes_document_id=document["document_id"]
        ),
        "broken_chain": lambda document: document.update(supersedes_document_id="0" * 64),
    }
    for reason, edit in reasons.items():
        stage = stage_economic_case(tmp_path / reason, "valid")
        document = _load_only_native_document(stage)
        edit(document)
        _write_native_document(stage, document)
        expect_closure(reason, pp.prepare_private_publication, stage)

def test_two_entry_chain_faults(tmp_path):
    stage = stage_economic_case(tmp_path / "self", "corrected")
    document = _load_native_documents(stage)[-1]
    document["supersedes_document_id"] = document["document_id"]
    _write_native_document(stage, document)
    expect_closure("predecessor_cycle", pp.prepare_private_publication, stage)

    stage = stage_economic_case(tmp_path / "outside", "corrected")
    document = _load_native_documents(stage)[-1]
    document["supersedes_document_id"] = "0" * 64
    _write_native_document(stage, document)
    expect_closure("broken_chain", pp.prepare_private_publication, stage)

    stage = stage_economic_case(tmp_path / "reversed", "corrected")
    latest = _load_native_documents(stage)[-1]
    latest["supersedes_document_id"] = _load_native_documents(stage)[0]["document_id"]
    _write_native_document(stage, latest)
    expect_closure("broken_chain", pp.prepare_private_publication, stage)

    stage = stage_economic_case(tmp_path / "clock", "corrected")
    stage_manifest_path = stage / "native" / "latest.json"
    stage_manifest = json.loads(stage_manifest_path.read_bytes())
    selection = next(iter(stage_manifest["selections"].values()))
    selection["chain"].reverse()
    stage_manifest_path.write_bytes(canonical_json_bytes(stage_manifest))
    expect_closure("broken_chain", pp.prepare_private_publication, stage)

def _load_native_documents(stage):
    directory = stage / "native" / "documents"
    return [json.loads(path.read_bytes()) for path in sorted(directory.glob("*.json"))]

def _load_only_native_document(stage):
    return _load_native_documents(stage)[0]

def _write_native_document(stage, document, index=-1):
    paths = sorted((stage / "native" / "documents").glob("*.json"))
    _write_hash_named_json(stage / "native" / "documents", document, old_path=paths[index])

def _load_native_workspaces(stage):
    directory = stage / "native" / "workspaces"
    return [json.loads(path.read_bytes()) for path in sorted(directory.glob("*.json"))]

def _write_native_workspace(stage, workspace, old_path):
    _write_hash_named_json(stage / "native" / "workspaces", workspace, old_path=old_path, stage=stage)

def _write_hash_named_json(directory, value, old_path=None, stage=None):
    if old_path is None:
        candidates = sorted(directory.glob("*.json"))
        old_path = candidates[-1]
    old_path.unlink()
    body = canonical_json_bytes(value)
    (directory / f"{sha256(body).hexdigest()}.json").write_bytes(body)
    target_stage = stage if stage is not None else directory.parent.parent
    _update_stage_chain_document(old_path.stem, sha256(body).hexdigest(), target_stage)
    return body

def _update_stage_chain_document(old_digest, new_digest, stage, *, workspace=False):
    if old_digest == new_digest:
        return
    manifest_path = stage / "native" / "latest.json"
    stage_manifest = json.loads(manifest_path.read_bytes())
    field = "workspace" if workspace else "document"
    for selection in stage_manifest["selections"].values():
        for entry in selection["chain"]:
            if entry[field] == old_digest:
                entry[field] = new_digest
    manifest_path.write_bytes(canonical_json_bytes(stage_manifest))

def test_source_bindings_and_native_object_faults(tmp_path):
    stage = stage_economic_case(tmp_path, "valid")
    body_path = next(iter((stage / "native" / "source_bodies").glob("*.txt")))
    original = body_path.read_bytes()
    replacement = original[:-1] + b"x"
    _rebind_source_body(stage, body_path, original, replacement)
    expect_closure("mismatched_source", pp.prepare_private_publication, stage)

    stage = stage_economic_case(tmp_path / "binary", "valid")
    body_path = next(iter((stage / "native" / "source_bodies").glob("*.txt")))
    replacement = original[:-1] + b"\xff"
    _rebind_source_body(stage, body_path, original, replacement)
    expect_closure("mismatched_source", pp.prepare_private_publication, stage)

    manifest, payloads = _prepared(tmp_path / "receipt")
    digest, source = next(iter(manifest["native"]["source_bodies"].items()))
    receipt = source["received"]
    for field, value in (("sha256", "0" * 64), ("length", receipt["length"] + 1), ("declared_encoding", "latin-1")):
        broken = json.loads(json.dumps(source))
        broken["received"][field] = value
        broken_manifest = json.loads(json.dumps(manifest))
        broken_manifest["native"]["source_bodies"][digest] = broken
        expect_closure("mismatched_source", pp.validate_native_closure, reseal_manifest(broken_manifest, pp), payloads)

    slug = manifest["native"]["economic_slots"]["cik:0000080424"]["slug"]
    record = json.loads(payloads[manifest["records"][slug]["object_key"]])
    record["economic_interpretation"]["event_id"] = "another event"
    _validate_rebuilt_record(tmp_path / "event", manifest, payloads, record, "interpretation_mismatch")

    for field, value, reason in (
        ("holds_bytes", True, "malformed_native_section"),
        ("rights_profile", _public_rights_profile(), "malformed_native_section"),
    ):
        broken = json.loads(json.dumps(_prepared_document(manifest, payloads)))
        broken[field] = value
        _validate_rebuilt_document(tmp_path / field, manifest, payloads, broken, reason)

    document = _prepared_document(manifest, payloads)
    document["supersedes_document_id"] = document["document_id"]
    _validate_rebuilt_document(tmp_path / "cycle", manifest, payloads, document, "predecessor_cycle")

def _prepared(path):
    return json.loads(pp.prepare_private_publication(stage_economic_case(path, "valid")).manifest_bytes), dict(
        pp.prepare_private_publication(stage_economic_case(path, "valid")).payloads
    )

def _prepared_document(manifest, payloads):
    document_key = next(iter(manifest["native"]["documents"].values()))["object_key"]
    return json.loads(payloads[document_key])

def _public_rights_profile():
    return pp.pg_profile.RIGHTS_PROFILE

def _validate_rebuilt_record(path, manifest, payloads, record, reason):
    rebuilt, objects = _rebuild_record(path, manifest, payloads, record)
    expect_closure(reason, pp.validate_native_closure, rebuilt, objects)

def _validate_rebuilt_document(path, manifest, payloads, document, reason):
    rebuilt, objects = _rebuild_document(path, manifest, payloads, document)
    expect_closure(reason, pp.validate_native_closure, rebuilt, objects)

def _rebuild_record(path, manifest, payloads, record):
    rebuilt = json.loads(json.dumps(manifest))
    objects = dict(payloads)
    slug = manifest["native"]["economic_slots"]["cik:0000080424"]["slug"]
    old_key = manifest["records"][slug]["object_key"]
    body = canonical_json_bytes(record)
    digest = sha256(body).hexdigest()
    key = object_key(digest)
    objects.pop(old_key)
    objects[key] = body
    rebuilt["records"][slug] = {"object_key": key, "sha256": digest, "bytes": len(body)}
    return reseal_manifest(rebuilt, pp), objects

def _rebuild_document(path, manifest, payloads, document):
    rebuilt = json.loads(json.dumps(manifest))
    objects = dict(payloads)
    old_id, old_receipt = next(iter(manifest["native"]["documents"].items()))
    old_key = old_receipt["object_key"]
    body = canonical_json_bytes(document)
    digest = sha256(body).hexdigest()
    key = object_key(digest)
    objects.pop(old_key)
    objects[key] = body
    rebuilt["native"]["documents"].pop(old_id)
    rebuilt["native"]["documents"][digest] = {"object_key": key, "sha256": digest, "bytes": len(body)}
    slug = next(iter(rebuilt["native"]["selections"]))
    rebuilt["native"]["selections"][slug]["chain"][0]["document"] = digest
    return reseal_manifest(rebuilt, pp), objects

def _rebind_source_body(stage, body_path, original, replacement):
    new_digest = sha256(replacement).hexdigest()
    target = body_path.with_name(f"{new_digest}.txt")
    body_path.unlink()
    target.write_bytes(replacement)
    manifest_path = stage / "native" / "latest.json"
    stage_manifest = json.loads(manifest_path.read_bytes())
    receipt = stage_manifest["received"].pop(sha256(original).hexdigest())
    document_path = next((stage / "native" / "documents").glob("*.json"))
    document = json.loads(document_path.read_bytes())
    document["content_sha256"] = new_digest
    document["content_bytes"] = len(replacement)
    document_path.unlink()
    document_body = canonical_json_bytes(document)
    new_document_path = stage / "native" / "documents" / f"{sha256(document_body).hexdigest()}.json"
    new_document_path.write_bytes(document_body)
    receipt.update({"sha256": new_digest, "length": len(replacement)})
    stage_manifest["received"][new_digest] = receipt
    for selection in stage_manifest["selections"].values():
        for entry in selection["chain"]:
            if entry["document"] == document_path.stem:
                entry["document"] = new_document_path.stem
    manifest_path.write_bytes(canonical_json_bytes(stage_manifest))

def test_clocks_issuers_and_interpretations(tmp_path, monkeypatch):
    prepared = pp.prepare_private_publication(stage_economic_case(tmp_path, "valid"))
    manifest = json.loads(prepared.manifest_bytes)
    payloads = dict(prepared.payloads)

    for edits, reason in (
        (lambda m: m.update(native_source_cutoff="2026-07-29T17:00:00Z"), "future_source_clock"),
        (lambda m: next(iter(m["native"]["selections"].values()))["selection"]["currentness"].update(
            source_clock="2026-08-01T00:00:00Z"
        ), "future_source_clock"),
    ):
        broken = json.loads(json.dumps(manifest))
        edits(broken)
        expect_closure(reason, pp.validate_native_closure, reseal_manifest(broken, pp), payloads)

    workspace_key = next(iter(manifest["native"]["workspaces"].values()))["object_key"]
    stored_workspace = json.loads(payloads[workspace_key])
    wrong_id_workspace = json.loads(json.dumps(stored_workspace))
    wrong_id_workspace["generation_id"] = "f" * 24
    _validate_rebuilt_workspace_only(
        tmp_path / "wrong-id", manifest, payloads, wrong_id_workspace, "digest_mismatch"
    )
    workspace = stored_workspace
    workspace["lifecycle"]["source_available_at"] = "2026-07-29T18:00:00Z"
    document = _prepared_document(manifest, payloads)
    document["available_at"] = "2026-07-29T18:00:00Z"
    workspace["generation_id"] = pp.event_workspace.preview_generation_identity(
        {workspace["event_id"]: workspace}, workspace["generated_at"], previous_generation_id=None
    )
    _validate_rebuilt_workspace_and_document(
        tmp_path / "clock", manifest, payloads, workspace, document, "future_source_clock"
    )

    selection = next(iter(manifest["native"]["selections"].values()))
    selection["company_id"] = "cik:not-admitted"
    expect_closure("cross_issuer", pp.validate_native_closure, reseal_manifest(manifest, pp), payloads)

    class Registry:
        @staticmethod
        def get(company_id):
            return object() if company_id == "cik:synthetic-other" else None

    monkeypatch.setattr(pp.pg_profile, "pg_private_registry", lambda: Registry)
    manifest = json.loads(prepared.manifest_bytes)
    selection = next(iter(manifest["native"]["selections"].values()))
    old_company = next(iter(manifest["native"]["economic_slots"]))
    selection["company_id"] = "cik:synthetic-other"
    manifest["native"]["economic_slots"]["cik:synthetic-other"] = manifest["native"]["economic_slots"].pop(old_company)
    expect_closure("cross_issuer", pp.validate_native_closure, reseal_manifest(manifest, pp), payloads)

def _validate_rebuilt_workspace_only(path, manifest, payloads, workspace, reason):
    rebuilt = json.loads(json.dumps(manifest))
    objects = dict(payloads)
    old_id, old_receipt = next(iter(manifest["native"]["workspaces"].items()))
    body = canonical_json_bytes(workspace)
    digest = sha256(body).hexdigest()
    key = object_key(digest)
    objects.pop(old_receipt["object_key"])
    objects[key] = body
    rebuilt["native"]["workspaces"].pop(old_id)
    rebuilt["native"]["workspaces"][workspace["generation_id"]] = {
        "object_key": key, "sha256": digest, "bytes": len(body)
    }
    slug = next(iter(rebuilt["native"]["selections"]))
    rebuilt["native"]["selections"][slug]["chain"][0]["workspace"] = workspace["generation_id"]
    expect_closure(reason, pp.validate_native_closure, reseal_manifest(rebuilt, pp), objects)

def _validate_rebuilt_workspace_and_document(path, manifest, payloads, workspace, document, reason):
    rebuilt = json.loads(json.dumps(manifest))
    objects = dict(payloads)
    old_id, old_receipt = next(iter(manifest["native"]["workspaces"].items()))
    body = canonical_json_bytes(workspace)
    old_key = old_receipt["object_key"]
    digest = sha256(body).hexdigest()
    key = object_key(digest)
    objects.pop(old_key)
    objects[key] = body
    rebuilt["native"]["workspaces"].pop(old_id)
    rebuilt["native"]["workspaces"][workspace["generation_id"]] = {
        "object_key": key, "sha256": digest, "bytes": len(body)
    }
    slug = next(iter(rebuilt["native"]["selections"]))
    rebuilt["native"]["selections"][slug]["chain"][0]["workspace"] = workspace["generation_id"]
    old_document_id, old_document_receipt = next(iter(manifest["native"]["documents"].items()))
    document_body = canonical_json_bytes(document)
    document_digest = sha256(document_body).hexdigest()
    document_key = object_key(document_digest)
    objects.pop(old_document_receipt["object_key"])
    objects[document_key] = document_body
    rebuilt["native"]["documents"].pop(old_document_id)
    rebuilt["native"]["documents"][document_digest] = {
        "object_key": document_key, "sha256": document_digest, "bytes": len(document_body)
    }
    rebuilt["native"]["selections"][slug]["chain"][0]["document"] = document_digest
    expect_closure(reason, pp.validate_native_closure, reseal_manifest(rebuilt, pp), objects)

def test_interpretation_replay_faults(tmp_path, monkeypatch):
    prepared = pp.prepare_private_publication(stage_economic_case(tmp_path, "valid"))
    manifest = json.loads(prepared.manifest_bytes)
    payloads = dict(prepared.payloads)
    slug = manifest["native"]["economic_slots"]["cik:0000080424"]["slug"]
    record = json.loads(payloads[manifest["records"][slug]["object_key"]])
    for field, value in (
        ("interpretation_id", "econ_" + "0" * 64),
        ("event_id", "another event"),
    ):
        broken_record = json.loads(json.dumps(record))
        broken_record["economic_interpretation"][field] = value
        _validate_rebuilt_record(tmp_path / field, manifest, payloads, broken_record, "interpretation_mismatch")

    for field, value in (
        ("profile_version", "pg_profile.v2"),
    ):
        broken = json.loads(json.dumps(manifest))
        broken["native"]["selections"][slug][field] = value
        expect_closure("interpretation_unsupported", pp.validate_native_closure, reseal_manifest(broken, pp), payloads)

    broken_record = json.loads(json.dumps(record))
    broken_record["economic_interpretation"]["schema"] = "economic_interpretation/v2"
    _validate_rebuilt_record(tmp_path / "schema", manifest, payloads, broken_record, "interpretation_unsupported")

    broken_record = json.loads(json.dumps(record))
    broken_record["economic_interpretation"]["observations"][0]["value"] = "999"
    rebuilt, objects = _rebuild_record(tmp_path / "skip", manifest, payloads, broken_record)
    assert json.loads(objects[rebuilt["records"][slug]["object_key"]]) == broken_record
    expect_closure("interpretation_mismatch", pp.validate_native_closure, rebuilt, objects)
    result = pp.validate_native_closure(rebuilt, objects, interpretations=False)
    assert result[slug]["chain"]
    assert result[slug]["interpretation"] == {
        key: broken_record["economic_interpretation"][key]
        for key in pp.economic_interpretation.TOP_LEVEL_KEYS
    }

    monkeypatch.setattr(
        pp.economic_interpretation,
        "validate_economic_interpretation",
        lambda *args, **kwargs: None,
    )
    _validate_rebuilt_record(
        tmp_path / "validator-seam", manifest, payloads, broken_record, "interpretation_mismatch"
    )

    original_build = pp.economic_interpretation.build_economic_interpretation

    def changed_code(*args, **kwargs):
        kwargs["code_revision"] = kwargs["code_revision"] + 1
        return original_build(*args, **kwargs)

    monkeypatch.setattr(pp.economic_interpretation, "build_economic_interpretation", changed_code)
    expect_closure("interpretation_mismatch", pp.validate_native_closure, manifest, payloads)

def test_native_stage_unexpected_directory(tmp_path):
    stage = stage_economic_case(tmp_path, "valid")
    (stage / "native" / "surprise").mkdir()
    expect_closure("unexpected_artifact", pp.prepare_private_publication, stage)

def test_pairing_and_record_faults(tmp_path):
    prepared = pp.prepare_private_publication(stage_economic_case(tmp_path, "valid"))
    manifest = json.loads(prepared.manifest_bytes)
    payloads = dict(prepared.payloads)
    slug = manifest["native"]["economic_slots"]["cik:0000080424"]["slug"]
    record = json.loads(payloads[manifest["records"][slug]["object_key"]])

    for field, value in (
        ("public_facts", 1),
        ("locked_facts", 19),
        ("facts_html", "<p>text</p>"),
        ("receipt_rows_html", "<tr></tr>"),
    ):
        broken = json.loads(json.dumps(record))
        broken[field] = value
        _validate_rebuilt_record(tmp_path / field, manifest, payloads, broken, "malformed_native_section")

    broken = json.loads(json.dumps(record))
    broken["economic_interpretation"] = {"state": "unavailable", "reason": "unknown"}
    _validate_rebuilt_record(tmp_path / "reason", manifest, payloads, broken, "malformed_native_section")

    broken = json.loads(json.dumps(record))
    broken["extra"] = 1
    _validate_rebuilt_record(tmp_path / "extra", manifest, payloads, broken, "malformed_native_section")

    broken = json.loads(json.dumps(record))
    broken["page"] = "unknown page"
    _validate_rebuilt_record(tmp_path / "page", manifest, payloads, broken, "malformed_native_section")

    for native_present, selection_present in ((False, True), (True, False)):
        broken_manifest = json.loads(json.dumps(manifest))
        broken_record = json.loads(json.dumps(record))
        if not native_present:
            broken_record["economic_interpretation"] = {"state": "unavailable", "reason": "no_native_selection"}
        if not selection_present:
            broken_manifest["native"]["selections"].pop(slug)
        rebuilt, objects = _rebuild_record(tmp_path / f"pair-{native_present}", broken_manifest, payloads, broken_record)
        expect_closure("malformed_native_section", pp.validate_native_closure, rebuilt, objects)

    broken = json.loads(json.dumps(manifest))
    second_slug = "synthetic-second-selection"
    broken["native"]["selections"][second_slug] = json.loads(json.dumps(broken["native"]["selections"][slug]))
    broken["records"][second_slug] = json.loads(json.dumps(broken["records"][slug]))
    broken["record_count"] = len(broken["records"])
    expect_closure("wrong_role", pp.validate_native_closure, reseal_manifest(broken, pp), payloads)

    broken = json.loads(json.dumps(manifest))
    broken["native"]["economic_slots"]["cik:0000080424"]["event_id"] = "another event"
    expect_closure("malformed_native_section", pp.validate_native_closure, reseal_manifest(broken, pp), payloads)

    broken_record = json.loads(json.dumps(record))
    broken_record["economic_interpretation"]["observations"] = [dict(item) for item in broken_record["economic_interpretation"]["observations"]] * 2
    broken_record["locked_facts"] = len(broken_record["economic_interpretation"]["observations"])
    _validate_rebuilt_record(tmp_path / "observations", manifest, payloads, broken_record, "over_limit")

def test_schemas_and_scope(tmp_path):
    prepared = pp.prepare_private_publication(stage_economic_case(tmp_path, "valid"))
    manifest = json.loads(prepared.manifest_bytes)
    payloads = dict(prepared.payloads)

    record = json.loads(next(iter(payloads.values())))
    record["schema"] = "earnings.tier_payload/v3"
    error = expect_closure("unsupported_schema", pp.validate_private_record, record)
    assert str(error) == "unsupported private record schema"

    broken = dict(manifest)
    broken["schema"] = "earnings.private_manifest/v3"
    expect_closure("unsupported_schema", pp.validate_private_manifest, broken)

    stage = stage_economic_case(tmp_path / "stage-schema", "valid")
    stage_manifest = json.loads((stage / "native" / "latest.json").read_bytes())
    stage_manifest["schema"] = "earnings.private_native_stage/v2"
    (stage / "native" / "latest.json").write_bytes(canonical_json_bytes(stage_manifest))
    expect_closure("unsupported_schema", pp.prepare_private_publication, stage)

    slug = manifest["native"]["economic_slots"]["cik:0000080424"]["slug"]
    record_key = manifest["records"][slug]["object_key"]
    native_keys = {
        next(iter(manifest["native"]["workspaces"].values()))["object_key"],
        next(iter(manifest["native"]["documents"].values()))["object_key"],
        next(iter(manifest["native"]["source_bodies"].values()))["text"]["object_key"],
    }
    scoped = {key: payloads[key] for key in native_keys | {record_key}}
    assert pp.validate_native_closure(manifest, scoped, slugs=(slug,))[slug]["chain"]
    without_document = {key: value for key, value in scoped.items() if key != next(iter(native_keys))}
    expect_closure("missing_artifact", pp.validate_native_closure, manifest, without_document, slugs=(slug,))
    expect_closure("missing_artifact", pp.validate_native_closure, manifest, scoped, slugs=("unknown-slug",))

@pytest.mark.parametrize("rights_class", ["derived_display_ok", "direct_display_ok", "internal_only", "unresolved"])
def test_rights_seam(tmp_path, monkeypatch, rights_class):
    registry = tmp_path / f"{rights_class}.yml"
    registry.write_text(
        "families:\n"
        "  sec_edgar:\n"
        f"    rights_class: {rights_class}\n"
        "    auth_class: keyless_public\n"
    )
    monkeypatch.setattr(pp, "NATIVE_RIGHTS_REGISTRY_PATH", registry)
    if rights_class.endswith("_ok"):
        pp.assert_native_rights()
    else:
        expect_closure("rights_refused", pp.assert_native_rights)

def test_rights_seam_failure_modes(tmp_path, monkeypatch):
    for name, body in (
        ("absent-family", "families: {}\n"),
        ("malformed", "{not yaml: [\n"),
    ):
        monkeypatch.setattr(pp, "NATIVE_RIGHTS_REGISTRY_PATH", tmp_path / f"{name}.yml")
        (tmp_path / f"{name}.yml").write_text(body)
        expect_closure("rights_refused", pp.assert_native_rights)
    missing = tmp_path / "missing.yml"
    monkeypatch.setattr(pp, "NATIVE_RIGHTS_REGISTRY_PATH", missing)
    expect_closure("rights_refused", pp.assert_native_rights)
