# Staged novelty admission repair

Operation: `mmx-public-intelligence-delivery-20261011-local-ceo-001`.
Base: `37ac222d0024983c830509799cddefff3fbec9e3`.
This began as an isolated follow-up while PR #8786 was proving its prior head.
That proof exposed a branch-caused CI dependency-coverage failure. The root
therefore consolidates this tested slice and the necessary CI repair onto the
same disarmed PR before fresh proof. No duplicate PR or publisher is created.

## Observed failure

Two real unedited drafts passed when individually generated. Replaying the
retained pair made the earlier Brief fail at 0.381 while the later Research
draft still passed at 0.174, against the unchanged 0.18 threshold. The shared
AI breadth paragraph had been embedded in a longer block in the later copy.
Windowed comparison was one-directional, allowing the new draft to invalidate
a previously passing staged peer only after acceptance.

The writer's first prompt has no peer prose. Its existing validation/rewrite
loop receives failure details and already owns repair/quarantine. Admission
now also scores each staged peer's prose blocks against the candidate text,
with the same quotation and required-furniture exclusions as peer replay.
This catches the overlap before a new passing stage record can be written.
Published-post behavior, thresholds, provider limits, planner deduplication,
and publication controls are unchanged. Existing records are not rewritten.

## Verification

The regression `test_self_similarity_rejects_new_copy_that_invalidates_a_shorter_staged_block`
first failed with `assert True is False`. After the repair:

```sh
python3 -m pytest tests/test_press_validators.py tests/test_press_run.py tests/test_press_writer.py -q --tb=short --basetemp=../mmx-cohort-fixtures
```

Result: **146 passed, 1 skipped in 6.33s**. The existing
`test_render_replay_is_idempotent_against_the_committed_estate` skipped because
this isolated worktree initially omits `site/`. The repair does not change
rendering. The focused new regression and two furniture/quotation controls
passed; existing self-exclusion and unrelated-copy tests also passed.
`git diff --check` exited zero.

Read-only replay through the repaired validator rejects both retained drafts
at 0.381. Their original SHA-256 values remain unchanged:

- Brief `press-brief-2026-10-11-6cf53bdfd11a`:
  `8a4c56105b869c20ce7b5928b3bab42417785cd40f70cbacdb2616434e79cfb0`
- Research `press-research_desk-2026-10-11-81675c403cda`:
  `ae72a0afdce3e0ffc261d38f8de71b330f989597fe3c25abef4191ae55bbff3b`

No new provider call, staged rewrite, emit, ledger entry or public article was
performed. This source repair does not grant the ten-draft acceptance gate,
editorial or rights approval. Continue with current-date bounded staging only
after source integration; retain each run's bytes and replay the full cohort.

## Combined-source verification

After materializing committed `site/`, the root merged exact PR #8786 source `b76706cfb9ccdd713d66ef29dca2d00c430c04e6` locally into this follow-up. There were no conflicts. This is local source integration, not protected landing.

```sh
python3 -m pytest tests/test_press_validators.py tests/test_press_run.py tests/test_press_writer.py tests/test_press_staging_inspection.py tests/test_earnings_dossier_link_contract.py tests/test_earnings_story_press_ingress.py -q --tb=short --basetemp=../mmx-cohort-integrated-fixtures
```

Result: **209 passed in 16.55s**, no skips. This includes the previously skipped estate replay, immutable dossier-link contract, read-only staging inspector and earnings ingress, against both implementation slices together. The earlier 146-test result is an overlapping subset, not additive.

## Interrupted staging attempt recovered at 16:53 UTC

The single current-date real staging attempt started at 12:07 UTC recorded one provider call at 12:07:55 UTC (19,654 input tokens and 1,097 output tokens). After interruption its process was absent, stdout log was empty, no new stage JSON existed, and the prior run summary was unchanged. Completion and command exit status are unknown. This is an **unsettled attempt, not a pass**; it is not replayed or replaced. `interrupted_staging_attempt.json` retains safe accounting fields and its hash. The two original drafts and all accounting files remain preserved. Accounting was written relative to the implementation worktree despite `--root`; those sparse local accounting files must never be staged as replacements for committed history.

The resumed source remains on the same disarmed PR #8786. Both red checks on b767 (`contract-delta` and `ci-pack-0`) report the same 19 uncovered import paths; all other 11 CI packs passed. No new provider call, publication or domain change is authorized by this recovery.

The resumed pure dependency audit completed: `python3 -m pytest tests/test_ci_pack.py::test_curated_exclusive_scopes_cover_their_own_import_closure -q --tb=short --basetemp=../mmx-closure-fixtures-resume` — **1 passed in 120.13s**, exit 0, with all 19 introduced gaps repaired. It exercised local merge `28c91feaa1c700e392d61b87facf5c175d32d159` plus the exact declaration additions. This is not hosted CI proof.

The root retained the interrupted attempt's three complete accounting files with SHA-256 receipts at `/Volumes/Mastermind/agent-workspaces/claude/14851c4656838a3b/mmx-interrupted-staging-accounting-20261011-1207/`, then materialized canonical accounting history in its own implementation worktree to permit integration. The original primary's dirty accounting is untouched. Source repair commit `c659b978ba83` is followed by conflict-free main integration `4827b81557f4689495795f8c32a8d5ed7d0f6971`, from protected main `a040596a32a4b2d690d6d921ad0ed17d97abec45`. Application implementation/tests were unchanged by that merge. `python3 -m scripts.build_free_content --check` again passed: 69 byte-identical files, zero orphans, three hand-authored exemptions. Current readonly staging replay (`cohort_recovery_inspection.json`) still rejects both preserved drafts at 0.381 and leaves their hashes intact.

Final local validation after current-main integration: import-closure regression **1 passed in 117.35s** (`--basetemp=../mmx-closure-final-fixtures`); free-content builder **69 byte-identical files, zero orphans**; Agent OS **1,643 records, zero errors, 141 warnings**. The 209-test combined application result remains applicable because main changed none of those implementation/test paths. `git diff --check` passes. PR preflight at 16:57 UTC confirmed OPEN b767 with only merge-blocked and no attached open refresh lease. The next commit is a documentation/evidence save before the same-carrier authored push; exact head and CI state must be read back after pushing.
