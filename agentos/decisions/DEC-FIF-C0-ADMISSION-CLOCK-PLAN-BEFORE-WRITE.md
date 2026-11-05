---
key: FIF-C0-ADMISSION-CLOCK-PLAN-BEFORE-WRITE
question: >
  When the nightly FIF production dataset publisher re-runs and code, registry
  or mint output changed but no capture clock moved, which admission clock
  does the new generation get, and may the publisher write before it knows
  every issuer can publish?
answer: >
  Plan every eligible issuer before any real-store write. Per issuer, read the
  latest pointer L (an unverifiable pointer is the typed failure
  latest_pointer_unreadable, never "absent"). If a scratch-store build at
  L.admitted_at reproduces L.generation_id the outcome is `unchanged` and
  nothing is written. Otherwise the clock is the content clock T_c when
  T_c > L.published_at (clock_basis=content), else the run's --recorded-at T_r
  when T_r > L.published_at (clock_basis=run_recorded_at), else the typed
  refusal admission_clock_not_after_latest raised before any write. The
  future-clock refusal admitted_at_after_recorded_at still fires first. Only
  after every issuer's plan succeeds does the commit phase publish, in
  entity_id order; a commit-phase failure writes a partial report naming
  committed / failed / not-attempted issuers.
rationale: >
  generation_id hashes admitted_at and the lineage mint stamps the clock into
  role bytes. Re-using the unchanged content clock for changed content makes
  published_at <= latest.published_at, so the pointer refuses "stale
  production dataset cannot rewind" every night after already writing orphan
  objects. Deriving the clock from the run clock alone mints a new generation
  every night (churn). Plan-then-commit with a clock-independent unchanged
  test is the only shape that neither rewinds, churns, nor orphans.
alternatives:
  - option: Always use the content clock T_c.
    why_not: Changed code/registry output with no new capture rewinds and is refused nightly after orphan writes (the #9021 review BLOCKER).
  - option: Always use the run clock T_r.
    why_not: A new generation every night with identical content — churn that defeats unchanged detection and the newer-generation chip.
  - option: Split a pure plan function out of engine production_datasets.publish_production_dataset.
    why_not: Not authorized in this PR; production_datasets.py stays unowned. A scratch store gives the same plan safety without an engine split.
evidence:
  - "PR #9021 (squash 2b9b1cda2738) — scripts/publish_fif_production_datasets.py:922-980 implements the plan; typed code at :130; clock_basis set validated at :1269 (git grep -n admission_clock_not_after_latest origin/main -- scripts)."
  - "Seat ERRATA-3 (2026-10-12 ~19:2xZ) after an independent opus review of #9021 at 54f21ff8 found the rewind/orphan BLOCKER."
  - "Required hermetic tests (i)-(vii): unchanged rerun = zero real writes; changed output = T_r; no churn the night after; T_r <= L refuses with store byte-identical; first publication = T_c; new later capture = T_c; injected mid-commit fault = partial report."
affects:
  - WS:FINANCIAL-INTELLIGENCE-FABRIC
  - scripts/publish_fif_production_datasets.py
  - engine/fundamental_forensics/production_datasets.py
confidence: high
reversibility: costly
decided_by: "seat 96dc937a (FIF Meta-CEO, Chairman commission 2026-10-11)"
decided_at: 2026-10-12
---

# Plan every issuer before any write; the clock advances only when content changes

The rule exists because `generation_id` is a hash over a manifest core that
includes `admitted_at`. Any change to that clock changes the generation. Any
change to the content without a clock change would collide with the pointer's
no-rewind law.

Outcomes reported per issuer: `published` or `unchanged`, with `clock_basis` in
{content, run_recorded_at, latest_unchanged} and the chosen `admitted_at`.
`verify` accepts `unchanged` when latest.json names the reported generation.
