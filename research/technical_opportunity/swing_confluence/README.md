# Swing Confluence research recipe

**Current capability: PARTIAL.** A deterministic local recipe compiler is implemented and tested. The intraday backtester, data admission, full scientific registration and lab/chart UI integration are not delivered by this slice. No market-performance result exists here.

This is a leaf consumer of Mastermind's existing Strategy Lab, Technical Opportunity Intelligence, Temporal Grain, Live Entry Radar and TrialLedger/Evaluation OS. It is not another lab service, indicator implementation, calendar, data store or evaluation authority.

## Use the saved environment

From the Macro repository root, with its Python environment (runtime uses only the standard library):

```bash
python scripts/research/run_toi_swing_plan.py \
  --recipe research/technical_opportunity/swing_confluence/recipe.json
```

For a complete 720-case plan, choose a **new**, nonexistent JSON file:

```bash
python scripts/research/run_toi_swing_plan.py \
  --recipe research/technical_opportunity/swing_confluence/recipe.json \
  --output /tmp/swing-confluence-plan-001.json --include-cases
```

The destination parent must exist. Existing files and symlinks are refused; there is no overwrite option. JSONL and the reserved trial_ledger.json name are refused. The CLI does not register a trial or call the backtester. References and statuses in the recipe are frozen planning assertions, not live owner receipts or permissions.

Copy the recipe to a new study artifact and change its candidate axes. Indicator-bundle and exit labels are not executable indicator formulas. Session length supplies arithmetic only. Changing a hash or study label does not reset the canonical research family's testing budget. Dates, point-in-time cohort, exact indicator parameters, source/session/correction receipts, folds, executable fills and the trial registration must be frozen by existing owners before any outcomes are read.

## Included candidate matrix

Two families: leader pullback and range reversal. Six trigger/setup pairs in minutes: 15/60, 30/120, 30/180, 30/130, 30/195, 60/240. Two memory controls, three mechanism bundles, five holding caps (1/2/3/5/10 sessions), two exits, three cost stresses and four controls.

The result is **720 configurations**, **2,160 cost scenarios** and an **8,640 paired-comparison upper bound**. These are plans, not completed backtests or independent trials. The 10-basis-point one-way primary cost is an uncalibrated planning assumption; it is not a verified execution-cost estimate. No best timeframe or profitable strategy is claimed.

## Tests

```bash
python -m pytest tests/test_toi_swing_plan.py -q
```

The isolated local slice passed 54 synthetic configuration/CLI tests. These do not test market returns, native Temporal Grain functions, the complete Macro repository, hosted CI, or production charts. See VERIFICATION.md for exact artifact identities and limitations.

## Read next

- DESIGN_AND_RESEARCH_PROTOCOL.md: ownership and experiment contract.
- RESEARCH_ASSESSMENT.md: the entry objective, separate setup families, rates/event evidence, falsification and chart-review design.
- IMPLEMENTATION_PLAN.md: scope and local implementation steps.
- VERIFICATION.md: what was and was not proved.
- recipe.json: editable saved candidate matrix.

## Remaining owner dependencies

The data-admission carrier is existing Macro #7094; the evidence census is #7107; candidate temporal machinery is #6803. At the exact recovery reads, #7094 was PARTIAL/HOLD and #6803 remained unmerged. Preserve their writers, early-close/fallback/basis/availability findings and outcome holds. This new leaf consumer does not take their custody or repair them.

Next capability step: reconcile those owner returns, admit the exact requested cohort and grains, register the two hypotheses and holding rulers, and connect the saved recipe to the existing intraday evaluator and Terminal replay. Independent source review and full-repository/hosted validation are also outstanding. No worker, watcher, live run, merge or deployment is created by this directory.
