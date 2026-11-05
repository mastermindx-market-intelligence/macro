---
key: STALE-BASE-STARVES-CI-PACK-ANCESTRY-FETCH-INTO-CANCEL
claim: >
  A PR branch whose base is far enough behind main can make ci.yml conclude
  CANCELLED — never FAILED — with `ci-gate` reporting "semantic proof is blocking"
  over a pile of `unknown` units and ZERO `pr_regression` units. The mechanism:
  one ci-pack job cannot resolve ancestry at the checkout's fetch depth, logs
  `ancestry fetch failed at depth 2048; retrying legacy all-branches deepen`, and
  grinds on that fallback deepen until it is killed. A killed pack never writes its
  `pack-N.json` fragment, so `ci-gate` — which reconciles a semantic proof over the
  per-pack fragments and is fail-closed — cannot classify that pack's units and
  reports them as `unknown`, blocking. Measured 2026-09-29 on macro #7861: branch
  1043 commits behind main on a base predating the pack fetch repair (#7853);
  ci-pack-5 burned 73 minutes (19:18-20:31Z) in that retry and was cancelled;
  ci-gate read 267 passed / 46 unknown, and all 46 unknown belonged to ci-pack-5.
  This is DETERMINISTIC for a given base, so a plain rerun reproduces it exactly.
  Merging fresh origin/main into the branch fixed it outright: the very next run
  concluded SUCCESS with "complete semantic proof is clear".
falsifier: >
  A branch >1000 commits behind a post-#7853 main whose ci-pack jobs all conclude
  normally would show base age is no longer sufficient to trigger this, or that the
  fetch depth now covers it. Conversely a run cancelled this way whose ci-gate
  `unknown` set does NOT map onto the cancelled pack would mean the unknowns have a
  different cause and the base update is the wrong remedy. Check by reading the
  cancelled run's ci-gate summary counts, then `gh run view <id> --log-failed` for
  the literal `ancestry fetch failed at depth` line and which pack emitted it.
so_what: >
  Read CANCELLED as a possible INFRASTRUCTURE verdict, not as "someone cancelled it"
  and not as a red to be healed in the diff. The instinct on a blocking ci-gate is
  to hunt the failing test; here there is no failing test — `pr_regression` is zero
  and the diff is innocent. The cheap discriminator is the passed/unknown split plus
  how far behind main the branch sits, and the remedy is to update the base, not to
  rerun (a rerun repeats it) and not to touch the code. A session that misreads this
  can burn hours attributing an environmental cancel to its own change, and a held or
  armed PR can sit unmergeable over a run that never judged its content at all.
kind: landmine
verified_at: 2026-09-29
verified_by: "macro ci.yml runs 36601596875 and 36604938778 (cancelled) vs 36627834814 (success) on PR #7861; ci-gate summary counts; gh run view --log-failed"
scope:
  - macro
  - .github/ci/**
  - .github/workflows/ci.yml
confidence: verified
---

Two consecutive `ci.yml` runs on macro #7861 concluded `cancelled` while `ci-gate`
reported `semantic proof is blocking`. Neither run had judged the change: the proof
carried **zero** `pr_regression` units. The blocking set was 46 `unknown` units, and
every one of them belonged to `ci-pack-5`.

`ci-pack-5` had not failed a test. It spent 73 minutes repeating

```
ancestry fetch failed at depth 2048; retrying legacy all-branches deepen
```

and was killed before it could write `pack-5.json`. `ci-gate` reconciles its semantic
proof over the per-pack fragments and is deliberately fail-closed, so a pack that
never reports is `unknown`, and `unknown` blocks.

The cause was base **age**, not content. The branch sat 1043 commits behind `main` on
a base from 09-24 that predated #7853 (*"ci(pack): fetch the full tree instead of
lazily fetching every blob at checkout"*, merged 09-25). Because the base is fixed,
the failure is deterministic — a rerun reproduces it rather than clearing it.

Merging fresh `origin/main` into the branch resolved it in one step. Only
`.github/ci/legacy-jobs.yml` overlapped and auto-merged; all three adopted source
files stayed byte-identical (sha256 verified before and after), so nothing about the
change under review moved. The next run, 36627834814, concluded `success` with
`complete semantic proof is clear` and `contract-delta clear`.

Related: the CI PROMISOR FETCH TRUNCATION lane and #7853, which fixed the checkout
side of the same blobless/promisor fetch problem. This record is the *consumer-visible
symptom* of an un-updated base still carrying the pre-fix behaviour.
