# GMI D2D — first lithium / storage curation review

## Outcome and authority

Five previously unmapped, no-proposal local concepts now have source-code-bound evidence-review dispositions: **two nonexclusive `EXPRESSES` candidates, one application-scope hold, and two source-membership receipts with unresolved owner-basket binding**. Two standard proposal drafts can be inspected through the existing worklist and proposal-review consumers. **No draft was added to the canonical queue, no proposal was ratified, and no graph mapping changed.** This packet is research evidence, not a second curation ledger or approval system.

The active operation remains `gmi-theme-ontology-d2d-20260827-sol-001`, macro PR #7462. The source reader commit is `d9734be7e9a1c3fbf96b8dbeaefb31bffe651ee3`; governing procedure is protected Mastermind `ce18ed4f1eaa28e65a616a90aecca5c5ce1c5a2e`. Sol retains source/release custody. The Chairman prioritized build-forward work over waiting for CI; release checks remain deferred, not waived.

## What was reviewed

The cohort was deliberately selected from the completed inventory: lithium batteries, power-battery recycling, solid-state batteries, sodium-ion batteries and vanadium batteries. It is not an exhaustive battery universe, ranking or representative statistical sample. Labels assisted research selection only. Every lookup, membership and proposal identity uses exact recorded IDs.

Both requested graph clocks are 2026-09-21. The stored graph was generated at **2026-09-18T17:42:29Z**; this review does not claim new production data. The current stored THS concept map is dated 2026-09-05. Primary-source research below is separately attributed and does not replace the owner records.

| Exact local concept | Source label | Recorded member paths | Shared with storage control | Research disposition |
| --- | --- | --- | --- | --- |
| `ltheme:ths:300733` | 锂电池概念 | No recorded graph member path | Not comparable | Raw source membership receipts exist; stable owner `basket_id` is absent. Do not fabricate a graph or canonical mapping. |
| `ltheme:ths:307822` | 动力电池回收 | No recorded graph member path | Not comparable | Raw source membership receipts exist; stable owner `basket_id` is absent. Recycling is not automatically extraction or grid storage. |
| `ltheme:ths:308294` | 固态电池 | 12 distinct graph companies | 5 of the 15-member control | **Application-scope hold**; exact THS definition does not establish grid-specific use, so overlap cannot promote it to a candidate. |
| `ltheme:ths:301096` | 钠离子电池 | 20 distinct graph companies | 2 of the 15-member control | **Nonexclusive `EXPRESSES` candidate**; exact THS definition explicitly spans grid/renewable storage and electric transport. |
| `ltheme:ths:301174` | 钒电池 | 16 distinct graph companies | 1 of the 15-member control | **Nonexclusive `EXPRESSES` candidate**; exact THS definition places vanadium redox-flow batteries in long-duration storage context. |

“Recorded member paths” counts distinct graph-company IDs reached through the existing `MEMBER_OF → EXPRESSES` path. It does not imply a complete vendor universe, unified issuer/security coverage or direct local-theme membership. Both edge receipts, their clocks, rights and intermediate basket IDs are retained in `facts.json`. No fuzzy ticker or label join was performed.

The two missing-path concepts exist in the source-code map, but no corresponding member path was found in the stored graph. Their comparisons are **null/not comparable**, not zero-overlap findings. The current `membership.json` has no lithium-battery or recycling `ths_concept` basket binding; no similarly named basket was substituted. Separate raw THS snapshots do contain label-keyed memberships, documented below, but D2C correctly refuses `ths_concept_dump` rows as graph membership because their concept→basket resolution is current-basis.

## Controls and why they matter

`ltheme:ths:306380` (储能) is already mapped to `theme:grid_electrification` and has 15 recorded companies through `ths_storage_ess`. Its owner basket describes grid / behind-the-meter storage. It is a specific local control, **not the whole canonical theme's member universe**.

`ltheme:ths:308991` (钙钛矿电池) is already mapped to `theme:solar` and has 16 recorded companies. The solid-state, sodium-ion and vanadium cohorts share 1, 0 and 0 names with it respectively. This is a useful label-collision control: a battery-related label does not establish the same application or canonical mapping.

`ltheme:ths:307904` (盐湖提锂) is already mapped to `theme:rare_earth_critical_min`, but this stored graph has no recorded member path for it. **Mapping coverage and member evidence are different dimensions.** Its mapping cannot justify assigning lithium-battery or recycling concepts to Critical Minerals by name association.

All three existing mapped controls remain untouched. Shared-name counts are descriptive observations, not mapping scores, statistical significance, causal evidence or investment priority.

## Primary-source scope check — distinct from graph facts

**Vanadium:** the exact THS definition for source code `301174` / displayed index `886003` describes vanadium redox-flow batteries and explicitly situates flow batteries in long-duration/new-energy storage [S9]. DOE's August 4, 2017 Painesville report independently documents a grid application [S1]. Together these support a **nonexclusive Grid & Electrification `EXPRESSES` candidate**, independently of the one shared company; they do not establish equivalence or every issuer exposure.

**Sodium-ion:** the exact THS definition for source code `301096` / displayed index `885928` explicitly names grid storage, renewable-energy storage and electric transport [S8]. DOE separately documents grid storage [S2] and EV/storage research [S3]. This supports a **nonexclusive Grid & Electrification `EXPRESSES` candidate**, while directly ruling out an exclusive grid interpretation.

**Solid-state:** the exact THS definition for source code `308294` / displayed index `886032` defines the battery technology but does **not** establish grid-specific application scope [S7]. ORNL lists vehicle, grid, portable-electronics and aerospace applications for its described technology [S4]. The five shared storage-control names therefore remain descriptive and cannot substitute for the missing semantic scope. **Disposition: application-scope hold; no proposal draft is retained.**

The five THS pages are exact source-code-bound definition receipts [S5–S9]. They establish board-definition scope only; the definition pages themselves are not dated membership receipts, issuer exposure measurements, current market forecasts, or redistribution permission. Dated membership evidence comes separately from the stored raw THS snapshots below and still does not create a stable owner basket binding.

## Source-native membership receipts — evidence present, owner binding absent

The stored THS raw concept snapshots provide genuine point-in-time **label-keyed** member sets for both missing graph concepts. For `锂电池概念`, counts are 10 on 2026-06-30 and 50 on each of 2026-08-22, 2026-08-29 and 2026-09-05. For `动力电池回收`, counts are 20, 50, 50 and 50 on those same dates. `facts.json` records each snapshot path, file SHA256, member count and normalized member-set SHA256.

This closes the narrow claim “no source membership receipt exists,” but **does not close graph admission**. The raw snapshot shape is `ths_concept_dump`; `engine/basket_membership_pit.py` states that its members are point-in-time while concept→basket resolution is current-basis. Current `data/baskets_china_ths/membership.json` tracks 237 THS concepts and binds neither of these labels to a `basket_id`. The current `concept_map.json` binds the labels to source codes `300733` and `307822` only as of **2026-09-05**.

D2C therefore intentionally excludes all `ths_concept_dump` rows from theme-graph `MEMBER_OF` truth: admitting them would backdate a mapping not historically possessed. The correct remaining gate is a curated stable owner-basket binding under the existing THS source owner, followed by the owner's lawful forward-only process. This packet does **not** create that binding and does not write graph or queue state.

## Drafts and the existing consumer path

The two retained drafts use the existing probation schema and `proposal_id(kind, subject)` identity function. Their proposer is honestly `llm_proposed`, status remains `proposed`, and `ratified_by` / `adjudicated_at` remain null. They propose `EXPRESSES`, **not EQUIVALENT or IS_A**.

| Local node | Draft proposal ID | Candidate target |
| --- | --- | --- |
| `ltheme:ths:301096` | `prop:de400c2bb566c04c` | `theme:grid_electrification` |
| `ltheme:ths:301174` | `prop:a1b11d839c5d789d` | `theme:grid_electrification` |

`draft-worklist-preview.json` and `draft-review-previews.json` carry an explicit **UNPUBLISHED_DRAFT_OVERLAY_NOT_CANONICAL_QUEUE** envelope. The existing consumer functions operated on a detached in-memory overlay: 234 canonical rows plus two drafts. Both returned exact `review_query` values opened their drafts with `RELATION_ABSENT`. This is not a raw canonical-file CLI proof for newly queued proposals. The actual canonical queue remains 234 rows, and all five concepts still have no canonical proposal.

The standard overlap-export consumer was not used to turn these two-hop paths into direct-membership claims. The retained path evidence and exact local-control comparisons are the basis of this batch.

## Verification and reproducibility

Sixteen actual `query_theme_ontology.py` subprocess calls produced sixteen schema-valid exact-node exports. The command list and file digests are in `facts.json`. Two detached worklist-to-review round trips passed. Seven deliberate attacks were detected: replacing missing evidence with zero, inflating overlap, relabeling a local control as the whole theme, inventing a member, forging a proposal's subject under the same ID, ratifying without authority, and claiming nonexistent queue admission.

Run the read-only frozen-packet check from this repository:

```bash
python3 research/prophet_v4/d2/curation/lithium-storage-2026-09-21/check_review.py
```

The verifier uses existing owner validators/consumers, checks exported path receipts and exact arithmetic, and compares all eleven canonical input hashes. It writes no files. Evidence remains bound to the source snapshot; a changed input requires a new research vintage, not editing this one into apparent freshness.

No production reader, graph, crosswalk, identity owner or queue implementation changed in this batch. The earlier 704-test suite result belongs to the predecessor source proof and is not presented as a new run. CI was not polled, restarted or waived.

## Remaining decisions and exact next action

Before any queue admission or curated ratification, independently review the **two retained nonexclusive candidates**. Keep solid-state on **application-scope hold** unless new exact evidence resolves grid relevance. For the two missing-path concepts, the raw dated source receipts are now present. The remaining gate is independent source-owner curation of a stable exact `basket_id` binding; never import the raw dump directly, backdate that binding, or populate the graph from a near-name match. A source-backed abstention remains a valid outcome.

The previous code-review request did not yield approval: the native reviewer failed to resolve the published d9734be ref (comment 5761538658). That is a reviewer ref-resolution failure, not proof the source was absent from GitHub and not a passing review. Reconcile on the same PR before a changed-head review request. Latest-base integration, applicable CI and required independent acceptance still gate release.

Full D2D, D2E, sole ThemeState W3B and cohort W3C remain incomplete. The separate four identity-baseline failures and the graph-only THS concept 309263 remain unwaived and untouched.

## Primary sources

[S1] U.S. Department of Energy, Office of Electricity. Painesville vanadium-redox demonstration, August 4, 2017. https://www.energy.gov/oe/articles/arra-sgdp-city-painesville-ohio-vanadium-redox-battery-demonstration-program

[S2] U.S. Department of Energy, Office of Electricity. Aquion sodium-ion grid application, August 4, 2017. https://www.energy.gov/oe/articles/arra-sgdp-aquion-energy-sodium-ion-battery-grid-level-applications

[S3] U.S. Department of Energy, Basic Energy Sciences. Sodium-ion battery research for electric vehicles and storage, October 16, 2023. https://www.energy.gov/science/bes/articles/scientists-find-potential-key-longer-lasting-sodium-batteries-electric

[S4] Oak Ridge National Laboratory. Solid-state batteries using single-ion-conducting polymer electrolyte and engineered interface, updated October 29, 2025. https://www.ornl.gov/technology/202405807

The four DOE/ORNL sources were checked on September 21, 2026. Dates above are publication/update dates, not claims of new events today.

[S5] 同花顺 (Hithink RoyalFlush). Lithium battery concept, source code `300733`, displayed index `885710`. https://q.10jqka.com.cn/gn/detail/code/300733/

[S6] 同花顺 (Hithink RoyalFlush). Power-battery recycling concept, source code `307822`, displayed index `885944`. https://q.10jqka.com.cn/gn/detail/code/307822/

[S7] 同花顺 (Hithink RoyalFlush). Solid-state battery concept, source code `308294`, displayed index `886032`. https://q.10jqka.com.cn/gn/detail/code/308294/

[S8] 同花顺 (Hithink RoyalFlush). Sodium-ion battery concept, source code `301096`, displayed index `885928`. https://q.10jqka.com.cn/gn/detail/code/301096/

[S9] 同花顺 (Hithink RoyalFlush). Vanadium battery concept, source code `301174`, displayed index `886003`. https://q.10jqka.com.cn/gn/detail/code/301174/

The five THS definition pages were observed on September 21, 2026. The pages do not supply definition publication dates; that observation date must not be backdated to the September 18 graph. No constituent list or price data from these pages was imported.
