# Terminal-twin dot, completed buckets; Stage 1, paper research, SCREEN 2013–19

Coverage for EVERY number below: 2013–17 survivor-biased; 2018–19 usable. Evidence grade by distinct months: ≥20 tested, 8–19 limited, <8 case-based. Pooled SCREEN results mix both coverage grades; not a HOLD claim.

## Four counting lines

| arm | n | n_A4 | months | evidence | estimate_pp | CI95_low_pp | CI95_high_pp | p_counting | Bonf_p | MDE_pp | gap_excluded_estimate_pp | gap_sensitive | p_month_personality_description | cluster_slope_pp_description | null_mean_pp |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A1 | 8477 | 7332 | 74 | tested | -0.00930702603054487 | -1.6438763227578768 | 1.6279399125881908 | 0.9858007099645018 | 1.0 | 3.113204741043209 | -0.00930702603054487 | False | 0.9855507224638768 | -0.022420774642367757 | 0.2657723087506067 |
| A2 | 11460 | 7332 | 77 | tested | 0.02480108291857434 | -1.5429687476902576 | 1.5457249150470462 | 0.9491525423728814 | 1.0 | 2.9192464992480227 | 0.02480108291857434 | False | 0.9623018849057547 | 0.6085164947981434 | 0.1327165308356835 |
| A3 | 10820 | 7332 | 74 | tested | 0.14034697556877307 | -1.4899277728118494 | 1.7782467685756371 | 0.8626568671566421 | 1.0 | 2.9527398551422435 | 0.14034697556877307 | False | 0.7936103194840258 | -0.5273001644619499 | 0.463641444835233 |
| ANY | 14441 | 7332 | 80 | tested | -0.08617043656565111 | -1.5487040421174463 | 1.3900519076145526 | 0.8269086545672716 | 1.0 | 2.7992202890497144 | -0.08617043656565111 | False | 0.8707064646767662 | -0.33558443681027555 | 0.17372995148703224 |

Positive estimates favour gated dots. Estimate=mean(day×personality-centred real63 in arm) − mean(same centred outcome in A4). P=(1+two-sided absolute exceedances)/20001; alpha=.025 per line. 95% CIs are 2000 whole-month percentile bootstraps, not simultaneous family intervals. P uses G1a outcome-block shuffle, not a z approximation. Fixed clusters contribute unchanged to null; null means are reported for transparency.

# Terminal-twin dot, completed buckets; Stage 1, paper research, SCREEN 2013–19

Coverage for EVERY number below: 2013–17 survivor-biased; 2018–19 usable. Evidence grade by distinct months: ≥20 tested, 8–19 limited, <8 case-based. Pooled SCREEN results mix both coverage grades; not a HOLD claim.

G1a recorded verbatim in RUN_LOG. This decision is fixed BEFORE any p is computed.

| arm | n | immobile_same_day_share | immobile_selected_pool_share |
| --- | --- | --- | --- |
| A1 | 8477 | 0.5415831072313319 | 0.47811725846407926 |
| A2 | 11460 | 0.5524432809773124 | 0.48411867364746947 |
| A3 | 10820 | 0.554713493530499 | 0.4877079482439926 |
| ANY | 14441 | 0.5109756942040025 | 0.4415206703136902 |
| A4 | 7332 | 0.26677577741407527 | 0.1879432624113475 |

Fallback triggered=True; selected pool=same ISO week × exact cluster size. Single-basket-day events excluded=13, days=11. Event order within each whole outcome block: personality tercile, ticker, event_id; fixed before outcomes. Singleton pools remain fixed.


## Actual arm base rates and W1 design effects (post-MDE association)

| arm | n | months | base_real63 | ICC_month | ICC_basket_day | W1_deff | effective_n | evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A1 | 8477 | 74 | 0.48684676182611775 | 0.0018009319617482674 | 0.07585867194978722 | 1.3324295579666232 | 6362.062406463326 | tested |
| A2 | 11460 | 77 | 0.48438045375218153 | 0.0002112798437789399 | 0.07357787933989278 | 1.3436425547200632 | 8529.054070029508 | tested |
| A3 | 10820 | 74 | 0.48512014787430685 | 0.0029250417774512546 | 0.06969048159782762 | 1.424763499195827 | 7594.2428382725175 | tested |
| ANY | 14441 | 80 | 0.4755903330794266 | 0.0 | 0.0735230746308889 | 1.2912130025744242 | 11184.057139455297 | tested |
| A4 | 7332 | 81 | 0.41134751773049644 | 0.0 | 0.02948022001555034 | 1.035312637644526 | 7081.91876869317 | tested |
## G5, LOO bias (description)

| arm | n | months | LOO_share | full_member_share | evidence |
| --- | --- | --- | --- | --- | --- |
| A2 | 21773 | 81 | 0.5263399623386763 | 0.5587654434391218 | tested |
| A3 | 21773 | 81 | 0.49694575850824413 | 0.5184402700592476 | tested |

G2 undefined-as-A4 any-gate W1 estimate=0.118306 pp; undefined original count=527; description only.

Option (iii) rejected for counting: original preflight found 59 mixed any-gate basket-day clusters (not 59 events); majority-for-shuffle differs from event flags and is not used. Option (ii) slopes and month×personality p are description only, never rescue counting.

Gap check is a no-op: leader reports False on all 35,465 retained events; zero gap_bar events on loaded SCREEN support. Every primary gap-excluded estimate equals the printed estimate; no line is gap-sensitive.

G3 family: DOT-GATE-1 has exactly four counting lines. Original provisional G3 W1 m_screen=27, removing the three identical §3g tests gives 24; total provisional G3 m_screen=41→38 (W2 14 includes underpowered description slots). No second claim from §3g, no BH rescue.

Detailed real21, signed distance from true swing low (sessions and fractional %), MAE21/63, fwd21/63 versus SPY, and k=.5/2 sensitivities are in DESCRIPTIVE_OUTCOMES.csv. All are description, not added counting lines.


## G4 plain comparator and verdict

# Terminal-twin dot, completed buckets; Stage 1, paper research, SCREEN 2013–19

Coverage for every number: 2013–17 survivor-biased; 2018–19 usable. Evidence by distinct months: ≥20 tested, 8–19 limited, <8 case-based. Descriptions only, not a new counting family.

G4b comparator: weakest LOO basket trailing 63-session relative strength versus SPY, exactly any-gate count per SCREEN year. All analytic gate-defined events eligible; sort ties by date,ticker,event_id. Comparator against its own nonselected complement, with the same day×personality outcome centring; using original A4 would overlap comparator and control. Share matching is retrospective SCREEN description, not a deployable selector.

| year | eligible | any_count | comparator_count | coverage | months | evidence |
| --- | --- | --- | --- | --- | --- | --- |
| 2013 | 2749 | 1541 | 1541 | survivor-biased | 12 | limited |
| 2014 | 2873 | 1979 | 1979 | survivor-biased | 12 | limited |
| 2015 | 3428 | 2303 | 2303 | survivor-biased | 12 | limited |
| 2016 | 3134 | 2246 | 2246 | survivor-biased | 12 | limited |
| 2017 | 3246 | 1872 | 1872 | survivor-biased | 12 | limited |
| 2018 | 4223 | 3174 | 3174 | usable | 12 | limited |
| 2019 | 2120 | 1326 | 1326 | usable | 9 | limited |

Any-gate real63 W1 estimate=-0.086170 pp; comparator estimate=0.105462 pp; any minus comparator=-0.191632 pp. G4b passes=False. RS unavailable=0; all prices loaded <=2019-12-31.

# Terminal-twin dot, completed buckets; Stage 1, paper research, SCREEN 2013–19

Coverage for every number: 2013–17 survivor-biased; 2018–19 usable. Evidence by distinct months: ≥20 tested, 8–19 limited, <8 case-based. Descriptions only, not a new counting family.

## no measurable benefit at this power

G4(a): any-gate estimate -0.086170 pp, counting p=0.82690865, Bonferroni threshold .025; pass=False.

G4(b): any-gate -0.086170 pp versus same-share weakest LOO RS comparator 0.105462 pp; pass=False.

G4(c): fwd63 relative-SPY W1 difference -0.205844 pp; pass=False.

All three are required together. MDE_any=2.799220 pp; event and month support in RESULTS/MDE. Evidence: tested on pooled SCREEN months, coverage mixed as above. This is one Stage1 paper-research evidence piece, not replication, not HOLD validation, not trading authority.

## DG1 old double gate

# Terminal-twin dot, completed buckets; Stage 1, paper research, SCREEN 2013–19

Coverage for every number: 2013–17 survivor-biased; 2018–19 usable. Evidence by distinct months: ≥20 tested, 8–19 limited, <8 case-based. Descriptions only, not a new counting family.

Earliness: among the 3449 matched gated dots, the dot precedes the old TAILWIND T1 entry by a median 12.0 sessions and captures a mean 5.580% move before that entry.

False calls: 76.117% of gated dots undercut before a valid TAILWIND T1 or never obtain one within 63 sessions; in reverse, 59.440% of eligible SCREEN TAILWIND T1 entries have no retained gated dot in the preceding 21 sessions.

DF2: completed buckets make measured earliness a lower bound on live earliness; the live false-call rate can be higher than measured because developing-bucket dots may disappear. Neither sentence establishes a return advantage.

| stratum | n | months | evidence | matched | lag_median | captured_mean | captured_median | false_call_share | undercut_before_T1_share |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | 14441 | 80 | tested | 3449 | 12.0 | 0.05580235374524086 | 0.04424359681644385 | 0.761166124229624 | 0.5325115989197424 |
| personality -1 | 296 | 66 | tested | 70 | 12.0 | 0.061303221128789276 | 0.05055968437545044 | 0.7635135135135135 | 0.5405405405405406 |
| personality 0 | 3568 | 78 | tested | 807 | 9.0 | 0.07636277665964825 | 0.0652414615450132 | 0.7738228699551569 | 0.5538116591928252 |
| personality 1 | 4806 | 75 | tested | 1127 | 9.0 | 0.05468111884582165 | 0.04488245072429331 | 0.7655014565126924 | 0.5434873075322514 |
| personality 2 | 5771 | 79 | tested | 1445 | 12.0 | 0.04492782760189851 | 0.03688231247325602 | 0.7496101195633339 | 0.5097903309651707 |
| coverage survivor-biased | 9941 | 60 | tested | 2306 | 12.0 | 0.052734006753940514 | 0.041631998940094284 | 0.7680313851725179 | 0.5194648425711699 |
| coverage usable | 4500 | 20 | tested | 1143 | 9.0 | 0.061992737089019145 | 0.049345838838903644 | 0.746 | 0.5613333333333334 |

DG1 input metadata rows=171378; cut before SCREEN=0; cut after SCREEN=84326; SCREEN metadata rows retained=87052; TAILWIND dated 500+400 entries=30168; reverse left-boundary entries excluded=148; reverse denominator=30020; reverse months=83 (tested). CSV was streamed using only ticker/date/arm/counting/size, no label/outcome columns. Both searches use only SCREEN-dated entries. Future metadata dates are counted for DG1 boundary disclosure but no future outcome or price is loaded. Dot pool is the outcome-qualified, gate-defined primary pool; reverse false-call share therefore refers to that stricter retained pool, not every possible live dot.

Old double gate is an ETF-level proxy: group ETF tier/regime, not live curated baskets. sector_signal thresholds and base rates are SPDR-calibrated on overlapping 2013–2023 history; regime leg is not discovery-clean. Strict no-undercut comparison uses the trough low, no ATR tolerance, before the first qualifying T1; same-day dots are excluded from the strictly preceding reverse 21-session window. No HOLD labels or HOLD comparison.

## Final validation and interpretation limits

Headline counts n_a1=8477, n_a2=11462, n_a3=10821, n_a4=7342, n_undef=527 refer to the 22313 Stage0-availability-qualified SCREEN events. Primary inference additionally excludes 13 events on 11 single-basket days: A1 loses 0, A2 loses 2, A3 loses 1, any loses 3, A4 loses 10. Primary denominators are printed per line; they are not silently conflated with headline arm counts.

WD4 binary-arm MDE is the explicitly documented preassociation size-scaled planning approximation, not an empirical per-arm power simulation. Actual ICC/deff and base rates are postassociation descriptions. The selected week×size null retains 44.15% of any-gate events immobile; this limitation remains, with no further fallback. Fixed blocks and constrained pools give a nonzero null mean, printed for each arm; the preregistered two-sided absolute-tail p is used unchanged, not silently recentered.

G4b reuses the accepted basket-index convention: missing constituent returns are omitted from each equal-weight daily mean, and an all-empty basket-day is compounded as a zero return, exactly as the event-builder index. An initial extra 63-complete-return restriction was rejected by a coverage assert BEFORE any comparator estimate or verdict; it was removed to match the accepted definition, not after viewing a comparator result. No price levels were persisted.

Raw signed lag means dot after true swing low when positive and dot before true swing low when negative. Percent-distance and MAE/forward-return CSV values are fractions (multiply by 100 for percent); primary estimates/MDE/CIs are already percentage points. Month evidence grades describe history support, not independent live validation. Coverage-stratified primary estimates are description-only in COVERAGE_DESCRIPTIONS.csv.

Validation checks are in VALIDATION.txt. No HOLD outcome read, no feature beyond A1–A3 joined except the explicitly required G4b comparator and personality inference strata. No network, git, secret, delegation, forbidden input, raw-price output or engine mutation. HR5: this run does not evaluate any held-back date and creates no held-back labels; any future moving held-back set needs a prospectively specified label-generation policy before its read.
