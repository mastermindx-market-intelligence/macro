# Finance R10C — capital regulation and corporate value-up rerating research

Date: 2026-09-23.  
Operation: `gmi-finance-sector-research-20260923-sol-001`.  
Carrier: Macro PR #7786 / `sol/finance-sector-research-20260923`.  
State: RESEARCH / RETROSPECTIVE MEASUREMENT / DRAFT-HOLD.  
Mission complete: false. Product implemented: false.  
Protected procedure for this tranche: `Mastermind@a7d2b3049e5cdc523e91e61a6e9d70a1cb911157`, Skillpack 1.0.1/bootstrap 1.  
Direct principal reason: `PRINCIPAL_JUDGMENT`.

This tranche advances two frozen R10 cases:

- `R10-EU-CRR3-APPLICATION-20250101`
- `R10-KR-CORPORATE-VALUE-UP-20240226`

It preserves the event-clock amendment and the R10B price-basis law. Formal case outcomes remain `UNMEASURED`; the observations below are mechanism and valuation research, not causal event-study verdicts, rankings or trading signals.

## 1. Executive conclusions

### R10C-1 — CRR3 is a capital-regime transition, not a clean announcement shock

The 1 January 2025 CRR3 application date was known well in advance. EBA disclosure/reporting implementation work was underway during 2024 and its October 2024 monitoring exercise quantified the expected full-implementation burden. Therefore a return window beginning on 1 January cannot be interpreted as the market first learning about CRR3.

The economically relevant object is not `CRR3_ON`. It is:

```text
source-native CRR3 rule change
→ bank-specific credit / operational / market / CVA / output-floor effect
→ RWA and capital headroom
→ pricing / balance-sheet mix / growth capacity
→ normalized return on allocated capital
→ distributable capital
→ required return and valuation
```

At sector level, the EBA estimated a 7.8% increase in minimum Tier 1 requirements at full implementation in 2033, driven mainly by the output floor and operational risk, but only €0.9bn of additional Tier 1 capital need and €5.1bn total capital shortfall for the sampled sector. Those are different quantities and clocks.

Issuer evidence demonstrates heterogeneity:

- Deutsche Bank ended 2024 at 13.8% CET1 and reported a 13.9% pro-forma CRR3 ratio before an expected Q1 operational-risk RWA effect; its fixed-income call described the total CRR3 CET1 burden at roughly 15bp, while the bank still proposed €2.1bn of 2025 shareholder distributions.
- ING reported 1Q25 CET1 of 13.6%, described the Basel IV/model-update CET1 effect as negligible, and reported a net €-1.4bn RWA effect composed of €-9.9bn credit RWA, +€4.6bn operational RWA and +€3.9bn market RWA.

A universal rule such as “higher regulatory capital is bad for banks” is therefore structurally inadequate.

### R10C-2 — The strong 2025 European-bank rally does not identify CRR3 as its cause

Using the incumbent adjusted-close international store and the same fixed 0/5/20/60/120/252-session windows:

- BNP / Deutsche Bank / Santander / ING equal-weight return at +252 sessions: **+88.05%**.
- Amundi EURO STOXX Banks proxy `BNKE.PA`: **+87.32%**.
- EURO STOXX 50 context: **+21.26%**.

The four-bank cohort nearly matched the bank-sector proxy. That is useful evidence of a broad European bank rerating, but not evidence that this four-name selection or CRR3 application caused the rally. Rates, earnings, capital return, credit, politics, positioning and other macro variables remain plausible concurrent explanations.

The Finance product should consequently display regulatory-capital change as one causal candidate inside the bank rerating bridge, not as an event label that directly explains price.

### R10C-3 — Korea Value-Up must be split into four clocks

The correct structure is:

```text
government framework
→ company decision to participate
→ issuer-specific plan and formula
→ actual capital / payout / share-count / ROE / per-share execution
→ valuation recognition
```

The February 26, 2024 Financial Services Commission framework explicitly described company participation and disclosure as voluntary. It encouraged companies to prepare, implement and communicate their own plans, while supporting investor comparison and infrastructure. It did not prescribe one payout formula or one valuation result for every financial group.

Therefore the government framework, a later issuer plan, an actual buyback/cancellation and subsequent financial results cannot share one timestamp.

### R10C-4 — Woori's initial plan date is July 25, not December 3

The prior R10 fixture's issuer-level Woori follow-up clock must use **25 July 2024** for the initial Corporate Value Enhancement Plan.

Primary evidence:

- Woori's Korean disclosure and plan material date the initial plan to July 25, 2024.
- Woori's SEC filing states that it became the first Korean financial group to disclose the plan on July 25.
- Woori's English site later shows a December 3 posting; that is not the initial adoption date and must not overwrite the original Korean/SEC clock.

This correction is append-only and does not alter the frozen broad government-case identity.

### R10C-5 — Company plan quality is more informative than the policy label

The four large financial groups disclose materially different capital starting points, plan formulas, per-share objectives and execution paths:

**Woori, July 25, 2024**
- 2Q24 BPS: KRW 39,133.
- CET1: 12.04%.
- Targets: sustainable ROE 10%, mid/long-term CET1 13%, early 12.5%, and total shareholder return up to 50% as capital improves.
- Important prior: February 2024 materials already contained a tiered capital/shareholder-return policy. The July plan evolved an existing policy; it did not create shareholder return from zero.

**Shinhan, July 26, 2024**
- Plan TBPS reference: KRW 94,635 from 1Q24.
- Targets by 2027: ROE 10%, ROTCE 11.5%, CET1 at least 13%, shareholder return around 50%, and shares reduced below 500m in 2024 and to 450m by 2027.
- The plan explicitly connects ROE/COE, PBR and per-share value rather than relying on dividend payout alone.

**KB, October 24, 2024**
- 3Q24 BPS/TBPS: KRW 152,242 / 147,057.
- Plan architecture links shareholder return to capital: year-end capital above a defined CET1 level funds the following year's return, with additional return tied to a higher second-half capital threshold.
- KB already had substantial buyback and quarterly-dividend activity before the October plan, so the plan is a predictability/formula change rather than a clean first-return event.

**Hana, October 29, 2024**
- September-end BPS: KRW 134,568.
- Plan disclosed PBR around 0.44x at September-end and identified conservative capital management / high CET1 volatility among the undervaluation issues.
- Targets: phased shareholder return to 50% by 2027, CET1 13.0–13.5%, and ROE at least 10%.

The reusable product object should therefore be a non-scoring **Value-Up Execution State**, not a binary `VALUE_UP=true`.

## 2. Broad Korea policy measurement

A preselected four-group cohort (KB, Shinhan, Hana, Woori) was frozen independently of subsequent plan success.

From the prior close before February 26, 2024:

| Window | Four-group equal weight | KODEX Banks proxy | KOSPI |
|---|---:|---:|---:|
| day 0 | -4.35% | -3.28% | -0.77% |
| +5 sessions | +3.93% | +2.27% | -0.69% |
| +20 | +9.99% | +7.63% | +3.35% |
| +60 | +10.46% | +5.63% | +2.07% |
| +120 | +28.18% | +18.54% | +1.25% |
| +252 | +18.38% | +16.08% | -3.53% |

The government framework was therefore **not** a clean positive same-day shock for these banks. Financials later outperformed the broad KOSPI in this descriptive window, but the four-group average remained close to the bank-sector proxy by +252 sessions.

This pattern is consistent with a broad sector rerating but cannot isolate the policy's causal contribution.

## 3. Issuer-plan reaction and later path

All price-return rows below use adjusted closes for shareholder-return path analysis. Quote closes are retained separately for valuation calculations.

| Issuer | Initial plan date | Day 0 | Day +1 | +20 sessions | +252 sessions | +252 excess vs bank proxy |
|---|---|---:|---:|---:|---:|---:|
| Woori | 2024-07-25 | -0.95% | +10.29% | +12.75% | +82.32% | +35.53pp |
| Shinhan | 2024-07-26 | +6.42% | +11.38% | +12.66% | +33.74% | -9.27pp |
| KB | 2024-10-24 | -1.17% | +7.10% | +3.18% | +40.63% | -5.51pp |
| Hana | 2024-10-29 | -0.61% | -4.28% | -5.05% | +56.76% | +9.34pp |

Release timing relative to the local trading session is still a required field: a same-day close cannot automatically be interpreted as the reaction to a plan if the relevant disclosure arrived after the close or alongside earnings.

The cross-sectional dispersion is itself informative. There was no universal “announce a Value-Up plan, receive the same rerating” effect.

## 4. Per-share book versus multiple decomposition

For each issuer, the plan-date quote is paired with the latest source-native book denominator the plan/release made available, then compared with year-end reported book and the final 2024 quote. These are ex-post decompositions; later year-end book values were not known at the plan date.

| Issuer | Anchor | Plan quote | Book anchor | Plan P/book-type multiple | Year-end quote | Year-end book | Year-end multiple | Price change | Book change | Multiple change |
|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|
| Woori | BPS | 14,530 | 39,133 | 0.371x | 15,370 | 40,788 | 0.377x | +5.78% | +4.23% | +1.49% |
| Shinhan | TBPS | 58,000 | 94,635 (1Q24) | 0.613x | 47,650 | 100,214 | 0.475x | -17.84% | +5.90% | -22.42% |
| KB | TBPS | 93,200 | 147,057 | 0.634x | 82,900 | 147,644 | 0.561x | -11.05% | +0.40% | -11.41% |
| Hana | BPS | 65,000 | 134,568 | 0.483x | 56,800 | 137,082 | 0.414x | -12.62% | +1.87% | -14.22% |

Shinhan's plan denominator is explicitly stale versus the July plan date because the plan used 1Q24 TBPS. Do not turn the table into a precision claim it cannot support.

The key finding is still valuable: book-per-share improvement did **not** guarantee near-term multiple expansion. Three of the four groups experienced substantial multiple compression between their plan date and year-end even while the relevant book metric increased.

Later adjusted-return paths reversed much of that near-term picture. That is exactly why Finance needs separate fundamental, expectation, valuation and price clocks.

## 5. Later execution observations

These observations are not used as information available at the original plan date.

- Woori reported FY2024 BPS of KRW 40,788, CET1 around 12.08% on its stated basis, a 33.3% shareholder-return ratio and DPS of KRW 1,200.
- Shinhan's FY2024 presentation shows TBPS of KRW 100,214, outstanding shares reduced to about 499.9m, CET1 around 13.03%, and its then-presented shareholder-return ratio around 39.6%. Later Shinhan communications cite 40.2%; retain both source/version clocks rather than silently replacing the earlier presentation.
- KB reported 2024 BPS/TBPS of KRW 152,836 / 147,644, EPS of KRW 12,880 and shares reduced to about 373.6m. Its 2024 annual report reported net profit up 10.5%.
- Hana's FY2024 presentation reported BPS of KRW 137,082, net income of KRW 3.739tn (+9.3%), ROE of 9.12%, CET1 around 13.13%, shareholder return around 38%, and a KRW400bn buyback.

These data illustrate the correct evaluation order:

```text
plan specificity
→ capital capacity
→ execution
→ per-share compounding
→ durable ROE vs cost of equity
→ valuation recognition
```

A payout target without capital/ROE execution is not sufficient, and improved fundamentals without valuation recognition are not the same thing as a rerating.

## 6. Proposed Value-Up Execution State

This is a research view, not a score.

Required fields:

1. **Policy clock** — government framework/guideline effective and publication dates.
2. **Participation clock** — issuer announcement and board approval.
3. **Pre-plan baseline** — ROE/ROTCE, CET1, BPS/TBPS, share count, existing payout/buyback policy.
4. **Plan specificity** — target horizon, formula versus aspiration, capital threshold, payout mechanism and per-share objective.
5. **Capital headroom** — current CET1 versus operating/regulatory target and disclosed sensitivities.
6. **Return execution** — dividends, buyback authorisations, actual purchases and cancellations.
7. **Per-share execution** — EPS/BPS/TBPS and share-count change.
8. **Profitability execution** — ROE/ROTCE and cost-of-equity relationship.
9. **Risk cost** — credit, funding, RWA, regulation and other offsets.
10. **Valuation recognition** — source-native P/B or P/TB and its denominator/as-of date.
11. **Price recognition** — adjusted return versus bank-sector and broad-market context.
12. **Expectation state** — actual dated consensus/guidance where available; null otherwise.
13. **Conflict state** — e.g. book up/multiple down, payout up/ROE down, price up/no issuer excess.
14. **Falsifier** — what future observation would invalidate the interpretation.

Never fuse these into one corporate-value score.

## 7. Product implications

The Finance dossier should support a direct question:

> Is the stock rerating because the business is compounding more per share, because the market is applying a different multiple, because cash is being returned, or because a wider sector/factor is moving?

For bank capital regulation it should show:

```text
rule → bank-specific RWA effect → CET1/headroom → business response → returns/capital distribution → valuation
```

For Korea Value-Up it should show:

```text
government framework → issuer plan → actual execution → per-share fundamentals → valuation recognition
```

This is much more useful than a generic “regulatory catalyst” or “shareholder-friendly” tag.

## 8. Evidence, owner and measurement boundaries

- International issuer adjusted-return paths use the incumbent `data/intl_search/closes.parquet` store. It is not a new market-data owner.
- Quote closes used for valuation diagnostics are fresh vendor reads and are not a historical-vintage market-data archive.
- KODEX Banks and EURO STOXX Banks proxies are descriptive sector context, not untreated controls.
- No valid historical analyst-consensus baseline has been established for these cases.
- Legal/accounting/capital definitions remain source-native.
- Later financial results are ex-post evaluation evidence, not prior expectations.
- Formal R10 outcome labels remain `UNMEASURED`.

## 9. Primary source register

- EBA, 4 Oct 2024, Basel III/CRR3 monitoring: https://eba.europa.eu/publications-and-media/press-releases/further-tier-1-capital-needs-full-implementation-eu-specific-basel-iii-reform-are-minimal-eba-report
- EBA, 9 Jul 2024, CRR3 supervisory reporting: https://eba.europa.eu/publications-and-media/press-releases/eba-updates-supervisory-reporting-framework
- Deutsche Bank FY2024 release: https://www.db.com/news/detail/20250130-full-year-results-2024
- ING 1Q2025 release: https://ing.com/binaries/content/assets/documents/files/1q2025_press_release__download_.pdf
- FSC Corporate Value-up Program, 26 Feb 2024: https://fsc.go.kr/eng/pr010101/81778
- FSC Value-up guidelines, 2 May 2024: https://fsc.go.kr/eng/pr010101/82213
- Woori initial plan: https://www.woorifg.com/cmm/fms/FileDown.do?fileId=FILE_000000000002901&fileSeq=0&saveFileNm=202407250254395130.pdf
- Woori SEC confirmation: https://www.sec.gov/Archives/edgar/data/1264136/000119312524200356/d870488d6k.htm
- Shinhan July 2024 SEC filing: https://www.sec.gov/Archives/edgar/data/1263043/000095017024086729/form_6k-20240726-1.htm
- Shinhan 2024 Value-Up Plan: https://shinhangroup.com/resources/publish/jp/resource/2024_Shinhan_Financial_Group_Value-up_Plan.pdf
- KB 2024 plan: https://www.kbfg.com/eng/ir/valueup-program/plan/view.htm?B=16&CONTENT=14511&QUERY=list.htm%3F
- Hana Value-Up archive: https://hanafn.com/en/hfm/mnu/ir/valueupplan.do

## 10. Exact next research action

R10C has materially resolved two additional mechanism cases but does not close the historical evaluation program.

Next principal research should move to the remaining unmaterialized R10 cases while preserving this same discipline. Highest-value next pair:

1. **RBI 16 Nov 2023 consumer-credit/NBFC risk-weight changes** — credit-capital tightening with bank/NBFC/product heterogeneity.
2. **APRA 6 Oct 2021 serviceability-buffer increase** — mortgage underwriting constraint with origination, housing and lender-share transmission.

These form a useful contrast with R10C because both change the economics of new credit rather than primarily altering payout/valuation communication.

Do not merge PR #7786 or begin final Fable implementation orchestration yet.
