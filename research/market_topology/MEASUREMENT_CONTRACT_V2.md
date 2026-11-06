# Market participation and leadership: measurement contract v2

RESEARCH DESIGN DECISION, NOT PRODUCTION ACCEPTANCE. Operation `market-topology-research-20260923-astra-001`; draft PR #7812. This refines the measurement/null/clock/context sections of `MEASUREMENT_AND_INTEGRATION_DRAFT_V1.md`; its existing-owner, no-duplicate-plane, forecast and Fable holds remain unchanged. No production code imports these research references. They are executable specifications for the later builder, not a new identity, data, control, memory or trading system.

## 1. Product boundary

The product must distinguish what is happening, why a metric changed, what relevant operating evidence says, and what a separately validated forecast predicts. It must not use one 'true leader' label for four different claims: past price leadership, current positive progress, business improvement and attractive future returns.

First useful user outcome: the user can open a declared universe or security, compare its recent and intermediate paths, understand changes in participation, see contradictory business evidence, and inspect historical context without receiving an unearned buy/bottom probability. This measurement outcome does not complete the parent research mission's emerging-leadership and loser-continuation forecasts.

## 2. Population and horizon identity

Every observation binds an existing universe-policy reference, stable entity IDs, entity level (security/issuer/industry portfolio), exchange session, horizon, weighting rule, benchmark, return basis, source revision and coverage. No ticker string is minted into an identity here. A missing share-class policy is not automatically equal-issuer weighting.

Three populations remain distinct:

- Market census: the declared population, including unavailable observations.
- Tradable opportunity set: the current price/liquidity/security-type eligibility policy.
- Formation cohort: the population fixed when a historical observation or forecast was made, including subsequent exits and failures.

Horizon labels use observed trading sessions, not casual calendar-week/month names. The selected current case has 20 increments and four 5-session blocks. Earlier industry studies used 63 increments and three 21-session blocks. Those definitions cannot be silently interchanged.

The basic descriptive predicate is literal: economic holding return over h completed sessions > 0, = 0, or < 0; unavailable input is unknown. 'Positive' is not 'materially profitable after costs' or 'persistent leader'. Thresholds for economically material progress, trend strength or future opportunity remain separate empirical decisions. Recent listings use a disclosed short-history profile; failure to meet the long-history forecast sample does not classify an IPO as weak or sideways.

## 3. Missingness is quantified, not hidden

For N census identities, p known positives and u unknown predicates, the full-census positive share is bounded by [p/N,(p+u)/N]. For known complete nonnegative weights, replace counts by positive, unknown and total weights. These are sharp logical bounds under missing classifications, NOT confidence or prediction intervals. Their validity assumes the declared population and observed labels are correct; they do not bound identity or corporate-action errors.

The known-only ratio p/(N-u) is a conditional statistic and must be labelled as such. Example: 20 positive, 50 negative and 30 unknown produces a known-only 28.57%, while the census share is only known to lie between 20% and 50%. Neither '28.57% of the whole market' nor 'unknown means sideways' is permitted. An all-unknown census yields [0,1] with no known-only estimate; an empty census yields no estimate. If weights themselves are missing, do not silently invent equal weights to report a market-cap-weighted bound.

The reference `participation` validates exact weight identities and literal true/false/unknown flags. Weights are scaled before summation to avoid overflowing on large but finite inputs; known weight is summed directly so a tiny known component is not lost through subtraction. An explicit extreme-weight counterexample exposed NaN in the initial reference; the corrected code and regression tests are the committed version.

## 4. Change attribution

On common identities, split known state changes from known/unknown coverage changes. Add observed-positive contributions from universe entrants and exits separately. Their sum must equal the change in observed-positive counts exactly. The complement of a leader flag is not automatically a loser state.

For a common, fully known population with normalized weights, the symmetric decomposition is:

  change sum(w*s) = sum(mean(w_old,w_new)*(s_new-s_old))
                 + sum(mean(s_old,s_new)*(w_new-w_old)).

The first term is state change; the second is reweighting. This is arithmetic attribution, not a causal explanation or investment-return contribution. Entry/exit and unknown-state effects are separate, not forced through this point decomposition. The reference returns a residual to check.

A hypothetical removal of 20 non-leaders from a 100-name universe with 20 leaders raises the share from 20% to 25% without any common-name state improvement. A changing market-cap weight can likewise change weighted breadth with no new positive names. Show these explanations instead of advertising false expansion.

## 5. Path, benchmark and overlapping information

Keep cumulative return, ordered block returns, running-peak drawdown, adverse excursion from formation, time underwater and recovery distance separate. A sign pattern is a literal path description, not a prediction. Current selected examples establish the need: BROS/MCD have four negative 5-session blocks, KRUS has three negative blocks then a positive one, while SMH has two positive blocks, one negative block and a strong positive final block. See the current-case report and its diagnostic addendum; no whole-market prevalence follows.

For log momentum, delta over k sessions is newest-k minus expired-k returns. Attribute both pieces. Relative-momentum improvement from expiring bad history is not new relative outperformance or observed buying. Price-volume statistics alone also do not establish institutional accumulation or net primary-market flow.

A common benchmark subtraction in log returns, or division by the same positive benchmark gross return, preserves cross-sectional security ranking. It is not an independent second ranking signal. Industry-specific comparisons, beta-adjusted residuals and absolute-positive predicates answer different questions and may differ. The reference verifies common-benchmark rank invariance, including tied total-loss outcomes, across 1,000 random inputs.

Chance-adjusted cohort overlap is a fixed-size independent-set reference only. It does not remove the mechanical overlap of trailing return windows, factor correlation or correlated securities. The earlier IID survival experiment remains controlling evidence against treating trailing-label retention as future alpha.

Concentration outputs must specify what is concentrated: issuer counts, lagged market weights, positive return contributions, negative contributions or economic exposures. Do not divide by nearly zero net returns to create unstable percentages, and do not rename positive-industry-return HHI as cap-weighted index contribution. Within- and between-industry dispersion require historical membership and stated weights. Many co-moving stocks are not automatically many independent opportunities.

## 6. Operating facts and expectations

Preserve operating measures individually, including their fiscal periods, definitions, currency, accounting basis, per-share basis, release time and source. Total revenue growth, same-establishment sales, traffic/transactions, price/mix, margins and financing are different observations. They need not point in the same direction. No composite 'fundamental winner' is inferred from one favourable number.

A reported actual versus a pre-announcement analyst estimate is a surprise; actual growth versus last year is not a substitute. A current consensus snapshot is not evidence of what analysts expected before a historical release. A coarse guidance language classification is not a calibrated surprise magnitude. Changed quarter/year horizons, reporting-company coverage and non-GAAP definitions must remain visible.

Estimate revision comparison requires the same security, metric, fixed fiscal target, accounting basis, currency and share basis. For equal-weight analyst means, split the overall change into mean revision among common analysts and the remaining composition component. Example: old analysts A=2,B=4; new B=4,C=6. The mean increases from 3 to 5, but the only common analyst did not revise. A FY2027-to-FY2028 target roll-forward is rejected as a revision comparison. Negative EPS estimates are valid; percentage-change or P/E formulas requiring positive earnings are not forced onto them.

The positive-EPS identity price = EPS * P/E demonstrates that growth can coexist with a price fall: +30% EPS and -40% multiple gives -22% price. This is arithmetic, not an attribution of the BROS decline or a claim that a multiple reset is unjustified. Expectations, financing, dilution and valuation evidence remain explicitly unverified until actually recovered.

## 7. Availability and revision clocks

Distinguish source-as-of research from a replay of what Mastermind actually served. Both require an effective observation and source availability no later than the decision; served replay additionally requires actual system readiness no later than the decision. A June quarter released in August is not June-known data. Data available at 11 a.m. cannot silently support that morning's opening trade.

The reference selects versions of ONE supplied observation family. It does not merge competing vendors or decide authority. Later ingestion cannot resolve conflicting values carrying the same source/effective clocks; return that conflict to the existing source owner. A future correction cannot alter an earlier as-of view. Timezone-aware clocks are mandatory. Production event mapping uses the existing exchange calendar/session owner, including daylight-saving and holidays; a universal fixed UTC cutoff is not a new clock authority.

Operating period, last source update and market-close cutoff should all be visible, rather than reducing heterogeneous planes to one apparently fresh timestamp. Where historical publication or ingestion times are not known, label the limitation and prohibit claims about an actually executable historical route.

## 8. Terminal economics: clarification before stock execution

`ORDER_TRANSITION_TRIAL_V1.md` remains frozen and unexecuted. This is a pre-execution numerical clarification of its existing complete-outcome obligation, not a tuned model amendment: compute genuinely future ranks from simple economic holding returns, retaining a verified total loss as -100%. For positive terminal wealth, simple and log returns give identical ordering. At zero terminal wealth, log return is unavailable but the known outcome remains rank-eligible and receives the appropriate lowest tied rank. Never use a generic finite-log filter to delete total losses.

An unknown terminal value remains unknown; an imputed bankruptcy value cannot wear observed status. A bankruptcy filing is not proof of instantaneous zero equity value. Source owners supply terminal consideration, cancellation and event dates. Competing-event timing and recovery labels remain as defined in the original trial. New assumptions about post-settlement cash reinvestment or unresolved distributions require an explicit economic-accounting policy before results; no price carry-forward is silently substituted.

## 9. Existing integration, not a parallel system

Existing contracts recovered at Macro `1177cf84ffa46fa3e049ebe785aa1b391e42102d` include `engine/group_earnings.py`, schema `group_earnings_pulse.v1`, context-only. It already separates results, guidance, revisions, drift and sympathy; carries per-block counts; and refuses to substitute actual EPS without consensus for an EPS-surprise statistic. Its latest revisions snapshot and limited earnings history do not by themselves qualify a deep point-in-time panel. Its symmetry/co-movement output is descriptive, not causal. This is source evidence, not fresh live consumer proof.

Use that existing earnings owner, the Data OS identity/price/temporal owners, the existing `brain.analogues.v1` context reader, the single regime reader and existing research/evaluation lineage. The user-facing projection may extend their accepted contracts through ordinary owner review, but must not create a parallel feature database, graph, queue, forecast authority, watcher or trade-sizing route. Input-evidence request #7858 records the remaining stock-panel dependency without dispatching a worker.

## 10. Executable specification and acceptance evidence

Committed references and tests:
- `measurement_semantics_v2.py`, Git blob `b1732bcea9700d2a8411d349f6cb3db63e33be67`.
- `test_measurement_semantics_v2.py`, Git blob `9e3e5190af31a6c2e2dc37d75b68fbf60fc2c97a`.
- `context_semantics_v1.py`, Git blob `06904ed96698eed51a6489b4529d77fe3e28d22b`.
- `test_context_semantics_v1.py`, Git blob `cc2929c6fd696150df660dc85f1dc061db7a710c`.

All four published blob identities were read back and matched the exact locally executed files at source commit `866837c0048c8598ce8052109ef497345353218e`. Run from this research directory:

  python -m unittest -v test_measurement_semantics_v2 test_context_semantics_v1

47 tests passed, including 1,000 random count decompositions, 1,000 random weighted decompositions, 1,000 common-benchmark ranking checks, all eight completions of one missing-data fixture, time/revision conflicts, analyst composition, fiscal rollover and known-zero versus unknown outcomes. This is not global repository CI, an independent outside audit, model calibration, raw-data qualification or production/browser proof. No empirical signal threshold was fitted by these tests.

For the later product acceptance, a real qualified input must reach the real existing consumer and visible UI. Required demonstrations include BROS price/business divergence, KRUS rebound versus wider decline, stale/unknown data, denominator changes, a total loss, an alias change, and an unaccepted forecast remaining unavailable. English/Chinese and light/dark states must preserve units and uncertainty. Tests of reference arithmetic do not satisfy that production obligation.
