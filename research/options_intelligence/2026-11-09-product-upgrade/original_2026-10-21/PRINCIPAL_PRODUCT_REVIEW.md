> Supporting principal review recorded during the audit. Read PRINCIPAL_REVIEW_RESOLUTION.md and the corrected masterplan/task register for the adopted final proposal. This is not production or scientific acceptance.

# Terminal Options product architecture review
Date: 2026-10-21
Role: principal product and experience judgment supporting the parent audit. These are recommendations, not implementation, production acceptance, or a claim that competitor parity has been attained.

## Recommendation

Make Terminal Options one continuous decision workflow: understand the market, discover a candidate, test the thesis, compare option structures, and monitor what changed. The distinguishing product should be the quality and continuity of that workflow, supported by unusually rich research tools. A large widget catalog or dramatic 3D scene does not establish usefulness.

The product promise should be: **Within a short, repeatable workflow, a user can understand what is happening, what the evidence supports, which risks matter, which option structures fit a stated thesis, and what would invalidate the decision.** Expert users can inspect and reproduce the calculation. New users can reach the same evidence without first learning the entire derivatives vocabulary.

Treat this as a product target. No existing source inspected here proves it is achieved.

## Observed evidence that changes the plan

1. The July 24 Options Suite Parity Masterplan contains a substantial historical QuantData feature catalog, but its current-state section includes claims such as no SSE and no replay. Current OptionsHubView imports useFlowStream and separate lazy desk components. The July plan is useful lineage, not a fresh inventory. The parent audit must reconcile capability by capability. [P1, P5]
2. The current Research Lab implementation contract explicitly states MISSION_COMPLETE false. It describes an implemented Chain consumer, raw published IV, selection/comparison behavior and entitlement withdrawal; Replay, package and scenario inputs remain unavailable, and Save remains disabled. These missing workflows are central to the user’s objective. [P2]
3. The Lab has valuable bounded work worth preserving: exact tables alongside 3D, stable scales, source-session validation, null/zero distinctions, demand-driven rendering, account withdrawal, mobile table default, light/dark and bilingual appearance. The same documents explicitly separate local fixture and native presentation proof from independent and authenticated production acceptance. [P2, P3]
4. The options companion already specifies a reusable matrix, one financial formula owner, source-aware perspectives, explicit chart pinning and a mobile sheet instead of compressing the chart. Those are good integration constraints for a redesigned suite. [P4]
5. OptionsHubView at the pinned source is 4,931 lines / 261,076 characters and declares 16 tab keys. This is a source-organization observation, not proof that all 16 are visible top-level navigation in production. The file mixes extensive feed types, selectors, charts and display logic; extracting coherent feature boundaries is warranted, but a rewrite should preserve accepted behavior and route aliases. [P5]

## Proposed information architecture

Use five user destinations under the existing Terminal shell. Preserve direct links and expert shortcuts; translate old tabs into lenses, saved presets, and focused workspaces.

| Destination | Question answered | Main content and completion action |
|---|---|---|
| Market Brief | What changed, and where is risk concentrated? | Market/session state, meaningful changes, positioning/volatility regimes, catalyst calendar, a short actionable research queue; open a scoped investigation. |
| Opportunities / Prophet | Which candidates deserve attention, for which thesis and horizon? | Options-originated and stock-originated lanes with distinct provenance, configurable screens, qualified candidates, explicit watch/avoid/abstain states; compare or investigate. |
| Workbench | Does the evidence support this idea? | A persistent symbol/contract investigation with Price & Flow, Positioning, Volatility, Chain and History lenses; linked views, source detail, saved investigation and replay. |
| Trade Lab | Which structure expresses the thesis with acceptable risks? | Structure comparison, payoff and pre-expiry scenarios, liquidity/cost checks, event risks, risk-budget comparison; save a research plan or export through an existing authorized workflow. |
| Monitor | What changed after I saved the plan or position? | Watchlists, scenario/level/catalyst alerts, plan invalidation, portfolio exposure and review of outcomes; resolve or revisit a decision. |

This is a proposal to test, not a requirement to replace existing global Terminal navigation. A skilled user must still jump directly to tape, an exposure map, volatility surface, a contract, or replay without traversing a beginner funnel.

“Research Lab” should become a Workbench presentation/lens, with 2D and 3D alternatives over the same selected data. It should not be an isolated product with a different clock, selection system, identity model or save mechanism.

### Mapping principle for existing surfaces

- Tape, largest events, 0DTE and screener become named views/presets with one filter model and clear coverage.
- Session tide and flow desk are linked Price & Flow panels.
- GEX, exposure matrices, positioning mechanics and levels become linked Positioning views, retaining distinct measured/modelled semantics.
- Volatility remains a complete lens: smile, skew, term structure, volatility history and event context.
- OI structure and exact contracts belong to Chain, with change/history accessible in place.
- Macro Plans and Options Alpha remain visibly distinct source lanes in Prophet until their separate evidence supports any qualified integration.
- Leaders and Radar must justify distinct user jobs; if they are alternate sorts of the same universe they should be presets, not duplicate destinations.
- Saved investigations, pinned contracts, alerts and outcomes should continue through existing shared owners.

## The five essential journeys

### 1. First-time market orientation

A new user arrives at a useful brief, chooses horizon and risk budget if needed, and reads a small number of plain-language findings. Each finding says what changed, why it could matter, what evidence supports it, and where uncertainty lies. A clear next action opens the exact relevant context.

The entry screen should answer five questions before it asks the user to learn abbreviations:
1. What market/session am I looking at?
2. What changed materially?
3. Is the information current enough for this purpose?
4. Which names or risks deserve investigation?
5. What should I inspect next?

The interface should make “wait” and “insufficient evidence” useful outcomes. It must not fill an empty research queue with weaker ideas merely to make the product appear active.

### 2. Candidate to decision

A Prophet candidate opens an investigation with the symbol, horizon, trigger, evidence snapshot, selected contracts and scenario assumptions intact. The user can compare the candidate with an explicit alternative, including holding the underlying or doing nothing where relevant.

The candidate’s first screen should contain:
- the thesis and horizon;
- why it appeared now;
- the strongest supporting evidence and strongest contradiction;
- trigger and invalidation conditions;
- the kind of exposure being considered;
- liquidity/cost qualification;
- a concise risk statement and source-age summary.

Do not present a single “confidence” percentage unless its meaning and calibration are established. Keep model confidence, source quality, evidence agreement, liquidity and uncertainty separate. A composite score may aid ordering only after its incremental utility and calibration are demonstrated.

### 3. Expert forensic investigation

An expert can select an unusual event, see its exact contract and contemporaneous price/quote context, inspect whether it is part of a package or correction, and compare the option evidence with underlying price, volume, off-exchange observations, positioning estimates and catalysts.

Linked crosshairs and selection should move across panels where the source clocks actually permit it. Incompatible snapshots stay visibly separate. A time-slider should never make an EOD estimate look intraday.

Each chart must answer a named question; its default filters should express a useful task, not merely plot every available point. The exact numerical table remains available for inspection and export.

### 4. Thesis to option structure

Trade Lab starts from a thesis rather than a strategy-name glossary: expected direction or range, horizon, volatility view, catalyst, maximum acceptable loss, and practical liquidity limits.

It compares eligible structures against explicit scenarios, including adverse spot, volatility, time and event paths. The user sees total premium, estimated costs, payoff limitations, relevant exercise/assignment/settlement conditions and what changes before expiry. An expiration payoff diagram must not be mistaken for current liquidation value.

New users receive progressive explanations next to the decision they change. Advanced users can inspect legs, inputs, model assumptions and sensitivity surfaces. Both modes use the same underlying computation.

“Asymmetric” should have an operational definition in the product: stated bounded loss and favorable payoff under specified scenarios, accompanied by likelihood uncertainty and costs. A large maximum payout alone does not earn the label.

### 5. Research plan to ongoing monitoring

Saving must preserve the actual investigation, not just today’s ticker. It records source references, data/model version, time context, thesis, triggers, option structure and selected assumptions through the existing persistence owner.

The monitor explains changes since the saved state: a level crossed, volatility changed, a catalyst passed, data became unavailable, liquidity deteriorated, a thesis was contradicted, or a plan expired. Alerts link to the exact affected evidence and retain the user’s context.

Outcomes distinguish signal quality, underlying movement, option theoretical marks, feasible trade marks and realized activity. The interface should make the limitations understandable without burying the user in operational receipts.

## Visual structure and proportions

These are initial design targets to validate in real tasks.

### Desktop

- The analytical stage occupies roughly 65–75% of the available content width, with a collapsible 25–35% inspector. A 300–380px inspector is a starting range, not a universal fixed rail.
- Keep one primary visualization at a time, plus two or three supporting views. Users can choose expert multi-panel layouts. Do not force six equally prominent cards above the fold.
- Preserve a compact persistent context bar for symbol, session/time mode, horizon and source state. Place specialized controls with the chart they affect.
- Summary content should be short enough to leave the primary chart visible at normal laptop dimensions. Details expand in context.
- Separate navigation, research filters, chart controls and decision actions by role and location. A new toolbar for each feature creates avoidable cognitive load.
- Tables should use readable tabular numbers, stable column widths, sticky identifiers, purposeful density presets and virtualization where needed.

### Mobile and magnification

- Use a single primary task and exact table or simplified 2D view by default. Offer expert detail without pretending a shrunken desktop is usable.
- Move inspectors into a sheet with clear return behavior. Preserve the selected symbol, contract and time.
- Give touch actions a generous target (44px is a proposed design target); test keyboard access and 200% magnification.
- Do not make essential labels, units or source state hover-only.
- Bilingual strings must be tested as actual layouts, including long labels and numerical units.

### Chart semantics

- Use one consistent color grammar across the suite. Direction, call/put, signed exposure, selection and warning are different concepts.
- Show units on axes and values. Preserve scale across comparisons by default; explicitly signal local normalization.
- Distinguish missing, zero and out-of-coverage visually and in the table.
- Make a selection conspicuous using more than color.
- Provide useful reset, back, undo-selection and compare behaviors.
- Show simplified evidence detail on demand rather than covering every chart with administrative text.

### 3D has to earn its screen space

Require a comparative task study. Test whether 3D improves identification of clusters, strike/expiry relationships or scenario structure relative to a well-designed 2D heatmap and table. Measure correct answers, completion time, navigation errors and confidence calibration.

If it wins only for a specialist task, offer it for that task. If it does not win, retain it as an optional exploratory view or retire it. “Looks sophisticated” is not an acceptance criterion.

## Usefulness and acceptance gates

Do not collapse these into one green readiness label.

| Gate | Proposed evidence |
|---|---|
| Understandability | New users correctly explain the main finding, data age, modeled versus observed status, maximum loss and invalidation in moderated tasks. |
| Task completion | At least 90% successful completion of the core journeys in each declared persona/locale/device cohort; report cohort denominators and critical errors separately. |
| Speed | Proposed target: first useful market assessment in 90 seconds; candidate-to-risk comparison in 3 minutes; expert access to exact evidence in at most two deliberate transitions. Measure rather than assume. |
| Decision quality | Compare against the current product and a simpler baseline using blinded, prewritten market cases. The new suite must reduce material interpretation errors, not just clicks. |
| Data truth | Root/contract/time/units/coverage/corrections/permission boundaries hold on actual supported paths. Synthetic proofs and live receipts remain distinct. |
| Quantitative utility | Every promoted model or confluence passes the parent quantitative program’s independent out-of-sample and forward tests, costs, calibration and incremental-value tests. |
| Visual usability | Real task observation at laptop, large desktop, tablet and phone sizes; dark/light, EN/ZH, keyboard and magnification; no clipped critical actions or misleading chart geometry. |
| Performance | Budget by real interaction and source load; p95/p99 latency and rendering stalls, memory, background work, re-entry and cleanup, with target devices declared. |
| Continuity | Candidate -> investigation -> structure -> saved plan -> alert -> outcome preserves exact context and entitlement behavior. |
| Production | Authenticated ordinary user paths, real data freshness, recovery, alert delivery, correction and release/rollback proof through the existing release owners. |

Suggested anti-theater rules:
- Passing screenshot tests does not prove useful hierarchy.
- A new source wrapper does not prove current coverage.
- A live connection icon does not prove live content.
- A warning-filled surface does not count as a completed workflow.
- A broad feature checklist does not count as parity until named user tasks succeed.
- A model that sounds plausible does not earn predictive or trading authority.
- A beautiful view with no comparative task advantage does not earn primary navigation.

## Program decisions for Fable

1. Freeze the five core journeys and testable north star before expanding the widget inventory.
2. Reconcile the exact three incumbent program roots, PRs, source custody and unresolved effects. The current user supports consolidation; stale or sleeping appearance is not runtime proof.
3. Preserve accepted source-semantic, accessibility, replay and selection work. Rebuild composition and workflows where evidence justifies it.
4. Give one Opus product/experience supervisor responsibility for the integrated journey across domains, not only individual pages. Pair with independent usefulness review.
5. Build one complete vertical slice: market finding -> options-originated candidate -> evidence -> structure comparison -> saved plan -> changed-state alert. Use real qualified inputs and one bounded universe.
6. Expand data/feature breadth in parallel only where it does not undermine the slice’s shared contracts.
7. Promote each capability separately. The integrated product remains incomplete until the journeys work together under ordinary production conditions.
8. Keep the ambitious research backlog—surface modeling, robust dealer scenarios, flow reconstruction, event studies, richer package intelligence—tied to concrete user questions and measurable incremental value.

## Source references

- P1: [Options Suite Parity Masterplan](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/d9ec4d2b86e9e9e0129d7fcd4c646f25f7670c49/docs/OPTIONS_SUITE_PARITY_MASTERPLAN.md), historical July24 assessment.
- P2: [Research Lab implementation frontier](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/d9ec4d2b86e9e9e0129d7fcd4c646f25f7670c49/docs/options-research-lab/IMPLEMENTATION.md), inspected including latest Oct9 entries.
- P3: [Research Lab appearance](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/d9ec4d2b86e9e9e0129d7fcd4c646f25f7670c49/docs/options-research-lab/APPEARANCE.md).
- P4: [Options companion contract](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/d9ec4d2b86e9e9e0129d7fcd4c646f25f7670c49/docs/TERMINAL_OPTIONS_COMPANION_2026-09-23.md).
- P5: [OptionsHubView source](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/d9ec4d2b86e9e9e0129d7fcd4c646f25f7670c49/terminal/components/OptionsHubView.tsx).
- P6: [Options Prophet audit and build contract](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/d9ec4d2b86e9e9e0129d7fcd4c646f25f7670c49/docs/audits/2026-08-08-options-prophet-system-audit.md), historical rationale for separate Macro Plans / Options Alpha lanes; current states require fresh reconciliation.


## Integration delta — existing Options R1/R2 and whole-suite ambition

Reviewed local audit sources S27 (OPTIONS_R1_PROGRAM), S28 (OPTIONS_R1_W1_FREEZE) and S21 (issue599 comments through 2026-10-21T09:44:34Z). This delta updates the earlier product recommendation. PR1096’s current source and PR1091’s merge/recovery evidence remain scoped as observed by the parent audit; neither establishes whole-suite live acceptance.

### Decision: absorb R1 as a valuable delivery stream

R1 is a concrete sector-origin research-continuity stream: Sector Central → holding → expiry/strike → chart → matched change → save → watch → review. Its current plan includes rotation, holdings coverage, source-aware changes, persistence, alerts, replay and scenarios. It should continue on its original carrier under the broader integrated product outcome. Recommissioning it as a competing “new Options suite” would duplicate source ownership and create avoidable integration risk.

The program document also identifies a sibling Fable R2 exposure-reducer stream. Treat its disjoint source responsibilities as existing inputs to the integrated plan. The user’s authority to consolidate programs does not make recorded active work abandoned or clear unknown effects. The final master plan should assign outcome supervision and dependency arbitration, then continue or transfer each actual child through its existing owner and custody mechanism.

**Takeover is warranted only for a specific reconciled responsibility that needs a successor.** Record which scope transfers, who accepts, the exact source and effect state, remaining obligations and original carrier. Do not create replacement roots merely to give the new master plan a clean appearance. Issue599’s original Options recovery, Exposure, Lab, IW2, flow and outcome obligations remain in the estate; R1 does not supersede them by existing.

### What R1 does not yet cover

R1’s strong continuity journey is insufficient for the user’s full ambition. The integrated program must additionally own:

- Whole-suite navigation, consistent density, chart hierarchy and novice/expert progression.
- Options-originated Prophet discovery, thesis formation, contradictory evidence, candidate comparison and incremental confluence validation.
- A complete contract/structure workflow with eligible chain discovery, liquidity/cost qualification, pre-expiry scenarios, event/settlement/exercise considerations and risk-budget comparison.
- Integration of measured flow, correction/package semantics, qualified off-exchange/pressure observations, technical context and dated catalysts.
- Ongoing plan/position monitoring and separately graded underlying, option-mark and feasible-trade outcomes.
- Task-level competitor parity across the declared universe, frequencies, history and entitlements.
- Actual evidence that these capabilities improve interpretation and decision quality.

R1 W4C’s lack of O-OPT results is a scoped scientific-promotion dependency. Continue descriptive usefulness while a separately owned evaluation program earns any stronger claim. Neither permanent prediction abstention nor immediate unvalidated fusion satisfies the requested north star.

### How the five-destination architecture absorbs R1

| R1 capability | Destination and integration |
|---|---|
| Rotation, holdings breadth/concentration | Market Brief and existing Sector Central entry; maintain the native sector owner and origin contract. |
| Holding → exposure → chart → matched change | Workbench’s Positioning lens and linked chart; preserve the current origin envelope and reference fingerprint. |
| Save/reopen revisions | Shared investigation continuation across Workbench, Trade Lab and Monitor. |
| Flow confidence, packages and volatility/events | Workbench lenses, exposing only their independently qualified claims. |
| Condition watches | Monitor through the existing alerts owner and explicit source/action/category consent. |
| Replay and scenarios | Workbench History and Trade Lab, with their actual source clocks and scenario assumptions. |
| Validated research claims | Prophet only after the separate scientific and authority gates are satisfied. |

Do not add a sixth isolated R1 application. The same symbol, investigation and contract selection should follow the user, with a clearly described transition when the data’s time basis changes.

### Highest-risk seams

**Saved research:** S28 proposes an InvestigationContextVNext candidate and references manifest v2; issue599 still requires genuine current source-use decisions and qualified IW2 v3 Save/read/reopen. Different version numbers alone do not prove incompatibility: they may name different namespaces. Before R1 W2C acceptance, bind the candidate to the exact admitted IW2 application/manifest/rights/recovery contract. A component can be buildable while Save remains unavailable. Reusing investigations.ts is necessary but does not by itself prove complete interoperable recovery.

**Alert activation:** issue599’s P09 selected-node delivery category is preparatory, defaults off, and still withholds sends. Paid entitlement, a new settings toggle or a saved condition does not establish trusted enrollment or source/action rights. R1 W3C must compose the existing owner’s actual activation contract; no duplicate scheduler, alert table or consent interpretation.

**Meaning of change:** W1C correctly preserves matched reported Gamma as a descriptive measurement with separate population counts. Keep that boundary local to this metric. A later qualified model may explain a distinct mechanism, but cannot relabel the inspector’s historical comparison as dealer activity or flow.

### User-experience hazards to address now

1. **Evidence crowding out the task.** W1C specifies five population tiles, three aggregate values, a table and several limitation notes. That can overwhelm the important answer. Lead with the selected comparison and largest relevant change, then disclose population and qualification details nearby. Preserve every fact without making every fact equally prominent.
2. **Small type as the default density solution.** W1’s proposed 9–11px labels and notes require actual reading tests, especially EN/ZH at magnification. Crop success cannot demonstrate comprehension.
3. **Multiple navigation origins.** Sector return, exposure return, chart navigation and future saved investigation continuation can create competing Back actions. Preserve browser history and clearly distinguish return-to-origin from change-lens.
4. **Duplicate context controls.** Symbol, session, scope, expiry and normalization should have one visible owner per task. Repeated controls with subtly different scopes will make correct backend behavior feel inconsistent.
5. **Unavailable panels consuming prime screen space.** An unavailable capability should state the consequence and a useful next action. Preserve a working view when a neighbor fails; do not make the whole page a status report.
6. **Late usability acceptance.** R1 puts responsive/a11y/performance proof in W5. Keep W5 for integrated regression and release proof, but require those qualities in each vertical wave before expanding it.
7. **Feature parity by screenshot resemblance.** A recreated chart earns parity only when users can perform the corresponding task on equivalent supported inputs. Visual similarity is one dimension, not the finish line.

### Useful-outcome acceptance addition

Require a small set of blinded market cases spanning ordinary, conflicting, stale, sparse and unavailable inputs. Novice and expert users must correctly distinguish observed facts, modeled positioning, conditional scenarios and predictive claims; identify the relevant contract and horizon; explain the meaningful risk; and preserve the investigation through save/reopen and an alert.

Compare R1/R2’s integrated journey against the current product and a simpler baseline. Report correctness, critical interpretation errors, time and abandoned tasks separately. Keep the earlier proposed 90% task-success target by declared cohort, but do not average away a failing novice, mobile or Chinese-language cohort. All critical factual-identity/time errors must block acceptance.

The decisive Fable milestone is a useful, coherent research-to-monitoring journey. W1 source, green checks, reviewed Paper boards, one successful screenshot set, a merged PR and a deployed page are distinct progress states; none alone closes that milestone.


