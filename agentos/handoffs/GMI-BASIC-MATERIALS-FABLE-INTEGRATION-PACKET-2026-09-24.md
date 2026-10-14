---
schema: mastermind.agent_handoff.v1
title: "Basic Materials Economics — Fable integration decision packet"
operation_key: gmi-basic-materials-research-20260923-sol-001
program: gmi-theme-graph
repository: mastermindx-market-intelligence/macro
mission_complete: false
implementation_authority: none
---

# Basic Materials Economics — current integration handoff

Updated 2026-09-26 through R25. This is the same canonical packet, not another handoff/control plane. The complete preceding R23 packet is retained at this path in commit `acde066d1d6fa756a64508114d1c457b613be054`, blob `68dbec7623c8e8225954f140f8800799be535f80`. R24 diagnosis is in the cumulative checkpoint at `48be143b38296d38845d1274694202d9414ea253`, blob `d359ae1bfba3530f4a710202682ab4dc6c5649f6`.

**Prepared for principal integration and independent review, not an unblocked production build.** Sol retains Materials principal responsibility under the live Chairman continuation. No Materials worker receiver, PICKUP_ACK, START, Executive Attempt or autonomous wake is established. Fable is reserved for consequential shared-owner integration/acceptance; routine execution uses the least-scarce capable admitted worker. This packet itself assigns nobody and grants no product/shared writer, identity, rights, admission or release authority.

## Mission and binding product topology

Deliver useful Materials Economics: what changed, which operating business or financial right captures it, what reaches retained cash/per-share economics, what was expected, and what evidence matters next.

Preserve **44 core requirements, eight task identities, five originals/four real company journeys, ten research-navigation families/eight lenses, and V0–V4 ambition**. Source-only fallback, arithmetic, an empty shell, shared merge or CI green is not full product acceptance.

R21 remains binding: **Basic Materials sector dossier first; reusable #7984 economics core below it; later canonical-theme drilldowns through #7870 only for accepted anchors**. Do not create `theme:basic_materials`, substitute a sector ETF/basket for a theme, or omit unanchored families. Accepted-theme examples in the R21 crosswalk are `rare_earth_critical_min`, `copper_steel_electrify`, and `ag_fertilizer`; exact current mappings still come from their owner. Precious-metals financial claims, forest products and other unmapped families remain legitimate sector/research slices, not newly minted themes.

Research/masterplan #7796 / `sol/basic-materials-research-20260923` remains the research-only carrier. #7984 / `claude/basic-materials-core-v0` remains the separate economic core. Last reconciled product head is `36f330b1f7829a289a44937bca0007c734d6df5e`, Draft/HOLD/RED; not refreshed by R25. Shared source inspected at #7870 tree `6cd958e92b259f7221690547e7076f4a0de4ed33`; pinned-source evidence is not a fresh whole-PR/runtime claim. Preserve #7462/#7669 and other incumbent shared/template custody.

## R25 Materials decision — separate source scope from presentation

**Materials design disposition:** prefer an explicit source-local assertion mode in the existing shared versioned curation owner. Retain theme-bound assertions where the theme really belongs to the statement. Sector/company/theme page placement must not become part of a new source assertion merely because the page needs a grouping key.

This selects the Materials compatibility approach; it does **not** enroll a shared schema, reserve a namespace, accept a new ontology identity, authorize shared implementation, or replace the shared owner's review. The exact wire vocabulary and source-reference grammar below remain proposals until that owner accepts them. A compatible owner-selected representation is acceptable if it meets the same invariants.

### Alternatives adjudicated

| Approach | Disposition and reason |
|---|---|
| Make `canonical_theme_id` nullable but leave the codec/ref path unchanged | Reject. The existing resolver embeds that field in the URI. Nullability alone leaves undefined ref derivation and can turn missingness into a string. It does not distinguish deliberate non-theme scope from malformed theme scope. |
| Register one Materials theme, place a sector ID in the theme field, or force the five originals into unrelated themes | Reject. Violates R21 and confuses ontology identity with product navigation. Fragment-valid text is not admission. |
| Explicit source-local mode within the existing versioned assertion owner; independent view associations | Preferred. Preserves the source's own subject and meaning without another store or global sector identity. Requires the shared codec/ref/K1 and reader work described below. |

### Proposed minimal scope change — shared v1.1 review input, not production schema

Only the proposed new version changes. Existing v1 remains byte-for-byte and behaviorally unchanged.

Proposed `scope_mode` has exactly two values: `theme_anchor` and `source_local`. These are provisional shared-wire names, not new graph classes or runtime states. All six existing scope fields remain required, including explicit `canonical_theme_id`; the five contextual fields retain their incumbent shapes.

| Mode | `canonical_theme_id` | Semantics |
|---|---|---|
| `theme_anchor` | Nonempty string, separately verified through the existing ontology owner | A genuinely theme-scoped statement. String validation does not establish accepted identity. |
| `source_local` | Explicit null, not omitted and not an empty string | The existing source/locator and source-scoped subject describe the claim. No invented sector/company/theme ID is needed merely to express it. |

Missing/unknown mode refuses; no default, inference, normalization or auto-upgrade. Source-local mode with a populated theme refuses. Theme mode with null/empty theme refuses. Extra `sector_ref`, `company_ref`, `page_profile`, rights or authority keys in this scope refuse. Existing subject company identity may remain null; its source business/product/platform/configuration labels remain source-local rather than becoming a global identity allocation.

The candidate fragment is the R24 scope fragment with these changes only:

```json
{
  "required_addition": "scope_mode",
  "properties": {
    "scope_mode": {"enum": ["theme_anchor", "source_local"]},
    "canonical_theme_id": {"type": ["string", "null"]}
  },
  "allOf": [
    {
      "if": {"required": ["scope_mode"], "properties": {"scope_mode": {"const": "theme_anchor"}}},
      "then": {"properties": {"canonical_theme_id": {"type": "string", "minLength": 1}}}
    },
    {
      "if": {"required": ["scope_mode"], "properties": {"scope_mode": {"const": "source_local"}}},
      "then": {"properties": {"canonical_theme_id": {"type": "null"}}}
    }
  ]
}
```

This block is an explanatory delta, **not a complete JSON Schema**; `required_addition` describes an edit, not a validator keyword. The complete candidate used for the design experiment retains the original `type`, closed `additionalProperties:false`, required fields and five contextual properties. No `.schema.json` production file was created.

### Codec, evidence receipt and K1 remain one owner chain

The shared owner's eventual implementation must keep the four existing entry points: `curation_revision`, `encode_assertion`, `source_ref_for`, and `reference_for_assertion`. Dispatch is exact by accepted schema and explicit mode; no parallel Materials codec/ref helper.

For non-theme source refs, **this packet deliberately does not mint or standardize a URI literal**. The incumbent owner must accept and return one collision-disjoint derivation under its existing ownership, with a matching reader/parser. It must not stringify null, use a dummy theme, take a page/profile key as source identity, collide with any valid legacy theme ref, or accept arbitrary ref grammar as a shortcut. A proposed signature remains `source_ref_for(payload) -> str`; callers consume its result rather than construct strings.

The existing outer evidence receipt's `evidence_id` algorithm is unchanged: `ev:` plus the existing truncated hash of kind/source_ref/published_at. Its `source_ref` is already a nonempty string rather than an enum of themes. This removes any need to design another evidence-row store just for source-local scope, but **does not prove native storage compatibility**. Validate the complete guard/codec/reader chain and current store custody before admission.

K1 stays in existing `theme_graph.curation_assertion` ownership with native `{evidence_id, curation_revision}`. Reuse the v1.1 proposal's exact owner-schema-set check and payload-derived native schema. Do not reinterpret a source-local business label as a security/CIK subject or invent a cross-type recipe. The existing **P5** preservation corpus must prove unchanged v1 encoded bytes, revisions, source refs, complete K1 objects and reference IDs. Local design checks are not P5.

### One statement can serve several views; content changes still create revisions

For the *same retained assertion revision*, changing a sector/company/theme page filter, sort order, label, page profile or navigation context must not re-encode the assertion or change its native source ref/evidence/K1 identity. Existing view/relationship/identity owners decide where it is relevant. The Materials projection only references their accepted associations and immutable evidence.

This is not a promise that revisions never change. A corrected source, different locator, newly retained digest, changed retained content or other field included in the owner's hash produces a new revision under existing correction law. Never silently rewrite old rows. A later identity-resolution result is consumed through the incumbent identity owner with its own vintage; it is not permission to mutate the original assertion or pretend the mapping was historically known.

Separate source publication, observation, retention, review, business-valid and mapping-known clocks. Preserve date-only and unknown values; no fabricated midnight, current-membership historical replay, or current build time as knowledge time. View duplication is not independent corroboration.

### Native source mode is not transport or rights permission

Source-local mode must never mean read-all. Auth and paid entitlement precede request parsing/reader construction, followed by a closed accepted profile, exact owner-resolved request scope, selected evidence and current source-rights checks. Unknown scope/profile/identity remains a private refusal; no wildcard registry, arbitrary import, direct object-key endpoint or new API/auth/client stack.

The actual inspected shared rights filter attributes from `source.source_uri`, not the assertion ref, `locator`, sector label or a new rights flag. Keep that one source attribution owner. The same current rights snapshot must govern loading/fingerprinting and emission; withheld sources also withhold dependent explanations and any pointers/metadata that would expose their existence. Rights restriction does not delete retained historical records. Positive source-mode validation grants neither retention nor display.

T5 still needs an accepted sector-private reader and exact sector/outer-inner join. The existing v1.1 proposal's `company_profile` branch is not itself a sector-aggregate grant. The shared owner must name an accepted closed sector path or explicitly hold it; Materials must not stretch a company ref to name a sector. The inspected loader's `private_assertions_unbound` remains a real private-path limitation, not a missing UI label.

## Five-original/four-company application of the decision

| Existing proof subject | Native interpretation to preserve | View behavior and prohibited inference |
|---|---|---|
| Nutrien manufactured phosphate | Same reported combined fertilizer/industrial/feed scope; comparable selling-price/COGS/unit-margin periods and units | May appear in sector research and a later accepted fertilizer-theme view without re-minting for that view. Do not claim fertilizer-only or whole-company profitability. |
| NOVONIX qualification original | Customer and internal testing remain different propositions; qualification and commercial acceptance are not percentages/probabilities invented from test counts | Source-local evidence can remain source-local; an identity/theme mapping is separate. Future sales/capacity remain conditional. |
| NOVONIX collaboration original | A separate announced nonbinding arrangement with its own locator, clocks and limitations | It neither supersedes nor proves completion of the older qualification proposition. Newer company news is not a correction edge by itself. |
| Wheaton/Antamina | Source-reported financial participation, payment obligations and delivery thresholds, not mine ownership/control | Sector and issuer/right views may reference the same accepted statement. Do not add physical supply, flatten tiers or calculate an investment return from incomplete terms. |
| Weyerhaeuser | Actual cash after total investment beside the issuer's separately adjusted distribution measure | Sector-research relevance does not change structural-sector membership. Growth investment still consumes cash; adjusted FAD is not automatically sustainable free cash flow. |

These are the existing cases, not newly admitted sources or a new corpus. AMS/Conch missingness, Canadian Nutrien identity uncertainty, original-source clocks and all source-specific limitations remain in the saved source registers.

## Owner implementation change map and acceptance return

This is one amendment to existing shared work, not a new implementation carrier or ninth Materials task.

| Incumbent surface | Required owner action before claiming acceptance |
|---|---|
| Proposed v1.1 scope and semantic layer | Accept explicit source-local semantics and exact field vocabulary; keep v1 validator/bytes intact; reject both ambiguous mode/anchor combinations and foreign fields. |
| Shared codec/ref | Return accepted non-theme derivation/parser and prove no collision with legacy refs, null-string fallback or page-induced re-minting. |
| Existing evidence/K1 binding | Real encode/decode/receipt/K1 round trip; exact native-schema ownership; P5 unchanged; source-subject and security identity remain distinct. |
| Shared registered reader/transport | Accept sector-specific scope through its existing owner; distinguish schema/profile existence from a bound private loader; unchanged auth, private errors and current rights. |
| Materials pure core/projection | Reuse #7984 when qualified; preserve pointer-only source dependencies and explicit missingness. Do not duplicate arithmetic in UI/projection or freeze its output around the current RED. |

Extend the **existing** shared tests/corpus, not another fixture programme: P5 legacy preservation; one real native source-local round trip from the existing proof set; same assertion referenced by two accepted views without new evidence identity; changed retained content creates a distinct correction revision; mixed/unknown modes refuse; unresolved subject identity stays unresolved; wrong view/cohort cannot retrieve a foreign assertion; current-rights revocation suppresses dependent output. All real sources need existing retention/review/admission first; fixture refs never become production admission.

The acceptance return must cite the owner's exact schema/module/ref/parser/K1 signatures, immutable implementation/test head, actual tests and independent review disposition, plus the separate private reader/rights/identity proof or named remaining holds. A docs-only answer cannot be labeled native compatibility. Materials-side design approval does not accept the shared implementation.

## R25 design experiment — actual limits

The existing R24 input export was reused unchanged (SHA256 `6d2583d59eabea4b48c8ec6c496acd45d82edfa0ef390c2018c8f7196fafa7d0`). The candidate mode tag was applied to its eight scope cases; five mutations of those same inputs tested missing/unknown mode, conflicting mode/anchor pairs and page-profile injection. **13/13 candidate shape expectations matched: four shape-valid, nine refused.** No new economic source/case corpus was created.

Two shape-valid controls still contain fabricated/misclassified theme strings. They deliberately prove that the ontology-owner gate remains necessary; the candidate does not claim to validate accepted theme membership. The design resolves deliberate source-local null versus malformed theme-null, not global identity admission.

Report `R25_SCOPE_DESIGN_QUALIFICATION.json` SHA256 `09f028c514f673225a20b6023f8f6457a76b6e1365808d1d65089cc58bec6abc`. This is a sandbox research artifact, not a production validator or canonical evidence store. **Native/product tests0, P5 runs0, source mints/admissions0, storage/API/browser proof0.** Input-file byte preservation is not legacy native codec/reference proof.

## Sector projection and UI boundaries retained

Consume the closed `sector_dossier_read_model.v1` by reference; do not append fields or fork it. The Materials inner model remains an owner-preserving projection of already-read outputs. Do not copy Finance's `sector:financials` or 52 slices. Exact Materials sector identity/outer-inner join remains UNBOUND until its incumbent owner returns it; no new alias.

Finance is a shell/navigation/projection precedent, not a connected private-reader precedent. At R22 pin `bd23cfbd3f192389166bef37e490003fadd6d453`, its builder has `FI_READ_URL = ""`; #8009 fixture-connected proof and #8006 fixture-only registration are not Materials production proof. One Finance-style sector-deep-dive card sits outside canonical theme lanes; the data-free dossier uses the existing shared design/navigation system and no private static payload. Dark/light, EN/ZH, desktop/mobile, keyboard and evidence-drawer proof remain required.

An unavailable native/private service is not by itself a bar to separately admitted pure projection or data-free-shell work. Such work must use explicit unavailable inputs, current path custody and existing design law; it must not invent identity, source values, capabilities or an accepted endpoint. Core output-schema freeze still waits for the frozen economic mechanisms. No #7870-only imports on a main-based merge candidate before the shared dependency lands or an accepted stacked topology is used. Preserve the Robotics #7908/#8013 sequencing lesson.

## The same eight tasks

| Task | Current required action |
|---|---|
| T1 | Consume the one accepted shared curation contract: exact/signed measurements, R25 non-theme scope/ref/K1 compatibility and original-source rights mapping through incumbent owners. No parallel schema/codec/store. |
| T2 | Accepted private publication, current rights snapshot, complete dependencies and negative-path proof; schema validity is not permission. |
| T3 | Accepted native K1 subtype with source/recorded clocks and identity-vintage boundaries; no fabricated unified security recipe. |
| T4 | Continue #7984's frozen repair order after permitted recovery/custody. T4b is the internal pure sector projection, not task9 or another economics core. Native adapter qualifies separately. |
| T5 | Accepted incumbent sector-private reader and exact sector/outer-inner join; currently UNBOUND. No forced theme route, new auth/client stack or repurposed Earnings namespace. |
| T6 | Sector-deep-dive entry plus data-free dossier under current design/template custody. Later canonical-theme mounts through #7870 only for accepted anchors. |
| T7 | All five originals/four company journeys, source/company navigation, private evidence and honest missingness; source-only fallback is incomplete. |
| T8 | Independent exact-head review/release, actual private-browser/negative-path proof and unchanged decision outputs. |

AM1 numeric exactness and legacy bytes; AM2 complete source-family mapping; AM3 scope/ref/reader compatibility; AM4 contractual/qualification meaning remain unaccepted shared obligations unless separately proven. H1/H2/H3/H5/H6/H7 open; H4 partial from historical NYSE NTR/WY observations, not four journeys. No issuer/vendor source inherits SEC rights by analogy.

## Frozen implementation, consumer constraints and denials

#7984 resumes only after genuine permitted recovery of the denied cash-write action and incumbent workspace/custody reconciliation: existing cash RED -> minimal GREEN -> strict decimal grammar -> duplicate-role refusal -> strict chronology -> commercial progression and contractual participation -> output schema/wider T4. Run the full Materials targeted file and exposure-map regression after each GREEN. Preserve working missing-quantity-basis refusal; no skipped RED, duplicate carrier, Ready, merge-on-green or core-only V0 claim.

The historical cash patch, R18 reviewer launch, R13 browser/additional identity/alias/delivery and `.local/bin/pool` read denials remain. R23 compound source-policy and R24 current-status-batch refusals were not retried, split or rerouted. A mode, account, provider, host, tool change or unrelated success does not establish recovery. No worker is running by implication of this packet.

R16 consumer constraints remain: AI Brief shared static outputs may not receive full private assertions, private links, holdings or decision snapshots. Public summary approval and external-processor permission are separate from viewing. Old evidence found late is background; corrections name predecessors; unrelated propositions/common-source repeats are not new corroboration. Consensus surprise needs a real earlier comparable consensus. Passed target windows are not completion. Preserve global stance, Prophet rank/selection/entry/weights and membership outputs; no model narrative originates or sizes trades.

## Minimal source and continuation map

Read the cumulative checkpoint `agentos/handoffs/GMI-BASIC-MATERIALS-RESEARCH-2026-09-23.md` for the latest effects. R21 architecture: `research/basic_materials/BASIC_MATERIALS_R21_SECTOR_UMBRELLA_AND_THEME_DRILLDOWN_ARCHITECTURE_2026-09-26.md` (blob `4acb9647da524e628596671fae6e2557b102c7ed`). Full preceding packet/history remain in the immutable revisions at this document's opening.

Shared proposal `research/theme_graph/CURATION_ASSERTION_V1_1_PROPOSAL_2026-09-24.md`: current file-specific branch read still returned blob `ca7223db241b82e13a15ce981716e0c3498f31b2`, identical to the inspected shared tree. No new shared enrollment is inferred. Additional pinned source: outer evidence schema `8f909df8ee4c5858512035d2dfef21eac982a34d`; curation module `9458ec4820095be3df8874f44c784f3ee98bb64c`; rights-filter transport `9cdf988e514eab38d0e2217e394c6e208a11d33a` at `6cd958e92b259f7221690547e7076f4a0de4ed33`.

Preserved requirements/source map: R8 specification `354ac7e305d43be8e4fe2b21dab54cbe2cf60736` and manifest `7aabc80d34278609e717fcbdfef56c080bfc9dce`; R9 44-requirement matrix `6465ff8586bfc6dd38ddbf843cbaae783eb7d5c9`; original implementation plan `dbd993f57fc636ab2675a2ebba3e1e2296064778`; R11 adoption matrix `443a29e64069c029e48aed14a2ea11f51e705257`; R15 complete source index `200fd463cf7f902022dcf14cde7dc24583110737`; R14 worksheet `4da2e39f6ffae09cb25e3cb1a6a15feebdc9d221`; R13 identity observations `3f54410ae6a0caeb36a0698f76a4beb4f48e3e63`; R18 report/qualification and R20 review are linked by the cumulative checkpoint. R16/R17 helper repair and original38 outputs remain research evidence, not production or independent acceptance.

Original Materials compatibility discussion: **#7773 comment5809093547**. Parent visibility: **#7886 comment5846397542**. Neither is a receiver grant; #7870 remains the shared implementation owner. No new compatibility queue, duplicate request or source-custody transfer.

**Primary next action:** the shared owner reviews this concrete source-local proposal within its existing v1.1 amendment and returns accepted scope/ref/K1 signatures and the separately held reader/identity disposition on the original request. Do not repeat the R24 gap probe or reopen the rejected fake-theme alternatives. Materials can advance separately admitted pure projection/data-free-shell work without claiming native input or private serving; #7984's denied action remains frozen. Exact current mode is not inferred; keep the working mode for this adjudication and request a change only for an actual capability/phase reason.
