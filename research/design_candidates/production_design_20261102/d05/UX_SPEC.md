# D05 UX specification

Status: complete design candidate specification; implementation and final shared acceptance held. Sources are indexed in [SOURCE_EVIDENCE.md](SOURCE_EVIDENCE.md). “Required” describes the target behavior; “observed” describes audited source or production.

## 1. User, job and completion

Primary user: a self-directed market researcher who starts with a regional market and needs to identify where leadership is strengthening, inspect why, locate relevant companies, and preserve the investigation. Secondary user: a returning analyst comparing a past reading with today's evidence. Their decisions require explicit universes, denominators, clocks and uncertainty, not a larger set of unexplained scores.

The job is complete when the user can:

1. Enter Sectors & themes from the chosen market without losing region or language.
2. Read the strongest current sector evidence and its observation date.
3. Inspect rotation, participation, money and cycle evidence without changing the meaning of a metric.
4. Move from a theme/group to a constituent and its exact listing.
5. Open Company using D07's canonical analysis route.
6. Return to the original universe, selected row, horizon, historical cutoff, filters, sort, chart selection, scroll and keyboard focus.
7. Save deliberately through the existing Research/Watch owner and see verified success or an honest pending/failure/unknown state.

These are acceptance requirements, not claims that Paper performs navigation or that production now passes them.

## 2. Information architecture

The shared shell supplies market navigation, search, account, language, theme and origin navigation. D05 has five task tabs: **Brief, Explore, Cycles, Research, Watches**. Do not add a second global navigation rail or replace shared Company/Research/Watch ownership.

| Home | First question | Progressive detail | Native capability preserved |
|---|---|---|---|
| Brief | Where should I look first? | Leadership handoff, observed outcomes, all native action lanes | Six source lane keys/five rendered columns, Bottoming Watch, source traces, self-grader |
| Explore · Leadership | Which sectors lead this defined universe? | Exact relative returns, comparison, selected-sector inspector | Eleven ETF rows, basket rank tables, benchmark and history coherence |
| Explore · Rotation | Who is gaining or losing relative momentum? | Cohort map/list, dated trail, rotation detail | Broad Finviz universe, eight horizons, turn/events context, top-30 members |
| Explore · Breadth & money | Is leadership widely supported? | Numerator/denominator, price coverage, source periods | Breadth, concentration, fragmentation, ETF creations/redemptions, all five flow windows |
| Explore · Themes & compare | What groups or exposures belong here? | Performance table, taxonomy, multiple selection | Full baskets, confluence universes, rebased comparison, identity-safe membership |
| Cycles | What does the historical rhythm show? | Price/cycle position, confirmed legs, timing, record, methods | Family/phase filters, zoom/log scale, DNA, narratives, recorded versus reconstructed evidence |
| Research | What was the dated thesis and what would falsify it? | State of Themes, Narrative Rotation, source records | Seven setup legs, options/trade-flow context, research priority, allocation model disclosures |
| Watches | What investigations am I following? | Saved scope, evidence and owner receipt | Existing account-owned watch/investigation store; no automatic save on navigation |

Existing six router hashes remain valid. Five task tabs are presentation, not an authority to retire old source routes. The old moving/money/confluence homes remain reachable through Explore lenses and redirects. [S03](SOURCE_EVIDENCE.md#s03--sector-central-cycles-and-routing)

## 3. Primary journey and interaction contract

### Market → Brief

Market selection establishes region, universe, calendar and currency. US opens the measured sector view; China opens a THS concept/sector view with Chinese trading sessions; Canada exposes only supported sector variants; HK exposes its actual sector slug family. A locale change changes text, formatting and price-tone convention, not region, listing, denominator or benchmark.

Brief presents one answer, observation clock, supported scope and a primary “Inspect the leaders” action. The evidence panel carries leadership context; the action-lane section carries engine-owned entry states. They remain separate. A strong sector does not create a buy instruction. If the handoff artifact is unavailable, use the existing generic heading and preserve independently valid sections.

All native action lanes remain reachable. Preserve source order, counts, preview/paid separation and Bottoming Watch as a watch-only strip. A compact brief may summarize these, but “All calls” must expose the full five-column/list equivalent without inventing counts.

### Brief → measured sector evidence

A01 is an observed 2026-10-30 US snapshot: eleven SPDR sector ETFs, 21/63-session relative wealth, all rows visible, selected Energy. The title promises measured leadership rather than an unevidenced change event. A selected row uses a background and focus outline; gain/loss is not the only selection cue.

Selection opens one inspector. The inspector shows entity kind, exact fund/listing, currency, observation clock, benchmark, formula, source and supported continuations. It does not silently replace the table's population. Selection is read-only; no Research/Watch write occurs.

The observed “Sectors 11” versus 38 theme marks defect is a release blocker. Labels, population count, plot marks, list, selected entity and source query must be derived from the same committed scope. A late response for the previous scope cannot replace them.

### Sector → rotation and cycle evidence

Provide three clearly labelled forms of rotation:

- Measured ETF/basket leadership: relative wealth versus a named benchmark and within-family rank.
- Broad subsector rotation: standardized momentum/strength relative to an eligible cohort; period performance and excess in percentage points remain separately labelled.
- Narrative Rotation: slower strategic research score plus independent recent return, durability, crowding and model allocation context.

The UI must never use one formula's axis label for another.

Cycles opens the selected instrument/family with an explicit historical cutoff and mode. Price and cycle-position axes are separate. The phase has a name; phase age has a unit and a lower-bound marker when the start predates history. “At least 18 trading sessions” must not become “18 days” or an exact start date.

**Reconstructed** means calculated later using historical observations. **Recorded then** requires contemporaneous archived availability evidence. Confirmed peaks may have confirmation lag. Show the effective event date and when it became known; do not move markers earlier to improve apparent foresight.

A02 is a separate illustrative design fixture. Its chart, 72/100 position and age are all explicitly labelled as examples. It must never be wired to A01's real Energy row as if those were live values. Production uses coherent real history or an unavailable state.

Cycle controls preserved under progressive disclosure: family selector; search and multi-select; all/clear; group and phase chips; focused comparison; price/cycle toggle; linear/log; range and Home; exact-value table; leg timeline; dated narratives; Cycle DNA; timing/clocks; source trace; research and Company continuation. A narrow viewport may move controls into a labelled sheet but cannot delete capabilities.

### Evidence → theme/group → constituent

Use the native key, kind, universe and namespace. A taxonomy node is a relationship; a theme basket is a measured construction; a sector ETF is a fund; a confluence group has its own gates; a company listing is a security on a venue. Similar names do not establish identity.

The group header shows configured membership, price-history availability and any count-based reliability qualifier independently. A06 uses actual Oct30 source data: AI Power & Neoclouds has 4 configured members and 4 with price history, plus a low/small-group qualifier. This is not proof of current-session prices. Native coverage_pct separately measures positive-volume coverage over the current live set. This does not establish certified Nasdaq-100 membership. Use “Nasdaq desk · configured complex.”

The group gate and each stock's setup remain separate. VRT can have a T2 setup while the group is BELOW_TREND and not buyable. The interface must not turn that stock setup into group eligibility or hide the conflict.

A constituent row exposes symbol, exchange, currency, source date, price/return units and the selected universe. A membership effective date not supplied by the producer remains “Not supplied”; today's member list cannot certify a historical list.

### Constituent → Company → return

D07 owns the canonical Company analysis route and listing resolution. Consume its route builder for /analysis?symbol=…&company_query=…; do not concatenate a display name into an inferred ticker. Preserve legacy stock links through the receiver adapter until the joint route is accepted.

Required return envelope, carried through the existing shared originNav owner:

- originating canonical page ID and safe route/hash;
- region, calendar/currency context, universe and native entity key/kind;
- selected listing and selected row key;
- lens, sort, filters, search, horizon, selected series and chart range;
- historical cutoff, history mode and source-generation identity;
- scroll anchor/offset and focus target;
- bounded navigation instance identifier to reject a stale return.

The receiver distinguishes **received** context from **applied** context. On return, re-fetch if needed, verify scope/generation compatibility, apply selection/filter state, then restore scroll/focus after layout. If the row disappeared, retain a compact explanation and focus the nearest stable heading. Do not silently select another listing or jump to the top.

An expired, malformed or external return target is rejected through the shared safe navigation contract. Account-specific data is not serialized into a public URL.

### Research and Watches

Reading a theme thesis shows its publication date, observation cutoff, supporting records, counterevidence and next falsifier. A newer reading appends/supersedes through the existing source lineage; it never rewrites the older claim's original date.

Allocation remains a research view: model allocations, optional de-risk overlay, playbook, risk history, alerts, validation and AI guardrails are accessible. A model weight is not the user's holding. The recent 10-session return does not silently alter the skip-month strategic score.

Explicit “Save investigation” is the only write trigger. Use the existing Research/Watch API and account owner. Pending remains pending across navigation; preserve the same operation identity. Failed permits retry only after confirmed failure. Unknown outcome permits reading the original record and reconciliation, never an automatic second submission. “Saved” requires owner readback and a usable record link. Sign-out/account switch clears private view data and cancels only locally cancellable reads, not an already submitted write.

**Current persistence limit:** watchstore.js saves the subject in the existing cloud watchlist when signed in, but the question, snapshot and origin remain device-local note data. Its ETF argument accepts only 1–8 uppercase ASCII letters; CNQ.TO, mainland/HK symbols and arbitrary theme IDs cannot use this save function. Show “Subject saved; notes on this device” after the corresponding readback. Cross-device investigation recovery and regional/theme saves remain explicit owner gaps; do not widen the regex or introduce another store in D05. Signed-out saves are device-only. See DATA_BACKEND_CONTRACT.md §8.

## 4. Regional journeys

| Region | Entry and detail | Required distinction | Company continuation |
|---|---|---|---|
| US | Central, SPDR sector ETF, curated basket or broad subsector | ETF versus equal-weight basket versus Finviz cohort; USD/US session | Exact US listing through D07; preserve native stock.html# symbol adapter |
| China | THS concept/sector and mainland fund detail | Concept is not GICS; CNY/CN calendar; no synthetic US flow parity | Exact mainland listing, e.g. 300308.SZ; native china_lookup.html# adapter |
| Canada | Supported /sectors/XEG.TO.html-style detail | CAD; sector-alias constituents are not automatically reported fund holdings; effective date may be absent | Preserve .TO identity, e.g. CNQ.TO; native canada_stock.html# adapter |
| Hong Kong | /sectors/hk-energy.html-style slug | Slug is not an ETF ticker; HKD/local calendar; separate source/template | Exact HK listing through hk_lookup.html# adapter; no mainland/ADR substitution |

A03's China concept membership is illustrative, explicitly labelled. A04 uses source-proven Canadian identities. Production regional interactions were not proved in this audit. D19/D20 must review their respective semantics before build acceptance. [S05](SOURCE_EVIDENCE.md#s05--regional-sector-families)

## 5. States and recovery

| State | User-visible behavior | Retained evidence / next action |
|---|---|---|
| Loading | Keep stable heading, scope and prior dated evidence; mark new request pending | No invented zero, no changing current scope until coherent response |
| Empty filtered result | “No sectors match these filters”; offer reset | Distinguish from zero configured members and source failure |
| Missing source | Show unavailable at the affected section | Other valid sections remain usable |
| Stale source | Show original observation date and source-specific freshness | Build time cannot replace observation date |
| Invalid/mixed generation | Withhold affected comparison | Explain dates/scopes that do not match; keep valid current table |
| 401 | Preserve free preview and sign-in action | No private fetch before settled auth |
| 403 | Preserve free content and permission explanation | No false empty population or auto-upgrade |
| Offline/timeout/malformed | Show source failure and last successful date if valid | Explicit read retry permitted; no duplicate writes |
| Partial coverage | Show numerator, denominator and missing count | Null stays null; comparison denominator stays explicit |
| Elapsed projection | “No current forward estimate” with historical median/window | Do not roll old projection forward |
| Denied internal route | Generic unavailable/not-found surface | factors remains denied; no navigation promotion |
| Save pending | Processing state | One operation, no duplicate submit on context change |
| Save failed | Not saved; preserve entered content | Retry only with confirmed failure and owner allowance |
| Save unknown | Result not yet confirmed | Read original record/reconcile; no blind retry |
| Save success | Saved plus durable record link | Only after verified owner result |

A08 demonstrates these states independently at 320px in dark ZH. It is a state catalogue, not one simultaneously rendered customer page.

## 6. Copy, hierarchy and visual decisions

Use a clear question/answer at the top, concise method adjacent to the chart/table and details on demand. Financial numbers use tabular figures. Keep the scope label, date and unit close to the number they qualify. An understated divider and strong type hierarchy carry structure; positive/negative fill is reserved for the data.

English and Chinese must preserve epistemic strength. “Not detected” is not “safe”; “unconfirmed” is not “false”; “small group” is not “unreliable forecast”; “recorded then” is not “reconstructed”. Keep 来源抽屉 unbroken where the inherited RIG condition applies.

Tokens, dimensions, responsive rules and motion are defined in RESPONSIVE_ACCESSIBILITY.md. Existing licensed assets/components are reused; no new remote design assets were introduced.

## 7. Acceptance boundary

Visual candidates are reviewable. Formal shared design acceptance, source-owner repairs, real user-path proof, auth proof, natural refresh proof and any implementation/deployment remain held. See REVIEW_AND_GATES.md and TEST_MATRIX.csv. Completing this specification does not close the wider production programme.

