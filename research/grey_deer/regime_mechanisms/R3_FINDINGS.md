# R3 — historical knowledge integrity and recipient-specific risk

**Date:** September 28, 2026. **Operation:** `risk-regime-mechanism-research-20260927-sol-001`. Existing Grey Deer / MAS-258; issue #8128; Draft/HOLD PR #8133.

**MISSION_COMPLETE: false. Research-only implementation and descriptive empirical findings. No predictive, sizing, trading, production or independent-review acceptance.**

## 1. What changed

R3 adds two concrete capabilities to the research substrate. A pure adapter selects the macro knowledge available before a historical decision and calls the existing regime endpoint only on an admissible score prefix. Separately, a pinned, common-calendar experiment measures whether a broad-equity loss target represents losses in regional banks and the wider financial sector.

The strongest empirical result is a target mismatch, not a newly successful predictor: in 1,140 of 1,930 regional-bank 5%-loss windows, SPY did not suffer a 5% loss under the same horizon definition. That is 59.1%. The mismatch also appears on a fixed nonoverlapping sampling grid and after the regional-bank fund's benchmark change. This supports recipient-specific evaluation, not a causal bank-stress label.

The original exact-incumbent comparison remains unrun. A source-inspection call for four existing source files was explicitly blocked at the start of the turn; it was not repeated or rerouted. R3 proceeded with distinct already-inspected source, existing archives and new recipient outcome data. The separate prior MOVE integration denial remains untouched.

## 2. Reconstruction implemented, with its limits intact

### The temporal adapter

`archive_asof` selects the latest valid value of each observation period strictly before a date-only decision, preserving publication date separately from observation period. It uses full-vintage input, not stitched initial releases. It rejects conflicting duplicates, impossible periods/validity intervals, invalid values and initial-release-only payloads. An expired value without a successor is unavailable, not silently filled.

The knowledge digest covers selected information, not the complete file containing later vintages. Appending a future revision therefore does not change an earlier knowledge identity. The raw archive hash remains separate run provenance. ALFRED explicitly distinguishes observation periods, historical vintages and closed validity intervals; initial-release-only data do not contain subsequent revisions. [S1–S3]

`endpoint_at` accepts score revisions with explicit timezone-aware availability timestamps. It selects only available score rows, takes the most recent eligible revision for each date, and invokes a callback owned by the existing regime producer. It publishes only that call's endpoint, not the callback's retrospectively reconstructed history. It preserves an explicit fit cutoff, score as-of, selected-knowledge digest and null state. It cannot mutate the caller's input and grants no rank/size/gate/execute authority.

### Actual-source execution

The runner extracts the already-inspected `_causal_filtered_pquad` and `_logsumexp` from immutable `engine/regime_one.py`. The fit and forward recursion remain original. Because the native runtime lacks `hmmlearn`, only the Gaussian emission-density dependency is supplied by SciPy, as in R2. This is dependency-isolated evidence, not full installed-production parity.

The native run computed **56 prespecified assessment endpoints**, all available, with zero fit-cutoff-after-decision violations. These are quarter-end source sessions from 2015 to the fixed September 25, 2026 cutoff plus ten declared episode dates. Three prespecified real-data comparisons—March 9, 2020; May 10, 2021; March 13, 2023—returned identical complete assessment objects whether the caller supplied the truncated archive or its later extension.

The macro adapter was tested at **12 fixed dates for each of PAYEMS and CPIAUCSL**. All 24 selected-knowledge snapshots were identical under future-archive extension and matched a separate direct selection of the applicable full archived vintage. Synthetic tests additionally cover later revisions, same-day exclusion, validity, mutation isolation and absent data.

### What this does not prove

The numerical regime experiment is explicitly **PARAMETER_ONLY_DIAGNOSTIC**. The legacy score archive used by the existing function is not historically vintage-qualified. Its 23:00 UTC daily availability is a declared synthetic date-label convention for testing the adapter, not an actual historical release timestamp.

Thus R3 fixes the *research call boundary* that allowed later observations to affect the parameter fit for an old endpoint. It does not establish that the score values originally supplied to that fit were available then. The full input-vintage-to-source-native-score reconstruction, exact incumbent replay and original common-sample R2 model comparison remain open. No existing production source was repaired, replaced or activated.

## 3. Recipient outcome experiment

The experiment was declared in commit `c3f2f5e4ee0419d8b059231a394f347467e7f476` before constructing its new outcomes.

Inputs are the existing SPY, KRE and XLF `close` series at immutable Macro pin `f6dae649ee6d32ec65a95ccea411b205d0b0bc45`, using the repository's dividend-adjusted total-return convention. They are traded fund proxies, not historical constituent panels or bank funding measurements. KRE represents regional-bank equity exposure; XLF includes a much broader range of financial industries. Current holdings must not be copied backward as historical holdings. [S4,S5]

All assets are aligned to the complete observed SPY calendar without forward or backward filling. A target is one if any of the next 21 session closes falls at least 5% below the decision close. A separate 10% threshold was prespecified. Today's already-realized loss is excluded. All future sessions must exist; incomplete/missing windows are unavailable, not no-event. Existing drawdown from the trailing 252-session high is recorded separately.

The main sample contains **4,943 common mature decision dates** beginning in 2007. Daily future windows overlap; counts are not independent crises. The fixed-grid sensitivity takes every 21st SPY session from the first session on/after January 1, 2007, with no event-driven reset, producing 236 common mature observations. Although outcome windows do not overlap on that grid, common crises and economic dependence remain.

### Primary 5% threshold, 21-session horizon

| Relationship to SPY | Regional banks: KRE | Broad financials: XLF |
|---|---:|---:|
| Both assets hit their 5% loss target | 790 | 841 |
| SPY only | 109 | 58 |
| Recipient only | **1,140** | **545** |
| Neither | 2,904 | 3,499 |
| Common decision dates | 4,943 | 4,943 |

Among KRE loss windows, **59.1%** did not coincide with the same SPY loss target (1,140/1,930). On the fixed 21-session grid the corresponding fraction is **59.1%** (52/88). For XLF the full-sample fraction is **39.3%** (545/1,386).

### Prespecified 10% sensitivity

At the 10% threshold, there are **521 KRE-only**, 203 joint, 26 SPY-only and 4,193 neither windows. Thus 72.0% of KRE 10%-loss windows lack a simultaneous SPY 10%-loss window. The fixed-grid equivalent is 26/37, or 70.3%.

This difference can partly reflect the funds' different volatility, concentration and changing exposures. It is not evidence that an early-warning model missed 59% or 72% of bank crises: no such model was tested. Nor is a 5% equity move a bank-run label. Equal-frequency/volatility-normalized comparisons and independent funding outcomes would be different, preregistered studies, not retroactive threshold changes here.

### Instrument changes and limitations

The KRE sponsor documents a benchmark change effective October 24, 2011. [S4] After that boundary, the primary sample still has 847 KRE-only versus 444 joint windows, a 65.6% recipient-only fraction. This is a descriptive split, not a significance claim.

XLF's 2016 reconstitution and special distribution are a separate structural change. An official exchange notice documents the distribution effective September 19, 2016; the sponsor's announcement describes the portfolio transition. [S6,S7] A **post-result source-quality sensitivity**, not a new predictive test, restricted the sample to September 19, 2016 onward. It yielded 647 KRE-only and 331 joint windows; XLF had 227 recipient-only and 346 joint windows, over 2,498 common dates. On the distribution date, the stored dividend-adjusted XLF daily return was approximately +0.638%, not an artificial double-digit loss. This is a useful seam check, not complete corporate-action certification.

No cross-country replication, historical bank membership panel, intraday execution study or provider-vintage market-price archive was created. Historical cases informed the design, so this is explicitly exploratory target diagnosis, not an untouched test.

## 4. Why the same market episode needs different recipients and stages

The dates below were specified before this new outcome calculation, but were chosen from already-known historical episodes. The numbers describe subsequent paths; they were not predictions issued on those dates.

| Decision date | SPY minimum subsequent 21-session return | KRE minimum | XLF minimum |
|---|---:|---:|---:|
| January 3, 2022 | −9.73% | −2.13% | −3.36% |
| March 8, 2023 | −3.40% | **−26.58%** | −11.38% |
| March 13, 2023 | +1.02% | −4.69% | −2.06% |
| May 1, 2023 | −2.50% | **−12.98%** | −4.63% |

A positive minimum means every future close in the specified window was above the decision close. These are close-based paths, not intraday maximum losses.

**March 8, 2023:** a SPY-only 5% outcome would classify the next window as no event, despite a 26.58% additional regional-bank decline and 11.38% broad-financial decline. The relevant equity recipient is crucial. These prices alone do not prove a bank run or which funding mechanism caused the losses.

**March 13, 2023:** KRE was already 37.48% below its trailing 252-session high. Its additional close-based decline in the next 21 sessions was 4.69%, narrowly short of the fixed 5% threshold. Declaring the environment calm because that future target was zero would confuse existing damage, further loss and economic repair. No threshold is moved to convert this particular observation into a hit.

**May 1, 2023:** KRE was already down 38.20% from its trailing high and subsequently fell another 12.98%, while the same SPY and XLF 5% barriers were not crossed. Broad financial-sector breadth is therefore not always a sufficient substitute for the most exposed subindustry.

**January 3, 2022:** the opposite pattern appears. SPY's subsequent minimum was −9.73%, while KRE and XLF stayed inside −5%. This argues against permanently treating banks as the strongest recipient of every risk-off episode. It is a comparison of return paths, not causal identification of rates or earnings shocks.

Across 2023, there were 112 KRE-only 5%-loss windows, 25 joint and zero SPY-only windows. At 10%, there were 57 KRE-only windows and zero SPY 10%-loss windows. These are overlapping dated windows—not 112 or 57 distinct banking crises.

## 5. Implications for the intended product

The research supports keeping three questions independently visible:

1. **Current damage:** which recipients are already impaired, and how severely?
2. **Incremental hazard:** what additional loss or dysfunction is being forecast, for which recipient and horizon?
3. **Propagation/repair:** is independently measured damage spreading through an evidenced channel, stabilizing, or repairing?

A country-level broad index can remain comparatively resilient while a subindustry is seriously damaged. A future-loss estimate can fall after a large selloff without proving repaired funding or a safe entry. Conversely, a sector can remain resilient while the broad index sells off. Those are distinctions a useful risk interface must preserve rather than compress into a single score.

R3 does not supply a new numerical aggregation formula or new live hazard stage. The existing Risk Envelope, Chronicle, Reflex Registry and grading owners retain their roles. Later qualified mechanism experts should emit recipient-specific evidence, keep common sources deduplicated and state attribution uncertainty. LLM explanation cannot create absent mechanism observations or capital-policy authority.

## 6. Exact execution and verification

- Pure adapter source commit: `243e2d967d498ff39573221d8d2cfb7db6cfbfbe`.
- Runner/source set commit: `e9ff7f8e5abb3706b92124554d22c647bbd48913`.
- Published tests commit: `dba3b26f37f6991906e966209f09d4067c2d977b`.
- `r3.py` SHA-256: `ec44dd8aab43f479765de66da4d803cd7909817a859c279ad622ad3571898225`.
- `run_r3.py` SHA-256: `b32be53b28c0c56702f9f2c99af625f0ab80d42676b5fbeaadb3398b14fddb14`.
- Published tests SHA-256: `85c31b07ff02cd3758f84841caec7b36a586c9a8e9ac01ed57ef13a406e656e7`.
- **34 research tests passed** locally and on the exact native mirror; native runtime 1.56 seconds. An initial missing-module RED was observed before implementation.
- Native process 27591 completed exit 0. A second complete run, process 31031, also completed exit 0 and matched both original output hashes byte-for-byte.
- Full results: 42,650 bytes; SHA-256 `d95369aeaa64dc422441e5982a229d1315c3d33d410704860525128fda5a28e6`.
- Parameter replay CSV: SHA-256 `7106254898685f656c939ee82673c228281ac5a9e4199028e09462fa041a4bea`.
- All immutable input hashes were rechecked. No recipient was missing. An independent loop-based outcome oracle returned zero primary-label discrepancies.
- Exact transferred compact summary: 4,478 bytes; SHA-256 `7d6be94e51a40019c36683b7f1e20aa3d3e98c5a70e5a0b5c0df2e78d0e8a2b4`.
- Post-result source-change sensitivity: 724 bytes; SHA-256 `3e9911ff0b9a1f6292227d177718a0085a08c1a9e55e60320b4bed548edc4dc8`.

Full original and reproduced native artifacts remain at:
`/Volumes/Mastermind/research/risk-regime-mechanism-research-20260927-sol-001/r3-e9ff7f8e`.

The downloadable companion contains the tested code/tests, exact compact result, source-change sensitivity, research report, source references, verification and continuation. It does not claim to contain the full 42,650-byte native result or replay CSV. Reproducibility is not independent scientific review; no full repository/Agent OS/hosted CI or production acceptance is claimed.

## 7. Unfinished critical paths and next phase

The original source-native input reconstruction and exact-incumbent R2 comparison remain blocked on the denied source-inspection action. The denial was action-scoped, not proof of a global GitHub/Studio outage. Do not retry the same requested reads by another carrier. No exact human control to resolve the provider refusal is known; do not invent one.

Independently, the next substantive research unit is **bank-funding mechanism qualification**: determine which already-existing bank balance-sheet and funding observations are available historically, at what publication delays, and whether ex-ante duration/refinancing/runnable-funding exposure plus fast stress distinguishes concentrated bank losses from ordinary equity repricing. Freeze the numerical experiment only after actual source coverage is known. Bank identifiers and historical memberships must be point-in-time; current ETF constituents are not a substitute. Equity outcomes remain separate from deposit withdrawal, funding substitution, credit restriction or actual failure outcomes.

R1 taxonomy/source research and the failed R2-D1 construction are preserved, not repeated or retuned. Country replication, energy, FX/carry, propagation, novelty, containment, repair, independent review and eventual integration remain in the parent mission. No early native implementation handoff is issued.

## Primary references

S1. ALFRED, Download Data Help: https://alfred.stlouisfed.org/help/downloaddata

S2. Federal Reserve Bank of St. Louis, FRED API Real-Time Periods: https://fred.stlouisfed.org/docs/api/fred/realtime_period.html

S3. Federal Reserve Bank of St. Louis, Series Observations API: https://fred.stlouisfed.org/docs/api/fred/series_observations.html

S4. State Street, KRE fund/benchmark documentation, including October 24, 2011 index change: https://www.ssga.com/us/en/institutional/etfs/state-street-spdr-sp-regional-banking-etf-kre

S5. State Street, XLF fund/industry coverage: https://www.ssga.com/us/en/individual/etfs/state-street-financial-select-sector-spdr-etf-xlf

S6. MIAX, corporate-action notice, September 16, 2016, effective September 19: https://www.miaxglobal.com/alert/2016/09/16/miax-corporate-action-alert-financial-select-sector-spdr-fund-xlf

S7. State Street issuer announcement syndicated by Business Wire, September 16, 2016: https://www.marketscreener.com/quote/stock/STATE-STREET-CORPORATION-14499/news/State-Street-Global-Advisors-Announces-Benchmark-Rebalance-for-The-Financial-Select-Sector-SPDR--23068654/

Sources checked September 28, 2026. Public source definitions support the data interpretation, not the new empirical counts or predictive validation. The counts are calculations from the frozen repository inputs.
