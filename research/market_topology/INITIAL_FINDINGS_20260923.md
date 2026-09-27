# Market topology: initial research findings, 2026-09-23

Status: RESEARCH INCOMPLETE. Not a production specification, accepted alpha model, or build commission. Fable handoff is held. This document records actual experiments and a revised research direction, not a claim that the wider study is finished.

Operation: `market-topology-research-20260923-astra-001`.
Procedure: Mastermind protected master `4c1b3d389286df2a4b5b98a4d4491f2c8a1263f2`, compatible Skillpack 1.0.1, INDEX/COLD_START/ACTIVE_EXECUTION/WEB_CEO_DELEGATION/CLOSEOUT loaded from that revision.
Architecture/Agent OS reference base: macro `88a3f1cfd18f391d2802e9086dc00f6fe5545607`.

## 1. What is being investigated

The core question is not simply how many securities advance. It is whether observing the identity, persistence, path, concentration, and transitions of participating securities gives a more useful account of the market, and whether any of that information improves forecasts beyond strong conventional baselines.

Three claims must remain separate:

1. Measurement: a representation describes current/past market structure more faithfully.
2. Prediction: it adds calibrated out-of-sample information about a specified future outcome.
3. Decision value: a feasible workflow or trading policy improves after costs, timing, risk, and selection effects.

An answer to the first is not evidence for the other two. Current leadership, expected future return, and suitability of an entry are distinct outputs. Narrow leadership is not automatically bearish. A high sign-switch rate is not automatically a poor holding experience.

## 2. Experiment A: daily breadth does not identify longitudinal populations

Executed a deterministic synthetic construction of 100 securities over 60 sessions. These are invented returns, not current or historical market observations.

Every session in both markets has the same complete return multiset: 20 securities with log return +0.004, 40 with +0.001, and 40 with -0.002. Therefore both have exactly 60% advancers, identical daily cross-sectional dispersion, identical cumulative advance-decline lines, and an identical DAILY-REBALANCED equal-weight index path.

Market A keeps 20 securities at +0.004 each day and 20 at -0.002. Its other 60 securities are three staggered groups repeating [+0.001,+0.001,-0.002]. Market B cyclically reallocates the same daily return multiset across identities by shifting its vector by five places per session.

| End of 60 sessions | Market A | Market B |
|---|---:|---:|
| Daily advancing share | 60% every day | 60% every day |
| Net-positive securities | 20% | 100% |
| Flat securities | 60% | 0% |
| Net-negative securities | 20% | 0% |
| Security-level cumulative outcomes | 20 at +27.1249%; 60 at 0%; 20 at -11.3080% | All at +2.4290% |
| Daily-rebalanced equal-weight index | +2.4445% | +2.4445% |

This is an identifiability counterexample: daily marginal statistics discard the identity linkage needed to reconstruct individual trajectories. It is NOT a demonstration that all conventional breadth measures fail. The 60-session positive-return participation measure already separates these examples. The study must beat a strong multi-horizon breadth baseline, not a straw-man one-day indicator. The construction also does not assert equality of buy-and-hold index paths.

Executed script SHA-256: `7671ae6f40653b4716797575b92d6d7f1314cfecb33adaed96e51a091959e121`.
Recorded result SHA-256: `6b5d8d7b571fcf88de16d74851aa660a1554821d26fbafda82400fe26cbaeaf5`.
The original ChatGPT scratch files were not present in the later container generation; these are execution receipts, not a claim those paths remain accessible. The construction is fully specified above.

## 3. Experiment B: pre-result frozen industry forecast pilot

### Data and protocol

Source: Kenneth French's daily 49 Industry Portfolios, FIRST value-weighted return block. Source URL: https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/49_Industry_Portfolios_daily_CSV.zip . Methodology: https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/det_49_ind_port.html .

Downloaded on 2026-09-23. File header states the 202607 CRSP database. Data span 1926-07-01 through 2026-07-31, 26,296 daily rows and 49 industries. Original -99.99/-999 missing sentinels were converted to missing, not zero. Percentage returns were divided by 100 before log1p. No forward-fill.

The protocol was frozen before inspecting predictive results; this is not external preregistration. Formation dates are month-end observed sessions, with 252 valid daily observations required. Training anchors start in 1990. For each test year 2010-2025, an expanding training sample includes only anchors whose 20-session forward outcome is fully observed before January 1 of that year. Outcomes extending beyond 2025-12-31 are excluded. Target: cross-sectional rank of the next 20-session cumulative log return.

Fixed ridge penalty 10 with an intercept, no parameter tuning. Features are cross-sectionally percentile-ranked at each anchor. Baseline and augmented models use identical complete-case samples.

Baseline features: 63-session momentum; 252-session momentum excluding the latest 21 sessions; 5-session return; 63-session realized daily volatility; 63-session momentum divided by that volatility.

Augmented features: signed efficiency `sum(r)/sum(abs(r))`; positive-day fraction; sign-switch fraction over the 62 adjacent pairs in a 63-return window; largest absolute daily move divided by total absolute movement. Zeros retain their zero sign, and missing observations are never treated as flat days.

Also evaluated the unfitted 63-session momentum ranking. Metrics: monthly Spearman rank information coefficient (IC), top-10 predicted/realized membership overlap, annual IC, and feature rank correlations. The paired IC difference uses a nominal 95% circular block-bootstrap interval: 12 monthly anchors per block, 5,000 resamples, fixed seed 20260923. No trading PnL or Sharpe claim.

### Actual results

191 test anchors from 2010-01-29 through 2025-11-28; all 49 industries available at each test anchor.

| Model | Mean rank IC | Mean top-10 overlap |
|---|---:|---:|
| Unfitted 63-session momentum | 0.020695 | 0.245550 |
| Momentum/volatility baseline | 0.031986 | 0.243455 |
| Baseline plus four path-quality features | 0.029690 | 0.239267 |

Paired mean IC increment: **-0.002296**. Nominal 95% block-bootstrap interval: **[-0.008361, +0.003544]**. Augmented annual mean IC exceeded baseline in only 6 of 16 years.

Mean cross-sectional rank correlation of signed efficiency with raw momentum: **0.938651**. With volatility-normalized momentum: **0.995989**.

Conclusion: this feature bundle and fixed model did not demonstrate incremental forecast value on this industry-level, 20-session test. Efficiency is nearly redundant with volatility-normalized momentum here. Do not promote it into a standalone alpha component. This is not a rejection of all persistence research, all nonlinear interactions, stock-level effects, or other horizons. It is not a literal replication of the Frog in the Pan paper.

Limitations: industry aggregates can hide within-industry dispersion; the data are current-vintage historical returns, not archived releases; one model and horizon; close-to-close research labels rather than executable next-session entries; nominal interval without multiple-testing adjustment; no September 2026 market inference. Training complete-case selection and any future stock-level eligibility logic require explicit audit rather than silent generalization.

### Reproducibility receipts

Research artifacts are on the authorized Studio under `/Volumes/Mastermind/research/market-topology-research-20260923-astra-001/`, not in a production data path. No raw vendor data are included in this PR.

- `49_industries_daily_source.zip`: SHA-256 `13be85084196424aa85f29136af47f147a443275f90eb0955dbcdc6d6d25f448`.
- `industry_pilot_v1.py`: SHA-256 `0fb167fb698f163a29e244206ede4b2f3d7e7a81efd914aaa428d87ca574c1e8`.
- `industry_pilot_v1_results.json`: SHA-256 `2de1afd4e2ee416eeb199a1513e5faa78160690d67348844fe219146f625c734`; independently re-read with shasum on the same host.
- `industry_pilot_v1_monthly.json` and `industry_pilot_v1_feature_correlations.json` retain the detailed results.
- Original pre-result protocol digest: `406b913c5b325c17ec2643718149f75d0de204e439c5d5d677cb89a96dab6e0f`. The original ChatGPT protocol scratch file is not asserted to survive; its complete substantive rules are recorded above.

Execution completed with exit code 0. Do not rerun unchanged work merely to reconstruct a progress narrative. Independent reproduction is appropriate only as a named validation task or after a material invalidator.

## 4. Experiment C: order-blind path metrics miss different holding experiences

A second deterministic synthetic test holds the 63-session return multiset, final five returns, 63-session momentum, 252-session momentum excluding 21 sessions, volatility, volatility-normalized momentum, efficiency, positive-day share, largest-move share, and terminal return fixed, but changes return ordering.

Both sequences have 63-session total return +2.122205%, efficiency one-third, and positive-day share two-thirds. Yet one has sign-switch frequency 14.5161% and maximum drawdown -0.697556%; the other has sign-switch frequency 62.9032% and maximum drawdown -0.199800%.

Construction uses `u=0.001`, `d=-0.001` log returns. Both share a 189-session prefix alternating +0.0003/-0.0003, beginning positive. The last 63 returns are:

- A: `14*u, 7*d, 14*u, 7*d, 11*u, 5*d, [u,u,d,u,d]`.
- B: `[u,u,d]` repeated 7 times, then repeated another 7 times, then `[d,u,u]` repeated 5 times, then `u`, then `[u,u,d,u,d]`.

Maximum drawdown is computed from the running peak of `exp([0,cumsum(last63)])`; sign-switch frequency uses its 62 adjacent pairs. Assertions verify matched features to numerical tolerance.

This establishes two cautions. First, `sum(r)/sum(abs(r))` is invariant to a permutation of the returns; it does not encode their full temporal order. Second, more frequent sign reversals need not imply worse drawdown or less cumulative progress. Therefore identity turnover, directional reversals, net progress, drawdown, and recovery time must not be collapsed into one supposedly monotonic 'bad churn' score.

No forecast benefit is claimed. The empirical pilot already included sign-switch frequency without a demonstrated aggregate improvement. A subsequent order-sensitive test must not forget that negative result.

Script SHA-256 `d141949216ebbcf2f03f6abd0841de74c8ff20233bda2f339c13f741d0facce7`; result SHA-256 `bdcbce48a1093bd45f35bdafc80a5b06ceb7f62f52bf3687d3e31432fe8b13ec`.

## 5. Prior research and the novelty boundary

Da, Gurun and Warachka's Frog in the Pan studies return-path information conditional on prior momentum. Its information-discreteness measure is not an interchangeable synonym for our 63-session efficiency ratio, and its individual-stock design differs from this pilot. Author manuscript: https://academicweb.nd.edu/~zda/Frog.pdf .

A Frog in Every Pan studies information discreteness and return lead-lag among economically linked firms: https://www.gsb.stanford.edu/faculty-research/publications/frog-every-pan-information-discreteness-lead-lag-returns-puzzle .

The publisher abstract for Herding for profits: Market breadth and the cross-section of global equity returns reports breadth-related information beyond standard controls: https://www.sciencedirect.com/science/article/pii/S0264999319312982 . Only abstract-level claims are being used for this source, not an asserted full-paper replication.

These are prior-art anchors, not independent validation of our proposed product. The opportunity is to test and integrate useful distinctions into a coherent, point-in-time-correct workflow, not to claim discovery of persistence or breadth as new fields.

## 6. Existing architecture and material data limits

Mastermind already has a related `research/eyes/rotation_spec.md`: relative-strength velocity, participation migration, top-cohort Jaccard turnover, flow proxies, and episodes. It names the existing market-view reader and advisory publication surfaces. Document presence is SPEC_ONLY evidence, not proof the producer and user path are live. Do not build a parallel rotation/state/data authority. Some example units merit recalculation before reuse.

Macro's `research/entry_intel/P0_2_SURVIVORSHIP_CENSUS.md` is a prior 2026-07-04 audit, not a fresh September census. It identifies substantial older-history missing coverage, especially removed names. The deep close matrix was originally built from current constituents; a long historical date span alone does not make its universe point-in-time correct. Missing acquisitions and missing failures cannot be assumed to cancel.

This session found actual local Macro stores: 20,476 files under `data/massive_stock_day`; a deep close matrix; a manually supplemented delisted matrix; and S&P 500 membership intervals. Presence is not proof of adjustment correctness, security identity continuity, terminal delisting returns, or complete coverage.

The sampled local Massive files for SPY, SMH, SOXX, BROS, KRUS and MCD all ended on **2026-07-02**. The corresponding local Yahoo paths were absent in the checked checkout. This says nothing about other production hosts, but these files cannot validate a September 22/23 current-market claim. French industry data end July 31. The current semiconductors-versus-consumer observation remains UNVERIFIED.

## 7. Revised representation and experiments

Keep a small, auditable vector rather than inventing a universal breadth score. Each observation must bind entity/universe, effective date, information-availability date, horizon, benchmark, eligibility, and coverage.

Candidate dimensions: absolute and relative progress; identity persistence; return ordering/drawdown/recovery; cross-sectional concentration and dispersion; population transitions; context and uncertainty. Relative leadership and positive absolute compounding are separate: a stock can lead a falling market while still losing money.

Population denominators must distinguish genuine transitions from index additions/removals, listings, missing data, and coverage changes. Unknown is not sideways. Transition counts need common eligibility and should expose entries/exits separately. Current descriptive labels must never use future-confirmed bottoms or retrospectively revised regimes.

The next discriminating empirical question is whether order-sensitive and cohort-transition information improves outcomes among stocks matched on momentum, volatility, industry, size and liquidity. Outcome families must remain separate: return rank, leader survival/deterioration, downside continuation, and prospective bottom-confirmation/failed-recovery rates. Define horizon and event labels before seeing results. Repeated windows are not independent episodes.

For historical analogues, start with interpretable past-only standardized features and episode-separated nearest neighbours. Predefine the available feature set and missingness policy, prevent outcome leakage into matching, report support and dissimilarities, and permit no-match. Neural representations must earn their place against these baselines; do not use a large feature database to justify unconstrained post-hoc pattern hunting.

## 8. Continuation and build gate

Next primary action: qualify one existing stock-level research panel before fitting another predictor. Audit stable security identity/ticker reuse, membership eligibility, corporate-action adjustment, terminal outcomes, actual dates, and matched coverage. Decide which claims that panel can support. Then freeze and execute a stock-level, momentum/volatility-matched order-and-transition experiment, retaining the failed industry pilot as prior evidence rather than tuning it away.

Independent research can define leader-survival and bottoming outcome labels and review relevant primary literature while the data lane is qualified. No blanket human or tool blocker has been established.

Fable build handoff remains held until accepted descriptive contracts, validated or explicitly rejected predictive components, data entitlements and quality, existing-owner integration, user workflows, reproducible experiments, bounded vertical slices, and production acceptance criteria are settled. No production code, worker commission, trade sizing, deployment, or autonomous market monitor was created by this study.
