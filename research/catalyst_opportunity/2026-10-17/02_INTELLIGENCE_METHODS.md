# Intelligence methods and domain specifications

Companion to `01_MASTERPLAN.md`. All algorithms and numerical defaults in this chapter are **proposed research specifications**, not fitted results, accepted trading rules or currently operating product behavior. Bracketed sources resolve in `06_EVIDENCE_REGISTER.md`.

## 1. Separate five questions before computing anything

For an incident, theme or security, retain five distinct objects of inquiry:

- What was actually observed, by whom, when, and with what revision history?
- What future event or scenario has become more or less plausible?
- What economic mechanism could affect a particular issuer or instrument?
- What expectations and market behavior are already observable?
- Is there a causal, executable timing setup under the existing decision rules?

A strong answer to one question cannot silently fill missing answers to the others. In particular, a physical-event probability, an economic sensitivity, a price-implied distribution, a research priority and an expected return are different quantities. No multiplication of arbitrary 0-100 scores is permitted.

## 2. Event understanding: claims, incidents and developments

### 2.1 The unit of reasoning

An article is a container, not an event. Extract attributed claims; cluster claims into an incident or company-event reference; represent a material new development as a revision to that evolving case. A continuing regional crisis can contain many distinct attacks, negotiations, sanctions and supply interruptions. Do not collapse them into one undifferentiated topic, and do not count every article as a new incident.

A proposed claim view contains the exact source-revision reference, source span when licensed, original-language text reference, translated interpretation, actor/action/object, geography, event-time interval, attributed speaker, assertion status, uncertainty, and the observation/availability clocks. The native source store owns the record; the view does not create a second evidence database.

Possible assertion statuses are reported, independently corroborated, disputed, retracted and unresolved. They describe evidential treatment, not reality with certainty. An official statement is primary evidence that the institution made that claim. An interested party's statement about its adversary still requires appropriate qualification.

### 2.2 Ordered, inexpensive-first analysis

1. Validate transport, rights, clock and source revision. Refuse malformed or unauthorized fields before expensive processing.
2. Resolve item identity and exact duplicates through qbus. Preserve updated and deleted versions.
3. Group likely copies by citation, wire origin, content similarity and publication sequence. Unknown lineage remains unknown.
4. Apply broad event-family routing. Preserve a sampled reject stream to measure recall; a cheap filter must not irreversibly erase all hard cases.
5. Extract structured claims with a constrained model or deterministic parser. Require source-span support for consequential numbers and actor relationships.
6. Compare with the prior eligible incident/company state. Determine whether this is genuinely new, a repeated assertion, a correction, an operational milestone or a change of magnitude/timing.
7. Route only material changes to deeper mechanism analysis. Cache by source revisions, contract and model version, never solely by ticker or headline.
8. Seek contrary evidence and plausible alternatives before creating a stronger assessment.

The deep reasoning unit is the changed case, not each article-ticker pair. One material announcement can generate one reviewed mechanism analysis and many inexpensive referenced presentations.

### 2.3 Novelty is multidimensional

Store factual novelty, source novelty, magnitude change, timing change and attention change separately. A first report from a new outlet may add no fact. An old story becoming viral can create a market-attention event without creating a new physical event. An amendment can reduce the credibility or magnitude of a prior claim. All three may matter, but for different reasons.

Report counts normalize against the source/language/region observation process and its availability. A surge caused by adding a new feed is a coverage change, not a geopolitical acceleration. GDELT's own documentation emphasizes the need for normalization as news coverage changes. [X01]

### 2.4 Incident split, merge and correction rules

Stable source IDs never change when the incident interpretation changes. A split or merge appends an alias/relationship revision through the existing owner; prior assessments retain the grouping actually used at issuance. A later discovery that several reports described one attack must not rewrite historical independent-witness counts. Instead, show the correction and preserve both as-known and current interpretations.

A correction that weakens an alert must reach users at least as reliably as the original escalation alert. No silent deletion of failed calls is allowed. Late-arriving older evidence can update the current case but cannot be backdated into an earlier issued prediction.

## 3. Geopolitical and supply-disruption intelligence

### 3.1 State vector, not an inevitable ladder

Represent the situation on several axes: diplomatic engagement, threats/rhetoric, public military posture, sanctions/enforcement, verified kinetic activity, shipping or infrastructure impact, retaliation, and containment/de-escalation. The axes can move in different directions. A deployment can deter conflict, prepare for it, or be routine; its interpretation depends on evidence and baseline.

Each assessment includes the previous view, new evidence, alternative explanations, what would favor escalation, what would favor de-escalation, affected economic channels and a valid decision horizon. Routine exercises, scheduled rotations, recycled advisories and unsupported social posts cannot be treated as imminent-strike confirmations.

Publicly available strategic context is sufficient for this financial product. Do not add tactical targeting, restricted intelligence or live individual military tracking. Any future imagery/AIS enrichment must have lawful source access, reliable timestamps and a financial-use justification; it is not a launch prerequisite.

### 3.2 Initial forecast targets

Begin with a small, predeclared target set rather than a universal war probability:

- A newly verified direct state-to-state strike involving a specified actor pair within 72 hours.
- A new, independently verifiable material interruption to a named energy/shipping corridor within seven days, under an explicit duration or flow-impact label.
- A qualifying de-escalatory development within seven days, defined by actual agreement/implementation evidence rather than optimistic rhetoric.

These targets can overlap. Their probabilities do not have to sum to one. Mutually exclusive scenario probabilities may sum to one only when the scenario set is genuinely exhaustive and its definitions are frozen.

The risk set is every eligible observation time for the declared actor-pair/corridor universe, including quiet periods and failures. Do not choose only weeks that later produced a crisis. Record target resolution, unknown labels, postponed resolution, and independent evidence for adjudication. UCDP can support selected retrospective labels where its event definition matches; its monthly candidate cadence does not make it a live warning source. [X03]

### 3.3 Baselines and model order

Start with empirical horizon-specific prevalence, persistence of the last state, and a simple regularized model over explicitly available features. Candidate features include independently sourced new acts, confirmed disruptions, changes in diplomatic posture, time since the last qualifying event, actor-pair background and coverage-adjusted novelty. Use a discrete-time hazard or horizon classifier only after the label/risk-set design is coherent.

A hazard model's multi-period cumulative probability must use the product of conditional survival terms over the declared periods; a daily probability cannot simply be multiplied by three and relabeled a 72-hour probability. Overlapping rolling forecasts require dependence-aware evaluation.

Only then compare structured model synthesis or an ensemble. Online change-point detection is an optional challenger for shifts in observed event intensity; it does not itself forecast war or establish causality. Hawkes/self-excitation models are deferred until deduplicated event identities and meaningful temporal denominators exist, because article echo otherwise masquerades as contagion. [X11, X17]

The initial product can display rising/unchanged/falling evidence with a clear rationale while probability is unavailable. Model probabilities require calibration and the exact advisory permission specified in the evaluation chapter.

### 3.4 De-escalation and nonconfirmation

Include a symmetric disconfirmation path: reclassified notices, withdrawn allegations, resumed shipping, restored production, verified ceasefire implementation, negotiations with concrete progress, or a price premium unwinding. An absence of reports during a source outage is not de-escalation. Retain the last known material fact with its age and coverage caveat.

## 4. Market-first theme discovery

### 4.1 Universe and observation basis

The release universe is a versioned set of instruments with valid identity, calendars, corporate-action handling, rights and usable data. Start with a reliable liquid US-equity cohort and actual admitted thematic membership. Broaden only with explicit coverage admission. The initial ticker-news implementation's S&P-oriented universe does not automatically cover small-cap biotech, foreign listings or every thematic constituent. [I05]

Separate discovery coverage from trading eligibility. An instrument may be relevant to the event yet unsuitable for a particular entry policy. Missing identity or sparse data remains visible without being admitted to execution.

Consume Group Reads, Theme Scoring and Sector Pulse observations rather than recomputing their canonical outputs. Where intraday features do not exist, implement them through the market/group owner as a new versioned observation, not as a competing theme-ranking engine. [I08, I09]

### 4.2 Initial feature set

Use completed five-minute bars for the first intraday research detector. Retain one-minute source observations when licensed, but avoid making a sub-second or second-bar pipeline a prerequisite. Daily context uses completed sessions; incomplete current-session daily bars must be labeled provisional.

For security i, benchmark b and horizon h, define market-relative log return as `RS(i,b,t,h) = log(P_i(t)/P_i(t-h)) - log(P_b(t)/P_b(t-h))`, using synchronized eligible observations and the same return basis. This is market-relative performance, not automatically factor-adjusted alpha.

Retain both whole-theme outperformance and the security's behavior versus its relevant sector. A beta/sector-residual view is a separate feature estimated from data available before the decision; neutralizing the whole sector move and discarding the raw view would remove precisely the rotation we want to detect. Benchmark membership and self-inclusion are documented; use a leave-one-out or separately defined benchmark where material.

The compact initial feature family is:

| Dimension | Proposed measurement | Important limitation |
|---|---|---|
| Relative behavior | 30- and 120-minute synchronized RS; 5- and 20-session context | High existing RS is not necessarily an early turn. |
| Acceleration | Change in the short-horizon RS estimate versus its earlier eligible value | Do not count derivatives of the same price series as independent evidence. |
| Participation | Fraction of eligible members with positive RS and constructive causal structure | Denominator excludes only declared unavailable instruments; report excluded counts. |
| Group robustness | Equal-weight and cap-weight returns, median member return, leader contribution | One large component must not impersonate broad participation. |
| Volume | Cumulative traded value or volume relative to the same time of day in prior valid sessions | OHLCV does not identify institutional buyers or hidden accumulation. |
| Compression/expansion | Trailing range and realized-volatility compression followed by expansion | Must use trailing, not centered windows. |
| Extension | Distance to eligible support/VWAP and trailing ATR or intraday volatility scale | A good catalyst can still be too extended to review as an entry. |
| Liquidity/quality | Spread when available, eligible volume, quote/bar age, halts and missingness | No bar may mean no eligible trades, not an outage or zero economic activity. |

For time-of-day volume, compare like session segments and calendar types. Do not compare 10 a.m. cumulative volume with an entire prior day. Treat half-days separately. A minimum usable history policy must return unavailable rather than silently use a thin or distorted denominator.

### 4.3 Proposed D0 research default

The first reproducible detector uses a limited parameter set: five-minute completed observations; at least five eligible theme members; at least 80% of the declared member set observed; at least 60% showing positive short-horizon market-relative behavior; short-horizon RS improvement in the top decile of the eligible theme distribution; and persistence across two completed five-minute observations. These are **initial research defaults**, not empirically justified optimal thresholds or a live buy rule.

An event-first watch does not need to satisfy D0. A narrow, genuinely material single-company catalyst can enter through its own issuer path without five peers. A theme with fewer than five members can be shown as a narrow cohort, but must not receive D0's broad-participation label.

The specification deliberately makes few choices. Freeze D0 before inspecting outcomes, compare it with the incumbent baseline, and change it only through a recorded development version. No post-hoc grid of dozens of windows followed by promotion of the best-looking one.

The current two-session theme confirmation remains unchanged. The new five-minute policy is a separate low-authority attention experiment, not a reinterpretation of those confirmed alerts. [I10]

### 4.4 Ranking and attention

Do not claim the largest numerical score is the best investment. Use transparent research ordering: newly material source corrections or risks first; then cases with a new causal setup transition and credible exposure; then unresolved but substantial market anomalies. Within a tier, expose the policy's freshness, novelty, coverage and burden criteria.

Cap simultaneous repetitive cases from the same incident and economic family. A defense incident affecting ten names should usually create one expandable case with distinct security timing rows, not ten phone notifications. Reserve some discovery attention for unheld/unfollowed sectors so personalization does not recreate the user's blind spot.

## 5. Cross-asset confirmation and alternative causes

Cross-asset evidence tests a mechanism; it does not prove the mechanism uniquely. Examples include oil supply-risk behavior, defense participation, shipping costs, dollar/real-yield changes, credit stress and broader equity risk appetite. Retain each observation's own clock and explanatory alternatives.

Oil rising while growth-sensitive assets weaken is compatible with supply concern but not conclusive. Oil can rise because of demand, inventories, OPEC decisions, currency changes, positioning or technical factors. An existing commodity residual-shock model can identify divergence from its fitted macro drivers; its residual is not a measured war premium. The discontinued New York Fed Oil Price Dynamics Report is methodological context, not a live data dependency. [I15, X18]

Cross-asset agreement receives no automatic independent-evidence multiplier. Oil, energy equities and an oil ETF may largely encode the same underlying price move. Price behavior used to discover a case cannot be used again as an independent confirmation of that same case without explicit dependence treatment.

## 6. Economic exposure and expectations

### 6.1 Edge contract

Every meaningful event-to-company edge states: source actor/project/program; issuer/security identity; company role; mechanism; positive/negative/ambiguous sign; effective and known-at interval; plausible realization lag; exposure basis; capacity or financing constraint; existing expectation baseline; uncertainty; source references; and a falsifier.

Distinguish structural association, commercial relationship, scenario sensitivity and observed market co-movement. A company can belong to a defense theme without producing the equipment implicated in the event. A supplier's gross contract value is not attributable revenue or incremental profit. A project NPV is not equity value without ownership, funding, debt and dilution treatment.

Where a numerical scenario is supportable, show its arithmetic and units. For example, an incremental contribution estimate needs attributable quantity, realized unit economics, capacity and timing assumptions; an equity implication additionally needs discounting, financing and share count. Do not add several scenario estimates that describe the same future order or supply effect.

### 6.2 Expectations and priced behavior

The product should show what can actually be observed: prior guidance, admissible consensus, analyst revisions, prior event discussions, price already moved, options-implied volatility and skew where licensed/qualified, and positioning proxies with their actual limits. Do not output a universal percent-priced-in number.

Separate immediate sentiment repricing, medium-term earnings revision and longer-term economic realization. A repeated well-known threat can have little incremental impact; a small unexpected development can matter more. Options prices describe risk-neutral pricing under assumptions, not a directly observed physical-event probability. A high call volume does not by itself prove opening bullish purchases.

The scenario screen can compare conditional paths without claiming their probabilities are calibrated. Expected returns may be displayed only where both the conditional payoff model and the probability model have compatible, qualified definitions.

## 7. Causal security-level timing

### 7.1 Four initial setup families

**Emerging-base break.** A predeclared trailing base exists before the breakout. The signal becomes observable only after the confirming bar closes. Volume and market-relative behavior qualify the observation, with extension measured against the pre-existing structure.

**First orderly pullback.** A preceding impulse is already observed; the pullback does not break the declared invalidation structure; selling pressure/range contracts; a subsequent causal reclaim is observed. The low is not known in advance merely because it is the eventual minimum.

**VWAP/structure reclaim.** A completed observation reclaims an explicitly session-anchored VWAP or prior structure with sufficient eligible liquidity. Session and anchor selection are fixed before outcomes. Overnight and regular-session VWAP are not silently interchanged.

**Bottoming transition.** Declining downside momentum, improved relative behavior and a confirmed structural change create a watch. A pivot requiring right-side bars has two clocks: the bar at the putative pivot and the later time at which confirmation became available. Alert and simulated entry use the latter.

These are research families to map onto the existing Radar detector registry, not permission to register its reserved F1 fusion detector prematurely. Existing detector semantics and independent validation remain binding. [I12, I16]

### 7.2 Entry and risk interface

A timing row states the instrument, observed setup family, eligible evidence cutoff, confirmation time, current market price age, reference structure, invalidation condition, extension state, spread/liquidity availability, relevant event/earnings hazards and qualification status.

Do not originate trade sizing from an LLM summary. The existing entry/decision owner determines whether an advisory entry zone or risk level is authorized. Before qualification, the product can describe an observed pattern and invite review without declaring a profitable buy signal.

Simulation uses the first actually executable observation after processing and delivery delay. A strategy that requires a bar close cannot fill at a more favorable price earlier in that same bar. Limit orders require explicit touch/queue/fill assumptions; touched price is not guaranteed execution. Slippage, gaps, partial fills, halts and canceled or corrected trades must be represented. Weekend stops do not guarantee a bounded loss at their stated level.

## 8. Specialist domain playbooks

Every playbook uses the shared coverage, clocks, evidence, revision, identity, product and evaluation contracts, but retains its domain's native events and economics. Each requires one ordinary real case plus adverse, missing and revised cases before operational acceptance.

### 8.1 Defense and Government Revenue

Separate geopolitical demand expectation from funded demand, actual company participation, shareholder economics and observed market recognition. Consume the incumbent GovRev/FMS/program ontology and the merged investor product. Budget request, authorization, appropriation, contract award, task order, obligation, delivery, outlay, backlog and revenue recognition are different states and amounts. FMS notification ceilings are not realized sales. [I01, I03, I04]

Assess prime/subcontractor role, program relevance, equipment family, replenishment need, production capacity, supply bottlenecks, funded backlog, contract type, margin pressure and execution charges. A positive order headline can coexist with poor cash economics. Preserve fiscal period, currency, cumulative-versus-delta basis and program/recipient identity.

First integration case: a documented program or company exposure is linked to an independently observed geopolitical or procurement development, alongside contemporaneous theme/security behavior. Negative cases include an analyst upgrade with no new geopolitical evidence, a proposed sale with no funding, a contract amendment counted twice, a delayed delivery, and de-escalation after a risk-premium rally.

### 8.2 Energy, oil, nuclear and grid

For oil, separate supply disruption, demand improvement, inventory surprise, refining constraint, transport/bypass capacity, sanctions enforcement and positioning. The EIA chokepoint baseline helps establish exposure, but historical flow estimates do not measure current interruption. Weekly inventories and hourly power observations retain their actual release cadence. [X06, X07]

Issuer channels include production geography, commodity mix, hedges, cost structure, integration/refining exposure, transport constraints and tax/royalty regimes. Higher crude can help an upstream producer while hurting a fuel-intensive firm; tanker effects depend on route availability, insurance, fleet positioning and operating risk.

For nuclear/grid, separate permit/licensing, financing, construction, fuel supply, offtake, interconnection and commissioning. A policy announcement is not an operating plant or recognized supplier revenue. Initial cases must include a real project/company role, a delay or financing shortfall, and a cost overrun. Do not reduce the entire Energy/Grid scope to oil prices or nuclear permit headlines.

### 8.3 BioCatalyst

Keep trial, asset, indication, endpoint, application, review cycle and jurisdiction identities. Registry completion dates are not topline release dates. Regulatory action, clinical efficacy and commercial uptake are separate outcomes. Positive trial news can still imply financing/dilution or weak commercial economics.

Use the existing Bio operational stores and Company Intelligence disclosure relationship, preserving their current identity and admission limits. Model partner/geographic rights, competing standards of care, endpoint relevance, cash runway and financing through their actual owners. The financial baseline must not be recreated in a Bio-local account engine. [I01]

Initial cases: a disclosed application or trial milestone with correct timing/rights, a failed or mixed endpoint, a delayed readout, an ambiguous issuer mapping, and a financing event. Native success probabilities must not be relabeled equity-upside probabilities.

### 8.4 MedTech

Keep device identity, regulatory pathway, jurisdiction, evidence quality, reimbursement, purchasing/adoption and commercial capacity distinct. Clearance, approval, coverage and market adoption are not synonyms. Repair eligibility before all derived historical states; hiding a future source ID at the final render does not undo leakage into materiality or relationship flags. [I01]

Include a regulatory milestone, a reimbursement gap, a safety/recall event, an unavailable commercial baseline and a later source correction. Economic scenarios use supported market access, pricing and attributable company exposure rather than generic total addressable market claims.

### 8.5 Semiconductors and technology infrastructure

Distinguish design announcement, qualification, design win, volume order, production ramp and realized revenue. Attach node/product/customer identity, capacity, capex commitment, pricing/mix, utilization, inventory and export restrictions. Competitive substitutions and bottleneck relief can reverse the sign across suppliers.

A large announced investment is not a realized purchase order for every thematic constituent. Read-through requires an actual customer/supplier or technology role. Initial cases include a real customer-capex change, a restriction or delayed ramp, and a case in which the same headline helps one supplier and harms another.

### 8.6 Resources and mining

Distinguish exploration result, mineral resource, economically recoverable reserve, permitting, funding, construction and production. Preserve attributable ownership, royalties/streams, recovery assumptions, capex/opex, commodity/currency sensitivity, debt and dilution. Do not map gross project value directly to common equity.

Initial cases include a material project milestone, a funding requirement that dilutes the benefit, a permit setback, a cost escalation, and an unclear ownership relationship. Sparse small-cap trading and incomplete fundamentals must constrain timing claims rather than be filled with sector averages.

### 8.7 Special situations

Use transaction, parties/roles, security, terms, financing, conditions, approval/vote, closing, termination and consideration history. Target, acquirer, creditor and indirect holder exposures are distinct. Deal completion probability, expected consideration and the security's price path need separate treatment.

Consume the incumbent event-study and transaction owners. Preserve the held evaluator repairs; unmatched high-return events must not boost a paired event/control inference. Include changed terms, financing failure, mixed cash/stock consideration, delisting/cash conversion and a break case. [I01, I14]

### 8.8 Earnings, policy and broad-sector extension

Earnings intelligence supplies expectations, actuals, guidance and company-event revisions; it is not absorbed into a generic news classifier. Policy can affect health-care reimbursement, staples input costs, trade barriers, taxes and subsidies. The same all-market attention mechanism should surface those cases without requiring the user to have selected the sector.

The common engine is a reusable workflow; event labels and financial mechanisms remain specialist. Expanding to another geography or asset class requires its calendars, identity, rights and outcome conventions, not merely translating headlines.

## 9. Graceful failure and honest abstention

When news is missing but market data are sound, continue market-first discovery and mark the explanation unresolved. When market data are stale but a major event is verified, show factual event risk without a current entry judgment. When exposure is unresolved, keep the incident visible but refuse the security-specific economic claim. When a setup is extended, keep the thesis while withholding entry urgency. When a source correction invalidates a premise, update the case and notify affected followers.

The expected advantage is not perfect prediction. It is a system that observes more of the declared market than a human can, distinguishes new information from noise, prioritizes investigation without laundering guesses into facts, and learns which combinations actually improve decisions.
