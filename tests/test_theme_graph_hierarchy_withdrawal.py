"""Curated PARENT_OF withdrawal on the v2 relation-event path (W-C2w)."""
from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pandas as pd
import pytest
import yaml

from engine.theme_graph import materialize, probation
from tests.test_theme_graph_hierarchy import (
    AFTER,
    EPOCH,
    category,
    hierarchy_doc,
    parent,
    tree,
    write_document,
)
from tests.test_theme_graph_relation_action_resolver import (
    _relation_owner_fixture,
    _schema_defs,
    _write_relation_event,
)

# Pinned on origin/main before W-C2w (EXPRESSES relation-event read path unchanged).
W1_EVENT_ID = (
    "relation-event:24ba0470fcddd1dac89dfcd0cbe07d847c16a5c1aa6ddd813663a2dd594b7408"
)
W1_EVENT_SHA256 = "24ba0470fcddd1dac89dfcd0cbe07d847c16a5c1aa6ddd813663a2dd594b7408"
W1_PRIOR_EDGE_ID = "expresses:basket:baskets_china_ths:thsc900001->theme:solar@2026-07-09"
W1_RECEIPT_REF_SUFFIX = W1_EVENT_ID
BELIEF_CLOSE = "2026-10-09"


def _contract_validator():
    contract = Path(__file__).resolve().parents[1] / (
        "contracts/theme_graph/probation_relation_event.v2.schema.json")
    return jsonschema.Draft202012Validator(json.loads(contract.read_text()))


def _parent_of_prior(src: str, dst: str, valid_from: str = EPOCH) -> dict:
    prior = dict(type="PARENT_OF", src=src, dst=dst, valid_from=valid_from)
    prior["edge_id"] = materialize.edge_id_for(
        prior["type"], prior["src"], prior["dst"], prior["valid_from"])
    return prior


def _parent_withdraw_row(source: Path, prior: dict, *, effective: str = f"{AFTER}T00:00:00Z",
                         known: str = f"{AFTER}T14:00:00Z") -> dict:
    row = dict(
        schema="gmi.probation_relation_event/v2",
        action="RELATION_WITHDRAW",
        status="ratified",
        ratified_by="controlled-authorized-curator",
        created_at="2026-08-12T00:00:00Z",
        adjudicated_at=known,
        known_at=known,
        effective_at=effective,
        prior_relation={key: prior[key] for key in ("edge_id", "type", "src", "dst", "valid_from")},
        new_destination=None,
        source_receipt=probation.relation_source_receipt(source),
        evidence_refs=["controlled:curation-receipt"],
        reason="curation",
        authority_caps=dict(may_rank=False, may_size=False, may_gate=False, may_escalate=False),
    )
    digest = probation.relation_event_digest(row)
    row.update(event_sha256=digest, event_id="relation-event:" + digest)
    return row


def _build_hierarchy_parent_edge(tree_fixture):
    write_document(
        tree_fixture,
        hierarchy_doc(categories=[category()], micro_themes=[], parents=[parent()]),
    )
    root, source = tree_fixture
    view = materialize.build(
        era="reconstruction",
        belief_time=AFTER,
        computed_at=f"{AFTER}T00:00:00Z",
        data_dir=root,
        crosswalk_path=source,
        raw_snapshot=(AFTER, {}),
        ths_history=pd.DataFrame(
            columns=["snapshot_date", "suite", "basket_id", "ticker", "source_shape"]),
    )
    edge = next(row for row in view.edges if row["type"] == "PARENT_OF")
    return root, source, view, edge


def _delete_parents_row(tree_fixture):
    doc = yaml.safe_load(tree_fixture[1].read_text(encoding="utf-8"))
    doc["hierarchy"]["parents"] = []
    tree_fixture[1].write_text(
        yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), encoding="utf-8")


def test_w1_expresses_relation_event_read_unchanged(tmp_path):
    source, path, row = _relation_owner_fixture(tmp_path)
    _write_relation_event(path, row)
    reader = probation.RelationActionOwnerReader(path)
    events = probation.read_relation_events(
        path,
        source_path=source,
        emitted_at="2026-08-14T01:00:00Z",
        owner_action_reader=reader,
    )
    assert len(events) == 1
    receipt = events[0].receipt
    assert receipt["event_id"] == W1_EVENT_ID
    assert receipt["event_sha256"] == W1_EVENT_SHA256
    assert receipt["prior_relation"]["edge_id"] == W1_PRIOR_EDGE_ID
    authority = events[0].authority_receipt
    assert authority["status"] == "ACCEPTED"
    assert authority["receipt_ref"].endswith("#" + W1_RECEIPT_REF_SUFFIX)
    jsonschema.Draft202012Validator(_schema_defs()["owner_action_read"]).validate(authority)


def test_w2_yaml_row_deletion_withdraw_closes_parent_of(tree):
    root, source, _view, edge = _build_hierarchy_parent_edge(tree)
    stored = pd.DataFrame([edge])
    _delete_parents_row(tree)
    computed_view = materialize.build(
        era="reconstruction",
        belief_time=AFTER,
        computed_at=f"{AFTER}T01:00:00Z",
        data_dir=root,
        crosswalk_path=source,
        raw_snapshot=(AFTER, {}),
        ths_history=pd.DataFrame(
            columns=["snapshot_date", "suite", "basket_id", "ticker", "source_shape"]),
    )
    computed = list(computed_view.edges)
    assert not any(
        row["edge_id"] == edge["edge_id"] and row.get("valid_to") in (None, float("nan"))
        for row in computed
        if row["type"] == "PARENT_OF"
    )
    prior = _parent_of_prior(edge["src"], edge["dst"], edge["valid_from"])
    event_path = root / "relation_events.v2.jsonl"
    row = _parent_withdraw_row(source, prior)
    _write_relation_event(event_path, row)
    reader = probation.RelationActionOwnerReader(event_path)
    emitted = f"{BELIEF_CLOSE}T01:00:00Z"
    events = probation.read_relation_events(
        event_path,
        source_path=source,
        emitted_at=emitted,
        owner_action_reader=reader,
    )
    closings, evidence = materialize.apply_relation_events(
        stored,
        computed,
        events,
        belief_time=BELIEF_CLOSE,
        era="reconstruction",
        computed_at=emitted,
    )
    assert len(closings) == 1
    closed = closings[0]
    assert closed["type"] == "PARENT_OF"
    assert closed["valid_to"] == AFTER
    assert closed["edge_id"] == edge["edge_id"]
    assert any("operator_curation" in str(ref) or ref.startswith("ev:")
               for ref in closed["evidence_refs"])
    assert len(evidence) == 2


def test_w3_withdraw_while_row_still_in_yaml_contradicts(tree):
    root, source, _view, edge = _build_hierarchy_parent_edge(tree)
    stored = pd.DataFrame([edge])
    computed_view = materialize.build(
        era="reconstruction",
        belief_time=AFTER,
        computed_at=f"{AFTER}T01:00:00Z",
        data_dir=root,
        crosswalk_path=source,
        raw_snapshot=(AFTER, {}),
        ths_history=pd.DataFrame(
            columns=["snapshot_date", "suite", "basket_id", "ticker", "source_shape"]),
    )
    computed = list(computed_view.edges)
    prior = _parent_of_prior(edge["src"], edge["dst"], edge["valid_from"])
    event_path = root / "relation_events.v2.jsonl"
    row = _parent_withdraw_row(source, prior)
    _write_relation_event(event_path, row)
    reader = probation.RelationActionOwnerReader(event_path)
    emitted = f"{BELIEF_CLOSE}T01:00:00Z"
    events = probation.read_relation_events(
        event_path,
        source_path=source,
        emitted_at=emitted,
        owner_action_reader=reader,
    )
    with pytest.raises(ValueError, match="contradicts the current curated mapping"):
        materialize.apply_relation_events(
            stored,
            computed,
            events,
            belief_time=BELIEF_CLOSE,
            era="reconstruction",
            computed_at=emitted,
        )


def test_w4_parent_of_destination_change_refused_at_read(tree):
    root, source, _view, edge = _build_hierarchy_parent_edge(tree)
    prior = _parent_of_prior(edge["src"], edge["dst"], edge["valid_from"])
    row = _parent_withdraw_row(source, prior)
    row["action"] = "DESTINATION_CHANGE"
    row["new_destination"] = "theme:replacement"
    event_path = root / "relation_events.v2.jsonl"
    _write_relation_event(event_path, row)
    with pytest.raises(probation.RelationEventRefusal, match="^PARENT_OF_DESTINATION_CHANGE_REFUSED"):
        probation.read_relation_events(
            event_path,
            source_path=source,
            emitted_at=f"{BELIEF_CLOSE}T01:00:00Z",
            owner_action_reader=probation.RelationActionOwnerReader(event_path),
        )


def test_w5_row_deleted_without_event_does_not_close(tree):
    root, source, _view, edge = _build_hierarchy_parent_edge(tree)
    stored = pd.DataFrame([edge])
    _delete_parents_row(tree)
    computed_view = materialize.build(
        era="reconstruction",
        belief_time=AFTER,
        computed_at=f"{AFTER}T01:00:00Z",
        data_dir=root,
        crosswalk_path=source,
        raw_snapshot=(AFTER, {}),
        ths_history=pd.DataFrame(
            columns=["snapshot_date", "suite", "basket_id", "ticker", "source_shape"]),
    )
    closings, evidence = materialize.apply_relation_events(
        stored,
        list(computed_view.edges),
        [],
        belief_time=AFTER,
        era="reconstruction",
        computed_at=f"{AFTER}T02:00:00Z",
    )
    assert closings == []
    assert evidence == []


def test_w6_schema_accepts_expresses_and_parent_of_refuses_bad_prior(tmp_path):
    validator = _contract_validator()
    source, _path, expresses_row = _relation_owner_fixture(tmp_path)
    expresses_row["event_sha256"] = probation.relation_event_digest(expresses_row)
    expresses_row["event_id"] = "relation-event:" + expresses_row["event_sha256"]
    validator.validate(expresses_row)

    prior = _parent_of_prior("theme:hierarchy_cat", "theme:solar")
    parent_row = _parent_withdraw_row(source, prior)
    validator.validate(parent_row)

    bad_src = dict(parent_row)
    bad_src["prior_relation"] = dict(prior)
    bad_src["prior_relation"]["src"] = "basket:baskets_china_ths:bad"
    bad_src["event_sha256"] = probation.relation_event_digest(bad_src)
    bad_src["event_id"] = "relation-event:" + bad_src["event_sha256"]
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(bad_src)

    bad_eid = dict(parent_row)
    bad_eid["prior_relation"] = dict(prior)
    bad_eid["prior_relation"]["edge_id"] = "expresses:theme:a->theme:b@2026-10-07"
    bad_eid["event_sha256"] = probation.relation_event_digest(bad_eid)
    bad_eid["event_id"] = "relation-event:" + bad_eid["event_sha256"]
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(bad_eid)
