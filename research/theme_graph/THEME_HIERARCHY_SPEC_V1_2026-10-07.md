# GMI Theme Hierarchy & Multi-Axis Classification — FROZEN SPEC V1 (2026-10-07)

Status: FROZEN by the GMI Meta-CEO seat (session 6f14c2da, Chairman-delegated 2026-10-06/07) under WS:GMI-THEME-GRAPH.
Decision record: DEC:GMI-THEME-HIERARCHY-ON-CROSSWALK. Thawing any clause below restarts the affected wave.
Inputs: census v2 + round-2 census + 3-angle design panel + red-team judge (seat scratch, 2026-10-07); freeze doc
`research/theme_graph/THEME_GRAPH_END_TO_END_COMPLETION_FREEZE_2026-08-27.md`; Chairman gates #2/#3/#4/#5/#8.

## 0. Acceptance gates (every wave is NOT DONE UNLESS these hold)
1. No new store, producer, selection store, ThemeState owner, rights resolver, publication control plane, lobe or
   vocabulary family (Gate #8, G0.9). Hierarchy lives ONLY in `config/theme_crosswalk.yml` and is emitted ONLY by the
   incumbent producer `engine/theme_graph/materialize.py` into `data/theme_graph/{nodes,edges}.parquet`.
2. With the hierarchy block empty or absent, `nodes.parquet` and `edges.parquet` are byte-identical to the pre-change
   producer on the same inputs (prove it with a fixture build, never a full local rebake —
   DSC:THEME-GRAPH-FULL-REBAKE-DIVERGES-LOCALLY).
3. No vendor family (`finviz_themes`, `ths_concepts`) contributes any node id, label, parent, or structure (Gate #2:
   "Do not use an internal-only vendor input to launder restricted structure into a house-owned output").
4. No per-ticker stored tag/exposure (DNR:HOLD-TICKER-EXPOSURE-TAGS). Semantic membership is group-level only.
5. Display-tier only: no rank/size/gate/score consumes the hierarchy until gauntleted (G0.1 no fused score).
6. LLMs may only PROPOSE (probation `proposed_by=llm_proposed`); only the operator or a delegated curation session
   ratifies; only a reviewed crosswalk PR materializes an edge (A7 / G0.6).

## 1. Tiers (node level)
- All hierarchy nodes are `kind=theme`, id `theme:<slug>`, slug grammar `^[a-z0-9][a-z0-9_]{1,62}$`, globally unique
  across all tiers (a slug may not be reused by a different tier).
- `tier` ∈ {`macro_category`, `theme`, `micro_theme`} and is REQUIRED (non-null) when `kind=theme`. The existing 18
  crosswalk `themes:` rows are tier `theme` and are NOT modified. Non-theme node kinds are unchanged.
- Rights: hierarchy nodes resolve to family `mastermind_curated` (`direct_display_ok`, licensing (T,T,T)) exactly as the
  existing theme nodes do. No new prefix, no new rights row.
- New-tier nodes (`macro_category`, `micro_theme`) carry NO `EXPRESSES` and NO `MEMBER_OF` edges in V1. Wiring baskets to
  micro-themes is a later wave gated on the consumer tier-guard (W-C2b) and recorded per consumer.

## 2. Edges
- Type `PARENT_OF` only (already in the edges.v1 enum). Direction: `src` = PARENT, `dst` = CHILD.
- Tier adjacency: `macro_category → theme` or `theme → micro_theme`. Nothing else (no category→micro, no theme→theme).
- Graph is a DAG; a node may have at most 3 parents; a `theme` may have zero categories (allowed).
- Fields: `source_class=curated`, `date_provenance=crosswalk`, `valid_from = asserted_on` of the parent row,
  evidence = operator curation of `config/theme_crosswalk.yml` (same evidence shape as crosswalk EXPRESSES), `era` per
  the producer's run-era semantics (a curated PARENT_OF is never promotion evidence). NO weight/share/count/score field.
- `edge_id` follows the existing grammar `<type>:<src>-><dst>@<valid_from>`.
- Typed polyhierarchy vocabulary from the #8324 blueprint (EQUIVALENT / NARROWER_THAN / BROADER_THAN / OVERLAPS /
  RELATED_NOT_EQUIVALENT / NO_CANONICAL_MAPPING / PENDING_ADJUDICATION / REJECTED) stays probation/mapping vocabulary;
  it is NOT a graph edge type in V1.

## 3. Store — crosswalk `hierarchy:` block (additive; crosswalk `version` stays 3, document `date` is NEVER bumped)
```yaml
hierarchy:
  categories:            # tier macro_category
    - id: <slug>
      name_en: <str>
      name_zh: <str>
      asserted_on: YYYY-MM-DD
      note: <str, optional>
  micro_themes:          # tier micro_theme
    - id: <slug>
      name_en: <str>
      name_zh: <str>
      asserted_on: YYYY-MM-DD
      nominated_from: <house source ref: basket:<id> | vertical:<registry>:<slice> | research:<path> >
      note: <str, optional>
  parents:
    - parent: <slug>     # a categories id or a themes id
      child: <slug>      # a themes id or a micro_themes id
      asserted_on: YYYY-MM-DD
```
- `asserted_on` is REQUIRED per entry; must be ≥ HIERARCHY_EPOCH `2026-10-07`; an entry whose `asserted_on` is after the
  build as-of date is NOT emitted yet (PIT). Bumping the document `date:` is forbidden (it re-ids every EXPRESSES edge).
- Producer refusals (typed `ThemeHierarchyError`, raised — the CI crosswalk test keeps a broken block off main): cycle;
  non-adjacent tiers; endpoint not declared (in `themes:` or the block); duplicate id or cross-tier id reuse; missing or
  pre-epoch `asserted_on`; any weight/share/count/score key; >3 parents; a new-tier id referenced by any basket/EXPRESSES
  map; a `nominated_from` naming a vendor family (finviz/ths).
- Withdrawal: deleting a `parents` row ends that edge exactly as a withdrawn crosswalk EXPRESSES edge ends today; the
  existing v2 relation-event WITHDRAW path must also accept a curated PARENT_OF prior; DESTINATION_CHANGE on PARENT_OF
  is refused with a typed reason; the contradiction scan covers PARENT_OF (withdrawn-by-event but still in YAML →
  typed contradiction notice, never silent re-emission).
- The stale comment at `materialize.py` ~:840-842 ("PARENT_OF edges are W4's") is replaced: PARENT_OF is GMI-owned on
  the incumbent producer (seat ruling 2026-10-07; freeze doc retires standalone W4).

## 4. Admission (how a new category/micro/parent gets in)
nominators (house research, house baskets, incumbent vertical registries, LLM) → OPTIONAL probation row of kind
`hierarchy` (a review queue only) → `ratified_by` (operator or delegated curation session; never an LLM) → a reviewed
crosswalk PR (the ONLY act that materializes an edge). Vendor taxonomies are not nominators in V1.

## 5. Federation (no vocabulary N+1)
- Incumbent vertical vocabularies federate by identity, never by copy: a vertical's slice that is a semantic subtheme
  is admitted as a `micro_theme` whose slug EQUALS the vertical's slice key, with a parity test.
- #7870 (Semiconductors, owner of the shared theme-graph/evidence/rights BASE): crosswalk is canonical for micro-theme
  ids; #7870's `VerticalRegistration.slice_keys` must be ⊆ crosswalk micro_themes under its `anchor_theme_id`
  (W-C5, parity test, needs the #7870 owner's countersign; until then the two slices are seeded with identical slugs).
- Finance R11 (52 slices / 7 domains): NOT federated in V1 (owner status conflicting: WS says active, seat memory says
  paused). No house micro-theme may be minted under `fintech_payments` that duplicates an R11 slice concept.
- Biocatalyst / GovRev / Defense archetypes: entity ontologies, not theme grain — no federation in V1.
- #7283 (house Theme Atlas): DISTINCT display surface owned by STSI; basket `category` ≠ canonical theme; semantic
  parents come only from GMI PARENT_OF.

## 6. Multi-axis classification (read-time composition — no stored per-ticker tags)
Axes: (A) semantic theme path macro_category → theme → micro_theme (this spec); (B) sector/industry via the bound owner
`intelligence_workspace.resolve_current_industry_relationship` (read-time `us_industry` id, never a theme node);
(C) market/geography (existing US/CN/HK scopes). Composition happens at READ time in
`engine/theme_graph/structural_navigation.py` (`hierarchy_paths(node_id, asof)`), keyed basket → theme → category with
no weight; a ticker's path is derived through its basket membership at read time, never stored as a tag list.
G0.13's four objects stay separate: semantic membership (group-level), economic exposure (null), trading exposure (W2,
unchanged), basket weight (labelled construction).

## 7. Consumer order (all display-tier)
**Records correction, 2026-10-08 — R-J.10/R9 and merged E1 Amendment A1.** W-C2b tier-guards precede
W-C6 read-time `hierarchy_paths`. W-C8 adds the optional F04 `ancestors` projection over that reader. W-C9 is the
[merged E1 preregistration and A1](THEME_HIERARCHY_E1_CHILD_LEADS_PARENT_PREREG_2026-10-07.md)
(PRs #8621/#8628); it has no W-C7 dependency. R-J.10 dropped the stored per-ticker `theme_category_ids` shadow
under `DNR:HOLD-TICKER-EXPOSURE-TAGS`. The later classification-context proposal #8643 remains a separately
scoped draft; it neither reinstates the dropped stored shadow nor gates E1.

E1a accrues only once W0 exists from the production graph's `macro_category → theme` belief and nonempty
as-known US curated `MEMBER_OF`/`EXPRESSES` composition (preregistration §4). A source merge alone does not
establish W0. E1b remains dormant until its separate merged basket→micro wiring trigger and honest window.
The preregistration §§1–5 and A1 govern the as-of-D reads, ≥50 matured counted episodes **and** ≥250 NYSE
trading days after excluding frozen intervals, and the permitted pre-gate telemetry. This correction does
not start either clock, authorize micro membership, or change any measurement or authority rule.

MO-DELTA-004 remains **PARTIAL**, as the
[existing F04 additive note](../market_intelligence_productization/MARKET_ONTOLOGY_F04_EXPOSURE_MAP_ANCESTORS_ADDITIVE_NOTE_2026-10-07.md)
records. W-C8's optional contract and tests do not supply the real shock→accepted-owner-edges→company
exposure product surface, typed refusals and evidence links required by the incumbent F04 closure map §2.1.

**Historical sequence, superseded only on the dependencies and closure claim corrected above:**

> W-C2b tier-guard in ThemeState / selection_cohort / exposure_map readers (byte-identical today) → W-C6
> structural_navigation `hierarchy_paths` → W-C7 us_context_vector shadow `theme_category_ids` keyed to belief_time →
> W-C8 F04 exposure_map `ancestors` (MO amendment; closes MO-DELTA-004) → W-C9 Evaluation OS E1 pre-registration
> ("child accelerates before parent confirms") — runs only after accrual.

## 8. Wave plan
| Wave | Owned files | Acceptance | Depends |
|---|---|---|---|
| W-C0 | this spec (research/theme_graph/THEME_HIERARCHY_SPEC_V1_2026-10-07.md); agentos/decisions/DEC-GMI-THEME-HIERARCHY-ON-CROSSWALK.md | `python3 scripts/agentos.py validate` exit 0 | — |
| W-C1 | contracts/theme_graph/nodes.v1.schema.json; contracts/theme_graph/edges.v1.schema.json; contracts/theme_graph/README.md; scripts/check_theme_graph_contracts.py; tests/test_theme_graph_hierarchy_contract.py | production parquets on main pass `--strict`; contract check enforces §1/§2 on fixtures (positive + each refusal) | W-C0 |
| W-C2 | engine/theme_graph/materialize.py; config/theme_crosswalk.yml (empty `hierarchy:` block); tests/test_theme_graph_hierarchy.py; tests/test_theme_graph_crosswalk.py | §0.2 byte-identity with empty block; fixture block emits curated/crosswalk PARENT_OF with valid_from=asserted_on; every §3 refusal tested; withdrawal + contradiction tested | W-C1 merged |
| W-C3 | contracts/theme_graph/probation_proposal.v1.schema.json; engine/theme_graph/probation.py; engine/theme_graph/proposal_worklist.py; engine/theme_graph/ontology.py; tests/test_theme_graph_probation_hierarchy.py | kind `hierarchy` accepted end-to-end; existing proposal ids unchanged; LLM row cannot be ratified; "reached graph" check matches PARENT_OF src=parent dst=child as-of; ontology readers ignore non-`theme`-tier theme nodes | W-C0 (parallel to W-C1) |
| W-C2b | engine/theme_graph/theme_state.py; engine/theme_graph/selection_cohort.py; engine/market_ontology/exposure_map.py; tests/test_theme_graph_tier_guard.py | readers ignore `kind=theme` nodes whose tier ≠ `theme`; existing tests unchanged & green | W-C1 merged |
| W-C4 | config/theme_crosswalk.yml (populate block from the seat-frozen table); tests/test_theme_graph_crosswalk.py (production block validates; every basket category accounted) | production build: PARENT_OF count = frozen table; all valid_from=asserted_on; ThemeState/cohort/exposure outputs unchanged | W-C2 + W-C2b merged |
| W-C5 | tests/test_theme_registry_hierarchy_parity.py | #7870 slice_keys ⊆ crosswalk micros | #7870 merged + owner countersign |
| W-C6 | engine/theme_graph/structural_navigation.py; tests/test_theme_graph_hierarchy_paths.py | rights receipts present; no vendor node ever a parent; as-of respected | W-C4 |
| W-C7 stored shadow — DROPPED-BY-RULING R-J.10 | No implementation from this historical row | Stored per-ticker `theme_category_ids` is refused; any later classification-context proposal retains its own scope | — |
| W-C8 | engine/market_ontology/exposure_map.py; contracts/market_ontology/exposure_map.v1.schema.json; tests/test_market_ontology_exposure_map.py | `ancestors` display-only, MO amendment recorded | W-C6 |
| W-C9 | Existing E1 preregistration and A1 (#8621/#8628) | E1a/E1b and gates as registered; A1 governs endpoint and freeze accounting | No W-C7 dependency (R-J.10/R9); accrual only from each arm's production W0 under §7 |

Historical W-C7 and W-C9 rows retained verbatim; the corrected rows above govern (R-J.10/R9):

```text
| W-C7 | engine/us_context_vector.py; its contract; tests/test_us_context_vector.py | shadow field empty before admission date | W-C6 |
| W-C9 | Evaluation OS E1 pre-registration doc | gates pre-registered; no run before accrual | W-C7 |
```

## 9. Pre-mortem tripwires
1. Document date bump re-ids every edge → test: EXPRESSES edge_id set unchanged; validator refuses missing asserted_on.
2. Category nodes leak into theme consumers → producer refuses EXPRESSES/MEMBER_OF on new tiers + W-C2b tier-guard.
3. Rights laundering through vendor parents → non-house endpoints refused; contract asserts mastermind_curated on every PARENT_OF.
4. #7870 grows a rival hierarchy → W-C5 parity test red; escalate to the #7870 owner.
5. Withdrawn edge re-emitted → W-C2 contradiction test.
6. Drift into per-ticker tags → contract test: no stored company→category/company→theme edge.
