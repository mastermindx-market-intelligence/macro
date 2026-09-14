# Macro Alert Center — Market Changes Desk experience freeze

**Status: SPEC_ONLY / ACCEPTED EXPERIENCE CONTRACT FOR FIGMA.** This freezes the product and interaction target for the shared Macro `alerts.html` redesign. It is not a Figma completion claim, implementation, schema change, source activation, customer notification, deployment, or production acceptance.

**Chairman direction:** Chris approved the Market Changes Desk direction and asked Sol to continue after a deeper hardening pass. The useful Terminal Alert Center prototype remains a separate preserved product and is not repurposed for this target.

**Current procedural pin:** Mastermind protected `master` `af9fce32861f9c1496b85a580e3569712170d92b`, Skillpack 1.0.1 (`INDEX`, `COLD_START`, `CLOSEOUT`). **Macro source pin:** `2e972811e82a56928e5f4871300ecb91daf0bed3`.

**Controlling background:** `MACRO_ALERTS_MARKET_CHANGES_DESK_HARDENING_20260914.md`. This freeze narrows that research into the exact user-facing target. The hardening document remains controlling for source/intelligence edge cases not repeated here.

## 1. Product promise

Keep the customer-facing name **Alert Center**. Its product identity is **Market Changes Desk**:

> Show me what materially changed across Mastermind's shared market evidence, what deserves attention now, why it matters, and the evidence behind it — without making me monitor every source dashboard.

This route is the estate's `monitor` archetype. Its identity device is the **change-log timeline**. It must not become another `start.html` command center, another `macro.html` regime dashboard, or Terminal's private notification inbox.

The design succeeds when a cold user can:

1. identify the most important fresh changes in roughly 5–10 seconds;
2. scan ordinary recent changes immediately after them;
3. inspect one observation's evidence in place without losing the timeline;
4. reach the complete population or historical firings when needed;
5. understand when missing evidence limits what Mastermind can safely conclude.

## 2. Information architecture

There are exactly three primary tasks:

### Now
The default product: board-day change timeline.

Sequence:

`page/session header -> compact context/coverage -> What Matters Now (0–3) -> Today -> Yesterday/earlier -> counted Explore link`

What Matters Now is **part of the timeline**, not a hero dashboard above it.

### Explore
The complete accessible alert/evidence population. This is the power-user surface for search, filters, source facets and canonical attention ordering. It is where useful #7022 uncapped-explorer ideas belong after fresh-main reconciliation.

### History
Actual logged firings and corrections only. History never interpolates continuous state between observations and discloses any publication/history cap.

Do not ship a `Situations` primary tab in v1. `Related observations` may group same-source, exact-subject observations and must state that grouping is not independent confirmation. **Situation** remains reserved for a later grounded cross-domain capability.

## 3. Tier-1 header and chrome

The first customer-visible block stays compact. Target copy architecture:

**Alert Center**  
*Market changes worth understanding now.*

One session line: `New York session · <board day>`.

Optional local-device continuity may say `<N> observations since your last visit on this device` only when the existing browser-local state can support it. It is not account read/unread state and must be labelled as device-local if surfaced.

Three task tabs: **Now / Explore / History**. Tab state remains shareable through the existing URL/hash approach.

Always-visible market context is one restrained inline strip, not a rail or dashboard:

`Regime <plain word> · Cross-asset <plain word> · Next catalyst <event/date>`

When coverage is partial, this normal strip is replaced/preceded by the appropriate coverage warning. A successful read is not advertised as “all data fresh.”

**Viewport budget:** header + tabs + ordinary compact context should remain about `<=140px` desktop and `<=120px` mobile before the first lead/timeline row. No giant verdict word, gauge, scoreboard or story strip may consume the fold.

## 4. What Matters Now

This is a pure presentation projection over canonical observations. It creates no new event/development identity and changes no source or notification authority.

### Eligibility

- known usable event board date;
- canonical `fresh` recency, currently `age_days <= 2`;
- fresh `act` tier is eligible;
- fresh `watch` tier is eligible only when post-governance severity is `major` or `critical`;
- `context` tier is ineligible in v1;
- future events are ineligible/quarantined;
- cross-asset confirmation can affect existing order/explanation but cannot promote an otherwise ineligible observation;
- null/negative validation remains visible and any existing governance demotion remains controlling.

Take at most three eligible observations in existing canonical attention order. Never pad to three, force source diversity or synthesize an aggregate solely for visual balance.

### Lead-row anatomy

Lead rows are larger than normal timeline rows but still row-like, not hero cards:

`source · event date`  
**plain short change**  
`one plain meaning or limiting clause`  
`research-attention action ->`

Target presentation actions:

- eligible act: **Review now**;
- qualifying cross-asset disagreement: **Confirm first**;
- qualifying watch: **Watch closely**.

These translate attention, not trading authority.

If a fresh recurring observation qualifies, say **Observed again / Re-fired today**, never “still active” unless the source has a continuity contract.

If zero observations qualify, render a quiet line rather than an empty hero:

> **No major fresh change requires review right now.**  
> `<N> other observations are available below.`

## 5. Partial coverage mode

Consequential source/backdrop failure changes page mode.

Tier-1 message:

> **Market read incomplete**  
> `<plain source/reason> is unavailable. Mastermind is withholding the whole-market summary; available source-specific changes remain below.`

Do not show a whole-market pressure score/stance when its authority is withdrawn. Do not substitute a conservative number. Do not turn missing evidence into “quiet market.”

Nonblocking source unavailability is disclosed more quietly and does not withdraw unrelated source conclusions.

`no coverage yet`, `read succeeded with zero events`, and `unavailable` remain distinct user states.

## 6. Ordinary timeline

Group rows by actual `board_date`: **Today**, **Yesterday**, then explicit earlier dates. Within one day, preserve canonical attention order.

Lead rows are removed from their duplicate position in the lower timeline. Initial Now view shows no more than eight non-lead rows before a counted `See all <N>` / Explore transition.

Ordinary row target: roughly 64–76px desktop. The row is scan-first:

`source · event date` -> **short headline** -> `one meaning/limitation line where lawful` -> `Investigate`

Tier 1 intentionally excludes raw priority score, severity mechanics, validation statistics, repeated methodology, Signal Lab link and full recurrence receipt.

Research-attention translation may use **Review now / Confirm first / Watch closely / For context**. Underlying `act/watch/context`, severity, source action and canonical score stay intact and visible in the inspector where useful.

Unknown-time rows use `Time not established`/equivalent and never appear under Today or What Matters Now merely because processing time is fresh.

## 7. Explore

Explore is where completeness beats compression.

Required controls:

- search: ticker/subject/change/keyword;
- source;
- topic/facet (`stress`, `regime`, `liquidity`, `rotation`, `single-name`, other) as display taxonomy only;
- research attention/tier facet;
- time window/freshness;
- new vs re-fired where lifecycle truth supports it;
- reset/no-results recovery.

Default ordering may expose canonical attention order. A Latest sort may be offered as a clearly presentation-only alternative if implementation preserves event-clock honesty.

The complete accessible population must not inherit the old top-60 cap merely because Now is concise. Account-specific watchlist evidence stays excluded from shared expansion.

Same-source exact-subject bundles can appear as **Related observations** inside result detail/inspector. Do not give them a stronger icon/color/label suggesting independent corroboration.

## 8. History

History shows **actual observed firings**. It is not a state-duration chart.

Each historical row shows source, actual available event/source time, historical headline/detail and a neutral `Open firing` action. A selected historical firing opens the inspector with that firing's original facts/clocks.

If the published history is capped, show an explicit receipt such as `Showing latest 1,000 of 1,252 recorded firings`; never imply older source records do not exist.

A deep-linked firing no longer present due to cap/window/correction renders an honest missing-selection state. Today's latest observation is not silently substituted for the missing historical one.

## 9. Evidence inspector

Desktop: right-side sheet/dialog about 520–600px. Mobile: full-screen sheet. Closing restores exact tab/filter/scroll state and visible keyboard focus.

Order:

1. **What changed** — source-grounded plain description.
2. **Why it matters** — source/deterministic explanation if available.
3. **Original evidence** — source, event time/date, source-as-of, processing clock as distinct fields where present, source deep link.
4. **Current read** — only for sources with an accepted independent current-state contract; otherwise omit.
5. **Context** — regime/cross-asset/catalyst facts with basis.
6. **Why this ranked here** — underlying tier, post-governance severity, existing priority components and validation/null/NO-GO receipt translated to plain language.
7. **Observed history** — actual firings and correction information; recurrence never becomes persistence by wording.
8. **Investigate further** — exact source-owned dashboard/evidence destination.

Optional AI explanation is downstream enhancement only. The page and inspector must remain useful if model synthesis is unavailable.

## 10. Copy and design law

Apply `docs/DESIGN_DOCTRINE.md` and `MASTER_PRODUCT_DESIGN_SYSTEM_V1.md` directly.

Tier 1: plain words, short copy, no raw machine slugs, no unexplained percentiles/z-scores/IC/FDR, and no paragraph-sized caveats. Meaning is visible; receipt/mechanics move to LENS/inspector/study depth.

Use existing Mastermind components/tokens where applicable: PageShell/PageHeader, `.mx-sec`, `.mx-chg-row`, `.mx-tabset`, `.dtp`, `.mx-empty`, `.mx-callout`, `.mx-disc`, `.gbtn`, LENS, shared monoline icons, `.panel/.panel2/.card`. Do not invent a parallel card/token system merely to make Alert Center look special.

Dark treatment: graphite/navy institutional depth, low-chroma surfaces, restrained brand-accent selection. Light treatment: cool paper canvas, white structured surfaces, hairlines and shadow — not a palette-inverted dark glass page. Hue remains semantic, not decoration. Emoji are not UI icons.

## 11. Responsive law

### Desktop 1440×900

With three lead observations, the fold must contain page/session identity, all lead observations and at least three ordinary timeline rows.

No permanent 1/3 command rail. Wide space increases line comfort rather than creating another dashboard.

### Mobile 390×844/900

Timeline owns the screen. First meaningful item appears immediately after compact header/tabs; first ordinary non-lead row is reachable within the first swipe even when leads exist. No horizontal page scroll.

Tabs become a horizontally scrollable tab strip if needed, not an accordion. Context collapses to one compact line/sheet. Inspector becomes full-screen.

## 12. Explicit demotions from current `alerts.html`

- `RISK-OFF/MIXED/...` giant hero -> context/methodology only when coverage permits;
- 0–100 pressure gauge -> inspector/context receipt, not page identity;
- Act/Watch/Live/Re-fired scoreboard -> derived counts only where task-relevant;
- five storyline cards -> Explore facets only;
- giant priority numerals -> inspector `Why ranked`;
- repeated severity/validation chips -> one restrained research-attention cue + inspector;
- recurrence badges -> subtle row note/history receipt;
- per-row Signal Lab link -> inspector validation section;
- tooltip forest -> one sanctioned help/receipt entry per section where needed;
- 60 equal-weight cards -> 0–3 lead + <=8 Now rows; full population in Explore.

These are demotions, not deletions of evidence.

## 13. Do-not-depict-as-live boundary

The v1 Macro Figma must **not** imply these exist in shared Alert Center unless separately proven before design acceptance:

- customer Prophet opportunity/state feed;
- private holdings/watchlist/thesis relevance;
- personal read/archive/unread state;
- quiet hours/email preferences/delivery status;
- natural-language monitor creation;
- cross-domain `Situation` intelligence;
- news event promotion based on headline sentiment or publisher count;
- model-originated ranking or market-event identity.

Future source adapters extend existing owners. They do not justify speculative controls in the v1 ship mockup.

## 14. Figma acceptance matrix

The Macro design is not accepted until the same coherent system covers:

1. complete coverage + 1–3 lead observations;
2. complete coverage + no lead-worthy observation but ordinary timeline rows;
3. genuine no-observation window;
4. blocking partial coverage;
5. nonblocking unavailable source;
6. unknown event time;
7. first firing vs fresh re-fire;
8. Explore populated/search/filter;
9. Explore no-results/reset;
10. History populated + cap disclosure;
11. selected historical firing;
12. missing/corrected/deep-link-outside-snapshot selection;
13. JS/interactive evidence failure with source links still usable;
14. dark + light, EN + ZH, desktop + 390px;
15. long-copy stress;
16. keyboard focus, Escape/close/focus restoration and reduced-motion intent.

Prototype flows required:

- **Flow A:** Now lead -> inspector -> source evidence -> return to exact Now position.
- **Flow B:** Now ordinary row -> inspector -> observed history -> selected firing -> return.
- **Flow C:** Explore -> filter/search -> select -> inspector -> close with filters intact -> reset.
- **Flow D:** History -> historical firing -> original evidence -> current-read section only when supported.
- **Flow E:** blocking coverage -> available changes without false whole-market summary.

## 15. Figma target and no-confusion law

Create a clearly separate design target named **`MastermindX — Macro Alert Center — Market Changes Desk`**. Do not rename or overwrite the preserved Terminal files:

- `wvVt4GTPGMqnaPprVnbloU` remains the Terminal-oriented connected-journey prototype/reference asset;
- `EQlAQXIOdRdO63nMX2RK3u` remains its reference/earlier ship-design asset.

Preferred Figma page structure for the new Macro target:

- `00 — Foundations + Design Law`
- `01 — Components`
- `02 — Now`
- `03 — Explore`
- `04 — History`
- `05 — Evidence Inspector`
- `06 — Mobile`
- `07 — States · Light · ZH`
- `08 — Prototype + Handoff`

If the connected Figma tool cannot create a new file but can only edit an existing project file, stop at that actual tool boundary rather than silently repurposing the Terminal file; use a clearly named separate page only after explicit reconciliation.

## 16. Implementation boundary after design acceptance

Figma acceptance does not authorize a rewrite. Implementation extends current owners:

- `engine.alert_triage.build_triage` stays the sole shared assembler;
- existing alert IDs, canonical score/order, tier/severity governance, clocks, coverage and push behavior remain unchanged;
- port/reconcile #7022's pure uncapped explorer, history, URL-state and inspector ideas onto current main where they still fit;
- add at most a pure presentation projection for What Matters Now/timeline grouping;
- no new database, event identity, alert score, queue, scheduler or private notification plane;
- acceptance requires real assembler -> real renderer -> browser proof using production-shaped inputs in dark/light × EN/ZH × desktop/mobile plus the negative-state matrix.

## 17. Completion state and exact next action

**Experience architecture:** accepted for Figma. **Macro visual design:** NOT_BUILT. **Macro implementation:** current live page remains the existing product; the redesign is SPEC_ONLY. **Production proof:** not applicable yet.

Exact next action: in Pro/Figma-capable mode, create/reconcile the dedicated Macro Figma target and execute the page structure above, starting with `Now` complete/quiet/partial states and the inspector before Explore/History. Preserve the Terminal prototype untouched. Stop only at a real Figma file-creation/access boundary or a material source-law contradiction.