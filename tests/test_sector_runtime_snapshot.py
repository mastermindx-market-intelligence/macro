"""Runtime join proof with actual captures/builders and isolated process faults."""
from copy import deepcopy
from datetime import timedelta
import fcntl
import io
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import threading
import time
from types import SimpleNamespace

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from collectors.sector_holdings import SectorHoldingsAdapter, SSGA_XLSX
from lib.sector_generation_contract import SECTOR_GENERATION_MEMBERS
from scripts import prepare_sector_snapshot as prepare, vps_live_orchestrator as owner
from app import main as macro_main
from app.sector_generation_reader import SectorGenerationReader
from tests.test_sector_captured_input_assembly import (
    sources, original, dependency, captured_inputs, _write_local_capture_sources,
    BUILT, DATED, SOURCE, REVISION, _incumbent_gates,
)


def _workbook():
    output = io.BytesIO()
    pd.DataFrame([
        ["", "As of " + DATED, ""],
        ["Name", "Ticker", "Weight"],
        ["Fixture 0", "T0000", 10.0],
        ["Fixture 1", "T0001", 9.0],
        ["Fixture 2", "T0002", 8.0],
    ]).to_excel(output, header=False, index=False)
    return output.getvalue()


def _runtime_roots(base, root, fixture_root):
    roots = _write_local_capture_sources(base, root / "inputs", alias_theme=True)
    state = root / "private/state"
    generations = state / "generations"
    generations.mkdir(parents=True, mode=0o700)
    for snapshot in (base["prices"].yahoo.snapshot, base["prices"].breadth.snapshot,
                     base["member_ohlcv"].snapshot):
        candidates = list(fixture_root.parent.glob("*/private/state/generations/" + snapshot.generation_dir))
        matches = []
        for candidate in candidates:
            if root == candidate or root in candidate.parents:
                continue
            try:
                observed = owner.read_selected_generation(generations_root=candidate.parents[1],
                    domain=snapshot.domain, members=tuple(snapshot.members))
            except owner.SelectedGenerationUnavailable:
                continue
            if observed.content_id == snapshot.content_id and dict(observed.members) == dict(snapshot.members):
                matches.append(candidate.parent)
        assert matches, "verified original fixture domain was not found"
        shutil.copytree(sorted(matches)[0], generations / snapshot.domain)
    return roots, state


def _orch(root, **kwargs):
    return owner.Orchestrator(live_dir=root / "public/live", state_dir=root / "private/state",
        data_dir=root / "legacy", source_revision=REVISION, **kwargs)


@pytest.fixture(scope="module")
def prepared_candidate(captured_inputs, tmp_path_factory):
    base, fixture_root = captured_inputs
    root = tmp_path_factory.mktemp("prepared-sector-runtime")
    roots, state = _runtime_roots(base, root, fixture_root)
    raw = _workbook()
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(SectorHoldingsAdapter, "http_get",
            staticmethod(lambda *a, **k: SimpleNamespace(content=raw)))
        mp.setattr(owner.Orchestrator, "publish_sector_documents",
            lambda *a, **k: pytest.fail("preparation child attempted publication"))
        composition, metadata = prepare.prepare_snapshot(
            repository_root=roots["R"], theme_root=roots["T"],
            generations_root=state / "generations", generation_id="prepared-runtime-1",
            source_revision=REVISION, clock=lambda: BUILT)
        stage = root / "candidate"
        stage.mkdir(mode=0o700)
        prepare.write_prepared(stage, composition, metadata)
    assert not (state / "generations/sector/current.json").exists()
    return stage, metadata


def test_actual_parent_join_reaches_mounted_api(captured_inputs, monkeypatch, tmp_path, _incumbent_gates):
    base, fixture_root = captured_inputs
    roots, state = _runtime_roots(base, tmp_path, fixture_root)
    monkeypatch.setattr(owner, "ROOT", roots["R"])
    raw = _workbook()
    urls = []
    def http_get(url, **kwargs):
        urls.append(url)
        return SimpleNamespace(content=raw)
    monkeypatch.setattr(SectorHoldingsAdapter, "http_get", staticmethod(http_get))
    publication_calls = []
    orchestrator = _orch(tmp_path, now=BUILT + timedelta(seconds=1),
        deadline_monotonic=time.monotonic() + 400)
    publish = orchestrator.publish_sector_documents
    def publish_once(*args, **kwargs):
        publication_calls.append(kwargs)
        return publish(*args, **kwargs)
    monkeypatch.setattr(orchestrator, "publish_sector_documents", publish_once)
    def runner(args, **kwargs):
        assert args[1:3] == ["-m", "scripts.prepare_sector_snapshot"]
        assert not publication_calls
        rc = prepare.main(args[3:])
        assert not (state / "generations/sector/current.json").exists()
        return subprocess.CompletedProcess(args, rc, "prepared", "")
    orchestrator.runner = runner
    result = orchestrator.sector_snapshot()
    assert result.status == "ok", result.detail
    assert len(publication_calls) == 1
    assert publication_calls[0]["source_revision"] == REVISION
    assert publication_calls[0]["expected_current_content_id"] is None
    assert len(urls) == 11 and set(urls) == {
        SSGA_XLSX.format(fund=f.lower()) for f in base["holdings"]}
    selected = owner.read_selected_generation(generations_root=state / "generations",
        domain="sector", members=SECTOR_GENERATION_MEMBERS)
    facts = selected.manifest["input_identity"]["sector_capture"]["holdings"]
    assert len(facts) == 11 and all(f["outcome"] == "present" for f in facts.values())
    assert selected.manifest["input_identity"]["sector_view"]["input_version"] == "sector-inputs-v1"
    assert selected.manifest["source_revision"] == REVISION
    assert not list(state.glob(".sector-prepare-*"))
    central = json.loads(selected.members["sectordata/sector_central.json"])
    measurements = central["measured_read"]["sector_window_measurements"]
    dated = central["dated_context"]
    assert dated["schema"] == "sector_dated_context/v1"
    assert dated["limitations"]["current_sector_usable"] is False
    assert all(value is False for value in dated["authority"].values())
    assert measurements["windows_sessions"] == [5, 20, 63]
    assert len(measurements["groups"]) == 11
    assert all(v is False for v in measurements["authority"].values())
    reader = SectorGenerationReader(generations_root=state / "generations",
        clock=lambda: BUILT + timedelta(seconds=2))
    monkeypatch.setattr(macro_main.app.state, "sector_generation_reader", reader, raising=False)
    client = TestClient(macro_main.app)
    client.cookies.set("sb-fixture-auth-token", "fixture")
    for audience in ("preview", "entitled"):
        response = client.get("/api/sector-generation?audience=" + audience)
        assert response.status_code == 200, response.text
        assert response.json()["projection"]["data"]["core"]["measured_read"]["sector_window_measurements"] == measurements
        assert response.json()["projection"]["data"]["core"]["dated_context"] == dated
        assert response.headers["cache-control"] == "private, no-store"
        assert response.headers["vary"] == "Cookie"


@pytest.mark.parametrize("damage", [
    "source_revision", "generation_id", "fence", "evidence", "deferred", "bytes", "extra", "symlink", "duplicate_json",
])
def test_parent_refuses_changed_or_incomplete_candidate(prepared_candidate, tmp_path, damage):
    source, original = prepared_candidate
    stage = tmp_path / "candidate"
    shutil.copytree(source, stage)
    metadata = deepcopy(original)
    if damage in {"source_revision", "generation_id"}:
        metadata[damage] = "f" * 40 if damage == "source_revision" else "different-attempt"
    elif damage == "fence":
        metadata["expected_current_content_id"] = "f" * 64
    elif damage == "evidence":
        metadata["composition_evidence"]["member_bytes"][SECTOR_GENERATION_MEMBERS[0]] += 1
    elif damage == "deferred":
        metadata["deferred_effects"].append({"kind": "unexpected"})
    elif damage == "bytes":
        (stage / SECTOR_GENERATION_MEMBERS[0]).write_bytes(b"{}")
    elif damage == "extra":
        (stage / "unexpected").write_bytes(b"unexpected")
    elif damage == "symlink":
        target = stage / SECTOR_GENERATION_MEMBERS[0]
        target.unlink()
        target.symlink_to(source / SECTOR_GENERATION_MEMBERS[0])
    raw = json.dumps(metadata)
    if damage == "duplicate_json":
        raw = '{"schema":"bad",' + raw[1:]
    (stage / prepare.PREPARED_NAME).write_text(raw)
    with pytest.raises(ValueError):
        prepare.read_prepared(stage, generation_id="prepared-runtime-1", source_revision=REVISION)


def test_valid_transport_preserves_deferred_data_without_replay(prepared_candidate):
    stage, metadata = prepared_candidate
    composition, actual = prepare.read_prepared(stage,
        generation_id="prepared-runtime-1", source_revision=REVISION)
    assert actual == metadata
    assert prepare._encode_deferred_effects(composition.deferred_effects) == metadata["deferred_effects"]
    assert len(composition.deferred_effects) == composition.evidence["deferred_effect_count"]


def test_missing_native_chain_refuses_before_holdings(tmp_path, monkeypatch):
    monkeypatch.setattr(SectorHoldingsAdapter, "http_get",
        staticmethod(lambda *a, **k: pytest.fail("provider called before native prerequisite")))
    generations = tmp_path / "private/generations"
    generations.mkdir(parents=True)
    with pytest.raises(owner.SelectedGenerationAbsent):
        prepare.prepare_snapshot(repository_root=tmp_path, theme_root=tmp_path,
            generations_root=generations, generation_id="missing-native",
            source_revision=REVISION, clock=lambda: BUILT)
    assert not (generations / "sector/current.json").exists()


def test_exhausted_budget_preserves_staging_and_never_launches(monkeypatch, tmp_path):
    monkeypatch.setattr(owner.time, "monotonic", lambda: 100.0)
    calls = []
    orchestrator = _orch(tmp_path, runner=lambda *a, **k: calls.append((a, k)),
        deadline_monotonic=99.0)
    source = tmp_path / "stage.json"
    source.write_text('{"old":true}')
    result = orchestrator.command("bounded", ["unused"], timeout=10,
        outputs=((source, tmp_path / "public/out.json"),))
    assert result.status == "budget_exhausted"
    assert not calls and source.read_text() == '{"old":true}'


def test_elapsed_work_and_reserve_reduce_the_same_deadline(monkeypatch, tmp_path):
    tick = [10.0]
    monkeypatch.setattr(owner.time, "monotonic", lambda: tick[0])
    limits = []
    def runner(*a, **kw):
        limits.append(kw["timeout"])
        tick[0] += 13.0
        return SimpleNamespace(returncode=0, stdout="", stderr="")
    orchestrator = _orch(tmp_path, runner=runner, deadline_monotonic=30.0)
    first = orchestrator.command("first", ["fixture"], timeout=15, reserve_s=5)
    second = orchestrator.command("second", ["fixture"], timeout=15, reserve_s=5)
    assert first.status == "ok" and second.status == "budget_exhausted"
    assert limits == [12.0]
    assert orchestrator._command_deadline == 30.0


def test_quote_failure_names_dependencies_but_still_attempts_sector(monkeypatch, tmp_path):
    orchestrator = _orch(tmp_path)
    calls = []
    def module(name, *a, **kw):
        assert name == "full_quotes"
        calls.append((name, kw["timeout"]))
        result = owner.TaskResult(name, "failed", .1)
        orchestrator.results.append(result)
        return result
    def sector_snapshot(**kw):
        calls.append(("sector_generation", kw["timeout"]))
        result = owner.TaskResult("sector_generation", "ok", .1)
        orchestrator.results.append(result)
        return result
    monkeypatch.setattr(orchestrator, "module", module)
    monkeypatch.setattr(orchestrator, "sector_snapshot", sector_snapshot)
    orchestrator.snapshot()
    assert calls == [("full_quotes", 170), ("sector_generation", 80)]
    assert [r.name for r in orchestrator.results] == [
        "full_quotes", "intraday_quotes", "basket_us", "basket_hk", "sector_generation"]
    assert [r.status for r in orchestrator.results][1:4] == ["dependency_blocked"] * 3


def test_owner_supplied_deadline_is_not_restarted(monkeypatch, tmp_path):
    tick = [1.0]
    monkeypatch.setattr(owner.time, "monotonic", lambda: tick[0])
    orchestrator = _orch(tmp_path, deadline_monotonic=100.0,
        runner=lambda *a, **k: pytest.fail("expired budget launched a child"))
    tick[0] = 99.0
    orchestrator.snapshot()
    assert orchestrator._command_deadline == 100.0
    assert len(orchestrator.results) == 5
    assert orchestrator.results[0].status == "budget_exhausted"
    assert orchestrator.results[-1].status == "budget_exhausted"


def test_hanging_child_and_descendant_cannot_write_after_timeout(tmp_path):
    late = tmp_path / "late"
    child = "import time;from pathlib import Path;time.sleep(1);Path(" + repr(str(late)) + ").write_text('late')"
    program = "import subprocess,sys,time;subprocess.Popen([sys.executable,'-c'," + repr(child) + "]);time.sleep(30)"
    with pytest.raises(subprocess.TimeoutExpired):
        owner._run_command_group([sys.executable, "-c", program], cwd=tmp_path,
            env=os.environ.copy(), text=True, capture_output=True, timeout=.15, check=False)
    time.sleep(1.05)
    assert not late.exists()


def test_child_retains_original_shared_source_lock_through_cleanup(tmp_path):
    lock = tmp_path / "source.lock"
    ready = tmp_path / "ready"
    fd = os.open(lock, os.O_CREAT | os.O_RDWR, 0o600)
    fcntl.flock(fd, fcntl.LOCK_SH)
    failure = []
    program = ("import os,time;from pathlib import Path;os.fstat(" + str(fd) + ");Path("
               + repr(str(ready)) + ").write_text('ready');time.sleep(30)")
    def run():
        try:
            owner._run_command_group([sys.executable, "-c", program], cwd=tmp_path,
                env=os.environ.copy(), text=True, capture_output=True,
                timeout=.7, check=False, pass_fds=(fd,))
        except Exception as exc:
            failure.append(exc)
    thread = threading.Thread(target=run)
    thread.start()
    until = time.monotonic() + 3
    while not ready.exists() and time.monotonic() < until:
        time.sleep(.01)
    assert ready.exists()
    os.close(fd)  # Child must preserve the original open description independently.
    contender = os.open(lock, os.O_RDWR)
    try:
        with pytest.raises(BlockingIOError):
            fcntl.flock(contender, fcntl.LOCK_EX | fcntl.LOCK_NB)
        thread.join(timeout=4)
        assert not thread.is_alive()
        assert len(failure) == 1 and isinstance(failure[0], subprocess.TimeoutExpired)
        fcntl.flock(contender, fcntl.LOCK_EX | fcntl.LOCK_NB)
    finally:
        os.close(contender)


def test_uncertain_publication_is_retained_and_not_replayed(tmp_path):
    orchestrator = _orch(tmp_path,
        runner=lambda *a, **k: pytest.fail("original uncertain publication was reacquired"))
    publication = {"status": "uncertain", "generation_id": "original-attempt",
                   "content_id": None, "durability": "not_applicable"}
    orchestrator._prior_snapshot = {"tasks": [{
        "name": "sector_generation", "generation_publication": publication}]}
    result = orchestrator.sector_snapshot()
    assert result.status == "publication_unconfirmed"
    assert result.generation_publication == publication
    assert not (orchestrator.state_dir / "generations/sector/current.json").exists()


def test_parent_refuses_a_symlink_at_stage_root(prepared_candidate, tmp_path):
    source, _ = prepared_candidate
    linked = tmp_path / "linked-stage"
    linked.symlink_to(source, target_is_directory=True)
    with pytest.raises(ValueError, match="private_sector_stage_required"):
        prepare.read_prepared(linked, generation_id="prepared-runtime-1", source_revision=REVISION)


def test_parent_keeps_full_publication_reserve_after_stage_validation(
        prepared_candidate, tmp_path, monkeypatch):
    source, original = prepared_candidate
    tick = [1.0]
    monkeypatch.setattr(owner.time, "monotonic", lambda: tick[0])
    orchestrator = _orch(tmp_path, deadline_monotonic=100.0)
    def runner(args, **kwargs):
        stage = Path(args[args.index("--stage") + 1])
        shutil.copytree(source, stage, dirs_exist_ok=True)
        metadata = deepcopy(original)
        metadata["generation_id"] = args[args.index("--generation-id") + 1]
        (stage / prepare.PREPARED_NAME).write_text(json.dumps(metadata))
        tick[0] = 80.0
        return subprocess.CompletedProcess(args, 0, "prepared", "")
    orchestrator.runner = runner
    original_reader = prepare.read_prepared
    def read(*args, **kwargs):
        result = original_reader(*args, **kwargs)
        tick[0] = 86.0
        return result
    monkeypatch.setattr(prepare, "read_prepared", read)
    monkeypatch.setattr(orchestrator, "publish_sector_documents",
        lambda *a, **k: pytest.fail("publication began with less than its reserved budget"))
    result = orchestrator.sector_snapshot()
    assert result.status == "budget_exhausted", result.detail
    assert result.generation_publication is None
    assert not (orchestrator.state_dir / "generations/sector/current.json").exists()
