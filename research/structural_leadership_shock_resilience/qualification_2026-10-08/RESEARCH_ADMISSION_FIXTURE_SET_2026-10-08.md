# SLR-P0 — deterministic pre-outcome admission fixture set (research only)

Date: 2026-10-08. Companion to frozen study v1.0.1 and the explicit **pre-outcome v1.1 amendment** in this directory. No actual SLR forward outcomes, protected CR1/AF1/RH1 states, or refused host source rows were opened; this file uses conceptual and synthetic examples. **TEST_FIXTURES_SPECIFIED / EXECUTION_NOT_CLAIMED / SCIENTIFIC_ADMISSION_NOT_GRANTED.**

## 1. What this document is and isn't

The purpose is to remove expensive ambiguity for an independent local-Codex/quant reviewer **after authorized historical evidence arrives**. These are exact test inputs, assertions, and failure labels; they are not runnable production code, a separate Data OS identity owner, a new scheduler, or proof of installed, executed, passing tests. They do not request a retry of the prior explicitly refused host source inventory, prior alias/issuer row audit or prior evidence-checker publication attempt.

The frozen v1.0.1 primary formula and numerical thresholds are unchanged. The v1.1 amendment solely disambiguates the H7 scheduled-landmark risk set and makes already-implied input gates explicit. `SOURCE_NOT_ADMITTED` remains the current factual state.

## 2. Pre-outcome mandatory fixtures and expected results

| ID | Controlled synthetic case | Required assertion |
|---|---|---|
| F01 | **H7 future-selection witness**: four equally likely records `(R,Y)=(-1,-1),(-1,+1),(+1,-1),(+1,+1)`. At D+20 all pass baseline source/leader rules. Define a *future* eligibility flag `S=(R==Y)` to illustrate conditioning on later C−1 leader status or first-shock presence. | Without conditioning, `E[R]=E[Y]=E[R*Y]=0` and covariance is 0. Selecting only future `S=true` leaves two records with covariance +1, a purely artificial perfect association. v1.1 H7 must enroll all four at D+20, independently of S. This demonstrates **possibility of selection bias**, not observed empirical bias or an exact model of the market. |
| F02 | **Ex-dividend total-return witness:** split-adjusted closing price $100 before ex-dividend, $99 after; $1 cash dividend ex-date; no split, no price movement other than payout. | Price-only return = −1%; correctly constructed one-day economic total return = 0%. If lagged residual RMSE=2% and peer return is 0, treating price-only as total return shifts standardized residual by −0.5. The demonstration is algebraic, not a claim about observed source error rates. |
| F03 | **Same issuer double class:** Subject share-class A and peer class B share a confirmed historically valid economic issuer on C−1, despite different security identifiers. | Both listings of the subject issuer excluded; require >=20 **other issuers**, not 20 share classes. Modern CIK equality alone cannot substitute for full historical issuer validity/exception adjudication. |
| F04 | **Ticker reuse:** Historical issuer I1 owns symbol XYZ until effective day u; unrelated I2 owns XYZ after date v, with an intervening gap. Both current ticker details and a timeless `XYZ->I2` alias exist. | Historical date before u resolves only I1 if independently evidenced; between u and v is unknown; >=v can resolve I2 if evidenced. Do not back-assign the current issuer to I1's historical returns. |
| F05 | **Alias interval:** A symbol is historically valid on `[2018-01-01,2018-06-01)` and newer alias on `[2018-06-01,open)`. | Resolve old alias on 2018-05-31, refuse old alias on 2018-06-01; new alias begins at valid_from. A legacy alias with both bounds null is not affirmative proof about 2014. |
| F06 | **GICS transition and ETF inception:** A technology-classified company on 2018-09-27 is recorded by a current vendor as Communication Services in 2026. XLC's first listed session is in June 2018. | Current sector does not overwrite historical sector. Historical source validity governs date; benchmark must not be left-truncated by selecting today's XLC blindly. Distinguish GICS structural-effective date, fund launch and index-implementation dates; a listing date alone is not the company's historical classification. |
| F07 | **SEC reporting-period leak:** A 10-Q has report period June 29, 2019 but was accepted by the SEC on July 31, 2019. A historical ticker-detail query at June 29 returns data derived from the 10-Q. | That filing's values are **not publicly known June 29** despite the API's as-of date. At July 31 after actual acceptance/dissemination, they may be available; enforce actual cutoff/next-session rule. No default based on report_period only. |
| F08 | **Missing exchange session:** Subject and benchmark have 64 valid common observed rows spanning 65 scheduled exchange sessions; one subject session is missing within a nominal 21-row return window. | A `pct_change(21)` computed after intersection of available dates is a 21-*observed-row* return that can span 22 exchange sessions. The frozen SLR session-count window must be rejected or completed only with genuinely qualified source data, not a forward fill/calendar compression. |
| F09 | **First-common-shock unknown:** first candidate date C0 in D+21..D+63 lacks qualified peer/issuer prices. A later date C1 passes all threshold tests. | `FIRST_CHALLENGE_UNOBSERVABLE`, not a C1 primary event. C1 cannot become the first challenge because C0 could qualify and change selection. |
| F10 | **Challenge controls:** issuer A and issuer B share a sector/date cell. Both have complete source/labels, but no within-cell Z variation. | Cell does not identify Z; record it explicitly. Date×sector singleton cells are non-identifying. Do not remove fixed effects, weaken peer criteria, or change the horizon to rescue positive regressions. |
| F11 | **C+1 label:** shock features use full C close; the 21-session economic-total-return label is anchored at C and uses days C+1..C+21. | No part of C's return appears in forward label. A close-C anchor is research measurement, not an executable close-C fill. Terminal cash proceeds remain in wealth or are unresolved, never silently zeroed. |
| F12 | **H5 rebound landmark:** independently observed rebound B>C, subject U only known after B close. | Never leak U into C-time features or labels; if predicting after B, reanchor the peer total-return baseline at B and include all no-rebound/unobservable cases in the risk-set accounting. |
| F13 | **Issuer/type unknown:** one of 20 purported peer tickers lacks historical instrument type; another is a preferred/share class; a third has ambiguous issuer reuse. | These may not count toward the >=20 *other issuers* coverage gate; exclude or abstain, and account for resulting peer-count shortfall. No current common-stock listing proves all older observations. |
| F14 | **Negative/positive-source gate:** documentation says a historical GICS dataset/API exists, but no actual feed file, usage right or historical issuer link is supplied. | `SOURCE_NOT_ADMITTED`. Documentation existence ≠ owner-entitled content availability; no invented credentials, blind purchase or generated “historical” sector labels. |
| F15 | **Owner-clock earnings schedule:** actual company earnings release occurred five sessions after C−1, but schedule was only publicly announced two sessions after C−1. | A “known upcoming earnings within five sessions” boolean at C−1 is **unknown**, not true. Retrospectively observed release dates may label *actual events*, not the preannounced schedule. |
| F16 | **Source/basis boundary:** prior 252-day subject bar series includes one raw/pre-split source splice and total-return benchmark; 2014-era old issuer and 2024-era new issuer share a ticker. | Do not fit lagged betas, generate Z or Y with mixed return bases/identities; require bounded source, split/dividend/merger action receipt and side-by-side rank-invariant parity or abstain. |

## 3. The independent review has to produce real evidence

For F01 and F02 the arithmetic is independently checkable without market files:

```
F01: full four-case E[R]=0, E[Y]=0, E[R*Y]=0, Cov=0.
     future S=true has only (-1,-1) and (+1,+1):
     E[R]=E[Y]=0, E[R*Y]=1, Cov=1.
F02: price_return=(99/100-1)=-0.01
     total_return=((99+1)/100-1)=0.00
     implied_Z_shift=(-0.01 - 0.00)/0.02=-0.50
```

A pure-JavaScript arithmetic canary in the originating conversation independently reproduced these exact expected values. That is not a test of installed source code or actual source quality.

**Mechanical-review acceptance** once a lawful, qualified source and code carrier exist: the actual isolated research adapter passes every applicable fixture against its source reads; code hashes, input receipts and test runner/exit codes are retained; test cases are from this frozen pre-outcome file, not selected after empirical SLR returns; all negative/unobservable cases are reported. A code file that was refused publication in a prior phase does not become available just because these fixture descriptions exist.

## 4. Required output of source-qualification Packet 1

Use the *existing* identity, classifications and price/adjustment owners, not a second canonical registry. Return an immutable owner-qualified source receipt with:

1. `source_owner / source_field / source_object_digest / coverage_period / permission_scope` for each historical GICS, ticker/security/issuer, type, membership, price basis/corporate actions, C−1 market cap and earnings/schedule control.
2. Distinct `economic_valid_from/to`, `classification_known_at`, `SEC_report_period`, `SEC_filing_accepted_at`, `first_available_at`, `ingested_at` and `correction_generation` wherever relevant; unknown clocks remain unknown, not backfilled.
3. Accepted historical **security and issuer identity** collision receipts and ticker-reuse/rename/delist/ADR exceptions; peer count by unique other issuer, never by symbol.
4. Source-validity comparison for 2016/2018/2023 taxonomy changes, 2015 XLRE and 2018 XLC ETF inception, source price adjustment crossovers, issuer-level ex-self, and historical terminal payoffs.
5. **Outcome-blind** Detector-D D-onset and C−1 watch continuation **prefix parity** (frozen original onsets, no silent new dates); 252/504-session lookbacks with exact master sessions; first C status and no-later-event substitution.
6. Date×sector cells, independent dates, issuers, candidate C observability, complete-case controls, and occupied 63-session blocks. Only after this incidence/power assessment and independent review can any historical forward label be read.

This is a **review/acceptance template**, not an automated source-admission gate or executable instruction to reuse forbidden host calls. The previously refused host row/inventory operations remain refused until the original governing permission changes; a new session, model, tool or operator is not itself evidence of such change.

## 5. Current status and next authorized action

**FIxture definitions: specified, not executed against production or historical data.**
**Input qualification: NOT_ADMITTED.**
**Historical hypothesis: NOT_TESTED.**
**Commercial GICS entitlement: unverified, not proven absent.**
**Risk review: independent source/method signoff owed; GitHub CI cannot supply scientific acceptance.**

Original research and both protocol revisions are retained intact. No protected forward outcomes, product ranking, trading, producer logic, Data OS identities or Executive jobs were modified. Once qualified source evidence is lawfully available, use this fixture set to limit builder ambiguity and accept or decisively reject the frozen cohort without data-mining.