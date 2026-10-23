# Policy Behavior, Revealed Preference, and Strategic Market Support — Research + Forward Program

**Date:** 2026-10-07 UTC  
**Status:** RESEARCH / ZERO-AUTHORITY / BUILD-READY PROGRAM DESIGN  
**Chairman objective:** make Mastermind materially better at distinguishing public rhetoric from revealed policy preference, identifying cross-institution pressure and selective protection, and understanding how policy, financing, news clusters and market structure interact without requiring private-room evidence before forming a useful hypothesis.

## 0. Executive ruling

The research question is not whether policymakers publicly admit to a hidden objective. Repeated actions, tolerated costs, selective relief, bargaining pressure, timing and beneficiary structure are themselves evidence.

Mastermind should therefore stop treating policy analysis as a speech-classification problem. It should model:

1. **stated preference** — what an actor says it wants;
2. **revealed preference** — what repeated choices imply when objectives conflict;
3. **constraint / leverage** — which other actors can narrow the feasible choice set;
4. **mechanical transmission** — what those choices do to rates, FX, inflation, credit, earnings and capital allocation whether or not the effect was intended;
5. **selective protection** — which sectors or firms receive financing, demand, guarantees, price floors, procurement, regulatory access or coordinated public support;
6. **information orchestration** — whether discretionary announcements, partnerships, capital returns and policy events arrive in abnormal clusters around stress;
7. **alternative explanations and falsifiers** — what would make an apparently coordinated pattern better explained by common incentives, normal calendars or independent firm action.

The correct output is not a universal secret-intent score. It is a **behavioral policy case with explicit evidence, competing mechanisms, uncertainty, beneficiaries, falsifiers and market implications**.

This program must remain separate from live ranking/size/gate authority until a prospective experiment earns promotion.

---

## 1. Why this is not a new system

A census of current Macro shows that much of the conceptual architecture already exists.

### Existing canonical owners to reuse

| Capability | Existing owner / source | Current implication |
|---|---|---|
| Realpolitik policy context | `data/policy/intel.json`, `scripts/build_policy_watch.py` | Already contains narrative-vs-revealed framing and strategic-capital analysis. The substrate is stale and needs a current evidence process, not replacement. |
| Policy-intent LLM layer | `engine/policy_intent_desk.py` | Already reasons from interests / revealed preference and creates falsifiable hypotheses. It must remain context-only; prior audits found an authority leak into scored Hub paths. |
| Policy-shock conditions | `research/POLICY_SHOCK_REGIME_MASTERPLAN_BY_FABLE.md` | Existing law correctly forbids a live administration-timing oracle. It permits conditions, de-escalation and forward evidence accrual. |
| Rates / policy repricing | WS:RATES-INFLATION-COMMAND; RIC | Existing rate, curve, Fed-path, transmission and forward-log owners. No second rates model. |
| Company event / news impact | Draft PR #8533, News-to-Business-Impact | Owns article deduplication, event clustering, issuer economic impact, expectation delta and market incorporation semantics. |
| Technical ignition / T2 | Draft PR #8495 and existing Prophet evaluation | Owns T2 mechanics and the current T2 × evidence discovery. No duplicate T2 study plane. |
| Narrative persistence / burst | Narrative Ignition | Owns attention/burst/persistence semantics; news volume is attention, not automatically bullish content. |
| Circular financing / credit fragility | Corporate Credit Watch + existing research | Already contains vendor-financing, round-trip demand and AI-credit analog work. |
| Economic propagation | existing relationship / theme / GMI owners | Reuse economic relationships, narrative similarity and market co-movement as distinct graphs. |

### Current collision map

This research is deliberately path-isolated under `research/policy_behavior/`.

Do **not** edit the active branches owned by:
- PR #8495 — NVDA ignition / T2 evidence convergence;
- PR #8533 — News-to-Business-Impact masterplan;
- PR #7923 / #7940 — RIC policy-path repricing and prospective ledger.

Those programs are dependencies, not targets of this save.

---

## 2. Critical empirical discovery recovered from current Prophet work

The exact T2 + news result that motivated part of this research is already present in draft PR #8495.

The current finding is narrower and more useful than “bullish news helps”:

- H5 T2 + news-burst rows: **10/11 positive versus SPY (90.9%)**;
- absolute-positive: **8/11**;
- first observation per issuer: **6/7 positive versus SPY**, **4/7 absolute**;
- H10 weakens materially and is sensitive to INTC;
- NVDA's own news-burst was **neutral sentiment**: six recent items, zero positive and zero negative;
- therefore news-burst is best interpreted as **information arrival / attention**, not bullish sentiment;
- the stronger post-hoc construction is **fresh T2 acceptance × at least two independent evidence legs**:
  - repeated rows: **10/12 H5 positive versus SPY**;
  - first T2 per ticker: **5/5 positive versus SPY and sector**, **4/5 absolute**;
  - same-date T2 controls were worse on all seven observed dates, with an average mean-excess gap of roughly **+4.19 percentage points**;
  - T1 + multi-leg and generic convergence did not reproduce the result.

This remains tiny, post-selected and **zero authority**. It is nonetheless exactly the sort of interaction the new policy/news research should preserve prospectively.

The important conceptual implication is:

> Technical acceptance and information arrival may be multiplicative rather than additive. A stock that has already entered a valid acceptance state can respond very differently to a credible rerating catalyst than a technically similar stock without a meaningful evidence delta.

The forward study must therefore test **event quality × technical state**, not just count headlines.

---

## 3. Behavioral thesis map

### H1 — Revealed high-rate preference / tolerated restrictive regime

**Working hypothesis:** repeated policy choices may reveal that maintaining restrictive nominal / real financing conditions is acceptable or strategically useful, even when public rhetoric advertises lower rates.

Potential strategic benefits to test:
- attracts or retains global capital in USD assets;
- creates scarcity value for firms capable of producing exceptional forward earnings growth;
- weakens refinancing-dependent competitors and foreign systems with less fiscal / financial flexibility;
- preserves inflation-fighting credibility while industrial policy selectively subsidizes strategic capacity;
- allows future easing to be politically and financially more powerful after credibility has been banked;
- supports national-security reshoring through targeted channels rather than economy-wide cheap money.

**Key distinction:** “high rates are tolerated because other goals dominate” and “high rates are themselves an instrument” are different hypotheses. Mastermind should compare them from observed decisions rather than declare either impossible because no official statement says so.

### H2 — U.S. leverage over Japanese monetary / FX policy

The behavioral sequence materially exceeds ordinary parallel policymaking:

- Treasury pressure for faster BOJ tightening;
- New York Fed yen rate checks;
- direct U.S.–Japan FX cooperation;
- subsequent Treasury pressure on instrument choice;
- BOJ tightening;
- discussion of FIMA liquidity capacity that can reduce disorderly Treasury liquidation while currency / monetary adjustment occurs.

The correct research label is **constraint / bargaining-power inference**.

Do not encode “U.S. takeover of BOJ” as a fact. Test whether the practical Japanese choice set became narrower after U.S. intervention and whether market expectations changed when U.S. pressure was unexpected.

### H3 — Selective protection in a restrictive financing regime

Government can keep aggregate financing expensive while changing the economics of selected projects through:
- procurement;
- price floors;
- guarantees;
- offtake contracts;
- equity investment;
- tax incentives;
- regulatory fast paths;
- strategic import / export controls;
- allied investment commitments;
- liquidity backstops.

This creates a two-speed cost-of-capital regime.

For equities, the relevant variable is not the policy rate alone. It is:
**effective financing burden + demand reliability + financing access + expected earnings revision + competitive attrition**.

### H4 — Strategic announcement orchestration / rolling support

The hypothesis is not merely that companies release good news.

The testable claim is that **discretionary economically material positive announcements become unusually likely in strategically connected firms after predefined market or own-stock stress, and may arrive in cross-firm sequences that are difficult to explain by normal calendars alone**.

Candidate event species:
- buyback authorization / acceleration;
- strategic partnership;
- hyperscaler / model-company commitment;
- government contract / subsidy / price floor / offtake;
- White House / Treasury / Commerce / Defense agreement;
- capex commitment;
- financing package;
- warrant / equity-linked commercial agreement;
- national-security / reshoring agreement.

A White House dinner is not itself proof of a scheduled support operation. It is evidence of a coordination channel. The stronger evidence comes from **contacts + abnormal timing + economic linkage + repeated pattern + market response**.

### H5 — Circular AI financing as rerating support and fragility

Map the cash and obligation graph explicitly:

`capital provider -> AI customer -> vendor spending -> vendor earnings / cash -> investment or guarantee -> customer`

Add government / strategic support edges where relevant.

For every loop, distinguish:
- external cash entering the network;
- internal financing;
- purchase commitments;
- vendor investment;
- warrants / equity incentives;
- guarantees / backstops;
- recognized revenue;
- delivered capacity;
- utilization;
- independent end-customer cash.

The core question is not “is circularity fake?” It is:

> How much of current demand and valuation depends on continued financing from participants who benefit from that demand, and how much converts into independent external cash generation?

### H6 — Geopolitical / inflation shock as policy lever, tolerated consequence or exogenous shock

Iran / energy events may:
- genuinely change inflation;
- provide political attribution;
- alter the path of rate expectations;
- support defense / energy / strategic-industry capital allocation.

These channels can all be true simultaneously.

Mastermind should maintain competing hypotheses:
1. exogenous shock;
2. strategically tolerated shock;
3. opportunistically exploited shock;
4. deliberately induced outcome.

The evidence threshold rises across those four claims. Market transmission can be modeled before private motive is resolved.

### H7 — Election-cycle optionality

Do not hard-code a calendar rule such as “tighten before X, ease before Y.”

Instead model a reaction function:
- which deterioration is tolerated;
- which deterioration forces a pivot;
- which objectives are protected first;
- what credibility has to be accumulated before easing;
- which communication commitments have been removed or preserved.

This turns “midterm cycle” from folklore into a set of testable conditional decisions.

---

## 4. The key analytical object: rhetoric–action divergence

The new research should add a **research-only divergence record** to the casebook, not a production scoring object.

For every material policy episode capture:

- actor;
- institution;
- timestamp / first-public clock;
- public statement;
- statement type:
  - preference,
  - forecast,
  - conditional commitment,
  - negotiating threat,
  - justification,
  - blame attribution,
  - operational instruction;
- observed action;
- known constraints;
- feasible alternatives;
- expected mechanical effects at the decision time;
- actual later effects, separately;
- beneficiaries;
- losers / burden bearers;
- selective relief / protection;
- whether the action was reversible;
- persistence after adverse effects became visible;
- competing motive hypotheses;
- evidence for and against each hypothesis;
- what observation would materially re-rank the hypotheses.

A speech and an action can disagree without the speech being a lie. For prediction, the important question is which object has historically described the actor's **reaction function** better.

---

## 5. Forward experiment A — literal rhetoric vs inversion vs actions-and-constraints

This is the foundational policy experiment.

### Models

**M0 — Literal rhetoric**
Use the contemporaneous public message at face value.

**M1 — Automatic inversion**
Assume the opposite of rhetoric.

**M2 — Actions + constraints + revealed preference**
Use only information available at the decision cut:
- actual actions;
- repeated choices;
- constraints;
- policy instruments;
- selective protection;
- market pricing;
- prior behavior;
- explicit alternatives.

### Targets

Do not collapse all policy outcomes into one target. Evaluate separately:
- next 1 / 3 / 6 month policy-rate direction;
- 2y / 10y yield direction and magnitude bucket;
- real-yield / breakeven decomposition;
- DXY / JPY;
- inflation impulse;
- sector-relative outcomes;
- strategic-industry earnings / revision breadth;
- breadth concentration / leadership concentration.

### Evaluation

Use chronological, point-in-time cases with:
- frozen information cuts;
- no later-news leakage;
- Brier / log scoring for probabilistic categorical calls;
- calibration;
- decision accuracy;
- coverage / abstention;
- source independence;
- leave-one-regime-out checks.

The program wins if M2 reliably improves on M0 and M1. It does **not** need to prove a single hidden master plan.

---

## 6. Forward experiment B — U.S.–Japan constraint casebook

Build a dated event sequence beginning before the 2025 public pressure cycle and extending through the 2026 intervention / BOJ decisions.

For each event:
- Japanese domestic inflation / wage backdrop;
- pre-event OIS / JGB / USDJPY expectations;
- U.S. Treasury / White House / NY Fed action;
- Japanese official action;
- public and privately reported pressure;
- alternative instruments available;
- FIMA / liquidity-backstop status;
- immediate market repricing;
- subsequent BOJ choice;
- whether the choice was already fully priced.

Primary question:

> Did unexpected U.S. involvement materially change the probability, timing or instrument mix of Japanese policy beyond the domestic-information baseline?

This can produce a useful constraint inference without claiming documentary proof of command-and-control.

---

## 7. Forward experiment C — strategic announcement orchestration

### Population

Start with:
- MAG7;
- leading semiconductors;
- AI infrastructure / networking / power;
- major AI model companies where public events map into listed counterparties;
- defense / critical minerals as non-tech strategic controls.

Include matched non-strategic large-cap controls.

### Event catalog

Use the existing News-to-Business-Impact event clustering from PR #8533, not raw article counts.

Label:
- event species;
- discretion level;
- materiality;
- government linkage;
- financing linkage;
- counterparties;
- first-public timestamp;
- source independence;
- whether it was pre-scheduled;
- issuer price state;
- Nasdaq / sector / breadth state.

### Stress windows, frozen ex ante

Examples:
- Nasdaq drawdown from 20d / 60d high;
- breadth deterioration;
- semis relative-strength drawdown;
- VIX / rates shock;
- issuer drawdown;
- index near prior support;
- high-rate / high-real-yield state.

### Tests

1. **Announcement hazard:** does the probability of discretionary positive events rise after stress?
2. **Cross-firm sequencing:** are related firms' announcements spaced / clustered unusually versus calendar nulls?
3. **Connected-network effect:** is the pattern stronger among firms with White House / government / strategic-program links?
4. **Market effect:** issuer residual response, index contribution, breadth, revisions, options repricing, 1d / 5d / 21d persistence.
5. **Counterfactual:** matched issuers, matched stress dates, normal earnings / conference / product calendars.
6. **Negative cases:** stress windows where no supportive announcement arrives.

This is the correct way to investigate “take a place in line” rolling support without selecting only memorable episodes.

---

## 8. Forward experiment D — T2 × information arrival × economic rerating

Do not promote the 90.9% discovery.

Use PR #8495's frozen work as the historical discovery seed and PR #8533's event semantics as the news-quality layer.

Prospective cells should separate:

- T2 alone;
- T2 + raw attention burst;
- T2 + one verified material event;
- T2 + at least two independent evidence legs;
- T2 + government-linked event;
- T2 + financing-linked event;
- T2 + genuine expectation / earnings revision;
- T2 + repeated coverage of one root event.

Primary endpoints:
- H5 / H10 / H21 absolute and SPY-relative return;
- sector-relative return;
- MFE / MAE;
- clean-liftoff rate;
- persistence after H5;
- failure / reversal frequency.

Critical law:
**article count never substitutes for independent economic evidence.**

---

## 9. Forward experiment E — AI circular-financing dependency graph

Reuse CCW, Company Intelligence and the relationship graph.

Build research-only cases that include:
- investor;
- customer;
- vendor;
- lender / SPV;
- government actor;
- amount;
- obligation;
- equity / warrant rights;
- purchase commitment;
- revenue recognition;
- capex;
- delivered capacity;
- utilization;
- external customer revenue.

Derive descriptive quantities only:
- fraction of disclosed demand linked to counterparties that also finance the buyer;
- external-cash ingress;
- dependence on new financing;
- receivable growth;
- customer-concentration changes;
- credit-spread / CDS / funding-cost changes;
- contract cancellation / minimum-purchase terms;
- network single-point failures.

Do not call this “fake revenue.” The purpose is to identify **financing-dependent demand** and its failure modes.

---

## 10. Product integration target

### Policy Watch

This should become the primary human surface for:
- rhetoric vs action;
- revealed-preference cases;
- actor reaction functions;
- policy leverage / external constraint;
- strategic beneficiaries;
- alternative hypotheses;
- falsifiers;
- staleness and evidence clocks.

### Rates & Inflation Command

Consume only properly owned rate / curve / inflation / repricing observations. It should show whether actual market transmission agrees with the policy case. It should not become a hidden-intent scorer.

### Intelligence Hub

Context only. The prior policy-lean authority leak must stay repaired / prohibited. A model-authored policy inference must not directly boost a ranked opportunity.

### Prophet / Entry

Consume **independently validated event facts / evidence legs**, not policy-intent prose. T2 × event-quality interactions remain research until prospective promotion.

### Company Dossier / Terminal

Show:
- government / policy relationship;
- financing loop;
- contract / commitment;
- event progression;
- expectation change;
- independent cash conversion;
- source provenance;
- technical-state interaction.

---

## 11. Data / source program

The immediate weakness is not absence of theory. It is the stale / manually curated policy substrate.

A lawful v2 substrate should prioritize mechanical, time-stamped source intake:

- White House statements / fact sheets / event records;
- Federal Register;
- Treasury releases / refunding / TIC / FX reports;
- Federal Reserve statements, speeches, minutes, balance-sheet actions;
- BOJ / Japan MOF;
- Congress / statutory actions;
- SEC / issuer filings;
- DoD / Commerce / DOE / USASpending for strategic support;
- independent wire reporting for privately reported pressure;
- institutional research as secondary interpretation, never the only fact source.

Keep `data/policy/intel.json` as editorial / synthesis context until its owner intentionally migrates it. Do not create a rival canonical policy database from this research branch.

---

## 12. Work program

### W0 — Owner / law / collision freeze — **DONE in this research pass**

Recovered:
- Policy Watch is the existing qualitative owner;
- RIC owns rates / policy repricing;
- News-to-Business-Impact owns event materiality / clustering;
- Prophet #8495 owns the T2 interaction seed;
- CCW owns circular-financing / credit fragility;
- Policy-Shock law forbids a live administration-timing oracle;
- existing qualitative audits prohibit LLM-originated policy direction from entering a scored path.

### W1 — Point-in-time policy behavior casebook

Build 40–60 episodes across:
- rates / Fed;
- Treasury funding;
- U.S.–Japan;
- tariffs / industrial policy;
- Iran / energy;
- AI / tech;
- defense / minerals.

Include positive, negative and ambiguous examples. Preserve cases where rhetoric and action agree.

### W2 — U.S.–Japan constraint study

Freeze the event panel, domestic-control variables and policy-expectation outcomes. Establish what portion of the inference can be supported prospectively.

### W3 — Strategic-announcement study

Build a complete issuer-event panel and prespecified stress windows. Test hazard and cross-firm clustering before making any central-orchestration claim.

### W4 — T2 × event-quality prospective registration

Reuse #8495 / #8533. Freeze exact event labels and control populations. Start forward accrual.

### W5 — Circular-financing dependency casebook

Integrate CCW and company-event facts. Measure external cash conversion and financing dependence.

### W6 — Rhetoric/action baseline race

Run M0 literal vs M1 inversion vs M2 actions/constraints. If M2 does not beat simpler baselines, do not promote a more elaborate policy model.

### W7 — Display integration

Only after source clocks and research objects are stable:
- Policy Watch behavioral panel;
- Rates & Inflation cross-check;
- Terminal / dossier relationship display.

No rank / gate / size authority is granted here.

---

## 13. Promotion and kill criteria

A behavior hypothesis may become a production context feature only if:
- its input is point-in-time;
- its source independence is known;
- it has explicit competing hypotheses;
- historical selection is not outcome-driven;
- prospective evidence accrues;
- it improves a declared baseline;
- confidence is calibrated;
- failures remain in the sample;
- source staleness / absence is typed, never silently zero.

A policy inference must **not** be promoted merely because it is compelling.

Kill or hold a construction when:
- the simple action-based baseline performs equally well;
- event timing is explained by known corporate calendars;
- results vanish after issuer / sector / regime controls;
- a “coordination” measure is just multiple reports of one source event;
- T2 interaction collapses out of sample;
- high-rate benefits disappear after accounting for starting valuation / credit exposure;
- circular-financing warnings do not precede any measurable funding or demand deterioration.

---

## 14. Current capability delta

This research pass changes the frontier in three ways:

1. **The user's thesis already has a natural home.** Policy Watch was explicitly designed around narrative-vs-revealed divergence; the problem is freshness, evidence architecture and discipline, not absence of a policy-intelligence concept.
2. **The T2 + news observation is no longer anecdotal.** The current Prophet research branch records the exact 90.9% H5 relative-return discovery, its limitations, and the stronger fresh-T2 × independent-evidence interaction.
3. **The next build should be a research casebook / experiment layer, not another scored signal.** Existing law already blocks a timing oracle and an LLM-originated policy score, while allowing the exact behavioral evidence work needed here.

## 15. Exact next action

The next critical-path operation is **W1: construct the point-in-time policy-behavior casebook and freeze the three baseline models (literal rhetoric, automatic inversion, actions + constraints)**.

Do that before touching live Policy Watch scoring or `data/policy/intel.json`.

W1 is complete when:
- at least 40 episodes are frozen;
- every episode has a decision-time source clock;
- actions and rhetoric are separately encoded;
- alternatives / constraints and beneficiaries are captured;
- competing motive hypotheses and falsifiers are explicit;
- a deterministic verifier prevents outcome leakage;
- the dataset can support the M0/M1/M2 baseline race.

---

## References / current internal dependencies

- `data/policy/intel.json`
- `engine/policy_intent_desk.py`
- `scripts/build_policy_watch.py`
- `research/POLICY_SHOCK_REGIME_MASTERPLAN_BY_FABLE.md`
- `research/RATES_INFLATION_COMMAND_RECOVERY_AND_COMPLETION_FREEZE_2026-08-27.md`
- `agentos/workstreams/WS-RATES-INFLATION-COMMAND.md`
- `research/CCW_CREDIT_FIELD_GUIDE.md`
- Draft PR #8495 — Prophet NVDA / T2 emergence and ignition research
- Draft PR #8533 — News-to-Business-Impact research packet
- Draft PR #7923 / #7940 — RIC policy-path repricing / prospective ledger

## Authority / safety boundary

This document is a research and program-design artifact. It creates no trade, sizing, ranking, gate, policy-timing, runtime, or deployment authority. It does not supersede existing RIC, Prophet, Policy Watch, Company Intelligence, CCW, event, graph, Agent OS or Executive OS owners.
