# Staged novelty admission repair

Operation: `mmx-public-intelligence-delivery-20261011-local-ceo-001`.
Base: `37ac222d0024983c830509799cddefff3fbec9e3`.
This is a follow-up source slice, separate from the running PR #8786 proof.
It must integrate #8786's protected landing before the combined implementation
is claimed. It does not replay or replace that PR's source changes.

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
