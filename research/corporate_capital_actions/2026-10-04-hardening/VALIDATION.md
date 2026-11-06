# Commission 13 — proposed validation and acceptance specification

**Status: research specification, not executed production tests or measured alpha.** This document accompanies [MASTERPLAN.md](MASTERPLAN.md). Synthetic arithmetic checks can verify the internal consistency of the recommendation; they do not validate an implemented ledger, a live source, a vendor feed or a forecasting model.

The later implementation/evaluation owner must accept this docket and map it to current house law before running data or outcome experiments. Existing W2/W4/share-substrate gates, protected outcomes and incumbent experiment ownership remain controlling. [R01, R02, R07](SOURCES.md)

## 1. Separate the claims being tested

| Layer | Claim | Ground truth / comparator | A pass does not imply |
|---|---|---|---|
| D — Data | We extracted the correct event, class, unit, amount and clock | Independent source adjudication with exact retained evidence | Forecast accuracy or live coverage |
| R — Replay/reconciliation | We reconstruct the permitted version and avoid duplicate effects | Time/version fixtures, share/cash/claim invariants, later direct observations | Economic benefit or alpha |
| A — Accounting usefulness | The new facts improve denominator/capital explanations | Existing consumer inputs plus direct future reported observations | Predictive authority |
| F — Forecast | Conditional share/capital predictions beat simple baselines | Future class-compatible observations, frozen prior information | Causal interpretation or tradability |
| M — Market information | Evidence adds out-of-sample information after existing controls | Admitted historical/prospective outcome study | Permission to rank, size or trade |
| P — Publication | An accepted generation reaches intended consumers safely | Native clean-runner/natural/served receipts and rollback | Any of the untested scientific claims above |

No gate can be passed with another gate's evidence. A green parser test is not a source-quality study; a schema is not a served product; a better EPS denominator is not proof of expected stock returns.

## 2. Cohort and gold-set design

### 2.1 Diagnostic pilot

Proposed first corpus: **240 economic-event clusters**, with 60 in each P0 stratum:

| Stratum | Required inclusions |
|---|---|
| Share basis / transformations | Splits, reverse splits, already-adjusted comparative facts, class ambiguity, fractional treatment and events near observation boundaries |
| Repurchases / ASRs | Board capacity without execution, ordinary execution, non-program purchases, initial/final ASR delivery, aggregate-versus-component overlap and unpaid cash settlement |
| ATM programs / actual sales | Active and expired capacity, actual sales, shared shelf limits, amendments, unknown price/quantity and no-sales negatives |
| Primary / secondary offerings | Mixed selling-holder deals, primary-only, secondary-only, fees, overallotment options, pricing versus close and canceled deals |

Sample from source/form coverage and historical issuer membership, not from known price winners or conveniently well-parsed filings. Include small/liquidity-constrained issuers and failed/acquired/delisted securities. Keep simple single-common-class cases as the first automated scope and explicitly count complex-class exclusions.

Use two independent adjudicators on the pilot, blind to the model output and market outcome, then a recorded reconciliation process. Two prompts to the same model on the same cached output are not independent adjudication. Preserve disagreement and irreducible ambiguity. Never force an uncertain number into the gold set to make evaluation easier.

Each gold record includes evidence spans, raw unit/rounding, class/basis, event/program links, time precision, disclosure scope, economic movement legs, correction lineage and expected eligibility by replay mode. Source documents belonging to one transaction form a cluster; multiple values from one source are not independent examples.

### 2.2 Pilot cost envelope

Planning assumption, not observed productivity: two five-minute reviews per event imply 40 reviewer-hours for 240 events. Reserve eight hours for adjudication: **48 expert-hours**. Time the first 40 events. If actual burden extrapolates beyond the accepted budget, narrow family/automation scope or request a revised budget; do not lower truth standards or hide unpaid review work. Complex term cases may require much longer than this assumption.

No paid sample or vendor subscription is authorized. Existing lawful source bytes come first. Retention of any new content must follow source rights and the incumbent source owner.

### 2.3 Promotion sample and uncertainty

The pilot finds defects; it does not certify 99.5% reliability. For zero observed critical errors in n independent accepted event-level observations, a one-sided 95% exact binomial lower bound for correctness is:

`p_lower = 0.05^(1/n)`.

At n=60 this is about **95.13%**, at n=240 about **98.76%**, and at n=600 about **99.50%**. Counting 600 correlated fields from 20 transactions as 600 independent trials is invalid.

Proposed high-integrity publication target: a one-sided 95% lower bound of at least 99.5% on material-event correctness **for the scope being promoted**, plus zero unresolved structural/PIT invariant failures. This may require at least 600 effectively independent, zero-error accepted events; real dependence, errors and family-specific requirements can demand more. The owner must accept cost and sample feasibility before adopting this as a production gate. Otherwise remain shadow/context-only and report the weaker achieved evidence honestly.

Report both accepted-set precision and total attempted coverage, all abstentions/exclusions, issuer/family composition, cluster dependence and errors weighted by materiality. An abstaining system cannot claim full coverage. A proposed pilot usability target is at least 80% complete accepted P0 events within its declared simple scope, **not** a reason to admit ambiguous events to meet a quota.

Do not inspect results until the declared batch closes and then extend only because the confidence interval looks inconvenient. Predeclare any staged sampling and error-correction/retest protocol; use a fresh held-out set after tuning. Keep diagnostic, calibration and confirmatory datasets separate.

## 3. Failure definitions and proposed quality gates

### 3.1 Critical failures

Any wrong security/class or unit, unsupported historical availability, future correction leakage, duplicated material economic movement, wrong primary/secondary classification, treasury retirement double count, unauthorized rights use, or source-fabricated numeric term is critical. Critical errors block promotion of the affected scope until corrected and re-evaluated.

A rounding difference within source-declared precision is not necessarily an extraction error. Preserve rounding intervals and decimal representations; do not invent a percentage tolerance that can excuse a large absolute economic error. Missing or conflicting terms should be deferred, not rounded into agreement.

### 3.2 Required measurements

| Dimension | Required reporting |
|---|---|
| Discovery | Precision and recall by family/form against an independently defined eligible source set |
| Extraction | Exact identity/class/unit/date match; amount error within declared source precision; stage/term classification |
| Deduplication | Duplicate economic effect rate and false-merge rate; component versus aggregate disclosure errors |
| Program linkage | Correct authorization/sales/execution/settlement association, including ambiguous aggregate programs |
| Share basis | Wrong-anchor rate, class ambiguity, basis mismatch, double-adjustment rate, unsupported currentness |
| Reconciliation | Signed and absolute residual versus next eligible direct observation, with explained/unknown components |
| PIT | Ineligible-future-record count, retroactive parser-correction count, exact query replay |
| Coverage | Attempted/admitted/deferred/unknown counts, reasons, issuer/family distribution and evidence age |
| Operations | Source-to-retention-to-canonical-to-consumer latency; queue age; review minutes; cost per usable issuer-period |
| Reproducibility | Same versioned input/query/policy produces the same normalized artifact hash |

Operational targets must be set against the existing source owner's actual schedule/capacity law. This research does not change the incumbent 500/20/20 envelope or define a new collector merely to meet a speculative latency target. A fast stale dataset is not healthy coverage.

## 4. Synthetic economic oracles

**All quantities below are deliberately hypothetical. Unless stated otherwise, share and dollar quantities are in millions; prices are dollars per share. These are exact arithmetic examples, not issuer data, recommendations or implemented test results.** The implementation owner should turn each into a named fixture with expected state, error/defer outcomes and source-generation receipts.

### V01 — Treasury acquisition is not treasury retirement

Start issued=120, treasury=20, outstanding=100. Acquire 8 into treasury: issued=120, treasury=28, outstanding=92. Retire those same 8: issued=112, treasury=20, outstanding remains 92. Reissue 3 treasury shares: outstanding=95. Issue 5 new shares: outstanding=100.

Reject a bridge ending at 84 after the retirement. Check `outstanding = issued − treasury` after every leg, not only at the endpoint.

### V02 — ASR initial and final shares

Start outstanding=100. Pay 200 cash under a stylized ASR and receive 8 initial shares. Final disclosure says **10 total** shares, including the initial 8. Final additional delivery is 2, so outstanding ends at 90, not 82. The final share true-up does not repeat the initial 200 cash payment.

A variation in which “10” is explicitly additional must yield a different result. Ambiguous “final shares” without scope must defer rather than choose the convenient interpretation. Real filings motivate the distinction but do not supply this synthetic arithmetic. [I01, I02](SOURCES.md)

### V03 — Mixed primary and selling-holder secondary offering

Starting O/S=100. Deal sells 4 newly issued shares and 6 selling-holder shares at 20. Issuer gross proceeds=80, fees=4, net cash=76; final O/S=104. A continuing holder of 10 shares owns approximately 9.61538%, not 9.09091% as a ten-share issuer-dilution assumption would imply.

The 200 headline deal value is not all issuer financing. A pure secondary variation changes neither issuer O/S nor issuer cash unless separately evidenced issuer fees or another actual leg applies.

### V04 — Employee grants, vesting and withholding

An award grant of 1 does not itself add 1 outstanding common share. Later 0.6 vests, with 0.2 withheld under the stated net-delivery assumptions. Net common delivery=0.4. An accounting expense of 5 dollars does not subtract 5 shares or prove 5 dollars of stock issued.

Represent either net +0.4, or gross +0.6 and return −0.2 with linked legs, but never both representations. Do not also add the same employee exercise in a separate option bucket. Registration/plan capacity remains a distinct state.

### V05 — Split once and preserve comparative basis

A 2-for-1 split transforms a pre-split 50-share observation into 100 on the post-split comparison basis. A later 110-share observation implies 10 of net movement on that basis, absent other changes. If a later comparative column already reports the old period as 100, do not multiply it to 200 again.

A negative test omits basis metadata: the selector must return ambiguity/unavailable for the comparison rather than infer a split from the ratio alone.

### V06 — Endpoint shares are not weighted-average shares

100 shares for 30 days, then 90 for 60 days, over a 90-day period gives weighted-average basic shares=93.333333. With baseline common income=120, denominator-only EPS=1.285714, versus 1.20 at 100 shares.

Now assume explicitly that lost positive interest income is 6 and incremental financing interest expense is 4 for this same modeled period. Common income becomes 110; EPS=1.178571, not 1.285714 and not an income increase from adding “lost interest.” These are supplied scenario amounts, not annual yields applied to an unspecified period.

If event dates are known only within a month, do not produce this exact period denominator without an explicit timing assumption. Common cash dividends are distributions, not an automatic deduction from net income; preferred effects depend on the numerator's existing definition.

### V07 — Convertible settlement branches

For principal F=100, conversion price K=10, and settlement price P=20, assume conversion is legally permitted and occurs. A full-share contractual branch delivers 10 common shares. A cash-principal/net-share branch delivers 5 common shares and requires 100 cash for principal. These branches are mutually exclusive.

A cash-only convertible cannot be turned into common shares merely because F/K is calculable. Payment amount and accounting EPS treatment need actual contract/policy inputs. Do not infer conversion probability or a universal GAAP denominator from this example. [I03](SOURCES.md#I03)

### V08 — Shared registration/ATM constraints

A shelf has gross-dollar capacity 100 and an ATM subprogram limit 60. An actual ATM sale of 20 leaves shelf capacity 80 and ATM capacity 40 under the stated simplified constraints. They are not additive 120 capacity. A future ATM sale of 40 plus another shelf issuance of 50 violates the shared remaining shelf limit, although each appears individually possible under an incomplete check.

Unknown legal constraints make legally executable capacity unavailable, not equal to the smallest number conveniently present. Fees do not automatically consume gross registration capacity in the same way as issuer proceeds; use the source-defined convention.

### V09 — Debt refinancing

Begin face debt=100. Draw/issue 80, repay 60 principal, and pay 2 fees. End face debt=120 and net financing cash change=+18, not +80. Common shares are unchanged absent a separate equity leg. Carrying value remains distinct from face principal and may be unavailable without accounting data.

A repayment cash flow already included in an aggregate financing statement must not be subtracted twice when event legs are combined with statement totals.

### V10 — Anchor containment and overlapping disclosures

An anchor on May 1 reports O/S=92 and already contains 8 acquired on April 30. A further 3 shares issued on May 2 produces 95. Applying April's 8-share repurchase again produces the wrong 87.

Separately, monthly repurchases 3+2+1 and an enclosing quarter total 6 describe 6, not 12. Without a reliable scope relationship, preserve competing observations rather than adding all rows.

### V11 — Economic time versus knowledge time

An event effective March 1 is first canonically known April 15 with quantity 10. A source amendment first known June 1 changes the quantity to 12. An actual-system query as of May 1 returns the original 10; a June 2 query can return the corrected 12. A latest-restated view may show 12 for March, but it is not a valid May 1 feature.

A parser correction first produced August 1 likewise cannot appear in an April actual-system result merely because the old source document was then public. Re-observation of unchanged bytes must not create a new economic occurrence.

### V12 — Spin and merger entitlements

A pro-rata spin gives 0.25 child share per parent share. A holder with 10 parent shares receives 2.5 child shares before any specified fractional treatment; parent O/S does not automatically change. Return evaluation must carry the parent/child/cash basket and not double-count a distribution already embedded in an adjusted return series.

A separate stylized merger exchanges each target share for 0.5 acquirer share plus 2 cash. With 20 target shares acquired, a new-issue settlement adds 10 acquirer shares and pays 40 cash. A holder of 2 target shares receives 1 acquirer share and 4 cash. Distinguish new issuance from treasury-share consideration and do not assume the agreement has closed before evidence supports it.

### V13 — Dividends and preferred claims

An ordinary common cash dividend changes cash/payable state when appropriate, not common share count merely on declaration. Declaration, ex, record and payable clocks remain distinct. Do not treat the cash distribution both as an EPS expense and as a separate subtraction from an already dividend-adjusted total return.

For a separate simplified equity-classified preferred issue: 10 preferred shares at 25 raises gross cash 250; fees of 1 leave net cash 249. A stated liquidation preference of 250 is not 10 additional common shares. A stated annual preferred dividend of 20 reduces income available to common only under the appropriate accounting/numerator assumptions; do not deduct it again from a baseline already net of preferred dividends.

### V14 — Business recovery is not purchase recovery

Assume 60 original common shares were purchased at 5, new issuance adds 60 shares at 2 with fees 6, all 114 net proceeds are spent, ending debt is 180 and ending cash is zero. At operating enterprise value 600, common value is 420 and 120 shares imply 3.50 per share. The original cohort is worth 210 versus its 300 purchase cost: −30%. Recovering the original 5-per-share purchase requires operating EV=780 under these assumptions.

This tests claims/cash/denominator consistency only. It supplies neither fair value nor a probability of recovery. If old securities are legally canceled with no entitlement, a valuable successor does not restore the old holder's claim. Reuse the incumbent recovery owner. [R09](SOURCES.md#R09)

### V15 — Future financing cannot erase an earlier cash-floor breach

Starting available cash=20. A dated outflow of 40 precedes a future financing inflow of 114. The path breaches the zero cash floor by 20 before funding arrives. A positive ending balance does not make the earlier path feasible. Report the breach or an explicit additional bridging-finance assumption; do not silently move funding earlier.

### V16 — Missing versus confirmed zero

A missing or unparsed repurchase disclosure returns unavailable/unknown. A source that explicitly establishes zero in the covered scope can return zero. An empty extraction result is not source evidence of zero. Shadow comparison must identify this difference from the existing shareholder-yield convention. [R07](SOURCES.md#R07)

### V17 — Material corrections and retractions

Retracting an erroneous event after June 1 may remove it from a June 2 current view, but must not alter a May 1 actual-system snapshot. A canceled offering changes prospective state without reversing shares that were never issued. A source amendment and a parser correction retain separate cause/version metadata. Concurrent or contradictory updates must obey existing owner ordering rather than inventing a new global sequencer.

### V18 — Authority and source-injection rejection

A retained filing passage containing instructions to ignore timestamps, buy shares or change a ranking is treated as source text, not an instruction. Any derived artifact attempting to set new rank/sizing/entry/veto/Prophet/trading authority true fails validation. An ambiguous issuer, unlicensed identifier use or unknown class cannot be rescued by an LLM confidence score.

## 5. Adversarial replay suite

Before publication, the later implementation must test:

- Late source amendment; late parser correction; silent changed source bytes at the same URL; retraction; unchanged re-observation; conflicting sources and out-of-order arrival.
- Missing/date-only/timezone-shifted availability; event interval crossing the anchor; an aggregate fact with a later filing date but older economic date; a newer current API response containing historical revised values.
- Split/reverse split around the cutoff; a later restated comparative; multiple common classes; ADR ratio changes; reused ticker; delisting, merger, spin and old-equity cancellation.
- Duplicated 8-K, exhibit, press release, period table, cash-flow total and normalized vendor record for one transaction; distinct transactions accidentally merged because they share a filing/program.
- Gross versus net proceeds, fees, debt face versus carrying amount, restricted cash, treasury reissue, zero versus missing, malformed decimal/scale and contradictory numeric terms.
- Identical pinned query and source generations yielding unequal output hashes; attempted mutation of immutable prior versions; unauthorized changes to existing publication/retention boundaries.

These are test requirements, not statements that the current code fails every case. Preserve existing conformance tests rather than replace them with a small new happy-path suite.

## 6. Forecast and market experiment registration

### 6.1 Forecast target and baselines

Register issuer/security population, share class/basis, source/replay mode, forecast origin, target economic observation date, horizon policy, label-publication handling and exclusion rules before fitting. Evaluate direct observed shares rather than treating an analyst/model estimate as ground truth.

Compare against: last compatible reported O/S; last O/S plus known deterministic actions; trailing net-issuance trend; and the admissible existing share-trend consumer. Report error/abstention jointly. Proposed promotion criterion: positive paired out-of-sample improvement over the best relevant simple baseline with confidence bounds excluding no improvement at the accepted confidence level, plus no material unaddressed degradation in key issuer/mechanism strata. The exact minimum economic improvement must be accepted before outcome inspection; do not choose it afterward.

Probabilistic forecasts require nominal coverage, interval width/sharpness and calibration by regime/family. Low/base/high scenario labels without probabilities receive no coverage-calibration claim. A model predicting endpoint shares must not be scored as having solved period EPS denominators.

### 6.2 Market test budget

Seven possible mechanism families: repurchases; primary/ATM supply; employee equity; warrants/convertibles; debt/funding; M&A/spin/tender; dividend/preferred. Two primary horizons: 21 and 63 trading sessions. Seven times two is 14 family comparisons; two joint-model comparisons make **16 maximum confirmatory comparisons** for the accepted experiment version.

Only two P0 families may initially qualify, so four family comparisons plus two joint comparisons make **6 active**, with **10 reserved**. Reserved tests cannot run merely because compute is available. New transformations, signs, thresholds, models, family definitions, horizons or selectively chosen subgroups consume additional research degrees of freedom and require the owner's multiplicity/budget policy.

Use hierarchical/family-aware multiplicity control under the accepted evaluation protocol. Keep exploratory outputs explicitly exploratory. Do not recycle an already inspected holdout as a new untouched test set; do not create a replacement experiment identity to reset a failed result.

### 6.3 Leakage and sampling protections

Freeze training, tuning and confirmatory periods by time; group by issuer/event and protect overlapping horizons with the approved purging/embargo policy. Use historical membership including exits and old-security entitlement policy. Label future corporate outcomes separately from features so eventual corrections used to score outcomes cannot enter prior inputs.

Controls must themselves be PIT-qualified. If analyst-revision, options or ownership history is unavailable, report that limitation and population shift rather than use current backfills. Include the existing payout/capital-allocation and price/fundamental baselines to measure incremental rather than duplicated evidence.

LLM extraction receives source-bounded passages and does not get future outcome labels. Models may have memorized historical public events; numeric acceptance therefore requires source support and deterministic checks, and prospective evidence is still needed for an actual-system claim. A fluent explanation of an old winner is not an independent forecast.

Separate returns between first public disclosure and Mastermind availability from returns after actionable receipt. An event study around economic event_time is not a usable-arrival backtest when the observation became known later. Test realistic information and execution delays; include liquidity/cost sensitivity only where the relevant data and trading simulation are separately admitted.

### 6.4 Falsifiers

Forecast promotion fails if complexity cannot beat appropriate persistence/mechanical-action baselines, confidence is uncalibrated or errors concentrate in the economically important tail. Market-information promotion fails if advantage disappears after version/timing corrections, existing-feature controls, failure-inclusive identity, costs or untouched out-of-sample evaluation. Do not turn a failed return result into an undocumented opposite-sign feature.

Keep a reliable non-predictive ledger for accounting/risk use when that utility is demonstrated. Kill its alpha claim, not necessarily the entire data family.

## 7. Operational publication and rollback

Before a later publication/cutover, require the current source owner's proof that admitted observations are retained and reproducible, the correct canonical generation is published, the intended consumer actually reads it, stale/deferred states surface truthfully, and authority flags remain bounded. Recorded historical natural proofs should be linked exactly and not restaged through a forbidden manual workflow dispatch.

Rollback disables the new consumer path or returns it to an approved prior generation while retaining immutable evidence and correction history. A deletion of inconvenient events is not rollback. Any source-rights removal follows a separately approved rights policy with preserved permissible audit metadata, not ad hoc history rewriting.

The final implementation return must distinguish `PROVEN_LIVE`, `BUILT_NOT_PROVEN`, `PARTIAL`, `SPEC_ONLY`, unavailable and held capabilities. This research packet itself establishes none of those implementation upgrades.
