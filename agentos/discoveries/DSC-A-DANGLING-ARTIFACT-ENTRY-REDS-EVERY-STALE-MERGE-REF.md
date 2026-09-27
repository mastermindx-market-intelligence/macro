---
key: A-DANGLING-ARTIFACT-ENTRY-REDS-EVERY-STALE-MERGE-REF
claim: >
  One AgentOS record `artifacts:` entry naming a file that is on `origin/main` but not
  on a pull request's merge ref reds that pull request's pack - even when the pull
  request touches nothing under `agentos/` and belongs to a different program. The
  validator reports a phantom artifact as a `::warning` and still exits 0, because
  in-repo and cross-repo artifact joins fail OPEN, so `scripts/agentos.py validate`
  saying `0 error(s)` is not a clear signal. The refusal comes from `self-mod-fence`,
  which is one of the two ALWAYS-ON unscoped jobs, through
  `tests/test_agentos_schema.py::test_cross_repo_path_is_unchecked_when_that_checkout_is_absent`
  - a negative assertion that the string `phantom-artifact` appears nowhere in the
  validator's output over a copy of the whole real store. The scope of the assertion is
  therefore the entire store, while the scope of the failing pull request's diff is
  irrelevant. Measured twice in one night on two independent programs.
falsifier: >
  For the red pull request, show the named path present in BOTH refs, or the entry
  absent from `origin/main`'s copy of the record: `git ls-tree --name-only origin/main
  -- <path>` plus `grep -n "<path>" <record at origin/main>`, then
  `git fetch origin 'refs/pull/<N>/merge:refs/tmp/x' --force` and
  `git ls-tree --name-only refs/tmp/x -- <path>`. Present in both refs disproves the
  staleness explanation and makes the red something else. Absent from `origin/main`
  disproves "main is not red" and means the entry itself is wrong and every pull
  request in the repository is reddened until it is removed. The claim about
  `validate` is falsified by any run where a phantom artifact raises the exit code:
  `MACRO_MASTERMIND_REPO=/nonexistent MACRO_TERMINAL_REPO=/nonexistent python3
  scripts/agentos.py validate; echo $?`.
so_what: >
  Triage a `self-mod-fence` phantom-artifact red with TWO refs before touching any
  code, and never treat it as a defect in your own diff. Entry and file both present at
  `origin/main` while the file is absent from `refs/pull/<N>/merge` means main is NOT
  red, your base is stale, and the base is the entire cause. The cure is a base refresh
  - merge fresh `origin/main` into the branch so the `synchronize` event computes a new
  merge ref - and NOT a code change, NOT a record edit, and NOT a rerun: rerunning the
  failed job reuses the same frozen merge commit and reproduces the red. Prefer a local
  merge over `gh pr update-branch` so the commit carries the required trailer. Because
  the refresh moves the head, an adjudicated pull request must then show that nothing
  reviewed changed (`git diff --stat <adjudicated sha> HEAD -- <owned files>` empty for
  the real content) and say in its body that the head is the adjudicated sha plus one
  base merge, since the old sha is pinned in the review record, the checkpoint and any
  dependent rulings. On the writing side: an `artifacts:` entry may name only a file
  this pull request carries or one already on `origin/main`, never one a sibling is
  carrying - such an entry would red every pull request in the repository if it landed.
  Finally, this test is untrustworthy LOCALLY in both directions: it reds in a sparse
  worktree, where entries under `data/`, `site/`, `mockups/` and `verify_shots/` are
  omitted-but-tracked and so read as phantom, and it can pass locally on a machine that
  has the `charting-app`/`Mastermind` sibling checkouts CI lacks. Emulate CI with
  `MACRO_MASTERMIND_REPO=/nonexistent MACRO_TERMINAL_REPO=/nonexistent`, and confirm
  each local phantom against `git ls-tree origin/main` before believing it.
kind: landmine
verified_at: 2026-09-27
verified_by: >
  Two independent programs, one night, same test. (1) GMI Mining records PR #8060:
  `ci-pack-0` had selected exactly one job, `self-mod-fence`, whose step "agent-os
  record contract (schema fail-closed, join fail-open)" exited 1 on
  `test_cross_repo_path_is_unchecked_when_that_checkout_is_absent` with
  `AssertionError: 'phantom-artifact' not in result.stdout`; the phantom was that pull
  request's OWN workstream record naming a review file a still-in-flight sibling was
  carrying, which landed on main minutes later. (2) GMI Industrials T04 PR #8062, whose
  diff is three files and nothing under `agentos/`: run 36291553267 concluded `failure`
  with ELEVEN of twelve packs green and `ci-pack-8` red on the same test, from
  `agentos/workstreams/WS-GMI-MINING-M1-INTEGRATION.md:77` naming
  `research/mining/m1_integration_program/reviews/OPUS_T04A_PR_REVIEW_R3_2026-09-26.md`
  - a sibling seat's entry. Two-ref check: `git ls-tree --name-only origin/main`
  showed that file present on main and the entry present in the record at main, while
  `refs/pull/8062/merge` did not carry it; the branch was 32 commits behind. A local
  merge of `origin/main` produced `cd46f9452c77`, the module and its suite diffed EMPTY
  against the adjudicated `0e3344a9071f`, and rerun 36296953418 concluded SUCCESS with
  `ci-gate` and all twelve packs green. Also measured: with nine phantom warnings in the
  store (all under the sparse-omitted trees, all nine confirmed present at
  `origin/main`), `scripts/agentos.py validate` reported `1304 records - 0 error(s),
  109 warning(s)` while `tests/test_agentos_schema.py` reported `1 failed, 75 passed`.
scope: [macro, agentos, ci-packs, all-programs]
confidence: verified
---

## Detail

Two properties combine into a fleet-wide coupling that neither one has alone.

**The join fails open, so the validator cannot be the gate.** A missing in-repo or
cross-repo artifact is reported as a warning and does not change the exit code. This is
deliberate - a record must not hard-fail because a sibling checkout is absent - and it
means a seat that runs `validate` after every edit, sees `0 error(s)` every time, and
concludes the store is clean is reasoning correctly from an instrument that was never
designed to answer this question.

**The test's scope is the whole store, so the pull request's scope is irrelevant.**
`self-mod-fence` is unscoped and always-on, and the assertion is a NEGATIVE one over
global output: the string `phantom-artifact` must appear nowhere. A negative assertion
is satisfied or broken by anything in range, and the range here is every record in
`agentos/`. That is why a pull request touching three engine and test files was reddened
by a Mining workstream record: the phantom is in range of the assertion and the diff is
not.

**The frozen merge ref is what makes it a base-staleness bug rather than a real one.**
CI tests `refs/pull/<N>/merge`, computed when the branch last changed. A sibling's file
landing on main afterwards does not advance it. So the store as CI sees it is your stale
base's store, which contains the sibling's entry but not the sibling's file. Main itself
is fine, every fresh pull request is fine, and only the pull requests whose merge refs
predate the file are red - which is why this presents as an inexplicable single-pack red
on an unrelated change.

The three wrong moves, in the order they are tempting: rerun the job (same merge
commit, same red), edit your own record (nothing is wrong with it), or edit the
sibling's record (you would be removing a now-valid entry to work around your own stale
base, and a sibling seat may be mid-flight on it). The right move is a base refresh,
which also converts the eventual green into proof against the CURRENT base rather than
against a base 32 commits back.

**Cost of not knowing this.** On #8060 the seat read the red, drew a fleet-wide
conclusion about main being broken, and spent the investigation there. On #8062 the
two-ref check settled ownership in two commands, and the cure was one merge - but the
same red on an adjudicated head also forced a head change that had to be reconciled
against a sha pinned in four places.

Related: `DSC:A-LANE-SELF-VERDICT-IS-NOT-A-CLOSURE-GATE` is the other T04 measurement
from the same pull request. The base-staleness family also includes the case where a
green proof against a stale base is not proof at all - the same frozen merge ref, read
from the other direction.
