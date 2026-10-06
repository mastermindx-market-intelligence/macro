"""Chairman gate #5: read-only relation-action owner resolver acceptance tests."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import jsonschema
import pytest
import yaml

from engine.theme_graph import materialize, probation


def _relation_owner_fixture(tmp_path, tag=""):
    tmp_path.mkdir(parents=True, exist_ok=True)
    source = tmp_path / f"theme_crosswalk{tag}.yml"
    source.write_text(yaml.safe_dump({"date": "2026-08-13", "themes": []}))
    prior = dict(type="EXPRESSES", src="basket:baskets_china_ths:thsc900001",
                 dst="theme:solar", valid_from="2026-07-09")
    prior["edge_id"] = materialize.edge_id_for(
        prior["type"], prior["src"], prior["dst"], prior["valid_from"])
    row = dict(schema="gmi.probation_relation_event/v2",
               action="RELATION_WITHDRAW", status="ratified",
               ratified_by="controlled-authorized-curator",
               created_at="2026-08-12T00:00:00Z",
               adjudicated_at="2026-08-13T14:00:00Z",
               known_at="2026-08-13T14:00:00Z", effective_at="2026-08-13T00:00:00Z",
               prior_relation=prior, new_destination=None,
               source_receipt=probation.relation_source_receipt(source),
               evidence_refs=["controlled:adjudication"], reason="curation",
               authority_caps=dict(may_rank=False, may_size=False,
                                   may_gate=False, may_escalate=False))
    path = tmp_path / f"relation_events{tag}.v2.jsonl"
    return source, path, row


def _write_relation_event(path, row):
    digest = probation.relation_event_digest(row)
    row.update(event_sha256=digest, event_id="relation-event:" + digest)
    path.write_text(json.dumps(row) + "\n")


def _schema_defs():
    contract = Path(__file__).resolve().parents[1] / (
        "contracts/theme_graph/probation_relation_event.v2.schema.json")
    return json.loads(contract.read_text())["$defs"]


def test_accepted_explicit_action_resolves_end_to_end(tmp_path):
    source, path, row = _relation_owner_fixture(tmp_path)
    _write_relation_event(path, row)
    reader = probation.RelationActionOwnerReader(path)
    events = probation.read_relation_events(
        path, source_path=source, emitted_at="2026-08-14T01:00:00Z",
        owner_action_reader=reader)
    assert len(events) == 1
    receipt = events[0].authority_receipt
    assert receipt["status"] == "ACCEPTED"
    assert receipt["receipt_ref"].endswith("#" + row["event_id"])
    assert receipt["accepted_at"] == row["adjudicated_at"]
    jsonschema.Draft202012Validator(_schema_defs()["owner_action_read"]).validate(receipt)
    probation.require_daily_relation_event(
        events[0], belief_time="2026-08-14", emitted_at="2026-08-14T01:00:00Z")


def test_missing_action_refuses_unavailable(tmp_path):
    source, path, row = _relation_owner_fixture(tmp_path)
    _write_relation_event(path, row)
    absent = tmp_path / "absent.jsonl"
    reader = probation.RelationActionOwnerReader(absent)
    out = reader.read_relation_action(
        event_sha256=row["event_sha256"], knowledge_cutoff="2026-08-14T01:00:00Z")
    assert out["status"] == "UNAVAILABLE"

    other = tmp_path / "other.jsonl"
    other.write_text(json.dumps({"event_sha256": "0" * 64}) + "\n")
    reader_other = probation.RelationActionOwnerReader(other)
    assert reader_other.read_relation_action(
        event_sha256=row["event_sha256"],
        knowledge_cutoff="2026-08-14T01:00:00Z")["status"] == "UNAVAILABLE"

    with pytest.raises(probation.RelationEventRefusal,
                       match="OWNER_ACTION_AUTHORITY_UNAVAILABLE"):
        probation.read_relation_events(
            path, source_path=source, emitted_at="2026-08-14T01:00:00Z",
            owner_action_reader=probation.RelationActionOwnerReader(absent))


def test_unratified_action_refuses_unavailable(tmp_path):
    source, path, row = _relation_owner_fixture(tmp_path)
    cases = [
        ("proposed", {"status": "proposed"}),
        ("ratifier", {"ratified_by": " "}),
        ("adjudicated", {"adjudicated_at": None}),
        ("caps", {"authority_caps": dict(may_rank=False, may_size=False,
                                         may_gate=True, may_escalate=False)}),
    ]
    for _name, patch in cases:
        _, p, r = _relation_owner_fixture(tmp_path, tag="_" + _name)
        r.update(patch)
        if patch.get("adjudicated_at") is None:
            del r["adjudicated_at"]
        _write_relation_event(p, r)
        reader = probation.RelationActionOwnerReader(p)
        out = reader.read_relation_action(
            event_sha256=r["event_sha256"], knowledge_cutoff="2026-08-14T01:00:00Z")
        assert out["status"] == "UNAVAILABLE"
        assert out["reason"].startswith("relation action not ratified by the curator path")


def test_malformed_or_stale_receipt_refuses(tmp_path):
    source, path, row = _relation_owner_fixture(tmp_path)
    _write_relation_event(path, row)
    reader = probation.RelationActionOwnerReader(path)

    tampered = json.loads(path.read_text())
    tampered["new_destination"] = "theme:other"
    path.write_text(json.dumps(tampered) + "\n")
    assert reader.read_relation_action(
        event_sha256=row["event_sha256"],
        knowledge_cutoff="2026-08-14T01:00:00Z")["status"] == "STALE"

    _, path2, row2 = _relation_owner_fixture(tmp_path, tag="_id")
    _write_relation_event(path2, row2)
    bad_id = json.loads(path2.read_text())
    bad_id["event_id"] = "relation-event:" + "f" * 64
    path2.write_text(json.dumps(bad_id) + "\n")
    assert probation.RelationActionOwnerReader(path2).read_relation_action(
        event_sha256=row2["event_sha256"],
        knowledge_cutoff="2026-08-14T01:00:00Z")["status"] == "STALE"

    dup_line = path2.read_text() + path2.read_text()
    path2.write_text(dup_line)
    assert probation.RelationActionOwnerReader(path2).read_relation_action(
        event_sha256=row2["event_sha256"],
        knowledge_cutoff="2026-08-14T01:00:00Z")["status"] == "STALE"

    _, path3, row3 = _relation_owner_fixture(tmp_path, tag="_json")
    _write_relation_event(path3, row3)
    path3.write_text(path3.read_text() + "not-json\n")
    assert probation.RelationActionOwnerReader(path3).read_relation_action(
        event_sha256=row3["event_sha256"],
        knowledge_cutoff="2026-08-14T01:00:00Z")["status"] == "STALE"

    _, path4, row4 = _relation_owner_fixture(tmp_path, tag="_cutoff")
    _write_relation_event(path4, row4)
    assert probation.RelationActionOwnerReader(path4).read_relation_action(
        event_sha256=row4["event_sha256"],
        knowledge_cutoff="2026-08-13T13:00:00Z")["status"] == "UNAVAILABLE"

    _, path5, row5 = _relation_owner_fixture(tmp_path, tag="_chrono")
    row5["created_at"] = "2026-08-14T00:00:00Z"
    _write_relation_event(path5, row5)
    assert probation.RelationActionOwnerReader(path5).read_relation_action(
        event_sha256=row5["event_sha256"],
        knowledge_cutoff="2026-08-14T01:00:00Z")["status"] == "STALE"

    r = probation.RelationActionOwnerReader(path5)
    assert r.read_relation_action(
        event_sha256="nothex", knowledge_cutoff="2026-08-14T01:00:00Z")["status"] == "UNAVAILABLE"
    naive = datetime(2026, 8, 14, 1, 0, 0)
    assert r.read_relation_action(
        event_sha256=row5["event_sha256"], knowledge_cutoff=naive)["status"] == "UNAVAILABLE"


def test_curation_assertion_cannot_substitute_for_action_authority(tmp_path):
    source = tmp_path / "theme_crosswalk.yml"
    source.write_text(yaml.safe_dump({
        "date": "2026-08-13",
        "themes": [{"id": "theme:solar", "baskets": ["basket:baskets_china_ths:thsc900001"]}],
    }))
    _, _path, memory_row = _relation_owner_fixture(tmp_path)
    memory_row["source_receipt"] = probation.relation_source_receipt(source)
    digest = probation.relation_event_digest(memory_row)
    memory_row.update(event_sha256=digest, event_id="relation-event:" + digest)

    ledger = tmp_path / "relation_events.v2.jsonl"
    assert not ledger.exists()
    reader = probation.RelationActionOwnerReader(ledger)
    assert reader.read_relation_action(
        event_sha256=digest, knowledge_cutoff="2026-08-14T01:00:00Z")["status"] == "UNAVAILABLE"

    assert probation.read_relation_events(
        ledger, source_path=source, emitted_at="2026-08-14T01:00:00Z",
        owner_action_reader=reader) == []

    legacy = probation.make_proposal(kind="mapping", subject={"old": "subject"},
                                    proposed_by="coverage_gap", created="2026-08-12")
    legacy.update(status="ratified", ratified_by="curator", adjudicated_at="2026-08-12T00:00:00Z")
    queue = tmp_path / "proposals.jsonl"
    probation.append_proposals([legacy], queue)
    before = queue.read_bytes()
    assert probation.read_relation_events(
        ledger, source_path=source, emitted_at="2026-08-14T01:00:00Z",
        owner_action_reader=reader) == []
    assert queue.read_bytes() == before


def test_mutated_ledger_after_acceptance_is_detected(tmp_path):
    source, path, row = _relation_owner_fixture(tmp_path)
    _write_relation_event(path, row)
    reader = probation.RelationActionOwnerReader(path)
    event = probation.read_relation_events(
        path, source_path=source, emitted_at="2026-08-14T01:00:00Z",
        owner_action_reader=reader)[0]
    mutated = json.loads(path.read_text())
    mutated["ratified_by"] = "post-acceptance-tamper"
    path.write_text(json.dumps(mutated) + "\n")
    with pytest.raises(probation.RelationEventRefusal, match="OWNER_ACTION_AUTHORITY_"):
        probation.require_daily_relation_event(
            event, belief_time="2026-08-14", emitted_at="2026-08-14T01:00:00Z")


def test_prior_pit_answers_unchanged_without_ledger(tmp_path):
    source, path, row = _relation_owner_fixture(tmp_path)
    _write_relation_event(path, row)
    absent = tmp_path / "missing.jsonl"
    crosswalk_only = probation.read_relation_events(
        absent, source_path=source, emitted_at="2026-08-14T01:00:00Z",
        owner_action_reader=probation.RelationActionOwnerReader(absent))
    assert crosswalk_only == []

    with pytest.raises(probation.RelationEventRefusal,
                       match="OWNER_ACTION_AUTHORITY_UNAVAILABLE"):
        probation.read_relation_events(
            path, source_path=source, emitted_at="2026-08-14T01:00:00Z",
            owner_action_reader=None)


def test_builder_wires_the_owner_ledger_resolver():
    import scripts.build_theme_graph as bake

    r = bake._relation_action_owner_reader()
    assert isinstance(r, probation.RelationActionOwnerReader)
    assert r._ledger_path == bake._relation_event_sources()[0]
