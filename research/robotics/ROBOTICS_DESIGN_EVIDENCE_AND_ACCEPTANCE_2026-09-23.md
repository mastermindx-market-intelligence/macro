# Robotics design evidence and acceptance cases — 23 September 2026

Operation: `gmi-robotics-bom-research-20260923-sol-001`. Same draft/HOLD PR #7773. Research and design evidence only; no production fact admission, new baskets, source-custody transfer or trade authority.

Written spec: `docs/superpowers/specs/2026-09-23-robotics-theme-evidence-vertical-design.md`, first committed at `ae4eccd2b281c8bddb65234a4f10d6534d429036`. Spec blob verified: `d248fd1b4c9b48df8f5c95c3bdd742c2a8ef7007`; portable spec SHA-256: `147b5640cad7b16bed2217cc6cbe92932c380043553a835cb6366a9e7bb911cf`.

## Primary evidence supplement

D1. Sanhua, 26 August 2026 interim results, PDF pages 28 and 30 (visually checked): https://www1.hkexnews.hk/listedco/listconews/sehk/2026/0826/2026082601555.pdf . The company describes progress toward actuator mass delivery/production ramp-up. The cited product-revenue table has refrigeration/air-conditioning and automotive categories, not a separately disclosed robotics number. Customer names from thermal management and total corporate production bases cannot be assigned to robotics without specific evidence.

D2. Parker K-Series: https://discover.parker.com/K-Series . This establishes frameless motor catalog capability and a robotics application category. It does not establish a named humanoid installation. The original publication date is unknown; 23 September 2026 is the observation date, not a product-launch date.

D3. Harmonic Drive Systems, exchange-filed Q1 report, 7 August 2026, period 1 April–30 June 2026: https://www2.jpx.co.jp/disc/63240/140120260804507706.pdf . PDF pages 14-16 were visually checked. This supplies a real component-business operating snapshot instead of an unsupported universal shortage label.

D4. Stabilus/Synapticon announcement, 29 July 2026: https://group.stabilus.com/news-and-events/press-releases/mail/news-synapticon-and-stabilus-form-partnership-to-develop-a-joint-product-line-of-integrated-actuators-for-humanoid-robots . Distinct development/manufacturing roles are disclosed. The source does not establish delivered units, qualified unit capacity or a production-start date. Proposed third-party 2027/2028 schedules were not imported into the accepted-as-research facts.

These sources remain issuer/supplier statements, not independent technical audits. Native immutable retention/admission receipts were not produced in this research turn.

## HDS observed operating snapshot

All monetary figures below are **JPY million**. Product group and reportable geography are preserved. Production is valued at selling prices, not units or nameplate capacity. A dash is retained as unavailable/not-applicable source presentation, not converted to measured zero. The table covers the company, not humanoids alone.

| Reportable geography | Product group | Production value | Orders | Orders YoY % | Backlog | Sales |
|---|---|---:|---:|---:|---:|---:|
| Japan | Speed reducers | 8,806 | 8,857 | 51.3 | 7,146 | 7,279 |
| Japan | Mechatronics | 1,759 | 1,193 | 58.8 | 1,287 | 811 |
| China | Speed reducers | — | 981 | -27.8 | 980 | 703 |
| China | Mechatronics | — | 149 | 33.9 | 119 | 304 |
| North America | Speed reducers | 1,308 | 2,663 | 25.3 | 5,259 | 1,735 |
| North America | Mechatronics | 1,014 | 4,416 | 336.2 | 5,330 | 1,299 |
| Europe | Speed reducers | 2,859 | 4,309 | 26.4 | 6,947 | 3,073 |
| Europe | Mechatronics | 1,318 | 1,555 | 77.3 | 2,385 | 1,473 |
| **Published total** | **All** | **17,068** | **24,128** | **55.7** | **29,457** | **16,681** |

Source: D3. The monetary order-to-sales ratio calculated from published totals is `24128 / 16681 = 1.446436` (rounded to six decimals). This is a descriptive book-to-bill calculation, not delivery lead time, utilization, a stock-return forecast or proof of a general shortage.

Published totals exceed sums of displayed component rows by 4 production, 5 orders, 4 backlog and 4 sales, consistent with the source's truncation below one million yen. Preserve both source totals and the discrepancy; do not fabricate balancing rows. Backlog is a point-in-time stock, whereas orders/sales cover the quarter. No earlier-period values were reconstructed from rounded YoY changes. A multi-period lead-time/capacity series remains unestablished.

## Thirty-two acceptance specifications

These are proposed behavioral tests, **not executed product tests**. Each maps to the numbered written-spec section. They survive here even without the portable JSON file.

| ID | Section | Required behavior |
|---|---|---|
| RBV-01 | 3.2 | Catalog capability must not become a named supply contract or SUPPLIES edge. |
| RBV-02 | 4 | Preserve the documented two-camera configuration and quantity basis; infer neither price nor revenue. |
| RBV-03 | 4 | A new robot generation without evidence must not inherit the predecessor BOM. |
| RBV-04 | 3.2 | A future deployment target remains a target, not delivered/installed units. |
| RBV-05 | 6 | Preserve reciprocal supply and planned customer roles as different directed relationships. |
| RBV-06 | 5 | Automotive customer names adjacent to robotics prose do not establish robotics customers. |
| RBV-07 | 5 | Corporate plant counts do not establish robot factories or robotics unit capacity. |
| RBV-08 | 4 | Not-separately-disclosed robotics revenue stays null, not zero. |
| RBV-09 | 4 | Reject financial ratios across incompatible entity, period or consolidation bases. |
| RBV-10 | 4 | Do not change operating ownership on an announcement whose closing date is unknown. |
| RBV-11 | 3.3 | An unresolved listing retains source-only evidence but no price/valuation/portfolio join. |
| RBV-12 | 3.2 | Similar business or model labels do not auto-merge into a canonical product. |
| RBV-13 | 3.3 | K1 cross-type joins without a consumed valid bridge refuse/degrade. |
| RBV-14 | 3 | Do not substitute the registered QLedger forward-claim object for factual product evidence. |
| RBV-15 | 3.1 | Keep unknown source publication separate from catalog retrieval and business-valid clocks. |
| RBV-16 | 3.1 | Two statements at one URL/date receive distinct immutable assertion selectors/revisions. |
| RBV-17 | 3.1 | Corrected source content at the same URL/date creates a new revision; the old evidence survives. |
| RBV-18 | 5 | Withdrawal or overdue review affects current applicability, not historical retention. |
| RBV-19 | 3.2 | Later-retained evidence cannot support a historically-known claim before retention. |
| RBV-20 | 3.1 | The date-only native edge key is not intraday replay proof. |
| RBV-21 | 4 | Reject simultaneous parent-assembly and contained-component cost counting. |
| RBV-22 | 4 | Do not convert per-hand into per-robot quantities without the missing multiplicity evidence. |
| RBV-23 | 4 | Backlog divided by quarterly sales is not supplier lead time. |
| RBV-24 | 4 | Preserve official rounded totals and residuals; do not manufacture balancing observations. |
| RBV-25 | 4 | Reject non-finite, negative or basis-free BOM quantities. |
| RBV-26 | 3.2 | Syndicated copies preserve upstream dependence, not independent confirmation count. |
| RBV-27 | 3.4 | Partial rights coverage must show restriction/partial state, not complete or empty. |
| RBV-28 | 6 | No current full-fidelity response through raw Git, Pages, public R2 or source-map mirrors. |
| RBV-29 | 6 | Unauthorized/forbidden/error responses preserve incumbent auth and private-no-store behavior. |
| RBV-30 | 6 | Desktop/mobile, EN/ZH and dark/light preserve identical quantities, units, statuses and sources. |
| RBV-31 | 8 | Frozen legacy membership, ranking, recommendation, entry and sizing outputs remain unchanged. |
| RBV-32 | 6 | A new UI build timestamp never hides lagging or incoherent source generations. |

Native round-trip/column persistence, opt-in K1 curation-clock binding and private source-publication admission are additional explicit first-unit gates in the spec. No field, bridge or auth behavior has been implemented by writing this table.

## Research integrity QA

Fourteen local checks passed: unique source IDs; source-reference closure; eight unique geography/product cells; all-false effect authority; no claimed canonical IDs; preserved unknown quantities/dates; published-total residuals; derived ratio arithmetic; 32 unique case IDs; zero product-test execution flags; section-reference closure; source pins; explicit private/native-owner language; unchanged original seed bytes.

The first QA invocation failed because a case-sensitive string test searched for `Evidence` while the specification used `K1 is a reference layer`. Inspection established a check defect, not missing semantics; the assertion was corrected to the actual requirement wording and all checks rerun. No research numbers or product requirements were weakened.

Portable artifacts:
- `ROBOTICS_PRIMARY_DELTA_2026-09-23.json`: SHA-256 `210e7534cb976e414c151bb0dcecf715e129f71436a59cf7502b06cb098a7b93`.
- `ROBOTICS_ACCEPTANCE_CASES_2026-09-23.json`: SHA-256 `10db9ff6e5d83b7cb7e3d6d873181bc3ff090120c357eaa214262c9402f474ae`.
- `verify_research_artifacts.py` reproduces integrity checks against the portable files; the original seed is an optional explicit input.

This is research integrity, not executed application tests, independent design acceptance, an Agent OS validator run, CI proof, native-source ingestion, browser proof or deployment. All production obligations remain open.
