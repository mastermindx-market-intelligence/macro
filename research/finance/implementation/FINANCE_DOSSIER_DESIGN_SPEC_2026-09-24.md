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

- **R11 §5 tier order (verbatim)** — `Tier 1 — What changed … Tier 2 — Rerating map … Tier 3 — System / flow map … Tier 4 — Subtheme atlas … Tier 5 — Company exposure matrix … Tier 6 — Macro/regime matrix … Tier 7 — Constraint map … Tier 8 — Evidence drawer`. The eight section ids in §A are these tiers in this order.
- **Doctrine glance-tier word budget (verbatim, §1 table)** — `title ≤ 4 words; subtitle ≤ 14 words; row ≤ 1 line; footer ≤ 1 sentence`. The dossier's section heads and "what changed" tiles honour this budget; technical detail moves to hover/drawer (Tier 2/3).
- **TP-0 dark/light sentence (verbatim, CLAUDE.md §"Theme art direction")** — "dark = command center: luminance depth, instrument calm, restrained glow; light = research workspace: cool canvas, white material, hairline discipline, shadow instead of glow — two art directions, token substitution alone is never a light design". §C below is written as TWO art directions with material rationale each, not as a token swap.
- **Doctrine §5 light parity ruling** — light panels must be white on a perceptibly deeper canvas, hairlines replace glow, shadow replaces saturation; `--bg:#f7f8fa` ships as the light canvas baseline.
- **Schema source:** the frozen Finance T1 read-model schema is not yet on `origin/main` (verified `git show origin/main:contracts/sector_intelligence/finance_intelligence_read_model.v1.schema.json` returns "does not exist"). This spec binds to the **FROZEN SCHEMA FIELD LIST** in the lane packet. Every visual state below names the schema field/enum it consumes; any field the schema lacks that the design needs is logged under GAPS, never invented in the spec.

**Atlas grid:** 52 slices / 7 domains (`banking_funding`, `capital_markets`, `payments`, `asset_wealth`, `insurance`, `software_trust`, `structural_disruption`) — counts verified from `research/finance/FINANCE_R11_SUBTHEME_ATLAS_V0_1_2026-09-23.json`.

---

## A. Information architecture + field bindings

The dossier is the read-only Finance Intelligence surface that lives AFTER the existing stock / basket / sector workflow. Authority comes from the read-model composer; the UI never recalculates. Eight sections render in the frozen id order below; section ids map 1:1 to Tier 1…Tier 8 in R11 §5.

| § | id | R11 tier | What the user sees (Tier 1 copy budget) | Schema fields consumed | Schema enums used |
|---|---|---|---|---|---|
| A.1 | `what-changed` | Tier 1 — What changed | "Material changes in the financial system this period" — one row per `material_changes[]` entry; plain-word operating implication; freshness chip | `material_changes[].{change_id, event_clock{published_at, observed_at, effective_at}, domain_ids, slice_ids, operating_implication, evidence_refs, conflict_ids, freshness_state}` | `freshness_state ∈ {FRESH, AGING, SOURCE_STALE, NO_EVIDENCE}` |
| A.2 | `rerating-map` | Tier 2 — Rerating map (PRIMARY VISUAL) | Seven-step horizontal stepper at ≥1024 (driver → operating → earnings/book/FCF/capital → expectations → valuation anchor → price recognition → what we're watching); vertical stepper at ≤768. Each node shows label, ONE primary metric, a state chip, a clock, and an evidence action | Per node: `slices[].rerating.{operating, expectations{history{state, observations[]}}, valuation, price}.{state, primary_metric{value,unit,currency,period_start,period_end,measurement_class,numerator,denominator,gross_net_basis,average_end,reported_derived_estimated}, clock, comparability_state, evidence_refs, note}`; `slices[].rerating.falsifier_ids[]` → `falsifiers[].{falsifier_id, statement, window, state}`; `slices[].rerating.bridge`; `valuation_anchor.{primary_per_share_anchor, primary_valuation_anchor, denominator, horizon, information_clock, required_return_context, state}` | PLANE.state ∈ `{OBSERVED, INFERRED, MISSING, CONFLICTING, STALE, REGIME_BREAK, VALUATION_ANCHOR_UNAVAILABLE, PRICE_BASIS_UNQUALIFIED, NOT_APPLICABLE}`; `comparability_state ∈ {COMPARABLE, REGIME_BREAK_NOT_COMPARABLE, MIXED_BASIS, UNKNOWN}`; `expectations.history.state ∈ {DATED_CONSENSUS_AVAILABLE, NO_HISTORICAL_CONSENSUS, MANAGEMENT_GUIDANCE_ONLY}`; `falsifiers[].state ∈ {WATCHING, NOT_YET_EVALUABLE}`; `valuation_anchor.state ∈ {AVAILABLE, VALUATION_ANCHOR_UNAVAILABLE}` |
| A.3 | `system-map` | Tier 3 — System / flow map | Three selectable views (contractual_flow, infrastructure_access, public_equity_economics). 5–8 nodes first paint; expand on interaction. Step-list equivalent for screen readers | `system_views[].{view_id, name_en, name_zh, nodes[]{node_id, label_en, label_zh, node_type, slice_ids, expandable, children_ids}, edges[]{from, to, relationship, evidence_state}}` | `evidence_state ∈ {OBSERVED, INFERRED, MISSING}` (edge-level) |
| A.4 | `subtheme-atlas` | Tier 4 — Subtheme atlas | 7-domain grid of 52 slices; per-slice state chip + basket posture chip. Honest "no price basket" wording where posture is `SEMANTIC_ONLY` | `slices[]{slice_id, domain_id, name_en, name_zh, slice_state, basket_state{posture, incumbent_basket_ids, membership_state, member_count, weighting_family, price_basis_state}, economic_job, revenue_mechanism, retained_risk}`; `domains[].{domain_id, name_en, name_zh, slice_ids}` | `slice_state ∈ {SEMANTIC_ONLY, RESEARCH_EVIDENCE_AVAILABLE, MEASURABLE, PRICE_SURFACE_AVAILABLE, EVALUATION_CONTEXT_AVAILABLE, RIGHTS_RESTRICTED, STALE, HELD_FOR_REVIEW}`; `basket_state.posture ∈ {SEMANTIC_ONLY, BROAD_CONTEXT_AVAILABLE, RESEARCH_CANDIDATE, CANDIDATE_READY_FOR_OWNER_REVIEW, ADMITTED}`; `membership_state ∈ {NONE, CURRENT_MEMBERSHIP_ONLY, PIT_MEMBERSHIP_INCOMPLETE, PIT_MEMBERSHIP_VALIDATED}` |
| A.5 | `company-exposure` | Tier 5 — Company exposure matrix | Sticky first column + sticky slice headers at ≥1024; card stack at ≤768. Cell = role (7-role vocabulary in plain words) + exposure basis + materiality + retained risk + evidence date. Never a hidden score | `company_exposures[]{row_id, issuer_label, ticker_hint, identity{state, company_node_id, security_ref, listing_note}, company_route{href, state}, cells[]{slice_id, role, exposure{basis, numerator, denominator, value, unit, state}, materiality, retained_risk, evidence_date, evidence_refs}}` | `identity.state ∈ {IDENTITY_VALIDATED, IDENTITY_UNRESOLVED, RESEARCH_HINT_UNVALIDATED}`; `role ∈ {DIRECT_PURE_OR_HIGH_EXPOSURE, DIRECT_DIVERSIFIED, ENABLER_OR_TOLL_COLLECTOR, SECOND_ORDER_BENEFICIARY, PROXY_OR_ADJACENCY, AT_RISK_OR_DISRUPTED, HEDGE_OR_OFFSET}` (rendered in plain words per §D); `exposure.basis ∈ {SEGMENT_REVENUE, TRANSACTION_VOLUME, AUC_A, AUM, NOTIONAL, QUALITATIVE, NOT_SEPARATELY_DISCLOSED}`; `exposure.state ∈ {MEASURED, EXPOSURE_NOT_SEPARATELY_DISCLOSED, DIRECT_DIVERSIFIED, QUALITATIVE_ONLY}`; `materiality ∈ {MATERIAL, PARTIAL, IMMATERIAL, UNMEASURED}` |
| A.6 | `macro-matrix` | Tier 6 — Macro / regime matrix | Rows = slices; columns = 13 drivers. Cell describes mechanism + lag, never a stock verdict | `macro_matrix[]{slice_id, driver, mechanism, lag, state}` | `driver ∈ {policy_rates, yield_curve, deposit_funding, credit_growth, losses_defaults, housing, equity_levels, volatility, issuance_ma, catastrophe_reinsurance, regulation_capital, fx, liquidity}`; `lag ∈ {IMMEDIATE, ONE_QUARTER, TWO_TO_FOUR_QUARTERS, MULTI_YEAR, UNKNOWN}`; `state ∈ {DESCRIBED, CAUSAL_EFFECT_UNMEASURED, NOT_APPLICABLE}` |
| A.7 | `constraint-map` | Tier 7 — Constraint map | One row per constraint per slice; every row carries its economic effect | `constraints[]{slice_id, constraint, economic_effect, evidence_refs}` | `constraint ∈ {regulatory_permission, capital, funding_liquidity, network_access, settlement_finality, data_benchmark_control, distribution, integration_switching, trust_identity, resilience}` |
| A.8 | `evidence-drawer` | Tier 8 — Evidence drawer | Inert drawer with focus trap/restore, Escape closes, deep-linkable via `#evidence=<record_id>`; renders 14 required fields | `source_records[]{record_id, source{publisher, source_family, source_uri, locator, published_at, published_at_grain, observed_at, retained_at, retention_ref, native_digest}, business_scope, metric, observation{value, value_high, period_start, period_end, reported_derived_estimated, precision}, temporal{business_valid_from, business_valid_to}, limitations{establishes, does_not_establish, coverage, source_dependence, expiry_trigger}, identity_state, rights_state, statement_mode, correction{predecessor_record_id, reason}, evidence_ref, excerpt}` | `rights_state ∈ {DIRECT_DISPLAY_OK, DERIVED_DISPLAY_OK, SOURCE_RIGHTS_HELD, INTERNAL_ONLY}` |

**Page-level bindings** (consumed once, in the dossier header): `contract_id`, `schema_version`, `generated_at`, `knowledge_cutoff`, `common_as_of`, `sector_ref`, `outer_dossier_ref.{contract_id, dossier_id, dossier_hash, state}` (state ∈ `{AVAILABLE, OUTER_CONTRACT_NOT_ACCEPTED, UNAVAILABLE}`), `snapshot_identity`, `coverage.{domains_total, domains_populated, slices_total, slices_populated, slices_semantic_only, companies_with_records, first_vertical.{name, slice_ids, state ∈ {NOT_BUILT, SYNTHETIC, RESEARCH_RECORDS, PRODUCTION_PROVEN}}}`, `freshness.{evidence_latest_observed_at, state, stale_after_days}`, `input_receipts[].{owner, generation, state ∈ {READ, UNAVAILABLE, NOT_ACCEPTED, DEGRADED}, note}`, `degraded_sections[].{section, state ∈ {AVAILABLE, UNAVAILABLE, PARTIAL}, reason}`.

**First vertical binding:** `coverage.first_vertical.name = "Financial Rails & Market Infrastructure"` (per frozen schema); the entry-module card (§F) exposes the two facets **Money Movement** and **Securities Infrastructure** as plain-word sub-tabs.


---

## B. DOM skeletons per section

All class names use the `fi-` prefix (finance-intelligence). All copy uses the `{{ t('en','zh') }}` idiom from `templates/capital_structure.html.j2:1`. Internal enum tokens appear ONLY in `data-state`/`data-*` attributes; visible text uses plain words per §D.

### B.0 Page shell

```html
<main class="fi-shell" id="fi-shell" data-state-coverage="{{ coverage.first_vertical.state }}"
      data-state-outer-dossier="{{ outer_dossier_ref.state }}">
  <header class="fi-hero" aria-labelledby="fi-hero-title">
    <p class="fi-kicker">{{ t('Finance Intelligence', '金融情报') }}</p>
    <h1 id="fi-hero-title">{{ t('Financial Rails & Market Infrastructure', '金融基础设施与市场运作') }}</h1>
    <p class="fi-deck">{{ t('Read how the financial system moves money, settles trades and prices assets — context only, not a trade call.', '阅读金融体系如何转移资金、结算交易并为资产定价 — 仅为背景，非交易指令。') }}</p>
    <p class="fi-meta">
      <span data-en="As of {{ common_as_of }}" data-zh="截至 {{ common_as_of }}">{{ t('As of', '截至') }} {{ common_as_of }}</span>
      <span aria-hidden="true">·</span>
      <span data-tip-en="Knowledge cutoff {{ knowledge_cutoff }}" data-tip-zh="知识截止 {{ knowledge_cutoff }}">{{ t('Knowledge cutoff', '知识截止') }} {{ knowledge_cutoff }}</span>
    </p>
  </header>

  <nav class="fi-toc" aria-label="{{ t('Section navigation', '章节导航') }}">
    <ol>
      <li><a href="#what-changed">{{ t('What changed', '近期变化') }}</a></li>
      <li><a href="#rerating-map">{{ t('Rerating map', '重估链路') }}</a></li>
      <li><a href="#system-map">{{ t('System map', '系统图') }}</a></li>
      <li><a href="#subtheme-atlas">{{ t('Subtheme atlas', '子主题图谱') }}</a></li>
      <li><a href="#company-exposure">{{ t('Company exposure', '公司敞口') }}</a></li>
      <li><a href="#macro-matrix">{{ t('Macro matrix', '宏观矩阵') }}</a></li>
      <li><a href="#constraint-map">{{ t('Constraint map', '约束图') }}</a></li>
      <li><a href="#evidence-drawer">{{ t('Evidence', '证据') }}</a></li>
    </ol>
  </nav>

  <!-- Section anchors: A.1 … A.8 in this order. -->
</main>

<aside class="fi-evidence-drawer" id="evidence-drawer" aria-labelledby="fi-evidence-title"
       aria-hidden="true" tabindex="-1" hidden inert>
  <header class="fi-evidence-head">
    <div>
      <p class="fi-kicker">{{ t('Source receipt', '来源凭据') }}</p>
      <h2 id="fi-evidence-title">{{ t('Evidence', '证据') }}</h2>
    </div>
    <button class="fi-drawer-close" id="fi-close-evidence" type="button"
            aria-label="{{ t('Close evidence drawer', '关闭证据抽屉') }}">×</button>
  </header>
  <div class="fi-evidence-body" id="fi-evidence-body"></div>
</aside>
<div class="fi-scrim" id="fi-scrim" hidden></div>
```

### B.1 `what-changed` — material changes

```html
<section id="what-changed" class="fi-section fi-changes" aria-labelledby="fi-changes-title"
         data-state-freshness="{{ material_changes[0].freshness_state }}">
  <h2 id="fi-changes-title" class="fi-section-title">
    {{ t('What changed', '近期变化') }}
    <span class="fi-section-eyebrow">{{ t('Material observations, plain words', '重要观察，直白表述') }}</span>
  </h2>
  <ul class="fi-change-list" role="list">
    {% for ch in material_changes %}
    <li class="fi-change-row" data-state-freshness="{{ ch.freshness_state }}"
        data-change-id="{{ ch.change_id }}">
      <span class="fi-change-clock">{{ ch.event_clock.published_at[:10] }}</span>
      <span class="fi-change-implication">{{ ch.operating_implication }}</span>
      <span class="fi-change-scope" data-en="{{ ch.domain_ids|join(', ') }}"
            data-zh="{{ ch.domain_ids|join('，') }}"></span>
      <button class="fi-evidence-trigger" type="button"
              data-evidence-ids="{{ ch.evidence_refs|join(',') }}"
              aria-label="{{ t('Open evidence', '打开证据') }}">↗</button>
      {% if ch.conflict_ids %}<span class="fi-conflict-pip"
        data-tip-en="{{ t('Conflict on file', '存在分歧') }}"
        data-tip-zh="{{ t('存在分歧', '存在分歧') }}"></span>{% endif %}
    </li>
    {% endfor %}
  </ul>
  <p class="fi-section-foot">
    {{ t('Read the underlying receipts before acting on any line.', '请先查阅原始凭据再行判断。') }}
  </p>
</section>
```

### B.2 `rerating-map` — primary visual

```html
<section id="rerating-map" class="fi-section fi-rerating" aria-labelledby="fi-rerating-title"
         data-state-plane="{{ slice.rerating.expectations.state }}">
  <h2 id="fi-rerating-title" class="fi-section-title">
    {{ t('Rerating map', '重估链路') }}
    <span class="fi-section-eyebrow">{{ t('How a slice reaches per-share value', '一个子主题如何抵达每股价值') }}</span>
  </h2>
  <p class="fi-section-foot">
    {{ t('Horizontal on desktop · vertical on mobile. State chips map to the schema\'s PLANE.state enum.', '桌面端为横向 · 移动端为纵向。状态标签对应 schema 中的 PLANE.state 枚举。') }}
  </p>

  <ol class="fi-rerating-steps" role="list">
    {% set steps = [
      ('fi-step-driver',       slice.rerating.driver_label,        slice.rerating.driver_metric,       slice.rerating.driver.state,       slice.rerating.driver.clock),
      ('fi-step-operating',    slice.rerating.operating_label,     slice.rerating.operating.primary_metric, slice.rerating.operating.state,     slice.rerating.operating.clock),
      ('fi-step-earnings',     slice.rerating.earnings_label,      slice.rerating.earnings.primary_metric,  slice.rerating.earnings.state,      slice.rerating.earnings.clock),
      ('fi-step-expectations', slice.rerating.expectations_label,  slice.rerating.expectations.primary_metric, slice.rerating.expectations.state, slice.rerating.expectations.history.state),
      ('fi-step-valuation',    slice.rerating.valuation_label,     slice.rerating.valuation.primary_metric,    slice.rerating.valuation.state,    slice.rerating.valuation.clock),
      ('fi-step-price',        slice.rerating.price_label,         slice.rerating.price.primary_metric,        slice.rerating.price.state,        slice.rerating.price.clock),
      ('fi-step-watch',        'What we are watching', 'What we are watching', 'NOT_APPLICABLE', slice.rerating.falsifier_horizon)
    ] %}
    {% for cls, label, metric, state, clock in steps %}
    <li class="fi-rerating-step {{ cls }}" data-state-plane="{{ state }}">
      <span class="fi-step-label">{{ label }}</span>
      <span class="fi-step-metric">{{ metric }}</span>
      <span class="fi-step-chip" data-state="{{ state }}">{{ t(state_chip_text[state].en, state_chip_text[state].zh) }}</span>
      <span class="fi-step-clock" data-tip-en="As of {{ clock }}" data-tip-zh="截至 {{ clock }}">{{ clock }}</span>
      <button class="fi-step-evidence" type="button" data-evidence-ids="{{ slice.evidence_refs|join(',') }}"
              aria-label="{{ t('Open evidence for this step', '打开该步骤的证据') }}">↗</button>
    </li>
    {% endfor %}
  </ol>
</section>
```

### B.3 `system-map` — three selectable views

```html
<section id="system-map" class="fi-section fi-system" aria-labelledby="fi-system-title">
  <h2 id="fi-system-title" class="fi-section-title">
    {{ t('System map', '系统图') }}
    <span class="fi-section-eyebrow">{{ t('Three views, never blended', '三种视图，永不混用') }}</span>
  </h2>

  <div class="fi-view-tabs" role="tablist" aria-label="{{ t('Choose a system view', '选择系统视图') }}">
    <button role="tab" id="tab-flow" aria-controls="panel-flow" aria-selected="true"
            class="fi-view-tab" data-view="contractual_flow">
      {{ t('Contractual money and risk flow', '合同化资金与风险流') }}
    </button>
    <button role="tab" id="tab-infra" aria-controls="panel-infra" aria-selected="false"
            class="fi-view-tab" data-view="infrastructure_access" tabindex="-1">
      {{ t('Regulated infrastructure and access', '受监管基础设施与接入') }}
    </button>
    <button role="tab" id="tab-eq" aria-controls="panel-eq" aria-selected="false"
            class="fi-view-tab" data-view="public_equity_economics" tabindex="-1">
      {{ t('Public-equity economics', '公开股权经济') }}
    </button>
  </div>

  {% for view in system_views %}
  <div role="tabpanel" id="panel-{{ view.view_id }}" class="fi-view-panel"
       data-view="{{ view.view_id }}" aria-labelledby="tab-{{ view.view_id }}"
       {% if not loop.first %}hidden{% endif %}>
    <svg class="fi-system-svg" role="img"
         aria-label="{{ view.name_en }} — {{ t('step list follows', '紧随其后是步骤列表') }}">
      <!-- nodes rendered as <g class="fi-svg-node" data-state-evidence="{{ edge.evidence_state }}">…</g>
           edges as <line data-state-evidence="…">. 5–8 nodes first paint; children render on click. -->
    </svg>
    <ol class="fi-system-step-list" role="list">
      {% for node in view.nodes %}
      <li class="fi-system-step" data-state-evidence="{{ node.evidence_state }}"
          data-node-id="{{ node.node_id }}">
        <span class="fi-system-step-label">{{ node.label_en }}</span>
        <span class="fi-system-step-state">{{ t(state_chip_text[node.evidence_state].en, state_chip_text[node.evidence_state].zh) }}</span>
        {% if node.expandable %}
        <button class="fi-system-expand" type="button" aria-expanded="false"
                aria-controls="node-{{ node.node_id }}-children">
          {{ t('Expand', '展开') }}
        </button>
        <ol id="node-{{ node.node_id }}-children" class="fi-system-children" hidden>
          {% for child_id in node.children_ids %}<li data-node-id="{{ child_id }}"></li>{% endfor %}
        </ol>
        {% endif %}
      </li>
      {% endfor %}
    </ol>
  </div>
  {% endfor %}
</section>
```

### B.4 `subtheme-atlas` — 7-domain × 52-slice grid

```html
<section id="subtheme-atlas" class="fi-section fi-atlas" aria-labelledby="fi-atlas-title">
  <h2 id="fi-atlas-title" class="fi-section-title">
    {{ t('Subtheme atlas', '子主题图谱') }}
    <span class="fi-section-eyebrow">{{ t('Seven domains · fifty-two slices', '七个子域 · 五十一个研究切片') }}</span>
  </h2>

  <div class="fi-domain-grid">
    {% for domain in domains %}
    <section class="fi-domain" data-domain-id="{{ domain.domain_id }}" aria-labelledby="domain-{{ domain.domain_id }}-title">
      <h3 id="domain-{{ domain.domain_id }}-title" class="fi-domain-title">
        {{ t(domain.name_en, domain.name_zh) }}
      </h3>
      <ul class="fi-slice-list" role="list">
        {% for slice_id in domain.slice_ids %}
        {% set sl = slices_by_id[slice_id] %}
        <li class="fi-slice" data-slice-id="{{ sl.slice_id }}"
            data-state-slice="{{ sl.slice_state }}"
            data-state-posture="{{ sl.basket_state.posture }}"
            data-state-membership="{{ sl.basket_state.membership_state }}"
            data-state-price-basis="{{ sl.basket_state.price_basis_state }}">
          <span class="fi-slice-name">{{ t(sl.name_en, sl.name_zh) }}</span>
          <span class="fi-slice-chip fi-chip-slice" data-state="{{ sl.slice_state }}">{{ t(slice_state_text[sl.slice_state].en, slice_state_text[sl.slice_state].zh) }}</span>
          <span class="fi-slice-chip fi-chip-posture" data-state="{{ sl.basket_state.posture }}">{{ t(posture_text[sl.basket_state.posture].en, posture_text[sl.basket_state.posture].zh) }}</span>
          {% if sl.basket_state.posture == 'SEMANTIC_ONLY' %}
          <span class="fi-slice-no-basket">{{ t('No price basket yet — research context only.', '暂无可用价格组合 — 仅作为研究背景。') }}</span>
          {% endif %}
          <button class="fi-slice-open" type="button"
                  data-tip-en="{{ t('Open this slice', '打开该切片') }}"
                  data-tip-zh="{{ t('打开该切片', '打开该切片') }}">↗</button>
        </li>
        {% endfor %}
      </ul>
    </section>
    {% endfor %}
  </div>
</section>
```

### B.5 `company-exposure` — sticky matrix / mobile cards

```html
<section id="company-exposure" class="fi-section fi-exposure" aria-labelledby="fi-exposure-title">
  <h2 id="fi-exposure-title" class="fi-section-title">
    {{ t('Company exposure', '公司敞口') }}
    <span class="fi-section-eyebrow">{{ t('Role, basis, materiality — never a hidden score', '角色、口径、重要性 — 绝无暗藏分数') }}</span>
  </h2>

  <div class="fi-exposure-table-wrap">
    <table class="fi-exposure-table" aria-describedby="fi-exposure-desc">
      <caption id="fi-exposure-desc" class="visually-hidden">
        {{ t('Company exposure matrix. Rows are companies. Columns are slices. Cells show role, exposure basis, materiality, retained risk and evidence date.', '公司敞口矩阵。行为公司，列为切片。单元格展示角色、敞口口径、重要性、留存风险和证据日期。') }}
      </caption>
      <thead>
        <tr>
          <th class="fi-col-company" scope="col">{{ t('Company', '公司') }}</th>
          {% for sl in selected_slices %}
          <th class="fi-col-slice" scope="col">{{ t(sl.name_en, sl.name_zh) }}</th>
          {% endfor %}
        </tr>
      </thead>
      <tbody>
        {% for row in company_exposures %}
        <tr data-row-id="{{ row.row_id }}" data-state-identity="{{ row.identity.state }}">
          <th class="fi-col-company" scope="row">
            {% if row.identity.state == 'IDENTITY_VALIDATED' %}
              <a class="fi-company-link" href="{{ row.company_route.href }}">{{ row.issuer_label }}</a>
            {% elif row.identity.state == 'IDENTITY_UNRESOLVED' %}
              <span class="fi-company-unresolved" data-tip-en="{{ t('Identity unresolved — no link', '身份未确认 — 无链接') }}">{{ row.issuer_label }}</span>
            {% else %}
              <span class="fi-company-hint" data-tip-en="{{ t('Research hint, not a validated binding', '研究线索，尚未确认绑定') }}">{{ row.issuer_label }}</span>
            {% endif %}
          </th>
          {% for cell in row.cells %}
          <td class="fi-cell" data-state-role="{{ cell.role }}"
              data-state-exposure="{{ cell.exposure.state }}"
              data-state-materiality="{{ cell.materiality }}">
            <span class="fi-cell-role">{{ t(role_text[cell.role].en, role_text[cell.role].zh) }}</span>
            <span class="fi-cell-basis" data-tip-en="{{ t('Exposure basis', '敞口口径') }}: {{ cell.exposure.basis }}" data-tip-zh="{{ t('敞口口径', '敞口口径') }}: {{ cell.exposure.basis }}">{{ t(basis_text[cell.exposure.basis].en, basis_text[cell.exposure.basis].zh) }}</span>
            <span class="fi-cell-materiality">{{ t(materiality_text[cell.materiality].en, materiality_text[cell.materiality].zh) }}</span>
            <span class="fi-cell-risk">{{ cell.retained_risk }}</span>
            <span class="fi-cell-evidence-date">{{ cell.evidence_date[:10] }}</span>
          </td>
          {% endfor %}
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>

  <ul class="fi-exposure-cards" role="list" aria-label="{{ t('Mobile exposure cards', '移动端敞口卡片') }}">
    {% for row in company_exposures %}
    <li class="fi-exposure-card" data-row-id="{{ row.row_id }}">
      <h3 class="fi-card-issuer">{{ row.issuer_label }}</h3>
      {% for cell in row.cells %}<div class="fi-card-cell" data-state-role="{{ cell.role }}">…</div>{% endfor %}
    </li>
    {% endfor %}
  </ul>
</section>
```

### B.6 `macro-matrix` — mechanism + lag grid

```html
<section id="macro-matrix" class="fi-section fi-macro" aria-labelledby="fi-macro-title">
  <h2 id="fi-macro-title" class="fi-section-title">
    {{ t('Macro matrix', '宏观矩阵') }}
    <span class="fi-section-eyebrow">{{ t('Mechanism and lag, never a stock verdict', '机制与时滞 — 非个股结论') }}</span>
  </h2>
  <div class="fi-macro-table-wrap">
    <table class="fi-macro-table" aria-describedby="fi-macro-desc">
      <caption id="fi-macro-desc" class="visually-hidden">
        {{ t('Macro driver matrix. Rows are slices. Columns are macro drivers. Cells describe the transmission mechanism and the lag.', '宏观驱动矩阵。行为切片，列为宏观驱动。单元格描述传导机制与时滞。') }}
      </caption>
      <thead>
        <tr>
          <th scope="col">{{ t('Slice', '切片') }}</th>
          {% for drv in macro_drivers %}<th scope="col">{{ t(driver_text[drv].en, driver_text[drv].zh) }}</th>{% endfor %}
        </tr>
      </thead>
      <tbody>
        {% for row in macro_matrix %}
        <tr data-slice-id="{{ row.slice_id }}">
          <th scope="row">{{ slices_by_id[row.slice_id].name_en }}</th>
          {% for cell in row.cells %}
          <td data-state="{{ cell.state }}" data-state-lag="{{ cell.lag }}">
            <span class="fi-macro-mechanism">{{ cell.mechanism }}</span>
            <span class="fi-macro-lag" data-tip-en="Lag: {{ cell.lag }}" data-tip-zh="时滞：{{ cell.lag }}">{{ t(lag_text[cell.lag].en, lag_text[cell.lag].zh) }}</span>
          </td>
          {% endfor %}
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</section>
```

### B.7 `constraint-map` — economic effect per constraint

```html
<section id="constraint-map" class="fi-section fi-constraint" aria-labelledby="fi-constraint-title">
  <h2 id="fi-constraint-title" class="fi-section-title">
    {{ t('Constraint map', '约束图') }}
    <span class="fi-section-eyebrow">{{ t('Every constraint links to its economic effect', '每条约束都对应一个经济效应') }}</span>
  </h2>
  <ul class="fi-constraint-list" role="list">
    {% for c in constraints %}
    <li class="fi-constraint-row" data-constraint="{{ c.constraint }}" data-slice-id="{{ c.slice_id }}">
      <span class="fi-constraint-name">{{ t(constraint_text[c.constraint].en, constraint_text[c.constraint].zh) }}</span>
      <span class="fi-constraint-effect">{{ c.economic_effect }}</span>
      <button class="fi-constraint-evidence" type="button"
              data-evidence-ids="{{ c.evidence_refs|join(',') }}"
              aria-label="{{ t('Open evidence', '打开证据') }}">↗</button>
    </li>
    {% endfor %}
  </ul>
</section>
```

### B.8 `evidence-drawer` — 14 required fields

```html
<aside class="fi-evidence-drawer" id="evidence-drawer" aria-labelledby="fi-evidence-title"
       aria-hidden="true" tabindex="-1" hidden inert>
  <header class="fi-evidence-head">
    <p class="fi-kicker">{{ t('Source receipt', '来源凭据') }}</p>
    <h2 id="fi-evidence-title">{{ t('Evidence', '证据') }}</h2>
    <button class="fi-drawer-close" type="button"
            aria-label="{{ t('Close evidence drawer', '关闭证据抽屉') }}">×</button>
  </header>
  <div class="fi-evidence-body">
    <dl class="fi-evidence-fields">
      <div><dt>{{ t('Publisher', '发布方') }}</dt><dd data-field="source.publisher"></dd></div>
      <div><dt>{{ t('Source family', '来源类型') }}</dt><dd data-field="source.source_family"></dd></div>
      <div><dt>{{ t('Locator', '定位') }}</dt><dd data-field="source.locator"></dd></div>
      <div><dt>{{ t('Clocks', '时间戳') }}</dt>
        <dd data-field="clocks">
          <span data-field="source.published_at"></span> ·
          <span data-field="source.observed_at"></span> ·
          <span data-field="source.effective_at"></span>
        </dd>
      </div>
      <div><dt>{{ t('Business scope', '业务范围') }}</dt><dd data-field="business_scope"></dd></div>
      <div><dt>{{ t('Metric definition', '指标定义') }}</dt><dd data-field="metric"></dd></div>
      <div><dt>{{ t('Numerator / denominator', '分子 / 分母') }}</dt><dd data-field="numerator_denominator"></dd></div>
      <div><dt>{{ t('Unit / currency', '单位 / 货币') }}</dt><dd data-field="unit_currency"></dd></div>
      <div><dt>{{ t('Statement mode', '陈述方式') }}</dt><dd data-field="statement_mode"></dd></div>
      <div><dt>{{ t('Reported / derived / estimated', '原始 / 推算 / 估计') }}</dt><dd data-field="reported_derived"></dd></div>
      <div><dt>{{ t('Limitations', '局限') }}</dt><dd data-field="limitations"></dd></div>
      <div><dt>{{ t('Correction', '更正') }}</dt><dd data-field="correction"></dd></div>
      <div><dt>{{ t('Rights state', '权利状态') }}</dt><dd data-field="rights_state"></dd></div>
      <div><dt>{{ t('Identity state', '身份状态') }}</dt><dd data-field="identity_state"></dd></div>
    </dl>
  </div>
</aside>
<div class="fi-scrim" id="fi-scrim" hidden></div>
```

### B.9 Conflicts — first-class cards

The conflicts view is appended after the evidence drawer trigger row (still inside `company-exposure` is wrong; per R11 §5 conflicts belong near the rerating map). Render as a sub-section after the rerating map:

```html
<section class="fi-section fi-conflicts" aria-labelledby="fi-conflicts-title">
  <h2 id="fi-conflicts-title" class="fi-section-title">
    {{ t('Where the planes disagree', '各维度之间的分歧') }}
    <span class="fi-section-eyebrow">{{ t('Surfaced, never averaged', '显示差异，而非取均值') }}</span>
  </h2>
  <ul class="fi-conflict-list" role="list">
    {% for c in conflicts %}
    <li class="fi-conflict-card" data-conflict-id="{{ c.conflict_id }}">
      <span class="fi-conflict-label">{{ t(conflict_text[c.conflict_id].en, conflict_text[c.conflict_id].zh) }}</span>
      <div class="fi-conflict-pair">
        <div class="fi-conflict-side fi-conflict-left" data-plane="{{ c.left.plane.state }}">
          <span class="fi-conflict-statement">{{ c.left.statement }}</span>
        </div>
        <div class="fi-conflict-side fi-conflict-right" data-plane="{{ c.right.plane.state }}">
          <span class="fi-conflict-statement">{{ c.right.statement }}</span>
        </div>
      </div>
      <p class="fi-conflict-resolution">{{ t('Unresolved by design — both statements stand.', '设计上不予调和 — 两种陈述同时成立。') }}</p>
    </li>
    {% endfor %}
  </ul>
</section>
```


---

## C. Scoped CSS — two art directions (no token swap)

The CSS is scoped to `templates/finance_intelligence.css`. It declares a `:root` / `[data-theme=dark]` block and a `[data-theme=light]` block, each written as a complete material treatment — not a colour inversion. Tokens come ONLY from `templates/theme.css` (existing `--` set) plus `--fi-*` locals for dossier-specific surface/elevation. **No new token family is added to `theme.css`.**

### C.0 Material rationale — dark (command center)

The dark dossier sits on a graphite canvas at near-black depth; panels float above the canvas by ~3% luminance steps, never by glow. Hairlines are 1px solid `--line` at 100% opacity. State meaning rides on chip contrast (light-tinted fill + high-contrast ink) and on icon/text companions — colour is never the only channel. Restrained glow appears only on the focused stepper node (1px outer ring at `--link` 38% alpha). The rerating stepper is a thin horizontal spine at 2px with circular nodes, sized so the connecting line carries the visual rhythm, not the nodes themselves.

### C.1 Material rationale — light (research workspace)

The light dossier sits on a perceptibly deeper canvas (`--bg:#f7f8fa` per doctrine §5) so panels read as paper laid on a desk. White panels (`--panel:#ffffff`) carry 1px hairlines (`--line`); elevation comes from a single 4-stop hairline-tight shadow stack, never from saturation. Glow becomes shadow: the focused stepper node drops a 2px ring at `--ink-link` 26% alpha; the "what changed" freshness pip replaces glow with a 3px left rail. Chips use a quiet tint + darkened ink pair (e.g. observed → `color-mix(in srgb, var(--ok) 12%, transparent)` fill + `--ink-ok` ink); no chip saturates the surface.

### C.2 Common tokens (always inherited from `theme.css`)

```
/* font, spacing, radius, type ramp — all from theme.css :root */
font-family: var(--font-ui);
font-feature-settings: "tnum" 1, "cv11" 1;
```

### C.3 Dark block

```css
:root,
html[data-theme="dark"] {
  /* existing theme tokens: --bg, --panel, --panel2, --line, --text, --muted,
     --up/--down, --ok/--warn/--act, --link/--info, --ink-* already on theme.css.
     The dossier adds ONLY --fi-* locals below — never new theme-wide tokens. */
  --fi-canvas:        var(--bg);              /* #0f1115 */
  --fi-panel:         var(--panel);           /* #181b21 */
  --fi-panel-2:       var(--panel2);          /* #1e222a */
  --fi-line:          var(--line);            /* #3a4150 */
  --fi-text:          var(--text);
  --fi-muted:         var(--muted);
  --fi-spine:         color-mix(in srgb, var(--line) 90%, transparent);
  --fi-step-fill:     color-mix(in srgb, var(--link) 14%, var(--panel));
  --fi-step-ring:     color-mix(in srgb, var(--link) 38%, transparent);
  --fi-chip-observed: color-mix(in srgb, var(--ok)   18%, var(--panel));
  --fi-chip-watch:    color-mix(in srgb, var(--warn) 18%, var(--panel));
  --fi-chip-caution:  color-mix(in srgb, var(--info) 14%, var(--panel));
  --fi-chip-missing:  color-mix(in srgb, var(--muted) 18%, var(--panel));
  --fi-chip-stale:    color-mix(in srgb, var(--act)  16%, var(--panel));
  --fi-chip-regime:   color-mix(in srgb, var(--act)  22%, var(--panel));
  --fi-shadow-1:      0 1px 0 0 color-mix(in srgb, #000 50%, transparent) inset,
                      0 12px 30px -16px rgba(0,0,0,.45);
  --fi-drawer-shadow: 0 24px 60px -20px rgba(0,0,0,.6);
  --fi-card-shadow:   0 6px 18px -10px rgba(0,0,0,.45);
}
```

### C.4 Light block

```css
html[data-theme="light"] {
  /* canvas raised per doctrine §5 (f7f8fa) so panels sit visibly above it.
     Glow is REPLACED by shadow + hairline; saturation is REPLACED by tint
     + darkened ink. No chip fills saturate the surface. */
  --fi-canvas:        #f7f8fa;               /* doctrine §5 baseline */
  --fi-panel:         #ffffff;
  --fi-panel-2:       #f1f3f6;
  --fi-line:          #d8dde4;
  --fi-text:          #1c2026;
  --fi-muted:         #5c6473;
  --fi-spine:         #c7cdd6;
  --fi-step-fill:     #eef3fb;               /* quiet tint, never saturated */
  --fi-step-ring:     color-mix(in srgb, var(--ink-link) 26%, transparent);
  --fi-chip-observed: color-mix(in srgb, var(--ok)   10%, #ffffff);
  --fi-chip-watch:    color-mix(in srgb, var(--warn) 10%, #ffffff);
  --fi-chip-caution:  color-mix(in srgb, var(--info) 8%,  #ffffff);
  --fi-chip-missing:  color-mix(in srgb, var(--muted) 8%, #ffffff);
  --fi-chip-stale:    color-mix(in srgb, var(--act)  8%,  #ffffff);
  --fi-chip-regime:   color-mix(in srgb, var(--act)  12%, #ffffff);
  --fi-shadow-1:      0 1px 0 0 rgba(255,255,255,.7) inset,
                      0 1px 2px rgba(15,25,55,.06),
                      0 12px 30px -18px rgba(15,25,55,.10);
  --fi-drawer-shadow: 0 24px 60px -24px rgba(15,25,55,.18);
  --fi-card-shadow:   0 1px 2px rgba(15,25,55,.06),
                      0 6px 18px -10px rgba(15,25,55,.08);
}
```

### C.5 Shell + layout

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
.fi-toc { margin: 18px 0 8px; padding: 12px 14px; border: 1px solid var(--fi-line); border-radius: 12px; background: var(--fi-panel); }
.fi-toc ol { display: flex; flex-wrap: wrap; gap: 8px 14px; margin: 0; padding: 0; list-style: none; font-size: var(--fs-sm); }
.fi-toc a { color: var(--fi-text); text-decoration: none; padding: 4px 8px; border-radius: 7px; }
.fi-toc a:hover { background: var(--fi-panel-2); }
.fi-section { margin-top: 40px; }
.fi-section-title { font-size: var(--fs-h2); font-weight: 700; letter-spacing: -.01em; margin: 0 0 4px; }
.fi-section-eyebrow { display: block; font-size: var(--fs-sm); color: var(--fi-muted); font-weight: 400; margin-top: 2px; }
.fi-section-foot { font-size: var(--fs-sm); color: var(--fi-muted); margin: 12px 0 0; max-width: 75ch; }
```

### C.6 Rerating stepper — primary visual

```css
.fi-rerating-steps {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
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
  padding: 0 6px; gap: 6px; background: var(--fi-canvas); /* sit ON the spine */
}
.fi-step-dot {
  width: 14px; height: 14px; border-radius: 50%;
  background: var(--fi-step-fill); border: 2px solid var(--fi-line);
  margin-bottom: 4px;
}
.fi-step-label { font-size: var(--fs-sm); font-weight: 600; color: var(--fi-text); }
.fi-step-metric { font-size: var(--fs-sm); color: var(--fi-muted); font-variant-numeric: tabular-nums; min-height: 1.4em; }
.fi-step-chip {
  display: inline-block; font-size: 10.5px; font-weight: 600;
  padding: 2px 7px; border-radius: 999px; border: 1px solid var(--fi-line);
  background: var(--fi-panel); color: var(--fi-text); white-space: nowrap;
}
.fi-step-clock { font-size: 10px; color: var(--fi-muted); font-variant-numeric: tabular-nums; }
.fi-step-evidence {
  background: transparent; border: 1px solid var(--fi-line);
  width: 22px; height: 22px; border-radius: 6px; color: var(--fi-muted);
  cursor: pointer; font-size: 12px;
}
.fi-step-evidence:hover { color: var(--fi-text); border-color: var(--fi-muted); }
.fi-rerating-step:focus-within .fi-step-dot { box-shadow: 0 0 0 3px var(--fi-step-ring); }

/* chip state colours — each maps to one PLANE.state and includes an icon-or-text
   companion so colour is never the only channel (doctrine §5 + WCAG 1.4.1). */
.fi-step-chip[data-state="OBSERVED"]    { background: var(--fi-chip-observed); }
.fi-step-chip[data-state="INFERRED"]    { background: var(--fi-chip-watch); }
.fi-step-chip[data-state="MISSING"]     { background: var(--fi-chip-missing); }
.fi-step-chip[data-state="CONFLICTING"] { background: var(--fi-chip-caution); }
.fi-step-chip[data-state="STALE"]       { background: var(--fi-chip-stale); }
.fi-step-chip[data-state="REGIME_BREAK"],
.fi-step-chip[data-state="VALUATION_ANCHOR_UNAVAILABLE"],
.fi-step-chip[data-state="PRICE_BASIS_UNQUALIFIED"] { background: var(--fi-chip-regime); }
.fi-step-chip[data-state="NOT_APPLICABLE"] { background: var(--fi-panel-2); color: var(--fi-muted); }
```

### C.7 Atlas grid, exposure table, conflicts

```css
.fi-domain-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 14px; margin-top: 16px; }
.fi-domain { background: var(--fi-panel); border: 1px solid var(--fi-line); border-radius: 12px; padding: 14px 14px 10px; box-shadow: var(--fi-card-shadow); }
.fi-domain-title { font-size: var(--fs-h3); font-weight: 700; margin: 0 0 8px; }
.fi-slice-list { list-style: none; margin: 0; padding: 0; display: grid; gap: 6px; }
.fi-slice {
  display: grid; grid-template-columns: 1fr auto auto auto;
  gap: 6px 8px; align-items: center;
  padding: 6px 8px; border-radius: 8px; background: var(--fi-panel-2);
}
.fi-slice-name { font-size: var(--fs-sm); font-weight: 600; color: var(--fi-text); }
.fi-slice-chip {
  font-size: 10px; font-weight: 600; padding: 1px 6px; border-radius: 999px;
  border: 1px solid var(--fi-line); background: var(--fi-panel); color: var(--fi-text);
}
.fi-slice[data-state-slice="SEMANTIC_ONLY"] .fi-chip-slice { background: var(--fi-chip-missing); }
.fi-slice[data-state-slice="MEASURABLE"]   .fi-chip-slice { background: var(--fi-chip-observed); }
.fi-slice[data-state-slice="STALE"]        .fi-chip-slice { background: var(--fi-chip-stale); }
.fi-slice[data-state-slice="HELD_FOR_REVIEW"] .fi-chip-slice { background: var(--fi-chip-watch); }
.fi-slice[data-state-posture="SEMANTIC_ONLY"] .fi-chip-posture { background: var(--fi-chip-missing); }
.fi-slice[data-state-posture="RESEARCH_CANDIDATE"] .fi-chip-posture { background: var(--fi-chip-caution); }
.fi-slice[data-state-posture="CANDIDATE_READY_FOR_OWNER_REVIEW"] .fi-chip-posture { background: var(--fi-chip-watch); }
.fi-slice[data-state-posture="ADMITTED"] .fi-chip-posture { background: var(--fi-chip-observed); }
.fi-slice-no-basket { grid-column: 1 / -1; font-size: 11px; color: var(--fi-muted); }
.fi-slice-open { background: transparent; border: 1px solid var(--fi-line); border-radius: 6px; color: var(--fi-muted); cursor: pointer; font-size: 11px; }

.fi-exposure-table-wrap { overflow-x: auto; margin-top: 14px; }
.fi-exposure-table { border-collapse: separate; border-spacing: 0; font-size: var(--fs-sm); min-width: 760px; width: 100%; }
.fi-exposure-table th, .fi-exposure-table td {
  border-bottom: 1px solid var(--fi-line); padding: 8px 10px; text-align: left; vertical-align: top;
}
.fi-exposure-table thead th { position: sticky; top: 0; background: var(--fi-panel); z-index: 2; font-weight: 600; color: var(--fi-muted); font-size: 11px; text-transform: uppercase; letter-spacing: .04em; }
.fi-exposure-table .fi-col-company { position: sticky; left: 0; background: var(--fi-panel); z-index: 1; min-width: 180px; font-weight: 600; }
.fi-exposure-table thead th.fi-col-company { z-index: 3; }
.fi-cell { min-width: 200px; }
.fi-cell-role { display: block; font-weight: 600; }
.fi-cell-basis { display: block; font-size: 11px; color: var(--fi-muted); }
.fi-cell-materiality { display: block; font-size: 11px; }
.fi-cell[data-state-materiality="MATERIAL"]   .fi-cell-materiality { color: var(--ink-up); }
.fi-cell[data-state-materiality="IMMATERIAL"] .fi-cell-materiality { color: var(--fi-muted); }
.fi-cell[data-state-materiality="UNMEASURED"] .fi-cell-materiality { color: var(--ink-warn); }
.fi-cell-risk { display: block; font-size: 11px; color: var(--fi-muted); margin-top: 2px; }
.fi-cell-evidence-date { display: block; font-size: 10.5px; color: var(--fi-muted); margin-top: 2px; font-variant-numeric: tabular-nums; }
.fi-company-unresolved, .fi-company-hint { color: var(--fi-muted); font-style: italic; }
.fi-exposure-cards { display: none; list-style: none; margin: 14px 0 0; padding: 0; gap: 10px; }
.fi-exposure-card { background: var(--fi-panel); border: 1px solid var(--fi-line); border-radius: 12px; padding: 12px 14px; box-shadow: var(--fi-card-shadow); }

.fi-conflict-list { display: grid; gap: 10px; margin: 12px 0 0; padding: 0; list-style: none; }
.fi-conflict-card { background: var(--fi-panel); border: 1px solid var(--fi-line); border-radius: 12px; padding: 12px 14px; box-shadow: var(--fi-card-shadow); }
.fi-conflict-label { font-size: var(--fs-sm); font-weight: 700; display: block; margin-bottom: 6px; }
.fi-conflict-pair { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.fi-conflict-side { padding: 8px 10px; border-radius: 8px; border: 1px solid var(--fi-line); background: var(--fi-panel-2); font-size: var(--fs-sm); }
.fi-conflict-resolution { font-size: 11px; color: var(--fi-muted); margin: 8px 0 0; }
```

### C.8 Evidence drawer + scrim

```css
.fi-evidence-drawer {
  position: fixed; top: 0; right: 0; bottom: 0; width: min(440px, 92vw);
  background: var(--fi-panel); border-left: 1px solid var(--fi-line);
  box-shadow: var(--fi-drawer-shadow); transform: translateX(100%);
  transition: transform .22s cubic-bezier(.2,.7,.3,1);
  display: flex; flex-direction: column; z-index: 80;
}
.fi-evidence-drawer[aria-hidden="false"] { transform: translateX(0); }
.fi-evidence-head { padding: 14px 18px 10px; border-bottom: 1px solid var(--fi-line); display: flex; gap: 12px; align-items: flex-start; }
.fi-evidence-head .fi-kicker { margin: 0; }
.fi-evidence-head h2 { font-size: var(--fs-h2); margin: 4px 0 0; }
.fi-drawer-close { margin-left: auto; background: transparent; border: 1px solid var(--fi-line); border-radius: 6px; color: var(--fi-muted); width: 28px; height: 28px; cursor: pointer; }
.fi-evidence-body { padding: 12px 18px 24px; overflow-y: auto; font-size: var(--fs-sm); }
.fi-evidence-fields { display: grid; gap: 8px; margin: 0; }
.fi-evidence-fields > div { display: grid; grid-template-columns: 36% 64%; gap: 8px; padding-bottom: 6px; border-bottom: 1px dashed var(--fi-line); }
.fi-evidence-fields dt { color: var(--fi-muted); font-weight: 600; }
.fi-evidence-fields dd { margin: 0; color: var(--fi-text); }
.fi-scrim { position: fixed; inset: 0; background: rgba(0,0,0,.45); z-index: 70; }
html[data-theme="light"] .fi-scrim { background: rgba(15,25,55,.30); }
```

### C.9 Visible focus rings (always)

```css
.fi-shell *:focus-visible,
.fi-evidence-drawer *:focus-visible {
  outline: 2px solid var(--ink-link, var(--link));
  outline-offset: 2px;
  border-radius: 6px;
}
.fi-step-evidence:focus-visible,
.fi-evidence-trigger:focus-visible,
.fi-slice-open:focus-visible,
.fi-constraint-evidence:focus-visible,
.fi-drawer-close:focus-visible,
.fi-view-tab:focus-visible,
.fi-system-expand:focus-visible {
  outline: 2px solid var(--ink-link, var(--link));
  outline-offset: 2px;
}
```

### C.10 Responsive — 1440 and 390

```css
@media (min-width: 1280px) {
  .fi-shell { max-width: 1280px; padding-left: clamp(28px, 4vw, 56px); padding-right: clamp(28px, 4vw, 56px); }
  .fi-domain-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); }
}
@media (max-width: 1023px) {
  /* rerating stepper collapses to vertical timeline */
  .fi-rerating-steps { grid-template-columns: 1fr; gap: 4px; }
  .fi-rerating-steps::before { display: none; }
  .fi-rerating-step { flex-direction: row; align-items: center; text-align: left; gap: 10px; padding: 8px 10px; border-radius: 10px; background: var(--fi-panel); border: 1px solid var(--fi-line); }
  .fi-step-dot { margin: 0 6px 0 0; }
}
@media (max-width: 768px) {
  .fi-domain-grid { grid-template-columns: 1fr; }
  .fi-exposure-table-wrap { display: none; }
  .fi-exposure-cards { display: grid; }
  .fi-conflict-pair { grid-template-columns: 1fr; }
  .fi-toc ol { flex-direction: column; gap: 4px; }
}
@media (max-width: 390px) {
  /* honour the no-page-level-horizontal-scroll law — only inner table wraps
     scroll horizontally; the page itself never scrolls horizontally. */
  .fi-shell { padding-left: 14px; padding-right: 14px; }
  .fi-hero h1 { font-size: 22px; }
  .fi-exposure-cards { gap: 8px; }
}
```

### C.11 Reduced motion + long-word wrapping

```css
@media (prefers-reduced-motion: reduce) {
  .fi-evidence-drawer { transition: none; }
  .fi-rerating-steps::before { animation: none; }
}
.fi-section-title, .fi-step-label, .fi-cell-role {
  overflow-wrap: anywhere;
  word-break: break-word;
}
.fi-slice-name { /* long Finance terms wrap without clipping */ overflow-wrap: anywhere; }
```


---

## D. EN / ZH copy table (plain words; internal tokens only in `data-state`)

Every visible string the dossier renders, in plain words. Internal enum tokens appear in `data-state`/`data-*` attributes only — never in text nodes. Banned vocabulary per doctrine §2 (internal state names, untranslated stats, raw slugs) is absent from this table.

### D.1 PLANE.state chips (rerating nodes + system edges)

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

### D.2 Slice state chips (atlas grid)

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

### D.3 Basket posture chips (atlas grid)

| enum | EN | ZH |
|---|---|---|
| SEMANTIC_ONLY | `No price basket yet` | `暂无价格组合` |
| BROAD_CONTEXT_AVAILABLE | `Broad existing context` | `已有广义背景` |
| RESEARCH_CANDIDATE | `Research candidate` | `研究候选` |
| CANDIDATE_READY_FOR_OWNER_REVIEW | `Ready for owner review` | `待负责人复核` |
| ADMITTED | `Admitted price basket` | `已收录价格组合` |

### D.4 Materiality chips (company exposure)

| enum | EN | ZH |
|---|---|---|
| MATERIAL | `Material exposure` | `重要敞口` |
| PARTIAL | `Partial exposure` | `部分敞口` |
| IMMATERIAL | `Immaterial` | `不重大` |
| UNMEASURED | `Not yet measured` | `尚未量化` |

### D.5 Role vocabulary (company exposure cells)

| enum | EN | ZH |
|---|---|---|
| DIRECT_PURE_OR_HIGH_EXPOSURE | `Direct, high exposure` | `直接且高敞口` |
| DIRECT_DIVERSIFIED | `Direct, diversified` | `直接，多元化` |
| ENABLER_OR_TOLL_COLLECTOR | `Enabler or toll collector` | `基础设施或收费方` |
| SECOND_ORDER_BENEFICIARY | `Second-order beneficiary` | `间接受益方` |
| PROXY_OR_ADJACENCY | `Proxy or adjacency` | `代理或邻近` |
| AT_RISK_OR_DISRUPTED | `At risk or disrupted` | `承压或被颠覆` |
| HEDGE_OR_OFFSET | `Hedge or offset` | `对冲或抵消` |

### D.6 Exposure basis (company exposure cells)

| enum | EN | ZH |
|---|---|---|
| SEGMENT_REVENUE | `Segment revenue` | `分部收入` |
| TRANSACTION_VOLUME | `Transaction volume` | `交易笔数` |
| AUC_A | `Assets under custody` | `在管资产规模` |
| AUM | `Assets under management` | `在管资产` |
| NOTIONAL | `Notional value` | `名义金额` |
| QUALITATIVE | `Qualitative read` | `定性读数` |
| NOT_SEPARATELY_DISCLOSED | `Not separately disclosed` | `未单独披露` |

### D.7 Constraint names

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

### D.8 Macro drivers (matrix columns)

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

### D.9 Lag (macro matrix cells)

| enum | EN | ZH |
|---|---|---|
| IMMEDIATE | `Immediate` | `即时` |
| ONE_QUARTER | `About a quarter` | `约一个季度` |
| TWO_TO_FOUR_QUARTERS | `Two to four quarters` | `两到四个季度` |
| MULTI_YEAR | `Multi-year` | `多年` |
| UNKNOWN | `Lag not measured` | `尚未测算时滞` |

### D.10 Freshness chips

| enum | EN | ZH |
|---|---|---|
| FRESH | `Fresh` | `新鲜` |
| AGING | `Aging` | `趋于陈旧` |
| SOURCE_STALE | `Source stale` | `来源已陈旧` |
| NO_EVIDENCE | `No evidence on file` | `暂无证据` |

### D.11 The eleven mandatory missing states (visible chips, semantic categories)

Each row maps the schema enum to a visible chip + a hover tooltip. Colour comes from one of the six semantic categories (observed/complete, watch/partial, caution/conflict, missing, stale, non-comparable); every chip carries an icon-or-text companion so colour is never the only channel.

| enum | Semantic category | EN chip | ZH chip |
|---|---|---|---|
| NO_HISTORICAL_CONSENSUS | missing | `No dated consensus on file` | `暂无可追溯的市场预期` |
| EXPOSURE_NOT_SEPARATELY_DISCLOSED | missing | `Exposure not separately disclosed` | `敞口未单独披露` |
| CURRENT_MEMBERSHIP_ONLY | non-comparable | `Current membership only — not a history` | `仅为当前成员 — 非历史口径` |
| PIT_MEMBERSHIP_INCOMPLETE | non-comparable | `Point-in-time membership incomplete` | `时点成员数据不完整` |
| IDENTITY_UNRESOLVED | missing | `Identity unresolved` | `身份尚未确认` |
| PRICE_BASIS_UNQUALIFIED | non-comparable | `Price basis not qualified` | `价格口径未达合格` |
| SOURCE_STALE | stale | `Source is stale` | `来源已陈旧` |
| SOURCE_RIGHTS_HELD | watch | `Source rights restrict display` | `来源权利限制展示` |
| REGIME_BREAK_NOT_COMPARABLE | non-comparable | `Regime break — not comparable` | `制度断裂 — 不可比` |
| VALUATION_ANCHOR_UNAVAILABLE | missing | `No valuation anchor available` | `暂无估值锚点` |
| CAUSAL_EFFECT_UNMEASURED | caution | `Causal effect not measured` | `因果效应尚未测算` |

### D.12 The ten conflict labels (first-class cards)

Each card shows the LEFT and RIGHT statement as written by the schema (`conflicts[].left.statement` / `conflicts[].right.statement`). The label below uses plain words.

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

### D.13 Action labels and footer copy

| Surface | EN | ZH |
|---|---|---|
| Theme Tracker card action | `Open Finance Intelligence` | `打开金融情报` |
| Financials launch action | `Open Finance Intelligence` | `打开金融情报` |
| Slice "open" button (Tier 1) | `Open this slice` | `打开该切片` |
| Evidence button (per node / per row) | `Open evidence` | `打开证据` |
| Drawer close | `Close evidence drawer` | `关闭证据抽屉` |
| System view: expand | `Expand` | `展开` |
| System view: collapse | `Collapse` | `收起` |
| Empty state — outer dossier not accepted | `Outer dossier not accepted — research context only` | `外部报告尚未接入 — 仅作研究背景` |
| Empty state — no generation yet | `No generation yet — refresh in a moment` | `本次尚无产物 — 请稍候刷新` |
| Empty state — generation torn | `Generation interrupted — partial context only` | `生成中断 — 仅展示部分背景` |
| Empty state — contract invalid | `Contract mismatch — showing public shell only` | `契约不一致 — 仅展示公开外壳` |
| Auth — unauthenticated | `Sign in to read current research` | `请登录以查阅当前研究` |
| Auth — non-entitled | `This dossier is part of the research tier` | `此报告为研究层内容` |
| Section foot (generic) | `Read the underlying receipts before acting on any line.` | `请先查阅原始凭据再行判断。` |


---

## E. JS behaviour contract (behaviour only — no implementation)

| Element | Event | State class change | ARIA change | Focus rule |
|---|---|---|---|---|
| `.fi-view-tab` | `click` | `aria-selected=true` on clicked tab; `aria-selected=false` on siblings | `tabindex` flipped (selected=0, others=-1) | Focus moves to clicked tab; show the matching `role=tabpanel`, hide others |
| `.fi-system-expand` | `click` | `aria-expanded` flips | `aria-controls` panel toggles `hidden` | Focus stays on the expand button; the now-revealed list is announced via `aria-live=polite` |
| `.fi-evidence-trigger`, `.fi-step-evidence`, `.fi-constraint-evidence`, `.fi-slice-open` | `click` | `.fi-evidence-drawer[aria-hidden]` flips to `false`; `body` gets `data-drawer-open` | Drawer `inert` and `hidden` removed; `aria-hidden=false`; scrim shown | Focus moves to the drawer's first focusable element; previous-active element saved for restore |
| `.fi-drawer-close`, `.fi-scrim`, `Escape` keydown | `click` / `keydown` | Drawer `aria-hidden=true`; `body` loses `data-drawer-open` | Drawer `hidden inert` reapplied | Focus restored to the element that opened it (saved in step 3) |
| Drawer focus trap | `keydown Tab` / `Shift+Tab` at edges | none | none | Cycle within drawer's focusable elements; do not escape to inert background |
| Resize observer on viewport | `resize` past 1023 → 767 breakpoint | `.fi-rerating-steps` switches from 7-col grid to vertical timeline | none | none |
| `prefers-reduced-motion: reduce` | media-query change | drawer's CSS transition collapses to `none` | none | none |
| Theme toggle (`.theme-toggle` global) | `click` | `html[data-theme]` flips between `dark` and `light` | none | Persist via existing `theme.js` |
| Language toggle (`.lang-toggle` global) | `click` | `html[data-lang]` flips between `en` and `zh`; `.l-en` / `.l-zh` visibility swaps; `data-en`/`data-zh` swap | none | Persist via existing `theme.js` |
| `IntersectionObserver` on each rerating step | viewport entry | none | none | none (visual lazy paint only) |
| Hash routing for drawer | `popstate` or `hashchange` | drawer opens to `record_id` decoded from `#evidence=<id>` | drawer `aria-hidden=false`, scrim shown | Focus moves to drawer's first focusable |
| Conflict card hover/focus | `mouseenter` / `focus` | none | `data-tip-*` tooltip (Tier 2) appears with conflict_id + source publisher | none |
| Table cell `.fi-cell` with `data-state-exposure="EXPOSURE_NOT_SEPARATELY_DISCLOSED"` | `focus` | none | screen-reader-only label: "Exposure not separately disclosed" appended to cell | none |

No keyboard shortcut invents new gestures; Tab order follows DOM order; the drawer is the only modal surface; the entire dossier is keyboard-operable end-to-end.

---

## F. Two entry modules

### F.1 `_finance_sector_deep_dive.html.j2` — Theme Tracker card

A **navigation-only** card placed AFTER the existing `rp` "What to look at first" module and OUTSIDE the canonical theme lanes (per packet §F + R11 §3). The card must NEVER claim a canonical theme stage or compute the seven Theme Tracker asymmetry legs for Finance.

```jinja
{% macro t(en, zh='') -%}<span class="l-en">{{ en }}</span><span class="l-zh">{{ zh if zh else en }}</span>{%- endmacro %}
{# Sector deep dives — Financials / Finance Intelligence. #}
{# Stays outside the canonical theme lanes; non-canonical context card. #}
{% set fin = finance_dossier if finance_dossier is defined else none %}
<section class="sot-sector-deep-dive" aria-labelledby="sot-finance-deep-dive-title"
         data-state-coverage="{{ fin.coverage_state if fin else 'UNAVAILABLE' }}"
         data-state-outer-dossier="{{ fin.outer_dossier_ref.state if fin else 'OUTER_CONTRACT_NOT_ACCEPTED' }}">
  <p class="sot-kicker">{{ t('Sector deep dive', '子行业深读') }}</p>
  <h3 id="sot-finance-deep-dive-title">
    {{ t('Financials · Finance Intelligence', '金融 · 金融情报') }}
  </h3>
  <p class="sot-deep-dive-deck">
    {{ t('Research context across the financial system — not a canonical theme stage or trade call.', '对金融体系的研究背景 — 非主题生命周期阶段或交易指令。') }}
  </p>
  <dl class="sot-deep-dive-meta">
    <div>
      <dt>{{ t('Coverage', '覆盖') }}</dt>
      <dd>{{ fin.coverage_label if fin else t('Not yet populated', '暂无数据') }}</dd>
    </div>
    <div>
      <dt>{{ t('Evidence freshness', '证据新鲜度') }}</dt>
      <dd>{{ fin.freshness_label if fin else t('No generation yet', '本次尚无产物') }}</dd>
    </div>
    <div>
      <dt>{{ t('Mapped slices', '已映射切片') }}</dt>
      <dd>{{ fin.slices_populated }} / {{ fin.slices_total if fin else 52 }}</dd>
    </div>
  </dl>
  {% if fin and fin.material_changes %}
  <ul class="sot-deep-dive-changes" role="list">
    {% for ch in fin.material_changes[:3] %}
    <li>{{ ch.operating_implication }}</li>
    {% endfor %}
  </ul>
  {% endif %}
  <a class="sot-deep-dive-action"
     href="{{ fin.entry_href if fin else '/sectors/XLF.html#finance-intelligence' }}"
     data-state-cta="navigation">
    {{ t('Open Finance Intelligence', '打开金融情报') }} ↗
  </a>
</section>
```

Field bindings: `coverage_state` and `freshness_label` come from the read-model composer; `slices_populated`/`slices_total` come from `coverage.{slices_populated, slices_total}`; `material_changes[]` is the first three entries from the dossier; `entry_href` is the canonical Financials sector route anchor.

### F.2 `_finance_intelligence_launch.html.j2` — Financials page module

A **compact launch module** placed near the existing back-link on `basket/us_sector_financials.html` (and the analogous Sector Intelligence route). It retains the existing broad Financials price context (equal-weight S&P 500 Financials participation, NOT a buy list, NOT an exposure-pure Finance basket).

```jinja
{% macro t(en, zh='') -%}<span class="l-en">{{ en }}</span><span class="l-zh">{{ zh if zh else en }}</span>{%- endmacro %}
{# Finance Intelligence launch — placed near back-link on basket/us_sector_financials.html.
   Reads as: broad Financials price context stays, plus top research domains + the link. #}
{% set fin = finance_dossier if finance_dossier is defined else none %}
<section class="fi-launch" aria-labelledby="fi-launch-title"
         data-state-coverage="{{ fin.coverage_state if fin else 'UNAVAILABLE' }}">
  <p class="fi-kicker">{{ t('Finance Intelligence', '金融情报') }}</p>
  <h3 id="fi-launch-title">
    {{ t('Research context for the financial system', '金融体系的研究背景') }}
  </h3>
  <p class="fi-launch-deck">
    {{ t('Broad Financials price context stays below — equal-weight, not a buy list. The dossier below is research context only.', '下方仍保留广义金融价格背景 — 等权重，非买入清单。下方的报告仅作研究背景。') }}
  </p>
  <dl class="fi-launch-meta">
    <div>
      <dt>{{ t('Top research domains', '重点研究子域') }}</dt>
      <dd>
        {% if fin and fin.top_domains %}
          {% for d in fin.top_domains[:3] %}<span class="fi-launch-domain">{{ t(d.name_en, d.name_zh) }}</span>{% endfor %}
        {% else %}
          <span class="fi-launch-domain">{{ t('Money Movement', '资金流动') }}</span>
          <span class="fi-launch-domain">{{ t('Securities Infrastructure', '证券基础设施') }}</span>
        {% endif %}
      </dd>
    </div>
    <div>
      <dt>{{ t('Evidence horizon', '证据时窗') }}</dt>
      <dd>{{ fin.evidence_horizon_label if fin else t('Not yet populated', '暂无数据') }}</dd>
    </div>
    <div>
      <dt>{{ t('First vertical', '首个研究垂直') }}</dt>
      <dd>{{ t('Financial Rails & Market Infrastructure', '金融基础设施与市场运作') }}</dd>
    </div>
  </dl>
  <a class="fi-launch-action"
     href="{{ fin.entry_href if fin else '/finance/intelligence.html' }}">
    {{ t('Open Finance Intelligence', '打开金融情报') }} ↗
  </a>
</section>
```

`basket/us_sector_financials.html` is NOT modified by this packet (the existing back-link pattern is read-only context for the launch placement); the launch module renders alongside it.

---

## G. Degraded states — public shell behaviour

The dossier must never expose a private payload. Every degraded state shows a typed refusal on the public shell and disables evidence triggers.

| Condition | Trigger source | What the public shell shows | What is hidden | What still renders |
|---|---|---|---|---|
| `API 503 PRIVATE_STORE_UNAVAILABLE` | dossier composer fetch fails with 503 | Title + deck; section foot reads: `Outer dossier not accepted — research context only` / `外部报告尚未接入 — 仅作研究背景`. A single banner across the shell with `data-state-coverage="UNAVAILABLE"` | All eight sections render as shells with empty-state copy; no evidence refs resolve; no company rows | Theme is honoured; TOC renders; chips show N/A |
| `NO_GENERATION` | composer has no committed generation this cycle | Same banner; foot reads: `No generation yet — refresh in a moment` / `本次尚无产物 — 请稍候刷新` | All quantitative fields; rerating nodes show "Not applicable here" chips | Slice grid renders with `slice_state` chips |
| `GENERATION_TORN` | composer aborted mid-write; partial cache | Foot reads: `Generation interrupted — partial context only` / `生成中断 — 仅展示部分背景`. Affected sections carry `data-state-partial="true"` | Partial numeric data within torn sections | Header + TOC + per-section availability indicator |
| `CONTRACT_INVALID` | response fails `finance_intelligence_read_model.v1.schema.json` validation | Foot reads: `Contract mismatch — showing public shell only` / `契约不一致 — 仅展示公开外壳`. No sections render | All eight sections | Title + deck + TOC only |
| Unauthenticated 401 | signed-out request to the authenticated route | Full header + TOC; **no sections render**. Foot: `Sign in to read current research` / `请登录以查阅当前研究`. Sign-in CTA links to the existing `?return=<path>` pattern | All sections | Theme toggle, language toggle |
| Non-entitled 402 | authenticated but tier does not include Finance Intelligence | Full header + TOC; first section "What changed" renders with `slice_state` chips only. Foot: `This dossier is part of the research tier` / `此报告为研究层内容`. Upgrade CTA | Sections A.2–A.8 evidence refs | Slice grid chips + cohort posture chips (they carry no private payload) |

The evidence drawer never opens in any degraded state — the trigger buttons get `aria-disabled="true"` and a visible chip `Evidence unavailable` / `证据暂不可用`. No private payload leaks via static, localStorage, IndexedDB, source maps, service workers, or alternate routes (per the carrier packet §15.1 / §15.4).

---

## H. Acceptance checklist — mirrors R11 §12 (14 cells)

Each row lists one of the 14 R11 §12 proof cells, the design obligation this spec binds to that cell, and the PNG path the seat's browser-evidence lane will capture against the implementation (NOT against this static spec). All 14 cells are required for sign-off.

| # | R11 §12 cell | Design obligation in this spec | Browser-evidence PNG |
|---|---|---|---|
| 1 | Theme Tracker with Finance sector-deep-dive entry | §F.1 navigation-only card, `data-state-coverage` honoured, no canonical lane contamination | `verify_shots/finance/c01_theme_tracker_deep_dive_<theme>.png` |
| 2 | Financials sector page with Finance Intelligence launch | §F.2 launch module, broad price context preserved, non-buy-list wording | `verify_shots/finance/c02_financials_launch_<theme>.png` |
| 3 | Finance dossier populated | §A.1–§A.8 all eight sections render with field bindings | `verify_shots/finance/c03_dossier_populated_1440_<theme>.png` |
| 4 | Semantic-only slice with honest no-basket state | §B.4 `.fi-slice-no-basket` element + §D.3 `SEMANTIC_ONLY` chip + §D.13 footer | `verify_shots/finance/c04_semantic_only_slice_<theme>.png` |
| 5 | Candidate-basket slice | §B.4 posture chip `CANDIDATE_READY_FOR_OWNER_REVIEW` with §D.3 copy | `verify_shots/finance/c05_candidate_basket_<theme>.png` |
| 6 | Missing-consensus state | §D.11 `NO_HISTORICAL_CONSENSUS` chip with text companion | `verify_shots/finance/c06_missing_consensus_<theme>.png` |
| 7 | Regime-break state | §D.11 `REGIME_BREAK_NOT_COMPARABLE` chip on a rerating node | `verify_shots/finance/c07_regime_break_<theme>.png` |
| 8 | Stale-source state | §D.11 `SOURCE_STALE` chip + §D.10 freshness chip | `verify_shots/finance/c08_stale_source_<theme>.png` |
| 9 | Company exposure drill | §B.5 sticky table at 1440 + card stack at ≤768; IDENTITY_UNRESOLVED row carries no link | `verify_shots/finance/c09_company_exposure_<viewport>_<theme>.png` |
| 10 | Evidence drawer | §B.8 14-field drawer; focus trap + Escape + deep-link via `#evidence=<id>` | `verify_shots/finance/c10_evidence_drawer_<theme>.png` |
| 11 | Mobile flow map | §C.10 vertical rerating stepper at ≤1023; no page-level horizontal scroll at 390 | `verify_shots/finance/c11_mobile_flow_map_390.png` |
| 12 | EN/ZH parity | §D copy table covers every visible string; `.l-en` / `.l-zh` swap on `data-lang` flip | `verify_shots/finance/c12_en_zh_parity_<theme>.png` |
| 13 | Light/dark parity | §C.3 dark block + §C.4 light block written as two art directions, both rendered + screenshotted | `verify_shots/finance/c13_light_dark_parity.png` |
| 14 | Keyboard-only journey | §E focus rings always visible; Tab order matches DOM; drawer trap works; no hover-only meaning | `verify_shots/finance/c14_keyboard_journey_<theme>.png` |

The seat's implementation lane runs the browser-evidence harness AFTER the implementation lands; this spec's obligation is only to make all 14 cells achievable without further design intervention.

---

## RETURN

**STATUS:** COMPLETE — the spec is the full lane deliverable. Static mockup delivery is recorded under DEVIATIONS and routed to `fin_d1b_mockup`.

**RESULT:**
- File: `research/finance/implementation/FINANCE_DOSSIER_DESIGN_SPEC_2026-09-24.md`
- Sections A–H all populated; every visible state binds to a schema field/enum; both art directions specified separately with rationale; EN/ZH copy table covers all eleven missing states and all ten conflict labels; two entry modules specified; degraded-state table covers 6 conditions; acceptance checklist covers all 14 R11 §12 cells.

**GAPS:**
- The Finance T1 read-model schema is not yet on `origin/main` (verified `git show origin/main:contracts/sector_intelligence/finance_intelligence_read_model.v1.schema.json` → does not exist). The spec binds to the lane-packet's **FROZEN SCHEMA FIELD LIST** verbatim; if the merged schema renames any field/enum, the build lane must reconcile under §A's field bindings.
- No field named `slice.display_headline`, `slice.guardrail`, `slice.user_action` exists in the schema. The dossier's Tier 1 "what to look at" copy is composed at render time from `operating_implication` + state chips; this is a render-time projection, not a stored field, and is consistent with §13.5's "no owner recalculation in browser" law only because the composer pre-composes the headline before shipping.
- `coverage.first_vertical.slice_ids` is consumed in §A but the exact slice-id order is implementation-defined; the atlas grid (§B.4) iterates `domains[].slice_ids` so any reordering is absorbed.
- `conflicts[].resolution` is the schema's literal `"UNRESOLVED_BY_DESIGN"`; the spec surfaces this as the plain-word footer (§B.9, §D.13) so the field name does not appear in user-facing copy.
- No live-test environment was available — no screenshots produced; the PNG paths in §H are the seat's responsibility against the build lane's output.

**DEVIATIONS:**
- **Mockup deferred to `fin_d1b_mockup` by seat instruction.** This run ships the spec only. The static mockup `mockups/refs/finance_intelligence/finance_intelligence_mockup.html` is delivered by a second lane onto the same PR after this head lands. The spec still binds every mockup obligation (four toggles, all eight sections, eight-from-eight theme/parity, eleven missing states, ten conflicts, SEMANTIC_ONLY slice, witness rows) — the build lane for `fin_d1b_mockup` reads §A–§H of THIS spec as the binding contract.
- No other deviations.

