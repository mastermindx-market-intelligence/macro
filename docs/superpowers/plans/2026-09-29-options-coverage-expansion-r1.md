# Options coverage expansion R1 implementation plan

> For agentic workers: execute inline with `superpowers:executing-plans`; use test-driven development. This is the first source slice of the Chairman-approved tiered expansion, not a new approval request.

**Goal:** Make the existing shared options universe capable of selecting an explicitly bounded 1,000-stock daily cohort (then up to 1,500), retaining existing roots and prioritizing supplied candidate symbols, with a non-writing preflight that reports selection rather than pretending collection has run.

**Architecture:** Extend `engine/options_universe.py`, already consumed by the canonical T1 resolver and AD denominator. Reuse `engine.universe_history.as_of_members` and its existing `data/universe/membership.parquet`; do not create another symbol registry. The legacy path remains byte-compatible in behavior unless an explicit `daily_expansion.enabled: true` configuration is supplied. Production configuration, collector/schedule/host state, and scoring gates are not modified in R1.

**Tech stack:** Python 3.12, pandas, existing NYSE calendar, pytest.

**Spec:** Chairman approval in the current conversation of the 2026-09-29 investigation; evidence at Macro #7889 comment 5888723981. Parent `WS:ADVANCED-DATA-OPTIONS`; broader approved scope remains market-wide EOD/OI where entitled, daily 1,000 then 1,500 qualified stocks, and separately owned 100 then 250-root Terminal intraday coverage.

## Source and custody

- Operation: `options-coverage-expansion-20260929-sol-001`.
- Protected procedure: Mastermind `c7407c6c77ef82cc6590401e80cc8f1868dc9085`, skillpack 1.0.1/bootstrap 1; INDEX blob `94d1af402598894372858793a5b1931019c5fa77`.
- Macro base: `d5e20a62b5da656f62b3cc06a7c7675c43f0de1a`.
- Sole source carrier: `claude/options-coverage-expansion-20260929`, isolated Studio workspace `/Volumes/Mastermind/worktrees/options-coverage-expansion-20260929-sol`.
- Direct execution reason: PRINCIPAL_JUDGMENT / LOWER_TOTAL_OVERHEAD for the bounded shared-resolver change and its source/clock boundary. No worker or provider is spawned.
- Open #7889 remains the host-placement repair; #7861 remains the heatmap/session repair. Neither carrier nor installed source is modified. Exact `options_universe` open-PR search returned zero; that is source-collision evidence, not a claim of global worker inactivity.

## Global constraints

- One canonical ThetaData Terminal/store/resolver; no new lifecycle, queue, registry, scheduler, source publisher, or background worker.
- No provider calls, entitlement purchase, service/process mutation, production configuration change, or automatic activation in this slice.
- Preserve the legacy selected roots and anchor priority. Never make a bigger count by dropping the old denominator.
- Stock counts use the existing equity-index membership classification, not the assertion that every options root is a stock. Roots outside that classification remain separately counted, not asserted to be ETFs.
- Membership is not optionability, collected chains, qualified Greeks/GEX, or predictive authority. All remain explicitly unmeasured by selection.
- No lowering the 90% source or Prophet admission/variance gates; no scoring/entry/trade change.
- No silent ticker-alias rewriting or historical replay/publication. Requested session, membership input digest, source caveats and all supplied priorities remain visible.
- Prior platform-denied raw-store/board inspections and the current compound source-symbol probe are not retried or delegated through another route. R1 uses the already recovered shared resolver and the separately readable published T1/membership interfaces.

## Review focus

1. Expansion turned off must perform no new membership read and retain legacy order/cap exactly.
2. A large list of ETF/unclassified roots must not satisfy the stock target.
3. Missing/stale/insufficient membership or an undersized total-root budget must refuse before any collection, never fall back to a silently smaller universe.
4. Candidate priority must not evict incumbent roots, invent optionability, translate class-share symbols, or permit malformed symbols/configuration.
5. Historical membership and current clock interpretation must use the existing owners and report their cold-start/gap caveats; a generated timestamp is not source freshness.

## Task 1 — shared expansion selector

Files: modify `engine/options_universe.py`; create `tests/test_options_universe_expansion.py`.

Interface: `plan_daily_expansion(expansion: dict, *, legacy_symbols: list[str], anchor_symbols: list[str], ledger=None, as_of=None) -> dict`. Result contains ordered symbols, classified-stock count, retained-root count, separately counted unclassified roots, normalized priorities and uncovered priorities, source session/digest, explicit collection/qualification nonclaims. `gex_symbols(cfg)` calls it only for explicit enabled configuration and returns the selected list through its existing interface.

- [x] Add failing tests for all five review cases, 1,000/1,500 targets, invalid integers/booleans, total ceilings, membership groups and date boundaries.
- [x] Observe the missing-function/integration failures.
- [x] Implement deterministic anchor -> supplied priorities -> retained legacy -> equity-group fill; use the existing membership resolver, not a parallel interval algorithm.
- [x] Run the full focused suite and regressions available to this scope; no full sparse-tree suite.
- [x] Commit tested source.

## Task 2 — executable, non-writing preflight

Files: create `scripts/plan_options_coverage.py`; extend the new test suite; enroll the test in its existing appropriate CI job without creating a new runner/workflow.

CLI: `python -m scripts.plan_options_coverage --as-of YYYY-MM-DD --target-stocks 1000 --max-total-roots 1500 [--priority ROOT ...]`. It reads existing configuration/membership, creates no file or directory, emits JSON to stdout and exits 0 only for a feasible selection. Refusals emit a typed reason and exit 2. It never invokes a collector or writes configuration.

- [x] Add failing CLI tests, including no new data/site files and machine-readable refusal.
- [x] Implement the CLI through the shared resolver; no second selection policy.
- [x] Exercise the CLI/module against an exact committed membership input where lawful; record input/source digests and actual selected counts, never a live-coverage claim.
- [x] Run contract enrollment and focused checks.

## Task 3 — durable source delivery

Files: R1 research result and existing Agent OS handoff schema under the parent workstream.

- [x] Record source delta, tests, denied actions, unchanged production state and the exact remaining gates.
- [x] Push the same source branch; create a draft PR; read back exact head and changed paths.
- [ ] Obtain exact-head CI/review through the existing owners; do not self-claim independent review, merge/deploy or hosted acceptance.

## Next tightly coupled phase

Qualify the market-wide EOD/OI adapter against the current official v3 schema, while preserving the existing per-root Greeks path (there are no Greeks flat files). The inspected official subscription documentation has an account-wide shared concurrency budget, not additive per-asset quotas. Raw-store normalization, actual entitlement, licensed-host recovery and two ordinary source-to-consumer cycles remain production prerequisites. Intraday stays with Terminal.

MISSION_COMPLETE: false

## Continuation slice — source-session coverage in the existing audit

The approved coverage-honesty requirement is implemented through `lib/options_coverage.py` and the existing `scripts/audit_options_entry_coverage.py` writer, not another collector, store, or registry. The state producer sets row `as_of` to the latest source date; that outer date must never qualify all four source clocks.

- [x] Add red-first tests for independently dated sources, duplicate/conflicting root observations, missing versus empty inputs, malformed/future/non-session clocks, and Monday-before-close comparison semantics.
- [x] Implement `source_session_coverage(frame, *, comparison_session, date_columns)` as an additive shared report of unique ticker identities and exact source-session alignment. Return named per-source ticker buckets; do not infer optionability, provider SLA freshness, complete chains, or a qualified ticker count.
- [x] Wire that report into the existing audit's returned/written `coverage.json` as `source_session_coverage`; reuse the existing exchange calendar and the same frozen run instant. Keep old feature-presence counts and promotion logic unchanged. Prove the real writer against operation-owned synthetic files only; do not read denied production data.
- [ ] Enroll through the already-wired coverage-object test suite, run existing audit regressions, and preserve measured results on the same PR.
