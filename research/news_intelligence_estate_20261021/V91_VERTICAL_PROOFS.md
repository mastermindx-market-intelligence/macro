# §9.1 vertical proofs: what runs, what it shows, what is missing

News Intelligence Estate, 2026-11-02. This page reports the seven vertical proofs required by `research/news_intelligence_estate_20261021/MASTERPLAN.md:467`. It is the same file in each of the seven proof pull requests.

## How the proofs work

Each vertical has one script under `research/news_intelligence_estate_20261021/v91_proofs/`, plus a sibling `.expected` file. The script calls the repository's own producers on offline inputs. It prints one verdict line per property and then one SUMMARY line. It uses no network and no model call, and it writes only under its `--scratch` directory.

`tests/test_v91_vertical_proofs.py` runs each script twice with sockets refused and credential-shaped environment variables removed. It requires:

- identical output on both runs, each run under 60 seconds;
- verdict counts that match the SUMMARY line;
- a rung equal to the best rung reachable without a human;
- every cited `path:line` names an existing file with at least that many lines;
- verdicts equal to the `.expected` file.

A proof whose committed artifact is not checked out, as in a sparse worktree, is skipped. CI runs the module in the `news-v91-vertical-proofs` job.

Each proof script lands in its own pull request, so this page names proof files by path only. Every `path:line` on this page resolves to the same line at the head of each of the seven pull requests.

**What the verdicts mean.**

- **PROVEN**: every named check held. The proof ran the producer end to end at the stated rung and compared it with expectations written in the proof from its own input sentences or from an independent read of the artifact. It is not production proof: no proof signs in, calls a live provider or reads the deployed site.
- **PARTIAL**: some checks held. The line names the ones that did not.
- **ABSENT**: no check held, or the capability does not exist.
- **HUMAN_GATE**: the next step needs a signed-in human session. The proof stops there and, where it can, shows that an unauthenticated caller is refused.

**What the rungs mean.**

- **OFFLINE_FIXTURE**: synthetic or committed test inputs pass through the repository producers.
- **COMMITTED_ARTIFACT**: the proof reads a tracked data or site artifact on main.

No property reaches a signed-in or live rung.

## Summary

| Vertical | Properties | Proven | Partial | Absent | Human gate | Rung |
|---|---|---|---|---|---|---|
| V1 Macro release and revision | 8 | 2 | 4 | 1 | 1 | COMMITTED_ARTIFACT |
| V2 Earnings/guidance | 6 | 0 | 6 | 0 | 0 | OFFLINE_FIXTURE |
| V3 Capital allocation or major contract | 7 | 1 | 4 | 2 | 0 | OFFLINE_FIXTURE |
| V4 Policy or supply-chain event | 5 | 0 | 4 | 1 | 0 | COMMITTED_ARTIFACT |
| V5 Rumor, denial, confirmation | 6 | 2 | 3 | 0 | 1 | OFFLINE_FIXTURE |
| V6 User research workflow | 7 | 2 | 1 | 3 | 1 | OFFLINE_FIXTURE |
| V7 Quiet, outage, rights loss | 9 | 5 | 2 | 1 | 1 | OFFLINE_FIXTURE |
| Total | 48 | 12 | 24 | 8 | 4 | |

No vertical is complete. Twelve of 48 properties are proven offline.

- Five of the 12 proven properties are in V7, the rights and outage behaviour of the ticker news API.
- The consumer halves of the masterplan rows are mostly missing:
  - the Brain answer does not read the release radar (V1 P7);
  - no page renders a news_impact scenario (V3 P6);
  - the AI evidence bundle does not carry the degraded state (V7 P7);
  - no route saves or follows research (V6 P4).
- Four properties stop at a signed-in human gate.

## V1 Macro release and revision

**Proof.** `research/news_intelligence_estate_20261021/v91_proofs/v1_macro_release_revision.py`.

**Rung.** COMMITTED_ARTIFACT. It reads `data/fred_vintage/release_targets/PAYEMS_all_vintages.parquet` and `data/fred_vintage/release_targets/CPIAUCSL_all_vintages.parquet`, both git-tracked, not LFS.

| Property | Proof line | Rung | Gap |
|---|---|---|---|
| P1 Exact release, period and units; first print versus later revision | PROVEN. PAYEMS 2026-05 released 2026-06-05: the producer gives +172.0k (thousands). That equals an independent read of the same vintage taken straight from the parquet; the latest vintage gives +63.0k. CPIAUCSL 2025-09: 0.3105% at release versus 0.2951% latest. `engine/release_target_truth.py:194`, `tests/test_release_target_truth.py:108` | COMMITTED_ARTIFACT | None at this rung. |
| P2 Prior level taken from the release vintage, in both radar and news | PARTIAL. Radar half observed: the prior level 158829.0 is the release-vintage row, distinct from the prior first print and the latest value. `engine/release_target_truth.py:194` | COMMITTED_ARTIFACT | The news half reads only the latest revised FRED level over the network (`engine/macro_surprise.py:8`), so it cannot be exercised offline. |
| P3 Dated expectation or honestly labelled alternative benchmark | PROVEN. On a synthetic Kalshi ladder with an older 0.12 row and a fresh 0.30 row, the producer returns source=kalshi implied_median=0.30 with the fresh as-of stamp. With the parquet missing it returns None, and no expectation is invented. `engine/release_market_context.py:331`, `tests/test_release_market_context.py:534` | OFFLINE_FIXTURE | The ladder is a synthetic parquet written to scratch, not a committed market snapshot. |
| P4 No fabricated consensus | PARTIAL. The market check labels its benchmark and emits no consensus. But a synthetic 'consensus/共识' string passes through the inflation row unchanged. `engine/rates_inflation_command.py:18`, `engine/rates_inflation_command.py:1432`, `tests/test_release_radar_render.py:124` | OFFLINE_FIXTURE | No runtime guard exists. The ban rests on a docstring and a render test. |
| P5 Later revision retained | PARTIAL. PAYEMS 2026-05 keeps three distinct vintage values with their validity windows. `engine/release_target_truth.py:163`, `tests/test_release_target_truth.py:339` | COMMITTED_ARTIFACT | The news path keeps only the latest revised level, so revisions are retained on the radar side only. |
| P6 Macro explanation and sector context agree | PARTIAL. Radar targets come from `scripts/build_release_forecast.py:2269`; news reads its surprise through `scripts/build_news.py:340`. | COMMITTED_ARTIFACT | The two paths share no target and no agreement artifact. |
| P7 Brain answer agrees | ABSENT. None of the 59 app modules reads release_forecast. The nearest Brain run code is `app/brain_runs.py:214`; the only consumer is the signed-in browser fetch at `templates/dashboard.html.j2:11546`. | none | No Brain path reads the radar. |
| P8 Signed-in radar read | HUMAN_GATE. `/macrodata/` is gated at `config/site_access.yml:714`. `tests/test_release_radar_render.py:157` | HUMAN_GATE | Needs a signed-in session. |

## V2 Earnings/guidance

**Proof.** `research/news_intelligence_estate_20261021/v91_proofs/v2_earnings_guidance.py`.

**Rung.** OFFLINE_FIXTURE. The inputs are:

- the committed earnings fixtures (a synthetic CIK release and its amendment);
- the P&G and Apple company-intelligence exhibits;
- synthetic release sentences written in the proof.

| Property | Proof line | Rung | Gap |
|---|---|---|---|
| P1 Issuer and listing identity | PARTIAL, 6 of 8 checks. An explicit CIK wins over the ticker. `engine/news_impact/issuer.py:339`, `engine/company_intelligence/event_workspace_build.py:181`, `tests/test_news_impact_issuer.py:151` | OFFLINE_FIXTURE | A CIK/listing conflict is not surfaced, and a foreign filing CIK is neither refused nor warned. |
| P2 Fiscal period and basis match | PARTIAL, 7 of 8. GAAP 2.18 and non-GAAP 2.51 bind to one period end; the guidance label is kept. `engine/earnings_release/figures.py:883`, `tests/test_earnings_release_binding.py:262` | OFFLINE_FIXTURE | When three-month and twelve-month tables end on the same day, revenue is refused as value_ambiguous instead of binding both. |
| P3 Output keeps period and basis | PARTIAL, 6 of 8. `engine/news_impact/validate.py:1154`, `engine/news_impact/prophet_adapter.py:453`, `tests/test_news_impact_producer_facts.py:752` | OFFLINE_FIXTURE | A full-year claim carrying a Q3 amount validates. EPS 2.18 renders as '2.2 USD/share' in both English and Chinese, so the cents are lost. |
| P4 Actual, expected and prior guide separated | PARTIAL, 4 of 9. `engine/earnings_release/figures.py:137`, `engine/earnings_release/figures.py:744`, `contracts/news_impact/news_impact_event.v1.schema.json:1739`, `tests/test_earnings_release_binding.py:348` | OFFLINE_FIXTURE | A consensus sentence binds as the company's guide. A prior-outlook clause binds as new guidance. The baseline carries no value, and the leaf and reader drop the prior amount. |
| P5 Source correction invalidates derivatives | PARTIAL, 6 of 9. An 8-K/A collapses to one event with two revisions (EPS 2.18 to 2.78), and the workspace state becomes corrected. `engine/earnings_release/binding.py:301`, `engine/news_impact/cluster.py:453`, `tests/test_earnings_release_binding.py:507` | OFFLINE_FIXTURE | The workspace does not keep the superseded value. The producer records the corrected figure as a new fact revision that supersedes nothing. No news_impact module reads the release correction. |
| P6 Ticker and catalyst explain the change and what is unknown | PARTIAL, 4 of 6. The Apple glance moves from $109.4B to $110.4B with state corrected; coverage names unlicensed consensus. `app/company_intelligence.py:464`, `engine/news_impact/thesis.py:940`, `tests/test_company_intelligence_event_workspace.py:763` | OFFLINE_FIXTURE | A profile metric correction does not reach the glance. The thesis does not state amount and direction. |

## V3 Capital allocation or major contract

**Proof.** `research/news_intelligence_estate_20261021/v91_proofs/v3_capital_contract.py`.

**Rung.** OFFLINE_FIXTURE. The inputs are synthetic news_impact events and an offline HKEX listing page read through a stub transport.

| Property | Proof line | Rung | Gap |
|---|---|---|---|
| P1 Authorised versus executed amount | PARTIAL. Authorisation 500,000,000 and executed 120,000,000 are kept apart through the mapping and producer facts. `engine/news_impact/mechanisms.py:961`, `engine/news_impact/producer_facts.py:287`, `tests/test_news_impact_producer_facts.py:258` | OFFLINE_FIXTURE | Nothing ties a role to its own quote. A swapped role validates, and the reader prints '$500 million bought'. |
| P2 Contract ceiling versus recognised economics | PROVEN. A firm 400M order with a 2B option ceiling yields stated bookings of 400M only. The ceiling is never summed and never shown as an amount. A ceiling-only event yields no quantity. `engine/news_impact/mechanisms.py:961`, `engine/news_impact/prophet_adapter.py:98`, `tests/test_news_impact_mechanisms.py:825` | OFFLINE_FIXTURE | The ceiling is dropped rather than shown as a labelled ceiling. |
| P3 Timing and conditions preserved | PARTIAL. A missing commitment status is refused. A grounded condition reaches the producer, the reader copy and the hover. `engine/news_impact/validate.py:1154`, `engine/news_impact/prophet_adapter.py:958`, `tests/test_news_impact_validate.py:677` | OFFLINE_FIXTURE | A conditions quote found in no evidence span still validates; no grounding check exists. |
| P4 Deterministic scenario with assumptions | PARTIAL. The duration scenarios are identical on repeat calls and carry no weights. `engine/news_impact/mechanisms.py:860`, `tests/test_news_impact_mechanisms.py:804` | OFFLINE_FIXTURE | No stated assumption can be changed. This vertical's own buyback and contract events produce no duration scenario. |
| P5 No automatic EPS or price target | PARTIAL. Structured price_target and rating fields are stripped and refused. `engine/news_impact/mechanisms.py:333`, `engine/news_impact/prophet_adapter.py:189`, `tests/test_news_impact_f2_text_safety.py:174` | OFFLINE_FIXTURE | The phrase gate covers glance copy only. 'price target of 250' and 'we rate it a buy' reach the hover. |
| P6 Consumer renders the scenario | ABSENT. No app, template or builder file names a news_impact scenario. The nearest reader, `scripts/build_ticker_pages.py:2363`, shows the ticker capital_allocation blob. | none | No user-facing consumer. |
| P7 Non-US variant (Hong Kong buyback) | ABSENT. The HKEX collector parses two rows offline but requests the English listing only. Amounts survive only in the title text. A news_impact event for this issuer is refused because company_id must be a SEC CIK. `collectors/hk_hkexnews.py:169`, `collectors/hk_hkexnews.py:221`, `contracts/news_impact/news_impact_event.v1.schema.json:68`, `tests/test_hk_filing_bus.py:109` | OFFLINE_FIXTURE | A non-US issuer cannot enter news_impact. |

## V4 Policy or supply-chain event

**Proof.** `research/news_intelligence_estate_20261021/v91_proofs/v4_policy_supply_chain.py`.

**Rung.** COMMITTED_ARTIFACT. It reads `site/basketdata/foresight_cascade.json` and `site/foresight.html`. The nightly render rewrites both files, so the evidence text moves with each render.

The verdicts were checked against the 75c68c5f base copies and against the 2026-11-02 render on main (b394a98b). They were the same both times. A render that changes a verdict fails the test and needs a reviewed `.expected` update.

| Property | Proof line | Rung | Gap |
|---|---|---|---|
| P1 Report, proposal, final and effective states distinct | PARTIAL. Synthetic Federal Register documents keep four distinct stages. `collectors/federal_register.py:107`, `engine/policy_calendar.py:146`, `tests/test_policy_calendar.py:246` | OFFLINE_FIXTURE | The next effective date takes the comment-close date as a proxy (2026-11-20 instead of 2026-12-15). |
| P2 Sourced, dated product and company exposure | PARTIAL. 17 of 18 committed theme rows carry a policy chip. `engine/foresight_cascade.py:669`, `scripts/build_foresight.py:332` | COMMITTED_ARTIFACT | The chips have no per-company, product or source members; dates and titles exist at theme level only. |
| P3 Alternatives and falsifiers | ABSENT. A recursive scan of the committed cascade finds no alternative or falsifier member. `engine/foresight_cascade.py:602` | COMMITTED_ARTIFACT | Policy text folds into the rationale as an assertion. |
| P4 Contract carries the policy condition | PARTIAL. Policy classes exist in the event enum, and the award-policy rule fires only on a policy class. `contracts/news_impact/news_impact_event.v1.schema.json:1577`, `contracts/news_impact/channel_library.v1.json:1099`, `engine/news_impact/mechanisms.py:961`, `tests/test_news_impact_mechanisms.py:458` | OFFLINE_FIXTURE | The event has no lifecycle stage, and a policy_stage field is refused. |
| P5 Theme and MarketOntology show a conditional mechanism | PARTIAL. The committed page has 17 policy pipeline lines with no causal verbs and no conditional markers. `scripts/build_foresight.py:340`, `engine/market_ontology/exposure_map.py:19` | COMMITTED_ARTIFACT | No MarketOntology consumer reads the policy lane, and the panel asserts lead time once. |

## V5 Rumor, denial, confirmation

**Proof.** `research/news_intelligence_estate_20261021/v91_proofs/v5_rumor_denial_confirmation.py`.

**Rung.** OFFLINE_FIXTURE. Synthetic stories go through the news store, the reducer and the thesis lane.

| Property | Proof line | Rung | Gap |
|---|---|---|---|
| P1 Original report stays versioned | PROVEN. Both revisions are retained, the v1 title is intact and v2 is current. An identical replay inserts nothing. `engine/qbus_news_store.py:242`, `engine/qbus_news_store.py:260`, `engine/qbus_news_reducer.py:189`, `tests/test_qbus_news_store.py:177` | OFFLINE_FIXTURE | None at this rung. |
| P2 Independent confirmation recognised | PARTIAL. A confirmation from an unseen group triggers new_independent_source, and a same-group reprint does not. `engine/news_impact/thesis.py:1608`, `engine/news_impact/producer_facts.py:401`, `tests/test_news_impact_thesis.py:1034` | OFFLINE_FIXTURE | A producer-shaped reprint carries its own document as its origin, so it counts as independent. No non-test module names a wire provenance family. |
| P3 Copied wires do not inflate corroboration | PARTIAL. The store counts an identical wire across two outlets as one source. `engine/qbus_news_quality.py:97`, `engine/news_impact/thesis.py:882`, `tests/test_shared_news_intelligence.py:1242` | OFFLINE_FIXTURE | A copy with an edited headline counts as a second source, and so does a producer-shaped reprint in the thesis lane. |
| P4 Denial stays versioned as a denial | PARTIAL. In the thesis lane, a contrary revision linked to the rumor triggers contradiction. `engine/news_events.py:303`, `engine/news_impact/thesis.py:1606`, `tests/test_news_impact_thesis.py:627` | OFFLINE_FIXTURE | The news lane has no denial class among its 23 event classes, and the store keeps the denial as a plain active item. In the thesis lane the rumor still counts as supporting after the denial. |
| P5 Current view and historical replay differ | PROVEN. Replay as of the earlier time shows only the rumor title; the current read shows v2. Flow counts are bound to possession time. `engine/qbus_news_store.py:2197`, `engine/qbus_news_velocity.py:303`, `tests/test_qbus_news_velocity.py:1270` | OFFLINE_FIXTURE | The proof applies the as-of cut itself, because the API reader takes no as-of time (`app/ticker_news.py:912`). |
| P6 Signed-in view of the versioned story | HUMAN_GATE. `/news/` is listed at `config/site_access.yml:712` under tier free_registered (`config/site_access.yml:687`). | HUMAN_GATE | Needs a signed-in session. |

## V6 User research workflow

**Proof.** `research/news_intelligence_estate_20261021/v91_proofs/v6_user_research_workflow.py`.

**Rung.** OFFLINE_FIXTURE for what exists offline. The signed-in step is HUMAN_GATE. Save, follow and propose are ABSENT.

| Property | Proof line | Rung | Gap |
|---|---|---|---|
| P1 Read a source | PROVEN. With a licensed receipt, the API read returns 200 and one row. An unknown-source receipt returns no rows; with no receipt the read returns 503. `app/ticker_news.py:341`, `engine/qbus_news_store.py:1758`, `tests/test_ticker_news_api.py:140` | OFFLINE_FIXTURE | None at this rung. |
| P2 Signed-in persistence and authorization | HUMAN_GATE. An unauthenticated read gets 401 'missing bearer token'. `app/main.py:1030`, `app/ticker_news.py:195` | HUMAN_GATE | Needs a signed-in session. |
| P3 Inspect company and theme | PROVEN. A member resolves to its theme exposure. A removed member and a non-member resolve to none. The integrated answer reports ok and absent accordingly. `app/integrated_answer.py:730`, `engine/company_theme_exposure/views.py:217`, `tests/test_company_theme_exposure.py:94` | OFFLINE_FIXTURE | None at this rung. |
| P4 Save or follow | ABSENT. None of the 43 handlers saves or follows a source or theme. The nearest handlers are `app/account_prefs.py:132`, `app/catalyst_integration.py:455`, `app/main.py:2239` and `app/ontology_explorer.py:330`; the cockpit row at `research/news_intelligence_estate_20261021/MASTERPLAN.md:77` places follow in open Macro #9612. | none | Missing capability. |
| P5 Propose a thesis change through the existing user owner | ABSENT. The thesis lane has no propose path. `engine/news_impact/thesis.py:569`, `engine/news_impact/thesis.py:660` | none | Missing capability. |
| P6 No second thesis or alert store | PARTIAL. A source scan finds no table named thesis or alert, and the standing kill at `engine/news_impact/thesis.py:8` declares no mutable thesis object. | OFFLINE_FIXTURE | Absence by source scan is not a runtime proof. |
| P7 Correction after save | ABSENT. The proof observes a correction in the store (`engine/qbus_news_reducer.py:166`), but no saved research exists to receive it. | none | No end-to-end path; see the next section. |

## V7 Quiet, outage, rights loss

**Proof.** `research/news_intelligence_estate_20261021/v91_proofs/v7_quiet_outage_rights.py`.

**Rung.** OFFLINE_FIXTURE. The proof runs synthetic receipts and a scratch SQLite store through the ticker news API, with the dependency check stubbed except in P9.

| Property | Proof line | Rung | Gap |
|---|---|---|---|
| P1 Quiet versus outage | PARTIAL. A live receipt with no rows gives quiet, and an unavailable one never gives quiet. `engine/qbus_news_receipts.py:306`, `app/ticker_news.py:408`, `tests/test_ticker_news_api.py:279` | OFFLINE_FIXTURE | The nightly RSS path returns the same empty result for an outage and an empty feed, with no per-source record (`engine/news_rss.py:256`, `research/news_intelligence_estate_20261021/A5_TRANSPORT_OBSERVABILITY_GAPS.md:39`). |
| P2 Stale data | PROVEN. The receipt ladder runs fresh to live, a stale receipt to unavailable and a stale catch-up to degraded. A future observation is refused. Additional sources are age-projected. `engine/qbus_news_receipts.py:306`, `app/ticker_news.py:380`, `tests/test_qbus_news_receipts.py:146` | OFFLINE_FIXTURE | None at this rung. |
| P3 Missing history | PROVEN. 26 days gives ok. 3 days and 0 days give thin_history. No access gives unavailable. `engine/qbus_news_store.py:1985`, `app/ticker_news.py:473`, `tests/test_qbus_news_flow_store.py:577` | OFFLINE_FIXTURE | None at this rung. |
| P4 Access withdrawal | PROVEN. A revoked or expired receipt returns 503 with its rights code. A mid-stream revoke ends the SSE stream after a restricted event. `engine/qbus_news_receipts.py:128`, `app/ticker_news.py:614`, `tests/test_ticker_news_end_to_end.py:287` | OFFLINE_FIXTURE | None at this rung. |
| P5 No stale protected content | PROVEN. Responses are private and no-store. A withdrawn response keeps the header and carries no protected keys. `app/ticker_news.py:70`, `tests/test_ticker_news_api.py:87` | OFFLINE_FIXTURE | None at this rung. |
| P6 Honest degraded API | PROVEN. A missing database gives 503; an empty store gives 200 quiet. `app/ticker_news.py:273`, `tests/test_ticker_news_api.py:194` | OFFLINE_FIXTURE | None at this rung. |
| P7 Honest degraded AI output | ABSENT. The AI evidence bundle has no degraded or health member and reports available even for a quiet store. `engine/qbus_news_context.py:35`, `engine/press/qbus_news.py:219`, `tests/test_shared_news_intelligence.py:426` | none | No model-facing reader reads the health receipt. |
| P8 No duplicate work on recovery | PARTIAL. A backlog replay after an outage inserts nothing. The provider stamp is enforced. `engine/qbus_news_store.py:1090`, `engine/qbus_news_store.py:260`, `tests/test_qbus_news_store.py:177`, `research/news_intelligence_estate_20261021/F2_RIGHTS_IDENTITY_NEGATIVE_CONTROLS.md:52` | OFFLINE_FIXTURE | Model calls are not coalesced (`research/news_intelligence_estate_20261021/F2_MODEL_CONTEXT_NEGATIVE_CONTROLS.md:54`). The press run's token cap and single attempt (`scripts/run_press.py:908`, `scripts/run_press.py:921`) are not exercised here. |
| P9 Signed-in live endpoint | HUMAN_GATE. An unauthenticated call gets 401 'missing bearer token' before any store opens. `app/ticker_news.py:195`, `app/ticker_news.py:200`, `tests/test_ticker_news_api.py:106` | HUMAN_GATE | Needs a signed-in paid session. |

## Cross-vertical requirements

`research/news_intelligence_estate_20261021/MASTERPLAN.md:479` asks for two unrelated domains beyond the optics reference case. It also asks for non-US and cross-language examples, with coverage declared rather than assumed.

### Domains beyond optics

No proof uses the optics case. The proofs cover these domains:

| Domain | Vertical | Inputs |
|---|---|---|
| US macro statistics | V1 | PAYEMS and CPIAUCSL vintages |
| US issuer filings | V2 | A synthetic CIK release and its amendment, plus P&G and Apple exhibits |
| Buyback and contract facts | V3 | Synthetic news_impact events |
| US federal regulation | V4 | Federal Register stages and the committed foresight cascade |
| Merger and acquisition rumor | V5 | Synthetic stories |
| News transport and rights | V7 | Synthetic receipts and a scratch store |

Macro statistics and federal regulation are unrelated to optics and to each other. The two-domain requirement is therefore met at the offline-fixture and committed-artifact rungs, not live.

### Non-US and cross-language coverage, declared

| Surface | Declared coverage | Evidence |
|---|---|---|
| Hong Kong buyback announcements | Collected offline, English listing only. Amounts appear only in title text. The issuer cannot enter news_impact because company_id must be a SEC CIK. | V3 P7 ABSENT. `collectors/hk_hkexnews.py:169`, `contracts/news_impact/news_impact_event.v1.schema.json:68` |
| Chinese HKEX titles | Kept verbatim when supplied. The collector never requests the Chinese listing. | V3 P7. `collectors/hk_hkexnews.py:221` |
| Chinese reader output | The per-share amount renders the same string in Chinese as in English and drops the cents. | V2 P3. `engine/news_impact/prophet_adapter.py:453` |
| Chinese consensus label | 'consensus/共识' passes through the inflation row with no runtime guard. | V1 P4. `engine/rates_inflation_command.py:1432` |
| Chinese news path | The `/chinanews/` prefix exists at `config/site_access.yml:713`. | Not exercised by any proof. |

**Declaration.**

- Non-US coverage is Hong Kong only. It is reached at OFFLINE_FIXTURE and is ABSENT end to end.
- Chinese appears in four places, none of which is a declared per-language coverage. No committed per-language coverage declaration exists, so translation support is not evidence of coverage.
- This cross-vertical requirement is PARTIAL.

### Correction after save

The masterplan (`research/news_intelligence_estate_20261021/MASTERPLAN.md:481`) requires a correction that arrives after an assessment is saved. That is **ABSENT end to end** (V6 P7).

The correction mechanisms exist offline:

- the store retains revisions (V5 P1, `engine/qbus_news_store.py:242`);
- an 8-K/A collapses into one event with two revisions (V2 P5);
- the thesis lane reduces magnitude on a source correction (`engine/news_impact/thesis.py:1297`).

Nothing in the product saves or adopts an assessment that a correction could reach (V6 P4).

## Documentation drift found while proving

- **Stale-data row.** The readiness map row at `research/news_intelligence_estate_20261021/V91_VERTICAL_PROOF_READINESS.md:145` says additional sources carry no writer observation age. That claim rests on A5 G2 (`research/news_intelligence_estate_20261021/A5_TRANSPORT_OBSERVABILITY_GAPS.md:40`). Current code does age-project them (`engine/qbus_news_receipts.py:359-364`): the source is unavailable when the receipt is stale, and degraded when its last poll is missing or older than 300 seconds. V7 P2 observes this, so the readiness row and G2 are stale.
- **Save-or-follow row.** The row at `research/news_intelligence_estate_20261021/V91_VERTICAL_PROOF_READINESS.md:128` cites handler lines that have since moved. The current lines are those given in V6 P4; the catalyst opt-in, for example, is now `app/catalyst_integration.py:455`.
- **Cross-vertical section.** That section of the readiness map cites `engine/news_impact/thesis.py` line 1481 for the correction mechanism, which now sits at `engine/news_impact/thesis.py:1297`.
- **Readiness summary.** The table at `research/news_intelligence_estate_20261021/V91_VERTICAL_PROOF_READINESS.md:176` inventoried producer surfaces before these proofs. For proof status, this page supersedes it; for example, V7 has 9 properties here and 8 there.

None of these documents is edited by the proof pull requests.

## Limits

- **Nothing here is production proof.** The four HUMAN_GATE properties (V1 P8, V5 P6, V6 P2, V7 P9) need a signed-in human session.
- **V1 P3** rests on a synthetic parquet written to scratch.
- **V4** reads nightly-rendered site artifacts.
- **Producer defects.** The PARTIAL and ABSENT lines above record producer defects as gaps, among them V2 P3, V2 P4, V3 P1, V3 P3, V3 P5 and V7 P7. Each proof script reproduces its gap: run it with `--scratch <dir>` and read the property line. No producer code is changed by these pull requests.
- **What PROVEN does not rest on.** No PROVEN line compares the producer with its own output. V1 P1 compares the producer with a direct read of the parquet. The other PROVEN lines compare the producer with values the proof writes into its own synthetic inputs.
