# PB-C — Strategic announcement timing: completed retrospective pilot

**PB-G disposition: PROSPECTIVE_ONLY.** The captured panel does not validate abnormal post-stress announcement orchestration. Ordinary corporate calendars remain a substantial explanation, while the primary population hypotheses cannot yet be estimated. This is a completed research return with a usable pilot and a build-ready prospective design; it is not a completed population study or a trading signal.

Operation: `PB-C-STRATEGIC-ANNOUNCEMENT-ORCHESTRATION-20261007`  
Study interval: January 1–December 31, 2025; extraction and analysis: October 7, 2026.  
Carrier: [Macro draft PR #8565](https://github.com/mastermindx-market-intelligence/macro/pull/8565), branch `research/pb-c-announcement-study-20261007`.  
Original protocol commit: `22a6ab802791848b496ac895ec3335d8ffe34d4d`.  
Accepted panel/code freeze before event tests: `f856691e4578db7029646bba1c5e90949e009de5`.

All numerical findings below are reproducible from `PB_C_EVENT_PANEL.json`, `PB_C_STRESS_WINDOWS.json`, `nyse_calendar_2025.csv`, `reproduce_pilot.py` and `reproduce_descriptive_audit.py`. Exact results, tail counts, exclusions and input hashes are in `PB_C_ANALYSIS_RESULTS.json` and `PB_C_DESCRIPTIVE_AUDIT.json`. `PB_C_NULL_TESTS.md` displays the full specification table. Source originals, dates, terms and limitations are attached to each root; the combined source/coverage manifest contains 143 unique URLs.

## 1. What the pilot establishes

The final panel contains **91 deduplicated research events**: 54 material candidates, 36 first-results audit members, and one additional Lumentum full-results comparator. Three Apple items from a separately fixed source-frame audit bring the complete delivery to **94 roots**. All 36 frozen issuers are represented. There are 108 unique event-source URLs; the larger 143-URL register also includes advance calendar notices and linkage/context evidence. Publisher count is not a count of independent economic events.

The main exploratory sample has **46 timing-eligible positive-or-mixed material roots from 25 issuers**. It produces **22 unordered cross-issuer pairs within three trading sessions**, against a simulated mean of **21.5448** and central 95% reference range of **15–30**; the upper-tail diagnostic is **p = 0.482852**. There is no excess under this particular selected-panel reference model. The five-session result is similarly ordinary: 42 pairs versus a mean of 40.7724, p = 0.413159.

The most informative falsification is the calendar control. Among **31 first-results releases with earlier calendar notices**, there are **95 three-session pairs**, versus a mean of **57.1754**, p = **0.00059994**. Ordinary earnings calendars readily generate a small probability under this simple month/weekday model. That demonstrates an inadequate baseline for interpreting a small timing probability as orchestration; it does not prove that every strategic announcement follows an ordinary calendar.

There is an isolated numerical hint in a sensitivity: after removing capex/capacity events, the relaxed primary-issuer-only three-session statistic gives p = **0.017798**. The stronger disjoint-issuer version gives p = **0.050295** at three sessions and **0.045395** at five. Those are correlated exploratory variants, not multiplicity-controlled confirmation. At the same three-session horizon, excluding directly shared-program pairs changes the disjoint statistic from 17 pairs, p = 0.050295, to 11 pairs, p = **0.413159**. The five-session statistic was not subjected to that additional program filter; it must not be described as having passed or failed an unrun comparison.

## 2. Separate judgments on C1–C5

| Claim | Finding | Evidence confidence and practical interpretation |
|---|---|---|
| **C1 — STRESS_HAZARD** | **NOT_ESTIMABLE** as a population hazard. Treasury selected-event alignment shows no upper-tail excess. | Low confidence in the proposed positive claim. Complete source-frame issuer-day coverage, primary Nasdaq/VIX inputs and certified timing freedom are missing. The missing estimate is not a measured zero effect. |
| **C2 — CONNECTED_HAZARD** | **NOT_ESTIMABLE**. | Low confidence in a differential effect. Some prior government relationships are documented, but there is no pre-exposure graph covering the universe and no balanced matched risk set. |
| **C3 — CROSS_FIRM_SEQUENCE** | **No support in the primary selected-panel proxy; isolated sensitive subgroup hint.** | Low confidence in abnormal related-firm sequencing. The main disjoint-set proximity statistic is ordinary; exact ordering and a pre-event economic network are unmeasured. |
| **C4 — ECONOMIC_QUALITY_MATTERS** | **NOT_MEASURED** for H1/H5/H21 persistence. | Economic terms can be classified from documents, but no admitted adjusted issuer/benchmark/corporate-action panel establishes return persistence. |
| **C5 — ORDINARY_CALENDAR_NULL** | **Survives as a serious explanation; not proved complete.** | Moderate confidence that ordinary calendar structure can create apparent sequences; high confidence in the reproduced descriptive control result. Full conference/product/policy-calendar adjustment has not been fitted. |

These are evidence judgments, not numerical probabilities that a hypothesis is true. In particular, p = 0.48 is not a 48% probability of coordination, and the calendar result is not proof that deliberate timing never occurs.

## 3. Scope, sampling and integrity

The universe was fixed before pilot extraction and tests: AAPL, MSFT, AMZN, GOOG, META, NVDA, TSLA; AMD, INTC, AVGO, MU, TSM, QCOM; ANET, VRT, DELL, HPE, COHR, LITE, ETN; ORCL; LMT, RTX, NOC, MP, ALB; CSCO, IBM, TXN, ADBE; CAT, DE, PG, KO, HON, PEP. GOOG/GOOGL is one issuer. The TSM ADR mapping and source-country date ambiguity remain explicit. These are comparison strata, not demonstrated matched controls.

This is a **retrospective pre-analysis freeze**, not historical preregistration or an outcome-blinded experiment. The 2025 interval avoids treating the upstream 2026 NVDA case as confirmatory data, but general historical knowledge and the commission's hypothesis were unblinded. Search-driven official-source capture remains partial for every issuer-year. Current archive pages were inspected in 2026; complete contemporaneous versions, deleted items and global earliest disclosure are not certified.

The original two lane extracts contained 87 rows. One Apple–MP July 15 agreement appeared in both and was merged. A pre-test consistency review added five already-known candidates whose initial exclusions were not consistent with other admitted partnerships, nonbinding agreements or the expanded transaction taxonomy. The initial extract hashes and amendment A11 preserve that history. Three mechanically selected Apple archive items were added in a distinct arm. No stock-return screen was used, and no admitted issuer-return panel was used to classify winners.

| Sampling arm | Roots | Positive | Mixed | Negative | Other/unknown |
|---|---:|---:|---:|---:|---:|
| Material-event pilot | 54 | 15 | 32 | 6 | 1 |
| First-results audit | 36 | 12 | 22 | 2 | 0 |
| Extra Lumentum full-results comparator | 1 | 0 | 1 | 0 | 0 |
| Fixed Apple newsroom audit | 3 | 0 | 0 | 0 | 3 |
| **Total** | **94** | **27** | **55** | **8** | **4** |

Economic direction means analyst-coded announcement content, not consensus surprise, a measured valuation change or a subsequent return. An unquantified partnership can have a plausible commercial-benefit channel while its magnitude remains unknown; a restructuring with undisclosed allocation of rights can remain UNKNOWN. Those distinctions should be independently recoded before a confirmatory study.

There are **36 SCHEDULED** rows and **58 UNKNOWN** rows; no date is certified freely timed. Among the 36 first-results audit members, 35 are scheduled-type releases and 31 have prior calendar notices. Lumentum's February 3 preliminary release precedes its February 6 scheduled full results and remains UNKNOWN. The later full report is a separate comparator, not a replacement for the literal first disclosure. Prior notices can establish an earnings call/calendar date without certifying the exact realized release clock.

Six roots have usable source clocks with timezone evidence, only five in the broad material sample. None has a certified globally earliest public clock. Two Adobe local clocks lack timezones and are preserved without inventing UTC times. HPE's June 28 press publication is Saturday and excluded from the trading-date sampler; June 27 court filing is a separately labeled assumption sensitivity. Tesla's recall has document dates but unverified publication availability and is excluded from timing calculations. TSM's March 3 U.S. and March 4 Taiwan manifestations are one root with a source-date sensitivity.

### Counts by primary material-event species

Each material root has one mutually exclusive primary species for the leave-species tests; its full multi-label economics remain in the panel. This table sums to 54. The 37 results-related roots and three source-frame audit items are separate.

| Primary species | Roots |
|---|---:|
| Strategic partnership | 16 |
| Capex/capacity | 11 |
| AI/hyperscaler commitment | 6 |
| Financing | 3 |
| Divestiture | 3 |
| Acquisition | 2 |
| Buyback | 2 |
| Adverse legal/regulatory action | 2 |
| Adverse export restriction | 2 |
| Government contract | 1 |
| Subsidy/price-floor/offtake package | 1 |
| Official government agreement | 1 |
| Conditional regulatory approval/settlement | 1 |
| Adverse procurement decision | 1 |
| Safety recall | 1 |
| Business exit | 1 |

Buyback, warrant, subsidy and capacity mechanisms embedded in a larger root do not produce extra event counts. The at-minimum taxonomy was extended explicitly for adverse actions and transactions. An export restriction is not coded as government support merely to fit a menu.

## 4. Timing model and sensitivity results

The statistic counts unordered pairs of distinct roots whose observed public-issuer sets are disjoint and whose dates are at most three NYSE sessions apart. Same-day pairs are included, but no within-day direction is inferred. The disjoint-set rule is stronger than comparing only the primary ticker; a joint release cannot masquerade as two unrelated issuers. It still does not establish economic independence from uncaptured common counterparties.

For each root, the reference model independently samples a trading date, with replacement, from its original month and weekday. There are 10,000 simulations, master seed 20261007, and stable SHA256-derived root seeds with NumPy PCG64. Root assignments are shared across sensitivities. The upper-tail probability is `(1 + simulations at least as large as observed) / 10001`. Calendar releases stay fixed in the material-event model; the separate calendar diagnostic deliberately moves calendar roots to test how calendar structure compares with that simple reference distribution.

| Specification | Eligible roots | Three-session pairs | Null mean | Upper-tail p |
|---|---:|---:|---:|---:|
| Broad positive/mixed candidates, timing UNKNOWN | 46 | 22 | 21.5448 | 0.482852 |
| Broad sample, exclude directly shared-program pairs | 46 | 16 | 20.0451 | 0.896610 |
| Exclude any NVDA involvement | 41 | 15 | 18.5016 | 0.873613 |
| Exclude any NVDA, AMD or ORCL involvement | 36 | 10 | 14.6977 | 0.961404 |
| Positive-content-only broad sample | 15 | 3 | 2.1290 | 0.346865 |
| First-results releases classified scheduled | 35 | 119 | 71.0872 | 0.000300 |
| First-results releases with prior calendar notices | 31 | 95 | 57.1754 | 0.000600 |

The broad sample has 47 selected positive/mixed candidates before HPE's Saturday exclusion. Of the 22 observed close pairs, 11 are same-day and six share the May 13 HUMAIN program. The four HUMAIN agreements create six unordered pairs by themselves. The originals name the same infrastructure initiative; Cisco explicitly connects its announcement with the presidential visit. These are real commercial announcements and a documented shared launch context. They are not six independent origins of support. [E1–E4]

HPE's alternative June 27 filing-date assumption gives 47 eligible roots and p = 0.684932. TSM's Taiwan-date alternative gives p = 0.494051. The source-clock subset has only five roots and a constant zero proximity statistic under the sampled date model, so its probability is suppressed. The strict freely timed positive subset is empty and reports NOT_ESTIMABLE.

The first-program-representative sensitivity leaves 38 trading-date representatives and 12 close pairs. Its probabilities are deliberately suppressed: selecting the first observed representative before resampling is not the same null as simulating all members and reselecting the first in every simulation. Multiple direct program memberships are retained without transitive collapse; a bridge between Apple and MP programs does not turn every connected agreement into one launch. The full program-review memo explains the declared disjoint partition used only for this descriptive sensitivity.

The model preserves month and weekday, but does not fully preserve earnings weeks, conference agendas, product readiness, regulatory processes, financing rounds or issuer bursts. Search capture can also make eligible dates nonexchangeable. Monte Carlo error—about 0.005 for the main p-value—measures simulation precision only. It says nothing about capture bias or a misspecified calendar model. All 23 case results are disclosed; no smallest-p-value promotion is made.

## 5. What the stress analysis actually measured

The primary Nasdaq Composite drawdown, VIX conditions, issuer drawdowns, sector-relative stress and breadth are **NOT_MEASURED**. The data-source review identified unresolved admission/rights and adjustment requirements. Existing repository cache declarations do not prove current provider entitlement or corporate-action quality. FRED and Cboe conditions were reviewed, and those quantitative routes were withheld for this product-oriented research. This is a conservative source-admission decision, not a blanket legal conclusion about research use. [D1–D3]

Direct U.S. Treasury XML supports two prespecified sensitivities: nominal two-year par yields and real ten-year par yields, separately. A shock is an increase of at least 25 bp over five NYSE intervals. Event exposure uses only the previous five sessions, with ten as a sensitivity. Same-day closes never enter. The 2025 calendar has 250 NYSE sessions, including the January 9 closure; each Treasury instrument has 249 dated observations. Explicit last-observation carry handles the two equity-open bank holidays, with source age retained. Current-vintage curves are not an exact historical intraday feed replay. [D4–D5]

| Treasury specification | New 2025 onsets | Eligible event dates exposed, prior 5 | Eligible event dates exposed, prior 10 |
|---|---|---:|---:|
| Two-year nominal | April 11; May 14 | 10 of 250 | 20 of 250 |
| Ten-year real | April 10 | 6 of 250 | 14 of 250 |

The nominal onset changes are +28 bp and +27 bp; real changes are +43 bp on April 10 and +45 bp on April 11, the latter in the same episode. There are two new nominal onsets and one new real onset, with April overlap. **These must not be added into three independent economic shocks.** Nor do 9,000 possible issuer-session rows create 9,000 independent observations of market stress. The real prior-ten-session window also inherits early-January exposure from 2024.

| Broad material sample: captured roots aligned with exposure | Observed of46 | Null mean | Central 95% reference range | Upper-tail p |
|---|---:|---:|---|---:|
| Nominal 2y, prior 5 | 3 | 3.5540 | 1–7 | 0.757724 |
| Nominal 2y, prior 10 | 4 | 5.8200 | 3–9 | 0.939906 |
| Real 10y, prior 5 | 2 | 1.9816 | 0–4 | 0.677032 |
| Real 10y, prior 10 | 4 | 3.1921 | 1–5 | 0.404760 |

Only five unique broad roots appear in any of these aligned sets: Microsoft's January capex discussion, NVIDIA's April manufacturing plan, Intel's April Altera agreement, IBM's April investment plan, and AMD's May Sanmina agreement. All are coded MIXED. The 15 positive-content-only roots fall outside all four rate windows. These are facts about the captured sample; they are neither population rates nor proof of an absence of a primary equity-stress effect.

The four May 13 HUMAIN releases precede the May 14 nominal-rate onset. They cannot be counted as responses to that later rate shock. This chronology says nothing decisive about unmeasured Nasdaq or issuer stress. The three April adverse disclosures—NVIDIA H20 licensing, AMD MI308 licensing, and the Google ad-tech ruling—fall within the measured rate exposures as well. Contrary content was retained; there is no supportive-only stress ledger. The same-species exposed/unexposed captured-event counts are provided in `PB_C_DESCRIPTIVE_AUDIT.json`.

## 6. Negative-window audit and missing controls

Before archive inspection, the audit fixed April 11–17, 2025: the first real-yield prior-five-session exposed date followed by seven calendar days, for the alphabetically first two frozen issuers, AAPL and ADBE.

Apple's current global English Newsroom archive pages surrounding the interval show three items: an April 14 Watch promotion, an April 15 filmmaker profile and an April 16 environmental update. The last includes new semiconductor-supplier commitments; its incremental issuer economics are unresolved and it is retained. April 11,12,13 and17 have no items **inside that enumerated archive frame as retrieved**. Two of those dates are NYSE sessions. A complete global announcement-free week is not established. [N1–N4]

Adobe's dynamic archive did not yield a complete dated census. All seven days remain UNKNOWN. Search absence was never changed to zero. Current archives also cannot certify that an old item was never deleted or revised.

Consequently the commission's stronger controls remain unmet: no matched globally announcement-free stress windows, no sector/size/volatility-balanced weak-linkage issuer set, and no full pre-period frequency comparison. The small archive audit is useful source-frame negative evidence, not a substitute for them. Those gaps are why the return uses the explicit insufficient-data/prospective-design route.

## 7. Economic coordination is observable; market-support intent is a different claim

Some announcements have substantive economic mechanisms. MP's July 10 package includes a ten-year NdPr price floor, magnet offtake assurance, preferred equity/warrants and financing conditions. That changes prospective cash-flow support and funding access, while retaining dilution and execution risk. It demonstrates government industrial support. It does not establish that the public announcement was timed to rescue an equity drawdown. [E5]

Stage and incremental scope matter. NVIDIA/OpenAI's September 22 release describes a letter of intent and investment progressively linked to deployment. AMD/OpenAI's October 6 release describes a definitive arrangement with a warrant subject to purchase, technical and share-price milestones. Broadcom/OpenAI's October 13 deployment document is a term sheet alongside earlier co-development arrangements. These are not interchangeable with closed financing, deliveries or recognized sales. [E6–E8]

Intel's August 22 announced $8.9bn equity funding uses previously awarded CHIPS and Secure Enclave funding; it is not wholly incremental subsidy. Apple and Alphabet buyback authorizations released with earnings are calendar-linked capital decisions, not proof of executed repurchases or freely timed support. Those latter two illustrative releases were independently inspected but are not added opportunistically to the frozen first-results sample. [E9–E11]

Strategic disclosure timing is a credible background mechanism: the deHaan–Shevlin–Thornock abstract reports associations involving bad news, after-hours/busy-day disclosure and advance notice. Only the abstract was inspected here; its findings do not establish coordinated 2025 support announcements. [M1]

Nor is public market support an impossible concept. The SEC's September 14, 2001 emergency order explicitly relaxed repurchase conditions to support liquidity and orderly reopening. This is an outside-sample example of documented policy intent, not a 2025 event or evidence of a hidden current program. [M2]

A private instruction document is not the only conceivable route to a reasoned coordination inference. Convergent evidence that survives selection, ordinary calendars, common economic causes and replication could justify a graded inference. This panel does not reach that threshold. Its useful immediate output is a better evidence taxonomy, not an orchestration score.

## 8. Prospective acceptance and integration

`PB_C_PROSPECTIVE_ACCEPTANCE_CONTRACT.md` specifies the next design. Lock an untouched interval and the issuer/source/calendar definitions before capture. Use existing source/event/claim ownership to record complete issuer-day coverage; UNKNOWN must remain separate from a certified zero within the declared frame. Admit the exact primary market series and a consistent adjusted-return/corporate-action panel with provenance and permitted-use evidence. Preserve event-time uncertainty and historical revisions.

The relationship owner must provide typed edges whose public evidence predates stress. Matching must establish actual common support in sector, business model, size, volatility, fiscal calendar and baseline announcement intensity; current broad strata are inadequate. Economic coding should precede stress/outcome inspection where feasible and distinguish plan, authorization, conditional commitment, definitive agreement and execution.

The proposed ten-episode floor is a provisional feasibility gate, **not** a power calculation. Episode dependence and cross-instrument overlap still matter. A design-specific simulation or interval-precision study must set the minimally meaningful effect, dependence assumptions, error criterion, multiplicity and stopping rule before confirmatory outcomes. Do not loosen thresholds or pool unlike proxies after an unhelpful result.

Reuse the existing event/claim and relationship owners, News-to-Business-Impact interpretation, Policy Watch case context, and Prophet/evaluation research responsibilities. Map proposed research fields to their canonical contracts. Do not create another event store, duplicate lifecycle or live collector. The return confers no ranking, sizing, entry-timing or deployment authority.

The bounded internal code and numerical reviews are included and explicitly do **not** constitute the program's independent PB-F review. PB-G can consume this return as **PROSPECTIVE_ONLY**; neither PB-F completion nor the parent program's closure is claimed. The draft carrier remains unmerged.

## Selected primary sources

Event-specific source URLs and timing/stage records for every included root are in the panel. These selected links support the interpretive examples above; all retrieved October 7, 2026 unless otherwise recorded.

- **E1:** [NVIDIA/HUMAIN, May 13, 2025](https://nvidianews.nvidia.com/news/humain-and-nvidia-announce-strategic-partnership-to-build-ai-factories-of-the-future-in-saudi-arabia).
- **E2:** [AMD/HUMAIN, May 13, 2025](https://ir.amd.com/news-events/press-releases/detail/1250/amd-and-humain-form-strategic-10b-collaboration-to-advance-global-ai).
- **E3:** [AWS/HUMAIN, May 13, 2025](https://press.aboutamazon.com/2025/5/aws-and-humain-announce-groundbreaking-ai-zone-to-accelerate-ai-adoption-in-saudi-arabia-and-globally).
- **E4:** [Cisco/HUMAIN and official-visit context, May 13, 2025](https://newsroom.cisco.com/c/r/newsroom/en/us/a/y2025/m05/cisco-expands-partnership-with-saudi-arabia-to-power-the-ai-future.html).
- **E5:** [MP/DoD package, July 10, 2025](https://mpmaterials.com/news/mp-materials-announces-transformational-public-private-partnership-with-the-department-of-defense-to-accelerate-u-s-rare-earth-magnet-independence).
- **E6:** [NVIDIA/OpenAI letter of intent, September 22, 2025](https://openai.com/index/openai-nvidia-systems-partnership/).
- **E7:** [AMD/OpenAI agreement, October 6, 2025](https://ir.amd.com/news-events/press-releases/detail/1260/amd-and-openai-announce-strategic-partnership-to-deploy-6-gigawatts-of-amd-gpus).
- **E8:** [Broadcom/OpenAI deployment term sheet, October 13, 2025](https://investors.broadcom.com/news-releases/news-release-details/openai-and-broadcom-announce-strategic-collaboration-deploy-10).
- **E9:** [Intel government equity agreement, August 22, 2025](https://www.intc.com/news-events/press-releases/detail/1748/intel-and-trump-administration-reach-historic-agreement-to).
- **E10:** [Apple May 1, 2025 earnings and buyback authorization](https://www.apple.com/newsroom/2025/05/apple-reports-second-quarter-results/).
- **E11:** [Alphabet April 24, 2025 earnings and buyback authorization](https://www.sec.gov/Archives/edgar/data/1652044/000165204425000040/googexhibit991q12025.htm).
- **N1:** [Apple archive page22](https://www.apple.com/newsroom/archive/?page=22); surrounding pages21 and23 are recorded in the audit.
- **N2:** [Apple Watch promotion, April 14, 2025](https://www.apple.com/newsroom/2025/04/get-active-with-apple-watch/).
- **N3:** [Apple filmmaker profile, April 15, 2025](https://www.apple.com/newsroom/2025/04/meet-four-emerging-filmmakers-bending-cultural-and-creative-lines-with-iphone-16-pro-max/).
- **N4:** [Apple environmental update and supplier commitments, April 16, 2025](https://www.apple.com/newsroom/2025/04/apple-surpasses-60-percent-reduction-in-global-greenhouse-gas-emissions/).
- **D1:** [FRED service terms](https://fred.stlouisfed.org/legal/).
- **D2:** [Cboe website terms](https://www.cboe.com/terms).
- **D3:** [Cboe content-use process](https://www.cboe.com/use-of-content).
- **D4:** [Treasury XML feed documentation](https://home.treasury.gov/treasury-daily-interest-rate-xml-feed); exact dated feed URLs and hashes are in `treasury_stress_manifest.json`.
- **D5:** [ICE notice of the January 9, 2025 NYSE closure](https://ir.theice.com/press/news-details/2024/The-New-York-Stock-Exchange-Will-Close-Markets-on-January-9-to-Honor-the-Passing-of-Former-President-Jimmy-Carter-on-National-Day-of-Mourning/default.aspx).
- **M1:** [deHaan, Shevlin and Thornock2015, author-institution abstract](https://scholarsarchive.byu.edu/facpub/8587/).
- **M2:** [SEC emergency order34-44791, September 14, 2001](https://www.sec.gov/rules-regulations/2001/09/emergency-order-pursuant-section-12k2-securities-exchange-act-1934-taking-temporary-action-respond).

The methods memo separately records the primary methodological literature and whether abstracts or full methods were actually inspected. No literature result is represented as an executed PB-C population model.
