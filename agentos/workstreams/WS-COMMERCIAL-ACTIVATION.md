---
key: COMMERCIAL-ACTIVATION
title: Commercial Front Door, Activation, and Retention
objective: 'Make the visitor-to-retention journey coherent, measurable, and trustworthy: genuine intelligence
  before registration; a personal act before a minimal free account; canonical state preserved through
  signup; measurable free and paid activation; contextual paid asks after value; authority-sourced billing;
  and a useful personalized return. Done means a real anonymous visitor can experience intelligence, save
  a personally meaningful state through free account creation, return to it, activate, upgrade at a measured
  value boundary, and retain — with every stage machine-readable from the existing analytics plane.

  '
status: active
program: terminal-user-services
p0: MONETIZATION_AND_ONBOARDING
repos:
- macro
- terminal
owner: ceo-sol
class: build
blast_radius: user_facing
ambiguity: scoped
owns_paths:
- research/commercial_activation/**
- scripts/activation_funnel_report.py
- tests/test_commercial_activation_event_spine.py
- tests/test_activation_funnel_report.py
decisions:
- DEC:COMMERCIAL-ACTIVATION-OWNS-JOURNEY-NOT-TRUTH-PLANES
- DEC:VALUE-AND-PERSONAL-ACT-PRECEDE-REGISTRATION
- DEC:FREE-SIGNUP-EXCLUDES-PLAN-AND-BILLING
- DEC:ANON-WATCHLIST-FOLDS-INTO-CANONICAL-WATCHLIST
- DEC:ANALYTICS-EID-USES-EXISTING-EVENT-PRIMARY-KEY
- DEC:BILLING-UNKNOWN-AND-MALFORMED-SUCCESS-FAIL-CLOSED
- DEC:TERMINAL-D7-COMPOSES-AFTER-E3-E4-SAME-CARRIER
discoveries:
- DSC:COMMERCIAL-ACTIVATION-OWNER-GAP-AND-COLLISION-CENSUS-20260903
artifacts:
- https://github.com/mastermindx-market-intelligence/Macro/pull/6835#issuecomment-5601315609
- https://github.com/mastermindx-market-intelligence/Macro/pull/6838
- https://github.com/mastermindx-market-intelligence/Macro/pull/6858
- https://github.com/mastermindx-market-intelligence/Macro/pull/7258
landmines:
- 'This workstream owns NO truth plane: auth, Stripe/billing, user_entitlements, Watchlist/Portfolio stores,
  Market OS product truth, analytics storage/transport, mail, and sentinel transport all keep their existing
  owners. A journey requirement that needs a truth-plane change is commissioned to that plane''s owner.

  '
- 'Analytics can describe behavior but can never grant product, payment, market, or trade authority; commercial
  telemetry never ranks or originates trades.

  '
- 'The September repo-wide Terminal CI-red observation is dated evidence, not current CI status or a reason
  to rerun its repair. Terminal #444, #446 and #435 have merged; #445 is closed/unmerged. Preserve the
  accepted composition and check actual current source and release gates only for newly admitted work.'
- 'Macro #6838 and #6858 already implemented and corrected the event-spine source. Do not reexecute the
  old CA1A implementation instructions. Implementation, report adoption, deployed behavior and the original
  section 16/full-journey proof remain separate.'
- 'The retained ordered-report review and producer R2 review accepted finite inert proposals. V1 was withdrawn;
  the pending-save/list-rebind finding remained separate. Synthetic Chrome store tests with application
  boot suppressed are not deployed product proof. Existing Draft #7258 is a distinct opt-in candidate,
  not an accepted integration.'
- Original source/history/caller/collision, archive-content, Flow Velocity and production-script refusals
  remain fenced. This records recovery does not retry, reconstruct or reroute them. The earlier local/runtime
  uncertainties remain with their original effects and owners.
waves:
- id: R0
  title: Owner charter, architecture decisions, collision census, CA1A handoff (records only)
  status: in_progress
  next_action: 'Finish the ten-record correction on original Macro #6835, consume its actual hosted checks
    and current release gates, then let the incumbent merge controller complete it. This source carrier
    grants no application or runtime execution.'
- id: CA1A
  title: Activation Event Spine V1 — registry-driven acceptance, eid idempotency, real producers, deterministic
    funnel report
  status: in_progress
  depends_on:
  - R0
  next_action: 'Source implementation is already merged in Macro #6838 and corrected in #6858. Here in_progress
    denotes remaining acceptance work, not a running worker. Recover any existing admissible report/adoption
    and section 16 receipts with the assigned incumbent owner. Preserve the accepted finite report/R2
    reviews, the distinct pending-save finding, and existing Draft #7258. Establish a currently accepted
    build and required adoption before any still-owed production canary under its actual admission. Do
    not rebuild the source carrier, rerun refused reads or claim the original proof completed.'
- id: CA1B
  title: Anonymous Insight → Canonical Save — third-symbol invitation, minimal signup, owner-verified
    fold, My Market return
  status: todo
  depends_on:
  - CA1A
  next_action: Commission only after the CA1A production canary passes; separate carrier.
- id: CA2
  title: Terminal journey parity — minimal signup and canonical save on Terminal
  status: todo
  depends_on:
  - CA1B
  next_action: 'After CA1B acceptance, scope Terminal journey parity with its existing owners. The old
    #444/#446/#435 source prerequisites have merged and #445 is closed/unmerged; their old release sequence
    and dated CI repair are not pending actions. Preserve verified trial and canonical-entitlement invalidation
    semantics on the accepted lineage.'
- id: CA3
  title: Free-activation projector and weekly CEO commercial report from real source events
  status: todo
  depends_on:
  - CA1B
  next_action: Includes the preregistered 30-day cohort review of the third-symbol hypothesis.
- id: CA4
  title: Contextual upgrade moments and paid-activation projector
  status: todo
  depends_on:
  - CA3
  next_action: First two moments — advanced evidence/depth ceiling and AI quota ceiling.
- id: CA5
  title: Since-you-were-last-here retention loop from canonical source changes
  status: todo
  depends_on:
  - CA3
  next_action: Honest no-change/stale/partial/unavailable states are in scope from day one.
- id: CA6
  title: Pricing and paywall experiments under preregistered statistical gates
  status: todo
  depends_on:
  - CA4
  - CA5
  next_action: No experiment ships without a preregistered promotion gate.
next_action: 'Complete the qualified original #6835 records carrier through actual CI and release. Then
  reconcile existing report/adoption and real-path acceptance evidence through the incumbent source owners,
  retaining the original section 16 and visitor-to-retention acceptance. No duplicate event-spine implementation
  or old Terminal release train.'
---

# Commercial Front Door, Activation, and Retention

The original visitor-to-retention objective, truth-plane boundaries and all eight waves
remain. The five policy laws still require value before registration, a personal act
before registration, a minimal free account, paid asks after value or purchase intent,
and authority from the existing payment/entitlement owners. The third-symbol prompt is
a preregistered hypothesis, not a measured outcome.

The September direct-grant and degraded-runtime narrative below records historical
authority. It is not a current runtime observation or a standing replacement for today's
admission requirements. The assigned November source-repair authority comes from the
current Chairman sweep and its source-linked claim.

## Source qualification — November 5, 2026

Assigned Sol root `macro-backlog-oldest-first-20261105-c3` qualifies this record under protected
Mastermind `5fbcbffe77a06e41bc590fa09d12a7e2baefb4f7`. The source boundary is the ten existing AgentOS records
on original PR #6835; [the current claim](https://github.com/mastermindx-market-intelligence/Macro/pull/6835#issuecomment-6661414324) transfers no application,
runtime, account, report or Watchlist writer.

The original PR's claim that frozen artifacts were committed under
`research/commercial_activation/` is retracted. The actual dated recovery source is
[receipt 5601315609](https://github.com/mastermindx-market-intelligence/Macro/pull/6835#issuecomment-5601315609): archive
`MMX_COMMERCIAL_ACTIVATION_SOL_BUNDLE_20260903.zip`, 32,868 bytes,
SHA-256 `642a1f27a33d30a7dc9cb076f7e1f8ec0880a5be3b349307fa4500f76628d27e`,
in authenticated Linear MAS-6 attachment `fcdbe167-85d4-4331-9857-b405ca2b0f49`.
That receipt records original-member hashes and authenticated custody, discloses the
unauthenticated 401, and does not claim a complete stored-object hash recomputation.
This qualification reads that published receipt, not the archive or attachment; it
publishes no replacement research payload and claims no fresh attachment availability.

Original policy references to that bundle are historical locators, not claims that this
carrier published those paths. Original source/history/caller/collision, archive-content,
Flow Velocity and production-script refusals remain fenced. No alternate carrier, retained
copy or reconstruction is used to repeat them. Current source merges and dated synthetic
proof remain distinct from the original production canary and full commercial journey.

## Source outcomes and retained proof gaps

| Component | Observed or retained evidence | Meaning for the current continuation |
|---|---|---|
| Macro #6815 | Merged `0007d955278c0456507bb4854eb85ddb41e2874e` | Preserve the existing flow-observation source; no rebuild |
| CA1A #6838 | Merged `d3294b0b974a4b592f68c43c9ab0ba4ad7e5bfe6` | Event-spine source already implemented |
| Collector correction #6858 | Merged `5e78f26767de167c1b47c6377bced1c8ce45003f` | Preserve DB-minted bigint `id`, separate UUID `eid`, `on_conflict=eid` |
| Terminal migration record #507 | Merged `7ca254722fa1aca8e3195c229e1d0701c01946cc` | Historical schema/DDL evidence; no new production read or DDL here |
| Terminal #444, #446 and #435 | Merged `b4fc51d38e966c1b2ee23bfb5a374def8dc35391`, `21e0d51d2c674f7c29360516c38bc859ce86047f`, `ce0d994202b18513b3135b07fa61d2bbfcfdf445` | Retain accepted entitlement/billing composition; no renewed old release train |
| Terminal #445 | Closed/unmerged; receipt 5592940939 identifies its behavior as absorbed into #446 | Do not reopen or commission a duplicate E-4 repair |
| Earlier ordered-report candidate | [5607238737](https://github.com/mastermindx-market-intelligence/Macro/pull/6838#issuecomment-5607238737): finite static review accepted/STOP; historical 69-test author evidence | Reviewed inert proposal; no source adoption or new execution inferred |
| Producer V1 and R2 | [5609711602](https://github.com/mastermindx-market-intelligence/Macro/pull/6838#issuecomment-5609711602): V1 withdrawn; R2 narrow attribution PASS, overall journey HOLD | Preserve the accepted finite review and distinct unresolved rebind/persistence finding |
| Native Chrome evidence | [5610769472](https://github.com/mastermindx-market-intelligence/Macro/pull/6838#issuecomment-5610769472): real DOM/storage/timers, synthetic page, boot suppressed | Store-API evidence, not production UI, deployed-byte or full-journey acceptance |
| Existing ordered-report PR #7258 | OPEN/Draft at `9872bbe611a3a2ce532f03e28ab15735371f38ef` on November 5 | Separate opt-in candidate; its source/adoption/check gates remain with its owner |

The September report, attribution and pending-save/list-rebind findings remain durable
evidence. This record does not re-attest today's deployed product as broken or repaired;
current adoption and real-path proof remain unverified in this source operation. The older
accepted report review does not approve the distinct #7258 implementation automatically.

The original section 16 proof still requires an accepted running build, genuine public
read, three controlled distinct Watchlist adds, exact same-visitor anonymous events, one
replay without a second row, a real report reaching save, analytics-failure noninterference,
client cleanup and retained evidence. Schema readback, source merges and synthetic browser
tests do not supply that acceptance. Recover any existing admissible accepted receipt through
its incumbent owner before proposing another canary; no refused action is retried here.

## Complete original September record — dated evidence

The complete original below is 6,507 UTF-8 bytes, Git blob `4f97365ca7757eed056798c7774ec74b5585ca6c`, including its final newline. Its historical attribution, erroneous factual assertions, then-current source/CI/runtime statements and execution directions are preserved for provenance. They are not active instructions or fresh verification; the qualified frontmatter and November disposition above control this record.

``````text
---
key: COMMERCIAL-ACTIVATION
title: Commercial Front Door, Activation, and Retention
objective: >
  Make the visitor-to-retention journey coherent, measurable, and trustworthy: genuine
  intelligence before registration; a personal act before a minimal free account;
  canonical state preserved through signup; measurable free and paid activation;
  contextual paid asks after value; authority-sourced billing; and a useful personalized
  return. Done means a real anonymous visitor can experience intelligence, save a
  personally meaningful state through free account creation, return to it, activate,
  upgrade at a measured value boundary, and retain — with every stage machine-readable
  from the existing analytics plane.
status: active
program: terminal-user-services
p0: MONETIZATION_AND_ONBOARDING
repos: [macro, terminal]
owner: ceo-sol
class: build
blast_radius: user_facing
ambiguity: scoped
owns_paths:
  - research/commercial_activation/**
  - scripts/activation_funnel_report.py
  - tests/test_commercial_activation_event_spine.py
  - tests/test_activation_funnel_report.py
decisions:
  - "DEC:COMMERCIAL-ACTIVATION-OWNS-JOURNEY-NOT-TRUTH-PLANES"
  - "DEC:VALUE-AND-PERSONAL-ACT-PRECEDE-REGISTRATION"
  - "DEC:FREE-SIGNUP-EXCLUDES-PLAN-AND-BILLING"
  - "DEC:ANON-WATCHLIST-FOLDS-INTO-CANONICAL-WATCHLIST"
  - "DEC:ANALYTICS-EID-USES-EXISTING-EVENT-PRIMARY-KEY"
  - "DEC:BILLING-UNKNOWN-AND-MALFORMED-SUCCESS-FAIL-CLOSED"
  - "DEC:TERMINAL-D7-COMPOSES-AFTER-E3-E4-SAME-CARRIER"
discoveries:
  - "DSC:COMMERCIAL-ACTIVATION-OWNER-GAP-AND-COLLISION-CENSUS-20260903"
artifacts:
  - research/commercial_activation/PROJECT_SOL_RETURN_V1_COMMERCIAL_ACTIVATION_20260903.md
  - research/commercial_activation/CLAUDE_ORCHESTRATOR_HANDOFF_V1_CA1A_EVENT_SPINE_20260903.md
landmines:
  - >
    This workstream owns NO truth plane: auth, Stripe/billing, user_entitlements,
    Watchlist/Portfolio stores, Market OS product truth, analytics storage/transport,
    mail, and sentinel transport all keep their existing owners. A journey requirement
    that needs a truth-plane change is commissioned to that plane's owner.
  - >
    Analytics can describe behavior but can never grant product, payment, market, or
    trade authority; commercial telemetry never ranks or originates trades.
  - >
    The Terminal required check "Terminal typecheck + tests" is red repo-wide (all PR
    branches, disjoint diffs); do not attribute it to #435/#444/#445 and do not weaken
    tests to pass it — it is owned by its own CI-health repair carrier.
waves:
  - id: R0
    title: Owner charter, architecture decisions, collision census, CA1A handoff (records only)
    status: in_progress
    next_action: Merge this records-only carrier; no runtime work starts from it.
  - id: CA1A
    title: Activation Event Spine V1 — registry-driven acceptance, eid idempotency, real producers, deterministic funnel report
    status: todo
    depends_on: [R0]
    next_action: >
      Execute on one Macro carrier (branch sol/commercial-activation-ca1a-event-spine-20260903)
      per research/commercial_activation/CLAUDE_ORCHESTRATOR_HANDOFF_V1_CA1A_EVENT_SPINE_20260903.md;
      at START repin macro main, rerun the owned-path collision census, and compose with
      the merged #6815 flowobs semantics. Production canary per §16 before any
      completion claim.
  - id: CA1B
    title: Anonymous Insight → Canonical Save — third-symbol invitation, minimal signup, owner-verified fold, My Market return
    status: todo
    depends_on: [CA1A]
    next_action: Commission only after the CA1A production canary passes; separate carrier.
  - id: CA2
    title: Terminal journey parity — minimal signup and canonical save on Terminal
    status: todo
    depends_on: [CA1B]
    next_action: >
      Requires settled Terminal carriers #444 → #445 → #435 (see
      DEC:TERMINAL-D7-COMPOSES-AFTER-E3-E4-SAME-CARRIER) and the repo-wide e2e CI repair.
  - id: CA3
    title: Free-activation projector and weekly CEO commercial report from real source events
    status: todo
    depends_on: [CA1B]
    next_action: Includes the preregistered 30-day cohort review of the third-symbol hypothesis.
  - id: CA4
    title: Contextual upgrade moments and paid-activation projector
    status: todo
    depends_on: [CA3]
    next_action: First two moments — advanced evidence/depth ceiling and AI quota ceiling.
  - id: CA5
    title: Since-you-were-last-here retention loop from canonical source changes
    status: todo
    depends_on: [CA3]
    next_action: Honest no-change/stale/partial/unavailable states are in scope from day one.
  - id: CA6
    title: Pricing and paywall experiments under preregistered statistical gates
    status: todo
    depends_on: [CA4, CA5]
    next_action: No experiment ships without a preregistered promotion gate.
next_action: >
  Merge the R0 records carrier, then execute CA1A on branch
  sol/commercial-activation-ca1a-event-spine-20260903 with a fresh START repin and
  collision census.
---

# WS:COMMERCIAL-ACTIVATION — Commercial Front Door, Activation, and Retention

The frozen product architecture (five laws), the complete journey/state vocabulary, the
data/identity/time/null/correction/provenance/authority contracts, the no-rebuild
boundaries, and the 30/60/90 capability sequence live in the frozen return:
`research/commercial_activation/PROJECT_SOL_RETURN_V1_COMMERCIAL_ACTIVATION_20260903.md`.

The five frozen laws, for fast orientation:

1. Value precedes registration.
2. A personal act precedes registration (v1 act: anonymous Watchlist save; third
   distinct symbol is the strongest initial prompt moment — a preregistered hypothesis).
3. Registration is free and minimal (Account + Preferences only; no Plan/Billing).
4. Paid asks follow activation or deliberate purchase intent.
5. Authority never leaks upward (billing from payment authority; unlocks from verified
   entitlement authority; analytics describes, never grants).

Authorization lineage: PROJECT_SOL packet MMX-SOL-COMMERCIAL-ACTIVATION-20260903-001
(status ARCHITECTURE_FROZEN_EXECUTION_NOT_ADMITTED) was ratified and granted end-to-end
execution authority by the Chairman directly to session
claude/mmx-commercial-activation-03fe73 on 2026-09-04. Executive OS runtime was
fixture/degraded at grant time, so runtime Job admission was substituted by the direct
Chairman grant; that substitution is recorded here and in the R0 handoff rather than
implied to have been an Executive Job.
``````
