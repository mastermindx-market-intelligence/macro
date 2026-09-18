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
  next_action: 'Macro #7275 is BUILT_NOT_PROVEN on its existing Radar-owned minute seam: a pure fail-closed resolver converts a complete qualified one-minute SessionTape into target-first/adverse-first/same-minute-ambiguous/neither without another store or fetch plane. Independent review is requested from mastermindx-2 and hosted checks are pending. DEC:TERMINAL-TACTICAL-MINUTE-EVIDENCE-CLASS admits current VendorMinuteReader output only as corrected-history minute-path evidence: historical known-at and prospective live freshness are unproven. Terminal #595 still owns refresh source; exact-head reproduction comments 5723524041/5723554467 prove failure masking and supply a disposable 47-pass repair spike. Consume the incumbent fix, then require a real current-session source-arrival receipt before any prospective/live minute claim.'
- id: R1
  title: Registered price-first hypotheses, causal evaluation and controls
  status: in_progress
  depends_on:
  - D0
  next_action: 'Macro #7270 current semantic head is 982a99a8adcac29c8158c2c31ec6639894dfdce1 after wiring its tactical suites into the canonical Entry Radar CI step. Local full Radar step 1522 passed/2 skipped; hosted ci-plan/contract-delta/fence/authority/hosted-plan are green, trusted executor packs remain QUEUED, and independent review is requested from MastermindX1 with no review result yet. R1-B v3 is frozen separately on draft Macro #7274 (freeze commit 1518ef7dabc74428bd79e7724f080226381b6fe4; 60 cells; no registration/outcomes); synthetic-only spec check on unchanged frozen hashes passed 9 cases and is durable at #7274 head 974bc84623e9207dfe7f7e494ba81824f4118525. Independent review is requested from mastermindx-2. Do not touch shared TrialLedger/implementation for R1-B until #7270 shared-source execution/review gate clears. No R1-A threshold rescue.'
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
next_action: 'Let #7270 current-head trusted executor packs and requested independent review complete under their existing owners; keep #7274 v3 docs/config-only until that shared-source gate clears, then append its frozen 60-cell grid before any outcome read and implement test-first. In parallel advance D1 through #7275 review/CI plus source-clock qualification on the existing VendorMinuteReader and consume #595/#601 when they move. Intraday top/HOD work remains a later separate preregistration under DEC:TERMINAL-TACTICAL-TOP-SIDE-BOUNDARY. No Executive prerequisite, live scan or validated edge is claimed.'
---

This record coordinates the approved Terminal product integration. Existing tactical and scientific owners remain controlling; no live execution is inferred from this authored record.


## 2026-09-17 direct-execution continuation
The Chairman correction removes the mistaken Executive-reconnect dependency. Independent source review advanced the current-history repair, and the first price-pattern/turn study now has a precise proposed measurement contract. New empirical implementation remains blocked by actual platform refusals, not by a need for further Chairman approval. The unfinished product retains its existing data/event/scientific owners.
