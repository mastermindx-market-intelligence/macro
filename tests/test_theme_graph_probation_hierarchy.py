"""Probation kind hierarchy and ontology tier filtering (W-C3)."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import jsonschema
import pytest

from engine.theme_graph import probation, proposal_worklist
from engine.theme_graph.ontology import compose_neighborhood

ROOT = Path(__file__).resolve().parents[1]
_SCHEMA = json.loads(
    (ROOT / "contracts/theme_graph/probation_proposal.v1.schema.json").read_text()
)
_VALIDATOR = jsonschema.Draft202012Validator(_SCHEMA)

_EXISTING_KIND_PINS: dict[str, tuple[str, str]] = {
    "new_theme": (
        "prop:5d7dc649fc50b72a",
        '{"adjudicated_at": null, "adjudication_note": null, "created": "2026-01-01T00:00:00Z", '
        '"evidence": {}, "evidence_refs": [], "kind": "new_theme", "note": null, '
        '"proposal_id": "prop:5d7dc649fc50b72a", "proposed_by": "coverage_gap", '
        '"ratified_by": null, "status": "proposed", "subject": {"name_en": "Test", '
        '"name_zh": "测试", "slug": "zz_test_theme"}}',
    ),
    "merge": (
        "prop:2cd039cd8238008f",
        '{"adjudicated_at": null, "adjudication_note": null, "created": "2026-01-01T00:00:00Z", '
        '"evidence": {}, "evidence_refs": [], "kind": "merge", "note": null, '
        '"proposal_id": "prop:2cd039cd8238008f", "proposed_by": "coverage_gap", '
        '"ratified_by": null, "status": "proposed", "subject": {"left": "theme:aa", '
        '"right": "theme:bb"}}',
    ),
    "split": (
        "prop:74fc21e9cf7484ef",
        '{"adjudicated_at": null, "adjudication_note": null, "created": "2026-01-01T00:00:00Z", '
        '"evidence": {}, "evidence_refs": [], "kind": "split", "note": null, '
        '"proposal_id": "prop:74fc21e9cf7484ef", "proposed_by": "coverage_gap", '
        '"ratified_by": null, "status": "proposed", "subject": {"source": "theme:cc", '
        '"targets": ["theme:dd", "theme:ee"]}}',
    ),
    "mapping": (
        "prop:4600ebec43eb21cf",
        '{"adjudicated_at": null, "adjudication_note": null, "created": "2026-01-01T00:00:00Z", '
        '"evidence": {}, "evidence_refs": [], "kind": "mapping", "note": null, '
        '"proposal_id": "prop:4600ebec43eb21cf", "proposed_by": "coverage_gap", '
        '"ratified_by": null, "status": "proposed", "subject": {"basket": "basket:us:tech", '
        '"local_theme": "ltheme:finviz:ai"}}',
    ),
    "key_rename": (
        "prop:499a6de835171bb5",
        '{"adjudicated_at": null, "adjudication_note": null, "created": "2026-01-01T00:00:00Z", '
        '"evidence": {}, "evidence_refs": [], "kind": "key_rename", "note": null, '
        '"proposal_id": "prop:499a6de835171bb5", "proposed_by": "coverage_gap", '
        '"ratified_by": null, "status": "proposed", "subject": {"family": "finviz_themes", '
        '"new_key": "new", "old_key": "old"}}',
    ),
    "identity_continuity": (
        "prop:8197e49066ec3405",
        '{"adjudicated_at": null, "adjudication_note": null, "created": "2026-01-01T00:00:00Z", '
        '"evidence": {}, "evidence_refs": [], "kind": "identity_continuity", "note": null, '
        '"proposal_id": "prop:8197e49066ec3405", "proposed_by": "coverage_gap", '
        '"ratified_by": null, "status": "proposed", "subject": {"prior_ticker": "AAPL", '
        '"ticker": "AAPL"}}',
    ),
}


def _hierarchy_subject(**overrides) -> dict:
    base = {
        "parent_id": "theme:macro_energy",
        "child_id": "theme:ai_power",
        "child_tier": "theme",
        "proposed_asserted_on": "2026-10-07",
        "nominated_from": "vertical:energy:nuclear",
    }
    base.update(overrides)
    return base


def _hierarchy_row(
    *,
    subject: dict | None = None,
    proposed_by: str = "coverage_gap",
    created: str = "2026-10-07T00:00:00Z",
    status: str = "proposed",
    ratified_by: str | None = None,
    adjudicated_at: str | None = None,
) -> dict:
    row = probation.make_proposal(
        kind="hierarchy",
        subject=subject or _hierarchy_subject(),
        proposed_by=proposed_by,
        created=created,
    )
    row["status"] = status
    row["ratified_by"] = ratified_by
    row["adjudicated_at"] = adjudicated_at
    return row


def _ont_node(node_id: str, kind: str, *, tier: str | None = "theme") -> dict:
    return {
        "node_id": node_id,
        "kind": kind,
        "name_en": node_id,
        "name_zh": None,
        "market_scope": "global",
        "tier": tier,
        "status": "canonical",
        "merged_into": None,
        "birth_date": "2026-01-01",
        "retire_date": None,
        "identity_epoch": 1,
        "external_ids": "{}",
        "provenance": "test",
        "computed_at": "2026-01-01T00:00:00Z",
        "engine_version": "theme_graph.v1",
        "source_meta": None,
    }


def _ont_edge(edge_id: str, type_: str, src: str, dst: str, *, valid_from: str = "2026-10-07") -> dict:
    return {
        "edge_id": edge_id,
        "type": type_,
        "src": src,
        "dst": dst,
        "valid_from": valid_from,
        "valid_to": None,
        "evidence_time": valid_from,
        "belief_time": valid_from,
        "era": "observed",
        "source_class": "curated",
        "date_provenance": "crosswalk",
        "evidence_refs": ["ev:test"],
        "confidence_basis": "test.v1",
        "computed_at": "2026-10-07T00:00:00Z",
        "engine_version": "theme_graph.v1",
    }


def _store(**kwargs):
    return SimpleNamespace(
        read_nodes=lambda: kwargs.get("nodes", []),
        read_node_lifecycle=lambda: kwargs.get("lifecycle", []),
        read_edges=lambda: kwargs.get("edges", []),
        read_proposals=lambda: kwargs.get("proposals", []),
    )


def test_hierarchy_row_passes_schema_validate_and_round_trips(tmp_path):
    row = _hierarchy_row()
    _VALIDATOR.validate(row)
    assert probation.validate(row) == []
    path = tmp_path / "proposals.jsonl"
    assert probation.append_proposals([row], path) == (1, 0)
    loaded = probation.read_proposals(path)[0]
    assert loaded == row
    assert loaded["proposal_id"] == probation.proposal_id("hierarchy", row["subject"])


@pytest.mark.parametrize("kind", list(_EXISTING_KIND_PINS))
def test_existing_kind_proposal_id_and_serialization_unchanged(kind):
    expected_id, expected_line = _EXISTING_KIND_PINS[kind]
    row = json.loads(expected_line)
    assert row["proposal_id"] == expected_id
    assert probation.proposal_id(kind, row["subject"]) == expected_id
    serialized = json.dumps(
        {key: row.get(key) for key in probation.ROW_FIELDS},
        ensure_ascii=False,
        sort_keys=True,
    )
    assert serialized == expected_line


def test_require_valid_rows_accepts_production_probation_file_if_present():
    path = ROOT / "data/theme_graph/probation/proposals.jsonl"
    if not path.is_file():
        pytest.skip("sparse checkout: production probation file absent")
    probation.require_valid_rows(probation.read_proposals(path, strict=True))


def test_llm_hierarchy_cannot_be_ratified():
    row = _hierarchy_row(proposed_by="llm_proposed", status="ratified",
                          ratified_by="bot", adjudicated_at="2026-10-08T00:00:00Z")
    with pytest.raises(jsonschema.ValidationError):
        _VALIDATOR.validate(row)
    assert any(e.startswith("LLM_HIERARCHY_NOT_RATIFIABLE") for e in probation.validate(row))


def test_llm_hierarchy_proposed_and_rejected_pass():
    for status in ("proposed", "rejected"):
        row = _hierarchy_row(
            proposed_by="llm_proposed",
            status=status,
            ratified_by=None,
            adjudicated_at="2026-10-08T00:00:00Z" if status == "rejected" else None,
        )
        _VALIDATOR.validate(row)
        assert probation.validate(row) == []


@pytest.mark.parametrize(
    "nominated_from,reason",
    [
        ("basket:baskets_china_ths:thsc900001", "VENDOR_NOMINATOR"),
        ("basket:finviz_themes:aicompute", "VENDOR_NOMINATOR"),
        ("research:ths_dump", "VENDOR_NOMINATOR"),
        ("not-a-valid-nominator", "NOMINATED_FROM_GRAMMAR"),
    ],
)
def test_vendor_and_malformed_nominators_refused(nominated_from, reason):
    row = _hierarchy_row(subject=_hierarchy_subject(nominated_from=nominated_from))
    assert any(e.startswith(reason) for e in probation.validate(row))


def test_house_nominators_accepted():
    for nominated_from in ("vertical:energy:nuclear", "research:research/x.md",
                           "basket:baskets:solar_us"):
        row = _hierarchy_row(subject=_hierarchy_subject(nominated_from=nominated_from))
        assert probation.validate(row) == []


def test_pre_epoch_and_self_parent_refused():
    row = _hierarchy_row(subject=_hierarchy_subject(proposed_asserted_on="2026-10-06"))
    assert any(e.startswith("HIERARCHY_EPOCH") for e in probation.validate(row))
    row = _hierarchy_row(
        subject=_hierarchy_subject(parent_id="theme:same", child_id="theme:same")
    )
    assert any(e.startswith("HIERARCHY_SELF_EDGE") for e in probation.validate(row))


def test_ontology_neighborhood_unchanged_when_hierarchy_nodes_present():
    theme = "theme:ai_semiconductors"
    base_nodes = [_ont_node(theme, "theme", tier="theme")]
    base_store = _store(nodes=base_nodes)
    before = compose_neighborhood(base_store, node_id=theme, asof="2026-10-07")

    extra_nodes = [
        _ont_node("theme:macro_ai", "theme", tier="macro_category"),
        _ont_node("theme:micro_hbm", "theme", tier="micro_theme"),
    ]
    extra_edges = [
        _ont_edge("p1", "PARENT_OF", "theme:macro_ai", theme),
        _ont_edge("p2", "PARENT_OF", theme, "theme:micro_hbm"),
    ]
    after = compose_neighborhood(
        _store(nodes=base_nodes + extra_nodes, edges=extra_edges),
        node_id=theme,
        asof="2026-10-07",
    )
    assert after == before


def test_macro_category_id_behaves_like_unknown():
    macro = "theme:macro_ai"
    store = _store(nodes=[_ont_node(macro, "theme", tier="macro_category")])
    result = compose_neighborhood(store, node_id=macro, asof="2026-10-07")
    assert result["availability"]["state"] == "SUBJECT_NOT_FOUND"


def test_ratified_hierarchy_materialization_follows_parent_of_edge():
    parent = "theme:macro_energy"
    child = "theme:ai_power"
    subject = _hierarchy_subject(parent_id=parent, child_id=child)
    proposal = _hierarchy_row(
        status="ratified",
        ratified_by="curator:test",
        adjudicated_at="2026-10-08T00:00:00Z",
        subject=subject,
    )
    nodes = [
        _ont_node(parent, "theme", tier="macro_category"),
        _ont_node(child, "theme", tier="theme"),
    ]
    edge = _ont_edge("parent_of:1", "PARENT_OF", parent, child)
    store_with = _store(nodes=nodes, edges=[edge], proposals=[proposal])
    store_without = _store(nodes=nodes, proposals=[proposal])

    materialized = compose_neighborhood(store_with, node_id=child, asof="2026-10-08")
    assert materialized["curation"]["state"] == "RATIFIED_AND_MATERIALIZED"

    not_yet = compose_neighborhood(store_without, node_id=child, asof="2026-10-08")
    assert not_yet["curation"]["state"] == "RATIFIED_NOT_MATERIALIZED"


def test_proposal_worklist_accepts_and_filters_hierarchy_kind():
    rows = [
        _hierarchy_row(),
        probation.make_proposal(
            kind="mapping",
            subject={"basket": "basket:baskets:solar_us", "local_theme": "ltheme:finviz:solar"},
            proposed_by="overlap_stats",
        ),
    ]
    page = proposal_worklist.compose_worklist(rows, asof="2026-10-07", kind="hierarchy")
    assert page["counts"]["matching"] == 1
    assert page["items"][0]["proposal"]["kind"] == "hierarchy"
