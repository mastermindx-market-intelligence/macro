# R31 depth, flow and continuity contracts

Status: native design and behavior specified; runtime integration remains pending. This extends the accepted R30 journey without adding a top-level product route. Read this document with the original implementation contract; R31 resolves the source-owner questions described there and takes precedence where an availability or persistence boundary differs.

## Product decisions

The default desk continues to answer three questions: what changed, what it means, and what to inspect next. Advanced tools open only when a decision needs them. They return to the same question, selected instrument, buyer perspective, horizon and evidence cutoff.

R31 adds I13 Market structure, I14 Buyer flows and I15 Save + compare. I02 gains nonparallel curve shocks. I05 gains a reported obligation calendar, a separate synthetic cash scenario, a complete cash-event table, draw eligibility and payment-cutoff states. These are tools and implementation specimens, not additional daily navigation destinations.

Native references:
- S06: 6B6Q-1 on Bonds p-1H-0.
- S07: 6C1S-1 on Cross-Asset p-1E-0.
- I13: 6B78-1; I02 shape: 6BZN-1.
- I05 reported: 6BMD-1; synthetic cash: 6BRC-1; cash events: 6E28-1.
- I14 transaction lens: 6C2T-1; funding pipes: 6CZY-1.
- I15 review: 6CEV-1; comparison: 6CLB-1.
- Mobile detail gallery: 6EHM-1, with phone roots 6E6G-1, 6E7X-1 and 6E8U-1.

## I13 — Market structure

**Decision:** “Rebound. Reversal unconfirmed.” A five-session gain can coexist with a weaker twenty-session trend and uneven participation across the curve.

Entry points are Curve → Inspect structure and Transmission evidence → Price structure. The tool retains the invoking route and focus target. Its default contains one yield chart, three meaningful numbers, a three-horizon return strip, curve participation and one next action.

The series selector must retain the economic instrument and basis: a constant-maturity yield estimate, a specific bond, a total-return basket and a futures contract are not interchangeable. Switching to returns explicitly changes the chart measure and unit. Futures rolls and basket changes require their declared adjustment method. Incompatible series block a comparison rather than silently resampling it.

The illustrative current yield is 5.10%, with a close-based test below 5.08% and invalidation above 5.22%. A current intraday touch is provisional. Evaluate unrounded values; 5.079% crosses a 5.080% boundary even if both would ordinarily display as 5.08%. Reveal sufficient precision around a threshold.

Volatility distance uses the sample standard deviation of twenty daily yield changes ending at the prior close. The input requires twenty-one aligned prior closes; the current move is excluded. The example volatility is 8 bp. Signed distances are −0.25 daily-volatility units to confirmation and +1.50 to invalidation. The glance can show the absolute 0.25× distance with the direction described in words. This is neither a probability nor a multi-day forecast interval.

Total-return comparison uses the same close calendar and horizon. The five-day long-minus-short difference is +0.90 percentage points; the twenty-day difference is −1.30 percentage points. A relative wealth index instead uses the return ratio and must not label its result “percentage points.” Price, momentum, relative performance and the threshold often reuse the same observations; they do not supply independent votes.

### I13 controls and states

| Control/state | Behavior |
| --- | --- |
| Rule settings | Opens 6BDP-1. Default Close break; optional authored Break + retest. |
| Break + retest example | Close below 5.08%; within three following sessions a close enters 5.06–5.08%; the next close is lower than the retest close and remains below 5.08%. |
| Apply to draft | Changes the local scenario revision draft. It does not arm monitoring or overwrite a retained revision. |
| Use these conditions | Carries the exact series basis, levels, clock and rule parameters to the existing case workspace. Saving follows I15. |
| Insufficient/zero-variance history | 6BE8-1. Normalized distance is unavailable. A valid raw 2 bp distance can remain visible. |
| Stale or incompatible inputs | Preserve the last observed value with its clock; clear the dependent normalized output and explain the missing requirement. |
| Selected close completes | Re-evaluate the frozen rule against eligible observations. Price invalidation remains distinct from the compound I04 monitor. |

A changed threshold, band, horizon or method is a new draft and, when supported, a new explicit retained revision. Do not retroactively rewrite earlier rule outcomes.

## I02 — Curve-shape extension

Entry points: Scenario → Curve shape and Curve → Shock settings. The existing parallel calculation remains available. Shape mode requires a complete compatible key-rate duration vector, not merely a single modified-duration number.

The illustrative nodes are 2Y, 5Y, 10Y and 30Y. Their durations are 0.2, 1.1, 5.2 and 1.3 years; shocks are −15, −10, +5 and +12 bp. First-order contributions are +0.030%, +0.110%, −0.260% and −0.156%, totaling −0.276% (display −0.28%).

Bind the sensitivity to position, valuation cutoff, curve type, node tenor, bump/interpolation method and coverage. Shocks from a different curve representation cannot silently consume this vector. Missing nodes or incompatible methods leave Shape unavailable and allow only independently supported modes.

The result is estimated price effect. Keep benchmark shocks separate from credit-spread shocks. First order excludes convexity, carry, roll, credit spread and FX. A scalar convexity estimate is not a general cross-tenor convexity matrix. Instrument repricing is a separate supported calculation mode, not a cosmetically renamed duration result.

“Apply shape” returns the scenario draft to the existing workspace. It performs no trade, notification, probability inference or saved revision mutation.

## I05 — Financing and cash timing

### Reported obligations

The CoreWeave panel is a June 30, 2026 reported consolidated USD snapshot. It displays annual principal buckets and explicitly marks daily timing and cash coverage incomplete. It does not claim current financing capacity or an actual January funding deficit.

“Open filing” opens the exact source. “Inspect obligations” keeps the selected issuer, liable entity, currency, date precision and obligation type. Principal, interest, leases, vendor commitments and contingent obligations remain separately typed. Current-debt carrying values are not substituted for contractual payment dates.

“Build cash scenario” retains the actual selected issuer and opens a setup/coverage review. It must not automatically populate the separate Parent A fixture. With the reported annual-only inputs shown, the coverage state is 6BVT-1: request dated obligations, legal cash pools and a facility rollforward. The exact-date Parent A view is a separate design example, not inferred CoreWeave data.

### Synthetic cash scenario

The Parent A example is explicitly synthetic, USD millions, October 16, 2026–January 15, 2027. Opening account balances are $3,000m; $900m restricted cash is excluded; usable opening cash is $2,100m. The selected $300m operating buffer is an analytical assumption.

For this complete stated fixture, the minimum scheduled cash is −$190m. Financing needed to cover obligations is $190m; financing to preserve the selected buffer is $490m. These are different outcomes.

The facility inspector shows commitment less drawn funds and capacity-consuming letters of credit, capped by the remaining borrowing base. Its $900m net usable proceeds assume the correct borrower, permitted purpose, active draw window, eligibility conditions and settlement timing. In-horizon draw fees and interest cash payments are explicitly zero in this fixture. Production schedules must include nonzero fees and interest when due.

A pre-cutoff draw produces $710m ending cash and $410m buffer headroom. Moving the assumed $200m operating receipt beyond the payment date lowers these to $510m and $210m. These sensitivities do not assert the probability of either event.

### I05 controls and states

| Control/state | Native reference and behavior |
| --- | --- |
| All cash events | 6E28-1. Read the complete base fixture, with opening balance initialized once and each event typed as obligation or assumption. |
| Select an event | Existing evidence/detail inspector: legal obligor, cash pool, source locator, amount semantics, date precision, settlement cutoff and amendment/rollforward. |
| Edit/Delay receipt timing | Changes only the assumed receipt date in the local scenario, then recomputes balances and both financing requirements. |
| Draw eligibility | 6BUK-1. Show gross/net capacity semantics, restrictions, expiry and any unresolved condition. Never subtract letters of credit twice. |
| Use this scenario | Returns the local draft; retaining it requires the owner extension described in I15. |
| Annual or trigger-dependent dates | Preserve interval/trigger precision. Do not manufacture an exact pressure date. |
| Unknown legal transfer or coverage | Mark timing/coverage incomplete. Consolidated cash cannot silently fund every subsidiary. |
| Late draw | 6E47-1. $190m remains unfunded at the 09:00 cutoff even though the 16:00 draw restores projected cash to $710m after scheduled overdue obligations are paid. |
| Late-draw interpretation | The projection does not prove an overdraft, timely payment or the amount of a legally defined default. Payment ordering and partial-settlement permissions can matter. |

Deduplicate the economic cash event across facilities, leases, vendor financing, capex and customer receipts. Include contingent guarantees as conditional obligations with their liable entity and trigger. Preserve source amendments rather than silently replacing the original reported terms.

## I14 — Buyer flows and funding pipes

Entry points: Capital → Inspect buyer flows; Transmission → Capital substitution → Buyer flows. Buyer eligibility reuses the existing matched buyer/hedge perspective. The interface keeps holder scope, asset scope, currency, period, valuation basis and release clock visible.

The reconciliation is change in market-value holdings = net transactions + price revaluation + FX effects + other changes. In the synthetic matched-holder example, Treasury holdings rise $5bn, consisting of $2bn purchases and $3bn revaluation. AI-credit holdings fall $3bn despite $1bn net purchases and −$4bn revaluation. FX/other are explicitly assumed zero; they are not missing observations.

Both net purchases can be positive while gross sales also occur. These totals do not establish a financing route between the assets. Sourced transactions and residual estimates have different labels. Unknown valuation or other-change components remain unexplained; they do not automatically become measured flows.

### I14 controls and states

| Control/state | Behavior |
| --- | --- |
| Buyer group / period | Requery the same typed reporting scope; show coverage and release date. Do not combine unmatched groups or periods. |
| Buyer eligibility | Reuse mandate, currency, hedge, duration and instrument-eligibility controls. |
| Funding pipes | 6CZY-1. Qualitative financing-demand/cash-supply view with no measured-volume arrow widths. |
| Test funding stress | Opens the existing scenario/funding counterpath. It does not assign an automatic price coefficient or probability. |
| Add evidence to case | Adds to the local draft; I15 discloses whether the current owner can retain the reference. |
| Missing transactions/revaluation | Display unknown components and any reconciliation residual. Label a calculated estimate explicitly. |
| Quarterly data on a daily question | Show period and publication lag; do not present interpolated observations as today's measured switch. |
| Mobile | One asset reconciliation card at a time; labeled amounts replace a compressed five-column table. A text table remains available. |

The funding diagram distinguishes coupon-related dealer financing demand from bill alternatives that can affect money-fund repo lending. Confirmation needs contemporaneous funding measures and market depth, with slower dealer/holder releases shown at their native frequency. Aggregate reserves alone do not measure cash actually lent into repo.

## I15 — Retained research and change review

The current owner is Terminal Investigation v2. The planned complete case state and the narrower source-inspected admission contract must stay distinct.

The save review (6CEV-1) lists supported and excluded contents before submission. The current service admits specified security/issuer subject owners and Earnings workspace evidence; it does not yet retain these bond evidence or scenario payloads. The “question-only” specimen applies only when the supported intent/continuation and any selected subject references pass the existing owner. An unsupported identity or an unavailable service does not receive a success state.

The user can explicitly save the question and next check or keep working locally. Do not serialize unsupported charts, rules or scenario JSON into free text to evade admission. A local draft is not a cloud-saved complete case.

Partial success is “Question saved” (6EHS-1), with “Scenario values, charts and monitor conditions were not saved.” Reopening must keep this boundary visible. A successful mutation receipt can coexist with exact-revision read unavailability (6CML-1). Retry the exact read; do not quietly substitute latest.

The full-case comparison (6CLB-1) is a synthetic future-capability state. It keeps saved revision 3 and latest close in separate columns. A new observation updates the comparison without rewriting history. The displayed breadth count is not a substitute for the I04 peer-basket mean spread condition.

### I15 controls and states

| Control/state | Behavior |
| --- | --- |
| Save question only | Submit admitted intent/continuation through the existing Investigation command and normal authentication; explicitly disclose exclusions. |
| Keep working / Back | Preserve local draft, selected evidence and invoking context; perform no retained-state mutation. |
| View revision N | Exact revision read. Missing/read failure cannot fall through to latest. |
| Create new revision | Review changes and submit against expected revision. Unsupported payload remains blocked. |
| Concurrent update | 6E4N-1. Keep the local draft and show the newer saved revision. Review before explicit rebase/new revision; no overwrite. |
| Uncertain mutation | Resolve the original operation receipt. A missing receipt is not permission to mint a new operation ID. |
| Same operation, changed payload | Treat as conflict; do not retry as the same mutation. |
| Compound monitor | Existing Alerts owner does not currently admit arbitrary yield + credit + funding AND conditions. Keep unavailable until the complete rule is supported. |
| Alert fallback | Do not split the compound rule into independent alerts and claim equivalent behavior. |

## Accessibility and responsive behavior

Existing R30 shared navigation, search, focusable tooltips, dialogs, source inspectors and save/undo patterns remain the component owners. New tool sheets use the same close/back behavior. At mobile widths, keep the case title and a 44px close target visible, place the main choice in the reachable footer and expose chart values as a text table.

A modal traps focus; a nonmodal detail route does not. Escape and close return focus to the invoking control. Preserve scroll and selection when returning. Form labels carry units. Invalid/missing inputs clear dependent calculations. Color is supplemented by labels and signs; translations preserve measure and condition meaning. The optional Chinese dark reference uses existing graphite tokens; the primary product remains the Mastermind light style.

Native JSX is editable reference markup, not a running application. Runtime components must reuse current owners and the accepted illustration/chart stack. These specimens do not constitute accessibility execution tests, data integration, active alerts or empirical forecast qualification.
