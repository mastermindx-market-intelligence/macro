# Market topology: analogue test, recovery versus persistence, and fresh-progress attribution

RESEARCH ONLY. Operation `market-topology-research-20260923-astra-001`, continuing Macro draft PR #7812. MISSION_COMPLETE: false. FABLE_HANDOFF_READY: false. No production or trading authority is changed.

## 1. Material results

This phase executed a new, pre-result-specified historical analogue experiment, independently audited its predictions and chronology, and decomposed actual historical industry paths. It did not repeat the original ridge pilot, raw-stock census or synthetic overlap experiment. The separate stock ORDER_TRANSITION_TRIAL_V1 remains held on its input requirements.

Findings:

- Adding eight topology fields to a ten-feature conventional analogue did not demonstrate improved future-breadth forecasting across 311 monthly test dates. Both nearest-neighbour variants were worse than the unconditional historical mean on the primary target.
- Persistent positive participation and emerging recovery are distinct. A selected January 1992 observation had 46/49 industries positive over 63 sessions, but only 2/49 positive in each of three 21-session blocks; 30/49 followed -++. Low uninterrupted block persistence was not synonymous with a sideways population.
- Improving trailing relative momentum need not mean fresh outperformance. In 1,985 of 7,656 improving industry-month relative-momentum observations, the newest 21-session relative return was nonpositive; the change was driven by worse old returns leaving the window. This 25.93% descriptive proportion is close to a 25% IID zero-drift reference and is NOT presented as an anomaly or alpha.
- Existing Data OS has a committed identity receipt and explicit price-basis contracts; the inspected price module is V1 vocabulary, not proof of a complete raw-plus-factors economic-return extraction. Existing brain analogue retrieval is explicitly context-only. Extend existing owners rather than invent new ones.

## 2. New empirical analogue experiment

### Before-results specification

Protocol `INDUSTRY_ANALOGUE_TRIAL_V1.md` was committed at `e1c3122f8260e8b3a3e00dfaebec0bbdbf226379`, before this experiment's results. Executable `industry_analogue_v1.py` was committed at `fa741cddb525071b1ed796641013b564e8a192b2`; its exact SHA256 is in section 7.

Source: the same previously archived official Kenneth French daily 49 Industry Portfolios ZIP, verified against its original digest. First value-weighted block only; 26,296 daily rows, July 1, 1926 to July 31, 2026, header names the July 2026 CRSP database. Missing sentinels are missing, not zero. The provider documents annually assigned industries and monthly reconstruction of historical returns. Thus this is current-vintage historical research, not a record of every past real-time data release. Official methodology: https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/det_49_ind_port.html and https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html .

The input is a panel of industry portfolios, NOT individual stocks. The equal-industry daily-rebalanced proxy used in this study is not SPY or a cap-weighted market index.

551 monthly formation anchors from January 1980 through November 2025 met the complete-history requirements. Test period: January 31, 2000 through November 28, 2025, 311 anchors; zero incomplete-data or insufficient-neighbour query exclusions. Each query requires 252 complete prior daily observations in every industry. No 2026 forecast outcome was used.

At query t, candidate s is eligible only when s+20 < t-252. Distances use historical-candidate scaling, not future/test scaling. Twenty neighbours are selected greedily, with any two at least 126 observed daily sessions apart. This reduces duplicate episodes; it does not prove independence. All selected neighbours get equal weight.

Conventional features: proxy momentum over 21/63/126 sessions, 63-session volatility, drawdown from the 126-session high, positive-return breadth over 21/63/126, and above-50/200-session-average participation.

Added fields: positive and negative consistency across three nonoverlapping 21-session blocks; low net progress relative to realised volatility; top10 industry turnover; 63-session cross-sectional dispersion; average correlation; positive-gain HHI; and 21-session change in 63-session breadth. The HHI is of positive parts of industry log returns, NOT market-cap or index-contribution concentration. Augmented distance weights the conventional and added groups equally. No tuning occurred after results.

### Primary target and results

Target: fraction of the 49 industries whose returns over the NEXT 20 sessions are positive. This uses future-only performance, not an overlapping trailing-leadership label.

| Model | RMSE, percentage points | MAE, percentage points |
|---|---:|---:|
| Expanding historical mean | 30.9049 | 27.2688 |
| Conventional analogue | 32.5333 | 28.2315 |
| Conventional plus topology | 32.3085 | 28.1259 |

Primary paired MSE gain, conventional minus augmented: +0.0014570764 in fraction-squared units. Nominal 95% circular 12-month block-bootstrap interval: [-0.0033736800, +0.0066914964], 5,000 resamples, seed 2026092303. No demonstrated incremental benefit. A 0.2247 percentage-point RMSE improvement over conventional matching is not a useful forecasting claim when uncertainty spans zero and both variants lose to the simple mean.

Predeclared era breakdown of the paired MSE gain:

| Era | Queries | Conventional minus augmented MSE |
|---|---:|---:|
| 2000-2009 | 120 | +0.0028398063 |
| 2010-2019 | 120 | -0.0021999948 |
| 2020-2025 | 71 | +0.0053010336 |

All leave-one-test-year-out mean gains were positive, but the weakest was after removing 2008 (+0.0002636478). This descriptive robustness check does not override the broad confidence interval or simple-baseline failure.

### All secondary outcomes

Positive paired MSE gain favours the augmented version. These are secondary diagnostics, not alternate primary claims.

| Target | Paired MSE gain | Nominal 95% interval |
|---|---:|---|
| Future cross-industry dispersion | -0.0000071736 | [-0.0000263561, +0.0000115400] |
| Future daily proxy volatility | -0.0000018797 | [-0.0000031398, -0.0000007399] |
| Future percentile rank of current top10 | +0.0000294623 | [-0.0009308729, +0.0009479946] |
| Future percentile rank of current bottom10 | -0.0002746838 | [-0.0009574523, +0.0004041027] |

No broad predictive-success claim follows. In particular, the added group worsened volatility forecasting under this fixed method. Nominal secondary intervals are not familywise-adjusted evidence.

## 3. Independent audit and limitations

The separately specified `ANALOGUE_AUDIT_PATH_ATTRIBUTION_V1.md` explicitly says it was written AFTER the first summary. Its follow-up is diagnostic, not external preregistration or an untouched replication.

The audit recomputed every target's RMSE and MAE from saved predictions and checked 12,440 neighbour date/outcome references (311 queries x 2 models x 20 neighbours). K, spacing, candidate/query chronology and source digests passed. No candidate-training feature had zero variance, so the original script's nonzero fallback for a constant field did not affect these results. A production implementation must still implement an explicit zero-contribution rule for that edge case.

Additional diagnostic paired comparisons against the unconditional mean:

- Conventional analogue MSE gain: -0.0103301950; nominal interval [-0.0184080092, -0.0034151454].
- Augmented analogue MSE gain: -0.0088731185; nominal interval [-0.0150651309, -0.0033366583].

These intervals were not predeclared primary comparisons and are not familywise tests. They reinforce caution rather than creating a new positive claim.

Uncalibrated 10th-90th percentile ranges of neighbour outcomes averaged 75.47 percentage points wide for conventional matching and 77.85 points for augmentation. Their realised coverage was only 73.95% and 74.92%, respectively, not an established 80% guarantee. Historical outcome ranges must not be sold as calibrated prediction intervals.

The test deliberately forced 20 matches whenever technically possible. It has no calibrated no-match rule. Neighbour distance is similarity in chosen coordinates, not a probability, support guarantee or causal similarity. A more detailed feature vector can make a compelling narrative without improving forecasts. This experiment is not a test of every possible analogue method, nonlinear model, stock-level signal, macro context or horizon.

Code audit disclosure: the conventional model's descriptive `largest_feature_mismatches` diagnostic included unused added fields. Its actual distance and predictions used only the prescribed conventional fields. Narration of that model's distance must use only its actual fields; no forecast refit was performed to hide the diagnostic issue.

A separate synthetic future-perturbation test in the ChatGPT container preserved all current features within rtol=1e-12/atol=1e-14 and changed future targets; 79 synthetic anchors passed population-containment checks. An initial exact floating-point equality assertion failed on differences no larger than 1.39e-17 in three proxy fields. This was reported and replaced with a declared numerical-tolerance check, not described as a pristine exact-equality pass. Neither self-audit is an independent external reviewer or full repository CI acceptance.

## 4. Persistence versus recovery: selected real-history illustration

The protocol selected the greatest difference in three-block positive participation among anchor pairs at least 126 sessions apart, requiring 63-session positive breadth within 2/49, proxy 63-session log return within 0.03 and proxy daily volatility within 0.002. It selected January 31, 1992 and November 29, 2013 without using future outcomes. This is a maximally contrasting illustration, NOT a random sample and NOT a match on all ten conventional features. For example, their 21-session breadth differs and conventional multi-horizon breadth already contains useful distinctions.

| Observation | 1992-01-31 | 2013-11-29 |
|---|---:|---:|
| Industries positive over 63 sessions | 46/49 (93.88%) | 48/49 (97.96%) |
| Positive in all three 21-session blocks (+++) | 2/49 (4.08%) | 41/49 (83.67%) |
| Negative, then positive, then positive (-++) | 30/49 (61.22%) | 0/49 |
| Proxy oldest block return | -3.0952% | +5.3223% |
| Proxy middle block return | +9.5640% | +3.8768% |
| Proxy newest block return | +2.3537% | +2.2215% |

Remaining January 1992 patterns: ++- six, +-+ one, -+- nine, --- one. Remaining November 2013 patterns: ++- four, +-+ one, +-- one, -+- two. Counts sum to 49 at each date.

Interpretation: low +++ participation can reflect an emerging broad recovery rather than an unproductive sideways market. The word 'persistent' is not a quality verdict by itself. Preserve trajectory order, recent progress and recovery separately from historical consistency. Conversely, a highly persistent historical winner is not automatically the best forward entry. No future performance of these selected cases is asserted here.

## 5. Fresh progress versus expired history

For a 63-session log-return momentum measure observed 21 sessions apart:

M63(t)-M63(t-21) = newest21(t) - expired21(t).

The identity was checked numerically for all 49 industries at all 311 query anchors. It also holds benchmark-relatively when each return leg uses the same equal-industry proxy.

| Attribution | Improving observations | Improved without positive newest21 | Fraction |
|---|---:|---:|---:|
| Absolute momentum | 7,307 | 1,293 | 17.6954% |
| Benchmark-relative momentum | 7,656 | 1,985 | 25.9274% |

Thus roughly one quarter of these improving relative-momentum observations did NOT have positive fresh relative returns. The trailing number improved because the discarded history was worse. This is not an assertion that relative rank rose; rank also depends on peers. It is not inferred capital inflow or accumulation.

Under independent symmetric continuous zero-drift newest and expired returns, P(new<=0 and new>expired)=1/8 and P(new>expired)=1/2, giving a 25% reference ratio. The measured relative figure is close to that null. No unusualness test or alpha claim is made.

Product implication: an 'emerging leadership' explanation should distinguish fresh positive progress/outperformance from roll-off-driven improvement. It should also recognise mixed contributions, not simply invert every roll-off improvement into a bearish signal. This is a transparent attribution feature to evaluate, not a new trading rule.

## 6. Existing owner recovery and product implications

At Macro source `cde1e7e5e0cd7134f88a7f78dbeec614976c5090`, `data/reference/_receipt.json` exists, generated September 21, 2026, by build_security_master code `b7289166c9a4fcae67c7a41228a465ea6f96962f`. It reports 708 resolved out of its 718-name target, with 10 unresolved. This is NOT coverage of all historical U.S. equities or proof of every required FB/META/terminal fixture. It corrects any inference from the prior absent local directory that no identity output exists anywhere. The receipt preserves identity exceptions and expressly has no ranking, signal or trade authority.

At the same Macro source, `config/dataset_registry.yml` explicitly distinguishes raw Massive bars, Yahoo dual-basis data and stock total-return data. `lib/dataos/price.py` explicitly identifies itself as V1 vocabulary; raw-plus-factor derivation is described as V2. A labelled basis is not a verified full economic-return extraction. The raw-stock trial remains held on historical identity, factors, controls, terminal outcomes and availability clocks. The blocked R2 read was not retried.

At Macro source `8bff771709df31aa7c5be723b71f89516c7bae01`, `engine/neuralweb/brain_analogues.py` already defines `brain.analogues.v1`, display/context-only retrieval, source coverage, lag notes, time exclusion and diversity. It explicitly does not emit forecasts or probabilities. Its full-window retrieval normalization must not silently become a purported causal historical forecast. Reuse this owner for historical context; validated forecasting, if later earned, stays separate.

At Mastermind protected source `4c1b3d389286df2a4b5b98a4d4491f2c8a1263f2`, `brain/regime_frame.py` already defines a single regime reader and existing rotation-evidence consumption. The earlier rotation tensor specification overlaps several studied features. Neither source presence nor this study proves a live user path; no parallel regime, data, identity or historical-memory service should be built.

Current working architecture: a transparent population/trajectory measurement extension, a separate forecast-evaluation lane, and context-only analogue retrieval. No universal fused breadth score, assumed neural advantage, raw-momentum-to-trade authority, or Fable build assignment is accepted by these results.

## 7. Reproducibility receipts and exact next frontier

Original research artifact home: `/Volumes/Mastermind/research/market-topology-research-20260923-astra-001/`.

| Artifact | SHA256 |
|---|---|
| industry_analogue_v1.py | 7113dbb88a27532444174517c63fb9890535aaf1c202f843b469041b984af9e9 |
| analogue_v1_summary.json | f0aaec4538bec2bc8a14cb1b2a7c30898a84679de7db8e090a13bf7ab0222285 |
| analogue_v1_panel.json | 4bcde563d722e962dc04b8beb30108b047ff598051b2924b37bddcc8df285015 |
| analogue_v1_predictions.json | a88aec19a8cfbc554e682885a37e7a92f23c09fa2b6d4a36cb03760f61cc0fcc |
| analogue_audit_path_v1.py | 23ec5e4fc5d2a0006bca49d650ce53f86e553896a43187bc8d6e647ce4449de3 |
| analogue_audit_path_v1_results.json | a4c337d0815d93fdc52b4cf15d0e4244cbdaf171fc424d3fe94744df5b9f9599 |
| analogue_audit_path_v1_monthly.json | a8a5a9ca03022c628b0cd9fb096ad1042f5a67a5a5cbe0b5513dfdcd8d3a8454 |

Both remote analyses completed with exit code 0; the audit verified saved input identities and unchanged source. Public ZIP transfer into the ChatGPT container failed; no foreign mirror was used. Computation used the original archived source on its original host. Original research scripts are now committed, rather than existing only in disposable scratch. No raw vendor source archive was published.

Next: close the measurement contract and feature-retention decisions using these findings; qualify a formation-time stock extraction through existing owners when lawfully available; execute the already frozen stock comparison only after its gates pass. Independently design/test information-availability-aware macro conditioning and no-match/shrinkage for analogues without relabelling this failed fixed test as successful. A build-only Fable handoff still requires those research adjudications, exact existing-system integration, data/rights contracts and real-path acceptance tests.
