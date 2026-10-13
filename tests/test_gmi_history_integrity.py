"""Authoritative GMI/PIT history protection; isolated files, never live data."""
from __future__ import annotations

import json

import pandas as pd
import pytest

from engine import basket_membership_pit as pit
from engine.theme_graph import store
from lib import config


TABLES = [
    ("nodes", store.NODE_COLUMNS, store.NODE_KEY),
    ("edges", store.EDGE_COLUMNS, store.EDGE_KEY),
    ("evidence", store.EVIDENCE_COLUMNS, store.EVIDENCE_KEY),
    ("capability", store.CAPABILITY_COLUMNS, store.CAPABILITY_KEY),
    ("identity_resolution", store.IDENTITY_RESOLUTION_COLUMNS, store.IDENTITY_RESOLUTION_KEY),
    ("node_lifecycle", store.NODE_LIFECYCLE_COLUMNS, store.NODE_LIFECYCLE_KEY),
]


def _row(columns, key):
    row = dict.fromkeys(columns)
    row.update({name: "2026-10-03" if "time" in name or name == "computed_at" else "fixture:id"
                for name in key})
    return row


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    return tmp_path


@pytest.mark.parametrize("name,columns,key", TABLES)
@pytest.mark.parametrize("damage", ["unreadable", "missing_key", "duplicate_key", "null_key"])
def test_graph_append_refuses_invalid_prior_without_replacement(isolated, monkeypatch, name, columns, key, damage):
    path = isolated / f"{name}.parquet"
    row = _row(columns, key)
    if damage == "unreadable":
        path.write_bytes(b"retained corrupt original")
    else:
        prior = pd.DataFrame([row], columns=columns)
        if damage == "missing_key":
            prior = prior.drop(columns=[key[0]])
        elif damage == "duplicate_key":
            prior = pd.concat([prior, prior], ignore_index=True)
        else:
            prior.loc[0, key[0]] = None
        prior.to_parquet(path, index=False)
    before = path.read_bytes()
    replacements = []
    monkeypatch.setattr(store, "_atomic_write_parquet", lambda *args: replacements.append(args))
    with pytest.raises(ValueError) as exc:
        store.append_rows(path, [row], columns, key)
    assert type(exc.value).__name__ == "GraphIntegrityError"
    assert replacements == []
    assert path.read_bytes() == before


def test_graph_empty_noop_cannot_hide_corrupt_existing_history(isolated):
    path = isolated / "nodes.parquet"
    path.write_bytes(b"corrupt")
    with pytest.raises(ValueError):
        store.append_rows(path, [], store.NODE_COLUMNS, store.NODE_KEY)
    assert path.read_bytes() == b"corrupt"


@pytest.mark.parametrize("name,columns,key", TABLES)
def test_graph_initialization_and_valid_empty_history_are_allowed(isolated, name, columns, key):
    path = isolated / f"{name}.parquet"
    row = _row(columns, key)
    assert store.append_rows(path, [row], columns, key) == 1
    assert store.append_rows(path, [row], columns, key) == 0
    empty = isolated / f"{name}-empty.parquet"
    pd.DataFrame(columns=columns).to_parquet(empty, index=False)
    assert store.append_rows(empty, [row], columns, key) == 1


@pytest.mark.parametrize("columns,key,optional", [
    (store.NODE_COLUMNS, store.NODE_KEY, ("source_meta",)),
    (store.EVIDENCE_COLUMNS, store.EVIDENCE_KEY, ("provider", "claim_type")),
])
def test_graph_legacy_additive_columns_do_not_rewrite_prior_meaning(isolated, columns, key, optional):
    path = isolated / "legacy.parquet"
    old = _row(columns, key)
    old["computed_at"] = "2026-07-01T00:00:00Z"
    pd.DataFrame([old], columns=[c for c in columns if c not in optional]).to_parquet(path, index=False)
    new = dict(old)
    new[key[0]] = "fixture:new"
    assert store.append_rows(path, [new], columns, key) == 1
    retained = pd.read_parquet(path)
    first = retained[retained[key[0]] == old[key[0]]].iloc[0]
    assert first["computed_at"] == old["computed_at"]
    assert all(pd.isna(first[c]) for c in optional)


def _pit_row():
    return pit._rows_from_doc({"baskets": {"basket:a": {"members": [
        {"ticker": "600001.SS", "added": "2026-07-01", "removed": None}
    ]}}}, "2026-07-01", pit.SUITE_THS)[0]


def _pit_prior(root, damage):
    path = pit.history_path(pit.SUITE_THS)
    path.parent.mkdir(parents=True, exist_ok=True)
    row = _pit_row()
    if damage == "unreadable":
        path.write_bytes(b"retained corrupt PIT")
    else:
        frame = pd.DataFrame([row], columns=pit.COLUMNS)
        if damage == "missing_key":
            frame = frame.drop(columns=["snapshot_date"])
        elif damage == "duplicate_key":
            frame = pd.concat([frame, frame], ignore_index=True)
        elif damage == "wrong_suite":
            frame["suite"] = pit.SUITE_CURATED
        else:
            frame["ticker"] = None
        frame.to_parquet(path, index=False)
    return path


@pytest.mark.parametrize("damage", ["unreadable", "missing_key", "duplicate_key", "wrong_suite", "null_key"])
def test_pit_authoritative_append_refuses_invalid_prior(isolated, damage):
    path = _pit_prior(isolated, damage)
    before = path.read_bytes()
    with pytest.raises(ValueError) as exc:
        pit._append_rows(pit.SUITE_THS, [_pit_row()])
    assert type(exc.value).__name__ == "HistoryIntegrityError"
    assert path.read_bytes() == before
    assert not list(path.parent.glob("*.tmp"))


@pytest.mark.parametrize("entry", ["snapshot", "backfill", "all"])
def test_pit_public_writer_reports_failure_not_noop(isolated, entry):
    path = _pit_prior(isolated, "unreadable")
    doc = {"baskets": {"basket:a": {"members": [{"ticker": "600001.SS"}]}}}
    pit.membership_path(pit.SUITE_THS).write_text(json.dumps(doc))
    snapshots = pit.snapshot_dir(pit.SUITE_THS)
    snapshots.mkdir(parents=True, exist_ok=True)
    (snapshots / "2026-07-02.json").write_text(json.dumps(doc))
    cadence = pit.cadence_path(pit.SUITE_THS)
    cadence.write_text('{"unchanged": true}')
    before = {p: p.read_bytes() for p in isolated.rglob("*") if p.is_file()}
    if entry == "snapshot":
        result = pit.append_snapshot(pit.SUITE_THS, asof="2026-07-02", lane="asia")
    elif entry == "backfill":
        result = pit.backfill_from_json_snapshots(pit.SUITE_THS, lane="asia")
    else:
        result = pit.append_all(asof="2026-07-02", lane="asia", suites=(pit.SUITE_THS,))[pit.SUITE_THS]
    assert result["error"] == "HistoryIntegrityError"
    assert {p: p.read_bytes() for p in isolated.rglob("*") if p.is_file()} == before
    assert path.read_bytes() == before[path]


def test_pit_strict_schema_and_legacy_additive_compatibility(isolated):
    path = pit.history_path(pit.SUITE_THS)
    path.parent.mkdir(parents=True)
    old = _pit_row()
    # Legacy optional fields remain unknown, not fabricated observations.
    pd.DataFrame([old], columns=pit.KEY + ("suite",)).to_parquet(path, index=False)
    view = pit.read_history(pit.SUITE_THS, strict=True)
    assert len(view) == 1
    assert pd.isna(view.iloc[0]["source_shape"])
    new = dict(old, snapshot_date="2026-07-02", ticker="600002.SS")
    assert pit._append_rows(pit.SUITE_THS, [new]) == 1
    assert pit.read_history(pit.SUITE_THS, strict=True).iloc[0]["snapshot_date"] == "2026-07-01"


def test_pit_failed_temporary_serialization_preserves_destination(isolated, monkeypatch):
    path = pit.history_path(pit.SUITE_THS)
    assert pit._append_rows(pit.SUITE_THS, [_pit_row()]) == 1
    before = path.read_bytes()
    destinations = []
    def fail(frame, target, **kwargs):
        destinations.append(target)
        target.write_bytes(b"partial serialized temporary")
        raise OSError("injected disk failure")
    monkeypatch.setattr(pd.DataFrame, "to_parquet", fail)
    with pytest.raises(ValueError) as exc:
        pit._append_rows(pit.SUITE_THS, [dict(_pit_row(), snapshot_date="2026-07-02")])
    assert type(exc.value).__name__ == "HistoryWriteError"
    assert path not in destinations
    assert path.read_bytes() == before
    assert not list(path.parent.glob("*.tmp"))


def test_pit_initialization_valid_empty_and_duplicate_noop(isolated):
    assert pit._append_rows(pit.SUITE_THS, [_pit_row()]) == 1
    assert pit._append_rows(pit.SUITE_THS, [_pit_row()]) == 0
    path = pit.history_path(pit.SUITE_THS)
    pd.DataFrame(columns=pit.COLUMNS).to_parquet(path, index=False)
    assert pit._append_rows(pit.SUITE_THS, [_pit_row()]) == 1



def test_pit_incoming_duplicates_keep_first_without_altering_prior(isolated):
    old = _pit_row()
    assert pit._append_rows(pit.SUITE_THS, [old]) == 1
    first = dict(old, snapshot_date="2026-07-02", source_shape="first observation")
    second = dict(first, source_shape="later duplicate")
    assert pit._append_rows(pit.SUITE_THS, [first, second]) == 1
    retained = pit.read_history(pit.SUITE_THS, strict=True)
    assert retained.loc[retained["snapshot_date"] == "2026-07-02", "source_shape"].tolist() == ["first observation"]


@pytest.mark.parametrize("entry", ["snapshot", "backfill", "all"])
def test_pit_public_write_failure_is_typed_and_preserves_bytes(isolated, monkeypatch, entry):
    assert pit._append_rows(pit.SUITE_THS, [_pit_row()]) == 1
    doc = {"baskets": {"basket:a": {"members": [{"ticker": "600002.SS"}]}}}
    pit.membership_path(pit.SUITE_THS).write_text(json.dumps(doc))
    snapshots = pit.snapshot_dir(pit.SUITE_THS)
    snapshots.mkdir(parents=True, exist_ok=True)
    (snapshots / "2026-07-02.json").write_text(json.dumps(doc))
    before = {p: p.read_bytes() for p in isolated.rglob("*") if p.is_file()}
    def fail_replace(*args):
        raise OSError("injected replace failure")
    monkeypatch.setattr(pit.os, "replace", fail_replace)
    if entry == "snapshot":
        result = pit.append_snapshot(pit.SUITE_THS, asof="2026-07-02", lane="asia")
    elif entry == "backfill":
        result = pit.backfill_from_json_snapshots(pit.SUITE_THS, lane="asia")
    else:
        result = pit.append_all(asof="2026-07-02", lane="asia", suites=(pit.SUITE_THS,))[pit.SUITE_THS]
    assert result["error"] == "HistoryWriteError"
    assert {p: p.read_bytes() for p in isolated.rglob("*") if p.is_file()} == before
    assert not list(pit.history_path(pit.SUITE_THS).parent.glob("*.tmp"))



def _metadata(*, counts=None):
    return {"computed_at": "2026-10-04T00:00:00Z", "engine_version": store.ENGINE_VERSION,
            "counts": counts if counts is not None else {}}


def _correction_receipt():
    return {"script": "scripts.correct_gmi_identity_lineage",
            "run_at": "2026-08-22T00:00:00Z",
            "rows_appended": {"node_lifecycle": 0, "edges": 0, "evidence": 0},
            "identity_break": [], "entity_type_conflict": [], "skipped_already_retired": []}


@pytest.mark.parametrize("prior", ["missing", "short_current_view"])
def test_r1_review_latest_belief_alias_refuses_before_builder_work(isolated, monkeypatch, prior):
    from scripts import build_theme_graph as bake
    store.store_dir().mkdir(parents=True)
    if prior == "short_current_view":
        row = _row(store.EDGE_COLUMNS, store.EDGE_KEY)
        newer = dict(row, belief_time="2026-10-04")
        pd.DataFrame([row, newer], columns=store.EDGE_COLUMNS).to_parquet(store.edges_path(), index=False)
    claim = 1 if prior == "missing" else 2
    store.meta_path().write_text(json.dumps(_metadata(counts={"nodes": 0, "edges_latest_belief": claim})))
    before = {p: p.read_bytes() for p in isolated.rglob("*") if p.is_file()}
    def forbidden(*args, **kwargs):
        pytest.fail("builder materialized before refusing unavailable claimed edge history")
    monkeypatch.setattr(bake.materialize, "build", forbidden)
    assert bake.run(backfill=False, force_backfill=False) == 1
    assert {p: p.read_bytes() for p in isolated.rglob("*") if p.is_file()} == before


def _controlled_correction(monkeypatch, *, emit=True):
    from scripts import correct_gmi_identity_lineage as correction
    stamp = "2026-10-04T00:00:00Z"
    lifecycle = _row(store.NODE_LIFECYCLE_COLUMNS, store.NODE_LIFECYCLE_KEY)
    lifecycle.update(node_id="company:fixture", computed_at=stamp, status="retired")
    evidence = _row(store.EVIDENCE_COLUMNS, store.EVIDENCE_KEY)
    evidence.update(evidence_id="evidence:fixture", computed_at=stamp)
    monkeypatch.setattr(correction, "_now", lambda: ("2026-10-04", stamp))
    monkeypatch.setattr(correction, "_load_breaks_rows", lambda *args: [])
    monkeypatch.setattr(correction, "compute_correction", lambda **kwargs:
                        ([lifecycle], [], [evidence], {}) if emit else ([], [], [], {}))
    return correction


@pytest.mark.parametrize("damage", ["evidence", "metadata", "claimed_missing_edges"])
@pytest.mark.parametrize("dry_run,emit", [(False, True), (True, True), (False, False)])
def test_r1_review_correction_preflight_precedes_reads_noop_and_writes(isolated, monkeypatch, damage, dry_run, emit):
    correction = _controlled_correction(monkeypatch, emit=emit)
    store.store_dir().mkdir(parents=True)
    if damage == "evidence":
        store.evidence_path().write_bytes(b"corrupt retained evidence")
    elif damage == "metadata":
        store.meta_path().write_text("{}")
    else:
        store.meta_path().write_text(json.dumps(_metadata(counts={"edges_latest_belief": 1})))
    before = {p: p.read_bytes() for p in isolated.rglob("*") if p.is_file()}
    reads = []
    original = store.read_nodes
    def observed_read(*args, **kwargs):
        reads.append("nodes")
        return original(*args, **kwargs)
    monkeypatch.setattr(store, "read_nodes", observed_read)
    assert correction.run(dry_run=dry_run) == 1
    assert reads == []
    assert {p: p.read_bytes() for p in isolated.rglob("*") if p.is_file()} == before
    assert not store.node_lifecycle_path().exists()


def test_r1_review_correction_from_absent_metadata_is_self_consistent(isolated, monkeypatch):
    correction = _controlled_correction(monkeypatch)
    assert correction.run(dry_run=False) == 0
    meta = json.loads(store.meta_path().read_text())
    assert meta["computed_at"] == "2026-10-04T00:00:00Z"
    assert meta["engine_version"] == store.ENGINE_VERSION
    assert meta["correction_receipt"]["run_at"] == "2026-10-04T00:00:00Z"
    assert meta["counts"]["node_lifecycle"] == meta["counts"]["evidence"] == 1
    store.preflight_existing_stores()


def test_r1_review_legacy_correction_metadata_keeps_unknown_old_clocks(isolated):
    store.store_dir().mkdir(parents=True)
    meta = {"counts": {"nodes": 0, "edges_latest_belief": 0},
            "correction_receipt": _correction_receipt()}
    store.meta_path().write_text(json.dumps(meta))
    before = store.meta_path().read_bytes()
    store.preflight_existing_stores()
    assert store.meta_path().read_bytes() == before
    assert "computed_at" not in store.read_meta()
    assert "engine_version" not in store.read_meta()


@pytest.mark.parametrize("damage", ["missing_receipt", "wrong_script", "missing_run_at",
                                    "invalid_rows", "declared_bad_clock", "half_envelope"])
def test_r1_review_legacy_compatibility_does_not_bless_malformed_metadata(isolated, damage):
    store.store_dir().mkdir(parents=True)
    meta = {"counts": {}, "correction_receipt": _correction_receipt()}
    if damage == "missing_receipt":
        meta.pop("correction_receipt")
    elif damage == "wrong_script":
        meta["correction_receipt"]["script"] = "unknown producer"
    elif damage == "missing_run_at":
        meta["correction_receipt"].pop("run_at")
    elif damage == "invalid_rows":
        meta["correction_receipt"]["rows_appended"]["edges"] = -1
    elif damage == "declared_bad_clock":
        meta.update(computed_at=None, engine_version=store.ENGINE_VERSION)
    else:
        meta["computed_at"] = "2026-10-04T00:00:00Z"
    store.meta_path().write_text(json.dumps(meta))
    before = store.meta_path().read_bytes()
    with pytest.raises(store.GraphIntegrityError):
        store.preflight_existing_stores()
    assert store.meta_path().read_bytes() == before



def test_r1_review_new_correction_from_legacy_metadata_uses_actual_current_clock(isolated, monkeypatch):
    correction = _controlled_correction(monkeypatch)
    store.store_dir().mkdir(parents=True)
    legacy = {"counts": {"nodes": 0, "edges_latest_belief": 0},
              "correction_receipt": _correction_receipt()}
    store.meta_path().write_text(json.dumps(legacy))
    assert correction.run(dry_run=False) == 0
    meta = store.read_meta()
    assert meta["computed_at"] == "2026-10-04T00:00:00Z"
    assert meta["computed_at"] != legacy["correction_receipt"]["run_at"]
    assert meta["engine_version"] == store.ENGINE_VERSION
    assert meta["correction_receipt"]["run_at"] == meta["computed_at"]
    store.preflight_existing_stores()
