# Defensive rotation bridge: integration and activation boundaries

Parent: WS:LEADERSHIP-ROTATION-INTELLIGENCE. Status: in progress; recording and sends disabled.

## Accepted recovery and source release

The original independent composite review, response SHA256 512f1c9ca505d235ceb06b268e8d45ad7d2403243aa8dc800f3d02110a209a78, was consumed and accepted for the exact pre-bridge consumer6ad0b54231a0d059508e9a582420dc1e39c29933 and display933498fc5fbbf523674c9c1fcb18649228ad4a57. All16 recorded source hashes matched. The display released normally as PR10103 merge8614f39ed1e75ea03b529e2e6f50ecd76148d504 at2026-10-23T09:25:13Z, after all applicable checks and independent review; no admin bypass or self-approval. Production visibility remains unverified.

## CI repair (not a relaxed gate)

Hosted10104 contract-delta identified9 missing trigger paths for the new shared notification contract and an increased ordinary-PR packing weight. The manifest now widens those exact9 scopes. Moving the two new suites into one command removed only1 weight unit; the two explicit test paths still added4 to every unrelated selection, which the full local gate correctly rejected. That intermediate repair was not accepted.

The final repair gives these two suites a narrow logical job, rotation-observation-delivery, within the incumbent ci-pack runner. Its22 concrete import/runtime paths and ancestor initializers come from the canonical scope-inference helper; the real Node test reads only templates/account.js and site/account.js, so those exact paths replace its opaque whole-directory fallback. The curated job set is updated; no packing ceiling, guard or test assertion was relaxed. The original support-email job retains its old suite list. All tests still execute under the same CI owner.

Actual full local check: python3 scripts/check_contract_delta.py --base 3b5058cf10a6791d5e8097e514af0c8ff15b9b59 ->0 introduced,0 inherited. Three ordinary probes remain byte-identical in job count/weight to base: index136/5884, free-content135/5856, plan-book128/5628;10packs each. New consumer job executed208 tests successfully. Curated-set assertion and exact selection tests cover all named dependency changes while excluding the three unrelated probes. Hosted acceptance is separately owed on the published head.

## Newly reproduced consent race

The current pre-bridge lib/user_prefs.py writer performs a fresh GET, overlays validated keys, then PUTs the entire merged user_metadata object. An offline two-thread test against the actual function established: language-save GET pauses; email opt-out reads and successfully writes false; delayed language-save resumes its stale PUT and restores true. Both calls return success. No network or live records were used. This is a real existing stale-write hazard, not proof that the new bridge already fixes it.

The returned bridge must be tested against this schedule. At minimum, unrelated preference saves must not rewrite or restore the server-owned rotation activation marker, and delivery must consult that marker plus current explicit email/category consent. Sending only the requested metadata patch can narrow the client-side overwrite, but must not be described as a transaction/CAS guarantee across concurrent Auth requests.

Primary upstream references inspected October23: Supabase auth internal/api/admin.go loads the user before adminUserUpdate's transaction and updates app/user metadata in that transaction; internal/models/user.go UpdateUserMetaData and UpdateAppMetaData merge onto an in-memory user object then UpdateOnly the JSON column. This is upstream source evidence, not the installed server's exact revision or a proven compare-and-swap facility. Official source: https://github.com/supabase/auth/blob/master/internal/api/admin.go and https://github.com/supabase/auth/blob/master/internal/models/user.go .

The strong claim that every overlapping opt-out wins requires a real version/serialization contract at the incumbent preference owner. Do not obtain it by adding a parallel identity/lock store or merely describing a timestamp as atomic. If unavailable in this source-only scope, retain a specific activation blocker; local fixture success cannot waive it.

## Original builder and held effects

Fabric bridge builder defensive-rotation-outbox-bridge-build-20261023, controller55052, conserves rootdefensive-rotation-20261022 and parentchatgpt-defensive-rotation-ceo-20261022. It owns isolated scratch only, with no shared-source/GitHub/database/users/SMTP/flags/deployment effects. Parent owns CI and final integration. Do not duplicate it while its original outcome is unresolved.

A read-only production SSH verification attempt was blocked by platform safety checks. No remote execution/authentication is proven. That exact verification lane is held: no rephrasing, retry or alternate carrier to obtain the blocked effect. This does not block independent authorized repository implementation/testing. Existing unrelated Macro-entry launch uncertainty remains preserved.

## Acceptance required next

Canonical retained source -> complete, typed subscriber read -> trusted activation interval -> deterministic per-user existing outbox -> existing drain/mailer. Prove duplicate/conflict/unknown-POST readback, correction and withdrawal, no backlog after new subscription, fresh consent and exact source at the pre-transport boundary. A later update cannot recall an already-entered SMTP effect. Keep default-off flags and all real sends disabled until independent review and actual activation conditions are met.
