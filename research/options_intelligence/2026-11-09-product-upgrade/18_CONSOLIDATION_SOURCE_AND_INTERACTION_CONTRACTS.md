# Consolidation source and interaction contracts

**C1 contract specification · planned extensions of existing owners.** Field names below describe required semantics; they are not claims that new wire fields, endpoints or routes already exist. Bind each field to its actual incumbent schema in the source-admission packet. Extend a producer or discriminated union when necessary; do not add a parallel source, auth, retention or state plane.

## 1. Source-family separation

| Family | Grain and eligible meaning | Required provenance | Forbidden substitution |
|---|---|---|---|
| Options aggregate | Declared option group and reported activity population | Exact contract/group, source batch, membership, premium basis, measured NBBO population and event population separately | Aggregate is not a child trade; premium is not investor net inflow |
| Options child event | An admitted individual print or package member | Original event/version, parent relation, cancellation/correction, quote association and actual time precision | Inferred children from aggregate totals or invented order intent |
| Daily off-exchange participation | One equity/ETF and reporting session | Reported numerator/facilities, matched denominator vendor/population, adjustment basis, coverage and revision | All off-exchange equals ATS, or daily volume reveals beneficial owner/direction |
| Short-marked composition | FINRA short-sale report population | Short-marked/exempt convention, eligible report volume, window and exact source | Short interest, net short position, net selling or institutional buying |
| Weekly venue report | Security × reporting week × source venue/category | Period bounds, first availability, report revision, ATS/non-ATS classification, measured eligible total | Same-day trade venue, live print tape or daily-volume denominator |
| Live TP5 off-exchange | Admitted equity prints/clusters | Original TP2/SIP/TRF source, event precision, quotes, correction lineage, rights and chart membership | Source-free ruler, daily totals or weekly ATS report used as a live feed |
| Market structure model | Market/index × independently dated model inputs | Chain, spot, sign/inventory convention, model/version, units, output validity and component dates | Actual dealer inventory, observed systematic fund flow or guaranteed price level |
| Locked weekly range | Immutable forecast/model lock and its validity interval | Lock identity/time, available-at, valid-from/to, model assumptions and full matured outcome denominator | Historical recompute presented as the originally available lock |

The producer's measured population controls the label. For example, a FINRA-reported numerator divided by a vendor's daily equity volume must name both sources and their eligibility; it must not silently claim a fully reconciled consolidated-tape denominator. Existing source qualification determines whether that comparison is admitted.

The settled display can retain daily and weekly context before live TP5 qualifies. That release explicitly shows live prints as unavailable. Terminal PR966 qualifies a scoped decoder source; Macro PR8859's source-free ruler does not qualify mounted live data, a price shelf or a named print venue.

## 2. Minimum logical evidence record

The existing source-retention and domain adapters must preserve these semantics. A missing field is explicitly missing; a schema adapter cannot fill it with the browser's current time or an unrelated source.

| Group | Required information | Invariant |
|---|---|---|
| Security identity | Canonical security/listing identity, display symbol, asset kind, market, currency and corporate-action basis | Symbol is a label; it cannot authorize an unsupported listing or merge adjusted identities |
| Option identity | Exact root, expiry, right, strike, multiplier, deliverable, exercise/settlement and terms version where applicable | One unqualified leg blocks the complete expression |
| Source identity | Supplier/artifact key, source schema, original record/group identity, publication revision, content identity and retained locator | Same displayed date with changed bytes is a distinct source version |
| Grain | Explicit family/granularity discriminator | Daily, weekly, trade, cluster, model and locked range are never interchangeable |
| Clocks | Observation time/session and its precision; reporting interval; source publication; first available/known time and basis; collector receipt; latest read time | Observation, knowledge, release and display clocks stay separate |
| Validity | Model/range valid-from/to, market calendar and expiry rules | Expired is not current; absent lock is not a zero-width range |
| Values | Units, sign convention, raw precision, numerator, denominator and eligible universe | Percent, percentage-point change, shares, contracts, premium, delta and gamma remain typed |
| Coverage | Expected, received, qualified, excluded and unavailable members; reasons and publication cap | A known subtotal is not a full total; capped absence is not cancellation |
| Method | Formula/version, input source identities, baseline window/N/variance convention, assumptions and claim domain | No unversioned client heuristic or mixed baseline thresholds |
| Revision lineage | Original/corrected/withdrawn relation, reason when supplied, superseded-by and receipt | Missing from a current capped feed does not prove withdrawal |
| Rights | Existing source-use and retention grant, current account lifetime, export/replay eligibility and revocation state | A retained reference is not perpetual permission to reveal protected values |
| Capabilities | Actual admitted children, quotes, exact retention, history, model, watch and export capability | A rendered control is enabled by actual receiver/source eligibility, not by a mockup |
| Claim | Observed/model/research/forecast/execution classification, exact family/horizon and allowed consumer use | Freshness, source coverage, scientific maturity and action authority are separate axes |

For nanosecond data, retain the existing TP1/TP2 exact integer-string/BigInt contract. Do not coerce it through floating-point JavaScript timestamps. For session-only inputs, display the session and granularity rather than inventing an intraday timestamp.

A collector's immutable first-known receipt can support a knowledge-time claim in its own scope; it is not retroactive proof of when a provider first published a record. If the required historical availability is unknown, descriptive history may remain available while point-in-time research/replay is unavailable.

## 3. Canonical calculations and permitted interpretations

### Off-exchange

Retire Terminal's duplicated accumulation/distribution classifier and its dependent labels, colors, filters, tests and exports. Canonical versioned observation semantics supply neutral participation/price conjunctions. Price is required for a joint price label. A missing or mismatched price leaves the participation observation visible without that conjunction.

Canonical own-history qualification specifies baseline membership, lookback, sample count, minimum history and zero/undefined variance behavior. The current Terminal and Macro norm thresholds differ; do not pick one opportunistically in the UI. The source owner supplies one versioned method and its literal qualified labels. Review v2 narrative strings independently: retaining a factual classifier does not justify inherited public-tape or large-order-intent language.

Short-marked share uses its own reported population and exemption convention. It is inspected beside participation, not algebraically substituted into participation. Sector composition uses a documented member map/date and reports unknown members.

### Exposure and market models

GEX/DEX/Greeks specify currency, move basis, multiplier and sign/inventory assumptions. Inspectors distinguish known subsets from full qualified books. Matched comparison separates membership changes, changed terms/qualification and actual value changes. Same-session correction uses its original/corrected lineage, not an ordinary next-session comparator.

The per-contract dated Gamma class remains distinct from a market-wide gamma regime. Market Structure does not discharge the original Flow→dated Gamma receiver proof. Flip/wall/max-pain or systematic switch levels remain modeled context in their actual source domain.

### Volatility and ranges

Actual observation tenor, expiry and method determine the label. Percentile and range-rank use distinct formulas and history counts. A missing wing has no invented surface. Fitted IV is allowed only under the fitted-surface owner's qualification; an independently admitted matched-quote IV has its own domain.

Expected move and weekly bands show method and validity. A displayed sigma band is a model construct; empirical coverage and calibrated probabilities require their own evidence. Original locks and outcomes are immutable. A backcast recomputation is labeled and separated from a forward ledger.

### Trade Lab and outcomes

The core comparison includes stock, one supported long option, a same-expiry defined-risk vertical and wait, within actual qualified terms/quotes/model. Pre-expiry price–IV–time analysis and expiry payoff are separate outputs. Quote convention, costs, timing, model assumptions, liquidity, exercise/settlement limitations and unsupported states are visible.

OA-3's one-long-contract same-RTH research ruler cannot be used to score a spread as the same outcome. Authored assessment, underlying return, conditional model result, expiry payoff, executable research quote ruler and actual fill P&L are separately named. No actual trading, sizing or execution authority follows.

## 4. Source ownership and consumer migration

| Confirmed source/consumer seam | Keep or extend | Retirement constraint |
|---|---|---|
| Options brief/Flow builders, flow_desk.json, flowdata/cohorts.json and existing live Tide | Reuse, with typed source and population projection | Do not stop the builder when retiring its HTML shell |
| Per-root GEX/vol/moves and ticker manifest | Reuse current options_hub/GEX producers and receiver validators | Preserve long-tail lookup and independent history/terms |
| scripts/build_darkpool_desk.py | Separate its presentation responsibility from its daily artifact/context output where required | Preserve site/darkpool_eod.json and the existing R2 mirror contract until all consumers migrate |
| engine/darkpool_context.py and its forward ledger | Canonical observation/method owner; repair unsafe text and expose safe typed fields | Keep nightly/forward rules and research chronology; no parallel ledger |
| Terminal eodContext.ts and DarkPoolMini | Remove retired client semantics and consume the qualified versioned observations | Prove all callers; a new full workspace cannot leave the old mini misleading |
| scripts/build_market_structure.py | Existing latest/history and lane-gated forward ledger | Off-lane recomputation cannot advance the forward ledger |
| scripts/build_market_structure_page.py | Presentation adapter can retire after parity | The artifact producer is a different owner/effect |
| Neural Web/world-state projections | Confirmed non-UI consumers of Market Structure and context feeds | Preserve exact supported projections and display-only status |
| TP5 #655, Macro #7367, TP2/TP1 decoders and chart overlays | Reuse source, precision, stream/cache and chart owners | No duplicate subscription, classifier, ingest or chart lifecycle |
| Investigation/retention/Plan/watch/outcome | Extend current typed reference/reader and operation contracts only where needed | UI retirement cannot discard committed cases, exact sources or operation receipts |

The implementation audit closes the consumer inventory by searching code, workflows, registry entries, API/R2 mirrors, exports and retained-reference resolvers at one pinned source cut. Each discovered consumer receives an owner, exact input identity, active/retired state and proof. A negative search in one repository is not a complete audit. No producer retirement is authorized until the closed ledger covers all affected consumers.

## 5. Navigation and compatibility protocol

### Current versus proposed

Current fifteen Options keys and aliases are frozen in 16 §2. New paths /off-exchange and /market-structure are proposed native receiver additions. Their query grammar is a new decoder contract, not an assertion about installed readers:

| Proposed direct receiver | Selection fields | Defaults and refusal |
|---|---|---|
| /off-exchange | symbol/listing resolution; view=daily, venues, live or history; session for daily; reportingWeek for venues; sourceRevision for exact historical selection | Unspecified view opens daily; unspecified symbol opens the browse universe. A requested invalid symbol/period/revision is not replaced by a default |
| /market-structure | market=SPX initially when qualified; view=overview, levels, history or weekly-range; modelSession; sourceRevision; rangeLock | Unspecified market can use the admitted default shown explicitly. An explicitly unsupported market/lock is refused without substitution |
| Options contextual entry | Existing selection owner; proposed optionsPanel=off-exchange, market-structure, settled-flow, opportunities or plans; root/expiry/sourceSession where that receiver admits them | Extend the current workspace decoder/serializer under its owner; never reinterpret an existing tab key as another analytical domain |
| Canonical saved investigation | Existing Analysis investigation URL with exact immutable revision | Saved historical evidence ignores ambient current-symbol changes |

The query names above are the proposed public compatibility contract. The corresponding internal values use existing canonical identities. This is an explicit Options decoder extension, not a claim about installed support. When optionsPanel is absent, retain the current fifteen-key decoder and its default/aliases. When present, decode the named panel as a separate discriminated case in that same owner: off-exchange uses the direct receiver's view/session/reportingWeek/sourceRevision fields; market-structure uses market/view/modelSession/sourceRevision/rangeLock; settled-flow uses flowView=overview, sectors, themes, etf or tide; opportunities uses opportunityView=all or settled-leaders; plans uses planView=draft, compare, saved, watching or review. Existing canonical Investigation URLs and exact revisions remain unchanged.

For the Options donor views, sourceMode=settled, live or mixed is a proposed explicit source-selection extension. It selects only actually admitted suppliers and keeps each visible source clock; an unavailable requested mode cannot silently fall back. An absent new field preserves current behavior. sourceSession/sourceRevision bind an exact retained source where requested. Source mode never reclassifies a daily equity report or weekly venue record as a live print. Macro's settled #leaders maps to the opportunities panel; the existing native tab=leaders alias still maps to Discover.

The additional compatibility field legacyTicker retains a donor ticker intent that was inactive on Brief, Flow, Scanner or Leaders. It is a bounded, encoding-validated copy of the decoded old intent within the existing Options selection owner, not an active root or a global filter. Listing qualification is deferred: an unknown or invalid listing seed does not block the market-wide view, fetch per-name data or retarget another source. On explicit Ticker activation, resolve it through the normal listing/source/access qualifier, then commit root or show selection review. If both an explicit active root and a different legacyTicker are present on a Ticker entry, require review; the serializer never emits both. Remove the consumed seed after deliberate selection. Exact old parsing, precedence, fixed-alias behavior and defaults are specified in 22; new native fields are not retroactively claimed as donor support.

The new panel serializer omits tab rather than giving an unrelated legacy key a second meaning. A URL containing both an explicit new panel and a conflicting legacy tab produces selection review. Selecting an ordinary Options view removes the panel-specific fields through the existing history owner and writes its existing tab value. A new root/expiry/sourceSession receiver validates actual admitted instrument/terms/source identity before committing to the incumbent selection owner; it does not merely change the heading. The default /options path still resolves to Tape. Saved or shared evidence uses the existing exact reference identity, regardless of which presentation entry was used.

Preserve query/hash intent once at the old entry boundary. Source-mode, security, expiry, period, filters, sort, selected evidence and origin are either translated to supported qualified values or shown in an explicit selection-review state. Old hashes are not discarded before parsing. Repeated unknown ordinary query fields and signed transport fields are handled by the existing route owner, not an ad hoc normalizer.

The current OptionsWorkspace derives the active view on every useSearchParams render, so do not reimplement a completed Back/Forward repair blindly. Its writeTabToUrl currently calls history.replaceState with null state. The Shell composition must preserve the existing history owner's key/restore data rather than overwriting it. Qualify the current shared writer or extend it; do not add a second history-key system.

The current exporter refuses a pathname that is simultaneously native and legacy. Each registry generation therefore resolves each path once. Keep historical destination/source identity separately from current resolution. Prove old-client/new-registry, cold and warm navigation, refresh and Back/Forward, including previous-generation restore behavior and rollback.

Return locations are admitted internal origins or existing opaque history receipts. Never trust an arbitrary return URL as navigation or authorization. An invalid return falls back to the explicit originating workspace with the preserved selection available for review.

## 6. Action → receiver → result → return

### Workspace capability composition

The current /options server route's single getLiveOptionsAccessDetail gate must be composed for the consolidated workspace. Extend the existing entitlement owner with a read-only view-capability result over its current decisions; do not introduce a login, billing, entitlement database or plan-name shortcut. Preserve default Tape's terminal_live_options requirement and the settled sources' effective site_full policy, including existing staged/early-enforced rules. Source APIs and exports enforce the same current decision independently of UI visibility.

For settled-only access, the explicit brief/scanner/ticker or direct market/off-exchange view is usable and live controls resolve to their existing denied/unavailable state. Live-only access does not grant settled data. Both grants enable both admitted source classes; neither supplies only the permitted preview/auth path. If one policy service is unavailable, do not erase an independently confirmed grant or turn the outage into an upgrade verdict. Server preview and hydration contain no unauthorized rows. Existing Options keep-alive panes retire protected state, subscriptions and callbacks when their current lifetime/access ends.

These are logical action contracts to bind to incumbent handlers, not a new command bus.

| Visible action / boards | Input and receiver | Result / failure | Return requirement |
|---|---|---|---|
| Inspect activity · C01 | Exact Flow group/version → existing Flow inspector | Qualified aggregate and measured coverage; children unavailable when absent | Same group, filters, scroll and focus |
| Inspect participation · C01 | Equity identity + exact session/reference → shared Off-Exchange module | C02 or an explicit unsupported/rights state | Exact original Options context |
| Open market structure · C01 | Explicit market context, not copied option contract → shared Market Structure module | C03; SPX context labeled independently of SPY | Restore original selected Flow/contract |
| View all sources · C01 | Current displayed source-reference set → existing evidence inspector | Independently dated source rows and limitations | Close returns to invoking control |
| Exact values · C02/C05 | Exact daily record/history selection → domain table in evidence slot/full-width mobile | Raw precision, denominator, dates, gaps and revision | Chart selection and focus preserved |
| Browse equities · C02/C05 | Existing admitted universe/filter state → full domain table | Full qualified population, explicit cap/pagination and unknowns | Selected equity/history remain stable |
| View composition · C02 | Exact short-marking source reference → typed composition inspector | Own denominator, exemption convention and baseline | Participation does not silently change |
| Venue reports · C02/C04 | Same equity plus an explicitly selected reporting week → weekly report reader | C04 or unavailable week; availability date shown | Daily session retained independently |
| Browse venue rows · C04 | Exact report revision and eligible venue population → full report table | Named rows only when supplied; no synthetic print mapping | Same report, sort and selected row |
| Export exact report · C04 | Exact report/filter/revision + current rights → existing export owner | Reproducible file with provenance/units, or explicit failed/unavailable export | No source/selection change; revoke stale callback on account change |
| Inspect model · C03/C07 | Exact model/input reference set → domain evidence inspector | Method, assumptions, dated spot/chain, known subset and original/corrected lineage | Same market, model and origin |
| Compare dated models · C03 | Two explicit qualified compatible revisions → existing comparator | Supported matched comparison or precise incompatibility | Neither source is silently replaced |
| Open range history · C03/C06 | Market + range-lock identity → historical lock reader | Expired/original locks, eligibility and outcomes separately | Current pending-lock state remains pending |
| Open volatility · C03/C06 | Explicit market/root + admitted expiry/tenor intent → Volatility receiver | Exact supported series or unsupported context; no guessed 30D | Preserve source market/model and return |
| New research · C02/C03/C04 | Detached exact typed reference → existing Investigation composer | Unsaved research draft; Save is a separate native action | No automatic save, duplicate case or ambient retarget |
| Open saved research · C01 | Existing case ID + acknowledged revision → canonical/embedded reader | Exact revision or unavailable reference state | Preserve origin and immutable saved identity |
| Source correction · S06 M01/M11 | Original + supplied correction relation → evidence comparison | Original and revised values separately; deliberate current-view selection | Saved decision never rewritten |
| Old desk moved · S06 M09 | Validated legacy translation + origin → admitted receiver | Same supported selection; accessible fallback link | One replacement entry, no loop |
| Review selection · S06 M10 | Rejected old field with retained raw intent → selection review | User deliberately chooses an available scope | No silent broadening or nearest row |
| Verify access · S06 M07 | Existing account/session owner → current access read | Allowed, denied, expired or unavailable accurately | Preserve safe selection without leaking payload |
| Live availability · C04/S06 M12 | Current capability manifest → source availability detail | Explain missing capability and link available daily/weekly views | Never switch source class silently |

Whole-screen, table and source-help controls must use the existing focus/keyboard/IME rules. Mobile exact-value content must remain readable without horizontal page overflow; large analytical tables may have their own labeled scroll region.

## 7. Persistence, monitoring and effect recovery

A source reference is qualified before it can be added to a case. When the exact source-retention contract is unavailable, the composer can retain a local unsaved question but must not claim durable evidence. A generic URL or screenshot does not become an exact historical source.

Reuse native operation IDs, journal, revision conflict and reconciliation. An interrupted Save/Arm may already have applied: read the original operation before any retry, never create a second case/watch to work around uncertainty. Known commit/read-failed, not-applied and unknown are distinct states. A later user edit does not mutate an acknowledged saved revision.

Plan #804's detached whole-plan bridge creates a new case at revision 1 through explicit New research/Add/Save. Existing-case attachment is a different qualified extension. Original 0030/0043/0047 admission, current rights and release holds remain with their owners.

Watch preview and Arm are separate. Selected-node identity, actual evaluator semantics, observation/source clocks, chosen firing, delivery receipts and review revision survive refresh and later firings. A condition firing never confirms a thesis. Capped/unreadable firing history is not “no events.” A new event cannot retarget the assessment being authored.

## 8. Discriminating verification and proof

The bounded implementation packet must test actual failure boundaries: slow A/fast B; account A→B→A; corrected same-date bytes; missing versus zero; capped feed versus withdrawn event; absent matching price; baseline too short or zero variance; split/terms mismatch; delayed weekly revision; expired range; unknown historical availability; malformed/foreign selected source; incomplete quote/package; unavailable export; lost Save/Arm response; and late firing during review.

For each released family, retain one natural source→publication→API/adapter→entitled browser→exact saved/returned evidence chain as applicable. Synthetic Paper fixtures and unit tests verify contracts but cannot supply this consumer proof. Actual source timing, payload size, table/panel load and responsive behavior are measured against the original admitted budgets; no arbitrary new latency threshold is asserted here.

Use existing telemetry and incident owners to record source/version, read outcome, suppression/refusal reason, publication-to-screen age, correction rate and route generation. Do not log secrets, protected payloads or a second analytics stream merely to prove a screen.

## Sources

This contract is bound to the exact references in 16 §8 and the preserved original task JSON/dispatch contract. It composes the existing OptionsWorkspace/optionsIa, Flow/EOD and TP1/TP2 contracts, Macro builders, F01 candidate.4, Investigation/Plan and current registry/access owners. Requalify only affected facts at execution admission; accepted unchanged evidence is reused.

