# Mining M1 closed domain definitions

This file defines the two closed M1 economic questions. The YAML blocks are the later code task's complete content contract: they may be copied verbatim, but their claims must still be bound to permitted native source bytes and replayable receipts by the incumbent owners. These definitions do not create Mining identity, evidence, rights, route, mount, ranking, sizing, trading, or entry vocabulary.

## A. W-C — copper economics

The copper question is whether Freeport-McMoRan's reported operating and cost outcomes, viewed beside management's earlier point estimate, change the investor's understanding of attributable copper economics. The dossier must retain the selected measure's reporting basis, exclusions, by-product assumptions, ownership basis, and source timestamp. A favorable comparison is an economic observation, not a consensus surprise, a productivity verdict, or a shareholder cash result.

The contract must especially protect attribution. An already proportionately consolidated Morenci figure has already had the stated ownership basis applied. A later ownership observation cannot be imposed on an earlier operating period, and a company-level reconciliation cannot be replaced with an invented temporal allocation. Production, sales, and cash receipts are different economic events.

```yaml
slice_key: mining_copper_economics
anchor_theme_id: theme:copper_steel_electrify
issuer:
  name: Freeport-McMoRan
  cik: '0000831259'
investor_question: Did Freeport-McMoRan's reported quarter deliver copper sales and unit cost outcomes different from management's earlier estimate?
affected_asset_or_process:
  - Consolidated copper sales
  - Consolidated copper unit net cash cost
  - Morenci proportionately consolidated copper reporting
economics_chain:
  - Mined and recovered copper
  - Consolidated sales and attributable economic interests
  - Operating costs, by-product credits, and excluded idle and restoration charges
  - Shareholder capture after ownership and cost definitions
  - Management expectations, later observations, and attribution counter-evidence
required_metrics:
  - key: consolidated_copper_sales
    label: Consolidated copper sales
    basis: reported
    period_kind: quarter
    sign_convention: Positive production and sales quantities; sales exclude purchases.
    exclusions_or_definition_notes: Million recoverable pounds on a consolidated reporting basis; this is not production or cash receipts.
    source_family: sec_edgar_8k_exhibit
    selection_label: Consolidated copper sales row
    research_locator: MINING_WITNESS_INPUT_QUALIFICATION_2026-09-24.md § W-C selected test inputs
  - key: copper_unit_net_cash_cost
    label: Copper unit net cash cost
    basis: company_adjusted
    period_kind: quarter
    sign_convention: Lower cost is shown as the reported cost per pound without changing the sign.
    exclusions_or_definition_notes: Includes by-product credits and excludes specified idle and restoration costs; changed by-product assumptions prevent an isolated productivity interpretation.
    source_family: sec_edgar_8k_exhibit
    selection_label: Copper consolidated unit net cash cost row
    research_locator: MINING_WITNESS_INPUT_QUALIFICATION_2026-09-24.md § W-C selected test inputs
  - key: idle_and_restoration_costs_excluded_from_unit_cost
    label: Excluded idle and restoration costs
    basis: reported
    period_kind: quarter
    sign_convention: Charges retain their reported charge direction.
    exclusions_or_definition_notes: Quarterly and half-year scopes are distinct and must not be added as though they reconcile.
    source_family: sec_edgar_8k_exhibit
    selection_label: Idle and restoration costs excluded from unit cost note
    research_locator: MINING_WITNESS_INPUT_QUALIFICATION_2026-09-24.md § W-C selected test inputs
  - key: copper_production_consolidated
    label: Consolidated copper production
    basis: reported
    period_kind: quarter
    sign_convention: Positive physical quantity.
    exclusions_or_definition_notes: Production is not sales, attributable cash receipts, or a Morenci-specific measure unless its row and basis are separately selected.
    source_family: sec_edgar_8k_exhibit
    selection_label: Consolidated copper production row
    research_locator: MINING_WITNESS_INPUT_QUALIFICATION_2026-09-24.md § W-C selected test inputs
  - key: morenci_copper_production
    label: Morenci copper production
    basis: reported
    period_kind: quarter
    sign_convention: Positive physical quantity already presented on the stated ownership basis.
    exclusions_or_definition_notes: The selected Morenci row is proportionately consolidated; ownership must not be applied again.
    source_family: sec_edgar_8k_exhibit
    selection_label: Morenci copper production row
    research_locator: MINING_WITNESS_INPUT_QUALIFICATION_2026-09-24.md § W-C selected test inputs
management_estimate_vs_actual:
  earlier_point_estimate:
    metric: management_issued_copper_sales_estimate
    source_family: sec_edgar_8k_exhibit
    selection_label: Second-quarter consolidated copper sales outlook
    research_locator: MINING_WITNESS_INPUT_QUALIFICATION_2026-09-24.md § W-C selected test inputs
    definition_fields_required: [unit, perimeter, basis]
    definition_notes: Million recoverable pounds; consolidated reporting; sales exclude purchases.
    period_kind: quarter
  later_actual:
    metric: consolidated_copper_sales
    source_family: sec_edgar_8k_exhibit
    selection_label: Second-quarter operating summary copper sales
    research_locator: MINING_WITNESS_INPUT_QUALIFICATION_2026-09-24.md § W-C selected test inputs
    definition_fields_required: [unit, perimeter, basis]
    definition_notes: Million recoverable pounds; consolidated reporting; sales exclude purchases.
    period_kind: quarter
  comparison: Comparison classification and any `definition_unqualified:<field>` warning are emitted by the shared helper at runtime from the qualified fields; when that warning is present both values stay inspectable and no beat/miss/badge or confirmed-surprise wording is produced; fully qualified compatible inputs are compared normally and never suppressed.
  pairs:
  - earlier_point_estimate:
      metric: management_issued_copper_unit_net_cash_cost_estimate
      source_family: sec_edgar_8k_exhibit
      selection_label: Second-quarter consolidated copper unit net cash cost outlook
      research_locator: MINING_WITNESS_INPUT_QUALIFICATION_2026-09-24.md § W-C selected test inputs
      definition_fields_required: [unit, perimeter, basis]
      definition_notes: USD per pound; consolidated reporting; includes by-product credits and excludes specified idle and restoration costs.
      period_kind: quarter
    later_actual:
      metric: copper_unit_net_cash_cost
      source_family: sec_edgar_8k_exhibit
      selection_label: Second-quarter operating summary copper unit net cash cost
      research_locator: MINING_WITNESS_INPUT_QUALIFICATION_2026-09-24.md § W-C selected test inputs
      definition_fields_required: [unit, perimeter, basis]
      definition_notes: USD per pound; consolidated reporting; includes by-product credits and excludes specified idle and restoration costs.
      period_kind: quarter
      comparison: Comparison classification and any `definition_unqualified:<field>` warning are emitted by the shared helper at runtime from the qualified fields; when that warning is present both values stay inspectable and no beat/miss/badge or confirmed-surprise wording is produced; fully qualified compatible inputs are compared normally and never suppressed.
      is_range: false
      is_consensus: false
    comparison: Same rule as the sales pair — classification and any `definition_unqualified:<field>` warning are emitted by the shared helper at runtime; both values stay inspectable; no beat/miss badge from an unqualified comparison; a cost measure whose by-product assumptions changed yields no isolated-productivity conclusion.
    is_range: false
    is_consensus: false

mechanism: Copper rock must become recoverable production before it can be sold under a stated reporting basis. Costs then reflect mine operations, by-product credits, and the exclusions the issuer defines. Ownership and accounting treatment determine which economic share reaches the listed company. Shareholder value depends on the durability of that capture after investment and other claims. A later reported result can test an earlier management expectation, but only when definitions and periods remain comparable.
counter_thesis:
  - A later consolidated sales observation at a different definition than the estimate, or evidence that shipment timing moved between periods, contradicts an inferred demand or productivity improvement.
  - A changed by-product assumption or excluded idle and restoration charge contradicts attributing the unit-cost difference to mine productivity alone.
  - Evidence that ownership or accounting treatment differs from the selected row's basis contradicts the claimed attributable economics.
  - A later consolidated_copper_sales or copper_unit_net_cash_cost observation on a matching definition and forecast vintage that reverses the direction contradicts an assertion of durable improvement.
limitations_vocabulary:
  - missing_derivation
  - definition_unqualified
  - missing_basis
  - source_only
  - changed_source
  - denied_source
  - page_generation_change
forbidden_derivations:
  - do not multiply a proportionately consolidated Morenci figure by ownership again
  - do not replace sales with production
  - do not add quarterly and half-year idle and restoration scopes
  - do not invent a period ownership split from a later ownership observation
  - no midpoint, percentage, metal-equivalent, or valuation from display strings
honest_degradation: Show both separately sourced literals, their source labels, definitions, periods, exclusions, and the definition-unqualified warning. Omit unsupported beat or miss language and derived percentage or difference panels while retaining the issuer's attributed operating explanation and cost scope.
authority:
  can_rank: false
  can_gate: false
  can_size: false
  can_originate: false
  can_open_entry: false
```

## B. W-R — rare-earth economics

The rare-earth question is whether MP Materials' physical processing and commercial progress convert into retained external economics. The dossier must keep material form, segment, period, elimination sign, accounting basis, and contractual income separate. Finished magnets, precursors, stockpiles, affiliate transfers, and external sales are not interchangeable merely because they share a label.

Processing progress and retained economics are different conclusions. Positive adjusted EBITDA can coexist with a GAAP loss; contractual price-protection income is not revenue; and the difference between production and sales does not by itself prove inventory depletion. The absence of a verified stream threshold leaves a contract explanation useful but its entitlement uncomputed.

The `stream_threshold_unknown` limitation is used here for any unverified contractual threshold balance, including a price-protection benchmark or capacity condition; it does not assert a metal-stream instrument.

```yaml
slice_key: mining_rare_earth_economics
anchor_theme_id: theme:rare_earth_critical_min
issuer:
  name: MP Materials
  cik: '0001801368'
investor_question: Does MP Materials' rare-earth processing and commercial progress translate into external revenue and adequately retained economics?
affected_asset_or_process:
  - NdPr production and sales definitions
  - Materials segment revenue including intersegment sales
  - Magnetics precursor product revenue
  - Intersegment revenue elimination
  - Price-protection income
  - GAAP net loss and adjusted EBITDA
  - Independence qualification and regulatory testing
economics_chain:
  - Mined and processed rare-earth material
  - External sales, affiliate transfers, and contractual rights
  - Operating costs, qualification investment, and price-protection income
  - Shareholder capture after losses, adjustments, and invested-capital claims
  - Processing expectations versus commercial and financial counter-evidence
required_metrics:
  - key: materials_revenue_including_intersegment_sales
    label: Materials revenue including intersegment sales
    basis: reported
    period_kind: quarter
    sign_convention: Revenue is positive; an elimination row retains its reported negative sign.
    exclusions_or_definition_notes: Segment revenue is not consolidated revenue until the issuer's stated elimination is applied; do not replace a quarter with a half-year column.
    source_family: sec_edgar_8k_exhibit
    selection_label: Materials segment revenue including intersegment sales
    research_locator: MINING_WITNESS_INPUT_QUALIFICATION_2026-09-24.md § W-R Selected Q2 measurements, USD thousands unless stated
  - key: magnetics_precursor_revenue
    label: Magnetics precursor product revenue
    basis: reported
    period_kind: quarter
    sign_convention: Positive revenue.
    exclusions_or_definition_notes: Precursor products are not finished magnets, and the segment label does not establish the customer program stage.
    source_family: sec_edgar_8k_exhibit
    selection_label: Magnetics revenue
    research_locator: MINING_WITNESS_INPUT_QUALIFICATION_2026-09-24.md § W-R Selected Q2 measurements, USD thousands unless stated
  - key: revenue_elimination
    label: Intersegment revenue elimination
    basis: reported
    period_kind: quarter
    sign_convention: Negative elimination retains its reported sign in the financial route.
    exclusions_or_definition_notes: The row must remain tied to the selected quarter and segment reconciliation.
    source_family: sec_edgar_8k_exhibit
    selection_label: Segment revenue elimination row
    research_locator: MINING_WITNESS_INPUT_QUALIFICATION_2026-09-24.md § W-R Selected Q2 measurements, USD thousands unless stated
  - key: consolidated_revenue
    label: Consolidated revenue
    basis: reported
    period_kind: quarter
    sign_convention: Positive revenue.
    exclusions_or_definition_notes: The issuer's reported total and linked components are preferred; a newly computed reconciliation requires a native financial derivation.
    source_family: sec_edgar_8k_exhibit
    selection_label: Segment revenue table total revenue row
    research_locator: MINING_WITNESS_INPUT_QUALIFICATION_2026-09-24.md § W-R Selected Q2 measurements, USD thousands unless stated
  - key: price_protection_income
    label: Price-protection income
    basis: reported
    period_kind: quarter
    sign_convention: Positive contractual income.
    exclusions_or_definition_notes: This is a separate financial line and not revenue; designated inventory and affiliate sales must not duplicate external sales.
    source_family: sec_edgar_8k_exhibit
    selection_label: Price protection income line
    research_locator: MINING_WITNESS_INPUT_QUALIFICATION_2026-09-24.md § W-R Selected Q2 measurements, USD thousands unless stated
  - key: gaap_net_loss
    label: GAAP net loss
    basis: reported
    period_kind: quarter
    sign_convention: Loss retains its negative sign in the signed financial route.
    exclusions_or_definition_notes: GAAP result must not be relabeled as adjusted performance.
    source_family: sec_edgar_8k_exhibit
    selection_label: Consolidated results GAAP net loss row
    research_locator: MINING_WITNESS_INPUT_QUALIFICATION_2026-09-24.md § W-R Selected Q2 measurements, USD thousands unless stated
  - key: adjusted_ebitda
    label: Adjusted EBITDA
    basis: company_adjusted
    period_kind: quarter
    sign_convention: The reported adjusted result retains its sign.
    exclusions_or_definition_notes: The issuer's reconciliation and non-GAAP definition travel with the literal and do not erase the GAAP loss.
    source_family: sec_edgar_8k_exhibit
    selection_label: Consolidated results adjusted EBITDA row
    research_locator: MINING_WITNESS_INPUT_QUALIFICATION_2026-09-24.md § W-R Selected Q2 measurements, USD thousands unless stated
  - key: ndpr_production
    label: NdPr production
    basis: reported
    period_kind: quarter
    sign_convention: Positive physical quantity.
    exclusions_or_definition_notes: Production is not output sold and cannot be mixed with the separately defined sales quantity.
    source_family: sec_edgar_8k_exhibit
    selection_label: Operating indicators NdPr production row
    research_locator: MINING_WITNESS_INPUT_QUALIFICATION_2026-09-24.md § W-R Selected Q2 measurements, USD thousands unless stated
  - key: ndpr_sales
    label: NdPr sales
    basis: reported
    period_kind: quarter
    sign_convention: Positive physical quantity.
    exclusions_or_definition_notes: The issuer's sales definition includes intercompany quantities and does not support a verified physical inventory-depletion calculation.
    source_family: sec_edgar_8k_exhibit
    selection_label: Operating indicators NdPr sales row
    research_locator: MINING_WITNESS_INPUT_QUALIFICATION_2026-09-24.md § W-R Selected Q2 measurements, USD thousands unless stated
management_estimate_vs_actual:
  earlier_point_estimate: null
  later_actual: null
  comparison: W-R has no selected management estimate-versus-actual comparison in M1; separately qualified quarter observations are reported without inventing one.
  is_range: false
  is_consensus: false
mechanism: Rare-earth concentrate must be processed into specified commercial material before it can earn external revenue. Magnet development adds product qualification, regulatory testing, and investment before finished-product economics arrive. Contractual price protection can alter price exposure without establishing orders, margins, or returns. Affiliate transfers and eliminations determine how much segment activity remains outside consolidated revenue. Shareholder capture ultimately depends on costs, contractual claims, funding, and the coexistence of adjusted profitability with GAAP losses.
counter_thesis:
  - A later operating indicator showing processing output without corresponding external revenue and qualification progress contradicts retained commercial economics.
  - A corrected segment, period, or elimination basis that changes consolidated external revenue contradicts the selected economic observation.
  - A GAAP loss or capital claim that persists beside positive adjusted EBITDA and contractual income contradicts adequate retained returns.
  - A native contract showing a different designation, threshold, benchmark, capacity condition, or upside-sharing boundary contradicts the claimed protection mechanism.
limitations_vocabulary:
  - missing_derivation
  - stream_threshold_unknown
  - definition_unqualified
  - missing_basis
  - source_only
  - missing_issuer
  - changed_source
  - denied_source
  - page_generation_change
  - industry_total_unknown
forbidden_derivations:
  - do not rename PPA income as revenue
  - do not compute stream entitlement from an unverified threshold balance
  - do not use production as external sales or output value
  - do not infer verified physical inventory depletion from production and sales definitions
  - do not move a half-year total into a quarter because a row label matches
  - do not combine GAAP and adjusted bases as one performance claim
  - no midpoint, percentage, metal-equivalent, or valuation from display strings
honest_degradation: Show reported quarter literals with their row labels, period, elimination sign, and GAAP or adjusted basis; explain the physical, commercial, contractual, and financial distinction; omit unsupported reconciliation, entitlement, inventory, and margin derivations while retaining the qualification and contract limitations.
authority:
  can_rank: false
  can_gate: false
  can_size: false
  can_originate: false
  can_open_entry: false
```

## Antamina stress case (descriptive only)

Antamina separates mine ownership from contractual silver-stream rights. The underlying owners and the stream counterparties do not each own another physical mine, and attributable reserve ounces already carry an ownership basis. Separate stream contracts can differ in silver interest, payability, cumulative-delivery threshold, later step-down, settlement form, and ongoing purchase price.

The supported distinction is therefore descriptive: ownership explains a share of the mining enterprise, while a stream explains a contractual claim with its own cost, price, timing, funding, and threshold profile. The missing contract parameters include reconciled cumulative delivered-ounce balances for each contract and all amendments needed to establish the current threshold state. No entitlement value is computed here.

## Provenance

| Research file | Heading | Source blob |
|---|---|---|
| `research/mining/MINING_WITNESS_INPUT_QUALIFICATION_2026-09-24.md` | Mining M1 witness-input qualification; §1 What became concrete; §2 W-C: Freeport operating outcome versus management's earlier estimate; §3 W-R: MP processing progress versus retained economics | `34548e6b874148e017ec9b4efb7566c3e94123c8` |
| `docs/superpowers/plans/2026-09-24-mining-economic-dossier-implementation.md` | Global Constraints; §6 Task T04 | `a2fca1c561b799b7e49d69c9095e5ffa7dd094cc` |
| `docs/superpowers/plans/2026-09-24-mining-integration-plan-addendum.md` | §4 IR-01, IR-02, IR-07 | `053a59e2b805c8e9eaffcd767c77f9d29cf380a8` |
| `research/mining/MINING_COPPER_PRECIOUS_ASSET_DOSSIERS_2026-09-23.md` | §2 Dossier 1 Freeport; §4 Dossier 3 Antamina's silver | `52ac589b7ab6e220c44deeb143ae33edcd550fde` |
| `research/mining/MINING_BATTERY_RARE_EARTH_ECONOMICS_2026-09-23.md` | §3 B04 MP Materials | `1bef33fc71eaf25f3627988ccb746bd3c827852c` |

