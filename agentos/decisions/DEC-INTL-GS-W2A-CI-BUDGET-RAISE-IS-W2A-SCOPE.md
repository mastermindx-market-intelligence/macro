---
key: INTL-GS-W2A-CI-BUDGET-RAISE-IS-W2A-SCOPE
question: >
  When the W2A scanner + coverage view made the international-workspace-browser legacy CI job exceed its
  12-minute pack budget on PR full-suite runs, whose scope was the budget change, and which form could it take?
answer: >
  W2A scope. The raise is a measured 12→20 minutes for the international-workspace-browser job in
  .github/ci/legacy-jobs.yml, carried in W2A #10288 together with its paired pack-semantic pin
  (tests/test_ci_pack_semantic.py asserts == 20; the test is renamed …international1200). Amendment c1: the
  international-dislocation-explorer 8→15 raise is #10341's (another author, merged 2026-10-31T20:08:34Z) and
  W2A takes it verbatim rather than re-raising it. A budget exemption for the job is refused. The structural
  cause — both international jobs do a full checkout AND a separate ~4-minute `git fetch origin main` on hosted
  runners — is deferred as F10 to its own PR (shallow / base-only fetch).
rationale: >
  The job's measured time grew because W2A added the scanner and coverage browser assertions the job exists to
  run; the budget is a pack-semantic contract, so the PR that changes the measured behaviour owns the measured
  raise and its pin, with the raise visible in the diff and the test. Exempting the job would hide a real cost;
  fixing the fetch path is a CI-structure change that touches another author's job and belongs to a dedicated,
  separately reviewable PR.
alternatives:
  - option: Exempt the international-workspace-browser job from the pack budget.
    why_not: Removes the only enforced signal of job cost; refused.
  - option: Fix the structural cause now (shallow / base-only fetch for both international jobs) inside W2A.
    why_not: >
      Touches CI structure and another author's job (dislocation-explorer, #10341) beyond W2A's measured
      change; deferred as F10 to its own PR so it can be reviewed on its own merits.
  - option: Measured raise 12→20 with the paired pack-semantic pin, carried by W2A (chosen).
    why_not: n/a — chosen.
evidence:
  - "W2A #10288 (head 74e28ce960bfe2608de1aeeeba8221f75a73e4a2 → main 92881169bb888435ab84b40740212a1fb0876a77, 2026-10-31T21:54:40Z; gh api graphql pullRequest(number:10288) → MERGED, read 2026-11-01)"
  - "#10341 ci(legacy-jobs): raise international-dislocation-explorer budget 8 -> 15 min (head 51b16608d57592b52d6c4b93877d65b2590a7c95 → dbaf1e07bcccf689a740ad3f1281c59ff1b9d946, 2026-10-31T20:08:34Z; same batched read)"
  - "Review record INTL-GS-W2A PASS_WITH_NOTES at head (seat kit; seat-attested)"
  - "Seat ruling 2026-10-31 recorded in the continuation handoff checkpoint 2026-10-31 21:5x–23:0xZ (records r8) and the seat lane ledger F10 entry (seat kit)"
affects:
  - "WS:INTL-GLOBAL-SURVEILLANCE"
  - ".github/ci/legacy-jobs.yml (international-workspace-browser budget 12→20)"
  - "tests/test_ci_pack_semantic.py (budget pin == 20)"
  - "deferred F10 — structural fetch fix for both international legacy jobs (own PR)"
confidence: high
reversibility: easy
decided_by: fable-meta-ceo-seat-d7c4f490
decided_at: 2026-10-31
review_by: 2026-11-30
---

## Scope

Binds the ownership and the form of the international-workspace-browser CI budget change made during the W2A
landing. It does not change any other job's budget, does not exempt any job from the pack-budget contract, and
does not decide the structural fetch fix (F10), which remains open in its own PR.

## Options considered

Exempt the job (refused); fix the structural fetch cause inside W2A (deferred as F10 — crosses into another
author's job and CI structure); a measured raise 12→20 with its paired pack-semantic pin carried by W2A (ruled).
Amendment c1: the dislocation-explorer 8→15 raise is #10341's and is taken verbatim.

## Consequences

- W2A #10288 carries the budget line and the `== 20` pin together; contract-delta stays 0 / 0 because the pin
  and the budget move in one PR.
- The dislocation-explorer budget (15) is #10341's fact; W2A neither restates nor re-raises it.
- F10 stays a named deferred item: a shallow / base-only fetch for both international jobs, own PR, own review.

## Provenance

Seat ruling of 2026-10-31 (Fable Meta-CEO seat d7c4f490), recorded in this records PR (r8) and in the
continuation handoff checkpoint "2026-10-31 21:5x–23:0xZ — W2A + records r7 MERGED".
