---
key: MX-CATALYST-CONSENT-RPC-V2-APPLY-20261102
question: "Should the catalyst_consent_* RPC v2 contract (migration 0009) be applied to the production Supabase project now, and by which path?"
answer: >
  Yes. The round-2 independent read-only review returned SAFE_AFTER_SHOULD_FIX (one should-fix,
  seven minor or nit); the fixes landed in c1341e7c and the delta re-review of that head
  returned PASS with no blocker (five post-PASS notes applied in f086b969 with harness proof).
  Once the reviewed bytes are merged, apply from the deployed checkout on the VPS with
  scripts/deploy/catalyst_consent_migrate.py --apply over the established Management-API query
  path (/etc/macro-admin.env sourced on the host), then --verify must print state=INSTALLED.
  CATALYST_OPTIN_ENABLED stays 0 after the apply; the RPCs are inert until the B1 wiring is
  deployed, both secrets are present and the switch is set under its own recorded gate.
rationale: >
  B1 (permission to communicate) cannot be proven without an owner-run consent contract in the
  database, and the app's boot-time probe refuses to configure the funnel without it. The
  migration is deny-all to every client role, installs only owner-executed functions and
  triggers, never blocks the incumbent mailer's writes, carries a reviewed rollback that keeps the
  ledger tables, and has a local Postgres harness and file fences that cover the review findings
  F1-F9. The Management-API path is the one the previous migrations 0004-0008 used from the same
  host; the host holds no direct database credential.
alternatives:
  - option: "Defer the apply until the B2 sender wave is ready."
    why_not: "It blocks the whole B1 proof (OTP request witness, opt-in switch) on unrelated delivery work; the installed functions have no caller until the switch is on."
  - option: "Apply from the /root copy of the applier before the PR merges."
    why_not: "The applier reads the SQL beside itself; applying from the deployed checkout keeps the applied bytes equal to the merged, reviewed bytes."
  - option: "Apply over a direct Postgres connection or the Supabase dashboard."
    why_not: "The host has no database credential and the dashboard is a human-only surface; the Management-API query path is the reviewed, scripted, auditable route."
evidence:
  - "Local Postgres review harness scripts/test_catalyst_consent_rpc_review.py at f086b969: 18 PASS lines incl. SERVICE_ROLE_TABLE_DENY, PENDING_INTENT_REPLAY, NULL_INPUTS_NAMED_REFUSALS, BEGIN_MISSING_FIELDS_NAMED_REFUSALS, INTENT_SINGLE_USER, GRANT_IMMUTABILITY, INSTALL_FENCE_FIRES (NOBYPASSRLS owner walk), REAPPLY_RECONCILES_WINDOW_OPTOUT (opt-out and suppression halves), ROLLBACK_RESTORES_INCUMBENT_WRITES, PRODUCTION_DB_EFFECTS=NONE."
  - "tests/test_catalyst_consent_migration_files.py: 9 passed (round-2 fix presence, rollback completeness, single transaction with timeouts, client-role revokes incl. service_role, owner-only execute, NULL-safety markers, applier prints no values)."
  - "VPS read-only census 2026-11-02 (names/booleans only): /opt/macro HEAD 392f59ace354; catalyst_consent_migrate.py --verify -> functions=0/10 triggers=0/3 tables=0/2 state=ABSENT exit=2; macro-api and admin active."
  - "Round-2 independent read-only Opus review of the 0009 SQL (d33e6075): SAFE_AFTER_SHOULD_FIX, no blocker; F1 rollback-window resurrection, F2 fence readability, F3 intent reuse, F4 harness gaps, F5 header, F6 pending owner, F7 fence proof, F8 applier census. Delta re-review of c1341e7c: PASS, F1-F7 CLOSED, F8 PARTIAL -> closed in f086b969 (transport-failure census, O/A triggers, owner SELECT, NOBYPASSRLS proof, suppression half). Both rounds summarised in one PR #10538 comment."
affects:
  - "WS:MARKETING-X-CATALYST-LOOP"
  - "scripts/deploy/0009_catalyst_consent_rpc_v2.sql"
  - "scripts/deploy/catalyst_consent_migrate.py"
  - "docs/ops/catalyst-consent-rpc.md"
confidence: high
reversibility: easy
decided_by: "ceo-seat ce215fa3 (Fable) under the Chairman's 2026-11-02 delegation"
decided_at: 2026-11-02
---

# Apply the Catalyst consent RPC v2 contract to production

The consent owner contract (`catalyst_consent_contract/begin/resolve/confirm/current/interested/revoke`,
two owner-only ledger tables, three guard triggers) is installed by migration 0009 over the
established Management-API path from the VPS. Rollback is `0009_catalyst_consent_rpc_v2_rollback.sql`
(drops triggers and functions, keeps the tables and rows). The opt-in switch is a separate gate:
see `docs/ops/catalyst-consent-rpc.md`, "Where this sits in the flag sequence", including the OTP
delivery constraint (no custom SMTP on the Supabase project).
