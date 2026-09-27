# Consumer Defensive R5 — design review and research verification

2026-09-23. Principal self-review of a proposed design, not independent acceptance, application qualification or a Fable commission.

Operation `gmi-consumer-defensive-research-20260923-sol-001`; Macro #7792, `sol/consumer-defensive-research-20260923`. MISSION_COMPLETE: false. FABLE_HANDOFF: NOT_ISSUED.

## 1. Exact reviewed artifacts

| Artifact | Content commit | Blob |
|---|---|---|
| Native-owner feasibility | 32a37c79aff4a602f5e15a1e3b7d5599e5805fde | e262f4fc2ea616223496c0614cfd02567958bd73 |
| Consolidated masterplan | 5fa43c0585f979263a2a7e28e4b468077c14aa55 | 34e46e1ccf17caf8ab913ff3cd12e9ceebb65ac2 |
| Written CDV-1 design | de3086fff1a883f2375ced3c9e8c713e8566f29b | 4539bb9db3e3f4e41ee9b1418ee4712eb4e5e56d |

The first two are under `research/consumer_defensive/`. The written design is `docs/superpowers/specs/2026-09-23-consumer-defensive-economic-dossier-design.md`. Native readbacks verified headers, the masterplan's rollout/limits sections, and the design's full 36-case table and closing gates. This is not a claim of an automated whole-document checker or independent code review.

Protected source remains Mastermind `4c1b3d389286df2a4b5b98a4d4491f2c8a1263f2`, compatible1.0.1/bootstrap1. Macro interface pin remains `2b2cae6a148f920b5c4e7ebd8df19ed14b159f5a`. No product source changed.

## 2. Self-review conclusions and narrow clarifications

The proposed first slice has a named persona, real source path, one launch issuer, finite data scope, private publication, a shared UI entry and measurable acceptance. The global Consumer Defensive mission is retained in six capability milestones; a single-company first release is not presented as global completion. Current shared-template and native-publication prerequisites are explicit rather than assumed.

The following clarify the proposed design, including potentially ambiguous shorthand. They are part of the review packet, not new source law:

1. **Organic growth is a company-defined revenue measure, not proven household demand.** Any shorthand such as organic demand in the design's opening intent must be read through sections5 and7: physical-consumption claims require actual appropriate evidence. The first interpretation says reported organic sales were flat; it does not establish that total consumer demand was exactly unchanged.
2. **Next eligible release means the latest currently eligible source selected at build/release time.** It does not require waiting for another quarter or permanently selecting the research example. A known newer unparsed source must be disclosed through the currentness rules.
3. **An unstable denominator needs an explicit mathematical definition.** For the implementation plan, derived percentage change requires a positive prior amount. Where the source provides a precision/uncertainty interval that reaches zero, do not compute an unqualified rate. Where only rounded displayed positive amounts are available, any calculated rate is explicitly approximate and cannot override the issuer-reported rate. No arbitrary company-specific small-EPS threshold is implied. Negative/zero denominators retain level/change disclosure rather than a misleading growth label.
4. **Private semantic reuse is not public publication.** New detailed workspace facts cannot be admitted to the public R2 publisher merely because event_workspace is the reusable source schema. Private record/manifest role evolution must be accepted within the existing earnings owner and verified before any live addition. V1 behavior remains readable; no parallel latest pointer or data store is proposed.
5. **Optional valuation does not silently complete the larger mandate.** CDV-1 can explain growth/earnings without licensed consensus or a current valuation join. The full masterplan still owes those capabilities. An unresolved company/security join cannot be cosmetically hidden by rendering a native issuer section beside market data.
6. **No company selection or investment conclusion follows from choosing PG for engineering proof.** The choice narrows the extraction and source-to-display test, not the thematic basket or opportunity list. Historical Hershey remains a regression input, not current coverage.

No product-specific live value, security binding, permission, source receipt or existing shared-template acceptance was invented to remove a dependency. The proposed version names and limits remain subject to native-owner/design review.

## 3. Executed research checks

A complete Python rerun passed sixteen research checks. Inputs were manually transcribed from the cited issuer sources, with Decimal arithmetic and explicit date comparisons. These tests do not execute or validate Mastermind product code.

| Check | Result |
|---|---|
| PG reported sales growth positive and reported organic flat remain different observations | PASS |
| PG rounded quarter bridge reconciles using disclosed neutral components, FX and other/rounding | PASS |
| PG displayed-input reported EPS change rounds to the reported rate | PASS |
| PG displayed-input core EPS change rounds to the core rate | PASS |
| PG both EPS measures decline, at different calculated rates | PASS |
| PG quarter and annual EPS are distinct inputs | PASS |
| PG release publication follows the selected fiscal quarter | PASS |
| Historical Hershey reported and adjusted EPS have opposite directions | PASS |
| Hershey reported EPS displayed-input change rounds to20.53% | PASS |
| Hershey adjusted EPS displayed-input change rounds to-2.29% | PASS |
| Hershey annual disclosure postdates its fiscal endpoint | PASS |
| Neither research example claims native admission or an invented source span | PASS |
| Authored review map covers exactly CDV1-01 through CDV1-36 | PASS |
| No duplicate acceptance IDs within a review group | PASS |
| All six authority-capability examples are literal false | PASS |
| Missing versus zero and mixed versus pure labels remain distinct examples | PASS |

The PG EPS inputs were1.26/1.48 and1.43/1.48; derived changes are approximately-14.8649% and-3.3784%, distinct from the source's rounded-15% and-3%. The historical Hershey inputs were10.92/9.06 and9.37/9.59; derived changes are20.5298% and-2.2941%. These are accounting example calculations, not stock returns, causal estimates or current valuation signals.

An initial optional local JSON export failed because the newly generated directory was owned by the container creator rather than the Python execution user. The directory's ownership and writability were inspected; only that assistant-generated directory was corrected. The entire research check routine was rerun, the file was written and its bytes/JSON were read back. No success was claimed from the failed run. GitHub writes were unaffected; no repo, credential or production permissions were changed.

Local QA export: `/mnt/data/consumer_defensive_r5/CONSUMER_DEFENSIVE_R5_RESEARCH_QA.json`.
Bytes:6762. SHA256:`ba21bbb9760514ed88255909f1cb2a9235e7c3812001e04a9373797f47713d81`.
This local export is a portable convenience. The durable design, research conclusions and verification statement live on #7792; future correctness does not depend on the local file surviving.

## 4. Acceptance traceability and unexecuted work

The review map groups all 36 proposed application cases:

| Review concern | Spec cases |
|---|---|
| Source and native economic scope | 01-14,32 |
| Interpretation and authority | 05-10,14-16,35 |
| Identity and membership | 17-18 |
| Time and correction | 19-24,36 |
| Private publication and access | 25-27,30,33-34 |
| Shared user journey and legacy behavior | 28-29,31 |

Overlapping groups are intentional review views, not additional test counts. Every case has status **NOT_EXECUTED**. A coverage assertion checks the authored map, not production enforcement. No parser, source retention, native extraction, schema migration, API authorization, browser UI, publisher or predictive strategy was exercised by the arithmetic checks.

Independent design review: not performed. Written-spec acceptance: not yet obtained. Native owner/private role acceptance: not yet obtained. Application tests run:0. Investment backtests run:0. CI/release/browser acceptance: not claimed. No source/control/test requirement was weakened to make the research checks pass.

## 5. Sources and next gate

Primary sources directly rechecked during R5:

- P&G, July29,2026 results: quarter versus annual tables, growth bridge and reported/core EPS. https://www.pginvestor.com/news/news-details/2026/PG-Announces-Fourth-Quarter-and-Fiscal-Year-2026-Results/default.aspx
- Hershey, February6,2025 results: historical annual reported/adjusted EPS and reconciliation. https://hershey.gcs-web.com/news-releases/news-release-details/hershey-reports-fourth-quarter-and-full-year-2024-financial
- SEC, EDGAR API documentation: aggregated non-custom/entity-wide facts and calendar Frames limitations. https://www.sec.gov/search-filings/edgar-application-programming-interfaces

Native-code references, exact blobs and unresolved publication/currentness reads are preserved in the R5 feasibility document. These web URLs are not native retention receipts. Earlier historical research checks have not been rerun or added to this turn's count.

The review packet consists of the masterplan, written CDV-1 design and these clarifications, supported by native feasibility and the preserved R1-R4 research. After written-design review/acceptance, the principal can prepare the exact implementation plan and reconcile current owner dependencies before the final lawful Fable handoff. This is not approval to implement, merge, deploy or dispatch Fable now.

Effect boundary: research/design/continuity artifacts only. EFFECT_UNKNOWN:none observed. No product source, live evidence, identity, membership, rank, entry, sizing, trade, auth, publisher configuration, worker, Executive Attempt or watcher changed. Preserve #7792 Draft/HOLD; parent mission remains incomplete.
