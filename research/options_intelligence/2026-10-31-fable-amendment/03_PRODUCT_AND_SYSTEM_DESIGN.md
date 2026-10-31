# Product and system design
## Editable reference for the incumbent Fable team

This is a detailed design proposal over the existing owners. It is not a new schema installation, native Paper edit, replacement component library or frozen UI specification. Fable may improve the layout and implementation when the evidence and user task support it. Existing accepted contracts and narrower source freezes take precedence until their owner records a justified amendment.

### 1. Product shape: one investigation, several evidence lenses

Keep the existing Options Hub, FlowDesk, Exposure, Volatility, shortlist/Plan and saved-investigation entry points. Make transitions preserve the relevant root, source session, expiry/strike, selected object and account context. Do not create a second application shell or an independent Options database to make navigation simpler.

The reader should encounter three layers in order:

1. **Orientation:** selected root and contract, observation/source dates, session state, visible coverage and the current lens.
2. **Investigation:** the tape/table/chart or scenario being examined, with stable selection and meaningful comparison.
3. **Evidence and continuation:** why this object exists, what is unavailable, the source/model assumptions, and the next admitted action.

Keep implementation details in the evidence drawer. A trader needs “Observed through 13:42ET;17 of 20 requested expiries qualified,” not a transport exception, SHA or orchestration run ID in the main flow. Exact digests, revision identities and technical receipts remain available to expert inspection and support.

Suggested primary workspace hierarchy:

| Existing surface | User question | Primary object |
|---|---|---|
| Tape / Statistics | What activity was observed, in which population? | Source-bound event/aggregate |
| Flow inspector | Why is this event notable; what does its side estimate mean? | Exact event and method |
| Exposure / Changes | What does this selected observed/assumed book imply mechanically? | Qualified source lens |
| Volatility | Which like-for-like maturity or event comparison is valid? | Defined tenor/expiry comparison |
| Shortlist / Plan | What would this exact option/strategy do under my assumptions? | Exact contract selection plus authored inputs |
| Saved research | What did I preserve at that revision? | Account-owned immutable investigation revision |
| Watch / Review | What condition did I ask about, and what later evidence exists? | Frozen condition, firing receipt and assessment |
| Candidate / Research | What has this research family actually earned? | Registered candidate/family/version |

The original Paper locators are recorded in [R51](06_EVIDENCE_REGISTER.md#r51). Inspect the relevant existing board when implementing its slice. The optional explorer in this bundle is a supplemental interaction reference; it is not evidence of Paper parity.

### 2. Keep seven meanings distinct

| Semantic layer | Valid meaning | Required distinction |
|---|---|---|
| Flow | Prints, quotes, conditions, timing and measured classifications | Ask/bid location is not opening/closing intent or participant identity |
| Package | Observed linkage or explicit inferred grouping of events | A possible package is not an exchange-confirmed complex trade |
| Positioning | Observed outstanding contracts and derived exposure under a stated sign/book convention | OI is not a directly observed dealer inventory |
| Candidate | Research object formed by the canonical frozen policy | Attention rank is not predictive probability or a trade |
| Outcome | Later observations admitted by a registered evaluation ruler | NBBO evaluation is not a fill; intrinsic scenario is not realized outcome |
| Calibration | Target/horizon/population/version-specific empirical relationship | No universal confidence percentage across families |
| Decision support | Traceable explanation, comparison and governed continuation | Authority must be earned by the underlying family, not by UI composition |

Reuse canonical identifiers across these layers, with explicitly declared joins. Do not make a new campaign key to simplify UI grouping or manufacture a common “confidence” scale to make the cards visually consistent. [R02](06_EVIDENCE_REGISTER.md#r02) [R18–R20](06_EVIDENCE_REGISTER.md#r18)

### 3. Claim class, availability and authority are separate axes

The incumbent D87 ruling adopts four claim classes: **OBSERVED, DERIVED, SCENARIO, FORECAST**. Availability and lifecycle are separate. A realized outcome can be observed; “research” is its authority/lifecycle, not a fifth class. An IV estimate is derived under named assumptions, and becomes part of a scenario when a hypothetical input is varied. [R09](06_EVIDENCE_REGISTER.md#r09)

A conceptual consumer projection should expose the information below through existing fields or adapters. It is not a proposal to add a new universal evidence table.

| Information | Consumer use |
|---|---|
| Canonical source/object/version reference | Link the same object across views and saved revisions |
| Root, option symbol, expiry, exact strike, right | Prevent cross-root/contract substitution |
| Multiplier, deliverable, currency, exercise and settlement terms | Determine which arithmetic and scenarios are supported |
| Event/session time | State when the market event occurred |
| Source snapshot/as-of | State the vintage of the source inputs |
| Published/first-observed/consumer-available times | Establish what was knowable and when |
| Claim class and method/model version | Explain observation versus calculation/assumption |
| Requested/configured/captured/qualified/displayed population | Keep scope and missingness visible |
| Correction/quarantine/reference validity | Preserve provenance while changing effective authority |
| Availability reason | Distinguish empty, stale, unavailable, unsupported and withheld |
| Authority/lifecycle | Explain descriptive, research, evaluated or promoted status |
| Allowed continuation | Open, compare, plan, save, watch or no action under the existing gate |

Do not demand every field from every source and then invent values to satisfy a schema. An unknown source clock should be explicitly unknown and restrict only the claims that require it. Preserve nullable semantics and stable refusal reasons.

Recommended main-view vocabulary:

| State | Reader copy | Permitted behavior |
|---|---|---|
| Successfully observed current population | “Observed through 13:42ET · partial coverage” | Inspect and use only admitted claims |
| Successfully empty population | “No qualifying observations in this scope” | Change filters; no false source-failure claim |
| Older retained source | “Retained snapshot · October 29” | Inspect and compare; do not show live action language |
| Failed source read | “Source could not be read” | Explicit retry/read recovery if owned; preserve previous context separately |
| Unknown qualification | “Qualification unavailable” | Show why the capability cannot yet make the stronger claim |
| Unsupported product/domain | “This contract is outside the supported model” | Preserve identity; offer supported scope or manual research |
| Research held | “Research result not qualified for prediction” | Show methodology/progress, not a fake probability |
| Unknown mutation result | “Save result not yet confirmed” | Reconcile the original operation; no automatic repeat |

Use distinct styling for source health and market direction. In Chinese, directional red/green conventions may differ from English, but health success/failure colors must not acquire opposite meanings. Labels, icons and text must carry the meaning independently of color.

### 4. Tape and Statistics: preserve the denominator

The Tape is a selected publication/event view; Statistics may summarize a broader received population. The October 29 receipt's1,492 published Tape events and SPY791,767 observed prints are therefore not expected to be equal. Display each population name and count alongside the aggregation, and explain the relationship on demand. [R12](06_EVIDENCE_REGISTER.md#r12)

Proposed desktop structure:

- A compact source strip with root/session, source freshness and coverage.
- A filter area for event time, root, expiry/DTE, contract right, size/premium where qualified, condition and classification.
- A stable table with timestamp, exact contract, size, qualified premium or unavailable, quote location/method and short context.
- A resizable detail region that shows source evidence and the user's next admitted action.

On narrow screens, keep the selected event header and essential evidence first. Use compact cards or a horizontally scoped table; do not make the whole page horizontally scroll. Preserve the existing inspector scroll ownership and selected-print placement from W3 instead of reintroducing its repaired clipping problem.

Sorting must be stable for equal timestamps and should not change the underlying observation population. Display filters narrow the result set; they do not improve original source coverage. Show “showingX ofY observed” and separate any eligibility denominator. Premium filters require qualified premium; an unavailable premium does not become zero and slip into the low-premium bucket.

A Statistics panel should distinguish:

- received event count and contracts;
- call/put partitions;
- quote-location/unknown partitions;
- venue/condition partitions;
- source and interval coverage;
- qualified premium and its separate denominator;
- inferred package or aggressor classifications, if admitted.

Partition sums should conserve the intended eligible population. Unknown mass must remain visible. If contract terms are unqualified, count and contract statistics may still be useful while premium stays unavailable. The accepted sample already demonstrates why a99.4% usable-NBBO figure cannot justify a premium total.

### 5. Event and package inspector

A selected event should show the exact original contract identity, source timestamp, observed size/price/quote, condition flags, the method used for side classification, and the limitations of that method. Keep a compact “What this does not establish” explanation near the side interpretation: a repeated print or quote-side estimate does not identify an opening transaction.

Package handling should expose linkage provenance:

- **Source linked:** the provider supplies a qualifying execution/package identity with defined semantics.
- **Inferred grouping:** grouping uses an explicit time/price/size/venue rule and names its uncertainty.
- **Unresolved:** there is insufficient evidence to decide whether legs are related.

The user can expand legs, inspect ratio/side/expiry and compare gross versus net exposures only when leg terms and grouping permit that computation. Missing legs or ambiguous signs prevent a complete strategy-economics claim. Never label a leg group “institutional bullish spread” merely because its notional is large.

Choose package functionality according to actual available data. Cboe's trade-by-trade offering documents explicit execution linkage for its current C1 product, while generic public flow reconstruction has a different evidence level. Buying or installing that source is not part of this plan. [W05](06_EVIDENCE_REGISTER.md#w05)

### 6. Intraday board: truthful timing without a second trigger owner

Preserve the six public lane keys and the existing canonical entry-state owner. A useful additional timing read is forming, active window, already moving, failed/blocked, or unknown. It should describe the canonical snapshot; it must not create a new episode memory or retrospectively invent when a trigger first occurred.

A “ready” presentation requires actual prerequisite evidence, the appropriate canonical timing state and the required live inputs. The known current source problem is that missing washout evidence can be inferred from status text or squeeze alone. Complete the existing 6867 repair and its downstream witnesses. [R28](06_EVIDENCE_REGISTER.md#r28)

Recommended user-facing improvements, subject to incumbent vocabulary decisions:

- Explain the prerequisite behind a lane, not just its name.
- Show a timing reason such as “entry window already opened” or “above the owner's chase boundary.”
- Separate an active pattern from a fresh entry opportunity.
- Suppress affirmative setup claims when timing is unknown or required live reads fail.
- Treat exchange holidays, half days, DST and off-hours through the canonical calendar, not a weekday check alone.
- Keep historical inspection possible with explicitly retained/source-dated context.

The current “Buy now” and “Take profits” language carries stronger action implications than a descriptive confluence badge. Fable should review its admitted meaning with the original owner. Renaming persisted keys or importing an unqualified alpha score is unnecessary; the meaningful task is aligning language, evidence and authority.

### 7. Exposure and change views

Exposure is valuable when users can see which book and assumptions produced the picture. Retain a visible root/session/expiry lens, selected strike and coverage explanation. Distinguish exact measured zero, a covered subtotal, unknown cells, and an unavailable complete total. A partially covered selection must not look like a complete heatmap with blank cells interpreted as zero.

Allow the reader to move among:

1. Current reported/assumed-book exposure.
2. Selected expiry and strike detail.
3. Matched changes between comparable source snapshots.
4. Conditional spot/IV/time scenarios.
5. Source explanation and saved reference.

Preserve the existing R1 sector-origin strip, same-roster semantics, Back/Forward behavior and chart reference. A source lens change must update or clear stale selection rather than apply an old strike to a different root. Return to a changed source should report whether it still matches the saved reference.

Mechanical quantities need explicit units. For a declared signed book with per-unit option delta, the hedge-share target is:

~~~text
B = -sum(position_i × multiplier_i × delta_i)
~~~

For a hypothetical endpoint, the target-trade notional is:

~~~text
H = S* × (B* - B0)
~~~

This is an endpoint change in a hedge target. It is not observed hedge trading, path turnover, portfolio P/L, causal price impact or a change in the market value of a hedge holding. Keep rates, dividends, exercise/model assumptions and unsupported positions visible. [R08](06_EVIDENCE_REGISTER.md#r08)

Do not fabricate a joint strike×expiry distribution from expiry-only totals. In particular, an aggregate Vanna/Charm series cannot justify filtered strike charts without the required joint inputs. Keep the established projection and held prerequisites as the owner; no extra scenario engine is implied.

### 8. Volatility: compare like with like

The user should choose either a real supplied expiry or a clearly named constant tenor. These are different objects.

For supplied expiries, show exact expiry and its source clock. For interpolated tenors, name the interpolation basis, selected maturity and clock convention. An unsupported tenor remains unsupported; nearest supplied fallback must be explicit. Preserve whether the displayed expected move is a source-provided band or a derived model estimate, its horizon, multiplier, as-of and method availability.

The current W3B question demonstrates why the display date and interpolation basis cannot be silently combined: an older source curve plus a today-anchored hypothetical tenor can reverse apparent calendar ordering. Adopt the owner's decision and then qualify the copy or clock; do not assume source as-of is automatically the correct maturity anchor. [R16](06_EVIDENCE_REGISTER.md#r16)

Event context should distinguish a known scheduled event, a versioned observed event timestamp and uncertain/missing calendar data. A chart marker is not permission to create a volatility forecast. Comparison panels should preserve the same root, price basis, annualization and exercise conventions, or clearly declare their incompatibility.

### 9. Exact-contract Plan

Use the incumbent shortlist and Plan editor. A draft begins with an explicitly selected exact contract and blank user assumptions. It must not silently import a stale observed mark as an executable entry. The newer Lab→Plan navigation proposal already follows this pattern and deliberately passes no Matrix payload. [R42](06_EVIDENCE_REGISTER.md#r42)

Recommended structure:

| Area | Content |
|---|---|
| Contract header | Root, exact expiry/strike/right, multiplier/deliverable, term qualification and reference vintage |
| Authored inputs | Buy/sell, required integer quantity, entry premium/debit; current v1 excludes fees and says so explicitly |
| Supported analysis | Expiry intrinsic curve first; richer pre-expiry scenarios only within their qualified model domain |
| Results | Entry cost, finite/unbounded max gain and signed worst outcome in the incumbent convention, exact breakevens, selected spot P/L; preserve the UNBOUNDED sentinel |
| Assumptions | Dated terms, hypothetical entry, settlement basis, unsupported effects and model version |
| Continuation | Save/reopen through IW2 when admitted; otherwise explicit current boundary |

For an eligible same-root, same-expiry strategy, signed quantities and a valid multiplier support the current fee-excluding intrinsic payoff calculation. The explanatory expression is:

~~~text
P/L(S) = sum(n_i × m_i × (intrinsic_i(S) - entry_i))
~~~

Use the existing canonical engine, its exact supported domain and its numerical tests; this equation is an explanatory expression, not replacement code. Current private Plan v1 is explicitly a symbolic expiry intrinsic curve over hypothetical prices. It excludes fees, early exercise, assignment and observed fixing/settlement; it admits only the qualified ordinary SPY/QQQ reference domain. Do not graft OA3's0.65-per-side research cost onto this API. A future cost-aware, other-contract or settlement-aware model needs its own versioned owner contract. OCC's contract-specific exercise/settlement guidance informs that future qualification, not the current curve's authority. [R19](06_EVIDENCE_REGISTER.md#r19) [R34–R36](06_EVIDENCE_REGISTER.md#r34) [W14](06_EVIDENCE_REGISTER.md#w14)

Keep precise contract identity through all transformations. Large or high-precision strikes must preserve the canonical representation or refuse. Display rounding must not change the underlying payoff, breakeven or request identity.

For pre-expiry analysis, expose spot, IV shift units, elapsed time/calendar, rates/dividends, exercise model, surface basis and settlement boundary. Distinguish an absolute percentage-point IV shock from a relative percentage change. Hold baseline inputs fixed for a comparison. No value may be labeled a forecast simply because the user can drag a slider.

A supported-model refusal should be useful: explain which term or model dimension is missing and preserve the draft. Do not fabricate a Black–Scholes price for an American or adjusted contract to keep the chart populated.

### 10. Scenarios, replay and comparisons

Scenario and replay must be visibly different modes:

- **Scenario:** hypothetical inputs applied to a defined source/model state.
- **Replay:** a retained observed state, with its actual source/availability version.
- **Comparison:** two states whose identities and compatibility are explicit.

A scenario slider changes hypothetical inputs, not source age. A replay scrubber selects actual retained frames, not an interpolated invention unless interpolation is explicitly shown as a separate derived object. A current correction does not overwrite what was available at the earlier decision.

When comparing A and B, show which dimensions differ: market source, valuation clock, authored assumptions, model version or selection. If multiple dimensions differ, do not attribute the entire P/L/exposure change to one of them. Matched attribution should follow the existing accepted decomposition and name any residual.

“Restore A” should recover the exact saved assumptions and references. If current source access cannot resolve an old reference, show the saved metadata and an unavailable replay result; do not substitute the latest chain while keeping the old date.

### 11. Durable research and exact account boundaries

Browser-local saved Tape screens are preferences. Account-owned saved investigations are evidence-bearing revisions. Both can coexist, but their durability and sharing promises must be explicit.

Use the existing investigation commands, validators and persistence owner. A saved revision should bind the question/title, selected objects, authored Plan, source reference, model/claim context and continuation intent. Do not embed unrestricted provider raw data into a shareable object merely to make it portable.

Key behaviors:

- A successful Save returns the specific accepted revision.
- A stale expected revision produces a conflict, not silent overwrite.
- An account or selected-investigation change invalidates outstanding results immediately.
- A lost response remains uncertain until the original operation is reconciled.
- Fresh reopen verifies exact source/reference identity.
- A successful exact empty manifest means no saved reference; a failed read means unverifiable.
- Sharing consent is deliberate, and recipient access is rechecked independently.
- Private research responses remain private/no-store across both successful and refused cases.

The current Plan API already uses private no-store headers, authentication, bounded JSON, strict request derivation and strict result admission. Preserve those properties when wiring the final workflow. This source inspection does not certify the entire authentication or RLS system. [R33](06_EVIDENCE_REGISTER.md#r33)

The 1144 preview proposal is an example of the required absence/failure distinction and should be integrated through its incumbent, with separate recipient and live proof where necessary. [R17](06_EVIDENCE_REGISTER.md#r17)

### 12. Watch and Review

A condition watch should freeze an explicit observable predicate, root/contract/source scope, expiry/validity window and associated investigation revision. Keep the existing alert owner, scheduler and notification path. No new agent should become a parallel evaluator.

User-visible states should distinguish draft, armed, paused, expired, unsupported, unavailable and unconfirmed enrollment. An unknown arm result is not safely “off” or safely “on.” The original attempt must be reconciled against its exact identity before another effect is considered.

A firing should link to the exact event/receipt, observed value, source time and delivery provenance. No delivery record found differs from a readable queue showing no delivery. Do not display the latest alert-row stamp as every historical firing's evidence; W3 already repaired that class of mistake.

Review should ask what happened to the stated question, using confirmed, contradicted or inconclusive assessment. Name the firing/revision being reviewed before Save. Keep human assessment separate from a numerical research label. A user saying “confirmed” does not become an outcome training label without the study's own contract. [R13–R15](06_EVIDENCE_REGISTER.md#r13)

### 13. Candidate and research surface

Candidates should carry a clear “research” authority state until qualification permits more. Show:

- formation reason and frozen qualifying campaign;
- exact expression and availability boundary;
- exclusions/abstention reasons;
- later outcome status under its registered ruler;
- family-specific sample/coverage and empirical status;
- what the object can currently support.

Use meaningful absent states such as “policy not activated,” “capture incomplete,” “outcome not mature,” “quote unavailable,” “not evaluable” and “study inconclusive.” Do not collapse them into “low confidence,” which implies a probability estimate exists.

If a probability is eventually admitted, accompany it with target, horizon, population, version, calibration/evaluation window, support, and out-of-domain status. A probability of an underlying excess-return target is not the chance that a particular option trade profits after costs.

### 14. Responsive, accessible and bilingual behavior

Design for actual task order on desktop, tablet and phone; do not simply shrink a desktop table.

| Context | Recommended behavior |
|---|---|
| Desktop around 1440 | Main evidence view plus secondary inspector; persistent selection; locally scoped scrolling |
| Tablet around 820 | Two-stage investigation with collapsible filters and a deliberate inspector panel |
| Phone around 390 | Single task column; selected object identity first; evidence drawer; sticky only where it does not hide controls |
|200% zoom | Reflow without clipped labels, hidden exit actions or page-level horizontal traps |
| Keyboard | Predictable focus, visible focus indication, usable row selection/drawers, restoration on Back/Close |
| Charts | Text/table alternative, accessible selection/value explanation, no color-only diagnosis |
| EN/ZH | Meaning-equivalent copy, complete error/empty states, locale-aware directional conventions |
| Dark/light | Same hierarchy and claim meaning; contrast verified for disabled/unavailable/selected states |

Use existing tokens, typography, spacing and controls. Scope new styles to the owner component so an Options improvement does not invalidate unrelated product surfaces. Preserve existing evidence locks and recapture only changed dependent views with their incumbent tools.

Representative acceptance must cover the actual changed journey across the established 1440/820/390 matrix, EN/ZH and both themes where relevant. Do not multiply screenshots merely to inflate test counts. Use one carefully chosen negative case to prove each meaningful boundary: unavailable source, changed account, mismatched revision, unqualified contract, no events, unknown premium, stale snapshot or ambiguous result.

### 15. Performance and explanation design

A reader needs both responsiveness and truthful freshness. Track independently:

- UI interaction/render latency;
- source acquisition/processing duration;
- publication delay;
- consumer arrival/render time;
- coverage and correction completeness.

A quick screen over old data is not live. A slow source can still support retained research if clearly labeled. Preserve the distinct clocks and establish the product objective from observed usage; do not borrow a research quote-age cutoff or a health threshold as the universal UI SLA.

Virtualize long event lists only if selection, keyboard access and stable sort remain correct. Reuse the canonical stream/cache. Avoid repeated full-provider calls from every lens, component or AI explanation.

Any language-model explanation should summarize the accepted evidence object and name its limitations. It should not calculate authoritative payoff independently, invent opening/closing intent, silently change a source or direct a runtime action. A generated rationale is a presentation of evidence, not an additional measured signal.

### 16. Design exit criteria

The slice is ready when an unfamiliar entitled reader can recover the source, meaning and next action without the designer present; unavailable states remain truthful; account/revision changes cannot leak stale private results; the actual integrated source passes its meaningful checks; and the admitted real journey is verified on the installed revision.

Fable may replace the proposed visual arrangement. The acceptance proposition remains: the user can complete the intended investigation and understand the limits of the evidence.

