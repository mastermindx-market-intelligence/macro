# T19 costed protection — preregistration DRAFT (2026-10-13)

Status: DRAFT. The seat freezes this file later. This draft grants no live capital authority.
Model output never gains sizing or execution authority. Policy research includes delay, costs, cash, FX, financing, turnover and missed rebound, and it grants no live capital authority.

Program: `WS:GREY-DEER-RISK-INTELLIGENCE` / MAS-258. Lane: `GD-W7-T19PRE`. Base: `origin/main`. Branch: `lane/grey-deer-w7-t19pre-20261013`. This file is a research-display protocol. It is not a freeze, not a sha256-pinned artifact, and not an order to compute outcomes. No return, hit rate, or skill number is computed or quoted here.

## 1. Question

When a pullback warning state is issued, does a protective response improve risk-adjusted outcomes net of delay, transaction costs, cash carry, FX carry, financing, turnover, and missed rebound?

The answer, when a later frozen revision is executed, is a research display. It does not size, rank, gate, or execute. `engine/risk_envelope.py:610-618` keeps `envelope_may_size` and `envelope_may_execute` false, and keeps `policy_actions_require_individual_authority` true. This protocol does not add a policy object. `engine/risk_envelope.py:826-839` leaves `policies` empty because the composer owns no policy ledger.

## 2. Input register

Every row is an input, a clock, or an explicit non-input that a reader could mistake for one. The executing lane uses a row only in the role written here.

| Id | What | file:line | Availability clock | Role in this protocol |
|---|---|---|---|---|
| I1 | US Risk Radar state vocabulary `calm`, `watch`, `caution`, `elevated`, `risk-off` | `engine/risk_radar.py:225` | The snapshot `asof` is the signal frame's last session (`engine/risk_radar.py:1071`, written at `engine/risk_radar.py:1257`) | State names. Loud membership is I3 |
| I2 | Loud banner threshold `alert_from = elevated` | `engine/risk_radar.py:226`, applied at `engine/risk_radar.py:1199-1200` | Same snapshot `asof` | Defines the primary trigger set with I3 |
| I3 | Loud alert states `elevated`, `risk-off` | `engine/risk_radar_audit.py:32` | The forward-log row's `asof` | Primary trigger set `T_loud` |
| I4 | Issued-state ledger | `engine/risk_radar_audit.py:69-71` path `data/risk_radar/forward_log.jsonl`; append `engine/risk_radar_audit.py:234-253` | Session date `asof`. Appends only when `COLLECT_LANE` is `nightly` (`engine/risk_radar_audit.py:50-66`). First writer for that `asof` wins (`engine/risk_radar_audit.py:250-252`). `snapshot_and_grade` is the nightly entry (`engine/risk_radar_audit.py:410-417`) | Primary slice. This draft does not open the log |
| I5 | Prospective issue receipt | `engine/risk_radar_audit.py:37-38` contract `risk_radar_forward_issue.v1`, epoch `2026-09-23-prospective-v1`; fields at `engine/risk_radar_audit.py:139-152` | `issued_at` equals `logged_at`, both UTC. A receipted row is timely only when `issued_at`'s calendar date is the session date or the next calendar day (`engine/risk_radar_scorecard.py:566-572`) | Rows with a valid receipt are `ISSUED_RECEIPTED`. Rows the ledger holds without that receipt stay `ISSUED_LEGACY_NO_RECEIPT`. The two sub-tables are separate. Historical rows are not backfilled |
| I6 | Current-vintage state replay | `engine/risk_radar_backtest.py:138-173` `state_series` | Replay date index of the signal frame passed in. The pullback preregistration classes this replay as `CURRENT_VINTAGE` (`research/grey_deer/PULLBACK_PREREGISTRATION_2026-10-11.md:54`, construction at `:198-213`) | Diagnostic slice only. A diagnostic table. The label on every table is `CURRENT_VINTAGE` |
| I7 | Envelope hazard vocabulary `NONE`, `FRAGILE`, `TRANSMITTING`, `BREAKDOWN` | `engine/risk_envelope.py:158` | Caller-supplied `observed_at`, `produced_at`, `stale_after`; `as_of` defaults to `source_session` (`engine/risk_envelope.py:777-824`, `:869-872`). The composer reads no clock (`engine/risk_envelope.py:22-27`) | Non-input. V0 `stage_since` is null (`engine/risk_envelope.py:84-89`, `:387-405`). `TRANSMITTING` and `BREAKDOWN` are unreachable in V0 (`engine/risk_envelope.py:70-78`). `ARMED` and `TRIGGERING` cannot be emitted (`engine/risk_envelope.py:183-198`). No episode ledger, no policy ledger |
| I8 | Market State display verdict | `engine/market_state.py:10-12` | Forward-ledger path and daily-engine cadence recorded at `docs/SIGNAL_BUS.md:371` | Non-input. Display blend (`engine/market_state.py:3-22`). This protocol does not read its ledger and does not claim an issue-field layout it has not specified |
| I9 | Vol-regime label `warning` | `engine/vol_regime.py:575-578`; haircut literal in `config.yml:3447` | Whatever `asof` the published regime snapshot already carries. `sizing_overlay` takes that snapshot as an argument (`engine/vol_regime.py:514`) | Non-input. The volatility-targeting baseline is I18, not this haircut |
| I10 | Pullback-forecast issue lane | `research/grey_deer/PULLBACK_PREREGISTRATION_2026-10-11.md:448-450` | Prospective clock starts at the first forecast that lane writes. That preregistration records the lane as not started | Non-input. No issued pullback-probability forecast exists to trigger on |
| I11 | SPY price path | `collectors/massive_stock_day.py:759-768` `load_ticker`; basis `config/dataset_registry.yml:135-158` (`adjustment: none`, `basis: raw`, `renames_to: close_raw`); floor `collectors/massive_stock_day.py:146-150` `EARLIEST_ENTITLED = 2021-07-06` | Session date of the RAW daily bar. The frozen pullback preregistration's measured window runs 2021-07-06 through 2026-10-07 (`research/grey_deer/PULLBACK_PREREGISTRATION_2026-10-11.md:71-73`). Manifest disposition for internal evaluation is recorded at `research/grey_deer/PULLBACK_SOURCE_RIGHTS_QUALIFICATION_2026-10-11.md` D1, D4, D5 | The only price path. Ratios of RAW closes. No raw level is written into a result file |
| I12 | NYSE session set | `lib/nyse_calendar.py:121-148` `is_session`, `sessions_between` | A date is a session when it is a weekday and it is outside that module's holiday and one-off closure sets | Index for every series. A non-session row is dropped. A duplicate session stops the run |
| I13 | Implied volatility, VIX close | `config.yml:209` `VIXCLS: vix_close`; also pointed from `config.yml:4312` and `config.yml:5362`. Collector `collectors/fred.py` | Observation date on the series. VIX is in the market group the collector treats as unrevised and keeps out of the ALFRED vintage matrix (`collectors/fred.py:36-41`). Usable for a decision at the close of session `t` because the trade is lagged to the next session | Put-cost proxy volatility. Annualized decimal is the print divided by 100 |
| I14 | Cash yield | `config.yml:391-402` `DTB3: us3m_bill`; reader order documented at `engine/equity_alloc.py:31-42` | Daily observation date. Same unrevised-market rule as I13 (`collectors/fred.py:36-41`). Discount basis, and the config comment marks it as distinct from `DGS3MO` | The only cash-carry series. The `bill_yield` fallback to `DGS3MO` or `DFF` is not used |
| I15 | Financing quote | `config.yml:403` `SOFR: sofr` | Daily observation date. Same unrevised-market rule (`collectors/fred.py:36-41`) | Named financing quote. Charge is zero in this revision because no weight exceeds 1 |
| I16 | Policy-rate and FX quotes | `config.yml:178` `DFF: fed_funds`; FX carry US leg `config.yml:5359` and `:5429`; H.10 FX pairs `config.yml:378-387` | `DFF` and the H.10 pairs are daily FRED observation dates. Same unrevised-market rule (`collectors/fred.py:36-41`) | Named so the FX and financing set is complete. This book is USD. FX carry is zero. No FX series is read into the P&L |
| I17 | Trade lag and one-way cost engine | `engine/validation.py:36-94` `backtest_core`; next-bar position at `:70` | Position decided at session `t` multiplies the close-to-close return of the next bar | The only lag and the only equity transaction-cost arithmetic. Imported. Not reimplemented |
| I18 | Volatility-target scalar | `engine/vol_managed.py:43-50` `vol_scalar`; research-helper contract at `engine/vol_managed.py:9-12` | Scalar at `t` uses closes through `t`. The caller then lags it through I17 | Baseline B1 |
| I19 | Published 12 percent vol target | `config.yml:3536-3538` `target_vol_pct: 12.0`, `realized_window_d: 21` | A config literal, versioned with the commit the executing lane pins | B1's `target=0.12`. The live cap `1.5` at `config.yml:3540` is not used |
| I20 | Published gross map used by the radar | `engine/regime_one.py:63-71` `RISK_STATE_GROSS_VERSION = "2026-07-01.v1"`, `elevated: 0.78`, `risk-off: 0.60`, floor `_GROSS_FLOOR = 0.50` at `:71`; radar application `engine/risk_radar.py:1352-1355` | A source literal. The radar comment at `engine/risk_radar.py:244-248` points `_gross_for` at this table | Policy P1 weights. Checked equal to these literals at execution |
| I21 | Equity one-way cost literal | `engine/equity_alloc.py:113` default `cost_bps = 3.0` | A function default. An assumption of that harness, inherited here as a literal | Primary one-way cost, 3.0 bps per unit of equity-weight turnover |
| I22 | Wider one-way cost literal | `config.yml:4045` `cost_bps: 8` on the cross-asset calibration block | A config literal for a futures-proxy harness | Sensitivity cost, 8.0 bps. Display only |
| I23 | Cash-carry day count inside the engine | `engine/validation.py:83-86` | Calendar days between bars, divided by 365, times the annualized yield divided by 100 | Imported with I17. The yield series is prepared under §6 before the call |
| I24 | Companion return-block bootstrap | `engine/validation.py:455-480` `block_bootstrap_ci` | Operates on a return series the executing lane has already built. Default block 21, default `B` 5000, default seed 7, default `ann` 365 | Companion display only, called with the overrides in §10. The primary uncertainty is §10 |
| I25 | Issued-warning duration display | `research/grey_deer/RISK_RADAR_ISSUED_WARNING_DURATION_2026-09-24.md:13-16` and `:34-48` | Counts consecutive issued NYSE sessions on I4 | Non-input. Display fact. The staged policy's 5-session step is a separate literal (§5) and does not read this feature |
| I26 | T12 matched-sample builder | Path named by the lane packet: `scripts/research/grey_deer_episode_samples.py` | Present on this base as the T12 episode and negative-control sample builder, but it does not export `matched_protection_masks` yet. Lane GD-W7-T12MASK builds that function against the B2 contract in §10 | Baseline B2. While the function is absent the baseline status is `BLOCKED_BUILDER_ABSENT` |
| I27 | Pullback stage-1 scripts | `scripts/research/grey_deer_pullback_stage1.py:2334` imports `state_series` | Those scripts are frozen for this lane. A search of `scripts/research/grey_deer_*.py` finds no `backtest_core`, `cost_bps`, or `shift(1)` | Non-input. They are not a protection-policy harness |
| I28 | Collection-advance limit recorded by the continuation handoff | `research/grey_deer/GREY_DEER_CONTINUATION_HANDOFF_2026-10-11.md:70` F2 | That note's verified newest US collection label on main is the 2026-10-09 collection | A bound on how far I4 can extend in the commit the handoff inspected. This draft does not re-measure the log. The executing lane's slice ends at the log's last `asof` |

FRED series I13, I14, I15, and I16 sit outside the qualified fitting set of `research/grey_deer/PULLBACK_SOURCE_RIGHTS_QUALIFICATION_2026-10-11.md` (the register pointer in that file at lines 69–72). This draft does not enlarge that disposition. Those series enter only the internal cost ledger of this research display. A customer-facing or published use of them is out of scope. Vendor license text is not restated here.

The price path is the Massive RAW tape in I11. `engine/equity_alloc.py:45-50` reads a Yahoo close. This protocol does not call it.

## 3. Slices

Two slices. Each metric is computed inside one slice. A table names its slice in the title.

**GENUINELY_ISSUED.** Sessions that have an I4 row with a non-null `state`, whose `asof` is an I12 session, and whose price path contains that session and the next session. `ISSUED_RECEIPTED` and `ISSUED_LEGACY_NO_RECEIPT` are sub-tables. The primary gate reads `ISSUED_RECEIPTED` when that sub-table exists. When every issued row lacks a receipt, the primary gate reads `ISSUED_LEGACY_NO_RECEIPT` and the table title says so. A receipt that fails the I5 timeliness check is dropped and counted as `ISSUE_CLOCK_REJECTED`.

**CURRENT_VINTAGE.** I6 states aligned onto the I11 session index inside the window 2021-07-06 through 2026-10-07. The table title is `CURRENT_VINTAGE`. The gate does not read this slice. Reconstruction remains a diagnostic (§14 of the pullback preregistration, lines 460–461, states the same rule for that protocol).

The probability table inside the radar is not an input. The executing lane does not read it, print it, or score against it.

## 4. Trigger

Primary trigger `T_loud`. On an issued row, the trigger is on when `state` is `elevated` or `risk-off` (I3).

- Entry decision: the first session of a run where the trigger is on.
- Exit decision: the first later session of that run where the trigger is off.
- `watch` and `calm` leave the trigger off.
- `state_ungated` is ignored.
- `can_force` is ignored.
- The duration feature I25 is ignored.
- The election-cycle gross multiplier inside the radar (`engine/risk_radar.py:1201-1207`) is ignored.

Sensitivity trigger `T_caution`, display only: on when `state` is `caution`, `elevated`, or `risk-off`. Same entry and exit rule. It cannot become the primary trigger after results exist.

A hole in the price path on the session after a decision keeps the previous live weight, charges no new equity turnover, and records `PRICE_HOLE`. The decision is applied on the next session that has a price, still subject to the lag in §6.

## 5. Policy set

Book: one unit of USD notional. Equity weight `w` is in `[0, 1]`. The cash sleeve is `1 - w`. No leverage, no short, no second asset, no FX conversion. Weights below are target weights at the decision close. The live weight is the lagged target (§6).

No weight is estimated from the sample. At execution, P1's two factors are read from `engine.regime_one.RISK_STATE_GROSS` and compared to the literals below. A mismatch stops the run with `GROSS_MAP_MOVED`. The version string must equal `2026-07-01.v1`.

| Id | Name | Target weight while the trigger is on | Target weight while the trigger is off |
|---|---|---|---|
| P0 | Always invested | `1` | `1` |
| P1 | Reduce exposure | `elevated → 0.78`, `risk-off → 0.60`, and never below `0.50` (I20) | `1` |
| P2 | Move to cash | `0` | `1` |
| P3 | Index-put cost proxy | `1`, plus the put in §7 | `1`, and no put |
| P4 | Staged de-risking | `0.75`, then `0.50`, then `0` on the schedule below | `1`, in one step |

P1 uses the published radar gross factors for the two loud states. It does not use the watch factor, the caution factor, or the election-cycle multiplier.

P4 schedule, counted in NYSE sessions from the entry decision `t0` with `len(sessions_between(t0, t)) - 1` (`lib/nyse_calendar.py:137-148`):

- At `t0`, target `0.75`.
- At the session where that distance equals 5, if the trigger is still on, target `0.50`.
- At the session where that distance equals 10, if the trigger is still on, target `0`.
- An exit decision cancels any later stage and sets the target to `1`.

The distances 5 and 10 are round literals chosen in this draft. They are not read from I25.

Sensitivity `P1-half`, display only: any loud state sets the target to `0.50`. It does not replace P1 in the gate.

P0 is also baseline B0.

## 6. Execution lag

Primary lag `L = 1` session. The target decided at the close of session `t` is the live weight that multiplies the return of the next session. That is the shift inside `backtest_core` (`engine/validation.py:70`).

The series passed into `backtest_core` for `L = 1` is the unshifted decision-target series. The function applies the one-session shift. A synthetic test must show that a target dated `t` first affects the return dated at the next session, and that it does not affect the return dated `t`.

Sensitivity `L = 2`, display only. The series passed into `backtest_core` is the decision-target series already shifted by one session, so the function's own shift makes the total lag two sessions. The same synthetic test pins the total at two.

`backtest_core` has no lag argument. The executing lane does not add one by editing `engine/validation.py`.

Same-session trading is outside this protocol. The price path is a daily close, so the one-session lag is the whole next session, which covers a receipt whose `issued_at` falls on the next calendar day (I5).

## 7. Index-put cost proxy

P3 keeps equity weight at 1. The put is a formula, not a vendor option chain. No option chain, no option price, and no raw index level is read or written.

Frozen contract:

- Strike factor `K_factor = 0.95`. The radar's declared pullback size for its own ledger grade is `0.05` (`engine/risk_radar_audit.py:30-31`). The strike sits that fraction below the decision close. This sentence cites a threshold literal. It cites no frequency.
- Tenor `N = 21` NYSE sessions after the decision session. Expiry is that 21st session (`sessions_between`).
- Year fraction `T = (expiry_date - decision_date).days / 365`. Floor `T` at `1/365` inside the mark formula.
- Dividend yield `q = 0`.
- Entry volatility `σ_in = VIXCLS_t / 100 + 0.0015`.
- Early-exit volatility `σ_out = max(VIXCLS_exit / 100 - 0.0015, 0.01)`.
- The half-spread `0.0015` is `ASSUMED_HALF_SPREAD`. It is a round literal. It is not a measured option spread. A round trip of two half-spreads is `0.0030` in volatility points.
- Rate `r = DTB3_t / 100`, used as the continuous rate in the formula below. `DTB3` is a discount-basis print (I14). The basis difference is a known exposure (§14). No conversion function is added at execution time.
- Spot in the formula is `S = 1`. Premiums are fractions of the decision-session RAW close.
- Premium cap: if the entry premium fraction exceeds `0.05`, that entry is skipped, counted as `PUT_PREMIUM_CAP`, and no put is opened.
- Missing `VIXCLS` on the decision session skips the entry, counted as `IV_MISSING`.
- A new put is opened only on an entry decision, and, if the trigger is still on at an expiry session, a roll is decided on that expiry session and the new put goes live on the next session under the same lag. The old put settles on its expiry session.
- Expiry settlement is intrinsic: `max(0.95 - close_expiry / close_decision, 0)`.
- An exit of the trigger before expiry marks the put with the formula at `σ_out` and the remaining `T`, as a fraction of the then spot, then multiplies by `close_exit / close_decision` so the cashflow stays in units of the original notional. The mark is received on the live session of the exit (the lagged session).
- Entry premium is paid on the live session of the entry (the lagged session).

Formula, with `N(·)` equal to `scipy.stats.norm.cdf`:

```
d1 = (ln(S / K_factor) + (r - q + σ² / 2) * T) / (σ * sqrt(T))
d2 = d1 - σ * sqrt(T)
premium = K_factor * exp(-r * T) * N(-d2) - S * exp(-q * T) * N(-d1)
```

There is no Black-Scholes function in this repository (a definition search for `black_scholes`, `bsm_`, `put_premium`, and `european_put` returned none). The executing lane calls `scipy.stats.norm.cdf` and writes this formula once. A synthetic test pins one hand-computable identity and uses no market series: `S = 1`, `K_factor = 1`, `r = 0`, `q = 0`, `σ = 0.20`, `T = 1` gives `d1 = 0.10`, `d2 = -0.10`, and `premium = N(0.10) - N(-0.10) = 2 * N(0.10) - 1`, within `1e-12`.

P3's equity turnover is zero, so I21 charges nothing on the equity sleeve. The put's cashflows are subtracted from the `backtest_core` net series after the call. Put rolls are counted in `put_rolls` and are not equity turnover.

CBOE SKEW (`config.yml:552-554`, context percentile at `engine/vol_regime.py:182-186`) is not an input. The manifest records unregistered CBOE substrates outside the qualified fitting set.

## 8. Costs, carry, financing

Applied to every policy, including P0 and both baselines.

- **Delay.** Section 6. Primary `L = 1`.
- **Equity transaction cost.** I21, `cost_bps = 3.0`, one-way, charged by I17 on `|Δw|`. A full exit and later re-entry pays `6.0` bps of notional. Sensitivity display uses I22, `cost_bps = 8.0`, in place of `3.0`, on the primary trigger and `L = 1`.
- **Cash carry.** The uninvested sleeve earns I14. Preparation, before the call: align `DTB3` onto the session index by exact session date; forward-fill at most 5 sessions; replace any session that is still empty with `0` and list that session as `CASH_RATE_STALE`. Pass the prepared series as `cash_yield`. I17's own forward-fill (`engine/validation.py:85`) then sees no gap longer than 5 sessions. Unlimited forward-fill and the `bill_yield` fallback are out of scope.
- **FX carry.** Zero. The book is USD. I16 is not read.
- **Financing.** Zero. No weight exceeds 1, so nothing is borrowed and I15 is not read. A later revision that adds leverage names SOFR as the financing quote and is a new preregistration.
- **Put spread and premium.** Section 7, policy P3 only.
- **Missed rebound.** A metric in §9. It is not a separate haircut on the equity curve. The net curve already contains it.

`backtest_core` sets the first close-to-close return to 0 via `pct_change().fillna(0)`, and the first live weight comes from a shift off a leading empty (`engine/validation.py:69-71`). The synthetic test pins both. The executing lane does not "correct" them.

## 9. Metrics

All metrics use the net-of-cost series from §8. None of them is computed in this draft.

Let `eq` be the cumulative product of `1 + net`. Let years be `(last_session - first_session).days / 365.25`, the same year rule as `backtest_core` (`engine/validation.py:92`).

1. **Drawdown avoided.** `maxdd(eq)` is the minimum of `eq / running_max(eq) - 1`. Drawdown avoided versus P0 is `maxdd(eq_P0) - maxdd(eq_policy)`. Positive means the policy's worst net loss is smaller.
2. **Missed rebound.** Over each protection episode (§10), `gap = cumulative_net(P0) - cumulative_net(policy)`. Floored missed rebound is `max(gap, 0)`. The signed gap is kept beside it. The gate uses the signed sum. The floored sum is the display decomposition of rebound given up.
3. **Turnover.** Sum of `|Δw|` divided by years. One-way. `put_rolls` is a separate count.
4. **Net-of-cost return difference.** Terminal `eq_policy - eq_P0`, and the sum of per-session `net_policy - net_P0`. Both are displayed. A positive terminal difference is not required for a pass (§12). An insurance overlay can finish with a lower terminal multiple and still be the research question this protocol asks, provided the drawdown and the signed episode comparison clear the baselines.
5. **Time in protection.** The fraction of slice sessions whose live weight is below 1, or whose live book holds an open put. Also the session count `k`. Baseline B2 matches `k` and matches the run lengths.

Episode window used inside (2): the live protection run, extended through 21 NYSE sessions after the exit decision, merged when those extended windows overlap. The extension is where a rebound after exit lands, so the episode sum contains the rebound. The extension length 21 equals the put tenor. It is a window literal, not a quoted probability.

## 10. Baselines, episodes, uncertainty

**B0.** P0. Always invested. Reference for every difference.

**B1. Volatility targeting.** Import `engine.vol_managed.vol_scalar` with `target=0.12`, `cap=1.0`, `floor=0.0`, `short=21`, `long=63`. The scalar ignores the warning. `cap=1.0` is the research helper's de-risk-only default (`engine/vol_managed.py:11-12`). The live conditions cap of `1.5` (I19) is not used, so B1 does not borrow. Pass the scalar series through I17 at `L = 1` and `cost_bps = 3.0`, with the same cash-yield preparation as every other row. B1's own protection sessions are the sessions whose live scalar is below 1.

**B2. Random timing with matched time in protection.** Built by `scripts/research/grey_deer_episode_samples.py` (I26). The module is on this base, but the function below is not in it yet. The contract below is the rule a later builder has to meet. The executing lane imports this function and does not ship a private substitute:

```
def matched_protection_masks(
    sessions: Sequence[date],
    on_mask: Sequence[bool],
    *,
    n: int = 200,
    seed: int = 20261013,
    block: int = 21,
) -> list[Sequence[bool]]
```

`on_mask` is the policy's live protection indicator on one slice. `k` is the number of true sessions. Each returned mask has exactly `k` true sessions and the same run lengths as `on_mask`, placed without overlap, starting only where the whole run fits. A draw that cannot place is rejected and redrawn. `n = 200`. Seed `20261013`. The `block` argument is accepted and must equal 21; the run lengths come from `on_mask`, and `block` is the maximum run the placer may split. This protocol's runs are not split, so a run longer than the session list rejects the draw. Masks are built inside one slice. The metric stored for B2 is the mean of the metric across the 200 masks. The 2.5 and 97.5 percentiles across the 200 masks are that baseline's dispersion.

While `matched_protection_masks` is absent from I26, B2's status is `BLOCKED_BUILDER_ABSENT`. The other tables are still produced. A gate that requires B2 stays `BLOCKED`.

**Episodes.** For a policy, an episode is a maximal run of live protection, extended 21 NYSE sessions past the exit decision, with overlapping extensions merged. The episode is defined from the trigger, the lag, and the calendar. It is not defined from price outcomes. The pullback preregistration's outcome-event cluster (`research/grey_deer/PULLBACK_PREREGISTRATION_2026-10-11.md:274-279`) is a different object and is not used here.

**Primary uncertainty: episode-clustered circular block bootstrap.**

- Order the episodes in time. The sequence wraps.
- Draw episodes with replacement until the drawn sessions number at least the slice length, then drop the tail of the last episode's sessions to the slice length. Session order inside an episode stays fixed.
- `B = 2000`.
- Policy draws use seed `20261013`. B1 draws use seed `20261014`.
- On each policy draw, recompute drawdown avoided against P0 on the concatenated sessions (paired: the same sessions for the policy and for P0).
- On each policy draw, recompute the signed episode-sum.
- The B1 comparison redraws B1's episodes independently and stores `policy_signed_sum - B1_signed_sum`.
- Report the 2.5, 50, and 97.5 percentiles of each stored statistic.

**Companion, display only.** `engine.validation.block_bootstrap_ci` on the policy's net series with `block=21`, `B=2000`, `seed=20261013`, `ann=252`. Its defaults (`B=5000`, `seed=7`, `ann=365`) are not used. It is not a gate. It answers a different question (a 21-day return block on Sharpe and max drawdown) from the episode bootstrap the gate uses.

Power floor: the primary claim is assessable at 8 or more protection episodes in the gate's sub-table. Below 8 the status is `UNDERPOWERED_DISCLOSED`. The tables are still written. Eight is a round literal fixed here. Ledger-length notes exist in the tree (I25, and the catalog note at `config/synapse.yml:1655-1664`). This draft does not repeat those counts and does not set the floor from them.

## 11. Multiplicity budget

Confirmatory comparisons, and the only ones that can change a status word. Four policies (P1, P2, P3, P4), three comparisons each, on the primary gate slice, `T_loud`, `L = 1`, `cost_bps = 3.0`:

1. Paired episode-bootstrap of drawdown avoided versus B0.
2. Episode-bootstrap of `signed_sum(policy) - signed_sum(B1)`.
3. Episode-bootstrap of `signed_sum(policy)` against the B2 mean.

Budget: 12. Each policy is judged on its own three comparisons. A pass on one policy is not a pass on another. No "best of four" selection is a further comparison, so the protocol reports every policy that passes and does not crown one.

Display families, each a repeat of the same 12, each barred from changing the status word:

| Family | What changes | Comparisons |
|---|---|---|
| S-caution | `T_caution` | 12 |
| S-lag | `L = 2` | 12 |
| S-cost | `cost_bps = 8.0` | 12 |
| S-half | `P1-half` in place of P1, other policies unchanged, so this family is the three P1-half comparisons plus the nine unchanged primary comparisons reprinted beside them | 12 |
| S-vintage | `CURRENT_VINTAGE` diagnostic | 12 |

Named comparisons: 12 confirmatory + 60 display = 72. The confirmatory budget is 12. Promoting a display cell is a new preregistration.

No alpha split is applied on top of the bootstrap percentiles. The budget is a selection budget. A later trial-ledger family name, if a later lane opens one, is `grey_deer_t19_costed_protection_v0`. This draft does not write `data/` and does not call `engine.trial_ledger`.

## 12. Promotion rule

Research display only. This draft grants no live capital authority. Model output never gains sizing or execution authority.

A primary cell's status word is one of:

| Status | Rule |
|---|---|
| `BLOCKED` | B2 is `BLOCKED_BUILDER_ABSENT`, or a kill in §13 fired, or the price path or the ledger failed a pre-check |
| `UNDERPOWERED_DISCLOSED` | Fewer than 8 protection episodes |
| `PASS_RESEARCH_DISPLAY` | All three of the following hold: the 2.5 percentile of drawdown avoided versus B0 is greater than 0; the 2.5 percentile of `signed_sum(policy) - signed_sum(B1)` is greater than 0; the 2.5 percentile of `signed_sum(policy)` is greater than the B2 mean |
| `NO_INCREMENT` | The cell is assessable and at least one of those three percentile tests fails |

`PASS_RESEARCH_DISPLAY` authorizes a results note under `research/grey_deer/` that copies these status words and the pre-registered tables. It does not authorize a live gross change, a radar-band change, a calibration write, a customer-surface change, an envelope policy, an authority boolean, an order, or a size.

The terminal-multiple difference is printed in the same table as the three tests. It is not one of the three tests.

## 13. Kill criteria

Any one of these sets the run to `KILLED` (tables may still be written; the status word is not a pass):

1. I4 cannot be read, or a used `asof` fails `lib.nyse_calendar.is_session`.
2. I11 is empty, or its basis is anything other than RAW `close_raw`.
3. A price is filled from Yahoo or from `equity_alloc.index_close`.
4. The lag is 0 or the shift in I17 is bypassed.
5. A weight, strike factor, tenor, cost, spread, seed, trigger set, episode length, or bootstrap count in this file is changed after any outcome on these policies has been computed.
6. A display family in §11 is reported under the primary status word.
7. A `CURRENT_VINTAGE` table is described as an issued forecast record.
8. A result is written into the live envelope, or any authority boolean is edited.
9. B2 is produced by any function other than I26.
10. The put formula is replaced by a scraped chain, a vendor mark, or a stored option price.
11. Cash carry uses `DGS3MO` or `DFF` after this file has named `DTB3` as the only cash series.
12. The radar probability table or any hit rate, return, or skill score is copied into the results note from a prior file.

`UNDERPOWERED_DISCLOSED` is the status when the episode floor fails. It is a killed promotion claim. It is not a deleted table, and it is not item 5.

## 14. Known exposure

File names only. This draft does not repeat statistics from them.

Text encountered while writing this draft:

- `engine/risk_radar.py`
- `engine/conditions.py`
- `engine/equity_alloc.py`
- `engine/validation.py`
- `config.yml`
- `config/dataset_registry.yml`
- `config/synapse.yml`
- `research/grey_deer/PULLBACK_SOURCE_RIGHTS_QUALIFICATION_2026-10-11.md`
- `research/grey_deer/PULLBACK_PREREGISTRATION_2026-10-11.md`
- `research/grey_deer/RISK_RADAR_ISSUED_WARNING_DURATION_2026-09-24.md`
- `research/grey_deer/GREY_DEER_CONTINUATION_HANDOFF_2026-10-11.md`
- `research/grey_deer/RISK_RADAR_EPISODE_WARNING_PATH_RESULTS_2026-09-21.md`
- `reports/vector-calibration.md`
- `reports/exit-policy-horserace.md`
- `docs/CLAIM_ACCOUNTABILITY.md`
- `docs/ORACLE_RED_QUEEN_INTERFACE.md`

Results files present under `research/grey_deer/` at this base. Names only. Not opened for this draft, except the one path listed in both groups because a search hit one line of it:

- `research/grey_deer/gd1/GD1_RESULTS_AND_ADJUDICATION.md`
- `research/grey_deer/gd1c/GD1C_RESULTS_AND_ADJUDICATION.md`
- `research/grey_deer/PULLBACK_STAGE1_RESULTS_2026-10-11.md`
- `research/grey_deer/PULLBACK_STAGE1_RESULTS_2026-10-11.json`
- `research/grey_deer/pullback_stage1_r1/PULLBACK_STAGE1_RESULTS_2026-10-11.md`
- `research/grey_deer/pullback_stage1_r1/PULLBACK_STAGE1_RESULTS_2026-10-11.json`
- `research/grey_deer/RISK_RADAR_CAUTION_PERSISTENCE_RESULTS_2026-09-21.md`
- `research/grey_deer/RISK_RADAR_DISPLAYED_PROBABILITY_AUDIT_RESULTS_2026-09-22.md`
- `research/grey_deer/RISK_RADAR_EPISODE_WARNING_PATH_RESULTS_2026-09-21.md`
- `research/grey_deer/RISK_RADAR_GATE_LATENCY_RESULTS_2026-09-21.md`
- `research/grey_deer/RISK_RADAR_PROBABILITY_AUDIT_RESULTS_2026-09-20.md`
- `research/grey_deer/RISK_RADAR_PROBABILITY_WALKFORWARD_RESULTS_2026-09-23.md`
- `research/grey_deer/RISK_RADAR_REPLAY_PARITY_RERUN_RESULTS_2026-09-21.md`
- `research/grey_deer/RISK_RADAR_REPLAY_PRICE_INTEGRITY_RESULTS_2026-09-20.md`
- `research/grey_deer/RISK_RADAR_STATE_LADDER_CALIBRATION_RESULTS_2026-09-21.md`

Further exposures, as statements about this drafting session:

- The issued ledger is known from secondary notes to be a short nightly record. The episode floor was fixed at 8 anyway.
- `DTB3` used as a continuous rate is a basis approximation.
- `q = 0` omits a dividend yield. No qualified dividend series is in the input register.
- The half-spread `0.0015` is assumed.
- The one-way cost `3.0` bps is the equity-allocation harness default, not a measured SPY spread from this work.
- B1's scalar and the radar warning are different mechanisms. Beating B1 is part of the gate for that reason.
- I26 does not export `matched_protection_masks` yet, so B2 cannot be built on this base.

## 15. What this draft does not do

- It does not compute a return, a drawdown, a hit rate, a skill score, or a bootstrap.
- It does not read `data/`, a price store, or a vendor endpoint.
- It does not freeze itself. The seat freezes a later revision.
- It does not edit a frozen file. The grey-deer research files that already existed, and the stage-1 and panel scripts, stay as they are.
- It does not grant live capital authority.
