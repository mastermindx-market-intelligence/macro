---
key: INVESTIGATION-VALIDATOR-ADMITTED-ONLY-THE-EARNINGS-EVIDENCE-OWNER
claim: >
  Until Terminal migration 0039, the installed Supabase function
  `valid_investigation_manifest_v2` admitted only the earnings evidence owner, so
  `apply_investigation_revision_v2` refused every saved revision that carried a
  reference from any other owner — including the Options evidence references the
  Terminal registry already accepted on the client.
falsifier: >
  Read the installed body with `select pg_get_functiondef('valid_investigation_manifest_v2'::regproc)`
  on the production project before 0039 is applied and find an owner allow-list wider
  than the earnings owner.
so_what: >
  Every new evidence owner the Terminal registry admits needs a migration that widens
  the validator's allow-list to the registry (authored from the installed body, every
  other byte unchanged) plus a contract test that pins the two lists together
  (`terminal/lib/__tests__/investigationEvidenceOwnersMigrationContract.test.ts`);
  the client registry alone never makes a save succeed. Migrations stacked on 0039
  (0040 `review`) are applied after it, each through `scripts/supabase_apply.py --apply
  --receipt` with the receipt posted on the PR.
kind: landmine
verified_at: 2026-10-21
verified_by: >
  `pg_get_functiondef` read of the installed validator from the production project on
  2026-10-21 (Options R1 W2 seat); Terminal PR #1103 carries
  `supabase/migrations/0039_investigation_options_evidence.sql` and the contract test
  (5 passed), `scripts/supabase_apply.py --dry-run` re-runnable OK.
scope:
  - terminal
  - terminal/supabase/migrations/0039_investigation_options_evidence.sql
  - terminal/supabase/migrations/0040_investigation_review.sql
  - terminal/lib/investigationEvidence*.ts
  - WS:OPTIONS-R1
confidence: verified
---

The client-side registry and the database predicate are two allow-lists; a save is
accepted only when both admit the owner. The contract test exists so they cannot drift
apart silently again.
