---
key: MARKET-TIDE-RESEARCH-FOUNDATION-20260924
claim: "Time decay and falling implied volatility do not imply uniformly supportive dealer hedging: a fixed-price short-put model reverses hedge-flow signs between out-of-the-money and in-the-money positions."
falsifier: "Recompute the zero-rate European put-delta example preserved at Macro commit 8de2d6b386ba2b9102c708caf6db71af84929167 in this same file; incorrect signs or arithmetic would falsify the specific model counterexample."
so_what: "Market Tide must condition hedge scenarios on signed inventory and moneyness; begin empirical work with source-qualified event/price benchmarks, exclude survivor-biased historical breadth, and preserve prior failed GEX hypotheses."
kind: constraint
verified_at: 2026-09-24
verified_by: "Macro #7925; original eight illustrative calculation checks at 8de2d6b386ba2b9102c708caf6db71af84929167, plus R1 source/receipt audit documented in research/options_estate/MARKET_TIDE_R1_SOURCE_AND_EVENT_SEQUENCE_2026-09-24.md; no new market backtest."
scope:
  - macro
  - WS:ADVANCED-DATA-OPTIONS
  - market-tide-research-20260924-sol-001
confidence: verified
---

# Market Tide — cumulative research continuation

## Mission and authority

Sol retains the Chairman's September 24 end-to-end commission: rigorous research and validation, then useful system integration and a dedicated Market Tide page if demonstrated value warrants it. User job: recognize deteriorating risk/reward and prepare exposure, entry/exit and re-entry decisions. Machine job: combine expiry structure, event sequence and observed market conditions with explicit horizon, evidence quality and invalidation. A current continuation supplies intent, not permission to bypass resource, source, runtime or effect gates.

Operation `market-tide-research-20260924-sol-001`; parent evidence carrier Macro #7925; source PR #7929, Draft/HOLD, branch `claude/market-tide-research-20260924-sol-001`. No new workstream or control plane. Protected Mastermind pin remains `1a7d400294b0d37c460b963b8865b40a23173b58`, Skillpack 1.0.1/bootstrap 1; current read verified unchanged. R1 implementation-source investigation pin is Macro `5ab62e1b7c6635b85dc4f079803c3376c239f2d2`.

## Accepted research foundation — preserve, do not recompute by habit

The original complete mechanical example, literature map and programme remain immutable in this file at commit `8de2d6b386ba2b9102c708caf6db71af84929167`, blob `740b8727c7e7ab1871e05e5ce197ed80d3b5b509`.

For hypothetical 100,000 equivalent shares of dealer short European puts at spot100 and zero rates/dividends, reducing time from10 to5 days at30% volatility produces approximately +7,542 hedge shares for strike95 but -8,407 for strike105. A separate volatility decline also reverses signs by moneyness. Original eight arithmetic/domain/direction checks verify a model illustration only. No observed dealer book, empirical frequency, causal estimate or trading result follows from it.

The original R0 calendar-only preregistration remains in #7925 unchanged and unexecuted. Do not rewrite its windows, source or endpoints after results, or execute it through an alternate route to bypass the original refusal.

## Current material result: R1 source audit and C1 benchmark freeze

Read the new report rather than old tool history:
`research/options_estate/MARKET_TIDE_R1_SOURCE_AND_EVENT_SEQUENCE_2026-09-24.md`.
First report commit `458023f18beb132c869397e6fe9788b096e3f6be`; blob `f7abf209ee811290c257335a37228b9eb47a7924`.

1. **Prior GEX evidence recovered directly.** The actual MAS-260 cross-instrument receipt was read from its incumbent locked local worktree at HEAD `b281fe529717656e070abaa15651c75fb74bf93f`. Receipt SHA-256 `5f241659cda73bb9283de75875b630ee79482ff318df674fb3541f095541b975`. Same-day QQQ120m was worse under its frozen recipe; IWM had one eligible record. Dynamic multi-expiry SPY lift did not transfer robustly to QQQ/IWM. These are receipt-verified results, not a new independent rerun. Original availability/dealer-side limitations remain. The later calibration rejection was recovered from the incumbent handoff, not rerun.
2. **Historical breadth has a concrete eligibility problem.** The canonical breadth projector states that upstream history uses today's constituent membership and permits only the current tip as an operational observation. Use actual historical membership or existing first-seen snapshots for a primary predictive cohort; do not treat recomputed history as contemporaneous information.
3. **Long price history exists, with explicit limitations.** Successful native footer inspection found 8,458 SPY rows in the local Yahoo file, January1993–September4,2026; separate close_price/close bases, no open/high/low. Breadth had16,229 rows and current constituents503. These are local metadata observations, not live-service freshness, complete history or immutable corpus proof. The follow-up byte-hash and QQQ/IWM/RSP inspection was refused before dispatch, so those additional facts remain unknown.
4. **Reuse existing event and price owners.** Current calendar is context-only and its third-Friday16:00 OPEX representation is not contract-specific settlement or historical schedule-vintage proof. Existing price vocabulary separates structure, total return and execution. Stock earnings expectation_state and Federal Register policy_calendar are not macro-consensus substitutes. Existing Treasury-calendar studies keep their trial/owner identities.
5. **Event sequence is a defensible research direction.** Accessible Alam working-paper abstract motivates macro-before-FOMC conditioning. Official SF Fed USMPD documentation and revised working-paper HTML support separate statement/conference/combined-event treatment. Full-paper quantitative version reconciliation and any data ingestion remain unverified; parsed PDF and screenshot versions disagreed. Event-window surprises are ex-post variables, not advance forecasts.
6. **C1 benchmark is frozen, not executed or data-admitted.** Five-session downside normalized by prior20-session volatility; price-only vs price+known-event vs two prespecified event×deterioration interactions; fixed ridge benchmark, monthly chronological evaluation, maturity/purge rules, dependence-aware paired comparisons and a predeclared materiality hurdle. Full details in R1 report. No options predictive feature or survivor-biased historical breadth in C1. Predictive improvement cannot authorize a sizing policy.

## Outcome before page

Separate return prediction, downside-risk prediction, trend-transition evidence and the economic usefulness of acting. Proposed page must show current conditions, upcoming event/expiry sequence, unresolved uncertainty, change explanations and timestamp-faithful replay. Statement release alone does not mean the whole FOMC event is over. A close-derived indicator cannot receive a same-close fill, and a next-open decision cannot claim to avoid a gap already realized before that open.

First product slice remains read-only composition through existing calendar, market-state, breadth, options and Market Memory owners. No synthetic confidence percentage, automatic safe-week label or independent learning ledger. Full consumer implementation and real production/browser proof remain owed.

## Custody and no-rebuild boundaries

MAS-260 / Macro #7328 owns `claude/mas260-exposure-baseline-20260918`, its local calibration/state/shadow work and30/60/90/120-minute contracts. Local read path:
`/Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/mas260-exposure-baseline-20260918` on m2studio. Its CI-deferral and source lock were preserved; this operation did not edit, push, rerun or absorb it.

Release Radar #6868 / WS:RATES-INFLATION-COMMAND / MAS-204 retain event/release/forecast ownership. Market Ontology #6819 F03/F05/F08/F10 are counterparts, not reassigned children. Market Memory already owns forecast/outcome persistence and first-write observation clocks. Existing Risk Radar/Portfolio/Prophet weights, scores, classifier, risk ladder and trading policy remain unchanged.

## Effects and exact holds

- Original R0 download/write action: platform refusal before dispatch, TOOL_DEGRADED / EFFECT_NONE. Original MacBook REPL67757 was previously reconciled untouched and closed exit0. No retry, rephrase, alternate carrier or delegated replacement.
- R1 follow-up native footer/hash inspection: explicit platform refusal before dispatch, no PID/result. No retry or alternate route. Earlier successful read-only metadata remains evidence, but no dataset hash is invented.
- Independent permitted work in this tranche: source/metadata reads, actual prior research-receipt inspection, public primary literature and GitHub research-record writes.
- No native repository source modification, worker submission, active child, watcher or automatic wake. No current unresolved modifying effect has been observed. Source-writing effects remain on the same GitHub branch until reconciled.
- Normal exact-head validation, independent review/CI and source acceptance remain owed. Draft/HOLD does not mean the research is validated or the page deployed. No native full Agent OS validator run is claimed for these updated records.

## Cumulative continuation

FINALIZATION_CLASSIFICATION: CHECKPOINTED_CONTINUATION, conditional on final exact-source and #7925 checkpoint readback.
MISSION_COMPLETE: false.

Boundary: completed source-eligibility/event-sequence tranche and prespecified C1 design, with substantial accumulated native/web/PDF-version context. This protects continuation; it is not completion, cancellation, writer release or custody transfer.

**Exact next action:** locate the incumbent historical event-occurrence/schedule-known-at evidence and price adjustment/availability receipts necessary to admit one C1 daily cohort. Use bounded existing-owner reads, not either refused operation. With a qualified supplied-input cohort, implement/evaluate the frozen C1 benchmark through existing research/validation owners. If only retrospective inputs qualify, keep that cohort explicitly separate from genuine historical/prospective availability and do not promote it. Actual breadth and post-event surprises remain later source-qualified increments.

**DO_NOT_REDO:** #7925, its R0 prereg, branch/PR, original mechanical example, R1 source discoveries, existing GEX/calibration falsifiers, refused acquisitions/metadata follow-up, or any existing calendar/price/classifier/forecast/state/learning/control plane. Do not turn private receipt recovery into permission to publish raw vendor data or overwrite another operation.

Resume through #7925's single cumulative checkpoint plus the exact new source revision and a fresh compatible Skillpack. The final PR head and two file blobs are recorded there after readback. Principal work remains with Sol; no autonomous execution between turns is claimed.
