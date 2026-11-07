"""Synthetic model and unavailable runtime-CLI contracts.

Fake drivers and temporary fixtures only. The actual CLI main function is
called in process; no browser, proxy configuration or subprocess is used."""
from __future__ import annotations

import datetime
import json
import sys
import time
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.xguerrilla import cli, profiles, selector_shadow  # noqa: E402
from tools.xguerrilla.supervisor import ChildState, SimulationSupervisor  # noqa: E402


# ---------------------------------------------------------------------------
# fake driver — records calls so we can prove shadow never acts
# ---------------------------------------------------------------------------
class FakeDriver:
    def __init__(self, missing=()):
        self.missing = set(missing)
        self.calls = []

    def locate(self, spec):
        self.calls.append(("locate", spec))
        return spec.get("id") not in self.missing

    def screenshot(self, path):
        self.calls.append(("screenshot", path))
        Path(path).write_bytes(b"\x89PNG\r\n\x1a\nfake")
        return path


# ---------------------------------------------------------------------------
# profiles
# ---------------------------------------------------------------------------
def test_profile_round_trip_and_prune(tmp_path):
    store = profiles.SimulationProfileStore(tmp_path / "store")
    hd = Path(store.init("kid01", slot="aws-00", chrome_version="131.0"))
    profile = hd / "profile"
    assert profile.is_dir()
    manifest = json.loads((hd / "manifest.json").read_text())
    assert manifest["created_at"] and manifest["slot"] == "aws-00"
    assert manifest["chrome_version"] == "131.0" and "notes" in manifest

    cookies = profile / "Cookies"
    cookies.write_bytes(b"session=abc\x00\x01binary")
    (profile / "Local Storage").mkdir()
    (profile / "Local Storage" / "leveldb").write_bytes(b"local-state")
    before = {p.relative_to(hd).as_posix(): p.read_bytes()
              for p in hd.rglob("*") if p.is_file()}

    archive = store.snapshot("kid01")
    assert Path(archive).parent == tmp_path / "store" / "snapshots"

    cookies.write_bytes(b"corrupted")
    (profile / "stray").write_bytes(b"should vanish")
    store.restore("kid01", archive)

    after = {p.relative_to(hd).as_posix(): p.read_bytes()
             for p in hd.rglob("*") if p.is_file() and p.name != "manifest.json"}
    for rel, data in after.items():
        if rel in before:
            assert data == before[rel], rel
    assert (hd / "profile" / "stray").exists() is False
    assert store.verify("kid01")["ok"] is True

    for i in range(9):
        (profile / "Cookies").write_bytes(f"gen-{i}".encode())
        store.snapshot("kid01")
    archives = sorted((tmp_path / "store" / "snapshots").glob("kid01-*.tar.gz"))
    assert len(archives) == 7
    manifest = json.loads((hd / "manifest.json").read_text())
    assert len(manifest["snapshots"]) == 7
    assert store.describe("kid01")["snapshot_count"] == 7


def test_verify_detects_a_mutated_file(tmp_path):
    store = profiles.SimulationProfileStore(tmp_path / "store")
    hd = Path(store.init("kid02"))
    (hd / "profile" / "Cookies").write_bytes(b"original")
    store.snapshot("kid02")
    assert store.verify("kid02")["ok"] is True

    (hd / "profile" / "Cookies").write_bytes(b"tampered")
    result = store.verify("kid02")
    assert result["ok"] is False
    assert "profile/Cookies" in result["changed"]


def test_needs_login_flips_past_ttl():
    store = profiles.SimulationProfileStore(Path("/tmp/does-not-matter"))
    now = datetime.datetime.now(datetime.timezone.utc)
    assert store.needs_login("kid03", now - datetime.timedelta(days=20)) is False
    assert store.needs_login("kid03", now - datetime.timedelta(days=22)) is True
    assert store.needs_login("kid03", None) is True


# ---------------------------------------------------------------------------
# selector shadow
# ---------------------------------------------------------------------------
def test_shadow_quarantines_one_step_without_touching_state(tmp_path):
    driver = FakeDriver(missing={"post-button"})
    steps = [
        selector_shadow.Step("open-composer", {"id": "composer"}),
        selector_shadow.Step("post-button", {"id": "post-button"}),
    ]
    shots = tmp_path / "shots"
    result = selector_shadow.simulation_check(driver, steps, shots)

    assert result["ok"] is False
    assert result["drifted"] == ["post-button"]
    assert result["checked"] == 2
    assert Path(result["screenshots"]["post-button"]).exists()
    methods = {c[0] for c in driver.calls}
    assert methods == {"locate", "screenshot"}  # no click, no navigate, no type

    ledger = tmp_path / "store"
    selector_shadow.simulation_quarantine(ledger, "kid04", "post-button", "shadow drift")
    assert selector_shadow.simulation_is_quarantined(ledger, "kid04", "post-button") is True
    assert selector_shadow.simulation_is_quarantined(ledger, "kid04", "open-composer") is False

    sup = SimulationSupervisor(tmp_path / "state.db", personas={})
    sup.activate("kid04")
    ok, _ = sup.can_run("kid04", now=time.time())
    assert ok is True  # a quarantined STEP does not quarantine the CHILD
    sup.close()


# ---------------------------------------------------------------------------
# supervisor
# ---------------------------------------------------------------------------
def _supervisor(tmp_path):
    personas = {
        "lead1": SimpleNamespace(role="lead"),
        "conv1": SimpleNamespace(role="conversation"),
        "bc1": SimpleNamespace(role="broadcast"),
        "bc2": SimpleNamespace(role="broadcast"),
    }
    return SimulationSupervisor(tmp_path / "state.db", personas=personas)


def test_degraded_mode_drops_broadcast_children(tmp_path):
    sup = _supervisor(tmp_path)
    handles = ["lead1", "conv1", "bc1", "bc2"]
    assert sup.pick(handles, now=time.time()) == handles

    sup.degrade("worker box down")
    assert sup.pick(handles, now=time.time()) == ["lead1", "conv1"]
    assert sup.can_run("bc1", now=time.time())[0] is False
    assert "degraded" in sup.can_run("bc1", now=time.time())[1]

    sup.recover()
    assert sup.pick(handles, now=time.time()) == handles
    sup.close()


def test_stale_health_row_degrades_automatically(tmp_path):
    sup = _supervisor(tmp_path)
    t = time.time()
    sup.degrade("heartbeat stopped", now=t)
    sup.conn.execute("UPDATE health SET updated_at = ? WHERE id = 1", (t - 1000,))
    sup.conn.commit()

    status = sup.status(now=t)
    assert status["health"]["stale"] is True
    assert status["degraded"] is True
    assert sup.pick(["lead1", "bc1"], now=t) == ["lead1"]

    sup.recover(now=t)
    assert sup.pick(["lead1", "bc1"], now=t) == ["lead1", "bc1"]
    sup.close()


def test_cool_blocks_then_expires(tmp_path):
    sup = _supervisor(tmp_path)
    t = time.time()
    sup.cool("lead1", 5, now=t)
    assert sup.can_run("lead1", now=t)[0] is False
    assert "cooling" in sup.can_run("lead1", now=t)[1]
    assert sup.can_run("lead1", now=t + 4 * 60)[0] is False
    assert sup.can_run("lead1", now=t + 6 * 60)[0] is True
    sup.close()


def test_retire_is_sticky(tmp_path):
    sup = _supervisor(tmp_path)
    sup.retire("bc1", "challenge")
    assert sup.can_run("bc1", now=time.time()) == (False, "challenge")
    sup.activate("bc1")
    assert sup.can_run("bc1", now=time.time())[0] is True
    sup.close()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def test_cli_status_refuses_without_creating_state(tmp_path, capsys):
    db = tmp_path / "state.db"
    assert cli.main(["status", "--db", str(db),
                     "--personas", str(tmp_path / "none")]) == 3
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert payload["status"] == "runtime_binding_unavailable"
    assert payload["runtime_binding_available"] is False
    assert not db.exists()


def test_cli_degrade_and_recover_cannot_create_local_health(tmp_path, capsys):
    db = tmp_path / "s.db"
    for command in ("degrade", "recover"):
        assert cli.main([command, "--db", str(db),
                         "--personas", str(tmp_path / "none")]) == 3
        payload = json.loads(capsys.readouterr().out)
        assert payload["status"] == "runtime_binding_unavailable"
        assert payload["ok"] is False
    assert not db.exists()
