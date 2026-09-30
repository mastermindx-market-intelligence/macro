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

The expansion suite is enrolled alongside the existing coverage-object suite in the `workflow-yaml` code gate. It originally ran in `ric-w2-surface`; the continuation moves it to the broader family-coverage step to close the measured packing regression described below. No new CI job, runner, workflow trigger or waiver was created.

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

Initial R1 focused regression command:

```sh
python -m pytest tests/test_options_surface.py tests/test_options_universe_expansion.py tests/test_universe_history.py -q --tb=short --basetemp <operation-owned-temporary-directory>
```

Initial R1 result: **85 passed** (49 expansion cases and 36 existing surface/membership cases). `git diff --cached --check` passed. These are local focused results, not a full repository or hosted CI pass. The full sparse-tree test suite is deliberately not run under the existing repository rule.

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

## Continuation: source-session coverage reaches the real audit writer

The existing options-entry state producer sets row `as_of` to the maximum of its four input dates (`engine/options_entry_state.py`); the original audit counted non-null values without reporting source-date alignment per ticker. A current row date therefore could not answer how many input observations matched the comparison session.

`lib/options_coverage.py::source_session_coverage` now provides that additive report, and the existing `scripts/audit_options_entry_coverage.py::run` emits it in its returned and written `coverage.json`. It reuses the existing exchange calendar with one frozen run instant, so Monday-before-close compares with the last settled Friday. GEX, skew, IV-spread and flow retain separate source-date columns. No overall row date or new generation timestamp substitutes for a missing source date.

Counts are by unique ticker strings. Identical duplicates collapse; conflicting date observations, including a dated row beside a null, stay conflicts rather than selecting a favorable row. Output contains exact ticker lists under matching-session, older-session, future-session, missing, invalid and conflict buckets. Missing inputs report unknown, not zero observed coverage. Symbols' class-share punctuation is preserved. Naive midnight timestamp storage is accepted as a session date; aware/non-midnight timestamps require an owner-defined conversion and are not guessed. Malformed non-scalar cells cannot crash the report.

This is **source-session alignment only**, not certified vendor freshness, optionability, complete chains, Greek quality, or scoring authority. Older dates are relative to the comparison session, not an assertion that a vendor missed its own availability deadline. `qualified_ticker_count` remains null even when all source dates match. The existing feature-presence counts, source providers, writer location and promotion thresholds are unchanged.

The real audit writer was exercised using operation-owned synthetic files only. Its two-ticker Monday fixture preserved two non-null GEX verdicts, but reported just one GEX date matching Friday and zero tickers matching all four source dates. The output was read back from the actual existing `coverage.json` writer; the input parquet bytes stayed identical. This is integrated synthetic-path proof, **not live data acquisition**. Evidence is `COVERAGE_EXPANSION_R1_SOURCE_SESSIONS_2026-09-29.json`, with exact input/output and implementation hashes.

Red-first proof: 19 missing-function/missing-writer-section cases failed, then passed. An additional adversarial pass reproduced two defects (non-scalar date cells and naive midnight storage), both repaired. The latest combined regression ran **189 tests, all passed**: expansion, options-surface, membership, import pinning, coverage-object and the full existing entry-audit suite. The 25 new source-session cases are in the already-wired coverage-object suite; there is no new CI job, runner, workflow or waiver.

No production options source, collector, store, process, subscription, publication job or gate was changed. The approved 1,000/1,500 stock acquisition and Terminal intraday goals remain unproven and incomplete. This continuation fixes the real R1 CI defect and adds the source-clock accounting needed to measure that future expansion honestly.


## Continuation: keep the shared-universe tests in their proper CI job

The full continuation contract-delta run completed with **two introduced findings**, both the same test-enrollment issue: the expanded CLI suite pulled the narrow `ric-w2-surface` job into the ordinary `build_free_content.py` and `engine/prophet/plan_book.py` packing probes, making 133 jobs exceed 132 and 128 exceed 127. The underlying guards were correct. The correction moves the entire expansion suite into the already-selected `workflow-yaml` options-coverage step and restores the ETF-surface step to its own original suite. No test, ceiling, failure, code gate, or review requirement is removed. Product implementation hashes in the synthetic writer receipt are unchanged by this CI-only repair. The exact packing-guard and refreshed contract results are recorded on the same PR after completion.

The corrected enrollment passed the actual existing packing assertion together with both affected suites: `python -B -m pytest tests/test_ci_pack.py::test_exclusive_curation_narrows_ordinary_code_prs tests/test_options_coverage_object.py tests/test_options_universe_expansion.py -q` returned **111 passed**, exit 0. This preserves all 51 expansion and 59 coverage-object cases and the packing ceilings. The earlier 189-test combined code regression remains valid for unchanged product code; the counts overlap and are not added together. A fresh full contract-delta run is separately owned and pending at this source checkpoint; the exact result belongs in the current PR receipt, not an invented pass.


## Continuation — legacy-provider isolation and incomplete-baseline refusal

Protected procedure was re-pinned to Mastermind `1405c634d8a0b0d3b05305fdd8d62e7b0b520e93`; INDEX and the previously loaded companions were read at that commit and byte-identical. On entry, exact-head CI `36603640507` for `4d5eb3e56d04a17721e76f55a988eefcb7ed8c24` had concluded SUCCESS, including all twelve packs and ci-gate. The prior local contract log also concluded zero introduced / zero inherited findings. Independent review had not returned; this was never merge or live acceptance.

The permitted inspection of two existing noncanonical consumers exposed an activation hazard: both `build_options_flow.build` and `build_polygon_gex.accrue` fed the expanded shared cohort into their legacy Massive/Polygon request paths. The new `legacy_gex_symbols` entry point delegates to the SAME existing resolver after removing only `daily_expansion` from a copied configuration. The two legacy consumers now use it. Their incumbent anchors, basket order/cap, request guards and shared configuration are preserved; the canonical expansion is not disabled. No new provider registry, collector, source store or policy list is introduced.

Seven regression cases first failed: five missing legacy-isolation cases and the two actual consumer entry paths attempting expanded membership. After the isolation change, the three involved suites passed 215 tests; the combined eight-suite regression passed **353 tests**. Provider calls were stubbed in the entry-path cases; these results establish source behavior, not real provider capacity or live collection.

A second reproduction exposed a preservation gap: with `include_baskets=true` but no basket members readable, the expansion and its CLI could still report selection_ready while retaining only the anchors. A new larger membership set could conceal the missing incumbent cohort. Two tests failed for this case; two control cases preserved anchor-overlapping baskets and legacy best-effort behavior. The resolver now refuses enabled expansion when the requested basket cohort is empty/unavailable, and the CLI requires the same baseline check via `require_baskets=True`. Legacy callers with expansion disabled retain their prior behavior. This does not certify a partially populated membership file as complete.

**The final regression execution was explicitly platform-blocked before a process handle. It was not retried, split into smaller tests, delegated, or moved to another runner. The incomplete-baseline repair therefore remains UNVERIFIED. The 353-pass result predates that repair and must not be attributed to the final candidate.** A separate attempted process-census diagnostic was also refused and was not repeated. Neither refusal is an unknown source-write effect.

The earlier local contract process `36138` began before the additional baseline-repair edits. Its result cannot be accepted as exact-final-source proof. Consume its original retained result only; do not launch a duplicate or substitute its outcome for the final blocked regression. Its output belongs to the existing operation evidence directory as `legacy-isolation-contract.log`.

Source preservation after this refusal must not cause another executor to run the denied test command. This checkpoint is not release-ready: use a commit-level skip instruction for the ordinary pull-request test workflow, retain DRAFT/unarmed/no auto-merge, and explicitly hold source release. GitHub's documented skip semantics cover push/pull_request only; the separately inspected pull_request_target authority workflow checks the trusted base and never materializes candidate code. No workflow, protection, test, threshold or requirement is removed or waived. A skipped or absent check is not a success. Any later test execution requires a permitted platform recovery, not removal of the marker merely to get a refusal through elsewhere.

The data dependency has materially changed independently of this source patch. MACRO-04's existing #7889 return reports that the intended M1 has zero roots in its tiers despite a healthy-looking manifest, and that no runner currently carries m1-theta. #8203's resolver hardening is merged at `54f62e4d4b25c4e475ece482aff856d052e42e67`; it is not a store refill or host recovery. This is attributed owner evidence, not a new inspection of the denied host/store. #7889's W4 hold remains; #7861's separate producer code already has its own semantic acceptance and conditional source-release owner, so it was not re-reviewed or taken over here.

**MISSION_COMPLETE: false.** No production configuration, provider subscription, collector, raw store, licensed Terminal, installed host service or scoring gate changed. 1,000/1,500 acquired and qualified stocks remain unproven. The remaining gates are permitted final verification plus independent review, authorized source-host/store recovery, and actual acquisition-to-consumer proof; another configured-universe count is not their substitute.
