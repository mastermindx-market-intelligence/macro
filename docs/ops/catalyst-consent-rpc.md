# Catalyst consent RPCs (0009) — install, verify, roll back

The Catalyst opt-in funnel (`app/catalyst_optin.py`, wired at boot by
`app/catalyst_optin_wiring.py`) keeps every consent record in the incumbent Supabase
email estate through seven owner-run RPCs. This page is the operator path for the SQL
that provides them. It installs no flag, no sender and no scheduler.

| What | Where |
| --- | --- |
| Migration (idempotent) | `scripts/deploy/0009_catalyst_consent_rpc_v2.sql` |
| Rollback (keeps the ledger tables) | `scripts/deploy/0009_catalyst_consent_rpc_v2_rollback.sql` |
| Applier / census (Management API, run on the VPS) | `scripts/deploy/catalyst_consent_migrate.py` |
| Local proof against a fresh socket-only PostgreSQL | `scripts/test_catalyst_consent_rpc_review.py` |
| File-level fences that run in CI | `tests/test_catalyst_consent_migration_files.py` |

## What it installs

- Tables `public.catalyst_consent_pending` (signed intents awaiting an OTP, swept one hour
  after expiry) and `public.catalyst_consent_grants` (confirmed grants; append-only, with a
  guard trigger that refuses any change to identity columns and any clearing of a
  revocation). RLS enabled, zero policies, every client role **including service_role**
  revoked from both tables and the identity sequence.
- RPCs `catalyst_consent_contract / begin / resolve / confirm / current / interested /
  revoke`, EXECUTE for `service_role` only. All but `contract` are SECURITY DEFINER and
  run as the table owner; the application's service-role key never touches a table.
- Two triggers on the incumbent tables: an insert or update on `email_suppression`
  permanently revokes that address's grants; `marketing_opt_out = true` on `email_prefs`
  permanently revokes that user's grants. Neither trigger can block an incumbent write
  (a blank address is left to the table's own constraints).
- An install fence that rolls the whole file back on: an existing client policy, any
  client or service_role table/sequence grant, FORCE RLS, a foreign or client owner.

The trust model, lock order and NULL-handling are documented in the migration header.

## Apply (production)

Run on the VPS, from the deployed checkout, with the admin env sourced so the Management
API token never leaves the box. Never print the env.

```bash
cd /opt/macro && set -a && . /etc/macro-admin.env && set +a && python3 scripts/deploy/catalyst_consent_migrate.py --apply
```

The applier posts the file to the Management API SQL endpoint (same route as 0004), then
prints a census of names, counts and booleans and `state=INSTALLED|PARTIAL|ABSENT`.
Exit 0 is INSTALLED. The migration sets `lock_timeout = 3s`: if an incumbent write holds
`email_suppression` or `email_prefs`, the file fails cleanly and rolls back; rerun it.

Verify at any time (read-only):

```bash
cd /opt/macro && set -a && . /etc/macro-admin.env && set +a && python3 scripts/deploy/catalyst_consent_migrate.py --verify
```

After INSTALLED, restart the API so the boot probe re-reads the contract (the probe runs
once per worker at import; see "boot-only probe" below):

```bash
systemctl restart macro-api
```

## Roll back

```bash
cd /opt/macro && set -a && . /etc/macro-admin.env && set +a && python3 scripts/deploy/catalyst_consent_migrate.py --rollback
```

Drops the three triggers, the three trigger functions and the seven RPCs, in that order,
and **retains** both ledger tables (dropping them is a separate owner decision). The
application's next boot probe answers `CONSENT_OWNER_NOT_READY` and the funnel refuses;
incumbent unsubscribe and preference writes are unaffected (proven by the local harness).

## Semantics operators should know

- **Revocation is permanent per (user, event, scope).** A later confirm for the same
  event raises `CONSENT_ALREADY_REVOKED_OR_MISMATCHED`. There is no re-subscribe path by
  design; re-consent needs a new event or scope.
- **Cascade.** Grants reference `auth.users` ON DELETE CASCADE: deleting the GoTrue user
  deletes that user's grants and replay-ledger rows.
- **Boot-only probe.** The application checks `catalyst_consent_contract()` once per
  worker at import (6 s timeout). A transient DB failure at boot leaves the funnel off for
  that worker until the next `systemctl restart macro-api`; workers can diverge.
- **Named refusals are collapsed by the app (B2 finding, corrected 2026-11-02).** An RPC
  `raise exception 'NAME'` reaches the app as a PostgREST 400 (`urllib.error.HTTPError`).
  `SupabaseConsentRpcOwner._rpc` does not parse the body; the lifecycle wraps the owner
  calls, so a resolve refusal (expired or unknown pending ref) surfaces as the generic
  503 `PENDING_CONSENT_UNAVAILABLE` and a confirm refusal (suppressed address, revoked
  grant, intent mismatch, clock window) as 503 `CONSENT_WRITE_UNCONFIRMED`; the browser
  never sees the name. No 500 and no grant or mail side effect. Mapping the allow-listed
  names to specific 4xx `FunnelGate` codes is B2 UX work; a pre-minted tree exists at
  `/Volumes/Mastermind/agent-workspaces/claude/14851c4656838a3b/mx-catalyst-b2-rpc-refusals-7c43dc6707b15c83`
  (branch `claude/ssd-mx-catalyst-b2-rpc-refusals-7c43dc6707b15c83`, base main 392f59ace354).
- **Re-apply reconciliation (round-2 review fix, 2026-11-02).** While the two incumbent-table
  triggers are absent (a rollback window) an opt-out or suppression cannot revoke grants, so
  every apply first revokes active grants whose user is opted out or whose address is
  suppressed. Re-applying never resurrects a withdrawn grant; a clean first apply is a no-op.
- **One intent, one user.** A second GoTrue user confirming the same signed intent gets
  `CONSENT_INTENT_ALREADY_USED`, never a raw unique-constraint error.
- **Install fence (extended).** Besides policies, client grants, a foreign owner and FORCE
  RLS on the consent tables, the fence stops on a pending table with a different owner
  (`CATALYST_CONSENT_TABLE_OWNER_BLOCK: pending`), on `email_suppression`/`email_prefs`
  missing (`…INCUMBENT_TABLE_MISSING_BLOCK`), on either being FORCE RLS or owned by someone
  other than the function owner without BYPASSRLS (`…INCUMBENT_TABLE_ACCESS_BLOCK: <table>`),
  and on the owner lacking SELECT on `auth.users` (`…AUTH_USERS_READ_BLOCK`). Any of these
  would otherwise make the suppression veto silently see no rows.
- **Failed apply.** The applier sends `rollback;` after a non-2xx apply or rollback, then
  prints the census state anyway (never a bare exit code). `--verify` also requires the
  `authenticated` role to hold no execute/select and all three triggers to be enabled on
  their tables.

## Where this sits in the flag sequence

`CATALYST_OPTIN_ENABLED=1` is set only after, in order: 0009 is INSTALLED here; the B1
wiring (`app/catalyst_optin_wiring.py`) is deployed; `MAIL_UNSUB_SECRET` (32+ chars) and
`CATALYST_SCAN_RECEIPT_SECRET` are present on the host; `systemctl restart macro-api`
logs `catalyst optin wiring configured`; and one real OTP request is witnessed on the
hosted page. `MAIL_CATALYST_ENABLED` is a separate, later gate (delivery), untouched here.

**OTP delivery constraint (read-only census of the Supabase auth config, 2026-11-02).**
The project has no custom SMTP configured (`smtp_host` unset); GoTrue sends the opt-in
OTP through Supabase's built-in email service, which is rate-limited to 2 emails per
hour (`rate_limit_email_sent`) and, per the Supabase docs page "Send emails with custom
SMTP" (read 2026-11-02), Auth refuses delivery to addresses that are not part of the
project's team. OTP length is 8 digits, expiry 3600 s
(the app accepts 6-8 digits). Consequences: the "one real OTP request witnessed" step
can be proven on the hosted page (202 + pending ref, GoTrue accepts the send) but the
code only arrives in a team member's inbox, and entering it is a human step; a pilot
cohort of outside recipients needs a custom SMTP provider configured in Supabase Auth
(credentials, SPF/DKIM) before B2. That provisioning is a Chairman decision (provider,
spend), not something a seat may enroll.

## Local proof

```bash
LC_ALL=C TMPDIR=/private/tmp/pgrev PATH=/opt/homebrew/bin:$PATH python3 scripts/test_catalyst_consent_rpc_review.py
```

Needs `initdb`, `pg_ctl`, `psql` on PATH and a short TMPDIR (Unix-socket path limit).
Creates a throwaway cluster, applies 0009 twice, runs the suppression races, applies the
rollback, proves the incumbent writes, opts a user out inside the window, re-applies and
proves the window opt-out revoked. Also runs the extracted install fence alone against a
stray client grant and an unreadable incumbent table. Prints one PASS line per property;
`PRODUCTION_DB_EFFECTS=NONE` is literal.
