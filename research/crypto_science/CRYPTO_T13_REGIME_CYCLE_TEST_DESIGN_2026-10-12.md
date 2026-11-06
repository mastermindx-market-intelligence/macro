# T13 regime and cycle labels — look-ahead census and test design

Date: 2026-10-12. Lane `cx-t13p-20261012`. Census is the worktree after the
candidate-base commit (origin/main `3634a83542` plus #8050 R2 source). The four
modules below are not in the R2 source delta; they are main's copies.
`engine/cycles.py` is cited only where `engine/btc_mtf.py` returns its labels.

Qualification boundary, binding for every row below. These outputs may stay on
screen as descriptive context. They carry no probability claim, and this design
adds no fused class score (no blend of band, thesis status, confluence grade,
and market stance into one number or one authority class). A null or a missing
input stays unavailable (`n/a`, `Unavailable`, `ok: false`). It is never stored
as zero. Nothing here sizes, times, or authorizes a trade. Promotion of any
label onto an exposure or a gate is a separate gauntlet; `engine/btc_regime.py:10-15`
already keeps the macro band off the size path because it did not beat the
hand-tuned allocator out of sample.

Shipped config the thesis monitor reads (`config.yml:6042-6059`): halvings
`2012-11-28`, `2016-07-09`, `2020-05-11`, `2024-04-20`; bottoms `2015-01-14`,
`2018-12-15`, `2022-11-21`; tops `2017-12-16`, `2021-11-08`, `2025-10-06`;
template lengths `up_days: 1064`, `down_days: 364` (the comment on
`config.yml:6053` says that fit is in-sample, n=3).

## Label inventory

Clock means the timestamp the label claims to describe. Horizon means the
lookback or the template the code names, not a claim that the template will
be realized.

### `engine/btc_regime.py` — macro band (display only)

| Label | Values | Inputs | Clock | Horizon |
| --- | --- | --- | --- | --- |
| `band` | STRONG TAILWIND ≥75, TAILWIND ≥58, NEUTRAL ≥42, HEADWIND ≥25, STRONG HEADWIND below, else `n/a` (`268-279`) | Composite index. Factors in `FACTORS` (`104-117`): net_liq_roc, global_m2_yoy, real_yield, dxy, curve_score, fed_score, VIX and HY OAS, etf_flow_z, stbl_growth_z, close vs 200D/200W, mvrv_z. Fixed weights. Renormalized over live factors. Thin under 6 live factors (`40`, `169`) | `asof = df.index[-1]` (`247`). No `as_of` argument | Trailing. Z window 365d (`35`, `49-51`), slope 20d (`36`), trend 200d / 1400d (`37-38`, `74-84`). Contemporaneous score, not a forward horizon |
| tier labels | Liquidity, Rates / Dollar, Curve / Fed, Equity / VIX, Crypto-native (`118-119`) | Same factor scores, summed inside the tier (`217-233`) | Same last row | Same trailing windows |
| `mode_lean.chip` | `+flow`, `+macro`, `mixed` via `btc_correlation_regime.lean` (`290-293`) | Trailing 90d absolute correlation of close returns with real-yield and DXY diffs, versus an ETF-flow leg (`btc_correlation_regime.py:20-64`) | Last row of `df` | 90d trailing. Non-numeric. The module says it re-weights nothing |
| `flags.active` | STAY-AWAY, DOUBLE-DOWN, NONE via `btc_regime_flags.evaluate` (`282-285`, `btc_regime_flags.py:209-210`) | Eight stay-away and eight double-down conditions, k in {4, 5, 6}, default k=5 called illustrative (`btc_regime_flags.py:8-10`, `149-168`) | `evaluate` reads the last row (`194-195`) | Trailing z 365d and percentile 180d (`btc_regime_flags.py:29-45`) |

`exposure_display` (`174-177`, `252`) is a display knot on the same index, not a label and not a size.

### `engine/btc_mtf.py` — cycle ladder and confluence

`mtf_ladder` (`34-44`) returns `cycles.analyze(close, high, kind="crypto")` plus 2W and ME states. `confluence_verdict` (`91-188`) collapses that into one grade. There is no `as_of`. The clock is the last close of the series the caller passed.

| Label | Values | Inputs | Clock | Horizon |
| --- | --- | --- | --- | --- |
| confluence `grade` | CAUTION, BUY-THE-DIP, TREND-FOLLOW, AVOID, WAIT (`67-88`, `170`) | Short sign from ladder state plus D/3D MACD (`131-144`); long sign from ladder `regime` plus monthly MACD, left-translation, failed cycle (`115-123`) | Last bar of the passed series | Indicator lookbacks inside `cycles._tf_state` (MACD 12/26/9, RSI 14). No declared forward horizon |
| `regime` / `regime_label` | bull/bear/neutral and BULLISH/MIXED/BEARISH (`115`, `186`; `cycles.py:885-892`, `958`) | Weekly and 3-day MACD, investor-cycle failed/phase, last-cycle translation (`cycles.py:895-958`) | Same | Crypto hand template: daily-cycle band 56–70 calendar days, investor-cycle 24–40 weeks (`cycles.py:74-75`). See the fitted override below |
| `ladder_state` / `ladder_label` | DECLINE, BOTTOM WATCH, TURN SIGNALED, FRESH BUY, RALLY ON, TOP WATCH, ROLLING OVER, COUNTERTREND BOUNCE, CONFIRMING TURN (`cycles.py:624-626`). Display labels DOWNTREND, NEARING A LOW, BOTTOMING, BUY ZONE, UPTREND, NEARING A HIGH, TOPPING, UNCONFIRMED TURN, TURN IN PROGRESS (`cycles.py:653-690`) | `cycle_state` troughs plus MTF MACD/RSI (`cycles.py:964+`) | Same | Same cycle template |
| `per_tf` | up / down / flat on D, 3D, W, 2W, ME (`111-112`) | MACD position, cross, curl, RSI 55/45 (`49-63`) | Same | Same |
| `cycle.dc_phase` | new, mid, approaching_band, in_band, stretched (`cycles.py:504-513`) | Elapsed bars since the last confirmed daily-cycle trough, versus `dc_band` / `dc_early` | Same | The band is a typical-length template |
| `cycle.ic_phase` | early, mid, late, overdue (`cycles.py:515-519`) | Elapsed weeks since the last confirmed weekly trough, versus `ic_band_w` | Same | Same, in weeks |
| `ladder.cycle_plain` | Prose for those phases (`cycles.py:694-706`, attached at `1662`) | The phase keys above | Same | The prose adds a forecast tone the enum does not have. Quoted under conflation |

2W and ME are resampled in `btc_mtf.py:27-30` with no completed-bar drop. `cycles.mtf_snapshot` defaults `completed_only=False` (`cycles.py:349-376`), so the weekly and monthly states also use the in-progress bar. The value of that bar is the last close on or before the series end. The resampled stamp can sit on a Friday or a month-end after that close (`cycles.py:321-347` is the gate the default path does not use).

Fitted horizon, when `data/regime/cycle_bands_fit.json` is on disk. This sparse worktree does not check out `data/`. The blob is on HEAD. `git show HEAD:data/regime/cycle_bands_fit.json` gives crypto `dc_band [22, 45]`, `ic_band_w [11, 22]`, `n_troughs 104`, `n_series 1`, `method median±½IQR`, `fitted_on 2026-07-02`. `_preset` applies that override when both ends are positive and ordered (`cycles.py:172-198`). A full checkout's live crypto ladder therefore uses 22–45 days and 11–22 weeks, not the hand constants in `cycles.py:74-75`. The fit is one series. It is not an out-of-sample horizon. FX in the same file is `[0, 0]` and fails the `fdc[0] > 0` check, so FX stays on the hand constants. This lane's tests do not see the file, so they run on the hand constants.

### `engine/btc_cycle_thesis.py` — halving / midterm monitor

`monitor(close, cfg, sig, asof)` (`72-78`). Clock is `asof` if passed, else the last close (`95`). Schema `btc_cycle_thesis.v1`.

| Label | Values | Inputs | Clock | Horizon |
| --- | --- | --- | --- | --- |
| `thesis_status` | intact, watch, breaking (`308-315`) | Worst flag level: alert → breaking, watch → watch, else intact | `asof` | The windows below |
| `time_status` | unknown, early, in_window, overdue, `bottomed?` (`196-222`) | Now versus peak_date+360d / +430d (`40-41`, `131-136`). Overdue if still within 3% of the window's low (`212-214`) | `asof` | Projected bottom window. 360/430 are fixed days after the configured top, bracketed around the 364d and 378d historical down-legs named in the module comment (`35-37`) |
| flag `dampening` | ok or watch (`177-194`) | Drawdown from the configured peak versus the mean depth of completed prior bears, gap 0.15 (`49`, `177-178`). Watch only once `now >= window start` | `asof` | Comparison with completed bears, not a remaining-drawdown number |
| flag `timing` | ok, alert, or watch (`196-243`) | The peak window, plus a halving-anchored window if that one is already past (`229-243`) | `asof` | Peak window as above. Halving window is [min, max] of completed halving→next-bottom gaps, projection = median gap (`139-157`) |
| flag `structure` | ok / watch / alert from caller `sig.cphase_status` (`245-255`) | Optional `btc_signals` row with index `<= now` (`160-166`) | `asof` | The 1064/364 template lives in the caller. This monitor does not recompute it |
| flag `desync` | ok or watch (`263-282`) | Halving-projected bottom versus the nearest US midterm (year % 4 == 2, Nov 4), threshold 4.0 months (`52`, `268-273`) | `asof` | A distance between two projected dates |
| flag `pivot_staleness` | alert, or absent (`291-306`) | Running max close on `close.loc[:now]` more than 21d after the configured top, and only when the last pivot on/before now is a top (`46`, `294-297`) | `asof` | 21d slack |
| `accumulate` | bool (`317-318`) | In the peak window, drawdown ≤ −45% (`55`), structure not invalidated | `asof` | Same peak window. Context only, per the module docstring (`23-24`, `53-54`) |
| `days_since_halving` | integer days (`107`, `326`) | Last configured halving with date `<= now` | `asof` | Elapsed. Not a remaining count |
| `halving_overdue`, `pivot_stale`, `dampening`, `in_window` | bools (`341-347`) | The flags above | `asof` | As above |

`struct_next_pivot` (`343`) is copied from the caller. In `engine/btc_signals.py:1046` and `:1080` that pivot is anchor date plus the fixed 1064 or 364. The same function also emits `cphase_days_in` (elapsed, `1045`) and `cphase_days_left` (template length minus elapsed, `1079`). The thesis monitor does not copy `cphase_days_left`. It does copy the projected date.

### `engine/crypto_market_state.py` — class display state

No `as_of` argument. `build_market_state` stamps `as_of` as the max last timestamp among total cap, dominance, fear-greed, stablecoins, and BTC (`282-287`). The ETF block carries its own `as_of` (`317`). Stance uses each series' own last row, so a later fear print can date the payload past the cap print that produced the stance.

| Label | Values | Inputs | Clock | Horizon |
| --- | --- | --- | --- | --- |
| `stance` | Advancing with wider participation; Advancing, led by Bitcoin; Cooling, with participation narrowing; Risk receding across the complex; Range-bound, waiting for participation (`154-184`) | Total-cap 30d percent (`147-149`) threshold ±3, and dominance 30d point-change threshold ±1 | Last row of each series | 30 days back. No forward horizon |
| `total_state`, `dominance_state`, stablecoin `state` | Rising, Falling, Steady, Unavailable (`101-108`, `149-150`, `188`) | 30d percent or point change. Thresholds 3 / 1 / 1 | Own last row | 30d |
| `fear_state` | Extreme fear ≤24, Fearful ≤44, Neutral <56, Greedy <76, Extreme greed, else Unavailable (`111-122`) | Last fear-greed print | Own last row | The print itself. No lookback |
| class `regimes[].tone` | bull, bear, neutral (`72-98`) | Total cap above/below its trailing 90d mean and 30d return beyond ±3% (`78-81`) | Each cap date. `build_market_state` passes only `total.tail(1460)` (`288`, `311`) | 90d mean, 30d momentum. The open segment's `end` is the last print |
| volume / funding / oi / vol / alt `state` | High participation, Quiet tape, Normal; Longs crowded, Shorts paying, Balanced, Unavailable; Leverage elevated / light / normal / Unavailable; Volatility hot / compressed / normal / Unavailable; Alt participation broad, Bitcoin-led, Mixed participation, Building history (`203-274`) | BTC volume percentile in a trailing 365d window (`200-202`); signal-row funding and OI and DVOL percentiles; ETH/BTC 90d relative return (`265`) | Last row of the relevant series. Signals come from `vector/signals` `iloc[-1]` with no date filter (`125-129`) | 365d, the signal row's own window, 90d |

`total_market_cap_history` forward-fills BTC cap and dominance with `ffill(limit=3)` (`59`). There is no backfill.

## Look-ahead

A label looks ahead when its value as of t changes because a row dated after t was visible, or because it uses a cycle peak or trough that was not confirmable at t.

### Confirmed leak — thesis pivot slack

`_extreme` (`engine/btc_cycle_thesis.py:62-69`) takes the max or min of `close` on `[pivot − 21d, pivot + 21d]` and does not clip the right edge at `now`. Callers:

- peak price, `112`: `peak_px = _extreme(close, peak_date, "top")` on the full `close`, not on `close.loc[:now]`.
- prior-bear depth, `123`: both the top and the bottom go through the same unsliced window. The bottom is included only when `nb <= now` (`121`), but the price of that bottom still reads 21 days past `nb`.

`px` (`96`), the running-max fallback (`114`), `recent_low` (`212`), the halving-window low (`232`), and the ATH used for pivot staleness (`295-296`) all slice at `now`. The halving-gap list keeps only bottoms `nb <= now` (`151`). Configured tops and bottoms dated after `now` are excluded from the current peak and from completed bears (`110`, `121`). Those filters do not close the slack window.

Discriminating fixture, encoded in `tests/test_btc_regime_lookahead.py::test_cycle_thesis_label_at_t_ignores_rows_after_t`. Top `2019-01-01`, bottom `2020-01-06`, `asof=2020-01-11` (five days after the bottom, inside the +21d slack, and inside the peak+360/430 window). Causal prior-bear depth is −0.52 and `thesis_status` is `intact`. A print of 20 on `2020-01-21` (after as-of, inside the slack) moves `prior_bear_mean` to −0.80, flips `dampening` to true, and flips `thesis_status` to `watch`. Same `asof` string both times: `2020-01-11`. That test is `xfail(strict)` until the patch lands, and an XPASS(strict) will fail CI to force the marker's removal.

Existing cover does not hit this window. `tests/test_btc_cycle_thesis.py:45` calls `monitor(_series(), asof="2026-06-28")` while `_series` runs through `2027-03-01` (`23-32`), but that as-of sits hundreds of days after the last configured pivot, so the slack does not reach the extra rows. `tests/test_btc_signals.py:229-238` checks `cphase_phase` under price truncation. It does not call `_extreme`.

Patch, not applied (this lane owns no engine file): `research/crypto_science/patches/cx-t13p-20261012__btc_cycle_thesis.patch`. It slices `close` to `now` once, immediately after the clock is chosen, and returns `asof_before_history` on an empty slice.

### Config pivots are known on their own date

`past_tops = [t for t in tops if t <= now]` (`110`) treats a configured top as known on the top's calendar date. The shipped list includes `2025-10-06` (`config.yml:6056`), which was recorded after the extreme. A replay that uses today's `config.yml` at an as-of on or just after that date sees a peak the tape had not confirmed. The code never versions the registry by the date the pivot was written. `pivot_staleness` (`284-306`) detects a new high after the recorded top. It does not detect "this top was not in the file yet." `cycle_phase_clock` has the same date filter and says so (`engine/btc_signals.py:999-1000`, `1025`). That is pivot-date filtering, not record-date filtering. No record-date column exists. UNVERIFIED: any older revision of `config.yml` that would show when `2025-10-06` was added. Search bound: this file and `config.yml:6050-6059` only.

### MTF troughs — lagged if truncated, revised if the full sample is labeled once

`find_troughs` (`engine/cycles.py:399-408`) confirms a local minimum only when `window` bars exist on both sides (`TROUGH_WINDOW = 10`, line `56`). The loop is `range(window, len(arr) - window)`. Given a series that ends at t, the label does not read a bar after t. The last ten bars cannot be a confirmed trough yet. That is a confirmation lag.

The merge (`414-418`) keeps the lower of two troughs closer than `TROUGH_MIN_GAP` (18). A trough confirmed at t can disappear from `find_troughs` once a later, lower trough inside that gap becomes confirmable. `test_full_sample_trough_merge_rewrites_a_trough_the_prefix_had_confirmed` builds that pair on a strictly rising series (iloc 30 price 50, iloc 47 price 40, prefix end iloc 49). The prefix returns only the first trough. The full sample replaces it with the second. That second trough is dated before the prefix end, but it is not confirmable until ten bars exist after it, which the prefix does not have. `signal_age` does not do this: it recomputes each past day on `iloc[:end+1]` (`cycles.py:1721-1734`). `mtf_ladder` is safe only when the caller passes a series that already ends at the decision date. It has no `as_of` of its own (`btc_mtf.py:34-40`).

Translation (`cycles.py:467-472`) is the argmax between two troughs that are already confirmed inside the passed series. It does not read the eventual next peak beyond the series end.

### Macro band, class tone, market stance

`composite_frame` uses trailing `rolling` (default `center=False`) and `diff` (`btc_regime.py:49-71`, `74-84`). The row at t in a longer frame matches `composite_frame` on `df.loc[:t]`. Checked by `test_regime_band_at_t_ignores_rows_after_t`. No look-ahead past the last row. A caller who leaves post-decision rows in `df` gets the band at the new end, because `compute` reads `iloc[-1]` (`198`).

`class_regimes` (`crypto_market_state.py:77-81`) is a trailing 90d mean and a 30d return. The tone on each date ≤ t is unchanged by later rows (`test_class_regime_tone_through_t_ignores_rows_after_t`). The segment list is not unchanged: the open segment's `end` is the last print (`91-96`), and a transition's `end` is the first day of the next tone (`86-89`). Reading `end - start` on the open segment as a finished regime length overstates a duration that is still running.

`build_market_state` has no clock argument. `test_market_state_stance_at_t_requires_the_caller_to_withhold_later_rows` shows a flat path whose stance is "Range-bound, waiting for participation" at t, and a different stance once a post-t crash is left in the reader. Withholding rows after t restores the pinned stance. `_latest_signals` (`125-129`) will also follow a future signal row if the reader returns one.

### Not look-ahead, and not a remaining-time field

Partial weekly and monthly bars on a series that already ends at t use the last known close. They do not invent a future price. They are look-ahead only when later bars of the same week or month are still in the frame and the caller meant an earlier t. Truncation is the fix the API allows today.

## Elapsed versus remaining

| Surface | What it actually is | Where the words slide |
| --- | --- | --- |
| `days_since_halving` (`107`) | Elapsed days since the last halving on or before `now` | Not a forecast |
| `cycle.dc_day`, `cycle.ic_week` (`cycles.py:435`, `501`) | Elapsed bars since the last confirmed trough | `cycle_plain.daily_line` prints "day N of a typical lo–hi" (`cycles.py:729`). Elapsed and template in one sentence |
| `dc_phase` / `ic_phase` (`504-519`) | Bins of that elapsed count | `DC_PHASE_PLAIN["stretched"]` (`699`): "overdue — past the typical window, so a low could form any day." `IC_PHASE_PLAIN["early"]` (`702`): "lots of room left in the bigger up-leg." `IC_PHASE_PLAIN["overdue"]` (`705`): "expect more volatility." The enum is elapsed. The prose states remaining room or an imminent low |
| dampening flag, pre-window (`192-194`) | "Drawdown X% so far … (bear still developing.)" | This branch keeps elapsed drawdown and the prior-bear average apart |
| dampening watch (`180-186`) | A conclusion that this bear is shallower than the completed-bear mean | Gated on `now >= window start` (`176`). Still one point-in-time drawdown, not a completed-cycle depth |
| `time_status=early` prose (`202-204`) | "~{d}d until the projected window opens" | This is a remaining-days figure. It is not stored as its own field. It is a countdown to a template, not an observed duration |
| `time_status=overdue` (`214-219`) | Elapsed past the template, and price still near the window low | The word names a missed forecast |
| `time_status=bottomed?` (`214`, `220-222`) | Price has lifted more than 3% off the min from window start through `now` | Computed only from data ≤ `now`. The name asserts a cycle trough. The eventual trough can still be later. Appending rows after `now` does not, by itself, rewrite this status |
| class regime open segment (`91-96`) | Start of the current tone through the last print | Duration so far. No remaining-length field |
| `cphase_days_left` (`btc_signals.py:1079`), not emitted here | Template length minus days already in the leg | Negative once the leg runs long. A consumer who prints it as "days left" is showing a remaining forecast that has gone negative. The monitor's copy of the same idea is `struct_next_pivot` |

No surface in the four files emits both an observed "duration so far" and a "days remaining" under one undifferentiated key. The conflations are the plain-language lines above, the early-window countdown inside the timing flag, and `bottomed?`.

## T13 test plan

The prefix tests in `tests/test_btc_regime_lookahead.py` are the look-ahead half. The rest is the evaluation contract. It is not implemented in this lane.

Information set. One clock per row: the decision date t. Every input is masked to dates ≤ t before the label function runs. For `monitor`, pass the longer frame and `asof=t` (that is the bug the patch closes). For `compute`, `mtf_ladder`, `confluence_verdict`, and `build_market_state`, the mask is the caller's truncation, because those functions treat the last row as t. A signal frame passed into `monitor` stays `sig[sig.index <= t]`, which the function already does (`160-162`). The pivot registry used at t contains only pivots whose record date is ≤ t. Today's `config.yml` has no record date, so a replay that needs one cannot claim it. Minimum censor, until a record date exists: drop any pivot with `pivot + 21d > t`, matching `_extreme`'s slack, and drop any pivot dated after t.

Controls, same clock and the same masked prices. No fitted classifier.

- Trend. `up` when close[t] > SMA200[t] and SMA200[t] > SMA200[t−20]. `down` when close[t] < SMA200[t] and the 20d SMA change is negative. `flat` otherwise. SMA is computed on `close.loc[:t]`.
- Volatility. 20-day realized volatility's percentile inside the trailing 365 days ending at t. `high` at or above 0.80, `low` at or below 0.20, else `mid`. Percentile uses only the window ending at t.

Report a contingency of each label against the trend control and against the vol control. Agreement is a description of overlap. It is not a hit rate and not a probability.

Time holdout. Do not retune the published cutoffs (band 75/58/42/25, class-regime 90/30/0.03, confluence signs, 360/430, 0.15 dampening gap) on the evaluation block. Those numbers stay the published ones. If a later lane moves a cutoff, the days that chose the cutoff and the days that report it are disjoint, with the cutoff frozen before the report block starts. The fitted cycle band (`fitted_on 2026-07-02`, one crypto series) is not refit inside T13, and it is not used as the control.

Episode holdout. Score by episode, not by day. Episodes: configured completed bears (bottom ≤ t); confirmed trough-to-trough spans from `find_troughs` on the truncated series; contiguous class-regime tones; contiguous macro-band runs. Leave each episode out of the descriptive contingency in turn. A label that agrees with the trend control only inside one episode does not get a broader sentence.

One omitted major cycle. At one frozen as-of after `2022-11-21`, recompute `prior_bear_mean`, the halving-gap min/max/median, `halving_proj_bottom`, `dampening`, and `thesis_status` three times, each time dropping one of the shipped completed bears (`2017-12-16→2018-12-15`, `2021-11-08→2022-11-21`, and the 2015 low's leg if a prior top is in the file). Publish the range of `prior_bear_mean` and whether `thesis_status` changes. Do not drop the omission that flatters the thesis. The crypto fitted band is `n_series: 1`; leaving out a calendar slice of that single series is the analogous check for `dc_band` / `ic_band_w`, and the hand constants in `cycles.py:74-75` stay the fallback the report also prints.

Event counts. Every sentence that talks about how often a label did something prints `n_episodes` and `n_days` as separate integers. `n_days` is not the sample size. The fitted artifact's `n_troughs: 104` on `n_series: 1` is a trough count, not 104 independent cycles. The thesis docstring's "n=3" (`btc_cycle_thesis.py:12`, `84`) is the event count that matters for prior bears. `btc_regime_flags.py:9` already says k=5 is not identifiable on about five cycles. Keep that sentence next to any flag count.

Qualification. Useful descriptive output may ship: the macro band, the confluence grade, the class stance and tones, `thesis_status` as a monitor chip. No probability is attached. No new column fuses those labels. `bottomed?`, the stretched/overdue prose, and the early-window countdown stay worded as template position, or they stay off any surface that a reader could take as a remaining-time forecast. Missing inputs stay unavailable.

## What this lane ran

`tests/test_btc_regime_lookahead.py` implements the prefix protocol, the leaky full-sample extreme oracle, the trough-merge counterexample on `find_troughs`, and the thesis case that current `monitor` fails. It does not implement the holdout, the leave-one-cycle table, or the control contingencies. Those stay in this plan until an evaluation lane has a price panel that is not the synthetic fixture.
