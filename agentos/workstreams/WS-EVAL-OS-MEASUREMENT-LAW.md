---
key: EVAL-OS-MEASUREMENT-LAW
title: Intelligence Evaluation OS — the measurement law wave (horizon clock, market ruler, promotion legality)
objective: >
  Make the qledger Universal Scoreboard measure what it says it measures: every claim
  declares its horizon UNIT, one resolver answers check_by/maturity/grading/render, the
  market ruler is the exchange the claim is priced on, promotion arithmetic is
  direction-correct and legality-gated, and forward-only registration starts a real
  evidence clock. Done when three desks are accruing prospective claims at their own
  declared rulers and no published promotion number is computed on a basis it was not
  measured on.
status: active
program: qualitative-intelligence
repos:
  - macro
owner: Intelligence Evaluation OS programme lead (current Chairman-assigned principal)
class: build
blast_radius: reversible
ambiguity: scoped
decisions:
  - "DEC:EVAL-OS-RECOVERY-ARCHITECTURE-FREEZE"
  - "DEC:EVAL-OS-DARK-WORKER-RECOVERY-2026-08-29"
  - "DEC:EVAL-OS-WAVE-AUTHORITY-AND-LEADERSHIP-CONTINUITY-20261024"
waves:
  - id: W1
    title: Architecture + metric validity
    status: done
    next_action: "None — PR #5471 merged. The separate fleet-wide strict-hardening residue remains a later completion wave because the current CLI is still WARN-tier by default."
  - id: W2
    title: Horizon-clock contract + market ruler
    status: done
    next_action: "None — PRs #5559 then #5563 merged. #5563 fixed #5559's shape_is_decisive defect."
  - id: W3
    title: Promotion legality substrate
    status: done
    next_action: "None — #5519, #5573, #5572 and later clock-legality repairs landed. Unified final-path adversarial acceptance remains a separate continuation wave, not a reopening of these merges."
  - id: W4
    title: Append-only law + forward-only accrual
    status: in_progress
    depends_on: [W2, W5]
    next_action: >
      The current programme lead inspects the existing producer/grader and runner-local
      control/cohort receipts, preserving demand_chain 2026-08-19, stock_desk 2026-08-29
      and thematic_desk 2026-08-31 general clocks. Identify the next genuine normal
      publication and verify its selected-store consumption. Protect the QLedger integration
      writer evidenced in the 2026-10-24T18:09Z recovery return and any unknown cutover
      effect; an absent historical owner alone is not a wait condition. Do not force a run,
      remint clocks or use the pre-release scheduled receipt as post-release proof.
  - id: W5
    title: Control-leg decision
    status: done
    next_action: >
      None — P0d/#5609 resolved the CEO policy: benchmark is universal baseline; matched control
      is required only where governed policy names a defensible counterfactual. stock_desk and
      demand_chain are matched-control-required; thematic_desk is benchmark-only. #5665/#5672
      repaired demand-chain wiring/replay semantics.
  - id: W6
    title: Final composed promotion and clock-integrity acceptance
    status: todo
    depends_on: [W2, W3, W5]
    next_action: >
      Reuse the landed direction, ruler, correction and readiness tests, then bind their
      adversarial conclusions to the actual released selected-store/consumer path.
      Verify lawful horizon, market, direction, denominator, cohort and control basis;
      missing or ineligible evidence must remain explicit and readiness must grant no
      promotion or financial authority. Obtain fresh non-authoring acceptance for the
      remaining exact-source scope. W3 remains done; this is its explicitly reserved
      continuation, not a rebuild or a requirement for new market outcomes.
  - id: W7
    title: Staged invalid-emitter qualification and strict-hardening disposition
    status: todo
    depends_on: [W1, W6]
    next_action: >
      Qualify current affected emitters through the existing metric-validity CLI and
      staged enforcement path, preserving accepted tests and WARN-tier behavior until
      the actual rollout gates are satisfied. Record emitter coverage, exclusions,
      observability and rollback evidence. Do not infer fleet-wide strict activation
      from a merged substrate, a source-only change or this documentation PR.

next_action: >
  Execute W4's read-only control/cohort and normal-publication evidence inspection under
  current role-based programme leadership; protect actual live writers and unknown effects.
  Prepare W6 on the released #6651/#10130 source using accepted evidence, then W7 under
  its declared prerequisites. The top product continuation is the independently executable
  WS:EVAL-OS-EVIDENCE-VIEW A1; W4 natural-time completion is not an A1 dependency.
  Use the wave records as the execution authority and the dated audit only as evidence.
owns_paths:
  - engine/qledger.py
  - engine/qledger_validity.py
  - scripts/grade_qledger.py
  - research/EVAL_OS_*.md
  - research/PREREG_P0C1_*.md
discoveries:
  - DSC:NO-QLEDGER-CLAIM-EVER-CARRIED-A-CONTROL-LEG
landmines:
  - "engine/source_registry.py keeps its OWN _add_trading_days NYSE walker and grades narrative_source_call through its own exit. 'ONE resolver' is true only for claims that grade through qledger; do not overstate qledger scope."
  - "Current production track_record contains explicit and legacy bases and refuses pooling; future consumers must preserve this rather than reconstructing family statistics from raw mixed rows."
  - "data/qledger/control_evidence_clock_start/ is intentionally runner-local/untracked after #5970. A missing Git file is not proof a live clock is absent; production host/runtime truth must be read without inventing another canonical copy."
  - "All three focal general clocks exist. First-event annotations are immutable and distinct from current declared rulers or available grades."
  - "The canonical nightly thematic path is already wired daily engine -> cl_baskets -> build_baskets -> build_allocation -> _run_thematic_desk -> engine.thematic_desk.run. Do not invent a second producer or misclassify the remaining gap as a generic scheduler absence."
do_not_redo:
  - "Do NOT re-propose 'the horizon fix is a one-line in_scope_horizons change'. The defect was missing unit declaration."
  - "Do NOT register retrospective claims for stock_desk/thematic_desk/demand_chain. The prior T9 adoption attempt was refused by 3/3 adversarial reviewers because rows were anchored/priced after the fact."
  - "Do NOT add a decorative `backfilled` provenance flag. A mixed store with a flag no authority reader enforces is worse than a small honest one."
  - "Do NOT extend GRADE_HORIZONS above 63 (LH-U6). >63 declared rulers remain check-by clocks, not own-horizon grades, until a separate explicit ruling."
  - "Do NOT re-derive a claim's market from ticker shape alone or provenance alone. Hard fact wins; inference must agree; provenance may decide only where shape is silent."
  - "Do NOT track/commit runner-local matched-control clock files merely to make them visible. #5970 intentionally removed that duplicate-state hazard."
  - "Do NOT re-mint or rewrite stock_desk's first general clock; it is durable evidence now."
artifacts:
  - research/EVAL_OS_RECOVERY_ARCHITECTURE_FREEZE_2026-08-27.md
  - research/EVAL_OS_SITREP_2026-08-14.md
  - research/EVAL_OS_P0A_HORIZON_CLOCK.md
  - research/PREREG_P0C1_DIRECTION_CORRECT_CONTROL_HITS.md
  - research/PREREG_P0D_MATCHED_CONTROL_CONTRACT.md
  - agentos/handoffs/EVAL-OS-E1-THEMATIC-COHORT-RECOVERY-2026-08-29.md
  - research/EVAL_OS_CONTINUATION_2026-10-12.md
  - research/EVAL_OS_WAVE_AUDIT_2026-10-24.md
  - agentos/handoffs/EVAL-OS-MEASUREMENT-LAW-2026-10-24-PRO.md
---

## Wave audit and leadership continuity — 2026-10-24

The existing objective and wave identities are the source of execution state. The Chairman's current instruction assigns the programme-lead role to the present principal. Historical roots, PR authors and absent sessions are provenance, not mandatory approval recipients. Actual active writes, pending effects, explicit denials and exact authentication consent remain protected. The original root's T03 advancement is retained; the reported active QLedger alias/entry-point integration is not taken over or duplicated.

| Wave | Audited status | Evidence and acceptance boundary |
|---|---|---|
| W1 | done | #5471 accepted the architecture/validity substrate. WARN-tier defaults do not prove global strict enforcement; W7 carries that reserved residue. |
| W2 | done | #5559 and corrective #5563 accepted the horizon/market substrate. Preserve 5/21/63 grade limits and explicit declared rulers. |
| W3 | done | #5519, #5573, #5572 and later legality repairs are retained. W6 represents the final composed-path acceptance explicitly reserved by this wave. |
| W4 | in_progress | All three general clocks exist. Current owner-local control/cohort qualification and genuine subsequent progression remain partial. Historical scheduled run 38406512307 is not a post-release pass. |
| W5 | done | P0d/#5609, #5665 and #5672 establish benchmark/control policy and wiring; stock/demand require governed controls, thematic is benchmark-only. |
| W6 | todo; added with rationale | Original P1/T17 composed acceptance was already reserved in W3 but absent from waves[]. It depends on accepted W2/W3/W5 and does not reopen them. Pass requires the released authority-consumer path, adversarial proof and independent acceptance. |
| W7 | todo; added with rationale | Original T0/T3/G1 strict-hardening residue was already reserved in W1. It depends on W1/W6. Pass requires affected-emitter qualification and an explicit governed enforcement disposition, not an automatic strict flip. |

W4 depends on W2/W5 because clock/cohort legality uses the accepted market and control contracts; both are already done. W6 and W7 expose previously declared obligations rather than enlarging the programme. No accepted wave is superseded or reopened, and no new programme/workstream is created.

### Programme boundaries retained

The August recovery decision still owns the original T0–T12 obligations. T2 benchmark/MFE/MAE, outcome-dependent T5 taxonomy, original T6 historical PIT/adjudication, broader T9 adoption and T10–T12 consumer/adoption residue remain explicitly assessed in the dated audit. They are not silently counted complete by these bounded wave states. The programme-lead role owns their reconciliation through existing source owners; a later separately specified empirical build belongs in an explicit bounded canonical wave, not a second plan or automatic cross-project commission.

A1 can complete its honest read-only product objective while W4 accrual remains incomplete. There is no A1 dependency on W4, QLedger #10079 activation, every empirical legacy objective, or the October commission's global T22–T24 closure chain. Programme completion remains false.

### Source-linked continuation

Recipient: current Intelligence Evaluation OS programme lead. Action: execute the highest-value safe A1 acceptance slice while W4 and W6 retain their explicit independent work. Source: WS:EVAL-OS-EVIDENCE-VIEW.md, wave A1 and its acceptance table. Return: the A1 workstream evidence section and the dated handoff in this Draft PR. Any independent review binds an exact candidate revision; the author neither approves nor merges their own change.



## Reconciliation — 2026-08-27

The 2026-08-14 W4/W5 next actions were stale. #5534 (append-only), #5577 (forward-only desk
registration) and #5584 (legacy-clock authority firewall) are merged. P0d/#5609 plus
#5665/#5672 resolved the control-policy question. Real production evidence later showed that
`demand_chain` started its general prospective clock at `2026-08-19T08:10:37.995754+00:00` and
its matched-control clock at `2026-08-19T08:10:37.332100+00:00` with control `XLU`, while the
tracked general clock estate still had no `stock_desk` or `thematic_desk` start. Therefore W4
remained genuinely in progress for natural-time accrual, not for old PR merges; W5 was done.

This workstream owns measurement law, not a new promotion authority and not the engines that
produce claims. T1 remains the single derived engine-registry sibling and is already done under
its own bounded completion law.

## Recovery reconciliation — 2026-08-29

The original E1 child `eval-os-e1-clock-accrual-20260827` produced two accepted implementation
repairs before its worker dialogue went dark: #6598 fixed stock/thematic anchor-at-registration
without weakening the forward gate, and #6607 persisted qledger state from the stock-briefs
production lane. Current canonical main now contains a real `stock_desk` clock receipt with
`first_prospective_registration_utc=2026-08-29T11:08:11.609328+00:00`, and current qledger
`run_status.json` is a post-clock real grading run (`generated_at=2026-08-29T14:56:46.111593Z`,
264 grades that run). The stock general-clock sub-capability is therefore `PROVEN_LIVE`.

No current `thematic_desk.json` evidence-clock receipt exists. The authoritative nightly path was
observed executing through the existing basket/allocation/thematic-desk chain, so the remaining
question is downstream of generic scheduling: current US state may lawfully yield no thesis, a
proxy/scorability gate may refuse it, the model/parse/fail-soft path may suppress output, or a real
product/policy defect may exist. The successor must classify that branch before modifying anything.
It may never fabricate a thematic thesis merely to start a clock.

The old E1 child received terminal `SOL CLOSED / STOP` on Slack thread
`C0BSBM78V1N/1787896831.113919` at message `1788024583.456369`; its temporary watcher was ordered
disarmed. The parent Eval OS program remains active. A fresh recovery child is required for the
remaining thematic + cohort proof rather than silently moving the old worker/session.

## Current clock reconciliation — 2026-10-12

`git show a8e054ce5d7d44e48ff552841dc93d3c0ec87149:data/qledger/evidence_clock_start/thematic_desk.json` confirms the original thematic first registration at `2026-08-31T05:01:42.762963+00:00`,20 trading days, source09cc2e0f465c5a27f7382b3656694b5d068ef00d. The stock receipt remains2026-08-29T11:08:11.609328+00:00. Earlier absent-clock text describes its historical observation only. No new receipt or registration is authorized by this correction. Current acceptance still owes real cohort/control qualification and natural-run status.

## Current consumer qualification — 2026-10-13

The internal existing response-eval owner now has accepted finite synthetic seven-class/overlap/trial/look/contamination contracts and136 affected controls. This is deterministic internal QA, not empirical class qualification or protected study access. The evidence consumer preserves recorded cohorts, control and whole-family baseline populations, clock partitions and explicit zero/null; current/all-input qualification remains unavailable even when named local generations match. No registration event, control origin or grade horizon changed. Natural owner progression and original excluded study/producer obligations remain open.
