# Commission 13 — source and evidence ledger

Research observation date: **2026-10-04**. This ledger distinguishes repository evidence, issuer/regulatory evidence, published research, and commercial product descriptions. A product page is not a tested feed, a historical catalogue date is not an as-was archive, and a PR description is not an independently reproduced test result.

The accompanying [masterplan](MASTERPLAN.md), [audit](AUDIT_AND_RECENSUS.md), and [validation specification](VALIDATION.md) use the identifiers below. Source links are durable repository revisions or identifiable primary publications, not citations dependent on a previous chat session. No proprietary dataset, licensed sample, vendor dictionary, or private Research Vault content is reproduced.

## Repository evidence

<a id="R01"></a>
### R01 — Current source law and identity

Mastermind protected `master` was resolved to **521720b09be2921e996d9396b522b1c4ca62041c**. The same-revision bootstrap was consumed, including [INDEX](https://github.com/mastermindx-market-intelligence/Mastermind/blob/521720b09be2921e996d9396b522b1c4ca62041c/docs/sol_skills/INDEX.md), [COLD_START](https://github.com/mastermindx-market-intelligence/Mastermind/blob/521720b09be2921e996d9396b522b1c4ca62041c/docs/sol_skills/COLD_START.md), [ACTIVE_EXECUTION](https://github.com/mastermindx-market-intelligence/Mastermind/blob/521720b09be2921e996d9396b522b1c4ca62041c/docs/sol_skills/ACTIVE_EXECUTION.md), [SESSION_RELIABILITY](https://github.com/mastermindx-market-intelligence/Mastermind/blob/521720b09be2921e996d9396b522b1c4ca62041c/docs/sol_skills/SESSION_RELIABILITY.md), [REVIEW_RETURN](https://github.com/mastermindx-market-intelligence/Mastermind/blob/521720b09be2921e996d9396b522b1c4ca62041c/docs/sol_skills/REVIEW_RETURN.md), and [CLOSEOUT](https://github.com/mastermindx-market-intelligence/Mastermind/blob/521720b09be2921e996d9396b522b1c4ca62041c/docs/sol_skills/CLOSEOUT.md).

Read depth: same-pin procedure texts. Their authority is not replaced by this research. In particular, a proposed feature, a merged change, recorded historical production proof, and current live service proof are separate claims.

<a id="R02"></a>
### R02 — Incumbent capital-structure workstream and gates

[WS-CAPITAL-STRUCTURE-INTELLIGENCE-V2.md at macro 79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f](https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/agentos/workstreams/WS-CAPITAL-STRUCTURE-INTELLIGENCE-V2.md).

Read depth: complete 229-line workstream. Blob: `290485d93c825fecaff3dc701237d6e52b31ef80`; SHA-256 of retrieved source bytes: `de32082a6a0135bd59a58cfd7e9b5887384822195dbb84d272d8a81bc4fa980a`.

Controlling findings: owner `coo-fable`, program `capital-structure-intelligence`; W2C/W2D merged but recorded `BUILT_NOT_PROVEN`; W3/W4 held behind W2; W6 contains share basis/corporate actions/cash/funding and depends on W4. Company Facts/share-count v2 remain described as default-off/unprovisioned. Recorded W1/W2A/W2B natural proofs are historical receipts, not a new October runtime certification. Do not manufacture a scheduled proof run or silently claim `company_event.v1`.

<a id="R03"></a>
### R03 — Existing capital-structure contracts and publication boundary

[Capital Structure contract](https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/docs/CAPITAL_STRUCTURE_INTELLIGENCE_CONTRACT.md), [event schema](https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/contracts/capital_structure_event.schema.json), and [projection schema](https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/contracts/capital_structure_projection.schema.json).

Read depth: source bytes collected at the audit pin; relevant contract/interface evidence combined with R02/R04/R05. Source-byte SHA-256 values respectively: `eca06010c66b8a28491c8c03509c420dff8dceca4ac90990720339234dddd714`, `db4a7bf377bfa78f5a93b5e79e788c78282a47b8a8b401fbb8cb6cf3ff7c1c5c`, `60d49203d80bc180d1e062062593a986cc855ae50d1507e25a2e737817347ff5`. Collection is not a claim that every line or invariant was re-audited.

<a id="R04"></a>
### R04 — Existing direct share-count observation contract

[capital_structure_share_count_observation.schema.json](https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/contracts/capital_structure_share_count_observation.schema.json) and [v2 schema](https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/contracts/capital_structure_share_count_observation_v2.schema.json).

Read depth: v1 lines 1–145 inspected directly; complete v1/v2 bytes collected. V1 blob: `8fc7bd1ca3fc453bb18a4739ecd626ed9c2608d0`. The schema already has immutable observation/slot/revision identity, direct fact provenance, ambiguity states, explicit unit and class semantics, acquisition clocks, corrections, and authority exclusions. It does not establish a selected security-specific current denominator. This is the contract to extend or adapt under its owner, not a reason to mint a parallel share-count truth store.

<a id="R05"></a>
### R05 — Projection capability withholding

[engine/capital_structure/projection.py](https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/engine/capital_structure/projection.py).

Read depth: complete bytes collected; capability/authority declarations inspected. SHA-256: `4528c304de27349c2f1d3ff2689804f367cd11411806609b0b651442e2e5f3c0`. The observed declarations include unavailable fully diluted shares and remaining capacity, with rank/sizing/entry/Prophet authority false. R09 independently describes the same withheld producer capabilities from an adjacent consumer. No served response was tested in this commission.

<a id="R06"></a>
### R06 — Mastermind held-risk consumer

[portfolio/held_risk.py](https://github.com/mastermindx-market-intelligence/Mastermind/blob/521720b09be2921e996d9396b522b1c4ca62041c/portfolio/held_risk.py#L1-L145).

Read depth: lines 1–145. Blob: `4ec5eb6047848d46b0d780dfdf9f3967fd0d1796`. The module describes deterministic lane composition, a missing `dilution_events.parquet` sub-check, and legacy financial proxies. Its documented `ni/debt_lt` interest-coverage proxy must not be relabeled as true EBIT/interest coverage. This research does not change the consumer or its live policy.

<a id="R07"></a>
### R07 — Mastermind existing fundamentals and missingness assumption

[loop/fundamentals.py](https://github.com/mastermindx-market-intelligence/Mastermind/blob/521720b09be2921e996d9396b522b1c4ca62041c/loop/fundamentals.py#L1-L150).

Read depth: lines 1–150. Blob: `b8ede9c1dc3d5c9adca9100a47a07db2c382267b`. The loader selects `asof_date <= t`; valuation uses price times last-reported shares. `_zero_if_missing` and the shareholder-yield branch convert missing dividends/repurchases to zero. This is an observed legacy assumption, not evidence that omitted issuer disclosures represent true zero activity. Existing factor experiments and holdouts must not be silently rerun or relabeled.

<a id="R08"></a>
### R08 — Static census age

[data/census/CENSUS.md](https://github.com/mastermindx-market-intelligence/Mastermind/blob/521720b09be2921e996d9396b522b1c4ca62041c/data/census/CENSUS.md#L1-L60).

Read depth: first 60 lines. Blob: `dcf51d160ba9b470c91309b2dc19cf2d0048b458`. Its generated timestamp remains `2026-07-16T23:46:57.358909+00:00`, with embedded Git reference `131290a`. Job counts, flags and endpoint counts inside it are therefore a dated inventory, not an October environment inspection. No generated census was edited or regenerated in this commission.

<a id="R09"></a>
### R09 — Adjacent original-equity/funding program

[macro PR #8308](https://github.com/mastermindx-market-intelligence/macro/pull/8308), read as **OPEN / DRAFT / not merged**, head **446ffd0f1062dd064c0716b576ceba7ce90acf2b**.

Read depth: current PR metadata and complete description, not a rerun of its tests. It proposes `engine/prophet_cycle_equity.py`, consumes `capital_need.v1` and existing share truth, couples financing proceeds with new claims, and distinguishes business recovery from original-shareholder recovery. Its declared status is `BUILT_NOT_PROVEN / MISSION_COMPLETE:false`. The reported 292-test battery is an author receipt, not this commission's independently reproduced result. Avoid a competing recovery or financing-probability owner.

<a id="R10"></a>
### R10 — Adjacent existing source and calculation owners

At the macro audit pin: [capital_allocation.py](https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/engine/capital_allocation.py), [capital_need.py](https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/engine/capital_need.py), [cash_runway.py](https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/engine/cash_runway.py), [debt_maturity.py](https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/engine/debt_maturity.py), [registration_lifecycle.py](https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/engine/capital_structure/registration_lifecycle.py), and [biocatalyst_pit_adapter.py](https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/engine/capital_structure/biocatalyst_pit_adapter.py).

Read depth: complete source bytes collected; selected declarations/signatures inspected. Source existence and source-level exclusions do not prove live population or complete semantic correctness. The report uses these as reuse boundaries, not as freshly certified services. The allocation code explicitly treats missing SBC as unavailable; its cash-expense-adjusted repurchase measure is not a literal count of net shares issued.

<a id="R11"></a>
### R11 — Existing architecture and share-count handoffs

[Capital Structure V2 masterplan](https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/research/CAPITAL_STRUCTURE_INTELLIGENCE_V2_MASTERPLAN_2026-08-18.md), [issuer-state W3 docket](https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/research/CAPITAL_STRUCTURE_ISSUER_STATE_W3_BUILD_DOCKET.md), [share-count truth handoff](https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/research/CAPITAL_STRUCTURE_SHARE_COUNT_TRUTH_FABLE_HANDOFF.md), and [R2 conformance handoff](https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/research/CAPITAL_STRUCTURE_SHARE_COUNT_R2_CONFORMANCE_HANDOFF.md).

Read depth: pinned source collection and relevant boundary excerpts; R02 controls current phase status. The historical W3 docket's title must not be confused with the later V2 workstream's W3 UX phase. Existing architecture already owns registration, instruments, share basis, corporate actions, cash, and funding. This commission is a hardening supplement, not a successor program.

<a id="R12"></a>
### R12 — Repository movement and census method

[macro comparison from original report pin to audit pin](https://github.com/mastermindx-market-intelligence/macro/compare/d2904d45fb2bbaf12d3dae4a35eacaaefcc8bad3...79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f).

The comparison returned one additional commit and four changed paths: `.github/ci/legacy-jobs.yml`, `collectors/china_ths_concepts.py`, `tests/test_ci_pack.py`, and `tests/test_ths_collection_receipts.py`. None is a capital-structure implementation path. The root recursive macro tree was truncated; the audit therefore fetched complete relevant subtrees separately. Counts and scope limits are recorded in AUDIT_AND_RECENSUS.md. No claim of all-branch, all-runtime or private-Vault content completeness is made.

## Regulatory, issuer and data-provider primary sources

<a id="S01"></a>
### S01 — SEC EDGAR API documentation

[SEC EDGAR application programming interfaces](https://www.sec.gov/search-filings/edgar-application-programming-interfaces). Official documentation inspected. It describes submissions/XBRL APIs and nightly bulk delivery. The XBRL API covers non-custom taxonomy facts applying to the entire entity; class-dimensional and custom-tag extraction can require original filings. Latest/frame endpoints do not by themselves establish historical as-was vintages. Typical processing descriptions are not a contractual end-to-end Mastermind latency SLA.

<a id="S02"></a>
### S02 — Repurchase-rule vacatur and restored disclosure basis

[SEC further announcement, February 9, 2024](https://www.sec.gov/newsroom/whats-new/further-announcement-regarding-share-repurchase-disclosure-modernization-rule). Official text inspected. It reports the December 19, 2023 vacatur and reversion to pre-amendment requirements. The commission does not assume a continuing daily public execution series from the vacated 2023 rule. Legal requirements must be checked again before implementation; this is data-design research, not a legal opinion.

<a id="S03"></a>
### S03 — Item 703 actual disclosure structure

[SEC pre-amendment Item 703](https://www.sec.gov/files/corpfin/pre-amendment-item-703.pdf). Both pages visually inspected, including the table. Monthly period totals, average price, purchases under announced plans, remaining authorization and plan footnotes are distinct fields. The disclosure includes purchases outside announced plans. These fields should not be treated as mutually additive event series.

<a id="S04"></a>
### S04 — Form 10-K cover: monetary public float versus class shares

[SEC Form 10-K](https://www.sec.gov/files/form10-k.pdf), printed page 10 / PDF page index 9, visually inspected. It separately requests the aggregate market value of common equity held by non-affiliates at the specified second-quarter date, and shares outstanding for each common-stock class at the latest practicable date. These differ in unit, population and date. This supports the dimensional guard against treating SEC public-float dollars as current freely tradable share count.

<a id="I01"></a>
### I01 — Filed ASR accounting and delivered shares

[Issuer CIK 1099800, accession 0001099800-24-000078, equity note R17](https://www.sec.gov/Archives/edgar/data/1099800/000109980024000078/R17.htm). Filing note inspected. Its ASRs distinguish initial shares acquired into treasury from the remaining forward-contract component. Initial share delivery affects weighted-average shares; final settlement is a separate step. Reported rounded quantities are not exact-share arithmetic or a historical availability receipt.

<a id="I02"></a>
### I02 — Actual purchases versus cash settlement

[Issuer CIK 39899, accession 0000950170-24-055643, note R19](https://www.sec.gov/Archives/edgar/data/39899/000095017024055643/R19.htm). Filing excerpt inspected. It distinguishes ASR initial/final deliveries and reports repurchased shares including amounts unpaid at quarter end. This is a concrete reason to keep share acquisition, aggregate disclosure and cash settlement legs separate; they cannot all be added as independent buybacks.

<a id="I03"></a>
### I03 — Convertible legal settlement alternatives

[Issuer CIK 1015820, 2021 Q3 Form 6-K](https://www.sec.gov/Archives/edgar/data/1015820/000101582021000054/a2021q36-k.htm) and [issuer CIK 812011, ASU adoption note](https://www.sec.gov/Archives/edgar/data/812011/000081201123000017/R8.htm). Primary filing excerpts inspected. Cash-principal/net-share settlement and cash-only convertibles demonstrate why principal divided by conversion price is not a universal actual-share or diluted-EPS formula. These are historical issuer policies, not substitutes for a current accounting-standard opinion.

<a id="I04"></a>
### I04 — Accounting adoption can revise comparative periods

[Issuer CIK 33213, accession 0000033213-22-000015, note R20](https://www.sec.gov/Archives/edgar/data/33213/000003321322000015/R20.htm). Filing excerpt inspected. The note presents retrospective ASU 2020-06 adjustments to previously reported results. A later comparative column must not overwrite what was available earlier. This is an accounting-version example, not evidence of a data-vendor correction service.

<a id="S05"></a>
### S05 — DTCC CA 20022

[DTCC service description](https://www.dtcc.com/products-and-services/data-services/corporate-actions-reference-data/ca-20022-service) and [DTCC Learning service/documentation page](https://dtcclearning.com/products-and-services/dtcc-data-services/ca-20022-service.html). Official descriptions and documentation listings inspected. Lifecycle messages and CAID are relevant to operational reconciliation. Sample-message/schema listings were visible, but licensed sample bytes and contractual historical-vintage behavior were not tested. Near-real-time operations do not by themselves establish historical research PIT.

<a id="S06"></a>
### S06 — NYSE Market Event Feed

[NYSE Market Event Feed](https://www.nyse.com/market-data/corporate-actions/market-event-feed). Official product description inspected. It advertises real-time and historical API access. Exact event-revision retention, earliest field-specific history, deletion semantics and redistribution rights remain unverified. Best candidate role: operational dates/status reconciliation, not replacement of filed economic terms.

<a id="S07"></a>
### S07 — Nasdaq Daily List: do not overstate historical depth

[Current Daily List product page](https://nasdaqtrader.com/Trader.aspx?id=DailyListPD) and [historical 2011 technical notice](https://www.nasdaqtrader.com/TraderNews.aspx?id=dtn2011-017). The current page describes history back to **1999**, whereas the older notice specifies December 7, 1998 for corporate actions and later starts for other files. Use current product scope for planning; obtain the exact archive manifest instead of presenting 1998 as universally verified current coverage. CUSIP and non-CUSIP versions exist; intended rights still need agreement review.

<a id="S08"></a>
### S08 — S&P Managed Corporate Actions: explicit PIT limitation

[S&P Global Marketplace MCA catalogue](https://www.marketplace.spglobal.com/en/datasets/managed-corporate-actions-mca-%281666897737%29). Official indexed catalogue content inspected. It lists history initiated in 2003, significant coverage from 2010, intraday delivery, and **“Point In Time: No.”** This is negative evidence against assuming this package is an as-was research archive. Operational golden-copy/lifecycle marketing does not cure that limitation. A distinct licensed vintage product could qualify later, but must be demonstrated rather than inferred.

<a id="S09"></a>
### S09 — LSEG corporate-actions catalogue

[LSEG corporate actions](https://www.lseg.com/en/data-catalogue/corporate-actions). Official product description inspected. It describes broad international event coverage, multiple delivery routes and some history extending to the early 1970s. Earliest coverage is not universal by field, exchange or event family. Latency varies by region/product. Historical as-was revisions, deletion handling and precise rights remain diligence questions.

<a id="S10"></a>
### S10 — Bloomberg: separate products, separate PIT claims

[Bloomberg Data License](https://professional.bloomberg.com/products/data/data-license/) and [Company Financials enterprise catalogue](https://professional.bloomberg.com/products/data/enterprise-catalog/cofi/). Official product descriptions inspected. Data License describes corporate-action content and delivery mechanisms. PIT corporate-action-adjusted company financials in a different catalogue do not prove that a corporate-action event feed preserves every historical notice version. No entitlement, dictionary or feed sample was inspected.

<a id="S11"></a>
### S11 — FactSet: candidate, not verified event-vintage source

[FactSet Global Prices API catalogue](https://developer.factset.com/api-catalog/factset-global-prices-api). The page was located, but its relevant event schema could not be meaningfully inspected through the rendered response. Corporate-action revision history, historical coverage, latency and rights therefore remain **unknown**, not presumed equivalent to another provider. This source is included for transparent diligence coverage, not as support for specific capabilities.

<a id="S12"></a>
### S12 — CRSP and Compustat research role

[CRSP US stock databases](https://www.crsp.org/research__trashed/crsp-us-stock-databases/) and [CRSP/Compustat merged database](https://www.crsp.org/research__trashed/crsp-compustat-merged-database/). Official catalogue pages inspected. Security histories, permanent identifiers, delisting information and returns are relevant to survivorship-safe validation. The official site reports a June 30, 2026 content transition to Morningstar Indexes. Verify present product/entitlement at procurement; do not confuse historical identifier links or corporate-action-adjusted returns with an as-run event feed or unrevised fundamental vintages.

<a id="S13"></a>
### S13 — OpenFIGI identity mapping

[OpenFIGI API documentation](https://www.openfigi.com/api/documentation). Public official API documentation located during the source review. Use as an optional identity bridge only. Current mappings are not effective-dated issuer/class truth, not a substitute for internal identity, and not a corporate-action source. No historical mapping archive or vendor-identifier redistribution entitlement was established in this commission.

## Research literature: findings and review depth

<a id="A01"></a>
### A01 — Payout yield as the relevant baseline

Boudoukh, Michaely, Richardson and Roberts (2007), **On the Importance of Measuring Payout Yield: Implications for Empirical Asset Pricing**, Journal of Finance 62(2), 877–915. [Publisher article](https://onlinelibrary.wiley.com/doi/10.1111/j.1540-6261.2007.01226.x); [NBER working-paper record](https://www.nber.org/papers/w10651).

Review depth: publisher article text, including data/method discussion, not just an abstract. The paper distinguishes dividends, total payout and net payout including issuance, with historical sample/availability conventions. Its historical findings motivate a strong net-payout baseline; they do not establish incremental 2026 Mastermind alpha. No proprietary data, table or reported effect size is reproduced.

<a id="A02"></a>
### A02 — Issuance effects depend on sample and era

Pontiff and Woodgate (2008), **Share Issuance and Cross-sectional Returns**, Journal of Finance 63(2), 921–945. [Publisher](https://onlinelibrary.wiley.com/doi/10.1111/j.1540-6261.2008.01335.x).

Review depth: primary abstract and publication metadata; full methods were not retrieved. The abstract distinguishes post-1970 predictability from much weaker earlier evidence. Use this to motivate era/size/mechanism falsifiers, not a universal negative sign or imported expected-return coefficient.

<a id="A03"></a>
### A03 — Employee awards and EPS incentives

Bens, Nagar, Skinner and Wong (2003), **Employee stock options, EPS dilution, and stock repurchases**, Journal of Accounting and Economics. [Publisher](https://www.sciencedirect.com/science/article/pii/S0165410103000703).

Review depth: primary abstract/introduction. The paper studies repurchases, employee-option dilution and EPS incentives. It motivates separating accounting dilution incentives from actual employee-share issuance and testing alternative financing explanations. It is not a license to infer intent or misconduct from repurchase data.

<a id="A04"></a>
### A04 — Critical discussion of the EPS interpretation

Larcker (2003), **Discussion of “Employee stock options, EPS dilution, and stock repurchases”**, Journal of Accounting and Economics. [Publisher](https://www.sciencedirect.com/science/article/pii/S0165410103000715).

Review depth: primary abstract/introduction. The discussion challenges the target-choice and managerial-myopia interpretation and raises alternative explanations. The Mastermind feature should expose observations and competing hypotheses rather than declare that EPS-related repurchases destroy value.

<a id="A05"></a>
### A05 — Local causal evidence, not a universal repurchase verdict

Almeida, Fos and Kronlund (2016), **The real effects of share repurchases**, Journal of Financial Economics 119(1), 168–185. [DOI](https://doi.org/10.1016/j.jfineco.2015.08.008); [coauthor's explanation](https://corpgov.law.harvard.edu/2016/02/08/the-real-effects-of-share-repurchases/).

Review depth: primary coauthor explanation of the study; the publisher's full paper was not retrieved. The authors use an EPS-threshold discontinuity and discuss investment/employment changes as well as heterogeneous shareholder outcomes. The design's local comparison is not evidence that all repurchases harm investment or all earnings accretion is beneficial. Do not reproduce its causal claim with an uncontrolled event study.

<a id="A06"></a>
### A06 — Newer innovation evidence complicates simple narratives

Almeida, Fos, Hsu, Kronlund and Tseng (2025 issue; online 2024), **Innovation Under Pressure**, JFQA 60(5), 2088–2120. [Cambridge publisher](https://www.cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis/article/innovation-under-pressure/6B4F24CCDC40E1D4043674C47E869C97).

Review depth: primary abstract and publication metadata; full PDF was advertised but not successfully retrieved. The abstract reports improved innovation outcomes in an EPS-pressure regression-discontinuity framework, especially for previously innovation-efficient firms. This is a counterweight to blanket underinvestment narratives, not a live trading signal or a full methodological replication.

<a id="A07"></a>
### A07 — Financing and maturity heterogeneity

El Ghoul, Guedhami, Kim and Suh (2024 issue; online 2023), **The persistence and consequences of share repurchases**, Journal of Business Finance & Accounting 51(1–2), 431–472. [Publisher](https://onlinelibrary.wiley.com/doi/10.1111/jbfa.12699).

Review depth: primary abstract/metadata. Findings emphasize internal financing, persistence and financial maturity rather than general underinvestment. The publisher notes licensed underlying data. This motivates conditioning on funding source and maturity and forbids treating a repurchase announcement alone as independent information about capital discipline.

## Evidence grades and unresolved diligence

`SOURCE_OBSERVED` means the identified text/metadata was inspected, not that its claims were independently measured. `CODE_OBSERVED` means pinned code/contracts, not runtime truth. `REPORTED_PROOF` means an incumbent receipt was read. `PROPOSED` denotes this commission's design, thresholds or experiments. `UNVERIFIED` denotes a missing sample, agreement, runtime witness or accounting/legal determination.

No vendor API transaction, correction replay, entitlement inspection, procurement quote, historical outcome backtest or production publication test was performed. Those are explicit acceptance gates, not claims hidden behind a product name. Current source law takes precedence over this packet; later branch drift must be checked against the exact pins before construction.
