"""
tests/test_ruling_graph.py — Test suite for the Ruling Graph v1 infrastructure.

Tests
-----
1.  yaml_loads          — config/ruling_graph.yml loads without YAML error
2.  schema_vocab_valid  — build module's validator returns no errors on the real graph
3.  source_quotes_present — every source_quote is a verbatim substring of source_doc
4.  check_flag_passes   — build_ruling_graph.py --check passes (committed outputs match)
5.  determinism_json    — generate JSON twice → identical bytes
6.  determinism_md      — generate MD twice → identical bytes
7.  public_json_no_internal — site JSON contains only public_research rows
8.  public_json_no_denylist — site JSON contains no denylist tokens
9.  selftest_passes     — check_ruling_conflicts.py --selftest exits 0
10. w2_respects_today   — RULING_GRAPH_TODAY env changes W2 expired-clock detection
11. cl_rows_present     — RUL-CL-1 through RUL-CL-14 all exist and are nondelegable
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

# ---------------------------------------------------------------------------
# Repo root and paths
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parent.parent
_RULING_YML = _REPO_ROOT / "config" / "ruling_graph.yml"
_OUT_JSON = _REPO_ROOT / "site" / "neuralwebdata" / "ruling_graph.json"
_OUT_MD = _REPO_ROOT / "docs" / "NEURAL_WEB_CASE_LAW.md"

# ---------------------------------------------------------------------------
# Import build module
# ---------------------------------------------------------------------------
_build_spec = importlib.util.spec_from_file_location(
    "build_ruling_graph",
    _REPO_ROOT / "scripts" / "build_ruling_graph.py",
)
_build_mod = importlib.util.module_from_spec(_build_spec)  # type: ignore[arg-type]
_build_spec.loader.exec_module(_build_mod)  # type: ignore[union-attr]

# Import conflict checker module
_conflict_spec = importlib.util.spec_from_file_location(
    "check_ruling_conflicts",
    _REPO_ROOT / "scripts" / "check_ruling_conflicts.py",
)
_conflict_mod = importlib.util.module_from_spec(_conflict_spec)  # type: ignore[arg-type]
_conflict_spec.loader.exec_module(_conflict_mod)  # type: ignore[union-attr]

validate = _build_mod.validate
_emit_json = _build_mod._emit_json
_emit_md = _build_mod._emit_md
_check_w2 = _conflict_mod._check_w2


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def raw_data() -> dict:
    """Load the raw YAML once for the module."""
    with _RULING_YML.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


@pytest.fixture(scope="module")
def rulings(raw_data: dict) -> list[dict]:
    return raw_data.get("rulings", [])


@pytest.fixture(scope="module")
def meta(raw_data: dict) -> dict:
    return raw_data.get("meta", {})


# ---------------------------------------------------------------------------
# Test 1: YAML loads
# ---------------------------------------------------------------------------

def test_yaml_loads():
    """config/ruling_graph.yml must load without YAML parse error."""
    assert _RULING_YML.exists(), f"ruling_graph.yml not found at {_RULING_YML}"
    with _RULING_YML.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    assert isinstance(data, dict), "ruling_graph.yml must parse to a dict"
    assert "meta" in data, "ruling_graph.yml must have a meta block"
    assert "rulings" in data, "ruling_graph.yml must have a rulings block"
    assert isinstance(data["rulings"], list), "rulings must be a list"


# ---------------------------------------------------------------------------
# Test 2: Schema / vocab validation clean (build module validator)
# ---------------------------------------------------------------------------

def test_schema_vocab_valid(raw_data: dict):
    """build_ruling_graph.validate() must return no errors on the real graph."""
    errors = validate(raw_data, _REPO_ROOT)
    assert errors == [], (
        f"Validator found {len(errors)} error(s):\n"
        + "\n".join(f"  {e}" for e in errors)
    )


# ---------------------------------------------------------------------------
# Test 3: Source quotes present verbatim in source_doc
# ---------------------------------------------------------------------------

def test_source_quotes_present(rulings: list[dict]):
    """Every source_quote must be a verbatim (whitespace-normalized) substring of source_doc."""
    failures = []
    for r in rulings:
        rid = r.get("ruling_id", "<missing>")
        sq = r.get("source_quote")
        sd = r.get("source_doc")
        if not sq or not sd:
            continue
        src_path = _REPO_ROOT / sd
        if not src_path.exists():
            failures.append(f"{rid}: source_doc not found: {sd}")
            continue
        src_text = src_path.read_text(encoding="utf-8", errors="replace")
        sq_norm = " ".join(sq.split())
        src_norm = " ".join(src_text.split())
        if sq_norm not in src_norm:
            failures.append(
                f"{rid}: source_quote not found in {sd}. "
                f"First 80 chars: {sq_norm[:80]!r}"
            )
    assert not failures, (
        f"{len(failures)} source_quote failure(s):\n"
        + "\n".join(f"  {f}" for f in failures)
    )


# ---------------------------------------------------------------------------
# Test 4: --check flag passes (committed outputs match regeneration)
# ---------------------------------------------------------------------------

def test_check_flag_passes():
    """build_ruling_graph.py --check must exit 0 (committed outputs match YAML)."""
    result = subprocess.run(
        [sys.executable, str(_REPO_ROOT / "scripts" / "build_ruling_graph.py"), "--check"],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"build_ruling_graph.py --check failed (exit {result.returncode}):\n"
        f"stdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )


# ---------------------------------------------------------------------------
# Test 5+6: Determinism — two consecutive generations must be byte-identical
# ---------------------------------------------------------------------------

def test_determinism_json(raw_data: dict):
    """Generating the JSON twice must produce identical strings."""
    first = _emit_json(raw_data, _RULING_YML)
    second = _emit_json(raw_data, _RULING_YML)
    assert first == second, "JSON generation is not deterministic"


def test_determinism_md(raw_data: dict):
    """Generating the Markdown twice must produce identical strings."""
    first = _emit_md(raw_data, _RULING_YML)
    second = _emit_md(raw_data, _RULING_YML)
    assert first == second, "Markdown generation is not deterministic"


# ---------------------------------------------------------------------------
# Test 7: Public JSON contains only public_research rows
# ---------------------------------------------------------------------------

def test_public_json_no_internal():
    """site/neuralwebdata/ruling_graph.json must contain only public_research rows."""
    assert _OUT_JSON.exists(), f"Public JSON not found at {_OUT_JSON}"
    with _OUT_JSON.open(encoding="utf-8") as fh:
        data = json.load(fh)
    public_rows = data.get("rulings", [])
    bad = [r.get("ruling_id", "<missing>") for r in public_rows
           if r.get("privacy_class") != "public_research"]
    assert not bad, (
        f"Site JSON contains non-public_research rows: {bad}"
    )


# ---------------------------------------------------------------------------
# Test 8: Public JSON contains no denylist tokens
# ---------------------------------------------------------------------------

def test_public_json_no_denylist(raw_data: dict):
    """site/neuralwebdata/ruling_graph.json must not contain any denylist tokens."""
    assert _OUT_JSON.exists(), f"Public JSON not found at {_OUT_JSON}"
    denylist = [t.lower() for t in raw_data.get("meta", {}).get("public_token_denylist", [])]
    site_text = _OUT_JSON.read_text(encoding="utf-8").lower()
    hits = [t for t in denylist if t in site_text]
    assert not hits, (
        f"Site JSON contains denylist token(s): {hits} (RUL-CL-9)"
    )


# ---------------------------------------------------------------------------
# Test 9: check_ruling_conflicts.py --selftest exits 0
# ---------------------------------------------------------------------------

def test_selftest_passes():
    """check_ruling_conflicts.py --selftest must exit 0."""
    result = subprocess.run(
        [sys.executable, str(_REPO_ROOT / "scripts" / "check_ruling_conflicts.py"), "--selftest"],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"check_ruling_conflicts.py --selftest failed (exit {result.returncode}):\n"
        f"stdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )


# ---------------------------------------------------------------------------
# Test 10: W2 respects RULING_GRAPH_TODAY
# ---------------------------------------------------------------------------

def test_w2_respects_today():
    """RULING_GRAPH_TODAY env must control the W2 expired-clock detection date."""
    fake_data = {
        "meta": {},
        "rulings": [
            {
                "ruling_id": "TEST-PAST-CLOCK",
                "come_back_on": "2020-01-01",
                "experiment_ref": None,
                "status": "deferred",
            },
            {
                "ruling_id": "TEST-FUTURE-CLOCK",
                "come_back_on": "2099-01-01",
                "experiment_ref": None,
                "status": "deferred",
            },
        ],
    }

    old_env = os.environ.get("RULING_GRAPH_TODAY")
    os.environ["RULING_GRAPH_TODAY"] = "2026-07-06"
    try:
        findings = _check_w2(fake_data, _REPO_ROOT)
    finally:
        if old_env is None:
            os.environ.pop("RULING_GRAPH_TODAY", None)
        else:
            os.environ["RULING_GRAPH_TODAY"] = old_env

    past_fired = any(f.get("ruling_id") == "TEST-PAST-CLOCK" for f in findings)
    future_fired = any(f.get("ruling_id") == "TEST-FUTURE-CLOCK" for f in findings)
    assert past_fired, "W2 should fire for come_back_on=2020-01-01 when today=2026-07-06"
    assert not future_fired, "W2 should NOT fire for come_back_on=2099-01-01 when today=2026-07-06"


# ---------------------------------------------------------------------------
# Test 11: RUL-CL-1 through RUL-CL-14 present and nondelegable
# ---------------------------------------------------------------------------

def test_cl_rows_present_and_nondelegable(rulings: list[dict]):
    """RUL-CL-1 through RUL-CL-14 must all exist and have nondelegable=True."""
    ruling_map = {r.get("ruling_id"): r for r in rulings}
    expected_ids = [f"RUL-CL-{i}" for i in range(1, 15)]
    missing = [rid for rid in expected_ids if rid not in ruling_map]
    assert not missing, f"Missing CL ruling IDs: {missing}"

    not_nondelegable = [
        rid for rid in expected_ids
        if not ruling_map[rid].get("nondelegable")
    ]
    assert not not_nondelegable, (
        f"CL rows that are not marked nondelegable=True: {not_nondelegable}"
    )


# ---------------------------------------------------------------------------
# Fail-closed CI diff coverage / exact tested-base transport regressions
# ---------------------------------------------------------------------------

def test_conflict_guard_fails_closed_without_git_diff(monkeypatch, capsys):
    """Missing history may not turn H1/H2/W1 into an accidental green run."""
    monkeypatch.setattr(_conflict_mod, "_get_changed_files", lambda _root: ([], False))
    monkeypatch.setattr(sys, "argv", ["check_ruling_conflicts.py"])
    assert _conflict_mod.main() == 2
    assert "H1/H2/W1" in capsys.readouterr().err


def test_conflict_guard_treats_failed_git_diff_as_unavailable(monkeypatch, tmp_path):
    """A valid merge-base is insufficient if changed-path enumeration fails."""
    def broken_diff(args, **_kwargs):
        if args[1] == "merge-base":
            return subprocess.CompletedProcess(args, 0, stdout="a" * 40 + "\n")
        if args[1] == "diff":
            return subprocess.CompletedProcess(args, 128, stdout="")
        return subprocess.CompletedProcess(args, 0, stdout="")

    monkeypatch.setattr(_conflict_mod.subprocess, "run", broken_diff)
    changed, available = _conflict_mod._get_changed_files(tmp_path)
    assert changed == []
    assert available is False


def test_ruling_ci_consumes_exact_base_without_network_refetch():
    """The ruling guard uses the planner's tested-base object, not moving main."""
    manifest = yaml.safe_load(
        (_REPO_ROOT / ".github" / "ci" / "legacy-jobs.yml").read_text(encoding="utf-8")
    )
    steps = manifest["jobs"]["ruling-graph"]["steps"]
    cmd = next(
        step["run"] for step in steps
        if step.get("name", "").startswith("conflict checker (hard fail")
    )
    assert "git fetch" not in cmd
    assert "TESTED_BASE_SHA" in cmd
    assert "git rev-list --parents -n 1 HEAD" in cmd
    assert "git merge-base --is-ancestor" in cmd
    assert "CI_DISABLE_BASE_REPLAY" in cmd
    assert "CI_TESTED_TREE_SHA" in cmd
    assert "head=$head_sha" in cmd
    assert 'RULING_DIFF_BASE="$TESTED_BASE_SHA"' in cmd


def test_trusted_pc_route_requires_two_parent_tested_merge(tmp_path):
    """Missing env pin is safe only at a proved two-parent synthetic merge."""
    manifest = yaml.safe_load(
        (_REPO_ROOT / ".github" / "ci" / "legacy-jobs.yml").read_text(encoding="utf-8")
    )
    cmd = next(
        step["run"] for step in manifest["jobs"]["ruling-graph"]["steps"]
        if step.get("name", "").startswith("conflict checker (hard fail")
    )
    # Execute the exact pre-check from the manifest, not the full graph checker
    # whose production inputs are intentionally absent from this temporary repo.
    prefix = cmd.split('RULING_DIFF_BASE="$TESTED_BASE_SHA" python ', 1)[0]
    script = prefix + '\nprintf "%s\\n" "$TESTED_BASE_SHA"\n'
    env = os.environ.copy()
    for key in ("TESTED_BASE_SHA", "CI_DISABLE_BASE_REPLAY",
                "CI_SEMANTIC_ROLE", "CI_BASE_SHA", "CI_TESTED_TREE_SHA",
                "TESTED_TREE_SHA", "GITHUB_REF", "GITHUB_EVENT_NAME"):
        env.pop(key, None)

    def run_checked(attributes=None):
        scoped_env = dict(env)
        scoped_env.update(attributes or {})
        return subprocess.run(
            ["bash", "-eo", "pipefail", "-c", script],
            cwd=tmp_path, env=scoped_env, capture_output=True, text=True,
        )

    def git(*args):
        result = subprocess.run(
            ["git", "-C", str(tmp_path), *args],
            check=True, capture_output=True, text=True,
        )
        return result.stdout.strip()

    git("init", "-b", "main")
    git("config", "user.name", "CI Test")
    git("config", "user.email", "ci-test@example.invalid")
    (tmp_path / "base.txt").write_text("base\n", encoding="utf-8")
    git("add", ".")
    git("commit", "-m", "base")
    base_sha = git("rev-parse", "HEAD")
    single_parent = run_checked()
    assert single_parent.returncode != 0
    assert base_sha in single_parent.stdout

    valid_replay = {
        "CI_DISABLE_BASE_REPLAY": "1",
        "CI_SEMANTIC_ROLE": "main",
        "CI_BASE_SHA": base_sha,
        "CI_TESTED_TREE_SHA": base_sha,
    }
    replay = run_checked(valid_replay)
    assert replay.returncode == 0, replay.stderr
    assert replay.stdout.splitlines()[-1] == base_sha

    main_baseline = run_checked({
        "TESTED_BASE_SHA": base_sha,
        "TESTED_TREE_SHA": base_sha,
        "GITHUB_REF": "refs/heads/main",
        "GITHUB_EVENT_NAME": "workflow_dispatch",
    })
    assert main_baseline.returncode == 0, main_baseline.stderr

    git("checkout", "-b", "feature")
    (tmp_path / "feature.txt").write_text("feature\n", encoding="utf-8")
    git("add", ".")
    git("commit", "-m", "feature")
    git("checkout", "main")
    (tmp_path / "main.txt").write_text("main\n", encoding="utf-8")
    git("add", ".")
    git("commit", "-m", "main")
    expected_base = git("rev-parse", "HEAD")
    git("merge", "--no-ff", "-m", "synthetic merge", "feature")

    two_parent = run_checked()
    assert two_parent.returncode == 0, two_parent.stderr
    assert two_parent.stdout.splitlines()[-1] == expected_base

    hosted = run_checked({"TESTED_BASE_SHA": expected_base})
    assert hosted.returncode == 0, hosted.stderr
    assert hosted.stdout.splitlines()[-1] == expected_base

    wrong_hosted = run_checked({"TESTED_BASE_SHA": base_sha})
    assert wrong_hosted.returncode != 0
    assert git("rev-parse", "HEAD") in wrong_hosted.stdout
    assert "does not match first parent" in wrong_hosted.stdout

    rejected_replay = run_checked(valid_replay)
    assert rejected_replay.returncode != 0
    assert "invalid base-replay identity" in rejected_replay.stdout
    assert git("rev-parse", "HEAD") in rejected_replay.stdout


@pytest.mark.parametrize("check_name", ["H1", "H2", "W1"])
def test_renamed_current_files_remain_guarded_without_historical_blobs(
    tmp_path, monkeypatch, check_name,
):
    """A filtered shallow clone must scan rename destinations without hydration."""
    source = tmp_path / "source"
    source.mkdir()
    root = tmp_path / "filtered"
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update(
        GIT_AUTHOR_NAME="CI fixture", GIT_AUTHOR_EMAIL="ci@example.invalid",
        GIT_COMMITTER_NAME="CI fixture", GIT_COMMITTER_EMAIL="ci@example.invalid",
        GIT_NO_REPLACE_OBJECTS="1",
    )

    def git(*args, cwd=source, check=True, offline=False):
        scoped_env = dict(env)
        if offline:
            scoped_env.update(GIT_NO_LAZY_FETCH="1", GIT_ALLOW_PROTOCOL="")
        return subprocess.run(
            ["git", *args], cwd=cwd, env=scoped_env, check=check,
            capture_output=True, text=True,
        )

    git("init", "-b", "main")
    git("config", "uploadpack.allowFilter", "true")
    old = source / "notes" / "original.txt"
    old.parent.mkdir()
    stable = "".join(f"Stable fixture line {index:03d} with unchanged content.\n" for index in range(100))
    old.write_text(stable, encoding="utf-8")
    git("add", ".")
    git("commit", "-m", "original")
    base = git("rev-parse", "HEAD").stdout.strip()
    old_blob = git("rev-parse", "HEAD:notes/original.txt").stdout.strip()

    data = {
        "meta": {"known_fdr_families": [], "site_privacy_tokens": ["held_book"]},
        "rulings": [{
            "ruling_id": "TEST-KILLED-RENAME", "status": "killed",
            "match_terms": ["synthetic_rename_proposal"],
        }],
    }
    if check_name == "H1":
        relative = "config/renamed.yml"
        token = "_".join(["synthetic", "rename", "family"])
        violation = f"fdr_family: {token}\n"
    elif check_name == "H2":
        relative = "site/renamed.html"
        violation = "<div>held_book</div>\n"
    else:
        relative = "research/renamed.md"
        violation = "This proposes synthetic_rename_proposal.\n"
    destination = source / relative
    destination.parent.mkdir(parents=True)
    old.rename(destination)
    destination.write_text(stable + violation, encoding="utf-8")
    git("add", "-A")
    git("commit", "-m", "rename with guarded content")
    tested = git("rev-parse", "HEAD").stdout.strip()
    # Establish that this fixture really takes the similarity/rename path when
    # the historical blobs are available, rather than only testing an addition.
    rename = git("diff", "--find-renames", "--name-status", f"{base}...HEAD").stdout
    assert rename.startswith("R"), rename
    assert rename.rstrip().endswith("\t" + relative)

    git("clone", "--no-checkout", "--filter=blob:none", "--depth=2",
        source.as_uri(), str(root), cwd=tmp_path)
    git("checkout", "--detach", tested, cwd=root)
    git("config", "diff.renames", "true", cwd=root)
    assert git("cat-file", "-e", old_blob, cwd=root, check=False, offline=True).returncode != 0
    for key, value in {
        "GIT_NO_LAZY_FETCH": "1", "GIT_ALLOW_PROTOCOL": "",
        "GIT_NO_REPLACE_OBJECTS": "1", "RULING_DIFF_BASE": base,
    }.items():
        monkeypatch.setenv(key, value)

    changed, available = _conflict_mod._get_changed_files(root)
    assert available is True
    assert root / relative in changed
    assert root / "notes/original.txt" not in changed
    if check_name == "H2":
        findings = _conflict_mod._check_h2(data, changed, root, [])
    else:
        checker = _conflict_mod._check_h1 if check_name == "H1" else _conflict_mod._check_w1
        findings = checker(data, changed, root)
    assert any(
        finding["check"] == check_name and finding["file"] == relative
        and finding["severity"] == ("WARN" if check_name == "W1" else "HARD")
        for finding in findings
    ), findings
    assert git("cat-file", "-e", old_blob, cwd=root, check=False, offline=True).returncode != 0
