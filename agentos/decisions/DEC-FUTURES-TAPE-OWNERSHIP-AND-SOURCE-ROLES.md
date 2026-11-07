---
key: FUTURES-TAPE-OWNERSHIP-AND-SOURCE-ROLES
question: >
  Which existing Mastermind owner should own a historical/live futures tape substrate,
  how should LSE, Massive Futures and ThetaData be separated, where should the bytes live,
  and what authority may the plane have?
answer: >
  The existing Mastermind Data OS / Macro market-data plane owns physical acquisition,
  immutable source partitions, normalized futures ticks, lineage, quality and dataset
  contracts. Existing market ontology/instrument owners retain exchange/product/contract,
  expiry, session, timezone, tick-size, multiplier and roll truth. LSE is initially
  secondary deep-history vendor-continuous research data; its ES.F symbol is never
  relabeled as a literal CME contract until its roll/adjustment semantics are proven.
  Massive Futures, when an enterprise/business entitlement is actually measured, is the
  preferred modern exact-contract source for CME trades/top-of-book/reference. ThetaData
  remains the canonical options plane and may later contribute recent futures depth if
  its product launches, but it is not a substitute for this plane today. Raw history is
  stored privately on operator-owned local storage selected by MMX_FUTURES_TAPE_ROOT;
  remote object storage receives only deliberately selected backup/derived artifacts.
  The tape plane has zero rank, gate, size, trade, Prophet or Golden Oracle authority at
  birth.
rationale: >
  The estate already contains Data OS identity, temporal, quality and lineage primitives;
  creating a separate Futures OS would duplicate a canonical system. Temporal Grain
  already distinguishes data/instrument plane D from grain/anchor/kernel and therefore
  needs a reusable source substrate rather than owning one. Prophet regime/timeframe
  research similarly consumes market context but does not own data custody. The existing
  Yahoo futures TapeHub is presentation/reference infrastructure and explicitly lacks
  exchange-grade historical provenance. Current internal Massive records describe a
  Stocks product; current public Massive documentation exposes a separate Futures product,
  so futures entitlement must be measured, not inferred. Current ThetaData estate is
  load-bearing for options and should not be displaced.
alternatives:
  - option: Make Prophet or Temporal Grain own the futures archive
    why_not: >
      Both are research/consumer systems. Giving either source custody would duplicate
      Data OS and contaminate experimental ownership with data admission.
  - option: Treat LSE ES.F as canonical exchange ES
    why_not: >
      It is a vendor symbol whose continuous/roll semantics are not yet qualified.
      Continuous vendor history is useful but not interchangeable with a literal CME
      contract.
  - option: Put the raw archive in public/shared R2
    why_not: >
      Raw tape is large, rights-sensitive and unnecessary for browsers. Local hot storage
      plus selective private/offsite backup is cheaper and preserves distribution controls.
  - option: Wait for ThetaData futures
    why_not: >
      The current Mastermind options plane does not provide a deep canonical CME futures
      archive today, and a future launch does not retroactively supply the pre-2017 history
      or our own roll semantics.
  - option: Download all CME quote history
    why_not: >
      Full-market BBO is multi-terabyte scale and not required for the first consumers.
      ES-first targeted quote windows preserve the microstructure option without waste.
evidence:
  - "Data OS already defines futures identities via FUT:<MIC>:<root>:<YYYYMM> in lib/dataos/identity.py."
  - "app/tape.py is a Yahoo websocket presentation relay with fallback semantics, not a historical store."
  - "WS:TEMPORAL-GRAIN-INTELLIGENCE assigns data/instrument truth to existing data/ontology owners."
  - "WS:PROPHET-REGIME-TIMEFRAME-RESEARCH consumes clock/data receipts and owns no market-data plane."
  - "research/licenses/THETADATA_ENTITLEMENT_RECORD.md and the ThetaData store/runbook establish options ownership."
  - "research/MASSIVE_ADVANCED_INTEGRATION_MASTERPLAN_BY_FABLE.md records the incumbent Massive plane as Stocks-focused and futures/indices outside the measured entitlement."
affects:
  - WS:FUTURES-MARKET-TAPE-PLANE
  - WS:TEMPORAL-GRAIN-INTELLIGENCE
  - WS:PROPHET-REGIME-TIMEFRAME-RESEARCH
  - dataos
  - macro-intelligence
confidence: high
reversibility: easy
decided_by: ceo-sol
decided_at: 2026-10-05
---

# Consequence

The first lawful acquisition wave is ES only. New instruments require a named consumer
benefit. Source quality/entitlement and storage-capacity receipts precede any bulk backfill.
A successful download is data availability, not signal authority or production proof.
