# Source and evidence index

All source and dataset links below bind immutable Macro commit `3d90aad6d83152dfeeaf8345bc995826ac9d3139`. This is the census observation epoch, not a claim that a later implementation is unchanged. Protected Mastermind procedure was read at `326c8469a21d7f50fc9ecb1848196bf1c6e66685`.

## 1. Production mechanism

| Ref | Immutable source | What it establishes |
|---|---|---|
| C1 | [config.yml](https://github.com/mastermindx-market-intelligence/macro/blob/3d90aad6d83152dfeeaf8345bc995826ac9d3139/config.yml#L6422-L6468) | Search universe and explicit extras |
| C2 | [collectors/china_universe.py](https://github.com/mastermindx-market-intelligence/macro/blob/3d90aad6d83152dfeeaf8345bc995826ac9d3139/collectors/china_universe.py#L249-L415) | Constituent selection and close cache |
| C3 | [collectors/china_stock_prices.py](https://github.com/mastermindx-market-intelligence/macro/blob/3d90aad6d83152dfeeaf8345bc995826ac9d3139/collectors/china_stock_prices.py#L34-L84) | Daily OHLC history and current-tail repair |
| C4 | [scripts/build_china_library.py](https://github.com/mastermindx-market-intelligence/macro/blob/3d90aad6d83152dfeeaf8345bc995826ac9d3139/scripts/build_china_library.py#L2508-L2696) | Responsibility screen, full signal input date |
| C5 | [engine/signal_gate.py](https://github.com/mastermindx-market-intelligence/macro/blob/3d90aad6d83152dfeeaf8345bc995826ac9d3139/engine/signal_gate.py#L379-L599) | Marker/cascade composition and buyability |
| C6 | [engine/signal_quality.py](https://github.com/mastermindx-market-intelligence/macro/blob/3d90aad6d83152dfeeaf8345bc995826ac9d3139/engine/signal_quality.py#L515-L645) | Quality hold/reclaim gates and known confirmation |
| C7 | [engine/confluence_tiers.py](https://github.com/mastermindx-market-intelligence/macro/blob/3d90aad6d83152dfeeaf8345bc995826ac9d3139/engine/confluence_tiers.py#L501-L629) | Tier and projection conditions |
| C8 | [engine/china_board_rank.py](https://github.com/mastermindx-market-intelligence/macro/blob/3d90aad6d83152dfeeaf8345bc995826ac9d3139/engine/china_board_rank.py#L105-L222) | Definitions, weights, caps and coverage contract |
| C9 | [engine/china_board_rank.py](https://github.com/mastermindx-market-intelligence/macro/blob/3d90aad6d83152dfeeaf8345bc995826ac9d3139/engine/china_board_rank.py#L284-L413) | Signal/entry/runway/theme score terms |
| C10 | [engine/china_board_rank.py](https://github.com/mastermindx-market-intelligence/macro/blob/3d90aad6d83152dfeeaf8345bc995826ac9d3139/engine/china_board_rank.py#L471-L674) | Intelligence attachment, coverage and ordering |
| C11 | [engine/china_board_rank.py](https://github.com/mastermindx-market-intelligence/macro/blob/3d90aad6d83152dfeeaf8345bc995826ac9d3139/engine/china_board_rank.py#L762-L948) | Enrichment, original points, rounding, ranks |
| C12 | [engine/china_board_rank.py](https://github.com/mastermindx-market-intelligence/macro/blob/3d90aad6d83152dfeeaf8345bc995826ac9d3139/engine/china_board_rank.py#L1129-L1435) | Execution, featured safeguards, lane partition, shadows |
| C13 | [engine/china_intel_interest.py](https://github.com/mastermindx-market-intelligence/macro/blob/3d90aad6d83152dfeeaf8345bc995826ac9d3139/engine/china_intel_interest.py) | Board-independent intelligence formula and current readers |
| C14 | [engine/china_altdata.py](https://github.com/mastermindx-market-intelligence/macro/blob/3d90aad6d83152dfeeaf8345bc995826ac9d3139/engine/china_altdata.py) | Seven-leg prior and earned-weight consumer |
| C15 | [engine/china_extras.py](https://github.com/mastermindx-market-intelligence/macro/blob/3d90aad6d83152dfeeaf8345bc995826ac9d3139/engine/china_extras.py#L35-L53) | Outer payload-clock erasure |
| C16 | [engine/china_intel_hub.py](https://github.com/mastermindx-market-intelligence/macro/blob/3d90aad6d83152dfeeaf8345bc995826ac9d3139/engine/china_intel_hub.py#L642-L766) | Latest trajectory/source readers |
| C17 | [engine/china_signal_lab.py](https://github.com/mastermindx-market-intelligence/macro/blob/3d90aad6d83152dfeeaf8345bc995826ac9d3139/engine/china_signal_lab.py#L43-L95) | Limited scorecard-based family adaptation |
| C18 | [scripts/build_china_library.py](https://github.com/mastermindx-market-intelligence/macro/blob/3d90aad6d83152dfeeaf8345bc995826ac9d3139/scripts/build_china_library.py#L3379-L3453) | Actual intelligence and rank invocation |
| C19 | [scripts/build_china_library.py](https://github.com/mastermindx-market-intelligence/macro/blob/3d90aad6d83152dfeeaf8345bc995826ac9d3139/scripts/build_china_library.py#L3969-L4438) | Lane assembly and Asia-only historical sinks |
| C20 | [scripts/build_china_library.py](https://github.com/mastermindx-market-intelligence/macro/blob/3d90aad6d83152dfeeaf8345bc995826ac9d3139/scripts/build_china_library.py#L4917-L4939) | Canonical JSON publication path |
| C21 | [scripts/build_china.py](https://github.com/mastermindx-market-intelligence/macro/blob/3d90aad6d83152dfeeaf8345bc995826ac9d3139/scripts/build_china.py#L145-L185) | Cached artifact admission check |
| C22 | [scripts/build_china.py](https://github.com/mastermindx-market-intelligence/macro/blob/3d90aad6d83152dfeeaf8345bc995826ac9d3139/scripts/build_china.py#L1896-L1918) | Build failure fallback |
| C23 | [templates/china.html.j2](https://github.com/mastermindx-market-intelligence/macro/blob/3d90aad6d83152dfeeaf8345bc995826ac9d3139/templates/china.html.j2#L3310-L3510) | Published card lanes and overflow sorting |
| C24 | [scripts/build_cn_live_pack.py](https://github.com/mastermindx-market-intelligence/macro/blob/3d90aad6d83152dfeeaf8345bc995826ac9d3139/scripts/build_cn_live_pack.py#L45-L119) | Frozen-board reader and caller |
| C25 | [engine/prophet_live/cn_pack.py](https://github.com/mastermindx-market-intelligence/macro/blob/3d90aad6d83152dfeeaf8345bc995826ac9d3139/engine/prophet_live/cn_pack.py#L133-L156) | Frozen score/rank field projection |
| C26 | [.github/workflows/asia-close.yml](https://github.com/mastermindx-market-intelligence/macro/blob/3d90aad6d83152dfeeaf8345bc995826ac9d3139/.github/workflows/asia-close.yml#L445-L473) | Actual scheduled reconciler invocation |
| C27 | [scripts/reconcile_cn_live.py](https://github.com/mastermindx-market-intelligence/macro/blob/3d90aad6d83152dfeeaf8345bc995826ac9d3139/scripts/reconcile_cn_live.py#L89-L184) | Unused pack argument and event/close-board consumers |
| C28 | [templates/cn_prophet_live.js](https://github.com/mastermindx-market-intelligence/macro/blob/3d90aad6d83152dfeeaf8345bc995826ac9d3139/templates/cn_prophet_live.js#L158-L176) | HTTP error/expiry path |
| C29 | [engine/china_microstructure.py](https://github.com/mastermindx-market-intelligence/macro/blob/3d90aad6d83152dfeeaf8345bc995826ac9d3139/engine/china_microstructure.py#L102-L189) | Already effective-dated current ST/board limits |
| C30 | [lib/cn_calendar.py](https://github.com/mastermindx-market-intelligence/macro/blob/3d90aad6d83152dfeeaf8345bc995826ac9d3139/lib/cn_calendar.py#L43-L123) | Official-notice-first calendar |
| C31 | [engine/china_standout_track.py](https://github.com/mastermindx-market-intelligence/macro/blob/3d90aad6d83152dfeeaf8345bc995826ac9d3139/engine/china_standout_track.py) | Original entry latch and public grade path |
| C32 | [engine/cn_prophet_audit.py](https://github.com/mastermindx-market-intelligence/macro/blob/3d90aad6d83152dfeeaf8345bc995826ac9d3139/engine/cn_prophet_audit.py) | Current-vintage episode telemetry and H10 conventions |
| C33 | [engine/track_scoring.py](https://github.com/mastermindx-market-intelligence/macro/blob/3d90aad6d83152dfeeaf8345bc995826ac9d3139/engine/track_scoring.py) | Shared episode and forward-grading owner |
| C34 | [engine/china_prophet_shadow.py](https://github.com/mastermindx-market-intelligence/macro/blob/3d90aad6d83152dfeeaf8345bc995826ac9d3139/engine/china_prophet_shadow.py) | Existing full-pool candidate store |
| C35 | [engine/confluence_latch.py](https://github.com/mastermindx-market-intelligence/macro/blob/3d90aad6d83152dfeeaf8345bc995826ac9d3139/engine/confluence_latch.py#L97-L150) | Observed T2 Boolean latch |
| C36 | [tests/test_cn_live_pack.py](https://github.com/mastermindx-market-intelligence/macro/blob/3d90aad6d83152dfeeaf8345bc995826ac9d3139/tests/test_cn_live_pack.py) | Existing injected-schema pack tests |
| C37 | [tests/test_cn_live_reconcile.py](https://github.com/mastermindx-market-intelligence/macro/blob/3d90aad6d83152dfeeaf8345bc995826ac9d3139/tests/test_cn_live_reconcile.py) | Existing injected event and workflow-string checks |

## 2. Existing data

The raw inputs remain in their existing repositories/stores. This docket stores diagnostics and input hashes, not a competing dataset owner.

- [site/factordata/china_standouts.json](https://github.com/mastermindx-market-intelligence/macro/blob/3d90aad6d83152dfeeaf8345bc995826ac9d3139/site/factordata/china_standouts.json)
- [data/china_standout_track/board.parquet](https://github.com/mastermindx-market-intelligence/macro/blob/3d90aad6d83152dfeeaf8345bc995826ac9d3139/data/china_standout_track/board.parquet)
- [data/china_standout_track/entry_latch.parquet](https://github.com/mastermindx-market-intelligence/macro/blob/3d90aad6d83152dfeeaf8345bc995826ac9d3139/data/china_standout_track/entry_latch.parquet)
- [data/china_prophet_rank/candidates.parquet](https://github.com/mastermindx-market-intelligence/macro/blob/3d90aad6d83152dfeeaf8345bc995826ac9d3139/data/china_prophet_rank/candidates.parquet)
- [data/cn_prophet_audit/forward_log.parquet](https://github.com/mastermindx-market-intelligence/macro/blob/3d90aad6d83152dfeeaf8345bc995826ac9d3139/data/cn_prophet_audit/forward_log.parquet)
- [data/cn_prophet_audit/latest.json](https://github.com/mastermindx-market-intelligence/macro/blob/3d90aad6d83152dfeeaf8345bc995826ac9d3139/data/cn_prophet_audit/latest.json)
- [data/cn_prophet_live/forward.parquet](https://github.com/mastermindx-market-intelligence/macro/blob/3d90aad6d83152dfeeaf8345bc995826ac9d3139/data/cn_prophet_live/forward.parquet)
- [data/china_search/members.parquet](https://github.com/mastermindx-market-intelligence/macro/blob/3d90aad6d83152dfeeaf8345bc995826ac9d3139/data/china_search/members.parquet)
- [data/china_search/dropped.parquet](https://github.com/mastermindx-market-intelligence/macro/blob/3d90aad6d83152dfeeaf8345bc995826ac9d3139/data/china_search/dropped.parquet)
- [data/china_search/index_cons.parquet](https://github.com/mastermindx-market-intelligence/macro/blob/3d90aad6d83152dfeeaf8345bc995826ac9d3139/data/china_search/index_cons.parquet)
- [data/china_valuation/percentiles.parquet](https://github.com/mastermindx-market-intelligence/macro/blob/3d90aad6d83152dfeeaf8345bc995826ac9d3139/data/china_valuation/percentiles.parquet)
- [data/china_analyst/forecast.parquet](https://github.com/mastermindx-market-intelligence/macro/blob/3d90aad6d83152dfeeaf8345bc995826ac9d3139/data/china_analyst/forecast.parquet)
- [data/china/510300.SS.parquet](https://github.com/mastermindx-market-intelligence/macro/blob/3d90aad6d83152dfeeaf8345bc995826ac9d3139/data/china/510300.SS.parquet)
- [data/china/510500.SS.parquet](https://github.com/mastermindx-market-intelligence/macro/blob/3d90aad6d83152dfeeaf8345bc995826ac9d3139/data/china/510500.SS.parquet)

Individual adjusted OHLC input hashes are recorded by the historical reproducer; raw legal-reference data belongs to the separate `data/china_stocks_raw/` owner. The original `510300.SS` benchmark file has close and volume only. Do not assume it contains opening prices.

## 3. In-repository prior evidence and authority

- [Do-not-rebuild register](https://github.com/mastermindx-market-intelligence/macro/blob/3d90aad6d83152dfeeaf8345bc995826ac9d3139/research/DO_NOT_REBUILD.md): exact killed constructions, not a blanket ban on distinct research.
- [Rank feature battery](https://github.com/mastermindx-market-intelligence/macro/blob/3d90aad6d83152dfeeaf8345bc995826ac9d3139/research/cn_prophet_audit/RANK_FEATURE_BATTERY.md) and [v3.1 adjudication](https://github.com/mastermindx-market-intelligence/macro/blob/3d90aad6d83152dfeeaf8345bc995826ac9d3139/research/cn_prophet_audit/SCORE_ITERATION_V3_1_ADJUDICATION.md): prior measured axes and limits; not re-executed as new claims here.
- [CN superintelligence roadmap](https://github.com/mastermindx-market-intelligence/macro/blob/3d90aad6d83152dfeeaf8345bc995826ac9d3139/research/PROPHET_CN_SUPERINTELLIGENCE_ROADMAP_BY_FABLE.md): existing component and hypothesis map; dated results and cadence assumptions require current verification.
- [China Alpha Intelligence workstream](https://github.com/mastermindx-market-intelligence/macro/blob/3d90aad6d83152dfeeaf8345bc995826ac9d3139/agentos/workstreams/WS-CHINA-ALPHA-INTELLIGENCE.md): existing source/candidate/grade ownership, CIE constraints and dependency distinctions.
- [Settled TuShare decision](https://github.com/mastermindx-market-intelligence/macro/blob/3d90aad6d83152dfeeaf8345bc995826ac9d3139/agentos/decisions/DEC-CNLI-TUSHARE-COMPLIANCE-IS-CHAIRMAN-VERIFIED-PRIVATE.md): compliance satisfied; no private document solicitation.
- [Prior semiconductor/leadership discovery](https://github.com/mastermindx-market-intelligence/macro/blob/3d90aad6d83152dfeeaf8345bc995826ac9d3139/agentos/discoveries/DSC-CN-PROPHET-SEMICON-LEADERSHIP-GATE-AUDIT.md): prior global fallback and bake-vintage finding; this audit extends it with October 9 counts and experiments.
- [TOI revival/integration chapter](https://github.com/mastermindx-market-intelligence/macro/blob/3d90aad6d83152dfeeaf8345bc995826ac9d3139/research/live_entry_radar/llr24/2026-10-06/11_TECHNICAL_OPPORTUNITY_REVIVAL_AND_INTEGRATION.md): reuse existing native setup/evaluation owners.
- [R0 replay #6871](https://github.com/mastermindx-market-intelligence/macro/pull/6871): original carrier preserved, observed head `51ddb898ff0c130910f9f3f4266727905826a92d` and Draft/HOLD. PR prose documents rejected prior assertions; it is not their rehabilitation.

## 4. This docket's evidence

| Artifact | Role / reproducibility boundary |
|---|---|
| [pipeline_evidence.json](pipeline_evidence.json) | Exact committed board, source dataset clocks, age census, true-schema frozen-reader probes and ignored-pack witness. |
| [reproduce_census.py](reproduce_census.py) | Immutable Git reads and disposable source-reader fixtures; no production writes. |
| [ordering_diagnostics.json](ordering_diagnostics.json) | Public-only shortlist sensitivity; separate candidate-snapshot coverage and 37 same-date intelligence-value differences. |
| [ordering_diagnostics.py](ordering_diagnostics.py) | Exact extracted order/coverage controls, published-cap positive control and source-rounded component omissions. |
| [ORDERING_REVIEW.md](ORDERING_REVIEW.md) | Independent review, including the caught and repaired rounding error and final accepted hashes. |
| [historical_evidence.json](historical_evidence.json) | Cohorts, matched-clock marks, as-published/current-fill reconciliation, frozen/common-cohort baselines and explicit unavailable analyses. |
| [HISTORICAL_EVALUATION.md](HISTORICAL_EVALUATION.md) | Human-readable historical interpretation and case studies. |
| [HISTORY_REVIEW.md](HISTORY_REVIEW.md) | Independent method review and recomputed metrics. |
| [RANK_METRICS_ADDENDUM.md](RANK_METRICS_ADDENDUM.md) | Requested precision@6, frozen top-decile excess-return/precision lift and one exact intended intelligence tie-break check; separate conditional cohorts and review. |
| [rank_metrics_pool_input.json](rank_metrics_pool_input.json) | Hash-bound subset of the original analytical CSV, including missing features, immature and missing-session outcomes; original manifest chain embedded. |
| [RANK_METRICS_REVIEW.md](RANK_METRICS_REVIEW.md) | Independent reconstruction of all 29 date gates, 55 arm/date controls, ten full pools, precision and paired bootstrap intervals; final report and handoff additions reviewed and accepted. |
| [rank_metrics_addendum.py](rank_metrics_addendum.py) / [rank_metrics_addendum.json](rank_metrics_addendum.json) | Reconstruct all 55 accepted arm/date controls before calculating the separately labeled ranking metrics; no new price or outcome generation. |
| [publication_probe.json](publication_probe.json) | Actual public HTML observation: source artifact membership/order comparison, page hash and timestamp; no JavaScript/visual/release-identity claim. |
| [publication_probe.py](publication_probe.py) | Replays a captured HTML page or performs one explicitly documented public HTTP read. |
| [pr_overlap.json](pr_overlap.json) | Freshly read existing PR identities/paths, not a new ownership or live-worker registry. |
| [VERIFICATION.md](VERIFICATION.md) | Commands, review decisions, hashes and effect/readback receipts. |

## 5. Public primary sources

[CHINA_MARKET_AND_RESEARCH.md](CHINA_MARKET_AND_RESEARCH.md) contains the 26-item M1–M12 / R1–R14 primary-source index with exact rule locators, publication dates and access limitations. Exchange-rule facts were checked against current official exchange/HKEX documents. Research was drawn from original papers, author repositories and original institutional abstracts. No paper's reported investment performance is presented as a reproduced product result.

The public page observation is [China stock dashboard](https://mastermind-x.com/china_stocks.html), captured 2026-10-09 at 21:08:14 UTC. Its 24 featured names and their order match the pinned artifact; its 124 additional cards match the score-sorted overflow. The public JSON routes returned unauthenticated HTTP401. Historical first-publication proof cannot be reconstructed from this one current observation.
