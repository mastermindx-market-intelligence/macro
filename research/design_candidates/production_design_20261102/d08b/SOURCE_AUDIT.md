> Publication note: root independently verified the exact Macro field is `summary.rr_25d` from `risk_reversal_25d`, versus `summary.skew.rr25` from `risk_reversal`. The earlier auditor shorthand `rr25d` below refers to that underscored key. The appended supplement supersedes earlier consumer/geometry gaps; upstream producer limits remain.

# D08B source semantic audit — read-only advisory

Status: bounded source audit complete; native advisory, not admitted independent RIG review or formal GitHub approval. No product, Paper, repository, branch, PR state or external communication was modified by this auditor. No source reads beyond the already acquired evidence were needed for closeout.

## Evidence pins

| Owner | Immutable evidence |
|---|---|
| Protected law, inherited verified compatible pin | `Mastermind@910803421beca53ca25145392725ab2d84c7a8e9` |
| Assignment | `macro@6e1862867193ec6486a22001a0e4fb515da20448`, `research/design_candidates/production_design_20261102/handoffs/D08B-options-exposure-volatility.md` |
| Frozen D08 interface | `macro@d0516e1bad9cb5982d43d20c4167d0355cb70e2c`, `research/design_candidates/production_design_20261102/d08/{README.md,SLICE_INTERFACES.json,SOURCE_MAP.md}` |
| Terminal source resolved once | `mastermind-terminal@2ded360882b9c721e690907ff363b553781fb920` |
| Macro producer source resolved once | `macro@df691495abb1c2ba8f61e5624126cb17ad14e056` |

All repository references below use `https://github.com/mastermindx-market-intelligence/` followed by repository, `/blob/`, immutable SHA and path.

## 1. Decisive source findings

### Current Exposure 3D is a qualified cell projection

Source: [ExposureSurface.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2ded360882b9c721e690907ff363b553781fb920/terminal/components/exposure-map/ExposureSurface.tsx), [exposureSurface.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2ded360882b9c721e690907ff363b553781fb920/terminal/lib/exposureSurface.ts), [exposureMapProjection.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2ded360882b9c721e690907ff363b553781fb920/terminal/lib/exposureMapProjection.ts).

- It draws isometric strike × expiry columns from a qualified projection. Heights are the cells' own gamma values, without smoothing. This implementation must not be described as an interpolated IV surface.
- `SURFACE_VERSION = "exposure-surface/v1"`; `SurfaceMode` is `net | gross | abs`. Finite gamma net/gross values are converted from dollars to millions with `/ 1e6`; null stays unavailable, never zero. The existing 3D mode does not establish a Vanna or Charm surface capability.
- Windows are 2%, 4%, 8% around reference spot; expiry caps 5, 9, 15; elevations 20, 30, 45, 60 degrees. These are visible analytical controls worth preserving under progressive disclosure on phone.
- Tier thresholds `[.7,.45,.25,.12,.04]` use the whole selected lens's maximum absolute net gamma before strike-window or expiry-cap cropping. Cropping must not recolor the same retained node into a different analytical tier.
- DTE is the difference between ISO expiry and the projection's `source_session`, not the browser's current day.
- Cells retain `strike`, ISO `expiry`, `economic_expiry_at`, `population_id`, and `joint.complete`. They are aggregates. A selected cell does not establish one exact contract with right, adjusted root, or unique series identity.
- Current/prior cell change is admitted only when `expiry|strike` matches, `population_id` matches, and both net values are finite. This narrow cell comparison is distinct from the more comprehensive matched-vintage comparator below.
- Strike and expiry totals use the full selected lens; if any required member is null, the total remains null. A cropped window must label full-lens totals rather than imply they total only displayed bars.
- `source_snapshot_ref` and `clocks.source_session` are preserved. `modeled_exposure` maps to the UI identity `provider_observed`; this label does not prove observed dealer positions. The design should expose the actual provider/model identity and assumption separately.

### A useful 2D alternative can use the identical projection

Source: [ExposureMap.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2ded360882b9c721e690907ff363b553781fb920/terminal/components/exposure-map/ExposureMap.tsx), [exposureMap.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2ded360882b9c721e690907ff363b553781fb920/terminal/lib/exposureMap.ts).

Existing controls already expose Compare Expiries, Changes, Replay, Review, Scenario, Surface and Exact Values. The expiry matrix uses ISO expiry keys, row/column buttons, selected-state semantics, signs and explicit unavailable cells; missing cells are not zero. Preserve these controls and use one selection/lens/source state for both 3D and accessible 2D.

Proposed acceptance requirement: a keyboard-operable table/heatmap with net/gross/absolute mode, the same window/cap, fixed tier normalization, exact selected coordinates, source/session, known/expected coverage and inspector must reproduce every numeric value in 3D. The table may reflow/paginate on phone, but changing representation must retain selection. This is a feasible design requirement grounded in the existing projection, not a claim that every proposed keyboard/export behavior is implemented today.

Reader states already distinguish `data`, `unavailable`, `wrong_root`, `future`, `malformed`; qualification distinguishes `legacy`, `qualified`, `dated`, `unqualified`. `coverage.expected` can be null. Known rendered grid positions and source collection coverage are different denominators.

### Reported change is not flow

Source: [exposureReportedChange.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2ded360882b9c721e690907ff363b553781fb920/terminal/lib/exposureReportedChange.ts).

The comparator accepts same identity/security/root, scope and definition; requires strictly advancing source sessions; and requires each source session and `availableAt` to be no later than the evaluation cutoff. It compares the globally matched member cohort whose values are finite in both vintages. Member keys are expiry, strike and right.

It returns matched-cohort signed net change, net magnitude change and gross change. Net magnitude change uses the absolute aggregate net; it is not the sum of strike-level absolute changes. Previous-only/current-only reported members and qualification lost/gained are separate counts. A reported set addition/deletion is not proof of economic entry/exit. Empty finite intersection is unavailable, not a zero change. `velocity` and `percentChange` are explicitly null. No flow, economic-terms, percentage or velocity inference should be introduced by visual copy.

### Volatility has explicit EOD and unit contracts

Source: [volTypes.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2ded360882b9c721e690907ff363b553781fb920/terminal/components/vol/volTypes.ts), [VolView.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2ded360882b9c721e690907ff363b553781fb920/terminal/components/vol/VolView.tsx).

`options_hub.vol/v1` is served by `/api/flow?f=vol:{ROOT}`, produced to `options_hub/vol/{ROOT}.json`. Its contract says NIGHTLY EOD, never live chrome. IV/RV values are percentage numbers, e.g. 58.2 means 58.2%; ranks use 0–100. `vrp` is the upstream-published `atm_iv - rv20`, displayed verbatim. Term rows retain `dte`, `exp`, `atm_iv`; smile retains exact `exp`, strike, nullable call/put IV. Source comments identify deep-ITM IV artifacts and nullable history rank/close, so trimming/default display must remain visible and unavailable fields must not be interpolated into observations.

Primary `vol:root` is independent of optional aggregate/moves panels; optional panel failure should not erase the verified main snapshot. Current source has a three-session stale threshold and no continuous live polling. A proposed source clock must describe this cadence truthfully.

### Macro GEX is a model under assumptions

Source: [gex_engine.py](https://github.com/mastermindx-market-intelligence/macro/blob/df691495abb1c2ba8f61e5624126cb17ad14e056/engine/gex_engine.py), [gex_model.py](https://github.com/mastermindx-market-intelligence/macro/blob/df691495abb1c2ba8f61e5624126cb17ad14e056/engine/gex_model.py), [build_gex_board.py](https://github.com/mastermindx-market-intelligence/macro/blob/df691495abb1c2ba8f61e5624126cb17ad14e056/scripts/build_gex_board.py).

- Core assumed dealer gamma uses call-positive/put-negative signs and dollar gamma magnitude `gamma × OI × multiplier × spot² × pct_move`; default multiplier 100 and pct_move .01. This is a dealer-convention model, not observed dealer inventory or trade flow.
- The engine reprices a European Black–Scholes curve under supplied rate/yield; regime is the sign of the same repriced curve at actual spot. Gamma flip is the nearest sampled crossing, not a forecast. No crossing yields null flip, not an invented spot-level crossing. Flip distance uses `100 × (spot - flip) / spot`.
- The display profile and engine have different ranges/sample counts: model display ±15%/81 points; engine ±25%/101 points. Do not promise exact interchangeability of displayed curve and scalar without method/parameter evidence.
- Summary `rr25d` computes `(call_IV - put_IV) × 100`; separate `risk_reversal` output `rr25` computes `(put_IV - call_IV) × 100`. Expiry selection/fallbacks differ too. This is a decisive field-name/sign collision: keep method ID, expiry and subtraction order explicit.
- Macro `iv_rank` is a strict percentile over up to 40 retained sessions, requiring at least 5; it is not automatically a 252-day IV range rank. Terminal's `iv_rank_252` is a separate contract.
- Macro surface is strike × expiry net dealer GEX, OI or volume. It uses ±10%, nearest 12 qualifying expiries/top 26 strikes; missing cells are `None`. Its human expiry labels and runtime-date-based day counts cannot establish exact contract identity or as-of DTE. Add ISO source identity to a build contract instead of reverse-parsing labels.
- Macro expected moves are IV-based model bands; strengths/tone labels do not establish calibrated probabilities. Preserve price levels and method context without relabeling them as empirical likelihoods.
- `build_gex_board._session_close_asof` constructs 16:00 ET from session date. That is a compatibility anchor, not observed event time, and does not model early closes. Total source failure can leave old payloads and return exit code zero; successful job exit is not fresh-source evidence.

## 2. Existing integration and ownership

Source: [OptionsWorkspace.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2ded360882b9c721e690907ff363b553781fb920/terminal/components/workspaces/OptionsWorkspace.tsx), [GexDeskView.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2ded360882b9c721e690907ff363b553781fb920/terminal/components/gexdesk/GexDeskView.tsx), [AdmittedOptionsResearchLab.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2ded360882b9c721e690907ff363b553781fb920/terminal/components/researchlab/AdmittedOptionsResearchLab.tsx).

- Preserve Options tab aliases: `gex`, `surface`, `prism→gex`, `structure`, `volatility`, `positioning`, `levels`. `vol` currently aliases screener, not the volatility tab. Legacy PRISM defaults matrix. Explicit valid GEX `view=strike|expiry|matrix|chart` wins. Research uses `research=1`, with legacy `view=research` recognized.
- GEX reads `gex:{root}`, `matrix:{root}`, `gex_dates:{root}`, `gex_at:{root}:{date}` under existing source owners. Greek matrix anchor is `matrix._build_meta.asof_date`, not quote time or GEX session. Root fences, invalid-root rejection, Back/Forward and source-specific failure behavior are retention requirements.
- Current Flow Surface (`components/surface/SurfaceView.tsx`) is strike × session-time field snapshots for net premium/GEX/Vanna/Charm. A shared candle interval does not resample field snapshots. It is not the same object as the qualified strike × expiry 3D projection or the IV smile/term surface.
- Existing 3D Research Lab admission checks matched verified identity and entitlement; do not bypass it when exposing a phone alternative. Lab source copy distinguishes read failure/404/refresh failure and labels pinned coordinates as instrument identity unverified. Saving is disabled because options evidence is not yet admitted to Saved Research.
- D08B passes an aggregate node and source identity to D08C. Only a unique actual qualified contract row supports a C-owned pin. Do not create a second shortlist/payoff/plan owner.
- D08B Exposure archive/replay stays under its existing owner. D08D owns futures/ES/NQ/IEX request, read and replay cursor. Do not append exposure filters to D's closed parser or recast futures as SPY/QQQ.

## 3. Suggested backend/build mapping

### Verified import and reader map

All paths below are relative to Terminal `terminal/` at the immutable Terminal pin above. `components/OptionsHubView.tsx` imports the first five views; the GEX view supplies the exposure and admitted Research Lab paths. These are source-reader keys, not newly proposed endpoints.

| Surface | Actual import | Reads verified in inspected file |
|---|---|---|
| GEX | `components/gexdesk/GexDeskView.tsx` | `gex:{root}`, `matrix:{root}`, `gex_dates:{root}`, `gex_at:{root}:{date}` through current flow owner |
| Flow Surface | `components/surface/SurfaceView.tsx` | `surface_dates:{root}`; delegates field/replay reads to existing child owners, whose complete keys were not audited here |
| Positioning | `components/msc/PositioningView.tsx` | Primary `gex:{root}` and `moves:{root}`; optional `agg:{root}`, `matrix:{root}`, `quad`, `grades:{root}`, `grades_universe` |
| Levels | `components/levels/LevelsView.tsx` | Import verified; internal reads/formulas not inspected and must remain an explicit build gate |
| Volatility | `components/vol/VolView.tsx` | Primary `vol:{root}`; optional `agg:{root}`, `moves:{root}` and `/data/{encodedRoot}.fund.json` |
| Qualified Exposure 3D | `components/exposure-map/ExposureMap.tsx` → `ExposureSurface.tsx` → `lib/exposureSurface.ts` | Existing qualified projection plus dated prior projection; retain source reader rather than introduce another transport |
| Research Lab 3D | `components/researchlab/AdmittedOptionsResearchLab.tsx` → `OptionsResearchLab.tsx` | Identity/entitlement gate verified; inherited matrix source and volatility adaptation; geometry/adapter semantics not fully traced |

### Exact macro gamma unit

`engine/gex_engine.py` lines 293–296 computes `sign = +1` for calls and `-1` for puts, `dg = gamma * oi * mult * spot ** 2`, then `gex = sign * dg * pm`. Defaults are `mult = 100` and `pm = 0.01`, so the ordinary displayed GEX is **US dollars of delta-hedging exposure per 1% underlying move under the assumed dealer sign convention**. More generally the function's unit is dollars per configured `pct_move`. The returned `net_gex_bn = sum(gex) / 1e9` is billions in that unit. This is not a trade-flow measurement. Current macro surface `z_gex` divides by `1e6`; its value is millions under the corresponding GEX convention. The newer Terminal projection has its own declared metric unit and source identity; do not infer its full methodological equivalence solely from the same `/1e6` display conversion.

| User action | Existing owner/input | Required contract/preserved behavior |
|---|---|---|
| Exposure heatmap / exact values / 3D | `exposureMap` reader → `QualifiedProjection` → `exposureSurface` | Same snapshot, lens, ISO coordinates, units, qualification, nulls, fixed tier normalization; one shared selection |
| Inspector / C handoff | Actual member resolver under current source owner | Aggregate flag; exact family/list/session/as-of/schema; C pin withheld without unique actual contract row |
| Prior-session change | `exposureReportedChange` and dated source plane | Identity/definition/scope/cutoff gates; matched cohort; membership and qualification differences separate |
| GEX archive | GEX current/dates/dated keys and existing session owner | Separate quote, source session, build/retrieval clocks; avoid live-book/history mismatch |
| Vol term / smile / compare | `vol:{root}` schema `options_hub.vol/v1` | Percent units; expiry/tenor method; EOD clock; nullable fields; published VRP verbatim |
| Flow Surface | Existing `surface_dates`/replay/surface contracts | Strike×time snapshots, native session boundaries, no implied resampling |
| Scenario | Existing qualified projection/scenario owner | Preserve shock dimensions and joint population qualification; model response labelled scenario, not reported flow |

## 4. Falsifiable acceptance cases

1. Switching 3D to 2D retains root/session/lens/window/cap/mode/selected cell; every finite number and null agrees.
2. Cropping a window leaves retained-cell tiers unchanged; full-lens totals are labelled as such.
3. Missing gamma remains unavailable, not a zero-height/zero-dollar observation; unknown source denominator is not turned into 100% coverage.
4. A selected aggregate with no unique qualified contract cannot create a C pin; all existing filters/context survive returning from C.
5. Same source session, mismatched scope/definition, future availability or empty finite cohort yields unavailable comparison; no signed flow or percentage appears.
6. Qualification lost/gained and additions/deletions are displayed separately from matched net change.
7. RR25 fixtures with call IV 20%, put IV 23% display the relevant method's -3 or +3 vol points correctly and never share an unlabeled universal RR25 value.
8. Archived/dated matrix DTE remains anchored to its source session after browser date changes.
9. An old GEX history point cannot inherit current-session walls/flip labels or current quote freshness without separate source clocks.
10. Vol main data remains usable after optional band failure; current-root loading cannot display an unlabeled prior-root snapshot.
11. Phone controls expose all research settings with keyboard/touch focus restoration; table and inspector remain usable without drag, hover, color, or WebGL.
12. Failed source acquisition leaving cached files is visibly stale/last-verified, regardless of successful job exit.

## 5. Limits and follow-up

This audit did not prove current production backend values or all formula producers behind positioning probability/hedging labels. The separate Research Lab geometry adapter was not fully traced; do not claim every legacy 3D plot is either measured or synthetic. The qualified Exposure Surface implementation above is specifically verified. Complete volatility tenor-comparison internals were not inspected; preserve explicit method/expiry definitions and require build fixtures before claiming identical-tenor comparisons.

Parent supplied bounded live observations: initially mixed loading/last-read chrome later settled; settled matrix showed 228/273 known grid positions and unknown source collection coverage. Initial state must not be generalized into permanent absence. Parent also observed independently dated quote/book/history/context and probability/flow wording; these support targeted acceptance cases, not a universal source-outage or calculation claim.

No changes, deployments, merge/Ready/queue/lifecycle operations or external publication were performed by this audit.

## Supplement — bounded Levels and Research Lab closure

Requested follow-up completed at the same Terminal SHA, `2ded360882b9c721e690907ff363b553781fb920`. Fresh reads were limited to `LevelsView.tsx`, `researchLabAdapter.ts`, `researchVolatility.ts` and `ResearchScene.tsx`; the previously acquired `OptionsResearchLab.tsx` and admission wrapper supplied consumer context. No broader source or producer census was performed. This supplement supersedes the earlier statement that these particular consumer/geometry paths were uninspected; producer definitions beyond them remain unresolved.

### Levels: source, retained features and exact limitations

Source: [LevelsView.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2ded360882b9c721e690907ff363b553781fb920/terminal/components/levels/LevelsView.tsx).

- Actual source is **`/api/flow?f=levels:{ROOT}`**, read via shared `flowGetResult('levels:'+root)`; contract comment names **`levels.v1`**, `engine/levels_engine.py` and fixture `public/data/levels_fixture.json`. These producer/fixture paths are source references in the consumer, not additional audited files.
- Poll interval is 60 seconds; hidden-document polling skips reads and visibility restoration reads again. Root validation uses the existing route rule; sequence fencing prevents a late older read from painting. Root change clears payload and selected node.
- Preserve validated root entry, quick roots, spot marker, vertical price map, named nodes/rail, void ranges, flip marker, confluence stacks, selectable source notes, theme/blue-orange colorblind palette, source convention and ET as-of. Side-rail role order is `anchor`, `call_wall`, `put_wall`, `flip`, `cluster`, `launchpad`, `counter`, `trapdoor`. Repeated clusters retain all column markers but the brightest representative in the rail.
- Strike is projected to the column using the overall price band. Collision avoidance moves readable labels while retaining an exact-price axis tick and leader. Brightness controls visual width/opacity; it is not rendered as a calibrated probability. Preserve the separation between label layout and analytical price.
- Read failure is not absence. First-read failure shows an error/retry; failed refresh keeps the last map with explicit last-read copy. 404/410 or a published object without a root map permits absence. A role is called not present only after a map or source absence is established.
- The contract carries `regime.net_gamma`, `net_gamma_unit`, nullable `label`, ribbon, nullable node strike/weight/sticky/brightness, void bounds, `source_schema`, `source_asof`, `source_convention`. The current UI exposes `payload.asof` and source convention, not every source field.
- **Specific design/build correction:** a non-null regime object with `label:null` is currently rendered Slippery because `isSticky = regime?.label === 'sticky'` and rendering uses a sticky/slippery ternary. The proposed design must retain unknown as unknown. Its as-of stale badge compares ET calendar days, not an exchange-session calendar. Also, local `levelsFor` accepts an object with nodes/root or a root-keyed object without a complete `levels.v1` structural validation; stronger validation belongs at the established owner, not a second reader.
- The consumer's stated dealer sign is assumed, and OI is daily. Upstream level-role formulas, brightness weighting and freshness provenance were not audited in this bounded supplement; they remain explicit build gates.

### Research Lab: actual published geometry, not a fitted surface

Sources: [OptionsResearchLab.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2ded360882b9c721e690907ff363b553781fb920/terminal/components/researchlab/OptionsResearchLab.tsx), [researchLabAdapter.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2ded360882b9c721e690907ff363b553781fb920/terminal/components/researchlab/researchLabAdapter.ts), [ResearchScene.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2ded360882b9c721e690907ff363b553781fb920/terminal/components/researchlab/ResearchScene.tsx), [researchVolatility.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2ded360882b9c721e690907ff363b553781fb920/terminal/components/researchlab/researchVolatility.ts).

- The Lab performs no I/O or new subscription. It receives the incumbent matrix/volatility payloads, read status and retry callbacks. Keep the existing admitted identity/entitlement wrapper.
- Matrix adaptation calls the admitted root validator and source-session reader. Valid cells require positive finite strike and canonical ISO expiry. Duplicate expiry/strike cells are excluded entirely. Call/put volume and OI require finite nonnegative values; ΔOI admits signed finite values. Invalid metrics become null with exclusion counts. The adapter preserves aggregate `c.gex` as `netGexDollars`, but does not pretend it is individual option gamma.
- Row key is `root|expiry|side|strike`: explicitly a source coordinate, not an exchange-qualified instrument ID. `oiSession` and `availableAt` remain null. Parsed `raw.asof` is build time, never substituted for availability. Selection/comparison is reconciled against the full admitted rows; invalid coordinates are removed and a filtered-out valid selection is explicitly indicated.
- Three.js draws an orthographic **point cloud of published volume, OI or ΔOI**, not an estimated continuous surface. Exact encoding is `x = sideSign * abs(value)/fullSnapshotMaximum * 1.6`; `y` is linearly normalized strike; `z` is **ordinal expiry index**, not elapsed days. Calls use positive x and puts negative x solely for separation. Negative ΔOI is hollow; it does not switch to the other side. Marker diameter is square-root-scaled for magnitude, bounded below by 2px and capped by full-snapshot density (12/20/34px).
- The full snapshot fixes scale across filters. Zero and null have no 3D mark but remain distinct in the exact table. Only the first 20,000 nonzero marks in source expiry/strike ordering are drawn; all admitted rows remain in the paginated table. The table is present even in 3D mode. Table mode is the initial choice below 600px; this is source behavior, not browser-verified responsive proof.
- Preserve side/expiry filters, three metrics, exact-value table with 50-row pages, three-item comparison, selection inspector, keyboard arrow selection, reset/front/top camera presets, orbit/zoom, focus restoration and WebGL-failure fallback. Rendering is demand-driven with no animation loop or data requests.
- Volatility adaptation requires `options_hub.vol/v1`, matching root and raw smile rows. It converts producer percent to ratio exactly once. It retains **`fit:null` and `availableAt:null`**; no model-qualified/fitted IV surface is inferred. Only a canonical date-valued `asof` establishes its session; timestamp fixtures are not truncated into session identities. Selected IV joins only when matrix and volatility source sessions match and coordinates match. Duplicate/invalid smile coordinates are excluded.
- Replay and Flow lenses presently explain missing admitted dated-chain/availability or package evidence. Scenario navigates to the existing exact-contract Plan owner when available; matrix coordinates are not transferred. Saving remains disabled until Saved Research admits options evidence. These are capability boundaries, not completed replay/package/scenario-analysis features to claim in the design.

### Additional acceptance cases

1. Levels `regime:{label:null,...}` displays Unknown, never Slippery; missing level strike remains absent after a proved read and unread before it.
2. Moving a crowded level label leaves its exact-price tick, strike text and selected note unchanged.
3. Research Lab put +100 and put -100 ΔOI occupy the same magnitude side; only the latter is hollow. The table shows both exact signs.
4. Expiry depth is labelled categorical/ordinal; equal depth spacing must not imply equal elapsed time.
5. Filtering leaves retained-point geometry/size scale unchanged; the table preserves zero/null and all rows beyond the 20,000-mark draw cap.
6. Mismatched matrix/vol source sessions withhold joined IV; timestamp-only volatility `asof` must not create a false session join.
7. Repeated coordinates are excluded rather than arbitrarily selected; the exclusion count remains inspectable.

No mutations outside this local advisory report were performed.
