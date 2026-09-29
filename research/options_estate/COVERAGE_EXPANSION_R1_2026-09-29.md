# Options coverage expansion — R1 source and evidence

## Outcome and current state

The Chairman approved the September 29 tiered expansion: broad ThetaData EOD/OI where entitled; 1,000 then 1,500 stocks with qualified daily options analytics; separately owned Terminal intraday coverage; priority for Prophet candidates without weakening quality or promotion gates.

R1 implements the first source slice, **BUILT_NOT_PROVEN**: the existing shared options-universe resolver can now select 1,000 or 1,500 membership-classified stocks while retaining every incumbent root. A real executable, non-writing preflight measures that selection using existing inputs. This is **not** a provider acquisition, a production deployment, a completed current-candidate integration, or proof of qualified Greeks/GEX coverage.

No production configuration was enabled. No provider calls, entitlement purchases, raw-store writes, host process/service changes, collector activation, scoring changes or deployment occurred.

## Exact source and ownership

- Operation: `options-coverage-expansion-20260929-sol-001`.
- Macro base: `d5e20a62b5da656f62b3cc06a7c7675c43f0de1a`.
- Source branch: `claude/options-coverage-expansion-20260929`.
- Protected procedure: Mastermind `c7407c6c77ef82cc6590401e80cc8f1868dc9085`, skillpack 1.0.1/bootstrap 1, INDEX blob `94d1af402598894372858793a5b1931019c5fa77`.
- Parent: `WS:ADVANCED-DATA-OPTIONS`; this is not another workstream, registry, collector or scheduler.
- Macro #7889 retains store-host placement / W4 admission at `ff11820b52be465cdaca48418634b0ccdaae2629`; #7861 retains aligned-source heatmaps at `ad114ece05c1c5a9a578d395195dde7e28dca533`. Both were observed open/draft; neither is altered or adopted by R1.
- Direct execution was retained for principal judgment and lower total overhead on the bounded shared-resolver contract. No external worker, provider session, or Executive Job was started.

## Implementation

`engine/options_universe.py` remains the shared resolver. Its legacy order and cap are unchanged when `daily_expansion` is absent or explicitly disabled. The documented T1 resolver and AD denominator already consume `gex_symbols()` (AD1T1 frozen cadence specification section A2).

When explicitly enabled, the resolver reads the existing `data/universe/membership.parquet` in one bounded snapshot and delegates membership-date interpretation to the existing `engine.universe_history.as_of_members`. It records the input hash and membership cold-start/gap caveat. It does not call the membership owner's directory-creating read helper.

Selection order is anchors, supplied priorities, all legacy roots, then existing equity-index groups (S&P 500, S&P 400, S&P 600, Russell 2000). Names are deterministic within each canonical group. This ordering is **collection scheduling**, not a return prediction or a stock ranking. The legacy and priority sets are never silently truncated to hit a stock count.

The stock target and total-root budget are separate. A name outside the existing equity-membership classification is retained and counted separately, not automatically labeled an ETF or a non-stock. Membership does not prove optionability. Invalid budgets, malformed symbols, conflicting or non-session dates, insufficient membership, malformed/null/reversed date intervals, and an inadequate total-root budget refuse before collection. Class-share punctuation is not silently translated.

`python -B -m scripts.plan_options_coverage` is the executable preflight. It reads existing configuration and membership, emits JSON to stdout, and does not write product data/configuration or invoke a collector. A named selection refusal returns exit 2. Required CLI arguments are `--as-of`, `--target-stocks`, and `--max-total-roots`; `--priority` is repeatable. No historical date from this evidence is installed in production configuration.

The new hermetic suite is enrolled in the existing `ric-w2-surface` code-gate job, alongside `tests/test_options_surface.py`. No new CI job, runner, workflow trigger or waiver was created.

## Real-input selection proof

Evidence: `research/options_estate/COVERAGE_EXPANSION_R1_SELECTION_2026-09-29.json`.

The real CLI was exercised with immutable inputs read from the pinned Macro commit, staged only in the operation's evidence workspace. The proof process redirected `config.data_dir()` to that evidence copy; no installed configuration or canonical store changed. Priorities were MU, ARM and INTC. The comparison session was September 28.

| Requested classified stocks | Selected roots | Classified stocks | Old roots retained | Added roots | Roots not classified as stocks |
|---|---:|---:|---:|---:|---:|
| 1,000 | 1,082 | 1,000 | 375 | 707 | 82 |
| 1,500 | 1,582 | 1,500 | 375 | 1,207 | 82 |

All three supplied priorities were present. The input had 2,859 eligible distinct equity-membership symbols. The 82 other roots are **not** asserted to be 82 ETFs. `qualified_stock_count` remains null and `collection_started` remains false.

Membership input: 78,300 bytes, SHA-256 `602f0cf393331653175e199a3249785ee40040c871501625d9dfc4b56a9b7556`. Basket input: 305,944 bytes, SHA-256 `b968e9812f60494bd02bbc0d5ad4b8dc67dcb90a939426728e9db6befba9678a`. The receipt pins exact code hashes and ordered selected-symbol hashes. The proof was repeated after interval validation changed; both selected sets remained identical.

## Verification

Red-first: 38 missing-selector/integration failures and one legacy-pass control; then 39 passes. The missing CLI produced three expected failures before implementation; then the expanded suite passed. Adversarial null/reversed membership intervals produced three failures before strict input validation; all passed afterward.

Current focused regression command:

```sh
python -m pytest tests/test_options_surface.py tests/test_options_universe_expansion.py tests/test_universe_history.py -q --tb=short --basetemp <operation-owned-temporary-directory>
```

Result: **85 passed** (49 expansion cases and 36 existing surface/membership cases). `git diff --cached --check` passed. These are local focused results, not a full repository or hosted CI pass. The full sparse-tree test suite is deliberately not run under the existing repository rule.

The first test run used the host's shared pytest temporary directory and produced unrelated cleanup warnings. Subsequent runs use an operation-owned unique temporary directory and finish without those warnings. No other session's files were removed or repaired.

## Remaining release and product obligations

1. Exact-head contract/CI and independent review; do not treat source push or green tests as acceptance.
2. Qualify the **whole shared consumer graph** before activation. `gex_symbols` serves multiple consumers, not just ThetaData; enabling it must not accidentally increase prohibited legacy vendor activity or alter an unreviewed denominator.
3. Wire dynamic Prophet/candidate priorities from the existing owner under its source/clock contract; R1 currently accepts explicit priority inputs, not an automatically refreshed board feed.
4. Verify actual ThetaData entitlement and the shared provider request budget. Qualify the existing licensed host, keep one Terminal/store, benchmark incremental acquisition, and integrate market-wide EOD/OI without inventing Greeks flat files.
5. Complete the original host-placement and aligned-source repairs through their existing gates. The M1 process-pressure finding remains unrepaired and is not proven to explain every stale artifact.
6. Prove optionability, same-session source alignment, per-feature completeness/freshness, publication and consumer use over ordinary scheduled cycles before reporting 1,000/1,500 qualified daily stocks.

## Denied actions and effect reconciliation

The earlier raw-store and board inspections were explicitly blocked by the platform; this turn's compound inspection of ThetaData collector/topup/backfill symbols, related PRs and the local sparse wrapper was also refused. No denied action was retried, delegated, rephrased, or moved to another carrier. Independent shared-resolver development used the already-read resolver and separately available published T1/membership interfaces.

One initial test-file write returned `Session terminated`. Same-carrier metadata reconciliation proved the file absent; one bounded technical recovery wrote and verified the smaller chunks. Later writes were acknowledged. No modifying effect remains unknown.

**MISSION_COMPLETE: false.** This record is a cumulative source checkpoint, not a transfer of custody or a background execution claim.

## Continuation: file-entry CI repair

Current continuation authority is the Chairman's same-chat instruction to continue. Protected Mastermind pin is `0b3bdf78be9b86bc3672f224ddacf80854a4c3fb`; INDEX and the required active/reconciliation/closeout companions were re-read and are byte-identical to the prior loaded pin.

Exact-head CI run `36563918232` concluded failure: eleven code packs passed, but `ci-pack-9` failed `tests/test_check_script_import_pinning.py::test_unpinned_entry_scripts_only_shrink` because the new CLI did not pin its repository before imports. This was a real R1 defect, not an inherited or waived check. Two additional real subprocess tests reproduced the defect before the repair: foreign-cwd/PYTHONPATH imported an unrelated `engine` package, and isolated Python file execution could not resolve `engine`.

The CLI now pins its own checkout using the established `_ROOT` / `sys.path.insert` pattern before importing repository packages. No baseline, waiver, CI policy, provider, production configuration or collection behavior changed. The selected-set algorithm is unchanged; the earlier immutable selection receipt remains evidence of its exact recorded code version, not a claim that later script/test hashes are identical.

Verification after repair: the expansion, options-surface, membership and complete import-pinning suites returned **98 passed** with exit 0. The CLI's two new subprocess cases cover ordinary and isolated Python startup from an unrelated working directory. The original CI failure remains preserved; fresh hosted proof and independent review are still required for the repaired head.

The Executive read preflight succeeded but reports `mode=readonly`; it cannot originate a reviewer via this ingress. No dummy modifying call or duplicate review was submitted. The existing repository reviewer request remains unconsumed. Denied provider/store/board inspections remain excluded; no alternate carrier or actor was used to repeat them.
