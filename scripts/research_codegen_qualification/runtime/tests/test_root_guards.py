"""Installer review probes; only invented temporary files and benign /bin/cat."""
from pathlib import Path
import os
import pytest
import test_runsc_install as original
m = original.mod


def test_cumulative_output_charges_shared_budget(tmp_path):
    payload = tmp_path / "plain"; payload.write_bytes(b"x" * 10)
    budget = m.Budget(combined_output_bytes=15, rollback_reserve_output_bytes=0)
    runner = m.BoundedRunner(budget, binaries=frozenset({"/bin/cat"}))
    assert len(runner.run(["/bin/cat", str(payload)])["out"]) == 10
    assert budget.spent_output_bytes == 10
    second = runner.run(["/bin/cat", str(payload)])
    assert second["truncated"] and len(second["out"]) == 5
    assert budget.spent_output_bytes == 15


def test_incomplete_observation_freezes_before_next_effect():
    fx = original.Fixture()
    try:
        fx.runner.script(out=b"parseable prefix", truncated=True)
        engine = fx.engine()
        with pytest.raises(m.InstallError):
            engine._run([m.DOCKER_BIN, "info"])
        assert engine.frozen
        with pytest.raises(m.InstallError):
            engine._run([m.SUDO_BIN, "-n", m.SYSTEMCTL_BIN, "reload", "docker.service"])
        assert len(fx.runner.calls) == 1
    finally: fx.close()


def test_real_runner_and_engine_share_one_budget():
    budget = m.Budget()
    runner = m.BoundedRunner(budget)
    engine = m.InstallEngine(m.Layout.under_root("/invented-not-used"), runner)
    assert engine.budget is budget


def test_existing_runtime_mapping_must_remain_identical():
    fx = original.Fixture()
    try:
        engine = fx.engine(); engine.default_runtime_before = "runc"
        engine.runtime_mapping_before = {"runc": {"path": "runc"}, "nvidia": {"path": "original"}}
        state = {"service": {"ActiveState": "active"}, "default": "runc",
                 "runtimes": {"runc": {"path": "runc"}, "nvidia": {"path": "changed"},
                              "rf-runsc": engine._expected_entry()}}
        assert not engine._state_verified(state, expect_rf=True)
    finally: fx.close()


def test_every_docker_call_uses_owned_anonymous_configuration():
    fx = original.Fixture()
    try:
        original.script_happy(fx.runner, polls_before_rf=0)
        code, _ = fx.engine().execute(fx.binding_path, fx.binding_sha)
        assert code == m.EXIT_OK
        expected = fx.scratch + "/docker-client"
        calls = [c["argv"] for c in fx.runner.calls if c["binary"] == m.DOCKER_BIN]
        assert calls and all(a[3:5] == ["--config", expected] for a in calls)
        import json
        assert json.loads(Path(expected, "config.json").read_bytes()) == {"auths": {"https://index.docker.io/v1/": {}}}
        assert os.stat(expected).st_mode & 0o777 == 0o700
        assert os.stat(Path(expected, "config.json")).st_mode & 0o777 == 0o600
    finally: fx.close()


def test_private_receipt_handles_short_writes(tmp_path, monkeypatch):
    actual = os.write
    monkeypatch.setattr(m.os, "write", lambda fd, raw: actual(fd, raw[:3]))
    path = tmp_path / "receipt"
    m.write_private_file(str(path), b"full-required-evidence", 0o600, None, lambda *_: None)
    assert path.read_bytes() == b"full-required-evidence"


def test_validation_refusal_preserves_staged_evidence_without_cleanup():
    fx = original.Fixture()
    try:
        engine = fx.engine(); engine.binding = m.Binding(fx.binding_dict, original.TEST_CONTRACT)
        def refuse(*args, **kwargs):
            fx.runner.freeze()
            raise m.InstallError("PERMISSION_REFUSED_TEST")
        fx.runner.run = refuse
        with pytest.raises(m.InstallError): engine._validate_with_dockerd(b"{}")
        assert engine.frozen
        assert Path(fx.scratch, "validate-candidate.json").read_bytes() == b"{}"
    finally: fx.close()


def test_published_bundle_is_reported_if_directory_sync_fails(monkeypatch):
    fx = original.Fixture()
    try:
        engine = fx.engine(); engine.binding = m.Binding(fx.binding_dict, original.TEST_CONTRACT)
        stage = engine._stage_bundle()
        monkeypatch.setattr(m, "fsync_dir", lambda *_: (_ for _ in ()).throw(OSError("sync unsettled")))
        with pytest.raises(OSError): engine._publish_bundle(stage)
        assert os.path.isdir(fx.version_dir())
        assert engine.bundle_created
    finally: fx.close()


def test_expired_budget_blocks_filesystem_publication():
    fx = original.Fixture()
    try:
        engine = fx.engine(); engine.binding = m.Binding(fx.binding_dict, original.TEST_CONTRACT)
        stage = engine._stage_bundle()
        fx.clock.bump(1000)
        with pytest.raises(m.InstallError, match="BUDGET_EXCEEDED"):
            engine._publish_bundle(stage)
        assert not os.path.exists(fx.version_dir())
        assert os.path.exists(stage)
    finally: fx.close()


def test_publication_permission_denial_freezes_followup():
    fx = original.Fixture()
    try:
        engine = fx.engine(); engine.binding = m.Binding(fx.binding_dict, original.TEST_CONTRACT)
        stage = engine._stage_bundle()
        def refuse(*_): raise PermissionError("fixture denial")
        engine.rename_fn = refuse
        with pytest.raises((m.InstallError, PermissionError)): engine._publish_bundle(stage)
        assert engine.frozen
        assert os.path.exists(stage)
    finally: fx.close()


def test_settlement_changed_daemon_identity_cannot_qualify(monkeypatch):
    fx = original.Fixture()
    try:
        engine = fx.engine(); engine.daemon_id = "original-daemon"
        engine.socket_facts = {"device": 1, "inode": 2}
        monkeypatch.setattr(engine, "socket_inspector", lambda *_: engine.socket_facts)
        monkeypatch.setattr(engine, "_service_facts", lambda *_: {"ActiveState": "active"})
        monkeypatch.setattr(engine, "_runtime_mapping", lambda *_: {})
        monkeypatch.setattr(engine, "_info_field", lambda fmt, *args: "replacement-daemon" if fmt == "{{.ID}}" else "runc")
        with pytest.raises(m.InstallError, match="DAEMON_IDENTITY_CHANGED"):
            engine._poll_state("main")
        assert engine.frozen
    finally: fx.close()


def test_existing_root_docker_group_socket_allowed_world_write_denied(tmp_path):
    import socket, tempfile
    # AF_UNIX sockaddr paths are short on macOS; only ephemeral fixture bytes here.
    with tempfile.TemporaryDirectory(prefix='rf-sock-') as root:
        path = Path(root) / 's'
        with socket.socket(socket.AF_UNIX) as sock:
            sock.bind(str(path)); path.chmod(0o660)
            facts = m.inspect_docker_socket(str(path), os.getuid())
            assert facts['mode'] == 0o660 and facts['inode'] == path.stat().st_ino
            path.chmod(0o666)
            with pytest.raises(m.InstallError, match='SOCKET_MODE_UNSAFE'):
                m.inspect_docker_socket(str(path), os.getuid())


def test_disk_admission_works_before_new_version_parent_exists():
    import shutil
    fx = original.Fixture()
    try:
        original.script_happy(fx.runner, polls_before_rf=0)
        checked = []
        def free(path):
            checked.append(path)
            return shutil.disk_usage(path).free
        code, receipt = fx.engine(disk_free_fn=free).execute(fx.binding_path, fx.binding_sha)
        assert code == m.EXIT_OK, receipt['status']
        assert checked and all(os.path.isdir(p) for p in checked)
    finally: fx.close()
