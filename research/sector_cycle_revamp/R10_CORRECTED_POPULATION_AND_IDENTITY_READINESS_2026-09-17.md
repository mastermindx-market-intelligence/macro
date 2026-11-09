# R10 — Corrected Atlas population and canonical identity readiness

Date: 2026-09-17  
Status: RESEARCH RULING / SOURCE REPAIR IN FLIGHT / ATLAS IMPLEMENTATION HELD  
Parent programme: existing Finviz / Sector / Theme / Cycle Intelligence revamp.

## 1. Material invalidator since R9

R9 admitted a first non-cap Atlas scope over the P1-captured 49 house groups: 1,020 group-member appearances and 702 distinct active source keys.

A later canonical-owner reconciliation found that the structural `us_sector_*` rows in `data/baskets/membership.json` had drifted behind the current S&P 500 constituent/GICS owner. This is upstream population truth, so the old 702-key receipt is no longer release-admissible.

The repair is isolated on Macro PR #7284 at `ac84fbbe1d09bd86174caeffc0f191e858e30510`. It is not yet accepted or merged. The existing P1 carrier #7252 was release-held without cancelling or rerunning its queued CI.

## 2. Corrected population candidate after #7284

The repaired source preserves:

- 49 house groups;
- 1,020 active group-member appearances;
- the existing membership/PIT model `[added, removed)`;
- `curated_added` as provenance rather than historical inclusion.

It changes the distinct active symbol union from **702 to 701**.

Union exits:

- AVB;
- CAG;
- EA.

Union entries:

- HONA;
- RDDT.

FERG was already active in `industrial_distribution`, so its addition to Industrials does not add a new union symbol. APP and DD are sector transfers and likewise do not change the union.

The eleven active `us_sector_*` rosters on #7284 reconcile exactly to the current 503-row S&P 500 sector reference: zero extra, zero missing, zero absent structural baskets.

This corrected population remains a candidate until #7284 clears its release gates. Do not rewrite R9/P1 evidence in place or call the new population current before that source repair is accepted.

## 3. Permanent drift guard without a second membership authority

The incumbent `scripts/reconcile_membership.py` already owns end-of-collect membership reconciliation for regional suites. It deliberately did not auto-mutate U.S. membership, which is correct because a current S&P snapshot cannot establish the historical effective date of a change.

#7284 therefore extends that incumbent owner only with a **non-mutating U.S. structural audit**:

- compare current active `us_sector_*` rows to `data/breadth/constituents.parquet`;
- write the comparison into the existing `membership_reconcile.json` receipt;
- emit a line-start GitHub warning on drift;
- never add, remove or move a U.S. member automatically.

Future drift is detected promptly, while dated membership edits still require evidence. No second roster, watcher, scheduler or lifecycle is created.

## 4. Canonical identity owner for Atlas

Atlas must not use ticker equality, GMI topology IDs, cap-cache keys or a new resolver as security identity.

The existing authority is Data OS:

- `config/identity_seams.yml`;
- `data/reference/security_master.parquet`;
- `data/reference/vendor_aliases.parquet`;
- `data/reference/issuer_master.parquet`;
- `lib/dataos/identity.py`.

For a current product projection, the existing `scripts/security_state_producer.py::_read_security_state_identity_rows` provides the right owner-composed read:

`VendorAliasTable.resolve("store") -> IssuerMaster.issuer_of_security -> issuer CIK -> listing key`.

It allocates no new identity, requires an exact current alias binding, round-trips the alias, and returns typed per-symbol failures.

## 5. Identity readiness on the corrected 701-symbol candidate

Using #7284's corrected active symbol union and exact committed Data OS identity artifacts at Macro `3c39f71bfd526ac35e5af67a497dd28f4c9a889d`, the current-only owner reader produced:

- population: **701** symbols;
- complete owner-composed identities: **695**;
- typed failures: **6**;
- coverage: **99.1441%**;
- unique security IDs: **695**;
- unique issuer IDs: **692**.

Three current issuers legitimately span two securities in this population:

- `ISS:US-XNAS-FOX`;
- `ISS:US-XNAS-GOOG`;
- `ISS:US-XNAS-NWS`.

This is direct evidence that ticker count is not issuer count. Atlas overlap/independence logic must use resolved security/issuer IDs where available and retain unresolved rows explicitly.

Receipt:
`/Volumes/Mastermind/agent-evidence/sector-cycle-identity-r10-20260917-sol-001/identity_coverage.json`

SHA-256:
`e5e05652070c5ae2c77ccd05447f78f7ddb2341877d35601129b89c062fd0549`.

## 6. Six typed identity failures

### ANGPY
No current Data OS `store` alias or security-master row.

### IMPUY
No current Data OS `store` alias or security-master row.

### RHHBY
No current Data OS `store` alias or security-master row.

These ADR/OTC-style names remain **UNRESOLVED**. Do not manufacture exchange, issuer or security identity from the ticker.

### B
No current Data OS `store` alias/master row even though the current symbol directory and CIK map observe Barrick Mining under `B`. This ticker participates in an already-known ticker-reuse/identity-break problem. It requires the existing identity-continuation law, not a new Atlas exception.

### CBOE
Current source evidence is unusually complete:

- symbol directory observes `CBOE`;
- SEC CIK map observes `CBOE -> 1374310`;
- the directory exchange code is `Z`, documented by the existing collector as BATS;
- the Data OS venue map intentionally refuses `Z` because the closed MIC vocabulary does not yet contain that venue.

This is a candidate **existing identity-owner venue-coverage repair**, not an Atlas resolver problem. Any repair must add the verified MIC through Data OS with discriminating tests and retain the closed-list/fail-closed law.

### FI
The current `store` alias resolves `FI -> SEC:US-XNAS-FISV`; the security/listing identity exists, but the issuer is `NO_ISSUER_EVIDENCE` with no canonical CIK, so the owner-composed reader correctly refuses a complete subject.

The current symbol directory and CIK map still observe `FISV`, not `FI`. This is a different identity-evidence problem from CBOE and must not be bundled into the venue repair or solved by manually filling a CIK.

## 7. GMI graph is not the Atlas population owner

A raw scan of append-only GMI edges initially appeared to expose stale GOLD membership. That interpretation was rejected after applying the graph's own latest-belief law: GOLD's latest edge is correctly closed.

The latest-belief graph still differs from the P1 membership source for legitimate graph-domain reasons, including the IBIT company-kind conflict and rename history. Therefore:

- house membership owns the first Atlas population;
- Data OS owns exact security/issuer identity;
- GMI remains a topology/exposure consumer/bridge;
- Atlas must not redefine current roster from GMI MEMBER_OF edges.

## 8. Release and product consequences

R10 does **not** start Atlas implementation.

Required sequence now:

1. #7284 source-truth repair clears hosted CI/review and is accepted.
2. #7252 stays on its existing carrier, reconciles the accepted membership source and regenerates only population-dependent P1 evidence. Completed math/source/review work is not repeated unless the new cohort exposes a real defect.
3. R9's compact real-scope receipt is regenerated from the accepted **701-symbol** population.
4. Data OS identity failures remain explicit. A bounded CBOE venue repair may proceed independently through the existing identity owner; FI/B/ADR cases stay separate.
5. Cap-owner #7278 continues independently.
6. Only after the accepted producer/source inputs are coherent may one real signed-in Terminal Atlas vertical begin.

No predictive, ranking, gating, sizing or trade authority is created here.
