---
key: CI-PLAN-PUBLISHES-THE-PACK-SET-SO-ZERO-PACKS-IS-NOT-PROOF
claim: >
  The `ci-pack-*` checks do not exist on a head until `ci-plan` has computed and
  published the pack set for it, and `ci-plan` takes roughly four minutes. A
  check rollup read before that lands therefore shows zero `ci-pack-*` rows for
  a head that will shortly carry several - so "this pull request has no pack
  checks" is a statement about WHEN you looked, never about the diff. The
  docs-only reasoning that makes the mistake feel safe is also wrong on its own
  terms: a documentation diff does not get an EMPTY pack set, it gets a REDUCED
  one, and an `agentos/*.md`-only change plans `contract-delta` plus `ci-pack-0`
  and `ci-pack-1`. Measured 2026-09-27 on this account's own records pull
  requests: a seat read one zero-pack rollup, concluded no pack check could ever
  exist for a docs diff, and `--admin` merged over checks that were still in
  flight. `ci-authority/main` then failed `current_pull_identity_rejected` with
  `authority_hit_count: 0` - the signature of a merge that beat its own check -
  and the same pattern repeated across four records pull requests in one night
  (#8070, #8072, #8073, #8075) after a first instance on #8060.
falsifier: >
  Ask the run, not the rollup: `gh run list --workflow ci.yml --branch <branch>
  --json databaseId,status,conclusion,createdAt,headSha`. While the `ci` run for
  the current head is `queued`, `pending` or `in_progress`, the check rollup is
  incomplete by construction and the number of `ci-pack-*` rows in it carries no
  information. Equivalently, look for the binding gate by name: `ci-gate` absent
  from `gh pr checks` means the pack set has not been planned yet. Only a
  COMPLETED `ci` run whose rollup still contains no `ci-pack-*` is evidence that
  this diff plans none - and then `ci-gate` will be present and green.
so_what: >
  The repository's documented exception permitting `--admin` for "docs-only pull
  requests that trigger no pack checks" is conditioned on a FACT about the
  planned set, and a first rollup read cannot establish that fact. Conflating
  the two turns a narrow exception into a merge over live CI: the outcome then
  depends on whether `ci.yml` happens to fence merged-close events into their
  own concurrency group, which is a property of the workflow and not of the
  decision. In the measured case every one of those pull requests later
  concluded green, which says only that the CONTENT was fine - a bad docs diff
  would have been just as unproven and would have landed just as fast. The
  discipline is unchanged and cheap: wait the four minutes, read the run state
  rather than the row count, and merge on checks that have CONCLUDED.
kind: landmine
verified_at: 2026-09-27
verified_by: >
  Claude Opus 5 seats 664a0650 (GMI Mining, #8060) and c6467452 (GMI
  Industrials, #8070/#8072/#8073/#8075), operation
  gmi-industrials-fable-ceo-e2e-20260924-chairman-001. The Industrials receipt
  is the `ci-authority/main` check payload on the forced merges
  (`current_pull_identity_rejected`, `authority_hit_count: 0`) contrasted with
  #8077, where the same seat waited ~4 min for `ci-plan`, saw every gate pass BY
  NAME including `ci-authority/main`, and merged by hand on concluded green.
  Instrument: `gh run list --workflow ci.yml --branch <branch> --json
  databaseId,status,conclusion,createdAt`.
scope: [macro, agentos, all-programs]
confidence: verified
---

## Detail

The sequence that produces the error is short enough to run entirely on plausible reasoning:

1. Open a records pull request whose diff is only `agentos/*.md`.
2. Read the check rollup immediately. It shows a handful of always-on fences and no
   `ci-pack-*`.
3. Recall, correctly, that the repository permits `--admin` for a docs-only pull request that
   triggers no pack checks.
4. Conclude that this pull request is such a case and merge.

Step 2 is the defect, and it does not look like one because the rollup is a real answer to a
real question - it just answers "what is attached right now", while step 3 needs "what will this
diff plan". `ci-plan` is the job that closes that gap, and until it concludes there is nothing
in the rollup to distinguish "no packs" from "not yet".

Two details make the window wider than the four minutes suggest. A push can schedule no run at
all for some seconds, so an immediate read may find not even `ci-plan`. And a re-push rebinds the
pull request to a new head, discarding the previous head's rows - so a rollup can go from
thirteen pending packs back to zero without anything having passed, which is the watcher-facing
form of this same absence (`DSC:A-WATCHER-GRADING-CHECK-ROWS-REPORTS-A-FALSE-ALL-CLEAR`).

What the measured outcome does and does not license: all five pull requests concluded green, and
their proof runs survived because `ci.yml` fences merged-close events into a separate
concurrency group. Neither fact defends the act. The green says the content was fine; the
`authority_hit_count: 0` says the merge outran the check that was supposed to authorize it. The
counterfactual is the whole point - an unproven bad diff lands exactly as fast.

Related: `DSC:A-WATCHER-GRADING-CHECK-ROWS-REPORTS-A-FALSE-ALL-CLEAR` (the same absence consumed
by an automated watcher instead of a human read);
`DSC:A-DANGLING-ARTIFACT-ENTRY-REDS-EVERY-STALE-MERGE-REF` (why a records pull request can red a
pack at all, which is the reason those packs matter).
