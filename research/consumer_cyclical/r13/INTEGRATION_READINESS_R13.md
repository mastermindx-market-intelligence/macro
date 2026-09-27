# Consumer Cyclical R13 — integration-readiness reconciliation

Operation: gmi-consumer-cyclical-research-20260923-sol-001
Carrier: Macro PR #7804
Input head: 83bca96a5ca786de3a55d351149813b5c2d0b1b2
Protected procedure: Mastermind 1a7d400294b0d37c460b963b8865b40a23173b58 (Skillpack 1.0.1 / bootstrap 1)
Authority: research/design only; no ranking, gating, sizing, entry, source admission, deployment or product acceptance.

## 1. What this R13 changes

R13 does not redo R1–R11 or reopen the completed independent review. It closes the review-packet and current-binding work that became necessary after the R12 H1–H3/M1–M5 executable repair.

The executable R12 candidate remains 83bca96a5ca786de3a55d351149813b5c2d0b1b2: 60 discriminating research checks pass and no native/product/browser proof is claimed.

R13 adds the exact machine-readable evidence the next reviewer needs for M6–M9 and records the live shared-owner frontier without pretending in-flight shared work is accepted.

## 2. M6 — complete reviewer packet

The original independent review omitted three existing companion maps. The targeted re-review must consume them directly:

- R6 design evidence: CONSUMER_CYCLICAL_R6_DESIGN_EVIDENCE_2026-09-23.json, blob cdab90b867e16b36ff08fd6a678d4547308cec95, 32 mapped requirements.
- R7 delivery map: CONSUMER_CYCLICAL_R7_REVIEW_AND_DELIVERY_MAP_2026-09-23.json, blob 58c26b787da834f92efb82363daecc631e034367, 10 mapped requirements.
- R10 foundation map: CONSUMER_CYCLICAL_FOUNDATION_INTEGRATION_MAP_R10_2026-09-24.json, blob 6b69882a3bf9cc43b686ddfdd41475606258334c, 16 mapped requirements.

That is 58 companion mappings. The corrected full requirement universe is 174, not 206. Every product obligation remains NOT_EXECUTED unless separately proven later.

## 3. M7 — source-rights representation classes are now explicit

Consumer's R11 objection on #7870 comment 5809660585 was accepted and landed by the shared owner. At #7870 head 0c7f637cc63c4d0c29232a0738f971c9eca3626a, config/theme_sources.yml blob 1073ca1e9841dc95084a57b4577d159e74f9d211 records:

- sec_edgar: direct_display_ok, keyless_public;
- factual inputs, receipted short excerpts and original interpretation with SEC attribution/link are the qualified house representation;
- whole expressive documents, attached third-party material, issuer logos/branding and dataset redistribution are not claimed;
- a third-party attachment requires its own reviewed family or refuses;
- licensing redistribution remains false.

Separately, R4 says current protected paid research remains private even when house-authored. Entitlement never manufactures source permission.

This is a representation-specific binding, not a blanket legal conclusion and not live source admission.

## 4. M8 — refreshed pins, but pins are not write authority

Current reconciliation pins:

- Macro main: e486949f565fd888d462fae405880b8b46161e81.
- Consumer #7804 input head: 83bca96a5ca786de3a55d351149813b5c2d0b1b2.
- Shared foundation #7870: 0c7f637cc63c4d0c29232a0738f971c9eca3626a.
- #7669 template owner: 6942b2b62bad2dfc9d3b50eb7042e0a126b708c4; its owned basket_detail blob remains f6540573c9319b1a1bcd04fbe2508254fe9cc342.
- #7462 Theme Graph store owner: 31706d7322af55696dc7b2e746ec511b08bd51d7 and frozen for Consumer writes.
- #7426 Company-history owner: 7bc04876747d773861b47519061279ae033a148d; existing Consumer consultation is comment 5807032650.

The exact current shared blobs needed by the Consumer handoff are enumerated in R13_REVIEW_MANIFEST.json, including the rights registry, guidance limitation, common mount seam, incumbent paywall and its test.

These pins are valid for review/handoff only. Fable must fresh-read the relevant owner heads and affected blobs immediately before any native write. An accepted T09/T11 commit, the B-foundation build-out ruling, owner movement on a relevant file or a source-custody change invalidates the corresponding pin.

The historical R7 pin 8db6896dab2199a4b7fc61a005c225380cac7cd6 remains evidence only and grants no write authority.

## 5. M9 — bind the chosen grace behavior to the incumbent paywall owner

R4 comment 5808854275 selected the existing positive-only site_full entitlement-store-outage grace, capped at 86,400 seconds from the last successful positive observation, with no grace for invalid auth/fresh negative/invalidation and no source-rights override.

The incumbent implementation and test are already identical on current Macro main and #7870:

- app/paywall.py blob 7e1c6861ebb7d27924865b2b8d157e6a9356405d;
- tests/test_paywall.py blob 1d958154eed91ee08f9f7ab65b719e1910e2ccd1.

Two explicit incumbent cases are material:

- test_missing_or_invalid_auth_never_uses_entitlement_grace;
- test_store_outage_graces_only_recent_positive.

A targeted local replay against those exact blobs passed 2 passed on 2026-09-24. This is existing-owner test evidence, not a Consumer native-staging action.

Production proof remains owed: actual deployed grace/cache values, the real invalidation path/timing, and the live protected research route.

## 6. Current shared-owner bindings

The old R10 statuses are superseded as follows:

- R4: architecture accepted with qualifications on #7780 comment 5808854275; live private proof still owed.
- Consumer disposition: #7870 comment 5809602368 consumed. Signed/exact and qualitative shared-assertion extensions are held to the same owner's separately gated v1.1; Consumer does not widen v1.
- Missing definitions: shared guidance_history.py now emits definition_unqualified:<field> for two absent definitions instead of silently certifying them.
- SEC rights: Consumer R11 objection accepted and landed.
- Shared page seam: #7669 ruling 5808986207 accepted; #7870 returned an independently reviewed common include at 5810675425. Consumer does not author another shared include.
- T09 transport: not accepted yet; its first review rejected and the fix lane is still queued at the current #7870 checkpoint.
- T11 private binding: not accepted yet; its lane is still queued.
- Cross-vertical profile + reported-economic-context build-out: still an open ruling request on #7780 comment 5811066300. Consumer must not fabricate guidance just to enter the Semiconductor economics path.
- LULU history: remains with #7331/#7426; no new Consumer consultation is opened.
- Generic economic_change_dossier.v1: the Energy proposal carrier #7898 is closed unmerged. It is not the common foundation contract.

Therefore consumer_cyclical / consumer_economic_change.v1 remains a design-level closed Consumer profile/discriminator, pending accepted shared-owner enrollment. Unsupported Consumer requests must refuse; they must never fall back to Semiconductor.

## 7. Re-review boundary

The new targeted independent reviewer should read only the changed repair package plus the three immutable companion maps and the exact current-owner evidence named in the manifest. It should not redo foundational sector research, shared-foundation archaeology, consultations, the old review, native staging, or production/browser testing.

The reviewer must distinguish:

1. Consumer package defect — something wrong or missing in R12/R13 that blocks a principled Fable handoff.
2. External named gate — T09, T11, build-out/profile/reported-economics, LULU history, live privacy/browser/source admission.

A clean package review does not clear an external gate. Conversely, an external gate does not require the research package to be redesigned if the dependency is already typed and held.

## 8. Final integration target

If the targeted re-review accepts the repaired package, the next product-level action is one final Fable integration handoff. Fable should consume the current shared foundation, preserve all source/custody fences, use the existing owners and routes when they become accepted, implement vertical content rather than a parallel platform, and re-pin every affected native group immediately before a write.

The blocked native-staging action remains sticky: do not retry, rephrase, re-home or delegate a workaround for that action.
