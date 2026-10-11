# Press interrupted-attempt recovery

Operation: `mmx-public-intelligence-delivery-20261011-local-ceo-001`.

## Verified problem

The 12:07 UTC current-date staging attempt left a provider-accounting row but no staged draft or completed run receipt when interrupted. Source inspection confirms the existing Codex adapter invokes an ephemeral process and returns its response in memory; `run_press` previously wrote the slot only after validation and its full retry loop. The missing historical response cannot be reconstructed from token accounting. That attempt remains unsettled and is not replayed or backfilled.

## Isolated repair

Before the first provider call, write a durable `in_progress` record in the existing staging directory. Create it exclusively: a pre-existing record, including a partial or unknown attempt, cannot be overwritten by a new preplanned call. The existing planner already excludes its source references, and the existing emitter only accepts `passed`; no new queue, publisher, approval or runtime owner is introduced.

After a successful writer return, retain the draft, provider/model, retained draft attempt number, available usage receipt and writer state before validation begins. During retries the progress field identifies the active attempt separately from the retained earlier draft. Finished passed/quarantined record shapes remain unchanged. Slot checkpoints and the final run summary use atomic replacement with file and directory synchronization. A storage failure propagates; there is no provider replay or in-memory success fallback.

This narrows the response-loss window. An interruption inside the provider or between its return and persistence can still leave an unknown response, but the initial record blocks blind replay. This does not recover the already-interrupted historical attempt, settle a live writer, authorize a retry, or grant publication.

## Test evidence

Both interruption regressions first failed on the missing checkpoint (`FileNotFoundError` and `StopIteration`). The implemented tests cover interruption during a provider call, interruption during validation, replay refusal without a second provider call, non-emission of incomplete drafts, storage failure before any provider call, and preservation of the previous complete JSON when atomic replacement fails.

```sh
python3 -m pytest tests/test_press_run.py tests/test_press_staging_inspection.py tests/test_earnings_story_press_ingress.py tests/test_press_writer.py -q --tb=short --basetemp=../mmx-recovery-final-fixtures
```

Result: **104 passed in 5.58s**, no skips after materializing committed `site/`. These use the existing fixture writer; no provider generation, publication, ledger append or domain action occurred. `git diff --check` passes.

## Delivery frontier

This slice is isolated in `/Volumes/Mastermind/agent-workspaces/claude/14851c4656838a3b/mmx-press-attempt-recovery-20261011-a46f27ad11045cb8`, initially based on fresh main `565d883c26571b00d7f660f56689f33ce8b13dcc` and merged with exact PR #8786 candidate `3b8a642735378309e73107690bbc4682ffbd3108` as `b45d8d629bd88c91ef39b998fc79708559b577cc`. It does not change the running PR proof. Preserve that sole carrier until its protected outcome settles; then integrate this separately tested follow-on through the normal current-main release path. No duplicate PR has been opened.

Additional integrated failure-boundary check: `python3 -m pytest tests/test_press_run.py::test_storage_failure_after_provider_return_blocks_replay -q --tb=short --basetemp=../mmx-recovery-returned-storage-fixtures` — **1 passed in 2.76s**. This injects replacement failure after the fixture writer has returned, verifies the original complete reservation survives, and proves an attempted repeat makes no second provider call. The implementation is unchanged from the 104-test result.
