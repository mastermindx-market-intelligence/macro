# PCE bridge — accepted R0 research and executable-reference evidence

**Program:** Macro #7030, `release-radar-pce-bridge-20260910-sol-001`. **Owner:** CEO Sol. **Date:** 2026-09-10. **State:** R0 bounded research accepted; local descriptive reference tested; product implementation and deployment NOT_PROVEN.

This is an evidence document. It does not contain or publish the local executable reference. The separate attempted GitHub tree upload of that code was blocked by the tool safety check, returned no tree SHA, and was not retried through another writer. A subsequent exact branch-ref read still showed `333468cd5c5687caa39a8f6502cc5923cf44fcd2`. Do not infer that code exists in this PR from the tests described below.

## 1. R0 actually executed and was explicitly closed

Existing capacity placed one isolated researcher without Chairman account allocation on the exact root `C0BSBM78V1N/1789048190.485369`. The actual model was a ChatGPT Sol-class model using High/non-Pro reasoning; Terra was the requested capability avenue, not a verified model-name claim.

Receipts on that same root:

- placement `1789050981.378909`;
- PICKUP_ACK `1789051106.333899`;
- separate START `1789051340.271879`;
- RESULT/HOLD-FOR-SOL `1789051927.418399`;
- Secretary RETURN_AVAILABLE `1789052488.474539`;
- **Sol accepted bounded research and issued terminal STOP `1789053528.112009`.**

The exact assigned conversation is `6aa2c013-0cb0-83ea-87f7-8056b1eb82f0`. That child is terminal, not WAITING_CAPACITY. Its STOP requires removal/suppression of only the exact child source; the permanent Secretary aggregate and sibling sources remain active. Child-source removal has not been independently read back at this checkpoint. No successor research or implementation was assigned by STOP. Executive lifecycle or production was never claimed.

## 2. Accepted source dispositions and numerical admission ceiling

The table preserves the returned primary-source review. Literal codes not independently reopened by the parent remain researcher-reported. Every raw PPI series described below is NSA. A source-family mapping is not an admitted raw-series-to-SA-PCE formula, verified weight, first-observed archive or calibrated forecast.

| Component | Accepted research disposition | Evidence and remaining restriction |
|---|---|---|
| Physician services | verified_direct_mapping, source-family level | BEA Table 5.B identifies physician-office PPI. Parent independently read BLS PCU621111621111, offices of physicians except mental health, NSA. Exact PCE scope/seasonal adjustments still require numerical method admission. |
| Hospitals | verified_direct_mapping, source-family level | BEA names hospital PPI. Researcher reports broad PCU622---622---. Parent independently read narrower PCU622110622110, general medical/surgical hospitals, NSA. Never silently substitute the narrower index for the broad aggregate. |
| Nursing homes | verified_direct_mapping, source-family level | BEA identifies nursing-care PPI; parent independently read PCU623110623110, NSA. Current history is not originally available vintage evidence. |
| Dental services | source_conflict | BEA December-2024 handbook names CPI; the BLS healthcare factsheet names dental PPI as a PCE input. Parent read PCU621210621210. Researcher reports CUSR0000SEMC02/ CUUR0000SEMC02 CPI variants. Series existence and fresher retrieval do not resolve BEA's applicable method. |
| Domestic scheduled passenger air | verified_direct_mapping, source-family level | BEA names domestic scheduled passenger-air PPI, not all air transportation. Researcher reports PCU4811114811111; parent did not independently re-verify that exact code endpoint. |
| Portfolio management / investment advice | historical_only for the old PPI bridge after the announced publication-method change | Old handbook uses a fixed-weight average of portfolio/advice PPIs. Researcher reports PCU5239405239401 and PCU5239405239402. The announced new method uses a CES quantity extrapolator. Exact CES measure/formula is unknown; employment is not a price index, and a combined PPI is not automatically equivalent to the two old detail inputs. |
| Legal services | verified_composite_requires_inputs | BEA announces a selected household-legal PPI composite replacing its CPI source beginning in 2024. Exact selected series and weights are not published in the preview. Researcher examples PCU5411105411102, ...3 and ...6 are not an admitted basket. |
| Computer software / accessories | verified_composite_requires_inputs | BEA announces a CPI plus game-publishing and hosting/ASP/infrastructure PPI composite. Researcher reports CUUR0000SEEE02, PCU5132105132107 and PCU5182105182105. Exact weights and seasonal transformation remain unavailable; parent has not independently re-verified those master rows. |

The smallest source review is complete, with explicit unresolveds. Descriptive P1 readiness and measurement-risk context can proceed with those limits. Numerical P2 must still admit exact source scope, seasonal treatment, PCE expenditure shares, component transforms, residual/prior behavior and source availability. No field in the reference fills those gaps with an LLM estimate.

Primary references:

- [BEA NIPA Handbook Chapter 5, December 2024](https://www.bea.gov/resources/methodologies/nipa-handbook/pdf/chapter-05.pdf): parent visually inspected Table 5.B on printed pages 5-20/21/23/29; the researcher inspected additional relevant pages.
- [BLS healthcare/PCE factsheet](https://www.bls.gov/ppi/factsheets/producer-price-index-healthcare-factsheet.htm): the dental method conflict is retained, not guessed away.
- [BEA June 2026 annual-update preview](https://apps.bea.gov/scb/issues/2026/06-june/0626-nea-preview.htm) and [August 17 announcement](https://www.bea.gov/news/blog/2026-08-17/annual-update-gdp-industry-and-state-stats-publicly-available-starting-sept-30): portfolio, legal and software method changes are announced for September 30, not already observed as applied at this review.
- [BLS PCE/CPI mapping](https://www.bls.gov/cpi/additional-resources/pce-cpi-code-mapping.htm) is a classification crosswalk, not proof of which deflator BEA uses. It does not settle dental.

The June preview also identifies professional-association dues as dependent on the legal-services deflator. Preserve that method dependency without widening the closed eight-row child or implying its numerical composite is known.

## 3. New release-day omission: source and real repository artifact agree

Inspected Macro pin: `d557e49029eae1333679e1edde80a4cc067a87e2`.

`data/release_forecast/latest.json` was 139687 bytes, SHA256 `e23a34a49dd70e152f34eba671d9eb95edff1604b2c488ca968af2bf150bf013`, as-of `2026-09-10T10:05:21Z`. This is a repository artifact, not served-production readback. It was built before the official 08:30 Eastern PPI release, contains August CPI for September 11 and August PCE for September 30, but has **no August PPI item**. Its next PPI item is September's reference month scheduled October 15.

The source reason is `scripts/build_release_forecast.py::_find_upcoming_releases`, lines 253-254: its `ev_date <= today` guard excludes the entire release day at date precision, including before the publication time. The source behavior and pre-release artifact omission agree. A next-row dependency join would therefore risk attaching October PPI to August PCE.

**Do not repair this by changing one comparison without preserving forecast admission.** Retaining a due-day display item and authorizing a fresh forecast are different things. A naive date-guard change could let a post-release model run enter a pre-release cohort. The existing owner needs to preserve the last lawful frozen prediction through release day, retain the canonical event, and join later official actuals without rerunning or backdating that prediction.

The current core PCE point, 0.2147% month-on-month, and its distinct p50, 0.2065%, are existing legacy outputs. They were frozen before PPI. They are not a new post-PPI bridge; the reference does not render them as one. The model/target epochs remain `champion_legacy_target_v1` / `legacy_cross_vintage_initial_levels_v0`.

The current `event_calendar` object has declared dates but no verified official reference-month binding. Release Radar currently infers a preceding month. P1 must label the inherited basis honestly until the existing source owner provides a stronger relation; same-day BEA national monthly PCE and state annual PCE are different targets.

Official schedule references: [BLS September](https://www.bls.gov/schedule/2026/09_sched_list.htm), [BEA schedule](https://www.bea.gov/news/schedule), [BLS PPI release](https://www.bls.gov/news.release/ppi.htm).

## 4. Publication, component freshness and inclusion are three different facts

The retrieved BLS physician, hospital and nursing series representations carried a September-10 00:00:39 extraction stamp and no August cell. The dental representation carried a June-28 stamp and only May data. These are limitations of the retrieved representations, not proof that the live BLS database failed. None is a fresh August component receipt merely because the PPI headline is published.

Parent-read primary endpoints: [physician](https://data.bls.gov/timeseries/pcu621111621111), [general medical/surgical hospital](https://data.bls.gov/timeseries/pcu622110622110), [nursing](https://data.bls.gov/timeseries/pcu623110623110), [dental](https://data.bls.gov/timeseries/pcu621210621210). An index base date is not a complete historical-vintage audit.

The canonical actuals repository snapshot had 12 rows, 12570 bytes and SHA256 `51996c0f016fbcf57f1de57d8164d645c04884247deb6687aba517ab7f1db84f`; its latest observed release was September-4 payrolls. Absence of today's PPI from this nightly copy does not prove a live-watcher failure. A direct served-artifact read was safety-blocked and not retried, so current served bytes and runtime health remain unverified.

## 5. Local executable reference: what was actually tested

The sandbox reference contains a pure standard-library context projection, bilingual Node/browser renderer, reduced/synthetic fixtures, six reference cases, and a standalone preview. It consumes a caller-supplied **already resolved first-print view from the existing actual owner**, never raw unadjudicated JSONL. Shape checks are display constraints, not a new publisher or correction validator.

It distinguishes same-reference-month CPI/PPI/PCE dependencies, headline publication stage, detailed component readiness, whether publication follows the old forecast snapshot, and announced method risk. Missing/conflicting data remain explicit. A model snapshot after publication does not prove inclusion. A method notice does not select a model or confirm implementation. No new PCE point, quantile, confidence, Fed-action probability or trade authority is produced.

Local evidence: **82 Python tests, 25 Node renderer tests, 16 Chromium cases passed.** Discriminating RED results preceded initial implementation and later clock/type/method/renderer hardening. Seeded permutations and future-clock probes are included. Browser cases cover dark/light × EN/ZH × 1440/768/390 plus unavailable, conflict, stale and reduced repository-shape states; keyboard detail controls, overflow and absence of fabricated forecasts were checked.

Environment: Python 3.13.5, Node 22.16.0, installed Chromium 144.0.7559.96. Browser proof is a direct mount of session-authored bytes, not existing-page integration or production. Local file navigation was administratively blocked; no policy was changed. The installed Chromium was used after the separate Playwright-managed browser was absent. Mobile light EN/ZH and desktop dark screenshots were visually inspected.

Exact local code identities, **not published in this PR**:

| File | Git blob | SHA256 |
|---|---|---|
| reference.py | 770e87763ba4c60d1ccb5c0aef1bf054f9a51f42 | fd596aac0793c1635f78eb445a140d7c00bd70d0dd8f7173d132a3bb5ce7b458 |
| renderer.cjs | a6d8fe9d91ef068faebd17dcd8046621e9fc328b | 0bd2667482256a2c74fdbe058d69edad8994fa7d99b86efc036b6c4d3b3919e4 |
| tests/test_context.py | 0c62ac785937b9fc970acdb135c1e845ba6d37bb | fe581f40416acac69f5ec4fead6ef86a141682552c91dcdd28a7dd1339b8ea0f |
| tests/test_renderer.cjs | b7802c8d4e12a0fe1877dee5f6726bb05bfd7fdd | ad42cf8f670006758ec479d5d7975207a87221ed1ede5d390643b44c3919c6f2 |

The source/test/preview files remain local to the current sandbox at `/mnt/data/pce_bridge_reference/`. The failed publication means a fresh repository-only session cannot assume access to their bytes. This is a visible recovery gap, not a reason to copy the code through an alternate writer after the safety refusal.

## 6. Existing consumer integration, not another product

`engine/inflation_intelligence.py` at the inspected pin, blob `5c5decc9e6e359924a0f20485826b43026056971`, currently composes CPI released/next/current-pressure blocks. Its CPI filter does not create PCE context. Existing Neural Web consumers are `cortex.py` (`read_inflation_intelligence`), `world_state.py`, `mastermind_context.py` and `ask_brain.py`; their authority-false and bounded-output tests already exist in `tests/test_inflation_intelligence_nw.py`.

The actual user entry is the Events dialog's **inline Release Radar**, not only the offscreen standalone Radar panel. P1 must wire that consumer and the existing inflation-intelligence machine path from the same owner-resolved context. Do not create a second calendar, public forecast JSON, model store, generic actual selector, tool whitelist or AI service.

A1 source compatibility was requested at `1789051124.775359` on its existing root `1788590913.182019`; no later owner answer was visible at the last delta read. That question is not an A1 redelivery, restart, takeover or new source order. F1's retained continuation is not reissued. Preserve #6593's workstream record, #6870's records, Macro Command shared UI and #7017 Policy Watch recovery.

## 7. Exact next action and still-open gates

The next independently useful capability is **same-month release context and measurement-risk explanation through the existing calendar and machine consumers**, while retaining the old numerical forecast and its true cutoff. It does not require full quantitative calibration, but it does require the correct existing-owner actual view, release-day display retention and compatible shared source/UI seams.

Obtain a finite owner-compatible P1 implementation boundary, including the due-day retention versus new-forecast-admission tests; then place one bounded worker through the existing capacity path. No new worker is assigned by this evidence document. Numerical core-PCE shadow, headline extension and subsequent release-triggered recomputation remain separately preregistered later verticals.

Current PR #7031 remains Draft/HOLD. At the latest check, fences completed successfully, ci run 34485040569 remained queued, and the combined status contained Vercel build-rate-limit failure. These are not green full CI or a semantic rejection of the PCE research. No check was dismissed, no spending upgrade or workflow rerun occurred, and nothing was merged/deployed.

Completion still requires real canonical input through the real publication path, matching browser and machine results, correction/replay/degraded-state proof, and prospective learning. This research/reference checkpoint is not that completion.
