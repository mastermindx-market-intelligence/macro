# §9.1 vertical proof readiness — News Intelligence Estate (2026-11-01)

## Scope and sources

This is an evidence map, not a proof, an acceptance or a design. It takes the seven
vertical rows of masterplan §9.1 (`research/news_intelligence_estate_20261021/MASTERPLAN.md:469-477`)
and records, for each required property, what exists on main today: the producer, the
artifact it persists, the surface that consumes it, the access class of that surface,
and the test that exercises it.

- **Base.** main `044d1cc63923c27318640219b150b757a4855118`. Every `path:line` resolves at
  that commit unless it is marked F2.
- **F2.** The three negative-control documents at commit
  `eaa60ce27fa685328ab0fee333441313f27d7172` (pending PR, not yet on main), read with
  `git show eaa60ce2:<path>`. They are abbreviated F2-R (`F2_RIGHTS_IDENTITY_NEGATIVE_CONTROLS.md`),
  F2-T (`F2_TIME_CORRECTIONS_NEGATIVE_CONTROLS.md`) and F2-M (`F2_MODEL_CONTEXT_NEGATIVE_CONTROLS.md`),
  all under `research/news_intelligence_estate_20261021/`.
- **Access classes** come from `config/site_access.yml`. The free_registered prefixes
  `/news/` (:712), `/chinanews/` (:713) and `/macrodata/` (:714) are SIGNED_IN. Every data
  path not named under `public` is gated (:24). HTML shells listed under `public` (:68) are ANON.
- **Status** grades the producer and its test: PRESENT_WITH_TEST, PRESENT_NO_TEST, PARTIAL,
  ABSENT. Consumer reach is recorded separately in the consumer column.
- **Rungs:** OFFLINE_FIXTURE, COMMITTED_ARTIFACT, ANON_DEPLOYED, SIGNED_IN_HUMAN_GATE, NONE.
- **Populations** stay separate and are not used as exemplars here: 600 registered,
  v2 74 scorable, v3 135 drawn, 40 routing-pending, 0 prospective.

## V1 Macro release and revision

§9.1 row (`MASTERPLAN.md:471`), quoted:
- Required observed behaviour: "Exact release/period/units, first-print versus revision, dated expectation or honestly labelled alternative benchmark; later revision retained"
- Consumer outcome: "Macro explanation, sector exposure context and Brain answer agree; no fabricated consensus"

| Required property | Producer (path:line) | Persisted artifact | Consumer surface | Test | Status |
|---|---|---|---|---|---|
| Exact release, period and units | `engine/release_target_truth.py:194` reconstruct_release_target over ALFRED full-vintage data (:1) | `data/fred_vintage/release_targets/{CPIAUCSL,CPILFESL,PAYEMS,PCEPILFE,PCEPI,PPIFES}_all_vintages.parquet`, tracked, written by `scripts/collect_release_target_vintages.py:1` | Release radar `templates/dashboard.html.j2:9522`, fetch at :11546 of `site/macrodata/release_forecast.json` (`scripts/build_release_forecast.py:48`); SIGNED_IN via `config/site_access.yml:714` | `tests/test_release_target_truth.py:108` (PAYEMS exact +57 thousand), :84 | PRESENT_WITH_TEST |
| First print versus revision | `engine/release_target_truth.py:202` current and prior levels from the same vintage; `engine/release_revision_model.py:1` covers NFP only | same parquet set | Radar as above. The news path uses `engine/macro_surprise.py`, whose PIT caveat (:8) says FRED serves latest revised values; consumed at `scripts/build_news.py:340` and `engine/news_common.py:438` | `tests/test_release_target_truth.py:45`, :137, :170 | PRESENT_WITH_TEST on the radar; PARTIAL on the news path |
| Dated expectation or labelled alternative benchmark | `engine/release_market_context.py:1-11`, display-only market context with no LLM | `site/macrodata/release_forecast.json` (`scripts/build_release_forecast.py:5`) | Radar, SIGNED_IN (:714) | `tests/test_release_market_context.py:534` | PRESENT_WITH_TEST |
| No fabricated consensus | `engine/rates_inflation_command.py:18-19` bans the word "consensus" from all strings, EN and ZH (MRI-R5), and prescribes "benchmark" as the labelled wording | same JSON | Radar, SIGNED_IN | `tests/test_release_radar_render.py:124` | PRESENT_WITH_TEST |
| Later revision retained | All-vintage parquet files; a failed collection leaves the prior cohort | parquet set | Radar shows the reconstructed target; the news path reads latest revised values (`engine/macro_surprise.py:8`) | `tests/test_release_target_truth.py:339` | PARTIAL |
| Macro explanation, sector context and Brain agree | Radar provenance `engine/release_provenance.py:1`; radar imports release_target_truth at `scripts/build_release_forecast.py:2269`, the news path does not | none shared | No module under `app/` reads `release_forecast` | none | PARTIAL for radar against news; ABSENT for Brain |

Exemplar: `tests/test_release_target_truth.py:45` (an annual revision discontinuity uses the prior level from the same release vintage).

Best reachable rung without a human: COMMITTED_ARTIFACT. The displayed radar is SIGNED_IN_HUMAN_GATE.

## V2 Earnings/guidance

§9.1 row (`MASTERPLAN.md:472`), quoted:
- Required observed behaviour: "Issuer/listing identity, fiscal period and basis match; actual/expected/prior guide separated; source correction invalidates derivatives"
- Consumer outcome: "Ticker and catalyst assessment explain the real change and what remains unknown"

| Required property | Producer (path:line) | Persisted artifact | Consumer surface | Test | Status |
|---|---|---|---|---|---|
| Issuer and listing identity | `engine/news_impact/issuer.py:1-8` cik ladder with typed absence; filing key in `engine/earnings_release/binding.py` | contract `contracts/news_impact/news_impact_event.v1.schema.json` | NONE in `templates/` or `app/*.py` | `tests/test_earnings_release_binding.py:136` (CIK:ACCESSION key); `tests/test_news_impact_issuer.py:110`, :123, :132 | PRESENT_WITH_TEST |
| Fiscal period and basis match | `engine/earnings_release/figures.py:1-6` (no model, no inference, typed absence), :80; `engine/news_impact/producer_facts.py:53`, :198 keep unit, basis and period | same contract | NONE | `tests/test_earnings_release_binding.py:262`, :399 | PRESENT_WITH_TEST on the deterministic path |
| Basis on the model-output path | F2-M rows on prophet_adapter handling | none | NONE | F2-M:44 M05, :45 M06a, :46 M06b are BROKEN; :48 M07b and :49 M08 are NO_MECHANISM | PARTIAL |
| Actual, expected and prior guide separated | `engine/earnings_release/figures.py:137` guidance sentence pattern; expectations only where `engine/group_earnings.py:108-111` records consensus, which is 715 of 1,976 stored names | none | NONE | `tests/test_earnings_release_binding.py:146` (byte-for-byte replay of bound figures) | PARTIAL |
| Source correction invalidates derivatives | `engine/earnings_release/binding.py:49`, :100, :197, :205 (an amended body is a second revision); `engine/news_impact/thesis.py:1481` corrected_fact with supersedes_fact_id | none | NONE | `tests/test_earnings_release_binding.py:507`; `tests/test_news_impact_thesis.py:1032` | PARTIAL: no committed consumer derivative is invalidated |
| Ticker and catalyst explanation | `engine/earnings_catalyst.py:1`, a date-only display tier | ticker pages | Ticker dossier `site/stocks/<TICKER>.html` (`scripts/build_ticker_pages.py:9`); per-ticker data gated (`config/site_access.yml:23`) | none for change explanation | ABSENT |

Exemplar: `tests/test_earnings_release_binding.py:507` (an amended release body is a second revision of one event).

Best reachable rung without a human: OFFLINE_FIXTURE.

## V3 Capital allocation or major contract

§9.1 row (`MASTERPLAN.md:473`), quoted:
- Required observed behaviour: "Authorised versus executed amount, contract ceiling versus recognised economics, timing and conditions preserved"
- Consumer outcome: "Deterministic scenario with assumptions; no automatic EPS/price target"

| Required property | Producer (path:line) | Persisted artifact | Consumer surface | Test | Status |
|---|---|---|---|---|---|
| Authorised versus executed amount | `contracts/news_impact/news_impact_event.v1.schema.json:1216` primary_amount_role; buyback execution reader `engine/capital_allocation.py:1-12` (display-only); HK buyback source `collectors/hk_hkexnews.py:16`, :36 | contract only for news_impact | news_impact NONE. The capital_allocation reader feeds the ticker dossier (`scripts/build_ticker_pages.py:2363`); whether that block sits in the ANON shell or the gated payload (:23) is not resolved here | `tests/test_news_impact_producer_facts.py:249` | PRESENT_WITH_TEST, no news consumer |
| Contract ceiling versus recognised economics | schema :1736 option_ceiling, :1647 recognized_revenue, :1639 demand_stage | contract | NONE | `tests/test_news_impact_mechanisms.py:825` (option ceiling not summed) | PRESENT_WITH_TEST, no consumer |
| Timing and conditions preserved | schema :93 commitment_status, :1261 conditions_quote | contract | NONE | `tests/test_news_impact_contracts.py:189` (commitment_status is critical in all three templates); `tests/test_news_impact_validate.py:662` (conditions_quote is validated) | PRESENT_WITH_TEST, no consumer |
| Deterministic scenario with assumptions | `engine/news_impact/mechanisms.py:859` assemble_duration_scenarios, with no weights | none | NONE | `tests/test_news_impact_mechanisms.py:804` | PRESENT_WITH_TEST, no consumer |
| No automatic EPS or price target | Forbidden-key gates; `engine/special_situations.py:34` SCORED = False | none | NONE | `tests/test_news_impact_contracts.py:156`; `tests/test_news_impact_cascade.py:126`, :808; `tests/test_news_impact_agreement.py:629`. F2-M:52 M11 is BROKEN: plain-language price-target and recommendation wording passes the gates | PARTIAL |

Exemplar: `tests/test_news_impact_mechanisms.py:825` (a contract option ceiling is not summed into recognised economics).

Best reachable rung without a human: OFFLINE_FIXTURE.

## V4 Policy or supply-chain event

§9.1 row (`MASTERPLAN.md:474`), quoted:
- Required observed behaviour: "Report/proposal/final/effective states distinct; sourced dated product/company exposure; alternatives and falsifiers"
- Consumer outcome: "Theme and MarketOntology show a conditional mechanism, not an asserted causal fact"

| Required property | Producer (path:line) | Persisted artifact | Consumer surface | Test | Status |
|---|---|---|---|---|---|
| Report, proposal, final and effective states distinct | `collectors/federal_register.py:58` stage taxonomy, :107 _reg_stage. `engine/policy_calendar.py:136` stores no separate effective date; :216 uses comments_close_on of final rules as a proxy | policy calendar rows | Foresight, below | `tests/test_policy_calendar.py:71`, :246 | PARTIAL: effective is not a distinct stored state |
| Sourced, dated product or company exposure | `scripts/build_foresight.py:1` | `site/foresight.html` and `site/basketdata/foresight_cascade.json` | Shell ANON; cascade JSON gated by `config/site_access.yml:24` | none located for exposure dating | PARTIAL: exposure is per theme |
| Alternatives and falsifiers | none located | none | NONE | none | ABSENT |
| Conditional mechanism, not asserted fact | News schema has policy_trade_control (:1107) and regulatory_probe (:1098) with no lifecycle state; `contracts/news_impact/channel_library.v1.json:1099` T2-AWARD-POLICY | contract | NONE | none located | PARTIAL |

Exemplar: `tests/test_policy_calendar.py:71` (latency join matched).

Best reachable rung without a human: COMMITTED_ARTIFACT.

## V5 Rumor → denial → confirmation

§9.1 row (`MASTERPLAN.md:475`), quoted:
- Required observed behaviour: "Original report, independent confirmations and denial remain versioned; copied wires do not inflate corroboration"
- Consumer outcome: "Current view and historical replay differ correctly"

| Required property | Producer (path:line) | Persisted artifact | Consumer surface | Test | Status |
|---|---|---|---|---|---|
| Original report stays versioned | `engine/qbus_news_store.py:239` news_revisions, :257 UNIQUE(revision_id, transport, message_id, received_at), :261 news_states | qbus news SQLite store | News views, SIGNED_IN via `config/site_access.yml:712` | `tests/test_qbus_news_store.py:177` | PRESENT_WITH_TEST |
| Independent confirmations | `engine/news_impact/thesis.py:1485` flags new_independent_source only for an unseen provenance group (:1717) | none | NONE | `tests/test_news_impact_thesis.py:1032` | PARTIAL |
| Copied wires do not inflate corroboration | Store count `engine/qbus_news_store.py:2160` is the number of publisher identities | store | SIGNED_IN (:712) | F2-R:50 R15 is BROKEN: a syndicated copy counts as a second source | PARTIAL: held in the thesis lane, broken in the store count |
| Denial stays versioned | `engine/news_events.py:303` has an mna_rumor class; no denial class located | none | NONE | none | ABSENT |
| Current view and historical replay differ | Store revisions as above | store | SIGNED_IN | F2-T:48 T04 is BROKEN: an archive retrieved today is not bound to a receipt on replay | PARTIAL |

Exemplar: `tests/test_news_impact_thesis.py:1032` (changed numeric terms, new independent source and source correction are distinguished).

Best reachable rung without a human: OFFLINE_FIXTURE. The store view is SIGNED_IN_HUMAN_GATE.

## V6 User research workflow

§9.1 row (`MASTERPLAN.md:476`), quoted:
- Required observed behaviour: "Read source → inspect company/theme → save/follow → propose thesis change through existing user owner"
- Consumer outcome: "Actual signed-in persistence and authorization; no second thesis or alert store"

| Required property | Producer (path:line) | Persisted artifact | Consumer surface | Test | Status |
|---|---|---|---|---|---|
| Read source | `engine/qbus_news_store.py:122` NewsReadRights; rights load at `app/ticker_news.py:341` | store | SIGNED_IN, site-full user required (`app/ticker_news.py:195-203`) | `tests/test_ticker_news_api.py:128` (unknown rights fail closed) | PRESENT_WITH_TEST |
| Inspect company or theme | `engine/company_theme_exposure/views.py:217-283` build_exposures (`C1_EXPOSURE_JOIN_CENSUS.md:141`) | exposure items | Not traced in this census | not traced | PARTIAL |
| Save or follow | No route on main persists a saved or followed source or theme. Of the 42 POST handlers in `app/*.py`, the ones closest to this need are `app/main.py:2238` (portfolio changes), `app/ontology_explorer.py:329` (portfolio v1), `app/account_prefs.py:131` (language and display theme) and `app/catalyst_integration.py:438` (Catalyst Scan email opt-in); none stores a news source or market theme. The cockpit row `MASTERPLAN.md:77` places follow and saved references in open Macro #9612 | none | NONE | none | ABSENT |
| Propose a thesis change through the existing user owner | `engine/news_impact/thesis.py:8` states there is no mutable thesis object; Mastermind tools and assessments are out of tree (`F1_CLAIM_EVIDENCE_DENOMINATOR_MATRIX.md:91`) | none | NONE in `app/` or `templates/` | none | ABSENT in this repository |
| No second thesis or alert store | `engine/news_impact/thesis.py:8` | none | none | none located | PRESENT_NO_TEST |

Exemplar: none on main. No committed fixture runs read, inspect, save and propose as one path.

Best reachable rung without a human: SIGNED_IN_HUMAN_GATE for the read step. NONE for save, follow and propose.

## V7 Quiet/outage/rights loss

§9.1 row (`MASTERPLAN.md:477`), quoted:
- Required observed behaviour: "Silent source, outage, stale data, missing history and access withdrawal distinguishable"
- Consumer outcome: "Honest degraded UI/AI output, no stale protected content, no duplicate work on recovery"

| Required property | Producer (path:line) | Persisted artifact | Consumer surface | Test | Status |
|---|---|---|---|---|---|
| Silent source versus outage | Health ladder `engine/qbus_news_receipts.py:306-321`; `app/ticker_news.py:408-421` maps a live source with zero rows to quiet | qbus.news_health.v1 receipt (`engine/qbus_news_receipts.py:25`) | Ticker news API, SIGNED_IN (`app/ticker_news.py:195-203`) | `tests/test_qbus_news_receipts.py:172`. A5 G1 (`A5_TRANSPORT_OBSERVABILITY_GAPS.md:39`): nightly families have no per-source health, and RSS cannot tell an empty feed from an unreachable one | PARTIAL |
| Stale data | Receipt ladder: receipt_stale gives unavailable, catchup_stale gives degraded (:306-321) | health receipt | API as above | `tests/test_qbus_news_receipts.py:146`, :159, :190. A5 G2 (`A5_TRANSPORT_OBSERVABILITY_GAPS.md:40`): additional sources carry no writer observation age | PRESENT_WITH_TEST for the writer; PARTIAL for additional sources |
| Missing history | `app/ticker_news.py:473`, :479 flow states ok, thin_history and unavailable | none | API | `tests/test_ticker_news_flow_api.py:456` (thin case at :449), :488 | PRESENT_WITH_TEST |
| Access withdrawal | `app/ticker_news.py:614-617` returns 503 when rights are unavailable; the stream rechecks rights | rights receipts (`app/ticker_news.py:338-347`) | API and SSE | `tests/test_ticker_news_api.py:222`, :412; `tests/test_ticker_news_end_to_end.py:287` | PRESENT_WITH_TEST |
| No stale protected content | `app/ticker_news.py:70` Cache-Control private, no-store | none | API | `tests/test_ticker_news_api.py:87` | PRESENT_WITH_TEST |
| Honest degraded output | Store unavailable returns 503, not an empty 200 | none | API | `tests/test_ticker_news_api.py:194` | PRESENT_WITH_TEST for the API |
| Honest degraded AI output | The Brief bindings B1 to B4 are each PARTIAL (`E4_BRIEF_BINDING_CENSUS.md:125-128`) | none | NONE | none | ABSENT |
| No duplicate work on recovery | Store uniqueness `engine/qbus_news_store.py:257` | store | none | `tests/test_qbus_news_store.py:177`. F2-T:51 T07 HELD. F2-M:54 M13 is NO_MECHANISM: no coalescing or spend budget before a model call. F2-T:59 T15 is NO_MECHANISM | PARTIAL |

Exemplar: `tests/test_ticker_news_end_to_end.py:287` (rights revoked mid-stream emits restricted and stops).

Best reachable rung without a human: OFFLINE_FIXTURE. The live API is SIGNED_IN_HUMAN_GATE.

## Cross-vertical requirements

`MASTERPLAN.md:479`, quoted: "Use at least two unrelated domains in addition to the original optics reference case. For global expansion, include cross-language and non-US examples, with coverage explicitly declared rather than assumed from translation support."

- The exemplars above come from macro releases (V1), SEC filings (V2), contract and buyback facts (V3) and Federal Register stages (V4). Each is an offline fixture or committed artifact, not a vertical proof.
- Non-US sources exist: `collectors/hk_hkexnews.py:16` and the `/chinanews/` prefix (`config/site_access.yml:713`).
- No committed declaration of per-language coverage was located in `engine/`, `config/` or `contracts/`.
- Status: PARTIAL.

`MASTERPLAN.md:481`, quoted: "The user-workflow proof must include a correction arriving after an assessment is saved or adopted. Retain its original evidence/version, display the new status and offer the authorised update path without an unrequested user-state mutation."

- The correction mechanism exists in the thesis lane (`engine/news_impact/thesis.py:1481`) and the store keeps revisions (`engine/qbus_news_store.py:239`).
- No saved or adopted assessment exists to receive it (V6 save and follow are ABSENT).
- Status: PARTIAL for the mechanism, ABSENT end to end.

## Summary

| Vertical | Properties | PRESENT_WITH_TEST | PRESENT_NO_TEST | PARTIAL | ABSENT | Best rung without a human |
|---|---|---|---|---|---|---|
| V1 Macro release and revision | 6 | 3 | 0 | 3 | 0 | COMMITTED_ARTIFACT |
| V2 Earnings/guidance | 6 | 2 | 0 | 3 | 1 | OFFLINE_FIXTURE |
| V3 Capital allocation or major contract | 5 | 4 | 0 | 1 | 0 | OFFLINE_FIXTURE |
| V4 Policy or supply-chain event | 4 | 0 | 0 | 3 | 1 | COMMITTED_ARTIFACT |
| V5 Rumor → denial → confirmation | 5 | 1 | 0 | 3 | 1 | OFFLINE_FIXTURE |
| V6 User research workflow | 5 | 1 | 1 | 1 | 2 | SIGNED_IN_HUMAN_GATE (read only) |
| V7 Quiet/outage/rights loss | 8 | 4 | 0 | 3 | 1 | OFFLINE_FIXTURE |

- Rows marked "PRESENT_WITH_TEST, no consumer" count as PRESENT_WITH_TEST. V1 row 2 and V7 row 2 count as PARTIAL, and V1 row 6 counts as PARTIAL.
- No vertical reaches ANON_DEPLOYED for its consumer outcome. Every displayed news surface is SIGNED_IN.
- The F2 findings cited above (R15, T04, M05, M06a, M06b, M11 BROKEN; M07b, M08, M13, T15 NO_MECHANISM) fall in V2, V3, V5 and V7.

## Evidence

Commands run at `044d1cc6` in a clean SSD worktree, plus `git show eaa60ce2:<path>` for F2:

```
sed -n 469,481p research/news_intelligence_estate_20261021/MASTERPLAN.md
grep -n "^def test" tests/test_release_target_truth.py tests/test_earnings_release_binding.py tests/test_qbus_news_receipts.py
grep -rln "release_forecast" app                 # no match
grep -rln "earnings_release" templates app/*.py  # no match
grep -rn -i -E "language_coverage|coverage_declared|declared_coverage" engine config contracts   # no match
grep -n -E "Depends|require_" app/ticker_news.py
git ls-files data/fred_vintage/release_targets
sed -n 687,722p config/site_access.yml
grep -n -E "^\| *(R15|T04|T07|T15|M05|M06a|M06b|M07b|M08|M11|M13) *\|" F2_*.md   # at eaa60ce2
```
