"""Draft a WS-* append and a handoff skeleton from seat PR JSON.

Knowledge plane only. The drafter reads a local JSON file (PR number, title,
head sha, files, merged_at, plus the workstream the seat names). Optional
``kinds`` of ``draft-decision`` and ``draft-discovery`` add those skeletons to
the same stdout or ``--out`` JSON. It does not write ``agentos/``, call GitHub,
or decide whether work may run. ``scripts/agentos.py`` checkers on a temp copy
of the store are the gate for the drafted records. An unfilled discovery keeps
``falsifier`` and ``so_what`` placeholders that fail ``check_discovery``.
"""
from __future__ import annotations

import ast
import importlib.util
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import unicodedata
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


def _draft(tmp_path: Path, payload: dict | None = None, *extra: str):
    result, path = _run(tmp_path, payload or _payload(), *extra)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout), path, result


def _init_observation_repo(repo: Path, env: dict[str, str]) -> None:
    """Throwaway git repo. HEAD is a no-ff merge whose plain diff-tree is empty."""
    subprocess.run(["git", "init", "-b", "main", str(repo)], check=True, capture_output=True, env=env)
    for key, value in (
        ("user.email", "lane@example.invalid"),
        ("user.name", "Records Draft Lane"),
        ("commit.gpgsign", "false"),
    ):
        subprocess.run(
            ["git", "-C", str(repo), "config", key, value],
            check=True,
            capture_output=True,
            env=env,
        )

    def commit(name: str, body: str, message: str) -> None:
        (repo / name).write_text(body, encoding="utf-8")
        subprocess.run(["git", "-C", str(repo), "add", name], check=True, capture_output=True, env=env)
        subprocess.run(
            ["git", "-C", str(repo), "commit", "-m", message],
            check=True,
            capture_output=True,
            env=env,
        )

    commit("observed.py", "one\n", "add observed.py")
    subprocess.run(["git", "-C", str(repo), "checkout", "-b", "side"], check=True, capture_output=True, env=env)
    commit("side.py", "two\n", "add side.py")
    subprocess.run(["git", "-C", str(repo), "checkout", "main"], check=True, capture_output=True, env=env)
    commit("main.py", "three\n", "add main.py")
    subprocess.run(
        ["git", "-C", str(repo), "merge", "--no-ff", "-m", "merge side", "side"],
        check=True,
        capture_output=True,
        env=env,
    )


def _validate_store(work: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(AGENTOS), "validate", "--root", str(work), "--quiet"],
        capture_output=True,
        text=True,
        cwd=REPO,
    )


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
        assert result.stderr.startswith("agentos-records-draft:"), result.stderr
        assert "refusing to write into agentos/" in result.stderr
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
    """Names come from a throwaway repo, not from this checkout's HEAD.

    A PR merge ref has an empty ``git diff-tree -r``. This repo's HEAD is that
    kind of merge. The drafter reads it only because ``--repo`` points there,
    and the sha under test is the newest non-merge commit.
    """
    env = _git_env()
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_observation_repo(repo, env)
    merge = subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True, env=env
    ).strip()
    merge_names = subprocess.check_output(
        ["git", "-C", str(repo), "diff-tree", "--no-commit-id", "--name-only", "-r", merge],
        text=True,
        env=env,
    ).splitlines()
    assert merge_names == []
    sha = subprocess.check_output(
        ["git", "-C", str(repo), "rev-list", "--no-merges", "--max-count=1", "HEAD"],
        text=True,
        env=env,
    ).strip()
    assert sha
    assert sha != merge
    names = subprocess.check_output(
        ["git", "-C", str(repo), "diff-tree", "--no-commit-id", "--name-only", "-r", sha],
        text=True,
        env=env,
    ).splitlines()
    assert names, "non-merge commit has an empty diff-tree; the observation test would have no power"
    real = names[0]
    fake = "no/such-records-draft-path.py"
    draft, _path, _result = _draft(
        tmp_path,
        _payload(pr={"head_sha": sha, "files": [real, fake]}),
        "--repo",
        str(repo),
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


def test_local_commit_merge_head_records_no_observed_paths(
    tmp_path: Path,
) -> None:
    """Drafting the merge commit itself: diff-tree returns no names.

    The throwaway repo's HEAD is the no-ff merge the existing helper creates.
    ``diff-tree --no-commit-id --name-only -r HEAD`` prints nothing for a
    merge. Empty output is not proof that a path is absent, so every seat
    path stays ``UNVERIFIED`` with ``in_local_commit=None``, the same as a
    diff-tree that could not run. A path that one of the parents changed must
    still NOT be marked ``observed``.
    """
    env = _git_env()
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_observation_repo(repo, env)
    merge = subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True, env=env
    ).strip()
    merge_names = subprocess.check_output(
        ["git", "-C", str(repo), "diff-tree", "--no-commit-id", "--name-only", "-r", merge],
        text=True,
        env=env,
    ).splitlines()
    assert merge_names == []
    # The merge does not list files, but its two parents did. Use those exact
    # file names so a buggy "any existing commit object is observed" path
    # would surface here.
    parents = subprocess.check_output(
        ["git", "-C", str(repo), "log", "--pretty=%P", "-n", "1", merge], text=True, env=env
    ).strip().split()
    parent_files: set[str] = set()
    for parent in parents:
        parent_files.update(
            subprocess.check_output(
                ["git", "-C", str(repo), "diff-tree", "--no-commit-id", "--name-only", "-r", parent],
                text=True,
                env=env,
            ).splitlines()
        )
    assert parent_files, "merge parents had no files; the merge-commit assertion would have no power"
    files = sorted(parent_files)
    draft, _path, _result = _draft(
        tmp_path,
        _payload(pr={"head_sha": merge, "files": files}),
        "--repo",
        str(repo),
    )
    by_path = {item["path"]: item for item in draft["files"]}
    assert all(by_path[p]["status"] == "UNVERIFIED" for p in files), {
        p: by_path[p]["status"] for p in files
    }
    assert all(by_path[p]["in_local_commit"] is None for p in files), {
        p: by_path[p]["in_local_commit"] for p in files
    }
    assert any(
        item.get("object_type") == "commit" for item in draft["observations"]
    ), "merge sha must still resolve to a commit object"


def test_diff_tree_does_not_invoke_repo_fsmonitor(tmp_path: Path) -> None:
    """A ``--repo`` target's ``.git/config`` can name ``core.fsmonitor``.

    ``git diff-tree`` invokes that hook. The drafter must not let a
    seat-controlled executable fire inside its short-lived diff-tree call.
    """
    env = _git_env()
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_observation_repo(repo, env)
    sha = subprocess.check_output(
        ["git", "-C", str(repo), "rev-list", "--no-merges", "--max-count=1", "HEAD"],
        text=True,
        env=env,
    ).strip()
    names = subprocess.check_output(
        ["git", "-C", str(repo), "diff-tree", "--no-commit-id", "--name-only", "-r", sha],
        text=True,
        env=env,
    ).splitlines()
    assert names, "non-merge commit has an empty diff-tree; the hardening test has no power"

    marker = tmp_path / "marker"
    script = tmp_path / "fsmonitor.sh"
    script.write_text(
        "#!/bin/sh\ntouch " + str(marker) + "\n",
        encoding="utf-8",
    )
    os.chmod(script, 0o755)
    subprocess.run(
        ["git", "-C", str(repo), "config", "core.fsmonitor", str(script)],
        check=True,
        capture_output=True,
        env=env,
    )

    # Sanity check: with the same argv the drafter used to use, the marker
    # would be touched. Recorded so a future regression that drops the
    # ``-c core.fsmonitor=`` switch has its RED line in the log.
    standalone = subprocess.run(
        ["git", "-C", str(repo), "diff-tree", "--no-commit-id", "--name-only", "-r", sha],
        capture_output=True,
        text=True,
        env=env,
    )
    assert standalone.returncode == 0
    assert marker.exists(), (
        "git diff-tree did not invoke the repo's core.fsmonitor on this git "
        "build; the hardening test has nothing to test against."
    )
    marker.unlink()

    real = names[0]
    draft, _path, _result = _draft(
        tmp_path,
        _payload(pr={"head_sha": sha, "files": [real, "no/such-fsmonitor-path.py"]}),
        "--repo",
        str(repo),
    )
    by_path = {item["path"]: item for item in draft["files"]}
    assert by_path[real]["status"] == "observed"
    assert by_path[real]["in_local_commit"] is True
    assert by_path["no/such-fsmonitor-path.py"]["status"] == "UNVERIFIED"
    assert by_path["no/such-fsmonitor-path.py"]["in_local_commit"] is False
    assert not marker.exists(), (
        "core.fsmonitor ran inside the drafter's git invocation; the "
        f"marker argv must override core.fsmonitor. marker={marker}"
    )


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


@pytest.mark.parametrize("separator", ["\n", "\r", "\u2028", "\u2029", "\u0085"])
def test_newline_title_head_sha_and_session_stay_one_quoted_line(
    tmp_path: Path, separator: str
) -> None:
    """Title, head sha, and session are quoted in the prose and the append.

    A line-separator inside the title must stay inside one physical line for
    every separator ``_q`` promises to escape: LF, CR, U+2028, U+2029, and
    U+0085. The same quoting is applied to head_sha and session. A temp-store
    validate of the drafted handoff plus the append must report 0 error(s).
    """
    title = "line1" + separator + "ended_because: crashed"
    session = "seat/example"
    payload = _payload(pr={"title": title}, session=session)
    draft, _path, _result = _draft(tmp_path, payload)
    prose = draft["handoff"]["markdown"].split("\n---\n", 1)[1]
    append = draft["ws_append"]["markdown"]
    # Mirror ``_q`` so we test the helper's escape form. Plain
    # ``json.dumps(..., ensure_ascii=False)`` would leave U+2028, U+2029 and
    # U+0085 as raw characters, mismatching what the drafter wrote.
    quoted_title = json.dumps(title, ensure_ascii=False)
    for sep, escape in (("\u2028", "\\u2028"), ("\u2029", "\\u2029"), ("\u0085", "\\u0085")):
        quoted_title = quoted_title.replace(sep, escape)
    quoted_sha = json.dumps(payload["pr"]["head_sha"], ensure_ascii=False)
    quoted_session = json.dumps(session, ensure_ascii=False)
    # LF and CR are escaped by json.dumps and so are invisible to the mutant;
    # the parametrized assertion would still be GREEN on the mutant for those,
    # which is exactly why the test exists: only the three explicit
    # ``_q`` escapes are load-bearing.
    for label, text in (("handoff body", prose), ("append", append)):
        assert quoted_title in text, label
        assert ("line1" + separator + "ended_because: crashed") not in text, label
        assert len([line for line in text.splitlines() if quoted_title in line]) == 1, label
        assert f"- head_sha: {quoted_sha}" in text, label
        assert f"- session: {quoted_session}" in text, label

    work = tmp_path / "agentos"
    shutil.copytree(STORE, work)
    target = work / "handoffs" / "AGENT-OS-2099-01-15.md"
    assert not target.exists()
    target.write_text(draft["handoff"]["markdown"], encoding="utf-8")
    ws = work / "workstreams" / "WS-AGENT-OS.md"
    text = ws.read_text(encoding="utf-8")
    if not text.endswith("\n"):
        text += "\n"
    ws.write_text(text + "\n" + append, encoding="utf-8")
    validated = _validate_store(work)
    assert validated.returncode == 0, validated.stdout + validated.stderr
    assert "0 error(s)" in validated.stdout, validated.stdout


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
        ({"pr": {"merged_at": "2026-10-13T99:99:99Z"}}, "merged_at"),
        ({"model": "telepathy"}, "model"),
    ],
)
def test_bad_input_exits_2(tmp_path: Path, payload: dict, needle: str) -> None:
    result, _path = _run(tmp_path, _payload(**payload))
    assert result.returncode == 2
    assert needle in result.stderr
    assert result.stdout == ""


def test_timestamp_time_part_validates_when_present(tmp_path: Path) -> None:
    """``YYYY-MM-DDTHH:MM:SSZ`` must reject impossible wall-clock times.

    The date-only branch is unchanged; the regex accepts any digits in the
    time component, so ``2026-10-13T99:99:99Z`` passes the regex but must be
    rejected by ``datetime.strptime``.
    """
    for ts in ("2026-10-13T23:59:59Z", "2026-10-13"):
        result, _path = _run(tmp_path, _payload(pr={"merged_at": ts}))
        assert result.returncode == 0, f"{ts!r} unexpectedly failed: {result.stderr}"


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


def test_omitted_kinds_omit_decision_and_discovery(tmp_path: Path) -> None:
    draft, _path, _result = _draft(tmp_path)
    assert "decision" not in draft
    assert "discovery" not in draft
    assert "kinds" not in draft


def test_unknown_kind_exits_2(tmp_path: Path) -> None:
    result, _path = _run(tmp_path, _payload(kinds=["draft-handoff"]))
    assert result.returncode == 2
    assert "draft-handoff" in result.stderr
    assert result.stdout == ""


def test_duplicate_kind_exits_2(tmp_path: Path) -> None:
    result, _path = _run(tmp_path, _payload(kinds=["draft-decision", "draft-decision"]))
    assert result.returncode == 2
    assert "duplicate" in result.stderr
    assert result.stdout == ""


def test_draft_decision_passes_check_decision_in_a_temp_store(tmp_path: Path) -> None:
    before = sorted(path.name for path in (STORE / "decisions").glob("*.md"))
    draft, _path, result = _draft(tmp_path, _payload(kinds=["draft-decision"]))
    assert result.stderr == ""
    decision = draft["decision"]
    assert decision["path"] == "agentos/decisions/DEC-AGENT-OS-PR-9001.md"
    assert decision["target_exists"] is False
    assert sorted(path.name for path in (STORE / "decisions").glob("*.md")) == before
    assert "does not gate execution" in decision["markdown"].lower()

    agentos = _load_agentos()
    preview = tmp_path / "DEC-AGENT-OS-PR-9001.md"
    preview.write_text(decision["markdown"], encoding="utf-8")
    rec, body = agentos.parse_record(preview)
    rec["_body"] = body
    hard = [item for item in agentos.check_decision(rec, Path(decision["path"])) if item.hard]
    assert hard == [], [item.message for item in hard]

    work = tmp_path / "agentos"
    shutil.copytree(STORE, work)
    target = work / "decisions" / "DEC-AGENT-OS-PR-9001.md"
    assert not target.exists()
    target.write_text(decision["markdown"], encoding="utf-8")
    validated = _validate_store(work)
    assert validated.returncode == 0, validated.stdout + validated.stderr
    assert "0 error(s)" in validated.stdout


def test_unfilled_discovery_fails_until_a_human_fills_falsifier_and_so_what(
    tmp_path: Path,
) -> None:
    before = sorted(path.name for path in (STORE / "discoveries").glob("*.md"))
    draft, _path, result = _draft(tmp_path, _payload(kinds=["draft-discovery"]))
    assert result.stderr == ""
    discovery = draft["discovery"]
    assert discovery["path"] == "agentos/discoveries/DSC-AGENT-OS-PR-9001.md"
    assert discovery["target_exists"] is False
    assert sorted(path.name for path in (STORE / "discoveries").glob("*.md")) == before
    text = discovery["markdown"]
    assert 'falsifier: "UNFILLED"' in text
    assert 'so_what: ""' in text
    assert "does not gate execution" in text.lower()

    agentos = _load_agentos()
    preview = tmp_path / "DSC-AGENT-OS-PR-9001.md"
    preview.write_text(text, encoding="utf-8")
    rec, body = agentos.parse_record(preview)
    rec["_body"] = body
    hard = [item for item in agentos.check_discovery(rec, Path(discovery["path"])) if item.hard]
    messages = [item.message for item in hard]
    assert any("falsifier" in message for message in messages)
    assert any("so_what" in message for message in messages)
    assert {item.rule for item in hard} <= {"unfalsifiable-claim", "required-field"}

    work = tmp_path / "agentos"
    shutil.copytree(STORE, work)
    target = work / "discoveries" / "DSC-AGENT-OS-PR-9001.md"
    target.write_text(text, encoding="utf-8")
    failed = _validate_store(work)
    assert failed.returncode != 0
    combined = failed.stdout + failed.stderr
    assert "falsifier" in combined
    assert "so_what" in combined

    filled = text.replace(
        'falsifier: "UNFILLED"',
        'falsifier: "python3 -c \'print(1)\' would disprove a contradictory reading"',
    ).replace(
        'so_what: ""',
        'so_what: "A future session does not treat this skeleton as a finding."',
    )
    target.write_text(filled, encoding="utf-8")
    rec2, body2 = agentos.parse_record(target)
    rec2["_body"] = body2
    hard2 = [item for item in agentos.check_discovery(rec2, target) if item.hard]
    assert hard2 == [], [item.message for item in hard2]
    passed = _validate_store(work)
    assert passed.returncode == 0, passed.stdout + passed.stderr
    assert "0 error(s)" in passed.stdout


def test_both_kinds_stay_inside_stdout(tmp_path: Path) -> None:
    decisions = sorted(path.name for path in (STORE / "decisions").glob("*.md"))
    discoveries = sorted(path.name for path in (STORE / "discoveries").glob("*.md"))
    dest = tmp_path / "draft.json"
    result, _path = _run(
        tmp_path,
        _payload(kinds=["draft-discovery", "draft-decision"]),
        "--out",
        str(dest),
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == ""
    draft = json.loads(dest.read_text(encoding="utf-8"))
    assert draft["decision"]["path"].startswith("agentos/decisions/DEC-")
    assert draft["discovery"]["path"].startswith("agentos/discoveries/DSC-")
    assert "UNFILLED" in draft["discovery"]["markdown"]
    assert sorted(path.name for path in (STORE / "decisions").glob("*.md")) == decisions
    assert sorted(path.name for path in (STORE / "discoveries").glob("*.md")) == discoveries
    assert list(tmp_path.glob("*.md")) == []


_RECORD_GIT_FLAGS = ("-c core.fsmonitor=", "-c core.hooksPath=")


def _recorded_git_commands(draft: dict) -> list[str]:
    """Recorded commands in the output that invoke ``git``.

    ``handoff_verified_commands`` always begins with the drafter itself
    (``python3 scripts/agentos_records_draft.py --pr-json …``), which is not a
    git invocation; the hardening law binds the git ones.
    """
    commands = [item["command"] for item in draft["handoff_verified_commands"]]
    commands += [item["command"] for item in draft.get("observations", [])]
    return [command for command in commands if " git " in command]


def _non_merge_observation(tmp_path: Path) -> tuple[Path, str, str]:
    """Throwaway repo plus its newest non-merge commit and one name it lists."""
    env = _git_env()
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_observation_repo(repo, env)
    sha = subprocess.check_output(
        ["git", "-C", str(repo), "rev-list", "--no-merges", "--max-count=1", "HEAD"],
        text=True,
        env=env,
    ).strip()
    assert sha
    names = subprocess.check_output(
        ["git", "-C", str(repo), "diff-tree", "--no-commit-id", "--name-only", "-r", sha],
        text=True,
        env=env,
    ).splitlines()
    assert names, (
        "non-merge commit has an empty diff-tree; the recorded-command test "
        "would have no power"
    )
    return repo, sha, names[0]


def test_recorded_git_commands_carry_the_hardening_flags(tmp_path: Path) -> None:
    """``verified[].command`` is copy-pasteable; it must harden git as ``_git`` does.

    ``_git`` runs ``git -c core.fsmonitor= -c core.hooksPath= -C <repo>``. The
    prefix recorded in the draft came from ``_git_tool``, which emitted a plain
    ``git -C <repo>``. A human pasting the recorded reproduction command into a
    hostile repository runs that repository's ``core.fsmonitor`` executable with
    their own credentials, so the two prefixes must be the same argv.
    """
    repo, sha, real = _non_merge_observation(tmp_path)
    fake = "no/such-recorded-command-path.py"
    draft, _path, _result = _draft(
        tmp_path,
        _payload(pr={"head_sha": sha, "files": [real, fake]}),
        "--repo",
        str(repo),
    )
    commands = _recorded_git_commands(draft)
    assert len(commands) >= 2, commands
    expected = "git " + " ".join(_RECORD_GIT_FLAGS) + " -C " + shlex.quote(str(repo)) + " "
    for command in commands:
        for flag in _RECORD_GIT_FLAGS:
            assert flag in command, command
        assert command.index("core.fsmonitor=") < command.index("core.hooksPath="), command
        assert expected in command, command
    # ``changed[].what`` carries the same prefix inside a sentence and is
    # copy-pasted just as often as the ``verified`` block.
    prose = [
        line for line in draft["handoff"]["markdown"].splitlines()
        if " GIT_NO_LAZY_FETCH=1 " in line
    ]
    assert prose, draft["handoff"]["markdown"]
    for line in prose:
        assert expected in line, line
    default, _dp, _dr = _draft(tmp_path)
    for command in _recorded_git_commands(default):
        for flag in _RECORD_GIT_FLAGS:
            assert flag in command, command
        assert " -C " not in command, command


def test_pasting_a_recorded_git_command_does_not_run_repo_fsmonitor(
    tmp_path: Path,
) -> None:
    """The recorded command is run by a human in a shell; it must be hardened.

    ``test_diff_tree_does_not_invoke_repo_fsmonitor`` proves the drafter's own
    argv never fires a seat-controlled ``core.fsmonitor``. This proves the
    argv the drafter RECORDS does not either.
    """
    env = _git_env()
    repo, sha, real = _non_merge_observation(tmp_path)
    marker = tmp_path / "marker"
    script = tmp_path / "fsmonitor.sh"
    script.write_text("#!/bin/sh\ntouch " + str(marker) + "\n", encoding="utf-8")
    os.chmod(script, 0o755)
    subprocess.run(
        ["git", "-C", str(repo), "config", "core.fsmonitor", str(script)],
        check=True,
        capture_output=True,
        env=env,
    )

    # Power check: the UNHARDENED argv touches the marker on this git build.
    # Without it the assert below could pass because this git never calls
    # fsmonitor for diff-tree, which is not the thing under test.
    plain = subprocess.run(
        ["git", "-C", str(repo), "diff-tree", "--no-commit-id", "--name-only", "-r", sha],
        capture_output=True,
        text=True,
        env=env,
    )
    assert plain.returncode == 0, plain.stderr
    assert marker.exists(), (
        "git diff-tree did not invoke the repo's core.fsmonitor on this git "
        "build; the recorded-command test has nothing to test against."
    )
    marker.unlink()

    draft, _path, _result = _draft(
        tmp_path,
        _payload(pr={"head_sha": sha, "files": [real]}),
        "--repo",
        str(repo),
    )
    recorded = [
        item["command"]
        for item in draft["handoff_verified_commands"]
        if " diff-tree " in item["command"]
    ]
    assert len(recorded) == 1, recorded
    pasted = subprocess.run(
        ["/bin/sh", "-c", recorded[0]], capture_output=True, text=True, env=env
    )
    assert pasted.returncode == 0, pasted.stderr
    assert not marker.exists(), (
        "the RECORDED command runs the repository's core.fsmonitor when pasted "
        f"into a shell: {recorded[0]}"
    )


@pytest.mark.parametrize("separator", ["\u2028", "\u0085", "\u2029", "\x0b", "\x0c"])
def test_file_path_line_separators_are_refused(tmp_path: Path, separator: str) -> None:
    """A ``pr.files`` entry is interpolated RAW in the handoff and the append.

    ``changed[].path`` goes through ``_q``, which escapes exactly the characters
    ``str.splitlines`` breaks on, but the ``- files:`` rows (handoff body and WS
    append) are plain f-strings, so the ``_pr_fields`` guard is the only place a
    separator can be refused. It tested only ``\\n`` and ``\\r``, so U+2028,
    U+0085, U+2029, VT and FF each turned one seat string into two rendered
    lines.
    """
    # Premise: this parameter really is a line break for str.splitlines. If a
    # future Python stops splitting on it the test must fail, not pass vacuously.
    assert len(("a" + separator + "b").splitlines()) == 2, repr(separator)
    clean, _cp, _cr = _draft(tmp_path, _payload(pr={"files": ["lib/x.py"]}))
    injected = f"lib{separator}ended_because: crashed.py"
    result, _path = _run(tmp_path, _payload(pr={"files": [injected]}))
    rendered = ""
    if result.stdout.strip():
        rendered = json.loads(result.stdout)["handoff"]["markdown"]
    assert result.returncode == 2, (
        f"separator {separator!r} was ACCEPTED: handoff str.splitlines() grew "
        f"{len(clean['handoff']['markdown'].splitlines())} -> "
        f"{len(rendered.splitlines())}"
    )
    assert "single-line repo-relative paths" in result.stderr
    assert result.stdout == ""


@pytest.mark.parametrize("separator", ["\x1b", "\t", "\x00", "\u200b", "\ufeff"])
def test_invisible_non_line_breakers_are_refused(tmp_path: Path, separator: str) -> None:
    """An invisible ``pr.files`` character is refused although it breaks no line.

    The sibling parametrization above pins the characters ``str.splitlines``
    breaks on. These five break NO line, so the ``splitlines()`` clause alone
    accepts them and only the ``unicodedata.category`` clause can refuse them:
    ESC, TAB and NUL are ``Cc``, ZWSP and BOM are ``Cf``. ``_q`` keeps the
    quoted fields on one physical line, but the ``- files:`` rows in the handoff
    body and the WS append are plain f-strings, so nothing else keeps an
    invisible character out of a rendered path that a human copies back into a
    shell. The clause is load-bearing: deleting it lets all five through (the PR
    #9310 review's mutation 2c), which is why this test sits beside the
    separator one instead of inside its parameter list.
    """
    # Premise 1: the parameter belongs to the guarded category set, which is the
    # only thing here that can refuse it.
    assert unicodedata.category(separator) in {"Cc", "Cf", "Zl", "Zp"}, repr(separator)
    # Premise 2: it is NOT a line break for str.splitlines, so a splitlines-only
    # guard could not fail on it. If a future Python starts splitting on it this
    # test must fail, not pass vacuously.
    assert len(("a" + separator + "b").splitlines()) == 1, repr(separator)
    clean, _cp, _cr = _draft(tmp_path, _payload(pr={"files": ["lib/x.py"]}))
    injected = f"lib{separator}ended_because: crashed.py"
    result, _path = _run(tmp_path, _payload(pr={"files": [injected]}))
    rendered = ""
    if result.stdout.strip():
        rendered = json.loads(result.stdout)["handoff"]["markdown"]
    smuggled = [ascii(line) for line in rendered.splitlines() if "ended_because" in line]
    assert result.returncode == 2, (
        f"character {separator!r} (category {unicodedata.category(separator)}, "
        f"not a str.splitlines breaker) was ACCEPTED: clean handoff has "
        f"{len(clean['handoff']['markdown'].splitlines())} lines and the injected "
        f"one rendered {smuggled}"
    )
    assert "pr.files entries must be single-line repo-relative paths" in result.stderr
    assert result.stdout == ""


# ---------------------------------------------------------------------------
# W15-F-FUP follow-up items. Each block is numbered to match the commission.
# ---------------------------------------------------------------------------

def _load_draft_module():
    spec = importlib.util.spec_from_file_location(
        "agentos_records_draft_under_test", CLI
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# --- item 1: _MERGED_RE is ASCII-only --------------------------------------
# Without re.ASCII, ``\d`` matches every Unicode Nd digit (Arabic-Indic
# U+0660..U+0669, fullwidth U+FF10..FF19, Devanagari U+0966..U+096F) and
# ``datetime.strptime``/``int`` coerce them, so a mixed string like
# ``2026-10-13T1٠:34:56Z`` used to reach the record. The refusal must be the
# same refusal the existing malformed-merged_at tests assert (rc 2, the
# ``merged_at`` message, empty stdout -- ``test_bad_input_exits_2``).
_UNICODE_DIGIT_PARAMS = [
    pytest.param("2026-10-1٣", "2026-10-13", id="date-arabic-indic"),
    pytest.param("2026-10-１3", "2026-10-13", id="date-fullwidth"),
    pytest.param("2026-10-१3", "2026-10-13", id="date-devanagari"),
    pytest.param("2026-10-13T1٠:34:56Z", "2026-10-13T10:34:56Z", id="hour-arabic-indic"),
    pytest.param("2026-10-13T１0:34:56Z", "2026-10-13T10:34:56Z", id="hour-fullwidth"),
    pytest.param("2026-10-13T१0:34:56Z", "2026-10-13T10:34:56Z", id="hour-devanagari"),
    pytest.param("2026-10-13T10:3٤:56Z", "2026-10-13T10:34:56Z", id="minute-arabic-indic"),
    pytest.param("2026-10-13T10:34:5٦Z", "2026-10-13T10:34:56Z", id="seconds-arabic-indic"),
    pytest.param("2026-10-13T10:34:５6Z", "2026-10-13T10:34:56Z", id="seconds-fullwidth"),
    pytest.param("2026-10-13T10:34:५6Z", "2026-10-13T10:34:56Z", id="seconds-devanagari"),
]


@pytest.mark.parametrize("hostile,ascii_twin", _UNICODE_DIGIT_PARAMS)
def test_merged_at_unicode_digits_are_refused(
    tmp_path: Path, hostile: str, ascii_twin: str
) -> None:
    """Mixed-script Nd digits are refused by ``_MERGED_RE`` itself."""
    # Premise: the hostile value differs from its ACCEPTED twin only by
    # non-ASCII Nd digits in one field (date, hour, minute or seconds).
    assert len(hostile) == len(ascii_twin), repr(hostile)
    assert any(not ch.isascii() and ch.isdigit() for ch in hostile), repr(hostile)
    control, _cp = _run(tmp_path, _payload(pr={"merged_at": ascii_twin}))
    assert control.returncode == 0, control.stderr
    result, _path = _run(tmp_path, _payload(pr={"merged_at": hostile}))
    assert result.returncode == 2, (
        f"{hostile!r} was ACCEPTED: strptime/int coerce Nd digits, so the regex "
        "class is the only door that can refuse it"
    )
    assert "pr.merged_at must be YYYY-MM-DD or YYYY-MM-DDTHH:MM:SSZ" in result.stderr
    assert result.stdout == ""


# --- item 2: anti-drift between the executed argv and the recorded prefix ---

def test_recorded_git_tool_prefix_matches_hardened_git_argv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """ANTI-DRIFT: ``_git``'s argv and ``_git_tool``'s recorded prefix are one.

    ``_git`` (scripts/agentos_records_draft.py:168) and ``_git_tool`` (:194)
    must both read the single ``_GIT_HARDENING`` tuple (:105) -- the shared
    prefix exists precisely so a copy-pasted recorded command never loses an
    ``-c`` override the in-process git used (comment :78-104). If either side
    inlines its own flag list, this test fails.
    """
    mod = _load_draft_module()
    captured: list[list[str]] = []

    def fake_run(argv, **kwargs):
        captured.append(list(argv))
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    repo = tmp_path / "carrier"
    repo.mkdir()
    assert mod._git("cat-file", "-t", "abc1234", repo=repo) is not None
    assert len(captured) == 1, captured
    argv = captured[0]
    expected = shlex.split(mod._git_tool(repo))
    assert argv[: len(expected)] == expected, (
        f"drift: _git executed {argv!r} but _git_tool records "
        f"{mod._git_tool(repo)!r}; the leading option segment must be identical"
    )
    assert argv[len(expected)] in {"cat-file", "diff-tree"}, argv


# --- item 3: every seat-supplied string field, refused or quoted ------------
# RAW-interpolation inventory (no ``_q`` on the rendered record line), with
# the guard that makes each safe:
#   pr.merged_at  :556 (handoff), :605 (ws append) -- ``_MERGED_RE`` :73 with
#                  re.ASCII + ``fullmatch`` :276 + ``fromisoformat`` :280 +
#                  ``strptime`` :294.
#   pr.files entry :562 (handoff), :611 (ws append) -- splitlines count :265 +
#                  category scan :266-268 + leading "/" or "\\" :269 + ``..``
#                  :272 (``_pr_fields``).
#   pr.number     :554, :596, :603 (also :478/:483/:507/:513/:516/:633/:634/
#                  :642/:643 inside ``_q`` scalars) -- strict ``type(...) is
#                  int`` coercion :248-250.
#   workstream key :565, :566, :602 -- ``_WS_RE`` :65 fullmatch :231 + store
#                  file must exist :234-238.
#   pr day        :566 -- regex group(1) :276 (ASCII after item 1) +
#                  ``fromisoformat`` :280.
# All other seat-supplied strings (title :478/:491/:555/:604/:670->:687/
# :716->:722, head_sha :492/:516/:557/:606, session :488/:558/:607) enter the
# record only through ``_q`` (:142-153): json escapes every control character
# including newline and ESC, and ``_q`` additionally escapes the raw-JSON
# line breaks U+2028/U+2029/U+0085. model/ended_because never interpolate at
# all unless they are enum members (:309-315, HANDOFF_MODEL/HANDOFF_ENDED in
# scripts/agentos.py:189-190).
_HOSTILE_CHARS = {
    "newline": "\n",
    "line-separator": "\u2028",
    "escape": "\x1b",
    "backtick-fence": "```",
}


def _escaped_form(value: str) -> str:
    """Exactly what ``_q`` renders inside its double-quoted scalar."""
    encoded = json.dumps(value, ensure_ascii=False)[1:-1]
    return (
        encoded.replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
        .replace("\u0085", "\\u0085")
    )


_SEAT_FIELD_PARAMS = [
    pytest.param(
        "pr.number", lambda h: _payload(pr={"number": f"9{h}001"}),
        "refused", "pr.number must be a positive integer",
        id="pr.number",
    ),
    pytest.param(
        "pr.merged_at", lambda h: _payload(pr={"merged_at": f"2026-10-13{h}"}),
        "refused", "pr.merged_at must be YYYY-MM-DD",
        id="pr.merged_at",
    ),
    pytest.param(
        "workstream", lambda h: _payload(workstream=f"WS:AGENT{h}OS"),
        "refused", "workstream must be a WS:KEY citation",
        id="workstream",
    ),
    pytest.param(
        "pr.files", lambda h: _payload(pr={"files": [f"lib/x{h}.py"]}),
        "mixed", "pr.files entries must be single-line repo-relative paths",
        id="pr.files",
    ),
    pytest.param(
        # Entry in the two-space bullet shape the handoff/append render
        # themselves (accepted by ``_pr_fields`` today); the bare-value
        # mutant then produces a line equal to the value that still
        # starts with "  - ", so the third positional clause is what
        # fails. Chosen as its own param so the id reads standalone.
        "pr.files", lambda h: _payload(pr={"files": [f"  - lib/x{h}.py"]}),
        "mixed", "pr.files entries must be single-line repo-relative paths",
        id="pr.files-bullet-form",
    ),
    pytest.param(
        "model", lambda h: _payload(model=f"opus{h}"),
        "refused", "model must be one of",
        id="model",
    ),
    pytest.param(
        "ended_because", lambda h: _payload(ended_because=f"complete{h}"),
        "refused", "ended_because must be one of",
        id="ended_because",
    ),
    pytest.param(
        "session", lambda h: _payload(session=f"seat/ok{h}second"),
        "quoted", None, id="session",
    ),
    pytest.param(
        "title", lambda h: _payload(pr={"title": f"Record {h}title"}),
        "quoted", None, id="pr.title",
    ),
    pytest.param(
        "head_sha", lambda h: _payload(pr={"head_sha": f"abc1234{h}def"}),
        "quoted", None, id="pr.head_sha",
    ),
]

_REFUSED_NEEDLES = {
    "pr.number": "pr.number must be a positive integer",
    "pr.merged_at": "pr.merged_at must be YYYY-MM-DD",
    "workstream": "workstream must be a WS:KEY citation",
    "pr.files": "pr.files entries must be single-line repo-relative paths",
    "model": "model must be one of",
    "ended_because": "ended_because must be one of",
}


def _is_yaml_key_line(line: str) -> bool:
    # Lexical, not structural. Optional "- " bullet, then the key candidate
    # [A-Za-z_][\w.:-]*: ``/`` is outside the class, so it still ends a
    # candidate and keeps raw paths such as ``lib/x.py`` out. The lookahead
    # tests the FINAL colon of the candidate, which must be followed by
    # whitespace or end-of-line: ``DEC:KEY: v`` is a key line, ``DEC:KEY``
    # alone is not. No module wording is pinned.
    return re.match(
        r"^\s*(?:-\s+)?[A-Za-z_][\w.:-]*:(?=\s|$)", line
    ) is not None


@pytest.mark.parametrize("field_id,builder,outcome,needle", _SEAT_FIELD_PARAMS)
def test_seat_string_fields_are_refused_or_quoted(
    tmp_path: Path, field_id: str, builder, outcome: str, needle
) -> None:
    """Every seat-supplied string field: refused at the door or escaped in.

    For each field, feed each hostile value (newline, U+2028, ESC, a
    backtick-fence). Assert EITHER the guard's refusal (rc 2 + that guard's
    message) OR -- for fields whose only guard is ``_q`` quoting, plus the
    printable-ASCII backtick on ``pr.files`` -- a rendered record that (i)
    exits 0, i.e. the module's own ``_assert_handoff_parses``/:749 and
    decision/discovery gates accepted it, (ii) has the SAME physical line
    count as the benign baseline (no injected break), (iii) contains NO raw
    U+2028 or ESC byte, (iv) has no line starting with `````` ``` ```` (a fence
    cannot open at column 0), and (v) contains the field's full value in
    ``_q``-escaped form -- so the hostile input survived only inside a quoted
    scalar; for ``pr.files`` (v) is POSITIONAL instead, because that field
    renders raw outside ``_q``: every line with a not-inside-quotes
    occurrence of the value must carry the two-space bullet prefix,
    at least one such line must exist, and no line may equal the
    bare value (in-quotes occurrences ride (i)-(iv)). "No raw hostile
    character" is read as "no raw structural escape": legitimate printable
    backticks necessarily survive inside quotes.
    """
    for hostile_name, h in _HOSTILE_CHARS.items():
        case = f"{field_id} x {hostile_name}"
        payload = builder(h)
        payload["kinds"] = ["draft-decision", "draft-discovery"]
        must_refuse = outcome in ("refused", "mixed") and not (
            outcome == "mixed" and hostile_name == "backtick-fence"
        )
        if must_refuse:
            result, _path = _run(tmp_path, payload)
            assert result.returncode == 2, (
                f"{case}: expected refusal, got rc={result.returncode} "
                f"stdout={ascii(result.stdout[:200])}"
            )
            assert _REFUSED_NEEDLES[field_id] in result.stderr, case
            assert result.stdout == "", case
            continue
        result, _path = _run(tmp_path, payload)
        assert result.returncode == 0, f"{case}: {result.stderr}"
        draft = json.loads(result.stdout)
        benign = builder("")
        benign["kinds"] = ["draft-decision", "draft-discovery"]
        clean_result, _cp = _run(tmp_path, benign)
        assert clean_result.returncode == 0, clean_result.stderr
        clean = json.loads(clean_result.stdout)
        if field_id == "session":
            value = payload["session"]
        elif field_id == "pr.files":
            value = payload["pr"]["files"][0]
        else:  # pr.title / pr.head_sha
            value = payload["pr"]["title" if field_id == "title" else "head_sha"]
        # Every rendered record is checked structurally. The value-presence
        # check runs where the module actually renders the field: handoff
        # (- session/head_sha/title lines and changed[].path) and ws_append
        # (- title/merged_at/head_sha/session lines and "  - {path}" rows).
        # decision/discovery legitimately carry only title (in answer/claim).
        for record_key in ("handoff", "ws_append", "decision", "discovery"):
            text = draft[record_key]["markdown"]
            base = clean[record_key]["markdown"]
            lines = text.splitlines()
            assert len(lines) == len(base.splitlines()), (
                f"{case}: {record_key} line count grew "
                f"{len(base.splitlines())} -> {len(lines)}"
            )
            assert "\u2028" not in text, case
            assert "\x1b" not in text, case
            assert not any(line.startswith("```") for line in lines), case
            if record_key in ("handoff", "ws_append") or field_id == "title":
                if field_id == "pr.files":
                    # (v), positional. Every seat string rendered RAW into a
                    # record body, with the guard that keeps each safe:
                    #   pr.files entry, module :562/:611 -- no single regex:
                    #     ``_pr_fields`` refuses a multi-line entry :265, an
                    #     unsafe Unicode category :266-268, a leading "/" or
                    #     "\" :269 and a ".." part :272. These files rows are
                    #     unpinned, so a substring test is vacuous there: the
                    #     path survives on SOME line whether or not its "  - "
                    #     bullet prefix does.
                    #   pr.merged_at, :556/:605 -- ``_MERGED_RE`` :73, an
                    #     ``re.ASCII`` fullmatch.
                    #   workstream key, :565/:566/:602 -- ``_WS_RE`` :65 pins
                    #     it to ``[A-Z0-9]+(?:-[A-Z0-9]+)*``.
                    #   pr day, :566 -- ``_MERGED_RE.group(1)`` :305, so ASCII
                    #     digits and hyphens only.
                    # Pin the shape instead. Occurrences INSIDE a
                    # double-quoted scalar (``- path: "..."``,
                    # ``result: "...absent: ..."``) ride ``_q`` and keep
                    # (i)-(iv); positional law binds the raw occurrences:
                    # every line with an occurrence outside the quotes
                    # starts with the two-space bullet, at least one such
                    # line exists, no line equals the bare value, AND
                    # (v.1) on any rendered line whose first non-space token
                    # is a YAML key (``<key>:``, optionally after ``- ``) the
                    # value does not occur outside quotes.
                    def _raw_has_value(line: str) -> bool:
                        # Escape-aware: ``_q`` renders a literal double quote
                        # inside a quoted scalar as \" and a literal backslash
                        # as \\. A one-character lookbehind cannot tell \"
                        # (an escaped quote, still inside) from \\" (an
                        # escaped backslash, then the real closing quote), so
                        # it flips the inside/outside parity for every later
                        # occurrence on the same line. Rule: a ``"`` is a
                        # boundary only when the run of backslashes right
                        # before it has EVEN length. Each outside segment is
                        # tested on its own, so a match never spans a quoted
                        # scalar.
                        outside: list[str] = []
                        in_quotes = False
                        pos = 0
                        for m in re.finditer(r'(\\*)"', line):
                            if len(m.group(1)) % 2:
                                continue
                            if not in_quotes:
                                outside.append(line[pos:m.end() - 1])
                            in_quotes = not in_quotes
                            pos = m.end()
                        if not in_quotes:
                            outside.append(line[pos:])
                        return any(value in segment for segment in outside)

                    # The parity scan in _raw_has_value flips inside/outside
                    # at each boundary quote; a ``"`` in the value makes it
                    # ambiguous. Assert the value once, not per scanned line.
                    assert '"' not in value, (
                        "value carries a double quote: the quote-parity scan "
                        "cannot distinguish a boundary from the quoted text"
                    )
                    raw_lines = [
                        line for line in lines
                        if value in line and _raw_has_value(line)
                    ]
                    assert raw_lines, (
                        f"{case}: {record_key} renders no raw line with the"
                        f" value (occurrences: {[l for l in lines if value in l]!r})"
                    )
                    assert all(
                        line.startswith("  - ") for line in raw_lines
                    ), f"{case}: {record_key} unbulleted line {raw_lines!r}"
                    assert value not in lines, (
                        f"{case}: {record_key} renders a bare-value line"
                    )
                    yaml_key_offenders = [
                        line for line in lines
                        if _is_yaml_key_line(line) and _raw_has_value(line)
                    ]
                    assert not yaml_key_offenders, (
                        f"{case}: {record_key} value occurs outside quotes "
                        f"on a YAML key line {yaml_key_offenders!r}"
                    )
                else:
                    assert _escaped_form(value) in text, (
                        f"{case}: value did not survive in "
                        f"{_escaped_form(value)!r} form"
                    )


_YAML_KEY_LINE_CASES = [
    pytest.param("  - DEC:SRC-FILE: x", True, id="embedded-colon-key"),
    pytest.param("  - src-file: x", True, id="kebab-key"),
    pytest.param("  file.path: x", True, id="dotted-key"),
    pytest.param("merged-at: 2026-01-01", True, id="merged-at-date"),
    pytest.param('  - path: "lib/x.py"', True, id="quoted-value"),
    pytest.param("title:", True, id="bare-key-eol"),
    pytest.param("  - lib_x:y.py", False, id="colon-in-word"),
    pytest.param("  - C:/x.py", False, id="colon-then-slash"),
    pytest.param("  - a:b", False, id="colon-no-space"),
    pytest.param("  - lib/x.py - not named", False, id="raw-path-note"),
    pytest.param("  - DEC:KEY", False, id="citation-alone"),
    pytest.param("  - WS:AGENT-OS", False, id="ws-key-alone"),
]


@pytest.mark.parametrize("line,expected", _YAML_KEY_LINE_CASES)
def test_yaml_key_line_classifier_cases(line: str, expected: bool) -> None:
    """The lifted classifier is pinned on the twelve probe lines.

    An embedded-colon citation key such as ``  - DEC:SRC-FILE: x`` is a
    mapping to PyYAML and must classify as a key line; the same citation
    alone (``  - DEC:KEY``) is a scalar and must not.
    """
    assert _is_yaml_key_line(line) is expected


# --- item 4: trailing separators are refused by the category clause ---------

@pytest.mark.parametrize(
    "entry",
    [
        pytest.param("lib/x.py\n", id="trailing-lf"),
        pytest.param("lib/x.py\r", id="trailing-cr"),
        pytest.param("lib/x.py\u2028", id="trailing-line-separator"),
        pytest.param("lib/x.py\u200b", id="trailing-zero-width-space"),
        pytest.param("lib/x.py\x00", id="trailing-nul"),
    ],
)
def test_trailing_separator_file_entries_are_refused(
    tmp_path: Path, entry: str
) -> None:
    """A separator at the END of a ``pr.files`` entry is refused.

    ``splitlines()`` only sees a separator FOLLOWED by text
    (``"lib/x.py\\n".splitlines() == ["lib/x.py"]``), so the count clause
    (scripts/agentos_records_draft.py:265) is blind here; these ride entirely
    on the ``unicodedata.category`` clause (:266-268) scanning the LAST
    character. A category clause that scans only the interior (``entry[1:-1]``)
    accepts all five. Same rc and message as
    ``test_invisible_non_line_breakers_are_refused``.
    """
    # Premise 1: the count clause really sees one line -- only the category
    # scan of the final character can refuse this entry.
    assert len(entry.splitlines()) == 1, repr(entry)
    # Premise 2: the trailing character is in the guarded category set.
    assert unicodedata.category(entry[-1]) in {"Cc", "Cf", "Zl", "Zp"}, repr(entry)
    result, _path = _run(tmp_path, _payload(pr={"files": [entry]}))
    assert result.returncode == 2, f"{entry!r} was ACCEPTED"
    assert "pr.files entries must be single-line repo-relative paths" in result.stderr
    assert result.stdout == ""


# --- item 5: the admitted git subcommand set equals its comment -------------

def test_git_admits_exactly_cat_file_and_diff_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """TRIPWIRE: ``_git`` admits exactly ``cat-file`` and ``diff-tree``.

    The ``_GIT_HARDENING`` comment (scripts/agentos_records_draft.py:82-83)
    labels ``-c core.hooksPath=`` defense-in-depth BECAUSE ``_git`` accepts
    only these two read-only plumbing subcommands -- the set is why no
    recordable command can reach a hook. Widening the set makes that comment
    (and the hook measurement it cites) stale, so the admitted set is pinned
    empirically by probing which names ``_git`` lets reach ``subprocess.run``.
    """
    mod = _load_draft_module()

    def fake_run(argv, **kwargs):
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    admitted: list[str] = []
    for name in (
        "cat-file", "diff-tree", "status", "commit", "add", "checkout", "config",
        "fetch", "push", "apply", "init", "show", "grep", "hash-object", "am", "gc",
    ):
        try:
            mod._git(name, "HEAD", repo=tmp_path)
        except RuntimeError:
            continue
        admitted.append(name)
    assert set(admitted) == {"cat-file", "diff-tree"}, (
        f"_git now admits {sorted(admitted)}; the comment at "
        "scripts/agentos_records_draft.py:78-104 calls -c core.hooksPath= "
        "defense-in-depth only because _git accepts cat-file and diff-tree -- "
        "that comment goes stale on any widening. Re-adjudicate the hooksPath "
        "claim against the new subcommands or revert the widening."
    )
