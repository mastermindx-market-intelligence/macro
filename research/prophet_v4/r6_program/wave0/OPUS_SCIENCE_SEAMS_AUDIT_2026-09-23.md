# Opus adversarial audit — R6 science seams (D03/D06/D07/D08, Q01–Q08)

Commissioned 2026-09-23 by the Fable Meta-CEO seat (session 48cdfd56) as an adversarial auditor (Claude Opus, `reviewer` route) under the Chairman's live routing instruction; the seat adjudicates. Read-only; no repo writes by the auditor. Reviewed at #7809 head f98e72fb2a57. Status PARTIAL by the auditor's own account (turn-limited; see GAPS).

---

STATUS: PARTIAL

RESULT:

**Blockers (B): these prevent honest closure of a D-decision**

B1 — The Cycle H252 primary (H126/H504 supporting) cannot support a formal read, and no limit on its claim is registered in advance.
- Citations:
  - `effective/PROPHET_US_MASTER_PLAN_R6.md:249` proposes "H252 primary; H126/H504 supporting".
  - `baseline_r5/inputs/PROPHET_US_EARNINGS_CYCLE_R4.md:225`: "Thousands of firms inside one recovery are not thousands of independent cycles."
  - `research/prophet_v4/CELL_G_FLAGSHIP_VOI_MEASUREMENT_LAW_2026-08-22.md:373`: "Fewer than 20 effective clusters on an applicable axis is `UNESTIMABLE`".
  - `research/PROPHET_CONDITIONAL_FUSION_MASTERPLAN_BY_FABLE.md:909`: embargo "≥ the longest horizon graded".
  - `DECISION_RESOLUTION_PLAYBOOK.md:76` (D06 step 3) says to count market cycles but never says what happens when there are too few.
- Failure it causes:
  - With one domain and perhaps 2–4 vintage-clean industrial cycles, differences between firms inside one or two recoveries can yield a "significant" H252 result. That is a false positive from dependent data.
  - Registering H504, even as supporting, forces a 504-session embargo if it counts as a graded horizon, which leaves almost no usable folds.
- Smallest repair: before D06 closes, register the cycle episode as the unit of inference. Cap Cycle's confirmatory claim at `DESCRIPTIVE_ONLY` unless the Cell G N_eff floors for date, issuer and cycle are met. Declare H504 descriptive-only and outside the embargo definition, or compute and publish the fold count in advance.

B2 — D06 is asked to set floors and margins that frozen repo law already fixes, and R6 never cites that law.
- Citations:
  - Cell G:24 requires "**zero allowed degradation margin**" on lead time, actionability and chase for flagship-early claims.
  - Cell G:295–298 sets a 70% broad-coverage floor.
  - Cell G:346–348 requires 50 matured episodes and N_eff(date) ≥ 20 and N_eff(issuer) ≥ 20.
  - Cell G:389–395 requires one primary endpoint per experiment, with Holm correction.
  - Cell G:405–410 sets a fixed-look default.
  - A grep of the whole handoff directory for "Cell G", "Holm", "fixed_look" and "N_eff" returns zero hits.
  - `DECISION_RESOLUTION_PLAYBOOK.md:75`: "Define the minimum worthwhile gain, maximum tolerated degradation and coverage floor from that job".
- Failure it causes: Early Leadership (EL) is an earlier-recognition claim (docket Q03:51, Q04:73). D06 as written could adopt a nonzero lead-time degradation margin, a looser coverage floor or repeated looks. Each of those is a contract violation that could promote a false positive.
- Smallest repair: D06 step 1 names Cell G as the governing measurement law. The closure artifact carries every Cell G §3 metric-contract field (Cell G:105). Any departure is a versioned amendment that applies going forward only.

B3 — Every "better than" or "earlier than" claim lacks a registered control population and a way to compute it.
- Citations:
  - `agentos/workstreams/WS-PROPHET-US-V4-RECOVERY.md:103–105`: the QLedger control leg was never populated on 46,630 claims, and the plan ledger has no benchmark column.
  - Cell G:52 requires `UNAVAILABLE_FIELD` rather than synthesized benchmark values.
  - The D06 owner is "Existing Evaluation/QLedger" (`effective/DECISION_REGISTER.json:165`), and D06 step 4 persists "benchmark … through the existing evaluation owner" (`DECISION_RESOLUTION_PLAYBOOK.md:77`).
  - The only existing benchmark forward-fills SPY onto each name's calendar (`PROPHET_US_MEASUREMENT_R2.md:38`).
  - R2's four controls apply only "where lawful" (R2:137), and historical sector is rejected as a decision-time input (R6:101).
- Failure it causes: reads compare against a control that is empty, or a forward-filled SPY, or a sector labelled with today's classification. The result is a false or unestimable "better than".
- Smallest repair: for each study, register the control arms as same-tape computations with B06 as the build owner:
  - cash;
  - SPY on the same clock with no forward-fill;
  - a point-in-time (PIT) sector comparator frozen at decision time, or declared `UNAVAILABLE`;
  - incumbent V3 on the identical field.
  
  Any claim whose control is `UNAVAILABLE_FIELD` is capped at descriptive.

B4 — D07/D03: the "public-information replay" class loosens the D5 admission rule, and historical Earnings (and Cycle) evidence is mostly that class.
- Citations:
  - `PROPHET_US_MEASUREMENT_R2.md:86`: a later-captured filing "may support a separate public-information replay with an explicit acquisition assumption".
  - `DECISION_RESOLUTION_PLAYBOOK.md:89` says only that such a document "is not observed-as-run evidence".
  - `WS-PROPHET-US-V4-RECOVERY.md:121–125`: admission requires both `source_available_at <= cut` and `observed_at <= cut`; "admitting it is lookahead".
- Failure it causes: pre-capture Earnings history mostly has `observed_at` after the cut or unknown. The H42 historical cohort would be built from rows that fail the admission rule. The bodies may also be later-corrected versions, and these rows could be pooled into a formal read.
- Smallest repair: D07 registers these rows as a named class (for example `PUBLIC_INFO_REPLAY`) with a declared acquisition lag and a sensitivity analysis. The class is never pooled with observed-as-run rows and never carries promotion weight. Bodies are read only through `read_event_source_revisions`. For each sleeve, D07 states whether any confirmatory read is possible before prospective accrual.

**Material bias (M)**

M1 — The unit of the timing primary endpoint is not registered, and the absolute version mechanically favours earlier arms.
- Citations: R2:121, R2:125, R2:141; R6:402; docket Q04:81.
- Failure it causes: the early arm holds equity for more of H10 while the other arms sit in cash at 0. It "wins" through market drift and capital-days in a rising tape, not through timing skill. The effect depends on the regime.
- Smallest repair: register the primary as the same-clock, market-excess, full-opportunity difference (or value per capital-day). Keep the absolute result as supporting. Disclose whether the current regime is in-sample.

M2 — Horizon multiplicity and prior visibility of outcomes.
- Citations: docket Q04:81 and Q06:125; R6:247–251; D06:79.
- The role of supporting horizons is not fixed: nothing says they cannot gatekeep or rescue a failed primary (Cell G:391).
- H21/H42/H63 already exist on the legacy grade ruler (R2:31), so their outcomes have already been produced.
- `b4_entry_policy_calibration/PREREG.json:91` makes H5/H10 co-primary on the same prospective EL tape as the new H10 timing study.
- `PROPHET_US_EARNINGS_CYCLE_R4.md:127`: H63 straddles the next quarterly report.
- Failure it causes: the "blind" horizon choice cannot be verified for Earnings, and the same EL outcomes are read under two registrations.
- Smallest repair:
  - Supporting horizons are descriptive-only, with no rescue authority.
  - Log prior legacy-ruler looks in the trial ledger.
  - Declare #7751 and the EL timing study one search family.
  - Flag H63 as crossing the next earnings event.

M3 — The #7751 decision law tests "any of K" with no multiplicity correction and treats nonsignificant harm as acceptable.
- Citations:
  - `PREREG.json:117`: "improvement in at least one adverse-tail endpoint".
  - `PREREG.json:118`: "no confidence-supported degradation".
  - This contradicts D06:78 ("A nonsignificant harm estimate is not non-inferiority") and R6:424.
  - `PREREG.json:95`: `net_return_after_measured_or_floor_costs` has no registered floor value.
  - No treatment is defined for rows refused by a gated cell.
  - Q18 consumes results "under that contract" (docket:391).
- Failure it causes: C1 is "supported" by one of many (endpoint × horizon) tests crossing by chance, while a wide interval hides harm. The cost floor can be chosen at read time. An admitted-rows-only mean shows gain purely by selection.
- Smallest repair: amend before capture starts. The cohort starts only after the merge (`PREREG.json:27`), and "Merge ad481059…" is still an open obligation in `CURRENT_CARRIER_FRONTIER.json`. The amendment should register:
  - one adverse-tail primary endpoint and one horizon;
  - Holm correction across the distinct cells;
  - a numeric non-inferiority margin tested on the lower bound;
  - a numeric cost floor;
  - full-opportunity cash treatment for refused rows.

M4 — #7751 has alias cells, no two-axis cell, and a unit definition that allows repeated rows.
- Citations:
  - `PREREG.json:60–62` equals `:80–82`, so C2 ≡ C6.
  - `PREREG.json:70–72` equals `:85–87`, so C4 ≡ C7.
  - `B4_ENTRY_POLICY_CALIBRATION_PREREG_2026-09-23.md:37` calls C6/C7 "combinations".
  - `PREREG.json:34`: the unit is "episode at one decision instant".
- Failure it causes:
  - Alias pairs can be reported as corroborating each other, or can distort the Holm family.
  - No cell tightens both axes, so the interaction those labels promise cannot be identified.
  - One episode can supply many instants toward the 300 floor.
- Smallest repair: an amendment with an alias map collapsing to 6 configurations; one instant per episode (the first admissible); report N_eff for date and issuer; add a both-tight cell before capture only if the interaction is wanted.

M5 — Q07/Q08 select the universe by coverage, which favours survivors and makes the Q08 falsifier untestable.
- Citations: docket Q07:141; Q08:163 and Q08:173; D03:38.
- Failure it causes: coverage measured on today's data keeps survivors. The falsifier "outcomes improve only after failed firms are excluded" cannot fire if failed firms are missing because of the data.
- Smallest repair: evaluate coverage at each historical cut among the issuers listed then. Pre-register a terminal-value coverage floor below which the result is `UNESTIMABLE`, and name the missing cohort.

M6 — Q07 can shop for a domain and can never reject Cycle.
- Citation: docket Q07:149: "One admissible pilot domain … or a documented alternative".
- Failure it causes: the process iterates over domains until a turn appears, with no terminal "no domain supports Cycle". The candidate domain was named by researchers who already know the recent cycles.
- Smallest repair: register a finite ordered domain list and the readiness rule before inspecting any series. Add a `NO_ADMISSIBLE_DOMAIN` outcome and count domains in the search family.

M7 — Q05 uses current-only group membership and overstates group-level N.
- Citations: docket Q05:97; R6:472; Cell G:352.
- Failure it causes: today's memberships were formed after the winners moved. Rows inside one group shock get counted as many observations.
- Smallest repair: the current-only cohort is retrospective diagnostic with zero confirmatory credit. The unit of inference is the group-episode, with N_eff(theme) ≥ 5.

M8 — D07 allows LLM extraction errors that correlate with outcomes.
- Citations: R6:163; D07:90.
- Failure it causes: an audit that is faithful on average does not rule out hindsight leaking in through the extraction step.
- Smallest repair: stratify the extraction audit by later outcome. Use deterministic XBRL facts where they exist.

M9 — D08 relies on numbers with no measured source.
- Citations:
  - `CURRENT_CARRIER_FRONTIER.json`: #7734 "Measured facts only; no calibrated policy or capacity authority"; #7738 "Operation constants remain uncalibrated".
  - R2:165: 50 bps "is a policy parameter, not a measured all-in round-trip cost".
  - Docket Q04:79 permits the incumbent next-close convention.
  - R6 never cites the Entry Radar PIT NBBO plane; only `B4_ENTRY_POLICY_CALIBRATION_PREREG_2026-09-23.md:25` does.
  - Nothing in R6 measures source-to-visible latency. The 300 s NBBO age is a gate, not a latency measurement.
- Failure it causes: the 50/300 constants get used as costs, and the cost range is chosen freely. Arms could use different conventions. Historical pullback fills cannot be identified from OHLC data.
- Smallest repair: the D08 artifact classifies every field as measured, estimated or unknown, with its source. Use one convention across arms. Register a numeric cost range with its source. Historical pullback-arm results are reported as bounds only.

M10 — D06 has no plan for repeated looks or futility, and none of the house adjudication-coverage outputs.
- Citations: `DECISION_RESOLUTION_PLAYBOOK.md:79–81`; repo CLAUDE.md § Adjudication coverage gate.
- Failure it causes: a long-horizon `INCONCLUSIVE` becomes a permanent state that invites repeated reads. Exemplars, whether today is in-sample, honest-N and the missing panel are never reported.
- Smallest repair: register either a fixed look or a sequential-safe design, plus a futility horizon. Add fields for exemplar coverage, current-regime in-sample status, episode honest-N and missing panel.

**Clarity (m)**

m1 — The 2026-08-14 PIT-reconstructed rows remain unmarked (`WS-PROPHET-US-V4-RECOVERY.md:142–145`), so the Q01/Q02 as-run census will misclassify that session. Repair: tag the session as PIT replay in the evidence matrix.

m2 — Q04, Q06 and Q07 have no check against earlier killed constructions: `DNR:KILL-FRESH-TICKS-WINDOW`, `DNR:KILL-STAGE-WIN-GATE` and `DNR:KILL-S10-MARGIN-RECLAIM`. Repair: add an equivalence check and count those prior looks.

m3 — Q03 does not register a `positive_label_id` for "useful" or a retrieval-volume-matched placebo (Cell G:97 and :451). Q02 picks the largest loss with no rule for when uncertainty prevents a pick (docket Q02:39). Repair: register both before any read.

**Self-refutation: the three findings most likely to be wrong**

1. **B2:** D06 step 4 ("Where existing law fixes an alpha/error rule or sample floor, preserve it", playbook:77) may already incorporate Cell G. Cell G is marked `SOL_FROZEN`, and I did not verify whether the 09-06 Chairman override retired Sol-era laws. If it did, B2 drops to a minor citation gap.
2. **B4:** R2:44–50 and D07 step 3 already stop replay from claiming "what the system knew". If the Evaluation owner already forbids pooling replay rows into confirmatory reads, this is M, not B.
3. **M3/M4 "amend before capture":** I could not confirm that #7751 capture has not started (the frontier says `NOT_RECHECKED_R5`). If it has, the amendment is no longer pre-outcome and must start a new evidence era.

**Verdict:** None of D03, D06, D07 or D08 can be closed honestly from the current docket.
- D06 needs, first:
  - explicit binding to Cell G;
  - a registered control population for each claim, given that QLedger has no control leg;
  - a same-clock excess primary for the timing study;
  - supporting horizons fixed as descriptive-only;
  - a Cycle claim cap tied to independent cycle episodes;
  - a look and futility plan;
  - a pre-capture amendment to #7751 (aliases, any-of-K test, cost floor, refused-row treatment, non-inferiority margin).
- D07 and D03 need, first: a named public-information-replay class that never mixes with the D5 admission rule, and survivorship-free coverage criteria evaluated at each historical cut.
- D08 needs, first: a register classifying each field as measured, estimated or unknown. Today every cost and fill number is an uncalibrated policy constant, #7734 is live-only, and no latency has been measured.

None of these repairs requires redesigning the program. Each is a pre-registration item the seat can freeze before any outcome read.

EVIDENCE:
Files read:
- `research/prophet_v4/r6_fable_meta_ceo_handoff/effective/RESEARCH_DOCKET.md` 1–532.
- `research/prophet_v4/r6_fable_meta_ceo_handoff/DECISION_RESOLUTION_PLAYBOOK.md` 1–161.
- `research/prophet_v4/r6_fable_meta_ceo_handoff/effective/PROPHET_US_MASTER_PLAN_R6.md`: lines 60–89, 147–236, 313–432, 592–631, plus grep hits.
- `research/prophet_v4/r6_fable_meta_ceo_handoff/baseline_r5/inputs/PROPHET_US_MEASUREMENT_R2.md` 1–358.
- `research/prophet_v4/r6_fable_meta_ceo_handoff/baseline_r5/inputs/PROPHET_US_EARNINGS_CYCLE_R4.md` 205–215, plus grep hits at 127, 225 and 241.
- `research/prophet_v4/r6_fable_meta_ceo_handoff/CURRENT_CARRIER_FRONTIER.json` 80–140.
- `research/prophet_v4/r6_fable_meta_ceo_handoff/work_cards/Q18.md` (full).
- `research/prophet_v4/CELL_G_FLAGSHIP_VOI_MEASUREMENT_LAW_2026-08-22.md` 1–125 and 283–462.
- `research/prophet_v4/B4_ENTRY_POLICY_CALIBRATION_PREREG_2026-09-23.md` 1–66.
- `research/prophet_v4/b4_entry_policy_calibration/PREREG.json` 1–134.
- `agentos/workstreams/WS-PROPHET-US-V4-RECOVERY.md` 55–154.
- `research/DO_NOT_REBUILD.md`: grep hits plus rows 120 and 126.
- `research/PROPHET_CONDITIONAL_FUSION_MASTERPLAN_BY_FABLE.md`: grep hits 909–914 and 1401.

Greps run: whole handoff directory for Cell G, Holm, N_eff and control-leg terms; all 24 work cards contain "support, rejection or inconclusive".

GAPS:
- The review is partial because the coordinator stopped my reading early.
- R6 master plan: §§1–2 beyond lines 60–89, §§14–19 and §§21–25 were not read closely.
- I did not read `PROPHET_US_RESEARCH_R1.md`, `PROPHET_US_EARLY_LEADERSHIP_R3.md` (one grep only) or `CELL_F_D5_CONTRACT_AMENDMENTS_2026-08-26.md` A7–A9; for the last I relied on the WS record's quotation of it.
- Cell G §§4–6 and §13 onward were skimmed only.
- The Conditional Fusion §9 full text was not read; the embargo wording is based only on the 909–914 grep.
- I used no network, so I could not verify the live state or diffs of PRs #7734, #7738 and #7751, or whether #7751 capture has started.
- `data/` is sparse-omitted in this worktree, so no empirical counts (cycles, coverage, Aug-14 rows) were checked.

DEVIATIONS:
- I did not use the 3 extra R2 greps the coordinator allowed, because I had already read R2 in full.
- I wrote no files and ran no git write commands.
