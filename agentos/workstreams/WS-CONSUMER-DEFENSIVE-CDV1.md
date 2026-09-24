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
    status: todo
    next_action: >
      Adjudicate lane returns in dependency order T1→T2∥T3→T4→T5∥T6→T7→T8;
      release readers first, producer flag last.
next_action: >
  Adjudicate lane returns in dependency order T1→T2∥T3→T4→T5∥T6→T7→T8;
  release readers first, producer flag last.
artifacts:
  - research/consumer_defensive/cdv1_program/README.md
  - research/consumer_defensive/cdv1_program/reviews/OPUS_PLAN_SEAM_AUDIT_2026-09-24.md
decisions:
  - "DEC:CDV1-PLAN-SEAM-RULINGS"
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
