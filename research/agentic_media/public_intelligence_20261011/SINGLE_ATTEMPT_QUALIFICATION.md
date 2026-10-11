# Press single-attempt qualification

Operation: `mmx-public-intelligence-delivery-20261011-local-ceo-001`.
Implementation: `2343aaec13bb13acff087fbd5fd61e72173c5634`.

The next ordinary qualification run can explicitly request `--single-attempt`.
The runner sets regeneration to zero and reuses the existing writer control that
sets SDK retries to zero and supplies only the first usable provider to the
waterfall. A handled provider or validator failure is quarantined after that
one attempt. Default scheduled behavior, planner/revision reconciliation,
validation, accounting, rights and emit authority are unchanged. The option
applies per planned slot; `--max-slots 1` bounds the run to one slot.

This is source prepared for later integration. It is not yet in PR #8786, main,
the installed service or a real generated draft. The earlier lost provider
response remains unsettled; the new option does not authorize its replay or
claim globally exactly-once execution.

## Verification

Before implementation, the provider-failure and validator-failure regressions
failed because `run_staging` lacked the new argument, and the CLI execution
regression rejected the unknown flag: **3 failed, 1 passed**. The separate
emit-refusal test was subsequently tightened to require the specific diagnostic.

After implementation and materializing committed `site/`:

```sh
python3 -m pytest tests/test_press_validators.py tests/test_press_run.py tests/test_press_writer.py tests/test_press_staging_inspection.py tests/test_earnings_dossier_link_contract.py tests/test_earnings_story_press_ingress.py -q --tb=short --basetemp=../mmx-single-attempt-complete-fixtures
```

**218 passed in 36.32s**, no skips. A final writer regression then exercised the
actual provider waterfall with controlled clients: default mode attempts the
second provider after the first fails; opt-in mode never calls it and passes
`client_max_retries=0` to construction. Final affected runner/writer verification:

```sh
python3 -m pytest tests/test_press_run.py tests/test_press_writer.py -q --tb=short --basetemp=../mmx-single-attempt-final-fixtures
```

**95 passed in 6.93s**, no skips. These suites overlap; do not add their counts.
The tests also establish that emit plus the flag is rejected before config load
or any emit action, and that ordinary qualification does not acquire the separate
immutable-ingress token-admission flag. All provider clients are controlled
fixtures; no real generation, publication or ledger append occurred.

## Recoverable source and next action

Owned worktree:
`/Volumes/Mastermind/agent-workspaces/claude/14851c4656838a3b/mmx-press-single-attempt-20261011-565fd14116bdcee2`.
Branch: `claude/ssd-mmx-press-single-attempt-20261011-565fd14116bdcee2`.
It starts at main `98a40e3f4b13876ee66cb0325e510273fd473d84` and merges the frozen
#8786 candidate through local merge `2024e0bd11b38a22bb659726548925aab5f20cf1`.
No duplicate PR or second release controller was created.

First complete #8786's existing protected refresh/landing/install/browser path.
Then integrate this real follow-on change against landed source and obtain its
own required proof. Only after current source identity, cadence, writer state and
input rights are ready should an ordinary current-date qualification use:

```sh
python3 -m scripts.run_press --staging --desks brief --max-slots 1 --single-attempt
```

Do not backdate or rerun the unsettled slot. The qualified market-event story
still requires the existing Earnings owner's immutable packet/revision and
public-article rights receipt through its permitted read path; this CLI option
does not replace `scripts/stage_earnings_story_press.py` or source ownership.
