# SNI-1 Identity Authority Amendment — Data OS Master + PIT Bridge

**Date:** 2026-08-28  
**Status:** binding amendment to `2026-08-28-sni1-reference-twin-design.md` for identity ownership and SNI-1A planning  
**Parent carrier:** `sol/sni1-reference-twin-20260828` / PR #6613  
**Chairman status:** SNI-1 direction approved; this amendment reconciles fresher canonical identity law discovered before implementation  
**Authority:** architecture only; no runtime, owner mutation, identity mint, source purchase, forecast, signal, rank, gate, size or trade authority

---

## Observation boundary

This amendment's source and coverage observations are dated 2026-08-28. Its 2026-11-05 fold into the parent design, matrix, ontology and specimen preserves the authority rule without refreshing coverage, rights, market facts or installed capability. Resolve current owner evidence at execution; no illustrative specimen here binds an admitted identity row/receipt.

## 1. Why this amendment exists

SNI-1 was initially written against the older Company Intelligence identity vocabulary. Before SNI-1A code began, the 2026-08-28 source inspection found an accepted estate-wide identity contract:

- `config/identity_seams.yml` declares `lib/dataos/identity.py` plus `data/reference/security_master.parquet`, `vendor_aliases.parquet`, `issuer_master.parquet` and migration receipts as the canonical Data OS issuer/security/listing identity authority.
- `contracts/evidence_foundation/README.md` requires `ISS:` / `SEC:` / listing identities to come from that produced Data OS master and separately names Earnings `company_identity.v1` as the lawful PIT CIK↔listing/security bridge where that bridge is supported.
- The V4-D2B2-CN-HK receipt sampled on 2026-08-28 reported 147/147 targeted HK listings resolved. That admission deliberately left CN/HK `issuer_id` null / `NO_ISSUER_EVIDENCE` and added no CN/HK issuer-evidence class. This bounded, dated receipt does not prove today's coverage or admission of each illustrative counter, and does not establish a continuing estate-wide absence of issuer evidence.
- `DEC:MARKET-OS-B1A-IDENTITY-GATE-OWNER-BACKED-CHAIN` separately records that no general namespace renderer exists between every owner-native identity grammar and Data OS, and that a narrow owner-backed chain must refuse rather than invent a bridge.

Therefore any SNI text that calls `company_identity.v1` the universal canonical issuer/security/listing owner is superseded by this amendment.

---

## 2. Frozen authority chain

SNI uses the following precedence:

```text
Data OS identity master
  canonical issuer/security/listing identity when admitted
        ↓
owner-native PIT bridge / company_identity.v1
  lawful CIK/listing/event attribution at its supported clock and grammar
        ↓
SNI relationship record
  source-receipted economic-security / counter / conversion relationship
        ↓
Reference Twin projection
  composition only; never an identity allocator
```

### 2.1 Data OS owns

- canonical `ISS:<...>` issuer IDs where the master has resolved issuer evidence;
- canonical `SEC:<...>` security IDs;
- canonical bare listing IDs;
- security/listing alias and correction semantics represented by the master and migration receipts;
- the estate rule that symbols are aliases, not durable identities.

### 2.2 `company_identity.v1` / owner-native identity owns

- its own point-in-time alias windows and issuer/event attribution;
- CIK-native company-event identity where supported;
- a lawful bridge or corroboration leg only at the precision its accepted contract provides.

It does **not** become a second estate-wide `ISS:/SEC:/listing` authority.

### 2.3 SNI owns only relationship projection

SNI may represent source-proven relationships that the current canonical identity master does not natively encode, including:

- multiple trading counters representing the same economic ordinary-share security;
- an ADS representing a fixed number of ordinary shares;
- a selected counter being one market representation of an issuer-linked security;
- the evidence, effective clock, correction state and confidence/coverage of those relationships.

SNI may not allocate or persist a new canonical issuer, security or listing ID.

---

## 3. Revised SNI-1A object model

The phrase `issuer → economic security → venue listing → trading counter` remains a useful **conceptual product model**, but its IDs are not all SNI-owned.

### 3.1 `issuer_subject`

```text
canonical_issuer_id: Data OS ISS id | null
issuer_resolution_state
owner_native_issuer_refs[]
external_entity_ids[]
legal_name_evidence_refs[]
```

For a current HK name where Data OS has admitted the listing/security but has no accepted issuer evidence, `canonical_issuer_id` remains null. A CIK, issuer name, HKEX stock code or SNI relationship is not allowed to silently fill it.

### 3.2 `counter_subject`

```text
mic
observed_code
trading_currency
canonical_listing_id: Data OS listing id | null
canonical_security_id: Data OS SEC id | null
identity_resolution_state
owner_native_refs[]
source_evidence_refs[]
```

A source-proven counter that has not been admitted into Data OS may still appear as an **observed counter descriptor**, but its canonical identity fields stay null with a typed reason. `lib.dataos.identity.normalize_hk_symbol()` is an allocator/normalizer; deriving the string is not proof that the stored master has admitted the identity.

### 3.3 `economic_security_relationship`

This is a relationship record, **not a canonical security ID**:

```text
relationship_id
relationship_type: same_economic_security | represents_units_of
members[]
unit_relationship
valid_from
valid_to
evidence_refs[]
correction_state
authority: descriptive
```

`relationship_id` identifies the SNI relationship record only. It must be deterministic from canonical JSON of the relationship content and must never use the `ISS:` or `SEC:` namespaces.

Reference relationships:

- Alibaba 9988 HKD counter ↔ 89988 RMB counter: `same_economic_security`, only when official issuer/HKEX evidence supports the counter relationship.
- Tencent 700 HKD counter ↔ 80700 RMB counter: `same_economic_security`, under the same evidence law.
- BABA ADS → Alibaba ordinary shares: `represents_units_of`, `1 ADS = 8 ordinary shares`, with the official issuer receipt.

---

## 4. HK identity state observed 2026-08-28 and product consequence

The Data OS receipt inspected on 2026-08-28 reported admission of its targeted HK listing population at listing/security grain: `resolved_total.hk = 147`, `target_n.hk = 147`, with SFC/HKEX evidence in that receipt. An aggregate population count does not bind a particular example counter to an admitted row.

It is **not** sufficient to claim canonical HK issuer resolution. The sampled accepted D2B2 handoff says those CN/HK rows entered with `issuer_id=None / issuer_state=NO_ISSUER_EVIDENCE`, and that admission added no CN/HK issuer-evidence class. A later owner receipt may change coverage; SNI must verify that actual receipt rather than infer either resolution or permanent absence.

When exact listing/security admission is independently bound but canonical issuer evidence remains unresolved, the first Alibaba/Tencent twin must be able to render a state such as:

```text
listing/security: canonical Data OS identity available
issuer external identity: source-backed owner-native evidence available
Data OS canonical issuer: unresolved
SNI counter relationship: source-backed descriptive relationship available
```

That is an honest identity rendering when its stated owner evidence is bound; it does not complete the overall product. The unbound illustrative JSON fixture retains null listing, security and issuer IDs instead. Neither case authorizes another issuer registry.

---

## 5. No-general-renderer law

SNI-1A must not solve the estate-wide namespace bridge problem incidentally.

If a relationship member cannot be connected to a stored Data OS listing/security through an accepted owner-native reference or exact owner-backed chain:

- `identity_resolution_state = unresolved`;
- canonical ID fields remain null;
- the relationship may retain the official observed counter descriptor when source-proven;
- SNI refuses any operation that requires the missing canonical ID.

A future general ListingAlias→DataOS ListingKey renderer is an identity-owner program, not an SNI helper function.

---

## 6. SNI-1A revised acceptance cases

The pure contract/validator must prove at least:

1. 9988/89988 can be represented as two source-proven counters in one `same_economic_security` relationship without minting a second issuer or pretending both counters already have stored Data OS IDs.
2. 700/80700 obey the same law.
3. BABA is a distinct ADS member with `1 ADS = 8 ordinary shares`; it is never collapsed into an ordinary-share counter.
4. A Data OS canonical listing/security ID must be owner-supplied/admitted; deriving a syntactically valid ID does not establish authority.
5. A null Data OS HK issuer ID remains null even when CIK/legal-name evidence exists elsewhere.
6. Conflicting canonical IDs for one relationship member are rejected.
7. A relationship with no source/effective clock is rejected.
8. Ambiguous issuer attribution is rejected or typed unresolved; no best-effort ticker guess exists.
9. SNI relationship IDs cannot use `ISS:` / `SEC:` / bare Data OS listing namespaces.
10. All authority remains descriptive/all-false for rank, gate, size, signal, escalation and trade.

Stale FX / asynchronous price comparison remains a hostile test of the broader reference-twin contract, but SNI-1A does not perform price conversion. It may freeze the identity/counter prerequisites required by the later SNI-1C comparison guard without adding price math to this PR.

---

## 7. Superseded wording in the parent SNI-1 packet

Where the parent spec, owner/source matrix, reference specimen or discovery says or implies:

- `company_identity.v1` is the universal canonical identity owner;
- SNI may generate a canonical `counter_id` merely from MIC+ticker;
- every reference counter already has a canonical stored security/listing ID;

read instead:

> Data OS owns canonical issuer/security/listing identities when admitted; owner-native/PIT bridges preserve their own identity and clock semantics; SNI owns only source-receipted relationship records and typed unresolved states.

This amendment remains the identity interpretation for SNI-1A and later plans. The 2026-11-05 repair folds that interpretation into the parent design, owner/source matrix, ontology and illustrative JSON fixture. Descriptive label fields do not allocate canonical IDs; only actual admitted rows and exact owner receipts can populate the nullable canonical fields.

---

## 8. Evidence

- `config/identity_seams.yml` — Data OS identity master and CN/HK admission semantics inspected on 2026-08-28.
- `lib/dataos/identity.py` — canonical ID allocator/reader vocabulary; explicitly states mint-once-and-store authority.
- `data/reference/_receipt.json` — generated identity receipt inspected on 2026-08-28, including the bounded 147/147 HK target listing observation.
- `agentos/handoffs/PROPHET-US-V4-RECOVERY-2026-08-20-D2B2.md` — accepted CN/HK admission implementation and explicit no-HK-issuer-evidence boundary.
- `contracts/evidence_foundation/README.md` — cross-owner identity reuse and PIT bridge law.
- `agentos/decisions/DEC-MARKET-OS-B1A-IDENTITY-GATE-OWNER-BACKED-CHAIN.md` — no-general-renderer boundary and owner-backed-chain precedent.

---

## 9. Exact next action

First qualify the current published PR #6613 head and verify its actual protected-main acceptance. Then the assigned receiver resolves the semantic registry decision using current `config/mastermind_programs.yml`, derives actual registry facts, and reconciles the existing stacked #6615 carrier before registration/workstream creation or a separately admitted SNI-1A **pure relationship contract** start. Preserve actual live writers and uncertain effects; old named seats or PRECOMMISSION packets do not establish current approval, START or release. No owner reads, Data OS mutation, issuer repair, reference-twin compiler, product route or forecast belongs in SNI-1A.
