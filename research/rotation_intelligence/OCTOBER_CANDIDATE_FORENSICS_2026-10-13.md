# October rotation: original candidate-record forensic audit

Date: 2026-10-13 UTC. Continuation of `rotation-intelligence-architecture-20261012`, existing research PR #9035. Parent mission incomplete. This audit changes no production recommendation, scoring rule, entry gate, Plan, ledger, notification or portfolio holding.

## Result

The candidate records support specific detection and presentation failures, not a single blanket finding that Mastermind saw none of the defensive opportunities. WMT was persistently blocked at the counter-trend filter. COST entered the raw buy lane on September 30 but never became Featured in the inspected records; it later became ran/pending-expired. ABBV entered on October 8 but was also not Featured. KO was excluded as an old, topped/rolled-over entry despite positive stored residual alpha. WM remained a raw gate rejection with no theme association in the retained columns. MCK provides counterevidence to a universal defensive miss: it qualified October 5 and became Featured October 6 and October 8.

**Important correction after tracing the source:** `alpha_below_floor` here is a **Featured shortfall**, not a universal candidate-admission failure. Both ABBV's October 8 row and COST's September 30–October 5 rows are in `more_actionable`, not a rejected-alpha population. A research claim that they were rejected entirely because of alpha would be wrong. Neither a raw `buyable=true` flag nor `more_actionable` proves B4 ENTRY_OPEN, a newly originated Plan, or user delivery.

## 1. Source identity, methods and limits

Macro source/archive snapshot: `317f2c06090d15347fe8117290a0e13ad2e2ad5b`. The existing documentation carrier remains PR #9035, originally at `a0c142607de2651acc987c84a393b0f7b1223036`. Protected procedure pin remains `Mastermind@7d60119c4e1dab35a65f0d80cc3234140bac17ef`; no unrelated re-bootstrap was needed.

The inputs are exact Git blobs copied into an isolated evidence input root, not reconstructed price-based candidates and not a current production board capture:

| Original archive path | Git blob | SHA-256 | Bytes / rows |
|---|---|---|---|
| `data/us_prophet_rank/candidates/2026-09.parquet` | `b3e3d7e19df9f9a40479e4d76e2e58503b3184f3` | `7fcafb328bfe74e54af3eb92f158ce4846f7928e05e60dc91a38287c17a29db2` | 10,066,463 / 70,476 |
| `data/us_prophet_rank/candidates/2026-10.parquet` | `e8482d6a5274a00b1406df9286db20e948d4d78d` | `fa666fff511c0d94e4c4cf3a97f07b198c9e864da4816f2f87ef487d0555fd4f` | 3,439,002 / 26,113 |

The owner `engine/us_context_vector.py:_store_dir/load_candidates` was AST-extracted from the exact pin, with its normal pandas dependencies and explicit isolated input root. Its owner reader, not a consumer-created parquet globber, performed the two-month projected read. Reader source SHA-256: `24d5d39cfc41331c090e1f6dfb3ff7efd34f3845c86219f8142a4a7b4914c424`. Original rows were neither rewritten nor backfilled. The scratch input copies and outputs belong to this research only.

Requested window: September 21–October 12, 2026. The retained snapshot contains 54,699 rows in that window: 32,235 curated and 22,464 scan-tier rows. All are `us_prophet_v3`; duplicate `(stamp_date,ticker,board_definition)` keys: zero. The selected audit contains 242 rows across 22 named cases, including 11 observations for each of the five Chairman-named securities. The comparison names were selected for this forensic audit after the incident; they are not a pre-event statistical test universe or independent validation sample.

The original store charter is feature/admission telemetry, with keep-first identity and no retroactive backfill. The store is stamped before the later origination run. It does not by itself prove source ingestion time, first publication time, an exact candidate-to-Plan relationship, an executable entry, a fill, or delivery to a person. A complete original-publication history scan remains unperformed: a bounded metadata-history request was refused before dispatch and was not retried, reshaped or proxied. Existing restrictions on live board/risk/options captures were not bypassed.

Research outputs are retained at `/Volumes/Mastermind/evidence/rotation-intelligence-20261012/original-candidate-audit/`: `archive-input-manifest.json`, `audit_candidates.py`, `candidate_rows.json`, `candidate_rows.csv`, `audit-summary.json`, and `coverage-and-semantics.json`. They are evidence artifacts, not another system of record.

## 2. Coverage: the archive does not contain a complete day-by-day curated sequence

| Session label | Curated rows | Scan rows |
|---|---:|---:|
| 2026-09-21 | 2,930 | 1,550 |
| 2026-09-22 | 2,930 | 1,551 |
| 2026-09-23 | 2,930 | 0 |
| 2026-09-24 | 2,928 | 1,565 |
| 2026-09-25 | 2,928 | 1,574 |
| 2026-09-28 | 0 | 1,581 |
| 2026-09-29 | 0 | 1,592 |
| 2026-09-30 | 2,930 | 1,597 |
| 2026-10-01 | 2,932 | 1,604 |
| 2026-10-02 | 2,932 | 1,611 |
| 2026-10-05 | 2,933 | 1,636 |
| 2026-10-06 | 2,931 | 1,641 |
| 2026-10-07 | 0 | 1,646 |
| 2026-10-08 | 2,931 | 1,655 |
| 2026-10-09 | 0 | 1,661 |

September 28/29 and October 7/9 are **missing curated observations in this retained snapshot**, not zero candidates or proof of no signals. Scan-only progress must not refresh a curated-board health indicator. No October 12 stamp is present in these inputs; without the applicable publication deadline and original normal-run receipt, this audit does not independently classify that day's missing stamp as a service failure.

First-observed dates below mean first qualifying row **within the inspected window and present records**. They are not proven first-ever signal dates. Missing days must remain holes in the user timeline. Five prior stamps are not necessarily five consecutive market sessions; the existing candidate-history source itself documents `SCORE_DELTA_BASIS = 5_prior_stamps`.

## 3. Security-by-security findings

### WMT — raw filter rejection, not rank or Featured displacement

All 11 retained rows say `eligible=false`, `buyable=false`, `lane=not_on_board`. The gate reason is consistently `buy blocked by filter: counter-trend, held but no 200-reclaim`.

WMT had stored memberships `defensives|retail`; its selected primary theme was `retail`, with `theme_label=deteriorating` and `theme_reco=avoid` throughout the inspected target rows. This proves context existed in the archive; it does not show that the ranker used it, or that every fast upstream observation agreed with that slower label.

The current filter is **not an unconditional no-waiver 200-day rule**. `signal_gate.gate` defaults `washout_waiver=True`; the existing ratified exception can relieve only the reclaim leg when a qualified, date-admissible basket-washout receipt exists. The hold leg remains required. `signal_quality.reclaim_waiver_for` disallows a future or over-age qualifying state. WMT's retained gate reason shows that no waiver changed these recorded verdicts, but these columns do not establish whether the missing prerequisite was qualification, coverage, age, identity, or a genuinely absent eligible event.

**Implication:** trace the existing exception and early-opportunity route before inventing a new waiver. A moderate defensive recovery need not resemble a deep basket washout. Study a strategy-specific recovery entry rather than globally deleting the long-trend safeguard.

### COST — recognized on September 30; not Featured; later late/expired

| Stamp | Raw eligible / buyable | Stage | Pool | Stored reasons | Admission class |
|---|---|---|---|---|---|
| Sep 30 | true / true | setting_up | more_actionable | alpha_below_floor | patience |
| Oct 1 | true / true | setting_up | more_actionable | alpha_below_floor | patience |
| Oct 2 | true / true | setting_up | more_actionable | alpha_below_floor | patience |
| Oct 5 | true / true | ran | more_actionable | stage_ran; alpha_below_floor; already_open | patience |
| Oct 6 | true / true | ran | late_or_unfillable | pending_expired | patience |
| Oct 8 | false / false | null | null | raw counter-trend / no-200-reclaim rejection | null |

The September 30–October 6 raw reason says `buy fired; forward confirmation pending`. Featured is false on all five dates. Earlier retained target dates were `flat: sell`.

The October 5 `already_open` reason is a **stored observation that an open Plan for the ticker was known to the pool producer**. It is counterevidence to an unqualified claim that COST never had any model Plan, but it is not an exact episode-linked new Plan, a holding/fill, or a notification receipt. The adapter reads the previous published Plan index and stores ticker-level `pool_open_plan`; exact episode identity must be resolved separately.

**Implication:** the miss is not total detection absence. The unresolved issues are whether a timely actual entry existed, what the user saw outside Featured, and whether stage/entry semantics and publication latency obscured the opportunity before it became late. Do not change a patience state into a buy merely because an archive field is named `buyable`.

### ABBV — qualified on October 8, not Featured

The first ten retained observations say `flat: sell`, not on the board. October 8 records T2 eligibility, `lane=buy`, `stage=live`, `pool_lane=more_actionable`, `pool_admission_class=confirmation`, and `featured=false`. Its sole stored pool reason is `alpha_below_floor`; stored alpha is -0.06, without treating that number as a percentage return. Its primary theme remains `big_pharma / deteriorating / avoid` in the inspected records.

**Implication:** candidate detection happened by the retained October 8 row. Featured selection and thematic interpretation are separate from entry authority and need an explicit product explanation. Whether it should have qualified earlier requires the actual point-in-time expert/price evidence; this archive alone cannot validate that counterfactual.

### KO — strength exists in the stored feature, but the old entry is no longer fresh

All 11 rows are raw rejections: `held but topped/rolled-over — no longer a fresh entry`. October stored alpha is positive (approximately 1.91–2.06), but no current board stage or pool lane is stamped. The archived primary context is `defensives / deteriorating / avoid`.

The current raw gate deliberately removes an old held master entry when its cascade no longer qualifies as fresh T1; this is a new-entry filter, not an instruction that the investor must sell an actual holding. Its source also distinguishes bucket-label age from knowable event age; changing the eligibility clock requires qualification and must not silently relabel old events as new.

**Implication:** an old rejected entry and a new continuation/re-entry opportunity are different. Retain the prior event and evaluate a genuine new strategy trigger. Do not resurrect it by resetting the date, and do not confuse positive alpha with entry permission.

### WM — no qualified raw entry; retained theme fields absent

All 11 observations are `flat: sell`, not on the board. No theme membership/primary-theme fields are populated in the selected archive columns. This is a retained association gap, not proof that WM is absent from every current ontology or that an absence alone caused the raw technical rejection.

**Implication:** separate technical-trigger coverage from economic classification coverage. Verify the existing multi-membership mapping and its historical availability, rather than adding an ad hoc WM-only defensive label to fix one retrospective case.

### MCK — positive control against an all-defensives-failed story

MCK is raw eligible October 5/6/8. October 5 is more_actionable with a provisional shortfall; October 6 and October 8 are Featured, with `already_open` recorded. The current screenshot showing MCK is consistent with this retained history, but the archive still does not establish the exact original render/delivery time.

## 4. Donor and resilient-theme controls

The 17 comparison names are MCK, PG, ETR, NVDA, AVGO, MU, AMD, ANET, SMCI, DELL, VRT, MSFT, PLTR, CRWD, PANW, ZS and NET. This is a diagnostic set, not a representative backtest or a claimed pure cohort.

Examples from the retained rows:

- NVDA was Featured September 30 and October 1, then no longer raw eligible from the October 2 retained row onward. This is a **new-entry state change**, not proof that an exit warning was emitted to holders.
- MU was eligible September 21–24, displaced by the sector display cap, and later rejected as an old topped/rolled-over entry.
- ANET was eligible September 21–25, displaced by the sector cap; later observations reject a topped or old entry.
- AVGO qualified October 5/6/8 but never became Featured; this prevents treating every hardware security as already equally rejected.
- CRWD had no new raw eligibility in these 11 observations, with the same old/topped-entry reason. PANW and most NET observations had a different raw rejection. Relative strength of a cybersecurity theme is not proof of a fresh individual entry.

**Required extension:** source-native cohort risk must reach existing-idea/holdings review independently of the new-buy filter. Deleting a name from the Buy shelf does not communicate why an existing position needs review. Conversely, raw new-entry rejection must not be rendered as an automatic sell of a holding.

## 5. A semantic collision affects more than the five named cases

Across the 32,235 curated observations, **284 rows across 184 distinct tickers** combine `pool_lane=more_actionable` with `pool_admission_class=patience`. This is not a count of failed trades or improper recommendations; it is a count of stored combinations requiring careful product interpretation.

Current `us_candidate_lanes._classify_buy_row` reads existing bridge refusal codes first. A non-Featured row without those refusals is placed in more_actionable, with Featured shortfalls attached. `pending_expired` is a separate override. Current `us_board_rank.featured_shortfalls` explicitly says its result affects the Featured flag, not population. The pipeline therefore has several legitimate but differently scoped meanings of buy/actionable/ready.

The archive does **not** include an exact B4 availability decision and does **not** include a complete episode-linked origination/delivery record. It must not be used to infer ENTRY_OPEN from `buyable`, Featured, or a pool name. The product's actual entry display should bind the existing B4 authority; discovery and visibility can remain broader.

## 6. Recovered existing work: complete it instead of starting duplicates

A scoped collision/reuse census found these existing carriers. All listed heads were open/draft at this census; historical author or update age is not proof of current source custody.

| Carrier / inspected head | Relevant existing scope | Consequence for this program |
|---|---|---|
| #7174 `effdbd13cb78f2da3770733e85f64c93d395eb0d` | Existing Prophet admin diagnostics: source absence, mismatched cutoffs, historical ticker matching, basket representation | Do not create a second admin diagnostic endpoint |
| #7168 `641904a3a350c1cdb5ab10c765dc59e01b7f6346` | Corrected conversion semantics, clock/episode integration and multi-speed research protocols | Reuse its finding that ticker-ever Plan matching is not on-time episode conversion |
| #7604 `abcf15fad369534eae73207e338913f2da96e8b4` | Existing miss-audit extension for emerging subthemes: admission/scoring/Featured gaps | Extend/reconcile the incumbent funnel rather than a parallel miss-audit |
| #7210 `0a08c4a2e32074f7a8f2ba2618ee4f4a0d7ed91e` | Research-only causal 21-session structural / 5-session tactical state frame | Reuse the causal state producer and preregistration; do not rebuild it or assume it is promoted |
| #8412 `7afe6716a7cecb1fb506e047918223b9d7f7bc1a` | Scratch replay alert-write isolation in subsector alert owner/build script/China test | Preserve it; a scratch analysis must not accidentally write shared alerts |

Current-main B03 `engine/prophet_early_observations.py` already supplies an uncapped logical observation population with server search and bounded paging, read from the existing private Turn Watch sidecar. It explicitly has no buy, alert, rank, entry-open or episode-write authority. Its source exists; its historical sidecar capture/publication clocks and this audit's original named-security B03 presence remain unproven. Do not conflate an observation with an accepted candidate or commission a replacement search shelf.

## 7. Architecture amendments and discriminating next tests

1. **Separate gate failure, Featured omission and entry unavailability.** Add source-owned reason links to the existing diagnostic and product projection. A counterexample must prove alpha-below-floor does not delete an otherwise existing candidate; another must prove patience never becomes an executable buy.
2. **Turn discovery must operate before slow structural promotion.** Reuse the existing early observation and candidate-intake paths. Bind a newly qualified tactical event to the incumbent strategy/episode/B4 owners; never directly promote B03 to trading authority.
3. **Model different recovery shapes.** Existing washed-out-basket waiver, moderate counter-trend recovery, within-trend pullback and continuation are different hypotheses. Reuse existing strategy definitions and test one new axis at a time; no blanket 200-day override.
4. **Retain both economic memberships and their horizons.** WMT/COST's defensives and retail memberships must remain visible without double-counting. A selected primary retail label should not erase the defensive exposure; WM's missing retained mapping needs separate coverage diagnostics.
5. **Audit the actual clocks.** Preserve bucket-open, event-known, source-session, recorded, published and delivered times. The `fresh_bars_knowable` field already exists for display; an eligibility-clock repair must own its causal/false-positive consequences.
6. **Make the decision timeline coverage-aware.** September 28/29 and October 7/9 stay explicit holes for curated records. Neither scanner progress nor latest build time means the curated decision population is current.
7. **Give donor exits a separate consumer path.** Former Featured/eligible names remain in the existing-idea review history. A missing new-buy row is not a holder warning, and a gate's word sell is not a portfolio trade instruction.

The narrow next evidence join is exact source event/candidate episode -> actual strategy/B4 decision -> original Plan if any -> publication/delivery. COST's stored already_open is the strongest priority for resolving the difference between ticker-level association and exact on-time recommendation. The refused history action and inherited live-capture holds remain lane-local constraints, not a reason to repeat them through another tool.

## 8. Predictive research refinement

The newly recovered records make a useful scientific distinction: test the incremental utility of earlier discovery, strategy-specific permission and better placement **separately**. A Featured change may increase visibility without improving an entry strategy; a stricter anti-chase rule may be correct even though a later chart rises.

Use the incumbent RPH-2 multi-speed state frame as an input candidate. Compare existing policy with a predeclared tactical-recovery challenger, a continuation challenger and a placement-only change, with historical membership/availability and unchanged negative controls. Do not tune all three simultaneously to the October cases. Score timely opportunity availability, missed/false entries, adverse excursion and later calibration at declared horizons; no performance estimate is produced here.

Primary literature verified in this continuation:
- Moskowitz and Grinblatt (1999), *Do Industries Explain Momentum?*, Journal of Finance 54(4), 1249–1290; https://doi.org/10.1111/0022-1082.00146. Motivates industry conditioning, not a one-week pivot guarantee.
- Daniel and Moskowitz, *Momentum Crashes*, NBER Working Paper 20439 / Journal of Financial Economics (2016); https://www.nber.org/papers/w20439. Past losers can rebound in stressed states; this is a competing hypothesis against extrapolating donor weakness.
- Adams and MacKay (2007), *Bayesian Online Changepoint Detection*; https://arxiv.org/abs/0710.3742. Candidate online change method, not evidence of Mastermind trading alpha.

## 9. Source references and reproducibility

All source references below are from Macro `317f2c06090d15347fe8117290a0e13ad2e2ad5b` unless the PR-specific head is stated above.

- `data/us_prophet_rank/README.md`: original store scope, tiers, keep-first identity, no-backfill, zero authority and owner-reader contract.
- `engine/us_context_vector.py:204–265`: selected owner reader; lines 970–1025: exact archived field provenance.
- `engine/us_candidate_lanes.py:251–258,334–442,714–750`: prior-stamp clock, bridge/Featured semantics, ticker-level open-Plan association.
- `engine/us_board_rank.py:644–654,966–1071`: residual-alpha field and Featured-only shortfalls.
- `engine/signal_gate.py:113–120,379–515`: raw buyable semantics, existing washout waiver, fresh versus knowable age and old-entry rejection.
- `engine/signal_quality.py:443–513`: qualifying source state, bar-level date admission and no retrospective waiver.
- `engine/prophet_early_observations.py:1–31`: B03 observation population and all-false authority.
- `agentos/handoffs/PROPHET-US-V4-RECOVERY-2026-10-11-b03-delivery.md`: existing delivery evidence and separate unresolved source/production clocks.

## 10. Outcome and continuation

This phase resolves a substantial part of the **original candidate funnel**, not the full incident. It replaces five undifferentiated alleged misses with source-supported categories and exposes curated coverage holes and action-language ambiguity. It also corrects the initial shorthand that alpha blocked candidate admission. No return, alpha, bottom-detection or live-delivery performance is claimed.

Preserve exact original source inputs and these conclusions as DO_NOT_REDO unless materially invalidated. The next engineering work may fix independently proven receipt truth without altering trade thresholds; the next forensic work requires the exact episode/Plan/publication relationship, not another ticker-only join. Parent mission remains incomplete, and no daemon/worker or automatic wake is asserted.
