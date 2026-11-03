> Integration note: original principal advisory retained as evidence, not RIG approval. The root D02 packet controls the candidate specification. Session-local cache paths below are provenance; durable source identities are in ../evidence/ and immutable GitHub links. The final root contract distinguishes reason-specific comparison refusal, evidence-cutoff admission from legitimate future targets, and source rights from user entitlement.

# D02 historical Macro family: provenance resolution

**Advisory result, 3 November 2026.** The historical `macro:macro_family` row is accounted for by **eleven Macro Command HTML fragments**. It is not evidence of eleven standalone indicator-detail documents. This finding supersedes any indicator-detail characterization in `D02_UX_ARCHITECTURE_ADVICE.md`; it does not change assignment ownership or authorize deletion, routing, registry, Paper or production changes.

## Source pins and decisive evidence

- Assignment: Macro `6e1862867193ec6486a22001a0e4fb515da20448`.
- Current implementation census: Macro `fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9`.
- Existing F03 directory/exporter carrier: `39ac3035b24b66d60dfc65f2cc58a81cb3f2b92d`, Draft #10631.
- F03's own source inventory pin: Macro `b66ca0fcfe7d79f1c90dbfa395e2d43ac5824a6e`.
- The canonical registry read at current Macro still records historical Macro source `73852e221d9ce087abe30b4703de3627773f3351`, generated `2026-10-21T16:34:10Z`. Its `macro:macro_family` row has source template unknown, no builder, and the note “11 committed pages under site/macro/”. [Registry](https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/data/product_experience/page_registry.json)

Both the [historical directory](https://github.com/mastermindx-market-intelligence/macro/tree/73852e221d9ce087abe30b4703de3627773f3351/site/macro) and [current directory](https://github.com/mastermindx-market-intelligence/macro/tree/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/site/macro) contain only `fragments/`. Their eleven child filenames are identical. All eleven current fragment blob SHAs are identical to F03's `b66ca0...` inventory pin, although some historical `73852...` contents differ.

## Exact members and host relationship

Every row below means the exact asset path `/macro/fragments/<filename>`. These are fetched into `/macro_monetary.html`; the hash targets are existing source section identities, not new routes. [Current files](https://github.com/mastermindx-market-intelligence/macro/tree/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/site/macro/fragments), [existing section and workspace map](https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/scripts/build_macro_suite_pages.py#L311-L377).

| Exact asset filename | Existing host section | Existing deep workspace(s) |
|---|---|---|
| `money.html` | `#money`; `liquidity`, `central_banks` subtabs | `macro_liquidity_regime.html`, `macro_liquidity_central_banks.html` |
| `policy.html` | `#policy` | `macro_monetary_policy.html` |
| `rates.html` | `#rates` | `macro_rates_curves.html` |
| `inflation.html` | `#inflation` | `macro_inflation_system.html` |
| `growth.html` | `#growth`; `economy`, `business` subtabs | `macro_growth_real_economy.html`, `macro_business_activity.html` |
| `jobs.html` | `#jobs` | `macro_labor_markets.html` |
| `housing.html` | `#housing` | `macro_housing_real_estate.html` |
| `consumer.html` | `#consumer` | `macro_consumer_payments.html` |
| `credit.html` | `#credit`; `borrowing`, `funding` subtabs | `macro_financial_conditions.html`, `macro_capital_structure.html` |
| `debt.html` | `#debt` | `macro_national_debt_liabilities.html` |
| `trade.html` | `#trade` | `macro_trade_flows.html` |

There is no `overview.html` fragment; the generator explicitly skips the first section. There is no direct `site/macro/money.html`, `site/macro/policy.html`, or analogous direct member in either inspected directory. Do not synthesize those URLs from the registry placeholder.

## Generator and source/data contract

**Resolved generator:** `scripts/build_macro_suite_pages.py::write_fragments`, lines1421–1451. It writes `site/macro/fragments/<section.id>.html` from `templates/_macro_command_fragment.html.j2` using `write_unshimmed_html`, then replaces each file atomically and removes stale fragment filenames. `build_hub` derives sections from the same workspace entries used by the fourteen deep pages, calls `write_fragments`, and enables `fragments_ready` for the host. The source states that the hub reads no independent artifact: it uses the snapshots or typed refusals already read for the workspace pages. This family therefore adds **no separate backend endpoint, indicator registry, historical model or data clock**. [Builder](https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/scripts/build_macro_suite_pages.py#L1404-L1536)

**Resolved template:** `templates/_macro_command_fragment.html.j2`, blob `5a0b38a9871b29711a698e61cd73199f2f33f52a`. It explicitly renders the inner HTML of `[data-mc-figure]` and imports `_macro_command_figures.html.j2`. It renders existing subtab wrappers, movement figures, typed empty states or deep-workspace offers, with the `data-mc-fragment` fetch marker. [Template](https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/templates/_macro_command_fragment.html.j2)

**Resolved consumer:** `site/macro_command.js::maybeFetchFragment`, lines187–256. It fetches the exact relative asset `macro/fragments/<sectionId>.html` once on first activation only when the host declares `data-mc-fragments`; skips overview; checks HTTP success, `text/html` and the marker; restores a typed fallback on timeout/failure; rebases relative links against the response URL; reapplies the selected subtab after insertion. [Consumer](https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/site/macro_command.js#L187-L256)

All eleven fetched current files contain `data-mc-fragment` and contain no document doctype, `html` or `head` marker. None contains a meta-refresh or location-assign/replace/href redirect marker. The builder, template and consumer establish fragment loading, not a navigation redirect.

## Why the canonical row said eleven pages

The existing registry generator folds nested tracked HTML into the first directory's family, then emits a generic `/<directory>/<id>.html` row when no family `write_page()` site is resolved. Its note counts those nested files. That mechanism accounts for the `/macro/<id>.html` label and unknown builder; the actual generator uses `write_unshimmed_html`. This is an evidence-supported census classification issue. [Existing registry generator, lines648–731](https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/scripts/build_product_page_registry.py#L648-L731)

F03 preserves this original row and D02 ownership in its [existing D02 assignment directory](https://github.com/mastermindx-market-intelligence/macro/blob/39ac3035b24b66d60dfc65f2cc58a81cb3f2b92d/research/design_candidates/production_design_20261102/f03/assignments/D02.md#L66-L104). Its inventory receipt reports 14025 tracked HTML assets and 14014 documents at `b66ca0...`, a difference of eleven. That receipt explicitly describes enumeration without deployment or route admission. [Receipt](https://github.com/mastermindx-market-intelligence/macro/blob/39ac3035b24b66d60dfc65f2cc58a81cb3f2b92d/research/design_candidates/production_design_20261102/f03/evidence/inventory-receipt.json)

The existing exporter has the **same blob `c0fb0903a07ceb4ac1081a63fee9fdef86c231d8` at current Macro and F03's inventory pin**. Its document probe accepts only HTML document declarations or html/head tags; `derive_projection` excludes non-documents with reason `html_fragment` before adding family membership. Thus the inspected eleven files cannot become public document routes through this existing exporter. [Exporter filtering](https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/scripts/export_shared_shell_routes.py#L108-L135), [document probe](https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/scripts/export_shared_shell_routes.py#L194-L243)

## Recommended disposition and remaining limits

**RETAIN** all eleven exact fetch assets and their host section/subtab/deep-workspace behavior. **IMPROVE** the D02 census description and coordinate this provenance correction through F03's existing carrier. Preserve `macro:macro_family` as the assigned historical row until its authoritative owner reconciles it; no new registry, IDs, duplicate sessions or replacement route set. Treat fragment retention as part of the Macro Command specification, with fourteen deep workspace documents separately retained.

The unknown builder/template provenance is resolved by inspected source. **No standalone page or redirect target is established**, and this read-only analysis supplies no live/deployed routing proof. Do not create a redirect to the hub or promote these assets to search/navigation destinations merely to satisfy a historical placeholder.

The connector returned empty content for F03's >1MB `generated-document-index.csv` and rejected its binary gzip inventory. Therefore I do not claim direct inspection of its per-file exclusion records. Its receipt, exact exporter source, historical/current directory lists and all eleven current fragment contents were inspected independently. Cached evidence and all eighteen cached text files passed exact Git blob SHA verification.

## Discriminating acceptance cases

1. The D02 retention ledger accounts for exactly eleven source assets under `/macro/fragments/`, and retains the historical family row with this qualification. No invented `/macro/<leaf>.html` document appears.
2. Macro Command deep links with a selected subtab retain that selection after delayed fragment insertion, including `#growth/business` and `#credit/funding`; deep-workspace links resolve correctly under a site URL prefix.
3. Missing HTTP asset, wrong content type, missing marker and timeout each show the existing typed fallback/working workspace destination without a new page, blank panel, false data or stale “loading” state.
4. The existing exporter continues to exclude these inner-HTML fragments as `html_fragment`; they do not acquire anonymous document shells merely because a historical canonical family row exists.
5. The host and deep workspace continue to expose the same snapshot/refusal and source clocks; no fragment-specific “updated now” or model confidence is invented.

**Artifacts:** `advisor-ux/family-resolution/evidence.json` records exact member blob SHAs at all three source pins, the historical row, source read limitations and verified cache manifest. This memo is advisory evidence only, with no Paper grant, review approval, release contract or production proof.

