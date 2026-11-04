# Clear Workstream Blockers: digest withdrawal fence

## Decision and ownership

The current Clear Workstream Blockers principal owns this bounded continuation under the Chairman's direction to finish the proposed permanent fixes. The source law pin is Mastermind/master@910803421beca53ca25145392725ab2d84c7a8e9 (INDEX 1.0.1 / bootstrap 1).

This change addresses the stale-enable-after-withdrawal problem identified in the independent privacy review of [macro #10597](https://github.com/mastermindx-market-intelligence/macro/pull/10597#pullrequestreview-5763602421). It uses the existing account preference owner and the original digest integration carrier. It is source-qualified and remains held for genuine non-author review and installation/product acceptance.

- Original integration PR: #10597, draft, no automatic merge observed.
- Exact starting commit: b0f3e4183170a2590950bbf7d85ff6f9e7ef542c.
- Original operation: clear-workstream-blockers-20261104-digest-withdrawal-fence.
- Native source branch: sol/web-clear-workstream-blockers-20261104-digest-withdrawal-fence.
- Canonical mission handoff: [Mastermind #917](https://github.com/mastermindx-market-intelligence/Mastermind/issues/917#issuecomment-6620138345).
- This principal authored the repair and cannot provide its independent approval or protected merge. The earlier independent REQUEST_CHANGES is not cleared by these tests.

## Consumer problem and guarantee

The original implementation could acknowledge a negative choice without advancing durable state when the preference was absent or already false. An older positive request could subsequently enable delivery. This is a stronger withdrawal-contract defect; the original concurrent schedule alone is not a violation of linearizability.

Every supported withdrawal now creates a durable negative choice with a new server-generated UUID revision. A positive choice carries the revision observed when the user made that decision. A stale observation cannot enable after a later withdrawal has committed. Explicit NULL denotes an observed absent row and can enable only while that row remains absent.

The guarantee applies while the same Auth account exists and the supported application operations retain the fence. A database/table owner can alter privileges, disable guards, erase data, restore older revisions, or recreate an Auth UUID. Those remain privileged consent-state maintenance, requiring the applicable enrollment/writer quiescence and restoration contract.

This is not an atomic cancellation guarantee for an SMTP transaction already beyond its final authorization decision. Sender retry consent is a separate P1 obligation below.

## Implementation

### Existing canonical preference owner

The migration extends public.email_prefs with portfolio_digest_opt_in (literal boolean, default false, non-null) and portfolio_digest_revision (server UUID, non-null). It does not create another consent registry, identity store, queue, scheduler, or state owner. The existing language and marketing_opt_out fields retain their owners.

public.portfolio_digest_consent_set_v1(uuid, boolean, uuid DEFAULT NULL) performs one atomic decision:

| Decision | Mutation | Outcome |
| --- | --- | --- |
| Withdraw, including absent/already-false preference | Insert or update false and a fresh revision | Applied; every withdrawal advances the fence |
| Enable with explicit NULL observation | Insert true only if the row is absent | Applied or stale_revision |
| Enable with an observed UUID | Update only that account and matching revision; mint a new revision | Applied or stale_revision |

A newly created language-only preference row has a real revision. It therefore rejects an older NULL enable. A stale response includes canonical current state so a client can ask for fresh intent; clients must never automatically rebase or replay the positive decision.

### Narrow database authority

The private macro_digest_consent_owner role is NOLOGIN, NOINHERIT, NOSUPERUSER, NOCREATEDB, NOCREATEROLE, NOREPLICATION and NOBYPASSRLS. It has no role membership paths and does not own the table or schema. Its column grants and role-only RLS policy cover only the necessary account/digest/revision/global-veto data and updated_at.

The fixed-search-path SECURITY DEFINER RPC is owned by that role. EXECUTE is revoked from PUBLIC, anon and authenticated and granted only to service_role. The application supplies the authenticated account identifier; clients cannot invoke the privileged RPC directly.

INVOKER insert/update guards prevent ordinary direct positive bypass, rotate revisions for supported negative writes, and prevent relocating the fence to another user_id. Ordinary partial upserts that include the same user_id remain compatible. Application DELETE/TRUNCATE authority on email_prefs is removed and effective erasure grants are checked. The real parent auth.users delete cascade remains supported and is exercised in the isolated fixture.

The transactional preflight refuses unexpected role attributes/membership, broad effective privileges, default/type drift, unreviewed owner routines, unrecognized user triggers and policies, or unexpected schema-create authority. It checks recognized reapplication rather than replacing or blessing unknown installed objects. The migration has a five-second lock timeout and thirty-second statement timeout.

Rollback removes the positive RPC entry point but retains negative fences, columns, guards, role restrictions and current revisions. Reapplication does not reset decisions or revisions.

### API contract

GET /api/account/prefs/portfolio-digest returns enabled, marketing_opt_out and revision from the authenticated account's canonical row. An absent row returns the explicit absent observation. A malformed existing row is unavailable, not an absent preference.

PUT accepts a strict literal boolean and an optional strict canonical UUID revision. An enable must explicitly include expected_revision, including explicit NULL only for an observed absence. Withdrawal remains available while enrollment is disabled. Unknown fields and malformed observations are rejected.

The API calls the existing billing._pg owner once with POST rpc/portfolio_digest_consent_set_v1. It performs no preliminary read, automatic retry, or conflict rebasing. A valid stale response produces HTTP 409 with private/no-store current state. Other response bindings, values and revision transitions are checked. Auth denial is reported unavailable/not applied; other failures or malformed replies remain unconfirmed. A committed mutation whose reply is lost is not retried.

The ordinary general-preference writer is unchanged. Its inherited C05 metadata race is not claimed fixed here.

### CI ownership

The two new modules are appended to the existing billing-emails pytest step alongside tests/test_billing_emails.py and tests/test_deliver_portfolio_digest.py. No new job, test owner, runner, dependency, cap, or budget is introduced.

The API tests use the incumbent direct-ASGI approach, avoiding an httpx dependency in the billing job. The PostgreSQL tests use an isolated temporary Unix-socket cluster; unavailable binaries fail instead of silently skipping. No live project, user account, mail service or scheduler is involved.

## Qualification

Complete machine-readable receipts and original logs are in [evidence/cwb_digest_consent_20261104](evidence/cwb_digest_consent_20261104).

| Evidence | Exact result |
| --- | --- |
| Final existing billing + digest step | 190 passed, 0 failed, 0 errors, 0 skipped; 18.87 seconds pytest / 21.4 seconds wrapper |
| New API module | 36 cases, included in the 190 |
| Real PostgreSQL module | 22 cases, included in the 190 |
| Original digest module | 23 cases, included in the 190 |
| Full differential contract gate against b0f3e4183170a2590950bbf7d85ff6f9e7ef542c | Exit 0; 0 introduced, 0 inherited; 493.36 seconds wrapper |
| Tested seven-file staged tree | c690a735fb7cea3180688c15f9ad801d56490e33 |
| Post-gate integrity | All seven source hashes unchanged |

The final qualification supersedes the exploratory 81-pass run that used the earlier TestClient harness. That exploratory run is not counted again. The new evidence/documentation files do not change the seven qualified implementation/test/CI files; the final publication manifest binds their hashes.

Real PostgreSQL qualification covers both lock orders for absent/inactive/active preferences, one-winner races between enables with the same observation, stale NULL observation after another preference writer, negative-to-negative revision changes, and committed positive/negative API mutations followed by a lost response with no replay.

It also covers real database-role denial, direct positive/update/revision/GUC bypass attempts, global veto preservation, same-ID partial upsert compatibility, row erasure and identity-relocation restrictions, parent Auth cascade, recognized reapplication, drift refusal, rollback and reapplication. These are fixture results, not installed Supabase catalog or production-path proof.

Receipt SHA-256 values:

- Final 190-case receipt: 520fc37bd7c7af8bf7901e7db835c315aa3743c2256167c63e9ee07fbab63b48.
- Final pytest log: 0bddc76d95a03b3b830aed6a625f8e1d8c422851a5cd9e1ff3b6c32cd08e3540.
- Full contract receipt: 1638c0e1e0d79389490684e900c8d98bd74d1097f57c871108ac463effc03b0f.
- Full contract log: 77a643a6805628a17045ee607848600b1aa9418e9e8cc5a9370e3cb2b60aaf35.
- Seven-file staging receipt: 791e2f072eadb36f1fbd4f33181de016d442f6221541da35a872c6234b7c2903.

## Installed environment: evidence and limits

The b0 application source names fsldfzlxyavsuwqbceod as its default Supabase project. That is a source binding; it does not prove which configuration is served.

The advertised Supabase list_projects, get_project and execute_sql read tools each returned MCP -32001 Unknown tool. The attempted SQL was catalog-only, with no user-row read or mutation. These are unavailable tool bindings, not evidence of denied authorization or an installed schema result.

The existing billing reader's prerequisite probe found no usable credential in this workspace and sent no request. Its original receipt is retained (SHA-256 ceb6015322b311c59d067868ccaf056a63abe6209efc401a7c134076a248d554). No credential value was exposed or extracted elsewhere. The Supabase CLI is not present on the observed PATH. No install, login, migration application or production RPC call occurred.

Installed RLS, role membership/effective privileges, function/trigger provenance, API exposure and schema-cache behavior remain unqualified. No database-owner or privilege-bypassing test harness may stand in for those installed facts.

## Acceptance and integration sequence

1. Preserve #10597 as the single digest integration PR. Reconcile its exact current head and live-writer state before any fast-forward composition. Publishing this operation's source branch is not a deployment or acceptance.
2. Obtain genuine non-author review of the exact composed source and SQL. Reviewers must assess installation compatibility and the bounded privileged-maintenance assumptions; this author's tests do not clear the earlier review.
3. On an available admitted read route, inspect the installed canonical project/catalog and known privileged erasure entry points. Refuse drift or missing evidence; do not create a replacement auth/migration/control plane.
4. Apply the reviewed migration through the established deployment owner, record its exact source and result, and verify installed definitions, RLS, grants, guards and real PostgREST behavior. Keep enrollment disabled.
5. Connect the authenticated revision-bearing client to this contract, including conflict presentation and uncertain-response handling. A 409 or unconfirmed result must require fresh observation and explicit user intent.
6. Finish and reconcile the original P1 sender carrier. Complete the trusted per-account nightly cursor contract. Then qualify the actual authenticated opt-in, one authorized delivery, duplicate suppression and one-click withdrawal under the real product path.
7. Record required browser/production receipts and persona acceptance before changing enrollment/runtime holds. Green CI alone does not establish completion.

## Preserved P1 uncertainty and remaining product work

P1's original retry-consent operation is clear-workstream-blockers-20261104-digest-retry-consent. Its existing source and completed qualification are preserved separately. The original attempt to append and run test_digest_fresh_address_suppression_at_each_attempt timed out without a returned process/request handle. Bounded supported completed-tool history and target reconciliation did not establish non-dispatch or terminal execution.

No replay, replacement carrier, P1 source mutation or alternate publication is authorized by absence of those effects. Its completed history receipt 1c7e335f-fe58-446f-af10-31966234fbc3 is 40,580 bytes, SHA-256 596619ac9fd1ed2f29f893270583f2f002bec9b86ec9739ebb3abb589410e5e3. The missing proof is the original request's dispatch/phase/terminal result.

The real remaining P1 policy gap is address-level email_suppression. The original unsubscribe handler can commit suppression before a preference update fails. Fresh digest/global preferences alone cannot establish permission to send. Once the original uncertainty is resolved, the existing pre-DATA hook must compose the master gate, fresh account consent and the incumbent suppression lookup for the same recipient; lookup uncertainty must remain unavailable. Preserve the original ledger, attempt marker, retry budget and stable account/day key.

This P2 source is deliberately not a duplicate implementation of P1. It introduces no sender changes and does not claim real delivery, complete digest acceptance, protected merge, installed execution or durable worker START.
