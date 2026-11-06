# Shared Shell: exact membership observation

Status: additive source-review slice for Macro #7949; not a released or wired UI.
Native origin: Shared Shell Frame41 / 1V82-1, Check saved status.

## Purpose

A status check must answer what the selected watchlist currently contains without submitting the save again.
`WatchStore.symbols.inspect(listId, symbol)` belongs to the existing WatchStore, not a new account, retry or persistence service.
The implementation starts from the original current-source store, NOT the R16/R17 conservative-retry candidate.
The automatic retry-policy dispute, R15 write-path repairs and R17 candidate remain separate review items.

## Operation

Use the exact list ID and the existing identity owner's symbol. The method trims whitespace but does not uppercase, convert a listing, change market or infer currency.
It captures the incumbent auth epoch/user/client, checks the exact owned watchlist, then reads only the requested list/symbol membership.
Each request uses at most two provider SELECTs. It does not enumerate the user's other lists or query sixty memberships.
A per-call timer reuses the store's existing cloud-read deadline. It never retries the request.
A late ownership response after timeout cannot start the membership request. Late responses cannot update caches or publish status.

The result has `state`, `membership`, `listId`, `symbol`, `listName`, `observedAt`, `readRetryAllowed`, and `writeRetryAllowed`.
`observedAt` is when this client observed the membership response, not quote freshness or the original save time.
`writeRetryAllowed` is always false. `readRetryAllowed` describes an explicit user-driven recheck, never automatic polling.
Old-session results redact IDs, names and observation time. Provider exception/SQL details are not returned.

## State to interface mapping

| State | User-facing meaning | Safe action |
| --- | --- | --- |
| present | NVDA is in AI research. / NVDA 已在 AI research 中。 | Return to the setup. Do not claim this request inserted the row. |
| not-confirmed | Not confirmed yet. / 尚未确认。 | Check again without another insertion. |
| unavailable | Could not check this list. / 暂时无法核对这个列表。 | Retry the read. Never convert failure to absence. |
| no-session | Sign in to check this list. / 登录后核对这个列表。 | Use the existing auth flow; no anonymous fallback. |
| stale-session | Account changed. Reopen this check. / 账户已更改，请重新打开核对。 | Drop the previous response and use fresh context. |
| invalid | This item could not be identified. / 无法识别此项目。 | Return to the original setup; do not guess IDs. |

The destination name is user data: render it as text and do not translate it.
A present observation does not settle the attribution, cancellation, retry or lifecycle of the original save.
Absence does not prove the original request cannot still commit. Never enable Add again from this result alone.
No pending insert, full-list push or tombstone is cleared. The current active list, local cache and holdings are unchanged by this method.
The existing account UI still must hide prior-account content immediately when auth changes; this read result is not a new global auth subscriber.

## Source and validation

Base: Macro39c84a1a35836fcde5cf170b3237ebc118a6af4b and #7949's ee7713f58ea370899e556fb3815bdb847288197a share WatchStore blob2933cca572afc01d5108a521b4c3aff0a6502f0d.
The proposed change adds only symbolInspect and its public symbols.inspect binding. Existing write/retry bodies remain byte-identical.
Template and shipping site copy must remain byte-identical; ordinary cache stamping and release proof are still required.
The new tests reuse the existing multi-list SHIM/FAKE_DB and are registered from that test module, not a second provider harness.

Known evidence limit: the late-membership auth test wrongly expects no global events although the test itself calls onAuthUser(null), which emits the legitimate local event.
The correction request was platform-blocked. The assertion remains present and RED; no skip/xfail or alternative correction is part of this slice.
The result itself is stale-session with the expected redaction, but this is not a blanket all-tests-pass claim.
All prior R17 test-contract and native-runtime verification refusals remain untouched.

## Acceptance still owed

Independent source review; resolving the held attribution assertion; actual cloud/RLS/account proof; existing UI invocation and returned-state rendering; keyboard/focus return and EN/ZH/device evidence; current-base and required CI; normal release.
No source merge, production deployment, database migration, real save, new retry, Paper edit, background worker or watcher is implied by this review slice.
