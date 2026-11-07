# Defensive rotation C0: atomic consent inside the preferences owner

Parent: WS:LEADERSHIP-ROTATION-INTELLIGENCE / Clear Workstream Blockers #917.
Authority: Chairman-approved continuation; current principal owns this bounded source slice.
Status: source candidate; recording and sends remain disabled. No live database,
user, email, scheduler, deployment, or account-route effect has been performed.

## Original state and bounded outcome

Observation continuity #10325 and records adoption #10249 did not implement the
subscriber/outbox bridge. The original Fabric bridge attempt
defensive-rotation-outbox-bridge-build-20261023 terminated rc1,
unrecognized_model MiniMax-M3, accepted=false/retry=false. It is not restarted.
A new canonical Fabric roots read returned backend_unavailable before dispatch;
direct permitted source work continues without inventing a worker or grant.

Original operation clear-workstream-blockers-20261104-rotation-consent owns the
managed Macro branch sol/web-clear-workstream-blockers-20261104-rotation-consent,
based on c53915f6d67078d5c0aeaf73bf85ddea1a23de03. Its PARTIAL acquisition
return was reconciled against the exact registered path, operation lock, branch,
clean tree and base before editing. The acquisition was not replayed.

C0 implements the missing per-user serialization primitive. It leaves the
incumbent account-route writer (#10597), roster, source ledger, outbox and sender
unchanged. Its SQL is a reviewable migration candidate, not an installation.

## One owner and exact consent semantics

The only stored state is rotation_notification_consent in the existing
auth.users.raw_app_meta_data. No directory, consent table, queue, lease service,
retry registry or schedule is created.

The marker has a closed v1 shape: a server-generated UUID revision, an active
boolean and a database-clock activation timestamp (null when inactive).
A UUID revision is an equality token, not a sortable clock or ordered counter.

The service-role-only read RPC returns fresh database state. The set RPC locks
the same Auth row. Explicit activation must match the revision presented to the
user, using NULL-safe comparison; NULL matches only a genuinely absent marker.
Current global email and rotation-category preferences must also be well formed
and explicitly enabled. An authorized opt-out needs no expected revision and
always installs a fresh inactive tombstone. Re-enabling creates a new revision
and activation time, so old prepared deliveries cannot borrow the new consent.

A SECURITY INVOKER trigger preserves the previous marker on generic writes,
including stale whole-object app-metadata writes, while preserving unrelated
app-metadata changes. Negative or malformed required preferences atomically
revoke activation and rotate the revision, including before first activation.
Generic positive saves never activate. Inserts cannot import active markers.
Malformed markers refuse activation; opt-out repairs a malformed marker without
casting its old token. An uninterpretable entire app-metadata object remains
fail-closed instead of discarding unrelated data.

The trigger grants marker-write provenance only to the dedicated NOLOGIN,
NOINHERIT, non-superuser, non-BYPASSRLS function owner. No application role gets
membership in that role. The narrow functions have fixed search paths and
column-scoped privileges. PUBLIC/anon/authenticated execution is explicitly
revoked even under Supabase-style default grants. Reapplication refuses an
unexpected owner, membership, trigger owner or additional function owned by this
role. No caller-supplied GUC, timestamp, JWT claim or helper output can authorize
an activation.

This boundary protects application writes. A privileged database administrator
or table owner able to disable triggers remains privileged; C0 does not claim
protection against that administrator.

## Existing account-owner integration contract

lib/user_prefs.py remains the single preferences owner. Its existing generic
writer and call signatures remain unchanged; C0 adds dormant read_rotation_consent
and write_rotation_consent adapters using the same injected/environment-resolved
service credential, with no default project or alternate credential.

The existing route must bind user_id to its authenticated subject and distinguish
an explicit consent action from an unrelated save. The revision belongs to the
user's observed state and intent. On stale_revision, show current state and
require a new explicit activation action; never silently fetch a newer token and
retry the old request. Selecting the rotation category must not implicitly
enable global email.

A successful write receipt is typed and bound to the requested user and active
state. Explicit authorization denial is NOT_APPLIED. A lost or malformed write
receipt is EFFECT_UNKNOWN and is never automatically retried. Reconcile the
original user record before any later action. A fresh read describes current
state; it does not prove which interrupted write produced it.

The old user_metadata projection can still be restored by a stale generic
whole-object save. The actual regression test preserves that sequence and proves
the server-owned rotation marker remains revoked. The future account UI must
display authoritative activation separately; C0 does not claim a general repair
of every preference key or existing transport category.

## Verification and CI ownership

Initial isolated PostgreSQL 17.11 and adapter qualification:
51 passed in 15.82s, log /tmp/cwb-rotation-consent-sql-1104.log,
SHA256 e9e8ed4631b235765977d123431b78af134a56ccf0641595d5b1ad0e471f999e.
The first run failed test collection; that harness error was repaired and no SQL
proof is attributed to the failed run.

The fixture creates a new private temporary cluster with Unix sockets only,
listen_addresses empty, synthetic users/roles and inherited PG variables removed.
It never connects to an existing database. Actual separate connections prove
both opt-out/enable lock orderings, one winner for competing enables, the
original Python preference writer's stale-save schedule, forged and deleted
markers, malformed-state revocation, real non-owner role refusal, reapply and
rollback. Missing PostgreSQL is a qualification failure, not a silent skip.

Three additional adversarial cases cover extra function-owner entry points,
role-membership drift and RLS incompatibility without granting BYPASSRLS.
The existing rotation-observation-delivery CI job owns both new suites and both
SQL files; no workflow, runner, scheduler, packing ceiling or global test
exclusion is added. Actual existing-owner suites, preference compatibility and both CI closure/budget guards: 313 passed, 3 skipped in 325.36s. The isolated new consent suites have no skip condition; the combined regression reports three existing skips and does not establish complete site-browser coverage. Log /tmp/cwb-rotation-consent-owner-1104.log, SHA256 cea51b3eaf337eade44376c6ed4311d400b816805644ede2d095cdf09c02f195. Full differential contract-delta qualification against c53915f6d67078d5c0aeaf73bf85ddea1a23de03 passed: 0 introduced, 0 inherited, 576.8 seconds. All three ordinary-change probes preserved the base job counts, weights and pack counts within the existing ceilings. Log /tmp/cwb-rotation-consent-contract-delta-1104.log, SHA256 3554133427ee04ff2b694f4970abe158d4898ea616acfff892a6f7d38989e6bf. Hosted CI and non-author review remain pending.

## Remaining acceptance boundary

C0 is done only after frozen-source local qualification, hosted CI and genuine
non-author review. It does not complete source-to-user delivery.

Before any production use, qualify the installed Auth/PostgREST version, schema,
role grants, RLS and existing trigger interactions; apply through the incumbent
migration/release owner. Integrate the existing account route's authenticated
explicit-intent contract. No production installation is performed by this work.

Next source slice must choose a real bounded subscriber snapshot contract:
keyset pagination plus a timestamp cutoff does not freeze transactions that
commit later. Bind retained canonical observations and deterministic existing
outbox identities to the consent revision. The current database state and
permitted recipient must be checked at the existing pre-transport boundary.
Database authorization and SMTP handoff are not one transaction; an opt-out or
correction cannot recall transport already entered.

Original live-drain SSH safety denial remains held. Do not retry it through a
different carrier. No recording, sends or live-user acceptance is implied by
this source primitive or its tests.

Primary behavior references:
- https://www.postgresql.org/docs/17/sql-createfunction.html
- https://supabase.com/docs/guides/auth/managing-user-data
- https://supabase.com/docs/guides/database/postgres/row-level-security
- https://github.com/actions/runner-images/blob/main/images/ubuntu/Ubuntu2404-Readme.md

The upstream references support interface/security reasoning. They do not prove
the deployed server's revision, roles, compatibility or behavior.
