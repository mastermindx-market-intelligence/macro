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

---

## D. EN / ZH label map + missing states

Every visible string the dossier renders, in plain words. Internal enum tokens appear ONLY in `data-state`/`data-*` attributes — never in text nodes. The label map is **closed**: every enum the live contract can deliver has one EN + one ZH row here. The visible "PLANE.state 枚举 / enum" footer copy from the previous spec is removed.

**Bilingual ARIA rule:** every `aria-label` attribute holds plain English; `data-aria-zh` carries the ZH; §E swaps the visible label by reading `data-aria-zh` when `html[data-lang="zh"]`. `t()` is never called inside an attribute (check #5).

### D.0 `fmtMetric` + `fmtClock` (binding render rules)

These two formatters are referenced by every section. They are not enumerated strings — they are algorithms with explicit null/empty handling.

`fmtMetric(metric)`:

1. If `metric.value` is null OR `metric.unit` is null OR `metric.measurement_class` is `QUALITATIVE`: render the plain-word chip "No metric on file / 暂无可用指标" (never "None" or "—").
2. Else render `${value} ${unit}` with the value formatted per `metric.measurement_class` (one decimal place for `RATIO`/`RATE`, two for `PER_SHARE`, zero for `VOLUME_VALUE`/`VOLUME_COUNT`/`REVENUE`/`EXPENSE`/`BALANCE`), then `currency` if present, then a `(period_start – period_end)` parenthetical if both present.

`fmtClock(clock)`:

1. If `clock.published_at` is null: render `"observed <observed_at>"` using `observation.observed_at` from `source_records[]`, then the grain word from §D.10. Never `[:10]` on a null.
2. Else render `clock.published_at` formatted as `YYYY-MM-DD` plus the grain word.

### D.1 Plane state chips (rerating nodes + system edges)

| enum (`data-state`) | EN | ZH |
|---|---|---|
| OBSERVED | `On file — observed` | `已观察，有据可查` |
| INFERRED | `On file — inferred` | `有据，推断得出` |
| MISSING | `No dated reading on file` | `暂无可追溯的读数` |
| CONFLICTING | `The numbers disagree` | `读数之间存在分歧` |
| STALE | `Older than freshness window` | `已超出新鲜度窗口` |
| REGIME_BREAK | `Not comparable to history` | `与历史不可比` |
| VALUATION_ANCHOR_UNAVAILABLE | `No valuation anchor on file` | `暂无估值锚点` |
| PRICE_BASIS_UNQUALIFIED | `No qualified price basis` | `价格口径未达合格` |
| NOT_APPLICABLE | `Not applicable here` | `此处不适用` |

(Edge `evidence_state` chips use the same row mapping under the subkey `evidence_state`.)

### D.2 Slice state chips — STANCE WORDS (per R-K)

| enum | EN | ZH |
|---|---|---|
| SEMANTIC_ONLY | `Definition only` | `仅完成定义` |
| RESEARCH_EVIDENCE_AVAILABLE | `Research evidence on file` | `已存研究证据` |
| MEASURABLE | `Measurable today` | `当前可量化` |
| PRICE_SURFACE_AVAILABLE | `Price surface available` | `已具备价格曲面` |
| EVALUATION_CONTEXT_AVAILABLE | `Evaluation context available` | `已具备评估背景` |
| RIGHTS_RESTRICTED | `Source rights restricted` | `来源权利受限` |
| STALE | `Stale` | `已陈旧` |
| HELD_FOR_REVIEW | `Held for review` | `待复核` |

(Stance words — "Definition only" / "Measurable today" — describe the slice's *stance* against measurement, not its lifecycle stage.)

### D.3 Basket posture chips — PLAIN WORDS (per R-K)

| enum | EN | ZH |
|---|---|---|
| SEMANTIC_ONLY | `No price basket yet` | `暂无价格组合` |
| BROAD_CONTEXT_AVAILABLE | `Reference basket admitted` | `已收录参考组合` |
| RESEARCH_CANDIDATE | `Research candidate` | `研究候选` |
| CANDIDATE_READY_FOR_OWNER_REVIEW | `Under owner review` | `待负责人复核` |
| ADMITTED | `Admitted price basket` | `已收录价格组合` |

(Plain words; "Reference basket admitted" replaces the prior "Admitted price basket" for the BROAD_CONTEXT_AVAILABLE bucket.)

### D.4 Membership state chips (atlas, per-slice visible chip)

| enum | EN | ZH |
|---|---|---|
| NONE | `No membership recorded` | `未记录成员` |
| CURRENT_MEMBERSHIP_ONLY | `Current membership only — not a history` | `仅为当前成员 — 非历史口径` |
| PIT_MEMBERSHIP_INCOMPLETE | `Point-in-time membership incomplete` | `时点成员数据不完整` |
| PIT_MEMBERSHIP_VALIDATED | `Point-in-time membership validated` | `时点成员数据已校验` |

### D.5 Materiality chips (company exposure)

| enum | EN | ZH |
|---|---|---|
| MATERIAL | `Material exposure` | `重要敞口` |
| PARTIAL | `Partial` | `部分` |
| IMMATERIAL | `Immaterial` | `不重大` |
| UNMEASURED | `Not yet measured` | `尚未量化` |

### D.6 Role vocabulary (company exposure cells)

| enum | EN | ZH |
|---|---|---|
| DIRECT_PURE_OR_HIGH_EXPOSURE | `Direct, high exposure` | `直接且高敞口` |
| DIRECT_DIVERSIFIED | `Direct, diversified` | `直接，多元化` |
| ENABLER_OR_TOLL_COLLECTOR | `Enabler or toll collector` | `基础设施或收费方` |
| SECOND_ORDER_BENEFICIARY | `Second-order beneficiary` | `间接受益方` |
| PROXY_OR_ADJACENCY | `Proxy or adjacency` | `代理或邻近` |
| AT_RISK_OR_DISRUPTED | `At risk or disrupted` | `承压或被颠覆` |
| HEDGE_OR_OFFSET | `Hedge or offset` | `对冲或抵消` |

### D.7 Exposure basis (company exposure cells)

| enum | EN | ZH |
|---|---|---|
| SEGMENT_REVENUE | `Segment revenue` | `分部收入` |
| TRANSACTION_VOLUME | `Transaction volume` | `交易笔数` |
| AUC_A | `Assets under custody` | `在管资产规模` |
| AUM | `Assets under management` | `在管资产` |
| NOTIONAL | `Notional value` | `名义金额` |
| QUALITATIVE | `Qualitative read` | `定性读数` |
| NOT_SEPARATELY_DISCLOSED | `Not separately disclosed` | `未单独披露` |

### D.8 Exposure state chips (cell text)

| enum | EN | ZH |
|---|---|---|
| MEASURED | `Measured` | `已量化` |
| EXPOSURE_NOT_SEPARATELY_DISCLOSED | `Exposure not separately disclosed` | `敞口未单独披露` |
| DIRECT_DIVERSIFIED | `Direct, diversified` | `直接，多元化` |
| QUALITATIVE_ONLY | `Qualitative only` | `仅作定性` |

### D.9 Constraint names

| enum | EN | ZH |
|---|---|---|
| regulatory_permission | `Regulatory permission` | `监管许可` |
| capital | `Capital adequacy` | `资本充足` |
| funding_liquidity | `Funding and liquidity` | `融资与流动性` |
| network_access | `Network access` | `网络接入` |
| settlement_finality | `Settlement finality` | `结算终局性` |
| data_benchmark_control | `Data and benchmark control` | `数据与基准控制` |
| distribution | `Distribution reach` | `分销覆盖` |
| integration_switching | `Integration and switching cost` | `集成与切换成本` |
| trust_identity | `Trust and identity` | `信任与身份` |
| resilience | `Operational resilience` | `运营韧性` |

### D.10 Macro drivers (matrix columns)

| enum | EN | ZH |
|---|---|---|
| policy_rates | `Policy rates` | `政策利率` |
| yield_curve | `Yield curve` | `收益率曲线` |
| deposit_funding | `Deposit funding` | `存款融资` |
| credit_growth | `Credit growth` | `信贷增长` |
| losses_defaults | `Losses and defaults` | `损失与违约` |
| housing | `Housing activity` | `房地产活动` |
| equity_levels | `Equity market levels` | `股市水平` |
| volatility | `Volatility regime` | `波动率环境` |
| issuance_ma | `Issuance and M&A` | `发行与并购` |
| catastrophe_reinsurance | `Catastrophe and reinsurance` | `巨灾与再保` |
| regulation_capital | `Regulation and capital` | `监管与资本` |
| fx | `FX regime` | `汇率环境` |
| liquidity | `Market liquidity` | `市场流动性` |

### D.11 Lag (macro matrix cells)

| enum | EN | ZH |
|---|---|---|
| IMMEDIATE | `Immediate` | `即时` |
| ONE_QUARTER | `About a quarter` | `约一个季度` |
| TWO_TO_FOUR_QUARTERS | `Two to four quarters` | `两到四个季度` |
| MULTI_YEAR | `Multi-year` | `多年` |
| UNKNOWN | `Lag not measured` | `尚未测算时滞` |

### D.12 Freshness state chips

| enum | EN | ZH |
|---|---|---|
| FRESH | `Fresh` | `新鲜` |
| AGING | `Aging` | `趋于陈旧` |
| SOURCE_STALE | `Source is stale` | `来源已陈旧` |
| NO_EVIDENCE | `No evidence on file` | `暂无证据` |

### D.13 First-vertical state chips (coverage.first_vertical.state)

| enum | EN | ZH |
|---|---|---|
| NOT_BUILT | `Not built yet` | `尚未构建` |
| SYNTHETIC | `Synthetic construction` | `合成构建` |
| RESEARCH_RECORDS | `Research records only` | `仅研究记录` |
| PRODUCTION_PROVEN | `Production-proven` | `已生产验证` |

### D.14 Outer-dossier state chips (outer_dossier_ref.state)

| enum | EN | ZH |
|---|---|---|
| AVAILABLE | `Outer dossier accepted` | `外部报告已接入` |
| OUTER_CONTRACT_NOT_ACCEPTED | `Outer dossier not accepted` | `外部报告尚未接入` |
| UNAVAILABLE | `Outer dossier unavailable` | `外部报告暂不可用` |

### D.15 Material-changes freshness state chips

| enum | EN | ZH |
|---|---|---|
| FRESH | `Fresh` | `新鲜` |
| AGING | `Aging` | `趋于陈旧` |
| SOURCE_STALE | `Source is stale` | `来源已陈旧` |
| NO_EVIDENCE | `No evidence on file` | `暂无证据` |

### D.16 Expectations history state chips (D.11 binding)

| enum | EN | ZH |
|---|---|---|
| DATED_CONSENSUS_AVAILABLE | `Dated consensus on file` | `已存可追溯的市场预期` |
| NO_HISTORICAL_CONSENSUS | `No dated consensus on file` | `暂无可追溯的市场预期` |
| MANAGEMENT_GUIDANCE_ONLY | `Management guidance only` | `仅管理层指引` |

### D.17 Valuation anchor label map (inside the valuation node)

| enum | EN | ZH |
|---|---|---|
| EPS | `Earnings per share` | `每股收益` |
| CORE_EPS | `Core earnings per share` | `核心每股收益` |
| TBVPS | `Tangible book per share` | `每股有形账面` |
| BVPS | `Book per share` | `每股账面` |
| FCF_PER_SHARE | `Free cash flow per share` | `每股自由现金流` |
| DPS | `Dividend per share` | `每股股息` |
| EMBEDDED_VALUE_PER_SHARE | `Embedded value per share` | `每股内含价值` |
| NAV_PER_SHARE | `Net asset value per share` | `每股净资产` |
| NOT_APPLICABLE | `Per-share anchor not applicable` | `每股锚点不适用` |

| enum | EN | ZH |
|---|---|---|
| P_E | `P/E multiple` | `市盈率` |
| P_TBV | `P/TBV multiple` | `市净率（有形）` |
| P_B | `P/B multiple` | `市净率` |
| EV_EBITDA | `EV/EBITDA` | `企业价值倍数` |
| FCF_YIELD | `Free cash flow yield` | `自由现金流收益率` |
| DIVIDEND_YIELD | `Dividend yield` | `股息率` |
| P_EV | `P/EV multiple` | `P/EV 倍数` |
| P_NAV | `P/NAV multiple` | `P/NAV 倍数` |
| P_AUM | `P/AUM multiple` | `P/AUM 倍数` |
| NOT_APPLICABLE | `Multiple not applicable` | `倍数不适用` |

| enum | EN | ZH |
|---|---|---|
| TRAILING_12M | `Trailing 12 months` | `过去 12 个月` |
| FORWARD_12M | `Forward 12 months` | `未来 12 个月` |
| FORWARD_24M | `Forward 24 months` | `未来 24 个月` |
| CURRENT_BOOK | `Current book` | `当前账面` |
| NOT_APPLICABLE | `Horizon not applicable` | `时不适用` |

`valuation_anchor.state`:

| enum | EN | ZH |
|---|---|---|
| AVAILABLE | `Anchor available` | `锚点可用` |
| VALUATION_ANCHOR_UNAVAILABLE | `No valuation anchor available` | `暂无估值锚点` |

### D.18 Falsifier state chips

| enum | EN | ZH |
|---|---|---|
| WATCHING | `Watching` | `观察中` |
| NOT_YET_EVALUABLE | `Not yet evaluable` | `暂无法评估` |

### D.19 Price-basis state chips (basket_state.price_basis_state)

| enum | EN | ZH |
|---|---|---|
| PRICE_BASIS_UNQUALIFIED | `Price basis not qualified` | `价格口径未达合格` |
| TOTAL_RETURN_QUALIFIED | `Total-return basis qualified` | `总回报口径合格` |
| PRICE_RETURN_QUALIFIED | `Price-return basis qualified` | `价格回报口径合格` |

### D.20 Weighting family chips (basket_state.weighting_family)

| enum | EN | ZH |
|---|---|---|
| EQUAL_WEIGHT | `Equal weight` | `等权重` |
| FLOAT_CAP_CONTEXT | `Float-cap context` | `流通上限背景` |
| EXPOSURE_WEIGHT | `Exposure weight` | `敞口权重` |
| EXPOSURE_CAPPED_WEIGHT | `Exposure-capped weight` | `敞口封顶权重` |
| STRATIFIED_EQUAL_WEIGHT | `Stratified equal weight` | `分层等权重` |

### D.21 Identity state chips (company_exposures[].identity.state, source_records[].identity_state)

| enum | EN | ZH |
|---|---|---|
| IDENTITY_VALIDATED | `Identity validated` | `身份已确认` |
| IDENTITY_UNRESOLVED | `Identity unresolved` | `身份尚未确认` |
| RESEARCH_HINT_UNVALIDATED | `Research hint, not validated` | `研究线索，尚未确认` |

### D.22 Company-route state chips (company_exposures[].company_route.state)

| enum | EN | ZH |
|---|---|---|
| AVAILABLE | `Route available` | `路由可用` |
| IDENTITY_UNRESOLVED | `Route unavailable — identity unresolved` | `路由暂不可用 — 身份尚未确认` |

### D.23 Source rights state chips (source_records[].rights_state) — DRAWER SUPPRESSION

| enum | EN | ZH |
|---|---|---|
| DIRECT_DISPLAY_OK | `Direct display OK` | `可直接展示` |
| DERIVED_DISPLAY_OK | `Derived display OK` | `可展示派生内容` |
| SOURCE_RIGHTS_HELD | `Source rights restrict display` | `来源权利限制展示` |
| INTERNAL_ONLY | `Internal only` | `仅供内部使用` |

**Suppression rule (binding, R-F):** when `rights_state` is `SOURCE_RIGHTS_HELD` or `INTERNAL_ONLY`, the drawer shows `publisher`, `source_family`, `locator` words and the five `limitations` fields but NEVER `value` / `excerpt` / `native_digest`. A plain-word notice renders: "Private evidence — source rights restrict display." / "私有证据 — 来源权利限制展示。"

### D.24 Source statement-mode chips (source_records[].statement_mode)

| enum | EN | ZH |
|---|---|---|
| REPORTED_FACT | `Reported fact` | `报告事实` |
| CATALOG_DESCRIPTION | `Catalog description` | `目录描述` |
| ANNOUNCED_ARRANGEMENT | `Announced arrangement` | `已公告安排` |
| FORWARD_TARGET | `Forward target` | `前瞻目标` |
| ATTRIBUTED_INTERPRETATION | `Attributed interpretation` | `归因解读` |

### D.25 Source published-at grain words (source.published_at_grain)

| enum | EN | ZH |
|---|---|---|
| DAY | `day` | `日` |
| MONTH | `month` | `月` |
| QUARTER | `quarter` | `季` |
| YEAR | `year` | `年` |
| UNKNOWN | `grain not stated` | `未说明粒度` |

### D.26 Metric measurement-class words (metric.measurement_class)

| enum | EN | ZH |
|---|---|---|
| VOLUME_VALUE | `volume` | `量值` |
| VOLUME_COUNT | `count` | `计数` |
| REVENUE | `revenue` | `收入` |
| EXPENSE | `expense` | `支出` |
| BALANCE | `balance` | `余额` |
| RATIO | `ratio` | `比率` |
| RATE | `rate` | `费率` |
| PER_SHARE | `per share` | `每股` |
| QUALITATIVE | `qualitative` | `定性` |

### D.27 Metric gross/net basis words (metric.gross_net_basis)

| enum | EN | ZH |
|---|---|---|
| GROSS | `gross` | `总额` |
| NET | `net` | `净额` |
| NOTIONAL | `notional` | `名义` |
| NOT_APPLICABLE | `not applicable` | `不适用` |

### D.28 Metric average/end words (metric.average_end)

| enum | EN | ZH |
|---|---|---|
| AVERAGE | `average` | `平均` |
| END | `end` | `期末` |
| NOT_APPLICABLE | `not applicable` | `不适用` |

### D.29 Metric reported/derived/estimated words (metric.reported_derived_estimated)

| enum | EN | ZH |
|---|---|---|
| REPORTED | `reported` | `原始报告` |
| DERIVED | `derived` | `推算` |
| ESTIMATED | `estimated` | `估计` |

### D.30 Indicator direction words (indicator.direction)

| enum | EN | ZH |
|---|---|---|
| LEADING | `leading` | `领先` |
| COINCIDENT | `coincident` | `同步` |
| LAGGING | `lagging` | `滞后` |

### D.31 Indicator state words (indicator.state)

| enum | EN | ZH |
|---|---|---|
| OBSERVED | `observed` | `已观察` |
| MISSING | `missing` | `缺失` |
| STALE | `stale` | `已陈旧` |

### D.32 Plane word map (conflicts[].{left,right}.plane)

| enum | EN | ZH |
|---|---|---|
| operating | `Operating` | `经营` |
| expectations | `Expectations` | `市场预期` |
| valuation | `Valuation` | `估值` |
| price | `Price` | `价格` |
| regime | `Regime` | `制度环境` |
| policy | `Policy` | `政策` |

### D.33 System-view edge relationship words (per view)

| view | enum | EN | ZH |
|---|---|---|---|
| contractual_flow | PAYS | `pays` | `支付` |
| contractual_flow | SETTLES | `settles` | `结算` |
| contractual_flow | CLEARS | `clears` | `清算` |
| contractual_flow | GUARANTEES | `guarantees` | `担保` |
| contractual_flow | FUNDS | `funds` | `融资` |
| contractual_flow | INSURES | `insures` | `承保` |
| contractual_flow | LENDS | `lends` | `放贷` |
| contractual_flow | HOLDS_CUSTODY | `holds custody` | `托管` |
| infrastructure_access | LICENSES | `licenses` | `许可` |
| infrastructure_access | SUPERVISES | `supervises` | `监管` |
| infrastructure_access | GRANTS_ACCESS | `grants access` | `授予接入` |
| infrastructure_access | PUBLISHES_BENCHMARK | `publishes benchmark` | `发布基准` |
| infrastructure_access | RATES | `rates` | `评级` |
| infrastructure_access | PROVIDES_DATA | `provides data` | `提供数据` |
| infrastructure_access | REQUIRES_MEMBERSHIP | `requires membership` | `要求成员资格` |
| public_equity_economics | EARNS_FEE_FROM | `earns fee from` | `向…收取费用` |
| public_equity_economics | BEARS_CREDIT_RISK_OF | `bears credit risk of` | `承担…信用风险` |
| public_equity_economics | CAPTURES_SPREAD_ON | `captures spread on` | `赚取…价差` |
| public_equity_economics | RECOGNISES_REVENUE_FROM | `recognises revenue from` | `确认…收入` |
| public_equity_economics | DEPENDS_ON_VOLUME_OF | `depends on volume of` | `依赖…数量` |

### D.34 Input-receipt owner + state word maps (provenance footer)

`input_receipts[].owner`:

| enum | EN | ZH |
|---|---|---|
| sector_intelligence | `Sector intelligence` | `子行业情报` |
| theme_graph | `Theme graph` | `主题图谱` |
| financial_intelligence | `Financial intelligence` | `金融情报` |
| expectations_revisions | `Expectations revisions` | `预期修订` |
| market_data | `Market data` | `市场数据` |
| baskets | `Baskets` | `组合` |
| macro_rates_credit | `Macro rates and credit` | `宏观利率与信贷` |
| identity | `Identity` | `身份` |
| private_publication | `Private publication` | `私有发布` |

`input_receipts[].state`:

| enum | EN | ZH |
|---|---|---|
| READ | `ready` | `就绪` |
| UNAVAILABLE | `unavailable` | `暂不可用` |
| NOT_ACCEPTED | `not accepted` | `未接入` |
| DEGRADED | `degraded` | `已降级` |

Provenance footer line shape (per non-`READ` entry): `"<owner words> — <state words> · <note if present>"` EN / `"<owner words> — <state words> · <note 字段如有>"` ZH.

### D.35 Degraded-section section enum + state word maps

`degraded_sections[].section`:

| enum | section id | EN | ZH |
|---|---|---|---|
| what_changed | `what-changed` | `What changed` | `近期变化` |
| rerating_map | `rerating-map` | `Rerating map` | `重估链路` |
| system_map | `system-map` | `System map` | `系统图` |
| subtheme_atlas | `subtheme-atlas` | `Subtheme atlas` | `子主题图谱` |
| company_exposure | `company-exposure` | `Company exposure` | `公司敞口` |
| macro_matrix | `macro-matrix` | `Macro matrix` | `宏观矩阵` |
| constraint_map | `constraint-map` | `Constraint map` | `约束图` |
| evidence_drawer | (aside; degraded path hides trigger chip) | `Evidence drawer` | `证据抽屉` |

`degraded_sections[].state`:

| enum | EN | ZH |
|---|---|---|
| AVAILABLE | `available` | `可用` |
| UNAVAILABLE | `unavailable` | `不可用` |
| PARTIAL | `partial` | `部分可用` |

A `degraded_sections[]` entry with `state ∈ {UNAVAILABLE, PARTIAL}` renders a plain-word notice (`mx-empty` + `mx-empty-why`) at the named section's mount.

### D.36 The eleven mandatory missing states (D.11 binding, plain-word chips at named DOM locations)

This is the canonical table the audit pinned D.11 to. Every row is one schema token; the chip binds to the named DOM location and reads as a visible, plain-word chip with a text companion (never colour-only).

| # | Token | Contract path (live schema, line reference) | DOM location | EN chip | ZH chip |
|---|---|---|---|---|---|
| 1 | NO_HISTORICAL_CONSENSUS | `$defs.expectations_plane[0].history.state` enum (`schema.json` line 1186) | `rerating-map` expectations node chip | `No dated consensus on file` | `暂无可追溯的市场预期` |
| 2 | VALUATION_ANCHOR_UNAVAILABLE | `$defs.valuation_anchor[0].state` enum + `$defs.plane_state` VALUATION_ANCHOR_UNAVAILABLE (schema.json line 1630) | `rerating-map` valuation node chip + anchor chip | `No valuation anchor available` | `暂无估值锚点` |
| 3 | PRICE_BASIS_UNQUALIFIED | `$defs.plane_state` PRICE_BASIS_UNQUALIFIED (schema.json plane_state enum) | `rerating-map` price node chip | `No qualified price basis` | `价格口径未达合格` |
| 4 | REGIME_BREAK_NOT_COMPARABLE | `$defs.plane[0].comparability_state[0]` enum (schema.json line 1062) | any `rerating-map` node chip + `system-map` edge chip | `Regime break — not comparable` | `制度断裂 — 不可比` |
| 5 | CURRENT_MEMBERSHIP_ONLY | `$defs.basket_state[0].membership_state` enum (schema.json line 1456) | `subtheme-atlas` per-slice membership chip (visible) | `Current membership only — not a history` | `仅为当前成员 — 非历史口径` |
| 6 | PIT_MEMBERSHIP_INCOMPLETE | `$defs.basket_state[0].membership_state` enum (same path) | `subtheme-atlas` per-slice membership chip (visible) | `Point-in-time membership incomplete` | `时点成员数据不完整` |
| 7 | CAUSAL_EFFECT_UNMEASURED | `macro_matrix[].state` enum (schema.json line 345) | `macro-matrix` cell chip (visible) | `Causal effect not measured` | `因果效应尚未测算` |
| 8 | EXPOSURE_NOT_SEPARATELY_DISCLOSED | `exposure.state` enum (schema.json line 2254) | `company-exposure` cell chip (visible text — never a `focus` handler on a `<td>`) | `Exposure not separately disclosed` | `敞口未单独披露` |
| 9 | IDENTITY_UNRESOLVED | `company_exposures[].identity.state` + `source_records[].identity_state` enum (schema.json lines 2428 / 1985) | `company-exposure` row chip + `evidence-drawer` chip (visible, bilingual) | `Identity unresolved` | `身份尚未确认` |
| 10 | SOURCE_STALE | `freshness.state` + `material_changes[].freshness_state` + `slices[].freshness.state` enum (schema.json line 578 / coverage line 149) | `what-changed` header chip + `rerating-map` node chip | `Source is stale` | `来源已陈旧` |
| 11 | SOURCE_RIGHTS_HELD | `source_records[].rights_state` enum (schema.json line 1985) | `evidence-drawer` chip + suppression rule (D.23) | `Source rights restrict display` | `来源权利限制展示` |

Each of the eleven tokens appears ≥1 time in §B markup as a `data-state-*`/`data-*` binding so the CSS / hydration can render the chip (check #12 — `awk '/^## B\./,/^## C\./' $F | grep -c <TOKEN>` ≥ 1 per token).

### D.37 The ten conflict labels (cards inside `.fi-conflicts`)

| enum (`conflict_id`) | EN label | ZH label |
|---|---|---|
| EARNINGS_UP_P_E_DOWN | `Earnings up, multiple down` | `盈利上升，倍数下降` |
| BOOK_UP_P_B_DOWN | `Book value up, multiple down` | `账面价值上升，倍数下降` |
| NII_UP_CREDIT_WORSE | `Net interest income up, credit worsening` | `净利息收入上升，信贷恶化` |
| POLICY_SUPPORT_NIM_PRESSURE | `Policy supports demand, margins under pressure` | `政策支撑需求，息差承压` |
| REGULATORY_RATIO_DOWN_REGIME_BREAK | `Regulatory ratio down, regime break` | `监管比率下降，制度断裂` |
| PLAN_DISCLOSED_EXECUTION_PENDING | `Plan disclosed, execution pending` | `计划已披露，执行待落地` |
| TAIL_RISK_DOWN_CURRENT_EARNINGS_WEAK | `Tail risk down, current earnings weak` | `尾部风险下降，当期盈利偏弱` |
| PRICE_UP_CAUSAL_EVENT_EFFECT_UNPROVEN | `Price up, causal effect not proven` | `价格上升，因果效应未证实` |
| CAPITAL_COST_UP_GROWTH_STILL_STRONG | `Cost of capital up, growth still strong` | `资本成本上升，增长仍然强劲` |
| VOLUME_UP_REVENUE_MATERIALITY_UNPROVEN | `Volume up, revenue materiality not proven` | `交易量上升，收入重要性未证实` |

### D.38 Action labels and footer copy

| Surface | EN | ZH |
|---|---|---|
| Theme Tracker card action (§F.1) | `Open Finance Intelligence` | `打开金融情报` |
| Financials launch action (§F.2) | `Open Finance Intelligence` | `打开金融情报` |
| Slice selector label (§B.2) | `Slice` | `切片` |
| Slice "open" button (B.4) | `Open this slice` | `打开该切片` |
| Evidence button (per node / per row) | `Open evidence` | `打开证据` |
| Drawer close | `Close evidence drawer` | `关闭证据抽屉` |
| System view: expand | `Expand` | `展开` |
| System view: collapse | `Collapse` | `收起` |
| Section foot (generic) | `Read the underlying receipts before acting on any line.` | `请先查阅原始凭据再行判断。` |
| Conflict card footer | `Unresolved by design — both statements stand.` | `设计上不予调和 — 两种陈述同时成立。` |
| Falsifier list heading | `What we're watching` | `我们正在观察` |
| Atlas footer chip | `<n> slices not yet mapped` | `<n> 个切片尚未映射` |

---

## E. Hydration contract + data-free shell

The §B markup is a data-free shell with one mount point per section. This section is the binding hydration contract the build lane implements verbatim.

### E.0 Single read URL

```
const FI_READ_URL = "__FI_READ_URL__";   // placeholder; bound at integration into
                                         // the shared foundation route. The spec
                                         // names no path.
```

### E.1 Hydration fetch

```js
fetch(FI_READ_URL, {
  credentials: "include",
  cache: "no-store",
  headers: { Accept: "application/json" },
})
```

The document lives in one in-memory closure variable only. Deep-link hashes `#evidence=<record_id>` and `#slice=<slice_id>` resolve against the in-memory document.

### E.2 FORBIDDEN storage (binding)

The hydration layer MUST NOT use any of the following:

- `localStorage`
- `sessionStorage`
- `IndexedDB`
- the Cache API (`caches.*`)
- service workers (`navigator.serviceWorker.*`)
- inline `<script type="application/json">` embedding
- any inline copy of payload into the DOM before the fetch resolves

The only place payload lands before hydration is the in-memory closure variable. (check #10 — these strings appear ONLY inside this list in §E.)

### E.3 Response status mapping

| Status | JSON `error` (if any) | Page state | UI treatment |
|---|---|---|---|
| 200 | — | `AVAILABLE` | full §B shell hydrated from the document |
| 401 | — | `SIGNED_OUT` | title + deck + TOC only; one `.mx-empty` + `.mx-empty-why` notice: `"Sign in to read current research" / "请登录以查阅当前研究"`. Sign-in CTA links to the existing `?return=<path>` pattern. All section bodies hidden. |
| 402 | — | `NOT_ENTITLED` | title + deck + TOC only; plain-word notice: `"This dossier is part of the research tier" / "此报告为研究层内容"`. Upgrade CTA. No sections render. **The previous spec's "slice grid chips + cohort posture chips" claim is removed — there is no public projection; only the static hero + TOC render.** |
| 403 | — | `NOT_ENTITLED` | same as 402 |
| 503 | `PRIVATE_STORE_UNAVAILABLE` | `PRIVATE_STORE_UNAVAILABLE` | title + deck + TOC + section shells; one `.mx-empty` + `.mx-empty-why` notice: `"Private evidence store unavailable" / "私有证据库暂不可用"`. (Per R-K: the prior copy "Outer dossier not accepted — research context only" was mis-bound; that wording belongs to `outer_dossier_ref.state` per D.14 and is NOT used here.) |
| 503 | `NO_GENERATION` | `NO_GENERATION` | plain-word notice: `"No evidence generation published yet — re-drawn after the next nightly" / "尚未发布证据版本，夜间更新后重绘"`. (Per R-K: the prior "refresh in a moment" wording is removed.) |
| 503 | `GENERATION_TORN` | `GENERATION_TORN` | plain-word notice: `"Generation interrupted — partial context only" / "生成中断 — 仅展示部分背景"`. Affected sections carry `data-state-partial="true"`. |
| 503 | `CONTRACT_INVALID` | `CONTRACT_INVALID` | plain-word notice: `"Contract mismatch — showing public shell only" / "契约不一致 — 仅展示公开外壳"`. No sections render; title + deck + TOC only. |
| Network failure | — | `NETWORK_ERROR` | plain-word notice: `"Couldn't load — try again" / "未能加载 — 请重试"`. Retry button. |
| Other | — | `UNKNOWN` | generic `mx-empty` + `mx-empty-why`: `"Read failed" / "读取失败"`. |

Every state uses the `.mx-empty` (the block) + `.mx-empty-why` (the one-line reason) classes; theme/lock are honoured throughout.

### E.4 Keyboard / ARIA behaviour contract

| Element | Event | State change | ARIA change | Focus rule |
|---|---|---|---|---|
| `.fi-view-tab` (3 tabs, generated from `system_views[]` payload order) | `click` / `ArrowLeft` / `ArrowRight` / `Home` / `End` | roving `tabindex` (selected=0, others=-1) | `aria-selected=true` on clicked, `false` on siblings | Focus moves to clicked tab; show the matching `role=tabpanel`, hide others |
| `.fi-system-expand` | `click` | `aria-expanded` flips | `aria-controls` panel toggles `hidden` | Focus stays on the expand button; the now-revealed list is announced via `aria-live=polite` |
| `.fi-evidence-trigger`, `.fi-step-evidence`, `.fi-constraint-evidence`, `.fi-slice-open`, `.fi-toc-evidence` | `click` | drawer `aria-hidden` flips to `false`; `<main>` receives `inert` | drawer `hidden`/`inert` removed; scrim shown | Focus moves to the drawer's first focusable; previous-active element saved for restore |
| `.fi-drawer-close`, `.fi-scrim`, `Escape` keydown | `click` / `keydown` | drawer `aria-hidden=true`; `<main>` loses `inert` | drawer `hidden inert` reapplied | Focus restored to the opener (deep-link open → returns to the section heading that triggered it) |
| Drawer focus trap | `keydown Tab` / `Shift+Tab` at edges | none | none | Cycle within drawer's focusable elements; do not escape to inert background |
| `.fi-slice-select` (native) | `change` | re-render `.fi-rerating-steps`, `.fi-falsifiers`, `.fi-conflicts` for the new slice | URL hash updates to `#slice=<slice_id>` | Focus stays on the select |
| `hashchange` / `popstate` | listener | re-render slice selector + drawer open if `#evidence=<id>` | drawer `aria-hidden=false` for `#evidence` | Focus moves to drawer's first focusable for `#evidence`; no focus shift for `#slice` (select retains focus) |
| Theme toggle (`.theme-toggle` global) | `click` | `html[data-theme]` flips between `dark` and `light` | none | Persist via existing `theme.js` |
| Language toggle (`.lang-toggle` global) | `click` | `html[data-lang]` flips between `en` and `zh`; `.l-en` / `.l-zh` visibility swaps; `data-en` / `data-zh` swap; aria-label read from `data-aria-zh` when `[data-lang=zh]` | `aria-label` swapped | Persist via existing `theme.js` |
| `prefers-reduced-motion: reduce` | media-query change | drawer's CSS transition collapses to `none` | none | none |
| Conflict card | `mouseenter` / `focus` | none | visible line + button (no hover-only meaning) | none |

The drawer is the only modal surface. Tab order follows DOM order. No keyboard shortcut invents new gestures.

### E.5 Field bindings → DOM mount points (cross-reference)

| `data-fi-mount` | Section | Hydration populates |
|---|---|---|
| `shell` | B.0 | `data-state-outer-dossier`, `data-state-coverage`, hero kicker/meta (one-time) |
| `provenance` | B.0 | one `.fi-receipt-line` per `input_receipts[]` entry whose `state ≠ READ` |
| `what-changed-list` | B.1 | one `<li class="fi-change-row" data-state-freshness data-change-id>` per `material_changes[]` entry, sorted by `event_clock.published_at` desc |
| `slice-select` | B.2 | one `<option value="<slice_id>">{name_en} / {name_zh}</option>` per `coverage.first_vertical.slice_ids` joined with `slices[]` |
| `rerating-steps` | B.2 | exactly four `<li class="fi-rerating-step fi-node-{name}">` in the order operating, expectations, valuation, price |
| `rerating-bridge` | B.2 | text node = `slices[].rerating.bridge` (fallback static copy from §B.2) |
| `falsifiers` | B.2 | one `<li class="fi-falsifier" data-state-falsifier>` per `slices[].falsifiers[]` |
| `conflicts` (`.fi-conflict-list`) | B.2 | one `<li class="fi-conflict-card" data-conflict-id>` per `conflicts[]` |
| `domain-grid` | B.4 | one `<section class="fi-domain">` per `domains[]` in payload order; inside, one `<li class="fi-slice">` per `slices[]` entry whose `domain_id` matches |
| `coverage eyebrow` | B.4 | text node from `coverage.{domains_populated, domains_total, slices_populated, slices_total}` |
| `atlas-gap` | B.4 | text node from `coverage.slices_total − sum(rendered)` |
| `exposure-rows` | B.5 | one `<tr>` per `company_exposures[]` sorted by `issuer_label` (EN, case-insensitive); `<td>` per `cells[]` cell (absent slice column → "No role recorded / 未记录角色") |
| `exposure-cards` | B.5 | one `<li class="fi-exposure-card">` per `company_exposures[]` entry (phone only; hidden ≥768) |
| `macro-rows` | B.6 | one `<tr data-slice-id>` per unique `slice_id` in `macro_matrix[]` in payload order; cell for each (slice, driver) pair; absent → "Not mapped / 未映射" |
| `constraint-list` | B.7 | one `<li class="fi-constraint-row">` per `constraints[]` |
| `view-tabs` / `view-panels` | B.3 | one `<button role="tab">` and one `<div role="tabpanel">` per `system_views[]` in payload order |
| `evidence-body` | B.0 aside | `dl.fi-evidence-fields` populated from `source_records[]`; suppression rule applied (D.23) |

---

## F. Two entry modules — static markup, no payload bindings

Both entry modules become **static markup** with NO payload-bound Jinja. No `{% for` over document data, no `{{ fin.… }}` bindings. Static bilingual copy uses the repo's `data-en`/`data-zh` idiom and is swapped by existing `theme.js` on `html[data-lang]` flip. The CTA href is a route variable `{{ fi_dossier_href }}` (placeholder; bound at integration into the shared foundation route — the spec names no path).

### F.1 `_finance_sector_deep_dive.html.j2` — Theme Tracker card (navigation-only)

A navigation-only card placed AFTER the existing `rp` "What to look at first" module and OUTSIDE the canonical theme lanes (per packet §F + R11 §3). The card must NEVER claim a canonical theme stage or compute the seven Theme Tracker asymmetry legs for Finance.

```jinja
{# Sector deep dives — Financials / Finance Intelligence.                #}
{# Stays outside the canonical theme lanes; non-canonical context card.   #}
{# STATIC markup — no payload bindings. Hydration is owned by §E.         #}
<section class="sot-sector-deep-dive" aria-labelledby="sot-finance-deep-dive-title"
         data-state-coverage="AVAILABLE" data-state-outer-dossier="AVAILABLE">
  <p class="sot-kicker">
    <span class="l-en" data-en="Sector deep dive">Sector deep dive</span>
    <span class="l-zh" data-zh="子行业深读">子行业深读</span>
  </p>
  <h3 id="sot-finance-deep-dive-title">
    <span class="l-en" data-en="Financials · Finance Intelligence">Financials · Finance Intelligence</span>
    <span class="l-zh" data-zh="金融 · 金融情报">金融 · 金融情报</span>
  </h3>
  <p class="sot-deep-dive-deck">
    <span class="l-en" data-en="Research context across the financial system — not a canonical theme stage or trade call.">Research context across the financial system — not a canonical theme stage or trade call.</span>
    <span class="l-zh" data-zh="对金融体系的研究背景 — 非主题生命周期阶段或交易指令。">对金融体系的研究背景 — 非主题生命周期阶段或交易指令。</span>
  </p>
  <a class="sot-deep-dive-action"
     href="{{ fi_dossier_href }}"
     data-state-cta="navigation"
     aria-label="Open Finance Intelligence" data-aria-zh="打开金融情报">
    <span class="l-en" data-en="Open Finance Intelligence ↗">Open Finance Intelligence ↗</span>
    <span class="l-zh" data-zh="打开金融情报 ↗">打开金融情报 ↗</span>
  </a>
</section>
```

No counts, no `material_changes` slice, no `coverage.{slices_populated, slices_total}` — the card is the eyebrow + title + one static sentence + CTA, per R-D.

### F.2 `_finance_intelligence_launch.html.j2` — Financials page module (static)

A compact launch module placed near the existing back-link on `basket/us_sector_financials.html` (and the analogous Sector Intelligence route). It retains the existing broad Financials price context (equal-weight S&P 500 Financials participation, NOT a buy list, NOT an exposure-pure Finance basket).

```jinja
{# Finance Intelligence launch — placed near back-link on basket/us_sector_financials.html.
   STATIC markup — no payload bindings. Hydration is owned by §E.            #}
<section class="fi-launch" aria-labelledby="fi-launch-title"
         data-state-coverage="AVAILABLE">
  <p class="fi-kicker">
    <span class="l-en" data-en="Finance Intelligence">Finance Intelligence</span>
    <span class="l-zh" data-zh="金融情报">金融情报</span>
  </p>
  <h3 id="fi-launch-title">
    <span class="l-en" data-en="Research context for the financial system">Research context for the financial system</span>
    <span class="l-zh" data-zh="金融体系的研究背景">金融体系的研究背景</span>
  </h3>
  <p class="fi-launch-deck">
    <span class="l-en" data-en="Broad Financials price context stays below — equal-weight, not a buy list. The dossier below is research context only.">Broad Financials price context stays below — equal-weight, not a buy list. The dossier below is research context only.</span>
    <span class="l-zh" data-zh="下方仍保留广义金融价格背景 — 等权重，非买入清单。下方的报告仅作研究背景。">下方仍保留广义金融价格背景 — 等权重，非买入清单。下方的报告仅作研究背景。</span>
  </p>
  <p class="fi-launch-vertical">
    <span class="l-en" data-en="Domains mapped: Money Movement, Securities Infrastructure">Domains mapped: Money Movement, Securities Infrastructure</span>
    <span class="l-zh" data-zh="已映射子域：资金流动、证券基础设施">已映射子域：资金流动、证券基础设施</span>
  </p>
  <a class="fi-launch-action"
     href="{{ fi_dossier_href }}"
     aria-label="Open Finance Intelligence" data-aria-zh="打开金融情报">
    <span class="l-en" data-en="Open Finance Intelligence ↗">Open Finance Intelligence ↗</span>
    <span class="l-zh" data-zh="打开金融情报 ↗">打开金融情报 ↗</span>
  </a>
</section>
```

The "Domains mapped" wording replaces the prior "Top research domains" (R-J). The two facets "Money Movement" and "Securities Infrastructure" are the static sub-buckets of `coverage.first_vertical` named in §A.0; they are NOT a baked taxonomy — they are the canonical first-vertical split for the dossier, present in the spec by reference to `coverage.first_vertical.name = "Financial Rails & Market Infrastructure"`.

---

## G. Degraded states — public shell behaviour

The dossier must never expose a private payload. Every degraded state shows a typed refusal on the public shell and disables evidence triggers. (Per R-K: §G was tightened — the previous "Outer dossier not accepted — research context only" copy was mis-bound to a 503 path; the wording belongs to `outer_dossier_ref.state` per D.14. The previous "refresh in a moment" copy is removed.)

| Condition | Trigger source | EN foot / banner | ZH foot / banner | Hidden | Still rendered |
|---|---|---|---|---|---|
| `503 PRIVATE_STORE_UNAVAILABLE` | composer fetch fails with `error="PRIVATE_STORE_UNAVAILABLE"` | `Private evidence store unavailable` | `私有证据库暂不可用` | all eight sections render as shells; no evidence refs resolve; no company rows | theme; TOC; chips show N/A |
| `503 NO_GENERATION` | composer has no committed generation this cycle | `No evidence generation published yet — re-drawn after the next nightly` | `尚未发布证据版本，夜间更新后重绘` | all quantitative fields; rerating nodes show "Not applicable here" chips | slice grid renders with `slice_state` chips |
| `503 GENERATION_TORN` | composer aborted mid-write; partial cache | `Generation interrupted — partial context only` | `生成中断 — 仅展示部分背景` | partial numeric data within torn sections | header + TOC + per-section `data-state-partial="true"` indicator |
| `503 CONTRACT_INVALID` | response fails `finance_intelligence_read_model.v1.schema.json` validation | `Contract mismatch — showing public shell only` | `契约不一致 — 仅展示公开外壳` | all eight sections | title + deck + TOC only |
| `outer_dossier_ref.state = OUTER_CONTRACT_NOT_ACCEPTED` | composer surface contract not yet wired | `Outer dossier not accepted — research context only` | `外部报告尚未接入 — 仅作研究背景` | (foot banner only) | dossier body still renders against the local contract |
| `outer_dossier_ref.state = UNAVAILABLE` | outer source down | `Outer dossier unavailable` | `外部报告暂不可用` | (foot banner only) | dossier body still renders against the local contract |
| `401` (signed out) | signed-out request | `Sign in to read current research` | `请登录以查阅当前研究` | all sections | theme toggle, language toggle; Sign-in CTA links to `?return=<path>` |
| `402 / 403` (not entitled) | authenticated but tier does not include Finance Intelligence | `This dossier is part of the research tier` | `此报告为研究层内容` | all sections (per R-D: no public projection; the prior "slice grid chips + cohort posture chips" claim is removed) | theme toggle, language toggle; Upgrade CTA |
| `degraded_sections[].state = UNAVAILABLE` | per-section composer surface empty | `data-fi-mount` block becomes `.mx-empty` + `.mx-empty-why` notice: `Unavailable — <reason if present>` | `不可用 — <reason 字段如有>` | section body | section header + foot |
| `degraded_sections[].state = PARTIAL` | per-section composer partial | `Partial — <reason if present>` | `部分可用 — <reason 字段如有>` | partial numeric data within torn sections | header + TOC + per-section indicator |
| Network failure | fetch rejected / timeout | `Couldn't load — try again` | `未能加载 — 请重试` | all sections | retry button |
| Unknown response | other 5xx | `Read failed` | `读取失败` | all sections | retry button |

The evidence drawer never opens in any degraded state — the trigger buttons get `aria-disabled="true"` and a visible chip `Evidence unavailable` / `证据暂不可用`. No private payload leaks via static, localStorage, IndexedDB, source maps, service workers, or alternate routes (per the carrier packet §15.1 / §15.4 and the §E FORBIDDEN list).

**Conflict pip + card rule (R-H):** the `.fi-conflict-pip` chip and the `.fi-conflict-card` both carry a visible line + an `Open evidence` button; no hover-only meaning anywhere.

**Materiality colour rule (R-J):** MATERIAL → `--ink-warn`; PARTIAL → `--muted` with the word "Partial" / "部分"; IMMATERIAL / UNMEASURED → `--muted` with the word. NEVER `--up`/`--down`/`--ink-up`/`--ink-down` anywhere on the exposure surface (or anywhere else in the dossier).

---

## H. Acceptance matrix — 8 base shots + per-cell close-ups

Per R-H: the full evidence matrix is 8 base shots (`{dark,light} × {en,zh} × {1440 desktop, 390 mobile}`) plus one close-up per acceptance cell. The single "parity" PNG from the previous spec is removed; the 390-only cell is expanded into the 8-shot matrix. The seat's browser-evidence lane runs the harness AFTER the implementation lands; this spec's obligation is only to make every cell achievable without further design intervention.

### H.0 Eight base shots

| # | Theme | Lang | Viewport | File |
|---|---|---|---|---|
| 1 | dark | EN | 1440 | `verify_shots/finance/c00_dark_en_1440.png` |
| 2 | dark | ZH | 1440 | `verify_shots/finance/c00_dark_zh_1440.png` |
| 3 | light | EN | 1440 | `verify_shots/finance/c00_light_en_1440.png` |
| 4 | light | ZH | 1440 | `verify_shots/finance/c00_light_zh_1440.png` |
| 5 | dark | EN | 390 | `verify_shots/finance/c00_dark_en_390.png` |
| 6 | dark | ZH | 390 | `verify_shots/finance/c00_dark_zh_390.png` |
| 7 | light | EN | 390 | `verify_shots/finance/c00_light_en_390.png` |
| 8 | light | ZH | 390 | `verify_shots/finance/c00_light_zh_390.png` |

### H.1 Per-cell close-ups

| Cell | R11 §12 obligation | Design reference | Close-up PNG |
|---|---|---|---|
| 1 | Theme Tracker with Finance sector-deep-dive entry | §F.1 — static eyebrow + title + plain sentence + CTA; no canonical lane contamination | `verify_shots/finance/c01_theme_tracker_deep_dive_{theme}.png` |
| 2 | Financials sector page with Finance Intelligence launch | §F.2 — "Domains mapped" + CTA; broad price context preserved, non-buy-list wording | `verify_shots/finance/c02_financials_launch_{theme}.png` |
| 3 | Finance dossier populated — all seven L1 sections + drawer aside | §B.0–§B.7 + §B.0 aside; C-company archetype (instrument_analyzer) | `verify_shots/finance/c03_dossier_populated_{viewport}_{theme}.png` |
| 4 | Semantic-only slice with honest no-basket state | §B.4 `.fi-slice-no-basket` element + §D.2 SEMANTIC_ONLY chip + §D.38 footer | `verify_shots/finance/c04_semantic_only_slice_{theme}.png` |
| 5 | Candidate-basket slice | §B.4 posture chip `CANDIDATE_READY_FOR_OWNER_REVIEW` with §D.3 plain-word copy "Under owner review" | `verify_shots/finance/c05_candidate_basket_{theme}.png` |
| 6 | Missing-consensus state | §D.11 NO_HISTORICAL_CONSENSUS chip on rerating-map expectations node + plain-word text companion | `verify_shots/finance/c06_missing_consensus_{theme}.png` |
| 7 | Regime-break state | §D.11 REGIME_BREAK_NOT_COMPARABLE chip on a rerating node + `comparability_state` chip when ≠ COMPARABLE | `verify_shots/finance/c07_regime_break_{theme}.png` |
| 8 | Stale-source state | §D.11 SOURCE_STALE chip + §D.12 freshness chip on the what-changed header + per-node chip | `verify_shots/finance/c08_stale_source_{theme}.png` |
| 9 | Company exposure drill | §B.5 sticky table at 1440 + card stack at ≤767; IDENTITY_UNRESOLVED row carries no link; EXPOSURE_NOT_SEPARATELY_DISCLOSED visible chip text | `verify_shots/finance/c09_company_exposure_{viewport}_{theme}.png` |
| 10 | Evidence drawer | §B.0 aside 14-field drawer; `role="dialog"`, `aria-modal="true"`, focus trap, Escape, `inert` on `<main>`; SOURCE_RIGHTS_HELD suppression (D.23) | `verify_shots/finance/c10_evidence_drawer_{theme}.png` |
| 11 | Mobile flow map | §C.10 vertical rerating stepper at ≤767; exposure AND macro matrices become per-row cards listing only present cells; 16px gutter; no page-level horizontal scroll at 390 | `verify_shots/finance/c11_mobile_flow_map_{theme}_390.png` |
| 12 | EN/ZH parity | §D label map covers every visible string; `.l-en` / `.l-zh` swap on `html[data-lang]` flip; `aria-label` reads `data-aria-zh` when `[data-lang=zh]` | `verify_shots/finance/c12_en_zh_parity_{viewport}_{theme}.png` |
| 13 | Light/dark parity | §C.3 dark block + §C.4 light block written as TWO art directions (token-only, no hex/rgb); both rendered + screenshotted | `verify_shots/finance/c13_light_dark_parity_{viewport}.png` |
| 14 | Keyboard-only journey | §E focus rings always visible; Tab order matches DOM; roving tabindex on system tabs; drawer trap works; deep-link open returns focus to section heading | `verify_shots/finance/c14_keyboard_journey_{theme}.png` |

### H.2 Mechanism-by-mechanism proof (the five differing CSS mechanisms)

The audit's strongest finding was that light was a token swap, not a light design. Each of the five mechanisms gets one close-up at 1440 dark EN + 1440 light EN so the seat can verify them visually.

| # | Mechanism | §Close-up dark | §Close-up light |
|---|---|---|---|
| M1 | Panel elevation | `verify_shots/finance/m01_dark_panel_inset.png` | `verify_shots/finance/m01_light_panel_shadow.png` |
| M2 | Freshness pip | `verify_shots/finance/m02_dark_freshness_glow.png` | `verify_shots/finance/m02_light_freshness_rail.png` |
| M3 | Focus ring | `verify_shots/finance/m03_dark_focus_glow.png` | `verify_shots/finance/m03_light_focus_outline.png` |
| M4 | Drawer scrim | `verify_shots/finance/m04_dark_scrim.png` | `verify_shots/finance/m04_light_scrim.png` |
| M5 | Stepper rail/dot | `verify_shots/finance/m05_dark_stepper_glow.png` | `verify_shots/finance/m05_light_stepper_hairline.png` |

### H.3 Responsive × theme × lang matrix

Acceptance requires every one of the 14 cells to hold in BOTH themes AND in BOTH EN/ZH AND at BOTH viewports. The matrix below is the cross-product the seat's harness must walk.

```
dark / 1440 / EN   ✅  dark / 1440 / ZH   ✅
dark /  390 / EN   ✅  dark /  390 / ZH   ✅
light / 1440 / EN  ✅  light / 1440 / ZH  ✅
light /  390 / EN  ✅  light /  390 / ZH  ✅
```

A failing cell in any of the four dimensions (theme × lang × viewport × cell) returns the build lane to the §B/§C owner; the dossier does NOT claim acceptance on partial coverage.

---

## RETURN

**STATUS:** COMPLETE — the spec is the full lane deliverable; every audit finding closed; six stream-safe commits land on the branch.

**RESULT:**

- File: `research/finance/implementation/FINANCE_DOSSIER_DESIGN_SPEC_2026-09-24.md`
- Sections A–H all populated.
- §A binds ONLY to paths in the live `finance_intelligence_read_model.v1.schema.json` (on `origin/main` since `b4c6e4bd`); the prior "not yet on main" claim is removed; every field the page would like but the schema lacks is moved to **GAPS** as a proposed contract amendment.
- §B renders seven L1 sections + one evidence-drawer aside; B.2 is exactly four data-bound nodes; the R11 chain questions are static node captions ≤14 words EN+ZH; `rerating.bridge` is the connective sentence; falsifiers[] render as a separate list (NOT a node); conflicts nested inside `rerating-map` as `.fi-conflicts`; the slice selector is a native `<select>` driving URL hash `#slice=<id>`; **zero `{% for` over document data, zero payload-bound `{{ … }}` Jinja bindings** anywhere in §B or §F.
- §C declares two art directions as full rules; zero hex / rgb / rgba literals in §C, dark block included; all five differing mechanisms written as real CSS; only `767px` / `768px` / `1199px` / `1200px` appear in `max-width`/`min-width`; font sizes only via `--fs-*` tokens.
- §D binds all eleven D.11 missing-state tokens with token | contract path | DOM location | EN | ZH; closes the label map across every enum the live schema can deliver (plane_state 9, slice_state 8, basket posture 5, membership_state 4, materiality 4, role 7, exposure basis 7, exposure state 4, constraint 10, macro driver 13, lag 5, freshness 4, first_vertical 4, outer_dossier 3, material_changes freshness 4, expectations.history 3, valuation_anchor 9+10+5+2, falsifier 2, price_basis 3, weighting 5, identity_state 3, company_route 2, source rights 4 with suppression, statement_mode 5, published_at_grain 5, measurement_class 9, gross_net_basis 4, average_end 3, reported_derived_estimated 3, indicator direction 3, indicator state 3, conflict plane 6, edge relationship per view 21, input_receipts owner 9, input_receipts state 4, degraded_sections section 8, degraded_sections state 3); visible "PLANE.state 枚举 / enum" footer copy removed; bilingual ARIA rule (plain EN in `aria-label`, ZH in `data-aria-zh`, no `t()` inside attributes).
- §E hydration contract: single `FI_READ_URL` placeholder; `credentials:'include'`, `cache:'no-store'`; in-memory closure variable only; explicit FORBIDDEN list; response status table covers 200 / 401 / 402 / 403 / 503 (typed by JSON `error`: PRIVATE_STORE_UNAVAILABLE / NO_GENERATION / GENERATION_TORN / CONTRACT_INVALID) / network failure / unknown; every state uses `.mx-empty` + `.mx-empty-why`; the prior "slice grid chips + cohort posture chips" claim for 402 is removed.
- §F entry modules are static markup only (eyebrow + title + one static plain sentence + CTA); the prior counts / `fin.top_domains` / `evidence_horizon_label` / `coverage_state` / `slices_populated` bindings are removed; CTA href is `{{ fi_dossier_href }}` placeholder; "Top research domains" renamed to "Domains mapped".
- §G degraded-state copy fixed per R-K; "Outer dossier not accepted" rebinds to `outer_dossier_ref.state` (not 503); "refresh in a moment" copy removed; new degraded_sections per-section rows added.
- §H evidence matrix is 8 base shots + 14 per-cell close-ups + 5 mechanism-by-mechanism proof shots + the theme × lang × viewport cross-product; the prior single-parity PNG and 390-only cell are removed.

**GAPS (proposed contract amendments):**

- No `slices[].display_headline` / `slices[].guardrail` / `slices[].user_action`. Tier 1 "what to look at" copy is composed at render time from `operating_implication` + state chips; this is a render-time projection, not a stored field, and is consistent with §13.5's "no owner recalculation in browser" law only because the composer pre-composes the headline before shipping.
- No `coverage.coverage_state` / `coverage.coverage_label` / `freshness.freshness_label` / `material_changes[].evidence_horizon_label`. The page surfaces `freshness.state` and `coverage.{domains_populated, domains_total, slices_populated, slices_total}` (numeric, not labelled).
- No `entry_href` — the dossier's CTA href is a route variable (`{{ fi_dossier_href }}`) bound at integration.
- No `fin.top_domains` — the "Domains mapped" copy is static in §F.2.
- No `fin.slices_populated` / `fin.selected_slices` — the slice selector is driven by `coverage.first_vertical.slice_ids` directly.
- No `conflicts[].resolution` as user-facing string — the schema carries a literal `UNRESOLVED_BY_DESIGN` enum that surfaces only as the §D.38 footer copy.
- No `macro_drivers` / `row.cells` — `macro_matrix[]` is iterated flat and grouped by `slice_id`; the 13-driver enum is the column header set.
- No `nodes[].evidence_state` — the edge-level `evidence_state` is what renders in the step-list equivalent (per §A.3).
- No `slices[].freshness.state` is rendered as a per-slice chip independent of the §A.1/A.4 chip — `freshness.state` lives on `slices[].freshness.state` AND on the top-level `freshness.state`, both consumed per their paths.
- No live-test environment was available — no screenshots produced; the PNG paths in §H are the seat's responsibility against the build lane's output.

**DEVIATIONS:**

- **Mockup deferred to `fin_d1b_mockup` by seat instruction.** This run ships the spec only. The static mockup is delivered by a second lane onto the same PR after this head lands. The spec still binds every mockup obligation (eight sections in the seven + aside count, four data-bound nodes, two art directions, eleven missing states, ten conflicts, ≥1 `SEMANTIC_ONLY` slice, witness rows, mechanism-by-mechanism proof) — the build lane for `fin_d1b_mockup` reads §A–§H of THIS spec as the binding contract.
- §H keeps the "PNG paths are the seat's responsibility" line because the spec author cannot run a browser environment; the eight base shots + per-cell close-ups + mechanism proof shots are the seat's obligation, not this spec's deliverable.
- No other deviations.
```
```