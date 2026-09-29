---
key: CONSUMER-DEFENSIVE-CDV1
title: "Consumer Defensive CDV-1 — P&G demand and earnings-quality dossier (Fable Meta-CEO program)"
objective: >
  Implement the frozen Consumer Defensive CDV-1 vertical as bounded native
  producer, publication, reader and display lanes. Done means the adjudicated
  task chain is merged, qualified through the named gate job, and released with
  readers enabled before the disabled producer flag.
status: active
program: earnings-intelligence
repos: [macro]
owner: fable-meta-ceo
class: build
blast_radius: user_facing
ambiguity: specified
owns_paths:
  - engine/company_intelligence/pg_profile.py
  - engine/company_intelligence/economic_observations.py
  - engine/earnings_narrative/economic_interpretation.py
  - engine/earnings_narrative/private_economic_stage.py
  - tests/earnings_economic_fixtures.py
  - tests/test_pg_economic_*.py
  - tests/test_earnings_economic_*.py
  - templates/earnings_wire/earnings-economic.js
  - templates/earnings_wire/_economic_dossier.html.j2
  - research/consumer_defensive/cdv1_program/**
depends_on:
  - WS:EARNINGS-INTELLIGENCE-OS
waves:
  - id: CDV1-T1-T8
    title: "Integrated Consumer Defensive CDV-1 implementation"
    status: in_progress
    next_action: >
      Land T1 (#7905: round-5 repair against the frozen probe suite, final
      Opus round bounded to R7–R16, CI on the exact head, merge), then dispatch
      T2 ∥ T3 off fresh main; T7 UI build and T8 release gates wait for the
      Semiconductors foundation (#7870).
next_action: >
  Land T1 (#7905) then T2 ∥ T3 → T4 → T5 ∥ T6; T7 is a merged CONTENT +
  CONTRACT spec awaiting the foundation host slot; readers first, producer
  flag last.
artifacts:
  - research/consumer_defensive/cdv1_program/README.md
  - research/consumer_defensive/cdv1_program/reviews/OPUS_PLAN_SEAM_AUDIT_2026-09-24.md
  - research/consumer_defensive/cdv1_program/design/T7_DOSSIER_DESIGN_SPEC_2026-09-24.md
  - research/consumer_defensive/cdv1_program/integration/FOUNDATION_INTEGRATION_MAP_2026-09-24.md
  - research/consumer_defensive/cdv1_program/release/RELEASE_READINESS_CENSUS_2026-09-24.md
decisions:
  - "DEC:CDV1-PLAN-SEAM-RULINGS"
  - "DEC:CDV1-FOUNDATION-INTEGRATION"
carrier:
  operation: gmi-consumer-defensive-research-20260923-sol-001
  research_pr: 7792
  ledger_pr: 7880
---

## Program boundary

This Fable Meta-CEO program implements the Consumer Defensive CDV-1 P&G demand
and earnings-quality dossier from the frozen implementation plan at plan pin
`88970a1a197884cc242f6d117cbf209603eccaf9`. The research carrier is Macro PR
#7792 on `sol/consumer-defensive-research-20260923`; it remains DRAFT/HOLD and
must carry documentation and research only. The implementation program ledger
and seam audit merged through Macro PR #7880 at `c52d80a1cc7a`.

The integrated lane order is T1 → T2∥T3 → T4 → T5∥T6 → T7 → T8. Readers are
qualified and released before the producer flag; `--economic-augment` remains
disabled last. Task gates G2 (real source admission), G3 (v2 closure
acceptance) and G4 (shared-shell mount acceptance) remain release evidence
gates, while the delegated owner exercises G1.

## Owned paths and shared seams

The frontmatter owns the planned path families from the frozen plan’s file
responsibility table, including the program-ledger subtree. It does not
transfer ownership of incumbent shared files. `issuer_profiles.py`,
`refresh_event_workspaces.py`, `private_publication.py`,
`build_earnings_public_wire.py`, `app/earnings.py`, and the sector and
state-of-themes templates remain owned by their incumbent workstreams; CDV-1
may touch them only at the named seams and with those owners’ accepted
contracts. `WS:EARNINGS-INTELLIGENCE-OS` owns the broad Earnings narrative and
company-intelligence homes, so this record depends on it rather than claiming
those shared homes.

## Operational law

- The plan and design are frozen at pin `88970a1a197884cc242f6d117cbf209603eccaf9`; do not re-research CDV-1 economics.
- The Opus seam audit findings F1–F19 are adopted as binding packet rulings through `DEC:CDV1-PLAN-SEAM-RULINGS`; do not re-audit the same seams.
- Never put implementation on the research carrier PR #7792.
- Sparse worktrees omit `data/` and `site/`; writing there can truncate committed artifacts.
- The private publication pointer uses strict conditional v2 writes. Never restore it best-effort after an uncertain v2 write.
- New implementation suites are wired into the existing `gate:code` job `earnings-economic-dossier`; do not add a second workflow or scheduler.

## Artifacts pending the Task 1 merge

The T1 seat rulings (`research/consumer_defensive/cdv1_program/reviews/SEAT_RULING_T1_PR_R{1,2,3}_2026-09-24.md`,
the Opus reviews beside them) and the two frozen probe suites
(`tests/test_pg_economic_observations_probes.py`, `tests/test_pg_economic_observations_probes_r2.py`) live on
PR #7905 until it merges; they join `artifacts:` then, because the Agent OS validator treats a path absent from
`origin/main` as a phantom artifact.

## Foundation integration (2026-09-24 re-scope)

Per the Chairman-relayed Astra CEO ruling (`DEC:CDV1-FOUNDATION-INTEGRATION`),
the shared base — theme-graph, evidence-foundation and rights layers on macro
#7870 plus the sector-intelligence contracts on main — is owned by the
Semiconductors session. The two `templates/earnings_wire/` adapter paths above
remain the planned home of the CDV-1 *adapter* only; the collapsed slot, host
toggle, issuer selector, auth wrapper, evidence dialog and asset families are
foundation surfaces this workstream does not own and must not mint. Task 7 is
therefore a merged CONTENT + CONTRACT spec (§6.2 field map binding on T3/T4/T6),
and its UI build waits for the foundation host slot. One rights mapping
(`rp_public_primary_v1 → sec_edgar`) is declared in T2, validated fail-closed in
T4 and gated at read in T6 through a single injectable registry-reader seam;
production PG publication stays refused until #7870 lands the `sec_edgar` row.
