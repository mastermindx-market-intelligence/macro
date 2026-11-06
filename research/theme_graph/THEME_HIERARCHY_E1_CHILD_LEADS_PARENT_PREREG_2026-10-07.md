# Theme hierarchy E1 — child leads parent: preregistration (W-C9)

Committed BEFORE any probe computation (the results commit must postdate this file).
Program: GMI Theme Graph (WS:GMI-THEME-GRAPH), DEC:GMI-THEME-HIERARCHY-ON-CROSSWALK; Seat rulings: R-J.9 / R-J.10 (2026-10-07); Status: DISPLAY tier — E1a clock NOT STARTED (W0 undefined until W-C4 PARENT_OF rows exist); E1b DORMANT; Standards: research/MASTERMIND_EVALUATION_STANDARDS.md §2, §3, §4.4–§4.8, §5.3, §10, §11, §12

## 0. Question under test and tier

**Question.** At scheduled decision dates, do theme-tier children (E1a) or micro-theme children (E1b) show a cross-sectional lead: higher recent relative performance of the child versus its leave-child-out parent set predicts higher subsequent relative performance of that parent set versus SPY?

**Tier.** DISPLAY tier only (contracts/theme_graph/README.md §3; research/MASTERMIND_EVALUATION_STANDARDS.md §1). This registration fixes construction, gates, placebos, and falsifiers before any read. It carries no rank, size, or gate authority. Episode-level honest-N accrues here for transparency only; any promotion is a separate gauntlet act (§12 checklist, including honest-N ≥ 50 matured episodes and a matched control). Computing Spearman correlations, hit rates, or any verdict statistic before both gate thresholds in §5 are met is a forbidden LOOK and voids one-look status (research/MASTERMIND_EVALUATION_STANDARDS.md §4.8).

**Hypothesis (narrative, not scored).** Narrow themes may move before their broad category confirms; E1 tests whether any such lead is hierarchy-specific in the curated US baskets rather than generic cross-sectional momentum.

## 1. Arms — E1a (primary) and E1b (registered, dormant)

**E1a (PRIMARY, accrues once W0 exists).** Child = a `theme`-tier node; parent = a `macro_category`-tier node. Pairs = every `macro_category → theme` `PARENT_OF` edge live at decision date D under the as-of-D rule (§2, seat ruling R5). A theme with multiple parents forms one pair per parent.

**E1b (REGISTERED DORMANT).** Identical construction with child = `micro_theme`, parent = `theme` (`theme → micro_theme` `PARENT_OF`), whose priced constituents exist only after **a merged basket→micro_theme wiring wave** (seat ruling R4 — no calendar estimate). Until that trigger, E1b has no clock, no episodes, no N, and no read. Its window W0b follows the honest-window rule (§4) with `theme → micro_theme` `PARENT_OF` and the wiring wave’s basket→`micro_theme` `EXPRESSES` rows in place of E1a’s window anchors. E1b uses the same frozen parameters and an independent gate when activated.

## 2. Inputs and the as-of-D read rule

**Stores (read-only at execution; paths on origin/main).** `data/theme_graph/nodes.parquet`, `data/theme_graph/edges.parquet` (membership and hierarchy), `data/baskets/membership.json` (materialized into the graph by the incumbent emitter), and per-ticker prices `data/yahoo/<TICKER>.parquet`. Benchmark: `data/yahoo/SPY.parquet`.

**Edge read.** Read the full edge history with `engine/theme_graph/store.py::read_edges(latest_belief=False)`. Rows dedupe on `EDGE_KEY = ("edge_id", "belief_time")` keep-first semantics in append paths; consumers must not read raw parquet without the house reader. `read_edges(latest_belief=True)` must never be used for an as-of-D read because it collapses the whole history to the current view.

**PIT / as-of-D (seat ruling R5).** Every edge (`PARENT_OF`, `EXPRESSES`, `MEMBER_OF`) enters a decision at D only under `contracts/theme_graph/README.md` §1 as-of-D collapse: first drop rows with `belief_time > D`, then for each `edge_id` keep the row with maximum `belief_time`, breaking ties on the later `computed_at` and then `edge_id`; the edge is live at D iff `valid_from ≤ D` and (`valid_to` is null or `valid_to > D`). The reference implementation of this collapse is `engine/theme_graph/ontology.py::_collapse_relevant_edges`, called with `asof = D` and `knowledge_cutoff = D`. The house reader for the `PARENT_OF` leg is **W-C6 hierarchy_paths (PR #8612)** in `engine/theme_graph/structural_navigation.py`, called with `knowledge_cutoff = D` (may not be merged at registration; do not treat as production until merged).

**EMPTY-BEFORE-BELIEF (seat ruling R6).** Backfilled membership rows carry `belief_time` = the backfill run date (`contracts/theme_graph/README.md` §2). An as-of-D read for any D before that belief stamp is **EMPTY** — not a reconstructed pre-backfill history and never presented as one. Any computation that applies a later hierarchy or membership backward to earlier dates is reconstruction (G0.2): display-only, excluded from N, excluded from every decision.

**Composition (no stored per-ticker tags).** Ticker → basket → theme → category is composed at read time only (`research/theme_graph/THEME_HIERARCHY_SPEC_V1_2026-10-07.md` §6; DNR:HOLD-TICKER-EXPOSURE-TAGS). Seat ruling R-J.10 dropped the planned W-C7 stored shadow column; E1 does not depend on any `us_context_vector` field (seat ruling R9).

**NODE-LIFECYCLE RESIDUAL (seat ruling R8).** E1a filters on edge `belief_time` and validity only. `read_node_lifecycle` in `engine/theme_graph/store.py` is not treated as bitemporal like edges; retired or renamed nodes are handled only through their edges’ `valid_to`. This is a known residual, not a solved problem.

## 3. Universe and construction rule

**Basket suite.** E1a uses the US curated basket suite only (`basket:baskets:<id>` nodes). Membership source: `data/baskets/membership.json` as materialized into `data/theme_graph` by the incumbent emitter. CN curated and THS suites are out of scope unless a new registered arm is added.

**Graph links (cite `contracts/theme_graph/README.md` §3–§4).** `MEMBER_OF`: company → basket (`src` = company, `dst` = basket). `EXPRESSES`: basket → theme (`src` = basket, `dst` = theme). Hierarchy: `PARENT_OF` with `src` = PARENT, `dst` = CHILD (`macro_category → theme` or `theme → micro_theme`; README § Hierarchy).

**Constituents at D.** Constituents of theme T = every company with a live `MEMBER_OF` at D to a US curated basket B such that `EXPRESSES` from B to T is live at D. Constituents of macro_category P = union of constituents of child themes of P live at D.

**Leave-child-out parent (seat ruling R1).** For pair (child c, parent p), the parent return set uses constituents(p) minus constituents(c) — even when a ticker also belongs to a sibling theme — so the category series never partially measures the child leading itself.

**Eligibility.** Eligibility is decided at D from the lookback only: a constituent counts toward P-MC or P-MP iff it has a close on every NYSE trading day from D−P-L through D. Child c needs ≥ P-MC such constituents; the leave-child-out parent set needs ≥ P-MP such constituents. Pair (c, p) is eligible at D only if both hold. A constituent eligible at D stays in its set for the whole outcome window; if its price series ends inside (D+1, D+6] (delisting or halt), its outcome return runs to its last available close in the window (zero if it has no close after D+1) — never dropped, never re-weighted.

**Returns.** For a set S and window (a, b], r_i = ln(close_i(b) / close_i(a)) for each constituent i of S, using the total-return column `close` (yfinance Adj Close renamed in `collectors.yahoo.py::extract_store_frame`, shared by `scripts/backfill_yahoo_universe.py::download_batch`); set return = the arithmetic mean of r_i over S. Sets are formed at each D from as-of-D membership and held fixed through that episode’s lookback and outcome windows, subject to §3 Eligibility. SPY over (a, b] = ln(close_SPY(b) / close_SPY(a)).

**Signal.** s(c, p, D) = set return of constituents(c) over window (D−P-L, D] minus set return of the leave-child-out parent set over the same window.

**Outcome.** y(c, p, D) = set return of the leave-child-out parent set over (D+P-SK, D+P-SK+P-H] = (D+1, D+6] by close minus SPY return over the same window (outcome starts at the close of D+1 after skip P-SK).

**Per-episode statistic.** rho_D = Spearman rank correlation between s(·) and y(·) across all eligible (c, p) pairs at D.

## 4. Honest window, episode schedule, honest-N and the gate

**W0 (seat ruling R7).** E1a’s window starts at W0 = the later of (a) the earliest `belief_time` of any `macro_category → theme` `PARENT_OF` row in the production store (minted by wave W-C4, not yet merged at registration), and (b) the earliest `belief_time` at which the as-of-D `MEMBER_OF` and `EXPRESSES` composition of the US curated suite is non-empty (by `contracts/theme_graph/README.md` §2 this is the backfill run date, never an earlier reconstructed date). For each candidate D, a pair contributes only if its full composition is non-empty under R5; the first scheduled D at which episode eligibility (P-EP) is met begins counted episodes. Gates count episodes inside the window only. Once both (a) and (b) exist in the store, W0 is a fixed date and never moves. Rows appended later (new members, new `EXPRESSES`, new or superseding `PARENT_OF`) enter decisions only from their own `belief_time` under R5; they never reset W0, the schedule, or the gate counts.

**Schedule.** Decision dates = every P-SCH-th NYSE trading day starting at the first trading day ≥ W0, so consecutive episodes’ outcome windows do not overlap.

**Episode eligibility (P-EP).** A scheduled date counts as an episode only if there are ≥ 8 eligible (child, parent) pairs spanning ≥ 3 distinct parent macro_categories at D. Otherwise the date is recorded as ineligible and is not an episode.

**Honest-N (seat ruling R3).** Count distinct non-overlapping decision dates (episodes), never pairs, fires, or rows. A matured episode is one whose outcome close D+P-SK+P-H (= D+6) exists.

**Pre-gate telemetry (permitted).** Scheduled dates; counted vs ineligible episodes; matured count; eligible pairs and distinct parents per episode; priced-constituent coverage. Forbidden before gates: rho_D, rho_bar, correlation-based hit rates, or any statistic that would inform PASS/FAIL.

**Clock at registration.** W0 does not exist until W-C4 `PARENT_OF` rows are in the production store; the study clock has **not** started at registration and must not be described as running.

## 5. Statistic, frozen thresholds and the decision rule

| Id | Parameter | Value |
|---|---|---|
| P-L | Signal lookback | 20 NYSE trading days; window (D−20, D] by close |
| P-SK | Skip after decision close | 1 trading day (outcome starts close of D+1) |
| P-H | Outcome horizon | 5 NYSE trading days; window (D+1, D+6] by close |
| P-SCH | Decision schedule | Every 5th NYSE trading day from first ≥ W0 |
| P-MC | Child min constituents | ≥ 3 with a close on every trading day of the lookback window at D |
| P-MP | Leave-child-out parent min | ≥ 5 with a close on every trading day of the lookback window at D |
| P-EP | Episode eligibility | ≥ 8 eligible pairs, ≥ 3 distinct parents at D |
| P-N | Gate: episodes | ≥ 50 matured counted episodes |
| P-T | Gate: calendar | ≥ 250 NYSE trading days since W0 |
| P-N2 | Extension read | Only if read 1 INCONCLUSIVE: second read at ≥ 100 matured episodes; no third read |
| P-TH | Significance boundary | Episode-level t ≥ 2.18 (Pocock, two looks, overall two-sided 0.05); at most 2 looks |
| P-B | Permutation draws | 2000, seed 20261007 |
| P-AD | Auto-demote after promotion | 26 matured counted episodes |
| P-FR | Clock freeze | 10 consecutive scheduled dates failing P-EP |
| P-SMA | Regime segment | SPY total-return `close` above vs below 200-day SMA at D |

**Primary metric.** rho_bar = mean of rho_D over matured counted episodes. Uncertainty: episode-level t = rho_bar / (sd(rho_D) / sqrt(N_ep)) with 95% interval. Report Newey-West (4 lags) as sensitivity only, never as the decision statistic.

**Base rate (research/MASTERMIND_EVALUATION_STANDARDS.md §4.5).** Report sign-agreement rate sign(s) = sign(y) beside base rate = share of y > 0.

**Reads.** Read 1 after both P-N and P-T hold. Read 2 only under P-N2 if read 1 is INCONCLUSIVE.

**PASS (all required at a read).** (P1) rho_bar > 0 with episode-level t ≥ P-TH; (P2) rho_bar above the 95th percentile of the shuffled-parent null (§6); (P3) mean d_D > 0 with episode-level paired t ≥ P-TH (d_D from non-parent placebo, §6).

**FAIL (falsifier — any triggers at a read).** rho_bar ≤ 0; or rho_bar ≤ the median (50th percentile) of the SHUF null; or mean d_D ≤ 0. On FAIL: close this E1a construction (parameters, suite, arms) with a DNR row per §10.4; the search space is not closed (research/MASTERMIND_EVALUATION_STANDARDS.md §1.3).

**INCONCLUSIVE.** No FAIL fired but PASS not met → no promotion; one extension read at P-N2 under the same boundary; if still not PASS at read 2, report “not shown at the declared horizon” and close the construction as not-shown (DNR row naming the construction).

**PASS confers nothing alone.** E1 remains DISPLAY tier; promotion requires the gauntlet separately (§12).

## 6. Placebo arms (pre-declared nulls)

**NP — non-parent (seat ruling R2).** NP mirrors the primary construction with q in place of p in both legs. For each eligible child c and each macro_category q that is **not** a parent of c at D, with ≥ P-MP constituents satisfying the §3 lookback eligibility rule after leave-child-out: s_NP(c, q, D) = set return of constituents(c) over (D−P-L, D] minus set return of (constituents(q) minus constituents(c)) over the same window; y_NP(c, q, D) = set return of (constituents(q) minus constituents(c)) over (D+P-SK, D+P-SK+P-H] minus SPY over the same window. rho_NP_D = Spearman(s_NP, y_NP) across all such (c, q) pairs at D. d_D = rho_D − rho_NP_D. An episode contributes d_D only if rho_NP_D is defined on at least the P-EP pair minimum (8) of (c, q) pairs; otherwise it is excluded from P3, the exclusion count is reported, and P3’s t uses the episodes where d_D is defined (report that N). Null (H0_NP): no hierarchy-specific lead — the child's trailing relative return predicts a non-parent category at least as well as its own parent (mean d_D ≤ 0).

**SHUF — shuffled parent.** Within each counted episode, permute parent labels across the episode’s eligible (child, parent) pairs, preserving each parent’s pair count. A child with several parents — `ai_semiconductors`, `data_center_power`, and `copper_steel_electrify` in Appendix A — contributes one pair per parent and therefore carries several labels. Recompute both legs, leave-child-out parent sets, and rho under each pseudo-parent assignment; the child is always excluded from its pseudo-parent set. A pseudo pair that duplicates another (same child, same pseudo-parent) or fails P-MC or P-MP after leave-child-out is dropped from that draw; an episode contributes a shuffled rho to a draw only if at least the P-EP pair minimum (8) of pseudo pairs remains, otherwise that episode is omitted from that draw’s mean. Repeat P-B draws with seed 20261007; null distribution of shuffled rho_bar. RESULTS reports, per read, the number of draws with any omitted episode and the mean count of omitted episodes per draw.

**Publication (§5.3).** Both placebo results publish beside the primary result, never suppressed.

**What each placebo controls.** s contains minus the parent-ex-child trailing return and y contains the parent-ex-child forward return, so any own-autocorrelation of the parent set’s returns (short-horizon reversal or momentum of the category itself) produces a nonzero rho_D with no child lead at all. SHUF recomputes both s and y under the pseudo-parent and so preserves that own-autocorrelation component — P2 is the control for it. NP, mirrored, preserves it too and additionally controls generic cross-sectional child-versus-category momentum — P3 is the control for that. P1 alone controls neither; P1 without P2 and P3 is never evidence of a lead.

## 7. Segmentation (descriptive only)

Segments: by parent macro_category; by P-SMA regime (SPY above/below 200-day SMA on total-return `close` at D); by child constituent-count tercile at D. No segment has its own pass/fail. Each segment reports its episode N or “not estimable.” If any segment statistic is quoted, apply Benjamini–Hochberg q across all segments (leakage class 8). E1a and E1b, when both have been read, use BH q across the two primary tests.

## 8. Leakage — the eight classes

1. **Lookahead.** R5 as-of-D beliefs plus R6 empty-before-belief plus P-SK between decision close and outcome start.
2. **Survivorship.** Closed edges never vanish (README §1); eligibility uses only closes through D; outcome returns of names that stop trading run to their last available close; cash delisting proceeds not in the price store are a named residual. Curated lists are a present-day selection of mostly surviving liquid names — forward-only reads are not outcome lookahead, but RESULTS must restate the selection fact.
3. **Revision.** No macro series revision; adjusted-price vintage is the store as read on the read date, named in RESULTS.
4. **Timestamp.** P-SK removes same-close belief stamped after decision close from the outcome path.
5. **Corporate actions.** Total-return via store column `close` (Adj Close basis).
6. **Universe.** As-of-D membership and hierarchy only; never today’s constituents or future `PARENT_OF` beliefs.
7. **Hyperparameters.** Every numeric threshold fixed in §5; no grid search; at most two looks (P-TH Pocock).
8. **Multiple testing.** One primary test for E1a; separate primary for E1b when active; BH q across segments when quoted; BH across E1a/E1b when both read.

## 9. Adjudication coverage

Before the verdict paragraph in `THEME_HIERARCHY_E1_CHILD_LEADS_PARENT_RESULTS.md` (research/MASTERMIND_EVALUATION_STANDARDS.md §11), RESULTS must:

1. **Motivating exemplars** (per-pair sign agreement and mean s·y over the window): (child `ai_semiconductors`, parent `semiconductors_hardware`), (child `ai_semiconductors`, parent `technology_software`), (child `data_center_power`, parent `energy_power`).
2. **Current regime:** whether the latest 10 counted episodes are in-sample of any winning cell.
3. **Honest-N:** episode-level matured count and ineligible dates.
4. **Who is missing:** tickers without price files, per-episode coverage, delisted names, curated-list selection fact.

## 10. Falsifier can fire; clock freeze; auto-demote

**Inputs exist.** `git ls-tree origin/main` shows blobs for `data/theme_graph/edges.parquet` and `data/yahoo/SPY.parquet` at registration; falsifier inputs are tracked on main.

**Falsifier can fire (§2.5, §10.2).** FAIL conditions in §5 are explicit and depend only on matured episodes after gates.

**Clock freeze (P-FR).** Ten consecutive scheduled dates failing P-EP freeze the clock; record in RESULTS. While frozen, the study does not age toward any verdict.

**Auto-demote (P-AD).** If E1a is ever promoted by a later act, it reverts to DISPLAY automatically if the next 26 matured counted episodes after promotion yield rho_bar ≤ 0.

## 11. Outputs and what this registration does NOT do

**Results file (not created in this PR).** `research/theme_graph/THEME_HIERARCHY_E1_CHILD_LEADS_PARENT_RESULTS.md` is created at the first read and published whether or not E1a passes (§10.3).

**This PR does NOT:** run code; compute statistics; read price or graph data bytes; edit registries or ledgers; add stored fields or user surfaces; change CI; wire producers; or claim any check or verdict. Registration only.

## Appendix A. Pairs at registration (informative; §3 governs)

As frozen for W-C4, not yet in the production store — 21 `macro_category → theme` `PARENT_OF` edges:

| Parent (macro_category) | Child (theme) |
|---|---|
| energy_power | data_center_power |
| energy_power | nuclear_power |
| energy_power | grid_electrification |
| energy_power | solar |
| financial_services | fintech_payments |
| healthcare_lifesciences | glp1_obesity |
| healthcare_lifesciences | medical_devices |
| healthcare_lifesciences | diagnostics_lifesci |
| industrials_defense | defense_aerospace |
| industrials_defense | robotics_automation |
| industrials_defense | space_satellite |
| industrials_defense | copper_steel_electrify |
| materials_mining | rare_earth_critical_min |
| materials_mining | copper_steel_electrify |
| materials_mining | ag_fertilizer |
| semiconductors_hardware | ai_semiconductors |
| semiconductors_hardware | memory_storage |
| semiconductors_hardware | semicap_equipment |
| technology_software | ai_semiconductors |
| technology_software | data_center_power |
| technology_software | cybersecurity |

Childless macro_categories at registration: `consumer_cyclical`, `consumer_defensive`, `crypto_digital_assets`. **financial_services** has only one child (`fintech_payments`); leave-child-out removes the entire parent constituent set for that pair, so it can never meet P-MP — the construction rule governs, not this table.

## Amendment A1 (pre-read, 2026-10-07)

**Status of this amendment.** Registered on 2026-10-07, after the registration above merged (PR #8621) and before the E1a clock can start: W0 does not exist until the W-C4 `PARENT_OF` rows are in the production store, and this amendment merges before W-C4 merges (seat ruling R-J.11). No statistic, price, or graph byte has been read. The text above is left unedited; where this amendment and the text above differ, this amendment governs. A1 closes the two gaps found by the seat review of PR #8621 (minors m1 and m2). It adds no new number and changes no frozen parameter.

**A1.1 — Outcome endpoint closes (closes m1).** In every set return over the outcome window (D+1, D+6] — y, y_NP, every SHUF recomputation of y, and the SPY leg of each — close_i(t) at an endpoint t of that window means the last available close of constituent i at or before NYSE trading day t. A constituent eligible at D has a close on D (§3 Eligibility), so both endpoints are always defined. This carries the last traded price forward through days with no close; it never uses a close after t. No case is left to the analyst: (a) a name halted on D+1 that trades again inside the window is measured from its close of D to its last close at or before D+6, so the move at resumption lands inside the window; (b) a name with no close on D+6 that trades again after the window is measured to its last close at or before D+6; (c) a name whose series ends inside the window is measured to its last available close, as §3 already states; (d) a name with no close after D+1 has outcome return zero, as §3 already states, whether or not it closed on D+1. For case (a) the skip day is not separately excluded: a halted name has no D+1 close to skip, and dropping the resumption move would discard the outcome it carries. The lookback window is unchanged: §3 eligibility already requires a close on every NYSE trading day from D−P-L through D, so no lookback endpoint is ever carried forward.

**A1.2 — Clock freeze, thaw, and day accounting (closes m2).** (a) Trigger: a run of P-FR consecutive scheduled dates that each fail P-EP freezes the clock. The frozen interval begins on the first scheduled date of that run. A shorter run freezes nothing; its dates are recorded as ineligible exactly as §4 says. (b) Thaw: the first later scheduled date that meets P-EP ends the freeze. That date is a counted episode under the ordinary rules, and the frozen interval ends on the NYSE trading day before it. If no scheduled date after the run has met P-EP by the as-of date E of a read or of telemetry, the freeze is open: its thaw date is not yet known, the interval runs from its first date through E, and every NYSE trading day in that span is excluded from P-T, so the study does not age toward any verdict while the freeze stays open (§10). A later thaw closes the interval as above. The schedule never restarts or re-anchors: decision dates stay every P-SCH-th NYSE trading day from the first trading day ≥ W0, frozen or not. (c) Day accounting: NYSE trading days inside a frozen interval do not count toward P-T. P-T holds when the NYSE trading days since W0, minus every trading day inside a frozen interval, reach the P-T threshold. P-N is unaffected, because a date that fails P-EP is never a counted episode. (d) A freeze never closes the construction and never fires a falsifier; only a read or a later seat act does. (e) Record: no new ledger, store, or record is created for a freeze. Freeze and thaw dates are a pure function of the schedule and the as-of-D P-EP test, so the analyst recomputes them at read time from the same as-of-D inputs (§2, R5) and lists every frozen interval (first date, thaw date or open, trading days excluded) in `research/theme_graph/THEME_HIERARCHY_E1_CHILD_LEADS_PARENT_RESULTS.md` beside the P-T count. Pre-gate telemetry (§4) may list the frozen intervals and the freeze-adjusted P-T count, because both follow from the permitted record of counted versus ineligible dates; the read-time recomputation governs wherever the two differ.
