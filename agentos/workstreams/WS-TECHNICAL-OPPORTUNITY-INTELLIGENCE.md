---
key: TECHNICAL-OPPORTUNITY-INTELLIGENCE
title: Technical Opportunity Intelligence — multi-timeframe setup, trigger, path, and remaining-opportunity system
objective: >
  Build one causal technical perception layer for U.S. equities that surfaces both
  Forming/Armed opportunities before a move and Triggered/Confirmed opportunities after
  evidence arrives, with explicit trigger, invalidation, confirmation cost, chase,
  contradiction, and remaining-opportunity semantics. Done for the first vertical when
  Compression Release is proven on completed Weekly/Daily/4H inputs, produces real
  two-queue occurrences in production, renders in the product and Terminal, accrues
  prospective evidence, and receives a Sol species-by-species authority ruling.
status: active
program: market-timing-intelligence
repos: [macro, terminal]
owner: ceo-sol
class: research
blast_radius: reversible
ambiguity: scoped
owns_paths:
  - research/TECHNICAL_OPPORTUNITY_INTELLIGENCE_
  - research/technical_opportunity/
  - scripts/research/validate_toi_
  - scripts/research/run_toi_
  - tests/test_toi_
  - agentos/workstreams/WS-TECHNICAL-OPPORTUNITY-INTELLIGENCE.md
  - agentos/decisions/DEC-TECHNICAL-OPPORTUNITY-INTELLIGENCE-
  - agentos/discoveries/DSC-TECHNICAL-CONFLUENCE-V1-EXCLUDES-TECH-LAB-FAMILIES.md
  - agentos/discoveries/DSC-TECHNICAL-4H-RESEARCH-PANEL-NOT-PROVEN.md
  - agentos/discoveries/DSC-TOI-
  - agentos/handoffs/TECHNICAL-OPPORTUNITY-INTELLIGENCE-
decisions:
  - DEC:TECHNICAL-OPPORTUNITY-INTELLIGENCE-CANONICAL-OWNERSHIP-AND-TWO-QUEUE-LAW
discoveries:
  - DSC:TECHNICAL-CONFLUENCE-V1-EXCLUDES-TECH-LAB-FAMILIES
  - DSC:TECHNICAL-4H-RESEARCH-PANEL-NOT-PROVEN
waves:
  - id: W0
    title: Architecture freeze, evidence contract, data/clock contract, and durable records
    status: done
    pr: 6570
    next_action: >
      DONE — PR #6570 merged 2026-08-30 as
      6e3126c5106d5d240961088a866bf0e45f940538. W0 is durable records-only
      `SPEC_ONLY`; it created no research result, runtime, data panel, signal, product or
      production authority.
  - id: W1
    title: Public-method and local-estate Technical Evidence Census
    status: in_progress
    pr: 7107
    depends_on: [W0]
    next_action: >
      PR #7107 is the one active W1 carrier under operation key
      TOI-W1-EVIDENCE-CENSUS-V1. Its method census remains `PARTIAL`; the prior
      `toi.inside_bar` source-quality item is closed, while the independent frozen
      20-passport reproduction review, any evidence-driven repairs, exact return-head
      validation/current-base proof, and Sol acceptance remain open. Live placement,
      pickup, and execution state must be read from their canonical carriers rather
      than inferred from this organizational projection.
  - id: W2-0
    title: Daily/Weekly/4H data, clock, correction, coverage, rights, and Terminal-parity archaeology
    status: awaiting_ci
    pr: 7094
    depends_on: [W0]
    next_action: >
      PR #7094 is the exact W2-0 carrier. Its scientific verdict remains
      `PARTIAL / HOLD`: current Massive daily depth and rights are real, but production
      Terminal early-close 4H parity failed 5/5 measured cases; whole-universe 4H can
      fall back to provider-built 1h bars; a same-basis historical Daily+4H
      known-at/correction contract and broad historical denominator remain unproven.
      The records release head must preserve the current W1 projection, settle exact-head
      checks, and pass current-base Sol review. Only after acceptance and merge may the
      bounded W2 existing-owner repair/qualification start. W3 remains held.
  - id: W2
    title: Bounded existing-owner data substrate extension, only if W2-0 authorizes it
    status: todo
    depends_on: [W2-0]
    next_action: >
      HELD pending W2-0 acceptance. If PR #7094 is accepted, first make actual exchange
      close load-bearing in Terminal/research 4H semantics and re-prove at least 20
      production parity cases including early closes. Then qualify one same-basis Daily+4H
      source family and broad historical eligible-universe denominator. Do not read outcomes.
  - id: W3
    title: Compression Release upside/downside preregistration and phase-zero family tournament
    status: todo
    depends_on: [W1, W2-0]
  - id: W4
    title: Current per-security occurrence engine and two-queue snapshot
    status: todo
    depends_on: [W3]
  - id: W5
    title: Technical Opportunity Radar, security detail, and Terminal vertical
    status: todo
    depends_on: [W4]
  - id: W6
    title: Production shadow accrual and real-path proof
    status: todo
    depends_on: [W5]
  - id: W7
    title: Sol species-by-species kill, version, accrue, display, or bounded-consumer adjudication
    status: todo
    depends_on: [W6]
  - id: W8
    title: Bottom/top reversal vertical using Durable Bottom and Setup Species law
    status: todo
    depends_on: [W7]
landmines:
  - "Live Entry Radar owns tactical 5-minute entry events; this program must not create another radar, WebSocket plane, entry-event store, or tactical evaluator."
  - "Setup Species is the canonical scientific registry; a new technical-species registry is a duplicate control plane."
  - "The current confluence miner is a Combo-v1 benchmark, not the complete technical estate and not an entry-timing authority."
  - "The U.S. 390-minute regular session does not divide evenly into four-hour bars; research and Terminal clocks must be measured and versioned."
  - "Entitlement or a successful API call is not proof of historical point-in-time availability, corrections, rights, or universe coverage."
  - "Downside breakdown research starts with zero directional-short authority."
  - "Weekly/Daily/4H is the first proving slice, not the final horizon estate; future cold starts must preserve Monthly structural context, Radar-owned true intraday context, and point-in-time sector/theme/basket expansion."
  - "A branch, PR, queue, transport delivery, or worker ACK is not evidence of live execution; W1 and W2-0 use one carrier each, typed returns, and reciprocal continuation watching under the current procedure amendment."
  - "WS:TEMPORAL-GRAIN-INTELLIGENCE is a sibling exact-chart G/A/K/D and filter-memory study; it neither completes nor replaces this program's W1 or W2-0."
do_not_redo:
  - "Do not build a universal technical score or average Forming/Armed with Triggered/Confirmed."
  - "Do not redo per-name in-sample outcome audition (DNR:KILL-OUTCOME-AUDITION)."
  - "Do not repackage killed PSS standalone timers or hard gates under new names."
  - "Do not merge the setup population into Prophet's graded board (DNR:KILL-PROPHET-POP-MERGE)."
  - "Do not let an LLM originate a signal, rank, gate, size, numeric confidence, or trade."
  - "Do not begin Compression Release outcome testing until W1 and W2-0 are both accepted."
  - "Do not treat Temporal Grain chart parity or artifact diagnostics as the TOI data-plane admission gate."
artifacts:
  - research/TECHNICAL_OPPORTUNITY_INTELLIGENCE_ARCHITECTURE_FREEZE_2026-08-27.md
  - research/TECHNICAL_OPPORTUNITY_INTELLIGENCE_W0_PROCEDURE_AND_CONTINUATION_AMENDMENT_2026-08-27.md
  - research/TECHNICAL_OPPORTUNITY_INTELLIGENCE_W1_EVIDENCE_CENSUS_HANDOFF_2026-08-27.md
  - research/TECHNICAL_OPPORTUNITY_INTELLIGENCE_W2_DATA_CLOCK_HANDOFF_2026-08-27.md
  - research/technical_opportunity/W2_DATA_PLANE_CENSUS.md
  - research/technical_opportunity/W2_DATA_CLOCK_ARCHITECTURE_FREEZE.md
  - research/technical_opportunity/W2_REPORT.md
  - agentos/handoffs/TECHNICAL-OPPORTUNITY-INTELLIGENCE-2026-08-27.md
  - agentos/handoffs/TECHNICAL-OPPORTUNITY-INTELLIGENCE-2026-08-27-w0-current-procedure.md
  - agentos/handoffs/TECHNICAL-OPPORTUNITY-INTELLIGENCE-2026-08-28-w0-finalization.md
  - agentos/handoffs/TECHNICAL-OPPORTUNITY-INTELLIGENCE-W2-0-2026-09-12.md
next_action: >
  W1 is active and `PARTIAL` on draft PR #7107; its independent review, exact validation,
  current-base proof, and Sol acceptance remain open. W2-0 is on draft PR #7094 with a
  `PARTIAL / HOLD` data-plane verdict and must settle this current-state correction,
  exact-head CI, and current-base Sol release review. W3 and all outcome testing remain
  blocked. If W2-0 is accepted and merged, execute one bounded W2 existing-owner
  repair/qualification wave: actual-close Terminal/research 4H parity first, then one
  same-basis Daily+4H source family plus the broad historical denominator. Neither
  carrier nor this projection creates runtime, signal, product, or trading authority.
---

## Boundary note

This workstream is the broad technical-perception program under
`market-timing-intelligence`. It does not subsume `WS:LIVE-ENTRY-RADAR`,
`WS:STOCK-IDENTITY`, `WS:PROPHET-US-ENTRY-TIMING`, or
`WS:TEMPORAL-GRAIN-INTELLIGENCE`; it consumes or hands off through their declared
boundaries.

`WS:TEMPORAL-GRAIN-INTELLIGENCE` owns exact motivating-chart identity/parity,
bar-grain versus anchor versus filter-memory versus data-plane causal separation, and a
possible later structure-to-kernel law. This workstream's W2-0 retains broad
U.S.-equity data/clock/correction/coverage/rights and Terminal-parity admission. One
cannot be used to mark the other complete.

## Horizon end-state

Weekly/Daily/4H is the first proving vertical, not a permanent ceiling. The complete
program must later incorporate Monthly structural/regime context, true intraday
context through Live Entry Radar's existing event and market-data owners, and
point-in-time sector, industry, theme, and basket opportunity objects. Those later
horizons reuse the same species and occurrence law; they do not authorize a second
intraday plane or a wider first PR.
