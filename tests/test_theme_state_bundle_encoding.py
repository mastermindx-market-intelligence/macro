"""Lossless capture encoding; controlled owner fixtures, no native execution."""
import copy
import dataclasses
import json

import pytest

from engine.neuralweb import theme_state_adapter as adapter
from engine.theme_graph import theme_state_production as production
from tests.test_theme_state_production import EFFECTIVE, EMITTED, KNOWN, production_world  # noqa: F401


def bundle_from_payload(payload):
    text = adapter._json(payload)
    return adapter.OwnerBundle(text, adapter._sha(text.encode()))


def test_retained_contract_exception_is_exactly_the_v1_bundle_predecessor():
    old = copy.deepcopy(production._SCHEMA_DOC)
    slot = old['properties']['bundle_ref']['properties']['schema']
    assert slot.pop('enum') == [adapter.BUNDLE_SCHEMA, adapter.COMPACT_BUNDLE_SCHEMA]
    slot['const'] = adapter.BUNDLE_SCHEMA
    raw = (json.dumps(old, indent=2, ensure_ascii=False) + '\n').encode()
    assert adapter._sha(raw) == production._V1_BUNDLE_SCHEMA_SHA256


def test_native_capture_compacts_shared_identity_without_losing_logical_values(production_world):
    bundle = adapter.capture_owner_bundle(production_world, effective_at=EFFECTIVE, known_at=KNOWN)
    wire = json.loads(bundle.payload_json)
    assert wire['schema'] == bundle.wire_schema == adapter.COMPACT_BUNDLE_SCHEMA
    assert len(wire['identity_read_tables']) == 1
    snapshot = bundle.snapshot()
    maps = [row['native_reads']['identity'] for row in snapshot['subjects'].values()]
    assert len(maps) > 1 and all(item is maps[0] for item in maps)
    legacy = bundle_from_payload(snapshot)
    assert legacy.wire_schema == adapter.BUNDLE_SCHEMA
    assert legacy.snapshot() == snapshot
    current = adapter.compose_state_only_from_owner_bundle(bundle, generated_at=EMITTED)
    retained = adapter.compose_state_only_from_owner_bundle(legacy, generated_at=EMITTED)
    assert current['subjects'] == retained['subjects']
    assert current['authority'] == retained['authority']
    assert current['owner_generations']['adapter.owner_bundle'] == bundle.bundle_sha256
    assert retained['owner_generations']['adapter.owner_bundle'] == legacy.bundle_sha256
    for field in ('effective_at', 'known_at', 'generated_at', 'graph_generation_id'):
        assert current[field] == retained[field]
    maps[0].clear()
    assert bundle.snapshot() == legacy.snapshot()  # caller mutation cannot change bundle


def test_assembly_never_reserializes_expanded_owner_payload(production_world, monkeypatch):
    bundle = adapter.capture_owner_bundle(production_world, effective_at=EFFECTIVE, known_at=KNOWN)
    original = adapter._json
    def guarded(value):
        if isinstance(value, dict) and value.get('schema') == adapter.BUNDLE_SCHEMA:
            raise AssertionError('expanded identity maps must not be serialized by assembly')
        return original(value)
    monkeypatch.setattr(adapter, '_json', guarded)
    state = adapter.compose_state_only_from_owner_bundle(bundle, generated_at=EMITTED)
    assert state['owner_generations']['adapter.owner_bundle'] == bundle.bundle_sha256


def test_production_names_actual_wire_schema_and_preserves_retained_v1(production_world):
    bundle = adapter.capture_owner_bundle(production_world, effective_at=EFFECTIVE, known_at=KNOWN)
    current = adapter.compose_production_from_owner_bundle(bundle, generated_at=EMITTED)['state']
    assert current['bundle_ref']['schema'] == adapter.COMPACT_BUNDLE_SCHEMA
    production.validate_state(current)
    legacy = bundle_from_payload(bundle.snapshot())
    retained = adapter.compose_production_from_owner_bundle(legacy, generated_at=EMITTED)['state']
    assert retained['bundle_ref']['schema'] == adapter.BUNDLE_SCHEMA
    assert current['subjects'] == retained['subjects']
    assert current['source_refs'] == retained['source_refs']
    assert current['compatibility'] == retained['compatibility']
    # The exact predecessor contract allowed only v1 wire bundles. Its retained
    # bundles and standalone states remain readable; it cannot certify the new v2 encoding.
    def with_schema(state, digest):
        result = copy.deepcopy(state)
        result['producer_refs']['schema']['sha256'] = digest
        result['state_sha256'] = production.state_digest(result)
        result['generation_id'] = production.GENERATION_PREFIX + result['state_sha256'][:20]
        return result
    production.validate_state(with_schema(retained, production._V1_BUNDLE_SCHEMA_SHA256))
    for state, digest in ((current, production._V1_BUNDLE_SCHEMA_SHA256), (retained, '0' * 64)):
        with pytest.raises(ValueError, match='schema revision'):
            production.validate_state(with_schema(state, digest))


def test_rehashed_compact_bundle_still_refuses_table_tampering(production_world):
    bundle = adapter.capture_owner_bundle(production_world, effective_at=EFFECTIVE, known_at=KNOWN)
    wire = json.loads(bundle.payload_json)
    key = next(iter(wire['identity_read_tables']))
    wire['identity_read_tables'][key]['forged'] = {'value': 'not captured'}
    with pytest.raises(ValueError):
        bundle_from_payload(wire).snapshot()
    with pytest.raises(ValueError, match='digest'):
        dataclasses.replace(bundle, payload_json=bundle.payload_json + ' ').snapshot()


@pytest.mark.parametrize("wire", ["v1", "v2"])
@pytest.mark.parametrize("at_use", [False, True])
def test_current_generation_read_contract_accepts_both_bundle_encodings(production_world, wire, at_use):
    from engine.neuralweb import theme_state_generation as g, theme_state_generation_reader as reader
    from tests.test_theme_state_generation import AcceptedFixture
    from tests.test_theme_state_generation_reader import ReadFixture, USE
    bundle = adapter.capture_owner_bundle(production_world, effective_at=EFFECTIVE, known_at=KNOWN)
    if wire == "v1":
        bundle = bundle_from_payload(bundle.snapshot())
    plan = g.prepare_generation(bundle, root=production_world, generated_at=EMITTED,
        activation_at=EMITTED, entry=g.entry_preflight(production_world, legacy_api=True))
    g.publish_generation(production_world, plan, controlled_verifier=AcceptedFixture())
    read = reader.read_generation_at_use if at_use else reader.read_generation
    validate = reader.validate_read_receipt_at_use if at_use else reader.validate_read_receipt
    receipt = read(production_world, effective_at=EFFECTIVE, known_at=KNOWN,
        purpose="research_internal", use_at=USE, controlled_verifier=ReadFixture())
    assert receipt["status"] == "DESCRIPTIVE", receipt["reason_codes"]
    assert receipt["state"]["bundle_ref"]["schema"] == bundle.wire_schema
    validate(receipt, publication_plan=plan)
    # Wire compatibility does not silently admit a different sealed producer.
    predecessor = copy.deepcopy(plan)
    predecessor["producer_bindings"]["engine/neuralweb/theme_state_adapter.py"] = "0" * 64
    with pytest.raises(Exception, match="GENERATION_PRODUCER_VERSION_MISMATCH"):
        g.validate_generation(predecessor)


def test_state_only_avoids_sidecar_decode_without_losing_state_or_structural_refusals(production_world, monkeypatch):
    bundle = adapter.capture_owner_bundle(production_world, effective_at=EFFECTIVE, known_at=KNOWN)
    expected = adapter.compose_from_owner_bundle(bundle, generated_at=EMITTED)["state"]
    def forbidden(*args, **kwargs):
        raise AssertionError("discarded specialist sidecar must not be decoded")
    monkeypatch.setattr(adapter, "_source_observation", forbidden)
    actual = adapter.compose_state_only_from_owner_bundle(bundle, generated_at=EMITTED)
    assert actual == expected
    for missing in ("source", "membership", "membership_value"):
        payload = json.loads(bundle.payload_json)
        if missing == "source":
            del payload["sources"]["narrative_emergence_cn"]
        else:
            reads = next(iter(payload["subjects"].values()))["native_reads"]
            if missing == "membership":
                del reads["membership"]
            else:
                del reads["membership"]["value"]
        with pytest.raises((KeyError, ValueError)):
            adapter.compose_state_only_from_owner_bundle(bundle_from_payload(payload), generated_at=EMITTED)
