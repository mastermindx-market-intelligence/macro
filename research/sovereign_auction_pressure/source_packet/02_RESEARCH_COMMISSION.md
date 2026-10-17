# Sovereign Auction Pressure and Cross-Asset Risk
## Pro-mode research commission, preregistration and feasibility program (v1.0)

**Prepared:** 2026-10-08. **Status:** unbound research **proposal**, not a completed study or a pre-existing runtime assignment. Read with `01_MASTERPLAN_PROPOSAL.md`. 

## R0. Objective and standard of proof

Establish whether **upcoming government debt issuance, announcement surprises, auction intermediation and settlement funding pressure**, conditional on contemporaneously known financial fragility, contain *incremental* information about (i) government-bond yield volatility/concession, (ii) funding/liquidity stress, and crucially (iii) pre-auction risk-asset drawdowns or defensive windows. Reject any model that merely repeats baseline stress/regime information without causal timing and useful forecast lift.

Research must distinguish:

- `established market mechanism` from `tradable/prospective prediction`;
- `known before event` from `only released after event`;
- `unexpected issuance announcement` from `already-scheduled auction size`;
- `gross notional` from `DV01 supply` and `privately held net funding`;
- `bond-specific rate price pressure` from `SPY/QQQ selloff`;
- `settlement transfer` from `enduring banking-reserve contraction`;
- `forecast` from `deterministic importance/ranking` and `scenario`;
- `daily historical ETF proxy` from true intraday Treasury WI quote, order-book or high-frequency order flow.

A high-quality `NULL / NO-GO` answer is admissible and must not halt the underlying lifecycle/product build; this program should still generate the most complete and usable PIT auction intelligence layer using public lawful data. Research cannot write an automatic cash/exit policy.

## R1. Explicit alternative hypotheses and falsifiers

**H1 (supply announcement shock / repricing):** an ex-ante *unexpected* positive change in net Treasury borrowing or duration supply is associated with abnormal rates moves, rates volatility and selected risk-asset reactions, after controlling for simultaneous Fed/macroeconomic releases. **Alternative:** announced supply was fully expected or simultaneous inflation/policy news drove moves. Falsifier: no incremental outcome vs an event-time surprise baseline or narrow-announcement matched controls.

**H2 (pre-auction capacity interaction):** abnormal pre-auction Treasury concessions and rates-vol events are more prevalent when maturity-weighted burden is high **and** known dealer/market liquidity stress is high, even when raw size or MOVE/term premium alone are weak. **Alternative:** general volatility explains everything; growing non-dealer participation makes today's huge issuance easy to absorb. Falsifier: interaction has no incremental performance over burden-only and fragility-only baselines in chronologically held-out data.

**H3 (settlement plumbing):** privately held *net new cash* settlement cohorts correlate with short-horizon funding changes only when buffers (reserves/RRP), funding markets and government cash flows are constrained. **Alternative:** cash is sourced from RRP or offset by spending/redemptions; no durable reserve shortage. Falsifier: observed reserve/funding response is absent, wrong-signed, or already explained by contemporaneous TGA/Fed plumbing baselines.

**H4 (post-results information):** contemporaneously timestamped auction result surprises improve near-future **rates** volatility/direction classification after result publication, beyond price/term-premium baseline. **Alternative:** markets already repriced by results time; a weak auction often marks a yield peak (sign reversal); bid-cover/dealer share are not surprises. Falsifier: failed horizon/gate, false improvement caused by using unavailable WI quotes, release-time misalignment or corrected auction result values.

**H5 (one-day-ahead risk-asset hazard, user priority):** a model evaluated at T-1 close or earlier identifies auction-linked windows with *incrementally* elevated SPY/QQQ downside incidence or excess risk-asset volatility, beyond Macro's current market regime, MOVE, term premium and Risk Radar. **Alternative:** the auction is merely scheduled on a day of high macro/credit stress; market stress would occur anyway and safe-haven Treasury buying can *support* duration. Falsifier: within-regime placebo event dates, matched non-auction controls and event-shuffled exposures perform equally, or alert benefit is outweighed by false alerts and opportunity cost. This H5 is the decisive gate for any proposed `go defensive/cash beforehand` hypothesis.

**H6 (international conditional spillover, optional):** JGB/gilt/euro auction shocks transmit to US rates/USD/risk assets conditionally on global duration repricing and FX funding. Treat as distinct country studies, not automatic extension of a US rule. Falsifier: no high-quality PIT national auction schedules/rights or no incremental effect vs global rates regime.

One H1-positive finding cannot approve H5; H2 rate-vol success cannot approve equity cash positioning. Explicitly preserve all counterexamples and survivor/regime-selection risks.

## R2. Source universe and point-in-time feasibility audit

### Required U.S. primary sources

1. TreasuryDirect `TA_WS/securities/upcoming`, `/announced`, `/auctioned`, search/query by securities; official auction announcement/results notices and historical announcements. Verify API schemas, type vs securityType, CMB visibility, pagination, history cutoff, correction mutation, time zones, actual competitive deadline, issue/settlement dates and rate/discount-margin conventions.
2. FiscalData `Treasury Securities Auctions Data` including published `record_date`, official DTS and Treasury receipts/redemptions / Daily Treasury Statement / Treasury Monthly Statement / QRA financing estimates. **Do not assume record_date is contemporaneously reliable until historical sample proves it.**
3. Treasury Quarterly Refunding archives: borrowing estimates, previous issuance plans, tentative schedules, official press releases, auction-size expectations/revisions, TBAC material. Surprises require *historical expectations vintages*, not just subtracting last observed actual from this week's actual.
4. Treasury buyback official operations/amounts and Fed/SOMA purchase/redemption schedules and outcomes. Preserve gross versus privately held net borrowing; Treasury states SOMA rollovers are excluded from privately held net marketable borrowing, redemptions can contribute financing need, and replacement issuance can offset buybacks.
5. NY Fed Primary Dealer Statistics, Treasury repo/SOFR and available intermediation proxies, with true publication lags; OFR FSI, term premium, MOVE and market-return histories from existing Macro with rights/freshness and original vintage validation.
6. Actual pre-auction benchmark/WI Treasury/futures quote data (if available legally at reasonable/no incremental cost), e.g. existing licensed venues/authorized historical data. Research **must** list fields, frequency, start dates, licensing, per-request limits and whether a true auction stop-out minus *just-before-auction* WI yield can be computed. No data license = no true tail or direct order-flow estimate.

### Data feasibility matrix (must deliver)

For each input: source URL + ownership + cost/redistribution license + earliest and last available date + refresh cadence + publication/first-seen timestamp semantics + historical revision/vintage support + granularity + event identity/key + state of Macro collection + representative example + known gaps + fallback + proposed consumer.

Hard checks:

- **Each government marketable type**, not just coupons: Bills, CMBs, Notes, Bonds, TIPS, FRN; odd reopened terms, unusual issue/settlement days, canceled/changed events.
- Investor allocation: primary dealer/direct/indirect shares use *competitive accepted* denominator; indirect is **not foreign ownership**. Official investor-class tables have a separate publication clock and must not be used ex ante.
- CUSIP date: one CUSIP may appear at multiple reopening auctions; official source may use distinct original issue dates. Do not collapse one issue's lifecycle or double count on re-fetch.
- Auction bid time is not universally 13:00 ET (e.g., some FRNs and bill auction deadlines differ); source-specific cutoff.
- QRA *tentative schedule* vs official *announced terms* vs current `upcoming` current snapshot; historical known-at cannot be inferred solely from eventual auction date.
- Multiple auctions share same date, quarter-end or settlement cohort. Avoid duplicated event windows and false independent sample size.
- Fed/OFR/primary dealer data can be revised or published late. PIT lag must use real releases, not fill future data backwards.
- `^MOVE` and commercial Treasury quotes/futures may be accessible for private analytics but not freely redistributable; rights must be reviewed before production.
- Some already-scored historical auction results in `auctions.parquet` were fetched retrospectively and are **not proof** the timestamped announcement history was recorded when it happened.

Begin with a small official audit set: at least one Bill, CMB, FRN, nominal coupon, TIPS, reopening and unusually amended auction. Prove exact PIT chronology for one real October 2026 auction from announcement through results to settlement when those phases are publicly complete; supplement with older source archives. Do not wait for future market events to complete basic source/data-model work.

## R3. Literature review / mechanism reconstruction

Do a primary-source-based research synthesis across:

- high-frequency auction-day yield concession/reversal and direct order flow;
- dealer warehousing and constraints vs natural buyer/nondealer participation;
- unexpected Treasury borrowing/auction-size announcements as supply shocks and their cross-asset transmission;
- maturity-mix vs debt-volume shocks (different signatures);
- settlement-day reserve effects, Treasury General Account, RRP offset and buyback financing;
- cash balance forecasts, tax dates, QT/SOMA, repo specialness and scarce collateral;
- flight-to-quality vs bear steepening, growth versus inflation/fiscal risk regimes;
- cross-market correlations and response direction stability (equities, credit, FX, gold, BTC).

Minimum direct anchors to read, not just cite abstract:

- Fleming, Liu & Nguyen (2026, revised Jul), NY Fed Staff Report 1188: https://www.newyorkfed.org/research/staff_reports/sr1188
- Duffie et al. (2023), NY Fed Staff Report 1070: https://www.newyorkfed.org/research/staff_reports/sr1070
- Phillot (2025), *AEJ Macro*, 17(1): https://pubs.aeaweb.org/doi/10.1257/mac.20210243
- Bi, Phillot & Zubairy (2026), Kansas City Fed/NBER: https://www.kansascityfed.org/research/research-working-papers/treasury-supply-shocks-propagation-through-debt-expansion-and-maturity-adjustment/
- Fed order-flow imbalance/market-depth April 2025 stress analysis: https://www.federalreserve.gov/econres/notes/feds-notes/order-flow-imbalances-and-amplification-of-price-movements-evidence-from-u-s-treasury-markets-20251103.html
- Official bidder classification: https://www.treasurydirect.gov/help-center/faqs/auction-faqs/

Required adversarial conclusion: recent NY Fed work finds meaningful **intraday** auction concessions but **no broad recent increase in price pressure** despite rising issuance, partly because participation and intermediation shifted. It cannot be glossed over or converted into a universal multi-day SPY selloff thesis. Document study data-rights gaps, periods and whether results are actually replicable using *our* feed.

## R4. Event taxonomy, information sets and outcome windows

Each study row must declare information set `I(t)` and the first legal decision time. Use distinct episode identities for announcement, auction, result and settlement to prevent stage leakage. For every event, stamp issuer, type, tenor, reopening, offered and accepted face, yield/DV01 estimate with version, net privately raised cash when known, relevant contemporaneous fragility, official source vintage and price-source version.

**Decision snapshots:** QRA publication + first official announcement; T-5 close, T-3 close, T-1 close, T0 pre-bid one hour and five minutes *only if a lawful intraday feed exists*; immediately after actual results publication; T+1 close; settlement S-1/S/S+1/S+5. If snapshot not supported by data, record `NOT_TESTABLE`, do not substitute same-day closing known-after data.

**Horizon matrices:**

- Announcement: from before to shortly after verified official timestamp (intraday) and close-to-close t0/t+1 when intraday unavailable; control for release coincidences.
- Pre-auction: T-5/T-3/T-1 to auction deadline; exact start/end price and timezone.
- Result: minutes/hours after published results (if intraday quotes available), plus next 1/3/5 trading-day rates and cross-asset returns as separate low-frequency studies.
- Settlement: S-1 through S+1/S+5 funding/repo/reserve observables with their true reporting lags.
- Cross-asset: SPY/QQQ/IWM HYG/LQD/TLT/IEF and VIX/MOVE when historical granular timestamp and license permit, plus USD/gold/BTC; the exact session/24h definition must match each market's trading hours.

**Equity early-warning target (H5):** jointly report 1) realized downside/maximum drawdown over a prespecified T-1 -> T+1 window in units of ex-ante equity volatility; 2) unusually high realized volatility; 3) distribution of signed excess return vs matched controls. Do not interpret elevated absolute volatility as proof a `sell to cash` direction. Free daily-only data may support a weaker T-1 close to T/T+1 close target; no claims about morning/lunchtime timing unless intraday data exist. Pre-register chosen loss thresholds based on economic user utility without tuning on held-out outcome data.

**Nested/overlapping events:** cluster by settlement date, auction group, issuance week and macro-news collision windows. Model event episodes, not duplicated stock-by-stock observations. Apply temporal/block bootstrap and cluster dependence at a sensible event/issuance-week level. Test same-day CPI/FOMC/NFP/OPEX, month/quarter-end, tax dates, Fed operations, large earnings clusters, exogenous shocks and known risk-off runs as confounds.

## R5. Computed variables (with PIT, formulas and alternatives)

**Supply:** face offered in USD, ex-ante security-price approximation, modified duration, DV01 $mm/bp, net duration burden and tenor percentile; 3/5/10-day clustered supply; QRA amount change (before-vs-after official); debt-volume versus maturity-composition surprises; reopening vs original.

**Cash:** redemptions/maturities due, net-new-private financing, SOMA add-ons/rollovers and buybacks, Treasury cash-flow projections, TGA outstanding and forecast change, repo/funding strain, RRP available buffer and counterparty mix uncertainty.

**Capacity:** *lagged and observable* dealer position utilization if empirically supported, rates vol/MOVE, OFR funding and safe-asset FSI, Treasury term premium, repo SOFR spreads, trading depth (if lawful), prior auction competitive share, prior tenor demand z-score, observed current credit stress, liquidity-quality state.

**Regime:** Macro's current regime and risk radar **as of decision time**; no label revisions/lookahead. Cross-asset factors and curve responses conditioned on fiscal/inflation/risk-off regimes. Test whether multiplier/interaction effect is monotonic or has thresholds. Pre-committed alternative: no multiplier; a simple regime-only baseline may win.

**Raw data model:** missing reason and confidence for every quantitative field; ex-ante `previous_auction_bid_to_cover` is allowed, today's yet-to-occur bid-to-cover is not. Historical QRA surprise cannot be computed from revised latest plan in lieu of announced vintage.

For every feature provide units, normalization population, source, source-known-at timestamp, field-level PIT rule, computation code path, availability coverage and a hand-checked worked example. All transformations deterministic; statistical fitting can estimate interactions, not invent missing observations.

## R6. Pre-registered evaluation design

### Benchmarks and incremental tests (mandatory)

Evaluate at least:

- B0: unconditional event-history/base-rate or simple same-tenor size percentile;
- B1: risk regime/MOVE/term-premium/credit/liquidity quality using only **known-before** features, no auction information;
- B2: B1 + schedule proximity alone;
- B3: B1 + raw notional + tenor controls;
- B4: B1 + DV01/net financing/supply surprise independently;
- B5: B4 + a prespecified burden x fragility interaction;
- B6: B5 + settlement funding-specific channel (for correctly dated targets only).

Force B5/B6 to prove *incremental* value above the existing Macro finance/risk baseline. Do not train and evaluate using current revision labels that had not been published at the decision date.

### Model forms and falsification

Start with transparent logistic/ridge or survival/hazard analysis, regularization and one economically interpretable interaction; use monotonic/isotonic calibration only in designated training/calibration folds. Nonlinear changepoint/threshold and gradient boosted challengers can remain shadow experiments if simple models fail. Never present statistically convenient post-hoc weight selection as deterministic law.

- No post-auction dealer share or result in pre-auction feature set.
- No backward fill of weekly NY Fed PD data to the observation date.
- No market close quote observed **after** the announcement as a pre-announcement control.
- Purge/watermark overlapping windows; cluster by auction/week and chronological cohort; event type/tenor segmentation requires adequate effective sample size.
- Freeze discovery, validation, untouched holdout and **prospective** start date. Include stress eras (e.g. 2008, 2020, 2022, 2023, 2025-2026) only where actual PIT sources support them; do not claim precise vintages in eras with only later records.
- Use paired in-regime placebo dates, week-matched non-auction dates, shuffled auction dates **within permissible seasonality/calendar strata**, and matched duration/term-premium stress periods.
- Controls for scheduled macro releases, Fed meetings, earnings season and rate-vol state. Withholding controls is only allowed as an explicitly separately reported sensitivity test.
- Test alert burden per year, precision and conditional lift over the regime base rate; evaluation includes adverse windows, missed stress, false alert cost and opportunity cost of de-risking.

### Metrics / decision gates

For binary stress outcomes: proper scoring rules (Brier/log loss), calibration curves/ECE with intervals, rate-vol or equity shock ROC/PR metrics, incremental test vs baseline, precision at a *frozen* economically tolerable alert rate and bootstrap interval. For continuous effects: incremental R2/RMSE/MAE as applicable, sign stability and effect-size intervals, matched-event contrasts with multiple-testing correction (BH-FDR or a prereg family-wise approach). For strategy studies: simulate a **hypothetical** pre-auction defensive window with slippage/fees, early sell opportunity cost, realistic close/next-open, and exposure held constant outside prespecified windows; no automatic position sizing. Provide calibration/false-alarm by regime, event tenor, era and shock source. A single profitable historical crisis does not pass.

The exact numerical thresholds for `GO` versus `NO-GO` must be frozen in a prereg **before opening holdout outcomes**, using practical baselines and economic utility. Do not post-select an AUC, p-value, sample split, score weight, target loss magnitude or false-alert quota after seeing results. A nominal positive t-stat alone is insufficient. Inferred probability is not validated simply because formulas are deterministic.

### Adversarial review

Have an independent reviewer test: (1) PIT clocks and vintages; (2) leakage from announcement/result/settlement; (3) sample overlap and multiple-testing; (4) base-rate confound/placebo; (5) statement of causal vs predictive inference; (6) math units and data rights; (7) rates-to-equities transmission sign assumption. Re-run a small randomly selected event casebook by hand from raw official sources. Cite which source edition was used and whether original data were actually inspected.

## R7. Historical failure memorial / DO_NOT_REDO

Read existing artifacts **before** suggesting new experiments:

- `macro/reports/slf006-auction-absorption-phase0.md`: SLF-006 demand absorption z-score not a validated forward signal; note corrected t-stat/FDR and sample-split result. Do not rebuild the exact same feature on the same cohort and call it a new alpha study.
- `macro/reports/d2-rates-calendar-flows-phase0.md`: unconditional/conditional 10Y/30Y pre-auction concession/rebound strategy failed; separate month-end index-extension effect did not validate V1.
- `mastermind-terminal/docs/PHASE2_MARKET_RISK_GATE_VERDICT.md`: per-name exit warning stress-gating is killed because within-regime placebo beats it; no approval by showing only a higher drawdown rate in stressed periods.
- `Mastermind/brain/anticipation.py` and `brain/treasury_context.py`: dormant/flagged context and auction stress, not the proof of successful prospective grading.

Only reopen a failed family on **materially new hypothesis, data, input timing, regime interaction, outcome or market mechanics**, and state how that avoids retrying a failed unchanged experiment. Publish nulls and do-not-promote rules even when a proprietary-style dashboard presentation is attractive.

## R8. Research deliverables / save locations (proposal)

Use existing repository/source-custody owners and existing Agent OS continuity; confirm the workstream is properly linked to `WS:RATES-INFLATION-COMMAND` / Event Intelligence before writing a new organizational record. Suggested research subtree under Macro, subject to current custody:

```
research/sovereign_auction_pressure/
  00_current_state_and_collision_census.md
  01_primary_source_and_rights_matrix.md
  02_pit_announcement_and_result_clock_audit.md
  03_mechanisms_and_counterevidence.md
  04_pre_registered_hypotheses_and_targets.md
  05_variable_dictionary_and_hand_checks.md
  06_evaluation_design_and_controls.md
  07_reproducible_code_and_results_manifest.md
  08_adversarial_review_and_verdict.md
  09_build_readiness_and_exact_w1_w2_commissions.md
```

Results should include actual rerunnable scripts/fixtures and data lineage but not proprietary datasets in GitHub, secrets, private holdings or unauthorized paid quotes. Source snapshots and historical revisions belong in the existing authorized DataOS artifact store, not a second state/event database. Keep stable ids/paths and digest/commit refs. If tools lack write permission, return a complete, copyable research report and exact `NOT_CANONICALLY_PERSISTED` state; never pretend it was saved.

Research outputs by branch:

- H1: first release-vintage event study or honest `PIT_GAP`/`DATA_GAP`.
- H2: pre-auction duration x fragility evidence/contrary case, with rates-market proxy feasibility.
- H3: settlement cash pressure accounting and empirical feasibility; scenario vs observed labeled.
- H4: ex-post auction demand/tail post-release effect plus null verdict.
- H5: T-1 equity shock hazard study and gate against regime placebo; specifically answer whether cash-before-auction has incremental value.
- H6: global sovereign source and rights expansion ranking, no obligation to launch international collection yet.

For each: evidence grade `MEASURED_DESCRIPTIVE`, `RETROSPECTIVE_ONLY`, `SHADOW_ELIGIBLE`, `PROSPECTIVE_PASS`, `NULL_NO_GO`, or `INSUFFICIENT_PIT`; explain why. These are report labels only, not formal trading authority or Executive states.

## R9. First 3 executable mission goals in receiving Pro session

1. **Recover without duplicating:** pin current protected source, Macro/Mastermind/Terminal revisions, exact open PRs and existing Agent OS records. Produce a capability ledger, collision map and confirmed data ownership; do not overwrite #7273/#7320.
2. **Prove official event and PIT feasibility:** choose real instrument examples, retrieve original dated announcement and result sources, construct a minimal known-at/revision timeline and a corrected release/settlement taxonomy; test source shape and parser assumptions. Return a concrete gap table with reproducible file/line/source citations.
3. **Freeze hypothesis/evaluation law and build path:** prereg H1-H5, baseline controls and holdout, map each validated mechanism to the first useful Macro display vertical, then start the first lawful implementation slice or delegate bounded source tests while continuing principal work. Verify actual producer-to-consumer evidence, not merely status artifacts.

Do not ask the user to re-authorize ordinary in-scope research and implementation after deliberate live delivery. If runtime source custody, payment, paid data, deployment, active worker or effect-uncertainty gates are missing, block **that specific action** and advance independent source/method work. Do not claim background agents, model modes, credentials, or permissions not observed.

## R10. Full program success / failure decision

**Mandatory win even under null alpha:** a trustworthy calendar and event dossier covering all eligible official US securities, source/version/freshness and economic importance with transparent no-false-precision DV01/new-cash accounting, integrated in current Macro/Bonds and delivered to Terminal context with actual browser/source proof.

**Research win:** either an incremental, preregistered, point-in-time cross-asset stress model worth forward testing *or* a rigorous demonstration that the existing regime-based risk system is already as good, so the auction project correctly remains intelligence/context.

**Optional later win:** prospectively validated risk warnings, gated solely through the existing Mastermind risk/portfolio authority. No unconditional `go cash` implication, no direct order/trade/sizing effect and no independent event-authority/control plane.
