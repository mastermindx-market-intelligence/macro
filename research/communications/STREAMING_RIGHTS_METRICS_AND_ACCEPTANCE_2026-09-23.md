# Communications Phase 3 — Metric Definitions and Acceptance Requirements

**Operation:** `gmi-communications-research-20260923-sol-001`. **Carrier:** Macro PR #7794.
**Status:** Proposed research definitions and future acceptance requirements, not an accepted schema or executed product test suite.

Read with `STREAMING_CONTENT_RIGHTS_RESEARCH_2026-09-23.md`. Source IDs below resolve only to that chapter's public primary-source register. Existing semantic, evidence, identity, rights, time/correction, evaluation and rendering owners remain authoritative. These tables are design inputs for the later Fable package, not a second store or permission system.

## 1. Twenty-four proposed metric contracts

Every proposed measure needs issuer/business scope, source locator, valid reporting period, publication/knowledge time, observation time, revision, units, accounting basis, denominator, comparability and authority. Source publicity does not establish retention or display rights. Definitions below specify what must be checked; they do not assert that every company discloses the measure or that Mastermind already ingests it.

| ID | Measure | Required definition / key trap |
|---|---|---|
| SRM01 | Paid relationships | Accounts, households, seats, profiles and entitlements are distinct; ending stock is not a flow. |
| SRM02 | Paid relationship-months | Average exposure over the billing period; match trials, time active and geography. |
| SRM03 | Realized price | Net subscription receipts per matched paid exposure, not list price applied to every user. |
| SRM04 | Adds and reactivations | Separate first-time paid, trial conversion, returning and bundled access; do not count trial conversion twice. |
| SRM05 | Cancellation and survival | Channel event clock, denominator, cohort date and treatment of resubscription; interrupted survival cannot regain rejoiners. |
| SRM06 | Bundle economics | Incremental household/cash basis, prior-service mix and allocation/elimination policy. |
| SRM07 | Advertising-tier contribution | Subscription plus retained ad receipts less incremental cost and migration effects; ad budget is not net retained revenue. |
| SRM08 | Content/rights milestone | Announced, committed, available, consumed, paid and financially material are separate dated claims. |
| SRM09 | Engagement | Hours, source-defined views, unique viewers and ranks are different; include measurement window and coverage. |
| SRM10 | Content cash payments | Additions and liability movement with source signs; retain units and avoid double-subtracting from CFO. |
| SRM11 | Content amortization | Expense period, estimate basis and changes; not a cash payment or measured title ROI. |
| SRM12 | Content commitments | Contract scope, remaining obligation, due windows and conditions; do not add an entire commitment to this quarter's cash expense. |
| SRM13 | FCF | Issuer formula and original/revised vintage; distinguish PP&E, restricted cash, leases, advances and strategic investment. |
| SRM14 | Segment-to-issuer profit | Inclusion/exclusion, corporate cost and eliminations; a subsegment is already inside its parent. |
| SRM15 | Sports-season economics | Full rights and recognition windows; season/calendar mismatches, incremental ads and subsequent retention. |
| SRM16 | Marginal content value | Counterfactual acquisition/retention contribution net of shared-cost duplication; unknown without suitable causal evidence. |
| SRM17 | Royalty pool | Matched platform, territory, period, tier and eligible consumption; no universal fixed per-stream rate. |
| SRM18 | Rights participation | Recording versus composition, ownership versus distribution/admin, duration and economic share. |
| SRM19 | Advances/recoupment | Opening balance, cash additions, recoupment, write-downs and closing scope; spending is not equivalent to expense. |
| SRM20 | Catalog capital | Acquisition and renewal economics, net book value versus modeled value, financing claims and remaining rights. |
| SRM21 | Comparable perimeter | Acquisition/disposal/renaming/reclassification and FX bridges; name similarity is not metric equivalence. |
| SRM22 | Equity-linked operating expense | Award/price linkage, published sensitivity, expense versus cash and endogenous stock-price effects. |
| SRM23 | Expectations | Guidance or consensus, original or restated vintage, range/floor, metric basis, fixed horizon and publication cutoff. |
| SRM24 | Per-share claim | Security/depositary basis, dilution, parent/minority interests, debt/lease claims and source-bound currency. |

## 2. Twenty-two worked primary-input calculations

Inputs are transcribed from the chapter's selected sources. Calculation agreement validates arithmetic, not extraction completeness, causality, full normalization or production behavior. Six decimals below are computational display precision only; the underlying source precision controls interpretation. The JSON attachment is a portable export of these research examples, not live data.

| ID | Calculation | Result | Unit / source | Interpretation |
|---|---|---:|---|---|
| P3-01 | `4927523-(-181794)` | 5109317.000000 | USD thousands [N2] | Implied content cash; do not subtract again from CFO |
| P3-02 | `5109317/4311309` | 1.185096 | times [N2] | Quarter cash/amortization; not an ROI or next-quarter forecast |
| P3-03 | `1743812-218644` | 1525168.000000 | USD thousands [N2] | Quarter CFO less PP&E, not annual recurring cash |
| P3-04 | `712-329` | 383.000000 | USD millions [D1] | SVOD operating-income increase within Entertainment |
| P3-05 | `(712/329-1)*100` | 116.413374 | percent [D1] | Same disclosed SVOD scope; not all streaming services |
| P3-06 | `658-179+501` | 980.000000 | USD millions [D1] | Total segment profit change; do not add SVOD again |
| P3-07 | `(858/1037-1)*100` | -17.261331 | percent [D2] | Sports reported OI change; cost timing included |
| P3-08 | `(3050/2762-1)*100` | 10.427227 | percent [D2] | Sports programming/production cost change, not cash commitment |
| P3-09 | `189-(-101)` | 290.000000 | USD millions [C1] | Peacock quarter EBITDA delta, not annual profit |
| P3-10 | `(656/521-1)*100` | 25.911708 | percent [S1] | Symmetric social-charge sensitivity, not normalized growth |
| P3-11 | `655-630` | 25.000000 | EUR millions [S1] | Versus guidance as restated in current report |
| P3-12 | `9/25*100` | 36.000000 | percent [S1] | Share of guide exceedance associated with lower social charges |
| P3-13 | `25-9` | 16.000000 | EUR millions [S1] | Residual exceedance, not wholly attributed to organic operations |
| P3-14 | `816-21+2` | 797.000000 | EUR millions [S1] | Company FCF formula, including restricted-cash change |
| P3-15 | `901+251-292-452-237` | 171.000000 | EUR millions [U2] | H1 CFO including advance cash; not a quarterly subtotal |
| P3-16 | `171+92-61-44+21-53-93-9` | 24.000000 | EUR millions [U2] | Restated-definition H1 FCF, before strategic investments |
| P3-17 | `3017+3376` | 6393.000000 | EUR millions [U2] | Net catalog plus advance carrying value, not market value |
| P3-18 | `142-28` | 114.000000 | USD millions [W1] | Warner quarter FCF, not matched to UMG H1 by label alone |
| P3-19 | `491-407` | 84.000000 | RMB millions [T1] | Growth less acquired contribution, not certified organic growth |
| P3-20 | `-0.2-2.5` | -2.700000 | million paid net adds [H1] | Netflix 2022 original-guide shortfall as reported at event |
| P3-21 | `-0.2-(-0.7)` | 0.500000 | million paid net adds [H1] | Market-exit adjustment still below original guide |
| P3-22 | `174.3-147.8` | 26.500000 | million subscription actions [M2] | Calendar 2024 panel net additions, not current unique households |

## 3. Twelve synthetic illustrations

All quantities in this section are invented teaching scenarios, not fitted company estimates. Ten are checked arithmetic illustrations; two are clock-order checks. They do not execute a Mastermind producer, schema or UI.

| ID | Scenario / expression | Result | Interpretation |
|---|---|---:|---|
| I01 | `(1.1*0.96-1)*100` | 5.600000 | Price +10%, retained quantity 96%: revenue change only |
| I02 | `100/1.1` | 90.909091 | Revenue-neutral retained quantity percent after 10% repricing |
| I03 | `(96*(11-4)/(100*(10-4))-1)*100` | 12.000000 | Contribution under invented constant unit cost 4, not an issuer estimate |
| I04 | `(17/20-1)*100` | -15.000000 | Already-dual customers rebundled at 17 versus 20 lose revenue before offsets |
| I05 | `100*0.9*0.9` | 81.000000 | Uninterrupted cohort survivors; 20 rejoiners are a separate 20 |
| I06 | `(1.05*(0.18/0.20)-1)*100` | -5.500000 | Royalty pool +5% and share 20% to 18% reduce receipt 5.5% |
| I07 | `80*15+20*(8+5)` | 1460.000000 | Ad-tier migration with no new members: synthetic revenue before costs |
| I08 | `80*15+20*(8+5)+10*(8+5)` | 1590.000000 | Same ad-tier case plus ten new members; adoption and migration differ |
| I09 | `30-5` | 25.000000 | CFO 30 already contains rights cash; deduct only additional PP&E 5 |
| I10 | `100-60` | 40.000000 | Increment above variable payment to meet a 100 minimum, not 100+60 |
| I11 | Calendar ordering | PASS | August publication of June results may describe June; it is not knowable in June |
| I12 | Calendar ordering | PASS | A September-effective development milestone cannot itself be assigned to June revenue |

These examples expose different questions. A price increase with a modest quantity decline can improve current contribution under an assumed fixed unit cost; it does not establish later retention. An ad tier can dilute existing customers yet create net revenue through genuinely new ones. A bigger royalty pool can still produce lower receipts for a participant losing share. A minimum guarantee modeled as a floor must not be added in full to the variable payment it guarantees. Actual contracts can be more complex and require separate disclosure.

## 4. Thirty proposed adversarial acceptance cases

**All SRC cases below are written requirements. None is an executed application PASS.** Each must be mapped to existing owners and to a concrete real-path test in the final accepted implementation plan. Positive examples, contrary evidence and unavailable states are all required.

| ID | Challenge | Required future behavior |
|---|---|---|
| SRC01 | Content cash already appears in CFO | Do not subtract it again when computing CFO less PP&E; explain the separate diagnostic bridge. |
| SRC02 | Negative content-liability cash-flow line | Use the source sign correctly; preserve units and reconcile to the statement. |
| SRC03 | USD-thousands table mixed with EUR-millions | Refuse unconverted arithmetic; expose units/currency rather than silently rescale. |
| SRC04 | H1 cash compared with a peer quarter | Label period mismatch; require matched duration before a comparative conclusion. |
| SRC05 | Subscriber stock, adds, profiles and entitlements mixed | Preserve populations; do not turn entitlement counts into unique paying households. |
| SRC06 | Ending subscribers used as all-quarter exposure | Require the correct average/relationship-month denominator or mark the estimate approximate. |
| SRC07 | Cancellation action and access expiry clocks differ | Preserve the source event convention; do not assert a matched-day churn jump. |
| SRC08 | A cancelled customer rejoins | Count reactivation separately; never rewrite uninterrupted cohort survival. |
| SRC09 | Dual-service subscribers receive a cheaper bundle | Compare incremental household contribution, not summed service subscriber gains. |
| SRC10 | A title has large viewing hours | Show engagement; withhold title ROI and causal subscriber attribution absent suitable evidence. |
| SRC11 | Engagement publication changes to annual | Apply source-specific schedule; lack of a half-year release is not zero usage or proof of collector failure. |
| SRC12 | An event creates peak subscriber additions | Keep milestone distinct from retention and full-season cash acceptance. |
| SRC13 | Rights costs move between reporting quarters | Show the season/contract and recognition bridge; avoid a permanent cost conclusion from one quarter. |
| SRC14 | SVOD definition excludes live-TV services | Keep exclusions visible and consistent through peer comparison and historical charts. |
| SRC15 | SVOD improvement already included in Entertainment | Do not add it again when calculating group segment-profit change. |
| SRC16 | Peacock has one positive EBITDA quarter | State the measured quarter and basis; do not claim annual net-income or cash profitability. |
| SRC17 | Global streams multiplied by a fixed royalty rate | Require matched pool and participation evidence; reject an unsupported payout estimate. |
| SRC18 | Distribution deal described as ownership | Preserve relationship type, territory, term and source; do not promote it to perpetual catalog ownership. |
| SRC19 | Artist/label split is undisclosed | Show unknown materiality, not 100% label ownership or an invented payout percentage. |
| SRC20 | Advance cash and royalty expense coexist | Reconcile cash versus recoupment/expense; prevent duplicate deductions. |
| SRC21 | Catalog book value offered as market valuation | Retain carrying-value label; any valuation is a separately labeled, assumption-bound model. |
| SRC22 | Licensed AI platform announced as in development | Keep agreed scope, availability, adoption and revenue distinct; no fabricated Q2 revenue contribution. |
| SRC23 | Company can license music; research site sees announcement | Do not infer rights for Mastermind to ingest or publicly expose full underlying content. |
| SRC24 | Acquired audio revenue and changed membership wording | Preserve acquisition date and metric-definition history; no silent old-to-new series join. |
| SRC25 | Corporate separation announced but not completed | Retain transaction stage and current perimeter; do not prematurely reassign securities or segment histories. |
| SRC26 | Share-price move changes operating social charges | Identify endogenous expense; do not label it purely operational cost improvement or an ex-ante price predictor. |
| SRC27 | Current report restates old guidance | Label the observed vintage; do not present an independently verified pre-release consensus or original archive. |
| SRC28 | Cohort/rights/expectation data unavailable | Useful sourced operating explanation remains available; missing values never become zero or a confident score. |
| SRC29 | Later retention/current surviving membership in backtest | Enforce actual knowledge cutoff and PIT eligibility; no retrospective predictive success claim. |
| SRC30 | Evidence works but user cannot finish the journey | Fail acceptance: require real input to theme explanation to company/watchlist, plus existing dark/light, EN/ZH, desktop/mobile proof. |

## 5. Proof and handoff boundary

The chapter has seventeen primary references. The local validation command is `python /mnt/data/communications_research/validate_phase3.py`: independent Decimal/Fraction calculations, declared expected rounding, source-reference resolution and document structure. The portable validation receipt records the scope and the exploratory heading-count check defect; correcting that check changed no research statement or source value.

Full repository Agent OS validation, CI qualification, product tests, source-owner schema acceptance, historical-return analysis and browser proof have not run. Do not convert local arithmetic PASS into any of those states. No temporary worker, new scheduler or Fable execution has started.

For final implementation, map these definitions to current GMI evidence/curation, identity and time/correction owners, source rights/display controls, ThemeState, F04 composition and evaluation. Source custody and native privacy/publication gates remain prerequisites. Reuse the shared template rather than authoring a parallel rights or content system. Fable's future packet must provide concrete inputs, permitted paths, expected negative states and real-path proof, not merely these abstract requirements.
