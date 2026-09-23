"""Pending CI holds release; hook advice must not prohibit independent work."""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("hold_progress", ROOT / "scripts/ship_loop_hold_wrapper.py")
WRAPPER = importlib.util.module_from_spec(spec)
spec.loader.exec_module(WRAPPER)


@pytest.mark.parametrize("branch,kind", [("claude/task", "ordinary_unmerged"), ("sol/task", "sol_authority")])
def test_pending_advice_preserves_hold_without_a_foreground_stop(branch, kind):
    probe = dict(number=12, branch=branch, head="a" * 40, candidate_kind=kind,
                 status="pending", pending=["ci-pack"], red=[], passed=[])
    result = WRAPPER._hold_block(probe)
    assert result["decision"] == "block"
    reason = result["reason"]
    assert "CI holds release, not independent authorized work" in reason
    assert "existing verified check observer" in reason
    assert "does not establish that a watcher exists" in reason
    assert "do not re-poll CI" in reason
    assert "Do not rename the branch" in reason
    assert "arm merge-on-green, merge, render" in reason
    assert "terminal PARKED" in reason
    assert "watcher only" not in reason


@pytest.mark.parametrize("status", ["pending", "red"])
def test_stop_entrypoint_emits_nonterminal_hold_and_never_relays(monkeypatch, capsys, status):
    payload = {"hook_event_name": "Stop", "cwd": str(ROOT)}
    probe = dict(number=12, branch="claude/task", head="a" * 40,
                 candidate_kind="ordinary_unmerged", status=status,
                 pending=["ci-pack"] if status == "pending" else [],
                 red=["ci-pack"] if status == "red" else [], passed=[])
    monkeypatch.setattr(WRAPPER, "_read_payload", lambda: (payload, b"{}"))
    monkeypatch.setattr(WRAPPER, "_load_guard", lambda _: object())
    monkeypatch.setattr(WRAPPER, "_hold_probe", lambda *_: probe)
    monkeypatch.setattr(WRAPPER, "_relay", lambda *_: pytest.fail("held Stop must not relay"))
    monkeypatch.setattr(WRAPPER.sys, "argv", ["wrapper"])
    WRAPPER.main()
    result = json.loads(capsys.readouterr().out)
    assert set(result) == {"decision", "reason"}
    assert result["decision"] == "block"
    assert "CI holds release, not independent authorized work" in result["reason"]
    assert "WATCH_ARMED" not in result["reason"]


@pytest.mark.parametrize("path", ["AGENTS.md", "CLAUDE.md"])
def test_native_entrypoints_keep_ci_wait_action_scoped(path):
    source = (ROOT / path).read_text()
    assert "CI holds release, not independent authorized work" in source
    assert "already-authorized, path/dependency-disjoint" in source
    assert "no new Stop-hook exit or release permission" in source
