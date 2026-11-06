---
key: TERMINAL-TACTICAL-INTELLIGENCE
title: Terminal Tactical Intelligence — session-aware short-horizon opportunities
objective: Upgrade Terminal from descriptive Day Trade Mode to an integrated, evidence-grounded workflow for
  forming and confirmed short-horizon opportunities, conditional exhaustion/reclaim and candidate extremes,
  extended-session context, and separately evaluated one-to-three-day follow-through. Completion requires real
  inputs, existing-Radar integration, visible Terminal/browser proof, prospective evaluation and species-specific
  promotion decisions; options expressions are separately evaluated.
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
- DEC:TERMINAL-TACTICAL-SYNTHETIC-CONSTRUCTION-CONTINUE
- DEC:TERMINAL-TACTICAL-R1B-STACKED-RESEARCH-ADMISSION
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
  status: done
  next_action: 'DONE source: Terminal601 actually merged 2026-09-20 as f4bc91827a075748dc5c97c889888ae2ee643a87.
    Retain its corrected-history/as-observed distinction and accepted evidence; do not rebuild or repeat its
    source review merely because a historical handoff says pending.'
- id: D1
  title: Current pilot history and finer-grain availability qualification
  status: in_progress
  next_action: Terminal595 actually merged 2026-10-04 as fb6f5cc39e592e7f9967835a85617b4fef427b09; current
    store freshness is still a separate proof. Macro7275 remains Draft at bf047bbf259d8f579ad8254f1ab3de80c5204299
    with its source review/current checks and natural current-RTH health-path receipt still owed. Preserve
    the existing Radar minute seam and all original source-availability limits.
- id: R1
  title: Registered price-first hypotheses, causal evaluation and controls
  status: in_progress
  depends_on:
  - D0
  next_action: R1-A Macro7270 actually merged 2026-10-03 as 5f20adbd6be6b136b2efe41585bd4ef964b5bf2e; NO_PROMOTION
    remains frozen. R1-B Macro7274 at51bb68b2cf9680f9abf4546a602172a5e157a7e3 contains its completed registered
    v4 result and spent study identity; source comment5984265269 and RUN_RECEIPT_V4.json require independent
    admission-artifact adjudication and retain Draft/release holds. Consume that existing result; never register
    or run the spent v4 study again. No live, rank, alert, size, trade or options authority follows.
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
- WS:LIVE-ENTRY-RADAR retains tactical event/evaluator ownership; this product-integration record does not
  create another radar, replay engine, store or WebSocket plane.
- WS:TECHNICAL-OPPORTUNITY-INTELLIGENCE retains its incumbent higher-timeframe setup/remaining-opportunity
  work. No existing wave or source custody is taken over.
- Setup Species and Evaluation OS remain the scientific owners. Context-only evidence is not rank, sizing,
  gating, trade or options-expression authority.
- Intraday top/HOD research must remain distinct from WS:TOP-ANATOMY winner-maturation/OOT research; no Top
  Anatomy threshold/OOT import and no automatic short/sell/trim authority. See DEC:TERMINAL-TACTICAL-TOP-SIDE-BOUNDARY.
- DSC:TERMINAL-TACTICAL-PILOT-HISTORY-QUALIFICATION distinguishes local-file absence, static publication, live
  freshness and historical availability.
- 'Terminal #595 is the existing refresh carrier. Do not modify its source without current custody reconciliation.'
do_not_redo:
- Do not rerun or re-register the spent R1-B v4 study, restore zero-outcome wording as current state, or create
  a second results carrier.
- Do not rerun or retune the unchanged R1-A 84-cell study, rebuild D0, or recensus the unchanged archived pilot.
- Do not replay any recorded platform, source, provider, INTC, authentication or review effect through another
  carrier. Later source receipts are not blanket clearance.
- Do not treat a merged dependency, published research result or records checkpoint as live freshness, calibrated
  probability, trade authority or parent product completion.
- 'The Chairman approved the price-first architecture and first milestone on 2026-09-17; Terminal #598 comment
  5720001976. Do not request that approval again.'
- 'D0 implementation exists on Terminal #601 at 773b16f8e825ab4b39ce3c7a5fa5caf32868d55f; do not create a replacement
  branch or rebuild the qualifier.'
- Do not retry the predecessor blocked live INTC API inspection through another tool or transport. Static non-INTC
  archival qualification is a separate completed operation.
- 'Session-chain qualification already exists at Terminal c0f36cb16fadd190ad747fc47a28405d9ec0fca4: 65 focused
  passes; exact original input hashes reused. Do not refetch/re-census the same archived files or treat nominal-grid
  counts as strategy accuracy.'
- 'Current Chairman correction: Executive is unfinished. Terminal #598 comment 5721925192 supersedes the prior
  user-reconnect prerequisite. Do not repeat Executive authentication probes or ask for design approval.'
- 'R1-A registration, implementation and corrected-history result are already on Macro #7270. Do not rerun
  the unchanged 84-cell grid or relax its thresholds after seeing outcomes; consume TTI_R1A_REPORT.md and DEC:TERMINAL-TACTICAL-R1A-DISPOSITION.'
- 'A bounded minute ambiguity resolver already exists on Macro #7275. Do not build another minute resolver,
  minute store or fetch plane; qualify and consume the existing Radar-owned seam if the PR is accepted.'
- MinuteBar.knowable_at is a mathematical bar-close clock, not source arrival. Never promote current VendorMinuteReader
  history to as-observed evidence without an actual archived availability receipt; see DEC:TERMINAL-TACTICAL-MINUTE-EVIDENCE-CLASS.
- 'R1-B v4 synthetic constructor, 40-case causal test expansion and synthetic explanation consumer are already
  on #7274 at f6738dffff1516216b552d426f956f8f6551248d. Consume their evidence; do not rewrite them, modify
  frozen v4 thresholds or claim synthetic counts as trading accuracy.'
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
- https://github.com/mastermindx-market-intelligence/macro/blob/51bb68b2cf9680f9abf4546a602172a5e157a7e3/research/species/TTI_R1B_V4_REPORT.md
- https://github.com/mastermindx-market-intelligence/macro/blob/51bb68b2cf9680f9abf4546a602172a5e157a7e3/research/species/tti_r1b/RESULT_V4.json
- https://github.com/mastermindx-market-intelligence/macro/blob/51bb68b2cf9680f9abf4546a602172a5e157a7e3/research/species/tti_r1b/RUN_RECEIPT_V4.json
next_action: '2026-11-06: Qualify this sixteen-record carrier; consume the existing spent R1-B result on Macro7274
  under its independent scientific and source-release holds; advance Macro7275 source review and natural current-RTH
  proof. Terminal601/595 and Macro7270 are already merged. Preserve the original Radar-to-Terminal browser
  and prospective product journey. No repeated registration, outcome run, D0 census, Executive reconnection
  or new results carrier.'
---

# Continuity qualification — 2026-11-06

This current frontmatter supersedes obsolete continuation instructions in the dated record below. Terminal #601 and #595 and Macro #7270 are actually merged. Macro #7274 already contains a registered v4 result and its study identity is spent; do not re-register or rerun it. Independent result adjudication, #7274/#7275 source release, current data freshness, Radar/Terminal integration and the original product acceptance remain separate and unfinished.

Authority and exact source evidence: https://github.com/mastermindx-market-intelligence/macro/pull/7262#issuecomment-6678637967; Mastermind#2028, root macro-backlog-oldest-first-20261105-c3. The twelve dated decision/discovery records retain their original bytes. This task changes no scientific rule, empirical result, TrialLedger, source denial, runtime or product surface. The original complete frontmatter and Markdown body are preserved verbatim.

# Historical original body — September 2026

This record coordinates the approved Terminal product integration. Existing tactical and scientific owners remain controlling; no live execution is inferred from this authored record.


## 2026-09-17 direct-execution continuation
The Chairman correction removes the mistaken Executive-reconnect dependency. Independent source review advanced the current-history repair, and the first price-pattern/turn study now has a precise proposed measurement contract. New empirical implementation remains blocked by actual platform refusals, not by a need for further Chairman approval. The unfinished product retains its existing data/event/scientific owners.

# Archived original frontmatter — September 2026

The complete original metadata is retained as dated evidence. Current next actions are in the qualified frontmatter above.

```yaml
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
- DEC:TERMINAL-TACTICAL-SYNTHETIC-CONSTRUCTION-CONTINUE
- DEC:TERMINAL-TACTICAL-R1B-STACKED-RESEARCH-ADMISSION
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
  status: done
  next_action: 'DONE: immutable D0 head c0f36cb16fadd190ad747fc47a28405d9ec0fca4 received independent APPROVED review from mastermindx-3 after a fresh 59-case focused run and all hosted source/security/e2e checks were green; stale PR metadata claiming 65 focused tests was corrected. Terminal #601 squash-merged as f4bc91827a075748dc5c97c889888ae2ee643a87. Preserve its corrected-history/as-observed distinction and do not rebuild the qualifier.'
- id: D1
  title: Current pilot history and finer-grain availability qualification
  status: in_progress
  next_action: 'Macro #7275 is BUILT_NOT_PROVEN at bf047bbf259d8f579ad8254f1ab3de80c5204299 on the existing Radar-owned minute seam. The in-memory arrival receipt is now bound to the exact ordered raw response through response_content_sha256: key-order invariant but sensitive to values/order/duplicates, including vendor vw/n and unparsed rows; unsupported JSON evidence yields null rather than invented identity. Exact pre-commit proof: complete C3/receipt/resolver suite 90 passed; full Radar W1-W6 regression 1522 passed/2 skipped; no current-main overlap on the changed reader/test paths. Historical known-at remains unproven and natural current-RTH health proof is still owed. Terminal #595 same carrier is repaired at 7b98ad64ac0de95522e7e9eb99747ea350ecf653: failed transport/partial pagination now fail closed and preserve old store bytes; focused refresh/nightly verification 47 passed. Hosted CI and fresh independent reviews remain gates; #601 also still awaits independent review.'
- id: R1
  title: Registered price-first hypotheses, causal evaluation and controls
  status: in_progress
  depends_on:
  - D0
  next_action: 'R1-A head b73f1c7bf13aa386fb11c4fdce762b999e91eae7 is independently APPROVED after custody checks, 265-pass causal/TrialLedger review, a preserved-input rerun with byte-identical feature/outcome rows, and conflict-free current-base TrialLedger integration. Its protected-main merge remains held by required ci-gate because lane-external HK/Canada stock-dashboard receipt hashes are red. D0 is merged. DEC:TERMINAL-TACTICAL-R1B-STACKED-RESEARCH-ADMISSION permits R1-B research to stack on accepted R1-A without bypassing release: merge accepted R1-A into #7274 research branch, append all 60 frozen v4 cells before any R1-B market outcome, then execute corrected-history research under no-promotion law. Current #7274 head 3222dd1a6f199a561d03707bc6e279563af86220 additionally derives ATR20/beta from prior-only daily inputs; full Radar regression 1537 passed/2 skipped.'
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
- "R1-B v4 synthetic constructor, 40-case causal test expansion and synthetic explanation consumer are already on #7274 at f6738dffff1516216b552d426f956f8f6551248d. Consume their evidence; do not rewrite them, modify frozen v4 thresholds or claim synthetic counts as trading accuracy."
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
next_action: "Review #7274 construction head f6738dffff1516216b552d426f956f8f6551248d and reconcile #7270 shared-source/review gates. Once lawful, append the unchanged v4 60-cell budget to the existing TrialLedger before market-outcome execution, then build the empirical qualified-input/outcome/matching consumer. Synthetic constructor and replay explanation are already built; no matching estimates, return/LOD labels or probabilities are yet computed. #7275 arrival receipt/health projection is already built and still owes natural live-source proof. #595 retains refresh custody, #601 release review remains separate. No new approval, Executive reconnection, repeated census or duplicate detector/store."
---
```
