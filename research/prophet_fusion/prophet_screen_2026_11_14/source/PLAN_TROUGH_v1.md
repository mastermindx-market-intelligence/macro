# Plan: trough entry v1 (RD, 2026-11-14; the desk's first line)

**Governing row:** ceo-trough-entry-mainline (CEO, ~05:30Z, quoting the Chairman). Method and statistics are ruled jointly with the Radar leader. The leader hashes this plan before any worker reads an outcome.

**Question.** Group and stock confirmation come late: much of the move is already priced in. The Terminal grey dot fires at the trough, on a momentum re-uptick. It catches very good entries, but it also gives false calls. The question: which features, all known at the dot's bar, separate a real trough from a false one? And how much earlier than the house T1 entry does the dot get in, and at what cost? The scoring rewards earliness. There is no matching on lateness.

## 0. Rules carried over unchanged
- **Discovery years only.**
  - Prices dated 2024-01-02 or later are never loaded; an assert enforces it.
  - SCREEN: 2013-01-02..2019-12-31.
  - HOLD: 2020-01-02..2023-05-31, one read only, after stage 1 (ADDENDUM_HOLD_R5 + H1-H3 style).
  - Forward labels may run to 2023-12-29. A 63-session label that would cross that date is dropped and counted.
- **Panel.** Rev 5 per CONSUMER_NOTES C1-C5 and U1.
  - The counting universe is dated S&P 500+400 members. The S&P 600 is description only, "from 2019-12 only".
  - WH before 2018-05-21 is excluded and counted.
  - Coverage grades by entry year: 2013-17 are survivor-biased and labelled; 2018-23 are usable.
- **Inference.** The month is the unit. The permutation p is the counting p; z only orders. BH at q .10. The MDE is stated first (Stage 0). Singles are screened; pairs are description.
- **Never open:** `sealed_post2019/`, any `*SEALED*` file, `pivots.parquet`, `catalogue/out/`, `catalogue/out_boundary/`, `catalogue/two_speed/astra/`, SI's stored per-group files.
  - No network, no secrets, no git. Raw prices are never written to an output folder.
  - Tickers and FF codes only.
- **F1 and its extension** (RUN_NOTES_V3) apply here. These features cannot make a HOLD claim:
  - group tier/regime, D-like, SPY-state and basket-arm features;
  - anything with |rho| ≥ .5 against D, index state or TAILWIND (rho on SCREEN).
  They are still screened, and flagged F1_hold_excluded.

## 1. Events
- **G3, the house dot.**
  - Import `engine/stock_identity/replay/grey_dot.py` read-only from `ext/macro_main_e999086d`, and print its sha256. The engine is never edited.
  - Use the Terminal locked-spec port: `_terminal_dot_mask` / `terminal_fires`. That is a 3D StochRSI K×D bullish cross with D < 20 within 8 bars, and a strictly rising 2D RSI-MACD histogram, PIT-joined.
  - The event date is **known_ts**, the close of the bar on which the dot was first knowable. The 3D bar label is display only.
  - Carry the house `in_washout_context` flag (the amber promotion) as a feature, not as a filter.
- **Hindsight guard (W2 warning).**
  - On 300 random dots, recompute the mask from closes truncated at known_ts. The dot must still be there on that same bar.
  - Print the agree count. Any dot that only exists with later data is dropped and counted.
  - Also report parity against the house function on the 3 house names (NVDA, NFLX, TSLA, 2013-2023) as fire-date agreement counts.
- **Timeframe analogues, the desk's own spec (labelled "desk analogue, not house").**
  - The same legs on other grids, with the rising-histogram leg one grid faster:
    - **G1:** 1D cross, rising 1D histogram (same bar);
    - **GW:** weekly cross, rising 3D histogram;
    - **G2W:** 2-week cross, rising weekly histogram.
  - The completed-bucket and PIT rules are those of `_period_last_session`.
- **Eligibility.** The stock is a dated 500+400 member on known_ts, has a valid close, and is not a share-class drop.
  - A new dot on the same stock and grid within 5 sessions of a previous one is folded into the earlier one; count the folds.
- **Sample check (60 random names).** 4.5 G3 dots per member-year. Expected G3 events in 500+400:
  - about 28,000 in SCREEN;
  - about 14,000 in HOLD.

## 2. Labels (earliness)
The member panel is closes only. So "ATR" here means ATR_c: the 14-session mean of |Δclose|, printed as a close-only proxy. The trough low is the lowest close in the 10 sessions ending on known_ts.
- **PRIMARY real63:** the trough low is not undercut by more than 1.0 ATR_c within 63 sessions after known_ts. real21 is the same over 21 sessions. k = 0.5 and k = 2.0 are description.
- **Distance from the true swing low**, as sessions and as percent:
  - the true swing low is the lowest close in [known_ts − 21, known_ts + 63];
  - a signed lag (dot before or after the low) is printed.
- **Path.**
  - MAE: the worst close-to-entry move after entry, at 21 and 63 sessions.
  - MFE at 21 and 63 sessions.
  - Reward/risk = MFE/|MAE|.
  - Forward returns: fwd21 and fwd63, raw and relative to SPY.
- **Against the house T1 on the same swing.**
  - Find the first house stock T1 entry (ENTRIES_stock_t1 definition, tier_stream) within 63 sessions after the dot, with no undercut of the trough low before it.
  - Captured move = close(T1)/close(dot) − 1.
  - Cost: the share of dots with no T1 that undercut first (extra false calls). Also the reverse case: T1 entries with no dot in the 21 sessions before.
  - Pooled description, plus the same by personality tercile.

## 3. Features (all known at known_ts; wide and cheap)
Each item is a few columns. Any feature that needs OHLC or volume prints "not built: closes only" in NOT_BUILT.md. That covers the true range, range contraction, volume climax and dry-up, and gap fills. It is not faked.
- **a. Personal depth:**
  - drawdown from the 252-session high, in ATR_c units;
  - its percentile among this stock's own prior dot drawdowns (expanding window, prior dots only);
  - sessions with 3D StochRSI D < 20 in the current spell, against the stock's own prior median;
  - RSI14 at the dot against the stock's own prior-dot distribution.
- **b. Personality.** A trailing 756-session scale (504 minimum; prior data only):
  - trend persistence (Hurst/variance-ratio proxy);
  - beta to SPY;
  - volatility;
  - share of days above the 200-day;
  - median depth and duration of prior 10%+ drawdowns.
  The first principal component, computed on SCREEN, is the "compounder ↔ cyclical" scale. Its loadings are printed.
  Shrinkage: each stock's own statistic is shrunk to its personality-tercile mean with weight n/(n+k), where n is its prior dot count and k = 10.
- **c. Timeframe match:**
  - the state of each grid (1D, 3D, W, 2W): D < 20 at the dot, or within 8 bars;
  - weekly StochRSI rolled over from above 80 within the last 8 weekly bars;
  - interactions with the personality scale, as description, rather than screened pairs.
- **d. Dot order:**
  - the number of G3 dots since the last weekly StochRSI top (cross down from > 80);
  - first versus later dots;
  - bullish divergence: a lower close-low than the prior dot together with a higher 3D RSI.
- **e. Seller exhaustion (closes only):**
  - second difference of the 10-session price slope;
  - 10-session SD / 63-session SD (contraction);
  - largest single down-day in the last 10 sessions, in ATR_c units, and the sessions since it.
- **f. Alone or together.** For the 21-session decline into the dot, the share explained by:
  - the market (SPY beta × SPY return);
  - the group (own basket, R44 assignment);
  - what is left, which is idiosyncratic.
- **g. Group washout.** On the own basket (dated 500+400 members, R44, PLAN_PASS2_BASKETS steps 1-3):
  - the share of members with 3D D < 20;
  - the share printing a G3 dot in the 10 sessions ending on known_ts ("dot breadth"), excluding the stock itself;
  - the basket's own G3 dot within 10 sessions.
- **h. Fear state.** Index-level inputs from `data/repo`, `data/yahoo`, read-only, truncated:
  - VIX percentile (252-session);
  - the VIX curve's term structure: inverted within 10 sessions and now normal;
  - vol-of-vol = the 21-session SD of VIX daily changes, its 63-session percentile and its 5-session slope;
  - credit = the 21-session change in HYG/IEF.
  - Slot `vol_forecast` is reserved, empty.
- **i. Index state and sell-off type:**
  - FALLING (SPY 63d < 0 and ≥ 5% below the 252d high);
  - the regime/type labels already built under `v4/regime/` (TYPE_SPEC_v1 + A/B), read-only;
  - D (the cross-sectional SD of the 27 ETFs' 21-session returns).
  All of these are F1_hold_excluded on STK by rule.

## 4. Second table: dot breadth as a group trough signal (GRP-DOT)
- **Unit:** one of the 27 baskets × day.
- **Event:** basket dot breadth (the share of members with a G3 dot in the last 10 sessions) crosses up through its own SCREEN 80th percentile while SPY's 21-session return is ≤ +1%. Refractory 21 sessions.
- **Labels:** the basket's return relative to SPY at 21 and 63 sessions. Base: the same basket on non-event days in the same month.
- **Description:** the same with the 27 ETFs (ETF-carried) and FF12.
- MDE first, as with every table.

## 5. Stage 0 (before any feature × label association)
For each of G3, G1, GW, G2W, plus GRP-DOT, print:
- the event count, SCREEN months, events per month and the PRIMARY base rate;
- deff = 1 + (m̄ − 1)·ICC, where the ICC is within calendar month and within basket × day (the larger is used);
- the effective n;
- the planning SE from 2000 whole-month bootstraps × sqrt(6) for top versus bottom tercile;
- the MDE (80%, two-sided) at the BH rank-1 bound and at the Bonferroni bound.

Then, per table:
- **Stage 0 stop:** a singles MDE above 15 pp ends that table at Stage 0. The numbers go to the leader first.
- Also print FEATURES_TROUGH.csv with its hash and m per table.

## 6. Stage 1 screen
- **Singles.** Each feature splits at its SCREEN terciles, top against bottom, on real63 (PRIMARY), with a z and the month-block permutation p.
  - The permutation keeps whole months within universe × personality tercile, 20,000 draws for the class-level family.
  - BH q .10 within table.
- **Description only, not counting:** MAE, MFE, distance-from-low and the T1-comparison numbers.
- **Coverage.** Every number carries the coverage grade and the evidence grade (≥ 20 tested, 8–19 limited, < 8 case-based).
- **Survivors** go to SURVIVORS_SCREEN with a dedup list: |rho| ≥ .7 to a stronger survivor is a duplicate.
- **Closing line:** `TROUGH_S1 COMPLETE g3=<n> mde=<pp> surv=<k> <sha8>`.

## 7. Staffing and order
1. **W-EVENTS (Sol):** events, hindsight guard, labels and the T1 comparison, then Stage 0. It stops after Stage 0 until the leader replies.
2. **W-FEATURES (Sol):** features a–i once the events are hashed. It may run in parallel from the event file, before any label is joined.
3. **W-SCREEN:** stage 1 on all tables that pass.
4. **Astra (staffed by the Prophet lead):** TROUGH-SYN-1, TYPE-1, DIG-1 and VOL-1. Each proposes; a desk worker reproduces before anything counts. Prompts contain nothing dated 2024 or later. Any desk-reproduced proposal joins the screen as a separate batch, folded into the one HOLD read.
5. **Synthesis log** (`catalogue/SYNTHESIS_LOG.md`): after every result batch, one Astra Pro run proposes the next three hypotheses; the RD adds its own; the best join the next screen.
