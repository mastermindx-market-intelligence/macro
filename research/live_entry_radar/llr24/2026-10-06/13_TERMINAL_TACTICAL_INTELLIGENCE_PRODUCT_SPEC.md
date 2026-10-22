# 13 — Terminal tactical product specification

## 0. Acceptance gates for the later design/build wave

The later product is not done until a signed-in user can move from a real Market/My row to the correct security, episode and chart interval; inspect first-known evidence and supported uncertainty; observe a truthful invalidation/expiry; and replay the episode without future information. Exercise real data from the canonical producer through the actual route and rendered UI, including healthy, stale, unavailable, partial, no-opportunity, invalidated, overnight and RTH cases. Fixtures supplement that evidence. They do not replace it.

Keep the existing navigation, authentication, entitlement, chart, watchlist/position and evidence owners. Use the existing design system and its dark/light and EN/ZH requirements. This is a design-ready product specification; no new UI, alert service or production route was implemented by this commission.

## 1. Product outcome

Terminal should let a user see **why a security matters, where it sits in the current price process, what has changed, what waiting costs, and what would end the tactical setup**. It must separate observed facts, model estimates and execution limitations.

The useful minimum surface is the existing `/dislocations` Market/My view, a security detail panel, the existing chart extended and qualified for the admitted24H session contract, replay and evidence tabs. A new top-level tactical dashboard is unnecessary. Discover already has screener, heatmap, sectors, leaders and Radar navigation. Existing suite events, replay controls, temporal presets and episode marks are reusable. [R19–R23; T01–T04; T57–T65]

## 2. Information architecture and density

| Surface | Glance tier | Explain tier | Research tier |
|---|---|---|---|
| Market tactical scanner | Security, factual tactical state, session, current location/extension, freshness, one relevant context badge | Why it appeared; contrary evidence; source/coverage limitation; chart action | Cohort/filter denominator, observation/prediction history and evidence references |
| My tactical watchlist | Same fields, scoped by existing watchlist/holdings; distinguish unheld versus held | Existing thesis/TOI context and the exact tactical change | Candidate relation, source and calibration |
| Security panel | One primary state, horizon, supporting condition and invalidation condition | Entry-now/wait comparison, adverse path, uncertainty, liquidity and remaining opportunity | Feature-family contributions, model/label/version/cohort, cases and null results |
| Chart | Price, session shading, selected low/reclaim/invalidation geometry and a small event set | Hover reveals event/known time and basis; click synchronizes panel | Replay/source clock, immutable prediction snapshot and corrected-history comparison |
| Position panel | Holding structure, extension/giveback risk, source freshness | Support/loss conditions, executable liquidation context, horizon mismatch | Exit-policy evidence and position-source lineage where authorized |
| Evidence tab | Compact qualification state | Reliability plot, sample support and reference comparator | Full calibration cohorts, splits, source mode, costs and disposition |

Suggested density budget: one stance line of at most12 words; one short “what changed” sentence; at most three distinct, dependency-labelled evidence-family chips; one freshness/session line. Distinct families may share price/volume inputs; statistical independence is not claimed. The default row should not expose model names, internal study IDs, multiple oscillators or several competing probabilities. The detail view can be rich without making the scan dense.

## 3. Scanner/watchlist contract

Default view preserves the existing user-selected Market/My scope and deterministic product ordering. The new intelligence does not rewrite Prophet rank or create a new universe. Any new tactical sort requires a disclosed field, supported population and explicit product/scientific acceptance; initial sorting can remain recency/state rather than an invented opportunity score.

Visible columns: security; setup context if admitted; factual tactical state; selected horizon; observed distance to the chosen supported low **or** extension from the fixed trigger; liquidity/freshness; next condition. On narrower widths retain security/state/session/age and open a details sheet for the rest. Show total eligible/evaluated/unavailable counts, plus applied filters. The current route caps at200 while a receipt reports312 candidates; later pagination/count semantics must prevent a capped response being presented as the entire market. [R20–R21; I784-live]

Distinguish `0 opportunities among evaluated names` from `names not evaluated`. Current live evidence has broad no-substrate coverage; that fact should remain visible without drowning out the useful subset. A quiet scanner is not a healthy source receipt.

## 4. Security entry card

The primary card answers eight questions in progressive depth: what happened; what changed; what supports it; what contradicts it; what strengthens it next; what invalidates it; how fresh it is; and what is not known.

**Example, observational and explicitly hypothetical:**

> **Reclaim forming · 30-minute view**
>
> Price has recovered the earlier range boundary; the hold is not confirmed.
>
> Reference low: $100.20 · Reclaim: $100.70 · Watch: two completed minutes above reclaim.
>
> Another-low probability: not yet estimated.
>
> Quote liquidity: unavailable for this source.

The sample prices are illustration, not a market call. A calibrated future version may replace “not yet estimated” with a clearly named probability, e.g. “Material new bid low within30min,” its band and support link. It cannot say “87% chance this is the bottom.” An observed two-minute hold is a fact; its probability of surviving another half-hour is a different estimate.

Forecast wording must identify the qualified target's price basis and horizon. The R3 price-bar target may describe a material new price-bar low; “material new bid low” is reserved for the separately qualified bid target. Missing execution data cannot be hidden by changing the displayed label.

Card fields include: owner episode/state and detector-specific plain label; TOI/higher-timeframe context; observed low/trigger/reclaim/invalidation reference with price basis; remaining opportunity/extension from fixed geometry; one primary supported forecast if any; expected adverse-path range; current execution qualification; supportive/contradictory/missing evidence; observed/known/expiry clocks; and direct evidence/replay actions.

Do not label every `CANDIDATE` “Reclaim held.” Current C5 records can be early-watch/blocked-trigger 3D context. The current generic mapping needs owner reconciliation using real rows before stronger language is accepted. [R20–R21; R34]

## 5. 24H chart hierarchy

The default chart shows actual qualified coverage with distinct Overnight, Premarket, RTH and After-hours shading and explicit closed/gap regions. Use a consistent user timezone display with ET session information available; preserve UTC/native clocks underneath. Do not fill an unobserved overnight interval with a smooth line. The current04:00–20:00 candle filter must be extended and qualified before a complete overnight chart is claimed. [T01–T04]

The primary overlay contains no more than one selected low basis, reclaim level and invalidation level, plus current episode markers. Optional layers: raw-print versus supported-quote low; prior-session/weekly levels; explicitly anchored VWAP; liquidity spread; TOI trigger/extension; known catalyst; auction phase; and separately qualified options geometry. Each layer has a meaningful independent reason to appear.

Show geometric anchor and first-known/confirmed time differently. A pivot can be drawn back at its geometric bar, but the actionable mark and replay event appear only at confirmation/availability. A hindsight final low belongs in an explicitly revealed outcome/replay layer, never the original live-state layer. Existing SuiteEvent `confirmedAt` is the relevant reusable contract. [T29; T32–T42]

Choosing an episode locks security identity, time range, grain and selected event. Chart navigation must not silently choose the latest episode or reload current options into an old replay. Keep geometry, current observation and forecast version synchronized. A30-minute target does not require a30-minute candle; temporal presets choose useful observation detail without changing the model horizon.

## 6. Four user journeys

### A. Higher-timeframe investor

Open a native desirable security/candidate → see accepted B4 availability and TOI setup context → inspect local price location/extension and source freshness → compare now versus waiting within a declared horizon → inspect the invalidation condition and evidence → watch the existing episode or create an explicitly chosen alert through the existing service. No tactical score promotes the security or chooses size.

Acceptance example: B4 closed plus a local rebound still displays the B4 reason; the rebound remains context. An unavailable low forecast never becomes an entry veto unless an accepted consumer policy explicitly requires it.

### B. Active day trader

Open Market or My tactical view → filter by supported session/liquidity and setup family → inspect a row's recent change → open its exact5m/1m chart context → compare price/volatility versus microstructure evidence and spread → watch confirmation or failure. The UI states the expected horizon and elapsed time; an old signal with a fresh file fetch does not appear newly actionable.

Acceptance example: a low print with a wide/unsupported ask shows a raw-price observation and execution limitation, without an executable-entry claim.

### C. Existing position

Open the existing holding → inspect position-horizon health alongside current tactical conditions → see extension, giveback risk and the next support condition → expand bid-side execution context and contrary evidence → follow the episode without changing the original investment thesis. A tactical failure and a higher-timeframe thesis failure have different meanings.

Acceptance example: partial liquidation liquidity does not render a full-position executable exit price; missing position identity remains unavailable.

### D. Historical replay

Choose a completed episode → start before first observation → step through actual known-time snapshots → inspect what the system knew at each step → reveal outcomes only on explicit request → compare settled corrections separately. Playback must use the same feature/prediction versions and source mode as the recorded episode, not recompute today's best-looking indicator history.

Acceptance example: a next-day trade break does not erase the original low observation; it appears as a later correction. A future options snapshot or final-profile POC never appears before its known time. [T20; T42; T54–T57]

“As observed” replay is available only when immutable source, feature and prediction snapshots with original known-time receipts exist for that episode. Otherwise this mode is unavailable. A separately labelled reconstructed or corrected-history view may be offered with its source mode and limitations; it cannot manufacture earlier prediction snapshots or claim to reproduce what the system knew then.

## 7. Decision-support language and degradation

| State of evidence | Plain-language treatment | Prohibited inference |
|---|---|---|
| Descriptive early state | “Bottom watch” / “Reclaim forming” when that detector actually establishes it | Low is confirmed or profitable |
| Confirmed causal condition | “Reclaim held for two completed minutes” | Entire day low will survive |
| Qualified adverse context | “Extended from the setup” / “Selling pressure remains elevated” with its observation basis | Guaranteed reversal or forced selling |
| Source stale | “Observation delayed” plus last usable time | Market is quiet |
| Required price source unavailable | “Price-path estimate unavailable,” naming the missing session/source | No opportunity / low failed |
| Quote source unavailable | “Execution context unavailable: overnight quotes missing”; retain an independently qualified price-path head with its actual basis | Missing quotes invalidate every independent head |
| Model unsupported | “Insufficient comparable history” / “Not yet estimated” | Neutral50% or hidden zero score |
| Price-only data | “Price-path estimate; execution not assessed” | Executable fill probability |
| Invalidation observed | “Support lost” plus causal condition/time | Investment thesis refuted |
| Forecast expired | “Window ended” | Win, loss or current recommendation |
| No qualifying opportunity | “No current setup in the evaluated set” with denominator | Complete market coverage |

Keep stale, source unavailable, insufficient model support, inconclusive evidence and no opportunity distinct. Use text plus icon/line style, not color alone. Validated ordinal bands need their own evidence; removing a percentage symbol does not cure unsupported confidence.

## 8. Alerts

Reuse the current suite/Radar alert transport, subscription controls, watermarks and deduplication. Proposed alert candidates are an accepted detector transition, first supported reclaim confirmation, a material invalidation, or an admitted entry-window change for a user-followed episode. Every rule needs causal known time, minimum freshness, supported session and episode/version identity.

Do not alert on every five-minute repeat, retrospectively drawn pivot, continuous probability jitter or recovery from an unknown source as though it were a new market event. Define hysteresis/cooldown in the accepted alert rule; significant invalidation should not be suppressed by a generic positive-alert cooldown. User opt-in, session preference and quiet hours remain with the existing product. This commission sends and schedules no alerts. [T58]

## 9. Visual and responsive direction

Use the incumbent design tokens and typography. Dark treatment: subdued layered surfaces, clear price/level contrast, restrained semantic emphasis and minimal glow. Light treatment: cool canvas, white analytical surfaces, hairline separators and deliberate shadows. These are two designed views of the same hierarchy, not an unreviewed token swap. Keep green/red from serving as the sole evidence cue.

At1440px, scanner plus selected security detail can coexist; the chart remains the primary analysis surface. At390px, show a compact row list, one selected security sheet and full-width chart; move evidence to tabs/disclosure, retain freshness and invalidation. Preserve keyboard navigation, focus order, screen-reader state text, text scaling and EN/ZH parity. Do not localize by truncating away a risk condition.

The later Paper/Figma wave should freeze annotated layouts and interaction states for Market/My, security entry, position health, chart selection, replay and evidence; both themes; desktop/narrow; and each degraded state. It should use real representative payloads including a C5 row and unavailable overnight case. Implementation choices must not leak into the normal user journey.

## 10. Product acceptance evidence packet

Record producer commit, source/episode/prediction IDs, payload hash, route/version, user scope, screen state and exact chart selection. Capture the real navigation sequence and screenshot evidence for the theme/language/width matrix, plus network/console errors. Verify private/no-store behavior, user watchlist/holding isolation and the200-row count/pagination contract.

For scientific displays, attach calibration support and model disposition; for observational displays, attach the exact detector/source semantics. A page200, merged component, successful fixture and aesthetically plausible mockup each establish less than the full journey. No current G8 or new scientific acceptance is claimed here.
