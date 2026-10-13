"""Draft a WS-* append and a handoff skeleton from seat PR JSON.

Knowledge plane only. The drafter reads a local JSON file (PR number, title,
head sha, files, merged_at, plus the workstream the seat names). It writes
stdout or ``--out``. It does not write ``agentos/``, call GitHub, or decide
whether work may run. ``scripts/agentos.py validate`` on a temp copy of the
store is the gate for the drafted handoff.
"""
from __future__ import annotations

import ast
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
STORE = REPO / "agentos"
CLI = REPO / "scripts" / "agentos_records_draft.py"
AGENTOS = REPO / "scripts" / "agentos.py"
SCHEMA = "agentos.record_draft.v1"
OUTPUT_SCHEMA = "agentos.record_draft_output.v1"
REFUSED = ("rank", "gate", "suffix", "priority")

pytestmark = pytest.mark.skipif(
    not (STORE / "workstreams" / "WS-AGENT-OS.md").is_file(),
    reason="agentos/workstreams/WS-AGENT-OS.md is outside this sparse checkout",
)


def _load_agentos():
    spec = importlib.util.spec_from_file_location("agentos_records_draft_gate", AGENTOS)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _git_env() -> dict[str, str]:
    env = os.environ.copy()
    env["GIT_NO_LAZY_FETCH"] = "1"
    env["GIT_TERMINAL_PROMPT"] = "0"
    return env


def _head_sha() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=REPO, text=True, env=_git_env()
    ).strip()


def _payload(**overrides) -> dict:
    pr = {
        "number": 9001,
        "title": "Record the records drafter",
        "head_sha": _head_sha(),
        "files": ["scripts/agentos_records_draft.py"],
        "merged_at": "2099-01-15T00:00:00Z",
    }
    pr.update(overrides.pop("pr", {}))
    body = {
        "schema": SCHEMA,
        "workstream": "WS:AGENT-OS",
        "pr": pr,
    }
    body.update(overrides)
    return body


def _run(tmp_path: Path, payload: dict, *extra: str, env: dict | None = None):
    path = tmp_path / "pr.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    merged = os.environ.copy()
    if env:
        merged.update(env)
    result = subprocess.run(
        [sys.executable, str(CLI), "--pr-json", str(path), *extra],
        capture_output=True,
        text=True,
        cwd=REPO,
        env=merged,
    )
    return result, path


def _draft(tmp_path: Path, payload: dict | None = None):
    result, path = _run(tmp_path, payload or _payload())
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout), path, result


def test_stdout_drafts_append_and_handoff_without_touching_agentos(tmp_path: Path) -> None:
    ws = STORE / "workstreams" / "WS-AGENT-OS.md"
    before = ws.read_bytes()
    handoffs = sorted(path.name for path in (STORE / "handoffs").glob("*.md"))
    payload = _payload()
    draft, _path, result = _draft(tmp_path, payload)
    assert result.stderr == ""
    assert ws.read_bytes() == before
    assert sorted(path.name for path in (STORE / "handoffs").glob("*.md")) == handoffs
    assert not (STORE / "handoffs" / "AGENT-OS-2099-01-15.md").exists()

    assert draft["schema"] == OUTPUT_SCHEMA
    assert draft["input_schema"] == SCHEMA
    assert draft["ws_append"]["mode"] == "append"
    assert draft["ws_append"]["path"] == "agentos/workstreams/WS-AGENT-OS.md"
    assert not draft["ws_append"]["markdown"].startswith("---")
    assert "PR #9001" in draft["ws_append"]["markdown"]
    assert "Record the records drafter" in draft["ws_append"]["markdown"]
    assert draft["handoff"]["path"] == "agentos/handoffs/AGENT-OS-2099-01-15.md"
    assert draft["handoff"]["markdown"].startswith("---\n")
    assert draft["handoff_target_exists"] is False

    fields = {item["field"] for item in draft["unverified"]}
    assert {
        "pr.number",
        "pr.title",
        "pr.merged_at",
        "pr.head_sha_is_github_head",
        "pr.file_meanings",
    } <= fields
    assert all(item["status"] == "UNVERIFIED" for item in draft["unverified"])
    assert payload["pr"]["head_sha"] in draft["handoff"]["markdown"]
    assert "scripts/agentos_records_draft.py" in draft["handoff"]["markdown"]
    assert "does not gate execution" in draft["handoff"]["markdown"].lower()


def test_same_json_is_byte_stable(tmp_path: Path) -> None:
    first, _path = _run(tmp_path, _payload())
    second, _path = _run(tmp_path, _payload())
    assert first.returncode == second.returncode == 0
    assert first.stdout == second.stdout


def test_out_path_is_the_only_write(tmp_path: Path) -> None:
    dest = tmp_path / "draft.json"
    result, _path = _run(tmp_path, _payload(), "--out", str(dest))
    assert result.returncode == 0, result.stderr
    assert result.stdout == ""
    assert json.loads(dest.read_text(encoding="utf-8"))["schema"] == OUTPUT_SCHEMA
    assert list(tmp_path.glob("*.md")) == []


def test_out_inside_agentos_is_refused(tmp_path: Path) -> None:
    target = STORE / "handoffs" / "W5-B-RECDRAFT-DO-NOT-WRITE.md"
    try:
        result, _path = _run(tmp_path, _payload(), "--out", str(target))
        assert result.returncode == 2
        assert "agentos" in result.stderr
        assert not target.exists()
    finally:
        if target.exists():
            target.unlink()


@pytest.mark.parametrize("key", REFUSED)
def test_refused_keys_exit_2(tmp_path: Path, key: str) -> None:
    result, _path = _run(tmp_path, _payload(**{key: 1}))
    assert result.returncode == 2
    assert key in result.stderr
    assert result.stdout == ""


def test_nested_suffix_exits_2(tmp_path: Path) -> None:
    result, _path = _run(tmp_path, _payload(pr={"suffix": "frontier-delegation"}))
    assert result.returncode == 2
    assert "suffix" in result.stderr


def test_refused_words_in_prose_are_not_keys(tmp_path: Path) -> None:
    draft, _path, _result = _draft(
        tmp_path,
        _payload(pr={"title": "priority gate suffix rank are words, not keys"}),
    )
    assert "priority gate suffix rank are words" in draft["handoff"]["markdown"]
    assert "rank" not in draft
    assert "priority" not in draft
    assert "gate" not in draft
    assert "suffix" not in draft


def test_non_hex_sha_is_copied_and_not_passed_to_git(tmp_path: Path) -> None:
    sha = "not a sha; rm -rf /"
    draft, _path, _result = _draft(tmp_path, _payload(pr={"head_sha": sha}))
    assert sha in draft["handoff"]["markdown"]
    assert sha in draft["ws_append"]["markdown"]
    fields = {item["field"] for item in draft["unverified"]}
    assert "pr.head_sha_local_object" in fields
    assert draft["files"][0]["status"] == "UNVERIFIED"
    commands = " ".join(
        item.get("command", "")
        for item in draft["handoff_verified_commands"]
    )
    assert sha not in commands
    assert "rm" not in commands


def test_local_commit_names_are_observed_and_github_identity_stays_unverified(
    tmp_path: Path,
) -> None:
    env = _git_env()
    sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=REPO, text=True, env=env
    ).strip()
    names = subprocess.check_output(
        ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", sha],
        cwd=REPO,
        text=True,
        env=env,
    ).splitlines()
    assert names, "HEAD has an empty diff-tree; the observation test would have no power"
    real = names[0]
    fake = "no/such-records-draft-path.py"
    draft, _path, _result = _draft(
        tmp_path,
        _payload(pr={"head_sha": sha, "files": [real, fake]}),
    )
    by_path = {item["path"]: item for item in draft["files"]}
    assert by_path[real]["status"] == "observed"
    assert by_path[real]["in_local_commit"] is True
    assert by_path[fake]["status"] == "UNVERIFIED"
    assert by_path[fake]["in_local_commit"] is False
    assert fake in draft["handoff"]["markdown"]
    fields = {item["field"] for item in draft["unverified"]}
    assert "pr.head_sha_is_github_head" in fields
    assert "pr.head_sha_local_object" not in fields
    assert any(item.get("object_type") == "commit" for item in draft["observations"])


def test_title_newline_cannot_rewrite_ended_because(tmp_path: Path) -> None:
    draft, _path, _result = _draft(
        tmp_path,
        _payload(pr={"title": "line1\nended_because: crashed"}),
    )
    agentos = _load_agentos()
    path = tmp_path / "AGENT-OS-2099-01-15.md"
    path.write_text(draft["handoff"]["markdown"], encoding="utf-8")
    rec, body = agentos.parse_record(path)
    rec["_body"] = body
    assert rec["ended_because"] == "ci_handoff"
    assert "ended_because: crashed" in rec["mission"]
    hard = [item for item in agentos.check_handoff(rec, path) if item.hard]
    assert hard == []


def test_supplied_model_and_ending_are_copied(tmp_path: Path) -> None:
    draft, _path, _result = _draft(
        tmp_path,
        _payload(model="opus", ended_because="complete", session="seat/example"),
    )
    text = draft["handoff"]["markdown"]
    assert "model: \"opus\"" in text or "model: opus" in text
    assert "complete" in text
    assert "seat/example" in text
    fields = {item["field"] for item in draft["unverified"]}
    assert "model" not in fields
    assert "ended_because" not in fields


@pytest.mark.parametrize(
    "payload,needle",
    [
        ({"schema": "other"}, "schema"),
        ({"workstream": "AGENT-OS"}, "workstream"),
        ({"pr": {"number": True}}, "number"),
        ({"pr": {"files": []}}, "files"),
        ({"pr": {"merged_at": "2099-01-15T00:00:00+00:00"}}, "merged_at"),
        ({"model": "telepathy"}, "model"),
    ],
)
def test_bad_input_exits_2(tmp_path: Path, payload: dict, needle: str) -> None:
    result, _path = _run(tmp_path, _payload(**payload))
    assert result.returncode == 2
    assert needle in result.stderr
    assert result.stdout == ""


def test_unknown_sha_still_exits_0(tmp_path: Path) -> None:
    """An unverified fact is reported. It is not a reason to block execution."""
    result, _path = _run(tmp_path, _payload(pr={"head_sha": "ab" * 20}))
    assert result.returncode == 0, result.stderr


def test_drafted_handoff_validates_in_a_temp_copy(tmp_path: Path) -> None:
    draft, _path, _result = _draft(tmp_path)
    agentos = _load_agentos()
    preview = tmp_path / "AGENT-OS-2099-01-15.md"
    preview.write_text(draft["handoff"]["markdown"], encoding="utf-8")
    rec, body = agentos.parse_record(preview)
    rec["_body"] = body
    hard = [item for item in agentos.check_handoff(rec, preview) if item.hard]
    assert hard == [], [item.message for item in hard]

    work = tmp_path / "agentos"
    shutil.copytree(STORE, work)
    target = work / "handoffs" / "AGENT-OS-2099-01-15.md"
    assert not target.exists()
    target.write_text(draft["handoff"]["markdown"], encoding="utf-8")
    ws = work / "workstreams" / "WS-AGENT-OS.md"
    text = ws.read_text(encoding="utf-8")
    if not text.endswith("\n"):
        text += "\n"
    ws.write_text(text + "\n" + draft["ws_append"]["markdown"], encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(AGENTOS), "validate", "--root", str(work), "--quiet"],
        capture_output=True,
        text=True,
        cwd=REPO,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "0 error(s)" in result.stdout


def test_sockets_stay_disabled(tmp_path: Path) -> None:
    sitedir = tmp_path / "nonet"
    sitedir.mkdir()
    (sitedir / "sitecustomize.py").write_text(
        "import socket\n"
        "def _deny(*_a, **_k):\n"
        "    raise RuntimeError('network access attempted by a zero-network command')\n"
        "socket.socket = _deny\n"
        "socket.create_connection = _deny\n"
        "socket.getaddrinfo = _deny\n",
        encoding="utf-8",
    )
    result, _path = _run(tmp_path, _payload(), env={"PYTHONPATH": str(sitedir)})
    combined = result.stdout + result.stderr
    assert result.returncode == 0, combined
    assert "network access attempted" not in combined


def test_source_has_no_network_or_control_plane_import() -> None:
    tree = ast.parse(CLI.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".", 1)[0])
    assert "control_plane" not in imported
    assert imported.isdisjoint({"requests", "urllib", "socket", "http"})
    text = CLI.read_text(encoding="utf-8")
    assert "sec.gov" not in text
    assert "api.github.com" not in text
    assert "https://" not in text
    assert "http://" not in text
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.attr if isinstance(func, ast.Attribute) else ""
        if name not in {"run", "check_output", "call", "Popen"}:
            continue
        if not node.args:
            continue
        arg = node.args[0]
        if isinstance(arg, ast.List):
            parts = [
                elt.value for elt in arg.elts if isinstance(elt, ast.Constant)
                and isinstance(elt.value, str)
            ]
            assert "gh" not in parts
            assert "curl" not in parts
            assert parts[0] == "git"
