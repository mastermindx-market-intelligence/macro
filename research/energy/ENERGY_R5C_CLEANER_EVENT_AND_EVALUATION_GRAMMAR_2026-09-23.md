# Energy R5C — Cleaner historical event case and evaluation grammar

**Research program date:** 2026-09-23  
**Operation:** `gmi-energy-sector-research-20260923-sol-001`  
**Carrier:** Macro PR #7791 / `sol/energy-sector-research-20260923`  
**State:** research-only / HOLD. No production ingestion, basket/rank/entry/size/trade authority and no Fable handoff.

## 1. Why this case exists

R5B's first historical case, Equinor Q4 2024, established a strong pre-event expectation chain but the result day also contained the company's Capital Markets Update. That makes it useful for information-clock and metric-definition controls but weak as a clean earnings-response experiment.

Q1 2025 is **cleaner, not clean**. It was an ordinary quarterly-results day rather than a Capital Markets Update. The Empire Wind stop-work order was already public on 17 April and Northern Lights Phase 2 FID was public on 27 March. However, the Q1 release added more Empire Wind exposure/context and announced the second 2025 buyback tranche. Broad-market and commodity moves were also material. The case therefore improves the event-study grammar without granting causal attribution.

## 2. Historical expectation evidence

On 9 April, Equinor invited analyst estimates for Q1 and stated that it publishes collected consensus one week before the 30 April result. The current Historical consensus archive identifies Q1 2025 as collected in April from 20 analyst inputs and records:

- adjusted operating income before tax: **USD 8.508bn**;
- adjusted operating income after tax: **USD 2.377bn**;
- adjusted EPS: **USD 0.85/share**;
- total equity production: **2.104m boe/day**.

The exact pre-event byte/version of that panel was not independently recovered. A 30 April 06:55 independent article confirms the USD8.508bn pre-tax expectation after the result was released, but result-morning reporting cannot be used to backdate the exact panel byte to a week earlier.

Evidence grade:

`ISSUER_PROCESS_PLUS_CURRENT_ARCHIVE / EXACT_VALUE_BYTE_NOT_INDEPENDENTLY_TIMESTAMPED_PRE_EVENT`

This is weaker than R5B Q4's independently timestamped 29 January values and must stay weaker.

## 3. Definition-matched actuals and surprise vector

The issuer's result reports adjusted operating income of approximately **USD 8.65bn**, adjusted operating income after tax of **USD 2.25bn**, adjusted EPS of **USD 0.66/share**, and equity production of **2.123m boe/day**.

Using the explicit research inputs in the model:

| Metric | Consensus | Actual | Descriptive difference |
|---|---:|---:|---:|
| Adjusted operating income before tax | 8.508bn | 8.650bn | **+1.67%** |
| Adjusted operating income after tax | 2.377bn | 2.250bn | **-5.34%** |
| Adjusted EPS | 0.85 | 0.66 | **-22.35%** |
| Equity production | 2.104m boe/day | 2.123m boe/day | **+0.90%** |

Again, the vector is mixed. A positive pre-tax and production read coexists with weaker after-tax operating income and EPS versus the archived aggregates.

The same-day independent article maps USD1.789bn to an after-tax adjusted operating label. Equinor's own release instead distinguishes approximately USD2.25bn adjusted operating income after tax from approximately USD1.79bn adjusted net income. R5B already established this family of label risk. The Q1 case reinforces the rule: **issuer metric definitions govern issuer actuals; third-party relabeling remains visible as a conflict, not silently adopted.**

## 4. Declared return window and market context

For a result released before the Oslo market opens, the proposed default event window is:

`prior official close -> event-day official close`

A 30 April closing-market report says:
- Equinor **-0.4%** to NOK237.90;
- Oslo Børs Benchmark Index **+1.0%**;
- Brent June contract **-1.4%** versus the prior Oslo close;
- Dutch TTF **+1.6%**.

These are **externally reported same-day context**, not a Mastermind-reproduced total-return or event-study series.

The simple EQNR-minus-OSEBX difference is **-1.4 percentage points**. It is a descriptive benchmark residual, not alpha and not a causal earnings-response estimate. Brent and TTF move in opposite directions, and Equinor has both liquids and gas exposure plus project-specific information. No one-for-one commodity subtraction is defensible without a predeclared exposure model.

## 5. Confound inventory

### Pre-known before results

- Empire Wind stop-work order: received 16 April and publicly disclosed 17 April.
- Northern Lights Phase 2 FID: announced 27 March.

These events belong in the pre-event information set and must not be relabelled as newly originated on 30 April.

### New or refreshed on results day

- Q1 earnings and production.
- Additional Empire Wind exposure/context in the report and analyst discussion.
- Second 2025 share-buyback tranche up to USD1.265bn, while the issuer said expected total 2025 capital distribution remained USD9bn.
- Other normal quarterly operational and capital-allocation disclosures.

Therefore Q1 is cleaner than Q4's earnings-plus-Capital-Markets-Update event, but it is not an uncontaminated earnings-only shock.

## 6. Frozen historical-evaluation grammar

The research program should use the following grammar before any future predictive qualification.

### Information time

Every estimate, actual, quote, benchmark and commodity input carries:
- observation period;
- first-known/publication time;
- retrieval time;
- correction/restatement vintage;
- source and rights state.

A current archive may corroborate history but does not manufacture an earlier byte timestamp.

### Metric matching

Compute a surprise only when estimate and actual share:
- metric definition;
- unit;
- fiscal/event period;
- ownership/per-share basis.

No generic beat/miss label is allowed when the matched vector has mixed signs.

### Forecast revision

A revision requires the same fixed forecast horizon. A roll from FY2026 to FY2027 is not a revision. A changed aggregate with a changed panel does not prove analysts revised their own estimates.

### Return construction

Use a predeclared window based on release time:
- before open: prior close to event-day close;
- after close: event-day close to next trading-day close.

Prefer reproducible official/accepted price series with corporate-action treatment. External reported moves remain external observations until reproduced.

### Controls

Benchmark residuals are descriptive unless an accepted model gives them stronger meaning. Relevant commodity prices remain separate contextual variables unless a predeclared exposure model specifies how to combine them.

### Corporate actions

Mechanical ex-dividend, split and rights effects require return adjustment. A buyback or financing announcement is event information and belongs in the confound ledger; it is not itself a mechanical price adjustment.

### Confounds

Inventory at minimum:
- earnings/result release;
- guidance;
- strategy/Capital Markets Day;
- M&A;
- financing/capital return;
- policy/regulatory news;
- commodity/macro shocks;
- corporate actions.

A confounded event may still test data handling and descriptive synthesis. It may not train a clean causal earnings-surprise rule without an explicit treatment.

### Predictive gate

No alpha, price-target, current cheap/expensive or forecasted-return claim follows from R5. A predictive claim requires a frozen sample/evidence grammar, non-lookahead inputs, declared controls, corporate-action-safe returns, and accepted out-of-sample evaluation.

## 7. R5 completion status

R5 now has:
- current/source-labelled expectations across multiple companies;
- one historical case with strong independently timestamped pre-event aggregate support but a major strategy confound (Q4 2024);
- one cleaner ordinary-quarter case with weaker exact-value timestamp evidence and explicit market/commodity controls (Q1 2025);
- a frozen evaluation grammar that tells R6 what data and proof the product must preserve.

This is sufficient to stop treating the historical-evaluation problem as an undefined research gap. It is **not** sufficient to claim predictive edge or to populate a production estimate warehouse.

R6 can now specify how existing Mastermind owners should store/compose these observations, how the UI communicates evidence quality and contradictions, and what implementation/browser acceptance proves the workflow. Fable handoff remains `NOT_ISSUED` until R6 is mature.

## Sources

S01 — Equinor Q1 consensus invitation, 9 Apr 2025: https://www.equinor.com/news/20250409-invitation-estimates-first-quarter-financial-results

S02 — Equinor consensus / historical-consensus archive: https://www.equinor.com/investors/consensus

S03 — Equinor Q1 result, 30 Apr 2025: https://www.equinor.com/news/equinor-first-quarter-2025-results

S04 — Equinor Q1 SEC filing: https://www.sec.gov/Archives/edgar/data/1140625/000114062525000084/a01equinorquarterlyreport-.htm

S05 — Finansavisen/Infront result-morning consensus reference: https://www.finansavisen.no/tdn/2025/04/30/06458190/equinor-justert-driftsresultat-usd-8.646m-i-1.kv-2025-ventet-8.508

S06 — Finansavisen 30 Apr close report: https://www.finansavisen.no/finans/2025/04/30/8261103/industriaksje-til-bunns-kurshopp-for-sveaas-og-fredriksen

S07 — Equinor Empire Wind halt disclosure, 17 Apr: https://www.equinor.com/news/20250417-suspends-offshore-construction-activities-empire-wind

S08 — Equinor Northern Lights Phase 2 FID, 27 Mar: https://www.equinor.com/news/20250327-northern-lights-phase-2

S09 — Equinor second 2025 buyback tranche, 30 Apr: https://www.equinor.com/news/20250430-second-tranche-2025-share-buy-back-programme
