# Fabric Independent Science Review — Retained Original Response

**Source:** Subagent Fabric `gd-risk-prospective-science-20261030` under root `gd-early-warning-20261030`, completed 2026-10-30, controller `34751`. **Exact response SHA-256:** `54a5d5b1021b2128e76fdbbf465c6ddd6e41a33cbbac1ed9d108d8392c22446a`. **Fabric manual_result_review acceptance:** `accepted=true`, `accepted_by=reviewer` (CEO verified result as *independent review work product*; NOT acceptance of predictive skill or permission to alter any production model/policy). Worker no source writes, no prices or return retrieval, no model fitted. Original review below is preserved verbatim; the science protocol still requires owner adjudication, frozen preregistration, power study and real forward scoring. One flagged editorial issue: protocol proposes Brier skill on a non-probabilistic descriptive watch; the eventual forecaster must register a separately calibrated probability output and strictly distinguish tier A categorical watch. Unknown availability in retrospective artifacts cannot be treated as actual issuance.

---

Memory write was refused by the harness (symlink path check); skipping it — the review is the deliverable.

---

# Independent Science Review — Pre-break sector-specific risk-off WATCH (EW-P3)

**Reviewer role:** independent non-author bounded science challenge (C2), read-only. No source writes, no fits, no implementation, no price retrieval, no derived probability or policy authorization.
**Anchors inspected:** Macro `ce5201f96f721967d0d6cf65a0afc759d28ce35b` (2026-10-30, origin/main; local checkout `main` is stale at `3c3f319` and was not trusted); Draft PR #10219 head `55218bee` (base = ce5201f9 exactly), task tree EW-P0–EW-P5; Draft PR #10218 head `d8332c79` ("research(audit): qualify legacy v1 false-positive predictive evidence"); `research/DEFENSIVE_ROTATION.md`; `research/RISK_ENGINE_V2_FINDINGS.md` (incl. §8/§9/§10); `agentos/decisions/DEC-RISK-RADAR-PROSPECTIVE-VALIDATION-READINESS-BAR.md`; `research/grey_deer/GREY_DEER_RISK_INTELLIGENCE_ARCHITECTURE_FREEZE_2026-08-19.md`; `research/LEADERSHIP_ROTATION_PREREG_V2_1.md` + `LEADERSHIP_ROTATION_T26_CLOSEOUT_2026_10_14.md`; `RISK_RADAR_PROSPECTIVE_VALIDATION_READINESS_PREREG_2026-09-24.md`; `RISK_RADAR_ISSUED_WARNING_DURATION_2026-09-24.md`; `research/audits/TECH_ROTATION_PRE_EVENT_CENSUS_2026-10-30.md` (from #10218); `research/grey_deer/EARLY_WARNING_INTEGRATION_INCREMENT_2026-10-30.md` + `commissions/EW_CROSS_SYSTEM_PRO_REVIEW_2026-10-30.md` (from #10219); DEC records `RISK-STATE-HAZARD-POLICY-SEPARATION`, `ROTATION-RISK-CONTEXT-REUSES-OBSERVATIONS`, `RISK-EPISODES-USE-CHRONICLE-AND-REFLEXES`, `LEADERSHIP-ROTATION-P1-WITHHELD-UNTIL-STATISTICS-REREGISTERED`. All reads via `git show <sha>:<path>` and GitHub content API; nothing in the repo was modified.

---

## 1. Verdict summary

1. **Yes, with conditions — a pre-break sector-specific *watch* can be useful without a validated broad-market crash forecast, but only as product (A) "correctly observed factual early warning."** It is useful as attention allocation, not as probability. The moment it is named or rendered as *risk-off*, it imports probability/policy semantics it has not earned, and the DEC bar + Grey Deer policy gates attach.
2. **The strongest argument for the watch is architectural, not statistical:** `engine/risk_radar.py`'s loud-alert gate (`context_gate_live`: SPY below 200dma AND weak breadth) is *by construction* silent in a strong-index regime — exactly the pre-break window at issue (Sept 30: risk_radar Caution, `alert=false`, `macro_risk=Low` while `risk_state.v1` ELEVATED/63.3 and `leadership_crack.v1` BROKEN). The census correctly rules: keep the gate, add a separately qualified sector watch that cannot masquerade as a validated broad-market probability.
3. **The statistical evidence for any sector watch is far weaker than the October narrative suggests.** The one preregistered rotation test (DEFENSIVE_ROTATION) failed all six gates and all seven variants; the only modern-era-leading signals in the revalidation (XLU/SPY defensive 1.91×, XLY/XLP 1.67×, parabolicity 2.06× at 2020+) were validated against **SPY drawdown onset** targets under a strict revalidation bar — not against sector-specific loss, and not prospectively. There is currently **zero** validated evidence that any sector watch predicts *sector-excess* loss.
4. **September 30 `risk_state.v1` ELEVATED cannot be counted as a validated hit.** Its band (composite abs≥60) measured **2.9× lift in 2006–2019 but 0.68× in 2020–2026** (RISK_ENGINE_V2 §8) — below base rate in the era that matters. The census states the correct reading: Sept 30 ELEVATED is "a genuinely retained earlier risk assessment, *not* a recovered validated edge," and it is "not a quantified accuracy score of this single September 30 observation." It is motivation for a *descriptive* watch; it is inadmissible as evidence for lowering the broad gate, resurrecting v1 authority, or tuning anything.
5. **The single biggest scientific defect in the current state is n=1 selection:** October 2026 is one episode, known in full, chosen because the watch material "worked." No protocol may fit trigger constants, thresholds, or persistence floors to it. The prereg must freeze all constants from pre-October law/rationale and earn every quantitative claim from prospective accrual.
6. EW-P3.T1/T2/T3 as drafted in #10219 are **directionally sound** and consistent with the frozen architecture; the protocol below makes T1 concrete and closes gaps T1 currently leaves open (abstention scoring, correction clocks, conditional baseline, nested-sector multiplicity budget, constant-freeze law, power precondition, demotion falsifiers).

---

## 2. Can a pre-break sector-specific risk-off WATCH be useful without a validated broad-market crash forecast?

**Answer: a *watch* — yes; a *risk-off* label — no, not yet.** Decompose by the increment's own three-product law (A/B/C in EW_INCREMENT DONE_WHEN):

- **(A) Observed factual early warning.** Useful *now*, conditionally. "XLP +1.98% vs SMH −3.99% over two sessions; semis RRG Leading→Weakening; 42-name hardware cohort cracked" is arithmetic on as-issued observations, not a forecast. Its utility claim is *decision-relevance*: it changes what a user reviews (concentration, hedging considerations), not what they should believe about odds. This utility rests on exactly three preconditions, each falsifiable:
  1. **Factuality** — the observation is verifiable from issued receipts with complete clocks (Oct 9 artifact currently fails this: `availability.status=UNKNOWN`, `available_at=null`, timezone-naive `generated_utc`);
  2. **Cheap response** — the user's review cost is low and the miss cost high (asymmetric loss); this is a design assertion, not evidence, and must be labeled as such;
  3. **No cry-wolf externality** — watch frequency must be budgeted so it does not habituate users to the broad alert. Unmeasured today; the FA budget below makes it measurable.
- **(B) Validated probability/lead-time skill.** Not available, and not required for A. The radar's own probability surface (`_PROB_CAL`, §9) is an in-sample historical calibration *still under test* by the frozen DEC readiness bar; nothing sector-specific has even an immature cohort.
- **(C) Policy.** Genuinely useful *without* B only through the freeze's `temporary_operator_safety` lane (§11 of the architecture freeze): labeled, scoped, time-boxed, individually authorized, never de-escalating on stale data. Absent that, no risk-off posture may follow from a watch.

**The naming discipline is the crux.** The architecture's separation law (DEC:RISK-STATE-HAZARD-POLICY-SEPARATION) means a "watch" must remain a *named measured state with its own target/horizon and invalidator* — "technology breadth is narrowing; review concentrated exposure" — never a number that blends into measured_state, never "risk-off," which is a policy/posture word owned by policy authority. The increment already encodes this (canonical semantics 3); this review's job is to give it objective entry/exit criteria (§8 below) so "watch" cannot silently drift into "forecast" after one flattering episode.

**Why the watch does not need the broad forecast to be useful:** the broad gate's selectivity is deliberate (its FP tradeoff is asserted in the increment and census). A gate that only fires when SPY is already below its 200dma with weak breadth *defines away* the pre-break segment of state space. The watch's value proposition is coverage of exactly that deliberately unserved segment, sold as *description* — "here is a measured leadership fact" — not as *prediction* — "a crash is coming." The former needs no lift validation to be honest; the latter always does. The failure mode to police is conversion of the former into the latter by typography.

---

## 3. Selection-bias challenge

Seven mechanisms, each independently sufficient to invalidate a naive claim:

1. **Outcome-selected episode (n=1).** October 2026 was chosen *because* the sector rotation preceded the selloff. The +6.2pp OOS "lift" in DEFENSIVE_ROTATION's primary (20.5% vs 14.3% at N=10) comes with 95% CI [−4.82, +19.94]pp, 80% false alarms, and only 25% of hits at the registered 2–4d lead — and that was the *preregistered* test. Any post-hoc sector-watch design that inherits October's parameters inherits the selection with none of the preregistration.
2. **Survivorship of retained artifacts.** The census compares git-committed nightly snapshots. Commits are a retention process, not an issuance process; sessions where a producer failed, was held, or emitted nothing are invisible. "Sept 30 source existed" ≠ "Sept 30 was issued and seen" — the census itself found the Sept 30 v1 ELEVATED headline absent from the served `macro.html`, and the Oct 29 envelope DEGRADED with Oct 23/Oct 20 legs while other surfaces showed Oct 29.
3. **Signal-selection over the candidate pool.** Many rotation-adjacent statistics exist (RRG, ratio lens, subsector rotation, turn watch, leadership_crack, breadth). The October episode is consistent with *some* subset of them firing; the fraction of candidate watchers that fire in arbitrary strong-tape weeks is unmeasured. A watch validated only on the episode that selected it is a multiple-testing survivor.
4. **Vintage / reconstruction bias.** Ratio-of-wealth observations recomputed today from back-adjusted Yahoo series are not the as-issued ratios; membership (e.g., the 42-name hardware cohort) drifts; the census notes the Oct 9 `generated_utc` is timezone-naive. Any 2026 "replay" that recomputes from current mutable caches is forbidden by house law — and by this task's constraints.
5. **The 0.68× band is anti-predictive in the modern era.** RISK_ENGINE_V2 §8's strict revalidation (day-level forward lift ≥1.5×, frequency-matched permutation p<0.05, 2020+ lift ≥1.2×) found `current_composite abs≥60` at 1.70× (06–12), 2.38× (13–19), **0.68× (20–26)** — "EDGE DEAD in modern era"; breadth_div 0.69× modern. Implication, stated precisely: the *band* had no conditional lift 2020–2026, so Sept 30 ELEVATED is one draw from a distribution whose conditional event rate was *at or below base*. One post-hoc-correct call from such a band is what 0.68× predicts; the number of modern-era ELEVATED sessions not followed by drawdowns is not in evidence and cannot be reconstructed (EW increment: "no 2026 lookback can invent original cohort vintages"). Therefore Sept 30 supports: (i) the *existence* of an as-issued descriptive risk fact, (ii) the *operational* finding that consumers were stale or silent. It does not support: any lift claim, any gate change, any v1 resurrection (frozen compatibility per the freeze §12), any threshold.
6. **Outcome-menu browsing.** DEFENSIVE_ROTATION's 12-outcome × 4-horizon grid and V0–V6 variants are exactly how a family of near-null tests produces one nominally attractive cell. Same discipline applies forward: the sector protocol must declare **one primary endpoint** and treat everything else as exploratory-never-claimable, or apply a preregistered Holm budget.
7. **Persistency illusion.** A warning that stays on for weeks will "cover" most onsets (the §9 pattern: radar elevated ~40bd before events, 5-day hazard spiking only at onset). Coverage without precision is the caution-persistence trap already documented: the 5-session persistence fact was found "far too common to become a prominent warning." Persistence must be scored as a *precision-conditional* claim, never as lead.

---

## 4. Reconstructed vs originally issued — classification of the record

| Item | Status | Evidentiary ceiling |
|---|---|---|
| Sept 30 `risk_state.v1` ELEVATED/63.3 + de-risk headline; `leadership_crack.v1` BROKEN (commit `b715204d`, data as-of Sep 30) | **Originally issued artifact** (retained git blob) | Descriptive fact only. Band modern-era lift 0.68× ⇒ no hit credit. Serving to a user NOT proven (absent from `macro.html`). |
| Sept 30 `risk_radar.v2` Caution / `state_ungated=risk-off` / `alert=false` / `macro_risk=Low` | **Originally issued artifact** | Descriptive; documents the deliberate gate clamp. |
| Oct 6 `leadership_crack.v1` INTACT (commit `856c5939`) | **Originally issued artifact** | Mandatory false-positive datum for any sector-watch grading: the hardware damage signal reversed *at the peak*. Must be in the FA record, not footnoted away. |
| Oct 8-data / Oct 9-generated `rotation_early_context/v1` (+6.217% XLP/SMH, +4.156% XLP/XLK, `active=[]`, availability UNKNOWN) | **Originally issued artifact**, availability unproven | First retained pair evidence; gradeable only as an observation with UNKNOWN availability, never as an issued alert. |
| Oct 9 RRG flips (XLK/Semis Leading→Weakening, XLP Lagging→Leading); subsector 1-week semis +3.00%→−3.13% | **Originally issued artifact**, vintage unproven | Descriptive corroboration; not a premarket alert. |
| SOXX/XLP Anticipation `TOSS_UP`, `direction_scored=false`; `turn_watch` null turns | **Originally issued artifacts** | Negative results; preserve. They are *unrelated forecasts* with explicit no-direction law — do not repurpose. |
| Oct 22 replay's "XLP/SOXX first sustained comparative observations Oct 8, 3-day confirmation Oct 12" | **Reconstructed** (per census) | Cannot count as issuance, lead time, or a delivered alert. For descriptive design context only. |
| "The watch would have fired on date X before the peak" (any form) | **Reconstructed / counterfactual** | Zero evidentiary weight without a provenance-provable issuance cohort. |
| Sept 30 Grey Deer envelope `FRAGILE`, `policy_count=0`; Oct 29 envelope DEGRADED (leadership Oct 23, rotation Oct 20) | **Originally issued artifacts** | Operational correctness evidence; explicitly not proof producers were down, and not a risk-off conclusion. |
| DEFENSIVE_ROTATION six-gate FALSIFIED verdict; V0–V6 all fail | **Frozen failed trial** | Preserve verbatim; no re-run, re-tune, or reinterpretation without a new dated prereg. |
| Leadership rotation H1/H2/H3 NOT_EXECUTABLE; P1 withheld (DEC) | **Frozen failed (pre-data) trial** | Preserve; V3 re-registration required before any read. |

The operational rule the protocol must encode: **grade the originally issued row, record the correction separately, never substitute the corrected or reconstructed value as the original** (keep-first ledger law; EW increment semantics 4 and 6).

---

## 5. Preservation orders (do not touch)

- `research/DEFENSIVE_ROTATION.md` — FALSIFIED/DISPLAY-ONLY; all six variants failed; no reevaluation without a new prereg (already "explicitly held" in the increment).
- Leadership rotation: prereg V1 blob `9d1313e0` / V2 `1fcd151c` / V2.1 `8f48509b` untouched; P1 withheld; `PREDICTIVE_CAPABILITY_QUALIFIED=NO`; V3 authoring belongs to the LR-W6 wave, not to EW-P3.
- `engine/risk_state.py` legacy v1 — frozen compatibility, never authority; the 0.68× finding stays.
- `engine/risk_radar.py` broad-market gate (SPY<200dma ∧ weak breadth; `can_force` requires above-base lift + validated confirmed leg) — preserved wholesale.
- Radar probability surface (`drawdown_prob`, `_PROB_CAL`) — under test by the DEC bar cohort; no retune, no threshold change, no authority grant. `DEC:RISK-RADAR-PROSPECTIVE-ISSUE-IDENTITY-NO-BACKFILL` stands.
- Anticipation (SOXX/XLP TOSS_UP), closed Trend Persistence trials, sealed study "C2" — unrelated/no-test.
- Active carriers and their owners: #10103 (merged renderer), #10104 (observation continuity, default-off), #10212/#10213 (PIT breadth drafts), #9035 (forensic), #9917 (Sector Central), Grey Deer #9957, Mastermind #1660/#1667 (production HOLD), Terminal #1103/#1132.
- DEC bar floors themselves: frozen before outcomes; may not be moved after any result (both DEC alternatives-rejected rows say so).

---

## 6. Pre-registered PIT evaluation protocol (EW-P3.T1 deliverable outline)

Proposed identity: `research/grey_deer/EW_SECTOR_WATCH_PIT_PREREG_2026-11-XX.md`, blob-pinned at merge to `origin/main` (LR V2.1 mechanics), with a committed look ledger and the invalidator/verdict-class law below. **Authoring owner: independent evidence scientist under EW-P3.T1; grading owners per §9.** Nothing below authorizes a probability, a policy, a send, or a threshold change.

### 6.1 Freeze mechanics
- Blob pin + harness refusal before any data read unless (a) prereg landed at reading head, (b) size/power artifact passed and committed, (c) look ledger readable, look = prior+1 (adopt `run_p1` gate pattern verbatim).
- Amendments: dated successor documents only; editing the prereg post-merge is invalidator `VOIDED`.
- **Constant-freeze law:** every numeric constant (δ_X, τ_S, persistence floor k, cooldown, FA budget, multiplicity m) frozen at authoring from (i) pre-2026-10 retained published tables, (ii) existing frozen law (e.g., DEC bar block lengths), or (iii) declared design rationale. **October 2026 observations may not set any constant.** If no lawful source exists for a constant, register the constant as "design default" with its rationale and its sensitivity band — declared, not tuned.

### 6.2 Targets — two event families + the genuinely sector-specific endpoint
Horizons H ∈ {5, 10, 21} sessions, aligned to the radar's existing H5/H10/H21 ≥5% max-loss forward-grader booleans (reuse the grader; **no recomputation from Yahoo history**).
- **E_MKT:** SPY max-loss ≥5% over H (identical to the existing grader's market leg; this makes B0/B1 pairing exact).
- **SEC:** registered semis proxy (SMH, and XLK as the broad-tech leg) max-loss ≥ τ_SEC over the same H. τ_SEC frozen at authoring (symmetric 5% is the lawful default; any other value needs a pre-October source).
- **EXCESS (primary sector-specific endpoint):** loss_SEC − loss_SPY ≥ δ_X over the same window, δ_X frozen at authoring. This is the endpoint that cannot be trivially repredicted by the market — nested sectors make raw sector loss mechanically collide with market loss; the excess form is what "sector-specific risk-off" must mean to be more than a market call in disguise. Where measurement law requires it: close-based max-loss (sector ETFs store close+volume only; VIX intraday highs only from 2026-05) — registered as a measurement limitation, never silently mixed with intraday bars.
- Onset definition: first session in the window at which the running max-loss first crosses the bar, computed from prospectively recorded grader rows only.

### 6.3 Issuance object and state machine
- The graded object is an **issued warning receipt**, not a recomputed signal: built by the incumbent `rotation_events`/`leadership_rotation_context` producers, carried through the envelope as display-only context (DEC:ROTATION-RISK-CONTEXT-REUSES-OBSERVATIONS), recorded keep-first in an issued-row ledger (pattern: `data/risk_radar/forward_log.jsonl`).
- Grades: `EPHEMERAL` (1 issued session), `CONFIRMED` (≥k consecutive issued sessions, k frozen), `WITHDRAWN`, `CORRECTED`, `ABSTAINED(reason)`. First eligible observation non-notifying (baseline non-send law).
- **Abstention semantics (explicit):** unqualified source, rights-blocked row, stale/degraded data, or availability UNKNOWN ⇒ `ABSTAINED`, never calm and never zero. Abstention-during-event scores as a **miss** (with its reason recorded); abstention-during-calm scores as correct abstention; abstention is never free when inputs were qualified (that is a coverage failure, Grey Deer gate 8).

### 6.4 Clocks, correction clocks, rights, membership
- Required per row: `event_ts, observed_ts, available_at, ingested_at, built_at, decision_cutoff, issued_session, graded_at, corrected_at?` — the census's failures (UNKNOWN availability, null `available_at`, timezone-naive `generated_utc`) become hard validity gates, not caveats.
- **Correction clock:** a warning graded as of each `decision_cutoff` uses the row known at that cutoff. Same-session corrections are not new news; in-flight sent/served warnings require follow-on correction records. Correction latency distribution (issue→correction) is itself a reported metric. A warning corrected before the horizon matures still counts as issued for FA scoring (keep-first); it is never rewritten as "not issued."
- **Rights & membership:** rows admitted only if source rights qualified (PULLBACK_SOURCE_RIGHTS_QUALIFICATION pattern) and membership is membership-as-known at issue (the 42-name hardware cohort law). Amended 2026 pricing vintages are prohibited as live originals (EW-P3.T2). Violations: row excluded, cohort flagged, and repeated violation is invalidator `VOIDED`.

### 6.5 Cohort identity and maturity
- Cohort = exact (watch-definition fingerprint ∏ producer build hashes ∪ membership-vintage law ∪ prereg blob). No backfill; no mixing fingerprints (DEC identity law). One cohort per definition change; definition change mints a new lineage, history not restamped (Grey Deer episode-identity rule).
- Maturity floors **inherited from the DEC bar** (≥252 issued sessions, ≥300-day span, per-horizon ≥200 graded rows, ≥20 event rows, ≥50 non-event rows, ≥5 overlap-aware event clusters) **plus** the sector-specific floor: ≥5 *sector-excess* event clusters and ≥12 adverse outcomes overall (Grey Deer gate 2 floor) before any "leading" language. If sector-excess events accrue slower than market events (likely), the cohort honestly reports `IMMATURE` longer — that is a feature, not a defect to be engineered around.

### 6.6 Baselines — conditional, per the task's requirement
- **B0 unconditional** paired per-row baseline (the DEC bar's construction; enables Brier-delta reuse).
- **B1 broad-market conditional (the key one):** within strata of the issued radar state/probability, does the sector watch improve prediction of E_SEC and E_XCESS? Concretely: paired Brier delta of the watch versus the radar's own issued H5/H10/H21 probability as baseline on sector targets. A sector watch that only repredicts the market fails B1 and is redundant, whatever its raw lift.
- **B2 naive rotation baseline:** leak-free persistence proxy (prior-session relative-return sign; trailing 5-session relative strength). The watch must beat B2 or match it with materially fewer false alarms — otherwise the honest product is B2 rendered as context.
- **B3 gate-silence conditional:** all lift metrics reported *within* the broad gate's silent regime (index strong) — the segment the watch exists to cover. Overall-sample lift is reported but non-primary, because outside the silent regime the radar already speaks.
- Statistical law: paired deltas, 90% circular moving-block bootstrap, block length = horizon (5/10/21), 2000 draws, fixed seed (DEC bar convention), **cluster-aware** honest-N (overlapping windows within horizon length = one cluster); mean/CI endpoints frozen.

### 6.7 Endpoints, gates, multiplicity, sample dependence
- **Primary endpoint (one):** B1-conditional paired Brier skill of `CONFIRMED` watch vs B1 baseline on **E_XCESS at H10**, prospective cohort, mature floors met, CI upper < 0. Secondaries (Holm over a preregistered family of at most m=6, mirroring LR V1's discipline): lead-time, FA budget, persistence-precision, H5/H21, E_SEC vs radar, B2 comparison. The DEFENSIVE_ROTATION-style outcome menu is exploratory-never-claimable.
- **Lead time:** distribution of (onset − first *issued* `available_at`, not `built_at`) among hits; "LEADING" label only if median lead ≥1 full session and p25 > 0 (Grey Deer gate 6), else the label is "coincident." Incremental lead vs the radar's own lead reported (does the sector watch precede, or merely shadow, the broad signal?).
- **False alarms:** alarm = a warning burst (registered cooldown, so persistence cannot masquerade as multiple alarms). FA = burst with no qualifying endpoint within H_max of the same family. Budget: ≤2 non-event critical sector episodes per quarter (adopt Grey Deer gate 7). Oct 6 `leadership_crack` INTACT-reversal is in-scope FA history once a cohort exists.
- **Persistence:** preregistered k-session confirmation; persistence-conditional precision curve as a secondary; the CAUTION-PERSISTENCE precedent's honest outcome ("useful as duration context, far too common to be a prominent warning") is the prior, and the same display-only ceiling applies to any persistence fact.
- **Abstention:** abstention rate, abstention-during-event (misses), coverage of declared critical inputs ≥80% (gate 8). Availability-weighted reporting; a cohort dominated by abstentions reports `SOURCE_LIMITED`.
- **Sample dependence / nested sectors:** honest-N = clusters, never rows; block bootstrap; era stratification reported (2020+ prospective only accrues, so era claims are structural: leave-one-crisis-out is `NOT_EXECUTABLE` unless a provably vintaged reconstruction cohort exists — say so, don't fake it). Multiplicity across nested families: **one primary sector family (SMH semis + XLK tech)**; at most m secondary sector groups under the Holm budget; the 41 themes / 269 subsectors are descriptive-only forever unless separately preregistered. Correlated-evidence law: both ETF legs derive from the same Yahoo equity prices — they are one observation lineage; any "two independent confirmations" language is an invalidator, and confluence arithmetic is banned (DEC:ROTATION-RISK-CONTEXT-REUSES-OBSERVATIONS).
- **Power precondition:** no cohort read until a committed size/power artifact (T12R/T13R pattern: per-cell simulation at registered margins, M ≥ 400 OK sims, two-part size rule) reports `SIZED` and `POWERED_IN_PRINCIPLE`. Underpowered ⇒ `UNDERPOWERED`, never `NOT_SUPPORTED` (LR V2.1 row-law). Margins never lowered to pass.

### 6.8 Verdict classes and invalidators (adopt LR V2.1 vocabulary)
`VOIDED:<k>` · `NOT_EXECUTABLE` · `SOURCE_LIMITED` · `IMMATURE` · `UNDERPOWERED` · `DEVELOPMENT_PASS/FAIL` (synthetic/retained-artifact reads only, never a claim) · `NOT_SUPPORTED` (binding) · `INSUFFICIENT` (non-binding) · `CONSISTENT` (descriptive tier) · `SUPPORTED` (forecast tier, prospective only). Invalidators include: any backfilled row; amended vintage admitted as original; any constant touched post-outcome; cohort fingerprint mixing; grading a corrected row as original; rights-unqualified admission; window/threshold redefinition after seeing outcomes; cross-vintage merging of source clocks.

### 6.9 Falsifiability (what kills each tier)
- **Watch tier dies if:** at maturity, B1-conditional lift on E_XCESS has CI upper below the registered floor (⇒ demote to raw observation card, drop "watch" language); FA budget exceeded in two consecutive quarters (⇒ auto-demotion + owner review); persistence fails to improve precision in both halves (⇒ persistence claim dropped); coverage <80% sustained (⇒ `SOURCE_LIMITED`, ship nothing).
- **Forecast tier dies if:** paired Brier delta ≥0 or its 90% CI upper ≥0 ⇒ `mature_refuting` under the DEC bar; calibration-in-the-large CI excludes 0 ⇒ systematic bias, no promotion review; B1 fails while B0 passes ⇒ the watch adds nothing beyond the broad radar (redundancy refutation).
- **September-30-style post-hoc arguments are structurally barred:** no single retrospective episode can flip any verdict class; the only retrospective role of Oct 2026 is *descriptive design context* recorded in the audit trail.

### 6.10 Maturity honesty
With ≥252 issued sessions / ≥300 days and ≥5 sector-excess clusters, the earliest possible forecast-grade read is roughly a year out, plausibly longer for sector-excess events. The descriptive watch may ship earlier (§8); the forecast tier cannot be hurried, and EW-P3.T3's `prohibited_until_review` posture is correct and preserved.

---

## 7. Weakest assumptions (ranked, most fragile first)

1. **That 2-session ~6% relative-wealth swings are informative rather than ordinary.** n=1; no distributional evidence exists for the trigger magnitude; the watch's visual salience currently rests entirely on October's single draw.
2. **That ETF closes are a faithful PIT proxy for "semis leadership."** Back-adjusted vintages, membership drift, close-only storage, and 2026-05-onward VIX OHLC all degrade the measurement; reconstructed ratios ≠ as-issued ratios.
3. **That sector-excess events are frequent enough to ever mature.** If E_XCESS clusters accrue much slower than market events, the cohort lives in `IMMATURE` indefinitely; the bar must be allowed to say that rather than silently substituting E_SEC or E_MKT (endpoint substitution would be an invalidator).
4. **That the radar gate's selectivity is correctly calibrated in the modern era.** The gate's own FA/coverage tradeoff has no prospective cohort either; the watch's incremental-value framing (B3) is only as good as the gate strata it conditions on.
5. **That issuing a strong-tape watch does not degrade broad-alert response.** The cry-wolf externality is unmeasured and plausible; the FA budget measures the watch's own FAs but not the behavioral spillover — it must be reported as an open risk, not assumed away.
6. **That prospective rights/vintage stability holds.** Vendor licensing is explicitly held as unknown; collectors are young; a rights break mid-cohort converts the cohort to `SOURCE_LIMITED`.
7. **That membership-as-known is recoverable per session going forward** for every cohort named in the watch (the 42-name cohort shows the pattern is definable; whether the collector persists it every session is unproven).
8. **That "review concentration" guidance changes user behavior at all.** The utility claim of tier A is a behavioral hypothesis with no measurement; the honest wording is "may be decision-relevant," graded by whether users open the linked context, not by market outcomes.
9. **Regime stability of anything validated:** the 0.68× modern-era death of the composite band is the standing reminder that lift claims decay; every promotion must carry an era re-qualification rule.

---

## 8. Objective criteria: descriptive watch vs forecast vs governed policy

| | **A — Descriptive watch** | **B — Forecast** | **C — Governed policy** |
|---|---|---|---|
| **Claim** | "A measured leadership fact changed; review X" | "P(loss ≥τ within H) = p, lift ×L, FA rate f, lead ℓ" | "Restrict/suppress actionability per registered rule" |
| **Entry criteria** | Issuance pipeline qualified (complete clocks, rights, membership-as-known, abstention semantics); definition preregistered; FA/persistence/abstention scoreboard accruing; ≥60 issued sessions of descriptive scoring before any prominence increase; Oct 6-style reversals shown in the record | DEC bar floors met (252 sessions/300d/200 graded/20 event/50 non-event/5 clusters per horizon) + paired Brier CI < 0 + calibration CI ⊃ 0 + Grey Deer gates 1–8 (≥30 episodes, ≥12 adverse, AP ≥1.25× with LBB >1.0, slope 0.7–1.3, era sign stability, lead gate, FA ≤2/quarter, coverage ≥80%) + B1 conditional-increment over the radar + SIZED/POWERED artifact | Grey Deer new-entry gates (≥40 decisions, ≥12 adverse, ≥1 quarter/60-session shadow, ES or max-DD improvement ≥15% both halves, LBB >0, downside/upside ≥1.33, ≥70% in-scope, FP budget held, Fable adversarial review + Sol acceptance + Chairman approval); size authority adds ≥20 prospective firings; automatic exit not eligible v1 |
| **Language ceiling** | No probability, no "risk-off," no crash language; duration/persistence shown as context with the too-common caveat; explicit invalidator on card | Probability printed with lift/FP/lead; "odds, not a forecast" framing per §9 discipline; never routes selection/direction | `temporary_operator_safety` only path before statistics: labeled, scoped, time-boxed (≤10 sessions / 2 settled post-REPAIR_CONFIRMED / Chairman revocation / fixed expiry), new decision ID per renewal, never de-escalates on stale data |
| **Authority ceiling** | Display only; cannot gate/rank/size (`envelope_may_*` all false) | `promotion_review_eligible=true` only; never sets `current_model_validated` or market authority | Individually authorized policy rule + graded reflex; Reflex Registry/QLedger receipts |
| **Demotion/exit** | FA budget breach ×2 quarters, sustained coverage <80%, definition drift ⇒ revert to raw observation card | `mature_refuting` or B1 redundancy failure ⇒ no promotion review; cohort dies with fingerprint | Fixed expiry / REPAIR_CONFIRMED / Chairman revocation; renewal requires new decision ID |

The transition rule between tiers is one-directional and evidential: A never implies B; B never implies C; each promotion is a separate reviewed decision with its named owner (EW-P3.T3 posture preserved).

---

## 9. Named existing grading owners (no new plane)

- **QLedger / Evaluation OS** — outcome grading (DEC:RISK-EPISODES-USE-CHRONICLE-AND-REFLEXES).
- **Chronicle** — settled hazard-episode state-transition history.
- **Reflex Registry** — trigger→action firing ledgers for any C-tier graded rule.
- **`data/risk_radar/forward_log.jsonl`** (keep-first issued-row ledger) and **`engine/risk_radar_scorecard.py`** (`risk_radar_prospective_validation_readiness.v1`) with `tests/test_risk_radar_scorecard.py` — the frozen DEC-bar evaluator and its cohort source.
- **The existing radar forward grader** (≥5% max-loss booleans, H5/H10/H21) — outcome source for E_MKT; sector legs grade on the same grader pattern, same nightly advancement law.
- **Producers (measurement owners):** `engine/rotation_events.py`, `engine/leadership_rotation_context.py`, `engine/risk_envelope.py` (pure composer; envelope owns no forward ledger per DEC:RISK-ENVELOPE-IS-CANONICAL-DERIVED-PROJECTION).
- **Workstreams:** `WS:GREY-DEER-RISK-INTELLIGENCE` (canonical risk/transition/policy), `WS:LEADERSHIP-ROTATION-INTELLIGENCE` (sector/theme measurement).
- **Carriers:** #10104 (observation continuity + opt-in outbox bridge), #10212/#10213 (PIT breadth drafts), #9035 (forensic programme), #9917 (Sector Central), Grey Deer #9957, Mastermind #1660/#1667, Terminal #1103/#1132, existing notification/outbox owner (`public.alert_outbox` unique `fire_event_id`, drain, mailer).
- **Science harness precedent:** `scripts/leadership_rotation_study.py` / `scripts/leadership_rotation_inference.py` blob-pin + size-gate + look-ledger pattern; LR V3 re-registration wave (DEC:LEADERSHIP-ROTATION-P1-WITHHELD…) owns its own statistics, not EW-P3.
- **Promotion decisions:** radar probability promotion review per the DEC bar; policy authority per Grey Deer §10 (Fable adversarial review, Sol acceptance, Chairman approval).

---

## 10. Constraint compliance and non-authorization

No historic Yahoo data was recomputed and no price series was retrieved (all statements above come from retained research documents and decision records read at pinned commits); no model was fit; no code was changed; no file in any repository was written; no probability, threshold, alert, or policy is authorized or proposed for authorization by this review. The protocol in §6 is an outline for the named EW-P3.T1 owner to author, freeze, and blob-pin; until then EW-P3.T3's `prohibited_until_review` stands, the broad-market gate stands, the frozen failed trials stand, and the descriptive watch — if shipped at all — ships under tier-A language only.

**Bottom line:** keep the broad gate; ship the sector watch as a named, clock-complete, abstention-honest *descriptive* observation with a registered FA budget; earn every quantitative claim from a blob-pinned, conditional-baseline, cluster-aware prospective cohort under the existing DEC bar and Grey Deer gates; treat September 30 ELEVATED as an as-issued descriptive datum riding a 0.68× band — motivation, never evidence; and let nothing in October 2026 set a single constant.
