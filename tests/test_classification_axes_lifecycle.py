"""Lifecycle classification-axis reader (WS:GMI-THEME-GRAPH Taxonomy V2, lane L09).

Point-in-time node status wrapped over the theme-graph store's write-once
node rows and append-only lifecycle lineage. Every test injects both frames —
no test ever touches the real store, the network, or ``data/**``.
"""
from __future__ import annotations

import inspect
from pathlib import Path

import pandas as pd
import pytest

import engine.classification_axes.lifecycle as lifecycle_mod
from engine.classification_axes import cell
from engine.classification_axes.lifecycle import (
    AXIS,
    MAX_AGE_DAYS,
    RIGHTS_CONTEXT,
    SOURCE_ARTIFACT,
    SOURCE_OWNER,
    SUBJECT_KINDS,
    read_lifecycle,
)
from engine.theme_graph import store
from engine.theme_graph.identity import basket_node_id

AS_OF = "2026-10-11"

BANNED_SOURCE_TEXT = (
    "engine.intelligence_workspace",
    "engine.market_ontology",
    "engine.company_intelligence",
    "scripts",
    "datetime.now",
    "date.today",
    # The current-overlay read is latest-as-of-now and can never answer a
    # historical as_of; the reader must always take the raw write-once rows.
    "current=True",
)


def _node(node_id: str, **over: object) -> dict:
    """One node row carrying every NODE_COLUMNS key (nulls where unset)."""
    row: dict[str, object] = {name: None for name in store.NODE_COLUMNS}
    row.update(
        {
            "node_id": node_id,
            "kind": over.get("kind", "company"),
            "name_en": over.get("name_en", node_id),
            "market_scope": over.get("market_scope", "global"),
            "tier": over.get("tier"),
            "status": over.get("status", "canonical"),
            "merged_into": over.get("merged_into"),
            "birth_date": over.get("birth_date"),
            "retire_date": over.get("retire_date"),
            "computed_at": over.get("computed_at", "2025-06-01T00:00:00Z"),
            "engine_version": "test",
        }
    )
    return row


def _life(node_id: str, *, status: str, computed_at: str, **over: object) -> dict:
    """One lifecycle lineage row (append-only side-car shape)."""
    row: dict[str, object] = {name: None for name in store.NODE_LIFECYCLE_COLUMNS}
    row.update(
        {
            "schema": "node_lifecycle.v1",
            "node_id": node_id,
            "status": status,
            "retire_date": over.get("retire_date"),
            "merged_into": over.get("merged_into"),
            "reason": over.get("reason", "test"),
            "computed_at": computed_at,
            "engine_version": "test",
        }
    )
    return row


def _frames(
    *nodes: dict,
    lifecycle: tuple[dict, ...] = (),
    node_columns: list[str] | None = None,
    life_columns: list[str] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    nodes_frame = pd.DataFrame(list(nodes), columns=node_columns or list(store.NODE_COLUMNS))
    life_frame = pd.DataFrame(
        list(lifecycle), columns=life_columns or list(store.NODE_LIFECYCLE_COLUMNS)
    )
    return nodes_frame, life_frame


def _read(subject_id: str, *, as_of: str = AS_OF, **frames: object) -> dict:
    result = read_lifecycle(subject_id, as_of=as_of, **frames)
    assert cell.validate_cell(result) == [], result
    assert result["axis"] == "lifecycle"
    assert result["quality"] == "display_only"
    assert result["source"] == {
        "owner": "engine/theme_graph/store.py",
        "artifact": "data/theme_graph/nodes.parquet",
        "field": "status",
    }
    return result


def test_constants_and_single_public_reader():
    assert AXIS == "lifecycle"
    assert SOURCE_OWNER == "engine/theme_graph/store.py"
    assert SOURCE_ARTIFACT == "data/theme_graph/nodes.parquet"
    assert MAX_AGE_DAYS is None
    assert SUBJECT_KINDS == ("co", "theme", "basket", "etf")
    assert RIGHTS_CONTEXT is None
    public = [
        name
        for name in dir(lifecycle_mod)
        if not name.startswith("_") and callable(getattr(lifecycle_mod, name))
    ]
    assert public == ["read_lifecycle"]
    signature = inspect.signature(read_lifecycle)
    assert list(signature.parameters) == [
        "subject_id", "as_of", "root", "nodes", "lifecycle",
    ]
    assert signature.parameters["root"].default is None
    assert signature.parameters["nodes"].default is None
    assert signature.parameters["lifecycle"].default is None


def test_canonical_company_node_without_lifecycle_is_available():
    nodes, life = _frames(_node("co:us:AAPL", birth_date="2015-01-01", tier="micro_theme"))
    got = _read("co:us:AAPL", nodes=nodes, lifecycle=life)
    assert got["status"] == "available"
    assert got["reason_code"] is None
    assert got["value"] == {
        "node_status": "canonical",
        "tier": "micro_theme",
        "kind": "co",
        "birth_date": "2015-01-01",
    }
    assert got["unit"] is None
    assert got["observed_at"] is None
    assert got["effective_at"] == "2015-01-01"
    assert got["freshness"] is None
    assert got["labels"] == []
    assert got["provenance"] == ["status_source:node_row"]
    assert got["rights_context"] is None


def test_retired_lifecycle_row_within_as_of_is_not_applicable():
    nodes, life = _frames(
        _node("co:us:OLD", birth_date="2001-03-04"),
        lifecycle=(
            _life("co:us:OLD", status="retired", computed_at="2026-01-05T00:00:00Z",
                  retire_date="2026-02-01"),
        ),
    )
    got = _read("co:us:OLD", nodes=nodes, lifecycle=life)
    assert got["status"] == "not_applicable"
    assert got["reason_code"] == "retired_entity"
    assert got["value"] is None
    assert got["provenance"] == ["status_source:lifecycle"]


def test_lifecycle_row_computed_after_as_of_is_ignored():
    nodes, life = _frames(
        _node("co:us:AAPL", birth_date="2015-01-01"),
        lifecycle=(
            _life("co:us:AAPL", status="retired", computed_at="2026-12-01T00:00:00Z",
                  retire_date="2027-01-01"),
        ),
    )
    got = _read("co:us:AAPL", nodes=nodes, lifecycle=life)
    assert got["status"] == "available"
    assert got["value"]["node_status"] == "canonical"
    assert got["provenance"] == ["status_source:node_row"]


def test_merged_row_is_superseded_with_merged_into_provenance():
    nodes, life = _frames(
        _node("co:us:OLD", birth_date="2001-03-04"),
        lifecycle=(
            _life("co:us:OLD", status="merged", computed_at="2026-03-01T00:00:00Z",
                  merged_into="co:us:NEW"),
        ),
    )
    got = _read("co:us:OLD", nodes=nodes, lifecycle=life)
    assert got["status"] == "not_applicable"
    assert got["reason_code"] == "superseded_entity"
    assert got["provenance"] == ["status_source:lifecycle", "merged_into:co:us:NEW"]


def test_retire_date_after_as_of_is_history_not_supported():
    nodes, life = _frames(
        _node("co:us:OLD", birth_date="2001-03-04"),
        lifecycle=(
            _life("co:us:OLD", status="retired", computed_at="2026-01-05T00:00:00Z",
                  retire_date="2027-01-01"),
        ),
    )
    got = _read("co:us:OLD", nodes=nodes, lifecycle=life)
    assert got["status"] == "unknown"
    assert got["reason_code"] == "history_not_supported"
    assert got["value"] is None


def test_birth_date_after_as_of_is_history_not_supported():
    nodes, life = _frames(
        _node("co:us:NEWCO", birth_date="2030-01-01"),
        lifecycle=(_life("co:us:NEWCO", status="canonical", computed_at="2030-02-01"),),
    )
    got = _read("co:us:NEWCO", nodes=nodes, lifecycle=life)
    assert got["status"] == "unknown"
    assert got["reason_code"] == "history_not_supported"


def test_blank_or_null_birth_date_is_null_birth_not_degraded():
    # A blank/NaN birth is a null birth, never a refusal and never an "" that
    # leaks into value/effective_at (R-birth).
    nodes, life = _frames(
        _node("co:us:BLANK", birth_date=""),
        _node("co:us:NAN", birth_date=float("nan")),
        lifecycle=(),
    )
    got = _read("co:us:BLANK", nodes=nodes, lifecycle=life)
    assert got["status"] == "available"
    assert got["value"]["birth_date"] is None
    assert got["effective_at"] is None
    got_nan = _read("co:us:NAN", nodes=nodes, lifecycle=life)
    assert got_nan["status"] == "available"
    assert got_nan["value"]["birth_date"] is None
    assert got_nan["effective_at"] is None


def test_impossible_birth_date_is_owner_degraded_with_provenance():
    nodes, life = _frames(_node("co:us:BAD", birth_date="2026-01-45"), lifecycle=())
    got = _read("co:us:BAD", nodes=nodes, lifecycle=life)
    assert got["status"] == "unavailable"
    assert got["reason_code"] == "owner_degraded"
    assert got["provenance"] == ["birth_date_unparseable"]
    assert got["value"] is None


def test_datetime_birth_date_normalises_to_calendar_day():
    nodes, life = _frames(
        _node("co:us:TS", birth_date="2026-06-27T00:00:00"),
        _node("co:us:TSOBJ", birth_date=pd.Timestamp("2024-02-02T09:30:00")),
        lifecycle=(),
    )
    got = _read("co:us:TS", as_of="2026-10-12", nodes=nodes, lifecycle=life)
    assert got["status"] == "available"
    assert got["value"]["birth_date"] == "2026-06-27"
    assert got["effective_at"] == "2026-06-27"
    got_obj = _read("co:us:TSOBJ", as_of="2026-10-12", nodes=nodes, lifecycle=life)
    assert got_obj["status"] == "available"
    assert got_obj["value"]["birth_date"] == "2024-02-02"


@pytest.mark.parametrize(
    "subject_id,kind",
    [
        ("theme:ai_compute", "theme"),
        (f"basket:baskets:semis", "basket"),
        ("etf:SPY", "etf"),
    ],
)
def test_theme_basket_and_etf_subjects_are_available(subject_id, kind):
    nodes, life = _frames(
        _node(subject_id, kind=kind, birth_date="2019-05-01", tier="theme"),
        lifecycle=(),
    )
    got = _read(subject_id, nodes=nodes, lifecycle=life)
    assert got["status"] == "available"
    assert got["value"] == {
        "node_status": "canonical",
        "tier": "theme",
        "kind": kind,
        "birth_date": "2019-05-01",
    }
    assert got["effective_at"] == "2019-05-01"
    assert got["provenance"] == ["status_source:node_row"]


def test_basket_subject_id_is_minted_by_the_house_identity():
    subject_id = basket_node_id("baskets", "semis")
    assert subject_id == "basket:baskets:semis"
    nodes, life = _frames(_node(subject_id, kind="basket", birth_date="2021-01-01"))
    assert _read(subject_id, nodes=nodes, lifecycle=life)["status"] == "available"


def test_absent_node_is_value_missing():
    nodes, life = _frames(_node("co:us:AAPL"), lifecycle=())
    got = _read("co:us:MISSING", nodes=nodes, lifecycle=life)
    assert got["status"] == "unknown"
    assert got["reason_code"] == "value_missing"
    assert got["value"] is None


def test_empty_nodes_frame_is_owner_missing():
    nodes, life = _frames(node_columns=list(store.NODE_COLUMNS), life_columns=list(store.NODE_LIFECYCLE_COLUMNS))
    got = _read("co:us:AAPL", nodes=nodes, lifecycle=life)
    assert got["status"] == "unavailable"
    assert got["reason_code"] == "owner_missing"
    assert got["value"] is None


def test_nodes_frame_missing_a_column_is_owner_degraded():
    nodes = pd.DataFrame([{"status": "canonical"}], columns=["status"])
    life = pd.DataFrame(columns=list(store.NODE_LIFECYCLE_COLUMNS))
    got = _read("co:us:AAPL", nodes=nodes, lifecycle=life)
    assert got["status"] == "unavailable"
    assert got["reason_code"] == "owner_degraded"
    assert got["provenance"] == ["missing_column:node_id"]
    assert got["value"] is None


def test_lifecycle_frame_missing_a_column_is_owner_degraded():
    nodes, life = _frames(
        _node("co:us:AAPL"),
        lifecycle=({"node_id": "co:us:AAPL", "status": "retired"},),
        life_columns=["node_id", "status"],
    )
    got = _read("co:us:AAPL", nodes=nodes, lifecycle=life)
    assert got["status"] == "unavailable"
    assert got["reason_code"] == "owner_degraded"
    # The report names the first gap in NODE_LIFECYCLE_COLUMNS order.
    assert got["provenance"] == ["missing_column:retire_date"]


# --- default-path reads are strict (R-strict): a corrupt artifact is
# --- owner_degraded, never laundered through the non-strict empty-frame
# --- fallback into owner_missing. The store's PATH functions are monkeypatched
# --- so no test ever touches the real data/ tree.


def test_strict_default_read_garbage_nodes_is_owner_degraded(tmp_path, monkeypatch):
    p = tmp_path / "nodes.parquet"
    p.write_bytes(b"not parquet")
    monkeypatch.setattr(store, "nodes_path", lambda: p)
    monkeypatch.setattr(
        store, "node_lifecycle_path", lambda: tmp_path / "absent_lifecycle.parquet"
    )
    got = _read("co:us:AAPL")
    assert got["status"] == "unavailable"
    assert got["reason_code"] == "owner_degraded"
    assert got["provenance"] == ["read_error:ValueError"]
    assert got["value"] is None


def test_strict_default_read_missing_nodes_table_is_owner_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "nodes_path", lambda: tmp_path / "absent_nodes.parquet")
    monkeypatch.setattr(
        store, "node_lifecycle_path", lambda: tmp_path / "absent_lifecycle.parquet"
    )
    got = _read("co:us:AAPL")
    assert got["status"] == "unavailable"
    assert got["reason_code"] == "owner_missing"
    assert got["value"] is None


def test_strict_default_read_absent_lifecycle_keeps_node_row_answer(
    tmp_path, monkeypatch
):
    p = tmp_path / "nodes.parquet"
    nodes_frame, _ = _frames(_node("co:us:STRICT", birth_date="2015-01-01"))
    nodes_frame.to_parquet(p)
    monkeypatch.setattr(store, "nodes_path", lambda: p)
    monkeypatch.setattr(
        store, "node_lifecycle_path", lambda: tmp_path / "absent_lifecycle.parquet"
    )
    got = _read("co:us:STRICT")
    assert got["status"] == "available"
    assert got["value"]["node_status"] == "canonical"
    assert got["provenance"] == ["status_source:node_row"]


def test_strict_default_read_garbage_lifecycle_is_owner_degraded(tmp_path, monkeypatch):
    p = tmp_path / "nodes.parquet"
    nodes_frame, _ = _frames(_node("co:us:STRICT", birth_date="2015-01-01"))
    nodes_frame.to_parquet(p)
    q = tmp_path / "lifecycle.parquet"
    q.write_bytes(b"not parquet")
    monkeypatch.setattr(store, "nodes_path", lambda: p)
    monkeypatch.setattr(store, "node_lifecycle_path", lambda: q)
    got = _read("co:us:STRICT")
    assert got["status"] == "unavailable"
    assert got["reason_code"] == "owner_degraded"
    assert got["provenance"] == ["read_error:ValueError"]


def test_empty_lifecycle_frame_is_normal_not_degraded():
    nodes, life = _frames(_node("co:us:AAPL", birth_date="2015-01-01"), lifecycle=())
    got = _read("co:us:AAPL", nodes=nodes, lifecycle=life)
    assert got["status"] == "available"
    assert got["provenance"] == ["status_source:node_row"]


def test_later_lifecycle_row_wins_regardless_of_input_order():
    rows = (
        _life("co:us:OLD", status="canonical", computed_at="2026-01-05T00:00:00Z"),
        _life("co:us:OLD", status="retired", computed_at="2026-06-01T00:00:00Z",
              retire_date="2026-06-15"),
    )
    forward = _frames(_node("co:us:OLD", birth_date="2001-03-04"), lifecycle=rows)
    backward = _frames(_node("co:us:OLD", birth_date="2001-03-04"), lifecycle=tuple(reversed(rows)))
    for frames in (forward, backward):
        got = _read("co:us:OLD", nodes=frames[0], lifecycle=frames[1])
        assert got["status"] == "not_applicable"
        assert got["reason_code"] == "retired_entity"


def test_earliest_node_row_wins_when_node_id_repeats():
    nodes, life = _frames(
        _node("co:us:AAPL", birth_date="2015-01-01", computed_at="2024-01-01T00:00:00Z"),
        _node("co:us:AAPL", birth_date="2020-06-06", computed_at="2025-01-01T00:00:00Z"),
        lifecycle=(),
    )
    got = _read("co:us:AAPL", nodes=nodes, lifecycle=life)
    assert got["value"]["birth_date"] == "2015-01-01"


def test_kind_outside_subject_kinds_is_not_applicable(monkeypatch):
    monkeypatch.setattr(lifecycle_mod, "SUBJECT_KINDS", ("co",))
    nodes, life = _frames(_node("theme:ai_compute", kind="theme"), lifecycle=())
    got = _read("theme:ai_compute", nodes=nodes, lifecycle=life)
    assert got["status"] == "not_applicable"
    assert got["reason_code"] == "not_applicable"


def test_bad_subject_id_propagates_axis_cell_error():
    nodes, life = _frames(_node("co:us:AAPL"), lifecycle=())
    for subject_id in ("ltheme:finviz:x", "theme:Bad-Slug", "foo:bar"):
        with pytest.raises(cell.AxisCellError):
            read_lifecycle(subject_id, as_of=AS_OF, nodes=nodes, lifecycle=life)


def test_reader_is_deterministic_via_to_json():
    nodes, life = _frames(
        _node("co:us:AAPL", birth_date="2015-01-01", tier="micro_theme"),
        lifecycle=(
            _life("co:us:AAPL", status="merged", computed_at="2026-03-01T00:00:00Z",
                  merged_into="co:us:NEW"),
        ),
    )
    first = read_lifecycle("co:us:AAPL", as_of=AS_OF, nodes=nodes, lifecycle=life)
    second = read_lifecycle("co:us:AAPL", as_of=AS_OF, nodes=nodes, lifecycle=life)
    assert cell.validate_cell(first) == []
    assert cell.validate_cell(second) == []
    assert cell.to_json(first) == cell.to_json(second)


def test_source_text_guard():
    source_path = Path(__file__).resolve().parents[1] / "engine" / "classification_axes" / "lifecycle.py"
    source = source_path.read_text(encoding="utf-8")
    for banned in BANNED_SOURCE_TEXT:
        assert banned not in source, banned
    assert "read_nodes(current=False, strict=True)" in source
    assert "read_node_lifecycle(latest=False, strict=True)" in source
    assert "RETIRED_LIKE_STATUSES" in source
