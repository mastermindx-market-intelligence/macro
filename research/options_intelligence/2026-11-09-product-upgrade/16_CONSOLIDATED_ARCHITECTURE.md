# Consolidated Options, Off-Exchange and Market Structure architecture

## Decision status and scope

**Architecture amendment C1 · 10 November 2026 · planning and design, not installation or release acceptance.**

This amendment integrates the Chairman's new Macro consolidation instruction into the recovered Options programme. The programme remains Terminal #599, with #603 the workbench/Lab carrier. It extends the five user jobs and six destinations in 05_IMPLEMENTATION_MASTERPLAN.md and the preserved original October 21 contracts. It does not replace the 104 OPT tasks, 130 OPR requirements or 294 earlier reference rows. Those 528 rows overlap; they are not 528 independent tests.

The decision is to keep the useful analytical capabilities of Macro options.html, market_structure.html and darkpool.html, integrate them into the Terminal/Shared Shell experience, and retire their duplicate page presentation after replacement proof. The prior four options aliases are included. The rest of Macro, including unrelated Stage/Allocation/Policy designs and intraday_flow.html's separate mission, is outside this retirement scope.

The completed design amendment adds nine editable boards to the existing Terminal Paper file. The 49 recovered Round 6 boards remain unchanged. All 58 have a fresh JSX snapshot; the nine new boards also have inspected native screenshots. These are design evidence with synthetic data, not deployed behavior.

## 1. Product rulings

| Decision | Ruling | Reason and boundary |
|---|---|---|
| Product home | One Options suite inside Terminal; Shared Shell provides direct Market Structure and Off-Exchange entry points | Market-wide and equity research must remain useful without selecting an options contract |
| Navigation | Six Options destinations under the six global Shell jobs | Global Today/Discover/Analysis/Monitor/Research/Portfolio remain distinct from workspace navigation |
| Off-exchange identity | Name the workspace **Off-Exchange & Dark Pool**; classify it as equity activity | Familiar search language remains, while daily participation, weekly venues and live prints retain precise meanings |
| Market Structure | A market-wide view shared by Exposure and a direct Analysis entry | It is distinct from chart price-action structure and the existing Options structure view |
| Analytical ownership | Reuse current producers, source/API adapters, chart engines, Investigation, Plan, alert and outcome owners | No new ingestion, classifier, identity, persistence, queue or trading plane |
| Macro retirement | Retire UI routes/rendering only after parity, rights, compatibility and rollback proof | Shared data builders, forward ledgers, historical artifacts and other consumers continue |
| Evidence clocks | Preserve observation, reporting period, first availability, publication/revision and current read time independently | A current page must not restamp an older source as current |
| Scientific claims | Observations, model estimates, research candidates, forecasts and actual execution outcomes remain separate | Bringing two panels together does not validate a combined prediction |
| Commercial policy | Preserve existing effective access; do not create a new upsell between settled and live surfaces | Current Essential and Pro bundles include both site_full and terminal_live_options, but their enforcement paths and service states still differ |
| Scope | Retain original specialist depth and full decision-to-outcome acceptance | A read-only migration is a useful slice, not OPT-100 or OPT-103 completion |

The older One Door decision said that Terminal and Macro would complement each other and remain separate destinations. This commission explicitly supersedes that placement decision. Its useful requirements—distinct clocks, uncapped browse, preserved long-tail ticker search, exact filters, source qualifications and alias compatibility—continue.

## 2. Information architecture and exact preservation

### Global and local navigation

Shared Shell owns global jobs, account identity, directory/search, theme/locale, admitted routes, history and shared layout. Options owns its analytical workspace. Labels in directory results and breadcrumbs use **Options research** and **Options plans & review** when necessary to distinguish them from global Research and Monitor.

| Options destination | Existing view keys retained | New or consolidated content |
|---|---|---|
| Overview | desk | Dated daily brief, material observed changes, independently dated participation/market context, retained work |
| Flow | tape, tide, zero_dte, largest, surface, screener, tickers | Settled Flow presets, full scanner, sector/theme premium, daily off-exchange entry, delayed venue reports and qualified TP5 live views |
| Exposure | gex, positioning, levels, structure | Exact per-name and per-book exposure; market-wide modeled structure as a separately typed view |
| Volatility | volatility | Smile, term, skew, actual tenor, expected move, realized risk, correlation/dispersion and VIX context |
| Research | statistics, prophet | Opportunities and dossiers, all retained Lab lenses, Statistics, family maturity, Macro/Options/Issue lanes |
| Plans & review | Existing Plan and Investigation identities, not a replacement save store | Draft, price–IV–time comparison, expiry payoff, Saved, Watching, selected firing, Review and outcomes |

All fifteen keys remain addressable. The current default /options→Tape is preserved. The accepted aliases remain: 0dte→zero_dte, vol/screener→Screener, prism→GEX, plus the existing leaders/radar→Discover and fundamentals→Analysis redirects. Flow Surface does not become a volatility-surface screen through a rename.

The new six-group presentation is a **versioned Options/F01 consumer amendment**. The current F01 source contract explicitly preserves the older seven categories; its candidate.4 is operative and candidate.5 remains proposed. This document does not pretend the six-group design is already adopted F01 parity. Implementation must amend the affected F01/Options contract and qualify the actual geometry and accessibility changes while preserving unrelated F01 policy and holds.

### Direct routes

The proposed native receiver paths are **/off-exchange** and **/market-structure**. Neither appears in the inspected current native-path inventory. They are planned additions through the existing canonical page registry and exporter, not installed routes or handwritten additions to generated JSON.

Each direct route mounts the same domain module and existing data/selection owners used by the Options entry. A direct visitor sees the Analysis breadcrumb and domain navigation. An Options visitor can open the equivalent context from Flow or Exposure and return to the exact origin. No contract selection is required for an equity or market-wide view. Access to an optional Options cross-link is evaluated independently.

Route admission remains with Macro's canonical page registry and scripts/export_shared_shell_routes.py. The current identities terminal:options, macro:options, macro:darkpool and macro:market_structure remain accounted for until the installed compatibility receiver works. LegacyPageHost remains for unrelated Macro pages.

### Source-selected identity

The existing ShellContext carries theme, locale and contextRevision. It is not a universal symbol/expiry cursor. Shell search may resolve an instrument and offer a destination; the destination's existing decoder commits the selection. Options retains root/contract/expiry/source selection; Off-Exchange retains equity identity, feed class and reporting period; Market Structure retains market/index and model session. Saved evidence never follows an ambient current-symbol change.

A US ticker label is not a complete global instrument identity. Unsupported listings, currencies, adjusted option terms, unqualified expiries or absent source sessions produce explicit states. They never fall back to an old SPY selection under a new heading.

## 3. Disposition of the Macro estate

The detailed feature register is 17_MACRO_FEATURE_DISPOSITION.csv. These are the governing decisions.

### Options donor

Keep the useful daily brief, indexes, source health, sector premium, theme groups, sector ETF context, Tide, scanner, full ticker browse, Leaders, net OI change, strike/expiry structure, positioning Greeks, volatility term/smile and expected-move context. Integrate them into the corresponding existing domain, preserving full populations and exact controls.

The ETF-share-change flow estimate is a different measure from options premium turnover; keep its source, unit and estimation method. Call/put premium is not net investor inflow. A net OI change does not identify which contracts were opened or closed by a particular trade. Largest reported activity is not automatically a directional “bet.”

Preserve the previous accepted long-tail decision: a smaller qualified scanner universe can coexist with a larger ticker manifest. Do not invent full scanner coverage by counting mostly-null ticker entries. Every excluded name has a truthful unsupported/not-screened state.

Retire duplicate Macro page chrome, redundant intensity gauges, redundant per-name boards and obsolete “go to the other product” CTAs. Retain the actual underlying capability in one place. Reassess narrative “rich/cheap,” confidence, tactical or recurrent-money labels against their exact claim contracts before importing them.

### Dark Pool donor

Keep daily off-exchange participation, eligible share counts, matched own-history baselines, coverage, missing sessions, price conjunctions, short-marking composition, sector composition, full browse/filter/sort/export and per-name history.

Daily off-exchange activity, weekly ATS/non-ATS reports and live print/cluster data are three source families. A weekly report is not a live venue identifier; an aggregate cannot produce a trade timestamp, print ID, signed trade, shelf or NBBO association. Existing Terminal #655/TP5 owns the admitted live/history/overlay path.

The P0 semantic repair is explicit. At Terminal abd68886, eodContext.ts still derives accumulation/distribution from off-exchange share and short-marking changes, and DarkPoolMini renders the result. Macro darkpool_context.v2 explicitly retired that construction. The norm-band thresholds also differ. This is a verified source divergence, not a verified deployed incident.

Remove the duplicate client directional rule and bind a versioned canonical observation contract. Do not simply adopt an old lean field or copy all v2 narrative strings. Some current prose still describes trades as away from the public tape or implies large-order intent without print evidence. Use reported off-exchange participation, measured price conjunctions, documented population/baseline and neutral language. Short-sale volume is not short interest, beneficial-owner identity, institutional buying or net selling.

### Market Structure donor

Keep modeled gamma/regime history, dated spot and modeled flip, systematic flow estimates, switch levels, correlation/dispersion, realized/implied volatility, VIX curve, locked weekly range and exact historical tables/exports.

Keep these dimensions separate. A composite tactical score, actual dealer inventory or actual fund flow is not created by placing their cards together. The gamma method must specify sign/inventory assumptions and units. The existing “positive gamma means they sold options” explanation needs correction. Modeled walls/flip are not guaranteed support, resistance or price magnets.

Weekly range carries lock time, validity interval, first availability, method and missing/expired states. Model ±1σ/±2σ bands do not inherit empirical 68%/95% coverage without an explicit distributional assumption and calibration evidence. A prior week's lock remains historical after expiry.

### What is archived

After acceptance, archive immutable copies of the three page templates/render outputs, replaced navigation entries, migration source maps, donor screenshots/JSX, redirect configuration and rollback receipts in their existing repository/design homes. Keep the admitted compatibility receivers and redirects active for supported historical URLs. Removing one later requires its own use/consumer evidence and explicit disposition. Mark old Paper pages as historical references with links to the adopted replacement; do not delete unrelated boards or the recovered 49.

**Do not archive or stop a shared producer merely because its HTML page is retired.** Confirmed continuing consumers include Terminal's EOD context and Macro's Neural Web/world-state projections. Market Structure latest/history and the nightly-only forward ledger have distinct roles. The consumer audit must include internal jobs, APIs/R2 mirrors, historical readers, source retention, exports and research ledgers.

## 4. Architecture and ownership boundaries

| Layer | Existing owner to reuse | Consolidation work |
|---|---|---|
| Acquisition/publication | FINRA, options/chain, Cboe/Yahoo, context and weekly-range producers | Add narrowly required fields or versioned observations; preserve original publication and forward-ledger rules |
| Source adapters | Existing Flow/API/R2 and EOD/TP2 decoders | Normalize discriminated source families, retain original identities and exact revision/rights |
| Domain models | Current Flow, exposure, volatility, market-context and TP5 owners | Eliminate duplicated heuristics; keep method and scope explicit |
| Shell | AppShell, route registry/exporter, shared navigation, history and access | Admit direct receivers and amend six-group IA; no parallel account, registry or cursor |
| Presentation | Existing domain components and shared table/chart/inspector primitives | Recompose donor capabilities and responsive states; one canonical implementation per domain |
| Research continuity | Investigation, source retention, Plan #804, canonical Analysis reader | Attach typed exact evidence; explicit New research/Add/Save; no automatic persistence |
| Monitoring/outcomes | Existing selected-node alert/evaluator/outbox and outcome owners | Preserve preview/Arm, selected firing, exact review revision and separate outcome types |
| Qualification | Existing trial ledger, G0–G6 and family consumer verdicts | Display maturity and limits; qualify stronger use under original rules |

An adapter is a boundary translation, not a new semantic authority. When an existing wire lacks a field, return an explicit unsupported capability until its producer supplies it. Local UI defaults must not manufacture freshness, precision, venue membership, historical availability or claim eligibility.

Backend fields and user actions are bound in 18_CONSOLIDATION_SOURCE_AND_INTERACTION_CONTRACTS.md. The implementation commission and original conditional rules are bound in 19 and 20.

## 5. Access, caching and account lifetime

Current Macro policy declares premium required_feature=site_full; current Essential and Pro products include site_full and terminal_live_options. The current native /options route calls getLiveOptionsAccessDetail and gates terminal_live_options. Macro also has staged versus early-enforced payload rules. Registry payloadTier is descriptive, not authorization.

The new direct routes must preserve the existing source-specific effective access policy, including public preview versus private payload, registration/trial/paid state and service unavailability. The same rule applies to the old Macro Options brief/scanner/ticker migration: the current whole-page live-options gate on /options must be composed into source/view capability checks through the existing entitlement owner. A thin server composition obtains the existing policy decisions; it does not infer a grant from a plan name or create an auth service. The default Tape entry retains its live gate; an explicitly selected settled brief/view uses its existing effective Macro policy. Public preview markup contains no protected payload. Do not weaken an API because a legacy page shell was visible.

Qualify four capability combinations—settled only, live only, both and neither—plus one unavailable policy read beside one confirmed grant. The UI mounts and fetches only the admitted source modules; a hidden keep-alive pane cannot retain or refresh protected values after revocation. This route-gate composition is required before retiring options.html, not an optional polish task. Current paid bundles include both features, but custom grants, registration/trial states and staged enforcement must still behave correctly.

Reuse server-resolved AccountIdentity/userId, current entitlement services, provider rights, source-use/retention rules and no-store/private response conventions. All reads, exports, saving and callbacks are bound to the current account lifetime. Account A→B→A cannot reuse an earlier A callback or protected response. Denied, expired and unavailable remain distinct. A rights change can make a retained reference unreadable without erasing its identity or inventing its values.

No new billing product, spend, provider subscription, activation or brokerage authority is granted by this masterplan.

## 6. Complete journeys and release slices

The original five jobs remain Market Brief, Opportunities, Workbench, Trade Lab and Monitor.

1. **Original observational precursor:** qualified natural aggregate Flow → independently qualified dated Gamma → exact original context. This named Gamma receiver/return proof remains mandatory for that slice. Additional Flow→participation and Flow→market-context journeys are independently accepted consolidation slices; neither substitutes for the original Gamma receipt. These read-only journeys can be useful before Plan or scientific promotion is ready.
2. **Settled consolidation:** direct Shell/legacy entry → complete daily/weekly/model browse → exact source inspection → native research continuity where admitted → qualified exports and exact return.
3. **First complete vertical:** Brief → at least two supported opportunity dossiers plus no-trade → stock/long-option/defined-risk-vertical/wait comparison → qualified pre-expiry price–IV–time results and separately labeled expiry payoff → native Save → selected-node watch → Monitor → source-linked outcome review → frozen usefulness verdict.
4. **Advanced scope:** all original Statistics, Prophet families, Lab lenses, R2 scanner/quad/replay/session review, lifecycle, Futures/Equity origin-return, structures and portfolio obligations remain explicitly assigned. Unsupported domains are not silently removed.
5. **Retirement:** replacement proof plus all scoped legacy entries/consumers, canary and rollback. This does not wait for unrelated empirical success; it does wait for the actual capabilities being retired.

OPT-100 retains 15 direct and 36 transitive unconditional prerequisites. OPT-079 makes OPT-015 exact-expression publication/integrity part of that first vertical even if a separate OPT-064 quote-ruler condition does not select OA-3. Two alternative option expressions of one observation are not automatically the two opportunities required by OPR-110.

The original Plan bridge supports New research → Add detached whole Plan → Save → new case revision 1. Existing-case revision-2 Plan attachment requires a separately qualified extension. Ordinary price watches or saved-case assessments do not substitute for selected-node OPT-035 or the original outcome journal.

## 7. Responsive and interaction contract

Preserve F01 candidate.4 geometry: 224px expanded navigation at ≥1200; 196px above 860 and below 1200; explicit 72px compact; one drawer at ≤860. Header is 64px above 860 and 56px at ≤860, including the exact boundary. Content gutters are 16/20/24 by the existing thresholds and applied once.

A shared 320px dock plus 24px gap is allowed only when the remaining primary content is at least 640px or the domain's larger qualified minimum. At 1440 the shown main stage is 824px. At narrower widths use the qualified modal/full-width evidence behavior; do not auto-collapse navigation to force a table to fit. Focused Terminal's D06 reader is a separate exception and keeps its existing owner/preference.

One evidence inspector, one modal, one body-scroll owner. Nested Escape, IME, focus recovery and history preserve the current domain identity. The proposed candidate.5 resize policy is not silently adopted. Important controls are at least 44px; phone rows at least 48px. Exact tables and exports remain available when a chart is unsuitable. Theme, EN/ZH, 200% zoom, 1280/820/390 and wide 1920 readability remain implementation acceptance obligations.

## 8. Evidence cut and current holds

| Source | Exact inspected reference |
|---|---|
| Governing Mastermind law | 76cca6bf0d4f54c1c4a732726a16c70dbe8ed679 |
| Existing planning carrier | Macro PR10898; recovered at a576fbba8b6562884b03cec7d78699e953dbbe2c; recovery commit 554e809c62da95e96dcfbbd3bd9a990b4f0f053b |
| Current Terminal domain source | abd68886b86713b2b0ac7f5a50fe7c0417a26662 |
| Current Macro domain/access source | 7e115b6f1f10832b4b123149215ea7a041279753 |
| F01 candidate contracts | dce261d07ebc993e8a9579cca2200e445b6636d4 |
| Terminal Plan PR804 | 27df56d997df0ae94a17b6b8e2d14867431bb394; Draft, release hold5989604142 |
| Macro retained-selection PR10866 | f9d9c1883b9a25ea2bd5f6b5b21f922a01307434; open; original controller/current-base/release conditions retained |
| F01 Terminal PR1276 | d02a49631724a6ef48ce507914396921d218ad03; Draft, scoped release hold retained |
| TP5 Terminal PR966 | 602c75721766945bd198c4f4320fe9d6a1742397; merged decoder source, not mounted/live consumer acceptance |
| TP2 Macro PR8859 | 7dad247d85c5fcd0e1e1ed3a74746f0a7b10f52f; Draft source-free ruler; live/named-venue capabilities remain unproved |

Do not rerun accepted recovery, original checksum validation or unchanged exact-head evidence. Re-read affected current facts at implementation admission; task titles are not permission to redo accepted work. Preserve T03k/P09 and original F01/F02/D08D effects on their original carriers. The new Paper page uses disjoint owned nodes; one response-parsing loss was reconciled by an exact unchanged original-subtree comparison before a fresh guarded same-carrier attempt. All nine new boards now have observed effects and exports.

## Sources

- [Original programme and release contract](11_RELEASE_AND_DESIGN_CONTRACT.md), [implementation baseline](05_IMPLEMENTATION_MASTERPLAN.md), [recovery](14_ROUND6_RECOVERY_AND_CONSOLIDATION_SCOPE.md).
- [Prior One Door ruling](https://github.com/mastermindx-market-intelligence/macro/blob/8f12b4e2a16068cf280d6cbfd33c735b56233dd3/research/options_estate/ONE_DOOR_RULING_AND_SPEC.md).
- [Current Options IA](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/abd68886b86713b2b0ac7f5a50fe7c0417a26662/terminal/lib/optionsIa.ts), [EOD context model](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/abd68886b86713b2b0ac7f5a50fe7c0417a26662/terminal/lib/eodContext.ts).
- [Canonical dark-pool context](https://github.com/mastermindx-market-intelligence/macro/blob/7e115b6f1f10832b4b123149215ea7a041279753/engine/darkpool_context.py), [Market Structure builder](https://github.com/mastermindx-market-intelligence/macro/blob/7e115b6f1f10832b4b123149215ea7a041279753/scripts/build_market_structure.py).
- [Current Macro access policy](https://github.com/mastermindx-market-intelligence/macro/blob/7e115b6f1f10832b4b123149215ea7a041279753/config/site_access.yml), [plan feature bundles](https://github.com/mastermindx-market-intelligence/macro/blob/7e115b6f1f10832b4b123149215ea7a041279753/config/plans.yml).
- [F01 source contract](https://github.com/mastermindx-market-intelligence/macro/blob/dce261d07ebc993e8a9579cca2200e445b6636d4/research/design_candidates/production_design_20261102/f01/SOURCE_AND_DATA_CONTRACT.md), [joint geometry/ownership contract](https://github.com/mastermindx-market-intelligence/macro/blob/dce261d07ebc993e8a9579cca2200e445b6636d4/research/design_candidates/production_design_20261102/f01/JOINT_SHELL_SYSTEM_CONTRACT.md).
- [FINRA: off-exchange reporting](https://syndication.finra.org/content/look-over-counter-equities-trading), [FINRA short-sale volume notice](https://www.finra.org/sites/default/files/2019-07/information-notice-051019.pdf).

