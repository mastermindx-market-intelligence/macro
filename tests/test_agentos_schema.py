"""Agent OS record contract — scripts/agentos.py validate.

Two properties are guarded here, and the second is the one that matters:

1.  The committed `agentos/` store is valid.
2.  The validator can FAIL.  A schema checker that only ever prints "0 errors" is
    indistinguishable from one that never ran, so every hard rule gets a mutation
    that must make it fire.  Each mutation corrupts a COPY in tmp_path; the real
    store is never written to.

Also pinned: the fail-closed / fail-open split (architecture invariant I4) and the
house annotation law — GitHub annotations must START the line, emitted by a bare
print, never through a logger.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
STORE = REPO / "agentos"
CLI = REPO / "scripts" / "agentos.py"

# Agent worktrees here are frequently CONE-MODE SPARSE checkouts, and a directory
# outside the cone is simply absent — which would otherwise read as "the store is
# broken" instead of "the store is not checked out".  CI checks out the full tree,
# so this never skips there; the CI step additionally runs `agentos.py validate`
# directly, which is not skippable, so an absent store cannot pass silently.
# Heal a sparse worktree with:  git sparse-checkout add agentos
SEED_KEYS = (
    sorted(path.stem[3:] for path in (STORE / "workstreams").glob("WS-*.md"))
    if STORE.exists() else []
)

pytestmark = [
    pytest.mark.skipif(
        not STORE.exists(),
        reason="agentos/ outside this sparse checkout — run: git sparse-checkout add agentos",
    ),
    pytest.mark.skipif(
        not SEED_KEYS,
        reason="agentos/workstreams/ holds no records in this checkout — "
               "run: git sparse-checkout add agentos",
    ),
]


def _load_agentos_module():
    spec = importlib.util.spec_from_file_location("agentos_fast_yaml_test", CLI)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _validate(root: Path, **env: str) -> subprocess.CompletedProcess[str]:
    environ = dict(os.environ)
    environ.update(env)
    return subprocess.run(
        [sys.executable, str(CLI), "validate", "--root", str(root)],
        capture_output=True,
        text=True,
        cwd=REPO,
        env=environ,
    )


@pytest.fixture()
def store(tmp_path: Path) -> Path:
    """An isolated copy of the committed store."""
    work = tmp_path / "agentos"
    shutil.copytree(STORE, work)
    return work


def _patch(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert old in text, f"mutation anchor missing in {path.name}: {old!r}"
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def _findings(
    result: subprocess.CompletedProcess[str], rule: str, *, on: str
) -> list[str]:
    """Validator lines for ``rule`` that name ``on`` — a record filename or a cited path.

    Use this for every WARNING-tier assertion.  A bare ``rule in result.stdout`` is a
    substring test over a validate of the WHOLE store, so it answers a question about
    every OTHER record too, and warning-tier rules legitimately fire on the committed
    store: measured on clean main 2026-09-27, 71 `phantom-owns-path`, 20
    `phantom-artifact`, one `active-but-complete`, one `blocked-without-cause`.  The set
    also moves with the ENVIRONMENT — an absent sibling checkout, or a sparse worktree
    whose omitted `data/`/`site/`/`verify_shots/` make every artifact under them read as
    phantom — so the same assertion answers differently in CI and on a dev machine.

    That coupling breaks both ways, and both were live here:

    * the negative form (`not in`) turned one in-flight sibling PR's stale `artifacts:`
      entry into a repo-wide red.  `validate` treats a phantom as a warning and still
      exits 0, so nobody saw it until `self-mod-fence` — an ALWAYS-ON job — ran this
      file (#8060, run 36288860409: `ci-pack-0` -> `ci-gate` failure on this one test).
    * the positive form (`in`) passes on an UNMUTATED store once any unrelated record
      emits the marker, which is why two of the three `state_rules` cases below had no
      power at all by 2026-09-27.

    Error-tier assertions stay unscoped on purpose: `test_committed_store_is_valid` pins
    the store at "0 error(s)", so an error marker can only have come from the mutation.
    """
    return [
        line for line in result.stdout.splitlines()
        if f"[{rule}]" in line and on in line
    ]


# --------------------------------------------------------------- green path


def test_committed_store_is_valid() -> None:
    result = _validate(STORE)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "0 error(s)" in result.stdout


def test_every_record_type_is_present() -> None:
    """A store that silently lost a directory would still validate green."""
    assert list((STORE / "workstreams").glob("WS-*.md"))
    assert list((STORE / "decisions").glob("DEC-*.md"))
    assert list((STORE / "discoveries").glob("DSC-*.md"))


def test_fast_yaml_loader_uses_c_loader_without_slow_fallback(monkeypatch) -> None:
    """Valid records take the C safe-loader path when PyYAML provides it."""
    agentos = _load_agentos_module()
    if agentos._FAST_YAML_LOADER is None:
        pytest.skip("PyYAML C SafeLoader unavailable on this runtime")

    def slow_path_must_not_run(_text):
        raise AssertionError("valid YAML unexpectedly fell back to yaml.safe_load")

    monkeypatch.setattr(agentos.yaml, "safe_load", slow_path_must_not_run)
    assert agentos._yaml_safe_load("alpha: 1\nitems: [x, y]\n") == {
        "alpha": 1,
        "items": ["x", "y"],
    }


def test_fast_yaml_loader_falls_back_when_c_loader_is_unavailable(monkeypatch) -> None:
    """Runtimes without CSafeLoader retain the historical safe_load path."""
    agentos = _load_agentos_module()
    original_text = "alpha: 1\nitems: [x, y]\n"
    sentinel = {"fallback": True}
    observed: list[str] = []

    def historical_safe_load(text):
        observed.append(text)
        return sentinel

    monkeypatch.setattr(agentos, "_FAST_YAML_LOADER", None)
    monkeypatch.setattr(agentos.yaml, "safe_load", historical_safe_load)

    assert agentos._yaml_safe_load(original_text) is sentinel
    assert observed == [original_text]


def test_fast_yaml_loader_preserves_historical_malformed_diagnostic() -> None:
    """C-parser failure must replay through safe_load before surfacing."""
    agentos = _load_agentos_module()
    malformed = "alpha: [one, two\n"
    with pytest.raises(agentos.yaml.YAMLError) as historical:
        agentos.yaml.safe_load(malformed)
    with pytest.raises(agentos.yaml.YAMLError) as accelerated:
        agentos._yaml_safe_load(malformed)
    assert type(accelerated.value) is type(historical.value)
    assert str(accelerated.value) == str(historical.value)


# --------------------------------------------------- mutation proofs (hard)


# (rule, relative path, anchor, replacement)
# Mutate the top-level status prefix; its current valid value becomes a comment.
# Workstreams may legitimately advance from active to done without hiding bad enums.
MUTATIONS: list[tuple[str, str, str, str]] = [
    ("bad-enum", "workstreams/WS-AGENT-OS.md", "\nstatus:", "\nstatus: humming #"),
    (
        "required-field",
        "workstreams/WS-PROPHET-US-ENTRY-TIMING.md",
        "next_action: Verify the 22:30Z bake (W1).",
        "",
    ),
    (
        "unknown-program",
        "workstreams/WS-GMI-THEME-GRAPH.md",
        "program: gmi-theme-graph",
        "program: not-a-real-program",
    ),
    (
        "dangling-ref",
        "workstreams/WS-AGENT-OS.md",
        "  - DEC:AGENTOS-NO-TASK-STORE",
        "  - DEC:DOES-NOT-EXIST",
    ),
    (
        # A bare key is not a citation.  Before the citation shape was enforced,
        # `depends_on: [NONEXISTENT]` validated with 0 errors and 0 warnings — the edge
        # was silently DROPPED from the graph that cycles and START NEXT walk.
        "bad-citation",
        "workstreams/WS-AGENT-OS.md",
        "  - DEC:AGENTOS-NO-TASK-STORE",
        "  - AGENTOS-NO-TASK-STORE",
    ),
    (
        "bad-date",
        "decisions/DEC-AGENTOS-NO-TASK-STORE.md",
        "decided_at: 2026-08-12",
        "decided_at: last Tuesday",
    ),
    (
        "filename-mismatch",
        "workstreams/WS-AGENT-OS.md",
        "key: AGENT-OS",
        "key: AGENT-OS-RENAMED",
    ),
    (
        "no-alternatives",
        "decisions/DEC-AGENTOS-NO-TASK-STORE.md",
        "alternatives:",
        "alternatives: []\nunused_alternatives:",
    ),
    (
        "bad-wave",
        "workstreams/WS-AGENT-OS.md",
        "  - id: W4",
        "  - id: 4",
    ),
    (
        "dangling-wave-dep",
        "workstreams/WS-PROPHET-US-ENTRY-TIMING.md",
        "    depends_on: [W1]",
        "    depends_on: [W99]",
    ),
    (
        "wave-cycle",
        "workstreams/WS-AGENT-OS.md",
        "    depends_on: [W1, W2, W2B]",
        "    depends_on: [W1, W2, W2B]\n"
        "  - id: WX\n    title: cycle a\n    status: todo\n    depends_on: [WY]\n"
        "  - id: WY\n    title: cycle b\n    status: todo\n    depends_on: [WX]",
    ),
    (
        "unparseable",
        "discoveries/DSC-GOVERNANCE-JSONL-NOT-TRACKED.md",
        "kind: architecture",
        "kind: [unclosed",
    ),
]


@pytest.mark.parametrize("rule,rel,anchor,replacement", MUTATIONS, ids=[m[0] for m in MUTATIONS])
def test_hard_rule_fires(store: Path, rule: str, rel: str, anchor: str, replacement: str) -> None:
    """Each hard rule must reject a record that violates it."""
    _patch(store / rel, anchor, replacement)
    result = _validate(store)
    assert result.returncode == 1, f"{rule} did not fail the run:\n{result.stdout}"
    assert rule in result.stdout, f"{rule} not named in output:\n{result.stdout}"


def test_duplicate_key_is_rejected(store: Path) -> None:
    """Only reachable alongside a filename mismatch — kept as defence in depth."""
    source = (store / "decisions" / "DEC-AGENTOS-FILE-PER-RECORD.md").read_text(encoding="utf-8")
    (store / "decisions" / "DEC-COPYCAT.md").write_text(source, encoding="utf-8")
    result = _validate(store)
    assert result.returncode == 1
    assert "duplicate-key" in result.stdout


def test_unreciprocated_supersession_is_rejected(store: Path) -> None:
    """A one-sided supersession silently forks provenance."""
    _patch(
        store / "decisions" / "DEC-AGENTOS-FILE-PER-RECORD.md",
        "decided_at: 2026-08-12",
        "decided_at: 2026-08-12\nsupersedes: [DEC:AGENTOS-NO-TASK-STORE]",
    )
    result = _validate(store)
    assert result.returncode == 1
    assert "unreciprocated-supersession" in result.stdout


# ------------------------------------------------------------ supersession
#
# `superseded_by` is the ONE field in the schema that deletes a live record from every
# compiled context bundle, and it was entirely unvalidated: any truthy string evicted a
# current decision forever while `validate` printed "0 error(s)", and `false`/`0`/`""` —
# the same intent, typed differently — did not evict at all.  A field that removes
# institutional reasoning from the document a cold session reads has to be the most
# checked field here, not the least.


@pytest.mark.parametrize("junk", ["no", "DEC-NEW", "false", "[DEC:A, DEC:B]", "''"])
def test_a_junk_superseded_by_is_rejected(store: Path, junk: str) -> None:
    """Every shape that is not exactly one `DEC:KEY` citation is refused.

    `no` is the expensive one: a plausible thing to type, it used to EVICT the record it
    was written on.  `DEC-NEW` is the bare-key shape `_citations` exists to refuse, and
    two replacements is not a supersession at all — supersession has one successor.
    """
    _patch(
        store / "decisions" / "DEC-AGENTOS-FILE-PER-RECORD.md",
        "decided_at: 2026-08-12",
        f"decided_at: 2026-08-12\nsuperseded_by: {junk}",
    )
    result = _validate(store)
    assert result.returncode == 1, f"superseded_by: {junk} validated clean:\n{result.stdout}"
    assert "bad-supersession" in result.stdout


def test_a_superseded_by_naming_nothing_is_rejected(store: Path) -> None:
    """A record retired in favour of one that does not exist loses its reasoning.

    Well-shaped and still wrong: the citation resolves against nothing, so the bundle would
    drop the old record while pointing at a replacement nobody can open.
    """
    _patch(
        store / "decisions" / "DEC-AGENTOS-FILE-PER-RECORD.md",
        "decided_at: 2026-08-12",
        "decided_at: 2026-08-12\nsuperseded_by: DEC:NO-SUCH-DECISION",
    )
    result = _validate(store)
    assert result.returncode == 1
    assert "dangling-ref" in result.stdout
    assert "superseded_by" in result.stdout


def test_a_one_sided_supersession_warns_but_never_blocks(store: Path) -> None:
    """DELIBERATELY the softer half of the reciprocity rule.

    `superseded_by` on the OLD record is how decision.schema.yml documents supersession —
    "set on the OLD record" — so the new record failing to list `supersedes` is untidy
    provenance, not a broken store.  Hard in this direction would make the schema's own
    worked example fail validation.
    """
    _patch(
        store / "decisions" / "DEC-AGENTOS-FILE-PER-RECORD.md",
        "decided_at: 2026-08-12",
        "decided_at: 2026-08-12\nsuperseded_by: DEC:AGENTOS-NO-TASK-STORE",
    )
    result = _validate(store)
    assert result.returncode == 0, result.stdout
    emitted = _findings(result, "one-sided-supersession", on="DEC-AGENTOS-FILE-PER-RECORD.md")
    assert emitted, (
        "the record carrying `superseded_by` must be the one warned about:\n"
        + result.stdout
    )
    for line in emitted:
        assert line.startswith("::warning"), f"reported at the wrong tier: {line!r}"


# ------------------------------------------------- invariant I4, both ways


def test_warning_never_blocks(store: Path) -> None:
    """Hygiene findings warn and exit 0 — fail-open on join."""
    _patch(
        store / "workstreams" / "WS-PROPHET-US-ENTRY-TIMING.md",
        "landmines:",
        "claim:\n  by: claude/ghost\n  at: 2025-01-01\n  expires: 2025-01-02\nlandmines:",
    )
    result = _validate(store)
    assert result.returncode == 0, result.stdout
    assert _findings(result, "stale-claim", on="WS-PROPHET-US-ENTRY-TIMING.md"), result.stdout


# ------------------------------------- the hard/soft line, and why it moved
#
# `validate` runs UNSCOPED on every PR in the fleet, over the whole store, not over the
# diff.  So a hard rule that keys on the STATE of the work is a fleet-wide fail-closed
# gate on a knowledge record — and it is reachable without anyone writing an invalid
# record.  These tests pin the demotion; each one EXITED 1 before it.


STATE_RULES_ARE_WARNINGS: list[tuple[str, str, str, str]] = [
    (
        "active-but-complete",
        "workstreams/WS-MACRO-CONTEXT-INDEX.md",
        # C0 regold 2026-08-28: W2/C0 are now `done`, so flipping the one
        # remaining in_progress wave (W1) to done manufactures the
        # all-waves-complete-but-status-active inconsistency by itself.
        "  - id: W1\n"
        "    title: Benchmark gates to green so the index stops being advisory\n"
        "    status: in_progress",
        "  - id: W1\n"
        "    title: Benchmark gates to green so the index stops being advisory\n"
        "    status: done",
    ),
    # These two anchor on WS-CN-LIMIT-ALPHA's LIVE top-level state and must CREATE
    # the inconsistent state from it (2026-08-14: the record moved blocked->active
    # with no blocked_by, which silently broke the previous anchors — a mutation
    # that only works while a real program stays blocked is a fixture landmine).
    # If the record's top-level status changes again, update the anchors so the
    # replacement still manufactures the rule's inconsistency by itself.
    (
        "blocked-without-cause",
        "workstreams/WS-CN-LIMIT-ALPHA.md",
        "status: active",
        "status: blocked",
    ),
    (
        "cause-without-blocked",
        "workstreams/WS-CN-LIMIT-ALPHA.md",
        "status: active",
        "status: active\nblocked_by:\n  - schema-probe cause (test-injected)",
    ),
]


@pytest.mark.parametrize(
    "rule,rel,anchor,replacement", STATE_RULES_ARE_WARNINGS,
    ids=[m[0] for m in STATE_RULES_ARE_WARNINGS],
)
def test_state_rules_warn_and_do_not_block(
    store: Path, rule: str, rel: str, anchor: str, replacement: str
) -> None:
    """Work-state disagreement is reported, never fatal."""
    _patch(store / rel, anchor, replacement)
    result = _validate(store)
    assert result.returncode == 0, (
        f"{rule} still hard-fails; a fleet-wide unscoped check must not gate on work "
        f"state:\n{result.stdout}"
    )
    assert _findings(result, rule, on=Path(rel).name), (
        f"{rule} was demoted into silence on the record this case mutates.  Scoped to "
        f"{Path(rel).name} on purpose: the committed store already emits "
        f"`active-but-complete` and `blocked-without-cause` on unrelated records, so an "
        f"unscoped `{rule} in stdout` passed here against an UNMUTATED store "
        f"(measured 2026-09-27):\n{result.stdout}"
    )


def test_clean_merge_of_two_valid_states_validates(store: Path, tmp_path: Path) -> None:
    """THE reproduction: two green PRs, a clean git merge, and a red main.

    Branch A marks one wave done; branch B marks another dropped.  Each validates 0.
    The textual merge is clean — different lines.  The merged tree is what the fleet
    then runs `validate` over on EVERY subsequent PR, so if the merged state hard-failed,
    two individually-correct sessions would red main with no bad record anywhere.
    """
    repo = tmp_path / "merge-probe"
    shutil.copytree(store, repo / "agentos")

    def git(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True)

    git("init", "-q", "-b", "main")
    git("config", "user.email", "test@example.com")
    git("config", "user.name", "test")
    git("add", "-A")
    git("commit", "-qm", "base")

    record = repo / "agentos" / "workstreams" / "WS-MACRO-CONTEXT-INDEX.md"
    git("checkout", "-q", "-b", "branch-a")
    _patch(record, "    status: in_progress", "    status: done")
    assert _validate(repo / "agentos").returncode == 0, "branch A is a valid state"
    git("commit", "-aqm", "W1 done")

    git("checkout", "-q", "main")
    git("checkout", "-q", "-b", "branch-b")
    # C0 regold 2026-08-28: no wave carries `status: todo` any more; drop the
    # C0 wave instead (its block is far enough from W1's for a clean merge).
    _patch(
        record,
        '    title: "Benchmark Truth Recovery (Sol op macro-context-index-completion-20260828-sol-001)"\n'
        "    status: done",
        '    title: "Benchmark Truth Recovery (Sol op macro-context-index-completion-20260828-sol-001)"\n'
        "    status: dropped",
    )
    assert _validate(repo / "agentos").returncode == 0, "branch B is a valid state"
    git("commit", "-aqm", "W2 dropped")

    git("checkout", "-q", "branch-a")
    merge = git("merge", "--no-edit", "branch-b")
    assert merge.returncode == 0, f"the merge itself must be clean:\n{merge.stdout}{merge.stderr}"

    result = _validate(repo / "agentos")
    assert result.returncode == 0, (
        "a clean merge of two individually-valid records must not red the fleet:\n"
        + result.stdout
    )


def test_bare_key_dependency_is_rejected_not_dropped(store: Path) -> None:
    """`depends_on: [FOO]` must not validate silently — the edge would vanish."""
    _patch(
        store / "workstreams" / "WS-AGENT-OS.md",
        "class: adjudication",
        "class: adjudication\ndepends_on: [TOTALLY-NONEXISTENT]",
    )
    result = _validate(store)
    assert result.returncode == 1, (
        "a bare depends_on key used to validate with 0 errors AND 0 warnings, which "
        f"silently removed an edge from the dependency graph:\n{result.stdout}"
    )
    assert "bad-citation" in result.stdout


def test_bare_supersedes_key_is_rejected_not_dropped(store: Path) -> None:
    """`supersedes: [FOO]` must not validate silently — `_refs` drops the bare key,
    which used to skip the reciprocity check entirely (the superseded_by defect class,
    one field over)."""
    _patch(
        store / "decisions" / "DEC-AGENTOS-READINESS-FEEDS-THE-AGENDA.md",
        "supersedes: [DEC:AGENTOS-START-NEXT-VS-AGENDA]",
        "supersedes: [AGENTOS-START-NEXT-VS-AGENDA]",
    )
    result = _validate(store)
    assert result.returncode == 1, (
        "a bare supersedes key used to validate clean while silently skipping the "
        f"reciprocity check:\n{result.stdout}"
    )
    assert "bad-citation" in result.stdout


def test_prefixed_unknown_dependency_is_still_dangling(store: Path) -> None:
    _patch(
        store / "workstreams" / "WS-AGENT-OS.md",
        "class: adjudication",
        "class: adjudication\ndepends_on: [WS:TOTALLY-NONEXISTENT]",
    )
    result = _validate(store)
    assert result.returncode == 1
    assert "dangling-ref" in result.stdout


# ------------------------------------------------- discovery admission gates


def test_unfalsifiable_discovery_is_rejected(store: Path) -> None:
    """`falsifier: no` passed a non-empty check and failed the gate it encodes."""
    _patch(
        store / "discoveries" / "DSC-GOVERNANCE-JSONL-NOT-TRACKED.md",
        "falsifier: >",
        "falsifier: it just is not\nunused_falsifier: >",
    )
    result = _validate(store)
    assert result.returncode == 1, result.stdout
    assert "unfalsifiable-claim" in result.stdout


def test_unprovable_verification_is_rejected(store: Path) -> None:
    _patch(
        store / "discoveries" / "DSC-GOVERNANCE-JSONL-NOT-TRACKED.md",
        'verified_by: "git ls-files',
        'verified_by: vibes\nunused_verified_by: "git ls-files',
    )
    result = _validate(store)
    assert result.returncode == 1, result.stdout
    assert "unprovable-verification" in result.stdout


# --------------------------------------------------------------- handoffs


HANDOFF = """---
workstream: WS:AGENT-OS
session: claude/agentos-phase2
model: opus
mission: Build the status generator.
state_before: Phase 0 landed; status and brief were stubs.
changed:
  - path: scripts/agentos.py
    what: added the status and brief subcommands
verified:
  - claim: validate still exits 0 on the real store
    command: python3 scripts/agentos.py validate
    result: "0 error(s)"
unverified: []
unresolved:
  - Whether C3 is ruled the way this session recommends.
next_actions:
  - Rule on C3.
do_not_redo:
  - Re-deriving PR state from gh; active_builds.v1 is the only source.
danger_areas:
  - validate runs unscoped on every PR in the fleet.
ended_because: complete
---

## What happened
The generator was built and the record set was repaired.
"""


def _write_handoff(store: Path, body: str) -> Path:
    target = store / "handoffs" / "AGENT-OS-2026-08-12.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")
    return target


def test_valid_handoff_is_counted(store: Path) -> None:
    """Handoffs used not to be validated OR counted — garbage read as an empty store.

    Asserts baseline+1, not an absolute count: the committed store legitimately
    accrues real handoffs (Phase 1 adoption), and pinning "1 handoffs" made the
    first real handoff ever written red this suite fleet-wide.
    """
    baseline = len(list((store / "handoffs").glob("*.md")))
    _write_handoff(store, HANDOFF)
    result = _validate(store)
    assert result.returncode == 0, result.stdout
    assert f"{baseline + 1} handoffs" in result.stdout


def test_garbage_handoff_is_rejected(store: Path) -> None:
    _write_handoff(store, "---\nthis: is not a handoff\nmodel: telepathy\n---\n\nSee above.\n")
    result = _validate(store)
    assert result.returncode == 1, (
        "a garbage handoff used to validate clean and was not even counted:\n"
        + result.stdout
    )


def test_handoff_verified_claim_needs_its_command(store: Path) -> None:
    _write_handoff(store, HANDOFF.replace(
        "    command: python3 scripts/agentos.py validate\n", ""))
    result = _validate(store)
    assert result.returncode == 1
    assert "unbacked-verification" in result.stdout


def test_handoff_unverified_may_be_empty_but_not_absent(store: Path) -> None:
    """An empty list is a meaningful answer; an absent key is not."""
    _write_handoff(store, HANDOFF.replace("unverified: []\n", ""))
    result = _validate(store)
    assert result.returncode == 1
    assert "'unverified'" in result.stdout


def test_handoff_body_may_not_point_at_a_conversation(store: Path) -> None:
    _write_handoff(store, HANDOFF.replace(
        "The generator was built and the record set was repaired.",
        "See above for what changed."))
    result = _validate(store)
    assert result.returncode == 1
    assert "context-free-handoff" in result.stdout


ORPHAN_DISCOVERY = """---
key: ORPHAN-PROBE
claim: An orphaned discovery exists solely to exercise the GC candidate rule.
falsifier: "grep -c ORPHAN-PROBE agentos/discoveries/ — a zero result disproves it."
so_what: A future session must not delete a discovery that a handoff still cites.
kind: architecture
verified_at: 2020-01-01
verified_by: "scripts/agentos.py:1 (fixture record, never shipped)"
scope: [macro]
confidence: verified
---

## Detail
Fixture only.
"""


def test_handoff_citation_counts_against_discovery_gc(store: Path) -> None:
    """A discovery cited ONLY by a handoff is cited — it used to read as an orphan.

    `check_references` counted citations from workstreams and decisions only, so a
    finding whose sole reader was a session handoff aged into a 90-day GC candidate.
    """
    (store / "discoveries" / "DSC-ORPHAN-PROBE.md").write_text(
        ORPHAN_DISCOVERY, encoding="utf-8")
    without = _validate(store)
    assert without.returncode == 0, without.stdout
    assert _findings(without, "uncited-discovery", on="DSC-ORPHAN-PROBE"), without.stdout

    _write_handoff(store, HANDOFF.replace(
        "unverified: []\n",
        "unverified: []\ndiscoveries: [DSC:ORPHAN-PROBE]\n"))
    with_citation = _validate(store)
    assert with_citation.returncode == 0, with_citation.stdout
    assert not _findings(with_citation, "uncited-discovery", on="DSC-ORPHAN-PROBE"), (
        "the handoff citation must clear THIS discovery:\n" + with_citation.stdout
    )


# Fixture subjects.  Every assertion below is scoped to one of these, never to the
# marker alone — see `_findings`.
IN_REPO_PHANTOM = "research/NO_SUCH_DOC.md"
CROSS_REPO_PHANTOM = "terminal:app/routes/portfolio.tsx"
GHOST_OWNS_PATH = "engine/ghost_dir"


def test_phantom_artifact_warns(store: Path) -> None:
    """A record citing a file that was never there sends the next session hunting."""
    _patch(
        store / "workstreams" / "WS-PROPHET-US-ENTRY-TIMING.md",
        "landmines:",
        f"artifacts:\n  - {IN_REPO_PHANTOM}\nlandmines:",
    )
    result = _validate(store)
    assert result.returncode == 0, "phantom paths are hygiene, not schema — must not block"
    assert _findings(result, "phantom-artifact", on=IN_REPO_PHANTOM), result.stdout


def test_phantom_owns_path_warns(store: Path) -> None:
    _patch(
        store / "workstreams" / "WS-PROPHET-US-ENTRY-TIMING.md",
        "  - engine/prophet_*.py",
        f"  - {GHOST_OWNS_PATH}/*.py",
    )
    result = _validate(store)
    assert result.returncode == 0
    assert _findings(result, "phantom-owns-path", on=GHOST_OWNS_PATH), result.stdout


def test_cross_repo_path_is_unchecked_when_that_checkout_is_absent(
    store: Path, tmp_path: Path
) -> None:
    """An absent sibling checkout is unknowable, not wrong (I4) — no warning.

    Scoped to the entries THIS fixture writes.  The subject is the cross-repo one; the
    in-repo phantom beside it and the present-checkout run below are the positive
    controls, so the test cannot be satisfied by a validator that warns about nothing.
    """
    _patch(
        store / "workstreams" / "WS-PROPHET-US-ENTRY-TIMING.md",
        "landmines:",
        f"artifacts:\n  - {CROSS_REPO_PHANTOM}\n  - {IN_REPO_PHANTOM}\nlandmines:",
    )
    absent = _validate(store, MACRO_TERMINAL_REPO=str(tmp_path / "no-such-checkout"))
    assert absent.returncode == 0
    assert not _findings(absent, "phantom-artifact", on=CROSS_REPO_PHANTOM), (
        "an absent sibling checkout leaves the path UNCHECKED (I4); it is not a phantom:\n"
        + absent.stdout
    )
    assert _findings(absent, "phantom-artifact", on=IN_REPO_PHANTOM), (
        "positive control — the in-repo phantom in the SAME record must still warn, or "
        "the assertion above would hold against a validator that checks nothing:\n"
        + absent.stdout
    )

    # The mirror, and the control that actually pins fail-open: point the env var at a
    # checkout that EXISTS and lacks the path.  The join stops being skipped and the very
    # same entry must warn — so dropping the `root is None` guard fails here, rather than
    # merely ceasing to be exercised.
    present = tmp_path / "terminal-checkout"
    present.mkdir()
    checked = _validate(store, MACRO_TERMINAL_REPO=str(present))
    assert checked.returncode == 0, "still a warning, never a hard failure"
    assert _findings(checked, "phantom-artifact", on=CROSS_REPO_PHANTOM), (
        "a PRESENT sibling checkout lacking the path must warn:\n" + checked.stdout
    )


def test_cross_repo_path_is_resolved_against_its_own_repo(store: Path, tmp_path: Path) -> None:
    """The silent FALSE PASS is the worse half of a Macro-pinned root.

    `terminal:scripts/agentos.py` exists in Macro and does not exist in Terminal.  A
    root pinned to the Macro checkout reports it as present — a clean bill of health for
    a path that is not there.
    """
    terminal = tmp_path / "terminal-checkout"
    terminal.mkdir()
    _patch(
        store / "workstreams" / "WS-PROPHET-US-ENTRY-TIMING.md",
        "landmines:",
        "artifacts:\n  - terminal:scripts/agentos.py\nlandmines:",
    )
    assert (REPO / "scripts" / "agentos.py").exists(), "the path must exist in MACRO"
    result = _validate(store, MACRO_TERMINAL_REPO=str(terminal))
    assert result.returncode == 0, "still a warning, never a hard failure"
    assert _findings(result, "phantom-artifact", on="terminal:scripts/agentos.py"), (
        "a Terminal path that exists only in Macro must not read as present:\n"
        + result.stdout
    )


def test_absent_store_exits_zero(tmp_path: Path) -> None:
    """A repo that has not adopted Agent OS is not a broken repo."""
    result = _validate(tmp_path / "nonexistent")
    assert result.returncode == 0
    assert "no agentos/ store" in result.stdout


def test_quiet_suppresses_warnings_but_not_errors(store: Path) -> None:
    """--quiet hides the warning LINES; it must not stop the checking.

    The bare `"stale-claim" not in stdout` this replaces was unfalsifiable: it held just
    as well if the rule had been deleted.  So the loud run below is the positive control,
    and the summary count keeps `--quiet` honest about having still looked.
    """
    _patch(
        store / "workstreams" / "WS-PROPHET-US-ENTRY-TIMING.md",
        "landmines:",
        "claim:\n  by: claude/ghost\n  at: 2025-01-01\n  expires: 2025-01-02\nlandmines:",
    )
    loud = _validate(store)
    assert _findings(loud, "stale-claim", on="WS-PROPHET-US-ENTRY-TIMING.md"), (
        "positive control — the fixture must produce the warning that --quiet then "
        "suppresses:\n" + loud.stdout
    )

    result = subprocess.run(
        [sys.executable, str(CLI), "validate", "--root", str(store), "--quiet"],
        capture_output=True,
        text=True,
        cwd=REPO,
    )
    assert result.returncode == 0
    assert not _findings(result, "stale-claim", on="WS-PROPHET-US-ENTRY-TIMING.md"), result.stdout
    # The mode contract itself, and uncoupled from any particular record: no warning
    # annotation survives --quiet, while the summary still counts what was found.
    assert not [ln for ln in result.stdout.splitlines() if ln.startswith("::warning")], \
        result.stdout
    # Read the count as a NUMBER.  `"0 warning(s)" not in stdout` is the very substring
    # trap this file is being cured of: it also matches "110 warning(s)", so it fired on
    # the store's real total the moment the sibling checkouts were absent.
    summary = [ln for ln in result.stdout.splitlines() if ln.startswith("agentos: ")]
    assert summary, "no summary line:\n" + result.stdout
    counted = re.search(r"(\d+) warning\(s\)", summary[-1])
    assert counted, "summary names no warning count: " + summary[-1]
    assert int(counted.group(1)) > 0, (
        "--quiet must suppress the display, not the detection:\n" + result.stdout
    )


# ------------------------------------------------------ house annotation law


def test_annotations_start_the_line(store: Path) -> None:
    """`::error`/`::warning` must START the line or GitHub silently drops them.

    This shipped dead five times in this repo before #3587 swept 69 sites, so the
    assertion is on line position, not on wording.
    """
    _patch(store / "workstreams" / "WS-AGENT-OS.md", "\nstatus:", "\nstatus: humming #")
    result = _validate(store)
    annotations = [ln for ln in result.stdout.splitlines() if "::error" in ln or "::warning" in ln]
    assert annotations, "no annotation emitted for a hard failure"
    for line in annotations:
        assert line.startswith("::"), f"annotation does not start the line: {line!r}"


def test_no_subcommand_still_announces_itself_as_a_stub() -> None:
    """Every advertised subcommand must do work or say it cannot — never exit silently.

    The expensive part of this contract is breadth, not process isolation.  One real CLI
    invocation proves argparse/transport wiring; the all-workstream sweep then reuses one
    parsed Store in-process.  Spawning one Python interpreter per workstream reparsed the
    entire Agent OS graph ~40 times and made this single contract dominate merge-gate wall
    time without proving a different behavior.
    """
    source = CLI.read_text(encoding="utf-8")
    assert "not implemented until" not in source, "a stub announcement outlived its stub"

    usage_error = subprocess.run(
        [sys.executable, str(CLI), "compile-context"], capture_output=True, text=True, cwd=REPO
    )
    assert usage_error.returncode == 2, (
        "neither a task nor --workstream is a USAGE error, not a silent empty bundle"
    )
    assert "exactly one" in usage_error.stderr

    # One true process boundary pins the public CLI. Argparse behavior does not vary by
    # workstream key, so repeating the process boundary for every record adds cost, not
    # coverage.
    representative = SEED_KEYS[0]
    real = subprocess.run(
        [sys.executable, str(CLI), "compile-context", "--workstream", representative,
         "--now", "2026-08-12T14:00:00Z"],
        capture_output=True, text=True, cwd=REPO,
    )
    assert real.returncode == 0, real.stdout + real.stderr
    real_bundle = json.loads(real.stdout)
    assert real_bundle["schema"] == "context_bundle.v1"
    assert any(section["items"] for section in real_bundle["sections"]), (
        f"WS:{representative} compiled to an empty bundle — a stub in everything but name"
    )

    # Breadth is still exhaustive. Load/validate the committed graph once, then compile
    # every seeded workstream through the same production compiler. Git timestamps and
    # repo SHA have dedicated contracts elsewhere; neutralising those read-only joins here
    # prevents this breadth proof from becoming a history benchmark.
    import importlib.util

    spec = importlib.util.spec_from_file_location("agentos_schema_breadth", CLI)
    assert spec is not None and spec.loader is not None
    agentos = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(agentos)
    parsed_store = agentos.load_store(STORE, agentos._load_programs())
    hard = [problem for problem in parsed_store.problems if problem.hard]
    assert not hard, "the committed store must be valid before breadth compilation"
    now = agentos._parse_moment("2026-08-12T14:00:00Z")
    assert now is not None

    original_git_dates = agentos.git_dates
    original_repo_sha = agentos._repo_sha
    agentos.git_dates = lambda _path: (None, None)
    agentos._repo_sha = lambda: "test-sha"
    try:
        for key in SEED_KEYS:
            bundle = agentos.compile_bundle(
                parsed_store,
                workstream=key,
                now=now,
                builds=None,
                degraded=agentos.Degraded(),
            )
            assert bundle["schema"] == "context_bundle.v1"
            assert bundle["target"]["workstream"] == f"WS:{key}"
            assert any(section["items"] for section in bundle["sections"]), (
                f"WS:{key} compiled to an empty bundle — a stub in everything but name"
            )
    finally:
        agentos.git_dates = original_git_dates
        agentos._repo_sha = original_repo_sha


# -------------------------------------------------- R8-B2 semantic program source


def _load_agentos_module_for_program_registry():
    import importlib.util

    spec = importlib.util.spec_from_file_location("agentos_program_registry_contract", CLI)
    assert spec is not None and spec.loader is not None
    agentos = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(agentos)
    return agentos


def _write_program_registry(
    path: Path,
    *,
    lifecycle_states: tuple[str, ...] = ("operating", "building"),
    programs_yaml: str,
) -> None:
    lifecycle = "\n".join(f"    - {value}" for value in lifecycle_states)
    path.write_text(
        "schema: mastermind_programs.v1\n"
        "ontology:\n"
        "  lifecycle_states:\n"
        f"{lifecycle}\n"
        "programs:\n"
        f"{programs_yaml}",
        encoding="utf-8",
    )


def test_program_registry_normalizes_exact_keys_and_sorts_them(tmp_path: Path) -> None:
    agentos = _load_agentos_module_for_program_registry()
    path = tmp_path / "mastermind_programs.yml"
    _write_program_registry(
        path,
        programs_yaml=(
            "  beta-program:\n"
            "    name: Beta\n"
            "    category: market_intelligence\n"
            "    kind: intelligence_program\n"
            "    lifecycle_state: building\n"
            "    scope: project\n"
            "  alpha-program:\n"
            "    name: Alpha\n"
            "    category: project_infrastructure\n"
            "    kind: infrastructure\n"
            "    lifecycle_state: operating\n"
            "    scope: project\n"
        ),
    )

    got = agentos._load_program_registry(path)

    assert got["schema"] == "agentos.program_registry.v1"
    assert got["available"] is True
    assert [row["key"] for row in got["programs"]] == ["alpha-program", "beta-program"]
    assert got["programs"][1]["lifecycle_state"] == "building"


def test_program_registry_lifecycle_membership_comes_from_authored_ontology(tmp_path: Path) -> None:
    agentos = _load_agentos_module_for_program_registry()
    path = tmp_path / "mastermind_programs.yml"
    _write_program_registry(
        path,
        lifecycle_states=("operating", "building", "evidence_wait"),
        programs_yaml=(
            "  alpha-program:\n"
            "    name: Alpha\n"
            "    category: market_intelligence\n"
            "    kind: research_program\n"
            "    lifecycle_state: evidence_wait\n"
            "    scope: project\n"
        ),
    )

    got = agentos._load_program_registry(path)

    assert got["available"] is True
    assert got["programs"][0]["lifecycle_state"] == "evidence_wait"


def test_program_registry_rejects_lifecycle_absent_from_authored_ontology(tmp_path: Path) -> None:
    agentos = _load_agentos_module_for_program_registry()
    path = tmp_path / "mastermind_programs.yml"
    _write_program_registry(
        path,
        lifecycle_states=("operating", "building"),
        programs_yaml=(
            "  alpha-program:\n"
            "    name: Alpha\n"
            "    category: market_intelligence\n"
            "    kind: research_program\n"
            "    lifecycle_state: evidence_wait\n"
            "    scope: project\n"
        ),
    )

    got = agentos._load_program_registry(path)

    assert got["available"] is False
    assert got["reason"] == "program_registry_malformed"
    assert got["programs"] == []


def test_richer_metadata_failure_does_not_delete_legacy_program_key(
    tmp_path: Path, monkeypatch,
) -> None:
    agentos = _load_agentos_module_for_program_registry()
    path = tmp_path / "mastermind_programs.yml"
    _write_program_registry(
        path,
        programs_yaml=(
            "  alpha-program:\n"
            "    category: market_intelligence\n"
            "    kind: research_program\n"
            "    lifecycle_state: building\n"
            "    scope: project\n"
        ),
    )
    monkeypatch.setattr(agentos, "_PROGRAMS", path)

    assert agentos._load_programs() == {"alpha-program"}
    got = agentos._load_program_registry(path)
    assert got["available"] is False
    assert got["reason"] == "program_registry_malformed"


def test_program_registry_missing_source_is_explicit_unavailable(tmp_path: Path) -> None:
    agentos = _load_agentos_module_for_program_registry()
    got = agentos._load_program_registry(tmp_path / "missing.yml")

    assert got == {
        "schema": "agentos.program_registry.v1",
        "available": False,
        "reason": "program_registry_unavailable",
        "source": "config/mastermind_programs.yml",
        "programs": [],
    }


def test_program_identity_is_mapping_key_not_display_name(tmp_path: Path) -> None:
    agentos = _load_agentos_module_for_program_registry()
    path = tmp_path / "mastermind_programs.yml"
    _write_program_registry(
        path,
        programs_yaml=(
            "  alpha-program:\n"
            "    name: Totally Different Display Name\n"
            "    category: market_intelligence\n"
            "    kind: research_program\n"
            "    lifecycle_state: building\n"
            "    scope: project\n"
        ),
    )

    got = agentos._load_program_registry(path)

    assert got["available"] is True
    assert [row["key"] for row in got["programs"]] == ["alpha-program"]
    assert got["programs"][0]["name"] == "Totally Different Display Name"


def test_program_registry_heterogeneous_keys_are_explicitly_malformed(tmp_path: Path) -> None:
    agentos = _load_agentos_module_for_program_registry()
    path = tmp_path / "mastermind_programs.yml"
    _write_program_registry(
        path,
        programs_yaml=(
            "  alpha-program:\n"
            "    name: Alpha\n"
            "    category: market_intelligence\n"
            "    kind: research_program\n"
            "    lifecycle_state: building\n"
            "    scope: project\n"
            "  1:\n"
            "    name: Numeric Key\n"
            "    category: market_intelligence\n"
            "    kind: research_program\n"
            "    lifecycle_state: building\n"
            "    scope: project\n"
        ),
    )

    assert agentos._load_program_registry(path) == {
        "schema": "agentos.program_registry.v1",
        "available": False,
        "reason": "program_registry_malformed",
        "source": "config/mastermind_programs.yml",
        "programs": [],
    }


def test_program_registry_invalid_utf8_is_explicitly_malformed(tmp_path: Path) -> None:
    agentos = _load_agentos_module_for_program_registry()
    path = tmp_path / "mastermind_programs.yml"
    path.write_bytes(b"\xff\xfe")

    assert agentos._load_program_registry(path) == {
        "schema": "agentos.program_registry.v1",
        "available": False,
        "reason": "program_registry_malformed",
        "source": "config/mastermind_programs.yml",
        "programs": [],
    }


def _build_state_for_program_registry(agentos, store: Path, *, now: str):
    parsed = agentos.load_store(store, agentos._load_programs())
    moment = agentos._parse_moment(now)
    assert moment is not None
    return agentos.build_state(
        parsed,
        now=moment,
        degraded=agentos.Degraded(),
        builds=None,
        p0_status=None,
        worktrees={"count": 0, "branches": [], "uncommitted": []},
    )


def test_build_state_projects_program_registry_into_the_pure_contract(
    store: Path, tmp_path: Path, monkeypatch,
) -> None:
    """Removing the state projection or PURE_SECTIONS membership must fail."""
    agentos = _load_agentos_module_for_program_registry()
    parsed_store = agentos.load_store(store, agentos._load_programs())
    path = tmp_path / "mastermind_programs.yml"
    _write_program_registry(
        path,
        programs_yaml=(
            "  beta-program:\n"
            "    name: Beta\n"
            "    category: market_intelligence\n"
            "    kind: intelligence_program\n"
            "    lifecycle_state: building\n"
            "    scope: project\n"
        ),
    )
    monkeypatch.setattr(agentos, "_PROGRAMS", path)
    monkeypatch.setattr(agentos, "git_dates", lambda _path: (None, None))
    moment = agentos._parse_moment("2026-08-28T16:00:00Z")
    assert moment is not None

    state = agentos.build_state(
        parsed_store,
        now=moment,
        degraded=agentos.Degraded(),
        builds=None,
        p0_status=None,
        worktrees={"count": 0, "branches": [], "uncommitted": []},
    )

    expected = {
        "schema": "agentos.program_registry.v1",
        "available": True,
        "source": "config/mastermind_programs.yml",
        "programs": [
            {
                "key": "beta-program",
                "name": "Beta",
                "lifecycle_state": "building",
                "scope": "project",
                "kind": "intelligence_program",
                "category": "market_intelligence",
            }
        ],
    }
    assert state["program_registry"] == expected
    assert agentos.pure_section(state)["program_registry"] == expected


def test_build_state_keeps_missing_program_registry_explicit_and_nonfatal(
    store: Path, tmp_path: Path, monkeypatch,
) -> None:
    """An unreadable rich source must not turn status into a hidden healthy empty set."""
    agentos = _load_agentos_module_for_program_registry()
    parsed_store = agentos.load_store(store, agentos._load_programs())
    monkeypatch.setattr(agentos, "_PROGRAMS", tmp_path / "missing.yml")
    monkeypatch.setattr(agentos, "git_dates", lambda _path: (None, None))
    degraded = agentos.Degraded()
    moment = agentos._parse_moment("2026-08-28T16:00:00Z")
    assert moment is not None

    state = agentos.build_state(
        parsed_store,
        now=moment,
        degraded=degraded,
        builds=None,
        p0_status=None,
        worktrees={"count": 0, "branches": [], "uncommitted": []},
    )

    assert state["program_registry"] == {
        "schema": "agentos.program_registry.v1",
        "available": False,
        "reason": "program_registry_unavailable",
        "source": "config/mastermind_programs.yml",
        "programs": [],
    }
    assert degraded.items == []


def test_program_registry_pure_section_is_deterministic_across_wall_clocks(
    store: Path, tmp_path: Path, monkeypatch,
) -> None:
    """A volatile omission from PURE_SECTIONS must not hide the registry contract."""
    agentos = _load_agentos_module_for_program_registry()
    path = tmp_path / "mastermind_programs.yml"
    _write_program_registry(
        path,
        programs_yaml=(
            "  alpha-program:\n"
            "    name: Alpha\n"
            "    category: project_infrastructure\n"
            "    kind: infrastructure\n"
            "    lifecycle_state: operating\n"
            "    scope: project\n"
        ),
    )
    monkeypatch.setattr(agentos, "_PROGRAMS", path)
    monkeypatch.setattr(agentos, "git_dates", lambda _path: (None, None))

    first = _build_state_for_program_registry(
        agentos, store, now="2026-08-28T16:00:00Z"
    )
    second = _build_state_for_program_registry(
        agentos, store, now="2026-08-29T16:00:00Z"
    )

    first_pure = agentos.pure_section(first)
    second_pure = agentos.pure_section(second)
    assert "program_registry" in first_pure
    assert first_pure == second_pure


# ------------------------------------------- Project Recovery R8-B1 typed wait


def _wait_workstream() -> dict[str, object]:
    return {
        "key": "TEST-WAIT",
        "title": "Test wait",
        "objective": "Exercise the typed intentional-wait contract.",
        "status": "active",
        "program": "test-program",
        "repos": ["macro"],
        "owner": "fable",
        "class": "research",
        "blast_radius": "reversible",
        "ambiguity": "specified",
        "waves": [{"id": "w1", "title": "Accrue", "status": "todo"}],
        "next_action": "Accrue prospectively.",
    }


def _wait_hard(rec: dict[str, object]):
    from scripts import agentos

    return [
        problem
        for problem in agentos.check_workstream(
            rec,
            Path("agentos/workstreams/WS-TEST-WAIT.md"),
            {"test-program"},
        )
        if problem.hard
    ]


def test_workstream_wait_accepts_closed_valid_shape() -> None:
    rec = _wait_workstream()
    rec["wait"] = {
        "kind": "natural_evidence",
        "review_after": "2026-09-25",
        "condition": "Review whether the preregistered prospective sample matured.",
    }
    assert _wait_hard(rec) == []


@pytest.mark.parametrize(
    "wait,message_fragment",
    [
        (
            {
                "kind": "until_ready",
                "review_after": "2026-09-25",
                "condition": "Not a registered kind.",
            },
            "kind",
        ),
        ({"kind": "natural_evidence"}, "review_after"),
        (
            {
                "kind": "external_action",
                "review_after": "next week",
                "condition": "Operator action remains outstanding.",
            },
            "review_after",
        ),
        (
            {
                "kind": "external_action",
                "review_after": "2026-09-25",
                "condition": "Operator action remains outstanding.",
                "auto_extend": True,
            },
            "auto_extend",
        ),
    ],
)
def test_workstream_wait_rejects_malformed_closed_contract(
    wait: dict[str, object], message_fragment: str
) -> None:
    rec = _wait_workstream()
    rec["wait"] = wait
    hard = _wait_hard(rec)
    assert any(problem.rule == "bad-wait" for problem in hard)
    assert any(message_fragment in problem.message for problem in hard)


def test_wave_wait_uses_same_contract_and_rejects_blank_condition() -> None:
    rec = _wait_workstream()
    wave = rec["waves"][0]
    assert isinstance(wave, dict)
    wave["wait"] = {
        "kind": "calendar_window",
        "review_after": "2026-09-01",
        "condition": "  ",
    }
    hard = _wait_hard(rec)
    assert any(problem.rule == "bad-wait" for problem in hard)
    assert any("condition" in problem.message for problem in hard)


def _inject_valid_waits(store: Path) -> None:
    record = store / "workstreams" / "WS-AGENT-OS.md"
    _patch(
        record,
        "waves:\n",
        "wait:\n"
        "  kind: natural_evidence\n"
        "  review_after: 2026-09-25\n"
        "  condition: Review whether the preregistered prospective sample matured.\n"
        "waves:\n",
    )
    _patch(
        record,
        "    status: done\n    pr: 5472",
        "    status: done\n"
        "    wait:\n"
        "      kind: calendar_window\n"
        "      review_after: 2026-09-01\n"
        "      condition: Review at the declared calendar window.\n"
        "    pr: 5472",
    )


def test_typed_wait_projects_into_state_without_date_serialization_failure(store: Path) -> None:
    from scripts import agentos

    _inject_valid_waits(store)
    parsed = agentos.load_store(store, agentos._load_programs())
    assert not [problem for problem in parsed.problems if problem.hard]
    now = agentos._parse_moment("2026-08-27T15:00:00Z")
    assert now is not None

    original_git_dates = agentos.git_dates
    agentos.git_dates = lambda _path: (None, None)
    try:
        state = agentos.build_state(
            parsed,
            now=now,
            degraded=agentos.Degraded(),
            builds=None,
            p0_status=None,
            worktrees={"count": 0, "branches": [], "uncommitted": []},
        )
    finally:
        agentos.git_dates = original_git_dates

    row = next(item for item in state["workstreams"] if item["key"] == "AGENT-OS")
    assert row["wait"] == {
        "kind": "natural_evidence",
        "review_after": "2026-09-25",
        "condition": "Review whether the preregistered prospective sample matured.",
    }
    first_wave = next(item for item in row["wave_detail"] if item["id"] == "W0")
    assert first_wave["wait"] == {
        "kind": "calendar_window",
        "review_after": "2026-09-01",
        "condition": "Review at the declared calendar window.",
    }
    json.dumps(state, sort_keys=True)


def test_typed_wait_projects_into_context_target_and_wave_excerpt(store: Path) -> None:
    from scripts import agentos

    _inject_valid_waits(store)
    parsed = agentos.load_store(store, agentos._load_programs())
    now = agentos._parse_moment("2026-08-27T15:00:00Z")
    assert now is not None

    original_git_dates = agentos.git_dates
    original_repo_sha = agentos._repo_sha
    agentos.git_dates = lambda _path: (None, None)
    agentos._repo_sha = lambda: "test-sha"
    try:
        first = agentos.compile_bundle(
            parsed,
            workstream="AGENT-OS",
            now=now,
            builds=None,
            degraded=agentos.Degraded(),
        )
        second = agentos.compile_bundle(
            parsed,
            workstream="AGENT-OS",
            now=now,
            builds=None,
            degraded=agentos.Degraded(),
        )
    finally:
        agentos.git_dates = original_git_dates
        agentos._repo_sha = original_repo_sha

    assert first["target"]["wait"] == {
        "kind": "natural_evidence",
        "review_after": "2026-09-25",
        "condition": "Review whether the preregistered prospective sample matured.",
    }
    workstream_item = next(
        item
        for section in first["sections"]
        for item in section["items"]
        if item.get("kind") == "workstream" and item.get("key") == "WS:AGENT-OS"
    )
    assert "wait: calendar_window" in workstream_item["excerpt"]
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def test_wait_schema_mirror_names_closed_contract() -> None:
    mirror = (REPO / "agentos" / "schema" / "workstream.schema.yml").read_text(
        encoding="utf-8"
    )
    for term in (
        "natural_evidence",
        "external_dependency",
        "calendar_window",
        "external_action",
        "review_after",
        "condition",
    ):
        assert term in mirror


@pytest.mark.parametrize(
    "wait",
    [
        # An unhashable authored `kind` — `kind:` followed by a YAML block sequence, or
        # the flow typo `kind: {natural_evidence}` which PyYAML resolves to a mapping.
        {"kind": ["natural_evidence"], "review_after": "2026-09-25", "condition": "c"},
        {"kind": {"natural_evidence": None}, "review_after": "2026-09-25", "condition": "c"},
        # Unknown keys of INCOMPARABLE types.  Authored YAML resolves bare `no:`/`on:` to
        # bools and `2026-09-01:` to a date, so the closed-contract check — the very rule
        # that exists to reject extra keys — is what a mixed-key mapping reaches first.
        {"kind": "natural_evidence", "review_after": "2026-09-25", "condition": "c",
         1: "a", "zz": "b"},
        {"kind": "natural_evidence", "review_after": "2026-09-25", "condition": "c",
         None: "a", "zz": "b"},
        # Pattern-shaped but not a day.  A review date nobody can arrive at is malformed.
        {"kind": "natural_evidence", "review_after": "2026-13-45", "condition": "c"},
    ],
)
def test_hostile_wait_is_reported_not_raised(wait: dict[str, object]) -> None:
    """A malformed wait must come back as a typed `bad-wait` finding at BOTH scopes.

    Every input here used to raise out of ``check_workstream``, which turns a record-level
    validation finding into a crash of the whole fleet-wide `validate` run — the one
    outcome a validator may never have.
    """
    at_workstream = _wait_workstream()
    at_workstream["wait"] = wait
    assert [p.rule for p in _wait_hard(at_workstream)] == ["bad-wait"]

    at_wave = _wait_workstream()
    waves = at_wave["waves"]
    assert isinstance(waves, list) and isinstance(waves[0], dict)
    waves[0]["wait"] = wait
    assert [p.rule for p in _wait_hard(at_wave)] == ["bad-wait"]


@pytest.mark.parametrize(
    "review_after",
    ["2026-09-25", "2020-01-01", _dt.date(2026, 9, 25), _dt.date(2020, 1, 1)],
)
def test_wait_review_after_accepts_dates_including_past_ones(review_after: object) -> None:
    """A PAST `review_after` is an OVERDUE REVIEW, not an expiry — it stays schema-valid."""
    rec = _wait_workstream()
    rec["wait"] = {
        "kind": "external_action",
        "review_after": review_after,
        "condition": "Operator action remains outstanding.",
    }
    assert _wait_hard(rec) == []


# ------------------------------------------------ D3 record drafts and strict pins
#
# Draft commands print a skeleton and write nothing. ``validate`` with no new
# flags stays the fleet gate (warnings do not fail). ``--paths`` judges only
# the named records. ``--strict`` also fails on schema warnings. ``--snapshot``
# without ``--strict`` reports how many PRs the seat supplied and adds no
# failure. Currency warnings (state_before, point-in-time transcripts) stay
# non-blocking: they are history, not a malformed record.


HEAD_8245 = "c72fde4b2307a389b7ec1c900f93362b5dfc104a"
BASE_8245 = "1f25c4abd1ea1111111111111111111111111111"
HEAD_7792 = "88970a1a1978aaaaaaaaaaaaaaaaaaaaaaaaaaaa"
BASE_7792 = "c4da107fe729e46b4d4036b3e0e290390315d0fd"
HEAD_7870 = "839bd6a1aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
HEAD_7891 = "4eef39349741aaaaaaaaaaaaaaaaaaaaaaaaaaaa"
OLD_7870 = "acc72f3f"
OLD_8245 = "b019f975"
OLD_7891 = "861d4049"

_D3_WS = """---
key: DRAFT-ROUNDTRIP
title: Draft round-trip fixture
objective: Hold a workstream so a drafted handoff citation resolves.
status: active
program: project-active-build-control
repos: [macro]
owner: chairman
class: build
blast_radius: reversible
ambiguity: specified
waves:
  - id: W0
    title: Fixture
    status: todo
next_action: Nothing for this fixture.
---
"""


def _agentos(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    environ = dict(os.environ)
    if env:
        environ.update(env)
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        capture_output=True,
        text=True,
        cwd=REPO,
        env=environ,
    )


def _write_tree(tmp_path: Path, files: dict[str, str]) -> Path:
    root = tmp_path / "agentos"
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


def _yaml_quote(value: str) -> str:
    return json.dumps(value)


def _handoff_payload(**overrides: object) -> dict:
    payload: dict = {
        "schema": "agentos.record_draft.v1",
        "as_of": "2026-10-12T04:42:56Z",
        "workstream": "WS:DRAFT-ROUNDTRIP",
        "session": "lane-w2-agos-strict",
        "model": "fable",
        "ended_because": "ci_handoff",
        "date": "2026-10-12",
        "mission": "Draft a schema-valid handoff skeleton from a seat snapshot.",
        "state_before": "No carrier pin is retyped.",
        "changed": [{"path": "scripts/agentos.py", "what": "added draft subcommands"}],
        "verified": [{
            "claim": "The skeleton names the snapshot head and does not call the network.",
            "command": "python3 scripts/agentos.py validate",
            "result": "0 error(s)",
        }],
        "unresolved": ["Seat copies a real mission before any records PR."],
        "next_actions": ["Keep validate without --strict as the fleet gate."],
        "do_not_redo": ["Do not mint a suffixed handoff filename."],
        "danger_areas": ["A strict check is path-scoped."],
        "prs": [{
            "number": 8245,
            "head_sha": HEAD_8245,
            "base_sha": BASE_8245,
            "draft": True,
            "state": "open",
            "merged": False,
            "read_label": "REQUEST_CHANGES",
            "comments": [{"id": 6117441661}],
            "reviewers": [{"id": 5927055846}],
            "ci_runs": [{"id": 0, "name": "fixture", "conclusion": "skipped"}],
        }],
    }
    payload.update(overrides)
    return payload


def _decision_payload(**overrides: object) -> dict:
    payload: dict = {
        "schema": "agentos.record_draft.v1",
        "key": "DRAFT-ROUNDTRIP-DECISION",
        "question": "Where do head SHAs in a new handoff come from?",
        "answer": "From the seat-supplied snapshot, copied into carriers.",
        "rationale": "Hand-copied heads go stale against the next dump.",
        "alternatives": [{
            "option": "Retype the SHAs from memory.",
            "why_not": "They drift the same night the record is written.",
        }],
        "evidence": ["scripts/agentos.py:150"],
        "affects": ["WS:DRAFT-ROUNDTRIP"],
        "confidence": "high",
        "reversibility": "easy",
        "decided_by": "lane",
        "decided_at": "2026-10-12",
    }
    payload.update(overrides)
    return payload


def _discovery_payload(**overrides: object) -> dict:
    payload: dict = {
        "schema": "agentos.record_draft.v1",
        "key": "DRAFT-ROUNDTRIP-DISCOVERY",
        "claim": "A handoff stem that does not end in a date is invisible to compile-context.",
        "falsifier": "scripts/agentos.py:2737",
        "so_what": "New drafts use the canonical filename and amend it in place.",
        "kind": "landmine",
        "verified_at": "2026-10-12",
        "verified_by": "python3 scripts/agentos.py validate",
        "scope": ["agentos/handoffs/"],
        "confidence": "verified",
    }
    payload.update(overrides)
    return payload


def _dump_json(tmp_path: Path, name: str, payload: dict) -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _pr(number: int, head: str, **extra: object) -> dict:
    row: dict = {
        "number": number,
        "head_sha": head,
        "draft": True,
        "state": "open",
        "merged": False,
    }
    row.update(extra)
    return row


def _handoff_doc(
    *,
    state_before: str,
    changed_what: str,
    unresolved: list[str],
    body: str,
    verified_result: str = "0 error(s)",
    extra_front: str = "",
) -> str:
    items = "\n".join(f"  - {item}" for item in unresolved)
    extra = extra_front
    if extra and not extra.endswith("\n"):
        extra += "\n"
    return (
        "---\n"
        "workstream: WS:DRAFT-ROUNDTRIP\n"
        "session: lane-w2-agos-strict\n"
        "model: fable\n"
        "mission: Pin checks.\n"
        f"state_before: {_yaml_quote(state_before)}\n"
        "changed:\n"
        "  - path: scripts/agentos.py\n"
        f"    what: {_yaml_quote(changed_what)}\n"
        "verified:\n"
        "  - claim: pins\n"
        "    command: python3 scripts/agentos.py validate\n"
        f"    result: {_yaml_quote(verified_result)}\n"
        "unverified: []\n"
        "unresolved:\n"
        f"{items}\n"
        "next_actions:\n"
        "  - Keep the fleet gate unscoped.\n"
        "do_not_redo:\n"
        "  - Do not mint a suffixed name.\n"
        "danger_areas:\n"
        "  - Strict mode is opt-in.\n"
        "ended_because: ci_handoff\n"
        f"{extra}"
        "---\n"
        "\n"
        f"{body}"
    )


def _workstream_with_landmine(sentence: str) -> str:
    return (
        "---\n"
        "key: DRAFT-WORDING\n"
        "title: Wording fixture\n"
        "objective: Hold one landmine sentence.\n"
        "status: active\n"
        "program: project-active-build-control\n"
        "repos: [macro]\n"
        "owner: chairman\n"
        "class: build\n"
        "blast_radius: reversible\n"
        "ambiguity: specified\n"
        "waves:\n"
        "  - id: W0\n"
        "    title: Fixture\n"
        "    status: todo\n"
        "next_action: Nothing for this fixture.\n"
        "landmines:\n"
        f"  - {_yaml_quote(sentence)}\n"
        "---\n"
    )


def test_d3_draft_handoff_round_trips(tmp_path: Path) -> None:
    """A drafted handoff is schema-valid, names the snapshot head, and is not written."""
    canonical = STORE / "handoffs" / "DRAFT-ROUNDTRIP-2026-10-12.md"
    assert not canonical.exists()
    src = _dump_json(tmp_path, "handoff.json", _handoff_payload())
    result = _agentos("draft-handoff", "--from", str(src))
    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith("---\n"), result.stdout
    assert "authored once" not in result.stdout.lower()
    assert "is to be continued at head c72fde4b2307" in result.stdout
    assert "REQUEST_CHANGES" in result.stdout
    assert "not landed" in result.stdout
    assert "6117441661" in result.stdout
    assert HEAD_8245 in result.stdout
    assert not canonical.exists()
    root = _write_tree(tmp_path, {
        "workstreams/WS-DRAFT-ROUNDTRIP.md": _D3_WS,
        "handoffs/DRAFT-ROUNDTRIP-2026-10-12.md": result.stdout,
    })
    validated = _agentos("validate", "--root", str(root))
    assert validated.returncode == 0, validated.stdout + validated.stderr
    assert "0 error(s)" in validated.stdout
    snap = _dump_json(tmp_path, "snap.json", _handoff_payload())
    strict = _agentos(
        "validate", "--strict", "--snapshot", str(snap), "--root", str(root),
        "--paths", str(root / "handoffs" / "DRAFT-ROUNDTRIP-2026-10-12.md"),
    )
    assert strict.returncode == 0, strict.stdout + strict.stderr
    assert "stale-head" not in strict.stdout
    assert "base-sha-reference" not in strict.stdout



def test_d3_draft_handoff_successor_guidance_without_new_gate(tmp_path: Path) -> None:
    """Authoring guidance prevents ghost-parent waits without claiming live custody."""
    payload = _handoff_payload(
        next_actions=["The original writer must finish the existing PR."],
    )
    source = _dump_json(tmp_path, "ghost_parent_handoff.json", payload)
    result = _agentos("draft-handoff", "--from", str(source))
    assert result.returncode == 0, result.stderr
    assert "currently assigned receiver" in result.stdout
    assert "historical original writer" in result.stdout
    assert "STARTed" in result.stdout and "EFFECT_UNKNOWN" in result.stdout
    assert "same original carrier" in result.stdout
    # A drafter cannot know whether a historical writer retains a live lease.
    # Preserve original payload as data; avoid manufacturing a gate or transfer.
    assert "The original writer must finish the existing PR." in result.stdout
    assert "agentos/handoffs/DRAFT-ROUNDTRIP-2026-10-12.md" in result.stdout
    protocol = (REPO / "research/MASTERMIND_AGENT_HANDOFF_PROTOCOL.md").read_text()
    schema = (REPO / "agentos/schema/handoff.schema.yml").read_text()
    assert "Historical writer references are not current liveness" in protocol
    assert "current assigned receiver owns recovery" in schema
    assert "reviewer judgment" in protocol
    root = _write_tree(tmp_path, {
        "workstreams/WS-DRAFT-ROUNDTRIP.md": _D3_WS,
        "handoffs/DRAFT-ROUNDTRIP-2026-10-12.md": result.stdout,
    })
    validated = _agentos("validate", "--root", str(root))
    assert validated.returncode == 0, validated.stdout + validated.stderr


def test_d3_draft_dec_and_decision_round_trip(tmp_path: Path) -> None:
    src = _dump_json(tmp_path, "decision.json", _decision_payload())
    alias = _agentos("draft-dec", "--from", str(src))
    full = _agentos("draft-decision", "--from", str(src))
    assert alias.returncode == 0, alias.stderr
    assert full.returncode == 0, full.stderr
    assert alias.stdout == full.stdout
    assert alias.stdout.startswith("---\n")
    assert "DEC-DRAFT-ROUNDTRIP-DECISION.md" in alias.stdout
    root = _write_tree(tmp_path, {
        "decisions/DEC-DRAFT-ROUNDTRIP-DECISION.md": alias.stdout,
    })
    validated = _agentos("validate", "--root", str(root))
    assert validated.returncode == 0, validated.stdout + validated.stderr
    assert "0 error(s)" in validated.stdout


def test_d3_draft_dsc_and_discovery_round_trip(tmp_path: Path) -> None:
    src = _dump_json(tmp_path, "discovery.json", _discovery_payload())
    alias = _agentos("draft-dsc", "--from", str(src))
    full = _agentos("draft-discovery", "--from", str(src))
    assert alias.returncode == 0, alias.stderr
    assert full.returncode == 0, full.stderr
    assert alias.stdout == full.stdout
    assert alias.stdout.startswith("---\n")
    assert "DSC-DRAFT-ROUNDTRIP-DISCOVERY.md" in alias.stdout
    root = _write_tree(tmp_path, {
        "discoveries/DSC-DRAFT-ROUNDTRIP-DISCOVERY.md": alias.stdout,
    })
    validated = _agentos("validate", "--root", str(root))
    assert validated.returncode == 0, validated.stdout + validated.stderr
    assert "0 error(s)" in validated.stdout


def test_d3_ws_append_phrase_and_no_write(tmp_path: Path) -> None:
    canonical = STORE / "workstreams" / "WS-DRAFT-ROUNDTRIP.md"
    assert not canonical.exists()
    src = _dump_json(tmp_path, "append.json", _handoff_payload())
    result = _agentos("draft-ws-append", "--from", str(src))
    assert result.returncode == 0, result.stderr
    assert "authored once" not in result.stdout.lower()
    assert "#8245 is to be continued at head c72fde4b2307, draft=true, " \
        "under a REQUEST_CHANGES read, not landed." in result.stdout
    assert "6117441661" in result.stdout
    assert not canonical.exists()
    renamed = _handoff_payload()
    renamed["prs"][0].pop("read_label")
    renamed["prs"][0]["review_state"] = "REQUEST_CHANGES"
    alt = _agentos("draft-ws-append", "--from", str(_dump_json(tmp_path, "alt.json", renamed)))
    assert alt.returncode == 0, alt.stderr
    assert "under a REQUEST_CHANGES read, not landed." in alt.stdout


def test_d3_draft_refuses_suffix_priority_and_bad_shape(tmp_path: Path) -> None:
    suffix = _dump_json(tmp_path, "suffix.json", _handoff_payload(suffix="frontier-delegation"))
    refused = _agentos("draft-handoff", "--from", str(suffix))
    assert refused.returncode == 2
    assert refused.stdout == ""
    assert "refusing a filename suffix" in refused.stderr

    priority = _dump_json(tmp_path, "priority.json", _handoff_payload(priority=1))
    refused = _agentos("draft-handoff", "--from", str(priority))
    assert refused.returncode == 2
    assert refused.stdout == ""
    assert "refusing input key 'priority'" in refused.stderr

    gated = _dump_json(tmp_path, "gate.json", _handoff_payload(gate="ship"))
    refused = _agentos("draft-dec", "--from", str(gated))
    assert refused.returncode == 2
    assert refused.stdout == ""
    assert "refusing input key 'gate'" in refused.stderr

    equal = _handoff_payload()
    equal["prs"][0]["base_sha"] = equal["prs"][0]["head_sha"]
    refused = _agentos("draft-handoff", "--from", str(_dump_json(tmp_path, "equal.json", equal)))
    assert refused.returncode == 2
    assert refused.stdout == ""
    assert "base_sha" in refused.stderr

    bad_model = _dump_json(tmp_path, "model.json", _handoff_payload(model="telepathy"))
    assert _agentos("draft-handoff", "--from", str(bad_model)).returncode == 2
    bad_ended = _dump_json(tmp_path, "ended.json", _handoff_payload(ended_because="checkpoint"))
    assert _agentos("draft-handoff", "--from", str(bad_ended)).returncode == 2

    bad_alt = _decision_payload(alternatives=[{"option": "only one side"}])
    refused = _agentos("draft-decision", "--from", str(_dump_json(tmp_path, "alt.json", bad_alt)))
    assert refused.returncode == 2
    assert refused.stdout == ""

    bad_prov = _discovery_payload(falsifier="no")
    refused = _agentos("draft-dsc", "--from", str(_dump_json(tmp_path, "prov.json", bad_prov)))
    assert refused.returncode == 2
    assert refused.stdout == ""
    assert "falsifier" in refused.stderr


def test_d3_strict_requires_snapshot_and_paths(tmp_path: Path) -> None:
    missing_snap = _agentos("validate", "--strict", "--paths", str(tmp_path / "missing.md"))
    assert missing_snap.returncode == 2
    assert "requires --snapshot" in missing_snap.stderr
    assert "records (" not in missing_snap.stdout

    snap = _dump_json(tmp_path, "snap.json", {"prs": []})
    missing_paths = _agentos("validate", "--strict", "--snapshot", str(snap))
    assert missing_paths.returncode == 2
    assert "requires --paths" in missing_paths.stderr
    assert "records (" not in missing_paths.stdout


def test_d3_snapshot_reports_counts_without_new_failures(tmp_path: Path) -> None:
    """A stale prose pin is invisible unless --strict is set. --snapshot only counts."""
    text = _handoff_doc(
        state_before="previous",
        changed_what=f"#8245 head {OLD_8245} is what the prose still says",
        unresolved=["one"],
        body="History only.\n",
    )
    root = _write_tree(tmp_path, {
        "workstreams/WS-DRAFT-ROUNDTRIP.md": _D3_WS,
        "handoffs/DRAFT-ROUNDTRIP-2026-10-12.md": text,
    })
    snap = _dump_json(tmp_path, "snap.json", {"prs": [_pr(8245, HEAD_8245, base_sha=BASE_8245)]})
    reported = _agentos("validate", "--root", str(root), "--snapshot", str(snap))
    assert reported.returncode == 0, reported.stdout + reported.stderr
    assert "snapshot: 1 prs — counts only, not a failing gate" in reported.stdout
    assert "stale-head" not in reported.stdout
    assert "0 error(s)" in reported.stdout


def test_d3_paths_validate_only_named_records(tmp_path: Path) -> None:
    decision = """---
key: DRAFT-ROUNDTRIP-DECISION
question: Where do pins come from?
answer: The seat snapshot.
rationale: Hands go stale.
alternatives:
  - option: Retype them.
    why_not: They drift the same night.
evidence:
  - scripts/agentos.py:150
affects:
  - WS:DRAFT-ROUNDTRIP
confidence: high
reversibility: easy
decided_by: lane
decided_at: "2026-10-12"
review_by: "2020-01-01"
---
"""
    root = _write_tree(tmp_path, {
        "decisions/DEC-DRAFT-ROUNDTRIP-DECISION.md": decision,
        "handoffs/GARBAGE-2026-10-12.md": "---\nthis: no\n---\n\nSee above.\n",
    })
    named = root / "decisions" / "DEC-DRAFT-ROUNDTRIP-DECISION.md"
    scoped = _agentos("validate", "--root", str(root), "--paths", str(named))
    assert scoped.returncode == 0, scoped.stdout + scoped.stderr
    assert "review-overdue" in scoped.stdout
    assert "unparseable" not in scoped.stdout
    assert "context-free-handoff" not in scoped.stdout
    whole = _agentos("validate", "--root", str(root))
    assert whole.returncode == 1
    assert "context-free-handoff" in whole.stdout


def test_d3_strict_fails_on_schema_warnings(tmp_path: Path) -> None:
    decision = """---
key: DRAFT-ROUNDTRIP-DECISION
question: Where do pins come from?
answer: The seat snapshot.
rationale: Hands go stale.
alternatives:
  - option: Retype them.
    why_not: They drift the same night.
evidence:
  - scripts/agentos.py:150
affects:
  - WS:DRAFT-ROUNDTRIP
confidence: high
reversibility: easy
decided_by: lane
decided_at: "2026-10-12"
review_by: "2020-01-01"
---
"""
    root = _write_tree(tmp_path, {
        "decisions/DEC-DRAFT-ROUNDTRIP-DECISION.md": decision,
        "handoffs/GARBAGE-2026-10-12.md": "---\nthis: no\n---\n\nSee above.\n",
    })
    named = root / "decisions" / "DEC-DRAFT-ROUNDTRIP-DECISION.md"
    snap = _dump_json(tmp_path, "snap.json", {"prs": []})
    strict = _agentos(
        "validate", "--strict", "--snapshot", str(snap),
        "--root", str(root), "--paths", str(named),
    )
    assert strict.returncode == 1, strict.stdout + strict.stderr
    assert "review-overdue" in strict.stdout
    assert "context-free-handoff" not in strict.stdout
    assert "unparseable" not in strict.stdout


def test_d3_carriers_head_matches_and_base_pin_fails(tmp_path: Path) -> None:
    src = _dump_json(tmp_path, "handoff.json", _handoff_payload())
    drafted = _agentos("draft-handoff", "--from", str(src))
    assert drafted.returncode == 0, drafted.stderr
    root = _write_tree(tmp_path, {
        "workstreams/WS-DRAFT-ROUNDTRIP.md": _D3_WS,
        "handoffs/DRAFT-ROUNDTRIP-2026-10-12.md": drafted.stdout,
    })
    handoff = root / "handoffs" / "DRAFT-ROUNDTRIP-2026-10-12.md"
    snap = _dump_json(tmp_path, "snap.json", _handoff_payload())
    clean = _agentos(
        "validate", "--strict", "--snapshot", str(snap),
        "--root", str(root), "--paths", str(handoff),
    )
    assert clean.returncode == 0, clean.stdout + clean.stderr

    planted = drafted.stdout.replace(HEAD_8245, BASE_8245, 1)
    assert planted != drafted.stdout
    handoff.write_text(planted, encoding="utf-8")
    dirty = _agentos(
        "validate", "--strict", "--snapshot", str(snap),
        "--root", str(root), "--paths", str(handoff),
    )
    assert dirty.returncode == 1, dirty.stdout + dirty.stderr
    assert "base-sha-reference" in dirty.stdout

    plain = _agentos("validate", "--root", str(root))
    assert plain.returncode == 0, plain.stdout + plain.stderr
    assert "0 error(s)" in plain.stdout


def test_d3_landmine_wording_and_stale_head(tmp_path: Path) -> None:
    pre = (
        "The role is authored once by #8245 "
        f"(head {OLD_8245}, draft, open at 2026-10-11T19:24:48Z)."
    )
    post = (
        "The role is to be authored by #8245 "
        f"(head {OLD_8245}, under a REQUEST_CHANGES read, not landed)."
    )
    snap = _dump_json(tmp_path, "snap.json", {
        "prs": [_pr(
            8245, HEAD_8245, base_sha=BASE_8245, draft=True, merged=False,
            state="open", read_label="REQUEST_CHANGES",
        )],
    })
    pre_root = _write_tree(tmp_path / "pre", {
        "workstreams/WS-DRAFT-WORDING.md": _workstream_with_landmine(pre),
    })
    pre_path = pre_root / "workstreams" / "WS-DRAFT-WORDING.md"
    pre_run = _agentos(
        "validate", "--strict", "--snapshot", str(snap),
        "--root", str(pre_root), "--paths", str(pre_path),
    )
    assert pre_run.returncode == 1, pre_run.stdout + pre_run.stderr
    assert "completion-wording" in pre_run.stdout
    assert "status-wording" in pre_run.stdout

    post_root = _write_tree(tmp_path / "post", {
        "workstreams/WS-DRAFT-WORDING.md": _workstream_with_landmine(post),
    })
    post_path = post_root / "workstreams" / "WS-DRAFT-WORDING.md"
    post_run = _agentos(
        "validate", "--strict", "--snapshot", str(snap),
        "--root", str(post_root), "--paths", str(post_path),
    )
    assert post_run.returncode == 1, post_run.stdout + post_run.stderr
    assert "completion-wording" not in post_run.stdout
    assert "status-wording" not in post_run.stdout
    assert "stale-head" in post_run.stdout


def test_d3_state_before_and_point_in_time_warn_only(tmp_path: Path) -> None:
    text = _handoff_doc(
        state_before=f"#7870 at {OLD_7870} was the previous head.",
        changed_what="No live pin in this field.",
        unresolved=["one"],
        verified_result=f"#7891 at {OLD_7891} equal the heads at that read and were not re-run",
        body="Narrative only.\n",
    )
    root = _write_tree(tmp_path, {
        "workstreams/WS-DRAFT-ROUNDTRIP.md": _D3_WS,
        "handoffs/DRAFT-ROUNDTRIP-2026-10-12.md": text,
    })
    snap = _dump_json(tmp_path, "snap.json", {"prs": [
        _pr(7870, HEAD_7870, base_sha="bbbbbbbbaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", merged=True, state="merged", draft=False),
        _pr(7891, HEAD_7891, base_sha=BASE_8245),
    ]})
    result = _agentos(
        "validate", "--strict", "--snapshot", str(snap), "--root", str(root),
        "--paths", str(root / "handoffs" / "DRAFT-ROUNDTRIP-2026-10-12.md"),
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "state-before-pin" in result.stdout
    assert "point-in-time-head" in result.stdout
    assert "stale-head" not in result.stdout


def test_d3_stale_unresolved_count(tmp_path: Path) -> None:
    text = _handoff_doc(
        state_before="previous",
        changed_what="no pin",
        unresolved=["one", "two", "three", "four", "five"],
        body="Reconcile note: unresolved: 112\n",
    )
    root = _write_tree(tmp_path, {
        "workstreams/WS-DRAFT-ROUNDTRIP.md": _D3_WS,
        "handoffs/DRAFT-ROUNDTRIP-2026-10-12.md": text,
    })
    snap = _dump_json(tmp_path, "snap.json", {"prs": []})
    result = _agentos(
        "validate", "--strict", "--snapshot", str(snap), "--root", str(root),
        "--paths", str(root / "handoffs" / "DRAFT-ROUNDTRIP-2026-10-12.md"),
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert "stale-unresolved-count" in result.stdout


def test_d3_base_label_quiet_and_base_as_head_fires(tmp_path: Path) -> None:
    quiet_text = _handoff_doc(
        state_before="previous",
        changed_what=f"#7792 at {BASE_7792} is the recorded base.",
        unresolved=["one"],
        body=(
            "Research original base remains "
            f"`{BASE_7792}` and must not be described as the head.\n"
        ),
    )
    loud_text = _handoff_doc(
        state_before="previous",
        changed_what=f"#7792 at {BASE_7792[:12]} is the carrier head.",
        unresolved=["one"],
        body="Pinned wrong.\n",
    )
    root = _write_tree(tmp_path, {
        "workstreams/WS-DRAFT-ROUNDTRIP.md": _D3_WS,
        "handoffs/QUIET-2026-10-12.md": quiet_text,
        "handoffs/LOUD-2026-10-12.md": loud_text,
    })
    snap = _dump_json(tmp_path, "snap.json", {
        "prs": [_pr(7792, HEAD_7792, base_sha=BASE_7792, read_label="COMMENT")],
    })
    quiet = _agentos(
        "validate", "--strict", "--snapshot", str(snap), "--root", str(root),
        "--paths", str(root / "handoffs" / "QUIET-2026-10-12.md"),
    )
    assert quiet.returncode == 0, quiet.stdout + quiet.stderr
    assert "base-sha-reference" not in quiet.stdout
    loud = _agentos(
        "validate", "--strict", "--snapshot", str(snap), "--root", str(root),
        "--paths", str(root / "handoffs" / "LOUD-2026-10-12.md"),
    )
    assert loud.returncode == 1, loud.stdout + loud.stderr
    assert "base-sha-reference" in loud.stdout


def test_d3_absent_snapshot_pr_is_fail_open(tmp_path: Path) -> None:
    text = _handoff_doc(
        state_before="previous",
        changed_what="no pin",
        unresolved=["one"],
        body="No prose pin.\n",
        extra_front=(
            "carriers:\n"
            "  - pr: 12345\n"
            "    role: head\n"
            "    sha: abcdef1234567890abcdef1234567890abcdef12\n"
            "    as_of: \"2026-10-12T04:42:56Z\"\n"
        ),
    )
    root = _write_tree(tmp_path, {
        "workstreams/WS-DRAFT-ROUNDTRIP.md": _D3_WS,
        "handoffs/DRAFT-ROUNDTRIP-2026-10-12.md": text,
    })
    snap = _dump_json(tmp_path, "snap.json", {"prs": [_pr(8245, HEAD_8245)]})
    result = _agentos(
        "validate", "--strict", "--snapshot", str(snap), "--root", str(root),
        "--paths", str(root / "handoffs" / "DRAFT-ROUNDTRIP-2026-10-12.md"),
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "snapshot-absent" in result.stdout
    assert "fail-open" in result.stdout


def test_d3_sockets_disabled(tmp_path: Path) -> None:
    sitedir = tmp_path / "nonet"
    sitedir.mkdir()
    (sitedir / "sitecustomize.py").write_text(
        "import socket\n"
        "def _deny(*a, **k):\n"
        "    raise RuntimeError('network access attempted by a zero-network command')\n"
        "socket.socket = _deny\n"
        "socket.create_connection = _deny\n"
        "socket.getaddrinfo = _deny\n",
        encoding="utf-8",
    )
    env = {"PYTHONPATH": str(sitedir)}
    src = _dump_json(tmp_path, "handoff.json", _handoff_payload())
    drafted = _agentos("draft-handoff", "--from", str(src), env=env)
    assert drafted.returncode == 0, drafted.stderr
    assert "network access attempted" not in (drafted.stdout + drafted.stderr)
    root = _write_tree(tmp_path, {
        "workstreams/WS-DRAFT-ROUNDTRIP.md": _D3_WS,
        "handoffs/DRAFT-ROUNDTRIP-2026-10-12.md": drafted.stdout,
    })
    snap = _dump_json(tmp_path, "snap.json", _handoff_payload())
    strict = _agentos(
        "validate", "--strict", "--snapshot", str(snap), "--root", str(root),
        "--paths", str(root / "handoffs" / "DRAFT-ROUNDTRIP-2026-10-12.md"),
        env=env,
    )
    assert strict.returncode == 0, strict.stdout + strict.stderr
    assert "network access attempted" not in (strict.stdout + strict.stderr)
    reported = _agentos("validate", "--root", str(root), "--snapshot", str(snap), env=env)
    assert reported.returncode == 0, reported.stdout + reported.stderr
    assert "network access attempted" not in (reported.stdout + reported.stderr)


_OUTSIDE_DECISION = """---
key: OUTSIDE-PATH
question: Cited by the workstream and left out of --paths.
answer: The file is on disk.
rationale: A partial load must not call this citation dangling.
alternatives:
  - option: Load every record.
    why_not: The handoff joins are already named.
evidence:
  - scripts/agentos.py:2185
affects:
  - WS:DRAFT-ROUNDTRIP
confidence: high
reversibility: easy
decided_by: lane
decided_at: "2026-10-12"
---
"""


def _join_fixture(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Handoff plus its workstream, and a decision the workstream cites.

    The decision is a sibling of the named set: it is a real record, and it
    is not a handoff join target. A garbage handoff sits beside them so a
    full-store load is observable when the test does not block it.
    """
    workstream = _D3_WS.replace(
        "next_action: Nothing for this fixture.\n---\n",
        "next_action: Nothing for this fixture.\n"
        "decisions:\n"
        "  - DEC:OUTSIDE-PATH\n"
        "---\n",
    )
    handoff = _handoff_doc(
        state_before="previous",
        changed_what="No live pin.",
        unresolved=["one"],
        body="Narrative only.\n",
    )
    root = _write_tree(tmp_path, {
        "workstreams/WS-DRAFT-ROUNDTRIP.md": workstream,
        "decisions/DEC-OUTSIDE-PATH.md": _OUTSIDE_DECISION,
        "handoffs/DRAFT-ROUNDTRIP-2026-10-12.md": handoff,
        "handoffs/GARBAGE-2026-10-12.md": "---\nthis: no\n---\n\nSee above.\n",
    })
    return (
        root,
        root / "handoffs" / "DRAFT-ROUNDTRIP-2026-10-12.md",
        root / "workstreams" / "WS-DRAFT-ROUNDTRIP.md",
    )


def _boom_on_full_store(module: object, monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(root: Path, programs: set[str] | None) -> object:
        raise RuntimeError("full-store load")

    monkeypatch.setattr(module, "load_store", _boom)


def test_d3_self_contained_paths_skip_full_store(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    """Named paths that already hold every handoff join must not load the store.

    The workstream cites DEC:OUTSIDE-PATH, which is on disk and not named.
    That citation is not a handoff join. It must not come back dangling, and
    the garbage sibling must not be judged.
    """
    module = _load_agentos_module()
    _boom_on_full_store(module, monkeypatch)
    root, handoff, workstream = _join_fixture(tmp_path)
    snap = _dump_json(tmp_path, "snap.json", {"prs": []})
    args = argparse.Namespace(
        root=str(root),
        quiet=False,
        strict=True,
        snapshot=str(snap),
        paths=[str(handoff), str(workstream)],
    )
    result = module.cmd_validate(args)
    captured = capsys.readouterr()
    assert result == 0, captured.out + captured.err
    assert "dangling-ref" not in captured.out
    assert "unparseable" not in captured.out
    assert "context-free-handoff" not in captured.out
    assert "2 records (1 workstreams, 0 decisions, 0 discoveries, 1 handoffs)" in captured.out


def test_d3_paths_missing_join_target_loads_full_store(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A handoff join that is not in --paths still loads the whole store."""
    module = _load_agentos_module()
    _boom_on_full_store(module, monkeypatch)
    root, handoff, _workstream = _join_fixture(tmp_path)
    snap = _dump_json(tmp_path, "snap.json", {"prs": []})
    args = argparse.Namespace(
        root=str(root),
        quiet=False,
        strict=True,
        snapshot=str(snap),
        paths=[str(handoff)],
    )
    with pytest.raises(RuntimeError, match="full-store load"):
        module.cmd_validate(args)


def _cycle_ws(key: str, depends_on: str) -> str:
    """A schema-valid workstream whose only edge is one workstream depends_on."""
    return _D3_WS.replace("key: DRAFT-ROUNDTRIP\n", f"key: {key}\n").replace(
        "next_action: Nothing for this fixture.\n---\n",
        "next_action: Nothing for this fixture.\n"
        "depends_on:\n"
        f"  - {depends_on}\n"
        "---\n",
    )


def _decision_doc(key: str, extra: str = "") -> str:
    """Schema-valid decision. ``extra`` is frontmatter inserted before the fence."""
    tail = extra if not extra or extra.endswith("\n") else extra + "\n"
    return _OUTSIDE_DECISION.replace("key: OUTSIDE-PATH\n", f"key: {key}\n").replace(
        'decided_at: "2026-10-12"\n---\n',
        'decided_at: "2026-10-12"\n' + tail + "---\n",
    )


def _plain_handoff() -> str:
    return _handoff_doc(
        state_before="previous",
        changed_what="No live pin.",
        unresolved=["one"],
        body="Narrative only.\n",
    )


def _strict_paths_args(root: Path, paths: list[Path], snap: Path) -> argparse.Namespace:
    return argparse.Namespace(
        root=str(root),
        quiet=False,
        strict=True,
        snapshot=str(snap),
        paths=[str(path) for path in paths],
    )


def test_d3_partial_paths_report_outside_workstream_cycle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    """--paths names the handoff and one member of a two-workstream cycle.

    The other workstream is on disk and is not a handoff join, so the partial
    loader must read that file and exit 1 with workstream-cycle. It must not
    call load_store, and the unparseable sibling must stay unjudged.
    """
    module = _load_agentos_module()
    _boom_on_full_store(module, monkeypatch)
    handoff = _handoff_doc(
        state_before="previous",
        changed_what="No live pin.",
        unresolved=["one"],
        body="Narrative only.\n",
    ).replace("workstream: WS:DRAFT-ROUNDTRIP\n", "workstream: WS:CYCLE-NAMED\n")
    root = _write_tree(tmp_path, {
        "workstreams/WS-CYCLE-NAMED.md": _cycle_ws("CYCLE-NAMED", "WS:CYCLE-OUTSIDE"),
        "workstreams/WS-CYCLE-OUTSIDE.md": _cycle_ws("CYCLE-OUTSIDE", "WS:CYCLE-NAMED"),
        "handoffs/CYCLE-NAMED-2026-10-12.md": handoff,
        "handoffs/GARBAGE-2026-10-12.md": "---\nthis: no\n---\n\nSee above.\n",
    })
    named = root / "workstreams" / "WS-CYCLE-NAMED.md"
    handoff_path = root / "handoffs" / "CYCLE-NAMED-2026-10-12.md"
    args = argparse.Namespace(
        root=str(root),
        quiet=False,
        strict=False,
        snapshot=None,
        paths=[str(handoff_path), str(named)],
    )
    result = module.cmd_validate(args)
    captured = capsys.readouterr()
    assert result == 1, captured.out + captured.err
    assert "workstream-cycle" in captured.out
    assert "WS:CYCLE-NAMED" in captured.out
    assert "WS:CYCLE-OUTSIDE" in captured.out
    assert "dangling-ref" not in captured.out
    assert "unparseable" not in captured.out
    assert "2 records (1 workstreams, 0 decisions, 0 discoveries, 1 handoffs)" in captured.out


def test_d3_partial_paths_report_outside_depends_on_cycle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    """A depends_on cycle through a workstream outside --paths still fails.

    The handoff join is the named workstream, so the real cover predicate is
    true. Nothing patches that predicate. The other workstream is on disk
    and is not named. cmd_validate must exit 1 with workstream-cycle and
    must not call load_store.
    """
    module = _load_agentos_module()
    _boom_on_full_store(module, monkeypatch)
    root = _write_tree(tmp_path, {
        "workstreams/WS-DRAFT-ROUNDTRIP.md": _cycle_ws("DRAFT-ROUNDTRIP", "WS:CYCLE-OTHER"),
        "workstreams/WS-CYCLE-OTHER.md": _cycle_ws("CYCLE-OTHER", "WS:DRAFT-ROUNDTRIP"),
        "handoffs/DRAFT-ROUNDTRIP-2026-10-12.md": _plain_handoff(),
        "handoffs/GARBAGE-2026-10-12.md": "---\nthis: no\n---\n\nSee above.\n",
    })
    handoff = root / "handoffs" / "DRAFT-ROUNDTRIP-2026-10-12.md"
    named = root / "workstreams" / "WS-DRAFT-ROUNDTRIP.md"
    snap = _dump_json(tmp_path, "snap.json", {"prs": []})
    args = _strict_paths_args(root, [handoff, named], snap)
    assert module._paths_cover_handoff_joins(root, args.paths) is True
    result = module.cmd_validate(args)
    captured = capsys.readouterr()
    assert result == 1, captured.out + captured.err
    assert "workstream-cycle" in captured.out
    assert "WS:DRAFT-ROUNDTRIP" in captured.out
    assert "WS:CYCLE-OTHER" in captured.out
    assert "dangling-ref" not in captured.out
    assert "unparseable" not in captured.out
    assert "2 records (1 workstreams, 0 decisions, 0 discoveries, 1 handoffs)" in captured.out


def test_d3_partial_paths_report_unreciprocated_supersession(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    """An outside decision that supersedes a named one is still unreciprocated.

    DEC-OLD-DEC is named and has no superseded_by. DEC-NEW-DEC is on disk,
    not named, and lists supersedes DEC:OLD-DEC. The finding sits on the
    named record. The real cover predicate is true; load_store must not run.
    """
    module = _load_agentos_module()
    _boom_on_full_store(module, monkeypatch)
    root = _write_tree(tmp_path, {
        "workstreams/WS-DRAFT-ROUNDTRIP.md": _D3_WS,
        "decisions/DEC-OLD-DEC.md": _decision_doc("OLD-DEC"),
        "decisions/DEC-NEW-DEC.md": _decision_doc(
            "NEW-DEC", "supersedes:\n  - DEC:OLD-DEC\n",
        ),
        "handoffs/DRAFT-ROUNDTRIP-2026-10-12.md": _plain_handoff(),
        "handoffs/GARBAGE-2026-10-12.md": "---\nthis: no\n---\n\nSee above.\n",
    })
    paths = [
        root / "handoffs" / "DRAFT-ROUNDTRIP-2026-10-12.md",
        root / "workstreams" / "WS-DRAFT-ROUNDTRIP.md",
        root / "decisions" / "DEC-OLD-DEC.md",
    ]
    snap = _dump_json(tmp_path, "snap.json", {"prs": []})
    args = _strict_paths_args(root, paths, snap)
    assert module._paths_cover_handoff_joins(root, args.paths) is True
    result = module.cmd_validate(args)
    captured = capsys.readouterr()
    assert result == 1, captured.out + captured.err
    assert "unreciprocated-supersession" in captured.out
    assert "DEC:NEW-DEC" in captured.out
    assert "one-sided-supersession" not in captured.out
    assert "dangling-ref" not in captured.out
    assert "unparseable" not in captured.out
    assert "3 records (1 workstreams, 1 decisions, 0 discoveries, 1 handoffs)" in captured.out


def test_d3_partial_paths_report_outbound_unreciprocated_supersession(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    """A named decision that lists supersedes still fails when the old record is outside.

    DEC-NEW-DEC is named and lists supersedes DEC:OLD-DEC. DEC-OLD-DEC is on
    disk, not named, and has no superseded_by. check_references files
    unreciprocated-supersession on the old file. Self-contained --paths must
    report that finding on the named decision. The real cover predicate is
    true; load_store must not run. The outside file is not counted.
    """
    module = _load_agentos_module()
    _boom_on_full_store(module, monkeypatch)
    root = _write_tree(tmp_path, {
        "workstreams/WS-DRAFT-ROUNDTRIP.md": _D3_WS,
        "decisions/DEC-OLD-DEC.md": _decision_doc("OLD-DEC"),
        "decisions/DEC-NEW-DEC.md": _decision_doc(
            "NEW-DEC", "supersedes:\n  - DEC:OLD-DEC\n",
        ),
        "handoffs/DRAFT-ROUNDTRIP-2026-10-12.md": _plain_handoff(),
        "handoffs/GARBAGE-2026-10-12.md": "---\nthis: no\n---\n\nSee above.\n",
    })
    paths = [
        root / "handoffs" / "DRAFT-ROUNDTRIP-2026-10-12.md",
        root / "workstreams" / "WS-DRAFT-ROUNDTRIP.md",
        root / "decisions" / "DEC-NEW-DEC.md",
    ]
    snap = _dump_json(tmp_path, "snap.json", {"prs": []})
    args = _strict_paths_args(root, paths, snap)
    assert module._paths_cover_handoff_joins(root, args.paths) is True
    result = module.cmd_validate(args)
    captured = capsys.readouterr()
    assert result == 1, captured.out + captured.err
    assert "DEC-NEW-DEC.md: [unreciprocated-supersession]" in captured.out
    assert "DEC:NEW-DEC supersedes this record" in captured.out
    assert "DEC-OLD-DEC.md:" not in captured.out
    assert "one-sided-supersession" not in captured.out
    assert "dangling-ref" not in captured.out
    assert "filename-mismatch" not in captured.out
    assert "unparseable" not in captured.out
    assert "3 records (1 workstreams, 1 decisions, 0 discoveries, 1 handoffs)" in captured.out


def test_d3_paths_report_outbound_unreciprocated_on_lone_decision(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    """--paths of only the decision that lists supersedes still fails.

    DEC-NEW-DEC lists supersedes DEC:OLD-DEC. DEC-OLD-DEC is on disk, not
    named, and has no superseded_by. No handoff is named, so the cover
    predicate is false and the whole store loads. check_references files
    unreciprocated-supersession on the old file. The named decision must
    still fail. The outside record stays uncounted.
    """
    module = _load_agentos_module()
    root = _write_tree(tmp_path, {
        "workstreams/WS-DRAFT-ROUNDTRIP.md": _D3_WS,
        "decisions/DEC-OLD-DEC.md": _decision_doc("OLD-DEC"),
        "decisions/DEC-NEW-DEC.md": _decision_doc(
            "NEW-DEC", "supersedes:\n  - DEC:OLD-DEC\n",
        ),
        "handoffs/DRAFT-ROUNDTRIP-2026-10-12.md": _plain_handoff(),
        "handoffs/GARBAGE-2026-10-12.md": "---\nthis: no\n---\n\nSee above.\n",
    })
    named = root / "decisions" / "DEC-NEW-DEC.md"
    args = argparse.Namespace(
        root=str(root),
        quiet=False,
        strict=False,
        snapshot=None,
        paths=[str(named)],
    )
    assert module._paths_cover_handoff_joins(root, args.paths) is False
    result = module.cmd_validate(args)
    captured = capsys.readouterr()
    assert result == 1, captured.out + captured.err
    assert "DEC-NEW-DEC.md: [unreciprocated-supersession]" in captured.out
    assert "DEC:NEW-DEC supersedes this record" in captured.out
    assert "DEC-OLD-DEC.md:" not in captured.out
    assert "one-sided-supersession" not in captured.out
    assert "dangling-ref" not in captured.out
    assert "filename-mismatch" not in captured.out
    assert "unparseable" not in captured.out
    assert "1 records (0 workstreams, 1 decisions, 0 discoveries, 0 handoffs)" in captured.out


def test_d3_partial_paths_report_one_sided_supersession(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    """superseded_by an outside decision that does not list supersedes still warns.

    --strict blocks that warning. The outside file exists, so a partial load
    must not drop the hole as a false dangling-ref. Cover is the real
    predicate, and load_store must not run.
    """
    module = _load_agentos_module()
    _boom_on_full_store(module, monkeypatch)
    root = _write_tree(tmp_path, {
        "workstreams/WS-DRAFT-ROUNDTRIP.md": _D3_WS,
        "decisions/DEC-OLD-DEC.md": _decision_doc("OLD-DEC", "superseded_by: DEC:NEW-DEC\n"),
        "decisions/DEC-NEW-DEC.md": _decision_doc("NEW-DEC"),
        "handoffs/DRAFT-ROUNDTRIP-2026-10-12.md": _plain_handoff(),
        "handoffs/GARBAGE-2026-10-12.md": "---\nthis: no\n---\n\nSee above.\n",
    })
    paths = [
        root / "handoffs" / "DRAFT-ROUNDTRIP-2026-10-12.md",
        root / "workstreams" / "WS-DRAFT-ROUNDTRIP.md",
        root / "decisions" / "DEC-OLD-DEC.md",
    ]
    snap = _dump_json(tmp_path, "snap.json", {"prs": []})
    args = _strict_paths_args(root, paths, snap)
    assert module._paths_cover_handoff_joins(root, args.paths) is True
    result = module.cmd_validate(args)
    captured = capsys.readouterr()
    assert result == 1, captured.out + captured.err
    assert "one-sided-supersession" in captured.out
    assert "DEC:NEW-DEC" in captured.out
    assert "unreciprocated-supersession" not in captured.out
    assert "dangling-ref" not in captured.out
    assert "unparseable" not in captured.out
    assert "0 error(s), 1 warning(s)" in captured.out
    assert "3 records (1 workstreams, 1 decisions, 0 discoveries, 1 handoffs)" in captured.out


def test_d3_paths_help_documents_uncited_discovery_drop(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    """A --paths subset drops uncited-discovery, and validate --help says so.

    The named discovery is old and cited by nothing in the tree. The partial
    run must stay silent: an outside record this subset did not load could
    still cite it, so keeping the finding would fail --strict where the full
    store would not. Unscoped validate still reports the rule.
    """
    module = _load_agentos_module()
    root = _write_tree(tmp_path, {
        "workstreams/WS-DRAFT-ROUNDTRIP.md": _D3_WS,
        "discoveries/DSC-ORPHAN-PROBE.md": ORPHAN_DISCOVERY,
        "handoffs/DRAFT-ROUNDTRIP-2026-10-12.md": _plain_handoff(),
    })
    discovery = root / "discoveries" / "DSC-ORPHAN-PROBE.md"
    paths = [
        root / "handoffs" / "DRAFT-ROUNDTRIP-2026-10-12.md",
        root / "workstreams" / "WS-DRAFT-ROUNDTRIP.md",
        discovery,
    ]
    snap = _dump_json(tmp_path, "snap.json", {"prs": []})
    args = _strict_paths_args(root, paths, snap)
    args.strict = False
    args.snapshot = None
    assert module._paths_cover_handoff_joins(root, args.paths) is True
    partial = module.cmd_validate(args)
    partial_out = capsys.readouterr()
    assert partial == 0, partial_out.out + partial_out.err
    assert "uncited-discovery" not in partial_out.out
    assert "3 records (1 workstreams, 0 decisions, 1 discoveries, 1 handoffs)" in partial_out.out

    full_args = argparse.Namespace(
        root=str(root), quiet=False, strict=False, snapshot=None, paths=[],
    )
    full = module.cmd_validate(full_args)
    full_out = capsys.readouterr()
    assert full == 0, full_out.out + full_out.err
    assert "uncited-discovery" in full_out.out
    assert "DSC-ORPHAN-PROBE" in full_out.out

    help_run = _agentos("validate", "--help")
    assert help_run.returncode == 0, help_run.stderr
    assert "uncited-discovery" in help_run.stdout


def test_d3_partial_paths_report_misnamed_stem_supersession(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    """A decision stem that is not DEC-<key> still joins on the record's own key.

    DEC-MISNAMED.md carries key OTHER-DEC and supersedes the named DEC-OLD-DEC.
    load_store indexes that content key and reports unreciprocated-supersession
    on the named record. --paths naming the handoff, the workstream, and
    DEC-OLD-DEC must report the same edge, must not call load_store, and must
    not count the outside file or judge its filename-mismatch.
    """
    module = _load_agentos_module()
    root = _write_tree(tmp_path, {
        "workstreams/WS-DRAFT-ROUNDTRIP.md": _D3_WS,
        "decisions/DEC-OLD-DEC.md": _decision_doc("OLD-DEC"),
        "decisions/DEC-MISNAMED.md": _decision_doc(
            "OTHER-DEC", "supersedes:\n  - DEC:OLD-DEC\n",
        ),
        "handoffs/DRAFT-ROUNDTRIP-2026-10-12.md": _plain_handoff(),
        "handoffs/GARBAGE-2026-10-12.md": "---\nthis: no\n---\n\nSee above.\n",
    })
    full = module.load_store(root, None)
    inbound = [
        problem for problem in full.problems
        if problem.rule == "unreciprocated-supersession"
        and problem.path.name == "DEC-OLD-DEC.md"
    ]
    assert inbound, [(problem.rule, problem.path.name) for problem in full.problems]
    assert "DEC:OTHER-DEC" in inbound[0].message
    _boom_on_full_store(module, monkeypatch)
    paths = [
        root / "handoffs" / "DRAFT-ROUNDTRIP-2026-10-12.md",
        root / "workstreams" / "WS-DRAFT-ROUNDTRIP.md",
        root / "decisions" / "DEC-OLD-DEC.md",
    ]
    snap = _dump_json(tmp_path, "snap.json", {"prs": []})
    args = _strict_paths_args(root, paths, snap)
    assert module._paths_cover_handoff_joins(root, args.paths) is True
    result = module.cmd_validate(args)
    captured = capsys.readouterr()
    assert result == 1, captured.out + captured.err
    assert "unreciprocated-supersession" in captured.out
    assert "DEC:OTHER-DEC" in captured.out
    assert "filename-mismatch" not in captured.out
    assert "dangling-ref" not in captured.out
    assert "one-sided-supersession" not in captured.out
    assert "unparseable" not in captured.out
    assert "3 records (1 workstreams, 1 decisions, 0 discoveries, 1 handoffs)" in captured.out


def test_d3_partial_paths_resolve_misnamed_decision_by_content_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    """A named superseded_by resolves a decision whose stem is not DEC-<key>.

    The file is decisions/DEC-MISNAMED.md and its key is OTHER-DEC. The full
    store reports one-sided-supersession on DEC-OLD-DEC, not a dangling ref.
    --paths naming that decision must resolve the same edge and must not call
    load_store. filename-mismatch stays on the outside file only.
    """
    module = _load_agentos_module()
    root = _write_tree(tmp_path, {
        "workstreams/WS-DRAFT-ROUNDTRIP.md": _D3_WS,
        "decisions/DEC-OLD-DEC.md": _decision_doc("OLD-DEC", "superseded_by: DEC:OTHER-DEC\n"),
        "decisions/DEC-MISNAMED.md": _decision_doc("OTHER-DEC"),
        "handoffs/DRAFT-ROUNDTRIP-2026-10-12.md": _plain_handoff(),
        "handoffs/GARBAGE-2026-10-12.md": "---\nthis: no\n---\n\nSee above.\n",
    })
    full = module.load_store(root, None)
    sided = [
        problem for problem in full.problems
        if problem.rule == "one-sided-supersession" and problem.path.name == "DEC-OLD-DEC.md"
    ]
    assert sided, [(problem.rule, problem.path.name) for problem in full.problems]
    assert "DEC:OTHER-DEC" in sided[0].message
    assert not any(
        problem.rule == "dangling-ref" and "OTHER-DEC" in problem.message
        for problem in full.problems
    )
    _boom_on_full_store(module, monkeypatch)
    paths = [
        root / "handoffs" / "DRAFT-ROUNDTRIP-2026-10-12.md",
        root / "workstreams" / "WS-DRAFT-ROUNDTRIP.md",
        root / "decisions" / "DEC-OLD-DEC.md",
    ]
    snap = _dump_json(tmp_path, "snap.json", {"prs": []})
    args = _strict_paths_args(root, paths, snap)
    assert module._paths_cover_handoff_joins(root, args.paths) is True
    result = module.cmd_validate(args)
    captured = capsys.readouterr()
    assert result == 1, captured.out + captured.err
    assert "one-sided-supersession" in captured.out
    assert "DEC:OTHER-DEC" in captured.out
    assert "dangling-ref" not in captured.out
    assert "filename-mismatch" not in captured.out
    assert "unreciprocated-supersession" not in captured.out
    assert "unparseable" not in captured.out
    assert "0 error(s), 1 warning(s)" in captured.out
    assert "3 records (1 workstreams, 1 decisions, 0 discoveries, 1 handoffs)" in captured.out


def test_d3_partial_paths_report_reached_outside_cycle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    """A depends_on cycle that contains no named workstream still fails the one that reaches it.

    WS-REACH depends on WS-OUT-B, and WS-OUT-B cycles with WS-OUT-C. Neither
    cycle member is a handoff join. The full store reports workstream-cycle.
    --paths naming the handoff and WS-REACH must too, on WS-REACH, without
    calling load_store. The outside records stay uncounted.
    """
    module = _load_agentos_module()
    handoff = _plain_handoff().replace(
        "workstream: WS:DRAFT-ROUNDTRIP\n",
        "workstream: WS:REACH\n",
    )
    root = _write_tree(tmp_path, {
        "workstreams/WS-REACH.md": _cycle_ws("REACH", "WS:OUT-B"),
        "workstreams/WS-OUT-B.md": _cycle_ws("OUT-B", "WS:OUT-C"),
        "workstreams/WS-OUT-C.md": _cycle_ws("OUT-C", "WS:OUT-B"),
        "handoffs/REACH-2026-10-12.md": handoff,
        "handoffs/GARBAGE-2026-10-12.md": "---\nthis: no\n---\n\nSee above.\n",
    })
    full = module.load_store(root, None)
    assert any(problem.rule == "workstream-cycle" for problem in full.problems)
    _boom_on_full_store(module, monkeypatch)
    paths = [
        root / "handoffs" / "REACH-2026-10-12.md",
        root / "workstreams" / "WS-REACH.md",
    ]
    snap = _dump_json(tmp_path, "snap.json", {"prs": []})
    args = _strict_paths_args(root, paths, snap)
    assert module._paths_cover_handoff_joins(root, args.paths) is True
    result = module.cmd_validate(args)
    captured = capsys.readouterr()
    assert result == 1, captured.out + captured.err
    assert "workstream-cycle" in captured.out
    assert "WS-REACH.md" in captured.out
    assert "WS:OUT-B" in captured.out
    assert "WS:OUT-C" in captured.out
    assert "dangling-ref" not in captured.out
    assert "unparseable" not in captured.out
    assert "2 records (1 workstreams, 0 decisions, 0 discoveries, 1 handoffs)" in captured.out


def test_d3_paths_report_outside_only_cycle_on_lone_workstream(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    """--paths of only the workstream that reaches an outside cycle still fails.

    WS-REACH depends on WS-OUT-B, and WS-OUT-B cycles with WS-OUT-C. No
    handoff is named, so the cover predicate is false and the whole store
    loads. workstream-cycle is filed on the outside members. The named
    workstream that reaches that cycle must still fail. The outside records
    and the unparseable sibling stay uncounted.
    """
    module = _load_agentos_module()
    handoff = _plain_handoff().replace(
        "workstream: WS:DRAFT-ROUNDTRIP\n",
        "workstream: WS:REACH\n",
    )
    root = _write_tree(tmp_path, {
        "workstreams/WS-REACH.md": _cycle_ws("REACH", "WS:OUT-B"),
        "workstreams/WS-OUT-B.md": _cycle_ws("OUT-B", "WS:OUT-C"),
        "workstreams/WS-OUT-C.md": _cycle_ws("OUT-C", "WS:OUT-B"),
        "handoffs/REACH-2026-10-12.md": handoff,
        "handoffs/GARBAGE-2026-10-12.md": "---\nthis: no\n---\n\nSee above.\n",
    })
    named = root / "workstreams" / "WS-REACH.md"
    args = argparse.Namespace(
        root=str(root),
        quiet=False,
        strict=False,
        snapshot=None,
        paths=[str(named)],
    )
    assert module._paths_cover_handoff_joins(root, args.paths) is False
    result = module.cmd_validate(args)
    captured = capsys.readouterr()
    assert result == 1, captured.out + captured.err
    assert "WS-REACH.md: [workstream-cycle]" in captured.out
    assert "WS:OUT-B" in captured.out
    assert "WS:OUT-C" in captured.out
    assert "WS-OUT-B.md:" not in captured.out
    assert "WS-OUT-C.md:" not in captured.out
    assert "dangling-ref" not in captured.out
    assert "unparseable" not in captured.out
    assert "required-field" not in captured.out
    assert "1 records (1 workstreams, 0 decisions, 0 discoveries, 0 handoffs)" in captured.out


def test_d3_partial_paths_join_misnamed_workstream_by_content_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    """A workstream stem that is not WS-<key> still joins on the record's own key.

    WS-AAA.md carries key OUT-B and cycles with WS-OUT-C. The conventional
    WS-OUT-B.md also carries key OUT-B and does not cycle. load_store
    indexes the alphabetically first file, so the full store reports
    workstream-cycle plus filename-mismatch and duplicate-key. --paths
    naming the handoff and WS-REACH must report that cycle on WS-REACH,
    must not call load_store, and must not count the outside files or
    judge their schema findings.
    """
    module = _load_agentos_module()
    handoff = _plain_handoff().replace(
        "workstream: WS:DRAFT-ROUNDTRIP\n",
        "workstream: WS:REACH\n",
    )
    root = _write_tree(tmp_path, {
        "workstreams/WS-REACH.md": _cycle_ws("REACH", "WS:OUT-B"),
        "workstreams/WS-AAA.md": _cycle_ws("OUT-B", "WS:OUT-C"),
        "workstreams/WS-OUT-B.md": _D3_WS.replace("key: DRAFT-ROUNDTRIP\n", "key: OUT-B\n"),
        "workstreams/WS-OUT-C.md": _cycle_ws("OUT-C", "WS:OUT-B"),
        "handoffs/REACH-2026-10-12.md": handoff,
        "handoffs/GARBAGE-2026-10-12.md": "---\nthis: no\n---\n\nSee above.\n",
    })
    full = module.load_store(root, None)
    assert any(problem.rule == "workstream-cycle" for problem in full.problems)
    assert any(
        problem.rule == "filename-mismatch" and problem.path.name == "WS-AAA.md"
        for problem in full.problems
    )
    assert any(
        problem.rule == "duplicate-key" and problem.path.name == "WS-OUT-B.md"
        for problem in full.problems
    )
    _boom_on_full_store(module, monkeypatch)
    paths = [
        root / "handoffs" / "REACH-2026-10-12.md",
        root / "workstreams" / "WS-REACH.md",
    ]
    snap = _dump_json(tmp_path, "snap.json", {"prs": []})
    args = _strict_paths_args(root, paths, snap)
    assert module._paths_cover_handoff_joins(root, args.paths) is True
    result = module.cmd_validate(args)
    captured = capsys.readouterr()
    assert result == 1, captured.out + captured.err
    assert "WS-REACH.md: [workstream-cycle]" in captured.out
    assert "WS:OUT-B" in captured.out
    assert "WS:OUT-C" in captured.out
    assert "filename-mismatch" not in captured.out
    assert "duplicate-key" not in captured.out
    assert "dangling-ref" not in captured.out
    assert "unparseable" not in captured.out
    assert "2 records (1 workstreams, 0 decisions, 0 discoveries, 1 handoffs)" in captured.out


def test_d3_partial_paths_report_cycle_when_both_members_are_misnamed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    """A reached cycle still fails when neither member's stem is WS-<key>.

    WS-AAA.md is key OUT-B and WS-BBB.md is key OUT-C. No conventional
    WS-OUT-B.md or WS-OUT-C.md exists. The full store reports
    workstream-cycle on those files. --paths naming the handoff and
    WS-REACH must report that cycle on WS-REACH and must not call
    load_store. Filename findings stay off the named summary.
    """
    module = _load_agentos_module()
    handoff = _plain_handoff().replace(
        "workstream: WS:DRAFT-ROUNDTRIP\n",
        "workstream: WS:REACH\n",
    )
    root = _write_tree(tmp_path, {
        "workstreams/WS-REACH.md": _cycle_ws("REACH", "WS:OUT-B"),
        "workstreams/WS-AAA.md": _cycle_ws("OUT-B", "WS:OUT-C"),
        "workstreams/WS-BBB.md": _cycle_ws("OUT-C", "WS:OUT-B"),
        "handoffs/REACH-2026-10-12.md": handoff,
        "handoffs/GARBAGE-2026-10-12.md": "---\nthis: no\n---\n\nSee above.\n",
    })
    full = module.load_store(root, None)
    assert any(
        problem.rule == "workstream-cycle" and problem.path.name == "WS-AAA.md"
        for problem in full.problems
    )
    _boom_on_full_store(module, monkeypatch)
    paths = [
        root / "handoffs" / "REACH-2026-10-12.md",
        root / "workstreams" / "WS-REACH.md",
    ]
    snap = _dump_json(tmp_path, "snap.json", {"prs": []})
    args = _strict_paths_args(root, paths, snap)
    assert module._paths_cover_handoff_joins(root, args.paths) is True
    result = module.cmd_validate(args)
    captured = capsys.readouterr()
    assert result == 1, captured.out + captured.err
    assert "WS-REACH.md: [workstream-cycle]" in captured.out
    assert "WS:OUT-B" in captured.out
    assert "WS:OUT-C" in captured.out
    assert "dangling-ref" not in captured.out
    assert "filename-mismatch" not in captured.out
    assert "unparseable" not in captured.out
    assert "2 records (1 workstreams, 0 decisions, 0 discoveries, 1 handoffs)" in captured.out


def test_d3_no_network_or_gh_in_agentos() -> None:
    source = CLI.read_text(encoding="utf-8")
    assert source.count("subprocess.run") == 1
    for forbidden in ("subprocess.Popen", "os.system", "os.execv", "sys.exit(1)", "merge-base"):
        assert forbidden not in source, forbidden
    for line in source.splitlines():
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith("*"):
            continue
        assert '"gh"' not in stripped and "'gh'" not in stripped, line
    for banned in ("import requests", "import urllib", "import http.client", "import socket"):
        assert banned not in source



# Evaluation OS T12: typed findings are evidence, never a priority or grant.
def _evaluation_finding(**overrides):
    finding = {
        "engine": "engine/example.py::EXAMPLE",
        "metric": "hit_rate",
        "observed_change": {"baseline": None, "current": 0, "unit": "fraction"},
        "segment": "synthetic smoke fixture",
        "evidence_link": "research/evidence/example.json",
        "suggested_tier": "T1",
    }
    finding.update(overrides)
    return finding


def test_evaluation_finding_survives_existing_discovery_draft():
    module = _load_agentos_module()
    finding = _evaluation_finding()
    payload = _discovery_payload(evaluation_finding=finding)
    text = module.draft_discovery(payload)
    rec = module.yaml.safe_load(text.split("---", 2)[1])
    assert rec["evaluation_finding"] == finding
    assert rec["evaluation_finding"]["observed_change"]["current"] == 0
    assert rec["evaluation_finding"]["observed_change"]["baseline"] is None
    assert not [p for p in module.check_discovery(rec, Path("DSC-DRAFT-ROUNDTRIP-DISCOVERY.md")) if p.hard]


@pytest.mark.parametrize("finding", [
    None, [], {},
    _evaluation_finding(engine=""),
    _evaluation_finding(metric=3),
    _evaluation_finding(segment=""),
    _evaluation_finding(evidence_link=""),
    _evaluation_finding(suggested_tier="validated"),
    _evaluation_finding(observed_change=True),
    _evaluation_finding(observed_change={"current": float("nan"), "baseline": 0, "unit": "fraction"}),
    _evaluation_finding(observed_change={"current": 1, "baseline": 0}),
    _evaluation_finding(priority="high"),
])
def test_evaluation_finding_invalid_shape_refused_by_draft_and_store(finding):
    module = _load_agentos_module()
    payload = _discovery_payload(evaluation_finding=finding)
    with pytest.raises(SystemExit):
        module.draft_discovery(payload)
    problems = module.check_discovery(payload, Path("DSC-DRAFT-ROUNDTRIP-DISCOVERY.md"))
    assert any(p.hard and p.rule == "bad-evaluation-finding" for p in problems)


def test_evaluation_finding_unresolved_is_explicit_not_a_pass():
    module = _load_agentos_module()
    finding = _evaluation_finding(observed_change=None, suggested_tier=None)
    text = module.draft_discovery(_discovery_payload(evaluation_finding=finding))
    rec = module.yaml.safe_load(text.split("---", 2)[1])
    assert rec["evaluation_finding"] == finding
    assert not [p for p in module.check_discovery(rec, Path("DSC-DRAFT-ROUNDTRIP-DISCOVERY.md")) if p.hard]


def test_evaluation_finding_does_not_supply_discovery_admission():
    module = _load_agentos_module()
    for field in ("falsifier", "verified_by", "confidence", "scope"):
        payload = _discovery_payload(evaluation_finding=_evaluation_finding())
        payload.pop(field)
        with pytest.raises(SystemExit):
            module.draft_discovery(payload)


@pytest.mark.parametrize("tier", ["T1", None])
def test_evaluation_finding_actual_cli_roundtrip(tmp_path: Path, tier):
    finding = _evaluation_finding(suggested_tier=tier)
    payload = _discovery_payload(evaluation_finding=finding)
    src = _dump_json(tmp_path, "evaluation.json", payload)
    drafted = _agentos("draft-discovery", "--from", str(src))
    assert drafted.returncode == 0, drafted.stderr
    module = _load_agentos_module()
    rec = module.yaml.safe_load(drafted.stdout.split("---", 2)[1])
    assert rec["evaluation_finding"] == finding
    root = _write_tree(tmp_path, {"discoveries/DSC-DRAFT-ROUNDTRIP-DISCOVERY.md": drafted.stdout})
    validated = _agentos("validate", "--root", str(root))
    assert validated.returncode == 0, validated.stdout + validated.stderr
    assert "0 error(s)" in validated.stdout
    assert not (STORE / "discoveries/DSC-DRAFT-ROUNDTRIP-DISCOVERY.md").exists()


@pytest.mark.parametrize("finding", [
    _evaluation_finding(metric="é" * 1025),
    _evaluation_finding(observed_change={"baseline": False, "current": 0, "unit": "fraction"}),
    _evaluation_finding(observed_change={"baseline": 0, "current": float("inf"), "unit": "fraction"}),
    _evaluation_finding(observed_change={"baseline": 0, "current": {"dispatch": "now"}, "unit": "fraction"}),
])
def test_evaluation_finding_bounds_and_control_fields(finding):
    module = _load_agentos_module()
    payload = _discovery_payload(evaluation_finding=finding)
    with pytest.raises(SystemExit):
        module.draft_discovery(payload)
    assert any(p.hard and p.rule == "bad-evaluation-finding" for p in module.check_discovery(payload, Path("DSC-DRAFT-ROUNDTRIP-DISCOVERY.md")))


@pytest.mark.parametrize("field", ["engine", "metric", "segment", "evidence_link", "unit"])
def test_evaluation_finding_malformed_unicode_is_a_typed_refusal(field):
    module = _load_agentos_module()
    finding = _evaluation_finding()
    if field == "unit":
        finding["observed_change"]["unit"] = "\ud800"
    else:
        finding[field] = "\ud800"
    payload = _discovery_payload(evaluation_finding=finding)
    with pytest.raises(SystemExit):
        module.draft_discovery(payload)
    assert any(p.hard and p.rule == "bad-evaluation-finding" for p in module.check_discovery(payload, Path("DSC-DRAFT-ROUNDTRIP-DISCOVERY.md")))


def test_evaluation_finding_preserves_qualitative_snapshot_without_inventing_delta():
    module = _load_agentos_module()
    detail = "Snapshot metric-validity finding: all claims carry direction zero; hit is undefined."
    finding = _evaluation_finding(metric="hit_rate", observed_change=detail, suggested_tier="T0")
    drafted = module.draft_discovery(_discovery_payload(evaluation_finding=finding))
    rec = module.yaml.safe_load(drafted.split("---", 2)[1])
    assert rec["evaluation_finding"] == finding
    assert not [p for p in module.check_discovery(rec, Path("DSC-DRAFT-ROUNDTRIP-DISCOVERY.md")) if p.hard]


@pytest.mark.parametrize("observation", ["", "é" * 1025, "\ud800"])
def test_evaluation_finding_invalid_qualitative_observation_is_refused(observation):
    module = _load_agentos_module()
    payload = _discovery_payload(evaluation_finding=_evaluation_finding(observed_change=observation))
    with pytest.raises(SystemExit):
        module.draft_discovery(payload)
    assert any(p.hard and p.rule == "bad-evaluation-finding" for p in module.check_discovery(payload, Path("DSC-DRAFT-ROUNDTRIP-DISCOVERY.md")))
