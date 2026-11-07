# D06 current Terminal source delta — 3 November 2026

**Source qualification only.** The D06 design carrier remains Draft #10655. This document binds relevant later Terminal source to the original Phase 2A specification; it does not implement, deploy, approve, or replace another owner's contract.

## Exact comparison and limits

Earlier Terminal pin: **3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9**. Later protected Terminal master observed: **2ded360882b9c721e690907ff363b553781fb920**, ten commits ahead. The browser's dpl token equals that later SHA; bundle identity and every served route remain independently unattested.

The compare endpoint returned 300 filenames, so it was not treated as an exhaustive changed-file list. Separate recursive trees at both exact commits reported truncated=false. Ten core files — ChartPanel, ChartPane, TerminalShell, ChartContextDock, VisualIntelligencePanel and its CSS, visualIntelligence, originNav, BrainWidget and mastermindBrain — have identical blobs at both pins. The current contracts for their existing ownership therefore remain applicable. Paper and Macro sources retain their separately recorded pins.

The following changes are material to D06's chart-entry, source-clock, data-state or Scripts implementation boundaries. Neighboring Company, Options and Sector designs remain with their existing owners.

## Company search is a listing decision with retained query context

[SymbolPicker](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2ded360882b9c721e690907ff363b553781fb920/terminal/components/SymbolPicker.tsx) now accepts onCompanyPick, searchSeed, initialSelection and optional portalDialog. [SearchModal](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2ded360882b9c721e690907ff363b553781fb920/terminal/components/SearchModal.tsx) treats a company-scope pick as a preview of a valid company row. Explicit Open, or Enter when that row is already previewed, commits the exact listing and trimmed query. Editing search text clears the preview. The ordinary symbol/compare/add modes are not universally converted to this company flow.

[companySearchContext](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2ded360882b9c721e690907ff363b553781fb920/terminal/lib/companySearchContext.ts) defines the limited handoff:

| Value | Current source rule | D06 consequence |
| --- | --- | --- |
| Selection | Plain object with only symbol and query; symbol already canonical | BABA and 9988.HK remain distinct listings; no display-name alias |
| Typed query | String, trimmed, at most 160 characters; rejects controls; empty string permitted | Empty search context differs from absent context; no silent truncation/coercion |
| Analysis URL | Encoded /analysis?symbol=…&company_query=… | Retain the exact accepted href through originNav; do not promise generic Terminal tf/bar/query parsing |
| Query reader | Exactly one company_query value; duplicate/absent/malformed returns null | No arbitrary first/last-value inference for this new field |
| Back context | mmxCompanySearch annotates the existing history entry | No second history store or guarantee of row/scroll restoration |
| Trading currency | Matching fund ticker and three-letter uppercase quote_currency | Never substitute statement currency, region or an exchange guess |
| Venue | Exact manifest symbol row, explicit Equities class, usable mkt | Missing or mismatched source is unknown, not a verified venue |

D07/Search owns preview, selection and Analysis presentation. Terminal/originNav owns its accepted chart entry and safe return href. F01 owns shared generic versus named navigation. This source shows a bounded company-search contract; it does not prove the complete Search→Analysis→Terminal→Back journey, nor that every chart launcher carries company_query.

**Keep/change:** retain the new exact-listing preview/commit and query context wherever the relevant owner uses them; preserve ordinary chart symbol selection and current route grammar. Extend NAV02/NAV07 and add NAV11 for the company-specific parsing and commit boundary. The proposed source extension for generic incoming Terminal interval/bar remains blocked pending its actual owner contract.

## Cache acquisition cutoff is a separate clock

[dataCache](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2ded360882b9c721e690907ff363b553781fb920/terminal/lib/dataCache.ts) adds an optional observedAtMs to the existing entry. On a usable data response it takes the minimum of request-start time and finite parsed Last-Modified/Date headers. Existing ts remains the commit/TTL/eviction clock. [idbJsonStore](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2ded360882b9c721e690907ff363b553781fb920/terminal/lib/idbJsonStore.ts) persists the optional field; memory, disk and stale-revalidation paths carry it forward.

The new ohlcObservationCutoff(symbol, payload) is a read of the existing cache. It returns a cutoff only when the current entry's data is the exact supplied object, the timestamp is finite and positive, and it is no later than the entry timestamp/current time. A cloned or replaced payload, absent entry, invalid cutoff or legacy disk record without the field yields null. It uses store.get rather than the cache's touch helper; it does not introduce a second cache or a freshness mutation.

| Clock / evidence | Meaning retained |
| --- | --- |
| Bar time / timeClose | Market interval identity from the bar producer |
| Source published/build time | Producer evidence only when actually supplied |
| observedAtMs | Conservative acquisition cutoff bound to this exact parsed cached payload object; not an independently measured acquisition instant |
| ts | Existing cache commit/TTL/eviction bookkeeping |
| DOM capture time | When a UI observation was collected |
| Painted generation | Which result the active chart actually adopted |

Do not convert acquisition cutoff into “live,” source publication time, market observation time, or proof the chart adopted a response. Header provenance is not independently certified here. Missing legacy cutoff remains unknown. Existing cache capacity, TTL, LRU/eviction, stale-response and supersession rules remain; there is no globally non-evicting cache.

**Keep/change:** retain this field and exact-payload binding in future presentation work. DATA09 specifies old headers, absent/invalid clocks, exact versus cloned/replaced objects, disk reload, stale revalidation and supersession. Existing DATA04 remains the request/outcome-state case. Do not manufacture a universal as-of badge on legacy envelopes.

## Missing public data has an explicit route fallback

The new [app/data/[...path]/route](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2ded360882b9c721e690907ff363b553781fb920/terminal/app/data/%5B...path%5D/route.ts) is a **missing-resource fallback, not a data proxy**. Existing public files are intended to be served first by Next. For a resource reaching this dynamic fallback:

| Method | Source-defined response |
| --- | --- |
| GET | 404 with JSON error=not_found, Content-Type application/json, Cache-Control no-store |
| HEAD | Bodyless 404 with the same content type and cache policy |

The purpose is to keep missing data from becoming an HTML account-unavailable shell with a streamed 200. This does not establish upstream provider absence, whole-market coverage, a successful public-file fetch, or a reason for every prior Stage error.

**Keep/change:** preserve the fallback and existing positive-public-file precedence. Extend DATA04 to verify actual served GET and HEAD, valid public resources, and absence versus network/auth/parse outcomes. No such request/response fixture was executed in this continuation; this is a source contract for the owning Next/data builders.

## Pine retained-series export is an opt-in evidence API

The [host](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2ded360882b9c721e690907ff363b553781fb920/terminal/lib/pine-engine/host.ts), [worker](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2ded360882b9c721e690907ff363b553781fb920/terminal/lib/pine-engine/worker.ts) and [retained-export](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2ded360882b9c721e690907ff363b553781fb920/terminal/lib/pine-engine/retained-export.ts) add an optional referenceExport request to an existing worker run. Ordinary runs remain ordinary runs; this does not add a customer CSV/download action to PineEditor.

| Contract | Source-defined behavior |
| --- | --- |
| Input binding | Original inputBytes plus expected inputSha256, probeSha256 and columnsSha256 |
| Host input bounds | At most 64 MiB source bytes; rejects shared backing buffers and uncloneable requests |
| Receipt validation bound | 1–100,000 bars, checked during retained-receipt construction; this is not a claim of host admission or a pre-evaluation runtime limit |
| Run custody | Clone the admitted request so a boot repost preserves bytes/columns/options; retain existing slot supersession and host budget |
| Execution | Worker required; compile the supplied source for the reference run instead of trusting a possibly mismatched AST cache label |
| Probe language | Positive restricted AST allowlist, including unselected branches; current name asc-six-series-v1 |
| Runtime evidence | Identified worker build and source closure; valid clocks/options/session phase; no runtime warnings; valid effective integer inputs |
| Row evidence | Explicit ordered, nonoverlapping bar intervals and full row count |
| Required outputs | Exactly one aligned, full-length TG_rsi, TG_rsi_macd, TG_rsi_macd_signal, TG_rsi_macd_hist, TG_stoch_k and TG_stoch_d |
| Result | retained with bytes, byteLength and SHA-256, or unavailable with a reason |
| Receipt schema | terminal.pine.reference_export.v1; origin terminal_native_worker |
| Crucial qualification | normalizationBinding is supplied_pair_unverified_derivation |

Digest agreement binds supplied raw and normalized inputs; it **does not independently prove that normalization derived those bars from those bytes**. A retained receipt is also not financial/model validation, full Pine compatibility, trading authority, a cross-runtime parity result or served-product acceptance.

Unavailable reasons include invalid input/shared bytes/uncloneable request, unidentified worker build, invalid clocks/session, runtime warning, invalid effective input, source-binding mismatch, incomplete/misaligned series, unsupported probe, timeout, cancellation, failed run and worker_required. The UI must not label a normal successful run as “evidence retained” when no matching retained receipt exists. Ordinary synchronous fallback stays useful for its original contract; it cannot silently certify reference evidence.

**Keep/change:** preserve this optional API in the existing Pine worker owner and its explicit failure states. Add SCRIPT06 for one qualified retained result plus negative boundaries and unchanged ordinary runs. Keep SCRIPT05's existing 130-bar synthetic diagnostic distinct; this reference contract does not turn the editor diagnostic into a real-data backtest. The 76 existing feature-group dispositions remain unchanged, with this contract attached to the existing Scripts/engine retention obligations.

## Navigation current-state semantics

[AppNav](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2ded360882b9c721e690907ff363b553781fb920/terminal/components/AppNav.tsx) and [MobileNav](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2ded360882b9c721e690907ff363b553781fb920/terminal/components/MobileNav.tsx) now distinguish aria-current=location for a parent location from aria-current=page for an exact destination under their respective source conditions. The previous guest Scripts screenshot showing Today/page remains a historical observation at its earlier deployment token. It must not be presented as a verified defect of this later source. The new semantics still need actual served sibling/deep-route accessibility checks; source correction is not a blanket navigation acceptance.

## Builder ownership and acceptance

| Seam | Existing owner | Evidence required before acceptance |
| --- | --- | --- |
| Company preview/query/listing | D07 / Search / Company source owner | Exact listing and query across preview, Open, route and Back; current head and served path |
| Chart return | Terminal originNav / F01 | Exact safe accepted href; any row/scroll fidelity proven by originating owner |
| Cache cutoff | Terminal dataCache / IDB owner | Exact-object timestamp semantics, legacy unknown, unchanged cache behavior |
| Missing public data | Next/public-data owner | Served positive and negative GET/HEAD fixtures |
| Pine reference output | Existing Pine worker/runtime owner | Real qualified worker receipt, negative states and ordinary-run compatibility |
| Reader fit/state | Terminal chart/reader/rail owner, F01/F02 mapping | Measured fit and state/focus tests from the responsive audit |

All four added migration specifications — LAY07, NAV11, DATA09 and SCRIPT06 — are **specified, not executed**. Together with the existing 71 they make 75. No independent GitHub approval, product/taste verdict, Paper write grant, runtime installation, production test or model-validation result is inferred from these source reads.

Original source law and immutable assignment boundaries remain intact. F01/F02 release and D06/C4 authoring admission remain external gates; the current draft contains a source-ready handoff for their eventual consumption.
