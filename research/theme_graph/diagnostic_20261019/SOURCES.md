# GMI diagnostic casebook — sources (2026-10-19, lane 7d)

One section per citation object used in `cases.jsonl` (as written, verbatim fields plus the case_ids that cite it). Access date for every entry: **2026-10-19**.

**Rights note (applies to all entries):** public regulatory filings, company IR pages, and repository files only. **No paid read; no HKEX scrape; no new vendor.** No network fetch was performed by this lane beyond nothing at all — the remote URLs below were inspected earlier by the orchestrator and are recorded here as citation objects; fetching was optional and none was needed for transcription.

**Repository-file citations** (`url_or_path` inside the repository) are **read-only internal evidence, not primary market sources**: they record what this repository's own config, code, research and Agent OS handoffs state, at the pinned revision `0221d6e171751c15b24d9f0bea27056aeab2716c` (origin/main at lane start). They never substitute for the issuer's primary disclosure.

---

### 1. NVIDIA FY2026 10-K segment note (primary)
- **source:** NVIDIA Corporation Form 10-K, fiscal year ended 25 January 2026 — Note: Segment Information (XBRL R25)
- **url_or_path:** https://www.sec.gov/Archives/edgar/data/1045810/000104581026000021/R25.htm
- **period:** FY2026 (12 months ended 2026-01-25)
- **locator:** Segment Information — concentration of revenue: one direct customer 22%, another direct customer 14% of total revenue, primarily Compute & Networking
- **language:** EN · **access date:** 2026-10-19
- **used by:** DX-01, DX-02, DX-03, DX-27

### 2. Walmart FY2027 Q2 earnings release (primary)
- **source:** Walmart Inc. earnings release, fiscal 2027 second quarter (Form 8-K exhibit)
- **url_or_path:** https://www.sec.gov/Archives/edgar/data/104169/000010416926000145/earningsreleasefy27q2.htm
- **period:** 13 weeks ended 2026-07-31
- **locator:** page 1 highlights, footnote 3: global advertising recorded in either net sales or as a reduction to cost of sales depending on the arrangement
- **language:** EN · **access date:** 2026-10-19
- **used by:** DX-04, DX-05

### 3. Cameco Westinghouse closing release (primary)
- **source:** Cameco news release: Cameco and Brookfield complete acquisition of Westinghouse Electric Company
- **url_or_path:** https://www.cameco.com/media/news/cameco-and-brookfield-complete-acquisition-of-westinghouse-electric-company
- **period:** closing 2023-11-07
- **locator:** closing and ownership paragraphs: Cameco 49%, Brookfield Renewable Partners with institutional partners 51%
- **language:** EN · **access date:** 2026-10-19
- **used by:** DX-06, DX-07

### 4. Alibaba investor-relations FAQ (primary)
- **source:** Alibaba Group investor relations FAQ
- **url_or_path:** https://www.alibabagroup.com/en-US/faqs-investor-information
- **period:** as accessed 2026-10-19
- **locator:** FAQ 'When was Alibaba Group listed?' (each ADS represents eight ordinary shares; 9988 HKD counter, 89988 RMB counter) and FAQ 'Are the U.S.-listed ADSs and Hong Kong-listed shares fungible?' (fully fungible, convertible both directions)
- **language:** EN · **access date:** 2026-10-19
- **used by:** DX-08, DX-09

### 5. Apple supplier list FY2023 (primary)
- **source:** Apple Supplier List (fiscal year 2023), Apple Supply Chain reports
- **url_or_path:** https://www.supplychainreports.apple/files/doc_downloads/2024/04/Apple-Supplier-List.pdf
- **period:** Apple fiscal year 2023
- **locator:** cover statement (suppliers representing 98% of direct spend for materials, manufacturing and assembly worldwide in fiscal 2023) and supplier tables (3M; ASE Technology)
- **language:** EN · **access date:** 2026-10-19
- **used by:** DX-10, DX-11, DX-12, DX-13, DX-14

### 6. Intuitive Surgical FY2025 10-K (primary)
- **source:** Intuitive Surgical, Inc. Form 10-K for fiscal year 2025 (accession 0001035267-26-000010, isrg-20251231.htm)
- **url_or_path:** https://www.sec.gov/Archives/edgar/data/1035267/000103526726000010/isrg-20251231.htm
- **period:** FY2025 (year ended 2025-12-31), filed 2026-02-03
- **locator:** Item 1 Business — Products — Systems — Da Vinci Surgical Systems
- **language:** EN · **access date:** 2026-10-19
- **used by:** DX-15

### 7. House theme crosswalk (repository file — internal evidence)
- **source:** House theme crosswalk (repository config, read-only)
- **url_or_path:** config/theme_crosswalk.yml
- **period:** origin/main 0221d6e171751c15b24d9f0bea27056aeab2716c
- **locator:** theme:surgical_robotics_systems definition (line 855) and its parents theme:robotics_automation, theme:medical_devices (lines 1118-1119) — line numbers grep-verified at the pinned revision; no `nominated_from` basket id is copied into any record
- **language:** EN · **access date:** 2026-10-19
- **used by:** DX-15, DX-16

### 8. Micron HBM3E press release (primary)
- **source:** Micron press release: Micron Commences Volume Production of Industry-Leading HBM3E Solution to Accelerate the Growth of AI
- **url_or_path:** https://investors.micron.com/news/press-release/2024/Micron-Commences-Volume-Production-of-Industry-Leading-HBM3E-Solution-to-Accelerate-the-Growth-of-AI-02-26-2024/default.aspx
- **period:** 2024-02-26
- **locator:** opening paragraphs: 24GB 8H HBM3E to be part of NVIDIA H200 Tensor Core GPUs shipping in calendar Q2 2024
- **language:** EN · **access date:** 2026-10-19
- **used by:** DX-17

### 9. GMI native-owner fact C01 (repository file — internal evidence)
- **source:** GMI native owner fact C01 (repository research, read-only)
- **url_or_path:** research/theme_graph/issuer_disclosures_20261011/C01_NATIVE_OWNER.json
- **period:** known_at 2026-10-11
- **locator:** fact kind product_integration, lifecycle planned, product 24GB 8H HBM3E, platform NVIDIA H200 (amount and economic_share null in the stored fact)
- **language:** EN · **access date:** 2026-10-19
- **used by:** DX-17

### 10. #9423 planned-integration vocabulary (repository file — internal evidence)
- **source:** GMI economic-context planned-integration vocabulary (PR #9423, repository code, read-only)
- **url_or_path:** engine/theme_graph/economic_context.py
- **period:** origin/main 0221d6e171751c15b24d9f0bea27056aeab2716c
- **locator:** native schema company_intelligence.private_product_integration/v2; mapping.state native_fact_context_only; reason PLANNED_INTEGRATION_MAPPING_NOT_ADOPTED; amount and economic_share null; authority context_only — every string grep-verified verbatim at the pinned revision
- **language:** EN · **access date:** 2026-10-19
- **used by:** DX-17

### 11. Security-master identity exceptions (repository files — internal evidence)
- **source:** Security-master identity exceptions (repository code + registry, read-only)
- **url_or_path:** scripts/build_security_master.py; config/dataset_registry.yml
- **period:** origin/main 0221d6e171751c15b24d9f0bea27056aeab2716c
- **locator:** DEFERRED_IDENTITY_KEYS['B'] (build_security_master.py lines 609-624) and DISCLOSED_IDENTITY_EXCEPTIONS['GOLD'] (lines 632-645); closed identity-exception enum 'Closed enum (V4-D2B1 §3)' (dataset_registry.yml line 315) — line numbers grep-verified at the pinned revision
- **language:** EN · **access date:** 2026-10-19
- **used by:** DX-19

### 12. Agent OS handoff recording the 2026-08-14 operator ruling (repository file — internal evidence)
- **source:** Agent OS handoffs recording the 2026-08-14 operator ruling
- **url_or_path:** agentos/handoffs/PROPHET-US-V4-RECOVERY-2026-08-21-D2B3-FREEZE.md
- **period:** 2026-08-21
- **locator:** identity-exception section: GOLD = CIK 1591588 (Gold.com), B = CIK 756894 (Barrick), ABX = CIK 1814287 (Abacus) (line 98); 'co:us:ABX absent is CORRECT (prior node never minted); do not "repair" it.' (line 154)
- **language:** EN · **access date:** 2026-10-19
- **used by:** DX-19, DX-20 — companion handoff `agentos/handoffs/STOCK-IDENTITY-2026-08-14-W2.md` exists and is named in the DX-19 disposition

### 13. CATL announcement 2021-053 (primary, ZH)
- **source:** Contemporary Amperex Technology Co., Limited announcement 2021-053 (cninfo)
- **url_or_path:** https://static.cninfo.com.cn/finalpage/2021-06-28/1210355996.PDF
- **period:** 2021-06-28
- **locator:** pages 1-3: supply framework with Tesla entities; quantities and prices determined by subsequent orders
- **language:** ZH · **access date:** 2026-10-19
- **used by:** DX-21, DX-22

### 14. AMD Q4/FY2024 results release (primary)
- **source:** AMD press release: AMD Reports Fourth Quarter and Full Year 2024 Financial Results
- **url_or_path:** https://ir.amd.com/news-events/press-releases/detail/1236/amd-reports-fourth-quarter-and-full-year-2024-financial-results
- **period:** Q4 and FY2024
- **locator:** segment results — Data Center segment
- **language:** EN · **access date:** 2026-10-19
- **used by:** DX-23, DX-24

### 15. Microsoft 2025 annual report (primary)
- **source:** Microsoft 2025 Annual Report
- **url_or_path:** https://www.microsoft.com/investor/reports/ar25/index.html
- **period:** fiscal year ended 2025-06-30
- **locator:** cash-flow statement (additions to property and equipment); material cash requirements; Note 13 commitments
- **language:** EN · **access date:** 2026-10-19
- **used by:** DX-26

### 16. GMI economic-network casebook (repository file — internal evidence)
- **source:** GMI economic-network casebook (repository research, read-only)
- **url_or_path:** research/theme_graph/economic_network_20261008/CASEBOOK_AND_COMPOSITION.md
- **period:** 2026-10-08
- **locator (per row, real section headings):** DX-03 preamble (entity names are source labels; canonical identity only via the identity owner) · DX-07 C04. Cameco, Brookfield and Westinghouse: ownership is a separate channel · DX-12/DX-13/DX-14 C03. Apple's supplier roster: coverage has a denominator · DX-18 C01. Micron → NVIDIA: a product-specific announcement (retrieval correction) · DX-22 C02. CATL ↔ Tesla entities: signed does not mean ordered · DX-24/DX-25 C05. AMD: one industry label can conceal opposing operating outcomes · DX-26 C06. Microsoft AI investment: stock, flow and commitment are different objects · DX-27 §3 Double counting and common causes
- **language:** EN · **access date:** 2026-10-19
- **used by:** DX-03, DX-07, DX-12, DX-13, DX-14, DX-18, DX-22, DX-24, DX-25, DX-26, DX-27

### 17. Security master parquet (data source for counts only — Table B)
- **url_or_path:** `origin/main:data/reference/security_master.parquet`, read via `git show` (this sparse tree has no `data/` checkout)
- **blob:** 452fe313fa8d1904539128edbc8fb2fdd7d861d1 (identical at the pinned revision and at origin/main on 2026-10-19)
- **used for:** STRATA_DESIGN.md Table B per-country and `issuer_state` counts, and check rule R5. Internal evidence; no new vendor, no paid read, no HKEX scrape.
