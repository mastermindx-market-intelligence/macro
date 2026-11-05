"""Selection-clock qualified_reads callback for finalized selection cohorts."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pandas as pd
import pytest

from engine.theme_graph.selection_cohort import compose_selection_cohort, content_sha256
from engine.theme_graph.selection_cohort_reads import (
    _REASON_NO_OVERLAP,
    _REASON_OWNER,
    _REASON_STALE,
    qualified_reads,
)
EFFECTIVE = "2026-10-03T08:00:00Z"
KNOWN = "2026-10-03T12:00:00Z"
OLD = "2026-10-02T08:00:00Z"
SHA = "a" * 64
EFFECTIVE_DATE = "2026-10-03"
FUTURE = "2026-10-04T12:00:00Z"


def selection(n=1):
    rows = [
        {
            "selection_id": f"owner-row-{i}",
            "original_identity": {"ticker": f"SEC{i}"},
            "original_reasons": {"en": f"Owner reason {i}", "zh": f"原始理由{i}"},
            "source_row": {"ticker": f"SEC{i}", "display_rank": i + 1, "owner_score": 20 - i},
        }
        for i in range(n)
    ]
    return dict(
        owner="fixture-selection-owner",
        source_schema="fixture.owner/v1",
        source_ref="fixture://immutable-generation",
        source_sha256=SHA,
        generation_id="owner-generation-1",
        cohort_scope="complete-finalized-fixture",
        effective_at=EFFECTIVE,
        selected_at="2026-10-03T12:01:00Z",
        known_at=KNOWN,
        n_selected=n,
        rows=rows,
        rows_sha256=content_sha256(rows),
        ordered_identity_sha256=content_sha256([r["original_identity"] for r in rows]),
        ordered_reasons_sha256=content_sha256([r["original_reasons"] for r in rows]),
    )


def member(i, node="ltheme:ths:battery", canonical=None):
    return dict(
        member_node_id=f"co:fixture:{i}",
        node_id=node,
        kind="local_theme",
        source_family="ths",
        native_id=node.split(":", 2)[2],
        node_kind="local_theme",
        canonical_node_ids=canonical,
        canonical_nodes=[
            {
                "node_id": x,
                "kind": "theme",
                "receipt_ref": "fixture://canonical/" + x,
                "receipt_sha256": SHA,
            }
            for x in (canonical or [])
        ],
        evidence_ref=f"fixture://membership/{i}/{node}",
        evidence_sha256=SHA,
        effective_from=OLD,
        effective_until=None,
        known_from=OLD,
        rights_status="ALLOWED",
        rights_receipt_ref="fixture://rights/allowed",
    )


def _selection_one_row(node_id="co:us:HUBB", ticker="HUBB"):
    source = selection(1)
    source["cohort_scope"] = "us_today"
    source["rows"][0]["original_identity"] = {"ticker": ticker, "node_id": node_id}
    rows = source["rows"]
    source["rows_sha256"] = content_sha256(rows)
    source["ordered_identity_sha256"] = content_sha256([r["original_identity"] for r in rows])
    return source


def _resolved_identity(node_id, security_id="SEC:US-XNYS-HUBB", computed_at=OLD):
    return {
        "node_id": node_id,
        "resolution_state": "RESOLVED",
        "security_id": security_id,
        "computed_at": computed_at,
        "engine_version": "theme_graph.v1",
    }


def _membership_payload(node_id="co:us:HUBB", theme="ltheme:ths:battery"):
    return [
        dict(
            member(i=0, node=theme),
            member_node_id=node_id,
            rights_status="ALLOWED",
        )
    ]


@pytest.fixture
def data_root(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "theme_graph").mkdir(parents=True)
    registry = Path(__file__).resolve().parents[1] / "config" / "theme_sources.yml"
    (tmp_path / "config").mkdir(exist_ok=True)
    (tmp_path / "config" / "theme_sources.yml").write_bytes(registry.read_bytes())
    monkeypatch.setattr(
        "engine.theme_graph.selection_cohort_reads.rights.emission_allowed",
        lambda family, path=None: True,
    )
    return tmp_path


def _write_graph(tmp_path, *, company="co:us:HUBB", theme="ltheme:ths:battery"):
    tg = tmp_path / "theme_graph"
    nodes = pd.DataFrame(
        [
            {
                "node_id": company,
                "kind": "company",
                "name_en": "Hubbell",
                "name_zh": None,
                "market_scope": "us",
                "tier": None,
                "status": "active",
                "merged_into": None,
                "birth_date": "2015-01-01",
                "retire_date": None,
                "identity_epoch": 1,
                "external_ids": "{}",
                "provenance": "test",
                "computed_at": OLD,
                "engine_version": "theme_graph.v1",
                "source_meta": None,
            },
            {
                "node_id": theme,
                "kind": "local_theme",
                "name_en": "Battery",
                "name_zh": "电池",
                "market_scope": "cn",
                "tier": None,
                "status": "active",
                "merged_into": None,
                "birth_date": "2015-01-01",
                "retire_date": None,
                "identity_epoch": 1,
                "external_ids": "{}",
                "provenance": "test",
                "computed_at": OLD,
                "engine_version": "theme_graph.v1",
                "source_meta": json.dumps({"source_family": "ths", "native_id": "battery"}),
            },
        ]
    )
    edges = pd.DataFrame(
        [
            {
                "edge_id": "edge-member-1",
                "type": "MEMBER_OF",
                "src": company,
                "dst": theme,
                "valid_from": "2015-01-01",
                "valid_to": None,
                "evidence_time": "2015-01-01",
                "belief_time": "2015-01-01",
                "era": "OBSERVED",
                "source_class": "scrape",
                "date_provenance": "membership_pit",
                "evidence_refs": json.dumps(["data/baskets/test/membership.json"]),
                "confidence_basis": "membership_pit.ths.v1",
                "economic_share": None,
                "trading_beta": None,
                "attention_share": None,
                "economic_share_formula_id": None,
                "trading_beta_formula_id": None,
                "attention_share_formula_id": None,
                "economic_share_display": None,
                "trading_beta_display": None,
                "attention_share_display": None,
                "computed_at": OLD,
                "engine_version": "theme_graph.v1",
            }
        ]
    )
    nodes.to_parquet(tg / "nodes.parquet", index=False)
    edges.to_parquet(tg / "edges.parquet", index=False)
    pd.DataFrame(
        columns=[
            "schema",
            "node_id",
            "status",
            "retire_date",
            "merged_into",
            "reason",
            "evidence",
            "ratified_by",
            "computed_at",
            "engine_version",
        ]
    ).to_parquet(tg / "node_lifecycle.parquet", index=False)
    (tg / "probation").mkdir(exist_ok=True)
    (tg / "probation" / "proposals.jsonl").write_text("", encoding="utf-8")
    (tg / "_meta.json").write_text(json.dumps({"engine_version": "theme_graph.v1"}), encoding="utf-8")


def _write_state_artifact(tmp_path, theme="ltheme:ths:battery"):
    import importlib.util

    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("fx_state", root / "tests/test_theme_graph_state.py")
    fx = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fx)
    fx.QUERY = {"effective_at": EFFECTIVE, "known_at": KNOWN}
    src = fx.subject(theme, qualified=True)
    src.update(source_family="ths", native_id="battery")
    artifact = fx.compose([src], generated_at=KNOWN)
    (tmp_path / "theme_graph" / "shadow_theme_state.v1.json").write_text(
        json.dumps(artifact, ensure_ascii=False), encoding="utf-8"
    )
    return artifact


def test_fully_qualified_member_compose_accepts(data_root, monkeypatch):
    _write_graph(data_root)
    artifact = _write_state_artifact(data_root)
    source = _selection_one_row()
    monkeypatch.setattr(
        "engine.theme_graph.selection_cohort_reads.ir.resolve_graph_node_identity",
        lambda node_id, asof=None: _resolved_identity(node_id),
    )
    reads = qualified_reads(source, data_dir=data_root)
    result = compose_selection_cohort(
        source,
        identity_reads=reads["identity_reads"],
        membership_reads=reads["membership_reads"],
        state_reads=reads["state_reads"],
    )
    assert result["coverage"]["n_selected"] == 1
    assert result["selected"][0]["security_id"] == "SEC:US-XNYS-HUBB"
    assert result["concepts"]
    assert result["concepts"][0]["state"]["generation_id"] == artifact["state_sha256"][:32]


def test_stale_for_known_clock(data_root, monkeypatch):
    source = _selection_one_row()
    monkeypatch.setattr(
        "engine.theme_graph.selection_cohort_reads.ir.resolve_graph_node_identity",
        lambda node_id, asof=None: _resolved_identity(node_id, computed_at=FUTURE),
    )
    reads = qualified_reads(source, data_dir=data_root)
    assert any(u["reason_code"] == _REASON_STALE for u in reads["unqualified"])
    assert reads["identity_reads"] == {}


def test_no_overlap_preserves_denominator(data_root, monkeypatch):
    _write_graph(data_root)
    source = _selection_one_row()
    monkeypatch.setattr(
        "engine.theme_graph.selection_cohort_reads.ir.resolve_graph_node_identity",
        lambda node_id, asof=None: _resolved_identity(node_id),
    )
    monkeypatch.setattr(
        "engine.theme_graph.selection_cohort_reads._membership_rows",
        lambda *args, **kwargs: [],
    )
    reads = qualified_reads(source, data_dir=data_root)
    assert any(u["reason_code"] == _REASON_NO_OVERLAP for u in reads["unqualified"])
    result = compose_selection_cohort(
        source,
        identity_reads=reads["identity_reads"],
        membership_reads=reads["membership_reads"],
        state_reads={},
    )
    assert result["coverage"]["n_selected"] == 1
    assert result["coverage"]["no_recorded_membership"] == ["owner-row-0"]


def test_multi_theme_memberships_carried(data_root, monkeypatch):
    _write_graph(data_root)
    second = "ltheme:ths:recycling"
    tg = data_root / "theme_graph"
    nodes = pd.read_parquet(tg / "nodes.parquet")
    extra = nodes[nodes["kind"] == "local_theme"].iloc[0].copy()
    extra["node_id"] = second
    extra["source_meta"] = json.dumps({"source_family": "ths", "native_id": "recycling"})
    nodes = pd.concat([nodes, pd.DataFrame([extra])], ignore_index=True)
    nodes.to_parquet(tg / "nodes.parquet", index=False)
    edges = pd.read_parquet(tg / "edges.parquet")
    row = edges.iloc[0].copy()
    row["edge_id"] = "edge-member-2"
    row["dst"] = second
    edges = pd.concat([edges, pd.DataFrame([row])], ignore_index=True)
    edges.to_parquet(tg / "edges.parquet", index=False)
    _write_state_artifact(data_root, theme="ltheme:ths:battery")
    _write_state_artifact(data_root)  # refresh with one subject only is fine
    source = _selection_one_row()
    monkeypatch.setattr(
        "engine.theme_graph.selection_cohort_reads.ir.resolve_graph_node_identity",
        lambda node_id, asof=None: _resolved_identity(node_id),
    )
    reads = qualified_reads(source, data_dir=data_root)
    memberships = reads["membership_reads"]["owner-row-0"]["memberships"]
    assert len(memberships) == 2
    result = compose_selection_cohort(
        source,
        identity_reads=reads["identity_reads"],
        membership_reads=reads["membership_reads"],
        state_reads=reads["state_reads"],
    )
    assert result["coverage"]["multi_theme"] == ["owner-row-0"]


def test_rights_unresolved_not_dropped(data_root, monkeypatch):
    _write_graph(data_root)
    source = _selection_one_row()
    monkeypatch.setattr(
        "engine.theme_graph.selection_cohort_reads.ir.resolve_graph_node_identity",
        lambda node_id, asof=None: _resolved_identity(node_id),
    )
    monkeypatch.setattr(
        "engine.theme_graph.selection_cohort_reads.rights.emission_allowed",
        lambda family, path=None: False,
    )
    monkeypatch.setattr(
        "engine.theme_graph.rights.emission_allowed",
        lambda family, path=None: False,
    )
    reads = qualified_reads(source, data_dir=data_root)
    result = compose_selection_cohort(
        source,
        identity_reads=reads["identity_reads"],
        membership_reads=reads["membership_reads"],
        state_reads={},
    )
    assert result["coverage"]["missing_rights"] == ["owner-row-0"]
    assert result["coverage"]["n_selected"] == 1


def test_owner_missing_does_not_raise(data_root, monkeypatch):
    source = _selection_one_row()
    monkeypatch.setattr(
        "engine.theme_graph.selection_cohort_reads.ir.resolve_graph_node_identity",
        lambda node_id, asof=None: (_ for _ in ()).throw(
            __import__("engine.theme_graph.identity_resolution", fromlist=["x"]).UnknownGraphNodeError("missing")
        ),
    )
    reads = qualified_reads(source, data_dir=data_root)
    assert any(u["reason_code"] == _REASON_OWNER for u in reads["unqualified"])


def test_selection_clock_not_now(data_root, monkeypatch):
    source = _selection_one_row()
    source["effective_at"] = EFFECTIVE
    source["known_at"] = KNOWN
    monkeypatch.setattr(
        "engine.theme_graph.selection_cohort_reads.ir.resolve_graph_node_identity",
        lambda node_id, asof=None: _resolved_identity(node_id),
    )
    monkeypatch.setattr(
        "engine.theme_graph.selection_cohort_reads._membership_rows",
        lambda *args, **kwargs: _membership_payload(),
    )
    frozen_now = "2099-01-01T00:00:00Z"
    reads = qualified_reads(source, data_dir=data_root, now=frozen_now)
    assert reads["selection_clock"] == {"effective_at": EFFECTIVE, "known_at": KNOWN}
    receipt = reads["identity_reads"]["owner-row-0"]
    assert receipt["effective_at"] == EFFECTIVE and receipt["known_at"] == KNOWN


def test_deterministic_across_two_calls(data_root, monkeypatch):
    _write_graph(data_root)
    source = _selection_one_row()
    monkeypatch.setattr(
        "engine.theme_graph.selection_cohort_reads.ir.resolve_graph_node_identity",
        lambda node_id, asof=None: _resolved_identity(node_id),
    )
    first = qualified_reads(source, data_dir=data_root)
    second = qualified_reads(source, data_dir=data_root)
    assert first == second
