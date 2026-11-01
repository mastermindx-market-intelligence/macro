# Press single-attempt qualification

Operation: `mmx-public-intelligence-delivery-20261011-local-ceo-001`.
Implementation: `2343aaec13bb13acff087fbd5fd61e72173c5634`.

The next ordinary qualification run can explicitly request `--single-attempt`.
The runner sets regeneration to zero and reuses the existing writer control that
sets Anthropic SDK retries to zero and supplies only the first usable provider
adapter to the waterfall. A handled provider or validator failure is quarantined
after that one adapter invocation. Default scheduled behavior, planner/revision reconciliation,
validation, accounting, rights and emit authority are unchanged. The option
applies per planned slot; `--max-slots 1` bounds the run to one slot.

This source is now integrated locally with the audit-discovery slice and current
main at `1c7b997f92fbe611d84a5e0c48a16291c90a6f1f` for the same PR #8786.
Protected landing, installation and a real generated draft remain unproven. The earlier lost provider
response remains unsettled; the new option does not authorize its replay or
claim globally exactly-once execution. The Codex adapter launches one CLI turn,
but does not forward this SDK retry setting or explicitly bound the CLI's
internal request/stream retries. Therefore the option is not a guarantee of one
actual upstream request for every provider, nor a hard total-spend cap.

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

The independent bounded acceptance reviewer inspected the orchestrator,
provider construction, Codex adapter/runner, planner and emitter at implementation
2343aaec13bb. No new reservation, rights, validation or emit defect was found.
The supported claim is one provider-adapter invocation per slot, no Press
fallback/regeneration, and Anthropic SDK retries disabled. The CLI help and
documentation now state the Codex limitation explicitly; no provider/runtime
owner was changed to extend the claim.

The corrected CLI help was inspected with `python3 -m scripts.run_press --help`;
`python3 -m pytest tests/test_press_run.py -q -k cli --tb=short
--basetemp=../mmx-single-attempt-help-fixtures` passed **5 tests in 1.90s**.
Only help/docstrings changed after the accepted behavioral suites.

Independent live-path evidence is retained in `public_pathway_browser_20261011.json`:
the existing TTWO dossier rendered in Chrome and its Earnings-record link reached
the expected record; the record's Terminal link preserves TTWO, quarter and
acquisition parameters. The public record exposes only a shortened source hash
and its own bounded evidence policy, not a new article-rights or immutable-packet
admission receipt. No Terminal denial was retried and no signup/follow was mutated.
`updater_preflight_20261011.json` retains the read-only installation preflight:
the updater is current and cron exists, source advances, and later W2C runtime
diagnostics are present. Press installation still needs its own source/served
proof after protected landing. No manual updater or service restart ran.

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
