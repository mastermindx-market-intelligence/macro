# Risk Warning + Capital Protection Briefing — Product Design Freeze

**Program:** WS:GREY-DEER-RISK-INTELLIGENCE / MAS-258  
**Operation:** grey-deer-warning-crash-recovery-20260927-sol-c1-001  
**Carrier:** Macro PR #8132 / claude/grey-deer-warning-delivery-20260927-sol-c1  
**Protected procedure pin:** Mastermind dcc4829a811d3f6e4fe8c16a103f813c3501f48e, Skillpack v1.0.1 / bootstrap-major 1.  
**Current Macro source read:** f6dae649ee6d32ec65a95ccea411b205d0b0bc45.  
**Design law:** docs/DESIGN_DOCTRINE.md > research/MASTER_PRODUCT_DESIGN_SYSTEM_V1.md.  
**Status:** DESIGN FREEZE for the next warning-delivery implementation wave. No model, probability, capital policy, recovery authority, or production state changes here.

## 1. Outcome

Turn Risk Radar from a passive score/modal into one capital-protection journey:

persistent warning rail -> click/keyboard open -> Capital Protection Briefing -> understand severity + stance -> understand what is breaking -> inspect downside evidence and economic backdrop -> see deterioration/resolution paths -> see recovery without confusing a bounce with an all-clear -> drill into existing Risk Radar evidence.

A user should answer in roughly five seconds: How serious is this? What should I do with risk? Why is the system worried? What would make it worse? What would let the system relax?

## 2. Four independent answers — never fuse them

| Answer | Meaning |
|---|---|
| Economic backdrop | growth/inflation regime and transition |
| Observed market condition | tape, breadth, leadership and stress already visible |
| Forward hazard | calibrated or explicitly uncalibrated likelihood/intensity of further downside |
| Protection / repair | qualified stance/policy and whether recovery is actually confirmed |

A friendly economic regime can coexist with dangerous internals. A falling hazard score is not a bottom call. A score of 99 is intensity, not 99% crash odds. Missing data is never calm.

## 3. Existing owners reused

Reuse engine/risk_radar.py, engine/risk_radar_intl.py, engine/market_state.py, engine/regime.py, engine/risk_envelope.py, engine/risk_radar_recovery.py and the existing Risk Radar dialogs. Reuse the existing global alert rail and PR #8132 display-only warning projection. No second risk engine, event store, scheduler, publication plane, recovery engine or capital-policy plane.

## 4. Persistent warning rail — Tier 1

The rail is a decision strip, not a ticker. For material risk it contains: severity + market scope; one diagnosis line (<=14 English words); one model-stance phrase; up to three top-driver chips; Open briefing; freshness; and acknowledge for critical only. The rail itself opens the briefing by click/Enter/Space.

| Engine state | Rail title | Model stance |
|---|---|---|
| calm | No active warning | Observe |
| watch | Risk watch | Get ready |
| caution | Risk building | Reduce concentration |
| elevated | High market risk | Protect gains / reduce gross |
| risk-off | Critical risk-off | Stand aside / protect capital |
| unavailable | Risk verification unavailable | Do not treat missing data as safety |

These are presentation words over the existing state. They never change state, can_force, ranking, sizing or execution authority.

Critical acknowledgement compacts the rail but never removes it. A new episode/escalation re-expands it. News can never consume the only visible slot while critical risk is active.

## 5. Capital Protection Briefing

Opening the rail reveals one responsive overlay using the existing modal/focus/inert family. Desktop: centered command sheet, max-width about 1180px, max-height about 86vh. Mobile: full-height bottom sheet with sticky header.

The first viewport contains only the decision:

- Header: severity, market scope, as-of/freshness, model stance, close.
- Verdict hero: what changed + why it matters; primary defensive stance; calibrated downside read where lawful; tiny Backdrop, not safety capsule.
- Three-answer strip: Damage now / Further downside / Repair. Word first; at most one figure each.
- Top three drivers.
- Capital-protection guidance.
- Deterioration path and Resolution path.

Everything deeper is progressive disclosure.

## 6. What is breaking

Use six diagnostic families, not six invented scores. Each renders source-native state + trend + evidence freshness; draw a normalized bar only if a lawful normalized measure exists:

1. Breadth & participation
2. Leadership
3. Credit & banks
4. Rates & liquidity
5. Volatility & positioning
6. Global transmission

Each row answers: What are we seeing? Is it worsening/stable/repairing? Why does it matter? Is evidence fresh?

## 7. Further-downside outlook

US uses existing H5/H10/H21 Risk Radar probabilities and base H21 when currently lawful. Always name target/horizon, e.g. >=5% SPY pullback within 21 sessions, and show normal/base beside current. Display as a risk runway (Now -> 5 -> 10 -> 21), not a theatrical gauge.

International markets show their own currently permitted calibrated probability only where the native market Radar supports it. Otherwise: Directional hazard only — probability not established. Never import US probabilities into another country.

## 8. Economic backdrop

Show regime quadrant, transition, growth score, inflation score, Market State score/verdict and its existing component scores when available. Keep this subordinate to market damage/hazard.

Required contradiction copy when applicable: **Reflation does not mean the tape is safe. The economic backdrop and market damage are different reads.** No economic score silently overrides the warning.

## 9. Capital-protection guidance

State-derived display guidance may say: reduce concentration in weak exposure; avoid aggressive new adds during elevated risk; reduce gross/leverage when the qualified Risk Radar state calls for de-risking; keep liquidity/optionality; do not chase the first bounce while recovery is unconfirmed.

Exact exposure targets appear only from an existing qualified policy owner. Otherwise say: **No exact exposure target is validated. The current stance is defensive, not an automatic all-cash instruction.** Preserve DEC:AUTO-EXIT-NOT-IN-GREY-DEER-V1 and current country-specific evidence ceilings.

## 10. Deterioration and resolution pathways

Show mirrored paths with each condition labelled Observed / Near / Not active / Unavailable.

**Deterioration examples:** breadth/new lows expand; former leaders fail support; credit/bank stress broadens; rates/funding pressure rises into weak equities; more regions move high/risk-off; volatility/liquidity becomes disorderly.

**Resolution examples:** breadth stabilizes then broadens; leaders stop making new damage and begin repair; credit/funding stabilizes; market-local liquidity turns supportive; volatility veto clears; downside retest holds with better participation.

The UI cannot self-clear a signal. Only the existing engine/recovery owner changes the underlying risk/recovery state.

## 11. Recovery watch

Presentation ladder: NO_REPAIR -> STABILIZING -> EARLY_REPAIR -> CONFIRMED_REPAIR -> FAILED_REPAIR. Use only labels supported by the existing recovery owner; otherwise show Unestablished.

At rest show: what improved; what is still missing; volatility veto; liquidity/internals confirmation; whether any qualified policy authorizes re-entry. Never print all clear merely because risk intensity falls.

## 12. What changed since the prior warning

Where an existing prior artifact allows it, show severity change, top-driver change, new market joining deterioration, leadership health change, repair failure/advance, and source staleness. Do not create a new event ledger. Hide this section if no lawful prior snapshot exists.

## 13. Visual direction

### Dark — night watch command center

Graphite canvas, panel/panel2 luminance depth, hairline borders and one restrained health-red aura around the severity capsule only. No flashing text or strobe. Use one slow onset sweep and a restrained breathing ring around the warning icon; acknowledgement stops motion but not the warning. Driver chips are mostly achromatic; red stays reserved for active severity.

### Light — institutional risk memo

Cool canvas, white sheet, hairline structure and restrained shadow. Red appears as severity ink/rail/small chips, not a pink page. This is a distinct art direction, not dark CSS with swapped colors.

### Grey Deer signature

One quiet radar-ripple / ear-to-ground motif in the header and path visuals. Approaching/receding tracks can encode deterioration/repair. No mascot/cartoon deer on the trading surface.

## 14. Layout

Desktop critical rail: roughly 64–76px expanded, 48–56px acknowledged. Briefing ~1180px wide. First viewport: severity/stance/why/downside/repair plus Why now, Capital protection, Deterioration path and Resolution path.

Mobile 390: rail stacks severity + one diagnosis + Open briefing. Briefing becomes full-height sheet. First screen must still contain severity, stance, one reason, downside level and repair state. No squeezed tables. Minimum existing control floor 40px; prefer 44px.

## 15. Additive display contract

Extend PR #8132 with mastermind.risk_warning_briefing/v1 carrying: severity; stance; summary; downside; backdrop; drivers; deterioration_path; resolution_path; recovery; changed_since_prior; freshness; and authority. Financial states are computed server-side by existing owners/adapters, never in the browser. Authority stays display_only=true and may_execute/may_size/may_gate/may_rank=false unless an existing separately qualified policy is explicitly embedded as evidence.

## 16. Failure and permission states

- Loading: retain last verified severe rail if available; Checking current risk…
- Stale: last verified state + stale badge; no silent severity reduction.
- Network failure: retain last verified severe warning + verification unavailable.
- Future/malformed: fail closed; no all-clear.
- Partial country coverage: N of M markets current; list unavailable markets.
- Restricted evidence: disclose restriction; do not substitute weaker public data as equivalent.
- No prior warning: unavailable, never calm.

## 17. Interaction/accessibility

Banner is named as an interactive risk region/control; acknowledge is separate. Dialog uses the existing focus trap/inert family. Escape closes briefing but never clears warning; focus returns to the banner trigger. Escalation gets one polite announcement, not one announcement per refresh. Severity has text/icon, not color alone. Reduced motion removes sweep/breathing. EN/ZH parity is mandatory. Severity red never flips under red-up/green-down localization because it represents health, not price direction.

## 18. Design-system rules

Use global tokens only. No new root palette. Health/severity uses warn/act family; action/wayfinding uses link/info; no violet risk data; nesting depth <=2. Production implementation must move material banner styling out of runtime JS style.textContent into governed CSS/template source rather than expanding that legacy debt. Dark and light receive separate visual review.

## 19. Implementation sequence

**W2A — Briefing projection:** deterministic view-model composition over existing owners. Fixtures: US caution-80, US critical, China directional-only, stale/missing, recovery-forming, Reflation + deteriorating tape.

**W2B — Premium rail:** governed CSS/markup consumes warning projection; preserve legacy alert meaning for operator-exposure consumers.

**W2C — Briefing shell:** upgrade/reuse existing Risk Radar modal, not a second modal framework. Hero + drivers + stance + downside + deterioration/resolution paths.

**W2D — Deep modules:** diagnostic families, economic backdrop, recovery, changed-since-prior, evidence.

**W2E — Multi-market/cross-product:** market-local clocks and entitlements; country and Terminal consumers; no second publication plane.

**W2F — Production acceptance:** owning CI, independent semantic/visual review, canonical render/origin hash, authenticated real-page journey, long-open refresh/failure proof.

## 20. Acceptance attacks

- US caution/80 is visible as Risk building, not silence and not Critical.
- Ungated risk-off cannot bypass gated caution.
- China 99/risk-off cannot be printed as 99% crash odds.
- Reflation + broken breadth/leadership explicitly shows the contradiction.
- Missing/stale refresh cannot clear a prior severe warning.
- Critical remains after acknowledge and after Escape-closing the briefing.
- News cannot occupy the only visible slot during critical risk.
- Falling intensity cannot print safe without recovery-owner confirmation.
- A policy announcement alone cannot clear liquidity stress unless effective evidence exists.
- Market-local recovery evidence cannot be imported across countries.
- Missing country coverage cannot disappear.
- Light theme is not a red-tinted dark sheet.
- ZH severity does not flip with market-direction red/green semantics.
- 390px first viewport contains severity + stance + why + downside + repair with no horizontal scroll.
- No new financial model score, capital authority, event ledger or browser-computed financial state appears.

## 21. Visual acceptance bar

The design passes when a cold user can answer **What is wrong? How serious is it? What should I do with risk? What would make it worse? What would let me relax?** in roughly five seconds without opening methodology.

The aesthetic target is an **institutional emergency memo that happens to be alive**: calm, decisive and beautiful because it compresses complexity rather than decorating it.