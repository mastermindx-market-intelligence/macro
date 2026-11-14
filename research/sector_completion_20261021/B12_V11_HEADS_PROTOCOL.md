# B12 v1.1 — predeclared protocol: four forecast heads + seven comparators

**Status: PREDECLARED. No head, comparator or outcome in this document had been computed when it
was committed.** Results go in `B12_V11_HEADS_RESULTS.md` and
`b12/v11_heads_result.json`, written by `b12/v11_heads.py` at a later commit. Any change to this
protocol after results exist is a deviation: it must be listed in the results file with its reason,
and the head it touches is judged under the protocol as committed here.

Lane 8 (analytics/B12), Sector Intelligence v1.1 amendment, carrier Macro #10924.
Governing sources: v1.1 handoff §4C/§5 step 5; Prophet v5.1 integration amendment §7, §11 (lane 8),
§12 SI02/SI04/SI08/SI12, §13 SP10/SP11/SP21/SP22; Prophet production masterplan §18.5–§18.7.

## 0. What this protocol may and may not establish

- It may give each of four heads one disposition: `QUALIFIED_RESEARCH`, `WITHHELD_FAILED`,
  `WITHHELD_UNDERPOWERED` or `NOT_EVALUATED`. Each head is judged **alone**. Passing one head
  qualifies none of its siblings. Failing one head withdraws only that head.
- The historical W4.2 4/6 verdict is not an input and authorizes nothing here.
- Comparator results are **descriptive economic evaluation**. They are not a qualification. They do
  not establish alpha, selection skill or a promotion. There is no universal Sharpe, win-rate or
  beta threshold in this document.
- Nothing here sizes, ranks, gates, trades or escalates. `may_rank / may_gate / may_size /
  may_trade / may_escalate` stay false. No new provider dataset. No ledger write. No nightly or
  render-path compute: the script runs off the render path, by hand.
- Wording law: raw relative strength is not estimated alpha. Positive selection contribution is not
  evidence of portfolio skill. Historical duration is not remaining upside.

## 1. Population, basis and point-in-time rules

- **Market:** US only. HK and mainland China heads are `NOT_EVALUATED` (no native tapes, calendars,
  costs or benchmarks in this lane's scope).
- **Universe:** the 11 Select Sector SPDR ETFs XLK XLE XLF XLV XLY XLP XLI XLB XLU XLRE XLC,
  each from its own first traded session (XLRE 2015-10, XLC 2018-06). No back-fill before listing.
- **Native basis and membership:** each ETF is a traded vehicle, so its price is the as-traded
  basis and its membership is the fund's own on each date. No constituent roster is reconstructed.
  The thematic baskets in `data/baskets/membership.json` are built from today's roster
  (`history_mode: reconstructed`); they are **excluded** from every head and comparator, and their
  records carry `membership_not_point_in_time` for all four heads.
- **Price tapes:** `data/yahoo/<T>.parquet` on `main`. `close_price` (unadjusted) drives turns;
  `close` (total-return adjusted) drives returns. Benchmark SPY `close`. Cash BIL `close` from
  2007-05-30; before that cash earns 0 (disclosed). Adjusted-price vintages are not retained, so
  returns use today's restated tape; this is a stated limit, not PIT price knowledge.
- **Turns:** `engine.cycle_ontology.detect_turns`, ZigZag v2, pct 14, basis `close_price`, on the
  full tape. A turn is usable at decision date `t` only if its `confirmed_at <= t`. The pivot date
  is the event date; `confirmed_at` is the first-known date. **PIT check (must pass before any
  head is scored):** at every decision date of every ETF, `detect_turns` on the tape truncated at
  `t` must return exactly the full-tape turns with `confirmed_at <= t` (same dates, kinds,
  confirmed_at). Any mismatch aborts the run.
- **Decision dates:** for each ETF, every 20th completed session starting at its 505th session
  (two years of warm-up). Information set = closes through `t`. **Entry** = close of `t+1` (no
  same-close fill). **Horizon** = 20 completed sessions after entry, ending at the close of `t+21`.
  Windows therefore do not overlap within an ETF. A window whose `t+21` is past the tape end is
  immature and dropped (not imputed).
- **State at t (the only conditioning variables):** `direction` = up if the last confirmed turn is
  a trough, down if a peak (no confirmed turn → abstain); `age` = sessions from that turn's pivot
  date to `t`, bucketed `A1 < 63`, `A2 63–188`, `A3 >= 189`. Cell = direction × age bucket
  (6 cells). `sigma20` = std of the last 252 daily TR log returns × sqrt(20), known at `t`.

## 2. The four heads (one primary specification each; no alternatives searched)

| head | target (per window) | forecast | score | baseline |
|---|---|---|---|---|
| H1 remaining-return distribution | `r = R_etf − R_spy − 0.0010`: 20-session TR return of the ETF minus SPY's over the same entry→exit closes, less a 10 bp round trip; percentage-point difference, not alpha | the cell's empirical quantiles q ∈ {0.10, 0.25, 0.50, 0.75, 0.90} | mean pinball loss over the five q | same quantiles of the unconditional training pool |
| H2 adverse tail | `1{min over the 20 sessions of the cumulative TR return from entry <= −1.5·sigma20}` (absolute) | cell frequency, (k+1)/(n+2) | Brier | unconditional pool frequency, same smoothing |
| H3 target-before-invalidation | `1{cumulative TR return from entry reaches +1·sigma20 before it reaches −1·sigma20, within 20 sessions}`; both on the same close, or neither within 20 sessions, count as 0 (competing events: target, invalidation, neither are all retained in the counts) | cell frequency, (k+1)/(n+2) | Brier | unconditional pool frequency |
| H4 transition time | `1{the next turn's confirmed_at falls in (t, t+20]}` — first-known date, not pivot date | cell frequency, (k+1)/(n+2) | Brier | unconditional pool frequency (every ETF at every decision date: the correct from-today at-risk population, not panel rows) |

## 3. Fitting: time-respecting, leave-one-sector-out

- For a test window of ETF `s` at `t`, the training pool is every window of the **other ten** ETFs
  whose exit close `t'+21 <= t` (matured strictly before the decision). ETF `s` never trains its own
  forecast (peer exclusion). Baseline and model use the same pool.
- **Abstention:** if the test window's cell has fewer than 30 training windows, or no confirmed
  turn exists, the model abstains. Abstained windows are excluded from both model and baseline
  scores and counted in coverage.
- **Test set:** windows with decision date `t >= 2008-01-01`.

## 4. Uncertainty, multiplicity, pass/fail

- Skill `S = 1 − score_model / score_baseline` (pinball for H1, Brier for H2–H4), on non-abstained
  test windows pooled over ETFs.
- Dependence: ETFs share dates. Resample **calendar years** of decision dates (all ETFs' windows in
  a year move together), 2,000 draws, seed 11. Report the 90% percentile interval and a one-sided
  bootstrap p = share of draws with `S <= 0`. Report n windows, n distinct decision dates and n
  years.
- Multiplicity: the four primary p-values are adjusted with Benjamini–Hochberg at q = 0.10.
- **A head is `QUALIFIED_RESEARCH` only if all hold:**
  1. PIT check passed;
  2. coverage (non-abstained / all test windows) >= 0.80;
  3. n non-abstained test windows >= 200;
  4. the 90% interval lower bound of `S` > 0;
  5. it survives BH at q = 0.10;
  6. calibration on the test set: H1 — empirical share of `r` inside the forecast [q0.10, q0.90]
     band is in [0.72, 0.88]; H2–H4 — |mean forecast − observed rate| <= 0.03 and the
     forecast-decile reliability slope (OLS of outcome on forecast over the test windows) is in
     [0.5, 1.5];
  7. skill is positive in at least 60% of test years with >= 10 non-abstained windows.
- Otherwise: `WITHHELD_UNDERPOWERED` if rule 2 or 3 fails (the data cannot answer at this bar);
  `WITHHELD_FAILED` for any other failing rule. Every failing rule is named in `reasons`.
- **What a QUALIFIED_RESEARCH head may do in the payload:** nothing numeric yet. The live Sector
  Cycles record uses the legacy v1 detector and has no v2 epoch identity (B12 Q8), so a live
  record cannot be matched to the qualified state definition. Its emitted status is
  `withheld` with reason `live_state_not_protocol_epoch` until the live record carries the v2
  `price_c4414dcb`-equivalent state. A failing head is `withheld` with its failure reason.

## 5. Seven comparators (Evaluation owner contract; descriptive)

Common rules: 20-session rebalancing on the decision dates of SPY (first at SPY's 505th session,
test from 2008-01-01); signal at close `t`, execution at close `t+1`; 5 bp per side on every
traded weight change (ETFs; spreads + commissions proxy), BIL TR on uninvested weight; no leverage,
no shorting. Sectors enter a rule only on and after their own 505th session. A rule with no
eligible holding is **no-entry** (100% cash) and counted. A signal on the last session (no `t+1`)
is **no-fill** and counted.

| # | comparator | rule here | status rule |
|---|---|---|---|
| C1 | passive investable market | 100% SPY (vehicle, not the index; expense inside TR) | evaluated |
| C2 | simple participation rule | SPY if SPY close > its 200-session mean at `t`, else cash | evaluated |
| C3 | sector allocation only | equal weight over sectors whose last confirmed v2 turn is a trough at `t`; cash if none. Neutral reference: equal weight over all eligible sectors (C3-EW) and the **exposure-matched** blend `w·C3-EW + (1−w)·cash`, `w` = C3's mean invested fraction | evaluated |
| C4 | member selection only | needs point-in-time sector constituents | `unavailable: no_pit_constituent_membership` (today's holdings would be survivorship-biased) |
| C5 | joint sector and name | needs C4's input | `unavailable: no_pit_constituent_membership` |
| C6 | exact incumbent Prophet | needs the incumbent Prophet policy/evidence record of its source era | `unavailable: incumbent_record_not_in_lane_scope` (Terminal/Prophet owner) |
| C7 | independent emergence | of sectors **not** in the top 3 by trailing 63-session TR return vs SPY at `t` that **are** top 3 over the next 63 sessions (emergers), the share C3 holds at `t`, against the share of all non-top-3 sectors C3 holds (base rate) | evaluated (recall, descriptive) |

Metrics for C1–C3 and the references: annualized TR, volatility, excess over cash, max drawdown,
beta and tracking error vs C1, upside/downside capture vs C1 (only months where |C1| >= 0.5%;
reported `unavailable` if the denominator sum's absolute value < 1%), mean invested fraction,
annual turnover, costs paid, no-entry and no-fill counts. Uncertainty: year-block bootstrap
(2,000, seed 11) 90% interval of annualized excess vs C1 and vs the exposure-matched reference.
**Failed leaders:** at each date, sectors in the trailing-63 top 3 that land in the bottom half
over the next 20 sessions; report their count and the share C3 held. **Rebounds:** the next 20
sessions after each C1 drawdown of >= 10% from peak; report C3's and C2's participation
(return ratio vs C1, unavailable on a near-zero C1 denominator).

## 6. Reproduce

```
python3 research/sector_completion_20261021/b12/v11_heads.py --tape-dir <dir containing data/yahoo> \
    --out research/sector_completion_20261021/b12/v11_heads_result.json
```

Inputs are the tracked `main` parquets listed in §1 (on a sparse tree, extract them with
`git show origin/main:data/yahoo/<T>.parquet`). The script is deterministic for a given tape.
