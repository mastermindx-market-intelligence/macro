# Worktree reclaim candidates — 2026-09-27

**Report only. Nothing has been deleted, sparsified, or modified.**
`config/worktree_gc.json` is untouched; the run below used a scratch copy with
`armed: false` and the two absent roots appended.

Source: `scripts/worktree_gc.py --report` over 729 on-disk registered trees, joined to the
807-tree PR-state census.

## A. Verdicted SAFE by the repo's own sweeper — 41 trees, 60.8 GiB

Unlocked, clean, unoccupied, no open PR, older than `min_age_days: 3`, and carrying one of the
three positive landed proofs. These are reclaimable the moment the two roots are in scope.

| worktree | GiB | proof |
|---|---:|---|
| `prophet-7018-baseline-repair-20260922` | 8.09 | HEAD contained in origin/sol/canada-opportunity-map-20260908; no open PR |
| `pr7633-review-repair-824f6d` | 7.29 | ancestor-of-origin/main |
| `tmp/contract-delta/contract-delta-base-tw14w7q8` | 6.25 | ancestor-of-origin/main |
| `admin-revamp-20260921` | 6.00 | PR #7602 merged at this exact head |
| `pr7633-independent-rereview-f7f1001` | 2.70 | ancestor-of-origin/main |
| `prophet-turn-watch-row-evidence-v2-sol-20260916` | 1.91 | HEAD contained in origin/claude/prophet-turn-watch-row-evidence-v2-20260916; no open PR |
| `tmp-7457-current-main-review` | 1.75 | ancestor-of-origin/main |
| `prophet-strategy-definition-v1-20260920-sol` | 1.74 | PR #7535 merged at this exact head |
| `prophet-rotation-science-20260920-sol` | 1.74 | ancestor-of-origin/main |
| `sol-7526-repair-20260920-auto` | 1.74 | ancestor-of-origin/main |
| `sol-r1b-7079-base-repro-01896` | 1.73 | ancestor-of-origin/main |
| `sol-qual-ci-curation-baseline-ebaa` | 1.64 | ancestor-of-origin/main |
| `sol-r1b-7079-release-maintenance-20260919-sol-001` | 1.60 | PR #7079 merged at this exact head |
| `us-prophet-candidate-visibility-20260921` | 1.41 | ancestor-of-origin/main |
| `research-screener-theme-stamp-20260922-sol` | 1.36 | ancestor-of-origin/main |
| `lane-f-review-a-c98d07` | 0.65 | ancestor-of-origin/main |
| `lane-f-review-a-aaa693` | 0.65 | ancestor-of-origin/main |
| `sol-mm-data-guard-hk-southbound-20260924-sparse` | 0.61 | PR #7914 merged at this exact head |
| `darkpool-data-trust-20260924` | 0.60 | HEAD contained in origin/claude/darkpool-participation-trust-20260924; no open PR |
| `prophet-four-market-recovery-sol-20260915` | 0.60 | PR #7180 merged at this exact head |
| `theme7664-mainproof-49374` | 0.59 | ancestor-of-origin/main |
| `us-sector-membership-reconcile-20260917-sol` | 0.59 | HEAD contained in origin/claude/us-sector-membership-reconcile-20260917-sol; no open PR |
| `stsi1-sector-federation-technology-dossier-20260921-sol` | 0.59 | ancestor-of-origin/main |
| `confluence-screener-rig-20260922` | 0.59 | ancestor-of-origin/main |
| `tmp/contract-delta/contract-delta-base-k550ubkj` | 0.59 | ancestor-of-origin/main |
| `pr7264-current-main-baseline-20260921-sol` | 0.58 | ancestor-of-origin/main |
| `pr7264-main-baseline-c506-sol` | 0.58 | ancestor-of-origin/main |
| `macro-touch-target-parity-20260919-r1` | 0.56 | PR #7500 merged at this exact head |
| `review/gmi-d2c-postmerge-main-365655` | 0.55 | ancestor-of-origin/main |
| `b2-base-inheritance-6ac3817e` | 0.55 | ancestor-of-origin/main |
| `sol/china-heatmap-sentinel-20260919` | 0.55 | HEAD contained in origin/sol/china-heatmap-sentinel-20260919; no open PR |
| `sol/push-retry-stale-rebase-r5-20260918` | 0.55 | ancestor-of-origin/main |
| `sol-daily-engine-precode-recovery-20260915` | 0.55 | PR #7196 merged at this exact head |
| `sol/ccr-h2-profile-search-health-provider-gate-closeout-20260914-sol-001` | 0.55 | HEAD contained in origin/sol/ccr-h2-profile-search-health-provider-gate-closeout-20260914; no op |
| `sol/ai-updates-7101-current-main-22f6759-20260915` | 0.55 | ancestor-of-origin/main |
| `sector-release-options-scope-20260924` | 0.51 | HEAD contained in origin/claude/sector-release-options-scope-20260924; no open PR |
| `risk-radar-prospective-validation-readiness-20260924` | 0.49 | PR #7894 merged at this exact head |
| `risk-radar-warning-duration-20260924` | 0.49 | ancestor-of-origin/main |
| `risk-radar-prospective-identity-20260923` | 0.48 | PR #7808 merged at this exact head |
| `us-pool-baseline-20260921` | 0.22 | ancestor-of-origin/main |
| `family-b-b0-row-repair-20260916-sol` | 0.00 | ancestor-of-origin/main |

## B. Clean + landed, but hidden behind a content-free lock stamp — 41 trees, 26.6 GiB

The SSD worktree helper stamps `mastermind-external-storage: removable volume protection` on
**every** tree it mints, and the GC treats any lock as an unconditional KEEP — so it never even
computes landedness for these. Each row below was re-checked by hand for the three things the
short-circuit skipped: dirty working tree (none), live process on the cwd (none), and a
positive landed proof (shown).

79 other locked trees carry real seat/operator text ("Active Sol China participation context;
release PR7592 untouched") and are **not** in this list.

| worktree | GiB | proof |
|---|---:|---|
| `claude/14851c4656838a3b/p0b-evidence-heal-21f8eaaf53d74217` | 3.77 | squash of this head is on origin/main |
| `claude/14851c4656838a3b/mo-ext-rev-m_rec_w5-776410577b47f395` | 0.82 | squash of this head is on origin/main |
| `claude/14851c4656838a3b/ind-t01-r6-seat-b47ff2cb69161d6c` | 0.62 | MERGED PR at this exact head |
| `claude/14851c4656838a3b/consumer-cyclical-v1-envelope-integrity-63a750ab8baaba18` | 0.62 | squash of this head is on origin/main |
| `claude/14851c4656838a3b/fable-healthcare-d1-merge-23a849218088f308` | 0.62 | squash of this head is on origin/main |
| `claude/14851c4656838a3b/mining-records-w2-99496ef1e9a8684d` | 0.62 | MERGED PR at this exact head |
| `claude/14851c4656838a3b/rob-review-17c9f82c-64154acdbd1290dd` | 0.61 | squash of this head is on origin/main |
| `claude/14851c4656838a3b/pack9-run-attempt-heal-68f0e67a31ec4548` | 0.60 | squash of this head is on origin/main |
| `claude/14851c4656838a3b/gmi-robotics-impl-17c9f82c-d191559b616f5c67` | 0.60 | zero commits ahead of base (pure cache) |
| `claude/14851c4656838a3b/robotics-main-heal-517a1eadbd313f98` | 0.60 | squash of this head is on origin/main |
| `claude/14851c4656838a3b/mo-b-recovery-handoff-20260924-0107f9553ea4546c` | 0.60 | zero commits ahead of base (pure cache) |
| `claude/14851c4656838a3b/semi-b-t05-witness-qual-af3989ddeb03b991` | 0.60 | zero commits ahead of base (pure cache) |
| `claude/14851c4656838a3b/f09-render-fragment-links-20260922-dd2043e3a1c8250e` | 0.59 | MERGED PR at this exact head |
| `claude/14851c4656838a3b/mo-ext-fix-7097-72a274c3b6903d85` | 0.56 | squash of this head is on origin/main |
| `claude/14851c4656838a3b/mo-ext-fix-7058-bb3984a8a6952933` | 0.55 | MERGED PR at this exact head |
| `claude/14851c4656838a3b/mo-ext-rev-7097-cc28251b4a4e4eb1` | 0.55 | squash of this head is on origin/main |
| `claude/14851c4656838a3b/mo-copy-plans-h4-9caa177459b75737` | 0.55 | MERGED PR at this exact head |
| `claude/14851c4656838a3b/heal-skip-only-uk-policy-1-dfc538bc020879d2` | 0.55 | squash of this head is on origin/main |
| `claude/14851c4656838a3b/mo-ext-fix-6861-bf6725b5140cb386` | 0.55 | squash of this head is on origin/main |
| `claude/14851c4656838a3b/mo-copy-start-h1-6e3267fb73e3c884` | 0.55 | MERGED PR at this exact head |
| `claude/14851c4656838a3b/mo-ext-fix-7061-e1cb463d0b5346a2` | 0.55 | MERGED PR at this exact head |
| `claude/14851c4656838a3b/mo-ext-fix-m_rec_w5-0ebfe5916057516d` | 0.55 | squash of this head is on origin/main |
| `claude/14851c4656838a3b/mo-heal-macro-w9-457d24e16b6d52ac` | 0.55 | MERGED PR at this exact head |
| `claude/14851c4656838a3b/f01-t10-2-cb93fc92f88ee6b6` | 0.55 | squash of this head is on origin/main |
| `claude/14851c4656838a3b/heal-ci-pack-ceiling-1-51059714073fc10b` | 0.55 | squash of this head is on origin/main |
| `claude/14851c4656838a3b/mo-heal-cmdty-w6-7c04aacc50e69b57` | 0.55 | MERGED PR at this exact head |
| `claude/14851c4656838a3b/heal-labels-2-ac7d082848747e98` | 0.55 | squash of this head is on origin/main |
| `claude/14851c4656838a3b/mo-copy-hk-h2-4081dab504fad3fb` | 0.55 | MERGED PR at this exact head |
| `claude/14851c4656838a3b/mo-heal-fxtrans-engine-fb5452c7777ae1b1` | 0.54 | MERGED PR at this exact head |
| `claude/14851c4656838a3b/mo-build-bonds-s3-cd5364030dddd86b` | 0.54 | MERGED PR at this exact head |
| `claude/14851c4656838a3b/f01-t10-1-47ad20e1f0f15107` | 0.54 | squash of this head is on origin/main |
| `claude/14851c4656838a3b/mo-ext-rev-6861-db085b0c15083638` | 0.54 | squash of this head is on origin/main |
| `claude/14851c4656838a3b/mo-ext-rev-m_f08_b5_3_macro-593ac76b7d0b6c5d` | 0.54 | squash of this head is on origin/main |
| `claude/14851c4656838a3b/mo-build-confluence-h3-317ef1bfe30a18da` | 0.54 | MERGED PR at this exact head |
| `claude/14851c4656838a3b/mo-copy-landing-zh-h5-1de14d9e45d8e5a6` | 0.54 | squash of this head is on origin/main |
| `claude/14851c4656838a3b/mo-ext-fix-6905-67bfe9fa85f762ce` | 0.54 | squash of this head is on origin/main |
| `claude/14851c4656838a3b/mo-ext-rev-6905-60d6bd5af10ffbea` | 0.54 | squash of this head is on origin/main |
| `claude/14851c4656838a3b/mo-ext-fix-t_f09_b5_1-7ec371637de369a9` | 0.54 | squash of this head is on origin/main |
| `claude/14851c4656838a3b/mo-ext-rev-t_f09_b5_1-d70594d93a26982e` | 0.54 | squash of this head is on origin/main |
| `claude/14851c4656838a3b/wave4-record-9318482e0c4a3192` | 0.54 | squash of this head is on origin/main |
| `claude/14851c4656838a3b/mo-ext-fix-m_f08_b5_3_macro-705488cb1b609c2b` | 0.54 | squash of this head is on origin/main |

## Totals

| pool | trees | GiB |
|---|---:|---:|
| A — verdicted SAFE under widened roots | 41 | 60.8 |
| B — clean+landed behind the lock stamp | 41 | 26.6 |
| **combined** | **82** | **87.3** |
| ORPHAN (separate `include_orphans` ratification) | 8 | 4.9 |

For contrast, the armed sweeper at its shipped scope freed **1.5 GiB** of a 308 GiB population.

## What this run KEPT, and why it is right to

| verdict | trees | GiB | why it is unreachable by a completion signal |
|---|---:|---:|---|
| DIRTY | 107 | 221.3 | uncommitted or untracked work on disk |
| RECENT | 66 | 122.4 | younger than `min_age_days: 3` |
| UNPUSHED | 100 | 86.7 | commits exist nowhere but that checkout |
| OPEN_PR | 19 | 33.1 | in flight |
| LIVE_PROC | 7 | 27.6 | a named pid holds the cwd |
| LOCKED (real operator text) | 79 | 83.6 | someone chose to park it |

Detached-HEAD trees satisfy none of the three landed proofs and are permanently KEEP until a
lane-exit receipt exists — 318 trees, 150 of them `mo-ext-*` labour lanes whose output ships
from the orchestrator seat's carrier branch, so they are *supposed* never to land.
