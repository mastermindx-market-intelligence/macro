# R11 — Identity-gated Atlas admission: complete group map, typed identity nulls

Date: 2026-09-18  
Status: RESEARCH RULING / SOURCE REPAIRS IN FLIGHT / ATLAS IMPLEMENTATION STILL HELD  
Parent programme: existing Finviz / Sector / Theme / Cycle Intelligence revamp.

## 1. Decision

Canonical security/issuer identity is required where the product makes a **security-identity or issuer-identity claim**. It is not a prerequisite for displaying an already accepted house group, its exact source-member roster, or its security/member-level strict breadth.

R11 therefore separates:

1. **group/member measurement admission** — governed by the house membership + P1 measurement owners; from
2. **identity-dependent feature admission** — governed by Data OS and allowed only where the required identities resolve.

This is the identity analogue of R9's cap ruling: a hard downstream enrichment gap must not erase a truthful upstream group or stall every representation.

The first Atlas still waits for the existing source/release gates (#7284 membership repair, #7252 P1 regeneration, #7211 publication composition). R11 changes what must be true *after* those gates: the remaining handful of typed identity nulls do not require all 49 groups to wait.

## 2. Evidence pins

Protected Skillpack at ruling time:
`mastermindx-market-intelligence/Mastermind@61a2ff79aba4e8a5685e779707ad5c4426cf5cc5`, Skillpack 1.0.1.

Input carriers:

- structural-sector source repair: #7284, current candidate head `4c36666287eb36721b258ff55ccf53a04bc52dc5`;
- cap owner coverage repair: #7278, head `504a55cc99d145fb36c71466a2d6be44276ab720`;
- FI/FISV canonical identity regression: #7299, current candidate head `b405ad51f94d019ffd5ea10eb81c90d97f40f0ee`;
- P1 member evidence: #7252, release-held pending accepted membership source;
- publication owner: #7211.

R10 pre-FI identity receipt:
`/Volumes/Mastermind/agent-evidence/sector-cycle-identity-r10-20260917-sol-001/identity_coverage.json`.

Post-FI candidate receipt:
`/Volumes/Mastermind/agent-evidence/sector-cycle-identity-r10-20260917-sol-001/post_fisv_candidate.json`,
SHA-256 `571317a64ce278252c6cf293a195ce7d3494e0f73fb8ef3b8bb9c96874985c17`.

## 3. Corrected population + identity coverage

The #7284 candidate keeps:

- 49 groups;
- 1,020 active group-member appearances;
- 701 distinct active source symbols.

The #7299 candidate restores Fiserv through the canonical Data OS owner:

`FI (stable repo/store key) -> SEC:US-XNAS-FISV -> ISS:US-XNAS-FISV -> CIK 0000798354`

while `FISV` remains the live listing/vendor symbol.

On the corrected 701-symbol candidate, the existing owner-composed current-only identity reader resolves:

- **696 / 701 distinct source symbols = 99.2867%**;
- **1,015 / 1,020 group-member appearances = 99.5098%**;
- 696 unique security IDs;
- 693 unique issuer IDs;
- 5 typed identity failures.

No ticker-equality fallback, issuer-name inference, guessed venue or synthetic ID is used.

## 4. Where the five unresolved identities actually matter

Only four of the 49 groups contain an unresolved member:

| Group | Resolved / members | Identity coverage | Typed unresolved |
| --- | ---: | ---: | --- |
| `pgm_miners` | 2 / 4 | 50.0% | IMPUY, ANGPY |
| `gold_miners` | 11 / 12 | 91.67% | B |
| `obesity_glp1` | 13 / 14 | 92.86% | RHHBY |
| `us_sector_financials` | 75 / 76 | 98.68% | CBOE |

The other **45 groups have 100% canonical identity coverage** for the corrected candidate.

The five failures remain first-class nulls:

- ANGPY — no current store/security-master binding;
- IMPUY — no current store/security-master binding;
- RHHBY — no current store/security-master binding;
- B — existing fail-closed ticker-reuse/identity-continuation case;
- CBOE — current listing evidence exists, but venue code `Z`/BATS is outside the closed Data OS MIC vocabulary.

CBOE's clean owner repair is currently source-collided with another open Data OS owner touching `lib/dataos/identity.py`; no competing write is started by this programme.

## 5. Identity changes semantics even at 100% coverage

`us_sector_comm` is 24 / 24 resolved securities but only **21 unique issuers**.

Three issuer pairs each contain two separately listed member securities:

- FOX + FOXA -> `ISS:US-XNAS-FOX`;
- GOOG + GOOGL -> `ISS:US-XNAS-GOOG`;
- NWS + NWSA -> `ISS:US-XNAS-NWS`.

Therefore:

- a source member count is not an issuer count;
- strict group breadth over member securities must not be retroactively issuer-deduplicated;
- a future issuer-footprint lens is a separate representation with separate denominator semantics;
- ticker-string equality is insufficient even when every ticker resolves.

This is direct evidence, not product preference.

## 6. Representation law after R11

### Group Grid / Table — identity NOT required for admission

May display every accepted group and its exact P1 group measurements from the house membership owner.

Allowed:

- group name/category;
- source member count / membership breadth;
- strict-trend-50 and strict-trend-200 group measurement;
- observation status/date;
- identity coverage receipt (e.g. 11/12) as context;
- evidence/detail link.

Identity nulls do not remove a group or member from the measurement population.

### Member evidence — unresolved rows remain visible

Every source member remains in the member evidence roster.

Resolved identity:
- may expose canonical security/issuer identifiers to machine consumers;
- may enable the admitted company drill-through.

Unresolved identity:
- remains visible with the existing measurement/missingness evidence;
- identity-dependent company drill-through is unavailable/typed;
- never inherits an identity from name similarity, ticker reuse, market cap or another group.

### Clusters / Bubbles — membership-breadth size remains valid

The R9 first-slice size encoding remains **member count / membership breadth**, not issuer count and not market cap.

That representation needs no identity dedup because it explicitly describes source membership appearances.

If an issuer-count lens is later offered, it must be separately labelled and use canonical issuer IDs.

### Cross-group overlap / “independent confirmation” — identity REQUIRED

Never compute overlap/independence from ticker strings.

Use canonical:
- security IDs for listing/security overlap;
- issuer IDs for economic-issuer overlap.

If either comparison population contains unresolved identities:
- the full overlap/independence statistic is **UNAVAILABLE/PARTIAL**;
- known resolved overlaps may be listed with an explicit resolved denominator;
- no scalar “independent confirmation,” diversification, duplicate-adjusted breadth or issuer-count claim may pretend the unresolved tail is zero.

This is especially load-bearing for `pgm_miners`, where only 2/4 current members resolve.

## 7. P1 metric semantics stay unchanged

R11 does not change Group Pulse/P1 calculations.

The P1 strict breadth measurements are defined over the admitted source-member/security population. They are not issuer-deduplicated and must not become issuer-deduplicated merely because Data OS can identify class-share siblings.

Identity is context and join authority around those measurements, not a new rank/selection input.

No LLM, identity coverage ratio or unresolved-state count may directly rank, gate, size or originate trades.

## 8. #7299 closes one real downstream integration gap

The Fiserv Data OS repair initially healed the master but left the derived GMI identity sidecar stale.

#7299 therefore also re-derived **only** `data/theme_graph/identity_resolution.parquet` from:

- committed graph nodes;
- healed Data OS identity artifacts;
- existing graph belief-time `2026-09-17`.

It appended one 2,807-row generation at `computed_at=2026-09-18T10:17:13Z`.

Verified:

- nodes/edges/evidence/capability/_meta hashes unchanged;
- FI and FISV latest sidecar rows both resolve to Fiserv's canonical issuer/security;
- committed-bake reproducibility passes;
- 53 relevant GMI identity tests pass with three pickup-base fixture contradictions excluded;
- strict theme-graph contracts pass;
- 55 identity-seam/theme-graph contract tests pass.

This proves the existing Data OS -> GMI consumer can absorb the heal without a new identity plane.

## 9. Known base debt is not laundered into this programme

Current protected Macro base already contains unrelated Data OS/GMI test drift:

- KHC pending-transition refusal exists while an older test expects none;
- current CIK map no longer carries GGRP while an older test pins it as a live exemplar;
- current graph has 2,807 company nodes while older tests pin 2,806;
- current sidecar includes VMRK while an older test asserts no VMRK;
- sparse worktrees omit some artifact fixtures such as Fred vintages.

These are disclosed/inherited, not fixed in #7299 and not treated as evidence that FI/FISV failed.

## 10. Exact product frontier

The first real Atlas no longer needs to wait for “100% identity coverage.”

It still must wait for truthful source composition:

1. #7284 accepted structural membership source;
2. #7252 regenerated population-dependent P1 evidence on that source;
3. #7211 current-run publication composition and real deployed proof;
4. one existing-owner compact projection + one signed-in Terminal consumer.

When that frontier clears, the real first vertical may ship all 49 groups with:

- group metrics for every group;
- source-member rosters for every member;
- per-group identity coverage;
- company drill-through only where identity resolves;
- no identity-dependent overlap/issuer claim where coverage is incomplete.

Cap sizing remains separately gated under R9/#7278.

The destination remains the full Matrix/Clusters/Bubbles/table experience with broader coverage, genuine cap sizing, temporal rotation, economic/regime intelligence and separately validated Prophet contribution.
