# Independent trough-gating research: different declines need different evidence

Date: 2026-11-14. Status: RESEARCH ONLY. No validated trading edge, calibrated stock probability, production change, release, position sizing or trade authorization is claimed.

## Executive finding

Keep the original dot/T1-T3 timers. My independent working hypothesis is that the research is mixing several different economic situations under one 'bottom' label. A stock-specific overshoot inside a sound industry, an industry-wide repricing, a systemic panic rebound and continuing business impairment need not benefit from the same gates. A healthy home industry could help the first case, while a washed-out industry undergoing genuine repair could matter for the second. A universal count of favorable conditions can erase that distinction.

This is a hypothesis, not an empirical victory. I tested simple recipient repair, prior-leader rollover, volatility cooling and adverse-day resilience on public industry data rather than presuming them beneficial. None earned promotion as a validated gate. Two measurement findings were more decisive: an apparent safety gain disappeared under fixed risk units, and market-relative dispersion was shown not to be market-exposure-neutral dispersion.

The deliverable is reproducible falsification, a narrower causal/predictive question and a stock-level experiment contract that reuses the existing Mastermind estate. It is not another conclusion that dots are useless, and it is not another independent information engine.

## 1. What was actually tested

### A. Recipient repair and the other side of rotation

The preregistered pilot used French49 daily value-weighted industry portfolios, numerically filtered through 2002-12-31 before parsing later values. Candidate industries were at least10% below their trailing126-session total-return-index high and trailing the market over126 sessions. Decisions were at month-end, entry at the next session's close, outcome63 subsequent sessions, with assumed20bp round-trip cost. This is a mechanism screen, not a dot reconstruction or implementable portfolio backtest.

8,902 industry-month observations span790 distinct decision months, 1927-06 through2002-09. They are correlated and have overlapping horizons; neither the observation count nor the2,659 consecutive industry spells is an independent-market-episode count.

R: the recipient's latest21-session return is positive both absolutely and relative to market. D: the prior-winner industry tercile rolls over in recent relative returns, excluding the recipient. V: market21-session daily volatility falls below its63-session value.

| Comparison | Win rate | Any closing loss >=10% within63 sessions | Mean63-session net excess return |
|---|---:|---:|---:|
| R absent |57.00%|35.06%|-0.21%|
| R present |56.62%|35.05%|-0.20%|
| R present, D absent |58.41%|32.16%|+0.39%|
| R present, D present |54.58%|38.32%|-0.87%|

R selects18.6% of candidates. Its win-rate difference is -0.39 percentage points, descriptive95% interval[-4.72,3.62]; the bad-buy difference is effectively zero. D's adverse point estimates are uncertain and do not prove all rotation-source information is harmful. They do refute treating this exact proxy as already validated positive evidence. V's Bad10 difference withinR is -7.54points with interval[-17.28,1.72], insufficient for promotion.

The fixed12-calendar-month moving-block bootstrap used2,000 replicates and retained industries together by month. Intervals are exploratory and not multiplicity-adjusted. Era signs differ. Same-month matching on volatility and decline/recovery geometry does not show a clear incremental benefit. An extra-session execution-delay sensitivity does not reverse the broad null.

Full cells, intervals, era splits, matching and exclusions: [PILOT_RESULTS.md](PILOT_RESULTS.md). Original design: [PROTOCOL.md](PROTOCOL.md); executable: [pilot.py](pilot.py).

### B. Resilience on market down days

The adaptive follow-up asked whether a candidate performs better than its own previously estimated market sensitivity on adverse market days. Intercept and beta were frozen from252 sessions ending before the latest21-session evaluation window. This is not a fundamental stock-type classification.

Within repaired candidates, the resilience-positive subset had54.90% wins versus62.23% without that signal, and35.62% versus32.54% Bad10. The excess-return difference was -1.78points[-3.30,-0.22]. After same-month, same-R, six-feature matching, no clear protective effect appeared; only276 pairs across94 months and22.55% of treated observations remained comparable.

This exact resilience proxy did not pass. Do not invert it into a new trading signal or pick its favorable era. Residual strength does not establish that cash-flow damage has stopped. Full evidence: [FOLLOWUP_RESULTS.md](FOLLOWUP_RESULTS.md), [FOLLOWUP_PROTOCOL.md](FOLLOWUP_PROTOCOL.md), [resilience.py](resilience.py).

### C. Label normalization exposed a concrete apparent edge

R reduced volatility-scaled downside-first events from27.53% to22.78%. Taken alone, that looks helpful. But upside-first also fell from30.11% to25.02%, and unresolved events rose from42.36% to52.21%.

The descriptive audit found mean trailing volatility31.10% forR versus26.83% withoutR, while mean forward volatility was similar:26.60% versus26.23%. Consequently, the mean downside barrier was wider:16.01% versus13.96% below entry. With a common10% downside boundary and a common10% upside boundary, downside-first was32.33% versus32.11%: no apparent safety advantage. Fixed10% adverse-excursion risk was already unchanged in the registered result.

This is evidence that the apparent benefit depends on outcome units and barrier geometry, not proof of a complete causal explanation. It does NOT invalidate the separate proprietary dot/close-ATR low-hold result, which was not reproduced here. It specifies an audit that any confidence claim needs: actual-entry dollar/path risk alongside normalized labels and timeout.

Full diagnostic: [LABEL_AUDIT.md](LABEL_AUDIT.md); code: [label_audit.py](label_audit.py).

### D. 'High dispersion' is not synonymous with rotational opportunity

Subtracting one market return from every industry leaves dispersion unchanged:

    SD(R_industry - R_market) = SD(R_industry).

A broad market shock interacting with different betas can produce sector dispersion and defensive relative outperformance even when every industry falls. This is a mathematical counterexample to identifying rotation from relative dispersion alone; it is not a claim that every dispersed market is beta-driven.

A feature-only audit compared raw recent21-session industry dispersion with dispersion after subtracting a frozen intercept-and-beta market prediction. Each high-state threshold was its own prior120-month80th percentile, with no current/future value in the threshold. In788 eligible months from1937-05 through2002-12,38 of175 raw-high months (21.71%) were not adjusted-high;39 of176 adjusted-high months (22.16%) were not raw-high. The series were still strongly correlated (~0.90). Neither measure was tested here for future profitability.

For the regime layer, retain raw and exposure-adjusted dispersion as distinct measurements. At stock level, also distinguish between-industry from within-industry dispersion. Do not award independent positive votes for several algebraically overlapping transforms.

Details and exact variance identity: [DISPERSION_AUDIT.md](DISPERSION_AUDIT.md); code: [dispersion_audit.py](dispersion_audit.py).

## 2. The central research question: why did it fall, and is that pressure changing?

The following mechanism taxonomy is my proposed experimental partition, not a claim that price data uniquely identifies causes.

| Situation | Evidence worth testing | What should not be assumed |
|---|---|---|
| Firm-specific overshoot in a sound home industry | Industry-adjusted dislocation; comparable expectations not deteriorating proportionally; relevant peers stable; sufficiently liquid execution | The home industry must itself be washed out |
| Industry-wide repricing | Industry operating/expectation pressure changing; broad recipient participation; macro-exposure fit; stock-specific impairment absent or bounded | Old leaders weakening proves money is entering this industry |
| Systemic panic/rebound | Market stress trajectory, financing conditions, changing exposures, explicit short versus longer horizon outcomes | A powerful rebound establishes a durable business or sector bottom |
| Continuing issuer impairment | New guidance/credit/refinancing/earnings damage, issuer event risk and source uncertainty | An oscillator extreme makes all information risk temporary |

Published work supports researching these distinctions, not their exact gates or thresholds. Da, Liu and Schaumburg(2014) separate cash-flow-related changes from other return components and find different short-run reversal behavior. Moskowitz and Grinblatt(1999) document industry continuation. Daniel and Moskowitz(2016) analyze loser rebounds during stressed-market momentum crashes. These are different populations and horizons; their coexistence is a reason to test interactions rather than count universal favorable conditions.

The most useful synthesis is not 'add fundamentals as a veto.' It is **compare the size and timing of the repricing with the changing information that could justify it**. A negative revision can be already reflected in price; a seemingly stable consensus can be stale. Both must be observable states, not stories selected after a rebound.

A research decomposition can compare the observed decline with owner-produced market, industry and information-response components. The remainder includes model error, omitted news and measurement error. It is not mispricing by definition. The existing Information-to-Price design already owns this distinction; reuse it instead of building another residual engine.

## 3. DNA should change the conditional response, not create a private rulebook per ticker

Proposed slow-moving descriptors: operating/cash-flow durability, leverage and refinancing exposure, economic customer/input/currency sensitivity, historical market/factor response, liquidity and gap behavior. Proposed fast state: current expectations and their change, announcement/guidance context, event calendar, own/cohort price state and current macro pressure.

Use company observations with partial pooling toward relevant archetypes when evidence is thin. Do not fit a separate high-dimensional model for every ticker, and do not label a price-defined low-beta group 'fundamental quality' without data. A firm's economic peers, industry peers and return-correlation peers should remain different relationship types with dated validity.

Cohen and Frazzini(2008) motivate economic-link propagation as a research object. Dai etal.(2024) distinguish the speed/persistence of reversal across liquidity characteristics. Gu, Kelly and Xiu(2020) support investigating nonlinear interactions, while their emphasis on momentum/liquidity/volatility also cautions against assuming static accounting quality alone solves return prediction. None proves our trough classifier.

For the MCD example, ask what information changed between the first and second setup: economic peers, relative performance, revisions/guidance, macro exposure, stress and event risk. 'Second dot' is an event-order descriptor, not the answer. An early entry followed eventually by a lower low is not automatically a losing trade under every exit rule; the original intended horizon and executable path define the outcome. The 2026 anecdote was not used to validate this study.

## 4. Regime: stance, impulse and transmission are separate

The sign of nominal short rates minus trailing inflation is not a sufficient easy/tight-money label. It is a backward-looking realized-rate proxy. Policy stance relative to a changing neutral benchmark, the direction/surprise of the change, and its economic transmission differ. A simple illustrative arithmetic example:0%-2% and4%-8% both give negative backward-looking real rates, despite a4-point nominal tightening. Those are hypothetical values, not historical observations.

The Federal Reserve's neutral-rate discussion supports the stance distinction. Jarocinski and Karadi(2020) distinguish policy and information shocks using high-frequency announcement co-movement; their identification cannot simply be copied into monthly price signs.

For the next test, preserve continuous known-time descriptors of rates/expected inflation, credit and dollar conditions, market stress, and raw/exposure-adjusted dispersion. Let their effects interact with company exposures. Simple rule states are useful baselines; a Markov model must use filtered probabilities based only on past/current information, with its estimator trained on a past prefix. Future-smoothed labels cannot be decision features. More populated regime cells do not by themselves make a definition economically correct.

## 5. Exact next stock-level experiment contract

This is a proposed new, trough-specific evaluation through the existing owner. It does not amend K3E-EVAL-0 or the incumbent gate protocol, and no private stock outcome was read for it.

### Primary hypothesis

Among the original dated dot events, **the interaction between firm-specific dislocation, home-industry state and comparable expectation deterioration adds decision value beyond the same information used additively and beyond existing price/timing controls**.

This is deliberately narrower than 'all fundamentals help' or 'a second dot is better.' It also distinguishes predictive improvement from proof of a causal mechanism.

### Minimum columns and clock law

Use the existing event/security/episode IDs, original timer and T1 versions, completed-bar clocks, entry rules and outcome definitions. Join only evidence possessed or public before the decision under the relevant owner contract.

An illustrative expectation-drift column is the change in EPS consensus for the **same fiscal period and accounting/share basis** over21 sessions, normalized by a valid pre-window share price rather than near-zero EPS. Keep level, recent change, prior-window change, coverage, staleness and missingness separate. Do not compare a rolling '+1y' label across fiscal rolls or fabricate contributor identity. A slowing decline in expectations is a hypothesis to test, not an automatic green light.

Group features use dated membership and leave the focal stock out. Economic-peer features use relationships disclosed before the decision. Source-derived event/driver tags must cite their documents; a language model may extract facts, but its narrative confidence is not a calibrated trade probability. Historical extraction tests should guard against outcome knowledge, including recognizable company/date leakage.

### Four comparison arms, identical information and opportunity set

A. Unchanged original timer and accepted baselines.

B. Existing/simple additive gate baseline, with accepted stock-type and market controls.

C. Low-capacity, regularized interactions between dislocation type, expectation state, home-group state and stock exposures, with partial pooling. A residual or mechanism label does not count as extra independent evidence when it is a recombination of the same inputs. Compare against a baseline with equal underlying information and comparable capacity.

D. An executable wait policy: delay until a specified new confirmation arrives, otherwise remain unentered. Include episodes where confirmation never arrives and the missed successful early entries. Compare the policies from the same online-defined episode start and fixed episode horizon, and separately report fixed post-entry path quality. Do not select only episodes that eventually printed a second dot or retrospectively choose the final low.

Preserve the original close-ATR low-hold label, worst adverse move, return and same-swing T1 comparison. Add fixed/economically comparable loss diagnostics and upper-first/lower-first/timeout outcomes, not replacements selected after inspecting results. Intraday data, gaps, halts, delistings and action costs must use the existing market owner and explicit availability masks.

### What confidence must mean

For a specified entry, horizon H and predeclared target/loss boundaries, estimate three mutually exclusive probabilities:

    P(upside first by H), P(downside first by H), P(neither by H).

They sum to1 only under the stated complete-observation contract. Incomplete horizons are censored or excluded under a frozen rule, not labeled losses or timeouts by convenience. Separately estimate expected net payoff, catastrophic/gap risk and whether the original low holds. A high low-hold probability is not the same as a high profitable-trade probability.

The output should support BUY-NOW CANDIDATE, WAIT, REJECT-FOR-THIS-HORIZON and INSUFFICIENT-EVIDENCE research states, with no implied execution authority. Gate count is an explanatory diagnostic, not a percentage confidence. Sparse archetype/regime cells require wider uncertainty or abstention.

### Evaluation and falsifiers

Freeze the event/sample/schema and feature transforms before additional outcome reads. Existing2013-19 stock data is development only, not virgin confirmation. Preserve stock2020-May2023 and the incumbent industry's2003-19 confirmation reserve. Do not silently spend one team's holdout for another team's experiment.

Use chronological folds containing all names for a date, purge overlapping label windows and keep online episode identities intact. Calibrate using training/validation folds only. Report results at fixed opportunity-coverage levels such as20/40/60/80%, rather than choosing an acceptance threshold after seeing the best win rate. Include a simple filter accepting the same fraction, same-date controls, adverse-selection/missingness audits and block/episode dependence.

The primary hypothesis is not nominated if its incremental risk/utility disappears after capacity-matched controls, if it mainly selects quieter unresolved positions, if low coverage hides the lost winners, if success rests on one era/archetype, or if probabilities fail chronological calibration. Show absolute and relative returns, losses, time in capital, coverage and uncertainty together. Define minimum economically useful effects before confirmation; statistical significance alone does not authorize release.

## 6. Reuse and the observed source boundary

A targeted source read found that Mastermind already has `collectors/equity_revisions.py`, K3E, Information-to-Price, economic-relationship and evaluation owners. Their inspected records distinguish prospective source acceptance from historical/PIT economic eligibility. The architecture is not absent. This run did not qualify a long-history joined stock/non-price panel, so it did not fabricate one from current snapshots.

A public author stock-characteristic archive was probed by metadata and header only. It lacked an explicit return target in the inspected header, and exact transformations, delisting coverage and historical timing were not certified. No1.56GB bulk download, paid source request, public raw-data release or shifted-momentum surrogate target was used. Full source-state evidence and owner mappings are in [SOURCE_QUALIFICATION_AND_REUSE.md](SOURCE_QUALIFICATION_AND_REUSE.md).

The next input action is a metadata-only qualification of one immutable development-event/expectations/price join under existing owners, with coverage by year/type/group and no held-out outcome read. This is a data proof requirement, not an invented human approval or claim that all potential sources are unavailable.

## 7. Evidence and boundaries for recovery

Procedural pin: protected Mastermind master `199fd4f91ecc426b1d974eb3bf47f5162476cf24`; skillpack1.0.1. GitHub branch: `research/astra-transition-repair-20261114`, based on `b8bb39510769b778fbe3f45dd8c197855ebf028a`. Research return carrier: Macro#11014. Existing source-owner code inspected separately at `2469f810b4867875b3be59fef89e980e3f0d3231`.

The code was authored on GitHub and executed in operation-bound M2 SSD workspace `/Volumes/Mastermind 2/agent-workspaces/macro/web/astra-transition-repair-20261114`. Initial workspace uncertainty was reconciled to the original operation before use. No alternative carrier retried a denied or uncertain effect. No worker, watcher, PR, production change, source rewrite, holdout consumption or trading action was commissioned.

Executed tests include prefix invariance, missing-sentinel handling, units, unique event keys, barrier partitions,32 direct simple-return path checks,32 separate least-squares beta checks and dispersion identities. These are author self-checks, not independent peer review or a live acceptance receipt. Full local aggregate JSON hashes are preserved in each report; the Markdown result reports and executable code are durable on this branch. Raw vendor data is not committed.

**Do not redo** these exact pilots without an input/code issue or a new preregistered question. Preserve all nulls, adverse signs, sparse matching and measurement diagnostics. Do not relabel the adaptive follow-up as untouched validation. Do not infer 2026 MCD performance, the private dot's hold-rate advantage, calibrated stock win rates or production improvement from these industry tests.

Bounded outcome: independent research and reproducible diagnostics completed; return delivery/readback must be recorded separately. Parent outcome: a superior, validated stock/sector decision engine remains unproven. No work is claimed to continue asynchronously. The next genuinely different experiment requires a qualified stock-level non-price input join, not another unregistered sweep over price-only filters.

## Primary public references

- Da, Liu and Schaumburg(2014), *A Closer Look at the Short-Term Return Reversal*: https://academicweb.nd.edu/~zda/Reversal.pdf
- Moskowitz and Grinblatt(1999), *Do Industries Explain Momentum?*: https://www.aqr.com/Insights/Research/Journal-Article/Do-Industries-Explain-Momentum
- Daniel and Moskowitz(2016), *Momentum Crashes*: https://www.kentdaniel.net/papers/published/jfe_16.pdf
- Dai, Medhat, Novy-Marx and Rizova(2024), *Reversals and the Returns to Liquidity Provision*: https://rpc.cfainstitute.org/research/financial-analysts-journal/2024/reversals-and-the-returns-to-liquidity-provision
- Cohen and Frazzini(2008), *Economic Links and Predictable Returns*: https://pages.stern.nyu.edu/~afrazzin/pdf/Economic%20Links%20and%20Predictable%20Returns%20-%20Cohen%20and%20Frazzini.pdf
- Gu, Kelly and Xiu(2020), *Empirical Asset Pricing via Machine Learning*: https://dachxiu.chicagobooth.edu/download/ML.pdf
- Jarocinski and Karadi(2020), *Deconstructing Monetary Policy Surprises*: https://www.aeaweb.org/articles?id=10.1257/mac.20180090
- Federal Reserve, Brainard(2015), neutral-rate/stance discussion: https://www.federalreserve.gov/newsevents/speech/brainard20151201a.htm
- Kenneth French49-industry construction: https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/det_49_ind_port.html
