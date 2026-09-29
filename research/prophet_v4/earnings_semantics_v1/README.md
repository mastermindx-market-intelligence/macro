# Prophet Earnings Semantics v1 — source repair and research seam

**Date:** 2026-09-29  
**Base:** `d5e20a62b5da656f62b3cc06a7c7675c43f0de1a`  
**Status:** BUILT_NOT_PROVEN on this branch; no live rank promotion, no regrade, no financial-effect authority.

## Why this exists

The US C1 board and its grading extractor used the same legacy Boolean:

```python
bool(sue_z and (sue_fresh_days or 999) <= 60)
```

That expression has three semantic problems:

1. an age of zero is falsy and becomes 999;
2. any negative non-zero `sue_z` is truthy;
3. invalid negative ages can satisfy the age cutoff.

More importantly, the native upstream `engine/sue.py` measure is not an analyst-consensus beat. It is based on quarterly EPS minus the calendar-matched year-ago EPS and is later standardized. A positive relative value therefore must not be presented as proof that the release beat a genuinely available analyst expectation.

The September 29 outcome-blind census on the committed 69-row board found 59 finite upstream earnings-momentum values among matched names, while only 14 board rows carried the existing earnings chip. That is evidence that a Boolean chip discards magnitude/sign information. It is not permission to backfill history, lower a coverage floor, or promote a new model.

## Implementation boundary

This branch adds the explicit extraction version `numeric-sue-compat-v1.1`.

- **Default remains `legacy`.** The current C1 champion and historical grades retain their original Boolean semantics unless an explicit caller selects the new version.
- **The corrected observation is non-authoritative.** It exposes finite relative value, valid zero age, explicit stale/unavailable states, and labels the measure as `cross_sectional_z_of_seasonal_eps_momentum`.
- **No consensus claim is created.** `analyst_consensus_beat` and raw seasonal surprise direction remain unknown in this adapter.
- **No rank or entry authority is created.** The structured observation stamps both as false.
- **Serving and evaluation use the same explicit version.** Unknown versions refuse rather than silently falling back.
- **Missingness is not smuggled into the current model.** The explicit compatibility mode keeps the existing Boolean slot Boolean while exposing missingness separately in the structured observation. Making the rank feature itself nullable is a different scientific change because it can alter family coverage and ranking.

## Source paths

- `engine/us_prophet_fusion.py` — versioned observation and optional extraction mode.
- `scripts/grade_us_board.py` — same optional extraction mode for evaluation; default unchanged.
- `tests/test_us_prophet_fusion.py` — legacy freeze, corrected edge cases, serving/evaluation parity and unknown-version refusal.

No outcome labels, H1/Cycle protected results, rank weights, B4, holding policy, options authority or portfolio policy are modified by this branch.

## Acceptance claims

The source change is acceptable only if all of the following hold on the exact candidate head:

1. existing C1 tests remain green;
2. default extraction still equals the legacy Boolean on the committed board when that artifact is present;
3. the corrected mode treats positive age-zero evidence as fresh, negative relative evidence as non-positive, stale evidence as stale, and invalid/missing inputs as unavailable;
4. serving and grading agree under both versions;
5. no other C1 member changes when only the earnings extraction version changes;
6. CI import-closure / source-ownership gates remain green;
7. no board or grade history is rewritten.

Green software tests do not establish predictive value.

## Next investment-quality unit

Under the existing Earnings/D5 and Evaluation owners, bind one exact earnings release and a genuinely pre-release expectation to a source-backed dossier. Preserve separately:

- reported operating change;
- seasonal EPS-change strength;
- genuinely comparable expectation surprise where licensed;
- matched-contributor forecast revisions;
- revenue/EPS agreement or conflict;
- share-count / per-share transmission;
- the price move already elapsed before the source became usable;
- present entry geometry and market permission.

Only after that factual input is source-qualified should B10/B15 test incremental selection value against the existing price/sector baseline. The comparison must use the same eligible population and information clocks; it must not relabel this source repair as alpha.
