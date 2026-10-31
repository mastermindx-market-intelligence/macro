# RS Leadership Suite - native Terminal integration contract

Source-only implementation boundary for P1.4 and P4 of `RS_LEADERSHIP_SUITE_MASTERPLAN.md`. Recorded 2026-10-31 UTC / 2026-10-30 America/Edmonton. Not a deployed API, chart feature, source admission, forecast or trading decision. Existing Terminal, Radar, Entry Engine, source and evaluation owners remain unchanged.

## 1. Exact inspected sources

Terminal repository `mastermindx-market-intelligence/mastermind-terminal` at `729a781acdb639f9e8ef9aaaba043c7624b6ceda`:

- `docs/research/RS30_PIVOT_RESEARCH_BOUNDARY.md`, blob `5565efb77e0783bd7030b192dedd09bfc9e48c43`.
- `terminal/components/workspaces/RSPivotStudy.tsx`, blob `a2bd197a205f7aae12d4c5d4c45dabcd5a060577` (imports, source/identity/request logic and UI wording inspected).
- Existing source search identifies `terminal/lib/rsPivotStudy.ts`, `terminal/components/workspaces/RSPivotChart.tsx`, `terminal/components/workspaces/DiscoverWorkspace.tsx`, `terminal/e2e/rs-pivot-study.spec.ts` and `terminal/docs/rs30-evidence/README.md`. These paths identify existing implementation seams; searching their names does not establish a fresh production test or full-file review.

Macro at `680b298e42c6e78100980d953582cc73f76a8e53`: `engine/entry_radar/replay/leader_pivot_descriptor.py`, blob `2f5670a83959256b7c7f151acef0b541690e382e`, and existing Phase-1 source owner.

The prior Terminal #879 acceptance remains evidence for the historical research consumer only. No current production browser or deployment was exercised in this contract work.

## 2. Three different setup species

| Species | Actual formation/confirmation | Consumer consequence |
|---|---|---|
| Existing Terminal `rs30-causal-v2` | Swing low with two left and two right completed bars; later reclaim; simulated next-permitted-open entry | Keep all four historical study arms and exported meanings unchanged |
| Existing Macro rejection v0 | Four prior same-session 30m lows; current undercut/reclaim and upper-half close; later completed 1m-close break | Preserve its exact descriptor and progress behavior |
| Incumbent one-red and additive two-red first-green | Current completed green 30m bar after one or two immediately preceding complete red bars; later confirmation is a separate step | Distinct definition, evidence and comparison arm; never rename it as either existing species |

The existing Terminal RS gate uses positive benchmark excess log returns over 65 and 260 aligned completed 30m bars. It is neither a market-wide percentile nor the existing daily leader owner's eligibility. A new qualified daily-leader annotation must state its own owner, definition, original as-of and coverage. Do not silently inherit the old research gate and call it the new leadership system.

The first-green one/two-red definition is an original, reproducible comparator. It does not encode an all-day decline, discretionary level selection, the trader's exact private rules or a validated probability of reversal.

## 3. Clock conversion is mandatory and one-way at presentation

Macro observations use aware UTC instants. The inspected Terminal research report exports ET wall-clock display epochs under `clockBasis=ET_wall_clock_display_epoch_not_UTC`. Its chart anchor represents candle open; completed observation and actual knowledge/issuance clocks differ.

Retain these separate facts in the eventual owner-approved read projection: candle start/end, structure first-known time, decision time, actual issuance time if any, and current source-read time. Source event time never substitutes for alert issue time. A null issuance field stays null for retrospective research.

Use the existing accepted exchange/session clock and chart conversion utilities at the presentation boundary. Do not use a fixed UTC offset, browser-local timezone, or numeric epoch multiplication as an implicit conversion. Do not feed a display epoch into Macro's `_clock` as if it were an absolute UTC instant. Original source clocks remain available in the evidence drawer/export. DST, early close, holiday, delayed receipt and a decision crossing a bar boundary require explicit fixtures.

Example only: an October regular-session 09:30 ET bar corresponds to 13:30 UTC while daylight saving time applies; this is not a year-round four-hour offset. The actual calendar owner must determine each conversion.

## 4. Formation-to-confirmation seam - incumbent correction

The rejection-v0 `_reference_value` correctly rejects a first-green schema. However, the expanded census found the ALREADY EXISTING `first_green_reversal_descriptor.py` in the same Macro source revision, with its own `freeze_first_green_reference` and `describe_first_green_progress`. It supplies native1m-close confirmation, low invalidation, gap/expiry semantics and original authority ceilings. The earlier inference that first-green freezing was missing was incorrect. Preserve and consume that implementation; do not build a new shared universal owner or copy its progress loop.

The current additive implementation changes only a separately typed two-red FORMATION comparator and exact one-red passthrough. Old formation/reference/progress outputs remain unchanged. Two-red records deliberately cannot impersonate the incumbent v0 frozen-reference schema. P1.4 is now a later reviewed compatibility extension inside that incumbent owner, not creation of first-green confirmation from scratch.

The original-author sample also contains explicit second30m-candle-close-above wording. That is a separate registered comparison, not the existing1m-close definition and not evidence for intrabar-touch execution. Keep immediate-next versus eventual confirmation, event/known/decision/issue clocks, source gaps, expiry, failure precedence and research buffer versus exchange tick distinct. A source digest is consistency evidence, not historical availability or financial authority.

## 5. Source and transport boundary

The current Terminal study reads `/api/intraday?tf=5m&ext=0` and builds 30m candles from six nominal 5m slots. This is appropriate to its declared exploratory consumer, but is not a substitute for the required native one-minute first-seen source, identity/basis receipts or quote-executable confirmation. Six nominal slots do not prove complete trading coverage or original availability.

Do not rerun the new first-green detector in the browser on a second differently qualified price feed. The intended feature consumes the owner-computed observation and retains its revision/source references. The existing chart renderer can display the associated candles only after their identity, session, basis and source construction are reconciled. If chart bars and observation evidence differ, disclose the mismatch instead of silently moving the marker.

Use the existing entitled API/publisher and event/evidence delivery path. No new WebSocket owner, collector, historical dataset, scheduler, auth service or public raw-price endpoint. A draft descriptor has no permission to appear on the customer route. Research-source qualification and customer-use rights are separate checks.

## 6. UI integration and minimum useful vertical

Reuse the existing Discover workspace navigation, shared chart engine, identity/auth shell, evidence drawer and replay patterns. A new dedicated application is not required. Preserve the accepted historical RS Pivot Study and its exports; a new observation panel or explicit variant choice must not silently alter old saved research reports.

The first useful user path is:

Market/theme or standalone-leader view -> qualified leader row -> pullback observation -> completed first-green variant -> frozen levels and later structural result -> source/catalyst evidence -> original-decision replay.

Compact leader row: original leader definition/as-of, benchmark and horizon, own absolute versus relative strength, optional group support and coverage, extension/accessibility, pivot variant and age, frozen levels, source delay and evidence maturity. Keep entry authority separately visible. No unvalidated combined confidence score.

State copy must distinguish: eligible observation; forming/incomplete candle (not a formed pivot); first-green formed; later break observed; invalidated; expired; no pattern; unsupported source; no qualifying candidate. Empty data are not zero probability or a bearish signal. Missing optional catalyst/group evidence must not erase an independently supported stock observation.

The inspected Terminal is dark-only. Required acceptance is EN/ZH and actual supported responsive settings; do not add a global light-theme project as a prerequisite. Shared CSS/chart tokens remain canonical. Keyboard focus, accessible status text and non-color-only distinction are required for any new controls.

## 7. Request and replay invariants

The current study guards account identity and hydration, rejects duplicate in-flight requests, aborts superseded requests and increments request generations on input changes. Reuse those established behaviors in any new read projection. A late response from a previous ticker, benchmark, user or timeframe must never overwrite the current view.

Freeze source/definition/candidate/decision identity with the displayed result. Changing symbol, universe, benchmark, variant, timeframe or cutoff invalidates the old result visibly. Navigating a chart must not mutate a frozen export. A historical observation cannot acquire a newly discovered catalyst or revised membership without an explicit separate corrected-now view.

For live factual notices, reuse the existing per-user outbox only after actual publication/admission. One observation/revision/recipient key must not cause duplicate delivery on rerender, reconnect or correction. A browser marker, network success or saved setting is not a delivered-alert receipt. No automatic order or position sizing belongs to this integration.

## 8. Acceptance matrix and evidence

Source tests: exact setup species, UTC/display clock refusal, DST/holiday/half-day conversion, incomplete candle, delayed known-at, source correction, chart/source mismatch, multiple share classes, missing identity/basis and unknown optional group/catalyst. Native owner outputs must not change under later invisible data.

Client tests: signed-in eligible path; anonymous gate; source unavailable; no candidates; early-session formed setup; failed/expired setup; late response after ticker switch; duplicate click before render; auth change; restored saved state; frozen export and replay; EN/ZH; three responsive sizes; keyboard/focus; no overflow or console/network failure.

Real-path proof: exact candidate source and build identity, actual authorized provider/owner payload, authenticated route response, rendered chart/evidence alignment and retained interaction evidence. Synthetic UI fixtures are not this proof. No source data, live credentials or private user holdings are copied into public GitHub artifacts.

Scientific acceptance remains Macro Setup Species/Evaluation OS, not the browser's hypothetical-trade table. The old three-symbol negative study is a cautionary result for its own definition and sample, not a verdict on the new first-green hypothesis. The old interactive 70/30 split remains exploratory, not an untouched holdout.

## 9. Immediate implementation boundary

P1 additive two-red formation and its synthetic tests can proceed independently; incumbent one-red formation/progress already exist. P1.4 common reference integration follows exact source tests/review and explicit owner compatibility. Real customer delivery additionally requires P2 source admission/latency and the accepted transport route. This contract eliminates concrete clock/species/renderer integration ambiguities; it does not waive those gates or modify Terminal source.
