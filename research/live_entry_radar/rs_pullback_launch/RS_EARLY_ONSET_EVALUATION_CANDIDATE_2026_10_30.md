# RS Leader Early-Onset: frozen candidate evaluation specification

**Scope:** WS:LIVE-ENTRY-RADAR, Macro #10225, task P3.3 of `RS_LEADERSHIP_SUITE_MASTERPLAN.md`. Written 2026-10-31 UTC. **SPEC_ONLY / NOT REGISTERED / NO MARKET OUTCOME READ.** This is a proposed source-bound submission to the incumbent Evaluation OS, not an independently admitted trial, score, signal, forecast, or source-qualification authority.

## 1. Question and falsifiable outcome

Can point-in-time relative-strength acceleration, downside resilience, and **independently qualified** peer breadth identify more *future* RS leaders earlier than a simple momentum/relative-strength baseline, under an identical daily attention budget, without an unacceptable increase in false starts, missingness, or risk? A positive chart anecdote, sample maximum, first-green candle, or follower self-reported return is not evidence.

The machine job is a daily known-at snapshot that offers research attention candidates. The user job is to find a developing theme or standalone leader with sufficient time to inspect entry accessibility. This protocol does **not** test entry triggers, fills or profitable trading. Those remain separate `P1/P5` comparisons under existing Radar/Evaluation OS protocols. If the experiment rejects predictive usefulness, descriptive RS, breadth and source-health annotations may still be useful.

Original relevant source contracts:
- `RS_LEADERSHIP_SUITE_MASTERPLAN.md`, §§3,4,6,8 and P3.1–P3.3;
- `RS_LEADERSHIP_GROUP_CONTEXT_CONTRACT.md`, exact owner fields, PIT/ex-issuer requirements and honest timeframe labels;
- the accepted GMI membership owner, native Data OS identity/price/source owners, and existing Evaluation OS science/admission. This document creates **no new owner**.
- The incumbent 14-chapter `leader_pivot_2026-10-08` study is preserved, not replaced.

## 2. Unit of observation and source clock

One observation is `(canonical_security_id, qualified_session, decision_cutoff, versioned_definition)`. A distinct optional group episode is `(canonical_group_id, membership_revision_as_known, session, cutoff)`. Never use ticker text as persistent security identity or count two share classes of one issuer as independent peer votes.

Before any trial, the existing source owner must certify each required field: supported rights and purpose, security/issuer identity, cash/split/dividend adjustment basis, opening/closing exchange calendar (DST and half days), complete price windows, original receive/first-known timestamps, correction lineage, PIT inclusion and delisting history, member effective-time **and knowledge-time**, source-health/coverage and corresponding known-at benchmark observations. The standing Chairman commercial-data-rights attestation settles licensing approval for the named feeds, **not** the above historical-vintage facts.

Freeze eligible stock universe and daily candidate origin from information actually visible by cutoff. Keep non-selected eligible stock rows for denominator and false-negative accounting. Labels/outcomes are never input fields. An item with mandatory identity, price, clock, basis or benchmark unsupported is `UNAVAILABLE`, not neutral or zero. A stock may remain eligible without any qualified theme, group or catalyst: group context is optional.

At present, Macro `PHASE1_ADMISSION_2026-10-07.json` says `NOT_ADMITTED`; newer source readers and pure computations are not a retroactive market-observation receipt. Do not execute or register this evaluation against substituted mutable latest snapshots or fabricate first-seen history. Prospectively acquired receipts may qualify only their future supported window.

## 3. Frozen comparison arms (all descriptive until accepted)

**B0: primitive context baseline.** Stock 20-completed-session total return, 20-session relative wealth vs qualified market benchmark, observed volatility, liquidity screen and distance from a supported prior-close/ATR reference, with fixed missingness and versioned eligibility. Rank at one declared cutoff under the same attention budget. A variant without coverage or required history abstains; do not make later winners retroactively eligible.

**A1: incremental acceleration/resilience block.** Add independently available relative-wealth observations over completed 1, 3, 5, 10, 20 and 63 sessions, slope/difference on explicitly reported matched windows, frequency/recency of RS highs and a downside-resilience annotation using only qualified down-benchmark sessions in a trailing 20-session window. Relative wealth for a common complete window is `(gross_stock / gross_benchmark) - 1`; a nonpositive, zero, unsupported or mismatched benchmark gross return refuses. Multiple overlapping windows are correlated features, **not independent confluence votes**. A count with insufficient down-market observations is `UNAVAILABLE`, not artificially positive resilience. Numerical feature transformations must be sealed before any labels are read.

**A2: qualified group breadth increment.** Apply the same A1 only when an accepted PIT group/issuer membership and eligible same-period benchmark/price measurements are available; append a separately named group support, change/dispersion and concentration context. Consumer never reinvents group identity, weights, breadth or 30m group bars. Current draft #10213 has actual 15m/60m/daily, **not 30m**; no relabelled synchronous 30m confirmation. Exclude the subject issuer through every asserted ex-self peer/parent contrast; inclusive ETF context remains explicitly inclusive. Report expected/eligible/observed members, missing contributors, effective support `(sum weights)^2/sum(weights^2)` and largest-member concentration. If coverage is incomplete, only qualified sample values and identified bounds are usable, never full-cohort means disguised as sample averages.

**A3 (separate secondary cohort only):** age/extension/accessibility annotation (distance to supported entry level in ATR units, trend age, first pullback since a known onset) for a *watchlist description*. It may not be tuned into A1/A2 after examining winners. Entry timing, execution and capital-risk scoring remain a distinct registered experiment; no trade trigger is generated here.

No LLM, narrative catalyst, topical similarity or retrospective group assignment can manufacture a numeric rank, group membership, source observation or probability. If optional narrative evidence is available, retain citation/known-at and explicit `UNKNOWN` semantics separately.

## 4. Outcomes and clean population accounting

**Primary proposed label:** Among stock episodes eligible for a full 252-session RS reference at the original cutoff, does a *subsequent*, genuinely knowable new 252-session RS-relative-wealth high occur within 10 completed sessions? Retain the original as-of high reference and use completed, appropriately known-at future observations only in the outcome owner. A signal already at the high is recorded separately from an episode that reaches a new high later; do not reward tautological same-day highs.

**Secondary proposed outcomes:** time-to-first future high, persistence (3 of the first 5 subsequent eligible daily observations remain above the frozen pre-event RS reference), 5/10-session relative-wealth change, downside/failed-onset frequency, and false-start rate per fixed number of displayed watchlist slots. Define censoring distinctly from true failure/loss and from a session that could never be observed. New/young listings lacking 252 days are **a declared separate short-history cohort**, not silently failed or winner-filtered.

Keep every eligible non-selected stock episode and attempted selection for missed-opportunity accounting; never compute a hit rate from only alerts or winners. Treat revisits as the same frozen episode until an explicit rearm/expiry rule is accepted. Group-level episodes are clustered and scored separately; overlapping themes do not become independent corroborating samples.

## 5. Fair decision budget and statistical gate

Proposed UI attention budgets, to freeze with the incumbent evaluation owner **before first label read**: at most 20 stock candidates and 5 groups per session, identical B0/A1/A2 budgets and baseline eligibility. Compare both precision-at-K **and** number of qualifying future events discovered; gains achieved by exploding the watchlist do not count. Also report median/quantile lead time, false alarms per 100 eligible episodes, abstention, uncovered universe weight, consumer wait/source age, trading-day and market-regime slices, and worst-case downmarket participation. No missingness-imputation winner filter.

Use chronological train/selection/calibration/untouched holdout with purging of overlapping label horizons and issuer/group/date clusters. Fix every attempted feature family, normalization, cohort definition, threshold and selection decision before holdout access. Report uncertainty clustered by session and issuer/group; perform a sensitivity check to alternative fixed baseline (primitive momentum/volatility) and stale-source stress. A study with an already inspected sample cannot be reused as a newly untouched holdout. Retain existing prior negative/weak studies in the comparison log.

**Proposed promotion margin, not yet approved:** A1 or A2 must improve held-out precision-at-K by at least 5 percentage points over B0 **and** give at least one additional supported session of median lead time with no material false-start/tail-loss deterioration, after appropriate multiple-comparison and uncertainty treatment. If sample size/power cannot support that claim, return `INCONCLUSIVE`; the bare count of 90 sessions is not power evidence. Double any later decision-cost assumptions when comparing executable opportunity; this protocol does not itself assert trade economics.

## 6. Falsifiers and abstention

Reject the incremental predictive claim when any of the following holds: naive momentum/volatility baseline matches it; time-to-new-high improvement disappears at true known-at latency; group effect disappears after ex-issuer removal; apparent acceleration is cohort shrinkage/revision; young-listing and delisted losers are absent; samples rely on future membership, frozen labels or unknown price basis; feature density increases false starts; claimed payoff depends on hindsight stops/fills; any required receipt becomes unsupported; or regime/cluster uncertainty overwhelms the marginal gain.

Keep outcome-specific dispositions `SUPPORTED`, `REJECTED`, `INCONCLUSIVE` and `NOT_TESTED` inside existing Evaluation OS. These are *research dispositions*, not detector registration or permission to publish alerts/trades. A qualified descriptive display may be advanced independently after product/source authority accepts it.

## 7. Submission and acceptance checklist

Before implementation or experiment enrollment: existing owner must sign off the exact daily cohort and source receipts, the B0/A1/A2 feature definitions and missingness, frozen labels, observation availability, attention budgets, split/purge, sample/power plan and prospective carry-forward. Then implement the smallest pure read projection and owner-native synthetic conformance tests. Discriminating tests must catch: future-known leader membership, future correction changing a past output, wrong basis/identity, incomplete 252-session history, comparison under unequal K, vanished-member acceleration, same-issuer peer leakage, missing group substituted by zero, intraday/daily timeframe masquerade, unsupported later catalyst and unauthorized ranking/issuance flags.

An accepted Evaluation OS registration and actual untouched-data/prospective proof are separate later receipts; no paper spec or synthetic test may impersonate them.

**Current delivery state:** this file freezes a proposed test design only. P2.1 market/source qualification and #10213/GMI group admission remain unresolved, P3.2 projection is not yet implemented, P3.3 is not registered. No data retrieval, label computation, backtest, discovery score, alert or live customer path is claimed.

## Source-inert feature consumer amendment (before label enrollment)

The pure daily measurement consumer at `engine/entry_radar/replay/rs_onset_features.py` now requires an as-of absolute `calendar.session_ends[ISO_date]` for every used session. Selected visible `stock` and `benchmark` rows must have `period_end` equal to the declared close and `period_end <= known_at <= decision_at`. This calendar is still caller-supplied and **not authenticated**; native calendar/source-owner evidence remains the P2.1 admission gate. Correctly labeled exceptional/offset closes are allowed; missing/wrong-session bars, not-yet-closed target days, future revisions, nonfinite numeric returns and unsupported metadata do not create rank or prediction permission. The consumer computes only descriptive 1/3/5/10/20/63-session relative wealth, adjacent-five-session change, and 20-session downside simple-excess median (minimum three benchmark-down observations). No empirical outcomes or trial enrollment have occurred. These engineering guards refine source eligibility and do not amend the proposed B0/A1/A2 comparison arms or their prespecified outcomes.
