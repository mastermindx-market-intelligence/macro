"""Which steps may cost a night of market data — bounded, named, and visible.

`daily.yml`'s `collect` job spends up to ~3 hours pulling the market data plane
(235 `data/stocks` names, `data/baskets/ohlcv`, the breadth close caches).  The
collected bytes live only on the runner, where the next job's `actions/checkout`
deletes them, so the ONLY thing that makes a night real is a commit that lands.

**Updated 2026-08-06 — first the checkpoint split, then the JOB split.**

    run collectors
      -> additive producers (Finviz, ZORI) + the two store tripwires
      -> "commit market data" + "push market data"      <-- the checkpoint
      -> salvage push (cancel path)
      -> the capital-structure handoff (stamp receipt, upload artifact)
      -> the two R2 store publishes

Before the checkpoint split there was ONE commit and it sat AFTER the
capital-structure chain.  Two earlier fixes had already narrowed the damage —
the commit gates on NAMED producers (`steps.collectors.outcome == 'success'`)
rather than job status, and the capital-structure paths were carved out of it
when the chain failed — so a capital-structure failure no longer DISCARDED the
collection outright.  What neither fix could remove is the WINDOW: ~3h of
collected bytes stayed unpublished for the whole length of the capital-structure
chain, one job-cap cancel, runner death, or host-disk fault away from being
deleted by the next checkout.  Six consecutive nights from 2026-08-01 went that
way, through four unrelated defects (#4534 duck-typing, runner ENOSPC, #4600
ledger identity, #4640 SEC grammar), and `data/stocks` froze at 2026-07-31.

**The chain then left this job entirely.**  Even below the checkpoint it was
still a fatal-by-design lane inside the job the whole nightly hangs off, and it
redded the nightly on three consecutive nights for three unrelated causes (#4600
08-04, #4640 08-05, #4740 08-06).  It now runs in the `capital_structure` job
(`needs: collect`), which nothing needs in turn.  That job's own law — the
all-or-nothing checkpoint, the fatal compilers, the narrow staging, the receipt
that proves it compiled TONIGHT's ledger — is pinned by
`tests/test_daily_capital_structure_job.py`.  This file keeps the market side.

**What this job still owes the capital-structure lane** is the carve-out and the
handoff, and they are two halves of one contract.  `run collectors`
(`sec_capital_structure`) rewrites the TRACKED `source_manifest.jsonl` long
before any compiler validates it, so the market checkpoint UNSTAGES those paths
— and must never `git checkout` them, because that freshly collected ledger is
the compilers' INPUT.  Unstaged means uncommitted, which means the ledger cannot
reach the next job through git at all: it goes as an artifact, with a
sha256/row-count receipt published as a job output.  Both handoff steps are
`continue-on-error`, because the entire point of the split is that no
capital-structure concern may red THIS job; a failed handoff fails closed one job
over instead.

So `DELIBERATE_VETO_STEPS` below is now EMPTY, which is the whole point: every
step that used to be on it left the job.  The allowlist stays because it is the
thing that keeps a future re-coupling deliberate — a new unguarded step between
the collectors and the market commit is almost always an oversight (the house
idiom is `|| echo "::warning::..."` or `continue-on-error: true`), and adding one
to the list is the act that writes the cost down for the next reader.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.workflow_run_source import resolve_run_source  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DAILY = ROOT / ".github/workflows/daily.yml"

MARKET_COMMIT_STEP = "commit market data"
MARKET_PUSH_STEP = "push market data"
COLLECTORS_STEP = "run collectors"
HANDOFF_STAMP_STEP = "stamp the capital-structure handoff receipt"
HANDOFF_UPLOAD_STEP = "hand the capital-structure workspace to its own job"
# Carve-custody steps (PR #9556 review 5566188238). Absent on a52f5ad8 — tests
# that look these up must use _index_of_absent so the RED phase can still run.
QLEDGER_PARK_STEP = "park carved qledger bytes outside the push autostash"
QLEDGER_RESTORE_STEP = "restore carved qledger bytes (runner-local, never published here)"
SALVAGE_PUSH_STEP = "salvage push"

# Steps that MAY fail the collect job before "commit market data", and why.  Every
# entry costs the night's market collection when it fires — that would be an
# accepted price, not an accident.  Keyed by a distinctive fragment of the step's
# `run:`.
#
# EMPTY since the 2026-08-06 two-checkpoint split.  It used to hold all five
# capital-structure steps; they now run AFTER the market checkpoint and answer to
# their own commit, so nothing between the collectors and the market commit may
# fail the job at all.  Keep the mechanism: an entry added here is a deliberate,
# reviewed decision to put a night of collection behind one more step.
DELIBERATE_VETO_STEPS: dict[str, str] = {}

# The chain that must stay OUT of this job entirely. Keyed by the `python -m`
# module each step runs, valued by what it would cost if it came back.
CAPITAL_STRUCTURE_STEPS = {
    "scripts.materialize_capital_structure_share_counts":
        "share-count publication (pre-production, var-gated off)",
    "scripts.retain_capital_structure_share_counts":
        "retention lane (pre-production, double var-gated off)",
    "scripts.compile_capital_structure_events":
        "event spine — fail-closed by design (#4600 ManifestIdentityError, 08-05)",
    "scripts.compile_capital_structure_document_terms":
        "term ledger — must not commit a partial ledger (#4640 SEC grammar)",
    "scripts.build_capital_structure_projection":
        "projection — canonical/public twin must stay byte-identical",
}


@pytest.fixture(scope="module")
def collect_steps() -> list[dict]:
    doc = yaml.safe_load(DAILY.read_text())
    steps = doc["jobs"]["collect"]["steps"]
    assert steps, "collect job has no steps — workflow shape changed"
    return steps


def _index_of(steps: list[dict], needle: str) -> int:
    for i, step in enumerate(steps):
        if needle in (step.get("name") or ""):
            return i
    raise AssertionError(f"no step whose name contains {needle!r}")


def _index_of_absent(steps: list[dict], needle: str) -> int | None:
    """Same as `_index_of` but returns None when the step is absent instead of
    raising. Used by the carve-custody tests so they can run on a52f5ad8 (RED
    baseline) where the park/restore steps do not yet exist."""
    for i, step in enumerate(steps):
        if needle in (step.get("name") or ""):
            return i
    return None


def _index_of_run(steps: list[dict], fragment: str) -> int:
    for i, step in enumerate(steps):
        if fragment in str(step.get("run") or ""):
            return i
    raise AssertionError(f"no step whose `run:` contains {fragment!r}")


def _is_non_fatal(step: dict) -> bool:
    """True when this step cannot fail the job."""
    if step.get("continue-on-error") is True:
        return True
    run = step.get("run") or ""
    if not run:
        return True  # `uses:` action steps are not the veto class this guards
    # Join backslash continuations FIRST: the house idiom puts the `|| echo` guard
    # on the continuation line ("python foo.py \\\n  || echo ..."), so a physical
    # line scan reads a guarded command as bare.
    run = re.sub(r"\\\n\s*", " ", run)
    body = [ln.strip() for ln in run.splitlines()]
    body = [ln for ln in body if ln and not ln.startswith("#")]
    if not body:
        return True
    return all("||" in ln or ln.endswith(("then", "else", "fi", "do", "done", "esac", "{", "}"))
               or ln.startswith(("if ", "for ", "while ", "case ", "elif "))
               for ln in body)


def _veto_reason(step: dict) -> str | None:
    run = str(step.get("run") or "")
    for fragment, reason in DELIBERATE_VETO_STEPS.items():
        if fragment in run:
            return reason
    return None


# --------------------------------------------------------------------------
# THE SPLIT ITSELF: no capital-structure step runs in this job at all.
# --------------------------------------------------------------------------


@pytest.mark.parametrize("module,cost", sorted(CAPITAL_STRUCTURE_STEPS.items()))
def test_no_capital_structure_step_runs_in_the_collect_job(collect_steps, module, cost):
    """The 2026-08-06 job split, stated from the market side.

    The earlier checkpoint split already stopped these steps from DELAYING or
    DISCARDING the night's market data. It could not stop them from redding the
    job the whole nightly hangs off, which they did on three consecutive nights
    (#4600 08-04, #4640 08-05, #4740 08-06). Moving one back here re-couples an
    all-or-nothing SEC publication protocol — whose compilers are deliberately
    fatal and may never be given continue-on-error — to every `needs: collect`
    job in the workflow.
    """
    present = [
        i for i, s in enumerate(collect_steps) if module in str(s.get("run") or "")
    ]
    assert not present, (
        f"{module} ({cost}) is back in the collect job at step(s) {present}. It "
        "belongs to the `capital_structure` job (needs: collect), which nothing "
        "needs in turn — see tests/test_daily_capital_structure_job.py."
    )


def test_the_market_checkpoint_is_ordered_and_distinctly_named(collect_steps):
    """commit market data -> push market data, and never the bare old name.

    The naming matters as much as the order. `test_capital_structure_compiler.py`
    locates both checkpoints by name; a step called "commit data ..." would
    satisfy that pin's pre-split letter while the market plane silently rode a
    capital-structure-vetoed checkpoint again.
    """
    market_commit = _index_of(collect_steps, MARKET_COMMIT_STEP)
    market_push = _index_of(collect_steps, MARKET_PUSH_STEP)
    assert market_commit < market_push

    names = [str(s.get("name") or "") for s in collect_steps]
    bare = [n for n in names if n.startswith("commit data")]
    assert not bare, (
        f"a collect step is named {bare!r} again. The market checkpoint is "
        "'commit market data'; the capital-structure one is 'commit "
        "capital-structure data' and lives in another job."
    )


def test_the_capital_structure_handoff_can_never_cost_the_night(collect_steps):
    """The handoff pays for the split; it must not be able to charge this job.

    The ledger the `capital_structure` job compiles is deliberately NOT committed
    here (see the carve-out test below), so it crosses as an artifact. That is a
    capital-structure concern living in the collect job — exactly the shape the
    split removed — and it is only safe because neither step can fail the job.
    A failed stamp or upload must fail CLOSED one job over, in that job's handoff
    verification, never here.
    """
    for step_name in (HANDOFF_STAMP_STEP, HANDOFF_UPLOAD_STEP):
        step = collect_steps[_index_of(collect_steps, step_name)]
        assert step.get("continue-on-error") is True, (
            f"{step_name!r} is not continue-on-error, so a capital-structure "
            "handoff failure reds the collect job and every `needs: collect` job "
            "pays for it — the defect the split exists to remove."
        )

    # And it must sit after the checkpoint, for the same reason everything else does.
    push = _index_of(collect_steps, MARKET_PUSH_STEP)
    assert _index_of(collect_steps, HANDOFF_STAMP_STEP) > push, (
        "the handoff receipt is stamped before the market push. It must be stamped "
        "AFTER: that push rebases with --autostash, and a conflicted re-apply "
        "resets hard to origin/main's committed ledger (#4600's self-heal). The "
        "receipt has to describe whatever actually survived."
    )


def test_only_allowlisted_steps_may_cost_the_nights_collection(collect_steps):
    """A NEW unguarded step between the collectors and the market commit.

    Such a step reds the job, which SKIPS the commit gate's siblings and delays
    the checkpoint — the exact shape the split was made to remove. Since
    2026-08-06 the allowlist is empty and should stay that way; a step that
    genuinely must block the market checkpoint belongs in DELIBERATE_VETO_STEPS,
    where the cost is written down.
    """
    start = _index_of(collect_steps, COLLECTORS_STEP)
    end = _index_of(collect_steps, MARKET_COMMIT_STEP)
    assert start < end, "collectors must run before the market checkpoint"

    offenders = [
        (i, collect_steps[i].get("name"))
        for i in range(start + 1, end)
        if not _is_non_fatal(collect_steps[i]) and _veto_reason(collect_steps[i]) is None
    ]
    assert not offenders, (
        "these steps sit between the collectors and 'commit market data' and can "
        "fail the job, which skips the commit and leaves ~3h of collection on the "
        f"runner: {offenders}. Guard each with `continue-on-error: true` or the "
        'house `|| echo "::warning::..."` idiom — or, if it truly must block the '
        "checkpoint, add it to DELIBERATE_VETO_STEPS with the reason."
    )


def test_the_veto_allowlist_is_not_stale(collect_steps):
    """Every allowlisted veto must still exist, so the list cannot rot into fiction."""
    runs = " \n".join(str(s.get("run") or "") for s in collect_steps)
    missing = [frag for frag in DELIBERATE_VETO_STEPS if frag not in runs]
    assert not missing, (
        f"DELIBERATE_VETO_STEPS names steps the collect job no longer runs: {missing}. "
        "Drop them — a stale allowlist silently licenses a future step that reuses "
        "the name."
    )


def test_collectors_step_contract_is_stated_in_its_own_name(collect_steps):
    """08-02/08-03 shape: the collectors step exited 1 and took the commit with it.

    `scripts.collect` degrades per source and exits non-zero only if EVERY source
    failed, but an exception escaping its runner machinery still killed the pass
    (#4560 added the `_run_one` net). This pins the stated contract so a rename
    cannot quietly drop it.
    """
    step = collect_steps[_index_of(collect_steps, COLLECTORS_STEP)]
    assert "never fails the build on one source" in (step.get("name") or ""), (
        "the collectors step's own name states the contract; if it was renamed, "
        "re-read whether the guarantee still holds"
    )


@pytest.mark.parametrize(
    "commit_step,push_step", [(MARKET_COMMIT_STEP, MARKET_PUSH_STEP)]
)
def test_each_checkpoint_keeps_the_commit_push_split(collect_steps, commit_step, push_step):
    """The local commit is its own step; the network publish is a separate one.

    2026-07-17 postmortem (run 29542087837): a hung `git push` ate 57m and the
    150m job cap killed the step mid-publish, so an already-collected night
    existed only on the runner. The capital-structure checkpoint carries the same
    shape one job over, pinned by tests/test_daily_capital_structure_job.py.
    """
    commit_at = _index_of(collect_steps, commit_step)
    push_at = _index_of(collect_steps, push_step)
    assert commit_at < push_at, f"{commit_step!r} must precede {push_step!r}"

    commit = collect_steps[commit_at]
    push = collect_steps[push_at]
    commit_run = str(commit.get("run") or "")
    push_run = str(push.get("run") or "")

    assert "git commit -m" in commit_run, f"{commit_step!r} no longer commits"
    assert "git push" not in commit_run and "push_do" not in commit_run, (
        f"{commit_step!r} performs the network push itself — merging the two back "
        "together is the 2026-07-17 defect. Keep the publish in its own step."
    )
    assert "git commit" not in push_run, (
        f"{push_step!r} commits as well as pushes; the commit must already be "
        "atomic before any network op runs"
    )
    assert "scripts/ci/push_retry.sh" in push_run, (
        f"{push_step!r} no longer sources the shared retry policy — it loses the "
        "contention/conflict split and the jittered backoff (render run 30167139398)"
    )
    assert "perl -e 'alarm" in push_run, (
        f"{push_step!r} has an unbounded git network op. macOS runners have no GNU "
        "timeout; a hung fetch/pull can only be killed by the perl alarm."
    )

    cond = str(push.get("if") or "")
    assert "always()" in cond, (
        f"{push_step!r} has `if: {cond or '<none>'}`, which carries no status "
        "function, so GitHub ANDs an implicit success() onto it and an earlier red "
        "skips the publish of an already-made commit"
    )
    commit_id = commit.get("id")
    assert commit_id and f"steps.{commit_id}.outputs.committed == 'true'" in cond, (
        f"{push_step!r} must be gated on {commit_step!r}'s own `committed` output "
        f"(id={commit_id!r}); if: {cond}"
    )


def test_salvage_push_covers_the_market_commit(collect_steps):
    """The cancel-path last-ditch publish belongs to the expensive checkpoint.

    It runs `if: cancelled()`, so it must sit where a cancel during the market
    push can still reach it — immediately after that push, not behind slower work
    later in the job.
    """
    market_push = _index_of(collect_steps, MARKET_PUSH_STEP)
    salvage = _index_of(collect_steps, "salvage push")
    assert salvage == market_push + 1, (
        "the salvage push must follow the market push DIRECTLY (2026-07-17 / "
        f"2026-07-16 postmortems); it is at {salvage}, the push at {market_push}"
    )
    cond = str(collect_steps[salvage].get("if") or "")
    assert "cancelled()" in cond and "steps.commitdata.outputs.committed" in cond, (
        f"the salvage push lost its cancel/commit gate; if: {cond}"
    )


# --------------------------------------------------------------------------
# Checkpoint 1: the market commit's gate — NAMED PRODUCERS, never job status.
# --------------------------------------------------------------------------
#
# "commit data" used to carry no `if:` at all, so it inherited an implicit
# success() and any earlier red discarded the night (08-02..08-05, four nights,
# three unrelated causes).  A bare `always()` is the other failure mode and is
# worse: on 2026-08-04 an always() commit step outran its SKIPPED normalizers
# and committed raw un-normalized pages sitewide.
#
# The lawful shape is a gate on the NAMED steps that PRODUCE what the commit
# stages, compared with `.outcome == 'success'` so a SKIPPED producer blocks
# exactly like a failed one.  These tests pin that shape from both sides: every
# producer must be in the gate, and nothing else may be.

# Staged path prefix -> (step id that produces it, must_gate).
#
# The capital-structure paths are NOT here any more: since 2026-08-06 they are
# staged by checkpoint 2, and this commit only unstages them (see the carve-out
# test below).
MARKET_STAGED_PATH_PRODUCERS = {
    "data/": [("collectors", True)],
    "site/qledger/": [("collectors", True)],
}

# The capital-structure checkpoint's own staging + gate moved with the chain;
# tests/test_daily_capital_structure_job.py owns them now.
CAPITAL_STRUCTURE_CHAIN = ("cs_spine", "cs_terms", "cs_projection")


def _gating(producers: dict) -> list[str]:
    return sorted({
        step_id
        for entries in producers.values()
        for step_id, must_gate in entries
        if must_gate
    })


MARKET_GATING_PRODUCERS = _gating(MARKET_STAGED_PATH_PRODUCERS)

CHECKPOINTS = {
    MARKET_COMMIT_STEP: (MARKET_STAGED_PATH_PRODUCERS, MARKET_GATING_PRODUCERS),
}


def _gate_refs(cond: str) -> set[str]:
    """Every `steps.<id>.<field>` referenced by an `if:` expression."""
    return set(re.findall(r"steps\.([A-Za-z0-9_-]+)\.", cond))


@pytest.mark.parametrize("commit_step", sorted(CHECKPOINTS))
def test_every_staged_path_has_a_declared_producer(collect_steps, commit_step):
    """Anti-rot: a new `git add` path must be mapped before it can ship.

    This is what keeps the gates honest. Without it, someone stages a new tree,
    forgets to name its producer, and a checkpoint silently commits a path nobody
    is gating — the original defect wearing a new path.
    """
    producers, _ = CHECKPOINTS[commit_step]
    run = collect_steps[_index_of(collect_steps, commit_step)]["run"]
    add_lines = [ln.strip() for ln in run.splitlines() if ln.strip().startswith("git add ")]
    assert add_lines, f"{commit_step!r} no longer contains a `git add` — the mapping is fiction"

    staged = {p for line in add_lines for p in line.split()[2:] if not p.startswith("-")}
    undeclared = staged - set(producers)
    assert not undeclared, (
        f"{commit_step!r} stages {sorted(undeclared)}, which its producer map does "
        "not cover. Add the mapping (and gate on the producer if a partial write "
        "there would corrupt the tree) before staging a new path."
    )
    unstaged = set(producers) - staged
    assert not unstaged, (
        f"the producer map claims {commit_step!r} stages {sorted(unstaged)}, which "
        "it no longer does — a stale mapping licenses a gate that guards nothing."
    )


@pytest.mark.parametrize("commit_step", sorted(CHECKPOINTS))
def test_commit_gate_names_exactly_the_producers_of_its_staged_paths(
    collect_steps, commit_step
):
    """Bidirectional: every gating producer present, and nothing else.

    (a) a missing producer means a partial tree can be checkpointed;
    (b) an extra name means an unrelated subsystem can veto this checkpoint,
        which is precisely what cost 08-02..08-05 on the market side.
    """
    _, gating = CHECKPOINTS[commit_step]
    cond = str(collect_steps[_index_of(collect_steps, commit_step)].get("if") or "")
    assert cond, (
        f"{commit_step!r} has no `if:` — it inherits success() and ANY earlier red "
        "in the ~3h job skips it"
    )

    refs = _gate_refs(cond)
    missing = set(gating) - refs
    assert not missing, (
        f"{commit_step!r} does not gate on {sorted(missing)}, which produce the tree "
        f"it stages. A partial or skipped run of those would be checkpointed. if: {cond}"
    )
    extra = refs - set(gating)
    assert not extra, (
        f"{commit_step!r} gates on {sorted(extra)}, which do not PRODUCE its staged "
        f"tree. A consumer, audit, or tripwire in this gate can discard real work "
        f"over an unrelated failure. if: {cond}"
    )


@pytest.mark.parametrize("step_id", sorted(MARKET_GATING_PRODUCERS))
def test_gated_producer_ids_actually_exist(collect_steps, step_id):
    """A gate naming a step that does not exist can never be satisfied."""
    ids = {s.get("id") for s in collect_steps if s.get("id")}
    assert step_id in ids, (
        f"a commit gate names step id {step_id!r}, which no collect step declares — "
        "the expression would evaluate to '' and the commit could never run"
    )


@pytest.mark.parametrize("commit_step", sorted(CHECKPOINTS))
def test_commit_gate_blocks_a_skipped_producer_exactly_like_a_failed_one(
    collect_steps, commit_step
):
    """The 2026-08-04 P0's actual lesson.

    An always() commit outran its SKIPPED normalizers and committed raw pages
    sitewide. `.outcome == 'success'` is the only comparison that blocks on
    'skipped'; `!= 'failure'` lets a skipped producer through, and `.conclusion`
    is laundered to 'success' by a continue-on-error — which matters most on the
    capital-structure checkpoint, whose whole contract is that its compile steps
    stay fatal (a future `continue-on-error:` there must not buy a commit).
    """
    _, gating = CHECKPOINTS[commit_step]
    cond = str(collect_steps[_index_of(collect_steps, commit_step)].get("if") or "")

    for step_id in gating:
        assert f"steps.{step_id}.outcome == 'success'" in cond, (
            f"{commit_step!r}'s gate on {step_id!r} must be exactly "
            f"`steps.{step_id}.outcome == 'success'`. A `!= 'failure'` test lets a "
            "SKIPPED producer through, and `.conclusion` is laundered by "
            f"continue-on-error. if: {cond}"
        )
    assert ".conclusion" not in cond, (
        f"{commit_step!r}'s gate uses `.conclusion`, which a continue-on-error "
        f"rewrites to 'success' — it cannot see the failure it must block. if: {cond}"
    )


@pytest.mark.parametrize("commit_step", sorted(CHECKPOINTS))
def test_commit_gate_is_explicit_never_bare_always_or_implicit_success(
    collect_steps, commit_step
):
    """It must survive an unrelated red, and must not be a blank cheque."""
    cond = str(collect_steps[_index_of(collect_steps, commit_step)].get("if") or "").strip()

    assert "always()" in cond, (
        f"without a status function {commit_step!r} inherits an implicit success() "
        f"and any earlier red in the ~3h job skips it. if: {cond!r}"
    )
    assert cond != "always()" and _gate_refs(cond), (
        f"`if: always()` alone is a bare always() — the 2026-08-04 P0 shape, where "
        "the commit outran its skipped producers. Name the producing steps."
    )
    assert "success()" not in cond, (
        "success() is job-wide status, not a named producer: it re-couples the commit "
        f"to every unrelated step in the job. if: {cond!r}"
    )


def test_market_commit_unstages_capital_structure_unconditionally(collect_steps):
    """Checkpoint 1 must drop the capital-structure paths — always, and by UNSTAGE.

    Two failure modes, opposite directions:

      * it stages them anyway. `run collectors` has already rewritten the tracked
        source_manifest.jsonl, and no compiler has accepted it yet, so the market
        commit would publish a source ledger that may be about to be REJECTED —
        and #4600's self-heal (each night restores a clean ledger from git) dies
        with it, because the drift becomes permanent.
      * it `git checkout`s them. The pre-split carve-out did exactly that, and it
        was right THEN: it fired after a FAILED chain, restoring the clean
        committed ledger. Here the chain has not run and that ledger is its
        INPUT, so a checkout would feed the spine yesterday's manifests every
        single night — a silently frozen lane that still goes green.
    """
    step = collect_steps[_index_of(collect_steps, MARKET_COMMIT_STEP)]
    run = str(step["run"])
    body = [ln.strip() for ln in run.splitlines() if not ln.strip().startswith("#")]

    reset_lines = [
        ln for ln in body
        if ln.startswith("git reset") and "data/capital_structure" in ln
    ]
    assert reset_lines, (
        "'commit market data' no longer unstages data/capital_structure, so the "
        "broad `git add data/` above it commits an unvalidated source ledger."
    )
    assert any("site/capital-structure-data" in ln for ln in reset_lines), (
        "the carve-out unstages data/capital_structure but leaves the public twin "
        "site/capital-structure-data/ staged — the two must move together or the "
        "'byte-identical twin' law breaks"
    )
    assert not any(
        ln.startswith("git checkout") and "capital_structure" in ln for ln in body
    ), (
        "'commit market data' reverts the capital-structure paths with `git "
        "checkout`. That discards the ledger the collectors just fetched, which is "
        "the INPUT to the compile chain below — the lane would recompile yesterday "
        "forever while every step stayed green."
    )

    # Unconditional: no `if [ ... ]` may guard the reset. Before the split the
    # carve-out was conditional on the chain's outcomes; those outcomes are now
    # the empty string here, so a surviving condition would be a silent no-op.
    idx = body.index(reset_lines[0])
    assert not any(ln.startswith(("if ", "elif ")) for ln in body[:idx]), (
        "the capital-structure unstage sits inside a conditional. At this point in "
        "the job no capital-structure step has run, so any `steps.cs_*.outcome` "
        "test evaluates to '' and the carve-out silently stops firing."
    )
    for var in CAPITAL_STRUCTURE_CHAIN:
        assert var not in str(step.get("env") or {}), (
            f"'commit market data' still reads {var} into its env; that outcome is "
            "always empty here because the step has not run yet"
        )


# The capital-structure checkpoint's narrow staging, its fatal compilers, and the
# placement of the rejected-ledger capture moved with the chain into
# tests/test_daily_capital_structure_job.py. They are the same laws, asserted
# against the job that now runs them.


# --------------------------------------------------------------------------
# The R2 publishes are NOT part of either checkpoint's gate.
# --------------------------------------------------------------------------
# The allowlist above bounds which steps may cost the night's GIT commit.
# The R2 store publishes sit after both commits and answer to a different law:
# they carry the day's upserted increments back to an R2-CANONICAL store, and
# the engine job's `audit_r2 --strict` anchor goes red within 26h if they do
# not run.  They were nevertheless collateral damage of every veto, because a
# step `if:` that names no status function inherits an implicit success().
#
# Run 30960328285 is the cost: the massive_stock_day publish had been in the
# workflow for three nights and had never once executed.  These tests pin the
# decoupling so a future edit cannot silently re-attach them to the veto.

R2_PUBLISH_STEPS = {
    "publish attention store back to R2": "steps.attention_restore.outcome",
    "publish massive_stock_day store back to R2": "steps.massive_restore.outcome",
}

_STATUS_FUNCS = ("always(", "failure(", "cancelled(", "!cancelled(")


@pytest.mark.parametrize("step_name,restore_gate", sorted(R2_PUBLISH_STEPS.items()))
def test_r2_publish_survives_a_veto_but_keeps_its_restore_gate(
    collect_steps, step_name, restore_gate
):
    """Each R2 publish must run after an earlier red AND stay restore-gated.

    Two failure modes, opposite directions:
      * no status function -> implicit success() -> skipped by any earlier red,
        which is how the store froze (nothing published 2026-07-30 -> 08-05);
      * no restore gate -> a failed/partial restore leaves a shallow tree that
        would overwrite the deep store on R2. The gate is the fence; keep both.
    """
    step = collect_steps[_index_of(collect_steps, step_name)]
    cond = str(step.get("if") or "")

    assert cond, f"{step_name!r} lost its `if:` entirely — the restore fence is gone"
    assert any(fn in cond for fn in _STATUS_FUNCS), (
        f"{step_name!r} has `if: {cond}`, which contains no status-check function, so "
        "GitHub ANDs an implicit success() onto it and ANY earlier failure in the ~3h "
        "collect job skips the publish. The R2 store then goes stale and the engine "
        "job's audit_r2 anchor reds within 26h. Use `always() && <restore gate>`."
    )
    assert restore_gate in cond, (
        f"{step_name!r} dropped its restore gate ({restore_gate}). Without it a failed "
        "or partial R2 restore leaves a shallow local tree that this step would publish "
        "OVER the deep canonical store."
    )


@pytest.mark.parametrize("step_name", sorted(R2_PUBLISH_STEPS))
def test_r2_publish_runs_after_the_market_checkpoint(collect_steps, step_name):
    """Publishing must never delay the local commit (2026-07-17 postmortem)."""
    at = _index_of(collect_steps, step_name)
    assert _index_of(collect_steps, MARKET_COMMIT_STEP) < at, (
        f"{step_name!r} moved ahead of {MARKET_COMMIT_STEP!r}; a slow upload would "
        "then sit between the collection and the checkpoint that preserves it"
    )
    assert _index_of(collect_steps, HANDOFF_UPLOAD_STEP) < at, (
        f"{step_name!r} moved ahead of the capital-structure handoff. The handoff "
        "is what lets the isolated job compile tonight's ledger at all; a slow or "
        "hung R2 upload must not sit in front of it and burn the job's budget."
    )


def test_store_tripwire_still_fires_on_a_lost_night(collect_steps):
    """The massive_store content audit must run even when the night is discarded.

    `continue-on-error: true` stops this step from FAILING the job; it does not
    stop an earlier failure from SKIPPING it. Through 08-02..08-05 the tripwire
    was dark on exactly the nights that needed it, and the freeze surfaced six
    days later as the engine job's R2 staleness anchor instead.
    """
    step = collect_steps[_index_of(collect_steps, "audit massive_stock_day store")]
    cond = str(step.get("if") or "")

    assert any(fn in cond for fn in _STATUS_FUNCS), (
        "the massive_store tripwire has `if: "
        f"{cond or '<none>'}`, so an earlier red in the collect job skips it and the "
        "store's freshness alarm goes dark on precisely the nights it matters."
    )
    assert step.get("continue-on-error") is True, (
        "the tripwire now runs under always(); without continue-on-error a content "
        "fail would red the collect job it was designed never to block."
    )


@pytest.mark.parametrize("step_name", sorted(R2_PUBLISH_STEPS))
def test_r2_publish_is_itself_non_fatal(collect_steps, step_name):
    """A failed upload must not red the collect job — the anchor alarm carries it."""
    step = collect_steps[_index_of(collect_steps, step_name)]
    assert _is_non_fatal(step), (
        f"{step_name!r} can now fail the collect job. It runs under always(), so a "
        "publish failure would red an otherwise-successful night. Keep the house "
        '`|| echo "::warning::..."` guard.'
    )


# ── GH001 qledger-oversize carve-out (2026-10-16/17 stall) ───────────────────
# GitHub rejects ANY commit whose tree contains a blob > 100 MiB (GH001,
# 104857600 bytes). data/qledger/claims.jsonl is an append-only monolith that
# crossed that limit on 2026-10-15 and stayed over it the next two nights, so
# `collect`'s market commit ("data: daily collection") was rejected WHOLE and
# data/baskets/ohlcv, data/stocks, breadth and macro stores stopped publishing
# (runs 38830626430 / job 116748357565 on 10-16; 38987623960 / job 117262684428
# on 10-17, "GH001 large-file rejection; automatic retry stopped"). The fix
# is to UNSTAGE every staged qledger blob whose size is within 1 MiB of the
# limit and let the market plane ship without the ledger — the ledger's
# shrinkage is owned by the qledger publication program, not by `collect`.
# These tests pin the carve-out so a future regression in daily.yml cannot
# silently re-sink the market plane.

import os  # noqa: E402


def _run_market_commit(tmp_path, collect_steps, mutate, seed=None):
    """Materialize a fresh git repo, mutate it, and run the verbatim `run:` body
    of the market-commit step. Returns (subprocess.CompletedProcess, parsed
    GITHUB_OUTPUT dict, Path to repo).

    `seed`, when given, is called as `seed(repo)` after the base files are
    written and before the base commit. Whatever it writes must land in the
    base commit. If a `seed` writes `.gitattributes` the helper adds it to the
    base commit alongside `data`/`site`; seed may also stage its own files
    using the helper's `env` (passed as the second positional arg)."""
    run = str(collect_steps[_index_of(collect_steps, MARKET_COMMIT_STEP)]["run"])
    assert "${{" not in run, (
        "test harness must run the step body verbatim — if daily.yml grew a "
        "${{ ... }} interpolation, render it through the GitHub env first or "
        "rewrite the test runner; do NOT silently swallow the substitution."
    )
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    env = {
        **os.environ,
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GITHUB_OUTPUT": str(tmp_path / "gh_output"),
    }
    for k, v in {
        "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
        "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
    }.items():
        env.setdefault(k, v)
    subprocess.run(["git", "config", "user.name", "t"], cwd=repo, env=env, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=repo, env=env, check=True)
    # Base files: every plane the step is responsible for, frozen at a known state.
    (repo / "data" / "baskets" / "ohlcv").mkdir(parents=True)
    (repo / "data" / "qledger").mkdir(parents=True)
    (repo / "site" / "qledger").mkdir(parents=True)
    (repo / "data" / "capital_structure").mkdir(parents=True)
    (repo / "data" / "hk").mkdir(parents=True)
    (repo / "data" / "baskets" / "ohlcv" / "NVDA.parquet").write_bytes(b"v1")
    (repo / "data" / "qledger" / "claims.jsonl").write_bytes(b'{"claim_id":"c0"}\n')
    (repo / "site" / "qledger" / "track_record.json").write_bytes(b"{}")
    (repo / "data" / "capital_structure" / "source_manifest.jsonl").write_bytes(b"m1\n")
    (repo / "data" / "hk" / "x.csv").write_bytes(b"h1\n")
    subprocess.run(["git", "add", "data", "site"], cwd=repo, env=env, check=True)
    if seed is not None:
        seed(repo, env)
        # Stage `.gitattributes` alongside `data`/`site` so the seeded file
        # lands in the base commit. `git add` on an already-staged file is a
        # no-op, so seeds that staged their own files still work.
        if (repo / ".gitattributes").exists():
            subprocess.run(["git", "add", ".gitattributes"], cwd=repo, env=env, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "base"], cwd=repo, env=env, check=True)
    mutate(repo)
    proc = subprocess.run(
        ["bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", run],
        cwd=repo, env=env, capture_output=True, text=True, timeout=300,
    )
    out_path = tmp_path / "gh_output"
    outputs = {}
    if out_path.exists():
        for line in out_path.read_text().splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                outputs[k] = v  # last write wins, matching GITHUB_OUTPUT semantics
    return proc, outputs, repo


def _grow(path, size):
    """Make `path` exactly `size` bytes — sparse so no real MB of zeros lands
    on disk. Appends one valid claim line first so the file is well-formed JSONL
    up to the first byte of the sparse hole."""
    with open(path, "r+b") as f:
        f.seek(0, 2)
        f.write(b'{"claim_id":"c1"}\n')
        f.truncate(size)


_LIMIT = 104857600
_MARGIN = 1048576


def test_qledger_carve_oversized_ledger_no_longer_sinks_the_market_commit(tmp_path, collect_steps):
    """The exact GH001 reproduction: a single 100 MiB+ ledger blob used to drop
    the WHOLE market commit. With the carve-out, market data publishes and the
    ledger is left for the qledger publication program."""

    def mutate(repo):
        (repo / "data" / "baskets" / "ohlcv" / "NVDA.parquet").write_bytes(b"v2")
        _grow(repo / "data" / "qledger" / "claims.jsonl", _LIMIT + 4096)
        (repo / "site" / "qledger" / "track_record.json").write_bytes(b'{"n":1}')
        (repo / "data" / "capital_structure" / "source_manifest.jsonl").write_bytes(b"m2\n")
        (repo / "data" / "hk" / "x.csv").write_bytes(b"h2\n")

    proc, outputs, repo = _run_market_commit(tmp_path, collect_steps, mutate)
    assert proc.returncode == 0, f"step failed: stdout={proc.stdout!r} stderr={proc.stderr!r}"
    subject = subprocess.run(
        ["git", "log", "-1", "--format=%s"], cwd=repo,
        env={**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"},
        capture_output=True, text=True, check=True,
    ).stdout
    assert subject.startswith("data: daily collection"), subject
    # Market plane landed (the whole reason the carve-out exists).
    blob = subprocess.run(
        ["git", "show", "HEAD:data/baskets/ohlcv/NVDA.parquet"], cwd=repo,
        env={**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"},
        capture_output=True, check=True,
    ).stdout
    assert blob == b"v2"
    # The exact GH001 invariant: no blob in HEAD may exceed the hard limit. THIS
    # is what 116748357565 / 117262684428 lost — and the only thing the carve-out
    # has to guarantee going forward.
    ls = subprocess.run(
        ["git", "ls-tree", "-r", "-l", "HEAD"], cwd=repo,
        env={**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"},
        capture_output=True, text=True, check=True,
    ).stdout
    oversized = [
        line for line in ls.splitlines()
        # format: "<mode> <type> <object> <size>\t<path>"; type is "blob" for files
        if line.split("\t", 1)[0].split()[1] == "blob"
        and int(line.split("\t", 1)[0].split()[3]) > _LIMIT
    ]
    assert not oversized, f"GH001: HEAD still carries a >{_LIMIT}B blob: {oversized}"
    # The qledger plane is held back, not deleted — the working tree is the
    # source of truth and the carve-out is only an unstage.
    for spec in (
        ("HEAD:data/qledger/claims.jsonl", b'{"claim_id":"c0"}\n'),
        ("HEAD:site/qledger/track_record.json", b"{}"),
    ):
        out = subprocess.run(
            ["git", "show", spec[0]], cwd=repo,
            env={**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"},
            capture_output=True, check=True,
        ).stdout
        assert out == spec[1], f"{spec[0]!r} drifted: {out!r}"
    # The pre-existing carve-outs still hold: capital_structure and hk are
    # still un-staged from the market commit (they ride their own checkpoints).
    for spec in (
        ("HEAD:data/capital_structure/source_manifest.jsonl", b"m1\n"),
        ("HEAD:data/hk/x.csv", b"h1\n"),
    ):
        out = subprocess.run(
            ["git", "show", spec[0]], cwd=repo,
            env={**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"},
            capture_output=True, check=True,
        ).stdout
        assert out == spec[1], f"{spec[0]!r} drifted: {out!r}"
    # CRITICAL: the working-tree ledger is INTACT. The carve-out un-stages; it
    # does not revert (reverting would feed tomorrow the old manifest).
    wt_size = (repo / "data" / "qledger" / "claims.jsonl").stat().st_size
    assert wt_size == _LIMIT + 4096, (
        f"working-tree ledger size {wt_size} ≠ {_LIMIT + 4096}; "
        "the carve-out must NOT `git checkout` or otherwise revert the file"
    )
    status = subprocess.run(
        ["git", "status", "--porcelain", "--", "data/qledger/claims.jsonl"],
        cwd=repo,
        env={**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"},
        capture_output=True, text=True, check=True,
    ).stdout
    assert "data/qledger/claims.jsonl" in status, (
        f"working-tree ledger should still be modified in the index after the "
        f"carve-out (carve-out un-stages, not reverts); got status: {status!r}"
    )
    # Outputs + warning are the user-visible contract: the run is honest about
    # what it did NOT publish.
    assert outputs.get("committed") == "true"
    assert outputs.get("qledger_carved") == "true"
    assert "::warning title=qledger carved out of market commit::" in proc.stdout
    assert "data/qledger/claims.jsonl" in proc.stdout


@pytest.mark.parametrize("size,carved", [(_LIMIT - _MARGIN + 1, True), (_LIMIT - _MARGIN, False)])
def test_qledger_carve_threshold(tmp_path, collect_steps, size, carved):
    """Threshold: carve when the blob is STRICTLY within the margin of the limit."""

    def mutate(repo):
        (repo / "data" / "baskets" / "ohlcv" / "NVDA.parquet").write_bytes(b"v2")
        _grow(repo / "data" / "qledger" / "claims.jsonl", size)

    proc, outputs, repo = _run_market_commit(tmp_path, collect_steps, mutate)
    if carved:
        assert outputs.get("qledger_carved") == "true", (
            f"size={size} should carve but outputs={outputs!r}"
        )
        head_claims = subprocess.run(
            ["git", "show", "HEAD:data/qledger/claims.jsonl"], cwd=repo,
            env={**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"},
            capture_output=True, check=True,
        ).stdout
        assert head_claims == b'{"claim_id":"c0"}\n', (
            f"size={size}: carved, but HEAD claims should equal base; got {head_claims!r}"
        )
    else:
        assert "qledger_carved" not in outputs, (
            f"size={size} should NOT carve but outputs={outputs!r}"
        )
        head_size = subprocess.run(
            ["git", "cat-file", "-s", "HEAD:data/qledger/claims.jsonl"], cwd=repo,
            env={**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"},
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        assert int(head_size) == size, f"size={size}: HEAD claims size {head_size}"
    # The market plane publishes either way — that's the carve-out's reason to exist.
    nvda = subprocess.run(
        ["git", "show", "HEAD:data/baskets/ohlcv/NVDA.parquet"], cwd=repo,
        env={**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"},
        capture_output=True, check=True,
    ).stdout
    assert nvda == b"v2"


def test_qledger_carve_only_ledger_changed_commits_nothing(tmp_path, collect_steps):
    """If the ONLY staged change is the oversize ledger, the whole market
    commit is a no-op — no regression on the existing empty-diff guard."""

    def mutate(repo):
        _grow(repo / "data" / "qledger" / "claims.jsonl", _LIMIT + 4096)

    proc, outputs, repo = _run_market_commit(tmp_path, collect_steps, mutate)
    assert proc.returncode == 0, f"step failed: stdout={proc.stdout!r} stderr={proc.stderr!r}"
    assert "no market data changes to commit" in proc.stdout
    assert outputs.get("committed") == "false"
    subject = subprocess.run(
        ["git", "log", "-1", "--format=%s"], cwd=repo,
        env={**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"},
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    assert subject == "base", f"HEAD should still be the base commit; got subject={subject!r}"


def test_qledger_carve_small_ledger_growth_is_published_as_before(tmp_path, collect_steps):
    """A ledger well below the threshold must still publish — the carve-out is
    a SAFETY VALVE, not a switch that turns off ledger publishing forever."""

    def mutate(repo):
        with open(repo / "data" / "qledger" / "claims.jsonl", "ab") as f:
            f.write(b'{"claim_id":"c2"}\n')
        (repo / "site" / "qledger" / "track_record.json").write_bytes(b'{"n":1}')
        (repo / "data" / "baskets" / "ohlcv" / "NVDA.parquet").write_bytes(b"v2")

    proc, outputs, repo = _run_market_commit(tmp_path, collect_steps, mutate)
    assert outputs.get("committed") == "true"
    assert "qledger_carved" not in outputs, (
        f"small ledger should NOT trigger the carve-out; outputs={outputs!r}"
    )
    new_claims = (repo / "data" / "qledger" / "claims.jsonl").read_bytes()
    head_claims = subprocess.run(
        ["git", "show", "HEAD:data/qledger/claims.jsonl"], cwd=repo,
        env={**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"},
        capture_output=True, check=True,
    ).stdout
    assert head_claims == new_claims, "small ledger growth did not land in HEAD"
    head_tr = subprocess.run(
        ["git", "show", "HEAD:site/qledger/track_record.json"], cwd=repo,
        env={**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"},
        capture_output=True, check=True,
    ).stdout
    assert head_tr == b'{"n":1}'
    assert "qledger carved" not in proc.stdout


# ── the other way to lose a night: publish it, then overwrite it ──────────────
# The commit path above makes a night REAL. This guard covers the mirror defect:
# a LATER job in the same night restoring a stale GHA cache on top of what an
# earlier job already committed, then committing the stale copy back.
#
# 2026-08-06, measured: `collect` wrote data/breadth/_closes_cache.parquet through
# the 08-05 close (348 rows x 510 names, 361136284f2); the `engine` job 14 hours
# later committed it back at 2026-07-31 (345 x 509, 2dfebf35dbd), because its
# actions/cache step carried `restore-keys: breadth-closes-`, which matches the
# newest cache under that prefix from ANY prior run.
#
# The blast radius was the whole US board. engine/residual_alpha.py stamps
# as_of = R.index.max() off that panel, alpha.json carries it, build_stock_library
# copies it into us_standouts.json, and the snapshotter keys on as_of — so
# data/us_board_ledger/snapshots.jsonl appended NOTHING for six days while the
# board kept publishing picks ranked on 07-31 factors next to current-day prices.
#
# china*/hk* never had this problem: the commit steps unstage every asia-owned
# path (W0b, 2026-07-08), so a stale restore there cannot reach a commit. This
# test encodes the real invariant rather than a list of paths — a git-tracked
# cache path that the commit step does NOT unstage must not carry a restore-key.

import fnmatch  # noqa: E402
import subprocess  # noqa: E402


def _is_git_tracked(path: str) -> bool:
    """True when the path has at least one tracked file (so a commit can carry it)."""
    out = subprocess.run(["git", "ls-files", "--", path],
                         cwd=ROOT, capture_output=True, text=True).stdout
    return bool(out.strip())


def _unstaged_by(commit_run: str, path: str) -> bool:
    """True when a `git reset` in the commit step unstages this path (asia-owned carve-out)."""
    for line in commit_run.splitlines():
        line = line.strip()
        if not line.startswith("git reset"):
            continue
        for tok in line.split():
            if not tok.startswith("data/"):
                continue
            if path == tok or path.startswith(tok.rstrip("*")) or fnmatch.fnmatch(path, tok):
                return True
    return False


#: Jobs that CONSUME the breadth panel without regenerating it. `collect` is
#: deliberately absent: it is the PRODUCER, and there its prefix restore-key is
#: load-bearing — it warm-starts the ~3-year panel so the collectors only have to
#: append today's closes. Restoring a prior cache and then rewriting the file is
#: safe; restoring one and then committing it unchanged is what corrupts the night.
_CACHE_CONSUMER_JOBS = ["engine"]


@pytest.mark.parametrize("job_name", _CACHE_CONSUMER_JOBS)
def test_no_job_restores_a_stale_cache_over_data_it_will_commit(job_name):
    doc = yaml.safe_load(DAILY.read_text())
    job = doc["jobs"][job_name]
    steps = job.get("steps") or []
    # 512KB-cap diet: some commit bodies live in scripts/ci/ — resolve the
    # effective source so the unstage carve-outs below stay visible.
    commit_run = "\n".join(
        resolve_run_source(str(s.get("run") or ""), ROOT) for s in steps
        if "commit" in ((s.get("name") or "").lower())
    )

    offenders = []
    for st in steps:
        if not str(st.get("uses") or "").startswith("actions/cache@"):
            continue
        w = st.get("with") or {}
        path = str(w.get("path") or "").strip()
        if not path.startswith("data/") or not w.get("restore-keys"):
            continue
        if not _is_git_tracked(path):
            continue              # untracked: no commit can carry it back
        if _unstaged_by(commit_run, path):
            continue              # carved out of `git add data/` before the commit
        offenders.append(f"{path} (restore-keys: {str(w['restore-keys']).strip()})")

    assert not offenders, (
        f"daily.yml job {job_name!r} restores a prefix-matched GHA cache onto GIT-TRACKED "
        f"paths it then commits: {offenders}. A prefix restore-key matches the newest cache "
        f"from ANY prior run, so this overwrites data an earlier job committed tonight and "
        f"pushes the stale copy back — it froze the US board at as_of=2026-07-31 for six "
        f"days on 2026-08-06. Either drop restore-keys (the job then simply uses the fresh "
        f"panel already in the git checkout) or unstage the path in the commit step the way "
        f"the asia-owned china*/hk* carve-out does."
    )


def test_gitignored_russell_cache_uses_the_collect_jobs_exact_same_run_key():
    """Russell cache is untracked: one producer→consumer run key; no old-cache fallback.

    Oct 16 repeat: market Git GH001 failed AFTER a healthy Russell collector,
    so the combined cache action's post-save was skipped and engine missed its
    exact key. Collect now has a separate, qualified save BEFORE that late
    push; engine still cannot prefix-restore any earlier night's source.
    """
    path = "data/russell_breadth/_closes_cache.parquet"
    assert not _is_git_tracked(path), (
        "the Russell cache became git-tracked; reassess the cross-job owner"
    )
    doc = yaml.safe_load(DAILY.read_text())
    engine = doc["jobs"]["engine"]
    assert "collect" in engine.get("needs", []), (
        "engine must wait for the producer of this run's Russell close panel"
    )

    def cache_step(job_name: str, owner_action: str) -> dict:
        matches = [
            step for step in doc["jobs"][job_name]["steps"]
            if (step.get("with") or {}).get("path") == path
            and step.get("uses") == owner_action
        ]
        assert len(matches) == 1, (
            f"expected exactly one {owner_action} for {path} in {job_name!r}; "
            f"found {len(matches)}"
        )
        return matches[0]

    producer = cache_step("collect", "actions/cache/restore@v4")["with"]
    saver = cache_step("collect", "actions/cache/save@v4")["with"]
    consumer_step = cache_step("engine", "actions/cache/restore@v4")
    consumer = consumer_step["with"]
    expected = "russell-closes-${{ github.run_id }}"

    assert producer.get("key") == expected
    assert producer.get("restore-keys") == "russell-closes-"
    assert saver == {"key": expected, "path": path}, (
        "the qualified pre-push save must create the exact same run's key"
    )
    assert consumer.get("key") == expected, (
        "the engine must request the exact same-run Russell source"
    )
    assert "restore-keys" not in consumer, (
        "the engine must not prefix-restore an earlier source and silently "
        "launder a stale cross-section"
    )


# The 2026-09-15 recurrence crossed the old guard: restore-only rendering jobs
# can publish stale DERIVED boards even when they never commit the raw panel.
_US_COMMITTED_PRICE_PANELS = {
    "data/breadth/_closes_cache.parquet": "breadth-closes-",
    "data/smallcap_breadth/_closes_cache.parquet": "smallcap-closes-",
    "data/midcap_breadth/_closes_cache.parquet": "midcap-closes-",
}


def _workflow_files() -> list[Path]:
    workflow_dir = ROOT / ".github/workflows"
    return sorted({*workflow_dir.glob("*.yml"), *workflow_dir.glob("*.yaml")})


def _action_paths(value: object):
    values = value if isinstance(value, (list, tuple)) else [value]
    for item in values:
        for line in str(item or "").splitlines():
            path = line.strip()
            if path:
                yield path


def _us_panel_cache_steps():
    for workflow in _workflow_files():
        document = yaml.safe_load(workflow.read_text()) or {}
        for job_name, job in (document.get("jobs") or {}).items():
            for step in job.get("steps", []):
                uses = str(step.get("uses") or "")
                if not uses.startswith(("actions/cache@", "actions/cache/restore@")):
                    continue
                with_ = step.get("with") or {}
                for path in _action_paths(with_.get("path")):
                    if path in _US_COMMITTED_PRICE_PANELS:
                        yield workflow.name, job_name, step, path


def test_all_readonly_us_panel_consumers_preserve_git_authority():
    """A rendering job's lack of data/ staging does not make stale input safe."""
    readers = [(workflow, job, step, path)
               for workflow, job, step, path in _us_panel_cache_steps()
               if (workflow, job) != ("daily.yml", "collect")]
    required_workflows = {
        "daily.yml", "closing-bell.yml", "earlyclose.yml", "engine-render.yml",
        "render.yml", "weekly.yml", "special-sits-backfill.yml",
    }
    assert required_workflows <= {
        p.name for p in _workflow_files()
    }, "a missing workflow is not proof of a repaired reader"
    offenders = [f"{workflow}:{job}:{path}"
                 for workflow, job, step, path in readers]
    assert not offenders, (
        "Read-only consumers overwrite committed US price panels with cached "
        f"copies and publish stale derived boards: {offenders}. Read the Git "
        "checkout directly. Even an exact cache key can restore an earlier "
        "attempt's input on a same-run retry. Never restamp stale inputs or "
        "remove the distinct gitignored Russell handoff."
    )


def test_daily_collector_keeps_us_panel_seed_cache_authority():
    """The producer seed remains useful; consumers cannot impersonate it."""
    seeds: dict[str, list[object]] = {}
    for workflow, job, step, path in _us_panel_cache_steps():
        if (workflow, job) != ("daily.yml", "collect"):
            continue
        seeds.setdefault(path, []).append((step.get("with") or {}).get("restore-keys"))

    assert set(seeds) == set(_US_COMMITTED_PRICE_PANELS)
    for path, expected_restore_key in _US_COMMITTED_PRICE_PANELS.items():
        assert len(seeds[path]) == 1, (
            f"{path} must have exactly one producer seed in daily.collect; found "
            f"{len(seeds[path])} cache steps"
        )
        assert seeds[path][0] == expected_restore_key
        assert _is_git_tracked(path), (
            f"{path} changed data ownership; do not silently replace the reviewed "
            "Git-authoritative reader policy with a cache fallback"
        )



def test_stock_briefs_restores_r2_stock_context_before_precompute():
    """The clean brief job must materialize its canonical R2-only stock context."""
    document = yaml.safe_load(DAILY.read_text()) or {}
    steps = document["jobs"]["stock_briefs"]["steps"]
    build_indexes = [
        index for index, step in enumerate(steps)
        if "python -m scripts.build_stock_briefs" in str(step.get("run") or "")
    ]
    assert len(build_indexes) == 1
    build_index = build_indexes[0]
    assert str(steps[build_index].get("run") or "").strip() == (
        "python -m scripts.build_stock_briefs"
    ), (
        "stock_briefs is an additive job that does not gate publish; do not turn a "
        "deterministic context failure into a green workflow with shell fail-open."
    )

    restores = [
        (index, step) for index, step in enumerate(steps[:build_index])
        if str(step.get("run") or "").strip()
        == "python -m scripts.fetch_r2 --dirs stockdata"
    ]
    assert len(restores) == 1, (
        "stock_briefs starts from a clean checkout while site/stockdata is R2-only. "
        "Restore the existing stockdata store before catalyst_stock asks for its "
        "deterministic ladder context; a green no_context batch is not usable output."
    )
    restore_index, restore = restores[0]
    assert restore_index < build_index
    gha = lambda name: "$" + "{{ secrets." + name + " }}"
    assert restore.get("env") == {
        "R2_ENDPOINT": gha("R2_ENDPOINT"),
        "R2_ACCESS_KEY_ID": gha("R2_ACCESS_KEY_ID"),
        "R2_SECRET_ACCESS_KEY": gha("R2_SECRET_ACCESS_KEY"),
        "R2_BUCKET": gha("R2_BUCKET"),
    }, "scope the existing R2 credentials to the stockdata restore step only"


def _write_panel_workflow(root: Path, filename: str, body: str) -> Path:
    workflow = root / ".github/workflows" / filename
    workflow.parent.mkdir(parents=True, exist_ok=True)
    workflow.write_text(body)
    return workflow


def test_us_panel_cache_scan_splits_multiline_action_paths(tmp_path, monkeypatch):
    _write_panel_workflow(tmp_path, "multiline.yml", """
jobs:
  engine:
    steps:
      - uses: actions/cache/restore@v4
        with:
          path: |
            data/breadth/_closes_cache.parquet
            data/unrelated.parquet
""")
    monkeypatch.setattr(sys.modules[__name__], "ROOT", tmp_path)

    paths = [path for _, _, _, path in _us_panel_cache_steps()]

    assert paths == ["data/breadth/_closes_cache.parquet"]


def test_us_panel_cache_scan_includes_yaml_workflows(tmp_path, monkeypatch):
    _write_panel_workflow(tmp_path, "reader.yaml", """
jobs:
  engine:
    steps:
      - uses: actions/cache/restore@v4
        with:
          path: data/midcap_breadth/_closes_cache.parquet
""")
    monkeypatch.setattr(sys.modules[__name__], "ROOT", tmp_path)

    paths = [path for _, _, _, path in _us_panel_cache_steps()]

    assert paths == ["data/midcap_breadth/_closes_cache.parquet"]


def test_duplicate_daily_panel_seed_steps_are_rejected(tmp_path, monkeypatch):
    daily = _write_panel_workflow(tmp_path, "daily.yml", """
jobs:
  collect:
    steps:
      - uses: actions/cache@v4
        with:
          path: data/breadth/_closes_cache.parquet
          restore-keys: breadth-closes-
      - uses: actions/cache@v4
        with:
          path: data/breadth/_closes_cache.parquet
          restore-keys: breadth-closes-
      - uses: actions/cache@v4
        with:
          path: data/smallcap_breadth/_closes_cache.parquet
          restore-keys: smallcap-closes-
      - uses: actions/cache@v4
        with:
          path: data/midcap_breadth/_closes_cache.parquet
          restore-keys: midcap-closes-
""")
    monkeypatch.setattr(sys.modules[__name__], "ROOT", tmp_path)
    monkeypatch.setattr(sys.modules[__name__], "DAILY", daily)
    monkeypatch.setattr(sys.modules[__name__], "_is_git_tracked", lambda _: True)

    with pytest.raises(AssertionError, match="exactly one producer seed"):
        test_daily_collector_keeps_us_panel_seed_cache_authority()


def test_russell_same_run_cache_is_saved_before_unrelated_git_push_failure():
    """Oct 16: GH001 after a healthy Russell collect must not erase engine's source."""
    doc = yaml.safe_load(DAILY.read_text())
    path = "data/russell_breadth/_closes_cache.parquet"
    key = "russell-closes-${{ github.run_id }}"
    collect = doc["jobs"]["collect"]["steps"]
    engine = doc["jobs"]["engine"]["steps"]

    def one(step_list, name):
        matches = [i for i, st in enumerate(step_list) if st.get("name") == name]
        assert len(matches) == 1, (name, matches)
        return matches[0], step_list[matches[0]]

    c, _ = one(collect, "run collectors (graceful degradation — never fails the build on one source)")
    readiness, gate = one(collect, "qualify Russell same-run cache handoff")
    save, saver = one(collect, "save qualified Russell close cache before market git push")
    push, _ = one(collect, "push market data (survives a job-cap cancel; alarm-bounded git ops)")
    assert c < readiness < save < push
    assert "started_at=$(date -u" in collect[c].get("run", "")
    assert '>> "$GITHUB_OUTPUT"' in collect[c].get("run", "")
    assert gate.get("env", {}).get("RUSSELL_COLLECT_STARTED_AT") == (
        "${{ steps.collectors.outputs.started_at }}"
    )
    assert 'receipt.get("last_run")' in str(gate.get("run", ""))
    assert gate.get("id") == "russell_cache_ready"
    assert "data/run_status.json" in str(gate.get("run", ""))
    assert "russell_breadth" in str(gate.get("run", ""))
    assert "expected_last_session" in str(gate.get("run", ""))
    assert "checked_at" in str(gate.get("run", ""))
    assert saver["uses"] == "actions/cache/save@v4"
    assert saver["with"] == {"path": path, "key": key}
    assert "steps.russell_cache_ready.outputs.qualified == 'true'" in saver["if"]

    restore = [st for st in collect
               if st.get("uses") == "actions/cache/restore@v4"
               and (st.get("with") or {}).get("path") == path]
    assert len(restore) == 1
    assert restore[0]["with"]["key"] == key
    assert restore[0]["with"]["restore-keys"] == "russell-closes-"

    consumer = [st for st in engine
                if (st.get("with") or {}).get("path") == path]
    assert len(consumer) == 1
    assert consumer[0]["uses"] == "actions/cache/restore@v4"
    assert consumer[0]["with"]["key"] == key
    assert "restore-keys" not in consumer[0]["with"]


@pytest.mark.parametrize(
    "case,expected_ready",
    [
        ("healthy", True),
        ("source_failed", False),
        ("source_stale", False),
        ("clock_before_close", False),
        ("clock_in_future", False),
        ("malformed_clock", False),
        ("cache_missing", False),
        ("receipt_missing", False),
        ("old_source_same_session", False),
        ("old_status_same_session", False),
        ("missing_run_marker", False),
        ("malformed_run_marker", False),
        ("malformed_last_run", False),
    ],
)
def test_russell_same_run_handoff_executes_original_gate_hermetically(
    tmp_path, case, expected_ready
):
    """The actual workflow's short gate, not a reimplementation in this test."""
    import json
    import os
    import subprocess
    from datetime import datetime, time, timezone, timedelta
    from zoneinfo import ZoneInfo
    from lib.nyse_calendar import expected_last_session

    doc = yaml.safe_load(DAILY.read_text())
    gate = next(st for st in doc["jobs"]["collect"]["steps"]
                if st.get("name") == "qualify Russell same-run cache handoff")
    raw = gate["run"]
    assert "<<'PY_RUSSELL_HANDOFF'\n" in raw
    script = raw.split("<<'PY_RUSSELL_HANDOFF'\n", 1)[1].rsplit(
        "\nPY_RUSSELL_HANDOFF", 1
    )[0]
    now = datetime.now(timezone.utc)
    session = expected_last_session()
    last_close = datetime.combine(
        session, time(16), tzinfo=ZoneInfo("America/New_York")
    ).astimezone(timezone.utc)
    checked = now
    if case == "clock_before_close":
        checked = last_close - timedelta(seconds=1)
    if case == "clock_in_future":
        checked = now + timedelta(days=1)
    if case in ("old_source_same_session", "old_status_same_session"):
        checked = now - timedelta(minutes=4)
    raw_stamp = checked.isoformat() if case != "malformed_clock" else "???"
    run_started = now - timedelta(minutes=3)
    if case == "old_status_same_session":
        run_started = now - timedelta(minutes=1)
    last_run = now - timedelta(minutes=1)
    if case == "old_status_same_session":
        last_run = now - timedelta(minutes=5)
    if case == "malformed_last_run":
        last_run = "?"
    status = {
        "last_run": last_run.isoformat() if isinstance(last_run, datetime) else last_run,
        "sources": {
            "russell_breadth": {
                "status": "failed" if case == "source_failed" else "ok",
                "last_date": (
                    (session - timedelta(days=1)).isoformat()
                    if case == "source_stale" else session.isoformat()
                ),
                "checked_at": raw_stamp,
            }
        }
    }
    data = tmp_path / "data"
    cache = data / "russell_breadth" / "_closes_cache.parquet"
    cache.parent.mkdir(parents=True)
    if case != "cache_missing":
        cache.write_bytes(b"PAR1a guarded producer already checkedPAR1")
    if case != "receipt_missing":
        (data / "run_status.json").write_text(json.dumps(status))
    output = tmp_path / "gate-output"
    env = {**os.environ, "GITHUB_OUTPUT": str(output),
           "PYTHONPATH": str(ROOT),
           "RUSSELL_COLLECT_STARTED_AT": run_started.isoformat()}
    if case == "missing_run_marker":
        del env["RUSSELL_COLLECT_STARTED_AT"]
    elif case == "malformed_run_marker":
        env["RUSSELL_COLLECT_STARTED_AT"] = "?"
    proc = subprocess.run(
        [sys.executable, "-c", script], cwd=tmp_path,
        env=env, capture_output=True, text=True, timeout=15,
    )
    assert proc.returncode == 0, proc.stderr[-500:]
    observed = output.read_text().strip()
    assert observed == f"qualified={'true' if expected_ready else 'false'}"
    assert "Russell cache handoff" in proc.stdout


def test_collect_job_has_publication_headroom_after_oct14_timeout_loss():
    """A real four-hour collect ended mid-push with just 6m08s left at entry.

    GH job 115629246223: 2026-10-14 01:20:35Z -> push at 05:14:27Z,
    cancelled at 05:25:36Z before GitHub received the original commit.
    An alarm-bounded push is 420s, plus fetch/rebase and retry overhead.
    Require at least one hour of reserved room from that observed entry
    point before raising another producer budget or claiming acceptance.
    """
    spec = yaml.safe_load(DAILY.read_text(encoding="utf-8"))["jobs"]["collect"]
    cap = spec["timeout-minutes"]
    assert type(cap) is int and cap <= 360
    observed_push_start = 3 * 3600 + 53 * 60 + 52
    required_reserve = 60 * 60
    assert cap * 60 - observed_push_start >= required_reserve, (
        "collect's clock leaves less than one hour for its existing "
        "market publisher after the observed October 14 producer duration"
    )
    market_push = [
        step for step in spec["steps"]
        if step.get("name", "").startswith("push market data")
    ]
    assert len(market_push) == 1
    assert "PUSH_ALARM=420" in market_push[0].get("run", "")


# ── Carve-custody guard (PR #9556 review 5566188238) ──────────────────────────
# The qledger carve-out leaves data/qledger + site/qledger DIRTY in the worktree,
# and the push step's `git pull --rebase --autostash` carries that dirt across
# the rebase. A conflicted re-apply (e.g. a concurrent site/qledger/
# track_record.json — NOT merge=union) makes push_autostash_ok drop the stash
# and `git reset --hard HEAD`, silently destroying the freshly-collected claims
# append while the market push still reports `published=true`. The park +
# restore steps isolate those bytes from the autostash and emit a non-fatal
# "not published" signal. These tests pin the guard with real Git integration:
# a synthetic racer clone forces the conflict and the harness runs the verbatim
# step bodies, so a regression in daily.yml fails with the exact loss scenario
# the lane was built to stop.

import shutil  # noqa: E402


def _carve_seed_gitattributes(repo, env):
    """Seed the temp repo's base commit with the REAL ROOT `.gitattributes` so
    the push step's `--autostash` / race re-apply sees the same merge attributes
    as the real repository (e.g. site/qledger/track_record.json is NOT
    `merge=union` on a52f5ad8)."""
    shutil.copy(ROOT / ".gitattributes", repo / ".gitattributes")


def _carve_step_body(collect_steps, needle):
    """Return the verbatim `run:` body for a step whose name contains `needle`,
    or None if absent. Used by the carve-custody tests so a52f5ad8 (no park or
    restore step yet) does not trip on a missing helper."""
    idx = _index_of_absent(collect_steps, needle)
    if idx is None:
        return None
    return str(collect_steps[idx].get("run") or "")


def _make_step_env(tmp_path, summary_path, snapshot, *,
                   racer_dir=None, counter_file=None, real_git=None):
    """Return the env dict used to run every step body verbatim. Honours the
    harness' git-config overrides and the lane's PUSH_* + QLEDGER_SNAPSHOT
    contract. Each caller writes a fresh GITHUB_OUTPUT per step."""
    shim_dir = tmp_path / "shim"
    path_dirs = [str(shim_dir)] + [
        d for d in os.environ.get("PATH", "").split(":")
        if d and d != str(shim_dir)
    ]
    env = {
        "PATH": ":".join(path_dirs),
        "PYTHONPATH": str(ROOT),
        "GITHUB_WORKSPACE": str(ROOT),
        "GITHUB_ACTIONS": "true",
        "GITHUB_OUTPUT": str(tmp_path / "step_output"),
        "GITHUB_STEP_SUMMARY": str(summary_path),
        "PUSH_MAX_ATTEMPTS": "3",
        "PUSH_BUDGET_SECS": "120",
        "PUSH_FENCE_PYTHON": sys.executable,
        "QLEDGER_SNAPSHOT": snapshot,
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_ALLOW_PROTOCOL": "file",
        "GIT_CONFIG_COUNT": "2",
        "GIT_CONFIG_KEY_0": "core.hooksPath",
        "GIT_CONFIG_VALUE_0": os.devnull,
        "GIT_CONFIG_KEY_1": "commit.gpgsign",
        "GIT_CONFIG_VALUE_1": "false",
        "GIT_AUTHOR_NAME": "bot",
        "GIT_AUTHOR_EMAIL": "bot@bot",
        "GIT_COMMITTER_NAME": "bot",
        "GIT_COMMITTER_EMAIL": "bot@bot",
    }
    if racer_dir is not None:
        env["SHIM_RACER_DIR"] = str(racer_dir)
    if counter_file is not None:
        env["SHIM_COUNTER"] = str(counter_file)
    if real_git is not None:
        env["SHIM_REAL_GIT"] = str(real_git)
    return env


def _run_step(body, cwd, env, *, timeout=300):
    """Run a step body verbatim with the harness shell. Asserts no `${{`
    survives — would have been swallowed by github_actions if present."""
    assert "${{" not in body, (
        f"step body has ${{...}} interpolation: {body[:120]!r}..."
    )
    return subprocess.run(
        ["bash", "--noprofile", "--norc", "-eo", "pipefail", "-c",
         "sleep() { :; }\n" + body],
        cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout,
    )


def _write_shims(shim_dir, real_git):
    """Write the `git`, `python`, `python3` shims used by the harness. The
    `git` shim is pass-through except for the FIRST `git push` it sees, when
    it also publishes the racer's racing-lane.txt (clean-race injection). The
    counter file lives next to the shim dir, so each test starts at zero.
    SHIM_RESTORE_MODE (unset = pass-through) faults `git restore`: `refuse`
    exits 74 without calling git; `noop` exits 0 without calling git."""
    shim_dir.mkdir(exist_ok=True)
    counter_file = shim_dir.parent / "push_count"
    counter_file.write_text("0")

    (shim_dir / "git").write_text(
        "#!/usr/bin/env bash\n"
        "set -e\n"
        "counter_file=\"${SHIM_COUNTER:?SHIM_COUNTER not set}\"\n"
        "racer_dir=\"${SHIM_RACER_DIR:-}\"\n"
        "real_git=\"${SHIM_REAL_GIT:?SHIM_REAL_GIT not set}\"\n"
        "restore_mode=\"${SHIM_RESTORE_MODE:-}\"\n"
        "if [ -n \"$restore_mode\" ]; then\n"
        "  for a in \"$@\"; do\n"
        "    if [ \"$a\" = \"restore\" ]; then\n"
        "      if [ \"$restore_mode\" = \"refuse\" ]; then\n"
        "        echo \"shim: git restore refused (simulated park failure)\" >&2\n"
        "        exit 74\n"
        "      fi\n"
        "      exit 0\n"
        "    fi\n"
        "  done\n"
        "fi\n"
        "is_push=0\n"
        "for a in \"$@\"; do\n"
        "  if [ \"$a\" = \"push\" ]; then is_push=1; break; fi\n"
        "done\n"
        "if [ \"$is_push\" = \"1\" ]; then\n"
        "  n=$(cat \"$counter_file\" 2>/dev/null || echo 0)\n"
        "  if [ \"$n\" = \"0\" ] && [ -n \"$racer_dir\" ] && "
        "[ -d \"$racer_dir\" ] && [ -f \"$racer_dir/racing-lane.txt\" ]; then\n"
        "    ( cd \"$racer_dir\" && \"$real_git\" push origin HEAD:main ) "
        ">\"$counter_file.publog\" 2>&1 || true\n"
        "  fi\n"
        "  echo $((n+1)) > \"$counter_file\" 2>/dev/null || true\n"
        "fi\n"
        "exec \"$real_git\" \"$@\"\n"
    )
    (shim_dir / "git").chmod(0o755)

    for py_name in ("python", "python3"):
        (shim_dir / py_name).write_text(
            f"#!/usr/bin/env bash\nexec \"{sys.executable}\" \"$@\"\n"
        )
        (shim_dir / py_name).chmod(0o755)


def _read_step_outputs(path):
    """Parse a GITHUB_OUTPUT file of key=value lines (last write wins;
    missing file -> {}), mirroring the parser in _run_market_commit."""
    outputs: dict[str, str] = {}
    if path.exists():
        for line in path.read_text().splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                outputs[k] = v
    return outputs


def _git_env(repo=None):
    """Minimal env for real-git helper calls that don't go through the shim."""
    env = {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
    if repo is not None:
        env["GIT_AUTHOR_NAME"] = "h"
        env["GIT_AUTHOR_EMAIL"] = "h@h"
        env["GIT_COMMITTER_NAME"] = "h"
        env["GIT_COMMITTER_EMAIL"] = "h@h"
    return env


def _git(repo, *args, **kw):
    """Run git in the repo with the harness env. Returns CompletedProcess."""
    return subprocess.run(
        ["git", *args], cwd=repo, env=_git_env(),
        capture_output=True, text=True, check=kw.pop("check", True), **kw,
    )


def _run_carve_publish(tmp_path, collect_steps, monkeypatch, race, park_mode=None):
    """Build the carve-custody harness. Returns a namespace dict with the repo,
    racer, origin, deferred/HEAD blob ids, step procs and outputs. park_mode
    (refuse | noop) faults `git restore` in the park step only."""
    # 1. Cleanup parent env so a contaminated host cannot leak into the steps.
    for k in list(os.environ):
        if k.startswith("GIT_") or k.startswith("PUSH_") or k in ("BASH_ENV", "ENV"):
            monkeypatch.delenv(k, raising=False)

    # 2. Locate the real git binary BEFORE the shim shadows it. `shutil.which`
    # resolves via the parent process PATH (which the harness has not touched);
    # fall back to the conventional location if shutil can't find it.
    real_git = shutil.which("git") or "/usr/bin/git"
    if not os.path.isfile(real_git):
        bash_which = subprocess.run(
            ["bash", "-c", "command -v git"],
            capture_output=True, text=True, check=False,
        )
        if bash_which.returncode == 0 and bash_which.stdout.strip():
            real_git = bash_which.stdout.strip()

    # 3. Step bodies.
    commit_run = str(collect_steps[_index_of(collect_steps, MARKET_COMMIT_STEP)]["run"])
    push_step = collect_steps[_index_of(collect_steps, MARKET_PUSH_STEP)]
    push_run = str(push_step["run"])
    park_run = _carve_step_body(collect_steps, QLEDGER_PARK_STEP)
    restore_run = _carve_step_body(collect_steps, QLEDGER_RESTORE_STEP)

    # 4. Run commitdata on a fresh repo (mutates + records deferred state).
    def mutate(repo):
        (repo / "data" / "baskets" / "ohlcv" / "NVDA.parquet").write_bytes(b"v2")
        _grow(repo / "data" / "qledger" / "claims.jsonl", _LIMIT + 4096)
        (repo / "site" / "qledger" / "track_record.json").write_bytes(b'{"n":1}')
        (repo / "data" / "capital_structure" / "source_manifest.jsonl").write_bytes(b"m2\n")

    commit_proc, commit_outputs, repo = _run_market_commit(
        tmp_path, collect_steps, mutate, seed=_carve_seed_gitattributes,
    )
    assert commit_proc.returncode == 0, (
        f"commitdata failed: stdout={commit_proc.stdout!r} "
        f"stderr={commit_proc.stderr!r}"
    )
    assert commit_outputs.get("committed") == "true", (
        f"commitdata did not commit (no market change?): {commit_outputs!r}"
    )
    assert commit_outputs.get("qledger_carved") == "true", (
        f"commitdata did not carve (no oversize?): {commit_outputs!r}"
    )

    # 5. Record committed (HEAD^/HEAD) and deferred (worktree) blob ids.
    base_sha = _git(repo, "rev-parse", "HEAD^").stdout.strip()

    def blob_at(rev, path):
        return subprocess.run(
            ["git", "show", f"{rev}:{path}"], cwd=repo, env=_git_env(),
            capture_output=True, check=True,
        ).stdout

    def hash_at(path):
        return subprocess.run(
            ["git", "hash-object", "--no-filters", "--", str(repo / path)],
            cwd=repo, env=_git_env(),
            capture_output=True, text=True, check=True,
        ).stdout.strip()

    head_sha = _git(repo, "rev-parse", "HEAD").stdout.strip()
    deferred_claims = hash_at("data/qledger/claims.jsonl")
    deferred_twin = hash_at("site/qledger/track_record.json")
    claims_at_base = blob_at(base_sha, "data/qledger/claims.jsonl")
    twin_at_base = blob_at(base_sha, "site/qledger/track_record.json")

    # 6. Origin: bare repo with the base commit (HEAD^).
    origin = tmp_path / "origin.git"
    subprocess.run(
        ["git", "init", "--bare", "-q", "-b", "main", str(origin)], check=True,
    )
    subprocess.run(
        ["git", "push", "-q", str(origin), f"{base_sha}:refs/heads/main"],
        cwd=repo, env=_git_env(), check=True,
    )
    _git(repo, "remote", "add", "origin", str(origin))
    _git(repo, "fetch", "origin", "main")
    _git(repo, "branch", "--set-upstream-to=origin/main", "main")

    # 7. Racer clone. The racer's commit differs per `race`.
    racer = tmp_path / "racer"
    subprocess.run(["git", "clone", "-q", str(origin), str(racer)], check=True)
    racer_env = _git_env()
    subprocess.run(["git", "config", "user.name", "racer"],
                   cwd=racer, env=racer_env, check=True)
    subprocess.run(["git", "config", "user.email", "racer@racer"],
                   cwd=racer, env=racer_env, check=True)
    if race == "clean":
        (racer / "racing-lane.txt").write_text("racing\n")
        subprocess.run(["git", "add", "racing-lane.txt"],
                       cwd=racer, env=racer_env, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "racing-lane"],
                       cwd=racer, env=racer_env, check=True)
    elif race == "conflicted":
        (racer / "site" / "qledger").mkdir(exist_ok=True)
        (racer / "site" / "qledger" / "track_record.json").write_bytes(b'{"racer":2}')
        subprocess.run(["git", "add", "site/qledger/track_record.json"],
                       cwd=racer, env=racer_env, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "racer twin"],
                       cwd=racer, env=racer_env, check=True)
        # Push the racer's divergent twin BEFORE pushdata starts so pushdata's
        # first pull sees it; this is the EXACT autostash-conflict scenario the
        # carve-out must survive.
        subprocess.run(
            ["git", "push", "-q", "origin", "HEAD:main"],
            cwd=racer, env=racer_env, check=True,
        )
    elif race == "reset":
        # A divergent capital-structure manifest: the CS carve-out leaves its
        # bytes dirty (they ride the autostash) and the path is NOT merge=union,
        # so the autostash re-apply conflicts and push_autostash_ok runs
        # `git reset --hard HEAD` even with the park step in place. The racer
        # never touches data/qledger or site/qledger.
        cs_dir = racer / "data" / "capital_structure"
        cs_dir.mkdir(parents=True, exist_ok=True)
        (cs_dir / "source_manifest.jsonl").write_bytes(b"racer-cs\n")
        subprocess.run(["git", "add", "data/capital_structure/source_manifest.jsonl"],
                       cwd=racer, env=racer_env, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "racer cs manifest"],
                       cwd=racer, env=racer_env, check=True)
        subprocess.run(
            ["git", "push", "-q", "origin", "HEAD:main"],
            cwd=racer, env=racer_env, check=True,
        )
    else:
        raise AssertionError(f"unknown race: {race!r}")

    # 8. Shims and step env.
    shim_dir = tmp_path / "shim"
    _write_shims(shim_dir, real_git)
    counter_file = shim_dir.parent / "push_count"
    summary_path = tmp_path / "summary.md"
    snapshot = commit_outputs.get("qledger_snapshot", "")

    env_template = _make_step_env(
        tmp_path, summary_path, snapshot,
        racer_dir=racer if race == "clean" else None,
        counter_file=counter_file, real_git=real_git,
    )

    def step_env_for(name):
        env = dict(env_template)
        env["GITHUB_OUTPUT"] = str(tmp_path / f"output_{name}")
        return env

    # 9. Run PARK / PUSH / RESTORE in workflow order, honouring the REAL gates.
    procs = {}

    if park_run and commit_outputs.get("committed") == "true" and snapshot:
        park_env = step_env_for("park")
        if park_mode:
            park_env["SHIM_RESTORE_MODE"] = park_mode
        procs["park"] = _run_step(park_run, repo, park_env)
    park_outputs = _read_step_outputs(tmp_path / "output_park")

    if _eval_commitdata_gate(
        push_step.get("if"), commit_outputs, cancelled=False, park_outputs=park_outputs,
    ):
        procs["push"] = _run_step(push_run, repo, step_env_for("push"))

    if restore_run and snapshot:
        procs["restore"] = _run_step(restore_run, repo, step_env_for("restore"))

    return {
        "commit_proc": commit_proc,
        "commit_outputs": commit_outputs,
        "repo": repo,
        "racer": racer,
        "origin": origin,
        "base_sha": base_sha,
        "head_sha": head_sha,
        "market_at_base": blob_at(base_sha, "data/baskets/ohlcv/NVDA.parquet"),
        "claims_at_base": claims_at_base,
        "twin_at_base": twin_at_base,
        "deferred_claims": deferred_claims,
        "deferred_twin": deferred_twin,
        "claims_size": (repo / "data" / "qledger" / "claims.jsonl").stat().st_size,
        "snapshot": snapshot,
        "summary_path": summary_path,
        "procs": procs,
        "park_outputs": park_outputs,
        "real_git": real_git,
    }


@pytest.mark.parametrize("race", ["clean", "conflicted", "reset"])
def test_qledger_carve_custody_survives_the_market_push(
    tmp_path, collect_steps, monkeypatch, race,
):
    """PR #9556 review 5566188238: end-to-end that the qledger carve-out must
    NOT silently destroy unpublished claims. A synthetic racer clone forces a
    real rebase race (clean = racing-lane only; conflicted = divergent
    site/qledger/track_record.json, the EXACT autostash-conflict scenario).
    reset = divergent capital-structure manifest, which forces a REAL
    conflicted autostash apply and `git reset --hard HEAD` even with the park
    step, so the claims must come back from the custody snapshot.
    On a52f5ad8 the carve-out is unprotected; the assertion order below makes
    the first failure the substantive one (BYTES for conflicted and reset,
    SIGNAL for clean — autostash re-applies cleanly when origin hasn't touched
    the carved paths)."""
    h = _run_carve_publish(tmp_path, collect_steps, monkeypatch, race)
    assert h["park_outputs"].get("parked") == "true", (
        f"park did not verify its parked state: {h['park_outputs']!r}"
    )
    assert "push" in h["procs"], "verified park must open the push gate"

    # 1. pushdata rc == 0 and `published` == "true".
    push = h["procs"].get("push")
    assert push is not None, "pushdata step did not run (commitdata did not commit)"
    assert push.returncode == 0, (
        f"pushdata failed: stdout={push.stdout!r} stderr={push.stderr!r}"
    )
    push_outputs_path = tmp_path / "output_push"
    push_outputs: dict[str, str] = {}
    if push_outputs_path.exists():
        for line in push_outputs_path.read_text().splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                push_outputs[k] = v  # last write wins, matching GITHUB_OUTPUT
    assert push_outputs.get("published") == "true", (
        f"published should be 'true' (last value in GITHUB_OUTPUT), got "
        f"{push_outputs!r}; full stdout={push.stdout!r} stderr={push.stderr!r}"
    )

    # 2. BYTES — the carved bytes survived in the worktree. On a52f5ad8 the
    #    conflict (race=conflicted) destroys the dirty bytes; the message below
    #    states the original local claim bytes were lost.
    worktree_claims_hash = subprocess.run(
        ["git", "hash-object", "--no-filters", "--",
         str(h["repo"] / "data/qledger/claims.jsonl")],
        cwd=h["repo"], env=_git_env(),
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    assert worktree_claims_hash == h["deferred_claims"], (
        f"worktree claims hash {worktree_claims_hash} != deferred "
        f"{h['deferred_claims']}; the original local claim bytes were lost — "
        f"the carve-out must NEVER drop, stash-drop, hard-reset or silently "
        f"issue the freshly-collected claims append"
    )
    assert (h["repo"] / "data" / "qledger" / "claims.jsonl").stat().st_size == _LIMIT + 4096, (
        f"worktree claims size != _LIMIT + 4096; the carve-out reverted or "
        f"truncated the file"
    )
    worktree_twin_hash = subprocess.run(
        ["git", "hash-object", "--no-filters", "--",
         str(h["repo"] / "site/qledger/track_record.json")],
        cwd=h["repo"], env=_git_env(),
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    assert worktree_twin_hash == h["deferred_twin"], (
        f"worktree twin hash {worktree_twin_hash} != deferred {h['deferred_twin']}"
    )
    if race == "reset":
        # The conflicted re-apply discarding the dirty CS manifest is
        # push_retry.sh's pre-existing behaviour (out of scope); pinning the
        # exact post-reset content pins the premise that the reset happened.
        assert (h["repo"] / "data" / "capital_structure"
                / "source_manifest.jsonl").read_bytes() == b"racer-cs\n", (
            "race=reset: the CS manifest should hold the racer's bytes after "
            "push_autostash_ok's hard reset"
        )
    else:
        assert (h["repo"] / "data" / "capital_structure"
                / "source_manifest.jsonl").read_bytes() == b"m2\n", (
            "the CS carve-out must keep its local bytes untouched in the worktree"
        )

    # 3. push stdout+stderr must not contain autostash-conflict markers — the
    #    park step is what isolates the carved bytes from --autostash. The
    #    reset race instead REQUIRES the marker: it exists to prove the claims
    #    survive a real hard reset.
    push_text = (push.stdout or "") + (push.stderr or "")
    if race == "reset":
        assert "conflicted autostash apply" in push_text, (
            f"race=reset: the harness failed to force the conflicted autostash "
            f"apply / hard reset this race exists to prove. Output: {push_text!r}"
        )
    else:
        assert "autostash-conflict" not in push_text, (
            f"pushdata reported autostash-conflict; the park step failed to "
            f"isolate the carved bytes from --autostash. Output: {push_text!r}"
        )
        assert "conflicted autostash apply" not in push_text, (
            f"pushdata reset hard after a conflicted autostash apply; the carve "
            f"bytes would be silently destroyed. Output: {push_text!r}"
        )

    # 4. Origin's main has the expected blobs.
    main_market = subprocess.run(
        ["git", "--git-dir", str(h["origin"]), "show",
         "main:data/baskets/ohlcv/NVDA.parquet"],
        capture_output=True, check=True,
    ).stdout
    assert main_market == b"v2", (
        f"market blob at origin main was {main_market!r}; the market plane "
        f"must publish even when qledger is carved out"
    )
    racer_tip = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=h["racer"], env=_git_env(),
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    ancestor = subprocess.run(
        ["git", "--git-dir", str(h["origin"]), "merge-base", "--is-ancestor",
         racer_tip, "main"],
        capture_output=True,
    )
    assert ancestor.returncode == 0, (
        f"racer tip {racer_tip} is NOT an ancestor of origin main; the "
        f"market lane did not actually pick up the racer's race commit"
    )
    main_claims = subprocess.run(
        ["git", "--git-dir", str(h["origin"]), "show",
         "main:data/qledger/claims.jsonl"],
        capture_output=True, check=True,
    ).stdout
    assert main_claims == h["claims_at_base"], (
        f"main claims != base claims (the carve-out must NOT publish the "
        f"deferred bytes); main={main_claims!r} base={h['claims_at_base']!r}"
    )
    main_twin = subprocess.run(
        ["git", "--git-dir", str(h["origin"]), "show",
         "main:site/qledger/track_record.json"],
        capture_output=True, check=True,
    ).stdout
    expected_twin_main = (
        b'{"racer":2}' if race == "conflicted" else h["twin_at_base"]
    )
    assert main_twin == expected_twin_main, (
        f"main twin mismatch for race={race!r}: got {main_twin!r}, "
        f"want {expected_twin_main!r}"
    )
    if race == "reset":
        main_cs = subprocess.run(
            ["git", "--git-dir", str(h["origin"]), "show",
             "main:data/capital_structure/source_manifest.jsonl"],
            capture_output=True, check=True,
        ).stdout
        assert main_cs == b"racer-cs\n", (
            f"race=reset: origin main CS manifest should be the racer's, got "
            f"{main_cs!r}"
        )

    # 5. Every blob in main's tree (above base) must NOT include the deferred
    #    blobs and must not exceed _LIMIT (GH001 invariant).
    objects = subprocess.run(
        ["git", "--git-dir", str(h["origin"]), "rev-list", "--objects",
         f"{h['base_sha']}..main"],
        capture_output=True, text=True, check=True,
    ).stdout
    seen_blobs: set[tuple[str, int]] = set()
    for line in objects.splitlines():
        parts = line.split(" ", 1)
        if len(parts) < 2:
            continue
        oid = parts[0]
        kind_proc = subprocess.run(
            ["git", "--git-dir", str(h["origin"]), "cat-file", "-t", oid],
            capture_output=True, text=True, check=True,
        )
        if kind_proc.stdout.strip() != "blob":
            continue
        size_proc = subprocess.run(
            ["git", "--git-dir", str(h["origin"]), "cat-file", "-s", oid],
            capture_output=True, text=True, check=True,
        )
        seen_blobs.add((oid, int(size_proc.stdout.strip())))
    assert (h["deferred_claims"], _LIMIT + 4096) not in seen_blobs, (
        f"main contains the deferred claims blob — the carve-out must NOT "
        f"publish it"
    )
    assert (h["deferred_twin"], len(b'{"n":1}')) not in seen_blobs, (
        f"main contains the deferred twin blob — the carve-out must NOT "
        f"publish it"
    )
    oversized = [(o, s) for o, s in seen_blobs if s > _LIMIT]
    assert not oversized, f"main has oversized blobs (>_LIMIT): {oversized}"

    # 6. Snapshot commit id is ABSENT from origin (runner-local, never pushed).
    snap_check = subprocess.run(
        ["git", "--git-dir", str(h["origin"]), "cat-file", "-e", h["snapshot"]],
        capture_output=True,
    )
    assert snap_check.returncode != 0, (
        f"snapshot commit {h['snapshot']} leaked to origin — the carve-out's "
        f"runner-local object store is not isolated"
    )

    # 7. Nothing staged in the repo after the carve+custody flow.
    staged = subprocess.run(
        ["git", "diff", "--cached", "--quiet"], cwd=h["repo"], env=_git_env(),
    )
    assert staged.returncode == 0, (
        "the repo has staged changes after the carve+custody flow; "
        "`git diff --cached` should be empty"
    )

    # 8. Signal — the restore step emitted the not-published warning AND the
    #    step summary AND nothing in the whole flow escalated to ::error.
    restore = h["procs"].get("restore")
    assert restore is not None, (
        "T1 requires the restore step (QLEDGER_RESTORE_STEP); the carve-custody "
        "guard cannot run without it. On a52f5ad8 this is the RED that motivates "
        "Edits A + B + C."
    )
    restore_text = (restore.stdout or "") + (restore.stderr or "")
    assert "::warning title=qledger carve-out not published::" in restore_text, (
        f"restore step did not emit the not-published warning; output: "
        f"{restore_text!r}"
    )
    assert "data/qledger/claims.jsonl" in restore_text, (
        f"restore step did not name the lost path; output: {restore_text!r}"
    )
    summary_text = (
        h["summary_path"].read_text() if h["summary_path"].exists() else ""
    )
    assert "### QLedger carve-out" in summary_text, (
        f"step summary missing the carve-out header; got: {summary_text!r}"
    )
    assert h["snapshot"] in summary_text, (
        f"step summary missing the snapshot id {h['snapshot']}; got: "
        f"{summary_text!r}"
    )
    for name, proc in h["procs"].items():
        text = (proc.stdout or "") + (proc.stderr or "")
        assert "::error" not in text, (
            f"{name} step emitted ::error; the carve-out must NEVER fail the "
            f"job (capital_structure and government_revenue_projection need "
            f"collect to succeed). Output: {text!r}"
        )


def test_qledger_carve_custody_steps_are_wired(collect_steps):
    """The park + restore steps must exist, sit in the right place in the
    workflow, and have the exact gates / env wiring from Edits B and C."""
    commit_idx = _index_of(collect_steps, MARKET_COMMIT_STEP)
    push_idx = _index_of(collect_steps, MARKET_PUSH_STEP)
    salvage_idx = _index_of(collect_steps, SALVAGE_PUSH_STEP)
    handoff_idx = _index_of(collect_steps, HANDOFF_STAMP_STEP)

    park_idx = _index_of_absent(collect_steps, QLEDGER_PARK_STEP)
    restore_idx = _index_of_absent(collect_steps, QLEDGER_RESTORE_STEP)

    assert park_idx is not None, (
        f"missing step: {QLEDGER_PARK_STEP!r} (Edit B must be applied)"
    )
    assert restore_idx is not None, (
        f"missing step: {QLEDGER_RESTORE_STEP!r} (Edit C must be applied)"
    )

    # Order — park sits between commitdata and pushdata; restore sits between
    # salvage-push and the capital-structure handoff (test_salvage_push_covers_
    # the_market_commit requires salvage == push+1, so restore cannot displace
    # salvage).
    assert park_idx > commit_idx, "park must follow commit market data"
    assert park_idx < push_idx, "park must precede push market data"
    assert restore_idx > salvage_idx, (
        "restore must follow the salvage push (salvage must stay directly after "
        "pushdata — test_salvage_push_covers_the_market_commit pins that order)"
    )
    assert restore_idx < handoff_idx, (
        "restore must precede stamp the capital-structure handoff receipt"
    )

    park_step = collect_steps[park_idx]
    restore_step = collect_steps[restore_idx]
    assert park_step.get("id") == "park", (
        "park must carry `id: park` so the push and salvage gates can read "
        "steps.park.outputs.parked (#9556 review 5570764032)"
    )

    # Gate text — EXACTLY the strings in Edits B / C.
    expected_park_if = (
        "always() && steps.commitdata.outputs.committed == 'true' && "
        "steps.commitdata.outputs.qledger_snapshot != ''"
    )
    expected_restore_if = (
        "always() && steps.commitdata.outputs.qledger_snapshot != ''"
    )
    assert park_step.get("if") == expected_park_if, (
        f"park if: mismatch; got {park_step.get('if')!r}, want "
        f"{expected_park_if!r}"
    )
    assert restore_step.get("if") == expected_restore_if, (
        f"restore if: mismatch; got {restore_step.get('if')!r}, want "
        f"{expected_restore_if!r}"
    )

    # Env — both reference the same commitdata output.
    park_env = park_step.get("env") or {}
    restore_env = restore_step.get("env") or {}
    assert park_env.get("QLEDGER_SNAPSHOT") == (
        "${{ steps.commitdata.outputs.qledger_snapshot }}"
    ), (
        f"park env QLEDGER_SNAPSHOT mismatch; got "
        f"{park_env.get('QLEDGER_SNAPSHOT')!r}"
    )
    assert restore_env.get("QLEDGER_SNAPSHOT") == (
        "${{ steps.commitdata.outputs.qledger_snapshot }}"
    ), (
        f"restore env QLEDGER_SNAPSHOT mismatch; got "
        f"{restore_env.get('QLEDGER_SNAPSHOT')!r}"
    )

    # Run bodies must not stage/commit/push/stash/reset-hard nor fail the job.
    park_run = str(park_step.get("run") or "")
    restore_run = str(restore_step.get("run") or "")
    for forbidden in (
        "${{", "git add", "git commit", "git push", "git stash",
        "reset --hard", "exit 1",
    ):
        assert forbidden not in park_run, (
            f"park run contains forbidden {forbidden!r}"
        )
        assert forbidden not in restore_run, (
            f"restore run contains forbidden {forbidden!r}"
        )

    # commitdata must capture the snapshot BEFORE the carve-out reset and
    # write the qledger_snapshot= output line.
    commit_run = str(collect_steps[commit_idx].get("run") or "")
    snap_idx = commit_run.find("qledger_snapshot=$(git commit-tree")
    reset_idx = commit_run.find("git reset -q -- data/qledger site/qledger")
    assert snap_idx != -1, (
        "commitdata does not write qledger_snapshot via `git commit-tree`; "
        "Edit A's snapshot line is missing"
    )
    assert reset_idx != -1, (
        "commitdata missing the qledger carve-out `git reset -q -- "
        "data/qledger site/qledger` line"
    )
    assert snap_idx < reset_idx, (
        f"the snapshot must be captured BEFORE the carve-out reset "
        f"(snapshot at {snap_idx}, reset at {reset_idx})"
    )
    assert "qledger_snapshot=" in commit_run, (
        "commitdata does not write `qledger_snapshot=` to GITHUB_OUTPUT"
    )


def test_qledger_carve_custody_reports_a_lost_path_without_failing(
    tmp_path, collect_steps,
):
    """When the restore step cannot write a path (claims.jsonl replaced by a
    directory mid-flow), it must report LOST via ::error AND step summary AND
    exit 0 — the carve-custody guard never fails the collect job, because
    capital_structure and government_revenue_projection need collect to
    succeed."""
    def mutate(repo):
        (repo / "data" / "baskets" / "ohlcv" / "NVDA.parquet").write_bytes(b"v2")
        _grow(repo / "data" / "qledger" / "claims.jsonl", _LIMIT + 4096)
        (repo / "site" / "qledger" / "track_record.json").write_bytes(b'{"n":1}')

    commit_proc, commit_outputs, repo = _run_market_commit(
        tmp_path, collect_steps, mutate, seed=_carve_seed_gitattributes,
    )
    assert commit_proc.returncode == 0
    assert commit_outputs.get("qledger_carved") == "true"
    snapshot = commit_outputs.get("qledger_snapshot", "")
    assert snapshot, "commitdata did not write qledger_snapshot"

    # Replace claims.jsonl with a DIRECTORY mid-flow. hash-object on a
    # directory fails, the cat-file write fails, so the path is LOST.
    claims_path = repo / "data" / "qledger" / "claims.jsonl"
    claims_path.unlink()
    claims_path.mkdir()
    (claims_path / "sentinel").write_text("placeholder\n")

    restore_run = _carve_step_body(collect_steps, QLEDGER_RESTORE_STEP)
    assert restore_run is not None, "restore step missing"
    summary_path = tmp_path / "summary_lost.md"
    env = _make_step_env(tmp_path, summary_path, snapshot)
    env["GITHUB_OUTPUT"] = str(tmp_path / "output_restore_lost")
    proc = _run_step(restore_run, repo, env)

    assert proc.returncode == 0, (
        f"restore step must NEVER fail the collect job; got "
        f"stdout={proc.stdout!r} stderr={proc.stderr!r}"
    )
    text = (proc.stdout or "") + (proc.stderr or "")
    assert "::error title=qledger carve custody LOST::" in text, (
        f"restore step did not emit the LOST ::error; output: {text!r}"
    )
    assert "data/qledger/claims.jsonl" in text, (
        f"restore step did not name the lost path; output: {text!r}"
    )
    summary = summary_path.read_text() if summary_path.exists() else ""
    assert "LOST" in summary, f"step summary missing the LOST marker: {summary!r}"
    assert "data/qledger/claims.jsonl" in summary, (
        f"step summary missing the claims path: {summary!r}"
    )
    # The twin (track_record.json) was restorable and must appear in BOTH the
    # warning AND as a successful restore in the worktree.
    twin_bytes = (repo / "site" / "qledger" / "track_record.json").read_bytes()
    assert twin_bytes == b'{"n":1}', (
        f"twin (track_record.json) was not restored byte-identical: "
        f"{twin_bytes!r}"
    )
    assert "site/qledger/track_record.json" in text, (
        f"restore step did not list the twin in the warning; output: {text!r}"
    )


def test_qledger_carve_custody_restores_on_a_deferred_only_night(
    tmp_path, collect_steps,
):
    """A night with ONLY the qledger oversize (no other market change) leaves
    commitdata at committed=false but still carves + snapshots the qledger
    bytes. The restore step must run regardless of pushdata, and must bring
    the carved bytes back."""
    def mutate(repo):
        _grow(repo / "data" / "qledger" / "claims.jsonl", _LIMIT + 4096)

    commit_proc, commit_outputs, repo = _run_market_commit(
        tmp_path, collect_steps, mutate, seed=_carve_seed_gitattributes,
    )
    assert commit_proc.returncode == 0
    assert commit_outputs.get("committed") == "false", (
        f"deferred-only night: commitdata should NOT commit; got "
        f"{commit_outputs!r}"
    )
    assert commit_outputs.get("qledger_carved") == "true"
    snapshot = commit_outputs.get("qledger_snapshot", "")
    assert snapshot, (
        "deferred-only night should still snapshot the carved bytes — the "
        "snapshot is what the restore step restores from"
    )

    # Record the deferred hash BEFORE running restore.
    deferred_hash = subprocess.run(
        ["git", "hash-object", "--no-filters", "--",
         str(repo / "data/qledger/claims.jsonl")],
        cwd=repo, env=_git_env(),
        capture_output=True, text=True, check=True,
    ).stdout.strip()

    restore_run = _carve_step_body(collect_steps, QLEDGER_RESTORE_STEP)
    assert restore_run is not None, "restore step missing"
    summary_path = tmp_path / "summary_deferred.md"
    env = _make_step_env(tmp_path, summary_path, snapshot)
    env["GITHUB_OUTPUT"] = str(tmp_path / "output_restore_deferred")
    proc = _run_step(restore_run, repo, env)

    assert proc.returncode == 0, (
        f"restore step failed on deferred-only night: "
        f"stdout={proc.stdout!r} stderr={proc.stderr!r}"
    )

    # Worktree claims hash unchanged (= deferred).
    after_hash = subprocess.run(
        ["git", "hash-object", "--no-filters", "--",
         str(repo / "data/qledger/claims.jsonl")],
        cwd=repo, env=_git_env(),
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    assert after_hash == deferred_hash, (
        f"deferred-only night: worktree claims changed (before={deferred_hash}, "
        f"after={after_hash})"
    )

    # Warning + summary still surface the not-published signal.
    text = (proc.stdout or "") + (proc.stderr or "")
    assert "data/qledger/claims.jsonl" in text, (
        f"deferred-only: restore warning missing claims path; output: {text!r}"
    )
    summary = summary_path.read_text() if summary_path.exists() else ""
    assert "### QLedger carve-out" in summary, (
        f"deferred-only: step summary missing the carve-out header; got: "
        f"{summary!r}"
    )
    assert snapshot in summary, (
        f"deferred-only: step summary missing the snapshot id {snapshot}; "
        f"got: {summary!r}"
    )


# ── Negative control: a failed custody snapshot must fail CLOSED on publication ──
# (#9556 review comments 2026-10-19 05:56Z / 06:01Z). Without a snapshot the park
# and restore steps are skipped, so if commitdata still committed, `push market
# data` (gated on committed only) would run with the dirty qledger bytes riding
# its --autostash unprotected. The step must instead withhold the market commit.

_WITHHELD_ERROR = "::error title=market publication withheld (qledger carve snapshot failed)::"


def _eval_commitdata_gate(cond, outputs, *, cancelled, park_outputs=None):
    """Evaluate a collect-step `if:` that reads ONLY commitdata and park outputs
    plus always()/cancelled(). Fails loudly if the gate grew any other reference."""
    park_outputs = park_outputs or {}
    expr = re.sub(
        r"steps\.commitdata\.outputs\.([A-Za-z0-9_]+)",
        lambda m: repr(outputs.get(m.group(1), "")),
        str(cond),
    )
    expr = re.sub(
        r"steps\.park\.outputs\.([A-Za-z0-9_]+)",
        lambda m: repr(park_outputs.get(m.group(1), "")),
        expr,
    )
    expr = (
        expr.replace("always()", "True")
        .replace("cancelled()", "True" if cancelled else "False")
        .replace("&&", " and ")
        .replace("||", " or ")
    )
    assert "steps." not in expr and "${{" not in expr and "!" not in expr.replace("!=", ""), (
        f"gate grew a reference this evaluator does not model: {cond!r}"
    )
    return bool(eval(expr, {"__builtins__": {}}, {}))  # noqa: S307 - literal gate text only


def test_qledger_carve_snapshot_failure_withholds_market_publication(
    tmp_path, collect_steps, monkeypatch,
):
    """Shim ONLY `git commit-tree` to fail (simulated snapshot I/O refusal; every
    other git call passes through) and run the real commitdata body with the real
    .gitattributes and a committable market change. The step must exit 0 (collect
    stays green for capital_structure / government_revenue_projection), write no
    committed=true and no qledger_snapshot, write qledger_withheld=true, emit the
    withheld ::error + summary, and leave HEAD and the collected bytes untouched,
    so no push / salvage / park / restore gate can open."""
    real_git = shutil.which("git")
    assert real_git, "git not on PATH"
    shim_dir = tmp_path / "commit_tree_refused"
    shim_dir.mkdir()
    (shim_dir / "git").write_text(
        "#!/usr/bin/env bash\n"
        "for a in \"$@\"; do\n"
        "  if [ \"$a\" = \"commit-tree\" ]; then\n"
        "    echo \"shim: commit-tree refused (simulated snapshot failure)\" >&2\n"
        "    exit 128\n"
        "  fi\n"
        "done\n"
        f"exec \"{real_git}\" \"$@\"\n"
    )
    (shim_dir / "git").chmod(0o755)
    monkeypatch.setenv("PATH", f"{shim_dir}:{os.environ.get('PATH', '')}")
    summary_path = tmp_path / "step_summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary_path))

    watched = (
        "data/qledger/claims.jsonl",
        "site/qledger/track_record.json",
        "data/baskets/ohlcv/NVDA.parquet",
    )
    before = {}

    def mutate(repo):
        (repo / "data" / "baskets" / "ohlcv" / "NVDA.parquet").write_bytes(b"v2")
        _grow(repo / "data" / "qledger" / "claims.jsonl", _LIMIT + 4096)
        (repo / "site" / "qledger" / "track_record.json").write_bytes(b'{"n":1}')
        (repo / "data" / "capital_structure" / "source_manifest.jsonl").write_bytes(b"m2\n")
        (repo / "data" / "hk" / "x.csv").write_bytes(b"h2\n")
        before["HEAD"] = _git(repo, "rev-parse", "HEAD").stdout.strip()
        for rel in watched:
            before[rel] = _git(repo, "hash-object", "--no-filters", "--", rel).stdout.strip()

    proc, outputs, repo = _run_market_commit(
        tmp_path, collect_steps, mutate, seed=_carve_seed_gitattributes,
    )
    assert proc.returncode == 0, (
        f"commitdata must not fail the collect job: stdout={proc.stdout!r} stderr={proc.stderr!r}"
    )
    assert outputs.get("committed") != "true", (
        "commitdata committed the market data although the carve snapshot failed; "
        "`push market data` would then run with the dirty qledger bytes riding its "
        f"--autostash unprotected (outputs={outputs!r})"
    )
    assert "qledger_snapshot" not in outputs, f"no snapshot may be advertised: {outputs!r}"
    assert outputs.get("qledger_withheld") == "true", f"qledger_withheld missing: {outputs!r}"
    assert _git(repo, "rev-parse", "HEAD").stdout.strip() == before["HEAD"], (
        "a market commit was made on the withheld path"
    )

    # No publication gate downstream of commitdata can open on these outputs.
    push_cond = collect_steps[_index_of(collect_steps, MARKET_PUSH_STEP)].get("if")
    assert _eval_commitdata_gate(push_cond, {"committed": "true"}, cancelled=False), (
        f"evaluator sanity: the push gate should open on committed=true: {push_cond!r}"
    )
    for name, cancelled in (
        (MARKET_PUSH_STEP, False),
        (SALVAGE_PUSH_STEP, True),
        (QLEDGER_PARK_STEP, False),
        (QLEDGER_RESTORE_STEP, False),
    ):
        cond = collect_steps[_index_of(collect_steps, name)].get("if")
        assert not _eval_commitdata_gate(cond, outputs, cancelled=cancelled), (
            f"{name!r} would run on the withheld path: if={cond!r} outputs={outputs!r}"
        )

    # Collected bytes are left untouched (claims + twin + the market change).
    for rel in watched:
        now = _git(repo, "hash-object", "--no-filters", "--", rel).stdout.strip()
        assert now == before[rel], f"{rel} changed on the withheld path ({before[rel]} -> {now})"
    assert (repo / "data" / "qledger" / "claims.jsonl").stat().st_size == _LIMIT + 4096

    # Loud and honest: the ::error names BOTH planes; the summary says the same.
    assert _WITHHELD_ERROR in proc.stdout, f"withheld ::error missing: {proc.stdout!r}"
    assert "NEITHER market data NOR data/qledger + site/qledger is published" in proc.stdout
    assert "data/qledger/claims.jsonl" in proc.stdout
    summary = summary_path.read_text() if summary_path.exists() else ""
    assert "### Market publication withheld: qledger carve snapshot failed" in summary, (
        f"step summary missing the withheld block: {summary!r}"
    )


# ── Negative control: a park it cannot VERIFY must fail CLOSED on publication ──
# (#9556 review 5570764032). The park step used to warn and exit 0 when `git
# restore` failed, so `push market data` and its cancel salvage still fetched,
# rebased --autostash and pushed against the dirty carved qledger bytes.

_PARK_WITHHELD_ERROR = "::error title=market publication withheld (qledger park failed)::"
_PUBLISHER_MARKERS = ("git push", "push_do", "git pull", "git fetch")


@pytest.mark.parametrize("park_mode", ["refuse", "noop"])
def test_qledger_carve_park_failure_withholds_market_publication(
    tmp_path, collect_steps, monkeypatch, park_mode,
):
    """#9556 review 5570764032: a failed park must open NO publisher step. Real
    git, real commitdata + park + restore bodies; the shim faults only the park
    step's `git restore`. refuse = the restore exits 74 (I/O refusal); noop = the
    restore exits 0 but changes nothing (a restore that lies), so only a VERIFIED
    parked state may open the push and salvage gates. The market commit stays
    local, origin is untouched, and the carved bytes survive for the restore step."""
    h = _run_carve_publish(
        tmp_path, collect_steps, monkeypatch, race="clean", park_mode=park_mode,
    )
    procs = h["procs"]
    park_outputs = h["park_outputs"]

    # 1. No publisher step executed on a failed park.
    assert "push" not in procs, (
        f"push market data ran although the park failed ({park_mode}); it fetched/"
        f"rebased/pushed against dirty carved qledger bytes. park_outputs={park_outputs!r}"
    )
    # 2-3. The park reported failure and did not fail the job.
    assert park_outputs.get("parked") != "true", f"park claimed success: {park_outputs!r}"
    park = procs.get("park")
    assert park is not None, "park step did not run"
    assert park.returncode == 0, (
        f"park must never fail the job: stdout={park.stdout!r} stderr={park.stderr!r}"
    )

    # 4. Neither publisher gate opens on these outputs; both open on a verified park.
    for name, cancelled in ((MARKET_PUSH_STEP, False), (SALVAGE_PUSH_STEP, True)):
        cond = collect_steps[_index_of(collect_steps, name)].get("if")
        assert not _eval_commitdata_gate(
            cond, h["commit_outputs"], cancelled=cancelled, park_outputs=park_outputs,
        ), f"{name!r} would run after a failed park: if={cond!r}"
        assert _eval_commitdata_gate(
            cond, h["commit_outputs"], cancelled=cancelled, park_outputs={"parked": "true"},
        ), f"evaluator sanity: {name!r} should open on a verified park: if={cond!r}"

    # 5. Every publisher after the park is one of the two gated steps.
    park_idx = _index_of(collect_steps, QLEDGER_PARK_STEP)
    publishers = {
        str(step.get("name") or "")
        for step in collect_steps[park_idx + 1:]
        if any(marker in str(step.get("run") or "") for marker in _PUBLISHER_MARKERS)
    }
    gated = {
        str(collect_steps[_index_of(collect_steps, MARKET_PUSH_STEP)].get("name")),
        str(collect_steps[_index_of(collect_steps, SALVAGE_PUSH_STEP)].get("name")),
    }
    assert publishers == gated, (
        f"publisher steps after the park must be exactly the gated push + salvage; "
        f"got {sorted(publishers)!r}"
    )

    # 6. Nothing reached origin; the market commit stays runner-local.
    origin_main = subprocess.run(
        ["git", "rev-parse", "refs/heads/main"], cwd=h["origin"], env=_git_env(),
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    assert origin_main == h["base_sha"], f"origin main moved: {origin_main} != {h['base_sha']}"
    assert (tmp_path / "push_count").read_text().strip() == "0", "a git push ran"
    assert _git(h["repo"], "rev-parse", "HEAD").stdout.strip() == h["head_sha"]

    # 7. Loud and honest: the ::error and the summary name BOTH planes.
    assert _PARK_WITHHELD_ERROR in park.stdout, f"park withheld ::error missing: {park.stdout!r}"
    assert "NEITHER market data NOR data/qledger + site/qledger is published" in park.stdout
    summary = h["summary_path"].read_text() if h["summary_path"].exists() else ""
    assert "### Market publication withheld: qledger park failed" in summary, (
        f"step summary missing the park-withheld block: {summary!r}"
    )

    # 8. The restore step ran and the carved bytes are preserved byte-identical.
    restore = procs.get("restore")
    assert restore is not None, "restore step did not run"
    restore_text = (restore.stdout or "") + (restore.stderr or "")
    assert "qledger carve custody LOST" not in restore_text, restore_text
    for rel, want in (
        ("data/qledger/claims.jsonl", h["deferred_claims"]),
        ("site/qledger/track_record.json", h["deferred_twin"]),
    ):
        have = _git(h["repo"], "hash-object", "--no-filters", "--", rel).stdout.strip()
        assert have == want, f"{rel} bytes changed after a failed park ({want} -> {have})"
    assert (h["repo"] / "data" / "qledger" / "claims.jsonl").stat().st_size == _LIMIT + 4096
