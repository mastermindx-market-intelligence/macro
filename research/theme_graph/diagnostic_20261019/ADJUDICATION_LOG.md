# GMI diagnostic casebook — adjudication log (2026-10-19, lane 7d)

Research artifacts only. One row per case in `cases.jsonl`; every count below is computed by the lane check script (2026-10-19 run) and equals its printed output. This is a diagnostic casebook: rows ≠ issuers ≠ episodes, and no "fires" are reported anywhere in this lane.

## 1. Adjudication table

| case_id | episode | expected | refusal | decided_by | status | one-line rationale |
|---|---|---|---|---|---|---|
| DX-01 | ep:nvda-fy2026-direct-customer-concentration | ANONYMOUS_RETAINED | — | GMI orchestrator A (model) | MODEL_PROPOSED_PENDING_HUMAN | The 22% customer concentration stays on an anonymous counterparty, never resolved to a name. |
| DX-02 | ep:nvda-fy2026-direct-customer-concentration | ANONYMOUS_RETAINED | — | GMI orchestrator A (model) | MODEL_PROPOSED_PENDING_HUMAN | Same rule at 14%: the share is real, the counterparty identity is not disclosed. |
| DX-03 | ep:nvda-fy2026-direct-customer-concentration | REFUSE | ANONYMOUS_COUNTERPARTY_RESOLUTION_REFUSED | 20261008 casebook + INDEPENDENT_REVIEW | PRIOR_REVIEW_PENDING_HUMAN | An anonymous disclosed customer is never inferred to a named issuer from press, rank or market share. |
| DX-04 | ep:wmt-fy27q2-advertising-basis | ADMIT_PROPOSED | — | GMI orchestrator A (model) | MODEL_PROPOSED_PENDING_HUMAN | Activity membership is proposable; the accounting basis splits between net sales and contra cost of sales, so no revenue share is invented. |
| DX-05 | ep:wmt-fy27q2-advertising-basis | REFUSE | GROWTH_RATE_IS_NOT_EXPOSURE_MAGNITUDE | GMI orchestrator A (model) | MODEL_PROPOSED_PENDING_HUMAN | A year-over-year growth rate has no exposure denominator. |
| DX-06 | ep:ccj-westinghouse-2023-acquisition | ADMIT_PROPOSED | — | GMI orchestrator A (model) | MODEL_PROPOSED_PENDING_HUMAN | 49% is an ownership magnitude at closing 2023-11-07, routed to the ownership/corporate-action owner. |
| DX-07 | ep:ccj-westinghouse-2023-acquisition | REFUSE | OWNERSHIP_IS_NOT_CUSTOMER_SHARE | 20261008 casebook + INDEPENDENT_REVIEW | PRIOR_REVIEW_PENDING_HUMAN | Equity ownership has an ownership denominator; it is neither a revenue share nor supplier dependence (casebook C04). |
| DX-08 | ep:baba-listing-identity | IDENTITY_SPLIT | — | GMI orchestrator A (model) | MODEL_PROPOSED_PENDING_HUMAN | One issuer, three securities; the HK line carries no master issuer evidence, the link is the issuer's own FAQ, and the 8-ordinary-share ADS ratio must normalise per-share comparison. |
| DX-09 | ep:baba-listing-identity | REFUSE | DUPLICATE_ISSUER_ACROSS_LISTINGS | GMI orchestrator A (model) | MODEL_PROPOSED_PENDING_HUMAN | BABA and 9988 are two securities of one issuer; counting both as issuers double counts (casebook C04 cross-listing rule). |
| DX-10 | ep:aapl-fy2023-supplier-roster | ADMIT_PROPOSED | — | GMI orchestrator A (model) | MODEL_PROPOSED_PENDING_HUMAN | Roster membership only; the 98% describes the whole roster's spend coverage, never this pair. |
| DX-11 | ep:aapl-fy2023-supplier-roster | ADMIT_PROPOSED | — | GMI orchestrator A (model) | MODEL_PROPOSED_PENDING_HUMAN | Same roster rule; strata stay those of the subject (Apple, US) — see §3 ASE note. |
| DX-12 | ep:aapl-fy2023-supplier-roster | REFUSE | ROSTER_IS_NOT_PER_SUPPLIER_SHARE | 20261008 casebook + INDEPENDENT_REVIEW | PRIOR_REVIEW_PENDING_HUMAN | The 98% is roster aggregate coverage and must not be copied to an edge, divided across the roster, or applied to Apple's total expenses (C03). |
| DX-13 | ep:aapl-fy2023-supplier-roster | REFUSE | CO_LISTING_IS_NOT_A_RELATIONSHIP | 20261008 casebook + INDEPENDENT_REVIEW | PRIOR_REVIEW_PENDING_HUMAN | Two suppliers retrieved together on one roster are not a commercial relationship (C03). |
| DX-14 | ep:aapl-fy2023-supplier-roster | REFUSE | ROSTER_OMISSION_IS_NOT_TERMINATION | 20261008 casebook + INDEPENDENT_REVIEW | PRIOR_REVIEW_PENDING_HUMAN | Omission from a later roster is an observation about that roster, not termination (C03 disappearance rule; same rule as the A2 history fold's REMOVAL_REFUSED_NON_EXHAUSTIVE_ROSTER). |
| DX-15 | ep:isrg-surgical-robotics-micro | ADMIT_PROPOSED | — | GMI orchestrator A (model) | MODEL_PROPOSED_PENDING_HUMAN | One proposal at micro grain; parent paths (robotics_automation, medical_devices) are derived from the hierarchy at read time. |
| DX-16 | ep:isrg-surgical-robotics-micro | REFUSE | PARENT_PATH_IS_DERIVED_NOT_A_SECOND_MEMBERSHIP | GMI orchestrator A (model) | MODEL_PROPOSED_PENDING_HUMAN | A derived parent path is never stored as a second membership; storing one double counts the optional-parent micro. |
| DX-17 | ep:mu-nvda-hbm3e-h200-2024 | ADMIT_PROPOSED | — | 20261008 casebook + INDEPENDENT_REVIEW | PRIOR_REVIEW_PENDING_HUMAN | Context-only planned integration: amount and economic_share stay null, the mapping is not adopted, and the A2 fold refuses it as GRAPH_MEMBERSHIP_USE_NOT_GRANTED until use is granted. |
| DX-18 | ep:mu-nvda-hbm3e-h200-2024 | REFUSE | SEARCH_SNIPPET_IS_NOT_AN_INSPECTED_SOURCE | 20261008 casebook + INDEPENDENT_REVIEW | PRIOR_REVIEW_PENDING_HUMAN | A search result is not an inspected source; the snippet's numerical claim is excluded (C01 retrieval correction). |
| DX-19 | ep:gold-ticker-reuse | IDENTITY_SPLIT | — | operator ruling 2026-08-14 (Chairman) | HUMAN_RULED | GOLD, B and ABX are three distinct identities; the live CIK map's GOLD row is Gold.com, not Barrick; held until the identity owner releases it. |
| DX-20 | ep:gold-ticker-reuse | REFUSE | TICKER_REUSE_IDENTITY_NOT_INFERRED | GMI orchestrator A (model) | MODEL_PROPOSED_PENDING_HUMAN | Ticker reuse is never resolved by symbol match; origin switched to HARD_NEGATIVE_20261019 — see §2. |
| DX-21 | ep:catl-tesla-2021-framework | REFUSE | IDENTITY_NOT_RESOLVED | 20261008 casebook + INDEPENDENT_REVIEW | PRIOR_REVIEW_PENDING_HUMAN | The relation is proposal-grade but the subject issuer has no issuer evidence in the master, so it cannot be proposed yet — this is the CN stratum gap. |
| DX-22 | ep:catl-tesla-2021-framework | REFUSE | FRAMEWORK_IS_NOT_COMMITTED_REVENUE | 20261008 casebook + INDEPENDENT_REVIEW | PRIOR_REVIEW_PENDING_HUMAN | Quantities and prices are determined by subsequent orders; the framework is not committed revenue and is not split across the named Tesla entities (C02). |
| DX-23 | ep:amd-fy2024-data-center | ADMIT_PROPOSED | — | 20261008 casebook + INDEPENDENT_REVIEW | PRIOR_REVIEW_PENDING_HUMAN | A dated segment-reported observation tied to issuer, fiscal period and source definition; membership at segment grain only (C05). |
| DX-24 | ep:amd-fy2024-data-center | REFUSE | SEGMENT_TOTAL_IS_NOT_PRODUCT_ALLOCATION | 20261008 casebook + INDEPENDENT_REVIEW | PRIOR_REVIEW_PENDING_HUMAN | A Data Center total is not a CPU-only measure and cannot be allocated to a single micro-theme (C05). |
| DX-25 | ep:amd-fy2024-data-center | REFUSE | SHARED_THEME_IS_NOT_SHARED_GROWTH | 20261008 casebook + INDEPENDENT_REVIEW | PRIOR_REVIEW_PENDING_HUMAN | Same-period segment divergence is the counterexample to a "shared theme implies shared growth" mapping (C05). |
| DX-26 | ep:msft-fy2025-capex-commitments | REFUSE | CAPEX_IS_NOT_SUPPLIER_ALLOCATION | 20261008 casebook + INDEPENDENT_REVIEW | PRIOR_REVIEW_PENDING_HUMAN | Cash additions, finance-lease additions and commitments are distinct measures; none identifies supplier receipts (C06). |
| DX-27 | ep:unreported-pair-generic | REFUSE | ABSENT_PAIR_IS_UNKNOWN_NOT_NEGATIVE | 20261008 casebook + INDEPENDENT_REVIEW | PRIOR_REVIEW_PENDING_HUMAN | Unreported pairs are unknown rather than negatives (INDEPENDENT_REVIEW lines 70/74/106; RESEARCH_FINDINGS line 28). |

## 2. Origin switch: DX-20 (HARD_NEGATIVE_20261008 → HARD_NEGATIVE_20261019)

The frozen packet listed DX-20 ("mapping NYSE GOLD to the Barrick gold miner") as `HARD_NEGATIVE_20261008` unless the 2026-10-08 documents contain the rule. The rule (ticker-reuse identity inference refused) is **not present** in `CASEBOOK_AND_COMPOSITION.md`, `INDEPENDENT_REVIEW.md` or `RESEARCH_FINDINGS.md` (grep over all three: no Barrick / NYSE-GOLD-reuse content; the only "gold" hits are unrelated statistical gold-set requirements). Per the frozen instruction, DX-20's origin was switched to `HARD_NEGATIVE_20261019`, its disposition to `MODEL_PROPOSED_PENDING_HUMAN`, and it is listed here. No other row was switched; no casebook section was invented. The two rows that could plausibly have needed the switch did not, and were left at 2026-10-08:

- DX-03 (anonymous-counterparty resolution): supported by INDEPENDENT_REVIEW line 170 ("anonymous aliases … retain their proper denominator/status") and the sourcing annotation state `OBSERVED_ANON` (SOURCING §6 line 136).
- DX-27 (absent pair unknown, not negative): supported by INDEPENDENT_REVIEW lines 70/74/106 ("unreported pairs are unknown rather than negatives") and RESEARCH_FINDINGS line 28 ("do not interpret absence as no relationship").

## 3. Verification notes recorded during transcription

- **CATL HK line:** the master contains **no** HK line for CATL — no `inception_code` containing `3750` exists in `origin/main:data/reference/security_master.parquet`. Recorded here; not added (frozen rule).
- **ASE home listing:** ASE Technology Holding Co., Ltd. is Taiwan-home-listed, which is outside the design's listing strata (schema value `OTHER`) and absent from the master as a home line. Only its US cross-listing exists (`SEC:US-XNYS-ASX`, XNYS, RESOLVED). DX-11/DX-13 keep the SUBJECT's strata (Apple, US) per the frozen spec.
- **BABA HK line:** `SEC:HK-XHKG-09988` exists with `issuer_state=NO_ISSUER_EVIDENCE` (no `issuer_id`), as the frozen spec instructed to verify.
- **GOLD identity:** `ISS:US-XNYS-GOLD` exists with `issuer_state=DEFERRED_IDENTITY_EXCEPTION`, so DX-19/DX-20 use the resolved-issuer party form. The locator line numbers in `scripts/build_security_master.py` are current-main lines (609–624, 632–645); the 2026-08-21 handoff cites the same blocks at their then-current lines (517–532, 540–553) — pure line drift, same content.
- **CIT_GOLD_RULING wording:** the handoff contains the CIK map verbatim (line 98) and the ABX no-repair rule (line 154); the packet's paraphrase "do not reinterpret NYSE GOLD as Barrick" appears in substance in `build_security_master.py` (GOLD exception reason, "must not be treated as Barrick/miner history"), not verbatim in the handoff. The locator records what is present.

## 4. Honest N (computed by script; rows ≠ issuers ≠ episodes; no fires reported)

| Measure | Value |
|---|---|
| Rows | **27** |
| Distinct episodes | **12** |
| Distinct resolved issuers (unique `ISS:` across subject+counterparty) | **13** |
| Distinct securities (`SEC:`) | **15** |
| Unresolved non-anonymous parties | **5 unique parties / 8 row occurrences** |
| Anonymous parties | **3 unique / 3 row occurrences** |

Unresolved non-anonymous parties by reason (script output):

- `DEFERRED_IDENTITY_KEY_NEVER_MINTS` — 2 rows, 1 unique party (Barrick (NYSE: B)).
- `NOT_IN_SECURITY_MASTER` — 1 row, 1 unique party (Alibaba HKEX RMB counter 89988).
- `NO_ISSUER_EVIDENCE` — 2 rows, 1 unique party (Contemporary Amperex Technology Co., Limited).
- `PRIVATE_COMPANY_NOT_IN_SECURITY_MASTER` — 2 rows, 1 unique party (Westinghouse Electric Company).
- `UNREPORTED_PAIR_UNKNOWN` — 1 row, 1 unique party (generic unreported-pair label).

(The expected values 27 rows / 12 episodes printed by the script match the frozen packet's expectation; the packet's numbers were a check, not the source — the script output is the reported fact.)

**Hard negatives retained: 15 rows, 15 distinct refusal codes** — `ABSENT_PAIR_IS_UNKNOWN_NOT_NEGATIVE`, `ANONYMOUS_COUNTERPARTY_RESOLUTION_REFUSED`, `CAPEX_IS_NOT_SUPPLIER_ALLOCATION`, `CO_LISTING_IS_NOT_A_RELATIONSHIP`, `DUPLICATE_ISSUER_ACROSS_LISTINGS`, `FRAMEWORK_IS_NOT_COMMITTED_REVENUE`, `GROWTH_RATE_IS_NOT_EXPOSURE_MAGNITUDE`, `OWNERSHIP_IS_NOT_CUSTOMER_SHARE`, `PARENT_PATH_IS_DERIVED_NOT_A_SECOND_MEMBERSHIP`, `ROSTER_IS_NOT_PER_SUPPLIER_SHARE`, `ROSTER_OMISSION_IS_NOT_TERMINATION`, `SEARCH_SNIPPET_IS_NOT_AN_INSPECTED_SOURCE`, `SEGMENT_TOTAL_IS_NOT_PRODUCT_ALLOCATION`, `SHARED_THEME_IS_NOT_SHARED_GROWTH`, `TICKER_REUSE_IDENTITY_NOT_INFERRED`.

**Dispositions: HUMAN_RULED 1 · PRIOR_REVIEW_PENDING_HUMAN 14 · MODEL_PROPOSED_PENDING_HUMAN 12.** Only the GOLD identity row (DX-19) carries a human ruling (operator ruling 2026-08-14, Chairman). After the DX-20 origin switch, everything else in this casebook awaits human disposition — a model proposed it or a prior model review supports it; neither is a ruling.

**Origin counts (script):** SECTION8 9 · CASEBOOK_20261008 3 · HARD_NEGATIVE_20261008 11 · HARD_NEGATIVE_20261019 4. **Expected-behaviour counts (script):** ADMIT_PROPOSED 7 · ANONYMOUS_RETAINED 2 · IDENTITY_SPLIT 2 · REFUSE 16.

## 5. Who is missing from the panel

- **Delisted / dead issuers:** the master is a survivorship panel of currently mapped securities; no exited issuer, no observation start, no fabricated history.
- **CA primary-listed issuers without a US line:** the TSX route returned 403; only US-cross-listed Canadians (e.g. Cameco via NYSE CCJ) appear.
- **UK / JP / EU (INT strata):** zero rows; JPX requires permission and no UK/EU route is installed.
- **CN and HK issuer evidence:** security-level only — 1,019 CN + 147 HK rows, all `NO_ISSUER_EVIDENCE`; issuer-level cells are unfillable today.
- **Private counterparties** (Westinghouse) outside any master.
- **Anonymous counterparties** (by construction — never resolved).
- **Taiwan-home-listed suppliers** (ASE's home line): outside the design's listing strata and absent from the master; only the US cross-listing exists.
- **Bilingual primary sources:** the only bilingual primary sources for the cases here (HKEX filings) are behind the HKEX scraping ban.
- **The financials sector group:** no case in this set exercises it (zero at every listing).

## 6. What this set can and cannot support

This is a **diagnostic casebook**: 27 authored rows over 12 episodes and 13 resolved issuers, exercising typed refusals, anonymous retention, identity splits and magnitude discipline. It can support qualitative schema/adjudication review, hard-negative regression expectations, and gap exposure per stratum. It **cannot** support precision qualification, recall or coverage claims, automatic-admission gates, or any market-wide statement. It does **not** satisfy the 120-issuer design: Table A in `STRATA_DESIGN.md` is planned 120 / frozen 0, the collection never ran (WP02 `NOT_READY — NO_120_ISSUER_SELECTION`), and INDEPENDENT_REVIEW lines 104/211/236 bar the diagnostic from per-stratum precision proof or global recall.
