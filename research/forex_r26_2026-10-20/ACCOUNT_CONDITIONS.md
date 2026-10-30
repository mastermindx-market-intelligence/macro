# Forex R26 account conditions — current integration contract

> **Current status, 22 October 2026:** inactive authenticated save/reload/edit/delete is **PROVEN_LIVE** and the disposable record was removed. Macro#9996 and the account-owner source merged; migration0038 was applied once. The fixture/Draft statements below are historical and do not reopen accepted CRUD. See [current master plan](MASTER_PLAN.md) and [canonical release checkpoint](https://github.com/mastermindx-market-intelligence/macro/pull/9996#issuecomment-6333973165). Active source binding/evaluation/delivery and Terminal#1106's documentation-review hold remain separate.

## Scope and release boundary

The R26 browser can prepare and explicitly save, reload, edit and delete **inactive** price-close conditions through the existing authenticated Supabase client and Terminal-owned `public.alerts` owner. This source slice does not enable monitoring, admit a finalized 4H feed, enqueue an alert, or send a notification. Missing owner RPCs are an unavailable service, never a successful save or empty account.

At this checkpoint the browser transport/UI is implemented and locally verified with a controlled account-owner fixture. The Terminal storage migration and API compatibility changes are still in progress. The fixture is not PostgreSQL, RLS, live account persistence or production proof. PR #9866 remains Draft/HOLD.

Original program: `forex-r26-native-completion-20261020-sol-001`.
Macro operation: `forex-r26-owner-adoption-20261020-sol-001`.
Terminal operation: `forex-r26-account-owner-20261021-sol-002`.
Protected procedure: `Mastermind@a0faf7e44f76ac77c61e177738663544ddb6949d`.

## Existing authorities

- Authentication and session events: existing `window.MDXAuth` and `getSupabaseClient` from the shared theme. No separate identity store.
- Persistence: existing Terminal `public.alerts` with owner RLS. No new watch table or local-storage queue.
- Browser reads: explicit captured user ID plus Forex type filter, with row validation. An authenticated successful zero-row read is the only empty-account proof.
- Writes: named invoker RPCs. Client validation is only a usability check; storage must enforce every invariant independently.
- Evaluation and delivery remain with their incumbent owners. A daily/synthetic Forex quote cannot qualify finalized 4H monitoring.

## Stored row and rule

A saved row retains `id, user_id, symbol, condition, active, created_at`. Its `active` must be false. The owner derives `user_id` from `auth.uid()`; `symbol` equals the literal pair.

The condition has owner-assigned envelope fields:

| Field | Value |
| --- | --- |
| type | `forex_price_close` |
| schema_version | `1` |
| condition_id | The row UUID |
| revision | Positive owner-assigned integer, starting at 1 |

The canonical rule fields are:

| Field | Contract |
| --- | --- |
| kind | `price_close` |
| pair | EURUSD, USDJPY, AUDUSD, GBPUSD, USDCAD, USDCHF, USDMXN, USDBRL or USDCNH |
| quote_basis | `literal` |
| interval | `4H` |
| calendar | `fx-utc-4h/v1` |
| operator | `lt`, `lte`, `gt` or `gte` |
| threshold | Finite positive number in literal pair units |
| consecutive | Integer from 1 through 10 |
| expires_at | UTC ISO timestamp ending in Z; future for a newly saved rule |
| feed | Explicit null; no source has been admitted |
| origin_snapshot_id | Optional inert provenance, null or nonempty string of at most 256 characters |

Expired stored rows remain readable and deletable. Their existence never activates a rule. Unknown fields cannot grant ownership, activation, feed or delivery authority.

## RPC interface being implemented in Terminal

`save_forex_watch(p_id uuid, p_expected_revision integer, p_expected_user_id uuid, p_rule jsonb)`

- The expected owner must equal the currently authenticated owner before mutation.
- Expected revision 0 creates at a client-generated secure UUID. Reusing that ID with the same original rule can acknowledge the existing revision-1 row; a changed payload or later revision conflicts.
- Positive expected revision edits that owned row with compare-and-set, increments the revision, and returns its authoritative postimage.
- Response is one alerts row, either an object or a one-row array.
- The client never automatically retries a mutation. Unknown acknowledgments remain unconfirmed.

`delete_forex_watch(p_id uuid, p_expected_revision integer, p_expected_user_id uuid)`

- Same expected-owner fence and positive expected revision.
- Returns `{id, deleted: boolean}`. A successful current absence is a valid deleted state; it does not prove which earlier request caused the absence.
- Hard deletion does not provide a durable operation journal. Create idempotency is limited to the lifetime of the original row. The product does not replay old creates after deletion.
- CAS applies to the supported RPC/API flow. Existing direct owner table privileges are not represented as an exclusive RPC gate.

Expected error tokens are `forex_watch_revision_conflict`, `forex_watch_identity_conflict`, `forex_watch_not_found`, `forex_watch_invalid_condition`, `forex_watch_invalid_request`, `forex_watch_limit_reached`, `forex_watch_owner_changed`, `forex_watch_unauthenticated`, and `forex_activation_unavailable`. Missing functions and access failures render unavailable. Other write failures render unconfirmed.

## Browser behavior and recovery

Every user intent captures the account UUID and an authentication epoch. An actual sign-out followed by sign-in creates a new epoch even for the same account. Routine same-account `SIGNED_IN` confirmation (including tab-focus session recovery) and ordinary token refresh preserve the current epoch, drafts, open editor and pending-write reconciliation. A late response from an earlier epoch is discarded. Account changes clear rows, pending operations, the editor and its hidden JSON/form values.

Signing in may retain an anonymous prepared draft, but never saves it automatically. Only an explicit Save invokes the owner. Successful saves are shown only after validating the exact owner, ID, canonical rule, inactive state and revision in the returned row.

A 12-second deadline bounds client startup and each request. A timed-out mutation is not retried or described as failed to apply. Check status reads the exact ID. A matching postimage can confirm a save; an absent row after a write timeout remains unconfirmed because the original request may still complete. Current absence can confirm deletion. No durable outbox or cross-account replay exists.

Two-tab edit conflicts require an explicit reload of the saved version before editing again. Read failures, pending mutations and ambiguous writes suppress misleading empty-account copy.

## Local evidence and remaining qualification

`account_evidence/validation.json` binds the initial slice's source hashes and test results. `account_evidence/review-repair.json` preserves the independent REQUEST_CHANGES on 2d45507 and binds the subsequent auth/pending-state regressions and repair proof. The real builder/Jinja/browser flow is exercised against synthetic market input and a controlled account owner, with HTTP(S) blocked. Browser cases cover desktop/mobile, EN/ZH, light/dark, explicit sign-in/save, reload/edit/delete, two tabs, account switches, lost responses and failed readback.

The storage implementation must independently prove owner RLS, direct activation/family-escape rejection, strict rule validation, concurrent create/edit/delete semantics and current grants in an isolated PostgreSQL fixture. Production application requires the established migration owner and actual catalog receipts. A deployed authenticated user path and admitted finalized-4H source/delivery remain separate obligations.
