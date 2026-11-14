---
key: PROPHET-NEWS-IMPACT
title: Prophet news-to-business-impact — measured event packets, baselines and a graded benchmark
objective: >
  Turn company news into a measured, span-cited, typed business-impact packet that
  Prophet can consume as context_only evidence. Done means: three frozen event
  templates with acceptance labels and closed schemas live under
  contracts/news_impact/; a validator in engine/news_impact/ rejects unknown fields
  and unsolicited instructions; a 600-case graded benchmark (200/200/200) reports
  critical-numeric correctness, material-event routing recall and zero unsupported
  ticker-to-supplier assertions against the masterplan §11 thresholds; and the
  Prophet evidence owner reads the packets without any change to master procedures,
  live portfolios, B4 gates, source licenses or provider authentication.
status: active
program: prophet-us
repos: [macro]
owner: fable-ceo
class: research
blast_radius: reversible
ambiguity: scoped
depends_on:
  - WS:PROPHET-US-V4-RECOVERY
owns_paths:
  - research/prophet_v4/news_to_business_impact_20261006/
  - research/PROPHET_NEWS_IMPACT_CONTINUATION_HANDOFF_2026-10-11.md
  - engine/news_impact/
  - contracts/news_impact/
  - tests/test_news_impact_*.py
  - agentos/handoffs/PROPHET-NEWS-IMPACT-*.md
landmines:
  - "Sol's DRAFT PR #8533 carries the masterplan packet on research/prophet-news-impact-masterplan-20261006; it is superseded by this workstream's branch (cherry-pick -x of cde0219b1040) and closes with one comment once the Phase 0 PR merges — never merge or rebase #8533 itself."
  - "Adjacent Sol lanes never touched by this workstream: #8697 (tiingo news quality, DRAFT/HOLD), #8698, #6514 (K3-D, HOLD-FOR-SOL). Masterplan §12 commission C never repairs or merges #6514."
  - "Masterplan §13: no changes to master procedures, live portfolios, B4 gates, source licenses, provider authentication or existing active workers. New code lives only in the LEAF namespace engine/news_impact/ + contracts/news_impact/ and consumes existing owners (engine/news_events.py, engine/news_event_ledger.py, engine/company_intelligence/*)."
  - "DNR:KILL-LLM-CONFIDENCE and DNR:KILL-CAUSAL-DAG-ALPHA bind: no model confidence field, no price target, no 0-100 rerating score, no multi-hop theme prediction in any packet schema."
do_not_redo:
  - "The section 11 report design is settled by DEC:NEWS-IMPACT-SECTION11-REPORT: the qwen family is the system under test and never gold; gold is the accepted MiniMax fam_a drafts plus a GLM draft of every critical slot of every MATCH case, a third family disjoint from MiniMax, GLM and qwen on disagreement, and the seat adjudicating three values; the registration (seeds 20261021 and 20261022) is committed before any GLM output exists. Do not re-open it without a material invalidator."
  - "Phase 0 recovery census (2026-10-11): nothing of this program is in origin/main; no sibling session owns it; engine/news_impact/ and contracts/news_impact/ are free. Do not re-census."
  - "Orchestration shape: Fable seat → one native Opus orchestrator → read-only fabric lanes on local m2 pools (glm-5.3-flash census, glm-5.3 candidates + attack reviews) → orchestrator synthesis → seat adjudication. The Workflow tool is platform-blocked in the seat session (hook dispatch timeout, verified twice); do not try it a third time."
  - "Orchestration shape from 2026-10-12 (Chairman directive): no native Claude children of any kind; the seat launches Grok (grok-4.6) and GLM (glm-5.3 / glm-5.3-flash) lanes directly with ext/remote_sub.sh on ubuntu0/ubuntu2/ubuntu3/mb, one launcher task per lane as its only watcher, and judges every return by artifact. The Phase 0 native-Opus orchestrators ORCH-W1/W1c/W1d are history, never a template."
  - "Wave-2 lanes B1-B5, A1-A7 and C1-C3 are ACCEPTED by artifact and integrated in the Phase 1 integration PR (2026-10-13); the hostile corpus reproduces 33/33 seat-ratified verdicts. Do not re-run them; repair forward."
  - "The nine W3 build lanes (X4 transfer, X4 observation, C5 cascade, M2 mechanisms, E3 receipt, E3 grade, T1 thesis, P7 adapter, L6 agreement) are ACCEPTED by artifact and integrated in W3 commit 0980ee37 (617 passed, 0 skipped). Do not re-launch them; the seven open design defects are repaired forward in wave w1c."
  - "The seven W3 design defects are settled by DEC:NEWS-IMPACT-W1C-DESIGN-RULINGS (2026-10-13). Do not re-adjudicate them, and do not edit the frozen A-design packets; amendments live in phase1_designs/AMENDMENTS_W1C.md and the superseded case values in AMENDMENTS_W1C.cases.json."
  - "The X4 session-counted matched window (lane W1C_X4_r3 on GLM glm-5.3) is ACCEPTED by artifact. Do not relaunch it."
  - "Benchmark bodies are settled by DEC:NEWS-IMPACT-BENCHMARK-BODY-SOURCE: issuer 8-Ks through the existing SEC owners, internal_only. Do not reopen vendor article bodies or write a second EDGAR client."
  - "The w2 two-family labeling of 157 cases and the 40-slot audit (seed 20261014) are ACCEPTED under DEC:NEWS-IMPACT-W2-BENCHMARK-SCORING. Add a third family on top; never relabel or redraw them. The absent-slot addendum audit (seed 20261015, 26 slots) is ACCEPTED under DEC:NEWS-IMPACT-ABSENCE-REASON-SCHEDULED-EXECUTION; extend it with new strata, never redraw it."
  - "The malformed-slot audit (all 11 malformed_value slots, no sampling) is ACCEPTED under DEC:NEWS-IMPACT-GUIDE-V12-T1-AMOUNT-RULES; the v1 labels are not relabeled under guide-v1.2 and summary.json is not re-scored."
  - "The routing check (seed 20261016, 40 sampled cases plus the three cases behind malformed cards M3, M7 and M9) is ACCEPTED under DEC:NEWS-IMPACT-CONTINUATION-ROUTING-GATES; extend it with new samples, never redraw it. The w2 labels and summary.json are not re-scored; their reading is narrowed to extraction from the attached filing."
  - "The routing gates validation (seed 20261017, 40 gated-in plus 20 gated-out cases, ni-routing-gates-1 frozen at a8f98d21) is ACCEPTED as a MISS under DEC:NEWS-IMPACT-ROUTING-GATES-1-MISS-PATH; never redraw it, and never re-score its 60 cards against a revised gate set. Gates-2 validates on a fresh seed that excludes all 103 carded cases."
  - "The routing gates 2 validation (seed 20261018, 40 gated-in plus 20 gated-out cases, ni-routing-gates-2 frozen at 5baa4b10) is ACCEPTED as a double MISS, and the paired comparison (seed 20261019, all 11 cases where the two gate sets disagree) is ACCEPTED with gates-2 as the draw filter, under DEC:NEWS-IMPACT-ROUTING-GATES-2-MISS-PATH. Never redraw or re-score either, and validate no further headline-gate revision on this 132-case pool; the next validation comes from a widened frame."
  - "ni-edgar-body-2 (band a-1..a+4, open-window guard, filing tags) is frozen at f0ba5795 under DEC:NEWS-IMPACT-EDGAR-BODY-2-BAND, and its --as-of 2026-10-14 fetch, gates-2 map and 99-case gated_v2 draw (seed 20261014) are ACCEPTED (DSC:NEWS-IMPACT-EDGAR-BODY-2-FRAME). A band change is a new version; the 113 open windows settle in a separately recorded re-run after 2026-10-19, never by redrawing gated_v2. The 73 drawn cases already graded keep their grade."
  - "The v2 routing census (seed 20261020, the 30 gated_v2 cases no card had shown, tool build_v2_routing.py) is ACCEPTED (DSC:NEWS-IMPACT-V2-ROUTING-CENSUS): 74 of the 99 drawn cases are MATCH and score, 12 of those are new to labeling. Never redraw or re-score it; a second auditor extends it."
  - "The fill-only issuer fallback (tape_draw --fallback-ledger, ledger b046d851… from SEC snapshot 844dfd1b…) is ACCEPTED under DEC:NEWS-IMPACT-ISSUER-FALLBACK-LEDGER (DSC:NEWS-IMPACT-ISSUER-FALLBACK-COUNTS); never switch to a replacement ledger, and never redraw gated_v2 with it. gated_v3 is the next draw, frozen before any v3 output is read."
  - "The two-family labels on the 12-case gated_v2 label queue (prompt-v1.2) are done and scored (DSC:NEWS-IMPACT-V2-QUEUE-SCORING); a third family extends them, nobody relabels them."
  - "The W3 producer stage one (engine/news_impact/producer.py, ni-producer-1) is settled by DEC:NEWS-IMPACT-W3-PRODUCER: fail closed, never remap a label onto the contract, issuer tie on the routed value, shadow output is a diagnostic and never measured packets. Its shadow runs on the 157 graded and 12 queue cases are recorded in DSC:NEWS-IMPACT-LABEL-CONTRACT-COHERENCE; re-run them only when the labels or the producer change."
  - "The W3 producer stage two (engine/news_impact/producer_facts.py, ni-producer-facts-1) is settled by DEC:NEWS-IMPACT-W3-PRODUCER-STAGE2: rule novelty, one record per append, per-event adapter accounting with owner crashes counted, outputs only under --out. Its shadow runs are recorded in the stage-two handoff; never add a bound to range events to suit the adapter (DSC:NEWS-IMPACT-ADAPTER-RANGE-BOUND)."
  - "The adapter's range projection is settled by DEC:NEWS-IMPACT-ADAPTER-RANGE-BOUND (ni-prophet-adapter-2): bound exact unless the input carries one, and a coded MISSING_REQUIRED_FIELD for a missing quantity key; never make bound optional in prophet_evidence.v1 to suit one producer."
waves:
  - id: p0
    title: Phase 0 — recovery census, three-candidate commission A, seat freeze of event templates + closed schemas
    status: done
    next_action: none; frozen by DEC:NEWS-IMPACT-PHASE0-FREEZE on PR #8873.
  - id: w1
    title: Wave 1 — benchmark candidate sampler (L3) + schema validator with hostile fixtures (L4)
    status: done
    depends_on: [p0]
    next_action: none; landed by the Phase 1 integration PR (validate.py with the S1-S13 semantic layer and strict loading, sampler, cluster, issuer, 33 hostile fixtures, A1-A7 designs, C2/C3 census).
  - id: w1b
    title: Wave 1b - Phase 1 leaf modules built from the accepted A-designs (thesis fold, mechanism mapper, transfer/observation, eval harness, labeler agreement, cost cascade planner, Prophet evidence adapter leaf)
    status: done
    depends_on: [w1]
    next_action: none; the nine leaf modules (transfer, observation, cascade, mechanisms, eval_receipt, eval_grade, thesis, prophet_adapter, agreement) and the 15 Phase 1 contracts landed by the Phase 1 integration PR (W3 commit 0980ee37) with fail-closed tests; prophet_adapter stays a leaf, not wired into engine/intelligence.py.
  - id: w1c
    title: Wave 1c - repair the seven design defects found at W3 integration (C5 cascade, X4 observation, M2 mechanisms, E3 receipt, T1 thesis, P7 adapter, L6 agreement)
    status: done
    depends_on: [w1b]
    next_action: none; C5, L6 and the four design amendments landed by PR #9262 (squash 33366ca7), and the X4 session-counted matched window by the X4 follow-up PR (GLM lane W1C_X4_r3, 72 observation tests).
  - id: w2
    title: Wave 2 — commission D 600-case graded benchmark (200 capital allocation / 200 demand-guidance / 200 strategic-partnership)
    status: in_progress
    depends_on: [w1]
    next_action: The draw (PR #9290, 157 of 600 cases), the two-family results, the absent-slot and malformed-slot audits, guide-v1.2, the routing check and both gate validations are done, and gates-2 (5baa4b10) is the draw filter under DEC:NEWS-IMPACT-ROUTING-GATES-2-MISS-PATH. The filing-first widening is done: ni-edgar-body-2 (band a-1..a+4, frozen at f0ba5795, DEC:NEWS-IMPACT-EDGAR-BODY-2-BAND) finds a body for 364 of 2,837 candidates, gates-2 lets 135 in, and the continuation draw gated_v2 holds 99 cases (T1 49, T2 46, T3 4; shortfall 501, printed), of which 73 are already graded and 26 are new (DSC:NEWS-IMPACT-EDGAR-BODY-2-FRAME). The routing census of the 30 drawn cases no card had shown is done: the 99 hold 74 MATCH cases (T1 34, T2 36, T3 4), 62 already graded, so 12 are new to labeling and the scorable shortfall is 526, printed (DSC:NEWS-IMPACT-V2-ROUTING-CENSUS). The 12 queue cases carry two-family labels (prompt-v1.2, span replay clean) and agree on 12 of 24 critical slots; all 12 wait on a third family, and T1 executed_amount splits on all 6 T1 cases (DSC:NEWS-IMPACT-V2-QUEUE-SCORING). A fill-only SEC ticker fallback resolves 256 of the 1,271 no-CIK candidates (T3 82) without changing gated_v2, and gated_v3 is frozen as the next draw (DEC:NEWS-IMPACT-ISSUER-FALLBACK-LEDGER). Next: gated_v3 on or after 2026-10-20 (one ni-edgar-body-2 fetch that reaches the newly resolved issuers and settles the 113 open windows), then a census routing verdict on each case new to the draw; GLM gold (after 2026-10-19 05:16Z, prompt-v1.2) on every critical slot of the 74 MATCH cases, 142 slots including the 12 queue cases and their T1 executed_amount split, then the registered third family on each MiniMax/GLM disagreement (DEC:NEWS-IMPACT-SECTION11-REPORT); a second auditor on the 60 gates-2 cards, the 11 disagreement cases and the 30 census cards; a MiniMax usage capture; a name rung for the 914 candidates that name no ticker; then the 600-case continuation.
  - id: w3
    title: Wave 3 — Phase 1 measured packet producer wired to the existing event ledger, context_only, behind the benchmark gate
    status: in_progress
    depends_on: [w2]
    next_action: Stage one (engine/news_impact/producer.py, ni-producer-1, DEC:NEWS-IMPACT-W3-PRODUCER) gates label returns into validated news_impact_event.v1 candidates with full emit/defer/reject accounting; on the 157 graded and 12 queue cases every case defers pending_third_family in adjudicated mode, and the shadow single-family runs are recorded in DSC:NEWS-IMPACT-LABEL-CONTRACT-COHERENCE. Stage two (engine/news_impact/producer_facts.py, ni-producer-facts-1, DEC:NEWS-IMPACT-W3-PRODUCER-STAGE2) turns events into fact log records with rule novelty, thesis views and Prophet evidence under an explicit output path only; on the shadow events it completes with no rejects, and since ni-prophet-adapter-2 every contract-valid range quantity projects with bound exact and the adapter crash count is zero (DEC:NEWS-IMPACT-ADAPTER-RANGE-BOUND); The section 11 report design is settled (DEC:NEWS-IMPACT-SECTION11-REPORT) and its registration is committed (benchmark/section11/registration.json, ni-section11-registration-1); qwen on prompt-v1.2 is the system under test, MiniMax-M3 and GLM are gold, the 74 MATCH cases and their 142 critical slots are listed, and the frontier-only audit subset (13 cases, seed 20261021) is drawn. The report assembler is written (engine/news_impact/section11_report.py, ni-section11-report-1), pure over eval_grade and eval_receipt, gated by require_registered_implementation, values in scratch only. Since #9732 (ni-producer-facts-2 plus the implementation guard) the v1 registration refuses every consumer on main (DSC:NEWS-IMPACT-V1-REGISTRATION-INELIGIBLE-ON-MAIN). Next, ni-section11-registration-2 with its DEC (same seeds, populations, slots and draw; current code versions), then the system-under-test run on the 74 cases, GLM gold, the third family and seat adjudication, adjudicated producer output, and one assembler run.
next_action: Wave w2 - gated_v3 on or after 2026-10-20 under the frozen fill-only issuer fallback (DEC:NEWS-IMPACT-ISSUER-FALLBACK-LEDGER; one ni-edgar-body-2 fetch that also settles the 113 open windows) and a census verdict on its new cases; GLM gold after GLM resets (2026-10-19 05:16Z) on all 142 critical slots of the 74 MATCH cases, then the registered third family on disagreements; a second auditor on the gates-2 and census cards; a MiniMax usage capture; a name rung for the 914 no-ticker candidates; 74 MATCH cases score, shortfall 526; shortfalls stay printed, never padded; keep the v1 contract byte-frozen. Wave w3 - producer stage one is built (DEC:NEWS-IMPACT-W3-PRODUCER); stage two is built (DEC:NEWS-IMPACT-W3-PRODUCER-STAGE2) and the adapter projects range quantities (DEC:NEWS-IMPACT-ADAPTER-RANGE-BOUND); the section 11 registration is committed (DEC:NEWS-IMPACT-SECTION11-REPORT), and the report assembler is written (ni-section11-report-1); the v1 registration is ineligible on main since #9732 (DSC:NEWS-IMPACT-V1-REGISTRATION-INELIGIBLE-ON-MAIN), so next come ni-section11-registration-2 with its DEC, then the system-under-test run on the 74 MATCH cases; adjudicated producer output waits on GLM gold and the third family, and the next prompt version carries the enum lists and cross-field rules (DSC:NEWS-IMPACT-LABEL-CONTRACT-COHERENCE).
---

# Prophet news-to-business-impact

Masterplan: `research/prophet_v4/news_to_business_impact_20261006/package/MASTERPLAN.md`
(cherry-picked from Sol's DRAFT PR #8533, commit `cde0219b1040`). Chairman assignment
2026-10-10/11: the Fable Meta-CEO seat owns delivery end to end, autonomously, with
labor on the Mastermind Executive/Subagent Fabric and judgment in the seat.

Program state at resumption grain lives in
`research/PROPHET_NEWS_IMPACT_CONTINUATION_HANDOFF_2026-10-11.md` (DECIDED / FACTS /
OPEN / NEXT + lane matrix). Phase 0's freeze is
`research/prophet_v4/news_to_business_impact_20261006/PHASE0_FREEZE_2026-10-11.md`.
