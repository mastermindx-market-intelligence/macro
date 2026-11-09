"""Native capture guards; synthetic owner files never establish natural eligibility."""
from __future__ import annotations

import copy
import dataclasses
import json

import pytest
import yaml

from engine.neuralweb import theme_state_adapter as adapter
from engine.theme_graph import identity, rights, theme_state
from engine.theme_graph.theme_state_owner_readers import StateQualificationReader
from tests import test_theme_state_owner_adapter as native
from tests.test_theme_state_owner_adapter import world  # noqa: F401

KNOWN = "2026-10-04T12:00:00Z"


@pytest.fixture
def mapped_world(world):
    root, crosswalk = world
    crosswalk["themes"][0]["basket_ids"] = ["power_grid"]
    (root / "config/theme_crosswalk.yml").write_text(yaml.safe_dump(crosswalk, sort_keys=False))
    return root, identity.theme_node_id(crosswalk["themes"][0]["id"])


def capture(root, *, reader=None, known_at=KNOWN):
    return adapter.capture_owner_bundle(root, effective_at=native.EFFECTIVE, known_at=known_at,
        owner_readers=reader if reader is not None else StateQualificationReader(root))


def read(bundle, node):
    state = adapter.compose_state_only_from_owner_bundle(bundle, generated_at=native.EMITTED)
    theme_state.validate_state(state)
    return state, next(row for row in state["subjects"] if row["node_id"] == node)


def test_native_local_receipts_are_descriptive_and_never_seal_current_eligibility(mapped_world):
    root, _ = mapped_world
    bundle = capture(root); snap = bundle.snapshot()
    state, subject = read(bundle, native.LOCAL)
    assert subject["availability"] == "AVAILABLE" and subject["reason_codes"] == []
    owners = subject["owner_receipts"]
    assert owners["membership"]["payload"]["members"] == [{"ticker": "HUBB",
        "security_id": "fixture-security:HUBB", "issuer_id": "fixture-issuer:HUBB"}]
    assert owners["membership"]["known_at"] == native.EFFECTIVE
    assert owners["identity"]["known_at"] == "2026-10-02T09:00:00Z"
    assert owners["rights"]["payload"]["purpose"] == "research_internal"
    assert subject["eligibility"] == {"status": "NOT_QUALIFIED", "policy_revision": None,
                                        "reason_codes": ["D2E_UNSEALED"]}
    assert owners["eligibility"] is None
    for role in ("ontology", "identity", "membership", "rights"):
        assert owners[role]["graph_generation_id"] == snap["graph_capture_id"]
        assert owners[role]["subject_id"] == native.LOCAL
        assert owners[role]["query"] == snap["query"]
    assert all(value is False for key, value in state["authority"].items() if key.startswith("may_"))
    assert set(snap["subjects"]) == {row["node_id"] for row in state["subjects"]}
    assert snap["subjects"][native.LOCAL]["qualification"]["source_receipts"] == {}
    assert theme_state.read_theme_state(state, native.LOCAL, effective_at=state["effective_at"],
        known_at=native.EMITTED, expected_generation_id=state["generation_id"])["status"] == "DESCRIPTIVE"


@pytest.mark.parametrize("baskets", [["power_grid"], [], ["power_grid", "housing"],
                                     ["power_grid", "power_grid"], None, "power_grid", [None], [""]])
def test_price_mapping_never_becomes_canonical_semantic_membership(mapped_world, baskets):
    root, node = mapped_world
    path = root / "config/theme_crosswalk.yml"; cfg = yaml.safe_load(path.read_text())
    cfg["themes"][0]["basket_ids"] = baskets
    cfg["themes"][0]["note"] = "Price proxy; no semantic member admission."
    path.write_text(yaml.safe_dump(cfg))
    bundle = capture(root)
    assert bundle.snapshot()["subjects"][node]["basket"] is None
    _, subject = read(bundle, node)
    assert subject["owner_receipts"]["membership"] is None
    assert subject["owner_receipts"]["identity"] is None
    assert subject["owner_receipts"]["rights"] is None
    assert subject["availability"] == "UNAVAILABLE"
    assert subject["aggregation"]["reason_codes"] == ["CANONICAL_AGGREGATION_UNSUPPLIED"]


def test_native_same_day_membership_and_registry_dates_remain_unproven(mapped_world):
    root, _ = mapped_world
    path = root / "config/theme_sources.yml"
    cfg = yaml.safe_load(path.read_text()); cfg["updated"] = native.EFFECTIVE
    path.write_text(yaml.safe_dump(cfg))
    _, subject = read(capture(root, known_at=native.KNOWN), native.LOCAL)
    assert subject["owner_receipts"]["membership"]["known_at"] == native.EFFECTIVE
    assert subject["owner_receipts"]["rights"]["known_at"] == native.EFFECTIVE
    assert subject["availability"] == "UNAVAILABLE"
    assert "KNOWLEDGE_TIME_UNPROVEN" in subject["reason_codes"]
    assert subject["eligibility"]["status"] == "NOT_QUALIFIED"


def test_vendor_structure_never_borrows_house_display_grant(mapped_world):
    root, _ = mapped_world; path = root / "config/theme_sources.yml"; before = path.read_bytes()
    bundle = capture(root)
    for node, family in [(native.LOCAL, "finviz_themes"), ("ltheme:ths:900001", "ths_concepts")]:
        native_rights = bundle.snapshot()["subjects"][node]["native_reads"]["rights"]
        assert native_rights["family"] == family and native_rights["licensing"] == [True, False, False]
        with pytest.raises(rights.RightsRefusal):
            rights.assert_public_emission_allowed(family, path=path)
        assert read(bundle, node)[1]["eligibility"]["status"] == "NOT_QUALIFIED"
    assert path.read_bytes() == before


def test_reader_refuses_changed_identity_and_registry_reads(mapped_world, monkeypatch):
    root, _ = mapped_world; bundle = capture(root); snap = bundle.snapshot()
    args = dict(node_id=native.LOCAL, query=snap["query"], graph_capture_id=snap["graph_capture_id"],
        native_reads=snap["subjects"][native.LOCAL]["native_reads"],
        source_sha256={k: v["sha256"] for k,v in snap["sources"].items()})
    reader = StateQualificationReader(root)
    original = adapter.identity_resolution.resolve_graph_node_identity
    def changed(*a, **kw):
        value = copy.deepcopy(original(*a, **kw)); value["security_id"] = "changed-security"
        return value
    monkeypatch.setattr(adapter.identity_resolution, "resolve_graph_node_identity", changed)
    assert "identity" not in reader.read_state_qualification(**args)["owner_receipts"]
    path = root / "config/theme_sources.yml"; path.write_text(path.read_text()+"\n# changed source\n")
    assert "rights" not in reader.read_state_qualification(**args)["owner_receipts"]


def test_rehashed_bundle_cannot_substitute_a_canonical_population(mapped_world):
    root, node = mapped_world; bundle = capture(root); snap = bundle.snapshot()
    snap["subjects"][node]["basket"] = {"suite": "baskets", "basket_id": "power_grid"}
    text = adapter._json(snap)
    forged = dataclasses.replace(bundle, payload_json=text, bundle_sha256=adapter._sha(text.encode()))
    with pytest.raises(ValueError, match="derived subject scope"):
        read(forged, node)


def test_shadow_writer_retains_unqualified_native_receipts_without_publishing_current(mapped_world):
    from scripts import build_thematic_state
    root, node = mapped_world
    assert build_thematic_state.build(root, mode="GRAPH_SHADOW_STATE", generated_at=native.EMITTED) == 0
    state = json.loads((root / "data/theme_graph/shadow_theme_state.v1.json").read_text())
    theme_state.validate_state(state)
    subjects = {row["node_id"]: row for row in state["subjects"]}
    assert subjects[native.LOCAL]["availability"] == "AVAILABLE"
    assert subjects[node]["owner_receipts"]["membership"] is None
    assert all(row["eligibility"]["status"] == "NOT_QUALIFIED" for row in subjects.values())
    assert state["mode"] == "shadow" and state["authority"]["may_publish"] is False
    assert not (root / "data/neuralweb/theme_state_current.json").exists()
    assert not (root / "data/neuralweb/theme_state.json").exists()
