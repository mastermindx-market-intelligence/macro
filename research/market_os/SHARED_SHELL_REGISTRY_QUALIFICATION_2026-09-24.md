# Shared-shell migration — existing registry qualification

**Design/evidence only. No application or production change.**

Operation: `market-os-shared-shell-design-20260924-sol-001`.
Existing parent: `WS:MARKET-OS`. Sole branch/PR: `sol/market-os-shared-shell-design-20260924` / Macro #7949.
Chairman intent remains a common application experience across Macro and eventual Terminal convergence, with editable mockups and refinement before site-wide release. This receipt advances that mission; it does not accept the incomplete design or authorize a cutover.

## Result

The incumbent `scripts/build_product_page_registry.py` was run unchanged against frozen source snapshots through its existing injectable GitRunner seam. Its build/override validation succeeded, its own CLI check succeeded, and a second build at the same inputs and timestamp was byte-identical.

| Inventory measure | September 4 committed baseline | Current frozen-source preview |
|---|---:|---:|
| Macro records | 308 | 310 |
| Terminal records | 15 | 17 |
| Mastermind records | 7 | 7 |
| Total records | 330 | 334 |

The current preview contains 314 `page` rows and 20 `family` rows. **334 is a raw generator inventory, not 334 approved customer pages or 334 separate redesigns.** There are four added records, none removed, and 74 existing records differ, predominantly in source-evidence references. Three existing records lose template/builder attribution; that is investigated below, not hidden.

The untruncated Macro `site` tree contains **12,700 committed HTML files**, including 282 at the root, 8,440 under `stocks`, and 2,760 under `research`. These are source-tree counts, not an assertion that every file is a unique, deployed, entitled customer page. Generated families, utility paths, fragments and developer surfaces require different treatment.

The existing registry remains the sole census/compliance owner. No canonical `page_registry.json`, generator, overrides, route registry, database or application file was edited. The temporary preview is verification evidence, not another maintained catalog.

## Exact input identity and verification

- Macro source: `43d8dac58743e22f2acc802db9c436bc0e523e13`.
- Terminal source: `1782ba073a04853c406a1c0909dd64fede28dec0` in `mastermindx-market-intelligence/mastermind-terminal`.
- Mastermind source/protected procedure: `819abc8c23609cdded2b33f6e1bfc7854bd5c847`.
- Skillpack: `mastermind.sol_skillpack.v1`, 1.0.1, bootstrap 1. Fresh master/INDEX matched the same previously loaded COLD_START, ACTIVE_EXECUTION, WEB_CEO_DELEGATION and CLOSEOUT revision.
- Qualification timestamp: `2026-09-24T16:18:13Z`.
- Python: 3.14.7. The host's default Python 3.9.6 could not parse two newer-syntax scripts; the qualification therefore used the already-installed 3.14 interpreter. **All 1,281 top-level script sources then parsed; zero syntax failures were hidden.**
- Exact unchanged generator SHA-256: `ff8b3364545abe3f303d5762ee46e2106ce7aebe6394249d6dd56f7590f46ffd`.
- Source download-receipt SHA-256: `4836494c5fddde9894c50b2b850374691bdc0ab79a25b667c45d55445ab08901`.
- Preview bytes SHA-256: `c9a87d6154eb0e6560b4c32e522ad8a3624e94d807f145ec3c19bbfb4a781813`.
- Canonicalized `pages` array SHA-256, sorted keys and compact JSON: `9d990aa22e26236b9832f90a726dbc2941a2dc11a29d5de405da5d819a6d1313`.
- Qualification receipt SHA-256: `aa6994b563c16fc6538103bed499aeb4dceb8633d81b1b2bbb9679b5c13f2f13`.

Commands actually executed on the isolated snapshot:

```text
/opt/homebrew/bin/python3 qualify_registry.py
  exit 0
  override_errors: []
  schema_errors: []
  syntax_failures: []
  deterministic_repeat: true

/opt/homebrew/bin/python3 snapshot/macro/scripts/build_product_page_registry.py \
  --check --output registry-preview.json \
  --overrides snapshot/macro/config/product_experience/page_registry_overrides.yml
  exit 0
  page registry OK: 334 rows, schema mastermind.page_registry.v1
```

The temporary helper only supplied exact-commit Git-tree listings and source bytes to the generator's existing read seam. It did not evaluate adaptive navigation JavaScript, read the refused Sector tests, invoke builders to generate market data, or change product source. Literal template includes were resolved from the snapshot; no unresolved include was omitted. No real worktree-clean claim was supplied.

**Transport limitation:** this was a source-snapshot qualification, not a normal checkout regeneration or production publication. The generator's default `HEAD`/worktree labels in the temporary preview are not live-worktree attestations; the exact snapshots above are the actual inputs. No deployed route, browser interaction, entitlement or data-quality result follows from schema success.

## Four additions: explicit dispositions for shell design

| Added record | Evidence | Shared-shell disposition |
|---|---|---|
| `macro:glossary`, `/glossary.html` | `templates/glossary.html.j2`, `scripts/build_public_pages.py:142`, public-navigation membership | Retain as a reference/utility destination. Do not invent a new intelligence workspace or change its access rules from the census. |
| `macro:macro_family`, `/macro/<id>.html` | 11 files, all under `site/macro/fragments/`; `scripts/build_macro_suite_pages.py:1419-1446` explicitly emits inner HTML from `_macro_command_fragment.html.j2` | **Not 11 standalone workspaces. Exclude these fragments from full-page sidebar/header wrapping.** Their owning page composes them. The raw generator's generic family/live labels are insufficient eligibility evidence. |
| `terminal:invite`, `/invite` | `terminal/app/invite/page.tsx`; no primary-nav membership | Preserve the invitation utility and its owning identity flow. Do not add it as a market/sidebar workspace or infer public access from missing static gate attribution. |
| `terminal:dev_workspaces`, `/dev/workspaces` | `terminal/app/dev/workspaces/page.tsx`; generator classifies `dev_only` | Keep out of customer navigation. It is a developer reference, not a new customer capability. |

The fragment finding changes the implementation boundary: a global transformation over every `*.html` file would be unsafe. A full-page application frame belongs around page consumers, not inside their dynamically loaded fragments.

## Heatmaps: missing attribution is not missing capability

The preview changes the three existing HK, Canada and China heatmap rows from `templates/market_heatmap.html.j2` / `scripts/build_site.py` attribution to `unknown` / no resolved builder.

Current source independently resolves the reason at the useful boundary: `scripts/build_market_heatmap.py:334-369::render_page` constructs `site / f"{market}_heatmap.html"` and renders **`market_heatmap.html.j2`**. The generator reports the dynamically constructed `out` expression among its unresolved writes.

Therefore:

- Do not remove these heatmaps or commission three replacement implementations.
- Treat them as existing consumers of a shared heatmap template, with a registry-attribution gap to reconcile through the existing generator owner.
- Do not silently hand-edit derived route/template/builder fields to force the artifact green.
- The source binding does not establish current live data or interaction success.

The raw preview still has **95 unknown source-template records** and **37 unresolved output-path expressions**. These are visible attribution limits, not counts of broken or unowned pages. They were not filled by guesses. A schema-valid registry is necessary but not sufficient for automatic full-site migration.

## Verified high-leverage adoption boundaries

These are source bindings for sequencing, not implementation grants:

| Consumer | Existing source boundary | Migration consequence |
|---|---|---|
| US Macro and US stock dashboard | Both bind to `templates/dashboard.html.j2` and `scripts/build_site.py`; their archetypes differ | Qualify one frame adapter against both regimes and dense-board states. Do not assume one screenshot proves both. |
| China macro dashboard | `templates/china.html.j2`, `scripts/build_china.py` | Preserve native country logic and its distinct user job. |
| China Intelligence | `templates/china_intel.html.j2`, `scripts/build_china_intel.py` | Preserve this separate intelligence workspace; the hub mockup does not replace China macro. |
| US/China Sector | Existing native templates/builders and routers | Preserve six US views and five China views, Confluence consumers and legacy hashes in the first adoption. Three-tab consolidation remains unaccepted. |
| Ticker dossiers | Direct source: `scripts/build_ticker_pages.py:6011` selects `ticker.html.j2`; line6261 writes each ticker; its normal output is `site/stocks` | Template-family leverage exists despite the registry's conservative unknown family attribution. Preserve listing identity, deep links and content owners; do not treat every stock file as bespoke UI. |
| Research report family | `templates/research_report.html.j2`, `scripts/build_research_pages.py` | Migrate a reading-layout family while preserving citations, document anchors and public/editorial entry behavior. |
| Terminal workspaces | Existing route modules and shared AppShell; chart retains its focused shell | Adopt common experience contracts through current owners rather than create another shell/auth/state plane. |

Recommended sequence after integrated design approval: qualify the common frame on the US overview/stock-board pair and one native country workspace; validate a dense Sector/security/return journey; then fan out by proven template families. Embedded charts, fragments, login/invitation utilities, admin/developer surfaces and public marketing/editorial pages require explicit disposition rather than blanket conversion.

The acceptance requirement remains a real overview -> sector/theme -> exact security -> existing saved attention set -> return journey, including native view activation, market context, stale/denied states, browser Back/reload, keyboard and narrow screens. No source-family count substitutes for that proof.

## Confluence and source-custody disposition

The scoped read of #7579 comments updated since 15:00Z returned only our existing evidence comment5816792377, not a new MM-07 acceptance return. No new Confluence browser test was run in this phase.

Adjacent carriers were inspected rather than assumed fixed:
- #7345 is merged admin UX/performance work, not a Confluence release receipt.
- #7685 remains open and concerns exact HK/Canada presentation clients; it is not a Confluence fix.
- #6872 remains an active WTI/ontology carrier and also changes shared navigation/registry/access surfaces. Its body explicitly records a manually inserted registry row and pending regeneration differences. That is a current source collision to reconcile before any canonical registry rewrite, not authority for this design branch to overwrite it.

The source blobs for native Sector routers are unchanged from the previous preservation review: US `509cb27e8b1a33813572594fb552794877facd4d`; China `cce323664dce5d81cdc88f1e84e27875fe3d7de8`.

Keep MM-07's serving/activation proof as a release dependency, without repeatedly polling unchanged evidence or making all independent design work wait for it. No duplicate repair, source writer, entitlement relaxation, or worker assignment was created.

## Remaining obligations

The current-source preview is now qualified at the stated level; do not repeat its entire source download or derivation absent a material invalidator. Canonical registry publication is still separate and held behind source-custody reconciliation and the fragment/attribution findings.

The Paper design set is unchanged and incomplete. Preserve the six existing artboards and every specifically refused editing operation on its original target. No alternative tool, new board or regenerated image is a substitute for permitted recovery. Visual acceptance, missing interaction states, implementation planning/custody, repository checks and production proof remain owed.

This receipt is a bounded capability delta: the migration now has a fresh, reproducible source inventory plus explicit exclusions and high-leverage source bindings. **The overall migration remains incomplete and unreleased.**
