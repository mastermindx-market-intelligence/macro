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
