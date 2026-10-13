# Q09 PREREG amendment 1 — post-hoc, non-confirmatory

Status: POST-HOC. Written after the independent audit (verdict PASS_WITH_FIXES; 0 blockers,
0 majors, 6 minors), and before any re-run that reads new outcomes. PREREG.md stays frozen
at sha256 `7b256cb8b990c424a14545c442a239c2fcd4b07a9448673988d8e9009b9f8a3a` (FREEZE.log).
None of the items below changes a §7 parameter, the confirmatory statistic, the holdout,
the seed or the decision rule. Under PREREG §8, this amendment cannot alter the verdict.

## A1. Erratum to PREREG §0 (line 27)

PREREG §0 says week 20260629 has "2,727 tickers present in both T1 and T2". That count is
wrong. The correct count is **413** tier-ambiguous tickers. It matches `support.20260629.
n_tier_ambiguous_dropped` in results.json, and VERDICT.md already reported 413. The
evaluation code has always dropped these tickers from the per-symbol panel (PREREG §3).
Only the prose in §0 was wrong.

## A2. Descriptive concentration is restricted to the T1+T2 universe (PREREG §6)

- **The problem.** The §6 descriptive market-wide ATS HHI and the non-ATS HHI summed every
  tier, OTCE included, with no coverage gate. In the latest week OTCE is about 3.9% of ATS
  shares and 28.5% of non-ATS shares. PREREG §3 defines the universe as T1/T2, and it
  excludes OTCE as a different market.
- **The fix.** From this amendment on:
  - Descriptive concentration takes per-tier venue volumes for T1 and T2 only.
  - The volumes pass through `coverage_snapshot` (required tiers T1 and T2, on the store
    clock) and then through `combine_tier_volumes`. Combining them refuses a partial state.
  - Every subject string names its tiers.
  - The excluded OTCE fraction of reported volume is printed beside each result.
- **What does not change.** The incumbent baseline reproduction keeps its verbatim
  all-tier logic, because it is a reproduction of the incumbent and it is labelled that
  way.
- **The store clock.** Each week file is committed whole, so every tier in it shares one
  store-first-seen upper bound: `per_week[w][1]`, or `bulk_commit_time` for a bulk week.
  The store does not separate tiers in time.
- **Status.** These are descriptive, non-trial outputs. They carry no verdict weight.

## A3. Clock enforcement of the split

The split was always required to respect the store clock (§3/§4):
- training weeks are admissible at the forecast origin;
- holdout weeks are first seen after it.

`evaluate.py` used to compute this flag without enforcing it. It now refuses to run
(`SystemExit("REFUSING: ...")`) when the flag is false. The flag is true for the frozen
inputs, so no number changes.

## A4. Wider forbidden-interpretation guard

- **Matching.** The guard now normalises text before it matches: lower-case, with `-`,
  `_`, `/` and runs of whitespace collapsed to one space. It also checks a
  separator-free form.
- **New terms.** It adds `accumulat`, `buying pressure`, `selling pressure`,
  `net purchase`, `institutional distribution` and `whale`.
- **Scope.** It now runs over the whole results dict, not only the descriptive block.
- **Not covered.** VERDICT.md and PR_BODY.md are not machine-guarded. They have to state
  the restrictions as negations ("FINRA short volume is not short interest"), and a
  substring guard cannot tell a negation from a claim. Their text is reviewed by hand
  for affirmative use instead.

## A5. Run attestation (RUNS.log)

- **Data hashes.** `_log` used to copy the PREREG's expected data hashes. It now records
  the data hashes this run recomputed.
- **Outputs.** It records output hashes only when the run exits 0 and this run wrote
  the file.
- **This amendment.** It also records the sha256 of this file, and `evaluate.py` refuses
  to run if this file does not match `AMENDMENT.log`.

## A6. Bootstrap helper

- **The change.** The ratio bootstrap moves from inline code into the module function
  `moving_block_bootstrap_ratio`. That function uses the same RNG draw sequence, so the
  CI is reproduced exactly; a test pins it against the inline algorithm.
- **Why not the existing helper.** The existing `moving_block_bootstrap_mean` bootstraps a
  mean, not the pre-registered ratio R. Calling it would change the statistic, so it is
  not used.
- **Caveat (stated in VERDICT).** The CI rests on 7 holdout weeks with block length 2,
  which is about 4 effective blocks. A percentile CI from so few blocks is coarse and its
  coverage is not reliable. The R sub-result is descriptive context only.
