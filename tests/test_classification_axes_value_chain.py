"""value_chain classification-axis reader (WS:GMI-THEME-GRAPH Taxonomy V2, lane L10).

Answers "where in its parent theme's value chain does this sub-theme /
micro-theme sit, as known on date D?" by reading the house-curated
``value_chain_position`` from a theme node's ``source_meta`` JSON. Most nodes
have no position yet: ``unknown/value_missing`` is the honest common answer.

Every reader call below asserts ``cell.validate_cell(cell) == []``. Frames are
built with ``store.NODE_COLUMNS`` / ``store.NODE_LIFECYCLE_COLUMNS`` and
injected, so no test reads ``data/**``. The sibling axis readers (including
the lifecycle axis) are never imported: this lane applies its own as_of
overlay per the L10 ruling.
"""
from __future__ import annotations

import inspect
import json
from pathlib import Path

import pandas as pd
import pytest

from engine.classification_axes import cell
from engine.classification_axes import value_chain
from engine.theme_graph import store

SUBJECT = "theme:ai_compute"
AS_OF = "2026-10-11"
BIRTH = "2026-01-15"


def _node_row(**over: object) -> dict:
    row: dict = {column: None for column in store.NODE_COLUMNS}
    row.update({
        "node_id": SUBJECT,
        "kind": "theme",
        "name_en": "AI compute",
        "name_zh": "AI 算力",
        "market_scope": "global",
        "tier": "sub_theme",
        "status": "active",
        "merged_into": None,
        "birth_date": BIRTH,
        "retire_date": None,
        "identity_epoch": None,
        "external_ids": None,
        "provenance": None,
        "computed_at": f"{BIRTH}T00:00:00Z",
        "engine_version": "test",
        "source_meta": json.dumps({"value_chain_position": "upstream"}),
    })
    row.update(over)
    return row


def _nodes(*rows: dict) -> pd.DataFrame:
    return pd.DataFrame(list(rows), columns=list(store.NODE_COLUMNS))


def _life_row(**over: object) -> dict:
    row: dict = {column: None for column in store.NODE_LIFECYCLE_COLUMNS}
    row.update({
        "schema": "node_lifecycle.v1",
        "node_id": SUBJECT,
        "status": "retired",
        "retire_date": "2026-06-01",
        "merged_into": None,
        "reason": "test",
        "evidence": None,
        "ratified_by": "test",
        "computed_at": "2026-06-01T00:00:00Z",
        "engine_version": "test",
    })
    row.update(over)
    return row


def _lifecycle(*rows: dict) -> pd.DataFrame:
    return pd.DataFrame(list(rows), columns=list(store.NODE_LIFECYCLE_COLUMNS))


def _read(nodes: pd.DataFrame, lifecycle: pd.DataFrame | None, subject_id: str = SUBJECT) -> dict:
    got = value_chain.read_value_chain(
        subject_id, as_of=AS_OF, nodes=nodes,
        lifecycle=_lifecycle() if lifecycle is None else lifecycle,
    )
    assert cell.validate_cell(got) == []
    return got


def test_constants_are_exact_and_the_reader_is_the_only_public_callable():
    assert value_chain.AXIS == "value_chain"
    assert value_chain.SOURCE_OWNER == "engine/theme_graph/store.py"
    assert value_chain.SOURCE_ARTIFACT == "data/theme_graph/nodes.parquet"
    assert value_chain.MAX_AGE_DAYS is None
    assert value_chain.SUBJECT_KINDS == ("theme",)
    assert value_chain.RIGHTS_CONTEXT is None
    assert value_chain.POSITIONS == ("upstream", "midstream", "downstream", "enabler")
    source = value_chain.SOURCE if hasattr(value_chain, "SOURCE") else None
    if source is not None:  # internal helper shape, if the module exposes it
        assert source == {
            "owner": value_chain.SOURCE_OWNER,
            "artifact": value_chain.SOURCE_ARTIFACT,
            "field": "source_meta.value_chain_position",
        }
    public = [
        name for name, obj in inspect.getmembers(value_chain, inspect.isfunction)
        if not name.startswith("_") and obj.__module__ == value_chain.__name__
    ]
    assert public == ["read_value_chain"]
    signature = inspect.signature(value_chain.read_value_chain)
    assert list(signature.parameters) == ["subject_id", "as_of", "root", "nodes", "lifecycle"]


def test_sub_theme_with_a_json_string_position_is_available():
    got = _read(_nodes(_node_row()), None)
    assert got["status"] == "available"
    assert got["reason_code"] is None
    assert got["value"] == {"value_chain_position": "upstream", "tier": "sub_theme"}
    assert got["labels"] == ["house_curated"]
    assert got["unit"] is None
    assert got["observed_at"] is None
    assert got["effective_at"] == BIRTH
    assert got["freshness"] is None
    assert got["as_of"] == AS_OF


def test_micro_theme_with_a_dict_source_meta_is_available():
    got = _read(
        _nodes(_node_row(
            tier="micro_theme",
            source_meta={"value_chain_position": "enabler"},
        )),
        None,
    )
    assert got["status"] == "available"
    assert got["value"] == {"value_chain_position": "enabler", "tier": "micro_theme"}


def test_top_level_theme_is_not_applicable_with_a_tier_provenance_token():
    got = _read(_nodes(_node_row(tier="theme")), None)
    assert got["status"] == "not_applicable"
    assert got["reason_code"] == "not_applicable"
    assert got["value"] is None
    assert got["provenance"] == ["tier:theme"]


def test_any_other_tier_is_not_applicable_with_a_tier_provenance_token():
    got = _read(_nodes(_node_row(tier="macro_category")), None)
    assert got["status"] == "not_applicable"
    assert got["reason_code"] == "not_applicable"
    assert got["provenance"] == ["tier:macro_category"]


@pytest.mark.parametrize(
    "source_meta",
    [
        None,
        float("nan"),
        "   ",
        "",
        json.dumps({"other": "field"}),
        {"other": "field"},
    ],
)
def test_absent_position_is_value_missing(source_meta):
    got = _read(_nodes(_node_row(source_meta=source_meta)), None)
    assert got["status"] == "unknown"
    assert got["reason_code"] == "value_missing"
    assert got["value"] is None


@pytest.mark.parametrize(
    "source_meta,token",
    [
        (json.dumps({"value_chain_position": "sideways"}), "invalid_value_chain_position:sideways"),
        ({"value_chain_position": "diagonal"}, "invalid_value_chain_position:diagonal"),
    ],
)
def test_an_out_of_vocabulary_position_is_owner_degraded(source_meta, token):
    got = _read(_nodes(_node_row(source_meta=source_meta)), None)
    assert got["status"] == "unavailable"
    assert got["reason_code"] == "owner_degraded"
    assert got["provenance"] == [token]


@pytest.mark.parametrize("source_meta", ["{not json", "[1, 2]", "42"])
def test_unparseable_source_meta_is_owner_degraded(source_meta):
    got = _read(_nodes(_node_row(source_meta=source_meta)), None)
    assert got["status"] == "unavailable"
    assert got["reason_code"] == "owner_degraded"
    assert got["provenance"] == ["source_meta_unparseable"]


def test_birth_after_as_of_is_history_not_supported():
    got = _read(_nodes(_node_row(birth_date="2026-12-01")), None)
    assert got["status"] == "unknown"
    assert got["reason_code"] == "history_not_supported"


def test_lifecycle_retired_on_or_before_as_of_is_retired_entity():
    got = _read(_nodes(_node_row()), _lifecycle(_life_row(status="retired")))
    assert got["status"] == "not_applicable"
    assert got["reason_code"] == "retired_entity"


def test_lifecycle_merged_on_or_before_as_of_is_superseded_entity():
    got = _read(
        _nodes(_node_row()),
        _lifecycle(_life_row(
            status="merged",
            merged_into="theme:ai_infra",
            retire_date="2026-06-01",
        )),
    )
    assert got["status"] == "not_applicable"
    assert got["reason_code"] == "superseded_entity"
    assert "merged_into:theme:ai_infra" in got["provenance"]


def test_a_lifecycle_row_computed_after_as_of_is_ignored():
    got = _read(_nodes(_node_row()), _lifecycle(_life_row(computed_at="2026-11-01T00:00:00Z")))
    assert got["status"] == "available"
    assert got["value"]["value_chain_position"] == "upstream"


def test_a_retirement_recorded_before_as_of_with_a_future_retire_date():
    got = _read(_nodes(_node_row()), _lifecycle(_life_row(retire_date="2027-01-01")))
    assert got["status"] == "unknown"
    assert got["reason_code"] == "history_not_supported"


def test_without_lifecycle_rows_the_node_row_status_decides():
    got = _read(_nodes(_node_row()), _lifecycle())
    assert got["status"] == "available"
    got = _read(
        _nodes(_node_row(status="retired", retire_date="2026-03-01")),
        _lifecycle(),
    )
    assert got["status"] == "not_applicable"
    assert got["reason_code"] == "retired_entity"


def test_a_malformed_lifecycle_frame_falls_back_to_the_node_row():
    bare = pd.DataFrame([_life_row()]).drop(columns=["computed_at"])
    got = _read(_nodes(_node_row()), bare)
    assert got["status"] == "available"


@pytest.mark.parametrize("subject_id", ["co:us:AAPL", "etf:SPY"])
def test_non_theme_subject_kinds_are_not_applicable(subject_id):
    got = _read(_nodes(_node_row()), None, subject_id=subject_id)
    assert got["status"] == "not_applicable"
    assert got["reason_code"] == "not_applicable"


@pytest.mark.parametrize(
    "subject_id",
    ["ltheme:finviz:x", "ltheme:ths:885001", "basket:finviz_themes:x"],
)
def test_vendor_subjects_are_refused(subject_id):
    with pytest.raises(cell.AxisCellError):
        value_chain.read_value_chain(
            subject_id, as_of=AS_OF, nodes=_nodes(_node_row()), lifecycle=_lifecycle(),
        )


def test_an_absent_node_is_value_missing_and_empty_nodes_is_owner_missing():
    got = _read(_nodes(_node_row(node_id="theme:other_theme")), None)
    assert got["status"] == "unknown"
    assert got["reason_code"] == "value_missing"
    got = _read(_nodes(), None)
    assert got["status"] == "unavailable"
    assert got["reason_code"] == "owner_missing"


def test_a_nodes_frame_missing_a_required_column_is_owner_degraded():
    bare = _nodes(_node_row()).drop(columns=["source_meta"])
    got = _read(bare, None)
    assert got["status"] == "unavailable"
    assert got["reason_code"] == "owner_degraded"


def test_several_node_rows_take_the_first_by_computed_at():
    got = _read(_nodes(
        _node_row(computed_at="2026-05-01T00:00:00Z",
                  source_meta=json.dumps({"value_chain_position": "downstream"})),
        _node_row(computed_at="2026-02-01T00:00:00Z",
                  source_meta=json.dumps({"value_chain_position": "upstream"})),
    ), None)
    assert got["status"] == "available"
    assert got["value"]["value_chain_position"] == "upstream"


def test_equal_inputs_give_byte_identical_json():
    nodes = _nodes(_node_row())
    lifecycle = _lifecycle()
    first = value_chain.read_value_chain(SUBJECT, as_of=AS_OF, nodes=nodes, lifecycle=lifecycle)
    second = value_chain.read_value_chain(SUBJECT, as_of=AS_OF, nodes=nodes, lifecycle=lifecycle)
    assert cell.validate_cell(first) == []
    assert cell.validate_cell(second) == []
    assert cell.to_json(first) == cell.to_json(second)
    assert cell.to_json(first) == cell.to_json(first)


def test_the_store_readers_are_called_when_nothing_is_injected(monkeypatch, tmp_path):
    monkeypatch.setattr(store, "nodes_path", lambda: tmp_path / "nodes.parquet")
    monkeypatch.setattr(store, "node_lifecycle_path", lambda: tmp_path / "node_lifecycle.parquet")
    got = value_chain.read_value_chain(SUBJECT, as_of=AS_OF)
    assert cell.validate_cell(got) == []
    assert got["status"] == "unavailable"
    assert got["reason_code"] == "owner_missing"


def test_source_text_guards():
    source = Path(value_chain.__file__).read_text(encoding="utf-8")
    assert "engine.classification_axes.lifecycle" not in source
    assert "engine.intelligence_workspace" not in source
    assert "engine.market_ontology" not in source
    assert "engine.company_intelligence" not in source
    assert "import scripts" not in source
    assert "from scripts" not in source
    assert "current=True" not in source
    assert "datetime.now" not in source
    assert "date.today" not in source
    assert "ltheme" not in source
    assert "read_nodes(current=False, strict=True)" in source
    assert "read_node_lifecycle(latest=False, strict=True)" in source


# --- repair round r3 (R-strict, R-birth; R-determinism above) --------------


def _read_default(subject_id: str = SUBJECT, *, as_of: str = AS_OF) -> dict:
    got = value_chain.read_value_chain(subject_id, as_of=as_of)
    assert cell.validate_cell(got) == []
    return got


def _write_nodes(rows: list[dict], path: Path) -> Path:
    pd.DataFrame(rows, columns=list(store.NODE_COLUMNS)).to_parquet(path)
    return path


def test_a_corrupt_default_nodes_file_is_owner_degraded(monkeypatch, tmp_path):
    nodes = tmp_path / "nodes.parquet"
    nodes.write_bytes(b"not parquet")
    monkeypatch.setattr(store, "nodes_path", lambda: nodes)
    monkeypatch.setattr(store, "node_lifecycle_path", lambda: tmp_path / "node_lifecycle.parquet")
    got = _read_default()
    assert got["status"] == "unavailable"
    assert got["reason_code"] == "owner_degraded"
    assert got["provenance"] == ["store_read_failed"]


def test_an_absent_default_nodes_file_is_owner_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(store, "nodes_path", lambda: tmp_path / "nodes.parquet")
    monkeypatch.setattr(store, "node_lifecycle_path", lambda: tmp_path / "node_lifecycle.parquet")
    got = _read_default()
    assert got["status"] == "unavailable"
    assert got["reason_code"] == "owner_missing"


def test_a_valid_default_nodes_file_answers_with_an_absent_lifecycle_file(monkeypatch, tmp_path):
    nodes = _write_nodes([_node_row()], tmp_path / "nodes.parquet")
    monkeypatch.setattr(store, "nodes_path", lambda: nodes)
    monkeypatch.setattr(store, "node_lifecycle_path", lambda: tmp_path / "absent.parquet")
    got = _read_default()
    assert got == _read(_nodes(_node_row()), None)


def test_a_corrupt_default_lifecycle_file_is_owner_degraded(monkeypatch, tmp_path):
    nodes = _write_nodes([_node_row()], tmp_path / "nodes.parquet")
    lifecycle = tmp_path / "node_lifecycle.parquet"
    lifecycle.write_bytes(b"not parquet")
    monkeypatch.setattr(store, "nodes_path", lambda: nodes)
    monkeypatch.setattr(store, "node_lifecycle_path", lambda: lifecycle)
    got = _read_default()
    assert got["status"] == "unavailable"
    assert got["reason_code"] == "owner_degraded"
    assert got["provenance"] == ["store_read_failed"]


def test_an_empty_birth_date_gives_no_effective_at():
    got = _read(_nodes(_node_row(birth_date="")), None)
    assert got["status"] == "available"
    assert got["effective_at"] is None


def test_an_unparseable_birth_date_is_owner_degraded():
    got = _read(_nodes(_node_row(birth_date="2026-01-45")), None)
    assert got["status"] == "unavailable"
    assert got["reason_code"] == "owner_degraded"
    assert "birth_date_unparseable" in got["provenance"]


def test_a_birth_datetime_is_truncated_to_its_calendar_day():
    got = value_chain.read_value_chain(
        SUBJECT,
        as_of="2026-10-12",
        nodes=_nodes(_node_row(birth_date="2026-06-27T00:00:00")),
        lifecycle=_lifecycle(),
    )
    assert cell.validate_cell(got) == []
    assert got["status"] == "available"
    assert got["effective_at"] == "2026-06-27"
