---
key: CDV1-PLAN-SEAM-RULINGS
question: >
  How does the CDV-1 implementation reconcile the frozen plan with the code
  seams the Opus audit found different?
answer: >
  Adopt all nineteen Opus seam-audit findings as binding packet rulings. Keep
  the frozen plan’s product intent, but implement through the production seams:
  PG-only `acquire_results_filing` reuses the production discovery helpers;
  a latin-1 fallback is `decode_failure` for PG evidence; `pg_profile(*,
  fiscal_scope)` is created per event and a prior-period `period` is the ISO
  prior end date; `validate_selected_facts` is new code that filters the `pg_`
  namespace; PG private facts use the private rights profile;
  `prepare_pg_workspace` stamps `generation_id` and carries `generated_at`
  forward; the Task 5 hook is inserted after `_write_context_manifest` in
  `publish_public_wire`, with `scripts/publish_earnings_private_store.py`
  reading the prior closure, and Task 4 lands first; the producer exposes an
  explicitly disabled `--economic-augment` flag while v1 constants remain
  untouched and use explicit v2 constants; artifact validation is per-role and
  v2-only; the v2 pointer uses
  `StrictConditionalWriteStore.put_bytes_strict_conditional`, never a
  best-effort restore; the evidence route is registered above the API catch-all
  with an auth-gated `/economic/{remainder:path}` sibling; the
  `economic_client` fixture uses `LocalStore`, the real publisher and
  `_reset_private_caches()`; and both new paid paths are added to
  `_MOUNTED_PAID_PATHS`.
rationale: >
  The plan was written from search snippets, while the checked-in code is the
  truth of the available seams. Each ruling preserves the plan’s intended
  invariant—native source discipline, exact evidence closure, private safety,
  and reader-first release—while fitting the incumbent owner and the seam that
  production actually exercises. This also protects the frozen plan from being
  silently diluted by an unused discovery path, lossy decoding, non-atomic
  publication, route shadowing, stale fixture caching, or unmounted paid probes.
alternatives:
  - option: Rewrite the frozen implementation plan before any task starts.
    why_not: >
      It would be slower and unnecessary while the research carrier is HOLD; the
      adopted audit rulings reconcile execution to the actual code without
      reopening the product design.
  - option: Follow the plan literally despite the audit.
    why_not: >
      The intended Task 5 hook would not exist at the planned location, stage
      handling would reject unknown files, publication could be non-atomic, and
      evidence probes could bypass authentication.
evidence:
  - "research/consumer_defensive/cdv1_program/reviews/OPUS_PLAN_SEAM_AUDIT_2026-09-24.md findings F1–F19"
  - "Macro PR #7880 merge head c52d80a1cc7a merged the program ledger and audit"
  - "git merge-base --is-ancestor c52d80a1cc7a origin/main; rc=0"
affects:
  - "WS:CONSUMER-DEFENSIVE-CDV1"
  - engine/company_intelligence/pg_profile.py
  - engine/company_intelligence/economic_observations.py
  - engine/earnings_narrative/economic_interpretation.py
  - engine/earnings_narrative/private_economic_stage.py
confidence: high
reversibility: easy
decided_by: fable-meta-ceo
decided_at: 2026-09-24
---

## Skeleton

## Binding rulings

1. **PG acquisition seam.** The PG-only `acquire_results_filing` path reuses the
   production discovery helpers so boundary, stated-period, candidate, and
   8-K/A behavior are not reimplemented divergently.
2. **Decode failure.** PG evidence records `utf-8` or a latin-1 fallback, and a
   fallback is treated as `decode_failure` for exact-evidence minting; legacy
   behavior remains byte-compatible outside PG.
3. **Scoped profile.** Construct `pg_profile(*, fiscal_scope)` per event, and
   represent prior-period `period` as the ISO prior end date.
4. **Native fact validation.** Add `validate_selected_facts` as new code,
   filtered to the `pg_` namespace, without pretending the existing workspace
   validator already covers native facts.
5. **Private rights.** Use the private rights profile for PG private-fact
   spans; do not derive a public rights profile from native private evidence.
6. **Preparation identity.** `prepare_pg_workspace` stamps `generation_id` and
   carries `generated_at` forward rather than minting unstable clock identity.
7. **Producer insertion.** Insert the Task 5 hook after `_write_context_manifest`
   inside `publish_public_wire`, not at the planned non-existent seam.
8. **Publisher closure.** `scripts/publish_earnings_private_store.py` is the
   prepare/publish caller and reads the prior closure for continuity.
9. **Task order.** Land Task 4 before Task 5 so v2 storage, validation and
   readers exist before refresh integration.
10. **Disabled producer.** Add the explicit `--economic-augment` flag only in a
    disabled default state; release the producer after readers.
11. **Constants.** Leave v1 constants untouched and introduce explicit v2
    constants rather than overloading the old schema.
12. **Validation version.** Validate artifacts by role and v2 contract only;
    do not impose native roles on v1 records.
13. **Atomic pointer.** Write the v2 pointer with
    `StrictConditionalWriteStore.put_bytes_strict_conditional`; never perform a
    best-effort restore after an uncertain v2 write.
14. **Stage closure.** Preserve the stage tree’s exact-closure behavior and make
    v2 members explicit members of the expected set.
15. **Object keys.** Extend object-key/receipt handling explicitly for v2
    native artifacts instead of forcing them through the JSON-only regex.
16. **Manifest evidence.** Preserve generation identity and use explicit v2
    fields for publication timing and evidence metadata.
17. **Route order.** Register the economic-evidence route above the records
    catch-all so FastAPI cannot shadow it.
18. **Auth catch-all and errors.** Add the auth-gated
    `/economic/{remainder:path}` catch-all and preserve the house private-error
    mapping, including generic failures as private 503s.
19. **Test infrastructure.** Build `economic_client` from `LocalStore` plus the
    real publisher, patch only `_build_store`, call `_reset_private_caches()`
    after publication, and add both new paths to `_MOUNTED_PAID_PATHS`.

## Reversibility

Each ruling remains revisable in its task PR before that task merges. After a
task merges, change it only through a superseding `DEC:*` record with new seam
evidence.
