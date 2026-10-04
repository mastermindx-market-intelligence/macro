---
key: FUTURES-MARKET-TAPE-PLANE
title: Futures Market Tape Plane
objective: >
  Establish one governed Data OS futures-tape substrate for deep historical and
  forward-accruing futures research, beginning with ES. Keep source identity,
  exchange-contract identity, vendor-continuous identity, roll semantics, storage,
  lineage and quality explicit. Deliver raw immutable partitions, normalized ticks,
  deterministic derived bars, source qualification, capacity fencing and health
  receipts without creating a second scheduler, event ledger, evaluator, identity
  system or trading authority.
status: active
program: market-timing-intelligence
repos: [macro]
owner: ceo-sol
class: build
blast_radius: reversible
ambiguity: scoped
owns_paths:
  - lib/dataos/futures_tape.py
  - scripts/futures_tape_ingest.py
  - scripts/probe_massive_futures.py
  - tests/test_futures_tape_ingest.py
  - tests/test_probe_massive_futures.py
  - .github/workflows/futures-tape-probe.yml
  - research/futures_tape/
  - agentos/workstreams/WS-FUTURES-MARKET-TAPE-PLANE.md
  - agentos/decisions/DEC-FUTURES-TAPE-
  - agentos/handoffs/FUTURES-MARKET-TAPE-
decisions:
  - DEC:FUTURES-TAPE-OWNERSHIP-AND-SOURCE-ROLES
waves:
  - id: F0
    title: Ownership, source qualification, storage contract and resumable ES pilot
    status: in_progress
    next_action: >
      Merge the F0 implementation carrier, then run the source-bearing Phase-0 probe
      on an ops host with LSE_API_KEY and the existing Massive credential. Record the
      exact ES.F catalog row/history span, Massive Futures entitlement result and
      external-SSD capacity receipt before a bulk export.
  - id: F1
    title: LSE ES deep-history backfill, audit and normalized daily partitions
    status: todo
    depends_on: [F0]
    next_action: >
      Start only after F0 source/rights/identity receipts pass. Backfill in bounded
      windows with the existing ingest CLI, audit every immutable partition, and keep
      LSE_ES.F classified vendor_continuous/secondary_research.
  - id: F2
    title: Exact CME contract plane and Mastermind continuous ES
    status: todo
    depends_on: [F0]
    next_action: >
      If the current enterprise Massive relationship is Futures-entitled, ingest exact
      CME ES contracts and build explicit volume/OI/calendar-roll continuous variants.
      If not entitled, leave F2 gated rather than substituting vendor-continuous data.
  - id: F3
    title: Derived bars, event windows and futures_context_v1
    status: todo
    depends_on: [F1]
  - id: F4
    title: Consumer qualification
    status: todo
    depends_on: [F3]
    next_action: >
      Qualify Macro/Event Intelligence first, Temporal Grain second, Prophet/Entry Radar
      context-only afterward. No raw tape becomes rank/gate/size/trade authority.
  - id: F5
    title: Perpetual accrual, finalization and backup
    status: todo
    depends_on: [F1]
    next_action: >
      Bind the producer to the existing persistent host/scheduler and existing data
      health owner. Provisional live observations reconcile to post-session/final
      history; compact derived artifacts may publish remotely, raw tape stays private.
landmines:
  - "LSE ES.F is a vendor-continuous identity until roll/adjustment semantics are proven."
  - "A trade tape is not an order book. OFI/liquidity-withdrawal claims require quote events."
  - "Do not infer a Massive Futures entitlement from the existing Stocks enterprise license."
  - "Do not expose or redistribute LSE raw data; current public terms permit internal research/model use, not a competing feed."
  - "Do not bulk-download all CME quote history. Filter exact required contracts/windows."
  - "Raw licensed/vendor data stays outside Git."
  - "A display websocket is not historical research truth and is not a storage owner."
do_not_redo:
  - "Do not create a Futures OS, second Data OS, second market identity system, second scheduler, second health plane or second outcome ledger."
  - "Do not replace ThetaData as canonical options data; futures is a separate plane."
  - "Do not treat Yahoo TapeHub display ticks as canonical historical futures data."
  - "Do not call LSE_ES.F an exchange contract."
  - "Do not buy new storage or a new futures plan before measured capacity/entitlement receipts."
next_action: >
  Consume exact-head CI and independent review for PR #8451, then merge if all release
  gates pass. Consume the path-triggered read-only futures-tape-probe run that starts when this
  implementation lands on protected main; it measures external-volume capacity and the
  existing Massive Futures entitlement. LSE remains an honest skip until LSE_API_KEY is
  configured out of band.
  Bulk backfill remains held until those exact source/rights/identity receipts exist.
---

# WS:FUTURES-MARKET-TAPE-PLANE

Capability at birth is BUILT_NOT_PROVEN for the producer code and SPEC_ONLY for
source-bearing acquisition. No LSE key or Massive Futures entitlement has been
observed by this carrier, no bulk tape has been downloaded, and no consumer authority
has changed.

The plane is a Data OS substrate. Market Ontology / existing futures identity owners
retain contract, venue, session, timezone and roll truth. Macro/Event Intelligence,
Temporal Grain, Prophet, Entry Radar and Market Microstructure are consumers. TrialLedger
/ Evaluation OS retain outcome authority. Executive OS remains runtime/admission owner.
