# Feed bridge: current writer and publication-seam census

**Decision: ready for a bounded source apply in the existing sovereign-auction workspace, with exact preimage checks.** This receipt does not authorize merging, deployment, scheduler activation, or changes in other owners' workspaces. Root remains the sole source writer for [Macro PR #8657](https://github.com/mastermindx-market-intelligence/macro/pull/8657).

The proposed change is a single exception for `site/feeds/event_calendar.json` in the existing ignore rule, plus moving the **one existing** `scripts.build_feeds` step immediately before the final `commit engine outputs` step. Existing producer ownership, the commit helper, the R2 publisher, and serving hydration retain their responsibilities. Seeded official receipts remain attended captures with their original clocks.

## Decision evidence and source drift

The open-PR collection contains **588 unique open PRs**. Local Git object comparisons classified 574 against their exact collection base/head SHAs; the 14 local object gaps were resolved with GitHub changed-file lists. All 588 have a scoped path classification. There are **13 overlaps** with the six publication-related paths, and **zero observed PR changes to `.gitignore` or `scripts/build_feeds.py`** at the captured states. No reviewed overlapping patch proposes the feed-build move or calendar Git exception.

The live filesystem scan completed at **2026-10-08T23:37:36.385961Z**: **745 registered worktrees; 716 scope-clean, 15 scope-dirty, 14 missing registered paths**. All **31 canonical managed locks** were clean for the two requested paths. The root workspace was clean at `d9325a8dc984ef902c3a1a72446884db7676702d`, under its existing lock:

```
mastermind-linked-worktree:v1 operation=sovereign-auction-pressure-20261008-sol-001 lane=web base=d2eec4732abee359ebb578b245fa7359b3c01a7d
```

Clean scoped status does not prove that an owner is idle. No lease was acquired, reassigned, released, or overridden. Missing paths remain missing; they were not cleared or repaired.

Macro main had advanced from the task's `8a35d8b...` to **`c44aae5f131a59571ad0afcd7197e3d8696bc2b9`**. Its daily workflow changed only in the regional Theme Graph witness block, away from the final feed/commit seam. Preserve that block during eventual integration. A final **local remote-tracking-ref** read at **2026-10-08T23:39:54.795496Z** saw **`b86c4ada64533320232a98278cf199978a369a92`**. Comparing c44 to b86 found **no changes** in `.gitignore`, daily.yml, build_feeds.py, the engine commit helper, or publish_r2.py. This final b86 observation is local object evidence, not a new GitHub API freshness assertion.

The c44 daily SHA-256 is `c7cb98bbed9242fe8b43dbedc1ca5c258513f352903fe672579d2ee38f569653`. Root's d2eec daily preimage is `1317cff29e8bf46e3b1346602bc42c2a50eaf92009082027cf52ed43a030c05b`. Applying to the owned d2eec-derived branch is appropriate; eventual integration must retain intervening main changes.

## Complete scoped open-PR overlaps

This is a path and relevant-hunk review, not blanket clearance of these PRs. **#7060 stays Draft/HOLD**. None was changed by this audit.

| PR | Captured exact head | Overlapping paths | Semantic finding |
|---|---|---|---|
| [#8008](https://github.com/mastermindx-market-intelligence/macro/pull/8008) · Draft | `d10f828c6fa7291a971ee5dab1bc0271b3e1c10d` | `.github/workflows/daily.yml` | Collect-job cap and cancellation/market-data push timing; no final feed-build or calendar transport hunk. |
| [#7871](https://github.com/mastermindx-market-intelligence/macro/pull/7871) · Draft | `df96a1e3a79d976c987470c12b0d15ccf579c5ef` | `.github/workflows/daily.yml` | Adds Cycle full-vintage collector before release radar; distinct data producer. |
| [#7596](https://github.com/mastermindx-market-intelligence/macro/pull/7596) | `50bc529e03d2ff46c69cd7c72e59bf441634d1d5` | `scripts/ci/daily_engine_commit_outputs.sh` | Gold post-rebase audit/receipt and staging repair in existing commit helper; no feed path. Preserve final-tree receipt semantics. |
| [#7559](https://github.com/mastermindx-market-intelligence/macro/pull/7559) | `9f9c1e869742c73a5e06c1881417258a11938719` | `.github/workflows/daily.yml` | Alert transport labeling and Discord/Telegram availability; unrelated execution steps. |
| [#7292](https://github.com/mastermindx-market-intelligence/macro/pull/7292) | `909dc5a058f0be752c49a4defc3a92438818edd8` | `.github/workflows/daily.yml` | Marketing persona publication-memory reconciliation; other job/band. |
| [#7246](https://github.com/mastermindx-market-intelligence/macro/pull/7246) · Draft | `acb2fb10c1cd2e3ac9157271e6abc845bc70048a` | `.github/workflows/daily.yml` | AgentOS nightly materializes Mastermind P0 input in RUNNER_TEMP; different tail producer, no feed seam. |
| [#7197](https://github.com/mastermindx-market-intelligence/macro/pull/7197) · Draft | `8cb51ef4e306be8e1839a01bedde8fe241061fda` | `.github/workflows/daily.yml` | Pressure-watch source hydration/freshness and price_pressure R2 publication; separate directory and gate. |
| [#7178](https://github.com/mastermindx-market-intelligence/macro/pull/7178) | `ec3190b33e0a3d5cc8a83797631f641274cdd974` | `.github/workflows/daily.yml` | Regional desk builder timeout before publication barrier; no assembler move. Keep upstream budget changes independent. |
| [#7084](https://github.com/mastermindx-market-intelligence/macro/pull/7084) | `4fab84d2bdad0a56b063f6da98a2c41585456ecd` | `.github/workflows/daily.yml` | USGS/critical-mineral ingest and recurring briefs; distinct producers. |
| [#7060](https://github.com/mastermindx-market-intelligence/macro/pull/7060) · Draft | `170ad35b12673eac75ebefb53b3a5da4640daf06` | `.github/workflows/closing-bell.yml`, `.github/workflows/daily.yml`, `scripts/ci/daily_engine_commit_outputs.sh`, `scripts/publish_r2.py` | Draft/HOLD sector participation bundle with earlier core checkpoint and other data/cache options changes; no build_feeds or final calendar Git exception. publish_r2 changes add options_skew/options_payoff_lab data directory rules, not feeds manifest timing. |
| [#7001](https://github.com/mastermindx-market-intelligence/macro/pull/7001) | `3684c7d51a0b5d894314c369b408896f54df2ffd` | `.github/workflows/daily.yml` | Adds early international dashboard checkpoint and timeout on final engine commit; move must preserve helper step configuration on integration. |
| [#6861](https://github.com/mastermindx-market-intelligence/macro/pull/6861) | `6f3b75657f342949b9e0e04b837565cdb71a38a2` | `.github/workflows/daily.yml` | Adds capability-health projection before commit-publish timing mark; preserve relative upstream execution, no competing assembler or feed exception. |
| [#6842](https://github.com/mastermindx-market-intelligence/macro/pull/6842) · Draft | `70815229c55963598d4441eef07ca3949d097b3b` | `.github/workflows/closing-bell.yml` | Closing-bell acquisition landing truth projection hooks; no daily bridge edit. |

The most relevant adjacent owners are #7596's **post-rebase Gold receipt**, #7001's **international publication checkpoint/timeout**, and #6861's **capability-health producer before the commit timing mark**. The source bridge should preserve these semantics when they are integrated. They do not require transplanting or editing those owners' code in this task.

#7060's broad overlap includes an earlier core checkpoint, US breadth cache authority, options-skew/payoff-lab directory rules, and unrelated producers. Its R2 diff does not change the `feeds` namespace or the manifest-last rule. Its daily patch does not move `build_feeds`, and its engine helper change does not add a competing calendar owner.

## Live dirty workspaces

Of the 15 dirty rows, **six contain whole-file deletions** in the scoped paths. These are preserved historical/incomplete-worktree states, not evidence for a new feed edit. The **nine remaining rows** have modified daily content; four contain the older **early core checkpoint** addition, while the other changes concern GMI, OIP, CPU shadow, or breadth cache authority. No reviewed working-tree patch changes the final feed build, `feeds/`, or calendar transport.

| Registered worktree | Observed HEAD | Scoped status | Relevant interpretation |
|---|---|---|---|
| `/Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/admin-uiux-sweep-20260918` | `b79a6e08ffb82a35ae4d7d28ad49979f3296b470` |  D .github/workflows/daily.yml | whole-file deletion; no hunk-level active bridge evidence. |
| `/Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/catalyst-r19-ci-20260927` | `17a94057c51c28583150b20f2b4f6cdc0436c546` | D  .github/workflows/daily.yml; D  .gitignore | whole-file deletion; no hunk-level active bridge evidence. |
| `/Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/risk-radar-displayed-probability-audit-20260922` | `25cecb06160a1766c537e218a8979c91e7bc3064` | D  .github/workflows/daily.yml; D  .gitignore | whole-file deletion; no hunk-level active bridge evidence. |
| `/Users/chriswong/Documents/Cluade/macro-worktrees/sol-macro-suite-registry-order-20260916` | `c1b018c179e2f66395acedda4aa5d9852aa7d04e` | M  .github/workflows/daily.yml | Older early core checkpoint addition; no final feed seam hunk. |
| `/Volumes/Mastermind/agent-workspaces/claude/14851c4656838a3b/customer-alert-delivery-20260922-6cd4e96c6eb00cfd` | `65a525df22c6107b24b321c1786246c42b7b22bb` |  M .github/workflows/daily.yml | Older early core checkpoint addition; no final feed seam hunk. |
| `/Volumes/Mastermind/agent-workspaces/claude/14851c4656838a3b/orch-b-gate8-7978e5304c569149` | `f83c60a1e64010a6c3524f33af4b2e93d7ef29a0` |  M .github/workflows/daily.yml | GMI graph shadow producer. |
| `/Volumes/Mastermind/agent-workspaces/claude/14851c4656838a3b/us-risk-breadth-integrity-20260916-sol-9a09b2c2fa2f1eb8` | `124781fcaf4e6010d0ec3cc95be1c438751beaf7` | M  .github/workflows/daily.yml | Older early core checkpoint addition; no final feed seam hunk. |
| `/Volumes/Mastermind/agent-workspaces/sol/push-retry-stale-rebase-20260917-sol` | `a45871683d2f13577c690b6ec8877dd9f57bad7a` |  D .github/workflows/daily.yml | whole-file deletion; no hunk-level active bridge evidence. |
| `/Volumes/Mastermind/tmp/prophet-packet3-r24-current-main-integration` | `a242e144205add650eed032da49e28aa56d6b325` |  D .github/workflows/daily.yml | whole-file deletion; no hunk-level active bridge evidence. |
| `/Volumes/Mastermind/worktrees/pr7264-ci-selfheal-r3-20260922-sol` | `9335a1bbab7968ba99d401c56809a687b02d26f0` | D  .github/workflows/daily.yml; D  .gitignore | whole-file deletion; no hunk-level active bridge evidence. |
| `/Volumes/Mastermind/worktrees/sol-mobile-settings-row-20260921` | `8bb010a76d187eae1d0c57a62a5392c4cf8e5079` | M  .github/workflows/daily.yml | OIP catalyst context producer. |
| `/Volumes/Mastermind/worktrees/sol-pr7505-canonical-20260921` | `81f6a7f76afdc757dc84997f486f4739ce50ae6b` | M  .github/workflows/daily.yml | Breadth cache authority repair. |
| `/Volumes/Mastermind/worktrees/sol-prophet-cpu-diagnosis-20260920` | `310a23dcd3e5fb8fdb95169a489b94487b091777` |  M .github/workflows/daily.yml | Prophet CPU shadow producer. |
| `/Volumes/Mastermind/worktrees/sol-start-mobile-controls-20260921` | `90b0d721d78eda8f9205275f3c6bb7a478fdcbeb` |  M .github/workflows/daily.yml | Older early core checkpoint addition; no final feed seam hunk. |
| `/Volumes/Mastermind/worktrees/tmp-7526-semantic-review` | `96ed7e880dfe4e54bbb693dfea5267cdb6e63629` | M  .github/workflows/daily.yml | Breadth cache authority repair. |

Git porcelain status reports index/worktree changes relative to HEAD. It does not distinguish an active human, a sleeping agent, or preserved unfinished work. Full branches, locks, all 31 managed registrations, and SHA-256 hashes of the nine modified daily diffs are in the JSON receipt. This audit did not write to these workspaces.

## Build side effects and the final commit boundary

At the pinned source, `build_feeds.build()` copies or writes its outputs under `site/feeds/`, reads already-produced data, invokes legacy event-calendar functions, and computes international radar snapshots through store readers. The latter call path has no explicit data writer in the inspected snapshot implementation.

The legacy calendar **can perform network reads and write caches** on cache misses. This is existing behavior, not a new sovereign collector:

- FRED release dates use `data/macro/release_cache/rel_<id>_<date>.json` with a 12-hour cache and bounded request timeout.
- TreasuryDirect upcoming auctions use `data/macro/auction_cache/upcoming_<date>.json` with a 12-hour cache and bounded request timeout.
- Both directories are explicitly ignored in the unchanged `.gitignore`, lines 172–173 of the captured source. Moving the assembler before broad staging does not make these caches new tracked output.
- The sovereign snapshot reads qualified persisted observations separately. Legacy cache reads must not be relabeled as qualified sovereign source observations.

Changing the directory ignore from `site/feeds/` to `site/feeds/*`, followed by `!site/feeds/event_calendar.json`, makes only the calendar eligible for normal Git staging. Existing `git add data/ site/ reports/` in `daily_engine_commit_outputs.sh` can then stage it. Other feed artifacts and `feeds_meta.json` remain ignored and continue through the existing R2 mechanism. The helper does not need a new writer or an extra forced-add path.

The move places the assembler's existing runtime on the critical path before the final commit. It does not add an invocation. Preserve its existing `if: always()` and nonfatal behavior, and preserve the final commit step's own configuration. No new full-job runtime/reachability guarantee was established by this source audit. A real build result from root belongs in root's execution receipt, not in this source-only census.

## R2 manifest timing and byte identity

Before the change, the final daily order was:

1. Commit engine outputs.
2. Assemble machine-consumable feeds.
3. Publish heavy stores, including `feeds`, to R2.

The proposed order is:

1. Assemble the same feed artifacts once.
2. Commit engine outputs, including the newly tracked calendar.
3. Invoke the unchanged R2 publisher.

In `publish_r2.py`, local feed files are enumerated from `site/feeds`; changed files upload first; the publisher writes `feeds/_manifest.json` **last**, and withholds that manifest after upload failure, append-only refusal, or a partial-tree guard. No manifest is created by the assembler itself. Its separate `feeds_meta.json:generated_utc` remains a build clock. Moving the build does not move the R2 manifest ahead of file upload or turn a manifest timestamp into a source publication timestamp.

There is a material limit to any “same bytes” claim: the existing engine commit helper may fetch, rebase, apply autostash, and heal conflicts before publication. Those operations can alter the final checkout. Its normalizers target rendered pages, but the Git conflict/healing machinery covers `site/`. The narrow source bridge establishes a **single produced calendar path and existing transport ownership**; it does not prove an atomic cross-feed snapshot or a post-rebase hash invariant for every future run. The actual publication receipt should bind the final committed calendar hash, served calendar hash, and Mastermind consumed hash when deployment/runtime verification becomes authorized. Do not create a direct public-R2 fallback in Terminal to close this evidence gap.

Existing closing-bell source already assembles feeds before its site staging, so no second order change is required there.

## Attended acquisition is an honest first vertical

Keeping the sovereign collector attended-only is useful and consistent with this bridge. Four existing official captures can seed `data/treasury_auctions/observations`; the full calendar build then proves schema, calendar wrapper, deterministic event treatment, parser compatibility, and the owned Git/serving route.

Rebuilding daily **reprojects the captured bytes** into the current query window. It cannot advance `source_observed_at`, certify “current” source freshness, infer release time from a date-only field, or create prospective S-1 eligibility. Source health should continue to say freshness is unassessed where no cadence/SLA is established. Collector activation, archive/retention ownership, the 128-receipt read bound, late-correction capture, and refresh policy remain explicit incomplete operations work. No additional scheduler or autonomous capture lane was activated.

This decision does not reverse the prior predictive null studies or promote funding pressure to risk-decision authority. The first vertical remains deterministic event context with independent predictive validation withheld until qualified point-in-time data and its preregistered gates exist.

## Coverage and quota limits

The convenience PR search returned only 60 records even when requested with a higher cap. It was not used as completeness evidence. The REST collection used nine requested pages: pages 1–5 had 100 PRs each, page 6 had 88, and pages 7–9 were empty. The 588-PR metadata inventory is saved separately.

To preserve the shared GitHub operating quota, the audit used local no-lazy-fetch Git object comparison for 574 PRs. Fourteen connector file lists covered the missing local merge bases; one additional filename validation and one patch read resolved PR #7246's bounded local blob-read timeout. A read of the generic rate-limit URL was rejected by the connector's endpoint allowlist, so **remaining shared quota was not observed**. Tool operation counts are not a proven count of underlying REST requests. No credentials were acquired and no further quota-consuming freshness loop was run.

The 574 local comparisons bind to exact collection SHAs. The 14 connector pathsets were not bracketed by an additional head re-read, so their file classifications are observed connector states associated with collection metadata, not an atomic exact-head assertion. New PRs and later head updates are outside this receipt. Root's subsequent bridge edits to #8657 are expected to change its own scoped path status.

The narrow path census also does not inspect every indirect owner, such as all changes to `.github/ci/legacy-jobs.yml`. It supplies decision evidence for the two explicitly requested files and four adjacent publication paths; it is not global merge clearance.

The standard `mmx-workspace census` was tried read-only but its full untracked-file scan across hundreds of worktrees exceeded the useful bound. Only that audit-owned process was stopped. The replacement enumerated the same Git worktree registrations and ran path-limited `git status --porcelain=v1 --untracked-files=no`, with optional locks and lazy fetch disabled. This preserved every registered workspace and made the coverage limits explicit.

## Source hashes and reproducible record

All hashes below identify bytes read at c44. The last scoped main-drift comparison found the five bridge-path blobs unchanged at b86.

| Source | Git blob | SHA-256 |
|---|---|---|
| [.gitignore](https://github.com/mastermindx-market-intelligence/macro/blob/c44aae5f131a59571ad0afcd7197e3d8696bc2b9/.gitignore) | `b1272ff5216d8f08bfccbf2904c8ad65bafaf825` | `8002e865c795a8c5ac529f0a9c8812a6c5abd4d69e8dc5ea56c682c5054a0c53` |
| [.github/workflows/daily.yml](https://github.com/mastermindx-market-intelligence/macro/blob/c44aae5f131a59571ad0afcd7197e3d8696bc2b9/.github/workflows/daily.yml) | `26731b7c6bf05a18f818e16e8139c51418d0f0ce` | `c7cb98bbed9242fe8b43dbedc1ca5c258513f352903fe672579d2ee38f569653` |
| [scripts/build_feeds.py](https://github.com/mastermindx-market-intelligence/macro/blob/c44aae5f131a59571ad0afcd7197e3d8696bc2b9/scripts/build_feeds.py) | `f5d086666914849fe76549f30c3e50145b316851` | `ba462cfb841e896185b586494be4220ca3f8c8b8188cc682ea32f23cf15ccafd` |
| [scripts/ci/daily_engine_commit_outputs.sh](https://github.com/mastermindx-market-intelligence/macro/blob/c44aae5f131a59571ad0afcd7197e3d8696bc2b9/scripts/ci/daily_engine_commit_outputs.sh) | `52cef03e9eddbeb359d990b440259a1e711e7c31` | `3f873da28b53ee8dcc20ef44615889488a7e318a4d6cdffb9be02628c5c26907` |
| [scripts/publish_r2.py](https://github.com/mastermindx-market-intelligence/macro/blob/c44aae5f131a59571ad0afcd7197e3d8696bc2b9/scripts/publish_r2.py) | `240b762a661db6fe1cb087049469acf1cfa9a5f4` | `d6446e1d3d66e5db51b19dde9e2c987a1f5f5d779c06a6c0e1400dbb8b1eaae0` |
| [engine/event_calendar.py](https://github.com/mastermindx-market-intelligence/macro/blob/c44aae5f131a59571ad0afcd7197e3d8696bc2b9/engine/event_calendar.py) | `ef9ebd3c380da1d81411dd62fc4b2885b231fafe` | `522f642131c7adcf6d8b2fce66df9e812d40e9d8fa556360a603049fa908788b` |
| [engine/risk_radar_intl.py](https://github.com/mastermindx-market-intelligence/macro/blob/c44aae5f131a59571ad0afcd7197e3d8696bc2b9/engine/risk_radar_intl.py) | `4ed9bdebf6e76cbf529115203ae5d8820ba07f13` | `1596e1da4794bf97d49f6f0ae42eaabff7226fa812fb0a96bfb0a6242faf7cd7` |

The machine-readable receipt contains the captured source clock, local-main drift check, all 588 classifications, all 13 reviewed overlap records, bounded patch excerpts, and live workspace evidence. The separate open-PR inventory supplies exact heads, bases, titles, draft flags, update times, and owner handles.

Reproduction is read-only: collect open PR metadata with bounded pagination; compare each available exact head to its merge base without rename similarity/blob reads; inspect only overlapping patches; enumerate Git worktree registrations; run scoped status for the two paths; hash the pinned source files. Re-running later creates a new census timestamp and must not overwrite this receipt's captured state.

