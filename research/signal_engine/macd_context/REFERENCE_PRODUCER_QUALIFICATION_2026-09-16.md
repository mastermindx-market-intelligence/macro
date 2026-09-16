# MACD study: historical reference producer qualification

## Capability delta and limits

Before: the failed July control had an unqualified original execution/publication clock. After: its actual GitHub producer job, checkout, cache-restore keys, several environment versions and Git publication are tied to primary-source receipts. The complete original working-state inputs are still NOT recovered. This is a material source qualification, not successful board reproduction or a Prophet signal upgrade.

Continue existing PR #7177 from `b72178fa16db09d4cba7df48a97c4d649bcaa38c`; no new program, backfill, replay owner, ledger or trading authority. Current protected Skillpack: Mastermind `e8803ba3d3ee928d150d7dcac1a1e2bad2dc0d48`, schema1/version1.0.1/bootstrap1 compatible; required companions read at that commit and unchanged from the previously loaded versions. Macro source comparison: `c359ed4403c9b8a8d097a8839c99448188618298`.

## 1. The reference's clocks are distinct

Existing reference board: price/as-of date July 15, 2026; Git blob `786e4fc2ae0e46b1581a9fcf708a64c30cd93e2c`. This pass does not reopen its security-level input comparison or compute returns.

| Evidence | Exact identity or observed UTC time | Meaning |
|---|---|---|
| Triggering push | `1f72b8743c36ae76f9098ab03b8e48bfde3458dc` | Event that queued the workflow; not the eventual checkout |
| Workflow run | `29589773634`, created July 17 at 14:52:22Z | Run metadata; not proof that its job was already executing |
| Producer job | `87936049727`, started July 17 at 16:22:16Z | Actual job interval begins |
| Checkout after checkout action | `413d6e9038f2ac12ee231e6e067ef4d400fff2a3`, logged at 16:22:25.849919Z | `git log -1 --format=%H`; subsequent pull reports already up to date |
| Build-site group | July 17 at 16:26:23.886850Z | The `macro dashboard + US stocks (build_site)` invocation; component output is buffered, not an exact per-stock decision timestamp |
| Repository publication commit | `f1f127e1ecbd24cad018af190be4793b60eb6fcc`, committer time 17:44:56Z | Commit metadata; not customer-serving proof |
| Successful main push observed | July 17 at 17:45:09.990638Z | Job log reports `b8ec17579d5..f1f127e1ecb main -> main` |
| Customer-visible availability | Not recovered | Do not substitute commit time or the price stamp |

The workflow explicitly checks out moving `main`, pulls again, and rebases before publication. Therefore trigger, executed checkout and publication commits must remain distinct. Seven declared source paths match byte-for-byte across those three commits and replay vintage `ff745b1ab54256b0188688cc5815e6675e4edef5`: the stock-library builder, site builder, entry-signal engine, stock-score engine, residual-alpha engine, requirements file and workflow. Different commit names are NOT evidence that those seven implementations changed; full dependency closure is not certified.

Raw historical log SHA256: `25343df31807d5922f66bddf02df5c7f6674084b76d3570ee7265ee28b38832b`. Bounded exact log excerpts and source/blob identities are in `replay_publication_clock_20260916_r3/`. No full log or credential values are published.

## 2. Git alone is not the complete producer input state

The historical log identifies these restored cache keys: `breadth-closes-engine-29542087837`, `smallcap-closes-engine-29542087837`, `midcap-closes-engine-29542087837`, `china-breadth-closes-29565416724`, `hk-breadth-closes-29565416724`, and `intraday-29590275868`. The workflow also restores attention data from R2. A cache key proves what restore was reported; without its object body/digest it does not certify the values used.

The workflow runs signal/regime recomputation and world-state preparation before rendering, but these steps are resilient: successful job completion does not prove every recomputation succeeded. Its publication policy commits `site/` and excludes per-build `data/` changes from that commit; this is not evidence that every local copy was immediately deleted. Consequently a publication Git tree is not an automatic snapshot of all working-state inputs consumed by its rendered board. No missing data is reconstructed from today's values in this pass.

The current GitHub artifact listing for run `29589773634` returned total_count 0. The current cache listing for the exact original breadth key returned total_count 0. These are bounded availability observations, NOT proof that no original snapshot exists in the existing Data OS/R2/host archives or that no artifacts ever existed. Other cache bodies remain unqualified.

The actual producer invokes `scripts.build_site`, which in turn calls `build_stock_library.main()`. The historical site builder reads the prior `us_standouts.json` before calling the library near the end of the build; its source explicitly notes that one-build lag. This is another reason not to equate a final JSON blob's Git timestamp with the exact decision every customer saw. No current UI defect or historical customer-serving result is inferred without surface-specific proof.

## 3. The environment is another distinct input

| Component | Historical job evidence | Current research interpreter |
|---|---|---|
| Python | 3.12 environment; patch version not recovered | 3.14.7 |
| pandas | 3.0.3 | 3.0.5 |
| numpy | 2.5.1 | 2.5.2 |
| pyarrow | 25.0.0 | 25.0.1 |
| scipy | 1.18.0 | 1.18.0 |

Historical package versions come from the original job's `pip install -r requirements.txt` output. The unchanged requirements file uses version floors, not a complete resolved lock. The listed differences are NOT demonstrated causes of the failed control. They must be preserved as reproduction conditions rather than silently assumed equivalent or blamed for the mismatch.

## 4. Scientific ruling

The July15 price stamp, July17 generation/publication evidence, Git revisions, mutable cache restores, local recomputation and dependency versions answer different questions. Do not collapse them into one as-of date. Do not choose a timestamp, source snapshot or benchmark because it improves agreement. The earlier exact-function experiment proves calendar sensitivity; this new producer evidence does not certify a universal historical clock override.

The existing full control remains 0.5769 agreement versus 0.85 required. No new full control, security-input census, return calculation, fitted score, probability or live trading rule was produced. The originally blocked security-level census remains held and was not retried or reconstructed. This metadata investigation is path-disjoint: it reads producer Git identities, execution logs and archive availability, not the refused per-security comparison.

## 5. Repair the actual CI omission, not the gate

Remote `contract-delta` job `104958128535` rejected this PR because `tests/test_prophet_pit_replay_alpha_result.py` and `tests/test_prophet_pit_replay_sparse_inputs.py` were not named by a workflow run step. Both are now included in the existing `prophet-anticipation-intake` job alongside `tests/test_prophet_pit_replay.py`. No waiver, new job, new pack, dependency change or acceptance-threshold change was added.

The exact amended YAML run command was extracted and executed locally. Process73442 exited0 with 199 tests passing. This proves the newly wired step on the current research interpreter; it is not a conclusion about remote repository CI or the original production environment. The existing differential contract checker also completed: process60217 exit0, zero introduced and zero inherited findings against main `c359ed4403c9b8a8d097a8839c99448188618298`. These local results do not mark remote checks green.

## 6. Exact continuation and no-redo boundary

The next scientific dependency is the original producer-state evidence: the existing data/replay owners must establish immutable bodies or equivalent verified source reconstructions for the restored caches and relevant per-build state, with the execution/source/environment clocks kept separate. A missing result from the two queried GitHub endpoints is not permission to declare all archive avenues exhausted. After that qualification and lawful clearance of the separately blocked security-level census, run the SAME canonical control on a declared contract. Keep the 0.85 floor and all existing temporal/data guards.

Independent source review remains separate from scientific acceptance. Reviewers receive the existing replay source/tests, CI wiring and the bounded metadata evidence, not instructions to redo market calculations or access the blocked input census. Native GitHub review, if accepted by existing repository policy, does not authorize a worker to edit, merge, deploy, change budgets or lift the Sol hold. No new Executive operation or provider session is claimed by a PR review request.

Preserve the completed original/expanded crossover study, repair attribution, holding/exit review, five-benchmark overlay, 48 contrasts, context joins and six-group adverse recorded-score audit. Do not invert the archived score, pool its overlapping windows into independent confirmations, fabricate current-v3 H21 or the specified SPY/RSP-divergence support, or market a 75–76% diagnostic rate as a calibrated trade probability. Long-Hold/B4/Portfolio/Evaluation retain their existing ownership; DNR:KILL-OUTCOME-AUDITION and TOI/Temporal Grain/Elliott holds remain.

Current outcome remains PARTIAL: stronger measurement and source qualification, no new accepted stock-selection edge, probability, signal, entry, sizing, plan, trade or customer-facing change. Direct-work reasons: LOWER_TOTAL_OVERHEAD for a one-step CI repair; PRINCIPAL_JUDGMENT for historical-clock and source-eligibility interpretation. The live Chairman continuation provides research intent; it does not itself release production or source-review holds.

## Recovery and cache-lineage qualification

The interrupted save was reconciled on the same Mac/carrier: all ten original evidence-file hashes, this report and the Agent OS handoff matched the saved verification receipt. The old process handle was unavailable, so no original process exit status is invented. Current protected Skillpack is Mastermind@5ee11ab1e993616f3568cfca4069cb21fa61fd8f. Current main comparison ec44523d17eedeea35bdf4513a0d4843a4e81a64 preserves the same AGENTS, CLAUDE, CI manifest and contract-checker source blobs. The exact replay CI step passed again: 199 tests in 226.27 seconds.

The original US cache chain is now traceable through two producer runs. Engine job87786234813 in run29542087837 restored US breadth/smallcap/midcap cache keys from run29470063998, then saved new engine-keyed caches on July17 around04:07Z. Its same-run collect job87766254630 was cancelled. The upstream run29470063998 had a successful collect job87531291811; its engine job87544560056 restored the same-run collection keys and saved the engine keys on July16 around07:58Z. The exact log excerpts, job dispositions and log digests are in cache_lineage_qualification.json.

A newer cache-save key therefore does not establish a new successful collection or fresh closing prices. This does NOT prove byte equality between restores and later saves, that every collector succeeded, or that the chain explains the full board mismatch. Original cache bodies remain unrecovered. The existing context archive's historical source describes selected daily fields and keep-first-per-day behavior; that description alone is not a complete input-state snapshot. A further bounded archive-source inspection was platform-blocked and was not retried through another tool.

The original security-level census and the new blocked archive-source inspection remain separate held operations. No full board control, market-outcome calculation, fit, score inversion, trade or live policy change occurred. After this publication, the next scientific requirement remains original cache/per-build input-state qualification through existing owners plus independent review; source publication cannot clear it.
