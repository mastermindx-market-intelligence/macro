---
key: SNI-IDENTITY-AUTHORITY-CHAIN
question: >
  For Single-Name Intelligence, which system owns canonical issuer/security/listing
  identity, which owner supplies PIT issuer/listing/event bridging, and what identity-like
  relationship may SNI itself represent without creating a second identity authority?
answer: >
  Data OS is the canonical estate-wide issuer/security/listing identity authority when an
  identity is admitted into its stored master. Owner-native identity, including Earnings
  company_identity.v1, supplies its own PIT alias/event bridge at its supported precision.
  SNI may create only source-receipted descriptive relationship records such as
  same_economic_security and represents_units_of; it may not mint canonical ISS:/SEC:/listing IDs.
rationale: >
  The identity authority inspected on 2026-08-28 declares lib/dataos/identity.py and the
  stored security/issuer/listing master as the canonical identity spine; Evidence
  Foundation binds cross-owner identities to that master. The sampled D2B2 receipt
  reported 147/147 targeted HK listings/security identities admitted, with HK issuer IDs
  unresolved and no HK issuer-evidence class added in that admission. This is a dated,
  bounded observation, not proof of today's issuer coverage or of admission for every
  illustrative counter. Exact stored rows and owner receipts remain necessary.
  Treating company_identity.v1 as the universal identity master would contradict that
  authority chain; letting SNI fill an unproven issuer gap would create the duplicate
  identity plane the program is explicitly forbidden to build. The economic-security/counter distinction is
  still necessary, but it belongs as an evidence-backed relationship projection until the
  canonical identity owner chooses to absorb that concept.
alternatives:
  - option: Make company_identity.v1 the canonical identity owner for SNI
    why_not: >
      It has useful PIT alias/event semantics but does not own the estate-wide Data OS
      ISS:/SEC:/listing master and would contradict current identity_seams and cross-owner
      Evidence Foundation law.
  - option: Let SNI mint missing HK issuer/security/listing IDs from official ticker/CIK evidence
    why_not: >
      That creates a second identity allocator and silently bypasses Data OS's explicit
      NO_ISSUER_EVIDENCE state for HK. A plausible ID string is not proof the canonical
      master admitted it.
  - option: Block all economic-security/counter representation until Data OS natively models it
    why_not: >
      Alibaba/Tencent multi-currency counters and BABA's ADS conversion are source-proven
      relationships needed by the user job now. A descriptive relation record can express
      them without claiming canonical identity authority.
evidence:
  - "config/identity_seams.yml — master.reader=lib/dataos/identity.py; canonical security/issuer/listing artifacts and id conventions"
  - "data/reference/_receipt.json — 2026-08-28 sampled china_hk_admission resolved_total.hk=147 / target_n.hk=147; population receipt, not an example-specific issuer/counter binding"
  - "agentos/handoffs/PROPHET-US-V4-RECOVERY-2026-08-20-D2B2.md — HK admission and explicit issuer_id=None / NO_ISSUER_EVIDENCE boundary"
  - "contracts/evidence_foundation/README.md — ISS:/SEC:/listing identity comes from Data OS master; company_identity.v1 is a PIT bridge"
  - "agentos/decisions/DEC-MARKET-OS-B1A-IDENTITY-GATE-OWNER-BACKED-CHAIN.md — no-general-namespace-renderer and owner-backed-chain precedent"
affects:
  - single-name-intelligence
  - docs/superpowers/specs/2026-08-28-sni1-reference-twin-design.md
  - docs/superpowers/specs/2026-08-28-sni1-identity-authority-amendment.md
  - research/single_name_intelligence/**
confidence: high
reversibility: costly
decided_by: ceo-sol
decided_at: 2026-08-28
---

## Observation and current execution boundary

The decision date and sampled source evidence remain 2026-08-28. The 2026-11-05
amendment fold does not refresh coverage, rights, installed capability or production
acceptance. Later owner evidence may supersede the sampled coverage without changing
the rule that SNI cannot mint canonical identity. The current published PR #6613 head
requires its actual source, CI and eligible nonauthor release qualification; the old
expected-head landing instruction is not reused.

## Operating consequence

SNI-1A is a relationship-contract wave, not an identity-master wave. An unresolved canonical
issuer/listing/security identity remains unresolved. Later SNI owner adapters must use current
Data OS receipts and owner-native PIT bridges rather than deriving a canonical ID from a ticker.

## What would supersede this decision

A later accepted Data OS identity contract may natively absorb economic-security / trading-counter
relationships or add a general owner-routed PIT namespace bridge. If that happens, SNI must consume
the new canonical owner and retire the overlapping relationship projection rather than maintain a
parallel authority.
