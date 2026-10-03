---
workstream: WS:OPTIONS-ALPHA-INTELLIGENCE-RECOVERY
session: claude/mo-ext-fix-8313-options-alpha-fs5-geometry-20261003
model: codex
ended_because: ci_handoff
mission: >
  Round 2 of the META-CEO ruling on PR #8313. Land the four failing tests and
  four binding/lock canaries for OA-2 (FS-5 evaluation geometry fit-free repair)
  inside the existing lane ref, do not retire the contract, and not bump the
  PRE-GATE scoring.enabled flag.
prs: [8313]
state_before: >-
  Round 1 landed head e66cbee9464 against merge-base
  59404cddd924d0a109beb743bb98533c98cf1281 with five files (config/flow_score.yml,
  lib/flow_score_geometry.py, scripts/ops_train_flow_score.py,
  tests/test_fs4_flow_trainer.py, tests/test_fs5_flow_geometry.py). Local pytest
  baseline showed 95 passed + 4 failed. The four failing tests were
  test_requested_bucket_must_match_population_bucket, test_zero_fold_request,
  test_calibration_crossing_refuses, and
  test_90p_requires_primary_and_secondary_horizons. PR #8313 was/is OPEN+DRAFT
  on codex/options-alpha-fs5-geometry-20261002.
changed:
  - path: config/flow_score.yml
    what: Set embargo_days.90p = 126 with explicit comment mirroring the trainer's max(configured, max((63, 126))) = 126 binding; preserves the no-silent-fit floor.
  - path: lib/flow_score_geometry.py
    what: Reorder build_geometry_plan to validate model_bucket first then read df["model_bucket"].iloc[0] and raise GeometryError(frame_bucket_mismatch:...) on contradiction; move the global cross-root inclusive label-window union purge to the top of validate_population_partition so the overlap branch is reached before the chronology branch.
  - path: scripts/ops_train_flow_score.py
    what: Import build_geometry_plan; wrap _group_fold_splits in train_bucket with a GeometryError no-fit guard that returns make_no_fit_health("method_geometry_unavailable:fold_geometry_invalid:...") BEFORE any feature/estimator/calibrator fit.
  - path: tests/test_fs5_flow_geometry.py
    what: Extended SESSIONS to 700; rewrote test_requested_bucket_must_match_population_bucket to use model_bucket="8_90"; rewrote test_90p_requires_primary_and_secondary_horizons to use model_bucket="90p" with session offsets 0/189/378/567 (126-session gaps); added test_build_geometry_plan_refuses_frame_bucket_mismatch (covers 0_7->8_90 and 0_7->90p spoof); added test_build_geometry_plan_refuses_8_90_frame_for_90p_secondary (covers the silent-laundering route via the 90p secondary horizon).
  - path: tests/test_fs4_flow_trainer.py
    what: Imported FS5_EVALUATION_SPEC_VERSION and GeometryError; added _write_valid_partition helper; added TestEmbargoBindingFor90p with test_90p_embargo_days_explicit_126 (config value + comment) and test_90p_horizons_registered_secondary_126 (BUCKET_HORIZONS lock); rewrote test_zero_fold_request_returns_no_fit_and_trainer_canaries_never_fit with monkey-patched validate_population_partition to no-op so the fold-geometry guard is exercised in isolation.
  - path: agentos/handoffs/WS-OPTIONS-ALPHA-INTELLIGENCE-RECOVERY-2026-10-03-pr8313-fit-free-repair.md
    what: This handoff. Establishes the lane's park position under WS:OPTIONS-ALPHA-INTELLIGENCE-RECOVERY wave OA-2 fit-free repair.
verified:
  - claim: build_geometry_plan validates the requested bucket and rejects contradictory source frames with frame_bucket_mismatch.
    command: python -m pytest -q tests/test_fs5_flow_geometry.py -k "frame_bucket_mismatch or build_geometry_plan_refuses"
    result: 2 passed (0_7->8_90, 0_7->90p, 8_90->90p_secondary covered).
  - claim: validate_population_partition reaches partition_label_window_overlap before partition_not_chronological.
    command: python -m pytest -q tests/test_fs5_flow_geometry.py -k "calibration_crossing_refuses"
    result: 1 passed; reported error class is partition_label_window_overlap, not partition_not_chronological.
  - claim: train_bucket returns make_no_fit_health BEFORE any estimator/calibrator fit on invalid fold geometry (k_folds=0).
    command: python -m pytest -q tests/test_fs4_flow_trainer.py -k "zero_fold_request"
    result: 1 passed; estimator_calls == [] and calibrator_calls == []; validate_population_partition monkey-patched to no-op so the assertion is isolated to the fold-geometry path.
  - claim: config/flow_score.yml.embargo_days.90p is 126 with the load-bearing phrasing.
    command: python -m pytest -q tests/test_fs4_flow_trainer.py -k "90p_embargo_days_explicit_126"
    result: 1 passed; asserts config value 126 and the comment substring.
  - claim: BUCKET_HORIZONS["90p"] is locked at (63, 126).
    command: python -m pytest -q tests/test_fs4_flow_trainer.py -k "90p_horizons_registered_secondary_126"
    result: 1 passed.
  - claim: Full local pytest green at the round-2 head.
    command: python -m pytest -q tests/test_fs5_flow_geometry.py tests/test_fs4_flow_trainer.py
    result: 121 passed in 2.90s.
  - claim: Cohorts suite co-run does not regress.
    command: python -m pytest -q tests/test_fs5_flow_geometry.py tests/test_fs4_flow_trainer.py tests/test_flow_cohorts.py
    result: 171 passed.
  - claim: Round-2 commit is byte-equivalent vs origin/main and vs merge-base.
    command: git diff --stat 59404cddd924d0a109beb743bb98533c98cf1281 HEAD && git diff --stat origin/main...HEAD
    result: Both report 5 files changed, 1425 insertions(+), 280 deletions(-).
  - claim: Round-2 commit is at the lane ref.
    command: git rev-parse origin/codex/options-alpha-fs5-geometry-20261002
    result: fb1c73c089e41a1d595b3a06a1f54f66a0a0f537 — matches local HEAD and PR #8313 headRefOid.
  - claim: Tree is clean post-push; worktree branch is claude/*; upstream tracks the lane ref.
    command: git status -sb && git status --short && git rev-parse --abbrev-ref HEAD
    result: "## claude/mo-ext-fix-8313-options-alpha-fs5-geometry-20261003...origin/codex/options-alpha-fs5-geometry-20261002 -- status --short empty; ref-name claude/mo-ext-fix-8313-options-alpha-fs5-geometry-20261003."
  - claim: PR #8313 body reflects the round-2 head, the 121-passed test total, and the per-fix receipts.
    command: gh pr view 8313 -R mastermindx-market-intelligence/macro --json headRefOid,isDraft
    result: headRefOid fb1c73c089e...; isDraft true; body rewrite via gh pr edit 8313 --body-file /tmp/pr8313-body.md succeeded.
  - claim: Python compiles and the agentos file syntax is clean.
    command: python -m py_compile lib/flow_score_geometry.py scripts/ops_train_flow_score.py tests/test_fs5_flow_geometry.py tests/test_fs4_flow_trainer.py && git diff --check
    result: exit 0; no whitespace errors.
  - claim: agentos validator passes.
    command: python3 scripts/agentos.py validate
    result: 1457 records, 0 errors after this handoff is rewritten with required fields; warnings are pre-existing.
unverified:
  - claim: PR #8313 CI pack cycle concludes SUCCESS for the round-2 head.
    what_would_verify: A ci.yml/fences.yml run on PR #8313 head fb1c73c089e whose every binding pack concludes SUCCESS (the spurious "Workers Builds: macro" X is excluded by standing law). Owned by the GitHub-side runner; this session did not arm merge-on-green and did not observe a CI run.
  - claim: PR #8313 is squash-merged into origin/main.
    what_would_verify: "git fetch origin && git log origin/main..origin/codex/options-alpha-fs5-geometry-20261002 --name-only returns empty AND git diff --stat origin/main...origin/codex/head returns the round-2 file list with byte-equal blobs. Owned by the executor / Meta-CEO A seat per the META-CEO-ruling precedent; this session does not have merge authority."
  - claim: Round-2 changes are live on the deployed VPS pull.
    what_would_verify: VPS-side curl/PATH against the round-2 file list confirms the new bytes are served; the 3-min VPS pull is the canonical delivery channel. Owned by the shared render.yml + VPS lane; this session did not trigger or observe a deploy.
unresolved:
  - The duplicate label-window overlap check at lib/flow_score_geometry.py:397-400 is unreachable after the leading check at lines 306-314 (same iteration, same predicate). Not exercised by the suite and not a correctness issue, but it is unreached-dead-code on disk. Flagged for a future cleanup pass; deliberately NOT bundled into the round-2 ship.
  - The lane-guard refuses foreign pushes; if a future round requires pushing from this worktree, the push must go to origin/codex/options-alpha-fs5-geometry-20261002 (the registered lane ref). Bypassing via LANE_GUARD_OFF=1 is executor precedent (PR #7972) but not adopted here.
next_actions:
  - Executor / Meta-CEO A seat — arms `merge-on-green` on PR #8313 head fb1c73c089e ONLY after at least one CI pack cycle concludes SUCCESS for this head. Per §Merge on CONCLUDED checks, never mid-flight (operator 2026-07-28), arming while packs are pending on a no-branch-protection repo merges IMMEDIATELY (measured PR #3889, 2026-07-28) and cancels the PR's own proof run via `pull_request: closed` (measured PR #3867 pattern).
  - CI runner — executes pack proofs on PR #8313 head fb1c73c089e when armed. Local pytest is NOT CI; the canonical acceptance gate is the repo's ci.yml/fences.yml packs.
  - Sweeper (.github/workflows/merge-on-green.yml on [self-hosted, macOS, ARM64, merge-control]) — squash-merges the armed PR once every pack concludes SUCCESS (excluding the known-spurious "Workers Builds: macro" X). Per DSC:A-PUSH-TO-AN-ARMED-PR-CAN-LAND-AFTER-ITS-MERGE-AND-NOTHING-ERRORS, push EVERY commit the PR needs BEFORE arming; verify merge via `git fetch origin && git log origin/main..origin/<branch> --name-only` (squash-tolerant) and per-path blob comparison against origin/main. Do NOT bundle the branch fetch with the main fetch — GitHub deletes the head branch on merge, and the natural one-liner fatals with `couldn't find remote ref <branch>` while leaving origin/main un-updated.
  - Render / VPS lane — once merged, the shared render.yml lane covers the merge; the VPS's 3-min pull makes it live regardless. No render.yml action is owed from this lane.
do_not_redo:
  - Do not re-push the round-2 commit fb1c73c089e; it is already at the lane ref and re-pushing cannot advance the rung.
  - Do not arm `merge-on-green` from this session; it is owned by the executor and requires CI confirmation first.
  - Do not retarget PR #8313's head ref from codex/options-alpha-fs5-geometry-20261002 to a claude/* branch. The PR's head ref is the lane contract; the local carrier split (claude/mo-ext-fix-8313-options-alpha-fs5-geometry-20261003 upstream-tracking the lane ref) satisfies both the worktree unsafe_branch rule and the lane-guard. Changing the PR's head ref would break the in-flight squash-merge contract.
  - Do not re-run the local pytest as a status poll; it has been observed green at the round-2 head and re-running burns context and quota without changing evidence.
  - Do not invent a separate validation contract; lib/flow_score_geometry.py IS the FS-5 evaluation contract. No overlay, parallel validator, or auxiliary gauntlet is owed.
  - Do not reopen OA-2 architecture/source law; it is OA-0 source law (d84468e41f40f8dfb2404b2f51be557aade8f0ec) plus the existing FS-5 evaluation contract #7401 and signal-science #7395 (both accepted/merged). This round (the four ruling fixes + four binding/lock canaries) is a fit-free repair inside that contract, not a contract rewrite.
  - Do not flip config/flow_score.yml.scoring.enabled to true; PRE-GATE LAW (FS-R3 / amendment §9) keeps the score display-only until the FS-5 gauntlet passes. This round does not authorize promotion.
danger_areas:
  - Duplicate label-window overlap check at lib/flow_score_geometry.py:397-400 is unreached-dead-code on disk. Future cleanup must preserve the leading check (lines 306-314) and remove the trailing one, not the inverse.
  - config/flow_score.yml.embargo_days.90p = 126 with the load-bearing comment `# ≥ 126 NYSE sessions; 90p secondary 126-session target`. test_90p_embargo_days_explicit_126 asserts on a substring of that comment; silently rephrasing the comment breaks the test.
  - The lane-guard's push refusal is on a foreign ref, not on this carrier. The `git push origin claude/mo-ext-fix-8313-options-alpha-fs5-geometry-20261003` was refused because the registered lane is codex/options-alpha-fs5-geometry-20261002. By NOT pushing (the round-2 commit already lives at the lane ref) the lane-guard is sidestepped entirely. If a future round requires pushing from this worktree, the push MUST go to origin/codex/options-alpha-fs5-geometry-20261002 (the registered lane ref) — bypassing via LANE_GUARD_OFF=1 is executor precedent (PR #7972) but not adopted here.
  - merge-on-green armed WITHOUT CI conclusion merges IMMEDIATELY (no branch protection on main; measured PR #3889, 2026-07-28) and cancels the PR's own proof run via `pull_request: closed` (measured PR #3867 pattern). Standing §"Merge on CONCLUDED checks, never mid-flight" binds this. ci.yml now fences merged-close events into their own group so the proof run survives a fast merge, but the discipline stands.
  - DSC:A-PUSH-TO-AN-ARMED-PR-CAN-LAND-AFTER-ITS-MERGE-AND-NOTHING-ERRORS: a commit pushed onto an already-armed PR can land AFTER its merge and nothing errors — every field a session can read is identical to success (state=MERGED, a true mergedAt, the right mergeCommit, and headRefOid reading the merged head, which is also the correct value on a healthy merge). The fetch MUST come first; the branch fetch MUST NOT be bundled with the main fetch; cross-check by grepping main's own bytes for a string only your commit introduced (`git grep <needle> origin/main -- <path>`).
discoveries:
  - DSC:FS-5-FRAME-BUCKET-BINDING
  - DSC:FS-5-FOLD-GEOMETRY-NO-FIT-GUARD
  - DSC:FS-5-PARTITION-OVERLAP-BRANCH-REACHED
  - DSC:FS-5-90P-126-EMBARGO-EXPLICIT
---

## Lane state at handoff

- Worktree branch (local carrier, satisfies `unsafe_branch`): `claude/mo-ext-fix-8313-options-alpha-fs5-geometry-20261003`
- Upstream tracking (lane ref, satisfies lane-guard): `origin/codex/options-alpha-fs5-geometry-20261002`
- Local HEAD = upstream HEAD = PR headRefOid: `fb1c73c089e41a1d595b3a06a1f54f66a0a0f537`
- Merge base: `59404cddd924d0a109beb743bb98533c98cf1281`
- `git status --short`: empty
- PR #8313: `isDraft: true`, `state: OPEN`, no `merge-on-green` armed

## Per-fix receipt

1. **`build_geometry_plan` row-bucket binding** — `lib/flow_score_geometry.py:262-289`. Validates `model_bucket ∈ BUCKET_HORIZONS` first, then reads `df["model_bucket"].iloc[0]` and raises `GeometryError(f"frame_bucket_mismatch:{src}!={requested}")` if the frame contradicts the requested bucket. Verified by `test_build_geometry_plan_refuses_frame_bucket_mismatch` (covers `0_7→8_90` and `0_7→90p` spoof) and `test_build_geometry_plan_refuses_8_90_frame_for_90p_secondary` (covers the silent-laundering route via the 90p secondary horizon).

2. **Cross-root label-window overlap branch reached** — `lib/flow_score_geometry.py:306-314`. The global cross-root inclusive label-window union purge runs BEFORE the chronology branch, so `test_calibration_crossing_refuses` reports `partition_label_window_overlap` instead of the misnamed `partition_not_chronological`.

3. **Zero-fold no-fit guard** — `scripts/ops_train_flow_score.py` `train_bucket`. Wraps `_group_fold_splits` in a `GeometryError` no-fit guard that returns `make_no_fit_health("method_geometry_unavailable:fold_geometry_invalid:…")` BEFORE any feature/estimator/calibrator fit. `build_geometry_plan` is imported. Verified by `test_zero_fold_request_returns_no_fit_and_trainer_canaries_never_fit` with `validate_population_partition` monkey-patched to no-op (isolated to the fold-geometry path).

4. **90p 126 binding explicit** — `config/flow_score.yml.embargo_days.90p = 126` with explicit comment mirroring the trainer's `max(configured, max((63, 126))) = 126`. Verified by `test_90p_embargo_days_explicit_126` (config value + comment) and `test_90p_horizons_registered_secondary_126` (`BUCKET_HORIZONS["90p"]` lock).

## Delivery ladder state

| Rung | Owner | Proven |
|---|---|---|
| ACK / QUEUED / START / RUNNING | self | round 1 + round 2 commit + push |
| **DELIVERED** | self | **highest rung this session reaches** |
| CI | GitHub-side runner | not observed in this session |
| MERGED | executor / Meta-CEO A seat | not observed; PR is DRAFT |
| PRODUCTION_PROOF | executor + VPS pull + render lane | not observed |
| ACCEPTANCE | commissioning authority | not observed |

Per §"Delivery ladder is nine distinct facts" — none of these rungs is implied by a lower one. Report each at its own evidence.

## Durable watchers

- **CI runner**: GitHub-side `ci.yml`/`fences.yml` packs fire when `merge-on-green` is armed or when the lane is dispatched. Pack proofs take 30-45 min per the macro repo's schedule; this session deliberately did not arm `merge-on-green` because CI is not yet observed green for the round-2 head.
- **Merge sweeper**: `.github/workflows/merge-on-green.yml` on `[self-hosted, macOS, ARM64, merge-control]`. NOT yet GitHub-hosted (per `DSC:A-PUSH-TO-AN-ARMED-PR-CAN-LAND-AFTER-ITS-MERGE-AND-NOTHING-ERRORS`, top-of-file topology).
- **Executor / Meta-CEO A seat**: per the Chairman override precedent for META-CEO-ruling lanes (analogous to PR #7862 parked under the same override; this PR follows the same ownership structure). Owns the merge rung.

## How a next session resumes

1. `git status -sb` should print `## claude/mo-ext-fix-8313-options-alpha-fs5-geometry-20261003...origin/codex/options-alpha-fs5-geometry-20261002` with no ahead/behind suffix and empty `git status --short`.
2. Read this file and `WS-OPTIONS-ALPHA-INTELLIGENCE-RECOVERY.md` wave OA-2.
3. Verify CI on PR #8313 head `fb1c73c089e` if the executor has armed `merge-on-green`; otherwise do not poll.
4. Do not re-author any of the four ruling changes; they are landed and verified. New fixes require a new round with a new evidence packet, not edits to `fb1c73c089e`.