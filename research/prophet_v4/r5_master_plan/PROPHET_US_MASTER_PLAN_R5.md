# Prophet US — Consolidated Flagship Master Plan

**Version:** R5 / 2026-09-23  
**Design disposition:** proposed integrated master plan for review and staged adoption; not a registered trial, accepted source change, or production release.  
**Parent:** `mastermindx-market-intelligence/macro#6805`  
**Operation:** `prophet-us-master-plan-r5-20260923-sol-001`  
**Current working checkpoint:** issue comment `5791272310`; read its final revision for continuation.  
**Procedure pin:** `Mastermind@89582a372aa2a57ec500868ce6d79cd156219445`, protected master, compatible Skillpack 1.0.1 / bootstrap-major 1.  
**Planning snapshot:** `macro@c9978765aa0085eba0213430284cb4b41065d4e2`. This is not an assertion about the deployed release.  
**Inputs:** four hash-verified R1–R4 dossiers, reproduced in `inputs/`; their 25,292 words are supporting analysis, not additional live authority.  
**Mission complete:** false. No research packet or implementation unit described below has been dispatched by this document.

## How to use this plan

This document is the integrated product, scientific, and delivery specification. `RESEARCH_DOCKET.md` expands the finite research questions; `BUILD_PROGRAM.md` expands implementation outcomes and review boundaries; the JSON companions connect requirements, research, decisions, acceptance cases, existing carriers, and proposed build units. These identifiers are document cross-references, not new Executive jobs, workstreams, queues, or state machines.

Read sections 1–4 for the product decision; sections 5–13 for the intelligence and strategy architecture; sections 14–19 for the experience and operating requirements; sections 20–26 for execution, acceptance, and continuity. The companion packets carry the detailed workload so a worker does not need this conversation.

Assertions about the previous implementation are explicitly historical findings from R1–R4 unless a fresh R5 source is named. Existing PR statuses must be refreshed at the exact action boundary. A prior green check, a branch name, a current file, and a served result are different evidence. Recommendations are proposed choices, not claims that unmeasured outcomes will occur.

## 1. Executive decision: rebuild the decision system, not just the score

Prophet US should become a continuous opportunity-and-thesis workspace. Its job is to help a user discover a worthwhile stock opportunity early, understand the economic and technical case, choose an appropriate strategy and timeframe, distinguish present entry from research interest, maintain the thesis, and learn from what happened. A stock list is a useful projection of that system, not its entire product.

The chosen architecture is **one shared platform, multiple governed sleeves, and independently evaluated decision components**. Preserve the working identity, episode, source, quote, entry-geometry, publication, account, plan, and evaluation owners. Replace weak behavior through bounded vertical slices rather than creating a second Prophet beside the first.

Three initial flagship sleeves anchor the rebuild: Early Leadership / Sector Rotation; Quality Earnings / Expectation Revision; and Cyclical Washout Accumulation / Cycle Capture. Their horizons, evidence, entry policies, and holding laws differ. A four-hour observation is not a fourth strategy. A two-year investment thesis cannot absorb a losing tactical trade by relabeling it.

The recommended model architecture estimates distinct quantities: expected net and relative opportunity, upside/downside distributions, severe-loss risk, target-before-invalidation and time-to-payoff, and applicability/uncertainty. Current entry permission remains deterministic and strategy-specific through B4. A readable narrative explains the evidence; it does not create eligibility or repair missing facts.

Three accomplishments advance separately: **useful research delivery**, **correct entry and management mechanics**, and **earned predictive advantage**. They converge in the full flagship, but a model result is not a delivery receipt, and attractive UI is not evidence of alpha. This separation is the central execution strategy: release honest usefulness early while the scientific program accrues the evidence needed for stronger claims.

### 1.1 Why not only tune V3?

The previous reconstruction identified V3 stage-plus-Fusion ordering as an incumbent control, not a calibrated return model. It also identified incomplete candidate visibility, entry/source integration seams, sparse effective evidence families, and mixed measurement grains. A few new weights cannot repair those missing capabilities. V3 remains a valuable reference and fallback; it is not the end-state abstraction. [R1 §§1–2; R2 §2; R3 §2]

### 1.2 Why not replace everything with a single large model?

A single learned output would conflate discovery, forecasting, timing, risk, and execution. It would make source failure difficult to distinguish from economic pessimism and encourage a confident score to override a price/basis defect. High-capacity models remain legitimate research candidates, but their influence is bounded by explicit inputs, comparisons, and accepted output heads. Model size is not a substitute for a coherent task.

### 1.3 The practical meaning of “from the ground up”

Redesign the user and machine decisions from first principles, while reusing sound infrastructure. The ambition is a different level of intelligence and workflow—not gratuitous file replacement. Existing negative evidence, exact source histories, accounts, and open positions are assets. A rebuild that loses them would reduce the moat.

## 2. North Star, personas, and completion

The product target is a complete, early, honest opportunity field; strategy-specific present-entry truth; intelligence-ranked research priority; visible uncertainty and counterevidence; deliberate user authority; and prospective learning. “Complete” means every in-scope observation is accounted for, including exclusions and unsupported cases. It does not promise knowledge of every tradable instrument or every future winner.

### 2.1 Three primary user jobs

**The tactical stock researcher** needs to move from market and group change to a small, useful review set without seeing a stock for the first time after most of the move. The task ends with a comprehensible watch, wait, or permitted entry assessment—not merely a high score.

**The event/earnings researcher** needs to understand what actually changed, which expectation it differs from, the integrity of the comparison, the price response already realized, and what remains. The task must still work honestly when licensed analyst history is absent.

**The structural cycle investor** needs to connect industry economics to issuer survival and per-share recovery, monitor milestones, and distinguish a valid core thesis from a tactical add opportunity. The task fails if the system exits only because of ordinary daily noise or holds through permanent impairment on narrative alone.

The Chairman is the initial demanding persona and final program authority. The commercial experience must nevertheless be usable by an entitled customer without knowing internal PR numbers, source schemas, or company governance vocabulary. Detailed receipts belong behind understandable explanations.

### 2.2 The machine job

Observe source-qualified events and market facts; preserve them at the time they become known; relate them to canonical identities and episodes; assemble a missing-aware evidence view; evaluate strategy-specific opportunity and entry; deliver a coherent snapshot; preserve actual user actions through existing owners; and evaluate every materially different decision without rewriting its original belief.

The learning objective is not only to improve selected picks. It must diagnose unseen winners, wrongly rejected candidates, poor ranking, late delivery, infeasible entry, weak management, and concentrated common risk. Those are different error classes with different repairs.

### 2.3 Proposed success scorecard

The following are design acceptance requirements or proposed engineering objectives, not measured present performance.

| Dimension | Required end-state evidence |
|---|---|
| Completeness | Every source-qualified in-scope nomination, suppression, episode, and board displacement is counted and has a comprehensible disposition; no silent cap loss |
| Time truth | Every decision references its actual source/observation/generation clocks; later corrections do not rewrite original decisions |
| Entry truth | No displayed new-entry permission without the accepted strategy and all mandatory current owner facts; no favorable model waiver |
| Intelligence | Incremental usefulness over strong same-tape controls, with tail risk, coverage, costs, uncertainty, and independent-date evidence |
| User workflow | A user can find, compare, explain, save, revisit, and evaluate an opportunity across the real entitled path |
| Persistence | A successful save has a real owner readback; watch, thesis, plan, and position effects remain distinct |
| Delivery | Accepted source bytes reach the served product and survive the next ordinary refresh, including corrected and degraded states |
| Performance | Proposed field targets: p75 LCP ≤2.5 s, INP ≤200 ms, CLS ≤0.1, separately for mobile and desktop; adoption follows measured baseline and implementation review |
| Trust | No unlicensed premium facts in anonymous payloads or generated prose; no experimental forecasts presented as established probabilities |

The Web Vitals values above are established public guidance; they are not a promise that current Prophet meets them. Lab tests are not a substitute for real-user measurement. [X07]

For investment results, do **not** choose a universal promised win rate. A 70% win rate with rare severe losses may be worse than a lower-win-rate asymmetric strategy. Require an economically material improvement in a declared primary endpoint, positive evidence of acceptable harm within a declared margin, usable coverage, and stable performance on untouched and prospective observations. Numerical economic margins are resolved through decision D06 before the affected experiment, not selected after seeing results.

### 2.4 Full flagship acceptance is broader than an initial release

An initial research release may be useful and accepted for a bounded claim while models remain in shadow. The full US flagship is not complete until all three advertised core sleeve journeys are integrated, their live decision/holding claims are supported at the claimed level, failures are visible, user state is durable, and the ordinary production path is proven. If a research mechanism fails, narrow or reject it explicitly; do not silently relabel its unbuilt promise as delivered.

## 3. What survives from the prior programs

This is convergence, not a new competing program parent. The August V4 architecture remains the platform backbone; Conditional Fusion remains the model-research foundation; the multi-strategy/Cycle Capture decision remains the sleeve law. R1–R4 provide the integrated scientific and source-bound product contracts. Source-law adoption still belongs to current repository and decision owners. [I01; R1–R4]

| Prior work | Role in the integrated plan | Narrowly superseded assumptions |
|---|---|---|
| V4 Recovery | Shared candidate, evidence, state, Availability, product, and learning architecture | None by this proposal alone |
| Conditional Fusion | Family separation, multi-head models, conditional research, same-tape controls | C1 heuristic is not the final predictive architecture |
| Strategy Platform / Cycle Capture | One platform with distinct economic sleeves and core/add semantics | One all-weather stock score or inherited universal hold law |
| September R2/global autopsy, #7218 | Measurement and point-in-time correction requirements | Historical popup rank/sector as decision-time features |
| Trend Intelligence / Eyes Open / Doors | High recall, explicit alternative discovery, source and geometry lessons | Old top-12 and conviction-primary bridge diagnosis; no revived killed signals |
| Learning Loop / Arena / miss audit | Full-population evidence, challenger controls, failure taxonomy | Published-plan-only success measurement |
| Candidate visibility / Entry Truth / Theme Intelligence | Existing implementation and proof carriers | No duplicate replacement PRs or new owners because integration is difficult |
| R1–R4 | Three-clock design, measurement, concrete sleeve templates, integration findings | Broad labels without exact observation/entry/holding semantics |

The retained negative evidence includes general freshness-window widening, flat veto removal, naive leader-reset authority, refuted ignition constructions, copied CN coefficients, per-ticker outcome audition, universal regime scorecards, the killed short Washout×Turn seed, and LLM-originated live ranking/trading authority. A genuinely new experiment requires a mechanism and a kill-equivalence check; a new name is not a new hypothesis. [R1; prior convergence checkpoint indexed in I01]

The point of preserving killed work is not to prohibit novel science. It is to prevent repeated expenditure on equivalent constructions. A material new data source, mechanism, population, horizon, or corrected evaluation flaw can justify re-adjudication through the existing owner, with the difference written before outcomes.

### 3.1 Existing carrier crosswalk

`CARRIER_MAP.json` records the exact known references and the round in which they were verified. It deliberately does not pretend every PR was re-read during R5. The map includes #7180, #7572, #7581, #7584, #7734, #7738, #7751, #7455/#7508, #7604, #7218, and merged-repair evidence such as #7294/#7295. Reconcile the exact current head, custody, and outstanding proof before each modifying action. Unrelated repository movement is not a reason to restart the entire audit.

The B4 prereg alias finding remains on #7751 comment 5787579945. The source-session binding finding remains on #7581 comment 5789777976. They are pending owner dispositions, not amendments accomplished by this plan. [R1 §11; R3 §2.4]

## 4. One architecture, six functional responsibilities

This is a functional description mapped onto existing owners, not a new registry or replacement state plane.

**Observe.** Data OS and source owners supply lawful prices, quotations, identities, company events, group facts, filings, ownership observations, and economic series. Every source says what is measured and when it became available. Optional source failure reduces evidence coverage; mandatory identity/price failure can block action.

**Preserve.** Owner-native nominations and suppressions remain visible even before they can originate B1. B1 alone owns episode identity, structural anchors, generation, corrections, and re-arm. B3 projects orthogonal lifecycle, emergence, and maturity rather than collapsing every state into one BUY/WAIT label.

**Understand.** D5 and the source owners assemble evidence families. Conditional Fusion and accepted research models estimate the relevant strategy/horizon outcomes. Shared evidence is not independent merely because it appears in multiple APIs or themes.

**Decide present availability.** B4 consumes the accepted strategy definition, exact candidate state, quote/basis, owner geometry, and gate facts. Models and prose cannot supply missing gate facts. Different sleeves may have different accepted policies; none bypasses source integrity.

**Deliver and maintain.** Existing private API/premium publication and the shared product shell render coherent snapshots. WatchStore, feedback, plan, and Portfolio/Risk owners persist their own deliberate effects. Alerts consume changes through the existing alert pipeline. New-entry assessments and holding assessments remain separate.

**Learn.** Existing Evaluation/QLedger, prospective grades, Arena, and audit owners attach outcomes to preserved decisions. Formal training occurs only on admissible data and accepted research paths; live rankers do not import future outcome stores to score current candidates. Reviews promote a defined artifact/version, not a research narrative.

### 4.1 The shared opportunity view

The composed view references, rather than re-owns: canonical security/issuer identity; episode ID and generation; strategy/version/scientific status; origin and current decision cutoff; source/evidence family references; emergence/maturity; forecast outputs and applicability; B4 availability and reasons; thesis and management references; user-action history; and outcome/control lineage.

A view is invalid if it combines a new quote with stale incompatible geometry or an episode generation with evidence evaluated against another cutoff without an explicit relationship. Display partial coverage where safe, but never hide a cross-generation mix behind a single green freshness badge.

The read model must distinguish an absent field, measured neutral value, failed access, unsupported calculation, post-cut observation, and unlicensed content. It must also distinguish structural hypothesis failure from data absence. This richer null vocabulary is part of the intelligence, not decorative provenance.

### 4.2 Identity across sleeves

One security can have several strategy assessments. Shared identity does not mean their trade forecasts are interchangeable. A user may view the same episode through tactical and structural lenses; existing positions retain their strategy lineage and actual transaction history. Portfolio exposure is aggregated once by the downstream owner, with shared issuers and correlated groups visible.

Do not create one physical position per sleeve merely to make the analytics easier. Do not equate a saved ticker with a saved episode thesis. When an existing owner cannot represent a required relation, decision D05 assigns a bounded extension there before the UI advertises persistence.

## 5. Time, corrections, and what the product actually knew

Preserve three evidence classes: **observed as run**, **point-in-time replay**, and **retrospective diagnostic**. A computation performed today using admissible historical inputs can be useful replay research. It is not proof that the old deployed system generated or displayed that decision. A diagnostic using later knowledge is useful for explanation but cannot enter confirmatory evidence under a historical-knowledge label. [R2 §§3–6]

The decision record references the owner-defined event time, source publication time, first observed/captured time, computation/version time, decision cutoff, accepted-publication time, and user-visible exposure where measured. Not every owner exposes every clock; the missing clock remains explicitly unknown. An economically effective date or bar close is not an acquisition timestamp.

D5's inspected correction law already prevents current-body data from becoming historical belief, and the episode cutoff is pinned to a B1 generation. Extend that discipline to every evidence family. An amendment can change the current assessment while leaving the original decision and later correction separately inspectable. Corrections must never make the displayed past rank improve retroactively. [R2 §6; R4 §2]

### 5.1 Source session and valid decision session

A prior completed-session technical fact may be meaningful during the next regular session, but the owner must state when that fact expires or is revoked. Do not relabel its source session to satisfy a consumer expecting today's date. The R3 characterization of #7581 showed a specific equality check refusing the prior-session/current-RTH composition; it did not prove a global production outage. B05 resolves the accepted validity contract on that carrier, preserving the difference between data age and present validity. [R3 §8]

For 1D, 2D, 3D, weekly, and 4H evidence, record native bar anchoring, completed versus provisional state, timezone, session boundaries, and adjustment basis. A developing bar may be a distinct registered observation, but it cannot pretend to be a completed historical bar. Each source must say whether a signal could have changed before its bar closed.

### 5.2 Model vintage is a separate clock

A modern LLM may contain later knowledge even when its supplied documents are old. Source-grounded extraction and outcome forecasting therefore have different admissibility questions. Extraction must be faithful to supplied evidence and audited against it; retrospective forecasts additionally need admissible model vintage or a clearly labeled limitation and prospective validation. Ticker masking is a control, not proof of chronological isolation. [R1 §10.1]

### 5.3 Record retention and cost discipline

Use the existing immutable source/generation and outcome infrastructure. Store exact references and hashes where the owner already retains the body; do not copy complete documents into every candidate row. Capture enough decision-time material to reproduce a forecast, including feature and model versions, without building a duplicate warehouse. Lifecycle corrections, retention, and access remain with existing Data OS/product owners.

The record-retention proposal must include research reproducibility, licensed-data retention rights, deletion obligations for user data, and storage cost. A research desire to retain everything does not waive a license or privacy boundary. Source retention and personal user-action retention are separate concerns.

## 6. Data and intelligence acquisition program

The design is base coverage plus incremental specialist evidence. Every supported name needs a reliable identity, price/basis, session, basic technical and group context, and a truthful data-health view. A richer evidence family can improve research or forecasts only when it is genuinely available and evaluated. Missing transcript or options coverage does not mean the company is economically poor.

### 6.1 Source-readiness matrix

The statuses below are planning dispositions, not new claims of full live or historical coverage.

| Family | First permitted use | Required evidence before predictive use | Existing owner to extend |
|---|---|---|---|
| Security identity, listing history, corporate actions | Exact routing, basis, and historical membership | Stable issuer/security mapping at each cutoff; delisted/renamed share classes retained | Data OS / Stock Identity |
| Daily and higher-timeframe prices | Native technical observations and fixed-horizon controls | Completed-bar calendar coverage, adjustment provenance, missing-bar handling | Existing price and technical owners |
| Intraday quotes and NBBO | Current quote/fillability facts | Actual quote timestamps, rights, basis, session, latency and fill assumptions | Live Quotes / Prophet Live; #7734/#7584 |
| Technical species | Nomination and explicit source state | Registered mechanism, event clock, anchor/re-arm, exact killed-equivalence check | TOI / TURN WATCH / Radar / B1 |
| Group/subtheme relationships | Descriptive context and navigation | Point-in-time membership/weights, lineage, coverage and benchmark basis | GMI / Theme Intelligence / Group Reads |
| Filings and financial facts | Source-backed research and survivability facts | Accession/revision, comparable units/period/scope, knowledge cutoff | Filing Forensics / Earnings |
| Earnings releases, calls, guidance | Event dossier and observed changes | Complete event discovery, correction history, source-stage clocks and comparable facts | Earnings Intelligence / D5 |
| Analyst expectations | Explicitly licensed expectation comparisons | Fixed-period/basis definitions, contributor changes, revision clocks, rights | Incumbent estimate/earnings data owner |
| Insider and institutional ownership | Disclosed transaction/position context | Transaction versus filing/observation time, transaction type and meaningful economic exposure | Existing ownership/filing sources |
| Congressional disclosures | Labeled public disclosure context | Disclosure date, transaction-date range, ownership identity and amendment uncertainty | Existing lawful disclosure owner |
| Options/positioning | Observed market context, not inferred certainty about investor intent | Historical quote/OI source timing; model assumptions; coverage and costs | Options / Flow / specialist owners |
| News and catalysts | Source-grounded event discovery and uncertainty | Deduplication, correction, novelty and availability clocks; source reliability | Intelligence Hub / event sources |
| Macro and industry economics | Dated context and mechanism evidence | Vintage-aware values and actual observation timing | Macro / Data OS / industry source owners |
| Directed economic relations | Exposed businesses and group research | Dated direct/proxy edges, confidence, rights, negative controls | GMI / Supply-chain / Graph owners |
| Funding and terminal outcomes | Per-share recovery and failure-inclusive labels | Restricted cash, debt schedule, dilution and reorganized-security treatment | Financial/identity/outcome owners |

The D5 adapter inspected in R4 exposes only three revenue lanes and current-event discovery. That is a valuable narrow bridge, not full earnings completeness. Expand through the owner rather than minting plausible EPS, margin, cash, or analyst-revision features in the ranker. [R4 §2]

The Census M3 source has useful broad manufacturing series but stopped separate semiconductor estimates with April 2010 reports. A broad computers/electronics series cannot be presented as memory, HBM, or NAND evidence. FRED defaults to information known today; ALFRED-style vintage parameters address a different question. These limitations shape source qualification rather than being cosmetically renamed. [X05; X09]

### 6.2 Qualitative evidence has to become usable intelligence

For each company/event family, the dossier should identify the factual change, mechanism of impact, likely exposed economic quantity, plausible persistence, counterevidence, observed price response, and a condition under which the interpretation would be revised. This is synthesis over typed facts, not simply a provenance checklist.

A source-backed insider purchase may be relevant, but the narrative cannot infer an official policy decision or future deal from it. Transaction type, significance relative to the investor's exposure, and publication timing matter. Institutional holdings snapshots are not contemporaneous buying-flow measurements. Options open interest and modeled dealer exposure are not direct observation of every participant's position. Those distinctions are feature definitions and research controls; no universal insider or flow bonus is authorized.

The model experiments should test incremental value by family and its correlated relatives. An analyst sentence repeated by several news outlets is one underlying information event, not five independent confirmations. Company, group, and market evidence can be economically dependent even when every source hash differs.

### 6.3 Acquisition priorities and paid-data decisions

Prioritize data that closes a named decision failure. First repair compulsory identity, basis, source clocks, publication, and outcome coverage. Then add earnings comparability, group membership history, and event discovery. Licensed analyst history, richer intraday data, or specialist series should be acquired when a documented use, rights contract, coverage sample, and expected research decision justify them.

No vendor purchase, API key creation, or subscription is authorized by this plan. The acquisition packet must list existing alternatives, sample coverage, revision policy, retention/display/model-use rights, economic cost, and the exact study or user capability that remains impossible without it. Do not buy a broad alternative-data catalog merely because more fields are available.

Missing paid consensus blocks the matched-analyst branch, not issuer guidance or comparable public-filing research. Missing true historical specialist evidence starts prospective accrual; it does not justify backdating current values. Missing compulsory execution data keeps the entry path unavailable while research remains viewable.

## 7. Discovery: preserve broadly, qualify explicitly

The initial expert set is the source-bound roster identified in R3, not an invented collection of indicators. TURN WATCH includes daily early-turn, 2D pre-confluence, basket-turn, and leader-reset observations. Its fixed population and minimum-history convention must be disclosed. A 4H expert needs a real registered owner and event/anchor/clock contract. [R3 §2.3]

At the inspected boundary, TURN WATCH alone supplied B1 structural anchors while other observations could remain unanchored. Additional independent discovery requires B1-approved anchor semantics, not a second episode implementation. Until that exists, retain the producer's nomination and suppression in the research field without calling it a canonical episode. [R3 §2.2]

### 7.1 Nomination, eligibility, rank, and entry are different filters

A nomination means a source observed something worth inspection. Eligibility means it belongs to a specified study or strategy population under declared inputs. A rank compares eligible opportunities for one purpose. Present Availability answers whether the accepted entry rule is currently satisfied. A plan represents a particular proposed or managed expression under its owner. User execution is another effect.

Every exclusion must have an attributable reason at the layer that owns it. A sector display cap cannot become evidence that the technical detector rejected the name. Missing final priority for an off-board candidate remains null; it cannot inherit a percentile computed on a different population. A terminal episode must not silently create a fresh recommendation merely because its ticker recurs.

### 7.2 Study recall at a fixed burden

Discovery improvement is not “add more rows.” Compare incremental coverage at a fixed review or alert burden, plus time gained before a useful entry, adverse-tail introductions, duplicates, liquidity, and coverage. A new expert that only produces late copies of existing nominations adds no useful recall.

Winner/loser review first decomposes the entire declared population by dated decision reasons, then uses individual names as illustrations. Famous winners must not be injected into the test universe. Young listings and short histories should have explicit support limits; a later young-name species must use its own conditions rather than weakening the incumbent history floor invisibly.

### 7.3 Counterfactual error taxonomy

Attribute failures to where they occurred: not in the supported universe; source not captured; nomination absent; B1 anchor unavailable; research eligibility refused; rank low; presentation displaced; delivery late; entry unavailable; user no action; fill not feasible; thesis failed; management surrendered value; concentrated exposure dominated. Some cases have multiple contributors, and unavailable evidence limits attribution.

A counterfactual suggestion remains a hypothesis until tested. “It would have won if we had bought it” is insufficient when the proposed rule would also have admitted many losing cases. Q02/Q03 formalize this before new discovery promotion.

## 8. Strategy contracts: the first three sleeves and the full roadmap

Each sleeve contract includes economic mechanism, supported instruments, population, source and model versions, nomination/anchor semantics, hypotheses, required versus optional evidence, current-entry law, holding/invalidation/expiry, labels and controls, uncertainty, user workflow, and exact promotion limits. A display name or horizon is not a strategy implementation.

| Initial sleeve | Economic job | Proposed research endpoints | Important distinction |
|---|---|---|---|
| Early Leadership / Sector Rotation | Capture emerging group and member strength while residual entry remains usable | New same-origin timing study: H10 primary; H5/H15 supporting | Existing 2–15-session field is a new-entry envelope, not a complete hold law |
| Quality Earnings / Expectation Revision | Capture persistent economic or expectation change not exhausted by the price response | Proposed H42 primary; H21/H63 supporting | Compatible surprise, issuer guidance, and matched analyst revision are separate constructions |
| Cycle Capture | Capture survivable industry recovery as value accruing to original equity | Proposed H252 primary; H126/H504 supporting | Industry recovery, company survival, and old-equity payoff are not synonyms |

These are new-study proposals, not accepted numerical strategy parameters. They do not amend #7751's H5/H10 co-primaries or frozen legacy graders. Horizon selection precedes outcome inspection. [R2 §8; R3 §4; R4 §§9,15]

### 8.1 Early Leadership / Sector Rotation

Separate strengthening group selection, within-group member selection, current price incorporation, and entry. Measure peer support excluding the candidate where valid: a star member can create the whole group return, so its own momentum and the group's momentum are not automatically independent confirmation. Keep fixed-period and actual-weight calculations consistent; undefined singleton peer support remains unknown.

Start with registered observations and competitive own-price/group controls. Do not require every lagging confirmation to be positive if the experiment is supposed to measure earlier recognition. Equally, earlier visibility does not waive B4's incumbent confluence. A genuinely earlier species-specific entry policy needs a distinct accepted owner version and same-origin comparison. A reader should see the earliest observed event, later confirmation, current geometry, and reasons for waiting separately.

### 8.2 Quality Earnings / Expectation Revision

Separate post-release repricing, issuer-guidance changes, and analyst revision. The initial comparable operating-company construction excludes specialized accounting from its predictive claim until those semantics are supported; it does not hide other companies from research.

Bind each comparison to metric, period, units, currency, GAAP or exact adjusted definition, continuing-operation/segment scope, and share basis. A missing licensed expectation cannot be replaced with prior reported earnings and labeled a beat. Consensus composition and horizon-rollover effects remain separate from matched contributor revisions. Profit growth can coexist with falling EPS after dilution; source-backed analysis must explain the distinction.

Record release, call, filing, and subsequent estimate changes separately. Do not earn a pre-entry gap in strategy performance. Next-report handling, guidance failure, operating milestones, expiry, and risk exits must be declared before evaluating management. The public earnings-momentum literature motivates the mechanism, but it does not prevalidate the proposed Prophet sleeve. [R4 §§4–9; external references in R4]

### 8.3 Cycle Capture

Select the first proving domain by data and mechanism readiness before returns. Industrial capital goods/machinery is the proposed readiness candidate, not an outcome-selected winner or a coverage-certified universe. Semiconductors/memory and producer/miner equities remain high-priority specialized domains, with sector-specific data rather than generic proxy substitutions.

Follow orders/demand quality, shipments/inventory, pricing/margins, cash/capital requirements, dated financing obligations, and value per diluted share. Current cash divided by current burn misses debt maturities and minimum cash requirements. Improving enterprise value may not rescue original shares after debt and dilution. Terminal outcomes must follow the actual held security through cancellation or reorganization.

The core thesis, tactical add permission, economic milestones, structural invalidation, and expiry remain distinct. Normal daily noise need not close a valid core, but a convincing long-term story cannot waive binding impairment. No averaging-down or leverage authority exists at sleeve birth. Funding and recovery probabilities need coherent joint modeling or explicit scenarios; multiplying marginal probabilities silently assumes independence. [R4 §§10–17]

### 8.4 Subsequent sleeves and instruments are retained, not hidden scope cuts

Policy/Event studies require precise public-event availability, authority and reversibility, exposed-business mapping, and price-response controls. Catalyst/Dislocation studies distinguish forced technical pressure from information-driven impairment. Range/Reversion studies need separate regime and cost evidence rather than general-purpose mean reversion. Real Assets/Producer studies separate commodity economics, equity claims, currency, hedging, and financing. Defensive/Risk views must specify the user decision they improve rather than promise positive alpha by inactivity.

Short-side and options expressions need their own instrument, borrowing/liquidity, payoff, and loss semantics. A strong stock thesis does not prove an options structure is attractive after implied volatility, decay, spread, and event risk. R5 preserves these avenues in Q23/B27 rather than adding silent trade permission. The three initial sleeves establish shared contracts; they do not exhaust the long-term platform ambition.

## 9. Evidence composition and the intelligence advantage

The central information unit is a source-qualified observation attached to the canonical episode/strategy view. It should say what changed, for whom, at which clock, on which definition, and why the economic interpretation is plausible. Missingness, counterevidence, and overlapping information are part of the interpretation.

The model-facing representation should group information by mechanism, not by the number of columns in a dataset. Price behavior, group participation, technical occurrence, earnings/expectations, ownership/flow, company quality/funding, macro context, and economic relationships have different meanings. A family contributes only what its actual data support. A renamed indicator does not create a new independent family.

### 9.1 Deterministic facts, model estimates, and prose

Deterministic normalization establishes identity, units, compatible periods, source clocks, and explicitly computed quantities. A model estimates outcomes or interprets uncertain mechanisms under a versioned method. Prose explains those results. None should be mislabeled as another.

An LLM may extract and summarize source-supported claims through the existing model/source pipeline, subject to rights and exact evidence verification. It must not invent a missing financial number, assert an undisclosed government action, manufacture a probability, or choose an entry because a narrative sounds favorable. A contradiction should be preserved as a contradiction rather than resolved through unsupported confidence.

The proposed quality review samples every important input class, including corrected filings, negatives expressed in parentheses, mixed currencies, missing periods, unusual fiscal calendars, stock splits, different adjusted-profit definitions, and unavailable source spans. A numerical error that changes the direction of a thesis is not a cosmetic citation issue.

### 9.2 Contextual evidence without a universal regime bonus

A market-wide regime value cannot rank stocks on a date when it is constant across them. It can inform a qualified interaction: which exposure or strategy behaves differently in that state. Only specific predeclared relationships with estimable support can affect an accepted model. Sparse cells shrink toward broader priors or abstain; they do not choose the expert that recently looked best.

Retain allowed global fingerprint-to-expert relationships and behavioral-neighbor pooling where the existing protocol permits them. Per-ticker historical winner selection stays rejected. Sector, history length, and coverage can identify a stock indirectly, so name-disjoint and permutation controls matter even when ticker is removed.

### 9.3 Economic graph research

Use the existing GMI/relationship owner to distinguish direct customer/supplier exposure, indirect dependency, competitor substitution, and broad thematic association. Edge direction, date, uncertainty, source rights, and economic relevance travel with the observation. A current relationship cannot be projected back before its existence or discovery.

First test simple directed features against own-stock, industry-only, no-graph, shuffled-edge, and shifted-clock controls. A temporal graph model is a challenger after the information itself proves incremental value. Popularity, degree, membership overlap, or a stock generating its own group strength are alternative explanations to reject. This turns graph research into a falsifiable economic study rather than a visualization project.

### 9.4 The maintained thesis

The future thesis view records the original hypothesis, supporting facts, counterevidence, expected measurable response, invalidation/expiry, and next review condition. Later assessments append changes. The original prediction does not become more prescient because a later model found a better explanation.

Thesis maintenance must follow source events and scheduled owner-defined reviews, not repeated generative restatements with no new evidence. Summaries should explicitly say when the information set is unchanged. This reduces false novelty for users and unnecessary model expense.

## 10. Prediction and ranking architecture

The proposed prediction target is conditional on **episode, strategy, observation time, horizon, and policy definition**. A ten-session tactical assessment and a two-year Cycle assessment are not directly comparable scalar scores.

For the appropriate decision cohort, estimate separately:

- expected absolute net outcome and benchmark/sector-relative outcome;
- relevant return quantiles and severe-loss probability;
- probability and timing of target-before-invalidation, with unresolved paths handled explicitly;
- evidence applicability, calibration uncertainty, and out-of-support status.

This list is a model-research contract, not a demand that every head be exposed at the initial launch. Each head earns acceptance independently. An unavailable or poorly calibrated time-to-payoff head stays absent while an accepted research ordering can remain useful.

### 10.1 Origin and current-landmark models

Origin models answer whether the initially observed opportunity was useful. Current-landmark models answer what remains after development, news, a reset, or deterioration. Applying an origin-only model repeatedly to old extended episodes does not establish calibrated current forecasts.

Keep the original forecast and the current forecast distinct in storage and display. Landmark sampling is registered through the existing outcome owner; repeated five-minute rows do not become independent evidence. Rank generation may change, but historical rank and original cohort membership remain immutable. [R3 §7]

### 10.2 Baseline ladder and ambitious challengers

Start with the exact incumbent control and strong transparent models: regularized linear and logistic models, additive models with bounded declared interactions, and hierarchical shrinkage. Baselines include own-price, group, economic event, and combined-evidence alternatives on comparable populations. A deliberately weak control makes an elaborate model look useful without proving a product improvement.

Then evaluate date-grouped gradient-boosted ranking, outcome regression, quantile models, and calibrated classification. XGBoost's ranking implementation uses query groups and produces relevance scores; it is not automatically a probability or expected return estimator. Freeze the query grain, relevance labels, objective and primary ranking metric before model comparison. [X01]

Complexity research may proceed in parallel: context-gated experts, regularized high-dimensional representations, sequence encoders, and temporal graph models. None receives influence solely from architectural prestige. Model selection includes training, calibration, inference, operational latency, and review cost. Aggregated ensemble performance is calculated from the actual combined policy series, not the average Sharpe ratio of separate hypothetical models. [R1 §6]

### 10.3 Two priority views, not two independent rank engines

**Research priority** identifies what deserves investigation, including uncertain or unavailable opportunities. It can emphasize new, material evidence and information gaps. It must be labeled as research ordering, and its usefulness is measured as such.

**Actionable priority** compares currently permitted opportunities within a strategy/horizon and the accepted risk preference. It cannot set B4 permission or create capital allocation. The UI's multi-sleeve overview groups candidates by purpose; it does not sum incompatible scores into a universal “best stock.”

These are two purpose-labeled projections from accepted shared models and owners. They do not require a parallel rank registry or a new live authority. Before predictive promotion, show the incumbent or explicitly experimental order with null unsupported heads.

### 10.4 Avoid premature scalarization

Expected return, rare-loss risk, payoff timing, confidence, and liquidity cannot be safely compressed by arbitrary coefficients chosen to make a leaderboard attractive. For a declared user task, research a constrained ordering: require accepted current entry, respect the risk/capacity owner, compare net opportunity, and expose uncertainty and materially different tradeoffs.

A proposed score of the form `mean − penalty × tail risk` is only one hypothesis. Its penalty must be fixed from declared economic preferences and tested, not fitted to the same outcomes used for acceptance. Compare it with simpler ranker and Pareto-style views. When intervals overlap substantially, acknowledge that the exact ordering is weakly identified instead of fabricating decimal-level precision.

### 10.5 Abstention and rank stability

Selective prediction trades coverage against error, so a selective model must be evaluated on both. The SelectiveNet paper motivates this research framing but does not demonstrate stock-selection performance. [X08]

Abstention has an explicit meaning: unavailable mandatory data, unsupported inference, or excessive forecast uncertainty. It is not the same as a bearish forecast. Calibration is tested after selection, including top-K, sleeve, horizon, and coverage cohorts. Reliability diagrams, proper scoring rules, interval coverage and widths, severe-event counts, and meaningful uncertainty accompany claims. Calibration research on general models is precedent, not direct evidence for Prophet. [X02]

The model may reorder a snapshot, but the user should not experience a table jumping underneath focus. Changes are delivered through the interaction contract in section 15. Model stability is measured alongside relevance so a tiny uncertain score difference does not create excessive daily turnover or notification noise.

## 11. Entry, execution, and management

The entry decision combines accepted strategy identity with current source/basis, quote, geometry, confluence or species-specific trigger, session, risk, liquidity, dislocation, and event/invalidation facts. Reuse B4 and its existing owner-fact adapters. Do not rebuild its arithmetic inside a model, route, or browser.

The adapter must preserve positive evidence and honest UNKNOWN. A compact source that lacks negative refusal provenance cannot be converted into a market FAIL. A missing optional extension must not create a permanent deadlock when the strategy already has the required binding fact. The exact distinction belongs to the relevant owner, not a convenience default in the UI.

### 11.1 Entry research separates policy from population

The first timing comparison starts from the same original eligible episodes and compares early-lawful, slower-confirmation, and owner-defined pullback policies, with cash as reference. Include never-confirmers, no-pullback cases, invalidations before entry, and expired opportunities. Initially keep management fixed; then study entry-by-management interactions under a separate registered comparison. [R2 §§8–9]

B4 calibration #7751 retains its accepted population, thresholds, clock law, and no-backfill restriction. The eight labels/six distinct configurations finding is a design-integrity issue for that existing owner. R5 does not silently alter the study, add independent N, or open its protected outcomes. [R1 §11]

### 11.2 Fill and cost semantics

A historical close, a last trade, midpoint, bid, ask, and an actual fill are different prices. Choose quote-side execution or midpoint-plus-spread consistently; do not double-charge spread. A touched limit is not a guaranteed fill. Gap, latency, participation and impact assumptions must be declared for the claim being made.

The initial US control's regular-session restriction is preserved until a qualified new session/instrument policy is accepted. Extended-hours observations can be useful research without becoming executable recommendations. Current NBBO coverage does not automatically establish capacity. No unmeasured L2 behavior or order-book reconstruction is assumed from L1 snapshots.

Options expressions remain separate: stock signal, option structure selection, quotes, Greeks assumptions, expiry/event exposure, and realizable option execution require their own validation. A stock-model promotion cannot activate options or leverage implicitly.

### 11.3 Hold law is strategy-native

New-entry RAN/WAIT is not an exit instruction for an existing position. A stale source is not proof that a thesis failed or remains safe. The management system must distinguish risk invalidation, deteriorating economic evidence, milestone failure, expiry, ordinary volatility, and additional entry opportunity.

For tactical positions, specify re-entry, time stops, target/invalidation ordering, and the treatment of rapid leadership reversal. For Earnings, specify next-report and revision handling. For Cycle, specify core hold, funded path to recovery, economic milestones, distribution review, and the original-equity claim. Existing legacy plans retain their original governing policy and complete record.

A holding policy is not validated by retrospectively choosing whichever horizon best flatters each trade. A new strategy assessment after loss can exist, but it cannot erase the original loss or automatically transfer its position.

## 12. Measurement, statistical evidence, and performance targets

The scientific standard is useful incremental policy value, not an impressive pooled headline. Separate discovery, ranking, entry, management, and delivery tests. Point-in-time information, model vintage, actual source clocks, costs, and complete accounting are required before claims.

### 12.1 Preserve the unit of evidence

Board-observation keys, canonical episodes, user decisions, fills, and positions remain distinct. A ticker-ever plan link is not timely episode conversion. Preserve unmatched and multiple joins. A view cannot reconstruct an old episode from today's anchor or assign past rank from the most recent board. [R2 §§2–5]

Historical prices must be checked against expected exchange sessions. Ten future rows do not prove ten sessions if bars are missing. Label the incumbent `fwd_mdd` accurately as entry-relative close adverse excursion rather than running-peak drawdown. Track both where required, and do not relabel frozen historical values. Close MFE is not intraday opportunity or captured profit. [R2 §§11,13]

### 12.2 Primary and supporting results

For a new timing policy, the proposed primary result is a date-weighted paired full-opportunity outcome from common origin, including declared cash while waiting and after exit. Episode-weighted and fill-conditional results remain supporting views. Unknown prices are not cash. Equal-opportunity accounting is not a feasible portfolio result.

For a ranker, compare the same decision cohort with a predeclared review/top-K burden and cost assumptions. For a discovery change, include genuinely new observations and compare incremental useful coverage with false-alert and adverse-tail effects. For holding changes, freeze entries. Portfolio results require the downstream feasible capital and overlap policy.

Report mean, median, tail loss, target/invalidation order, time to payoff, turnover, cost sensitivity, market and sector excess, coverage, and drawdown where meaningful. Do not treat all these as independent primary tests. Every formal comparison has an endpoint hierarchy.

### 12.3 Unresolved observations and first-event labels

A no-entry policy outcome, an unfinished horizon, an unpriced path, a halt, a delisting, and invalid source identity are different dispositions. Every original observation is accounted for. Bounds or sensitivity analyses can be informative where exact labels are unavailable, but an unknown cannot be silently dropped to improve a score.

When both target and invalidation occur inside one coarse OHLC bar, report unresolved sequence unless finer lawful evidence determines order. Conservative adverse-first assumptions are sensitivity conventions, not observed chronology. Competing-risk probabilities must form one coherent first-event law.

### 12.4 Splits, leakage, dependence and selection

Split whole dates and then map rows, enforcing episode and label-information intervals. A library gap measured in samples cannot be assumed to represent sessions. Training labels must have matured before fitting. Learned transforms, feature selection, calibration and hyperparameter choices belong inside the training fold.

Preserve the existing Conditional Fusion protocol, including its horizon-based purging/embargo, minimum distinct-date rules, and identity/capacity/permutation controls at the required rungs. R5 does not relax a floor because the current sample is inconvenient. Separate source eras and exclude inadmissible periods from promotion.

Rows, episodes, issuers, dates, event counts and independent blocks are different sample-size measures. Overlapping horizons, shared market shocks, repeated observations, and identical policies do not add independent N. Freeze dependence treatment and the unit of inference before results. Trial accounting includes model, metric, horizon, feature, threshold and selection variants—not only the final winner. The multiple-testing literature supports a higher evidentiary standard than one attractive conventional significance test. [X03]

### 12.5 Proposed promotion decision

A candidate can advance only if it passes information/rights integrity, demonstrates an economically material primary improvement, supports non-inferiority within the predeclared harmful-endpoint margin, retains useful coverage, behaves acceptably on meaningful subgroups and adverse states, and is operationally reproducible. Uncertain results remain uncertain; absence of statistically detected harm is not proof of safety.

Decision D06 must establish numeric economic and coverage margins, the exact test family, and the formal-read schedule without viewing protected outcomes. Until then the associated study is not registered. This is an explicit decision deliverable, not an empty “choose thresholds later” step. It requires an economic loss budget, data-independent preference, power/sensitivity analysis on permitted pilot evidence, and owner approval recorded before the held-out read.

No automatic live online-learning feedback changes the model from recent P&L, clicks, or sentiment. Retraining and promotion occur through the existing accepted research/model release pathway, with immutable originals and rollback.

## 13. The finite research program

`RESEARCH_DOCKET.md` defines 24 research packets, Q01–Q24, with mechanism, population, inputs, controls, primary decision, falsifier, owner dependency, and build consumer. This is the initial finite program; a new idea needs a new registered comparison, not a hidden expansion of an existing outcome search.

The program first qualifies truth and attribution, then tests broader discovery, multi-clock entry, group/member effects, comparable event expectations, Cycle survivability, predictive heads, ranking, uncertainty, context routing, propagation, and specialist evidence. Execution realism, holding policies, user feedback, feasible portfolio aggregation, complex representations, drift, and deferred sleeves are measured separately.

The hard questions are intentionally not outsourced as “find a better AI model.” A valid research return must state the strongest alternative explanation, what evidence would reverse its conclusion, the unsupported scope, and the exact experiment that should or should not be built. Negative and non-identifiable results are useful deliverables when they prevent incorrect product authority.

Research packets consume the shared measurement spine. No packet may create its own outcome universe, replacement episode identity, private grading convention, or event-store authority. Historical and prospective evidence are complementary, not substitutes for each other's claims.

## 14. Final product information architecture

Redesign the Prophet workspace within the existing authenticated navigation family, not as a third application header. The repository's current AGENTS guide identifies the shared navigation, theme token root, design-system specimen, density rules, and independent dark/light treatments. That is the presentation boundary for the design packet. [I03]

The proposed Prophet-local navigation has six task destinations: **Action Desk**, **Early Radar**, **All Candidates**, **Themes & Propagation**, **Track Record**, and **Health & Receipts**. A persistent strategy selector sets the relevant economic job and horizon. Watchlist/positions remain linked through their existing product owners rather than duplicated as another portfolio inside Prophet.

The common header says which market and strategy are selected, what observation/quote times apply, and whether the visible view is research/control or promoted. A small context strip summarizes measured market/group conditions and their limitations. It should not turn every broad macro label into a new score.

### 14.1 Action Desk

The desk answers what can be meaningfully considered now under the selected strategy. Each row/card prioritizes company identity, strategy/horizon, accepted availability, entry/risk geometry, ranked opportunity where qualified, the most consequential supporting and opposing facts, and the next condition that could change the decision.

The first screen must not be a wall of equally weighted statistics. Use progressive disclosure: one-line thesis/change, one-line risk/refusal, meaningful forecast range or explicitly uncalibrated status, and a route to the exact episode drawer. Keep a clearly labeled distinction between an executable-price condition and an actual recommendation, plan, or filled position.

An empty actionable list is a valid product state. Explain whether there are no qualifying opportunities, the strategy is unsupported in this environment, or mandatory source data are unavailable. Do not fill the space with low-quality trades to avoid an empty dashboard.

### 14.2 Early Radar

Radar preserves early observations before full confirmation. It must distinguish producer nominations from canonical episodes and show why a candidate is being watched rather than acted on. Include first observation, development since origin, technical event, group/issuer context, missing evidence, and the exact confirmation or geometry condition being monitored.

A four-hour slot appears only when a registered source exists. A symbol outside the current history floor receives an explicit support note or a separate qualified young-name study, not fabricated long-history indicators. Early users need visibility; they do not need every early event to be called a high-conviction trade.

### 14.3 All Candidates

Search and filters cover the complete supported field, including off-board and cap-displaced rows. Counts must reconcile across source-qualified nominations, B1 episodes, ranked cohorts, presentation shelves and entry states. The filters include strategy, lifecycle/maturity, source availability, research/entry status, sector/group, evidence completeness, and user watch context where permitted.

A null rank remains null. Users can ask why a name is outside the review set and see the actual layer's reason. Comparisons use the same snapshot and meaningful units. Search results must not leak protected facts before entitlement is established.

### 14.4 Themes & Propagation

This view should connect market/group development to the selected companies, exposing membership, weights where applicable, participation, persistence, concentration and direct versus proxy economic relationships. It reuses GMI and Theme Intelligence. It must not reclassify companies or mint a second theme lifecycle.

A group can be strong because of one stock. Show the relevant contribution and peer comparison where computed. A broad proxy cannot masquerade as a granular subtheme series. Current-only relationships can support current research with disclosure; they are not a historical point-in-time graph.

### 14.5 Track Record

The default record is strategy-specific and declares its population and ruler. Separate observational signal quality, rank quality, simulated policy value, managed plans, and user-recorded outcomes. Do not pool them into one win rate.

The scorecard includes source/selection/model eras, endpoints, cost/fill convention, horizons, coverage, unresolved observations, and meaningful sample counts. A user should be able to open an original decision, compare its then-known evidence with later developments, and see whether a loss came from selection, timing, execution, management, or an unresolved cause.

The record should be useful without forcing the user to read a research report. Plain language comes first; exact receipts and statistical details are expandable. Newly accruing estimates show their uncertainty, not an apparently finished verdict.

### 14.6 Health & Receipts

Health explains what the product can and cannot currently know: owed session, source freshness, basis/identity coverage, upstream optional outages, accepted publication generation, model version and status, and delivery age. It separates current product correctness from model evidence maturity.

A green workflow is not a guarantee that the right market session reached the customer. An optional transcript outage should not make the entire price panel disappear. A stale required quote must not retain an actionable appearance. Health messages name impact in user terms and route operational repair through the existing owner.

## 15. Visual and interaction design contract

The product must feel like one advanced research workspace rather than several legacy cards pasted together. The design packet should reuse the shared component registry, tokens and route archetypes. It includes two independently reviewed art directions, EN/ZH parity, desktop 1440 and mobile 390 layouts, and measured degraded states. These requirements are already present in the repository's shared design law. [I03]

### 15.1 Dark treatment

Use the existing dark command-center direction: calm luminance hierarchy, restrained emphasis, readable surfaces, and clear separation of evidence, estimated outcomes, and actions. Avoid oversized neon “BUY” badges, saturated heatmap noise, or chart backgrounds that reduce text contrast. Critical uncertainty/refusal should be visually clear without making every unavailable optional field look like an emergency.

### 15.2 Light treatment

Use the light research-workspace direction: clear canvas/material hierarchy, crisp rules, readable evidence tables, and depth from the existing light treatment rather than copying dark glow. Keep the same semantics, actions, ordering, and density. Token substitution alone is not design acceptance. Positive, adverse, unknown, and experimental states must remain distinguishable in both treatments.

### 15.3 Desktop composition

The default desktop state should keep a compact strategy/context header, a scannable opportunity list, and an optional evidence drawer. The drawer should allow comparison without losing the selected row. Avoid fetching a large transcript, full graph, or every chart before the list becomes usable. Fold expensive evidence behind deliberate expansion with a bounded owner read and clear loading state.

The list should support keyboard navigation, stable selection, visible column definitions, and user-controlled sorting. Not every internal model head belongs in the default columns. Preserve access to detail without requiring users to interpret raw schema fields.

### 15.4 Mobile composition

Mobile is a first-class decision path, not a horizontally scrolling desktop table. The collapsed item should retain identity, strategy, availability, key risk, and next action. A full-width detail view provides evidence and chart context. Return navigation preserves the originating filter/selection. Touch controls and text must remain readable in both languages, including long translated refusal reasons.

A row can be visually compact without omitting that its quote is stale or forecast uncalibrated. Never bury the most important trade limitation below several unrelated charts.

### 15.5 Coherent updates and accessibility

Treat each rendered snapshot as internally coherent. Hydration must refuse a mismatched source generation, duplicate tail, or partial replacement rather than mixing records. Same-date corrections can require a refresh even when a date stamp does not change.

Critical availability invalidation updates promptly. Noncritical ranking reorder is offered through a visible “updated” control while preserving keyboard focus and the user's selected episode. Use accessible status notifications without stealing focus; do not announce every quote tick as an urgent alert. W3C's status-message guidance supports programmatically exposed updates, but this plan is not a claim of WCAG conformance. [X06]

### 15.6 First user study

Q24 tests whether representative users can correctly identify strategy/horizon, distinguish research priority from entry permission, explain the leading risk, save to the intended list, and retrieve the original decision. Use actual source states and deliberately difficult cases, not only polished positives.

Proposed product targets should be adopted before the test: high task completion, low false-action interpretation, and short time to locate a material reason. Numerical test thresholds belong to the registered usability protocol; a small sample's task success is not an estimate of market alpha. Optimize clarity and useful decisions, not simply clicks or trading frequency.

## 16. User actions, alerts, and thesis continuity

The initial deliberate action is watch/save through the existing list-scoped WatchStore. Verify the actual owner result before announcing success. Opening a dossier is not a save; saving a ticker is not a position; a plan is not a fill. Existing local-only note behavior cannot be advertised as cloud thesis persistence. [R3 §10.4]

To add durable Pass, reason, thesis, milestone, or review actions, first map the desired effect to the incumbent feedback or plan owner. D05 resolves exact identity, version, storage, permissions, correction, and readback. Extend that owner if necessary. Do not add an ad hoc Prophet-only personal database because the UI needs a button.

### 16.1 Alerts are meaningful state changes

Use the existing alert/notification transport and preferences. Candidate events might include first source-qualified emergence, a newly available accepted entry, a binding invalidation, material earnings revision, a funding milestone, or an important source failure. Each type must identify the owner event/generation that makes it new.

A quote fluctuation or repeated generative summary is not necessarily a new event. Duplicate suppression, retries, preference handling, and delivery acknowledgment stay with the incumbent alert owner. Source correction may require correcting an earlier alert, not minting another independent opportunity. A previously delivered notification does not prove the user read it or acted on it.

Notifications must not reveal unlicensed/premium facts to channels without the right entitlement. A compact notification can direct the user to the protected episode view. The existence of alert research does not create automated trade execution.

### 16.2 Feedback is not an alpha label

User save, click, pass, and watch frequency are useful for product relevance and workload research. They are not ground-truth future-return labels. Rank position affects exposure, and financial outcomes may be missing for users who do not record fills. Do not train a trading model to reproduce the most-clicked or most-confident user choices.

Keep product experimentation and financial strategy experiments separately identified and measured. A presentation test may improve comprehension without altering strategy authority. A strategy comparison must not quietly randomize financial recommendations through a general UI experimentation switch.

### 16.3 Portfolio context is downstream and explicit

The workspace should show existing holdings and overlapping issuer/theme exposures only through authorized Portfolio/Risk reads. Strategy suggestions do not allocate capital. A single stock appearing in two sleeves should reveal the relationship rather than double-count diversification. Any future sizing, hedge, or options allocation work requires its own accepted policy and portfolio-level evidence.

## 17. Reliability, performance, and operating economics

The critical delivery chain is owed market session → qualified source generation → candidate/evidence/strategy evaluation → accepted artifact → served bytes → entitled user. Every stage has a named owner. Provenance is useful only when it supports a reliable, understandable decision.

### 17.1 Functional reliability requirements

A source generation either qualifies or produces a typed degraded result. An optional family can time out without wedging the whole list. Required source failures must block the affected entry state. Forecast freshness and price freshness are separate: a nightly forecast can remain the last accepted forecast while current quote geometry changes, but the relationship must be explicit.

Existing jobs, retries, and publication stages should carry the new consumer contracts. Do not create another scheduler, queue, or “self-healing” control plane. Long tests, scheduled refreshes and workers belong to durable owners rather than a Web principal polling unchanged results.

### 17.2 Performance budget

Adopt the proposed p75 Web Vitals targets only with measured field instrumentation through the existing analytics owner. Keep a separate budget for evidence-detail fetches, current quote updates, and save acknowledgment. Endpoint latency alone is not the whole experience: a fast endpoint can still leave the page blocked by large payloads or expensive layout.

Prefer precomputed compact decision views, progressive detail loading, stable row reuse, and bounded fanout. A page should not recompute the quantitative model in the browser. Expensive model inference should not occur synchronously on every row expansion unless that is an explicitly measured, bounded research feature.

Use exact source/model versions as cache identity through existing caching mechanisms. Entitlement-sensitive content cannot share an anonymous cache. A stale research snapshot can remain viewable with disclosure, but it cannot preserve an expired live entry indication. [X07; I03]

### 17.3 Cost accounting

Track source costs, storage, compute, model inference, worker execution, review/repair, and operational support through existing owners. Require a named user or machine capability for each added cost. Repeated extraction of unchanged documents, large-context refetches, and unnecessary principal polling are avoidable waste.

The experimental model ladder compares accuracy/value and operational costs together. A more complex model must justify longer latency, maintenance, or poorer explanation with incremental decision value. No arbitrary provider budget, unlimited API spending, or unbounded worker fanout is inferred from the Chairman's ambition.

## 18. Monitoring and learning after launch

Monitor source coverage and semantic integrity before model performance. A data feed switching basis or dropping a coverage subgroup can look like market drift. Model-quality monitoring must distinguish changing feature distributions, changing outcomes, selection effects, delayed labels, and delivery defects.

Q22 defines the permitted drift indicators and formal response rules. Unusual behavior can create a review or restrict an affected claim through its existing owner; it does not authorize an autonomous model to invent a new strategy or retry a failed effect. Record the exact generation and preserve the offending evidence.

The learning cycle is bounded: observe changed behavior, attribute it, propose a test, preregister through the incumbent research owner, train/calibrate on admissible data, compare against preserved controls, review, and promote a version with rollback. A recent losing streak is not sufficient evidence to flip the strategy or tune a threshold.

The system must learn from missed opportunities and non-entries as well as managed positions. Distinguish “source never observed,” “human chose not to act,” “policy prevented entry,” and “entry could not be executed.” These are valuable outcomes for different parts of the product, not identical negative labels.

## 19. Onboarding, commercial usefulness, and trust

A new user should select a research goal and see the relevant sleeve without needing to choose a model. Explain that strategy horizon, present entry state, and position sizing are different. Show an actual source-backed example with a clearly stated limitation, not a cherry-picked historical winner presented as typical.

The acquisition surface can demonstrate workflow and appropriately entitled evidence, while detailed research and saved-state actions use the existing subscription/auth system. Do not create a second paywall or assume rights to publish all vendor-derived facts because a user has paid Mastermind. Model-generated paraphrases also need to respect the underlying usage rights.

The proposed onboarding activation is completion of a useful research workflow: identify an opportunity, understand the reason and risk, save deliberately, and return to a meaningful update. Daily trade count, dopamine-inducing alerts, and unsupported accuracy claims are not the product goal.

Before marketing performance, the existing business/legal owners should review the actual product, jurisdiction, claims, and evidence. This plan makes no jurisdiction-specific legal conclusion or return guarantee. Public performance displays must match their actual population, dates, costs, and limitations; evidence from a synthetic check, source test, or backfilled reconstruction is not a commercial live track record.

## 20. Dependency-ordered implementation program

`BUILD_PROGRAM.md` and `BUILD_PROGRAM.json` define B00–B28. Each unit has a useful outcome or an explicitly named prerequisite gate; a source/owner boundary; required inputs; verification and negative cases; research dependencies; and a release limit. These are not active jobs. They must be bound to existing carriers and current custody before implementation.

The build follows four overlapping paths rather than one giant rewrite.

**Truth and usability:** source/session publication, candidate continuity, complete searchable field, evidence dossier, coherent UI, and deliberate watch/readback.

**Scientific improvement:** source-qualified labels, event/group/financial extensions, same-origin experiments, strong baselines, calibration, and prospective comparisons.

**Strategy mechanics:** B4 validity and mandatory facts, accepted earlier-entry policy, tactical management, event holding, and structural core/add behavior.

**Release and operation:** entitlement, performance, alerts, track record, portfolio context, independent acceptance, rollback, and ordinary-refresh proof.

The paths converge only where a capability actually depends on them. A missing analyst-estimate license does not block candidate search. A long-horizon Cycle outcome does not block a source-backed financing dossier. An unfinished model cannot justify displaying a fake probability. A source-custody conflict freezes its lane rather than spawning a replacement owner.

### 20.1 First release: coherent research, not fictional alpha

The first bounded user release should complete the Early Leadership research-to-watch journey using actual accepted owner evidence and honest Availability/refusal. Include missing, cap-displaced, corrected, and unavailable cases. New models stay explicitly experimental or absent. The first user-facing result is a better decision workspace, not a claim that a superior ranking model has already been discovered.

**Avoid a false global dependency:** B06's shared measurement and admissible historical-analysis work does not require completion of every live B4 policy. Only its prospective B4-cell capture branch waits for B05 and the existing preregistration's dependencies. Likewise, current-only specialist evidence does not prevent qualified price/issuer baselines from advancing. The graph records shared prerequisites; activation conditions remain explicit at the affected branch. This is parallel useful work, not permission to backdate unavailable facts or start a held experiment.

### 20.2 Subsequent model and policy releases

Model promotion references exact features, dataset partitions, calibration artifact, trial registration, source/model clocks, controls, and supported cohorts. Entry promotion references a separate strategy/policy version and current owner facts. Holding changes preserve legacy plan semantics and are evaluated separately. The final UI can show these pieces side by side without implying that one promotion grants all other authority.

### 20.3 First three bounded execution packets

**Packet A — completed technical evidence during current RTH.** Continue on the incumbent #7581 integration carrier and relevant source owner after current custody/review reconciliation. Consume R3's exact finding. Determine whether a current-session predecision confluence receipt genuinely exists; otherwise freeze the explicit source-session/validity/revocation contract. Required proof includes previous completed session, current-session valid receipt, late emission, stale/expired evidence, retraction, shortened sessions, basis mismatch, and native adapter-to-B4 behavior. No date relabel or PASS injection.

**Packet B — complete searchable candidate journey.** Consume the incumbent #7572 and publication #7180 boundaries. Preserve board pool versus B1 versus pre-B1 populations and current corrected generation. Prove that a cap-displaced, unscored candidate remains searchable in the entitled browser with the true reason, honest score null, coherent detail, and correct WatchStore save/readback. Do not claim that a component screenshot or simulated auth callback is deployed acceptance.

**Packet C — source-ready event and cycle evidence.** Extend the existing Earnings/D5 and GMI/financial source owners with the narrowly needed comparable facts and dated histories. Produce an actual company-event dossier and an actual financing/per-share scenario from source-backed inputs, with missing data and corrections preserved. No study outcome read, candidate-anchor invention, model fit, or live entry permission is needed to prove this research utility.

Packets A and B must not duplicate a live or unconsumed incumbent review operation. Packet C splits into path-disjoint owner work only after source custody is clear. Full runnable code-level task plans are minted against the exact accepted source head when each slice is admitted; this master program does not pretend to provide compilable unknown future APIs.

## 21. Astra, Fable, and external-fabric execution

The Chairman's requested mix is preserved: concentrated Astra Pro research for difficult quantitative and architectural questions, and Fable principal integration for the genuinely difficult cross-owner build boundaries. Routine engineering belongs to the least-scarce capable admitted workers. Neither importance nor a large task automatically justifies Fable. [I04]

### 21.1 Astra research sessions

Each research session receives one bounded decision packet from Q01–Q24: the exact unresolved question; mechanism and alternatives; relevant source revisions; admissible data and protected-outcome boundaries; prior killed-equivalence references; what would falsify the proposal; and the decision artifact a builder can consume.

A session should return a clear supported conclusion, narrower alternative, rejection, or non-identifiable result. It should not generate a new broad master plan every time. Complex research can span several sessions, but each ends with a compact current-owner checkpoint and exact next uncertainty. Unchanged raw tool history is not rehydrated.

Use Pro only when the actual current cognition admission, task class, and capability support it. A user-reported mode is not a platform attestation, and no duration or metered budget is fabricated to obtain admission. Comment-write success does not prove source-edit, merge, deployment, or fabric-admission capability. The execution turn checks the action family it actually needs.

### 21.2 Fable principal work

A suitable Fable integration assignment is reconciling the versioned B1/B3/D5/B4/strategy/plan/publication contracts into a coherent live decision path, where contradictions span several existing owners and principal continuity materially reduces failure. The routing receipt must say why an ordinary bounded worker is insufficient.

Fable should freeze the hard seam, delegate bounded changes through the existing admitted fabric, review material returns, and prove the integrated user/machine outcome. It should not spend scarce principal capacity serializing straightforward JSON or polling CI. An independent reviewer remains independent of the source author, including when Fable owns the integration.

### 21.3 Bounded workers and review capacity

Ordinary extraction, adapters, tests, source fixtures, UI components, and standard technical reviews use the current cheapest capable eligible avenue. Capability tier, tool harness, host, account, subscription, and source authority are separate dimensions. No concrete provider credential, host, or receiver is selected by this document.

Concurrency is bounded by admitted global capacity, writer independence, budget, and the parent's ability to consume reviews. Reserve review/repair capacity before opening more work. Several tightly coupled interface changes may be safer under one writer than split across many apparently idle workers.

### 21.4 Required work packet

A worker brief includes the current canonical source and operation, permitted files/effects, consumed and produced interface, parent specification digest, accepted decisions, explicit non-goals, failure semantics, red/green and adversarial requirements, real consumer proof, return path, and stop/escalation conditions. It carries the necessary source excerpts and not the whole CEO transcript.

Existing Executive admission and placement govern execution. Delivery, acknowledgment, START/RUNNING, result, review, merge, deployment, and acceptance are different states. Missing fabric capacity does not automatically stop lawful principal work before any conflicting effect, but it does not permit a duplicate queue or raw provider-spawn workaround.

No worker is running because this plan names it. No source writer is released by a new chat. An unknown modifying effect stays on its original carrier until reconciled.

## 22. Review, testing, and proof

The verification program has five layers, and each answers a different question.

**Contract correctness:** closed identity/state/permission fields, basis and clock handling, missingness, correction lineage, stable serialization, and refusals. A schema test is not a model-performance test.

**Native integration:** real accepted producer bytes through real adapters, source-owner APIs, private payloads, and outcome-owner write/read contracts. Hand-constructed fixtures are useful negative controls but not sole proof that the actual source path works.

**Scientific qualification:** preregistered same-cohort comparisons, untouched date blocks, effective sample accounting, costs, tail/coverage constraints, and calibration. Synthetic arithmetic is not evidence of alpha.

**Product and security:** actual entitled user journey, anonymous/unentitled refusal, vendor-rights boundaries, same-date corrections, focus stability, mobile/desktop, EN/ZH, and independent dark/light review. Do not use an auth bypass as the production acceptance path.

**Natural continuity:** the accepted deployment processes a real source generation and a subsequent ordinary refresh without manual seeding or special commands. Receipt persistence, alert behavior, user actions, and historical decisions remain coherent.

`ACCEPTANCE_CATALOG.json` preserves the 36 R3 and 48 R4 cases with their original references and unexecuted status, adds the integrated R5 cases, and maps them to build units. It is a required-test catalog, not a test report. The packet verifier checks mapping consistency and hashes only.

### 22.1 Independent review and defect disposition

Before integration, obtain a genuinely independent exact-artifact/source review suited to the risk. The reviewer checks the original user job, not only whether tests pass. Material research review challenges information leakage, alternative mechanisms, denominators, and promotion claims. Product review challenges usability and adverse states. Source review challenges ownership, effects, and hidden dependencies.

A material issue returns to its existing carrier. Preserve reviewed/accepted evidence and repair only the invalidated scope. A new SHA without a relevant semantic correction is not progress. Two equivalent cycles without new evidence require changing tactic or ownership through the existing process, not a third status document.

## 23. Rollout, rollback, and legacy continuity

Do not replace the whole live product in one switch. First introduce a private or clearly controlled integrated research view. Then advance exact capabilities through accepted release stages, keeping the incumbent V3 control and original records intact.

A release receipt identifies source/build version, strategy/model/policy versions, accepted data generation, feature flags through the existing owner, migration state, evidence, and rollback target. Do not invent another release registry. Rollback can remove a new read view or model/policy promotion without deleting appended evidence, user actions, original grades, or legacy plans.

### 23.1 Safe rollback examples

If a new model's inputs become invalid, withdraw that model's current claim through its owner and show the last lawful control or unavailable state. Do not regenerate old decisions using the fallback and call them original.

If a new UI snapshot is inconsistent, retain a clearly dated last accepted read-only snapshot or a typed unavailable view. Do not leave a stale green entry action active.

If an owner write response is ambiguous, reconcile the exact operation on the same carrier. Do not retry through another host, API, or fresh job because the user interface did not show success.

If a schema migration fails, preserve the existing owner record and the exact pending migration evidence. A destructive wipe is not a rollout strategy. User watch and portfolio state require stricter preservation than reconstructible presentation caches.

### 23.2 Legacy grade and plan preservation

Keep historical ruler versions and their limitations. New close/intraday risk metrics do not rewrite the old `fwd_mdd` meaning. New strategy definitions do not reclassify historical plans or assign contemporary group membership to past decisions. A previous record may be displayed beside a corrected analytical view, but the two must remain distinct.

Retire old user-facing fragments only after their useful jobs and required history are covered by the replacement. Removing a legacy card does not authorize deleting the data or releasing another source writer.

## 24. Risks, unresolved decisions, and bounded gates

`DECISION_REGISTER.json` names the unresolved decisions, their existing owner, required evidence, forbidden shortcut, and blocked consumers. An unresolved gate freezes only the affected work. It is not a reason to stop research visibility or an excuse to fabricate a parameter.

The highest-priority risks are: source-time versus decision-validity confusion; limited B1 anchor origination; current-only group/event discovery masquerading as historical coverage; uncalibrated confidence; survivor and financing omission; model selection on protected outcomes; mismatch between new-entry and holding semantics; user-action persistence claims beyond the current owner; premium/rights leaks; and over-parallelized conflicting writers.

The explicit decision outputs include a source validity/revocation contract, new expert anchor/re-arm eligibility, real data availability/rights matrix, approved strategy/holding versions, user feedback/episode mapping, numerical economic/statistical margins, review/admission bindings, and exact production proof surfaces. Every decision has a finite artifact and an acceptance owner. Their absence is visible rather than hidden behind “research needed.”

### 24.1 Budget and uncertainty

This plan makes no invented dollar, worker-count, return, or completion-date commitment. Before each admitted unit, its owner estimates effort/cost under the actual surface and budget, includes review/repair and data expenses, and sets an enforceable limit where required. Research can be ambitious without granting unlimited spending.

Unknown source histories may reduce model scope. Unknown statistical power may require a longer accrual period. Neither means all progress must stop: qualified historical baselines, genuine prospective capture, evidence dossiers, and product integration can advance independently. The exact limitation must be carried into what the user sees and what the model claims.

## 25. US-first completion and later markets

CN, HK, and CA remain deferred until the US flagship reaches its declared acceptance. Preserve shared interfaces so later market-native adaptations are possible, but do not spend this program's critical path on a global cutover.

Later markets require their own calendar, currency, listing/security identity, corporate-action and suspension semantics, source licensing, market microstructure, economic regime, calibration, and user proof. A US coefficient or entry rule does not transfer automatically. The repeatable asset is the measurement and owner-bound architecture, not copied thresholds.

Before declaring the US complete, answer: can each advertised persona perform the task; are all three initial sleeves honest and useful at their advertised authority; are meaningful omissions exposed; does the served path reflect accepted source/model/policy versions; are decisions and outcomes durable; do ordinary refreshes and rollback work; and is there any useful uncompleted in-scope promise being silently renamed as future work?

A later-sleeve research queue can be explicitly unpromoted without invalidating a bounded US launch. However, the broad roadmap remains part of the program, and any rejected mechanism has a recorded reason. The label “final master plan” means complete program design, not permanent perfection or authority to fabricate positive research results.

## 26. Immediate continuation and finalization boundary

The next unit is **R5 source publication/adversarial review and first-wave binding**, not another general research audit. Use this exact packet and its manifest. Publish the proposal under the existing owning research path only after current source-writer and repository gates are satisfied, retain the parent #6805, and obtain an independent review of the integration and scientific contradictions.

In parallel where lawful and path-disjoint, reconcile the existing #7581 validity finding and #7572/#7180 delivery boundaries. Do not originate duplicate review children. Select the first genuinely ready unit in B01–B07; a bounded owner decision or positive release proof is more valuable than another census of all Prophet PRs.

Recommended next interaction surface: **Extra High for publication, exact-source reconciliation and fabric admission**, while the designated hard Q-packets remain candidates for separately admitted Pro research. This is a task-fit preference, not a claim that Pro lacks comment writes. The current session has performed records-only comments, not source-edit/merge/deployment or fabric execution tests.

A fresh conversation is appropriate at this large synthesis-to-execution boundary. Resume from final #6805 comment5791272310 and the packet manifest, not the entire preceding conversation. This does not transfer custody, release a lease, or claim an autonomous wake. The final checkpoint states all material effects and unresolveds.

**Program disposition at this boundary: CHECKPOINTED_CONTINUATION. Mission complete: false.** A verified master-plan candidate is the output of this phase. No model, strategy, test catalog, or future build graph is promoted merely by being included.

## References and evidence scope

### Internal inputs and fresh sources

- **R1:** `inputs/PROPHET_US_RESEARCH_R1.md`, SHA-256 `96d0ab34f5db94537fe60b493af166b0c50ca8eac2b89641703d9bb290166465`.
- **R2:** `inputs/PROPHET_US_MEASUREMENT_R2.md`, SHA-256 `32bf1ddba37aa269469d7fb641dcf862ff4ea0aad3a567acdffa857cb26de19e`.
- **R3:** `inputs/PROPHET_US_EARLY_LEADERSHIP_R3.md`, SHA-256 `4ad7b39e8b4916029755f863d3b56ba0dc30d75ff46d95b031ceb24cb8946ff5`.
- **R4:** `inputs/PROPHET_US_EARNINGS_CYCLE_R4.md`, SHA-256 `e9464a12b8faba1e61b2d8ed6cb3d508f7c99efd41a6e3b4ee715a849fd593d2`.
- **I01:** Macro #6805 comment5790671385, final R4 cumulative checkpoint, freshly read during R5. Earlier material rulings and research sources are indexed there and in the reproduced dossiers; no broad outcome set was reopened.
- **I02:** Mastermind protected `89582a372aa2a57ec500868ce6d79cd156219445`; same-pin INDEX, ACTIVE_EXECUTION, WEB_CEO_DELEGATION, CLOSEOUT.
- **I03:** Macro `AGENTS.md` lines1–180 at `c9978765aa0085eba0213430284cb4b41065d4e2`, connector-reported blob `ba426238eb93faf478d05e66c5b4168fcc1a74d3`. Navigation/design/workspace obligations were inspected; this was not a full local delivery boot or source-write qualification.
- **I04:** `docs/EXECUTIVE_WORKER_ROUTING_CHAIRMAN_ADDENDUM.md` at the I02 pin, lines1–310; relevant routing/independence and economics provisions consumed for planning, not runtime activation.

The prior dossier references preserve their original access limitations. A literature summary is not an empirical replication, and a source-code characterization is not production proof. R5 newly verifies packet consistency and cited documentation, not the underlying market hypotheses.

### Public primary references refreshed for R5

- **X01 — XGBoost, Learning to Rank:** https://xgboost.readthedocs.io/en/stable/tutorials/learning_to_rank.html . Official documentation inspected; query groups, pairwise LambdaMART and relevance-score semantics. No library installed or Prophet model fitted.
- **X02 — Guo et al. (2017), On Calibration of Modern Neural Networks:** https://proceedings.mlr.press/v70/guo17a.html . Publisher abstract inspected; calibration motivation, not stock-market validation.
- **X03 — Harvey, Liu, Zhu, Cross-Section of Expected Returns:** https://www.nber.org/papers/w20592 . Primary abstract inspected; multiple-testing discipline, not a universal numerical Prophet promotion threshold.
- **X04 — SEC EDGAR API documentation:** https://www.sec.gov/search-filings/edgar-application-programming-interfaces . Official documentation inspected; frame-period/last-filed semantics, not an analyst-expectation dataset.
- **X05 — FRED real-time periods:** https://fred.stlouisfed.org/docs/api/fred/realtime_period.html . Official vintage semantics inspected; provider availability is not identical to user-system capture.
- **X06 — W3C status messages:** https://www.w3.org/WAI/WCAG21/Understanding/status-messages . Official explanatory guidance inspected; implementation still requires actual accessibility testing.
- **X07 — Google Web Vitals:** https://web.dev/articles/vitals . Official thresholds and field/lab distinction inspected; proposed product targets only.
- **X08 — Geifman and El-Yaniv (2019), SelectiveNet:** https://proceedings.mlr.press/v97/geifman19a.html . Publisher abstract inspected; risk/coverage framing, not financial validation.
- **X09 — Census M3 historical series:** https://www.census.gov/manufacturing/m3/historical/timeseries.html . Official source-scope and revision note inspected; no dataset collected.

Additional domain literature is retained with its original reading limits in R1–R4. Direct NBER opens for w12362 and w20984 returned access errors in R5; no new full-paper reading is claimed. Their earlier summaries are not refreshed empirical evidence.