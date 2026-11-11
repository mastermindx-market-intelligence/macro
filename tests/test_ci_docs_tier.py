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


def _repository(path: Path, *, manifest: str | None = MINIMAL_MANIFEST) -> Path:
    """A repo whose base commit carries a manifest; returns it ready to branch."""
    path.mkdir()
    _git(path, "init", "-b", "main")
    _git(path, "config", "user.email", "ci@example.test")
    _git(path, "config", "user.name", "CI Test")
    if manifest is not None:
        (path / ".github" / "ci").mkdir(parents=True)
        (path / ".github" / "ci" / "legacy-jobs.yml").write_text(manifest, encoding="utf-8")
    (path / "README.md").write_text("# repo\n", encoding="utf-8")
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
