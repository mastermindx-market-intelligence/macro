# D04 — Route and deep-link compatibility

**Current-source correction:** the handoff says23 legacy mappings. At Macro `df691495abb1c2ba8f61e5624126cb17ad14e056`, `templates/si_workspace.js` contains **21 original entries plus3 merged entries =24**. Retain all 24. The mapping owner is D05's existing Sector Central workspace; this does not add a canonical route to D04 or authorize D04 to rewrite that workspace. Root verified the parsed table after the architectural adviser identified the discrepancy. [Source S19](SOURCE_INDEX.md#s19)

The [machine-readable map](compatibility.json) binds the ten assigned canonical routes, six Discover tabs, ten Quant Lab anchors and special fragment families. The exact 49 basket IDs remain in [source extracts](evidence/source_extracts.json). All compatibility behavior still requires future served-path acceptance; the source count is mechanically checked.

## All 24 current Sector Central mappings

Every incoming fragment below is relative to `/sector_central.html`. Select the owning view before scrolling to the exact target. Two aliases deliberately target a different ID.

| Fragment | Selected view | Exact scroll target | Source table |
| --- | --- | --- | --- |
| `#actnow-section` | `overview` | `actnow-section` | `LEGACY_ANCHORS` |
| `#regime` | `overview` | `regime` | `LEGACY_ANCHORS` |
| `#grader` | `overview` | `grader` | `LEGACY_ANCHORS` |
| `#si-map` | `map` | `si-map` | `LEGACY_ANCHORS` |
| `#rotmap-section` | `map` | `rotmap-section` | `LEGACY_ANCHORS` |
| `#sc-cyclemap` | `map` | `sc-cyclemap` | `LEGACY_ANCHORS` |
| `#board` | `map` | `board` | `LEGACY_ANCHORS` |
| `#si-movement` | `moving` | `si-movement` | `LEGACY_ANCHORS` |
| `#rc-events-mount` | `moving` | `rc-events-mount` | `LEGACY_ANCHORS` |
| `#rotation-app` | `moving` | `rotation-app` | `LEGACY_ANCHORS` |
| `#si-money` | `money` | `si-money` | `LEGACY_ANCHORS` |
| `#internals-section` | `money` | `internals-section` | `LEGACY_ANCHORS` |
| `#scc-leadership` | `money` | `scc-leadership` | `LEGACY_ANCHORS` |
| `#explore-section` | `explore` | `explore-section` | `LEGACY_ANCHORS` |
| `#table-section` | `explore` | `table-section` | `LEGACY_ANCHORS` |
| `#chart-section` | `explore` | `chart-section` | `LEGACY_ANCHORS` |
| `#forming-narratives` | `explore` | `forming-narratives` | `LEGACY_ANCHORS` |
| `#tm-mount` | `explore` | `tm-mount` | `LEGACY_ANCHORS` |
| `#confluence` | `confluence` | `si-confluence` | `LEGACY_ANCHORS` |
| `#sc-app` | `confluence` | `sc-app` | `LEGACY_ANCHORS` |
| `#sc-top` | `confluence` | `sc-top` | `LEGACY_ANCHORS` |
| `#accumulation-section` | `moving` | `accumulation-section` | `LEGACY_ANCHORS_S2` |
| `#si-heat-section` | `explore` | `theme-heat-section` | `LEGACY_ANCHORS_S2` |
| `#si-measured` | `map` | `si-measured` | `LEGACY_ANCHORS_S2` |

Do not change the original21-key literal merely to reconcile the merged count: existing parser tests intentionally distinguish the base literal from the live table. The legacy comment's23 shorthand is not the authoritative executable count. `#si-measured` is the third merged entry.

## Special resolvers remain separate

| Entry family | Existing behavior / owner | Required migration behavior |
| --- | --- | --- |
| `/sector_central.html#theme-<id>` | Workspace yields to theme resolver; valid theme replaces to basket/<encoded-id>.html. Owner: Existing resolveThemeHash; D05/D13. | Preserve this owner and order; test malformed/retired inputs and no redirect loop. |
| `/baskets.html#theme-<id>` | Catalog validated; valid basket detail, invalid sector_central.html#actnow-section; verify multiple-script sequencing. Owner: Basket gateway/build-supplied theme_ids. | Preserve this owner and order; test malformed/retired inputs and no redirect loop. |
| `/baskets.html#ne-<signature>` | Forward fragment; do not consume as ordinary workspace tab. Owner: Sector Central forming-narrative subsystem. | Preserve this owner and order; test malformed/retired inputs and no redirect loop. |
| `/sector_central.html#read-<id>` | Overview then asynchronously open/center matching .rvx-trow[data-mlc-bid]. Owner: Existing workspace pendingTrace. | Preserve this owner and order; test malformed/retired inputs and no redirect loop. |
| `subsector/b-<key>.html` | Path prefix, not a US #b-* fragment. Owner: Subsector baskets dataset; D05. | Preserve this owner and order; test malformed/retired inputs and no redirect loop. |
| `../sector_cycles_china.html#b-<bid>` | Actual regional #b-* family; no universal US resolver inferred. Owner: China cycles; build_theme_detail.py regional receiver. | Preserve this owner and order; test malformed/retired inputs and no redirect loop. |
| `/movers.html` | Fixed replace to /stocks/index.html#today-movers; deliberately discard old query/hash. Owner: Stocks hub compatibility. | Preserve this owner and order; test malformed/retired inputs and no redirect loop. |

`#sc-app`, `#sc-top` and `#confluence` are Sector Central/Subsector Confluence contracts, not proof that the standalone technical-combination screener owns the same DOM. Do not transfer them to a generic Discover root. `#b-*` means the documented regional fragment only where the actual receiver supports it; US basket subsector detail uses a path prefix. A universal `#b-*` resolver remains unproven and must not be invented.

## Source-owned history and asynchronous state

Sector Central already remembers `window.scrollY` per view and uses `SCROLL_GEN` to suppress obsolete queued restoration during rapid switches. It leaves native `history.scrollRestoration` untouched. Explicit targets scroll after view activation; an absent explicit target replaces the fragment with the chosen view. Unknown nonempty hashes fall back to Overview without overwriting the hash; an empty hash becomes `#overview`. Preserve this distinction and propose accessible focus acknowledgment through the existing owner.

Lazy organ initialization forces synchronous layout before initialization because a hidden/background tab may not run a requestAnimationFrame callback. `time_machine.js` depends on the globally initialized `subsector_rotation.js` / `SRR`. A performance refactor that delays every mount into animation frames can leave a blank background/restored tab. Test foreground/background and rapid-view cases. This is source behavior, not newly browser-proven behavior. [S19](SOURCE_INDEX.md#s19)

Terminal Discover has a separate history seam: six accepted tab keys, executable `history.pushState`, current query/hash preservation, existing shell event, and owner-specific Leaders/Radar reset nonces. Macro/Terminal heatmap filters remain largely component-local today. Full filter/range/selection/focus return is the proposed contract in [PRODUCT_AND_UX.md](PRODUCT_AND_UX.md), not something proved by the presence of an accepted return URL.

## Stable detail identity and benchmarks

| Origin | Current detail shape | Qualification |
| --- | --- | --- |
| Technical Confluence | `stocks/<ticker>.html` | Both free markup and hydrated identity links use this path. Preserve URL encoding in dynamic links. |
| Top Picks / Quant Lab | `stock.html#<ticker>` | Different current entry contract; no untested universal replacement. |
| US basket detail | `../stock.html#<ticker>` | Keep relative root and regional receiver. |
| Macro S&P heatmap | Payload `stock_url` + symbol | Inspected payload targets `https://app.mastermind-x.com/terminal?symbol=`. |
| Terminal Dislocations | `/terminal?symbol=<encoded ticker>` | Preserve episode context separately from listing URL. |
| Subsector S&P | `subsector/<key>.html` | Dataset `marketdata/subsector_confluence.json`. |
| Subsector baskets | `subsector/b-<key>.html` | Dataset `marketdata/basket_confluence.json`; distinct from curated basket/<id>.html. |
| Nasdaq subindustries | `subsector_nasdaq/<key>.html` | Dataset `marketdata/subsector_confluence_nasdaq.json`; within-index RS vs QQQ. |
| Russell subindustries | `subsector_russell/<key>.html` | Dataset `marketdata/subsector_confluence_russell.json`; within-index RS vs IWM. |

The Subsector Confluence desk has a verdict, buy-ready/avoid board, double-confluence picks, leadership, sector backdrop, Nasdaq internals and full searchable/sortable group table with per-tab state. Preserve reachable functionality through D05; a link migration must not merge its evaluator with D/W technical combinations. The future shared comparison envelope names dataset, benchmark and interval before comparing observations.

## Parser and migration acceptance

Exercise all 24 mappings, all 49 current basket IDs plus retired/unknown IDs, special resolvers, malformed encodings, shared shell events, and no-JS fallback. A source parser count alone is not the test. Inspect final URL, active view, actual target, focus, scroll, disclosure and Back/Forward behavior. Deliberately test that filtering out free rank1 never makes an originally protected rank free. Preserve original source ranks and access semantics.

Run A001–A007, A042–A043, A061, A064, A071 and A073 from [acceptance_cases.json](acceptance_cases.json). Nothing in this specification applies redirects, registers a new route, changes canonical/SEO policy or implements a parser.

