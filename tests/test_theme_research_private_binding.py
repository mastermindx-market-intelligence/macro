"""Private-root admission classifier (T03) — one test per status, plus purity pins.

``engine/theme_graph/admission.py::classify_private_evidence_root`` decides whether a
candidate evidence root may be bound as private theme-research evidence. It is PURE:
path logic plus a read of the candidate's own ``evidence.parquet``, no store, no
writer, and deliberately no environment override — custody stays with the caller.
These tests walk every status in the contract's evaluation order and pin the two
purity properties (env-blind, and a signature that cannot grow a caller-supplied
trust flag).
"""
from __future__ import annotations

import os

import pandas as pd
import pytest

from engine.theme_graph.admission import classify_private_evidence_root
from engine.theme_graph.store import EVIDENCE_COLUMNS


def _write_evidence(root, rows: int):
    """A valid evidence parquet under ``root`` with every required column."""
    root.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(
        [{col: f"v{i}" for col in EVIDENCE_COLUMNS} for i in range(rows)],
        columns=list(EVIDENCE_COLUMNS))
    frame.to_parquet(root / "evidence.parquet", index=False)
    return root


def _classify(root, public_roots=()):
    return classify_private_evidence_root(
        root, public_roots=list(public_roots), required_columns=list(EVIDENCE_COLUMNS))


def _assert_shape(out):
    assert set(out) == {"status", "reason", "root"}
    assert isinstance(out["reason"], str) and out["reason"]
    assert isinstance(out["root"], str) and out["root"]
    return out


def test_status_missing(tmp_path):
    out = _assert_shape(_classify(tmp_path / "absent"))
    assert out["status"] == "missing"


def test_status_public_root(tmp_path):
    public = _write_evidence(tmp_path / "public", rows=1)
    (public / "sub").mkdir()
    out = _assert_shape(_classify(public / "sub", public_roots=[public]))
    assert out["status"] == "public_root"
    # The public root itself classifies the same way.
    assert _classify(public, public_roots=[public])["status"] == "public_root"


def test_status_symlink_to_public(tmp_path):
    public = _write_evidence(tmp_path / "public", rows=1)
    link = tmp_path / "link"
    link.symlink_to(public, target_is_directory=True)
    out = _assert_shape(_classify(link, public_roots=[public]))
    assert out["status"] == "symlink_to_public"


def test_status_symlinked_parent_component_to_public(tmp_path):
    public = _write_evidence(tmp_path / "public", rows=1)
    (public / "nested").mkdir()
    link = tmp_path / "link"
    link.symlink_to(public, target_is_directory=True)
    out = _assert_shape(_classify(link / "nested", public_roots=[public]))
    assert out["status"] == "symlink_to_public"


def test_status_unreadable(tmp_path):
    root = tmp_path / "priv"
    root.mkdir()
    (root / "evidence.parquet").write_bytes(b"this is not a parquet file at all")
    out = _assert_shape(_classify(root))
    assert out["status"] == "unreadable"


def test_status_missing_column(tmp_path):
    root = tmp_path / "priv"
    root.mkdir()
    frame = pd.DataFrame(
        [{col: f"v{i}" for col in EVIDENCE_COLUMNS if col != "provider"}
         for i in range(1)],
        columns=[c for c in EVIDENCE_COLUMNS if c != "provider"])
    frame.to_parquet(root / "evidence.parquet", index=False)
    out = _assert_shape(_classify(root))
    assert out["status"] == "missing_column"


def test_status_empty_private(tmp_path):
    root = _write_evidence(tmp_path / "priv", rows=0)
    out = _assert_shape(_classify(root))
    assert out["status"] == "empty_private"


def test_empty_private_is_distinct_from_unreadable(tmp_path):
    empty = _classify(_write_evidence(tmp_path / "empty", rows=0))
    garbage = tmp_path / "garbage"
    garbage.mkdir()
    (garbage / "evidence.parquet").write_bytes(b"\x00\x01garbage bytes")
    unreadable = _classify(garbage)
    assert empty["status"] == "empty_private"
    assert unreadable["status"] == "unreadable"
    assert empty["status"] != unreadable["status"]


def test_status_no_parquet(tmp_path):
    root = tmp_path / "priv"
    root.mkdir()
    out = _assert_shape(_classify(root))
    assert out["status"] == "no_parquet"


def test_status_private_ok(tmp_path):
    root = _write_evidence(tmp_path / "priv", rows=1)
    out = _assert_shape(_classify(root))
    assert out["status"] == "private_ok"


def test_evaluation_order_public_beats_parquet_content(tmp_path):
    """A public root refuses on PATH, before any evidence read — first match wins."""
    public = tmp_path / "public"
    public.mkdir()
    (public / "evidence.parquet").write_bytes(b"garbage, and it must not matter")
    out = _classify(public, public_roots=[public])
    assert out["status"] == "public_root"


def test_classifier_never_reads_os_environ(tmp_path, monkeypatch):
    root = _write_evidence(tmp_path / "priv", rows=1)
    monkeypatch.setattr(os, "environ", {})
    out = _classify(root)
    assert out["status"] == "private_ok"


def test_caller_cannot_supply_a_trust_flag(tmp_path):
    root = _write_evidence(tmp_path / "priv", rows=1)
    with pytest.raises(TypeError):
        classify_private_evidence_root(
            root, public_roots=[tmp_path / "public"],
            required_columns=list(EVIDENCE_COLUMNS), private=True)


def test_evidence_filename_is_pinned_to_the_store_owner(tmp_path, monkeypatch):
    """admission.py restates the evidence file name instead of importing the store;
    this pin turns a silent rename in ``store.evidence_path()`` into a red."""
    from engine.theme_graph import admission, store
    monkeypatch.setattr(store.config, "data_dir", lambda: tmp_path)
    assert admission.EVIDENCE_FILENAME == store.evidence_path().name
