# Crypto science R2 — timing repairs and paired replay results

**Date:** 2026-09-28. **Parent:** WS:CRYPTO-INTELLIGENCE / Macro PR #8050. **Source candidate:** `a5a2d98cbb192f02113fc957fba28f40f37deff2`. **Baseline:** `060c6bab567a7e45e6aad73393ade9aff9a55016`. **Plan frozen before new full-history outcomes:** `0f5340dff3ba72fb6f07c0e0e93bc00356de392f`.

## Decision-ready result

The two R1 defects are repaired in a tested source candidate. The corrected bottom-pressure calculation has **zero prefix mismatches across all 4,393 available daily cutoffs**, versus 54 for the original. Future outcomes that have not matured now remain unknown and do not enter evaluation as negative examples. These are correctness improvements, not evidence of a newly discovered forecasting edge.

The complete old/corrected signal engines were replayed on identical stored inputs. Only bottom-pressure and its downstream allocation columns changed; the other 188 columns stayed equal. The latest stored-snapshot exposure was unchanged. The paired historical accounting improved slightly under the frozen cost scenarios, but still shows substantial drawdowns. The model is not thereby promoted or advertised as a reliable high/low oracle.

A more consequential scientific result is that **none of the three incumbent impulse legs clears its complete current evaluator gate** on this stored snapshot, either before or after the timing correction. This agrees with the pre-existing local gate artifact; R2 did not demote a live signal or modify a gate file. Earlier reports of qualified legs must not be treated as current evidence of immediate de-risk/re-entry accuracy.

## 1. The source correction preserves the original question

### Completed three-day input

R1 identified a left-labeled three-day aggregate that could attach a later close to an earlier date. R2 preserves the original three-day constituents instead of promoting R1's differently anchored research counterfactual. It exposes each aggregate only on its third daily observation's completed close. An unfinished terminal group is omitted; a group missing one of its three finite positive daily closes remains unknown. Daily and weekly signal definitions, thresholds and weights otherwise stay fixed.

Example: Jan1, Jan2 and Jan3 closes remain one group, but its Jan3 close is visible on Jan3 after close—not Jan1. This label is a daily observation date, not a assertion of midnight publication. The source's actual release/ingestion clock still needs separate qualification. Reversed, duplicate, non-date and non-midnight daily indices are rejected rather than silently made into bars.

The bottom-pressure docstring now describes a heuristic washout-pressure score, not an unsupported multiple of bottom odds. It does not become a probability merely because it is bounded between zero and one.

### Mature nullable labels

The existing forward-window construction was already fixed before R2. We retained its exact next-three-close horizon and +/-5% thresholds. R2 instead fixes the missing-outcome semantics: the reference price and all three future prices must be finite and positive, the full horizon must exist, and a daily window cannot span missing calendar days as though three observed rows were three days.

The result is nullable boolean: true event, false completed non-event, or unknown. Lift and permutation routines explicitly exclude unknown labels and safely handle empty mature samples. All labels require the same complete horizon even when a partial window has already hit a barrier; this avoids outcome-dependent early inclusion. The current price remains the legitimate return denominator; only future extrema exclude current/prior bars.

No signal threshold, portfolio rule, evaluator floor, 2024 split, minimum sample of 30 holdout fires, permutation count, config value or provider data was optimized to make the corrected result pass.

## 2. Full-history temporal proof

The replay loaded the full current stored input snapshot once, supplied deep copies to the old and corrected engines, and retained original code through an exact Git read rather than overwriting the worktree. It tested every daily cutoff from **2014-09-17 through 2026-09-26**.

| Check | Original | Corrected candidate |
| --- | ---: | ---: |
| Available daily cutoffs tested | 4,393 | 4,393 |
| Bottom-pressure value changes when future rows are removed | 54 | 0 |
| Maximum absolute prefix discrepancy, 0–1 scale | 0.1860465 | 0 |
| R1's final-366-date window discrepancies | 3 | 0 |

The first 199 observations are separately identified as short-history/warm-up rows; four original discrepancies fell in that segment. Thus the corrected result is not obtained by hiding the warm-up or avoiding the latest unfinished bucket. Complete cutoff-level evidence is in `research/crypto_science/r2/prefix_all_dates.csv`.

The count of historical values changed by the fix is a different measure: **169** full-history bottom-pressure rows differ old versus corrected. Repainting at the final prefix and consistently delaying each completed-bin value are different comparisons, so 54 and 169 are not contradictory. Downstream allocations changed on 83 dates in the optimal/moderate/aggressive variants and 84 in the conservative variant, with a maximum absolute difference of **10.6312 percentage points**. Both the raw and final columns were compared; current override configuration remains unchanged.

The other **188 of 197 columns** are unchanged. Independently, the original full engine reproduced the stored baseline's close, momentum, risk, bottom-pressure, optimal allocation and raw-optimal allocation exactly over all 4,393 common rows. This strengthens the paired comparison: it is not a synthetic substitute for the incumbent stored baseline.

At the latest stored observation, **2026-09-26**, both runs have bottom-pressure 0 and final model exposure 100%. That is a replay observation, not today's live trade instruction. The stored signals, gate artifacts and deployed site were not rewritten.

## 3. What changed economically—and what this does not prove

The diagnostic accounting was frozen before these results: one-observation-lag exposure multiplied by close-to-close returns, with 0/10/25 basis-point one-way turnover charges. The 2024+ segment uses the existing carry-in position at its boundary; no final forced liquidation is invented. No funding/cash-yield/slippage model or realistic exchange outage/fill reconstruction is included. The cost values are sensitivity assumptions, not verified venue pricing.

Selected optimal-variant results, with **10 basis points per unit of one-way turnover**:

| Stored-vintage diagnostic | Original | Corrected |
| --- | ---: | ---: |
| Full history annualized geometric growth | 60.4207% | 61.7011% |
| Full history maximum drawdown | −41.2364% | −40.6880% |
| Full history average exposure | 47.4331% | 47.3730% |
| Reused 2024+ annualized geometric growth | 16.0439% | 16.2279% |
| Reused 2024+ maximum drawdown | −31.6769% | −31.6575% |
| Reused 2024+ average exposure | 46.1813% | 46.1039% |
| Reused 2024+ turnover units | 44.7982 | 44.6568 |

All variants, both raw/final columns, both periods and all three cost assumptions are retained in the JSON rather than selecting only this table. In this replay the correction does not destroy the baseline; it improves the selected summary modestly. That is **not** evidence that timing repairs generally improve returns, that the displayed growth is achievable, or that this is new out-of-sample alpha. The rules and source data are current stored vintages applied retrospectively, and the 2024+ period was already used in earlier research.

Most importantly, drawdown near 31.7% in the reused 2024+ diagnostic remains a significant limitation for a product aspiring to strong crash protection. The next model research must improve the protection/recovery tradeoff against properly risk-matched baselines, not present a small return improvement as the mission complete.

## 4. Re-evaluating the existing short-term signals

The old and corrected evaluator were run on the same close series and same incumbent trigger definitions. No `main()` or `write_gate()` was called. The existing local `impulse_legs_gate.json`, dated2026-09-26, already records D2/D3 as demoted and U1 as insufficient sample; its hash was unchanged.

Corrected diagnostic, reused 2024+ segment:

| Leg | Hypothesis | Trigger rows | Conditional event frequency | Existing evaluator status |
| --- | --- | ---: | ---: | --- |
| D2 | DVOL range shock precedes downside | 61 | 19.6721% | demoted |
| D3 | SOPR profit-taking spike precedes downside | 31 | 12.9032% | demoted |
| U1 | SOPR capitulation precedes an upside bounce | 14 | 21.4286% | insufficient_n |

D2's reused-period lift is1.850 but its existing full-sample permutation p-value is0.4478, so it fails the combined gate. D3 has reused-period lift1.214 below its1.3 floor and p0.4153. U1 has lift1.643 and p0.0015 but only14 holdout trigger rows, below the unchanged30 minimum. These are conditional frequencies and test outputs, not calibrated probabilities for the current market. Adjacent trigger rows can overlap; 61 rows need not be61 independent episodes.

Correcting maturity changes the full label count from4,393 to4,390 and the reused2024+ count from1,000 to997. No signal happened in those last three rows, so conditional hit fractions remain equal; denominator-dependent base rates/lifts and permutation values change slightly. The status of every leg stays the same. This is valuable negative evidence: the label bug was real, but fixing it did not magically turn the current legs into accepted predictors.

**Remaining evaluator limitations are explicit.** `fire_series` still fills some unavailable feature dates withFalse; the existing broad evaluation baseline can include dates before a given source is available. Purged event-level evaluation and source-available cohorts are therefore still owed. A demotion by this gate is not proof that a feature is useless in every regime; conversely, a favorable isolated lift is not grounds to bypass its full evidence requirements. Do not silently change floors or cohort definitions until preregistered and independently reviewed.

## 5. Funding history: the next material input-contract gap

A read-only follow-up explains R1's discrepancy between a long raw funding store and only83 non-null derived funding observations. The raw file has1,168 dates and three columns:

| Physical column | Non-null rows | Coverage |
| --- | ---: | --- |
| funding_rate_fundingRate | 80 | 2026-07-01 to2026-09-18 |
| funding_rate_markPrice | 80 | 2026-07-01 to2026-09-18 |
| funding_rate | 1,089 | 2023-07-09 to2026-07-01 |

The input loader calls `_col("bgeo", "funding_rate")` without naming a field; the helper selects the first physical column. Consequently the recent80-row field enters the model, with a three-day forward-fill producing the observed83 derived rows. The older1,089-row field is not consumed. This is a confirmed selection/coverage seam, **not a confirmed safe merge of the two columns**.

Do not concatenate or rescale them just to lengthen the backtest. Provider schema, venue coverage, funding period, units, revisions and any overlap must be reconciled first. The leverage transform currently annualizes under an8-hour assumption; that assumption must be matched to the actual selected provider field. This probe changed neither input selection nor allocation. Its source/input hashes and reproduction script are retained in `r2/input_contract_findings.json` and `input_contract_probe.py`.

## 6. Verification, limitations and the next decision

Evidence includes actual RED failures for the old behavior, GREEN tests of the new behavior, full-history prefix records, paired replay, mature denominators, source/input hashes and a minimal hand-checked accounting example. The original R1 artifacts remain unchanged. The scientific suites are now invoked in the existing Vector CI step rather than simply existing on disk. No new job, control plane, strategy owner, ledger or collector was created.

Before the final extra malformed-index test, the combined current Vector/Crypto/science pack passed234 tests. The final count and static-check receipt are recorded in `research/crypto_science/r2/verification.txt`. Existing pandas/pytest temporary-browser cleanup warnings were not repaired; the paired run additionally records an existing DataFrame-fragmentation warning. None is concealed as a warning-free run.

The replay hashes **55 input files**, **18 existing data gates/ledgers** and **9 source/config files** before and after; all remain unchanged. JSON digest: `d220c97cee4c2d4386d597c128ea3d8bfa8d18ef205b62461e837c41bb2f6494`. The code correction is in the branch only, not the live publication. A complete provider-vintage/candle-availability audit, independent code/science review, exact-head CI and actual release proof remain open.

**Next substantive science phase:** qualify the funding and other input field/time contracts; build source-available mature evaluation cohorts under the existing evaluator; then preregister a fast downside experiment and a post-washout recovery experiment against the corrected incumbent baseline. The fixed-horizon research must grade warning versus continuation, false alarms, lead time, adverse excursion, missed upside and net execution. It must not treat future local extremes as achievable trades or reused2024+ data as untouched.

The immediate outcome is a trustworthy correction and an honest baseline assessment. We have not yet earned a new high-accuracy exit/entry strategy. The parent Crypto/Vector mission remains incomplete.
