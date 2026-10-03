---
ws: OPTIONS-OA3-EXACT-RULER
date: 2026-10-03
status: EXACT_HUMAN_GATE
head_sha: e7388708361db9ae06806ead6757c492b8d44aad
remote_branch: origin/codex/options-alpha-exact-ruler-20261003
local_branch: claude/options-alpha-exact-ruler-20261003
---

# Wait

## Why

The OA-3 exact-option outcome ruler fixture (frozen by
`DEC:OPTIONS-ALPHA-EXACT-OPTION-OUTCOME-RULER`) is fully implemented,
tested, committed and pushed, but the lane cannot lawfully finish the
PR chain in-session: two guards disagree on the branch name.

## What is verified green

- `engine/options_alpha_exact_option_outcome.py` — pure fixture-only
  OA-3 v1 evaluator.  Reuses only generic mechanics from
  `engine/options_nbbo_cohort.py`.  No MomoEdge benchmark identity,
  registries or 600s live-capture fence inherited.  Status vocabulary
  is the closed five states.  All 11 authority flags are false.
- `tests/test_options_alpha_exact_option_outcome.py` — 46 focused
  tests.  All pass: `46 passed in 0.34s`.
- `tests/test_options_nbbo_cohort.py` — 63 existing tests still pass
  with the 5 policy assertions kept:
  `63 passed in 4.11s`.
- Exact head `e7388708361db9ae06806ead6757c492b8d44aad` is pushed to
  `origin/codex/options-alpha-exact-ruler-20261003` (the lane name
  the mission explicitly named).

## Constraint the seat must resolve

1. The mission spec told me to use
   `codex/options-alpha-exact-ruler-20261003`.  That push is done.
2. The ship loop independently rejects any non-`claude/*` branch as
   `unsafe_branch`.
3. The lane guard refuses to push anywhere but the lane-named ref
   (`refs/heads/codex/options-alpha-exact-ruler-20261003`), and refuses
   `git branch -m` to rename.
4. The lane guard refuses `gh pr create` (executors never do this; the
   seat does).

The seat must decide one of:

  - **(A) Accept the `codex/*` lane branch** as the canonical PR branch
    for this extension lane (the worktree path
    `mo-ext-fix-options_product_20261003_exact_ruler` strongly suggests
    a Codex-extension lane, not a `claude/*` Claude session lane),
    then open the DRAFT PR against `main` @ `60d7551e52c` with the
    bundled description (see "PR body" below).
  - **(B) Rename the lane** to a `claude/*` name and re-push under that
    name.  This is a seat-level git operation the executor cannot
    perform.

## PR body (drafted for the seat)

    ## OA-3 exact-option outcome ruler fixture (DRAFT)

    Implements the pure fixture-only OA-3 v1 evaluator frozen by
    DEC:OPTIONS-ALPHA-EXACT-OPTION-OUTCOME-RULER.

    ### Branch / head

    - Branch: `codex/options-alpha-exact-ruler-20261003`
      (or `claude/options-alpha-exact-ruler-20261003` per seat choice)
    - Head: `e7388708361db9ae06806ead6757c492b8d44aad`
    - Base: `origin/main` @ `60d7551e52c`

    ### Files changed

    - `engine/options_alpha_exact_option_outcome.py` (new) — pure
      fixture-only OA-3 v1 evaluator.
    - `tests/test_options_alpha_exact_option_outcome.py` (new) — 46
      focused tests.

    ### Spec invariants honored

    - Long single-leg, one-contract, H+60 NBBO quote ruler
      (entry ask / exit bid).
    - Reuses only generic mechanics from
      `engine/options_nbbo_cohort.py`.
    - Does NOT reuse the MomoEdge benchmark cohort identity,
      registries, or 600s live-capture fence.
    - Closed status vocabulary:
      `pending | complete | unavailable | excluded | invalid`.
    - Frozen arithmetic:
      `100*((100*exit_bid-0.65)-(100*entry_ask+0.65))/(100*entry_ask+0.65)`.
    - All 11 authority flags are false; no fill claim.
    - Exit window starts at admitted `entry.event_at + 60m` (NOT at
      `expression.available_at + 60m`).
    - Causal clock ordering enforced.
    - Raw response + canonical payload SHA256 + byte count bound to
      the record.

    ### Tests

        python -m pytest tests/test_options_alpha_exact_option_outcome.py
        # 46 passed in 0.34s
        python -m pytest tests/test_options_nbbo_cohort.py
        # 63 passed in 4.11s

    ### Out of scope

    - Live source-query wrapper (`build_observation`, `source_query`)
      is intentionally NOT inherited from the benchmark cohort.
    - Package / short / non-standard / multi-leg accounting remains a
      separate later ruler.

## Open by URL

    https://github.com/mastermindx-market-intelligence/macro/pull/new/codex/options-alpha-exact-ruler-20261003

## DO NOT REBUILD

The OA-3 v1 evaluator contract is pinned by
`DEC:OPTIONS-ALPHA-EXACT-OPTION-OUTCOME-RULER` and the machine policy
JSON
`research/options_estate/options_alpha_exact_option_outcome_policy_v1.json`.
Do not re-propose the contract; this packet is an evaluator fixture
under the contract.

## Verified

- `git status --short` — clean (2 files already committed).
- `git rev-parse HEAD` — `e7388708361db9ae06806ead6757c492b8d44aad`.
- `git ls-remote origin codex/options-alpha-exact-ruler-20261003` —
  exact head present.
- `python -m pytest tests/test_options_alpha_exact_option_outcome.py` —
  `46 passed in 0.34s`.
- `python -m pytest tests/test_options_nbbo_cohort.py` — `63 passed in 4.11s`.