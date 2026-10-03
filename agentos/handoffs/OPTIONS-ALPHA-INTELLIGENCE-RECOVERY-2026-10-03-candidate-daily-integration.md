---
workstream: "WS:OPTIONS-ALPHA-INTELLIGENCE-RECOVERY"
session: mo-ext-fix-options-product-20261003-candidate-daily-integration
model: codex
ended_because: complete
mission: >-
  Keep the existing draft PR #8358 (branch codex/options-alpha-candidate-daily-20261003,
  base claude/mo-ext-fix-8342) as the sole carrier of the candidate daily integration.
  Merge current parent #8350 and refuse admitted outcome facts dated after
  feed.generated_at. Do not open, close, retarget, or activate anything.
state_before: >-
  Draft PR #8358 already exists on codex/options-alpha-candidate-daily-20261003.
  Its pre-repair head was 9837f2df94a8cc23a598edd6cd8a7f2ab8e00863. The historical
  source parent of that stack was 1abc243b94295e867d12fd166bbd2a42948e76f1. Parent
  campaign PR #8350 is open on claude/mo-ext-fix-8342 at 9999b5c9518ec0ac6829245b16aa374957de004e.
  Closed PR #8356 and closed duplicate #8357 are not carriers. No second composer,
  publisher, ledger, score path, score plane, promotion path, or Issue Desk exists.
  scripts/publish_options_alpha_candidate_r2.py remains the only writer of
  options_alpha/candidate_feed.json and options_alpha/candidate_feed.receipt.json.
changed:
  - path: scripts/build_options_alpha_candidate_feed.py
    what: "Inactive-safe CLI composer: preconditioned activation receipt, fail-closed bucket/client gate, pending-recovery activation-binding check, post-formation outcome enrichment join keyed by the frozen first qualifying revision."
  - path: scripts/publish_options_alpha_candidate_r2.py
    what: "recover_pending_pair() binds a pending payload to the current activation before replay and does not recompose."
  - path: engine/options_alpha_candidate_outcome_enrichment.py
    what: "Six-horizon enrichment of admitted effective-view rows only. Recorded facts campaign_available_at, computed_at, and matured_at must not be later than the already validated feed.generated_at. target_time stays a scheduled horizon and may be in the future. CandidateOutcomeEnrichmentError is raised before any such row is published."
  - path: contracts/options/options.alpha_candidate_feed.v2.schema.json
    what: "Strict additive v2 schema for post-formation outcomes and the campaign_context block."
  - path: tests/test_build_options_alpha_candidate_feed.py
    what: "Dedicated build-feed cases. The active composer/enricher/publisher case now publishes at 2026-10-16T15:00:00Z so its October 15 outcome facts are not future relative to feed.generated_at. The August event session is unchanged."
  - path: tests/test_publish_options_alpha_candidate_r2.py
    what: "Publisher suite covers recover_pending_pair, including activation binding."
  - path: tests/test_options_alpha_candidate_outcome_enrichment.py
    what: "Enrichment cases plus three negative cases that set campaign_available_at, computed_at, or matured_at to 2999 and expect CandidateOutcomeEnrichmentError. The fixture observation clock is 2026-10-16T15:00:00Z, after the existing 2026-10-15 facts."
  - path: tests/test_options_signal_episode.py
    what: "Candidate step sits between the campaign checkpoint and XSR. It gates on the four prior successes, uses the publication lock outside the checkout, and the terminal integrity test requires OIP_CANDIDATE_BUILD_OUTCOME."
  - path: scripts/ci/options_signal_nightly.sh
    what: "assert-integrity() requires OIP_CANDIDATE_BUILD_OUTCOME in addition to the four prior outcomes."
  - path: .github/workflows/daily.yml
    what: "options_alpha_candidate_feed step is gated on the four prior successes, times out in 5 minutes, continues on error, and runs the candidate builder with the publication lock. OIP_CANDIDATE_BUILD_OUTCOME is passed into assert-integrity."
  - path: .github/ci/legacy-jobs.yml
    what: "options-alpha-candidate-feed exclusive paths cover the composer and enrichment closure. The dedicated pytest command includes the build and enrichment suites."
  - path: agentos/handoffs/OPTIONS-ALPHA-INTELLIGENCE-RECOVERY-2026-10-03-candidate-daily-integration.md
    what: "This record. Carrier is existing draft PR #8358. No new WS/DEC/DSC."
prs: [8358]
verified:
  - claim: "Availability-guard patch matches the ruled bytes and applies on the post-merge tree."
    command: "shasum -a 256 /private/tmp/options-candidate-outcome-availability-guard-v2.patch; git apply --check /private/tmp/options-candidate-outcome-availability-guard-v2.patch"
    result: "4754 bytes, SHA-256 5e47f5d27f69eb0db0824da3e43defece645455f1c0712922c5e0bafab4539b0; apply --check exit 0. The patch touches only the enrichment module and its test."
  - claim: "On the pre-guard head the three negative cases publish future recorded facts."
    command: "PYTHONPATH=tests:scripts python3 -m pytest tests/test_options_alpha_candidate_outcome_enrichment.py::test_future_recorded_outcome_clock_refuses_before_exposure -q --tb=line"
    result: "3 failed in 2.00s. Each case failed with 'DID NOT RAISE CandidateOutcomeEnrichmentError' for campaign_available_at, computed_at, and matured_at."
  - claim: "The four dedicated candidate suites pass after the guard."
    command: "PYTHONPATH=tests:scripts python3 -m pytest tests/test_options_alpha_candidate_feed.py tests/test_publish_options_alpha_candidate_r2.py tests/test_build_options_alpha_candidate_feed.py tests/test_options_alpha_candidate_outcome_enrichment.py -q"
    result: "114 passed in 16.48s."
  - claim: "The workflow helper slice touched by this PR passes."
    command: "PYTHONPATH=tests:scripts python3 -m pytest tests/test_options_signal_episode.py -k \"daily_options_pit_checkpoint or terminal_integrity or broad_cleanup_removes\" -q"
    result: "8 passed, 258 deselected in 2.31s."
  - claim: "Merging origin/claude/mo-ext-fix-8342 at 9999b5c9518e preserved every pre-merge PR path."
    command: "git diff --stat 1abc243b94295e867d12fd166bbd2a42948e76f1 9837f2df94a8cc23a598edd6cd8a7f2ab8e00863; git diff --stat origin/claude/mo-ext-fix-8342...7744db4435697df48800309546bb10c2bcc49948"
    result: "Before the merge the PR differed from merge-base 1abc243b9429 by 12 files, 2084 insertions and 23 deletions. After the merge the same 12 files showed the same 2084 insertions and 23 deletions against origin/claude/mo-ext-fix-8342. No file was dropped."
  - claim: "A missing or uncleared activation receipt stays inactive before R2, journal, or clock use."
    command: "sed -n '213,245p' scripts/build_options_alpha_candidate_feed.py"
    result: "Lines 214-220 return inactive activation_receipt_absent. Lines 227-232 return inactive activation_preconditions_uncleared. Lines 242-245 fail closed when client or bucket is missing."
unverified:
  - claim: "Parent PR #8350 hosted CI is green and the PR is merged."
    what_would_verify: "Root-owned review and merge of #8350. This draft stays based on claude/mo-ext-fix-8342 until root retargets it."
  - claim: "Natural RTH publication of the candidate feed or of the live-flow cutover."
    what_would_verify: "A later natural RTH readback. The M1 live-flow install below is outside RTH and is not publication proof."
  - claim: "Candidate activation and the four candidate plus six correction preconditions are cleared."
    what_would_verify: "An operator receipt. They are not auto-cleared. No R2 pair was published by this repair."
  - claim: "AD1 org-admin runner group 5 can run the required workflows."
    what_would_verify: "Removal of the workflow restriction. Canary is the only accepted path today, and AD1_M1_LANE is absent."
  - claim: "Terminal PR #788 is deployed."
    what_would_verify: "Remaining required CI and deploy. Source head 38a2a15a7ba90f8ce621d0c5b00742af186129e8 is Ready and source-approved only."
  - claim: "Prior contract-delta and CI trigger-closure numbers still hold."
    what_would_verify: "A fresh run only if a later change adds a dependency. This repair adds datetime from the standard library and does not change the CI catalog. The earlier 111-test, zero contract-delta, and zero pack-closure qualifications were not repeated."
decisions: []
discoveries: []
unresolved:
  - "Parent PR #8350 (head 9999b5c9518ec0ac6829245b16aa374957de004e) is still open. Root merges it and then retargets #8358 to main. This lane must not retarget, mark Ready, or merge."
  - "Candidate activation is absent and the builder stays inactive. Four candidate preconditions and six correction preconditions are not cleared. No candidate R2 pair was published."
  - "AD1 org-admin runner group 5 workflow restriction is still blocked. Canary is the only accepted path. AD1_M1_LANE is absent."
  - "Live-flow M1 cutover is installed and was clean outside RTH. Natural RTH publication is not proven."
  - "Terminal PR #788 head 38a2a15a7ba90f8ce621d0c5b00742af186129e8 is Ready and source-approved. Required CI and deploy are still owed."
  - "The journal path $HOME/.local/state/mastermind/options-alpha-candidate/publication.lock is not yet bound to a proven single publication principal."
next_actions:
  - "Root reviews the exact head of existing draft PR #8358. Do not open a new PR, do not mark Ready, do not arm merge-on-green, and do not wait on CI in this lane."
  - "Root merges PR #8350, then retargets #8358 to main and runs the hosted CI pack plus the scoped live check."
  - "Activation still requires a real receipt, M2 runner continuity at the publication lock, and a natural publication readback. This draft does not clear those gates."
do_not_redo:
  - "Do not close, reopen, migrate, or replace PR #8358 or branch codex/options-alpha-candidate-daily-20261003. Closed #8356 and closed duplicate #8357 are not carriers."
  - "Do not rebuild or fork scripts/publish_options_alpha_candidate_r2.py. It is the only candidate-feed R2 writer."
  - "Do not add a second composer, daily caller, ledger, score plane, score path, promotion path, collector, or Issue Desk."
  - "Do not guard target_time. It is a scheduled horizon and may be in the future. Do guard campaign_available_at, computed_at, and matured_at against feed.generated_at."
  - "Do not synthesize ChainHeat as measured NBBO."
  - "Do not re-hunt Sep-17 or Sep-18 RTH evidence. The measured source and Flow consumer are already evidenced."
  - "Do not reopen the OA-0 architecture freeze. Preserve the Sep-03 bad-campaign-outcome incident and the corrected-but-unmerged correction prereg."
  - "Do not promote OA-1C-MACRO or OA-1T-MACRO to PROVEN_LIVE from this draft. Durable publication, integrity, and scoring.enabled=false stay the acceptance gates."
  - "Do not mint a new WS, DEC, or DSC for this draft. Canonical episode and campaign owners stay."
  - "Do not claim a natural RTH publication from the outside-RTH live-flow install."
danger_areas:
  - "PR #8358 is stacked on open PR #8350. Until #8350 merges, origin/main does not contain this parent. Do not treat a local HEAD as main."
  - "The historical source parent 1abc243b94295e867d12fd166bbd2a42948e76f1 is history only. The current parent head is 9999b5c9518ec0ac6829245b16aa374957de004e."
  - "The builder validates activation before journal recovery. The journal helper may read pending transaction bytes and must not recompose the feed."
  - "Enrichment reseals feed_id from canonical bytes that include the mutable outcome block. A changed outcome view must not reuse a prior feed_id."
  - "Enrichment fail-closes when an admitted row's campaign_available_at, computed_at, or matured_at is later than feed.generated_at. A fixture that records October 15 facts must use an observation clock after those facts."
  - "Sparse checkout: missing data/options_signal_episode/checkpoint.json fails unrelated episode tests. The 114-test command and the 8-test helper slice do not need that data."
  - "The macstudio label is not proof of single-host journal custody."
---

## State now

Draft PR #8358 on `codex/options-alpha-candidate-daily-20261003` is the carrier. It is already open. It is not ready for a new PR, Ready, or merge. Closed #8356 and closed duplicate #8357 are not carriers.

Parent PR #8350 is open at `9999b5c9518ec0ac6829245b16aa374957de004e` on `claude/mo-ext-fix-8342`. That head is merged into this branch. The older source parent `1abc243b94295e867d12fd166bbd2a42948e76f1` is history only. The pre-repair head of #8358 was `9837f2df94a8cc23a598edd6cd8a7f2ab8e00863`.

Admitted outcome rows now fail closed when `campaign_available_at`, `computed_at`, or `matured_at` is later than the validated `feed.generated_at`. `target_time` is not guarded. The guard patch is 4754 bytes, SHA-256 `5e47f5d27f69eb0db0824da3e43defece645455f1c0712922c5e0bafab4539b0`. Before the guard, the three negative cases did not raise. After it, the four candidate suites passed 114 tests and the touched workflow helper passed 8 tests.

Candidate activation is absent. The builder stays inactive. The four candidate preconditions and six correction preconditions are not cleared. No candidate R2 pair was published. No journal or runtime effect was made by this repair.

## Runtime facts recorded for this handoff

These facts are root-verified and are not publication proof.

- FS5 #8313 is merged at `603fcc5065accb61a299696c715121a94f77b960`.
- OA3 #8318 is merged at `1df2cc9f692a6d7502379c503b62e3cbe8ffbefd`.
- Episode #8346 is merged at `7fdca240e1cfc9263458d9cd8670d06634806ded`.
- Live-flow #8322 is merged at `fbddeb4fce82525d51aa43bd87b0704a58b210b0`.
- The M1 live-flow canonical clone, swap, and reload were installed at 15:26 on `7fdca240`. The reviewed poller and plist were byte-exact. Import and help passed. The raw 28 September WAL is unchanged at SHA-256 `d9a25966a8d50090f8619d878e4133860cc54682b53764126bf7299e1ca00b06`. The reviewed quarantine receipt is SHA-256 `4b503b01eb11e19c22cb9e4bbdab630249312d0ba51d86a7755ee0619c46c819`. A second invocation was idempotent. Outside RTH the service exited 0 and was not running at 15:30.
- The root receipt is `/private/tmp/options-alpha-liveflow-cutover-20261003/receipt.json` on M1. Rollback is `/Users/chriswong/liveflow-ops-wt.orphaned-20261003T152622Z` plus the external full backup `/Volumes/STORAGE/Offloaded/m1-20261003/options-alpha-liveflow-rollback-bffd9931b2e3`, retained through the next natural RTH. This is not natural RTH publication proof.
- Terminal #788 head `38a2a15a7ba90f8ce621d0c5b00742af186129e8` is Ready and source-approved: 53 focused tests, 25 pair tests, typecheck, and build passed; browser checks at 390, 820, and 1440 in English and Chinese showed six horizons without overflow; CodeQL passed. Required CI and deploy are still owed.
- AD1 org-admin runner group 5 is still blocked by the workflow restriction. Canary is the only accepted path. `AD1_M1_LANE` is absent.

## What is left

1. Root reviews the exact head of draft PR #8358. Do not open another PR and do not mark it Ready.
2. Root finishes PR #8350, retargets #8358 to main, and runs hosted CI plus the scoped live check.
3. Activation still needs a real receipt, runner continuity at `$HOME/.local/state/mastermind/options-alpha-candidate/publication.lock`, and a natural publication readback.

## What will bite you

Until #8350 merges, this draft's parent is not on main. The builder checks activation before journal recovery and does not recompose from the journal. Enrichment reseals `feed_id` when the outcome block changes, and it refuses recorded outcome clocks later than `feed.generated_at`. A test that uses the 15 October outcome facts must observe them at or after `2026-10-16T15:00:00Z`.

## What was decided

No new DEC or DSC was minted. The daily caller, workflow gate, and terminal integrity gate are in this diff. Activation is unchanged. The availability guard is source-only: it does not create an activation receipt, write a journal, or publish to R2.

## Not in scope

Do not infer option PNL, executable options economics, option ML production authority, ranking, gating, sizing, issue-desk action, or trading from this draft. Do not create a second collector, ledger, score plane, score path, promotion path, store, or Issue Desk. Do not synthesize ChainHeat as measured NBBO. Do not re-hunt September RTH evidence. Do not reopen the OA-0 architecture freeze. Do not promote OA-1C-MACRO or OA-1T-MACRO to PROVEN_LIVE from this draft.
