"""Publication-time reads: source capture may predate assembly.

v1 keeps the equal-clock refusal. The new read does not grant rights, restamp
clocks, or accept a caller-selected schema switch.
"""
import copy
import hashlib
import json
from pathlib import Path

import pytest

from engine.neuralweb import theme_state_generation as g
from engine.neuralweb import theme_state_generation_reader as reader
from engine.theme_graph import theme_state_production as production
from tests.test_theme_state_generation import AcceptedFixture, put
from tests.test_theme_state_generation_reader import ReadFixture, files, publication_plan
from tests.test_theme_state_production import EFFECTIVE, LOCAL, CN, production_world

CAPTURE = "2026-10-04T12:00:00Z"
EMISSION = "2026-10-05T12:00:00Z"
ACTIVATION = "2026-10-06T12:00:00Z"
USE = "2026-10-06T13:00:00Z"
CORR_KNOWN = "2026-10-05T12:30:00Z"
CORR_EMITTED = "2026-10-05T13:00:00Z"
CORR_ACTIVATION = "2026-10-06T15:00:00Z"
ROOT = Path(__file__).resolve().parents[1]



def _use_reader():
    from engine.theme_graph import theme_state_use_reader as use_reader
    return use_reader


def publish_predated(root, *, known_at=CAPTURE, generated_at=EMISSION, activation_at=ACTIVATION):
    from engine.neuralweb import theme_state_adapter as adapter
    bundle = adapter.capture_owner_bundle(root, effective_at=EFFECTIVE, known_at=known_at)
    plan = g.prepare_generation(bundle, root=root, generated_at=generated_at,
        activation_at=activation_at, entry=g.entry_preflight(root, legacy_api=True))
    g.publish_generation(root, plan, controlled_verifier=AcceptedFixture())
    state = g.validate_generation(plan)
    assert state["known_at"] == known_at
    assert state["generated_at"] == generated_at
    assert plan["activation_at"] == activation_at
    assert plan["query"] == {"effective_at": EFFECTIVE, "known_at": known_at}
    return plan


def invoke(root, fn, **kw):
    before = files(root)
    args = dict(effective_at=EFFECTIVE, known_at=CAPTURE, purpose="research_internal",
        use_at=USE, controlled_verifier=ReadFixture())
    args.update(kw)
    answer = fn(root, **args)
    assert files(root) == before, "read/refusal changed owner bytes"
    return answer


def call_v1(root, **kw):
    return invoke(root, reader.read_generation, **kw)


def call_v2(root, **kw):
    before = files(root)
    answer = invoke(root, reader.read_generation_at_use, **kw)
    witness = publication_plan(root, answer) if answer["state"] is not None else None
    assert reader.validate_read_receipt_at_use(answer, publication_plan=witness) == answer
    assert files(root) == before, "detached validation changed owner bytes"
    return answer


def assert_powerless(receipt):
    assert receipt["materialization_allowed"] is False
    assert all(value is False for value in receipt["authority_caps"].values())
    if receipt["state"] is not None:
        assert receipt["state"]["materialization_allowed"] is False
        assert all(value is False for value in receipt["state"]["authority_caps"].values())
    subject = receipt.get("subject_read")
    if subject is not None:
        assert all(value is False for value in subject["authority_caps"].values())
        assert set(subject) == {
            "schema", "query", "use_at", "subject_id", "state_generation_id", "state_sha256",
            "state_generated_at", "status", "subject", "reason_codes", "authority_caps"}


def test_v1_refuses_capture_before_emission(production_world):
    publish_predated(production_world)
    before = files(production_world)
    old = call_v1(production_world)
    assert old["schema"] == "neuralweb.theme_state_generation_read.v1"
    assert old["status"] == "UNAVAILABLE"
    assert old["reason_codes"] == ["STATE_NOT_YET_EMITTED"]
    assert old["state"] is None and old["subject_read"] is None
    assert files(production_world) == before


def test_strict_publication_time_order_is_descriptive(production_world):
    plan = publish_predated(production_world)
    assert call_v1(production_world)["reason_codes"] == ["STATE_NOT_YET_EMITTED"]
    out = call_v2(production_world, node_id="theme:grid")
    assert out["schema"] == "neuralweb.theme_state_generation_read.v2"
    assert out["status"] == "DESCRIPTIVE"
    assert out["query"] == {"effective_at": EFFECTIVE, "known_at": CAPTURE}
    assert out["use_at"] == USE
    assert out["publication"]["generation_id"] == plan["generation_id"]
    assert out["publication"]["activation_at"] == ACTIVATION
    assert out["publication"]["activation_kind"] == "INITIAL"
    assert out["state"]["known_at"] == CAPTURE
    assert out["state"]["generated_at"] == EMISSION
    assert out["state_identity"]["generated_at"] == EMISSION
    assert out["state_identity"]["age_seconds_at_use"] == 90000
    assert out["reason_codes"] == ["CONTROLLED_TEST_ONLY", "D2E_NOT_QUALIFIED"]
    assert_powerless(out)
    subject = out["subject_read"]
    assert subject["schema"] == "gmi.theme_state_read/v3"
    assert subject["status"] == "DESCRIPTIVE"
    assert subject["use_at"] == USE
    assert subject["query"] == out["query"]
    assert subject["subject"] == next(row for row in out["state"]["subjects"] if row["node_id"] == "theme:grid")
    assert subject["reason_codes"] == [
        "NATIVE_KNOWABILITY_AND_SOURCE_PURPOSE_QUALIFICATION_REMAIN_PER_LEG", "D2E_NOT_QUALIFIED"]
    assert "publication" not in subject and "activation_at" not in subject


def test_subject_use_boundary_does_not_imply_activation(production_world):
    plan = publish_predated(production_world)
    state = g.validate_generation(plan)
    original = copy.deepcopy(state)
    use_reader = _use_reader()
    held = use_reader.read_subject_at_use(state, node_id="theme:grid", effective_at=EFFECTIVE,
        known_at=CAPTURE, use_at=EMISSION)
    assert held["status"] == "DESCRIPTIVE"
    assert held["state_generated_at"] == EMISSION
    assert state == original
    early = use_reader.read_subject_at_use(state, node_id="theme:grid", effective_at=EFFECTIVE,
        known_at=CAPTURE, use_at="2026-10-05T11:59:59Z")
    assert early["status"] == "UNAVAILABLE" and early["subject"] is None
    assert early["reason_codes"] == ["STATE_NOT_YET_EMITTED"]
    blocked = call_v2(production_world, use_at=EMISSION)
    assert blocked["status"] == "UNAVAILABLE"
    assert blocked["reason_codes"] == ["PUBLICATION_NOT_YET_ACTIVATED"]
    assert blocked["state"] is None and blocked["subject_read"] is None
    old = production.read_subject(state, node_id="theme:grid", effective_at=EFFECTIVE, known_at=CAPTURE)
    assert old["schema"] == "gmi.theme_state_read/v2"
    assert old["status"] == "UNAVAILABLE" and old["reason_codes"] == ["STATE_NOT_YET_EMITTED"]
    assert "use_at" not in old


def test_equal_clock_stays_positive_and_schemas_do_not_cross(production_world):
    from tests.test_theme_state_production import compose, KNOWN
    bundle, _ = compose(production_world)
    plan = g.prepare_generation(bundle, root=production_world, generated_at=KNOWN, activation_at=KNOWN,
        entry=g.entry_preflight(production_world, legacy_api=True))
    g.publish_generation(production_world, plan, controlled_verifier=AcceptedFixture())
    old = invoke(production_world, reader.read_generation, known_at=KNOWN, use_at="2026-10-04T13:00:00Z",
        node_id="theme:grid")
    new = invoke(production_world, reader.read_generation_at_use, known_at=KNOWN, use_at="2026-10-04T13:00:00Z",
        node_id="theme:grid")
    witness = publication_plan(production_world, old)
    assert old["status"] == new["status"] == "DESCRIPTIVE"
    assert old["schema"] == "neuralweb.theme_state_generation_read.v1"
    assert new["schema"] == "neuralweb.theme_state_generation_read.v2"
    assert reader.validate_read_receipt(old, publication_plan=witness) == old
    assert reader.validate_read_receipt_at_use(new, publication_plan=witness) == new
    with pytest.raises(ValueError):
        reader.validate_read_receipt(new, publication_plan=witness)
    with pytest.raises(ValueError):
        reader.validate_read_receipt_at_use(old, publication_plan=witness)
    production.validate_read_receipt(old["subject_read"])
    _use_reader().validate_read_receipt_at_use(new["subject_read"])
    with pytest.raises(ValueError):
        production.validate_read_receipt(new["subject_read"])
    with pytest.raises(ValueError):
        _use_reader().validate_read_receipt_at_use(old["subject_read"])
    exact = invoke(production_world, reader.read_generation, effective_at="2026-10-02", known_at=KNOWN,
        use_at="2026-10-04T13:00:00Z")
    assert exact["reason_codes"] == ["EXACT_CAPTURE_QUERY_REQUIRED"]


def test_v1_entrypoint_rejects_a_version_switch(production_world):
    publish_predated(production_world)
    with pytest.raises(TypeError):
        reader.read_generation(production_world, effective_at=EFFECTIVE, known_at=CAPTURE,
            purpose="research_internal", use_at=USE, controlled_verifier=ReadFixture(),
            schema="neuralweb.theme_state_generation_read.v2")
    assert call_v1(production_world)["reason_codes"] == ["STATE_NOT_YET_EMITTED"]


@pytest.mark.parametrize("known_at,reason", [
    ("2026-10-04T12:00:00+00:00", "EXACT_CAPTURE_QUERY_REQUIRED"),
    ("2026-10-05T12:00:01Z", "EXACT_CAPTURE_QUERY_REQUIRED"),
    ("2026-10-07T00:00:00Z", "QUERY_KNOWLEDGE_AFTER_USE"),
])
def test_v2_query_match_is_string_exact(production_world, known_at, reason):
    publish_predated(production_world)
    out = call_v2(production_world, known_at=known_at)
    assert out["status"] == "UNAVAILABLE" and out["state"] is None
    assert out["reason_codes"] == [reason]
    if known_at.endswith("+00:00"):
        assert call_v1(production_world, known_at=known_at)["reason_codes"] == ["STATE_NOT_YET_EMITTED"]


def test_effective_spelling_and_future_clocks_stay_distinct(production_world):
    publish_predated(production_world)
    spelling = call_v2(production_world, effective_at="2026-10-03T00:00:00Z")
    assert spelling["reason_codes"] == ["EXACT_CAPTURE_QUERY_REQUIRED"]
    future_activation = call_v2(production_world, use_at="2026-10-06T11:59:59Z")
    assert future_activation["status"] == "UNAVAILABLE"
    assert future_activation["reason_codes"] == ["PUBLICATION_NOT_YET_ACTIVATED"]
    assert future_activation["state"] is None
    knowledge = call_v2(production_world, use_at="2026-10-04T11:00:00Z")
    assert knowledge["reason_codes"] == ["QUERY_KNOWLEDGE_AFTER_USE"]
    malformed = call_v2(production_world, use_at="not-a-clock")
    assert malformed["status"] == "INVALID" and malformed["reason_codes"] == ["INVALID_PRECISE_CLOCK"]
    boundary = call_v2(production_world, use_at=ACTIVATION)
    assert boundary["status"] == "DESCRIPTIVE"
    assert boundary["state_identity"]["age_seconds_at_use"] == 86400


def test_correction_and_rollback_keep_source_dates_and_emission_age(production_world):
    first = publish_predated(production_world)
    from engine.neuralweb import theme_state_adapter as adapter
    bundle = adapter.capture_owner_bundle(production_world, effective_at=EFFECTIVE, known_at=CORR_KNOWN)
    second = g.prepare_generation(bundle, root=production_world, generated_at=CORR_EMITTED,
        activation_at=CORR_ACTIVATION, entry=g.entry_preflight(production_world),
        correction_reason="controlled later-known owner correction")
    g.publish_generation(production_world, second, controlled_verifier=AcceptedFixture())
    wrong = call_v2(production_world, use_at="2026-10-06T16:00:00Z")
    assert wrong["reason_codes"] == ["EXACT_CAPTURE_QUERY_REQUIRED"]
    corrected = call_v2(production_world, known_at=CORR_KNOWN, use_at="2026-10-06T16:00:00Z")
    assert corrected["status"] == "DESCRIPTIVE"
    assert corrected["publication"]["activation_kind"] == "CORRECTION"
    assert corrected["state"]["known_at"] == CORR_KNOWN
    assert corrected["state"]["generated_at"] == CORR_EMITTED
    assert corrected["state"]["correction"]["previous"]["generated_at"] == EMISSION
    assert corrected["state_identity"]["age_seconds_at_use"] == 97200
    assert_powerless(corrected)
    g.rollback_generation(production_world, first["generation_id"], activation_at="2026-10-06T18:00:00Z",
        controlled_verifier=AcceptedFixture())
    restored = call_v2(production_world, use_at="2026-10-06T19:00:00Z")
    assert restored["publication"]["activation_kind"] == "ROLLBACK"
    assert restored["publication"]["activation_at"] == "2026-10-06T18:00:00Z"
    assert restored["publication"]["rollback_selection"]["generation_id"] == first["generation_id"]
    assert restored["state"]["known_at"] == CAPTURE
    assert restored["state"]["generated_at"] == EMISSION
    assert restored["state_identity"]["generated_at"] == EMISSION
    assert restored["state_identity"]["age_seconds_at_use"] == 111600
    assert call_v1(production_world, use_at="2026-10-06T19:00:00Z")["reason_codes"] == ["STATE_NOT_YET_EMITTED"]
    assert_powerless(restored)


def test_missing_pending_malformed_and_tamper_stay_distinct(production_world):
    missing = call_v2(production_world)
    assert missing["status"] == "MISSING" and missing["reason_codes"] == ["ACCEPTED_REFERENCE_MISSING"]
    assert missing["state"] is None
    plan = publish_predated(production_world)
    from engine.neuralweb import theme_state_adapter as adapter
    bundle = adapter.capture_owner_bundle(production_world, effective_at=EFFECTIVE, known_at=CORR_KNOWN)
    pending = g.prepare_generation(bundle, root=production_world, generated_at=CORR_EMITTED,
        activation_at=CORR_ACTIVATION, entry=g.entry_preflight(production_world),
        correction_reason="controlled later-known owner correction")

    def crash(point):
        if point == "seal":
            raise RuntimeError("controlled interruption")
    with pytest.raises(RuntimeError):
        g.publish_generation(production_world, pending, controlled_verifier=AcceptedFixture(), fault=crash)
    held = call_v2(production_world)
    assert held["status"] == "PENDING"
    assert held["publication"]["generation_id"] == plan["generation_id"]
    assert held["publication"]["pending_generation_id"] == pending["generation_id"]
    assert held["state"]["generated_at"] == EMISSION
    assert held["state"]["known_at"] == CAPTURE
    (production_world / g.PENDING).unlink()
    put(production_world, g.PENDING, b"{")
    malformed = call_v2(production_world)
    assert malformed["status"] == "INVALID" and malformed["reason_codes"] == ["MALFORMED_JSON"]
    assert malformed["state"] is None
    (production_world / g.PENDING).unlink()
    put(production_world, g.GENERATIONS + "/" + plan["generation_id"] + "/state.json", b"foreign")
    tampered = call_v2(production_world)
    assert tampered["status"] == "INVALID" and tampered["state"] is None


def test_witness_required_and_foreign_plan_rejected(production_world):
    plan = publish_predated(production_world)
    out = invoke(production_world, reader.read_generation_at_use)
    assert out["status"] == "DESCRIPTIVE"
    before = files(production_world)
    with pytest.raises(ValueError, match="publication plan witness required"):
        reader.validate_read_receipt_at_use(out)
    witness = publication_plan(production_world, out)
    assert reader.validate_read_receipt_at_use(out, publication_plan=witness) == out
    foreign = copy.deepcopy(plan)
    foreign["activation_at"] = "2026-10-06T12:30:00Z"
    with pytest.raises(ValueError):
        reader.validate_read_receipt_at_use(out, publication_plan=foreign)
    with pytest.raises(ValueError):
        reader.validate_read_receipt_at_use(out, publication_plan=True)
    relabelled = copy.deepcopy(out)
    relabelled["schema"] = "neuralweb.theme_state_generation_read.v1"
    with pytest.raises(ValueError):
        reader.validate_read_receipt_at_use(relabelled, publication_plan=witness)
    with pytest.raises(ValueError):
        reader.validate_read_receipt(out, publication_plan=witness)
    assert files(production_world) == before


def test_unqualified_reader_and_bad_verifier_grant_nothing(production_world):
    publish_predated(production_world)
    for authority in (None, True, object(), "accepted"):
        out = call_v2(production_world, controlled_verifier=authority)
        assert out["status"] == "UNAVAILABLE"
        assert out["reason_codes"] == ["CURRENT_USE_AUTHORITY_UNAVAILABLE"]
        assert out["state"] is None
        assert_powerless(out)
    purpose = call_v2(production_world, purpose="trade")
    assert purpose["reason_codes"] == ["S1_UNMATERIALIZED_CURRENT_SOURCE_PURPOSE_GRANT_REQUIRED"]
    assert purpose["state"] is None
    mismatch = call_v2(production_world, controlled_verifier=ReadFixture(change={"accepted_at": EMISSION}))
    assert mismatch["status"] == "UNAVAILABLE" and mismatch["state"] is None
    absent = call_v2(production_world, node_id="theme:absent")
    assert absent["status"] == "DESCRIPTIVE"
    assert absent["subject_read"]["status"] == "UNAVAILABLE"
    assert absent["subject_read"]["reason_codes"] == ["SUBJECT_UNAVAILABLE"]
    link = production_world.parent / "linked-owner"
    link.symlink_to(production_world, target_is_directory=True)
    linked = call_v2(link)
    assert linked["status"] == "INVALID" and linked["reason_codes"] == ["FAMILY_SYMLINK"]
    assert linked["state"] is None


def test_direct_subject_refuses_rights_tamper_and_unknown_fields(production_world):
    plan = publish_predated(production_world)
    state = g.validate_generation(plan)
    use_reader = _use_reader()
    receipt = use_reader.read_subject_at_use(state, node_id=LOCAL, effective_at=EFFECTIVE,
        known_at=CAPTURE, use_at=USE)
    assert receipt["status"] == "DESCRIPTIVE"
    assert receipt["subject"]["node_id"] == LOCAL
    denied = use_reader.read_subject_at_use(state, node_id=CN, effective_at=EFFECTIVE,
        known_at=CAPTURE, use_at=USE, purpose="public")
    assert denied["status"] == "UNAVAILABLE" and denied["subject"] is None
    assert denied["reason_codes"] == ["S1_UNMATERIALIZED_CURRENT_SOURCE_PURPOSE_GRANT_REQUIRED"]
    assert all(value is False for value in denied["authority_caps"].values())
    tampered = copy.deepcopy(receipt)
    tampered["subject"]["legs"]["baskets"]["records"][0]["reason_codes"] = ["TAMPER"]
    with pytest.raises(ValueError):
        use_reader.validate_read_receipt_at_use(tampered)
    extra = copy.deepcopy(receipt)
    extra["consumer_as_known_at"] = CAPTURE
    with pytest.raises(ValueError):
        use_reader.validate_read_receipt_at_use(extra)
    flagged = copy.deepcopy(receipt)
    flagged["authority_caps"]["may_publish"] = True
    with pytest.raises(ValueError):
        use_reader.validate_read_receipt_at_use(flagged)
    dated = copy.deepcopy(receipt)
    dated["use_at"] = "2026-10-06"
    with pytest.raises(ValueError):
        use_reader.validate_read_receipt_at_use(dated)


def test_stale_and_valid_empty_keep_meaning_without_rights(production_world):
    from engine.neuralweb import thematic_state as legacy
    source = production_world / legacy._FORESIGHT_PATH
    value = json.loads(source.read_text())
    value["asof"] = "2026-09-20"
    source.write_text(json.dumps(value))
    publish_predated(production_world)
    stale = call_v2(production_world)
    assert stale["status"] == "STALE"
    leg = next(row for row in stale["source_clocks"]
        if row["node_id"] == "theme:grid" and row["source_id"] == "foresight_cascade")
    assert leg["freshness"] == "STALE"
    record = next(row for row in stale["state"]["subjects"] if row["node_id"] == "theme:grid")
    assert record["legs"]["foresight_cascade"]["records"][0]["native_clocks"]["effective_at"]["value"] == "2026-09-20"
    assert_powerless(stale)
    refused = call_v2(production_world, controlled_verifier=None)
    assert refused["status"] == "UNAVAILABLE" and refused["state"] is None


def test_valid_empty_is_not_permission(production_world):
    import pandas as pd
    import yaml
    graph = production_world / "data/theme_graph"
    nodes = pd.read_parquet(graph / "nodes.parquet")
    nodes.iloc[0:0].to_parquet(graph / "nodes.parquet", index=False)
    (production_world / "config/theme_crosswalk.yml").write_text(yaml.safe_dump({"themes": []}))
    publish_predated(production_world)
    empty = call_v2(production_world)
    assert empty["status"] == "VALID_EMPTY"
    assert empty["state"]["subjects"] == []
    assert empty["compatibility"]["projection"]["themes"] == []
    assert empty["compatibility"]["projection"]["n_themes"] == 0
    assert_powerless(empty)
    assert call_v2(production_world, controlled_verifier=None)["status"] == "UNAVAILABLE"


def test_closed_schemas_reuse_owner_definitions_without_new_rights():
    use_doc = json.loads((ROOT / "contracts/theme_graph/theme_state_use_read.v1.schema.json").read_text())
    generation = json.loads((ROOT / "contracts/theme_graph/theme_state_generation_read.v2.schema.json").read_text())
    previous = json.loads(reader.SCHEMA_PATH.read_text())
    for key, value in production._SCHEMA_DOC["$defs"].items():
        assert use_doc["$defs"][key] == value
        assert generation["$defs"][key] == value
    assert use_doc["properties"]["schema"]["const"] == "gmi.theme_state_read/v3"
    assert "use_at" in use_doc["required"]
    assert "consumer_as_known_at" not in use_doc["properties"]
    assert use_doc["additionalProperties"] is False
    assert generation["properties"]["schema"]["const"] == "neuralweb.theme_state_generation_read.v2"
    assert generation["required"] == previous["required"]
    for key, value in previous["properties"].items():
        if key in ("schema", "subject_read"):
            continue
        assert generation["properties"][key] == value
    assert generation["properties"]["subject_read"]["anyOf"][1]["$ref"] == "#/$defs/use_read_receipt"
    embedded = generation["$defs"]["use_read_receipt"]
    assert embedded["properties"]["schema"]["const"] == "gmi.theme_state_read/v3"
    assert "use_at" in embedded["required"]
    assert generation["properties"]["materialization_allowed"]["const"] is False


def test_declared_seals_and_v1_contracts_are_unchanged():
    expected = {
        "engine/neuralweb/theme_state_generation.py", "engine/neuralweb/thematic_state.py",
        "engine/neuralweb/envelope.py", "scripts/build_thematic_state.py",
        "contracts/theme_graph/theme_state_generation.v1.schema.json",
        "engine/neuralweb/theme_state_adapter.py", "engine/theme_graph/theme_state_production.py",
        "contracts/theme_graph/theme_state.v2.schema.json",
    }
    bindings = g.producer_bindings()
    assert set(bindings) == expected
    for relative, digest in bindings.items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == digest
    assert "engine/theme_graph/theme_state_use_reader.py" not in bindings
    assert reader.SCHEMA == "neuralweb.theme_state_generation_read.v1"
