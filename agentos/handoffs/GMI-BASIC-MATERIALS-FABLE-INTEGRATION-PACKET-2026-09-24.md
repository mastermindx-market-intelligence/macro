---
schema: mastermind.agent_handoff.v1
title: "Basic Materials Economics — Fable integration decision packet"
operation_key: gmi-basic-materials-research-20260923-sol-001
program: gmi-theme-graph
repository: mastermindx-market-intelligence/macro
mission_complete: false
implementation_authority: none
---

# Basic Materials Economics — current Fable implementation handoff

Updated 2026-09-26 through R21. This is the canonical current handoff; it updates the existing packet in place and does not create a parallel handoff/control plane. The prior R17 packet remains at `1474e14f6bb220efdd77f556f70e18040a78f1d6`, blob `ab11564b902c0e9959abb3ae4eeea0bd2c6ec2d1`.

**Prepared for principal integration and independent review, not an unblocked production build.** Preferred avenue Fable for consequential shared-owner integration and acceptance; routine implementation uses the least-scarce capable avenue. CAPACITY_SELECTABLE / WAITING_CAPACITY / needs_placement. No Materials receiver, ACK, START, Executive Attempt or autonomous wake is established. The Semiconductor Fable assignment does not assign Materials.


## R21 architecture checkpoint — read first

**Binding architecture:** Basic Materials is a **sector umbrella**, not one canonical GMI theme. Do **not** mint `theme:basic_materials`, force the sector ETF/basket into theme identity, or register one giant synthetic Materials vertical in #7870.

Read first:
- `research/basic_materials/BASIC_MATERIALS_R21_SECTOR_UMBRELLA_AND_THEME_DRILLDOWN_ARCHITECTURE_2026-09-26.md`
- cumulative Agent OS frontier `agentos/handoffs/GMI-BASIC-MATERIALS-RESEARCH-2026-09-23.md`
- then R20/R18 and the saved implementation plan only as amended by R21.

### V0 topology

1. **Basic Materials sector dossier** is the first served product. It spans all Materials families and all four proof subjects, including unmapped families such as precious-metals financial claims and forest products.
2. **#7984** remains the reusable pure economics core underneath the sector dossier and later canonical-theme drilldowns.
3. **Canonical-theme drilldowns** come later through #7870 only for accepted anchors such as `rare_earth_critical_min`, `copper_steel_electrify`, and `ag_fertilizer`.
4. Families without canonical anchors remain sector/research slices until the ontology owner admits a theme. No Materials worker mints one unilaterally.

### Current carriers

- Research/masterplan: **#7796**, branch `sol/basic-materials-research-20260923`, current R21 head from its live PR/readback.
- T4 core: **#7984**, branch `claude/basic-materials-core-v0`, exact head `36f330b1f7829a289a44937bca0007c734d6df5e`, Draft/HOLD/intentional RED.
- Shared theme foundation: **#7870**, exact inspected head `6cd958e92b259f7221690547e7076f4a0de4ed33`, Draft/HOLD. It now contains the closed `VerticalRegistration`, `MountFacts`, generic API/binding/mount/rights-refresh infrastructure, but has not accepted the Materials AM1–AM4 request.

### Sector precedent and sequencing law

Use the **Finance sector-deep-dive** pattern for V0:
- one Theme Tracker sector-deep-dive card outside canonical theme lanes;
- one data-free Materials dossier shell;
- one Materials-specific Sector Intelligence read model that references existing evidence owners rather than storing evidence itself;
- no rank/stage/score/entry authority.

Consume `sector_dossier_read_model.v1` as the outer sector object where applicable; do not fork it. A Materials-specific inner read model is allowed only as an owner-preserving projection, analogous to Finance's inner read model, with its own Materials domains/slices/mechanisms.

Do **not** repeat Robotics #7908's sequencing defect. #7908 merged before #7870, imported shared modules absent on main, broke first-party-import CI, and was reverted by #8013. Any #7870-dependent Materials theme vertical must be stacked on or land after the actual shared foundation. The sector V0 core/projection must not import #7870-only modules while merging on main.

### Frozen implementation order

**T4 core (#7984):**
- cash-reconciliation RED first;
- strict canonical-decimal RED;
- duplicate-required-role refusal RED;
- strict chronology RED;
- remaining commercial-progression and contractual-participation cases;
- output schema / wider T4 gates only after those are green.

**Sector V0 (after current design/custody review):**
- freeze `basic_materials_intelligence_read_model.v1` as a sector projection; no second evidence store;
- first-release slice catalog comes from R1–R20 families, not a generic theme slug;
- Finance-style data-free shell and sector-deep-dive card;
- private/native adapter consumes existing source/identity/rights owners;
- all five original documents / four company journeys remain mandatory real-path proof.

### Current holds

- #7984 product-write class was blocked before dispatch for the cash patch; EFFECT_NONE, not retry permission.
- #7870 Materials compatibility acceptance is unreturned.
- native retained source/rights/private publication and four-company browser proof remain incomplete.
- no Materials receiver / ACK / START is created by this handoff.

### Handoff execution boundary

This packet is ready for a future Fable/authorized implementation principal to consume. It grants **no** authority by itself. A lawful assignment/placement still requires the normal runtime/admission/custody gates. On pickup, reconcile only changed heads/custody; do not replay R1–R21 research.

## R20 principal review of implementation PR #7984

Read `research/basic_materials/BASIC_MATERIALS_R20_T4_CORE_PRINCIPAL_REVIEW_2026-09-24.md` before continuing T4. The implementation carrier is now real: Macro **#7984**, `claude/basic-materials-core-v0`, exact reviewed head `36f330b1f7829a289a44937bca0007c734d6df5e`, intentionally Draft/HOLD/RED.

The existing cash-reconciliation test remains the next TDD step. Its minimal production patch was platform-blocked before dispatch in R19; no retry/reroute is authorized. Principal read-only probes found three additional defects to convert into RED tests after cash is green: (1) exponent and whitespace numeric text are accepted even though the qualified scalar grammar is plain decimal text; (2) duplicate required metric labels silently overwrite earlier evidence; (3) reversed current/prior periods still emit an economic-change explanation. Missing `quantity_basis` already refuses correctly and must not regress.

Merged Consumer Cyclical V1 core (#7942) is the sibling precedent: deterministic Decimal core may land separately while shared/private/browser legs stay frozen, but merged arithmetic is not the product acceptance ruler. Reuse its generic invariants—deterministic fact pairing, strict chronology, explicit unavailable state—not its sector-specific contract/source envelope.

Frozen repair order when product writes are permitted: existing cash RED -> strict decimal grammar RED -> duplicate-role RED -> chronology RED -> complete targeted + exposure-map non-regression after each GREEN -> output schema only after the four economic mechanisms/denials are stable. T7/T8 real-source/private/browser acceptance remains unchanged.

## R18 sequencing refinement — read before assigning implementation

Read `research/basic_materials/BASIC_MATERIALS_R18_NUMERIC_CORE_AND_SHARED_CONTRACT_BOUNDARY_2026-09-24.md` and `R18_EXISTING_CONTRACT_QUALIFICATION_2026-09-24.json`. Current main at `5600bb63b27978031769eb428911fe9b46572a92` has a Consumer Cyclical read-model scalar convention supporting signed exact decimal text. Twelve actual schema-fragment checks confirmed its representation and its sector-specific limits. Its SEC-only source shape, revenue/expense kinds and comparison scope are NOT a Materials record. Do not copy that contract ID, invent SEC provenance or switch Materials to another evidence owner.

Refine T4 internally: a pure Materials calculation-and-explanation core can be implemented and independently reviewed after a lawful bounded implementation assignment without waiting for private publication. It receives immutable, explicitly scoped arguments and returns economics, explanation and limitations; no I/O, persisted state, source/identity allocation, permission flags, provider calls or routing. Reuse the already-planned F04 consumer/output paths and existing R12–R17 cases. Do not import the research helper as a finished production engine. Native input adaptation still requires accepted GMI/FIF/K1/identity/rights contracts and actual references. A correct arithmetic result is not permission to publish. T7/T8 still require all five originals/four real company journeys and private-browser proof; core-only progress does not become a completed V0 release. No product writes are granted on #7796.

R18 independent-review disposition: full-packet operator selection returned no eligible operator. A separately bounded fixed-invariant audit reached native MiniMax remote selection and a successful dry run, but its actual launch was blocked by OpenAI safety checks BEFORE dispatch. No reviewer process, ACK, START, output or served-model proof exists. Do not retry, rephrase, change tools/providers or use another host to get that blocked effect through; platform-permitted recovery is required. The separate R13 browser/identity-action and `.local/bin/pool` file-read denials remain intact. No review verdict is inferred from the 12 schema checks.

The R17 local-Qwen failure and R18 platform launch denial are different facts. The permitted kit's remote-placement policy explains why local execution is inappropriate; it does not override the later platform denial. Routine placement still belongs to the existing owner. A later actual implementation assignment must preserve the current source and runtime gates rather than silently converting this research packet into a worker grant.

## R17 review result — preserved correction

Principal review found and repaired one actual R16 reference-code defect: background/correction return paths bypassed R16-C07's comparison prerequisites. The updated existing `R16_CHANGE_CONTENT_EXERCISE_2026-09-24.py` applies those prerequisites before any text-bearing path. See `research/basic_materials/BASIC_MATERIALS_R17_REVIEW_FINDING_AND_DISPOSITION_2026-09-24.md`, `R17_COMPARISON_GUARD_TESTS_2026-09-24.py` and `R17_REVIEW_AND_REPAIR_VERIFICATION_2026-09-24.json`. Twenty regression failures on the parent become zero; the original38 complete outputs are unchanged. This corrects a research utility, not production behavior. R17 also removes the packet's mistaken Chairman-only delivery sentence: the existing authorized Sol/placement paths remain valid, without creating any actual assignment.

An independent worker review was attempted through the existing pool owner but did **not** start. Native planning/pick offered Qwen; local `pool run qwen` ended78 with `LOCAL_SEAT_REMOTE_REQUIRED`, while the remote host selector does not support qwen. No reviewer ACK/START/result exists, no alternative provider was used to evade that gate, and the seven staged input files remained unchanged. Independent review therefore remains owed, not replaced by the author's repair. Its routing recovery belongs to the existing pool/placement owner, not a new queue or direct provider call.

R16-C07 now explicitly applies to background/corrections as well as current observations. Preserve an independent noncomparative fact only through separately reviewed wording; do not remove a comparison tag while retaining unsupported comparative language. All44 core requirements and the shared-foundation holds remain unchanged. Review the corrected current packet rather than the staged pre-correction snapshot.

## Mission and preserved scope

Deliver Materials Economics inside the existing Themes/sector-to-company workflow: what changed, which operating business or financial right captures it, what can reach retained cash/per-share economics, what was expected, and what evidence matters next. The five selected originals across Nutrien, NOVONIX (two), Wheaton/Antamina and Weyerhaeuser must each retain their correct scope. Full acceptance includes lawful company navigation and actual source-to-private-browser proof, not source-only fallback.

Sol retains Materials principal responsibility. Macro #7796 / `sol/basic-materials-research-20260923` remains research-only Draft/HOLD; no merge, rebase, replacement or product code on this carrier. Re-pin protected procedure and actual shared source/custody before effects. This packet creates no worker or authority grant. A receiver needs a current bounded assignment through live Chairman delivery, an authorized Sol direct handoff, or the existing canonical placement owner, with the applicable admission and custody gates. Merely reading this packet grants none. Routine placement does not require another Chairman ceremony.

Preserve all44 core requirements, eight tasks, seven open/partial gates, ten research navigation families, eight economic lenses and V0–V4 ambition: explanation, comparable changes, conditional economics, evaluated discovery, broader global coverage/learning. Research context does not rank, gate, originate, size or open trades. No new evidence/identity/correction/permissions/store/publisher/client/evaluation/queue control system.

## Read only the necessary exact sources

1. R18 sequencing/contract qualification above, then current cumulative frontier: `agentos/handoffs/GMI-BASIC-MATERIALS-RESEARCH-2026-09-23.md`. It owns last effects, denials, source pins and exact next action.
2. R16 consumer decisions: `research/basic_materials/BASIC_MATERIALS_R16_ECONOMIC_CHANGE_TO_EXISTING_CONSUMERS_2026-09-24.md`, with its38 synthetic-case exercise/tests/verification. No native permission or model performance is implied.
3. R11 foundation-adoption amendment and `R11_FOUNDATION_ADOPTION_MATRIX_2026-09-24.json` (blob `443a29e64069c029e48aed14a2ea11f51e705257`) BEFORE the older implementation steps. They supersede the standalone Materials API/client and shared-code duplication.
4. Saved plan: `docs/superpowers/plans/2026-09-23-basic-materials-economics-v0-implementation.md`, blob `dbd993f57fc636ab2675a2ebba3e1e2296064778`; R9 matrix blob `6465ff8586bfc6dd38ddbf843cbaae783eb7d5c9` preserves all44 core requirements.
5. R15 complete selected-source index `R15_REMAINING_SOURCE_REVIEW_AND_PROOF_SET_2026-09-24.json`, blob `200fd463cf7f902022dcf14cde7dc24583110737`; references unchanged R14 worksheet `4da2e39f6ffae09cb25e3cb1a6a15feebdc9d221` rather than duplicating it.
6. R13 native identity observations blob `3f54410ae6a0caeb36a0698f76a4beb4f48e3e63`; R12 economic reference set for expected answers, not an independent holdout.
7. R8 integrated specification blob `354ac7e305d43be8e4fe2b21dab54cbe2cf60736` and manifest `7aabc80d34278609e717fcbdfef56c080bfc9dce` locate the full family research/source registers. Read a family annex only when its economic interpretation is disputed; do not repeat R1–R15 surveys.

All research filenames not otherwise qualified are under `research/basic_materials/`. Exact committed versions remain on this one carrier.

## Shared foundation and revised eight tasks

Consume #7870, not another Materials base. R17 inspection: `e2f4d490915660fc6db64d750505309343e9e0e8`, open/draft/unmerged. Schema `ff3928f0c54aa164ef8283d9da45af67e6a0d971` remains unchanged. The prior R16 owner checkpoint reported R4 architecture accepted with qualifications and private-publication/projection/rights findings. Those detailed findings were not requalified in R17 and must not be projected as newly verified defects. Current Materials compatibility and deployed private acceptance remain unestablished. AM1–AM4 acceptance is unestablished; original same-discussion request5809093547 remains, not a new dispatch.

| Task | Required action |
|---|---|
| T1 | Consume one shared curation contract; close exact/signed/fractional measurement and original-input rights mapping through its owner. |
| T2 | Consume accepted private publication and fresh rights snapshot; prove strict failure states, complete source dependencies and current permission at emission. |
| T3 | Consume the same K1 subtype without losing source/recorded clocks or inventing a unified security recipe. |
| T4 | Implement the pure Materials F04 calculation/explanation core after lawful assignment; qualify its native-input adapter separately under accepted contracts. Preserve company/financial-right and economic scope. Core-only success is not V0 acceptance. |
| T5 | Extend the accepted shared POST research query/evidence interface with a closed Materials profile; no standalone Materials endpoint or auth path. |
| T6 | Extend the shared theme-research client and accepted mounts; no duplicated network client, template or global theme identity. |
| T7 | Rehearse all five real sources/four company journeys, including missing-data cases, native review and actual identity/route evidence. |
| T8 | Obtain independent exact-head review/release, actual private-browser proof and unchanged decision-output evidence. |

AM1 preserves legacy bytes when optional measurement is absent; exact values cannot pass through floats or dual populated branches. AM2 must not treat unresolved source families as an empty allowed set. AM3 must not force Materials into the two Semiconductor slices. AM4 must not turn contractual participation into ownership/additional physical supply or an MOU into qualification.

H1 shared compatibility, H2 store custody, H3 accepted private profile/proof, H5 detail custody, H6 independent release and H7 actual source retention/rights/review stay open. H4 is partial from two NYSE identities, not four completed journeys. R13 Canadian Nutrien remains unresolved. Source declarations, native identity, collection coverage and published routes are separate evidence. Preserve the existing #7462/#7669 custody unless their current owners explicitly reconcile it.

## R16 consumer constraints

Current source pin `ee908cb8f0b591a693d6de18fdf6e7ad314f1108` identifies `engine/master_brain.py`, `scripts/build_aibrief.py`, `_aibrief_body.html.j2`, `desk_ledger.py` and the closed Company Theme Exposure contract. AI Brief has shared static outputs. Do not send full private assertions, private links, holdings or decision snapshots there. Public summary approval and external-processor permission are independent from private viewing. No provider/credential call is authorized here.

Source novelty is not a fresh build ID. Old evidence found late is background; corrections target exact predecessors; unrelated propositions and common-source repeats remain separate. A consensus-surprise claim needs actual earlier comparable consensus. A target window passing is not completion. Date-only actual source calendars need qualification; the synthetic exercise's UTC dates do not supply it.

Keep global stance, Prophet selection/rank/entry/weights and membership projection unchanged. The16 mapped R16 requirements refine T3–T8; later brief/notification adoption is not an excuse to withhold the V0 private dossier. The offline helper is a development reference exercise, not production code or another permissions gate.

## Acceptance and current limits

Actual completion requires retained originals, native review/admission, correct measurement/identity generations, current permitted representations, paid authorization before private reads, working sources/company pages and desktop/mobile, EN/ZH, dark/light and keyboard proof. Denied/public/cache/alternate-path cases must not expose private bodies or source existence. CI, a shared merge or a screenshot alone is insufficient.

R12/R15/R16 tests are research exercises, not independent semantic review or predicted returns. All new native source/retention/current-rights/production/route receipts remain absent until supplied by their owners. R13 browser and additional identity/delivery actions were platform-denied before dispatch and must not be retried/reframed/rerouted absent actual permitted recovery. No full original reports or protected production payloads are in this packet.

## Exact next action

After an actual bounded implementation assignment, build and review the T4 pure calculation-and-explanation core against the existing cases and current F04 ownership. In parallel, resolve the accepted shared exact-measure/private/profile and native-input adapter decisions; only then rehearse real admitted cases through private delivery. The blocked R18 review launch cannot be retried or rerouted without permitted recovery. Full-packet independent review and all T7/T8 proof remain owed. Do not repeat source worksheets or equivalent fixture expansion. No response grants takeover of the shared writer. This packet itself creates no receiver, START or product-write grant.
