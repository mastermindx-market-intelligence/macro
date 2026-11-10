# Migration, retirement and installed acceptance

## Boundary and owner

**Consolidation C1 · executable plan, not a completed migration.** This contract moves the useful capabilities of Macro options.html, darkpool.html and market_structure.html into the shared Terminal experience. It also accounts for gex.html, options_screener.html, flow_desk.html and flow_leaders.html. No other Macro route, source producer, global bridge or unrelated Paper design is retired by this scope.

The canonical registry/exporter, Shell, entitlement, domain-source, source-retention, deployment and incident owners remain responsible for their existing surfaces. Use 19's bounded packets and original OPT/OPR tasks. The labels below are document proof references, not new runtime tasks, queues or controls.

## 1. Legacy intent and proposed native destinations

All source behavior in this section was inspected at Macro **7e115b6f1f10832b4b123149215ea7a041279753**. It is not evidence that the proposed receivers are installed. 18 defines the new native decoder/serializer extensions.

### Options modes

The donor recognizes five case-sensitive fragment modes: brief, flow, scanner, ticker and leaders. Missing or unknown modes remain Brief. It parses an exact fragment substring ?t= by decoding and uppercasing the entire following string; a nonempty first query-string t overrides that value. Only Ticker mode uses it for per-name data fetches. The other four modes remain market-wide.

| Old entry | Native equivalent to implement | Selection rule |
|---|---|---|
| /options.html, #brief, absent or unknown mode | /options?tab=desk&sourceMode=settled | Market-wide Brief; no invented per-name filter |
| /options.html#flow | /options?optionsPanel=settled-flow&flowView=overview&sourceMode=settled | Settled aggregate Flow |
| /options.html#scanner | /options?tab=vol&sourceMode=settled | Existing Screener key/alias; preserve complete donor controls/population |
| /options.html#ticker?t=SYM or ?t=SYM#ticker | /options?tab=tickers&root=QUALIFIED_SYM&sourceMode=settled | Resolve the actual listing/source before committing the active root |
| /options.html#ticker without an effective t | /options?tab=tickers&sourceMode=settled | Resolve the donor default under the explicit policy below |
| /options.html#leaders | /options?optionsPanel=opportunities&opportunityView=settled-leaders&sourceMode=settled | Source-qualified settled Leaders; do not use native tab=leaders |
| A non-Ticker mode with an effective t | Corresponding market-wide URL plus legacyTicker=DECODED_INTENT | Deferred Ticker context only; never an active global filter |

The proposed legacyTicker field belongs to the incumbent Options decoder/selection owner. It preserves the bounded old intent without fetching per-name data. On explicit Ticker activation, resolve it through the normal listing/source/access qualifier and either commit the actual root or show selection review. A conflicting active root and seed cannot silently choose one. Remove the consumed seed after deliberate selection. This closes a real compatibility gap without creating a global cursor.

Bare Ticker default policy: use the donor's recorded render-time default from the same admitted discovery/source manifest when that identity is supported and accessible. The donor falls back to SPY only when its configured default is absent. The native receiver may use that fallback only when SPY itself qualifies. Otherwise show a Ticker selection-required state. Never let an unavailable default become a fabricated source, arbitrary old selection or a headline claiming another ticker.

The per-name receiver must preserve the donor's Flow/GEX/volatility/session capabilities and deliberate domain handoffs. A matching Tickers label alone is not parity.

### Four existing aliases

| Alias | Current observed chain | Required new behavior |
|---|---|---|
| options_screener.html | options.html#scanner | Same settled Scanner; incoming old query/fragment is not merged into business selection |
| flow_desk.html | options.html#flow | Same settled aggregate Flow |
| flow_leaders.html | options.html#leaders | Same settled Leaders |
| gex.html#RAW_SYMBOL | options.html?t=SYMBOL#ticker when raw fragment passes its rule | Same qualified settled Ticker identity |
| gex.html with no accepted raw fragment | options.html#ticker | Same explicit default-resolution policy |

GEX accepts a raw fragment matching [A-Za-z0-9.-]{1,10}, excluding brief/flow/scanner/ticker/leaders case-insensitively. It uppercases accepted text, but does not decode the fragment before validation. The regex establishes syntax, not listing identity. A query-only gex.html?t=NVDA ignores t. The three fixed redirects drop their incoming business query/hash; Shared Shell's new URL resolution does not merge it back.

The current aliases use MMXSharedShell.navigate(destination, replace), otherwise location.replace. A future one-hop compatibility receiver can remove a redundant intermediate load only if the semantic result is identical. **A server cannot see the fragment:** keep the qualified client compatibility seam for hash-based modes and GEX symbols. Supply an accessible explicit destination when navigation is unavailable. The old no-JavaScript GEX fallback opens bare Ticker and cannot carry its fragment symbol; do not claim otherwise.

### Dark Pool and Market Structure

| Old entry | Native equivalent | What the old URL actually supplies |
|---|---|---|
| /darkpool.html | /off-exchange?view=daily | Full settled browse, with no invented symbol |
| /darkpool.html#dp-table | Same daily browse, then focus/scroll to the full table | Ordinary DOM anchor, not a saved filter |
| /market_structure.html | /market-structure?view=overview | Overview with the independently qualified initial SPX market context |
| /market_structure.html#watch-band | Same overview, then focus/scroll to its qualified observed-context section | Section anchor, not an alert or selected historical range |
| /market_structure.html#msp-drivers | Same overview, then focus/scroll to its source/model drivers | Section anchor, not a model revision |

The two donors have no page-specific business query/hash decoder. Do not retroactively interpret old symbol, ticker, preset, session, reportingWeek, modelSession, sourceRevision or rangeLock parameters as supported filters. The corresponding fields on the new direct routes are explicit new capabilities. If an old input contains an unsupported requested business selection, show the selection-review state; do not apply a plausible nearest match. Other observed chart/title anchors map to the same semantic section after the DOM is ready; an unknown anchor opens overview with no invented selection.

Market Structure's browser-local range preferences are presentation settings: msp-gex-range defaults to 126 with choices 21/63/126/252/9999; msp-sys-range and msp-cor-range default to 252 with choices 63/252/9999. Preserve an available valid setting once through the existing preference owner when origins permit it. Across a different origin, use the documented defaults and an explicit range control; never claim an inaccessible localStorage value was transferred. These preferences do not select historical source revisions, lock identities or decision-time eligibility.

### Decoder and owner boundaries

Known native aliases remain unchanged: default /options→Tape, 0dte→zero_dte, vol/screener→Screener, prism→GEX, leaders/radar→Discover and fundamentals→Analysis. The compatibility receiver first decodes the old route's intent, then serializes an explicit native destination. It does not blindly merge old query fields into the new grammar; doing so could turn a formerly ignored tab or root into a new selection.

Malformed percent encoding produces an explicit safe parser-error/review state. An invalid/ambiguous active listing, an unsupported ticker on a Ticker entry or contradictory active source fields resolves to selection review. An invalid or unqualified inactive legacyTicker does not block Brief, Flow, Scanner or Leaders and does not initiate a per-name fetch; it requires listing review only when Ticker is deliberately activated. Thus /options.html?t=NOT_A_LISTING#scanner remains the global Scanner. Old malformed fragment text such as #ticker?t=NVDA&x=1 is not a generic parameter object; do not truncate it into a successful NVDA selection. Bounded raw intent may be displayed as escaped text, never executed or used as a data path.

Authentication code/error, validated ret and Shell transport parameters remain with their incumbent owners. Consume and validate them in the existing order; never forward credentials to source APIs, log tokens or create an open redirect. Preserve safe origin return, ordinary tracking data where the existing contract allows it, and supported query-byte semantics. Replacement navigation is for the compatibility hop; subsequent intentional domain navigation follows existing history rules.

## 2. One registry generation and one active resolution

The canonical page registry currently accounts for all seven old paths. Route admission and generated projection remain owned by the existing Macro registry/exporter. Do not hand-edit the generated Terminal arrays or add an Options-private registry.

Within a generation, a pathname resolves exactly once. The current exporter refuses a pathname that is simultaneously native and legacy. Admit /off-exchange and /market-structure through the actual native inventory and registry contract. Cut over an old identity to its compatibility receiver in one consistent generation; preserve historical source identity separately from active path resolution.

The release binds exact producer/exporter commit, registry digest, build/document/protocol/bridge versions, current native source and installed consumer. Previous-generation clients must encounter the existing changed-generation recovery rather than a half-upgraded mixed owner. Do not bypass LegacyPageHost's validation or account-lifetime retirement to make a route appear usable.

LegacyPageHost, shared bridge, auth/theme services and Macro navigation remain for unrelated pages. The source/view entitlement composition for settled Options views must be installed before options.html can retire. A correct neutral direct route does not repair the whole-page live gate on /options.

## 3. Stages and exit receipts

| Stage | Work and required evidence | What may progress next |
|---|---|---|
| Admission and census closure | Current custody/holds, source/capability/rights map; all 55 donor rows and seven entries mapped to original owners; closed consumer ledger for any producer proposed for removal | Ready semantic, adapter and domain packets |
| Shadow comparison | Same exact source artifact/revision and population in old and native readers; compare values, units, missingness, filters, exports and corrected versions | Native optional entry under current access |
| Native optional entry | Real source→publication→API→authenticated browser on direct and Options entry; independent clocks, natural records, exact action/return and relevant persistence | Bounded canary through existing release mechanisms |
| Canary | Existing cohort/rollout owner enables an admitted sample; observe natural refresh and degradation under the window below; prove rollback and old-client behavior | Per-donor compatibility cutover |
| Compatibility cutover | One installed registry generation; every old path/alias, auth return and source/view entitlement resolves correctly; full capability parity or explicit accepted removal | Archive duplicate presentation |
| Archive | Immutable old source/render/design copies, hashes, consumer/compatibility map and rollback receipt; remove obsolete chrome and navigation under existing owners | Normal monitored operation |
| Whole-suite accounting | Original vertical, mandatory deeper scope, usefulness, source/science/consumer gates and original OPT-103 dispositions | Only the scope actually proven may be called complete |

A qualified source correction can be released before the UI migration. A qualified domain can progress while a different source family is unavailable. **Per-donor retirement requires every retained capability of that donor**, including its existing filters/exports and delayed venue content. A new live-print extension does not become a prerequisite for retiring a daily/weekly donor merely because it appears in the same workspace. Conversely, a preview placeholder cannot count as replacement parity for an existing working capability.

Do not create a parallel production analytics deployment just for shadowing. Reuse captured natural artifacts and existing read-only/test/canary facilities; any actual deployment needs its normal authority.

### Canary window and acceptance rule

Planning decision for the actual admitted migration cohort: include two consecutive scheduled daily source/publication cycles for daily-dependent views, one naturally published report for each released weekly-report family, and one validity rollover for a released locked-range view. A newly fetched copy of the same old artifact is not a new publication. These are separate source-specific evidence windows, not a universal delay on unrelated releases. Use existing telemetry and return paths; no new daemon or duplicate watcher.

Exercise correction, unavailable source, revoked access and rollback with controlled permitted fixtures where a natural incident would be unsafe or impractical; label those results as injected. Require at least one natural production record for each released family. Do not cause an actual financial or destructive effect to manufacture a test.

Expand only with zero unresolved selection/rights/revision-loss, semantic-fabrication or compatibility failures in the observed acceptance set. No unobserved failure rate or population guarantee is implied. Compare measured performance and source age with the original admitted budgets and recorded pre-cutover baseline; investigate any material regression before expanding. This plan does not invent a new numerical latency SLO.

## 4. Discriminating acceptance matrix

| Proof | Input/action | Required observable result |
|---|---|---|
| Legacy modes and precedence | ?t=NVDA#ticker?t=TSLA; ?t=NVDA; #scanner?t=NVDA; ?t=NOT_A_LISTING#scanner; unknown/case-mismatched mode; repeated/empty t | Ticker NVDA in the first case; market-wide Brief/Scanner with deferred context in the next cases, including an unqualified inactive seed; exact old default-mode behavior; deterministic first-value precedence |
| Alias behavior | GEX raw/reserved/encoded/query-only cases; all three fixed aliases with extra fields | Source-equivalent destination; qualified listing or explicit default/review; no invented merged business filters |
| Direct source entry | Bare Dark Pool/Market Structure; supported anchors; newly supported native selection | Full browse/qualified overview by default; section focus preserved; only native fields supply explicit new selection |
| Source and revision | Same-date corrected bytes; delayed weekly report; old range expires before next lock | Original/corrected references distinct; reporting and availability clocks visible; expired lock cannot masquerade as current |
| Denominator and method | Missing versus zero; short history; zero variance; absent matched price; incomplete book | Correct missing/refusal/partial states; no synthetic z-score, price conjunction, comparable total or directional inference |
| Navigation and history | Cold/warm entry; tab/panel change; refresh; Back/Forward; Sector/Futures/Equity return | Exact subject, filters, scroll/focus and source identity; existing Shell history state preserved; native time/contract grammars unchanged |
| Generation boundary | Previous registry client, changed registry/build, visibility return, rollback | Existing release/version validation and safe recovery; one path owner, no loops or double host |
| Rights and account | Settled-only, live-only, both, neither; policy unavailable; revoke during fetch; A→B→A | Correct independent capability, preview without protected payload, old callbacks/subscriptions retired, no cross-account cached response |
| Export | Exact report/filter/revision; unavailable source; revoked prepared callback/direct URL | Exact entitled reproducible contents or explicit failure; API enforcement independent of hidden UI; OPT-040 dependencies/receipt satisfied |
| Research and Plan | New reference; exact Save; lost Save response; later source correction | Existing composer/operation owner; known commit versus unknown distinguished; no duplicate case; original revision never restamped |
| Monitoring/review | Lost Arm response; later firing during authored assessment; capped/unreadable history | Original-operation reconciliation; selected firing stable; delivery and assessment separate; no fabricated empty/full history |
| Accessible density | 1440/1280/820/390, 1920 readability, 200% zoom; EN/ZH; both themes; keyboard/IME/touch | Existing geometry, one modal/scroll owner, no clipped critical content, exact tables and safe focus return |
| Full original vertical | Two supported dossiers plus no-trade through comparison, Save, selected-node monitoring, outcome review and usefulness | All original OPT-100/OPR-110 conditions and applicable additions; no substitution by the narrower rows above |

A source-free decoder or synthetic browser fixture proves only its own scope. Every release receipt records the exact input artifact, producer/build/API identity, current consumer/account class, actions, observed outcome, relevant failure cases and remaining limits. Reuse accepted unchanged proof at its actual head/domain.

## 5. Consumer ledger and archive manifest

Before disabling a producer, enumerate and disposition its consumers across both repositories, workflows, rendered site, APIs/R2 mirrors, current Terminal EOD/TP2/TP5 paths, Neural Web/world state, historical readers, exports, retained-reference resolvers and research/forward ledgers. Record owner, path, exact input identity, frequency, current status, replacement or retained producer, acceptance link and rollback. A negative search in one repository is not closure.

The expected decision is to **retain shared producers** while retiring page rendering. Market Structure latest/history, nightly forward ledger and weekly locks have distinct retention/chronology roles. Source names containing macro are not a reason to move or delete a producer. Only proven consumer closure and the existing owner may authorize a later producer retirement.

For each donor archive, retain:

- Last accepted source/render/build identity and immutable copies with hashes.
- Capability disposition and value/population/filter/export parity receipts.
- Exact old-route/alias decoder and active compatibility generation.
- Source/consumer/rights map and installed proof.
- Paper donor file/page/node identities, accepted replacement links and frozen exports.
- Rollback version, tested action and original operation/persistence limitations.

Archive the obsolete presentation and its historical configuration. **Keep supported compatibility receivers/redirects active.** Their later removal is a distinct owner decision with consumer/use evidence. Do not delete old templates or Paper pages merely to make the new suite look complete; mark historical artifacts accurately after adoption.

## 6. Rollback and operational handover

Use the existing release/incident mechanism and source owner. Roll back only the affected surface/generation. Preserve acknowledged cases/revisions, frozen expressions, historical artifacts, retention rights, original operations and unresolved effects. Do not copy protected payload into public static pages or reissue Save/Arm on another carrier.

A rollback must never restore the retired accumulation/distribution heuristic, false net-inflow/OI-intent wording or a known authorization leak. Keep a neutral read-only/limited receiver available where qualified; otherwise make the affected capability explicitly unavailable. Restoring an earlier presentation is acceptable only if its source semantics and access remain safe.

Prove that rollback maintains working old links, current account lifetime, exact source/revision identity and unrelated Macro/Terminal pages. Observe recovery through existing telemetry, record the actual incident/action/result and reassess the next useful phase. A recorded rollback plan without an exercised permitted path is not migration acceptance.

## Sources

- [Options template and decoder](https://github.com/mastermindx-market-intelligence/macro/blob/7e115b6f1f10832b4b123149215ea7a041279753/templates/options.html.j2), [GEX alias](https://github.com/mastermindx-market-intelligence/macro/blob/7e115b6f1f10832b4b123149215ea7a041279753/templates/gex.html.j2).
- [Dark Pool template](https://github.com/mastermindx-market-intelligence/macro/blob/7e115b6f1f10832b4b123149215ea7a041279753/templates/darkpool.html.j2), [Market Structure template](https://github.com/mastermindx-market-intelligence/macro/blob/7e115b6f1f10832b4b123149215ea7a041279753/templates/market_structure.html.j2).
- [Canonical page registry](https://github.com/mastermindx-market-intelligence/macro/blob/7e115b6f1f10832b4b123149215ea7a041279753/data/product_experience/page_registry.json), [route exporter](https://github.com/mastermindx-market-intelligence/macro/blob/7e115b6f1f10832b4b123149215ea7a041279753/scripts/export_shared_shell_routes.py), [generated bridge at the source cut](https://github.com/mastermindx-market-intelligence/macro/blob/7e115b6f1f10832b4b123149215ea7a041279753/site/shared_shell_bridge.js).
- [Architecture source pins and holds](16_CONSOLIDATED_ARCHITECTURE.md), [new source/action grammar](18_CONSOLIDATION_SOURCE_AND_INTERACTION_CONTRACTS.md), [original release acceptance](11_RELEASE_AND_DESIGN_CONTRACT.md), [conditional bindings](20_COHORT_AND_CONDITIONAL_BINDINGS.json).

