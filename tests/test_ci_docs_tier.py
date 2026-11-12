"""The docs fast lane's trusted-base classifier: every doubt refuses the tier.

WHY THIS SUITE EXISTS.  `build_plan` lets an affirmative verdict from
`scripts/ci_docs_tier.py` select ZERO legacy jobs for a pull request — that is
authority over CI execution, so the classifier must be impossible to satisfy
from anything but a pure, additive, narrative-markdown diff of the exact
(base, merge) pair the planner itself resolved.  The suite executes the REAL
classifier (the same file ci.yml's `ci-plan` job copies from the default
branch) against throwaway git repositories, because the failure that matters
is not "the function returns False" but "git produced a surprising status
stream and the parser survived it".

The fail-closed law under test: the ONLY path to `docs_tier: true` is
add/modify of `.md` under `docs/`, `research/` or `agentos/`, none of them a
consumed registry document or a manifest-declared literal, in a repo whose
base manifest parses.  Everything else — deletions, renames, copies,
typechanges, unresolved rows, paths outside the roots, non-markdown paths,
curated consumers, manifest literals, unreadable manifests, missing yaml,
bad SHAs, git failures — publishes a NEGATIVE verdict with exit 0, and the
planner then runs the incumbent scoped selection unchanged
(tests/test_ci_pack_docs_tier.py pins that half).

Run: python3 -m pytest tests/test_ci_docs_tier.py -q
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

SPEC = importlib.util.spec_from_file_location(
    "ci_docs_tier", ROOT / "scripts" / "ci_docs_tier.py"
)
assert SPEC and SPEC.loader
TIER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = TIER
SPEC.loader.exec_module(TIER)

# The planner side of the same handshake must not drift from the classifier.
PLANNER_SCHEMA = "ci.docs_tier.v1"

MINIMAL_MANIFEST = """\
jobs:
  always:
    if: never_true
    runs-on: ubuntu-latest
    steps:
      - run: echo hello
"""


def _git(path: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(path), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _commit_all(path: Path, message: str) -> str:
    _git(path, "add", "-A")
    _git(path, "commit", "-m", message)
    return _git(path, "rev-parse", "HEAD")


def _repository(
    path: Path,
    *,
    manifest: str | None = MINIMAL_MANIFEST,
    code: dict[str, str] | None = None,
) -> Path:
    """A repo whose base commit carries a manifest; returns it ready to branch."""
    path.mkdir()
    _git(path, "init", "-b", "main")
    _git(path, "config", "user.email", "ci@example.test")
    _git(path, "config", "user.name", "CI Test")
    if manifest is not None:
        (path / ".github" / "ci").mkdir(parents=True)
        (path / ".github" / "ci" / "legacy-jobs.yml").write_text(manifest, encoding="utf-8")
    (path / "README.md").write_text("# repo\n", encoding="utf-8")
    # The code-derived consumer scan refuses a base with no Python at all.
    (path / "tools").mkdir()
    (path / "tools" / "noop.py").write_text("VALUE = 1\n", encoding="utf-8")
    for rel, source in (code or {}).items():
        _write(path, rel, source)
    _commit_all(path, "base")
    return path


def _write(path: Path, rel: str, content: str = "note\n") -> None:
    target = path / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def _verdict(path: Path, base: str, merge: str) -> dict[str, object]:
    return TIER.classify_workspace(path, base=base, merge=merge)


def _base_of(path: Path) -> str:
    return _git(path, "rev-parse", "HEAD")


# ─── the affirmative tier ──────────────────────────────────────────────────────


def test_pure_additive_markdown_under_all_three_roots_attests_the_tier(
    tmp_path: Path,
) -> None:
    repo = _repository(tmp_path / "repo")
    base = _base_of(repo)
    _write(repo, "docs/NOTE.md")
    _write(repo, "research/plan_2026/ROOM.md")
    _write(repo, "agentos/decisions/DEC-X.md", "decision\n")
    (repo / "README.md").write_text("# repo edited\n", encoding="utf-8")  # M, but outside roots
    merge = _commit_all(repo, "narrative + readme")
    verdict = _verdict(repo, base, merge)
    assert verdict["docs_tier"] is False, "README.md at the root must refuse the tier"
    assert "README.md is not narrative markdown" in str(verdict["reason"])

    repo2 = _repository(tmp_path / "repo2")
    base2 = _base_of(repo2)
    _write(repo2, "docs/NOTE.md")
    _write(repo2, "research/plan_2026/ROOM.md")
    _write(repo2, "agentos/decisions/DEC-X.md", "decision\n")
    merge2 = _commit_all(repo2, "narrative only")
    verdict2 = _verdict(repo2, base2, merge2)
    assert verdict2["schema"] == TIER.SCHEMA
    assert verdict2["docs_tier"] is True, verdict2["reason"]
    assert verdict2["base_sha"] == base2
    assert verdict2["merge_sha"] == merge2
    assert verdict2["paths_count"] == 3
    assert verdict2["paths_sha256"] == TIER.changed_paths_digest(
        ["agentos/decisions/DEC-X.md", "docs/NOTE.md", "research/plan_2026/ROOM.md"]
    )
    assert isinstance(verdict2["example_path"], str)


def test_verdict_digest_is_the_planner_twin_and_order_sensitive() -> None:
    from scripts.run_ci_pack import changed_files_digest

    ordered = ["docs/A.md", "docs/B.md"]
    assert TIER.changed_paths_digest(ordered) == changed_files_digest(ordered)
    assert TIER.SCHEMA == PLANNER_SCHEMA
    assert TIER.changed_paths_digest(ordered) != TIER.changed_paths_digest(
        list(reversed(ordered))
    )


# ─── status letters that must refuse ──────────────────────────────────────────


@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        pytest.param(lambda repo: (repo / "docs/A.md").unlink(), False, id="delete"),
        pytest.param(
            lambda repo: _git(repo, "mv", "docs/A.md", "docs/RENAMED.md"),
            False,
            id="rename",
        ),
        pytest.param(
            lambda repo: _write(repo, "docs/EXTRA.md") or None,
            True,
            id="pure-add-still-eligible",
        ),
    ],
)
def test_moving_deleting_or_adding_narrative_paths(
    tmp_path: Path, mutate, expected: bool
) -> None:
    """Delete/rename refuse the tier (both-sides expansion never gets a chance
    to launder a moved path); a pure add on top of prior narrative stays in it."""
    repo = _repository(tmp_path / "repo")
    _write(repo, "docs/A.md")
    _write(repo, "docs/B.md")
    _commit_all(repo, "seed narrative")
    base = _base_of(repo)
    mutate(repo)
    merge = _commit_all(repo, "mutate")
    verdict = _verdict(repo, base, merge)
    assert verdict["docs_tier"] is expected
    if not expected:
        assert "not add/modify" in str(verdict["reason"])


def test_status_letters_are_refused_purely_before_any_expansion() -> None:
    """D, R100, C100, T, U and the empty inventory never reach digest binding."""
    consumed = set(TIER.CONSUMED_MARKDOWN)
    for status in ("D", "R100", "C100", "T", "U", "A", "M"):
        got, _ = TIER.classify_entries([(status, "docs/NOTE.md")], consumed=consumed)
        assert got is (status in ("A", "M")), status
    got, reason = TIER.classify_entries([], consumed=consumed)
    assert got is False and "empty" in reason


# ─── path shapes that must refuse ──────────────────────────────────────────────


@pytest.mark.parametrize(
    "rel",
    [
        "README.md",  # root markdown is not narrative
        "engine/notes/dev.md",  # markdown outside the three roots
        "docs/evidence.json",  # under a root but not markdown
        "research/note.markdown",  # not .md
    ],
)
def test_non_narrative_paths_refuse_the_tier(tmp_path: Path, rel: str) -> None:
    repo = _repository(tmp_path / "repo")
    base = _base_of(repo)
    _write(repo, rel)
    merge = _commit_all(repo, "touch")
    verdict = _verdict(repo, base, merge)
    assert verdict["docs_tier"] is False
    assert "not narrative markdown" in str(verdict["reason"])


# ─── B2: markdown that first-party code reads refuses the tier ────────────────


RESTORE_READER = """\
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def test_runbook():
    runbook = (ROOT / "docs/RESTORE_RUNBOOK.md").read_text()
    assert "restore" in runbook
"""

CASES_GLOBBER = """\
from pathlib import Path
_REPO_ROOT = Path(__file__).resolve().parents[1]
_CASES = sorted((_REPO_ROOT / "research" / "winners" / "cases").glob("*.md"))
"""

RGLOB_SWEEP = """\
from pathlib import Path

def run_sweep(root: Path):
    research_dir = root / "research"
    return sorted(research_dir.rglob("*.md"))
"""


def test_a_literally_read_runbook_edit_refuses_the_tier(tmp_path: Path) -> None:
    repo = _repository(
        tmp_path / "repo", code={"tests/test_backup_user_tables.py": RESTORE_READER}
    )
    _write(repo, "docs/RESTORE_RUNBOOK.md", "# restore\n")
    _commit_all(repo, "seed runbook")
    base = _base_of(repo)
    _write(repo, "docs/RESTORE_RUNBOOK.md", "# restore, edited\n")
    merge = _commit_all(repo, "edit runbook")
    verdict = _verdict(repo, base, merge)
    assert verdict["docs_tier"] is False
    assert "docs/RESTORE_RUNBOOK.md is read by code" in str(verdict["reason"])
    assert "tests/test_backup_user_tables.py" in str(verdict["reason"])


@pytest.mark.parametrize(
    ("code", "rel"),
    [
        pytest.param(
            {"tests/test_winner_autopsy.py": CASES_GLOBBER},
            "research/winners/cases/NEW_2099.md",
            id="glob-dir",
        ),
        pytest.param(
            {"scripts/build_ruling_index.py": RGLOB_SWEEP},
            "research/deep/nested/RULING.md",
            id="rglob-root",
        ),
    ],
)
def test_markdown_under_an_enumerated_directory_refuses_the_tier(
    tmp_path: Path, code: dict[str, str], rel: str
) -> None:
    repo = _repository(tmp_path / "repo", code=code)
    base = _base_of(repo)
    _write(repo, rel, "# new\n")
    merge = _commit_all(repo, "add a case")
    verdict = _verdict(repo, base, merge)
    assert verdict["docs_tier"] is False
    assert "is read by code" in str(verdict["reason"]) and "enumerates" in str(verdict["reason"])


def test_an_unreferenced_docs_markdown_stays_eligible_beside_readers(tmp_path: Path) -> None:
    repo = _repository(
        tmp_path / "repo",
        code={
            "tests/test_backup_user_tables.py": RESTORE_READER,
            "tests/test_winner_autopsy.py": CASES_GLOBBER,
        },
    )
    base = _base_of(repo)
    _write(repo, "docs/ZZ_UNREFERENCED_NOTE_2099.md", "# nobody reads me\n")
    merge = _commit_all(repo, "narrative")
    verdict = _verdict(repo, base, merge)
    assert verdict["docs_tier"] is True, verdict["reason"]


def test_consumers_come_from_the_base_tree_not_the_candidate(tmp_path: Path) -> None:
    """A reader the candidate deletes still protects its file (base wins)."""
    repo = _repository(
        tmp_path / "repo", code={"tests/test_backup_user_tables.py": RESTORE_READER}
    )
    base = _base_of(repo)
    (repo / "tests/test_backup_user_tables.py").unlink()
    _write(repo, "docs/RESTORE_RUNBOOK.md")
    merge = _commit_all(repo, "drop reader + edit")
    # The delete itself refuses first; the pure scan still names the reader.
    assert _verdict(repo, base, merge)["docs_tier"] is False
    derived = TIER.derive_consumed_markdown(repo, base)
    assert derived.claims("docs/RESTORE_RUNBOOK.md") is not None


def test_an_unparseable_base_module_fails_the_scan_closed(tmp_path: Path) -> None:
    repo = _repository(
        tmp_path / "repo", code={"scripts/broken.py": 'DOCS = "docs/"\ndef (:\n'}
    )
    base = _base_of(repo)
    _write(repo, "docs/ZZ_UNREFERENCED_NOTE_2099.md")
    merge = _commit_all(repo, "narrative")
    verdict = _verdict(repo, base, merge)
    assert verdict["docs_tier"] is False
    assert str(verdict["reason"]).startswith("classifier-error: consumer scan failed")


def test_any_scan_exception_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _repository(tmp_path / "repo")
    base = _base_of(repo)
    _write(repo, "docs/ZZ_UNREFERENCED_NOTE_2099.md")
    merge = _commit_all(repo, "narrative")

    def boom(*_args, **_kwargs):
        raise OSError("simulated git failure")

    monkeypatch.setattr(TIER, "derive_consumed_markdown", boom)
    verdict = _verdict(repo, base, merge)
    assert verdict["docs_tier"] is False
    assert "consumer scan failed" in str(verdict["reason"])


def test_hung_base_blob_read_times_out_and_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A lazy blob:none fetch that stalls must refuse the tier, not hang ci-plan."""
    repo = _repository(tmp_path / "repo")
    base = _base_of(repo)
    _write(repo, "docs/ZZ_UNREFERENCED_NOTE_2099.md")
    merge = _commit_all(repo, "narrative")
    real_run = TIER.subprocess.run
    seen: list[object] = []

    def stalled(argv, *args, **kwargs):
        if "--batch" in argv:
            seen.append(kwargs.get("timeout"))
            raise subprocess.TimeoutExpired(argv, kwargs.get("timeout") or 0)
        return real_run(argv, *args, **kwargs)

    monkeypatch.setattr(TIER.subprocess, "run", stalled)
    verdict = _verdict(repo, base, merge)
    assert seen == [TIER.GIT_TIMEOUT_SECONDS]
    assert verdict["docs_tier"] is False
    assert "consumer scan failed" in str(verdict["reason"])


def test_every_git_call_in_the_classifier_is_bounded() -> None:
    source = Path(TIER.__file__).read_text(encoding="utf-8")
    assert 0 < TIER.GIT_TIMEOUT_SECONDS <= 900
    runs = source.count("subprocess.run(")
    assert runs == source.count("timeout=GIT_TIMEOUT_SECONDS") + source.count("timeout=300")


@pytest.mark.parametrize(
    ("source", "path", "claimed"),
    [
        ('X = ROOT / "docs" / "A.md"\n', "docs/A.md", True),
        ('X = Path(ROOT, "agentos", "workstreams", "WS-A.md")\n', "agentos/workstreams/WS-A.md", True),
        ('X = os.path.join(R, "research", "B.md")\n', "research/B.md", True),
        ('X = DOCS / "RUNBOOK.md"\n', "docs/ops/RUNBOOK.md", True),  # basename
        ('D = ROOT / "agentos" / "handoffs"\nfor p in D.glob("*.md"): pass\n', "agentos/handoffs/H.md", True),
        ('D = ROOT / "agentos" / "handoffs"\nfor p in D.iterdir(): pass\n', "agentos/handoffs/H.md", True),
        ('import os\nfor r, d, f in os.walk(os.path.join(ROOT, "docs", "ops")): pass\n', "docs/ops/x.md", True),
        ('import glob\nglob.glob("research/packets/*.md")\n', "research/packets/p.md", True),
        ('D = ROOT / "docs" / "plans"\nX = D / f"{name}.md"\n', "docs/plans/p.md", True),
        ('D = ROOT / "docs" / "evidence"\nfor p in D.glob("*.json"): pass\n', "docs/evidence/e.md", False),
        ('X = ROOT / "engine" / "docs" / "A.md"\n', "docs/OTHER.md", False),
        ('"""Prose naming nothing."""\nX = 1\n', "docs/A.md", False),
    ],
)
def test_scanner_reference_shapes(source: str, path: str, claimed: bool) -> None:
    found = TIER.scan_python_source(source, "scripts/example.py")
    assert (found.claims(path) is not None) is claimed, (source, path)


def test_python_living_under_a_root_claims_its_own_subtree() -> None:
    found = TIER.scan_python_source("X = 1\n", "research/packet_2026/verify.py")
    assert found.claims("research/packet_2026/README_x.md") is not None
    assert found.claims("research/other/README_x.md") is None


def test_non_python_code_literals_are_claimed() -> None:
    found = TIER.scan_other_source("python x.py --doc docs/live_breadth_runbook.md\n")
    assert found.claims("docs/live_breadth_runbook.md") is not None


_GUARD_LITERAL = __import__("re").compile(
    r"(?<![A-Za-z0-9_.\-/])(?:docs|research|agentos)/[A-Za-z0-9_./\-]*?\.md(?![A-Za-z0-9_])"
)


def test_every_narrative_markdown_named_in_first_party_code_is_covered() -> None:
    """GUARD (B2): any tracked narrative .md whose repo path appears literally in
    a first-party ``*.py`` is in the derived consumed set.

    Independent of the scanner's AST resolution: a plain regex over every
    present first-party Python file finds the literal mentions, and each one
    that is a tracked narrative .md must be claimed by scanning that same
    file.  A scanner regression that drops a literal reader reds here.
    """
    listed = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "-z"], capture_output=True, check=True
    ).stdout.decode("utf-8", "replace").split("\0")
    tracked = set(listed)
    narrative = {p for p in tracked if TIER._is_narrative_markdown(p)}
    readers = subprocess.run(
        ["git", "-C", str(ROOT), "grep", "-lzE", r"(docs|research|agentos)/[^ ]*\.md", "--", "*.py"],
        capture_output=True,
    ).stdout.decode("utf-8", "replace").split("\0")
    readers = [r for r in readers if r and (ROOT / r).is_file()]
    assert readers, "the guard found no first-party markdown readers at all"
    uncovered: list[tuple[str, str]] = []
    for rel in readers:
        text = (ROOT / rel).read_text(encoding="utf-8", errors="replace")
        found = TIER.scan_python_source(text, rel)
        for match in _GUARD_LITERAL.findall(text):
            if match in narrative and found.claims(match) is None:
                uncovered.append((rel, match))
    assert not uncovered, f"{len(uncovered)} literal narrative readers escape the scan: {uncovered[:10]}"


def test_the_named_review_cases_are_claimed_by_the_real_tree() -> None:
    """The review's concrete fail-open examples, scanned from this checkout."""
    examples = {
        "tests/test_backup_user_tables.py": "docs/RESTORE_RUNBOOK.md",
        "tests/test_agentos_acceptance_basis.py": "agentos/workstreams/WS-CHAIRMAN-CONTROL-ROOM.md",
        "tests/test_winner_autopsy.py": "research/winners/cases/ZZ_NEW_CASE_2099.md",
        "scripts/build_ruling_index.py": "research/anything/ZZ_NEW_2099.md",
    }
    for reader, path in examples.items():
        source = ROOT / reader
        if not source.is_file():
            pytest.skip(f"{reader} not present in this checkout")
        found = TIER.scan_python_source(source.read_text(encoding="utf-8"), reader)
        assert found.claims(path) is not None, (reader, path)


@pytest.mark.parametrize("rel", sorted(TIER.CONSUMED_MARKDOWN))
def test_curated_consumed_registry_documents_refuse_the_tier(
    tmp_path: Path, rel: str
) -> None:
    repo = _repository(tmp_path / "repo")
    base = _base_of(repo)
    _write(repo, rel, "# registry\n")
    merge = _commit_all(repo, "edit registry doc")
    verdict = _verdict(repo, base, merge)
    assert verdict["docs_tier"] is False
    assert "consumed registry document" in str(verdict["reason"])


def test_manifest_literal_markdown_refuses_only_the_named_file(tmp_path: Path) -> None:
    manifest = """\
jobs:
  reader:
    if: never_true
    runs-on: ubuntu-latest
    paths:
      - research/**/*.md
      - research/DO_NOT_REBUILD.md
    steps:
      - run: echo reads one literal md
"""
    repo = _repository(tmp_path / "repo", manifest=manifest)
    base = _base_of(repo)
    _write(repo, "research/DO_NOT_REBUILD.md", "# read by a suite\n")
    merge_named = _commit_all(repo, "edit the literal")
    verdict = _verdict(repo, base, merge_named)
    assert verdict["docs_tier"] is False
    assert "consumed registry document" in str(verdict["reason"])

    # A fresh base→merge range touching ONLY wildcard-covered markdown stays in
    # the tier: the hand-written literal row is the manifest's one signal that a
    # suite reads that exact file, and `research/**/*.md` is scope smear.
    twin = _repository(tmp_path / "twin", manifest=manifest)
    twin_base = _base_of(twin)
    _write(twin, "research/FREE.md", "# smeared wildcard only\n")
    twin_merge = _commit_all(twin, "edit a wildcard-only path")
    assert _verdict(twin, twin_base, twin_merge)["docs_tier"] is True


def test_manifest_wildcards_and_non_markdown_rows_are_not_consumed() -> None:
    literal = TIER.manifest_literal_markdown(
        {
            "jobs": {
                "a": {"paths": ["docs/**/*.md", "docs/LITERAL.md", "noslash.md", "/abs.md", "docs/**/X.md"]},
                "b": {"scope": ["engine/x.py", "docs/glob?char.md", "docs/set[char].md"]},
                "c": {"paths": "not-a-list"},
                "d": "not-a-mapping",
            },
            "other": {"paths": ["docs/OTHER_ROOT.md"]},
        }
    )
    assert literal == {"docs/LITERAL.md"}


# ─── infrastructure doubts publish negative verdicts with exit 0 ──────────────


def test_unreadable_base_manifest_fails_closed(tmp_path: Path) -> None:
    repo = _repository(tmp_path / "repo", manifest="jobs: [unclosed\n")
    base = _base_of(repo)
    _write(repo, "docs/NOTE.md")
    merge = _commit_all(repo, "docs only")
    verdict = _verdict(repo, base, merge)
    assert verdict["docs_tier"] is False
    assert str(verdict["reason"]).startswith("classifier-error: base manifest unreadable")


def test_missing_manifest_fails_closed(tmp_path: Path) -> None:
    repo = _repository(tmp_path / "repo", manifest=None)
    base = _base_of(repo)
    _write(repo, "docs/NOTE.md")
    merge = _commit_all(repo, "docs only")
    verdict = _verdict(repo, base, merge)
    assert verdict["docs_tier"] is False
    assert str(verdict["reason"]).startswith("classifier-error:")


def test_missing_yaml_reader_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repository(tmp_path / "repo")
    base = _base_of(repo)
    _write(repo, "docs/NOTE.md")
    merge = _commit_all(repo, "docs only")
    monkeypatch.setitem(sys.modules, "yaml", None)  # `import yaml` raises ImportError
    verdict = _verdict(repo, base, merge)
    assert verdict["docs_tier"] is False
    assert str(verdict["reason"]).startswith("classifier-error: no yaml reader")


def test_non_sha_or_unknown_revisions_fail_closed_without_git(tmp_path: Path) -> None:
    repo = _repository(tmp_path / "repo")
    base = _base_of(repo)
    _write(repo, "docs/NOTE.md")
    merge = _commit_all(repo, "docs only")
    for bad_base, bad_merge in (
        ("main", merge),  # branch name, not a 40-hex SHA
        (base, "HEAD"),  # symbolic merge ref
        ("0" * 40, merge),  # well-formed but unknown object
        (base, "f" * 40),
    ):
        verdict = _verdict(repo, bad_base, bad_merge)
        assert verdict["docs_tier"] is False, (bad_base, bad_merge)
        assert str(verdict["reason"]).startswith("classifier-error") or "SHA" in str(
            verdict["reason"]
        )
    # A workspace with no git at all is a classifier error, never an exception.
    empty = tmp_path / "empty"
    empty.mkdir()
    verdict = _verdict(empty, base, merge)
    assert verdict["docs_tier"] is False
    assert str(verdict["reason"]).startswith("classifier-error:")


def test_main_writes_the_verdict_and_exits_zero_on_classifier_trouble(
    tmp_path: Path,
) -> None:
    """The workflow step must never see a nonzero exit: fail-closed, not red."""
    out = tmp_path / "verdicts" / "bad.json"
    rc = TIER.main(
        [
            "--workspace",
            str(tmp_path),  # no git repository here
            "--base",
            "0" * 40,
            "--merge",
            "1" * 40,
            "--out",
            str(out),
        ]
    )
    assert rc == 0
    published = json.loads(out.read_text(encoding="utf-8"))
    assert published["schema"] == TIER.SCHEMA
    assert published["docs_tier"] is False
    assert published["reason"].startswith("classifier-error:")
    assert published["paths_count"] == 0 and published["paths_sha256"] == ""


def test_main_writes_an_affirmative_verdict_for_a_real_repository(
    tmp_path: Path,
) -> None:
    repo = _repository(tmp_path / "repo")
    base = _base_of(repo)
    _write(repo, "agentos/handoffs/WS-1.md", "handoff\n")
    merge = _commit_all(repo, "narrative")
    out = tmp_path / "verdicts" / "ok.json"
    rc = TIER.main(
        ["--workspace", str(repo), "--base", base, "--merge", merge, "--out", str(out)]
    )
    assert rc == 0
    published = json.loads(out.read_text(encoding="utf-8"))
    assert published["docs_tier"] is True
    assert published["paths_count"] == 1
    assert published["example_path"] == "agentos/handoffs/WS-1.md"


def test_selftest_proves_the_pure_classification_table() -> None:
    assert TIER.main(["--selftest"]) == 0
