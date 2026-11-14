# Brief: G3 within-day stock-feature screen, W1 (RD, 2026-11-14)

**Governs.** This brief runs PLAN_TROUGH_v1.md §3 and §6 (426ae551) for the G3 table, view 1 only. It applies:
- RUN_NOTES_LEADER.md (a303ba6d);
- ADDENDUM_TROUGH_WITHINDAY_v1 (c0cc028b) and v1a (05acdf0e);
- FLOOR_MATCHED_MAP.md (4b247b52);
- the HTF_STATE_1B family count M_HTF.md (d3c447b1);
- the ASTRA_REPRO_T1 batch M_ASTRA_T1.md (683ab1bb), with leader ruling astra-repro-t1-leader-blind-read-match-w1-m44;
- EVIDENCE_GRADES.md (8e7ebf45).

Where a leader ruling and this brief disagree, the ruling governs. SCREEN only, 2013-01-02 to 2019-12-31. **No HOLD label is computed, read or joined.** The deadline is 3 hours from start.

## 0. Gate on the split calendar (checked first; nothing runs before it)
The RD names the case at launch from the closing line of SPLIT_CALENDAR_v1b. Apply it exactly.
- **Case A, `coverage=sufficient rebuild=no`.** Exclusions are `split_calendar/EXCLUSIONS_V2.csv` (G3 rows) plus the 22 BLL/DISCA/COG events. The unresolved set is `split_calendar/UNRESOLVED_V2.csv` (G3 SCREEN rows).
- **Case B, `coverage=insufficient`.** EXCLUSIONS_V2 is not applied. Exclusions are the 37 in `split_audit/EXCLUSIONS_IDENTITY_SPLITS.csv` (f1502bae). The unresolved set is `split_audit/UNRESOLVED_EVENTS.csv` (144c3d7b), G3 SCREEN rows, of which 716 are additional to the exclusions (SPLIT_AUDIT.md 9f559346, line 72).
- **Case C, `REBUILD_TRIGGERED`.** Do not run. Write `W1 not run: REBUILD_TRIGGERED, dots to be rebuilt on the repaired panel first (CEO ruling 2026-11-14)` and STOP.
- Print the case and the hash of every exclusion file used. Print the result of the >10 rebuild trigger as the calendar reported it.

## 1. Events and labels
- **Events.** `events_v1/EVENTS_G3.parquet` (bad2ff33), with window == SCREEN and counting == True.
  - Drop the events in `events_v1/LABEL_EXCLUSIONS.csv` (93686fd5), which holds the boundary and missing rows.
  - Then drop the §0 exclusions.
  - Print the count after each step.
- **WH before 2018-05-21** is excluded (unresolved seam, REV5_NOTES). Print the count.
- **Labels.** PRIMARY is real63, centred within day as in addendum v1 W1: real63_c = real63 minus the same-known_ts-day mean over eligible events. real21, k = 0.5, k = 2.0 and fwd63_rel_spy are centred the same way and used only for the guards in §4.
- **Singleton days** are excluded and counted, as in addendum v1.

## 2. The W1 family: m = 44 (fixed now)
Each line is one single. Test every one of them, even if it later looks redundant. No line is added or dropped after labels are joined.

**A. Plan a–g remainder (22).** These are not yet built, so they are built here (§3).
- **a:** drawdown252_atrc, prior_dot_depth_percentile, oversold_spell_vs_prior_median, rsi14_prior_dot_percentile.
- **b:** personality_pc1.
- **c:** D_floor_1D, D_floor_3D, recent_floor_1D, recent_floor_3D.
- **d:** dot_order, first_vs_later_dot, bullish_divergence.
- **e:** slope10_second_difference, sd10_sd63, largest_down10_atrc, sessions_since_largest_down10.
- **f:** decline_market_share, decline_group_share, decline_idiosyncratic_share.
- **g:** group_floor_share_loo, group_dot_share10_loo, group_basket_dot10_loo.

**B. Weekly and two-week state (13),** read from `htf_state_1b/COLUMNS_HTF.parquet` (b9e31aa0), desk resampler:
- weekly: D_W, K_rising_W, D_rising_W, hist_pos_W, hist_rising_W, top_roll8_W;
- two-week: D_2W, floor8_2W, K_gt_D_2W, K_rising_2W, D_rising_2W, hist_rising_2W, top_roll8_2W.

**C. floor_matched (1),** from the same parquet, per FLOOR_MATCHED_MAP.md.
- It counts as its pre-registered single even if its |ρ| with D_W or D_2W is .7 or more.
- Print that ρ beside it. If ρ ≥ .7, label the line "overlaps D_<grid>"; the two lines are then read as one piece of evidence.

**D. Astra batch (8),** read from `astra_repro_t1/COLUMNS_ASTRA_T1.parquet` (7e7858a4):
- floor_recovery, realized_vol_retreat, postshock_compression, downside_share_retreat, dispersion_contraction, correlation_release, peer_washout_w30, low_holding_20.
- Each of these 8 lines carries the label **"Astra proposal, desk-reproduced"** and the caveat "no point-in-time corporate-action vintage".
- **downside_share_retreat_lag1** is printed only as a robustness line under downside_share_retreat. It adds 0 to m. It can never be a survivor, and it cannot rescue its parent.
- The four day-constant Astra columns (credit_resilience, vix_peak_age, vix_vov_easing, credit_relief) are not in W1. They are view 2, out of scope here.

22 + 13 + 1 + 8 = **44**. Assert it. Print the Bonferroni and BH rank-1 MDE at m = 44 from the accepted W1 planning SE of .010384 (STAGE0 08ecbfdf). If the Bonferroni MDE is above 15 pp, write STOP and end.

## 3. Building the 22 (label-free; before any label is loaded)
- **Definitions** are exactly those in PLAN_TROUGH_v1 §3a–g, with ATR_c as defined in §2. Breadth follows TROUGH_BREADTH_DEF_v1.md (d8f18acc), using leave-one-out.
- **group_* columns.** Use `events_v1/EVENT_GATE_COLS.parquet` (3af7a492) where it carries them: loo_floor_share, loo_dot_share_10 and loo_basket_g3_last10, which hold 35,462 of 35,465 events. Print the 3 missing events; they stay undefined.
- **personality_pc1.** Use the pinned components (PERSONALITY_STRATA ea72fc7f) with the SCREEN loadings in PERSONALITY_PCA.json (3c7964a5), unchanged. Also apply the plan's shrinkage rule.
- **Panel.** Use the panel rev5 cache only, through `catalogue/interior/panel` loaders, the same inputs ASTRA_REPRO_T1 used. Assert date ≤ 2023-12-29 after every load. No 2024+ price is materialised.
- **Engine code** (`ext/macro_main_e999086d`) is imported read-only and never edited.
- **PIT check.** For each of the 22, recompute 200 random events (seed 20261114) from inputs literally truncated at known_ts. A single disagreement drops the column. A dropped column is still counted in m and printed as "not built: PIT fail".
- **Not built.** Any column that cannot be built from closes prints "not built: <reason>" and stays counted in m.
- **Feature file.** Write FEATURES_W1.parquet: event_id plus the 44 columns plus the lag1 robustness column.
  - Hash it and write the hash to RUN_LOG.txt **before** any label column is read.
  - Then write SPLITS_W1.csv: each feature's split rule and its SCREEN cut values on the day-centred feature (terciles), or "by level" for binary and few-level features. These cuts are computed without labels.
  - Hash that file too.

## 4. Screen (after the two hashes are in RUN_LOG)
- **Contrast.** Top tercile vs bottom tercile of feature_c on real63_c. For binary features, the level 1 vs level 0 contrast on real63_c.
- **Counting p.** 20,000-draw permutation of feature_c within day × personality-tercile stratum. Unknown personality is its own stratum.
  - For personality_pc1 only, shuffle within day × universe (ruling ii).
- **Interval.** CI from a whole-month block bootstrap.
- **Family.** BH at q .10 within the 44, plus the Bonferroni line.
- **Guards on every BH survivor:**
  - T3: fwd63_rel_spy_c has the same favourable sign as real63_c. Otherwise print "holds the low, no move".
  - T4: if the sign flips between k = 0.5 and k = 2.0, flag "threshold-fragile".
  - Dedup: a survivor with |ρ| ≥ .7 to a stronger survivor is a duplicate. The floor_matched rule above still applies.
- **716 sensitivity line.** For every line, re-run the contrast and p with the §0 unresolved set also excluded (716 events in case B, or the V2 unresolved count in case A). Print it beside the primary. A survivor whose sign flips, or whose p rises above its BH bar, is flagged "split-sensitive".
- **Pooled tercile contrast** (plan §6) is printed beside each line as description only.
- **Evidence grade.** Every line gets a grade per EVIDENCE_GRADES.md. This is one sample (SCREEN 2013–2019), so C is the highest grade available, and D needs an opposite-direction interval that excludes 0. Also print the coverage grade and the evidence count in months.
- **Fixed in advance.** No cut is fitted on SCREEN labels. No feature, cut or family change after labels are joined.

## 5. Caveats printed in RESULTS.md
1. "Retained dots are those visible on their own close. About 1 in 10 dots (synthetic estimate) first print a session late in live use and are excluded here. Results describe same-session-visible dots." (NOTE_2SESSION_TRAILING_BIN.md, faa65cae.)
2. Weekly and two-week states use the desk resampler (scheduled-session completion). The house T1/T2 weekly states are replay-not-live on 8 holiday-short Thursdays (Macro #11244). The house T1 is not used in this screen.
3. Coverage: 2013–17 survivor-biased, 2018–19 usable.
4. The 3 events without gate columns are undefined for g.

## Rules
- **Python:** `/home/ubuntu2/tmp/rotation-core/v4/.venv/bin/python -P -E -B`, run from /tmp, never with -I. Run `date -u` before every time label. No network, git, delegation or secrets.
- **Never open:** `catalogue/out/`, `catalogue/out_boundary/`, any `*SEALED*` file, `pivots.parquet`, `data/french/sealed_post2019/`, `catalogue/two_speed/astra/`, `catalogue/trough/astra/`, `catalogue/interior/detection_v1/d3_build/`, any HOLD_LABELS_* file, and any HOLD-window label.
  - The Risk Radar composite and production state are not used.
- **Writes** go only to `catalogue/trough/w1_screen/`. Every build step writes its own new log file and never appends to a file another step pinned. Raw prices are never written.
- Checkpoint PROGRESS.txt every 20 minutes.

## Outputs
In `catalogue/trough/w1_screen/`: FEATURES_W1.parquet, SPLITS_W1.csv, PIT_CHECK_W1.md, NOT_BUILT.md, RESULTS.md, RESULTS.csv, SURVIVORS_SCREEN.md, the scripts, RUN_LOG.txt and SHA256SUMS.

**Closing line:** `W1_SCREEN COMPLETE case=<A|B|C> n=<events> days=<n> m=44 built=<n> mde_bonf=<pp> bh_surv=<k> split_sensitive=<k> <sha8 RESULTS.md>`
