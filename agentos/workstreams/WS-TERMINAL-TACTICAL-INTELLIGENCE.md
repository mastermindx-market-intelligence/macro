---
key: TERMINAL-TACTICAL-INTELLIGENCE
title: Terminal Tactical Intelligence — session-aware short-horizon opportunities
objective: Upgrade Terminal from descriptive Day Trade Mode to an integrated, evidence-grounded workflow for forming
  and confirmed short-horizon opportunities, conditional exhaustion/reclaim and candidate extremes, extended-session
  context, and separately evaluated one-to-three-day follow-through. Completion requires real inputs, existing-Radar
  integration, visible Terminal/browser proof, prospective evaluation and species-specific promotion decisions;
  options expressions are separately evaluated.
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
- DEC:TERMINAL-TACTICAL-R1A-DISPOSITION
- DEC:TERMINAL-TACTICAL-TOP-SIDE-BOUNDARY
- DEC:TERMINAL-TACTICAL-MINUTE-EVIDENCE-CLASS
discoveries:
- DSC:TERMINAL-TACTICAL-PILOT-HISTORY-QUALIFICATION
- DSC:TERMINAL-INTRADAY-REFRESH-FAILURE-MASKING
- DSC:TERMINAL-TACTICAL-R1A-EXTENDED-SESSION-RESULT
- DSC:TERMINAL-TACTICAL-R1A-CURRENT-MAIN-RECONCILIATION
- DSC:TERMINAL-TACTICAL-BOUNDED-MINUTE-SEAM
- DSC:TERMINAL-TACTICAL-MINUTE-AMBIGUITY-RESOLVER
waves:
- id: D0
  title: Existing-store qualification and causal cutoff consumer
  status: in_progress
  next_action: 'Preserve Terminal #601 at c0f36cb16fadd190ad747fc47a28405d9ec0fca4. Independent review remains unproven.
    One GitHub-native Copilot request was made on the same existing review operation; returned metadata, review
    list and timeline did not establish a reviewer or execution. No duplicate request, raw provider launch or Executive
    reconnection prerequisite. Require actual current-head review and concluded applicable checks before release.'
- id: D1
  title: Current pilot history and finer-grain availability qualification
  status: in_progress
  next_action: 'Macro #7275 is BUILT_NOT_PROVEN at cd25ac719522bdecfc15e35c81d0d5c1ca314c58 on the existing Radar-owned minute seam: the resolver is fail-closed, its authority/evidence class and adjusted-basis contract are caller-non-overridable, and it always exposes source_clock_proven=false / availability_time_unproven. Exact-head C3 reader/resolver suite: 66 passed; independent review remains requested from mastermindx-2. Hosted packs 3-5 failed before candidate checkout because the shared self-hosted runner received a shutdown signal; comment 5741053579 preserves the exact infrastructure evidence and no blind rerun was issued. Terminal #595 still owns refresh source and remains CHANGES_REQUESTED at ba7c48c on the proven failure-masking defects; #601 remains green but awaits requested independent review.'
- id: R1
  title: Registered price-first hypotheses, causal evaluation and controls
  status: in_progress
  depends_on:
  - D0
  next_action: 'Macro #7270 head a3c539675e6314ad8fcdf5c633b8d136e79c0fd8 is conflict-free against main 7babc6c17d50968683a0b7fc49323c103edf89da. Current-main ledger 1676 + exactly 84 R1-A cells = 1760, with all main rows retained once and integrated SHA256 beb48ca70d10c81e9c149afea5dbdbc31614bfe2489f2558e8c45d8fb112a794. Exact integration proof: 68 focused tests, full Radar+tactical 1520 passed/4 skipped, contract-delta 0/0, compile/diff clean. Current-head hosted CI is running and independent review remains requested from MastermindX1 with no result. R1-B v3 remains frozen on #7274 head 974bc84623e9207dfe7f7e494ba81824f4118525: 60 cells, no registration/outcomes, 9-case synthetic spec check only. Do not touch shared TrialLedger/implementation for R1-B until #7270 hosted/review gate clears. No R1-A threshold rescue.'
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
- WS:LIVE-ENTRY-RADAR retains tactical event/evaluator ownership; this product-integration record does not create
  another radar, replay engine, store or WebSocket plane.
- WS:TECHNICAL-OPPORTUNITY-INTELLIGENCE retains its incumbent higher-timeframe setup/remaining-opportunity work.
  No existing wave or source custody is taken over.
- Setup Species and Evaluation OS remain the scientific owners. Context-only evidence is not rank, sizing, gating,
  trade or options-expression authority.
- Intraday top/HOD research must remain distinct from WS:TOP-ANATOMY winner-maturation/OOT research; no Top Anatomy threshold/OOT import and no automatic short/sell/trim authority. See DEC:TERMINAL-TACTICAL-TOP-SIDE-BOUNDARY.
- DSC:TERMINAL-TACTICAL-PILOT-HISTORY-QUALIFICATION distinguishes local-file absence, static publication, live freshness
  and historical availability.
- 'Terminal #595 is the existing refresh carrier. Do not modify its source without current custody reconciliation.'
do_not_redo:
- 'The Chairman approved the price-first architecture and first milestone on 2026-09-17; Terminal #598 comment 5720001976.
  Do not request that approval again.'
- 'D0 implementation exists on Terminal #601 at 773b16f8e825ab4b39ce3c7a5fa5caf32868d55f; do not create a replacement
  branch or rebuild the qualifier.'
- Do not retry the predecessor blocked live INTC API inspection through another tool or transport. Static non-INTC
  archival qualification is a separate completed operation.
- 'Session-chain qualification already exists at Terminal c0f36cb16fadd190ad747fc47a28405d9ec0fca4: 65 focused passes;
  exact original input hashes reused. Do not refetch/re-census the same archived files or treat nominal-grid counts
  as strategy accuracy.'
- 'Current Chairman correction: Executive is unfinished. Terminal #598 comment 5721925192 supersedes the prior user-reconnect
  prerequisite. Do not repeat Executive authentication probes or ask for design approval.'
- 'R1-A registration, implementation and corrected-history result are already on Macro #7270. Do not rerun the unchanged 84-cell grid or relax its thresholds after seeing outcomes; consume TTI_R1A_REPORT.md and DEC:TERMINAL-TACTICAL-R1A-DISPOSITION.'
- 'A bounded minute ambiguity resolver already exists on Macro #7275. Do not build another minute resolver, minute store or fetch plane; qualify and consume the existing Radar-owned seam if the PR is accepted.'
- 'MinuteBar.knowable_at is a mathematical bar-close clock, not source arrival. Never promote current VendorMinuteReader history to as-observed evidence without an actual archived availability receipt; see DEC:TERMINAL-TACTICAL-MINUTE-EVIDENCE-CLASS.'
artifacts:
- terminal:docs/research/TERMINAL_TACTICAL_D0_EVIDENCE_2026-09-17.md
- terminal:docs/research/TERMINAL_TACTICAL_D0_CONTRACT.md
- agentos/handoffs/TERMINAL-TACTICAL-INTELLIGENCE-2026-09-17-d0.md
- terminal:docs/research/TERMINAL_TACTICAL_SESSION_CHAIN_EVIDENCE_2026-09-17.md
- research/species/tti_r1/STATUS.md
- research/species/TTI_R1A_PREREG.md
- research/species/TTI_R1A_REPORT.md
- research/species/tti_r1/RESULT.json
- research/species/tti_r1/REGISTRATION_RECEIPT.json
next_action: 'Consume #7270 head a3c539675e6314ad8fcdf5c633b8d136e79c0fd8 current-head hosted checks and requested independent review; do not merge/promote on local integration proof alone. Keep #7274 v3 docs/config-only until that gate clears, then append its frozen 60-cell grid before any outcome read and implement test-first. In parallel finish D1 current-session arrival-receipt hardening on the existing #7275 carrier, preserving corrected-history versus live-arrival evidence classes, and consume #595/#601 when their incumbent owners move. Intraday top/HOD remains a later separate preregistration. No Executive prerequisite, live scan, or validated edge is claimed.'
---

This record coordinates the approved Terminal product integration. Existing tactical and scientific owners remain controlling; no live execution is inferred from this authored record.


## 2026-09-17 direct-execution continuation
The Chairman correction removes the mistaken Executive-reconnect dependency. Independent source review advanced the current-history repair, and the first price-pattern/turn study now has a precise proposed measurement contract. New empirical implementation remains blocked by actual platform refusals, not by a need for further Chairman approval. The unfinished product retains its existing data/event/scientific owners.
