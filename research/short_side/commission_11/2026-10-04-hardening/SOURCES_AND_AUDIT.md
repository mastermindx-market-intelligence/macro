# Source ledger, current-state receipts and adversarial audit

## Scope and provenance

All live sources below were inspected on **2026-10-04**. Repository reads are bound to the stated commits. Public pages are date-stamped observations and may change. This packet uses durable source links rather than opaque citations from the input report. It contains no raw proprietary data, authenticated broker history, private Research Vault corpus or production credentials.

The source manifest is research evidence, not a new operational registry. Repository and source reads establish the claims noted below, not runtime liveness. The complete Macro tree was truncated; non-results from code/PR search are bounded search outcomes, not exhaustive absence proofs.

### Supplied baseline

- Attachment: `deep-research-report (16).md`.
- Bytes: 74,669. SHA-256: `91e00aeb7dc970b10e54b14c5a6322d923ff607c2ad065f6722a55e5b856615d`.
- The supplied 1,376-line report was read as the requested basis. Its core thesis is retained; the audited REPORT.md supersedes its implementation recommendation. Original embedded turn citations are not independently resolvable here and are not treated as fresh evidence.

## Internal source witnesses

### R1 — Macro FINRA current collector

[collectors/finra.py](https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/collectors/finra.py)

**Read:** 1–220. **Classification:** OBSERVED_SOURCE.
**Commit:** `79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f`.
**Returned blob:** `fab5d3d913dc8fc4b023921ee35bf4f6188f51ef`.

Destructive latest-per-settlement history, current-universe filtering, limited normalized fields, paging and fallback semantics.

### R2 — Macro FINRA short-volume collector

[collectors/finra_short_volume.py](https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/collectors/finra_short_volume.py)

**Read:** 1–220. **Classification:** OBSERVED_SOURCE.
**Commit:** `79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f`.
**Returned blob:** `d92a342a38dd0fdaa5885c71c36f56e71770c7c6`.

Recent re-fetch plus keep-last replacement; Market scope discarded; malformed exempt volume coerced to zero; 18:30 ET operational expectation.

### R3 — Macro IBKR collector

[collectors/ibkr_borrow.py](https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/collectors/ibkr_borrow.py)

**Read:** 1–250. **Classification:** OBSERVED_SOURCE.
**Commit:** `79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f`.
**Returned blob:** `26dc4407520e311c9ecc219090efc0895c9a333c`.

Same-day overwrite, indicative broker rates, predictor-dependent retained population, discarded raw identifiers, lower-bound token labeled unlimited.

### R4 — Macro short-pressure axes

[engine/short_pressure.py](https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/engine/short_pressure.py)

**Read:** 1–170. **Classification:** OBSERVED_SOURCE.
**Commit:** `79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f`.
**Returned blob:** `5471b59cc0334ab2b8ea74370283d8d8d3f6c46e`.

Display authority; eight-session lag; staleness relative to panel maximum; optional cutoff; missing-ADV-column guard inconsistency.

### R5 — Macro ownership crowding

[engine/ownership_crowding.py](https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/engine/ownership_crowding.py)

**Read:** 1–160. **Classification:** OBSERVED_SOURCE.
**Commit:** `79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f`.
**Returned blob:** `3cb610cac65a92fecd96444afb863b143f68a400`.

Existing owner and no-fusion boundary; FINRA ADV anchor uses settlement rather than publication.

### R6 — Macro SI backfill

[scripts/backfill_finra_short_interest.py](https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/scripts/backfill_finra_short_interest.py)

**Read:** 1–190. **Classification:** OBSERVED_SOURCE.
**Commit:** `79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f`.
**Returned blob:** `d0b4e8f639a83f5a47bb9347d25391a4797b0046`.

Explicit as-restated status, inferred lag, manual/local historical panel and sampled revision observations.

### R7 — SI coverage receipt

[data/finra/short_interest_panel_coverage.json](https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/data/finra/short_interest_panel_coverage.json)

**Read:** complete. **Classification:** OBSERVED_SOURCE.
**Commit:** `79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f`.
**Returned blob:** `a0c5f8fff501ed488eb6854919bc311cd4f2414c`.

Stored receipt generated August 15; July 31 horizon; 3,888,611 rows, 206 settlements, 48,679 ticker strings.

### R8 — SP1 frozen research and amendments

[research/short_side/SP1_SHORT_PRESSURE_PREREG.md](https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/research/short_side/SP1_SHORT_PRESSURE_PREREG.md)

**Read:** 1–260 requested; tool excerpt truncated. **Classification:** OBSERVED_SOURCE.
**Commit:** `79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f`.

Historical source and governance evidence only; later amendments must be fully loaded before faithful reproduction. Earlier header text is not current experiment status.

### R9 — SP1-B stored result

[data/research/sp1_short_pressure.json](https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/data/research/sp1_short_pressure.json)

**Read:** complete. **Classification:** STORED_RESULT.
**Commit:** `79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f`.
**Returned blob:** `e8592f58d775e74e2f31bfd7b995258bda88e414`.

NULL promotion verdict; branch tests uninterpretable after H0 failure; explicit current-universe bias; actual entry window ends May 12, 2026.

### R10 — PSS-CD1 separate construction

[engine/personality_crowding_hazard.py](https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/engine/personality_crowding_hazard.py)

**Read:** 1–75. **Classification:** OBSERVED_SOURCE.
**Commit:** `79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f`.
**Returned blob:** `b5a7f048f670c85e97a0b957b5da4f41fc73c71f`.

Prospective correlation/dispersion lane, frozen construction hashes and its own maturity thresholds; not C11 authority.

### R11 — Historical-leaver sector coverage

[data/breadth/_sp1500_pit_sectors_coverage.json](https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/data/breadth/_sp1500_pit_sectors_coverage.json)

**Read:** complete. **Classification:** OBSERVED_SOURCE.
**Commit:** `79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f`.
**Returned blob:** `4fc4b782974d9c315dd7f3803bc7383c2204172d`.

Generated October 4; 1,083 leavers, 281 labeled via CIK, 802 unlabeled; zero era-correct labels.

### R12 — Portfolio V3 architecture

[docs/superpowers/specs/2026-09-15-mastermind-portfolio-v3-risk-first-autonomous-manager-design.md](https://github.com/mastermindx-market-intelligence/Mastermind/blob/521720b09be2921e996d9396b522b1c4ca62041c/docs/superpowers/specs/2026-09-15-mastermind-portfolio-v3-risk-first-autonomous-manager-design.md)

**Read:** 1–140. **Classification:** OBSERVED_SOURCE.
**Commit:** `521720b09be2921e996d9396b522b1c4ca62041c`.
**Returned blob:** `d700d50d62c9ee585aafb9737e3a35e7734e42e4`.

Inspected specification explicitly architecture-approved, SPEC_ONLY, records-only, production-inert; not proof of runtime capability.

### R13 — Mastermind decision lenses

[portfolio/lenses.py](https://github.com/mastermindx-market-intelligence/Mastermind/blob/521720b09be2921e996d9396b522b1c4ca62041c/portfolio/lenses.py)

**Read:** 1–100. **Classification:** OBSERVED_SOURCE.
**Commit:** `521720b09be2921e996d9396b522b1c4ca62041c`.
**Returned blob:** `2b8f593991d963de3d5d5d97c5970c36115cc411`.

Existing lens composition distinguishes context and authority-bearing inputs; source comments do not independently prove empirical claims.

### R14 — Static Mastermind census

[data/census/CENSUS.md](https://github.com/mastermindx-market-intelligence/Mastermind/blob/521720b09be2921e996d9396b522b1c4ca62041c/data/census/CENSUS.md)

**Read:** 1–38. **Classification:** OBSERVED_SOURCE.
**Commit:** `521720b09be2921e996d9396b522b1c4ca62041c`.
**Returned blob:** `dcf51d160ba9b470c91309b2dc19cf2d0048b458`.

Generated July 16, 2026; stale inventory, not October runtime certification.

### R15 — Current protected procedure and authority basis

Mastermind pin: `521720b09be2921e996d9396b522b1c4ca62041c`. Read INDEX, COLD_START, ACTIVE_EXECUTION and SESSION_RELIABILITY, plus the task-specific research, delivery, authority and review procedures below. Broad procedure reads may have bounded/truncated outputs; no claim of a full-text estate review is made.

- [docs/sol_skills/INDEX.md](https://github.com/mastermindx-market-intelligence/Mastermind/blob/521720b09be2921e996d9396b522b1c4ca62041c/docs/sol_skills/INDEX.md)
- [docs/sol_skills/COLD_START.md](https://github.com/mastermindx-market-intelligence/Mastermind/blob/521720b09be2921e996d9396b522b1c4ca62041c/docs/sol_skills/COLD_START.md)
- [docs/sol_skills/ACTIVE_EXECUTION.md](https://github.com/mastermindx-market-intelligence/Mastermind/blob/521720b09be2921e996d9396b522b1c4ca62041c/docs/sol_skills/ACTIVE_EXECUTION.md)
- [docs/sol_skills/SESSION_RELIABILITY.md](https://github.com/mastermindx-market-intelligence/Mastermind/blob/521720b09be2921e996d9396b522b1c4ca62041c/docs/sol_skills/SESSION_RELIABILITY.md)
- [plugins/mastermind-sol/skills/mastermind-deep-research/SKILL.md](https://github.com/mastermindx-market-intelligence/Mastermind/blob/521720b09be2921e996d9396b522b1c4ca62041c/plugins/mastermind-sol/skills/mastermind-deep-research/SKILL.md)
- [plugins/mastermind-sol/references/authority-boundaries.md](https://github.com/mastermindx-market-intelligence/Mastermind/blob/521720b09be2921e996d9396b522b1c4ca62041c/plugins/mastermind-sol/references/authority-boundaries.md)
- [docs/DELIVERY_WORKFLOW.md](https://github.com/mastermindx-market-intelligence/Mastermind/blob/521720b09be2921e996d9396b522b1c4ca62041c/docs/DELIVERY_WORKFLOW.md)
- [docs/sol_skills/REVIEW_RETURN.md](https://github.com/mastermindx-market-intelligence/Mastermind/blob/521720b09be2921e996d9396b522b1c4ca62041c/docs/sol_skills/REVIEW_RETURN.md)

Source law distinguishes GitHub code/review evidence from runtime-owner receipts. Research permission does not authorize production behavior or a second control plane.

### R16 — Repository identity, drift and publication-placement checks

- [Mastermind audit commit](https://github.com/mastermindx-market-intelligence/Mastermind/commit/521720b09be2921e996d9396b522b1c4ca62041c) — default `master`; protected flag observed true.
- [Macro audit commit](https://github.com/mastermindx-market-intelligence/macro/commit/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f) — default `main`; protected flag observed false.
- [Macro original-report-to-audit comparison](https://github.com/mastermindx-market-intelligence/macro/compare/d2904d45fb2bbaf12d3dae4a35eacaaefcc8bad3...79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f) — one commit ahead; four THS/CI/test paths; inspected crowding paths not changed by this delta.
- [Terminal pin](https://github.com/mastermindx-market-intelligence/mastermind-terminal/commit/1c708450187755160e1a5889b69598a2fcb1f0d1) — repository identity/source pin only.
- Research Vault: `mastermindx-market-intelligence/executive-dr-vault@ea422c92bd29800d1f7fb3ae850236cc44d8c890`, private; identity/tree metadata inspected, private content not reproduced.
- Exact Commission 11 searches in Mastermind and Macro did not identify an existing report file. Broader PR searches found adjacent work, not a proven C11 carrier.
- Macro #7173 was verified to concern signal-alert authority, not this commission; it is not reused or modified.
- Macro #8403 was observed merged at `acce37e8bf77970374c16237aed666b510e6ea8c`; the actual coverage limitations are recorded in R11.

### R17 — Prophet Cell E adjacent proposal, not accepted production truth

[Macro PR #6264](https://github.com/mastermindx-market-intelligence/macro/pull/6264) was observed **open/draft**, with head `5d6fd20e5716258f4d6aa93811561a3a6463360c` and branch `sol/prophet-flagship-fanout-hardening-20260822`. The read was PR metadata/body, not a fresh line-by-line audit of the entire draft.

Its body describes Cell E/MAS-121 fragility/positioning/coverage separation and a launch handoff. A fetch of that handoff on current `main` returned 404. Older SHAs quoted in the PR body do not replace the current head identity. Reconcile with this proposal; do not present it as deployed or merged.

### Publication-base compatibility recheck

Macro `main` advanced after the audit to `59a0789c0e5ffcce15e682b6f3880f3eacc6f6fc`. The [bounded comparison](https://github.com/mastermindx-market-intelligence/macro/compare/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f...59a0789c0e5ffcce15e682b6f3880f3eacc6f6fc) showed one records-only commit modifying `agentos/handoffs/TREND-PERSISTENCE-2026-10-04.md` and `agentos/workstreams/WS-TREND-PERSISTENCE.md`. No inspected C11 producer/consumer/schema changed. Publication uses the newer base while preserving the source audit pin and limits. The protected CLOSEOUT procedure was also read at the Mastermind audit pin.

## Primary public evidence and capability boundaries

Vendor entries below are first-party descriptions. No pricing quote, signed license, delivered original-vintage sample or API/bulk benchmark was obtained. Academic findings were examined at the stated depth; this audit does not claim to have replicated those studies.

### P1 — FINRA short-interest reporting schedule and semantics

[FINRA short-interest reporting schedule and semantics](https://www.finra.org/filing-reporting/regulatory-filing-systems/short-interest)

Official schedule read; September 30 settlement is published October 9, not on the October 2 reporting deadline.
Companion primary explanation: [FINRA short-interest semantics](https://syndication.finra.org/content/short-interest-what-it-what-it-not).

### P2 — FINRA Daily Short Sale Volume Files

[FINRA Daily Short Sale Volume Files](https://www.finra.org/finra-data/browse-catalog/short-sale-volume-data/daily-short-sale-volume-files)

Official source scope, evening release and subsequent corrections; consolidated NMS history begins August 1, 2018.

### P3 — FINRA file-format specification

[FINRA file-format specification](https://www.finra.org/sites/default/files/2021-07/DailyShortSaleVolumeFileLayout.pdf)

Official two-page PDF; page 1 table visually checked. ShortVolume includes exempt trades; exempt is a subset. Footer/count and facility fields specified.

### P4 — IBKR short-securities availability

[IBKR short-securities availability](https://www.interactivebrokers.com/en/trading/short-securities-availability.php)

Official product description; indicative availability/rates and historical indicative rate tools. No authenticated historical download or entitlement was tested.

### P5 — SEC Form 13F FAQ

[SEC Form 13F FAQ](https://www.sec.gov/rules-regulations/staff-guidance/frequently-asked-questions-about-form-13f)

Official staff guidance updated March 6, 2026; holdings and short-position distinction, identifiers and 2023 dollar-unit change. Not a new legal opinion.

### P6 — SEC exemptive order, December 2025

[SEC exemptive order, December 2025](https://www.govinfo.gov/content/pkg/FR-2025-12-08/pdf/2025-22158.pdf)

Official order; Form SHO January 2, 2028; loan reporting September 28, 2028 and dissemination March 29, 2029. Page 2 visually reviewed.

### P7 — FINRA SLATE current implementation page

[FINRA SLATE current implementation page](https://www.finra.org/filing-reporting/slate)

Official current schedule corroboration; launch and future onboarding/testing information, not a current production loan dataset.

### P8 — SEC September 30, 2026 notice

[SEC September 30, 2026 notice](https://www.govinfo.gov/content/pkg/FR-2026-09-30/pdf/2026-20056.pdf)

Recent official corroboration of deferred securities-loan reporting and public dissemination.

### P9 — SEC final Rule 10c-1a, Release 34-98737

[SEC final Rule 10c-1a, Release 34-98737](https://www.sec.gov/files/rules/final/2023/34-98737.pdf)

Official final-rule text; printed pp. 124–125 on removed available-to-lend requirement; pp. 148–149 and final rule on differentiated dissemination delays. Original compliance dates are superseded by P6–P8.

### P10 — DataLend product description

[DataLend product description](https://datalend.com/services/datalend/)

PROVIDER_CLAIM: raw lending quantities, rates and historical products. No delivered sample or contractual vintage history independently tested.

### P11 — DataLend API description

[DataLend API description](https://datalend.com/services/datalend-api/)

PROVIDER_CLAIM: REST/API/history and reflected amendments. This does not by itself prove original-vintage retrieval.

### P12 — S&P Global Securities Finance

[S&P Global Securities Finance](https://www.spglobal.com/market-intelligence/en/solutions/products/securities-finance)

PROVIDER_CLAIM: supply/demand/fees, broad population and multi-decade PIT history. Descriptive history counts vary across page sections; exact field/version contract remains unverified.

### P13 — FIS Securities Finance Market Data

[FIS Securities Finance Market Data](https://www.fisglobal.com/products/fis-securities-finance-market-data)

PROVIDER_CLAIM: global/intraday lending analytics. Exact original-vintage depth, API schema, corrections and terms not established.

### P14 — S3 Partners product descriptions

[S3 Partners product descriptions](https://www.s3partners.com/)

PROVIDER_CLAIM: proprietary short estimates, crowding/lending analytics and delivery products. Estimated SI is not regulatory SI.

### P15 — S3 market-structure/product methodology description

[S3 market-structure/product methodology description](https://www.s3partners.com/articles/market-structure-sentiment-portfolio-impact)

PROVIDER_CLAIM: history, intraday lending measures and derived analytics. Methodology/version and float-denominator comparability require diligence.

### P16 — Cohen, Diether and Malloy, Supply and Demand Shifts in the Shorting Market (2007)

[Cohen, Diether and Malloy, Supply and Demand Shifts in the Shorting Market (2007)](https://onlinelibrary.wiley.com/doi/10.1111/j.1540-6261.2007.01269.x)

Original research, abstract-level evidence reviewed; supports joint supply/demand reasoning, not Mastermind effect-size replication.

### P17 — Saffi and Sigurdsson, Price Efficiency and Short Selling (2011)

[Saffi and Sigurdsson, Price Efficiency and Short Selling (2011)](https://academic.oup.com/rfs/article-abstract/24/3/821/1590469)

Original research abstract reviewed; historical international constraints/efficiency evidence. DOI 10.1093/rfs/hhq124.

### P18 — Hong, Li, Ni, Scheinkman and Yan, Days to Cover and Stock Returns (2015 working paper)

[Hong, Li, Ni, Scheinkman and Yan, Days to Cover and Stock Returns (2015 working paper)](https://www.nber.org/papers/w21166)

Original working-paper abstract reviewed; DTC mechanism and historical result, not evidence of current product alpha.

### P19 — Muravyev, Pearson and Pollet, borrowing costs and anomaly returns (2025)

[Muravyev, Pearson and Pollet, borrowing costs and anomaly returns (2025)](https://onlinelibrary.wiley.com/doi/abs/10.1111/jofi.13501)

Original research abstract reviewed; financing-cost warning for tested anomalies. Do not universalize the sample result.

### P20 — Muravyev, Pearson and Pollet, Why does options market information predict stock returns? (2025)

[Muravyev, Pearson and Pollet, Why does options market information predict stock returns? (2025)](https://doi.org/10.1016/j.jfineco.2025.104153)

Original research text/abstract evidence reviewed; borrow-cost overlap for specific option signals, not all options/GEX measures.

### P21 — SEC fails-to-deliver data

[SEC fails-to-deliver data](https://www.sec.gov/data-research/sec-markets-data/fails-deliver-data)

Official download/caveat page; aggregate outstanding settlement failures, delayed release, not proof of naked shorts. No C11 incremental-value test conducted.

### P22 — SEC Investor.gov, Updated Investor Bulletin: ETFs

[SEC Investor.gov, Updated Investor Bulletin: ETFs](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-24)

Official explanation of creation/redemption baskets and cash equivalents; supports distinction between ETF redemption and an observed stock sale.

## Adversarial audit and disposition

Severity is relative to the proposed historical use or consumer contract, not an assertion of a production incident. “Addressed” below means the recommendation was corrected; it does not mean source code was repaired.

| ID | Severity | Finding | Corrected recommendation / remaining gate | Evidence |
|---|---|---|---|---|
| A01 | Critical | Publication clock conflated with actual system knowledge | Two explicit replay modes; actual receipt/validation required for system replay | REPORT E; R1–R6 |
| A02 | Critical | As-restated SI could be treated as original PIT after a lag | Qualification tiers; no retroactive admission without original-generation proof | R6–R7 |
| A03 | High | Economic effective interval conflated with knowledge validity | Separate economic and transaction-time intervals and generation lineage | REPORT E |
| A04 | Critical | Ownership FINRA ADV gates on settlement, not publication | Owner-specific regression case and later bounded repair gate | R5 |
| A05 | High | Daily short-volume never-revised assertion is false | Capture original and updated generations; preserve facility scope | R1–R2; P2 |
| A06 | High | Exempt volume interpretation could double count | Exempt is included in short total; subset validation; no invented zero | P3; R2 |
| A07 | High | IBKR date file is not an immutable intraday sequence | Every distinct snapshot retained with local receipt clocks | R3 |
| A08 | High | IBKR lower bound mislabeled unlimited | Censored interval, not infinity or exact ten million | R3 |
| A09 | High | Identifier fields lost; ticker reuse risk | Retain raw identifiers and canonical effective-dated listing resolution | R3 |
| A10 | High | Out-of-universe retention depends on fee predictor | Full lawful capture or inclusion manifest and stable-cohort estimand | R3 |
| A11 | High | Whole frozen panel can appear internally fresh | Decision-clock freshness and expected source release, independent of panel maximum | R4 |
| A12 | High | Missing ADV column contradicts promised thinness guard | Fail closed in contract tests; static defect, not runtime incident claim | R4 |
| A13 | High | Recent source pin confused with fresh data | August SI sidecar and July census visibly stale; demand current artifact receipt | R7; R14 |
| A14 | High | New leaver-sector substrate overstated as historical repair | Zero era-correct labels; no delisting-return proof; limited reuse only | R11 |
| A15 | High | SP1 null overinterpreted or mined for a squeeze effect | Preserve null authority and uncertainty; exact reproduction before amendments | R8–R9 |
| A16 | High | Future regulation assumed to solve utilization | Available-to-lend requirement removed; qualify actual future schema | P6–P9 |
| A17 | Medium | No IBKR history asserted too broadly | Live endpoint is forward capture; separate historical indicative tool exists but unqualified | P4; R3 |
| A18 | High | Draft Cell E or stale PR body presented as canonical state | Current PR head and draft status recorded; do not inherit unapproved authority | R17 |
| A19 | High | All existing consumers presumed display-only | Enumerate actual factor/lens consumers; new adapter cannot silently change authority | R1; R13 |
| A20 | High | Original first implementation commission too broad | Capture-only F1; historical feasibility, features, evaluation and promotion split | REPORT K–L |
| A21 | Medium | Perfect historical panel blocks irreversible future capture | F1 and F2 parallel after rights/owner admission | REPORT J–K |
| A22 | High | Same-sample vendor alpha and incomparable support | Matched support, prior-access record and paired incremental tests | REPORT H |
| A23 | Medium | Paid data rejected unless public alpha first succeeds | Separate quality/coverage, risk and alpha value cases; separate spending approval | REPORT D/J |
| A24 | High | Avoiding names assumed to be economically free | Explicit replacement/cash/exposure and opportunity-cost counterfactual | REPORT H |
| A25 | High | Unbounded horizons/features create researcher degrees of freedom | Eight public confirmatory tests; two optional commercial tests; exploratory variants cannot promote | REPORT H |
| A26 | High | Missing supply or OI can masquerade as low risk | Unavailable/partial separate from measured zero; no unearned aggregate hazard grade | REPORT E–F |
| A27 | Medium | ETF redemptions or FTD balances mistaken for forced short flow | Mechanism-specific scenarios; no additive daily FTD flow or deterministic stock sale | P21–P22 |
| A28 | High | Vendor PIT marketing accepted as original-vintage proof | Correction examples, original-version endpoints, rights and population checks | P10–P15 |

## What remains genuinely unverified

No current runtime certification; no full private-Vault semantic search; no complete Macro tree census; no authenticated historical IBKR extraction; no commercial source sample or price; no rights clearance; no original-vintage FINRA reconstruction; no delisting-inclusive return panel; no new outcome run; no SP1 reproduction; no current hidden consumer guarantee. Each is either outside this research commission or a specifically named later gate. The hardening pass does not silently fill these gaps with general knowledge.

## Source-use verification

Internal conclusions use the pinned code, stored receipts and current PR metadata listed above. Public factual corrections use the official regulator/provider sources. Architecture, formulas, risk gates and experiment budgets are labeled proposed reasoning rather than observed performance. A failed source lookup was not used as evidence for a stronger claim. No third-party regulatory summary supersedes the current SEC/FINRA primary schedule.
