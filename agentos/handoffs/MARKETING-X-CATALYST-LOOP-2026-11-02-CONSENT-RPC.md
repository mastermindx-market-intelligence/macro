---
workstream: WS:MARKETING-X-CATALYST-LOOP
session: claude/ssd-mx-catalyst-consent-provision-1cb1d009da985ae7
model: fable
ended_because: ci_handoff
decisions:
  - DEC:MX-CATALYST-CONSENT-RPC-V2-APPLY-20261102
mission: >
  CEO seat provisioning the B1 consent owner contract: turn the review-only consent RPC v2 SQL
  into a reviewed, fenced, rollback-able production migration with a scripted applier over the
  established Management-API path, so the opt-in funnel (PR #10532 wiring) has a real owner to
  probe at boot.
state_before: >
  The consent RPC v2 SQL lived under research/marketing_dockets as REVIEW ONLY with nine open
  review findings (F1-F9: NULL inputs, service_role table access, grant mutability, pending-row
  replay, expired-row growth, ticker order, lock/statement timeouts, trigger blocking of incumbent
  writes, policy fence gaps). Production had none of the catalyst_consent_* objects. PR #10522
  (flags-ON preconditions) and PR #10532 (B1 wiring seam) were armed merge-on-green.
changed:
  - path: scripts/deploy/0009_catalyst_consent_rpc_v2.sql
    what: production migration (single transaction, lock_timeout 3s, statement_timeout 60s) with F1-F9 applied, NULL-safe named refusals, PENDING_INTENT_REPLAY on duplicate nonce, hourly sweep of expired pending rows, order-insensitive ticker comparison, grant immutability trigger, client roles (anon, authenticated, service_role) revoked from both tables and the sequence, owner/RLS/privilege fence
  - path: scripts/deploy/0009_catalyst_consent_rpc_v2_rollback.sql
    what: drops the three triggers, three trigger functions and seven RPCs by exact signature; keeps the ledger tables and rows
  - path: scripts/deploy/catalyst_consent_migrate.py
    what: --apply / --verify / --rollback over the Management-API query endpoint; census prints counts, booleans and state only, never values; exit 0 requested state, 2 opposite clean state, 1 partial or HTTP error
  - path: scripts/test_catalyst_consent_rpc_review.py
    what: local Postgres harness rewritten against the deploy files (15 PASS lines incl. rollback restores incumbent writes, service_role table deny, NULL inputs, immutability, positive revoke path, clock windows, expired sweep, policy install veto)
  - path: tests/test_catalyst_consent_migration_files.py
    what: eight file fences (rollback completeness and order, single transaction with both timeouts, every client role revoked incl. service_role, owner-only execute, NULL-safety markers, applier prints no values, review-only file superseded)
  - path: docs/ops/catalyst-consent-rpc.md
    what: operator runbook (apply/verify/rollback commands, semantics, flag sequence, corrected B2 finding on collapsed refusals, OTP delivery constraint from the Supabase auth census)
  - path: research/marketing_dockets/MKT_CATALYST_CONSENT_RPC_V2_REVIEW_ONLY.sql
    what: replaced by a comment-only SUPERSEDED stub pointing at the deploy files
verified:
  - claim: "Round-2 independent read-only review returned SAFE_AFTER_SHOULD_FIX (no blocker) and the delta re-review of the fix head c1341e7c returned PASS with F1-F7 CLOSED and F8 PARTIAL; the five post-PASS notes were applied in f086b969."
    command: "Opus reviewer (ROUTE review, MODE READ_ONLY) over git show c1341e7c9a01 in the consent worktree; then harness + file fences on f086b969"
    result: "VERDICT PASS; harness 18 PASS lines + PRODUCTION_DB_EFFECTS=NONE; tests/test_catalyst_consent_migration_files.py 9 passed"
  - claim: "The migration, rollback and re-apply behave as specified on a local Postgres with the incumbent email tables present: every named refusal, deny-all grants, immutability, revoke path, sweep and rollback-restores-writes pass."
    command: "python3 scripts/test_catalyst_consent_rpc_review.py"
    result: "15 PASS lines, PRODUCTION_DB_EFFECTS=NONE"
  - claim: "The deploy files satisfy the eight static fences."
    command: "python3 -m pytest tests/test_catalyst_consent_migration_files.py -q -p no:cacheprovider"
    result: "8 passed"
  - claim: "Production has none of the catalyst_consent_* objects before the apply and the applier's census path works from the VPS with the admin env (names and booleans only)."
    command: "ssh root@VPS 'set -a; . /etc/macro-admin.env; set +a; python3 /root/mx-consent-migrate.py --verify'"
    result: "functions=0/10 triggers=0/3 tables=0/2 state=ABSENT exit=2; /opt/macro HEAD 392f59ace354; macro-api active"
  - claim: "The Supabase auth project sends OTP mail through the built-in service: no custom SMTP configured, 2 emails/hour, 8-digit OTP, 3600 s expiry."
    command: "curl -H 'Authorization: Bearer <PAT>' https://api.supabase.com/v1/projects/<ref>/config/auth (keys printed as set/unset or booleans)"
    result: "smtp_host unset; rate_limit_email_sent 2; mailer_otp_length 8; mailer_otp_exp 3600; external_email_enabled true"
unverified:
  - claim: "Production INSTALLED state after the apply (functions=10/10 triggers=3/3 tables=2/2 contract_ok grants_ok)."
    what_would_verify: "After #10538 merges and deploys: cd /opt/macro && set -a && . /etc/macro-admin.env && set +a && python3 scripts/deploy/catalyst_consent_migrate.py --apply, then --verify prints state=INSTALLED exit=0."
  - claim: "The production Management API behaves like local psql for the explicit begin/commit file (mid-file failure commits nothing)."
    what_would_verify: "The first --apply on production prints apply_http=2xx then state=INSTALLED; a non-2xx apply followed by state=ABSENT would prove the same the other way."
unresolved:
  - "CATALYST_OPTIN_ENABLED stays 0 until: 0009 INSTALLED, #10532 deployed, MAIL_UNSUB_SECRET (32+ chars) generated on the host, macro-api restarted and the journal reads 'catalyst optin wiring configured', one OTP request witnessed on the hosted page."
  - "OTP delivery: no custom SMTP on the Supabase project; built-in mail is 2/hour and delivers only to project team members, so the OTP code lands in a team member's inbox (human step) and a pilot cohort of outside recipients needs a Chairman-provisioned SMTP provider before B2."
  - "B2 UX: named owner refusals are collapsed into generic 503 gates by the lifecycle (not a 500); mapping to 4xx FunnelGate codes is pending in the pre-minted tree mx-catalyst-b2-rpc-refusals-7c43dc6707b15c83."
  - "MAIL_CATALYST_ENABLED stays OFF while the B04 strict xfail stands."
  - "#10468 (figure yield) stays with the repo sweeper."
next_actions:
  - "Consume the round-2 verdict; on PASS arm merge-on-green for #10538; after merge and the 3-minute deploy, run --apply then --verify from /opt/macro and record INSTALLED in this workstream."
  - "After #10532 deploys: generate MAIL_UNSUB_SECRET on the host (never printed), restart macro-api, read back the wiring log line, witness one OTP request, then set CATALYST_OPTIN_ENABLED=1 under its own decision record."
do_not_redo:
  - "The F1-F9 review findings are applied and witnessed by the harness and fences; do not re-derive them from the superseded review-only file."
  - "The VPS pre-install census is recorded here; do not re-run it before the apply."
  - "The flags-ON decision and the B1 wiring review are done (DEC:MX-CATALYST-FLAGS-ON-20261102; PR #10532 PASS)."
danger_areas:
  - "Never print or record SUPABASE_ACCESS_TOKEN, SUPABASE_PROJECT_REF values, service-role keys or any host env value; the applier and census print names, counts and booleans only."
  - "Never apply 0009 from a copy whose bytes differ from the merged PR head; never bypass the Management-API path with a dashboard or direct connection."
  - "The rollback keeps the ledger tables and their rows on purpose (consent evidence); never add a table drop to it."
---

# Consent RPC v2 provisioning (B1 owner contract)

Migration 0009 provisions the owner-run consent contract that `app/catalyst_optin.py`'s
`SupabaseConsentRpcOwner` probes at boot. Everything client-facing is denied at the table and
sequence level; only the owner role executes the RPCs. Rollback keeps the tables. Operators use
`docs/ops/catalyst-consent-rpc.md`.
