---
key: BIOCATALYST-CORE-PRODUCT
title: BioCatalyst Decision Intelligence V3 — end-to-end research product
objective: >
  Deliver BioCatalyst Decision Intelligence V3 end to end: preserve proven
  source-truth lanes, broaden lawful correction-safe event discovery, bind
  events to asset, company and security identities plus economic-exposure
  relationships supplied by canonical owners,
  and present an explainable What Matters Next research workflow with
  separate fact, timing, expectation, probability, issuer-materiality,
  history, incorporation and ResearchPriority objects. R0 freezes the
  architecture and owner contracts; R1A and R1B must then prove broad real
  source truth and the first useful production board before R2-R7 advance.
  Completion requires Truth, Intelligence, Product and Learning evidence;
  records, infrastructure, CI or merge alone are not completion.
status: active
program: biocatalyst
repos: [macro]
owner: coo-fable
class: build
blast_radius: user_facing
ambiguity: specified
owns_paths:
  - app/biocatalyst.py
  - engine/biocatalyst/catalyst_events.py
  - templates/biocatalyst.html.j2
  - templates/biocatalyst.js
  - templates/biocatalyst.css
  - site/biocatalyst.js
  - site/biocatalyst.css
  - tests/test_biocatalyst_api.py
  - tests/test_biocatalyst_page.py
  - tests/test_biocatalyst_d0a_design_contract.py
  - tests/test_biocatalyst_d0b_ui.py
  - tests/test_biocatalyst_hydration.py
  - tests/biocatalyst_hydration_harness.js
  - tests/test_biocatalyst_peer_api_contract.py
  - tests/test_biocatalyst_catalyst_radar.py
  - tests/test_biocatalyst_catalyst_radar_api.py
  - research/BIOCATALYST_P1_*
  - agentos/workstreams/WS-BIOCATALYST-CORE-PRODUCT.md
  - agentos/handoffs/BIOCATALYST-CORE-PRODUCT-*
waves:
  - id: P1-1
    title: Catalyst Radar — Trial Milestones first slice
    status: done
    next_action: >
      P1-1 is complete. No next CORE-PRODUCT wave is currently commissioned.
      P1-2 requires a separate explicit Sol ruling. The 2026-08-26T02:00Z
      source/launch-soak boundary remains owned by its source-governance path:
      window end grants no expansion authority; exact evidence must be frozen
      and adjudicated before any successor source/cohort transition.
  - id: P1-AVAIL-1
    title: P1-1 availability regression diagnosis (MAS-172, Chairman report)
    status: done
    next_action: >
      CLOSED 2026-08-28 pending Sol's terminal acceptance on the thread.
      Root cause: the Chairman's browser was signed out (designed locked
      state = the reported "down"); no origin-side defect existed; nothing
      was repaired because nothing was broken. One transient
      Supabase-upstream /api/me 502 window (22:56-22:59Z Aug 27) self-healed.
      After the Chairman signed back in, the full step-(9) entitled matrix
      PASSED on the real production path (200/400/401 contracts, current-hour
      fresh 4/4 generation, exact 3+1+0+4=8 arithmetic, 6 lineage entries
      EN/ZH, geometry clean at 2055/1280 EN+ZH and mobile 500x844 real-window
      with the exact-390 deviation recorded, zero console errors, zero
      4xx/5xx/524, exact accepted asset stamps). Receipts:
      research/BIOCATALYST_P1_AVAIL_1_AVAILABILITY_AUDIT_2026-08-28.md (PR
      #6594, merge 2299cbafe425) and
      research/BIOCATALYST_P1_AVAIL_1_ENTITLED_REACCEPTANCE_2026-08-28.md.
  - id: R0-V3
    title: Decision Intelligence V3 architecture freeze and estate reconciliation
    status: in_progress
    pr: 6712
    next_action: >
      Continue the existing PR #6712 source-repair carrier. Findings 1, 2, 3
      and 5 plus PR hygiene are accepted. Close finding 4 with an independent
      six-state experience review, close finding 6 by reviewing this canonical
      workstream reconciliation, then run fresh exact-head/current-main
      integration proof and whole-R0 Sol acceptance. R1A and R1B remain
      unstarted and require fresh bounded assignments after R0 acceptance.
decisions:
  - "DEC:BIOCATALYST-DECISION-INTELLIGENCE-V3-RECHARTER"
  - "DEC:BIOCATALYST-FABLE-COO-END-TO-END-DELEGATED-AUTHORITY"
  - "DEC:BIOCATALYST-P1-FIRST-VERTICAL-MILESTONE-RADAR"
  - "DEC:BIOCATALYST-PDUFA-TRUTH-IS-CORPORATE-DISCLOSURE-PLANE"
  - "DEC:BIOCATALYST-CASH-RUNWAY-OWNED-BY-CAPITAL-STRUCTURE"
  - "DEC:BPC-CATALYST-COMPOSES-WITH-COMPANY-EVENT-NOT-FISCAL-WORKSPACE"
  - "DEC:BIOCATALYST-RECOVERY-V2-CORE-NOT-JV-OR-BCI"
landmines:
  - >-
    Ownership is narrow by Sol order (P1-0R review): this workstream does NOT
    own engine/biocatalyst/** or a blanket tests/test_biocatalyst_* claim —
    those globs include source/publication/history/storage/regulatory and
    source-soak surfaces owned elsewhere. Owned tests are the product-facing
    files enumerated in owns_paths only. The P1-1 implementation PR adds the
    exact new engine/biocatalyst/catalyst_events.py and its exact new test
    path to owns_paths when those files actually exist. Reading another
    plane/module never requires owning it.
  - >-
    Explicitly OUT of this workstream (Sol P1-0R charter): P0 recovery
    (WS:BIOCATALYST-RECOVERY-V2 is closed); BPC JV snapshot
    reconstruction/onboarding (WS:BPC-JV-RECON); source-soak governance (the
    launch SLO / source-registry truth program owns it); duplicate
    Company/Stock Identity; Capital Structure/FIF computations (consume,
    never compute — DEC:BIOCATALYST-CASH-RUNWAY-OWNED-BY-CAPITAL-STRUCTURE);
    Options transport; BCI market-episode/analogue intelligence (#5821 stays
    a draft candidate); Neural Web; Prophet/rank/selection/size authority.
  - >-
    Preserve the proven P1-1 Trial Milestones EventFact/API as deterministic
    source truth; no model result belongs inside that fact payload. V3 may add
    separate typed TimingAssessment, ExpectationBaseline,
    OutcomeProbabilityAssessment, IssuerMaterialityAssessment,
    HistoricalResponseDistribution, IncorporationEvidence and
    ResearchPriority objects only in their gated waves and owner-compatible
    contracts. No opaque or generic composite score is allowed. Unsupported
    estimates must be NOT_ESTIMABLE. ResearchPriority is explainable research
    triage, never entry/exit, sizing, Availability, Prophet promotion or trade
    authority.
  - >-
    R1A and R1B may start only through fresh bounded assignments after whole-R0
    acceptance. R2-R7 cannot outrun the real broad-data R1B product vertical.
    PR #6389 / WS:BPC-JV-RECON remains a separate historical-data carrier and
    is not an R1B prerequisite; consume it later only if lawfully reconciled.
  - >-
    Public wording law (Sol-ratified): "Trial milestone", "Primary
    completion", "Study completion", "days to milestone"; never label a
    registry completion date a "readout", "catalyst date", or market event.
  - >-
    Zero mutation of the frozen soak surface until the post-soak
    successor-registry transition concludes: config/biocatalyst_sources.yml,
    the launch SLO manifest, CT.gov cadence, fixed cohort, freshness budget,
    denominator law, launch verifier. 2026-08-26T02:00Z ends the observation
    window; it grants no expansion authority by itself (soak evidence freeze
    → pass/fail adjudication → successor transition first).
  - >-
    Prospective PDUFA enters only through the Company Intelligence
    disclosure-plane consumer port
    (DEC:BIOCATALYST-PDUFA-TRUTH-IS-CORPORATE-DISCLOSURE-PLANE); never
    duplicate SEC/IR ingest, never manufacture forward dates from Drugs@FDA.
  - >-
    Never mint a local CIK/security map. Identity joins reuse an existing
    canonical PIT Company/Stock Identity read seam when archaeology proves
    one suitable; otherwise surfaces carry a typed
    company_identity_not_joined / ticker_only state.
  - >-
    Browser evidence drill-down exposes only the public-safe pointer-bound
    evidence projection (NCT, source URL, source clocks, generation-safe
    provenance, public record-history versions/revision values) — never
    private worker receipts, R2 keys, filesystem paths, private hashes, or
    credentials; do not widen macro-api filesystem access.
do_not_redo:
  - >-
    Do not re-adjudicate the first vertical; Sol ratified
    Catalyst Radar — Trial Milestones (P1-0R, 2026-08-20).
  - >-
    Do not reopen the completed P0 recovery chain (#5788→#6090) or reuse
    WS:BIOCATALYST-RECOVERY-V2 as an implementation catch-all.
  - >-
    Do not map TERMINATED / WITHDRAWN / SUSPENDED to a generic "cancelled
    catalyst". Preserve the exact trial status; SUSPENDED is paused, not
    terminal; a future milestone may be marked inactive because of trial
    status without inventing an event-cancellation fact.
  - >-
    P1-1 is now PROVEN_LIVE_COHORT_LIMITED on the real current four-NCT
    production cohort. Do not widen that bounded claim into full functional
    parity, production-scale proof, source-soak acceptance, or authority to
    start P1-2. The broader parity ledger remains PARTIAL.
artifacts:
  - agentos/handoffs/BIOCATALYST-CORE-PRODUCT-2026-09-06.md
  - research/biocatalyst_decision_intelligence_v3/BIOCATALYST_DECISION_INTELLIGENCE_V3_MASTERPLAN_2026-09-01.md
  - research/BIOCATALYST_P1_AVAIL_1_ENTITLED_REACCEPTANCE_2026-08-28.md
  - research/BIOCATALYST_P1_AVAIL_1_AVAILABILITY_AUDIT_2026-08-28.md
  - research/BIOCATALYST_P1_RECHARTER_AND_FIRST_VERTICAL_ARCHITECTURE_2026-08-20.md
  - research/BIOCATALYST_P1_CONTINUATION_HANDOFF_2026-08-20.md
  - research/BIOCATALYST_P1_1_PRODUCTION_ACCEPTANCE_2026-08-22.md
  - research/BIOCATALYST_P1_1R_PRODUCTION_ACCEPTANCE_2026-08-23.md
next_action: >
  Continue BioCatalyst Decision Intelligence V3 R0 on PR #6712 from the
  repaired source, not the completed P0 recovery or stopped original
  principal. Independently review the six-state experience evidence and this
  Agent OS reconciliation, then prove the exact resulting head against current
  main and issue whole-R0 Sol acceptance. Preserve the proven P1 facts-only
  payload and cohort-limited production claim. After R0 acceptance, commission
  fresh bounded R1A source-graduation and R1B What Matters Next verticals; do
  not infer source activation, deployment, model promotion or trade authority
  from this organizational record.
---

## Context

Created by Sol's P1-0R authority-closure ruling (2026-08-20) as the P1
workstream home the recharter's §11.2 asked for. The P0 recovery program
(WS:BIOCATALYST-RECOVERY-V2) is complete and closed; this workstream owns
what comes after: product projections over the proven truth plane, the
Catalyst Radar container whose first lane is Trial Milestones (registry
schedule facts) and whose designed second tenant is Regulatory/PDUFA via the
disclosure-plane port, dossier/Explorer workflows, and bounded product APIs.
It is deliberately not a new semantic program — program stays `biocatalyst`.

Wave P1-1's frozen spec lives in
`research/BIOCATALYST_P1_CONTINUATION_HANDOFF_2026-08-20.md` (as amended by
P1-0R); the architecture constitution is
`research/BIOCATALYST_P1_RECHARTER_AND_FIRST_VERTICAL_ARCHITECTURE_2026-08-20.md`.

## Historical lifecycle reconciliation — 2026-08-24/25

At that time, Sol reconciled the top-level lifecycle from stale `active` to
`parked`: P1-1 was complete and production-proven at its bounded cohort, there
was no live carrier or commissioned successor wave, and P1-2 required a
separate Sol ruling. That historical correction remains valid for the interval
before the V3 recharter.

## V3 reactivation — 2026-09-01 onward

Sol ratified Decision Intelligence V3 under the existing `biocatalyst` program
and this canonical workstream. R0 is an active records-only architecture and
estate-reconciliation wave on PR #6712; it does not itself prove product,
source activation, deployment or model authority. The earlier facts-only rule
continues to govern the P1-1 EventFact payload, while the V3 constitution
permits separate typed and gated intelligence objects. R1A/R1B remain
unstarted until R0 receives whole-program acceptance.
