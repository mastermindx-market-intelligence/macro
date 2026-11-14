# Pivot catalogue: specification (Research Director, written 2026-11-12, before any build)

This is the label set for the identification target (principal ruling, 2026-11-12). One written rule is applied after the fact. It reads prices only. There is no signal and no outcome join, so no ledger row is needed to build it. Reads that use it are another matter: any test that scores a signal against it writes its row first.

## 0. Hard boundary
- **Inputs are truncated at 2023-12-29 before the rule runs.** No price dated 2024-01-02 or later is loaded.
  - A pivot whose confirmation would need a later price is marked `censored=1` and is never counted as a pivot.
- Pre-2020 is included and labelled by block:
  - `block = PRE` (before 2020-01-02);
  - `block = D` (2020-01-02 to 2023-12-29).
- Do not open `/home/ubuntu2/tmp/rotation-core/data/french/sealed_post2019/`. Raw vendor rows are never committed or uploaded anywhere.

## 1. Series (each its own universe)
- **U1 broad equity, absolute:** SPY, RSP, QQQ, IWM, MDY, DIA. Use ^GSPC for SPY before its start.
- **U2 sectors, absolute and relative:** the 11 SPDR sectors (XLC and XLRE from their start). Each is taken in two ways:
  - absolute;
  - relative, as log(ETF / SPY).
- **U3 groups:** the EQUITY_27 group ETFs, absolute and relative to SPY. Group-weeks with `priced_share < 0.9` are irrelevant here, because we use ETF prices, not members.
- **U4 cross-asset, absolute:**
  - TLT, IEF, SHY, TIP, LQD, HYG, GLD, DBC/GSG, UUP (if held), EFA, EEM, EWJ, FXI, INDA, the country ETFs held, and VNQ;
  - style pairs where held (IWD/IWF, MTUM, USMV, QUAL if present; skip missing).
- **U5 risk ratios (risk-on/off in relative terms):**
  - log(SPY/TLT), log(HYG/IEF), log(SPY/GLD);
  - cyclicals versus defensives: log(equal-weight XLY+XLI+XLF / equal-weight XLP+XLU+XLV);
  - log(IWM/SPY), log(EEM/SPY).
- **U6 FRED levels** (repository store, as held):
  - HY OAS (BAMLH0A0HYM2) and BAA−10y in bp;
  - DGS10 and DGS2 in bp;
  - the broad dollar (DTWEXBGS).

  Pivot levels in the series, not prices. Apply no publication lag: this is an after-the-fact label. Lags apply to the features only.

Missing tickers are skipped and listed. Data come from `/home/ubuntu2/tmp/rotation-core/data/yahoo/` and the FRED repository store via the existing loaders (`v4/panel/loader.py`, `v4/features/`). Never print vendor keys.

## 2. The swing rule (one rule, two tiers)
- Work on log price, or on the level for U6.
- σ_a is the asset's annualised daily-return volatility, the median of 252-session rolling values over **2005-01-03 to 2019-12-31**. If the history is shorter, use the first 3 years available before 2020. Record which.
  - Pre-2020 volatility only, so that the threshold carries no D information.
  - For U6, σ_a is the same median of the 252-session std of daily level changes × √252, in bp.
- Tiers:
  - **Minor:** threshold θ = 0.25 · σ_a, for example SPY ≈ 4–5 %.
  - **Major:** θ = 0.50 · σ_a.
- Rule, per tier (classical zig-zag, Pagan–Sossounov style):
  - **Starting:** take the first 252 sessions and the extreme of that window as the provisional starting state.
  - **Peaks:** in an up-leg, track the running maximum M. A **peak** at the date of M is confirmed on the first session where log P ≤ log M − θ. That date is `confirm_date`. Then switch to a down-leg.
  - **Troughs:** symmetrically for a **trough**.
  - **Minimum spacing:** consecutive turns must be ≥ 10 sessions apart. If not, keep the more extreme turn and continue.
  - **No other rules:** no smoothing, and no rule fitted to an outcome.
- Fields per pivot:
  - `series`, `universe`, `kind` (peak/trough), `tier`, `date` (the turn), `confirm_date`, `confirm_lag` (sessions);
  - `prior_leg_size`, `next_leg_size` (to the next confirmed turn, or censored), `next_leg_sessions`;
  - `block`, `censored`, `sigma_a`, `sigma_window`.

## 3. Pivot types (derived columns)
- `risk_off` for:
  - a peak in U1 absolute;
  - a peak in the U5 ratios, with the ratio oriented risk-on up: SPY/TLT, HYG/IEF, cyclicals/defensives, IWM/SPY, EEM/SPY;
  - a trough in HY OAS or BAA−10y.
- `risk_on`: the mirror image of `risk_off`.
- `leadership_start` / `leadership_end`: a trough or peak in U2/U3 **relative** series.
  - Also carry the existing mechanical top-3 rank events from `v4/w0/out/labels_rotation_events.parquet` as a separate type `rank_change` (do not recompute).
- `asset_turn`: a peak or trough in U4 absolute, by asset class (rates, credit, commodity, FX, international, real estate).

## 4. Date clusters
- **Algorithm:** within each `kind × type`, sort the turns by `date`. Turns within 10 sessions of the previous turn join its cluster (single linkage).
- **Report:** the cluster id, the size, the universes present, and the date span.
- **Counting:** the effective independent count for any test is the number of clusters, not the number of turns.

## 5. Outputs (to `v4/catalogue/out/`, derived tables only)
- `pivots.parquet`: one row per pivot, both tiers, all fields above plus `cluster_id`.
- `clusters.parquet`.
- `COUNTS.md`: counts by universe × kind × type × tier × block, as turns and as clusters. Include the median confirm_lag and the median next_leg_size. Highlight the D block's major- and minor-tier cluster counts for `risk_off`, `risk_on`, `leadership_start` and `leadership_end`.
- `SKIPPED.md`: missing series and short histories.
- Tests in `v4/catalogue/tests/`:
  - the zig-zag on synthetic series with known turns;
  - truncation: no input date ≥ 2024-01-02;
  - censoring;
  - minimum spacing;
  - σ from pre-2020 only.
- **Sanity check, reported, not tuned:** the SPY major tier on D should include turns near 2020-02-19, 2020-03-23, 2022-01-03 and 2022-10-12. Report the rule's actual dates, whatever they are. **Do not change θ after seeing the dates.** Any proposed change goes to the Director in writing, and the spec is versioned.

## 6. Amendment A1 (principal ruling, 2026-11-12): hold-out boundary count, labels only
The principal will decide where the hold-out boundary sits. For that decision only, run the **same rule unchanged** (same θ from 2005–2019 σ, same spacing and clustering) a second time on prices **through the latest date held**, as a separate run.
- **Output:** only `v4/catalogue/out_boundary/BOUNDARY_COUNTS.md` and `boundary_counts.csv`. They give the pivot counts and date-cluster counts by type (`risk_off`, `risk_on`, `leadership_start`, `leadership_end`, `asset_turn`) × tier, on each side of three boundaries: **2024-01-02, 2025-01-02 and 2025-07-01**. Also state the last date held per universe and the number of right-censored turns per side.
- **Post-2023 rows stay out of desk inputs:** they never enter `out/pivots.parquet` or any other desk input. If a row-level file is needed to compute the counts, keep it in `out_boundary/` and name it `SEALED_LABELS_DO_NOT_JOIN.parquet`.
- **Labels only:** no feature, signal, score or return is computed on, or joined to, any post-2023 date. The desk's sealed block stays at 2024-01-02 until the principal rules.

## 7. Amendment A2 (principal, 2026-11-12 ~07:00Z): three primary pivot families (Chairman's frame)
The rule (§2), θ, spacing and clustering are unchanged. A2 adds series and three derived **primary family** cuts. All other types stay in the catalogue as secondary.

**New series (U7, ratio, oriented risk-on up):**
- Cap-weighted: log(XLK / EW(XLP,XLU,XLV)), log(SMH / EW(XLP,XLU,XLV)), log(IGV / EW(XLP,XLU,XLV)), log(QQQ / EW(XLP,XLU,XLV)).
- Equal-weighted: log(RSPT / EW(RSPS,RSPU,RSPH)) and log(RSP / SPY) (breadth of the index itself).
  - Fetch RSPT, RSPS, RSPU and RSPH (pre-2023 history under the old RYT/RHS/RYU/RYH listings, where Yahoo carries it), plus SPHB and SPLV, through the existing free Yahoo route into `data/yahoo/`. This needs no spend, and no raw file is committed.
  - Truncate at 2023-12-29 at load.
  - If a ticker cannot be fetched, the fallback is an equal-weight member index from the v4 member panel, labelled `hindsight_members`. List the fallback in SKIPPED.md.
- log(SPHB / SPLV) where held.
- The rule applies to U7 as to U5. σ comes from pre-2020 data (or the first 3 years before 2020).

**Primary family cuts** (columns on `pivots.parquet` plus a section each in COUNTS.md):
- **F1 `beta_tech_vs_defensive`:** every peak and trough on U7, cap-weighted and equal-weighted reported side by side. A peak means rotation into defensives; a trough means rotation back into high-beta technology.
- **F2 `rotation_out_onset`:** a **peak** on a U2/U3 relative series (absolute and relative versions are both kept) where the series was a **leader** at the peak date.
  - A leader means: its 126-session relative return was in the top third of its universe at the turn date. That uses only data up to the turn date.
  - This is the "do not get hit" call.
- **F3 `durable_washout_bottom`:** a **trough** on a U2/U3 series (relative and absolute both kept) where:
  - (a) the prior leg was a decline of at least θ_major, i.e. sold off; and
  - (b) **durable** holds: no close below the trough for **63 sessions** after the trough date.
  - Durability is a label property known only after 63 sessions. Troughs whose 63-session window reaches past 2023-12-29 are `censored_durable=1` and not counted.
  - Also report the count at 21 and 126 sessions as a sensitivity. **63 is primary and is fixed now.**
  - Also count non-durable troughs (failed washouts). They are the knife-catching cases that the condition sets must avoid.
- Theme and subsector versions of F2 and F3 are added only when the SI side's merged theme/subsector series arrive. Their floors apply: breadth share at ≥10 members, an index only with ≥5 priced members.

**Dispersion regime (a column only, not a filter):** the cross-sectional std of 63-session returns across the 11 sectors on each pivot date. Tercile cut-points come from 2005–2019 only. Values are `low`, `mid` and `high`.

**COUNTS.md additions:** F1, F2 and F3 counts as turns and clusters, by tier × block × dispersion tercile. Report F3 durable versus non-durable counts.

## 8. Ruling R1 (Director, 2026-11-12T07:27Z, after the build and before any read)
- **F1 primary** = the `family_variant` values `cap_weighted` and `equal_weighted` only.
  - SPHB/SPLV (`factor`) is a separate secondary family, **F1f**.
  - RSP/SPY (breadth of the index) is secondary too.
- **Tier columns are not independent:** a cluster can hold both a major and a minor turn. All tests count clusters per type × block, as the primary N.
- **Leg sizes are in rule space.** They are compared only within the same metric.
