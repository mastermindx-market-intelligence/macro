# Earnings Wire Incremental Recovery Design

**Operation:** `earnings-wire-incremental-recovery-20260914-sol-001`
**Base:** Macro `878147de1cfbce89768ccf98a140d922ba1a6ce5`
**Procedure:** Mastermind Sol Skillpack `51b815ab9527e15c9218b049f622dc4d3e0bfbc4`

## Outcome

The public Earnings Wire must consume current, already-admitted earnings evidence without replaying the historical corpus on every hourly refresh. The user job is to open `/stocks/earnings/` and see current call records. The machine job is to project the canonical story-packet plane into deterministic public and private Wire products while preserving receipts, corrections, policy holds, and atomic publication.

The 10/10 state is a bounded hourly refresh whose work scales with the current public estate plus genuinely new/corrected forward events, not the complete transcript archive. Because the production workflow stages a fresh private publication root, an unchanged source still rehydrates the current admitted estate; the no-op fast path applies only when no private stage is requested. Completion requires live production to advance beyond 2026-07-29, not merely green tests or a merged PR.

## Verified failure

Production has 3,361 admitted routes and stops at call date 2026-07-29. The canonical story manifest and Terminal index each contain 29,364 matching event keys through 2026-09-11, including 2,392 events newer than the Wire. The manifest is about 19.6 MB and packet bodies total about 1.9 GB.

`build_earnings_public_wire.py` rejects manifests over 8 MB or 10,000 packets, then its full-corpus hydration design would download every packet before admission filtering. When fresh collection fails, the stale-existing guard replaces the causal error with `existing earnings-wire publication is older than 48 hours`.

## Authority and non-goals

Canonical event truth remains the immutable earnings story-packet manifest and its receipt-bound packet objects. Terminal's transcript index supplies event dates for bounded selection only. The route catalog remains the existing Wire projection state. No second earnings truth, queue, journal, retry plane, private pointer, or publication authority is introduced.

The repair does not publish historical backfill before the recovery floor; the floor date itself is inclusive so same-day source advances cannot be stranded. That corpus is separately valuable but is not required to restore current Wire freshness and would recreate the unbounded replay failure. Press, model-written summaries, releases, filings, slides, consensus, and market reaction remain outside this exact-evidence Wire.

## State contract

The redacted catalog advances from `earnings.public_wire_routes/v1` to `earnings.public_wire_routes/v2` by adding `forward_selection_floor_date` and bounded `deferred_packet_keys` continuation state.

For an existing v1 catalog, migration derives the floor once from the maximum dated event already published. For the current production state this is 2026-07-29. Every v2 publication preserves that original floor; it does not move to the newest call date. A fixed floor ensures a late-arriving post-floor call remains eligible for evaluation even after newer calls have published.

`deferred_packet_keys` contains only canonical `TICKER/TRANSCRIPT_ID` identities for source packets whose Terminal date is later than the current completed-call ceiling. It contains no facts, excerpts, hashes, object keys, storage paths, receipts, or private-member coordinates, is capped at the selected-work ceiling, and is reclassified against the bounded public transcript index on every otherwise-no-change refresh. Selection rejects a deferred-key overflow before any packet hydration, public rendering, or private staging begins. The writer always emits the field. The reader treats an early pre-release v2 catalog without it as an empty list so existing dry-run artifacts can be replayed safely. This is projection continuation metadata inside the existing route catalog, not a second queue, truth store, or publication authority.

The catalog's existing `source_generation_id` and `source_manifest_sha256` continue to identify the last accepted story generation. They are sufficient to retrieve and verify the prior immutable manifest. The floor and deferred identities are selection-policy metadata, not event truth.

A large source with no valid prior catalog fails closed with a clear bootstrap error. Small catalogs retain the full-hydration path for deterministic fixtures and initial installations.

## Selection algorithm

1. Validate the current mutable marker and byte-identical immutable generation manifest.
2. Load the prior redacted catalog and fetch its immutable story manifest.
3. Verify the prior manifest generation and SHA-256 against the catalog receipt.
4. Fetch the bounded Terminal transcript index and validate its generated-at ceiling and date map.
5. Always select every currently admitted route key, so the complete public/private product can be deterministically rebuilt and admitted corrections can remove stale pages.
6. Select every changed packet index present in both generations, regardless of date, so corrections to admitted or held history are re-evaluated.
7. Select a newly added key only when its Terminal call date is on or after the preserved floor and not later than the index's completed-call ceiling.
8. Fail closed if any newly added key lacks a canonical `YYYY-MM-DD` date. Historical additions before the floor are deliberately skipped; scheduled/future dates after the completed-call ceiling are deferred and logged without blocking completed calls in the same generation.
9. Hydrate, receipt-check, contract-validate, and apply the existing evidence admission policy only to the selected keys.
10. Build the complete public manifest from selected articles, preserving admitted survivors and adding newly eligible calls. If every selected packet is held or invalid, abort and retain the verified prior publication instead of publishing an empty catalog and deleting all public/private records.

Unchanged held packets do not replay because they are neither admitted, changed, nor newly added relative to the accepted source generation. After successful publication the catalog advances to the current source receipt, so those held keys remain known without a duplicate evaluated-key ledger.

## Bounds

Structural marker limits increase to accommodate the canonical index: 64 MiB and 100,000 packet entries. These are read/validation bounds, not permission to hydrate the corpus. Separate selected-work bounds of 10,000 packets and 1 GiB of advertised packet bytes apply before packet downloads begin. The latest measured recovery selects 3,361 admitted plus 2,392 candidates on or after the inclusive floor: 5,753 packets and 378.49 MiB, below both ceilings.

If a policy or correction wave changes more than the selected ceiling, the lane fails with a specific bounded-selection error and requires an explicit migration wave. It never silently publishes a partial catalog.

## Correction and removal behavior

A changed index entry is rehydrated even when its date is before the floor. If a formerly admitted packet becomes held or invalid under the current governed contract, it is absent from the new manifest; existing stale article pages and private record payloads are removed by the current publication cleanup paths. Source-manifest shrinkage or loss of an admitted key remains a hard error.

A newly admitted forward event receives the same deterministic public article, private member payload, context packet, feed, sitemap, weekly rollup, and route entry as an event admitted by a full build. No model call or alternate copy path is introduced.

## Failure behavior

Current marker/immutable mismatch, prior-receipt mismatch, missing or non-canonical transcript dates, selected-count overflow, an all-held/empty result, packet receipt mismatch, or contract failure aborts before publication. Scheduled dates beyond the index's completed-call ceiling are not evidence failures; they remain deferred until a later completed index. A source failure may retain a verified existing publication for at most 48 hours. Strict production state loading preserves the exact catalog-validation cause, and when fallback is unavailable the raised message includes both the causal fresh-source error and the stale-fallback error.

## Files and compatibility

Primary implementation lives in `scripts/build_earnings_public_wire.py`; the deterministic article and manifest contract in `engine/earnings_narrative/public_wire.py` remains unchanged. The ticker-dossier browser consumer in `site/assets/js/company-intelligence-dossier.js` is part of the compatibility closure because it validates the route-catalog schema before exposing exact record links. Tests live in `tests/test_earnings_public_wire.py`, `tests/test_company_intelligence_dossier_js.py`, and `tests/test_ticker_pages.py`. Workflow changes are only made if measured runtime or invocation semantics require them.

The builder loader accepts v1 for migration and v2 thereafter; the writer emits v2. The ticker-dossier consumer accepts both v1 and v2 so the schema rollout cannot silently demote exact record links to the generic archive during deployment or rollback. Because versioned JavaScript is served immutable for one year, the ticker template and every committed ticker page carry the first eight hex characters of the actual dossier asset SHA-256 (`a3f07e08`) rather than a hand-written stamp. Unknown schemas remain rejected.

## Acceptance and production proof

Tests must prove selection excludes pre-floor backfill, includes same-day and post-floor additions, defers scheduled/future entries without blocking completed calls, includes all corrections, rebuilds admitted routes, refuses an all-held empty publication, enforces bounds, migrates v1 state, preserves the floor, accepts both v1 and v2 in the browser, pins every immutable browser URL to the asset body hash, and retains the causal error.

Repository acceptance requires targeted tests, the owning CI pack, static/contract gates, and an adversarial review against this design. Production acceptance requires the hourly workflow to publish successfully; the live route catalog must have a new source generation and `verified_at`, its newest event must exceed 2026-07-29, a corresponding live article and first-page card must return current content, and the strict freshness audit must no longer report the 44-day/2,392-body outage.

## Routing receipt

`COGNITION_ROUTE: CHAT_INCLUDED_DEFAULT`
`CHAT_REASONING_MODE: PRO_MODE_EXCEPTION`
`WHY_PRO_MODE: The production incident requires long-horizon root-cause analysis, bounded data-plane redesign, adversarial proof, current-base reconciliation, and production acceptance in one continuous responsibility.`
`WHY_NON_PRO_INSUFFICIENT: Earlier bounded attempts established symptoms but did not complete the cross-layer selector, correction semantics, production-shaped replay, review, and release chain.`
`PRO_MODE_TASK_CLASS: HARD_DEBUGGING`
`EXPECTED_DURATION_MINUTES: 180`
`STOP_CONDITION: The exact repair is either production-proven beyond 2026-07-29 or stopped at a genuine security, authority, destructive-action, collision, or irreconcilable production gate.`
`ROUTE: Sol on Chat included Pro exception, with bounded Codex/Opus-capable review through the authorized Studio surface.`
`WHY NOT FABLE: The product thesis and state contract are frozen; implementation and review are bounded repository work, so scarce principal continuity is unnecessary.`

A bounded OpenClaw/OpenRouter architecture review was attempted read-only and returned no adjudicable conclusion; under `REVIEW_RETURN` it is `HOLD` and supplies no accepted claims. The merged provider fabric remains production-disarmed, so no Executive lifecycle state is inferred from local agent execution.
