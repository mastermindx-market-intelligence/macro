# Route, source, numerical and builder contract

## Authority and status

This is a consumer specification of **D08-OPTIONS/1.0.0**, frozen at macro `d0516e1bad9cb5982d43d20c4167d0355cb70e2c`. Its logical objects are design obligations on existing owners, not a released wire schema or a new store. This document proposes no endpoint, independent source transport, identity service, durable cache, plan store or replay cursor.

Source facts below are pinned to Terminal `2ded360882b9c721e690907ff363b553781fb920` and macro `df691495abb1c2ba8f61e5624126cb17ad14e056`. The read-only [source audit](SOURCE_AUDIT.md) records exact evidence, bounded limits and the follow-up that resolved Levels and Research Lab consumer/geometry questions. Served browser evidence is separately dated; the served deployment SHA was not established and must not be inferred from the source pin.

## 1. Route and object map

| Canonical registry family | Existing route/variant | Host and entry | Retention / owner |
| --- | --- | --- | --- |
| `macro:gex` | `/gex.html` and its existing root/context controls | Macro `templates/gex.html.j2`; board builder `scripts/build_gex_board.py` | Live anonymous family in assignment registry. Preserve source page and common-shell integration; F01/F02/F03 consulted. |
| `terminal:options` | `/options` | `terminal/app/(shell)/options/page.tsx`, `components/workspaces/OptionsWorkspace.tsx`, `components/OptionsHubView.tsx` | D08 owns route/navigation parsing and shared Objects. Access is source/feature-specific, not blanket anonymous. |
| Exposure/GEX view | `tab=gex`; alias `prism→gex` | `components/gexdesk/GexDeskView.tsx` | Legacy PRISM defaults to matrix; explicit valid `view=strike|expiry|matrix|chart` wins. Preserve reload and Back/Forward. |
| Flow Surface | `tab=surface` | `components/surface/SurfaceView.tsx` | Preserve strike×session-time field snapshots and the current temporal child owners. |
| Positioning / Levels | `tab=positioning`, `tab=levels` | `components/msc/PositioningView.tsx`; `components/levels/LevelsView.tsx` | B presentation; source producers keep definitions. |
| Volatility | `tab=volatility` | `components/vol/VolView.tsx` | **`vol` currently aliases the screener**, so do not repurpose it as volatility. |
| Research Lab | `research=1`; legacy `view=research` | `components/researchlab/AdmittedOptionsResearchLab.tsx` → `OptionsResearchLab.tsx` | Existing verified identity/entitlement admission must survive every new entry and 2D alternative. |
| Plan / Scenario transition | Existing D08C route/owner only | Existing shortlist/Plan validator | No B-specific plan route, saved-scenario store or append-only query invention. |
| Replay reference | Existing dataset-specific validated route/codec | D08D and incumbent archive/distribution owners | No conversion between dataset cursors; no added parameters to closed futures/equity parsers. |

Do not serialize B-only filters into a route without D08's admitted parser change. Use existing validated same-origin history/return context for transient state. Preserve exact route bytes when lawful rather than reconstructing them from display labels. Unknown aliases, invalid roots and unsafe return targets get explicit fallback. An originating print, exposure node, chain coordinate and qualified contract remain different identities.

Listing identity requires source namespace and exact root; issuer/security ID, venue, region, currency and quote symbol are nullable if the source does not establish them. Do not join listings by displayed ticker alone. US options coverage is not automatically available for Chinese/Hong Kong/Canadian/global shell selections. A global shell company selection must not silently relabel an independent SPY options book; show each active context and require an explicit change.

## 2. Actual reader/producer map

All Terminal paths in this table are under `terminal/`. Keys name existing reads through the current flow/source owner; they are not new proposed APIs.

| Surface | Actual files and reads | Cadence, validation and failure obligations |
| --- | --- | --- |
| GEX and archive | `components/gexdesk/GexDeskView.tsx`; keys `gex:{root}`, `matrix:{root}`, `gex_dates:{root}`, `gex_at:{root}:{date}` | Preserve sequence/root fences and current archive owner. Matrix anchor is `_build_meta.asof_date`; quote time cannot replace it. Keep separate current and dated keys. Effective edge/cache TTL must be verified at build time; no new global polling is authorized. |
| Qualified exposure | `components/exposure-map/ExposureMap.tsx`; `lib/exposureMap.ts`, `exposureMapProjection.ts`, `exposureSurface.ts`; `ExposureSurface.tsx` | Use the existing validated projection and prior projection. Reader states include data, unavailable, wrong_root, future, malformed; qualification includes legacy, qualified, dated, unqualified. Preserve schema/version checks and nullable expected coverage. |
| Reported comparison | `lib/exposureReportedChange.ts` | Pure function over two coordinator-validated `ReportedGammaSnapshot` objects. No independent fetch/cache or temporal authority. |
| Flow Surface | `components/surface/SurfaceView.tsx`, `surface_dates:{root}` and existing field/replay child contracts | Snapshot time is not candle-resampled. Full child transport details remain those owners' build integration responsibility; do not replace them with another reader. |
| Positioning | `components/msc/PositioningView.tsx`; primary `gex:{root}`, `moves:{root}`; optional `agg:{root}`, `matrix:{root}`, `quad`, `grades:{root}`, `grades_universe` | Optional context failure cannot erase valid primary data. No inferred flow/probability semantics from labels alone. |
| Levels | `components/levels/LevelsView.tsx`; `/api/flow?f=levels:{ROOT}`; schema `levels.v1` | Shared `flowGetResult`, 60s polling only while visible, refresh on visibility return, sequence fencing, root-change clear. Current stale badge uses ET calendar days; do not call that exchange-session age. Referenced producer `engine/levels_engine.py` and fixture `public/data/levels_fixture.json`; producer role/brightness formulas remain an explicit build gate. |
| Volatility | `components/vol/VolView.tsx`, `volTypes.ts`; `/api/flow?f=vol:{ROOT}`; stored `options_hub/vol/{ROOT}.json`; schema `options_hub.vol/v1` | Nightly EOD, three-session stale threshold in current consumer, no continuous live polling. Optional `agg`, `moves`, `/data/{encodedRoot}.fund.json` are independent bands. History rank and close may be null. |
| Research Lab | `AdmittedOptionsResearchLab.tsx`, `OptionsResearchLab.tsx`, `researchLabAdapter.ts`, `ResearchScene.tsx`, `researchVolatility.ts` | Reuse admitted matrix/volatility payloads and existing read status/retry callbacks. Lab creates no source reader/subscription or valuation engine. Invalid/duplicate coordinates are excluded with counts. |
| Macro GEX | `engine/gex_engine.py`, `engine/gex_model.py`, `scripts/build_gex_board.py`, `templates/gex.html.j2` | Preserve model definition and source file identity. Build success can retain old payloads after acquisition failure; it is not freshness proof. Constructed 16:00 ET session time is a compatibility anchor, not observed event time and not an early-close-aware timestamp. |

Cache keys must include exact root and existing source family/date identity. Request de-duplication, TTL and cancellation remain with the incumbent reader. The future builder must document effective production cache headers/TTL before asserting freshness; this audit does not invent those values. Client state owns presentation/selection only. Server/source owners own access decisions, source qualification, producer semantics and distributions. The browser must not fetch protected data first and merely hide it later.

## 3. Units, sign and calculation identity

### Macro gamma

The inspected engine computes, with `sign=+1` for calls and `−1` for puts:

```text
dg  = gamma × open_interest × contract_multiplier × spot²
gex = sign × dg × pct_move
net_gex_bn = sum(gex) / 1e9
```

Defaults are multiplier 100 and `pct_move=.01`. The ordinary unit is model gamma exposure in USD per +1% underlying move under the assumed sign convention. The general unit follows configured `pct_move`. It is not observed dealer inventory or trading flow. Preserve the engine's assumption-basis regime passport, including its single-name qualification. The newer Terminal projection has its own metric/source definition; a shared display divisor does not prove methodological equivalence.

The engine reprices European Black–Scholes gamma with supplied rate/yield. Regime is the sign of that curve at actual spot; flip is the nearest sampled crossing. No crossing remains null. Signed flip distance is `100 × (spot−flip)/spot`. Macro display and engine grids differ (±15%/81 versus ±25%/101), so their curve/scalar values must not be asserted interchangeable without parameter alignment.

VEX is `sign × vanna × OI × multiplier × spot × pct_move`; CEX is `sign × (charm/365) × OI × multiplier × spot`. The inspected VEX comment itself qualifies its unit approximately. Precise labeling remains a producer gate. Uncomputed Vanna/Charm in a particular matrix stay unavailable; computation in another source family cannot enable them by analogy.

### Risk reversal and rank collisions

| Exact producer output | Definition | Required label |
| --- | --- | --- |
| `summary.rr_25d` from `risk_reversal_25d` | `(25Δ call IV − 25Δ put IV) × 100` | Call-minus-put, selected expiry/method and vol-point scale |
| `summary.skew.rr25` from `risk_reversal` | `(25Δ put IV − 25Δ call IV) × 100` | Put-minus-call, selected expiry/fallback method and vol-point scale |
| Macro `iv_rank` | Strict historical percentile over up to 40 retained sessions; needs at least five | Method/window and actual history count |
| Terminal `iv_rank_252` / `iv_rank_all` | Distinct published contract | Published method, window, coverage/since; do not relabel as the macro statistic |

Call IV 20% and put IV 23% yield −3 or +3 volatility points according to the specific RR method. No generic unlabeled RR25 field or silent sign normalization is acceptable. Semantic reconciliation belongs to the existing producer/D08 measurement owners and is a build gate.

### Volatility values

`VolTermRow` is `{dte, exp, atm_iv:number|null}`; smile rows preserve exact `exp`, `strike`, `call_iv|null`, `put_iv|null`. IV/RV are percent numbers, so 58.2 means 58.2%. Ranks are 0–100. Upstream published `vrp = atm_iv−rv20` is displayed verbatim, never recomputed from visually selected observations. Nullable history rank/close are not backfilled. Default deep-ITM wing trimming is explicit and reversible.

Research volatility converts percent to ratio exactly once, carries `fit:null` and `availableAt:null`, and accepts only a canonical date-valued `asof` as a session. It must not truncate a timestamp fixture into an invented source session. IV is joined to a Lab coordinate only when source sessions and coordinates match. Modeled/fitted IV terrain remains unavailable without a qualified producer.

## 4. Identity, clocks and coverage

Every measurement retains source namespace/family/key, exact root/listing, grain, source schema when supplied, metric/unit/currency/scale/sign basis, source session and qualification. Distinguish event time, spot time, OI position session, OI report date, availability, build time, retrieval and correction reference. Unknown clocks remain unknown. The current spot can be newer than the chain, but it cannot redate the chain. DTE derives from the selected source session where the source provides that definition, not today's browser clock.

Coverage denominators must name their population:

- **Reported rows:** supplied source rows, with finite/qualified and excluded counts.
- **Rendered grid positions:** known cells divided by declared visible/selected positions.
- **Full-lens population:** the full qualified scope before crop; distinct from displayed-window totals.
- **Source collection/market coverage:** unknown unless the source establishes an expected population.

The served `228/273` matrix evidence establishes grid completeness only. Candidate fixture `108/112` describes its illustrative reported rows; neither establishes exchange-wide coverage. A complete total is unavailable when required constituents are unknown. A useful known subtotal can be shown with that name and explicit exclusions. Zero is a finite observation; null, absent, malformed, wrong-root, future, unsupported and unqualified are distinct states and never become zero.

Corrections retain source identity/revision and original evidence when available. A later correction is not silently rewritten into historical knowledge. If a source lacks a qualified availability instant, point-in-time comparison is unavailable; displaying its date is not proof of historical availability.

**Effective comparison cutoff:** the existing temporal/coordinator owner supplies an aware instant and mode. With no inherited historical context, request that owner's current-knowledge stamp for this comparison. With a historical origin, preserve its exact cutoff across view switches and returns; do not replace it with browser `Date.now()` or silently advance it when loading newer data. Display date, time, timezone and current-knowledge/historical mode in the comparison basis and source details. Missing cutoff/availability retains the existing unavailable outcome. The fixture cutoff is `2026-11-03T04:15:00-05:00`, after current availability `2026-11-03T03:52:00-05:00`. At a Nov 2 cutoff the same current observation must be refused. This is an obligation on the existing owner, not a new temporal store, route parameter or cursor.

## 5. Cross-slice contracts

**A→B:** accept observation + existing returnContext. Resolve exact root and a qualified dated book; declare broader scope if only the root transfers. Decline reasons remain identity_ambiguous, missing_book, denied or source_unavailable. Preserve originating row/filter/focus.

**B node:** listing, snapshotRef, coordinate, metric, unit, lens and qualification are required. Expiry, strike, right, spot/spotAt and fingerprint remain nullable when not established. Mark whether the coordinate aggregates members. `population_id`, `economic_expiry_at` and joint completeness survive the qualified Surface adapter.

**B→C:** B supplies node/cohort/returnContext; C admits exact actual contracts using `optionsContractShortlist.ts` and its existing stale/term/duplicate policy. Keep exact root including adjusted roots, expiry, strike, right, copied source row/session/family/list and optional terms. Missing nullable terms are not fabricated; C's actual validation determines eligibility. An aggregate-only coordinate is refused, not converted to a synthetic leg. C retains ownership of draft, payoff, plan assumptions and saved scenarios.

**B comparison:** reuse `ReportedGammaSnapshot`: securityId, root, scopeKey, definitionKey, sourceSession, sourceKey, availableAt, oiReportDate, members; optional OI position session/correction reference. Members remain `{expiry,strike,right,valueUsd|null}`. Same identity/scope/definition, advancing sessions and cutoff eligibility are required. Global matched finite intersection defines the result. `velocity` and `percentChange` remain null. Surface's same-cell/same-population comparison is a distinct narrower method and must keep its own basis label.

**B→D:** request only the existing valid dataset grammar, access result and return context. Requested and loaded windows/cutoffs/cursors are distinct. No shared cursor conversion among options books, futures and equity replay. B retains its presentation and origin; D/incumbent archives decide admission and temporal evidence.

**Durable save:** this design performs no durable write. A future explicit save stays with C/D23/native Investigation and requires the existing authenticated owner, reconciliation identity, accepted protocol and returned ID/revision readback. Pending, saved, rejected and unknown outcome are different. An unknown effect is not resent. Navigation, root changes and view switches never persist research implicitly.

### Integration qualification of the D08A/D08D returns

The [D08A immutable return](https://github.com/mastermindx-market-intelligence/macro/pull/10649#issuecomment-6619632039) at `c3413d84650ce85ca0c875c16b53b5e519b46f35` and [D08D immutable return](https://github.com/mastermindx-market-intelligence/macro/pull/10649#issuecomment-6619899660) at `a6ffdef508eb6f6293c74242f85d50d8c8843e6f` were consumed before D08B publication. They do not change the frozen D08 interface or confer review/release authority.

1. **Original observation stays original.** A tape row can be a coalesced observation. Keep its grain, source row/key, source session, methods, clocks and uncertainties available as **Original source evidence**. A later dated book is a separate observation; never copy its terms or timing backward into the original print. If exact linkage cannot be qualified, label the receiving scope as root-only or return the declared unavailable reason. Access loss, correction or expired windows preserve the permitted origin/return identity and exact scan restoration; protected source values remain subject to their owner.
2. **`sourceList` is provenance, not a new deduplication key.** The frozen logical pin requires source-list context. At the inspected Terminal pin, `ShortlistPin.hotView` retains a hot-list origin, but `pinKeyFor` is exactly `${family}@${session}#${identityKey}`. Different hot views of the same identity/family/session therefore do not create separate pins. `buildPin` checks ambiguity over the **full original unfiltered list**. Keep the source-list context and full-list evidence for validation; do not alter the key, fabricate a list, or introduce another identity store. The stale code comment about two lists is not a replacement for the executable key function.
3. **Existing C admission remains narrower than an arbitrary B row.** `ShortlistFamily` currently admits only `doi | hot`; an exposure node/member or chain coordinate must not be cast into one of those families. The Plan affordance is usable only after the existing C/source owner has resolved an actual accepted source row and validated terms, or explicitly admitted an adapter through its own build scope. Otherwise retain B's investigation and show `missing_evidence`/`aggregate_only`/`ambiguous_terms` as appropriate. B17 is an illustrative qualified-contract state, not proof of a currently implemented arbitrary-exposure-to-Plan path.
4. **Replay grammar stays with D.** Futures' validated integer `at` and its closed query grammar do not transfer to equity replay. B adds no return query key, shared cursor, source catalog or save plane. D's exact-versus-time-only and source/admission/window decisions remain intact; return restores the originating B node or explicitly names its unavailable state.

Primary shortlist readback: `terminal/lib/optionsContractShortlist.ts` at Terminal `2ded360882b9c721e690907ff363b553781fb920`, Git blob `8d42da79f3e5bbda9ea236df93845824feb4900d`. This is a B consumer qualification; D08/C retain implementation and any shared-contract amendment.

## 6. Reuse and builder sequence

1. Obtain the released F01/F02 foundation and D08 admission for the committed reference. Verify relevant source drift against the pins; do not re-census unrelated products.
2. Add consumer-level fixture coverage around the existing projection, comparison, source adapters and route parsers. Preserve current tests and accepted method definitions before changing composition.
3. Recompose Options/GEX presentation within the owned component tree. Reuse the existing flow readers, root fences, qualified projections, selection and history/return codecs. Do not add route-global stores or duplicate subscriptions.
4. Implement responsive selected inspector and complete phone menus; retain original row focus/scroll. Bind exact-table and 3D to one projection/selection. Lazy-mount 3D only when selected and allowed; unmount resources when no longer needed.
5. Integrate volatility/positioning/levels with separate source identities and optional-panel failure isolation. Preserve old aliases and legacy root/date URLs. Correct null regime display; do not silently change level formulas.
6. Integrate C/D transitions against frozen accepted shapes and actual access/admission. Gate unsupported data instead of inventing values or stores.
7. Run the falsifiable acceptance suite in VERIFICATION, including dense source data, wrong-root late responses, method/cutoff refusal, null/zero, ordinal geometry, full-dataset table parity, mobile/zoom/locale and access states.
8. Use the existing release mechanism only after separate implementation authority. Preserve the old presentation path until route/source parity is proven. Roll back presentation through the existing flag/release owner while retaining contracts and saved objects; do not create a new flag plane or migrate persisted data in this design wave.

Performance targets are future p75 mobile/desktop budgets: LCP ≤2.5s, INP ≤200ms, CLS ≤0.1. Reserve chart/table space; bound visible cell/mark work; retain pagination/virtualization semantics and accessible row navigation; do not eagerly mount hidden views or all expiry workspaces. Measure representative dense books, not only the 54-node design fixture. The Lab's 20,000 mark cap and 50-row table page remain explicit; any new bounds require source-preserving pagination and tests.

## 7. Unresolved owner gates

| Gate | Owner | Minimum evidence to close |
| --- | --- | --- |
| Foundation release | F01/F02 | Released shell/system version and inherited effect/review disposition, then geometry recheck |
| Formal reference acceptance | D08 + existing admitted RIG/review owner | Trusted root/parent/admission, immutable artifact binding, independent required receipts; native advisory review is insufficient |
| RR/rank cross-source reconciliation | Incumbent Macro/Terminal measurement producers + D08 | Exact method/expiry/window mapping and sign fixtures; no field-name-only merge |
| Exact contract admission from aggregates | C + incumbent source resolver | Unique actual accepted row and terms/stale validation; no coordinate promotion |
| B evidence outside current `doi`/`hot` pin families | C + incumbent source resolver / D08 | Resolve an existing accepted row or explicitly admit an owner-scoped adapter; preserve source-list provenance and existing pin-key semantics; no cast or new identity store |
| Levels upstream interpretation | Existing Levels producer | Role/brightness formula and freshness evidence before altered analytical copy or probability claims |
| Effective cache/source freshness | Existing reader/deployment owner | Production cache/TTL and successful fresh payload evidence, independent of job exit |
| Fitted IV/unsupported Greek capability | Existing producers | Qualified source/method/unit/availability; useful unavailable state until supplied |
| Durable options research / replay evidence | C/D23/D and incumbent owners | Existing admission and supported evidence/readback; no parallel owner |

## Primary source references

- [D08 common objects](https://github.com/mastermindx-market-intelligence/macro/blob/d0516e1bad9cb5982d43d20c4167d0355cb70e2c/research/design_candidates/production_design_20261102/d08/SLICE_INTERFACES.json)
- [Macro gamma engine](https://github.com/mastermindx-market-intelligence/macro/blob/df691495abb1c2ba8f61e5624126cb17ad14e056/engine/gex_engine.py)
- [Macro GEX model and RR methods](https://github.com/mastermindx-market-intelligence/macro/blob/df691495abb1c2ba8f61e5624126cb17ad14e056/engine/gex_model.py)
- [Reported comparison](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2ded360882b9c721e690907ff363b553781fb920/terminal/lib/exposureReportedChange.ts)
- [Existing exact-contract shortlist admission](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2ded360882b9c721e690907ff363b553781fb920/terminal/lib/optionsContractShortlist.ts)
- [Qualified 3D model](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2ded360882b9c721e690907ff363b553781fb920/terminal/lib/exposureSurface.ts)
- [Volatility schema](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2ded360882b9c721e690907ff363b553781fb920/terminal/components/vol/volTypes.ts)
- [Levels consumer](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2ded360882b9c721e690907ff363b553781fb920/terminal/components/levels/LevelsView.tsx)
- [Research Lab adapter](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2ded360882b9c721e690907ff363b553781fb920/terminal/components/researchlab/researchLabAdapter.ts)
- [Research Lab geometry](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2ded360882b9c721e690907ff363b553781fb920/terminal/components/researchlab/ResearchScene.tsx)
- [Research volatility adapter](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2ded360882b9c721e690907ff363b553781fb920/terminal/components/researchlab/researchVolatility.ts)
- [Web Vitals thresholds](https://web.dev/articles/vitals)
