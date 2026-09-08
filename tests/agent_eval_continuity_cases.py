"""Regression for the September 8 stale Agent Evaluation continuation incident.

This exercises the existing Agent OS consumer, not a new reader or authority.
The dated handoff is a retrospective case; future program progress is not held
by an assertion that today's open implementation PRs must remain open.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest
import yaml

REPO = Path(__file__).resolve().parents[1]
STORE = REPO / "agentos"
KEY = "AGENT-EVAL-FABRIC"
WS = Path("workstreams") / f"WS-{KEY}.md"
OLD = Path("handoffs") / f"{KEY}-2026-09-01.md"
NEW = Path("handoffs") / f"{KEY}-2026-09-08.md"
DEC = Path("decisions/DEC-AGENT-EVAL-FABLE-COO-DELEGATION.md")


def record(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8").split("---", 2)[1])


@pytest.mark.parametrize("release", ["#6760", "#6713", "#332", "#333", "#336", "#337"])
def test_dated_handoff_preserves_protected_release_evidence(release: str) -> None:
    # Pin historical evidence, never the mutable status of a production workstream.
    assert (STORE / NEW).is_file(), "The corrected dated handoff is absent"
    assert release in json.dumps(record(STORE / NEW)["verified"])


def test_dated_handoff_does_not_repeat_superseded_release() -> None:
    assert (STORE / NEW).is_file(), "The corrected dated handoff is absent"
    historical = record(STORE / NEW)
    assert "Merge A2 (#6699" not in " ".join(historical["next_actions"])
    assert "Do not reopen #6699/#6711" in " ".join(historical["do_not_redo"])


def test_historical_handoff_names_both_live_source_gates_without_permission() -> None:
    assert (STORE / NEW).is_file(), "The latest recoverable handoff is still September 1"
    handoff = record(STORE / NEW)
    actions = " ".join(handoff["next_actions"])
    assert "Mastermind #162" in actions and "Mastermind #398" in actions
    assert "HOLD" in actions and "EFFECT_UNKNOWN" in " ".join(handoff["do_not_redo"])
    assert "6760" in json.dumps(handoff["verified"])
    assert handoff["unverified"], "Pending proof must not disappear during records repair"


def case_store(tmp_path: Path) -> Path:
    """Only the two dated handoffs: newer production work is not pinned by this case."""
    assert (STORE / NEW).is_file(), "Missing corrected continuation record"
    root = tmp_path / "agentos"
    for relative in (WS, OLD, NEW, DEC):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(STORE / relative, target)
    return root


def digests(root: Path) -> dict[str, str]:
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*.md")}


def compile_case(root: Path, *, mentioned: bool = False, budget: int = 8000) -> dict:
    target = [f"Continue WS:{KEY}"] if mentioned else ["--workstream", KEY]
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", GIT_OPTIONAL_LOCKS="0",
               MACRO_MASTERMIND_REPO=str(root / "absent-mastermind"),
               MACRO_TERMINAL_REPO=str(root / "absent-terminal"))
    args = [sys.executable, str(REPO / "scripts/agentos.py"), "compile-context",
            *target, "--root", str(root), "--now", "2026-09-08T23:59:00Z",
            "--budget", str(budget)]
    result = subprocess.run(args, cwd=REPO, env=env, text=True,
                            capture_output=True, timeout=45)
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)


def section(bundle: dict, key: str) -> dict:
    return next(s for s in bundle["sections"] if s["id"] == key)


@pytest.mark.parametrize("mentioned", [False, True])
def test_real_compiler_recovers_new_handoff_and_excludes_old(tmp_path, mentioned) -> None:
    root = case_store(tmp_path)
    before = digests(root)
    bundle = compile_case(root, mentioned=mentioned)
    items = section(bundle, "handoff")["items"]
    assert len(items) == 1 and items[0]["path"].endswith(str(NEW))
    assert "Mastermind #162" in items[0]["excerpt"]
    assert "Mastermind #398" in items[0]["excerpt"]
    assert "HOLD" in items[0]["excerpt"]
    assert any(x["path"].endswith(str(OLD)) and "older_handoff" in x["reason"]
               for x in bundle["excluded"])
    assert "not for permission" in section(bundle, "workstream")["title"]
    assert digests(root) == before, "Read-only recovery changed its source records"
    assert all(i["path"] and i["why_included"] for s in bundle["sections"] for i in s["items"])


def rewrite_record(path: Path, front: dict) -> None:
    body = path.read_text(encoding="utf-8").split("---", 2)[2]
    path.write_text("---\n" + yaml.safe_dump(front, sort_keys=False) + "---" + body,
                    encoding="utf-8")


def test_unknown_effect_is_visible_not_cured_by_a_new_handoff(tmp_path) -> None:
    root = case_store(tmp_path)
    current = record(root / WS)
    current["next_action"] = "EFFECT_UNKNOWN: reconcile the incumbent; no replay or replacement."
    wave = next(w for w in current["waves"] if w["id"] == "B3")
    wave["status"] = "in_progress"
    wave["next_action"] = current["next_action"]
    rewrite_record(root / WS, current)
    bundle = compile_case(root)
    text = "\n".join(i["excerpt"] for i in section(bundle, "workstream")["items"])
    assert "EFFECT_UNKNOWN" in text and "no replay or replacement" in text
    assert "in_progress" in text
    assert "never decides whether work may run" in section(bundle, "workstream")["authority_note"]


def test_malformed_new_handoff_never_silently_restores_obsolete_instructions(tmp_path) -> None:
    root = case_store(tmp_path)
    handoff = record(root / NEW)
    del handoff["unverified"]
    rewrite_record(root / NEW, handoff)
    bundle = compile_case(root)
    assert section(bundle, "handoff")["items"] == []
    assert any(x["path"].endswith(str(NEW)) and "malformed" in x["reason"]
               for x in bundle["excluded"])
    assert any(x["path"].endswith(str(OLD)) and "older_handoff" in x["reason"]
               for x in bundle["excluded"])


def test_later_workstream_completion_is_not_blocked_by_historical_case(tmp_path) -> None:
    root = case_store(tmp_path)
    current = record(root / WS)
    current["status"] = "done"
    current["next_action"] = "Historical fixture: all required outcome evidence accepted; archive."
    for wave in current["waves"]:
        wave["status"] = "done"
    rewrite_record(root / WS, current)
    bundle = compile_case(root)
    items = section(bundle, "workstream")["items"]
    row = next(item for item in items if item["kind"] == "workstream")
    assert row["status"] == "done"
    assert "all required outcome evidence accepted; archive" in row["excerpt"]
    assert "not for permission" in section(bundle, "workstream")["title"]


@pytest.mark.parametrize("runner_status, expected", [("in_progress", "blocked"), ("done", "ready")])
def test_e1_readiness_requires_the_runner_even_when_bridge_source_is_done(
    tmp_path: Path, runner_status: str, expected: str,
) -> None:
    """Completed bridge SOURCE cannot satisfy the still-held live runner dependency."""
    root = case_store(tmp_path)
    current = record(root / WS)
    current["status"] = "active"
    for wave in current["waves"]:
        if wave["id"] in {"B2", "B4", "C1"}:
            wave["status"] = "done"
        elif wave["id"] == "B3":
            wave["status"] = runner_status
        elif wave["id"] == "C2":
            wave["status"] = "todo"
    rewrite_record(root / WS, current)
    before = digests(root)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", GIT_OPTIONAL_LOCKS="0",
               MACRO_MASTERMIND_REPO=str(root / "absent-mastermind"),
               MACRO_TERMINAL_REPO=str(root / "absent-terminal"))
    result = subprocess.run(
        [sys.executable, str(REPO / "scripts/agentos.py"), "brief", "--root",
         str(root), "--json", "--no-remember", "--now", "2026-09-08T23:59:00Z"],
        cwd=REPO, env=env, text=True, capture_output=True, timeout=45,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    readiness = json.loads(result.stdout)["readiness"]
    e1 = next(row for row in readiness["records"]
              if row["workstream"] == KEY and row["wave"] == "C2")
    assert e1["state"] == expected
    if expected == "blocked":
        assert f"WS:{KEY}#B3" in e1["unmet_dependencies"]
    else:
        assert e1["unmet_dependencies"] == []
    assert digests(root) == before
