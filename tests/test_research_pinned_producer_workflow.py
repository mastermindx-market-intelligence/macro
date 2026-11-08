"""Regression tests for the pinned research-producer selector in
``.github/workflows/research-ingest.yml``.

These tests exercise the ACTUAL extracted `run:` scripts of the first
mode-admission step and of the `ingest` step. Only the fixed installation
prefix (``/Volumes/Mastermind/runtime/research-producer``) is rewritten to a
temporary stub root inside the extracted test copy; every stub is a temporary
executable or manifest created under ``tmp_path``. No real launcher, store,
credential, network or service is ever invoked. The interpreter stub proxies
only the isolated stdlib manifest resolver to the test interpreter; launcher
calls are recorded without execution. The legacy `python` remains a PATH stub.

Fail-closed contract under test:
  * an empty selector keeps the unchanged legacy / materialize modes;
  * a malformed selector refuses in the FIRST step, before any effect;
  * a pinned selector combined with materialize_only refuses;
  * a verified pinned bundle launches the fixed interpreter with the exact
    isolated argv (including the original run id and attempt) and never
    touches the legacy CLI;
  * a hash mismatch, a missing bundle/manifest/interpreter, or a nonzero
    launcher rc records a nonzero rc in GITHUB_OUTPUT with zero legacy calls.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import shlex
import json
from pathlib import Path

import pytest
import yaml

WORKFLOW_REL = Path(".github") / "workflows" / "research-ingest.yml"
FIXED_PREFIX = "/Volumes/Mastermind/runtime/research-producer"
INTERPRETER_SUBPATH = (
    "dependencies/0c43d2132a6afaba75e5b5720c234d1b565679b650d7c04c024a1a12d711206a"
    "/venv/bin/python"
)
MASTERMIND_COMMIT = "a" * 40
LAUNCHER_SUBPATH = f"mastermind/{MASTERMIND_COMMIT}/ops/research_producer/launch.py"
# The valid selector is the REAL SHA-256 of the stub manifest bytes, so the
# workflow's digest verification passes against the stub bundle.
MANIFEST_BYTES = json.dumps({"schema": "mastermind.research_read_stage.v1", "state": "INERT_CANDIDATE", "mastermind_commit": MASTERMIND_COMMIT}).encode()
VALID_DIGEST = hashlib.sha256(MANIFEST_BYTES).hexdigest()
RUN_ID = "8675309"
RUN_ATTEMPT = "4"

PREPARATION_REFUSAL = (
    "::error title=research-ingest::pinned producer release preparation refused; "
    "nothing was ingested and legacy mode is not permitted"
)

LEGACY_TAIL = (
    'if [ "$MATERIALIZE_ONLY" = "true" ]; then\n'
    "  python -m scripts.ingest_research --require-store --materialize-only\n"
    "else\n"
    "  python -m scripts.ingest_research --require-store\n"
    "fi\n"
    'echo "rc=$?" >> "$GITHUB_OUTPUT"\n'
    "exit 0\n"
)

LEGACY_PLAIN_ARGV = ["-m", "scripts.ingest_research", "--require-store"]
LEGACY_MATERIALIZE_ARGV = LEGACY_PLAIN_ARGV + ["--materialize-only"]


# --------------------------------------------------------------------------- #
# workflow loading + step extraction
# --------------------------------------------------------------------------- #

def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _workflow_text() -> str:
    return (_repo_root() / WORKFLOW_REL).read_text(encoding="utf-8")


def _workflow_doc():
    text = _workflow_text()
    doc = yaml.safe_load(text)
    assert isinstance(doc, dict) and "jobs" in doc
    return doc


def _code(run: str) -> str:
    """Script text with full-line shell comments removed (for token checks)."""
    return "\n".join(
        line for line in run.splitlines() if not line.lstrip().startswith("#")
    )


def _step_by_name(doc: dict, name: str) -> dict:
    steps = doc["jobs"]["ingest"]["steps"]
    for step in steps:
        if step.get("name") == name:
            return step
    raise AssertionError(f"step {name!r} not found")


def _ingest_step(doc: dict) -> dict:
    for step in doc["jobs"]["ingest"]["steps"]:
        if step.get("id") == "ingest":
            return step
    raise AssertionError("step with id 'ingest' not found")


def _with_prefix_replaced(script: str, install_root: Path, expect_prefix: bool = True) -> str:
    """Rewrite ONLY the fixed installation prefix in the extracted copy."""
    if expect_prefix:
        assert FIXED_PREFIX in script, "extracted script lost the fixed install prefix"
    return script.replace(FIXED_PREFIX, str(install_root))


def _write_and_run(script: str, env: dict, tmp_path: Path, name: str):
    path = tmp_path / f"{name}.sh"
    path.write_text(script, encoding="utf-8")
    return subprocess.run(
        ["/bin/bash", "--noprofile", "--norc", "-e", "-o", "pipefail", str(path)],
        env=env,
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        timeout=120,
    )


# --------------------------------------------------------------------------- #
# stub executables + manifests
# --------------------------------------------------------------------------- #

def _write_stub(path: Path, argv_log_env: str) -> None:
    path.write_text(
        "#!/bin/bash\n"
        'printf \'%s\\0\' "$@" >> "${' + argv_log_env + '}"\n'
        'printf "\\n" >> "${' + argv_log_env + '}"\n'
        "if [ -n \"${" + argv_log_env + "_RC:-}\" ]; then\n"
        "  exit \"${" + argv_log_env + "_RC}\"\n"
        "fi\n"
        "exit 0\n",
        encoding="utf-8",
    )
    path.chmod(0o755)


def _install_root(tmp_path: Path) -> Path:
    return tmp_path / "install"


def _make_bundle(
    tmp_path: Path,
    digest: str = VALID_DIGEST,
    manifest_bytes: bytes | None = None,
    with_manifest: bool = True,
    with_interpreter: bool = True,
) -> Path:
    root = _install_root(tmp_path)
    bundle = root / "releases" / digest
    (bundle / LAUNCHER_SUBPATH).parent.mkdir(parents=True)
    if with_manifest:
        payload = manifest_bytes if manifest_bytes is not None else MANIFEST_BYTES
        (bundle / "manifest.json").write_bytes(payload)
    (bundle / "producer.json").write_text('{"engine": "stub"}\n', encoding="utf-8")
    (bundle / LAUNCHER_SUBPATH).write_text("# stub launcher\n", encoding="utf-8")
    if with_interpreter:
        interpreter = root / INTERPRETER_SUBPATH
        interpreter.parent.mkdir(parents=True, exist_ok=True)
        _write_stub(interpreter, "PINNED_STUB_ARGV_LOG")
        stub = interpreter.read_text()
        parser = ('#!/bin/bash\n'
            'if [ "$1" = "-I" ] && [ "$2" = "-B" ] && [ "$3" = "-" ]; then\n'
            '  exec ' + shlex.quote(sys.executable) + ' "$@"\nfi\n')
        interpreter.write_text(parser + stub.split('\n', 1)[1])
    return bundle


def _make_env(
    tmp_path: Path,
    producer_release: str | None = None,
    materialize_only: str | None = None,
    publish_forensics: str | None = None,
    bootstrap_forensics: str | None = None,
) -> dict:
    env = {"PATH": os.environ["PATH"], "LANG": "C", "LC_ALL": "C"}
    env["GITHUB_OUTPUT"] = str(tmp_path / "github_output.txt")
    Path(env["GITHUB_OUTPUT"]).write_text("", encoding="utf-8")
    env["GITHUB_RUN_ID"] = RUN_ID
    env["GITHUB_RUN_ATTEMPT"] = RUN_ATTEMPT
    env["PINNED_STUB_ARGV_LOG"] = str(tmp_path / "pinned_argv.log")
    env["LEGACY_STUB_ARGV_LOG"] = str(tmp_path / "legacy_argv.log")
    env.pop("PRODUCER_RELEASE", None)
    env.pop("MATERIALIZE_ONLY", None)
    env.pop("PUBLISH_FORENSICS", None)
    env.pop("BOOTSTRAP_FORENSICS", None)
    if producer_release is not None:
        env["PRODUCER_RELEASE"] = producer_release
    if materialize_only is not None:
        env["MATERIALIZE_ONLY"] = materialize_only
    if publish_forensics is not None:
        env["PUBLISH_FORENSICS"] = publish_forensics
    if bootstrap_forensics is not None:
        env["BOOTSTRAP_FORENSICS"] = bootstrap_forensics
    stub_bin = tmp_path / "stub-bin"
    stub_bin.mkdir(exist_ok=True)
    _write_stub(stub_bin / "python", "LEGACY_STUB_ARGV_LOG")
    env["PATH"] = os.pathsep.join([str(stub_bin), env.get("PATH", "")])
    return env


def _argv_calls(log_path: Path) -> list[list[str]]:
    """Parse the stub argv log: one invocation per line, NUL-separated argv."""
    if not log_path.exists():
        return []
    calls = []
    for raw in log_path.read_bytes().split(b"\n"):
        if not raw:
            continue
        parts = raw.split(b"\0")
        parts = [p for p in parts if p != b""]
        calls.append([p.decode("utf-8") for p in parts])
    return calls


def _output_rcs(env: dict) -> list[str]:
    path = Path(env["GITHUB_OUTPUT"])
    if not path.exists():
        return []
    rcs = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("rc="):
            rcs.append(line[len("rc="):])
    return rcs


def _run_ingest(tmp_path: Path, env: dict):
    doc = _workflow_doc()
    script = _with_prefix_replaced(_ingest_step(doc)["run"], _install_root(tmp_path))
    return _write_and_run(script, env, tmp_path, "ingest_step")


def _run_admission(tmp_path: Path, env: dict):
    doc = _workflow_doc()
    script = _with_prefix_replaced(
        _step_by_name(doc, "admit one explicit producer mode")["run"],
        _install_root(tmp_path),
        expect_prefix=False,
    )
    return _write_and_run(script, env, tmp_path, "admission_step")


# --------------------------------------------------------------------------- #
# legacy modes (empty selector)
# --------------------------------------------------------------------------- #

def test_empty_selector_runs_legacy_cli_and_never_the_pinned_bundle(tmp_path):
    env = _make_env(tmp_path)
    proc = _run_ingest(tmp_path, env)
    assert proc.returncode == 0, proc.stderr
    assert _argv_calls(Path(env["LEGACY_STUB_ARGV_LOG"])) == [LEGACY_PLAIN_ARGV]
    assert _argv_calls(Path(env["PINNED_STUB_ARGV_LOG"])) == []
    assert _output_rcs(env) == ["0"]


def test_empty_selector_materialize_mode_keeps_materialize_flag(tmp_path):
    env = _make_env(tmp_path, materialize_only="true")
    proc = _run_ingest(tmp_path, env)
    assert proc.returncode == 0, proc.stderr
    assert _argv_calls(Path(env["LEGACY_STUB_ARGV_LOG"])) == [LEGACY_MATERIALIZE_ARGV]
    assert _argv_calls(Path(env["PINNED_STUB_ARGV_LOG"])) == []
    assert _output_rcs(env) == ["0"]


# --------------------------------------------------------------------------- #
# admission step (first step, before checkout/pip/ingest)
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize(
    "bad",
    [
        "AB12CD34EF567890AB12CD34EF567890AB12CD34EF567890AB12CD34EF567890",  # uppercase
        VALID_DIGEST[:-1],  # 63 chars
        VALID_DIGEST + "0",  # 65 chars
        VALID_DIGEST + "\n",  # grep must not accept one line of a malformed selector
        "\n" + VALID_DIGEST,
        VALID_DIGEST + "\nunexpected",
        "zz" * 32,  # not hex
        "releases/latest",  # human-readable tag, not a digest
        "   ",
        f"{VALID_DIGEST[:32]}; rm -rf \"$HOME\"",  # shell metacharacters
        f"$({VALID_DIGEST[:32]})",  # command substitution attempt
    ],
)
def test_malformed_selector_refuses_in_first_step_before_any_effect(tmp_path, bad):
    env = _make_env(tmp_path, producer_release=bad)
    proc = _run_admission(tmp_path, env)
    assert proc.returncode != 0, proc.stdout
    assert "::error" in proc.stdout or "::error" in proc.stderr
    # Nothing was executed to probe the installation: the admission script must
    # not even reference the fixed installation prefix.
    doc = _workflow_doc()
    assert FIXED_PREFIX not in _step_by_name(
        doc, "admit one explicit producer mode"
    )["run"]


def test_malformed_selector_with_metacharacters_executes_nothing(tmp_path):
    marker = tmp_path / "pwned-marker"
    env = _make_env(
        tmp_path, producer_release=f"{VALID_DIGEST[:32]}; touch '{marker}'"
    )
    proc = _run_admission(tmp_path, env)
    assert proc.returncode != 0
    assert not marker.exists()
    assert _argv_calls(Path(env["LEGACY_STUB_ARGV_LOG"])) == []
    assert _argv_calls(Path(env["PINNED_STUB_ARGV_LOG"])) == []


def test_valid_selector_and_empty_selector_both_admit(tmp_path):
    ok = _run_admission(tmp_path, _make_env(tmp_path, producer_release=VALID_DIGEST))
    assert ok.returncode == 0, ok.stdout
    empty = _run_admission(tmp_path, _make_env(tmp_path))
    assert empty.returncode == 0, empty.stdout


def test_pinned_selector_with_materialize_only_refuses_in_first_step(tmp_path):
    env = _make_env(
        tmp_path, producer_release=VALID_DIGEST, materialize_only="true"
    )
    proc = _run_admission(tmp_path, env)
    assert proc.returncode != 0, proc.stdout
    assert "materialize_only" in (proc.stdout + proc.stderr)
    assert _argv_calls(Path(env["PINNED_STUB_ARGV_LOG"])) == []
    assert _argv_calls(Path(env["LEGACY_STUB_ARGV_LOG"])) == []


def test_existing_forensics_combination_guard_is_preserved(tmp_path):
    env = _make_env(
        tmp_path,
        materialize_only="true",
        publish_forensics="true",
    )
    proc = _run_admission(tmp_path, env)
    assert proc.returncode != 0, proc.stdout
    assert (
        "::error::materialize_only cannot be combined with forensics publication "
        "or bootstrap" in proc.stdout
    )
    env = _make_env(
        tmp_path,
        materialize_only="true",
        bootstrap_forensics="true",
    )
    proc = _run_admission(tmp_path, env)
    assert proc.returncode != 0, proc.stdout


# --------------------------------------------------------------------------- #
# pinned ingest: verified launch
# --------------------------------------------------------------------------- #

def test_valid_digest_launches_pinned_interpreter_with_exact_isolated_argv(tmp_path):
    _make_bundle(tmp_path)
    env = _make_env(tmp_path, producer_release=VALID_DIGEST)
    proc = _run_ingest(tmp_path, env)
    assert proc.returncode == 0, proc.stderr
    bundle = _install_root(tmp_path) / "releases" / VALID_DIGEST
    expected = [
        "-I",
        "-B",
        str(bundle / LAUNCHER_SUBPATH),
        "--config",
        str(bundle / "producer.json"),
        "--run-id",
        RUN_ID,
        "--attempt",
        RUN_ATTEMPT,
        "--execute",
    ]
    assert _argv_calls(Path(env["PINNED_STUB_ARGV_LOG"])) == [expected]
    assert _argv_calls(Path(env["LEGACY_STUB_ARGV_LOG"])) == []
    assert _output_rcs(env) == ["0"]


def test_pinned_mode_refuses_materialize_flag_even_without_admission(tmp_path):
    # The launch boundary also refuses, even if admission was not executed.
    _make_bundle(tmp_path)
    env = _make_env(
        tmp_path, producer_release=VALID_DIGEST, materialize_only="true"
    )
    proc = _run_ingest(tmp_path, env)
    assert proc.returncode == 0, proc.stderr
    assert _argv_calls(Path(env["LEGACY_STUB_ARGV_LOG"])) == []
    assert _argv_calls(Path(env["PINNED_STUB_ARGV_LOG"])) == []
    assert _output_rcs(env) == ["1"]
    assert "materialize_only" in proc.stdout


# --------------------------------------------------------------------------- #
# pinned ingest: preparation refusals (fail closed, zero legacy calls)
# --------------------------------------------------------------------------- #

def _assert_preparation_refusal(tmp_path, producer_release=VALID_DIGEST, **bundle_kw):
    _make_bundle(tmp_path, **bundle_kw)
    env = _make_env(tmp_path, producer_release=producer_release)
    proc = _run_ingest(tmp_path, env)
    assert proc.returncode == 0, proc.stderr  # never-raise step: rc via output
    assert _output_rcs(env) == ["1"], proc.stdout
    assert PREPARATION_REFUSAL in proc.stdout
    assert _argv_calls(Path(env["PINNED_STUB_ARGV_LOG"])) == []
    assert _argv_calls(Path(env["LEGACY_STUB_ARGV_LOG"])) == []
    return proc


def test_hash_mismatch_refuses_and_never_falls_back(tmp_path):
    _assert_preparation_refusal(tmp_path, manifest_bytes=b'{"release_sha256": "tampered"}\n')


def test_missing_bundle_refuses_and_never_falls_back(tmp_path):
    # Nothing installed at all under the prefix.
    _install_root(tmp_path).mkdir(parents=True)
    env = _make_env(tmp_path, producer_release=VALID_DIGEST)
    proc = _run_ingest(tmp_path, env)
    assert proc.returncode == 0, proc.stderr
    assert _output_rcs(env) == ["1"]
    assert PREPARATION_REFUSAL in proc.stdout
    assert _argv_calls(Path(env["PINNED_STUB_ARGV_LOG"])) == []
    assert _argv_calls(Path(env["LEGACY_STUB_ARGV_LOG"])) == []


def test_missing_manifest_refuses_and_never_falls_back(tmp_path):
    _assert_preparation_refusal(tmp_path, with_manifest=False)


def test_missing_interpreter_refuses_and_never_falls_back(tmp_path):
    _assert_preparation_refusal(tmp_path, with_interpreter=False)


@pytest.mark.parametrize("missing", ["producer.json", LAUNCHER_SUBPATH])
def test_missing_launcher_or_config_refuses_and_never_falls_back(tmp_path, missing):
    _make_bundle(tmp_path)
    bundle = _install_root(tmp_path) / "releases" / VALID_DIGEST
    (bundle / missing).unlink()
    env = _make_env(tmp_path, producer_release=VALID_DIGEST)
    proc = _run_ingest(tmp_path, env)
    assert _output_rcs(env) == ["1"]
    assert PREPARATION_REFUSAL in proc.stdout
    assert _argv_calls(Path(env["PINNED_STUB_ARGV_LOG"])) == []
    assert _argv_calls(Path(env["LEGACY_STUB_ARGV_LOG"])) == []


def test_refusal_message_does_not_echo_the_selector_or_paths(tmp_path):
    noisy = f"{VALID_DIGEST[:32]}with 'quotes' and $backticks"
    proc = _assert_preparation_refusal(tmp_path, producer_release=noisy)
    assert noisy not in proc.stdout
    assert FIXED_PREFIX not in proc.stdout


# --------------------------------------------------------------------------- #
# pinned ingest: nonzero launcher rc propagates, no fallback
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("child_rc", ["2", "7", "137"])
def test_nonzero_launcher_rc_is_recorded_and_legacy_is_never_called(
    tmp_path, child_rc
):
    _make_bundle(tmp_path)
    env = _make_env(tmp_path, producer_release=VALID_DIGEST)
    env["PINNED_STUB_ARGV_LOG_RC"] = child_rc
    proc = _run_ingest(tmp_path, env)
    assert proc.returncode == 0, proc.stderr  # rc is propagated via GITHUB_OUTPUT
    assert _output_rcs(env) == [child_rc]
    assert "legacy fallback is not permitted" in proc.stdout
    assert len(_argv_calls(Path(env["PINNED_STUB_ARGV_LOG"]))) == 1
    assert _argv_calls(Path(env["LEGACY_STUB_ARGV_LOG"])) == []


# --------------------------------------------------------------------------- #
# parsed YAML invariants (no new scheduler/job/upload/retry; untouched lanes)
# --------------------------------------------------------------------------- #

def test_workflow_invariants_unchanged_and_pinned_wiring_is_scoped():
    doc = _workflow_doc()
    text = _workflow_text()

    # Existing modes/schedule remain, plus the exclusive read-only resource mode.
    assert doc[True]["workflow_dispatch"]["inputs"].keys() == {
        "materialize_only",
        "publish_forensics",
        "bootstrap_forensics_sources",
        "run_census",
        "qualify_discovery_only",
    }
    assert doc[True]["schedule"] == [{"cron": "0 * * * *"}]

    # Concurrency, permissions, runner, timeout unchanged.
    concurrency = doc["concurrency"]
    assert concurrency["group"] == "research-ingest"
    assert concurrency["cancel-in-progress"] is False
    assert doc["permissions"] == {"contents": "write"}
    job = doc["jobs"]["ingest"]
    assert job["runs-on"] == ["self-hosted", "macstudio-light"]
    assert job["timeout-minutes"] == 15
    assert list(doc["jobs"].keys()) == ["ingest"]

    # Job secrets namespace unchanged; the selector is a vars mapping.
    assert "RESEARCH_VAULT_PRODUCER_RELEASE" not in job["env"]
    secret_keys = {k for k in job["env"] if k.startswith("R2")}
    assert secret_keys == {
        "R2_ENDPOINT",
        "R2_ACCESS_KEY_ID",
        "R2_SECRET_ACCESS_KEY",
        "R2_BUCKET",
        "R2_RESEARCH_ENDPOINT",
        "R2_RESEARCH_ACCESS_KEY_ID",
        "R2_RESEARCH_SECRET_ACCESS_KEY",
        "R2_RESEARCH_BUCKET",
    }

    # One exclusive read-only step; no new scheduler/job/dispatch/upload/retry.
    steps = job["steps"]
    identity = [
        (s.get("name"), s.get("id"), s.get("uses")) for s in steps
    ]
    assert identity == [
        ("admit one explicit producer mode", None, None),
        (None, "checkout", "actions/checkout@v4"),
        ("python 3.12 (Homebrew venv — self-hosted runner)", "python_setup", None),
        (None, "pip_install", None),
        ("preflight — poppler pdftotext (HOST dependency)", "preflight", None),
        ("bootstrap Filing Forensics private state", None, None),
        ("research vault ingest (hourly)", "ingest", None),
        ("read-only full-body resource qualification", None, None),
        ("commit catalog snapshot (salvage-push)", None, None),
        ("grade Research Vault source-content freshness", "source_freshness", None),
        ("research vault id-set census (read-only)", None, None),
        ("upload census report", None, "actions/upload-artifact@v4"),
        ("fail the lane if ingest or source freshness failed", None, None),
    ]
    # The admission step is FIRST: selector refusal precedes checkout/pip/ingest.
    assert steps[0]["name"] == "admit one explicit producer mode"
    assert steps[1].get("id") == "checkout"
    assert text.count("actions/upload-artifact@v4") == 1
    assert "schedule:" in text
    assert text.count("cron:") == 1
    assert "kill" not in text
    assert text.count("for i in 1 2 3 4 5") == 1  # only the original salvage retry

    # Census + forensics + salvage + final propagation untouched.
    assert "python -m scripts.research_vault_census --json" in text
    assert "python -m scripts.build_fundamental_forensics --publish-private" in text
    assert "research-vault-census" in text
    assert 'python -m scripts.check_research_vault_source_freshness "${args[@]}"' in text
    assert '. "${GITHUB_WORKSPACE:-.}/scripts/ci/push_retry.sh"' in text
    assert '${{ steps.ingest.outputs.rc }}' in text
    assert '${{ steps.source_freshness.outputs.rc }}' in text
    assert "if: ${{ always() && steps.checkout.outcome == 'success' && !inputs.materialize_only && !inputs.qualify_discovery_only }}" in text


def test_admission_step_admits_the_selector_from_the_same_variable():
    doc = _workflow_doc()
    step = _step_by_name(doc, "admit one explicit producer mode")
    assert step["env"]["PRODUCER_RELEASE"] == (
        "${{ vars.RESEARCH_VAULT_PRODUCER_RELEASE }}"
    )
    run = step["run"]
    # Values are matched on stdin, never re-parsed by the shell.
    assert "LC_ALL=C grep -Eq '^[0-9a-f]{64}$'" in run
    assert "eval" not in _code(run) and "source " not in _code(run)
    # The pre-existing forensics guard text is intact, unchanged, and first.
    assert run.index('if [ "$MATERIALIZE_ONLY" = "true" ] && { [ "$PUBLISH_FORENSICS"') < run.index(
        'grep -Eq'
    )


def test_ingest_step_pinned_branch_is_fixed_and_scoped():
    doc = _workflow_doc()
    step = _ingest_step(doc)
    assert step["id"] == "ingest"
    assert step["env"]["PRODUCER_RELEASE"] == (
        "${{ vars.RESEARCH_VAULT_PRODUCER_RELEASE }}"
    )
    run = step["run"]
    assert "eval" not in _code(run) and "source " not in _code(run)

    # Legacy branch is byte-identical and remains the fall-through tail.
    assert run.endswith(LEGACY_TAIL)
    assert run.index("set +e") < run.index('if [ -n "${PRODUCER_RELEASE:-}" ]')
    assert run.index('if [ -n "${PRODUCER_RELEASE:-}" ]') < run.index(
        'if [ "$MATERIALIZE_ONLY" = "true" ]; then'
    )

    # Exactly the two fixed installation paths, under the one fixed prefix.
    assert run.count(FIXED_PREFIX) == 2
    assert (
        f'bundle="{FIXED_PREFIX}/releases/$PRODUCER_RELEASE"' in run
    )
    assert (
        f'pinned_python="{FIXED_PREFIX}/{INTERPRETER_SUBPATH}"' in run
    )

    # Manifest digest is verified against the selector before launch.
    assert 'manifest_digest="$(shasum -a 256 "$bundle/manifest.json"' in run
    assert 'manifest_digest="$(sha256sum "$bundle/manifest.json"' in run
    assert '[ "$manifest_digest" = "$PRODUCER_RELEASE" ]' in run

    # Fixed interpreter, isolated flags, original run id + attempt, quoted paths.
    launch_line = [
        line for line in run.splitlines() if "--execute" in line
    ]
    assert 'launcher="$bundle/mastermind/$mastermind_commit/ops/research_producer/launch.py"' in run
    assert run.index('[ "$manifest_digest" = "$PRODUCER_RELEASE" ]') < run.index('mastermind_commit=')
    assert "stream.read(4 * 1024 * 1024 + 1)" in run
    assert "object_pairs_hook=unique" in run
    assert '[ -f "$launcher" ]' in run
    assert len(launch_line) == 1
    assert launch_line[0].strip() == (
        '"$pinned_python" -I -B "$launcher" '
        '--config "$bundle/producer.json" --run-id "$GITHUB_RUN_ID" '
        '--attempt "$GITHUB_RUN_ATTEMPT" --execute'
    )

    # Refusals record a nonzero rc and never fall back; the fixed refusal text
    # carries no private config or log body.
    assert run.count(PREPARATION_REFUSAL) == 3
    assert 'echo "rc=$pinned_rc" >> "$GITHUB_OUTPUT"' in run
    assert "legacy fallback is not permitted" in run
    assert FIXED_PREFIX not in PREPARATION_REFUSAL


@pytest.mark.parametrize("qualification", [False, True])
@pytest.mark.parametrize("checkout", ["skipped", "failure", "success"])
@pytest.mark.parametrize("step_name", [
    "commit catalog snapshot (salvage-push)",
    "grade Research Vault source-content freshness",
    "research vault id-set census (read-only)",
    "upload census report",
])
def test_post_steps_require_current_checkout_even_with_always(checkout, step_name, qualification):
    # These workflow predicates are conjunctions. Evaluate their actual terms for
    # a refused admission (checkout skipped), failed checkout, and a later ingest
    # failure after a successful checkout. always() remains true in all cases:
    # https://docs.github.com/en/actions/reference/workflows-and-actions/expressions#always
    condition = _step_by_name(_workflow_doc(), step_name)["if"]
    terms = [term.strip() for term in condition.removeprefix("${{").removesuffix("}}").split("&&")]
    values = {
        "always()": True,
        "steps.checkout.outcome == 'success'": checkout == "success",
        "!inputs.materialize_only": True,
        "github.event_name == 'workflow_dispatch'": True,
        "inputs.run_census": True,
        "!inputs.qualify_discovery_only": not qualification,
    }
    assert "always()" in terms  # Preserve salvage/census after an ingest failure.
    allowed = all(values[term] for term in terms)
    assert allowed is (checkout == "success" and not qualification)


@pytest.mark.parametrize("locale_name", ["C", "en_US.UTF-8"])
@pytest.mark.parametrize("value", ["é" * 64, "à" * 64, "ｅ" * 64])
def test_selector_rejects_collating_unicode_in_caller_locale(tmp_path, locale_name, value):
    env = _make_env(tmp_path, producer_release=value)
    env.update(LANG=locale_name, LC_ALL=locale_name)
    proc = _run_admission(tmp_path, env)
    assert proc.returncode != 0
    assert "exactly 64 lowercase hex" in proc.stdout
    assert _argv_calls(Path(env["PINNED_STUB_ARGV_LOG"])) == []


@pytest.mark.parametrize('payload', [
    b'[]', b'{}', b'{broken',
    json.dumps({'schema': 'wrong', 'state': 'INERT_CANDIDATE', 'mastermind_commit': MASTERMIND_COMMIT}).encode(),
    json.dumps({'schema': 'mastermind.research_read_stage.v1', 'state': 'ACTIVE', 'mastermind_commit': MASTERMIND_COMMIT}).encode(),
    *[json.dumps({'schema': 'mastermind.research_read_stage.v1', 'state': 'INERT_CANDIDATE', 'mastermind_commit': value}).encode()
      for value in (None, 123, 'A' * 40, 'a' * 39, '../outside', '$(touch marker)')],
    ('{"schema":"mastermind.research_read_stage.v1","state":"INERT_CANDIDATE",'
     '"mastermind_commit":"' + MASTERMIND_COMMIT + '","mastermind_commit":"' + MASTERMIND_COMMIT + '"}').encode(),
    MANIFEST_BYTES + b' ' * (4 * 1024 * 1024),
])
def test_matching_digest_with_invalid_locator_manifest_never_launches(tmp_path, payload):
    digest = hashlib.sha256(payload).hexdigest()
    _make_bundle(tmp_path, digest=digest, manifest_bytes=payload)
    env = _make_env(tmp_path, producer_release=digest)
    proc = _run_ingest(tmp_path, env)
    assert proc.returncode == 0
    assert PREPARATION_REFUSAL in proc.stdout
    assert _output_rcs(env) == ['1']
    assert _argv_calls(Path(env['PINNED_STUB_ARGV_LOG'])) == []
    assert _argv_calls(Path(env['LEGACY_STUB_ARGV_LOG'])) == []
    assert not (tmp_path / 'marker').exists()


def test_old_flat_launcher_is_never_a_layout_fallback(tmp_path):
    bundle = _make_bundle(tmp_path)
    (bundle / LAUNCHER_SUBPATH).unlink()
    flat = bundle / 'mastermind/ops/research_producer/launch.py'
    flat.parent.mkdir(parents=True)
    flat.write_text('# obsolete unverified flat entry\n')
    env = _make_env(tmp_path, producer_release=VALID_DIGEST)
    proc = _run_ingest(tmp_path, env)
    assert PREPARATION_REFUSAL in proc.stdout
    assert _output_rcs(env) == ['1']
    assert _argv_calls(Path(env['PINNED_STUB_ARGV_LOG'])) == []
    assert _argv_calls(Path(env['LEGACY_STUB_ARGV_LOG'])) == []



def test_locator_rejects_manifest_replaced_after_shell_hash(tmp_path):
    bundle = _make_bundle(tmp_path)
    replacement = tmp_path / 'replacement-manifest.json'
    replacement.write_text(json.dumps({'schema': 'mastermind.research_read_stage.v1',
        'state': 'INERT_CANDIDATE', 'mastermind_commit': 'b' * 40}))
    alternate = bundle / ('mastermind/' + 'b' * 40 + '/ops/research_producer/launch.py')
    alternate.parent.mkdir(parents=True)
    alternate.write_text('# different commit-root entry\n')
    interpreter = _install_root(tmp_path) / INTERPRETER_SUBPATH
    stub = interpreter.read_text()
    command = '  exec ' + shlex.quote(sys.executable) + ' "$@"'
    assert stub.count(command) == 1
    interpreter.write_text(stub.replace(command,
        '  cp ' + shlex.quote(str(replacement)) + ' "$4"\n' + command))
    env = _make_env(tmp_path, producer_release=VALID_DIGEST)
    proc = _run_ingest(tmp_path, env)
    assert PREPARATION_REFUSAL in proc.stdout
    assert _output_rcs(env) == ['1']
    assert _argv_calls(Path(env['PINNED_STUB_ARGV_LOG'])) == []
    assert _argv_calls(Path(env['LEGACY_STUB_ARGV_LOG'])) == []
