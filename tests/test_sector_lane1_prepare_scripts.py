"""Lane 1 prepare-scripts increment: import surface plus snapshot-lane proof.

Two properties in one test, per the commission:

(a) every local module ``scripts/vps_live_orchestrator.py`` imports — at any
    depth — must be importable in this tree. Before this increment the
    orchestrator imported ``scripts.prepare_sector_snapshot`` and
    ``scripts.prepare_sector_native_inputs`` while neither module existed in
    the lane 1 stack, so the snapshot lane could not even be entered.

(b) the snapshot lane, driven against a temporary state directory with fixture
    inputs, publishes a selected ``sector`` generation which
    ``SectorGenerationReader`` — the module the serve route reads through —
    then reads back as the current projection.

No network (the holdings workbook is an in-memory fixture) and no production
path: everything happens under pytest temporary directories.
"""
from __future__ import annotations

import ast
import importlib
from pathlib import Path
import subprocess
import time
from datetime import timedelta
from types import SimpleNamespace

import pytest

from collectors.sector_holdings import SectorHoldingsAdapter
from lib.sector_generation_contract import SECTOR_GENERATION_MEMBERS
from scripts import prepare_sector_snapshot as prepare, vps_live_orchestrator as owner
from app.sector_generation import SectorGenerationRequest
from app.sector_generation_reader import SectorGenerationReader
from tests.test_sector_runtime_snapshot import _runtime_roots, _workbook, _orch
from tests.test_sector_captured_input_assembly import (
    sources, original, dependency, captured_inputs, BUILT, REVISION,
)

_LOCAL_ROOTS = ("app", "collectors", "engine", "lib", "scripts", "tests")


def _orchestrator_local_imports():
    """Every local module the orchestrator imports, at any nesting depth."""
    tree = ast.parse(Path(owner.__file__).read_text())
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names
                         if alias.name.split(".", 1)[0] in _LOCAL_ROOTS)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            if node.module.split(".", 1)[0] in _LOCAL_ROOTS:
                found.add(node.module)
    assert found, "orchestrator local import surface disappeared"
    return sorted(found)


def test_prepare_scripts_resolve_and_snapshot_lane_publishes_readable_generation(
        captured_inputs, monkeypatch, tmp_path):
    # (a) The incumbent orchestrator's whole local import surface resolves.
    unresolved = []
    for name in _orchestrator_local_imports():
        try:
            importlib.import_module(name)
        except Exception as exc:  # noqa: BLE001 — the failure names the module
            unresolved.append(f"{name} ({type(exc).__name__}: {exc})")
    assert unresolved == [], "orchestrator imports do not resolve: " + "; ".join(unresolved)

    # (b) The snapshot lane publishes a selected `sector` generation the reader reads.
    base, fixture_root = captured_inputs
    roots, state = _runtime_roots(base, tmp_path, fixture_root)
    monkeypatch.setattr(owner, "ROOT", roots["R"])
    monkeypatch.setattr(SectorHoldingsAdapter, "http_get",
        staticmethod(lambda *args, **kwargs: SimpleNamespace(content=_workbook())))
    orchestrator = _orch(tmp_path, now=BUILT + timedelta(seconds=1),
        deadline_monotonic=time.monotonic() + 400)
    lane_children = []

    def runner(args, **kwargs):
        assert args[1:3] == ["-m", "scripts.prepare_sector_snapshot"]
        lane_children.append(args[1:3])
        return subprocess.CompletedProcess(args, prepare.main(args[3:]), "prepared", "")

    orchestrator.runner = runner
    result = orchestrator.sector_snapshot()
    assert result.status == "ok", result.detail
    assert lane_children == [["-m", "scripts.prepare_sector_snapshot"]]
    assert result.generation_publication["source_revision"] == REVISION

    selected = owner.read_selected_generation(generations_root=state / "generations",
        domain="sector", members=SECTOR_GENERATION_MEMBERS)
    assert selected.manifest["source_revision"] == REVISION

    reader = SectorGenerationReader(generations_root=state / "generations",
        clock=lambda: BUILT + timedelta(seconds=2))
    projection = reader.read_selected_generation(SectorGenerationRequest(audience="preview"))
    assert projection.qualification == "accepted"
    assert projection.published_at == selected.published_at
    assert projection.payload["receipt"]["generation_id"] == selected.generation_id
    assert projection.payload["data"]["audience"] == "preview"
