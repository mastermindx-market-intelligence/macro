# T14 preregistration DRAFT — leader damage and the index pullback

**Status:** DRAFT. The seat freezes this file later. This document is not a registration, not a result, and not authority to fit a model.

**Lane:** GD-W7-T14PRE. Seat `da1ad7ad`. Workstream `WS:GREY-DEER-RISK-INTELLIGENCE`. Program MAS-258.

**Date:** 2026-10-13.

**Question.** Does damage to market leadership, known at the session close of origin `t`, change the probability or the depth of a 5-, 10-, or 21-session pullback in SPY, and does the same pre-declared statement hold for QQQ?

**Outcome-blind attestation.** This draft computes, looks up, and quotes no statistic that links a leader, breadth, crowding, concentration, or surprise feature to a pullback outcome. No hit rate, skill score, return-after-signal, or base rate is stated. Files whose names match `research/grey_deer/*RESULTS*` were not opened. Their names appear only in the known-exposure list. The local price store was not read. History starts below are code constants, instrument listing dates, or explicit statements that the span was not measured.

---

## 1. Frozen target and horizons

The label is the frozen target in `research/grey_deer/PULLBACK_PREREGISTRATION_V1_1_2026-10-12.md` §4. For cohort ticker `i`, origin session `t`, close `P_i,t`, and horizon `h ∈ {5, 10, 21}` sessions:

`A_i(t, h) = max(0, 1 − min(P_i,{t+1}, …, P_i,{t+h}) / P_i,t)`

The minimum runs over the next `h` sessions of that cohort's own session axis, using that cohort's own closes. No other ticker's price enters the label.

- **Event.** `Y_i(t, h) = 1` when `A_i(t, h) ≥ 0.05`. Otherwise `Y_i(t, h) = 0` when the label is mature.
- **Depth.** `A_i(t, h)` itself, at `τ ∈ {0.5, 0.8, 0.9}`. The gate uses `τ = 0.8`. The other two levels are counted sensitivities.
- **Maturity.** Origin `t` is mature for `h` when session `t+h` lies on the cohort's session axis inside the sample window. An immature label is absent. It is never filled with zero.
- **Basis.** Closes are the same adjusted closes the frozen protocol names in §4 (split adjustment as in that protocol's D14; dividends left unadjusted). A close can drop on an ex-dividend date. That inflation of measured loss is inherited and is not "corrected" here.
- **`D_total` and P-active.** Left uncomputed. v1.1 §5 leaves P-active blocked while `lib/pullback_observation.py` `observe()` (`close_path.v1`) is off main. This draft does not copy that observer and does not open a P-active population.

Horizons stay `{5, 10, 21}`. No other horizon is a claim.

This draft applies that label to SPY and to QQQ. It does not reopen the v1.1 fourteen-name panel, and it does not revise the v1.1 SPY verdict. A result here is a new family.

## 2. Cohort

| Role | Ticker | What the label uses |
|---|---|---|
| Primary | SPY | SPY's own closes. The common-factor control is SPY's own drawdown and realized volatility. |
| Pre-declared replication | QQQ | QQQ's own closes. The common-factor control is QQQ's own drawdown and realized volatility. |

QQQ is one replication, declared before any fit. It is not a second search after a SPY result. SPY and QQQ claims are charged separately in the trial budget. Their episode calendars overlap, so the two cohorts are not treated as independent evidence and are not pooled into a third claim.

No other index, sector ETF, or single stock is a cohort in this family.

## 3. Sample

The sample is the table emitted by `scripts/research/grey_deer_episode_samples.py` (the T12 builder, in progress on another lane).

On this base, that path is absent (`scripts/research/` listing, 2026-10-13). This draft does not invent a substitute episode rule and does not choose a seed.

**Freeze before any fit.**

- `T12_SEED`: unbound.
- `T12_TABLE_SHA256`: unbound. This is the sha256 of the emitted episode table the execution will read.

A fit, a feature join, or a label build that runs before both values are written into the frozen revision of this preregistration is killed. This draft does not fill either value.

**Row grain the execution requires.** One origin per cohort per session. If the frozen T12 table uses another grain, the run stops (`BLOCKED / SAMPLE_GRAIN`). Block length is not rescaled to make a shorter table fit.

**Provisional calendar, subordinate to the frozen T12 table.** NYSE sessions of the cohort from 2021-07-06 through 2026-10-07, the v1.1 window. The pinned exclusion `2026-08-18` is dropped when that date is present, before any label is built. When the frozen T12 table's dates differ, the frozen table is the sample. This paragraph does not extend it.

**Warmth and abstention.** An origin enters a feature's fit only when that feature is finite on data timed at or before `t`, using the full lookback named for the feature. A short window that a library function would still fill is an abstention in this protocol. Missing values are not imputed. A non-finite control feature (`dd63` or `log rv20`) abstains the origin for every incremental claim.

Labels are built at execution from §4 above. This draft does not build them.

## 4. Hypotheses

Each direction is stated for every horizon `h ∈ {5, 10, 21}`. "Raises" means a higher `P(Y = 1)` and a higher conditional quantile of `A`. The claim that can pass is the increment over the common-factor control in §6, not a raw association.

### 4.1 Eligible, inside the trial family

**H1. Narrowing.** A lower 20-session change in the RSP/SPY close ratio (feature F1) raises the SPY pullback probability and depth. The same direction is the QQQ replication, with QQQ's own label and QQQ's own control.

**H2. Mega-cap complex damage.** A lower 20-session change in the XLK/RSP close ratio (feature F2) raises the SPY pullback probability and depth. The same direction is the QQQ replication.

**H3. Leader-line break.** A larger 126-session gap of the QQQ/SPY relative-strength line below its own trailing high (feature F3) raises the SPY pullback probability and depth. The same direction is the QQQ replication.

H1–H3 are the only hypotheses the execution may fit.

### 4.2 Direction recorded, estimation forbidden

These directions are written down so a later repair cannot flip them. They are not in the trial budget. Fitting one of them under this family is a kill.

**HB1. Breadth deterioration.** A lower share of names above the 200-session average, and a lower high-low balance (new highs minus new lows), raises pullback probability and depth. The producers in §5.2 rebuild that share from today's constituents. Ineligible until a point-in-time membership history replaces that universe. A repaired series is a new preregistration.

**HB2. Named-cohort leader drawdown.** A higher share of a tracked mega-cap or AI-hardware cohort sitting well below its own trailing high, or a larger count of those names below their own 50-session average while the index is still near its high, raises pullback probability and depth. The producers in §5.2 take today's basket membership and apply it on past dates. Ineligible. `engine/basket_membership_pit.py` is a China-suite store (file header, line 1) and does not repair the US baskets.

**HB3. Negative surprise at leaders.** A negative earnings surprise at leaders, known at the public announcement clock, raises the 5-session pullback probability, and raises it by at least as much as it raises the 21-session probability. The consensus-surprise store and the SUE panel in §5.2 fail the clock or the survivorship rule. Ineligible.

**HB4. Crowded-winner liquidation.** A leader set that is extended and crowded, then breaks, raises pullback probability and depth. The crowding producers in §5.2 use a latest short-interest snapshot, live basket members, or a prospective ledger that starts on 2026-07-24. Ineligible for the retrospective sample.

## 5. Feature census

Every row is a producer that exists in this tree. "Clock" is the latest information the producer is allowed to use for an origin at session `t`. "History start" is a code constant or a listing date. The price store was not opened, so a listing date is not a measured cache span.

### 5.1 Eligible features

Eligible means the object is a traded fund's own close. The fund's holdings at each date are inside that close. The feature does not rebuild a past index from today's member list.

| Id | Feature | Producer | Inputs and clock | Survivorship | History start |
|---|---|---|---|---|---|
| F1 | RSP/SPY 20-session ratio change. The 60-session change is the named sensitivity, not a second hypothesis. | `engine/index_leadership.py:210` `ratio_read`; mom windows at `:221`. Pair declared at `scripts/build_index_leadership.py:57`. Closes loaded at `scripts/build_index_leadership.py:171` `_etf_close`. | Daily closes of RSP and SPY. Clock: both session closes at `t`. Evaluation truncates both series to sessions on or before `t`, then reads the same mom field. `ratio_read` itself returns the latest point of whatever series it is given, so the execution passes the truncated series. | **Eligible.** Traded ratio. | `ratio_read` returns no read until the aligned ratio has at least 70 sessions (`:216`). RSP listed 2003-04-24; SPY listed 1993-01-22. The later listing binds. Local cache span not measured. |
| F2 | XLK/RSP 20-session ratio change. The 60-session change is the named sensitivity. | Same `ratio_read` at `engine/index_leadership.py:210`. Pair at `scripts/build_index_leadership.py:69`. | Daily closes of XLK and RSP. Same truncation clock as F1. | **Eligible.** Traded ratio. | Same 70-session floor. XLK listed 1998-12-16; RSP listed 2003-04-24. RSP binds. Local cache span not measured. |
| F3 | Percent gap of the QQQ/SPY relative-strength line below its own trailing high. Lookback 126 sessions, full window required. | `engine/leader_lifecycle.py:846` `rs_line_gap_pct`. Lookback constant `RS_LINE_GAP_HIGH_LOOKBACK = 126` at `:206`. The ratio series is `rs_series` at `:307`. | Daily closes of QQQ and SPY through `t`. The function's own minimum is `lookback // 2` (`:859`). This protocol abstains until 126 finite sessions exist. A half-window value is not used. | **Eligible.** One traded fund versus SPY. | QQQ listed 1999-03-10; SPY listed 1993-01-22. The 126-session warm-up binds inside the sample window. Local cache span not measured. |

The execution records F1 and F2 as a ratio change (the mom field), and F3 as a percent gap. It does not substitute a level, a percentile, or an "above the 200-session average" flag. Those other fields exist on `ratio_read` (`:225`–`:232`) and are outside the family.

**Eligible producers deliberately left out of the family.** Adding one after a result is a new preregistration.

| Producer | Clock | Survivorship | Why it is outside the family |
|---|---|---|---|
| `scripts/build_index_leadership.py:61` IWM/SPY and `:65` IWF/IWD, via the same `ratio_read` | EOD closes through `t` | Eligible traded ratios | Size and style tilts. They are not the leader-damage hypotheses in §4.1. |
| `engine/rs_leader_highs.py:107` `observe_rs_highs` | Completed daily close and completed NYSE week, both cut at `as_of` (`:32`–`:36`, `:168`) | Eligible when both series are traded funds. The function does not choose a stock universe. | Boolean new-high of the same QQQ/SPY ratio. A second transform of F3. |
| `engine/leader_lifecycle.py:364` `rs_line_new_high` | EOD closes through the end of the supplied series | Eligible on a traded pair. Caller-dependent otherwise. | The chip is "RS at a high while price is below its high", a breakout lead. It is not a damage state. |

### 5.2 Ineligible features

A feature that uses today's constituents on past dates is ineligible. Repair means a new point-in-time universe, then a new preregistration. Relabeling the current series does not repair it.

| Feature | Producer | Inputs and clock | Survivorship | History start |
|---|---|---|---|---|
| Share above the 50- and 200-session average; new highs; new lows; advances; declines | `collectors/breadth.py:293` `constituents`; `:621` `compute`. Windows from `config.yml:2321` (`lookback_days_live: 1100`), `:2322` (`ma_windows: [50, 200]`), `:2323` (`nhnl_window: 252`). | Member daily closes. Clock: session close, after the collector writes the aggregate. | **Ineligible.** Constituents are the current Wikipedia S&P 500 table (`collectors/breadth.py:1`–`:4`). The same pattern is the S&P 400 and S&P 600 blocks at `config.yml:2367` and `:2376`. | Configured live window is 1100 days. `engine/advanced_breadth.py:26`–`:30` describes a deeper series rebuilt from today's members, thin before about 1990. That deep span was not measured (`data/` is not in this worktree). |
| McClellan oscillator, Zweig thrust, high-low index, advance/decline divergence | `engine/advanced_breadth.py:62` `mcclellan`; `:99` `breadth_thrust`; `:146` `high_low_index`; `:178` `divergence` | The breadth aggregates above. Clock: those aggregates' session close. | **Ineligible.** Same current-member rebuild. The module states the caveat at `:26`–`:30`. | No start of its own. It consumes the aggregate. |
| AI versus non-AI breadth split | `engine/breadth_split.py:128` `compute_breadth_split`; percent-above at `:95` | `data/breadth/_closes_cache.parquet` (`:143`) plus the current AI tag (`:165`). Clock: EOD closes in that cache. | **Ineligible.** Cache columns are the current breadth universe. The tag is today's tag. | Young-cache floor is 252 rows (`:57`). Underlying collector window is 1100 days. |
| Broad/narrow verdict from the breadth tape | `engine/basket_score.py:470` `market_concentration` | Latest rows of `breadth.parquet` (`:477`). Clock: the aggregate's last session. | **Ineligible.** The parquet is the current-constituent aggregate. | Same aggregate as the breadth collector. |
| Intraday breadth scoreboard | `engine/live_breadth.py:81` `evaluate_usable`. Tier map at `:50`. | One intraday full-market snapshot joined to nightly thresholds. Source-age gate defaults to 25 minutes (`:42`). | **Ineligible** for a retrospective sample. The universe default is the current S&P Composite 1500 (`:40`). The module stores no historical snapshot. | No history. Each poll is a fresh snapshot. |
| Leadership-crack velocity, carnage share, INTACT/CRACKING/BROKEN | `engine/leadership_crack.py:96` `_live_members`; velocity at `:168`; carnage window constant `:64` | Current members' basket OHLCV closes and the SPY close (`:86`, `:139`). Clock: EOD close. Members with `removed is None` (`:109`). | **Ineligible.** Today's basket membership is applied across the close history. | No start constant in the producer. Member-file span was not measured. |
| Mega-cap names below their 50-session average ("stealth leaders") | `engine/froth_fragility.py:878` `_stealth_leaders`, called with `_live_members` at `:884`. Live-member read at `:190`. Cohort key `mag7` at `:63`. | Current `mag7` members' closes, truncated at `asof` by `:220` `_close_at`. Clock: EOD, given `asof`. | **Ineligible.** `_live_members` keeps current members. Truncation at `asof` does not repair membership. | Call asks for 60 rows (`:884`). File span not measured. |
| Leader-radar state, including CROWDED and the narrow-leadership regime | Universe in `scripts/build_leader_radar.py:6`–`:10`. Dow-30 pin dated 2026-07-11 at `:73`. Regime classifier `engine/leader_lifecycle.py:750` `leadership_regime`. | Nightly EOD state on that universe. `leadership_regime` does not load membership; it classifies caller-supplied `pct_above_200` and `top5_share_21d`. Those inputs inherit the breadth cache when that cache is the source. | **Ineligible** as a cross-section. The universe is a current basket union plus a Dow pin applied backward. | State rows accrue from the builder's nightly append (`:14`, `:27`–`:33`). That append is not a 2021 point-in-time panel. One analyst chip's store is described as born 2026-07-16 (`:29`). |
| Cross-sectional RS percentile and the per-name LEADER / PULLBACK state | `engine/us_leader_pullback.py:230` `rs_excess_percentile`; `:346` `evaluate` | EOD closes. The percentile is point-in-time only for the panel the caller passes (`:70`–`:72`, `:236`). | **Ineligible** on the shipped breadth-cache panel, which is today's constituents. A point-in-time panel would still be a different question: this organ labels the name's own reset, not the index pullback in §1. It stays out of this family. | `MIN_HISTORY_BARS = 260` at `:179`. RS lookback 126 at `:132`. |
| Standardized unexpected earnings (seasonal EPS change, not consensus) | `engine/sue.py:62` `sue_cross_section`. Panel built at `collectors/edgar_eps.py:190` `build_eps_panel`. Filing-date overlay at `:174` and `:241`–`:243`. | `asof_date` is the 10-Q or 10-K filing date when that date is on or after `period_end`; otherwise `period_end` plus `quarterly_lag_days` (default 60, `:206`). Forms that count are 10-Q and 10-K (`:43`). The 8-K earnings release is excluded. `sue_cross_section` keeps quarters with `asof_date <= asof` (`:68`). | **Ineligible** as a leader cross-section. The universe is the current S&P 1500 breadth-cache tickers (`collectors/edgar_eps.py:194`, `:207`). A name that left the index is absent. A name that joined is present for its older filings. | `start_year` default 2008 (`:190`). |
| Consensus EPS surprise percent | `collectors/equity_earnings.py:184` `_surprises`. Attachment clock in `engine/group_earnings.py:60`–`:62` and parse at `:350`. | The stored `dateReported` has no time of day. The group reader treats it as after the close unless a same-name 8-K lands inside the match window, in which case the 8-K time wins. | **Ineligible** for the 2021–2026 sample. The collector keeps a current snapshot of the last four quarters (`collectors/equity_earnings.py:8`–`:9`), stamped at collection time. It is not a point-in-time archive of what was known on each origin. | Trailing four quarters in the current store. |
| Fragile / crowded-and-shorted flag | `engine/crowding.py:94` `compute_fragility`. Thresholds at `:39`–`:42`. | Latest cross-section of the close panel and the latest FINRA short-interest snapshot (`:83`, `:112`). The module states that the short-interest leg has no point-in-time history (`:21`–`:22`). | **Ineligible.** Latest snapshot, and the close panel is the current S&P 1500 board the function reads. | RS window constant 252 (`:42`). No historical short-interest panel in this producer. |
| Theme crowding composite (co-movement, RS stretch, extension) | `engine/theme_crowding.py:45` `_mean_pairwise_corr` and the composite described at `:7`–`:18` | EOD returns of live members (`:13`). Short interest is context only (`:17`). | **Ineligible.** Live members on past dates. | Z-score window described as the basket's own trailing history, about three years (`:5`). Short-interest leg has no history in this module. |
| Ownership days-to-exit | `engine/ownership_crowding.py:56` `adv_shares` | FINRA average-volume row, skipped when its settlement date is after `as_of` (`:60`–`:61`); else 30-session mean volume through `as_of`. | **Ineligible** for this family. The primary file is a latest short-interest snapshot. The 13F mark is a quarter-end proxy (`:26`–`:29`), not an EOD leader-price state. | No daily leader panel from 2021 is built here. |
| Prospective correlation-one hazard | `engine/personality_crowding_hazard.py:25` `CONSTRUCTION_ID`. Start date `engine/personality_followon_common.py:16` `NOT_BEFORE_SESSION`. | Session accrual on or after that date. | **Ineligible** for a sample that runs through the v1.1 window. The ledger starts 2026-07-24. | 2026-07-24. |
| Cross-sectional dispersion and average correlation | `engine/dispersion.py:162` `assess` | Caller-supplied daily-return panel. Trailing 63 sessions for the correlation proxy (`:174`); the function returns the latest state of the panel it is given. | **Ineligible** when the panel is the current-constituent close cache. The word "point-in-time" in the module header (`:13`) refers to the trailing window. It is not a membership guarantee. Outside this family even on a repaired panel: it is a selection-sizing dial, not one of H1–H3. | Needs 60 rows and 20 names (`:166`). |
| Subsector breadth thrust and cross-tab leadership score | `engine/index_leadership.py:82` `breadth_thrust`; `:169` `cross_tab_leadership` | Closes of the tab's subsector baskets (`scripts/build_index_leadership.py:40`–`:51`). Clock: EOD. | **Ineligible.** Basket membership is the current group list, not a point-in-time member set. | Thrust needs a 50-session average (`:82`). |
| Options-flow leader boards | `engine/flow_leaders.py:650` `board_a_legs` | Options-tape rows the caller supplies. | **Outside this family.** The producer does not define an equity leader universe or a price-leadership damage state. Survivorship of the tape's name list is not established in the module. | Not pinned in the module header. |

## 6. Common-factor control and baselines

Leader damage has to add information beyond the cohort index's own drawdown and volatility. Beating a weaker baseline is not a pass.

Definitions are the ones already named in v1.1 §6, evaluated on the cohort's own closes at or before `t`:

- `dd63`: one minus the close divided by the maximum of the 63 closes ending at `t`.
- `log rv20`: log of `engine.vol_forecast.realized_vol(close, 20)`.
- `sma_gap21`: close divided by the 21-session average, minus one.

| Id | Role | Specification |
|---|---|---|
| B0 | Unconditional baseline. Reported. Not a gate. | The v1.1 B0 construction on the pooled purged training origins of that block: `(k + 0.5) / (n + 1)`, one probability for every test origin in the block. |
| B1 | Volatility baseline. Reported. Not a gate. | L2 logistic on `log rv20`. This is the volatility-matched baseline. |
| B2 | Trend baseline. Reported. Not a gate. | L2 logistic on `sma_gap21`. |
| M0 | Common-factor control. The nested model every claim is scored against. | L2 logistic, for the event, on `dd63` and `log rv20`. Quantile regression on the same two features for the depth claims. |
| M1 | Incremental model. One leader feature at a time. | M0 plus exactly one of F1, F2, F3. Features are not entered together. A joint model is a different claim and is outside the budget. |

For SPY claims, `dd63` and `log rv20` are SPY's. For QQQ claims, they are QQQ's. The leader feature is not replaced by the control, and the control is not dropped in a second specification.

**Score that can pass.** Binary gate: Brier skill of M1 minus Brier skill of M0, on the same test origins. Depth gate: pinball skill at `τ = 0.8` of M1 minus pinball skill of M0. Skill uses M0 as the reference forecast. A positive increment is the direction required by §4.1.

Log loss of M1 versus M0 is reported beside Brier skill. It is not a second way to pass. When the two proper scores disagree in sign, the claim dies.

Skill against B0, B1, or B2 is reported in the same table and cannot replace a failed increment over M0.

## 7. Estimation, uncertainty, leave-one-episode-out

Origins stay in date order. The split is a walk-forward on that sequence.

- Block length 126 origins. Minimum final block 63 origins. First test block starts only after at least 315 training origins exist before the purge. These are the v1.1 fold constants applied to this origin sequence.
- Purge: drop a training origin whose label span `[t, t+h]` overlaps the test block, and drop the 21 origins immediately before the test block (`EPISODE_PRE` from v1.1 §6).
- When the frozen sample cannot fill the first test block, the run stops (`BLOCKED / FOLDS_EMPTY`). The block is not shortened.

**Episodes.** Event origins are those with `Y = 1`. On a single cohort, event origins merge into one episode when the gap between them is at most `h` sessions. The episode window runs from 21 sessions before the first event origin through `h` sessions after the last. This is the v1.1 §7 rule on one ticker. This draft does not count episodes and does not state an expected count.

**Uncertainty.** Episode-clustered bootstrap of the incremental skill. The episode is the resampling unit. A 90% interval is reported. The interval is not a second gate and is not searched across confidence levels.

**Leave-one-episode-out.** Each episode is removed once, M0 and M1 are refit on the remaining origins, and the incremental skill is recomputed. A claim passes the stability check only when every leave-one-episode-out increment has the same sign as the full-sample increment. A sign change kills that claim.

**Halves.** The frozen origin dates are cut once, at their median date. Each half is scored separately. The two halves must agree in sign with each other and with the full sample. The cut is the median. It is not a searched date. This draft does not compute the median.

No shuffled k-fold. No random origin split. No pooling of SPY with QQQ.

## 8. Multiplicity

**Trial family.** `grey_deer_t14_leader_damage`.

**Basis.** Itemized. The science budget is 51. A fit that issues a specification outside this list is outside the family and kills the run.

| Block | What is counted | Count |
|---|---|---|
| SPY gate, binary | 3 horizons × 3 features (F1, F2, F3) × Brier skill versus M0 | 9 |
| SPY gate, depth | 3 horizons × 3 features × pinball skill at `τ = 0.8` versus M0 | 9 |
| QQQ replication, binary | 3 horizons × 3 features × Brier skill versus M0 | 9 |
| Sensitivity, slower ratio | SPY only, F1 and F2, 60-session mom, binary skill versus M0, 3 horizons | 6 |
| Sensitivity, other pinball levels | SPY only, 3 features × 3 horizons × `{τ = 0.5, τ = 0.9}` | 18 |
| **Family budget** | | **51** |

QQQ has no depth gate and no sensitivity block. Those would be new claims.

B0, B1, B2, the log-loss companion, the bootstrap interval, the leave-one-episode-out path, the half-sample split, and the negative controls are mandatory reports. They are not extra passes and they are not spare looks.

HB1–HB4 are not in the 51.

## 9. Promotion

Display only, until a gauntlet that this draft does not run and does not declare passed.

A pass in this family may be shown as a research read. It ranks nothing, gates nothing, sizes nothing, and escalates nothing. It does not enter an allocation, a risk-radar threshold, or a trading rule. Promotion past display requires a later preregistration written after this one is frozen and executed. This document is not that gauntlet.

## 10. Negative controls

Both controls are reported. A control that prints a positive incremental skill does not move a gate and does not get a new shift, a new seed, or a new feature to make it flat.

1. **Label shift.** Inside each training block, stack the training origins by date and apply a circular shift of half the training length to `Y` and to `A`, the same construction as v1.1 §12. Refit M0 and M1. The expected incremental Brier skill and the expected incremental pinball skill are at or below zero.
2. **Noise feature.** Replace the leader feature with a noise series drawn from `T12_SEED` once that seed is frozen, matching the real feature's missingness mask. Draw identity is the family name, the horizon, and the feature id. Expected incremental skill is at or below zero. Until `T12_SEED` is frozen, this control is unspecified and the run waits. This draft does not pick a second seed.

## 11. Kill criteria

Any one of these ends the affected claim. A killed claim stays in the report. It is not refit under a new transform.

1. Incremental Brier skill of M1 over M0 is zero or negative.
2. For a SPY depth claim, incremental pinball skill at `τ = 0.8` is zero or negative.
3. Brier skill and log loss disagree in sign.
4. Leave-one-episode-out changes the sign of the increment.
5. The two median-date halves disagree in sign, or either half disagrees with the full sample.
6. An ineligible feature from §5.2 is entered as if it were F1, F2, or F3.
7. A fit starts before `T12_SEED` and `T12_TABLE_SHA256` are frozen in the registered revision.
8. A missing feature or a missing control is imputed.
9. A close after `t`, a filing dated after `t`, or a constituent list as of a date after `t` enters a feature.
10. The T12 table's row grain is not one origin per cohort-session, or the folds are empty under the constants in §7.
11. A threshold, a horizon, a τ, a feature transform, or a cohort is chosen after an outcome from this family has been seen. The remedy is a new preregistration.
12. Skill against B0, B1, or B2 is reported as the result when the increment over M0 fails.

A SPY failure is a SPY failure. The QQQ replication is still reported. It is not a replacement primary.

## 12. Known exposure

Research and study files that already carried these mechanisms onto outcomes. Names only. Contents of `*RESULTS*` files were not opened. Nothing in those files is quoted here.

- `research/grey_deer/gd1/GD1_RESULTS_AND_ADJUDICATION.md`
- `research/grey_deer/gd1c/GD1C_RESULTS_AND_ADJUDICATION.md`
- `research/grey_deer/commissions/GD-1C_LEADERSHIP_CRACK_DESIGN_ERA_COMMISSION_2026-08-19.md`
- `research/prophet_us_audit/LEADER_PULLBACK_REPLAY_2026-08-08.md`
- `research/prophet_us_audit/LEADER_PULLBACK_REPLAY_2026-08-08.json`
- `research/prophet_us_audit/leader_pullback_replay.py`
- `research/prophet_us_audit/leader_reset_study.py`
- `research/prophet/cpu_leadership/ENTRY_RS_THRESHOLD_FINDINGS_2026-09-21.md`
- `research/prophet/cpu_leadership/entry_rs_threshold_study.py`
- `research/prophet/cpu_leadership/entry_rs_threshold_inference.py`
- `research/INTRADAY_LARGE_CAP_TECH_LEADER_PHASE0_RESULTS.md`
- `research/EXIT_CROWDING_L4_INTERIM.md`
- `research/REGIME_RELIABILITY_FACTOR_CROWDING_ADJUDICATION.md`
- `research/release_forecast/SURPRISE_ANATOMY_1998_2026.md`
- `research/live_entry_radar/rs_pullback_launch/RS_PULLBACK_LAUNCH_RESEARCH_2026-10-06.md`
- `research/DATA_SIGNAL_EXPANSION_2026.md`
- `scripts/research/intraday_large_cap_tech_leader_study.py`
- `scripts/research/leader_recovery_policy_study.py`
- `scripts/research/leader_recovery_census.py`
- `scripts/research/pead_sue_pit.py`
- `scripts/fund_crowding_phase0.py`
- `scripts/thematic_rotation_phase0.py`
- `scripts/grade_breadth_divergence.py`
- `scripts/validate_sue.py`
- `scripts/sue_insider_deep_phase0.py`
- `scripts/pead_freshness_phase0.py`
- `engine/leader_recovery_outcomes.py`

The stage-1 pullback artifacts `research/grey_deer/PULLBACK_STAGE1_RESULTS_2026-10-11.md`, `research/grey_deer/PULLBACK_STAGE1_RESULTS_2026-10-11.json`, and the `research/grey_deer/pullback_stage1_r1/` pair of the same names exist. They were not opened. They are the frozen protocol's own outcome files for a different feature set (the index's own price, trend, and volatility). They are not counted above as studies of leader damage.

## 13. What this draft leaves undone

- It does not freeze itself. The seat freezes the draft later.
- It does not set `T12_SEED` or `T12_TABLE_SHA256`.
- It does not fit M0 or M1, and it does not build `A` or `Y`.
- It does not repair the ineligible producers. A repair is a new file and a new preregistration.
- It does not add an execution runner. The owned path of this lane is this document.
