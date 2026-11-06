"""Focused cover for the hardened candidate proof gate.

One file, no repo imports, minutes to run: each test builds a throwaway
git tree, runs the REAL gate (``scripts/ci/govrev_candidate_proof.py``)
against it, and asserts the refusal class.  The scenarios are the two
fail-open branches the shell gate shipped plus the rebase hole beside
them:

* pytest missing refused even with the fatal ratchet disarmed;
* xdist absent degrades to a serial run;
* a real suite failure refuses and preserves the fatal gate;
* bytes or the set of files under ``data/government_revenue`` mutating
  DURING the prover refuses, including mutations porcelain cannot see
  (the legacy comparator is proven blind inline, so the discrimination
  is demonstrated, not asserted);
* a zero exit without a complete terminal summary (stub, junk output,
  "no tests ran") refuses;
* clean complete success mints a receipt that binds checkout, generation,
  inputs, outputs, source dependencies, and suite/prover versions;
* unchanged generation reuses the accepted proof — it is not a new proof;
* a changed post-rebuild generation fails the exact-generation witness
  (reproof required), while an unrelated-only checkout change with
  identical outputs passes it;
* a missing, truncated, or field-stripped receipt refuses publication.

Every test here fails on the pre-patch tree: the helper does not exist
there, and the workflow still carries the ``publishing UNPROVEN``
exit-0 branch (asserted by the wiring test at the bottom).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "scripts/ci/govrev_candidate_proof.py"

EXIT_PROOF_FAILED = 2
EXIT_PYTEST_UNAVAILABLE = 3
EXIT_TREE_MUTATED = 4
EXIT_INCOMPLETE_PROOF = 5
EXIT_RECEIPT_INVALID = 6
EXIT_WITNESS_MISMATCH = 10

SUITE_OK = "def test_proof_green():\n    assert True\n"
SUITE_FAIL = "def test_proof_boom():\n    assert False, 'intentional gate probe'\n"
SUITE_MUTATE_BYTES = (
    "from pathlib import Path\n"
    "\n"
    "def test_mutates_ignored_bytes():\n"
    '    with Path("data/government_revenue/.probe_scratch").open("ab") as fh:\n'
    '        fh.write(b"x")\n'
)
SUITE_SWAP_FILES = (
    "from pathlib import Path\n"
    "\n"
    "def test_swaps_ignored_files():\n"
    '    Path("data/government_revenue/.probe_vanish").unlink()\n'
    '    Path("data/government_revenue/.probe_added").write_text("replacement\\n")\n'
)


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def _proof_tree(tmp_path: Path, *, suite_body: str = SUITE_OK) -> Path:
    """A throwaway repo shaped like the live lane's proof boundary.

    Candidate artifacts (ledger/queue/state/status), the byte-identical
    public twin, the source documents the suites read directly, and a
    suite file the gate will actually execute.  The ``.probe_*`` files
    are git-ignored so a hostile suite can mutate data/ without moving
    porcelain -- the exact blindness the content inventory closes.
    """
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "proof-gate@test")
    _git(root, "config", "user.name", "proof-gate test")

    data = root / "data/government_revenue"
    site = root / "site/government-revenue-data"
    config = root / "config/government_revenue"
    tests = root / "tests"
    for directory in (data, site, config, tests):
        directory.mkdir(parents=True)

    queue = json.dumps({"content_id": "grcq1-proofgate", "counts": {"total": 1}})
    (data / "candidate_queue.json").write_text(queue, encoding="utf-8")
    (site / "candidates.json").write_text(queue, encoding="utf-8")
    (data / "candidate_ledger.jsonl").write_text(
        json.dumps({"candidate_id": "grc1-proofgate"}) + "\n", encoding="utf-8"
    )
    (data / "candidate_projection_state.json").write_text(
        json.dumps(
            {"generated_at": "2026-10-12T00:00:00+00:00", "queue_content_id": "grcq1-proofgate"}
        ),
        encoding="utf-8",
    )
    (data / "candidate_projection_status.json").write_text('{"status": "ok"}', encoding="utf-8")
    (data / "latest.json").write_text('{"generated_at": "2026-10-12T00:00:00+00:00"}', encoding="utf-8")
    (data / "workspace.json").write_text('{"bundle_id": "grw2-proofgate"}', encoding="utf-8")
    (data / "recipient_entity_graph.json").write_text('{"graph_id": "recipient-graph:test"}', encoding="utf-8")
    (config / "candidate_historical_suppressions.v1.json").write_text("{}", encoding="utf-8")

    (tests / "test_proof_gate_suite.py").write_text(suite_body, encoding="utf-8")
    (root / ".gitignore").write_text(
        "data/government_revenue/.probe_scratch\n"
        "data/government_revenue/.probe_vanish\n"
        "data/government_revenue/.probe_added\n"
        "__pycache__/\n",
        encoding="utf-8",
    )
    (data / ".probe_scratch").write_bytes(b"seed")
    (data / ".probe_vanish").write_text("doomed\n", encoding="utf-8")

    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "baseline")
    return root


def _run_gate(
    root: Path,
    *cli: str,
    fatal: str = "1",
    env_extra: dict[str, str] | None = None,
) -> subprocess.CompletedProcess:
    env = {
        **os.environ,
        "GOVREV_CANDIDATE_PROOF_FATAL": fatal,
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    env.pop("GITHUB_STEP_SUMMARY", None)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, str(HELPER), *cli],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(root),
    )


def _prove(root: Path, tmp_path: Path, *extra: str, fatal: str = "1",
           env_extra: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    return _run_gate(
        root,
        "prove",
        "--root", ".",
        "--suite", "tests/test_proof_gate_suite.py",
        "--receipt", str(tmp_path / "receipts" / "receipt.json"),
        "--log", str(tmp_path / "proof.log"),
        *extra,
        fatal=fatal,
        env_extra=env_extra,
    )


def _receipt_path(tmp_path: Path) -> Path:
    return tmp_path / "receipts" / "receipt.json"


def _porcelain(root: Path) -> str:
    return subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain", "--", "data/government_revenue"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout


# ── prover availability ────────────────────────────────────────────────────


@pytest.mark.parametrize("fatal", ["1", "0"])
def test_missing_pytest_refuses_in_every_mode(tmp_path: Path, fatal: str) -> None:
    """The old gate warned and published UNPROVEN; this refuses, ratchet or not."""
    root = _proof_tree(tmp_path)
    result = _prove(
        root,
        tmp_path,
        "--simulate-pytest-unavailable",
        fatal=fatal,
    )
    assert result.returncode == EXIT_PYTEST_UNAVAILABLE
    assert "refusing to publish an unproven" in (result.stdout + result.stderr)
    assert not _receipt_path(tmp_path).exists()


def test_xdist_absent_runs_serially_and_still_proves(tmp_path: Path) -> None:
    root = _proof_tree(tmp_path)
    result = _prove(root, tmp_path, "--simulate-xdist-unavailable")
    assert result.returncode == 0, result.stdout + result.stderr
    receipt = json.loads(_receipt_path(tmp_path).read_text(encoding="utf-8"))
    assert receipt["suite"]["serial"] is True
    assert receipt["suite"]["xdist_version"] is None
    assert "-n" not in receipt["suite"]["argv"]
    assert "running serially" in result.stdout


# ── proof outcome classes ──────────────────────────────────────────────────


def test_clean_complete_success_permits_and_mints_a_bound_receipt(tmp_path: Path) -> None:
    root = _proof_tree(tmp_path)
    result = _prove(root, tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    receipt = json.loads(_receipt_path(tmp_path).read_text(encoding="utf-8"))
    assert receipt["conclusion"] == "passed"
    assert receipt["pytest_exit"] == 0
    assert "1 passed" in receipt["pytest_summary"]
    head = _git(root, "rev-parse", "HEAD").strip()
    assert receipt["source_checkout"] == head
    assert receipt["generation"]["queue_content_id"] == "grcq1-proofgate"
    assert receipt["generation"]["ledger_line_count"] == 1
    # Output bytes are bound individually, public twin included.
    queue_bytes = (root / "data/government_revenue/candidate_queue.json").read_bytes()
    import hashlib

    assert receipt["outputs"]["data/government_revenue/candidate_queue.json"] == hashlib.sha256(queue_bytes).hexdigest()
    assert receipt["outputs"]["site/government-revenue-data/candidates.json"] == hashlib.sha256(queue_bytes).hexdigest()
    # And the witness accepts the generation it just proved.
    verify = _run_gate(root, "verify", "--root", ".", "--suite",
                       "tests/test_proof_gate_suite.py",
                       "--receipt", str(_receipt_path(tmp_path)))
    assert verify.returncode == 0, verify.stdout + verify.stderr


def test_real_pytest_failure_refuses_and_preserves_the_fatal_gate(tmp_path: Path) -> None:
    root = _proof_tree(tmp_path, suite_body=SUITE_FAIL)
    result = _prove(root, tmp_path, fatal="1")
    assert result.returncode == EXIT_PROOF_FAILED
    assert "refusing to publish an unproven candidate projection" in result.stdout
    assert not _receipt_path(tmp_path).exists()


def test_real_pytest_failure_with_ratchet_disarmed_still_mints_no_receipt(tmp_path: Path) -> None:
    """Disarming the old fatal flag cannot turn a real failure into proof."""
    root = _proof_tree(tmp_path, suite_body=SUITE_FAIL)
    result = _prove(root, tmp_path, fatal="0")
    assert result.returncode == EXIT_PROOF_FAILED
    assert "govrev candidate proof failed" in result.stdout
    assert not _receipt_path(tmp_path).exists()


# ── the prover must not write what it checks ───────────────────────────────


def test_same_porcelain_mutation_during_proof_refuses_and_legacy_was_blind(tmp_path: Path) -> None:
    root = _proof_tree(tmp_path, suite_body=SUITE_MUTATE_BYTES)
    # Reproduce the OLD guard by hand: porcelain over data/government_revenue
    # before and after the hostile suite runs is byte-identical, because the
    # mutated file is ignored.  The legacy comparator had exactly this view
    # and would have published.
    before = _porcelain(root)
    subprocess.run(
        [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "-q",
         "tests/test_proof_gate_suite.py"],
        cwd=str(root), capture_output=True, check=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    after = _porcelain(root)
    assert before == after, "legacy-blindness premise: porcelain must be unchanged here"
    assert (root / "data/government_revenue/.probe_scratch").read_bytes() == b"seedx"

    result = _prove(root, tmp_path)
    assert result.returncode == EXIT_TREE_MUTATED
    assert "mutated the tree" in result.stdout
    assert not _receipt_path(tmp_path).exists()


def test_file_deletion_and_addition_during_proof_refuses(tmp_path: Path) -> None:
    root = _proof_tree(tmp_path, suite_body=SUITE_SWAP_FILES)
    result = _prove(root, tmp_path)
    assert result.returncode == EXIT_TREE_MUTATED
    assert not _receipt_path(tmp_path).exists()
    # The set change really happened (the suite did run), so the refusal is
    # the guard's, not a collection error.
    assert not (root / "data/government_revenue/.probe_vanish").exists()
    assert (root / "data/government_revenue/.probe_added").exists()


# ── a zero status is not a proof ───────────────────────────────────────────


def _fake_pytest_package(tmp_path: Path, program: str) -> str:
    package_root = tmp_path / "fakebin" / "pytest"
    package_root.mkdir(parents=True, exist_ok=True)
    (package_root / "__init__.py").write_text("", encoding="utf-8")
    (package_root / "__main__.py").write_text(program, encoding="utf-8")
    return str(tmp_path / "fakebin")


@pytest.mark.parametrize(
    ("program", "label"),
    [
        ("import sys\nsys.exit(0)\n", "silent zero exit"),
        ("import sys\nprint('all good')\nsys.exit(0)\n", "junk without a summary"),
        ("import sys\nprint('no tests ran in 0.01s')\nsys.exit(0)\n", "no tests ran"),
    ],
)
def test_fake_zero_exit_lacking_full_proof_refuses(tmp_path: Path, program: str, label: str) -> None:
    """A stub pytest that exits 0 is not a green suite, whatever it prints."""
    root = _proof_tree(tmp_path)
    pythonpath = _fake_pytest_package(tmp_path, program)
    result = _prove(root, tmp_path, env_extra={"PYTHONPATH": pythonpath})
    assert result.returncode == EXIT_INCOMPLETE_PROOF, label
    assert "without a complete terminal summary" in result.stdout
    assert not _receipt_path(tmp_path).exists()


# ── receipt identity, reuse, and the exact-generation witness ─────────────


def test_unchanged_generation_reuses_the_accepted_proof(tmp_path: Path) -> None:
    root = _proof_tree(tmp_path)
    assert _prove(root, tmp_path).returncode == 0
    receipt_before = _receipt_path(tmp_path).read_bytes()
    result = _prove(root, tmp_path)
    assert result.returncode == 0
    assert "prior proof stands" in result.stdout
    # Unchanged output is unchanged: the SAME receipt, not a new proof.
    assert _receipt_path(tmp_path).read_bytes() == receipt_before


def test_missing_partial_or_stripped_receipt_refuses_publication(tmp_path: Path) -> None:
    root = _proof_tree(tmp_path)
    assert _prove(root, tmp_path).returncode == 0
    receipt = _receipt_path(tmp_path)
    full = json.loads(receipt.read_text(encoding="utf-8"))
    common = ("verify", "--root", ".", "--suite", "tests/test_proof_gate_suite.py")

    receipt.unlink()
    result = _run_gate(root, *common, "--receipt", str(receipt))
    assert result.returncode == EXIT_RECEIPT_INVALID
    assert "receipt missing" in result.stdout

    receipt.write_text('{"contract": "government_revenue.candidate_proof.v1", "conclu', encoding="utf-8")
    result = _run_gate(root, *common, "--receipt", str(receipt))
    assert result.returncode == EXIT_RECEIPT_INVALID

    stripped = dict(full)
    del stripped["outputs"]
    receipt.write_text(json.dumps(stripped), encoding="utf-8")
    result = _run_gate(root, *common, "--receipt", str(receipt))
    assert result.returncode == EXIT_RECEIPT_INVALID
    assert "partial" in result.stdout


def test_output_drift_after_the_fact_requires_reproof(tmp_path: Path) -> None:
    """Changed output bytes are not covered by the accepted proof."""
    root = _proof_tree(tmp_path)
    assert _prove(root, tmp_path).returncode == 0
    queue = root / "data/government_revenue/candidate_queue.json"
    queue.write_text(json.dumps({"content_id": "grcq1-rebuilt"}), encoding="utf-8")
    result = _run_gate(root, "verify", "--root", ".", "--suite",
                       "tests/test_proof_gate_suite.py", "--receipt", str(_receipt_path(tmp_path)))
    assert result.returncode == EXIT_WITNESS_MISMATCH
    assert "output drift" in result.stdout


def test_changed_post_rebuild_generation_requires_reproof(tmp_path: Path) -> None:
    """The rebase shape: source dependency AND outputs move; witness refuses.

    This is the hole the 2026-08-18 incident class lived in -- prove, then
    rebuild on a newer generation, then publish.  Source change must not
    blindly reuse the proof even when the checkout delta is otherwise clean.
    """
    root = _proof_tree(tmp_path)
    assert _prove(root, tmp_path).returncode == 0
    # A newer upstream generation: the reviewed manifest the suites read
    # directly changes, the rebuild emits different candidate bytes, and the
    # tree is committed -- exactly the retry loop's post-rebase state.
    (root / "config/government_revenue/candidate_historical_suppressions.v1.json").write_text(
        '{"reviewed_at": "2026-10-12T01:00:00+00:00"}', encoding="utf-8"
    )
    queue = json.dumps({"content_id": "grcq1-rebuilt", "counts": {"total": 2}})
    (root / "data/government_revenue/candidate_queue.json").write_text(queue, encoding="utf-8")
    (root / "site/government-revenue-data/candidates.json").write_text(queue, encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "rebase rebuild")
    result = _run_gate(root, "verify", "--root", ".", "--suite",
                       "tests/test_proof_gate_suite.py", "--receipt", str(_receipt_path(tmp_path)))
    assert result.returncode == EXIT_WITNESS_MISMATCH
    # And reproof covers the new generation, binding the new checkout.
    reproved = _prove(root, tmp_path)
    assert reproved.returncode == 0, reproved.stdout + reproved.stderr
    receipt = json.loads(_receipt_path(tmp_path).read_text(encoding="utf-8"))
    assert receipt["generation"]["queue_content_id"] == "grcq1-rebuilt"
    assert receipt["source_checkout"] == _git(root, "rev-parse", "HEAD").strip()


def test_unrelated_checkout_change_with_identical_outputs_witness_accepts(tmp_path: Path) -> None:
    """An upstream commit that touched nothing material is not a new generation."""
    root = _proof_tree(tmp_path)
    assert _prove(root, tmp_path).returncode == 0
    (root / "README.md").write_text("unrelated desk change\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "unrelated")
    result = _run_gate(root, "verify", "--root", ".", "--suite",
                       "tests/test_proof_gate_suite.py", "--receipt", str(_receipt_path(tmp_path)))
    assert result.returncode == 0, result.stdout + result.stderr
    assert "covers this generation exactly" in result.stdout


def test_material_source_change_alone_requires_reproof(tmp_path: Path) -> None:
    """A moving dependency refuses even when output bytes happen to match."""
    root = _proof_tree(tmp_path)
    assert _prove(root, tmp_path).returncode == 0
    (root / "data/government_revenue/latest.json").write_text(
        json.dumps({"generated_at": "2026-10-12T02:00:00+00:00"}), encoding="utf-8"
    )
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "newer canonical generation")
    result = _run_gate(root, "verify", "--root", ".", "--suite",
                       "tests/test_proof_gate_suite.py", "--receipt", str(_receipt_path(tmp_path)))
    assert result.returncode == EXIT_WITNESS_MISMATCH
    assert "output drift" in result.stdout


# ── workflow wiring ────────────────────────────────────────────────────────


def test_patched_workflow_gates_publication_through_the_proof_helper() -> None:
    """The lane calls the helper, dropped the fail-open branch, uploads on failure."""
    text = (ROOT / ".github/workflows/government-revenue-live.yml").read_text(encoding="utf-8")
    assert "scripts/ci/govrev_candidate_proof.py prove" in text
    assert "scripts/ci/govrev_candidate_proof.py verify" in text
    # The fail-open escape is gone.
    assert "publishing UNPROVEN" not in text
    # Bounded failure diagnostics via the standard artifact owner, always on.
    assert "govrev-candidate-proof-diagnostics" in text
    assert "if: ${{ always() }}" in text
    assert "retention-days: 7" in text


@pytest.mark.parametrize("path", ["data/government_revenue/sbir_progression.json",
    "data/government_revenue/defense_economics.json", "site/government-revenue-data/sbir-progression.json",
    "site/government-revenue-data/defense-economics.json", "site/government_revenue.html",
    "site/theme.js"])
def test_complete_generation_covers_new_derived_bytes(tmp_path, path):
    root = _proof_tree(tmp_path)
    (root / path).parent.mkdir(parents=True, exist_ok=True)
    (root / path).write_text("first")
    assert _prove(root, tmp_path).returncode == 0
    before = _porcelain(root)
    (root / path).write_text("second")
    assert _porcelain(root) == before  # dirty-to-dirty state stayed identical
    result = _run_gate(root, "verify", "--suite", "tests/test_proof_gate_suite.py", "--receipt", str(_receipt_path(tmp_path)))
    assert result.returncode == EXIT_WITNESS_MISMATCH


@pytest.mark.parametrize("target", [
    "site/government-revenue-data/candidates.json", "app/govrev.py",
    "templates/govrev.html", "tests/test_proof_gate_suite.py",
    "site/theme.js",
    "tests/fixtures/government_revenue/issuance_incident_5fc18d5/candidate_queue.json",
    "tests/defense_o2_source_contracts/fixtures/noc_siaw_theme_fact.json",
    "tests/test_government_revenue_priority.cjs",
])
def test_source_and_public_mutations_during_prove_refuse(tmp_path, target):
    body = "from pathlib import Path\ndef test_hostile():\n    p=Path(" + repr(target) + ")\n    p.parent.mkdir(parents=True, exist_ok=True)\n    p.write_text('hostile')\n"
    root = _proof_tree(tmp_path, suite_body=body)
    result = _prove(root, tmp_path)
    assert result.returncode == EXIT_TREE_MUTATED, result.stdout + result.stderr
    assert not _receipt_path(tmp_path).exists()


@pytest.mark.parametrize("filter_source", ["environment", "configuration"])
def test_inherited_deselection_cannot_hide_a_real_failure(tmp_path, filter_source):
    root = _proof_tree(tmp_path, suite_body=SUITE_OK + SUITE_FAIL)
    extra = {"PYTEST_ADDOPTS": "-k proof_green"} if filter_source == "environment" else {}
    if filter_source == "configuration":
        (root / "pytest.ini").write_text("[pytest]\naddopts = -k proof_green\n")
    result = _prove(root, tmp_path, env_extra=extra)
    assert result.returncode == EXIT_PROOF_FAILED, result.stdout + result.stderr
    assert not _receipt_path(tmp_path).exists()


def test_current_runtime_binding_refuses_reuse_after_plugin_policy_drift(tmp_path):
    root = _proof_tree(tmp_path)
    assert _prove(root, tmp_path).returncode == 0
    result = _run_gate(root, "verify", "--suite", "tests/test_proof_gate_suite.py", "--receipt", str(_receipt_path(tmp_path)), env_extra={"PYTEST_DISABLE_PLUGIN_AUTOLOAD":"1"})
    assert result.returncode == EXIT_WITNESS_MISMATCH


def _helper_module():
    import importlib.util
    spec = importlib.util.spec_from_file_location("proof_gate_under_test", HELPER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_long_real_pytest_summary_is_complete():
    assert _helper_module().parse_pytest_summary("101 passed, 1 skipped, 1 warning in 494.05s (0:08:14)") == ("101 passed, 1 skipped, 1 warning in 494.05s (0:08:14)", 101)


@pytest.mark.parametrize("junit", [
    '<testsuites><testsuite tests="1" failures="0" errors="0"><testcase classname="tests.test_proof_gate_suite" name="test_a"/></testsuite></testsuites>',
    '<testsuites><testsuite tests="99" failures="0" errors="0"><testcase classname="tests.test_proof_gate_suite" name="test_a"/><testcase classname="tests.test_proof_gate_suite" name="test_b"/></testsuite></testsuites>',
    '<testsuites><testsuite tests="2" failures="0" errors="0"><testcase classname="tests.test_proof_gate_suite" name="test_a"/><testcase classname="tests.test_proof_gate_suite" name="test_a"/></testsuite></testsuites>',
])
def test_partial_duplicate_or_inconsistent_execution_evidence_refuses(tmp_path, junit):
    report = tmp_path / "junit.xml"
    report.write_text(junit)
    with pytest.raises(ValueError):
        _helper_module()._complete_execution(["tests/test_proof_gate_suite.py::test_a", "tests/test_proof_gate_suite.py::test_b"], report)


def test_reuse_after_own_output_commit_keeps_exact_receipt(tmp_path):
    root = _proof_tree(tmp_path)
    queue = root / "data/government_revenue/candidate_queue.json"
    queue.write_text(queue.read_text() + "\n")
    assert _prove(root, tmp_path).returncode == 0
    before = _receipt_path(tmp_path).read_bytes()
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "publish exact proved output")
    result = _prove(root, tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "prior proof stands" in result.stdout
    assert _receipt_path(tmp_path).read_bytes() == before


def test_prover_bytes_drift_refuses_witness(tmp_path, monkeypatch):
    root = _proof_tree(tmp_path)
    copied = tmp_path / "helper.py"
    copied.write_bytes(HELPER.read_bytes())
    monkeypatch.setattr(sys.modules[__name__], "HELPER", copied)
    assert _prove(root, tmp_path).returncode == 0
    copied.write_text(copied.read_text() + "\n# changed prover\n")
    result = _run_gate(root, "verify", "--suite", "tests/test_proof_gate_suite.py", "--receipt", str(_receipt_path(tmp_path)))
    assert result.returncode == EXIT_WITNESS_MISMATCH


def test_failed_reproof_retains_prior_certificate_and_refuses(tmp_path):
    root = _proof_tree(tmp_path)
    assert _prove(root, tmp_path).returncode == 0
    original = _receipt_path(tmp_path).read_bytes()
    (root / "tests/test_proof_gate_suite.py").write_text(SUITE_FAIL)
    assert _prove(root, tmp_path).returncode == EXIT_PROOF_FAILED
    assert not _receipt_path(tmp_path).exists()
    archives = list(_receipt_path(tmp_path).parent.glob("receipt.json.previous-*"))
    assert len(archives) == 1 and archives[0].read_bytes() == original


def test_certificate_archive_preserves_exact_bytes_even_above_log_limit(tmp_path):
    receipt, log = tmp_path / "receipt.json", tmp_path / "proof.log"
    payload = b"x" * (1048576 + 1024)
    receipt.write_bytes(payload)
    log.write_bytes(payload)
    _helper_module()._retain_previous_evidence(receipt, log)
    assert next(tmp_path.glob("receipt.json.previous-*")).read_bytes() == payload
    assert len(next(tmp_path.glob("proof.log.previous-*")).read_bytes()) == 1048576


def test_plugin_deselection_is_an_incomplete_named_suite(tmp_path):
    root = _proof_tree(tmp_path, suite_body=SUITE_OK + SUITE_FAIL)
    (root / "conftest.py").write_text(
        "def pytest_collection_modifyitems(config, items):\n"
        "    omitted = [item for item in items if 'boom' in item.name]\n"
        "    config.hook.pytest_deselected(items=omitted)\n"
        "    items[:] = [item for item in items if item not in omitted]\n")
    result = _prove(root, tmp_path)
    assert result.returncode == EXIT_INCOMPLETE_PROOF, result.stdout + result.stderr
    assert "deselected cases" in result.stdout
    assert not _receipt_path(tmp_path).exists()


@pytest.mark.parametrize("kind", ["log", "collection", "junit"])
def test_sealed_execution_artifact_loss_or_drift_refuses_witness(tmp_path, kind):
    root = _proof_tree(tmp_path)
    assert _prove(root, tmp_path).returncode == 0
    receipt = json.loads(_receipt_path(tmp_path).read_text())
    item = receipt["execution_evidence"]["artifacts"][kind]
    sealed = _receipt_path(tmp_path).parent / item["filename"]
    sealed.write_bytes(b"tampered")
    result = _run_gate(root, "verify", "--suite", "tests/test_proof_gate_suite.py", "--receipt", str(_receipt_path(tmp_path)))
    assert result.returncode == EXIT_RECEIPT_INVALID
    assert "missing or altered" in result.stdout


def test_committed_witness_refuses_uncommitted_generation_then_binds_exact_commit(tmp_path):
    root = _proof_tree(tmp_path)
    queue = root / "data/government_revenue/candidate_queue.json"
    queue.write_text(queue.read_text() + "\n")
    assert _prove(root, tmp_path).returncode == 0
    common = ("--suite", "tests/test_proof_gate_suite.py", "--receipt", str(_receipt_path(tmp_path)))
    assert _run_gate(root, "verify", "--committed", *common).returncode == EXIT_WITNESS_MISMATCH
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "publish exact sealed bytes")
    commit = _git(root, "rev-parse", "HEAD").strip()
    out = tmp_path / "publication.json"
    result = _run_gate(root, "publication-witness", *common, "--commit", commit, "--push-status", "successful", "--out", str(out))
    assert result.returncode == 0, result.stdout + result.stderr
    witness = json.loads(out.read_text())
    receipt = json.loads(_receipt_path(tmp_path).read_text())
    assert witness["proof_identity"] == receipt["identity"]
    assert witness["committed_generation"]["commit"] == commit
    assert witness["committed_generation"]["artifacts"]["data/government_revenue/candidate_queue.json"]["sha256"] == receipt["outputs"]["data/government_revenue/candidate_queue.json"]
    assert witness["issuance_authority"] is False
    assert witness["observed_at"] != receipt["generation"]["projection_generated_at"]


def test_committed_witness_refuses_unstaged_new_derived_output(tmp_path):
    root = _proof_tree(tmp_path)
    (root / "data/government_revenue/sbir_progression.json").write_text("{}")
    assert _prove(root, tmp_path).returncode == 0
    result = _run_gate(root, "verify", "--committed", "--suite", "tests/test_proof_gate_suite.py", "--receipt", str(_receipt_path(tmp_path)))
    assert result.returncode == EXIT_WITNESS_MISMATCH
    assert "generated bytes were not committed" in result.stdout


@pytest.mark.parametrize("path", ["site/government-revenue-investor.js", "site/government-revenue-sbir.css"])
def test_published_static_asset_bytes_require_reproof(tmp_path, path):
    root = _proof_tree(tmp_path)
    (root / path).write_text("sealed")
    assert _prove(root, tmp_path).returncode == 0
    (root / path).write_text("drifted")
    result = _run_gate(root, "verify", "--suite", "tests/test_proof_gate_suite.py", "--receipt", str(_receipt_path(tmp_path)))
    assert result.returncode == EXIT_WITNESS_MISMATCH


def test_new_committed_static_asset_cannot_bypass_existing_receipt(tmp_path):
    root = _proof_tree(tmp_path)
    assert _prove(root, tmp_path).returncode == 0
    (root / "site/government-revenue-investor.js").write_text("added")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "new copied static asset")
    result = _run_gate(root, "verify", "--committed", "--suite", "tests/test_proof_gate_suite.py", "--receipt", str(_receipt_path(tmp_path)))
    assert result.returncode == EXIT_WITNESS_MISMATCH


def test_economics_company_profile_source_drift_requires_reproof(tmp_path):
    root = _proof_tree(tmp_path)
    directory = root / "engine/company_intelligence"
    directory.mkdir(parents=True)
    path = directory / "defense_profiles.py"
    path.write_text("PROFILES = {}\n")
    assert _prove(root, tmp_path).returncode == 0
    path.write_text("PROFILES = {'new': True}\n")
    result = _run_gate(root, "verify", "--suite", "tests/test_proof_gate_suite.py", "--receipt", str(_receipt_path(tmp_path)))
    assert result.returncode == EXIT_WITNESS_MISMATCH


def test_earnings_receipt_binding_source_drift_requires_reproof(tmp_path):
    root = _proof_tree(tmp_path)
    directory = root / "engine/earnings_release"
    directory.mkdir(parents=True)
    path = directory / "receipts.py"
    path.write_text("RECEIPT_SCHEMA = 'original'\n")
    assert _prove(root, tmp_path).returncode == 0
    path.write_text("RECEIPT_SCHEMA = 'hostile-drift'\n")
    result = _run_gate(root, "verify", "--suite", "tests/test_proof_gate_suite.py", "--receipt", str(_receipt_path(tmp_path)))
    assert result.returncode == EXIT_WITNESS_MISMATCH
    assert "source drift" in result.stdout


def test_research_preregistration_source_drift_requires_reproof(tmp_path):
    root = _proof_tree(tmp_path)
    directory = root / "research"
    directory.mkdir()
    path = directory / "GOVERNMENT_REVENUE_CANDIDATE_GRADER_PREREG.md"
    path.write_text("registered incumbent family terms\n")
    assert _prove(root, tmp_path).returncode == 0
    path.write_text("changed preregistration terms after proof\n")
    result = _run_gate(root, "verify", "--suite", "tests/test_proof_gate_suite.py", "--receipt", str(_receipt_path(tmp_path)))
    assert result.returncode == EXIT_WITNESS_MISMATCH
    assert "source drift" in result.stdout



def _owner_generation(root, *, generation="owner-test", body=b'{"event_id":"current"}'):
    import hashlib
    nest = root / "data/company_intelligence/event_workspaces"
    immutable = nest / "generations" / generation
    (immutable / "workspaces").mkdir(parents=True)
    row = immutable / "workspaces/current.json"
    row.write_bytes(body)
    manifest = {"generation_id": generation, "files": {
        "workspaces/current.json": {"bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()}}}
    raw = json.dumps(manifest, sort_keys=True).encode()
    (immutable / "manifest.json").write_bytes(raw)
    (nest / "manifest.json").write_bytes(raw)
    return nest, immutable


def test_current_owner_generation_bound_and_history_not_scanned(tmp_path):
    root = _proof_tree(tmp_path)
    nest, immutable = _owner_generation(root)
    historical = nest / "generations/history/workspaces/old.json"
    historical.parent.mkdir(parents=True)
    historical.write_text("irrelevant old owner generation")
    assert _prove(root, tmp_path).returncode == 0
    receipt = json.loads(_receipt_path(tmp_path).read_text())
    source = receipt["source_dependencies"]
    assert "data/company_intelligence/event_workspaces/manifest.json" in source
    assert "data/company_intelligence/event_workspaces/generations/owner-test/manifest.json" in source
    assert "data/company_intelligence/event_workspaces/generations/owner-test/workspaces/current.json" in source
    assert not any("/history/" in path for path in source)
    historical.write_text("changed unrelated history")
    result = _run_gate(root, "verify", "--suite", "tests/test_proof_gate_suite.py", "--receipt", str(_receipt_path(tmp_path)))
    assert result.returncode == 0, result.stdout + result.stderr


def test_current_owner_row_drift_refuses_witness(tmp_path):
    root = _proof_tree(tmp_path)
    _, immutable = _owner_generation(root)
    assert _prove(root, tmp_path).returncode == 0
    (immutable / "workspaces/current.json").write_text("tampered owner row")
    result = _run_gate(root, "verify", "--suite", "tests/test_proof_gate_suite.py", "--receipt", str(_receipt_path(tmp_path)))
    assert result.returncode == EXIT_WITNESS_MISMATCH
    assert "owner workspace receipt mismatch" in result.stdout


def test_owner_current_marker_repoint_requires_reproof(tmp_path):
    root = _proof_tree(tmp_path)
    _owner_generation(root)
    assert _prove(root, tmp_path).returncode == 0
    _owner_generation(root, generation="owner-new", body=b'{"event_id":"new"}')
    result = _run_gate(root, "verify", "--suite", "tests/test_proof_gate_suite.py", "--receipt", str(_receipt_path(tmp_path)))
    assert result.returncode == EXIT_WITNESS_MISMATCH
    assert "source drift" in result.stdout


@pytest.mark.parametrize("failure", ["immutable_manifest", "missing_row", "receipt_hash", "unsafe_path"])
def test_incomplete_or_invalid_owner_generation_refuses_proof(tmp_path, failure):
    root = _proof_tree(tmp_path)
    nest, immutable = _owner_generation(root)
    if failure == "immutable_manifest":
        (immutable / "manifest.json").write_text("{}");
    elif failure == "missing_row":
        (immutable / "workspaces/current.json").unlink()
    else:
        manifest = json.loads((nest / "manifest.json").read_text())
        if failure == "receipt_hash":
            manifest["files"]["workspaces/current.json"]["sha256"] = "0" * 64
        else:
            manifest["files"]["../escape.json"] = manifest["files"].pop("workspaces/current.json")
        raw = json.dumps(manifest).encode()
        (nest / "manifest.json").write_bytes(raw)
        (immutable / "manifest.json").write_bytes(raw)
    result = _prove(root, tmp_path)
    assert result.returncode == EXIT_RECEIPT_INVALID, result.stdout + result.stderr
    assert not _receipt_path(tmp_path).exists()


def test_absent_owner_marker_is_bound_explicitly(tmp_path):
    root = _proof_tree(tmp_path)
    assert _prove(root, tmp_path).returncode == 0
    receipt = json.loads(_receipt_path(tmp_path).read_text())
    assert receipt["source_dependencies"]["data/company_intelligence/event_workspaces/manifest.json"] == "absent"


def test_owner_input_mutation_during_prover_refuses_even_with_valid_receipts(tmp_path):
    body = '''from pathlib import Path
import json, hashlib

def test_mutates_owner_inputs():
    nest = Path("data/company_intelligence/event_workspaces")
    manifest = json.loads((nest / "manifest.json").read_text())
    immutable = nest / "generations" / manifest["generation_id"]
    row = immutable / "workspaces/current.json"
    raw = b'{"event_id":"changed-during-proof"}'
    row.write_bytes(raw)
    manifest["files"]["workspaces/current.json"] = {"bytes":len(raw), "sha256":hashlib.sha256(raw).hexdigest()}
    encoded = json.dumps(manifest, sort_keys=True).encode()
    (nest / "manifest.json").write_bytes(encoded)
    (immutable / "manifest.json").write_bytes(encoded)
'''
    root = _proof_tree(tmp_path, suite_body=body)
    _owner_generation(root)
    result = _prove(root, tmp_path)
    assert result.returncode == EXIT_TREE_MUTATED, result.stdout + result.stderr
    assert not _receipt_path(tmp_path).exists()


def _market_module():
    import importlib.util
    spec = importlib.util.spec_from_file_location("market_bound_proof", HELPER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_participation_owner_dependencies_follow_roster_and_bind_absence(tmp_path):
    module = _market_module()
    root = tmp_path
    marker = root / 'data/baskets/membership.json'
    marker.parent.mkdir(parents=True)
    marker.write_text(json.dumps({'baskets': {'defense': {'members': [{'ticker': 'SYN-A'}, {'ticker': 'SYN-B'}]}}}))
    paths = module._market_input_paths(root)
    from engine.government_revenue.defense_participation_context import participation_input_paths
    assert set(participation_input_paths(root)) <= set(paths)
    inventory = module._hash_files(root, paths)
    assert inventory['data/baskets/ohlcv/SYN-A.parquet'] == 'absent'
    assert inventory['data/yahoo/SPY.parquet'] == 'absent'
    tape = root / 'data/baskets/ohlcv/SYN-A.parquet'
    tape.parent.mkdir(parents=True)
    tape.write_bytes(b'synthetic-owner-bytes')
    assert inventory != module._hash_files(root, paths)
    marker.write_text(json.dumps({'baskets': {'defense': {'members': [{'ticker': '../escape'}]}}}))
    with pytest.raises(ValueError, match='member path'):
        module._market_input_paths(root)


@pytest.mark.parametrize("relative", [
    "data/massive_stock_day/LMT.parquet", "data/massive_stock_day/RTX.parquet",
    "data/massive_stock_day/NOC.parquet", "data/massive_stock_day/LHX.parquet",
    "data/massive_stock_day/.defense_read/manifest.json",
    "data/massive_stock_day/.defense_read/read_receipt.json",
    "data/reference/_receipt.json", "data/reference/security_master.parquet",
    "data/reference/vendor_aliases.parquet", "data/reference/issuer_master.parquet",
    "config/dataset_registry.yml", "research/licenses/MASSIVE_ENTITLEMENT_RECORD.md",
    "engine/stock_technicals.py",
])
def test_market_exact_input_absence_and_dirty_to_dirty_drift_are_bound(tmp_path, relative):
    module = _market_module()
    first = module._hash_files(tmp_path, module._source_dependency_paths(tmp_path))
    assert first[relative] == "absent"
    path = tmp_path / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"first dirty input")
    first = module._hash_files(tmp_path, module._source_dependency_paths(tmp_path))
    path.write_bytes(b"second dirty input")
    second = module._hash_files(tmp_path, module._source_dependency_paths(tmp_path))
    assert first[relative] != second[relative]
    history = tmp_path / "data/massive_stock_day/history/not-consumed.parquet"
    history.parent.mkdir(parents=True, exist_ok=True)
    history.write_bytes(b"unconsumed")
    assert history.relative_to(tmp_path).as_posix() not in module._source_dependency_paths(tmp_path)


@pytest.mark.parametrize("parent_link", [False, True])
def test_market_exact_input_symlink_is_refused(tmp_path, parent_link):
    module = _market_module()
    target = tmp_path / "other"
    target.mkdir()
    nest = tmp_path / "data/massive_stock_day"
    nest.parent.mkdir()
    if parent_link:
        nest.symlink_to(target, target_is_directory=True)
    else:
        nest.mkdir()
        (target / "body").write_bytes(b"raw")
        (nest / "LMT.parquet").symlink_to(target / "body")
    with pytest.raises(ValueError, match="symlink refused"):
        module._source_dependency_paths(tmp_path)


def test_market_receipt_drift_refuses_exact_generation_witness(tmp_path):
    root = _proof_tree(tmp_path)
    path = root / "data/massive_stock_day/.defense_read/read_receipt.json"
    path.parent.mkdir(parents=True)
    path.write_text('{"snapshot":"first"}')
    assert _prove(root, tmp_path).returncode == 0
    path.write_text('{"snapshot":"changed"}')
    result = _run_gate(root, "verify", "--root", ".", "--suite", "tests/test_proof_gate_suite.py", "--receipt", str(_receipt_path(tmp_path)))
    assert result.returncode != 0, result.stdout


def test_market_mutation_during_proof_is_refused(tmp_path):
    root = _proof_tree(tmp_path, suite_body="def test_market_mutation():\n    from pathlib import Path\n    Path('data/massive_stock_day/LMT.parquet').write_bytes(b'changed')\n")
    path = root / "data/massive_stock_day/LMT.parquet"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"original")
    result = _prove(root, tmp_path)
    assert result.returncode != 0, result.stdout
    assert not _receipt_path(tmp_path).exists()
