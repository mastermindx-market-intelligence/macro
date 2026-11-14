# Slate v2: rotation and pivot desk (Research Director, 2026-11-12T07:31Z), for one approval

**What this asks for:** approval of §1–§6 as the desk's frame for the D block. Nothing in this slate has been read against outcomes, except the looks listed in §6.
**Ledger at writing:** 310 rows. Families: LEDGER_FAMILIES.csv (291 rows classified, 23 families, 98 primary).
**Shared scorer:** Radar `pivots.py` at Macro `fable/risk-radar-masterplan-20261112` @ 2945b55b66. This pin has H19/H20 applied. The desk's vendored copy is still 558638d0; the re-vendor to 2945b55b66 is running and lands before any read.

---

## 1. The pivot catalogue: the rule and its counts (`catalogue/CATALOGUE_SPEC.md` §0–§8; `catalogue/out/COUNTS.md`)

**Rule.** One zig-zag on log price (on the level for FRED series):
- **Thresholds:** θ = 0.25σ for the minor tier and 0.5σ for the major tier.
- **σ:** taken from 2005–2019 only.
- **Spacing:** turns at least 10 sessions apart.
- **Clusters:** single linkage within 10 sessions, by kind × type.
- **Inputs:** truncated at 2023-12-29. Any turn whose confirmation would need a later price is censored.
- **Fixing:** θ was fixed before the dates were seen.
- **Build:** 23,003 pivots (22,813 confirmed) in 2,841 clusters; 33 tests pass.

**Sanity check.** SPY major tier on D has 9 peaks and 9 troughs. All four anchors are present: 2020-02-19, 2020-03-23, 2022-01-03, 2022-10-12.

**D-block cluster counts (major / minor).** Clusters, not turns, are the N for every test (ruling R1).

| type | major | minor |
|---|---|---|
| risk_off | 45 | 55 |
| risk_on | 48 | 58 |
| leadership_start | 22 | 22 |
| leadership_end | 14 | 15 |

**Primary families (A2 plus R1).**

| Family | Call | D clusters, major | Notes |
|---|---|---|---|
| **F1** high-beta tech ↔ defensives | into defensives, or back into high beta | 55 | Primary = cap-weighted (XLK/SMH/IGV/QQQ vs EW(XLP,XLU,XLV)) and equal-weighted (RSPT vs EW(RSPS,RSPU,RSPH)). SPHB/SPLV (F1f) and RSP/SPY are secondary. |
| **F2** rotation-out onset | "do not get hit": a leader peaks | 14 | Leader = top third by 126-session relative return at the turn date. |
| **F3** durable washout bottom | enter the sold-off group | 41 | Prior leg ≥θ_major, with no lower close for 63 sessions (fixed). Durable vs failed turns: 340 vs 85 on D major, 1,100 vs 194 on PRE. 37 are censored. The failed washouts are the knife-catch set the conditions must avoid. |

- Dispersion terciles (cut-points from 2005–2019) are a column, not a filter.
- All other types stay in the catalogue as secondary.

## 2. Scoring window and pass line (identification only; principal ruling after the Chairman's correction)

**Window.**
- D runs 2020-01-02 to 2023-12-29, with PRE as extra history.
- Walk-forward is purged and embargoed.
- Execution is at t+1. Credit and FRED inputs are lagged 1 session or more (H19/H20 desk rules).
- No label window reaches 2024-01-02.

**Pass line.** Agreed with the Radar leader; computed per asset and reported as a pass count over clusters.
- **Flagged share:** at or above the near-start placebo p90, compared on the share itself. The near-start placebo is near-high for tops and near-low for bottoms.
- **False risk-off calls per year:** at or below the placebo median.
- **Settings:** 2000 draws, tol 0.01, window [turn − 21, turn + post], post 5/10/21, min_off 10.
- **Reported beside every result:**
  - sessions before or after the turn;
  - false calls per year;
  - results by regime;
  - the drawdown-level / distance-to-peak mechanical reference (distance-to-trough for bottoms) at the same budget;
  - the 200-session trend rule, as an **identification baseline only**: when it called each turn, and how late.

**First read:** recall on SPY turns of ≥10 % and ≥7 %, with false alarms per year beside it.

**What is not a pass condition:**
- No card passes or fails on a sleeve's Sharpe, drawdown or return.
- Vol-matched SPY + bills, 60/40 and the trend rule as a sleeve go to a descriptive appendix at most.
- Each family's realised outcomes after a call are appendix context only.

**Power** (`POWER_STATEMENT.md`, H28-corrected):
- The pass line needs ≥4 of 13 clusters.
- The minimum detectable difference in false alarms per year is about 5.6.
- A monotonicity claim needs |ρ| > 0.6 at N = 19.
- On return ranking, MDE80 is 0.093–0.115 at h20 and 0.113–0.132 at h63, and power at IC 0.03 is only 0.11–0.15. That is a further reason the pass line is identification, not ranking.

## 3. First condition sets (written; none read)

Each set is scored per family against the pass line in §2. Every set's ledger row is written before its read. A confluence must beat its best single part.

**a. The engine's states, taken as coded (the incumbents)** (census A, B, C):
- **Sector cycle phase and stance.** The legacy `phase` chip, with the "Rolling over" override, against `phase_v2`/`pos_v2`. These are two classifiers and are scored separately.
- **The four turn organs, scored separately, never pooled** (census C §0):
  - `subsector_turn` (turn_up/down, bottoming/topping);
  - `basket_turn_watch` (WATCH/IGNITION/DOWNGRADE, K-of-N);
  - `us_basket_turn` (FALLING → WASHED_OUT → BASING → CONFIRMED);
  - `mtf_upturn` (single stocks).

  `subsector_turn` is the incumbent for F2. `us_basket_turn` WASHED_OUT→CONFIRMED is the incumbent for F3.
- **Rotation-map quadrants** (RS-Ratio × RS-Momentum) and the fast-lens rank (census B).
- **Caveat:** reconstructed history uses today's membership and is labelled `hindsight`. Results are reported three ways:
  - all groups;
  - only groups whose members were all listed before the test date;
  - by date cluster.

**b. Fabric wave 3** (`pro_wave3/returns/`; Fabric models, not Pro):
- **H1–H5, tops (Sol):**
  - H1 narrowing plus rate pressure;
  - H2 fast-onset confirmation (after the turn, window 0 to +5);
  - H3 credit-led top;
  - H4 rate-shock top;
  - H5 bear-regime lower high.
- **C1–C5, bottoms (Sol):**
  - C1 credit plus price;
  - C2 policy relief plus price;
  - C3 thrust plus credit;
  - C4 bear-regime veto, an AND-NOT applied to any set above;
  - C5 broadening leadership, as an upgrade, not a gate.
- **S1–S5, leadership start (Kimi):**
  - S1 driver turn;
  - S2 relative acceleration;
  - S3 participation up ≥20 points;
  - S4 credit not contradicting;
  - S5 cross-group breadth.
- **E1–E5, leadership end (Kimi):**
  - E1 internal divergence;
  - E2 driver reversal;
  - E3 velocity roll-over after a blow-off;
  - E4 defensive/credit confirmation;
  - E5 rate-hedge gate.
- Kimi's return was written from memory. Its thresholds marked UNVERIFIED stay that way until written down before the read.

**c. The #10604 / #1232 breadth-change framework** (census F §2):
- **What it computes:** six one-day advance/decline counts per sector on today's cohort.
  - Daily level = advancing/matched. This includes flat names, against a monthly fallback that excludes them.
  - Change over 1 or 5 sessions; regimes broad/narrow × up/down; overtakes.
- **Status:** state, not turn. It is not persisted. Its producer is not on Macro main (404 at 94ee7e6; #10604 is still open).
- **As a condition set:**
  - recomputed from member prices on D;
  - labelled `hindsight` (current cohort, survivorship not removed);
  - scored as the "breadth change" ingredient of F2 and F3.
- Read-only. We do not edit, refresh or comment on #1232 or #10604.

**d. The Chairman's F2/F3 ingredients** (`slate2/DRAFT_FAMILIES_AND_BEAT.md`):
- **F1:**
  - rates and real rates (DFII10);
  - credit (HY OAS, BAA−10y), lagged;
  - bond competition (SPY/TLT, earnings yield − 10y);
  - dispersion tercile.
- **F2:**
  - narrowing participation inside the leader;
  - a lower high in relative strength;
  - competing groups' breadth improving;
  - the same backdrop.
- **F3:**
  - the washed-out group's breadth against its competitors;
  - capitulation and its reversal;
  - the backdrop;
  - durable at 63 sessions.

**e. Theme-graph candidates (principal ruling on the SI COO 07:46Z scope facts; GMI theme graph is the SI side's, not censused by the desk).**
- **E1 "child leads parent"**: the pre-registration on Macro `research/theme_graph/THEME_HIERARCHY_E1_CHILD_LEADS_PARENT_PREREG_2026-10-07.md` (2026-10-07) is an outcome study, so it is ours. A read-only flash audit is running (`si_upgrade/PREREG_E1_AUDIT.md`): what it declares, whether and when it was run, and whether any outcome dated 2024-01-02 or later was already looked at. If it was run on sealed years, that read is seen history for this hypothesis and is ledgered as such; a fresh test is then on reconstructed history through 2023-12-29 only. The file is not edited.
- **G-edge, supplier and economic edges** (declared from reasoning; no read): a confirmed zig-zag turn (minor tier, its own pre-2020 σ) in a child or supplier node, followed by the same-direction turn in its parent or customer node within 5–63 sessions, more often than for placebo node pairs with no edge (same node universe, same dates, 2000 draws, clusters as N). Edges are taken as recorded in the graph at their dated evidence, never at today's state where a date exists; otherwise labelled `hindsight_edges`. Scored on the identification pass line in §2 for the parent node's turn. No run until the slate is approved and the SI side's dated series exist (first drafts from 2000-01-01, with the yearly vendor-disagreement table).

## 4. Second question: the destination map (`destination/DESTINATION_SPEC.md`)

The question: after each catalogued risk-off and leadership pivot, which destinations yielded positive returns, and was that identifiable at the pivot? **It is never a buy list.**

**Step 1 (descriptive; ledger family DEST-describe):**
- Forward returns over 21, 63 and 126 sessions from t+1, absolute and relative to SPY and RSP.
- Destinations (GMI themes, subthemes and microthemes are added when their series land; SI floors: counts at any size, shares only at ≥10 members, no index under 5 priced members):
  - sectors and the EQUITY_27 groups;
  - countries: 14 held plus 29 to fetch, built by the desk on flash;
  - Treasuries by maturity, TIPS, gold, commodities, the dollar and bills;
  - themes when the SI side's merged series arrive.
- Grouped by family × tier × regime. Repeatability is tested against the near-high/low placebo, with clusters as N.
- Forward windows end by 2023-12-29; anything later is `censored_h`.
- **Running** (worker …0a8440a5); no output yet.

**Step 2 (identification condition sets at the pivot):** after approval.

## 5. Pro programme (chatgpt3 only; pasted, ≤8000 characters per fill; no upload, since upload was refused by policy; "Pro" label checked before each fill)

| Run | Purpose | Status |
|---|---|---|
| W3-1, W3-2, W3-3 on Pro | the same tops / bottoms / leadership commissions as the Fabric returns in §3b | operator on chatgpt3 (m2studio); report pending |
| W3-4 | turning-point identification and confluence methods: the published evidence (any date; research, not a test) | queued |
| W3-5 | pre-declared condition sets with thresholds, per family F1/F2/F3 | queued after W3-1..3, so it can build on them |
| SI engine diagnosis plus an adversarial second session | from `si_upgrade/pro_packet/` (PACKET.md ≤6000 characters plus a derived CSV via a committed raw link, if used) | after AUDIT_1_3 |
| Destination step 2 | identification conditions for destinations | after step 1 and approval |

## 6. Hold-out boundary (`catalogue/out_boundary/BOUNDARY_COUNTS.md`; labels only, no outcome joined)

Major-tier clusters after each boundary:

| Boundary | risk_off | risk_on | leadership_start | leadership_end |
|---|---|---|---|---|
| **2024-01-02** | 30 | 27 | 17 | 13 |
| 2025-01-02 | 20 | 18 | 12 | 8 |
| 2025-07-01 | 15 | 14 | 10 | 7 |

**My recommendation (RD):**
- Keep 2024-01-02. It is the only boundary that leaves every pivot type at or above Part C's 13-cluster floor.
- Moving the boundary later adds only about 9 risk-off clusters to D and does not change D's power class, while it starves the hold-out.

**Attack seat (W4, Opus):**
- Keep 2024-01-02, but seal it as a single-shot, catch-rate-only, per-family test.
- Its reasons: the engine and the Radar are already touched after 2024; false-alarm gaps cannot be detected at any boundary (MDE about 7.3/yr); and a leadership card passes only if its true catch rate is about 39 % or higher.

**W4's conditions, which I accept:**
- a fixed hold-out end date, set at approval;
- the 69 boundary-confirmed turns stay censored;
- the 5 clusters that straddle the boundary are scored by onset date;
- each card names its universe and recomputes its floor, because the 30 risk-off clusters are pooled across 99 series.

**Looks already taken after 2024** (these families are *touched*, so they are confirmed only forward):
- the SI engine audit period: calls dated ≤2026-11-10, outcomes ≤2026-11-11, diagnosis only (`RELEASE_ENGINE_AUDIT.md`);
- the census looks in `si_upgrade/LOOKS.md`, from parts A, C and E: the published track records, e.g. subsector 63d IC −0.1356 and hub 63d −0.0489;
- the Radar's in-sample scorecard.

## 7. Census summary (`census/parts/`; Macro pin a53877ee83; Terminal origin/master 07225405)

| Part | Status | Headline |
|---|---|---|
| A, per-sector read | in | Stores: calls.parquet 2026-06-28..10-16, 73 dates, 4,294 rows = the self-grader N, no score_version. forward_log runs to 11-06; backfill is month-end from 2010. Defects: two position/phase classifiers behind one chip; the stale central surface (10-16 vs 11-06). |
| B, rotation map | in | Two incommensurable maps. The fast lens has produced no ranks since 2026-10-16 (proven producer stall; the mechanism is with the SI side). Missing inputs are scored as zero. Theme history uses today's membership. |
| C, turn detection | in | Four independent organs are all called "a turn" (§3a). Day-by-day replay from prices; parameter provenance; defect register. |
| D, desk watch / accumulation / subsector confluence | in | 31 items. `false_positive_5d` is exactly 1 − p_onset_5d (not an independent measurement). The turn-desk edge block is hard-coded while tape-onset rates recompute nightly. The turn-desk artifact carries only tape_onset_nodes, and its ledger is absent (promotion clock 0/15 while an edge figure is shown). `p_confirmed_10d` is null for all nodes. Holdings history is about 2 days. Its published edge figures (turn desk, tape onset, confluence tiers) are looks, some spanning 2024+, so those families are touched. |
| E, track record / taxonomy / membership | in | 49 curated baskets (11 sector sleeves + 38 thematic), 40 Finviz themes, 268 subsectors (+1 synthetic). Membership is real only from about 2026-06-14; member prices from 2014. Every coded ledger says "measuring". The 63d ICs are negative. Independent windows: 3.95 (21d) and 0.84 (63d), against a floor of 6. |
| F, Terminal surface plus #1232/#10604 | in | Terminal is a consumer of Macro JSON. Some engine outputs are dropped (F-T19). The #10604 producer is absent on main (B-1). Two breadth denominators. Not persisted. Hindsight cohort. |

**Merge:** the merged CENSUS.md and census.csv come from the SI lead after the spot-check. They are published to Macro in the next desk publication.

**Theme catalogue counts:** pending on the SI side (draft Macro #11107; floors: breadth share at ≥10 members, index at ≥5 priced members). Census E gives the raw taxonomy, and the SI side reports 33 of 49 baskets reaching 10 members. Accepted as pending.

## 8. Stale numbers (`STALE_NUMBERS.md`)

- 41 figures checked: 14 OK, 23 STALE, 2 UNKNOWN.
- STALE:
  - every W3P net %/yr figure;
  - baselines B3/B4;
  - the RISKADJ table (built on the unlagged-credit alert);
  - early-warning F1 +0.89/+1.07 %/yr.
- **None of them is used in this slate.** None is restated, because the early-warning card is closed and its numbers do not return.

## 9. Closed and not tried

- The early-warning candidate is **CLOSED** (`cards/DO_NOT_TRY.md`): no freeze, no forward record, no tuning. On the risk-adjusted re-read (W4c), excess Sharpe was 0.52 vs 0.77 for the trend rule, and max DD −28.8 % vs −13.7 %.
- Slate v1 rows that framed acting on a signal "against SPY" are superseded by §2.

## 10. Running, and capacity

**Running:**
- SI engine-upgrade lead (glm-5.3, under `RELEASE_ENGINE_AUDIT.md`): first return AUDIT_1_3.md; incumbent-look ledger row `siu-inc-look-001` written.
- Census D.
- Destination step 1.
- Kit re-vendor to 2945b55b66.
- Adapter.
- Pro operator.

**Publication:**
- Carrier: PR #11096, branch `rotation-desk/v4-charter-20261112`.
- Contents: CATALOGUE_SPEC, plus `RELEASE_ENGINE_AUDIT.md` unchanged (c01e97ce…b2ea2f), plus the census once merged.
- The publisher failed twice with 503 and was reconciled (remote head unchanged at b036d6d48d). It was re-dispatched on flash on the same carrier, and its report is pending.
- CATALOGUE_SPEC has gained §8 (R1) since the publisher's sha. I send the current file.

**Upload to ChatGPT:** refused by policy, never retried; Pro gets pasted inputs only.

**On approval, the next steps are:**
1. condition-set ledger rows, family by family;
2. first read: recall on SPY ≥10 % and ≥7 % turns on 2945b55b66;
3. destination step 2 prompts.
