# D2D — applied rejection receipts for two lithium/storage mappings

## 0. Scope, decision and authority

This packet applies the parent-adjudicated **REJECT** disposition to the existing probation owner in a source candidate branch. It is a curation decision, not full D2D acceptance or production proof. No runtime graph was written. Root owns commit, PR, independent source review and the remaining acceptance chain.

Independent semantic reviewer: **/root/d2d_curation**, concluded **2026-10-04T00:33:06Z**. The accepted temporary report SHA256 is **fc076ee1b52f37d807aa4c41a579bc1674323cad83d6d1abacf7c79dce0bc13c**. [Parent decision receipt](https://github.com/mastermindx-market-intelligence/macro/pull/8324#issuecomment-5975054698) was recorded **2026-10-04T00:38:00Z** and is reproduced in admission.json. Applied curator: **/root/evaluation_capture**, delegated by Astra parent /root under **gmi-d2d-curation-decisions-20261004-astra-001**. Current protected procedure pin: **c776f8dc8d3dabb0070b51ad7f04d71987ff6df1**. Exact Macro source base: **7593bb1424477a880d24528eece5366b1ec41209**.

| Existing proposal identity | Exact local subject | Target | Applied disposition |
| --- | --- | --- | --- |
| prop:de400c2bb566c04c | ltheme:ths:301096 | theme:grid_electrification | rejected; ratified_by=null |
| prop:a1b11d839c5d789d | ltheme:ths:301174 | theme:grid_electrification | rejected; ratified_by=null |

Both local concepts remain unmapped; their recorded grid-application facts and exact source identities are preserved. Solid-state ltheme:ths:308294 retains its application-scope HOLD. Lithium-battery 300733 and recycling 307822 remain OWNER_BASKET_NOT_BOUND. Existing mapped controls 306380/308991/307904 and their crosswalk rows are unchanged.

## 1. Semantic basis and historical ancestry

contracts/theme_graph/README.md:103–107 defines local→canonical EXPRESSES as vocabulary resolution: vendor concept and canonical theme name the same thing. engine/theme_graph/materialize.py:1099–1120 implements that meaning. The original sodium-ion and vanadium drafts establish narrower, nonexclusive grid/storage applications and disclaim identity. Application facts do not justify the offered canonical vocabulary mappings. Adding their ths_concept_ids would also express entire matching owner baskets in canonical terms.

The September 21 [drafts](../lithium-storage-2026-09-21/draft-proposals.json) and every file in that frozen review directory are byte-preserved. Each new row retains its proposal_id, kind, subject, proposed_by, original note, evidence_refs and original evidence fields. The prior canonical_queue_admission=false is retained within the complete immutable draft_ancestry.original_record; the admitted source row now records canonical_queue_admission=true with stage SOURCE_BRANCH_CANDIDATE_NOT_MAIN. Original draft_created=2026-09-21, source_head, graph-generated clock, scope receipts, source IDs and descriptive overlaps retain their historical meanings. The September asof/knowledge_cutoff in evidence describe that research vintage, not today's queue admission or current constituents.

THS remains rights_class=unresolved and auth_class=receipted_scrape. House curation preserves external source parents and does not grant public/new GMI emission, source redistribution, grandfathered-owner permission or economic exposure. No sources or rights registry changed.

## 2. Admission clocks and preservation

The actual candidate-branch admission and applied decision use **2026-10-04T00:51:55.181207Z** for created and adjudicated_at. They are the same bounded curator act; no claim is made that the drafts were queued on September 21. The earlier independent review and parent ruling clocks are recorded separately. Commit/main adoption, ordinary graph consumption and exact-head review remain pending.

The original full queue contains **234 proposed rows / 205,671 bytes**, SHA256 **8ce0d428bb8d3d3164430da316f615e16bce1c188a0e4412ed3bcbca6c37632c**. It remains an exact byte prefix. The candidate now contains **236 rows: 234 proposed, 2 rejected, 0 ratified**. Both new rows use the existing rejected enum and null ratified_by; no rejected_by field, authority placeholder, relationship or separate queue was introduced. The incumbent append_proposals returned (2, 0). Its keep-FIRST behavior would not update an existing ID; the complete strict queue was re-read and both IDs were absent immediately before append.

Only data/theme_graph/probation was materialized via scoped git sparse-checkout add before reading; the recovered queue exactly matched HEAD. site/mockups/verify_shots remain excluded. MM_DATA_GUARD was not disabled.

## 9. Verification, limits and remaining gates

[admission.json](admission.json) records queue digests, clocks, original-file hashes and unchanged crosswalk/materializer/probation/schema/rights sources. [reader-witness.json](reader-witness.json) records the four actual read-only list_theme_proposals CLI calls over the branch's full queue, validated against the existing output schema. The 2026-10-03 cutoff hides both new rows; the 2026-10-04 cutoff returns both as rejected. Output schemas were resolved through a fail-closed offline Registry of committed contract files after the initial validator attempted website retrieval and received HTTP401. No schema was changed and no second append occurred. Complete input validation used the incumbent probation schema and probation.require_valid_rows, including deterministic identities and duplicate rejection.

The incumbent reader parses precise UTC admission/decision stamps but selects proposal visibility by UTC **date**. A same-day cutoff cannot represent a time before this admission; only the preceding day is a valid before-admission witness here. Precise stored clocks do not establish intraday reader resolution.

The two proposal-review reader round trips use an explicitly isolated fixture: three unchanged September endpoint projections plus empty edges/lifecycle, and the current branch queue. Current fixture endpoints remain local/unmapped and the offered relations are absent. This proves consumer behavior only. It is not current canonical Parquet proof, a natural graph build or a production census. The current source crosswalk independently omits both target codes and remains byte-unchanged; the graph producer excludes all unratified rows.

No new tests or test implementation were written, no frozen research verifier was reinterpreted as a current proof, and no provider/data refresh was run. These two dispositions are proposal-grain counts, not node coverage or predictive evidence. Full D2D, natural graph/reader consumption, structural owner binding, independent exact-head review, D2E current rights/measurement coverage and W3B/W3C release remain held. Rank, gate, size, origination and escalation authority remain false.
