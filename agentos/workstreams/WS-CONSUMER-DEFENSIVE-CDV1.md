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
---

## Skeleton

This workstream record is being initialized and will describe the program
boundary, carrier state, ownership seams and operational law in a subsequent
commit.
