# Shared-shell production design contract — requirements for F01/F02

**Status: proposed requirements, not a new approved visual template.** F01/F02 must turn these into a versioned reviewed design contract. The live beta shell and current Paper completion references are baselines, not automatic acceptance.

## Product structure

The current principal jobs are Today, Discover, Analysis, Monitor, Research and Portfolio. Regional context is separate: US, China, Hong Kong, Canada and International. Test the existing model against actual user tasks before changing it. Preserve direct entry to specialist tools and focused Terminal without making All Tools the only usable navigation path.

Define four related compositions: investor workspace, focused chart Terminal, public/anonymous page, and internal executive/admin product. They may share tokens and primitives; their navigation, access and primary task differ. `/terminal` already owns focused chart chrome and a Brain singleton; do not double-wrap it with AppShell. Existing Macro Jinja pages remain supported content within the shared host where appropriate. Full native rewriting is not a prerequisite to coherent design.

Global Market Cycles (`/markets.html`), country cycles and International surveillance are distinct products. `/ontology.html` is the WTI Live Path, not merely an issuer taxonomy. `/allocation.html` is Narrative Rotation, not personal holdings. `/analysis` is a substantive workspace with company/thesis/investigation variants under one existing parser. Public `/x/<slug>` is a shared chart. Route names must not decide UX semantics.

## Required ownership contract

| Element | Owner | Consumer obligation |
| --- | --- | --- |
| Global primary navigation, region/context, search entry, account entry | F01 | Use the frozen composition and semantics |
| Tokens, common components, chart/table/accessibility patterns | F02 | Map to source components; request changes rather than fork |
| Product title, local tabs, filters, content, inspectors and domain states | Domain | Fit the allowed slots; retain actual capabilities |
| Search/All Tools taxonomy and aliases | F01 with F03 registry owner | Preserve exact route identity and access, resolve duplicate-looking labels |
| Saved-object and alert mutation semantics | D23 | Domains supply condition meaning, not a second persistence system |
| Analysis route composition and query variants | D07 | D11/D12/D14 supply view contracts; keep analysisRoute.ts authoritative |
| Shared dashboard template | D02 integration; D02 Macro / D03 US regions | Preserve body.page-macro and body.page-stocks boundaries |
| Strategy/model detail archetype | D12 | Asset/regional sessions supply their valid semantics |
| Rotation detail archetype | D05 | D19 supplies China behavior; no invented parity |
| Registry/export and route admission | Existing source owner, tracked by F03 | Do not hand-edit a competing route catalogue |

## Geometry and visual direction

F01 must publish actual rail/expanded-nav/header/local-nav/inspector dimensions and resulting content-container widths. Domain designers test those content widths, not only a 1440px standalone screenshot. Show narrow desktop with expanded navigation and an inspector, compact rail, tablet drawer and phone. Define minimum useful widths and the exact point where a component changes layout.

The visual direction should be refined, recognizable and calm enough for dense financial analysis: clear type hierarchy, aligned data, deliberate quiet space, meaningful chart emphasis and restrained status treatment. Avoid decorating every module or turning metadata into the dominant visual object. Current doctrine disallows colored container borders/accent stripes; nav selection must use an approved fill/text/icon treatment. Test proposed visual directions on Macro, Company and Options before declaring the shell reusable.

Phone design needs an intentional reading/decision order. Preserve access to demoted controls. Decide the global navigation pattern once; each domain must not invent a separate bottom bar. Tables and 2D graphics may have scoped overflow with visible affordances, but the application as a whole must reflow.

## Navigation and context invariants

- Exactly distinguish active destination from selected market/entity context. Show one clear global destination; a regional chip is not a second competing active page.
- Keep global destination search, entity search and executable actions distinguishable. Use concise human labels, aliases and disambiguation by product/region/type. Avoid sentence-length destination labels and duplicate-looking results with no context.
- Preserve existing path, exact query bytes where required, hash anchors, back/forward history, focus and scroll. A redesign may improve presentation without silently normalizing away a meaningful URL contract.
- Preserve company versus listing/exchange identity. Never relabel stale cached US content as China merely because the region control changed.
- Context/theme/language controls specify local versus persisted state. Context changes do not write watchlists, holdings or saved preferences by accident.
- Keep auth, entitlement, session expiry, invalid route, known-but-unavailable route and upstream unavailable content separate. An expired session during a save must preserve uncertain outcome rather than assert failure and blindly repeat it.
- Preserve source clocks, data-access boundaries and consistent release generation across the host and embedded content. Domain data may refresh independently with explicit states; the shell must not pretend mixed snapshots are one synchronized observation.

## Transition and overlay contract

Specify focus trap and restoration, Escape behavior, keyboard shortcuts, scroll ownership, URL reflection and dismissal for every drawer/modal/popover. Choose whether a new inspector replaces or stacks with the previous one. Prevent obscured content and unreachable actions at zoom. Preserve a meaningful return destination when moving between research, company, chart and options.

F01 provides state specimens for guest, denied/plan required, expired session, account unavailable, known route unavailable, unknown route, host/content mismatch, load/error and uncertain save. Domain owners supply their actual copy and data details. These are interaction contracts, not decorative warning cards.

## Migration contract

Use the current canonical registry and shared-shell generator. At audit, the registry had 348 records and the projection 13,123 legacy paths, 17 native paths and 291 directory entries. Pending #1226 proposed 13,987/17/290, mostly additional earnings documents plus two company pages and removal of one withdrawn synthetic fixture. It did not admit the six GMI routes, Expectation Surface or new native equity replay. These are source observations, not served release proof.

F03 must obtain a fresh full generated-document inventory at frozen source pins before implementation acceptance. The audit reconciled current Terminal page modules and Macro root-level pages, but did not certify every nested generated document at the latest Macro head. Preserve explicit exclusions for dev/internal/lab/admin as supported by actual access evidence.

Each route family receives: current host/source, intended shell composition, supported region, template/component, alias/query/hash contract, content-width adaptations, data and access owner, reference IDs, acceptance evidence and migration/rollback plan. Implementation can proceed family by family after reference approval; completion of one family must not imply entire-site migration.

## Foundation handoff acceptance

F01/F02 return a frozen v1 contract, three composed stress-test workspaces, navigation taxonomy, component/token mappings, accessibility and state examples, route/return invariants and an explicit list of unresolved decisions. Domain owners may begin source/retention work before this handoff. They must recompose and re-review affected screens if the foundation contract changes.
