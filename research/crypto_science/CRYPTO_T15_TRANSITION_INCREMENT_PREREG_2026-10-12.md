# Crypto T15 — transition detection, advance prediction, response value

Date 2026-10-12. Lane `claude/cx-t15p-20261012`. Existing WS:CRYPTO-INTELLIGENCE. Carrier is draft PR #8050, head `fd8095012e91`, merge-base `7150f29a765387f1c14fbae086314af6e0d6bddc`. This file is a preregistration. It records no new outcome. No backtest, collector, or study module was executed to produce it. Every R9 figure below is a quotation from the committed results document, not a recomputation.

R9 texts are absent from this worktree. The candidate-base apply covered `collectors/`, `engine/`, `scripts/build_crypto.py`, `scripts/build_vector.py`, `templates/crypto.html.j2`, `templates/vector.html.j2`, and `tests/` only. Citations of the form `fd8095012e91:<path>:<line>` are `git show` line numbers of that blob.

Three jobs stay separate. Transition detection is the timestamp at which a frozen first-passage label has already printed. Advance prediction is an R9 warning whose issue and action reference both sit strictly before break availability. Response value is the frozen cash-versus-incumbent account at a named action reference. A row may sit in only one of the first two jobs. Response value is computed for a named reference and is never converted into a recall numerator.

## 1. R9 baseline, restated

Abbreviations used below, all at commit `fd8095012e91`: `RESULTS` = `research/CRYPTO_SCIENCE_R9_PREBREAK_RESULTS_2026-09-29.md`; `PREREG` = `research/CRYPTO_SCIENCE_R9_PREBREAK_PREREG_2026-09-29.md`; `r9_prebreak_study.py` and `r4_sequence_study.py` under `research/crypto_science/`. Constants recorded by the R9 run (`r9_prebreak_study.py:251`): clock 6h, pre-break lookback 24h, threshold 0.10, horizon 24h, lower −0.05, upper +0.03, minimum training 1000 / 30 positive / 300 negative, recent-rate half-life 365 days.

### 1.1 Target

The target is a future 24h price path from the assumed action-opening price: a 5% decline before a 3% rise (`RESULTS:13`, `PREREG:21`). The primary target is that price path from the watch's own action reference. It is not proof that a 72h break will precede the path (`PREREG:23`).

Ordering uses the original R4 rule: an opening gap decides when the open itself is through a barrier; a same-bar high/low that crosses both barriers with unknown order is ambiguous; a complete path that hits neither barrier is a completed negative; a missing or incomplete window is unknown (`RESULTS:13`, `PREREG:21`). The label needs the terminal open. It does not use the terminal candle's later high, low, or close (`RESULTS:13`, `PREREG:21`). Stored opens are idealized reference prices. They do not prove a crash-time fill or a publication latency (`RESULTS:13`, `PREREG:21`).

`outcome` maps `lower_first` to y=1, `upper_first` or `neither` to y=0, and every other category to y missing (`r9_prebreak_study.py:42-45`).

### 1.2 Clock

The study enumerates every 00/06/12/18 UTC clock in the existing hourly source range (`RESULTS:9`). A watch is pre-break only when every prior 24 completed hourly D0 states are known and none is true (`RESULTS:9`, `r9_prebreak_study.py:34-36`). Recent breakdowns stay in the file as excluded-from-watch rows. Missing history is unknown. It is not evidence of safety (`RESULTS:9`). Price and known-target features require the original 721-hour continuity (`RESULTS:9`, `PREREG:17`, `r9_prebreak_study.py:23`). No clock is kept because a future event happens, and none is removed because nothing happens (`RESULTS:9`).

The fixed study contains 31,372 clock/lag rows (15,686 unique clocks under the 1h and 6h delays), 70 quarter fits, 25,526 issued-period candidate rows, and 1,176 catalogue event/lag rows (588 unique D0 onsets) (`RESULTS:35`). For primary 1h forecasts from 2018 onward, 12,763 clock rows divide into 8,879 forecast-qualified, 2,507 recent-break, 1,130 price-history-unknown, and 247 past-context-unknown (`RESULTS:37`). Among qualified forecasts, 8,838 have mature unambiguous targets and 41 are unscored. There are 828 positive overlapping clock targets (9.37%). Those overlapping rows are not 828 distinct damaging D0 events (`RESULTS:37`).

### 1.3 Negative economics

At the primary 1h delay and 10bp one-way costs, 1,109 price warnings have complete paired account paths. 237 begin with the incumbent already in cash. 910 produce an economically nonzero difference. The hypothetical cash policy removes 49 marked-drawdown cases that exceed 5% in this selected sample. Mean net return versus following the incumbent is −0.1419 percentage points per warning, block interval [−0.2702, −0.0194] pp. Mean reduction in excess drawdown is +0.1123 pp. Mean utility is −0.0296 pp, interval [−0.1422, +0.0909] (`RESULTS:109-111`).

On the recent 228 accounts, 61 start in cash and 175 differ economically. Cash removes 11 incumbent marked-loss cases above 5% and costs −0.2222 pp mean return, interval [−0.3990, −0.0447], and −0.1505 pp mean utility, interval [−0.3458, +0.0428] (`RESULTS:113`). The same issued stream marked at other fees (`RESULTS:117-121`):

| Price-warning cash policy, primary 1h | Full mean return / utility, pp | Recent mean return / utility, pp |
| --- | ---: | ---: |
| 0bp | −0.0560 / +0.0562 | −0.1353 / −0.0636 |
| 10bp | −0.1419 / −0.0296 | −0.2222 / −0.1505 |
| 25bp | −0.2706 / −0.1582 | −0.3524 / −0.2806 |

All 6h-delay results keep a negative mean return. At 10bp the full mean return/utility are −0.1562 / −0.0579 pp and the recent figures are −0.2532 / −0.1857 pp (`RESULTS:123`). The rate-only stream's full mean return is −0.1376 pp and utility −0.0442 pp on 1,213 complete accounts. Those warning times differ from the price model, so the two mean utilities are not a paired increment (`RESULTS:125`).

R9's ruling on this table: no live warning and no protective-allocation promotion (`RESULTS:129`). There is no evidence in that table for an emergency allocation veto (`RESULTS:113`). Per-warning accounts reset equity and are not an annualized portfolio (`RESULTS:123`, `PREREG:53`).

### 1.4 Consumed-history limits

The price model reuses the eight R8 contemporaneous price and known-target measurements. It does not use signed flow, order-book absorption, or a new causal source. No calibration and no threshold sweep is inside R9 (`RESULTS:11`). The repeated, already-used historical data and the unverified source-publication assumptions prevent a fresh predictive-skill acceptance claim (`RESULTS:48`). The study limitations string says the same thing: all history was repeatedly inspected; there is no untouched holdout and no live policy change (`r9_prebreak_study.py:256`).

The full-period paired Brier difference, price minus recent-rate, is −0.003210, interval [−0.005411, −0.001303] (`RESULTS:48`). On the reused 2024+ slice the paired Brier difference is +0.000461, interval [−0.001204, +0.002030]: ranking can still look better while probability loss does not improve (`RESULTS:61`). The recent era does not reproduce the full-period proper-score gain (`RESULTS:129`). The minimum training counts cannot be relaxed after results (`RESULTS:11`, `PREREG:27`). The study process ran once; no outcome, threshold, feature, or label was amended afterward (`RESULTS:143`).

Forward-issued evidence, exact live publication, rights, and execution qualification, and independent review remain open before any promotion (`RESULTS:137`, `RESULTS:160`, `PREREG:63`). Hourly source timestamps and opens do not prove publication or execution parity (`r9_prebreak_study.py:255`).

## 2. Five metrics, kept distinct

These five are different objects. An own-window hit is not a catalogue match. A match count is not a recall. Supported recall and all-event recall use the same numerator and different denominators. Alert burden counts non-events and issuance, and it is not a precision to advertise. R9 states the split directly: 156 own-window hits need not equal 20 strictly anticipatory D0 matches (`RESULTS:103`). Selectively reporting a supported-recall figure alone would mislead (`RESULTS:101`, `RESULTS:129`).

Published primary figures are the 1h price stream over the full issued period, with the reused 2024+ figure beside them. They are quotations.

| Metric | Definition frozen here | Quoted primary figure | Code that computed it | This worktree |
| --- | --- | --- | --- | --- |
| Own-window hit rate | Among issued warnings whose own y is 0 or 1, the fraction with y=1. y=1 only for `lower_first` on that warning's own entry. Ambiguous and censored y are outside the denominator. Results name this "observed own-window precision". | 156 / 1,109 = 14.07%. Unknown own outcomes: 5. Recent: 20 / 228 = 8.77% (`RESULTS:69-75`). | `alarm_counts` precision, `r9_prebreak_study.py:84-89`, labels from `outcome` `:42-45`. | Not computable today. |
| Strict catalogue matching | The one-to-one pair set. A warning matches a damaging event only when issue is inside the 24h before `break_issue`, `entry < break_issue`, and `confirm <= end`. One warning takes the earliest such event. One event is credited once. Leads are issue-to-break and action-to-break, measured to the observable break. | 20 pairs. Median issue lead 9h, median action lead 8h, issue-lead range 2–20h. Recent: 1 pair, issue lead 3h, action lead 2h (`RESULTS:85-89`, predicate `PREREG:43`). | `match_events`, `r9_prebreak_study.py:72-81`. | Not computable today. |
| Supported recall | Matched damaging events in the period, divided by damaging events that had at least one `forecast_status==ok` clock meeting the same lead and expiry predicate, whether or not a warning was issued. | 20 / 37 = 54.05%. Recent: 1 / 5 (`RESULTS:87-89`). | `supported_event_recall`, `r9_prebreak_study.py:148`, support flag `:224-229`. | Not computable today. |
| All-event recall | Matched damaging events divided by all mature `lower_first` catalogue events in the period. Unsupported events stay in the denominator. | 20 / 78 = 25.64%. Recent: 1 / 15 (`RESULTS:87-89`). Coverage split of the 78: 18 timing, 12 context, 11 feature history, 37 supported (`RESULTS:93-99`). | `all_event_recall`, `r9_prebreak_study.py:147`. | Not computable today. |
| Alert burden | Issued warnings after forecast ≥ 0.10 and cooldown until that warning's own `end`. Future labels do not shorten, extend, or erase it. False-window means y=0 (completed upper-first or neither). Unknown is not false. Exposure-adjusted rate uses eligible scored watch clocks × 6h / (24 × 30.4375). Raw above-threshold clocks are a separate count. | 4,557 above-threshold clocks, 1,114 issued, 953 completed own-window non-events, 13.13 false-window warnings per equivalent observed-watch month (72.59 equivalent months against 105 calendar months). Recent: 228 issued, 8.42 per equivalent month (24.69 against 33 calendar months) (`RESULTS:65-77`). Rate-only recent stream issues none; its precision is undefined (`RESULTS:79`, `alarm_counts` returns None when none are scored, `:88`). | `emit_warnings` `:62-69` and `alarm_counts` `:84-89`. | Not computable today. |

"Not computable today" means this worktree has no `research/crypto_science/r9_prebreak_study.py` and no `research/crypto_science/r4_sequence_study.py`. `engine/btc_impulse_radar.py:241` `compute` returns a display ladder (`:415-442`) and does not return these five fields. `engine/btc_impulse_radar_backtest.py:89-95` `_lift` is a fire-conditional rate divided by a base rate. Its label is an unordered daily extrema test: forward minimum over (t, t+3] ≤ −5%, or forward maximum ≥ +5% (`btc_impulse_radar_backtest.py:20-24`, `:58-86`). The same file states that a full horizon is required even after a partial window has crossed a barrier, so those cohorts do not depend on which outcome arrives first (`:66-67`). That lift is none of the five metrics. Substituting it for own-window hit rate, either recall, the match set, or alert burden is a protocol breach.

6h price figures, quoted so they are not silently merged into the primary row: 1,111 warnings, 1,104 scored, 144 own-window hits, 12 strict matches among 83 damaging events of which 33 are supported. Recent 6h: 220 warnings, 219 scored, 17 own-window hits, 0 strict matches among 19 damaging events of which 4 are supported (`RESULTS:105`). Delay changes reference prices, populations, and the eligible lead window (`RESULTS:105`).

## 3. Objects the question inherits, already frozen

### 3.1 First-passage ordering

`barrier_label` walks completed bars and stops at the first deciding bar (`fd8095012e91:research/crypto_science/r4_sequence_study.py:115-143`). The loop is `w.iloc[:-1]`, so the terminal bar's high, low, and close do not decide the category. Inside a bar the order is:

1. open at or through the lower barrier → `lower_first`
2. else open at or through the upper barrier → `upper_first`
3. else low through the lower barrier and high through the upper barrier → `ambiguous`
4. else low through the lower barrier → `lower_first`
5. else high through the upper barrier → `upper_first`
6. else the bar does not decide

If no bar decides, the category is `neither`. The reference price is the window's first open. The terminal return uses the terminal open (`r4_sequence_study.py:122`, `:141`). Event construction attaches this label at `entry = break_issue + lag`, with `break_issue = anchor + 1h` (`r9_prebreak_study.py:194-197`).

### 3.2 Unknown both-barrier candles

Category `ambiguous`. `outcome` sets y to missing (`r9_prebreak_study.py:44`). A both-barrier candle with unknown order is not a scored negative (`RESULTS:13`). Unknown is not a false-window (`PREREG:37`). The unit contract that encodes this is `tests/test_btc_impulse_falsifier.py:931-940` (`test_r9_unknown_and_ambiguous_targets_never_become_false_alarms`), which imports the study module. That import is not satisfiable in this worktree, so the assertion was not re-executed here. The contract text is the freeze.

Censored windows stay censored (`r4_sequence_study.py:119-121`). They are not filled with zero return.

### 3.3 Action-reference delay

Warning entry is issue plus lag hours. Lag 1h is primary. Lag 6h is sensitivity (`PREREG:21`, `r9_prebreak_study.py:190`). Matching requires `entry < break_issue` (`r9_prebreak_study.py:77`). For a damaging catalogue event, confirmation is the end of the deciding bar: `confirm = entry + (barrier_hour + 1) hours` when category is `lower_first`, otherwise confirmation is missing (`r9_prebreak_study.py:197`, `PREREG:41`). Because event entry is already `break_issue + lag` and `barrier_hour` is at least 0, `confirm` is strictly after `break_issue`.

### 3.4 Cost model

For a named entry with a complete 24h price path and a complete incumbent-target path, compare the corrected incumbent with a switch to cash at that entry, a 24h cash hold, and restoration of the incumbent's terminal target (`PREREG:51`, `warning_account` at `r9_prebreak_study.py:92-99`). Both paths start from the same incumbent exposure. Costs are 0, 10, and 25bp one-way, applied to the same issued set. Costs do not change which warnings exist (`RESULTS:115`, `PREREG:51`). Utility is return difference plus the reduction in `max(drawdown − 5%, 0)` (`r9_prebreak_study.py:97-99`, `PREREG:53`). The 5% figure is the inherited research objective. It is not user risk consent, a guaranteed stop, or account-specific advice (`RESULTS:23`, `PREREG:53`). A missing path returns `account_unavailable` (`r9_prebreak_study.py:94`). That status is unavailable. It is not a zero return. Block intervals stay on the already declared procedure: 90 calendar-day blocks, 1000 resamples, seed 20260928 (`PREREG:31`).

## 4. Candidate question, declared before outcomes

Identifier: **T15-Q1**. Status: declared. No cell in §4.4 has been filled. No sign pattern in a future table authorizes an alert, a size, or an allocation change.

### 4.1 The question

On the frozen R9 catalogue of mature `lower_first` events, using only prices and the inherited incumbent target path, what is the paired response-cost difference between acting at transition detection and acting at the already matched advance warning?

Detection reference, for each primary-lag event with category `lower_first` and a non-missing `confirm`: the action reference is `confirm` as defined in §3.3. The cash account is `warning_account` at that timestamp, same lag's incumbent map, same costs. This reference is after `break_issue`. It is transition detection. It is ineligible for `match_events`, for supported recall, for all-event recall, and for either lead statistic.

Advance reference: the existing R9 price-model warning account on the warning that `match_events` already paired to that event. Unmatched events have no advance account. One is not imputed. The 20 full-period pairs and the 1 recent pair stay the published match set (`RESULTS:85-89`).

The information increment is the paired difference, detection minus advance, of `dr` and of `du`, on the intersection of events where both accounts return status `ok`, at the primary cell (lag 1h, cost 10bp). Sensitivity cells are reported beside the primary cell and do not replace it.

This increment uses the frozen price path and the incumbent target series already required by `warning_account`. It adds no feature, no threshold, and no new catalogue. It does not refit `PRICE_LOGIT` or `RECENT_RATE`. It does not read `engine/btc_impulse_radar.py:241` or `engine/btc_impulse_radar_backtest.py:123`.

### 4.2 Why this is an increment and not a relabeling

R9 already measured advance-warning response value and recorded negative primary economics (§1.3). R9 also recorded that an observation after a first break is conditional management, and that a pre-break model is not rescued by moving its successes into post-break detection (`RESULTS:133`). T15-Q1 measures the response cost of the detection timestamp on its own row and leaves the advance match counts on their published figures. The advance predicate requires both `issue < break_issue` and `entry < break_issue` (`r9_prebreak_study.py:77`). The detection action reference is `confirm`, which §3.3 places after `break_issue`, so that row fails the advance predicate.

The question does not reproduce Grey Deer. Grey Deer is WS-GREY-DEER-RISK-INTELLIGENCE on `origin/main`: a separate program whose objective is one canonical risk envelope across Macro, Prophet, Terminal, and Mastermind Portfolio, with protection rules that affect actionability (`agentos/workstreams/WS-GREY-DEER-RISK-INTELLIGENCE.md:2-10`). Its owned paths include `research/grey_deer/` and `engine/risk_envelope.py` (`:18-20`). Its own rules forbid a universal fused risk score on scored or authority paths (`:56`) and forbid automatic held-position exits in v1 (`:60`, decisions `DEC:RISK-STATE-HAZARD-POLICY-SEPARATION` at `:35` and `DEC:AUTO-EXIT-NOT-IN-GREY-DEER-V1` at `:42`). T15-Q1 does not write those paths, does not fuse the impulse-radar ladder with an R9 probability into an actionability score, and does not arm an exit. The Vector impulse radar remains the display object already described at `engine/btc_impulse_radar.py:1` and `:439-442` (display-only, sizes nothing, no alert from this module). This preregistration does not change that object and does not attach it to a risk envelope.

### 4.3 Falsifier

Any one of the following falsifies T15-Q1. A falsified run is a breach record. It is not a result, and it is not mined for a friendlier cell.

1. A detection-reference row is counted in `matched_events`, `supported_event_recall`, `all_event_recall`, issue-to-break lead, or action-to-break lead. Those fields remain the quoted R9 counts in §2. A recomputation that changes 20/78, 20/37, 1/15, or 1/5 is a breach.
2. A row with action reference at or before `break_issue` is placed in the detection cohort, or a row with action reference after `break_issue` is added to the advance-match set.
3. An ambiguous both-barrier candle is scored as `lower_first`, as a false-window, or as a zero return. A censored window is scored as a zero return.
4. An `account_unavailable` path is filled with 0, dropped from the written record, or replaced by a nearby filled hour.
5. Any threshold, barrier, horizon, lag, cost, catalogue membership, or training minimum other than §1 is tried. The impulse-radar ladder cuts (`engine/btc_impulse_radar.py:65`, `:77-88`), act-leg floors (`engine/btc_impulse_radar_backtest.py:16-18`, `:51-55`), and ±5% / 3-day extrema label are a different instrument. They are not a search grid for T15-Q1.
6. The paired difference is promoted to an urgent alert, a live warning, a protective allocation, a trade size, an execution instruction, or a Grey Deer envelope input. No sign pattern, including a positive mean paired `du`, is that promotion.
7. The advance account is refit, the warning set is re-selected, or the cooldown is rewritten. Advance accounts are the published R9 rows for the already matched warnings.

A future run also fails closed when `research/crypto_science/r9_prebreak_study.py` is absent, because §2 records that the five metrics and `warning_account` are not computable in this worktree. Absence of the module is reported. It is not patched around with the impulse-radar lift.

### 4.4 Response-cost assessment template

Fill only in a later run that this preregistration does not authorize by itself. Every cell below is **unfilled**. A later missing path is written `unavailable`, never `0`. Primary cell is lag 1h, cost 10bp. Other rows are sensitivity and stay visible. `paired` means detection minus advance on the intersection only. Block interval uses the procedure in §3.4; if the paired series is empty the interval is `unavailable`.

The breach column must be 0. A non-zero breach column falsifies the run under §4.3.1 and freezes the rest of that row as a breach record.

| Cell | n both ok | n detection only | n advance only | n unavailable | mean dr detection | mean dr advance | mean paired dr | mean du detection | mean du advance | mean paired du | avoided-loss sum, detection | missed-rebound sum, detection | already-cash, detection | block interval, paired du | detection rows admitted to advance recall |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1h, 10bp, full (primary) | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled |
| 1h, 10bp, 2024+ | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled |
| 1h, 0bp, full | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled |
| 1h, 25bp, full | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled |
| 6h, 10bp, full | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled |
| 6h, 0bp, full | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled |
| 6h, 25bp, full | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled |
| 6h, 10bp, 2024+ | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled | unfilled |

Avoided-loss sum and missed-rebound sum use the R9 definitions on the detection accounts only: sum of positive `dr`, and the sign-flipped sum of negative `dr` (`r9_prebreak_study.py:164`). They are not netted into one number before they are written. Already-cash counts detection accounts whose initial exposure is 0 (`:162`).

Disposition rule for whatever those cells later contain: a null, an empty intersection, an interval that covers both signs, or a negative mean does not block display-tier work and does not confer authority. Promotion to authority needs its own accepted gate. This document is not that gate. The same consumed-history limit as §1.4 applies: T15-Q1 reuses the R9 events and the R9 warning accounts, so a filled table would still be retrospective on already inspected history.

## 5. Prohibitions

Unregistered threshold search is prohibited. The searchable surface is closed by the constants in §1 and the ordering, delay, and cost model in §3. A new threshold, a new barrier pair, a new horizon, a new lag, a new cost, a new catalogue cut, a calibration offset, or a quantile chosen after seeing T15-Q1 or R9 outcomes requires a new preregistration committed before those outcomes are computed. R9 already refused a threshold or calibration re-selection on its own outcomes (`RESULTS:61`, `RESULTS:137`). Repeating that search under this filename is the same prohibition.

Urgent alerts and financial promotion are prohibited without their own accepted gates. That covers a live warning, an urgent notification, a protective allocation, a trade size, an execution instruction, and an emergency veto. R9's disposition is no policy promotion and no high-confidence forecast promotion (`RESULTS:160`). The impulse radar's own note says it sizes nothing and emits no alert (`engine/btc_impulse_radar.py:43-44`, `:441-442`). Display of an already shipped ladder can remain display-tier. This preregistration does not promote it. Instrument verdicts are not market verdicts: a leg lift, a catalogue match, or a filled cell in §4.4 is not a statement that the bitcoin market will rise or fall.

`r9_prebreak_study.py:171` raises if `research/crypto_science/r9/results.json` already exists, and that `main` reads parquet under the data directory and writes the R9 output directory. This lane does not invoke it. A later lane does not invoke it in order to fill §4.4; filling §4.4 requires a separate, still-frozen evaluator that reads the published event and warning-account artifacts and does not refit.

## 6. Conditional boundary with T09

T09 flow and funding qualification is required only if an increment's features include signed flow, funding, open interest, order-book absorption, or dealer inventory. R9 names that dependency for those inputs: instrument, units, aggregation and settlement interval, observation time versus publication time, and venue coverage, with short supported flow history kept separate from the long price history, without splicing, without renaming unsigned spot volume as absorption, and without inferring dealer inventory (`RESULTS:135-136`).

T15-Q1 does not use those inputs. It uses the hourly open path inside `barrier_label` / `warning_account` and the inherited incumbent target path. It proceeds without T09. A later question that adds a flow or funding feature is a different question. That question waits for an accepted T09 qualification and gets its own preregistration. It is not filled into §4.4.

## 7. What this document does not contain

No new outcome, no filled template cell, no refit, no engine edit, no collector run, no alert copy, and no Grey Deer artifact. The up-gauge boolean at `engine/btc_impulse_radar.py:423` is outside T15-Q1. This document does not treat that field as scientific acceptance and does not change it.

Verification boundary: R9 arithmetic was not re-run. The quotations in §1 and §2 match the committed results prose at the cited lines. They were not checked against `research/crypto_science/r9/*.csv`, because that directory is not in this worktree and the mission forbids a new backtest. Independence of the original R9 verification remains what R9 itself recorded: same-session numerical re-expression, not a separate reviewer (`RESULTS:147`).
