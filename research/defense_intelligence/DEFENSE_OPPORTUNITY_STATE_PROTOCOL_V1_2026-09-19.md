# Defense Intelligence — Opportunity State Protocol V1

Date: 2026-09-19. Owner: Sol. Parent: `WS:DEFENSE-PROCUREMENT-V3`.
Carrier: existing Defense Intelligence research PR #7175.
Procedure pin: Mastermind `733389933e605e508517732fb6c69b6c18b7fef6`, Skillpack 1.0.1/bootstrap 1.
Macro observation pin used for the current negative control: `423e49d59f7b2c8a4ab0afe029a34cb308818d9e`.

This is an architecture/research contract for a composed **display-tier research state**. It is not a new source-of-truth plane, a Prophet ranker, an execution signal, a reviewed D5 admission, or a current investment recommendation. Existing Group Reads, program ontology, Government Revenue, Company/Earnings Intelligence, market data, Event Intelligence and Prophet owners remain authoritative.

## 1. User job and machine job

The investor job is not “show me more defense contracts.” It is:

1. determine whether Defense is receiving broad market participation or only isolated bids;
2. identify the mission/product theme that explains the participation;
3. identify which listed businesses have reviewed exposure to that theme;
4. translate the changed demand into plausible shareholder economics;
5. distinguish under-recognized economics from already-priced enthusiasm or execution risk;
6. expose the next observable condition and invalidation before any entry feature is considered.

The machine job is to compose those independent owners without collapsing them into one confidence number.

## 2. Four independent axes

### A. Market participation

Read the existing Group Reads `defense` owner. Preserve its own dates, denominators and semantics:

- basket coverage and membership version;
- unusual-activity share/count;
- 50d/200d trend shares with their readable denominators;
- directional state and active denominator;
- SPY-relative basket performance;
- active participation episode;
- observed activity leader.

An activity leader is not an alpha leader. A current generation clock is not a newer market observation. Defense Intelligence must never silently reconstruct these measures or substitute an ETF move for the owner packet.

### B. Theme / mission demand

Consume Event Intelligence, Government Revenue/FMS/budget and the reviewed program ontology. Keep separate:

- scenario / reported geopolitical event / confirmed event;
- requirement or consumption pressure;
- policy proposal / enacted authority / appropriated amount / obligated amount;
- framework / development / qualification / production / delivery / sustainment;
- prime award / supplier agreement / actual government obligation;
- source publication time / Mastermind first-seen time / analysis time.

A war headline, oil shock, FMS notification, capacity framework or contract ceiling is not automatically a positive earnings event.

### C. Issuer economics

For every candidate issuer, show what is known and what is not:

- reviewed legal-entity/program role and stage;
- attributable revenue or cash basis only where sourced;
- contract type and pricing exposure where known;
- production capacity and alternative-source risk;
- margin basis and accounting basis;
- capital expenditure, working capital and customer advances;
- common-shareholder claims and dilution/subsidiary interests;
- company guidance and reported financial facts with period/unit/basis.

Do not use a program association as a revenue share. Do not add prime and supplier contract values as independent end demand.

### D. Recognition / expectations

Separate observed market recognition from fundamental economics:

- company and theme relative price response from the existing market owner;
- valuation scenarios from the existing reported-fundamentals F07 owner;
- explicit scenario assumptions and current price when available;
- management guidance changes and licensed expectations only when rights-cleared.

Without a licensed consensus source, “not priced in” is not an observed field. A price-equivalent earnings hurdle under an explicit multiple is an algebraic scenario, not “what the market expects.”

## 3. Descriptive state machine — no composite score

A dossier may carry one state from each axis plus a composed plain-language research state. V1 composed states are intentionally qualitative and mutually intelligible:

- `SECTOR_BID_ABSENT` — broad Defense participation is not confirmed.
- `SECTOR_BID_PRESENT_THEME_UNRESOLVED` — participation exists, but causal theme evidence is unresolved.
- `THEME_CONFIRMED_ECONOMICS_UNRESOLVED` — reviewed demand/theme evidence exists; issuer economics are not yet supportable.
- `ECONOMICS_IMPROVING_RECOGNITION_LOW` — sourced scenario improves versus reported base while observed recognition remains limited; this is a research hypothesis requiring validation, not a buy instruction.
- `ECONOMICS_IMPROVING_RECOGNITION_HIGH` — economics improve, but substantial observed recognition/extension is already present.
- `PRICE_STRENGTH_WITHOUT_ECONOMIC_CONFIRMATION` — price/theme participation leads the fundamental evidence.
- `ECONOMICS_WEAKENING_OR_EXECUTION_RISK` — cost, schedule, funding, margin or shareholder-capture evidence offsets demand.
- `EVIDENCE_INSUFFICIENT` — a required owner is stale, unavailable, contradictory or unreviewed.

Never average these axes into a 0–100 “Defense conviction” score. No state may rank, size, gate, originate, add or escalate a Prophet plan in V1.

## 4. Research-entry readiness is a checklist, not authority

The product may show a **research readiness** panel only when each item is individually visible:

- participation context is current, or a documented narrow-theme exception is explicit;
- mission/theme evidence is source-bound and time-valid;
- issuer role is reviewed at the correct legal-entity/product stage;
- a financial transmission scenario exists with explicit unknowns;
- the contrary economics case is shown;
- observed market recognition is shown separately;
- next catalyst/window and invalidation are explicit;
- data freshness and first-availability clocks are visible.

Missing items remain missing. “Ready for research” does not mean “enter now.” Entry authority remains with existing validated timing/Prophet owners after separate qualification.

## 5. Current negative-control observation

At Macro `423e49d59f7b2c8a4ab0afe029a34cb308818d9e`:

- Group Reads defense pulse is observed through 2026-09-18 with 21/21 covered;
- unusual activity: 0/21;
- 50-session trend share: 0.0952 (21 readable);
- 200-session trend share: 0.0 (21 readable);
- participation episode: inactive / quiet;
- arc: `washout_complete_awaiting_reclaim`.

The companion basket measurement observed through 2026-09-17 reports 20-session basket return about -11.38% and SPY-relative return about -10.54%. The four core names were all negative over 20 sessions; over five sessions LMT/NOC/LHX were modestly positive while RTX remained negative.

Correct V1 interpretation: **broad sector-bid confirmation is absent**. This does not prove every Defense long thesis is wrong and does not rank the quartet. It demonstrates why the product must support “no broad confirmation / theme-specific research only” instead of manufacturing a leader whenever procurement headlines are positive.

## 5A. Exploratory sector-persistence and leader qualification

This section tests whether the Chairman's preferred ordering — sector strength first, then alpha leader — has enough observed structure to deserve product treatment. It is exploratory qualification only, not a promoted signal.

Evidence snapshot was read from current production artifacts after #7186 merged to main at `dfcab9236060b22578ed5714ff18debd90647c28`:

- `site/basketdata/pulse.json` blob `2ea459c4f4b8985cabded8ddf5ed05226db9ae2a`;
- `site/basketdata/baskets.json` blob `48da64016f5779d2c35164713893cb8a8638df37`;
- `site/basketdata/episodes.json` blob `9fcaa4cedeb9e2ad59ca97172092bfcc08ad8f4e`;
- first-cohort tapes: LMT `b5d9bb554213c0a1d1726e58b85bfc744cfd736a`, RTX `44d560bcb37faad8de2898d632c3f416342ba0c1`, NOC `06c8b63cdbbf8ca20fd9246548677cb43ddaff4b`, LHX `4c7d75948421858781b41277dca68d278ef98bc4`.

### Current market state

The September 18 Group Reads packet remains a negative control rather than a sector-bid confirmation: 0/21 unusual-activity members, 2/21 above the 50-session trend line, 0/21 above the 200-session trend line, no active episode, and a mixed direction state.

The equal-weight Defense basket showed approximately +1.14% over five sessions but -11.38% over twenty sessions and -6.73% over sixty sessions. Its SPY-relative returns were approximately +0.51%, -10.54%, and -10.68% over those same horizons. LMT was the strongest of the initial LMT/RTX/NOC/LHX cohort on the observed 5d, 20d-loss containment, and YTD comparisons, but that is **relative leadership inside a weak sector**, not the Chairman's desired sector-strength + theme + leader configuration.

### Participation-episode study

The retained Group Reads history contains only ten Defense participation episodes from September 2025 through July 2026. From episode **start**:

- 5-session Defense return: mean +0.11%, median -1.43%, positive 4/10;
- 5-session SPY-relative return: mean +0.36%, median -0.93%, positive 4/10;
- 20-session Defense return: mean +0.97%, median +1.90%, positive 7/10;
- 20-session SPY-relative return: mean +0.54%, median -0.28%, positive 5/10.

Across all ordinary dates in the same observed window, the 20-session SPY-relative mean was about -1.00% and median about -2.33%. That makes participation worthy of continued research, but ten clustered episodes do not establish an edge.

A stricter descriptive subset requiring at least two active sessions contained only six episodes. Their 20-session SPY-relative mean was about +2.83%, median +2.71%, with 4/6 positive. The 5-session relative mean was about +1.24%, median approximately flat, with 3/6 positive. This suggests **persistence may matter more at a multi-week horizon than at immediate entry**, but the sample is far too small and event-clustered for promotion.

### Alpha-leader study

Using only information through each episode-start close, the top prior-5-session performer among LMT/RTX/NOC/LHX became the subsequent 20-session winner 4/10 times overall and 3/6 times in the persistent subset. The top prior-20-session performer did so 5/10 overall and 3/6 in the persistent subset.

The prior-20-session leader's subsequent 20-session return exceeded the four-stock cohort mean by about +2.46 percentage points on average across all ten episodes and +2.21 points across the six persistent episodes. Those means are concentrated: individual episodes include both a strong positive continuation and a large negative miss. No robustness, independence, survivorship, transaction-cost, or multiplicity claim is made.

### V1 ruling from the study

Do **not** make broad-sector participation or recent relative strength a hard gate, automatic ranker, or trade trigger.

Instead:

- persistent sector participation is a **candidate confluence feature** for the 20-session research horizon;
- current sector weakness can truthfully produce `SECTOR_BID_ABSENT` while permitting narrow-theme research;
- recent company leadership is a separate observed-recognition leg, not proof of economic asymmetry;
- the stronger thesis is the interaction of persistent participation + reviewed theme exposure + improving issuer economics + limited recognition;
- promotion requires a larger point-in-time episode panel, versioned historical membership, clustered-event validation, costs, and prospective frozen observations.

This evidence therefore strengthens the architecture while reducing its authority: the sector-first idea is useful enough to measure, but not yet reliable enough to decide entries by itself.

## 5B. Existing subtheme owner, breadth probe and rights boundary

Defense Intelligence must not mint a second theme taxonomy. The Dynamic Theme Graph already contains seven canonical local Defense subthemes:

- Aviation — next-generation aircraft and maintenance;
- CyberDefense — cyber defense and electronic warfare;
- Drones — drones and anti-drone systems;
- Manufacturing — secure defense supply chains;
- Missiles — missile defense and long-range weapons;
- SpaceTech — space technology and satellite services;
- Weapons — precision weapons and ammunition resupply.

The observed graph already links LMT, RTX, NOC and LHX into the Missiles local theme. Those edges are **theme-membership context**, not D5-reviewed program-role assertions, economic-share estimates, or permission to say each company has equal missile sensitivity.

### Current public-emission boundary

These local themes are sourced from the existing `finviz_themes` family. Current owner law in `config/theme_sources.yml` classifies that family as `rights_class: unresolved`. `engine/theme_graph/rights.py` therefore permits internal computation but refuses a new public GMI emission of the vendor-derived subtheme→member structure.

The public labels themselves are not the restricted object; owner law explicitly distinguishes a public theme name from republishing the membership structure. Existing pre-GMI heatmap/rotation surfaces are grandfathered owner products. A new Defense Intelligence surface is not grandfathered.

V1 ruling:

- internal Defense research may consume these Theme Graph memberships;
- Defense must not copy them into a new public basket, identity store, or curated membership file;
- a public Defense subtheme surface must either receive the existing Theme Graph owner's explicit derived-display rights resolution, or use independently reviewed house/primary-source program relationships through the existing D5 path;
- do not solve the rights gate by renaming copied vendor memberships as “Mastermind curated.”

### First quartet theme-breadth probe

Using only the existing committed LMT/RTX/NOC/LHX price tapes, an exploratory proxy treated the quartet as the initial missile cohort and counted how many had positive trailing-20-session returns at each broad Defense participation-episode start.

Across the ten retained Defense episodes:

- at least two of four positive beforehand: 7 episodes; subsequent 20-session quartet mean approximately +3.27%; four positive;
- at least three of four positive beforehand: 6 episodes; subsequent mean approximately +4.64%; four positive.

Restricting to the six episodes with at least two active sector-participation sessions:

- at least two of four positive beforehand: 5 episodes; subsequent mean approximately +4.25%; three positive;
- at least three of four positive beforehand: 4 episodes; subsequent mean approximately +6.55%; three positive.

This is not monotonic or robust enough for authority. One persistent episode with all four names already positive subsequently produced about -11.4% for the quartet, while another persistent episode with only one positive name subsequently produced about +11.1%. The sample is tiny and conflict/event-clustered.

The correct conclusion is that theme breadth may be a useful **interaction variable** with persistent sector participation, but neither breadth nor leadership should become a deterministic prerequisite. The validation target is whether the combined state adds incremental value over the sector-only and momentum-only baselines on a larger point-in-time panel.

## 6. Prime/supplier asymmetry rules

The PAC-3 and Standard Missile research cases establish a reusable law:

- demand growth;
- incumbent supplier exposure;
- alternative-source qualification;
- prime delivery improvement;
- supplier pricing/allocation;
- capital required to add capacity;
- actual output achieved

are different variables.

A bottleneck may initially increase supplier scarcity value while later second sourcing improves prime execution and changes the supplier's economics. Development/qualification exposure is not mature replenishment exposure. The same demand shock can therefore produce different economic paths for LMT, RTX, NOC, LHX or another supplier without contradiction.

## 7. Validation before any authority promotion

Pre-register the event family, theme membership version, issuer-role state, horizon and outcome before measuring edge. Required comparisons:

- market/sector-only baseline;
- price/relative-strength baseline;
- procurement-only;
- economics-only;
- event/context-only;
- combined Defense Intelligence state.

Use true first-availability timestamps, frozen historical predictions, executable price assumptions, costs, clustered conflict/event holdouts and prospective shadow observations. Report false positives, missed opportunities, drawdown, turnover and stability across regimes.

Financial forecast accuracy and stock-return predictability are separate outcomes. A correct procurement forecast does not prove an entry edge.

Only a family/horizon that demonstrates incremental value may request admission through the existing Prophet governance. Unqualified families remain useful display-tier research context.

## 8. First product slice

The first complete slice remains:

`Defense sector context → munitions/air-and-missile-defense theme → LMT / RTX / NOC / LHX → reviewed role/stage → typed economics → recognition/expectations → next condition + invalidation`.

Acceptance requires real owner inputs, stale/missing/contradictory states, correction handling, user-visible output and machine-consumer output. A document, schema, merged PR or green CI does not complete the slice.

## 9. Current implementation dependencies

1. #7186 is merged at `dfcab9236060b22578ed5714ff18debd90647c28`; its natural production publisher run `35431106133` must complete and the served signed-in generation must be proven before DI-R0 is accepted.
2. Release #7199 only after its acquisition→existing-publisher path is current-main compatible and naturally proven.
3. Correct financial basis/period semantics at the existing Company/Earnings owner; do not hard-code fixes in Government Revenue.
4. Human-admit the required munitions program/role mappings through existing D5 propose/curate law.
5. Build this composed read model/UI as a consumer of existing owners, not another scoring, identity, market-data or publication plane.