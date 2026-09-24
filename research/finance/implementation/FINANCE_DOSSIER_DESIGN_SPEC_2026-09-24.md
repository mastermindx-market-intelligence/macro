# Finance Intelligence dossier — design spec (Finance D1)

**Date:** 2026-09-24
**Operation:** `gmi-finance-fable-ceo-e2e-20260924-chairman-001`
**Carrier PR:** #7887 (Fable CEO seat). Spec lane branch: `claude/finance-d1-dossier-design-spec`.
**State:** DESIGN (spec + static mockup) / DRAFT-HOLD / lane-owned. Mockup deferred to `fin_d1b_mockup`.
**Authority:** design only — no product code, no schema enrollment, no source admission, no basket membership, no rank/recommendation/entry/sizing/trade authority. Every `authority_caps` field in the frozen schema is literal `false`.
**Audience:** a later build lane that will implement the frozen design verbatim; an independent read-only audit that will attack the spec against `docs/DESIGN_DOCTRINE.md`, `research/MASTER_PRODUCT_DESIGN_SYSTEM_V1.md`, and `research/finance/FINANCE_R11_PRODUCT_AND_VISUALIZATION_ARCHITECTURE_FREEZE_2026-09-23.md`.
**SPLIT DELIVERY:** this run ships the spec only. Static mockup is delivered by `fin_d1b_mockup` onto the same PR after this head lands. See DEVIATIONS for the deferral record.

---

## 0. Reading order and proof of reading

The spec quotes the frozen research beside each design decision so the audit can verify chain-of-custody without re-reading every research file.

- **R11 §5 tier order (verbatim)** — `Tier 1 — What changed … Tier 2 — Rerating map … Tier 3 — System / flow map … Tier 4 — Subtheme atlas … Tier 5 — Company exposure matrix … Tier 6 — Macro/regime matrix … Tier 7 — Constraint map … Tier 8 — Evidence drawer`. The page renders seven L1 sections; `evidence-drawer` is a single aside, not a section (see §B.0).
- **Doctrine glance-tier word budget (verbatim, §1 table)** — `title ≤ 4 words; subtitle ≤ 14 words; row ≤ 1 line; footer ≤ 1 sentence`. The dossier's section heads and "what changed" tiles honour this budget; technical detail moves to hover/drawer.
- **TP-0 dark/light sentence (verbatim, CLAUDE.md §"Theme art direction")** — "dark = command center: luminance depth, instrument calm, restrained glow; light = research workspace: cool canvas, white material, hairline discipline, shadow instead of glow — two art directions, token substitution alone is never a light design". §C is written as TWO art directions with material rationale each, not as a token swap.
- **Doctrine empty-state law** — every null is stated in plain words on Tier 1 with a `mx-empty` block and a `mx-empty-why` line; no invisible removal, no averaged-over conflict.
- **Schema source (live, on `origin/main`)** — the frozen Finance T1 read-model schema **is** on `origin/main` since `b4c6e4bd` (PR #7896). This spec binds ONLY to fields and enums that exist in that live contract. Anything the page needs but the schema lacks lives under **GAPS** as a proposed contract amendment — never in a binding.

**Atlas grid (schema-bounded):** the atlas iterates whatever `domains[].slice_ids` the payload carries, grouped by `domains[]` in payload order. It is **not** a baked taxonomy of "52 slices / 7 domains" in the shell — slices the payload omits simply never render, and a footer chip reports the gap.

**Page archetype (per `research/MASTER_PRODUCT_DESIGN_SYSTEM_V1.md` §10 row C, C-company subtype):** `instrument_analyzer` / C-company = decision header → what-changed → evidence task tabs → risk & catalysts → provenance. The seven L1 sections map onto that archetype as: decision header = B.0 hero + TOC; what-changed = `what-changed`; evidence task tabs = `system-map` + `subtheme-atlas` (the reader's two lookup paths into the slice); risk & catalysts = `company-exposure` + `macro-matrix` + `constraint-map`; provenance = `rerating-map` chain (the connective story the dossier is here to tell) plus the evidence-drawer aside for source receipts. The C-signal subtype (Prophet detail) is **not** used here; the subtypes share the decision header and nothing else load-bearing.

---

## A. Information architecture + field bindings

The dossier is the read-only Finance Intelligence surface that lives AFTER the existing stock / basket / sector workflow. Authority comes from the read-model composer; the UI never recalculates. The page renders **seven L1 sections** plus one evidence-drawer aside; the section ids map to Tier 1…Tier 7 of R11 §5, and Tier 8 is the aside.

### A.0 Page-header bindings (consumed once, in the hero)

| Schema path | Schema enums | Where the page renders it |
|---|---|---|
| `contract_id` | const `finance_intelligence_read_model.v1` | page `<title>` (informational only; not displayed) |
| `schema_version` | pattern `^\d+\.\d+\.\d+$` | not displayed (locked at integration) |
| `generated_at` | date-time | `data-tip-en` / `data-tip-zh` on the hero meta line "Generated at …" / "生成于 …" (full ISO, not sliced) |
| `knowledge_cutoff` | date-time | visible hero meta: "Knowledge cutoff {{knowledge_cutoff}}" / "知识截止 {{knowledge_cutoff}}" |
| `common_as_of` | date | visible hero meta: "As of {{common_as_of}}" / "截至 {{common_as_of}}" |
| `sector_ref` | const `sector:financials` | page `<title>` only |
| `outer_dossier_ref.{contract_id, dossier_id, dossier_hash, state}` | `state ∈ {AVAILABLE, OUTER_CONTRACT_NOT_ACCEPTED, UNAVAILABLE}` | hero kicker shows plain-word chip "Outer dossier {state}" / "外部报告 {state}"; shell receives `data-state-outer-dossier` |
| `snapshot_identity.{composer_version, input_digest, curation_revision_set, rights_profile, view_scope}` | string / pattern / array / string / string | not displayed (provenance; surfaces only via the seat's debug tools) |
| `coverage.{domains_total, domains_populated, slices_total, slices_populated, slices_semantic_only, companies_with_records}` | integer | atlas (§B.4) eyebrow: "{{domains_populated}} of {{domains_total}} domains · {{slices_populated}} of {{slices_total}} slices mapped" EN/ZH |
| `coverage.first_vertical.{name, slice_ids[], state}` | `state ∈ {NOT_BUILT, SYNTHETIC, RESEARCH_RECORDS, PRODUCTION_PROVEN}` | slice selector (§B.2) iterates `first_vertical.slice_ids` in payload order |
| `freshness.{evidence_latest_observed_at, state, stale_after_days}` | `state ∈ {FRESH, AGING, SOURCE_STALE, NO_EVIDENCE}` | hero meta line "Evidence {{state}} · observed {{evidence_latest_observed_at}}" EN/ZH |
| `input_receipts[].{owner, generation, state, note}` | `owner ∈ {sector_intelligence, theme_graph, financial_intelligence, expectations_revisions, market_data, baskets, macro_rates_credit, identity, private_publication}`; `state ∈ {READ, UNAVAILABLE, NOT_ACCEPTED, DEGRADED}` | provenance footer (§B.0) renders one plain-word notice per entry whose `state` is not `READ` |
| `degraded_sections[].{section, state, reason}` | `section ∈ {what_changed, rerating_map, system_map, subtheme_atlas, company_exposure, macro_matrix, constraint_map, evidence_drawer}`; `state ∈ {AVAILABLE, UNAVAILABLE, PARTIAL}` | a `mx-empty` + `mx-empty-why` notice at the section (telemetry at §G) |
| `authority_caps.{rank, gate, size, trade, create_theme, change_membership, write_graph, admit_source}` | const-false | not displayed (read-only dossier; authority remains zero) |

**Anything the page would like but the schema does not supply** (a binding the audit found but the schema lacks): `slices[].display_headline`, `slices[].guardrail`, `slices[].user_action`, `material_changes[].display_label`, `slice.guardrail`, `coverage.coverage_state`, `coverage.coverage_label`, `freshness.freshness_label`, `material_changes[].evidence_horizon_label`, `entry_href`, `fin.top_domains`, `fin.slices_populated`, `fin.selected_slices`, `conflicts[].resolution` as user-facing string (the schema carries a literal `"UNRESOLVED_BY_DESIGN"` enum — surfaced only as the footer copy "Unresolved by design — both statements stand." / "设计上不予调和 — 两种陈述同时成立。"). None of these are bound in this spec; they live under **GAPS** as proposed contract amendments.

### A.1 `what-changed` (Tier 1)

| Visible surface | Schema path | Schema enums |
|---|---|---|
| one row per entry; freshness chip on each | `material_changes[].{change_id, event_clock{published_at, observed_at}, domain_ids, slice_ids, operating_implication, evidence_refs, conflict_ids, freshness_state}` | `freshness_state ∈ {FRESH, AGING, SOURCE_STALE, NO_EVIDENCE}` |
| conflict pip on the row when `conflict_ids` is non-empty | `material_changes[].conflict_ids[]` | (consumed by reference into `conflicts[]`) |
| per-row evidence button | `material_changes[].evidence_refs[]` | — |

### A.2 `rerating-map` (Tier 2 — primary visual)

Exactly four data-bound nodes, in order: **operating, expectations, valuation, price**. Each node's `primary_metric` formats via `fmtMetric` (explicit rule, see §D); each node's `clock` formats via `fmtClock` (see §D).

| Visible surface | Schema path | Schema enums |
|---|---|---|
| node `operating` caption: "What drives earnings, book, free cash flow and capital per share?" / "什么驱动每股盈利、账面、自由现金流与资本？" (≤14 words EN+ZH, static) | `slices[].rerating.operating.{state, primary_metric, clock, comparability_state, evidence_refs, note}` | `state ∈ {OBSERVED, INFERRED, MISSING, CONFLICTING, STALE, REGIME_BREAK, VALUATION_ANCHOR_UNAVAILABLE, PRICE_BASIS_UNQUALIFIED, NOT_APPLICABLE}`; `comparability_state ∈ {COMPARABLE, REGIME_BREAK_NOT_COMPARABLE, MIXED_BASIS, UNKNOWN}` |
| node `expectations` caption: "What does the market already expect?" / "市场已经在期待什么？" | `slices[].rerating.expectations.{state, primary_metric, clock, history.{state, observations[]}, comparability_state, evidence_refs, note}` | `state ∈ {plane_state}`; `expectations.history.state ∈ {DATED_CONSENSUS_AVAILABLE, NO_HISTORICAL_CONSENSUS, MANAGEMENT_GUIDANCE_ONLY}` |
| node `valuation` caption: "What anchor is the price paid against?" / "价格是基于什么锚定的？" | `slices[].rerating.valuation.{state, primary_metric, clock, comparability_state, evidence_refs, note}` | `state ∈ {plane_state}` |
| node `price` caption: "Has the price recognised it?" / "价格是否已经反映？" | `slices[].rerating.price.{state, primary_metric, clock, comparability_state, evidence_refs, note}` | `state ∈ {plane_state}` |
| connective sentence under the stepper | `slices[].rerating.bridge` (string) | — |
| node `valuation_anchor` chip inside the valuation node (renders via §D label map) | `slices[].valuation_anchor.{primary_per_share_anchor, primary_valuation_anchor, denominator, horizon, information_clock, required_return_context, state}` | `primary_per_share_anchor ∈ {EPS, CORE_EPS, TBVPS, BVPS, FCF_PER_SHARE, DPS, EMBEDDED_VALUE_PER_SHARE, NAV_PER_SHARE, NOT_APPLICABLE}`; `primary_valuation_anchor ∈ {P_E, P_TBV, P_B, EV_EBITDA, FCF_YIELD, DIVIDEND_YIELD, P_EV, P_NAV, P_AUM, NOT_APPLICABLE}`; `horizon ∈ {TRAILING_12M, FORWARD_12M, FORWARD_24M, CURRENT_BOOK, NOT_APPLICABLE}`; `state ∈ {AVAILABLE, VALUATION_ANCHOR_UNAVAILABLE}` |
| falsifiers list "What we're watching" beside/under the stepper (rendered as a SEPARATE list, never a node) | `slices[].falsifiers[].{falsifier_id, statement, window, state}` | `state ∈ {WATCHING, NOT_YET_EVALUABLE}` |
| slice selector above the stepper (native `<select>`) | `coverage.first_vertical.slice_ids[]` joined with `slices[].{slice_id, name_en, name_zh}` | — |

The R11 chain questions (`driver / new information → operating variable → earnings/book/FCF/capital → expectations → valuation anchor → price recognition → falsifier`) are STATIC node captions and the connective sentence; they are not separate data fields. `rerating.driver_label` / `rerating.driver_metric` / `rerating.driver.state` / `rerating.earnings_label` / `rerating.earnings.primary_metric` / `rerating.falsifier_horizon` are NOT in the schema and NOT bound.

### A.3 `system-map` (Tier 3)

Three selectable views; tabs generated from `system_views[]` in payload order; each tab id `tab-{{view_id}}` ↔ panel id `panel-{{view_id}}`.

| Visible surface | Schema path | Schema enums |
|---|---|---|
| three tabs | `system_views[].view_id` | — |
| tab label | `system_views[].{name_en, name_zh}` | — |
| per-view nodes (5–8 first paint; children render on click) | `system_views[].nodes[].{node_id, label_en, label_zh, node_type, slice_ids, expandable, children_ids}` | — |
| per-view edges (visible `<ol>` under `<details>`, not hover-only) | `system_views[].edges[].{from, to, relationship, evidence_state}` | `relationship ∈ {PAYS, SETTLES, CLEARS, GUARANTEES, FUNDS, INSURES, LENDS, HOLDS_CUSTODY, LICENSES, SUPERVISES, GRANTS_ACCESS, PUBLISHES_BENCHMARK, RATES, PROVIDES_DATA, REQUIRES_MEMBERSHIP, EARNS_FEE_FROM, BEARS_CREDIT_RISK_OF, CAPTURES_SPREAD_ON, RECOGNISES_REVENUE_FROM, DEPENDS_ON_VOLUME_OF}` (per view); `evidence_state ∈ {OBSERVED, INFERRED, MISSING}` |

`nodes[].evidence_state` is NOT in the schema (the enum lives on `edges[]` only); the step-list equivalent therefore carries the edge-level `evidence_state` chip, not a per-node chip.

### A.4 `subtheme-atlas` (Tier 4)

| Visible surface | Schema path | Schema enums |
|---|---|---|
| eyebrow: "{{domains_populated}} of {{domains_total}} domains · {{slices_populated}} of {{slices_total}} slices mapped" EN/ZH | `coverage.{domains_populated, domains_total, slices_populated, slices_total}` | — |
| groups in `domains[]` payload order; one `<section>` per `domain_id` | `domains[].{domain_id, name_en, name_zh, slice_ids}` | — |
| per-slice name + chip | `slices[].{slice_id, name_en, name_zh}` joined with `slices[].{slice_state, basket_state, identity_state}` | `slice_state ∈ {SEMANTIC_ONLY, RESEARCH_EVIDENCE_AVAILABLE, MEASURABLE, PRICE_SURFACE_AVAILABLE, EVALUATION_CONTEXT_AVAILABLE, RIGHTS_RESTRICTED, STALE, HELD_FOR_REVIEW}` |
| per-slice basket-state chips (visible, plain words) | `slices[].basket_state.{posture, incumbent_basket_ids, membership_state, member_count, weighting_family, price_basis_state}` | `posture ∈ {SEMANTIC_ONLY, BROAD_CONTEXT_AVAILABLE, RESEARCH_CANDIDATE, CANDIDATE_READY_FOR_OWNER_REVIEW, ADMITTED}`; `membership_state ∈ {NONE, CURRENT_MEMBERSHIP_ONLY, PIT_MEMBERSHIP_INCOMPLETE, PIT_MEMBERSHIP_VALIDATED}`; `weighting_family ∈ {EQUAL_WEIGHT, FLOAT_CAP_CONTEXT, EXPOSURE_WEIGHT, EXPOSURE_CAPPED_WEIGHT, STRATIFIED_EQUAL_WEIGHT}`; `price_basis_state ∈ {TOTAL_RETURN_QUALIFIED, PRICE_RETURN_QUALIFIED}` |
| footer chip: "{{slices_total − rendered}} slices not yet mapped" / "尚有 {{slices_total − rendered}} 个切片未映射" | `coverage.slices_total − sum(grouped)` | — |

The atlas renders **only** the slices the payload carries, grouped by `domains[]` in payload order. No baked taxonomy in the shell; nothing vanishes silently.

### A.5 `company-exposure` (Tier 5)

| Visible surface | Schema path | Schema enums |
|---|---|---|
| rows = `company_exposures[]`, sorted by `issuer_label` (EN) in both languages | `company_exposures[].{row_id, issuer_label, ticker_hint, identity, company_route, cells[]}` | — |
| row identity chip + (when `IDENTITY_UNRESOLVED` / `RESEARCH_HINT_UNVALIDATED`) no link | `company_exposures[].identity.{state, company_node_id, security_ref, listing_note}` | `identity.state ∈ {IDENTITY_VALIDATED, IDENTITY_UNRESOLVED, RESEARCH_HINT_UNVALIDATED}` |
| route (when `IDENTITY_VALIDATED` and `company_route.state == AVAILABLE`) | `company_exposures[].company_route.{href, state}` | `company_route.state ∈ {AVAILABLE, IDENTITY_UNRESOLVED}` |
| columns = `coverage.first_vertical.slice_ids` in atlas order; cell placed by `cells[].slice_id` (absent → "No role recorded / 未记录角色" cell) | `company_exposures[].cells[].{slice_id, role, exposure, materiality, retained_risk, evidence_date, evidence_refs}` | `role ∈ {DIRECT_PURE_OR_HIGH_EXPOSURE, DIRECT_DIVERSIFIED, ENABLER_OR_TOLL_COLLECTOR, SECOND_ORDER_BENEFICIARY, PROXY_OR_ADJACENCY, AT_RISK_OR_DISRUPTED, HEDGE_OR_OFFSET}`; `materiality ∈ {MATERIAL, PARTIAL, IMMATERIAL, UNMEASURED}` |
| exposure basis + state (cell chip when `EXPOSURE_NOT_SEPARATELY_DISCLOSED` — visible text, never a hover-only `focus` handler) | `company_exposures[].cells[].exposure.{basis, numerator, denominator, value, unit, state}` | `basis ∈ {SEGMENT_REVENUE, TRANSACTION_VOLUME, AUC_A, AUM, NOTIONAL, QUALITATIVE, NOT_SEPARATELY_DISCLOSED}`; `exposure.state ∈ {MEASURED, EXPOSURE_NOT_SEPARATELY_DISCLOSED, DIRECT_DIVERSIFIED, QUALITATIVE_ONLY}` |

Materiality colour law (per §C, tokens only): `MATERIAL → --ink-warn`; `PARTIAL → --muted` with the word "Partial" / "部分"; `IMMATERIAL / UNMEASURED → --muted` with the word. Never `--up`/`--down`/`--ink-up`/`--ink-down` anywhere on the exposure surface.

### A.6 `macro-matrix` (Tier 6)

Flat `macro_matrix[]` (NEVER a pivoted `rows/cells` shape). Rows = slice ids present in payload order; columns = the 13-driver enum; absent (slice, driver) pair → "Not mapped / 未映射" cell.

| Visible surface | Schema path | Schema enums |
|---|---|---|
| row header per slice (name from `slices[].name_en` / `name_zh`) | `macro_matrix[].slice_id` joined with `slices[]` | — |
| column header per driver | `macro_matrix[].driver` | `driver ∈ {policy_rates, yield_curve, deposit_funding, credit_growth, losses_defaults, housing, equity_levels, volatility, issuance_ma, catastrophe_reinsurance, regulation_capital, fx, liquidity}` |
| cell = plain-word mechanism + lag chip + state chip | `macro_matrix[].{mechanism, lag, state}` | `lag ∈ {IMMEDIATE, ONE_QUARTER, TWO_TO_FOUR_QUARTERS, MULTI_YEAR, UNKNOWN}`; `state ∈ {DESCRIBED, CAUSAL_EFFECT_UNMEASURED, NOT_APPLICABLE}` |

### A.7 `constraint-map` (Tier 7)

| Visible surface | Schema path | Schema enums |
|---|---|---|
| one row per `constraints[]` entry | `constraints[].{slice_id, constraint, economic_effect, evidence_refs}` | — |
| constraint name chip | `constraints[].constraint` | `constraint ∈ {regulatory_permission, capital, funding_liquidity, network_access, settlement_finality, data_benchmark_control, distribution, integration_switching, trust_identity, resilience}` |

`macro_drivers` and `row.cells` are NOT in the schema and NOT bound.

### A.8 `evidence-drawer` — NOT a section, single aside

One instance, `<aside id="evidence-drawer" role="dialog" aria-modal="true" aria-labelledby="fi-evidence-title" hidden>` (see §B.0). It is the only modal surface.

| Visible surface | Schema path | Schema enums |
|---|---|---|
| record fields | `source_records[].{record_id, source, business_scope, metric, observation, temporal, limitations, identity_state, rights_state, statement_mode, correction, evidence_ref, excerpt}` | `rights_state ∈ {DIRECT_DISPLAY_OK, DERIVED_DISPLAY_OK, SOURCE_RIGHTS_HELD, INTERNAL_ONLY}`; `identity_state ∈ {IDENTITY_VALIDATED, IDENTITY_UNRESOLVED, RESEARCH_HINT_UNVALIDATED}`; `statement_mode ∈ {REPORTED_FACT, CATALOG_DESCRIPTION, ANNOUNCED_ARRANGEMENT, FORWARD_TARGET, ATTRIBUTED_INTERPRETATION}` |
| source clocks | `source_records[].source.{published_at, published_at_grain, observed_at, retained_at, retention_ref, native_digest}` | `published_at_grain ∈ {DAY, MONTH, QUARTER, YEAR, UNKNOWN}` |

**Suppression rule (binding):** when `rights_state` is `SOURCE_RIGHTS_HELD` or `INTERNAL_ONLY`, the drawer shows `publisher`, `source_family`, `locator` words and the five `limitations` fields but **NEVER** `value` / `excerpt` / `native_digest`. A plain-word notice in the drawer makes this rule explicit: "Private evidence — source rights restrict display." / "私有证据 — 来源权利限制展示。"

`slices[].freshness.{evidence_latest_observed_at, state}` is the per-slice freshness (see §A.4 chips); it lives next to the atlas and rerating nodes, not in the drawer.

### A.9 Conflicts sub-block — nested INSIDE `rerating-map` (not a section)

`conflicts[]` are first-class cards, but they sit as a `.fi-conflicts` sub-block after the stepper inside the `rerating-map` section; they do not have their own L1 id. `B.9` as a top-level section is removed.

| Visible surface | Schema path | Schema enums |
|---|---|---|
| card label (plain words, from §D.12 map) | `conflicts[].label` (literal enum token; surfaced only as the label map) | `label ∈ {EARNINGS_UP_P_E_DOWN, BOOK_UP_P_B_DOWN, NII_UP_CREDIT_WORSE, POLICY_SUPPORT_NIM_PRESSURE, REGULATORY_RATIO_DOWN_REGIME_BREAK, PLAN_DISCLOSED_EXECUTION_PENDING, TAIL_RISK_DOWN_CURRENT_EARNINGS_WEAK, PRICE_UP_CAUSAL_EVENT_EFFECT_UNPROVEN, CAPITAL_COST_UP_GROWTH_STILL_STRONG, VOLUME_UP_REVENUE_MATERIALITY_UNPROVEN}` |
| left statement + plane word + evidence button | `conflicts[].left.{plane, statement, evidence_refs}` | `plane ∈ {operating, expectations, valuation, price, regime, policy}` |
| right statement + plane word + evidence button | `conflicts[].right.{plane, statement, evidence_refs}` | `plane ∈ {plane_state}` |
| footer copy | `conflicts[].resolution` (literal enum token; surfaced only as the footer copy) | literal `UNRESOLVED_BY_DESIGN` (plain-word footer copy only) |

`conflict_text[c.conflict_id]` and `c.left.plane.state` are NOT in the schema and NOT bound.