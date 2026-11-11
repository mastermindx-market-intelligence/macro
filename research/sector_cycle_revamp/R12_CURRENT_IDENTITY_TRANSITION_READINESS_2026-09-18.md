# R12 — Current identity readiness has two axes: owner subject vs settled listing

Date: 2026-09-18  
Status: RESEARCH CORRECTION / PRODUCT SEMANTIC RULING / NO SOURCE WRITE  
Parent programme: existing Finviz / Sector / Theme / Cycle Intelligence revamp.

## 1. Why R11 needs this refinement

R11 correctly separated group/member measurements from identity-dependent product features and measured 696 / 701 corrected candidate symbols as owner-composed through Data OS after the FI/FISV repair.

One of those 696 subjects, KHC, carries a **current listing transition that Data OS itself has not adjudicated**.

Therefore “owner reader returned a subject” and “every current identity coordinate is settled” are not the same state.

R12 does not retract R11's product law. It refines the identity state machine used by identity-dependent features.

## 2. KHC evidence is current and internally coherent

Current repository evidence at Macro `391eebc44f9a697f10abc7d51a575c81b95ba18d`:

### Committed Data OS master

KHC remains stored as:

- security_id: `SEC:US-XNAS-KHC`
- listing_key: `US-XNAS-KHC`
- issuer_id: `ISS:US-XNAS-KHC`
- issuer CIK: `0001637459`
- issuer_state: `RESOLVED`.

### Current symbol directory

Tracked symbol-directory history changes from:

- `2026-07-13`: `NASDAQ`, “The Kraft Heinz Company - Common Stock”
- `2026-09-15`: exchange code `N` / NYSE, same KHC symbol.

### Current SEC registrant evidence

Every checked weekly CIK map from 2026-08-10 through 2026-09-14 continues to map:

`KHC -> CIK 1637459 -> Kraft Heinz Co`.

### Data OS's own refusal receipt

The canonical Data OS receipt contains:

- candidate listing key `US-XNYS-KHC`;
- a `pending_transition_refusals` row for KHC;
- listing continuity naming KHC;
- reason: a candidate new listing coordinate exists while the general pending-transition fence has not yet accepted the continuation.

This is exactly the fail-closed behavior the Data OS contract promises.

## 3. External primary-source corroboration

Kraft Heinz's own investor-relations release dated 2026-08-26 states that its common stock would transfer from Nasdaq to the NYSE and **begin trading on the NYSE on September 14, 2026 under the same ticker KHC**:

https://ir.kraftheinzcompany.com/news/kraft-heinz-to-transfer-stock-exchange-listing-to-nyse/0f3f933b-8f7f-4c91-a860-0cb6457f9d6f

The issuer's SEC-filings page records the transfer paperwork:

- 2026-09-08: Form 25;
- 2026-09-08: Form 8-A12B;
- 2026-09-09: exchange certification.

https://ir.kraftheinzcompany.com/sec-filings

This proves the current venue move is real. It does not by itself decide Data OS's security-ID continuation semantics; that remains the identity owner's job.

## 4. Three readiness states for Atlas identity-dependent features

### A. SETTLED_CURRENT

Owner-composed current identity exists **and** the Data OS current-listing transition fences do not name the member as unsettled.

Corrected candidate: **695 / 701** distinct source symbols.

### B. TRANSITION_PENDING

Owner-composed identity exists and issuer continuity is evidenced, but Data OS has an unresolved current listing/security transition.

Current candidate: **1 / 701 — KHC**.

KHC appears in one Atlas group: `us_sector_staples`.

### C. UNRESOLVED_CURRENT

No complete current owner-composed subject.

Current candidate: **5 / 701**:
ANGPY, B, CBOE, IMPUY, RHHBY.

These five appearances occur in four groups, exactly as R11 records.

## 5. Candidate population impact

At the member-appearance level:

- 1,014 / 1,020 appearances are SETTLED_CURRENT;
- 1 / 1,020 is TRANSITION_PENDING (KHC);
- 5 / 1,020 are UNRESOLVED_CURRENT.

Thus:

- owner-composed subject coverage remains 1,015 / 1,020 = 99.5098%;
- fully current-listing-settled coverage is **1,014 / 1,020 = 99.4118%**.

At group level:

- 44 / 49 groups are fully SETTLED_CURRENT;
- 1 group (`us_sector_staples`) contains a transition-pending member;
- 4 groups contain unresolved members.

This is still more than sufficient for truthful group-level Atlas representations, because those representations are owned by source membership and P1 measurement semantics rather than current listing-ID completeness.

## 6. Product behavior for TRANSITION_PENDING

KHC remains in:

- the source-member roster;
- Group Pulse/P1 measurement denominators;
- group Grid/Table/Cluster/Bubble membership breadth.

It must **not** be removed or set to zero merely because the canonical security transition is pending.

Identity-dependent UI/machine behavior:

- may identify the stable house member as KHC;
- may disclose issuer continuity (same SEC CIK) as source context;
- must not present the old `US-XNAS-KHC` listing coordinate as confidently current;
- must not invent or pre-commit `SEC:US-XNYS-KHC` before Data OS adjudicates the transition;
- security-level overlap/independence involving KHC is partial/unavailable;
- issuer-level overlap also remains partial for Atlas until the canonical identity owner declares which issuer/security IDs survive the transfer, because today's issuer ID is itself listing-key-derived.

A stable house route may remain usable if it does not claim a settled listing venue. Current-listing-sensitive drill-through must carry the transition state.

## 7. Why Atlas must not fix KHC locally

Data OS's own ID grammar derives security and default issuer identifiers from the canonical listing key. A venue transfer therefore raises a real architecture question about:

- listing-key transition;
- security continuation/supersession;
- issuer-ID continuity/migration;
- alias epochs.

Atlas has no authority to answer it.

No R12 change is made to:

- Data OS;
- security master;
- vendor aliases;
- KHC membership;
- P1;
- GMI topology;
- Terminal;
- source rights.

The existing pending-transition fence remains authoritative.

## 8. Revised identity readiness for first Atlas

The first real Atlas may proceed after the source/P1/publication gates with:

- every accepted group visible;
- every source member visible;
- group breadth and member-count representations intact;
- per-group identity readiness exposing SETTLED / TRANSITION_PENDING / UNRESOLVED counts.

Identity-dependent claims fail closed:

- full security overlap requires all relevant members SETTLED_CURRENT;
- full issuer overlap requires canonical issuer identity settled for every relevant member;
- a transition-pending or unresolved member makes the full scalar PARTIAL/UNAVAILABLE;
- known resolved intersections may still be shown with explicit coverage denominators.

This preserves the user job without turning unresolved infrastructure into hidden completeness.

## 9. Exact continuation

KHC identity continuation is a separate Data OS principal decision, not the next blocker for group-level Atlas work.

Current critical product chain remains:

1. #7284 accepted membership source;
2. #7252 same-carrier population-dependent P1 regeneration;
3. #7211 current-run publication/deployed proof;
4. compact existing-owner producer + signed-in Terminal consumer.

#7299 improves identity and GMI consumption independently. KHC/CBOE/B/ADR identity gaps remain side lanes unless an identity-dependent product feature specifically requires them.
