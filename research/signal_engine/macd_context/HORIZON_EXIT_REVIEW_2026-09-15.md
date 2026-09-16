# MACD horizon, exit and common-state review — 2026-09-15

**State: PARTIAL research; descriptive development evidence; zero production authority.** This continuation consumes the existing frozen replay. It does not rerun it, create a new market sample, establish statistical superiority, or approve a trade rule.

## Evidence and review boundary

Current Skillpack: Mastermind@4709b9483182c20153868dac164e1f621aac505c, schema1/version1.0.1/bootstrap1. Current Macro main inspected: 52bd0cde0669cd8ea396dfbe692399261dd5cfe5. Existing publication carrier is PR7177, sol/macd-cycle-research-20260915-c3. Original research carrier remains Remote Desktop Commander on the same Mac Studio.

The prior combined horizon-table inspection had failed. Current direct bounded same-carrier reads succeeded. All eight existing replay-output digests and the source digest match the original receipt. No original equity replay was run again, no raw price data was moved to another host, and no 2026 equity outcome was admitted.

This review joined all 126,440 incumbent-family event identities to the original table and verified both 21/63-session raw and SPY-excess returns with rtol=0, atol=1e-12: the measured maximum absolute difference was exactly 0.0 for each of the four outcome columns. All non-null modeled entries are after the event date. The common252 summary has 1,404 rows and zero censored outcomes across its declared policies.

The common252 sample retains only events with 252 sessions of follow-up available before the frozen 2025-12-31 cutoff. It fixes the cohort across horizons *within each construction*, not across constructions. It does not fix the current-universe survivorship exposure or equalize stock/date/risk populations.

Local review evidence: `/Volumes/Mastermind/Mastermind/artifacts/macd-context-first-look-20260915-c3/cycle_extension_v2/review_20260915_r1/`. `review_receipt.json` names the source and exported-table digests.

## 1. The same crossover cohort gives different answers at different horizons

Bullish crosses in each construction's own deep-negative bin; next-session adjusted-close entry; gross positive endpoint returns. These are not target-before-stop wins.

| Construction | Common-cohort n | 21 sessions | 63 sessions | 126 sessions | 252 sessions |
|---|---:|---:|---:|---:|---:|
| Price-fast 3D | 1,094 | 67.28% | 66.09% | 69.65% | 75.96% |
| Price-fast weekly | 524 | 52.67% | 61.45% | 67.18% | 75.00% |
| RSI-slow 3D | 3,127 | 58.49% | 63.35% | 68.53% | 74.51% |
| RSI-slow weekly | 1,812 | 59.99% | 61.75% | 65.40% | 72.24% |

Corresponding mean SPY-relative endpoint returns:

| Construction | 21 sessions | 63 sessions | 126 sessions | 252 sessions |
|---|---:|---:|---:|---:|
| Price-fast 3D | +1.33% | +0.46% | +1.18% | +6.27% |
| Price-fast weekly | -1.28% | -1.52% | -0.06% | +6.66% |
| RSI-slow 3D | +0.07% | +0.28% | +1.21% | +2.95% |
| RSI-slow weekly | +0.33% | -0.23% | +0.63% | +2.63% |

The weekly deep-negative price condition is poor as a one-month selector in this sample, yet stronger at one year. This supports a horizon-dependent interpretation, not an optimal one-year holding rule. The horizon curve is not monotonic in relative return; there is no single universally best endpoint established here.

### The baseline rises too

All weekly price-fast crosses in the same follow-up cohort are 73.82% positive at 252 sessions (7,315 observations), versus 75.00% for the deep-negative subset. Other known-depth weekly crosses are 73.68% positive. Thus the high long-horizon headline does not represent a 75-percentage-point selection advantage or a high-certainty entry.

The deep-negative weekly mean 252-session return is 27.05%, versus 18.44% across all weekly price crosses. That payoff difference deserves investigation, but it is not risk/date matched. At 21 sessions the same deep-negative group is 52.67% positive versus 58.61% across all weekly price crosses.

For 3D price-fast, all-cross positive frequency is 61.05% at 21 sessions and 74.42% at 252; the deep-negative subset is 67.28% and 75.96%, respectively. Its positive-rate lift narrows substantially with horizon, while payoff and exposure questions remain distinct.

RSI-slow 3D is especially instructive at 252 sessions: deep-negative is 74.51% positive and all-cross is 74.48%, essentially the same sign frequency, while mean SPY excess is 2.95% in the deep-negative subset versus 4.78% across all crosses. A high endpoint-positive rate alone is not evidence that the depth filter improved selection.

These all-cross references are signal-population benchmarks, not arbitrary-day, risk-matched or portfolio counterfactuals.

## 2. Native-bar time does not erase timeframe differences

Deep-negative price-fast, common252 cohort, exit after ten additional completed native bars at the following session close:

| Signal grain | Typical holding sessions | Positive rate | Mean SPY excess | Median close-path adverse excursion |
|---|---:|---:|---:|---:|
| Daily | 10 | 58.84% | +0.24% | -2.17% |
| 2D | 20 | 60.69% | +0.21% | -3.31% |
| 3D | 30 | 66.54% | +1.38% | -3.99% |
| Weekly | 48 | 56.68% | -1.80% | -7.13% |

Ten weekly bars are a different economic and risk commitment from ten daily bars. Equal native bar count is a useful second ruler, not a universal correction that makes horizons comparable. The adverse-excursion values use closes, omit intraday lows, and are medians rather than worst-case risk.

## 3. Waiting for the opposite crossover changes both hit rate and payoff shape

Opposite-cross policy: first subsequently confirmed bearish histogram crossing, executed at the following session close, capped at 252 sessions. It is a diagnostic, not an accepted structural-hold exit.

| Deep-negative construction | Positive rate | Mean gross return | Mean SPY excess | Median holding sessions |
|---|---:|---:|---:|---:|
| Price-fast 3D | 51.74% | +4.99% | +0.19% | 60 |
| Price-fast weekly | 48.66% | +7.63% | -0.24% | 97.5 |
| RSI-slow 3D | 47.84% | +2.59% | +0.15% | 45 |
| RSI-slow weekly | 46.41% | +3.69% | +0.20% | 67 |

For price-fast 3D, the fixed-21 positive rate is 67.28%, versus 51.74% for the opposite-cross exit. The latter nevertheless has a larger mean gross return, with winners averaging +17.49% and non-winners -8.41%. Its SPY-relative mean is small. Lower hit rate is not by itself proof of a worse strategy, and higher mean gross return is not proof of a superior deployable policy.

Weekly price-fast has median opposite-exit return -0.40% despite mean return +7.63%. For weekly RSI-slow the corresponding figures are -1.18% and +3.69%. The distribution is asymmetric; the average and the typical trade tell different stories.

The policy does not include a protective stop, portfolio exposure constraints, sector neutrality, market impact, or an actual Prophet candidate admission rule. No return is annualized or represented as portfolio CAGR.

## 4. Longer holding does not produce certainty

For weekly deep-negative price-fast at 252 sessions, the 5th percentile endpoint return is -28.81%; the mean return among non-winners is -19.33%. For 3D price-fast, the corresponding 5th percentile is -25.82%.

These are endpoint losses, not maximum drawdowns. The review does not have 252-session intraday or close-path adverse excursion in the saved table, and does not infer it from the endpoint. The profitable one-year headline is therefore not evidence that a short-horizon trader can safely tolerate the path.

The saved illustrative cost sensitivity is 10 basis points per side, not a calibrated execution model. For example, weekly price-fast fixed-21 positive frequency falls from 52.67% gross to 51.15% under that sensitivity. Liquidity- and volatility-dependent costs still need qualified input data.

## 5. Common price-depth conditioning changes the price/RSI comparison

The following table uses a common *price-fast MACD depth predicate at each native grain*, rather than each trigger's own depth bin. It uses the full matured cohort for each horizon, not the common252 cohort above.

| Trigger / grain | 21-session n | 21-session positive | 21-session mean return | 21-session SPY excess | 63-session positive | 63-session mean return |
|---|---:|---:|---:|---:|---:|---:|
| Price-fast / 2D | 2,062 | 60.82% | 2.20% | +0.33% | 64.71% | 5.14% |
| RSI-slow / 2D | 3,036 | 61.00% | 2.56% | +0.40% | 64.78% | 5.70% |
| Price-fast / 3D | 1,178 | 67.49% | 3.68% | +1.42% | 66.70% | 5.81% |
| RSI-slow / 3D | 1,795 | 60.67% | 2.60% | +0.65% | 66.12% | 5.82% |

At 63 sessions the 3D mean returns are essentially equal, and RSI-slow mean SPY excess is 0.885% versus 0.771% for price-fast. At 21 sessions price-fast retains a larger point estimate in 3D. At 2D the same broad dominance claim is not present.

The common predicate improves interpretability of input comparisons at the *same grain*. It does not equalize event dates, tickers, risks or trade opportunities. Across grains, the price-depth predicate itself is evaluated on different bars. Do not describe this as a fully matched causal comparison.

A new predeclared module to calculate pooled year-cluster and shared-date uncertainty for four input/memory contrasts was blocked during its first source write. Native readback returned ENOENT. Its two test cases were observed RED because the implementation was absent. No comparison interval was computed, no alternative implementation/carrier was used, and no statistical-superiority claim is made here. This is a new narrow code-execution boundary, not a continuing claim that the frozen horizon tables are inaccessible.

## 6. Canonical look accounting: measured and staged, not yet applied

The current-main TrialLedger source blob is eb364fe9fa53f46d0455e194d3e3ccdbb5732778, and the canonical data blob is da5647e6fc67697384813406874c436740017b23. Both match the local read-only copies. The canonical file has 1,674 rows and no matching MACD-context/cycle family.

The evidence census found 23 generated summary CSVs containing 6,235 rows: 736 first-look rows, 5,267 extension rows, and 232 attribution rows. These are diagnostic cells/views, not 6,235 independent tests, profitable strategies, or event observations. The base construction grid is 18 variants times 13 policies = 234 construction/exit combinations before context and cohort views.

A temporary-copy dry run used the unchanged canonical TrialLedger.log_declared_budget API to propose a scoped floor of 6,235 under family macd_context_cycle. It preserved the entire original prefix, added one row, and a second identical call added zero rows. The temporary copy was removed. The generated proposed_trial_ledger_reconciliation.patch is 1,080 UTF-8 bytes and targets only an append to data/trial_ledger.jsonl.

**The patch is a proposal, not a second ledger and not an applied registration.** The count/family and completeness of historical exposure still require the evaluation owner's adjudication. No multiple-testing correction, DSR, or calibrated probability is inferred from the number. In particular, it is not certified as the total of every undocumented historical research decision.

The current GitHub file-update action requires complete replacement text for the existing approximately 642 KB ledger; it does not offer append/patch execution. The attended workspace wrapper verified here targets the Mastermind repository, not Macro. No shared source/worktree was silently modified and no alternate publication carrier was substituted. The exact patch/preimage and inventory now make the remaining owner-native append bounded rather than unspecified.

## 7. Source custody and reproducibility

The previously host-only expanded replay has now been published under `source/run_extension.py`. Its Git blob 4fe9e9abcafdef5f903db4df3c21dc5b834e36db was verified byte-identical to the measured local source (SHA256 4ab075bf730b780e51d904f4f7301a964b259c6c3614d1033765f4e6d289a803). `source/test_extension.py` and the original `source/RESUMPTION_AMENDMENT.md` accompany it.

The source retains the original run-time pins, by design; those are provenance of the completed run, not current procedure. Full replay still requires the rights-constrained frozen price/calendar/event inputs and the original reproduce_study.py at its already-recorded digest. Those remain at the source root. The published mechanical tests use synthetic prices and do not require those equity files.

This source publication is not an independent scientific review or production deployment. The two new blocked comparison tests are not included as passing tests. A future reviewer must distinguish the already-working replay from that unfinished extension.

## Mechanism and implementation ruling

The useful result is a differentiated measurement contract: trigger location, signal memory, intended horizon, exit policy, incremental payoff and path risk must remain separate. No single MACD percentage answers all those jobs.

Primary-source mechanism priors remain Dai et al., *Reversals and the Returns to Liquidity Provision* (FAJ 2024; NBER w30917), and Daniel/Moskowitz, *Momentum Crashes* (JFE 2016; NBER w20439). The former distinguishes volatility-linked fast reversal from turnover-linked persistence; the latter motivates state-dependent rebound-exposure controls. They motivate hypotheses, not causal explanations already verified in this panel. Elliott-specific incremental value is still untested.

Next primary action: the approved Macro evaluation/source owner adjudicates and applies the staged retrospective-accounting append against the verified current preimage, then independently reviews the published replay and current horizon/exit evidence. New uncertainty execution remains at its explicit platform boundary. Before promotion, freeze an owner-native common-opportunity early/confirmed policy with real fills, costs and invalidations; qualify point-in-time sector, liquidity, universe and delisting inputs; and accrue forward evidence through existing owners. Do not optimize away the exposed failures, select per-name historical winners, replace Prophet RSI, or promote the 75–76% headlines to customer probabilities.
