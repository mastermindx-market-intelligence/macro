# Commission 16 — Current Estate Census
## Operational Alternative Data Adapters
**Evidence cut: 4 October 2026 · Research companion · Read-only source archaeology**

## 1. Conclusion and scope

Mastermind already has several operationally adjacent measurements, but the inspected estate does not yet constitute the company-KPI Operational Sensor layer proposed by Commission 16. App ratings, GitHub mindshare, Hugging Face download momentum, DOL foreign-labor certification intent, and aggregate import flows have existing source or transformation owners. They must be reused or extended through those owners. Their existence does not establish a usable company nowcast, an expectation surprise, independent information, or production acceptance.

Two corrections to the supplied research are material. First, broad claims that hiring or customs infrastructure is absent are too strong: TIL W7 and W8 already contain DOL certification and Census import-flow machinery. Second, the August statement that the mid/slow primary cohorts were ungraded is historical. The October 3 committed qledger contains matured 63-day observations for both families; their displayed means remain negative and their cohorts remain below the ledger's date-based promotion floors. [M06][M07][M08][M09][M10][M11][M12][M13]

This census covers Macro and mastermind-terminal only. It is an evidence companion to the main A–L report, not a replacement for the Mastermind census, Research Vault source resolution, legal source-rights review, or vendor evaluation. It used bounded GitHub trees, files, search results, pull-request metadata, and Actions receipts. No repository clone, source-host probe, external mutation, new acquisition, or implementation was performed.

| Repository | Pinned revision | Branch qualification |
|---|---|---|
| `mastermindx-market-intelligence/macro` | `79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f` | `main`; the branch response showed `protected=false`. It must not be described as protected. |
| `mastermindx-market-intelligence/mastermind-terminal` | `1c708450187755160e1a5889b69598a2fcb1f0d1` | Protected `master`, as observed in the source pin. |

Publication recheck by the integrating owner: Macro main advanced to [59a0789c0e5ffcce15e682b6f3880f3eacc6f6fc](https://github.com/mastermindx-market-intelligence/macro/commit/59a0789c0e5ffcce15e682b6f3880f3eacc6f6fc), a direct child changing only two Trend Persistence coordination documents. Sensor code/contracts/artifacts cited here are unchanged. Terminal's head was unchanged.

Every main-branch source link below uses these immutable revisions. Open PRs are separate candidate surfaces, observed during the census; their bodies are author claims and must not be promoted into facts about merged production behavior.

## 2. App demand: existing proxy, incomplete coverage, no true usage

Macro's Quiver app adapter acquires app-store ratings by ticker. The transformation aggregates review counts and computes a review-weighted rating. Its `app_demand` channel fires only when the resulting rating is at least 4.3 and total reviews are at least 1,000. Review velocity compares the latest and prior snapshot, with a 1,000-review denominator floor, but it is explicitly a display-only field. The channel does not consume it. Therefore “rating/review proxy” is the accurate description; downloads, active users, sessions, retention, paid conversion, subscriptions, or app revenue have not been established by this source. [M01]

The distinction is consequential. A high accumulated review count can satisfy the channel while current users or monetization decline. A changed app portfolio can alter total reviews without a comparable operating change. A sensor extension should preserve raw measurement semantics, app identity, observation time, provider coverage, and the company's relevant KPI bridge rather than rename the existing rule as “usage.”

An incumbent coverage diagnostic is already open: **Macro PR #7420**, head `de1dfc7093c5170fd53f7f41c6362b612c900769`. Its body reports a frozen source of 178,845 retained rows, 812 provider ticker keys, and 98 snapshot dates. At an explicit September 18 cutoff, 1,810 later-observed rows are excluded. The unchanged app function yields 732 eligible summaries and 312 strong-rule summaries; its normal top-15 cap retains 15 and excludes 297 strong-rule keys. The diagnostic also distinguishes unknown clocks, later observations, app-cohort changes, decreasing counters, missing comparisons, duplicates, and invalid measurements. [P01]

These are candidate diagnostic receipts, not 297 missed trades, canonical issuer resolution, real usage, learned alpha, or authenticated product proof. Commission 16 should coordinate with this carrier rather than duplicate its cutoff and coverage instrumentation. Its stated integration boundary preserves #7305 named sponsorship, #7361 Hub presentation, and #7175 Defense Intelligence. Source acquisition and Quiver commercial rights remain separate questions. [P01]

## 3. Developer activity: usable measurement owners, narrow causal interpretation

The GitHub collector snapshots stargazers and forks for curated public repositories, then represents each ticker by the repository with the largest star count. Its forks value comes from that selected repository; this is not a sum of all company repository activity. The curated map contains 17 ticker keys and expressly describes the blind spot for closed-source SaaS and API-only AI providers. The engine derives week-over-week star velocity and marks positive momentum at or above the cross-sectional median as “hot.” This is developer mindshare, not production deployment, paid-seat growth, or company revenue. [M02][M03][M04]

Hugging Face uses a different instrument: for each curated author organization it sums downloads across the top 25 models, then aggregates authors into the ticker. Its nine-ticker mapping favors companies publishing open weights. The engine compares the trailing-30-day download measure across snapshots, producing relative model-adoption momentum. Download telemetry can be economically relevant, but attribution, model replacement, automated downloads, hosted APIs, and monetization can intervene before any reported KPI. [M03][M04]

Both collectors record `_first_seen`, yet their daily snapshot deduplication uses `keep="last"` for `(ticker, snapshot_date)`. Thus comments calling the tables append-only should not be converted into a claim that every original same-day observation survives immutably. A company-KPI sensor needs an explicit revision policy and availability contract before historical nowcasts can rely on these tables. [M02][M03]

The convergence kernel assigns weights 0.30 to `github_momentum` and 0.35 to `hf_model_momentum`; both route to `altdata_mid`. These existing channels are relevant adjacent owners and narrow candidate measurement inputs. Their prior weights and “hot” rule do not prove causal KPI accuracy or independent investment information. [M01][M06]

## 4. Hiring and physical trade: existing TIL owners, incomplete operational evidence

### DOL hiring intent

`collectors/dol_labor_certs.py` already acquires public LCA and PERM disclosure files. `engine/theme_hiring.py` derives per-basket certification velocity, AI/ML title share, and median-wage change. Employer mapping reuses `lib.warn_fuzzy` and the shared WARN ticker map; the module explicitly prohibits a second employer matcher. TIL W7 owns this source and transformation. This is foreign-labor certification intent, not a broad daily job-posting or total workforce panel. [M10][M11]

The availability contract needs care. The collector says rows are keyed by certification decision date while file publication is retained, and documents publication lag of four to eight weeks after quarter-end. A historical reader cannot assume that decision date is the date the observation became publicly knowable. File release, ingestion, and first availability must constrain the cutoff independently. Reusing the existing owner does not remove that audit obligation. [M10]

Synapse identifies `til-w7-hiring-intent`, runner-local and gitignored certificate storage, separate display metrics, no scored surfaces, and no consumers for either hiring output. At the pinned revision the proposed site projection, `site/basketdata/hiring_intent.json`, is absent in the inspected directory and returns 404. Code and registry entries exist; a current committed hiring output and a natural production-to-consumer journey were not verified. [M13]

### Census import flows

TIL W8 already acquires US Census monthly HS-code imports and derives per-theme year-over-year growth and recent-versus-annual acceleration. The sign rule distinguishes imports confirming demand from declining imports confirming domestic substitution. It deliberately keeps theme legs separate, prohibits a cross-theme composite, and prohibits folding the leg into `fused_obs_z`. This is aggregate physical-flow context, not company manifests, customs counterparty identity, or issuer shipment/revenue measurement. [M12]

The committed site artifact is especially instructive. Its September 30 `as_of` and generation receipt coexist with `parquet_absent=true`, zero of 29 configured HS codes with data, and zero of 11 themes with data. It explains the missing source rather than fabricating values. Fresh render time therefore cannot be treated as a successful data-acquisition receipt. Synapse records existing consumers in State of Themes and Neural Web Ask Brain, but consumer declarations alone do not establish a live non-null journey. [M13][M14]

A false methodology assumption must also be corrected before this collector becomes a Commission 16 historical input. Its source comment says trade statistics are not revised after roughly a two-month lag and consequently no revision column is needed. That is unsafe as a PIT contract: the vendor-verification companion's authoritative Census check records monthly and annual revisions, including changes to previously published historical data. See [Census program methodology](https://www.census.gov/foreign-trade/guide/sec2.html) and [International Trade API documentation](https://www.census.gov/data/developers/data-sets/international-trade.html). This census establishes that the problematic assumption is present in code; it does not reconstruct historical trade vintages. [M12]

## 5. Alt-data reboot and current outcome state

The actual canonical family names are `altdata_event`, `altdata_flow`, `altdata_mid`, `altdata_slow`, and `altdata_attention`. No `altdata_fast` family was found in the inspected routing. Event and flow use 21-day rulers, mid and slow 63-day rulers, and attention a five-day fade. The highest-weight channel assigns the thesis family while all channels remain recorded. App, GitHub, and Hugging Face belong to mid. [M06][M07]

This construction addresses generic convergence timing, not company/KPI sensor causality. A new operational channel placed into this kernel could receive a horizon determined by an unrelated co-firing channel. Commission 16 should keep KPI targets, sensor families, availability clocks, and independent evaluations explicit, then earn any downstream claim authority through existing evaluation owners.

The July reboot diagnosed horizon mismatch, correlated same-day claim bursts, and absent placebo controls. It froze legacy claims, introduced family routing and episode cooldowns, and registered two matched placebos per new-family claim. Attention was dormant by construction in the W2 plan; independent attention emission and later promotion studies were deferred. [M07]

The August 13 first-cohort adjudication remains a binding historical caution: 58 graded convergence rows from only two firing dates, 44.83% directional accuracy, and −0.103% mean SPY excess. Five already-due ungraded names worsened the due-panel sensitivity to 63 rows, 41.27% accuracy, and −0.507% mean. The ruling was **HOLD — adverse first maturity, non-decision-grade**, preserving display demotion and prohibiting post-result sign flipping or channel optimization. It also diagnosed clock and construction epoch contamination. [M08]

By October 3, matured mid/slow primary cohorts exist. The following are the committed **display** `by_family` receipts, not pooled proof across clock vintages. [M09]

| Family and ruler | Observations | Dates | Directional hit rate | Mean signed excess | Display state |
|---|---:|---:|---:|---:|---|
| Event @21 | 104 | 19 | 48.08% | +0.7771% | ACCRUING |
| Flow @21 | 50 | 14 | 42.00% | −0.8641% | ACCRUING |
| Mid @63 | 22 | 6 | 40.91% | −1.2884% | ACCRUING |
| Slow @63 | 93 | 11 | 35.48% | −2.3153% | ACCRUING |

The **authority-bearing ladder** uses different clock eligibility. Event @21 counts only six corrected `trading_days` dates and flow @21 only four; their older 19/14-date vintages are excluded. Mid/slow @63 use legacy unstamped clocks with six/11 dates. All relevant eligibility decisions are false and below the 25-independent-date floor. Mixed-clock 5/21 display panels disclose `pooling_refused=true`. Using the largest historical display date count to imply current promotion readiness would misstate the instrument. [M09]

Two other ledgers must remain distinct. October 3 deterministic convergence has 288 scored rows, a 54.5% “hit rate” defined as survival of a −5% falsifier, and only 41.3% directional accuracy. The separate Mastermind-facing brain emit has `is_context_only=true`, Article 3 not granted because `n=17<25`, and brain calibration `n_scored=0` with 27 open theses. Zero brain scores does not erase the deterministic ledger; the deterministic survival rate does not establish positive directional edge. [M15][M16]

## 6. Freshness, workflow success, and proof rung

Committed `data/run_status.json` records an October 3 run and “ok” statuses for GitHub, Hugging Face, and app ratings, with `last_date=2026-10-03`. Their reported `rows=1` means a tiny ingest-log row, not one measured issuer or complete provider coverage. Source parquet blobs exist, but the connector's text retrieval did not decode their actual observations. Therefore source-table maximum timestamps are not independently established here. [M17]

| Source table at Macro pin | Blob SHA | Bytes | Verified rung |
|---|---|---:|---|
| `data/quiver/appratings.parquet` | `2be7279fbd0a652fac6dd8e6c8b6a814c05531f9` | 1,908,308 | Committed blob exists; row contents not decoded |
| `data/github/repo_stars.parquet` | `e74a9e4d71c30453cab3b5a6989dc1d40b69acb8` | 17,125 | Committed blob exists; row contents not decoded |
| `data/huggingface/downloads.parquet` | `b1a85bf7323ec6effa8241327bc426f723d22c95` | 11,754 | Committed blob exists; row contents not decoded |

The latest scheduled daily run observed in the bounded Actions census was run **37172153941**, created October 4 at 02:48:01 UTC, on `dfcb3042aea4a9653f2b5ecc5200a61af5bd2366`, with overall conclusion success. Its collect, engine, and collect-tail jobs were **all skipped**. This is a successful workflow receipt, not a latest-successful collector execution. Workflow-specific run-list endpoints were connector-rejected; broader pagination was not substituted. [W01]

For these sensors, the established rungs are source architecture, selected committed artifacts, and limited status/workflow receipts. Natural scheduled acquisition, non-null source freshness, publication, downstream consumption, and an authenticated visible result have not been proved as one journey. This companion is explicitly **not live runtime acceptance**.

## 7. Semiconductor comparator and bounded negatives

A semiconductor-first commission should consider public issuer monthly operating KPIs as a comparator before importing a consumer-spend priority unchanged. The repository already contemplated “TSMC monthly revenue surprise → US semis residual drift” and cautioned that the release is plausibly priced immediately. The international audit explicitly listed a TSMC monthly-revenue feed as a new collector needed. This supports a candidate experiment, not a measured return edge. [M18][M19]

Bounded search also found June and August 2026 TSMC monthly disclosure prose in Special Situations classifier caches, categorized `None` as routine 6-K disclosures: [June classifier entry](https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/data/special_situations/classify_cache/0001046179-26-000447.json) and [August classifier entry](https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/data/special_situations/classify_cache/0001046179-26-000658.json). Such model-authored summaries establish disclosure awareness, not a canonical numeric monthly KPI series, independently verified values, PIT corporate mapping, or contemporaneous expectation surprise. This prose does not constitute completed sensor acquisition.

No direct Similarweb, Facteus, or Panjiva result appeared in the combined vendor-keyword query. The inspected collector filenames did not identify card-spend, modeled-web-traffic, broad job-posting, company customs-manifest, or foot-traffic adapters. The TSMC search found research and disclosure-summary adjacency rather than a named canonical collector. These are **negatives within bounded searched surfaces**, not proof of global absence across experimental branches, uncommitted runners, external stores, or the wider estate.

## 8. Consumer ownership and collision ledger

Terminal's existing Macro bridge trims source stockdata into `intel/v1` and already handles freshness abstention. Company Intelligence separately provides an immutable-generation, same-origin BFF and strict normalization, field lineage, source date/hash receipts, and a context-only boundary. Its admitted source kinds are earnings history, score overlay, and transcript; an operational sensor family is not currently admitted in the inspected contract. The natural integration seam is a typed extension through the canonical producer, followed by the bounded Terminal contract. Browser components should not become acquisition or scoring owners. [T01][T02][T03]

The GMI disposition sweep permits consuming existing organ outputs while inheriting their fences. Company Theme Exposure is extended through its incumbent sidecar contract. Hiring, import flows, and adoption remain separate context legs. AgentOS names `WS-GMI-THEME-GRAPH` as active, owner `coo-fable`, with production proof obligations and no duplicate graph/state truth. [M20][M21]

| Open or adjacent carrier | Collision implication |
|---|---|
| Macro #7420 | App cutoff, coverage, and measurement diagnostics; extend its incumbent research path |
| Macro #7305; #7361; #7175 | Sponsorship, Hub presentation, and Defense owners explicitly preserved by #7420 |
| Macro #8324; #8417 | Audited GMI completion plan and state/Company Theme Exposure/finalized-cohort reader integration |
| Macro #7870 | Semiconductor Theme Intelligence B implementation carrier, observed DRAFT/HOLD |
| Terminal #777 | Private Investigation persistence and pinned Earnings/layout context |
| Terminal #792 | Closed Investigation research-manifest validation; candidate states no application consumer/API/database behavior enabled |
| Terminal #778 | Existing saved-view integrity and typed definitions; draft implementation, separate database/deployment acceptance |

The PR census was bounded to a top-15 broad query and a top-10 alt-data-focused query. The table identifies coordination surfaces; it is not an exhaustive planned-write intersection or release approval. Before implementation, the commissioned owner must refresh candidate heads and changed paths. [P01][P02][P03][P04][P05][P06][P07][P08]

## 9. Source register and provenance

The historical input was the supplied **“MastermindX Research Commission — Operational Alternative Data Adapters”** attachment. Its older heads and August outcome statements were used as hypotheses to verify, not current source authority. The companion hardening audit resolves Research Vault to Macro's `engine/research_vault`, `app/research.py`, and associated contracts, rather than the separate `executive-dr-vault` repository. The [pinned Vault masterplan](https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/research/RESEARCH_VAULT_MASTERPLAN.md) explicitly defines a display-tier document surface and separates access control from redistribution rights. No individual Vault document was used as a research source in this commission.

The following register supplies exact source locations and Git blob identities. Main-source links are immutable; PR links identify candidate carriers.


| Ref | Immutable source | Git blob SHA |
|---|---|---|
| M01 | [engine/altdata_models.py, L189–233](https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/engine/altdata_models.py#L189-L233) | `af7bb95f283efc28e84304c29c6e780632ec49c4` |
| M02 | [collectors/github_repos.py, L56–93](https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/collectors/github_repos.py#L56-L93) | `388e575481e0c1fa70eb544cf1a458d9fb0cf83b` |
| M03 | [collectors/huggingface.py, L56–76](https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/collectors/huggingface.py#L56-L76) | `a22c9ee30ceafe082c6da4c1bce0ba634c30bf3d` |
| M04 | [engine/altdata.py, L698–777](https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/engine/altdata.py#L698-L777) | `6bb05b69e97370652502629fb66314964f79bd84` |
| M05 | [data/github/repo_ticker.json, L1–27](https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/data/github/repo_ticker.json#L1-L27) | `8b63fe85390c3a94c038cce2a1c088ad36427cec` |
| M06 | [engine/altdata_ledger.py, L71–130](https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/engine/altdata_ledger.py#L71-L130) | `a84ea31856ca93503251d086c03d85713b11e6e9` |
| M07 | [research/ALTDATA_REBOOT.md, L1–7](https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/research/ALTDATA_REBOOT.md#L1-L7) | `95be63c823aaf50ab46873a9c72265282747ccb6` |
| M08 | [research/ALTDATA_CONVERGENCE_FIRST_COHORT_ADJUDICATION_2026-08-13.md, L7–106](https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/research/ALTDATA_CONVERGENCE_FIRST_COHORT_ADJUDICATION_2026-08-13.md#L7-L106) | `e4b6537278f88a8fef447f4ae83a86326c0d8710` |
| M09 | [site/qledger/track_record.json, L1202–1397](https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/site/qledger/track_record.json#L1202-L1397) | `735273741e518130c59ab8c80c133aac5004649a` |
| M10 | [collectors/dol_labor_certs.py, L1–57](https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/collectors/dol_labor_certs.py#L1-L57) | `0d45cd39603c01d2f2f4fe4f5020812c281230d5` |
| M11 | [engine/theme_hiring.py, L1–48](https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/engine/theme_hiring.py#L1-L48) | `44794e3003af3f1097fed5a1e9d9bde5900c9279` |
| M12 | [collectors/census_trade.py, L1–46](https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/collectors/census_trade.py#L1-L46) | `6fb7be62cef3214d8f0176e08728221893088323` |
| M13 | [config/synapse.yml, L13802–13884](https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/config/synapse.yml#L13802-L13884) | `b931b59948ab3f66ce3c04a42084cd729e03390d` |
| M14 | [site/basketdata/trade_flows.json, L1–36](https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/site/basketdata/trade_flows.json#L1-L36) | `0072721b9caf217bc10e7fd3175061bb329dc16b` |
| M15 | [data/altdata/track_record.json, L1–13](https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/data/altdata/track_record.json#L1-L13) | `8e59e1a9a7df5f441496abc6d56349759a94e39f` |
| M16 | [data/altdata/mastermind.json, L1–21](https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/data/altdata/mastermind.json#L1-L21) | `c0d3bf704c13aab338b58ad6241e2c977b9e72d4` |
| M17 | [data/run_status.json, L1258–1267](https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/data/run_status.json#L1258-L1267) | `a8a59900b1ca63d144bd35f9f4224030a12cbcc4` |
| M18 | [research/SIGNAL_LAB_FRONTIER_DAY2_FABLE_DOCKET_2026-07-06.md, L35–41](https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/research/SIGNAL_LAB_FRONTIER_DAY2_FABLE_DOCKET_2026-07-06.md#L35-L41) | `d028530b658425e98ceeb236670fc79fa17583d7` |
| M19 | [research/INTL_ENGINE_PROBLEM_AUDIT_FOR_FABLE.md, L593–602](https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/research/INTL_ENGINE_PROBLEM_AUDIT_FOR_FABLE.md#L593-L602) | `adcdbab42b89bb4747255b2b80ce0a5d878f4e60` |
| M20 | [research/theme_graph/THEME_ORGAN_DISPOSITION_SWEEP.md, L7–40](https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/research/theme_graph/THEME_ORGAN_DISPOSITION_SWEEP.md#L7-L40) | `dbd939d6034d4fe4209c2a2ad424204e133f6cf7` |
| M21 | [agentos/workstreams/WS-GMI-THEME-GRAPH.md, L1–25](https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/agentos/workstreams/WS-GMI-THEME-GRAPH.md#L1-L25) | `db5a41f3516c22665341a83952b018889322568c` |
| T01 | [ingest/pull_macro_intel.py, L1–33](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/1c708450187755160e1a5889b69598a2fcb1f0d1/ingest/pull_macro_intel.py#L1-L33) | `ddbd09edcca9731f93e9f7dba25aa9ba37fc6deb` |
| T02 | [terminal/lib/companyIntelligence.ts, L1–33](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/1c708450187755160e1a5889b69598a2fcb1f0d1/terminal/lib/companyIntelligence.ts#L1-L33) | `6b15b8f1a68348c2fcaebd3dc973d7748b4a1b33` |
| T03 | [docs/COMPANY_INTELLIGENCE_WORKSPACE.md, L3–10](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/1c708450187755160e1a5889b69598a2fcb1f0d1/docs/COMPANY_INTELLIGENCE_WORKSPACE.md#L3-L10) | `d0a1ce9243be506e728a4fad9a92c8d4695e41a2` |

Additional ranges: M01 channels L614–691; M06 rulers and cooldowns L105–130; M07 deferred work and matured-cohort amendment L257–305; M09 authority ladders L3349–3660; M13 trade owner/consumers L14137–14245; M17 GitHub L1313–1322 and app ratings L2189–2198. HF mapping: [data/huggingface/author_ticker.json](https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/data/huggingface/author_ticker.json), blob `c530eb34d23d083bcb90e69da2c1f95a0235d94f`. Trade transform: [engine/theme_trade_flows.py, L1–46](https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/engine/theme_trade_flows.py#L1-L46), blob `f222eb597b4197d4326c553a81fc5038f798121a`.

- P01: [macro PR #7420](https://github.com/mastermindx-market-intelligence/macro/pull/7420).
- P02: [macro PR #7305](https://github.com/mastermindx-market-intelligence/macro/pull/7305).
- P03: [macro PR #8324](https://github.com/mastermindx-market-intelligence/macro/pull/8324).
- P04: [macro PR #8417](https://github.com/mastermindx-market-intelligence/macro/pull/8417).
- P05: [macro PR #7870](https://github.com/mastermindx-market-intelligence/macro/pull/7870).
- P06: [mastermind-terminal PR #777](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/777).
- P07: [mastermind-terminal PR #792](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/792).
- P08: [mastermind-terminal PR #778](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/778).
- W01: [scheduled daily run 37172153941](https://github.com/mastermindx-market-intelligence/macro/actions/runs/37172153941); overall success with acquisition/engine jobs skipped.

[M01]: https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/engine/altdata_models.py#L189-L233
[M02]: https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/collectors/github_repos.py#L56-L93
[M03]: https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/collectors/huggingface.py#L56-L76
[M04]: https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/engine/altdata.py#L698-L777
[M05]: https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/data/github/repo_ticker.json#L1-L27
[M06]: https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/engine/altdata_ledger.py#L71-L130
[M07]: https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/research/ALTDATA_REBOOT.md#L1-L7
[M08]: https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/research/ALTDATA_CONVERGENCE_FIRST_COHORT_ADJUDICATION_2026-08-13.md#L7-L106
[M09]: https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/site/qledger/track_record.json#L1202-L1397
[M10]: https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/collectors/dol_labor_certs.py#L1-L57
[M11]: https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/engine/theme_hiring.py#L1-L48
[M12]: https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/collectors/census_trade.py#L1-L46
[M13]: https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/config/synapse.yml#L13802-L13884
[M14]: https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/site/basketdata/trade_flows.json#L1-L36
[M15]: https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/data/altdata/track_record.json#L1-L13
[M16]: https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/data/altdata/mastermind.json#L1-L21
[M17]: https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/data/run_status.json#L1258-L1267
[M18]: https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/research/SIGNAL_LAB_FRONTIER_DAY2_FABLE_DOCKET_2026-07-06.md#L35-L41
[M19]: https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/research/INTL_ENGINE_PROBLEM_AUDIT_FOR_FABLE.md#L593-L602
[M20]: https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/research/theme_graph/THEME_ORGAN_DISPOSITION_SWEEP.md#L7-L40
[M21]: https://github.com/mastermindx-market-intelligence/macro/blob/79251a22d731cf3f7e8d8ba2185bfcd0e9bb098f/agentos/workstreams/WS-GMI-THEME-GRAPH.md#L1-L25
[T01]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/1c708450187755160e1a5889b69598a2fcb1f0d1/ingest/pull_macro_intel.py#L1-L33
[T02]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/1c708450187755160e1a5889b69598a2fcb1f0d1/terminal/lib/companyIntelligence.ts#L1-L33
[T03]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/1c708450187755160e1a5889b69598a2fcb1f0d1/docs/COMPANY_INTELLIGENCE_WORKSPACE.md#L3-L10
[P01]: https://github.com/mastermindx-market-intelligence/macro/pull/7420
[P02]: https://github.com/mastermindx-market-intelligence/macro/pull/7305
[P03]: https://github.com/mastermindx-market-intelligence/macro/pull/8324
[P04]: https://github.com/mastermindx-market-intelligence/macro/pull/8417
[P05]: https://github.com/mastermindx-market-intelligence/macro/pull/7870
[P06]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/777
[P07]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/792
[P08]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/778
[W01]: https://github.com/mastermindx-market-intelligence/macro/actions/runs/37172153941
