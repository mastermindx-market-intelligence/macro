---
key: TERMINAL-TACTICAL-INTELLIGENCE
title: Terminal Tactical Intelligence — session-aware short-horizon opportunities
objective: Upgrade Terminal from descriptive Day Trade Mode to an integrated, evidence-grounded workflow
  for forming and confirmed short-horizon opportunities, conditional exhaustion/reclaim and candidate
  extremes, extended-session context, and separately evaluated one-to-three-day follow-through. Completion
  requires real inputs, existing-Radar integration, visible Terminal/browser proof, prospective evaluation
  and species-specific promotion decisions; options expressions are separately evaluated.
status: active
program: market-timing-intelligence
repos:
- macro
- terminal
owner: ceo-sol
class: build
blast_radius: user_facing
ambiguity: scoped
owns_paths:
- agentos/workstreams/WS-TERMINAL-TACTICAL-INTELLIGENCE.md
- agentos/decisions/DEC-TERMINAL-TACTICAL-
- agentos/discoveries/DSC-TERMINAL-TACTICAL-
- agentos/handoffs/TERMINAL-TACTICAL-INTELLIGENCE-
- terminal:ingest/intraday_qualification.py
- terminal:scripts/qualify_intraday_research.py
- terminal:config/tactical_research_pilot.json
- terminal:docs/research/TERMINAL_TACTICAL_
decisions:
- DEC:TERMINAL-TACTICAL-PRICE-FIRST-APPROVAL
discoveries:
- DSC:TERMINAL-TACTICAL-PILOT-HISTORY-QUALIFICATION
waves:
- id: D0
  title: Existing-store qualification and causal cutoff consumer
  status: in_progress
  next_action: 'Review and release Terminal PR #601 at 773b16f8e825ab4b39ce3c7a5fa5caf32868d55f through
    its existing gates. Local archival-input proof and 46 focused tests exist; no production or parent
    completion is asserted.'
- id: D1
  title: Current pilot history and finer-grain availability qualification
  status: todo
  next_action: 'Use the existing data owner: reconcile Terminal #595 for freshness; separately qualify
    whether an existing one-minute history/capture path can serve the pilot. Preserve the held INTC
    live operation. Do not create another updater or infer vendor entitlement from static 404s.'
- id: R1
  title: Registered price-first hypotheses, causal evaluation and controls
  status: todo
  depends_on:
  - D0
  next_action: 'Freeze experiments in the existing Setup Species/Evaluation ownership: extended-hours
    persistence after weakness, exhaustion/reclaim versus continuation controls, then remaining-session
    and one-to-three-day outcomes. Use corrected history only with explicit limitations; admission
    and promotion remain separate.'
- id: I1
  title: Existing Radar-owned shadow opportunity integration
  status: todo
  depends_on:
  - R1
  - D1
- id: U1
  title: Terminal forming/confirmed workspace and chart explanation
  status: todo
  depends_on:
  - I1
- id: V1
  title: Prospective calibration, browser proof and species-specific adjudication
  status: todo
  depends_on:
  - U1
- id: O1
  title: Options incremental information and separately tested short-dated expressions
  status: todo
  depends_on:
  - V1
landmines:
- WS:LIVE-ENTRY-RADAR retains tactical event/evaluator ownership; this product-integration record
  does not create another radar, replay engine, store or WebSocket plane.
- WS:TECHNICAL-OPPORTUNITY-INTELLIGENCE retains its incumbent higher-timeframe setup/remaining-opportunity
  work. No existing wave or source custody is taken over.
- Setup Species and Evaluation OS remain the scientific owners. Context-only evidence is not rank,
  sizing, gating, trade or options-expression authority.
- DSC:TERMINAL-TACTICAL-PILOT-HISTORY-QUALIFICATION distinguishes local-file absence, static publication,
  live freshness and historical availability.
- 'Terminal #595 is the existing refresh carrier. Do not modify its source without current custody
  reconciliation.'
do_not_redo:
- 'The Chairman approved the price-first architecture and first milestone on 2026-09-17; Terminal
  #598 comment 5720001976. Do not request that approval again.'
- 'D0 implementation exists on Terminal #601 at 773b16f8e825ab4b39ce3c7a5fa5caf32868d55f; do not
  create a replacement branch or rebuild the qualifier.'
- Do not retry the predecessor blocked live INTC API inspection through another tool or transport.
  Static non-INTC archival qualification is a separate completed operation.
artifacts:
- terminal:docs/research/TERMINAL_TACTICAL_D0_EVIDENCE_2026-09-17.md
- terminal:docs/research/TERMINAL_TACTICAL_D0_CONTRACT.md
- agentos/handoffs/TERMINAL-TACTICAL-INTELLIGENCE-2026-09-17-d0.md
next_action: 'Adjudicate the exact D0 candidate in Terminal #601 after independent review and required
  checks; use its measured gaps to advance existing-owner data qualification. Preserve #598 as the
  product carrier and do not claim live scanning or a proven strategy.'
---

This record coordinates the approved Terminal product integration. Existing tactical and scientific owners remain controlling; no live execution is inferred from this authored record.
