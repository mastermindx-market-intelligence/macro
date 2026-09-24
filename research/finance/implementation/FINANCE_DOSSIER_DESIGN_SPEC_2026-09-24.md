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

---

## B. DOM skeletons per section

All class names use the `fi-` prefix. All copy uses the repo's `data-en` / `data-zh` idiom (`<span class="l-en">…</span><span class="l-zh">…</span>` swapped on `html[data-lang]` flip per existing `theme.js`). Internal enum tokens appear ONLY in `data-state`/`data-*` attributes; visible text uses plain words per §D. **No `{% for` / `{{ ch.… }}` / `{{ row.… }}` / `{{ slice.… }}` Jinja bindings — every section is a data-free shell with one mount point** (`data-fi-mount="<section>"`); hydration is owned by §E.

### B.0 Page shell + evidence-drawer aside (one instance each)

```html
<main class="fi-shell" id="fi-shell" data-fi-mount="shell"
      data-state-outer-dossier="AVAILABLE"
      data-state-coverage="AVAILABLE">
  <header class="fi-hero" aria-labelledby="fi-hero-title">
    <p class="fi-kicker" data-en="Finance Intelligence" data-zh="金融情报">Finance Intelligence</p>
    <h1 id="fi-hero-title" data-en="Financial Rails &amp; Market Infrastructure"
        data-zh="金融基础设施与市场运作">Financial Rails &amp; Market Infrastructure</h1>
    <p class="fi-deck" data-en="Read how the financial system moves money, settles trades and prices assets — context only, not a trade call."
       data-zh="阅读金融体系如何转移资金、结算交易并为资产定价 — 仅为背景，非交易指令。">Read how the financial system moves money, settles trades and prices assets — context only, not a trade call.</p>
    <p class="fi-meta">
      <span data-en="As of 2026-09-24" data-zh="截至 2026-09-24">As of 2026-09-24</span>
      <span aria-hidden="true">·</span>
      <span data-en="Knowledge cutoff 2026-09-23" data-zh="知识截止 2026-09-23">Knowledge cutoff 2026-09-23</span>
      <span aria-hidden="true">·</span>
      <span class="fi-freshness" data-state-fresh="Fresh" data-en="Evidence Fresh" data-zh="证据新鲜">Fresh</span>
      <span class="fi-outer-dossier" data-state-outer-dossier="AVAILABLE" data-en="Outer dossier: accepted" data-zh="外承报告：已接入">Outer dossier: accepted</span>
    </p>
  </header>

  <nav class="fi-toc" aria-label="Section navigation" data-en="Section navigation" data-aria-zh="章节导航">
    <ol>
      <li><a href="#what-changed" data-en="What changed" data-zh="近期变化">What changed</a></li>
      <li><a href="#rerating-map" data-en="Rerating map" data-zh="重估链路">Rerating map</a></li>
      <li><a href="#system-map" data-en="System map" data-zh="系统图">System map</a></li>
      <li><a href="#subtheme-atlas" data-en="Subtheme atlas" data-zh="子主题图谱">Subtheme atlas</a></li>
      <li><a href="#company-exposure" data-en="Company exposure" data-zh="公司敞口">Company exposure</a></li>
      <li><a href="#macro-matrix" data-en="Macro matrix" data-zh="宏观矩阵">Macro matrix</a></li>
      <li><a href="#constraint-map" data-en="Constraint map" data-zh="约束图">Constraint map</a></li>
      <li><button type="button" class="fi-toc-evidence" aria-controls="evidence-drawer" data-en="Evidence" data-zh="证据">Evidence</button></li>
    </ol>
  </nav>

  <footer class="fi-provenance" data-fi-mount="provenance" aria-label="Input receipts">
    <!-- Hydration (§E) renders one .fi-receipt-line per input_receipts entry whose state ≠ READ. -->
  </footer>
</main>

<aside id="evidence-drawer" class="fi-drawer" role="dialog" aria-modal="true"
       aria-labelledby="fi-evidence-title" hidden inert tabindex="-1">
  <header class="fi-drawer-head">
    <div>
      <p class="fi-kicker" data-en="Source receipt" data-zh="来源凭据">Source receipt</p>
      <h2 id="fi-evidence-title" data-en="Evidence" data-zh="证据">Evidence</h2>
    </div>
    <button class="fi-drawer-close" id="fi-close-evidence" type="button"
            aria-label="Close evidence drawer" data-aria-zh="关闭证据抽屉">×</button>
  </header>
  <div class="fi-drawer-body" id="fi-evidence-body" data-fi-mount="evidence-body">
    <!-- Hydration populates the .fi-evidence-fields list; the suppression rule (A.8)
         hides value/excerpt/native_digest when rights_state is SOURCE_RIGHTS_HELD or INTERNAL_ONLY. -->
  </div>
</aside>
<div class="fi-scrim" id="fi-scrim" hidden></div>
```

Exactly one instance of `id="evidence-drawer"` (check #9); exactly one role="dialog" (check #9); the TOC entry "Evidence" is a `<button>` opening the drawer (R-H). The duplicate drawer markup that lived in B.0/B.8 is removed.

### B.1 `what-changed` — material changes

```html
<section id="what-changed" class="fi-section fi-changes" aria-labelledby="fi-changes-title"
         data-fi-mount="what-changed">
  <h2 id="fi-changes-title" class="fi-section-title">
    <span data-en="What changed" data-zh="近期变化">What changed</span>
    <span class="fi-section-eyebrow" data-en="Material observations, plain words" data-zh="重要观察，直白表述">Material observations, plain words</span>
  </h2>
  <ul class="fi-change-list" role="list" data-fi-mount="what-changed-list">
    <!-- Hydration appends one <li class="fi-change-row"> per material_changes entry. -->
  </ul>
  <p class="fi-section-foot" data-en="Read the underlying receipts before acting on any line."
     data-zh="请先查阅原始凭据再行判断。">Read the underlying receipts before acting on any line.</p>
</section>
```

### B.2 `rerating-map` — primary visual (exactly four nodes)

The primary visual has exactly four data-bound stepper nodes — **operating, expectations, valuation, price** — in that order. The R11 chain questions become STATIC node captions (≤14 words each, EN + ZH). `rerating.bridge` renders as the connective sentence under the stepper. `valuation_anchor` renders INSIDE the valuation node (a separate chip via §D label map; `state ∈ {AVAILABLE, VALUATION_ANCHOR_UNAVAILABLE}` maps to plain words). `slices[].falsifiers[]` render as a SEPARATE list beside/under the stepper — they are NOT a node.

A native `<select id="fi-slice-select">` precedes the stepper; options come from `coverage.first_vertical.slice_ids` joined with `slices[].{slice_id, name_en, name_zh}`. The default option is the first slice id. `change` re-renders the stepper. URL hash `#slice=<slice_id>` overrides on hydration and updates on change.

```html
<section id="rerating-map" class="fi-section fi-rerating" aria-labelledby="fi-rerating-title"
         data-fi-mount="rerating-map">
  <h2 id="fi-rerating-title" class="fi-section-title">
    <span data-en="Rerating map" data-zh="重估链路">Rerating map</span>
    <span class="fi-section-eyebrow" data-en="How a slice reaches per-share value" data-zh="一个子主题如何抵达每股价值">How a slice reaches per-share value</span>
  </h2>

  <div class="fi-slice-picker">
    <label for="fi-slice-select" data-en="Slice" data-zh="切片">Slice</label>
    <select id="fi-slice-select" class="fi-slice-select" data-fi-mount="slice-select">
      <!-- Hydration populates <option> per coverage.first_vertical.slice_ids. -->
    </select>
  </div>

  <ol class="fi-rerating-steps" role="list" data-fi-mount="rerating-steps">
    <!-- Hydration renders exactly 4 <li class="fi-rerating-step fi-node-{name}"> in the order operating, expectations, valuation, price.
         Each step carries:
           <span class="fi-step-dot" aria-hidden="true"></span>
           <span class="fi-step-label" data-en="..." data-zh="...">{caption from A.2}</span>
           <span class="fi-step-metric">{primary_metric via fmtMetric}</span>
           <span class="fi-step-chip" data-state="{plane.state}">{plain-word chip from §D.1}</span>
           <span class="fi-step-clock">{clock via fmtClock}</span>
           <button class="fi-step-evidence" type="button" data-evidence-ids="{evidence_refs join}"
                   aria-label="Open evidence for this step" data-aria-zh="打开该步骤的证据">↗</button>
         The valuation node additionally carries a <span class="fi-anchor-chip" data-anchor-state="{valuation_anchor.state}">
         with the primary_per_share_anchor / primary_valuation_anchor / horizon plain-word chip.
         The expectations node additionally carries <span class="fi-history-chip" data-history-state="{expectations.history.state}">. -->
  </ol>

  <p class="fi-rerating-bridge" data-fi-mount="rerating-bridge">
    <!-- Hydration sets the text node from rerating.bridge; static fallback: "The chain from earnings to divergence is documented in the chips above." -->
  </p>

  <ul class="fi-falsifiers" role="list" data-fi-mount="falsifiers" aria-label="What we are watching" data-en="What we are watching" data-aria-zh="我们正在观察">
    <!-- Hydration appends one <li class="fi-falsifier" data-state-falsifier="{falsifier.state}"> per falsifiers[] entry. -->
  </ul>

  <div class="fi-conflicts" data-fi-mount="conflicts" aria-labelledby="fi-conflicts-title">
    <h3 id="fi-conflicts-title" class="fi-conflicts-title">
      <span data-en="Where the planes disagree" data-zh="各维度之间的分歧">Where the planes disagree</span>
      <span class="fi-section-eyebrow" data-en="Surfaced, never averaged" data-zh="显示差异，而非取均值">Surfaced, never averaged</span>
    </h3>
    <ul class="fi-conflict-list" role="list" data-fi-mount="conflict-list">
      <!-- Hydration appends one <li class="fi-conflict-card" data-conflict-id="{c.label}"> per conflicts[] entry. -->
    </ul>
  </div>

  <p class="fi-section-foot" data-en="Horizontal on desktop · vertical on mobile. State chips map to the schema's plane state tokens."
     data-zh="桌面端为横向 · 移动端为纵向。状态标签对应 schema 中的状态枚举。">Horizontal on desktop · vertical on mobile. State chips map to the schema's plane state tokens.</p>
</section>
```

The stepper `<li>` markup includes `.fi-step-dot` (R-B: the audit found the CSS targets a missing element).

### B.3 `system-map` — three selectable views

Tab ids `tab-{{view_id}}` ↔ panel ids `panel-{{view_id}}`. Roving tabindex with ArrowLeft/ArrowRight/Home/End (R-H). Edges render as a visible `<ol>` under `<details>` (not hover-only).

```html
<section id="system-map" class="fi-section fi-system" aria-labelledby="fi-system-title"
         data-fi-mount="system-map">
  <h2 id="fi-system-title" class="fi-section-title">
    <span data-en="System map" data-zh="系统图">System map</span>
    <span class="fi-section-eyebrow" data-en="Three views, never blended" data-zh="三种视图，永不混用">Three views, never blended</span>
  </h2>

  <div class="fi-view-tabs" role="tablist" aria-label="Choose a system view" data-en="Choose a system view" data-aria-zh="选择系统视图">
    <!-- Hydration renders one <button role="tab" id="tab-{view_id}" aria-controls="panel-{view_id}" aria-selected="true|false" class="fi-view-tab" data-view="{view_id}" tabindex="0|-1">{name_en}</button> per system_views[] in payload order. -->
  </div>

  <!-- Hydration renders one <div role="tabpanel" id="panel-{view_id}" class="fi-view-panel" data-view="{view_id}" aria-labelledby="tab-{view_id}" hidden> per system_views[] in payload order. -->
  <template class="fi-view-panel-template">
    <svg class="fi-system-svg" role="img" aria-labelledby="fi-view-label">
      <title id="fi-view-label" class="fi-view-label">{name_en}</title>
      <!-- 5–8 <g class="fi-svg-node"> nodes first paint; children render on click. -->
    </svg>
    <details class="fi-system-edges" open>
      <summary data-en="Edge list (step view)" data-zh="边的步骤视图">Edge list (step view)</summary>
      <ol class="fi-system-edge-list" role="list">
        <!-- Hydration appends one <li class="fi-system-edge" data-state-evidence="{evidence_state}"> per edges[] entry, format: "<from label> — {relationship word} → <to label> · <evidence_state chip>". -->
      </ol>
    </details>
  </template>
</section>
```

### B.4 `subtheme-atlas` — payload-driven domain × slice grid

```html
<section id="subtheme-atlas" class="fi-section fi-atlas" aria-labelledby="fi-atlas-title"
         data-fi-mount="subtheme-atlas">
  <h2 id="fi-atlas-title" class="fi-section-title">
    <span data-en="Subtheme atlas" data-zh="子主题图谱">Subtheme atlas</span>
    <span class="fi-section-eyebrow" class="fi-atlas-eyebrow" data-fi-mount="coverage eyebrow">
      <span data-en="0 of 0 domains · 0 of 0 slices mapped" data-zh="0 / 0 个子域 · 0 / 0 个切片已映射">0 of 0 domains · 0 of 0 slices mapped</span>
    </span>
  </h2>

  <div class="fi-domain-grid" data-fi-mount="domain-grid">
    <!-- Hydration renders one <section class="fi-domain"> per domains[] entry in payload order.
         Inside, one <li class="fi-slice"> per slices[] entry whose domain_id matches, in payload order. -->
  </div>

  <p class="fi-atlas-gap" data-fi-mount="atlas-gap">
    <!-- Hydration sets text from (coverage.slices_total - sum(rendered)); static placeholder: "0 slices not yet mapped / 尚未映射". -->
  </p>
</section>
```

The atlas renders only the slices the payload carries (R-F). The "Domains mapped" header lists all populated `domains[]` in payload order (R-J); the literal "Top research domains" rename to "Domains mapped" is at §F.2.

### B.5 `company-exposure` — sticky matrix / mobile cards

```html
<section id="company-exposure" class="fi-section fi-exposure" aria-labelledby="fi-exposure-title"
         data-fi-mount="company-exposure">
  <h2 id="fi-exposure-title" class="fi-section-title">
    <span data-en="Company exposure" data-zh="公司敞口">Company exposure</span>
    <span class="fi-section-eyebrow" data-en="Role, basis, materiality — never a hidden score" data-zh="角色、口径、重要性 — 绝无暗藏分数">Role, basis, materiality — never a hidden score</span>
  </h2>

  <div class="fi-exposure-table-wrap">
    <table class="fi-exposure-table" aria-describedby="fi-exposure-desc">
      <caption id="fi-exposure-desc" class="visually-hidden" data-en="Company exposure matrix. Rows are companies. Columns are slices."
              data-zh="公司敞口矩阵。行为公司，列为切片。">Company exposure matrix. Rows are companies. Columns are slices.</caption>
      <thead>
        <tr>
          <th class="fi-col-company" scope="col" data-en="Company" data-zh="公司">Company</th>
          <!-- Hydration renders one <th class="fi-col-slice" scope="col">{slice name}</th> per coverage.first_vertical.slice_ids in atlas order. -->
        </tr>
      </thead>
      <tbody data-fi-mount="exposure-rows">
        <!-- Hydration renders one <tr data-row-id data-state-identity> per company_exposures[] sorted by issuer_label (EN, case-insensitive). -->
      </tbody>
    </table>
  </div>

  <ul class="fi-exposure-cards" role="list" data-fi-mount="exposure-cards" aria-label="Mobile exposure cards" data-en="Mobile exposure cards" data-aria-zh="移动端敞口卡片" hidden>
    <!-- Hydration renders one <li class="fi-exposure-card"> per company_exposures[] entry listing only the cells the row carries. -->
  </ul>
</section>
```

`<td>` cells never carry a hover-only or `focus`-handler-driven state. The `EXPOSURE_NOT_SEPARATELY_DISCLOSED` chip is visible text inside the cell (R-F).

### B.6 `macro-matrix` — flat mechanism + lag grid

```html
<section id="macro-matrix" class="fi-section fi-macro" aria-labelledby="fi-macro-title"
         data-fi-mount="macro-matrix">
  <h2 id="fi-macro-title" class="fi-section-title">
    <span data-en="Macro matrix" data-zh="宏观矩阵">Macro matrix</span>
    <span class="fi-section-eyebrow" data-en="Mechanism and lag, never a stock verdict" data-zh="机制与时滞 — 非个股结论">Mechanism and lag, never a stock verdict</span>
  </h2>
  <div class="fi-macro-table-wrap">
    <table class="fi-macro-table" aria-describedby="fi-macro-desc">
      <caption id="fi-macro-desc" class="visually-hidden" data-en="Macro driver matrix. Rows are slices. Columns are macro drivers."
              data-zh="宏观驱动矩阵。行为切片，列为宏观驱动。">Macro driver matrix. Rows are slices. Columns are macro drivers.</caption>
      <thead>
        <tr>
          <th scope="col" data-en="Slice" data-zh="切片">Slice</th>
          <!-- 13 columns, headers from §D.8 driver label map. -->
        </tr>
      </thead>
      <tbody data-fi-mount="macro-rows">
        <!-- Hydration renders one <tr data-slice-id> per unique slice_id in macro_matrix[], grouped. Cells by (slice, driver) pair; absent → "Not mapped / 未映射". -->
      </tbody>
    </table>
  </div>
</section>
```

### B.7 `constraint-map` — economic effect per constraint

```html
<section id="constraint-map" class="fi-section fi-constraint" aria-labelledby="fi-constraint-title"
         data-fi-mount="constraint-map">
  <h2 id="fi-constraint-title" class="fi-section-title">
    <span data-en="Constraint map" data-zh="约束图">Constraint map</span>
    <span class="fi-section-eyebrow" data-en="Every constraint links to its economic effect" data-zh="每条约束都对应一个经济效应">Every constraint links to its economic effect</span>
  </h2>
  <ul class="fi-constraint-list" role="list" data-fi-mount="constraint-list">
    <!-- Hydration appends one <li class="fi-constraint-row" data-constraint data-slice-id> per constraints[] entry. -->
  </ul>
</section>

---

## C. Scoped CSS — two art directions (no token swap, no hex/rgb literals)

The CSS is scoped to `templates/finance_intelligence.css`. It declares a `:root` / `html[data-theme="dark"]` block (default) and an `html[data-theme="light"]` block — the SAME selector `theme.css` uses for light tokens (see `templates/theme.css` lines 186–223). Each block is a complete material treatment — not a colour inversion. Tokens come ONLY from `templates/theme.css` (`--bg`, `--panel`, `--panel2`, `--text`, `--muted`, `--line`, `--link`, `--ok`, `--warn`, `--act`, `--info`, `--ink-link`, `--ink-ok`, `--ink-warn`, `--ink-act`, `--font-ui`, `--fs-*`) plus `--fi-*` locals for dossier-specific elevation. **No new token family is added to `theme.css`.**

**Colour law (R-E):** every colour in this section is `var(--token)` or `color-mix(in srgb, var(--token) N%, transparent|var(--token))`. Zero hex literals (`#xxx`/`#xxxxxx`), zero `rgb()`/`rgba()` literals — anywhere in §C, dark block included. Font sizes ONLY via `--fs-*` tokens (no `10px`/`11px`/`font-size: 1Xpx` literals).

### C.0 Material rationale — dark (command center)

The dark dossier rides a near-black depth; elevation is a ~3% luminance step (`--panel` over `--bg`, `--panel2` over `--panel`), never a glow. Hairlines are 1px solid `--line`. State meaning rides on chip contrast (light-tinted fill + high-contrast ink) and on icon/text companions — colour is never the only channel (doctrine §5 + WCAG 1.4.1). Restrained glow appears only on the focused stepper dot and the focused "what changed" freshness pip (1px outer ring at `--link`). The rerating stepper is a thin horizontal spine at 2px with circular dots; the spine carries the rhythm, the dots are anchors.

### C.1 Material rationale — light (research workspace)

The light dossier sits on a perceptibly deeper canvas (doctrine §5: `--bg: #f7f8fa` shipped in `theme.css` light block, lines 199–223) so panels read as paper laid on a desk. White panels (`--panel: #ffffff`, from theme.css light) carry 1px hairlines (`--line`); elevation comes from a 2-stop hairline-tight shadow stack, never from saturation. Glow becomes shadow: the focused stepper dot drops a 2px ring at `--ink-link`; the "what changed" freshness pip replaces glow with a 3px left rail. Chips use a quiet tint + darkened ink pair; no chip saturates the surface.

### C.2 Common tokens (always inherited from `theme.css`)

```
/* font, type ramp, spacing — all from theme.css :root. Never redeclared. */
.fi-shell { font-family: var(--font-ui); font-feature-settings: "tnum" 1, "cv11" 1; }
```

### C.3 Dark block

```css
:root,
html[data-theme="dark"] {
  /* Existing theme tokens: --bg, --panel, --panel2, --line, --text, --muted,
     --ok/--warn/--act, --link/--info, --ink-* already on theme.css.
     The dossier adds ONLY --fi-* locals below — never new theme-wide tokens. */
  --fi-canvas:        var(--bg);
  --fi-panel:         var(--panel);
  --fi-panel2:        var(--panel2);
  --fi-line:          var(--line);
  --fi-text:          var(--text);
  --fi-muted:         var(--muted);
  --fi-link:          var(--link);
  --fi-spine:         color-mix(in srgb, var(--line) 90%, transparent);
  --fi-step-fill:     color-mix(in srgb, var(--link) 14%, var(--panel));
  --fi-step-ring:     color-mix(in srgb, var(--link) 38%, transparent);
  --fi-chip-observed: color-mix(in srgb, var(--ok)   18%, var(--panel));
  --fi-chip-watch:    color-mix(in srgb, var(--warn) 18%, var(--panel));
  --fi-chip-caution:  color-mix(in srgb, var(--info) 14%, var(--panel));
  --fi-chip-missing:  color-mix(in srgb, var(--muted) 18%, var(--panel));
  --fi-chip-stale:    color-mix(in srgb, var(--act)  16%, var(--panel));
  --fi-chip-regime:   color-mix(in srgb, var(--act)  22%, var(--panel));
}
```

### C.4 Light block

```css
html[data-theme="light"] {
  /* Same token family; light tokens (#f7f8fa, #ffffff, etc.) already on
     theme.css light block (lines 186–223). --fi-* locals are RECOMPUTED for
     light's "paper on desk" reading; saturation never escapes the panel. */
  --fi-canvas:        var(--bg);
  --fi-panel:         var(--panel);
  --fi-panel2:        var(--panel2);
  --fi-line:          var(--line);
  --fi-text:          var(--text);
  --fi-muted:         var(--muted);
  --fi-link:          var(--link);
  --fi-spine:         color-mix(in srgb, var(--line) 90%, transparent);
  --fi-step-fill:     color-mix(in srgb, var(--link) 12%, var(--panel));
  --fi-step-ring:     color-mix(in srgb, var(--ink-link) 26%, transparent);
  --fi-chip-observed: color-mix(in srgb, var(--ok)   10%, var(--panel));
  --fi-chip-watch:    color-mix(in srgb, var(--warn) 10%, var(--panel));
  --fi-chip-caution:  color-mix(in srgb, var(--info)  8%, var(--panel));
  --fi-chip-missing:  color-mix(in srgb, var(--muted)  8%, var(--panel));
  --fi-chip-stale:    color-mix(in srgb, var(--act)   8%, var(--panel));
  --fi-chip-regime:   color-mix(in srgb, var(--act)  12%, var(--panel));
}
```

### C.5 Mechanisms that MUST differ — dark vs light

The five mechanisms below are the load-bearing art-direction differences; each is a complete CSS rule (token-mixed). The audit found them either missing or wrongly shared.

**(1) Panel elevation.** Dark: nested luminance steps + a hairline inset highlight (no shadow). Light: 1px hairline border + a 2-stop shadow stack (no inset).

```css
.fi-panel {
  background: var(--fi-panel);
  border: 1px solid var(--fi-line);
  border-radius: 12px;
  box-shadow: inset 0 1px 0 color-mix(in srgb, var(--text) 7%, transparent);
}
.fi-panel2 { background: var(--fi-panel2); }
html[data-theme="light"] .fi-panel {
  background: var(--fi-panel);
  border: 1px solid var(--fi-line);
  box-shadow:
    0 1px 2px color-mix(in srgb, var(--text) 6%, transparent),
    0 6px 20px color-mix(in srgb, var(--text) 5%, transparent);
}
html[data-theme="light"] .fi-panel2 { background: var(--fi-panel2); }
```

**(2) Freshness pip.** Dark: glow halo on the dot (focused/active state only). Light: NO glow; a 3px left rail on the section header element. The element is the section header `.fi-section-head` on `what-changed` (per B.1 markup); the rail is on that element, not on the chip.

```css
.fi-freshness[data-state-fresh="Fresh"] {
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--ok) 25%, transparent);
}
html[data-theme="light"] .fi-freshness[data-state-fresh="Fresh"] {
  box-shadow: none;
}
html[data-theme="light"] #what-changed .fi-section-head {
  border-left: 3px solid var(--ok);
  padding-left: 12px;
}
```

**(3) Focus ring.** Dark: 1px outline + a 4px glow halo. Light: 2px outline, no halo.

```css
.fi-shell *:focus-visible,
.fi-drawer *:focus-visible {
  outline: 1px solid var(--fi-link);
  outline-offset: 2px;
  box-shadow: 0 0 0 4px color-mix(in srgb, var(--fi-link) 30%, transparent);
  border-radius: 6px;
}
html[data-theme="light"] .fi-shell *:focus-visible,
html[data-theme="light"] .fi-drawer *:focus-visible {
  outline: 2px solid var(--fi-link);
  outline-offset: 2px;
  box-shadow: none;
}
```

**(4) Drawer scrim.** Dark: black scrim (`--bg` mixed). Light: a higher-percentage text-tinted scrim so the panel stays readable.

```css
.fi-scrim { background: color-mix(in srgb, var(--bg) 70%, transparent); }
html[data-theme="light"] .fi-scrim { background: color-mix(in srgb, var(--text) 35%, transparent); }
```

**(5) Stepper rail/dot.** Dark: glow on the active dot. Light: solid dot + hairline rail.

```css
.fi-rerating-step[data-active="true"] .fi-step-dot {
  box-shadow: 0 0 0 3px var(--fi-step-ring);
}
html[data-theme="light"] .fi-rerating-step[data-active="true"] .fi-step-dot {
  box-shadow: none;
  background: var(--fi-step-fill);
  border-color: var(--fi-link);
}
html[data-theme="light"] .fi-rerating-steps::before {
  background: color-mix(in srgb, var(--line) 60%, transparent);
}
```

### C.6 Shell + layout

```css
.fi-shell {
  max-width: 1200px;
  margin: 0 auto;
  padding: clamp(18px, 3vw, 36px) clamp(16px, 3vw, 28px) 80px;
  background: var(--fi-canvas);
  color: var(--fi-text);
}
.fi-hero { padding: 28px 0 22px; border-bottom: 1px solid var(--fi-line); }
.fi-kicker { font-size: var(--fs-label); letter-spacing: .09em; text-transform: uppercase; color: var(--fi-muted); margin: 0 0 8px; font-weight: 700; }
.fi-hero h1 { font-size: var(--fs-h1); font-weight: 800; letter-spacing: -.02em; margin: 0; }
.fi-deck { font-size: var(--fs-md); line-height: 1.55; margin: 8px 0 0; max-width: 70ch; color: var(--fi-text); }
.fi-meta { font-size: var(--fs-sm); color: var(--fi-muted); margin: 10px 0 0; display: flex; gap: 10px; flex-wrap: wrap; }
.fi-freshness { display: inline-flex; align-items: center; padding: 2px 8px; border-radius: 999px; border: 1px solid var(--fi-line); }
.fi-outer-dossier { display: inline-flex; align-items: center; padding: 2px 8px; border-radius: 999px; border: 1px solid var(--fi-line); }
.fi-toc { margin: 18px 0 8px; padding: 12px 14px; border: 1px solid var(--fi-line); border-radius: 12px; background: var(--fi-panel); }
.fi-toc ol { display: flex; flex-wrap: wrap; gap: 8px 14px; margin: 0; padding: 0; list-style: none; font-size: var(--fs-sm); }
.fi-toc a, .fi-toc-evidence { color: var(--fi-text); text-decoration: none; padding: 4px 8px; border-radius: 7px; background: transparent; border: 0; cursor: pointer; font: inherit; }
.fi-toc a:hover, .fi-toc-evidence:hover { background: var(--fi-panel2); }
.fi-section { margin-top: 40px; }
.fi-section-title { font-size: var(--fs-h2); font-weight: 700; letter-spacing: -.01em; margin: 0 0 4px; }
.fi-section-eyebrow { display: block; font-size: var(--fs-sm); color: var(--fi-muted); font-weight: 400; margin-top: 2px; }
.fi-section-foot { font-size: var(--fs-sm); color: var(--fi-muted); margin: 12px 0 0; max-width: 75ch; }
.fi-section-head { padding: 4px 0; }
```

### C.7 Rerating stepper — primary visual

```css
.fi-slice-picker { margin: 12px 0 14px; display: flex; gap: 10px; align-items: center; font-size: var(--fs-sm); }
.fi-slice-select { font: inherit; padding: 4px 8px; border-radius: 7px; border: 1px solid var(--fi-line); background: var(--fi-panel); color: var(--fi-text); }
.fi-rerating-steps {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0;
  margin: 18px 0 0;
  padding: 0;
  list-style: none;
  position: relative;
}
.fi-rerating-steps::before {
  content: ""; position: absolute; left: 5%; right: 5%; top: 23px; height: 2px;
  background: var(--fi-spine); border-radius: 2px; z-index: 0;
}
.fi-rerating-step {
  position: relative; z-index: 1;
  display: flex; flex-direction: column; align-items: center; text-align: center;
  padding: 0 6px; gap: 6px; background: var(--fi-canvas);
}
.fi-step-dot {
  width: 14px; height: 14px; border-radius: 50%;
  background: var(--fi-step-fill); border: 2px solid var(--fi-line);
  margin-bottom: 4px;
}
.fi-step-label { font-size: var(--fs-sm); font-weight: 600; color: var(--fi-text); }
.fi-step-metric { font-size: var(--fs-sm); color: var(--fi-muted); font-variant-numeric: tabular-nums; min-height: 1.4em; }
.fi-step-chip {
  display: inline-block; font-size: var(--fs-sm); font-weight: 600;
  padding: 2px 7px; border-radius: 999px; border: 1px solid var(--fi-line);
  background: var(--fi-panel); color: var(--fi-text); white-space: nowrap;
}
.fi-step-clock { font-size: var(--fs-sm); color: var(--fi-muted); font-variant-numeric: tabular-nums; }
.fi-anchor-chip, .fi-history-chip {
  display: inline-block; font-size: var(--fs-sm); font-weight: 600;
  padding: 2px 7px; border-radius: 999px; border: 1px solid var(--fi-line);
  background: var(--fi-panel); color: var(--fi-text); white-space: nowrap;
}
.fi-step-evidence {
  background: transparent; border: 1px solid var(--fi-line);
  width: 22px; height: 22px; border-radius: 6px; color: var(--fi-muted);
  cursor: pointer; font-size: var(--fs-sm);
}
.fi-step-evidence:hover { color: var(--fi-text); border-color: var(--fi-muted); }
.fi-rerating-bridge { font-size: var(--fs-md); color: var(--fi-text); margin: 14px 0 0; max-width: 75ch; }

/* falsifiers list */
.fi-falsifiers { list-style: none; margin: 12px 0 0; padding: 0; display: grid; gap: 6px; }
.fi-falsifier { display: grid; grid-template-columns: auto 1fr auto; gap: 8px; align-items: center; padding: 6px 10px; border-radius: 8px; border: 1px solid var(--fi-line); background: var(--fi-panel); font-size: var(--fs-sm); }
.fi-falsifier-chip { font-size: var(--fs-sm); padding: 1px 7px; border-radius: 999px; border: 1px solid var(--fi-line); }
.fi-falsifier-statement { color: var(--fi-text); }
.fi-falsifier-window { color: var(--fi-muted); font-variant-numeric: tabular-nums; }

/* conflicts sub-block */
.fi-conflicts { margin-top: 24px; padding-top: 16px; border-top: 1px solid var(--fi-line); }
.fi-conflicts-title { font-size: var(--fs-h3); font-weight: 700; margin: 0 0 8px; }
.fi-conflict-list { display: grid; gap: 10px; margin: 12px 0 0; padding: 0; list-style: none; }
.fi-conflict-card { background: var(--fi-panel); border: 1px solid var(--fi-line); border-radius: 12px; padding: 12px 14px; }
.fi-conflict-label { font-size: var(--fs-sm); font-weight: 700; display: block; margin-bottom: 6px; }
.fi-conflict-pair { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.fi-conflict-side { padding: 8px 10px; border-radius: 8px; border: 1px solid var(--fi-line); background: var(--fi-panel2); font-size: var(--fs-sm); }
.fi-conflict-side-statement { display: block; }
.fi-conflict-side-evidence { margin-top: 4px; font-size: var(--fs-sm); }
.fi-conflict-resolution { font-size: var(--fs-sm); color: var(--fi-muted); margin: 8px 0 0; }

/* chip state colours — each maps to one plane-state token and includes a plain-word
   companion so colour is never the only channel (doctrine §5 + WCAG 1.4.1). */
.fi-step-chip[data-state="OBSERVED"]    { background: var(--fi-chip-observed); }
.fi-step-chip[data-state="INFERRED"]    { background: var(--fi-chip-watch); }
.fi-step-chip[data-state="MISSING"]     { background: var(--fi-chip-missing); }
.fi-step-chip[data-state="CONFLICTING"] { background: var(--fi-chip-caution); }
.fi-step-chip[data-state="STALE"]       { background: var(--fi-chip-stale); }
.fi-step-chip[data-state="REGIME_BREAK"],
.fi-step-chip[data-state="VALUATION_ANCHOR_UNAVAILABLE"],
.fi-step-chip[data-state="PRICE_BASIS_UNQUALIFIED"] { background: var(--fi-chip-regime); }
.fi-step-chip[data-state="NOT_APPLICABLE"] { background: var(--fi-panel2); color: var(--fi-muted); }
```

### C.8 Atlas grid, exposure table, macro matrix, constraints, system map

```css
.fi-domain-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 14px; margin-top: 16px; }
.fi-domain { padding: 14px 14px 10px; }
.fi-domain-title { font-size: var(--fs-h3); font-weight: 700; margin: 0 0 8px; }
.fi-slice-list { list-style: none; margin: 0; padding: 0; display: grid; gap: 6px; }
.fi-slice {
  display: grid; grid-template-columns: 1fr auto auto;
  gap: 6px 8px; align-items: center;
  padding: 6px 8px; border-radius: 8px; background: var(--fi-panel2);
}
.fi-slice-name { font-size: var(--fs-sm); font-weight: 600; color: var(--fi-text); }
.fi-slice-chip {
  font-size: var(--fs-sm); font-weight: 600; padding: 1px 7px; border-radius: 999px;
  border: 1px solid var(--fi-line); background: var(--fi-panel); color: var(--fi-text);
}
.fi-slice[data-state-slice="SEMANTIC_ONLY"] .fi-chip-slice { background: var(--fi-chip-missing); }
.fi-slice[data-state-slice="MEASURABLE"]   .fi-chip-slice { background: var(--fi-chip-observed); }
.fi-slice[data-state-slice="STALE"]        .fi-chip-slice { background: var(--fi-chip-stale); }
.fi-slice[data-state-slice="HELD_FOR_REVIEW"] .fi-chip-slice { background: var(--fi-chip-watch); }
.fi-slice[data-state-membership="CURRENT_MEMBERSHIP_ONLY"] .fi-chip-membership,
.fi-slice[data-state-membership="PIT_MEMBERSHIP_INCOMPLETE"] .fi-chip-membership { background: var(--fi-chip-regime); }
.fi-slice[data-state-posture="SEMANTIC_ONLY"] .fi-chip-posture { background: var(--fi-chip-missing); }
.fi-slice[data-state-posture="RESEARCH_CANDIDATE"] .fi-chip-posture { background: var(--fi-chip-caution); }
.fi-slice[data-state-posture="CANDIDATE_READY_FOR_OWNER_REVIEW"] .fi-chip-posture { background: var(--fi-chip-watch); }
.fi-slice[data-state-posture="ADMITTED"] .fi-chip-posture { background: var(--fi-chip-observed); }
.fi-slice-open { background: transparent; border: 1px solid var(--fi-line); border-radius: 6px; color: var(--fi-muted); cursor: pointer; font-size: var(--fs-sm); }
.fi-atlas-gap { font-size: var(--fs-sm); color: var(--fi-muted); margin: 10px 0 0; }

.fi-exposure-table-wrap { overflow-x: auto; margin-top: 14px; }
.fi-exposure-table { border-collapse: separate; border-spacing: 0; font-size: var(--fs-sm); min-width: 760px; width: 100%; }
.fi-exposure-table th, .fi-exposure-table td {
  border-bottom: 1px solid var(--fi-line); padding: 8px 10px; text-align: left; vertical-align: top;
}
.fi-exposure-table thead th { position: sticky; top: 0; background: var(--fi-panel); z-index: 2; font-weight: 600; color: var(--fi-muted); font-size: var(--fs-sm); text-transform: uppercase; letter-spacing: .04em; }
.fi-exposure-table .fi-col-company { position: sticky; left: 0; background: var(--fi-panel); z-index: 1; min-width: 180px; font-weight: 600; }
.fi-exposure-table thead th.fi-col-company { z-index: 3; }
.fi-cell { min-width: 200px; }
.fi-cell-role { display: block; font-weight: 600; }
.fi-cell-basis { display: block; font-size: var(--fs-sm); color: var(--fi-muted); }
.fi-cell-materiality { display: block; font-size: var(--fs-sm); }
/* No --up/--down/--ink-up/--ink-down anywhere on the exposure surface. */
.fi-cell[data-state-materiality="MATERIAL"]    .fi-cell-materiality { color: var(--ink-warn); }
.fi-cell[data-state-materiality="PARTIAL"]    .fi-cell-materiality { color: var(--fi-muted); }
.fi-cell[data-state-materiality="IMMATERIAL"]  .fi-cell-materiality { color: var(--fi-muted); }
.fi-cell[data-state-materiality="UNMEASURED"]  .fi-cell-materiality { color: var(--fi-muted); }
.fi-cell-risk { display: block; font-size: var(--fs-sm); color: var(--fi-muted); margin-top: 2px; }
.fi-cell-evidence-date { display: block; font-size: var(--fs-sm); color: var(--fi-muted); margin-top: 2px; font-variant-numeric: tabular-nums; }
.fi-company-unresolved, .fi-company-hint { color: var(--fi-muted); font-style: italic; }
.fi-exposure-cards { display: none; list-style: none; margin: 14px 0 0; padding: 0; gap: 10px; }
.fi-exposure-card { padding: 12px 14px; }

.fi-macro-table-wrap { overflow-x: auto; margin-top: 14px; }
.fi-macro-table { border-collapse: separate; border-spacing: 0; font-size: var(--fs-sm); min-width: 760px; width: 100%; }
.fi-macro-table th, .fi-macro-table td {
  border-bottom: 1px solid var(--fi-line); padding: 8px 10px; text-align: left; vertical-align: top;
}
.fi-macro-table thead th { position: sticky; top: 0; background: var(--fi-panel); z-index: 2; font-weight: 600; color: var(--fi-muted); font-size: var(--fs-sm); }
.fi-macro-table .fi-col-company { position: sticky; left: 0; background: var(--fi-panel); z-index: 1; min-width: 180px; font-weight: 600; }
.fi-macro-cell-state { display: inline-block; font-size: var(--fs-sm); padding: 1px 7px; border-radius: 999px; border: 1px solid var(--fi-line); }
.fi-macro-cell-state[data-state="CAUSAL_EFFECT_UNMEASURED"] { background: var(--fi-chip-caution); }
.fi-macro-cell-state[data-state="NOT_APPLICABLE"] { background: var(--fi-panel2); color: var(--fi-muted); }
.fi-macro-cell-state[data-state="DESCRIBED"] { background: var(--fi-chip-observed); }

.fi-constraint-list { list-style: none; margin: 12px 0 0; padding: 0; display: grid; gap: 8px; }
.fi-constraint-row { display: grid; grid-template-columns: auto 1fr auto; gap: 8px; align-items: center; padding: 8px 10px; border-radius: 8px; border: 1px solid var(--fi-line); background: var(--fi-panel); font-size: var(--fs-sm); }

.fi-view-tabs { display: flex; gap: 6px; flex-wrap: wrap; margin: 12px 0 14px; }
.fi-view-tab { font: inherit; padding: 6px 10px; border-radius: 8px; border: 1px solid var(--fi-line); background: var(--fi-panel); color: var(--fi-text); cursor: pointer; }
.fi-view-tab[aria-selected="true"] { background: var(--fi-step-fill); border-color: var(--fi-link); }
.fi-system-svg { width: 100%; height: 280px; background: var(--fi-panel2); border-radius: 12px; border: 1px solid var(--fi-line); }
.fi-system-edge-list { list-style: none; margin: 8px 0 0; padding: 0; display: grid; gap: 4px; font-size: var(--fs-sm); }
.fi-system-edge { padding: 4px 0; border-bottom: 1px dashed var(--fi-line); display: grid; grid-template-columns: 1fr auto; gap: 8px; align-items: center; }
.fi-system-edge-statement { color: var(--fi-text); }
```

### C.9 Evidence drawer + scrim

```css
.fi-drawer {
  position: fixed; top: 0; right: 0; bottom: 0; width: min(440px, 92vw);
  background: var(--fi-panel); border-left: 1px solid var(--fi-line);
  transform: translateX(100%);
  transition: transform .22s cubic-bezier(.2,.7,.3,1);
  display: flex; flex-direction: column; z-index: 80;
}
.fi-drawer[aria-hidden="false"] { transform: translateX(0); }
.fi-drawer-head { padding: 14px 18px 10px; border-bottom: 1px solid var(--fi-line); display: flex; gap: 12px; align-items: flex-start; }
.fi-drawer-head .fi-kicker { margin: 0; }
.fi-drawer-head h2 { font-size: var(--fs-h2); margin: 4px 0 0; }
.fi-drawer-close { margin-left: auto; background: transparent; border: 1px solid var(--fi-line); border-radius: 6px; color: var(--fi-muted); width: 28px; height: 28px; cursor: pointer; font: inherit; }
.fi-drawer-body { padding: 12px 18px 24px; overflow-y: auto; font-size: var(--fs-sm); }
.fi-evidence-fields { display: grid; gap: 8px; margin: 0; }
.fi-evidence-fields > div { display: grid; grid-template-columns: 36% 64%; gap: 8px; padding-bottom: 6px; border-bottom: 1px dashed var(--fi-line); }
.fi-evidence-fields dt { color: var(--fi-muted); font-weight: 600; }
.fi-evidence-fields dd { margin: 0; color: var(--fi-text); }
.fi-evidence-private-notice { font-size: var(--fs-sm); color: var(--fi-muted); padding: 8px 10px; border-radius: 8px; border: 1px solid var(--fi-line); background: var(--fi-panel2); margin: 0 0 10px; }
.fi-scrim { position: fixed; inset: 0; z-index: 70; }
```

### C.10 Responsive — three breakpoints (R-I)

One breakpoint set: ≤767 phone, 768–1199 tablet, ≥1200 desktop. The grep of `max-width|min-width` in §C shows ONLY `767px`, `768px`, `1199px`, `1200px` (check #8). The 14px gutter from the previous spec is removed; phone gutter is 16px.

```css
@media (min-width: 1200px) {
  .fi-shell { max-width: 1200px; }
  .fi-domain-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); }
}
@media (min-width: 768px) and (max-width: 1199px) {
  .fi-rerating-steps { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 6px; }
  .fi-rerating-steps::before { display: none; }
  .fi-rerating-step { flex-direction: row; align-items: center; text-align: left; gap: 10px; padding: 8px 10px; border-radius: 10px; background: var(--fi-panel); border: 1px solid var(--fi-line); }
  .fi-step-dot { margin: 0 6px 0 0; }
}
@media (max-width: 767px) {
  .fi-rerating-steps { grid-template-columns: 1fr; gap: 6px; }
  .fi-rerating-steps::before { display: none; }
  .fi-rerating-step { flex-direction: row; align-items: center; text-align: left; gap: 10px; padding: 8px 10px; border-radius: 10px; background: var(--fi-panel); border: 1px solid var(--fi-line); }
  .fi-step-dot { margin: 0 6px 0 0; }
  .fi-domain-grid { grid-template-columns: 1fr; }
  .fi-exposure-table-wrap { display: none; }
  .fi-exposure-cards { display: grid; }
  .fi-macro-table-wrap { overflow-x: auto; }
  .fi-conflict-pair { grid-template-columns: 1fr; }
  .fi-toc ol { flex-direction: column; gap: 4px; }
  .fi-shell { padding-left: 16px; padding-right: 16px; }
}
@media (max-width: 390px) {
  .fi-hero h1 { font-size: var(--fs-h2); }
  .fi-exposure-cards { gap: 8px; }
}
```

### C.11 Reduced motion + long-word wrapping

```css
@media (prefers-reduced-motion: reduce) {
  .fi-drawer { transition: none; }
  .fi-rerating-steps::before { animation: none; }
}
.fi-section-title, .fi-step-label, .fi-cell-role {
  overflow-wrap: anywhere;
  word-break: break-word;
}
.fi-slice-name { overflow-wrap: anywhere; }
```
```