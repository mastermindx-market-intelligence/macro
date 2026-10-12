# Crypto science R3 — source identity, observable cohorts and episode evidence

Date: 2026-09-28. Parent: WS:CRYPTO-INTELLIGENCE / Macro Draft PR #8050. Frozen plan: `953eedfa53a5a201efebc03b74853316cad6a2cf`; tested source/study candidate: `cc5f0a2d16311db7639aba5f8f54ef6772a30374`; baseline: `40ab75b261fba57b4357e1c7ffb38ddd62f62871`. No live allocation, alert, falsifier gate or deployment changed.

## Decision-ready result

R3 makes input identity stable and creates a nullable observation view inside the existing radar owner, without changing the default signals consumed by live alert/decision paths. It then measures the three existing impulse hypotheses on comparable source-observed periods, under assumed reporting delays and nonoverlapping signal episodes.

The main finding is not a new high-accuracy strategy. Much of the apparent sample size in the recent bounce signal comes from repeated trigger days: 14 trigger rows become eight separated onset episodes, and only one meets the unchanged +5% next-three-close objective at zero assumed delay. The DVOL downside hypothesis has more episodes, but its favorable count declines sharply when action is delayed. These results establish exactly what the next predictor needs to improve; they do not rehabilitate previously unqualified legs.

## 1. Funding: fix identity, do not fabricate history

### Confirmed pipeline mechanism

The provider collector maps a single-value response to `funding_rate`, but prefixes multi-value response fields as `funding_rate_fundingRate` and `funding_rate_markPrice`. The old generic input selector chooses the first physical column. Reordering columns could therefore turn a mark price into a funding rate without changing the requested dataset name.

The candidate adds a narrow `_funding()` selector in `engine/btc_inputs.py`, used only by the funding key in `load_all()`. It selects exactly the current `funding_rate_fundingRate` field, preserves finite signed values and valid zero, and returns unavailable when that field is absent or duplicated. It does not fall back to markPrice or legacy values, splice history, rescale units or modify generic `_col()` behavior for other sources. It has been tested against shuffled columns, legacy-only inputs, missing/duplicated fields, numeric strings, infinities and nulls.

The current stored rate series is exactly equal before/after the selector change. It contains 80 non-null raw values; the legacy field contains 1,089. There is only **one overlapping observation**, and the two values are equal there. One equality is insufficient evidence that every historical observation has the same units, venue coverage, settlement period, daily aggregation or revision behavior.

### Public-source qualification result

The provider's current public landing page links Scalar API documentation. Its HTML in turn identifies `https://api.bitcoin-data.com/v3/api-docs`. The inspected static OpenAPI document (version 0.1; SHA-256 `5b79637596b021d69f06849f9ff9fbfa71d6d4e179f38805f7b66a87e0b7396c`) gives `/v1/funding-rate` a generic object response; it does not describe the required field semantics. The provider's explanatory funding page says intervals are usually eight hours but can differ by exchange. It is not a source-specific settlement contract for the two historical fields.

**Disposition:** funding-history restoration remains HOLD. The existing downstream eight-hour annualization is still an unqualified assumption; it was not silently replaced or declared correct. Field-order protection is completed in the source candidate, but semantic equivalence and historical publication timing are not. No metric endpoint, paid source, account, API key or collector was invoked. Exact public references are listed at the end.

## 2. An observed non-signal is not a missing measurement

`btc_impulse_radar.fire_series()` now accepts an optional `preserve_unknown=True` research view. It uses the same condition builders, thresholds and input stores. The default remains the original ordinary booleans used by current live callers; a full-frame comparison with the pinned baseline confirms exact default-output parity.

The opt-in result distinguishes True, observed False, and unknown. D2 requires the full daily DVOL lookback for its current/previous z-scores. D3/U1 require the full daily SOPR lookback and six positive finite daily price observations for their five-day return. A missing calendar day is not replaced with the next surviving row; nonfinite values or zero-variance z-scores do not become observations. Missing source families remain all-unknown without hiding independent families.

This is **source-observed**, not **publication-time-qualified**. The parquet timestamp and non-null value do not prove that the value had been released or ingested at that moment. The code documents that limitation and does not claim point-in-time provider vintages.

| Full stored-history cohort | R2 mature outcomes, ordinary booleans | Mature outcomes and source-observed inputs |
| --- | ---: | ---: |
| D2 DVOL range shock | 4,390 eligible days | 1,949 eligible days |
| D3 SOPR profit-taking spike | 4,390 | 4,381 |
| U1 SOPR capitulation | 4,390 | 4,381 |

The separate D2 observation mask contains 1,952 known dates before excluding immature outcomes, and 2,441 unknown dates. The old denominator included many dates without a usable DVOL signal history. Correcting the comparator changes the full-sample D2 base event rate from 16.10% to 13.24%, while its trigger-day hit frequency stays 17.21%. The descriptive lift therefore changes from 1.069 to 1.300 **without one additional correct forecast**. This is a denominator correction, not improved predictive ability.

In reused 2024+ the DVOL source is available throughout the mature comparison period, so D2's 997 eligible days and 61 trigger rows do not change. SOPR-based cohorts lose four eligible days, from 997 to 993. All valid, observed conditions agree with the old boolean values. No new gate class was assigned; existing validate(), compute(), alert behavior and gate persistence remain unchanged.

## 3. Repeated trigger rows overstate the number of distinct opportunities

The plan fixed an episode rule before the new outcomes: accept an observed False-to-True onset, then select the earliest subsequent onset strictly more than three calendar days after the previous selected onset. This prevents overlap of the existing three-day outcome windows. A positive state first seen after missing coverage is not assumed to be a fresh onset. Selection does not inspect future labels.

This is a controlled episode definition, not proof that the episodes are statistically independent. A separate fixed seven-day spacing check is retained; it was not chosen after comparing results.

### Source-observed, zero assumed release delay, reused 2024+

| Existing hypothesis | Trigger rows | Separated onset episodes | Episodes meeting the target | Episode fraction | Missed-target episodes per 30 eligible days |
| --- | ---: | ---: | ---: | ---: | ---: |
| D2: DVOL shock precedes a downside move | 61 | 35 | 8 | 22.9% | 0.81 |
| D3: SOPR profit spike precedes downside | 31 | 18 | 2 | 11.1% | 0.48 |
| U1: SOPR capitulation precedes recovery | 14 | 8 | 1 | 12.5% | 0.21 |

The target remains a close at least 5% below/above the reference within the next three daily closes. A missed target does not necessarily mean an unprofitable trade, and a hit does not prove an attainable exit or net profitable policy. No transaction simulation was performed in R3. The false-episode rate uses 30 eligible observation days, not a promise of a fixed monthly alert rate.

Fixed 30-calendar-day block bootstrap, seed 20260928 and 1,000 replicates, gives approximate95% episode-hit ranges of 7.4–40.0% for D2, 0–27.3% for D3 and0–50.0% for U1. These are retrospective resampling intervals under one blocking convention, not calibrated next-signal probabilities. The recovery interval is particularly uninformative because there are so few episodes. Intervals are withheld when fewer than two blocks contain episodes.

With seven-day spacing the counts become D2: 7/27, D3: 1/16 and U1: 1/7. The broad conclusion does not depend on presenting the most favorable of the two episode spacings. Neither spacing supplies a fresh holdout; 2024+ has already been used in prior research.

## 4. Timing sensitivity: a useful warning must survive plausible information delay

The study delays the completed condition and its observation mask together by exactly one or two calendar days, then grades the unchanged next-three-close target from that delayed decision date. It does not move the feature backward or pretend a known release delay. These are sensitivity assumptions, not measured historical provider latencies.

| Hypothesis | Zero-delay episode hits | One-day assumed delay | Two-day assumed delay |
| --- | ---: | ---: | ---: |
| D2 | 8/35 (22.9%) | 6/35 (17.1%) | 3/35 (8.6%) |
| D3 | 2/18 (11.1%) | 1/18 (5.6%) | 2/18 (11.1%) |
| U1 | 1/8 (12.5%) | 3/8 (37.5%) | 2/8 (25.0%) |

D2's trigger-day descriptive lift falls from 1.850 at zero delay to 1.234 with one day and 0.925 with two. This makes actual release and action timing a critical dependency for interpreting its historical edge. It does not imply the source actually takes two days to arrive.

U1's apparently better one-day result is **not** a newly selected trading rule. Three successes among eight episodes, with an approximate bootstrap range of 0–80%, is too fragile to justify picking the best delay. It motivates testing an explicitly defined stabilization/reclaim sequence on a separately frozen protocol rather than buying an oversold reading or mechanically waiting one day.

The study retains all 48 cohort/period/lag/separation summaries and 2,090 scenario-episode records. That latter count includes the same underlying episode across scenarios; it is not 2,090 independent observations. No outcome combination, delay or minimum sample was optimized to produce a pass.

## 5. What is implemented, what is diagnostic, and what remains held

**Implemented in the draft source candidate:** exact funding-field selection; opt-in nullable source observations; default compatibility; synthetic tests for gaps, nonfinite data, invalid timestamps, prefix/future perturbation and cold starts.

**Completed diagnostic:** pinned old-versus-current default-fire parity; current funding-value parity; source-observed mature cohorts; assumed calendar-delay scenarios; onset spacing; fixed block-resampling uncertainty; all input/source/gate hash checks.

**Unchanged:** trading rules, thresholds, current signal defaults, model weights, canonical allocation, portfolio policy, evaluator gate/status floors, alert ownership, stored market data and existing gate artifacts. No validate()/write_gate()/collector or deployed publication call ran in the study. The existing mature label and `_lift` implementations were reused. We did not use the old circular-shift permutation as a new acceptance test: it compresses missing dates before shifting, which is unsuitable evidence of calendar-time dependence preservation in the newly gapped cohorts. The planned block-resampling intervals are diagnostics only; no new p-value-based promotion was made.

**Held:** equivalence of legacy/current funding, funding settlement-time metadata, historical source release/vintage qualification, independent code/science review, production release and any claim of a new high-accuracy model. Default live gates are deliberately not switched to the opt-in cohort view before those policy/review requirements are settled.

Local verification before the study: 247 tests passed in the existing VectorCI pytest command plus all Crypto suites; 25 warnings remain. Test logs preserve actual RED failures followed by GREEN behavior. The study completed with exit 0 and retained matching hashes for 4 market-input files, 5 existing gate/ledger artifacts and 6 source/config files. Current engine source/study candidate is `cc5f0a2d16311db7639aba5f8f54ef6772a30374`; complete current verification and artifact digests accompany this report.

## 6. Next model experiment: test a sequence, not a single oversold/crowded reading

The next substantive research should compare a fast downside-warning baseline and an explicit post-washout recovery sequence against these corrected incumbents. R3 provides motivation, not frozen thresholds for that next experiment.

For downside, separate pre-move warning from continuation detection after damage has begun. Start with transparent completed-price/volatility structure and add actual spot/taker-flow evidence only where it exists. A raw-price-only baseline can use the long history; the true-flow extension must retain its shorter history and distinct source/venue coverage. Do not concatenate synthetic candle-signed flow with real aggressor data to claim a long history.

For recovery, require a separately defined stabilization/reclaim condition after the washout and test it against false rebounds. Predeclare event barriers, issue time, execution delay, endpoint convention, overlapping-episode handling and the risk-matched incumbent before reading outcomes. The eight recent U1 episodes are not enough to optimize those choices.

A model must show useful protection/participation after realistic delays and costs, not merely a better relative lift or more independent-looking indicators. Release decisions remain with the existing BitcoinDecisionState and policy owners. The broader Crypto/Vector mission remains incomplete.

## Public primary documentation consulted

- https://bitcoin-data.com/ — official provider landing page and link to API documentation.
- https://api.bitcoin-data.com/scalar.html — official documentation shell; points to `/v3/api-docs`.
- https://api.bitcoin-data.com/v3/api-docs — inspected static schema, version 0.1; generic funding response, not a historical field-unit contract.
- https://charts.bgeometrics.com/funding_rate.html — provider explanation; funding interval may vary by exchange. General explanation does not establish the interval of a particular stored field.

No external page is treated as proof of private account entitlements, historical data equivalence or predictive accuracy.
