---
key: PROPHET-US-B04-EVIDENCE-DOSSIER-CONTRACT
question: >
  What is the binding contract for the Prophet US episode evidence dossier — its wrapper,
  its typed absence vocabulary, its rights and eligibility fields — and in what order is it
  built? (R6 work card B04, ruling R6-B04-01 over the B04 contract census)
answer: >
  The census's Q6 contract is adopted with six amendments. Wrapper
  `prophet.episode_evidence_dossier/v1`; nine closed absence reason codes with verbatim
  EN/ZH sentences (NOT_CAPTURED_AT_DECISION, CORRECTED_LATER,
  HISTORICAL_EVENT_SET_UNAVAILABLE, IDENTITY_BINDING_CONFLICT, RIGHTS_INTERNAL_ONLY,
  RIGHTS_NOT_A_SOURCE, CONFLICTING_SOURCE_CLOCKS, EXACT_LINEAGE_UNAVAILABLE, UNKNOWN).
  A1: a machine-readable posture map `config/prophet_source_rights_postures.yml` derived
  from the rights register, carrying postures only and no commercial terms. A2:
  `evidence_class.basis` is closed to `D07_OPEN` or `D07_REG:<registration artifact path>`
  and `value ∈ {OBSERVED_AS_RUN, PUBLIC_INFO_REPLAY, RETROSPECTIVE, null}`, a value being set
  only when the basis names a merged registration artifact. A3: the `current` view is never
  decision-admissible (`decision_admissibility=false`, `view_basis=RESEARCH_KNOWN_NOW`).
  A4: every authority boolean is false. A5: a route-boundary rights test runs on the
  serialized JSON. A6: proof event AAPL FY2026 Q3 with six fixtures. Build order: B04-A
  (wrapper, codes, NOT_ASSERTED, typed historical absence; new
  `engine/prophet_lab/evidence_dossier.py`, route
  `GET /api/prophet/lab/v1/episodes/{episode_id}/dossier`,
  `tests/test_prophet_lab_dossier_b04a.py`) → B04-B (rights gate) → B04-C (current view
  and renderer) → B04-D (evidence-class propagation, blocked on D07).
rationale: >
  The census found the existing evidence path COVERED for two questions, PARTIAL for two
  and BLIND for two — historical event-set missingness had no typed absence and no
  source-family rights gate existed at the detail boundary. A closed absence vocabulary
  with verbatim bilingual copy makes every hole visible to the user without narrating
  internals, the closed basis field keeps D07 honest until a registration artifact
  exists, and the ordered build lets three units ship while the fourth waits on D07.
alternatives:
  - option: Let the dossier state an evidence class from date-filtered retrieval now.
    why_not: That is D07's forbidden shortcut; the class stays null under `D07_OPEN` until a registration artifact is merged.
  - option: Carry commercial licence terms in the posture map for completeness.
    why_not: Commercial terms are never recorded in program artifacts; postures alone decide user-facing versus internal-only.
  - option: Ship one large B04 unit including the D07-dependent propagation.
    why_not: It would block three deliverable units on an open decision; the ordered split keeps B04-A/B/C shippable.
evidence:
  - research/prophet_v4/r6_program/wave2/B04_EVIDENCE_DOSSIER_CONTRACT_CENSUS_2026-09-23.md
  - research/prophet_v4/r6_program/rulings/R6-B04-01_DOSSIER_CONTRACT_2026-09-24.md
  - research/licenses/PROPHET_US_SOURCE_RIGHTS_REGISTER_2026-09-23.md
  - Macro PR 7850 (census + ruling)
affects:
  - WS:PROPHET-US-V4-RECOVERY
confidence: high
reversibility: costly
decided_by: coo-fable
decided_at: 2026-09-23
---

## Scope

Binds the dossier contract for every Prophet US surface that shows evidence for an
episode (B07, B14, B17 consume it) and fixes the build order. B04-A is commissioned on
the external fabric as the first unit; B04-D waits on `DEC:PROPHET-US-D07-*` when D07 is
resolved.

## What this decision does not do

It does not resolve D07, does not grant any source a user-facing posture (the register
does), does not create authority booleans that are true, and does not change the episode
registry or its anchor vocabulary (`DEC:PROPHET-US-D02-EPISODE-ADMISSION-GATED`).
