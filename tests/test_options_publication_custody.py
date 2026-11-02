"""Actual process exclusion and persistent UNKNOWN; no provider or target host."""
import hashlib
import os
from pathlib import Path
import subprocess
import sys

import pytest

from lib import options_publication_custody as custody

REPO = Path(__file__).resolve().parents[1]
CHILD = """
from pathlib import Path
import os,sys
from lib import options_publication_custody as c
c._native_state_root = lambda: Path(sys.argv[1])
try:
 with c.publication_custody():
  print('HELD', flush=True)
  if sys.argv[2]=='hold': sys.stdin.readline()
  if sys.argv[2]=='crash':
   c.begin_correction({'bucket':'test-bucket','key':'dated/key','input_sha256':'0'*64,'input_bytes':1})
   os._exit(0)
except c.PublicationCustodyError as e:
 print(str(e),flush=True)
 sys.exit(75)
"""


@pytest.fixture
def state(tmp_path, monkeypatch):
    p = tmp_path / "state"
    p.mkdir()
    monkeypatch.setattr(custody, "_native_state_root", lambda: p)
    return p


def child(state, mode, **kwargs):
    return subprocess.Popen([sys.executable, "-c", CHILD, str(state), mode],
        env={**os.environ, "PYTHONPATH": str(REPO)}, text=True,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)


def test_separate_process_and_cwd_cannot_take_parent_lock(state, tmp_path):
    with custody.publication_custody():
        ino = (state / "options-hub-publication.lock").stat().st_ino
        proc = child(state, "try", cwd=tmp_path)
        out, err = proc.communicate(timeout=10)
        assert proc.returncode == 75, err
        assert "publication_busy" in out
        with custody.publication_custody():
            custody.require_custody()
        # Nested exit did not release the outer descriptor.
        proc = child(state, "try", cwd=tmp_path)
        assert proc.communicate(timeout=10)[0].strip() == "publication_busy"
        assert proc.returncode == 75
    with custody.publication_custody():
        assert (state / "options-hub-publication.lock").stat().st_ino == ino


def test_child_holder_excludes_nightly_legacy_and_upload_before_effect(state, monkeypatch, tmp_path):
    from scripts import build_options_hub_nightly as nightly, repair_gex_history as repair
    called = []
    monkeypatch.setattr(nightly, "_run", lambda args: called.append("nightly"))
    monkeypatch.setattr(repair, "_publish_locked", lambda *a, **kw: called.append("repair"))
    monkeypatch.setattr(nightly, "_upload_r2_locked", lambda *a: called.append("upload"))
    monkeypatch.setattr(sys, "argv", ["nightly", "--publish"])
    proc = child(state, "hold", cwd=tmp_path)
    try:
        assert proc.stdout.readline().strip() == "HELD"
        for call in [nightly.main, lambda: repair._publish([("SPY", tmp_path / "x")]),
                     lambda: nightly._upload_r2(None, "test-bucket", tmp_path / "x", "options_hub/gex_history/SPY/2026-10-16.json")]:
            with pytest.raises(custody.PublicationCustodyError, match="publication_busy"):
                call()
        assert called == []
    finally:
        proc.communicate("release\n", timeout=10)
    assert proc.returncode == 0


def test_process_death_releases_lock_but_not_claim(state):
    proc = child(state, "crash")
    proc.communicate(timeout=10)
    assert proc.returncode == 0
    with pytest.raises(custody.PublicationCustodyError, match="installation_correction_unsettled"):
        with custody.installation_custody():
            pytest.fail("installer crossed unresolved correction")
    with custody.publication_custody():
        with pytest.raises(custody.PublicationCustodyError, match="unsettled"):
            custody.assert_target_available("test-bucket", "dated/key")
        custody.assert_target_available("test-bucket", "unrelated/key")
        with pytest.raises(custody.PublicationCustodyError, match="no_replay"):
            custody.begin_correction({})
        with pytest.raises(custody.PublicationCustodyError, match="acknowledged"):
            custody.verify_correction_readback(b"x")


def test_ack_only_releases_target_after_exact_readback_without_allowing_replay(state):
    body = b'{"native":"fixture"}'
    binding = dict(bucket="test-bucket", key="dated/key", input_bytes=len(body),
                   input_sha256=hashlib.sha256(body).hexdigest())
    with custody.publication_custody():
        custody.begin_correction(binding)
        custody.retain_correction_result({"status": "acknowledged"})
        with pytest.raises(custody.PublicationCustodyError, match="unsettled"):
            custody.assert_target_available("test-bucket", "dated/key")
        with pytest.raises(custody.PublicationCustodyError, match="mismatch"):
            custody.verify_correction_readback(b"different")
        custody.verify_correction_readback(body)
        custody.assert_target_available("test-bucket", "dated/key")
        with pytest.raises(custody.PublicationCustodyError, match="no_replay"):
            custody.begin_correction(binding)


def test_incomplete_claim_and_replaced_inode_fail_closed(state):
    with custody.publication_custody():
        (state / custody.OPERATION).mkdir()
        with pytest.raises(custody.PublicationCustodyError, match="unreadable"):
            custody.assert_target_available("test-bucket", "dated/key")
        lock = state / "options-hub-publication.lock"
        lock.rename(state / "retained-original-lock")
        lock.touch()
        with pytest.raises(custody.PublicationCustodyError, match="identity_changed"):
            custody.require_custody()


def test_missing_native_state_never_constructs_a_replacement(tmp_path, monkeypatch):
    p = tmp_path / "absent"
    monkeypatch.setattr(custody, "_native_state_root", lambda: p)
    with pytest.raises(custody.PublicationCustodyError, match="unavailable"):
        with custody.publication_custody():
            pytest.fail("unavailable native state admitted")
    assert not p.exists()


def test_correction_requires_outer_interval_and_preserves_unknown_on_receipt_failure(state, monkeypatch):
    from scripts import repair_gex_history as repair
    prepared = dict(status="prepared", bucket="test-bucket", key="dated/key", wrapper_invocations=0)
    calls = []
    def core(*args, apply=False, **kwargs):
        if not apply:
            return dict(prepared)
        calls.append("put")
        return dict(prepared, status="acknowledged", wrapper_invocations=1)
    monkeypatch.setattr(repair, "_correct_archive_artifact_locked", core)
    binding = dict(bucket="test-bucket", key="dated/key", input_bytes=1, input_sha256="0"*64)
    refused = repair.correct_archive_artifact(Path("fixture"), binding, apply=True, bucket="test-bucket")
    assert refused["reason"] == "publication_custody_required"
    assert refused["status"] == "not_attempted" and calls == []
    with custody.publication_custody():
        def failed_save(result):
            raise OSError("private path must not leak")
        monkeypatch.setattr(custody, "retain_correction_result", failed_save)
        result = repair.correct_archive_artifact(Path("fixture"), binding, apply=True, bucket="test-bucket")
        assert result["status"] == "unknown" and result["wrapper_invocations"] == 1
        assert result["reason"] == "publication_custody_io_failure"
        assert calls == ["put"]
        with pytest.raises(custody.PublicationCustodyError, match="unsettled"):
            custody.assert_target_available("test-bucket", "dated/key")


def test_adoption_barrier_blocks_publication_but_not_nonpublishing_installer(state):
    (state / "options-hub-adoption.pending").write_text("retained bootstrap identity")
    with pytest.raises(custody.PublicationCustodyError, match="adoption_fenced"):
        with custody.publication_custody():
            pytest.fail("publisher crossed adoption fence")
    with custody.installation_custody():
        custody.require_custody(installation=True)
        with pytest.raises(custody.PublicationCustodyError, match="role_mismatch"):
            with custody.publication_custody():
                pytest.fail("installer token authorized publication")
    assert (state / "options-hub-adoption.pending").exists()


def test_dispatch_admission_is_durable_once_and_binding_exact(state):
    binding = dict(bucket="test-bucket", key="dated/key", input_bytes=1, input_sha256="0"*64)
    with custody.publication_custody():
        with pytest.raises(custody.PublicationCustodyError, match="not_admitted"):
            custody.mark_correction_dispatch(binding)
        custody.begin_correction(binding)
        with pytest.raises(custody.PublicationCustodyError, match="not_admitted"):
            custody.mark_correction_dispatch(dict(binding, key="other/key"))
        custody.mark_correction_dispatch(binding)
        with pytest.raises(custody.PublicationCustodyError, match="not_admitted"):
            custody.mark_correction_dispatch(binding)
    with custody.publication_custody():
        with pytest.raises(custody.PublicationCustodyError, match="unsettled"):
            custody.assert_target_available("test-bucket", "dated/key")


@pytest.mark.parametrize("module", ["scripts.build_options_hub_nightly", "scripts.repair_gex_history"])
def test_new_direct_module_entry_honors_adoption_barrier(state, module):
    (state / "options-hub-adoption.pending").touch()
    code = '''
import importlib,sys
from pathlib import Path
from lib import options_publication_custody as c
c._native_state_root=lambda:Path(sys.argv[1])
try:
 module = importlib.import_module(sys.argv[2])
 module.main()
except c.PublicationCustodyError as exc:
 print(str(exc))
 sys.exit(75)
raise AssertionError('new legacy/module entry crossed barrier')
'''
    result = subprocess.run([sys.executable, "-c", code, str(state), module],
        env={**os.environ, "PYTHONPATH": str(REPO)}, capture_output=True, text=True, timeout=20)
    assert result.returncode == 75, result.stderr
    assert result.stdout.strip() == "publication_adoption_fenced"


def test_unrelated_upload_reuses_transport_without_native_custody(tmp_path, monkeypatch):
    from scripts import build_options_hub_nightly as nightly
    monkeypatch.setattr(custody, "_native_state_root", lambda: tmp_path / "absent-native-state")
    seen = []
    class Client:
        def upload_file(self, *args, **kwargs):
            seen.append(args[2])
    assert nightly._upload_r2(Client(), "test-bucket", tmp_path / "fixture", "options_hub/agg_greeks/SPY.json")
    assert seen == ["options_hub/agg_greeks/SPY.json"]
    with pytest.raises(custody.PublicationCustodyError, match="unavailable"):
        nightly._upload_r2(Client(), "test-bucket", tmp_path / "fixture", "options_hub/gex_history/SPY/2026-10-16.json")
    assert len(seen) == 1


@pytest.mark.parametrize("publish", [False, True])
def test_actual_legacy_main_contention_precedes_local_apply(state, tmp_path, monkeypatch, publish):
    from scripts import repair_gex_history as repair
    archive = tmp_path / "gex_history"
    snapshot = archive / "SPY" / "2026-10-16.json"
    snapshot.parent.mkdir(parents=True)
    snapshot.write_text("original")
    monkeypatch.setattr(repair, "HIST_DIR", archive)
    effects = []
    def changed_before_lock(*args, **kwargs):
        effects.append("local-write")
        snapshot.write_text("changed-before-lock")
        return dict(n=1, changed=1, impossible=0, skipped=0, paths=[snapshot])
    monkeypatch.setattr(repair, "repair_root", changed_before_lock)
    monkeypatch.setattr(repair, "_publish", lambda *a, **kw: effects.append("publish"))
    proc = child(state, "hold")
    try:
        assert proc.stdout.readline().strip() == "HELD"
        with pytest.raises(custody.PublicationCustodyError, match="publication_busy"):
            repair.main(["--roots", "SPY", "--apply"] + (["--publish"] if publish else []))
        assert snapshot.read_text() == "original" and effects == []
    finally:
        proc.communicate("release\n", timeout=10)


def test_direct_repair_apply_contention_and_dry_run(state, tmp_path, monkeypatch):
    from scripts import repair_gex_history as repair
    effects = []
    def run(*args, apply=False, **kwargs):
        if apply:
            effects.append("write")
        return {"dry_run": not apply}
    monkeypatch.setattr(repair, "_repair_root_locked", run)
    proc = child(state, "hold")
    try:
        assert proc.stdout.readline().strip() == "HELD"
        assert repair.repair_root("SPY", None, apply=False) == {"dry_run": True}
        with pytest.raises(custody.PublicationCustodyError, match="publication_busy"):
            repair.repair_root("SPY", None, apply=True)
        assert effects == []
    finally:
        proc.communicate("release\n", timeout=10)


def test_unsettled_target_blocks_actual_local_repair_and_nightly_write(state, tmp_path, monkeypatch):
    import pandas as pd
    from scripts import repair_gex_history as repair, build_options_hub_nightly as nightly
    archive = tmp_path / "gex_history"
    snapshot = archive / "SPY" / "2026-10-16.json"
    snapshot.parent.mkdir(parents=True)
    snapshot.write_text("original")
    monkeypatch.setattr(repair, "HIST_DIR", archive)
    monkeypatch.setattr(repair, "_read_year", lambda *a: pd.DataFrame({"date": ["2026-10-16"]}))
    binding = dict(bucket="test-bucket", key="options_hub/gex_history/SPY/2026-10-16.json",
                   input_bytes=1, input_sha256="0"*64)
    with custody.publication_custody():
        custody.begin_correction(binding)
        with pytest.raises(custody.PublicationCustodyError, match="local_target_unsettled"):
            repair.repair_root("SPY", None, apply=True)
        with pytest.raises(custody.PublicationCustodyError, match="local_target_unsettled"):
            nightly._write_json(snapshot, {"would": "overwrite"})
        assert snapshot.read_text() == "original"
        other = snapshot.with_name("2026-10-15.json")
        nightly._write_json(other, {"eligible": True})
        assert other.exists()


def test_native_nightly_no_publish_is_still_an_effectful_writer(state, monkeypatch):
    from scripts import build_options_hub_nightly as nightly
    monkeypatch.setattr(nightly, "_REPO", (Path.home() / "optionshub-ops-wt").resolve())
    effects = []
    monkeypatch.setattr(nightly, "_run", lambda args: effects.append("local-write"))
    monkeypatch.setattr(sys, "argv", ["nightly", "--no-publish"])
    proc = child(state, "hold")
    try:
        assert proc.stdout.readline().strip() == "HELD"
        with pytest.raises(custody.PublicationCustodyError, match="publication_busy"):
            nightly.main()
        assert effects == []
    finally:
        proc.communicate("release\n", timeout=10)
