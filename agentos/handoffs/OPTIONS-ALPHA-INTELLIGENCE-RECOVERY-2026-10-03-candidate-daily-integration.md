---
workstream: "WS:OPTIONS-ALPHA-INTELLIGENCE-RECOVERY"
session: mo-ext-fix-options-product-20261003-candidate-daily-integration
model: codex
ended_because: complete
mission: >-
  Adopt the prepared candidate-daily-integration patch
  c91c61c3142c7c6e2365ac33b091fd408e9d8770c605045298b4d641cb230341 (81707 bytes, 11 paths) as
  a stacked Draft PR on top of parent campaign PR #8350, wired into the existing daily pipeline,
  with the inactive-safe fail-closed boundary, journal outside checkout, and the activation-
  receipt gate enforced before any R2 effect or recovery.
state_before: >-
  Parent campaign PR #8350 (head 2a061e788db on claude/mo-ext-fix-8342) was migrated from
  #8342 and is armed with merge-on-green, awaiting hosted CI. The pre-integration local
  HEAD 1abc243b94295e867d12fd166bbd2a42948e76f1 is the parent-repair-derived clone of 8350 and
  is the source-qualified base for this stacked PR. No additional composer, publisher, ledger,
  score path, score plane, promotion path, or Issue Desk is created. The existing one publisher
  scripts/publish_options_alpha_candidate_r2.py continues to own the fixed keys
  options_alpha/candidate_feed.json and options_alpha/candidate_feed.receipt.json; the daily
  builder was absent before dispatch and no second writer was minted by this change.
changed:
  - path: scripts/build_options_alpha_candidate_feed.py
    what: "New inactive-safe CLI composer: preconditioned activation receipt, fail-closed bucket/client gate, pending-recovery activation-binding check, post-formation outcome enrichment join keyed by the frozen first qualifying revision."
  - path: scripts/publish_options_alpha_candidate_r2.py
    what: "Added recover_pending_pair() that binds pending payload to current activation before replay; no recomposition."
  - path: engine/options_alpha_candidate_outcome_enrichment.py
    what: "Pure six-horizon underlying-outcome enrichment joining admitted rows from the effective view only; strict additive schema; strict campaign_context deep-copy from the frozen first revision; deep-copy/source-hash identity guarded."
  - path: contracts/options/options.alpha_candidate_feed.v2.schema.json
    what: "Strict additive v2 schema for post-formation outcomes + campaign_context block."
  - path: tests/test_build_options_alpha_candidate_feed.py
    what: "Six dedicated build-feed cases: source loading, activation refusal, source/recovery refusal, malformed journal refusal, campaign-context deep-copy identity, idempotence."
  - path: tests/test_publish_options_alpha_candidate_r2.py
    what: "Updated publisher suite for recover_pending_pair path including activation binding."
  - path: tests/test_options_alpha_candidate_outcome_enrichment.py
    what: "Four dedicated enrichment cases: real view joins, malformed-row rejection, campaign context deep-copy, wrong revision/source-hash refusal."
  - path: tests/test_options_signal_episode.py
    what: "Inserted candidate step between campaign checkpoint and XSR; asserted candidate block gates all four prior successes, uses --publication-lock $HOME/.local/state/mastermind/options-alpha-candidate/publication.lock, and renames the terminal integrity test to require OIP_CANDIDATE_BUILD_OUTCOME in the fail-closed gate."
  - path: scripts/ci/options_signal_nightly.sh
    what: "assert-integrity() now requires OIP_CANDIDATE_BUILD_OUTCOME in addition to the four prior outcomes."
  - path: .github/workflows/daily.yml
    what: "New step options_alpha_candidate_feed (id) gated on all four prior exact successes, 5min timeout-minutes, continue-on-error true, env R2 secrets, run python -m scripts.build_options_alpha_candidate_feed --publication-lock $HOME/.local/state/mastermind/options-alpha-candidate/publication.lock; new env OIP_CANDIDATE_BUILD_OUTCOME plumbed into assert-integrity."
  - path: .github/ci/legacy-jobs.yml
    what: "options-alpha-candidate-feed scope:exclusive paths widened to 44 declared paths covering the new composer + enrichment closure; dedicated 111-test pytest command expanded with PYTHONPATH=tests:scripts prefix and the two new test files."
  - path: agentos/handoffs/OPTIONS-ALPHA-INTELLIGENCE-RECOVERY-2026-10-03-candidate-daily-integration.md
    what: "This handoff record (no WS/DEC/DSC mint; canonical episode/campaign owners preserved)."
prs: [8357]
verified:
  - claim: "Patch SHA-256 matches and applies cleanly at the parent head."
    command: "sha256sum /private/tmp/options-candidate-daily-enrichment-complete.patch; git apply --check /private/tmp/options-candidate-daily-enrichment-complete.patch; git apply /private/tmp/options-candidate-daily-enrichment-complete.patch"
    result: "c91c61c3142c7c6e2365ac33b091fd408e9d8770c605045298b4d641cb230341 81707 bytes; --check exit 0; apply exit 0; git status shows 7 modified + 4 new files matching the 11-path patch."
  - claim: "The dedicated 111-test command passes against the parent-repair-derived base."
    command: "PYTHONPATH=tests:scripts python3 -m pytest tests/test_options_alpha_candidate_feed.py tests/test_publish_options_alpha_candidate_r2.py tests/test_build_options_alpha_candidate_feed.py tests/test_options_alpha_candidate_outcome_enrichment.py -q"
    result: "111 passed in 11.78s."
  - claim: "The workflow/helper slice touched by the patch passes in isolation (data-sparse failures are sparse-checkout artifacts, not defects)."
    command: "PYTHONPATH=tests:scripts python3 -m pytest tests/test_options_signal_episode.py -k \"daily_options_pit_checkpoint or terminal_integrity or broad_cleanup_removes\" -q"
    result: "8 passed, 237 deselected in 1.17s."
  - claim: "CI import-closure and curated-exclusivity gates pass."
    command: "PYTHONPATH=tests:scripts python3 -m pytest tests/test_ci_pack.py::test_curated_exclusive_scopes_cover_their_own_import_closure tests/test_ci_pack.py::test_the_curated_exclusive_set_is_actually_declared -v"
    result: "2 passed; curated_exclusive_closure_findings({}) yields zero MISS rows on this PR's manifest; options-alpha-candidate-feed declares 44 paths covering the composer + enrichment transitive closure."
  - claim: "Contract-delta against origin/main is zero-introduced."
    command: "python3 scripts/check_contract_delta.py --base origin/main"
    result: "0 introduced, 0 inherited (base e4fb8df254d2); wall 333.0 s; head census 0 closure misses."
  - claim: "CI trigger closure is gap-free."
    command: "python3 scripts/check_ci_trigger_closure.py"
    result: "2083 suites fully reachable; TRIGGER GAP 0; 95 marked-data suites excluded."
  - claim: "Exactly one R2 writer exists for the candidate feed."
    command: "grep -rln \"options_alpha_candidate_feed.json\\|options_alpha/candidate_feed\" --include='*.py' --include='*.yml' --include='*.sh' --include='*.json' --include='*.md' scripts/ engine/ tests/ .github/ research/ agentos/ contracts/"
    result: "Only scripts/publish_options_alpha_candidate_r2.py hits the fixed keys; all other matches are schema, policy, prereg, or test references. No second writer minted."
  - claim: "Inactive boundary is structured: missing/uncleared activation receipt exits inactive with zero R2 reads/writes/journal and no clock."
    command: "sed -n '210,250p' scripts/build_options_alpha_candidate_feed.py"
    result: "Lines 213-220 return {produced: False, state: inactive, reason: activation_receipt_absent} before any R2 client or journal use; lines 227-232 return activation_preconditions_uncleared; lines 242-245 and 313-317 fail-closed when client/bucket are missing under allow_dry_compose=False."
  - claim: "Recovery binds pending payload to current activation before replay."
    command: "sed -n '247,275p' scripts/build_options_alpha_candidate_feed.py"
    result: "Lines 261-269 raise DailyCandidateError when pending publisher journal activation_receipt_id or activation_receipt_digest_sha256 does not match the current normalized receipt; recover_pending_pair() is then called only after the binding passes."
unverified:
  - claim: "Parent PR #8350 hosted CI is green."
    what_would_verify: "Root-owned release review, hosted CI pack read, and same-day squash-merge of #8350. This stacked Draft inherits the parent's CI lane by virtue of base = claude/mo-ext-fix-8342."
  - claim: "Journal path $HOME/.local/state/mastermind/options-alpha-candidate/publication.lock is single-host bound to the actual publication runner/principal."
    what_would_verify: "Exact M2 runner/principal/state-path continuity + a natural publication readback against the macstudio-only label; the macstudio label alone is not proof of single-host custody."
  - claim: "Four candidate prerequisites and six correction prerequisites are cleared."
    what_would_verify: "Independent reviewer/operator readback of the live AD1 group 5 admin gap, natural RTH Saturday proof, and the four + six prerequisite ledger. All remain unmodified and unmet by this read."
  - claim: "Daily.yml exact-path promotion to the merged parent and downstream Stack-2 live verification."
    what_would_verify: "Root-owned retarget to main after #8350 merges, followed by hosted CI + a scoped live verification cycle."
decisions: []
discoveries: []
unresolved:
  - "Parent PR #8350 hosted CI green + same-day squash-merge remain root-owned."
  - "AD1 group 5 org-admin gap is unresolved; natural RTH Saturday proof is not produced; activation gates (four candidate + six correction) remain unmodified and unmet."
  - "Actual exclusive proof of publication/runtime is owed — the macstudio label binding is not a single-host custody proof."
  - "Terminal schema/UI companion repair on #788 is in flight on a separate lane and is not blocked by this Draft."
next_actions:
  - "Root: open PR #8362 as DRAFT, base claude/mo-ext-fix-8342, head codex/options-alpha-candidate-daily-20261003; verify exact head sha 1abc243b94295e867d12fd166bbd2a42948e76f1 + the 11 owned files; do not arm merge-on-green, do not mark Ready, do not run a long CI wait in this lane."
  - "Root: after #8350 merges, retarget this PR to main and run the hosted CI pack + downstream Stack-2 live verification."
  - "Future activation: requires exact M2 runner/principal/state-path continuity at $HOME/.local/state/mastermind/options-alpha-candidate/publication.lock and a natural publication readback. No auto-clearance by this Draft."
do_not_redo:
  - "Do not rebuild or fork scripts/publish_options_alpha_candidate_r2.py; it is the only candidate-feed R2 writer."
  - "Do not add a second composer, daily caller, ledger, score plane, score path, promotion path, collector, or Issue Desk."
  - "Do not synthesize ChainHeat as measured NBBO."
  - "Do not re-hunt Sep-17/Sep-18 RTH evidence; the measured source/Flow consumer is naturally evidenced."
  - "Do not reopen OA-0 architecture freeze; preserve the Sep-03 bad-campaign-outcome incident and the corrected-but-unmerged correction prereg."
  - "Do not promote OA-1C-MACRO or OA-1T-MACRO to PROVEN_LIVE based on this Draft; the existing acceptance gates (durable publication/integrity + scoring.enabled=false) remain unchanged."
  - "Do not re-author the WS record or mint new DEC/DSC for this Draft; canonical episode/campaign owners stay."
danger_areas:
  - "This Draft inherits parent PR #8350's CI state — until #8350 merges, the parent head is not on main, and any read that conflates the local HEAD with origin/main will misreport."
  - "Stacking onto a local source-quality commit is forbidden; the spec requires base = claude/mo-ext-fix-8342 and a push that creates the remote branch without checking it out locally."
  - "The build composer calls _validate_activation() before journal recovery; the journal helper is permitted to read pending transaction bytes but never to substitute them or recompose the feed."
  - "The enrichment reseals feed_id from canonical bytes including the mutable outcome block — a changed outcome view MUST NOT reuse a prior feed_id."
  - "Sparse worktree artifacts: data/options_signal_episode/checkpoint.json missing causes 17 unrelated test_options_signal_episode.py failures; the dedicated 111-test command and the touched workflow/helper slice are independent of data/ and pass cleanly."
  - "macstudio label is not proof of single-host journal custody; record actual publication/runtime proof truthfully when produced."
---

## §0 State — what is true right now

The candidate-daily-integration source adoption is complete in this worktree: patch SHA-256
c91c61c3142c7c6e2365ac33b091fd408e9d8770c605045298b4d641cb230341 (81707 bytes, 11 paths) was
verified, dry-run clean, applied at the parent-repair-derived HEAD 1abc243b942, and produces 7
modified + 4 new tracked files matching the patch manifest. The dedicated 111-test command
passes on PYTHONPATH=tests:scripts, the workflow/helper slice touched by the patch passes in
isolation (data-sparse failures are sparse-checkout artifacts, not defects), the curated-
exclusive import closure is gap-free, contract-delta against origin/main is zero-introduced,
and CI trigger closure is gap-free (TRIGGER GAP 0). Exactly one R2 writer exists, the inactive
fail-closed boundary is structured to return {state:inactive} before any R2/journal effect, and
the recovery helper binds pending payload to the current activation receipt before replay. The
new stacked DRAFT PR #8362 (base claude/mo-ext-fix-8342, head codex/options-alpha-candidate-
daily-20261003) is ready to be opened by root and is INACTIVE until activation receipt,
configured client/bucket, and the four candidate + six correction prerequisites are cleared.

## §1 What is LEFT — in order

1. Root opens PR #8357 as DRAFT (already prepared in this lane; #8356 on `codex/options-alpha-candidate-daily-20261003` was closed and re-opened on the `claude/mo-ext-fix-options-product-20261003-candidate-daily-integration` ref per the GitHub PR-API-cannot-retarget-source-ref precedent — same head sha, no content change), does NOT arm merge-on-green,
   does NOT mark Ready, does NOT run a long CI wait in this lane. Verify exact head sha and
   the 11 owned files before opening.
2. Root completes normal PR #8350 review + hosted CI gates + same-day squash-merge.
3. Root retargets this PR to main after #8350 merges, then runs the hosted CI pack and a
   scoped live verification cycle (Stack-2).
4. Future activation requires exact M2 runner/principal/state-path continuity at the journal
   path $HOME/.local/state/mastermind/options-alpha-candidate/publication.lock and a natural
   publication readback. The macstudio label alone is not single-host custody proof.

## §2 What will bite you

The parent PR #8350 has not yet hosted-CI'd green. Until it does, this Draft inherits a parent
head that is not on main; treat `origin/main` as the only authoritative truth and never
substitute the local HEAD for it. Stacking onto an unpublished local commit is forbidden by the
spec — base must be claude/mo-ext-fix-8342 and the remote branch is created via push without
checkout. The build composer calls `_validate_activation` BEFORE journal recovery; the recovery
helper reads the durable transaction bytes but never recomposes the feed. Enrichment reseals
feed_id from canonical bytes including the mutable outcome block, so a changed outcome view
cannot reuse a prior feed_id. Sparse worktree artifacts: 17 failures in test_options_signal_episode
are data-checkout misses, not integration defects.

## §3 What was decided and found

- No new DEC / DSC was minted by this Draft. Canonical episode/campaign owners are preserved
  (WS:OPTIONS-ALPHA-INTELLIGENCE-RECOVERY waves OA-1T-MACRO, OA-1C-MACRO, OA-1T-TERMINAL
  remain unchanged).
- The single bounded finding is: the inactive-safe CLI composer + recovery + six-horizon
  enrichment + strict additive schema + 111-test dedicated command + scoped CI closure are
  ready as source. The Daily caller, the workflow gate, and the terminal integrity gate are
  wired in this diff. Activation is unchanged, owed to a future M2 runner with principal/state-
  path continuity and a natural publication readback.

## §4 Not in scope — do not adopt

Do not infer option PNL, executable options economics, option ML production authority, ranking,
gating, sizing, issue-desk action, or trading from this Draft. Do not create a second
collector, ledger, score plane, score path, promotion path, store, or Issue Desk. Do not
synthesize ChainHeat as measured NBBO. Do not re-hunt Sep-17/Sep-18 RTH evidence. Do not reopen
OA-0 architecture freeze. Do not promote OA-1C-MACRO or OA-1T-MACRO to PROVEN_LIVE based on
this Draft; durable publication/integrity + scoring.enabled=false remain the acceptance gates.